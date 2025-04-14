from django.db import models
from django.utils.translation import gettext_lazy as _


class DashboardWidget(models.Model):
    """نموذج ودجات لوحة التحكم"""
    WIDGET_TYPES = (
        ('applications_stats', _('إحصائيات الطلبات')),
        ('scholarship_stats', _('إحصائيات فرص الابتعاث')),
        ('evaluations_stats', _('إحصائيات التقييمات')),
        ('recent_applications', _('آخر الطلبات')),
        ('recent_scholarships', _('آخر فرص الابتعاث')),
        ('recent_evaluations', _('آخر التقييمات')),
        ('status_chart', _('مخطط حالات الطلبات')),
        ('committee_chart', _('مخطط تقييمات اللجان')),
    )

    name = models.CharField(_("اسم الودجة"), max_length=100)
    widget_type = models.CharField(_("نوع الودجة"), max_length=30, choices=WIDGET_TYPES)
    description = models.TextField(_("الوصف"), blank=True, null=True)
    is_active = models.BooleanField(_("نشطة"), default=True)
    order = models.PositiveIntegerField(_("الترتيب"), default=0)
    show_to_roles = models.CharField(_("ظهور للأدوار"), max_length=200,
                                     help_text=_("أدوار المستخدمين الذين سيشاهدون هذه الودجة، مفصولة بفواصل"))

    class Meta:
        verbose_name = _("ودجة لوحة التحكم")
        verbose_name_plural = _("ودجات لوحة التحكم")
        ordering = ['order']

    def __str__(self):
        return self.name