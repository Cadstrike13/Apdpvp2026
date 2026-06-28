from django.db import models

from core.models import SoftDeleteModel
from employees.models import Department


class JobPosting(SoftDeleteModel):
    STATUS_CHOICES = [("ouvert", "Ouvert"), ("ferme", "Fermé"), ("pourvu", "Pourvu")]

    titre = models.CharField(max_length=200)
    departement = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    lieu = models.CharField(max_length=100)
    date_publication = models.DateField(auto_now_add=True)
    date_limite = models.DateField()
    statut = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ouvert")
    description = models.TextField()

    class Meta:
        verbose_name = "Offre d'emploi"
        ordering = ["-date_publication"]

    def __str__(self):
        return self.titre


class Candidate(SoftDeleteModel):
    STATUS_CHOICES = [
        ("examen", "En examen"),
        ("entretien", "Entretien"),
        ("offre", "Offre"),
        ("refuse", "Refusé"),
    ]

    offre = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name="candidats")
    nom = models.CharField(max_length=200)
    email = models.EmailField()
    date_candidature = models.DateField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default="examen")
    note = models.PositiveSmallIntegerField(default=0)  # /5
    cv = models.FileField(upload_to="cvs/", blank=True)

    class Meta:
        verbose_name = "Candidat"
        ordering = ["-date_candidature"]

    def __str__(self):
        return self.nom
