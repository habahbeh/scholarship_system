# from django.shortcuts import render
# from django.contrib.auth.decorators import login_required
# from django.db.models import Count, Sum, Avg, Q
# from django.http import JsonResponse
# from django.utils import timezone
# from django.utils.translation import gettext_lazy as _
# from datetime import datetime, timedelta
# from dateutil.relativedelta import relativedelta
# import json
#
# from accounts.models import Profile, Faculty, Department
# from announcements.models import Scholarship, Announcement, ScholarshipType
# from applications.models import Application, ApplicationStatus, ApplicationLog
# from evaluation.models import Committee, EvaluationRound, ApplicationEvaluation, CriterionScore
#
# from .forms import DateRangeForm, ApplicationStatsFilterForm, EvaluationStatsFilterForm
#
# @login_required
# def index(request):
#     """الصفحة الرئيسية للوحة التحكم - توجيه المستخدم إلى لوحة التحكم المناسبة حسب دوره"""
#     user_role = request.user.profile.role
#
#     # الإحصائيات المشتركة لجميع المستخدمين
#     active_scholarships_count = Scholarship.objects.filter(
#         status='published',
#         deadline__gte=timezone.now()
#     ).count()
#
#     announcements_count = Announcement.objects.filter(is_active=True).count()
#
#     # تحديد أنواع المستخدمين والإحصائيات الخاصة بكل نوع
#     context = {
#         'active_scholarships_count': active_scholarships_count,
#         'announcements_count': announcements_count,
#         'user_role': user_role
#     }
#
#     # إحصائيات حسب نوع المستخدم
#     if user_role == 'admin':
#         # إحصائيات المشرف
#         applications_by_status = Application.objects.values('status__name') \
#             .annotate(application_count=Count('id')) \
#             .order_by('status__order')
#
#         recent_applications = Application.objects.all().order_by('-application_date')[:5]
#
#         context.update({
#             'applications_by_status': applications_by_status,
#             'recent_applications': recent_applications,
#         })
#
#     elif user_role == 'committee':
#         # إحصائيات عضو لجنة التقييم
#         user_committees = Committee.objects.filter(members=request.user)
#
#         # التقييمات المعلقة للمستخدم
#         pending_evaluations = ApplicationEvaluation.objects.filter(
#             evaluator=request.user,
#             is_submitted=False,
#             evaluation_round__end_date__gte=timezone.now()
#         ).select_related('application', 'application__scholarship', 'application__applicant')
#
#         context.update({
#             'user_committees': user_committees,
#             'pending_evaluations': pending_evaluations,
#         })
#
#     elif user_role == 'faculty':
#         # إحصائيات عضو هيئة التدريس
#         faculty_students = Profile.objects.filter(
#             faculty=request.user.profile.faculty,
#             role='student'
#         )
#
#         faculty_applications_by_status = Application.objects.filter(
#             applicant__profile__faculty=request.user.profile.faculty
#         ).values('status__name').annotate(count=Count('id'))
#
#         context.update({
#             'faculty_students': faculty_students,
#             'faculty_applications_by_status': faculty_applications_by_status,
#         })
#
#     else:  # student أو أي قيمة أخرى
#         # إحصائيات الطالب
#         user_applications = Application.objects.filter(applicant=request.user)
#
#         # تحديثات الطلبات
#         recent_application_logs = Application.objects.filter(
#             applicant=request.user
#         ).values(
#             'id', 'scholarship__title', 'logs__created_at',
#             'logs__from_status__name', 'logs__to_status__name'
#         ).filter(
#             logs__created_at__isnull=False
#         ).order_by('-logs__created_at')[:5]
#
#         context.update({
#             'user_applications': user_applications,
#             'recent_application_logs': recent_application_logs,
#         })
#
#     # قائمة فرص الابتعاث القادمة لجميع المستخدمين
#     upcoming_deadlines = Scholarship.objects.filter(
#         status='published',
#         deadline__gte=timezone.now()
#     ).order_by('deadline')[:5]
#
#     context['upcoming_deadlines'] = upcoming_deadlines
#
#     return render(request, 'dashboard/index.html', context)
#
# @login_required
# def admin_dashboard(request):
#     """لوحة تحكم المشرفين"""
#     # التحقق من صلاحيات المستخدم
#     if request.user.profile.role != 'admin':
#         return redirect('dashboard:index')
#
#     # إحصائيات عامة
#     total_applications = Application.objects.count()
#     total_scholarships = Scholarship.objects.count()
#     active_scholarships = Scholarship.objects.filter(status='published', deadline__gte=timezone.now()).count()
#
#     # عدد الطلبات حسب الحالة
#     applications_by_status = Application.objects.values('status__name') \
#         .annotate(count=Count('id')) \
#         .order_by('status__order')
#
#     # عدد الطلبات حسب نوع الابتعاث
#     applications_by_type = Application.objects.values('scholarship__scholarship_type__name') \
#         .annotate(count=Count('id')) \
#         .order_by('-count')
#
#     # عدد الطلبات على مدار آخر 6 أشهر
#     last_6_months = timezone.now() - relativedelta(months=6)
#     monthly_applications = Application.objects.filter(application_date__gte=last_6_months) \
#         .extra({'month': "date_trunc('month', application_date)"}) \
#         .values('month') \
#         .annotate(count=Count('id')) \
#         .order_by('month')
#
#     # تنسيق البيانات للرسم البياني
#     months = []
#     counts = []
#     for item in monthly_applications:
#         month_name = item['month'].strftime('%B %Y')
#         months.append(month_name)
#         counts.append(item['count'])
#
#     # أحدث الطلبات
#     recent_applications = Application.objects.order_by('-application_date')[:10]
#
#     context = {
#         'total_applications': total_applications,
#         'total_scholarships': total_scholarships,
#         'active_scholarships': active_scholarships,
#         'applications_by_status': applications_by_status,
#         'applications_by_type': applications_by_type,
#         'months': months,
#         'counts': counts,
#         'recent_applications': recent_applications,
#     }
#
#     return render(request, 'dashboard/admin_dashboard.html', context)
#
# @login_required
# def student_dashboard(request):
#     """لوحة تحكم الطلاب"""
#     # التحقق من أن المستخدم طالب
#     if request.user.profile.role != 'student':
#         return redirect('dashboard:index')
#
#     # طلبات المستخدم
#     user_applications = Application.objects.filter(applicant=request.user)
#
#     # تقسيم الطلبات حسب الحالة
#     applications_by_status = {}
#     for app in user_applications:
#         status_name = app.status.name
#         if status_name in applications_by_status:
#             applications_by_status[status_name].append(app)
#         else:
#             applications_by_status[status_name] = [app]
#
#     # فرص الابتعاث القادمة
#     upcoming_scholarships = Scholarship.objects.filter(
#         status='published',
#         deadline__gte=timezone.now()
#     ).order_by('deadline')[:5]
#
#     # تحديثات الطلبات
#     application_logs = ApplicationLog.objects.filter(
#         application__applicant=request.user
#     ).order_by('-created_at')[:10]
#
#     context = {
#         'user_applications': user_applications,
#         'applications_by_status': applications_by_status,
#         'upcoming_scholarships': upcoming_scholarships,
#         'application_logs': application_logs,
#     }
#
#     return render(request, 'dashboard/student_dashboard.html', context)
#
# @login_required
# def faculty_dashboard(request):
#     """لوحة تحكم أعضاء هيئة التدريس"""
#     # التحقق من أن المستخدم عضو هيئة تدريس
#     if request.user.profile.role != 'faculty':
#         return redirect('dashboard:index')
#
#     # الكلية الخاصة بالمستخدم
#     faculty = request.user.profile.faculty
#
#     # عدد الطلاب في الكلية
#     students_count = Profile.objects.filter(
#         faculty=faculty,
#         role='student'
#     ).count()
#
#     # طلبات طلاب الكلية
#     faculty_applications = Application.objects.filter(
#         applicant__profile__faculty=faculty
#     )
#
#     # عدد الطلبات حسب الحالة
#     applications_by_status = faculty_applications.values('status__name') \
#         .annotate(count=Count('id')) \
#         .order_by('status__order')
#
#     # عدد الطلبات حسب نوع الابتعاث
#     applications_by_type = faculty_applications.values('scholarship__scholarship_type__name') \
#         .annotate(count=Count('id')) \
#         .order_by('-count')
#
#     # أحدث الطلبات
#     recent_applications = faculty_applications.order_by('-application_date')[:10]
#
#     context = {
#         'faculty': faculty,
#         'students_count': students_count,
#         'faculty_applications': faculty_applications,
#         'applications_by_status': applications_by_status,
#         'applications_by_type': applications_by_type,
#         'recent_applications': recent_applications,
#     }
#
#     return render(request, 'dashboard/faculty_dashboard.html', context)
#
# @login_required
# def application_stats(request):
#     """إحصائيات وتقارير الطلبات"""
#     # نموذج التصفية
#     filter_form = ApplicationStatsFilterForm(request.GET or None)
#
#     # الطلبات الأساسية
#     applications = Application.objects.all()
#
#     # تطبيق المرشحات
#     if filter_form.is_valid():
#         data = filter_form.cleaned_data
#
#         # تصفية حسب نوع الابتعاث
#         if data.get('scholarship_type'):
#             applications = applications.filter(scholarship__scholarship_type=data['scholarship_type'])
#
#         # تصفية حسب الحالة
#         if data.get('status'):
#             applications = applications.filter(status=data['status'])
#
#         # تصفية حسب النطاق الزمني
#         date_range = data.get('date_range')
#         if date_range:
#             now = timezone.now()
#             if date_range == 'month':
#                 start_date = now - relativedelta(months=1)
#                 applications = applications.filter(application_date__gte=start_date)
#             elif date_range == 'quarter':
#                 start_date = now - relativedelta(months=3)
#                 applications = applications.filter(application_date__gte=start_date)
#             elif date_range == 'year':
#                 start_date = now - relativedelta(years=1)
#                 applications = applications.filter(application_date__gte=start_date)
#             elif date_range == 'custom':
#                 if data.get('start_date'):
#                     applications = applications.filter(application_date__gte=data['start_date'])
#                 if data.get('end_date'):
#                     applications = applications.filter(application_date__lte=data['end_date'])
#
#         # تجميع البيانات للرسم البياني
#         group_by = data.get('group_by', 'status')
#         if group_by == 'status':
#             chart_data = applications.values('status__name') \
#                 .annotate(count=Count('id')) \
#                 .order_by('status__order')
#             chart_labels = [item['status__name'] for item in chart_data]
#             chart_values = [item['count'] for item in chart_data]
#         elif group_by == 'scholarship_type':
#             chart_data = applications.values('scholarship__scholarship_type__name') \
#                 .annotate(count=Count('id')) \
#                 .order_by('-count')
#             chart_labels = [item['scholarship__scholarship_type__name'] for item in chart_data]
#             chart_values = [item['count'] for item in chart_data]
#         elif group_by == 'month':
#             chart_data = applications.extra({'month': "date_trunc('month', application_date)"}) \
#                 .values('month') \
#                 .annotate(count=Count('id')) \
#                 .order_by('month')
#             chart_labels = [item['month'].strftime('%B %Y') for item in chart_data]
#             chart_values = [item['count'] for item in chart_data]
#         elif group_by == 'faculty':
#             chart_data = applications.values('applicant__profile__faculty__name') \
#                 .annotate(count=Count('id')) \
#                 .order_by('-count')
#             chart_labels = [item['applicant__profile__faculty__name'] or _("غير محدد") for item in chart_data]
#             chart_values = [item['count'] for item in chart_data]
#     else:
#         # القيم الافتراضية
#         chart_data = applications.values('status__name') \
#             .annotate(count=Count('id')) \
#             .order_by('status__order')
#         chart_labels = [item['status__name'] for item in chart_data]
#         chart_values = [item['count'] for item in chart_data]
#
#     # البيانات الإضافية
#     total_applications = applications.count()
#     applications_by_gender = applications.values('applicant__profile__gender') \
#         .annotate(count=Count('id'))
#
#     context = {
#         'filter_form': filter_form,
#         'total_applications': total_applications,
#         'applications_by_gender': applications_by_gender,
#         'chart_labels': chart_labels,
#         'chart_values': chart_values,
#         'chart_type': filter_form.cleaned_data.get('chart_type', 'bar') if filter_form.is_valid() else 'bar',
#     }
#
#     return render(request, 'dashboard/application_stats.html', context)
#
# @login_required
# def evaluation_stats(request):
#     """إحصائيات وتقارير التقييمات"""
#     # نموذج التصفية
#     filter_form = EvaluationStatsFilterForm(request.GET or None)
#
#     # التقييمات الأساسية
#     evaluations = ApplicationEvaluation.objects.all()
#
#     # تطبيق المرشحات
#     if filter_form.is_valid():
#         data = filter_form.cleaned_data
#
#         # تصفية حسب اللجنة
#         if data.get('committee'):
#             evaluations = evaluations.filter(evaluation_round__committee_id=data['committee'])
#
#         # تصفية حسب نوع الجولة
#         if data.get('round_type'):
#             evaluations = evaluations.filter(evaluation_round__round_type=data['round_type'])
#
#         # تصفية حسب المقيّم
#         if data.get('evaluator'):
#             evaluations = evaluations.filter(evaluator=data['evaluator'])
#
#         # تصفية حسب النطاق الزمني
#         date_range = data.get('date_range')
#         if date_range:
#             now = timezone.now()
#             if date_range == 'month':
#                 start_date = now - relativedelta(months=1)
#                 evaluations = evaluations.filter(evaluation_date__gte=start_date)
#             elif date_range == 'quarter':
#                 start_date = now - relativedelta(months=3)
#                 evaluations = evaluations.filter(evaluation_date__gte=start_date)
#             elif date_range == 'year':
#                 start_date = now - relativedelta(years=1)
#                 evaluations = evaluations.filter(evaluation_date__gte=start_date)
#             elif date_range == 'custom':
#                 if data.get('start_date'):
#                     evaluations = evaluations.filter(evaluation_date__gte=data['start_date'])
#                 if data.get('end_date'):
#                     evaluations = evaluations.filter(evaluation_date__lte=data['end_date'])
#
#     # البيانات الأساسية
#     total_evaluations = evaluations.count()
#     completed_evaluations = evaluations.filter(is_submitted=True).count()
#     pending_evaluations = total_evaluations - completed_evaluations
#
#     if total_evaluations > 0:
#         completion_rate = (completed_evaluations / total_evaluations) * 100
#     else:
#         completion_rate = 0
#
#     # متوسط الدرجات حسب المعيار
#     avg_scores_by_criterion = CriterionScore.objects.filter(
#         evaluation__in=evaluations
#     ).values('criterion__name').annotate(
#         avg_score=Avg('score')
#     ).order_by('-avg_score')
#
#     # عدد التقييمات حسب الجولة
#     evaluations_by_round = evaluations.values('evaluation_round__name').annotate(
#         count=Count('id')
#     ).order_by('-count')
#
#     # عدد التقييمات حسب المقيّم
#     evaluations_by_evaluator = evaluations.values(
#         'evaluator__first_name', 'evaluator__last_name'
#     ).annotate(
#         count=Count('id')
#     ).order_by('-count')[:10]
#
#     context = {
#         'filter_form': filter_form,
#         'total_evaluations': total_evaluations,
#         'completed_evaluations': completed_evaluations,
#         'pending_evaluations': pending_evaluations,
#         'completion_rate': completion_rate,
#         'avg_scores_by_criterion': avg_scores_by_criterion,
#         'evaluations_by_round': evaluations_by_round,
#         'evaluations_by_evaluator': evaluations_by_evaluator,
#     }
#
#     return render(request, 'dashboard/evaluation_stats.html', context)
#
# @login_required
# def scholarship_stats(request):
#     """إحصائيات وتقارير فرص الابتعاث"""
#     # نموذج النطاق الزمني
#     form = DateRangeForm(request.GET or None)
#
#     # فرص الابتعاث
#     scholarships = Scholarship.objects.all()
#
#     # تطبيق المرشحات
#     if form.is_valid():
#         if form.cleaned_data.get('start_date'):
#             scholarships = scholarships.filter(publication_date__gte=form.cleaned_data['start_date'])
#         if form.cleaned_data.get('end_date'):
#             scholarships = scholarships.filter(publication_date__lte=form.cleaned_data['end_date'])
#
#     # عدد الفرص حسب النوع
#     scholarships_by_type = scholarships.values('scholarship_type__name').annotate(
#         count=Count('id')
#     ).order_by('-count')
#
#     # عدد الفرص حسب الحالة
#     scholarships_by_status = scholarships.values('status').annotate(
#         count=Count('id')
#     ).order_by('status')
#
#     # عدد الطلبات على كل فرصة
#     applications_per_scholarship = Application.objects.values(
#         'scholarship__title'
#     ).annotate(
#         count=Count('id')
#     ).order_by('-count')[:10]
#
#     # إجمالي عدد الطلبات - ADDED THIS LINE
#     applications_total = Application.objects.count()
#
#     # نسب القبول
#     scholarships_acceptance_rates = []
#     for scholarship in scholarships:
#         total_apps = Application.objects.filter(scholarship=scholarship).count()
#         if total_apps > 0:
#             accepted_apps = Application.objects.filter(
#                 scholarship=scholarship,
#                 status__name__icontains='مقبول'
#             ).count()
#             rate = (accepted_apps / total_apps) * 100
#             scholarships_acceptance_rates.append({
#                 'scholarship': scholarship.title,
#                 'total': total_apps,
#                 'accepted': accepted_apps,
#                 'rate': rate
#             })
#
#     context = {
#         'form': form,
#         'scholarships_by_type': scholarships_by_type,
#         'scholarships_by_status': scholarships_by_status,
#         'applications_per_scholarship': applications_per_scholarship,
#         'scholarships_acceptance_rates': scholarships_acceptance_rates,
#         'applications_total': applications_total,  # ADDED THIS LINE
#     }
#
#     return render(request, 'dashboard/scholarship_stats.html', context)
#
# # ============ واجهات برمجة التطبيقات (API) - لوحات التحكم ============
#
# @login_required
# def api_application_statuses(request):
#     """بيانات API لحالات الطلبات - للرسوم البيانية"""
#     applications_by_status = Application.objects.values('status__name') \
#         .annotate(count=Count('id')) \
#         .order_by('status__order')
#
#     data = {
#         'labels': [item['status__name'] for item in applications_by_status],
#         'data': [item['count'] for item in applications_by_status],
#     }
#
#     return JsonResponse(data)
#
# @login_required
# def api_scholarships_count(request):
#     """بيانات API لعدد فرص الابتعاث - للرسوم البيانية"""
#     active_count = Scholarship.objects.filter(
#         status='published',
#         deadline__gte=timezone.now()
#     ).count()
#
#     closed_count = Scholarship.objects.filter(
#         status='published',
#         deadline__lt=timezone.now()
#     ).count()
#
#     draft_count = Scholarship.objects.filter(status='draft').count()
#
#     data = {
#         'labels': [_("نشطة"), _("مغلقة"), _("مسودة")],
#         'data': [active_count, closed_count, draft_count],
#     }
#
#     return JsonResponse(data)
#
# @login_required
# def api_evaluations_progress(request):
#     """بيانات API لتقدم التقييمات - للرسوم البيانية"""
#     evaluations = ApplicationEvaluation.objects.all()
#
#     completed = evaluations.filter(is_submitted=True).count()
#     pending = evaluations.filter(is_submitted=False).count()
#
#     data = {
#         'labels': [_("مكتملة"), _("معلقة")],
#         'data': [completed, pending],
#     }
#
#     return JsonResponse(data)
#
# @login_required
# def api_monthly_applications(request):
#     """بيانات API لعدد الطلبات الشهرية - للرسوم البيانية"""
#     # الطلبات في آخر 6 أشهر
#     last_6_months = timezone.now() - relativedelta(months=6)
#
#     monthly_data = Application.objects.filter(
#         application_date__gte=last_6_months
#     ).extra(
#         {'month': "date_trunc('month', application_date)"}
#     ).values('month').annotate(
#         count=Count('id')
#     ).order_by('month')
#
#     data = {
#         'labels': [item['month'].strftime('%B %Y') for item in monthly_data],
#         'data': [item['count'] for item in monthly_data],
#     }
#
#     return JsonResponse(data)




