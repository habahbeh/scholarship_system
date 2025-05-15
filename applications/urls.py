"""
تعديلات على ملف urls.py لدعم الروابط الجديدة
"""
from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    # الروابط الحالية
    path('apply-tabs/<int:scholarship_id>/', views.apply_tabs, name='apply_tabs'),
    path('application/<int:application_id>/update-tabs/', views.update_application_tabs,
         name='update_application_tabs'),
    path('my-applications/', views.my_applications, name='my_applications'),
    path('application/<int:application_id>/', views.application_detail, name='application_detail'),
    path('application/<int:application_id>/documents/', views.application_documents, name='application_documents'),
    path('document/<int:document_id>/delete/', views.delete_document, name='delete_document'),
    path('manage/', views.admin_applications, name='admin_applications'),
    path('application/<int:application_id>/change-status/', views.change_status, name='change_status'),
    path('application/<int:application_id>/delete/', views.delete_application, name='delete_application'),
    path('applications/', views.admin_applications_list, name='admin_applications_list'),

    # تحديث روابط سير العمل
    path('applications/<int:application_id>/check-requirements/', views.check_requirements,
         name='check_requirements'),
    path('applications/<int:application_id>/higher-committee-approval/', views.higher_committee_approval,
         name='higher_committee_approval'),

    # إضافة رابط جديد لموافقة مجلس القسم
    path('applications/<int:application_id>/department-council-approval/', views.department_council_approval,
         name='department_council_approval'),

    path('applications/<int:application_id>/faculty-council-approval/', views.faculty_council_approval,
         name='faculty_council_approval'),

    # تغيير اسم الرابط من president-approval إلى deans-council-approval
    path('applications/<int:application_id>/deans-council-approval/', views.deans_council_approval,
         name='deans_council_approval'),

    # روابط التقارير
    path('reports/requirements/', views.requirements_report, name='requirements_report'),
    path('reports/higher-committee/', views.higher_committee_report, name='higher_committee_report'),

    # إضافة رابط جديد لتقرير مجلس القسم
    path('reports/department-council/', views.department_council_report, name='department_council_report'),

    path('reports/faculty-council/', views.faculty_council_report, name='faculty_council_report'),

    # تغيير اسم الرابط من president إلى deans-council
    path('reports/deans-council/', views.deans_council_report, name='deans_council_report'),

    path('reports/application/<int:application_id>/', views.application_full_report,
         name='application_full_report'),
]