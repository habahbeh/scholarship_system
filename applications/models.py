# في ملف applications/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _


class ApplicationStatus(models.Model):
    """نموذج حالات طلب الابتعاث"""
    name = models.CharField(_("اسم الحالة"), max_length=100)
    description = models.TextField(_("الوصف"), blank=True, null=True)
    order = models.PositiveSmallIntegerField(_("الترتيب"), default=0)

    # إضافة علامة لتحديد ما إذا كانت الحالة تتطلب مرفقات
    requires_attachment = models.BooleanField(_("تتطلب مرفقات"), default=False)

    class Meta:
        verbose_name = _("حالة الطلب")
        verbose_name_plural = _("حالات الطلبات")
        ordering = ['order']

    def __str__(self):
        return self.name


# الحالات المطلوبة للنظام الجديد:
# 1. تم التقديم (order=1)
# 2. قيد المراجعة (order=2)
# 3. مطابق للشروط (order=3)
# 4. غير مطابق للشروط (order=4)
# 5. موافق من اللجنة العليا (order=5، requires_attachment=True)
# 6. غير موافق من اللجنة العليا (order=6)
# 7. موافق من مجلس الكلية (order=7، requires_attachment=True)
# 8. غير موافق من مجلس الكلية (order=8)
# 9. موافق من رئيس الجامعة (order=9، requires_attachment=True)
# 10. غير موافق من رئيس الجامعة (order=10)

# في ملف applications/models.py - إضافة نموذج لمرفقات الموافقات

class ApprovalAttachment(models.Model):
    """نموذج مرفقات الموافقات"""
    application = models.ForeignKey('Application', on_delete=models.CASCADE,
                                    related_name='approval_attachments',
                                    verbose_name=_("الطلب"))
    approval_type = models.CharField(_("نوع الموافقة"), max_length=50, choices=[
        ('higher_committee', _('اللجنة العليا')),
        ('faculty_council', _('مجلس الكلية')),
        ('president', _('رئيس الجامعة')),
    ])
    attachment = models.FileField(_("المرفق"), upload_to='approvals/%Y/%m/')
    upload_date = models.DateTimeField(_("تاريخ الرفع"), auto_now_add=True)
    notes = models.TextField(_("ملاحظات"), blank=True, null=True)

    class Meta:
        verbose_name = _("مرفق موافقة")
        verbose_name_plural = _("مرفقات الموافقات")
        ordering = ['-upload_date']

    def __str__(self):
        return f"{self.get_approval_type_display()} - {self.application}"


# from django.db import models
# from django.contrib.auth.models import User
# from django.utils.translation import gettext_lazy as _
# from django.urls import reverse
# from django.utils import timezone
# from announcements.models import Scholarship
#
#
# class ApplicationStatus(models.Model):
#     """نموذج حالات الطلب"""
#     name = models.CharField(_("الاسم"), max_length=100)
#     description = models.TextField(_("الوصف"), blank=True, null=True)
#     order = models.PositiveIntegerField(_("الترتيب"), default=0)
#
#     class Meta:
#         verbose_name = _("حالة الطلب")
#         verbose_name_plural = _("حالات الطلب")
#         ordering = ['order']
#
#     def __str__(self):
#         return self.name
#
#
# class Application(models.Model):
#     """نموذج طلبات الابتعاث"""
#     scholarship = models.ForeignKey(Scholarship, verbose_name=_("فرصة الابتعاث"), on_delete=models.CASCADE,
#                                     related_name="applications")
#     applicant = models.ForeignKey(User, verbose_name=_("المتقدم"), on_delete=models.CASCADE,
#                                   related_name="applications")
#     status = models.ForeignKey(ApplicationStatus, verbose_name=_("حالة الطلب"), on_delete=models.PROTECT,
#                                related_name="applications")
#     application_date = models.DateTimeField(_("تاريخ التقديم"), auto_now_add=True)
#     last_update = models.DateTimeField(_("آخر تحديث"), auto_now=True)
#     motivation_letter = models.TextField(_("خطاب الدوافع"),
#                                          help_text=_("اشرح لماذا تريد التقدم لهذه الفرصة وما هي أهدافك"))
#     research_proposal = models.TextField(_("مقترح البحث"), blank=True, null=True,
#                                          help_text=_("إذا كان الابتعاث لدراسة الدكتوراه، أرفق مقترح البحث الخاص بك"))
#     comments = models.TextField(_("ملاحظات إضافية"), blank=True, null=True,
#                                 help_text=_("أي معلومات إضافية تود إضافتها لطلبك"))
#     acceptance_letter = models.BooleanField(_("هل لديك قبول مبدئي؟"), default=False)
#     acceptance_university = models.CharField(_("اسم الجامعة التي لديك قبول فيها"), max_length=200, blank=True,
#                                              null=True)
#
#     class Meta:
#         verbose_name = _("طلب ابتعاث")
#         verbose_name_plural = _("طلبات الابتعاث")
#         ordering = ['-application_date']
#         unique_together = ['scholarship', 'applicant']  # لا يمكن للمستخدم التقديم على نفس الفرصة مرتين
#
#     def __str__(self):
#         return f"{self.applicant.get_full_name()} - {self.scholarship.title}"
#
#     def get_absolute_url(self):
#         return reverse('applications:application_detail', args=[self.id])
#
#
# class Document(models.Model):
#     """نموذج المستندات المرفقة بالطلب"""
#     application = models.ForeignKey(Application, verbose_name=_("الطلب"), on_delete=models.CASCADE,
#                                     related_name="documents")
#     name = models.CharField(_("اسم المستند"), max_length=100)
#     description = models.TextField(_("وصف المستند"), blank=True, null=True)
#     file = models.FileField(_("الملف"), upload_to='application_documents/')
#     upload_date = models.DateTimeField(_("تاريخ الرفع"), auto_now_add=True)
#     is_required = models.BooleanField(_("مطلوب"), default=True)
#
#     class Meta:
#         verbose_name = _("مستند")
#         verbose_name_plural = _("المستندات")
#         ordering = ['name']
#
#     def __str__(self):
#         return f"{self.name} - {self.application}"
#
#
# class ApplicationLog(models.Model):
#     """نموذج سجل التغييرات على الطلب"""
#     application = models.ForeignKey(Application, verbose_name=_("الطلب"), on_delete=models.CASCADE, related_name="logs")
#     from_status = models.ForeignKey(ApplicationStatus, verbose_name=_("من حالة"), on_delete=models.PROTECT,
#                                     related_name="from_logs", null=True, blank=True)
#     to_status = models.ForeignKey(ApplicationStatus, verbose_name=_("إلى حالة"), on_delete=models.PROTECT,
#                                   related_name="to_logs")
#     created_by = models.ForeignKey(User, verbose_name=_("تم بواسطة"), on_delete=models.CASCADE,
#                                    related_name="application_logs")
#     created_at = models.DateTimeField(_("تاريخ التغيير"), auto_now_add=True)
#     comment = models.TextField(_("التعليق"), blank=True, null=True)
#
#     class Meta:
#         verbose_name = _("سجل الطلب")
#         verbose_name_plural = _("سجلات الطلبات")
#         ordering = ['-created_at']
#
#     def __str__(self):
#         return f"{self.application} - {self.from_status} to {self.to_status}"