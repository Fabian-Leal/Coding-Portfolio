from django.urls import path
from optimalmix import views

app_name = 'optimalmix'
urlpatterns = [
    path('', views.index, name='index'),
    path('new/', views.new_plan, name='new_plan'),
    path('<int:plan_id>/', views.plan_detail, name='plan_detail'),
    path('<int:plan_id>/task-<int:task_id>/', views.task_detail, name='task_detail'),
    path('<int:plan_id>/parameters/', views.plan_parameters, name='plan_parameters'),
    path('<int:plan_id>/cancel/', views.cancel_plan, name='cancel_plan'),
    path('tasks/<int:task_id>/cancel/', views.cancel_task, name='cancel_task')
]
