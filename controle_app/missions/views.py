import os
import tempfile

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files import File
from django.http import Http404
from django.shortcuts import redirect, render

from core.permissions import require_chef_mission, require_membre_mission
from entites.models import EntiteControlee
from personnes.models import Personne

from .forms import (
    EvaluationFormSet,
    InfosPVForm,
    MembreGroupeControleForm,
    MissionControleForm,
    ObservationsForm,
    Page1FormSet,
    Page2FormSet,
    Page3FormSet,
    Page4FormSet,
    Page5FormSet,
    PersonneInterrogeeForm,
    RapportSigneForm,
    ScanSigneForm,
)
from .generate_pv import generate_pv
from .models import EvaluationConformite, MembreGroupeControle, MissionControle, PersonneInterrogee, \
    ReponsePage1, ReponsePage2, ReponsePage3, ReponsePage4, ReponsePage5, RoleMission, StatutMission, \
    TypeAction, journaliser

QUESTIONNAIRE_PAGES = {
    1: {"model": ReponsePage1, "formset": Page1FormSet, "template": "missions/questionnaire_page1.html"},
    2: {"model": ReponsePage2, "formset": Page2FormSet, "template": "missions/questionnaire_page2.html"},
    3: {"model": ReponsePage3, "formset": Page3FormSet, "template": "missions/questionnaire_page3.html"},
    4: {"model": ReponsePage4, "formset": Page4FormSet, "template": "missions/questionnaire_page4.html"},
    5: {"model": ReponsePage5, "formset": Page5FormSet, "template": "missions/questionnaire_page5.html"},
}


def _erreurs_en_message(form):
    return "; ".join(f"{champ} : {', '.join(erreurs)}" for champ, erreurs in form.errors.items())


@login_required
def mission_list(request):
    missions = MissionControle.objects.select_related("entite_controlee").order_by("-date_mission")
    return render(request, "missions/mission_list.html", {"missions": missions})


@login_required
def mission_create(request):
    if request.method == "POST":
        form = MissionControleForm(request.POST)
        if form.is_valid():
            entite = form.cleaned_data["entite_controlee"]
            if not entite:
                entite = EntiteControlee.objects.create(nom=form.cleaned_data["nom_nouvelle_entite"])
            mission = MissionControle.objects.create(
                entite_controlee=entite,
                date_mission=form.cleaned_data["date_mission"],
                commentaires_observations=form.cleaned_data["commentaires_observations"],
            )
            journaliser(mission, request.user, TypeAction.CREATION)
            return redirect("missions:mission_detail", mission_pk=mission.pk)
    else:
        form = MissionControleForm()
    return render(request, "missions/mission_form.html", {"form": form})


@require_membre_mission
def mission_detail(request, mission_pk):
    mission = request.mission
    est_chef = request.user.is_superuser or mission.membres_groupe.chefs().filter(agent__user=request.user).exists()
    reponses = mission.reponses.select_related("page1", "page2", "page3", "page4", "page5")
    return render(
        request,
        "missions/mission_detail.html",
        {
            "mission": mission,
            "reponses": reponses,
            "membre_form": MembreGroupeControleForm(),
            "personne_form": PersonneInterrogeeForm(),
            "observations_form": ObservationsForm(instance=mission),
            "infos_pv_form": InfosPVForm(instance=mission),
            "page_range": range(1, 6),
            "est_chef": est_chef,
            "peut_marquer_pv_genere": est_chef and StatutMission.QUESTIONNAIRE_COMPLETE <= mission.statut < StatutMission.PV_GENERE,
            "peut_uploader_scan": est_chef and StatutMission.PV_GENERE <= mission.statut < StatutMission.RAPPORT_GENERE,
            "peut_marquer_rapport_genere": est_chef and StatutMission.PV_SCAN_UPLOAD <= mission.statut < StatutMission.RAPPORT_GENERE,
            "peut_uploader_rapport_signe": est_chef and StatutMission.RAPPORT_GENERE <= mission.statut < StatutMission.VALIDEE,
            "peut_valider": est_chef and mission.statut == StatutMission.RAPPORT_SCAN_UPLOAD,
        },
    )


