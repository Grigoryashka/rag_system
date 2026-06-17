import os
import json
import re
import pandas as pd
from datasets import Dataset
from langchain_ollama import ChatOllama, OllamaEmbeddings
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from .services import generate_rag_answer



BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EVAL_MODEL_NAME = "llama3.2:3b"


def get_eval_llm():
    return ChatOllama(
        model=EVAL_MODEL_NAME,
        temperature=0,
        base_url="http://localhost:11434",
        format="json"  # <-- ВАЖНО: просим модель отдавать только JSON
    )


def get_eval_embeddings():
    return OllamaEmbeddings(model=EVAL_MODEL_NAME, base_url="http://localhost:11434")


def create_test_dataset():
    """
    Тестовый датасет с ПРЕДВАРИТЕЛЬНО ЗАПОЛНЕННЫМИ answer и contexts.
    Это важно: RAGAS не будет сам генерировать ответы, он будет оценивать готовые.
    """
    # Сначала "прогони" свои вопросы через основной RAG-пайплайн,
    # чтобы получить реальные answer и contexts, затем вставь их сюда.
    test_data = [
        {
            "question": "Как создать DataFrame в pandas?",
            "answer": "Используйте pd.DataFrame() с словарем данных.",  # <-- Заполни реальным ответом твоей системы
            "contexts": [
                "DataFrame — это двумерная структура данных. Создание: pd.DataFrame({'A': [1, 2]})"
            ],
            "ground_truth": "Для создания DataFrame используйте конструктор pd.DataFrame()."
        },
        {
            "question": "Что такое n_estimators в RandomForest?",
            "answer": "Это количество деревьев в лесу.",
            "contexts": [
                "n_estimators: The number of trees in the forest. Default is 100."
            ],
            "ground_truth": "Параметр n_estimators задает количество деревьев в ансамбле Random Forest."
        },
    ]
    return Dataset.from_list(test_data)


# chat/evaluation.py - альтернативная функция
def simple_manual_eval():
    """
    Простая ручная оценка - возвращает список словарей.
    """
    test_cases = [
        {
            "question": "Как создать DataFrame?",
            "expected_keywords": ["pd.DataFrame", "DataFrame(", "pandas"],
        },
        {
            "question": "n_estimators в RandomForest",  # ✅ Уточнили!
            "expected_keywords": ["дерев", "количеств", "n_estimators", "RandomForest"],
        }
    ]

    results = []  # <-- Это обычный Python список
    for case in test_cases:
        print(f"🤔 Вопрос: {case['question']}")
        answer = generate_rag_answer(case["question"])
        print(f"✅ Ответ: {answer[:50]}...")

        score = sum(1 for kw in case["expected_keywords"] if kw.lower() in answer.lower())

        results.append({
            "question": case["question"],
            "score": f"{score}/{len(case['expected_keywords'])}",
            "answer": answer if len(answer) <= 100 else answer[:100] + "..."
        })

    print(f"\n📊 Результаты: {results}")
    return results  # <-- Возвращаем список, НЕ объект RAGAS


def run_evaluation():
    print("🔄 Запуск RAGAS оценки...")

    dataset = create_test_dataset()
    llm = get_eval_llm()
    embeddings = get_eval_embeddings()

    try:
        result = evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy],
            llm=llm,
            embeddings=embeddings,
        )

        # ✅ RAGAS возвращает объект, который конвертируется в pandas DataFrame
        df = result.to_pandas()

        # Извлекаем средние значения метрик
        metrics_dict = {
            "faithfulness": float(df["faithfulness"].mean()) if "faithfulness" in df.columns else 0.0,
            "answer_relevancy": float(df["answer_relevancy"].mean()) if "answer_relevancy" in df.columns else 0.0,
        }

        print("\n📊 Метрики:")
        for metric, score in metrics_dict.items():
            print(f"  • {metric}: {score:.3f}")

        df.to_csv(os.path.join(BASE_DIR, "ragas_results.csv"), index=False)
        print(f"💾 Сохранено в ragas_results.csv")

        return metrics_dict

    except Exception as e:
        print(f"❌ RAGAS evaluation failed: {e}")
        print("⚠️  Falling back to simple evaluation...")
        # Если RAGAS сломался, возвращаем простую оценку
        return simple_manual_eval()