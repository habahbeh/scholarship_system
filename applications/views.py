# في ملف applications/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.core.paginator import Paginator

from .models import Application, ApplicationStatus, ApprovalAttachment
from .forms import (
    RequirementsCheckForm, HigherCommitteeApprovalForm,
    FacultyCouncilApprovalForm, PresidentApprovalForm
)


from django.http import HttpResponse
from django.template.loader import render_to_string
import weasyprint
from django.conf import settings
import os



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
@permission_required('applications.change_application')
def check_requirements(request, application_id):
    """مطابقة الشروط للطلب"""
    application = get_object_or_404(Application, pk=application_id)

    # التحقق من أن الطلب في حالة تسمح بمطابقة الشروط
    if application.status.order > 2:
        messages.error(request, _("لا يمكن مطابقة الشروط لهذا الطلب في حالته الحالية"))
        return redirect('applications:admin_applications_list')

    if request.method == 'POST':
        form = RequirementsCheckForm(request.POST)
        if form.is_valid():
            meets_requirements = form.cleaned_data['meets_requirements']
            notes = form.cleaned_data['notes']

            # تحديث حالة الطلب
            if meets_requirements == 'yes':
                # البحث عن حالة "مطابق للشروط"
                status = ApplicationStatus.objects.get(order=3)
            else:
                # البحث عن حالة "غير مطابق للشروط"
                status = ApplicationStatus.objects.get(order=4)

            application.status = status
            application.admin_notes = notes
            application.save()

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
@permission_required('applications.change_application')
def higher_committee_approval(request, application_id):
    """موافقة اللجنة العليا"""
    application = get_object_or_404(Application, pk=application_id)

    # التحقق من أن الطلب مطابق للشروط
    if application.status.order != 3:
        messages.error(request, _("لا يمكن تقديم موافقة اللجنة العليا لهذا الطلب في حالته الحالية"))
        return redirect('applications:admin_applications_list')

    if request.method == 'POST':
        form = HigherCommitteeApprovalForm(request.POST, request.FILES)
        if form.is_valid():
            is_approved = form.cleaned_data['is_approved']
            notes = form.cleaned_data['notes']

            # تحديث حالة الطلب
            if is_approved == 'yes':
                # البحث عن حالة "موافق من اللجنة العليا"
                status = ApplicationStatus.objects.get(order=5)

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
                # البحث عن حالة "غير موافق من اللجنة العليا"
                status = ApplicationStatus.objects.get(order=6)

            application.status = status
            application.save()

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
@permission_required('applications.change_application')
def faculty_council_approval(request, application_id):
    """موافقة مجلس الكلية"""
    application = get_object_or_404(Application, pk=application_id)

    # التحقق من أن الطلب موافق من اللجنة العليا
    if application.status.order != 5:
        messages.error(request, _("لا يمكن تقديم موافقة مجلس الكلية لهذا الطلب في حالته الحالية"))
        return redirect('applications:admin_applications_list')

    if request.method == 'POST':
        form = FacultyCouncilApprovalForm(request.POST, request.FILES)
        if form.is_valid():
            is_approved = form.cleaned_data['is_approved']
            notes = form.cleaned_data['notes']

            # تحديث حالة الطلب
            if is_approved == 'yes':
                # البحث عن حالة "موافق من مجلس الكلية"
                status = ApplicationStatus.objects.get(order=7)

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
                # البحث عن حالة "غير موافق من مجلس الكلية"
                status = ApplicationStatus.objects.get(order=8)

            application.status = status
            application.save()

            messages.success(request, _("تم تحديث حالة الطلب بنجاح"))
            return redirect('applications:admin_applications_list')
    else:
        # تهيئة النموذج
        form = FacultyCouncilApprovalForm()

    context = {
        'form': form,
        'application': application,
    }
    return render(request, 'applications/faculty_council_approval.html', context)

