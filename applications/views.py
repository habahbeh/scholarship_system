from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
import weasyprint
from django.conf import settings
import os
from django.urls import reverse

from announcements.models import Scholarship
from .models import (
    Application, Document, ApplicationStatus, ApplicationLog, ApprovalAttachment,
    HighSchoolQualification, BachelorQualification, MasterQualification, OtherCertificate,
    LanguageProficiency
)
from .forms import (
    DocumentForm, DocumentUploadForm, ApplicationStatusForm, ApplicationFilterForm,
    RequirementsCheckForm, HigherCommitteeApprovalForm, FacultyCouncilApprovalForm, PresidentApprovalForm,
    ApplicationTabsForm, HighSchoolQualificationFormSet, BachelorQualificationFormSet,
    MasterQualificationFormSet, OtherCertificateFormSet, LanguageProficiencyFormSet, DocumentFormSet,
    DepartmentCouncilApprovalForm, DeansCouncilApprovalForm
)


# --- New Workflow Views ---

@login_required
@permission_required('applications.view_application')
def admin_applications_list(request):
    """عرض قائمة الطلبات لمدير النظام"""
    # البحث والتصفية
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search', '')

    applications = Application.objects.all().order_by('-application_date')

    # تطبيق فلتر الحالة
    if status_filter:
        applications = applications.filter(status_id=status_filter)

    # تطبيق البحث
    if search_query:
        applications = applications.filter(
            Q(applicant__first_name__icontains=search_query) |
            Q(applicant__last_name__icontains=search_query) |
            Q(applicant__username__icontains=search_query) |
            Q(scholarship__title__icontains=search_query)
        )

    # الترقيم
    paginator = Paginator(applications, 10)
    page = request.GET.get('page')
    applications_page = paginator.get_page(page)

    # قائمة حالات الطلبات للفلترة
    statuses = ApplicationStatus.objects.all()

    context = {
        'applications': applications_page,
        'statuses': statuses,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'applications/admin_applications_list.html', context)


@login_required
@permission_required('applications.change_application', raise_exception=True)
def check_requirements(request, application_id):
    """مطابقة الشروط للطلب"""
    application = get_object_or_404(Application, pk=application_id)

    # التحقق من أن الطلب في حالة تسمح بمطابقة الشروط
    if application.status.order > 1:  # تغيير من 2 إلى 1 لأن قيد المراجعة تم حذفها
        messages.error(request, _("لا يمكن مطابقة الشروط لهذا الطلب في حالته الحالية"))
        return redirect('applications:admin_applications_list')

    if request.method == 'POST':
        form = RequirementsCheckForm(request.POST)
        if form.is_valid():
            meets_requirements = form.cleaned_data['meets_requirements']
            notes = form.cleaned_data['notes']

            # تحديث حالة الطلب
            if meets_requirements == 'yes':
                # البحث عن حالة "مطابق للشروط" (order=2 في النظام الجديد)
                status = ApplicationStatus.objects.get(order=2)
            else:
                # البحث عن حالة "غير مطابق للشروط" (order=3 في النظام الجديد)
                status = ApplicationStatus.objects.get(order=3)

            old_status = application.status
            application.status = status
            application.admin_notes = notes
            application.save()

            # إضافة سجل للتغيير
            ApplicationLog.objects.create(
                application=application,
                from_status=old_status,
                to_status=status,
                created_by=request.user,
                comment=_("تم تحديث مطابقة الشروط") + (f": {notes}" if notes else "")
            )

            messages.success(request, _("تم تحديث حالة الطلب بنجاح"))
            return redirect('applications:admin_applications_list')
    else:
        # تهيئة النموذج
        form = RequirementsCheckForm()

    context = {
        'form': form,
        'application': application,
    }
    return render(request, 'applications/check_requirements.html', context)



@login_required
@permission_required('applications.change_application', raise_exception=True)
def higher_committee_approval(request, application_id):
    """موافقة اللجنة العليا"""
    application = get_object_or_404(Application, pk=application_id)

    # التحقق من أن الطلب مطابق للشروط
    if application.status.order != 2:  # تغيير من 3 إلى 2
        messages.error(request, _("لا يمكن تقديم موافقة اللجنة العليا لهذا الطلب في حالته الحالية"))
        return redirect('applications:admin_applications_list')

    if request.method == 'POST':
        form = HigherCommitteeApprovalForm(request.POST, request.FILES)
        if form.is_valid():
            is_approved = form.cleaned_data['is_approved']
            notes = form.cleaned_data['notes']

            # تحديث حالة الطلب
            if is_approved == 'yes':
                # البحث عن حالة "موافق من اللجنة العليا" (order=4 في النظام الجديد)
                status = ApplicationStatus.objects.get(order=4)

                # حفظ مرفق الموافقة
                attachment = form.cleaned_data['attachment']
                if attachment:
                    approval_attachment = ApprovalAttachment(
                        application=application,
                        approval_type='higher_committee',
                        attachment=attachment,
                        notes=notes
                    )
                    approval_attachment.save()
            else:
                # البحث عن حالة "غير موافق من اللجنة العليا" (order=5 في النظام الجديد)
                status = ApplicationStatus.objects.get(order=5)

            old_status = application.status
            application.status = status
            application.save()

            # إضافة سجل للتغيير
            ApplicationLog.objects.create(
                application=application,
                from_status=old_status,
                to_status=status,
                created_by=request.user,
                comment=_("قرار اللجنة العليا") + (f": {notes}" if notes else "")
            )

            messages.success(request, _("تم تحديث حالة الطلب بنجاح"))
            return redirect('applications:admin_applications_list')
    else:
        # تهيئة النموذج
        form = HigherCommitteeApprovalForm()

    context = {
        'form': form,
        'application': application,
    }

    return render(request, 'applications/higher_committee_approval.html', context)


