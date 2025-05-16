# في ملف finance/views.py

# إضافة هذه الاستيرادات
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Count, Q, F, Value
from django.db.models.functions import TruncMonth, Coalesce
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
import json
import weasyprint
import xlsxwriter
import io
import datetime
from decimal import Decimal
from itertools import groupby
from operator import attrgetter

from applications.models import Application, ApplicationStatus
from .models import (
    ScholarshipBudget, Expense, ExpenseCategory,
    FinancialReport, BudgetAdjustment, FinancialLog,
    FiscalYear, YearlyScholarshipCosts, ScholarshipSettings
)
from .forms import (
    ScholarshipBudgetForm, ExpenseForm, ExpenseCategoryForm,
    ExpenseApprovalForm, BudgetAdjustmentForm, BudgetAdjustmentApprovalForm,
    FinancialReportForm, DateRangeForm, BudgetFilterForm, ExpenseFilterForm,
    FiscalYearForm, YearlyScholarshipCostsForm, ScholarshipSettingsForm
)



@login_required
def finance_home(request):
    """الصفحة الرئيسية للشؤون المالية"""
    # الحصول على السنة المالية الحالية
    settings = ScholarshipSettings.objects.first()
    current_fiscal_year = None

    if settings and settings.current_fiscal_year:
        current_fiscal_year = settings.current_fiscal_year
    else:
        # في حالة عدم وجود إعدادات، استخدم أحدث سنة مالية مفتوحة
        current_fiscal_year = FiscalYear.objects.filter(status='open').order_by('-year').first()

    # إحصائيات عامة
    total_budgets = ScholarshipBudget.objects.count()
    active_budgets = ScholarshipBudget.objects.filter(status='active').count()
    total_expenses = Expense.objects.count()
    pending_expenses = Expense.objects.filter(status='pending').count()

    # إحصائيات السنة المالية الحالية
    fiscal_year_stats = {}
    if current_fiscal_year:
        fiscal_year_stats = {
            'year': current_fiscal_year.year,
            'total_budget': current_fiscal_year.total_budget,
            'spent_amount': current_fiscal_year.get_spent_amount(),
            'remaining_amount': current_fiscal_year.get_remaining_amount(),
            'spent_percentage': current_fiscal_year.get_spent_percentage(),
            'budgets_count': current_fiscal_year.scholarship_budgets.count(),
        }

    # إجمالي الميزانيات والمصروفات
    total_budget_amount = ScholarshipBudget.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    total_expense_amount = Expense.objects.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0

    # أحدث 5 ميزانيات
    latest_budgets = ScholarshipBudget.objects.all().order_by('-created_at')[:5]

    # أحدث 5 مصروفات
    latest_expenses = Expense.objects.all().order_by('-created_at')[:5]

    # السنوات المالية
    fiscal_years = FiscalYear.objects.all().order_by('-year')[:5]

    context = {
        'total_budgets': total_budgets,
        'active_budgets': active_budgets,
        'total_expenses': total_expenses,
        'pending_expenses': pending_expenses,
        'total_budget_amount': total_budget_amount,
        'total_expense_amount': total_expense_amount,
        'latest_budgets': latest_budgets,
        'latest_expenses': latest_expenses,
        'current_fiscal_year': current_fiscal_year,
        'fiscal_year_stats': fiscal_year_stats,
        'fiscal_years': fiscal_years,
    }
    return render(request, 'finance/home.html', context)


# ثم إضافة الوظائف الجديدة

@login_required
@permission_required('finance.view_fiscalyear', raise_exception=True)
def fiscal_year_list(request):
    """عرض قائمة السنوات المالية"""
    # استخدام نموذج الفلترة
    filter_form = FiscalYearFilterForm(request.GET)
    fiscal_years = FiscalYear.objects.all().order_by('-year')

    # تطبيق الفلاتر
    if filter_form.is_valid():
        data = filter_form.cleaned_data

        # فلتر حالة السنة المالية
        if data.get('status'):
            fiscal_years = fiscal_years.filter(status=data['status'])

        # فلتر السنة (مدى سنوات)
        if data.get('year_from'):
            fiscal_years = fiscal_years.filter(year__gte=data['year_from'])
        if data.get('year_to'):
            fiscal_years = fiscal_years.filter(year__lte=data['year_to'])

        # فلتر البحث
        if data.get('search'):
            search_query = data['search']
            fiscal_years = fiscal_years.filter(
                Q(description__icontains=search_query) |
                Q(year__icontains=search_query)
            )

    # إضافة البيانات المحسوبة
    for fiscal_year in fiscal_years:
        fiscal_year.spent_amount = fiscal_year.get_spent_amount()
        fiscal_year.remaining_amount = fiscal_year.get_remaining_amount()
        fiscal_year.spent_percentage = fiscal_year.get_spent_percentage()
        fiscal_year.budgets_count = fiscal_year.scholarship_budgets.count()

    # ترقيم الصفحات
    paginator = Paginator(fiscal_years, 10)  # 10 عناصر في كل صفحة
    page = request.GET.get('page')
    try:
        fiscal_years_page = paginator.page(page)
    except PageNotAnInteger:
        fiscal_years_page = paginator.page(1)
    except EmptyPage:
        fiscal_years_page = paginator.page(paginator.num_pages)

    context = {
        'fiscal_years': fiscal_years_page,
        'filter_form': filter_form,
    }
    return render(request, 'finance/fiscal_year_list.html', context)


@login_required
@permission_required('finance.view_fiscalyear', raise_exception=True)
def fiscal_year_detail(request, fiscal_year_id):
    """عرض تفاصيل السنة المالية"""
    fiscal_year = get_object_or_404(FiscalYear, id=fiscal_year_id)

    # البيانات المحسوبة
    fiscal_year.spent_amount = fiscal_year.get_spent_amount()
    fiscal_year.remaining_amount = fiscal_year.get_remaining_amount()
    fiscal_year.spent_percentage = fiscal_year.get_spent_percentage()

    # الميزانيات المرتبطة بهذه السنة المالية
    budgets = ScholarshipBudget.objects.filter(fiscal_year=fiscal_year)

    # المصروفات خلال هذه السنة المالية
    expenses = Expense.objects.filter(
        fiscal_year=fiscal_year
    ).order_by('-date')[:10]  # عرض آخر 10 مصروفات فقط

    # إجمالي المصروفات حسب الفئة
    expenses_by_category = Expense.objects.filter(
        fiscal_year=fiscal_year,
        status='approved'
    ).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')

    # سجل العمليات المرتبطة بهذه السنة المالية
    logs = FinancialLog.objects.filter(
        fiscal_year=fiscal_year
    ).order_by('-created_at')[:20]

    context = {
        'fiscal_year': fiscal_year,
        'budgets': budgets,
        'expenses': expenses,
        'expenses_by_category': expenses_by_category,
        'logs': logs,
    }
    return render(request, 'finance/fiscal_year_detail.html', context)


@login_required
@permission_required('finance.add_fiscalyear', raise_exception=True)
def create_fiscal_year(request):
    """إنشاء سنة مالية جديدة"""
    if request.method == 'POST':
        form = FiscalYearForm(request.POST)
        if form.is_valid():
            fiscal_year = form.save(commit=False)
            fiscal_year.created_by = request.user
            fiscal_year.save()

            # إنشاء سجل للعملية
            FinancialLog.objects.create(
                fiscal_year=fiscal_year,
                action_type='create',
                description=_("إنشاء سنة مالية جديدة"),
                created_by=request.user
            )

            # التحقق من تعيين السنة المالية الحالية في الإعدادات
            settings = ScholarshipSettings.objects.first()
            if not settings:
                settings = ScholarshipSettings.objects.create(
                    current_fiscal_year=fiscal_year,
                    created_by=request.user
                )
            elif not settings.current_fiscal_year:
                settings.current_fiscal_year = fiscal_year
                settings.save()

            messages.success(request, _("تم إنشاء السنة المالية بنجاح"))
            return redirect('finance:fiscal_year_detail', fiscal_year_id=fiscal_year.id)
    else:
        # القيم الافتراضية: السنة الحالية
        current_year = timezone.now().year
        current_date = timezone.now().date()
        form = FiscalYearForm(initial={
            'year': current_year,
            'start_date': datetime.date(current_year, 1, 1),
            'end_date': datetime.date(current_year, 12, 31),
        })

    context = {
        'form': form,
    }
    return render(request, 'finance/fiscal_year_form.html', context)


@login_required
@permission_required('finance.change_fiscalyear', raise_exception=True)
def update_fiscal_year(request, fiscal_year_id):
    """تحديث سنة مالية"""
    fiscal_year = get_object_or_404(FiscalYear, id=fiscal_year_id)

    # لا يمكن تعديل سنة مالية مغلقة
    if fiscal_year.status == 'closed':
        messages.error(request, _("لا يمكن تعديل سنة مالية مغلقة"))
        return redirect('finance:fiscal_year_detail', fiscal_year_id=fiscal_year.id)

    if request.method == 'POST':
        form = FiscalYearForm(request.POST, instance=fiscal_year)
        if form.is_valid():
            form.save()

            # إنشاء سجل للعملية
            FinancialLog.objects.create(
                fiscal_year=fiscal_year,
                action_type='update',
                description=_("تحديث سنة مالية"),
                created_by=request.user
            )

            messages.success(request, _("تم تحديث السنة المالية بنجاح"))
            return redirect('finance:fiscal_year_detail', fiscal_year_id=fiscal_year.id)
    else:
        form = FiscalYearForm(instance=fiscal_year)

    context = {
        'form': form,
        'fiscal_year': fiscal_year,
        'is_update': True,
    }
    return render(request, 'finance/fiscal_year_form.html', context)


@login_required
@permission_required('finance.change_fiscalyear', raise_exception=True)
def close_fiscal_year(request, fiscal_year_id):
    """إغلاق سنة مالية وفتح سنة جديدة"""
    fiscal_year = get_object_or_404(FiscalYear, id=fiscal_year_id)

    # لا يمكن إغلاق سنة مالية مغلقة بالفعل
    if fiscal_year.status == 'closed':
        messages.error(request, _("السنة المالية مغلقة بالفعل"))
        return redirect('finance:fiscal_year_detail', fiscal_year_id=fiscal_year.id)

    if request.method == 'POST':
        # استخدام دالة إغلاق السنة الحالية وفتح سنة جديدة
        new_fiscal_year = fiscal_year.close_and_create_new()

        if new_fiscal_year:
            # إنشاء سجل للعملية - إغلاق السنة الحالية
            FinancialLog.objects.create(
                fiscal_year=fiscal_year,
                action_type='close',
                description=_("إغلاق السنة المالية"),
                created_by=request.user
            )

            # إنشاء سجل للعملية - فتح سنة جديدة
            FinancialLog.objects.create(
                fiscal_year=new_fiscal_year,
                action_type='create',
                description=_("إنشاء سنة مالية جديدة بعد إغلاق السنة السابقة"),
                created_by=request.user
            )

            # تحديث السنة المالية الحالية في الإعدادات
            settings = ScholarshipSettings.objects.first()
            if settings and settings.current_fiscal_year == fiscal_year:
                settings.current_fiscal_year = new_fiscal_year
                settings.save()

            messages.success(request, _(f"تم إغلاق السنة المالية {fiscal_year.year} وفتح سنة مالية جديدة {new_fiscal_year.year} بنجاح"))
            return redirect('finance:fiscal_year_detail', fiscal_year_id=new_fiscal_year.id)
        else:
            messages.error(request, _("حدث خطأ أثناء إغلاق السنة المالية"))
            return redirect('finance:fiscal_year_detail', fiscal_year_id=fiscal_year.id)

    context = {
        'fiscal_year': fiscal_year,
    }
    return render(request, 'finance/fiscal_year_close_confirm.html', context)


@login_required
@permission_required('finance.view_fiscalyear', raise_exception=True)
def fiscal_year_report(request, fiscal_year_id):
    """تقرير السنة المالية"""
    fiscal_year = get_object_or_404(FiscalYear, id=fiscal_year_id)

    # البيانات المحسوبة
    spent_amount = fiscal_year.get_spent_amount()
    remaining_amount = fiscal_year.get_remaining_amount()
    spent_percentage = fiscal_year.get_spent_percentage()

    # الميزانيات المرتبطة بهذه السنة المالية
    budgets = ScholarshipBudget.objects.filter(fiscal_year=fiscal_year)

    # تجميع تكاليف الابتعاث لكل ميزانية
    scholarship_costs = []
    for budget in budgets:
        yearly_costs = YearlyScholarshipCosts.objects.filter(budget=budget, fiscal_year=fiscal_year)
        if yearly_costs.exists():
            scholarship_costs.append({
                'budget': budget,
                'applicant': budget.application.applicant.get_full_name(),
                'yearly_costs': yearly_costs,
                'total_costs': sum(cost.total_year_cost() for cost in yearly_costs),
            })

    # المصروفات في هذه السنة المالية حسب الفئة
    expenses_by_category = Expense.objects.filter(
        fiscal_year=fiscal_year,
        status='approved'
    ).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')

    # المصروفات الشهرية في هذه السنة المالية
    monthly_expenses = Expense.objects.filter(
        fiscal_year=fiscal_year,
        status='approved'
    ).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')

    # تحويل البيانات الشهرية إلى تنسيق مناسب
    months_data = []
    for month in range(1, 13):
        month_date = datetime.date(fiscal_year.year, month, 1)
        month_name = month_date.strftime('%B')  # اسم الشهر

        # البحث عن المصروفات في هذا الشهر
        month_expense = next(
            (item for item in monthly_expenses if item['month'].month == month),
            {'total': 0}
        )

        months_data.append({
            'month': month_name,
            'total': month_expense['total'],
        })

    context = {
        'fiscal_year': fiscal_year,
        'spent_amount': spent_amount,
        'remaining_amount': remaining_amount,
        'spent_percentage': spent_percentage,
        'budgets': budgets,
        'scholarship_costs': scholarship_costs,
        'expenses_by_category': expenses_by_category,
        'months_data': months_data,
    }
    return render(request, 'finance/reports/fiscal_year_report.html', context)


