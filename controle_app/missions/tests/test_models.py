from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from agents.models import AgentControleur
from entites.models import EntiteControlee
from personnes.models import Personne

from ..models import (
    JournalAction,
    MembreGroupeControle,
    MissionControle,
    PersonneInterrogee,
    RoleMission,
    StatutMission,
    Traitement,
    TypeAction,
    journaliser,
)


def creer_mission(**kwargs):
    entite = kwargs.pop("entite_controlee", None) or EntiteControlee.objects.create(nom="ACME SA")
    return MissionControle.objects.create(entite_controlee=entite, date_mission="2026-07-01", **kwargs)


class SignalCreationReponsesTests(TestCase):
    def test_creation_mission_genere_10_reponses_et_5_pages_chacune(self):
        mission = creer_mission()

        self.assertEqual(mission.reponses.count(), len(Traitement.choices))
        for reponse in mission.reponses.all():
            self.assertTrue(hasattr(reponse, "page1"))
            self.assertTrue(hasattr(reponse, "page2"))
            self.assertTrue(hasattr(reponse, "page3"))
            self.assertTrue(hasattr(reponse, "page4"))
            self.assertTrue(hasattr(reponse, "page5"))

    def test_sauvegarde_ulterieure_ne_recree_pas_de_reponses(self):
        mission = creer_mission()
        mission.commentaires_observations = "mise à jour"
        mission.save()

        self.assertEqual(mission.reponses.count(), len(Traitement.choices))


class VerrouillagePostGenerationTests(TestCase):
    def setUp(self):
        self.mission = creer_mission()

    def test_non_verrouillee_par_defaut(self):
        self.assertFalse(self.mission.est_verrouillee)

    def test_statut_css_classes_couvre_tous_les_statuts(self):
        from ..models import COULEURS_STATUT

        for statut, _ in StatutMission.choices:
            self.assertIn(statut, COULEURS_STATUT, msg=f"statut {statut} sans couleur dédiée")

        self.mission.statut = StatutMission.VALIDEE
        self.assertIn("green", self.mission.statut_css_classes)

    def test_verrouillee_a_partir_du_pv_genere(self):
        self.mission.statut = StatutMission.PV_GENERE
        self.mission.save()
        self.assertTrue(self.mission.est_verrouillee)

    def test_date_mission_immuable_apres_verrouillage(self):
        self.mission.statut = StatutMission.PV_GENERE
        self.mission.save()

        self.mission.date_mission = "2026-08-01"
        with self.assertRaises(ValidationError):
            self.mission.save()

    def test_entite_controlee_immuable_apres_verrouillage(self):
        autre_entite = EntiteControlee.objects.create(nom="Beta SARL")
        self.mission.statut = StatutMission.PV_GENERE
        self.mission.save()

        self.mission.entite_controlee = autre_entite
        with self.assertRaises(ValidationError):
            self.mission.save()

    def test_commentaires_observations_reste_modifiable_apres_verrouillage(self):
        self.mission.statut = StatutMission.PV_GENERE
        self.mission.save()

        self.mission.commentaires_observations = "toujours modifiable"
        self.mission.save()  # ne doit pas lever

        self.mission.refresh_from_db()
        self.assertEqual(self.mission.commentaires_observations, "toujours modifiable")


