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
    TYPE_DEMANDE_CHOICES = [
        ("emploi", "Demande d'emploi"),
        ("stage", "Demande de stage"),
    ]
    PRIORITE_CHOICES = [
        ("normale", "Normale"),
        ("importante", "Importante"),
        ("urgente", "Urgente"),
    ]
    # Poids pour le tri (urgente en premier)
    PRIORITE_ORDRE = {"urgente": 0, "importante": 1, "normale": 2}

    offre = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name="candidats", null=True, blank=True)
    type_demande = models.CharField(max_length=10, choices=TYPE_DEMANDE_CHOICES, default="emploi")
    priorite = models.CharField(max_length=12, choices=PRIORITE_CHOICES, default="normale")
    nom = models.CharField(max_length=200)
    email = models.EmailField()
    telephone = models.CharField(max_length=30, blank=True)
    date_candidature = models.DateField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default="examen")
    note = models.PositiveSmallIntegerField(default=0)  # /5
    cv = models.FileField(upload_to="cvs/", blank=True)
    lettre_motivation = models.FileField(upload_to="candidatures/lettres/", blank=True)

    class Meta:
        verbose_name = "Candidat"
        ordering = ["-date_candidature"]

    def __str__(self):
        return self.nom
