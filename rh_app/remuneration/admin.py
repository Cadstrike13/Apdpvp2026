from django.contrib import admin

from core.admin import SoftDeleteAdmin
from .models import TauxCotisation, Salaire, Prime, AvanceSalaire, AllocationConge


@admin.register(TauxCotisation)
class TauxCotisationAdmin(SoftDeleteAdmin):
    list_display = ("code", "libelle", "taux_salarial", "taux_patronal", "is_deleted")
    list_filter = ("is_deleted",)


@admin.register(Salaire)
class SalaireAdmin(SoftDeleteAdmin):
    list_display = ("employe", "montant_base", "date_effet", "is_deleted")
    list_filter = ("is_deleted",)
    search_fields = ("employe__nom", "employe__prenom")


@admin.register(Prime)
class PrimeAdmin(SoftDeleteAdmin):
    list_display = ("employe", "libelle", "montant", "date", "imposable", "is_deleted")
    list_filter = ("is_deleted", "imposable")


@admin.register(AvanceSalaire)
class AvanceSalaireAdmin(SoftDeleteAdmin):
    list_display = ("employe", "montant", "date", "rembourse", "is_deleted")
    list_filter = ("is_deleted", "rembourse")


@admin.register(AllocationConge)
class AllocationCongeAdmin(SoftDeleteAdmin):
    list_display = ("employe", "montant", "date", "is_deleted")
    list_filter = ("is_deleted",)
