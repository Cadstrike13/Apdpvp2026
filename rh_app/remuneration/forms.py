from django import forms

from .models import Salaire, Prime, AvanceSalaire, AllocationConge


class SalaireForm(forms.ModelForm):
    class Meta:
        model = Salaire
        fields = ["employe", "montant_base", "date_effet", "motif"]
        widgets = {"date_effet": forms.DateInput(attrs={"type": "date"})}


class PrimeForm(forms.ModelForm):
    class Meta:
        model = Prime
        fields = ["employe", "libelle", "montant", "date", "imposable"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class AvanceForm(forms.ModelForm):
    class Meta:
        model = AvanceSalaire
        fields = ["employe", "montant", "date", "motif", "rembourse"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class AllocationForm(forms.ModelForm):
    class Meta:
        model = AllocationConge
        fields = ["employe", "montant", "date", "libelle"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}
