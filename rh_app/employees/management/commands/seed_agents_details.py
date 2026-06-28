from datetime import date

from django.core.management.base import BaseCommand

from employees.models import (
    Employee, CategorieProfessionnelle, StatutAgent, Poste, TypeContrat,
    Contrat, Affectation, Diplome, Evaluation,
)

# Mapping poste -> catégorie (code) selon la spec
CATEGORIE_PAR_POSTE = {
    "Responsable RH": "CAT_A",
    "Administrateur systèmes": "CAT_B",
    "Contrôleur de gestion": "CAT_B",
    "Développeur back-end": "CAT_B",
    "Comptable": "CAT_C",
    "Chargé de recrutement": "CAT_C",
    "Gestionnaire logistique": "CAT_C",
    "Magasinier": "CAT_D",
}


class Command(BaseCommand):
    help = "Enrichit les agents de démonstration (matricules, contacts, contrats, affectations, diplômes, évaluations)."

    def handle(self, *args, **options):
        statut_actif = StatutAgent.objects.filter(code="actif").first()
        statut_licencie = StatutAgent.objects.filter(code="licencie").first()
        cdi = TypeContrat.objects.filter(code="CDI").first()
        n = 0
        for emp in Employee.objects.all():
            cat = CategorieProfessionnelle.objects.filter(code=CATEGORIE_PAR_POSTE.get(emp.poste, "CAT_D")).first()
            emp.categorie = cat
            emp.statut_agent = statut_actif if emp.statut == "actif" else statut_licencie
            emp.matricule_cnss = emp.matricule_cnss or f"CNSS{1000 + emp.pk}"
            emp.matricule_cnamgs = emp.matricule_cnamgs or f"CNAMGS{2000 + emp.pk}"
            emp.matricule_apdpvp = emp.matricule_apdpvp or f"AP-{2018 + emp.pk}-{emp.pk:03d}"
            if not emp.telephone1:
                emp.telephone1 = f"+241 06 {emp.pk:02d} {emp.pk:02d} {emp.pk:02d}"
            emp.telephone_urgence = emp.telephone_urgence or f"+241 07 {emp.pk:02d} 00 00"
            emp.save()

            # Affectation principale (poste correspondant au libellé, créé si absent)
            if emp.poste and not emp.affectations.exists():
                poste, _ = Poste.objects.get_or_create(
                    intitule=emp.poste, defaults={"departement": emp.departement})
                Affectation.objects.create(employe=emp, poste=poste, date_debut=emp.date_embauche, principal=True)

            # Contrat
            if cdi and not emp.contrats.exists():
                Contrat.objects.create(
                    employe=emp, type_contrat=cdi,
                    reference=f"CT-{emp.date_embauche.year}-{emp.pk:03d}",
                    date_debut=emp.date_embauche,
                )

            # Diplôme
            if not emp.diplomes.exists():
                Diplome.objects.create(employe=emp, intitule="Licence", etablissement="Université Omar Bongo", annee=2015)

            # Évaluation
            if not emp.evaluations.exists():
                Evaluation.objects.create(
                    employe=emp, date_evaluation=date(2025, 12, 15),
                    note=14 + (emp.pk % 5), appreciation="Évaluation annuelle satisfaisante.",
                )
            n += 1
        self.stdout.write(self.style.SUCCESS(f"{n} agent(s) enrichi(s)."))
