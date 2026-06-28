from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.urls import reverse

from .models import Employee
from .forms import EmployeeForm


def employee_list(request):
    q = request.GET.get("q", "")
    employees = Employee.objects.select_related("departement").all()
    if q:
        employees = employees.filter(nom__icontains=q) | employees.filter(email__icontains=q)

    if request.htmx and request.GET.get("q") is not None:
        return render(request, "employees/partials/table.html", {"employees": employees, "query": q})

    template = "employees/partials/content.html" if request.htmx else "employees/list.html"
    return render(request, template, {"employees": employees, "query": q})


def employee_detail(request, pk):
    emp = get_object_or_404(Employee.objects.select_related("departement"), pk=pk)
    template = "employees/partials/detail.html" if request.htmx else "employees/detail.html"
    return render(request, template, {"employee": emp})


def employee_create(request):
    form = EmployeeForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("employees:list")
    template = "partials/form.html" if request.htmx else "crud_form.html"
    return render(request, template, {
        "form": form, "titre": "Nouvel employé", "cancel_url": reverse("employees:list"),
    })


def employee_update(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    form = EmployeeForm(request.POST or None, request.FILES or None, instance=emp)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("employees:list")
    template = "partials/form.html" if request.htmx else "crud_form.html"
    return render(request, template, {
        "form": form, "titre": f"Modifier {emp}", "cancel_url": reverse("employees:list"),
    })


def employee_delete(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    if request.method in ("POST", "DELETE"):
        emp.delete()
        return HttpResponse("")
    return render(request, "employees/partials/confirm_delete.html", {"employee": emp})
