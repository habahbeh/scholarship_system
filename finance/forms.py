# في ملف finance/forms.py

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import ScholarshipBudget, Expense, ExpenseCategory, FinancialReport, BudgetAdjustment, YearlyScholarshipCosts
from applications.models import Application


class ScholarshipBudgetForm(forms.ModelForm):
    """نموذج إنشاء وتعديل ميزانية ابتعاث"""

    class Meta:
        model = ScholarshipBudget
        fields = ['total_amount', 'start_date', 'end_date', 'tuition_fees', 'monthly_stipend',
                  'travel_allowance', 'health_insurance', 'books_allowance', 'research_allowance',
                  'conference_allowance', 'other_expenses', 'notes']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        # التحقق من تاريخ البداية والنهاية
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError(_("تاريخ البداية لا يمكن أن يكون بعد تاريخ النهاية"))

        # التحقق من أن مجموع الفئات يساوي إجمالي الميزانية
        total_amount = cleaned_data.get('total_amount') or 0
        tuition_fees = cleaned_data.get('tuition_fees') or 0
        monthly_stipend = cleaned_data.get('monthly_stipend') or 0
        travel_allowance = cleaned_data.get('travel_allowance') or 0
        health_insurance = cleaned_data.get('health_insurance') or 0
        books_allowance = cleaned_data.get('books_allowance') or 0
        research_allowance = cleaned_data.get('research_allowance') or 0
        conference_allowance = cleaned_data.get('conference_allowance') or 0
        other_expenses = cleaned_data.get('other_expenses') or 0

        sum_categories = (tuition_fees + monthly_stipend + travel_allowance +
                          health_insurance + books_allowance + research_allowance +
                          conference_allowance + other_expenses)

        if abs(total_amount - sum_categories) > 0.01:  # تسامح صغير للأرقام العشرية
            raise forms.ValidationError(_("مجموع فئات الميزانية يجب أن يساوي إجمالي الميزانية"))

        return cleaned_data


class ExpenseForm(forms.ModelForm):
    """نموذج إنشاء وتعديل المصروفات"""

    class Meta:
        model = Expense
        fields = ['category', 'amount', 'date', 'description', 'receipt_number', 'receipt_file']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.budget = kwargs.pop('budget', None)
        super().__init__(*args, **kwargs)

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
        fields = ['amount', 'date', 'reason', 'adjustment_type']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.budget = kwargs.pop('budget', None)
        super().__init__(*args, **kwargs)

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
        fields = ['title', 'description', 'report_type', 'is_public']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


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
        fields = ['year_number', 'academic_year', 'travel_tickets', 'monthly_allowance',
                'monthly_duration', 'visa_fees', 'health_insurance',
                'tuition_fees_foreign', 'tuition_fees_local']
        widgets = {
            'academic_year': forms.Select(choices=[(f"{y}-{y+1}", f"{y}-{y+1}")
                                                for y in range(2020, 2030)]),
        }