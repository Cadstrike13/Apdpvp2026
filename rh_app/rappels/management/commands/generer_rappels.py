from datetime import date, timedelta

from django.core.management.base import BaseCommand

from employees.models import Employee, Contrat
from leaves.models import LeaveRequest
from rappels.models import Rappel


def niveau_pour(jours_restants):
    if jours_restants <= 7:
        return "urgent"
    if jours_restants <= 21:
        return "important"
    return "info"


class Command(BaseCommand):
    help = "Génère les rappels RH pour les échéances à venir (défaut : 30 jours)."

    def add_arguments(self, parser):
        parser.add_argument("--jours", type=int, default=30, help="Fenêtre d'anticipation en jours.")

    def handle(self, *args, **options):
        jours = options["jours"]
        today = date.today()
        horizon = today + timedelta(days=jours)
        crees = 0

        def creer(type_rappel, employe, objet, echeance, message=""):
            nonlocal crees
            _, created = Rappel.objects.get_or_create(
                type_rappel=type_rappel, employe=employe, date_echeance=echeance,
                defaults={"objet": objet[:200], "message": message,
                          "niveau": niveau_pour((echeance - today).days)},
            )
            if created:
                crees += 1

        # Anniversaires (naissance) + de service + avancement
        for emp in Employee.objects.all():
            j = emp.jours_avant_anniversaire
            if j is not None and 0 <= j <= jours:
                creer("anniversaire", emp, f"Anniversaire de {emp}", emp.prochain_anniversaire)
            js = emp.jours_avant_anniversaire_service
            if js is not None and 0 <= js <= jours:
                occ = emp.prochain_anniversaire_service
                annees = occ.year - emp.date_embauche.year
                creer("anniversaire_service", emp,
                      f"{annees} an(s) de service — {emp}", occ)
                # Avancement à examiner tous les 3 ans d'ancienneté
                if annees > 0 and annees % 3 == 0:
                    creer("avancement", emp,
                          f"Examiner l'avancement de {emp} ({annees} ans)", occ,
                          message="Échéance d'ancienneté : vérifier un éventuel changement de catégorie.")

        # Fins de contrat
        for ct in Contrat.objects.select_related("employe").filter(date_fin__range=(today, horizon)):
            creer("fin_contrat", ct.employe,
                  f"Fin de contrat {ct.type_contrat or ''} — {ct.employe}", ct.date_fin,
                  message=f"Référence : {ct.reference}")

        # Congés à venir
        for lv in LeaveRequest.objects.select_related("employe").filter(
                date_debut__range=(today, horizon), statut__in=["en_attente", "approuve"]):
            creer("conge", lv.employe,
                  f"Congé {lv.get_type_conge_display()} — {lv.employe}", lv.date_debut,
                  message=f"Du {lv.date_debut} au {lv.date_fin} ({lv.get_statut_display()})")

        self.stdout.write(self.style.SUCCESS(
            f"{crees} rappel(s) cree(s) (fenetre {jours}j). Total actifs : "
            f"{Rappel.objects.filter(traite=False).count()}."
        ))
