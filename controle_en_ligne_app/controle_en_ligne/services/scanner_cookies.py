"""
Scanner cookies — EMPLACEMENT À REMPLACER.

La version opérationnelle de ce module existe sur le poste de développement
mais n'a pas encore été versionnée. Copier ici le fichier réel.
Tant que ce module n'est pas remplacé, l'orchestration consigne l'échec du
scan « cookies » dans mission.erreurs_scan et poursuit les autres scans.

Contrat attendu par tasks.py :
    scanner_cookies(url, headless=True) -> dict par scénario :
    {"avant": [...], "acceptation": [...], "refus": [...], "modification": [...]}
    chaque entrée : {"nom", "domaine", "est_tiers", "type_traceur"?, "expires"?, "duree_vie_jours"?}
    Un type_traceur inconnu est accepté : l'orchestration le répertorie en « non classé ».
"""


def scanner_cookies(url: str, *args, **kwargs):
    raise NotImplementedError(
        "scanner_cookies n'est pas encore versionné dans ce service : "
        "copier la version opérationnelle dans controle_en_ligne/services/scanner_cookies.py."
    )
