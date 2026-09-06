from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from agents.models import AgentControleur
from entites.models import EntiteControlee
from personnes.models import Personne

from ..models import (
    ControleEntite,
    EvaluationConformite,
    JournalAction,
    MembreGroupeControle,
    MissionControle,
    PersonneInterrogee,
    ReponsePage1,
    RoleMission,
    StatutMission,
    Traitement,
    TypeAction,
    journaliser,
)


def creer_controle(**kwargs):
    """`statut` est appliqué via un save() séparé, après la création — comme
    dans l'usage réel — pour que le signal post_save (création des 10
    ReponseTraitement) s'exécute pendant que le contrôle est encore
    BROUILLON, jamais déjà verrouillé."""
    entite = kwargs.pop("entite", None) or EntiteControlee.objects.create(nom="ACME SA")
    mission = kwargs.pop("mission", None) or MissionControle.objects.create(date_mission="2026-07-01")
    statut = kwargs.pop("statut", None)
    controle = ControleEntite.objects.create(mission=mission, entite=entite, **kwargs)
    if statut is not None:
        controle.statut = statut
        controle.save()
    return controle


class SignalCreationReponsesTests(TestCase):
    def test_creation_controle_genere_10_reponses_et_5_pages_chacune(self):
        controle = creer_controle()

        self.assertEqual(controle.reponses.count(), len(Traitement.choices))
        for reponse in controle.reponses.all():
            self.assertTrue(hasattr(reponse, "page1"))
            self.assertTrue(hasattr(reponse, "page2"))
            self.assertTrue(hasattr(reponse, "page3"))
            self.assertTrue(hasattr(reponse, "page4"))
            self.assertTrue(hasattr(reponse, "page5"))

    def test_sauvegarde_ulterieure_ne_recree_pas_de_reponses(self):
        controle = creer_controle()
        controle.commentaires_observations = "mise à jour"
        controle.save()

        self.assertEqual(controle.reponses.count(), len(Traitement.choices))


class StatutGeneralMissionTests(TestCase):
    """MissionControle.statut_general : vue agrégée (le minimum des statuts
    de ses ControleEntite) — chaque entité garde son propre circuit réel."""

    def test_brouillon_si_aucune_entite(self):
        mission = MissionControle.objects.create(date_mission="2026-07-01")
        self.assertEqual(mission.statut_general, StatutMission.BROUILLON)

    def test_reflete_lentite_la_moins_avancee(self):
        mission = MissionControle.objects.create(date_mission="2026-07-01")
        controle_avance = creer_controle(mission=mission, statut=StatutMission.VALIDEE)
        controle_retard = creer_controle(
            mission=mission, entite=EntiteControlee.objects.create(nom="Beta SARL"),
            statut=StatutMission.EN_COURS,
        )

        self.assertEqual(mission.statut_general, StatutMission.EN_COURS)
        # Chaque entité garde son statut propre, non écrasé par l'agrégat.
        self.assertEqual(controle_avance.statut, StatutMission.VALIDEE)
        self.assertEqual(controle_retard.statut, StatutMission.EN_COURS)


