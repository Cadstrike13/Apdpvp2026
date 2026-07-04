from django.db import models

from core.models import CorbeilleManager, SoftDeleteManager, SoftDeleteMixin, SoftDeleteQuerySet, TousManager


class EntiteControleeQuerySet(SoftDeleteQuerySet):
    pass  # ajouter ici les filtres métier propres à EntiteControlee


class EntiteControleeManager(SoftDeleteManager):
    def get_queryset(self):
        return EntiteControleeQuerySet(self.model, using=self._db).actifs()


class EntiteControlee(SoftDeleteMixin, models.Model):
    nom = models.CharField(max_length=255)

    objects = EntiteControleeManager()
    tous = TousManager()
    corbeille = CorbeilleManager()

    class Meta:
        verbose_name = "Entité contrôlée"
        verbose_name_plural = "Entités contrôlées"

    def __str__(self):
        return self.nom
