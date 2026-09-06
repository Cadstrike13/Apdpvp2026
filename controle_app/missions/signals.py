from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from .models import (
    MissionControle,
    ReponsePage1,
    ReponsePage2,
    ReponsePage3,
    ReponsePage4,
    ReponsePage5,
    ReponseTraitement,
    Traitement,
)


@receiver(post_save, sender=MissionControle)
def creer_reponses_traitements(sender, instance, created, **kwargs):
    if not created:
        return
    for code, _ in Traitement.choices:
        reponse = ReponseTraitement.objects.create(mission=instance, traitement=code)
        ReponsePage1.objects.create(reponse=reponse)
        ReponsePage2.objects.create(reponse=reponse)
        ReponsePage3.objects.create(reponse=reponse)
        ReponsePage4.objects.create(reponse=reponse)
        ReponsePage5.objects.create(reponse=reponse)


@receiver(m2m_changed, sender=MissionControle.entites_controlees.through)
def proteger_entites_controlees_si_verrouillee(sender, instance, action, **kwargs):
    """Les entités contrôlées d'une mission sont immuables une fois le
    procès-verbal généré — même règle que `date_mission` (voir
    MissionControle.save()), mais appliquée ici car une M2M se modifie via
    .add()/.remove()/.set(), jamais via save()."""
    if action in {"pre_add", "pre_remove", "pre_clear"} and instance.pk and instance.est_verrouillee:
        raise ValidationError("Impossible de modifier les entités contrôlées : mission verrouillée.")
