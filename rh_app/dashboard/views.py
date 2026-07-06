from datetime import date

from django.shortcuts import render

from employees.models import Employee
from leaves.models import LeaveRequest
from recruitment.models import JobPosting
from training.models import TrainingProgram
from actes.models import ActeAdministratif
from rappels.models import Rappel

HORIZON_JOURS = 30  # fenetre des "prochains" evenements


def dashboard(request):
    today = date.today()
    emps = list(Employee.objects.all())

    anniversaires = sorted(
        (e for e in emps if e.jours_avant_anniversaire is not None and e.jours_avant_anniversaire <= HORIZON_JOURS),
        key=lambda e: e.jours_avant_anniversaire,
    )[:6]
    anniversaires_service = sorted(
        (e for e in emps if e.jours_avant_anniversaire_service is not None and e.jours_avant_anniversaire_service <= HORIZON_JOURS),
        key=lambda e: e.jours_avant_anniversaire_service,
    )[:6]

    context = {
        "total_employes": Employee.objects.filter(statut="actif").count(),
        "conges_en_attente": LeaveRequest.objects.filter(statut="en_attente").count(),
        "offres_ouvertes": JobPosting.objects.filter(statut="ouvert").count(),
        "total_actes": ActeAdministratif.objects.count(),
        "anniversaires": anniversaires,
        "anniversaires_service": anniversaires_service,
        "prochaines_formations": TrainingProgram.objects.filter(date_debut__gte=today).order_by("date_debut")[:5],
        "actes_recents": ActeAdministratif.objects.select_related("employe").all()[:5],
        "derniers_conges": LeaveRequest.objects.select_related("employe").order_by("-date_demande")[:5],
        "rappels": Rappel.objects.filter(traite=False).order_by("date_echeance")[:6],
    }
    template = "dashboard/partials/content.html" if request.htmx else "dashboard/index.html"
    return render(request, template, context)
