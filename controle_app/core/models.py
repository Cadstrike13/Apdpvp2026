from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def actifs(self):
        return self.filter(supprime_le__isnull=True)

    def supprimes(self):
        return self.filter(supprime_le__isnull=False)

    def supprimer(self):
        return self.update(supprime_le=timezone.now())

    def restaurer(self):
        return self.update(supprime_le=None)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).actifs()


class TousManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class CorbeilleManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).supprimes()


class SoftDeleteMixin(models.Model):
    """Modèles "catalogue" : EntiteControlee, AgentControleur, Personne, MissionControle."""

    supprime_le = models.DateTimeField(null=True, blank=True, editable=False)

    objects = SoftDeleteManager()
    tous = TousManager()
    corbeille = CorbeilleManager()

    class Meta:
        abstract = True

    def delete(self, *args, using_hard_delete=False, **kwargs):
        if using_hard_delete:
            return super().delete(*args, **kwargs)
        self.supprime_le = timezone.now()
        self.save(update_fields=["supprime_le"])

    def restaurer(self):
        self.supprime_le = None
        self.save(update_fields=["supprime_le"])

    @property
    def est_supprime(self):
        return self.supprime_le is not None
