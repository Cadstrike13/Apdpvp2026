from django.db.models import Case, When, IntegerField
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.urls import reverse

from .models import JobPosting, Candidate
from .forms import JobPostingForm, CandidateForm


def _candidats_tries(type_demande=""):
    """Candidats triés par priorité (urgente d'abord) puis date."""
    qs = Candidate.objects.select_related("offre")
    if type_demande in ("emploi", "stage"):
        qs = qs.filter(type_demande=type_demande)
    return qs.annotate(
        prio_ordre=Case(
            When(priorite="urgente", then=0),
            When(priorite="importante", then=1),
            default=2,
            output_field=IntegerField(),
        )
    ).order_by("prio_ordre", "-date_candidature")


def recruitment_list(request):
    type_demande = request.GET.get("type", "")
    context = {
        "offres": JobPosting.objects.select_related("departement").all(),
        "candidats": _candidats_tries(type_demande),
        "type_selected": type_demande,
        "classement": [("", "Tous"), ("emploi", "Emploi"), ("stage", "Stage")],
    }
    if request.htmx and request.GET.get("type") is not None:
        return render(request, "recruitment/partials/candidats.html", context)
    template = "recruitment/partials/content.html" if request.htmx else "recruitment/list.html"
    return render(request, template, context)


def _render_form(request, form, titre):
    template = "partials/form.html" if request.htmx else "crud_form.html"
    return render(request, template, {
        "form": form, "titre": titre, "cancel_url": reverse("recruitment:list"),
    })


# --- Offres d'emploi ---
def job_create(request):
    form = JobPostingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("recruitment:list")
    return _render_form(request, form, "Nouvelle offre d'emploi")


def job_update(request, pk):
    job = get_object_or_404(JobPosting, pk=pk)
    form = JobPostingForm(request.POST or None, instance=job)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("recruitment:list")
    return _render_form(request, form, "Modifier l'offre")


def job_delete(request, pk):
    job = get_object_or_404(JobPosting, pk=pk)
    if request.method in ("POST", "DELETE"):
        job.delete()
        return HttpResponse("")
    return redirect("recruitment:list")


# --- Candidats ---
def candidate_create(request):
    form = CandidateForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("recruitment:list")
    return _render_form(request, form, "Nouveau candidat")


def candidate_update(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    form = CandidateForm(request.POST or None, request.FILES or None, instance=candidate)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("recruitment:list")
    return _render_form(request, form, "Modifier le candidat")


def candidate_delete(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    if request.method in ("POST", "DELETE"):
        candidate.delete()
        return HttpResponse("")
    return redirect("recruitment:list")
