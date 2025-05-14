from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import (
    Application, ApplicationStatus, Document, ApplicationLog, ApprovalAttachment,
    HighSchoolQualification, BachelorQualification, MasterQualification, OtherCertificate,
    LanguageProficiency
)


class ApplicationStatusAdmin(admin.ModelAdmin):
    """إدارة حالات الطلبات"""
    list_display = ('name', 'order', 'requires_attachment', 'description')
    list_editable = ('order', 'requires_attachment')
    search_fields = ('name', 'description')
    ordering = ('order',)


class HighSchoolQualificationInline(admin.StackedInline):
    """إدراج مؤهلات الثانوية العامة ضمن الطلب"""
    model = HighSchoolQualification
    extra = 0
    classes = ['collapse']
    verbose_name = _("مؤهل الثانوية العامة")
    verbose_name_plural = _("مؤهلات الثانوية العامة")


class BachelorQualificationInline(admin.StackedInline):
    """إدراج مؤهلات البكالوريوس ضمن الطلب"""
    model = BachelorQualification
    extra = 0
    classes = ['collapse']
    verbose_name = _("مؤهل البكالوريوس")
    verbose_name_plural = _("مؤهلات البكالوريوس")


class MasterQualificationInline(admin.StackedInline):
    """إدراج مؤهلات الماجستير ضمن الطلب"""
    model = MasterQualification
    extra = 0
    classes = ['collapse']
    verbose_name = _("مؤهل الماجستير")
    verbose_name_plural = _("مؤهلات الماجستير")


class OtherCertificateInline(admin.StackedInline):
    """إدراج الشهادات الأخرى ضمن الطلب"""
    model = OtherCertificate
    extra = 0
    classes = ['collapse']
    verbose_name = _("شهادة أخرى")
    verbose_name_plural = _("شهادات أخرى")


class LanguageProficiencyInline(admin.StackedInline):
    """إدراج الكفاءات اللغوية ضمن الطلب"""
    model = LanguageProficiency
    extra = 0
    classes = ['collapse']
    verbose_name = _("كفاءة لغوية")
    verbose_name_plural = _("الكفاءات اللغوية")


class DocumentInline(admin.TabularInline):
    """إدراج المستندات ضمن الطلب"""
    model = Document
    extra = 0
    classes = ['collapse']
    verbose_name = _("مستند")
    verbose_name_plural = _("المستندات")
    readonly_fields = ('file_link',)

    def file_link(self, obj):
        if obj.file:
            return format_html("<a href='{0}' target='_blank'>عرض الملف</a>", obj.file.url)
        return "-"

    file_link.short_description = _("عرض الملف")


class ApplicationLogInline(admin.TabularInline):
    """إدراج سجلات الطلب ضمن الطلب"""
    model = ApplicationLog
    extra = 0
    classes = ['collapse']
    verbose_name = _("سجل")
    verbose_name_plural = _("سجلات الطلب")
    readonly_fields = ('created_at', 'created_by', 'from_status', 'to_status', 'comment')
    ordering = ('-created_at',)
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ApprovalAttachmentInline(admin.TabularInline):
    """إدراج مرفقات الموافقات ضمن الطلب"""
    model = ApprovalAttachment
    extra = 0
    classes = ['collapse']
    verbose_name = _("مرفق موافقة")
    verbose_name_plural = _("مرفقات الموافقات")
    readonly_fields = ('attachment_link',)
    fields = ('approval_type', 'attachment', 'attachment_link', 'upload_date', 'notes')

    def attachment_link(self, obj):
        if obj.attachment:
            return format_html("<a href='{0}' target='_blank'>عرض المرفق</a>", obj.attachment.url)
        return "-"

    attachment_link.short_description = _("عرض المرفق")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """إدارة طلبات الابتعاث"""
    list_display = ('id', 'applicant_name', 'scholarship_title', 'status', 'application_date', 'last_update')
    list_filter = ('status', 'scholarship', 'application_date')
    search_fields = ('applicant__username', 'applicant__first_name', 'applicant__last_name', 'scholarship__title')
    readonly_fields = ('application_date', 'last_update')
    date_hierarchy = 'application_date'
    fieldsets = (
        (_("معلومات الطلب"), {
            'fields': ('scholarship', 'applicant', 'status', 'application_date', 'last_update')
        }),
        (_("تفاصيل الطلب"), {
            'fields': (
            'motivation_letter', 'research_proposal', 'comments', 'acceptance_letter', 'acceptance_university')
        }),
        (_("ملاحظات إدارية"), {
            'fields': ('admin_notes',),
            'classes': ('collapse',)
        }),
    )
    inlines = [
        HighSchoolQualificationInline,
        BachelorQualificationInline,
        MasterQualificationInline,
        OtherCertificateInline,
        LanguageProficiencyInline,
        DocumentInline,
        ApprovalAttachmentInline,
        ApplicationLogInline,
    ]

    def applicant_name(self, obj):
        return obj.applicant.get_full_name() or obj.applicant.username

    applicant_name.short_description = _("المتقدم")

    def scholarship_title(self, obj):
        return obj.scholarship.title

    scholarship_title.short_description = _("فرصة الابتعاث")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """إدارة المستندات"""
    list_display = ('name', 'document_type', 'application_link', 'upload_date', 'is_required', 'file_link')
    list_filter = ('document_type', 'is_required', 'upload_date')
    search_fields = ('name', 'description', 'application__applicant__username')
    readonly_fields = ('upload_date', 'file_link')

    def application_link(self, obj):
        if obj.application:
            url = f"/admin/applications/application/{obj.application.id}/change/"
            return format_html("<a href='{0}'>{1}</a>", url, obj.application)
        return "-"

    application_link.short_description = _("الطلب")

    def file_link(self, obj):
        if obj.file:
            return format_html("<a href='{0}' target='_blank'>عرض الملف</a>", obj.file.url)
        return "-"

    file_link.short_description = _("عرض الملف")


