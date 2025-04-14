from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Application, Document, ApplicationStatus, ApplicationLog


class DocumentInline(admin.TabularInline):
    """عرض المستندات كجزء من الطلب في لوحة الإدارة"""
    model = Document
    extra = 0


class ApplicationLogInline(admin.TabularInline):
    """عرض سجل الطلب كجزء من الطلب في لوحة الإدارة"""
    model = ApplicationLog
    extra = 0
    readonly_fields = ('created_at', 'created_by', 'from_status', 'to_status', 'comment')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ApplicationStatus)
class ApplicationStatusAdmin(admin.ModelAdmin):
    """إدارة حالات الطلب"""
    list_display = ('name', 'order', 'description')
    list_editable = ('order',)
    search_fields = ('name', 'description')
    ordering = ('order',)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """إدارة طلبات الابتعاث"""
    list_display = ('id', 'applicant', 'scholarship', 'status', 'application_date', 'last_update')
    list_filter = ('status', 'application_date', 'scholarship')
    search_fields = ('applicant__username', 'applicant__first_name', 'applicant__last_name', 'scholarship__title')
    date_hierarchy = 'application_date'
    readonly_fields = ('application_date', 'last_update')
    inlines = [DocumentInline, ApplicationLogInline]

    def save_model(self, request, obj, form, change):
        """تسجيل تغييرات الحالة في سجل الطلب"""
        if change and 'status' in form.changed_data:
            # إذا تم تغيير الحالة، أنشئ سجل جديد
            old_obj = self.model.objects.get(pk=obj.pk)
            ApplicationLog.objects.create(
                application=obj,
                from_status=old_obj.status,
                to_status=obj.status,
                created_by=request.user,
                comment=_("تم تغيير الحالة من لوحة الإدارة")
            )
        super().save_model(request, obj, form, change)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """إدارة المستندات"""
    list_display = ('name', 'application', 'upload_date', 'is_required')
    list_filter = ('is_required', 'upload_date')
    search_fields = ('name', 'description', 'application__id', 'application__applicant__username')
    date_hierarchy = 'upload_date'


@admin.register(ApplicationLog)
class ApplicationLogAdmin(admin.ModelAdmin):
    """إدارة سجلات التغييرات"""
    list_display = ('application', 'from_status', 'to_status', 'created_by', 'created_at')
    list_filter = ('to_status', 'created_at')
    search_fields = ('application__id', 'application__applicant__username', 'comment')
    date_hierarchy = 'created_at'
    readonly_fields = ('application', 'from_status', 'to_status', 'created_by', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False