# في ملف finance/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone
from applications.models import Application
import datetime
from decimal import Decimal

class FiscalYear(models.Model):
    """نموذج السنة المالية"""
    year = models.IntegerField(_("السنة المالية"))
    start_date = models.DateField(_("تاريخ البداية"))
    end_date = models.DateField(_("تاريخ النهاية"))
    status = models.CharField(_("الحالة"), max_length=10,
                              choices=[('open', 'مفتوحة'), ('closed', 'مغلقة')],
                              default='open')
    total_budget = models.DecimalField(_("إجمالي الميزانية السنوية"),
                                       max_digits=15, decimal_places=2)
    description = models.TextField(_("وصف/ملاحظات"), blank=True, null=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   verbose_name=_("تم الإنشاء بواسطة"),
                                   related_name="created_fiscal_years",
                                   null=True)

    class Meta:
        verbose_name = _("السنة المالية")
        verbose_name_plural = _("السنوات المالية")
        ordering = ['-year']
        unique_together = ['year']

    def __str__(self):
        return f"السنة المالية {self.year} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse('finance:fiscal_year_detail', args=[self.id])

    def get_spent_amount(self):
        """إجمالي المصاريف في هذه السنة المالية"""
        return Expense.objects.filter(
            date__gte=self.start_date,
            date__lte=self.end_date,
            status='approved'
        ).aggregate(models.Sum('amount'))['amount__sum'] or 0

    def get_remaining_amount(self):
        """المبلغ المتبقي من الميزانية"""
        return self.total_budget - self.get_spent_amount()

    def get_spent_percentage(self):
        """نسبة الإنفاق من الميزانية"""
        if self.total_budget > 0:
            return (self.get_spent_amount() / self.total_budget) * 100
        return 0

    def get_scholarship_budgets_count(self):
        """عدد ميزانيات الابتعاث المرتبطة بهذه السنة المالية"""
        return self.scholarship_budgets.count()

    def close_and_create_new(self):
        """إغلاق السنة المالية الحالية وإنشاء سنة جديدة"""
        if self.status == 'closed':
            return None

        # إغلاق السنة الحالية
        self.status = 'closed'
        self.save()

        # إنشاء سنة مالية جديدة
        next_year = self.year + 1
        new_fiscal_year = FiscalYear.objects.create(
            year=next_year,
            start_date=datetime.date(next_year, 1, 1),
            end_date=datetime.date(next_year, 12, 31),
            status='open',
            total_budget=self.total_budget,  # يمكن تعديله لاحقًا
            description=f"السنة المالية {next_year}",
            created_by=self.created_by
        )

        return new_fiscal_year


