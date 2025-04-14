from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import Profile, Faculty, Department


class ProfileInline(admin.StackedInline):
    """عرض الملف الشخصي كجزء من المستخدم في لوحة الإدارة"""
    model = Profile
    can_delete = False
    verbose_name_plural = _('الملف الشخصي')
    fk_name = 'user'


class UserAdmin(BaseUserAdmin):
    """تخصيص عرض المستخدم في لوحة الإدارة"""
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role')
    list_filter = ('profile__role', 'is_staff', 'is_superuser', 'is_active')

    def get_role(self, obj):
        return obj.profile.get_role_display()

    get_role.short_description = _('الدور')

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)


# إعادة تسجيل نموذج المستخدم مع الإدارة المخصصة
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    """إدارة الكليات"""
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """إدارة الأقسام"""
    list_display = ('name', 'code', 'faculty')
    list_filter = ('faculty',)
    search_fields = ('name', 'code')