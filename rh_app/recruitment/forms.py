from django import forms

from .models import JobPosting, Candidate


class JobPostingForm(forms.ModelForm):
    class Meta:
        model = JobPosting
        fields = ["titre", "departement", "lieu", "date_limite", "statut", "description"]
        widgets = {
            "date_limite": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ["type_demande", "priorite", "offre", "nom", "email", "telephone",
                  "statut", "note", "cv", "lettre_motivation"]
