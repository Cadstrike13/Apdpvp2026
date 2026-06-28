from django import forms

from .models import Document


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["nom", "categorie", "fichier", "uploade_par", "acces_employes"]
        widgets = {
            "acces_employes": forms.SelectMultiple(),
        }
