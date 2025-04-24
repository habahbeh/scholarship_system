# في ملف finance/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    ScholarshipBudget, Expense, ExpenseCategory,
    FinancialReport, BudgetAdjustment, FinancialLog
)


@admin.register(ScholarshipBudget)
class ScholarshipBudgetAdmin(admin.ModelAdmin):
    list_display = ('application', 'get_applicant_name', 'total_amount', 'get_spent_amount',
                    'get_remaining_amount', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'start_date', 'end_date')
    search_fields = ('application__applicant__first_name', 'application__applicant__last_name',
                     'application__scholarship__title')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('application', 'total_amount', 'start_date', 'end_date', 'status', 'notes')
        }),
        (_('تفاصيل الميزانية'), {
            'fields': ('tuition_fees', 'monthly_stipend', 'travel_allowance', 'health_insurance',
                       'books_allowance', 'research_allowance', 'conference_allowance', 'other_expenses')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )

    def get_applicant_name(self, obj):
        return obj.application.applicant.get_full_name()

    get_applicant_name.short_description = _('اسم المبتعث')

    def save_model(self, request, obj, form, change):
        if not change:  # في حالة إنشاء سجل جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

        # إنشاء سجل للعملية
        action_type = 'update' if change else 'create'
        description = f"{_('تحديث الميزانية') if change else _('إنشاء ميزانية جديدة')}"
        FinancialLog.objects.create(
            budget=obj,
            action_type=action_type,
            description=description,
            created_by=request.user
        )


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('budget', 'get_applicant_name', 'category', 'amount', 'date', 'status')
    list_filter = ('status', 'category', 'date')
    search_fields = ('budget__application__applicant__first_name', 'budget__application__applicant__last_name',
                     'description', 'receipt_number')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at', 'approval_date')

    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('budget', 'category', 'amount', 'date', 'description')
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
            action_type=action_type,
            description=description,
            created_by=request.user
        )


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'description')
    search_fields = ('name', 'code', 'description')


@admin.register(BudgetAdjustment)
class BudgetAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('budget', 'get_applicant_name', 'amount', 'adjustment_type', 'date', 'status')
    list_filter = ('adjustment_type', 'status', 'date')
    search_fields = ('budget__application__applicant__first_name', 'budget__application__applicant__last_name',
                     'reason')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'approval_date')

    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('budget', 'amount', 'adjustment_type', 'date', 'reason')
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
            action_type=action_type,
            description=description,
            created_by=request.user
        )


@admin.register(FinancialReport)
class FinancialReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'report_type', 'created_by', 'created_at', 'is_public')
    list_filter = ('report_type', 'is_public', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(FinancialLog)
class FinancialLogAdmin(admin.ModelAdmin):
    list_display = ('action_type', 'get_related_entity', 'created_by', 'created_at')
    list_filter = ('action_type', 'created_at')
    search_fields = ('description', 'created_by__first_name', 'created_by__last_name')
    readonly_fields = ('budget', 'expense', 'adjustment', 'action_type', 'description',
                       'created_by', 'created_at')

    def get_related_entity(self, obj):
        if obj.budget:
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