from django import forms


class TailwindFieldsMixin:
    """Applique des classes Tailwind par défaut à chaque champ — évite de
    répéter le style dans chaque formulaire de l'app."""

    champ_classe = (
        "mt-1 block w-full rounded-md border-gray-300 bg-gray-50 shadow-sm "
        "focus:bg-white focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
    )
    case_classe = "h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
    fichier_classe = (
        "block w-full text-sm text-gray-600 bg-gray-50 rounded-md border border-gray-300 px-2 py-1.5 "
        "file:mr-3 file:py-2 file:px-4 file:rounded-md file:border-0 "
        "file:bg-blue-50 file:text-blue-700 file:font-medium hover:file:bg-blue-100"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", self.case_classe)
            elif isinstance(field.widget, forms.ClearableFileInput):
                field.widget.attrs.setdefault("class", self.fichier_classe)
            else:
                field.widget.attrs.setdefault("class", self.champ_classe)


class TailwindForm(TailwindFieldsMixin, forms.Form):
    pass


class TailwindModelForm(TailwindFieldsMixin, forms.ModelForm):
    pass