from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg, Q
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json

from accounts.models import Profile, Faculty, Department
from announcements.models import Scholarship, Announcement, ScholarshipType
from applications.models import Application, ApplicationStatus, ApplicationLog
from evaluation.models import Committee, EvaluationRound, ApplicationEvaluation, CriterionScore

from .forms import DateRangeForm, ApplicationStatsFilterForm, EvaluationStatsFilterForm

@login_required
def index(request):
    """الصفحة الرئيسية للوحة التحكم - توجيه المستخدم إلى لوحة التحكم المناسبة حسب دوره"""
    user_role = request.user.profile.role

    # الإحصائيات المشتركة لجميع المستخدمين
    active_scholarships_count = Scholarship.objects.filter(
        status='published',
        deadline__gte=timezone.now()
    ).count()

    announcements_count = Announcement.objects.filter(is_active=True).count()

    # تحديد أنواع المستخدمين والإحصائيات الخاصة بكل نوع
    context = {
        'active_scholarships_count': active_scholarships_count,
        'announcements_count': announcements_count,
        'user_role': user_role
    }

    # إحصائيات حسب نوع المستخدم
    if user_role == 'admin':
        # إحصائيات المشرف
        applications_by_status = Application.objects.values('status__name') \
            .annotate(application_count=Count('id')) \
            .order_by('status__order')

        recent_applications = Application.objects.all().order_by('-application_date')[:5]

        context.update({
            'applications_by_status': applications_by_status,
            'recent_applications': recent_applications,
        })

    elif user_role == 'committee':
        # إحصائيات عضو لجنة التقييم
        user_committees = Committee.objects.filter(members=request.user)

        # التقييمات المعلقة للمستخدم
        pending_evaluations = ApplicationEvaluation.objects.filter(
            evaluator=request.user,
            is_submitted=False,
            evaluation_round__end_date__gte=timezone.now()
        ).select_related('application', 'application__scholarship', 'application__applicant')

        context.update({
            'user_committees': user_committees,
            'pending_evaluations': pending_evaluations,
        })

    elif user_role == 'faculty':
        # إحصائيات عضو هيئة التدريس
        faculty_students = Profile.objects.filter(
            faculty=request.user.profile.faculty,
            role='student'
        )

        faculty_applications_by_status = Application.objects.filter(
            applicant__profile__faculty=request.user.profile.faculty
        ).values('status__name').annotate(count=Count('id'))

        context.update({
            'faculty_students': faculty_students,
            'faculty_applications_by_status': faculty_applications_by_status,
        })

    else:  # student أو أي قيمة أخرى
        # إحصائيات الطالب
        user_applications = Application.objects.filter(applicant=request.user)

        # تحديثات الطلبات
        recent_application_logs = Application.objects.filter(
            applicant=request.user
        ).values(
            'id', 'scholarship__title', 'logs__created_at',
            'logs__from_status__name', 'logs__to_status__name'
        ).filter(
            logs__created_at__isnull=False
        ).order_by('-logs__created_at')[:5]

        context.update({
            'user_applications': user_applications,
            'recent_application_logs': recent_application_logs,
        })

    # قائمة فرص الابتعاث القادمة لجميع المستخدمين
    upcoming_deadlines = Scholarship.objects.filter(
        status='published',
        deadline__gte=timezone.now()
    ).order_by('deadline')[:5]

    context['upcoming_deadlines'] = upcoming_deadlines

    return render(request, 'dashboard/index.html', context)

