"""Crée les groupes de rôles APDPVP — identiques à rh_app/core/roles.py."""
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

ROLES = ["admin", "superuser", "directeur", "chef_service", "agent_rh", "usager"]


class Command(BaseCommand):
    help = "Crée les groupes de rôles APDPVP (identiques sur tous les services)"

    def handle(self, *args, **options):
        for role in ROLES:
            group, created = Group.objects.get_or_create(name=role)
            statut = "créé" if created else "déjà existant"
            self.stdout.write(f"  Rôle « {role} » : {statut}")
        self.stdout.write(self.style.SUCCESS("Rôles initialisés."))