class ScholarshipBudget(models.Model):
    """نموذج ميزانية المبتعث"""
    application = models.OneToOneField(Application, on_delete=models.CASCADE,
                                       verbose_name=_("طلب الابتعاث"),
                                       related_name="budget")
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE,
                                    verbose_name=_("السنة المالية"),
                                    related_name="scholarship_budgets",
                                    null=True)
    total_amount = models.DecimalField(_("المبلغ الإجمالي"), max_digits=12, decimal_places=2)
    start_date = models.DateField(_("تاريخ بدء الميزانية"))
    end_date = models.DateField(_("تاريخ انتهاء الميزانية"))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   verbose_name=_("تم الإنشاء بواسطة"),
                                   related_name="created_budgets")
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)
    notes = models.TextField(_("ملاحظات"), blank=True, null=True)

    # حالة الميزانية
    STATUS_CHOICES = [
        ('active', _('نشطة')),
        ('suspended', _('معلقة')),
        ('closed', _('مغلقة')),
    ]
    status = models.CharField(_("حالة الميزانية"), max_length=20, choices=STATUS_CHOICES, default='active')

    # حقول للدعم السنوي والعملات
    academic_year = models.CharField(_("السنة الدراسية"), max_length=9,
                                     help_text=_("مثال: 2024-2025"), default="2024-2025")
    exchange_rate = models.DecimalField(_("سعر الصرف"), max_digits=6, decimal_places=2, default=0.91,
                                        help_text=_("سعر صرف العملة الأجنبية"))
    foreign_currency = models.CharField(_("العملة الأجنبية"), max_length=3, default="GBP")
    is_current = models.BooleanField(_("السنة الحالية"), default=True,
                                     help_text=_("هل هذه الميزانية للسنة الحالية؟"))

    class Meta:
        verbose_name = _("ميزانية الابتعاث")
        verbose_name_plural = _("ميزانيات الابتعاث")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.application.applicant.get_full_name()} - {self.total_amount} - {self.academic_year}"

    def get_absolute_url(self):
        return reverse('finance:budget_detail', args=[self.id])

    def get_remaining_amount(self):
        """حساب المبلغ المتبقي في الميزانية"""
        spent_amount = self.expenses.filter(
            date__gte=self.fiscal_year.start_date if self.fiscal_year else self.start_date,
            date__lte=self.fiscal_year.end_date if self.fiscal_year else self.end_date,
            status='approved'
        ).aggregate(models.Sum('amount'))['amount__sum'] or 0
        return self.total_amount - spent_amount

    def get_spent_amount(self):
        """حساب المبلغ المصروف من الميزانية"""
        return self.expenses.filter(
            date__gte=self.fiscal_year.start_date if self.fiscal_year else self.start_date,
            date__lte=self.fiscal_year.end_date if self.fiscal_year else self.end_date,
            status='approved'
        ).aggregate(models.Sum('amount'))['amount__sum'] or 0

    def get_spent_percentage(self):
        """حساب نسبة الصرف من الميزانية"""
        if self.total_amount > 0:
            return (self.get_spent_amount() / self.total_amount) * 100
        return 0

    def get_yearly_costs_total(self):
        """حساب إجمالي التكاليف السنوية للابتعاث"""
        return sum(cost.total_year_cost() for cost in self.yearly_costs.all())

    def save(self, *args, **kwargs):
        """تقريب القيم العشرية عند الحفظ"""
        # تقريب القيم المالية إلى منزلتين عشريتين
        if self.total_amount:
            self.total_amount = Decimal(self.total_amount).quantize(Decimal('0.01'))
        if self.exchange_rate:
            self.exchange_rate = Decimal(self.exchange_rate).quantize(Decimal('0.01'))

        super().save(*args, **kwargs)

    def close_current_year_open_new(self):
        """إغلاق السنة الدراسية الحالية وفتح سنة جديدة"""
        if not self.is_current or self.status == 'closed':
            return None

        # تحديث السنة الحالية
        current_year = self.academic_year
        year_parts = current_year.split('-')
        next_year = f"{int(year_parts[0]) + 1}-{int(year_parts[1]) + 1}"

        # إغلاق السنة الحالية
        self.is_current = False
        self.status = 'closed'
        self.save()

        # إنشاء ميزانية جديدة للسنة التالية
        new_budget = ScholarshipBudget.objects.create(
            application=self.application,
            fiscal_year=self.fiscal_year,
            total_amount=self.total_amount,
            start_date=self.end_date + datetime.timedelta(days=1),
            end_date=self.end_date + datetime.timedelta(days=365),
            created_by=self.created_by,
            academic_year=next_year,
            exchange_rate=self.exchange_rate,
            foreign_currency=self.foreign_currency,
            is_current=True
        )

        return new_budget

class YearlyScholarshipCosts(models.Model):
    """نموذج التكاليف السنوية للابتعاث"""
    budget = models.ForeignKey(ScholarshipBudget, on_delete=models.CASCADE,
                               related_name="yearly_costs", verbose_name=_("الميزانية"))
    year_number = models.PositiveIntegerField(_("رقم السنة"), help_text=_("رقم السنة من الابتعاث (1, 2, 3, ...)"))
    academic_year = models.CharField(_("السنة الدراسية"), max_length=9, help_text=_("مثال: 2024-2025"))

    # تفاصيل التكاليف
    travel_tickets = models.DecimalField(_("تذكرة سفر"), max_digits=10, decimal_places=2, default=0)
    monthly_allowance = models.DecimalField(_("المخصص الشهري"), max_digits=10, decimal_places=2, default=0)
    monthly_duration = models.PositiveIntegerField(_("عدد الأشهر"), default=12)
    visa_fees = models.DecimalField(_("رسوم الفيزا"), max_digits=10, decimal_places=2, default=0)
    health_insurance = models.DecimalField(_("التأمين الصحي"), max_digits=10, decimal_places=2, default=0)
    tuition_fees_local = models.DecimalField(_("الرسوم الدراسية (بالدينار)"), max_digits=10, decimal_places=2,
                                             default=0)
    tuition_fees_foreign = models.DecimalField(_("الرسوم الدراسية (بالعملة الأجنبية)"), max_digits=10, decimal_places=2,
                                               default=0)

    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.SET_NULL,
                                    verbose_name=_("السنة المالية"),
                                    related_name="yearly_scholarship_costs",
                                    null=True, blank=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    def total_monthly_allowance(self):
        """إجمالي المخصصات الشهرية"""
        return self.monthly_allowance * self.monthly_duration

    def total_year_cost(self):
        """إجمالي تكلفة السنة"""
        return (
                self.travel_tickets +
                self.total_monthly_allowance() +
                self.visa_fees +
                self.health_insurance +
                self.tuition_fees_local
        )

    def save(self, *args, **kwargs):
        """تقريب القيم العشرية عند الحفظ"""
        # تقريب القيم المالية إلى منزلتين عشريتين
        if self.travel_tickets:
            self.travel_tickets = Decimal(self.travel_tickets).quantize(Decimal('0.01'))
        if self.monthly_allowance:
            self.monthly_allowance = Decimal(self.monthly_allowance).quantize(Decimal('0.01'))
        if self.visa_fees:
            self.visa_fees = Decimal(self.visa_fees).quantize(Decimal('0.01'))
        if self.health_insurance:
            self.health_insurance = Decimal(self.health_insurance).quantize(Decimal('0.01'))
        if self.tuition_fees_local:
            self.tuition_fees_local = Decimal(self.tuition_fees_local).quantize(Decimal('0.01'))
        if self.tuition_fees_foreign:
            self.tuition_fees_foreign = Decimal(self.tuition_fees_foreign).quantize(Decimal('0.01'))

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("تكاليف سنوية للابتعاث")
        verbose_name_plural = _("التكاليف السنوية للابتعاث")
        ordering = ['year_number']
        unique_together = ['budget', 'year_number']

    def __str__(self):
        return f"{self.budget.application.applicant.get_full_name()} - السنة {self.year_number} ({self.academic_year})"


