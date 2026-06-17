from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/search/', views.api_search, name='api_search'),
    path('api/rebuild/', views.admin_rebuild, name='admin_rebuild'),
    path('api/run-eval-api/', views.run_eval_api, name='run_eval_api'),
    path('api/evaluate-query/', views.evaluate_current_query, name='evaluate_current_query'),
]