@login_required
@permission_required('applications.change_application')
def president_approval(request, application_id):
    """موافقة رئيس الجامعة"""
    application = get_object_or_404(Application, pk=application_id)

    # التحقق من أن الطلب موافق من مجلس الكلية
    if application.status.order != 7:
        messages.error(request, _("لا يمكن تقديم موافقة رئيس الجامعة لهذا الطلب في حالته الحالية"))
        return redirect('applications:admin_applications_list')

    if request.method == 'POST':
        form = PresidentApprovalForm(request.POST, request.FILES)
        if form.is_valid():
            is_approved = form.cleaned_data['is_approved']
            notes = form.cleaned_data['notes']

            # تحديث حالة الطلب
            if is_approved == 'yes':
                # البحث عن حالة "موافق من رئيس الجامعة"
                status = ApplicationStatus.objects.get(order=9)

                # حفظ مرفق الموافقة
                attachment = form.cleaned_data['attachment']
                if attachment:
                    approval_attachment = ApprovalAttachment(
                        application=application,
                        approval_type='president',
                        attachment=attachment,
                        notes=notes
                    )
                    approval_attachment.save()
            else:
                # البحث عن حالة "غير موافق من رئيس الجامعة"
                status = ApplicationStatus.objects.get(order=10)

            application.status = status
            application.save()

            messages.success(request, _("تم تحديث حالة الطلب بنجاح"))
            return redirect('applications:admin_applications_list')
    else:
        # تهيئة النموذج
        form = PresidentApprovalForm()

    context = {
        'form': form,
        'application': application,
    }
    return render(request, 'applications/president_approval.html', context)

