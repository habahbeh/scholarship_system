from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Avg, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.contrib.auth.models import User
from django.forms import inlineformset_factory

from applications.models import Application, ApplicationStatus
from .models import (
    Committee, EvaluationCriterion, EvaluationRound,
    ApplicationEvaluation, CriterionScore, Vote, Recommendation
)
from .forms import (
    CommitteeForm, CommitteeMemberForm, CriterionForm, EvaluationRoundForm,
    RoundAssignApplicationsForm, ApplicationEvaluationForm, CriterionScoreForm,
    VoteForm, RecommendationForm
)

# ============ لجان التقييم ============

@login_required
@permission_required('evaluation.view_committee')
def committee_list(request):
    """عرض قائمة لجان التقييم"""
    committees = Committee.objects.all().order_by('name')

    # ترقيم الصفحات
    paginator = Paginator(committees, 10)
    page = request.GET.get('page')
    try:
        committees_page = paginator.page(page)
    except PageNotAnInteger:
        committees_page = paginator.page(1)
    except EmptyPage:
        committees_page = paginator.page(paginator.num_pages)

    context = {
        'committees': committees_page,
    }
    return render(request, 'evaluation/committee_list.html', context)

@login_required
@permission_required('evaluation.view_committee')
def committee_detail(request, pk):
    """عرض تفاصيل لجنة تقييم"""
    committee = get_object_or_404(Committee, pk=pk)
    members = committee.members.all()
    evaluation_rounds = committee.evaluation_rounds.all().order_by('-start_date')

    context = {
        'committee': committee,
        'members': members,
        'evaluation_rounds': evaluation_rounds,
    }
    return render(request, 'evaluation/committee_detail.html', context)

@login_required
@permission_required('evaluation.add_committee')
def committee_create(request):
    """إنشاء لجنة تقييم جديدة"""
    if request.method == 'POST':
        form = CommitteeForm(request.POST)
        if form.is_valid():
            committee = form.save()
            messages.success(request, _("تم إنشاء اللجنة بنجاح"))
            return redirect('evaluation:committee_detail', pk=committee.pk)
    else:
        form = CommitteeForm()

    context = {
        'form': form,
        'is_create': True,
    }
    return render(request, 'evaluation/committee_form.html', context)

@login_required
@permission_required('evaluation.change_committee')
def committee_edit(request, pk):
    """تعديل لجنة تقييم"""
    committee = get_object_or_404(Committee, pk=pk)

    if request.method == 'POST':
        form = CommitteeForm(request.POST, instance=committee)
        if form.is_valid():
            form.save()
            messages.success(request, _("تم تحديث اللجنة بنجاح"))
            return redirect('evaluation:committee_detail', pk=committee.pk)
    else:
        form = CommitteeForm(instance=committee)

    context = {
        'form': form,
        'committee': committee,
        'is_create': False,
    }
    return render(request, 'evaluation/committee_form.html', context)

@login_required
@permission_required('evaluation.delete_committee')
def committee_delete(request, pk):
    """حذف لجنة تقييم"""
    committee = get_object_or_404(Committee, pk=pk)

    if request.method == 'POST':
        committee.delete()
        messages.success(request, _("تم حذف اللجنة بنجاح"))
        return redirect('evaluation:committee_list')

    context = {
        'committee': committee,
    }
    return render(request, 'evaluation/committee_confirm_delete.html', context)

@login_required
@permission_required('evaluation.change_committee')
def committee_add_member(request, pk):
    """إضافة عضو للجنة"""
    committee = get_object_or_404(Committee, pk=pk)

    if request.method == 'POST':
        form = CommitteeMemberForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            if user in committee.members.all():
                messages.warning(request, _("هذا المستخدم عضو بالفعل في اللجنة"))
            else:
                committee.members.add(user)
                messages.success(request, _("تمت إضافة العضو بنجاح"))
            return redirect('evaluation:committee_detail', pk=committee.pk)
    else:
        # استبعاد الأعضاء الحاليين من القائمة
        current_members = committee.members.all()
        queryset = User.objects.exclude(id__in=current_members.values_list('id', flat=True))
        form = CommitteeMemberForm()
        form.fields['user'].queryset = queryset

    context = {
        'form': form,
        'committee': committee,
    }
    return render(request, 'evaluation/committee_add_member.html', context)

