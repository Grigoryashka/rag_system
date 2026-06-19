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
import time
import psutil
from dataclasses import dataclass


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


# Метрики поиска
@dataclass
class SearchMetrics:
    query: str = ""
    search_time_ms: float = 0
    num_docs_found: int = 0
    llm_time_ms: float = 0
    total_time_ms: float = 0
    memory_mb: float = 0


# Глобальный лог метрик
_metrics_log = []


def get_metrics_log():
    """Получить лог всех метрик"""
    return _metrics_log


def log_search_metrics(query: str, search_time: float, num_docs: int, llm_time: float):
    """Логирование метрик поиска"""
    metrics = SearchMetrics(
        query=query[:50],
        search_time_ms=search_time * 1000,
        num_docs_found=num_docs,
        llm_time_ms=llm_time * 1000,
        total_time_ms=(search_time + llm_time) * 1000,
        memory_mb=psutil.Process().memory_info().rss / 1024 / 1024
    )
    _metrics_log.append(metrics)

    print(f"\n📊 МЕТРИКИ ПОИСКА:")
    print(f"  🔎 Запрос: {query[:50]}...")
    print(f"  ⏱️  Поиск документов: {metrics.search_time_ms:.0f} мс")
    print(f"  📄 Найдено чанков: {num_docs}")
    print(f"  🤖 Генерация LLM: {metrics.llm_time_ms:.0f} мс")
    print(f"  ⏳ Общее время: {metrics.total_time_ms:.0f} мс")
    print(f"  💾 Память: {metrics.memory_mb:.1f} MB")


def generate_rag_answer(query: str) -> str:
    """
    Генерирует ответ на вопрос через RAG с кэшированием
    """
    # 1. Проверяем кэш
    cached_answer = answers_cache.get(query)
    if cached_answer:
        print(f"✅ Ответ найден в кэше: {query[:50]}...")
        return cached_answer

    # 2. Загружаем базу (из кэша в памяти)
    db = load_vector_store()
    if not db:
        return "Ошибка: База знаний не загружена."

    # 3. Поиск контекста
    search_start = time.time()
    docs = db.similarity_search(query, k=6)
    search_time = time.time() - search_start

    # Отладка
    print(f"\n🔍 Запрос: {query}")
    print(f"📄 Найдено документов: {len(docs)}")
    for i, doc in enumerate(docs):
        print(f"📝 Контекст {i + 1}:\n{doc.page_content[:200]}...\n")

    context_text = "\n\n".join([d.page_content for d in docs])

    if not context_text.strip():
        print("⚠️ КОНТЕКСТ ПУСТОЙ!")
        return "Информация не найдена в документации."

    # 4. Формируем промпт
    prompt = f"""Ты эксперт по машинному обучению.

    Вопрос: {query}

    Контекст из документации:
    {context_text}

    Дай понятный ответ на русском с примерами кода.
    Если в контексте нет информации — скажи об этом.

    Ответ:"""

    # 5. Запрос к Ollama + замер времени
    try:
        llm_start = time.time()  # 👈 Засекаем время LLM

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5:3b",
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

        llm_time = time.time() - llm_start  # 👈 Засекаем конец LLM

        result = response.json()
        answer = result.get("response", "Нет ответа от модели")
        answer = clean_answer(answer)

        # 👇 ЛОГИРУЕМ МЕТРИКИ
        log_search_metrics(query, search_time, len(docs), llm_time)

        answers_cache.set(query, answer)
        return answer

    except requests.exceptions.Timeout:
        return "Превышено время ожидания ответа."
    except Exception as e:
        return f"Ошибка API: {str(e)}"