@login_required
def admin_dashboard(request):
    """لوحة تحكم المشرفين"""
    # التحقق من صلاحيات المستخدم
    if request.user.profile.role != 'admin':
        return redirect('dashboard:index')

    # إحصائيات عامة
    total_applications = Application.objects.count()
    total_scholarships = Scholarship.objects.count()
    active_scholarships = Scholarship.objects.filter(status='published', deadline__gte=timezone.now()).count()

    # عدد الطلبات حسب الحالة
    applications_by_status = Application.objects.values('status__name') \
        .annotate(count=Count('id')) \
        .order_by('status__order')

    # عدد الطلبات حسب نوع الابتعاث
    applications_by_type = Application.objects.values('scholarship__scholarship_type__name') \
        .annotate(count=Count('id')) \
        .order_by('-count')

    # عدد الطلبات على مدار آخر 6 أشهر
    last_6_months = timezone.now() - relativedelta(months=6)

    # بدلاً من استخدام date_trunc، نستخدم طريقة متوافقة مع SQLite
    # نحصل على الطلبات وننظمها يدويًا حسب الشهر
    monthly_apps = Application.objects.filter(application_date__gte=last_6_months).order_by('application_date')

    # تنظيم البيانات حسب الشهر
    months_data = {}
    for app in monthly_apps:
        # استخراج الشهر والسنة
        month_year = app.application_date.strftime('%Y-%m')
        month_name = app.application_date.strftime('%B %Y')

        if month_year in months_data:
            months_data[month_year]['count'] += 1
        else:
            months_data[month_year] = {
                'name': month_name,
                'count': 1
            }

    # تنسيق البيانات للرسم البياني
    months = []
    counts = []
    for month_key in sorted(months_data.keys()):
        months.append(months_data[month_key]['name'])
        counts.append(months_data[month_key]['count'])

    # أحدث الطلبات
    recent_applications = Application.objects.order_by('-application_date')[:10]

    context = {
        'total_applications': total_applications,
        'total_scholarships': total_scholarships,
        'active_scholarships': active_scholarships,
        'applications_by_status': applications_by_status,
        'applications_by_type': applications_by_type,
        'months': months,
        'counts': counts,
        'recent_applications': recent_applications,
    }

    return render(request, 'dashboard/admin_dashboard.html', context)