@login_required
@permission_required('finance.view_fiscalyear', raise_exception=True)
def fiscal_year_expenses(request, fiscal_year_id):
    """عرض مصروفات السنة المالية"""
    fiscal_year = get_object_or_404(FiscalYear, id=fiscal_year_id)

    # استخدام نموذج الفلترة
    filter_form = ExpenseFilterForm(request.GET)
    expenses = Expense.objects.filter(fiscal_year=fiscal_year).order_by('-date')

    # تطبيق الفلاتر
    if filter_form.is_valid():
        data = filter_form.cleaned_data

        # فلتر حالة المصروف
        if data.get('status'):
            expenses = expenses.filter(status=data['status'])

        # فلتر الفئة
        if data.get('category'):
            expenses = expenses.filter(category=data['category'])

        # فلتر التاريخ (مدى تاريخي)
        if data.get('start_date'):
            expenses = expenses.filter(date__gte=data['start_date'])
        if data.get('end_date'):
            expenses = expenses.filter(date__lte=data['end_date'])

        # فلتر المبلغ (مدى مالي)
        if data.get('min_amount'):
            expenses = expenses.filter(amount__gte=data['min_amount'])
        if data.get('max_amount'):
            expenses = expenses.filter(amount__lte=data['max_amount'])

        # فلتر البحث
        if data.get('search'):
            search_query = data['search']
            expenses = expenses.filter(
                Q(budget__application__applicant__first_name__icontains=search_query) |
                Q(budget__application__applicant__last_name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(receipt_number__icontains=search_query)
            )

    # ترقيم الصفحات
    paginator = Paginator(expenses, 20)  # 20 عنصر في كل صفحة
    page = request.GET.get('page')
    try:
        expenses_page = paginator.page(page)
    except PageNotAnInteger:
        expenses_page = paginator.page(1)
    except EmptyPage:
        expenses_page = paginator.page(paginator.num_pages)

    context = {
        'fiscal_year': fiscal_year,
        'expenses': expenses_page,
        'filter_form': filter_form,
        'total_expenses': expenses.aggregate(total=Sum('amount'))['total'] or 0,
        'total_approved': expenses.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0,
        'total_pending': expenses.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0,
    }
    return render(request, 'finance/fiscal_year_expenses.html', context)


@login_required
@permission_required('finance.view_fiscalyear', raise_exception=True)
def fiscal_year_budgets(request, fiscal_year_id):
    """عرض ميزانيات السنة المالية"""
    fiscal_year = get_object_or_404(FiscalYear, id=fiscal_year_id)

    # استخدام نموذج الفلترة
    filter_form = BudgetFilterForm(request.GET)
    budgets = ScholarshipBudget.objects.filter(fiscal_year=fiscal_year).order_by('-created_at')

    # تطبيق الفلاتر
    if filter_form.is_valid():
        data = filter_form.cleaned_data

        # فلتر حالة الميزانية
        if data.get('status'):
            budgets = budgets.filter(status=data['status'])

        # فلتر التاريخ (مدى تاريخي)
        if data.get('start_date'):
            budgets = budgets.filter(start_date__gte=data['start_date'])
        if data.get('end_date'):
            budgets = budgets.filter(end_date__lte=data['end_date'])

        # فلتر المبلغ (مدى مالي)
        if data.get('min_amount'):
            budgets = budgets.filter(total_amount__gte=data['min_amount'])
        if data.get('max_amount'):
            budgets = budgets.filter(total_amount__lte=data['max_amount'])

        # فلتر البحث
        if data.get('search'):
            search_query = data['search']
            budgets = budgets.filter(
                Q(application__applicant__first_name__icontains=search_query) |
                Q(application__applicant__last_name__icontains=search_query) |
                Q(application__scholarship__title__icontains=search_query)
            )

    # إضافة البيانات المحسوبة
    for budget in budgets:
        budget.spent_amount = budget.get_spent_amount()
        budget.remaining_amount = budget.get_remaining_amount()
        budget.spent_percentage = budget.get_spent_percentage()

    # ترقيم الصفحات
    paginator = Paginator(budgets, 20)  # 20 عنصر في كل صفحة
    page = request.GET.get('page')
    try:
        budgets_page = paginator.page(page)
    except PageNotAnInteger:
        budgets_page = paginator.page(1)
    except EmptyPage:
        budgets_page = paginator.page(paginator.num_pages)

    context = {
        'fiscal_year': fiscal_year,
        'budgets': budgets_page,
        'filter_form': filter_form,
        'total_budget': budgets.aggregate(total=Sum('total_amount'))['total'] or 0,
        'active_budgets': budgets.filter(status='active').count(),
    }
    return render(request, 'finance/fiscal_year_budgets.html', context)


@login_required
@permission_required('finance.change_scholarshipsettings', raise_exception=True)
def scholarship_settings(request):
    """إدارة إعدادات نظام الابتعاث"""
    # الحصول على الإعدادات الحالية أو إنشاء إعدادات جديدة
    settings = ScholarshipSettings.objects.first()
    if not settings:
        settings = ScholarshipSettings.objects.create()

    if request.method == 'POST':
        form = ScholarshipSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, _("تم تحديث الإعدادات بنجاح"))
            return redirect('finance:scholarship_settings')
    else:
        form = ScholarshipSettingsForm(instance=settings)

    context = {
        'form': form,
        'settings': settings,
    }
    return render(request, 'finance/scholarship_settings.html', context)


@login_required
@permission_required('finance.view_fiscalyear', raise_exception=True)
def fiscal_year_summary_report(request):
    """تقرير ملخص السنوات المالية"""
    # الحصول على جميع السنوات المالية
    fiscal_years = FiscalYear.objects.all().order_by('-year')

    # إضافة البيانات المحسوبة
    for fiscal_year in fiscal_years:
        fiscal_year.spent_amount = fiscal_year.get_spent_amount()
        fiscal_year.remaining_amount = fiscal_year.get_remaining_amount()
        fiscal_year.spent_percentage = fiscal_year.get_spent_percentage()
        fiscal_year.budgets_count = fiscal_year.scholarship_budgets.count()
        fiscal_year.expenses_count = Expense.objects.filter(fiscal_year=fiscal_year).count()

    # السنة المالية الحالية
    settings = ScholarshipSettings.objects.first()
    current_fiscal_year = settings.current_fiscal_year if settings else None

    context = {
        'fiscal_years': fiscal_years,
        'current_fiscal_year': current_fiscal_year,
        'report_title': _('تقرير ملخص السنوات المالية'),
    }
    return render(request, 'finance/reports/fiscal_year_summary.html', context)


@login_required
def api_fiscal_year_summary(request):
    """API لبيانات ملخص السنة المالية"""
    fiscal_year_id = request.GET.get('fiscal_year_id')

    if fiscal_year_id:
        fiscal_year = get_object_or_404(FiscalYear, id=fiscal_year_id)
    else:
        # استخدام السنة المالية الحالية
        settings = ScholarshipSettings.objects.first()
        if settings and settings.current_fiscal_year:
            fiscal_year = settings.current_fiscal_year
        else:
            # أحدث سنة مالية
            fiscal_year = FiscalYear.objects.filter(status='open').order_by('-year').first()

            if not fiscal_year:
                return JsonResponse({
                    'error': 'لا توجد سنة مالية مفتوحة'
                })

    # حساب إجماليات السنة المالية
    total_budget = fiscal_year.total_budget
    spent_amount = fiscal_year.get_spent_amount()
    remaining_amount = fiscal_year.get_remaining_amount()

    # بيانات الرسم البياني الدائري
    pie_data = [
        {'name': _('المبلغ المصروف'), 'value': float(spent_amount)},
        {'name': _('المبلغ المتبقي'), 'value': float(remaining_amount)},
    ]

    # المصروفات الشهرية
    monthly_expenses = Expense.objects.filter(
        fiscal_year=fiscal_year,
        status='approved'
    ).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')

    # تحويل البيانات الشهرية إلى تنسيق مناسب
    months_data = []
    for month in range(1, 13):
        month_date = datetime.date(fiscal_year.year, month, 1)
        month_name = month_date.strftime('%B')  # اسم الشهر

        # البحث عن المصروفات في هذا الشهر
        month_expense = next(
            (item for item in monthly_expenses if item['month'].month == month),
            {'total': 0}
        )

        months_data.append({
            'month': month_name,
            'value': float(month_expense['total']),
        })

    # المصروفات حسب الفئة
    category_expenses = Expense.objects.filter(
        fiscal_year=fiscal_year,
        status='approved'
    ).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')

    category_data = [
        {'name': item['category__name'], 'value': float(item['total'])}
        for item in category_expenses
    ]

    return JsonResponse({
        'fiscal_year': {
            'id': fiscal_year.id,
            'year': fiscal_year.year,
            'status': fiscal_year.status,
        },
        'pie_data': pie_data,
        'months_data': months_data,
        'category_data': category_data,
        'total_budget': float(total_budget),
        'spent_amount': float(spent_amount),
        'remaining_amount': float(remaining_amount),
    })

@login_required
@permission_required('finance.view_scholarshipbudget', raise_exception=True)
def budget_list(request):
    """عرض قائمة الميزانيات"""
    # استخدام نموذج الفلترة
    filter_form = BudgetFilterForm(request.GET)
    budgets = ScholarshipBudget.objects.all().order_by('-created_at')

    # تطبيق الفلاتر
    if filter_form.is_valid():
        data = filter_form.cleaned_data

        # فلتر حالة الميزانية
        if data.get('status'):
            budgets = budgets.filter(status=data['status'])

        # فلتر السنة المالية
        if data.get('fiscal_year'):
            budgets = budgets.filter(fiscal_year=data['fiscal_year'])

        # فلتر التاريخ (مدى تاريخي)
        if data.get('start_date'):
            budgets = budgets.filter(start_date__gte=data['start_date'])
        if data.get('end_date'):
            budgets = budgets.filter(end_date__lte=data['end_date'])

        # فلتر المبلغ (مدى مالي)
        if data.get('min_amount'):
            budgets = budgets.filter(total_amount__gte=data['min_amount'])
        if data.get('max_amount'):
            budgets = budgets.filter(total_amount__lte=data['max_amount'])

        # فلتر البحث (في اسم المتقدم واسم المنحة)
        if data.get('search'):
            search_query = data['search']
            budgets = budgets.filter(
                Q(application__applicant__first_name__icontains=search_query) |
                Q(application__applicant__last_name__icontains=search_query) |
                Q(application__scholarship__title__icontains=search_query)
            )

    # إضافة البيانات المحسوبة
    for budget in budgets:
        budget.spent_amount = budget.get_spent_amount()
        budget.remaining_amount = budget.get_remaining_amount()
        budget.spent_percentage = budget.get_spent_percentage()

    # ترقيم الصفحات
    paginator = Paginator(budgets, 10)  # 10 عناصر في كل صفحة
    page = request.GET.get('page')
    try:
        budgets_page = paginator.page(page)
    except PageNotAnInteger:
        budgets_page = paginator.page(1)
    except EmptyPage:
        budgets_page = paginator.page(paginator.num_pages)

    # الحصول على السنوات المالية المفتوحة للعرض في الواجهة
    open_fiscal_years = FiscalYear.objects.filter(status='open').order_by('-year')

    context = {
        'budgets': budgets_page,
        'filter_form': filter_form,
        'total_count': budgets.count(),
        'open_fiscal_years': open_fiscal_years,
        'total_budget_amount': budgets.aggregate(total=Sum('total_amount'))['total'] or 0,
    }
    return render(request, 'finance/budget_list.html', context)

@login_required
@permission_required('finance.view_scholarshipbudget', raise_exception=True)
def budget_detail(request, budget_id):
    """عرض تفاصيل ميزانية محددة"""
    budget = get_object_or_404(ScholarshipBudget, id=budget_id)

    # البيانات المحسوبة
    budget.spent_amount = budget.get_spent_amount()
    budget.remaining_amount = budget.get_remaining_amount()
    budget.spent_percentage = budget.get_spent_percentage()

    # المصروفات المرتبطة
    if budget.fiscal_year:
        # إذا كانت الميزانية مرتبطة بسنة مالية، اعرض المصروفات خلال تلك السنة فقط
        expenses = Expense.objects.filter(
            budget=budget,
            fiscal_year=budget.fiscal_year
        ).order_by('-date')
    else:
        # وإلا اعرض جميع المصروفات
        expenses = Expense.objects.filter(budget=budget).order_by('-date')

    # إجمالي المصروفات حسب الفئة
    expenses_by_category = expenses.values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')

    # تعديلات الميزانية
    if budget.fiscal_year:
        # إذا كانت الميزانية مرتبطة بسنة مالية، اعرض التعديلات خلال تلك السنة فقط
        adjustments = BudgetAdjustment.objects.filter(
            budget=budget,
            fiscal_year=budget.fiscal_year
        ).order_by('-date')
    else:
        # وإلا اعرض جميع التعديلات
        adjustments = BudgetAdjustment.objects.filter(budget=budget).order_by('-date')

    # السنوات الدراسية للابتعاث
    yearly_costs = YearlyScholarshipCosts.objects.filter(budget=budget).order_by('year_number')

    # سجل العمليات المرتبطة بالميزانية
    logs = FinancialLog.objects.filter(
        Q(budget=budget) |
        Q(expense__budget=budget) |
        Q(adjustment__budget=budget)
    ).order_by('-created_at')[:20]

    # الحصول على السنوات المالية المفتوحة للعرض في الواجهة
    open_fiscal_years = FiscalYear.objects.filter(status='open').order_by('-year')

    context = {
        'budget': budget,
        'expenses': expenses,
        'expenses_by_category': expenses_by_category,
        'adjustments': adjustments,
        'yearly_costs': yearly_costs,
        'logs': logs,
        'open_fiscal_years': open_fiscal_years,
    }
    return render(request, 'finance/budget_detail.html', context)


