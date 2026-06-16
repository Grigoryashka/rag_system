import os
import requests
from bs4 import BeautifulSoup
import time

# Создаем папку docs, если нет
os.makedirs("docs", exist_ok=True)

def fetch_and_clean(url, output_file, lang="en"):
    print(f"[*] Скачиваем и парсим: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # Удаляем скрипты, стили, навигацию - оставляем только контент
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Ищем основной блок контента (для Sphinx/Pandas/Sklearn обычно это div[class*="content"] или article)
        # Это эвристика, может потребоваться подстройка под конкретный сайт, но для примера берем весь текст body
        text = soup.get_text(separator='\n', strip=True)

        # Чистим от лишних пустых строк
        lines = [line for line in text.split('\n') if line.strip()]
        clean_text = '\n'.join(lines)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(clean_text)

        print(f"[+] Сохранено в {output_file} ({len(clean_text)} символов)")

    except Exception as e:
        print(f"[-] Ошибка с {url}: {e}")

if __name__ == "__main__":
    # 1. Английская документация (Pandas + Sklearn примеры)
    # Берем основные страницы, так как полная дока огромна
    urls_en = [
        ("https://pandas.pydata.org/docs/user_guide/10min.html", "docs/ml_docs_en.txt"),
        ("https://scikit-learn.org/stable/modules/linear_model.html", "docs/ml_docs_en_temp.txt")
    ]

    # 2. Русская документация (Pandas перевод + Habr/Docs статьи)
    # Официальной полной русской доки sklearn нет, берем лучшие доступные источники
    urls_ru = [
        ("https://pandas.pydata.org/docs/getting_started/intro_tutorials/01_table_oriented.html", "docs/ml_docs_ru_temp.txt"),
        # Для примера возьмем статью с Habr или аналогичный ресурс с хорошим обзором ML на русском
        # Так как прямые ссылки на русские доки часто битые, используем заглушку с реальным контентом ниже
    ]

    # Скачиваем EN
    full_text_en = ""
    for url, fname in urls_en:
        fetch_and_clean(url, fname)
        if os.path.exists(fname):
            with open(fname, 'r', encoding='utf-8') as f:
                full_text_en += f.read() + "\n\n--- NEW SECTION ---\n\n"
            os.remove(fname) # удаляем временный

    with open("docs/ml_docs_en.txt", "w", encoding="utf-8") as f:
        f.write(full_text_en)

    # Скачиваем RU (эмуляция качественного контента, так как парсить ру-сегмент сложнее из-за разрозненности)
    # В реальном проекте тут были бы ссылки на translate.yandex.ru или русскоязычные блоги
    # Для теста я запишу сюда качественный перевод ключевых концепций, чтобы ты видел работу RAG

    ru_content = """
    Pandas: Введение в таблицы данных
    DataFrame — это двумерная структура данных с метками. Представьте себе таблицу Excel или SQL.
    
    Создание DataFrame:
    import pandas as pd
    df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    
    Основные методы:
    - head(): показывает первые строки.
    - info(): выводит сводку по типам данных и пропускам.
    - describe(): статистика (среднее, мин, макс).
    
    Scikit-Learn: Линейные модели
    Линейная регрессия предсказывает целевую переменную как линейную комбинацию входных признаков.
    
    Пример использования RandomForest (Случайный лес):
    from sklearn.ensemble import RandomForestClassifier
    clf = RandomForestClassifier(n_estimators=100)
    clf.fit(X_train, y_train)
    
    Параметры:
    - n_estimators: количество деревьев в лесу.
    - max_depth: максимальная глубина дерева.
    
    Важность признаков (feature_importances_): позволяет понять, какие колонки больше всего влияют на прогноз.
    """

    with open("docs/ml_docs_ru.txt", "w", encoding="utf-8") as f:
        f.write(ru_content)

    print("\n[ГОТОВО] Файлы docs/ml_docs_en.txt и docs/ml_docs_ru.txt созданы.")
    print("Теперь запусти: python manage.py shell -> from chat.services import create_vector_store; create_vector_store()")