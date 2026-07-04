from django.contrib.auth.models import AbstractUser
from django.db import models


class Poste(models.Model):
    """Poste occupé par un agent — indépendant du rôle (groupe Django)."""

    code = models.SlugField(max_length=50, unique=True)
    libelle = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Poste"
        verbose_name_plural = "Postes"
        ordering = ["libelle"]

    def __str__(self):
        return self.libelle


class User(AbstractUser):
    """Utilisateur APDPVP — identité SSO partagée entre tous les services."""

    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    telephone = models.CharField(max_length=30, blank=True)
    # Un utilisateur peut occuper plusieurs postes simultanément.
    postes = models.ManyToManyField(Poste, blank=True, related_name="agents", verbose_name="Postes occupés")

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def get_roles(self):
        return list(self.groups.values_list("name", flat=True))


class Application(models.Model):
    """
    Application du portail APDPVP, affichée sur le tableau de bord
    si l'utilisateur a un rôle OU un poste autorisé (superuser : accès total).
    """

    nom = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True)
    url = models.CharField(max_length=200, help_text="URL complète, ex: http://rh.apdpvp.local")
    description = models.TextField(blank=True)
    icone = models.CharField(max_length=50, default="layout-dashboard", help_text="Nom d'icône Lucide")
    couleur = models.CharField(max_length=30, default="indigo", help_text="Couleur Tailwind, ex: emerald, blue, violet")
    est_active = models.BooleanField(default=True)
    ordre = models.PositiveSmallIntegerField(default=0)

    roles_autorises = models.ManyToManyField(
        "auth.Group", blank=True, related_name="applications",
        verbose_name="Rôles autorisés",
        help_text="Groupes (rôles) pouvant accéder à cette application",
    )
    postes_autorises = models.ManyToManyField(
        Poste, blank=True, related_name="applications",
        verbose_name="Postes autorisés",
        help_text="Postes pouvant accéder à cette application",
    )

    class Meta:
        verbose_name = "Application"
        verbose_name_plural = "Applications"
        ordering = ["ordre", "nom"]

    def __str__(self):
        return self.nom

    def est_accessible_par(self, user):
        if user.is_superuser:
            return True
        return (
            self.roles_autorises.filter(pk__in=user.groups.all()).exists()
            or self.postes_autorises.filter(pk__in=user.postes.all()).exists()
        )

    @classmethod
    def accessibles_par(cls, user):
        """Retourne les applications actives accessibles à `user`."""
        qs = cls.objects.filter(est_active=True)
        if user.is_superuser:
            return qs
        from django.db.models import Q
        return qs.filter(
            Q(roles_autorises__in=user.groups.all()) | Q(postes_autorises__in=user.postes.all())
        ).distinct()
