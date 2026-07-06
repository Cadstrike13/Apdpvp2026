from django.db import models

from core.models import SoftDeleteModel
from employees.models import Employee, CategorieProfessionnelle


class Avancement(SoftDeleteModel):
    """Changement de catégorie professionnelle (promotion / avancement)."""

    employe = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="avancements")
    ancienne_categorie = models.ForeignKey(
        CategorieProfessionnelle, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    nouvelle_categorie = models.ForeignKey(
        CategorieProfessionnelle, on_delete=models.PROTECT, related_name="avancements"
    )
    date_effet = models.DateField()
    reference = models.CharField(max_length=50, blank=True)
    motif = models.TextField(blank=True)
    fichier = models.FileField(upload_to="avancements/", blank=True)

    class Meta:
        verbose_name = "Avancement"
        ordering = ["-date_effet"]

    def __str__(self):
        return f"Avancement {self.employe} → {self.nouvelle_categorie} ({self.date_effet})"

    def appliquer(self):
        """Applique l'avancement : met à jour la catégorie de l'agent."""
        if self.employe.categorie_id != self.nouvelle_categorie_id:
            self.employe.categorie = self.nouvelle_categorie
            self.employe.save(update_fields=["categorie", "updated_at"])
