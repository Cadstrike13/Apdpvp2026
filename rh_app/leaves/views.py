from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.urls import reverse

from .models import LeaveRequest
from .forms import LeaveRequestForm


def leave_list(request):
    leaves = LeaveRequest.objects.select_related("employe").all()
    template = "leaves/partials/content.html" if request.htmx else "leaves/list.html"
    return render(request, template, {"leaves": leaves})


def leave_create(request):
    form = LeaveRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("leaves:list")
    template = "partials/form.html" if request.htmx else "crud_form.html"
    return render(request, template, {
        "form": form, "titre": "Nouvelle demande de congé", "cancel_url": reverse("leaves:list"),
    })


def leave_update(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    form = LeaveRequestForm(request.POST or None, instance=leave)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("leaves:list")
    template = "partials/form.html" if request.htmx else "crud_form.html"
    return render(request, template, {
        "form": form, "titre": "Modifier la demande", "cancel_url": reverse("leaves:list"),
    })


def leave_delete(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    if request.method in ("POST", "DELETE"):
        leave.delete()
        return HttpResponse("")
    return redirect("leaves:list")


def approve_leave(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    if request.method == "POST":
        leave.statut = "approuve"
        leave.save()
    return render(request, "leaves/partials/status_badge.html", {"leave": leave})


def reject_leave(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    if request.method == "POST":
        leave.statut = "refuse"
        leave.save()
    return render(request, "leaves/partials/status_badge.html", {"leave": leave})
