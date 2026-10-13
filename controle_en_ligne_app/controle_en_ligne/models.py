"""
App: controle_en_ligne
Implémente la méthodologie décrite dans GUIDE_CONTROLE_EN_LIGNE.md

Séparation fondamentale (guide §6-7) :
- un CONSTAT porte des faits, écrits par un scan ou par l'agent ;
- une QUALIFICATION porte le jugement de l'agent sur ce constat :
  analyse, conformité, criticité, suite proposée, validation.

Les scans automatiques créent des constats, jamais de qualification.
La qualification vit dans sa propre table (Qualification), reliée à
n'importe quel constat, historisée, et signée par l'agent qui valide.
"""

import hashlib

from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from simple_history.models import HistoricalRecords

from core.models import SoftDeleteMixin, AgentProvider, ResponsableTraitement


# ---------------------------------------------------------------------------
# Qualification (guide §7) — table dédiée au jugement de l'agent
# ---------------------------------------------------------------------------

class Qualification(models.Model):
    """
    Jugement de l'agent sur un constat. Une seule qualification par constat.

    Conformité et criticité sont deux axes indépendants : ne jamais les
    fusionner en une « cotation » unique.
    """

    CONFORMITES = [
        ("conforme", "Conforme"),
        ("partiellement_conforme", "Partiellement conforme"),
        ("non_conforme", "Non conforme"),
        ("non_applicable", "Non applicable"),
    ]
    CRITICITES = [
        ("faible", "Faible"),
        ("moderee", "Modérée"),
        ("elevee", "Élevée"),
        ("critique", "Critique"),
    ]
    # "partiellement_conforme" = 22 caractères ; toute colonne qui stocke
    # une valeur de CONFORMITES doit utiliser cette longueur.
    LONGUEUR_CONFORMITE = 25

    # Constat qualifié (n'importe quel modèle héritant de ConstatBase).
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    constat = GenericForeignKey("content_type", "object_id")

    # Dénormalisé pour filtrer vite les qualifications d'une mission.
    mission = models.ForeignKey(
        "MissionControleEnLigne", on_delete=models.CASCADE, related_name="qualifications"
    )
    reference_grille = models.CharField(
        max_length=5, blank=True, help_text="Point de la grille concerné, ex. D05, H07."
    )

    analyse = models.TextField(
        blank=True, help_text="Mise en relation du fait avec les exigences applicables."
    )
    conformite = models.CharField(
        max_length=LONGUEUR_CONFORMITE, choices=CONFORMITES, null=True, blank=True
    )
    criticite = models.CharField(max_length=10, choices=CRITICITES, null=True, blank=True)
    suite_proposee = models.TextField(blank=True)
    commentaire_agent = models.TextField(blank=True)

    valide_par_agent = models.BooleanField(
        default=False,
        help_text="Verrou de clôture : un constat ne fait foi qu'une fois sa qualification validée.",
    )
    agent = models.ForeignKey(
        AgentProvider, null=True, blank=True, on_delete=models.PROTECT,
        related_name="qualifications",
        help_text="Agent qui a validé. Obligatoire dès que la qualification est validée.",
    )
    date_validation = models.DateTimeField(null=True, blank=True)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Qualification"
        verbose_name_plural = "Qualifications"
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id"], name="qualification_unique_par_constat"
            ),
            # Une qualification validée est complète et signée, en base aussi.
            models.CheckConstraint(
                condition=Q(valide_par_agent=False) | (
                    Q(conformite__isnull=False)
                    & Q(agent__isnull=False)
                    & Q(date_validation__isnull=False)
                    & (Q(criticite__isnull=False) | Q(conformite="non_applicable"))
                ),
                name="qualification_validee_complete",
            ),
        ]
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self):
        etat = "validée" if self.valide_par_agent else "en cours"
        ref = f"{self.reference_grille} · " if self.reference_grille else ""
        return f"{ref}{self.get_conformite_display() or 'non qualifiée'} ({etat})"

    def clean(self):
        erreurs = {}
        modele = self.content_type.model_class() if self.content_type_id else None
        if modele is not None and not issubclass(modele, ConstatBase):
            erreurs["content_type"] = "Seul un constat peut être qualifié."
        constat = self.constat if modele is not None else None
        if constat is not None and self.mission_id and constat.mission_id != self.mission_id:
            erreurs["mission"] = "La qualification doit appartenir à la mission du constat."
        if self.valide_par_agent:
            if not self.conformite:
                erreurs["conformite"] = "La conformité est obligatoire pour valider."
            if not self.criticite and self.conformite != "non_applicable":
                erreurs["criticite"] = "La criticité est obligatoire pour valider (sauf « Non applicable »)."
            if not self.agent_id:
                erreurs["agent"] = "L'agent qui valide doit être renseigné."
        if erreurs:
            raise ValidationError(erreurs)

    def save(self, *args, **kwargs):
        if self.constat is not None and not self.mission_id:
            self.mission_id = self.constat.mission_id
        if not self.reference_grille and self.constat is not None:
            self.reference_grille = getattr(self.constat, "REFERENCE_GRILLE", "")
        if self.valide_par_agent and not self.date_validation:
            self.date_validation = timezone.now()
        if not self.valide_par_agent:
            self.date_validation = None
        super().save(*args, **kwargs)

    # Opérations de l'agent, journalisées.

    def valider(self, agent: AgentProvider):
        from core.audit import journaliser

        self.valide_par_agent = True
        self.agent = agent
        self.date_validation = timezone.now()
        self.full_clean()
        self.save()
        journaliser("validation", self, acteur=agent,
                    description=f"Validation : {self.get_conformite_display()} / {self.get_criticite_display() or '—'}")
        return self

    def devalider(self, agent: AgentProvider, motif: str):
        from core.audit import journaliser

        self.valide_par_agent = False
        self.save()
        journaliser("devalidation", self, acteur=agent, description=motif)
        return self


