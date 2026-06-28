from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.urls import reverse

from .models import Document
from .forms import DocumentForm


def document_list(request):
    documents = Document.objects.select_related("uploade_par").all()
    template = "documents/partials/content.html" if request.htmx else "documents/list.html"
    return render(request, template, {"documents": documents})


def document_create(request):
    form = DocumentForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("documents:list")
    template = "partials/form.html" if request.htmx else "crud_form.html"
    return render(request, template, {
        "form": form, "titre": "Nouveau document", "cancel_url": reverse("documents:list"),
    })


def document_update(request, pk):
    document = get_object_or_404(Document, pk=pk)
    form = DocumentForm(request.POST or None, request.FILES or None, instance=document)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("documents:list")
    template = "partials/form.html" if request.htmx else "crud_form.html"
    return render(request, template, {
        "form": form, "titre": "Modifier le document", "cancel_url": reverse("documents:list"),
    })


def document_delete(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if request.method in ("POST", "DELETE"):
        document.delete()
        return HttpResponse("")
    return redirect("documents:list")
