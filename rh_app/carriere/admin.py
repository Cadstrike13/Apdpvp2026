from django.contrib import admin

from core.admin import SoftDeleteAdmin
from .models import Avancement


@admin.register(Avancement)
class AvancementAdmin(SoftDeleteAdmin):
    list_display = ("employe", "ancienne_categorie", "nouvelle_categorie", "date_effet", "reference", "is_deleted")
    list_filter = ("is_deleted", "nouvelle_categorie")
    search_fields = ("employe__nom", "employe__prenom", "reference")
