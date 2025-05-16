# في ملف finance/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from django.utils import timezone
from .models import (
    ScholarshipBudget, Expense, ExpenseCategory,
    FinancialReport, BudgetAdjustment, FinancialLog,
    YearlyScholarshipCosts, FiscalYear, ScholarshipSettings
)


@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    list_display = ('year', 'start_date', 'end_date', 'total_budget', 'get_spent_amount',
                    'get_remaining_amount', 'get_spent_percentage', 'status', 'get_scholarship_budgets_count')
    list_filter = ('status', 'year', 'start_date')
    search_fields = ('year', 'description')
    date_hierarchy = 'start_date'
    readonly_fields = ('created_at', 'updated_at', 'get_spent_amount', 'get_remaining_amount')

    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('year', 'start_date', 'end_date', 'total_budget', 'status', 'description')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
        (_('المعلومات المحسوبة'), {
            'fields': ('get_spent_amount', 'get_remaining_amount'),
            'classes': ('collapse',),
        })
    )

    def get_spent_amount(self, obj):
        return obj.get_spent_amount()

    get_spent_amount.short_description = _('المبلغ المصروف')

    def get_remaining_amount(self, obj):
        return obj.get_remaining_amount()

    get_remaining_amount.short_description = _('المبلغ المتبقي')

    def get_spent_percentage(self, obj):
        percentage = obj.get_spent_percentage()
        return f"{percentage:.2f}%"

    get_spent_percentage.short_description = _('نسبة الصرف')

    def get_scholarship_budgets_count(self, obj):
        return obj.scholarship_budgets.count()

    get_scholarship_budgets_count.short_description = _('عدد الميزانيات')

    def save_model(self, request, obj, form, change):
        if not change:  # في حالة إنشاء سجل جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

        # إنشاء سجل للعملية
        action_type = 'update' if change else 'create'
        description = f"{_('تحديث السنة المالية') if change else _('إنشاء سنة مالية جديدة')}"
        FinancialLog.objects.create(
            fiscal_year=obj,
            action_type=action_type,
            description=description,
            created_by=request.user
        )


@admin.register(ScholarshipSettings)
class ScholarshipSettingsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'life_insurance_rate', 'add_percentage', 'current_fiscal_year')
    fieldsets = (
        (_('إعدادات الحساب'), {
            'fields': ('life_insurance_rate', 'add_percentage')
        }),
        (_('السنة المالية'), {
            'fields': ('current_fiscal_year',)
        }),
    )