@login_required
@permission_required('applications.change_application', raise_exception=True)
def department_council_approval(request, application_id):
    """موافقة مجلس القسم"""
    application = get_object_or_404(Application, pk=application_id)

    # التحقق من أن الطلب موافق من اللجنة العليا
    if application.status.order != 4:  # حالة موافق من اللجنة العليا
        messages.error(request, _("لا يمكن تقديم موافقة مجلس القسم لهذا الطلب في حالته الحالية"))
        return redirect('applications:admin_applications_list')

    # الحصول على مرفقات اللجنة العليا
    higher_committee_attachments = ApprovalAttachment.objects.filter(
        application=application,
        approval_type='higher_committee'
    )

    if request.method == 'POST':
        form = DepartmentCouncilApprovalForm(request.POST, request.FILES)
        if form.is_valid():
            is_approved = form.cleaned_data['is_approved']
            notes = form.cleaned_data['notes']

            # تحديث حالة الطلب
            if is_approved == 'yes':
                # البحث عن حالة "موافق من مجلس القسم" (order=6)
                status = ApplicationStatus.objects.get(order=6)

                # حفظ مرفق الموافقة
                attachment = form.cleaned_data['attachment']
                if attachment:
                    approval_attachment = ApprovalAttachment(
                        application=application,
                        approval_type='department_council',
                        attachment=attachment,
                        notes=notes
                    )
                    approval_attachment.save()
            else:
                # البحث عن حالة "غير موافق من مجلس القسم" (order=7)
                status = ApplicationStatus.objects.get(order=7)

            old_status = application.status
            application.status = status
            application.save()

            # إضافة سجل للتغيير
            ApplicationLog.objects.create(
                application=application,
                from_status=old_status,
                to_status=status,
                created_by=request.user,
                comment=_("قرار مجلس القسم") + (f": {notes}" if notes else "")
            )

            messages.success(request, _("تم تحديث حالة الطلب بنجاح"))
            return redirect('applications:admin_applications_list')
    else:
        # تهيئة النموذج
        form = DepartmentCouncilApprovalForm()

    context = {
        'form': form,
        'application': application,
        'higher_committee_attachments': higher_committee_attachments
    }
    return render(request, 'applications/department_council_approval.html', context)


@login_required
@permission_required('applications.change_application', raise_exception=True)
def faculty_council_approval(request, application_id):
    """موافقة مجلس الكلية"""
    application = get_object_or_404(Application, pk=application_id)

    # التحقق من أن الطلب موافق من مجلس القسم
    if application.status.order != 6:  # تغيير من 5 إلى 6 (موافق من مجلس القسم)
        messages.error(request, _("لا يمكن تقديم موافقة مجلس الكلية لهذا الطلب في حالته الحالية"))
        return redirect('applications:admin_applications_list')

    # الحصول على مرفقات اللجنة العليا ومجلس القسم
    higher_committee_attachments = ApprovalAttachment.objects.filter(
        application=application,
        approval_type='higher_committee'
    )

    department_council_attachments = ApprovalAttachment.objects.filter(
        application=application,
        approval_type='department_council'
    )

    if request.method == 'POST':
        form = FacultyCouncilApprovalForm(request.POST, request.FILES)
        if form.is_valid():
            is_approved = form.cleaned_data['is_approved']
            notes = form.cleaned_data['notes']

            # تحديث حالة الطلب
            if is_approved == 'yes':
                # البحث عن حالة "موافق من مجلس الكلية" (order=8)
                status = ApplicationStatus.objects.get(order=8)

                # حفظ مرفق الموافقة
                attachment = form.cleaned_data['attachment']
                if attachment:
                    approval_attachment = ApprovalAttachment(
                        application=application,
                        approval_type='faculty_council',
                        attachment=attachment,
                        notes=notes
                    )
                    approval_attachment.save()
            else:
                # البحث عن حالة "غير موافق من مجلس الكلية" (order=9)
                status = ApplicationStatus.objects.get(order=9)

            old_status = application.status
            application.status = status
            application.save()

            # إضافة سجل للتغيير
            ApplicationLog.objects.create(
                application=application,
                from_status=old_status,
                to_status=status,
                created_by=request.user,
                comment=_("قرار مجلس الكلية") + (f": {notes}" if notes else "")
            )

            messages.success(request, _("تم تحديث حالة الطلب بنجاح"))
            return redirect('applications:admin_applications_list')
    else:
        # تهيئة النموذج
        form = FacultyCouncilApprovalForm()

    context = {
        'form': form,
        'application': application,
        'higher_committee_attachments': higher_committee_attachments,
        'department_council_attachments': department_council_attachments
    }
    return render(request, 'applications/faculty_council_approval.html', context)


# تعديل دالة president_approval إلى deans_council_approval
@login_required
@permission_required('applications.change_application', raise_exception=True)
def deans_council_approval(request, application_id):
    """موافقة مجلس العمداء"""
    application = get_object_or_404(Application, pk=application_id)

    # التحقق من أن الطلب موافق من مجلس الكلية
    if application.status.order != 8:  # تغيير من 7 إلى 8
        messages.error(request, _("لا يمكن تقديم موافقة مجلس العمداء لهذا الطلب في حالته الحالية"))
        return redirect('applications:admin_applications_list')

    # الحصول على مرفقات سابقة
    higher_committee_attachments = ApprovalAttachment.objects.filter(
        application=application,
        approval_type='higher_committee'
    )

    department_council_attachments = ApprovalAttachment.objects.filter(
        application=application,
        approval_type='department_council'
    )

    faculty_council_attachments = ApprovalAttachment.objects.filter(
        application=application,
        approval_type='faculty_council'
    )

    if request.method == 'POST':
        form = DeansCouncilApprovalForm(request.POST, request.FILES)
        if form.is_valid():
            is_approved = form.cleaned_data['is_approved']
            notes = form.cleaned_data['notes']

            # تحديث حالة الطلب
            if is_approved == 'yes':
                # البحث عن حالة "موافق من مجلس العمداء" (order=10)
                status = ApplicationStatus.objects.get(order=10)

                # حفظ مرفق الموافقة
                attachment = form.cleaned_data['attachment']
                if attachment:
                    approval_attachment = ApprovalAttachment(
                        application=application,
                        approval_type='deans_council',
                        attachment=attachment,
                        notes=notes
                    )
                    approval_attachment.save()
            else:
                # البحث عن حالة "غير موافق من مجلس العمداء" (order=11)
                status = ApplicationStatus.objects.get(order=11)

            old_status = application.status
            application.status = status
            application.save()

            # إضافة سجل للتغيير
            ApplicationLog.objects.create(
                application=application,
                from_status=old_status,
                to_status=status,
                created_by=request.user,
                comment=_("قرار مجلس العمداء") + (f": {notes}" if notes else "")
            )

            messages.success(request, _("تم تحديث حالة الطلب بنجاح"))
            return redirect('applications:admin_applications_list')
    else:
        # تهيئة النموذج
        form = DeansCouncilApprovalForm()

    context = {
        'form': form,
        'application': application,
        'higher_committee_attachments': higher_committee_attachments,
        'department_council_attachments': department_council_attachments,
        'faculty_council_attachments': faculty_council_attachments
    }
    return render(request, 'applications/deans_council_approval.html', context)


