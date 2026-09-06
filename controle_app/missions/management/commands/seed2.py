import datetime
import random

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from agents.models import AgentControleur
from entites.models import EntiteControlee, SecteurActivite
from personnes.models import Personne

from ...models import (
    ControleEntite,
    EvaluationConformite,
    MembreGroupeControle,
    MissionControle,
    ModePV,
    PersonneInterrogee,
    RoleMission,
    StatutMission,
    Traitement,
    TypeAction,
    journaliser,
)

GRAINE_ALEATOIRE = 20260906  # déterministe : mêmes données à chaque exécution

# Marqueur préfixé aux observations de chaque ControleEntite pour identifier
# — et donc dédupliquer — les contrôles générés par cette commande
# (indépendante de seed_missions).
MARQUEUR_SEED = "[Démo — seed2]"

ENTITES_DEMO = [
    ("Digital Services Gabon (démo)", SecteurActivite.INFORMATIQUE_TELECOM),
    ("Quincaillerie du Port (démo)", SecteurActivite.COMMERCE),
    ("Mutuelle Santé Estuaire (démo)", SecteurActivite.SANTE),
    ("Lycée International (démo)", SecteurActivite.EDUCATION),
    ("Résidence Les Manguiers (démo)", SecteurActivite.IMMOBILIER),
    ("Transports Fluviaux Ogooué (démo)", SecteurActivite.TRANSPORT_LOGISTIQUE),
    ("Auberge du Fleuve (démo)", SecteurActivite.HOTELLERIE_RESTAURATION),
    ("Cimenterie Nationale (démo)", SecteurActivite.INDUSTRIE),
    ("Banque Australe (démo)", SecteurActivite.BANQUE_FINANCE),
    ("Préfecture du Littoral (démo)", SecteurActivite.ADMINISTRATION),
]

PERSONNES_DEMO = [
    {"nom": "Mabika", "prenom": "Ruth", "poste": "Responsable conformité", "service": "Juridique"},
    {"nom": "Ogandaga", "prenom": "Franck", "poste": "Directeur technique", "service": "SI"},
    {"nom": "Nziengui", "prenom": "Carine", "poste": "Responsable RH", "service": "Ressources humaines"},
]

# Un scénario par statut du circuit (couverture complète du workflow), plus
# deux missions multi-entités pour illustrer cette fonctionnalité — chaque
# entité listée obtient son propre ControleEntite indépendant (même groupe
# de démo, même statut/nb_declares pour simplifier, mais des lignes
# distinctes en base, comme dans l'application réelle). `entites` prend 1 ou
# 2 index dans ENTITES_DEMO ; `nb_declares` fixe combien de traitements sont
# cochés "déclarés" à la checkliste de chaque contrôle (les autres sont
# automatiquement classés non conformes, sauf pour les statuts pas encore
# démarrés où la checkliste n'a simplement pas été faite).
SCENARIOS = [
    {"statut": StatutMission.BROUILLON, "entites": [0], "nb_declares": 0},
    {"statut": StatutMission.PLANIFIEE, "entites": [1], "nb_declares": 0},
    {"statut": StatutMission.EN_COURS, "entites": [2], "nb_declares": 3},
    {"statut": StatutMission.QUESTIONNAIRE_COMPLETE, "entites": [3], "nb_declares": 5},
    {"statut": StatutMission.PV_GENERE, "entites": [4], "nb_declares": 4},
    {"statut": StatutMission.PV_SCAN_UPLOAD, "entites": [5], "nb_declares": 6},
    {"statut": StatutMission.RAPPORT_GENERE, "entites": [6], "nb_declares": 5},
    {"statut": StatutMission.RAPPORT_SCAN_UPLOAD, "entites": [7], "nb_declares": 7},
    {"statut": StatutMission.VALIDEE, "entites": [8], "nb_declares": 8},
    {"statut": StatutMission.EN_COURS, "entites": [0, 1], "nb_declares": 4},
    {"statut": StatutMission.VALIDEE, "entites": [2, 9], "nb_declares": 9},
]


