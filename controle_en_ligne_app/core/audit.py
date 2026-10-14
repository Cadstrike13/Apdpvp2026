"""Point d'entrée de la traçabilité, même chemin d'import que dans missions_controle."""

from .models import JournalAction


def journaliser(action: str, objet, *, acteur=None, description: str = "", donnees: dict | None = None):
    """Ajoute une entrée au journal. `objet` est une instance de modèle Django."""
    return JournalAction.objects.create(
        action=action,
        acteur=acteur,
        objet_type=objet._meta.label,
        objet_id=str(objet.pk),
        description=description,
        donnees=donnees or {},
    )


__all__ = ["JournalAction", "journaliser"]
