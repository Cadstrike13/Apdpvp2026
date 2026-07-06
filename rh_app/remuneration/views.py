from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse

from xhtml2pdf import pisa

from core.permissions import role_required, REMU_ROLES
from employees.models import Employee
from .models import Salaire, Prime, AvanceSalaire, calcul_droits
from .forms import SalaireForm, PrimeForm, AvanceForm


@role_required(*REMU_ROLES)
def remuneration_home(request):
    agents = Employee.objects.filter(statut="actif")
    lignes = [{"employe": e, "droits": calcul_droits(e)} for e in agents]
    context = {
        "lignes": lignes,
        "primes": Prime.objects.select_related("employe").all()[:30],
        "avances": AvanceSalaire.objects.select_related("employe").all()[:30],
    }
    template = "remuneration/partials/content.html" if request.htmx else "remuneration/home.html"
    return render(request, template, context)


def _form(request, form, titre):
    template = "partials/form.html" if request.htmx else "crud_form.html"
    return render(request, template, {"form": form, "titre": titre, "cancel_url": reverse("remuneration:home")})


# ---------- Salaire ----------
@role_required(*REMU_ROLES)
def salaire_create(request):
    form = SalaireForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("remuneration:home")
    return _form(request, form, "Nouveau salaire de base")


# ---------- Prime ----------
@role_required(*REMU_ROLES)
def prime_create(request):
    form = PrimeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("remuneration:home")
    return _form(request, form, "Nouvelle prime")


@role_required(*REMU_ROLES)
def prime_update(request, pk):
    obj = get_object_or_404(Prime, pk=pk)
    form = PrimeForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("remuneration:home")
    return _form(request, form, "Modifier la prime")


@role_required(*REMU_ROLES)
def prime_delete(request, pk):
    obj = get_object_or_404(Prime, pk=pk)
    if request.method in ("POST", "DELETE"):
        obj.delete()
        return HttpResponse("")
    return redirect("remuneration:home")


# ---------- Avance ----------
@role_required(*REMU_ROLES)
def avance_create(request):
    form = AvanceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("remuneration:home")
    return _form(request, form, "Nouvelle avance sur salaire")


@role_required(*REMU_ROLES)
def avance_update(request, pk):
    obj = get_object_or_404(AvanceSalaire, pk=pk)
    form = AvanceForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("remuneration:home")
    return _form(request, form, "Modifier l'avance")


@role_required(*REMU_ROLES)
def avance_delete(request, pk):
    obj = get_object_or_404(AvanceSalaire, pk=pk)
    if request.method in ("POST", "DELETE"):
        obj.delete()
        return HttpResponse("")
    return redirect("remuneration:home")


# ---------- Bulletin de paie (PDF) ----------
@role_required(*REMU_ROLES)
def bulletin_pdf(request, pk):
    employe = get_object_or_404(Employee, pk=pk)
    droits = calcul_droits(employe)
    html = render_to_string("remuneration/bulletin.html", {"employe": employe, "droits": droits})
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="bulletin-{employe.pk}.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response
