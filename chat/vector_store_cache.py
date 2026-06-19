"""
Кэширование FAISS базы и эмбеддингов в памяти
"""
import os
from pathlib import Path

import faiss
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from .etl_pipeline import DocumentETLPipeline
import torch

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
DB_DIR = BASE_DIR / "db"
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Глобальные переменные для кэширования
_embeddings = None
_vector_db = None


def get_embeddings():
    """Загружает модель эмбеддингов с явным указанием устройства"""
    global _embeddings

    if _embeddings is None:
        print("⏳ Загрузка модели эмбеддингов...")

        try:
            _embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                model_kwargs={
                    'device': 'cpu',  # ← Явно указываем CPU
                },
                encode_kwargs={
                    'normalize_embeddings': True
                }
            )
            print("✅ Модель загружена на CPU")
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            # Фоллбэк: пробуем без torch_dtype
            _embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                model_kwargs={'device': 'cpu'}
            )

    return _embeddings


def load_vector_store():
    """
    Загружает FAISS базу (загружается один раз)
    """
    global _vector_db
    if _vector_db is None:
        if not DB_DIR.exists():
            print("❌ База FAISS не найдена")
            return None
        try:
            embeddings = get_embeddings()
            _vector_db = FAISS.load_local(
                str(DB_DIR),
                embeddings,
                allow_dangerous_deserialization=True
            )
            print("✅ База FAISS загружена в память")
        except Exception as e:
            print(f"❌ Ошибка загрузки FAISS: {e}")
            return None
    return _vector_db


def reset_cache():
    """
    Сбрасывает кэш (используется при пересоздании базы)
    """
    global _vector_db, _embeddings
    _vector_db = None
    # Эмбеддинги не сбрасываем — они тяжёлые и не меняются
    print("🔄 Кэш FAISS сброшен")


def create_vector_store():
    """
    Создаёт FAISS базу используя Big Data ETL pipeline
    """
    global _vector_db

    from .etl_pipeline import DocumentETLPipeline

    print("\n" + "=" * 60)
    print("🚀 СОЗДАНИЕ FAISS БАЗЫ С ETL PIPELINE")
    print("=" * 60)

    # 1. Запуск ETL Pipeline
    print("\n📥 Этап 1: Запуск ETL Pipeline...")
    pipeline = DocumentETLPipeline(num_workers=2)

    # Получаем список файлов
    file_paths = [str(f) for f in DOCS_DIR.glob("**/*.txt")]

    if not file_paths:
        print("❌ Не найдено файлов в", DOCS_DIR)
        return None

    print(f"📄 Найдено файлов: {len(file_paths)}")

    # Запускаем ETL
    df = pipeline.run(file_paths)
    pipeline.close()

    print(f"✅ ETL завершён: обработано {len(df)} чанков")

    # 2. Конвертация DataFrame в LangChain документы
    print("\n📝 Этап 2: Создание LangChain документов...")
    from langchain_core.documents import Document

    documents = []
    for _, row in df.iterrows():
        doc = Document(
            page_content=row['text'],
            metadata={
                'source': row['filepath'],
                'category': row.get('category', 'unknown')
            }
        )
        documents.append(doc)

    print(f"✅ Создано {len(documents)} документов")

    # 3. Дополнительный чанкинг (если нужно)
    print("\n✂️ Этап 3: Дополнительный чанкинг...")
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    texts = text_splitter.split_documents(documents)
    print(f"✅ После чанкинга: {len(texts)} фрагментов")

    # 4. Создание эмбеддингов и FAISS
    print("\n🔢 Этап 4: Создание эмбеддингов и FAISS индекса...")
    embeddings = get_embeddings()

    # Создаём FAISS
    index = faiss.IndexFlatIP(384)  # <--- ВОТ ОНО, 384!
    db = FAISS.from_documents(texts, embeddings, index=index)

    # 5. Сохранение на диск
    print("\n💾 Этап 5: Сохранение базы на диск...")
    DB_DIR.mkdir(exist_ok=True)
    db.save_local(str(DB_DIR))

    print(f"✅ База сохранена в {DB_DIR}")

    # Обновляем глобальную переменную
    _vector_db = db

    print("\n" + "=" * 60)
    print("✅ FAISS БАЗА УСПЕШНО СОЗДАНА")
    print("=" * 60)
    print(f"  📊 Всего чанков: {len(texts)}")
    print(f"  📁 Исходных файлов: {len(file_paths)}")
    print(f"  💾 Размер базы: {sum(f.stat().st_size for f in DB_DIR.iterdir()) / 1024:.1f} KB")
    print("=" * 60 + "\n")

    return db