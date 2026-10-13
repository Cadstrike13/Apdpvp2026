from django.contrib import admin

from .models import AgentProvider, JournalAction, ResponsableTraitement


@admin.register(AgentProvider)
class AgentProviderAdmin(admin.ModelAdmin):
    list_display = ("__str__", "fonction", "email", "actif")
    list_filter = ("actif",)
    search_fields = ("nom", "prenom", "email", "identifiant_sso")


@admin.register(ResponsableTraitement)
class ResponsableTraitementAdmin(admin.ModelAdmin):
    list_display = ("raison_sociale", "sigle", "secteur", "site_web")
    search_fields = ("raison_sociale", "sigle", "site_web")


@admin.register(JournalAction)
class JournalActionAdmin(admin.ModelAdmin):
    list_display = ("horodatage", "action", "acteur", "objet_type", "objet_id")
    list_filter = ("action", "objet_type")
    search_fields = ("description", "objet_id")
    date_hierarchy = "horodatage"

    # Le journal est en lecture seule : il fait foi de ce qui s'est passé.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
