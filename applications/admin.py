from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    Application, Document, ApplicationStatus, ApplicationLog,
    AcademicQualification, LanguageProficiency, ApprovalAttachment
)


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


class AcademicQualificationInline(admin.StackedInline):
    """عرض المؤهلات الأكاديمية كجزء من الطلب في لوحة الإدارة"""
    model = AcademicQualification
    extra = 0
    fieldsets = (
        (None, {
            'fields': ('qualification_type',)
        }),
        (_('الثانوية العامة'), {
            'classes': ('collapse',),
            'fields': ('high_school_certificate_type', 'high_school_branch', 'high_school_graduation_year',
                       'high_school_gpa', 'high_school_country')
        }),
        (_('البكالوريوس'), {
            'classes': ('collapse',),
            'fields': ('bachelor_institution_name', 'bachelor_major', 'bachelor_graduation_year',
                       'bachelor_gpa', 'bachelor_grade', 'bachelor_country', 'study_system', 'bachelor_type')
        }),
        (_('الماجستير'), {
            'classes': ('collapse',),
            'fields': ('masters_institution_name', 'masters_major', 'masters_graduation_year',
                       'masters_gpa', 'masters_grade', 'masters_country', 'masters_system', 'study_language')
        }),
        (_('شهادة أخرى'), {
            'classes': ('collapse',),
            'fields': ('certificate_type', 'certificate_name', 'certificate_issuer', 'certificate_graduation_year')
        }),
        (_('معلومات إضافية'), {
            'fields': ('additional_info',)
        }),
    )


class LanguageProficiencyInline(admin.StackedInline):
    """عرض الكفاءة اللغوية كجزء من الطلب في لوحة الإدارة"""
    model = LanguageProficiency
    extra = 0
    fieldsets = (
        (None, {
            'fields': ('is_english',)
        }),
        (_('اللغة الإنجليزية'), {
            'classes': ('collapse',),
            'fields': ('test_type', 'other_test_name', 'test_date', 'overall_score', 'reference_number',
                       'reading_score', 'listening_score', 'speaking_score', 'writing_score')
        }),
        (_('لغة أخرى'), {
            'classes': ('collapse',),
            'fields': ('other_language', 'other_language_name', 'proficiency_level')
        }),
        (_('معلومات إضافية'), {
            'fields': ('additional_info',)
        }),
    )


class ApprovalAttachmentInline(admin.TabularInline):
    """عرض مرفقات الموافقات كجزء من الطلب في لوحة الإدارة"""
    model = ApprovalAttachment
    extra = 0


@admin.register(ApplicationStatus)
class ApplicationStatusAdmin(admin.ModelAdmin):
    """إدارة حالات الطلب"""
    list_display = ('name', 'order', 'description', 'requires_attachment')
    list_editable = ('order', 'requires_attachment')
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
    inlines = [
        AcademicQualificationInline,
        LanguageProficiencyInline,
        DocumentInline,
        ApprovalAttachmentInline,
        ApplicationLogInline
    ]

    # Enhancement 1: Add fieldsets for better organization
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('scholarship', 'applicant', 'status', 'application_date', 'last_update')
        }),
        (_('محتوى الطلب'), {
            'fields': ('motivation_letter', 'research_proposal', 'comments')
        }),
        (_('القبول'), {
            'fields': ('acceptance_letter', 'acceptance_university')
        }),
        (_('ملاحظات إدارية'), {
            'fields': ('admin_notes',)
        }),
    )

    # Enhancement 2: Add autocomplete_fields for better performance with large datasets
    autocomplete_fields = ['scholarship', 'applicant', 'status']

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
    list_display = ('name', 'document_type', 'application', 'upload_date', 'is_required')
    list_filter = ('document_type', 'is_required', 'upload_date')
    search_fields = ('name', 'description', 'application__id', 'application__applicant__username')
    date_hierarchy = 'upload_date'
    # Enhancement: Add autocomplete for application field
    autocomplete_fields = ['application', 'academic_qualification', 'language_proficiency']


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


