from django.urls import path
from . import views

app_name = 'announcements'

urlpatterns = [
    # فرص الابتعاث
    path('scholarships/', views.scholarship_list, name='scholarship_list'),
    path('scholarships/<int:pk>/', views.scholarship_detail, name='scholarship_detail'),
    path('scholarships/create/', views.scholarship_create, name='scholarship_create'),
    path('scholarships/<int:pk>/edit/', views.scholarship_edit, name='scholarship_edit'),
    path('scholarships/<int:pk>/delete/', views.scholarship_delete, name='scholarship_delete'),

    # الإعلانات
    path('announcements/', views.announcement_list, name='announcement_list'),
    path('announcements/<int:pk>/', views.announcement_detail, name='announcement_detail'),
    path('announcements/create/', views.announcement_create, name='announcement_create'),
    path('announcements/<int:pk>/edit/', views.announcement_edit, name='announcement_edit'),
    path('announcements/<int:pk>/delete/', views.announcement_delete, name='announcement_delete'),

    # أنواع الابتعاث
    path('scholarship-types/create/', views.scholarship_type_create, name='scholarship_type_create'),

    # لوحة التحكم
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
]