@login_required
@permission_required('evaluation.change_committee')
def committee_remove_member(request, pk, user_id):
    """إزالة عضو من اللجنة"""
    committee = get_object_or_404(Committee, pk=pk)
    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        committee.members.remove(user)
        messages.success(request, _("تمت إزالة العضو بنجاح"))
        return redirect('evaluation:committee_detail', pk=committee.pk)

    context = {
        'committee': committee,
        'user': user,
    }
    return render(request, 'evaluation/committee_remove_member.html', context)

# ============ معايير التقييم ============

@login_required
@permission_required('evaluation.view_evaluationcriterion')
def criterion_list(request):
    """عرض قائمة معايير التقييم"""
    criteria = EvaluationCriterion.objects.all().order_by('order', 'name')

    context = {
        'criteria': criteria,
    }
    return render(request, 'evaluation/criterion_list.html', context)

@login_required
@permission_required('evaluation.add_evaluationcriterion')
def criterion_create(request):
    """إنشاء معيار تقييم جديد"""
    if request.method == 'POST':
        form = CriterionForm(request.POST)
        if form.is_valid():
            criterion = form.save()
            messages.success(request, _("تم إنشاء المعيار بنجاح"))
            return redirect('evaluation:criterion_list')
    else:
        form = CriterionForm()

    context = {
        'form': form,
        'is_create': True,
    }
    return render(request, 'evaluation/criterion_form.html', context)

@login_required
@permission_required('evaluation.change_evaluationcriterion')
def criterion_edit(request, pk):
    """تعديل معيار تقييم"""
    criterion = get_object_or_404(EvaluationCriterion, pk=pk)

    if request.method == 'POST':
        form = CriterionForm(request.POST, instance=criterion)
        if form.is_valid():
            form.save()
            messages.success(request, _("تم تحديث المعيار بنجاح"))
            return redirect('evaluation:criterion_list')
    else:
        form = CriterionForm(instance=criterion)

    context = {
        'form': form,
        'criterion': criterion,
        'is_create': False,
    }
    return render(request, 'evaluation/criterion_form.html', context)

@login_required
@permission_required('evaluation.delete_evaluationcriterion')
def criterion_delete(request, pk):
    """حذف معيار تقييم"""
    criterion = get_object_or_404(EvaluationCriterion, pk=pk)

    if request.method == 'POST':
        criterion.delete()
        messages.success(request, _("تم حذف المعيار بنجاح"))
        return redirect('evaluation:criterion_list')

    context = {
        'criterion': criterion,
    }
    return render(request, 'evaluation/criterion_confirm_delete.html', context)

# ============ جولات التقييم ============

@login_required
@permission_required('evaluation.view_evaluationround')
def round_list(request):
    """عرض قائمة جولات التقييم"""
    rounds = EvaluationRound.objects.all().order_by('-start_date')

    # ترقيم الصفحات
    paginator = Paginator(rounds, 10)
    page = request.GET.get('page')
    try:
        rounds_page = paginator.page(page)
    except PageNotAnInteger:
        rounds_page = paginator.page(1)
    except EmptyPage:
        rounds_page = paginator.page(paginator.num_pages)

    context = {
        'rounds': rounds_page,
    }
    return render(request, 'evaluation/round_list.html', context)

@login_required
@permission_required('evaluation.view_evaluationround')
def round_detail(request, pk):
    """عرض تفاصيل جولة تقييم"""
    evaluation_round = get_object_or_404(EvaluationRound, pk=pk)

    # الطلبات التي تم تقييمها في هذه الجولة
    evaluations = ApplicationEvaluation.objects.filter(evaluation_round=evaluation_round)

    # الإحصائيات
    total_evaluations = evaluations.count()
    completed_evaluations = evaluations.filter(is_submitted=True).count()

    if total_evaluations > 0:
        completion_rate = (completed_evaluations / total_evaluations) * 100
    else:
        completion_rate = 0

    # عدد التقييمات لكل طلب
    application_stats = evaluations.values('application').annotate(
        total_evaluations=Count('id'),
        completed_evaluations=Count('id', filter=Q(is_submitted=True))
    )

    context = {
        'evaluation_round': evaluation_round,
        'evaluations': evaluations,
        'total_evaluations': total_evaluations,
        'completed_evaluations': completed_evaluations,
        'completion_rate': completion_rate,
        'application_stats': application_stats,
    }
    return render(request, 'evaluation/round_detail.html', context)

