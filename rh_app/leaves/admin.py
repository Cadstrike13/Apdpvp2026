from django.contrib import admin

from core.admin import SoftDeleteAdmin
from .models import LeaveRequest


@admin.register(LeaveRequest)
class LeaveRequestAdmin(SoftDeleteAdmin):
    list_display = ("employe", "type_conge", "date_debut", "date_fin", "statut", "is_deleted")
    list_filter = ("is_deleted", "statut", "type_conge")
