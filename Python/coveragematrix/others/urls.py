from django.urls import path
from coveragematrix import views

app_name = 'coveragematrix'
urlpatterns = [
    path('', views.index, name='index'),
    path('new/', views.new_plan, name='new_plan'),
    path('<int:plan_id>/', views.plan_detail, name='plan_detail'),
    path('<int:plan_id>/results/', views.plan_results, name='plan_results'),
    path('<int:plan_id>/cancel/', views.cancel_plan, name='cancel_plan'),
    path('tasks/<int:task_id>/cancel/', views.cancel_task, name='cancel_task')
]
