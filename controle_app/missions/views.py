import os
import tempfile
from collections import Counter
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files import File
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from core.permissions import (
    GROUPE_ADMINISTRATEUR,
    est_dans_groupe,
    require_chef_controle,
    require_groupe,
    require_membre_controle,
)
from entites.models import EntiteControlee, SecteurActivite
from personnes.models import Personne

from .forms import (
    AjouterEntiteForm,
    DeclarationChecklistFormSet,
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
from .models import ControleEntite, EvaluationConformite, MembreGroupeControle, MissionControle, \
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
    missions = MissionControle.objects.prefetch_related("controles_entites").order_by("-date_mission")
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
    d'évolution même sur les mois sans contrôle."""
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
    """Statistiques des contrôles d'entité : avancement, taux de conformité
    (global et dans le temps), répartition des entités par secteur
    d'activité et traitements les plus audités. Chaque entité contrôlée a
    son propre circuit (ControleEntite) — c'est l'unité de mesure de ces
    statistiques, pas la mission (qui peut en regrouper plusieurs).
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

    controles_qs = ControleEntite.objects.filter(mission__in=missions_qs)
    total_controles = controles_qs.count()

    compte_par_statut = {
        ligne["statut"]: ligne["total"]
        for ligne in controles_qs.values("statut").annotate(total=Count("id"))
    }
    controles_valides = compte_par_statut.get(StatutMission.VALIDEE.value, 0)
    controles_en_cours = total_controles - controles_valides

    reponses_qs = ReponseTraitement.objects.filter(controle__in=controles_qs).exclude(evaluation="")
    total_evaluees = reponses_qs.count()
    conformes = reponses_qs.filter(evaluation__in=VERDICTS_CONFORMES).count()
    taux_conformite_global = round(conformes * 100 / total_evaluees) if total_evaluees else None

    # Traitements non déclarés exclus : ils n'ont pas de questionnaire à
    # compléter (voir questionnaire_checklist), un avancement à 0% pour eux
    # n'indiquerait pas un retard mais un état normal et définitif.
    reponses_avancement = ReponseTraitement.objects.filter(
        controle__in=controles_qs, page1__declaration_effectuee=True,
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

    controles_par_mois = {
        ligne["mois"]: ligne["total"]
        for ligne in controles_qs.annotate(mois=TruncMonth("mission__date_mission")).values("mois").annotate(total=Count("id"))
    }
    reponses_par_mois = {
        ligne["mois"]: ligne
        for ligne in (
            reponses_qs.annotate(mois=TruncMonth("controle__mission__date_mission"))
            .values("mois")
            .annotate(total=Count("id"), conformes=Count("id", filter=Q(evaluation__in=VERDICTS_CONFORMES)))
        )
    }
    if mois_axe is None:
        mois_axe = sorted(set(controles_par_mois) | {m for m in reponses_par_mois if m})

    max_controles_mois = max(controles_par_mois.values(), default=0)
    evolution = []
    for mois in mois_axe:
        total_mois = controles_par_mois.get(mois, 0)
        ligne_reponses = reponses_par_mois.get(mois)
        taux_mois = (
            round(ligne_reponses["conformes"] * 100 / ligne_reponses["total"])
            if ligne_reponses and ligne_reponses["total"]
            else None
        )
        evolution.append({
            "mois": mois,
            "total_missions": total_mois,
            "hauteur_missions": round(total_mois * 100 / max_controles_mois) if max_controles_mois else 0,
            "taux_conformite": taux_mois,
        })

    structures = []
    entites_controlees = (
        EntiteControlee.objects.filter(controles__in=controles_qs).distinct().order_by("nom")
    )
    for entite in entites_controlees:
        controles_entite = controles_qs.filter(entite=entite).select_related("mission").order_by("-mission__date_mission")
        dernier_controle = controles_entite.first()
        reponses_entite = reponses_qs.filter(controle__entite=entite)
        total_eval_entite = reponses_entite.count()
        conformes_entite = reponses_entite.filter(evaluation__in=VERDICTS_CONFORMES).count()
        traitements_couverts = set(reponses_entite.values_list("traitement", flat=True))
        structures.append({
            "entite": entite,
            "nb_missions": controles_entite.count(),
            "dernier_controle": dernier_controle,
            "taux_conformite": round(conformes_entite * 100 / total_eval_entite) if total_eval_entite else None,
            "total_evalue": total_eval_entite,
            "traitements": [
                {"code": code, "label": label, "couvert": code in traitements_couverts}
                for code, label in Traitement.choices
            ],
        })
    structures.sort(
        key=lambda s: s["dernier_controle"].mission.date_mission if s["dernier_controle"] else date.min, reverse=True
    )

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
            "total_controles": total_controles,
            "controles_valides": controles_valides,
            "controles_en_cours": controles_en_cours,
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
    """Formulaire de l'admin : crée la mission et un ControleEntite par
    entité sélectionnée/déclarée — chacun démarre son propre circuit
    (BROUILLON). L'affectation du groupe de contrôle de chaque entité se
    fait ensuite depuis la fiche mission (voir entite_ajouter, membre_ajouter)."""
    if request.method == "POST":
        form = MissionControleForm(request.POST, request.FILES)
        if form.is_valid():
            entites = list(form.cleaned_data["entites_controlees"])
            if form.cleaned_data.get("nom_nouvelle_entite"):
                entites.append(EntiteControlee.objects.create(
                    nom=form.cleaned_data["nom_nouvelle_entite"],
                    secteur_activite=form.cleaned_data["secteur_activite_nouvelle_entite"],
                ))

            mission = MissionControle.objects.create(
                date_mission=form.cleaned_data["date_mission"],
                ordre_mission=form.cleaned_data["ordre_mission"],
            )
            for entite in entites:
                controle = ControleEntite.objects.create(mission=mission, entite=entite)
                journaliser(controle, request.user, TypeAction.CREATION)

            return redirect("missions:mission_detail", mission_pk=mission.pk)
    else:
        form = MissionControleForm()
    return render(request, "missions/mission_form.html", {"form": form})


@login_required
def mission_detail(request, mission_pk):
    """Vue d'ensemble de la mission (admin) : liste des entités contrôlées,
    chacune avec son propre statut et son groupe de contrôle — accessible à
    l'admin ainsi qu'à tout membre d'au moins un des contrôles de cette
    mission (pour naviguer vers le sien)."""
    mission = get_object_or_404(MissionControle, pk=mission_pk)
    est_admin = est_dans_groupe(request.user, GROUPE_ADMINISTRATEUR)
    if not est_admin and not mission.controles_entites.filter(membres_groupe__agent__user=request.user).exists():
        raise PermissionDenied("Vous n'êtes membre d'aucun contrôle de cette mission.")

    controles = (
        mission.controles_entites.select_related("entite")
        .prefetch_related("membres_groupe__agent")
        .order_by("entite__nom")
    )
    return render(
        request,
        "missions/mission_detail.html",
        {
            "mission": mission,
            "controles": controles,
            "est_admin": est_admin,
            "entite_form": AjouterEntiteForm(),
        },
    )


@require_groupe(GROUPE_ADMINISTRATEUR)
def entite_ajouter(request, mission_pk):
    """Ajoute une entité (et donc un nouveau ControleEntite indépendant) à
    une mission existante."""
    mission = get_object_or_404(MissionControle, pk=mission_pk)
    if request.method == "POST":
        form = AjouterEntiteForm(request.POST)
        if form.is_valid():
            entite = form.cleaned_data["entite_controlee"]
            if not entite:
                entite = EntiteControlee.objects.create(
                    nom=form.cleaned_data["nom_nouvelle_entite"],
                    secteur_activite=form.cleaned_data["secteur_activite_nouvelle_entite"],
                )
            try:
                controle = ControleEntite.objects.create(mission=mission, entite=entite)
                journaliser(controle, request.user, TypeAction.CREATION)
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
        else:
            messages.error(request, _erreurs_en_message(form))
    return redirect("missions:mission_detail", mission_pk=mission.pk)


@require_membre_controle
def controle_entite_detail(request, controle_pk):
    controle = request.controle
    est_chef = request.user.is_superuser or controle.membres_groupe.chefs().filter(agent__user=request.user).exists()
    reponses = controle.reponses.select_related("page1", "page2", "page3", "page4", "page5")
    rapport_marque_genere = controle.statut >= StatutMission.RAPPORT_GENERE
    action_rapport_genere = None
    if rapport_marque_genere:
        action_rapport_genere = controle.journal.filter(type_action=TypeAction.RAPPORT_GENERE).first()
    return render(
        request,
        "missions/controle_entite_detail.html",
        {
            "controle": controle,
            "reponses": reponses,
            "membre_form": MembreGroupeControleForm(),
            "personne_form": PersonneInterrogeeForm(),
            "observations_form": ObservationsForm(instance=controle),
            "infos_pv_form": InfosPVForm(instance=controle),
            "page_range": range(1, 6),
            "est_chef": est_chef,
            "questionnaire_incomplet": controle.statut < StatutMission.QUESTIONNAIRE_COMPLETE,
            "peut_marquer_pv_genere": est_chef and StatutMission.QUESTIONNAIRE_COMPLETE <= controle.statut < StatutMission.PV_GENERE,
            "peut_uploader_scan": est_chef and StatutMission.PV_GENERE <= controle.statut < StatutMission.RAPPORT_GENERE,
            "peut_marquer_rapport_genere": est_chef and StatutMission.PV_SCAN_UPLOAD <= controle.statut < StatutMission.RAPPORT_GENERE,
            "peut_uploader_rapport_signe": est_chef and StatutMission.RAPPORT_GENERE <= controle.statut < StatutMission.VALIDEE,
            "peut_valider": est_chef and controle.statut == StatutMission.RAPPORT_SCAN_UPLOAD,
            "rapport_marque_genere": rapport_marque_genere,
            "action_rapport_genere": action_rapport_genere,
        },
    )


@require_chef_controle
def membre_ajouter(request, controle_pk):
    controle = request.controle
    if request.method == "POST":
        form = MembreGroupeControleForm(request.POST, instance=MembreGroupeControle(controle=controle))
        if form.is_valid():
            # La contrainte "un seul chef" référence `controle`, qui n'est pas
            # un champ du formulaire — form.is_valid() ne la voit donc pas
            # (exclue de la validation), elle ne se déclenche qu'ici, au save().
            try:
                form.save()
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
        else:
            messages.error(request, _erreurs_en_message(form))
    return redirect("missions:controle_entite_detail", controle_pk=controle.pk)


@require_membre_controle
def personne_ajouter(request, controle_pk):
    controle = request.controle
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
                    entite=controle.entite, date_fin__isnull=True
                ).first()
                if fonction:
                    poste = fonction.poste
                    service = fonction.service

            try:
                PersonneInterrogee.objects.create(
                    controle=controle, personne=personne, poste_snapshot=poste, service_snapshot=service,
                )
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
        else:
            messages.error(request, _erreurs_en_message(form))
    return redirect("missions:controle_entite_detail", controle_pk=controle.pk)


@require_membre_controle
def questionnaire_checklist(request, controle_pk):
    """Étape préalable au questionnaire : cocher les traitements réellement
    déclarés par l'entité contrôlée. Seuls les traitements déclarés sont
    ensuite détaillés dans les pages 1 à 5 (voir questionnaire_page) — les
    autres sont directement classés non conformes, sans qu'il soit besoin
    de les détailler (voir ReponseTraitement.suggestion_verdict)."""
    controle = request.controle
    queryset = (
        ReponsePage1.objects.filter(reponse__controle=controle)
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
            return redirect("missions:questionnaire_page", controle_pk=controle.pk, page=1)
        messages.error(request, "Le formulaire contient des erreurs — voir le détail ci-dessous.")
    else:
        formset = DeclarationChecklistFormSet(queryset=queryset)

    return render(
        request,
        "missions/questionnaire_checklist.html",
        {
            "controle": controle,
            "formset": formset,
            "lignes": list(zip(formset.forms, queryset)),
            "page_range": range(1, 6),
        },
    )


@require_membre_controle
def questionnaire_page(request, controle_pk, page):
    controle = request.controle
    config = QUESTIONNAIRE_PAGES.get(page)
    if config is None:
        raise Http404("Page de questionnaire inconnue.")

    queryset = (
        config["model"].objects.filter(reponse__controle=controle)
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
                journaliser(controle, request.user, TypeAction.QUESTIONNAIRE_COMPLETE)
                if controle.statut < StatutMission.QUESTIONNAIRE_COMPLETE:
                    controle.statut = StatutMission.QUESTIONNAIRE_COMPLETE
                    controle.save()
                return redirect("missions:controle_entite_detail", controle_pk=controle.pk)
            return redirect("missions:questionnaire_page", controle_pk=controle.pk, page=page + 1)
        messages.error(request, "Le formulaire contient des erreurs — voir le détail ci-dessous.")
    else:
        formset = FormSet(queryset=queryset)

    return render(
        request,
        config["template"],
        {
            "controle": controle,
            "formset": formset,
            "lignes": list(zip(formset.forms, queryset)),
            "page": page,
            "page_range": range(1, 6),
        },
    )


@require_membre_controle
def observations_modifier(request, controle_pk):
    controle = request.controle
    if request.method == "POST":
        form = ObservationsForm(request.POST, instance=controle)
        if form.is_valid():
            form.save()
        else:
            messages.error(request, _erreurs_en_message(form))
    return redirect("missions:controle_entite_detail", controle_pk=controle.pk)


@require_chef_controle
def infos_pv_modifier(request, controle_pk):
    controle = request.controle
    if request.method == "POST":
        form = InfosPVForm(request.POST, instance=controle)
        if form.is_valid():
            form.save()
        else:
            messages.error(request, _erreurs_en_message(form))
    return redirect("missions:controle_entite_detail", controle_pk=controle.pk)


@require_chef_controle
def evaluation_page(request, controle_pk):
    """Verdict du contrôleur (conforme/partiel/non conforme/préoccupant) et
    observations par traitement — saisi après le questionnaire, avant la
    génération du procès-verbal. Alimente le tableau 3 du PV."""
    controle = request.controle
    queryset = controle.reponses.select_related("page1", "page2", "page3", "page4", "page5").order_by("traitement")

    if request.method == "POST":
        formset = EvaluationFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Évaluation enregistrée.")
            return redirect("missions:controle_entite_detail", controle_pk=controle.pk)
        messages.error(request, "Le formulaire contient des erreurs — voir le détail ci-dessous.")
    else:
        formset = EvaluationFormSet(queryset=queryset)

    lignes = [(form, reponse, reponse.suggestion_verdict()) for form, reponse in zip(formset.forms, queryset)]

    return render(
        request,
        "missions/evaluation.html",
        {
            "controle": controle,
            "formset": formset,
            "lignes": lignes,
        },
    )


def _construire_donnees_pv(controle):
    """Rassemble les données du contrôle d'entité au format attendu par
    generate_pv() — voir missions/generate_pv.py."""
    membres = (
        list(controle.membres_groupe.select_related("agent").chefs())
        + list(controle.membres_groupe.select_related("agent").agents())
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
        for pi in controle.personnes_interrogees.select_related("personne")
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
        for reponse in controle.reponses.order_by("traitement")
    ]
    # Ligne "k) Autres" fixe du formulaire officiel, sans donnée correspondante
    # dans notre grille de 10 traitements (a→j).
    traitements.append({"libelle": "k) Autres (à préciser)"})

    chef = next((membre for membre in membres if membre.role == RoleMission.CHEF), None)

    return dict(
        mode_pv=controle.get_mode_pv_display() if controle.mode_pv else "",
        entite_controlee=str(controle.entite),
        nom_representant=controle.nom_representant_entite,
        controleurs=controleurs,
        agents_interroges=agents_interroges,
        date_controle=controle.mission.date_mission.strftime("%d/%m/%Y"),
        heure_controle=controle.heure_controle,
        deliberation_numero=controle.deliberation_numero,
        deliberation_organe=controle.deliberation_organe,
        traitements=traitements,
        obs_controleur_general=controle.commentaires_observations,
        lieu_signature=controle.lieu_signature,
        date_signature=controle.date_signature.strftime("%d/%m/%Y") if controle.date_signature else "",
        heure_signature=controle.heure_signature,
        nom_controleur_signature=str(chef.agent) if chef else "",
        nom_representant_signature=controle.nom_representant_entite,
    )


@require_chef_controle
def pv_marquer_genere(request, controle_pk):
    """Génère le procès-verbal (missions/generate_pv.py) à partir des
    données du contrôle et le verrouille une fois le questionnaire complété.
    Le PV doit ensuite être imprimé, signé, puis son scan uploadé — le
    rapport final n'est généré qu'après."""
    controle = request.controle
    if request.method == "POST":
        if controle.statut < StatutMission.QUESTIONNAIRE_COMPLETE:
            messages.error(request, "Le questionnaire doit être complété avant de générer le procès-verbal.")
        elif controle.est_verrouillee:
            messages.error(request, "Le procès-verbal a déjà été généré pour ce contrôle.")
        else:
            donnees = _construire_donnees_pv(controle)
            nom_fichier = f"pv_controle_{controle.pk}.docx"
            try:
                with tempfile.TemporaryDirectory() as dossier_temp:
                    chemin_docx = os.path.join(dossier_temp, nom_fichier)
                    resultat = generate_pv(output_path=chemin_docx, generate_pdf=True, **donnees)

                    with open(resultat["docx"], "rb") as fichier_docx:
                        controle.pv_document.save(nom_fichier, File(fichier_docx), save=False)
                    if resultat["pdf"]:
                        with open(resultat["pdf"], "rb") as fichier_pdf:
                            controle.pv_document_pdf.save(
                                os.path.splitext(nom_fichier)[0] + ".pdf", File(fichier_pdf), save=False
                            )
            except Exception as exc:  # génération de document externe : on ne laisse pas planter la vue
                messages.error(request, f"Échec de la génération du procès-verbal : {exc}")
                return redirect("missions:controle_entite_detail", controle_pk=controle.pk)

            controle.statut = StatutMission.PV_GENERE
            controle.save()
            journaliser(controle, request.user, TypeAction.PV_GENERE, fichier=nom_fichier)
            messages.success(
                request,
                "Procès-verbal généré et contrôle verrouillé. Imprimez-le, faites-le signer, "
                "puis chargez le scan.",
            )
    return redirect("missions:controle_entite_detail", controle_pk=controle.pk)


@require_chef_controle
def scan_uploader(request, controle_pk):
    controle = request.controle
    if request.method == "POST":
        if controle.statut < StatutMission.PV_GENERE:
            messages.error(request, "Le procès-verbal doit être généré avant l'upload du scan signé.")
            return redirect("missions:controle_entite_detail", controle_pk=controle.pk)
        form = ScanSigneForm(request.POST, request.FILES, instance=controle)
        if form.is_valid():
            controle = form.save(commit=False)
            if controle.statut < StatutMission.PV_SCAN_UPLOAD:
                controle.statut = StatutMission.PV_SCAN_UPLOAD
            controle.save()
            journaliser(controle, request.user, TypeAction.SCAN_UPLOAD)
        else:
            messages.error(request, _erreurs_en_message(form))
    return redirect("missions:controle_entite_detail", controle_pk=controle.pk)


@require_chef_controle
def rapport_marquer_genere(request, controle_pk):
    """Étape provisoire tant que la génération automatique réelle du rapport
    Word n'existe pas (modèle en attente) : le rapport final n'est généré
    qu'une fois le procès-verbal signé et son scan uploadé."""
    controle = request.controle
    if request.method == "POST":
        if controle.statut < StatutMission.PV_SCAN_UPLOAD:
            messages.error(request, "Le procès-verbal signé doit être uploadé avant de générer le rapport.")
        elif controle.statut >= StatutMission.RAPPORT_GENERE:
            messages.error(request, "Le rapport a déjà été généré pour ce contrôle.")
        else:
            controle.statut = StatutMission.RAPPORT_GENERE
            controle.save()
            journaliser(controle, request.user, TypeAction.RAPPORT_GENERE, provisoire=True)
            messages.success(
                request,
                "La création automatique du rapport est en cours de développement. "
                "En attendant, le rapport a été marqué comme généré — imprimez-le, faites-le "
                "signer, puis chargez le scan.",
            )
    return redirect("missions:controle_entite_detail", controle_pk=controle.pk)


@require_chef_controle
def rapport_uploader(request, controle_pk):
    controle = request.controle
    if request.method == "POST":
        if controle.statut < StatutMission.RAPPORT_GENERE:
            messages.error(request, "Le rapport doit être généré avant l'upload du rapport signé.")
            return redirect("missions:controle_entite_detail", controle_pk=controle.pk)
        form = RapportSigneForm(request.POST, request.FILES, instance=controle)
        if form.is_valid():
            controle = form.save(commit=False)
            if controle.statut < StatutMission.RAPPORT_SCAN_UPLOAD:
                controle.statut = StatutMission.RAPPORT_SCAN_UPLOAD
            controle.save()
            journaliser(controle, request.user, TypeAction.RAPPORT_SCAN_UPLOAD)
        else:
            messages.error(request, _erreurs_en_message(form))
    return redirect("missions:controle_entite_detail", controle_pk=controle.pk)


@require_chef_controle
def controle_valider(request, controle_pk):
    controle = request.controle
    if request.method == "POST":
        if controle.statut != StatutMission.RAPPORT_SCAN_UPLOAD:
            messages.error(request, "Le rapport signé doit être uploadé avant validation.")
        else:
            controle.statut = StatutMission.VALIDEE
            controle.save()
            journaliser(controle, request.user, TypeAction.VALIDATION)
            messages.success(request, "Contrôle validé.")
    return redirect("missions:controle_entite_detail", controle_pk=controle.pk)
