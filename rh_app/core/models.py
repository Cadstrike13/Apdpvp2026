from django.conf import settings
from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet conscient du soft delete."""

    def delete(self):
        # Suppression logique en masse
        return super().update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        # Suppression physique réelle
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    """Manager par défaut : ne retourne que les objets non supprimés."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    """Manager retournant TOUS les objets (y compris supprimés)."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class TimeStampedModel(models.Model):
    """Horodatage de création / modification."""

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        abstract = True


class SoftDeleteModel(TimeStampedModel):
    """
    Modèle de base : soft delete + horodatage.

    - `objects`     : uniquement les objets actifs (non supprimés)
    - `all_objects` : tous les objets, supprimés inclus
    """

    is_deleted = models.BooleanField(default=False, db_index=True, editable=False)
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Suppression logique (par défaut)."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(using=using, update_fields=["is_deleted", "deleted_at", "updated_at"])

    def hard_delete(self, using=None, keep_parents=False):
        """Suppression physique réelle en base."""
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Restaure un objet précédemment soft-deleted."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])


class AuditLog(models.Model):
    """
    Journal d'audit immuable : trace les actions (CRUD, soft delete, connexions).
    Jamais supprimé / modifié — c'est une trace.
    """

    ACTION_CHOICES = [
        ("create", "Création"),
        ("update", "Modification"),
        ("delete", "Suppression"),
        ("restore", "Restauration"),
        ("login", "Connexion"),
        ("logout", "Déconnexion"),
        ("login_failed", "Échec de connexion"),
    ]

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs"
    )
    username = models.CharField(max_length=150, blank=True)  # instantané (l'utilisateur peut être supprimé)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    model = models.CharField(max_length=100, blank=True)      # ex: employees.Employee
    object_id = models.CharField(max_length=50, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(null=True, blank=True)         # {champ: [ancien, nouveau]}
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Entrée d'audit"
        verbose_name_plural = "Journal d'audit"
        ordering = ["-timestamp", "-id"]

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.username or 'système'} · {self.get_action_display()} · {self.model}#{self.object_id}"
