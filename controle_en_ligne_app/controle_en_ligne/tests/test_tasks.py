import time
from unittest import mock

from core.models import JournalAction
from controle_en_ligne import tasks
from controle_en_ligne.models import ConstatCookie, ConstatSecurite, PageIdentifiee, Qualification

from .outils import TestAvecMedia, creer_agent, creer_mission

DANS_30_JOURS = time.time() + 30 * 86400 - 60

CARTOGRAPHIE = {
    "url_depart": "https://exemple.ga", "url_finale": "https://exemple.ga/", "pages_visitees": 5,
    "pages": [
        {"type_page": "accueil", "url": "https://exemple.ga/", "presente": True, "indice": "Page de départ"},
        {"type_page": "confidentialite", "url": "https://exemple.ga/vie-privee", "presente": True, "indice": "Lien"},
        {"type_page": "cgu", "url": "https://exemple.ga/cgu", "presente": True, "indice": "Lien"},
        {"type_page": "mentions_legales", "url": "", "presente": False, "indice": "Aucun lien"},
        {"type_page": "cgv", "url": "https://exemple.ga/cgv", "presente": None, "indice": "robots.txt"},
        {"type_page": "inconnu", "url": "x", "presente": True},
    ],
    "bloquees_par_robots": ["https://exemple.ga/cgv"], "erreurs": [], "certificat_non_verifie": False,
}
SECURITE = {
    "https_complet": True, "certificat_valide": False, "fichiers_exposes": [".git/HEAD"],
    # Clés qu'un scan ne doit jamais pouvoir écrire :
    "conformite": "conforme", "criticite": "faible", "valide_par_agent": True, "cle_inconnue": 1,
}
COOKIES = {
    "avant": [
        {"nom": "_ga", "domaine": ".google-analytics.com", "est_tiers": True,
         "expires": DANS_30_JOURS, "valeur": "GA1.2.999"},
        {"name": "uid", "domain": "exemple.ga", "type_traceur": "local_storage", "est_tiers": False, "value": "abc"},
        {"nom": "canvas-hash", "domaine": "fp.example", "type_traceur": "webgl_fingerprint", "est_tiers": True},
    ],
    "acceptation": [],
    "refus": [{"nom": "sess", "domaine": "exemple.ga", "est_tiers": False, "expires": -1}],
    "modification": [],
}
TIERS = [{"domaine_tiers": "google-analytics.com", "categorie": "analytics"},
         {"domaine_tiers": "cdn.x.com", "categorie": "n-importe"}]


def scanners(**remplacements):
    """Remplace les quatre scanners appelés par tasks.py."""
    valeurs = {
        "scanner_cartographie": CARTOGRAPHIE, "scanner_securite": SECURITE,
        "scanner_cookies": COOKIES, "scanner_tiers": TIERS, **remplacements,
    }
    patchs = []
    for nom, valeur in valeurs.items():
        if isinstance(valeur, Exception):
            patchs.append(mock.patch.object(tasks, nom, side_effect=valeur))
        else:
            patchs.append(mock.patch.object(tasks, nom, return_value=valeur))
    return patchs


