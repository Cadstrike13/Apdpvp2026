from django.core.management.base import BaseCommand

from agents.models import AgentControleur


class Command(BaseCommand):
    help = "Synchronise le pool d'agents contrôleurs depuis la source configurée (mock ou API)"

    def handle(self, *args, **options):
        AgentControleur.objects.sync_from_source()
        self.stdout.write(self.style.SUCCESS("Agents synchronisés."))