# ---------------------------------------------------------------------------
# Base commune des constats : les faits seulement
# ---------------------------------------------------------------------------

class ConstatBase(models.Model):
    """
    Un constat décrit ce qui a été observé, sans interprétation.
    Son jugement se trouve dans `qualification` (table Qualification).
    """

    REFERENCE_GRILLE = ""  # lettre ou point de grille par défaut, surchargé par chaque constat

    fait_observe = models.TextField(
        blank=True, help_text="Description neutre du fait constaté, sans interprétation."
    )
    qualifications = GenericRelation(Qualification)

    class Meta:
        abstract = True

    @property
    def qualification(self) -> Qualification | None:
        return self.qualifications.first()

    @property
    def est_valide(self) -> bool:
        return self.qualifications.filter(valide_par_agent=True).exists()

    def qualifier(self, **champs) -> Qualification:
        """Crée ou complète la qualification de ce constat (sans la valider)."""
        champs.pop("valide_par_agent", None)  # la validation passe par Qualification.valider()
        qualification = self.qualification or Qualification(constat=self, mission_id=self.mission_id)
        for nom, valeur in champs.items():
            setattr(qualification, nom, valeur)
        qualification.full_clean()
        qualification.save()
        return qualification


def modeles_constat() -> list[type[ConstatBase]]:
    """Tous les modèles de constat de l'app : aucun ne peut échapper au verrou."""
    return [
        m for m in apps.get_app_config("controle_en_ligne").get_models()
        if issubclass(m, ConstatBase)
    ]


# ---------------------------------------------------------------------------
# Mission
# ---------------------------------------------------------------------------