@admin.register(ScholarshipBudget)
class ScholarshipBudgetAdmin(admin.ModelAdmin):
    list_display = ('application', 'get_applicant_name', 'fiscal_year', 'total_amount', 'get_spent_amount',
                    'get_remaining_amount', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'fiscal_year', 'start_date', 'end_date', 'is_current')
    search_fields = ('application__applicant__first_name', 'application__applicant__last_name',
                     'application__scholarship__title')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'get_spent_amount', 'get_remaining_amount')
    list_select_related = ('application__applicant', 'fiscal_year')

    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('application', 'fiscal_year', 'total_amount', 'start_date', 'end_date', 'status', 'notes')
        }),
        (_('تفاصيل الميزانية'), {
            'fields': ('tuition_fees', 'monthly_stipend', 'travel_allowance', 'health_insurance',
                       'books_allowance', 'research_allowance', 'conference_allowance', 'other_expenses')
        }),
        (_('معلومات السنة الدراسية'), {
            'fields': ('academic_year', 'is_current', 'exchange_rate', 'foreign_currency')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )

    def get_applicant_name(self, obj):
        return obj.application.applicant.get_full_name()

    get_applicant_name.short_description = _('اسم المبتعث')

    def get_spent_amount(self, obj):
        return obj.get_spent_amount()

    get_spent_amount.short_description = _('المبلغ المصروف')

    def get_remaining_amount(self, obj):
        return obj.get_remaining_amount()

    get_remaining_amount.short_description = _('المبلغ المتبقي')

    def save_model(self, request, obj, form, change):
        if not change:  # في حالة إنشاء سجل جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

        # إنشاء سجل للعملية
        action_type = 'update' if change else 'create'
        description = f"{_('تحديث الميزانية') if change else _('إنشاء ميزانية جديدة')}"
        FinancialLog.objects.create(
            budget=obj,
            fiscal_year=obj.fiscal_year,
            action_type=action_type,
            description=description,
            created_by=request.user
        )


@admin.register(YearlyScholarshipCosts)
class YearlyScholarshipCostsAdmin(admin.ModelAdmin):
    list_display = ('budget', 'year_number', 'academic_year', 'fiscal_year', 'total_monthly_allowance',
                    'tuition_fees_foreign', 'tuition_fees_local', 'total_year_cost')
    list_filter = ('year_number', 'academic_year', 'fiscal_year')
    search_fields = ('budget__application__applicant__first_name', 'budget__application__applicant__last_name',
                     'academic_year')
    list_select_related = ('budget__application__applicant', 'fiscal_year')

    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('budget', 'fiscal_year', 'year_number', 'academic_year')
        }),
        (_('تفاصيل التكاليف'), {
            'fields': ('travel_tickets', 'monthly_allowance', 'monthly_duration', 'visa_fees',
                       'health_insurance', 'tuition_fees_local', 'tuition_fees_foreign')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def total_year_cost(self, obj):
        return obj.total_year_cost()

    total_year_cost.short_description = _('إجمالي تكلفة السنة')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('budget', 'get_applicant_name', 'fiscal_year', 'category', 'amount', 'date', 'status')
    list_filter = ('status', 'fiscal_year', 'category', 'date')
    search_fields = ('budget__application__applicant__first_name', 'budget__application__applicant__last_name',
                     'description', 'receipt_number')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at', 'approval_date')
    list_select_related = ('budget__application__applicant', 'category', 'fiscal_year')

    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('budget', 'fiscal_year', 'category', 'amount', 'date', 'description')
        }),
        (_('تفاصيل الإيصال'), {
            'fields': ('receipt_number', 'receipt_file')
        }),
        (_('حالة المصروف'), {
            'fields': ('status', 'approval_notes', 'approved_by', 'approval_date')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )

    def get_applicant_name(self, obj):
        return obj.budget.application.applicant.get_full_name()

    get_applicant_name.short_description = _('اسم المبتعث')

    def save_model(self, request, obj, form, change):
        if not change:  # في حالة إنشاء سجل جديد
            obj.created_by = request.user

        # في حالة تغيير الحالة إلى موافق أو مرفوض
        old_status = None
        if change:
            old_obj = Expense.objects.get(pk=obj.pk)
            old_status = old_obj.status

        if change and old_status != obj.status and obj.status in ['approved', 'rejected']:
            obj.approved_by = request.user
            obj.approval_date = timezone.now()

        # التأكد من تعيين السنة المالية
        if not obj.fiscal_year and obj.budget and obj.budget.fiscal_year:
            obj.fiscal_year = obj.budget.fiscal_year

        super().save_model(request, obj, form, change)

        # إنشاء سجل للعملية
        action_type = 'update' if change else 'create'
        if change and old_status != obj.status:
            if obj.status == 'approved':
                action_type = 'approve'
            elif obj.status == 'rejected':
                action_type = 'reject'

        description = f"{_('تحديث المصروف') if change else _('إنشاء مصروف جديد')}"
        if action_type in ['approve', 'reject']:
            description = f"{_('الموافقة على المصروف') if action_type == 'approve' else _('رفض المصروف')}"

        FinancialLog.objects.create(
            expense=obj,
            budget=obj.budget,
            fiscal_year=obj.fiscal_year,
            action_type=action_type,
            description=description,
            created_by=request.user
        )


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'description', 'get_expenses_count')
    search_fields = ('name', 'code', 'description')

    def get_expenses_count(self, obj):
        return obj.expenses.count()

    get_expenses_count.short_description = _('عدد المصروفات')


