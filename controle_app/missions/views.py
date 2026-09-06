import os
import tempfile
from collections import Counter
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.http import Http404
from django.shortcuts import redirect, render

from core.permissions import GROUPE_ADMINISTRATEUR, est_dans_groupe, require_chef_mission, require_groupe, require_membre_mission
from entites.models import EntiteControlee, SecteurActivite
from personnes.models import Personne

from .forms import (
    DeclarationChecklistFormSet,
    EvaluationFormSet,
    InfosPVForm,
    MembreGroupeControleCreationFormSet,
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
from .models import EvaluationConformite, MembreGroupeControle, MissionControle, \
    PersonneInterrogee, ReponsePage1, ReponsePage2, ReponsePage3, ReponsePage4, ReponsePage5, \
    ReponseTraitement, RoleMission, StatutMission, Traitement, TypeAction, journaliser

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
    missions = MissionControle.objects.prefetch_related("entites_controlees").order_by("-date_mission")
    return render(
        request,
        "missions/mission_list.html",
        {
            "missions": missions,
            "peut_creer_mission": est_dans_groupe(request.user, GROUPE_ADMINISTRATEUR),
        },
    )


VERDICTS_CONFORMES = [EvaluationConformite.CTO, EvaluationConformite.CPA]
PERIODES_DASHBOARD_MOIS = {"3": 3, "6": 6, "12": 12, "24": 24}


def _mois_glissants(nombre_mois, aujourdhui=None):
    """Liste (ordre chronologique) du 1er jour de chacun des `nombre_mois`
    derniers mois, mois courant inclus — sert d'axe complet pour le graphe
    d'évolution même sur les mois sans mission."""
    aujourdhui = aujourdhui or date.today()
    annee, mois = aujourdhui.year, aujourdhui.month
    resultat = []
    for _ in range(nombre_mois):
        resultat.append(date(annee, mois, 1))
        mois -= 1
        if mois == 0:
            mois = 12
            annee -= 1
    return list(reversed(resultat))


@login_required
def dashboard(request):
    """Statistiques des missions de contrôle : avancement, taux de
    conformité (global et dans le temps), répartition des entités par
    secteur d'activité et traitements les plus audités.
    Filtrable par période via ?periode=3|6|12|24|all (12 mois par défaut)."""
    periode = request.GET.get("periode", "12")
    if periode not in PERIODES_DASHBOARD_MOIS and periode != "all":
        periode = "12"

    missions_qs = MissionControle.objects.all()
    mois_axe = None
    if periode != "all":
        mois_axe = _mois_glissants(PERIODES_DASHBOARD_MOIS[periode])
        missions_qs = missions_qs.filter(date_mission__gte=mois_axe[0])

    total_missions = missions_qs.count()

    compte_par_statut = {
        ligne["statut"]: ligne["total"]
        for ligne in missions_qs.values("statut").annotate(total=Count("id"))
    }
    missions_validees = compte_par_statut.get(StatutMission.VALIDEE.value, 0)
    missions_en_cours = total_missions - missions_validees

    reponses_qs = ReponseTraitement.objects.filter(mission__in=missions_qs).exclude(evaluation="")
    total_evaluees = reponses_qs.count()
    conformes = reponses_qs.filter(evaluation__in=VERDICTS_CONFORMES).count()
    taux_conformite_global = round(conformes * 100 / total_evaluees) if total_evaluees else None

    # Traitements non déclarés exclus : ils n'ont pas de questionnaire à
    # compléter (voir questionnaire_checklist), un avancement à 0% pour eux
    # n'indiquerait pas un retard mais un état normal et définitif.
    reponses_avancement = ReponseTraitement.objects.filter(
        mission__in=missions_qs, page1__declaration_effectuee=True,
    ).select_related("page1", "page2", "page3", "page4", "page5")
    pourcentages_avancement = [r.pourcentage_complete for r in reponses_avancement]
    avancement_moyen = round(sum(pourcentages_avancement) / len(pourcentages_avancement)) if pourcentages_avancement else 0

    compte_par_traitement = Counter(reponses_qs.values_list("traitement", flat=True))
    traitements_populaires = sorted(
        (
            {
                "label": label,
                "total_evalue": compte_par_traitement.get(code, 0),
                "pourcentage": round(compte_par_traitement.get(code, 0) * 100 / total_evaluees) if total_evaluees else 0,
            }
            for code, label in Traitement.choices
        ),
        key=lambda ligne: ligne["total_evalue"],
        reverse=True,
    )

    missions_par_mois = {
        ligne["mois"]: ligne["total"]
        for ligne in missions_qs.annotate(mois=TruncMonth("date_mission")).values("mois").annotate(total=Count("id"))
    }
    reponses_par_mois = {
        ligne["mois"]: ligne
        for ligne in (
            reponses_qs.annotate(mois=TruncMonth("mission__date_mission"))
            .values("mois")
            .annotate(total=Count("id"), conformes=Count("id", filter=Q(evaluation__in=VERDICTS_CONFORMES)))
        )
    }
    if mois_axe is None:
        mois_axe = sorted(set(missions_par_mois) | {m for m in reponses_par_mois if m})

    max_missions_mois = max(missions_par_mois.values(), default=0)
    evolution = []
    for mois in mois_axe:
        total_mois = missions_par_mois.get(mois, 0)
        ligne_reponses = reponses_par_mois.get(mois)
        taux_mois = (
            round(ligne_reponses["conformes"] * 100 / ligne_reponses["total"])
            if ligne_reponses and ligne_reponses["total"]
            else None
        )
        evolution.append({
            "mois": mois,
            "total_missions": total_mois,
            "hauteur_missions": round(total_mois * 100 / max_missions_mois) if max_missions_mois else 0,
            "taux_conformite": taux_mois,
        })

    structures = []
    entites_controlees = (
        EntiteControlee.objects.filter(missions__in=missions_qs).distinct().order_by("nom")
    )
    for entite in entites_controlees:
        missions_entite = missions_qs.filter(entites_controlees=entite).order_by("-date_mission")
        derniere_mission = missions_entite.prefetch_related("entites_controlees").first()
        reponses_entite = reponses_qs.filter(mission__entites_controlees=entite)
        total_eval_entite = reponses_entite.count()
        conformes_entite = reponses_entite.filter(evaluation__in=VERDICTS_CONFORMES).count()
        traitements_couverts = set(reponses_entite.values_list("traitement", flat=True))
        structures.append({
            "entite": entite,
            "nb_missions": missions_entite.count(),
            "derniere_mission": derniere_mission,
            "taux_conformite": round(conformes_entite * 100 / total_eval_entite) if total_eval_entite else None,
            "total_evalue": total_eval_entite,
            "traitements": [
                {"code": code, "label": label, "couvert": code in traitements_couverts}
                for code, label in Traitement.choices
            ],
        })
    structures.sort(
        key=lambda s: s["derniere_mission"].date_mission if s["derniere_mission"] else date.min, reverse=True
    )

    # Décompte en Python (et non via .values().annotate()) : `entites_controlees`
    # combine .filter(missions__in=...) et .distinct() — enchaîner .values()
    # sur ce queryset relance une requête qui perd la déduplication et compte
    # une entité une fois par mission jointe plutôt qu'une fois par entité.
    nb_entites_controlees = len(structures)
    labels_secteurs = dict(SecteurActivite.choices)
    compte_par_secteur = Counter(structure["entite"].secteur_activite for structure in structures)
    repartition_secteurs = sorted(
        (
            {
                "label": labels_secteurs.get(code, "Non renseigné") if code else "Non renseigné",
                "total": total,
                "pourcentage": round(total * 100 / nb_entites_controlees) if nb_entites_controlees else 0,
            }
            for code, total in compte_par_secteur.items()
        ),
        key=lambda ligne: ligne["total"],
        reverse=True,
    )

    return render(
        request,
        "missions/dashboard.html",
        {
            "periode": periode,
            "total_missions": total_missions,
            "missions_validees": missions_validees,
            "missions_en_cours": missions_en_cours,
            "taux_conformite_global": taux_conformite_global,
            "total_evaluees": total_evaluees,
            "avancement_moyen": avancement_moyen,
            "traitements_populaires": traitements_populaires,
            "evolution": evolution,
            "structures": structures,
            "nb_entites_controlees": nb_entites_controlees,
            "repartition_secteurs": repartition_secteurs,
        },
    )


@require_groupe(GROUPE_ADMINISTRATEUR)
def mission_create(request):
    """Formulaire de création subdivisé en deux parties soumises ensemble :
    MissionControleForm (entité(s), date, ordre de mission) et
    MembreGroupeControleCreationFormSet (membres du groupe de contrôle et
    chef de mission — mêmes champs que l'ajout a posteriori, voir
    membre_ajouter)."""
    if request.method == "POST":
        form = MissionControleForm(request.POST, request.FILES)
        membre_formset = MembreGroupeControleCreationFormSet(request.POST, prefix="membres")
        if form.is_valid() and membre_formset.is_valid():
            entites = list(form.cleaned_data["entites_controlees"])
            if form.cleaned_data.get("nom_nouvelle_entite"):
                entites.append(EntiteControlee.objects.create(
                    nom=form.cleaned_data["nom_nouvelle_entite"],
                    secteur_activite=form.cleaned_data["secteur_activite_nouvelle_entite"],
                ))

            mission = MissionControle.objects.create(
                date_mission=form.cleaned_data["date_mission"],
                commentaires_observations=form.cleaned_data["commentaires_observations"],
                ordre_mission=form.cleaned_data["ordre_mission"],
            )
            mission.entites_controlees.set(entites)

            for membre_form in membre_formset:
                if not membre_form.cleaned_data or membre_form.cleaned_data.get("DELETE"):
                    continue
                agent = membre_form.cleaned_data.get("agent")
                if not agent:
                    continue
                MembreGroupeControle.objects.create(
                    mission=mission, agent=agent,
                    role=membre_form.cleaned_data.get("role") or RoleMission.AGENT,
                )

            journaliser(mission, request.user, TypeAction.CREATION)
            return redirect("missions:mission_detail", mission_pk=mission.pk)
    else:
        form = MissionControleForm()
        membre_formset = MembreGroupeControleCreationFormSet(prefix="membres")
    return render(request, "missions/mission_form.html", {"form": form, "membre_formset": membre_formset})


@require_membre_mission
def mission_detail(request, mission_pk):
    mission = request.mission
    est_chef = request.user.is_superuser or mission.membres_groupe.chefs().filter(agent__user=request.user).exists()
    reponses = mission.reponses.select_related("page1", "page2", "page3", "page4", "page5")
    rapport_marque_genere = mission.statut >= StatutMission.RAPPORT_GENERE
    action_rapport_genere = None
    if rapport_marque_genere:
        action_rapport_genere = mission.journal.filter(type_action=TypeAction.RAPPORT_GENERE).first()
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
            "questionnaire_incomplet": mission.statut < StatutMission.QUESTIONNAIRE_COMPLETE,
            "peut_marquer_pv_genere": est_chef and StatutMission.QUESTIONNAIRE_COMPLETE <= mission.statut < StatutMission.PV_GENERE,
            "peut_uploader_scan": est_chef and StatutMission.PV_GENERE <= mission.statut < StatutMission.RAPPORT_GENERE,
            "peut_marquer_rapport_genere": est_chef and StatutMission.PV_SCAN_UPLOAD <= mission.statut < StatutMission.RAPPORT_GENERE,
            "peut_uploader_rapport_signe": est_chef and StatutMission.RAPPORT_GENERE <= mission.statut < StatutMission.VALIDEE,
            "peut_valider": est_chef and mission.statut == StatutMission.RAPPORT_SCAN_UPLOAD,
            "rapport_marque_genere": rapport_marque_genere,
            "action_rapport_genere": action_rapport_genere,
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
                    entite__in=mission.entites_controlees.all(), date_fin__isnull=True
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
def questionnaire_checklist(request, mission_pk):
    """Étape préalable au questionnaire : cocher les traitements réellement
    déclarés par l'entité contrôlée. Seuls les traitements déclarés sont
    ensuite détaillés dans les pages 1 à 5 (voir questionnaire_page) — les
    autres sont directement classés non conformes, sans qu'il soit besoin
    de les détailler (voir ReponseTraitement.suggestion_verdict)."""
    mission = request.mission
    queryset = (
        ReponsePage1.objects.filter(reponse__mission=mission)
        .select_related("reponse")
        .order_by("reponse__traitement")
    )

    if request.method == "POST":
        formset = DeclarationChecklistFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            for form in formset.forms:
                page1 = form.instance
                reponse = page1.reponse
                if not page1.declaration_effectuee and not reponse.evaluation:
                    reponse.evaluation = EvaluationConformite.NC
                    reponse.save()
            return redirect("missions:questionnaire_page", mission_pk=mission.pk, page=1)
        messages.error(request, "Le formulaire contient des erreurs — voir le détail ci-dessous.")
    else:
        formset = DeclarationChecklistFormSet(queryset=queryset)

    return render(
        request,
        "missions/questionnaire_checklist.html",
        {
            "mission": mission,
            "formset": formset,
            "lignes": list(zip(formset.forms, queryset)),
            "page_range": range(1, 6),
        },
    )


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
    if page == 1:
        queryset = queryset.filter(declaration_effectuee=True)
    else:
        queryset = queryset.filter(reponse__page1__declaration_effectuee=True)
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
    queryset = mission.reponses.select_related("page1", "page2", "page3", "page4", "page5").order_by("traitement")

    if request.method == "POST":
        formset = EvaluationFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Évaluation enregistrée.")
            return redirect("missions:mission_detail", mission_pk=mission.pk)
        messages.error(request, "Le formulaire contient des erreurs — voir le détail ci-dessous.")
    else:
        formset = EvaluationFormSet(queryset=queryset)

    lignes = [(form, reponse, reponse.suggestion_verdict()) for form, reponse in zip(formset.forms, queryset)]

    return render(
        request,
        "missions/evaluation.html",
        {
            "mission": mission,
            "formset": formset,
            "lignes": lignes,
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
        entite_controlee=mission.entites_str,
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