@login_required
@permission_required('evaluation.add_evaluationround')
def round_create(request):
    """إنشاء جولة تقييم جديدة"""
    if request.method == 'POST':
        form = EvaluationRoundForm(request.POST)
        if form.is_valid():
            evaluation_round = form.save()
            messages.success(request, _("تم إنشاء جولة التقييم بنجاح"))
            return redirect('evaluation:round_detail', pk=evaluation_round.pk)
    else:
        form = EvaluationRoundForm()

    context = {
        'form': form,
        'is_create': True,
    }
    return render(request, 'evaluation/round_form.html', context)

@login_required
@permission_required('evaluation.change_evaluationround')
def round_edit(request, pk):
    """تعديل جولة تقييم"""
    evaluation_round = get_object_or_404(EvaluationRound, pk=pk)

    if request.method == 'POST':
        form = EvaluationRoundForm(request.POST, instance=evaluation_round)
        if form.is_valid():
            form.save()
            messages.success(request, _("تم تحديث جولة التقييم بنجاح"))
            return redirect('evaluation:round_detail', pk=evaluation_round.pk)
    else:
        form = EvaluationRoundForm(instance=evaluation_round)

    context = {
        'form': form,
        'evaluation_round': evaluation_round,
        'is_create': False,
    }
    return render(request, 'evaluation/round_form.html', context)

@login_required
@permission_required('evaluation.delete_evaluationround')
def round_delete(request, pk):
    """حذف جولة تقييم"""
    evaluation_round = get_object_or_404(EvaluationRound, pk=pk)

    if request.method == 'POST':
        evaluation_round.delete()
        messages.success(request, _("تم حذف جولة التقييم بنجاح"))
        return redirect('evaluation:round_list')

    context = {
        'evaluation_round': evaluation_round,
    }
    return render(request, 'evaluation/round_confirm_delete.html', context)

@login_required
@permission_required('evaluation.change_evaluationround')
def round_assign_applications(request, pk):
    """تعيين طلبات للتقييم في جولة معينة"""
    evaluation_round = get_object_or_404(EvaluationRound, pk=pk)

    if request.method == 'POST':
        form = RoundAssignApplicationsForm(request.POST, round_id=pk)
        if form.is_valid():
            applications = form.cleaned_data['applications']

            # إنشاء تقييمات لكل عضو في اللجنة ولكل طلب
            committee_members = evaluation_round.committee.members.all()
            for application in applications:
                for member in committee_members:
                    # تجنب إنشاء تقييمات مكررة
                    evaluation, created = ApplicationEvaluation.objects.get_or_create(
                        application=application,
                        evaluation_round=evaluation_round,
                        evaluator=member,
                        defaults={'is_submitted': False}
                    )

            messages.success(request, _(f"تم تعيين {len(applications)} طلب للتقييم بنجاح"))
            return redirect('evaluation:round_detail', pk=evaluation_round.pk)
    else:
        form = RoundAssignApplicationsForm(round_id=pk)

    context = {
        'form': form,
        'evaluation_round': evaluation_round,
    }
    return render(request, 'evaluation/round_assign_applications.html', context)

# ============ تقييم الطلبات ============

@login_required
def evaluator_dashboard(request):
    """لوحة تحكم المقيّم"""
    # التقييمات المسندة للمستخدم الحالي
    pending_evaluations = ApplicationEvaluation.objects.filter(
        evaluator=request.user,
        is_submitted=False,
        evaluation_round__end_date__gte=timezone.now()
    ).order_by('evaluation_round__end_date')

    completed_evaluations = ApplicationEvaluation.objects.filter(
        evaluator=request.user,
        is_submitted=True
    ).order_by('-evaluation_date')[:10]

    # اللجان التي المستخدم عضو فيها
    committees = Committee.objects.filter(members=request.user)

    # جولات التقييم الحالية
    active_rounds = EvaluationRound.objects.filter(
        committee__members=request.user,
        start_date__lte=timezone.now(),
        end_date__gte=timezone.now()
    )

    context = {
        'pending_evaluations': pending_evaluations,
        'completed_evaluations': completed_evaluations,
        'committees': committees,
        'active_rounds': active_rounds,
    }
    return render(request, 'evaluation/evaluator_dashboard.html', context)

