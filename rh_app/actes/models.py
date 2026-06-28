from datetime import date

from django.core.validators import FileExtensionValidator
from django.db import models

from core.models import SoftDeleteModel
from employees.models import Employee
from .choices import TYPE_ACTE_CHOICES


class ActeAdministratif(SoftDeleteModel):
    TYPE_CHOICES = TYPE_ACTE_CHOICES
    STATUS_CHOICES = [
        ("brouillon", "Brouillon"),
        ("emis", "Émis"),
        ("signe", "Signé"),
        ("archive", "Archivé"),
    ]

    reference = models.CharField(max_length=50, blank=True, help_text="Généré automatiquement si laissé vide.")
    employe = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="actes")
    type_acte = models.CharField(max_length=60, choices=TYPE_ACTE_CHOICES)
    objet = models.CharField(max_length=200)
    contenu = models.TextField(blank=True)
    date_acte = models.DateField()
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default="brouillon")
    # Document signé scanné, joint à l'acte (pièce justificative émise)
    fichier = models.FileField(
        upload_to="actes/",
        blank=True,
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png"])],
        verbose_name="Document signé scanné",
        help_text="Scan du document signé (PDF ou image). Obligatoire dès l'émission.",
    )
    redige_par = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="actes_rediges"
    )

    class Meta:
        verbose_name = "Acte administratif"
        verbose_name_plural = "Actes administratifs"
        ordering = ["-date_acte", "-id"]

    def __str__(self):
        return f"{self.reference or '(sans réf.)'} — {self.get_type_acte_display()}"

    @property
    def piece_jointe_presente(self):
        return bool(self.fichier)

    @classmethod
    def generer_reference(cls, annee):
        """Calcule la prochaine référence ACT-<annee>-NNN (en tenant compte des supprimés)."""
        prefixe = f"ACT-{annee}-"
        dernier = (
            cls.all_objects.filter(reference__startswith=prefixe)
            .order_by("-reference")
            .first()
        )
        suite = 1
        if dernier:
            reste = dernier.reference[len(prefixe):]
            if reste.isdigit():
                suite = int(reste) + 1
        return f"{prefixe}{suite:03d}"

    def save(self, *args, **kwargs):
        if not self.reference:
            annee = (self.date_acte or date.today()).year
            self.reference = self.generer_reference(annee)
        super().save(*args, **kwargs)
