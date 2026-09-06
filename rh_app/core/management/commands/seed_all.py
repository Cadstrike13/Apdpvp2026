from django.core.management import call_command
from django.core.management.base import BaseCommand

# Ordre important : chaque étape peut dépendre des données créées par la précédente
# (ex. seed_agents_details a besoin des référentiels, seed_avancements a besoin
# des catégories professionnelles et des agents).
SEED_COMMANDS = [
    "init_roles",
    "seed_users",
    "seed_referentiels",
    "seed_agents_details",
    "seed_remuneration",
    "seed_leaves",
    "seed_training",
    "seed_recruitment",
    "seed_documents",
    "seed_avancements",
    "seed_actes",
]


class Command(BaseCommand):
    help = "Exécute dans l'ordre toutes les commandes seed de rh_app (données de démonstration)."

    def handle(self, *args, **options):
        for name in SEED_COMMANDS:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n== {name} =="))
            call_command(name)
        self.stdout.write(self.style.SUCCESS("\nSeed complet termine."))