def _remplir_traitement_declare(reponse, evaluation=None):
    """Renseigne des valeurs plausibles sur les 5 pages d'un traitement
    coché comme déclaré à la checkliste."""
    code = reponse.traitement

    page1 = reponse.page1
    page1.declaration_effectuee = True
    page1.numero_recepisse = "REC-2026-DEMO2"
    page1.raison_collecte = "Gestion administrative courante de l'activité."
    page1.methode_consentement = "Consentement recueilli à l'inscription."
    page1.droits_respectes = True
    if code == Traitement.GEOLOCALISATION:
        page1.type_objet_geolocalise = "Véhicule de service"
        page1.desactivation_geoloc_pause = True
    page1.save()

    page2 = reponse.page2
    page2.contrat_sous_traitance = True
    page2.nombre_sous_traitants = 1
    page2.entites_destinataires = "Prestataire technique agréé"
    page2.sous_traitants_declares = True
    page2.transmission_mail = True
    if code in (Traitement.TELE_VIDEOSURVEILLANCE, Traitement.VIDEOSURVEILLANCE):
        page2.nombre_cameras = 6
        page2.listing_cameras_disponible = True
    page2.save()

    page3 = reponse.page3
    page3.donnees_identification = True
    page3.donnees_professionnelles = True
    page3.origine_donnees = "Collecte directe auprès des personnes concernées."
    page3.destinataires_donnees = "Service en charge du traitement"
    page3.duree_conservation = "5 ans"
    page3.save()

    page4 = reponse.page4
    page4.personnes_habilitees_noms = "Responsable du service concerné"
    page4.personnes_habilitees_fonctions = "Habilité par décision interne"
    if code == Traitement.TRANSFERT_DONNEES:
        page4.pays_transfert = "France"
        page4.autorite_protection_pays = "CNIL"
        page4.entite_destinataire_nom_adresse = "Partenaire — Paris, France"
    page4.save()

    page5 = reponse.page5
    page5.mesures_organisationnelles = "Charte interne, sensibilisation du personnel."
    page5.mesures_techniques = "Pare-feu, chiffrement des accès, contrôle d'accès physique."
    page5.save()

    if evaluation is not None:
        reponse.evaluation = evaluation
        reponse.observations_controleur = "RAS lors du contrôle."
        reponse.save()


def _appliquer_checkliste(controle, nb_declares, evaluer=False):
    """Reproduit l'effet de la checkliste (questionnaire_checklist) : coche
    `nb_declares` traitements comme déclarés et les détaille, classe
    automatiquement les autres non conformes — exactement le comportement de
    la vue, pour obtenir des données de démo cohérentes avec l'application."""
    codes = [code for code, _ in Traitement.choices]
    codes_declares = set(random.sample(codes, min(nb_declares, len(codes))))

    for reponse in controle.reponses.all():
        if reponse.traitement in codes_declares:
            evaluation = random.choice(list(EvaluationConformite.values)) if evaluer else None
            _remplir_traitement_declare(reponse, evaluation=evaluation)
        else:
            reponse.evaluation = EvaluationConformite.NC
            reponse.observations_controleur = "Traitement non déclaré par l'entité."
            reponse.save()


def _journaliser_progression(controle, utilisateur, statut):
    journaliser(controle, utilisateur, TypeAction.CREATION)
    if statut >= StatutMission.QUESTIONNAIRE_COMPLETE:
        journaliser(controle, utilisateur, TypeAction.QUESTIONNAIRE_COMPLETE)
    if statut >= StatutMission.PV_GENERE:
        journaliser(controle, utilisateur, TypeAction.PV_GENERE, fichier="pv_controle_demo2.docx")
    if statut >= StatutMission.PV_SCAN_UPLOAD:
        journaliser(controle, utilisateur, TypeAction.SCAN_UPLOAD)
    if statut >= StatutMission.RAPPORT_GENERE:
        journaliser(controle, utilisateur, TypeAction.RAPPORT_GENERE, provisoire=True)
    if statut >= StatutMission.RAPPORT_SCAN_UPLOAD:
        journaliser(controle, utilisateur, TypeAction.RAPPORT_SCAN_UPLOAD)
    if statut >= StatutMission.VALIDEE:
        journaliser(controle, utilisateur, TypeAction.VALIDATION)


