"""Middlewares : contexte d'audit + authentification JWT inter-services."""
from .audit import set_current, client_ip
from .jwt_utils import decode_token


class AuditContextMiddleware:
    """Rend l'utilisateur courant et l'IP accessibles aux signaux d'audit."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current(getattr(request, "user", None), client_ip(request))
        try:
            return self.get_response(request)
        finally:
            set_current(None, None)


class JWTAuthenticationMiddleware:
    """
    Authentifie via un JWT (SSO inter-services) si aucune session active.
    Token cherché dans l'en-tête `Authorization: Bearer <token>` ou le cookie `access_token`.
    L'utilisateur local est créé/synchronisé à partir du token (username, email, rôles).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(request.user, "is_authenticated", False):
            token = self._get_token(request)
            if token:
                payload = decode_token(token)
                if payload:
                    user = self._sync_user(payload)
                    if user:
                        request.user = user
        return self.get_response(request)

    @staticmethod
    def _get_token(request):
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if auth.startswith("Bearer "):
            return auth[7:].strip()
        return request.COOKIES.get("access_token")

    @staticmethod
    def _sync_user(payload):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group

        User = get_user_model()
        username = payload.get("username")
        if not username:
            return None
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={"email": payload.get("email", "")},
        )
        # Synchronise email / superuser
        changed = False
        email = payload.get("email", "")
        if email and user.email != email:
            user.email = email
            changed = True
        if user.is_superuser != bool(payload.get("is_superuser")):
            user.is_superuser = bool(payload.get("is_superuser"))
            changed = True
        if changed:
            user.save(update_fields=["email", "is_superuser"])
        # Synchronise les rôles (groupes)
        roles = payload.get("roles") or []
        if roles:
            user.groups.set(Group.objects.filter(name__in=roles))
        return user
