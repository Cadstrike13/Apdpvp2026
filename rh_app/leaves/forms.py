from django import forms

from .models import LeaveRequest


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ["employe", "type_conge", "date_debut", "date_fin", "motif", "statut"]
        widgets = {
            "date_debut": forms.DateInput(attrs={"type": "date"}),
            "date_fin": forms.DateInput(attrs={"type": "date"}),
            "motif": forms.Textarea(attrs={"rows": 3}),
        }
