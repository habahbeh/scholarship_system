# في ملف finance/urls.py

from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    # الصفحة الرئيسية للمالية
    path('', views.finance_home, name='home'),

    # إدارة الميزانيات
    path('budgets/', views.budget_list, name='budget_list'),
    path('budgets/<int:budget_id>/', views.budget_detail, name='budget_detail'),
    path('applications/<int:application_id>/budget/create/', views.create_budget, name='create_budget'),
    path('budgets/<int:budget_id>/update/', views.update_budget, name='update_budget'),
    path('budgets/<int:budget_id>/delete/', views.delete_budget, name='delete_budget'),

    # إدارة المصروفات
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/<int:expense_id>/', views.expense_detail, name='expense_detail'),
    path('budgets/<int:budget_id>/expenses/create/', views.create_expense, name='create_expense'),
    path('expenses/<int:expense_id>/update/', views.update_expense, name='update_expense'),
    path('expenses/<int:expense_id>/delete/', views.delete_expense, name='delete_expense'),
    path('expenses/<int:expense_id>/approve/', views.approve_expense, name='approve_expense'),

    # إدارة فئات المصروفات
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.create_category, name='create_category'),
    path('categories/<int:category_id>/update/', views.update_category, name='update_category'),
    path('categories/<int:category_id>/delete/', views.delete_category, name='delete_category'),

    # إدارة تعديلات الميزانية
    path('budgets/<int:budget_id>/adjustments/', views.adjustment_list, name='adjustment_list'),
    path('adjustments/<int:adjustment_id>/', views.adjustment_detail, name='adjustment_detail'),
    path('budgets/<int:budget_id>/adjustments/create/', views.create_adjustment, name='create_adjustment'),
    path('adjustments/<int:adjustment_id>/approve/', views.approve_adjustment, name='approve_adjustment'),

    # التقارير المالية
    path('reports/', views.report_list, name='report_list'),
    path('reports/create/', views.create_report, name='create_report'),
    path('reports/<int:report_id>/', views.report_detail, name='report_detail'),
    path('reports/<int:report_id>/update/', views.update_report, name='update_report'),
    path('reports/<int:report_id>/delete/', views.delete_report, name='delete_report'),
    path('reports/<int:report_id>/export-pdf/', views.export_report_pdf, name='export_report_pdf'),
    path('reports/<int:report_id>/export-excel/', views.export_report_excel, name='export_report_excel'),

    # تقارير محددة مسبقًا
    path('reports/budget-summary/', views.budget_summary_report, name='budget_summary_report'),
    path('reports/expense-summary/', views.expense_summary_report, name='expense_summary_report'),
    path('reports/monthly-expenses/', views.monthly_expenses_report, name='monthly_expenses_report'),
    path('reports/category-expenses/', views.category_expenses_report, name='category_expenses_report'),

    # لوحة المعلومات المالية (Dashboard)
    path('dashboard/', views.finance_dashboard, name='dashboard'),

    # API للرسوم البيانية
    path('api/budget-summary/', views.api_budget_summary, name='api_budget_summary'),
    path('api/expense-categories/', views.api_expense_categories, name='api_expense_categories'),
    path('api/monthly-expenses/', views.api_monthly_expenses, name='api_monthly_expenses'),
    path('api/budget-status/', views.api_budget_status, name='api_budget_status'),

    # API endpoints for charts
    path('api/monthly-expenses/', views.api_monthly_expenses, name='api_monthly_expenses'),
    path('api/expense-categories/', views.api_expense_categories, name='api_expense_categories'),
    path('api/budget-status/', views.api_budget_status, name='api_budget_status'),

    # إضافة مسارات جديدة
    path('budgets/<int:budget_id>/add-year/', views.add_scholarship_year, name='add_scholarship_year'),
    path('budgets/<int:budget_id>/close-year/', views.close_current_year_open_new, name='close_current_year_open_new'),
    path('budgets/<int:budget_id>/costs-report/', views.scholarship_years_costs_report, name='scholarship_years_costs_report'),

]