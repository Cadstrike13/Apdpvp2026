from django.urls import path
from . import views

app_name = "actes"

urlpatterns = [
    path("", views.acte_list, name="list"),
    path("nouveau/", views.acte_create, name="create"),
    path("<int:pk>/modifier/", views.acte_update, name="update"),
    path("<int:pk>/supprimer/", views.acte_delete, name="delete"),
    path("<int:pk>/pdf/", views.acte_pdf, name="pdf"),
]
