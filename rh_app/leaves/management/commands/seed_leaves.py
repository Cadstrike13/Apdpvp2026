from datetime import date, timedelta

from django.core.management.base import BaseCommand

from employees.models import Employee
from leaves.models import LeaveRequest

# (offset début en jours depuis aujourd'hui, durée en jours, type, statut)
DEMANDES = [
    (-30, 10, "conge", "approuve"),
    (-5, 3, "maladie", "approuve"),
    (7, 14, "conge", "en_attente"),
    (20, 5, "conge", "en_attente"),
    (-60, 1, "autre", "refuse"),
]


class Command(BaseCommand):
    help = "Crée des demandes de congé de démonstration pour les agents existants."

    def handle(self, *args, **options):
        employes = list(Employee.objects.all())
        if not employes:
            self.stdout.write(self.style.WARNING(
                "Aucun agent trouvé — lancez d'abord seed_users / seed_referentiels / seed_agents_details."))
            return

        n = 0
        for i, (offset_debut, duree, type_conge, statut) in enumerate(DEMANDES):
            emp = employes[i % len(employes)]
            date_debut = date.today() + timedelta(days=offset_debut)
            date_fin = date_debut + timedelta(days=duree - 1)
            _, created = LeaveRequest.objects.get_or_create(
                employe=emp, type_conge=type_conge, date_debut=date_debut,
                defaults={
                    "date_fin": date_fin,
                    "statut": statut,
                    "motif": f"Demande de {LeaveRequest(type_conge=type_conge).get_type_conge_display().lower()}.",
                },
            )
            if created:
                n += 1
        self.stdout.write(self.style.SUCCESS(f"{n} demande(s) de congé créée(s)."))
