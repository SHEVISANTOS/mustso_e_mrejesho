from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('feedback/', include('feedback.urls')),
    path('notifications/', include('notifications.urls')),
    path('adminpanel/', include('adminpanel.urls')),
    path('accountability/', include('accountability.urls')),
    path('', RedirectView.as_view(pattern_name='feedback:dashboard', permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
