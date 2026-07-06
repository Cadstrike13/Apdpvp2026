from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse

from xhtml2pdf import pisa

from employees.models import Evaluation, Poste
from .models import Avancement
from .forms import EvaluationForm, AvancementForm


def carriere_home(request):
    context = {
        "evaluations": Evaluation.objects.select_related("employe", "evaluateur").all()[:50],
        "avancements": Avancement.objects.select_related("employe", "nouvelle_categorie").all()[:50],
        "postes": Poste.objects.select_related("departement").all(),
    }
    template = "carriere/partials/content.html" if request.htmx else "carriere/home.html"
    return render(request, template, context)


def _form(request, form, titre):
    template = "partials/form.html" if request.htmx else "crud_form.html"
    return render(request, template, {"form": form, "titre": titre, "cancel_url": reverse("carriere:home")})


# ---------- Évaluations ----------
def evaluation_create(request):
    form = EvaluationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("carriere:home")
    return _form(request, form, "Nouvelle évaluation")


def evaluation_update(request, pk):
    obj = get_object_or_404(Evaluation, pk=pk)
    form = EvaluationForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("carriere:home")
    return _form(request, form, "Modifier l'évaluation")


def evaluation_delete(request, pk):
    obj = get_object_or_404(Evaluation, pk=pk)
    if request.method in ("POST", "DELETE"):
        obj.delete()
        return HttpResponse("")
    return redirect("carriere:home")


# ---------- Avancements ----------
def avancement_create(request):
    form = AvancementForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        avancement = form.save()
        avancement.appliquer()  # met à jour la catégorie de l'agent
        return redirect("carriere:home")
    return _form(request, form, "Nouvel avancement")


def avancement_update(request, pk):
    obj = get_object_or_404(Avancement, pk=pk)
    form = AvancementForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        avancement = form.save()
        avancement.appliquer()
        return redirect("carriere:home")
    return _form(request, form, "Modifier l'avancement")


def avancement_delete(request, pk):
    obj = get_object_or_404(Avancement, pk=pk)
    if request.method in ("POST", "DELETE"):
        obj.delete()
        return HttpResponse("")
    return redirect("carriere:home")


# ---------- Fiche de poste (PDF) ----------
def fiche_poste_pdf(request, pk):
    poste = get_object_or_404(Poste.objects.select_related("departement"), pk=pk)
    occupants = poste.affectations.select_related("employe").filter(date_fin__isnull=True)
    html = render_to_string("carriere/fiche_poste.html", {"poste": poste, "occupants": occupants})
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="fiche-poste-{poste.pk}.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response
