from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.conf.urls.i18n import i18n_patterns

# الصفحة الرئيسية المؤقتة
home_view = TemplateView.as_view(template_name='home.html')

# URLs غير المترجمة
urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),  # لتبديل اللغات
]

# URLs المترجمة
urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', home_view, name='home'),
    path('', include('announcements.urls')),
    path('', include('applications.urls')),
    path('evaluation/', include('evaluation.urls')),
    path('dashboard/', include('dashboard.urls')),
    # ستضاف المزيد من التطبيقات لاحقاً
    prefix_default_language=False
)

# إضافة URLs للوسائط والملفات الثابتة في وضع التطوير
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)