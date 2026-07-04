from django.test import TestCase

from .models import EntiteControlee


class EntiteControleeSoftDeleteTests(TestCase):
    def test_delete_est_un_soft_delete(self):
        entite = EntiteControlee.objects.create(nom="ACME SA")
        entite.delete()

        self.assertFalse(EntiteControlee.objects.filter(pk=entite.pk).exists())
        self.assertTrue(EntiteControlee.tous.filter(pk=entite.pk).exists())
        self.assertTrue(EntiteControlee.corbeille.filter(pk=entite.pk).exists())

    def test_restaurer(self):
        entite = EntiteControlee.objects.create(nom="ACME SA")
        entite.delete()
        entite.restaurer()

        self.assertTrue(EntiteControlee.objects.filter(pk=entite.pk).exists())
        self.assertFalse(entite.est_supprime)

    def test_hard_delete(self):
        entite = EntiteControlee.objects.create(nom="ACME SA")
        entite.delete(using_hard_delete=True)

        self.assertFalse(EntiteControlee.tous.filter(pk=entite.pk).exists())