def fix_hybrid_words(text: str) -> str:
    """
    Исправляет смешанные кириллица-латиница слова
    """
    # Словарь правильных названий
    correct_names = {
        'pandas': r'[pр][аa][nн][dд][аa][sс]',
        'numpy': r'[nн][uю][mм][pр][yу]',
        'sklearn': r'[sс][kк][lл][еe][аa][rр][nн]',
        'DataFrame': r'[dд][аa][tт][аa][fф][rр][аa][mм][еe]',
        'Series': r'[sс][еe][rр][iи][еe][sс]',
        'TensorFlow': r'[tт][еe][nн][sс][оo][rр][fф][lл][оo][wв]',
        'RandomForest': r'[rр][аa][nн][dд][оo][mм][fф][оo][rр][еe][sс][tт]',
        'fit': r'[fф][iи][tт]',
        'predict': r'[pр][rр][еe][dд][iи][cс][tт]',
        'transform': r'[tт][rр][аa][nн][sс][fф][оo][rр][mм]',
    }

    fixed_text = text

    # Ищем гибриды и заменяем на правильные названия
    for correct, pattern in correct_names.items():
        fixed_text = re.sub(pattern, correct, fixed_text, flags=re.IGNORECASE)

    # Исправляем русские слова с латинскими буквами
    # Например: "работать" → "работать"
    common_words = {
        'работать': r'[rр][аa][бб][оo][tт][аa][tт]ь',
        'оператор': r'[оo][пp][еe][rр][аa][tт][оo][rр]',
        'функция': r'[fф][uю][nн][kк][цц][иi][яя]',
        'библиотека': r'[бб][иi][бб][lл][иi][оo][tт][еe][kк][аa]',
    }

    for correct, pattern in common_words.items():
        fixed_text = re.sub(pattern, correct, fixed_text, flags=re.IGNORECASE)

    return fixed_text


def clean_answer(answer: str) -> str:
    """Исправляет типичные ошибки маленьких моделей"""
    import re

    # 1. Исправляем смешанные слова
    fixes = {
        r'вMachine': 'в Machine',
        r'в sklearn': 'в sklearn',
        r'В general': 'В целом',
        r'в general': 'в целом',
        r'к overfittingу': 'к переобучению',
        r'в cFOREсте': 'в RandomForest',
        r'bforest': 'forest',
    }

    for wrong, correct in fixes.items():
        answer = re.sub(wrong, correct, answer, flags=re.IGNORECASE)

    # 2. Убираем мета-объяснения про алфавиты
    lines = answer.split('\n')
    filtered = []
    for line in lines:
        if 'латиниц' in line.lower() and 'кириллиц' in line.lower():
            continue
        if 'смешанн' in line.lower() and 'букв' in line.lower():
            continue
        filtered.append(line)

    answer = '\n'.join(filtered)

    # 3. Убираем лишние пробелы
    answer = re.sub(r' {2,}', ' ', answer)

    return answer.strip()


@dataclass
class SearchMetrics:
    """Метрики поиска"""
    query: str = ""
    search_time_ms: float = 0
    num_docs_found: int = 0
    llm_time_ms: float = 0
    total_time_ms: float = 0
    memory_mb: float = 0


# Глобальный счётчик метрик
_metrics_log = []


def get_metrics_log():
    """Получить лог метрик"""
    return _metrics_log


def log_search_metrics(query: str, search_time: float, num_docs: int, llm_time: float):
    """Логирование метрик поиска"""
    metrics = SearchMetrics(
        query=query[:50],
        search_time_ms=search_time * 1000,
        num_docs_found=num_docs,
        llm_time_ms=llm_time * 1000,
        total_time_ms=(search_time + llm_time) * 1000,
        memory_mb=psutil.Process().memory_info().rss / 1024 / 1024
    )
    _metrics_log.append(metrics)

    print(f"\n📊 МЕТРИКИ ПОИСКА:")
    print(f"  Запрос: {query[:50]}...")
    print(f"  Поиск документов: {metrics.search_time_ms:.0f} мс")
    print(f"  Найдено чанков: {num_docs}")
    print(f"  Генерация LLM: {metrics.llm_time_ms:.0f} мс")
    print(f"  Общее время: {metrics.total_time_ms:.0f} мс")
    print(f"  Память: {metrics.memory_mb:.1f} MB")
