from django.urls import path

from . import views

app_name = "missions"

urlpatterns = [
    path("", views.mission_list, name="mission_list"),
    path("tableau-de-bord/", views.dashboard, name="dashboard"),
    path("nouvelle/", views.mission_create, name="mission_create"),
    path("<int:mission_pk>/", views.mission_detail, name="mission_detail"),
    path("<int:mission_pk>/membres/ajouter/", views.membre_ajouter, name="membre_ajouter"),
    path("<int:mission_pk>/personnes/ajouter/", views.personne_ajouter, name="personne_ajouter"),
    path(
        "<int:mission_pk>/questionnaire/traitements-declares/",
        views.questionnaire_checklist, name="questionnaire_checklist",
    ),
    path("<int:mission_pk>/questionnaire/<int:page>/", views.questionnaire_page, name="questionnaire_page"),
    path("<int:mission_pk>/observations/modifier/", views.observations_modifier, name="observations_modifier"),
    path("<int:mission_pk>/infos-pv/modifier/", views.infos_pv_modifier, name="infos_pv_modifier"),
    path("<int:mission_pk>/evaluation/", views.evaluation_page, name="evaluation_page"),
    path("<int:mission_pk>/pv/marquer-genere/", views.pv_marquer_genere, name="pv_marquer_genere"),
    path("<int:mission_pk>/scan/uploader/", views.scan_uploader, name="scan_uploader"),
    path("<int:mission_pk>/rapport/marquer-genere/", views.rapport_marquer_genere, name="rapport_marquer_genere"),
    path("<int:mission_pk>/rapport/uploader/", views.rapport_uploader, name="rapport_uploader"),
    path("<int:mission_pk>/valider/", views.mission_valider, name="mission_valider"),
]
