# في ملف applications/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone
from announcements.models import Scholarship
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator


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


class Application(models.Model):
    """نموذج طلبات الابتعاث"""
    scholarship = models.ForeignKey(Scholarship, verbose_name=_("فرصة الابتعاث"), on_delete=models.CASCADE,
                                    related_name="applications")
    applicant = models.ForeignKey(User, verbose_name=_("المتقدم"), on_delete=models.CASCADE,
                                  related_name="applications")
    status = models.ForeignKey(ApplicationStatus, verbose_name=_("حالة الطلب"), on_delete=models.PROTECT,
                               related_name="applications")
    application_date = models.DateTimeField(_("تاريخ التقديم"), auto_now_add=True)
    last_update = models.DateTimeField(_("آخر تحديث"), auto_now=True)
    motivation_letter = models.TextField(_("خطاب الدوافع"),
                                         help_text=_("اشرح لماذا تريد التقدم لهذه الفرصة وما هي أهدافك"))
    research_proposal = models.TextField(_("مقترح البحث"), blank=True, null=True,
                                         help_text=_("إذا كان الابتعاث لدراسة الدكتوراه، أرفق مقترح البحث الخاص بك"))
    comments = models.TextField(_("ملاحظات إضافية"), blank=True, null=True,
                                help_text=_("أي معلومات إضافية تود إضافتها لطلبك"))
    acceptance_letter = models.BooleanField(_("هل لديك قبول مبدئي؟"), default=False)
    acceptance_university = models.CharField(_("اسم الجامعة التي لديك قبول فيها"), max_length=200, blank=True,
                                             null=True)

    # حقل جديد للملاحظات الإدارية عند مطابقة الشروط
    admin_notes = models.TextField(_("ملاحظات إدارية"), blank=True, null=True)

    class Meta:
        verbose_name = _("طلب ابتعاث")
        verbose_name_plural = _("طلبات الابتعاث")
        ordering = ['-application_date']
        unique_together = ['scholarship', 'applicant']  # لا يمكن للمستخدم التقديم على نفس الفرصة مرتين

    def __str__(self):
        return f"{self.applicant.get_full_name()} - {self.scholarship.title}"

    def get_absolute_url(self):
        return reverse('applications:application_detail', args=[self.id])


