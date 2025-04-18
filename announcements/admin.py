from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Scholarship, Announcement, ScholarshipType


@admin.register(ScholarshipType)
class ScholarshipTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display = ('title', 'scholarship_type', 'deadline', 'status', 'is_active')
    # Fix: Remove 'is_active' from list_filter since it's a method, not a field
    list_filter = ('status', 'scholarship_type', 'deadline')
    search_fields = ('title', 'description')
    date_hierarchy = 'publication_date'
    # Fix: Remove 'created_at' from readonly_fields if it doesn't exist
    readonly_fields = ('created_by', 'updated_at')

    def save_model(self, request, obj, form, change):
        if not change:  # إذا كان إنشاء جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def is_active(self, obj):
        return obj.is_active

    is_active.boolean = True
    is_active.short_description = _('نشط')


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'publication_date', 'is_active')
    list_filter = ('is_active', 'publication_date')
    search_fields = ('title', 'content')
    date_hierarchy = 'publication_date'
    # Fix: Make sure these fields actually exist in the Announcement model
    readonly_fields = ('created_by', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        if not change:  # إذا كان إنشاء جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)