from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Application, Poste, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Informations APDPVP", {"fields": ("avatar", "telephone", "postes")}),
    )
    filter_horizontal = UserAdmin.filter_horizontal + ("postes",)
    list_display = ("username", "first_name", "last_name", "email", "is_staff", "is_superuser")


@admin.register(Poste)
class PosteAdmin(admin.ModelAdmin):
    list_display = ("libelle", "code")
    search_fields = ("libelle", "code")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("nom", "slug", "url", "est_active", "ordre")
    list_editable = ("est_active", "ordre")
    filter_horizontal = ("roles_autorises", "postes_autorises")
    prepopulated_fields = {"slug": ("nom",)}
