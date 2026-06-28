from django.contrib import admin
from django.utils import timezone

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Journal d'audit en lecture seule (aucune création/modification/suppression)."""

    list_display = ("timestamp", "username", "action", "model", "object_id", "object_repr", "ip_address")
    list_filter = ("action", "model")
    search_fields = ("username", "object_repr", "object_id")
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class SoftDeleteAdmin(admin.ModelAdmin):
    """
    Admin de base pour les modèles à soft delete :
    - affiche aussi les objets supprimés (via all_objects)
    - colonne / filtre `is_deleted`
    - actions : suppression logique, restauration, suppression définitive
    """

    actions = ["soft_delete_selected", "restore_selected", "hard_delete_selected"]

    def get_queryset(self, request):
        return self.model.all_objects.get_queryset()

    @admin.action(description="Supprimer (soft delete)")
    def soft_delete_selected(self, request, queryset):
        n = queryset.update(is_deleted=True, deleted_at=timezone.now())
        self.message_user(request, f"{n} élément(s) supprimé(s) logiquement.")

    @admin.action(description="Restaurer")
    def restore_selected(self, request, queryset):
        n = queryset.update(is_deleted=False, deleted_at=None)
        self.message_user(request, f"{n} élément(s) restauré(s).")

    @admin.action(description="Supprimer définitivement (hard delete)")
    def hard_delete_selected(self, request, queryset):
        count = queryset.count()
        for obj in queryset:
            obj.hard_delete()
        self.message_user(request, f"{count} élément(s) supprimé(s) définitivement.")
