"""
Orchestration des scans automatiques.
Déclenché à la création d'une MissionControleEnLigne ou manuellement
depuis l'admin.

Ordre : cartographie -> sécurité -> cookies/traceurs -> tiers.

Règles appliquées ici (cf. controle_en_ligne/CLAUDE.md) :
- Les scans écrivent des constats (faits), jamais de Qualification :
  analyse, conformité, criticité et validation relèvent de l'agent.
- Aucune tâche ne fait passer la mission en "validee".
- Un constat qu'un agent a commencé à qualifier n'est jamais écrasé
  ni supprimé par une relance.
- Chaque scan tourne dans sa propre transaction : un échec annule ce que
  ce scan avait commencé à écrire, est consigné dans mission.erreurs_scan
  et au journal, et n'empêche pas les scans suivants.
- Chaque scan réussi laisse une preuve "résultat technique brut" (JSON
  horodaté, empreinte SHA-256), purgée des valeurs de cookies/stockage.
"""

import json
import logging
import math

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from core.audit import journaliser

from .models import (
    MissionControleEnLigne, PageIdentifiee, ConstatCookie, ConstatSecurite,
    ConstatTiers, ScenarioTest, PreuveCapture,
)
from .services.scanner_cartographie import scanner_cartographie
from .services.scanner_securite import scanner_securite
from .services.scanner_cookies import scanner_cookies
from .services.scanner_tiers import scanner_tiers

logger = logging.getLogger(__name__)

SCENARIOS_COOKIES = ("avant", "acceptation", "refus", "modification")

# Numéros de ScenarioTest alimentés par l'orchestration.
NUMEROS_TESTS = {
    "cartographie": 1,
    "avant": 2,
    "acceptation": 3,
    "refus": 4,
    "modification": 5,
    "securite": 10,
}

# Champs qu'aucun scan ne peut écrire, même si le scanner les renvoie.
# La qualification n'existe pas sur les constats (table Qualification),
# mais on écarte aussi ses noms par défense en profondeur.
CHAMPS_INTERDITS_AUX_SCANS = {
    "id", "mission", "qualifications",
    "conformite", "criticite", "valide_par_agent", "agent", "date_validation",
    "analyse", "suite_proposee", "commentaire_agent",
    "fait_observe",              # rédigé par l'orchestration, pas par le scanner
    "risque_technique_suspecte",  # calculé ici à partir des faits
}

# Clés retirées des résultats bruts avant archivage comme preuve :
# la valeur d'un cookie ou d'une clé de stockage peut être un identifiant
# de visiteur et n'est pas nécessaire pour documenter le constat.
CLES_NON_CONSERVEES = {"valeur", "value"}


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

@shared_task
def lancer_scans_automatiques(mission_id: int):
    """
    Enchaîne les scans du niveau 1/2 uniquement
    (jamais le niveau 3 — technique approfondi, toujours déclenché à part).

    Fin de tâche :
    - tous les scans ont abouti  -> statut "terminee", erreurs_scan vide ;
    - au moins un échec          -> statut "en_cours", erreurs_scan renseigné,
      pour que l'agent voie la mission incomplète et relance.
    """
    mission = MissionControleEnLigne.objects.get(pk=mission_id)
    mission.erreurs_scan = []
    _changer_statut(mission, "cartographie")
    journaliser("lancement_scans", mission, description=f"Scans lancés sur {mission.url_principale}")

    _executer(mission, "cartographie", _scanner_cartographie_task, tests=[NUMEROS_TESTS["cartographie"]])

    _changer_statut(mission, "en_cours")
    _executer(mission, "securite", _scanner_securite_task, tests=[NUMEROS_TESTS["securite"]])
    _executer(mission, "cookies", _scanner_cookies_task,
              tests=[NUMEROS_TESTS[s] for s in SCENARIOS_COOKIES])
    _executer(mission, "tiers", _scanner_tiers_task)

    mission.statut = "en_cours" if mission.erreurs_scan else "terminee"
    mission.save(update_fields=["statut", "erreurs_scan"])
    journaliser(
        "fin_scans", mission,
        description="Scans terminés" + (f" avec {len(mission.erreurs_scan)} échec(s)" if mission.erreurs_scan else ""),
        donnees={"statut": mission.statut, "erreurs": mission.erreurs_scan},
    )
    return {"statut": mission.statut, "erreurs": mission.erreurs_scan}


