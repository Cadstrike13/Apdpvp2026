from django.urls import path
from . import views

app_name = "remuneration"

urlpatterns = [
    path("", views.remuneration_home, name="home"),
    path("salaires/nouveau/", views.salaire_create, name="salaire_create"),
    path("primes/nouvelle/", views.prime_create, name="prime_create"),
    path("primes/<int:pk>/modifier/", views.prime_update, name="prime_update"),
    path("primes/<int:pk>/supprimer/", views.prime_delete, name="prime_delete"),
    path("avances/nouvelle/", views.avance_create, name="avance_create"),
    path("avances/<int:pk>/modifier/", views.avance_update, name="avance_update"),
    path("avances/<int:pk>/supprimer/", views.avance_delete, name="avance_delete"),
    path("agents/<int:pk>/bulletin.pdf", views.bulletin_pdf, name="bulletin_pdf"),
]
