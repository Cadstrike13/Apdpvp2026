"""
Socle minimal du service controle_en_ligne_app.

Dans le projet APDPVP principal (missions_controle), ces modèles vivent dans
son app `core`. Ce service étant déployé à part (un service = une base,
cf. CLAUDE.md racine), il en porte des versions locales réduites, sous les
mêmes noms, pour que l'app controle_en_ligne puisse migrer d'un projet à
l'autre en changeant le moins de code possible.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Suppression logique
# ---------------------------------------------------------------------------

class _NonSupprimesManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(supprime_le__isnull=True)


class _CorbeilleManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(supprime_le__isnull=False)


class SoftDeleteMixin(models.Model):
    """objects = actifs · tous = tout · corbeille = supprimés logiquement."""

    supprime_le = models.DateTimeField(null=True, blank=True, editable=False)

    objects = _NonSupprimesManager()
    tous = models.Manager()
    corbeille = _CorbeilleManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.supprime_le = timezone.now()
        self.save(update_fields=["supprime_le"])

    def restaurer(self):
        self.supprime_le = None
        self.save(update_fields=["supprime_le"])

    def supprimer_definitivement(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)


# ---------------------------------------------------------------------------
# Acteurs
# ---------------------------------------------------------------------------

class AgentProvider(models.Model):
    """
    Agent de l'APDPVP habilité à contrôler. L'authentification relève
    d'auth_app (jeton JWT) ; identifiant_sso relie l'agent à son compte.
    """

    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="agent",
    )
    identifiant_sso = models.CharField(max_length=100, blank=True, db_index=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    fonction = models.CharField(max_length=150, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Agent"
        ordering = ["nom", "prenom"]

    def __str__(self):
        return f"{self.prenom} {self.nom}".strip()


class ResponsableTraitement(SoftDeleteMixin, models.Model):
    """Organisme contrôlé : éditeur du site ou du service en ligne."""

    raison_sociale = models.CharField(max_length=255)
    sigle = models.CharField(max_length=50, blank=True)
    secteur = models.CharField(max_length=150, blank=True)
    adresse = models.TextField(blank=True)
    email_contact = models.EmailField(blank=True)
    telephone = models.CharField(max_length=50, blank=True)
    site_web = models.URLField(blank=True)
    # Lien éventuel avec la fiche du même organisme dans missions_controle.
    reference_externe = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Responsable de traitement"
        verbose_name_plural = "Responsables de traitement"
        ordering = ["raison_sociale"]

    def __str__(self):
        return self.raison_sociale


# ---------------------------------------------------------------------------
# Journal des actions (traçabilité, principe 2.3 du guide)
# ---------------------------------------------------------------------------

class JournalAction(models.Model):
    ACTIONS = [
        ("creation", "Création"),
        ("lancement_scans", "Lancement des scans"),
        ("fin_scans", "Fin des scans"),
        ("echec_scan", "Échec d'un scan"),
        ("qualification", "Qualification d'un constat"),
        ("validation", "Validation d'un constat"),
        ("devalidation", "Retrait d'une validation"),
        ("changement_statut", "Changement de statut"),
    ]

    horodatage = models.DateTimeField(default=timezone.now, db_index=True)
    action = models.CharField(max_length=30, choices=ACTIONS)
    acteur = models.ForeignKey(
        AgentProvider, null=True, blank=True, on_delete=models.SET_NULL,
        help_text="Vide pour une action du système (tâche automatique).",
    )
    objet_type = models.CharField(max_length=100)
    objet_id = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    donnees = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Entrée du journal"
        verbose_name_plural = "Journal des actions"
        ordering = ["-horodatage"]
        indexes = [models.Index(fields=["objet_type", "objet_id"])]

    def __str__(self):
        return f"{self.horodatage:%d/%m/%Y %H:%M} · {self.get_action_display()} · {self.objet_type} {self.objet_id}"
