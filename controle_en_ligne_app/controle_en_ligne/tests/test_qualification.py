from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from core.models import JournalAction
from controle_en_ligne.models import (
    ConstatCookie, ConstatFormulaire, ConstatSecurite, ConstatTiers, Qualification, modeles_constat,
)

from .outils import TestAvecMedia, creer_agent, creer_mission


class QualificationTests(TestAvecMedia):
    def setUp(self):
        self.mission = creer_mission()
        self.agent = creer_agent()
        self.securite = ConstatSecurite.objects.create(mission=self.mission, fait_observe="HTTPS complet.")

    def test_les_constats_ne_portent_plus_de_qualification(self):
        noms = {f.name for f in ConstatSecurite._meta.get_fields()}
        for champ in ("conformite", "criticite", "valide_par_agent", "analyse"):
            self.assertNotIn(champ, noms)

    def test_tous_les_constats_sont_soumis_au_verrou(self):
        self.assertIn(ConstatTiers, modeles_constat())
        self.assertIn(ConstatCookie, modeles_constat())
        self.assertEqual(len(modeles_constat()), 10)

    def test_qualifier_puis_valider(self):
        q = self.securite.qualifier(analyse="Conforme aux attentes.", conformite="conforme", criticite="faible")
        self.assertEqual(q.mission, self.mission)
        self.assertEqual(q.reference_grille, "H")
        self.assertFalse(self.securite.est_valide)

        q.valider(self.agent)
        q.refresh_from_db()
        self.assertTrue(self.securite.est_valide)
        self.assertEqual(q.agent, self.agent)
        self.assertIsNotNone(q.date_validation)
        self.assertTrue(JournalAction.objects.filter(action="validation", acteur=self.agent).exists())
        self.assertEqual(q.history.count(), 2)

    def test_valider_sans_conformite_est_refuse(self):
        q = self.securite.qualifier(analyse="Brouillon")
        with self.assertRaises(ValidationError) as erreur:
            q.valider(self.agent)
        self.assertIn("conformite", erreur.exception.message_dict)

    def test_non_applicable_se_valide_sans_criticite(self):
        q = self.securite.qualifier(conformite="non_applicable")
        q.valider(self.agent)
        self.assertTrue(self.securite.est_valide)

    def test_la_base_refuse_une_validation_sans_agent(self):
        q = self.securite.qualifier(conformite="non_conforme", criticite="elevee")
        q.valide_par_agent = True
        with self.assertRaises(IntegrityError), transaction.atomic():
            q.save()

    def test_une_seule_qualification_par_constat(self):
        self.securite.qualifier(conformite="conforme", criticite="faible")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Qualification.objects.create(constat=self.securite, mission=self.mission)

    def test_partiellement_conforme_tient_dans_la_colonne(self):
        q = self.securite.qualifier(conformite="partiellement_conforme", criticite="moderee")
        q.refresh_from_db()
        self.assertEqual(q.conformite, "partiellement_conforme")

    def test_devalider_rouvre_le_verrou(self):
        q = self.securite.qualifier(conformite="conforme", criticite="faible")
        q.valider(self.agent)
        q.devalider(self.agent, "Nouveau relevé à examiner")
        self.assertFalse(self.securite.est_valide)
        self.assertIsNone(Qualification.objects.get(pk=q.pk).date_validation)


class VerrouDeClotureTests(TestAvecMedia):
    def setUp(self):
        self.mission = creer_mission()
        self.agent = creer_agent()

    def _valider(self, constat):
        constat.qualifier(conformite="conforme", criticite="faible").valider(self.agent)

    def test_mission_sans_constat(self):
        self.assertFalse(self.mission.tous_constats_valides())

    def test_constats_uniques_et_multiples(self):
        securite = ConstatSecurite.objects.create(mission=self.mission)
        self._valider(securite)
        self.assertTrue(self.mission.tous_constats_valides())

        cookie = ConstatCookie.objects.create(
            mission=self.mission, scenario="avant", nom="_ga", domaine="google.com", est_tiers=True,
        )
        self.assertFalse(self.mission.tous_constats_valides())
        self.assertEqual(self.mission.bilan_validation(), (1, 2))

        self._valider(cookie)
        self.assertTrue(self.mission.tous_constats_valides())

        ConstatFormulaire.objects.create(mission=self.mission, url_formulaire="https://exemple.ga/contact")
        ConstatTiers.objects.create(mission=self.mission, domaine_tiers="cdn.x.com", categorie="autre")
        self.assertEqual(self.mission.bilan_validation(), (2, 4))

    def test_qualification_non_validee_ne_suffit_pas(self):
        securite = ConstatSecurite.objects.create(mission=self.mission)
        securite.qualifier(conformite="conforme", criticite="faible")
        self.assertFalse(self.mission.tous_constats_valides())

    def test_la_mission_ne_passe_pas_en_validee_sans_verrou(self):
        ConstatSecurite.objects.create(mission=self.mission)
        self.mission.statut = "validee"
        with self.assertRaises(ValidationError):
            self.mission.full_clean()
