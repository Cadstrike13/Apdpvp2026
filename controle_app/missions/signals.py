from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import (
    ControleEntite,
    ReponsePage1,
    ReponsePage2,
    ReponsePage3,
    ReponsePage4,
    ReponsePage5,
    ReponseTraitement,
    Traitement,
)


@receiver(post_save, sender=ControleEntite)
def creer_reponses_traitements(sender, instance, created, **kwargs):
    if not created:
        return
    for code, _ in Traitement.choices:
        reponse = ReponseTraitement.objects.create(controle=instance, traitement=code)
        ReponsePage1.objects.create(reponse=reponse)
        ReponsePage2.objects.create(reponse=reponse)
        ReponsePage3.objects.create(reponse=reponse)
        ReponsePage4.objects.create(reponse=reponse)
        ReponsePage5.objects.create(reponse=reponse)