class AcademicQualification(models.Model):
    """نموذج المؤهلات الأكاديمية"""
    application = models.ForeignKey(Application, verbose_name=_("الطلب"), on_delete=models.CASCADE,
                                    related_name="academic_qualifications")
    QUALIFICATION_TYPE_CHOICES = [
        ('high_school', _('الثانوية العامة')),
        ('bachelors', _('البكالوريوس')),
        ('masters', _('الماجستير')),
        ('other', _('شهادة أخرى')),
    ]
    qualification_type = models.CharField(_("نوع المؤهل"), max_length=20, choices=QUALIFICATION_TYPE_CHOICES)

    # حقول الثانوية العامة
    high_school_certificate_type = models.CharField(_("نوع الشهادة"), max_length=50, blank=True, null=True,
                                                    help_text=_("مثل: أردنية، سعودية، بكالوريا دولية، إلخ"))
    high_school_branch = models.CharField(_("الفرع/التخصص"), max_length=50, blank=True, null=True,
                                          help_text=_("مثل: علمي، أدبي، تجاري، إلخ"))
    high_school_graduation_year = models.IntegerField(_("سنة التخرج - الثانوية"),
                                                      validators=[MinValueValidator(1950), MaxValueValidator(2030)],
                                                      blank=True, null=True)
    high_school_gpa = models.DecimalField(_("المعدل - الثانوية"), max_digits=5, decimal_places=2, blank=True, null=True,
                                          help_text=_("بالنسبة المئوية"))
    high_school_country = models.CharField(_("بلد الدراسة - الثانوية"), max_length=100, blank=True, null=True)

    # حقول البكالوريوس
    bachelor_institution_name = models.CharField(_("اسم المؤسسة/الجامعة - البكالوريوس"), max_length=200, blank=True,
                                                 null=True)
    bachelor_major = models.CharField(_("التخصص - البكالوريوس"), max_length=200, blank=True, null=True)
    bachelor_graduation_year = models.IntegerField(_("سنة التخرج - البكالوريوس"),
                                                   validators=[MinValueValidator(1950), MaxValueValidator(2030)],
                                                   blank=True, null=True)
    bachelor_gpa = models.DecimalField(_("المعدل - البكالوريوس"), max_digits=5, decimal_places=2, blank=True, null=True,
                                       help_text=_("بالنسبة المئوية"))
    GRADE_CHOICES = [
        ('excellent', _('ممتاز')),
        ('very_good', _('جيد جداً')),
        ('good', _('جيد')),
        ('acceptable', _('مقبول')),
    ]
    bachelor_grade = models.CharField(_("التقدير - البكالوريوس"), max_length=20, choices=GRADE_CHOICES, blank=True,
                                      null=True)
    bachelor_country = models.CharField(_("بلد الدراسة - البكالوريوس"), max_length=100, blank=True, null=True)

    # حقول الماجستير
    masters_institution_name = models.CharField(_("اسم المؤسسة/الجامعة - الماجستير"), max_length=200, blank=True,
                                                null=True)
    masters_major = models.CharField(_("التخصص - الماجستير"), max_length=200, blank=True, null=True)
    masters_graduation_year = models.IntegerField(_("سنة التخرج - الماجستير"),
                                                  validators=[MinValueValidator(1950), MaxValueValidator(2030)],
                                                  blank=True, null=True)
    masters_gpa = models.DecimalField(_("المعدل - الماجستير"), max_digits=5, decimal_places=2, blank=True, null=True,
                                      help_text=_("بالنسبة المئوية"))
    masters_grade = models.CharField(_("التقدير - الماجستير"), max_length=20, choices=GRADE_CHOICES, blank=True,
                                     null=True)
    masters_country = models.CharField(_("بلد الدراسة - الماجستير"), max_length=100, blank=True, null=True)

    # حقول الشهادة الأخرى
    certificate_graduation_year = models.IntegerField(_("سنة التخرج - الشهادة"),
                                                      validators=[MinValueValidator(1950), MaxValueValidator(2030)],
                                                      blank=True, null=True)

    # حقول مشتركة (للتوافق الخلفي، سيتم إزالتها لاحقاً)
    institution_name = models.CharField(_("اسم المؤسسة/الجامعة"), max_length=200, blank=True, null=True)
    major = models.CharField(_("التخصص"), max_length=200, blank=True, null=True)
    graduation_year = models.IntegerField(_("سنة التخرج"),
                                          validators=[MinValueValidator(1950), MaxValueValidator(2030)],
                                          blank=True, null=True)
    gpa = models.DecimalField(_("المعدل"), max_digits=5, decimal_places=2, blank=True, null=True,
                              help_text=_("بالنسبة المئوية"))
    grade = models.CharField(_("التقدير"), max_length=20, choices=GRADE_CHOICES, blank=True, null=True)
    country = models.CharField(_("بلد الدراسة"), max_length=100, blank=True, null=True)

    # حقول خاصة بالبكالوريوس
    STUDY_SYSTEM_CHOICES = [
        ('regular', _('انتظام')),
        ('distance', _('انتساب')),
    ]
    study_system = models.CharField(_("نظام الدراسة"), max_length=20, choices=STUDY_SYSTEM_CHOICES,
                                    blank=True, null=True)

    BACHELOR_TYPE_CHOICES = [
        ('regular', _('عادية')),
        ('bridge', _('تجسير')),
    ]
    bachelor_type = models.CharField(_("نوع الشهادة"), max_length=20, choices=BACHELOR_TYPE_CHOICES,
                                     blank=True, null=True)

    # حقول خاصة بالماجستير
    MASTERS_SYSTEM_CHOICES = [
        ('thesis', _('مسار الرسالة')),
        ('comprehensive', _('مسار الشامل')),
    ]
    masters_system = models.CharField(_("نظام الدراسة"), max_length=20, choices=MASTERS_SYSTEM_CHOICES,
                                      blank=True, null=True)

    LANGUAGE_CHOICES = [
        ('arabic', _('عربي')),
        ('english', _('إنجليزي')),
        ('other', _('أخرى')),
    ]
    study_language = models.CharField(_("لغة الدراسة"), max_length=20, choices=LANGUAGE_CHOICES,
                                      blank=True, null=True)

    # حقول خاصة بالشهادات الأخرى
    CERTIFICATE_TYPE_CHOICES = [
        ('diploma', _('دبلوم')),
        ('professional', _('شهادة مهنية')),
        ('training', _('دورة تدريبية')),
        ('other', _('أخرى')),
    ]
    certificate_type = models.CharField(_("نوع الشهادة"), max_length=20, choices=CERTIFICATE_TYPE_CHOICES,
                                        blank=True, null=True)
    certificate_name = models.CharField(_("اسم الشهادة"), max_length=200, blank=True, null=True)
    certificate_issuer = models.CharField(_("الجهة المانحة"), max_length=200, blank=True, null=True)

    # معلومات إضافية
    additional_info = models.TextField(_("معلومات إضافية"), blank=True, null=True)

    # الوثائق المرفقة - سيتم ربطها من خلال نموذج المستندات Document

    class Meta:
        verbose_name = _("مؤهل أكاديمي")
        verbose_name_plural = _("المؤهلات الأكاديمية")
        ordering = ['qualification_type', '-graduation_year']

    def __str__(self):
        qualification_types = dict(self.QUALIFICATION_TYPE_CHOICES)
        qualification_type_display = qualification_types.get(self.qualification_type, self.qualification_type)

        if self.qualification_type == 'high_school':
            return f"{qualification_type_display} - {self.high_school_certificate_type} ({self.high_school_graduation_year or self.graduation_year})"
        elif self.qualification_type in ['bachelors', 'masters']:
            if self.qualification_type == 'bachelors':
                return f"{qualification_type_display} - {self.bachelor_major or self.major} ({self.bachelor_institution_name or self.institution_name})"
            else:  # masters
                return f"{qualification_type_display} - {self.masters_major or self.major} ({self.masters_institution_name or self.institution_name})"
        else:
            return f"{qualification_type_display} - {self.certificate_name} ({self.certificate_issuer})"