@login_required
@permission_required('finance.add_scholarshipbudget', raise_exception=True)
def create_budget(request, application_id):
    """إنشاء ميزانية جديدة لطلب ابتعاث"""
    application = get_object_or_404(Application, id=application_id)

    # التحقق من أن الطلب موافق عليه
    if application.status.order < 9:  # 9 هو ترتيب حالة "موافق من رئيس الجامعة"
        messages.error(request, _("لا يمكن إنشاء ميزانية لطلب غير موافق عليه من رئيس الجامعة"))
        return redirect('applications:application_detail', application_id=application.id)

    # التحقق من عدم وجود ميزانية سابقة
    if hasattr(application, 'budget'):
        messages.warning(request, _("يوجد ميزانية بالفعل لهذا الطلب"))
        return redirect('finance:budget_detail', budget_id=application.budget.id)

    # الحصول على السنة المالية الحالية
    settings = ScholarshipSettings.objects.first()
    current_fiscal_year = None
    if settings:
        current_fiscal_year = settings.current_fiscal_year
    else:
        # في حالة عدم وجود إعدادات، استخدم أحدث سنة مالية مفتوحة
        current_fiscal_year = FiscalYear.objects.filter(status='open').order_by('-year').first()

    if request.method == 'POST':
        form = ScholarshipBudgetForm(request.POST)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.application = application
            budget.created_by = request.user

            # التحقق من تعيين السنة المالية
            if not budget.fiscal_year and current_fiscal_year:
                budget.fiscal_year = current_fiscal_year

            budget.save()

            # إنشاء سجل للعملية
            FinancialLog.objects.create(
                budget=budget,
                fiscal_year=budget.fiscal_year,
                action_type='create',
                description=_("إنشاء ميزانية جديدة"),
                created_by=request.user
            )

            messages.success(request, _("تم إنشاء الميزانية بنجاح"))
            return redirect('finance:budget_detail', budget_id=budget.id)
    else:
        # القيم الافتراضية: تاريخ البداية والنهاية مرتبط بمدة الابتعاث في المنحة
        scholarship = application.scholarship
        start_date = timezone.now().date()
        end_date = start_date + datetime.timedelta(days=365)  # سنة افتراضية

        form = ScholarshipBudgetForm(initial={
            'fiscal_year': current_fiscal_year,
            'start_date': start_date,
            'end_date': end_date,
        })

    context = {
        'form': form,
        'application': application,
        'current_fiscal_year': current_fiscal_year,
    }
    return render(request, 'finance/budget_form.html', context)

@login_required
@permission_required('finance.view_expense', raise_exception=True)
def expense_list(request):
    """عرض قائمة المصروفات"""
    # استخدام نموذج الفلترة
    filter_form = ExpenseFilterForm(request.GET)
    expenses = Expense.objects.all().order_by('-date')

    # تطبيق الفلاتر
    if filter_form.is_valid():
        data = filter_form.cleaned_data

        # فلتر حالة المصروف
        if data.get('status'):
            expenses = expenses.filter(status=data['status'])

        # فلتر السنة المالية
        if data.get('fiscal_year'):
            expenses = expenses.filter(fiscal_year=data['fiscal_year'])

        # فلتر الفئة
        if data.get('category'):
            expenses = expenses.filter(category=data['category'])

        # فلتر التاريخ (مدى تاريخي)
        if data.get('start_date'):
            expenses = expenses.filter(date__gte=data['start_date'])
        if data.get('end_date'):
            expenses = expenses.filter(date__lte=data['end_date'])

        # فلتر المبلغ (مدى مالي)
        if data.get('min_amount'):
            expenses = expenses.filter(amount__gte=data['min_amount'])
        if data.get('max_amount'):
            expenses = expenses.filter(amount__lte=data['max_amount'])

        # فلتر البحث
        if data.get('search'):
            search_query = data['search']
            expenses = expenses.filter(
                Q(budget__application__applicant__first_name__icontains=search_query) |
                Q(budget__application__applicant__last_name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(receipt_number__icontains=search_query)
            )

    # ترقيم الصفحات
    paginator = Paginator(expenses, 10)  # 10 عناصر في كل صفحة
    page = request.GET.get('page')
    try:
        expenses_page = paginator.page(page)
    except PageNotAnInteger:
        expenses_page = paginator.page(1)
    except EmptyPage:
        expenses_page = paginator.page(paginator.num_pages)

    # الحصول على إحصائيات المصروفات
    total_amount = expenses.aggregate(total=Sum('amount'))['total'] or 0
    approved_amount = expenses.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0
    pending_amount = expenses.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0

    # الحصول على السنوات المالية للعرض في الواجهة
    fiscal_years = FiscalYear.objects.all().order_by('-year')

    context = {
        'expenses': expenses_page,
        'filter_form': filter_form,
        'total_count': expenses.count(),
        'total_amount': total_amount,
        'approved_amount': approved_amount,
        'pending_amount': pending_amount,
        'fiscal_years': fiscal_years,
    }
    return render(request, 'finance/expense_list.html', context)

@login_required
@permission_required('finance.add_expense', raise_exception=True)
def create_expense(request, budget_id):
    """إنشاء مصروف جديد لميزانية"""
    budget = get_object_or_404(ScholarshipBudget, id=budget_id)

    # التحقق من حالة الميزانية
    if budget.status != 'active':
        messages.error(request, _("لا يمكن إضافة مصروفات لميزانية غير نشطة"))
        return redirect('finance:budget_detail', budget_id=budget.id)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, budget=budget)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.budget = budget
            expense.created_by = request.user

            # التحقق من تعيين السنة المالية
            if not expense.fiscal_year and budget.fiscal_year:
                expense.fiscal_year = budget.fiscal_year

            expense.save()

            # إنشاء سجل للعملية
            FinancialLog.objects.create(
                expense=expense,
                budget=budget,
                fiscal_year=expense.fiscal_year,
                action_type='create',
                description=_("إنشاء مصروف جديد"),
                created_by=request.user
            )

            messages.success(request, _("تم إنشاء المصروف بنجاح"))
            return redirect('finance:budget_detail', budget_id=budget.id)
    else:
        # تعيين السنة المالية تلقائيًا
        initial_data = {'date': timezone.now().date()}
        if budget.fiscal_year:
            initial_data['fiscal_year'] = budget.fiscal_year

        form = ExpenseForm(budget=budget, initial=initial_data)

    context = {
        'form': form,
        'budget': budget,
    }
    return render(request, 'finance/expense_form.html', context)

