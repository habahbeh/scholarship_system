from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView, PasswordResetView, PasswordResetConfirmView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy
from .forms import (
    UserLoginForm, UserRegisterForm, UserUpdateForm, ProfileUpdateForm,
    CustomPasswordChangeForm, CustomPasswordResetForm, CustomSetPasswordForm
)
from .models import Profile

class CustomLoginView(LoginView):
    """وجهة عرض تسجيل الدخول"""
    form_class = UserLoginForm
    template_name = 'accounts/login.html'

    def form_valid(self, form):
        messages.success(self.request, _("تم تسجيل الدخول بنجاح"))
        return super().form_valid(form)

class CustomLogoutView(LogoutView):
    """وجهة عرض تسجيل الخروج"""
    next_page = reverse_lazy('home')
    template_name = 'accounts/logout.html'

    # Allow both GET and POST
    http_method_names = ['get', 'post']

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, _("تم تسجيل الخروج بنجاح"))
        return super().dispatch(request, *args, **kwargs)

def register_view(request):
    """وجهة عرض التسجيل"""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            messages.success(request, _("تم إنشاء الحساب بنجاح. يمكنك الآن تسجيل الدخول."))
            return redirect('accounts:login')
    else:
        form = UserRegisterForm()

    return render(request, 'accounts/register.html', {'form': form})

@login_required
def profile_view(request):
    """وجهة عرض الملف الشخصي"""
    return render(request, 'accounts/profile.html', {'profile': request.user.profile})

@login_required
def profile_edit_view(request):
    """وجهة عرض تعديل الملف الشخصي"""
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, _("تم تحديث الملف الشخصي بنجاح"))
            return redirect('accounts:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'user_form': user_form,
        'form': profile_form
    }
    return render(request, 'accounts/profile_edit.html', context)

class CustomPasswordChangeView(PasswordChangeView):
    """وجهة عرض تغيير كلمة المرور"""
    form_class = CustomPasswordChangeForm
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:profile')

    def form_valid(self, form):
        messages.success(self.request, _("تم تغيير كلمة المرور بنجاح"))
        return super().form_valid(form)

class CustomPasswordResetView(PasswordResetView):
    """وجهة عرض إعادة تعيين كلمة المرور"""
    form_class = CustomPasswordResetForm
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'  # تصحيح مسار القالب
    subject_template_name = 'emails/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """وجهة عرض تأكيد إعادة تعيين كلمة المرور"""
    form_class = CustomSetPasswordForm
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        messages.success(self.request, _("تم إعادة تعيين كلمة المرور بنجاح. يمكنك الآن تسجيل الدخول."))
        return super().form_valid(form)