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


    # روابط إدارة الطلبات الجديدة
    path('admin/applications/', views.admin_applications_list, name='admin_applications_list'),
    path('admin/applications/<int:application_id>/check-requirements/', views.check_requirements,
         name='check_requirements'),
    path('admin/applications/<int:application_id>/higher-committee-approval/', views.higher_committee_approval,
         name='higher_committee_approval'),
    path('admin/applications/<int:application_id>/faculty-council-approval/', views.faculty_council_approval,
         name='faculty_council_approval'),
    path('admin/applications/<int:application_id>/president-approval/', views.president_approval,
         name='president_approval'),

    # روابط التقارير
    path('admin/reports/requirements/', views.requirements_report, name='requirements_report'),
    path('admin/reports/higher-committee/', views.higher_committee_report, name='higher_committee_report'),
    path('admin/reports/faculty-council/', views.faculty_council_report, name='faculty_council_report'),
    path('admin/reports/president/', views.president_report, name='president_report'),
    path('admin/reports/application/<int:application_id>/', views.application_full_report,
         name='application_full_report'),
]