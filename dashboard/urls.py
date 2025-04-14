from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # لوحات التحكم الرئيسية
    path('', views.index, name='index'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('faculty/', views.faculty_dashboard, name='faculty_dashboard'),

    # الإحصائيات والتقارير
    path('application-stats/', views.application_stats, name='application_stats'),
    path('evaluation-stats/', views.evaluation_stats, name='evaluation_stats'),
    path('scholarship-stats/', views.scholarship_stats, name='scholarship_stats'),

    # بيانات لوحة التحكم (AJAX)
    path('api/application-statuses/', views.api_application_statuses, name='api_application_statuses'),
    path('api/scholarships-count/', views.api_scholarships_count, name='api_scholarships_count'),
    path('api/evaluations-progress/', views.api_evaluations_progress, name='api_evaluations_progress'),
    path('api/monthly-applications/', views.api_monthly_applications, name='api_monthly_applications'),
]