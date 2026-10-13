"""
Scan cookies et traceurs (guide §4, Bloc D de GRILLE_CONTROLE.md).

Playwright, 4 scénarios comparés : avant interaction / après acceptation /
après refus / après modification du choix. Ne PAS fusionner ces 4 relevés en
un seul enregistrement par cookie — c'est la base de la comparaison exigée
par le guide (cf. erreur listée dans CLAUDE.md).

Principe non-intrusif : le script clique uniquement sur des éléments visibles
et destinés au public (bandeau de consentement), ne remplit aucun compte réel,
ne contourne aucune authentification.

Ce module ne renseigne QUE des faits bruts (nom / domaine / est_tiers, etc.),
jamais de conformite/criticite.
"""

from __future__ import annotations

from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

TIMEOUT_MS = 8000
DELAI_APRES_CLIC_MS = 1500

# Heuristiques de détection des boutons de bandeau CMP. Volontairement large
# (fr/en) mais limité à des libellés publics standards — pas de contournement,
# juste de la reconnaissance de texte visible.
LIBELLES_ACCEPTATION = [
    "tout accepter", "accepter tout", "j'accepte", "accepter", "accept all",
    "accept", "i agree", "agree", "allow all", "autoriser tout",
]
LIBELLES_REFUS = [
    "tout refuser", "refuser tout", "je refuse", "refuser", "continuer sans accepter",
    "decline all", "reject all", "reject", "decline", "refuse",
]
LIBELLES_PARAMETRES = [
    "paramétrer", "paramètres", "personnaliser", "gérer mes choix", "gérer les cookies",
    "cookie settings", "manage cookies", "preferences", "préférences", "customize",
]


def scanner_cookies(url_principale: str, headless: bool = True, ralenti_ms: int = 0) -> dict:
    """
    Point d'entrée. Retourne :
    {
        "avant": [{"nom": ..., "domaine": ..., "est_tiers": bool, "expires": float}, ...],
        "acceptation": [...],
        "refus": [...],
        "modification": [...],
    }
    Chaque liste peut être vide si le scénario correspondant n'a pas pu être
    déclenché automatiquement (ex : bandeau non standard) — dans ce cas la
    ligne reste à compléter manuellement (méthode "Semi-auto" pour D07/D08,
    l'agent peut aussi ré-enrichir D01-D06 à la main si besoin).
    """
    domaine_principal = urlparse(url_principale).hostname or ""
    resultats = {"avant": [], "acceptation": [], "refus": [], "modification": []}

    with sync_playwright() as p:
        # channel="chromium" : navigateur complet, visible si headless=False, et
        # utilisable en headless sans le chromium-headless-shell de Playwright.
        navigateur = p.chromium.launch(headless=headless, channel="chromium", slow_mo=ralenti_ms)

        # --- Scénario 1 : avant toute interaction --------------------------
        contexte = navigateur.new_context()
        page = contexte.new_page()
        _naviguer(page, url_principale)
        resultats["avant"] = _capturer_cookies(contexte, domaine_principal)
        contexte.close()

        # --- Scénario 2 : après acceptation ---------------------------------
        contexte = navigateur.new_context()
        page = contexte.new_page()
        _naviguer(page, url_principale)
        if _cliquer_sur_libelle(page, LIBELLES_ACCEPTATION):
            page.wait_for_timeout(DELAI_APRES_CLIC_MS)
        resultats["acceptation"] = _capturer_cookies(contexte, domaine_principal)
        contexte.close()

        # --- Scénario 3 : après refus ----------------------------------------
        contexte = navigateur.new_context()
        page = contexte.new_page()
        _naviguer(page, url_principale)
        if _cliquer_sur_libelle(page, LIBELLES_REFUS):
            page.wait_for_timeout(DELAI_APRES_CLIC_MS)
        resultats["refus"] = _capturer_cookies(contexte, domaine_principal)
        contexte.close()

        # --- Scénario 4 : après modification du choix ------------------------
        # On accepte d'abord, puis on rouvre les paramètres pour revenir sur
        # un choix restrictif — reproduit le parcours "je change d'avis".
        contexte = navigateur.new_context()
        page = contexte.new_page()
        _naviguer(page, url_principale)
        _cliquer_sur_libelle(page, LIBELLES_ACCEPTATION)
        page.wait_for_timeout(DELAI_APRES_CLIC_MS)
        if _cliquer_sur_libelle(page, LIBELLES_PARAMETRES):
            page.wait_for_timeout(500)
            _cliquer_sur_libelle(page, LIBELLES_REFUS)
            page.wait_for_timeout(DELAI_APRES_CLIC_MS)
        resultats["modification"] = _capturer_cookies(contexte, domaine_principal)
        contexte.close()

        navigateur.close()

    return resultats


def _naviguer(page, url: str) -> None:
    try:
        page.goto(url, timeout=TIMEOUT_MS * 2, wait_until="networkidle")
    except PlaywrightTimeoutError:
        # Le chargement réseau ne se stabilise pas toujours (traceurs en
        # boucle) : on continue avec ce qui a pu être capturé.
        pass


def _cliquer_sur_libelle(page, libelles: list[str]) -> bool:
    """
    Cherche un élément cliquable visible dont le texte correspond à l'un des
    libellés donnés (bouton/lien standard de bandeau CMP). Retourne True si
    un clic a eu lieu.
    """
    for libelle in libelles:
        try:
            localisateur = page.get_by_role("button", name=libelle, exact=False).first
            if localisateur.is_visible(timeout=500):
                localisateur.click(timeout=TIMEOUT_MS)
                return True
        except Exception:
            continue
    return False


def _capturer_cookies(contexte, domaine_principal: str) -> list[dict]:
    cookies = contexte.cookies()
    resultat = []
    for cookie in cookies:
        domaine_cookie = cookie.get("domain", "").lstrip(".")
        resultat.append({
            "nom": cookie.get("name", ""),
            "domaine": domaine_cookie,
            "est_tiers": _est_domaine_tiers(domaine_cookie, domaine_principal),
            # Horodatage Unix d'expiration ; -1 pour un cookie de session.
            "expires": cookie.get("expires", -1),
        })
    return resultat


def _est_domaine_tiers(domaine_cookie: str, domaine_principal: str) -> bool:
    if not domaine_cookie or not domaine_principal:
        return False
    return not (domaine_cookie == domaine_principal or domaine_cookie.endswith("." + domaine_principal))