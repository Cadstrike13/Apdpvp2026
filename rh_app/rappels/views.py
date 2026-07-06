from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect

from .models import Rappel


def rappel_list(request):
    afficher_traites = request.GET.get("traites") == "1"
    rappels = Rappel.objects.select_related("employe")
    if not afficher_traites:
        rappels = rappels.filter(traite=False)
    context = {"rappels": rappels, "afficher_traites": afficher_traites}
    if request.htmx and request.GET.get("traites") is not None:
        return render(request, "rappels/partials/table.html", context)
    template = "rappels/partials/content.html" if request.htmx else "rappels/list.html"
    return render(request, template, context)


def rappel_traiter(request, pk):
    rappel = get_object_or_404(Rappel, pk=pk)
    if request.method == "POST":
        rappel.traite = True
        rappel.save(update_fields=["traite"])
        return HttpResponse("")  # retire la ligne (liste des actifs)
    return redirect("rappels:list")