def _changer_statut(mission: MissionControleEnLigne, statut: str) -> None:
    mission.statut = statut
    mission.save(update_fields=["statut"])


def _executer(mission: MissionControleEnLigne, nom_scan: str, fonction, tests=()) -> bool:
    """Exécute un scan dans sa transaction ; consigne l'échec sans interrompre la suite."""
    try:
        with transaction.atomic():
            fonction(mission)
    except Exception as exc:  # un scanner tiers peut lever n'importe quoi
        logger.exception("Scan %s en échec pour la mission %s", nom_scan, mission.pk)
        message = f"{type(exc).__name__}: {exc}"[:500]
        mission.erreurs_scan.append(
            {"scan": nom_scan, "erreur": message, "horodatage": timezone.now().isoformat()}
        )
        mission.save(update_fields=["erreurs_scan"])
        journaliser("echec_scan", mission, description=f"{nom_scan} : {message}")
        for numero in tests:
            _marquer_test(mission, numero, {"erreur": message}, execute=False)
        return False
    return True


# ---------------------------------------------------------------------------
# Phase 1 — Cartographie
# ---------------------------------------------------------------------------

def _scanner_cartographie_task(mission: MissionControleEnLigne):
    """
    Les pages saisies à la main par l'agent (origine="manuel") ne sont jamais
    écrasées ; les pages automatiques d'un lancement précédent sont remplacées.
    Les types absents sont enregistrés avec presente=False : l'absence d'une
    page (politique de confidentialité, mentions légales) est un fait utile.
    """
    horodatage = timezone.now()
    resultat = scanner_cartographie(
        mission.url_principale,
        user_agent=settings.CONTROLE_USER_AGENT,
        respecter_robots=settings.CONTROLE_RESPECTER_ROBOTS,
    )
    pages = resultat.get("pages", [])
    types_valides = {cle for cle, _ in PageIdentifiee.TYPES}
    types_manuels = set(
        mission.pages.filter(origine="manuel").values_list("type_page", flat=True)
    )

    mission.pages.filter(origine="auto").delete()
    compte = {True: 0, False: 0, None: 0}
    for page in pages:
        type_page = page.get("type_page")
        if type_page not in types_valides or type_page in types_manuels:
            continue
        url = page.get("url") or ""
        # True = page trouvée et accessible ; False = absente ou en erreur ;
        # None = lien vu mais page non visitée (limite de pages, robots.txt).
        presente = page.get("presente", bool(url))
        PageIdentifiee.objects.create(
            mission=mission,
            type_page=type_page,
            url=url[:500],
            presente=presente,
            indice=(page.get("indice") or "")[:255],
            origine="auto",
        )
        compte[presente] += 1
    trouvees, absentes = compte[True], compte[False]

    resume = (
        f"{resultat.get('pages_visitees', 0)} page(s) visitée(s) ; "
        f"{trouvees} type(s) de page trouvé(s), {absentes} non trouvé(s), {compte[None]} non vérifié(s)."
    )
    if resultat.get("bloquees_par_robots"):
        resume += f" {len(resultat['bloquees_par_robots'])} lien(s) non visité(s) (robots.txt)."
    _enregistrer_preuve(
        mission, nom_scan="cartographie", scenario="", horodatage=horodatage,
        contenu=resultat, outil="requests + beautifulsoup4", resume=resume,
    )
    _marquer_test(mission, NUMEROS_TESTS["cartographie"], {
        "pages_visitees": resultat.get("pages_visitees", 0), "trouvees": trouvees, "absentes": absentes,
    })


# ---------------------------------------------------------------------------
# Phase 8 — Sécurité observable
# ---------------------------------------------------------------------------

