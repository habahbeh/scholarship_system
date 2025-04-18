from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from applications.models import Application


class Committee(models.Model):
    """نموذج لجان التقييم"""
    name = models.CharField(_("اسم اللجنة"), max_length=100)
    description = models.TextField(_("الوصف"), blank=True, null=True)
    members = models.ManyToManyField(User, verbose_name=_("الأعضاء"), related_name="committees")
    is_active = models.BooleanField(_("نشطة"), default=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("لجنة تقييم")
        verbose_name_plural = _("لجان التقييم")
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.members.count()


class EvaluationCriterion(models.Model):
    """نموذج معايير التقييم"""
    name = models.CharField(_("المعيار"), max_length=100)
    description = models.TextField(_("الوصف"), blank=True, null=True)
    weight = models.PositiveIntegerField(_("الوزن"), default=1, help_text=_("أهمية المعيار (1-10)"))
    order = models.PositiveIntegerField(_("الترتيب"), default=0)
    is_active = models.BooleanField(_("نشط"), default=True)

    class Meta:
        verbose_name = _("معيار تقييم")
        verbose_name_plural = _("معايير التقييم")
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class EvaluationRound(models.Model):
    """نموذج جولات التقييم"""
    ROUND_TYPES = (
        ('initial', _('المراجعة الأولية')),
        ('committee', _('تقييم اللجنة')),
        ('final', _('التقييم النهائي')),
    )

    name = models.CharField(_("اسم الجولة"), max_length=100)
    description = models.TextField(_("الوصف"), blank=True, null=True)
    round_type = models.CharField(_("نوع الجولة"), max_length=20, choices=ROUND_TYPES)
    committee = models.ForeignKey(Committee, verbose_name=_("اللجنة"), on_delete=models.CASCADE,
                                  related_name="evaluation_rounds")
    start_date = models.DateTimeField(_("تاريخ البدء"), default=timezone.now)
    end_date = models.DateTimeField(_("تاريخ الانتهاء"),)

    is_active = models.BooleanField(_("نشطة"), default=True)
    criteria = models.ManyToManyField(EvaluationCriterion, verbose_name=_("المعايير"), related_name="evaluation_rounds")
    min_evaluators = models.PositiveIntegerField(_("الحد الأدنى للمقيمين"), default=1)

    class Meta:
        verbose_name = _("جولة تقييم")
        verbose_name_plural = _("جولات التقييم")
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.name} ({self.get_round_type_display()})"

    # @property
    # def is_in_progress(self):
    #     now = timezone.now()
    #     return self.start_date <= now <= self.end_date
    #
    # @property
    # def is_completed(self):
    #     return timezone.now() > self.end_date

    @property
    def is_in_progress(self):
        now = timezone.now()
        # Check if dates exist before comparing
        if self.start_date is None or self.end_date is None:
            return False
        return self.start_date <= now <= self.end_date

    @property
    def is_completed(self):
        # Check if end_date exists before comparing
        if self.end_date is None:
            return False
        return timezone.now() > self.end_date


class ApplicationEvaluation(models.Model):
    """نموذج تقييم طلب ابتعاث"""
    application = models.ForeignKey(Application, verbose_name=_("الطلب"), on_delete=models.CASCADE,
                                    related_name="evaluations")
    evaluation_round = models.ForeignKey(EvaluationRound, verbose_name=_("جولة التقييم"), on_delete=models.CASCADE,
                                         related_name="application_evaluations")
    evaluator = models.ForeignKey(User, verbose_name=_("المقيم"), on_delete=models.CASCADE, related_name="evaluations")
    overall_score = models.DecimalField(_("الدرجة الإجمالية"), max_digits=5, decimal_places=2, null=True, blank=True)
    comments = models.TextField(_("ملاحظات"), blank=True, null=True)
    evaluation_date = models.DateTimeField(_("تاريخ التقييم"), auto_now_add=True)
    is_submitted = models.BooleanField(_("تم التقديم"), default=False)

    class Meta:
        verbose_name = _("تقييم طلب")
        verbose_name_plural = _("تقييمات الطلبات")
        ordering = ['-evaluation_date']
        unique_together = ['application', 'evaluation_round', 'evaluator']

    def __str__(self):
        return f"{self.application} - {self.evaluator.get_full_name()} - {self.evaluation_round.name}"

    def save(self, *args, **kwargs):
        # حساب الدرجة الإجمالية عند الحفظ
        if self.is_submitted and self.criteria_scores.exists():
            total_weight = sum(score.criterion.weight for score in self.criteria_scores.all())
            weighted_sum = sum(score.score * score.criterion.weight for score in self.criteria_scores.all())
            if total_weight > 0:
                self.overall_score = weighted_sum / total_weight
        super().save(*args, **kwargs)


