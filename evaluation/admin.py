from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    Committee, EvaluationCriterion, EvaluationRound, ApplicationEvaluation,
    CriterionScore, Vote, Recommendation
)


@admin.register(Committee)
class CommitteeAdmin(admin.ModelAdmin):
    list_display = ('name', 'member_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    filter_horizontal = ('members',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(EvaluationCriterion)
class EvaluationCriterionAdmin(admin.ModelAdmin):
    list_display = ('name', 'weight', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    ordering = ('order',)


class CriterionInline(admin.TabularInline):
    model = EvaluationRound.criteria.through
    extra = 1


@admin.register(EvaluationRound)
class EvaluationRoundAdmin(admin.ModelAdmin):
    list_display = ('name', 'round_type', 'committee', 'start_date', 'end_date', 'is_active', 'is_in_progress', 'is_completed')
    list_filter = ('round_type', 'is_active', 'committee', 'start_date')
    search_fields = ('name', 'description')
    date_hierarchy = 'start_date'
    filter_horizontal = ('criteria',)
    readonly_fields = ('is_in_progress', 'is_completed')
    inlines = [CriterionInline]
    exclude = ('criteria',)

    def is_in_progress(self, obj):
        return obj.is_in_progress
    is_in_progress.boolean = True
    is_in_progress.short_description = _('جارية')

    def is_completed(self, obj):
        return obj.is_completed
    is_completed.boolean = True
    is_completed.short_description = _('مكتملة')


class CriterionScoreInline(admin.TabularInline):
    model = CriterionScore
    extra = 1


@admin.register(ApplicationEvaluation)
class ApplicationEvaluationAdmin(admin.ModelAdmin):
    list_display = ('application', 'evaluation_round', 'evaluator', 'overall_score', 'is_submitted', 'evaluation_date')
    list_filter = ('is_submitted', 'evaluation_date', 'evaluation_round')
    search_fields = ('application__applicant__username', 'evaluator__username')
    date_hierarchy = 'evaluation_date'
    readonly_fields = ('evaluation_date', 'overall_score')
    inlines = [CriterionScoreInline]
    autocomplete_fields = ['application', 'evaluation_round', 'evaluator']


@admin.register(CriterionScore)
class CriterionScoreAdmin(admin.ModelAdmin):
    list_display = ('evaluation', 'criterion', 'score')
    list_filter = ('criterion', 'score')
    search_fields = ('evaluation__application__applicant__username', 'criterion__name')
    autocomplete_fields = ['evaluation', 'criterion']


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('application', 'committee_member', 'vote', 'vote_date')
    list_filter = ('vote', 'vote_date')
    search_fields = ('application__applicant__username', 'committee_member__username', 'comments')
    date_hierarchy = 'vote_date'
    autocomplete_fields = ['application', 'committee_member']


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('application', 'committee', 'recommendation', 'created_by', 'created_at')
    list_filter = ('recommendation', 'committee', 'created_at')
    search_fields = ('application__applicant__username', 'comments', 'conditions')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_by', 'created_at', 'updated_at')
    autocomplete_fields = ['application', 'committee']

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)