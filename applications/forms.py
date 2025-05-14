from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    Application, ApplicationStatus, ApprovalAttachment, Document,
    HighSchoolQualification, BachelorQualification, MasterQualification, OtherCertificate,
    LanguageProficiency
)


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


# Forms for the tabbed application system
# نماذج المؤهلات الأكاديمية الجديدة
class HighSchoolQualificationForm(forms.ModelForm):
    """نموذج الثانوية العامة"""

    class Meta:
        model = HighSchoolQualification
        exclude = ['application']
        widgets = {
            'certificate_type': forms.TextInput(attrs={'class': 'form-control'}),
            'branch': forms.TextInput(attrs={'class': 'form-control'}),
            'graduation_year': forms.NumberInput(attrs={'class': 'form-control', 'min': '1950', 'max': '2030'}),
            'gpa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'study_language': forms.Select(attrs={'class': 'form-control'}),
            'additional_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BachelorQualificationForm(forms.ModelForm):
    """نموذج البكالوريوس"""

    class Meta:
        model = BachelorQualification
        exclude = ['application']
        widgets = {
            'institution_name': forms.TextInput(attrs={'class': 'form-control'}),
            'major': forms.TextInput(attrs={'class': 'form-control'}),
            'graduation_year': forms.NumberInput(attrs={'class': 'form-control', 'min': '1950', 'max': '2030'}),
            'gpa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'grade': forms.Select(attrs={'class': 'form-select'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'study_system': forms.Select(attrs={'class': 'form-control'}),
            'bachelor_type': forms.Select(attrs={'class': 'form-control'}),
            'study_language': forms.Select(attrs={'class': 'form-control'}),
            'additional_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class MasterQualificationForm(forms.ModelForm):
    """نموذج الماجستير"""

    class Meta:
        model = MasterQualification
        exclude = ['application']
        widgets = {
            'institution_name': forms.TextInput(attrs={'class': 'form-control'}),
            'major': forms.TextInput(attrs={'class': 'form-control'}),
            'graduation_year': forms.NumberInput(attrs={'class': 'form-control', 'min': '1950', 'max': '2030'}),
            'gpa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'grade': forms.Select(attrs={'class': 'form-select'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'masters_system': forms.Select(attrs={'class': 'form-control'}),
            'study_language': forms.Select(attrs={'class': 'form-control'}),
            'additional_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class OtherCertificateForm(forms.ModelForm):
    """نموذج الشهادات الأخرى"""

    class Meta:
        model = OtherCertificate
        exclude = ['application']
        widgets = {
            'certificate_type': forms.Select(attrs={'class': 'form-control'}),
            'certificate_name': forms.TextInput(attrs={'class': 'form-control'}),
            'certificate_issuer': forms.TextInput(attrs={'class': 'form-control'}),
            'graduation_year': forms.NumberInput(attrs={'class': 'form-control', 'min': '1950', 'max': '2030'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'study_language': forms.Select(attrs={'class': 'form-control'}),
            'additional_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class LanguageProficiencyForm(forms.ModelForm):
    """نموذج الكفاءة اللغوية"""

    class Meta:
        model = LanguageProficiency
        exclude = ['application']
        widgets = {
            'is_english': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'test_type': forms.Select(attrs={'class': 'form-select english-field'}),
            'other_test_name': forms.TextInput(attrs={'class': 'form-control english-field other-test-field'}),
            'test_date': forms.DateInput(attrs={'class': 'form-control english-field', 'type': 'date'}),
            'overall_score': forms.NumberInput(attrs={'class': 'form-control english-field', 'step': '0.1'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control english-field'}),
            'reading_score': forms.NumberInput(attrs={'class': 'form-control english-field', 'step': '0.1'}),
            'listening_score': forms.NumberInput(attrs={'class': 'form-control english-field', 'step': '0.1'}),
            'speaking_score': forms.NumberInput(attrs={'class': 'form-control english-field', 'step': '0.1'}),
            'writing_score': forms.NumberInput(attrs={'class': 'form-control english-field', 'step': '0.1'}),
            'other_language': forms.Select(attrs={'class': 'form-select other-language-field'}),
            'other_language_name': forms.TextInput(
                attrs={'class': 'form-control other-language-field other-language-name-field'}),
            'proficiency_level': forms.Select(attrs={'class': 'form-select other-language-field'}),
            'additional_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # عند تحرير كفاءة لغوية موجودة، تعيين الحقول المطلوبة حسب نوع اللغة
        if self.instance.pk:
            if self.instance.is_english:
                self.fields['test_type'].required = True
                self.fields['test_date'].required = True
                self.fields['overall_score'].required = True

                # إذا كان نوع الاختبار "أخرى"، يكون حقل "اسم الاختبار الآخر" مطلوبًا
                if self.instance.test_type == 'other':
                    self.fields['other_test_name'].required = True
            else:
                self.fields['other_language'].required = True
                self.fields['proficiency_level'].required = True

                # إذا كانت اللغة "أخرى"، يكون حقل "اسم اللغة الأخرى" مطلوبًا
                if self.instance.other_language == 'other':
                    self.fields['other_language_name'].required = True


class DocumentUploadForm(forms.ModelForm):
    """نموذج رفع المستندات"""

    class Meta:
        model = Document
        fields = ['document_type', 'name', 'description', 'file', 'is_required',
                  'high_school_qualification', 'bachelor_qualification', 'master_qualification', 'other_certificate']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'is_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'high_school_qualification': forms.Select(attrs={'class': 'form-select'}),
            'bachelor_qualification': forms.Select(attrs={'class': 'form-select'}),
            'master_qualification': forms.Select(attrs={'class': 'form-select'}),
            'other_certificate': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # تحضير مجال اختياري للمؤهلات المختلفة
        if 'application' in kwargs.get('initial', {}):
            application = kwargs['initial']['application']

            # تقييد الاختيارات للمؤهلات التابعة لهذا الطلب فقط
            self.fields['high_school_qualification'].queryset = HighSchoolQualification.objects.filter(
                application=application)
            self.fields['bachelor_qualification'].queryset = BachelorQualification.objects.filter(
                application=application)
            self.fields['master_qualification'].queryset = MasterQualification.objects.filter(application=application)
            self.fields['other_certificate'].queryset = OtherCertificate.objects.filter(application=application)


class ApplicationTabsForm(forms.ModelForm):
    """نموذج الطلب الرئيسي بالتبويبات"""

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


# FormSets for tabbed application
HighSchoolQualificationFormSet = forms.inlineformset_factory(
    Application, HighSchoolQualification,
    form=HighSchoolQualificationForm,
    extra=1, can_delete=True
)

BachelorQualificationFormSet = forms.inlineformset_factory(
    Application, BachelorQualification,
    form=BachelorQualificationForm,
    extra=1, can_delete=True
)

MasterQualificationFormSet = forms.inlineformset_factory(
    Application, MasterQualification,
    form=MasterQualificationForm,
    extra=1, can_delete=True
)

OtherCertificateFormSet = forms.inlineformset_factory(
    Application, OtherCertificate,
    form=OtherCertificateForm,
    extra=1, can_delete=True
)

LanguageProficiencyFormSet = forms.inlineformset_factory(
    Application, LanguageProficiency,
    form=LanguageProficiencyForm,
    extra=1, can_delete=True
)

DocumentFormSet = forms.inlineformset_factory(
    Application, Document,
    form=DocumentUploadForm,
    extra=1, can_delete=True
)