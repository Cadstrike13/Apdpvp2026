from django.urls import path
from . import views

app_name = "training"

urlpatterns = [
    path("", views.training_list, name="list"),
    path("nouvelle/", views.training_create, name="create"),
    path("<int:pk>/modifier/", views.training_update, name="update"),
    path("<int:pk>/supprimer/", views.training_delete, name="delete"),
]
