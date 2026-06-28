from django import forms

from .models import TrainingProgram


class TrainingProgramForm(forms.ModelForm):
    class Meta:
        model = TrainingProgram
        fields = [
            "titre", "prestataire", "type_formation", "date_debut", "date_fin",
            "duree_heures", "statut", "participants",
        ]
        widgets = {
            "date_debut": forms.DateInput(attrs={"type": "date"}),
            "date_fin": forms.DateInput(attrs={"type": "date"}),
            "participants": forms.SelectMultiple(),
        }
