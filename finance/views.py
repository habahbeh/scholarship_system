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

# استكمال وظائف توليد بيانات التقارير

def generate_budget_summary_data(filters):
    """توليد بيانات تقرير ملخص الميزانية"""
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')

    # إنشاء استعلام أساسي
    budgets_query = ScholarshipBudget.objects.all()

    # تطبيق الفلاتر
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

    # إنشاء استعلام أساسي
    expenses_query = Expense.objects.all()

    # تطبيق الفلاتر
    if status:
        expenses_query = expenses_query.filter(status=status)
    if category:
        expenses_query = expenses_query.filter(category_id=category)
    if start_date:
        expenses_query = expenses_query.filter(date__gte=start_date)
    if end_date:
        expenses_query = expenses_query.filter(date__lte=end_date)

    # حساب الإجماليات
    total_amount = expenses_query.aggregate(total=Sum('amount'))['total'] or 0

    # جمع البيانات عن المصروفات
    expenses_data = []
    for expense in expenses_query.select_related('budget__application__applicant', 'category'):
        expenses_data.append({
            'id': expense.id,
            'applicant': expense.budget.application.applicant.get_full_name(),
            'category': expense.category.name,
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

    # الحصول على المصروفات في العام المحدد
    expenses = Expense.objects.filter(
        date__year=year,
        status='approved'
    ).annotate(
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
    }

def generate_category_expenses_data(filters):
    """توليد بيانات تقرير المصروفات حسب الفئة"""
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')

    # إنشاء استعلام أساسي
    expenses_query = Expense.objects.filter(status='approved')

    # تطبيق الفلاتر
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

def generate_budget_comparison_data(filters):
    """توليد بيانات تقرير مقارنة الميزانيات"""
    # الحصول على جميع الميزانيات النشطة
    budgets = ScholarshipBudget.objects.filter(status='active')

    comparison_data = []
    for budget in budgets:
        # حساب مبالغ الميزانية والمصروفات لكل فئة
        tuition_expenses = Expense.objects.filter(
            budget=budget,
            category__name__icontains='رسوم دراسية',
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0

        monthly_expenses = Expense.objects.filter(
            budget=budget,
            category__name__icontains='مخصص شهري',
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0

        travel_expenses = Expense.objects.filter(
            budget=budget,
            category__name__icontains='سفر',
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0

        health_expenses = Expense.objects.filter(
            budget=budget,
            category__name__icontains='تأمين صحي',
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0

        books_expenses = Expense.objects.filter(
            budget=budget,
            category__name__icontains='كتب',
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0

        research_expenses = Expense.objects.filter(
            budget=budget,
            category__name__icontains='بحث',
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0

        conference_expenses = Expense.objects.filter(
            budget=budget,
            category__name__icontains='مؤتمر',
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0

        other_expenses = Expense.objects.filter(
            budget=budget,
            category__name__icontains='أخرى',
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0

        comparison_data.append({
            'id': budget.id,
            'applicant': budget.application.applicant.get_full_name(),
            'tuition': {
                'budget': budget.tuition_fees,
                'spent': tuition_expenses,
                'remaining': budget.tuition_fees - tuition_expenses,
                'percentage': (tuition_expenses / budget.tuition_fees * 100) if budget.tuition_fees > 0 else 0,
            },
            'monthly': {
                'budget': budget.monthly_stipend,
                'spent': monthly_expenses,
                'remaining': budget.monthly_stipend - monthly_expenses,
                'percentage': (monthly_expenses / budget.monthly_stipend * 100) if budget.monthly_stipend > 0 else 0,
            },
            'travel': {
                'budget': budget.travel_allowance,
                'spent': travel_expenses,
                'remaining': budget.travel_allowance - travel_expenses,
                'percentage': (travel_expenses / budget.travel_allowance * 100) if budget.travel_allowance > 0 else 0,
            },
            'health': {
                'budget': budget.health_insurance,
                'spent': health_expenses,
                'remaining': budget.health_insurance - health_expenses,
                'percentage': (health_expenses / budget.health_insurance * 100) if budget.health_insurance > 0 else 0,
            },
            'books': {
                'budget': budget.books_allowance,
                'spent': books_expenses,
                'remaining': budget.books_allowance - books_expenses,
                'percentage': (books_expenses / budget.books_allowance * 100) if budget.books_allowance > 0 else 0,
            },
            'research': {
                'budget': budget.research_allowance,
                'spent': research_expenses,
                'remaining': budget.research_allowance - research_expenses,
                'percentage': (research_expenses / budget.research_allowance * 100) if budget.research_allowance > 0 else 0,
            },
            'conference': {
                'budget': budget.conference_allowance,
                'spent': conference_expenses,
                'remaining': budget.conference_allowance - conference_expenses,
                'percentage': (conference_expenses / budget.conference_allowance * 100) if budget.conference_allowance > 0 else 0,
            },
            'other': {
                'budget': budget.other_expenses,
                'spent': other_expenses,
                'remaining': budget.other_expenses - other_expenses,
                'percentage': (other_expenses / budget.other_expenses * 100) if budget.other_expenses > 0 else 0,
            },
        })

    return {
        'comparison_data': comparison_data,
        'categories': [
            {'key': 'tuition', 'name': _('الرسوم الدراسية')},
            {'key': 'monthly', 'name': _('المخصص الشهري')},
            {'key': 'travel', 'name': _('بدل السفر')},
            {'key': 'health', 'name': _('التأمين الصحي')},
            {'key': 'books', 'name': _('بدل الكتب')},
            {'key': 'research', 'name': _('بدل البحث العلمي')},
            {'key': 'conference', 'name': _('بدل المؤتمرات')},
            {'key': 'other', 'name': _('مصاريف أخرى')},
        ],
    }

# وظائف تصدير التقارير إلى Excel

def export_budget_summary_excel(worksheet, data, header_format, cell_format, date_format, money_format):
    """تصدير تقرير ملخص الميزانية إلى Excel"""
    # كتابة العناوين
    headers = [
        _("المتقدم"), _("المنحة"), _("المبلغ الإجمالي"), _("المبلغ المصروف"),
        _("المبلغ المتبقي"), _("نسبة الصرف"), _("تاريخ البداية"), _("تاريخ النهاية"), _("الحالة")
    ]

    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
        worksheet.set_column(col, col, 18)  # تعيين عرض العمود

    # كتابة البيانات
    for row, budget in enumerate(data['budgets']):
        worksheet.write(row + 1, 0, budget['applicant'], cell_format)
        worksheet.write(row + 1, 1, budget['scholarship'], cell_format)
        worksheet.write(row + 1, 2, budget['total_amount'], money_format)
        worksheet.write(row + 1, 3, budget['spent_amount'], money_format)
        worksheet.write(row + 1, 4, budget['remaining_amount'], money_format)
        worksheet.write(row + 1, 5, f"{budget['spent_percentage']:.2f}%", cell_format)
        worksheet.write(row + 1, 6, budget['start_date'], date_format)
        worksheet.write(row + 1, 7, budget['end_date'], date_format)
        worksheet.write(row + 1, 8, budget['status'], cell_format)

    # كتابة الإجماليات
    row_total = len(data['budgets']) + 2
    worksheet.write(row_total, 0, _("الإجمالي"), header_format)
    worksheet.write(row_total, 2, data['total_budget'], money_format)
    worksheet.write(row_total, 3, data['total_spent'], money_format)
    worksheet.write(row_total, 4, data['total_remaining'], money_format)


def export_expense_summary_excel(worksheet, data, header_format, cell_format, date_format, money_format):
    """تصدير تقرير ملخص المصروفات إلى Excel"""
    # كتابة العناوين
    headers = [
        _("المتقدم"), _("الفئة"), _("المبلغ"), _("التاريخ"), _("الحالة"), _("الوصف")
    ]

    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
        worksheet.set_column(col, col, 18)  # تعيين عرض العمود

    # وصف أطول للوصف
    worksheet.set_column(5, 5, 40)

    # كتابة البيانات
    for row, expense in enumerate(data['expenses']):
        worksheet.write(row + 1, 0, expense['applicant'], cell_format)
        worksheet.write(row + 1, 1, expense['category'], cell_format)
        worksheet.write(row + 1, 2, expense['amount'], money_format)
        worksheet.write(row + 1, 3, expense['date'], date_format)
        worksheet.write(row + 1, 4, expense['status'], cell_format)
        worksheet.write(row + 1, 5, expense['description'], cell_format)

    # كتابة الإجماليات
    row_total = len(data['expenses']) + 2
    worksheet.write(row_total, 0, _("الإجمالي"), header_format)
    worksheet.write(row_total, 2, data['total_amount'], money_format)

    # كتابة المصروفات حسب الفئة
    row_category = row_total + 2
    worksheet.write(row_category, 0, _("المصروفات حسب الفئة"), header_format)
    worksheet.write(row_category, 1, _("المبلغ"), header_format)

    for i, category in enumerate(data['expenses_by_category']):
        worksheet.write(row_category + i + 1, 0, category['category__name'], cell_format)
        worksheet.write(row_category + i + 1, 1, category['total'], money_format)


def export_monthly_expenses_excel(worksheet, data, header_format, cell_format, money_format):
    """تصدير تقرير المصروفات الشهرية إلى Excel"""
    # كتابة العناوين
    headers = [_("الشهر"), _("المبلغ")]

    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
        worksheet.set_column(col, col, 18)  # تعيين عرض العمود

    # كتابة البيانات
    for row, month_data in enumerate(data['monthly_data']):
        worksheet.write(row + 1, 0, month_data['month'], cell_format)
        worksheet.write(row + 1, 1, month_data['total'], money_format)

    # كتابة الإجماليات
    row_total = len(data['monthly_data']) + 2
    worksheet.write(row_total, 0, _("الإجمالي السنوي"), header_format)
    worksheet.write(row_total, 1, data['total_year_expenses'], money_format)

    worksheet.write(row_total + 1, 0, _("المتوسط الشهري"), header_format)
    worksheet.write(row_total + 1, 1, data['monthly_average'], money_format)


def export_category_expenses_excel(worksheet, data, header_format, cell_format, money_format):
    """تصدير تقرير المصروفات حسب الفئة إلى Excel"""
    # كتابة العناوين
    headers = [_("الفئة"), _("المبلغ"), _("عدد المصروفات"), _("النسبة المئوية")]

    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
        worksheet.set_column(col, col, 18)  # تعيين عرض العمود

    # كتابة البيانات
    for row, category in enumerate(data['category_data']):
        worksheet.write(row + 1, 0, category['category__name'], cell_format)
        worksheet.write(row + 1, 1, category['total'], money_format)
        worksheet.write(row + 1, 2, category['count'], cell_format)
        worksheet.write(row + 1, 3, f"{category['percentage']:.2f}%", cell_format)

    # كتابة الإجمالي
    row_total = len(data['category_data']) + 2
    worksheet.write(row_total, 0, _("الإجمالي"), header_format)
    worksheet.write(row_total, 1, data['total_amount'], money_format)


def export_budget_comparison_excel(worksheet, data, header_format, cell_format, money_format):
    """تصدير تقرير مقارنة الميزانيات إلى Excel"""
    # كتابة اسم المتقدم في العمود الأول
    worksheet.write(0, 0, _("المتقدم"), header_format)
    worksheet.set_column(0, 0, 20)  # تعيين عرض العمود

    # كتابة أسماء الفئات كعناوين أعمدة
    for col, category in enumerate(data['categories']):
        worksheet.write(0, col + 1, category['name'], header_format)
        worksheet.set_column(col + 1, col + 1, 18)  # تعيين عرض العمود

    # كتابة بيانات كل متقدم
    for row, budget in enumerate(data['comparison_data']):
        worksheet.write(row + 1, 0, budget['applicant'], cell_format)

        # كتابة قيم كل فئة
        for col, category in enumerate(data['categories']):
            key = category['key']
            value = f"{budget[key]['spent']} / {budget[key]['budget']} ({budget[key]['percentage']:.1f}%)"
            worksheet.write(row + 1, col + 1, value, cell_format)


# إضافة وظائف التقارير المحددة مسبقاً

@login_required
@permission_required('finance.view_financialreport', raise_exception=True)
def budget_summary_report(request):
    """تقرير ملخص الميزانية"""
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            filters = {
                'start_date': form.cleaned_data['start_date'],
                'end_date': form.cleaned_data['end_date'],
            }
            report_data = generate_budget_summary_data(filters)
        else:
            report_data = generate_budget_summary_data({})
    else:
        form = DateRangeForm()
        report_data = generate_budget_summary_data({})

    context = {
        'form': form,
        'report_data': report_data,
        'report_type': 'budget_summary',
        'report_title': _('تقرير ملخص الميزانية'),
    }
    return render(request, 'finance/reports/budget_summary.html', context)


@login_required
@permission_required('finance.view_financialreport', raise_exception=True)
def expense_summary_report(request):
    """تقرير ملخص المصروفات"""
    if request.method == 'POST':
        form = ExpenseFilterForm(request.POST)
        if form.is_valid():
            filters = {
                'status': form.cleaned_data['status'],
                'category': form.cleaned_data['category'].id if form.cleaned_data['category'] else None,
                'start_date': form.cleaned_data['start_date'],
                'end_date': form.cleaned_data['end_date'],
            }
            report_data = generate_expense_summary_data(filters)
        else:
            report_data = generate_expense_summary_data({})
    else:
        form = ExpenseFilterForm()
        report_data = generate_expense_summary_data({})

    context = {
        'form': form,
        'report_data': report_data,
        'report_type': 'expense_summary',
        'report_title': _('تقرير ملخص المصروفات'),
    }
    return render(request, 'finance/reports/expense_summary.html', context)


@login_required
@permission_required('finance.view_financialreport', raise_exception=True)
def monthly_expenses_report(request):
    """تقرير المصروفات الشهرية"""
    years = list(range(timezone.now().year - 5, timezone.now().year + 1))

    if request.method == 'POST':
        year = request.POST.get('year', timezone.now().year)
        filters = {'year': year}
        report_data = generate_monthly_expenses_data(filters)
    else:
        year = timezone.now().year
        filters = {'year': year}
        report_data = generate_monthly_expenses_data(filters)

    context = {
        'years': years,
        'selected_year': int(year),
        'report_data': report_data,
        'report_type': 'monthly_expenses',
        'report_title': _('تقرير المصروفات الشهرية'),
    }
    return render(request, 'finance/reports/monthly_expenses.html', context)


@login_required
@permission_required('finance.view_financialreport', raise_exception=True)
def category_expenses_report(request):
    """تقرير المصروفات حسب الفئة"""
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            filters = {
                'start_date': form.cleaned_data['start_date'],
                'end_date': form.cleaned_data['end_date'],
            }
            report_data = generate_category_expenses_data(filters)
        else:
            report_data = generate_category_expenses_data({})
    else:
        form = DateRangeForm()
        report_data = generate_category_expenses_data({})

    context = {
        'form': form,
        'report_data': report_data,
        'report_type': 'category_expenses',
        'report_title': _('تقرير المصروفات حسب الفئة'),
    }
    return render(request, 'finance/reports/category_expenses.html', context)


# لوحة القيادة المالية

@login_required
@permission_required('finance.view_scholarshipbudget', raise_exception=True)
def finance_dashboard(request):
    """لوحة معلومات الشؤون المالية"""
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
    total_expense_amount = Expense.objects.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0
    remaining_budget = total_budget_amount - total_expense_amount
    budget_percentage = (total_expense_amount / total_budget_amount * 100) if total_budget_amount > 0 else 0

    # حساب التغير في المصروفات
    # يمكن حساب التغير بمقارنة الشهر الحالي مع الشهر السابق
    this_month = timezone.now().replace(day=1)
    last_month = (this_month - datetime.timedelta(days=1)).replace(day=1)

    this_month_expenses = Expense.objects.filter(
        date__gte=this_month, status='approved'
    ).aggregate(total=Sum('amount'))['total'] or 0

    last_month_expenses = Expense.objects.filter(
        date__gte=last_month, date__lt=this_month, status='approved'
    ).aggregate(total=Sum('amount'))['total'] or 0

    expense_change = ((this_month_expenses - last_month_expenses) / last_month_expenses * 100) if last_month_expenses > 0 else 0

    # حساب معدل الصرف اليومي
    today = timezone.now().date()
    month_start = today.replace(day=1)
    days_passed = (today - month_start).days + 1

    monthly_expenses = Expense.objects.filter(
        date__gte=month_start, date__lte=today, status='approved'
    ).aggregate(total=Sum('amount'))['total'] or 0

    daily_spend_rate = monthly_expenses / days_passed if days_passed > 0 else 0
    print("monthly_expenses", monthly_expenses)
    print("days_passed", days_passed)
    # آخر تحديث
    last_update = today

    # الحصول على أحدث المصروفات
    recent_expenses = Expense.objects.all().order_by('-date')[:10]

    context = {
        # قيم ضرورية للقالب
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


# API للرسوم البيانية

@login_required
def api_budget_summary(request):
    """API لبيانات ملخص الميزانية"""
    # حساب إجماليات الميزانية والمصروفات
    total_budget = ScholarshipBudget.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    total_spent = Expense.objects.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0
    total_remaining = total_budget - total_spent

    # بيانات الرسم البياني
    pie_data = [
        {'name': _('المبلغ المصروف'), 'value': float(total_spent)},
        {'name': _('المبلغ المتبقي'), 'value': float(total_remaining)},
    ]

    return JsonResponse({
        'pie_data': pie_data,
        'total_budget': float(total_budget),
        'total_spent': float(total_spent),
        'total_remaining': float(total_remaining),
    })


@login_required
def api_expense_categories(request):
    """API لبيانات المصروفات حسب الفئة"""
    # تجميع المصروفات حسب الفئة
    expenses_by_category = Expense.objects.filter(status='approved').values(
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
    year = request.GET.get('year', timezone.now().year)

    # الحصول على المصروفات الشهرية
    expenses = Expense.objects.filter(
        date__year=year,
        status='approved'
    ).annotate(
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
    # عدد الميزانيات حسب الحالة
    budgets_by_status = ScholarshipBudget.objects.values(
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
@permission_required('finance.add_yearlyscholarshipcosts')
def add_scholarship_year(request, budget_id):
    """إضافة سنة جديدة لميزانية المبتعث"""
    budget = get_object_or_404(ScholarshipBudget, id=budget_id)

    # تحديد رقم السنة الجديدة
    next_year_number = YearlyScholarshipCosts.objects.filter(budget=budget).count() + 1

    if request.method == 'POST':
        form = YearlyScholarshipCostsForm(request.POST)
        if form.is_valid():
            yearly_cost = form.save(commit=False)
            yearly_cost.budget = budget
            yearly_cost.save()

            messages.success(request, _("تمت إضافة السنة الدراسية بنجاح"))
            return redirect('finance:budget_detail', budget_id=budget.id)
    else:
        # القيم الافتراضية حسب تقرير PDF المرفق
        initial_data = {
            'year_number': next_year_number,
            'academic_year': budget.academic_year,
            'monthly_allowance': 1000,
            'monthly_duration': 12,
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
    }
    return render(request, 'finance/scholarship_year_form.html', context)


@login_required
@permission_required('finance.view_scholarshipbudget')
def scholarship_years_costs_report(request, budget_id):
    """عرض تقرير تكاليف الابتعاث حسب السنوات"""
    budget = get_object_or_404(ScholarshipBudget, id=budget_id)
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

    context = {
        'budget': budget,
        'yearly_costs': yearly_costs,
        'total_costs': total_costs,
        'insurance_rate': settings.life_insurance_rate,
        'insurance_amount': insurance_amount,
        'true_cost': true_cost,
        'additional_percent': additional_percentage,
        'grand_total': grand_total,
    }
    return render(request, 'finance/reports/scholarship_years_costs_report.html', context)


@login_required
@permission_required('finance.change_scholarshipbudget')
def close_current_year_open_new(request, budget_id):
    """إغلاق السنة الحالية وفتح سنة جديدة"""
    budget = get_object_or_404(ScholarshipBudget, id=budget_id)

    if request.method == 'POST':
        # تحديث السنة الحالية
        current_year = budget.academic_year
        year_parts = current_year.split('-')
        next_year = f"{int(year_parts[0])+1}-{int(year_parts[1])+1}"

        # إغلاق السنة الحالية
        budget.is_current = False
        budget.save()

        # إنشاء ميزانية جديدة للسنة التالية
        new_budget = ScholarshipBudget.objects.create(
            application=budget.application,
            total_amount=budget.total_amount,  # يمكن تغييره حسب الحاجة
            start_date=budget.end_date + datetime.timedelta(days=1),
            end_date=budget.end_date + datetime.timedelta(days=365),
            academic_year=next_year,
            exchange_rate=budget.exchange_rate,
            foreign_currency=budget.foreign_currency,
            is_current=True
        )

        messages.success(request, f"تم إغلاق السنة {current_year} وفتح سنة جديدة {next_year} بنجاح")
        return redirect('finance:budget_detail', budget_id=new_budget.id)

    context = {
        'budget': budget,
    }
    return render(request, 'finance/close_year_confirm.html', context)