class LanguageProficiency(models.Model):
    """نموذج الكفاءة اللغوية"""
    application = models.ForeignKey(Application, verbose_name=_("الطلب"), on_delete=models.CASCADE,
                                    related_name="language_proficiencies")

    # حقول اللغة الإنجليزية
    ENGLISH_TEST_TYPE_CHOICES = [
        ('toefl_ibt', _('TOEFL iBT')),
        ('toefl_pbt', _('TOEFL PBT')),
        ('ielts', _('IELTS')),
        ('duolingo', _('Duolingo')),
        ('other', _('أخرى')),
    ]
    is_english = models.BooleanField(_("اللغة الإنجليزية"), default=True)
    test_type = models.CharField(_("نوع الاختبار"), max_length=20, choices=ENGLISH_TEST_TYPE_CHOICES,
                                 blank=True, null=True)
    other_test_name = models.CharField(_("اسم الاختبار الآخر"), max_length=100, blank=True, null=True)
    test_date = models.DateField(_("تاريخ الاختبار"), blank=True, null=True)
    overall_score = models.DecimalField(_("الدرجة الكلية"), max_digits=5, decimal_places=2, blank=True, null=True)
    reference_number = models.CharField(_("الرقم المرجعي للاختبار"), max_length=50, blank=True, null=True)

    # درجات فرعية للاختبار
    reading_score = models.DecimalField(_("درجة القراءة"), max_digits=5, decimal_places=2, blank=True, null=True)
    listening_score = models.DecimalField(_("درجة الاستماع"), max_digits=5, decimal_places=2, blank=True, null=True)
    speaking_score = models.DecimalField(_("درجة المحادثة"), max_digits=5, decimal_places=2, blank=True, null=True)
    writing_score = models.DecimalField(_("درجة الكتابة"), max_digits=5, decimal_places=2, blank=True, null=True)

    # حقول لغات أخرى
    LANGUAGE_CHOICES = [
        ('french', _('الفرنسية')),
        ('german', _('الألمانية')),
        ('spanish', _('الإسبانية')),
        ('chinese', _('الصينية')),
        ('other', _('أخرى')),
    ]
    other_language = models.CharField(_("اللغة"), max_length=20, choices=LANGUAGE_CHOICES, blank=True, null=True)
    other_language_name = models.CharField(_("اسم اللغة الأخرى"), max_length=50, blank=True, null=True)

    PROFICIENCY_LEVEL_CHOICES = [
        ('beginner', _('مبتدئ')),
        ('intermediate', _('متوسط')),
        ('advanced', _('متقدم')),
        ('native', _('متحدث أصلي')),
    ]
    proficiency_level = models.CharField(_("مستوى الإتقان"), max_length=20, choices=PROFICIENCY_LEVEL_CHOICES,
                                         blank=True, null=True)

    # معلومات إضافية
    additional_info = models.TextField(_("معلومات إضافية"), blank=True, null=True)

    class Meta:
        verbose_name = _("كفاءة لغوية")
        verbose_name_plural = _("الكفاءات اللغوية")

    def __str__(self):
        if self.is_english:
            test_types = dict(self.ENGLISH_TEST_TYPE_CHOICES)
            test_type_display = test_types.get(self.test_type, self.test_type)
            return f"اللغة الإنجليزية - {test_type_display} ({self.overall_score})"
        else:
            languages = dict(self.LANGUAGE_CHOICES)
            language_display = languages.get(self.other_language, self.other_language_name)
            levels = dict(self.PROFICIENCY_LEVEL_CHOICES)
            level_display = levels.get(self.proficiency_level, self.proficiency_level)
            return f"{language_display} - {level_display}"


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