# --- Report Views ---

@login_required
@permission_required('applications.view_application')
def requirements_report(request):
    """تقرير الطلبات المطابقة للشروط"""
    # الحصول على الطلبات المطابقة للشروط (حالة رقم 2)
    applications = Application.objects.filter(status__order=2).order_by('-application_date')

    context = {
        'applications': applications,
        'title': _("تقرير الطلبات المطابقة للشروط"),
        'date': timezone.now()
    }

    # تحديد ما إذا كان التقرير للعرض أو للطباعة
    if request.GET.get('print') == 'true':
        # إنشاء ملف PDF
        html_string = render_to_string('applications/reports/requirements_report_pdf.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'filename="requirements_report.pdf"'

        # استخدام weasyprint لتحويل HTML إلى PDF
        pdf = weasyprint.HTML(string=html_string).write_pdf()
        response.write(pdf)
        return response

    return render(request, 'applications/reports/requirements_report.html', context)


@login_required
@permission_required('applications.view_application')
def higher_committee_report(request):
    """تقرير الطلبات الموافق عليها من اللجنة العليا"""
    # الحصول على الطلبات الموافق عليها من اللجنة العليا (حالة رقم 4)
    applications = Application.objects.filter(status__order=4).order_by('-application_date')

    # تحميل المرفقات للطلبات
    for application in applications:
        application.higher_committee_attachment = ApprovalAttachment.objects.filter(
            application=application,
            approval_type='higher_committee'
        ).first()

    context = {
        'applications': applications,
        'title': _("تقرير الطلبات الموافق عليها من اللجنة العليا"),
        'date': timezone.now()
    }

    # تحديد ما إذا كان التقرير للعرض أو للطباعة
    if request.GET.get('print') == 'true':
        # إنشاء ملف PDF
        html_string = render_to_string('applications/reports/higher_committee_report_pdf.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'filename="higher_committee_report.pdf"'

        # استخدام weasyprint لتحويل HTML إلى PDF
        pdf = weasyprint.HTML(string=html_string).write_pdf()
        response.write(pdf)
        return response

    return render(request, 'applications/reports/higher_committee_report.html', context)


@login_required
@permission_required('applications.view_application')
def faculty_council_report(request):
    """تقرير الطلبات الموافق عليها من مجلس الكلية"""
    # الحصول على الطلبات الموافق عليها من مجلس الكلية (حالة رقم 8)
    applications = Application.objects.filter(status__order=8).order_by('-application_date')

    # تحميل المرفقات للطلبات
    for application in applications:
        application.higher_committee_attachment = ApprovalAttachment.objects.filter(
            application=application,
            approval_type='higher_committee'
        ).first()

        application.faculty_council_attachment = ApprovalAttachment.objects.filter(
            application=application,
            approval_type='faculty_council'
        ).first()

    context = {
        'applications': applications,
        'title': _("تقرير الطلبات الموافق عليها من مجلس الكلية"),
        'date': timezone.now()
    }

    # تحديد ما إذا كان التقرير للعرض أو للطباعة
    if request.GET.get('print') == 'true':
        # إنشاء ملف PDF
        html_string = render_to_string('applications/reports/faculty_council_report_pdf.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'filename="faculty_council_report.pdf"'

        # استخدام weasyprint لتحويل HTML إلى PDF
        pdf = weasyprint.HTML(string=html_string).write_pdf()
        response.write(pdf)
        return response

    return render(request, 'applications/reports/faculty_council_report.html', context)


@login_required
@permission_required('applications.view_application')
def president_report(request):
    """تقرير الطلبات الموافق عليها من رئيس الجامعة"""
    # الحصول على الطلبات الموافق عليها من رئيس الجامعة (حالة رقم 9)
    applications = Application.objects.filter(status__order=9).order_by('-application_date')

    # تحميل المرفقات للطلبات
    for application in applications:
        application.higher_committee_attachment = ApprovalAttachment.objects.filter(
            application=application,
            approval_type='higher_committee'
        ).first()

        application.faculty_council_attachment = ApprovalAttachment.objects.filter(
            application=application,
            approval_type='faculty_council'
        ).first()

        application.president_attachment = ApprovalAttachment.objects.filter(
            application=application,
            approval_type='president'
        ).first()

    context = {
        'applications': applications,
        'title': _("تقرير الطلبات الموافق عليها من رئيس الجامعة"),
        'date': timezone.now()
    }

    # تحديد ما إذا كان التقرير للعرض أو للطباعة
    if request.GET.get('print') == 'true':
        # إنشاء ملف PDF
        html_string = render_to_string('applications/reports/president_report_pdf.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'filename="president_report.pdf"'

        # استخدام weasyprint لتحويل HTML إلى PDF
        pdf = weasyprint.HTML(string=html_string).write_pdf()
        response.write(pdf)
        return response

    return render(request, 'applications/reports/president_report.html', context)


@login_required
@permission_required('applications.view_application')
def application_full_report(request, application_id):
    """تقرير تفصيلي لطلب معين مع جميع المرفقات"""
    application = get_object_or_404(Application, pk=application_id)

    # Get all attachments
    attachments = ApprovalAttachment.objects.filter(application=application)

    # Pre-filter attachments by type and get the most recent ones
    higher_committee_attachment = attachments.filter(
        approval_type='higher_committee'
    ).order_by('-upload_date').first()

    faculty_council_attachment = attachments.filter(
        approval_type='faculty_council'
    ).order_by('-upload_date').first()

    president_attachment = attachments.filter(
        approval_type='president'
    ).order_by('-upload_date').first()

    # الحصول على المؤهلات الأكاديمية المختلفة لهذا الطلب
    high_school_qualifications = application.high_school_qualifications.all()
    bachelor_qualifications = application.bachelor_qualifications.all()
    master_qualifications = application.master_qualifications.all()
    other_certificates = application.other_certificates.all()

    # الحصول على الكفاءات اللغوية
    language_proficiencies = LanguageProficiency.objects.filter(application=application)

    # الحصول على المستندات
    documents = Document.objects.filter(application=application)

    context = {
        'application': application,
        'attachments': attachments,
        'higher_committee_attachment': higher_committee_attachment,
        'faculty_council_attachment': faculty_council_attachment,
        'president_attachment': president_attachment,
        'high_school_qualifications': high_school_qualifications,
        'bachelor_qualifications': bachelor_qualifications,
        'master_qualifications': master_qualifications,
        'other_certificates': other_certificates,
        'language_proficiencies': language_proficiencies,
        'documents': documents,
        'title': _("تقرير تفصيلي لطلب ابتعاث"),
        'date': timezone.now()
    }

    # تحديد ما إذا كان التقرير للعرض أو للطباعة
    if request.GET.get('print') == 'true':
        # إنشاء ملف PDF
        html_string = render_to_string('applications/reports/application_full_report_pdf.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'filename="application_{application_id}_report.pdf"'

        # استخدام weasyprint لتحويل HTML إلى PDF
        pdf = weasyprint.HTML(string=html_string).write_pdf()
        response.write(pdf)
        return response

    return render(request, 'applications/reports/application_full_report.html', context)

# --- Standard Application Views ---



@login_required
def application_documents(request, application_id):
    """إدارة مستندات الطلب"""
    application = get_object_or_404(Application, id=application_id, applicant=request.user)

    # الحصول على المؤهلات الأكاديمية المختلفة والكفاءات اللغوية لربطها بالمستندات
    high_school_qualifications = application.high_school_qualifications.all()
    bachelor_qualifications = application.bachelor_qualifications.all()
    master_qualifications = application.master_qualifications.all()
    other_certificates = application.other_certificates.all()
    language_proficiencies = LanguageProficiency.objects.filter(application=application)

    # استخراج أنواع المستندات الموجودة للتحقق من المستندات المطلوبة
    document_types = list(Document.objects.filter(application=application).values_list('document_type', flat=True))

    # الحصول على المستندات المرفوعة
    documents = Document.objects.filter(application=application)

    if request.method == 'POST':
        # استخدام نموذج DocumentUploadForm القديم أو تكييف DocumentFormSet للاستخدام هنا
        form = DocumentUploadForm(request.POST, request.FILES)

        if form.is_valid():
            document_type = form.cleaned_data['document_type']
            description = form.cleaned_data['description']
            file = form.cleaned_data['file']

            # استخراج نوع المستند من الخيارات
            document_type_display = dict(form.fields['document_type'].choices)[document_type]

            # إنشاء المستند مع إمكانية الربط بالمؤهلات
            document = Document(
                application=application,
                document_type=document_type,
                name=document_type_display,
                description=description,
                file=file,
                is_required=True if document_type in ['cv', 'personal_id', 'high_school_certificate', 'bachelors_certificate', 'language_certificate'] else False
            )

            # إضافة العلاقات بالمؤهلات إذا تم تحديدها
            high_school_id = request.POST.get('high_school_qualification')
            bachelor_id = request.POST.get('bachelor_qualification')
            master_id = request.POST.get('master_qualification')
            other_id = request.POST.get('other_certificate')
            language_id = request.POST.get('language_proficiency')

            if high_school_id and high_school_id != '':
                document.high_school_qualification_id = high_school_id

            if bachelor_id and bachelor_id != '':
                document.bachelor_qualification_id = bachelor_id

            if master_id and master_id != '':
                document.master_qualification_id = master_id

            if other_id and other_id != '':
                document.other_certificate_id = other_id

            if language_id and language_id != '':
                document.language_proficiency_id = language_id

            document.save()

            messages.success(request, _("تم رفع المستند بنجاح"))
            return redirect('applications:application_documents', application_id=application.id)
    else:
        # تهيئة نموذج DocumentUploadForm
        form = DocumentUploadForm()

    context = {
        'form': form,
        'application': application,
        'documents': documents,
        'document_types': document_types,
        'high_school_qualifications': high_school_qualifications,
        'bachelor_qualifications': bachelor_qualifications,
        'master_qualifications': master_qualifications,
        'other_certificates': other_certificates,
        'language_proficiencies': language_proficiencies,
    }
    return render(request, 'applications/application_documents.html', context)

@login_required
def delete_document(request, document_id):
    """حذف مستند"""
    document = get_object_or_404(Document, id=document_id)
    application = document.application

    # التحقق من أن المستخدم هو صاحب الطلب
    if application.applicant != request.user:
        messages.error(request, _("ليس لديك صلاحية حذف هذا المستند"))
        return redirect('applications:my_applications')

    if request.method == 'POST':
        document.delete()
        messages.success(request, _("تم حذف المستند بنجاح"))
        return redirect('applications:application_documents', application_id=application.id)

    context = {
        'document': document,
        'application': application,
    }
    return render(request, 'applications/document_confirm_delete.html', context)


@login_required
def my_applications(request):
    """عرض طلبات المستخدم"""
    applications = Application.objects.filter(applicant=request.user).order_by('-application_date')

    # ترقيم الصفحات
    paginator = Paginator(applications, 10)  # 10 عناصر في كل صفحة
    page = request.GET.get('page')
    try:
        applications_page = paginator.page(page)
    except PageNotAnInteger:
        applications_page = paginator.page(1)
    except EmptyPage:
        applications_page = paginator.page(paginator.num_pages)

    context = {
        'applications': applications_page,
    }
    return render(request, 'applications/my_applications.html', context)


@login_required
def application_detail(request, application_id):
    """عرض تفاصيل الطلب"""
    # يمكن للمستخدم عرض طلبه فقط، أو للمستخدمين ذوي الصلاحيات عرض أي طلب
    if request.user.has_perm('applications.view_application'):
        application = get_object_or_404(Application, id=application_id)
    else:
        application = get_object_or_404(Application, id=application_id, applicant=request.user)

    # الحصول على المؤهلات الأكاديمية المختلفة
    high_school_qualifications = application.high_school_qualifications.all()
    bachelor_qualifications = application.bachelor_qualifications.all()
    master_qualifications = application.master_qualifications.all()
    other_certificates = application.other_certificates.all()

    # الحصول على الكفاءات اللغوية
    language_proficiencies = LanguageProficiency.objects.filter(application=application)

    # الحصول على المستندات وسجلات الطلب
    documents = Document.objects.filter(application=application)
    logs = ApplicationLog.objects.filter(application=application).order_by('-created_at')

    # تصنيف وإعداد المستندات حسب النوع
    document_types = list(documents.values_list('document_type', flat=True))

    context = {
        'application': application,
        'high_school_qualifications': high_school_qualifications,
        'bachelor_qualifications': bachelor_qualifications,
        'master_qualifications': master_qualifications,
        'other_certificates': other_certificates,
        'language_proficiencies': language_proficiencies,
        'documents': documents,
        'document_types': document_types,
        'logs': logs,
    }
    return render(request, 'applications/application_detail.html', context)



@login_required
@permission_required('applications.change_application', raise_exception=True)
def change_status(request, application_id):
    """تغيير حالة الطلب (للمشرفين)"""
    application = get_object_or_404(Application, id=application_id)
    statuses = ApplicationStatus.objects.exclude(id=application.status.id).order_by('order')

    if request.method == 'POST':
        status_id = request.POST.get('status')
        form = ApplicationStatusForm(request.POST)

        if form.is_valid() and status_id:
            new_status = get_object_or_404(ApplicationStatus, id=status_id)
            old_status = application.status

            # تحديث حالة الطلب
            application.status = new_status
            application.save()

            # إنشاء سجل للتغيير
            ApplicationLog.objects.create(
                application=application,
                from_status=old_status,
                to_status=new_status,
                created_by=request.user,
                comment=form.cleaned_data['comment']
            )

            messages.success(request, _("تم تغيير حالة الطلب بنجاح"))
            return redirect('applications:application_detail', application_id=application.id)
    else:
        form = ApplicationStatusForm()

    context = {
        'form': form,
        'application': application,
        'statuses': statuses,
    }
    return render(request, 'applications/change_status.html', context)


@login_required
@permission_required('applications.view_application', raise_exception=True)
def admin_applications(request):
    """عرض جميع الطلبات (للمشرفين)"""
    applications = Application.objects.all().order_by('-application_date')
    filter_form = ApplicationFilterForm(request.GET)

    # تطبيق المرشحات
    if filter_form.is_valid():
        data = filter_form.cleaned_data

        if data.get('status'):
            if data['status'] == 'pending':
                applications = applications.filter(status__order=1)
            elif data['status'] == 'review':
                applications = applications.filter(status__order=2)
            elif data['status'] == 'accepted':
                applications = applications.filter(status__name__icontains='مقبول')
            elif data['status'] == 'rejected':
                applications = applications.filter(status__name__icontains='مرفوض')

        if data.get('scholarship'):
            applications = applications.filter(scholarship__title__icontains=data['scholarship'])

        if data.get('date_from'):
            applications = applications.filter(application_date__gte=data['date_from'])

        if data.get('date_to'):
            applications = applications.filter(application_date__lte=data['date_to'])

        if data.get('search'):
            search_query = data['search']
            applications = applications.filter(
                Q(applicant__first_name__icontains=search_query) |
                Q(applicant__last_name__icontains=search_query) |
                Q(scholarship__title__icontains=search_query)
            )

    # ترقيم الصفحات
    paginator = Paginator(applications, 20)  # 20 عنصر في كل صفحة
    page = request.GET.get('page')
    try:
        applications_page = paginator.page(page)
    except PageNotAnInteger:
        applications_page = paginator.page(1)
    except EmptyPage:
        applications_page = paginator.page(paginator.num_pages)

    context = {
        'applications': applications_page,
        'filter_form': filter_form,
    }
    return render(request, 'applications/admin_applications.html', context)


@login_required
@permission_required('applications.delete_application', raise_exception=True)
def delete_application(request, application_id):
    """حذف طلب (للمشرفين)"""
    application = get_object_or_404(Application, id=application_id)

    if request.method == 'POST':
        application.delete()
        messages.success(request, _("تم حذف الطلب بنجاح"))
        return redirect('applications:admin_applications')

    context = {
        'application': application,
    }
    return render(request, 'applications/application_confirm_delete.html', context)


# --- Tabbed Application System Views ---

@login_required
def apply_tabs(request, scholarship_id):
    """التقديم على فرصة ابتعاث بنظام التبويبات"""
    scholarship = get_object_or_404(Scholarship, id=scholarship_id)

    # Get temp application ID from session first
    temp_application_id = request.session.get(f'temp_application_{scholarship_id}')

    # التحقق من أن الفرصة ما زالت متاحة
    if not scholarship.is_active:
        messages.error(request, _("انتهت مهلة التقديم لهذه الفرصة"))
        return redirect('announcements:scholarship_detail', pk=scholarship.id)

    # Check for submitted (non-temporary) applications for this scholarship
    existing_application = Application.objects.filter(
        scholarship=scholarship,
        applicant=request.user,
        status__order__gt=1  # Only consider non-temporary applications
    ).first()

    if existing_application:
        messages.warning(request, _("لقد تقدمت بالفعل لهذه الفرصة"))
        return redirect('applications:application_detail', application_id=existing_application.id)

    # Get or create temporary application
    application = None
    if temp_application_id:
        try:
            application = Application.objects.get(
                id=temp_application_id,
                applicant=request.user,
                scholarship=scholarship
            )
        except Application.DoesNotExist:
            pass

    if not application:
        # Get or create default status for temporary applications
        temp_status = ApplicationStatus.objects.filter(order=0).first()
        if not temp_status:
            temp_status = ApplicationStatus.objects.create(
                name=_("مسودة"),
                order=0,
                description=_("طلب قيد الإنشاء")
            )

        # Create new temporary application
        application = Application(
            scholarship=scholarship,
            applicant=request.user,
            status=temp_status
        )
        application.save()

        # Store application ID in session with scholarship-specific key
        request.session[f'temp_application_{scholarship_id}'] = application.id

    # Get current step from query parameters
    current_step = request.GET.get('step', 'personal')

    # Prepare context
    context = {
        'scholarship': scholarship,
        'application': application,
        'current_step': current_step,
        'is_update': False,
    }

    # Handle each step
    if current_step == 'personal':
        return handle_personal_info_step(request, application, context)
    elif current_step == 'academic':
        return handle_academic_qualifications_step(request, application, context)
    elif current_step == 'language':
        return handle_language_proficiency_step(request, application, context)
    elif current_step == 'documents':
        return handle_documents_step(request, application, context)
    elif current_step == 'preview':
        return handle_preview_step(request, application, context)
    elif current_step == 'submit':
        return handle_submit_step(request, application, context)
    else:
        return handle_personal_info_step(request, application, context)


def handle_personal_info_step(request, application, context):
    """معالجة تبويب المعلومات الأساسية"""
    if request.method == 'POST':
        form = ApplicationTabsForm(request.POST, instance=application)
        if form.is_valid():
            form.save()
            messages.success(request, _("تم حفظ المعلومات الأساسية بنجاح"))
            # Construct the URL with query parameter
            url = f"/ar/apply-tabs/{application.scholarship.id}/?step=academic"
            return redirect(url)
    else:
        form = ApplicationTabsForm(instance=application)

    context.update({
        'form': form,
        'title': _("المعلومات الأساسية"),
    })
    return render(request, 'applications/apply_tabs/personal_info.html', context)


def handle_academic_qualifications_step(request, application, context):
    """معالجة تبويب المؤهلات الأكاديمية"""
    if request.method == 'POST':
        # تحديد التبويب الفرعي النشط (نوع المؤهل)
        active_tab = request.POST.get('qualification_type', 'high_school')
        # استخدام حقل للبقاء في نفس التبويب
        stay_in_tab = request.POST.get('stay_in_tab')

        if active_tab == 'high_school':
            formset = HighSchoolQualificationFormSet(request.POST, instance=application, prefix='high_school')
        elif active_tab == 'bachelors':
            formset = BachelorQualificationFormSet(request.POST, instance=application, prefix='bachelors')
        elif active_tab == 'masters':
            formset = MasterQualificationFormSet(request.POST, instance=application, prefix='masters')
        else:  # 'other'
            formset = OtherCertificateFormSet(request.POST, instance=application, prefix='other')

        if formset.is_valid():
            # حفظ البيانات
            instances = formset.save(commit=False)
            for instance in instances:
                instance.save()

            # حفظ علاقات M2M إذا وجدت
            formset.save_m2m()

            # حذف المؤهلات المحددة للحذف
            for obj in formset.deleted_objects:
                obj.delete()

            messages.success(request, _("تم حفظ المؤهلات الأكاديمية بنجاح"))

            # البقاء في نفس التبويب بعد الحفظ
            if stay_in_tab:
                redirect_url = f"{reverse('applications:apply_tabs', args=[application.scholarship.id])}?step=academic&qualification_type={stay_in_tab}"
                return redirect(redirect_url)

            # الانتقال للخطوة التالية إذا لم يكن هناك إشارة للبقاء
            return redirect(f"{reverse('applications:apply_tabs', args=[application.scholarship.id])}?step=language")
        else:
            # عرض رسائل الخطأ للمستخدم
            for form in formset:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
    else:
        # تحديد التبويب النشط (نوع المؤهل) من الطلب
        active_tab = request.GET.get('qualification_type', 'high_school')

    # تحضير جميع النماذج
    high_school_formset = HighSchoolQualificationFormSet(instance=application, prefix='high_school')
    bachelor_formset = BachelorQualificationFormSet(instance=application, prefix='bachelors')
    master_formset = MasterQualificationFormSet(instance=application, prefix='masters')
    other_certificate_formset = OtherCertificateFormSet(instance=application, prefix='other')

    # تقييد الثانوية العامة والبكالوريوس والماجستير لعرض نموذج واحد فقط
    if high_school_formset.forms:
        high_school_formset.extra = 0 if application.high_school_qualifications.exists() else 1
    if bachelor_formset.forms:
        bachelor_formset.extra = 0 if application.bachelor_qualifications.exists() else 1
    if master_formset.forms:
        master_formset.extra = 0 if application.master_qualifications.exists() else 1

    # إحصاءات عن المؤهلات الموجودة
    qualifications_stats = {
        'high_school': application.high_school_qualifications.count(),
        'bachelors': application.bachelor_qualifications.count(),
        'masters': application.master_qualifications.count(),
        'other': application.other_certificates.count(),
    }

    context.update({
        'high_school_formset': high_school_formset,
        'bachelor_formset': bachelor_formset,
        'master_formset': master_formset,
        'other_certificate_formset': other_certificate_formset,
        'active_tab': active_tab,
        'qualifications_stats': qualifications_stats,
        'title': _("المؤهلات الأكاديمية"),
    })

    return render(request, 'applications/apply_tabs/academic_qualifications.html', context)


def handle_language_proficiency_step(request, application, context):
    """معالجة تبويب الكفاءة اللغوية"""
    if request.method == 'POST':
        formset = LanguageProficiencyFormSet(request.POST, instance=application)
        if formset.is_valid():
            formset.save()
            messages.success(request, _("تم حفظ معلومات الكفاءة اللغوية بنجاح"))
            return redirect(f"{reverse('applications:apply_tabs', args=[application.scholarship.id])}?step=documents")
    else:
        formset = LanguageProficiencyFormSet(instance=application)

    context.update({
        'formset': formset,
        'title': _("الكفاءة اللغوية"),
    })
    return render(request, 'applications/apply_tabs/language_proficiency.html', context)


def handle_documents_step(request, application, context):
    """معالجة تبويب المستندات بطريقة مبسطة"""
    if request.method == 'POST' and request.POST.get('action') == 'upload_document':
        # رفع مستند واحد فقط
        document_type = request.POST.get('document_type')
        file = request.FILES.get('file')

        if document_type and file:
            # الحصول على العرض المقابل لنوع المستند
            document_types_dict = dict(Document.DOCUMENT_TYPE_CHOICES)
            document_type_display = document_types_dict.get(document_type, document_type)

            # إنشاء مستند جديد
            document = Document(
                application=application,
                document_type=document_type,
                name=document_type_display,
                file=file,
                # تحديد ما إذا كان المستند مطلوبًا بناءً على نوع المستند
                is_required=document_type in ['cv', 'personal_id', 'high_school_certificate', 'bachelors_certificate', 'language_certificate']
            )
            document.save()

            messages.success(request, _("تم رفع المستند بنجاح"))
            return redirect(request.path_info + "?step=documents")
        else:
            messages.error(request, _("يرجى اختيار نوع المستند وتحميل الملف"))

    # استخراج أنواع المستندات الموجودة للتحقق من المستندات المطلوبة
    document_types = list(Document.objects.filter(application=application).values_list('document_type', flat=True))

    context.update({
        'title': _("المستندات المطلوبة"),
        'document_types': document_types,
    })

    return render(request, 'applications/apply_tabs/documents.html', context)


def handle_preview_step(request, application, context):
    """معالجة تبويب المعاينة"""
    # الحصول على المؤهلات الأكاديمية المختلفة
    high_school_qualifications = application.high_school_qualifications.all()
    bachelor_qualifications = application.bachelor_qualifications.all()
    master_qualifications = application.master_qualifications.all()
    other_certificates = application.other_certificates.all()

    language_proficiencies = LanguageProficiency.objects.filter(application=application)
    documents = Document.objects.filter(application=application)

    context.update({
        'high_school_qualifications': high_school_qualifications,
        'bachelor_qualifications': bachelor_qualifications,
        'master_qualifications': master_qualifications,
        'other_certificates': other_certificates,
        'language_proficiencies': language_proficiencies,
        'documents': documents,
        'title': _("معاينة الطلب"),
    })
    return render(request, 'applications/apply_tabs/preview.html', context)


def handle_submit_step(request, application, context):
    """معالجة تبويب التقديم النهائي"""
    # التحقق من اكتمال الطلب
    is_complete = True
    missing_fields = []

    # 1. التحقق من وجود معلومات شخصية
    if not application.motivation_letter:
        is_complete = False
        missing_fields.append(_("خطاب الدوافع"))

    # 2. التحقق من وجود مؤهلات أكاديمية مطلوبة
    # التحقق من وجود شهادة الثانوية العامة
    if not application.high_school_qualifications.exists():
        is_complete = False
        missing_fields.append(_("مؤهل الثانوية العامة"))

    # التحقق من وجود شهادة البكالوريوس
    if not application.bachelor_qualifications.exists():
        is_complete = False
        missing_fields.append(_("مؤهل البكالوريوس"))

    # 3. التحقق من وجود كفاءة لغوية في اللغة الإنجليزية
    if not LanguageProficiency.objects.filter(application=application, is_english=True).exists():
        is_complete = False
        missing_fields.append(_("الكفاءة اللغوية في اللغة الإنجليزية"))

    # 4. التحقق من وجود المستندات المطلوبة
    required_document_types = [
        'cv',
        'personal_id',
        'high_school_certificate',
        'bachelors_certificate'
    ]
    existing_document_types = Document.objects.filter(application=application).values_list('document_type', flat=True)

    for doc_type in required_document_types:
        if doc_type not in existing_document_types:
            is_complete = False
            doc_type_display = dict(Document.DOCUMENT_TYPE_CHOICES).get(doc_type, doc_type)
            missing_fields.append(doc_type_display)

    # 5. إذا كان الطلب كاملا ويتم النقر على زر التقديم
    if request.method == 'POST' and is_complete:
        # الحصول على حالة "تم التقديم" (order=1)
        submitted_status = ApplicationStatus.objects.filter(order=1).first()
        if not submitted_status:
            submitted_status = ApplicationStatus.objects.create(
                name=_("تم التقديم"),
                order=1,
                description=_("تم تقديم الطلب")
            )

        # تحديث حالة الطلب من مؤقتة إلى مقدمة
        old_status = application.status
        application.status = submitted_status
        application.application_date = timezone.now()
        application.save()

        # إنشاء سجل للطلب
        ApplicationLog.objects.create(
            application=application,
            from_status=old_status,
            to_status=submitted_status,
            created_by=request.user,
            comment=_("تم تقديم الطلب")
        )

        # إزالة معرف الطلب المؤقت من الجلسة
        scholarship_id = application.scholarship.id
        if f'temp_application_{scholarship_id}' in request.session:
            del request.session[f'temp_application_{scholarship_id}']

        messages.success(request, _("تم تقديم طلبك بنجاح"))
        return redirect('applications:application_detail', application_id=application.id)

    # إعداد سياق العرض
    context.update({
        'is_complete': is_complete,
        'missing_fields': missing_fields,
        'title': _("تقديم الطلب"),
    })

    # عرض ملخص الطلب
    high_school_qualifications = application.high_school_qualifications.all()
    bachelor_qualifications = application.bachelor_qualifications.all()
    master_qualifications = application.master_qualifications.all()
    other_certificates = application.other_certificates.all()
    language_proficiencies = LanguageProficiency.objects.filter(application=application)
    documents = Document.objects.filter(application=application)

    context.update({
        'high_school_qualifications': high_school_qualifications,
        'bachelor_qualifications': bachelor_qualifications,
        'master_qualifications': master_qualifications,
        'other_certificates': other_certificates,
        'language_proficiencies': language_proficiencies,
        'documents': documents,
    })

    return render(request, 'applications/apply_tabs/submit.html', context)


@login_required
def update_application_tabs(request, application_id):
    """تحديث الطلب بنظام التبويبات"""
    application = get_object_or_404(Application, id=application_id, applicant=request.user)

    # التحقق من أن الطلب ما زال قابل للتعديل
    if application.status.order > 2:  # إذا تجاوزت الحالة مرحلة المراجعة الأولية
        messages.error(request, _("لا يمكن تعديل هذا الطلب في مرحلته الحالية"))
        return redirect('applications:application_detail', application_id=application.id)

    # الخطوة الحالية من الطلب
    current_step = request.GET.get('step', 'personal')

    context = {
        'scholarship': application.scholarship,
        'application': application,
        'current_step': current_step,
        'is_update': True,
    }

    # معالجة كل خطوة من خطوات الطلب
    if current_step == 'personal':
        return handle_personal_info_step(request, application, context)
    elif current_step == 'academic':
        return handle_academic_qualifications_step(request, application, context)
    elif current_step == 'language':
        return handle_language_proficiency_step(request, application, context)
    elif current_step == 'documents':
        return handle_documents_step(request, application, context)
    elif current_step == 'preview':
        return handle_preview_step(request, application, context)
    elif current_step == 'submit':
        return handle_update_submit_step(request, application, context)
    else:
        return handle_personal_info_step(request, application, context)


def handle_update_submit_step(request, application, context):
    """معالجة تبويب تحديث الطلب النهائي"""
    # التحقق من اكتمال الطلب (نفس المنطق كما في handle_submit_step)
    is_complete = True
    missing_fields = []

    # التحقق من وجود معلومات شخصية
    if not application.motivation_letter:
        is_complete = False
        missing_fields.append(_("خطاب الدوافع"))

    # التحقق من وجود مؤهلات أكاديمية مطلوبة
    if not application.high_school_qualifications.exists():
        is_complete = False
        missing_fields.append(_("مؤهل الثانوية العامة"))

    if not application.bachelor_qualifications.exists():
        is_complete = False
        missing_fields.append(_("مؤهل البكالوريوس"))

    # التحقق من وجود كفاءة لغوية في اللغة الإنجليزية
    if not LanguageProficiency.objects.filter(application=application, is_english=True).exists():
        is_complete = False
        missing_fields.append(_("الكفاءة اللغوية في اللغة الإنجليزية"))

    # التحقق من وجود المستندات المطلوبة
    required_document_types = [
        'cv',
        'personal_id',
        'high_school_certificate',
        'bachelors_certificate'
    ]
    existing_document_types = Document.objects.filter(application=application).values_list('document_type', flat=True)

    for doc_type in required_document_types:
        if doc_type not in existing_document_types:
            is_complete = False
            doc_type_display = dict(Document.DOCUMENT_TYPE_CHOICES).get(doc_type, doc_type)
            missing_fields.append(doc_type_display)

    if request.method == 'POST' and is_complete:
        # تحديث الطلب
        application.last_update = timezone.now()
        application.save()

        # إنشاء سجل للتحديث
        ApplicationLog.objects.create(
            application=application,
            from_status=application.status,
            to_status=application.status,
            created_by=request.user,
            comment=_("تم تحديث الطلب")
        )

        messages.success(request, _("تم تحديث طلبك بنجاح"))
        return redirect('applications:application_detail', application_id=application.id)

    # إعداد سياق العرض لمعاينة الطلب
    high_school_qualifications = application.high_school_qualifications.all()
    bachelor_qualifications = application.bachelor_qualifications.all()
    master_qualifications = application.master_qualifications.all()
    other_certificates = application.other_certificates.all()
    language_proficiencies = LanguageProficiency.objects.filter(application=application)
    documents = Document.objects.filter(application=application)

    context.update({
        'is_complete': is_complete,
        'missing_fields': missing_fields,
        'high_school_qualifications': high_school_qualifications,
        'bachelor_qualifications': bachelor_qualifications,
        'master_qualifications': master_qualifications,
        'other_certificates': other_certificates,
        'language_proficiencies': language_proficiencies,
        'documents': documents,
        'title': _("تحديث الطلب"),
    })

    return render(request, 'applications/apply_tabs/submit.html', context)


@login_required
@permission_required('applications.view_application')
def department_council_report(request):
    """تقرير الطلبات الموافق عليها من مجلس القسم"""
    # الحصول على الطلبات الموافق عليها من مجلس القسم (حالة رقم 6)
    applications = Application.objects.filter(status__order=6).order_by('-application_date')

    # تحميل المرفقات للطلبات
    for application in applications:
        application.higher_committee_attachment = ApprovalAttachment.objects.filter(
            application=application,
            approval_type='higher_committee'
        ).first()

        application.department_council_attachment = ApprovalAttachment.objects.filter(
            application=application,
            approval_type='department_council'
        ).first()

    context = {
        'applications': applications,
        'title': _("تقرير الطلبات الموافق عليها من مجلس القسم"),
        'date': timezone.now()
    }

    # تحديد ما إذا كان التقرير للعرض أو للطباعة
    if request.GET.get('print') == 'true':
        # إنشاء ملف PDF
        html_string = render_to_string('applications/reports/department_council_report_pdf.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'filename="department_council_report.pdf"'

        # استخدام weasyprint لتحويل HTML إلى PDF
        pdf = weasyprint.HTML(string=html_string).write_pdf()
        response.write(pdf)
        return response

    return render(request, 'applications/reports/department_council_report.html', context)


@login_required
@permission_required('applications.view_application')
def deans_council_report(request):
    """تقرير الطلبات الموافق عليها من مجلس العمداء"""
    # الحصول على الطلبات الموافق عليها من مجلس العمداء (حالة رقم 10)
    applications = Application.objects.filter(status__order=10).order_by('-application_date')

    # تحميل المرفقات للطلبات
    for application in applications:
        application.higher_committee_attachment = ApprovalAttachment.objects.filter(
            application=application,
            approval_type='higher_committee'
        ).first()

        application.department_council_attachment = ApprovalAttachment.objects.filter(
            application=application,
            approval_type='department_council'
        ).first()

        application.faculty_council_attachment = ApprovalAttachment.objects.filter(
            application=application,
            approval_type='faculty_council'
        ).first()

        application.deans_council_attachment = ApprovalAttachment.objects.filter(
            application=application,
            approval_type='deans_council'
        ).first()

    context = {
        'applications': applications,
        'title': _("تقرير الطلبات الموافق عليها من مجلس العمداء"),
        'date': timezone.now()
    }

    # تحديد ما إذا كان التقرير للعرض أو للطباعة
    if request.GET.get('print') == 'true':
        # إنشاء ملف PDF
        html_string = render_to_string('applications/reports/deans_council_report_pdf.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'filename="deans_council_report.pdf"'

        # استخدام weasyprint لتحويل HTML إلى PDF
        pdf = weasyprint.HTML(string=html_string).write_pdf()
        response.write(pdf)
        return response

    return render(request, 'applications/reports/deans_council_report.html', context)