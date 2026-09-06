from datetime import date, timedelta

from django.core.management.base import BaseCommand

from actes.models import ActeAdministratif
from employees.models import Employee

# (type_acte, objet, offset date acte (jours), statut)
ACTES = [
    ("contrat_travail", "Contrat de travail initial", -365, "archive"),
    ("attestation_travail", "Attestation de travail", -30, "signe"),
    ("attestation_conge", "Attestation de congé annuel", -10, "emis"),
    ("bulletin_paie", "Bulletin de paie", -5, "signe"),
    ("lettre_promotion", "Lettre de promotion", -60, "brouillon"),
]


class Command(BaseCommand):
    help = "Crée des actes administratifs de démonstration pour les agents existants."

    def handle(self, *args, **options):
        employes = list(Employee.objects.all())
        if not employes:
            self.stdout.write(self.style.WARNING(
                "Aucun agent trouvé — lancez d'abord seed_users / seed_referentiels / seed_agents_details."))
            return

        redacteur = employes[0]
        n = 0
        for i, (type_acte, objet, offset_jours, statut) in enumerate(ACTES):
            emp = employes[i % len(employes)]
            date_acte = date.today() + timedelta(days=offset_jours)
            if ActeAdministratif.objects.filter(employe=emp, type_acte=type_acte, date_acte=date_acte).exists():
                continue
            ActeAdministratif.objects.create(
                employe=emp, type_acte=type_acte, objet=objet, date_acte=date_acte,
                statut=statut, redige_par=redacteur,
            )
            n += 1
        self.stdout.write(self.style.SUCCESS(f"{n} acte(s) administratif(s) créé(s)."))
