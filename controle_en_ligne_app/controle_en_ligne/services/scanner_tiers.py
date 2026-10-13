"""
Scanner tiers — EMPLACEMENT À REMPLACER.

La version opérationnelle de ce module existe sur le poste de développement
mais n'a pas encore été versionnée. Copier ici le fichier réel.
Tant que ce module n'est pas remplacé, l'orchestration consigne l'échec du
scan « tiers » dans mission.erreurs_scan et poursuit les autres scans.

Contrat attendu par tasks.py :
    scanner_tiers(url) -> list[{"domaine_tiers": str, "categorie": str}]
    categorie parmi les clés de ConstatTiers.CATEGORIES (sinon rangée en « autre »).
"""


def scanner_tiers(url: str, *args, **kwargs):
    raise NotImplementedError(
        "scanner_tiers n'est pas encore versionné dans ce service : "
        "copier la version opérationnelle dans controle_en_ligne/services/scanner_tiers.py."
    )
