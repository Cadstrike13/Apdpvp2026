import datetime

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

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


class Command(BaseCommand):
    help = "Crée 3 missions de contrôle de démonstration à des statuts différents (DEBUG uniquement)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_missions refuse de tourner avec DEBUG=False (données de test local uniquement).")

        call_command("seed_dev")

        agents = {agent.external_id: agent for agent in AgentControleur.objects.all()}
        chef = agents.get("AG-001")
        agent_principal = agents.get("AG-002")
        agent_secondaire = agents.get("AG-003")
        chef_user = chef.user if chef else None
        if not chef or not chef_user:
            raise CommandError("Agent chef AG-001 introuvable ou non lié à un utilisateur — vérifiez seed_dev.")

        aujourd_hui = datetime.date.today()

        personne_interrogee, _ = Personne.objects.get_or_create(
            nom="Ondo", prenom="Jean", defaults={"email": "j.ondo@exemple-demo.ga"},
        )

        # --- Mission 1 : en cours (questionnaire partiellement rempli) ---
        entite_1, _ = EntiteControlee.objects.get_or_create(nom="ACME SA (démo)")
        if not MissionControle.objects.filter(entite_controlee=entite_1).exists():
            mission_1 = MissionControle.objects.create(
                entite_controlee=entite_1,
                date_mission=aujourd_hui - datetime.timedelta(days=5),
                commentaires_observations="Contrôle initié, questionnaire en cours de remplissage.",
            )
            MembreGroupeControle.objects.create(mission=mission_1, agent=chef, role=RoleMission.CHEF)
            if agent_principal:
                MembreGroupeControle.objects.create(mission=mission_1, agent=agent_principal, role=RoleMission.AGENT)
            PersonneInterrogee.objects.create(
                mission=mission_1, personne=personne_interrogee,
                poste_snapshot="Responsable administratif", service_snapshot="Administration",
            )
            # Seuls 2 des 10 traitements sont déjà traités — le reste attend encore.
            for reponse in mission_1.reponses.filter(traitement__in=[Traitement.GESTION_PERSONNEL, Traitement.GESTION_CLIENTS]):
                _remplir_reponse(reponse)
            journaliser(mission_1, chef_user, TypeAction.CREATION)
            mission_1.statut = StatutMission.EN_COURS
            mission_1.save()
            self.stdout.write(self.style.SUCCESS(f"Mission créée (en cours) : {mission_1}"))
        else:
            self.stdout.write("Mission 'en cours' déjà présente — ignorée.")

        # --- Mission 2 : questionnaire complété (prête pour le PV) ---
        entite_2, _ = EntiteControlee.objects.get_or_create(nom="Société Gabonaise de Transport (démo)")
        if not MissionControle.objects.filter(entite_controlee=entite_2).exists():
            mission_2 = MissionControle.objects.create(
                entite_controlee=entite_2,
                date_mission=aujourd_hui - datetime.timedelta(days=15),
                commentaires_observations="Questionnaire complété, évaluation réalisée, en attente du procès-verbal.",
            )
            MembreGroupeControle.objects.create(mission=mission_2, agent=chef, role=RoleMission.CHEF)
            if agent_principal:
                MembreGroupeControle.objects.create(mission=mission_2, agent=agent_principal, role=RoleMission.AGENT)
            PersonneInterrogee.objects.create(
                mission=mission_2, personne=personne_interrogee,
                poste_snapshot="Responsable administratif", service_snapshot="Administration",
            )
            evaluations = [
                EvaluationConformite.CTO, EvaluationConformite.CTO, EvaluationConformite.CPA,
                EvaluationConformite.CPA, EvaluationConformite.NC, EvaluationConformite.CTO,
                EvaluationConformite.CPA, EvaluationConformite.CTO, EvaluationConformite.CPR,
                EvaluationConformite.CTO,
            ]
            for reponse, evaluation in zip(mission_2.reponses.order_by("traitement"), evaluations):
                _remplir_reponse(reponse, evaluation=evaluation)
            journaliser(mission_2, chef_user, TypeAction.CREATION)
            journaliser(mission_2, chef_user, TypeAction.QUESTIONNAIRE_COMPLETE)
            mission_2.statut = StatutMission.QUESTIONNAIRE_COMPLETE
            mission_2.save()
            self.stdout.write(self.style.SUCCESS(f"Mission créée (questionnaire complété) : {mission_2}"))
        else:
            self.stdout.write("Mission 'questionnaire complété' déjà présente — ignorée.")

        # --- Mission 3 : validée (circuit de clôture terminé) ---
        entite_3, _ = EntiteControlee.objects.get_or_create(nom="Clinique Sainte-Marie (démo)")
        if not MissionControle.objects.filter(entite_controlee=entite_3).exists():
            mission_3 = MissionControle.objects.create(
                entite_controlee=entite_3,
                date_mission=aujourd_hui - datetime.timedelta(days=45),
                commentaires_observations="Mission clôturée et validée.",
                mode_pv=ModePV.IN_SITU,
                nom_representant_entite="Dr. Nzamba Alice",
                heure_controle="09h30",
                deliberation_numero="DEL-2025-014",
                lieu_signature="Libreville",
                date_signature=aujourd_hui - datetime.timedelta(days=40),
                heure_signature="12h15",
            )
            MembreGroupeControle.objects.create(mission=mission_3, agent=chef, role=RoleMission.CHEF)
            if agent_secondaire:
                MembreGroupeControle.objects.create(mission=mission_3, agent=agent_secondaire, role=RoleMission.AGENT)
            PersonneInterrogee.objects.create(
                mission=mission_3, personne=personne_interrogee,
                poste_snapshot="Directrice administrative", service_snapshot="Direction",
            )
            for reponse in mission_3.reponses.order_by("traitement"):
                _remplir_reponse(reponse, evaluation=EvaluationConformite.CTO)

            utilisateur = chef_user
            journaliser(mission_3, utilisateur, TypeAction.CREATION)
            journaliser(mission_3, utilisateur, TypeAction.QUESTIONNAIRE_COMPLETE)
            journaliser(mission_3, utilisateur, TypeAction.PV_GENERE, fichier="pv_mission_demo.docx")
            journaliser(mission_3, utilisateur, TypeAction.SCAN_UPLOAD)
            journaliser(mission_3, utilisateur, TypeAction.RAPPORT_GENERE, provisoire=True)
            journaliser(mission_3, utilisateur, TypeAction.RAPPORT_SCAN_UPLOAD)
            journaliser(mission_3, utilisateur, TypeAction.VALIDATION)
            # Les documents PV/rapport ne sont pas générés/uploadés pour cette
            # donnée de démo (pas de vrais fichiers) — seul le statut avance ;
            # les templates gèrent déjà l'absence de ces fichiers.
            mission_3.statut = StatutMission.VALIDEE
            mission_3.save()
            self.stdout.write(self.style.SUCCESS(f"Mission créée (validée) : {mission_3}"))
        else:
            self.stdout.write("Mission 'validée' déjà présente — ignorée.")