@admin.register(AcademicQualification)
class AcademicQualificationAdmin(admin.ModelAdmin):
    """إدارة المؤهلات الأكاديمية"""
    list_display = ('get_qualification_type_display', 'application', 'get_major_display', 'get_institution_display',
                    'get_graduation_year_display')
    list_filter = (
    'qualification_type', 'high_school_graduation_year', 'bachelor_graduation_year', 'masters_graduation_year',
    'certificate_graduation_year')
    search_fields = ('application__id', 'application__applicant__username', 'bachelor_major', 'masters_major',
                     'bachelor_institution_name', 'masters_institution_name')
    autocomplete_fields = ['application']
    fieldsets = (
        (None, {
            'fields': ('application', 'qualification_type')
        }),
        (_('الثانوية العامة'), {
            'classes': ('collapse',),
            'fields': ('high_school_certificate_type', 'high_school_branch', 'high_school_graduation_year',
                       'high_school_gpa', 'high_school_country')
        }),
        (_('البكالوريوس'), {
            'classes': ('collapse',),
            'fields': ('bachelor_institution_name', 'bachelor_major', 'bachelor_graduation_year',
                       'bachelor_gpa', 'bachelor_grade', 'bachelor_country', 'study_system', 'bachelor_type')
        }),
        (_('الماجستير'), {
            'classes': ('collapse',),
            'fields': ('masters_institution_name', 'masters_major', 'masters_graduation_year',
                       'masters_gpa', 'masters_grade', 'masters_country', 'masters_system', 'study_language')
        }),
        (_('شهادة أخرى'), {
            'classes': ('collapse',),
            'fields': ('certificate_type', 'certificate_name', 'certificate_issuer', 'certificate_graduation_year')
        }),
        (_('معلومات إضافية'), {
            'fields': ('additional_info',)
        }),
    )

    def get_major_display(self, obj):
        """عرض التخصص بناءً على نوع المؤهل"""
        if obj.qualification_type == 'bachelor':
            return obj.bachelor_major
        elif obj.qualification_type == 'masters':
            return obj.masters_major
        return "-"

    get_major_display.short_description = _("التخصص")

    def get_institution_display(self, obj):
        """عرض اسم المؤسسة بناءً على نوع المؤهل"""
        if obj.qualification_type == 'bachelor':
            return obj.bachelor_institution_name
        elif obj.qualification_type == 'masters':
            return obj.masters_institution_name
        elif obj.qualification_type == 'other':
            return obj.certificate_issuer
        return "-"

    get_institution_display.short_description = _("المؤسسة التعليمية")

    def get_graduation_year_display(self, obj):
        """عرض سنة التخرج بناءً على نوع المؤهل"""
        if obj.qualification_type == 'high_school':
            return obj.high_school_graduation_year
        elif obj.qualification_type == 'bachelor':
            return obj.bachelor_graduation_year
        elif obj.qualification_type == 'masters':
            return obj.masters_graduation_year
        elif obj.qualification_type == 'other':
            return obj.certificate_graduation_year
        return "-"

    get_graduation_year_display.short_description = _("سنة التخرج")


@admin.register(LanguageProficiency)
class LanguageProficiencyAdmin(admin.ModelAdmin):
    """إدارة الكفاءة اللغوية"""
    list_display = ('get_language_display', 'application', 'get_proficiency_display')
    list_filter = ('is_english', 'test_type', 'other_language')
    search_fields = ('application__id', 'application__applicant__username')
    autocomplete_fields = ['application']
    fieldsets = (
        (None, {
            'fields': ('application', 'is_english')
        }),
        (_('اللغة الإنجليزية'), {
            'classes': ('collapse',),
            'fields': ('test_type', 'other_test_name', 'test_date', 'overall_score', 'reference_number',
                       'reading_score', 'listening_score', 'speaking_score', 'writing_score')
        }),
        (_('لغة أخرى'), {
            'classes': ('collapse',),
            'fields': ('other_language', 'other_language_name', 'proficiency_level')
        }),
        (_('معلومات إضافية'), {
            'fields': ('additional_info',)
        }),
    )

    def get_language_display(self, obj):
        """عرض اسم اللغة بشكل مناسب"""
        if obj.is_english:
            return _("اللغة الإنجليزية")
        else:
            if obj.other_language == 'other':
                return obj.other_language_name
            return obj.get_other_language_display()

    get_language_display.short_description = _("اللغة")

    def get_proficiency_display(self, obj):
        """عرض مستوى الإتقان بشكل مناسب"""
        if obj.is_english:
            return f"{obj.get_test_type_display()} ({obj.overall_score})"
        else:
            return obj.get_proficiency_level_display()

    get_proficiency_display.short_description = _("مستوى الإتقان")


@admin.register(ApprovalAttachment)
class ApprovalAttachmentAdmin(admin.ModelAdmin):
    """إدارة مرفقات الموافقات"""
    list_display = ('application', 'get_approval_type_display', 'upload_date')
    list_filter = ('approval_type', 'upload_date')
    search_fields = ('application__id', 'application__applicant__username', 'notes')
    date_hierarchy = 'upload_date'
    autocomplete_fields = ['application']