@login_required
def student_dashboard(request):
    """لوحة تحكم الطلاب"""
    # التحقق من أن المستخدم طالب
    if request.user.profile.role != 'student':
        return redirect('dashboard:index')

    # طلبات المستخدم
    user_applications = Application.objects.filter(applicant=request.user)

    # تقسيم الطلبات حسب الحالة
    applications_by_status = {}
    for app in user_applications:
        status_name = app.status.name
        if status_name in applications_by_status:
            applications_by_status[status_name].append(app)
        else:
            applications_by_status[status_name] = [app]

    # فرص الابتعاث القادمة
    upcoming_scholarships = Scholarship.objects.filter(
        status='published',
        deadline__gte=timezone.now()
    ).order_by('deadline')[:5]

    # تحديثات الطلبات
    application_logs = ApplicationLog.objects.filter(
        application__applicant=request.user
    ).order_by('-created_at')[:10]

    context = {
        'user_applications': user_applications,
        'applications_by_status': applications_by_status,
        'upcoming_scholarships': upcoming_scholarships,
        'application_logs': application_logs,
    }

    return render(request, 'dashboard/student_dashboard.html', context)

@login_required
def faculty_dashboard(request):
    """لوحة تحكم أعضاء هيئة التدريس"""
    # التحقق من أن المستخدم عضو هيئة تدريس
    if request.user.profile.role != 'faculty':
        return redirect('dashboard:index')

    # الكلية الخاصة بالمستخدم
    faculty = request.user.profile.faculty

    # عدد الطلاب في الكلية
    students_count = Profile.objects.filter(
        faculty=faculty,
        role='student'
    ).count()

    # طلبات طلاب الكلية
    faculty_applications = Application.objects.filter(
        applicant__profile__faculty=faculty
    )

    # عدد الطلبات حسب الحالة
    applications_by_status = faculty_applications.values('status__name') \
        .annotate(count=Count('id')) \
        .order_by('status__order')

    # عدد الطلبات حسب نوع الابتعاث
    applications_by_type = faculty_applications.values('scholarship__scholarship_type__name') \
        .annotate(count=Count('id')) \
        .order_by('-count')

    # أحدث الطلبات
    recent_applications = faculty_applications.order_by('-application_date')[:10]

    context = {
        'faculty': faculty,
        'students_count': students_count,
        'faculty_applications': faculty_applications,
        'applications_by_status': applications_by_status,
        'applications_by_type': applications_by_type,
        'recent_applications': recent_applications,
    }

    return render(request, 'dashboard/faculty_dashboard.html', context)

