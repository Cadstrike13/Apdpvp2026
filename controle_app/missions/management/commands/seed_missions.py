import datetime
import random

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from agents.models import AgentControleur
from entites.models import EntiteControlee
from personnes.models import Personne

from ...models import (
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

NB_MISSIONS = 60
NB_ANNEES = 3
GRAINE_ALEATOIRE = 20260821  # déterministe : mêmes données à chaque exécution

# Marqueur préfixé aux observations pour identifier — et donc dédupliquer —
# les missions générées par cette commande, indépendamment des entités
# utilisées (qui peuvent être partagées avec seed_dev / d'anciennes données).
MARQUEUR_SEED = "[Démo — seed_missions]"

ENTITES_DEMO = [
    "ACME SA (démo)",
    "Société Gabonaise de Transport (démo)",
    "Clinique Sainte-Marie (démo)",
    "Banque Populaire du Gabon (démo)",
    "Télécom Estuaire (démo)",
    "Hôtel Okoumé Palace (démo)",
    "Supermarché Mbolo (démo)",
    "Assurances Aurore (démo)",
    "Groupe Scolaire Les Palmiers (démo)",
    "Sécurité Plus SARL (démo)",
    "Compagnie Minière du Sud (démo)",
    "Agence Immobilière Littoral (démo)",
    "Cabinet Médical Nkembo (démo)",
    "Radio-Taxi Libreville (démo)",
]

PERSONNES_DEMO = [
    {"nom": "Ondo", "prenom": "Jean", "poste": "Responsable administratif", "service": "Administration"},
    {"nom": "Nzamba", "prenom": "Alice", "poste": "Directrice administrative", "service": "Direction"},
    {"nom": "Moussavou", "prenom": "Pierre", "poste": "Responsable RH", "service": "Ressources humaines"},
    {"nom": "Ella", "prenom": "Sandrine", "poste": "Responsable informatique", "service": "SI"},
    {"nom": "Bongo", "prenom": "Serge", "poste": "Responsable sécurité", "service": "Sécurité"},
    {"nom": "Ivinza", "prenom": "Christelle", "poste": "Chargée de clientèle", "service": "Relation clients"},
    {"nom": "Mintsa", "prenom": "David", "poste": "Directeur d'exploitation", "service": "Exploitation"},
]


def _remplir_reponse(reponse, evaluation=None):
    """Renseigne des valeurs plausibles sur les 5 pages d'un ReponseTraitement
    (créées automatiquement par le signal post_save de MissionControle) pour
    obtenir une donnée de démo réaliste plutôt que des pages vides."""
    code = reponse.traitement

    page1 = reponse.page1
    page1.declaration_effectuee = True
    page1.numero_recepisse = "REC-2026-001"
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
        page2.nombre_cameras = 8
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
    if code == Traitement.INTERCONNEXION:
        page4.entites_interconnexion = "Ministère de tutelle"
    if code == Traitement.TRANSFERT_DONNEES:
        page4.pays_transfert = "France"
        page4.autorite_protection_pays = "CNIL"
        page4.entite_destinataire_nom_adresse = "Partenaire — Paris, France"
    if code == Traitement.CONTROLE_ACCES_AVEC_BIOMETRIE:
        page4.empreinte_pouces_index = True
    page4.save()

    page5 = reponse.page5
    page5.mesures_organisationnelles = "Charte interne, sensibilisation du personnel."
    page5.mesures_techniques = "Pare-feu, chiffrement des accès, contrôle d'accès physique."
    page5.save()

    if evaluation is not None:
        reponse.evaluation = evaluation
        reponse.observations_controleur = "RAS lors du contrôle."
        reponse.save()


def _dates_reparties(nb_missions, nb_annees):
    """`nb_missions` dates réparties en blocs égaux sur les `nb_annees`
    dernières années (bloc 0 = les 365 derniers jours, etc.), pour garantir
    une couverture homogène des 3 ans plutôt qu'un tirage aléatoire pouvant
    se concentrer sur une seule période."""
    aujourd_hui = datetime.date.today()
    par_bloc = nb_missions // nb_annees
    dates = []
    for bloc in range(nb_annees):
        debut, fin = bloc * 365, bloc * 365 + 364
        for _ in range(par_bloc):
            dates.append(aujourd_hui - datetime.timedelta(days=random.randint(debut, fin)))
    # Reliquat si nb_missions n'est pas un multiple exact de nb_annees.
    while len(dates) < nb_missions:
        dates.append(aujourd_hui - datetime.timedelta(days=random.randint(0, nb_annees * 365 - 1)))
    dates.sort()
    return dates


def _statut_pour_age(age_jours):
    """Statut plausible compte tenu de l'ancienneté : les missions récentes
    sont encore en amont du circuit, les plus anciennes très majoritairement
    clôturées — comme dans un vrai historique d'activité."""
    if age_jours < 30:
        choix = [StatutMission.BROUILLON, StatutMission.PLANIFIEE, StatutMission.EN_COURS]
        poids = [1, 2, 3]
    elif age_jours < 180:
        choix = [
            StatutMission.EN_COURS, StatutMission.QUESTIONNAIRE_COMPLETE,
            StatutMission.PV_GENERE, StatutMission.PV_SCAN_UPLOAD,
        ]
        poids = [2, 3, 2, 2]
    else:
        choix = [
            StatutMission.PV_SCAN_UPLOAD, StatutMission.RAPPORT_GENERE,
            StatutMission.RAPPORT_SCAN_UPLOAD, StatutMission.VALIDEE,
        ]
        poids = [1, 1, 1, 6]
    return random.choices(choix, weights=poids)[0]


def _tirer_evaluation(recence):
    """Verdict de conformité tiré aléatoirement, légèrement biaisé vers un
    meilleur taux pour les missions récentes (`recence` proche de 1) — pour
    illustrer une tendance d'amélioration dans le temps sur le graphe
    d'évolution du tableau de bord."""
    poids_cto = 15 + round(35 * recence)
    poids_cpa = 35
    poids_nc = max(5, 30 - round(15 * recence))
    poids_cpr = max(5, 20 - round(15 * recence))
    return random.choices(
        [EvaluationConformite.CTO, EvaluationConformite.CPA, EvaluationConformite.NC, EvaluationConformite.CPR],
        weights=[poids_cto, poids_cpa, poids_nc, poids_cpr],
    )[0]


def _remplir_traitements(mission, statut, recence):
    """Remplit les pages du questionnaire pour un sous-ensemble (ou la
    totalité, une fois le questionnaire marqué complet) des 10 traitements,
    avec une évaluation sur une partie d'entre eux dès que la mission a
    dépassé cette étape — pour obtenir une matrice « traitements audités »
    variable d'une structure à l'autre."""
    codes_traitements = [code for code, _ in Traitement.choices]
    if statut >= StatutMission.QUESTIONNAIRE_COMPLETE:
        codes_a_remplir = codes_traitements
    else:
        codes_a_remplir = random.sample(codes_traitements, random.randint(2, 8))

    codes_a_evaluer = set()
    if statut >= StatutMission.QUESTIONNAIRE_COMPLETE:
        codes_a_evaluer = set(random.sample(codes_a_remplir, random.randint(6, len(codes_a_remplir))))

    for reponse in mission.reponses.filter(traitement__in=codes_a_remplir):
        evaluation = _tirer_evaluation(recence) if reponse.traitement in codes_a_evaluer else None
        _remplir_reponse(reponse, evaluation=evaluation)


def _journaliser_progression(mission, utilisateur, statut):
    journaliser(mission, utilisateur, TypeAction.CREATION)
    if statut >= StatutMission.QUESTIONNAIRE_COMPLETE:
        journaliser(mission, utilisateur, TypeAction.QUESTIONNAIRE_COMPLETE)
    if statut >= StatutMission.PV_GENERE:
        journaliser(mission, utilisateur, TypeAction.PV_GENERE, fichier="pv_mission_demo.docx")
    if statut >= StatutMission.PV_SCAN_UPLOAD:
        journaliser(mission, utilisateur, TypeAction.SCAN_UPLOAD)
    if statut >= StatutMission.RAPPORT_GENERE:
        journaliser(mission, utilisateur, TypeAction.RAPPORT_GENERE, provisoire=True)
    if statut >= StatutMission.RAPPORT_SCAN_UPLOAD:
        journaliser(mission, utilisateur, TypeAction.RAPPORT_SCAN_UPLOAD)
    if statut >= StatutMission.VALIDEE:
        journaliser(mission, utilisateur, TypeAction.VALIDATION)


class Command(BaseCommand):
    help = (
        f"Crée {NB_MISSIONS} missions de contrôle de démonstration réparties sur "
        f"{NB_ANNEES} ans, à des statuts et niveaux de conformité variés (DEBUG uniquement)."
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_missions refuse de tourner avec DEBUG=False (données de test local uniquement).")

        call_command("seed_dev")

        deja_presentes = MissionControle.objects.filter(
            commentaires_observations__startswith=MARQUEUR_SEED
        ).count()
        if deja_presentes >= NB_MISSIONS:
            self.stdout.write(f"{NB_MISSIONS} missions de démo déjà présentes — génération ignorée.")
            return

        agents = {agent.external_id: agent for agent in AgentControleur.objects.all()}
        chef = agents.get("AG-001")
        autres_agents = [agents[eid] for eid in ("AG-002", "AG-003") if eid in agents]
        chef_user = chef.user if chef else None
        if not chef or not chef_user:
            raise CommandError("Agent chef AG-001 introuvable ou non lié à un utilisateur — vérifiez seed_dev.")

        random.seed(GRAINE_ALEATOIRE)

        entites = [EntiteControlee.objects.get_or_create(nom=nom)[0] for nom in ENTITES_DEMO]
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

        dates = _dates_reparties(NB_MISSIONS, NB_ANNEES)
        aujourd_hui = datetime.date.today()

        with transaction.atomic():
            for i, date_mission in enumerate(dates):
                age_jours = (aujourd_hui - date_mission).days
                recence = 1 - min(age_jours / (NB_ANNEES * 365), 1)
                statut = _statut_pour_age(age_jours)
                entite = random.choice(entites)

                mission = MissionControle.objects.create(
                    date_mission=date_mission,
                    commentaires_observations=f"{MARQUEUR_SEED} Mission de contrôle n°{i + 1}.",
                )
                mission.entites_controlees.add(entite)

                MembreGroupeControle.objects.create(mission=mission, agent=chef, role=RoleMission.CHEF)
                for agent in random.sample(autres_agents, k=min(random.randint(1, 2), len(autres_agents))):
                    MembreGroupeControle.objects.create(mission=mission, agent=agent, role=RoleMission.AGENT)

                for personne, infos in random.sample(personnes, k=random.randint(1, 2)):
                    PersonneInterrogee.objects.create(
                        mission=mission, personne=personne,
                        poste_snapshot=infos["poste"], service_snapshot=infos["service"],
                    )

                _remplir_traitements(mission, statut, recence)

                if statut >= StatutMission.PV_GENERE:
                    representant, _ = random.choice(personnes)
                    mission.mode_pv = random.choice(ModePV.values)
                    mission.nom_representant_entite = str(representant)
                    mission.heure_controle = "09h30"
                    mission.deliberation_numero = f"DEL-{date_mission.year}-{i + 1:03d}"
                    mission.lieu_signature = "Libreville"
                    mission.date_signature = date_mission + datetime.timedelta(days=5)
                    mission.heure_signature = "12h15"

                _journaliser_progression(mission, chef_user, statut)

                mission.statut = statut
                mission.save()

            self.stdout.write(self.style.SUCCESS(
                f"{NB_MISSIONS} missions de démo créées, réparties sur {NB_ANNEES} ans "
                f"({len(entites)} structures)."
            ))
