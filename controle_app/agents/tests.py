from django.test import TestCase, override_settings

from .models import AgentControleur
from .services import MockAgentProvider, get_agent_provider


class ProviderSelectionTests(TestCase):
    @override_settings(AGENTS_SOURCE="mock")
    def test_mock_par_defaut(self):
        self.assertIsInstance(get_agent_provider(), MockAgentProvider)


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
