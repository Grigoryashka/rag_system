from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .services import generate_rag_answer, create_vector_store


def index(request):
    return render(request, 'chat/index.html')


def api_search(request):
    if request.method == "POST":
        query = request.POST.get('query', '')
        if not query:
            return JsonResponse({"error": "Пустой запрос"}, status=400)

        answer_text = generate_rag_answer(query)
        return render(request, 'chat/_results.html', {
            'results': [{"content": answer_text, "source": "AI Generated"}],
            'query': query
        })

    return JsonResponse({"error": "Method not allowed"}, status=405)


def admin_rebuild(request):
    try:
        create_vector_store()
        return JsonResponse({"status": "success", "message": "База пересобрана"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@require_POST
def run_eval_api(request):
    """Запускает ПРОСТУЮ оценку для дашборда (без RAGAS)"""
    try:
        from .evaluation import simple_manual_eval

        # Вызываем ТОЛЬКО простую ручную оценку
        results = simple_manual_eval()

        return JsonResponse({"status": "success", "data": results})

    except Exception as e:
        import traceback
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)


@require_POST
def evaluate_current_query(request):
    """Оценивает текущий запрос пользователя"""
    import json
    from .services import generate_rag_answer

    data = json.loads(request.body)
    query = data.get('query', '').strip()

    if not query:
        return JsonResponse({"error": "Пустой запрос"}, status=400)

    # Генерируем ответ
    answer = generate_rag_answer(query)

    # Простая эвристика: ищем ключевые слова из вопроса в ответе
    # Исключаем короткие слова и служебные части речи
    stop_words = {'как', 'что', 'где', 'когда', 'почему', 'зачем', 'кто',
                  'для', 'без', 'под', 'над', 'при', 'через', 'после',
                  'перед', 'между', 'около', 'во', 'в', 'на', 'у', 'к', 'по', 'с', 'со'}

    # Извлекаем значимые слова из вопроса (длиннее 3 букв)
    keywords = [w.lower().strip('.,!?;:') for w in query.split()
                if len(w) > 3 and w.lower() not in stop_words]

    # Считаем, сколько ключевых слов найдено в ответе
    found_keywords = [kw for kw in keywords if kw in answer.lower()]
    score = len(found_keywords)
    total = len(keywords)

    return JsonResponse({
        "query": query,
        "answer": answer,
        "keywords": keywords,
        "found_keywords": found_keywords,
        "score": f"{score}/{total}",
        "percent": (score / total * 100) if total > 0 else 0
    })