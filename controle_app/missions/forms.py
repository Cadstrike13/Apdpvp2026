from django import forms
from django.forms import modelformset_factory

from core.forms import TailwindForm, TailwindModelForm
from entites.models import EntiteControlee
from personnes.models import Personne

from .models import (
    MembreGroupeControle,
    MissionControle,
    ReponsePage1,
    ReponsePage2,
    ReponsePage3,
    ReponsePage4,
    ReponsePage5,
    ReponseTraitement,
)


class MissionControleForm(TailwindForm):
    """Sélectionner une entité déjà connue OU en déclarer une nouvelle."""

    entite_controlee = forms.ModelChoiceField(
        queryset=EntiteControlee.objects.all(), required=False, label="Entité contrôlée",
        help_text="Laisser vide pour déclarer une nouvelle entité ci-dessous.",
    )
    nom_nouvelle_entite = forms.CharField(required=False, label="Nom de la nouvelle entité")
    date_mission = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), label="Date de la mission",
    )
    commentaires_observations = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3}), label="Commentaires / observations",
    )

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("entite_controlee") and not cleaned_data.get("nom_nouvelle_entite"):
            raise forms.ValidationError(
                "Sélectionnez une entité déjà contrôlée ou renseignez le nom d'une nouvelle entité."
            )
        return cleaned_data


class MembreGroupeControleForm(TailwindModelForm):
    class Meta:
        model = MembreGroupeControle
        fields = ["agent", "role"]


class PersonneInterrogeeForm(TailwindForm):
    """Sélectionner une personne existante OU en créer une nouvelle, plus les
    infos propres à l'interrogatoire (poste/service au moment de la mission —
    pré-remplis depuis la Fonction active si laissés vides, voir missions/views.py)."""

    personne = forms.ModelChoiceField(
        queryset=Personne.objects.all(), required=False, label="Personne existante",
        help_text="Laisser vide pour créer une nouvelle personne ci-dessous.",
    )
    nom = forms.CharField(required=False, label="Nom (nouvelle personne)")
    prenom = forms.CharField(required=False, label="Prénom (nouvelle personne)")
    email = forms.EmailField(required=False, label="Email")
    telephone = forms.CharField(required=False, label="Téléphone")
    poste_snapshot = forms.CharField(required=False, label="Poste (au moment de la mission)")
    service_snapshot = forms.CharField(required=False, label="Service (au moment de la mission)")

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("personne") and not (cleaned_data.get("nom") and cleaned_data.get("prenom")):
            raise forms.ValidationError(
                "Sélectionnez une personne existante ou renseignez au moins son nom et son prénom."
            )
        return cleaned_data


class ObservationsForm(TailwindModelForm):
    class Meta:
        model = MissionControle
        fields = ["commentaires_observations"]
        widgets = {"commentaires_observations": forms.Textarea(attrs={"rows": 4})}


class ScanSigneForm(TailwindModelForm):
    class Meta:
        model = MissionControle
        fields = ["scan_signe"]


class RapportSigneForm(TailwindModelForm):
    class Meta:
        model = MissionControle
        fields = ["rapport_signe"]


class InfosPVForm(TailwindModelForm):
    """Informations nécessaires à la génération du procès-verbal, absentes
    des autres formulaires (voir missions/generate_pv.py)."""

    class Meta:
        model = MissionControle
        fields = [
            "mode_pv", "nom_representant_entite", "heure_controle",
            "deliberation_numero", "deliberation_organe",
            "lieu_signature", "date_signature", "heure_signature",
        ]
        widgets = {"date_signature": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}


class EvaluationForm(TailwindModelForm):
    class Meta:
        model = ReponseTraitement
        fields = ["evaluation", "observations_controleur", "observations_entite"]
        widgets = {
            "evaluation": forms.RadioSelect,
            "observations_controleur": forms.Textarea(attrs={"rows": 3}),
            "observations_entite": forms.Textarea(attrs={"rows": 3}),
        }


EvaluationFormSet = modelformset_factory(ReponseTraitement, form=EvaluationForm, extra=0)


class ReponsePage1Form(TailwindModelForm):
    class Meta:
        model = ReponsePage1
        exclude = ["reponse"]


class ReponsePage2Form(TailwindModelForm):
    class Meta:
        model = ReponsePage2
        exclude = ["reponse"]


class ReponsePage3Form(TailwindModelForm):
    class Meta:
        model = ReponsePage3
        exclude = ["reponse"]


class ReponsePage4Form(TailwindModelForm):
    class Meta:
        model = ReponsePage4
        exclude = ["reponse"]


class ReponsePage5Form(TailwindModelForm):
    class Meta:
        model = ReponsePage5
        exclude = ["reponse"]


Page1FormSet = modelformset_factory(ReponsePage1, form=ReponsePage1Form, extra=0)
Page2FormSet = modelformset_factory(ReponsePage2, form=ReponsePage2Form, extra=0)
Page3FormSet = modelformset_factory(ReponsePage3, form=ReponsePage3Form, extra=0)
Page4FormSet = modelformset_factory(ReponsePage4, form=ReponsePage4Form, extra=0)
Page5FormSet = modelformset_factory(ReponsePage5, form=ReponsePage5Form, extra=0)
