from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from core.roles import Roles


class Command(BaseCommand):
    help = "Crée les groupes/rôles APDPVP et leur affecte les permissions."

    def handle(self, *args, **options):
        groups = {}
        for code, label in Roles.CHOICES:
            group, created = Group.objects.get_or_create(name=code)
            groups[code] = group
            self.stdout.write(("  + cree : " if created else "  = existe : ") + f"{code} ({label})")

        all_rh = Permission.objects.filter(content_type__app_label__in=Roles.RH_APPS)

        def perms(apps=None, models=None, actions=None):
            qs = Permission.objects.filter(content_type__app_label__in=(apps or Roles.RH_APPS))
            if models:
                qs = qs.filter(content_type__model__in=models)
            if actions:
                import functools, operator
                from django.db.models import Q
                q = functools.reduce(operator.or_, [Q(codename__startswith=a) for a in actions])
                qs = qs.filter(q)
            return qs

        # admin & superuser : permissions étendues
        groups[Roles.ADMIN].permissions.set(all_rh)
        groups[Roles.SUPERUSER].permissions.set(Permission.objects.all())

        # directeur(trice) : contrôle total sur le RH
        groups[Roles.DIRECTEUR].permissions.set(perms())

        # agent RH : consulter tout + ajouter/modifier (sans suppression)
        agent = list(perms(actions=["view", "add", "change"]))
        groups[Roles.AGENT_RH].permissions.set(agent)

        # chef de service : voir tout le RH + gérer congés/formations/documents
        chef = list(perms(actions=["view"])) + list(
            perms(models=["leaverequest", "trainingprogram", "document"], actions=["add", "change"])
        )
        groups[Roles.CHEF_SERVICE].permissions.set(chef)

        # usager : consulter congés/documents + déposer une demande de congé
        usager = list(perms(models=["leaverequest", "document"], actions=["view"])) + list(
            perms(models=["leaverequest"], actions=["add"])
        )
        groups[Roles.USAGER].permissions.set(usager)

        self.stdout.write(self.style.SUCCESS("Roles initialises avec succes."))
