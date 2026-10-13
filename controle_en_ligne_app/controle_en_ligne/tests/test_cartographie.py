"""
Tests du scanner de cartographie sur un petit site servi en local
(aucun accès réseau extérieur).
"""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import TestCase

from controle_en_ligne.services.scanner_cartographie import (
    _types_correspondants, scanner_cartographie,
)

ACCUEIL = """<!doctype html><html><head><title>Boutique test</title></head><body>
<nav>
  <a href="/vie-privee">Politique de confidentialité</a>
  <a href="/cookies#preferences">Gestion des cookies</a>
  <a href="/cgv.pdf">Conditions générales de vente</a>
  <a href="conditions-utilisation">CGU</a>
  <a href="/mentions">Mentions légales</a>
  <a href="/contact">Nous contacter</a>
  <a href="/secret">Mon compte</a>
  <a href="/blog">Blog</a>
  <a href="https://reseau-social.example/page">Suivez-nous</a>
  <a href="mailto:dpo@exemple.ga">Écrire au DPO</a>
  <a href="#haut">Haut de page</a>
</nav>
<form action="/abonnement" method="post">
  <label>Abonnez-vous à notre newsletter</label><input type="email" name="email"><button>OK</button>
</form>
</body></html>"""

PAGES = {
    "/": (200, "text/html; charset=utf-8", ACCUEIL),
    "/robots.txt": (200, "text/plain", "User-agent: *\nDisallow: /secret\n"),
    "/vie-privee": (200, "text/html", "<title>Vie privée</title><h1>Protection des données</h1>"),
    "/cookies": (200, "text/html", "<title>Cookies</title>"),
    "/cgv.pdf": (200, "application/pdf", "%PDF-1.4 faux"),
    "/conditions-utilisation": (200, "text/html", "<title>Conditions</title>"),
    "/contact": (200, "text/html", "<title>Contact</title><form><input type=text name=nom></form>"),
    "/secret": (200, "text/html", "<title>Espace client</title>"),
    "/blog": (200, "text/html",
              "<title>Blog</title><form><input type=text name=u><input type=password name=p></form>"),
}


class _Gestionnaire(BaseHTTPRequestHandler):
    visites: list[str] = []
    agents: set[str] = set()

    def do_GET(self):  # noqa: N802 (nom imposé par http.server)
        chemin = self.path.split("?")[0]
        _Gestionnaire.visites.append(chemin)
        _Gestionnaire.agents.add(self.headers.get("User-Agent", ""))
        statut, type_contenu, corps = PAGES.get(chemin, (404, "text/html", "<title>Introuvable</title>"))
        donnees = corps.encode("utf-8")
        self.send_response(statut)
        self.send_header("Content-Type", type_contenu)
        self.send_header("Content-Length", str(len(donnees)))
        self.end_headers()
        self.wfile.write(donnees)

    def do_POST(self):  # noqa: N802
        _Gestionnaire.visites.append(f"POST {self.path}")
        self.send_response(405)
        self.end_headers()

    def log_message(self, *args):
        pass


class ScannerCartographieTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.serveur = ThreadingHTTPServer(("127.0.0.1", 0), _Gestionnaire)
        cls.url = f"http://127.0.0.1:{cls.serveur.server_address[1]}/"
        threading.Thread(target=cls.serveur.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.serveur.shutdown()
        cls.serveur.server_close()

    def setUp(self):
        _Gestionnaire.visites = []
        _Gestionnaire.agents = set()

    def scanner(self, **options):
        options.setdefault("delai", 0)
        options.setdefault("user_agent", "APDPVP-Test/1.0")
        resultat = scanner_cartographie(self.url, **options)
        return resultat, {p["type_page"]: p for p in resultat["pages"]}

    def test_identifie_les_pages_attendues(self):
        resultat, pages = self.scanner()

        self.assertEqual(len(pages), 13)  # un résultat par type de PageIdentifiee
        self.assertTrue(pages["accueil"]["presente"])
        self.assertTrue(pages["confidentialite"]["presente"])
        self.assertTrue(pages["confidentialite"]["url"].endswith("/vie-privee"))
        self.assertTrue(pages["cookies"]["url"].endswith("/cookies"))  # fragment retiré
        self.assertTrue(pages["cgv"]["presente"])                       # PDF accepté
        self.assertTrue(pages["cgu"]["url"].endswith("/conditions-utilisation"))
        self.assertTrue(pages["contact"]["presente"])

    def test_cgv_ne_sont_pas_prises_pour_des_cgu(self):
        _, pages = self.scanner()
        self.assertNotIn("cgv", pages["cgu"]["url"])

    def test_formulaires_reperes_sans_etre_soumis(self):
        _, pages = self.scanner()
        self.assertTrue(pages["newsletter"]["presente"])
        self.assertIn("abonnement", pages["newsletter"]["indice"])
        self.assertTrue(pages["connexion"]["url"].endswith("/blog"))
        self.assertFalse(any(v.startswith("POST") for v in _Gestionnaire.visites))

    def test_page_en_erreur_et_page_absente(self):
        _, pages = self.scanner()
        self.assertFalse(pages["mentions_legales"]["presente"])
        self.assertIn("inaccessible", pages["mentions_legales"]["indice"])
        self.assertFalse(pages["inscription"]["presente"])
        self.assertEqual(pages["inscription"]["url"], "")

    def test_robots_txt_respecte(self):
        resultat, pages = self.scanner()
        self.assertNotIn("/secret", _Gestionnaire.visites)
        self.assertTrue(any(u.endswith("/secret") for u in resultat["bloquees_par_robots"]))
        self.assertIsNone(pages["espace_client"]["presente"])

    def test_robots_txt_peut_etre_ignore_sur_decision(self):
        _, pages = self.scanner(respecter_robots=False)
        self.assertIn("/secret", _Gestionnaire.visites)
        self.assertTrue(pages["espace_client"]["presente"])

    def test_non_intrusif(self):
        resultat, _ = self.scanner()
        # Profondeur 1 : aucune page qui n'est pas liée depuis l'accueil.
        autorisees = {"/", "/robots.txt", "/vie-privee", "/cookies", "/cgv.pdf", "/conditions-utilisation",
                      "/mentions", "/contact", "/blog"}
        self.assertLessEqual(set(_Gestionnaire.visites), autorisees)
        self.assertEqual(len(_Gestionnaire.visites), len(set(_Gestionnaire.visites)))  # une visite par page
        self.assertEqual(_Gestionnaire.agents, {"APDPVP-Test/1.0"})
        self.assertEqual(resultat["pages_visitees"], 8)

    def test_limite_de_pages(self):
        resultat, pages = self.scanner(max_pages=3)
        self.assertEqual(resultat["pages_visitees"], 3)
        non_verifiees = [p for p in pages.values() if p["presente"] is None]
        self.assertTrue(non_verifiees)
        self.assertTrue(all("non visitée" in p["indice"] for p in non_verifiees))

    def test_accueil_inaccessible_leve_une_erreur(self):
        with self.assertRaises(Exception):
            scanner_cartographie("http://127.0.0.1:9/", delai=0)


class ClassementTests(TestCase):
    def test_motifs(self):
        cas = {
            "Politique de protection des données personnelles": "confidentialite",
            "Privacy policy": "confidentialite",
            "Mentions-légales": "mentions_legales",
            "Conditions générales d'utilisation": "cgu",
            "Terms of Service": "cgu",
            "Créer un compte": "inscription",
            "Se connecter": "connexion",
            "Votre panier": "commande",
        }
        for texte, attendu in cas.items():
            with self.subTest(texte=texte):
                self.assertIn(attendu, _types_correspondants(texte))

    def test_conditions_generales_de_vente(self):
        self.assertEqual(_types_correspondants("Conditions générales de vente"), ["cgv"])

    def test_texte_neutre(self):
        self.assertEqual(_types_correspondants("Nos actualités"), [])