class OrchestrationTests(TestAvecMedia):
    def lancer(self, mission, **remplacements):
        patchs = scanners(**remplacements)
        for p in patchs:
            p.start()
        try:
            return tasks.lancer_scans_automatiques(mission.pk)
        finally:
            for p in patchs:
                p.stop()

    def test_cas_nominal(self):
        mission = creer_mission()
        PageIdentifiee.objects.create(mission=mission, type_page="cgu", url="https://exemple.ga/conditions", origine="manuel")
        resultat = self.lancer(mission)
        mission.refresh_from_db()

        self.assertEqual(resultat["statut"], "terminee")
        self.assertEqual(mission.erreurs_scan, [])

        # Cartographie : page manuelle conservée, absences et pages non vérifiées enregistrées.
        pages = {(p.type_page, p.origine): p for p in mission.pages.all()}
        self.assertEqual(pages[("cgu", "manuel")].url, "https://exemple.ga/conditions")
        self.assertNotIn(("cgu", "auto"), pages)
        self.assertFalse(pages[("mentions_legales", "auto")].presente)
        self.assertIsNone(pages[("cgv", "auto")].presente)
        self.assertEqual(len(pages), 5)

        # Sécurité : aucune qualification créée, signal de risque posé.
        securite = mission.constatsecurite
        self.assertIsNone(securite.qualification)
        self.assertTrue(securite.risque_technique_suspecte)
        self.assertEqual(Qualification.objects.filter(mission=mission).count(), 0)

        # Traceurs : type transmis, type inconnu répertorié, durée calculée.
        cookies = {c.nom: c for c in mission.constats_cookies.all()}
        self.assertEqual(len(cookies), 4)
        self.assertEqual(cookies["_ga"].duree_vie_jours, 30)
        self.assertEqual(cookies["uid"].type_traceur, "local_storage")
        self.assertEqual(cookies["canvas-hash"].type_traceur, "non_classe")
        self.assertEqual(cookies["canvas-hash"].type_brut, "webgl_fingerprint")
        self.assertIn("À classer", cookies["canvas-hash"].fait_observe)
        self.assertIsNone(cookies["sess"].duree_vie_jours)

        # Tiers : catégorie inconnue rangée en « autre ».
        self.assertEqual(set(mission.constats_tiers.values_list("categorie", flat=True)), {"analytics", "autre"})

        # Preuves : une par scan et par scénario, empreinte valide, valeurs purgées.
        preuves = list(mission.preuves.all())
        self.assertEqual(len(preuves), 7)
        contenu = ""
        for preuve in preuves:
            self.assertTrue(preuve.integrite_verifiee())
            with preuve.fichier.open("rb") as f:
                contenu += f.read().decode()
        self.assertNotIn("GA1.2.999", contenu)
        self.assertNotIn('"abc"', contenu)
        self.assertIn("webgl_fingerprint", contenu)

        self.assertEqual(set(mission.scenarios_tests.values_list("numero_test", flat=True)), {1, 2, 3, 4, 5, 10})
        self.assertFalse(mission.tous_constats_valides())
        actions = set(JournalAction.objects.values_list("action", flat=True))
        self.assertTrue({"lancement_scans", "fin_scans"} <= actions)

    def test_relance_respecte_le_travail_de_l_agent(self):
        mission = creer_mission()
        agent = creer_agent()
        self.lancer(mission)

        cookie = mission.constats_cookies.get(nom="_ga")
        cookie.qualifier(conformite="non_conforme", criticite="elevee").valider(agent)
        brouillon = mission.constats_cookies.get(nom="uid")
        brouillon.qualifier(analyse="En cours d'examen")
        securite = mission.constatsecurite
        securite.qualifier(analyse="À confirmer")

        self.lancer(mission, scanner_securite={"https_complet": False, "certificat_valide": True})

        self.assertEqual(mission.constats_cookies.filter(nom="_ga").count(), 2)
        self.assertEqual(mission.constats_cookies.filter(nom="uid").count(), 2)
        self.assertTrue(mission.constats_cookies.get(pk=cookie.pk).est_valide)
        self.assertEqual(mission.constats_cookies.filter(nom="sess").count(), 1)

        securite.refresh_from_db()
        self.assertEqual(securite.fichiers_exposes, [".git/HEAD"])  # faits non écrasés
        self.assertEqual(ConstatSecurite.objects.filter(mission=mission).count(), 1)

    def test_un_scanner_en_panne_n_arrete_pas_les_autres(self):
        mission = creer_mission()
        self.lancer(mission, scanner_cookies=RuntimeError("Timeout Playwright après 30 s"))
        mission.refresh_from_db()

        self.assertEqual(mission.statut, "en_cours")
        self.assertEqual([e["scan"] for e in mission.erreurs_scan], ["cookies"])
        self.assertIn("Timeout", mission.erreurs_scan[0]["erreur"])
        self.assertEqual(mission.constats_cookies.count(), 0)
        self.assertTrue(ConstatSecurite.objects.filter(mission=mission).exists())
        self.assertEqual(mission.constats_tiers.count(), 2)
        test_acceptation = mission.scenarios_tests.get(numero_test=3)
        self.assertFalse(test_acceptation.execute)
        self.assertTrue(JournalAction.objects.filter(action="echec_scan").exists())

    def test_scanner_non_versionne(self):
        """Les modules de remplacement lèvent NotImplementedError : la mission le signale."""
        mission = creer_mission()
        with mock.patch.object(tasks, "scanner_cartographie", return_value=CARTOGRAPHIE):
            tasks.lancer_scans_automatiques(mission.pk)
        mission.refresh_from_db()
        self.assertEqual({e["scan"] for e in mission.erreurs_scan}, {"securite", "cookies", "tiers"})
        self.assertEqual(mission.pages.count(), 5)


class TypesTraceurTests(TestAvecMedia):
    def test_chaque_type_connu_est_conserve(self):
        connus = [cle for cle, _ in ConstatCookie.TYPES_TRACEUR if cle != "non_classe"]
        mission = creer_mission()
        entrees = [{"nom": f"t-{t}", "domaine": "d", "est_tiers": False, "type_traceur": t} for t in connus]
        cookies = dict(COOKIES, avant=entrees)
        patchs = scanners(scanner_cookies=cookies)
        for p in patchs:
            p.start()
        try:
            tasks.lancer_scans_automatiques(mission.pk)
        finally:
            for p in patchs:
                p.stop()
        enregistres = dict(mission.constats_cookies.filter(scenario="avant").values_list("nom", "type_traceur"))
        self.assertEqual(enregistres, {f"t-{t}": t for t in connus})
