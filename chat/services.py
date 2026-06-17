import os
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
# Если поставил новый пакет: from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import requests
from .vector_store_cache import load_vector_store, create_vector_store
from .cache import answers_cache
import re


# Глобальная переменная для хранения базы в памяти
_vector_db = None
_embeddings = None

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = BASE_DIR / "rag_core/docs"
DB_DIR = BASE_DIR / "rag_core/db"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # Или путь к локальной папке


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        print("Загрузка модели эмбеддингов в память...")
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    return _embeddings


def load_vector_store():
    global _vector_db
    if _vector_db is None:
        if not DB_DIR.exists():
            return None
        try:
            embeddings = get_embeddings()  # Берем из кэша
            _vector_db = FAISS.load_local(str(DB_DIR), embeddings, allow_dangerous_deserialization=True)
            print("База FAISS загружена в память.")
        except Exception as e:
            print(f"Ошибка загрузки базы: {e}")
            return None
    return _vector_db


def create_vector_store():
    global _vector_db
    _vector_db = None  # Сброс кэша при пересоздании

    if not DOCS_DIR.exists():
        raise FileNotFoundError(f"Папка {DOCS_DIR} не найдена.")

    loader = DirectoryLoader(str(DOCS_DIR), glob="**/*.txt", loader_cls=lambda path: TextLoader(path, encoding="utf-8"))
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = text_splitter.split_documents(documents)

    embeddings = get_embeddings()
    db = FAISS.from_documents(texts, embeddings)

    DB_DIR.mkdir(exist_ok=True)
    db.save_local(str(DB_DIR))
    _vector_db = db  # Сохраняем в глобальную переменную сразу
    print(f"[УСПЕХ] База создана и сохранена в {DB_DIR}")


def generate_rag_answer(query: str) -> str:
    """
    Генерирует ответ на вопрос через RAG с кэшированием
    """
    # 1. Проверяем кэш
    cached_answer = answers_cache.get(query)
    if cached_answer:
        print(f" Ответ найден в кэше: {query[:50]}...")
        return cached_answer

    # 2. Загружаем базу (из кэша в памяти)
    db = load_vector_store()
    if not db:
        return "Ошибка: База знаний не загружена."

    # 3. Поиск контекста
    docs = db.similarity_search(query, k=6)

    # 👇 ДОБАВЬ ЭТО ДЛЯ ОТЛАДКИ:
    print(f"\n🔍 Запрос: {query}")
    print(f"📄 Найдено документов: {len(docs)}")
    for i, doc in enumerate(docs):
        print(f"📝 Контекст {i+1}:\n{doc.page_content[:200]}...\n")
    # 👆 КОНЕЦ ОТЛАДКИ

    context_text = "\n\n".join([d.page_content for d in docs])

    if not context_text.strip():
        print("⚠️ КОНТЕКСТ ПУСТОЙ!")
        return "Информация не найдена в документации."

    # 4. Формируем промпт
    prompt = f"""Ты эксперт по Machine Learning.
                1. Прочитай КОНТЕКСТ и ответь на вопрос.
                2. ВАЖНО: Названия библиотек и функций пиши ТОЛЬКО ЛАТИНИЦЕЙ: pandas, numpy, sklearn, TensorFlow, RandomForest, DataFrame, n_estimators.
                3. Не смешивай кириллицу и латиницу в одном слове.
                4. Отвечай четко и по делу.
            
                Контекст: {context_text}
            
                Вопрос: {query}
            
                Ответ:"""

    # 5. Запрос к Ollama
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 700,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1,
                    "num_ctx": 2048
                }
            },
            timeout=90
        )
        response.raise_for_status()
        result = response.json()
        answer = result.get("response", "Нет ответа от модели")
        answer = clean_answer(answer)  #
        answers_cache.set(query, answer)
        return answer

    except requests.exceptions.Timeout:
        return "Превышено время ожидания ответа."
    except Exception as e:
        return f"Ошибка API: {str(e)}"


def clean_answer(answer: str) -> str:
    """Чистит смешанные кириллица-латиница слова"""
    # Словарь исправлений
    fixes = {
        r'[ПпРр]andas': 'pandas',
        r'[НнHh]umpy': 'numpy',
        r'[СсСс]klearn': 'sklearn',
        r'[ТтTt]ensor[Ff]low': 'TensorFlow',
        r'[КкKk]eras': 'Keras',
        r'[ДдDd]ata[Ff]rame': 'DataFrame',
        r'[НнNn]_estimators': 'n_estimators',
        r'[РрRr]andom[Ff]orest': 'RandomForest',
    }

    cleaned = answer
    for pattern, replacement in fixes.items():
        cleaned = re.sub(pattern, replacement, cleaned)

    return cleaned