@login_required
@permission_required('finance.view_scholarshipbudget', raise_exception=True)
def finance_dashboard(request):
    """لوحة معلومات الشؤون المالية"""
    # الحصول على السنة المالية الحالية
    settings = ScholarshipSettings.objects.first()
    current_fiscal_year = None

    if settings and settings.current_fiscal_year:
        current_fiscal_year = settings.current_fiscal_year
    else:
        # في حالة عدم وجود إعدادات، استخدم أحدث سنة مالية مفتوحة
        current_fiscal_year = FiscalYear.objects.filter(status='open').order_by('-year').first()

    # إحصائيات السنة المالية الحالية
    fiscal_year_stats = {}
    if current_fiscal_year:
        fiscal_year_stats = {
            'total_budget': current_fiscal_year.total_budget,
            'spent_amount': current_fiscal_year.get_spent_amount(),
            'remaining_amount': current_fiscal_year.get_remaining_amount(),
            'spent_percentage': current_fiscal_year.get_spent_percentage(),
        }

    # إحصائيات عامة
    total_budgets = ScholarshipBudget.objects.count()
    active_budgets = ScholarshipBudget.objects.filter(status='active').count()
    pending_budgets = ScholarshipBudget.objects.filter(status='pending').count()
    closed_budgets = ScholarshipBudget.objects.filter(status='closed').count()

    # حساب النسب المئوية للميزانيات
    active_budget_percentage = (active_budgets / total_budgets * 100) if total_budgets > 0 else 0
    pending_budget_percentage = (pending_budgets / total_budgets * 100) if total_budgets > 0 else 0
    closed_budget_percentage = (closed_budgets / total_budgets * 100) if total_budgets > 0 else 0

    # المصروفات
    total_expenses = Expense.objects.count()
    pending_expense_count = Expense.objects.filter(status='pending').count()
    pending_expense_amount = Expense.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0

    # إجمالي الميزانيات والمصروفات
    total_budget_amount = ScholarshipBudget.objects.aggregate(total=Sum('total_amount'))['total'] or 0

    # إذا كانت هناك سنة مالية حالية، احسب المصروفات المعتمدة فيها فقط
    if current_fiscal_year:
        total_expense_amount = Expense.objects.filter(
            fiscal_year=current_fiscal_year,
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0
    else:
        # وإلا احسب جميع المصروفات المعتمدة
        total_expense_amount = Expense.objects.filter(
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0

    remaining_budget = total_budget_amount - total_expense_amount
    budget_percentage = (total_expense_amount / total_budget_amount * 100) if total_budget_amount > 0 else 0

    # حساب التغير في المصروفات
    # يمكن حساب التغير بمقارنة الشهر الحالي مع الشهر السابق
    this_month = timezone.now().replace(day=1)
    last_month = (this_month - datetime.timedelta(days=1)).replace(day=1)

    # إذا كانت هناك سنة مالية حالية، احسب المصروفات الشهرية فيها فقط
    if current_fiscal_year:
        this_month_expenses = Expense.objects.filter(
            fiscal_year=current_fiscal_year,
            date__gte=this_month,
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0

        last_month_expenses = Expense.objects.filter(
            fiscal_year=current_fiscal_year,
            date__gte=last_month, date__lt=this_month,
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0
    else:
        # وإلا احسب جميع المصروفات الشهرية
        this_month_expenses = Expense.objects.filter(
            date__gte=this_month,
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0

        last_month_expenses = Expense.objects.filter(
            date__gte=last_month, date__lt=this_month,
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0

    expense_change = ((this_month_expenses - last_month_expenses) / last_month_expenses * 100) if last_month_expenses > 0 else 0

    # حساب معدل الصرف اليومي
    today = timezone.now().date()
    month_start = today.replace(day=1)
    days_passed = (today - month_start).days + 1

    # إذا كانت هناك سنة مالية حالية، احسب معدل الصرف اليومي فيها فقط
    if current_fiscal_year:
        monthly_expenses = Expense.objects.filter(
            fiscal_year=current_fiscal_year,
            date__gte=month_start, date__lte=today,
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0
    else:
        # وإلا احسب معدل الصرف اليومي لجميع المصروفات
        monthly_expenses = Expense.objects.filter(
            date__gte=month_start, date__lte=today,
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0

    daily_spend_rate = monthly_expenses / days_passed if days_passed > 0 else 0

    # آخر تحديث
    last_update = today

    # الحصول على أحدث المصروفات
    # إذا كانت هناك سنة مالية حالية، اعرض أحدث المصروفات فيها فقط
    if current_fiscal_year:
        recent_expenses = Expense.objects.filter(
            fiscal_year=current_fiscal_year
        ).order_by('-date')[:10]
    else:
        # وإلا اعرض أحدث المصروفات عمومًا
        recent_expenses = Expense.objects.all().order_by('-date')[:10]

    context = {
        # قيم ضرورية للقالب
        'current_fiscal_year': current_fiscal_year,
        'fiscal_year_stats': fiscal_year_stats,
        'remaining_budget': remaining_budget,
        'budget_percentage': budget_percentage,
        'monthly_expenses': this_month_expenses,
        'expense_change': expense_change,
        'daily_spend_rate': daily_spend_rate,
        'last_update': last_update,
        'pending_expense_count': pending_expense_count,
        'pending_expense_amount': pending_expense_amount,
        'recent_expenses': recent_expenses,
        'active_budgets': active_budgets,
        'pending_budgets': pending_budgets,
        'closed_budgets': closed_budgets,
        'total_budgets': total_budgets,
        'active_budget_percentage': active_budget_percentage,
        'pending_budget_percentage': pending_budget_percentage,
        'closed_budget_percentage': closed_budget_percentage,

        # قيم إضافية
        'total_expenses': total_expenses,
        'total_budget_amount': total_budget_amount,
        'total_expense_amount': total_expense_amount,
    }
    return render(request, 'finance/dashboard.html', context)


@login_required
@permission_required('finance.change_scholarshipbudget', raise_exception=True)
def update_budget(request, budget_id):
    """تحديث ميزانية موجودة"""
    budget = get_object_or_404(ScholarshipBudget, id=budget_id)

    # التحقق من حالة الميزانية - لا يمكن تعديل الميزانيات المغلقة
    if budget.status == 'closed':
        messages.error(request, _("لا يمكن تعديل ميزانية مغلقة"))
        return redirect('finance:budget_detail', budget_id=budget.id)

    if request.method == 'POST':
        form = ScholarshipBudgetForm(request.POST, instance=budget)
        if form.is_valid():
            # حفظ الميزانية المحدثة
            updated_budget = form.save()

            # إنشاء سجل للعملية
            FinancialLog.objects.create(
                budget=updated_budget,
                fiscal_year=updated_budget.fiscal_year,
                action_type='update',
                description=_("تحديث ميزانية"),
                created_by=request.user
            )

            messages.success(request, _("تم تحديث الميزانية بنجاح"))
            return redirect('finance:budget_detail', budget_id=budget.id)
    else:
        form = ScholarshipBudgetForm(instance=budget)

    context = {
        'form': form,
        'budget': budget,
        'is_update': True,
    }
    return render(request, 'finance/budget_form.html', context)


@login_required
@permission_required('finance.delete_scholarshipbudget', raise_exception=True)
def delete_budget(request, budget_id):
    """حذف ميزانية"""
    budget = get_object_or_404(ScholarshipBudget, id=budget_id)

    # إذا كان هناك مصروفات معتمدة، لا يمكن الحذف
    if Expense.objects.filter(budget=budget, status='approved').exists():
        messages.error(request, _("لا يمكن حذف الميزانية لأنها تحتوي على مصروفات معتمدة"))
        return redirect('finance:budget_detail', budget_id=budget.id)

    # لا يمكن حذف ميزانية مرتبطة بسجلات أخرى
    if BudgetAdjustment.objects.filter(budget=budget).exists():
        messages.error(request, _("لا يمكن حذف الميزانية لأنها مرتبطة بتعديلات ميزانية"))
        return redirect('finance:budget_detail', budget_id=budget.id)

    if YearlyScholarshipCosts.objects.filter(budget=budget).exists():
        messages.error(request, _("لا يمكن حذف الميزانية لأنها مرتبطة بتكاليف سنوية"))
        return redirect('finance:budget_detail', budget_id=budget.id)

    if request.method == 'POST':
        application = budget.application
        fiscal_year = budget.fiscal_year

        # إنشاء سجل للعملية
        FinancialLog.objects.create(
            fiscal_year=fiscal_year,
            action_type='delete',
            description=_("حذف ميزانية") + f" - {application.applicant.get_full_name()}",
            created_by=request.user
        )

        budget.delete()
        messages.success(request, _("تم حذف الميزانية بنجاح"))
        return redirect('finance:budget_list')

    context = {
        'budget': budget,
    }
    return render(request, 'finance/budget_confirm_delete.html', context)


@login_required
@permission_required('finance.view_expense', raise_exception=True)
def expense_detail(request, expense_id):
    """عرض تفاصيل مصروف محدد"""
    expense = get_object_or_404(Expense, id=expense_id)

    # سجل العمليات المرتبطة بهذا المصروف
    logs = FinancialLog.objects.filter(expense=expense).order_by('-created_at')

    context = {
        'expense': expense,
        'logs': logs,
    }
    return render(request, 'finance/expense_detail.html', context)


@login_required
@permission_required('finance.change_expense', raise_exception=True)
def update_expense(request, expense_id):
    """تحديث مصروف موجود"""
    expense = get_object_or_404(Expense, id=expense_id)

    # لا يمكن تعديل المصروفات المعتمدة
    if expense.status == 'approved':
        messages.error(request, _("لا يمكن تعديل المصروفات المعتمدة"))
        return redirect('finance:expense_detail', expense_id=expense.id)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense, budget=expense.budget)
        if form.is_valid():
            updated_expense = form.save()

            # إنشاء سجل للعملية
            FinancialLog.objects.create(
                expense=updated_expense,
                budget=updated_expense.budget,
                fiscal_year=updated_expense.fiscal_year,
                action_type='update',
                description=_("تحديث مصروف"),
                created_by=request.user
            )

            messages.success(request, _("تم تحديث المصروف بنجاح"))
            return redirect('finance:expense_detail', expense_id=expense.id)
    else:
        form = ExpenseForm(instance=expense, budget=expense.budget)

    context = {
        'form': form,
        'expense': expense,
        'is_update': True,
    }
    return render(request, 'finance/expense_form.html', context)


@login_required
@permission_required('finance.delete_expense', raise_exception=True)
def delete_expense(request, expense_id):
    """حذف مصروف"""
    expense = get_object_or_404(Expense, id=expense_id)

    # لا يمكن حذف المصروفات المعتمدة
    if expense.status == 'approved':
        messages.error(request, _("لا يمكن حذف المصروفات المعتمدة"))
        return redirect('finance:expense_detail', expense_id=expense.id)

    if request.method == 'POST':
        budget_id = expense.budget.id
        fiscal_year = expense.fiscal_year

        # إنشاء سجل للعملية
        FinancialLog.objects.create(
            budget=expense.budget,
            fiscal_year=fiscal_year,
            action_type='delete',
            description=_("حذف مصروف") + f" - {expense.category.name} - {expense.amount}",
            created_by=request.user
        )

        expense.delete()
        messages.success(request, _("تم حذف المصروف بنجاح"))
        return redirect('finance:budget_detail', budget_id=budget_id)

    context = {
        'expense': expense,
    }
    return render(request, 'finance/expense_confirm_delete.html', context)


@login_required
@permission_required('finance.change_expense', raise_exception=True)
def approve_expense(request, expense_id):
    """الموافقة على مصروف أو رفضه"""
    expense = get_object_or_404(Expense, id=expense_id)

    # لا يمكن تغيير حالة المصروفات المعتمدة أو المرفوضة
    if expense.status != 'pending':
        messages.error(request, _("لا يمكن تغيير حالة المصروفات المعتمدة أو المرفوضة"))
        return redirect('finance:expense_detail', expense_id=expense.id)

    if request.method == 'POST':
        form = ExpenseApprovalForm(request.POST, instance=expense)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.approved_by = request.user
            expense.approval_date = timezone.now()
            expense.save()

            # إنشاء سجل للعملية
            action_type = 'approve' if expense.status == 'approved' else 'reject'
            description = _("الموافقة على المصروف") if expense.status == 'approved' else _("رفض المصروف")

            FinancialLog.objects.create(
                expense=expense,
                budget=expense.budget,
                fiscal_year=expense.fiscal_year,
                action_type=action_type,
                description=description,
                created_by=request.user
            )

            messages.success(request, _("تم تحديث حالة المصروف بنجاح"))
            return redirect('finance:expense_detail', expense_id=expense.id)
    else:
        form = ExpenseApprovalForm(instance=expense)

    context = {
        'form': form,
        'expense': expense,
    }
    return render(request, 'finance/expense_approval_form.html', context)

@login_required
@permission_required('finance.view_expensecategory', raise_exception=True)
def category_list(request):
    """عرض قائمة فئات المصروفات"""
    categories = ExpenseCategory.objects.all().order_by('name')

    # إحصائيات حول استخدام كل فئة
    for category in categories:
        category.expenses_count = Expense.objects.filter(category=category).count()
        category.total_amount = Expense.objects.filter(category=category).aggregate(
            total=Sum('amount'))['total'] or 0

    context = {
        'categories': categories,
    }
    return render(request, 'finance/category_list.html', context)


@login_required
@permission_required('finance.add_expensecategory', raise_exception=True)
def create_category(request):
    """إنشاء فئة مصروفات جديدة"""
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, _("تم إنشاء فئة المصروفات بنجاح"))
            return redirect('finance:category_list')
    else:
        form = ExpenseCategoryForm()

    context = {
        'form': form,
    }
    return render(request, 'finance/category_form.html', context)

@login_required
@permission_required('finance.change_expensecategory', raise_exception=True)
def update_category(request, category_id):
    """تحديث فئة مصروفات"""
    category = get_object_or_404(ExpenseCategory, id=category_id)

    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, _("تم تحديث فئة المصروفات بنجاح"))
            return redirect('finance:category_list')
    else:
        form = ExpenseCategoryForm(instance=category)

    context = {
        'form': form,
        'category': category,
        'is_update': True,
    }
    return render(request, 'finance/category_form.html', context)

@login_required
@permission_required('finance.delete_expensecategory', raise_exception=True)
def delete_category(request, category_id):
    """حذف فئة مصروفات"""
    category = get_object_or_404(ExpenseCategory, id=category_id)

    # التحقق من عدم وجود مصروفات مرتبطة بهذه الفئة
    if Expense.objects.filter(category=category).exists():
        messages.error(request, _("لا يمكن حذف فئة مصروفات مستخدمة في مصروفات"))
        return redirect('finance:category_list')

    if request.method == 'POST':
        category.delete()
        messages.success(request, _("تم حذف فئة المصروفات بنجاح"))
        return redirect('finance:category_list')

    context = {
        'category': category,
    }
    return render(request, 'finance/category_confirm_delete.html', context)

@login_required
@permission_required('finance.view_budgetadjustment', raise_exception=True)
def adjustment_list(request, budget_id):
    """عرض قائمة تعديلات الميزانية"""
    budget = get_object_or_404(ScholarshipBudget, id=budget_id)

    # التعديلات المرتبطة بالميزانية
    if budget.fiscal_year:
        # إذا كانت الميزانية مرتبطة بسنة مالية، اعرض التعديلات خلال تلك السنة فقط
        adjustments = BudgetAdjustment.objects.filter(
            budget=budget,
            fiscal_year=budget.fiscal_year
        ).order_by('-date')
    else:
        # وإلا اعرض جميع التعديلات
        adjustments = BudgetAdjustment.objects.filter(budget=budget).order_by('-date')

    context = {
        'budget': budget,
        'adjustments': adjustments,
    }
    return render(request, 'finance/adjustment_list.html', context)

@login_required
@permission_required('finance.view_budgetadjustment', raise_exception=True)
def adjustment_detail(request, adjustment_id):
    """عرض تفاصيل تعديل ميزانية محدد"""
    adjustment = get_object_or_404(BudgetAdjustment, id=adjustment_id)

    # سجل العمليات المرتبطة بهذا التعديل
    logs = FinancialLog.objects.filter(adjustment=adjustment).order_by('-created_at')

    context = {
        'adjustment': adjustment,
        'logs': logs,
    }
    return render(request, 'finance/adjustment_detail.html', context)

@login_required
@permission_required('finance.add_budgetadjustment', raise_exception=True)
def create_adjustment(request, budget_id):
    """إنشاء تعديل ميزانية جديد"""
    budget = get_object_or_404(ScholarshipBudget, id=budget_id)

    # التحقق من حالة الميزانية
    if budget.status != 'active':
        messages.error(request, _("لا يمكن إضافة تعديلات لميزانية غير نشطة"))
        return redirect('finance:budget_detail', budget_id=budget.id)

    if request.method == 'POST':
        form = BudgetAdjustmentForm(request.POST, budget=budget)
        if form.is_valid():
            adjustment = form.save(commit=False)
            adjustment.budget = budget
            adjustment.created_by = request.user

            # التحقق من تعيين السنة المالية
            if not adjustment.fiscal_year and budget.fiscal_year:
                adjustment.fiscal_year = budget.fiscal_year

            adjustment.save()

            # إنشاء سجل للعملية
            FinancialLog.objects.create(
                adjustment=adjustment,
                budget=budget,
                fiscal_year=adjustment.fiscal_year,
                action_type='create',
                description=_("إنشاء تعديل ميزانية جديد"),
                created_by=request.user
            )

            messages.success(request, _("تم إنشاء تعديل الميزانية بنجاح وهو قيد المراجعة"))
            return redirect('finance:budget_detail', budget_id=budget.id)
    else:
        # تعيين السنة المالية تلقائيًا
        initial_data = {'date': timezone.now().date()}
        if budget.fiscal_year:
            initial_data['fiscal_year'] = budget.fiscal_year

        form = BudgetAdjustmentForm(budget=budget, initial=initial_data)

    context = {
        'form': form,
        'budget': budget,
    }
    return render(request, 'finance/adjustment_form.html', context)

@login_required
@permission_required('finance.change_budgetadjustment', raise_exception=True)
def approve_adjustment(request, adjustment_id):
    """الموافقة على تعديل ميزانية"""
    adjustment = get_object_or_404(BudgetAdjustment, id=adjustment_id)

    # لا يمكن تغيير حالة التعديلات المعتمدة أو المرفوضة
    if adjustment.status != 'pending':
        messages.error(request, _("لا يمكن تغيير حالة التعديلات المعتمدة أو المرفوضة"))
        return redirect('finance:adjustment_detail', adjustment_id=adjustment.id)

    if request.method == 'POST':
        form = BudgetAdjustmentApprovalForm(request.POST, instance=adjustment)
        if form.is_valid():
            old_status = adjustment.status
            adjustment = form.save(commit=False)
            adjustment.approved_by = request.user
            adjustment.approval_date = timezone.now()
            adjustment.save()

            # تطبيق التعديل على الميزانية إذا تمت الموافقة
            if old_status != 'approved' and adjustment.status == 'approved':
                budget = adjustment.budget
                if adjustment.adjustment_type == 'increase':
                    budget.total_amount += adjustment.amount
                else:  # decrease
                    budget.total_amount -= adjustment.amount
                budget.save()

                # إنشاء سجل لتحديث الميزانية
                FinancialLog.objects.create(
                    budget=budget,
                    fiscal_year=adjustment.fiscal_year,
                    action_type='update',
                    description=_("تحديث إجمالي الميزانية من خلال تعديل معتمد"),
                    created_by=request.user
                )

            # إنشاء سجل للعملية
            action_type = 'approve' if adjustment.status == 'approved' else 'reject'
            description = _("الموافقة على تعديل الميزانية") if adjustment.status == 'approved' else _("رفض تعديل الميزانية")

            FinancialLog.objects.create(
                adjustment=adjustment,
                budget=adjustment.budget,
                fiscal_year=adjustment.fiscal_year,
                action_type=action_type,
                description=description,
                created_by=request.user
            )

            messages.success(request, _("تم تحديث حالة تعديل الميزانية بنجاح"))
            return redirect('finance:adjustment_detail', adjustment_id=adjustment.id)
    else:
        form = BudgetAdjustmentApprovalForm(instance=adjustment)

    context = {
        'form': form,
        'adjustment': adjustment,
    }
    return render(request, 'finance/adjustment_approval_form.html', context)


@login_required
@permission_required('finance.view_financialreport', raise_exception=True)
def report_list(request):
    """عرض قائمة التقارير المالية"""
    # التقارير التي أنشأها المستخدم
    user_reports = FinancialReport.objects.filter(created_by=request.user).order_by('-created_at')

    # التقارير العامة
    public_reports = FinancialReport.objects.filter(is_public=True).exclude(created_by=request.user).order_by('-created_at')

    # تحسين الأداء باستخدام select_related للحقول المرتبطة
    user_reports = user_reports.select_related('fiscal_year', 'created_by')
    public_reports = public_reports.select_related('fiscal_year', 'created_by')

    # الحصول على السنوات المالية للعرض في الواجهة
    fiscal_years = FiscalYear.objects.all().order_by('-year')

    context = {
        'user_reports': user_reports,
        'public_reports': public_reports,
        'fiscal_years': fiscal_years,
        'report_types': dict(FinancialReport.REPORT_TYPE_CHOICES),
    }
    return render(request, 'finance/report_list.html', context)

@login_required
@permission_required('finance.add_financialreport', raise_exception=True)
def create_report(request):
    """إنشاء تقرير مالي جديد"""
    if request.method == 'POST':
        form = FinancialReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.created_by = request.user

            # حفظ فلاتر التقرير
            filters = {}
            report_type = form.cleaned_data['report_type']

            # جمع البيانات حسب نوع التقرير
            if report_type == 'budget_summary':
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                fiscal_year_id = request.POST.get('fiscal_year_filter')
                filters = {'start_date': start_date, 'end_date': end_date, 'fiscal_year_id': fiscal_year_id}

            elif report_type == 'expense_summary':
                status = request.POST.get('status')
                category = request.POST.get('category')
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                fiscal_year_id = request.POST.get('fiscal_year_filter')
                filters = {
                    'status': status,
                    'category': category,
                    'start_date': start_date,
                    'end_date': end_date,
                    'fiscal_year_id': fiscal_year_id
                }

            elif report_type == 'monthly_expenses':
                year = request.POST.get('year')
                fiscal_year_id = request.POST.get('fiscal_year_filter')
                filters = {'year': year, 'fiscal_year_id': fiscal_year_id}

            elif report_type == 'category_expenses':
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                fiscal_year_id = request.POST.get('fiscal_year_filter')
                filters = {'start_date': start_date, 'end_date': end_date, 'fiscal_year_id': fiscal_year_id}

            elif report_type == 'fiscal_year_summary':
                fiscal_year_id = request.POST.get('fiscal_year_filter')
                filters = {'fiscal_year_id': fiscal_year_id}

            # حفظ الفلاتر والتقرير
            report.filters = filters
            report.save()

            messages.success(request, _("تم إنشاء التقرير المالي بنجاح"))
            return redirect('finance:report_detail', report_id=report.id)
    else:
        form = FinancialReportForm()

    # بيانات إضافية حسب نوع التقرير (لعرضها في الفورم)
    date_range_form = DateRangeForm()
    expense_filter_form = ExpenseFilterForm()
    fiscal_years = FiscalYear.objects.all().order_by('-year')
    categories = ExpenseCategory.objects.all().order_by('name')
    years = list(range(timezone.now().year - 5, timezone.now().year + 1))

    context = {
        'form': form,
        'date_range_form': date_range_form,
        'expense_filter_form': expense_filter_form,
        'fiscal_years': fiscal_years,
        'categories': categories,
        'years': years,
    }
    return render(request, 'finance/report_form.html', context)

@login_required
@permission_required('finance.view_financialreport', raise_exception=True)
def report_detail(request, report_id):
    """عرض تفاصيل تقرير مالي"""
    report = get_object_or_404(FinancialReport, id=report_id)

    # التحقق من الصلاحيات (مالك التقرير أو تقرير عام)
    if report.created_by != request.user and not report.is_public:
        messages.error(request, _("ليس لديك صلاحية لعرض هذا التقرير"))
        return redirect('finance:report_list')

    # بيانات التقرير حسب نوعه
    report_data = {}

    if report.report_type == 'budget_summary':
        report_data = generate_budget_summary_data(report.filters)

    elif report.report_type == 'expense_summary':
        report_data = generate_expense_summary_data(report.filters)

    elif report.report_type == 'monthly_expenses':
        report_data = generate_monthly_expenses_data(report.filters)

    elif report.report_type == 'category_expenses':
        report_data = generate_category_expenses_data(report.filters)

    elif report.report_type == 'budget_comparison':
        report_data = generate_budget_comparison_data(report.filters)

    elif report.report_type == 'fiscal_year_summary':
        report_data = generate_fiscal_year_summary_data(report.filters)

    elif report.report_type == 'scholarship_years_costs':
        report_data = generate_scholarship_years_costs_data(report.filters)

    elif report.report_type == 'custom':
        # التقارير المخصصة تعتمد على معالجة خاصة
        report_data = {'message': _('التقرير المخصص غير متاح حالياً')}

    context = {
        'report': report,
        'report_data': report_data,
    }
    return render(request, 'finance/report_detail.html', context)

@login_required
@permission_required('finance.change_financialreport', raise_exception=True)
def update_report(request, report_id):
    """تحديث تقرير مالي"""
    report = get_object_or_404(FinancialReport, id=report_id)

    # التحقق من الصلاحيات (فقط مالك التقرير)
    if report.created_by != request.user:
        messages.error(request, _("ليس لديك صلاحية لتعديل هذا التقرير"))
        return redirect('finance:report_list')

    if request.method == 'POST':
        form = FinancialReportForm(request.POST, instance=report)
        if form.is_valid():
            updated_report = form.save(commit=False)

            # تحديث فلاتر التقرير
            filters = {}
            report_type = form.cleaned_data['report_type']

            # جمع البيانات حسب نوع التقرير
            if report_type == 'budget_summary':
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                fiscal_year_id = request.POST.get('fiscal_year_filter')
                filters = {'start_date': start_date, 'end_date': end_date, 'fiscal_year_id': fiscal_year_id}

            elif report_type == 'expense_summary':
                status = request.POST.get('status')
                category = request.POST.get('category')
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                fiscal_year_id = request.POST.get('fiscal_year_filter')
                filters = {
                    'status': status,
                    'category': category,
                    'start_date': start_date,
                    'end_date': end_date,
                    'fiscal_year_id': fiscal_year_id
                }

            elif report_type == 'monthly_expenses':
                year = request.POST.get('year')
                fiscal_year_id = request.POST.get('fiscal_year_filter')
                filters = {'year': year, 'fiscal_year_id': fiscal_year_id}

            elif report_type == 'category_expenses':
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                fiscal_year_id = request.POST.get('fiscal_year_filter')
                filters = {'start_date': start_date, 'end_date': end_date, 'fiscal_year_id': fiscal_year_id}

            elif report_type == 'fiscal_year_summary':
                fiscal_year_id = request.POST.get('fiscal_year_filter')
                filters = {'fiscal_year_id': fiscal_year_id}

            # حفظ الفلاتر والتقرير
            updated_report.filters = filters
            updated_report.save()

            messages.success(request, _("تم تحديث التقرير المالي بنجاح"))
            return redirect('finance:report_detail', report_id=report.id)
    else:
        form = FinancialReportForm(instance=report)

    # بيانات إضافية حسب نوع التقرير (لعرضها في الفورم)
    filters = report.filters or {}
    date_range_form = DateRangeForm(initial={
        'start_date': filters.get('start_date'),
        'end_date': filters.get('end_date')
    })
    expense_filter_form = ExpenseFilterForm(initial={
        'status': filters.get('status'),
        'category': filters.get('category'),
        'start_date': filters.get('start_date'),
        'end_date': filters.get('end_date'),
        'fiscal_year': filters.get('fiscal_year_id')
    })
    fiscal_years = FiscalYear.objects.all().order_by('-year')
    categories = ExpenseCategory.objects.all().order_by('name')
    years = list(range(timezone.now().year - 5, timezone.now().year + 1))

    context = {
        'form': form,
        'report': report,
        'date_range_form': date_range_form,
        'expense_filter_form': expense_filter_form,
        'fiscal_years': fiscal_years,
        'categories': categories,
        'years': years,
        'is_update': True,
        'filters': filters,
    }
    return render(request, 'finance/report_form.html', context)

@login_required
@permission_required('finance.delete_financialreport', raise_exception=True)
def delete_report(request, report_id):
    """حذف تقرير مالي"""
    report = get_object_or_404(FinancialReport, id=report_id)

    # التحقق من الصلاحيات (فقط مالك التقرير)
    if report.created_by != request.user:
        messages.error(request, _("ليس لديك صلاحية لحذف هذا التقرير"))
        return redirect('finance:report_list')

    if request.method == 'POST':
        report.delete()
        messages.success(request, _("تم حذف التقرير المالي بنجاح"))
        return redirect('finance:report_list')

    context = {
        'report': report,
    }
    return render(request, 'finance/report_confirm_delete.html', context)

@login_required
@permission_required('finance.view_financialreport', raise_exception=True)
def export_report_pdf(request, report_id):
    """تصدير التقرير كملف PDF"""
    report = get_object_or_404(FinancialReport, id=report_id)

    # التحقق من الصلاحيات (مالك التقرير أو تقرير عام)
    if report.created_by != request.user and not report.is_public:
        messages.error(request, _("ليس لديك صلاحية لتصدير هذا التقرير"))
        return redirect('finance:report_list')

    # بيانات التقرير حسب نوعه
    report_data = {}

    if report.report_type == 'budget_summary':
        report_data = generate_budget_summary_data(report.filters)
    elif report.report_type == 'expense_summary':
        report_data = generate_expense_summary_data(report.filters)
    elif report.report_type == 'monthly_expenses':
        report_data = generate_monthly_expenses_data(report.filters)
    elif report.report_type == 'category_expenses':
        report_data = generate_category_expenses_data(report.filters)
    elif report.report_type == 'budget_comparison':
        report_data = generate_budget_comparison_data(report.filters)
    elif report.report_type == 'fiscal_year_summary':
        report_data = generate_fiscal_year_summary_data(report.filters)
    elif report.report_type == 'scholarship_years_costs':
        report_data = generate_scholarship_years_costs_data(report.filters)

    # إنشاء قالب HTML للتقرير
    context = {
        'report': report,
        'report_data': report_data,
        'export_date': timezone.now(),
    }

    html_string = render_to_string('finance/reports/pdf_template.html', context)

    # تحويل HTML إلى PDF
    response = HttpResponse(content_type='application/pdf')
    report_name = report.title.replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{report_name}.pdf"'

    pdf = weasyprint.HTML(string=html_string).write_pdf()
    response.write(pdf)

    return response

@login_required
@permission_required('finance.view_financialreport', raise_exception=True)
def export_report_excel(request, report_id):
    """تصدير التقرير كملف Excel"""
    report = get_object_or_404(FinancialReport, id=report_id)

    # التحقق من الصلاحيات (مالك التقرير أو تقرير عام)
    if report.created_by != request.user and not report.is_public:
        messages.error(request, _("ليس لديك صلاحية لتصدير هذا التقرير"))
        return redirect('finance:report_list')

    # بيانات التقرير حسب نوعه
    report_data = {}

    if report.report_type == 'budget_summary':
        report_data = generate_budget_summary_data(report.filters)
    elif report.report_type == 'expense_summary':
        report_data = generate_expense_summary_data(report.filters)
    elif report.report_type == 'monthly_expenses':
        report_data = generate_monthly_expenses_data(report.filters)
    elif report.report_type == 'category_expenses':
        report_data = generate_category_expenses_data(report.filters)
    elif report.report_type == 'budget_comparison':
        report_data = generate_budget_comparison_data(report.filters)
    elif report.report_type == 'fiscal_year_summary':
        report_data = generate_fiscal_year_summary_data(report.filters)
    elif report.report_type == 'scholarship_years_costs':
        report_data = generate_scholarship_years_costs_data(report.filters)

    # إنشاء ملف Excel
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)

    # إضافة ورقة عمل
    worksheet = workbook.add_worksheet(report.title[:31])  # تقييد الاسم بـ 31 حرف

    # تنسيقات الخلايا
    header_format = workbook.add_format({
        'bold': True,
        'align': 'center',
        'valign': 'vcenter',
        'bg_color': '#4472C4',
        'color': 'white',
        'border': 1
    })

    cell_format = workbook.add_format({
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })

    date_format = workbook.add_format({
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'num_format': 'yyyy-mm-dd'
    })

    money_format = workbook.add_format({
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'num_format': '#,##0.00'
    })

    # كتابة البيانات حسب نوع التقرير
    if report.report_type == 'budget_summary':
        export_budget_summary_excel(worksheet, report_data, header_format, cell_format, date_format, money_format)

    elif report.report_type == 'expense_summary':
        export_expense_summary_excel(worksheet, report_data, header_format, cell_format, date_format, money_format)

    elif report.report_type == 'monthly_expenses':
        export_monthly_expenses_excel(worksheet, report_data, header_format, cell_format, money_format)

    elif report.report_type == 'category_expenses':
        export_category_expenses_excel(worksheet, report_data, header_format, cell_format, money_format)

    elif report.report_type == 'budget_comparison':
        export_budget_comparison_excel(worksheet, report_data, header_format, cell_format, money_format)

    elif report.report_type == 'fiscal_year_summary':
        export_fiscal_year_summary_excel(worksheet, report_data, header_format, cell_format, money_format)

    elif report.report_type == 'scholarship_years_costs':
        export_scholarship_years_costs_excel(worksheet, report_data, header_format, cell_format, money_format)

    workbook.close()

    # إرسال الملف
    output.seek(0)
    report_name = report.title.replace(' ', '_')
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{report_name}.xlsx"'

    return response

@login_required
@permission_required('finance.view_financialreport', raise_exception=True)
def budget_summary_report(request):
    """تقرير ملخص الميزانية"""
    # الإعدادات الافتراضية
    fiscal_year = None
    start_date = None
    end_date = None

    # الحصول على قائمة السنوات المالية للاختيار منها
    fiscal_years = FiscalYear.objects.all().order_by('-year')

    if request.method == 'POST':
        form = DateRangeForm(request.POST)

        # التحقق من وجود سنة مالية محددة
        fiscal_year_id = request.POST.get('fiscal_year')
        if fiscal_year_id:
            try:
                fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
            except FiscalYear.DoesNotExist:
                fiscal_year = None

        if form.is_valid():
            filters = {
                'start_date': form.cleaned_data['start_date'],
                'end_date': form.cleaned_data['end_date'],
                'fiscal_year_id': fiscal_year_id if fiscal_year else None,
            }
            report_data = generate_budget_summary_data(filters)

            # حفظ القيم لإعادة عرضها
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
        else:
            # في حالة وجود سنة مالية فقط
            if fiscal_year:
                filters = {
                    'fiscal_year_id': fiscal_year.id,
                    'start_date': fiscal_year.start_date,
                    'end_date': fiscal_year.end_date,
                }
                report_data = generate_budget_summary_data(filters)

                # حفظ القيم لإعادة عرضها
                start_date = fiscal_year.start_date
                end_date = fiscal_year.end_date
            else:
                # في حالة عدم وجود أي فلتر صالح
                report_data = generate_budget_summary_data({})
    else:
        # في حالة وجود سنة مالية في الاستعلام
        fiscal_year_id = request.GET.get('fiscal_year')
        if fiscal_year_id:
            try:
                fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
                # تعيين القيم الافتراضية للنموذج
                form = DateRangeForm(initial={
                    'start_date': fiscal_year.start_date,
                    'end_date': fiscal_year.end_date,
                })

                # إنشاء التقرير باستخدام السنة المالية
                filters = {
                    'fiscal_year_id': fiscal_year.id,
                    'start_date': fiscal_year.start_date,
                    'end_date': fiscal_year.end_date,
                }
                report_data = generate_budget_summary_data(filters)

                # حفظ القيم لإعادة عرضها
                start_date = fiscal_year.start_date
                end_date = fiscal_year.end_date
            except FiscalYear.DoesNotExist:
                form = DateRangeForm()
                report_data = generate_budget_summary_data({})
        else:
            form = DateRangeForm()
            report_data = generate_budget_summary_data({})

    context = {
        'form': form,
        'report_data': report_data,
        'fiscal_years': fiscal_years,
        'selected_fiscal_year': fiscal_year,
        'start_date': start_date,
        'end_date': end_date,
        'report_type': 'budget_summary',
        'report_title': _('تقرير ملخص الميزانية'),
    }
    return render(request, 'finance/reports/budget_summary.html', context)

@login_required
@permission_required('finance.view_financialreport', raise_exception=True)
def expense_summary_report(request):
    """تقرير ملخص المصروفات"""
    # الإعدادات الافتراضية
    fiscal_year = None

    # الحصول على قائمة السنوات المالية والفئات للاختيار منها
    fiscal_years = FiscalYear.objects.all().order_by('-year')
    categories = ExpenseCategory.objects.all().order_by('name')

    if request.method == 'POST':
        form = ExpenseFilterForm(request.POST)

        # التحقق من وجود سنة مالية محددة
        fiscal_year_id = request.POST.get('fiscal_year')
        if fiscal_year_id:
            try:
                fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
            except FiscalYear.DoesNotExist:
                fiscal_year = None

        if form.is_valid():
            filters = {
                'status': form.cleaned_data['status'],
                'category': form.cleaned_data['category'].id if form.cleaned_data['category'] else None,
                'start_date': form.cleaned_data['start_date'],
                'end_date': form.cleaned_data['end_date'],
                'fiscal_year_id': fiscal_year_id if fiscal_year else None,
            }
            report_data = generate_expense_summary_data(filters)
        else:
            # في حالة وجود سنة مالية فقط
            if fiscal_year:
                filters = {
                    'fiscal_year_id': fiscal_year.id,
                    'start_date': fiscal_year.start_date,
                    'end_date': fiscal_year.end_date,
                }
                report_data = generate_expense_summary_data(filters)
            else:
                # في حالة عدم وجود أي فلتر صالح
                report_data = generate_expense_summary_data({})
    else:
        form = ExpenseFilterForm()

        # في حالة وجود سنة مالية في الاستعلام
        fiscal_year_id = request.GET.get('fiscal_year')
        if fiscal_year_id:
            try:
                fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
                # تعيين القيم الافتراضية للنموذج
                form = ExpenseFilterForm(initial={
                    'fiscal_year': fiscal_year,
                    'start_date': fiscal_year.start_date,
                    'end_date': fiscal_year.end_date,
                })

                # إنشاء التقرير باستخدام السنة المالية
                filters = {
                    'fiscal_year_id': fiscal_year.id,
                    'start_date': fiscal_year.start_date,
                    'end_date': fiscal_year.end_date,
                }
                report_data = generate_expense_summary_data(filters)
            except FiscalYear.DoesNotExist:
                report_data = generate_expense_summary_data({})
        else:
            report_data = generate_expense_summary_data({})

    context = {
        'form': form,
        'report_data': report_data,
        'fiscal_years': fiscal_years,
        'categories': categories,
        'selected_fiscal_year': fiscal_year,
        'report_type': 'expense_summary',
        'report_title': _('تقرير ملخص المصروفات'),
    }
    return render(request, 'finance/reports/expense_summary.html', context)

@login_required
@permission_required('finance.view_financialreport', raise_exception=True)
def monthly_expenses_report(request):
    """تقرير المصروفات الشهرية"""
    years = list(range(timezone.now().year - 5, timezone.now().year + 1))
    fiscal_years = FiscalYear.objects.all().order_by('-year')

    # الإعدادات الافتراضية
    fiscal_year = None
    selected_year = timezone.now().year

    if request.method == 'POST':
        year = request.POST.get('year', selected_year)

        # التحقق من وجود سنة مالية محددة
        fiscal_year_id = request.POST.get('fiscal_year')
        if fiscal_year_id:
            try:
                fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
                filters = {
                    'year': year,
                    'fiscal_year_id': fiscal_year.id,
                }
            except FiscalYear.DoesNotExist:
                filters = {'year': year}
        else:
            filters = {'year': year}

        report_data = generate_monthly_expenses_data(filters)
        selected_year = int(year)
    else:
        # في حالة وجود سنة مالية في الاستعلام
        fiscal_year_id = request.GET.get('fiscal_year')
        if fiscal_year_id:
            try:
                fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
                filters = {
                    'year': fiscal_year.year,
                    'fiscal_year_id': fiscal_year.id,
                }
                selected_year = fiscal_year.year
            except FiscalYear.DoesNotExist:
                filters = {'year': selected_year}
        else:
            filters = {'year': selected_year}

        report_data = generate_monthly_expenses_data(filters)

    context = {
        'years': years,
        'fiscal_years': fiscal_years,
        'selected_year': selected_year,
        'selected_fiscal_year': fiscal_year,
        'report_data': report_data,
        'report_type': 'monthly_expenses',
        'report_title': _('تقرير المصروفات الشهرية'),
    }
    return render(request, 'finance/reports/monthly_expenses.html', context)

@login_required
@permission_required('finance.view_financialreport', raise_exception=True)
def category_expenses_report(request):
    """تقرير المصروفات حسب الفئة"""
    # الإعدادات الافتراضية
    fiscal_year = None
    fiscal_years = FiscalYear.objects.all().order_by('-year')

    if request.method == 'POST':
        form = DateRangeForm(request.POST)

        # التحقق من وجود سنة مالية محددة
        fiscal_year_id = request.POST.get('fiscal_year')
        if fiscal_year_id:
            try:
                fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
            except FiscalYear.DoesNotExist:
                fiscal_year = None

        if form.is_valid():
            filters = {
                'start_date': form.cleaned_data['start_date'],
                'end_date': form.cleaned_data['end_date'],
                'fiscal_year_id': fiscal_year_id if fiscal_year else None,
            }
            report_data = generate_category_expenses_data(filters)
        else:
            # في حالة وجود سنة مالية فقط
            if fiscal_year:
                filters = {
                    'fiscal_year_id': fiscal_year.id,
                    'start_date': fiscal_year.start_date,
                    'end_date': fiscal_year.end_date,
                }
                report_data = generate_category_expenses_data(filters)
            else:
                # في حالة عدم وجود أي فلتر صالح
                report_data = generate_category_expenses_data({})
    else:
        form = DateRangeForm()

        # في حالة وجود سنة مالية في الاستعلام
        fiscal_year_id = request.GET.get('fiscal_year')
        if fiscal_year_id:
            try:
                fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
                # تعيين القيم الافتراضية للنموذج
                form = DateRangeForm(initial={
                    'start_date': fiscal_year.start_date,
                    'end_date': fiscal_year.end_date,
                })

                # إنشاء التقرير باستخدام السنة المالية
                filters = {
                    'fiscal_year_id': fiscal_year.id,
                    'start_date': fiscal_year.start_date,
                    'end_date': fiscal_year.end_date,
                }
                report_data = generate_category_expenses_data(filters)
            except FiscalYear.DoesNotExist:
                report_data = generate_category_expenses_data({})
        else:
            report_data = generate_category_expenses_data({})

    context = {
        'form': form,
        'report_data': report_data,
        'fiscal_years': fiscal_years,
        'selected_fiscal_year': fiscal_year,
        'report_type': 'category_expenses',
        'report_title': _('تقرير المصروفات حسب الفئة'),
    }
    return render(request, 'finance/reports/category_expenses.html', context)

@login_required
@permission_required('finance.view_financialreport', raise_exception=True)
def fiscal_year_summary_report(request):
    """تقرير ملخص السنة المالية"""
    # الحصول على قائمة السنوات المالية للاختيار منها
    fiscal_years = FiscalYear.objects.all().order_by('-year')

    # الإعدادات الافتراضية
    fiscal_year = None

    # البحث عن السنة المالية الحالية
    settings = ScholarshipSettings.objects.first()
    if settings and settings.current_fiscal_year:
        current_fiscal_year = settings.current_fiscal_year
    else:
        # في حالة عدم وجود إعدادات، استخدم أحدث سنة مالية مفتوحة
        current_fiscal_year = FiscalYear.objects.filter(status='open').order_by('-year').first()

    if request.method == 'POST':
        # التحقق من وجود سنة مالية محددة
        fiscal_year_id = request.POST.get('fiscal_year')
        if fiscal_year_id:
            try:
                fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
                filters = {'fiscal_year_id': fiscal_year.id}
                report_data = generate_fiscal_year_summary_data(filters)
            except FiscalYear.DoesNotExist:
                if current_fiscal_year:
                    fiscal_year = current_fiscal_year
                    filters = {'fiscal_year_id': current_fiscal_year.id}
                    report_data = generate_fiscal_year_summary_data(filters)
                else:
                    filters = {}
                    report_data = generate_fiscal_year_summary_data(filters)
        else:
            if current_fiscal_year:
                fiscal_year = current_fiscal_year
                filters = {'fiscal_year_id': current_fiscal_year.id}
                report_data = generate_fiscal_year_summary_data(filters)
            else:
                filters = {}
                report_data = generate_fiscal_year_summary_data(filters)
    else:
        # في حالة وجود سنة مالية في الاستعلام
        fiscal_year_id = request.GET.get('fiscal_year')
        if fiscal_year_id:
            try:
                fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
                filters = {'fiscal_year_id': fiscal_year.id}
                report_data = generate_fiscal_year_summary_data(filters)
            except FiscalYear.DoesNotExist:
                if current_fiscal_year:
                    fiscal_year = current_fiscal_year
                    filters = {'fiscal_year_id': current_fiscal_year.id}
                    report_data = generate_fiscal_year_summary_data(filters)
                else:
                    filters = {}
                    report_data = generate_fiscal_year_summary_data(filters)
        else:
            if current_fiscal_year:
                fiscal_year = current_fiscal_year
                filters = {'fiscal_year_id': current_fiscal_year.id}
                report_data = generate_fiscal_year_summary_data(filters)
            else:
                filters = {}
                report_data = generate_fiscal_year_summary_data(filters)

    context = {
        'fiscal_years': fiscal_years,
        'selected_fiscal_year': fiscal_year,
        'current_fiscal_year': current_fiscal_year,
        'report_data': report_data,
        'report_type': 'fiscal_year_summary',
        'report_title': _('تقرير ملخص السنة المالية'),
    }
    return render(request, 'finance/reports/fiscal_year_summary.html', context)

def generate_budget_summary_data(filters):
    """توليد بيانات تقرير ملخص الميزانية"""
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    fiscal_year_id = filters.get('fiscal_year_id')

    # إنشاء استعلام أساسي
    budgets_query = ScholarshipBudget.objects.all()

    # تطبيق الفلاتر
    if fiscal_year_id:
        budgets_query = budgets_query.filter(fiscal_year_id=fiscal_year_id)
    else:
        if start_date:
            budgets_query = budgets_query.filter(start_date__gte=start_date)
        if end_date:
            budgets_query = budgets_query.filter(end_date__lte=end_date)

    # حساب الإجماليات
    total_budget = budgets_query.aggregate(total=Sum('total_amount'))['total'] or 0

    # حساب المصروفات لكل ميزانية
    budgets_data = []
    for budget in budgets_query:
        spent_amount = budget.get_spent_amount()
        remaining_amount = budget.get_remaining_amount()
        spent_percentage = budget.get_spent_percentage()

        budgets_data.append({
            'id': budget.id,
            'applicant': budget.application.applicant.get_full_name(),
            'scholarship': budget.application.scholarship.title,
            'fiscal_year': budget.fiscal_year.year if budget.fiscal_year else None,
            'total_amount': budget.total_amount,
            'spent_amount': spent_amount,
            'remaining_amount': remaining_amount,
            'spent_percentage': spent_percentage,
            'start_date': budget.start_date,
            'end_date': budget.end_date,
            'status': budget.get_status_display(),
        })

    # إجماليات عامة
    total_spent = sum(item['spent_amount'] for item in budgets_data)
    total_remaining = sum(item['remaining_amount'] for item in budgets_data)

    # بيانات لرسم بياني دائري
    pie_chart_data = [
        {'name': _('المبلغ المصروف'), 'value': total_spent},
        {'name': _('المبلغ المتبقي'), 'value': total_remaining},
    ]

    return {
        'budgets': budgets_data,
        'total_budget': total_budget,
        'total_spent': total_spent,
        'total_remaining': total_remaining,
        'pie_chart_data': pie_chart_data,
        'filters': filters,
    }

def generate_expense_summary_data(filters):
    """توليد بيانات تقرير ملخص المصروفات"""
    status = filters.get('status')
    category = filters.get('category')
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    fiscal_year_id = filters.get('fiscal_year_id')

    # إنشاء استعلام أساسي
    expenses_query = Expense.objects.all()

    # تطبيق الفلاتر
    if fiscal_year_id:
        expenses_query = expenses_query.filter(fiscal_year_id=fiscal_year_id)
    else:
        if start_date:
            expenses_query = expenses_query.filter(date__gte=start_date)
        if end_date:
            expenses_query = expenses_query.filter(date__lte=end_date)

    if status:
        expenses_query = expenses_query.filter(status=status)
    if category:
        expenses_query = expenses_query.filter(category_id=category)

    # حساب الإجماليات
    total_amount = expenses_query.aggregate(total=Sum('amount'))['total'] or 0

    # جمع البيانات عن المصروفات
    expenses_data = []
    for expense in expenses_query.select_related('budget__application__applicant', 'category', 'fiscal_year'):
        expenses_data.append({
            'id': expense.id,
            'applicant': expense.budget.application.applicant.get_full_name(),
            'category': expense.category.name,
            'fiscal_year': expense.fiscal_year.year if expense.fiscal_year else None,
            'amount': expense.amount,
            'date': expense.date,
            'status': expense.get_status_display(),
            'description': expense.description,
        })

    # تجميع المصروفات حسب الفئة
    expenses_by_category = expenses_query.values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')

    # تجميع المصروفات حسب الحالة
    expenses_by_status = expenses_query.values('status').annotate(
        total=Sum('amount'), count=Count('id')
    ).order_by('status')

    # تحويل المصروفات حسب الحالة إلى تنسيق مناسب للرسم البياني
    status_chart_data = []
    for item in expenses_by_status:
        status_display = dict(Expense.STATUS_CHOICES).get(item['status'])
        status_chart_data.append({
            'name': status_display,
            'value': float(item['total']),
            'count': item['count'],
        })

    return {
        'expenses': expenses_data,
        'total_amount': total_amount,
        'expenses_by_category': expenses_by_category,
        'status_chart_data': status_chart_data,
        'filters': filters,
    }

def generate_monthly_expenses_data(filters):
    """توليد بيانات تقرير المصروفات الشهرية"""
    year = int(filters.get('year', timezone.now().year))
    fiscal_year_id = filters.get('fiscal_year_id')

    # الحصول على المصروفات في العام المحدد
    expenses_query = Expense.objects.filter(
        date__year=year,
        status='approved'
    )

    # تطبيق فلتر السنة المالية
    if fiscal_year_id:
        expenses_query = expenses_query.filter(fiscal_year_id=fiscal_year_id)

    expenses = expenses_query.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')

    # تجهيز بيانات شهرية كاملة (مع إضافة الأشهر بدون مصروفات)
    monthly_data = []
    for month in range(1, 13):
        month_date = datetime.date(year, month, 1)
        month_name = month_date.strftime('%B')  # اسم الشهر

        # البحث عن المصروفات في هذا الشهر
        month_expense = next(
            (item for item in expenses if item['month'].month == month),
            {'total': 0}
        )

        monthly_data.append({
            'month': month_name,
            'month_number': month,
            'total': month_expense['total'],
        })

    # حساب إجمالي المصروفات للعام
    total_year_expenses = sum(item['total'] for item in monthly_data)

    # حساب المتوسط الشهري
    monthly_average = total_year_expenses / 12 if total_year_expenses > 0 else 0

    return {
        'monthly_data': monthly_data,
        'total_year_expenses': total_year_expenses,
        'monthly_average': monthly_average,
        'year': year,
        'fiscal_year_id': fiscal_year_id,
    }

def generate_category_expenses_data(filters):
    """توليد بيانات تقرير المصروفات حسب الفئة"""
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    fiscal_year_id = filters.get('fiscal_year_id')

    # إنشاء استعلام أساسي
    expenses_query = Expense.objects.filter(status='approved')

    # تطبيق الفلاتر
    if fiscal_year_id:
        expenses_query = expenses_query.filter(fiscal_year_id=fiscal_year_id)
    else:
        if start_date:
            expenses_query = expenses_query.filter(date__gte=start_date)
        if end_date:
            expenses_query = expenses_query.filter(date__lte=end_date)

    # تجميع المصروفات حسب الفئة
    category_data = expenses_query.values('category__name').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')

    # حساب الإجمالي
    total_amount = sum(item['total'] for item in category_data)

    # إضافة النسبة المئوية لكل فئة
    for item in category_data:
        item['percentage'] = (item['total'] / total_amount * 100) if total_amount > 0 else 0

    # تحويل البيانات لتنسيق مناسب للرسم البياني
    chart_data = [
        {
            'name': item['category__name'],
            'value': float(item['total']),
            'percentage': float(item['percentage']),
        }
        for item in category_data
    ]

    return {
        'category_data': category_data,
        'total_amount': total_amount,
        'chart_data': chart_data,
        'filters': filters,
    }

def generate_fiscal_year_summary_data(filters):
    """توليد بيانات تقرير ملخص السنة المالية"""
    fiscal_year_id = filters.get('fiscal_year_id')

    if not fiscal_year_id:
        # في حالة عدم وجود سنة مالية، استخدم السنة المالية الحالية
        settings = ScholarshipSettings.objects.first()
        if settings and settings.current_fiscal_year:
            fiscal_year_id = settings.current_fiscal_year.id
        else:
            # في حالة عدم وجود إعدادات، استخدم أحدث سنة مالية مفتوحة
            fiscal_year = FiscalYear.objects.filter(status='open').order_by('-year').first()
            if fiscal_year:
                fiscal_year_id = fiscal_year.id

    # الحصول على السنة المالية
    try:
        fiscal_year = FiscalYear.objects.get(id=fiscal_year_id) if fiscal_year_id else None
    except FiscalYear.DoesNotExist:
        fiscal_year = None

    if not fiscal_year:
        return {
            'fiscal_year': None,
            'budgets': [],
            'expenses': [],
            'expenses_by_category': [],
            'monthly_expenses': [],
            'total_budget': 0,
            'total_spent': 0,
            'total_remaining': 0,
            'spent_percentage': 0,
        }

    # البيانات المحسوبة
    spent_amount = fiscal_year.get_spent_amount()
    remaining_amount = fiscal_year.get_remaining_amount()
    spent_percentage = fiscal_year.get_spent_percentage()

    # الميزانيات المرتبطة بهذه السنة المالية
    budgets = ScholarshipBudget.objects.filter(fiscal_year=fiscal_year)

    # المصروفات في هذه السنة المالية
    expenses = Expense.objects.filter(fiscal_year=fiscal_year).order_by('-date')

    # المصروفات في هذه السنة المالية حسب الفئة
    expenses_by_category = Expense.objects.filter(
        fiscal_year=fiscal_year,
        status='approved'
    ).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')

    # المصروفات الشهرية في هذه السنة المالية
    monthly_expenses = Expense.objects.filter(
        fiscal_year=fiscal_year,
        status='approved'
    ).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')

    # تحويل البيانات الشهرية إلى تنسيق مناسب
    months_data = []
    for month in range(1, 13):
        month_date = datetime.date(fiscal_year.year, month, 1)
        month_name = month_date.strftime('%B')  # اسم الشهر

        # البحث عن المصروفات في هذا الشهر
        month_expense = next(
            (item for item in monthly_expenses if item['month'].month == month),
            {'total': 0}
        )

        months_data.append({
            'month': month_name,
            'month_number': month,
            'total': month_expense['total'],
        })

    return {
        'fiscal_year': fiscal_year,
        'budgets': budgets,
        'expenses': expenses[:10],  # عرض آخر 10 مصروفات فقط
        'expenses_by_category': expenses_by_category,
        'monthly_expenses': months_data,
        'total_budget': fiscal_year.total_budget,
        'total_spent': spent_amount,
        'total_remaining': remaining_amount,
        'spent_percentage': spent_percentage,
    }


def export_fiscal_year_summary_excel(worksheet, data, header_format, cell_format, money_format):
    """تصدير تقرير ملخص السنة المالية إلى Excel"""
    # التحقق من وجود سنة مالية
    if not data.get('fiscal_year'):
        worksheet.write(0, 0, _("لا توجد سنة مالية محددة"), header_format)
        return

    fiscal_year = data['fiscal_year']

    # كتابة عنوان التقرير
    worksheet.merge_range(0, 0, 0, 5, _("تقرير ملخص السنة المالية") + f" {fiscal_year.year}", header_format)

    # كتابة معلومات السنة المالية
    worksheet.write(1, 0, _("السنة المالية"), header_format)
    worksheet.write(1, 1, fiscal_year.year, cell_format)
    worksheet.write(1, 2, _("الحالة"), header_format)
    worksheet.write(1, 3, fiscal_year.get_status_display(), cell_format)
    worksheet.write(1, 4, _("الفترة"), header_format)
    worksheet.write(1, 5, f"{fiscal_year.start_date} - {fiscal_year.end_date}", cell_format)

    # كتابة إجماليات السنة المالية
    worksheet.write(3, 0, _("ملخص السنة المالية"), header_format)
    worksheet.merge_range(3, 0, 3, 5, _("ملخص السنة المالية"), header_format)

    worksheet.write(4, 0, _("إجمالي الميزانية"), header_format)
    worksheet.write(4, 1, data['total_budget'], money_format)
    worksheet.write(4, 2, _("إجمالي المصروفات"), header_format)
    worksheet.write(4, 3, data['total_spent'], money_format)
    worksheet.write(4, 4, _("نسبة الصرف"), header_format)
    worksheet.write(4, 5, f"{data['spent_percentage']:.2f}%", cell_format)

    worksheet.write(5, 0, _("المبلغ المتبقي"), header_format)
    worksheet.write(5, 1, data['total_remaining'], money_format)

    # كتابة المصروفات الشهرية
    worksheet.write(7, 0, _("المصروفات الشهرية"), header_format)
    worksheet.merge_range(7, 0, 7, 5, _("المصروفات الشهرية"), header_format)

    # عناوين الأعمدة للمصروفات الشهرية
    worksheet.write(8, 0, _("الشهر"), header_format)
    worksheet.write(8, 1, _("المبلغ"), header_format)
    worksheet.write(8, 3, _("الشهر"), header_format)
    worksheet.write(8, 4, _("المبلغ"), header_format)

    # كتابة بيانات المصروفات الشهرية في عمودين (6 أشهر في كل عمود)
    monthly_data = data.get('monthly_expenses', [])
    for i, month_data in enumerate(monthly_data[:6]):
        worksheet.write(9 + i, 0, month_data['month'], cell_format)
        worksheet.write(9 + i, 1, month_data['total'], money_format)

    for i, month_data in enumerate(monthly_data[6:]):
        worksheet.write(9 + i, 3, month_data['month'], cell_format)
        worksheet.write(9 + i, 4, month_data['total'], money_format)

    # كتابة المصروفات حسب الفئة
    start_row = 17  # بعد المصروفات الشهرية
    worksheet.write(start_row, 0, _("المصروفات حسب الفئة"), header_format)
    worksheet.merge_range(start_row, 0, start_row, 5, _("المصروفات حسب الفئة"), header_format)

    # عناوين الأعمدة للمصروفات حسب الفئة
    worksheet.write(start_row + 1, 0, _("الفئة"), header_format)
    worksheet.write(start_row + 1, 1, _("المبلغ"), header_format)
    worksheet.write(start_row + 1, 2, _("النسبة من الإجمالي"), header_format)

    # كتابة بيانات المصروفات حسب الفئة
    expenses_by_category = data.get('expenses_by_category', [])
    total_expenses = data['total_spent'] or 1  # لتجنب القسمة على صفر

    for i, category in enumerate(expenses_by_category):
        worksheet.write(start_row + 2 + i, 0, category['category__name'], cell_format)
        worksheet.write(start_row + 2 + i, 1, category['total'], money_format)
        percentage = (category['total'] / total_expenses) * 100
        worksheet.write(start_row + 2 + i, 2, f"{percentage:.2f}%", cell_format)

    # كتابة معلومات الميزانيات
    start_row = start_row + 3 + len(expenses_by_category)  # بعد المصروفات حسب الفئة
    worksheet.write(start_row, 0, _("الميزانيات في السنة المالية"), header_format)
    worksheet.merge_range(start_row, 0, start_row, 5, _("الميزانيات في السنة المالية"), header_format)

    # عناوين الأعمدة للميزانيات
    worksheet.write(start_row + 1, 0, _("المبتعث"), header_format)
    worksheet.write(start_row + 1, 1, _("إجمالي الميزانية"), header_format)
    worksheet.write(start_row + 1, 2, _("المصروفات"), header_format)
    worksheet.write(start_row + 1, 3, _("المتبقي"), header_format)
    worksheet.write(start_row + 1, 4, _("نسبة الصرف"), header_format)
    worksheet.write(start_row + 1, 5, _("الحالة"), header_format)

    # كتابة بيانات الميزانيات
    budgets = data.get('budgets', [])
    for i, budget in enumerate(budgets):
        # حساب المصروفات والمتبقي ونسبة الصرف
        spent_amount = budget.get_spent_amount()
        remaining_amount = budget.get_remaining_amount()
        if budget.total_amount > 0:
            spent_percentage = (spent_amount / budget.total_amount) * 100
        else:
            spent_percentage = 0

        worksheet.write(start_row + 2 + i, 0, budget.application.applicant.get_full_name(), cell_format)
        worksheet.write(start_row + 2 + i, 1, budget.total_amount, money_format)
        worksheet.write(start_row + 2 + i, 2, spent_amount, money_format)
        worksheet.write(start_row + 2 + i, 3, remaining_amount, money_format)
        worksheet.write(start_row + 2 + i, 4, f"{spent_percentage:.2f}%", cell_format)
        worksheet.write(start_row + 2 + i, 5, budget.get_status_display(), cell_format)

    # تنسيق الأعمدة
    worksheet.set_column(0, 0, 25)  # عمود الاسم/الفئة
    worksheet.set_column(1, 1, 15)  # عمود المبلغ
    worksheet.set_column(2, 2, 18)  # عمود النسبة/إجمالي الميزانية
    worksheet.set_column(3, 3, 15)  # عمود الشهر/المتبقي
    worksheet.set_column(4, 4, 15)  # عمود المبلغ/نسبة الصرف
    worksheet.set_column(5, 5, 15)  # عمود الحالة


@login_required
def api_budget_summary(request):
    """API لبيانات ملخص الميزانية"""
    # الحصول على معلمات الاستعلام
    fiscal_year_id = request.GET.get('fiscal_year')

    if fiscal_year_id:
        try:
            fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
            filters = {
                'fiscal_year_id': fiscal_year_id,
                'start_date': fiscal_year.start_date,
                'end_date': fiscal_year.end_date,
            }
        except FiscalYear.DoesNotExist:
            filters = {}
    else:
        # البحث عن السنة المالية الحالية
        settings = ScholarshipSettings.objects.first()
        if settings and settings.current_fiscal_year:
            fiscal_year = settings.current_fiscal_year
            filters = {
                'fiscal_year_id': fiscal_year.id,
                'start_date': fiscal_year.start_date,
                'end_date': fiscal_year.end_date,
            }
        else:
            filters = {}

    # حساب إجماليات الميزانية والمصروفات
    report_data = generate_budget_summary_data(filters)

    total_budget = report_data['total_budget']
    total_spent = report_data['total_spent']
    total_remaining = report_data['total_remaining']

    # بيانات الرسم البياني
    pie_data = [
        {'name': _('المبلغ المصروف'), 'value': float(total_spent)},
        {'name': _('المبلغ المتبقي'), 'value': float(total_remaining)},
    ]

    # بيانات الرسم البياني للميزانيات
    budgets_data = []
    for budget in report_data['budgets'][:10]:  # اعرض أعلى 10 ميزانيات فقط
        budgets_data.append({
            'name': budget['applicant'],
            'total': float(budget['total_amount']),
            'spent': float(budget['spent_amount']),
            'remaining': float(budget['remaining_amount']),
            'percentage': float(budget['spent_percentage']),
        })

    return JsonResponse({
        'pie_data': pie_data,
        'budgets_data': budgets_data,
        'total_budget': float(total_budget),
        'total_spent': float(total_spent),
        'total_remaining': float(total_remaining),
        'spent_percentage': float(total_spent / total_budget * 100) if total_budget > 0 else 0,
    })

@login_required
def api_expense_categories(request):
    """API لبيانات المصروفات حسب الفئة"""
    # الحصول على معلمات الاستعلام
    fiscal_year_id = request.GET.get('fiscal_year')

    # إنشاء استعلام أساسي
    expenses_query = Expense.objects.filter(status='approved')

    # تطبيق فلتر السنة المالية
    if fiscal_year_id:
        try:
            fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
            expenses_query = expenses_query.filter(fiscal_year=fiscal_year)
        except FiscalYear.DoesNotExist:
            pass
    else:
        # البحث عن السنة المالية الحالية
        settings = ScholarshipSettings.objects.first()
        if settings and settings.current_fiscal_year:
            expenses_query = expenses_query.filter(fiscal_year=settings.current_fiscal_year)

    # تجميع المصروفات حسب الفئة
    expenses_by_category = expenses_query.values(
        'category__name'
    ).annotate(
        total=Sum('amount')
    ).order_by('-total')

    # تحويل البيانات لتنسيق مناسب للرسم البياني
    category_data = [
        {'name': item['category__name'], 'value': float(item['total'])}
        for item in expenses_by_category
    ]

    return JsonResponse({'data': category_data})

@login_required
def api_monthly_expenses(request):
    """API لبيانات المصروفات الشهرية"""
    # الحصول على معلمات الاستعلام
    fiscal_year_id = request.GET.get('fiscal_year')
    year = request.GET.get('year', timezone.now().year)

    # استعلام أساسي
    expenses_query = Expense.objects.filter(
        date__year=year,
        status='approved'
    )

    # تطبيق فلتر السنة المالية
    if fiscal_year_id:
        try:
            fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
            expenses_query = expenses_query.filter(fiscal_year=fiscal_year)
        except FiscalYear.DoesNotExist:
            pass
    else:
        # البحث عن السنة المالية الحالية
        settings = ScholarshipSettings.objects.first()
        if settings and settings.current_fiscal_year:
            expenses_query = expenses_query.filter(fiscal_year=settings.current_fiscal_year)

    # الحصول على المصروفات الشهرية
    expenses = expenses_query.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')

    # تجهيز بيانات شهرية كاملة
    monthly_data = []
    for month in range(1, 13):
        month_date = datetime.date(int(year), month, 1)
        month_name = month_date.strftime('%B')  # اسم الشهر

        # البحث عن المصروفات في هذا الشهر
        month_expense = next(
            (item for item in expenses if item['month'].month == month),
            {'total': 0}
        )

        monthly_data.append({
            'month': month_name,
            'value': float(month_expense['total']),
        })

    return JsonResponse({'data': monthly_data})

@login_required
def api_budget_status(request):
    """API لبيانات حالة الميزانيات"""
    # الحصول على معلمات الاستعلام
    fiscal_year_id = request.GET.get('fiscal_year')

    # استعلام أساسي
    budgets_query = ScholarshipBudget.objects.all()

    # تطبيق فلتر السنة المالية
    if fiscal_year_id:
        try:
            fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
            budgets_query = budgets_query.filter(fiscal_year=fiscal_year)
        except FiscalYear.DoesNotExist:
            pass
    else:
        # البحث عن السنة المالية الحالية
        settings = ScholarshipSettings.objects.first()
        if settings and settings.current_fiscal_year:
            budgets_query = budgets_query.filter(fiscal_year=settings.current_fiscal_year)

    # عدد الميزانيات حسب الحالة
    budgets_by_status = budgets_query.values(
        'status'
    ).annotate(
        count=Count('id')
    )

    # تحويل البيانات لتنسيق مناسب للرسم البياني
    status_data = []
    for item in budgets_by_status:
        status_display = dict(ScholarshipBudget.STATUS_CHOICES).get(item['status'])
        status_data.append({
            'name': status_display,
            'value': item['count'],
        })

    return JsonResponse({'data': status_data})

@login_required
def api_fiscal_year_summary(request):
    """API لبيانات ملخص السنة المالية"""
    fiscal_year_id = request.GET.get('fiscal_year_id')

    if fiscal_year_id:
        try:
            fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
        except FiscalYear.DoesNotExist:
            # البحث عن السنة المالية الحالية
            settings = ScholarshipSettings.objects.first()
            if settings and settings.current_fiscal_year:
                fiscal_year = settings.current_fiscal_year
            else:
                # في حالة عدم وجود سنة مالية
                return JsonResponse({
                    'error': _('لا توجد سنة مالية محددة')
                })
    else:
        # البحث عن السنة المالية الحالية
        settings = ScholarshipSettings.objects.first()
        if settings and settings.current_fiscal_year:
            fiscal_year = settings.current_fiscal_year
        else:
            # البحث عن أحدث سنة مالية مفتوحة
            fiscal_year = FiscalYear.objects.filter(status='open').order_by('-year').first()

            if not fiscal_year:
                return JsonResponse({
                    'error': _('لا توجد سنة مالية مفتوحة')
                })

    # حساب إجماليات السنة المالية
    total_budget = fiscal_year.total_budget
    spent_amount = fiscal_year.get_spent_amount()
    remaining_amount = fiscal_year.get_remaining_amount()

    # بيانات الرسم البياني الدائري
    pie_data = [
        {'name': _('المبلغ المصروف'), 'value': float(spent_amount)},
        {'name': _('المبلغ المتبقي'), 'value': float(remaining_amount)},
    ]

    # المصروفات الشهرية
    monthly_expenses = Expense.objects.filter(
        fiscal_year=fiscal_year,
        status='approved'
    ).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')

    # تحويل البيانات الشهرية إلى تنسيق مناسب
    months_data = []
    for month in range(1, 13):
        month_date = datetime.date(fiscal_year.year, month, 1)
        month_name = month_date.strftime('%B')  # اسم الشهر

        # البحث عن المصروفات في هذا الشهر
        month_expense = next(
            (item for item in monthly_expenses if item['month'].month == month),
            {'total': 0}
        )

        months_data.append({
            'month': month_name,
            'value': float(month_expense['total']),
        })

    # المصروفات حسب الفئة
    category_expenses = Expense.objects.filter(
        fiscal_year=fiscal_year,
        status='approved'
    ).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')

    category_data = [
        {'name': item['category__name'], 'value': float(item['total'])}
        for item in category_expenses
    ]

    return JsonResponse({
        'fiscal_year': {
            'id': fiscal_year.id,
            'year': fiscal_year.year,
            'status': fiscal_year.status,
        },
        'pie_data': pie_data,
        'months_data': months_data,
        'category_data': category_data,
        'total_budget': float(total_budget),
        'spent_amount': float(spent_amount),
        'remaining_amount': float(remaining_amount),
        'spent_percentage': float((spent_amount / total_budget) * 100) if total_budget > 0 else 0,
    })

@login_required
@permission_required('finance.add_yearlyscholarshipcosts', raise_exception=True)
def add_scholarship_year(request, budget_id):
    """إضافة سنة جديدة لميزانية المبتعث"""
    budget = get_object_or_404(ScholarshipBudget, id=budget_id)

    # تحديد رقم السنة الجديدة
    next_year_number = YearlyScholarshipCosts.objects.filter(budget=budget).count() + 1

    # الحصول على قائمة السنوات المالية المفتوحة
    fiscal_years = FiscalYear.objects.filter(status='open').order_by('-year')

    # السنة المالية الافتراضية
    default_fiscal_year = None
    if budget.fiscal_year:
        default_fiscal_year = budget.fiscal_year
    else:
        # البحث عن السنة المالية الحالية
        settings = ScholarshipSettings.objects.first()
        if settings and settings.current_fiscal_year:
            default_fiscal_year = settings.current_fiscal_year

    if request.method == 'POST':
        form = YearlyScholarshipCostsForm(request.POST)
        if form.is_valid():
            yearly_cost = form.save(commit=False)
            yearly_cost.budget = budget

            # تعيين السنة المالية إذا تم اختيارها
            if form.cleaned_data.get('fiscal_year'):
                yearly_cost.fiscal_year = form.cleaned_data['fiscal_year']
            elif default_fiscal_year:
                yearly_cost.fiscal_year = default_fiscal_year

            yearly_cost.save()

            # إنشاء سجل للعملية
            FinancialLog.objects.create(
                budget=budget,
                fiscal_year=yearly_cost.fiscal_year,
                action_type='create',
                description=_("إضافة سنة دراسية جديدة للابتعاث") + f" - {yearly_cost.year_number}",
                created_by=request.user
            )

            messages.success(request, _("تمت إضافة السنة الدراسية بنجاح"))
            return redirect('finance:budget_detail', budget_id=budget.id)
    else:
        # القيم الافتراضية حسب تقرير PDF المرفق
        academic_year_parts = budget.academic_year.split('-')
        next_academic_year = f"{int(academic_year_parts[0]) + next_year_number - 1}-{int(academic_year_parts[1]) + next_year_number - 1}"

        initial_data = {
            'year_number': next_year_number,
            'academic_year': next_academic_year,
            'monthly_allowance': 1000,
            'monthly_duration': 12,
            'fiscal_year': default_fiscal_year,
        }

        # القيم الافتراضية تختلف حسب السنة
        if next_year_number == 1:
            initial_data.update({
                'travel_tickets': 1100,
                'visa_fees': 358,
                'health_insurance': 500,
                'tuition_fees_foreign': 22350,
            })
        else:
            initial_data.update({
                'travel_tickets': 0,
                'visa_fees': 0,
                'health_insurance': 0,
                'tuition_fees_foreign': 22350,
            })

        form = YearlyScholarshipCostsForm(initial=initial_data)

    context = {
        'form': form,
        'budget': budget,
        'next_year_number': next_year_number,
        'fiscal_years': fiscal_years,
        'default_fiscal_year': default_fiscal_year,
    }
    return render(request, 'finance/scholarship_year_form.html', context)

@login_required
@permission_required('finance.change_scholarshipbudget', raise_exception=True)
def close_current_year_open_new(request, budget_id):
    """إغلاق السنة الدراسية الحالية وفتح سنة جديدة"""
    budget = get_object_or_404(ScholarshipBudget, id=budget_id)

    # الحصول على قائمة السنوات المالية المفتوحة
    fiscal_years = FiscalYear.objects.filter(status='open').order_by('-year')

    # التحقق من أن الميزانية الحالية نشطة
    if budget.status != 'active':
        messages.error(request, _("لا يمكن إغلاق وفتح سنة جديدة لميزانية غير نشطة"))
        return redirect('finance:budget_detail', budget_id=budget_id)

    # التحقق من أن الميزانية الحالية هي السنة الحالية
    if not budget.is_current:
        messages.error(request, _("لا يمكن إغلاق وفتح سنة جديدة لميزانية ليست السنة الحالية"))
        return redirect('finance:budget_detail', budget_id=budget_id)

    if request.method == 'POST':
        # تحديث السنة الحالية
        current_year = budget.academic_year
        year_parts = current_year.split('-')
        next_year = f"{int(year_parts[0])+1}-{int(year_parts[1])+1}"

        # إغلاق السنة الحالية
        budget.is_current = False
        budget.status = 'closed'
        budget.save()

        # إنشاء سجل للعملية - إغلاق السنة الحالية
        FinancialLog.objects.create(
            budget=budget,
            fiscal_year=budget.fiscal_year,
            action_type='close',
            description=_("إغلاق السنة الدراسية الحالية") + f" - {current_year}",
            created_by=request.user
        )

        # الحصول على السنة المالية للسنة الجديدة
        fiscal_year_id = request.POST.get('fiscal_year')
        fiscal_year = None

        if fiscal_year_id:
            try:
                fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
            except FiscalYear.DoesNotExist:
                fiscal_year = budget.fiscal_year
        else:
            fiscal_year = budget.fiscal_year

        # إنشاء ميزانية جديدة للسنة التالية
        new_budget = ScholarshipBudget.objects.create(
            application=budget.application,
            fiscal_year=fiscal_year,
            total_amount=budget.total_amount,  # يمكن تغييره حسب الحاجة
            start_date=budget.end_date + datetime.timedelta(days=1),
            end_date=budget.end_date + datetime.timedelta(days=365),
            created_by=request.user,
            tuition_fees=budget.tuition_fees,
            monthly_stipend=budget.monthly_stipend,
            travel_allowance=budget.travel_allowance,
            health_insurance=budget.health_insurance,
            books_allowance=budget.books_allowance,
            research_allowance=budget.research_allowance,
            conference_allowance=budget.conference_allowance,
            other_expenses=budget.other_expenses,
            academic_year=next_year,
            exchange_rate=budget.exchange_rate,
            foreign_currency=budget.foreign_currency,
            is_current=True
        )

        # إنشاء سجل للعملية - فتح سنة جديدة
        FinancialLog.objects.create(
            budget=new_budget,
            fiscal_year=fiscal_year,
            action_type='create',
            description=_("فتح سنة دراسية جديدة") + f" - {next_year}",
            created_by=request.user
        )

        messages.success(request, f"تم إغلاق السنة {current_year} وفتح سنة جديدة {next_year} بنجاح")
        return redirect('finance:budget_detail', budget_id=new_budget.id)

    context = {
        'budget': budget,
        'fiscal_years': fiscal_years,
    }
    return render(request, 'finance/close_year_confirm.html', context)

@login_required
@permission_required('finance.view_scholarshipbudget', raise_exception=True)
def scholarship_years_costs_report(request, budget_id):
    """عرض تقرير تكاليف الابتعاث حسب السنوات"""
    budget = get_object_or_404(ScholarshipBudget, id=budget_id)

    # الحصول على التكاليف السنوية مرتبة حسب رقم السنة
    yearly_costs = YearlyScholarshipCosts.objects.filter(budget=budget).order_by('year_number')

    # الحصول على الإعدادات
    settings = ScholarshipSettings.objects.first()
    if not settings:
        settings = ScholarshipSettings.objects.create()

    # حساب إجمالي التكاليف
    total_costs = sum(cost.total_year_cost() for cost in yearly_costs)
    insurance_amount = total_costs * settings.life_insurance_rate
    true_cost = total_costs + insurance_amount
    additional_percentage = settings.add_percentage
    grand_total = true_cost * (1 + additional_percentage / 100)

    # تجميع التكاليف حسب السنة المالية
    costs_by_fiscal_year = {}
    for cost in yearly_costs:
        if cost.fiscal_year:
            fiscal_year_id = cost.fiscal_year.id
            fiscal_year_name = str(cost.fiscal_year)

            if fiscal_year_id not in costs_by_fiscal_year:
                costs_by_fiscal_year[fiscal_year_id] = {
                    'fiscal_year': cost.fiscal_year,
                    'name': fiscal_year_name,
                    'costs': [],
                    'total': 0,
                }

            costs_by_fiscal_year[fiscal_year_id]['costs'].append(cost)
            costs_by_fiscal_year[fiscal_year_id]['total'] += cost.total_year_cost()

    # تحويل القاموس إلى قائمة
    costs_by_fiscal_year_list = list(costs_by_fiscal_year.values())

    context = {
        'budget': budget,
        'yearly_costs': yearly_costs,
        'total_costs': total_costs,
        'insurance_rate': settings.life_insurance_rate,
        'insurance_amount': insurance_amount,
        'true_cost': true_cost,
        'additional_percent': additional_percentage,
        'grand_total': grand_total,
        'costs_by_fiscal_year': costs_by_fiscal_year_list,
    }
    return render(request, 'finance/reports/scholarship_years_costs_report.html', context)


