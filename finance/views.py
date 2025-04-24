# في ملف finance/views.py

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
    FinancialReport, BudgetAdjustment, FinancialLog
)
from .forms import (
    ScholarshipBudgetForm, ExpenseForm, ExpenseCategoryForm, 
    ExpenseApprovalForm, BudgetAdjustmentForm, BudgetAdjustmentApprovalForm, 
    FinancialReportForm, DateRangeForm, BudgetFilterForm, ExpenseFilterForm
)


@login_required
def finance_home(request):
    """الصفحة الرئيسية للشؤون المالية"""
    # إحصائيات عامة
    total_budgets = ScholarshipBudget.objects.count()
    active_budgets = ScholarshipBudget.objects.filter(status='active').count()
    total_expenses = Expense.objects.count()
    pending_expenses = Expense.objects.filter(status='pending').count()
    
    # إجمالي الميزانيات والمصروفات
    total_budget_amount = ScholarshipBudget.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    total_expense_amount = Expense.objects.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0
    
    # أحدث 5 ميزانيات
    latest_budgets = ScholarshipBudget.objects.all().order_by('-created_at')[:5]
    
    # أحدث 5 مصروفات
    latest_expenses = Expense.objects.all().order_by('-created_at')[:5]
    
    context = {
        'total_budgets': total_budgets,
        'active_budgets': active_budgets,
        'total_expenses': total_expenses,
        'pending_expenses': pending_expenses,
        'total_budget_amount': total_budget_amount,
        'total_expense_amount': total_expense_amount,
        'latest_budgets': latest_budgets,
        'latest_expenses': latest_expenses,
    }
    return render(request, 'finance/home.html', context)


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
    
    context = {
        'budgets': budgets_page,
        'filter_form': filter_form,
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
    expenses = Expense.objects.filter(budget=budget).order_by('-date')
    
    # إجمالي المصروفات حسب الفئة
    expenses_by_category = expenses.values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    # تعديلات الميزانية
    adjustments = BudgetAdjustment.objects.filter(budget=budget).order_by('-date')
    
    # سجل العمليات
    logs = FinancialLog.objects.filter(
        Q(budget=budget) | 
        Q(expense__budget=budget) | 
        Q(adjustment__budget=budget)
    ).order_by('-created_at')[:20]
    
    context = {
        'budget': budget,
        'expenses': expenses,
        'expenses_by_category': expenses_by_category,
        'adjustments': adjustments,
        'logs': logs,
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
    
    if request.method == 'POST':
        form = ScholarshipBudgetForm(request.POST)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.application = application
            budget.created_by = request.user
            budget.save()
            
            # إنشاء سجل للعملية
            FinancialLog.objects.create(
                budget=budget,
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
            'start_date': start_date,
            'end_date': end_date,
        })
    
    context = {
        'form': form,
        'application': application,
    }
    return render(request, 'finance/budget_form.html', context)


@login_required
@permission_required('finance.change_scholarshipbudget', raise_exception=True)
def update_budget(request, budget_id):
    """تحديث ميزانية موجودة"""
    budget = get_object_or_404(ScholarshipBudget, id=budget_id)
    
    if request.method == 'POST':
        form = ScholarshipBudgetForm(request.POST, instance=budget)
        if form.is_valid():
            form.save()
            
            # إنشاء سجل للعملية
            FinancialLog.objects.create(
                budget=budget,
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
    
    if request.method == 'POST':
        application = budget.application
        
        # إنشاء سجل للعملية
        FinancialLog.objects.create(
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



# إدارة المصروفات

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

    context = {
        'expenses': expenses_page,
        'filter_form': filter_form,
    }
    return render(request, 'finance/expense_list.html', context)


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
            expense.save()

            # إنشاء سجل للعملية
            FinancialLog.objects.create(
                expense=expense,
                action_type='create',
                description=_("إنشاء مصروف جديد"),
                created_by=request.user
            )

            messages.success(request, _("تم إنشاء المصروف بنجاح"))
            return redirect('finance:budget_detail', budget_id=budget.id)
    else:
        form = ExpenseForm(budget=budget, initial={'date': timezone.now().date()})

    context = {
        'form': form,
        'budget': budget,
    }
    return render(request, 'finance/expense_form.html', context)


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
            form.save()

            # إنشاء سجل للعملية
            FinancialLog.objects.create(
                expense=expense,
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

        # إنشاء سجل للعملية
        FinancialLog.objects.create(
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


# إدارة فئات المصروفات

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


# إدارة تعديلات الميزانية

@login_required
@permission_required('finance.view_budgetadjustment', raise_exception=True)
def adjustment_list(request, budget_id):
    """عرض قائمة تعديلات الميزانية"""
    budget = get_object_or_404(ScholarshipBudget, id=budget_id)
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
            adjustment.save()

            # إنشاء سجل للعملية
            FinancialLog.objects.create(
                adjustment=adjustment,
                action_type='create',
                description=_("إنشاء تعديل ميزانية جديد"),
                created_by=request.user
            )

            messages.success(request, _("تم إنشاء تعديل الميزانية بنجاح وهو قيد المراجعة"))
            return redirect('finance:budget_detail', budget_id=budget.id)
    else:
        form = BudgetAdjustmentForm(budget=budget, initial={'date': timezone.now().date()})

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
                    action_type='update',
                    description=_("تحديث إجمالي الميزانية من خلال تعديل معتمد"),
                    created_by=request.user
                )

            # إنشاء سجل للعملية
            action_type = 'approve' if adjustment.status == 'approved' else 'reject'
            description = _("الموافقة على تعديل الميزانية") if adjustment.status == 'approved' else _("رفض تعديل الميزانية")

            FinancialLog.objects.create(
                adjustment=adjustment,
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


# التقارير المالية

@login_required
@permission_required('finance.view_financialreport', raise_exception=True)
def report_list(request):
    """عرض قائمة التقارير المالية"""
    # التقارير التي أنشأها المستخدم
    user_reports = FinancialReport.objects.filter(created_by=request.user).order_by('-created_at')

    # التقارير العامة
    public_reports = FinancialReport.objects.filter(is_public=True).exclude(created_by=request.user).order_by('-created_at')

    context = {
        'user_reports': user_reports,
        'public_reports': public_reports,
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
                filters = {'start_date': start_date, 'end_date': end_date}

            elif report_type == 'expense_summary':
                status = request.POST.get('status')
                category = request.POST.get('category')
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                filters = {
                    'status': status,
                    'category': category,
                    'start_date': start_date,
                    'end_date': end_date
                }

            elif report_type == 'monthly_expenses':
                year = request.POST.get('year')
                filters = {'year': year}

            elif report_type == 'category_expenses':
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                filters = {'start_date': start_date, 'end_date': end_date}

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
    years = list(range(timezone.now().year - 5, timezone.now().year + 1))

    context = {
        'form': form,
        'date_range_form': date_range_form,
        'expense_filter_form': expense_filter_form,
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
                filters = {'start_date': start_date, 'end_date': end_date}

            elif report_type == 'expense_summary':
                status = request.POST.get('status')
                category = request.POST.get('category')
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                filters = {
                    'status': status,
                    'category': category,
                    'start_date': start_date,
                    'end_date': end_date
                }

            elif report_type == 'monthly_expenses':
                year = request.POST.get('year')
                filters = {'year': year}

            elif report_type == 'category_expenses':
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                filters = {'start_date': start_date, 'end_date': end_date}

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
        'end_date': filters.get('end_date')
    })
    years = list(range(timezone.now().year - 5, timezone.now().year + 1))

    context = {
        'form': form,
        'report': report,
        'date_range_form': date_range_form,
        'expense_filter_form': expense_filter_form,
        'years': years,
        'is_update': True,
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