@require_chef_mission
def membre_ajouter(request, mission_pk):
    mission = request.mission
    if request.method == "POST":
        form = MembreGroupeControleForm(request.POST, instance=MembreGroupeControle(mission=mission))
        if form.is_valid():
            form.save()
        else:
            messages.error(request, _erreurs_en_message(form))
    return redirect("missions:mission_detail", mission_pk=mission.pk)


@require_membre_mission
def personne_ajouter(request, mission_pk):
    mission = request.mission
    if request.method == "POST":
        form = PersonneInterrogeeForm(request.POST)
        if form.is_valid():
            personne = form.cleaned_data["personne"]
            if not personne:
                personne = Personne.objects.create(
                    nom=form.cleaned_data["nom"],
                    prenom=form.cleaned_data["prenom"],
                    email=form.cleaned_data["email"],
                    telephone=form.cleaned_data["telephone"],
                )

            poste = form.cleaned_data["poste_snapshot"]
            service = form.cleaned_data["service_snapshot"]
            if not poste and not service:
                fonction = personne.fonctions.filter(
                    entite=mission.entite_controlee, date_fin__isnull=True
                ).first()
                if fonction:
                    poste = fonction.poste
                    service = fonction.service

            try:
                PersonneInterrogee.objects.create(
                    mission=mission, personne=personne, poste_snapshot=poste, service_snapshot=service,
                )
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
        else:
            messages.error(request, _erreurs_en_message(form))
    return redirect("missions:mission_detail", mission_pk=mission.pk)


@require_membre_mission
def questionnaire_page(request, mission_pk, page):
    mission = request.mission
    config = QUESTIONNAIRE_PAGES.get(page)
    if config is None:
        raise Http404("Page de questionnaire inconnue.")

    queryset = (
        config["model"].objects.filter(reponse__mission=mission)
        .select_related("reponse")
        .order_by("reponse__traitement")
    )
    FormSet = config["formset"]

    if request.method == "POST":
        formset = FormSet(request.POST, request.FILES, queryset=queryset)
        if formset.is_valid():
            formset.save()
            if page == 5:
                journaliser(mission, request.user, TypeAction.QUESTIONNAIRE_COMPLETE)
                if mission.statut < StatutMission.QUESTIONNAIRE_COMPLETE:
                    mission.statut = StatutMission.QUESTIONNAIRE_COMPLETE
                    mission.save()
                return redirect("missions:mission_detail", mission_pk=mission.pk)
            return redirect("missions:questionnaire_page", mission_pk=mission.pk, page=page + 1)
        messages.error(request, "Le formulaire contient des erreurs — voir le détail ci-dessous.")
    else:
        formset = FormSet(queryset=queryset)

    return render(
        request,
        config["template"],
        {
            "mission": mission,
            "formset": formset,
            "lignes": list(zip(formset.forms, queryset)),
            "page": page,
            "page_range": range(1, 6),
        },
    )


@require_membre_mission
def observations_modifier(request, mission_pk):
    mission = request.mission
    if request.method == "POST":
        form = ObservationsForm(request.POST, instance=mission)
        if form.is_valid():
            form.save()
        else:
            messages.error(request, _erreurs_en_message(form))
    return redirect("missions:mission_detail", mission_pk=mission.pk)


@require_chef_mission
def infos_pv_modifier(request, mission_pk):
    mission = request.mission
    if request.method == "POST":
        form = InfosPVForm(request.POST, instance=mission)
        if form.is_valid():
            form.save()
        else:
            messages.error(request, _erreurs_en_message(form))
    return redirect("missions:mission_detail", mission_pk=mission.pk)


@require_chef_mission
def evaluation_page(request, mission_pk):
    """Verdict du contrôleur (conforme/partiel/non conforme/préoccupant) et
    observations par traitement — saisi après le questionnaire, avant la
    génération du procès-verbal. Alimente le tableau 3 du PV."""
    mission = request.mission
    queryset = mission.reponses.order_by("traitement")

    if request.method == "POST":
        formset = EvaluationFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Évaluation enregistrée.")
            return redirect("missions:mission_detail", mission_pk=mission.pk)
        messages.error(request, "Le formulaire contient des erreurs — voir le détail ci-dessous.")
    else:
        formset = EvaluationFormSet(queryset=queryset)

    return render(
        request,
        "missions/evaluation.html",
        {
            "mission": mission,
            "formset": formset,
            "lignes": list(zip(formset.forms, queryset)),
        },
    )