@login_required
def application_stats(request):
    """إحصائيات وتقارير الطلبات"""
    # نموذج التصفية
    filter_form = ApplicationStatsFilterForm(request.GET or None)

    # الطلبات الأساسية
    applications = Application.objects.all()

    # تطبيق المرشحات
    if filter_form.is_valid():
        data = filter_form.cleaned_data

        # تصفية حسب نوع الابتعاث
        if data.get('scholarship_type'):
            applications = applications.filter(scholarship__scholarship_type=data['scholarship_type'])

        # تصفية حسب الحالة
        if data.get('status'):
            applications = applications.filter(status=data['status'])

        # تصفية حسب النطاق الزمني
        date_range = data.get('date_range')
        if date_range:
            now = timezone.now()
            if date_range == 'month':
                start_date = now - relativedelta(months=1)
                applications = applications.filter(application_date__gte=start_date)
            elif date_range == 'quarter':
                start_date = now - relativedelta(months=3)
                applications = applications.filter(application_date__gte=start_date)
            elif date_range == 'year':
                start_date = now - relativedelta(years=1)
                applications = applications.filter(application_date__gte=start_date)
            elif date_range == 'custom':
                if data.get('start_date'):
                    applications = applications.filter(application_date__gte=data['start_date'])
                if data.get('end_date'):
                    applications = applications.filter(application_date__lte=data['end_date'])

        # تجميع البيانات للرسم البياني
        group_by = data.get('group_by', 'status')
        if group_by == 'status':
            chart_data = applications.values('status__name') \
                .annotate(count=Count('id')) \
                .order_by('status__order')
            chart_labels = [item['status__name'] for item in chart_data]
            chart_values = [item['count'] for item in chart_data]
        elif group_by == 'scholarship_type':
            chart_data = applications.values('scholarship__scholarship_type__name') \
                .annotate(count=Count('id')) \
                .order_by('-count')
            chart_labels = [item['scholarship__scholarship_type__name'] for item in chart_data]
            chart_values = [item['count'] for item in chart_data]
        elif group_by == 'month':
            # بدلاً من استخدام date_trunc، نقوم بتجميع البيانات يدويًا
            apps_with_month = list(applications)
            month_data = {}

            for app in apps_with_month:
                month_key = app.application_date.strftime('%Y-%m')
                month_name = app.application_date.strftime('%B %Y')

                if month_key in month_data:
                    month_data[month_key]['count'] += 1
                else:
                    month_data[month_key] = {
                        'month': month_name,
                        'count': 1
                    }

            # ترتيب البيانات حسب الشهر
            sorted_months = sorted(month_data.keys())
            chart_data = [month_data[m] for m in sorted_months]
            chart_labels = [item['month'] for item in chart_data]
            chart_values = [item['count'] for item in chart_data]
        elif group_by == 'faculty':
            chart_data = applications.values('applicant__profile__faculty__name') \
                .annotate(count=Count('id')) \
                .order_by('-count')
            chart_labels = [item['applicant__profile__faculty__name'] or _("غير محدد") for item in chart_data]
            chart_values = [item['count'] for item in chart_data]
    else:
        # القيم الافتراضية
        chart_data = applications.values('status__name') \
            .annotate(count=Count('id')) \
            .order_by('status__order')
        chart_labels = [item['status__name'] for item in chart_data]
        chart_values = [item['count'] for item in chart_data]

    # البيانات الإضافية
    total_applications = applications.count()
    applications_by_gender = applications.values('applicant__profile__gender') \
        .annotate(count=Count('id'))

    context = {
        'filter_form': filter_form,
        'total_applications': total_applications,
        'applications_by_gender': applications_by_gender,
        'chart_labels': chart_labels,
        'chart_values': chart_values,
        'chart_type': filter_form.cleaned_data.get('chart_type', 'bar') if filter_form.is_valid() else 'bar',
        'chart_colors': [
            'rgba(54, 162, 235, 0.7)',
            'rgba(255, 99, 132, 0.7)',
            'rgba(75, 192, 192, 0.7)',
            'rgba(255, 159, 64, 0.7)',
            'rgba(153, 102, 255, 0.7)',
            'rgba(255, 205, 86, 0.7)',
            'rgba(201, 203, 207, 0.7)'
        ]
    }

    return render(request, 'dashboard/application_stats.html', context)

