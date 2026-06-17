"""
Кэширование FAISS базы и эмбеддингов в памяти
"""
import os
from pathlib import Path
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "db"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Глобальные переменные для кэширования
_embeddings = None
_vector_db = None


def get_embeddings():
    """
    Возвращает модель эмбеддингов (загружается один раз)
    """
    global _embeddings
    if _embeddings is None:
        print("⏳ Загрузка модели эмбеддингов в память...")
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        print("✅ Модель эмбеддингов загружена")
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
    Создаёт новую FAISS базу из документов
    """
    from langchain_community.document_loaders import DirectoryLoader, TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    DOCS_DIR = BASE_DIR / "docs"

    if not DOCS_DIR.exists():
        raise FileNotFoundError(f"Папка {DOCS_DIR} не найдена.")

    print("📚 Загрузка документов...")
    loader = DirectoryLoader(
        str(DOCS_DIR),
        glob="**/*.txt",
        loader_cls=lambda path: TextLoader(path, encoding="utf-8")
    )
    documents = loader.load()

    print("️ Разбиение на чанки...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    texts = text_splitter.split_documents(documents)

    print("🔢 Создание эмбеддингов...")
    embeddings = get_embeddings()
    db = FAISS.from_documents(texts, embeddings)

    print("💾 Сохранение базы...")
    DB_DIR.mkdir(exist_ok=True)
    db.save_local(str(DB_DIR))

    # Обновляем кэш
    global _vector_db
    _vector_db = db

    print(f"✅ База создана и сохранена в {DB_DIR}")
    return db
