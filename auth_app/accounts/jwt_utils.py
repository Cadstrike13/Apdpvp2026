"""
Utilitaires JWT inter-services APDPVP.

Contrat de token (HS256, clé partagée settings.JWT_SECRET_KEY) :
{
  "sub": <user_id>, "username": "...", "email": "...",
  "roles": ["agent_rh", ...], "iss": "apdpvp",
  "iat": <timestamp>, "exp": <timestamp>
}
Tous les services (auth_app, rh_app, ...) doivent partager la même JWT_SECRET_KEY.
Contrat identique à rh_app/core/jwt_utils.py — ne pas diverger.
"""
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings

ALGORITHM = "HS256"
ISSUER = "apdpvp"
DUREE_VALIDITE = timedelta(hours=12)


def encode_token(user, duree=DUREE_VALIDITE):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.pk),
        "username": user.get_username(),
        "email": getattr(user, "email", "") or "",
        "roles": list(user.groups.values_list("name", flat=True)),
        "is_superuser": user.is_superuser,
        "iss": ISSUER,
        "iat": now,
        "exp": now + duree,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token):
    """Retourne le payload si valide, sinon None."""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM], issuer=ISSUER)
    except jwt.PyJWTError:
        return None