@login_required
def committee_dashboard(request):
    """لوحة تحكم اللجنة - للمشرفين على اللجان"""
    # اللجان التي المستخدم عضو فيها
    committees = Committee.objects.filter(members=request.user)

    # التقييمات التي تمت في اللجان التي المستخدم عضو فيها
    if committees.exists():
        recent_evaluations = ApplicationEvaluation.objects.filter(
            evaluation_round__committee__in=committees,
            is_submitted=True
        ).order_by('-evaluation_date')[:10]

        rounds = EvaluationRound.objects.filter(committee__in=committees).order_by('-start_date')
        active_rounds = rounds.filter(
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        )

        evaluations_needed = ApplicationEvaluation.objects.filter(
            evaluation_round__committee__in=committees,
            is_submitted=False,
            evaluation_round__end_date__gte=timezone.now()
        ).count()
    else:
        recent_evaluations = []
        rounds = []
        active_rounds = []
        evaluations_needed = 0

    context = {
        'committees': committees,
        'recent_evaluations': recent_evaluations,
        'rounds': rounds,
        'active_rounds': active_rounds,
        'evaluations_needed': evaluations_needed,
    }
    return render(request, 'evaluation/committee_dashboard.html', context)

@login_required
def evaluate_application(request, pk):
    """تقييم طلب ابتعاث"""
    evaluation = get_object_or_404(
        ApplicationEvaluation,
        pk=pk,
        evaluator=request.user
    )

    # نموذج التقييم العام
    if request.method == 'POST':
        form = ApplicationEvaluationForm(request.POST, instance=evaluation)

        # إعداد formset لمعايير التقييم
        CriterionScoreFormSet = inlineformset_factory(
            ApplicationEvaluation,
            CriterionScore,
            form=CriterionScoreForm,
            extra=0,
            can_delete=False
        )
        formset = CriterionScoreFormSet(request.POST, instance=evaluation)

        if form.is_valid() and formset.is_valid():
            evaluation = form.save(commit=False)
            formset.save()  # حفظ درجات المعايير

            # التحقق من أن جميع المعايير تم تقييمها إذا تم تقديم التقييم
            if evaluation.is_submitted:
                criteria_count = evaluation.evaluation_round.criteria.count()
                scores_count = evaluation.criteria_scores.count()

                if scores_count < criteria_count:
                    messages.error(request, _("يجب تقييم جميع المعايير قبل تقديم التقييم"))
                    evaluation.is_submitted = False
                else:
                    messages.success(request, _("تم تقديم التقييم بنجاح"))
            else:
                messages.success(request, _("تم حفظ التقييم كمسودة"))

            evaluation.save()

            if evaluation.is_submitted:
                return redirect('evaluation:evaluator_dashboard')
            else:
                return redirect('evaluation:evaluate_application', pk=evaluation.pk)
    else:
        form = ApplicationEvaluationForm(instance=evaluation)

        # إعداد/إنشاء نماذج تقييم المعايير
        criteria = evaluation.evaluation_round.criteria.all()

        # إنشاء نموذج لكل معيار إذا لم يكن موجوداً بالفعل
        for criterion in criteria:
            CriterionScore.objects.get_or_create(
                evaluation=evaluation,
                criterion=criterion,
                defaults={'score': 0}
            )

        # إعداد formset
        CriterionScoreFormSet = inlineformset_factory(
            ApplicationEvaluation,
            CriterionScore,
            form=CriterionScoreForm,
            extra=0,
            can_delete=False
        )
        formset = CriterionScoreFormSet(instance=evaluation)

    # الحصول على معلومات الطلب
    application = evaluation.application
    documents = application.documents.all()

    context = {
        'evaluation': evaluation,
        'form': form,
        'formset': formset,
        'application': application,
        'documents': documents,
    }
    return render(request, 'evaluation/evaluate_application.html', context)

@login_required
@permission_required('evaluation.view_applicationevaluation')
def evaluation_list(request):
    """عرض قائمة التقييمات"""
    if request.user.has_perm('evaluation.view_all_evaluations'):
        # يستطيع المسؤولون مشاهدة جميع التقييمات
        evaluations = ApplicationEvaluation.objects.all()
    else:
        # يستطيع المستخدمون العاديون مشاهدة تقييماتهم فقط
        evaluations = ApplicationEvaluation.objects.filter(evaluator=request.user)

    evaluations = evaluations.order_by('-evaluation_date')

    # ترقيم الصفحات
    paginator = Paginator(evaluations, 10)
    page = request.GET.get('page')
    try:
        evaluations_page = paginator.page(page)
    except PageNotAnInteger:
        evaluations_page = paginator.page(1)
    except EmptyPage:
        evaluations_page = paginator.page(paginator.num_pages)

    context = {
        'evaluations': evaluations_page,
    }
    return render(request, 'evaluation/evaluation_list.html', context)

