from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    FiscalYear, ScholarshipBudget, YearlyScholarshipCosts, ScholarshipSettings,
    ExpenseCategory, Expense, FinancialReport, BudgetAdjustment, FinancialLog
)


class YearlyScholarshipCostsInline(admin.TabularInline):
    """عرض تكاليف السنوات الدراسية كجزء من نموذج الميزانية"""
    model = YearlyScholarshipCosts
    extra = 0
    fields = ('year_number', 'academic_year', 'travel_tickets', 'monthly_allowance',
              'monthly_duration', 'visa_fees', 'health_insurance',
              'tuition_fees_foreign', 'tuition_fees_local')
    readonly_fields = ('total_monthly_allowance', 'total_year_cost')


class ExpenseInline(admin.TabularInline):
    """عرض المصروفات كجزء من نموذج الميزانية"""
    model = Expense
    extra = 0
    fields = ('date', 'category', 'amount', 'status')
    readonly_fields = ('status',)
    can_delete = False


class BudgetAdjustmentInline(admin.TabularInline):
    """عرض تعديلات الميزانية كجزء من نموذج الميزانية"""
    model = BudgetAdjustment
    extra = 0
    fields = ('date', 'adjustment_type', 'amount', 'status')
    readonly_fields = ('status',)
    can_delete = False


