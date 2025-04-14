from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.utils import timezone
from .models import Scholarship, Announcement, ScholarshipType
from .forms import ScholarshipForm, AnnouncementForm, ScholarshipTypeForm, ScholarshipFilterForm

def scholarship_list(request):
    """عرض قائمة فرص الابتعاث مع إمكانية التصفية والبحث"""
    scholarships = Scholarship.objects.filter(status='published')
    filter_form = ScholarshipFilterForm(request.GET)

    # تطبيق المرشحات
    if filter_form.is_valid():
        data = filter_form.cleaned_data

        if data.get('scholarship_type'):
            scholarships = scholarships.filter(scholarship_type=data['scholarship_type'])

        if data.get('status') == 'active':
            scholarships = scholarships.filter(deadline__gt=timezone.now())
        elif data.get('status') == 'closed':
            scholarships = scholarships.filter(deadline__lte=timezone.now())

        if data.get('country'):
            scholarships = scholarships.filter(countries__icontains=data['country'])

        if data.get('search'):
            search_query = data['search']
            scholarships = scholarships.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(requirements__icontains=search_query)
            )

        # الترتيب
        sort_by = data.get('sort_by', 'newest')
        if sort_by == 'newest':
            scholarships = scholarships.order_by('-publication_date')
        elif sort_by == 'deadline':
            scholarships = scholarships.order_by('deadline')
        elif sort_by == 'title':
            scholarships = scholarships.order_by('title')

    # ترقيم الصفحات
    paginator = Paginator(scholarships, 9)  # 9 عناصر في كل صفحة
    page = request.GET.get('page')
    try:
        scholarships_page = paginator.page(page)
    except PageNotAnInteger:
        scholarships_page = paginator.page(1)
    except EmptyPage:
        scholarships_page = paginator.page(paginator.num_pages)

    context = {
        'scholarships': scholarships_page,
        'filter_form': filter_form,
    }
    return render(request, 'announcements/scholarship_list.html', context)

def scholarship_detail(request, pk):
    """عرض تفاصيل فرصة ابتعاث معينة"""
    scholarship = get_object_or_404(Scholarship, pk=pk)

    # التحقق ما إذا كان المستخدم قد تقدم بالفعل لهذه الفرصة
    has_applied = False
    if request.user.is_authenticated:
        has_applied = scholarship.applications.filter(applicant=request.user).exists()

    context = {
        'scholarship': scholarship,
        'has_applied': has_applied,
    }
    return render(request, 'announcements/scholarship_detail.html', context)

@login_required
@permission_required('announcements.add_scholarship', raise_exception=True)
def scholarship_create(request):
    """إنشاء فرصة ابتعاث جديدة"""
    if request.method == 'POST':
        form = ScholarshipForm(request.POST, request.FILES)
        if form.is_valid():
            scholarship = form.save(commit=False)
            scholarship.created_by = request.user
            scholarship.save()
            messages.success(request, _("تم إنشاء فرصة الابتعاث بنجاح"))
            return redirect('announcements:scholarship_detail', pk=scholarship.pk)
    else:
        form = ScholarshipForm()

    context = {'form': form, 'is_create': True}
    return render(request, 'announcements/scholarship_form.html', context)

@login_required
@permission_required('announcements.change_scholarship', raise_exception=True)
def scholarship_edit(request, pk):
    """تعديل فرصة ابتعاث موجودة"""
    scholarship = get_object_or_404(Scholarship, pk=pk)

    if request.method == 'POST':
        form = ScholarshipForm(request.POST, request.FILES, instance=scholarship)
        if form.is_valid():
            form.save()
            messages.success(request, _("تم تحديث فرصة الابتعاث بنجاح"))
            return redirect('announcements:scholarship_detail', pk=scholarship.pk)
    else:
        form = ScholarshipForm(instance=scholarship)

    context = {'form': form, 'is_create': False, 'scholarship': scholarship}
    return render(request, 'announcements/scholarship_form.html', context)

