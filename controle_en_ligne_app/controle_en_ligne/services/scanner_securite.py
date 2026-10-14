"""
Scan de sécurité observable (guide §8, Bloc H de GRILLE_CONTROLE.md).

100% automatisable via requests + ssl : aucune tentative d'authentification,
aucune exploitation de faille, aucun accès à autre chose que ce qu'un
visiteur public normal peut voir (principe "non-intrusif", cf. CLAUDE.md).

CHEMINS_LISTE_BLANCHE est une liste FERMÉE de chemins publics/courants
utilisée pour repérer une exposition accidentelle (fichier de config oublié,
.git exposé, etc). Elle ne doit JAMAIS être transformée en bruteforce de
répertoires ni étendue dynamiquement à partir d'un wordlist.

Ce module ne renseigne que des FAITS OBSERVÉS bruts. Il ne doit jamais
écrire `conformite` ou `criticite` : ces deux axes indépendants (Qualifiable,
models.py) relèvent exclusivement de la validation humaine.
"""

from __future__ import annotations

import socket
import ssl
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests

# Liste fermée (guide §8). Ne jamais transformer en bruteforce de répertoires.
# En service, la liste vient du modèle CheminListeBlanche (éditable dans
# l'admin, plafonnée) ; ce tuple sert de valeur par défaut et a amorcé la base.
CHEMINS_LISTE_BLANCHE: tuple[str, ...] = (
    "/robots.txt",
    "/sitemap.xml",
    "/.well-known/security.txt",
    "/.git/config",
    "/.env",
    "/.env.local",
    "/wp-config.php.bak",
    "/backup.zip",
    "/backup.sql",
    "/phpinfo.php",
    "/.DS_Store",
    "/config.json",
    "/swagger.json",
    "/swagger-ui.html",
    "/admin",
    "/administrator",
    "/server-status",
    "/.htaccess",
)

TIMEOUT_SECONDES = 10
USER_AGENT_PAR_DEFAUT = "APDPVP-ControleEnLigne/1.0 (controle en ligne)"

EN_TETES_SECURITE_SURVEILLES = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
]

# Fragments de nom de cookie évoquant une session (heuristique, pas exhaustif).
FRAGMENTS_NOM_COOKIE_SESSION = ["sess", "sid", "auth", "token"]


def scanner_securite(
    url_principale: str,
    user_agent: str = USER_AGENT_PAR_DEFAUT,
    chemins: tuple[str, ...] = CHEMINS_LISTE_BLANCHE,
) -> dict:
    """
    Point d'entrée du scan. Retourne un dict dont les clés correspondent
    directement aux champs de ConstatSecurite (models.py) — jamais
    conformite/criticite, qui restent du ressort de l'agent.
    """
    resultats = {
        "https_complet": None,
        "redirection_http_https": None,
        "certificat_valide": None,
        "certificat_expiration": None,
        "en_tetes_securite": {},
        "fichiers_exposes": [],
        "cookie_session_secure_httponly": None,
    }

    parsed = urlparse(url_principale)
    domaine = parsed.hostname
    if not domaine:
        return resultats

    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})

    resultats["https_complet"] = parsed.scheme == "https"
    resultats["redirection_http_https"] = _verifier_redirection(session, domaine)

    cert_info = _verifier_certificat(domaine)
    resultats["certificat_valide"] = cert_info["valide"]
    resultats["certificat_expiration"] = cert_info["expiration"]

    try:
        reponse = session.get(url_principale, timeout=TIMEOUT_SECONDES, allow_redirects=True)
        resultats["en_tetes_securite"] = _extraire_en_tetes_securite(reponse.headers)
        resultats["cookie_session_secure_httponly"] = _verifier_cookies_session(reponse)
    except requests.RequestException:
        pass

    resultats["fichiers_exposes"] = _verifier_chemins_liste_blanche(session, url_principale, chemins)

    return resultats


def _verifier_redirection(session: requests.Session, domaine: str) -> bool | None:
    """Un GET simple sur la version http:// suffit ; aucune interaction supplémentaire."""
    url_http = f"http://{domaine}/"
    try:
        reponse = session.get(url_http, timeout=TIMEOUT_SECONDES, allow_redirects=True)
    except requests.RequestException:
        return None
    return reponse.url.startswith("https://")


def _verifier_certificat(domaine: str) -> dict:
    contexte = ssl.create_default_context()
    try:
        with socket.create_connection((domaine, 443), timeout=TIMEOUT_SECONDES) as sock:
            with contexte.wrap_socket(sock, server_hostname=domaine) as ssl_sock:
                cert = ssl_sock.getpeercert()
        expiration = None
        expiration_str = cert.get("notAfter") if cert else None
        if expiration_str:
            expiration = datetime.strptime(str(expiration_str), "%b %d %H:%M:%S %Y %Z").date()
        return {"valide": True, "expiration": expiration}
    except ssl.SSLCertVerificationError:
        return {"valide": False, "expiration": None}
    except (socket.timeout, socket.gaierror, ConnectionRefusedError, OSError):
        # Impossible de se connecter / de vérifier : on ne conclut rien,
        # l'agent tranchera (pas de qualification depuis un scan auto).
        return {"valide": None, "expiration": None}


def _extraire_en_tetes_securite(en_tetes) -> dict:
    return {nom: en_tetes.get(nom) for nom in EN_TETES_SECURITE_SURVEILLES if nom in en_tetes}


def _verifier_cookies_session(reponse: requests.Response) -> bool | None:
    """
    Inspecte les en-têtes Set-Cookie bruts : les attributs Secure/HttpOnly ne
    sont pas fiablement exposés par l'API cookies de haut niveau de requests.
    """
    try:
        entetes_brutes = reponse.raw.headers.getlist("Set-Cookie")
    except AttributeError:
        valeur = reponse.headers.get("Set-Cookie", "")
        entetes_brutes = [valeur] if valeur else []

    cookies_session = [
        entete for entete in entetes_brutes
        if any(fragment in entete.split("=", 1)[0].lower() for fragment in FRAGMENTS_NOM_COOKIE_SESSION)
    ]
    if not cookies_session:
        return None

    return all("secure" in entete.lower() and "httponly" in entete.lower() for entete in cookies_session)


def _verifier_chemins_liste_blanche(
    session: requests.Session, url_principale: str, chemins: tuple[str, ...],
) -> list[str]:
    """Un GET par chemin de la liste fermée, sans suivre de logique de découverte."""
    exposes = []
    for chemin in chemins:
        url_test = urljoin(url_principale, chemin)
        try:
            reponse = session.get(url_test, timeout=TIMEOUT_SECONDES, allow_redirects=False)
            if reponse.status_code == 200:
                exposes.append(chemin)
        except requests.RequestException:
            continue
    return exposes