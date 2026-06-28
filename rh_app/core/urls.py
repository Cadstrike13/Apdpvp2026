from django.urls import path
from . import views

app_name = "roles"

urlpatterns = [
    path("", views.role_list, name="list"),
    path("affecter/", views.role_assign, name="assign"),
    path("<str:role>/retirer/<int:user_id>/", views.role_remove, name="remove"),
    path("audit/", views.audit_log, name="audit"),
    path("token/", views.token, name="token"),
]