class VerrouillagePostGenerationTests(TestCase):
    def setUp(self):
        self.controle = creer_controle()

    def test_non_verrouille_par_defaut(self):
        self.assertFalse(self.controle.est_verrouillee)

    def test_statut_css_classes_couvre_tous_les_statuts(self):
        from ..models import COULEURS_STATUT

        for statut, _ in StatutMission.choices:
            self.assertIn(statut, COULEURS_STATUT, msg=f"statut {statut} sans couleur dédiée")

        self.controle.statut = StatutMission.VALIDEE
        self.assertIn("green", self.controle.statut_css_classes)

    def test_verrouille_a_partir_du_pv_genere(self):
        self.controle.statut = StatutMission.PV_GENERE
        self.controle.save()
        self.assertTrue(self.controle.est_verrouillee)

    def test_date_mission_immuable_apres_verrouillage_dune_entite(self):
        self.controle.statut = StatutMission.PV_GENERE
        self.controle.save()

        mission = self.controle.mission
        mission.date_mission = "2026-08-01"
        with self.assertRaises(ValidationError):
            mission.save()

    def test_controle_non_supprimable_apres_verrouillage(self):
        self.controle.statut = StatutMission.PV_GENERE
        self.controle.save()

        with self.assertRaises(ValidationError):
            self.controle.delete()

    def test_controle_supprimable_si_non_verrouille(self):
        self.controle.delete()
        self.assertFalse(ControleEntite.objects.filter(pk=self.controle.pk).exists())

    def test_commentaires_observations_reste_modifiable_apres_verrouillage(self):
        self.controle.statut = StatutMission.PV_GENERE
        self.controle.save()

        self.controle.commentaires_observations = "toujours modifiable"
        self.controle.save()  # ne doit pas lever

        self.controle.refresh_from_db()
        self.assertEqual(self.controle.commentaires_observations, "toujours modifiable")

    def test_date_mission_identique_ne_declenche_pas_le_verrou(self):
        self.controle.statut = StatutMission.PV_GENERE
        self.controle.save()

        mission = self.controle.mission
        mission.date_mission = mission.date_mission  # même valeur
        mission.save()  # ne doit pas lever

    def test_une_autre_entite_non_verrouillee_reste_librement_modifiable(self):
        """Le verrouillage est propre à chaque ControleEntite — une autre
        entité de la même mission, non verrouillée, n'est pas affectée."""
        self.controle.statut = StatutMission.PV_GENERE
        self.controle.save()

        autre_controle = creer_controle(
            mission=self.controle.mission, entite=EntiteControlee.objects.create(nom="Beta SARL"),
        )
        autre_controle.delete()  # ne doit pas lever
        self.assertFalse(ControleEntite.objects.filter(pk=autre_controle.pk).exists())


class MembreGroupeControleTests(TestCase):
    def setUp(self):
        self.controle = creer_controle()
        self.agent1 = AgentControleur.objects.create(external_id="AG-001", nom="Obiang", prenom="Marie")
        self.agent2 = AgentControleur.objects.create(external_id="AG-002", nom="Ndong", prenom="Paul")

    def test_un_seul_chef_par_controle(self):
        MembreGroupeControle.objects.create(controle=self.controle, agent=self.agent1, role=RoleMission.CHEF)
        with self.assertRaises(ValidationError):
            MembreGroupeControle.objects.create(controle=self.controle, agent=self.agent2, role=RoleMission.CHEF)

    def test_chefs_queryset(self):
        MembreGroupeControle.objects.create(controle=self.controle, agent=self.agent1, role=RoleMission.CHEF)
        MembreGroupeControle.objects.create(controle=self.controle, agent=self.agent2, role=RoleMission.AGENT)

        self.assertEqual(self.controle.membres_groupe.chefs().count(), 1)
        self.assertEqual(self.controle.membres_groupe.chefs().first().agent, self.agent1)

    def test_ajout_impossible_si_controle_verrouille(self):
        self.controle.statut = StatutMission.PV_GENERE
        self.controle.save()

        with self.assertRaises(ValidationError):
            MembreGroupeControle.objects.create(controle=self.controle, agent=self.agent1, role=RoleMission.AGENT)

    def test_suppression_impossible_si_controle_verrouille(self):
        membre = MembreGroupeControle.objects.create(controle=self.controle, agent=self.agent1, role=RoleMission.AGENT)
        self.controle.statut = StatutMission.PV_GENERE
        self.controle.save()

        with self.assertRaises(ValidationError):
            membre.delete()

    def test_suppression_reussie_si_controle_non_verrouille(self):
        membre = MembreGroupeControle.objects.create(controle=self.controle, agent=self.agent1, role=RoleMission.AGENT)
        membre.delete()
        self.assertEqual(self.controle.membres_groupe.count(), 0)


class PersonneInterrogeeTests(TestCase):
    def setUp(self):
        self.controle = creer_controle()
        self.personne = Personne.objects.create(nom="Mba", prenom="Sylvie")

    def test_ajout_impossible_si_controle_verrouille(self):
        self.controle.statut = StatutMission.PV_GENERE
        self.controle.save()

        with self.assertRaises(ValidationError):
            PersonneInterrogee.objects.create(controle=self.controle, personne=self.personne)

    def test_suppression_impossible_si_controle_verrouille(self):
        pi = PersonneInterrogee.objects.create(controle=self.controle, personne=self.personne)
        self.controle.statut = StatutMission.PV_GENERE
        self.controle.save()

        with self.assertRaises(ValidationError):
            pi.delete()

    def test_suppression_reussie_si_controle_non_verrouille(self):
        pi = PersonneInterrogee.objects.create(controle=self.controle, personne=self.personne)
        pi.delete()
        self.assertEqual(self.controle.personnes_interrogees.count(), 0)


