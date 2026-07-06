from django.core.management.base import BaseCommand

from employees.models import Employee
from remuneration.models import TauxCotisation, Salaire

# Taux indicatifs Gabon (à ajuster) : (code, libellé, part salariale %, part patronale %)
TAUX = [
    ("CNSS", "CNSS", 2.50, 20.10),
    ("CNAMGS", "CNAMGS", 1.00, 4.10),
]


class Command(BaseCommand):
    help = "Crée les taux de cotisation (CNSS/CNAMGS) et un salaire de base par agent."

    def handle(self, *args, **options):
        for code, libelle, sal, pat in TAUX:
            TauxCotisation.objects.get_or_create(
                code=code, defaults={"libelle": libelle, "taux_salarial": sal, "taux_patronal": pat})

        n = 0
        for emp in Employee.objects.all():
            if emp.salaire and not emp.salaires.exists():
                Salaire.objects.create(
                    employe=emp, montant_base=emp.salaire,
                    date_effet=emp.date_embauche, motif="Salaire initial")
                n += 1
        self.stdout.write(self.style.SUCCESS(
            f"Taux OK ({TauxCotisation.objects.count()}). {n} salaire(s) de base cree(s)."))
