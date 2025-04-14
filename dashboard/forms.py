from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from announcements.models import ScholarshipType
from applications.models import ApplicationStatus


class DateRangeForm(forms.Form):
    """نموذج اختيار نطاق زمني للإحصائيات"""
    start_date = forms.DateField(
        label=_("تاريخ البداية"),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )

    end_date = forms.DateField(
        label=_("تاريخ النهاية"),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )


class ApplicationStatsFilterForm(forms.Form):
    """نموذج تصفية إحصائيات الطلبات"""
    scholarship_type = forms.ModelChoiceField(
        queryset=ScholarshipType.objects.all(),
        label=_("نوع الابتعاث"),
        required=False,
        empty_label=_("الكل"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    status = forms.ModelChoiceField(
        queryset=ApplicationStatus.objects.all(),
        label=_("حالة الطلب"),
        required=False,
        empty_label=_("الكل"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    date_range = forms.ChoiceField(
        label=_("النطاق الزمني"),
        choices=(
            ('all', _("كل الفترات")),
            ('month', _("الشهر الحالي")),
            ('quarter', _("الربع الحالي")),
            ('year', _("السنة الحالية")),
            ('custom', _("مخصص")),
        ),
        initial='month',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    start_date = forms.DateField(
        label=_("تاريخ البداية"),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )

    end_date = forms.DateField(
        label=_("تاريخ النهاية"),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )

    group_by = forms.ChoiceField(
        label=_("تجميع حسب"),
        choices=(
            ('status', _("الحالة")),
            ('scholarship_type', _("نوع الابتعاث")),
            ('month', _("الشهر")),
            ('faculty', _("الكلية")),
        ),
        initial='status',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    chart_type = forms.ChoiceField(
        label=_("نوع الرسم البياني"),
        choices=(
            ('bar', _("أعمدة")),
            ('pie', _("دائري")),
            ('line', _("خطي")),
        ),
        initial='bar',
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class EvaluationStatsFilterForm(forms.Form):
    """نموذج تصفية إحصائيات التقييمات"""
    committee = forms.ChoiceField(
        label=_("اللجنة"),
        choices=(),  # سيتم تعبئتها في __init__
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    round_type = forms.ChoiceField(
        label=_("نوع الجولة"),
        choices=(
            ('', _("الكل")),
            ('initial', _("المراجعة الأولية")),
            ('committee', _("تقييم اللجنة")),
            ('final', _("التقييم النهائي")),
        ),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    evaluator = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label=_("المقيّم"),
        required=False,
        empty_label=_("الكل"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    date_range = forms.ChoiceField(
        label=_("النطاق الزمني"),
        choices=(
            ('all', _("كل الفترات")),
            ('month', _("الشهر الحالي")),
            ('quarter', _("الربع الحالي")),
            ('year', _("السنة الحالية")),
            ('custom', _("مخصص")),
        ),
        initial='month',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    start_date = forms.DateField(
        label=_("تاريخ البداية"),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )

    end_date = forms.DateField(
        label=_("تاريخ النهاية"),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )

    def __init__(self, *args, **kwargs):
        from evaluation.models import Committee
        super().__init__(*args, **kwargs)

        # تعبئة خيارات اللجان
        committee_choices = [('', _("الكل"))]
        committee_choices.extend([
            (committee.id, committee.name)
            for committee in Committee.objects.filter(is_active=True)
        ])
        self.fields['committee'].choices = committee_choices