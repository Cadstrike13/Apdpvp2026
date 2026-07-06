from django.urls import path
from . import views

app_name = "rappels"

urlpatterns = [
    path("", views.rappel_list, name="list"),
    path("<int:pk>/traiter/", views.rappel_traiter, name="traiter"),
]
