from django.urls import path
from . import views

app_name = "documents"

urlpatterns = [
    path("", views.document_list, name="list"),
    path("nouveau/", views.document_create, name="create"),
    path("<int:pk>/modifier/", views.document_update, name="update"),
    path("<int:pk>/supprimer/", views.document_delete, name="delete"),
]
