from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from agents.models import AgentControleur
from core.permissions import GROUPE_AGENT, GROUPE_CHEF_MISSION
from entites.models import EntiteControlee

# Identifiants fixes réservés au développement local — jamais utilisés si
# DEBUG=False (voir la garde ci-dessous). Documentés dans CLAUDE.md.
IDENTIFIANTS_DEV = {
    "admin": {"password": "admin1234", "superuser": True},
    "chef_test": {"password": "test1234", "role": GROUPE_CHEF_MISSION, "agent_external_id": "AG-001"},
    "agent_test": {"password": "test1234", "role": GROUPE_AGENT, "agent_external_id": "AG-002"},
}


class Command(BaseCommand):
    help = "Crée des comptes et données de démonstration pour les tests manuels en local (DEBUG uniquement)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_dev refuse de tourner avec DEBUG=False (données de test local uniquement).")

        call_command("setup_groups")
        AgentControleur.objects.sync_from_source()

        admin, _ = User.objects.get_or_create(username="admin")
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password(IDENTIFIANTS_DEV["admin"]["password"])
        admin.save()

        for username in ("chef_test", "agent_test"):
            config = IDENTIFIANTS_DEV[username]
            user, _ = User.objects.get_or_create(username=username)
            user.set_password(config["password"])
            user.save()
            user.groups.set(Group.objects.filter(name=config["role"]))
            AgentControleur.objects.filter(external_id=config["agent_external_id"]).update(user=user)

        EntiteControlee.objects.get_or_create(nom="ACME SA (démo)")

        self.stdout.write(self.style.SUCCESS("Comptes de démo créés :"))
        for username, config in IDENTIFIANTS_DEV.items():
            self.stdout.write(f"  {username} / {config['password']}")
