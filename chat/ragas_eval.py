"""
Модуль оценки качества RAG-системы
Использует:
- Лемматизацию (pymorphy2) для учёта склонений русского языка
- Косинусную схожесть эмбеддингов для семантической оценки
"""
import os
import re
import numpy as np
import pymorphy2
from sentence_transformers import SentenceTransformer
from .services import generate_rag_answer

# ==================== ГЛОБАЛЬНЫЕ ОБЪЕКТЫ ====================

_morph = pymorphy2.MorphAnalyzer()
_cosine_model = None


# ==================== ЛЕММАТИЗАЦИЯ ====================

def normalize_word(word: str) -> str:
    """
    Приводит слово к начальной форме (лемма)

    Args:
        word: Слово для нормализации

    Returns:
        Нормализованная форма слова
    """
    word = word.strip().lower()
    if not word:
        return word

    parsed = _morph.parse(word)
    if parsed:
        return parsed[0].normal_form
    return word


def check_keywords_in_answer(answer: str, keywords: list) -> bool:
    """
    Проверяет наличие ВСЕХ ключевых слов с учётом склонений

    Args:
        answer: Текст ответа
        keywords: Список ключевых слов

    Returns:
        True если ВСЕ ключевые слова найдены, False иначе
    """
    if not keywords:
        return True

    answer_lower = answer.lower()

    for keyword in keywords:
        keyword_lemma = normalize_word(keyword)

        found = False
        for word in answer_lower.split():
            # Убираем пунктуацию и спецсимволы
            word_clean = ''.join(c for c in word if c.isalpha() or c.isdigit())
            if word_clean:
                word_lemma = normalize_word(word_clean)
                if word_lemma == keyword_lemma:
                    found = True
                    break

        if not found:
            return False

    return True


def check_single_keyword(answer: str, keyword: str) -> bool:
    """
    Проверяет одно ключевое слово

    Args:
        answer: Текст ответа
        keyword: Ключевое слово

    Returns:
        True если найдено
    """
    return check_keywords_in_answer(answer, [keyword])


# ==================== КОСИНУСНАЯ СХОЖЕСТЬ ====================

def get_cosine_model():
    """Загружает модель эмбеддингов для косинусной схожести"""
    global _cosine_model
    if _cosine_model is None:
        print("⏳ Загрузка модели для косинусной оценки...")
        _cosine_model = SentenceTransformer(
            'paraphrase-multilingual-MiniLM-L12-v2',
            model_kwargs={'device': 'cpu'}
        )
        print("✅ Модель загружена")
    return _cosine_model


def cosine_similarity(text1: str, text2: str) -> float:
    """
    Вычисляет косинусную схожесть между двумя текстами

    Args:
        text1: Первый текст (обычно вопрос)
        text2: Второй текст (обычно ответ)

    Returns:
        Коэффициент схожести от -1 до 1
    """
    try:
        model = get_cosine_model()
        embeddings = model.encode([text1, text2], normalize_embeddings=True)
        similarity = float(np.dot(embeddings[0], embeddings[1]))
        return similarity
    except Exception as e:
        print(f"️ Ошибка вычисления косинусной схожести: {e}")
        return 0.0


# ==================== ТЕСТОВЫЕ КЕЙСЫ ====================

def get_test_cases():
    """
    Возвращает список тестовых вопросов для оценки

    Returns:
        Список словарей с вопросами и ожидаемыми ключевыми словами
    """
    return [
        {
            "question": "Как создать DataFrame?",
            "expected_keywords": ["создать", "DataFrame", "pandas"],
            "description": "Базовый вопрос по pandas"
        },
        {
            "question": "Что такое n_estimators в RandomForest?",
            "expected_keywords": ["дерев", "количеств", "n_estimators", "RandomForest"],
            "description": "Параметр модели Random Forest"
        },
        {
            "question": "Как создать нейросеть?",
            "expected_keywords": ["создать", "нейросет", "модель"],
            "description": "Создание нейронной сети"
        },
        {
            "question": "Что такое переобучение модели?",
            "expected_keywords": ["переобучен", "модель", "обучающ"],
            "description": "Проблема переобучения в ML"
        },
        {
            "question": "Как работает алгоритм backpropagation?",
            "expected_keywords": ["backpropagation", "градиент", "ошибк"],
            "description": "Алгоритм обратного распространения ошибки"
        }
    ]


