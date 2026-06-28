from django import forms

from .models import ActeAdministratif
from .choices import STATUTS_PIECE_REQUISE


class ActeAdministratifForm(forms.ModelForm):
    class Meta:
        model = ActeAdministratif
        fields = [
            "reference", "employe", "type_acte", "objet", "contenu",
            "date_acte", "date_debut", "date_fin", "statut", "fichier", "redige_par",
        ]
        widgets = {
            "date_acte": forms.DateInput(attrs={"type": "date"}),
            "date_debut": forms.DateInput(attrs={"type": "date"}),
            "date_fin": forms.DateInput(attrs={"type": "date"}),
            "contenu": forms.Textarea(attrs={"rows": 5}),
            "fichier": forms.ClearableFileInput(attrs={"accept": ".pdf,image/*"}),
        }

    def clean(self):
        cleaned = super().clean()
        statut = cleaned.get("statut")
        fichier = cleaned.get("fichier")
        # Fichier déjà présent sur l'instance (cas modification sans ré-upload)
        deja_present = bool(getattr(self.instance, "fichier", None))
        if statut in STATUTS_PIECE_REQUISE and not (fichier or deja_present):
            self.add_error(
                "fichier",
                "Un document signé scanné (PDF ou image) est obligatoire "
                "pour un acte émis, signé ou archivé.",
            )
        return cleaned
