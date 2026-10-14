import shutil
import tempfile

from django.test import TestCase, override_settings

from core.models import AgentProvider, ResponsableTraitement
from controle_en_ligne.models import MissionControleEnLigne


class TestAvecMedia(TestCase):
    """Isole les fichiers de preuve dans un dossier temporaire."""

    @classmethod
    def setUpClass(cls):
        cls._media = tempfile.mkdtemp(prefix="controle-tests-")
        cls._override = override_settings(MEDIA_ROOT=cls._media)
        cls._override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._override.disable()
        shutil.rmtree(cls._media, ignore_errors=True)


def creer_mission(**champs) -> MissionControleEnLigne:
    organisme = ResponsableTraitement.objects.create(raison_sociale="Organisme test")
    valeurs = {
        "responsable_traitement": organisme,
        "origine_controle": "programme",
        "nom_service": "Site test",
        "url_principale": "https://exemple.ga",
    }
    valeurs.update(champs)
    return MissionControleEnLigne.objects.create(**valeurs)


def creer_agent(nom="Mba") -> AgentProvider:
    return AgentProvider.objects.create(nom=nom, prenom="Aline", fonction="Contrôleuse")
