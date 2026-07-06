from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from .models import AgentControleur
from .services import ApiAgentProvider, MockAgentProvider, get_agent_provider


class ProviderSelectionTests(TestCase):
    @override_settings(AGENTS_SOURCE="mock")
    def test_mock_par_defaut(self):
        self.assertIsInstance(get_agent_provider(), MockAgentProvider)

    @override_settings(AGENTS_SOURCE="api")
    def test_api_si_configure(self):
        self.assertIsInstance(get_agent_provider(), ApiAgentProvider)


class ApiAgentProviderTests(TestCase):
    @patch("requests.get")
    def test_fetch_agents_appelle_lapi_avec_le_token_et_retourne_la_liste(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "agents": [{"id": "AG-100", "nom": "Test", "prenom": "Api", "poste": "X"}]
        }
        mock_get.return_value = mock_response

        with override_settings(AGENTS_API_URL="https://example.test/agents", AGENTS_API_TOKEN="secret-token"):
            resultat = ApiAgentProvider().fetch_agents()

        self.assertEqual(resultat, [{"id": "AG-100", "nom": "Test", "prenom": "Api", "poste": "X"}])
        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], "https://example.test/agents")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret-token")
        mock_response.raise_for_status.assert_called_once()


class SyncAgentsCommandTests(TestCase):
    @override_settings(AGENTS_SOURCE="mock")
    def test_commande_synchronise_les_agents_du_mock(self):
        call_command("sync_agents")
        self.assertEqual(AgentControleur.objects.count(), 3)


class SyncFromSourceTests(TestCase):
    @override_settings(AGENTS_SOURCE="mock")
    def test_sync_cree_les_agents_du_mock(self):
        AgentControleur.objects.sync_from_source()

        self.assertEqual(AgentControleur.objects.count(), len(MockAgentProvider().fetch_agents()))
        agent = AgentControleur.objects.get(external_id="AG-001")
        self.assertEqual(agent.nom, "Obiang")

    @override_settings(AGENTS_SOURCE="mock")
    def test_sync_ne_duplique_pas_un_agent_soft_supprime(self):
        """update_or_create passe par `tous` : un agent soft-supprimé est mis à
        jour en place (pas de doublon sur external_id) mais reste supprimé —
        la resynchronisation ne restaure pas silencieusement un agent retiré."""
        AgentControleur.objects.sync_from_source()
        agent = AgentControleur.objects.get(external_id="AG-001")
        agent.delete()  # soft delete

        AgentControleur.objects.sync_from_source()

        self.assertEqual(AgentControleur.tous.filter(external_id="AG-001").count(), 1)
        self.assertTrue(AgentControleur.tous.get(external_id="AG-001").est_supprime)
