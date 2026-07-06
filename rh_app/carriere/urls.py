from django.urls import path
from . import views

app_name = "carriere"

urlpatterns = [
    path("", views.carriere_home, name="home"),
    path("evaluations/nouvelle/", views.evaluation_create, name="evaluation_create"),
    path("evaluations/<int:pk>/modifier/", views.evaluation_update, name="evaluation_update"),
    path("evaluations/<int:pk>/supprimer/", views.evaluation_delete, name="evaluation_delete"),
    path("avancements/nouveau/", views.avancement_create, name="avancement_create"),
    path("avancements/<int:pk>/modifier/", views.avancement_update, name="avancement_update"),
    path("avancements/<int:pk>/supprimer/", views.avancement_delete, name="avancement_delete"),
    path("postes/<int:pk>/fiche.pdf", views.fiche_poste_pdf, name="fiche_poste_pdf"),
]
