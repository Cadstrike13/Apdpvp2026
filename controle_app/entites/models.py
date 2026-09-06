from django.db import models

from core.models import CorbeilleManager, SoftDeleteManager, SoftDeleteMixin, SoftDeleteQuerySet, TousManager


class SecteurActivite(models.TextChoices):
    """Secteur d'activité de l'entité contrôlée — alimente la répartition
    par secteur du tableau de bord des missions."""

    ADMINISTRATION = "administration", "Administration publique"
    BANQUE_FINANCE = "banque_finance", "Banque / Finance / Assurance"
    COMMERCE = "commerce", "Commerce"
    EDUCATION = "education", "Éducation"
    HOTELLERIE_RESTAURATION = "hotellerie_restauration", "Hôtellerie / Restauration"
    IMMOBILIER = "immobilier", "Immobilier"
    INDUSTRIE = "industrie", "Industrie"
    INFORMATIQUE_TELECOM = "informatique_telecom", "Informatique / Télécommunications"
    ONG_ASSOCIATION = "ong_association", "ONG / Association"
    SANTE = "sante", "Santé"
    TRANSPORT_LOGISTIQUE = "transport_logistique", "Transport / Logistique"
    AUTRE = "autre", "Autre"


class EntiteControleeQuerySet(SoftDeleteQuerySet):
    pass  # ajouter ici les filtres métier propres à EntiteControlee


class EntiteControleeManager(SoftDeleteManager):
    def get_queryset(self):
        return EntiteControleeQuerySet(self.model, using=self._db).actifs()


class EntiteControlee(SoftDeleteMixin, models.Model):
    nom = models.CharField(max_length=255)
    secteur_activite = models.CharField(
        "Secteur d'activité", max_length=30, choices=SecteurActivite.choices, blank=True,
    )

    objects = EntiteControleeManager()
    tous = TousManager()
    corbeille = CorbeilleManager()

    class Meta:
        verbose_name = "Entité contrôlée"
        verbose_name_plural = "Entités contrôlées"

    def __str__(self):
        return self.nom
