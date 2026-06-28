from django.urls import reverse

from core.permissions import has_role, GESTION_ROLES


def sidebar_nav(request):
    """Navigation latérale, filtrée selon les droits de l'utilisateur."""
    items = [
        {"label": "Tableau de bord", "url": reverse("dashboard:index"), "icon": "layout-dashboard"},
        {"label": "Employés", "url": reverse("employees:list"), "icon": "users"},
        {"label": "Recrutement", "url": reverse("recruitment:list"), "icon": "briefcase"},
        {"label": "Congés", "url": reverse("leaves:list"), "icon": "calendar-days"},
        {"label": "Formations", "url": reverse("training:list"), "icon": "graduation-cap"},
        {"label": "Documents", "url": reverse("documents:list"), "icon": "folder"},
        {"label": "Actes administratifs", "url": reverse("actes:list"), "icon": "file-text"},
    ]
    peut_gerer = has_role(getattr(request, "user", None), *GESTION_ROLES)
    if peut_gerer:
        items.append({"label": "Rôles", "url": reverse("roles:list"), "icon": "shield-check"})
        items.append({"label": "Journal d'audit", "url": reverse("roles:audit"), "icon": "scroll-text"})
    return {"sidebar_nav": items, "peut_gerer_roles": peut_gerer}
