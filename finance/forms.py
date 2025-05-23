# في ملف finance/forms.py

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    ScholarshipBudget, Expense, ExpenseCategory, FinancialReport, BudgetAdjustment,
    YearlyScholarshipCosts, FiscalYear, ScholarshipSettings
)
from applications.models import Application


class FiscalYearForm(forms.ModelForm):
    """نموذج إنشاء وتعديل السنة المالية"""

    class Meta:
        model = FiscalYear
        fields = ['year', 'start_date', 'end_date', 'total_budget', 'description']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        # التحقق من تاريخ البداية والنهاية
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError(_("تاريخ البداية لا يمكن أن يكون بعد تاريخ النهاية"))

        return cleaned_data


class FiscalYearFilterForm(forms.Form):
    """نموذج للبحث وفلترة السنوات المالية"""
    status = forms.ChoiceField(
        label=_("الحالة"),
        choices=[('', _('جميع الحالات')), ('open', _('مفتوحة')), ('closed', _('مغلقة'))],
        required=False
    )
    year_from = forms.IntegerField(
        label=_("من سنة"),
        required=False
    )
    year_to = forms.IntegerField(
        label=_("إلى سنة"),
        required=False
    )
    search = forms.CharField(
        label=_("بحث"),
        required=False
    )


class ScholarshipBudgetForm(forms.ModelForm):
    """نموذج إنشاء وتعديل ميزانية ابتعاث"""

    class Meta:
        model = ScholarshipBudget
        fields = ['fiscal_year', 'total_amount', 'start_date', 'end_date',
                 'foreign_currency', 'exchange_rate', 'academic_year', 'notes']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # عرض فقط السنوات المالية المفتوحة
        self.fields['fiscal_year'].queryset = FiscalYear.objects.filter(status='open')

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        # التحقق من تاريخ البداية والنهاية
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError(_("تاريخ البداية لا يمكن أن يكون بعد تاريخ النهاية"))

        return cleaned_data


class ExpenseForm(forms.ModelForm):
    """نموذج إنشاء وتعديل المصروفات"""

    class Meta:
        model = Expense
        fields = ['fiscal_year', 'category', 'amount', 'date', 'description', 'receipt_number', 'receipt_file']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.budget = kwargs.pop('budget', None)
        super().__init__(*args, **kwargs)

        # عرض فقط السنوات المالية المفتوحة
        self.fields['fiscal_year'].queryset = FiscalYear.objects.filter(status='open')

        # تعيين السنة المالية تلقائيًا إذا كانت الميزانية مرتبطة بسنة مالية
        if self.budget and self.budget.fiscal_year and not self.instance.pk:
            self.fields['fiscal_year'].initial = self.budget.fiscal_year

        # تعيين الميزانية تلقائيًا إذا تم تمريرها
        if self.budget and not self.instance.pk:
            self.instance.budget = self.budget

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')

        # التحقق من أن المبلغ أكبر من صفر
        if amount <= 0:
            raise forms.ValidationError(_("يجب أن يكون المبلغ أكبر من صفر"))

        # التحقق من توفر المبلغ في الميزانية إذا كان هناك ميزانية محددة
        if self.budget:
            remaining = self.budget.get_remaining_amount()
            if self.instance.pk:  # في حالة التعديل
                current_amount = Expense.objects.get(pk=self.instance.pk).amount
                if amount - current_amount > remaining:
                    raise forms.ValidationError(_("المبلغ المدخل يتجاوز المبلغ المتبقي في الميزانية"))
            else:  # في حالة الإنشاء
                if amount > remaining:
                    raise forms.ValidationError(_("المبلغ المدخل يتجاوز المبلغ المتبقي في الميزانية"))

        return amount


class ExpenseCategoryForm(forms.ModelForm):
    """نموذج إنشاء وتعديل فئات المصروفات"""

    class Meta:
        model = ExpenseCategory
        fields = ['name', 'description', 'code']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class ExpenseApprovalForm(forms.ModelForm):
    """نموذج الموافقة أو رفض المصروفات"""

    class Meta:
        model = Expense
        fields = ['status', 'approval_notes']
        widgets = {
            'approval_notes': forms.Textarea(attrs={'rows': 3}),
        }


