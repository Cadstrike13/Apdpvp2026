from django.contrib import admin

from .models import AgentControleur


@admin.register(AgentControleur)
class AgentControleurAdmin(admin.ModelAdmin):
    list_display = ("external_id", "nom", "prenom", "poste", "user", "est_supprime")
    search_fields = ("nom", "prenom", "external_id")
