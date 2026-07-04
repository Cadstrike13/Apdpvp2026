from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class ValidateurTailleFichier:
    """Rejette un fichier dépassant `max_mo` mégaoctets."""

    def __init__(self, max_mo):
        self.max_mo = max_mo

    def __call__(self, fichier):
        limite = self.max_mo * 1024 * 1024
        if fichier.size > limite:
            raise ValidationError(f"Fichier trop volumineux (max {self.max_mo} Mo).")

    def __eq__(self, other):
        return isinstance(other, ValidateurTailleFichier) and self.max_mo == other.max_mo