class ReponsePageVerrouillageTests(TestCase):
    def setUp(self):
        self.controle = creer_controle()
        self.reponse = self.controle.reponses.first()

    def test_edition_impossible_si_controle_verrouille(self):
        self.controle.statut = StatutMission.PV_GENERE
        self.controle.save()

        self.reponse.page1.declaration_effectuee = True
        with self.assertRaises(ValidationError):
            self.reponse.page1.save()

    def test_suppression_impossible_si_controle_verrouille(self):
        self.controle.statut = StatutMission.PV_GENERE
        self.controle.save()

        with self.assertRaises(ValidationError):
            self.reponse.page1.delete()

    def test_suppression_reussie_si_controle_non_verrouille(self):
        self.reponse.page1.delete()
        self.assertFalse(ReponsePage1.objects.filter(reponse=self.reponse).exists())


class PourcentageCompleteTests(TestCase):
    def setUp(self):
        self.controle = creer_controle()

    def test_zero_pourcent_par_defaut(self):
        for reponse in self.controle.reponses.all():
            self.assertEqual(reponse.pourcentage_complete, 0)

    def test_augmente_apres_remplissage(self):
        reponse_a = self.controle.reponses.get(traitement=Traitement.GESTION_PERSONNEL)
        reponse_a.page1.declaration_effectuee = True
        reponse_a.page1.save()
        self.assertGreater(reponse_a.pourcentage_complete, 0)

    def test_champs_conditionnels_comptes_uniquement_pour_le_bon_traitement(self):
        reponse_a = self.controle.reponses.get(traitement=Traitement.GESTION_PERSONNEL)
        reponse_j = self.controle.reponses.get(traitement=Traitement.GEOLOCALISATION)

        reponse_j.page1.type_objet_geolocalise = "Véhicule"
        reponse_j.page1.save()

        self.assertGreater(reponse_j.pourcentage_complete, 0)
        self.assertEqual(reponse_a.pourcentage_complete, 0)


