from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from applications.models import Application
from .models import (
    Committee, EvaluationCriterion, EvaluationRound,
    ApplicationEvaluation, CriterionScore, Vote, Recommendation
)


class CommitteeForm(forms.ModelForm):
    """نموذج إنشاء/تعديل لجنة تقييم"""

    class Meta:
        model = Committee
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CommitteeMemberForm(forms.Form):
    """نموذج إضافة عضو للجنة"""
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label=_("المستخدم"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class CriterionForm(forms.ModelForm):
    """نموذج إنشاء/تعديل معيار تقييم"""

    class Meta:
        model = EvaluationCriterion
        fields = ['name', 'description', 'weight', 'order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EvaluationRoundForm(forms.ModelForm):
    """نموذج إنشاء/تعديل جولة تقييم"""
    criteria = forms.ModelMultipleChoiceField(
        queryset=EvaluationCriterion.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label=_("معايير التقييم"),
        required=True
    )

    class Meta:
        model = EvaluationRound
        fields = ['name', 'description', 'round_type', 'committee',
                  'start_date', 'end_date', 'is_active', 'criteria', 'min_evaluators']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'round_type': forms.Select(attrs={'class': 'form-select'}),
            'committee': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'min_evaluators': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }


class RoundAssignApplicationsForm(forms.Form):
    """نموذج تعيين طلبات للتقييم في جولة معينة"""
    applications = forms.ModelMultipleChoiceField(
        queryset=Application.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label=_("الطلبات"),
        required=True
    )

    def __init__(self, *args, round_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if round_id:
            # تفلتر الطلبات التي لم يتم تقييمها بعد في هذه الجولة
            evaluation_round = EvaluationRound.objects.get(id=round_id)
            existing_applications = ApplicationEvaluation.objects.filter(
                evaluation_round=evaluation_round
            ).values_list('application_id', flat=True)

            self.fields['applications'].queryset = Application.objects.exclude(
                id__in=existing_applications
            )


class CriterionScoreForm(forms.ModelForm):
    """نموذج تقييم معيار"""

    class Meta:
        model = CriterionScore
        fields = ['score', 'comments']
        widgets = {
            'score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 10}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ApplicationEvaluationForm(forms.ModelForm):
    """نموذج تقييم طلب"""

    class Meta:
        model = ApplicationEvaluation
        fields = ['comments', 'is_submitted']
        widgets = {
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_submitted': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class VoteForm(forms.ModelForm):
    """نموذج التصويت على طلب"""

    class Meta:
        model = Vote
        fields = ['vote', 'comments']
        widgets = {
            'vote': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class RecommendationForm(forms.ModelForm):
    """نموذج تقديم توصية"""

    class Meta:
        model = Recommendation
        fields = ['recommendation', 'comments', 'conditions']
        widgets = {
            'recommendation': forms.Select(attrs={'class': 'form-select'}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }