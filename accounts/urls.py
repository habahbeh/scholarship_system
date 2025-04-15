from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import ajax

app_name = 'accounts'

urlpatterns = [
    # تسجيل الدخول والخروج
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(template_name='accounts/logout.html'), name='logout'),
    path('register/', views.register_view, name='register'),

    # الملف الشخصي
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),

    # تغيير كلمة المرور
    path('password/change/', views.CustomPasswordChangeView.as_view(), name='password_change'),

    # إعادة تعيين كلمة المرور
    path('password/reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password/reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path('password/reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    path('password/reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),

    # AJAX endpoints
    path('ajax/get-departments/', ajax.get_departments, name='get_departments'),
]