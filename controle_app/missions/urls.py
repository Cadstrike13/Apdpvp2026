from django.urls import path

from . import views

app_name = "missions"

urlpatterns = [
    path("", views.mission_list, name="mission_list"),
    path("tableau-de-bord/", views.dashboard, name="dashboard"),
    path("nouvelle/", views.mission_create, name="mission_create"),
    path("<int:mission_pk>/", views.mission_detail, name="mission_detail"),
    path("<int:mission_pk>/entites/ajouter/", views.entite_ajouter, name="entite_ajouter"),
    path("controles/<int:controle_pk>/", views.controle_entite_detail, name="controle_entite_detail"),
    path("controles/<int:controle_pk>/membres/ajouter/", views.membre_ajouter, name="membre_ajouter"),
    path("controles/<int:controle_pk>/personnes/ajouter/", views.personne_ajouter, name="personne_ajouter"),
    path(
        "controles/<int:controle_pk>/questionnaire/traitements-declares/",
        views.questionnaire_checklist, name="questionnaire_checklist",
    ),
    path("controles/<int:controle_pk>/questionnaire/<int:page>/", views.questionnaire_page, name="questionnaire_page"),
    path("controles/<int:controle_pk>/observations/modifier/", views.observations_modifier, name="observations_modifier"),
    path("controles/<int:controle_pk>/infos-pv/modifier/", views.infos_pv_modifier, name="infos_pv_modifier"),
    path("controles/<int:controle_pk>/evaluation/", views.evaluation_page, name="evaluation_page"),
    path("controles/<int:controle_pk>/pv/marquer-genere/", views.pv_marquer_genere, name="pv_marquer_genere"),
    path("controles/<int:controle_pk>/scan/uploader/", views.scan_uploader, name="scan_uploader"),
    path("controles/<int:controle_pk>/rapport/marquer-genere/", views.rapport_marquer_genere, name="rapport_marquer_genere"),
    path("controles/<int:controle_pk>/rapport/uploader/", views.rapport_uploader, name="rapport_uploader"),
    path("controles/<int:controle_pk>/valider/", views.controle_valider, name="controle_valider"),
]