class BudgetAdjustmentForm(forms.ModelForm):
    """نموذج تعديل الميزانية"""

    class Meta:
        model = BudgetAdjustment
        fields = ['fiscal_year', 'amount', 'date', 'reason', 'adjustment_type']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.budget = kwargs.pop('budget', None)
        super().__init__(*args, **kwargs)

        # عرض فقط السنوات المالية المفتوحة
        self.fields['fiscal_year'].queryset = FiscalYear.objects.filter(status='open')

        # تعيين السنة المالية تلقائيًا إذا كانت الميزانية مرتبطة بسنة مالية
        if self.budget and self.budget.fiscal_year and not self.instance.pk:
            self.fields['fiscal_year'].initial = self.budget.fiscal_year

        # تعيين الميزانية تلقائيًا إذا تم تمريرها
        if self.budget and not self.instance.pk:
            self.instance.budget = self.budget


class BudgetAdjustmentApprovalForm(forms.ModelForm):
    """نموذج الموافقة أو رفض تعديلات الميزانية"""

    class Meta:
        model = BudgetAdjustment
        fields = ['status']


class FinancialReportForm(forms.ModelForm):
    """نموذج إنشاء وتعديل التقارير المالية"""

    class Meta:
        model = FinancialReport
        fields = ['title', 'description', 'report_type', 'fiscal_year', 'is_public']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # إضافة خيار السنة المالية
        self.fields['fiscal_year'].queryset = FiscalYear.objects.all().order_by('-year')
        self.fields['fiscal_year'].required = False


