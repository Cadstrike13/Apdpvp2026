from datetime import date, timedelta

from django.core.management.base import BaseCommand

from employees.models import Employee
from training.models import TrainingProgram

# (titre, prestataire, type, offset début (jours), durée (jours), heures, statut)
FORMATIONS = [
    ("Sécurité des systèmes d'information", "CyberGabon Formation", "technique", -45, 3, 21, "termine"),
    ("Communication interpersonnelle", "Institut National RH", "soft_skills", -10, 2, 14, "en_cours"),
    ("Management d'équipe", "École de Management d'Afrique", "management", 15, 5, 35, "planifie"),
    ("Excel avancé pour la gestion", "CyberGabon Formation", "technique", 30, 2, 14, "planifie"),
]


class Command(BaseCommand):
    help = "Crée des formations de démonstration et y inscrit des agents."

    def handle(self, *args, **options):
        employes = list(Employee.objects.all())
        if not employes:
            self.stdout.write(self.style.WARNING(
                "Aucun agent trouvé — lancez d'abord seed_users / seed_referentiels / seed_agents_details."))
            return

        n = 0
        for i, (titre, prestataire, type_formation, offset_debut, duree, heures, statut) in enumerate(FORMATIONS):
            date_debut = date.today() + timedelta(days=offset_debut)
            date_fin = date_debut + timedelta(days=duree - 1)
            formation, created = TrainingProgram.objects.get_or_create(
                titre=titre,
                defaults={
                    "prestataire": prestataire,
                    "type_formation": type_formation,
                    "date_debut": date_debut,
                    "date_fin": date_fin,
                    "duree_heures": heures,
                    "statut": statut,
                },
            )
            if created:
                participants = [employes[i % len(employes)], employes[(i + 1) % len(employes)]]
                formation.participants.add(*participants)
                n += 1
        self.stdout.write(self.style.SUCCESS(f"{n} formation(s) créée(s)."))
