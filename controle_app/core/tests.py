from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .permissions import GROUPE_CHEF_MISSION, est_dans_groupe


class EstDansGroupeTests(TestCase):
    def test_superuser_toujours_autorise(self):
        superuser = User.objects.create_superuser(username="admin", password="x", email="a@a.com")
        self.assertTrue(est_dans_groupe(superuser, GROUPE_CHEF_MISSION))

    def test_utilisateur_du_bon_groupe_autorise(self):
        user = User.objects.create_user(username="chef")
        groupe = Group.objects.create(name=GROUPE_CHEF_MISSION)
        user.groups.add(groupe)
        self.assertTrue(est_dans_groupe(user, GROUPE_CHEF_MISSION))

    def test_utilisateur_hors_groupe_refuse(self):
        user = User.objects.create_user(username="lambda")
        self.assertFalse(est_dans_groupe(user, GROUPE_CHEF_MISSION))


class IndexViewTests(TestCase):
    def test_anonyme_voit_la_page_index(self):
        r = self.client.get(reverse("index"))
        self.assertEqual(r.status_code, 200)

    def test_utilisateur_connecte_redirige_vers_le_dashboard(self):
        User.objects.create_user(username="quelconque", password="pass-123")
        self.client.login(username="quelconque", password="pass-123")
        r = self.client.get(reverse("index"))
        self.assertRedirects(r, reverse("missions:mission_list"))
