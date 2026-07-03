"""Crée des postes de démo et les applications du portail APDPVP (cf. CLAUDE.md)."""
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from accounts.models import Application, Poste

POSTES_DEMO = [
    ("drh", "Directeur des Ressources Humaines"),
    ("chef_service_rh", "Chef de Service RH"),
    ("agent_administratif", "Agent Administratif"),
    ("technicien", "Technicien"),
    ("gestionnaire", "Gestionnaire"),
    ("inspecteur", "Inspecteur"),
]

APPS = [
    {
        "nom": "Gestion RH",
        "slug": "rh",
        "url": "http://rh.apdpvp.local",
        "description": "Employés, congés, recrutement, formations et actes administratifs.",
        "icone": "users",
        "couleur": "emerald",
        "ordre": 1,
        "roles": ["admin", "directeur", "chef_service", "agent_rh"],
    },
    {
        "nom": "Dépannage & Maintenance",
        "slug": "depanage",
        "url": "http://depanage.apdpvp.local",
        "description": "Suivi des interventions techniques et demandes de dépannage.",
        "icone": "wrench",
        "couleur": "orange",
        "ordre": 2,
        "roles": ["admin", "directeur", "chef_service"],
    },
    {
        "nom": "Questure",
        "slug": "questure",
        "url": "http://questure.apdpvp.local",
        "description": "Gestion financière et comptable.",
        "icone": "landmark",
        "couleur": "blue",
        "ordre": 3,
        "roles": ["admin", "directeur"],
    },
    {
        "nom": "Missions & Contrôle",
        "slug": "missions",
        "url": "http://missions.apdpvp.local",
        "description": "Planification et suivi des missions de contrôle.",
        "icone": "clipboard-check",
        "couleur": "violet",
        "ordre": 4,
        "roles": ["admin", "directeur", "chef_service", "agent_rh"],
    },
    {
        "nom": "Administration des accès",
        "slug": "auth",
        "url": "http://auth.apdpvp.local",
        "description": "Gestion des utilisateurs, rôles, postes et applications du portail.",
        "icone": "shield",
        "couleur": "slate",
        "ordre": 5,
        "roles": ["admin", "superuser"],
    },
]


class Command(BaseCommand):
    help = "Crée les postes de démo et les applications du portail APDPVP"

    def handle(self, *args, **options):
        for code, libelle in POSTES_DEMO:
            poste, created = Poste.objects.get_or_create(code=code, defaults={"libelle": libelle})
            statut = "créé" if created else "déjà existant"
            self.stdout.write(f"  Poste « {poste.libelle} » : {statut}")

        for app_data in APPS:
            data = dict(app_data)
            roles = data.pop("roles")
            app, created = Application.objects.update_or_create(
                slug=data["slug"],
                defaults=data,
            )
            app.roles_autorises.set(Group.objects.filter(name__in=roles))
            statut = "créée" if created else "mise à jour"
            self.stdout.write(f"  Application « {app.nom} » : {statut}")

        self.stdout.write(self.style.SUCCESS("Postes et applications initialisés."))