class CriterionScore(models.Model):
    """نموذج درجات معايير التقييم"""
    evaluation = models.ForeignKey(ApplicationEvaluation, verbose_name=_("التقييم"), on_delete=models.CASCADE,
                                   related_name="criteria_scores")
    criterion = models.ForeignKey(EvaluationCriterion, verbose_name=_("المعيار"), on_delete=models.CASCADE,
                                  related_name="criterion_scores")
    score = models.PositiveIntegerField(_("الدرجة"), validators=[MinValueValidator(0), MaxValueValidator(10)])
    comments = models.TextField(_("ملاحظات"), blank=True, null=True)

    class Meta:
        verbose_name = _("درجة معيار")
        verbose_name_plural = _("درجات المعايير")
        unique_together = ['evaluation', 'criterion']

    def __str__(self):
        return f"{self.criterion.name}: {self.score}/10"


class Vote(models.Model):
    """نموذج التصويت على الطلبات"""
    VOTE_CHOICES = (
        ('approve', _('موافق')),
        ('reject', _('غير موافق')),
        ('abstain', _('ممتنع')),
    )

    application = models.ForeignKey(Application, verbose_name=_("الطلب"), on_delete=models.CASCADE,
                                    related_name="votes")
    committee_member = models.ForeignKey(User, verbose_name=_("عضو اللجنة"), on_delete=models.CASCADE,
                                         related_name="votes")
    vote = models.CharField(_("التصويت"), max_length=10, choices=VOTE_CHOICES)
    comments = models.TextField(_("ملاحظات"), blank=True, null=True)
    vote_date = models.DateTimeField(_("تاريخ التصويت"), auto_now_add=True)

    class Meta:
        verbose_name = _("تصويت")
        verbose_name_plural = _("التصويتات")
        ordering = ['-vote_date']
        unique_together = ['application', 'committee_member']

    def __str__(self):
        return f"{self.application} - {self.committee_member.get_full_name()} - {self.get_vote_display()}"


class Recommendation(models.Model):
    """نموذج التوصيات"""
    RECOMMENDATION_CHOICES = (
        ('approve', _('الموافقة على الطلب')),
        ('approve_with_conditions', _('الموافقة بشروط')),
        ('reject', _('رفض الطلب')),
        ('postpone', _('تأجيل القرار')),
        ('request_more_info', _('طلب معلومات إضافية')),
    )

    application = models.ForeignKey(Application, verbose_name=_("الطلب"), on_delete=models.CASCADE,
                                    related_name="recommendations")
    committee = models.ForeignKey(Committee, verbose_name=_("اللجنة"), on_delete=models.CASCADE,
                                  related_name="recommendations")
    recommendation = models.CharField(_("التوصية"), max_length=30, choices=RECOMMENDATION_CHOICES)
    comments = models.TextField(_("ملاحظات"), blank=True, null=True)
    conditions = models.TextField(_("الشروط"), blank=True, null=True, help_text=_("في حالة الموافقة بشروط"))
    created_by = models.ForeignKey(User, verbose_name=_("تم إنشاؤها بواسطة"), on_delete=models.CASCADE,
                                   related_name="created_recommendations")
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("توصية")
        verbose_name_plural = _("التوصيات")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.application} - {self.committee.name} - {self.get_recommendation_display()}"