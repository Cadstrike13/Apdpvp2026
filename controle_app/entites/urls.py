from django.urls import path

from . import views

app_name = "entites"

urlpatterns = [
    path("", views.entite_list, name="entite_list"),
    path("<int:entite_pk>/", views.entite_detail, name="entite_detail"),
    path("<int:entite_pk>/secteur/", views.entite_secteur_modifier, name="entite_secteur_modifier"),
]
