from django.urls import reverse

from core.permissions import has_role, GESTION_ROLES, REMU_ROLES


def sidebar_nav(request):
    """Navigation latérale, filtrée selon les droits de l'utilisateur."""
    user = getattr(request, "user", None)

    # Nombre de rappels actifs (badge), seulement pour les utilisateurs connectés
    rappels_actifs = 0
    if getattr(user, "is_authenticated", False):
        from rappels.models import Rappel
        rappels_actifs = Rappel.objects.filter(traite=False).count()

    items = [
        {"label": "Tableau de bord", "url": reverse("dashboard:index"), "icon": "layout-dashboard"},
        {"label": "Employés", "url": reverse("employees:list"), "icon": "users"},
        {"label": "Recrutement", "url": reverse("recruitment:list"), "icon": "briefcase"},
        {"label": "Congés", "url": reverse("leaves:list"), "icon": "calendar-days"},
        {"label": "Formations", "url": reverse("training:list"), "icon": "graduation-cap"},
        {"label": "Documents", "url": reverse("documents:list"), "icon": "folder"},
        {"label": "Actes administratifs", "url": reverse("actes:list"), "icon": "file-text"},
        {"label": "Carrière", "url": reverse("carriere:home"), "icon": "trending-up"},
        {"label": "Rappels", "url": reverse("rappels:list"), "icon": "bell", "badge": rappels_actifs or None},
    ]
    if has_role(user, *REMU_ROLES):
        items.append({"label": "Rémunérations", "url": reverse("remuneration:home"), "icon": "wallet"})
    peut_gerer = has_role(user, *GESTION_ROLES)
    if peut_gerer:
        items.append({"label": "Rôles", "url": reverse("roles:list"), "icon": "shield-check"})
        items.append({"label": "Journal d'audit", "url": reverse("roles:audit"), "icon": "scroll-text"})
    return {"sidebar_nav": items, "peut_gerer_roles": peut_gerer, "rappels_actifs": rappels_actifs}
