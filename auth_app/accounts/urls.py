"""URL configuration for the accounts app."""
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import CustomPasswordResetForm, CustomSetPasswordForm

app_name = "accounts"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("connexion/", views.AccountsLoginView.as_view(), name="login"),
    path("deconnexion/", views.logout_view, name="logout"),
    path("profil/", views.profile, name="profile"),
    path("mot-de-passe/", views.change_password, name="change_password"),
    path("token/", views.token_view, name="token"),

    # Mot de passe oublié
    path(
        "mot-de-passe-oublie/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
            form_class=CustomPasswordResetForm,
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "mot-de-passe-oublie/envoye/",
        auth_views.PasswordResetDoneView.as_view(template_name="registration/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "mot-de-passe-oublie/confirmer/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            form_class=CustomSetPasswordForm,
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "mot-de-passe-oublie/termine/",
        auth_views.PasswordResetCompleteView.as_view(template_name="registration/password_reset_complete.html"),
        name="password_reset_complete",
    ),
]