def _construire_donnees_pv(mission):
    """Rassemble les données de la mission au format attendu par
    generate_pv() — voir missions/generate_pv.py."""
    membres = (
        list(mission.membres_groupe.select_related("agent").chefs())
        + list(mission.membres_groupe.select_related("agent").agents())
    )
    controleurs = [
        {
            "nom": str(membre.agent),
            "role": "Chef de Mission" if membre.role == RoleMission.CHEF else (membre.agent.poste or "Contrôleur"),
        }
        for membre in membres
    ]
    agents_interroges = [
        {"nom": str(pi.personne), "fonction": pi.poste_snapshot}
        for pi in mission.personnes_interrogees.select_related("personne")
    ]
    traitements = [
        {
            "libelle": f"{reponse.traitement}) {reponse.get_traitement_display()}",
            "cto": reponse.evaluation == EvaluationConformite.CTO,
            "cpa": reponse.evaluation == EvaluationConformite.CPA,
            "nc": reponse.evaluation == EvaluationConformite.NC,
            "cpr": reponse.evaluation == EvaluationConformite.CPR,
            "obs_controleur": reponse.observations_controleur,
            "obs_entite": reponse.observations_entite,
        }
        for reponse in mission.reponses.order_by("traitement")
    ]
    # Ligne "k) Autres" fixe du formulaire officiel, sans donnée correspondante
    # dans notre grille de 10 traitements (a→j).
    traitements.append({"libelle": "k) Autres (à préciser)"})

    chef = next((membre for membre in membres if membre.role == RoleMission.CHEF), None)

    return dict(
        mode_pv=mission.get_mode_pv_display() if mission.mode_pv else "",
        entite_controlee=str(mission.entite_controlee),
        nom_representant=mission.nom_representant_entite,
        controleurs=controleurs,
        agents_interroges=agents_interroges,
        date_controle=mission.date_mission.strftime("%d/%m/%Y"),
        heure_controle=mission.heure_controle,
        deliberation_numero=mission.deliberation_numero,
        deliberation_organe=mission.deliberation_organe,
        traitements=traitements,
        obs_controleur_general=mission.commentaires_observations,
        lieu_signature=mission.lieu_signature,
        date_signature=mission.date_signature.strftime("%d/%m/%Y") if mission.date_signature else "",
        heure_signature=mission.heure_signature,
        nom_controleur_signature=str(chef.agent) if chef else "",
        nom_representant_signature=mission.nom_representant_entite,
    )


@require_chef_mission
def pv_marquer_genere(request, mission_pk):
    """Génère le procès-verbal (missions/generate_pv.py) à partir des données
    de la mission et verrouille la mission une fois le questionnaire
    complété. Le PV doit ensuite être imprimé, signé, puis son scan
    uploadé — le rapport final n'est généré qu'après."""
    mission = request.mission
    if request.method == "POST":
        if mission.statut < StatutMission.QUESTIONNAIRE_COMPLETE:
            messages.error(request, "Le questionnaire doit être complété avant de générer le procès-verbal.")
        elif mission.est_verrouillee:
            messages.error(request, "Le procès-verbal a déjà été généré pour cette mission.")
        else:
            donnees = _construire_donnees_pv(mission)
            nom_fichier = f"pv_mission_{mission.pk}.docx"
            try:
                with tempfile.TemporaryDirectory() as dossier_temp:
                    chemin_docx = os.path.join(dossier_temp, nom_fichier)
                    resultat = generate_pv(output_path=chemin_docx, generate_pdf=True, **donnees)

                    with open(resultat["docx"], "rb") as fichier_docx:
                        mission.pv_document.save(nom_fichier, File(fichier_docx), save=False)
                    if resultat["pdf"]:
                        with open(resultat["pdf"], "rb") as fichier_pdf:
                            mission.pv_document_pdf.save(
                                os.path.splitext(nom_fichier)[0] + ".pdf", File(fichier_pdf), save=False
                            )
            except Exception as exc:  # génération de document externe : on ne laisse pas planter la vue
                messages.error(request, f"Échec de la génération du procès-verbal : {exc}")
                return redirect("missions:mission_detail", mission_pk=mission.pk)

            mission.statut = StatutMission.PV_GENERE
            mission.save()
            journaliser(mission, request.user, TypeAction.PV_GENERE, fichier=nom_fichier)
            messages.success(
                request,
                "Procès-verbal généré et mission verrouillée. Imprimez-le, faites-le signer, "
                "puis chargez le scan.",
            )
    return redirect("missions:mission_detail", mission_pk=mission.pk)


