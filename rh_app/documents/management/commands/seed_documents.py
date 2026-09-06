from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from documents.models import Document
from employees.models import Employee

# (nom, catégorie)
DOCUMENTS = [
    ("Règlement intérieur", "politique"),
    ("Convention collective APDPVP", "politique"),
    ("Modèle de contrat de travail CDI", "contrat"),
    ("Politique de formation 2026", "formation"),
    ("Grille d'évaluation annuelle", "evaluation"),
]


class Command(BaseCommand):
    help = "Crée des documents RH de démonstration (fichiers texte factices)."

    def handle(self, *args, **options):
        auteur = Employee.objects.first()
        n = 0
        for nom, categorie in DOCUMENTS:
            doc, created = Document.objects.get_or_create(
                nom=nom,
                defaults={"categorie": categorie, "uploade_par": auteur},
            )
            if created:
                doc.fichier.save(
                    f"{nom.lower().replace(' ', '_')}.txt",
                    ContentFile(f"Document de démonstration : {nom}\n".encode("utf-8")),
                    save=True,
                )
                n += 1
        self.stdout.write(self.style.SUCCESS(f"{n} document(s) créé(s)."))
