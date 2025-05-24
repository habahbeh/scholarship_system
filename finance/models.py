# في ملف finance/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone
from applications.models import Application
import datetime
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal, ROUND_HALF_UP


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
    """نموذج ميزانية الابتعاث"""

    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('pending', _('قيد المراجعة')),
        ('active', _('نشطة')),
        ('closed', _('مغلقة')),
        ('cancelled', _('ملغية')),
    ]

    # العلاقات الأساسية
    application = models.OneToOneField(
        'applications.Application',
        on_delete=models.CASCADE,
        related_name='budget',
        verbose_name=_('طلب الابتعاث')
    )

    fiscal_year = models.ForeignKey(
        'FiscalYear',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='scholarship_budgets',
        verbose_name=_('السنة المالية')
    )

    # المعلومات الأساسية
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('إجمالي الميزانية'),
        help_text=_('إجمالي مبلغ الميزانية بالدينار الأردني')
    )

    start_date = models.DateField(
        verbose_name=_('تاريخ البداية'),
        help_text=_('تاريخ بداية صرف الميزانية')
    )

    end_date = models.DateField(
        verbose_name=_('تاريخ النهاية'),
        help_text=_('تاريخ انتهاء صرف الميزانية')
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name=_('حالة الميزانية')
    )


    # تفاصيل الفئات المالية
    tuition_fees = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('الرسوم الدراسية'),
        help_text=_('إجمالي الرسوم الدراسية بالدينار الأردني')
    )

    monthly_stipend = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('المخصص الشهري'),
        help_text=_('إجمالي المخصصات الشهرية لجميع السنوات')
    )

    travel_allowance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('مخصص السفر'),
        help_text=_('تكلفة تذاكر السفر')
    )

    health_insurance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('التأمين الصحي'),
        help_text=_('تكلفة التأمين الصحي لجميع السنوات')
    )

    other_expenses = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('مصاريف أخرى'),
        help_text=_('التأمين على الحياة، النسبة الإضافية، رسوم الفيزا، إلخ')
    )

    # معلومات العملة والصرف
    exchange_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal('0.7100'),
        validators=[MinValueValidator(Decimal('0.0001'))],
        verbose_name=_('سعر الصرف'),
        help_text=_('سعر صرف العملة الأجنبية مقابل الدينار الأردني')
    )

    foreign_currency = models.CharField(
        max_length=3,
        default='GBP',
        verbose_name=_('العملة الأجنبية'),
        help_text=_('رمز العملة الأجنبية (مثل: GBP, USD, EUR)')
    )

    # معلومات السنة الدراسية
    academic_year = models.CharField(
        max_length=20,
        verbose_name=_('السنة الدراسية'),
        help_text=_('السنة الدراسية (مثال: 2024-2025)')
    )

    is_current = models.BooleanField(
        default=True,
        verbose_name=_('السنة الحالية'),
        help_text=_('هل هذه هي السنة الدراسية الحالية للمبتعث؟')
    )

    # معلومات التتبع
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_budgets',
        verbose_name=_('أنشأ بواسطة')
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('تاريخ الإنشاء')
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('تاريخ التحديث')
    )

    # الملاحظات
    notes = models.TextField(
        blank=True,
        verbose_name=_('ملاحظات'),
        help_text=_('ملاحظات إضافية حول الميزانية')
    )

    class Meta:
        verbose_name = _('ميزانية ابتعاث')
        verbose_name_plural = _('ميزانيات الابتعاث')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['fiscal_year']),
            models.Index(fields=['academic_year']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.application.applicant.get_full_name()} - {self.academic_year} - {self.total_amount} د.أ"

    def save(self, *args, **kwargs):
        """حفظ محسن مع التحقق من البيانات"""
        # التأكد من أن تاريخ النهاية بعد تاريخ البداية
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValueError(_("تاريخ النهاية يجب أن يكون بعد تاريخ البداية"))

        # تحديث حالة السنة الحالية
        if self.is_current:
            # إلغاء تحديد السنة الحالية للميزانيات الأخرى لنفس المتقدم
            ScholarshipBudget.objects.filter(
                application__applicant=self.application.applicant
            ).exclude(id=self.id).update(is_current=False)

        super().save(*args, **kwargs)

    def get_insurance_amount(self):
        """
        حساب مبلغ التأمين على الحياة بناءً على إجمالي التكاليف السنوية
        """
        from decimal import Decimal

        # الحصول على إعدادات المنح الدراسية
        settings = ScholarshipSettings.get_settings()
        life_insurance_rate = settings.life_insurance_rate

        # حساب إجمالي التكاليف السنوية
        yearly_costs_total = self.get_yearly_costs_total()

        # حساب التأمين
        insurance_rate_decimal = Decimal(life_insurance_rate) / Decimal('100')
        insurance_amount = yearly_costs_total * insurance_rate_decimal

        return insurance_amount

    def get_true_cost(self):
        """
        حساب التكلفة الحقيقية (التكاليف السنوية + التأمين)
        """
        return self.get_yearly_costs_total() + self.get_insurance_amount()

    def get_additional_amount(self):
        """
        حساب مبلغ النسبة الإضافية بناءً على التكلفة الحقيقية
        """
        from decimal import Decimal

        # الحصول على إعدادات المنح الدراسية
        settings = ScholarshipSettings.get_settings()
        add_percentage = settings.add_percentage

        # حساب التكلفة الحقيقية
        true_cost = self.get_true_cost()

        # حساب النسبة الإضافية
        add_percentage_decimal = Decimal(add_percentage) / Decimal('100')
        additional_amount = true_cost * add_percentage_decimal

        return additional_amount

    def calculate_total_amount(self):
        """
        حساب المبلغ الإجمالي للميزانية
        (التكاليف السنوية + التأمين + النسبة الإضافية)
        """
        true_cost = self.get_true_cost()
        additional_amount = self.get_additional_amount()

        return true_cost + additional_amount

    # دالة لتفعيل الميزانية
    def activate(self):
        """تفعيل الميزانية بعد المراجعة"""
        if self.status == 'draft':
            self.status = 'active'
            self.save()
            return True
        return False

    # دوال الحساب المحسنة
    def get_spent_amount(self):
        """حساب إجمالي المبلغ المصروف مع تقريب دقيق ومتسق"""
        total = self.expenses.filter(status='approved').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

        return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def get_remaining_amount(self):
        """حساب المبلغ المتبقي مع تقريب دقيق ومتسق"""
        spent = self.get_spent_amount()
        remaining = self.total_amount - spent

        return remaining.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def get_spent_percentage(self):
        """حساب نسبة الصرف مع تقريب دقيق ومتسق"""
        if self.total_amount <= 0:
            return Decimal('0.00')

        spent = self.get_spent_amount()
        percentage = (spent / self.total_amount * 100)

        return percentage.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def get_yearly_costs_total(self):
        """حساب إجمالي التكاليف السنوية بنفس طريقة حساب الميزانية الأصلية"""
        # الحصول على الإعدادات
        try:
            settings = ScholarshipSettings.objects.first()
            if not settings:
                # استخدام القيم الافتراضية
                life_insurance_rate = Decimal('0.0034')
                add_percentage = Decimal('50.0')
            else:
                life_insurance_rate = settings.life_insurance_rate
                add_percentage = settings.add_percentage
        except:
            life_insurance_rate = Decimal('0.0034')
            add_percentage = Decimal('50.0')

        # حساب إجمالي التكاليف الأساسية
        base_total = Decimal('0.00')

        for cost in self.yearly_costs.all():
            monthly_total = (cost.monthly_allowance * cost.monthly_duration).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            year_cost = (
                    cost.travel_tickets +
                    monthly_total +
                    cost.visa_fees +
                    cost.health_insurance +
                    cost.tuition_fees_local
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            base_total += year_cost

        # تطبيق نفس الحسابات المستخدمة في إنشاء الميزانية
        # إضافة التأمين على الحياة
        if life_insurance_rate > 0:
            insurance = (base_total * life_insurance_rate).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            base_total += insurance

        # إضافة النسبة الإضافية
        if add_percentage > 0:
            additional = (base_total * (add_percentage / Decimal('100'))).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            base_total += additional

        return base_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def recalculate_total_amount(self):
        """إعادة حساب إجمالي الميزانية بناءً على التكاليف السنوية الحالية"""
        calculated_total = self.get_yearly_costs_total()

        # تحديث إجمالي الميزانية
        old_total = self.total_amount
        self.total_amount = calculated_total
        self.save()

        return {
            'old_total': old_total,
            'new_total': calculated_total,
            'difference': abs(calculated_total - old_total)
        }

    def validate_budget_calculation(self, tolerance=Decimal('0.10')):
        """التحقق من صحة حساب الميزانية"""
        calculated_total = self.get_yearly_costs_total()
        difference = abs(self.total_amount - calculated_total)

        return {
            'is_valid': difference <= tolerance,
            'saved_total': self.total_amount,
            'calculated_total': calculated_total,
            'difference': difference,
            'tolerance': tolerance
        }

    # دوال مساعدة إضافية
    def get_duration_in_days(self):
        """حساب مدة الميزانية بالأيام"""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return 0

    def get_duration_in_months(self):
        """حساب مدة الميزانية بالأشهر تقريباً"""
        days = self.get_duration_in_days()
        return round(days / 30.44)  # متوسط أيام الشهر

    def is_expired(self):
        """التحقق من انتهاء صلاحية الميزانية"""
        if self.end_date:
            return timezone.now().date() > self.end_date
        return False

    def is_active_now(self):
        """التحقق من أن الميزانية نشطة حالياً"""
        now = timezone.now().date()
        return (
                self.status == 'active' and
                self.start_date <= now <= self.end_date
        )

    def get_category_percentage(self, category_amount):
        """حساب نسبة فئة معينة من إجمالي الميزانية"""
        if self.total_amount <= 0:
            return Decimal('0.00')

        percentage = (category_amount / self.total_amount * 100)
        return percentage.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def can_be_modified(self):
        """التحقق من إمكانية تعديل الميزانية"""
        return self.status in ['draft', 'pending', 'active']

    def can_be_deleted(self):
        """التحقق من إمكانية حذف الميزانية"""
        # لا يمكن حذف الميزانية إذا كانت لها مصروفات معتمدة
        has_approved_expenses = self.expenses.filter(status='approved').exists()
        return not has_approved_expenses and self.status != 'closed'


class YearlyScholarshipCosts(models.Model):
    """نموذج التكاليف السنوية للابتعاث"""

    # العلاقات الأساسية
    budget = models.ForeignKey(
        ScholarshipBudget,
        on_delete=models.CASCADE,
        related_name='yearly_costs',
        verbose_name=_('الميزانية')
    )

    fiscal_year = models.ForeignKey(
        'FiscalYear',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='yearly_scholarship_costs',
        verbose_name=_('السنة المالية')
    )

    # معلومات السنة
    year_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name=_('رقم السنة'),
        help_text=_('رقم السنة الدراسية (1، 2، 3، إلخ)')
    )

    academic_year = models.CharField(
        max_length=20,
        verbose_name=_('السنة الدراسية'),
        help_text=_('السنة الدراسية (مثال: 2024-2025)')
    )

    # التكاليف الأساسية
    travel_tickets = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('تذاكر السفر'),
        help_text=_('تكلفة تذاكر السفر للسنة بالدينار الأردني')
    )

    monthly_allowance = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('1000.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('المخصص الشهري'),
        help_text=_('المبلغ الشهري للمعيشة بالدينار الأردني')
    )

    monthly_duration = models.PositiveSmallIntegerField(
        default=12,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name=_('عدد الأشهر'),
        help_text=_('عدد أشهر صرف المخصص الشهري')
    )

    visa_fees = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('رسوم الفيزا'),
        help_text=_('رسوم الحصول على الفيزا بالدينار الأردني')
    )

    health_insurance = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('500.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('التأمين الصحي'),
        help_text=_('تكلفة التأمين الصحي للسنة بالدينار الأردني')
    )

    # الرسوم الدراسية
    tuition_fees_foreign = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('الرسوم الدراسية (عملة أجنبية)'),
        help_text=_('الرسوم الدراسية بالعملة الأجنبية')
    )

    tuition_fees_local = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('الرسوم الدراسية (دينار أردني)'),
        help_text=_('الرسوم الدراسية بالدينار الأردني')
    )

    # معلومات التتبع
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('تاريخ الإنشاء')
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('تاريخ التحديث')
    )

    # الملاحظات
    notes = models.TextField(
        blank=True,
        verbose_name=_('ملاحظات'),
        help_text=_('ملاحظات خاصة بهذه السنة الدراسية')
    )

    class Meta:
        verbose_name = _('التكاليف السنوية للابتعاث')
        verbose_name_plural = _('التكاليف السنوية للابتعاث')
        ordering = ['budget', 'year_number']
        unique_together = ['budget', 'year_number']
        indexes = [
            models.Index(fields=['budget', 'year_number']),
            models.Index(fields=['fiscal_year']),
            models.Index(fields=['academic_year']),
        ]

    def __str__(self):
        return f"{self.budget.application.applicant.get_full_name()} - السنة {self.year_number} ({self.academic_year})"

    def save(self, *args, **kwargs):
        """حفظ محسن مع التحقق من البيانات"""
        # التأكد من أن الرسوم المحلية محسوبة إذا لم تكن موجودة
        if self.tuition_fees_foreign > 0 and self.tuition_fees_local == 0:
            if self.budget and self.budget.exchange_rate > 0:
                self.tuition_fees_local = (
                        self.tuition_fees_foreign * self.budget.exchange_rate
                ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # تعيين السنة المالية من الميزانية إذا لم تكن محددة
        if not self.fiscal_year and self.budget and self.budget.fiscal_year:
            self.fiscal_year = self.budget.fiscal_year

        super().save(*args, **kwargs)

    def total_year_cost(self):
        """حساب إجمالي تكلفة السنة مع تقريب دقيق ومتسق"""
        monthly_total = (self.monthly_allowance * self.monthly_duration).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        total = (
                self.travel_tickets +
                monthly_total +
                self.visa_fees +
                self.health_insurance +
                self.tuition_fees_local
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return total

    def get_monthly_total(self):
        """حساب إجمالي المخصصات الشهرية"""
        return (self.monthly_allowance * self.monthly_duration).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

    def get_tuition_in_foreign_currency(self):
        """حساب الرسوم الدراسية بالعملة الأجنبية من المبلغ المحلي"""
        if self.budget and self.budget.exchange_rate > 0 and self.tuition_fees_local > 0:
            return (self.tuition_fees_local / self.budget.exchange_rate).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        return self.tuition_fees_foreign

    def update_tuition_from_foreign(self, foreign_amount, exchange_rate):
        """تحديث الرسوم المحلية من المبلغ الأجنبي"""
        self.tuition_fees_foreign = Decimal(str(foreign_amount)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        self.tuition_fees_local = (
                self.tuition_fees_foreign * Decimal(str(exchange_rate))
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.save()

    def get_cost_breakdown(self):
        """إرجاع تفكيك مفصل للتكاليف"""
        monthly_total = self.get_monthly_total()
        year_total = self.total_year_cost()

        return {
            'travel_tickets': self.travel_tickets,
            'monthly_allowance': self.monthly_allowance,
            'monthly_duration': self.monthly_duration,
            'monthly_total': monthly_total,
            'visa_fees': self.visa_fees,
            'health_insurance': self.health_insurance,
            'tuition_fees_foreign': self.tuition_fees_foreign,
            'tuition_fees_local': self.tuition_fees_local,
            'year_total': year_total
        }

    def get_cost_percentages(self):
        """حساب نسب التكاليف"""
        total = self.total_year_cost()
        if total <= 0:
            return {}

        monthly_total = self.get_monthly_total()

        return {
            'travel_percentage': (self.travel_tickets / total * 100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP),
            'monthly_percentage': (monthly_total / total * 100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP),
            'visa_percentage': (self.visa_fees / total * 100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP),
            'health_percentage': (self.health_insurance / total * 100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP),
            'tuition_percentage': (self.tuition_fees_local / total * 100).quantize(Decimal('0.1'),
                                                                                   rounding=ROUND_HALF_UP),
        }

    def is_first_year(self):
        """التحقق من أن هذه هي السنة الأولى"""
        return self.year_number == 1

    def is_last_year(self):
        """التحقق من أن هذه هي السنة الأخيرة"""
        max_year = self.budget.yearly_costs.aggregate(
            max_year=models.Max('year_number')
        )['max_year']
        return self.year_number == max_year

    def get_next_year(self):
        """الحصول على السنة التالية"""
        try:
            return self.budget.yearly_costs.get(year_number=self.year_number + 1)
        except YearlyScholarshipCosts.DoesNotExist:
            return None

    def get_previous_year(self):
        """الحصول على السنة السابقة"""
        if self.year_number <= 1:
            return None
        try:
            return self.budget.yearly_costs.get(year_number=self.year_number - 1)
        except YearlyScholarshipCosts.DoesNotExist:
            return None


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

    @classmethod
    def get_settings(cls):
        """الحصول على إعدادات النظام أو إنشاء إعدادات افتراضية إذا لم تكن موجودة"""
        settings = cls.objects.first()
        if not settings:
            settings = cls.objects.create(
                life_insurance_rate=Decimal('0.0034'),
                add_percentage=Decimal('50.0')
            )
        return settings


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