@login_required
@permission_required('evaluation.view_applicationevaluation')
def evaluation_detail(request, pk):
    """عرض تفاصيل تقييم"""
    # المستخدم يستطيع مشاهدة تقييمه فقط أو إذا كان مسؤولاً
    if request.user.has_perm('evaluation.view_all_evaluations'):
        evaluation = get_object_or_404(ApplicationEvaluation, pk=pk)
    else:
        evaluation = get_object_or_404(ApplicationEvaluation, pk=pk, evaluator=request.user)

    criteria_scores = evaluation.criteria_scores.all().order_by('criterion__order')

    context = {
        'evaluation': evaluation,
        'criteria_scores': criteria_scores,
    }
    return render(request, 'evaluation/evaluation_detail.html', context)

# ============ التصويت ============

@login_required
def vote_create(request, application_id):
    """التصويت على طلب"""
    application = get_object_or_404(Application, pk=application_id)

    # التحقق من أن المستخدم عضو في لجنة
    user_committees = Committee.objects.filter(members=request.user)
    if not user_committees.exists():
        messages.error(request, _("يجب أن تكون عضواً في لجنة للتصويت"))
        return redirect('applications:application_detail', application_id=application_id)

    # التحقق من أنه لم يصوت سابقاً
    vote = Vote.objects.filter(application=application, committee_member=request.user).first()

    if request.method == 'POST':
        form = VoteForm(request.POST, instance=vote)
        if form.is_valid():
            vote = form.save(commit=False)
            vote.application = application
            vote.committee_member = request.user
            vote.save()
            messages.success(request, _("تم تسجيل تصويتك بنجاح"))
            return redirect('applications:application_detail', application_id=application_id)
    else:
        form = VoteForm(instance=vote)

    context = {
        'form': form,
        'application': application,
    }
    return render(request, 'evaluation/vote_form.html', context)

@login_required
@permission_required('evaluation.view_vote')
def vote_list(request):
    """عرض قائمة التصويتات"""
    votes = Vote.objects.all().order_by('-vote_date')

    # ترقيم الصفحات
    paginator = Paginator(votes, 10)
    page = request.GET.get('page')
    try:
        votes_page = paginator.page(page)
    except PageNotAnInteger:
        votes_page = paginator.page(1)
    except EmptyPage:
        votes_page = paginator.page(paginator.num_pages)

    context = {
        'votes': votes_page,
    }
    return render(request, 'evaluation/vote_list.html', context)

# ============ التوصيات ============

@login_required
@permission_required('evaluation.view_recommendation')
def recommendation_list(request):
    """عرض قائمة التوصيات"""
    recommendations = Recommendation.objects.all().order_by('-recommendation_date')

    # ترقيم الصفحات
    paginator = Paginator(recommendations, 10)
    page = request.GET.get('page')
    try:
        recommendations_page = paginator.page(page)
    except PageNotAnInteger:
        recommendations_page = paginator.page(1)
    except EmptyPage:
        recommendations_page = paginator.page(paginator.num_pages)

    context = {
        'recommendations': recommendations_page,
    }
    return render(request, 'evaluation/recommendation_list.html', context)

@login_required
@permission_required('evaluation.view_recommendation')
def recommendation_detail(request, pk):
    """عرض تفاصيل توصية"""
    recommendation = get_object_or_404(Recommendation, pk=pk)

    context = {
        'recommendation': recommendation,
    }
    return render(request, 'evaluation/recommendation_detail.html', context)

@login_required
@permission_required('evaluation.add_recommendation')
def recommendation_create(request, application_id):
    """إنشاء توصية لطلب"""
    application = get_object_or_404(Application, pk=application_id)

    # التحقق من أن المستخدم عضو في لجنة
    user_committees = Committee.objects.filter(members=request.user)
    if not user_committees.exists():
        messages.error(request, _("يجب أن تكون عضواً في لجنة لتقديم توصية"))
        return redirect('applications:application_detail', application_id=application_id)

    if request.method == 'POST':
        form = RecommendationForm(request.POST)
        if form.is_valid():
            recommendation = form.save(commit=False)
            recommendation.application = application
            recommendation.committee = user_committees.first()  # استخدام أول لجنة المستخدم عضو فيها
            recommendation.created_by = request.user
            recommendation.save()
            messages.success(request, _("تم تقديم التوصية بنجاح"))
            return redirect('applications:application_detail', application_id=application_id)
    else:
        form = RecommendationForm()

    context = {
        'form': form,
        'application': application,
    }
    return render(request, 'evaluation/recommendation_form.html', context)