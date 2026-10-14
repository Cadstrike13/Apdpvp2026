import json
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase

from controle_en_ligne import tasks
from controle_en_ligne.models import CheminListeBlanche, PreuveCapture
from controle_en_ligne.services.scanner_securite import CHEMINS_LISTE_BLANCHE

from .outils import TestAvecMedia, creer_mission


def chemin(valeur, actif=True):
    return CheminListeBlanche(chemin=valeur, justification="test", actif=actif)


class ValidationCheminTests(TestCase):
    def test_amorce_identique_a_la_liste_du_scanner(self):
        self.assertEqual(set(CheminListeBlanche.chemins_actifs()), set(CHEMINS_LISTE_BLANCHE))

    def test_chemin_exact_accepte(self):
        c = chemin("  /wp-admin/install.php ")
        c.full_clean()
        self.assertEqual(c.chemin, "/wp-admin/install.php")

    def test_chemins_refuses(self):
        for valeur in ["robots.txt", "//hote.ga/x", "https://x.ga/.env", "/../etc/passwd",
                       "/admin/*", "/page?id=1", "/a#b", "/a b", "/%2e%2e/x"]:
            with self.subTest(valeur=valeur), self.assertRaises(ValidationError):
                chemin(valeur).full_clean()

    def test_plafond_des_chemins_actifs(self):
        manquants = CheminListeBlanche.MAX_ACTIFS - CheminListeBlanche.objects.filter(actif=True).count()
        CheminListeBlanche.objects.bulk_create(
            [CheminListeBlanche(chemin=f"/plafond-{i}", justification="test") for i in range(manquants)]
        )
        with self.assertRaises(ValidationError):
            chemin("/un-de-trop").full_clean()
        chemin("/inactif", actif=False).full_clean()  # un chemin inactif ne compte pas

    def test_seuls_les_actifs_sont_testes(self):
        CheminListeBlanche.objects.filter(chemin="/.env").update(actif=False)
        self.assertNotIn("/.env", CheminListeBlanche.chemins_actifs())


class ScanAvecListeEditableTests(TestAvecMedia):
    def test_liste_de_la_base_transmise_et_archivee(self):
        CheminListeBlanche.objects.exclude(chemin="/.git/config").update(actif=False)
        mission = creer_mission()
        with mock.patch.object(tasks, "scanner_securite", return_value={"https_complet": True}) as scan:
            tasks._scanner_securite_task(mission)
        self.assertEqual(scan.call_args.kwargs["chemins"], ("/.git/config",))
        preuve = PreuveCapture.objects.get(mission=mission, scenario_lie__contains="securite")
        with preuve.fichier.open("rb") as f:
            self.assertEqual(json.load(f)["resultat"]["chemins_testes"], ["/.git/config"])
