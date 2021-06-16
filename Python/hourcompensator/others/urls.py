from django.urls import path
from hourcompensator import views

app_name = 'hourcompensator'
urlpatterns = [
    path('', views.index, name='index'),
    path('run/', views.run_plan, name='run_plan'),
    path('<int:plan_id>/', views.plan_detail, name='plan_detail'),
    path('<int:plan_id>/task-<int:task_id>/', views.task_detail, name='task_detail'),
    path('<int:plan_id>/results/', views.plan_results, name='plan_results'),
    #path('new/', views.new_plan, name='new_plan'),
]
