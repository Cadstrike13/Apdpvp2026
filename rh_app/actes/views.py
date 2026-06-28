from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse

from xhtml2pdf import pisa

from .models import ActeAdministratif
from .forms import ActeAdministratifForm


def acte_list(request):
    q = request.GET.get("q", "")
    type_acte = request.GET.get("type", "")
    actes = ActeAdministratif.objects.select_related("employe").all()
    if q:
        actes = actes.filter(objet__icontains=q) | actes.filter(reference__icontains=q)
    if type_acte:
        actes = actes.filter(type_acte=type_acte)

    if request.htmx and (request.GET.get("q") is not None or request.GET.get("type") is not None):
        return render(request, "actes/partials/table.html", {"actes": actes})

    template = "actes/partials/content.html" if request.htmx else "actes/list.html"
    return render(request, template, {
        "actes": actes, "query": q, "type_actes": ActeAdministratif.TYPE_CHOICES, "type_selected": type_acte,
    })


def acte_create(request):
    form = ActeAdministratifForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("actes:list")
    template = "partials/form.html" if request.htmx else "crud_form.html"
    return render(request, template, {
        "form": form, "titre": "Nouvel acte administratif", "cancel_url": reverse("actes:list"),
    })


def acte_update(request, pk):
    acte = get_object_or_404(ActeAdministratif, pk=pk)
    form = ActeAdministratifForm(request.POST or None, request.FILES or None, instance=acte)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("actes:list")
    template = "partials/form.html" if request.htmx else "crud_form.html"
    return render(request, template, {
        "form": form, "titre": "Modifier l'acte", "cancel_url": reverse("actes:list"),
    })


def acte_delete(request, pk):
    acte = get_object_or_404(ActeAdministratif, pk=pk)
    if request.method in ("POST", "DELETE"):
        acte.delete()
        return HttpResponse("")
    return redirect("actes:list")


def acte_pdf(request, pk):
    """Génère le PDF imprimable de l'acte (à faire signer puis re-scanner)."""
    acte = get_object_or_404(ActeAdministratif.objects.select_related("employe", "redige_par"), pk=pk)
    html = render_to_string("actes/pdf.html", {"acte": acte})
    response = HttpResponse(content_type="application/pdf")
    nom_fichier = (acte.reference or f"acte-{acte.pk}").replace("/", "-")
    response["Content-Disposition"] = f'inline; filename="{nom_fichier}.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response
