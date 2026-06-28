from django.db import models

from core.models import SoftDeleteModel
from employees.models import Employee


class LeaveRequest(SoftDeleteModel):
    TYPE_CHOICES = [
        ("conge", "Congé annuel"),
        ("maladie", "Maladie"),
        ("maternite", "Maternité"),
        ("paternite", "Paternité"),
        ("autre", "Autre"),
    ]
    STATUS_CHOICES = [
        ("en_attente", "En attente"),
        ("approuve", "Approuvé"),
        ("refuse", "Refusé"),
    ]

    employe = models.ForeignKey(Employee, on_delete=models.CASCADE)
    type_conge = models.CharField(max_length=20, choices=TYPE_CHOICES)
    date_debut = models.DateField()
    date_fin = models.DateField()
    motif = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default="en_attente")
    date_demande = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Demande de congé"
        ordering = ["-date_demande"]

    def __str__(self):
        return f"{self.employe} — {self.get_type_conge_display()}"

    @property
    def nb_jours(self):
        return (self.date_fin - self.date_debut).days + 1
