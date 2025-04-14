from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.utils import timezone
from announcements.models import Scholarship
from .models import Application, Document, ApplicationStatus, ApplicationLog
from .forms import ApplicationForm, DocumentForm, DocumentUploadForm, ApplicationStatusForm, ApplicationFilterForm

@login_required
def apply(request, scholarship_id):
    """التقديم على فرصة ابتعاث"""
    scholarship = get_object_or_404(Scholarship, id=scholarship_id)

    # التحقق من أن الفرصة ما زالت متاحة
    if not scholarship.is_active:
        messages.error(request, _("انتهت مهلة التقديم لهذه الفرصة"))
        return redirect('announcements:scholarship_detail', pk=scholarship.id)

    # التحقق من أن المستخدم لم يتقدم مسبقًا
    if Application.objects.filter(scholarship=scholarship, applicant=request.user).exists():
        messages.warning(request, _("لقد تقدمت بالفعل لهذه الفرصة"))
        return redirect('applications:my_applications')

    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.scholarship = scholarship
            application.applicant = request.user

            # تعيين حالة الطلب الافتراضية
            default_status = ApplicationStatus.objects.filter(order=1).first()
            if not default_status:
                default_status = ApplicationStatus.objects.create(name=_("قيد الانتظار"), order=1)
            application.status = default_status

            application.save()

            # إنشاء سجل للطلب
            ApplicationLog.objects.create(
                application=application,
                to_status=default_status,
                created_by=request.user,
                comment=_("تم إنشاء الطلب")
            )

            messages.success(request, _("تم تقديم طلبك بنجاح"))
            return redirect('applications:application_documents', application_id=application.id)
    else:
        form = ApplicationForm()

    context = {
        'form': form,
        'scholarship': scholarship,
    }
    return render(request, 'applications/application_form.html', context)

@login_required
def application_documents(request, application_id):
    """إدارة مستندات الطلب"""
    application = get_object_or_404(Application, id=application_id, applicant=request.user)

    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document_type = form.cleaned_data['document_type']
            description = form.cleaned_data['description']
            file = form.cleaned_data['file']

            # استخراج نوع المستند من الخيارات
            document_type_display = dict(form.fields['document_type'].choices)[document_type]

            # إنشاء المستند
            Document.objects.create(
                application=application,
                name=document_type_display,
                description=description,
                file=file,
                is_required=True if document_type in ['cv', 'transcript', 'certificate'] else False
            )

            messages.success(request, _("تم رفع المستند بنجاح"))
            return redirect('applications:application_documents', application_id=application.id)
    else:
        form = DocumentUploadForm()

    documents = Document.objects.filter(application=application)

    context = {
        'form': form,
        'application': application,
        'documents': documents,
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

    documents = Document.objects.filter(application=application)
    logs = ApplicationLog.objects.filter(application=application).order_by('-created_at')

    context = {
        'application': application,
        'documents': documents,
        'logs': logs,
    }
    return render(request, 'applications/application_detail.html', context)

@login_required
def update_application(request, application_id):
    """تحديث معلومات الطلب"""
    application = get_object_or_404(Application, id=application_id, applicant=request.user)

    # التحقق من أن الطلب ما زال قابل للتعديل
    if application.status.order > 2:  # إذا تجاوزت الحالة مرحلة المراجعة الأولية
        messages.error(request, _("لا يمكن تعديل هذا الطلب في مرحلته الحالية"))
        return redirect('applications:application_detail', application_id=application.id)

    if request.method == 'POST':
        form = ApplicationForm(request.POST, instance=application)
        if form.is_valid():
            form.save()
            messages.success(request, _("تم تحديث معلومات الطلب بنجاح"))
            return redirect('applications:application_detail', application_id=application.id)
    else:
        form = ApplicationForm(instance=application)

    context = {
        'form': form,
        'application': application,
        'is_update': True,
    }
    return render(request, 'applications/application_form.html', context)

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