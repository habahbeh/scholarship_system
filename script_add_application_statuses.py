# script_add_application_statuses.py

from django.db import transaction
from applications.models import ApplicationStatus

# Define the list of required statuses
statuses = [
    {
        "name": "تم التقديم",
        "description": "تم تقديم الطلب وبانتظار المراجعة الأولية",
        "order": 1,
        "requires_attachment": False
    },
    {
        "name": "قيد المراجعة",
        "description": "الطلب قيد المراجعة من قبل الإدارة",
        "order": 2,
        "requires_attachment": False
    },
    {
        "name": "مطابق للشروط",
        "description": "الطلب مطابق لشروط الابتعاث",
        "order": 3,
        "requires_attachment": False
    },
    {
        "name": "غير مطابق للشروط",
        "description": "الطلب غير مطابق لشروط الابتعاث",
        "order": 4,
        "requires_attachment": False
    },
    {
        "name": "موافق من اللجنة العليا",
        "description": "تمت الموافقة على الطلب من قبل اللجنة العليا",
        "order": 5,
        "requires_attachment": True
    },
    {
        "name": "غير موافق من اللجنة العليا",
        "description": "لم تتم الموافقة على الطلب من قبل اللجنة العليا",
        "order": 6,
        "requires_attachment": False
    },
    {
        "name": "موافق من مجلس الكلية",
        "description": "تمت الموافقة على الطلب من قبل مجلس الكلية",
        "order": 7,
        "requires_attachment": True
    },
    {
        "name": "غير موافق من مجلس الكلية",
        "description": "لم تتم الموافقة على الطلب من قبل مجلس الكلية",
        "order": 8,
        "requires_attachment": False
    },
    {
        "name": "موافق من رئيس الجامعة",
        "description": "تمت الموافقة على الطلب من قبل رئيس الجامعة",
        "order": 9,
        "requires_attachment": True
    },
    {
        "name": "غير موافق من رئيس الجامعة",
        "description": "لم تتم الموافقة على الطلب من قبل رئيس الجامعة",
        "order": 10,
        "requires_attachment": False
    },
]


def run():
    """
    حذف الحالات القديمة وإضافة الحالات الجديدة للنظام
    """
    with transaction.atomic():
        # حذف جميع الحالات الموجودة
        ApplicationStatus.objects.all().delete()

        # إضافة الحالات الجديدة
        for status_data in statuses:
            ApplicationStatus.objects.create(**status_data)

        # التحقق من عدد الحالات التي تم إنشاؤها
        status_count = ApplicationStatus.objects.count()
        print(f"تم إنشاء {status_count} حالة بنجاح")

        # طباعة جميع الحالات للتأكد
        for status in ApplicationStatus.objects.all().order_by('order'):
            print(f"{status.order}. {status.name} {'(يتطلب مرفق)' if status.requires_attachment else ''}")


# لتشغيل السكربت مباشرة من Django shell
if __name__ == '__main__':
    run()