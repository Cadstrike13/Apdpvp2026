from datetime import date

from django.db import models

from employees.models import Employee


class Rappel(models.Model):
    """Alerte RH générée à l'avance (J-21 / J-30) sur une échéance."""

    TYPE_CHOICES = [
        ("anniversaire", "Anniversaire"),
        ("anniversaire_service", "Anniversaire de service"),
        ("fin_contrat", "Fin de contrat"),
        ("conge", "Congé à venir"),
        ("avancement", "Avancement à examiner"),
    ]
    NIVEAU_CHOICES = [
        ("info", "Info"),
        ("important", "Important"),
        ("urgent", "Urgent"),
    ]

    type_rappel = models.CharField(max_length=30, choices=TYPE_CHOICES)
    employe = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True, blank=True, related_name="rappels")
    objet = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    date_echeance = models.DateField(db_index=True)
    niveau = models.CharField(max_length=10, choices=NIVEAU_CHOICES, default="info")
    traite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Rappel"
        ordering = ["traite", "date_echeance"]
        constraints = [
            models.UniqueConstraint(
                fields=["type_rappel", "employe", "date_echeance"],
                name="unique_rappel_type_employe_echeance",
            ),
        ]

    def __str__(self):
        return f"{self.get_type_rappel_display()} — {self.objet} ({self.date_echeance})"

    @property
    def jours_restants(self):
        return (self.date_echeance - date.today()).days
