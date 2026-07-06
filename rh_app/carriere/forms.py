from django import forms

from employees.models import Evaluation
from .models import Avancement


class EvaluationForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = ["employe", "date_evaluation", "note", "appreciation", "evaluateur"]
        widgets = {
            "date_evaluation": forms.DateInput(attrs={"type": "date"}),
            "appreciation": forms.Textarea(attrs={"rows": 4}),
        }


class AvancementForm(forms.ModelForm):
    class Meta:
        model = Avancement
        fields = ["employe", "ancienne_categorie", "nouvelle_categorie",
                  "date_effet", "reference", "motif", "fichier"]
        widgets = {
            "date_effet": forms.DateInput(attrs={"type": "date"}),
            "motif": forms.Textarea(attrs={"rows": 3}),
        }
