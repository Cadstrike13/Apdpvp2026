from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.urls import reverse

from .models import JobPosting, Candidate
from .forms import JobPostingForm, CandidateForm


def recruitment_list(request):
    context = {
        "offres": JobPosting.objects.select_related("departement").all(),
        "candidats": Candidate.objects.select_related("offre").all(),
    }
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