@login_required
@permission_required('applications.view_application')
def requirements_report(request):
    """تقرير الطلبات المطابقة للشروط"""
    # الحصول على الطلبات المطابقة للشروط (حالة رقم 3)
    applications = Application.objects.filter(status__order=3).order_by('-application_date')

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
    # الحصول على الطلبات الموافق عليها من اللجنة العليا (حالة رقم 5)
    applications = Application.objects.filter(status__order=5).order_by('-application_date')

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
    # الحصول على الطلبات الموافق عليها من مجلس الكلية (حالة رقم 7)
    applications = Application.objects.filter(status__order=7).order_by('-application_date')

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

    # تحميل المرفقات للطلب
    attachments = ApprovalAttachment.objects.filter(application=application)

    context = {
        'application': application,
        'attachments': attachments,
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

# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.decorators import login_required, permission_required
# from django.contrib import messages
# from django.utils.translation import gettext_lazy as _
# from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# from django.db.models import Q
# from django.utils import timezone
# from announcements.models import Scholarship
# from .models import Application, Document, ApplicationStatus, ApplicationLog
# from .forms import ApplicationForm, DocumentForm, DocumentUploadForm, ApplicationStatusForm, ApplicationFilterForm
#
# @login_required
# def apply(request, scholarship_id):
#     """التقديم على فرصة ابتعاث"""
#     scholarship = get_object_or_404(Scholarship, id=scholarship_id)
#
#     # التحقق من أن الفرصة ما زالت متاحة
#     if not scholarship.is_active:
#         messages.error(request, _("انتهت مهلة التقديم لهذه الفرصة"))
#         return redirect('announcements:scholarship_detail', pk=scholarship.id)
#
#     # التحقق من أن المستخدم لم يتقدم مسبقًا
#     if Application.objects.filter(scholarship=scholarship, applicant=request.user).exists():
#         messages.warning(request, _("لقد تقدمت بالفعل لهذه الفرصة"))
#         return redirect('applications:my_applications')
#
#     if request.method == 'POST':
#         form = ApplicationForm(request.POST)
#         if form.is_valid():
#             application = form.save(commit=False)
#             application.scholarship = scholarship
#             application.applicant = request.user
#
#             # تعيين حالة الطلب الافتراضية
#             default_status = ApplicationStatus.objects.filter(order=1).first()
#             if not default_status:
#                 default_status = ApplicationStatus.objects.create(name=_("قيد الانتظار"), order=1)
#             application.status = default_status
#
#             application.save()
#
#             # إنشاء سجل للطلب
#             ApplicationLog.objects.create(
#                 application=application,
#                 to_status=default_status,
#                 created_by=request.user,
#                 comment=_("تم إنشاء الطلب")
#             )
#
#             messages.success(request, _("تم تقديم طلبك بنجاح"))
#             return redirect('applications:application_documents', application_id=application.id)
#     else:
#         form = ApplicationForm()
#
#     context = {
#         'form': form,
#         'scholarship': scholarship,
#     }
#     return render(request, 'applications/application_form.html', context)
#
# @login_required
# def application_documents(request, application_id):
#     """إدارة مستندات الطلب"""
#     application = get_object_or_404(Application, id=application_id, applicant=request.user)
#
#     if request.method == 'POST':
#         form = DocumentUploadForm(request.POST, request.FILES)
#         if form.is_valid():
#             document_type = form.cleaned_data['document_type']
#             description = form.cleaned_data['description']
#             file = form.cleaned_data['file']
#
#             # استخراج نوع المستند من الخيارات
#             document_type_display = dict(form.fields['document_type'].choices)[document_type]
#
#             # إنشاء المستند
#             Document.objects.create(
#                 application=application,
#                 name=document_type_display,
#                 description=description,
#                 file=file,
#                 is_required=True if document_type in ['cv', 'transcript', 'certificate'] else False
#             )
#
#             messages.success(request, _("تم رفع المستند بنجاح"))
#             return redirect('applications:application_documents', application_id=application.id)
#     else:
#         form = DocumentUploadForm()
#
#     documents = Document.objects.filter(application=application)
#
#     context = {
#         'form': form,
#         'application': application,
#         'documents': documents,
#     }
#     return render(request, 'applications/application_documents.html', context)
#
# @login_required
# def delete_document(request, document_id):
#     """حذف مستند"""
#     document = get_object_or_404(Document, id=document_id)
#     application = document.application
#
#     # التحقق من أن المستخدم هو صاحب الطلب
#     if application.applicant != request.user:
#         messages.error(request, _("ليس لديك صلاحية حذف هذا المستند"))
#         return redirect('applications:my_applications')
#
#     if request.method == 'POST':
#         document.delete()
#         messages.success(request, _("تم حذف المستند بنجاح"))
#         return redirect('applications:application_documents', application_id=application.id)
#
#     context = {
#         'document': document,
#         'application': application,
#     }
#     return render(request, 'applications/document_confirm_delete.html', context)
#
# @login_required
# def my_applications(request):
#     """عرض طلبات المستخدم"""
#     applications = Application.objects.filter(applicant=request.user).order_by('-application_date')
#
#     # ترقيم الصفحات
#     paginator = Paginator(applications, 10)  # 10 عناصر في كل صفحة
#     page = request.GET.get('page')
#     try:
#         applications_page = paginator.page(page)
#     except PageNotAnInteger:
#         applications_page = paginator.page(1)
#     except EmptyPage:
#         applications_page = paginator.page(paginator.num_pages)
#
#     context = {
#         'applications': applications_page,
#     }
#     return render(request, 'applications/my_applications.html', context)
#
# @login_required
# def application_detail(request, application_id):
#     """عرض تفاصيل الطلب"""
#     # يمكن للمستخدم عرض طلبه فقط، أو للمستخدمين ذوي الصلاحيات عرض أي طلب
#     if request.user.has_perm('applications.view_application'):
#         application = get_object_or_404(Application, id=application_id)
#     else:
#         application = get_object_or_404(Application, id=application_id, applicant=request.user)
#
#     documents = Document.objects.filter(application=application)
#     logs = ApplicationLog.objects.filter(application=application).order_by('-created_at')
#
#     context = {
#         'application': application,
#         'documents': documents,
#         'logs': logs,
#     }
#     return render(request, 'applications/application_detail.html', context)
#
# @login_required
# def update_application(request, application_id):
#     """تحديث معلومات الطلب"""
#     application = get_object_or_404(Application, id=application_id, applicant=request.user)
#
#     # التحقق من أن الطلب ما زال قابل للتعديل
#     if application.status.order > 2:  # إذا تجاوزت الحالة مرحلة المراجعة الأولية
#         messages.error(request, _("لا يمكن تعديل هذا الطلب في مرحلته الحالية"))
#         return redirect('applications:application_detail', application_id=application.id)
#
#     if request.method == 'POST':
#         form = ApplicationForm(request.POST, instance=application)
#         if form.is_valid():
#             form.save()
#             messages.success(request, _("تم تحديث معلومات الطلب بنجاح"))
#             return redirect('applications:application_detail', application_id=application.id)
#     else:
#         form = ApplicationForm(instance=application)
#
#     context = {
#         'form': form,
#         'application': application,
#         'is_update': True,
#     }
#     return render(request, 'applications/application_form.html', context)
#
# @login_required
# @permission_required('applications.change_application', raise_exception=True)
# def change_status(request, application_id):
#     """تغيير حالة الطلب (للمشرفين)"""
#     application = get_object_or_404(Application, id=application_id)
#     statuses = ApplicationStatus.objects.exclude(id=application.status.id).order_by('order')
#
#     if request.method == 'POST':
#         status_id = request.POST.get('status')
#         form = ApplicationStatusForm(request.POST)
#
#         if form.is_valid() and status_id:
#             new_status = get_object_or_404(ApplicationStatus, id=status_id)
#             old_status = application.status
#
#             # تحديث حالة الطلب
#             application.status = new_status
#             application.save()
#
#             # إنشاء سجل للتغيير
#             ApplicationLog.objects.create(
#                 application=application,
#                 from_status=old_status,
#                 to_status=new_status,
#                 created_by=request.user,
#                 comment=form.cleaned_data['comment']
#             )
#
#             messages.success(request, _("تم تغيير حالة الطلب بنجاح"))
#             return redirect('applications:application_detail', application_id=application.id)
#     else:
#         form = ApplicationStatusForm()
#
#     context = {
#         'form': form,
#         'application': application,
#         'statuses': statuses,
#     }
#     return render(request, 'applications/change_status.html', context)
#
# @login_required
# @permission_required('applications.view_application', raise_exception=True)
# def admin_applications(request):
#     """عرض جميع الطلبات (للمشرفين)"""
#     applications = Application.objects.all().order_by('-application_date')
#     filter_form = ApplicationFilterForm(request.GET)
#
#     # تطبيق المرشحات
#     if filter_form.is_valid():
#         data = filter_form.cleaned_data
#
#         if data.get('status'):
#             if data['status'] == 'pending':
#                 applications = applications.filter(status__order=1)
#             elif data['status'] == 'review':
#                 applications = applications.filter(status__order=2)
#             elif data['status'] == 'accepted':
#                 applications = applications.filter(status__name__icontains='مقبول')
#             elif data['status'] == 'rejected':
#                 applications = applications.filter(status__name__icontains='مرفوض')
#
#         if data.get('scholarship'):
#             applications = applications.filter(scholarship__title__icontains=data['scholarship'])
#
#         if data.get('date_from'):
#             applications = applications.filter(application_date__gte=data['date_from'])
#
#         if data.get('date_to'):
#             applications = applications.filter(application_date__lte=data['date_to'])
#
#         if data.get('search'):
#             search_query = data['search']
#             applications = applications.filter(
#                 Q(applicant__first_name__icontains=search_query) |
#                 Q(applicant__last_name__icontains=search_query) |
#                 Q(scholarship__title__icontains=search_query)
#             )
#
#     # ترقيم الصفحات
#     paginator = Paginator(applications, 20)  # 20 عنصر في كل صفحة
#     page = request.GET.get('page')
#     try:
#         applications_page = paginator.page(page)
#     except PageNotAnInteger:
#         applications_page = paginator.page(1)
#     except EmptyPage:
#         applications_page = paginator.page(paginator.num_pages)
#
#     context = {
#         'applications': applications_page,
#         'filter_form': filter_form,
#     }
#     return render(request, 'applications/admin_applications.html', context)
#
# @login_required
# @permission_required('applications.delete_application', raise_exception=True)
# def delete_application(request, application_id):
#     """حذف طلب (للمشرفين)"""
#     application = get_object_or_404(Application, id=application_id)
#
#     if request.method == 'POST':
#         application.delete()
#         messages.success(request, _("تم حذف الطلب بنجاح"))
#         return redirect('applications:admin_applications')
#
#     context = {
#         'application': application,
#     }
#     return render(request, 'applications/application_confirm_delete.html', context)