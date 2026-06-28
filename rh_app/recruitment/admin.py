from django.contrib import admin

from core.admin import SoftDeleteAdmin
from .models import JobPosting, Candidate


@admin.register(JobPosting)
class JobPostingAdmin(SoftDeleteAdmin):
    list_display = ("titre", "departement", "lieu", "statut", "date_limite", "is_deleted")
    list_filter = ("is_deleted", "statut", "departement")


@admin.register(Candidate)
class CandidateAdmin(SoftDeleteAdmin):
    list_display = ("nom", "offre", "statut", "note", "date_candidature", "is_deleted")
    list_filter = ("is_deleted", "statut")
