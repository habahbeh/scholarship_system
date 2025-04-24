# في ملف finance/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone
from applications.models import Application


class ScholarshipBudget(models.Model):
    """نموذج ميزانية المبتعث"""
    application = models.OneToOneField(Application, on_delete=models.CASCADE,
                                       verbose_name=_("طلب الابتعاث"),
                                       related_name="budget")
    total_amount = models.DecimalField(_("المبلغ الإجمالي"), max_digits=12, decimal_places=2)
    start_date = models.DateField(_("تاريخ بدء الميزانية"))
    end_date = models.DateField(_("تاريخ انتهاء الميزانية"))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   verbose_name=_("تم الإنشاء بواسطة"),
                                   related_name="created_budgets")
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)
    notes = models.TextField(_("ملاحظات"), blank=True, null=True)

    # الفئات المالية داخل الميزانية
    tuition_fees = models.DecimalField(_("الرسوم الدراسية"), max_digits=12, decimal_places=2, default=0)
    monthly_stipend = models.DecimalField(_("المخصص الشهري"), max_digits=12, decimal_places=2, default=0)
    travel_allowance = models.DecimalField(_("بدل السفر"), max_digits=12, decimal_places=2, default=0)
    health_insurance = models.DecimalField(_("التأمين الصحي"), max_digits=12, decimal_places=2, default=0)
    books_allowance = models.DecimalField(_("بدل الكتب"), max_digits=12, decimal_places=2, default=0)
    research_allowance = models.DecimalField(_("بدل البحث العلمي"), max_digits=12, decimal_places=2, default=0)
    conference_allowance = models.DecimalField(_("بدل المؤتمرات"), max_digits=12, decimal_places=2, default=0)
    other_expenses = models.DecimalField(_("مصاريف أخرى"), max_digits=12, decimal_places=2, default=0)

    # حالة الميزانية
    STATUS_CHOICES = [
        ('active', _('نشطة')),
        ('suspended', _('معلقة')),
        ('closed', _('مغلقة')),
    ]
    status = models.CharField(_("حالة الميزانية"), max_length=20, choices=STATUS_CHOICES, default='active')

    class Meta:
        verbose_name = _("ميزانية الابتعاث")
        verbose_name_plural = _("ميزانيات الابتعاث")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.application.applicant.get_full_name()} - {self.total_amount}"

    def get_absolute_url(self):
        return reverse('finance:budget_detail', args=[self.id])

    def get_remaining_amount(self):
        """حساب المبلغ المتبقي في الميزانية"""
        spent_amount = self.expenses.aggregate(models.Sum('amount'))['amount__sum'] or 0
        return self.total_amount - spent_amount

    def get_spent_amount(self):
        """حساب المبلغ المصروف من الميزانية"""
        return self.expenses.aggregate(models.Sum('amount'))['amount__sum'] or 0

    def get_spent_percentage(self):
        """حساب نسبة الصرف من الميزانية"""
        if self.total_amount > 0:
            return (self.get_spent_amount() / self.total_amount) * 100
        return 0


class ExpenseCategory(models.Model):
    """نموذج فئات المصروفات"""
    name = models.CharField(_("اسم الفئة"), max_length=100)
    description = models.TextField(_("وصف الفئة"), blank=True, null=True)
    code = models.CharField(_("رمز الفئة"), max_length=20, blank=True, null=True)

    class Meta:
        verbose_name = _("فئة المصروفات")
        verbose_name_plural = _("فئات المصروفات")
        ordering = ['name']

    def __str__(self):
        return self.name


class Expense(models.Model):
    """نموذج المصروفات المالية"""
    budget = models.ForeignKey(ScholarshipBudget, on_delete=models.CASCADE,
                               verbose_name=_("الميزانية"),
                               related_name="expenses")
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT,
                                 verbose_name=_("فئة المصروف"),
                                 related_name="expenses")
    amount = models.DecimalField(_("المبلغ"), max_digits=12, decimal_places=2)
    date = models.DateField(_("تاريخ المصروف"))
    description = models.TextField(_("وصف المصروف"))
    receipt_number = models.CharField(_("رقم الإيصال"), max_length=100, blank=True, null=True)
    receipt_file = models.FileField(_("ملف الإيصال"), upload_to='finance/receipts/%Y/%m/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   verbose_name=_("تم الإنشاء بواسطة"),
                                   related_name="created_expenses")
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    # حالة المصروف
    STATUS_CHOICES = [
        ('pending', _('قيد المراجعة')),
        ('approved', _('تمت الموافقة')),
        ('rejected', _('مرفوض')),
    ]
    status = models.CharField(_("حالة المصروف"), max_length=20, choices=STATUS_CHOICES, default='pending')

    # تفاصيل الموافقة أو الرفض
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                    verbose_name=_("تمت الموافقة/الرفض بواسطة"),
                                    related_name="approved_expenses",
                                    blank=True, null=True)
    approval_date = models.DateTimeField(_("تاريخ الموافقة/الرفض"), blank=True, null=True)
    approval_notes = models.TextField(_("ملاحظات الموافقة/الرفض"), blank=True, null=True)

    class Meta:
        verbose_name = _("مصروف")
        verbose_name_plural = _("المصروفات")
        ordering = ['-date']

    def __str__(self):
        return f"{self.budget.application.applicant.get_full_name()} - {self.category.name} - {self.amount}"

    def get_absolute_url(self):
        return reverse('finance:expense_detail', args=[self.id])


