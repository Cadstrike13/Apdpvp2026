from django.db import models

from core.models import CorbeilleManager, SoftDeleteManager, SoftDeleteMixin, SoftDeleteQuerySet, TousManager


class PersonneQuerySet(SoftDeleteQuerySet):
    pass


class PersonneManager(SoftDeleteManager):
    def get_queryset(self):
        return PersonneQuerySet(self.model, using=self._db).actifs()


class Personne(SoftDeleteMixin, models.Model):
    nom = models.CharField(max_length=150)
    prenom = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    telephone = models.CharField(max_length=30, blank=True)

    objects = PersonneManager()
    tous = TousManager()
    corbeille = CorbeilleManager()

    class Meta:
        verbose_name = "Personne"
        verbose_name_plural = "Personnes"

    def __str__(self):
        return f"{self.prenom} {self.nom}"


class Fonction(models.Model):
    """Lien Personne <-> EntiteControlee : une personne peut avoir plusieurs
    fonctions dans plusieurs entités (ex: responsable de traitement chez
    plusieurs entreprises)."""

    personne = models.ForeignKey(Personne, on_delete=models.CASCADE, related_name="fonctions")
    entite = models.ForeignKey("entites.EntiteControlee", on_delete=models.CASCADE, related_name="fonctions")
    poste = models.CharField(max_length=255)
    service = models.CharField(max_length=255, blank=True)
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)  # null = fonction actuelle

    class Meta:
        unique_together = ("personne", "entite", "poste", "date_debut")
        verbose_name = "Fonction"
        verbose_name_plural = "Fonctions"

    def __str__(self):
        return f"{self.personne} — {self.poste} ({self.entite})"
