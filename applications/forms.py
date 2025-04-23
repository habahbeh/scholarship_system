from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Application, ApplicationStatus, ApprovalAttachment, Document


# New workflow forms
class ApplicationStatusUpdateForm(forms.ModelForm):
    """نموذج تحديث حالة الطلب"""

    class Meta:
        model = Application
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        # تمرير حالات الطلب المتاحة للاختيار بينها
        available_statuses = kwargs.pop('available_statuses', None)
        super().__init__(*args, **kwargs)

        if available_statuses:
            self.fields['status'].queryset = available_statuses


class RequirementsCheckForm(forms.Form):
    """نموذج مطابقة الشروط"""
    meets_requirements = forms.ChoiceField(
        label=_("مطابقة الشروط"),
        choices=[
            ('yes', _("مطابق للشروط")),
            ('no', _("غير مطابق للشروط")),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    notes = forms.CharField(
        label=_("ملاحظات"),
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )


class HigherCommitteeApprovalForm(forms.Form):
    """نموذج موافقة اللجنة العليا"""
    APPROVAL_CHOICES = [
        ('yes', _('موافق')),
        ('no', _('غير موافق')),
    ]

    is_approved = forms.ChoiceField(
        label=_('قرار اللجنة العليا'),
        choices=APPROVAL_CHOICES,
        widget=forms.RadioSelect(),
        required=True
    )

    attachment = forms.FileField(
        label=_('مرفق الموافقة'),
        required=False,
        help_text=_('مطلوب فقط في حالة الموافقة')
    )

    notes = forms.CharField(
        label=_('ملاحظات'),
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        is_approved = cleaned_data.get('is_approved')
        attachment = cleaned_data.get('attachment')

        if is_approved == 'yes' and not attachment:
            self.add_error('attachment', _('يجب إرفاق مستند الموافقة في حالة الموافقة'))

        return cleaned_data


class FacultyCouncilApprovalForm(forms.Form):
    """نموذج موافقة مجلس الكلية"""
    APPROVAL_CHOICES = [
        ('yes', _('موافق')),
        ('no', _('غير موافق')),
    ]

    is_approved = forms.ChoiceField(
        label=_('قرار مجلس الكلية'),
        choices=APPROVAL_CHOICES,
        widget=forms.RadioSelect(),
        required=True
    )

    attachment = forms.FileField(
        label=_('مرفق الموافقة'),
        required=False,
        help_text=_('مطلوب فقط في حالة الموافقة')
    )

    notes = forms.CharField(
        label=_('ملاحظات'),
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        is_approved = cleaned_data.get('is_approved')
        attachment = cleaned_data.get('attachment')

        if is_approved == 'yes' and not attachment:
            self.add_error('attachment', _('يجب إرفاق مستند الموافقة في حالة الموافقة'))

        return cleaned_data


class PresidentApprovalForm(forms.Form):
    """نموذج موافقة رئيس الجامعة"""
    APPROVAL_CHOICES = [
        ('yes', _('موافق')),
        ('no', _('غير موافق')),
    ]

    is_approved = forms.ChoiceField(
        label=_('قرار رئيس الجامعة'),
        choices=APPROVAL_CHOICES,
        widget=forms.RadioSelect(),
        required=True
    )

    attachment = forms.FileField(
        label=_('مرفق الموافقة'),
        required=False,
        help_text=_('مطلوب فقط في حالة الموافقة')
    )

    notes = forms.CharField(
        label=_('ملاحظات'),
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        is_approved = cleaned_data.get('is_approved')
        attachment = cleaned_data.get('attachment')

        if is_approved == 'yes' and not attachment:
            self.add_error('attachment', _('يجب إرفاق مستند الموافقة في حالة الموافقة'))

        return cleaned_data

# Standard application forms
class ApplicationForm(forms.ModelForm):
    """نموذج التقديم على فرصة ابتعاث"""

    class Meta:
        model = Application
        fields = ['motivation_letter', 'research_proposal', 'comments', 'acceptance_letter', 'acceptance_university']
        widgets = {
            'motivation_letter': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'research_proposal': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'acceptance_letter': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'acceptance_university': forms.TextInput(attrs={'class': 'form-control'}),
        }


class DocumentForm(forms.ModelForm):
    """نموذج رفع المستندات"""

    class Meta:
        model = Document
        fields = ['name', 'description', 'file', 'is_required']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'is_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DocumentUploadForm(forms.Form):
    """نموذج رفع مستند"""
    DOCUMENT_TYPES = (
        ('cv', _('السيرة الذاتية')),
        ('transcript', _('كشف الدرجات')),
        ('certificate', _('الشهادة العلمية')),
        ('id', _('إثبات الهوية')),
        ('language', _('شهادة اللغة')),
        ('recommendation', _('رسالة توصية')),
        ('acceptance', _('خطاب القبول')),
        ('research', _('خطة البحث')),
        ('other', _('مستند آخر')),
    )

    document_type = forms.ChoiceField(
        label=_("نوع المستند"),
        choices=DOCUMENT_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    description = forms.CharField(
        label=_("وصف المستند"),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('وصف اختياري للمستند')})
    )

    file = forms.FileField(
        label=_("الملف"),
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )


class ApplicationStatusForm(forms.Form):
    """نموذج تغيير حالة الطلب"""
    comment = forms.CharField(
        label=_("تعليق"),
        required=False,
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('أدخل تعليقًا اختياريًا لشرح سبب التغيير')})
    )


class ApplicationFilterForm(forms.Form):
    """نموذج تصفية الطلبات"""
    STATUS_CHOICES = (
        ('', _('كل الحالات')),
        ('pending', _('قيد الانتظار')),
        ('review', _('قيد المراجعة')),
        ('accepted', _('مقبول')),
        ('rejected', _('مرفوض')),
    )

    status = forms.ChoiceField(
        label=_("الحالة"),
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    scholarship = forms.CharField(
        label=_("فرصة الابتعاث"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('اسم الفرصة')})
    )

    date_from = forms.DateField(
        label=_("من تاريخ"),
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    date_to = forms.DateField(
        label=_("إلى تاريخ"),
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    search = forms.CharField(
        label=_("بحث"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('بحث...')})
    )