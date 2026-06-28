from datetime import date

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

from core.models import SoftDeleteModel


# ============ Modèles de référence ============
class Department(SoftDeleteModel):
    nom = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Département"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class CategorieProfessionnelle(SoftDeleteModel):
    code = models.CharField(max_length=20, unique=True)
    libelle = models.CharField(max_length=100)
    niveau = models.PositiveSmallIntegerField(default=1, help_text="Pour l'ordre d'avancement")

    class Meta:
        verbose_name = "Catégorie professionnelle"
        verbose_name_plural = "Catégories professionnelles"
        ordering = ["-niveau", "libelle"]

    def __str__(self):
        return self.libelle


class StatutAgent(SoftDeleteModel):
    code = models.CharField(max_length=20, unique=True)
    libelle = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Statut d'agent"
        verbose_name_plural = "Statuts d'agent"
        ordering = ["libelle"]

    def __str__(self):
        return self.libelle


class Poste(SoftDeleteModel):
    intitule = models.CharField(max_length=150)
    departement = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True, help_text="Sert à générer la fiche de poste")

    class Meta:
        verbose_name = "Poste"
        ordering = ["intitule"]

    def __str__(self):
        return self.intitule


class TypeContrat(SoftDeleteModel):
    code = models.CharField(max_length=20, unique=True)
    libelle = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Type de contrat"
        verbose_name_plural = "Types de contrat"
        ordering = ["libelle"]

    def __str__(self):
        return self.libelle


# ============ Helpers ============
def _prochaine_occurrence(d):
    """Prochaine occurrence (>= aujourd'hui) du jour/mois de `d`."""
    if not d:
        return None
    today = date.today()
    for annee in (today.year, today.year + 1):
        try:
            occ = d.replace(year=annee)
        except ValueError:  # 29 février sur année non bissextile
            occ = date(annee, 3, 1)
        if occ >= today:
            return occ
    return None


PDF_IMG = FileExtensionValidator(["pdf", "jpg", "jpeg", "png"])


# ============ Agent ============
class Employee(SoftDeleteModel):
    STATUS_CHOICES = [("actif", "Actif"), ("inactif", "Inactif")]
    MATRIMONIAL_CHOICES = [
        ("celibataire", "Célibataire"),
        ("marie", "Marié(e)"),
        ("divorce", "Divorcé(e)"),
        ("veuf", "Veuf(ve)"),
        ("union_libre", "Union libre"),
    ]

    # Compte de connexion lié (SSO)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="employee", verbose_name="Compte utilisateur",
    )

    # Identité
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField()
    date_naissance = models.DateField(null=True, blank=True)
    statut_matrimonial = models.CharField(max_length=15, choices=MATRIMONIAL_CHOICES, default="celibataire")
    nombre_enfants = models.PositiveSmallIntegerField(default=0)

    # Contacts
    telephone1 = models.CharField("Téléphone 1", max_length=30, blank=True)
    telephone2 = models.CharField("Téléphone 2", max_length=30, blank=True)
    telephone_urgence = models.CharField("Téléphone d'urgence", max_length=30, blank=True)

    # Dossier
    cv = models.FileField(upload_to="cv/", blank=True, validators=[PDF_IMG])
    lettre_motivation = models.FileField(upload_to="lettres/", blank=True, validators=[PDF_IMG])

    # Matricules (uniques parmi les agents actifs, voir contraintes)
    matricule_cnss = models.CharField("Matricule CNSS", max_length=50, blank=True)
    matricule_cnamgs = models.CharField("Matricule CNAMGS", max_length=50, blank=True)
    matricule_apdpvp = models.CharField("Matricule APDPVP", max_length=50, blank=True)

    # Affectation / situation
    departement = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    categorie = models.ForeignKey(CategorieProfessionnelle, on_delete=models.SET_NULL, null=True, blank=True)
    poste = models.CharField(max_length=100, blank=True, help_text="Poste principal (libellé). Voir aussi Affectations.")
    statut_agent = models.ForeignKey(StatutAgent, on_delete=models.SET_NULL, null=True, blank=True)
    date_embauche = models.DateField(help_text="Ne change pas après création.")
    salaire = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    statut = models.CharField(max_length=10, choices=STATUS_CHOICES, default="actif")
    photo = models.ImageField(upload_to="photos/", blank=True)

    class Meta:
        verbose_name = "Employé"
        ordering = ["nom", "prenom"]
        constraints = [
            models.UniqueConstraint(
                fields=["email"], condition=models.Q(is_deleted=False),
                name="unique_email_employe_actif",
            ),
            models.UniqueConstraint(
                fields=["matricule_cnss"],
                condition=models.Q(is_deleted=False) & ~models.Q(matricule_cnss=""),
                name="unique_cnss_actif",
            ),
            models.UniqueConstraint(
                fields=["matricule_cnamgs"],
                condition=models.Q(is_deleted=False) & ~models.Q(matricule_cnamgs=""),
                name="unique_cnamgs_actif",
            ),
            models.UniqueConstraint(
                fields=["matricule_apdpvp"],
                condition=models.Q(is_deleted=False) & ~models.Q(matricule_apdpvp=""),
                name="unique_apdpvp_actif",
            ),
        ]

    def __str__(self):
        return f"{self.prenom} {self.nom}"

    # --- Anniversaire de naissance ---
    @property
    def prochain_anniversaire(self):
        return _prochaine_occurrence(self.date_naissance)

    @property
    def jours_avant_anniversaire(self):
        occ = self.prochain_anniversaire
        return (occ - date.today()).days if occ else None

    @property
    def age(self):
        if not self.date_naissance:
            return None
        t = date.today()
        return t.year - self.date_naissance.year - (
            (t.month, t.day) < (self.date_naissance.month, self.date_naissance.day)
        )

    # --- Anniversaire de service (embauche) ---
    @property
    def prochain_anniversaire_service(self):
        return _prochaine_occurrence(self.date_embauche)

    @property
    def jours_avant_anniversaire_service(self):
        occ = self.prochain_anniversaire_service
        return (occ - date.today()).days if occ else None

    @property
    def anciennete(self):
        if not self.date_embauche:
            return None
        t = date.today()
        return t.year - self.date_embauche.year - (
            (t.month, t.day) < (self.date_embauche.month, self.date_embauche.day)
        )

    @property
    def contrat_courant(self):
        return self.contrats.filter(date_fin__isnull=True).order_by("-date_debut").first() \
            or self.contrats.order_by("-date_debut").first()

    @property
    def poste_principal(self):
        aff = self.affectations.filter(principal=True).first() or self.affectations.first()
        return aff.poste if aff else None


