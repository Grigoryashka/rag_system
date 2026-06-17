import os
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
# Если поставил новый пакет: from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import requests

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


def generate_rag_answer(query: str):
    db = load_vector_store()
    if not db:
        return "Ошибка: База знаний не загружена."

    # 1. Поиск (k=1 для максимальной скорости)
    docs = db.similarity_search(query, k=3)
    context_text = "\n\n".join([d.page_content for d in docs])

    if not context_text.strip():
        return "Ничего не найдено."

    prompt = f"""Ты ассистент по ML-библиотекам. 
                1. Сначала проверь КОНТЕКСТ ниже. Если в нём есть ответ, используй его.
                2. Если контекст неполный или отсутствует, ответь кратко из своих знаний, но отметь: "(На основе общих знаний)".
                3. Отвечай четко, без воды.
                
                Контекст: {context_text}
                Вопрос: {query}
                Ответ:"""

    try:
        # 2. Прямой вызов Ollama с жесткими лимитами
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:3b",  # Или твоя модель
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 500,  # Очень короткий ответ = очень быстро
                    "top_p": 0.9,
                    "num_ctx": 2048
                }
            },
            timeout=90
        )
        return response.json().get("response", "Нет ответа")
    except Exception as e:
        return f"Ошибка API: {e}"