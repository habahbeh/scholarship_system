from django.urls import path
from . import views

app_name = 'evaluation'

urlpatterns = [
    # لجان التقييم
    path('committees/', views.committee_list, name='committee_list'),
    path('committees/<int:pk>/', views.committee_detail, name='committee_detail'),
    path('committees/create/', views.committee_create, name='committee_create'),
    path('committees/<int:pk>/edit/', views.committee_edit, name='committee_edit'),
    path('committees/<int:pk>/delete/', views.committee_delete, name='committee_delete'),
    path('committees/<int:pk>/add-member/', views.committee_add_member, name='committee_add_member'),
    path('committees/<int:pk>/remove-member/<int:user_id>/', views.committee_remove_member,
         name='committee_remove_member'),

    # معايير التقييم
    path('criteria/', views.criterion_list, name='criterion_list'),
    path('criteria/create/', views.criterion_create, name='criterion_create'),
    path('criteria/<int:pk>/edit/', views.criterion_edit, name='criterion_edit'),
    path('criteria/<int:pk>/delete/', views.criterion_delete, name='criterion_delete'),

    # جولات التقييم
    path('rounds/', views.round_list, name='round_list'),
    path('rounds/<int:pk>/', views.round_detail, name='round_detail'),
    path('rounds/create/', views.round_create, name='round_create'),
    path('rounds/<int:pk>/edit/', views.round_edit, name='round_edit'),
    path('rounds/<int:pk>/delete/', views.round_delete, name='round_delete'),
    path('rounds/<int:pk>/assign-applications/', views.round_assign_applications, name='round_assign_applications'),

    # تقييم الطلبات
    path('evaluator-dashboard/', views.evaluator_dashboard, name='evaluator_dashboard'),
    path('committee-dashboard/', views.committee_dashboard, name='committee_dashboard'),
    path('evaluate-application/<int:pk>/', views.evaluate_application, name='evaluate_application'),
    path('evaluations/', views.evaluation_list, name='evaluation_list'),
    path('evaluations/<int:pk>/', views.evaluation_detail, name='evaluation_detail'),

    # التصويت
    path('vote/<int:application_id>/', views.vote_create, name='vote_create'),
    path('votes/', views.vote_list, name='vote_list'),
    # إضافة مسار جديد للطلبات المتاحة للتصويت
    path('applications-for-voting/', views.applications_for_voting, name='applications_for_voting'),

    # التوصيات
    path('recommendations/', views.recommendation_list, name='recommendation_list'),
    path('recommendations/<int:pk>/', views.recommendation_detail, name='recommendation_detail'),
    path('recommend/<int:application_id>/', views.recommendation_create, name='recommendation_create'),
]