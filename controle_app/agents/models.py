from django.conf import settings
from django.db import models

from core.models import CorbeilleManager, SoftDeleteManager, SoftDeleteMixin, SoftDeleteQuerySet, TousManager


class AgentControleurQuerySet(SoftDeleteQuerySet):
    pass


class AgentControleurManager(SoftDeleteManager):
    def get_queryset(self):
        return AgentControleurQuerySet(self.model, using=self._db).actifs()

    def sync_from_source(self):
        """Synchronise le pool d'agents depuis le provider configuré
        (AGENTS_SOURCE = mock en dev, api en prod). Un update_or_create par
        external_id — passe par `tous` pour retrouver aussi les agents
        soft-supprimés entre deux synchronisations."""
        from .services import get_agent_provider

        provider = get_agent_provider()
        for data in provider.fetch_agents():
            self.model.tous.update_or_create(
                external_id=data["id"],
                defaults={
                    "nom": data["nom"],
                    "prenom": data["prenom"],
                    "poste": data.get("poste", ""),
                },
            )


class AgentControleur(SoftDeleteMixin, models.Model):
    external_id = models.CharField(max_length=50, unique=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="agent_controleur"
    )
    nom = models.CharField(max_length=150)
    prenom = models.CharField(max_length=150)
    poste = models.CharField(max_length=255, blank=True)

    objects = AgentControleurManager()
    tous = TousManager()
    corbeille = CorbeilleManager()

    class Meta:
        verbose_name = "Agent contrôleur"
        verbose_name_plural = "Agents contrôleurs"

    def __str__(self):
        return f"{self.prenom} {self.nom}"
