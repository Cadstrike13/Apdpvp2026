from django.contrib import admin

from .models import Fonction, Personne


class FonctionInline(admin.TabularInline):
    model = Fonction
    extra = 0


@admin.register(Personne)
class PersonneAdmin(admin.ModelAdmin):
    list_display = ("nom", "prenom", "email", "telephone", "est_supprime")
    search_fields = ("nom", "prenom", "email")
    inlines = [FonctionInline]


@admin.register(Fonction)
class FonctionAdmin(admin.ModelAdmin):
    list_display = ("personne", "entite", "poste", "date_debut", "date_fin")
    list_filter = ("entite",)
