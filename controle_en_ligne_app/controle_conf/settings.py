"""
Réglages du service controle_en_ligne_app (APDPVP 2026).

Toute valeur sensible ou propre au déploiement vient de l'environnement
(fichier .env non versionné, voir .env.example). Aucun secret dans ce fichier.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(nom: str, defaut: bool = False) -> bool:
    return os.environ.get(nom, str(defaut)).strip().lower() in {"1", "true", "yes", "oui"}


def _liste(nom: str, defaut: str = "") -> list[str]:
    return [v.strip() for v in os.environ.get(nom, defaut).split(",") if v.strip()]


DEBUG = _bool("DEBUG", False)

SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-uniquement-ne-pas-utiliser-en-production"
    else:
        raise ImproperlyConfigured("SECRET_KEY doit être défini dans l'environnement.")

# Clé partagée entre les services pour valider les jetons émis par auth_app.
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "")

ALLOWED_HOSTS = _liste("ALLOWED_HOSTS", "controle.apdpvp.local,localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = _liste("CSRF_TRUSTED_ORIGINS", "http://controle.apdpvp.local")

# À activer dès que Traefik termine TLS devant le service (entrée websecure).
# Tant que le routage reste en HTTP (entrée web), le laisser à False sinon
# les cookies de session ne seraient jamais renvoyés par le navigateur.
HTTPS_ACTIF = _bool("HTTPS_ACTIF", False)
if HTTPS_ACTIF:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SESSION_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "simple_history",
    "core",
    "controle_en_ligne",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "controle_conf.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "controle_conf.wsgi.application"


# Base de données : SQLite dans le volume nommé controle_db (cf. CLAUDE.md racine).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DATABASE_PATH", str(BASE_DIR / "db" / "controle.sqlite3")),
        # Le worker Celery et le serveur web écrivent dans la même base :
        # on attend un verrou plutôt que d'échouer immédiatement.
        "OPTIONS": {"timeout": 20},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = os.environ.get("LANGUAGE_CODE", "fr-fr")
TIME_ZONE = "Africa/Libreville"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATIC_ROOT = os.environ.get("STATIC_ROOT", str(BASE_DIR / "staticfiles"))
MEDIA_URL = "media/"
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", str(BASE_DIR / "media"))
# Les preuves (media) ne sont jamais servies publiquement : accès par l'admin seulement.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}


# Celery : les scans tournent dans un worker séparé (broker Redis sur controle_net).
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_ALWAYS_EAGER = _bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TIMEZONE = TIME_ZONE
# Un contrôle complet (Playwright, 4 scénarios) dure quelques minutes au plus.
CELERY_TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", "1800"))


# Scanners : identité déclarée et politesse envers les sites contrôlés.
CONTROLE_USER_AGENT = os.environ.get(
    "CONTROLE_USER_AGENT",
    "APDPVP-ControleEnLigne/1.0 (+https://apdpvp.ga ; controle en ligne)",
)
CONTROLE_RESPECTER_ROBOTS = _bool("CONTROLE_RESPECTER_ROBOTS", True)


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "controle_en_ligne": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
    },
}
