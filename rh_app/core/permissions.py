"""Contrôles d'accès par rôle."""
from django.contrib.auth.decorators import user_passes_test

from .roles import Roles

# Rôles autorisés à gérer les rôles et consulter l'audit
GESTION_ROLES = (Roles.ADMIN, Roles.SUPERUSER, Roles.DIRECTEUR)


def has_role(user, *roles):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=roles).exists()


def role_required(*roles):
    """Décorateur : réserve une vue aux rôles indiqués (superuser toujours autorisé)."""
    return user_passes_test(lambda u: has_role(u, *roles))
