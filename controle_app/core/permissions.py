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


def require_membre_mission(vue):
    """Tout membre (chef ou agent) du groupe de contrôle de CETTE mission."""

    @wraps(vue)
    @login_required
    def wrapper(request, mission_pk, *args, **kwargs):
        from missions.models import MissionControle

        mission = get_object_or_404(MissionControle, pk=mission_pk)
        request.mission = mission
        if request.user.is_superuser:
            return vue(request, mission_pk, *args, **kwargs)
        est_membre = mission.membres_groupe.filter(agent__user=request.user).exists()
        if not est_membre:
            raise PermissionDenied("Vous n'êtes pas membre du groupe de contrôle de cette mission.")
        return vue(request, mission_pk, *args, **kwargs)

    return wrapper


def require_chef_mission(vue):
    """Uniquement le chef de CETTE mission (validation)."""

    @wraps(vue)
    @login_required
    def wrapper(request, mission_pk, *args, **kwargs):
        from missions.models import MissionControle

        mission = get_object_or_404(MissionControle, pk=mission_pk)
        request.mission = mission
        if request.user.is_superuser:
            return vue(request, mission_pk, *args, **kwargs)
        est_chef = mission.membres_groupe.chefs().filter(agent__user=request.user).exists()
        if not est_chef:
            raise PermissionDenied("Seul le chef de mission peut valider ce contrôle.")
        return vue(request, mission_pk, *args, **kwargs)

    return wrapper
