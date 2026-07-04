from django.db import IntegrityError, transaction
from django.test import TestCase

from entites.models import EntiteControlee

from .models import Fonction, Personne


class FonctionTests(TestCase):
    def setUp(self):
        self.personne = Personne.objects.create(nom="Ndong", prenom="Paul")
        self.entite = EntiteControlee.objects.create(nom="ACME SA")

    def test_une_personne_peut_avoir_plusieurs_fonctions_dans_des_entites_differentes(self):
        autre_entite = EntiteControlee.objects.create(nom="Beta SARL")
        Fonction.objects.create(personne=self.personne, entite=self.entite, poste="DRH")
        Fonction.objects.create(personne=self.personne, entite=autre_entite, poste="Consultant")

        self.assertEqual(self.personne.fonctions.count(), 2)

    def test_unicite_personne_entite_poste_date_debut(self):
        # NULL n'est jamais égal à NULL pour une contrainte unique — le test
        # doit donc porter sur un date_debut concret, pas sur `None`.
        Fonction.objects.create(personne=self.personne, entite=self.entite, poste="DRH", date_debut="2020-01-01")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Fonction.objects.create(
                    personne=self.personne, entite=self.entite, poste="DRH", date_debut="2020-01-01"
                )
