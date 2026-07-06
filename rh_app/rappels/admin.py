from django.contrib import admin

from .models import Rappel


@admin.register(Rappel)
class RappelAdmin(admin.ModelAdmin):
    list_display = ("date_echeance", "type_rappel", "objet", "niveau", "traite")
    list_filter = ("traite", "type_rappel", "niveau")
    search_fields = ("objet",)
    date_hierarchy = "date_echeance"
