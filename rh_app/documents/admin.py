from django.contrib import admin

from core.admin import SoftDeleteAdmin
from .models import Document


@admin.register(Document)
class DocumentAdmin(SoftDeleteAdmin):
    list_display = ("nom", "categorie", "uploade_par", "date_upload", "is_deleted")
    list_filter = ("is_deleted", "categorie")
    filter_horizontal = ("acces_employes",)
