from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

GROUPE_ADMINISTRATEUR = "Administrateur"
GROUPE_CHEF_MISSION = "Chef de mission"
GROUPE_AGENT = "Agent contrôleur"


def est_dans_groupe(user, *groupes):
    return user.is_superuser or user.groups.filter(name__in=groupes).exists()


def require_groupe(*groupes):
    def decorateur(vue):
        @wraps(vue)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not est_dans_groupe(request.user, *groupes):
                raise PermissionDenied("Vous n'avez pas les droits nécessaires.")
            return vue(request, *args, **kwargs)

        return wrapper

    return decorateur


def require_membre_controle(vue):
    """Tout membre (chef ou agent) du groupe de contrôle de CE contrôle
    d'entité (ControleEntite) — le groupe de contrôle est propre à chaque
    entité, pas à la mission entière."""

    @wraps(vue)
    @login_required
    def wrapper(request, controle_pk, *args, **kwargs):
        from missions.models import ControleEntite

        controle = get_object_or_404(ControleEntite, pk=controle_pk)
        request.controle = controle
        if request.user.is_superuser:
            return vue(request, controle_pk, *args, **kwargs)
        est_membre = controle.membres_groupe.filter(agent__user=request.user).exists()
        if not est_membre:
            raise PermissionDenied("Vous n'êtes pas membre du groupe de contrôle de cette entité.")
        return vue(request, controle_pk, *args, **kwargs)

    return wrapper


def require_chef_controle(vue):
    """Uniquement le chef de CE contrôle d'entité (validation)."""

    @wraps(vue)
    @login_required
    def wrapper(request, controle_pk, *args, **kwargs):
        from missions.models import ControleEntite

        controle = get_object_or_404(ControleEntite, pk=controle_pk)
        request.controle = controle
        if request.user.is_superuser:
            return vue(request, controle_pk, *args, **kwargs)
        est_chef = controle.membres_groupe.chefs().filter(agent__user=request.user).exists()
        if not est_chef:
            raise PermissionDenied("Seul le chef de mission peut valider ce contrôle.")
        return vue(request, controle_pk, *args, **kwargs)

    return wrapper
