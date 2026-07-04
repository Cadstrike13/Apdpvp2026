from django.conf import settings


class BaseAgentProvider:
    def fetch_agents(self) -> list[dict]:
        raise NotImplementedError


class MockAgentProvider(BaseAgentProvider):
    def fetch_agents(self):
        return [
            {"id": "AG-001", "nom": "Obiang", "prenom": "Marie", "poste": "Contrôleur senior"},
            {"id": "AG-002", "nom": "Ndong", "prenom": "Paul", "poste": "Contrôleur"},
            {"id": "AG-003", "nom": "Mba", "prenom": "Sylvie", "poste": "Juriste"},
        ]


class ApiAgentProvider(BaseAgentProvider):
    """Contrat supposé, en attente de la spec réelle de l'API agents en
    production (URL/auth/format de réponse à confirmer par l'utilisateur —
    voir AVANCEMENT.md). GET avec Bearer token, réponse {"agents": [...]}
    avec des objets {id, nom, prenom, poste} comme MockAgentProvider."""

    def fetch_agents(self):
        import requests

        resp = requests.get(
            settings.AGENTS_API_URL,
            timeout=10,
            headers={"Authorization": f"Bearer {settings.AGENTS_API_TOKEN}"},
        )
        resp.raise_for_status()
        return resp.json()["agents"]


def get_agent_provider() -> BaseAgentProvider:
    if getattr(settings, "AGENTS_SOURCE", "mock") == "api":
        return ApiAgentProvider()
    return MockAgentProvider()