class SuggestionVerdictTests(TestCase):
    def setUp(self):
        self.controle = creer_controle()
        self.reponse_a = self.controle.reponses.get(traitement=Traitement.GESTION_PERSONNEL)

    def test_aucun_critere_rempli_suggere_constatation_preoccupante(self):
        suggestion = self.reponse_a.suggestion_verdict()
        self.assertEqual(suggestion["verdict"], EvaluationConformite.CPR)
        self.assertEqual(suggestion["pourcentage"], 0)

    def test_tous_les_criteres_remplis_suggere_conformite_totale(self):
        page1 = self.reponse_a.page1
        page1.declaration_effectuee = True
        page1.droits_respectes = True
        page1.save()

        page3 = self.reponse_a.page3
        page3.duree_conservation = "5 ans"
        page3.save()

        page4 = self.reponse_a.page4
        page4.personnes_habilitees_noms = "M. Test"
        page4.save()

        page5 = self.reponse_a.page5
        page5.mesures_organisationnelles = "Politique interne"
        page5.mesures_techniques = "Chiffrement"
        page5.save()

        suggestion = self.reponse_a.suggestion_verdict()
        self.assertEqual(suggestion["verdict"], EvaluationConformite.CTO)
        self.assertEqual(suggestion["pourcentage"], 100)

    def test_criteres_sous_traitance_ignores_si_aucun_sous_traitant(self):
        # nombre_sous_traitants n'est pas renseigné -> les 2 critères de
        # sous-traitance ne doivent pas compter dans le total.
        labels = [c["label"] for c in self.reponse_a.suggestion_verdict()["details"]]
        self.assertNotIn("Contrat de sous-traitance en place", labels)
        self.assertNotIn("Sous-traitant(s) déclaré(s)", labels)

    def test_criteres_sous_traitance_comptes_si_sous_traitants_declares(self):
        page2 = self.reponse_a.page2
        page2.nombre_sous_traitants = 2
        page2.contrat_sous_traitance = True
        page2.sous_traitants_declares = True
        page2.save()

        labels = [c["label"] for c in self.reponse_a.suggestion_verdict()["details"]]
        self.assertIn("Contrat de sous-traitance en place", labels)
        self.assertIn("Sous-traitant(s) déclaré(s)", labels)

    def test_critere_listing_cameras_uniquement_pour_f_et_g(self):
        reponse_f = self.controle.reponses.get(traitement=Traitement.TELE_VIDEOSURVEILLANCE)
        labels_f = [c["label"] for c in reponse_f.suggestion_verdict()["details"]]
        labels_a = [c["label"] for c in self.reponse_a.suggestion_verdict()["details"]]
        self.assertIn("Listing des caméras disponible", labels_f)
        self.assertNotIn("Listing des caméras disponible", labels_a)

    def test_critere_autorite_protection_uniquement_pour_h(self):
        reponse_h = self.controle.reponses.get(traitement=Traitement.TRANSFERT_DONNEES)
        labels_h = [c["label"] for c in reponse_h.suggestion_verdict()["details"]]
        labels_a = [c["label"] for c in self.reponse_a.suggestion_verdict()["details"]]
        self.assertIn("Autorité de protection du pays destinataire documentée", labels_h)
        self.assertNotIn("Autorité de protection du pays destinataire documentée", labels_a)

    def test_verdicts_intermediaires(self):
        # 6 critères applicables pour "a" (déclaration, droits, mesures x2,
        # personnes habilitées, durée) — 2/6 = 33% -> CPR ; 4/6 = 67% -> NC.
        page1 = self.reponse_a.page1
        page1.declaration_effectuee = True
        page1.droits_respectes = True
        page1.save()
        self.assertEqual(self.reponse_a.suggestion_verdict()["verdict"], EvaluationConformite.CPR)

        page5 = self.reponse_a.page5
        page5.mesures_organisationnelles = "Politique interne"
        page5.mesures_techniques = "Chiffrement"
        page5.save()
        self.assertEqual(self.reponse_a.suggestion_verdict()["verdict"], EvaluationConformite.NC)

        page4 = self.reponse_a.page4
        page4.personnes_habilitees_noms = "M. Test"
        page4.save()
        # 5/6 = 83% -> CPA (>= 70 % et < 100 %).
        self.assertEqual(self.reponse_a.suggestion_verdict()["verdict"], EvaluationConformite.CPA)

    def test_non_declare_plafonne_le_verdict_a_non_conforme(self):
        """Règle métier : un traitement non déclaré n'est jamais jugé
        conforme (CTO/CPA), même si tous les autres critères sont respectés —
        le verdict est plafonné à NC (voir calcul_conformite.md)."""
        page1 = self.reponse_a.page1
        page1.declaration_effectuee = False
        page1.droits_respectes = True
        page1.save()

        page3 = self.reponse_a.page3
        page3.duree_conservation = "5 ans"
        page3.save()

        page4 = self.reponse_a.page4
        page4.personnes_habilitees_noms = "M. Test"
        page4.save()

        page5 = self.reponse_a.page5
        page5.mesures_organisationnelles = "Politique interne"
        page5.mesures_techniques = "Chiffrement"
        page5.save()

        suggestion = self.reponse_a.suggestion_verdict()
        # 5/6 = 83% aurait donné CPA si déclaré — plafonné à NC ici.
        self.assertEqual(suggestion["pourcentage"], 83)
        self.assertEqual(suggestion["verdict"], EvaluationConformite.NC)

    def test_non_declare_n_ameliore_pas_un_score_deja_preoccupant(self):
        """La règle de plafonnement n'améliore jamais un verdict déjà pire
        que NC : un score très faible reste CPR, pas NC."""
        suggestion = self.reponse_a.suggestion_verdict()
        self.assertFalse(self.reponse_a.page1.declaration_effectuee)
        self.assertEqual(suggestion["verdict"], EvaluationConformite.CPR)


class JournalActionTests(TestCase):
    def test_journaliser_cree_une_entree(self):
        controle = creer_controle()
        utilisateur = User.objects.create_user(username="chef")

        entree = journaliser(controle, utilisateur, TypeAction.CREATION, note="premier essai")

        self.assertEqual(JournalAction.objects.count(), 1)
        self.assertEqual(entree.details, {"note": "premier essai"})
        self.assertEqual(controle.journal.first(), entree)
