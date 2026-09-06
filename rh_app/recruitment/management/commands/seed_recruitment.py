from datetime import date, timedelta

from django.core.management.base import BaseCommand

from employees.models import Department
from recruitment.models import Candidate, JobPosting

# (titre, département, lieu, offset date limite (jours), statut, description)
OFFRES = [
    ("Chargé de recrutement junior", "Ressources Humaines", "Libreville", 30, "ouvert",
     "Appui au processus de recrutement et gestion des candidatures."),
    ("Développeur back-end", "Informatique", "Libreville", 15, "ouvert",
     "Développement et maintenance des applications internes."),
    ("Comptable senior", "Finances", "Libreville", -10, "pourvu",
     "Suivi comptable et reporting financier."),
]

# (nom, email, téléphone, offre index, type demande, priorité, statut, note)
CANDIDATS = [
    ("Alice Ndong", "alice.ndong@example.ga", "+241 06 11 22 33", 0, "emploi", "normale", "examen", 3),
    ("Brice Ondo", "brice.ondo@example.ga", "+241 06 22 33 44", 0, "emploi", "importante", "entretien", 4),
    ("Christelle Mba", "christelle.mba@example.ga", "+241 06 33 44 55", 1, "emploi", "urgente", "entretien", 4),
    ("David Koumba", "david.koumba@example.ga", "+241 06 44 55 66", None, "stage", "normale", "examen", 0),
    ("Emma Obame", "emma.obame@example.ga", "+241 06 55 66 77", 2, "emploi", "normale", "offre", 5),
]


class Command(BaseCommand):
    help = "Crée des offres d'emploi et candidatures de démonstration."

    def handle(self, *args, **options):
        offres = []
        for titre, dept_nom, lieu, offset_limite, statut, description in OFFRES:
            dept, _ = Department.objects.get_or_create(nom=dept_nom)
            offre, _ = JobPosting.objects.get_or_create(
                titre=titre,
                defaults={
                    "departement": dept,
                    "lieu": lieu,
                    "date_limite": date.today() + timedelta(days=offset_limite),
                    "statut": statut,
                    "description": description,
                },
            )
            offres.append(offre)

        n = 0
        for nom, email, telephone, offre_idx, type_demande, priorite, statut, note in CANDIDATS:
            _, created = Candidate.objects.get_or_create(
                email=email,
                defaults={
                    "offre": offres[offre_idx] if offre_idx is not None else None,
                    "type_demande": type_demande,
                    "priorite": priorite,
                    "nom": nom,
                    "telephone": telephone,
                    "statut": statut,
                    "note": note,
                },
            )
            if created:
                n += 1
        self.stdout.write(self.style.SUCCESS(
            f"{len(offres)} offre(s) d'emploi, {n} candidat(s) créé(s)."))
