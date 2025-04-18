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

    # Enhancement: Add fieldsets for better organization
    fieldsets = (
        (_('معلومات شخصية'), {
            'fields': ('id_number', 'phone_number', 'date_of_birth', 'gender', 'address')
        }),
        (_('معلومات أكاديمية'), {
            'fields': ('role', 'faculty', 'department', 'academic_rank', 'specialization')
        }),
        (_('معلومات إضافية'), {
            'fields': ('bio', 'profile_picture')
        }),
    )

    # Enhancement: Add autocomplete fields for better performance
    autocomplete_fields = ['faculty', 'department']


class UserAdmin(BaseUserAdmin):
    """تخصيص عرض المستخدم في لوحة الإدارة"""
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role')
    list_filter = ('profile__role', 'profile__faculty', 'profile__department', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'profile__id_number', 'profile__phone_number')

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
    list_display = ('name', 'code', 'description')
    search_fields = ('name', 'code')
    list_filter = ('name',)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """إدارة الأقسام"""
    list_display = ('name', 'code', 'faculty')
    list_filter = ('faculty',)
    search_fields = ('name', 'code')
    # Enhancement: Add autocomplete for faculty field
    autocomplete_fields = ['faculty']


# Add a separate ProfileAdmin if you want to manage profiles directly
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """إدارة الملفات الشخصية"""
    list_display = ('user', 'id_number', 'role', 'faculty', 'department')
    list_filter = ('role', 'faculty', 'department', 'gender', 'academic_rank')
    search_fields = ('user__username', 'user__email', 'id_number', 'phone_number')
    autocomplete_fields = ['user', 'faculty', 'department']

    fieldsets = (
        (_('معلومات المستخدم'), {
            'fields': ('user',)
        }),
        (_('معلومات شخصية'), {
            'fields': ('id_number', 'phone_number', 'date_of_birth', 'gender', 'address')
        }),
        (_('معلومات أكاديمية'), {
            'fields': ('role', 'faculty', 'department', 'academic_rank', 'specialization')
        }),
        (_('معلومات إضافية'), {
            'fields': ('bio', 'profile_picture')
        }),
    )