def _scanner_securite_task(mission: MissionControleEnLigne):
    horodatage = timezone.now()
    donnees = scanner_securite(mission.url_principale) or {}
    fait = _resumer_fait_securite(donnees)

    existant = ConstatSecurite.objects.filter(mission=mission).first()
    if existant is not None and existant.qualification is not None:
        # L'agent a commencé à qualifier ce constat : on n'écrase pas les faits
        # sur lesquels il s'appuie. Le nouveau résultat reste dans la preuve.
        logger.info("Sécurité mission %s : constat déjà qualifié, conservé tel quel.", mission.pk)
        fait = "Constat déjà qualifié, non modifié. Nouveau relevé : " + fait
    else:
        champs = _filtrer_champs(ConstatSecurite, donnees, "securite")
        # Signal de risque technique (jamais une qualification).
        risque = bool(donnees.get("fichiers_exposes")) or donnees.get("certificat_valide") is False
        ConstatSecurite.objects.update_or_create(
            mission=mission,
            defaults={**champs, "fait_observe": fait, "risque_technique_suspecte": risque},
        )

    _enregistrer_preuve(
        mission, nom_scan="securite", scenario="", horodatage=horodatage,
        contenu=donnees, outil="requests + ssl", resume=fait,
    )
    _marquer_test(mission, NUMEROS_TESTS["securite"], donnees)


def _resumer_fait_securite(donnees: dict) -> str:
    lignes = []
    if donnees.get("fichiers_exposes"):
        lignes.append(f"Chemins accessibles en liste blanche : {donnees['fichiers_exposes']}")
    if donnees.get("certificat_valide") is False:
        lignes.append("Certificat TLS invalide ou non vérifiable.")
    if donnees.get("https_complet") is False:
        lignes.append("Le site n'est pas intégralement servi en HTTPS.")
    return " / ".join(lignes) or "Aucune anomalie détectée par le scan automatique."


# ---------------------------------------------------------------------------
# Phase 4 — Cookies et autres traceurs
# ---------------------------------------------------------------------------

def _scanner_cookies_task(mission: MissionControleEnLigne):
    """
    Les constats sans qualification d'un lancement précédent sont remplacés ;
    ceux qu'un agent a commencé à qualifier sont conservés.
    Un traceur de type inconnu est répertorié en "non_classe" avec son type brut.
    """
    horodatage = timezone.now()
    resultats = scanner_cookies(mission.url_principale) or {}
    types_connus = {cle for cle, _ in ConstatCookie.TYPES_TRACEUR} - {"non_classe"}

    mission.constats_cookies.filter(qualifications__isnull=True).delete()

    for scenario in SCENARIOS_COOKIES:
        entrees = resultats.get(scenario, []) or []
        crees = non_classes = 0
        for entree in entrees:
            type_recu = entree.get("type_traceur") or "cookie"
            type_traceur = type_recu if type_recu in types_connus else "non_classe"
            nom = entree.get("nom") or entree.get("name") or ""
            domaine = entree.get("domaine") or entree.get("domain") or ""
            ConstatCookie.objects.create(
                mission=mission,
                scenario=scenario,
                type_traceur=type_traceur,
                type_brut="" if type_traceur != "non_classe" else str(type_recu)[:100],
                nom=nom[:255],
                domaine=domaine[:255],
                est_tiers=bool(entree.get("est_tiers")),
                duree_vie_jours=_duree_vie_jours(entree, horodatage),
                horodatage_scan=horodatage,
                fait_observe=_resumer_fait_traceur(type_traceur, type_recu, nom, domaine, scenario),
            )
            crees += 1
            non_classes += type_traceur == "non_classe"

        if non_classes:
            logger.warning(
                "Cookies mission %s, scénario %s : %d traceur(s) de type inconnu répertorié(s) en non classé.",
                mission.pk, scenario, non_classes,
            )
        _enregistrer_preuve(
            mission, nom_scan="cookies", scenario=scenario, horodatage=horodatage,
            contenu=entrees, outil="playwright",
            resume=f"{crees} traceur(s) relevé(s), dont {non_classes} de type non reconnu (à classer).",
        )
        _marquer_test(mission, NUMEROS_TESTS[scenario], _purger(entrees))


def _duree_vie_jours(entree: dict, horodatage) -> int | None:
    """
    Durée fournie par le scanner, sinon calculée depuis l'expiration
    Playwright (secondes epoch, -1 pour un cookie de session).
    """
    duree = entree.get("duree_vie_jours")
    if isinstance(duree, (int, float)):
        return int(duree)
    expires = entree.get("expires")
    if isinstance(expires, (int, float)) and expires > 0:
        restant = expires - horodatage.timestamp()
        return max(0, math.ceil(restant / 86400))
    return None