class FinancialReport(models.Model):
    """نموذج التقارير المالية"""
    title = models.CharField(_("عنوان التقرير"), max_length=200)
    description = models.TextField(_("وصف التقرير"), blank=True, null=True)

    # نوع التقرير
    REPORT_TYPE_CHOICES = [
        ('budget_summary', _('ملخص الميزانية')),
        ('expense_summary', _('ملخص المصروفات')),
        ('budget_comparison', _('مقارنة الميزانيات')),
        ('monthly_expenses', _('المصروفات الشهرية')),
        ('category_expenses', _('المصروفات حسب الفئة')),
        ('custom', _('تقرير مخصص')),
    ]
    report_type = models.CharField(_("نوع التقرير"), max_length=50, choices=REPORT_TYPE_CHOICES)

    # فلاتر التقرير (يتم تخزينها كـ JSON)
    filters = models.JSONField(_("فلاتر التقرير"), blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   verbose_name=_("تم الإنشاء بواسطة"),
                                   related_name="created_reports")
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    # هل التقرير متاح للمستخدمين الآخرين
    is_public = models.BooleanField(_("متاح للجميع"), default=False)

    class Meta:
        verbose_name = _("تقرير مالي")
        verbose_name_plural = _("التقارير المالية")
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('finance:report_detail', args=[self.id])


class BudgetAdjustment(models.Model):
    """نموذج تعديلات الميزانية"""
    budget = models.ForeignKey(ScholarshipBudget, on_delete=models.CASCADE,
                               verbose_name=_("الميزانية"),
                               related_name="adjustments")
    amount = models.DecimalField(_("المبلغ"), max_digits=12, decimal_places=2)
    date = models.DateField(_("تاريخ التعديل"))
    reason = models.TextField(_("سبب التعديل"))

    # نوع التعديل
    ADJUSTMENT_TYPE_CHOICES = [
        ('increase', _('زيادة')),
        ('decrease', _('تخفيض')),
    ]
    adjustment_type = models.CharField(_("نوع التعديل"), max_length=20, choices=ADJUSTMENT_TYPE_CHOICES)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   verbose_name=_("تم الإنشاء بواسطة"),
                                   related_name="created_adjustments")
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)

    # تفاصيل الموافقة
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                    verbose_name=_("تمت الموافقة بواسطة"),
                                    related_name="approved_adjustments",
                                    blank=True, null=True)
    approval_date = models.DateTimeField(_("تاريخ الموافقة"), blank=True, null=True)

    STATUS_CHOICES = [
        ('pending', _('قيد المراجعة')),
        ('approved', _('تمت الموافقة')),
        ('rejected', _('مرفوض')),
    ]
    status = models.CharField(_("حالة التعديل"), max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        verbose_name = _("تعديل الميزانية")
        verbose_name_plural = _("تعديلات الميزانية")
        ordering = ['-date']

    def __str__(self):
        return f"{self.budget.application.applicant.get_full_name()} - {self.adjustment_type} - {self.amount}"

    def get_absolute_url(self):
        return reverse('finance:adjustment_detail', args=[self.id])


class FinancialLog(models.Model):
    """نموذج سجل العمليات المالية"""
    budget = models.ForeignKey(ScholarshipBudget, on_delete=models.CASCADE,
                               verbose_name=_("الميزانية"),
                               related_name="logs",
                               blank=True, null=True)
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE,
                                verbose_name=_("المصروف"),
                                related_name="logs",
                                blank=True, null=True)
    adjustment = models.ForeignKey(BudgetAdjustment, on_delete=models.CASCADE,
                                   verbose_name=_("تعديل الميزانية"),
                                   related_name="logs",
                                   blank=True, null=True)

    # نوع العملية
    ACTION_TYPE_CHOICES = [
        ('create', _('إنشاء')),
        ('update', _('تحديث')),
        ('delete', _('حذف')),
        ('approve', _('موافقة')),
        ('reject', _('رفض')),
    ]
    action_type = models.CharField(_("نوع العملية"), max_length=20, choices=ACTION_TYPE_CHOICES)
    description = models.TextField(_("وصف العملية"))

    created_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   verbose_name=_("تم بواسطة"),
                                   related_name="financial_logs")
    created_at = models.DateTimeField(_("تاريخ العملية"), auto_now_add=True)

    class Meta:
        verbose_name = _("سجل مالي")
        verbose_name_plural = _("السجلات المالية")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action_type} - {self.created_at}"