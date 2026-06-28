from django.db import models

from core.models import SoftDeleteModel
from employees.models import Employee


class TrainingProgram(SoftDeleteModel):
    TYPE_CHOICES = [
        ("technique", "Technique"),
        ("soft_skills", "Soft-skills"),
        ("management", "Management"),
    ]
    STATUS_CHOICES = [
        ("planifie", "Planifié"),
        ("en_cours", "En cours"),
        ("termine", "Terminé"),
    ]

    titre = models.CharField(max_length=200)
    prestataire = models.CharField(max_length=200)
    type_formation = models.CharField(max_length=20, choices=TYPE_CHOICES)
    date_debut = models.DateField()
    date_fin = models.DateField()
    duree_heures = models.PositiveIntegerField()
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planifie")
    participants = models.ManyToManyField(Employee, blank=True)

    class Meta:
        verbose_name = "Formation"
        ordering = ["-date_debut"]

    def __str__(self):
        return self.titre

    @property
    def nb_participants(self):
        return self.participants.count()