class DateRangeForm(forms.Form):
    """نموذج لتحديد نطاق تاريخي للتقارير"""
    start_date = forms.DateField(label=_("تاريخ البداية"), widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(label=_("تاريخ النهاية"), widget=forms.DateInput(attrs={'type': 'date'}))


class BudgetFilterForm(forms.Form):
    """نموذج للبحث وفلترة الميزانيات"""
    status = forms.ChoiceField(
        label=_("الحالة"),
        choices=[('', _('جميع الحالات'))] + list(ScholarshipBudget.STATUS_CHOICES),
        required=False
    )
    fiscal_year = forms.ModelChoiceField(
        label=_("السنة المالية"),
        queryset=FiscalYear.objects.all().order_by('-year'),
        required=False
    )
    start_date = forms.DateField(
        label=_("من تاريخ"),
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    end_date = forms.DateField(
        label=_("إلى تاريخ"),
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    min_amount = forms.DecimalField(
        label=_("الحد الأدنى للمبلغ"),
        required=False
    )
    max_amount = forms.DecimalField(
        label=_("الحد الأعلى للمبلغ"),
        required=False
    )
    search = forms.CharField(
        label=_("بحث"),
        required=False
    )


class ExpenseFilterForm(forms.Form):
    """نموذج للبحث وفلترة المصروفات"""
    status = forms.ChoiceField(
        label=_("الحالة"),
        choices=[('', _('جميع الحالات'))] + list(Expense.STATUS_CHOICES),
        required=False
    )
    fiscal_year = forms.ModelChoiceField(
        label=_("السنة المالية"),
        queryset=FiscalYear.objects.all().order_by('-year'),
        required=False
    )
    category = forms.ModelChoiceField(
        label=_("الفئة"),
        queryset=ExpenseCategory.objects.all(),
        required=False
    )
    start_date = forms.DateField(
        label=_("من تاريخ"),
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    end_date = forms.DateField(
        label=_("إلى تاريخ"),
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    min_amount = forms.DecimalField(
        label=_("الحد الأدنى للمبلغ"),
        required=False
    )
    max_amount = forms.DecimalField(
        label=_("الحد الأعلى للمبلغ"),
        required=False
    )
    search = forms.CharField(
        label=_("بحث"),
        required=False
    )


class YearlyScholarshipCostsForm(forms.ModelForm):
    class Meta:
        model = YearlyScholarshipCosts
        fields = ['year_number', 'academic_year', 'fiscal_year', 'travel_tickets', 'monthly_allowance',
                  'monthly_duration', 'visa_fees', 'health_insurance',
                  'tuition_fees_foreign', 'tuition_fees_local']
        widgets = {
            'academic_year': forms.Select(choices=[(f"{y}-{y + 1}", f"{y}-{y + 1}")
                                                   for y in range(2020, 2030)]),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # عرض فقط السنوات المالية المفتوحة
        self.fields['fiscal_year'].queryset = FiscalYear.objects.filter(status='open')
        self.fields['fiscal_year'].required = False


class ScholarshipSettingsForm(forms.ModelForm):
    """نموذج إعدادات نظام الابتعاث"""

    class Meta:
        model = ScholarshipSettings
        fields = ['life_insurance_rate', 'add_percentage', 'current_fiscal_year']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # عرض فقط السنوات المالية المفتوحة للسنة الحالية
        self.fields['current_fiscal_year'].queryset = FiscalYear.objects.filter(status='open')


class ScholarshipYearFormSet(forms.BaseFormSet):
    """مجموعة نماذج مرنة لإدخال بيانات السنوات الدراسية"""

    def clean(self):
        """التحقق من صحة البيانات المدخلة للسنوات الدراسية"""
        if any(self.errors):
            return

        # فقط التحقق من السنوات التي تم تضمينها
        included_forms = [form for form in self.forms if form.cleaned_data and form.cleaned_data.get('include_year')]

        if not included_forms:
            raise forms.ValidationError(_("يجب تضمين سنة دراسية واحدة على الأقل"))

        year_numbers = []
        for form in included_forms:
            year_number = form.cleaned_data.get('year_number')
            # التحقق من عدم تكرار رقم السنة
            if year_number in year_numbers:
                raise forms.ValidationError(_("لا يمكن تكرار رقم السنة"))
            year_numbers.append(year_number)

        # التأكد من أن أرقام السنوات متسلسلة
        year_numbers.sort()
        for i, year_num in enumerate(year_numbers, start=1):
            if year_num != i:
                raise forms.ValidationError(_("يجب أن تكون أرقام السنوات متسلسلة تبدأ من 1"))


class YearlyScholarshipCostsInlineForm(forms.ModelForm):
    """نموذج تكاليف السنة الدراسية أثناء إنشاء الميزانية"""
    include_year = forms.BooleanField(
        label=_("تضمين هذه السنة"),
        required=False,
        initial=True
    )

    class Meta:
        model = YearlyScholarshipCosts
        fields = ['year_number', 'academic_year', 'travel_tickets', 'monthly_allowance',
                  'monthly_duration', 'visa_fees', 'health_insurance',
                  'tuition_fees_foreign', 'tuition_fees_local']
        widgets = {
            'academic_year': forms.Select(choices=[(f"{y}-{y + 1}", f"{y}-{y + 1}")
                                                   for y in range(2020, 2030)]),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # حذف حقل السنة المالية
        if 'fiscal_year' in self.fields:
            del self.fields['fiscal_year']

        # تعديل جميع الحقول المالية لتقييدها بمنزلتين عشريتين فقط
        decimal_fields = [
            'travel_tickets', 'monthly_allowance', 'visa_fees',
            'health_insurance', 'tuition_fees_foreign', 'tuition_fees_local'
        ]

        for field_name in decimal_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'step': '0.01',
                    'pattern': r'^\d+(\.\d{1,2})?$',
                    'title': _('أدخل رقمًا بمنزلتين عشريتين كحد أقصى')
                })

    def clean(self):
        cleaned_data = super().clean()
        # لا نتحقق من البيانات إذا لم يتم تضمين هذه السنة
        if not cleaned_data.get('include_year'):
            return cleaned_data

        required_fields = ['year_number', 'academic_year', 'monthly_allowance', 'monthly_duration']
        for field in required_fields:
            if not cleaned_data.get(field):
                self.add_error(field, _("هذا الحقل مطلوب"))

        return cleaned_data


class ScholarshipBudgetWithYearsForm(forms.ModelForm):
    """نموذج إنشاء ميزانية ابتعاث مع التركيز على سنوات الدراسة"""

    num_years = forms.IntegerField(
        label=_("عدد سنوات الدراسة"),
        min_value=1,
        max_value=6,
        initial=3,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '6'})
    )

    class Meta:
        model = ScholarshipBudget
        fields = ['fiscal_year', 'total_amount', 'start_date', 'end_date',
                  'foreign_currency', 'exchange_rate', 'academic_year', 'notes']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # عرض فقط السنوات المالية المفتوحة
        self.fields['fiscal_year'].queryset = FiscalYear.objects.filter(status='open')

        # تعديل جميع الحقول المالية لتقييدها بمنزلتين عشريتين فقط
        decimal_fields = ['total_amount', 'exchange_rate']

        for field_name in decimal_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'step': '0.01',
                    'pattern': r'^\d+(\.\d{1,2})?$',
                    'title': _('أدخل رقمًا بمنزلتين عشريتين كحد أقصى')
                })

        # تغيير المسميات والوصف
        self.fields['total_amount'].label = _("إجمالي كلفة الابتعاث")
        self.fields['total_amount'].help_text = _("المبلغ الإجمالي المخصص لكامل فترة الابتعاث")