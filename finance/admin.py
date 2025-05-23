from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.contrib import messages
from django.db import models
from django.forms import TextInput, Textarea
from decimal import Decimal
import datetime

from .models import (
    FiscalYear, ScholarshipSettings, ScholarshipBudget,
    YearlyScholarshipCosts, Expense, ExpenseCategory,
    BudgetAdjustment, FinancialReport, FinancialLog
)


def safe_format(template, *args, **kwargs):
    """تنسيق آمن للنصوص HTML"""
    return mark_safe(template.format(*args, **kwargs))


class BaseFinanceAdmin(admin.ModelAdmin):
    """فئة أساسية لجميع نماذج الإدارة المالية"""

    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '40'})},
        models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 60})},
        models.DecimalField: {'widget': TextInput(attrs={'size': '20', 'style': 'text-align: right;'})},
    }

    def get_readonly_fields(self, request, obj=None):
        """جعل حقول التتبع للقراءة فقط"""
        readonly_fields = list(self.readonly_fields)
        if hasattr(self.model, 'created_at'):
            readonly_fields.append('created_at')
        if hasattr(self.model, 'updated_at'):
            readonly_fields.append('updated_at')
        return readonly_fields

    def save_model(self, request, obj, form, change):
        """حفظ محسن مع تعيين المستخدم الحالي"""
        if not change and hasattr(obj, 'created_by'):
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# Inline Classes
class YearlyScholarshipCostsInline(admin.TabularInline):
    """إدراج التكاليف السنوية في صفحة الميزانية"""
    model = YearlyScholarshipCosts
    extra = 1
    min_num = 1
    max_num = 10

    fields = [
        'year_number', 'academic_year', 'fiscal_year',
        'travel_tickets', 'monthly_allowance', 'monthly_duration',
        'visa_fees', 'health_insurance',
        'tuition_fees_foreign', 'tuition_fees_local',
        'total_cost_display'
    ]

    readonly_fields = ['total_cost_display']

    def total_cost_display(self, obj):
        """عرض إجمالي تكلفة السنة"""
        if obj and obj.pk:
            total = obj.total_year_cost()
            return safe_format(
                '<strong style="color: #007cba;">{:.2f} د.أ</strong>',
                total
            )
        return '-'

    total_cost_display.short_description = _('إجمالي السنة')


class ExpenseInline(admin.TabularInline):
    """إدراج المصروفات في صفحة الميزانية"""
    model = Expense
    extra = 0
    max_num = 5

    fields = ['date', 'category', 'amount', 'description', 'status']
    readonly_fields = ['status']
    ordering = ['-date']  # ترتيب مباشر بدلاً من get_queryset


class BudgetAdjustmentInline(admin.TabularInline):
    """إدراج تعديلات الميزانية"""
    model = BudgetAdjustment
    extra = 0
    max_num = 3

    fields = ['date', 'adjustment_type', 'amount', 'status']
    readonly_fields = ['status']
    ordering = ['-date']  # ترتيب مباشر


