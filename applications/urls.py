from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    # طلبات المستخدم
    path('apply/<int:scholarship_id>/', views.apply, name='apply'),
    path('my-applications/', views.my_applications, name='my_applications'),
    path('application/<int:application_id>/', views.application_detail, name='application_detail'),
    path('application/<int:application_id>/update/', views.update_application, name='update_application'),
    path('application/<int:application_id>/documents/', views.application_documents, name='application_documents'),
    path('document/<int:document_id>/delete/', views.delete_document, name='delete_document'),

    # إدارة الطلبات (للمشرفين)
    path('admin/applications/', views.admin_applications, name='admin_applications'),
    path('application/<int:application_id>/change-status/', views.change_status, name='change_status'),
    path('application/<int:application_id>/delete/', views.delete_application, name='delete_application'),
]