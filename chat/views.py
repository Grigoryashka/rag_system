from django.shortcuts import render
from django.http import JsonResponse
from .services import generate_rag_answer, create_vector_store

def index(request):
    return render(request, 'chat/index.html')

def api_search(request):
    if request.method == "POST":
        query = request.POST.get('query', '')
        if not query:
            return JsonResponse({"error": "Пустой запрос"}, status=400)

        # Вызываем умную функцию вместо простого поиска
        answer_text = generate_rag_answer(query)

        # Возвращаем HTML с ответом
        # Мы используем простой рендер, чтобы сохранить стиль
        return render(request, 'chat/_results.html', {'results': [{"content": answer_text, "source": "AI Generated"}], 'query': query})

    return JsonResponse({"error": "Method not allowed"}, status=405)

def admin_rebuild(request):
    try:
        create_vector_store()
        return JsonResponse({"status": "success", "message": "База пересобрана"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)