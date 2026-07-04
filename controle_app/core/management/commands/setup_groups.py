from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from core.permissions import GROUPE_ADMINISTRATEUR, GROUPE_AGENT, GROUPE_CHEF_MISSION


class Command(BaseCommand):
    help = "Crée les groupes et permissions de l'application APDPVP"

    def handle(self, *args, **options):
        administrateur, _ = Group.objects.get_or_create(name=GROUPE_ADMINISTRATEUR)
        chef, _ = Group.objects.get_or_create(name=GROUPE_CHEF_MISSION)
        agent, _ = Group.objects.get_or_create(name=GROUPE_AGENT)

        administrateur.permissions.set(Permission.objects.all())

        perms_chef = Permission.objects.filter(
            content_type__app_label__in=["missions", "personnes", "entites"],
        )
        chef.permissions.set(perms_chef)

        perms_agent = Permission.objects.filter(
            content_type__app_label__in=["missions", "personnes"],
            codename__in=[
                "view_missioncontrole", "change_reponsetraitement", "view_reponsetraitement",
                "add_personneinterrogee", "view_personneinterrogee",
            ],
        )
        agent.permissions.set(perms_agent)

        self.stdout.write(self.style.SUCCESS("Groupes et permissions créés."))
