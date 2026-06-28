from django import forms

from .models import Employee


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            # Identité
            "nom", "prenom", "email", "date_naissance",
            "statut_matrimonial", "nombre_enfants",
            # Contacts
            "telephone1", "telephone2", "telephone_urgence",
            # Compte
            "user",
            # Dossier
            "cv", "lettre_motivation",
            # Matricules
            "matricule_cnss", "matricule_cnamgs", "matricule_apdpvp",
            # Affectation / situation
            "departement", "categorie", "poste", "statut_agent",
            "date_embauche", "salaire", "statut", "photo",
        ]
        widgets = {
            "date_naissance": forms.DateInput(attrs={"type": "date"}),
            "date_embauche": forms.DateInput(attrs={"type": "date"}),
        }
