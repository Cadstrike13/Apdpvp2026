"""
Admin de validation agent : chaque constat affiche sa qualification en ligne
(analyse, conformité, criticité, suite proposée, validation).
"""

from django.contrib import admin, messages
from django.contrib.contenttypes.admin import GenericStackedInline

from core.audit import journaliser

from .models import (
    MissionControleEnLigne, MembreControleEnLigne, EnvironnementControle, PageIdentifiee,
    Qualification, ConstatDonnees, ConstatInformation, ConstatCookie, ConstatConsentement,
    ConstatFormulaire, ConstatCompte, ConstatSecurite, ConstatLegal, ConstatDroits,
    ConstatTiers, ScenarioTest, PreuveCapture, SuiviCorrectif,
)


# ---------------------------------------------------------------------------
# Qualification
# ---------------------------------------------------------------------------

class QualificationInline(GenericStackedInline):
    model = Qualification
    extra = 1
    max_num = 1
    can_delete = False
    fields = (
        "reference_grille", "analyse", ("conformite", "criticite"), "suite_proposee",
        "commentaire_agent", ("valide_par_agent", "agent"), "date_validation",
    )
    readonly_fields = ("date_validation",)


def _journaliser_qualifications(request, formset):
    """Trace au journal chaque qualification enregistrée depuis l'admin."""
    for objet in formset.new_objects + [o for o, _ in formset.changed_objects]:
        if not isinstance(objet, Qualification):
            continue
        agent = getattr(request.user, "agent", None)
        action = "validation" if objet.valide_par_agent else "qualification"
        journaliser(action, objet, acteur=agent,
                    description=f"{objet.get_conformite_display() or '—'} / {objet.get_criticite_display() or '—'}")


class ConstatAdmin(admin.ModelAdmin):
    inlines = [QualificationInline]
    list_display = ("__str__", "mission", "etat_qualification")
    list_filter = ("mission",)

    @admin.display(description="Qualification")
    def etat_qualification(self, obj):
        q = obj.qualification
        if q is None:
            return "À qualifier"
        return "Validée" if q.valide_par_agent else "En cours"

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, Qualification) and not instance.mission_id:
                instance.mission_id = form.instance.mission_id
        formset.save()
        _journaliser_qualifications(request, formset)


@admin.register(Qualification)
class QualificationAdmin(admin.ModelAdmin):
    list_display = ("reference_grille", "constat", "conformite", "criticite", "valide_par_agent", "agent", "mission")
    list_filter = ("valide_par_agent", "conformite", "criticite", "mission")
    search_fields = ("reference_grille", "analyse", "commentaire_agent")
    readonly_fields = ("content_type", "object_id", "mission", "date_validation", "date_creation", "date_modification")

    def has_add_permission(self, request):
        return False  # une qualification se crée depuis son constat


# ---------------------------------------------------------------------------
# Constats
# ---------------------------------------------------------------------------

@admin.register(ConstatCookie)
class ConstatCookieAdmin(ConstatAdmin):
    list_display = ("nom", "domaine", "scenario", "type_traceur", "type_brut", "est_tiers", "duree_vie_jours", "etat_qualification")
    list_filter = ("scenario", "type_traceur", "est_tiers", "mission")
    search_fields = ("nom", "domaine", "type_brut")


@admin.register(ConstatTiers)
class ConstatTiersAdmin(ConstatAdmin):
    list_display = ("domaine_tiers", "categorie", "declare_dans_politique", "origine", "etat_qualification")
    list_filter = ("categorie", "declare_dans_politique", "mission")


for _modele in (
    ConstatDonnees, ConstatInformation, ConstatConsentement, ConstatFormulaire,
    ConstatCompte, ConstatSecurite, ConstatLegal, ConstatDroits,
):
    admin.site.register(_modele, ConstatAdmin)


# ---------------------------------------------------------------------------
# Mission
# ---------------------------------------------------------------------------

class MembreInline(admin.TabularInline):
    model = MembreControleEnLigne
    extra = 1


class EnvironnementInline(admin.StackedInline):
    model = EnvironnementControle
    extra = 0
    max_num = 1


class PageInline(admin.TabularInline):
    model = PageIdentifiee
    extra = 0
    fields = ("type_page", "url", "presente", "origine", "indice")


@admin.register(MissionControleEnLigne)
class MissionAdmin(admin.ModelAdmin):
    list_display = ("nom_service", "responsable_traitement", "niveau_controle", "statut", "avancement_validation", "date_lancement")
    list_filter = ("statut", "niveau_controle", "origine_controle")
    search_fields = ("nom_service", "url_principale", "responsable_traitement__raison_sociale")
    readonly_fields = ("date_lancement", "erreurs_scan", "avancement_validation")
    inlines = [MembreInline, EnvironnementInline, PageInline]
    actions = ["lancer_scans"]

    @admin.display(description="Constats validés")
    def avancement_validation(self, obj):
        valides, total = obj.bilan_validation()
        return f"{valides} / {total}" if total else "Aucun constat"

    @admin.action(description="Lancer les scans automatiques")
    def lancer_scans(self, request, queryset):
        from .tasks import lancer_scans_automatiques

        for mission in queryset:
            lancer_scans_automatiques.delay(mission.pk)
        self.message_user(request, f"Scans lancés pour {queryset.count()} mission(s).", messages.SUCCESS)


@admin.register(PreuveCapture)
class PreuveAdmin(admin.ModelAdmin):
    list_display = ("horodatage", "mission", "type_preuve", "scenario_lie", "outil_technique", "empreinte_courte")
    list_filter = ("type_preuve", "genere_automatiquement", "mission")
    readonly_fields = ("empreinte_sha256", "horodatage")

    @admin.display(description="SHA-256")
    def empreinte_courte(self, obj):
        return f"{obj.empreinte_sha256[:12]}…" if obj.empreinte_sha256 else "—"

    def has_change_permission(self, request, obj=None):
        return False  # une preuve ne se modifie pas


admin.site.register(ScenarioTest)
admin.site.register(SuiviCorrectif)