class Command(BaseCommand):
    help = (
        "Crée un jeu de missions de démonstration couvrant chaque statut du circuit de "
        "clôture, avec entités sectorisées, missions multi-entités (un ControleEntite "
        "indépendant par entité), checkliste des traitements déclarés et ordre de mission "
        "joint (DEBUG uniquement)."
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed2 refuse de tourner avec DEBUG=False (données de test local uniquement).")

        call_command("seed_dev")

        if ControleEntite.objects.filter(commentaires_observations__startswith=MARQUEUR_SEED).exists():
            self.stdout.write("Missions de démo seed2 déjà présentes — génération ignorée.")
            return

        agents = {agent.external_id: agent for agent in AgentControleur.objects.all()}
        chef = agents.get("AG-001")
        autres_agents = [agents[eid] for eid in ("AG-002", "AG-003") if eid in agents]
        chef_user = chef.user if chef else None
        if not chef or not chef_user:
            raise CommandError("Agent chef AG-001 introuvable ou non lié à un utilisateur — vérifiez seed_dev.")

        random.seed(GRAINE_ALEATOIRE)

        entites = [
            EntiteControlee.objects.get_or_create(nom=nom, defaults={"secteur_activite": secteur})[0]
            for nom, secteur in ENTITES_DEMO
        ]
        personnes = [
            (
                Personne.objects.get_or_create(
                    nom=infos["nom"], prenom=infos["prenom"],
                    defaults={"email": f"{infos['prenom'].lower()}.{infos['nom'].lower()}@exemple-demo.ga"},
                )[0],
                infos,
            )
            for infos in PERSONNES_DEMO
        ]

        aujourd_hui = datetime.date.today()
        nb_controles = 0

        with transaction.atomic():
            for i, scenario in enumerate(SCENARIOS):
                statut = scenario["statut"]
                date_mission = aujourd_hui - datetime.timedelta(days=random.randint(10, 400))

                mission = MissionControle.objects.create(date_mission=date_mission)
                mission.ordre_mission.save(
                    f"ordre_mission_demo2_{i + 1}.pdf",
                    ContentFile(b"%PDF-1.4 Ordre de mission (demo seed2)"), save=True,
                )

                for idx in scenario["entites"]:
                    controle = ControleEntite.objects.create(
                        mission=mission, entite=entites[idx],
                        commentaires_observations=f"{MARQUEUR_SEED} Contrôle n°{i + 1}.",
                    )
                    nb_controles += 1

                    MembreGroupeControle.objects.create(controle=controle, agent=chef, role=RoleMission.CHEF)
                    for agent in random.sample(autres_agents, k=min(random.randint(1, 2), len(autres_agents))):
                        MembreGroupeControle.objects.create(controle=controle, agent=agent, role=RoleMission.AGENT)

                    for personne, infos in random.sample(personnes, k=random.randint(1, len(personnes))):
                        PersonneInterrogee.objects.create(
                            controle=controle, personne=personne,
                            poste_snapshot=infos["poste"], service_snapshot=infos["service"],
                        )

                    if scenario["nb_declares"]:
                        _appliquer_checkliste(
                            controle, scenario["nb_declares"], evaluer=statut >= StatutMission.QUESTIONNAIRE_COMPLETE,
                        )

                    if statut >= StatutMission.PV_GENERE:
                        representant, _ = random.choice(personnes)
                        controle.mode_pv = random.choice(ModePV.values)
                        controle.nom_representant_entite = str(representant)
                        controle.heure_controle = "09h30"
                        controle.deliberation_numero = f"DEL-{date_mission.year}-{i + 1:03d}"
                        controle.lieu_signature = "Libreville"
                        controle.date_signature = date_mission + datetime.timedelta(days=5)
                        controle.heure_signature = "12h15"

                    _journaliser_progression(controle, chef_user, statut)

                    controle.statut = statut
                    controle.save()

            self.stdout.write(self.style.SUCCESS(
                f"{len(SCENARIOS)} missions de démo seed2 créées ({nb_controles} contrôles d'entité — "
                f"1 par statut du circuit + 2 multi-entités, {len(entites)} structures sectorisées)."
            ))
