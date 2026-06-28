from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.urls import reverse

from .models import TrainingProgram
from .forms import TrainingProgramForm


def training_list(request):
    formations = TrainingProgram.objects.prefetch_related("participants").all()
    template = "training/partials/content.html" if request.htmx else "training/list.html"
    return render(request, template, {"formations": formations})


def training_create(request):
    form = TrainingProgramForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("training:list")
    template = "partials/form.html" if request.htmx else "crud_form.html"
    return render(request, template, {
        "form": form, "titre": "Nouvelle formation", "cancel_url": reverse("training:list"),
    })


def training_update(request, pk):
    formation = get_object_or_404(TrainingProgram, pk=pk)
    form = TrainingProgramForm(request.POST or None, instance=formation)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("training:list")
    template = "partials/form.html" if request.htmx else "crud_form.html"
    return render(request, template, {
        "form": form, "titre": "Modifier la formation", "cancel_url": reverse("training:list"),
    })


def training_delete(request, pk):
    formation = get_object_or_404(TrainingProgram, pk=pk)
    if request.method in ("POST", "DELETE"):
        formation.delete()
        return HttpResponse("")
    return redirect("training:list")
