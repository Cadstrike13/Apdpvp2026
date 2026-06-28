from django.contrib import admin

from core.admin import SoftDeleteAdmin
from .models import ActeAdministratif


@admin.register(ActeAdministratif)
class ActeAdministratifAdmin(SoftDeleteAdmin):
    list_display = ("reference", "type_acte", "employe", "objet", "date_acte", "statut", "is_deleted")
    list_filter = ("is_deleted", "type_acte", "statut")
    search_fields = ("reference", "objet", "employe__nom", "employe__prenom")
