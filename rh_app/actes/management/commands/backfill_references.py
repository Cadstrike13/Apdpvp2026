from django.core.management.base import BaseCommand

from actes.models import ActeAdministratif


class Command(BaseCommand):
    help = "Attribue une référence ACT-<annee>-NNN aux actes qui n'en ont pas."

    def handle(self, *args, **options):
        sans_ref = ActeAdministratif.all_objects.filter(reference="").order_by("date_acte", "id")
        n = 0
        for acte in sans_ref:
            acte.save()  # save() génère la référence automatiquement
            n += 1
            self.stdout.write(f"  + {acte.reference} -> {acte.objet}")
        self.stdout.write(self.style.SUCCESS(f"{n} reference(s) attribuee(s)."))
