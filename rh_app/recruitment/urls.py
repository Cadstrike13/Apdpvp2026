from django.urls import path
from . import views

app_name = "recruitment"

urlpatterns = [
    path("", views.recruitment_list, name="list"),
    path("offres/nouvelle/", views.job_create, name="job_create"),
    path("offres/<int:pk>/modifier/", views.job_update, name="job_update"),
    path("offres/<int:pk>/supprimer/", views.job_delete, name="job_delete"),
    path("candidats/nouveau/", views.candidate_create, name="candidate_create"),
    path("candidats/<int:pk>/modifier/", views.candidate_update, name="candidate_update"),
    path("candidats/<int:pk>/supprimer/", views.candidate_delete, name="candidate_delete"),
]