class ScholarshipSettings(models.Model):
    """إعدادات نظام الابتعاث"""
    life_insurance_rate = models.DecimalField(_("معدل التأمين على الحياة"), max_digits=6, decimal_places=4,
                                              default=0.0034, help_text=_("3.4/1000"))
    add_percentage = models.DecimalField(_("نسبة الزيادة"), max_digits=5, decimal_places=2,
                                         default=50.0, help_text=_("نسبة الزيادة على المجموع الكلي (%)"))
    current_fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.SET_NULL,
                                            verbose_name=_("السنة المالية الحالية"),
                                            null=True, blank=True)

    class Meta:
        verbose_name = _("إعدادات نظام الابتعاث")
        verbose_name_plural = _("إعدادات نظام الابتعاث")

    def __str__(self):
        return _("إعدادات نظام الابتعاث")


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
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.SET_NULL,
                                    verbose_name=_("السنة المالية"),
                                    related_name="expenses",
                                    null=True, blank=True)

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

    def save(self, *args, **kwargs):
        # التحقق من تعيين السنة المالية تلقائيًا
        if not self.fiscal_year and self.budget and self.budget.fiscal_year:
            self.fiscal_year = self.budget.fiscal_year

        super().save(*args, **kwargs)


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
        ('scholarship_years_costs', _('تكاليف الابتعاث حسب السنوات')),
        ('fiscal_year_summary', _('ملخص السنة المالية')),
        ('custom', _('تقرير مخصص')),
    ]
    report_type = models.CharField(_("نوع التقرير"), max_length=50, choices=REPORT_TYPE_CHOICES)

    # فلاتر التقرير (يتم تخزينها كـ JSON)
    filters = models.JSONField(_("فلاتر التقرير"), blank=True, null=True)
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.SET_NULL,
                                    verbose_name=_("السنة المالية"),
                                    related_name="reports",
                                    null=True, blank=True)

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
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.SET_NULL,
                                    verbose_name=_("السنة المالية"),
                                    related_name="budget_adjustments",
                                    null=True, blank=True)

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

    def save(self, *args, **kwargs):
        # التحقق من تعيين السنة المالية تلقائيًا
        if not self.fiscal_year and self.budget and self.budget.fiscal_year:
            self.fiscal_year = self.budget.fiscal_year

        super().save(*args, **kwargs)


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
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.SET_NULL,
                                    verbose_name=_("السنة المالية"),
                                    related_name="financial_logs",
                                    null=True, blank=True)

    # نوع العملية
    ACTION_TYPE_CHOICES = [
        ('create', _('إنشاء')),
        ('update', _('تحديث')),
        ('delete', _('حذف')),
        ('approve', _('موافقة')),
        ('reject', _('رفض')),
        ('close', _('إغلاق')),
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

    def save(self, *args, **kwargs):
        # التحقق من تعيين السنة المالية تلقائيًا
        if not self.fiscal_year:
            if self.budget and self.budget.fiscal_year:
                self.fiscal_year = self.budget.fiscal_year
            elif self.expense and self.expense.fiscal_year:
                self.fiscal_year = self.expense.fiscal_year
            elif self.adjustment and self.adjustment.fiscal_year:
                self.fiscal_year = self.adjustment.fiscal_year

        super().save(*args, **kwargs)