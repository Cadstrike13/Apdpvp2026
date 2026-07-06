from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from simple_history.models import HistoricalRecords

from core.models import CorbeilleManager, SoftDeleteManager, SoftDeleteMixin, SoftDeleteQuerySet, TousManager
from core.validators import ValidateurTailleFichier

EXTENSIONS_SCAN_AUTORISEES = ["pdf", "jpg", "jpeg", "png"]
EXTENSIONS_CONTRAT_AUTORISEES = ["pdf", "doc", "docx"]
TAILLE_MAX_FICHIER_MO = 10


class Traitement(models.TextChoices):
    """Les 10 traitements audités par mission (grille du questionnaire)."""

    GESTION_PERSONNEL = "a", "Gestion du personnel"
    GESTION_CLIENTS = "b", "Gestion des clients"
    COMMUNICATION_TRANSMISSION = "c", "Communication par transmission"
    CONTROLE_ACCES_SANS_BIOMETRIE = "d", "Contrôle d'accès sans biométrie"
    CONTROLE_ACCES_AVEC_BIOMETRIE = "e", "Contrôle d'accès avec biométrie"
    TELE_VIDEOSURVEILLANCE = "f", "Télé-vidéosurveillance"
    VIDEOSURVEILLANCE = "g", "Vidéosurveillance"
    TRANSFERT_DONNEES = "h", "Transfert des données"
    INTERCONNEXION = "i", "Interconnexion"
    GEOLOCALISATION = "j", "Géolocalisation"


class StatutMission(models.IntegerChoices):
    """Ordre du circuit de clôture : le procès-verbal (PV) est généré et
    verrouille la mission ; une fois imprimé/signé/scanné, le rapport final
    est généré à partir du PV signé ; la mission est enfin validée."""

    BROUILLON = 10, "Brouillon"
    PLANIFIEE = 20, "Planifiée"
    EN_COURS = 30, "En cours"
    QUESTIONNAIRE_COMPLETE = 40, "Questionnaire complété"
    PV_GENERE = 50, "Procès-verbal généré"
    PV_SCAN_UPLOAD = 60, "Procès-verbal signé uploadé"
    RAPPORT_GENERE = 70, "Rapport généré"
    RAPPORT_SCAN_UPLOAD = 80, "Rapport signé uploadé"
    VALIDEE = 90, "Validée"


COULEURS_STATUT = {
    StatutMission.BROUILLON: "bg-gray-100 text-gray-700",
    StatutMission.PLANIFIEE: "bg-blue-100 text-blue-800",
    StatutMission.EN_COURS: "bg-blue-100 text-blue-800",
    StatutMission.QUESTIONNAIRE_COMPLETE: "bg-blue-100 text-blue-800",
    StatutMission.PV_GENERE: "bg-amber-100 text-amber-800",
    StatutMission.PV_SCAN_UPLOAD: "bg-amber-100 text-amber-800",
    StatutMission.RAPPORT_GENERE: "bg-amber-100 text-amber-800",
    StatutMission.RAPPORT_SCAN_UPLOAD: "bg-amber-100 text-amber-800",
    StatutMission.VALIDEE: "bg-green-100 text-green-800",
}


class ModePV(models.TextChoices):
    """Mode de déroulement du contrôle — voir missions/generate_pv.py."""

    IN_SITU = "in situ", "In situ"
    EN_LIGNE = "en ligne", "En ligne"


class RoleMission(models.TextChoices):
    CHEF = "chef", "Chef de mission"
    AGENT = "agent", "Agent contrôleur"


class TypeAction(models.TextChoices):
    CREATION = "creation", "Création de la mission"
    QUESTIONNAIRE_COMPLETE = "questionnaire_complete", "Questionnaire complété"
    PV_GENERE = "pv_genere", "Procès-verbal généré"
    SCAN_UPLOAD = "scan_upload", "Procès-verbal signé uploadé"
    RAPPORT_GENERE = "rapport_genere", "Rapport généré"
    RAPPORT_SCAN_UPLOAD = "rapport_scan_upload", "Rapport signé uploadé"
    VALIDATION = "validation", "Mission validée"


class MissionControleQuerySet(SoftDeleteQuerySet):
    pass