@login_required
def evaluation_stats(request):
    """إحصائيات وتقارير التقييمات"""
    # نموذج التصفية
    filter_form = EvaluationStatsFilterForm(request.GET or None)

    # التقييمات الأساسية
    evaluations = ApplicationEvaluation.objects.all()

    # تطبيق المرشحات
    if filter_form.is_valid():
        data = filter_form.cleaned_data

        # تصفية حسب اللجنة
        if data.get('committee'):
            evaluations = evaluations.filter(evaluation_round__committee_id=data['committee'])

        # تصفية حسب نوع الجولة
        if data.get('round_type'):
            evaluations = evaluations.filter(evaluation_round__round_type=data['round_type'])

        # تصفية حسب المقيّم
        if data.get('evaluator'):
            evaluations = evaluations.filter(evaluator=data['evaluator'])

        # تصفية حسب النطاق الزمني
        date_range = data.get('date_range')
        if date_range:
            now = timezone.now()
            if date_range == 'month':
                start_date = now - relativedelta(months=1)
                evaluations = evaluations.filter(evaluation_date__gte=start_date)
            elif date_range == 'quarter':
                start_date = now - relativedelta(months=3)
                evaluations = evaluations.filter(evaluation_date__gte=start_date)
            elif date_range == 'year':
                start_date = now - relativedelta(years=1)
                evaluations = evaluations.filter(evaluation_date__gte=start_date)
            elif date_range == 'custom':
                if data.get('start_date'):
                    evaluations = evaluations.filter(evaluation_date__gte=data['start_date'])
                if data.get('end_date'):
                    evaluations = evaluations.filter(evaluation_date__lte=data['end_date'])

    # البيانات الأساسية
    total_evaluations = evaluations.count()
    completed_evaluations = evaluations.filter(is_submitted=True).count()
    pending_evaluations = total_evaluations - completed_evaluations

    if total_evaluations > 0:
        completion_rate = (completed_evaluations / total_evaluations) * 100
    else:
        completion_rate = 0

    # متوسط الدرجات حسب المعيار
    avg_scores_by_criterion = CriterionScore.objects.filter(
        evaluation__in=evaluations
    ).values('criterion__name').annotate(
        avg_score=Avg('score')
    ).order_by('-avg_score')

    # عدد التقييمات حسب الجولة
    evaluations_by_round = evaluations.values('evaluation_round__name').annotate(
        count=Count('id')
    ).order_by('-count')

    # عدد التقييمات حسب المقيّم
    evaluations_by_evaluator = evaluations.values(
        'evaluator__first_name', 'evaluator__last_name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    context = {
        'filter_form': filter_form,
        'total_evaluations': total_evaluations,
        'completed_evaluations': completed_evaluations,
        'pending_evaluations': pending_evaluations,
        'completion_rate': completion_rate,
        'avg_scores_by_criterion': avg_scores_by_criterion,
        'evaluations_by_round': evaluations_by_round,
        'evaluations_by_evaluator': evaluations_by_evaluator,
    }

    return render(request, 'dashboard/evaluation_stats.html', context)