@login_required
@permission_required('announcements.delete_scholarship', raise_exception=True)
def scholarship_delete(request, pk):
    """حذف فرصة ابتعاث"""
    scholarship = get_object_or_404(Scholarship, pk=pk)

    if request.method == 'POST':
        scholarship.delete()
        messages.success(request, _("تم حذف فرصة الابتعاث بنجاح"))
        return redirect('announcements:scholarship_list')

    context = {'scholarship': scholarship}
    return render(request, 'announcements/scholarship_confirm_delete.html', context)

def announcement_list(request):
    """عرض قائمة الإعلانات العامة"""
    announcements = Announcement.objects.filter(is_active=True).order_by('-publication_date')

    # ترقيم الصفحات
    paginator = Paginator(announcements, 10)  # 10 عناصر في كل صفحة
    page = request.GET.get('page')
    try:
        announcements_page = paginator.page(page)
    except PageNotAnInteger:
        announcements_page = paginator.page(1)
    except EmptyPage:
        announcements_page = paginator.page(paginator.num_pages)

    context = {'announcements': announcements_page}
    return render(request, 'announcements/announcement_list.html', context)

def announcement_detail(request, pk):
    """عرض تفاصيل إعلان معين"""
    announcement = get_object_or_404(Announcement, pk=pk, is_active=True)
    context = {'announcement': announcement}
    return render(request, 'announcements/announcement_detail.html', context)

@login_required
@permission_required('announcements.add_announcement', raise_exception=True)
def announcement_create(request):
    """إنشاء إعلان جديد"""
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.save()
            messages.success(request, _("تم إنشاء الإعلان بنجاح"))
            return redirect('announcements:announcement_detail', pk=announcement.pk)
    else:
        form = AnnouncementForm()

    context = {'form': form, 'is_create': True}
    return render(request, 'announcements/announcement_form.html', context)

@login_required
@permission_required('announcements.change_announcement', raise_exception=True)
def announcement_edit(request, pk):
    """تعديل إعلان موجود"""
    announcement = get_object_or_404(Announcement, pk=pk)

    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, _("تم تحديث الإعلان بنجاح"))
            return redirect('announcements:announcement_detail', pk=announcement.pk)
    else:
        form = AnnouncementForm(instance=announcement)

    context = {'form': form, 'is_create': False, 'announcement': announcement}
    return render(request, 'announcements/announcement_form.html', context)

@login_required
@permission_required('announcements.delete_announcement', raise_exception=True)
def announcement_delete(request, pk):
    """حذف إعلان"""
    announcement = get_object_or_404(Announcement, pk=pk)

    if request.method == 'POST':
        announcement.delete()
        messages.success(request, _("تم حذف الإعلان بنجاح"))
        return redirect('announcements:announcement_list')

    context = {'announcement': announcement}
    return render(request, 'announcements/announcement_confirm_delete.html', context)

@login_required
@permission_required('announcements.add_scholarshiptype', raise_exception=True)
def scholarship_type_create(request):
    """إنشاء نوع ابتعاث جديد"""
    if request.method == 'POST':
        form = ScholarshipTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("تم إنشاء نوع الابتعاث بنجاح"))
            return redirect('announcements:scholarship_list')
    else:
        form = ScholarshipTypeForm()

    context = {'form': form}
    return render(request, 'announcements/scholarship_type_form.html', context)

@login_required
def admin_dashboard(request):
    """لوحة تحكم الإعلانات للمشرفين"""
    scholarships = Scholarship.objects.order_by('-publication_date')
    announcements = Announcement.objects.order_by('-publication_date')
    scholarship_types = ScholarshipType.objects.all()

    context = {
        'scholarships': scholarships,
        'announcements': announcements,
        'scholarship_types': scholarship_types,
    }
    return render(request, 'announcements/admin_dashboard.html', context)