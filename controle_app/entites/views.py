from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from missions.models import EvaluationConformite, PersonneInterrogee, ReponseTraitement, Traitement

from .models import EntiteControlee, SecteurActivite

VERDICTS_CONFORMES = [EvaluationConformite.CTO, EvaluationConformite.CPA]


def _taux_conformite(reponses_qs):
    total = reponses_qs.count()
    if not total:
        return None, total
    conformes = reponses_qs.filter(evaluation__in=VERDICTS_CONFORMES).count()
    return round(conformes * 100 / total), total


@login_required
def entite_list(request):
    q = request.GET.get("q", "").strip()
    entites = EntiteControlee.objects.all().order_by("nom")
    if q:
        entites = entites.filter(nom__icontains=q)

    lignes = []
    for entite in entites:
        controles = entite.controles.select_related("mission")
        reponses = ReponseTraitement.objects.filter(controle__entite=entite).exclude(evaluation="")
        taux, total_eval = _taux_conformite(reponses)
        lignes.append({
            "entite": entite,
            "nb_missions": controles.count(),
            "dernier_controle": controles.order_by("-mission__date_mission").first(),
            "taux_conformite": taux,
        })
    lignes.sort(
        key=lambda ligne: ligne["dernier_controle"].mission.date_mission if ligne["dernier_controle"] else date.min,
        reverse=True,
    )

    return render(request, "entites/entite_list.html", {"lignes": lignes, "q": q})


@login_required
def entite_detail(request, entite_pk):
    entite = get_object_or_404(EntiteControlee, pk=entite_pk)
    controles = entite.controles.select_related("mission").order_by("-mission__date_mission")

    controles_info = []
    for controle in controles:
        taux, total_eval = _taux_conformite(controle.reponses.exclude(evaluation=""))
        controles_info.append({"controle": controle, "taux_conformite": taux, "total_evalue": total_eval})

    reponses_entite = ReponseTraitement.objects.filter(controle__entite=entite).exclude(evaluation="")
    taux_conformite_global, total_evalue_entite = _taux_conformite(reponses_entite)
    traitements_couverts = set(reponses_entite.values_list("traitement", flat=True))
    traitements = [
        {"code": code, "label": label, "couvert": code in traitements_couverts}
        for code, label in Traitement.choices
    ]

    personnes_par_id = {}
    for pi in (
        PersonneInterrogee.objects.filter(controle__entite=entite)
        .select_related("personne")
        .order_by("controle__mission__date_mission")
    ):
        ligne = personnes_par_id.setdefault(
            pi.personne_id, {"personne": pi.personne, "poste": pi.poste_snapshot, "nb_missions": 0}
        )
        ligne["nb_missions"] += 1
    personnes = sorted(personnes_par_id.values(), key=lambda ligne: ligne["personne"].nom)

    return render(
        request,
        "entites/entite_detail.html",
        {
            "entite": entite,
            "controles_info": controles_info,
            "nb_missions": len(controles_info),
            "taux_conformite_global": taux_conformite_global,
            "total_evalue_entite": total_evalue_entite,
            "traitements": traitements,
            "personnes": personnes,
            "secteurs_choices": SecteurActivite.choices,
        },
    )


@login_required
def entite_secteur_modifier(request, entite_pk):
    entite = get_object_or_404(EntiteControlee, pk=entite_pk)
    if request.method == "POST":
        secteur = request.POST.get("secteur_activite", "")
        if secteur in dict(SecteurActivite.choices) or secteur == "":
            entite.secteur_activite = secteur
            entite.save(update_fields=["secteur_activite"])
    return redirect("entites:entite_detail", entite_pk=entite.pk)
