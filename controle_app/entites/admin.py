from django.contrib import admin

from .models import EntiteControlee


@admin.register(EntiteControlee)
class EntiteControleeAdmin(admin.ModelAdmin):
    list_display = ("nom", "secteur_activite", "est_supprime")
    list_filter = ("secteur_activite",)
    search_fields = ("nom",)
