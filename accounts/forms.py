from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm, PasswordResetForm, \
    SetPasswordForm
from django.utils.translation import gettext_lazy as _
from .models import Profile, Faculty, Department


class UserLoginForm(AuthenticationForm):
    """نموذج تسجيل الدخول"""
    username = forms.CharField(
        label=_("اسم المستخدم"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('أدخل اسم المستخدم')}),
    )
    password = forms.CharField(
        label=_("كلمة المرور"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('أدخل كلمة المرور')}),
    )


class UserRegisterForm(UserCreationForm):
    """نموذج تسجيل مستخدم جديد"""
    first_name = forms.CharField(
        label=_("الاسم الأول"),
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    last_name = forms.CharField(
        label=_("اسم العائلة"),
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    email = forms.EmailField(
        label=_("البريد الإلكتروني"),
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )
    id_number = forms.CharField(
        label=_("رقم الهوية"),
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    phone_number = forms.CharField(
        label=_("رقم الهاتف"),
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    date_of_birth = forms.DateField(
        label=_("تاريخ الميلاد"),
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    gender = forms.ChoiceField(
        label=_("الجنس"),
        choices=Profile.GENDER_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    faculty = forms.ModelChoiceField(
        label=_("الكلية"),
        queryset=Faculty.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    department = forms.ModelChoiceField(
        label=_("القسم"),
        queryset=Department.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    profile_picture = forms.ImageField(
        label=_("الصورة الشخصية"),
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        """حفظ المستخدم والملف الشخصي"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']

        if commit:
            user.save()
            user.profile.id_number = self.cleaned_data.get('id_number', '')
            user.profile.phone_number = self.cleaned_data.get('phone_number', '')
            user.profile.date_of_birth = self.cleaned_data.get('date_of_birth')
            user.profile.gender = self.cleaned_data.get('gender', 'M')
            user.profile.faculty = self.cleaned_data.get('faculty')
            user.profile.department = self.cleaned_data.get('department')
            user.profile.profile_picture = self.cleaned_data.get('profile_picture')
            user.profile.save()

        return user


class UserUpdateForm(forms.ModelForm):
    """نموذج تحديث بيانات المستخدم"""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
        }


class ProfileUpdateForm(forms.ModelForm):
    """نموذج تحديث بيانات الملف الشخصي"""

    class Meta:
        model = Profile
        fields = ['id_number', 'phone_number', 'date_of_birth', 'gender', 'address',
                  'faculty', 'department', 'academic_rank', 'specialization', 'bio', 'profile_picture']
        widgets = {
            'id_number': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'faculty': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'academic_rank': forms.Select(attrs={'class': 'form-control'}),
            'specialization': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    """نموذج تغيير كلمة المرور"""
    old_password = forms.CharField(
        label=_("كلمة المرور الحالية"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    new_password1 = forms.CharField(
        label=_("كلمة المرور الجديدة"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    new_password2 = forms.CharField(
        label=_("تأكيد كلمة المرور الجديدة"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )


class CustomPasswordResetForm(PasswordResetForm):
    """نموذج إعادة تعيين كلمة المرور"""
    email = forms.EmailField(
        label=_("البريد الإلكتروني"),
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )


class CustomSetPasswordForm(SetPasswordForm):
    """نموذج تعيين كلمة مرور جديدة"""
    new_password1 = forms.CharField(
        label=_("كلمة المرور الجديدة"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    new_password2 = forms.CharField(
        label=_("تأكيد كلمة المرور الجديدة"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )