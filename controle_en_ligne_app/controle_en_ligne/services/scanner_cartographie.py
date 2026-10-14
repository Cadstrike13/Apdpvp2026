"""
Phase 1 — Cartographie (bloc PageIdentifiee).

Repère, à partir de la page d'accueil, les pages utiles au contrôle :
politique de confidentialité, page cookies, mentions légales, CGU, CGV,
contact, inscription, connexion, espace client, commande, paiement,
newsletter.

Principe de non-intrusion (CLAUDE.md, principe 1) :
- uniquement des requêtes GET sur des liens publiés par le site lui-même ;
- profondeur 1 : la page d'accueil et les liens qu'elle contient, rien de plus ;
- même domaine seulement (sous-domaines compris, www ignoré) ;
- 40 pages au plus, une pause entre deux requêtes, robots.txt respecté
  par défaut, User-Agent qui identifie l'APDPVP ;
- aucun formulaire soumis, aucune URL devinée ou construite.

Minimisation : seuls les URL, titres et indices d'identification sont
renvoyés ; le contenu des pages n'est pas conservé.

Contrat de retour (consommé par tasks._scanner_cartographie_task) :
{
  "url_depart": str, "url_finale": str, "pages_visitees": int,
  "pages": [{"type_page", "url", "presente", "indice"}, ...],  # un par type
  "bloquees_par_robots": [url, ...],
  "erreurs": [{"url", "erreur"}, ...],
  "certificat_non_verifie": bool,
}
"""

from __future__ import annotations

import logging
import re
import time
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

PROFONDEUR = 1
MAX_PAGES = 40
DELAI_ENTRE_REQUETES = 0.5   # secondes
DELAI_REPONSE = 10           # secondes
TAILLE_MAX_PAGE = 2 * 1024 * 1024  # on ne lit pas plus de 2 Mo par page

USER_AGENT_PAR_DEFAUT = "APDPVP-ControleEnLigne/1.0 (controle en ligne)"

# Types dans l'ordre de PageIdentifiee.TYPES.
TYPES_PAGE = [
    "accueil", "inscription", "connexion", "commande", "paiement", "contact",
    "newsletter", "espace_client", "cookies", "confidentialite",
    "mentions_legales", "cgu", "cgv",
]

# Motifs recherchés dans le texte du lien, son URL et le titre de la page,
# après passage en minuscules sans accents. Les CGV passent avant les CGU :
# « conditions générales de vente » ne doit pas être pris pour des CGU.
MOTIFS: dict[str, list[str]] = {
    "cgv": [
        r"\bcgv\b", r"conditions? generales? de vente", r"conditions-generales-de-vente",
        r"conditions de vente", r"terms (of|and conditions of) sale",
    ],
    "cgu": [
        r"\bcgu\b", r"conditions? generales? d.?utilisation", r"conditions-generales-d?-?utilisation",
        r"conditions d.?utilisation", r"terms (of use|of service|and conditions)", r"\btos\b",
    ],
    "confidentialite": [
        r"confidentialite", r"vie[ -]privee", r"donnees[ -]personnelles", r"protection des donnees",
        r"privacy", r"\brgpd\b", r"\bgdpr\b", r"\bdpo\b",
    ],
    "cookies": [r"cookie", r"traceurs?\b"],
    "mentions_legales": [r"mentions?[ -]legales?", r"legal[ -]notice", r"\bimprint\b", r"informations legales"],
    "contact": [r"\bcontact", r"nous[ -]ecrire", r"contactez"],
    "inscription": [
        r"inscription", r"s.?inscrire", r"creer[ -](un|mon)[ -]compte", r"\bregister\b",
        r"sign[ -]?up", r"ouvrir un compte",
    ],
    "connexion": [r"\bconnexion\b", r"se connecter", r"\blogin\b", r"\blog[ -]?in\b", r"sign[ -]?in", r"identifiez"],
    "espace_client": [r"mon[ -]compte", r"espace[ -](client|personnel|membre)", r"my[ -]account", r"\bprofil\b"],
    "commande": [r"\bpanier\b", r"\bcart\b", r"\bbasket\b", r"\bcommande", r"\bcheckout\b", r"\border\b"],
    "paiement": [r"paiement", r"\bpayment\b", r"\bpayer\b", r"\bpay\b"],
    "newsletter": [r"newsletter", r"lettre d.?information", r"abonnez", r"\bsubscribe\b"],
}
_MOTIFS_COMPILES = {t: [re.compile(m) for m in motifs] for t, motifs in MOTIFS.items()}

_SCHEMES_IGNORES = ("mailto:", "tel:", "javascript:", "data:", "sms:", "whatsapp:")


@dataclass
class _Candidat:
    url: str
    indice: str
    confirme: bool | None = None  # None = pas encore visité


@dataclass
class _Etat:
    url_depart: str
    url_finale: str = ""
    pages_visitees: int = 0
    candidats: dict[str, list[_Candidat]] = field(default_factory=dict)
    bloquees_par_robots: list[str] = field(default_factory=list)
    erreurs: list[dict] = field(default_factory=list)
    certificat_non_verifie: bool = False


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def scanner_cartographie(
    url: str,
    *,
    user_agent: str = USER_AGENT_PAR_DEFAUT,
    respecter_robots: bool = True,
    max_pages: int = MAX_PAGES,
    delai: float = DELAI_ENTRE_REQUETES,
    session: requests.Session | None = None,
) -> dict:
    """
    Parcourt la page d'accueil et ses liens directs (profondeur 1).
    Lève une exception si la page d'accueil elle-même est inaccessible :
    l'orchestration consigne alors l'échec du scan.
    """
    session = session or requests.Session()
    session.headers.update({"User-Agent": user_agent, "Accept-Language": "fr,en;q=0.8"})
    etat = _Etat(url_depart=url)

    robots = _charger_robots(session, url, user_agent) if respecter_robots else None

    # 1. Page d'accueil (toujours visitée : c'est le point d'entrée du contrôle).
    reponse = _get(session, url, etat)
    etat.pages_visitees += 1
    if reponse is None:
        raise ConnectionError(f"Page d'accueil inaccessible : {etat.erreurs[-1]['erreur']}")
    reponse.raise_for_status()
    etat.url_finale = reponse.url
    hote = _hote_de_base(reponse.url)

    soupe = _soupe(reponse)
    _ajouter(etat, "accueil", reponse.url, "Page de départ", confirme=True)
    if soupe is not None:
        _classer_formulaires(etat, soupe, reponse.url)

    # 2. Liens de la page d'accueil, même domaine, classés par motifs.
    liens = _liens_internes(soupe, reponse.url, hote) if soupe is not None else []
    for lien_url, texte in liens:
        for type_page in _types_correspondants(f"{texte} {urlsplit(lien_url).path}"):
            _ajouter(etat, type_page, lien_url, f"Lien « {texte[:80]} »" if texte else "Adresse du lien")

    # 3. Visite (profondeur 1) : les liens candidats d'abord, puis les autres.
    urls_candidates = list(dict.fromkeys(
        c.url for liste in etat.candidats.values() for c in liste if c.confirme is None
    ))
    autres = [u for u, _ in liens if u not in set(urls_candidates)]
    deja_vues = {_cle(reponse.url), _cle(url)}

    for lien_url in urls_candidates + autres:
        if etat.pages_visitees >= max_pages:
            break
        if _cle(lien_url) in deja_vues:
            _confirmer(etat, lien_url, True)
            continue
        deja_vues.add(_cle(lien_url))
        if robots is not None and not robots.can_fetch(user_agent, lien_url):
            etat.bloquees_par_robots.append(lien_url)
            continue

        if delai:
            time.sleep(delai)
        page = _get(session, lien_url, etat)
        etat.pages_visitees += 1
        if page is None:
            _confirmer(etat, lien_url, False)
            continue
        accessible = page.status_code < 400
        _confirmer(etat, lien_url, accessible)
        if not accessible:
            continue

        page_soupe = _soupe(page)
        if page_soupe is None:
            continue  # PDF, image… : la présence suffit, rien à analyser
        titre = _titre(page_soupe)
        for type_page in _types_correspondants(titre):
            _ajouter(etat, type_page, page.url, f"Titre « {titre[:80]} »", confirme=True)
        _classer_formulaires(etat, page_soupe, page.url)

    return _resultat(etat)


# ---------------------------------------------------------------------------
# Réseau
# ---------------------------------------------------------------------------

def _get(session: requests.Session, url: str, etat: _Etat) -> requests.Response | None:
    """GET plafonné en taille ; un certificat invalide n'empêche pas la cartographie
    (il est relevé par le scan sécurité) mais il est signalé."""
    for verifier in (True, False):
        try:
            reponse = session.get(
                url, timeout=DELAI_REPONSE, allow_redirects=True, stream=True, verify=verifier,
            )
            contenu = reponse.raw.read(TAILLE_MAX_PAGE, decode_content=True)
            reponse._content = contenu
            reponse.close()
            if not verifier:
                etat.certificat_non_verifie = True
            return reponse
        except requests.exceptions.SSLError as exc:
            if not verifier:
                etat.erreurs.append({"url": url, "erreur": f"SSLError: {exc}"[:300]})
                return None
            continue
        except requests.RequestException as exc:
            etat.erreurs.append({"url": url, "erreur": f"{type(exc).__name__}: {exc}"[:300]})
            return None
    return None


def _charger_robots(session: requests.Session, url: str, user_agent: str) -> RobotFileParser | None:
    parties = urlsplit(url)
    robots_url = f"{parties.scheme}://{parties.netloc}/robots.txt"
    analyseur = RobotFileParser(robots_url)
    try:
        reponse = session.get(robots_url, timeout=DELAI_REPONSE)
    except requests.RequestException:
        return None  # pas de robots.txt lisible : aucune restriction déclarée
    if reponse.status_code >= 400:
        return None
    analyseur.parse(reponse.text.splitlines())
    return analyseur


# ---------------------------------------------------------------------------
# Analyse HTML
# ---------------------------------------------------------------------------

def _soupe(reponse: requests.Response) -> BeautifulSoup | None:
    type_contenu = reponse.headers.get("Content-Type", "")
    if "html" not in type_contenu:
        return None
    return BeautifulSoup(reponse.content, "html.parser")


def _titre(soupe: BeautifulSoup) -> str:
    morceaux = []
    if soupe.title and soupe.title.string:
        morceaux.append(soupe.title.string)
    h1 = soupe.find("h1")
    if h1:
        morceaux.append(h1.get_text(" ", strip=True))
    return " — ".join(m.strip() for m in morceaux if m and m.strip())


def _liens_internes(soupe: BeautifulSoup, base: str, hote: str) -> list[tuple[str, str]]:
    liens: dict[str, str] = {}
    for balise in soupe.find_all("a", href=True):
        href = balise["href"].strip()
        if not href or href.startswith("#") or href.lower().startswith(_SCHEMES_IGNORES):
            continue
        absolue, _ = urldefrag(urljoin(base, href))
        parties = urlsplit(absolue)
        if parties.scheme not in ("http", "https") or _hote_de_base(absolue) != hote:
            continue
        texte = " ".join(
            filter(None, [balise.get_text(" ", strip=True), balise.get("title", ""), balise.get("aria-label", "")])
        )
        liens.setdefault(absolue, texte)
    return list(liens.items())


def _classer_formulaires(etat: _Etat, soupe: BeautifulSoup, url: str) -> None:
    """Repère connexion, inscription et newsletter par la forme des formulaires
    (sans jamais les soumettre)."""
    for formulaire in soupe.find_all("form"):
        mots_de_passe = formulaire.find_all("input", attrs={"type": "password"})
        texte = _normaliser(formulaire.get_text(" ", strip=True))
        if len(mots_de_passe) >= 2:
            _ajouter(etat, "inscription", url, "Formulaire avec confirmation de mot de passe", confirme=True)
        elif len(mots_de_passe) == 1:
            _ajouter(etat, "connexion", url, "Formulaire avec mot de passe", confirme=True)
        elif formulaire.find("input", attrs={"type": "email"}) and any(
            m.search(texte) for m in _MOTIFS_COMPILES["newsletter"]
        ):
            _ajouter(etat, "newsletter", url, "Formulaire d'abonnement par e-mail", confirme=True)


# ---------------------------------------------------------------------------
# Classement
# ---------------------------------------------------------------------------

def _normaliser(texte: str) -> str:
    sans_accents = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode()
    return re.sub(r"[\s_/]+", " ", sans_accents.lower().replace("-", " ")).strip()


def _types_correspondants(texte: str) -> list[str]:
    normalise = _normaliser(texte)
    trouves = [t for t, motifs in _MOTIFS_COMPILES.items() if any(m.search(normalise) for m in motifs)]
    # « Conditions générales de vente » contient aussi « conditions générales » :
    # quand les CGV sont reconnues, on n'en déduit pas des CGU.
    if "cgv" in trouves and "cgu" in trouves and not re.search(r"\bcgu\b|utilisation|terms of (use|service)", normalise):
        trouves.remove("cgu")
    return trouves


def _ajouter(etat: _Etat, type_page: str, url: str, indice: str, confirme: bool | None = None) -> None:
    liste = etat.candidats.setdefault(type_page, [])
    for candidat in liste:
        if _cle(candidat.url) == _cle(url):
            if confirme is not None:
                candidat.confirme = confirme
            return
    liste.append(_Candidat(url=url, indice=indice, confirme=confirme))


def _confirmer(etat: _Etat, url: str, accessible: bool) -> None:
    for liste in etat.candidats.values():
        for candidat in liste:
            if _cle(candidat.url) == _cle(url) and candidat.confirme is None:
                candidat.confirme = accessible


def _resultat(etat: _Etat) -> dict:
    pages = []
    for type_page in TYPES_PAGE:
        candidats = etat.candidats.get(type_page, [])
        retenu = next((c for c in candidats if c.confirme), None)
        if retenu is not None:
            pages.append({"type_page": type_page, "url": retenu.url, "presente": True, "indice": retenu.indice})
            continue
        en_erreur = next((c for c in candidats if c.confirme is False), None)
        non_visite = next((c for c in candidats if c.confirme is None), None)
        if en_erreur is not None:
            indice = f"{en_erreur.indice} — lien présent mais page inaccessible"
            pages.append({"type_page": type_page, "url": en_erreur.url, "presente": False, "indice": indice})
        elif non_visite is not None:
            indice = f"{non_visite.indice} — lien présent, page non visitée (limite ou robots.txt)"
            pages.append({"type_page": type_page, "url": non_visite.url, "presente": None, "indice": indice})
        else:
            pages.append({"type_page": type_page, "url": "", "presente": False,
                          "indice": "Aucun lien ni formulaire correspondant trouvé"})
    return {
        "url_depart": etat.url_depart,
        "url_finale": etat.url_finale,
        "pages_visitees": etat.pages_visitees,
        "pages": pages,
        "bloquees_par_robots": etat.bloquees_par_robots,
        "erreurs": etat.erreurs,
        "certificat_non_verifie": etat.certificat_non_verifie,
    }


# ---------------------------------------------------------------------------
# URL
# ---------------------------------------------------------------------------

def _hote_de_base(url: str) -> str:
    hote = (urlsplit(url).hostname or "").lower()
    return hote[4:] if hote.startswith("www.") else hote


def _cle(url: str) -> str:
    """Clé de comparaison : sans fragment, sans / final, hôte sans www."""
    parties = urlsplit(urldefrag(url)[0])
    chemin = parties.path.rstrip("/") or "/"
    requete = f"?{parties.query}" if parties.query else ""
    return f"{_hote_de_base(url)}{chemin}{requete}"
