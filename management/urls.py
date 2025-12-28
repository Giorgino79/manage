"""
URL configuration for management project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("select2/", include("django_select2.urls")),  # django-select2 URLs
    path("dipendenti/", include('dipendenti.urls')),
    path("core/", include('core.urls')),
    path("mail/", include('mail.urls')),  # Sistema Email integrato
    path("anagrafica/", include('anagrafica.urls')),
    path("preventivi/", include('preventivi.urls')),
    path("acquisti/", include('acquisti.urls')),
    path("fatturazione/", include('fatturazione.urls')),
    path("automezzi/", include('automezzi.urls')),
    path("stabilimenti/", include('stabilimenti.urls')),
    path("api/", include('core.urls')),  # API endpoints
    path("", include('dipendenti.urls')),  # Landing page from dipendenti
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
