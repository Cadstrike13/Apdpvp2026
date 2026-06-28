from django.contrib import admin

from core.admin import SoftDeleteAdmin
from .models import TrainingProgram


@admin.register(TrainingProgram)
class TrainingProgramAdmin(SoftDeleteAdmin):
    list_display = ("titre", "prestataire", "type_formation", "statut", "date_debut", "is_deleted")
    list_filter = ("is_deleted", "statut", "type_formation")
    filter_horizontal = ("participants",)