@require_chef_mission
def scan_uploader(request, mission_pk):
    mission = request.mission
    if request.method == "POST":
        if mission.statut < StatutMission.PV_GENERE:
            messages.error(request, "Le procès-verbal doit être généré avant l'upload du scan signé.")
            return redirect("missions:mission_detail", mission_pk=mission.pk)
        form = ScanSigneForm(request.POST, request.FILES, instance=mission)
        if form.is_valid():
            mission = form.save(commit=False)
            if mission.statut < StatutMission.PV_SCAN_UPLOAD:
                mission.statut = StatutMission.PV_SCAN_UPLOAD
            mission.save()
            journaliser(mission, request.user, TypeAction.SCAN_UPLOAD)
        else:
            messages.error(request, _erreurs_en_message(form))
    return redirect("missions:mission_detail", mission_pk=mission.pk)


@require_chef_mission
def rapport_marquer_genere(request, mission_pk):
    """Étape provisoire tant que la génération automatique réelle du rapport
    Word n'existe pas (modèle en attente) : le rapport final n'est généré
    qu'une fois le procès-verbal signé et son scan uploadé."""
    mission = request.mission
    if request.method == "POST":
        if mission.statut < StatutMission.PV_SCAN_UPLOAD:
            messages.error(request, "Le procès-verbal signé doit être uploadé avant de générer le rapport.")
        elif mission.statut >= StatutMission.RAPPORT_GENERE:
            messages.error(request, "Le rapport a déjà été généré pour cette mission.")
        else:
            mission.statut = StatutMission.RAPPORT_GENERE
            mission.save()
            journaliser(mission, request.user, TypeAction.RAPPORT_GENERE, provisoire=True)
            messages.success(
                request,
                "La création automatique du rapport est en cours de développement. "
                "En attendant, le rapport a été marqué comme généré — imprimez-le, faites-le "
                "signer, puis chargez le scan.",
            )
    return redirect("missions:mission_detail", mission_pk=mission.pk)


@require_chef_mission
def rapport_uploader(request, mission_pk):
    mission = request.mission
    if request.method == "POST":
        if mission.statut < StatutMission.RAPPORT_GENERE:
            messages.error(request, "Le rapport doit être généré avant l'upload du rapport signé.")
            return redirect("missions:mission_detail", mission_pk=mission.pk)
        form = RapportSigneForm(request.POST, request.FILES, instance=mission)
        if form.is_valid():
            mission = form.save(commit=False)
            if mission.statut < StatutMission.RAPPORT_SCAN_UPLOAD:
                mission.statut = StatutMission.RAPPORT_SCAN_UPLOAD
            mission.save()
            journaliser(mission, request.user, TypeAction.RAPPORT_SCAN_UPLOAD)
        else:
            messages.error(request, _erreurs_en_message(form))
    return redirect("missions:mission_detail", mission_pk=mission.pk)


@require_chef_mission
def mission_valider(request, mission_pk):
    mission = request.mission
    if request.method == "POST":
        if mission.statut != StatutMission.RAPPORT_SCAN_UPLOAD:
            messages.error(request, "Le rapport signé doit être uploadé avant validation.")
        else:
            mission.statut = StatutMission.VALIDEE
            mission.save()
            journaliser(mission, request.user, TypeAction.VALIDATION)
            messages.success(request, "Mission validée.")
    return redirect("missions:mission_detail", mission_pk=mission.pk)
