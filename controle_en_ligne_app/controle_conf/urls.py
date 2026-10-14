from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

admin.site.site_header = "APDPVP — Contrôle en ligne"
admin.site.site_title = "Contrôle en ligne"
admin.site.index_title = "Missions, constats et qualifications"

urlpatterns = [
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