# ==================== ОСНОВНАЯ ФУНКЦИЯ ОЦЕНКИ ====================

def run_ragas_evaluation():
    """
    Запуск полной оценки качества RAG-системы

    Для каждого тестового вопроса:
    1. Генерирует ответ через RAG
    2. Проверяет ключевые слова с лемматизацией
    3. Вычисляет косинусную схожесть вопрос-ответ
    4. Считает итоговый скор

    Returns:
        Словарь с результатами:
        - results: список результатов по каждому вопросу
        - avg_cosine: средняя косинусная схожесть
        - avg_score: средний итоговый скор
        - total_questions: количество протестированных вопросов
    """
    print("\n" + "=" * 60)
    print("🚀 ЗАПУСК ОЦЕНКИ КАЧЕСТВА RAG")
    print("=" * 60)

    test_cases = get_test_cases()
    results = []

    for i, case in enumerate(test_cases, 1):
        question = case["question"]
        keywords = case["expected_keywords"]
        description = case.get("description", "")

        print(f"\n[{i}/{len(test_cases)}] 🤔 Вопрос: {question}")
        print(f"   📝 Описание: {description}")

        # 1. Генерируем ответ через RAG
        try:
            answer = generate_rag_answer(question)
        except Exception as e:
            print(f"   ❌ Ошибка генерации ответа: {e}")
            answer = ""

        if not answer:
            print(f"   ️ Пустой ответ")
            results.append({
                "question": question,
                "description": description,
                "keywords_found": "0/0",
                "keywords_details": {kw: False for kw in keywords},
                "cosine_similarity": 0.0,
                "answer_length": 0,
                "total_score": 0.0,
                "answer": "Ошибка генерации ответа"
            })
            continue

        print(f"   ✅ Ответ: {answer[:80]}...")

        # 2. Проверяем ключевые слова с лемматизацией
        keywords_details = {}
        keywords_score = 0
        for kw in keywords:
            found = check_single_keyword(answer, kw)
            keywords_details[kw] = found
            if found:
                keywords_score += 1
                print(f"      ✅ {kw}")
            else:
                print(f"      ❌ {kw}")

        # 3. Косинусная схожесть вопрос-ответ
        cosine_sim = cosine_similarity(question, answer)
        print(f"   📐 Косинусная схожесть: {cosine_sim:.3f}")

        # 4. Итоговый скор (50% ключевые слова + 50% косинус)
        keyword_score_pct = (keywords_score / len(keywords) * 100) if keywords else 0
        cosine_score_pct = cosine_sim * 100
        total_score = (keyword_score_pct * 0.5) + (cosine_score_pct * 0.5)

        print(f"   🎯 Итоговый скор: {total_score:.1f}/100")

        results.append({
            "question": question,
            "description": description,
            "keywords_found": f"{keywords_score}/{len(keywords)}",
            "keywords_details": keywords_details,
            "cosine_similarity": round(cosine_sim, 3),
            "answer_length": len(answer),
            "total_score": round(total_score, 1),
            "answer": answer[:300] + "..." if len(answer) > 300 else answer
        })

    # Средние метрики
    avg_cosine = sum(r['cosine_similarity'] for r in results) / len(results) if results else 0
    avg_score = sum(r['total_score'] for r in results) / len(results) if results else 0

    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 60)
    print(f"  Протестировано вопросов: {len(results)}")
    print(f"  Средняя косинусная схожесть: {avg_cosine:.3f}")
    print(f"  Средний итоговый скор: {avg_score:.1f}/100")
    print("=" * 60 + "\n")

    return {
        'results': results,
        'avg_cosine': round(avg_cosine, 3),
        'avg_score': round(avg_score, 1),
        'total_questions': len(results)
    }


# ==================== ТОЧКА ВХОДА ====================

if __name__ == "__main__":
    """
    Для запуска из командной строки:
    python -m chat.ragas_eval
    """
    result = run_ragas_evaluation()

    print(f"\n📈 Сводка:")
    print(f"  Всего вопросов: {result['total_questions']}")
    print(f"  Средняя косинусная схожесть: {result['avg_cosine']}")
    print(f"  Средний скор: {result['avg_score']}/100")

    print(f"\n Детали:")
    for r in result['results']:
        status = "✅" if r['total_score'] >= 70 else "️" if r['total_score'] >= 50 else "❌"
        print(f"  {status} {r['question']}: {r['total_score']}/100 (косинус: {r['cosine_similarity']})")