class MissionControleManager(SoftDeleteManager):
    def get_queryset(self):
        return MissionControleQuerySet(self.model, using=self._db).actifs()


class MissionControle(SoftDeleteMixin, models.Model):
    entite_controlee = models.ForeignKey(
        "entites.EntiteControlee", on_delete=models.PROTECT, related_name="missions"
    )
    date_mission = models.DateField()
    statut = models.IntegerField(choices=StatutMission.choices, default=StatutMission.BROUILLON)
    commentaires_observations = models.TextField(blank=True)
    scan_signe = models.FileField(
        verbose_name="Procès-verbal signé (scan)",
        upload_to="scans_signes/%Y/%m/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(EXTENSIONS_SCAN_AUTORISEES),
            ValidateurTailleFichier(TAILLE_MAX_FICHIER_MO),
        ],
    )

    # Informations nécessaires à la génération du procès-verbal
    # (missions/generate_pv.py) — non déductibles des autres modèles.
    mode_pv = models.CharField(max_length=10, choices=ModePV.choices, blank=True)
    nom_representant_entite = models.CharField(
        "Nom du représentant de l'entité", max_length=255, blank=True,
    )
    heure_controle = models.CharField(max_length=20, blank=True, help_text="Ex. 09h30")
    deliberation_numero = models.CharField(
        "N° de délibération", max_length=50, blank=True,
        help_text="Délibération portant adoption de la procédure des missions de contrôle.",
    )
    deliberation_organe = models.CharField(
        "Organe de la délibération", max_length=255, blank=True, default="Conseil de l'APDPVP",
    )
    lieu_signature = models.CharField(max_length=255, blank=True)
    date_signature = models.DateField(null=True, blank=True)
    heure_signature = models.CharField(max_length=20, blank=True, help_text="Ex. 12h15")
    pv_document = models.FileField(
        verbose_name="Procès-verbal (document généré)",
        upload_to="pv/%Y/%m/", blank=True, null=True,
    )
    pv_document_pdf = models.FileField(
        verbose_name="Procès-verbal (PDF généré)",
        upload_to="pv/%Y/%m/", blank=True, null=True,
    )
    rapport_signe = models.FileField(
        verbose_name="Rapport signé (scan)",
        upload_to="rapports_signes/%Y/%m/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(EXTENSIONS_SCAN_AUTORISEES),
            ValidateurTailleFichier(TAILLE_MAX_FICHIER_MO),
        ],
    )

    history = HistoricalRecords()

    objects = MissionControleManager()
    tous = TousManager()
    corbeille = CorbeilleManager()

    class Meta:
        verbose_name = "Mission de contrôle"
        verbose_name_plural = "Missions de contrôle"

    def __str__(self):
        return f"Mission {self.entite_controlee} — {self.date_mission}"

    @property
    def est_verrouillee(self):
        return self.statut >= StatutMission.PV_GENERE

    @property
    def statut_css_classes(self):
        return COULEURS_STATUT.get(self.statut, "bg-gray-100 text-gray-700")

    def save(self, *args, **kwargs):
        if self.pk:
            ancien = MissionControle.tous.get(pk=self.pk)
            if ancien.est_verrouillee:
                # to_python() normalise les valeurs encore sous forme brute (ex.
                # date_mission="2026-07-01" avant le premier full_clean) — sans
                # ça une valeur inchangée mais non coercée est vue à tort comme
                # une modification.
                date_mission = self._meta.get_field("date_mission").to_python(self.date_mission)
                if ancien.date_mission != date_mission:
                    raise ValidationError("Impossible de modifier 'date_mission' : mission verrouillée.")
                entite_controlee_id = self.entite_controlee_id
                if isinstance(entite_controlee_id, str):
                    entite_controlee_id = int(entite_controlee_id)
                if ancien.entite_controlee_id != entite_controlee_id:
                    raise ValidationError("Impossible de modifier 'entite_controlee' : mission verrouillée.")
        super().save(*args, **kwargs)


class MembreGroupeControleQuerySet(models.QuerySet):
    def chefs(self):
        return self.filter(role=RoleMission.CHEF)

    def agents(self):
        return self.filter(role=RoleMission.AGENT)