@admin.register(BudgetAdjustment)
class BudgetAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('budget', 'get_applicant_name', 'fiscal_year', 'amount', 'adjustment_type', 'date', 'status')
    list_filter = ('adjustment_type', 'status', 'fiscal_year', 'date')
    search_fields = ('budget__application__applicant__first_name', 'budget__application__applicant__last_name',
                     'reason')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'approval_date')
    list_select_related = ('budget__application__applicant', 'fiscal_year')

    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('budget', 'fiscal_year', 'amount', 'adjustment_type', 'date', 'reason')
        }),
        (_('حالة التعديل'), {
            'fields': ('status', 'approved_by', 'approval_date')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_by', 'created_at')
        }),
    )

    def get_applicant_name(self, obj):
        return obj.budget.application.applicant.get_full_name()

    get_applicant_name.short_description = _('اسم المبتعث')

    def save_model(self, request, obj, form, change):
        if not change:  # في حالة إنشاء سجل جديد
            obj.created_by = request.user

        # في حالة تغيير الحالة إلى موافق
        old_status = None
        if change:
            old_obj = BudgetAdjustment.objects.get(pk=obj.pk)
            old_status = old_obj.status

        if change and old_status != obj.status and obj.status == 'approved':
            obj.approved_by = request.user
            obj.approval_date = timezone.now()

            # تطبيق التعديل على الميزانية
            budget = obj.budget
            if obj.adjustment_type == 'increase':
                budget.total_amount += obj.amount
            else:  # decrease
                budget.total_amount -= obj.amount
            budget.save()

        # التأكد من تعيين السنة المالية
        if not obj.fiscal_year and obj.budget and obj.budget.fiscal_year:
            obj.fiscal_year = obj.budget.fiscal_year

        super().save_model(request, obj, form, change)

        # إنشاء سجل للعملية
        action_type = 'update' if change else 'create'
        if change and old_status != obj.status:
            if obj.status == 'approved':
                action_type = 'approve'
            elif obj.status == 'rejected':
                action_type = 'reject'

        description = f"{_('تحديث تعديل الميزانية') if change else _('إنشاء تعديل ميزانية جديد')}"
        if action_type in ['approve', 'reject']:
            description = f"{_('الموافقة على تعديل الميزانية') if action_type == 'approve' else _('رفض تعديل الميزانية')}"

        FinancialLog.objects.create(
            adjustment=obj,
            budget=obj.budget,
            fiscal_year=obj.fiscal_year,
            action_type=action_type,
            description=description,
            created_by=request.user
        )


@admin.register(FinancialReport)
class FinancialReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'report_type', 'fiscal_year', 'created_by', 'created_at', 'is_public')
    list_filter = ('report_type', 'fiscal_year', 'is_public', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('fiscal_year', 'created_by')

    fieldsets = (
        (_('معلومات التقرير'), {
            'fields': ('title', 'description', 'report_type', 'fiscal_year', 'is_public')
        }),
        (_('فلاتر التقرير'), {
            'fields': ('filters',),
            'classes': ('collapse',),
        }),
        (_('معلومات النظام'), {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # في حالة إنشاء سجل جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(FinancialLog)
class FinancialLogAdmin(admin.ModelAdmin):
    list_display = ('action_type', 'get_related_entity', 'fiscal_year', 'created_by', 'created_at')
    list_filter = ('action_type', 'fiscal_year', 'created_at')
    search_fields = ('description', 'created_by__first_name', 'created_by__last_name')
    readonly_fields = ('budget', 'expense', 'adjustment', 'fiscal_year', 'action_type', 'description',
                       'created_by', 'created_at')
    list_select_related = ('budget', 'expense', 'adjustment', 'fiscal_year', 'created_by')

    def get_related_entity(self, obj):
        if obj.fiscal_year and not (obj.budget or obj.expense or obj.adjustment):
            return f"سنة مالية: {obj.fiscal_year}"
        elif obj.budget:
            return f"ميزانية: {obj.budget}"
        elif obj.expense:
            return f"مصروف: {obj.expense}"
        elif obj.adjustment:
            return f"تعديل: {obj.adjustment}"
        else:
            return "-"

    get_related_entity.short_description = _('الكيان المرتبط')

    def has_add_permission(self, request):
        return False  # لا يمكن إضافة سجلات يدويًا

    def has_change_permission(self, request, obj=None):
        return False  # لا يمكن تعديل السجلات