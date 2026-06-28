from django.core.management.base import BaseCommand

from employees.models import (
    Department, CategorieProfessionnelle, StatutAgent, Poste, TypeContrat,
)

CATEGORIES = [
    ("CAT_A", "Cadre supérieur", 4),
    ("CAT_B", "Cadre", 3),
    ("CAT_C", "Agent de maîtrise", 2),
    ("CAT_D", "Agent d'exécution", 1),
]

STATUTS = [
    ("stage", "Stagiaire"),
    ("actif", "Actif"),
    ("conge", "En congé"),
    ("absent", "Absent"),
    ("licencie", "Licencié"),
]

TYPES_CONTRAT = [
    ("CDI", "CDI"),
    ("CDD", "CDD"),
    ("STAGE", "Stage"),
    ("MANDAT", "Mandat"),
]

# (intitulé, département)
POSTES = [
    ("Responsable RH", "Ressources Humaines"),
    ("Chargé de recrutement", "Ressources Humaines"),
    ("Développeur back-end", "Informatique"),
    ("Administrateur systèmes", "Informatique"),
    ("Comptable", "Finances"),
    ("Contrôleur de gestion", "Finances"),
    ("Gestionnaire logistique", "Logistique"),
    ("Magasinier", "Logistique"),
]


class Command(BaseCommand):
    help = "Crée les référentiels RH (catégories, statuts, postes, types de contrat)."

    def handle(self, *args, **options):
        for code, libelle, niveau in CATEGORIES:
            CategorieProfessionnelle.objects.get_or_create(
                code=code, defaults={"libelle": libelle, "niveau": niveau})
        for code, libelle in STATUTS:
            StatutAgent.objects.get_or_create(code=code, defaults={"libelle": libelle})
        for code, libelle in TYPES_CONTRAT:
            TypeContrat.objects.get_or_create(code=code, defaults={"libelle": libelle})
        for intitule, dept_nom in POSTES:
            dept, _ = Department.objects.get_or_create(nom=dept_nom)
            Poste.objects.get_or_create(intitule=intitule, defaults={"departement": dept})
        self.stdout.write(self.style.SUCCESS(
            f"Referentiels OK : {CategorieProfessionnelle.objects.count()} categories, "
            f"{StatutAgent.objects.count()} statuts, {TypeContrat.objects.count()} types de contrat, "
            f"{Poste.objects.count()} postes."
        ))
