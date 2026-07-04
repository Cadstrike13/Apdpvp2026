from django.contrib import admin

from .models import EntiteControlee


@admin.register(EntiteControlee)
class EntiteControleeAdmin(admin.ModelAdmin):
    list_display = ("nom", "est_supprime")
    search_fields = ("nom",)
