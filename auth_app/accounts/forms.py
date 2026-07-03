from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
)

User = get_user_model()

INPUT_CLASSES = (
    "w-full px-4 py-2.5 rounded-lg border border-gray-300 text-gray-800 "
    "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
)


def _style(field, **attrs):
    base = {"class": INPUT_CLASSES}
    base.update(attrs)
    field.widget.attrs.update(base)


class LoginForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Identifiant ou mot de passe incorrect.",
        "inactive": "Ce compte est désactivé.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields["username"], placeholder="Identifiant", autofocus=True)
        _style(self.fields["password"], placeholder="Mot de passe")
        self.fields["username"].label = "Identifiant"
        self.fields["password"].label = "Mot de passe"


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "telephone", "avatar"]
        labels = {
            "first_name": "Prénom",
            "last_name": "Nom",
            "email": "Email",
            "telephone": "Téléphone",
            "avatar": "Photo de profil",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == "avatar":
                field.widget.attrs.update({"class": "block w-full text-sm text-gray-600"})
            else:
                _style(field)


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields["old_password"], placeholder="Mot de passe actuel")
        _style(self.fields["new_password1"], placeholder="Nouveau mot de passe")
        _style(self.fields["new_password2"], placeholder="Confirmer le nouveau mot de passe")
        self.fields["old_password"].label = "Mot de passe actuel"
        self.fields["new_password1"].label = "Nouveau mot de passe"
        self.fields["new_password2"].label = "Confirmation"


class CustomPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields["email"], placeholder="Votre adresse email")
        self.fields["email"].label = "Email"


class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields["new_password1"], placeholder="Nouveau mot de passe")
        _style(self.fields["new_password2"], placeholder="Confirmer le nouveau mot de passe")
        self.fields["new_password1"].label = "Nouveau mot de passe"
        self.fields["new_password2"].label = "Confirmation"