# ============ Modèles liés à l'agent ============
class Diplome(SoftDeleteModel):
    employe = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="diplomes")
    intitule = models.CharField(max_length=200)
    etablissement = models.CharField(max_length=200, blank=True)
    annee = models.PositiveSmallIntegerField(null=True, blank=True)
    fichier = models.FileField(upload_to="diplomes/", blank=True, validators=[PDF_IMG])

    class Meta:
        verbose_name = "Diplôme"
        ordering = ["-annee", "intitule"]

    def __str__(self):
        return f"{self.intitule} — {self.employe}"


class Contrat(SoftDeleteModel):
    employe = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="contrats")
    type_contrat = models.ForeignKey(TypeContrat, on_delete=models.SET_NULL, null=True)
    reference = models.CharField(max_length=50, blank=True)
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True, help_text="Vide = en cours / indéterminé")
    fichier = models.FileField(upload_to="contrats/", blank=True, validators=[PDF_IMG])

    class Meta:
        verbose_name = "Contrat"
        ordering = ["-date_debut"]

    def __str__(self):
        return f"{self.type_contrat} — {self.employe}"

    @property
    def en_cours(self):
        return self.date_fin is None or self.date_fin >= date.today()


class Affectation(SoftDeleteModel):
    employe = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="affectations")
    poste = models.ForeignKey(Poste, on_delete=models.CASCADE, related_name="affectations")
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)
    principal = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Affectation"
        ordering = ["-principal", "-date_debut"]

    def __str__(self):
        return f"{self.poste} — {self.employe}"


class Evaluation(SoftDeleteModel):
    employe = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="evaluations")
    date_evaluation = models.DateField()
    note = models.PositiveSmallIntegerField(default=0, help_text="Sur 20")
    appreciation = models.TextField(blank=True)
    evaluateur = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="evaluations_menees"
    )

    class Meta:
        verbose_name = "Évaluation"
        ordering = ["-date_evaluation"]

    def __str__(self):
        return f"Éval. {self.employe} ({self.date_evaluation})"
