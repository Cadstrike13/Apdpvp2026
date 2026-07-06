from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from agents.models import AgentControleur
from entites.models import EntiteControlee

from .permissions import GROUPE_AGENT, GROUPE_CHEF_MISSION, est_dans_groupe, require_groupe
from .validators import ValidateurTailleFichier


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


class RequireGroupeTests(TestCase):
    """require_groupe n'est câblé sur aucune URL pour l'instant — testé en
    appelant directement le décorateur avec une fausse vue."""

    def setUp(self):
        self.factory = RequestFactory()

        @require_groupe(GROUPE_CHEF_MISSION)
        def vue_protegee(request):
            return "ok"

        self.vue_protegee = vue_protegee

    def test_utilisateur_du_bon_groupe_autorise(self):
        user = User.objects.create_user(username="chef")
        user.groups.add(Group.objects.create(name=GROUPE_CHEF_MISSION))
        request = self.factory.get("/")
        request.user = user
        self.assertEqual(self.vue_protegee(request), "ok")

    def test_utilisateur_hors_groupe_refuse(self):
        user = User.objects.create_user(username="agent")
        user.groups.add(Group.objects.create(name=GROUPE_AGENT))
        request = self.factory.get("/")
        request.user = user
        with self.assertRaises(PermissionDenied):
            self.vue_protegee(request)

    def test_superuser_toujours_autorise(self):
        superuser = User.objects.create_superuser(username="admin", password="x", email="a@a.com")
        request = self.factory.get("/")
        request.user = superuser
        self.assertEqual(self.vue_protegee(request), "ok")


class ValidateurTailleFichierTests(TestCase):
    def test_refuse_un_fichier_trop_volumineux(self):
        validateur = ValidateurTailleFichier(max_mo=1)
        gros_fichier = SimpleUploadedFile("gros.pdf", b"x" * (2 * 1024 * 1024))
        with self.assertRaises(Exception):
            validateur(gros_fichier)

    def test_accepte_un_fichier_dans_la_limite(self):
        validateur = ValidateurTailleFichier(max_mo=1)
        petit_fichier = SimpleUploadedFile("petit.pdf", b"x" * 1024)
        validateur(petit_fichier)  # ne doit pas lever

    def test_egalite_pour_la_stabilite_des_migrations(self):
        self.assertEqual(ValidateurTailleFichier(max_mo=10), ValidateurTailleFichier(max_mo=10))
        self.assertNotEqual(ValidateurTailleFichier(max_mo=10), ValidateurTailleFichier(max_mo=5))


class SoftDeleteQuerySetBulkTests(TestCase):
    """Comportement des managers/queryset au niveau bulk (pas juste
    instance.delete()) — voir core/models.py."""

    def test_supprimer_bulk_et_tous_manager(self):
        EntiteControlee.objects.create(nom="A")
        EntiteControlee.objects.create(nom="B")

        EntiteControlee.objects.all().supprimer()

        self.assertEqual(EntiteControlee.objects.count(), 0)
        self.assertEqual(EntiteControlee.tous.count(), 2)
        self.assertEqual(EntiteControlee.corbeille.count(), 2)

    def test_restaurer_bulk(self):
        EntiteControlee.objects.create(nom="A").delete()

        EntiteControlee.corbeille.all().restaurer()

        self.assertEqual(EntiteControlee.objects.count(), 1)
        self.assertEqual(EntiteControlee.corbeille.count(), 0)


class SetupGroupsCommandTests(TestCase):
    def test_cree_les_trois_groupes_avec_les_bonnes_permissions(self):
        call_command("setup_groups")

        self.assertEqual(Group.objects.count(), 3)
        administrateur = Group.objects.get(name="Administrateur")
        chef = Group.objects.get(name="Chef de mission")
        agent = Group.objects.get(name="Agent contrôleur")

        self.assertGreater(administrateur.permissions.count(), 0)
        self.assertTrue(chef.permissions.filter(codename="view_missioncontrole").exists())
        self.assertTrue(agent.permissions.filter(codename="add_personneinterrogee").exists())
        self.assertFalse(agent.permissions.filter(codename="delete_missioncontrole").exists())

    def test_idempotent(self):
        call_command("setup_groups")
        call_command("setup_groups")
        self.assertEqual(Group.objects.count(), 3)


class SeedDevCommandTests(TestCase):
    @override_settings(DEBUG=False)
    def test_refuse_si_debug_false(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("seed_dev")

    @override_settings(DEBUG=True)
    def test_cree_les_comptes_et_les_liens_agents(self):
        call_command("seed_dev")

        admin = User.objects.get(username="admin")
        self.assertTrue(admin.is_superuser)

        chef = User.objects.get(username="chef_test")
        self.assertTrue(chef.groups.filter(name=GROUPE_CHEF_MISSION).exists())
        self.assertEqual(AgentControleur.objects.get(external_id="AG-001").user, chef)

        agent = User.objects.get(username="agent_test")
        self.assertTrue(agent.groups.filter(name=GROUPE_AGENT).exists())
        self.assertEqual(AgentControleur.objects.get(external_id="AG-002").user, agent)

        self.assertTrue(EntiteControlee.objects.filter(nom="ACME SA (démo)").exists())

    @override_settings(DEBUG=True)
    def test_idempotent(self):
        call_command("seed_dev")
        call_command("seed_dev")

        self.assertEqual(User.objects.filter(username="admin").count(), 1)
        self.assertEqual(EntiteControlee.objects.filter(nom="ACME SA (démo)").count(), 1)