def _resumer_fait_traceur(type_traceur: str, type_recu, nom: str, domaine: str, scenario: str) -> str:
    libelle_scenario = dict(ConstatCookie.SCENARIOS)[scenario].lower()
    origine = domaine or "domaine inconnu"
    if type_traceur == "non_classe":
        return (f"Traceur de type non reconnu « {type_recu} », nom « {nom} », "
                f"déposé par {origine}, {libelle_scenario}. À classer par l'agent.")
    libelle_type = dict(ConstatCookie.TYPES_TRACEUR)[type_traceur]
    return f"{libelle_type} « {nom} » déposé par {origine}, {libelle_scenario}."


# ---------------------------------------------------------------------------
# Phase 11 — Tiers
# ---------------------------------------------------------------------------

def _scanner_tiers_task(mission: MissionControleEnLigne):
    horodatage = timezone.now()
    tiers = scanner_tiers(mission.url_principale) or []
    categories_valides = {cle for cle, _ in ConstatTiers.CATEGORIES}

    for entree in tiers:
        domaine = entree.get("domaine_tiers")
        if not domaine:
            continue
        categorie = entree.get("categorie")
        ConstatTiers.objects.get_or_create(
            mission=mission,
            domaine_tiers=domaine[:255],
            defaults={
                "categorie": categorie if categorie in categories_valides else "autre",
                "origine": "auto",
                "fait_observe": f"Appel vers le service tiers {domaine} observé lors du chargement du site.",
            },
        )
    _enregistrer_preuve(
        mission, nom_scan="tiers", scenario="", horodatage=horodatage,
        contenu=tiers, outil="playwright (interception réseau)",
        resume=f"{len(tiers)} service(s) tiers détecté(s).",
    )


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def _filtrer_champs(modele, donnees: dict, nom_scan: str) -> dict:
    """Ne garde que les champs du modèle qu'un scan a le droit d'écrire."""
    autorises = {f.name for f in modele._meta.concrete_fields} - CHAMPS_INTERDITS_AUX_SCANS
    retenus = {cle: valeur for cle, valeur in donnees.items() if cle in autorises}
    ecartes = sorted(set(donnees) - set(retenus))
    if ecartes:
        logger.info("Scan %s : clés non enregistrées dans %s : %s", nom_scan, modele.__name__, ecartes)
    return retenus


def _purger(contenu):
    """Retire récursivement les valeurs de cookies/stockage (minimisation)."""
    if isinstance(contenu, dict):
        return {k: _purger(v) for k, v in contenu.items() if k not in CLES_NON_CONSERVEES}
    if isinstance(contenu, list):
        return [_purger(v) for v in contenu]
    return contenu


def _enregistrer_preuve(mission, *, nom_scan, scenario, horodatage, contenu, outil, resume):
    """Archive le résultat brut (purgé) ; l'empreinte SHA-256 est calculée par PreuveCapture.save()."""
    brut = json.dumps(
        {
            "mission": mission.pk,
            "url": mission.url_principale,
            "scan": nom_scan,
            "scenario": scenario,
            "horodatage": horodatage.isoformat(),
            "resultat": _purger(contenu),
        },
        ensure_ascii=False, indent=2, sort_keys=True, default=str,
    ).encode("utf-8")

    suffixe = f"-{scenario}" if scenario else ""
    nom_fichier = f"mission-{mission.pk}/{nom_scan}{suffixe}-{horodatage:%Y%m%dT%H%M%S}.json"

    preuve = PreuveCapture(
        mission=mission,
        type_preuve="resultat_technique",
        scenario_lie=scenario or nom_scan,
        parcours_effectue=f"Scan automatique « {nom_scan} » sur {mission.url_principale}",
        resultat_obtenu=resume,
        outil_technique=outil,
        genere_automatiquement=True,
    )
    preuve.fichier.save(nom_fichier, ContentFile(brut), save=False)
    preuve.save()
    return preuve


def _marquer_test(mission: MissionControleEnLigne, numero: int, resultat, execute: bool = True) -> None:
    ScenarioTest.objects.update_or_create(
        mission=mission,
        numero_test=numero,
        defaults={
            "execute": execute,
            "date_execution": timezone.now(),
            "resultat_json": resultat if isinstance(resultat, dict) else {"data": resultat},
        },
    )
