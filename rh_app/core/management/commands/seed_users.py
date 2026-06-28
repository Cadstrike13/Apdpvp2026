from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from core.roles import Roles

User = get_user_model()

# (username, prenom, nom, role)
DEMO_USERS = [
    ("directeur",  "Jean",     "Obame",     Roles.DIRECTEUR),
    ("chef.rh",    "Sandrine", "Mba",       Roles.CHEF_SERVICE),
    ("agent.rh1",  "Carine",   "Nzue",      Roles.AGENT_RH),
    ("agent.rh2",  "Patrick",  "Ndong",     Roles.AGENT_RH),
    ("usager1",    "Eric",     "Koumba",    Roles.USAGER),
]

DEFAULT_PASSWORD = "apdpvp2026"


class Command(BaseCommand):
    help = "Crée des comptes utilisateurs de démonstration et leur affecte un rôle."

    def handle(self, *args, **options):
        # Superutilisateur d'administration
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={"first_name": "Admin", "last_name": "APDPVP", "email": "admin@apdpvp.ga",
                      "is_staff": True, "is_superuser": True},
        )
        if created:
            admin.set_password(DEFAULT_PASSWORD)
            admin.save()
        admin.groups.add(*Group.objects.filter(name__in=[Roles.ADMIN, Roles.SUPERUSER]))
        self.stdout.write(("  + cree : " if created else "  = existe : ") + "admin (superuser)")

        for username, prenom, nom, role in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"first_name": prenom, "last_name": nom,
                          "email": f"{username}@apdpvp.ga", "is_staff": True},
            )
            if created:
                user.set_password(DEFAULT_PASSWORD)
                user.save()
            group = Group.objects.filter(name=role).first()
            if group:
                user.groups.add(group)
            self.stdout.write(("  + cree : " if created else "  = existe : ") + f"{username} -> {role}")
        self.stdout.write(self.style.SUCCESS(f"Comptes de demo prets (mot de passe : {DEFAULT_PASSWORD})."))
