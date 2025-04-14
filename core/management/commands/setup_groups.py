from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from evaluation.models import Committee, EvaluationCriterion, EvaluationRound
from applications.models import Application
from announcements.models import Scholarship


class Command(BaseCommand):
    help = 'إعداد مجموعات المستخدمين والصلاحيات'

    def handle(self, *args, **options):
        # إنشاء المجموعات
        admin_group, created_admin = Group.objects.get_or_create(name="مشرفو النظام")
        committee_group, created_committee = Group.objects.get_or_create(name="لجنة التقييم")
        faculty_group, created_faculty = Group.objects.get_or_create(name="أعضاء هيئة التدريس")

        if created_admin:
            self.stdout.write(self.style.SUCCESS('تم إنشاء مجموعة مشرفو النظام'))
        if created_committee:
            self.stdout.write(self.style.SUCCESS('تم إنشاء مجموعة لجنة التقييم'))
        if created_faculty:
            self.stdout.write(self.style.SUCCESS('تم إنشاء مجموعة أعضاء هيئة التدريس'))

        # تجميع ContentType لنماذج التقييم
        evaluation_models = [Committee, EvaluationCriterion, EvaluationRound]
        eval_content_types = [ContentType.objects.get_for_model(model) for model in evaluation_models]

        # الصلاحيات للجان التقييم - القراءة والتحديث فقط
        eval_view_perms = Permission.objects.filter(
            content_type__in=eval_content_types,
            codename__startswith='view_'
        )
        committee_group.permissions.add(*eval_view_perms)

        # صلاحيات التقييم للجان
        app_eval_ct = ContentType.objects.get_for_model(Application)
        app_perms = Permission.objects.filter(
            content_type=app_eval_ct,
            codename__in=['view_application']
        )
        committee_group.permissions.add(*app_perms)

        # صلاحيات شاملة للمشرفين
        admin_perms = Permission.objects.filter(content_type__in=eval_content_types)
        admin_group.permissions.add(*admin_perms)

        self.stdout.write(self.style.SUCCESS('تم إعداد الصلاحيات بنجاح!'))