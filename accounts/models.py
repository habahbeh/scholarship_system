from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver


class Faculty(models.Model):
    """نموذج الكليات في الجامعة"""
    name = models.CharField(_("اسم الكلية"), max_length=100)
    code = models.CharField(_("رمز الكلية"), max_length=10, unique=True)
    description = models.TextField(_("الوصف"), blank=True, null=True)

    class Meta:
        verbose_name = _("كلية")
        verbose_name_plural = _("الكليات")
        ordering = ['name']

    def __str__(self):
        return self.name


class Department(models.Model):
    """نموذج الأقسام في الكلية"""
    name = models.CharField(_("اسم القسم"), max_length=100)
    code = models.CharField(_("رمز القسم"), max_length=10, unique=True)
    faculty = models.ForeignKey(Faculty, verbose_name=_("الكلية"), related_name="departments", on_delete=models.CASCADE)
    description = models.TextField(_("الوصف"), blank=True, null=True)

    class Meta:
        verbose_name = _("قسم")
        verbose_name_plural = _("الأقسام")
        ordering = ['faculty__name', 'name']

    def __str__(self):
        return f"{self.name} - {self.faculty.name}"


class Profile(models.Model):
    """نموذج الملف الشخصي للمستخدم"""
    GENDER_CHOICES = (
        ('M', _('ذكر')),
        ('F', _('أنثى')),
    )

    ROLE_CHOICES = (
        ('student', _('طالب')),
        ('faculty', _('عضو هيئة تدريس')),
        ('admin', _('مشرف نظام')),
        ('committee', _('عضو لجنة')),
    )

    ACADEMIC_RANK_CHOICES = (
        ('assistant_prof', _('أستاذ مساعد')),
        ('associate_prof', _('أستاذ مشارك')),
        ('professor', _('أستاذ')),
        ('lecturer', _('محاضر')),
        ('na', _('غير منطبق')),
    )

    user = models.OneToOneField(User, verbose_name=_("المستخدم"), related_name="profile", on_delete=models.CASCADE)
    id_number = models.CharField(_("رقم الهوية"), max_length=20, unique=True)
    phone_number = models.CharField(_("رقم الهاتف"), max_length=15)
    date_of_birth = models.DateField(_("تاريخ الميلاد"), null=True, blank=True)
    gender = models.CharField(_("الجنس"), max_length=1, choices=GENDER_CHOICES)
    address = models.TextField(_("العنوان"), blank=True, null=True)
    role = models.CharField(_("الدور"), max_length=20, choices=ROLE_CHOICES, default='student')
    faculty = models.ForeignKey(Faculty, verbose_name=_("الكلية"), on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, verbose_name=_("القسم"), on_delete=models.SET_NULL, null=True,
                                   blank=True)
    academic_rank = models.CharField(_("الرتبة الأكاديمية"), max_length=20, choices=ACADEMIC_RANK_CHOICES, default='na')
    specialization = models.CharField(_("التخصص"), max_length=100, blank=True, null=True)
    bio = models.TextField(_("نبذة شخصية"), blank=True, null=True)
    profile_picture = models.ImageField(_("الصورة الشخصية"), upload_to='profile_pictures/', blank=True, null=True)

    class Meta:
        verbose_name = _("ملف شخصي")
        verbose_name_plural = _("الملفات الشخصية")

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    def get_role_display_class(self):
        """إرجاع صنف Bootstrap المناسب للدور"""
        role_classes = {
            'student': 'primary',
            'faculty': 'success',
            'admin': 'danger',
            'committee': 'info',
        }
        return role_classes.get(self.role, 'secondary')


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """إنشاء ملف شخصي تلقائياً عند إنشاء مستخدم جديد"""
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """حفظ الملف الشخصي عند حفظ المستخدم"""
    instance.profile.save()