class MembreGroupeControle(models.Model):
    mission = models.ForeignKey(MissionControle, on_delete=models.CASCADE, related_name="membres_groupe")
    agent = models.ForeignKey("agents.AgentControleur", on_delete=models.PROTECT, related_name="participations")
    role = models.CharField(max_length=10, choices=RoleMission.choices, default=RoleMission.AGENT)

    history = HistoricalRecords()

    objects = MembreGroupeControleQuerySet.as_manager()

    class Meta:
        verbose_name = "Membre du groupe de contrôle"
        verbose_name_plural = "Membres du groupe de contrôle"
        unique_together = ("mission", "agent")
        constraints = [
            models.UniqueConstraint(
                fields=["mission"], condition=models.Q(role="chef"),
                name="un_seul_chef_par_mission",
            )
        ]

    def __str__(self):
        return f"{self.agent} ({self.get_role_display()}) — {self.mission}"

    def clean(self):
        if self.mission.est_verrouillee:
            raise ValidationError("Mission verrouillée.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.mission.est_verrouillee:
            raise ValidationError("Impossible de supprimer : mission verrouillée.")
        super().delete(*args, **kwargs)


class PersonneInterrogee(models.Model):
    """Personne interrogée pendant l'audit — distincte des `personnes_habilitees_*`
    de la Page 4 (personnes ayant accès aux données dans le cadre du traitement)."""

    mission = models.ForeignKey(MissionControle, on_delete=models.CASCADE, related_name="personnes_interrogees")
    personne = models.ForeignKey("personnes.Personne", on_delete=models.PROTECT, related_name="interrogatoires")
    poste_snapshot = models.CharField(max_length=255, blank=True)
    service_snapshot = models.CharField(max_length=255, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Personne interrogée"
        verbose_name_plural = "Personnes interrogées"

    def __str__(self):
        return f"{self.personne} — {self.mission}"

    def clean(self):
        if self.mission.est_verrouillee:
            raise ValidationError("Mission verrouillée après génération du rapport.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.mission.est_verrouillee:
            raise ValidationError("Impossible de supprimer : mission verrouillée.")
        super().delete(*args, **kwargs)


# Champs de chaque page pris en compte pour le calcul de progression par
# traitement : (champs communs à tous les traitements, {champ: {codes concernés}}
# pour les champs propres à certains traitements uniquement — voir
# reponse_traitement_fields.md). Centralisé ici pour ne pas dupliquer cette
# connaissance dans chaque template du questionnaire.
CHAMPS_PAGE_PAR_TRAITEMENT = {
    "page1": (
        ["declaration_effectuee", "numero_recepisse", "raison_collecte", "methode_consentement",
         "droits_respectes", "dispositions_legales_derogatoires"],
        {"type_objet_geolocalise": {"j"}, "desactivation_geoloc_pause": {"j"}},
    ),
    "page2": (
        ["contrat_sous_traitance", "contrat_sous_traitance_fichier", "nombre_sous_traitants",
         "entites_destinataires", "sous_traitants_declares", "transmission_support_physique",
         "transmission_mail", "transmission_protocole", "transmission_autres"],
        {"nombre_cameras": {"f", "g"}, "listing_cameras_disponible": {"f", "g"}},
    ),
    "page3": (
        ["donnees_identification", "donnees_comportement", "donnees_professionnelles",
         "donnees_situation_financiere", "donnees_deplacements", "donnees_complementaires",
         "origine_donnees", "destinataires_donnees", "duree_conservation"],
        {},
    ),
    "page4": (
        ["personnes_habilitees_noms", "personnes_habilitees_fonctions"],
        {
            "entites_interconnexion": {"i"}, "pays_transfert": {"h"}, "autorite_protection_pays": {"h"},
            "entite_destinataire_nom_adresse": {"h"}, "empreinte_pouces_index": {"e"},
            "empreinte_palmaire": {"e"}, "empreinte_faciale": {"e"}, "empreinte_autres": {"e"},
        },
    ),
    "page5": (["mesures_organisationnelles", "mesures_techniques"], {}),
}


def _est_rempli(valeur):
    if valeur is None:
        return False
    if isinstance(valeur, bool):
        return valeur is True
    if isinstance(valeur, str):
        return bool(valeur.strip())
    return bool(valeur)


class EvaluationConformite(models.TextChoices):
    """Verdict du contrôleur pour un traitement — alimente le tableau 3 du
    procès-verbal (missions/generate_pv.py)."""

    CTO = "cto", "Conformité totale"
    CPA = "cpa", "Conformité partielle"
    NC = "nc", "Non conforme"
    CPR = "cpr", "Constatation préoccupante"


COULEURS_VERDICT = {
    EvaluationConformite.CTO: "bg-green-100 text-green-800",
    EvaluationConformite.CPA: "bg-blue-100 text-blue-800",
    EvaluationConformite.NC: "bg-amber-100 text-amber-800",
    EvaluationConformite.CPR: "bg-red-100 text-red-800",
}


def _sous_traitance_declaree_applicable(reponse):
    return (reponse.page2.nombre_sous_traitants or 0) > 0


# Checklist utilisée pour SUGGÉRER un verdict (jamais l'imposer — le
# contrôleur reste responsable de la saisie finale, voir evaluation_page).
# Ne couvre que les champs qui sont de vrais signaux de conformité ; les
# champs purement descriptifs (catégories de données, moyen de transmission,
# type d'objet géolocalisé...) ne sont volontairement pas notés.
CRITERES_CONFORMITE = [
    {"label": "Déclaration effectuée", "test": lambda r: r.page1.declaration_effectuee},
    {"label": "Droits des personnes respectés", "test": lambda r: r.page1.droits_respectes},
    {
        "label": "Contrat de sous-traitance en place",
        "applicable": _sous_traitance_declaree_applicable,
        "test": lambda r: r.page2.contrat_sous_traitance,
    },
    {
        "label": "Sous-traitant(s) déclaré(s)",
        "applicable": _sous_traitance_declaree_applicable,
        "test": lambda r: r.page2.sous_traitants_declares,
    },
    {
        "label": "Listing des caméras disponible",
        "traitements": {"f", "g"},
        "test": lambda r: r.page2.listing_cameras_disponible,
    },
    {"label": "Mesures organisationnelles documentées", "test": lambda r: _est_rempli(r.page5.mesures_organisationnelles)},
    {"label": "Mesures techniques documentées", "test": lambda r: _est_rempli(r.page5.mesures_techniques)},
    {"label": "Personnes habilitées identifiées", "test": lambda r: _est_rempli(r.page4.personnes_habilitees_noms)},
    {"label": "Durée de conservation définie", "test": lambda r: _est_rempli(r.page3.duree_conservation)},
    {
        "label": "Autorité de protection du pays destinataire documentée",
        "traitements": {"h"},
        "test": lambda r: _est_rempli(r.page4.autorite_protection_pays),
    },
]


class ReponseTraitement(models.Model):
    """Ligne pivot (mission, traitement) — créée automatiquement à la
    création de la mission, voir missions/signals.py."""

    mission = models.ForeignKey(MissionControle, on_delete=models.CASCADE, related_name="reponses")
    traitement = models.CharField(max_length=1, choices=Traitement.choices)

    # Évaluation du contrôleur, saisie après le questionnaire et avant la
    # génération du PV — alimente le tableau 3 du procès-verbal.
    evaluation = models.CharField(max_length=3, choices=EvaluationConformite.choices, blank=True)
    observations_controleur = models.TextField(blank=True)
    observations_entite = models.TextField(blank=True)

    class Meta:
        verbose_name = "Réponse traitement"
        verbose_name_plural = "Réponses traitement"
        unique_together = ("mission", "traitement")
        ordering = ["traitement"]

    def __str__(self):
        return f"{self.mission} — {self.get_traitement_display()}"

    @property
    def est_verrouille(self):
        return self.mission.est_verrouillee

    def clean(self):
        if self.pk and self.est_verrouille:
            raise ValidationError("Évaluation verrouillée après génération du procès-verbal.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def pourcentage_complete(self):
        """Proportion des champs applicables à ce traitement qui sont
        renseignés (approximation : un booléen à False est considéré comme
        « non renseigné », même s'il peut s'agir d'une réponse négative
        volontaire — il n'existe pas de suivi « touché » distinct)."""
        total = 0
        remplis = 0
        for nom_page, (champs_communs, champs_conditionnels) in CHAMPS_PAGE_PAR_TRAITEMENT.items():
            page = getattr(self, nom_page, None)
            if page is None:
                continue
            champs = list(champs_communs)
            for champ, traitements in champs_conditionnels.items():
                if self.traitement in traitements:
                    champs.append(champ)
            for champ in champs:
                total += 1
                if _est_rempli(getattr(page, champ)):
                    remplis += 1
        if total == 0:
            return 0
        return round(remplis * 100 / total)

    def suggestion_verdict(self):
        """Suggestion de verdict de conformité à partir d'une checklist de
        signaux concrets (CRITERES_CONFORMITE) — jamais appliquée
        automatiquement, seulement affichée pour aide à la décision sur la
        page Évaluation. Le contrôleur saisit le verdict final lui-même."""
        details = []
        total = 0
        respectes = 0
        for critere in CRITERES_CONFORMITE:
            traitements = critere.get("traitements")
            if traitements is not None and self.traitement not in traitements:
                continue
            applicable = critere.get("applicable")
            if applicable is not None and not applicable(self):
                continue
            total += 1
            ok = bool(critere["test"](self))
            respectes += ok
            details.append({"label": critere["label"], "respecte": ok})

        if total == 0:
            return {"verdict": None, "verdict_label": None, "pourcentage": None, "details": details}

        pourcentage = round(respectes * 100 / total)
        if pourcentage == 100:
            verdict = EvaluationConformite.CTO
        elif pourcentage >= 70:
            verdict = EvaluationConformite.CPA
        elif pourcentage >= 40:
            verdict = EvaluationConformite.NC
        else:
            verdict = EvaluationConformite.CPR

        return {
            "verdict": verdict,
            "verdict_label": EvaluationConformite(verdict).label,
            "verdict_css_classes": COULEURS_VERDICT.get(verdict, ""),
            "pourcentage": pourcentage,
            "details": details,
        }


class ReponsePageMixin(models.Model):
    """Pattern de verrouillage commun aux 5 pages du questionnaire —
    appliqué au niveau modèle, jamais seulement dans les vues."""

    class Meta:
        abstract = True

    def clean(self):
        # self.reponse_id peut être vide pour un formulaire "extra" fabriqué
        # par un formset dont le TOTAL_FORMS dépasse le nombre de lignes
        # réelles (ex. management form trafiqué côté client) — dans ce cas
        # il n'y a pas de mission à verrouiller, on laisse les autres
        # validations du formulaire s'appliquer normalement.
        if self.reponse_id and self.reponse.est_verrouille:
            raise ValidationError("Mission verrouillée après génération du rapport.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.reponse_id and self.reponse.est_verrouille:
            raise ValidationError("Impossible de supprimer : mission verrouillée.")
        super().delete(*args, **kwargs)


class ReponsePage1(ReponsePageMixin, models.Model):
    """Conformité déclarative."""

    reponse = models.OneToOneField(ReponseTraitement, on_delete=models.CASCADE, related_name="page1")

    declaration_effectuee = models.BooleanField(default=False)
    numero_recepisse = models.CharField(max_length=255, blank=True)
    raison_collecte = models.TextField(blank=True)
    methode_consentement = models.TextField(blank=True)
    droits_respectes = models.BooleanField(default=False)
    dispositions_legales_derogatoires = models.BooleanField(default=False)
    type_objet_geolocalise = models.CharField(max_length=255, blank=True)  # j uniquement
    desactivation_geoloc_pause = models.BooleanField(default=False)  # j uniquement

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Réponse — Page 1"
        verbose_name_plural = "Réponses — Page 1"

    def __str__(self):
        return f"Page 1 — {self.reponse}"


class ReponsePage2(ReponsePageMixin, models.Model):
    """Vidéosurveillance & sous-traitance."""

    reponse = models.OneToOneField(ReponseTraitement, on_delete=models.CASCADE, related_name="page2")

    nombre_cameras = models.PositiveIntegerField(null=True, blank=True)  # f/g uniquement
    listing_cameras_disponible = models.BooleanField(default=False)  # f/g uniquement
    contrat_sous_traitance = models.BooleanField(default=False)
    contrat_sous_traitance_fichier = models.FileField(
        upload_to="contrats_sous_traitance/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(EXTENSIONS_CONTRAT_AUTORISEES),
            ValidateurTailleFichier(TAILLE_MAX_FICHIER_MO),
        ],
    )
    nombre_sous_traitants = models.PositiveIntegerField(null=True, blank=True)
    entites_destinataires = models.TextField(blank=True)
    sous_traitants_declares = models.BooleanField(default=False)
    transmission_support_physique = models.BooleanField(default=False)
    transmission_mail = models.BooleanField(default=False)
    transmission_protocole = models.BooleanField(default=False)
    transmission_autres = models.CharField(max_length=255, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Réponse — Page 2"
        verbose_name_plural = "Réponses — Page 2"

    def __str__(self):
        return f"Page 2 — {self.reponse}"


class ReponsePage3(ReponsePageMixin, models.Model):
    """Nature des données collectées."""

    reponse = models.OneToOneField(ReponseTraitement, on_delete=models.CASCADE, related_name="page3")

    donnees_identification = models.BooleanField(default=False)
    donnees_comportement = models.BooleanField(default=False)
    donnees_professionnelles = models.BooleanField(default=False)
    donnees_situation_financiere = models.BooleanField(default=False)
    donnees_deplacements = models.BooleanField(default=False)
    donnees_complementaires = models.BooleanField(default=False)
    origine_donnees = models.TextField(blank=True)
    destinataires_donnees = models.TextField(blank=True)
    duree_conservation = models.CharField(max_length=255, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Réponse — Page 3"
        verbose_name_plural = "Réponses — Page 3"

    def __str__(self):
        return f"Page 3 — {self.reponse}"


class ReponsePage4(ReponsePageMixin, models.Model):
    """Accès et transferts internationaux."""

    reponse = models.OneToOneField(ReponseTraitement, on_delete=models.CASCADE, related_name="page4")

    personnes_habilitees_noms = models.TextField(blank=True)
    personnes_habilitees_fonctions = models.TextField(blank=True)
    entites_interconnexion = models.TextField(blank=True)  # i uniquement
    pays_transfert = models.CharField(max_length=255, blank=True)  # h uniquement
    autorite_protection_pays = models.CharField(max_length=255, blank=True)  # h uniquement
    entite_destinataire_nom_adresse = models.TextField(blank=True)  # h uniquement
    empreinte_pouces_index = models.BooleanField(default=False)  # e uniquement
    empreinte_palmaire = models.BooleanField(default=False)  # e uniquement
    empreinte_faciale = models.BooleanField(default=False)  # e uniquement
    empreinte_autres = models.CharField(max_length=255, blank=True)  # e uniquement

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Réponse — Page 4"
        verbose_name_plural = "Réponses — Page 4"

    def __str__(self):
        return f"Page 4 — {self.reponse}"


class ReponsePage5(ReponsePageMixin, models.Model):
    """Mesures de sécurité."""

    reponse = models.OneToOneField(ReponseTraitement, on_delete=models.CASCADE, related_name="page5")

    mesures_organisationnelles = models.TextField(blank=True)
    mesures_techniques = models.TextField(blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Réponse — Page 5"
        verbose_name_plural = "Réponses — Page 5"

    def __str__(self):
        return f"Page 5 — {self.reponse}"


class JournalAction(models.Model):
    """Événements de workflow (création, génération rapport, upload scan,
    validation) — distinct de l'historique champ par champ (django-simple-history)."""

    mission = models.ForeignKey(MissionControle, on_delete=models.CASCADE, related_name="journal")
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    type_action = models.CharField(max_length=30, choices=TypeAction.choices)
    details = models.JSONField(default=dict, blank=True)
    horodatage = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Action journalisée"
        verbose_name_plural = "Journal des actions"
        ordering = ["-horodatage"]

    def __str__(self):
        return f"{self.get_type_action_display()} — {self.mission} ({self.horodatage:%Y-%m-%d %H:%M})"


def journaliser(mission, utilisateur, type_action, **details):
    return JournalAction.objects.create(
        mission=mission, utilisateur=utilisateur, type_action=type_action, details=details,
    )
