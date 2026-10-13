"""
Scanner securite — EMPLACEMENT À REMPLACER.

La version opérationnelle de ce module existe sur le poste de développement
mais n'a pas encore été versionnée. Copier ici le fichier réel.
Tant que ce module n'est pas remplacé, l'orchestration consigne l'échec du
scan « securite » dans mission.erreurs_scan et poursuit les autres scans.

Contrat attendu par tasks.py :
    scanner_securite(url) -> dict des champs de ConstatSecurite :
    {"https_complet": bool, "redirection_http_https": bool, "certificat_valide": bool,
     "certificat_expiration": date | None, "en_tetes_securite": dict,
     "fichiers_exposes": list[str], "cookie_session_secure_httponly": bool, ...}
    Les chemins testés viennent de CHEMINS_LISTE_BLANCHE, liste fermée.
"""

# Liste FERMÉE (CLAUDE.md, principe 1) : ne jamais la transformer en exploration de répertoires.
CHEMINS_LISTE_BLANCHE: tuple[str, ...] = ()


def scanner_securite(url: str, *args, **kwargs):
    raise NotImplementedError(
        "scanner_securite n'est pas encore versionné dans ce service : "
        "copier la version opérationnelle dans controle_en_ligne/services/scanner_securite.py."
    )
