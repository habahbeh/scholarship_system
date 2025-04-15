from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Scholarship, Announcement, ScholarshipType


class ScholarshipForm(forms.ModelForm):
    """نموذج إنشاء/تعديل فرصة ابتعاث"""

    class Meta:
        model = Scholarship
        fields = ['title', 'scholarship_type', 'description', 'requirements', 'benefits',
                  'countries', 'universities', 'deadline', 'status', 'max_applicants',
                  'eligibility_criteria', 'application_process', 'contact_info', 'attachment']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'scholarship_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'benefits': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'countries': forms.TextInput(attrs={'class': 'form-control'}),
            'universities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'deadline': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'max_applicants': forms.NumberInput(attrs={'class': 'form-control'}),
            'eligibility_criteria': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'application_process': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contact_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }


class AnnouncementForm(forms.ModelForm):
    """نموذج إنشاء/تعديل إعلان"""

    class Meta:
        model = Announcement
        fields = ['title', 'content', 'publication_date', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'publication_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }



class ScholarshipTypeForm(forms.ModelForm):
    """نموذج نوع الابتعاث"""
    class Meta:
        model = ScholarshipType
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ScholarshipFilterForm(forms.Form):
    """نموذج تصفية فرص الابتعاث"""
    SORT_CHOICES = (
        ('newest', _('الأحدث')),
        ('deadline', _('الموعد النهائي')),
        ('title', _('العنوان')),
    )

    scholarship_type = forms.ModelChoiceField(
        queryset=ScholarshipType.objects.all(),
        required=False,
        empty_label=_("كل الأنواع"),
        label=_("نوع الابتعاث"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    status = forms.ChoiceField(
        choices=(
            ('', _('كل الحالات')),
            ('active', _('نشط')),
            ('closed', _('مغلق')),
        ),
        required=False,
        label=_("الحالة"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    country = forms.CharField(
        required=False,
        label=_("الدولة"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('أدخل اسم الدولة')})
    )

    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='newest',
        label=_("ترتيب حسب"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    search = forms.CharField(
        required=False,
        label=_("بحث"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('بحث...')})
    )


