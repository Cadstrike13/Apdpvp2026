from datetime import date

from django.core.management.base import BaseCommand

from carriere.models import Avancement
from employees.models import CategorieProfessionnelle, Employee


class Command(BaseCommand):
    help = "Crée des avancements de démonstration pour les agents ayant une catégorie professionnelle."

    def handle(self, *args, **options):
        categories = list(CategorieProfessionnelle.objects.order_by("niveau"))
        if not categories:
            self.stdout.write(self.style.WARNING(
                "Aucune catégorie professionnelle trouvée — lancez d'abord seed_referentiels."))
            return
        niveau_max = max(c.niveau for c in categories)

        n = 0
        for emp in Employee.objects.filter(categorie__isnull=False):
            if emp.categorie.niveau >= niveau_max or emp.avancements.exists():
                continue
            nouvelle_categorie = next(
                (c for c in categories if c.niveau == emp.categorie.niveau + 1), None)
            if not nouvelle_categorie:
                continue
            Avancement.objects.create(
                employe=emp,
                ancienne_categorie=emp.categorie,
                nouvelle_categorie=nouvelle_categorie,
                date_effet=date(2026, 1, 1),
                reference=f"AV-2026-{emp.pk:03d}",
                motif="Avancement annuel pour ancienneté et performance.",
            )
            n += 1
        self.stdout.write(self.style.SUCCESS(f"{n} avancement(s) créé(s)."))
