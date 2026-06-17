from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .services import generate_rag_answer, create_vector_store
from .vector_store_cache import create_vector_store, reset_cache
from .cache import answers_cache
from .evaluation import simple_manual_eval


def index(request):
    return render(request, 'chat/index.html')


@require_POST
def api_search(request):
    query = request.POST.get('query', '').strip()
    if not query:
        return JsonResponse({"error": "Пустой запрос"}, status=400)

    answer = generate_rag_answer(query)

    return render(request, 'chat/_results.html', {
        'results': [{"content": answer, "source": "AI Generated"}],
        'query': query
    })


@require_POST
def admin_rebuild(request):
    try:
        reset_cache()  # Сбрасываем кэш FAISS
        answers_cache.clear()  # Очищаем кэш ответов
        create_vector_store()
        return JsonResponse({"status": "success", "message": "База пересобрана"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@require_POST
def run_eval_api(request):
    try:
        results = simple_manual_eval()
        return JsonResponse({"status": "success", "data": results})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@require_POST
def evaluate_current_query(request):
    import json
    from .services import generate_rag_answer

    data = json.loads(request.body)
    query = data.get('query', '').strip()

    if not query:
        return JsonResponse({"error": "Пустой запрос"}, status=400)

    answer = generate_rag_answer(query)

    # Простая эвристика оценки
    stop_words = {'как', 'что', 'где', 'когда', 'почему', 'зачем', 'кто',
                  'для', 'без', 'под', 'над', 'при', 'через', 'после',
                  'перед', 'между', 'около', 'во', 'в', 'на', 'у', 'к', 'по', 'с', 'со'}

    keywords = [w.lower().strip('.,!?;:') for w in query.split()
                if len(w) > 3 and w.lower() not in stop_words]

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


@require_POST
def clear_cache(request):
    """Очищает кэш ответов"""
    try:
        answers_cache.clear()
        return JsonResponse({"status": "success", "message": "Кэш очищен"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