class MembreGroupeControleTests(TestCase):
    def setUp(self):
        self.mission = creer_mission()
        self.agent1 = AgentControleur.objects.create(external_id="AG-001", nom="Obiang", prenom="Marie")
        self.agent2 = AgentControleur.objects.create(external_id="AG-002", nom="Ndong", prenom="Paul")

    def test_un_seul_chef_par_mission(self):
        MembreGroupeControle.objects.create(mission=self.mission, agent=self.agent1, role=RoleMission.CHEF)
        with self.assertRaises(ValidationError):
            MembreGroupeControle.objects.create(mission=self.mission, agent=self.agent2, role=RoleMission.CHEF)

    def test_chefs_queryset(self):
        MembreGroupeControle.objects.create(mission=self.mission, agent=self.agent1, role=RoleMission.CHEF)
        MembreGroupeControle.objects.create(mission=self.mission, agent=self.agent2, role=RoleMission.AGENT)

        self.assertEqual(self.mission.membres_groupe.chefs().count(), 1)
        self.assertEqual(self.mission.membres_groupe.chefs().first().agent, self.agent1)

    def test_ajout_impossible_si_mission_verrouillee(self):
        self.mission.statut = StatutMission.PV_GENERE
        self.mission.save()

        with self.assertRaises(ValidationError):
            MembreGroupeControle.objects.create(mission=self.mission, agent=self.agent1, role=RoleMission.AGENT)

    def test_suppression_impossible_si_mission_verrouillee(self):
        membre = MembreGroupeControle.objects.create(mission=self.mission, agent=self.agent1, role=RoleMission.AGENT)
        self.mission.statut = StatutMission.PV_GENERE
        self.mission.save()

        with self.assertRaises(ValidationError):
            membre.delete()


class PersonneInterrogeeTests(TestCase):
    def setUp(self):
        self.mission = creer_mission()
        self.personne = Personne.objects.create(nom="Mba", prenom="Sylvie")

    def test_ajout_impossible_si_mission_verrouillee(self):
        self.mission.statut = StatutMission.PV_GENERE
        self.mission.save()

        with self.assertRaises(ValidationError):
            PersonneInterrogee.objects.create(mission=self.mission, personne=self.personne)

    def test_suppression_impossible_si_mission_verrouillee(self):
        pi = PersonneInterrogee.objects.create(mission=self.mission, personne=self.personne)
        self.mission.statut = StatutMission.PV_GENERE
        self.mission.save()

        with self.assertRaises(ValidationError):
            pi.delete()


class ReponsePageVerrouillageTests(TestCase):
    def setUp(self):
        self.mission = creer_mission()
        self.reponse = self.mission.reponses.first()

    def test_edition_impossible_si_mission_verrouillee(self):
        self.mission.statut = StatutMission.PV_GENERE
        self.mission.save()

        self.reponse.page1.declaration_effectuee = True
        with self.assertRaises(ValidationError):
            self.reponse.page1.save()

    def test_suppression_impossible_si_mission_verrouillee(self):
        self.mission.statut = StatutMission.PV_GENERE
        self.mission.save()

        with self.assertRaises(ValidationError):
            self.reponse.page1.delete()


class PourcentageCompleteTests(TestCase):
    def setUp(self):
        self.mission = creer_mission()

    def test_zero_pourcent_par_defaut(self):
        for reponse in self.mission.reponses.all():
            self.assertEqual(reponse.pourcentage_complete, 0)

    def test_augmente_apres_remplissage(self):
        reponse_a = self.mission.reponses.get(traitement=Traitement.GESTION_PERSONNEL)
        reponse_a.page1.declaration_effectuee = True
        reponse_a.page1.save()
        self.assertGreater(reponse_a.pourcentage_complete, 0)

    def test_champs_conditionnels_comptes_uniquement_pour_le_bon_traitement(self):
        reponse_a = self.mission.reponses.get(traitement=Traitement.GESTION_PERSONNEL)
        reponse_j = self.mission.reponses.get(traitement=Traitement.GEOLOCALISATION)

        reponse_j.page1.type_objet_geolocalise = "Véhicule"
        reponse_j.page1.save()

        self.assertGreater(reponse_j.pourcentage_complete, 0)
        self.assertEqual(reponse_a.pourcentage_complete, 0)


class JournalActionTests(TestCase):
    def test_journaliser_cree_une_entree(self):
        mission = creer_mission()
        utilisateur = User.objects.create_user(username="chef")

        entree = journaliser(mission, utilisateur, TypeAction.CREATION, note="premier essai")

        self.assertEqual(JournalAction.objects.count(), 1)
        self.assertEqual(entree.details, {"note": "premier essai"})
        self.assertEqual(mission.journal.first(), entree)
