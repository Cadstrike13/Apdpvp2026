from django.db import models

from core.models import SoftDeleteModel
from employees.models import Employee


class Document(SoftDeleteModel):
    CATEGORY_CHOICES = [
        ("contrat", "Contrat"),
        ("politique", "Politique"),
        ("formation", "Formation"),
        ("evaluation", "Évaluation"),
        ("autre", "Autre"),
    ]

    nom = models.CharField(max_length=200)
    categorie = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    fichier = models.FileField(upload_to="documents/")
    uploade_par = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    date_upload = models.DateTimeField(auto_now_add=True)
    acces_employes = models.ManyToManyField(Employee, blank=True, related_name="documents_accessibles")

    class Meta:
        verbose_name = "Document"
        ordering = ["-date_upload"]

    def __str__(self):
        return self.nom

    @property
    def taille(self):
        try:
            return f"{self.fichier.size / 1024:.0f} KB"
        except Exception:
            return "N/A"
