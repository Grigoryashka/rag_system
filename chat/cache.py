"""
Кэширование ответов и FAISS базы
"""
import os
import json
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Пути для кэша
CACHE_DIR = BASE_DIR / "cache"
ANSWERS_CACHE_FILE = CACHE_DIR / "answers_cache.json"
FAISS_CACHE_FILE = CACHE_DIR / "faiss_cache.json"

# Создаём папку кэша, если нет
CACHE_DIR.mkdir(exist_ok=True)


class AnswersCache:
    """Кэш ответов на вопросы (JSON файл)"""

    def __init__(self, cache_file=ANSWERS_CACHE_FILE):
        self.cache_file = cache_file
        self._cache = self._load()

    def _load(self):
        """Загружает кэш из файла"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save(self):
        """Сохраняет кэш в файл"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)

    def _make_key(self, query: str) -> str:
        """Создаёт хэш-ключ для запроса"""
        # Нормализуем запрос: убираем пробелы, приводим к нижнему регистру
        normalized = query.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()

    def get(self, query: str):
        """Получает ответ из кэша"""
        key = self._make_key(query)
        return self._cache.get(key)

    def set(self, query: str, answer: str):
        """Сохраняет ответ в кэш"""
        key = self._make_key(query)
        self._cache[key] = answer
        self._save()

    def clear(self):
        """Очищает кэш"""
        self._cache = {}
        self._save()

    def stats(self) -> dict:
        """Статистика кэша"""
        return {
            "total_entries": len(self._cache),
            "file_size_mb": round(self.cache_file.stat().st_size / 1024 / 1024, 2) if self.cache_file.exists() else 0
        }


# Глобальный инстанс кэша (создаётся один раз)
answers_cache = AnswersCache()
