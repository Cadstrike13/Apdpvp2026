"""
Scan des services tiers appelés par le site (guide §11, Bloc K de
GRILLE_CONTROLE.md).

Playwright, interception réseau passive : on observe les requêtes émises
pendant un chargement normal de la page, on ne déclenche aucune action qui
irait au-delà d'une navigation publique standard.

Chaque domaine tiers détecté est catégorisé par correspondance de mots-clés
sur une liste connue (heuristique, non exhaustive — l'agent complète/corrige
en Bloc K02 par croisement manuel avec la politique de confidentialité).

Ce module ne se prononce jamais sur `declare_dans_politique` : c'est un
croisement manuel (K02), pas un fait détectable par un scan réseau.
"""

from __future__ import annotations

from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

TIMEOUT_MS = 20000

# Correspondance domaine (fragment) -> catégorie (choix de ConstatTiers.CATEGORIES).
# Liste indicative : à enrichir au fil des contrôles, jamais un motif d'aller
# chercher au-delà de ce qu'un chargement de page normal révèle.
CATEGORIES_DOMAINES = {
    "google-analytics.com": "analytics",
    "googletagmanager.com": "analytics",
    "analytics.google.com": "analytics",
    "matomo": "analytics",
    "hotjar.com": "analytics",
    "mixpanel.com": "analytics",
    "segment.com": "analytics",
    "amplitude.com": "analytics",

    "doubleclick.net": "publicite",
    "googlesyndication.com": "publicite",
    "googleadservices.com": "publicite",
    "adnxs.com": "publicite",
    "criteo.com": "publicite",
    "taboola.com": "publicite",
    "outbrain.com": "publicite",

    "youtube.com": "video",
    "vimeo.com": "video",
    "dailymotion.com": "video",
    "player.twitch.tv": "video",

    "maps.google": "carte",
    "maps.googleapis.com": "carte",
    "openstreetmap.org": "carte",
    "mapbox.com": "carte",

    "stripe.com": "paiement",
    "paypal.com": "paiement",
    "paypalobjects.com": "paiement",
    "adyen.com": "paiement",
    "mangopay.com": "paiement",

    "intercom.io": "support",
    "zendesk.com": "support",
    "crisp.chat": "support",
    "livechatinc.com": "support",
    "tawk.to": "support",

    "mailchimp.com": "marketing",
    "hubspot.com": "marketing",
    "sendinblue.com": "marketing",
    "brevo.com": "marketing",
    "klaviyo.com": "marketing",

    "facebook.net": "reseau_social",
    "facebook.com": "reseau_social",
    "connect.facebook.net": "reseau_social",
    "twitter.com": "reseau_social",
    "x.com": "reseau_social",
    "linkedin.com": "reseau_social",
    "tiktok.com": "reseau_social",
    "instagram.com": "reseau_social",

    "gstatic.com": "autre",
    "cloudflare.com": "autre",
    "jsdelivr.net": "autre",
    "cdnjs.cloudflare.com": "autre",
}


def scanner_tiers(url_principale: str, headless: bool = True, ralenti_ms: int = 0) -> list[dict]:
    """
    Point d'entrée. Retourne une liste de {"domaine_tiers": str, "categorie": str},
    dédupliquée par domaine.
    """
    domaine_principal = urlparse(url_principale).hostname or ""
    domaines_observes: set[str] = set()

    def sur_requete(requete):
        domaine = urlparse(requete.url).hostname
        if domaine and not _meme_site(domaine, domaine_principal):
            domaines_observes.add(domaine)

    with sync_playwright() as p:
        # channel="chromium" : navigateur complet, visible si headless=False, et
        # utilisable en headless sans le chromium-headless-shell de Playwright.
        navigateur = p.chromium.launch(headless=headless, channel="chromium", slow_mo=ralenti_ms)
        contexte = navigateur.new_context()
        page = contexte.new_page()
        page.on("request", sur_requete)

        try:
            page.goto(url_principale, timeout=TIMEOUT_MS, wait_until="networkidle")
        except PlaywrightTimeoutError:
            # Certains sites gardent des connexions ouvertes en continu
            # (websockets de tracking...) : on garde ce qui a été observé.
            pass

        contexte.close()
        navigateur.close()

    return [
        {"domaine_tiers": domaine, "categorie": _categoriser(domaine)}
        for domaine in sorted(domaines_observes)
    ]


def _meme_site(domaine: str, domaine_principal: str) -> bool:
    if not domaine or not domaine_principal:
        return False
    return domaine == domaine_principal or domaine.endswith("." + domaine_principal)


def _categoriser(domaine: str) -> str:
    for fragment, categorie in CATEGORIES_DOMAINES.items():
        if fragment in domaine:
            return categorie
    return "autre"