class MissionControleEnLigne(SoftDeleteMixin, models.Model):
    NIVEAUX = [
        ("documentaire", "Niveau 1 — Documentaire"),
        ("fonctionnel", "Niveau 2 — Fonctionnel"),
        ("technique_approfondi", "Niveau 3 — Technique approfondi"),
    ]
    STATUTS = [
        ("planifiee", "Planifiée"),
        ("cartographie", "Cartographie en cours"),
        ("en_cours", "Contrôle en cours"),
        ("terminee", "Terminée"),
        ("validee", "Validée"),
        ("cloturee", "Clôturée"),
    ]
    ORIGINES_CONTROLE = [
        ("programme", "Contrôle programmé"),
        ("campagne_thematique", "Campagne thématique"),
        ("signalement", "Signalement / plainte"),
        ("incident", "Consécutif à un incident"),
        ("secteur_prioritaire", "Secteur prioritaire"),
        ("suivi", "Contrôle de suivi"),
        ("aleatoire", "Contrôle aléatoire"),
        ("nouveau_service", "Nouveau service numérique"),
    ]

    responsable_traitement = models.ForeignKey(ResponsableTraitement, on_delete=models.PROTECT)
    origine_controle = models.CharField(max_length=25, choices=ORIGINES_CONTROLE)
    nom_service = models.CharField(max_length=255)
    url_principale = models.URLField()
    pays_zone_ciblee = models.CharField(max_length=100, blank=True)
    nature_activite = models.CharField(max_length=255, blank=True)
    niveau_controle = models.CharField(max_length=25, choices=NIVEAUX, default="documentaire")
    statut = models.CharField(max_length=20, choices=STATUTS, default="planifiee")
    agents = models.ManyToManyField(AgentProvider, through="MembreControleEnLigne")
    # La mission sur place vit dans le service missions_controle (autre base) :
    # on garde sa référence, pas une clé étrangère.
    reference_mission_sur_place = models.CharField(max_length=100, blank=True)
    ip_publique_observee = models.GenericIPAddressField(null=True, blank=True)
    date_lancement = models.DateTimeField(auto_now_add=True)
    date_cloture = models.DateTimeField(null=True, blank=True)
    erreurs_scan = models.JSONField(
        default=list, blank=True,
        help_text="Échecs du dernier lancement des scans automatiques : "
                  "[{scan, erreur, horodatage}]. Liste vide = tous les scans ont abouti.",
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Mission de contrôle en ligne"
        verbose_name_plural = "Missions de contrôle en ligne"
        ordering = ["-date_lancement"]

    def __str__(self):
        return f"{self.nom_service} ({self.get_statut_display()})"

    def bilan_validation(self) -> tuple[int, int]:
        """(constats validés, constats au total) sur tous les modèles de constat."""
        valides = total = 0
        for modele in modeles_constat():
            ids = list(modele.objects.filter(mission=self).values_list("pk", flat=True))
            if not ids:
                continue
            total += len(ids)
            valides += Qualification.objects.filter(
                content_type=ContentType.objects.get_for_model(modele),
                object_id__in=ids,
                valide_par_agent=True,
            ).count()
        return valides, total

    def tous_constats_valides(self) -> bool:
        """
        Condition nécessaire (non suffisante) au passage terminee -> validee :
        au moins un constat, et chacun porte une qualification validée.
        """
        valides, total = self.bilan_validation()
        return total > 0 and valides == total

    def clean(self):
        if self.statut in {"validee", "cloturee"} and self.pk and not self.tous_constats_valides():
            raise ValidationError(
                {"statut": "Tous les constats doivent avoir une qualification validée avant validation de la mission."}
            )


class MembreControleEnLigne(models.Model):
    mission = models.ForeignKey(MissionControleEnLigne, on_delete=models.CASCADE)
    agent = models.ForeignKey(AgentProvider, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Membre de l'équipe de contrôle"
        constraints = [
            models.UniqueConstraint(fields=["mission", "agent"], name="membre_unique_par_mission"),
        ]


class EnvironnementControle(models.Model):
    """
    Le "poste de contrôle APDPVP" (guide §4). Répond à la question :
    dans quelles conditions ce constat a-t-il été réalisé ?
    """
    mission = models.OneToOneField(MissionControleEnLigne, on_delete=models.CASCADE)
    navigateur = models.CharField(max_length=100)
    version_navigateur = models.CharField(max_length=50)
    systeme_exploitation = models.CharField(max_length=100, blank=True)
    profil_vierge = models.BooleanField(default=True)
    horloge_synchronisee = models.BooleanField(default=True)
    outils_utilises = models.JSONField(default=list, blank=True)  # ex: ["playwright", "requests"]
    compte_test_utilise = models.BooleanField(default=False)
    donnees_fictives_utilisees = models.BooleanField(default=False)
    date_enregistrement = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Environnement de contrôle"


# ---------------------------------------------------------------------------
# Phase 1 — Cartographie
# ---------------------------------------------------------------------------

class PageIdentifiee(models.Model):
    TYPES = [
        ("accueil", "Accueil"), ("inscription", "Inscription"), ("connexion", "Connexion"),
        ("commande", "Commande"), ("paiement", "Paiement"), ("contact", "Contact"),
        ("newsletter", "Newsletter"), ("espace_client", "Espace client"),
        ("cookies", "Page cookies"), ("confidentialite", "Politique de confidentialité"),
        ("mentions_legales", "Mentions légales"), ("cgu", "CGU"), ("cgv", "CGV"),
    ]
    ORIGINES = [("auto", "Automatique"), ("manuel", "Manuel")]

    mission = models.ForeignKey(MissionControleEnLigne, on_delete=models.CASCADE, related_name="pages")
    type_page = models.CharField(max_length=30, choices=TYPES)
    url = models.URLField(blank=True, max_length=500)
    presente = models.BooleanField(null=True)
    origine = models.CharField(max_length=10, choices=ORIGINES, default="auto")
    indice = models.CharField(
        max_length=255, blank=True,
        help_text="Ce qui a permis l'identification (texte du lien, titre, formulaire).",
    )

    class Meta:
        verbose_name = "Page identifiée"
        verbose_name_plural = "Pages identifiées"


# ---------------------------------------------------------------------------
# Phase 2 — Données collectées
# ---------------------------------------------------------------------------

class ConstatDonnees(ConstatBase):
    REFERENCE_GRILLE = "F01"

    mission = models.ForeignKey(MissionControleEnLigne, on_delete=models.CASCADE, related_name="constats_donnees")
    fonctionnalite = models.CharField(max_length=100)
    categorie_donnee = models.CharField(max_length=100)
    champ_html_detecte = models.CharField(max_length=100, blank=True)
    donnee_justifiee_par_finalite = models.BooleanField(null=True)

    class Meta:
        verbose_name = "Constat — données collectées"


# ---------------------------------------------------------------------------
# Phase 3 — Information des personnes
# ---------------------------------------------------------------------------

class ConstatInformation(ConstatBase):
    REFERENCE_GRILLE = "C"
    # Relevé point par point (C02 à C09) ; distinct de la qualification globale du constat.
    QUALIF = Qualification.CONFORMITES
    _LONGUEUR = Qualification.LONGUEUR_CONFORMITE

    mission = models.OneToOneField(MissionControleEnLigne, on_delete=models.CASCADE)
    politique_disponible = models.BooleanField(null=True, help_text="C01")
    identite_responsable = models.CharField(max_length=_LONGUEUR, choices=QUALIF, null=True, blank=True)
    finalites = models.CharField(max_length=_LONGUEUR, choices=QUALIF, null=True, blank=True)
    categories_donnees = models.CharField(max_length=_LONGUEUR, choices=QUALIF, null=True, blank=True)
    base_juridique = models.CharField(max_length=_LONGUEUR, choices=QUALIF, null=True, blank=True)
    duree_conservation = models.CharField(max_length=_LONGUEUR, choices=QUALIF, null=True, blank=True)
    destinataires = models.CharField(max_length=_LONGUEUR, choices=QUALIF, null=True, blank=True)
    transferts = models.CharField(max_length=_LONGUEUR, choices=QUALIF, null=True, blank=True)
    droits = models.CharField(max_length=_LONGUEUR, choices=QUALIF, null=True, blank=True)
    contact_dpo = models.CharField(max_length=_LONGUEUR, choices=QUALIF, null=True, blank=True)
    texte_extrait = models.TextField(blank=True)

    class Meta:
        verbose_name = "Constat — information des personnes"


# ---------------------------------------------------------------------------
# Phase 4 — Cookies et autres traceurs
#
# Modèle volontairement générique (guide §5) : cookies, storages, pixels,
# scripts tiers, identifiants publicitaires, fingerprinting.
# Un traceur dont le scanner ne connaît pas le type est répertorié en
# "non_classe" avec son type brut, pour que l'agent le classe à la main.
# ---------------------------------------------------------------------------

class ConstatCookie(ConstatBase):
    REFERENCE_GRILLE = "D"

    SCENARIOS = [
        ("avant", "Avant interaction"),
        ("acceptation", "Après acceptation"),
        ("refus", "Après refus"),
        ("modification", "Après modification du choix"),
    ]
    TYPES_TRACEUR = [
        ("cookie", "Cookie"),
        ("local_storage", "localStorage"),
        ("session_storage", "sessionStorage"),
        ("pixel", "Pixel de suivi"),
        ("script_tiers", "Script tiers"),
        ("identifiant_pub", "Identifiant publicitaire"),
        ("fingerprinting", "Fingerprinting"),
        ("appel_reseau_tiers", "Appel réseau vers service tiers"),
        ("non_classe", "Non classé — à qualifier"),
    ]

    mission = models.ForeignKey(MissionControleEnLigne, on_delete=models.CASCADE, related_name="constats_cookies")
    scenario = models.CharField(max_length=15, choices=SCENARIOS)
    type_traceur = models.CharField(max_length=20, choices=TYPES_TRACEUR, default="cookie")
    type_brut = models.CharField(
        max_length=100, blank=True,
        help_text="Type tel que renvoyé par le scanner, conservé quand il n'est pas reconnu.",
    )
    nom = models.CharField(max_length=255, help_text="Nom du cookie, ou clé de stockage, ou domaine du script.")
    domaine = models.CharField(max_length=255)
    est_tiers = models.BooleanField()
    duree_vie_jours = models.IntegerField(null=True, blank=True)
    finalite_annoncee = models.CharField(max_length=100, blank=True)
    finalite_apparente = models.CharField(max_length=100, blank=True)
    necessaire = models.BooleanField(null=True)
    horodatage_scan = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Constat — traceur"
        verbose_name_plural = "Constats — traceurs"
        indexes = [models.Index(fields=["mission", "scenario"])]

    def __str__(self):
        return f"{self.get_scenario_display()} · {self.nom} ({self.domaine})"


# ---------------------------------------------------------------------------
# Phase 5 — Consentement
# ---------------------------------------------------------------------------

class ConstatConsentement(ConstatBase):
    REFERENCE_GRILLE = "E"

    mission = models.OneToOneField(MissionControleEnLigne, on_delete=models.CASCADE)
    banniere_detectee = models.BooleanField(null=True)
    cmp_identifiee = models.CharField(max_length=100, blank=True)
    consentement_avant_traitement = models.BooleanField(null=True)
    information_claire = models.BooleanField(null=True)
    refus_possible = models.BooleanField(null=True)
    refus_aussi_simple = models.BooleanField(null=True)
    finalites_distinguees = models.BooleanField(null=True)
    choix_modifiable = models.BooleanField(null=True)
    choix_persiste = models.BooleanField(null=True)
    traceurs_avant_consentement = models.BooleanField(null=True)

    class Meta:
        verbose_name = "Constat — consentement"


# ---------------------------------------------------------------------------
# Phase 6 — Formulaires
# ---------------------------------------------------------------------------

class ConstatFormulaire(ConstatBase):
    REFERENCE_GRILLE = "F"

    mission = models.ForeignKey(MissionControleEnLigne, on_delete=models.CASCADE, related_name="constats_formulaires")
    url_formulaire = models.URLField(max_length=500)
    champs_demandes = models.JSONField(default=list, blank=True)
    minimisation_respectee = models.BooleanField(null=True)
    information_presente = models.BooleanField(null=True)
    case_consentement_presente = models.BooleanField(null=True)
    case_precochee = models.BooleanField(null=True)
    methode_http = models.CharField(max_length=10, blank=True)
    donnee_sensible_en_get = models.BooleanField(null=True)
    transmission_securisee = models.BooleanField(null=True)
    message_erreur_verbeux = models.BooleanField(null=True)

    class Meta:
        verbose_name = "Constat — formulaire"


# ---------------------------------------------------------------------------
# Phase 7 — Comptes utilisateurs
# ---------------------------------------------------------------------------

class ConstatCompte(ConstatBase):
    REFERENCE_GRILLE = "G"

    mission = models.OneToOneField(MissionControleEnLigne, on_delete=models.CASCADE)
    compte_test_cree = models.BooleanField(default=False)
    creation_ok = models.BooleanField(null=True)
    connexion_ok = models.BooleanField(null=True)
    modification_profil_ok = models.BooleanField(null=True)
    modification_mdp_ok = models.BooleanField(null=True)
    reinitialisation_mdp_ok = models.BooleanField(null=True)
    suppression_compte_ok = models.BooleanField(null=True)
    consultation_donnees_ok = models.BooleanField(null=True)
    exercice_droits_depuis_compte_ok = models.BooleanField(null=True)

    class Meta:
        verbose_name = "Constat — comptes utilisateurs"


# ---------------------------------------------------------------------------
# Phase 8 — Sécurité observable
# ---------------------------------------------------------------------------

class ConstatSecurite(ConstatBase):
    REFERENCE_GRILLE = "H"

    mission = models.OneToOneField(MissionControleEnLigne, on_delete=models.CASCADE)
    https_complet = models.BooleanField(null=True)
    redirection_http_https = models.BooleanField(null=True)
    certificat_valide = models.BooleanField(null=True)
    certificat_expiration = models.DateField(null=True, blank=True)
    en_tetes_securite = models.JSONField(default=dict, blank=True)
    contenu_sensible_non_chiffre = models.BooleanField(null=True)
    infos_techniques_exposees = models.BooleanField(null=True)
    donnees_personnelles_exposees = models.BooleanField(null=True)
    pages_admin_test_exposees = models.BooleanField(null=True)
    fichiers_exposes = models.JSONField(default=list, blank=True)
    cookie_session_secure_httponly = models.BooleanField(null=True)
    risque_technique_suspecte = models.BooleanField(
        default=False,
        help_text="Signal qui ouvre, hors périmètre auto, une procédure de contrôle niveau 3.",
    )

    class Meta:
        verbose_name = "Constat — sécurité observable"


# ---------------------------------------------------------------------------
# Phase 9 — CGU / CGV / mentions légales
# ---------------------------------------------------------------------------

class ConstatLegal(ConstatBase):
    REFERENCE_GRILLE = "I"

    mission = models.OneToOneField(MissionControleEnLigne, on_delete=models.CASCADE)

    cgu_identite_operateur = models.BooleanField(null=True)
    cgu_conditions_utilisation = models.BooleanField(null=True)
    cgu_regles_comptes = models.BooleanField(null=True)
    cgu_traitement_donnees = models.BooleanField(null=True)
    cgu_responsabilites = models.BooleanField(null=True)
    cgu_contact = models.BooleanField(null=True)
    texte_cgu_extrait = models.TextField(blank=True)

    cgv_identite_vendeur = models.BooleanField(null=True)
    cgv_infos_produits = models.BooleanField(null=True)
    cgv_prix = models.BooleanField(null=True)
    cgv_conditions_commande = models.BooleanField(null=True)
    cgv_paiement = models.BooleanField(null=True)
    cgv_livraison = models.BooleanField(null=True)
    cgv_retractation = models.BooleanField(null=True)
    cgv_remboursement = models.BooleanField(null=True)
    cgv_reclamation = models.BooleanField(null=True)
    texte_cgv_extrait = models.TextField(blank=True)

    mentions_legales_presentes = models.BooleanField(null=True)
    coherence_pratiques_declarees = models.BooleanField(null=True)

    class Meta:
        verbose_name = "Constat — CGU / CGV / mentions légales"


# ---------------------------------------------------------------------------
# Phase 10 — Exercice des droits
# ---------------------------------------------------------------------------

class ConstatDroits(ConstatBase):
    REFERENCE_GRILLE = "J"

    mission = models.OneToOneField(MissionControleEnLigne, on_delete=models.CASCADE)
    mecanisme_existe = models.BooleanField(null=True)
    facilement_accessible = models.BooleanField(null=True)
    modalites_claires = models.BooleanField(null=True)
    droits_identifies = models.BooleanField(null=True)
    infos_necessaires_precisees = models.BooleanField(null=True)
    procedure_suppression_existe = models.BooleanField(null=True)
    teste_via_compte_test = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Constat — exercice des droits"


# ---------------------------------------------------------------------------
# Phase 11 — Tiers et services externes
# ---------------------------------------------------------------------------

class ConstatTiers(ConstatBase):
    REFERENCE_GRILLE = "K"

    CATEGORIES = [
        ("analytics", "Statistiques"), ("publicite", "Régie publicitaire"),
        ("video", "Plateforme vidéo"), ("carte", "Géolocalisation"),
        ("paiement", "Paiement"), ("messagerie", "Messagerie"),
        ("marketing", "Marketing"), ("support", "Support client"),
        ("reseau_social", "Réseau social"), ("autre", "Autre"),
    ]
    ORIGINES = [("auto", "Automatique"), ("manuel", "Manuel")]

    mission = models.ForeignKey(MissionControleEnLigne, on_delete=models.CASCADE, related_name="constats_tiers")
    domaine_tiers = models.CharField(max_length=255)
    categorie = models.CharField(max_length=20, choices=CATEGORIES)
    declare_dans_politique = models.BooleanField(null=True)
    origine = models.CharField(max_length=10, choices=ORIGINES, default="auto")

    class Meta:
        verbose_name = "Constat — service tiers"
        verbose_name_plural = "Constats — services tiers"
        constraints = [
            models.UniqueConstraint(fields=["mission", "domaine_tiers"], name="tiers_unique_par_mission"),
        ]


# ---------------------------------------------------------------------------
# Phase 12 — Tests reproductibles
# ---------------------------------------------------------------------------

class ScenarioTest(models.Model):
    NUMEROS = [(i, f"Test {i}") for i in range(1, 11)]

    mission = models.ForeignKey(MissionControleEnLigne, on_delete=models.CASCADE, related_name="scenarios_tests")
    numero_test = models.IntegerField(choices=NUMEROS)
    execute = models.BooleanField(default=False)
    date_execution = models.DateTimeField(null=True, blank=True)
    resultat_json = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Test reproductible"
        constraints = [
            models.UniqueConstraint(fields=["mission", "numero_test"], name="test_unique_par_mission"),
        ]


# ---------------------------------------------------------------------------
# Preuves (guide §8 — table de constitution de la preuve)
# ---------------------------------------------------------------------------

class PreuveCapture(models.Model):
    TYPES = [
        ("screenshot", "Capture"), ("har", "Export HAR"), ("pdf", "PDF page"),
        ("resultat_technique", "Résultat technique brut"),
    ]

    mission = models.ForeignKey(MissionControleEnLigne, on_delete=models.CASCADE, related_name="preuves")
    type_preuve = models.CharField(max_length=25, choices=TYPES)
    fichier = models.FileField(upload_to="controle_en_ligne/preuves/", max_length=255)
    empreinte_sha256 = models.CharField(
        max_length=64, blank=True, editable=False,
        help_text="Hash d'intégrité de la preuve, calculé et figé au premier enregistrement.",
    )
    scenario_lie = models.CharField(max_length=50, blank=True)
    parcours_effectue = models.TextField(blank=True)
    action_agent = models.TextField(blank=True)
    resultat_obtenu = models.TextField(blank=True)
    outil_technique = models.CharField(max_length=100, blank=True)
    horodatage = models.DateTimeField(auto_now_add=True)
    genere_automatiquement = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Preuve"
        ordering = ["horodatage"]

    def save(self, *args, **kwargs):
        # L'empreinte fige l'état de la preuve : jamais recalculée après coup.
        if self.fichier and not self.empreinte_sha256:
            self.empreinte_sha256 = self.calculer_empreinte()
        super().save(*args, **kwargs)

    def calculer_empreinte(self) -> str:
        """SHA-256 du fichier tel qu'il est stocké."""
        empreinte = hashlib.sha256()
        self.fichier.open("rb")
        try:
            for bloc in self.fichier.chunks():
                empreinte.update(bloc)
        finally:
            self.fichier.close()
        return empreinte.hexdigest()

    def integrite_verifiee(self) -> bool:
        return bool(self.empreinte_sha256) and self.calculer_empreinte() == self.empreinte_sha256


# ---------------------------------------------------------------------------
# Suivi (guide §12 — Notifier / Mesures correctives / Suivre / Clôturer)
# ---------------------------------------------------------------------------

class SuiviCorrectif(models.Model):
    STATUTS = [
        ("notifiee", "Notifiée au responsable de traitement"),
        ("en_attente", "En attente de correction"),
        ("corrigee", "Corrigée — vérifiée en contrôle de suivi"),
        ("non_corrigee", "Non corrigée à l'échéance"),
        ("escaladee", "Escaladée vers une nouvelle suite administrative"),
    ]
    mission = models.ForeignKey(MissionControleEnLigne, on_delete=models.CASCADE, related_name="suivis")
    qualification = models.ForeignKey(
        Qualification, null=True, blank=True, on_delete=models.SET_NULL, related_name="suivis",
        help_text="Qualification à l'origine de la mesure corrective.",
    )
    constat_reference = models.CharField(max_length=50, help_text="Ex. référence de grille : D05, H07...")
    statut = models.CharField(max_length=20, choices=STATUTS, default="notifiee")
    date_notification = models.DateTimeField(null=True, blank=True)
    delai_correction = models.DateField(null=True, blank=True)
    date_controle_suivi = models.DateTimeField(null=True, blank=True)
    mission_suivi_liee = models.ForeignKey(
        MissionControleEnLigne, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="suivis_en_tant_que_controle_suivi",
    )

    class Meta:
        verbose_name = "Suivi correctif"
