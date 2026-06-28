"""Logique du journal d'audit : contexte courant (thread-local) + signaux."""
import threading

from django.db import models

_local = threading.local()

# Champs ignorés dans le diff d'audit
AUDIT_EXCLUDE_FIELDS = {"created_at", "updated_at", "deleted_at"}

# Modèles audités (créations / modifications / suppressions)
AUDITED_MODELS = [
    "employees.Department", "employees.Employee",
    "leaves.LeaveRequest",
    "recruitment.JobPosting", "recruitment.Candidate",
    "training.TrainingProgram",
    "documents.Document",
    "actes.ActeAdministratif",
]


# --- Contexte courant (rempli par le middleware) ---
def set_current(user=None, ip=None):
    _local.user = user
    _local.ip = ip


def get_current_user():
    user = getattr(_local, "user", None)
    return user if (user is not None and getattr(user, "is_authenticated", False)) else None


def get_current_ip():
    return getattr(_local, "ip", None)


def _serialize(value):
    if isinstance(value, models.Model):
        return str(value.pk)
    return None if value is None else str(value)


def log_action(action, instance=None, changes=None, *, model="", object_id="",
               object_repr="", user=None, username="", ip=None):
    """Crée une entrée d'audit. Ne lève jamais d'exception bloquante."""
    from .models import AuditLog
    try:
        if instance is not None:
            model = model or f"{instance._meta.app_label}.{instance._meta.object_name}"
            object_id = object_id or str(instance.pk)
            object_repr = object_repr or str(instance)[:255]
        if user is None:
            user = get_current_user()
        if not username and user is not None:
            username = user.get_username()
        AuditLog.objects.create(
            user=user, username=username, action=action, model=model,
            object_id=str(object_id), object_repr=object_repr[:255],
            changes=changes, ip_address=ip if ip is not None else get_current_ip(),
        )
    except Exception:
        # L'audit ne doit jamais casser une requête métier
        pass


# --- Signaux modèles ---
def _pre_save(sender, instance, **kwargs):
    if kwargs.get("raw"):  # chargement de fixtures : pas d'audit
        return
    if not instance.pk:
        instance._audit_old = None
        return
    manager = getattr(sender, "all_objects", None) or sender._default_manager
    try:
        instance._audit_old = manager.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._audit_old = None


def _post_save(sender, instance, created, **kwargs):
    if kwargs.get("raw"):
        return
    if created:
        log_action("create", instance)
        return
    old = getattr(instance, "_audit_old", None)
    changes = {}
    for field in instance._meta.fields:
        if field.name in AUDIT_EXCLUDE_FIELDS:
            continue
        old_v = getattr(old, field.attname, None) if old else None
        new_v = getattr(instance, field.attname, None)
        if old_v != new_v:
            changes[field.name] = [_serialize(old_v), _serialize(new_v)]
    if not changes:
        return
    if old is not None and "is_deleted" in changes:
        action = "delete" if instance.is_deleted else "restore"
    else:
        action = "update"
    log_action(action, instance, changes=changes)


def _post_delete(sender, instance, **kwargs):
    log_action("delete", instance, object_repr=f"{instance} (suppression physique)")


# --- Signaux authentification ---
def client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _on_login(sender, request, user, **kwargs):
    log_action("login", user=user, model="auth.User", object_id=user.pk,
               object_repr=user.get_username(), ip=client_ip(request) if request else None)


def _on_logout(sender, request, user, **kwargs):
    if user:
        log_action("logout", user=user, model="auth.User", object_id=user.pk,
                   object_repr=user.get_username(), ip=client_ip(request) if request else None)


def _on_login_failed(sender, credentials, request=None, **kwargs):
    log_action("login_failed", model="auth.User",
               username=credentials.get("username", ""),
               object_repr=credentials.get("username", ""),
               ip=client_ip(request) if request else None)


def connect_signals():
    from django.apps import apps
    from django.db.models.signals import pre_save, post_save, post_delete
    from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed

    for label in AUDITED_MODELS:
        model = apps.get_model(label)
        pre_save.connect(_pre_save, sender=model, dispatch_uid=f"audit_pre_{label}")
        post_save.connect(_post_save, sender=model, dispatch_uid=f"audit_post_{label}")
        post_delete.connect(_post_delete, sender=model, dispatch_uid=f"audit_del_{label}")

    user_logged_in.connect(_on_login, dispatch_uid="audit_login")
    user_logged_out.connect(_on_logout, dispatch_uid="audit_logout")
    user_login_failed.connect(_on_login_failed, dispatch_uid="audit_login_failed")
