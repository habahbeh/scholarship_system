from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone


class ScholarshipType(models.Model):
    """نموذج أنواع المنح الدراسية والابتعاث"""
    name = models.CharField(_("اسم النوع"), max_length=100)
    description = models.TextField(_("الوصف"), blank=True, null=True)

    class Meta:
        verbose_name = _("نوع الابتعاث")
        verbose_name_plural = _("أنواع الابتعاث")
        ordering = ['name']

    def __str__(self):
        return self.name


class Scholarship(models.Model):
    """نموذج فرص الابتعاث"""
    STATUS_CHOICES = (
        ('draft', _('مسودة')),
        ('published', _('منشور')),
        ('closed', _('مغلق')),
    )

    title = models.CharField(_("العنوان"), max_length=200)
    scholarship_type = models.ForeignKey(ScholarshipType, verbose_name=_("نوع الابتعاث"), on_delete=models.CASCADE,
                                         related_name="scholarships")
    description = models.TextField(_("الوصف"))
    requirements = models.TextField(_("المتطلبات"))
    benefits = models.TextField(_("المميزات"), blank=True, null=True)
    countries = models.CharField(_("الدول المتاحة"), max_length=255, blank=True, null=True)
    universities = models.TextField(_("الجامعات المتاحة"), blank=True, null=True)
    deadline = models.DateTimeField(_("الموعد النهائي للتقديم"))
    publication_date = models.DateTimeField(_("تاريخ النشر"), default=timezone.now)
    status = models.CharField(_("الحالة"), max_length=20, choices=STATUS_CHOICES, default='draft')
    max_applicants = models.PositiveIntegerField(_("الحد الأقصى للمتقدمين"), default=0, help_text=_("0 يعني غير محدود"))
    eligibility_criteria = models.TextField(_("معايير الأهلية"), blank=True, null=True)
    application_process = models.TextField(_("عملية التقديم"), blank=True, null=True)
    contact_info = models.TextField(_("معلومات الاتصال"), blank=True, null=True)
    attachment = models.FileField(_("مرفق"), upload_to='scholarship_attachments/', blank=True, null=True)
    created_by = models.ForeignKey(User, verbose_name=_("تم إنشاؤه بواسطة"), on_delete=models.CASCADE,
                                   related_name="created_scholarships")
    updated_at = models.DateTimeField(_("تم التحديث في"), auto_now=True)

    class Meta:
        verbose_name = _("فرصة ابتعاث")
        verbose_name_plural = _("فرص الابتعاث")
        ordering = ['-publication_date']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('announcements:scholarship_detail', args=[self.id])

    @property
    def is_active(self):
        return self.status == 'published' and self.deadline > timezone.now()


class Announcement(models.Model):
    """نموذج الإعلانات العامة"""
    title = models.CharField(_("العنوان"), max_length=200)
    content = models.TextField(_("المحتوى"))
    publication_date = models.DateTimeField(_("تاريخ النشر"), default=timezone.now)
    is_active = models.BooleanField(_("نشط"), default=True)
    created_by = models.ForeignKey(User, verbose_name=_("تم إنشاؤه بواسطة"), on_delete=models.CASCADE,
                                   related_name="created_announcements")
    created_at = models.DateTimeField(_("تم الإنشاء في"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تم التحديث في"), auto_now=True)

    class Meta:
        verbose_name = _("إعلان")
        verbose_name_plural = _("الإعلانات")
        ordering = ['-publication_date']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('announcements:announcement_detail', args=[self.id])