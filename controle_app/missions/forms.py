from django import forms
from django.core.validators import FileExtensionValidator
from django.forms import modelformset_factory

from core.forms import TailwindForm, TailwindModelForm
from core.validators import ValidateurTailleFichier
from entites.models import EntiteControlee, SecteurActivite
from personnes.models import Personne

from .models import (
    EXTENSIONS_SCAN_AUTORISEES,
    TAILLE_MAX_FICHIER_MO,
    ControleEntite,
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
    """Formulaire de l'admin : crée la mission et l'entité (ou les entités)
    contrôlée(s) — une ligne ControleEntite est créée par entité, chacune
    avec son propre circuit indépendant. L'affectation du groupe de
    contrôle de chaque entité se fait ensuite depuis sa fiche (voir
    controle_entite_detail / membre_ajouter)."""

    entites_controlees = forms.ModelMultipleChoiceField(
        queryset=EntiteControlee.objects.all(), required=False, label="Entités contrôlées",
        widget=forms.CheckboxSelectMultiple,
        help_text="Sélectionnez une ou plusieurs entités déjà connues. Ajoutez-en une nouvelle ci-dessous si besoin.",
    )
    nom_nouvelle_entite = forms.CharField(required=False, label="Nom de la nouvelle entité")
    secteur_activite_nouvelle_entite = forms.ChoiceField(
        choices=[("", "—")] + SecteurActivite.choices, required=False,
        label="Secteur d'activité de la nouvelle entité",
    )
    date_mission = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), label="Date de la mission",
    )
    ordre_mission = forms.FileField(
        required=False, label="Ordre de mission",
        validators=[
            FileExtensionValidator(EXTENSIONS_SCAN_AUTORISEES),
            ValidateurTailleFichier(TAILLE_MAX_FICHIER_MO),
        ],
    )

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("entites_controlees") and not cleaned_data.get("nom_nouvelle_entite"):
            raise forms.ValidationError(
                "Sélectionnez au moins une entité déjà contrôlée ou renseignez le nom d'une nouvelle entité."
            )
        return cleaned_data


class AjouterEntiteForm(TailwindForm):
    """Ajoute une entité (et donc un nouveau ControleEntite, avec son propre
    circuit) à une mission existante — depuis la fiche mission (admin)."""

    entite_controlee = forms.ModelChoiceField(
        queryset=EntiteControlee.objects.all(), required=False, label="Entité déjà connue",
        help_text="Laisser vide pour déclarer une nouvelle entité ci-dessous.",
    )
    nom_nouvelle_entite = forms.CharField(required=False, label="Nom de la nouvelle entité")
    secteur_activite_nouvelle_entite = forms.ChoiceField(
        choices=[("", "—")] + SecteurActivite.choices, required=False,
        label="Secteur d'activité de la nouvelle entité",
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
    infos propres à l'interrogatoire (poste/service au moment du contrôle —
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
        model = ControleEntite
        fields = ["commentaires_observations"]
        widgets = {"commentaires_observations": forms.Textarea(attrs={"rows": 4})}


class ScanSigneForm(TailwindModelForm):
    class Meta:
        model = ControleEntite
        fields = ["scan_signe"]


class RapportSigneForm(TailwindModelForm):
    class Meta:
        model = ControleEntite
        fields = ["rapport_signe"]


class InfosPVForm(TailwindModelForm):
    """Informations nécessaires à la génération du procès-verbal, absentes
    des autres formulaires (voir missions/generate_pv.py)."""

    class Meta:
        model = ControleEntite
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


class DeclarationChecklistForm(TailwindModelForm):
    """Une ligne de la checkliste des traitements déclarés — étape
    préalable au questionnaire (voir missions/views.py::questionnaire_checklist)."""

    class Meta:
        model = ReponsePage1
        fields = ["declaration_effectuee"]


DeclarationChecklistFormSet = modelformset_factory(ReponsePage1, form=DeclarationChecklistForm, extra=0)


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
