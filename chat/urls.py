from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/search/', views.api_search, name='api_search'),
    path('api/rebuild/', views.admin_rebuild, name='admin_rebuild'),
    path('api/run-eval-api/', views.run_eval_api, name='run_eval_api'),
    path('api/evaluate-query/', views.evaluate_current_query, name='evaluate_current_query'),
    path('api/clear-cache/', views.clear_cache, name='clear_cache'),
    path('api/metrics/', views.show_metrics, name='show_metrics'),
    path('api/run-ragas-eval/', views.run_ragas_eval_api, name='run_ragas_eval'),
]