@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    """إدارة السنوات المالية"""
    list_display = (
    'year', 'start_date', 'end_date', 'total_budget', 'status', 'get_spent_amount', 'get_remaining_amount')
    list_filter = ('status', 'year')
    search_fields = ('year', 'description')
    readonly_fields = (
    'created_at', 'updated_at', 'created_by', 'get_spent_amount', 'get_remaining_amount', 'get_spent_percentage')
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('year', 'start_date', 'end_date', 'total_budget', 'status')
        }),
        (_('معلومات الإنفاق'), {
            'fields': ('get_spent_amount', 'get_remaining_amount', 'get_spent_percentage')
        }),
        (_('معلومات إضافية'), {
            'fields': ('description', 'created_at', 'updated_at', 'created_by')
        }),
    )

    def save_model(self, request, obj, form, change):
        """حفظ اسم المستخدم الذي قام بإنشاء السنة المالية"""
        if not change:  # إذا كان هذا إنشاء جديد وليس تعديل
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ScholarshipBudget)
class ScholarshipBudgetAdmin(admin.ModelAdmin):
    """إدارة ميزانيات الابتعاث"""
    list_display = (
    'application', 'academic_year', 'fiscal_year', 'total_amount', 'get_spent_amount', 'get_remaining_amount', 'status',
    'is_current')
    list_filter = ('status', 'fiscal_year', 'academic_year', 'is_current')
    search_fields = (
    'application__applicant__first_name', 'application__applicant__last_name', 'application__university',
    'application__major')
    readonly_fields = (
    'created_at', 'updated_at', 'created_by', 'get_spent_amount', 'get_remaining_amount', 'get_spent_percentage',
    'get_yearly_costs_total')
    inlines = [YearlyScholarshipCostsInline, ExpenseInline, BudgetAdjustmentInline]
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('application', 'fiscal_year', 'total_amount', 'start_date', 'end_date')
        }),
        (_('معلومات السنة الدراسية'), {
            'fields': ('academic_year', 'foreign_currency', 'exchange_rate', 'is_current')
        }),
        (_('حالة الميزانية'), {
            'fields': (
            'status', 'get_spent_amount', 'get_remaining_amount', 'get_spent_percentage', 'get_yearly_costs_total')
        }),
        (_('ملاحظات'), {
            'fields': ('notes',)
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        """حفظ اسم المستخدم الذي قام بإنشاء الميزانية"""
        if not change:  # إذا كان هذا إنشاء جديد وليس تعديل
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(YearlyScholarshipCosts)
class YearlyScholarshipCostsAdmin(admin.ModelAdmin):
    """إدارة تكاليف السنوات الدراسية"""
    list_display = (
    'budget', 'year_number', 'academic_year', 'monthly_allowance', 'monthly_duration', 'tuition_fees_local',
    'total_year_cost')
    list_filter = ('budget__fiscal_year', 'academic_year', 'year_number')
    search_fields = (
    'budget__application__applicant__first_name', 'budget__application__applicant__last_name', 'academic_year')
    readonly_fields = ('created_at', 'updated_at', 'total_monthly_allowance', 'total_year_cost')
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('budget', 'year_number', 'academic_year', 'fiscal_year')
        }),
        (_('تفاصيل التكاليف'), {
            'fields': ('travel_tickets', 'monthly_allowance', 'monthly_duration', 'visa_fees', 'health_insurance',
                       'tuition_fees_local', 'tuition_fees_foreign', 'total_monthly_allowance', 'total_year_cost')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    """إدارة فئات المصروفات"""
    list_display = ('name', 'code', 'description')
    search_fields = ('name', 'code', 'description')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    """إدارة المصروفات"""
    list_display = ('budget', 'category', 'amount', 'date', 'status', 'created_by')
    list_filter = ('status', 'category', 'date', 'fiscal_year')
    search_fields = (
    'budget__application__applicant__first_name', 'budget__application__applicant__last_name', 'description',
    'receipt_number')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'approved_by', 'approval_date')
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('budget', 'category', 'amount', 'date', 'fiscal_year')
        }),
        (_('تفاصيل المصروف'), {
            'fields': ('description', 'receipt_number', 'receipt_file')
        }),
        (_('حالة المصروف'), {
            'fields': ('status', 'approval_notes', 'approved_by', 'approval_date')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        """حفظ اسم المستخدم الذي قام بإنشاء المصروف"""
        if not change:  # إذا كان هذا إنشاء جديد وليس تعديل
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(BudgetAdjustment)
class BudgetAdjustmentAdmin(admin.ModelAdmin):
    """إدارة تعديلات الميزانية"""
    list_display = ('budget', 'adjustment_type', 'amount', 'date', 'status', 'created_by')
    list_filter = ('status', 'adjustment_type', 'date', 'fiscal_year')
    search_fields = (
    'budget__application__applicant__first_name', 'budget__application__applicant__last_name', 'reason')
    readonly_fields = ('created_at', 'created_by', 'approved_by', 'approval_date')
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('budget', 'amount', 'date', 'adjustment_type', 'fiscal_year')
        }),
        (_('تفاصيل التعديل'), {
            'fields': ('reason',)
        }),
        (_('حالة التعديل'), {
            'fields': ('status', 'approved_by', 'approval_date')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        """حفظ اسم المستخدم الذي قام بإنشاء التعديل"""
        if not change:  # إذا كان هذا إنشاء جديد وليس تعديل
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(FinancialReport)
class FinancialReportAdmin(admin.ModelAdmin):
    """إدارة التقارير المالية"""
    list_display = ('title', 'report_type', 'fiscal_year', 'created_by', 'created_at', 'is_public')
    list_filter = ('report_type', 'fiscal_year', 'is_public', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('title', 'description', 'report_type', 'fiscal_year', 'is_public')
        }),
        (_('فلاتر التقرير'), {
            'fields': ('filters',)
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        """حفظ اسم المستخدم الذي قام بإنشاء التقرير"""
        if not change:  # إذا كان هذا إنشاء جديد وليس تعديل
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(FinancialLog)
class FinancialLogAdmin(admin.ModelAdmin):
    """إدارة سجلات العمليات المالية"""
    list_display = ('action_type', 'description', 'created_by', 'created_at')
    list_filter = ('action_type', 'created_at', 'fiscal_year')
    search_fields = ('description', 'created_by__username')
    readonly_fields = ('created_at', 'created_by', 'budget', 'expense', 'adjustment', 'fiscal_year')
    fieldsets = (
        (_('معلومات العملية'), {
            'fields': ('action_type', 'description')
        }),
        (_('العناصر المرتبطة'), {
            'fields': ('budget', 'expense', 'adjustment', 'fiscal_year')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',),
        }),
    )


@admin.register(ScholarshipSettings)
class ScholarshipSettingsAdmin(admin.ModelAdmin):
    """إدارة إعدادات نظام الابتعاث"""
    list_display = ('life_insurance_rate', 'add_percentage', 'current_fiscal_year')
    fieldsets = (
        (_('إعدادات الابتعاث'), {
            'fields': ('life_insurance_rate', 'add_percentage', 'current_fiscal_year')
        }),
    )

    def has_add_permission(self, request):
        """منع إنشاء أكثر من سجل واحد للإعدادات"""
        # التحقق من وجود سجلات
        if ScholarshipSettings.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        """منع حذف سجل الإعدادات"""
        return False