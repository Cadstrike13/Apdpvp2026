from django.urls import path
from . import views

app_name = "leaves"

urlpatterns = [
    path("", views.leave_list, name="list"),
    path("nouvelle/", views.leave_create, name="create"),
    path("<int:pk>/modifier/", views.leave_update, name="update"),
    path("<int:pk>/supprimer/", views.leave_delete, name="delete"),
    path("<int:pk>/approuver/", views.approve_leave, name="approve"),
    path("<int:pk>/refuser/", views.reject_leave, name="reject"),
]