@admin.register(ApplicationLog)
class ApplicationLogAdmin(admin.ModelAdmin):
    """إدارة سجلات الطلبات"""
    list_display = ('application', 'from_status', 'to_status', 'created_by', 'created_at')
    list_filter = ('to_status', 'created_at', 'created_by')
    search_fields = ('application__applicant__username', 'comment')
    readonly_fields = ('created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(HighSchoolQualification)
class HighSchoolQualificationAdmin(admin.ModelAdmin):
    """إدارة مؤهلات الثانوية العامة"""
    list_display = ('id', 'application_link', 'certificate_type', 'branch', 'graduation_year', 'gpa', 'country')
    list_filter = ('graduation_year', 'study_language')
    search_fields = ('certificate_type', 'branch', 'application__applicant__username')

    def application_link(self, obj):
        if obj.application:
            url = f"/admin/applications/application/{obj.application.id}/change/"
            return format_html("<a href='{0}'>{1}</a>", url, obj.application)
        return "-"

    application_link.short_description = _("الطلب")


@admin.register(BachelorQualification)
class BachelorQualificationAdmin(admin.ModelAdmin):
    """إدارة مؤهلات البكالوريوس"""
    list_display = (
    'id', 'application_link', 'institution_name', 'major', 'graduation_year', 'gpa', 'grade', 'study_system')
    list_filter = ('graduation_year', 'grade', 'study_system', 'bachelor_type')
    search_fields = ('institution_name', 'major', 'application__applicant__username')

    def application_link(self, obj):
        if obj.application:
            url = f"/admin/applications/application/{obj.application.id}/change/"
            return format_html("<a href='{0}'>{1}</a>", url, obj.application)
        return "-"

    application_link.short_description = _("الطلب")


@admin.register(MasterQualification)
class MasterQualificationAdmin(admin.ModelAdmin):
    """إدارة مؤهلات الماجستير"""
    list_display = (
    'id', 'application_link', 'institution_name', 'major', 'graduation_year', 'gpa', 'grade', 'masters_system')
    list_filter = ('graduation_year', 'grade', 'masters_system')
    search_fields = ('institution_name', 'major', 'application__applicant__username')

    def application_link(self, obj):
        if obj.application:
            url = f"/admin/applications/application/{obj.application.id}/change/"
            return format_html("<a href='{0}'>{1}</a>", url, obj.application)
        return "-"

    application_link.short_description = _("الطلب")


@admin.register(OtherCertificate)
class OtherCertificateAdmin(admin.ModelAdmin):
    """إدارة الشهادات الأخرى"""
    list_display = (
    'id', 'application_link', 'certificate_type', 'certificate_name', 'certificate_issuer', 'graduation_year')
    list_filter = ('certificate_type', 'graduation_year')
    search_fields = ('certificate_name', 'certificate_issuer', 'application__applicant__username')

    def application_link(self, obj):
        if obj.application:
            url = f"/admin/applications/application/{obj.application.id}/change/"
            return format_html("<a href='{0}'>{1}</a>", url, obj.application)
        return "-"

    application_link.short_description = _("الطلب")


@admin.register(LanguageProficiency)
class LanguageProficiencyAdmin(admin.ModelAdmin):
    """إدارة الكفاءات اللغوية"""
    list_display = ('id', 'application_link', 'language_type', 'proficiency_display', 'test_date')
    list_filter = ('is_english', 'test_type', 'test_date', 'proficiency_level')
    search_fields = ('application__applicant__username', 'other_test_name', 'other_language_name')

    def application_link(self, obj):
        if obj.application:
            url = f"/admin/applications/application/{obj.application.id}/change/"
            return format_html("<a href='{0}'>{1}</a>", url, obj.application)
        return "-"

    application_link.short_description = _("الطلب")

    def language_type(self, obj):
        if obj.is_english:
            test_types = dict(obj.ENGLISH_TEST_TYPE_CHOICES)
            return f"الإنجليزية - {test_types.get(obj.test_type, obj.other_test_name or '')}"
        else:
            languages = dict(obj.LANGUAGE_CHOICES)
            return languages.get(obj.other_language, obj.other_language_name or '')

    language_type.short_description = _("اللغة")

    def proficiency_display(self, obj):
        if obj.is_english:
            return f"{obj.overall_score}" if obj.overall_score else "-"
        else:
            levels = dict(obj.PROFICIENCY_LEVEL_CHOICES)
            return levels.get(obj.proficiency_level, "-")

    proficiency_display.short_description = _("مستوى الإتقان")


@admin.register(ApprovalAttachment)
class ApprovalAttachmentAdmin(admin.ModelAdmin):
    """إدارة مرفقات الموافقات"""
    list_display = ('id', 'application_link', 'approval_type', 'upload_date', 'attachment_link')
    list_filter = ('approval_type', 'upload_date')
    search_fields = ('application__applicant__username', 'notes')
    readonly_fields = ('upload_date', 'attachment_link')

    def application_link(self, obj):
        if obj.application:
            url = f"/admin/applications/application/{obj.application.id}/change/"
            return format_html("<a href='{0}'>{1}</a>", url, obj.application)
        return "-"

    application_link.short_description = _("الطلب")

    def attachment_link(self, obj):
        if obj.attachment:
            return format_html("<a href='{0}' target='_blank'>عرض المرفق</a>", obj.attachment.url)
        return "-"

    attachment_link.short_description = _("عرض المرفق")


# تسجيل النماذج في لوحة الإدارة
admin.site.register(ApplicationStatus, ApplicationStatusAdmin)