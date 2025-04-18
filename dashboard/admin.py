from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import DashboardWidget


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ('name', 'widget_type', 'is_active', 'order')
    list_filter = ('widget_type', 'is_active')
    search_fields = ('name', 'description')
    ordering = ('order',)

    fieldsets = (
        (_('معلومات الودجة'), {
            'fields': ('name', 'widget_type', 'description')
        }),
        (_('إعدادات الظهور'), {
            'fields': ('is_active', 'order', 'show_to_roles')
        }),
    )