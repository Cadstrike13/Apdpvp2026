from django.contrib import admin

from .models import (
    JournalAction,
    MembreGroupeControle,
    MissionControle,
    PersonneInterrogee,
    ReponsePage1,
    ReponsePage2,
    ReponsePage3,
    ReponsePage4,
    ReponsePage5,
    ReponseTraitement,
)


class MembreGroupeControleInline(admin.TabularInline):
    model = MembreGroupeControle
    extra = 0


class PersonneInterrogeeInline(admin.TabularInline):
    model = PersonneInterrogee
    extra = 0


class JournalActionInline(admin.TabularInline):
    model = JournalAction
    extra = 0
    readonly_fields = ("utilisateur", "type_action", "details", "horodatage")
    can_delete = False


@admin.register(MissionControle)
class MissionControleAdmin(admin.ModelAdmin):
    list_display = ("entite_controlee", "date_mission", "statut", "est_verrouillee", "est_supprime")
    list_filter = ("statut", "entite_controlee")
    inlines = [MembreGroupeControleInline, PersonneInterrogeeInline, JournalActionInline]


class ReponsePageInline(admin.StackedInline):
    extra = 0
    max_num = 1
    can_delete = False


class ReponsePage1Inline(ReponsePageInline):
    model = ReponsePage1


class ReponsePage2Inline(ReponsePageInline):
    model = ReponsePage2


class ReponsePage3Inline(ReponsePageInline):
    model = ReponsePage3


class ReponsePage4Inline(ReponsePageInline):
    model = ReponsePage4


class ReponsePage5Inline(ReponsePageInline):
    model = ReponsePage5


@admin.register(ReponseTraitement)
class ReponseTraitementAdmin(admin.ModelAdmin):
    list_display = ("mission", "traitement", "est_verrouille")
    list_filter = ("traitement",)
    inlines = [
        ReponsePage1Inline, ReponsePage2Inline, ReponsePage3Inline, ReponsePage4Inline, ReponsePage5Inline,
    ]


@admin.register(JournalAction)
class JournalActionAdmin(admin.ModelAdmin):
    list_display = ("mission", "type_action", "utilisateur", "horodatage")
    list_filter = ("type_action",)
    readonly_fields = ("mission", "utilisateur", "type_action", "details", "horodatage")