# Main Admin Classes
@admin.register(FiscalYear)
class FiscalYearAdmin(BaseFinanceAdmin):
    """إدارة السنوات المالية"""

    list_display = [
        'year', 'status_display', 'budget_display',
        'spent_display', 'remaining_display', 'percentage_display',
        'budgets_count', 'period_display'
    ]

    list_filter = ['status', 'year']
    search_fields = ['year', 'description']
    ordering = ['-year']

    fieldsets = (
        (_('المعلومات الأساسية'), {
            'fields': ('year', 'description', 'status')
        }),
        (_('الفترة المالية'), {
            'fields': ('start_date', 'end_date')
        }),
        (_('الميزانية'), {
            'fields': ('total_budget',)
        }),
        (_('ملاحظات'), {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        (_('معلومات التتبع'), {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_by']

    def status_display(self, obj):
        """عرض حالة السنة المالية مع ألوان"""
        colors = {
            'open': '#28a745',
            'closed': '#6c757d',
            'planning': '#ffc107'
        }
        color = colors.get(obj.status, '#007cba')
        return safe_format(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )

    status_display.short_description = 'الحالة'

    def budget_display(self, obj):
        """عرض إجمالي الميزانية"""
        return safe_format('<strong>{:,.2f} د.أ</strong>', obj.total_budget)

    budget_display.short_description = 'إجمالي الميزانية'

    def spent_display(self, obj):
        """عرض المبلغ المصروف"""
        spent = obj.get_spent_amount()
        return safe_format('<span style="color: #dc3545;">{:,.2f} د.أ</span>', spent)

    spent_display.short_description = 'المصروف'

    def remaining_display(self, obj):
        """عرض المبلغ المتبقي"""
        remaining = obj.get_remaining_amount()
        color = '#28a745' if remaining >= 0 else '#dc3545'
        return safe_format('<span style="color: {};">{:,.2f} د.أ</span>', color, remaining)

    remaining_display.short_description = 'المتبقي'

    def percentage_display(self, obj):
        """عرض نسبة الصرف"""
        percentage = obj.get_spent_percentage()
        if percentage >= 90:
            color = '#dc3545'
        elif percentage >= 75:
            color = '#ffc107'
        else:
            color = '#28a745'

        return safe_format('<span style="color: {}; font-weight: bold;">{:.1f}%</span>', color, percentage)

    percentage_display.short_description = 'نسبة الصرف'

    def budgets_count(self, obj):
        """عدد الميزانيات في السنة المالية"""
        count = obj.scholarship_budgets.count()
        url = reverse('admin:finance_scholarshipbudget_changelist') + '?fiscal_year__id__exact={}'.format(obj.id)
        return safe_format('<a href="{}">{} ميزانية</a>', url, count)

    budgets_count.short_description = 'عدد الميزانيات'

    def period_display(self, obj):
        """عرض فترة السنة المالية"""
        return "{} - {}".format(obj.start_date, obj.end_date)

    period_display.short_description = 'الفترة'


@admin.register(ScholarshipSettings)
class ScholarshipSettingsAdmin(admin.ModelAdmin):
    """إدارة إعدادات الابتعاث"""

    list_display = [
        'current_fiscal_year', 'insurance_rate_display',
        'add_percentage_display'
    ]

    fieldsets = (
        (_('السنة المالية الحالية'), {
            'fields': ('current_fiscal_year',)
        }),
        (_('إعدادات التأمين والنسب'), {
            'fields': ('life_insurance_rate', 'add_percentage')
        }),
    )

    def insurance_rate_display(self, obj):
        """عرض معدل التأمين"""
        rate_per_thousand = obj.life_insurance_rate * 1000
        return safe_format('{:.1f}‰ ({:.4f})', rate_per_thousand, obj.life_insurance_rate)

    insurance_rate_display.short_description = 'معدل التأمين'

    def add_percentage_display(self, obj):
        """عرض النسبة الإضافية"""
        return safe_format('<strong>{:.1f}%</strong>', obj.add_percentage)

    add_percentage_display.short_description = 'النسبة الإضافية'

    def has_add_permission(self, request):
        """السماح بإضافة إعدادات واحدة فقط"""
        return not ScholarshipSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """منع حذف الإعدادات"""
        return False


@admin.register(ScholarshipBudget)
class ScholarshipBudgetAdmin(BaseFinanceAdmin):
    """إدارة ميزانيات الابتعاث"""

    list_display = [
        'applicant_name', 'academic_year', 'fiscal_year',
        'status_display', 'total_amount_display',
        'spent_display', 'remaining_display', 'years_count'
    ]

    list_filter = [
        'status', 'fiscal_year', 'academic_year',
        'is_current', 'created_at'
    ]

    search_fields = [
        'application__applicant__first_name',
        'application__applicant__last_name',
        'application__applicant__national_id',
        'academic_year'
    ]

    ordering = ['-created_at']

    fieldsets = (
        (_('معلومات المتقدم'), {
            'fields': ('application', 'fiscal_year')
        }),
        (_('معلومات الميزانية'), {
            'fields': (
                'total_amount', 'status', 'academic_year', 'is_current'
            )
        }),
        (_('الفترة الزمنية'), {
            'fields': ('start_date', 'end_date')
        }),
        (_('تفاصيل الفئات المالية'), {
            'fields': (
                'tuition_fees', 'monthly_stipend', 'travel_allowance',
                'health_insurance', 'other_expenses'
            ),
            'classes': ('collapse',)
        }),
        (_('معلومات العملة'), {
            'fields': ('exchange_rate', 'foreign_currency'),
            'classes': ('collapse',)
        }),
        (_('ملاحظات'), {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        (_('معلومات التتبع'), {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_by']

    inlines = [YearlyScholarshipCostsInline, ExpenseInline, BudgetAdjustmentInline]

    actions = ['recalculate_budgets', 'activate_budgets', 'close_budgets']

    def applicant_name(self, obj):
        """اسم المتقدم"""
        return obj.application.applicant.get_full_name()

    applicant_name.short_description = 'المتقدم'

    def status_display(self, obj):
        """عرض حالة الميزانية مع ألوان"""
        colors = {
            'draft': '#6c757d',
            'pending': '#ffc107',
            'active': '#28a745',
            'closed': '#dc3545',
            'cancelled': '#6f42c1'
        }
        color = colors.get(obj.status, '#007cba')
        return safe_format(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )

    status_display.short_description = 'الحالة'

    def total_amount_display(self, obj):
        """عرض إجمالي الميزانية"""
        return safe_format('<strong style="color: #007cba;">{:,.2f} د.أ</strong>', obj.total_amount)

    total_amount_display.short_description = 'إجمالي الميزانية'

    def spent_display(self, obj):
        """عرض المبلغ المصروف"""
        spent = obj.get_spent_amount()
        percentage = obj.get_spent_percentage()
        return safe_format(
            '<span style="color: #dc3545;">{:,.2f} د.أ</span><br><small>({:.1f}%)</small>',
            spent, percentage
        )

    spent_display.short_description = 'المصروف'

    def remaining_display(self, obj):
        """عرض المبلغ المتبقي"""
        remaining = obj.get_remaining_amount()
        color = '#28a745' if remaining >= 0 else '#dc3545'
        return safe_format('<span style="color: {};">{:,.2f} د.أ</span>', color, remaining)

    remaining_display.short_description = 'المتبقي'

    def years_count(self, obj):
        """عدد السنوات الدراسية"""
        count = obj.yearly_costs.count()
        total_cost = obj.get_yearly_costs_total()

        return safe_format('{} سنة<br><small>{:,.2f} د.أ</small>', count, total_cost)

    years_count.short_description = 'السنوات'

    # Custom Actions
    def recalculate_budgets(self, request, queryset):
        """إعادة حساب الميزانيات المحددة"""
        updated = 0
        for budget in queryset:
            validation = budget.validate_budget_calculation()
            if not validation['is_valid']:
                budget.recalculate_total_amount()
                updated += 1

        message = 'تم إعادة حساب {} ميزانية من أصل {}'.format(updated, queryset.count())
        self.message_user(request, message, messages.SUCCESS)

    recalculate_budgets.short_description = 'إعادة حساب الميزانيات المحددة'

    def activate_budgets(self, request, queryset):
        """تفعيل الميزانيات المحددة"""
        updated = queryset.update(status='active')
        message = 'تم تفعيل {} ميزانية'.format(updated)
        self.message_user(request, message, messages.SUCCESS)

    activate_budgets.short_description = 'تفعيل الميزانيات المحددة'

    def close_budgets(self, request, queryset):
        """إغلاق الميزانيات المحددة"""
        updated = queryset.update(status='closed')
        message = 'تم إغلاق {} ميزانية'.format(updated)
        self.message_user(request, message, messages.SUCCESS)

    close_budgets.short_description = 'إغلاق الميزانيات المحددة'


@admin.register(YearlyScholarshipCosts)
class YearlyScholarshipCostsAdmin(BaseFinanceAdmin):
    """إدارة التكاليف السنوية"""

    list_display = [
        'budget_applicant', 'year_number', 'academic_year',
        'fiscal_year', 'total_display', 'breakdown_display'
    ]

    list_filter = [
        'year_number', 'fiscal_year', 'academic_year',
        'budget__status'
    ]

    search_fields = [
        'budget__application__applicant__first_name',
        'budget__application__applicant__last_name',
        'academic_year'
    ]

    ordering = ['budget', 'year_number']

    fieldsets = (
        (_('معلومات السنة'), {
            'fields': ('budget', 'fiscal_year', 'year_number', 'academic_year')
        }),
        (_('التكاليف الأساسية'), {
            'fields': (
                'travel_tickets', 'monthly_allowance', 'monthly_duration',
                'visa_fees', 'health_insurance'
            )
        }),
        (_('الرسوم الدراسية'), {
            'fields': ('tuition_fees_foreign', 'tuition_fees_local')
        }),
        (_('ملاحظات'), {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def budget_applicant(self, obj):
        """اسم المتقدم والميزانية"""
        url = reverse('admin:finance_scholarshipbudget_change', args=[obj.budget.id])
        return safe_format('<a href="{}">{}</a>', url, obj.budget.application.applicant.get_full_name())

    budget_applicant.short_description = 'الميزانية'

    def total_display(self, obj):
        """إجمالي تكلفة السنة"""
        total = obj.total_year_cost()
        return safe_format('<strong style="color: #007cba;">{:,.2f} د.أ</strong>', total)

    total_display.short_description = 'الإجمالي'

    def breakdown_display(self, obj):
        """تفكيك سريع للتكاليف"""
        monthly_total = obj.get_monthly_total()
        travel_other = obj.travel_tickets + obj.visa_fees + obj.health_insurance
        return safe_format(
            'رسوم: {:,.0f} د.أ<br>شهري: {:,.0f} د.أ<br>أخرى: {:,.0f} د.أ',
            obj.tuition_fees_local, monthly_total, travel_other
        )

    breakdown_display.short_description = 'التفكيك'


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    """إدارة فئات المصروفات"""

    list_display = ['name', 'description', 'expenses_count', 'total_amount']
    search_fields = ['name', 'description']
    ordering = ['name']

    fieldsets = (
        (_('معلومات الفئة'), {
            'fields': ('name', 'description')
        }),
    )

    def expenses_count(self, obj):
        """عدد المصروفات في هذه الفئة"""
        count = obj.expenses.count()
        url = reverse('admin:finance_expense_changelist') + '?category__id__exact={}'.format(obj.id)
        return safe_format('<a href="{}">{} مصروف</a>', url, count)

    expenses_count.short_description = 'عدد المصروفات'

    def total_amount(self, obj):
        """إجمالي المصروفات في هذه الفئة"""
        total = obj.expenses.filter(status='approved').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

        return safe_format('<strong>{:,.2f} د.أ</strong>', total)

    total_amount.short_description = 'إجمالي المبلغ'


@admin.register(Expense)
class ExpenseAdmin(BaseFinanceAdmin):
    """إدارة المصروفات"""

    list_display = [
        'budget_applicant', 'date', 'category',
        'amount_display', 'status_display', 'approval_info'
    ]

    list_filter = [
        'status', 'category', 'fiscal_year',
        'date', 'approval_date'
    ]

    search_fields = [
        'budget__application__applicant__first_name',
        'budget__application__applicant__last_name',
        'description', 'receipt_number'
    ]

    ordering = ['-date']

    fieldsets = (
        (_('معلومات المصروف'), {
            'fields': ('budget', 'fiscal_year', 'category')
        }),
        (_('تفاصيل المصروف'), {
            'fields': ('date', 'amount', 'description', 'receipt_number')
        }),
        (_('المرفقات'), {
            'fields': ('receipt_file',),
            'classes': ('collapse',)
        }),
        (_('الموافقة'), {
            'fields': ('status', 'approved_by', 'approval_date', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        (_('معلومات التتبع'), {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_by', 'approved_by', 'approval_date']

    actions = ['approve_expenses', 'reject_expenses']

    def budget_applicant(self, obj):
        """اسم المتقدم والميزانية"""
        url = reverse('admin:finance_scholarshipbudget_change', args=[obj.budget.id])
        return safe_format('<a href="{}" title="عرض الميزانية">{}</a>', url,
                           obj.budget.application.applicant.get_full_name())

    budget_applicant.short_description = 'المتقدم'

    def amount_display(self, obj):
        """عرض المبلغ مع تنسيق"""
        return safe_format('<strong style="color: #dc3545;">{:,.2f} د.أ</strong>', obj.amount)

    amount_display.short_description = 'المبلغ'

    def status_display(self, obj):
        """عرض حالة المصروف مع ألوان"""
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545'
        }
        color = colors.get(obj.status, '#007cba')
        return safe_format('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display())

    status_display.short_description = 'الحالة'

    def approval_info(self, obj):
        """معلومات الموافقة"""
        if obj.status == 'approved' and obj.approved_by:
            approval_date = obj.approval_date.strftime('%Y-%m-%d') if obj.approval_date else '-'
            return safe_format('<small>بواسطة: {}<br>في: {}</small>', obj.approved_by.get_full_name(), approval_date)
        elif obj.status == 'rejected':
            return safe_format('<small style="color: #dc3545;">مرفوض</small>')
        return '-'

    approval_info.short_description = 'معلومات الموافقة'

    def approve_expenses(self, request, queryset):
        """الموافقة على المصروفات المحددة"""
        updated = queryset.filter(status='pending').update(
            status='approved',
            approved_by=request.user,
            approval_date=datetime.datetime.now()
        )
        message = 'تمت الموافقة على {} مصروف'.format(updated)
        self.message_user(request, message, messages.SUCCESS)

    approve_expenses.short_description = 'الموافقة على المصروفات المحددة'

    def reject_expenses(self, request, queryset):
        """رفض المصروفات المحددة"""
        updated = queryset.filter(status='pending').update(
            status='rejected',
            approved_by=request.user,
            approval_date=datetime.datetime.now()
        )
        message = 'تم رفض {} مصروف'.format(updated)
        self.message_user(request, message, messages.WARNING)

    reject_expenses.short_description = 'رفض المصروفات المحددة'


@admin.register(BudgetAdjustment)
class BudgetAdjustmentAdmin(admin.ModelAdmin):
    """إدارة تعديلات الميزانية"""

    list_display = [
        'budget_applicant', 'date', 'adjustment_type_display',
        'amount_display', 'status_display', 'approval_info'
    ]

    list_filter = [
        'adjustment_type', 'status', 'fiscal_year', 'date'
    ]

    search_fields = [
        'budget__application__applicant__first_name',
        'budget__application__applicant__last_name'
    ]

    ordering = ['-date']

    fieldsets = (
        (_('معلومات التعديل'), {
            'fields': ('budget', 'fiscal_year', 'date')
        }),
        (_('تفاصيل التعديل'), {
            'fields': ('adjustment_type', 'amount')
        }),
        (_('الموافقة'), {
            'fields': ('status', 'approved_by', 'approval_date', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        (_('معلومات التتبع'), {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_by', 'approved_by', 'approval_date']

    def budget_applicant(self, obj):
        """اسم المتقدم والميزانية"""
        url = reverse('admin:finance_scholarshipbudget_change', args=[obj.budget.id])
        return safe_format('<a href="{}" title="عرض الميزانية">{}</a>', url,
                           obj.budget.application.applicant.get_full_name())

    budget_applicant.short_description = 'المتقدم'

    def adjustment_type_display(self, obj):
        """عرض نوع التعديل مع أيقونة"""
        if obj.adjustment_type == 'increase':
            return safe_format('<span style="color: #28a745;">↗ {}</span>', obj.get_adjustment_type_display())
        else:
            return safe_format('<span style="color: #dc3545;">↘ {}</span>', obj.get_adjustment_type_display())

    adjustment_type_display.short_description = 'نوع التعديل'

    def amount_display(self, obj):
        """عرض مبلغ التعديل"""
        color = '#28a745' if obj.adjustment_type == 'increase' else '#dc3545'
        symbol = '+' if obj.adjustment_type == 'increase' else '-'

        return safe_format('<strong style="color: {};">{}{:,.2f} د.أ</strong>', color, symbol, obj.amount)

    amount_display.short_description = 'المبلغ'

    def status_display(self, obj):
        """عرض حالة التعديل"""
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545'
        }
        color = colors.get(obj.status, '#007cba')
        return safe_format('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display())

    status_display.short_description = 'الحالة'

    def approval_info(self, obj):
        """معلومات الموافقة"""
        if obj.status == 'approved' and obj.approved_by:
            approval_date = obj.approval_date.strftime('%Y-%m-%d') if obj.approval_date else '-'
            return safe_format('<small>بواسطة: {}<br>في: {}</small>', obj.approved_by.get_full_name(), approval_date)
        elif obj.status == 'rejected':
            return safe_format('<small style="color: #dc3545;">مرفوض</small>')
        return '-'

    approval_info.short_description = 'معلومات الموافقة'


@admin.register(FinancialReport)
class FinancialReportAdmin(BaseFinanceAdmin):
    """إدارة التقارير المالية"""

    list_display = [
        'title', 'report_type', 'fiscal_year',
        'created_by', 'is_public'
    ]

    list_filter = [
        'report_type', 'fiscal_year', 'is_public', 'created_at'
    ]

    search_fields = ['title', 'description']
    ordering = ['-created_at']

    fieldsets = (
        (_('معلومات التقرير'), {
            'fields': ('title', 'description', 'report_type')
        }),
        (_('المرشحات والإعدادات'), {
            'fields': ('fiscal_year', 'filters', 'is_public')
        }),
        (_('معلومات التتبع'), {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_by']


@admin.register(FinancialLog)
class FinancialLogAdmin(admin.ModelAdmin):
    """إدارة سجل العمليات المالية"""

    list_display = [
        'created_at', 'action_type', 'entity_info',
        'description_short', 'created_by'
    ]

    list_filter = [
        'action_type', 'fiscal_year', 'created_at'
    ]

    search_fields = [
        'description', 'budget__application__applicant__first_name',
        'budget__application__applicant__last_name'
    ]

    ordering = ['-created_at']

    readonly_fields = [
        'budget', 'expense', 'adjustment', 'fiscal_year',
        'action_type', 'description', 'created_by', 'created_at'
    ]

    def has_add_permission(self, request):
        """منع إضافة سجلات يدوياً"""
        return False

    def has_change_permission(self, request, obj=None):
        """منع تعديل السجلات"""
        return False

    def has_delete_permission(self, request, obj=None):
        """السماح بحذف السجلات القديمة فقط"""
        return request.user.is_superuser

    def entity_info(self, obj):
        """معلومات الكيان المرتبط"""
        if obj.budget:
            url = reverse('admin:finance_scholarshipbudget_change', args=[obj.budget.id])
            return safe_format('ميزانية: <a href="{}">{}</a>', url, obj.budget.application.applicant.get_full_name())
        elif obj.expense:
            url = reverse('admin:finance_expense_change', args=[obj.expense.id])
            return safe_format('مصروف: <a href="{}">{:,.2f} د.أ</a>', url, obj.expense.amount)
        elif obj.adjustment:
            url = reverse('admin:finance_budgetadjustment_change', args=[obj.adjustment.id])
            return safe_format('تعديل: <a href="{}">{:,.2f} د.أ</a>', url, obj.adjustment.amount)
        return '-'

    entity_info.short_description = 'الكيان'

    def description_short(self, obj):
        """وصف مختصر"""
        return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description

    description_short.short_description = 'الوصف'


# تخصيص عنوان لوحة الإدارة
admin.site.site_header = 'نظام إدارة الابتعاث - الشؤون المالية'
admin.site.site_title = 'الشؤون المالية'
admin.site.index_title = 'إدارة الشؤون المالية'