@login_required
def scholarship_stats(request):
    """إحصائيات وتقارير فرص الابتعاث"""
    # نموذج النطاق الزمني
    form = DateRangeForm(request.GET or None)

    # فرص الابتعاث
    scholarships = Scholarship.objects.all()

    # تطبيق المرشحات
    if form.is_valid():
        if form.cleaned_data.get('start_date'):
            scholarships = scholarships.filter(publication_date__gte=form.cleaned_data['start_date'])
        if form.cleaned_data.get('end_date'):
            scholarships = scholarships.filter(publication_date__lte=form.cleaned_data['end_date'])

    # عدد الفرص حسب النوع
    scholarships_by_type = scholarships.values('scholarship_type__name').annotate(
        count=Count('id')
    ).order_by('-count')

    # عدد الفرص حسب الحالة
    scholarships_by_status = scholarships.values('status').annotate(
        count=Count('id')
    ).order_by('status')

    # عدد الطلبات على كل فرصة
    applications_per_scholarship = Application.objects.values(
        'scholarship__title'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    # إجمالي عدد الطلبات
    applications_total = Application.objects.count()

    # نسب القبول
    scholarships_acceptance_rates = []
    for scholarship in scholarships:
        total_apps = Application.objects.filter(scholarship=scholarship).count()
        if total_apps > 0:
            accepted_apps = Application.objects.filter(
                scholarship=scholarship,
                status__name__icontains='مقبول'
            ).count()
            rate = (accepted_apps / total_apps) * 100
            scholarships_acceptance_rates.append({
                'scholarship': scholarship.title,
                'total': total_apps,
                'accepted': accepted_apps,
                'rate': rate
            })

    context = {
        'form': form,
        'scholarships_by_type': scholarships_by_type,
        'scholarships_by_status': scholarships_by_status,
        'applications_per_scholarship': applications_per_scholarship,
        'scholarships_acceptance_rates': scholarships_acceptance_rates,
        'applications_total': applications_total,
    }

    return render(request, 'dashboard/scholarship_stats.html', context)

# ============ واجهات برمجة التطبيقات (API) - لوحات التحكم ============

@login_required
def api_application_statuses(request):
    """بيانات API لحالات الطلبات - للرسوم البيانية"""
    applications_by_status = Application.objects.values('status__name') \
        .annotate(count=Count('id')) \
        .order_by('status__order')

    data = {
        'labels': [item['status__name'] for item in applications_by_status],
        'data': [item['count'] for item in applications_by_status],
    }

    return JsonResponse(data)

@login_required
def api_scholarships_count(request):
    """بيانات API لعدد فرص الابتعاث - للرسوم البيانية"""
    active_count = Scholarship.objects.filter(
        status='published',
        deadline__gte=timezone.now()
    ).count()

    closed_count = Scholarship.objects.filter(
        status='published',
        deadline__lt=timezone.now()
    ).count()

    draft_count = Scholarship.objects.filter(status='draft').count()

    data = {
        'labels': [_("نشطة"), _("مغلقة"), _("مسودة")],
        'data': [active_count, closed_count, draft_count],
    }

    return JsonResponse(data)

@login_required
def api_evaluations_progress(request):
    """بيانات API لتقدم التقييمات - للرسوم البيانية"""
    evaluations = ApplicationEvaluation.objects.all()

    completed = evaluations.filter(is_submitted=True).count()
    pending = evaluations.filter(is_submitted=False).count()

    data = {
        'labels': [_("مكتملة"), _("معلقة")],
        'data': [completed, pending],
    }

    return JsonResponse(data)

@login_required
def api_monthly_applications(request):
    """بيانات API لعدد الطلبات الشهرية - للرسوم البيانية"""
    # الطلبات في آخر 6 أشهر
    last_6_months = timezone.now() - relativedelta(months=6)

    # بدلاً من استخدام date_trunc، نستخدم طريقة متوافقة مع SQLite
    monthly_applications = Application.objects.filter(application_date__gte=last_6_months)

    # معالجة البيانات يدويًا
    month_data = {}
    for app in monthly_applications:
        month_key = app.application_date.strftime('%Y-%m')
        month_name = app.application_date.strftime('%B %Y')

        if month_key in month_data:
            month_data[month_key]['count'] += 1
        else:
            month_data[month_key] = {
                'month': month_name,
                'count': 1
            }

    # ترتيب البيانات حسب الشهر
    sorted_data = []
    for month_key in sorted(month_data.keys()):
        sorted_data.append(month_data[month_key])

    data = {
        'labels': [item['month'] for item in sorted_data],
        'data': [item['count'] for item in sorted_data],
    }

    return JsonResponse(data)