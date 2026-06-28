from django.urls import path
from . import views

app_name = "employees"

urlpatterns = [
    path("", views.employee_list, name="list"),
    path("nouveau/", views.employee_create, name="create"),
    path("<int:pk>/", views.employee_detail, name="detail"),
    path("<int:pk>/modifier/", views.employee_update, name="update"),
    path("<int:pk>/supprimer/", views.employee_delete, name="delete"),
]
