from django.contrib import admin

from core.admin import SoftDeleteAdmin
from .models import (
    Department, CategorieProfessionnelle, StatutAgent, Poste, TypeContrat,
    Employee, Diplome, Contrat, Affectation, Evaluation,
)


@admin.register(Department)
class DepartmentAdmin(SoftDeleteAdmin):
    list_display = ("nom", "is_deleted")
    list_filter = ("is_deleted",)
    search_fields = ("nom",)


@admin.register(CategorieProfessionnelle)
class CategorieProfessionnelleAdmin(SoftDeleteAdmin):
    list_display = ("libelle", "code", "niveau", "is_deleted")
    list_filter = ("is_deleted",)
    search_fields = ("libelle", "code")


@admin.register(StatutAgent)
class StatutAgentAdmin(SoftDeleteAdmin):
    list_display = ("libelle", "code", "is_deleted")
    list_filter = ("is_deleted",)


@admin.register(Poste)
class PosteAdmin(SoftDeleteAdmin):
    list_display = ("intitule", "departement", "is_deleted")
    list_filter = ("is_deleted", "departement")
    search_fields = ("intitule",)


@admin.register(TypeContrat)
class TypeContratAdmin(SoftDeleteAdmin):
    list_display = ("libelle", "code", "is_deleted")
    list_filter = ("is_deleted",)


class DiplomeInline(admin.TabularInline):
    model = Diplome
    extra = 0


class ContratInline(admin.TabularInline):
    model = Contrat
    extra = 0
    fk_name = "employe"


class AffectationInline(admin.TabularInline):
    model = Affectation
    extra = 0


class EvaluationInline(admin.TabularInline):
    model = Evaluation
    extra = 0
    fk_name = "employe"


@admin.register(Employee)
class EmployeeAdmin(SoftDeleteAdmin):
    list_display = ("nom", "prenom", "email", "matricule_apdpvp", "categorie",
                    "statut_agent", "user", "departement", "is_deleted")
    list_filter = ("is_deleted", "statut", "statut_agent", "categorie", "departement")
    search_fields = ("nom", "prenom", "email", "matricule_cnss", "matricule_cnamgs", "matricule_apdpvp")
    raw_id_fields = ("user",)
    inlines = [AffectationInline, ContratInline, DiplomeInline, EvaluationInline]


@admin.register(Diplome)
class DiplomeAdmin(SoftDeleteAdmin):
    list_display = ("intitule", "employe", "etablissement", "annee", "is_deleted")
    list_filter = ("is_deleted",)
    search_fields = ("intitule", "employe__nom", "employe__prenom")


@admin.register(Contrat)
class ContratAdmin(SoftDeleteAdmin):
    list_display = ("employe", "type_contrat", "reference", "date_debut", "date_fin", "is_deleted")
    list_filter = ("is_deleted", "type_contrat")


@admin.register(Affectation)
class AffectationAdmin(SoftDeleteAdmin):
    list_display = ("employe", "poste", "date_debut", "date_fin", "principal", "is_deleted")
    list_filter = ("is_deleted", "principal", "poste")


@admin.register(Evaluation)
class EvaluationAdmin(SoftDeleteAdmin):
    list_display = ("employe", "date_evaluation", "note", "evaluateur", "is_deleted")
    list_filter = ("is_deleted",)