def document_upload_path(instance, filename):
    """تحديد مسار رفع المستندات حسب نوعها"""
    document_type = instance.document_type
    application_id = instance.application.id
    ext = filename.split('.')[-1]
    filename = f"{document_type}_{uuid.uuid4()}.{ext}"
    return f"application_documents/{application_id}/{document_type}/{filename}"


class Document(models.Model):
    """نموذج المستندات المرفقة بالطلب"""
    application = models.ForeignKey(Application, verbose_name=_("الطلب"), on_delete=models.CASCADE,
                                    related_name="documents")

    DOCUMENT_TYPE_CHOICES = [
        # مستندات عامة
        ('cv', _('السيرة الذاتية')),
        ('personal_id', _('إثبات الهوية')),
        ('photo', _('صورة شخصية')),

        # مستندات المؤهلات الأكاديمية
        ('high_school_certificate', _('شهادة الثانوية العامة')),
        ('high_school_transcript', _('كشف درجات الثانوية العامة')),
        ('bachelors_certificate', _('شهادة البكالوريوس')),
        ('bachelors_transcript', _('كشف درجات البكالوريوس')),
        ('masters_certificate', _('شهادة الماجستير')),
        ('masters_transcript', _('كشف درجات الماجستير')),
        ('other_certificate', _('شهادة أخرى')),

        # مستندات الكفاءة اللغوية
        ('language_certificate', _('شهادة اختبار اللغة')),
        ('other_language_certificate', _('شهادة لغة أخرى')),

        # مستندات أخرى
        ('acceptance_letter', _('خطاب القبول')),
        ('research_proposal', _('مقترح البحث')),
        ('recommendation_letter', _('رسالة توصية')),
        ('other', _('مستند آخر')),
    ]

    document_type = models.CharField(_("نوع المستند"), max_length=50, choices=DOCUMENT_TYPE_CHOICES, default='other')
    name = models.CharField(_("اسم المستند"), max_length=100)
    description = models.TextField(_("وصف المستند"), blank=True, null=True)
    file = models.FileField(_("الملف"), upload_to=document_upload_path)
    upload_date = models.DateTimeField(_("تاريخ الرفع"), auto_now_add=True)
    is_required = models.BooleanField(_("مطلوب"), default=True)

    # ربط المستند بمؤهل أكاديمي (اختياري)
    academic_qualification = models.ForeignKey(AcademicQualification, verbose_name=_("المؤهل الأكاديمي"),
                                               on_delete=models.SET_NULL, null=True, blank=True,
                                               related_name="documents")

    # ربط المستند بكفاءة لغوية (اختياري)
    language_proficiency = models.ForeignKey(LanguageProficiency, verbose_name=_("الكفاءة اللغوية"),
                                             on_delete=models.SET_NULL, null=True, blank=True,
                                             related_name="documents")

    class Meta:
        verbose_name = _("مستند")
        verbose_name_plural = _("المستندات")
        ordering = ['document_type', 'upload_date']

    def __str__(self):
        return f"{self.name} - {self.application}"


class ApplicationLog(models.Model):
    """نموذج سجل التغييرات على الطلب"""
    application = models.ForeignKey(Application, verbose_name=_("الطلب"), on_delete=models.CASCADE, related_name="logs")
    from_status = models.ForeignKey(ApplicationStatus, verbose_name=_("من حالة"), on_delete=models.PROTECT,
                                    related_name="from_logs", null=True, blank=True)
    to_status = models.ForeignKey(ApplicationStatus, verbose_name=_("إلى حالة"), on_delete=models.PROTECT,
                                  related_name="to_logs")
    created_by = models.ForeignKey(User, verbose_name=_("تم بواسطة"), on_delete=models.CASCADE,
                                   related_name="application_logs")
    created_at = models.DateTimeField(_("تاريخ التغيير"), auto_now_add=True)
    comment = models.TextField(_("التعليق"), blank=True, null=True)

    class Meta:
        verbose_name = _("سجل الطلب")
        verbose_name_plural = _("سجلات الطلبات")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.application} - {self.from_status} to {self.to_status}"