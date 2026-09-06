# Exemples de code — patterns établis du projet

Ce fichier centralise les patterns déjà validés dans les échanges de
conception. Objectif : rester cohérent avec l'existant plutôt que de
réinventer une variante à chaque nouveau modèle. À lire avant d'ajouter un
nouveau modèle, manager, vue ou règle de verrouillage.

---

## 1. `SoftDeleteMixin` (core/models.py)

Utilisé sur les modèles "catalogue" : `EntiteControlee`, `AgentControleur`,
`Personne`, `MissionControle`.

```python
from django.db import models
from django.utils import timezone

class SoftDeleteQuerySet(models.QuerySet):
    def actifs(self):
        return self.filter(supprime_le__isnull=True)

    def supprimes(self):
        return self.filter(supprime_le__isnull=False)

    def supprimer(self):
        return self.update(supprime_le=timezone.now())

    def restaurer(self):
        return self.update(supprime_le=None)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).actifs()


class TousManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class CorbeilleManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).supprimes()


class SoftDeleteMixin(models.Model):
    supprime_le = models.DateTimeField(null=True, blank=True, editable=False)

    objects = SoftDeleteManager()
    tous = TousManager()
    corbeille = CorbeilleManager()

    class Meta:
        abstract = True

    def delete(self, *args, using_hard_delete=False, **kwargs):
        if using_hard_delete:
            return super().delete(*args, **kwargs)
        self.supprime_le = timezone.now()
        self.save(update_fields=["supprime_le"])

    def restaurer(self):
        self.supprime_le = None
        self.save(update_fields=["supprime_le"])

    @property
    def est_supprime(self):
        return self.supprime_le is not None
```

Pattern d'application (fusionner avec un queryset métier existant) :

```python
class EntiteControleeQuerySet(SoftDeleteQuerySet):
    pass  # ajouter ici les filtres métier propres à EntiteControlee

class EntiteControleeManager(SoftDeleteManager):
    def get_queryset(self):
        return EntiteControleeQuerySet(self.model, using=self._db).actifs()

class EntiteControlee(SoftDeleteMixin, models.Model):
    nom = models.CharField(max_length=255)
    objects = EntiteControleeManager()
    tous = TousManager()
    corbeille = CorbeilleManager()
```

---

## 2. Permissions (core/permissions.py)

```python
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

GROUPE_ADMINISTRATEUR = "Administrateur"
GROUPE_CHEF_MISSION = "Chef de mission"
GROUPE_AGENT = "Agent contrôleur"

def est_dans_groupe(user, *groupes):
    return user.is_superuser or user.groups.filter(name__in=groupes).exists()


def require_groupe(*groupes):
    def decorateur(vue):
        @wraps(vue)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not est_dans_groupe(request.user, *groupes):
                raise PermissionDenied("Vous n'avez pas les droits nécessaires.")
            return vue(request, *args, **kwargs)
        return wrapper
    return decorateur


def require_membre_controle(vue):
    """Tout membre (chef ou agent) du groupe de contrôle de CE contrôle
    d'entité (ControleEntite) — le groupe est propre à chaque entité, pas à
    la mission entière."""
    @wraps(vue)
    @login_required
    def wrapper(request, controle_pk, *args, **kwargs):
        from missions.models import ControleEntite
        controle = get_object_or_404(ControleEntite, pk=controle_pk)
        request.controle = controle  # toujours défini, même pour un superuser
        if request.user.is_superuser:
            return vue(request, controle_pk, *args, **kwargs)
        est_membre = controle.membres_groupe.filter(agent__user=request.user).exists()
        if not est_membre:
            raise PermissionDenied("Vous n'êtes pas membre du groupe de contrôle de cette entité.")
        return vue(request, controle_pk, *args, **kwargs)
    return wrapper


def require_chef_controle(vue):
    """Uniquement le chef de CE contrôle d'entité (validation)."""
    @wraps(vue)
    @login_required
    def wrapper(request, controle_pk, *args, **kwargs):
        from missions.models import ControleEntite
        controle = get_object_or_404(ControleEntite, pk=controle_pk)
        request.controle = controle  # toujours défini, même pour un superuser
        if request.user.is_superuser:
            return vue(request, controle_pk, *args, **kwargs)
        est_chef = controle.membres_groupe.chefs().filter(agent__user=request.user).exists()
        if not est_chef:
            raise PermissionDenied("Seul le chef de mission peut valider ce contrôle.")
        return vue(request, controle_pk, *args, **kwargs)
    return wrapper
```

Commande `setup_groups` (core/management/commands/setup_groups.py) :

```python
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from core.permissions import GROUPE_ADMINISTRATEUR, GROUPE_CHEF_MISSION, GROUPE_AGENT

class Command(BaseCommand):
    help = "Crée les groupes et permissions de l'application APDPVP"

    def handle(self, *args, **options):
        administrateur, _ = Group.objects.get_or_create(name=GROUPE_ADMINISTRATEUR)
        chef, _ = Group.objects.get_or_create(name=GROUPE_CHEF_MISSION)
        agent, _ = Group.objects.get_or_create(name=GROUPE_AGENT)

        administrateur.permissions.set(Permission.objects.all())

        perms_chef = Permission.objects.filter(
            content_type__app_label__in=["missions", "personnes", "entites"],
        )
        chef.permissions.set(perms_chef)

        perms_agent = Permission.objects.filter(
            content_type__app_label__in=["missions", "personnes"],
            codename__in=[
                "view_missioncontrole", "change_reponsetraitement", "view_reponsetraitement",
                "add_personneinterrogee", "view_personneinterrogee",
            ],
        )
        agent.permissions.set(perms_agent)

        self.stdout.write(self.style.SUCCESS("Groupes et permissions créés."))
```

Usage dans les vues :

```python
@require_membre_controle
def remplir_questionnaire(request, controle_pk):
    ...

@require_chef_controle
def valider_controle(request, controle_pk):
    ...
```

---

## 3. Agents contrôleurs — provider mock/API (agents/services.py)

```python
from django.conf import settings

class BaseAgentProvider:
    def fetch_agents(self) -> list[dict]:
        raise NotImplementedError

class MockAgentProvider(BaseAgentProvider):
    def fetch_agents(self):
        return [
            {"id": "AG-001", "nom": "Obiang", "prenom": "Marie", "poste": "Contrôleur senior"},
            {"id": "AG-002", "nom": "Ndong", "prenom": "Paul", "poste": "Contrôleur"},
            {"id": "AG-003", "nom": "Mba", "prenom": "Sylvie", "poste": "Juriste"},
        ]

class ApiAgentProvider(BaseAgentProvider):
    def fetch_agents(self):
        import requests
        resp = requests.get(settings.AGENTS_API_URL, timeout=10,
                             headers={"Authorization": f"Bearer {settings.AGENTS_API_TOKEN}"})
        resp.raise_for_status()
        return resp.json()["agents"]

def get_agent_provider() -> BaseAgentProvider:
    if getattr(settings, "AGENTS_SOURCE", "mock") == "api":
        return ApiAgentProvider()
    return MockAgentProvider()
```

`AgentControleur.objects.sync_from_source()` appelle ce provider et fait un
`update_or_create` par `external_id`. `AGENTS_SOURCE` vaut `"mock"` en dev,
`"api"` en prod (settings.py).

---

## 4. Personne réutilisable multi-entités (personnes/models.py)

```python
class Fonction(models.Model):
    """Lien Personne <-> EntiteControlee : une personne peut avoir plusieurs
    fonctions dans plusieurs entités (ex: responsable de traitement chez
    plusieurs entreprises)."""
    personne = models.ForeignKey(Personne, on_delete=models.CASCADE, related_name="fonctions")
    entite = models.ForeignKey("entites.EntiteControlee", on_delete=models.CASCADE, related_name="fonctions")
    poste = models.CharField(max_length=255)
    service = models.CharField(max_length=255, blank=True)
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)  # null = fonction actuelle

    class Meta:
        unique_together = ("personne", "entite", "poste", "date_debut")
```

`PersonneInterrogee` garde une FK vers `Personne` + un **snapshot figé**
(`poste_snapshot`, `service_snapshot`) copié au moment de l'ajout au
contrôle, pour que le rapport reste fidèle même si la fonction change plus
tard.

---

## 5. Verrouillage post-génération — le pattern à reproduire

`ControleEntite` (pas `MissionControle`) porte le statut et le verrouillage
réel — voir `ControleEntite.est_verrouillee` (statut ≥ `pv_genere`). Trois
façons selon le type de relation, **toujours appliquées au niveau modèle**,
jamais seulement dans les vues.

### a) Champ simple sensible sur un objet PARENT (MissionControle.date_mission)

`MissionControle` n'a pas de statut propre — sa date reste modifiable tant
qu'aucune de ses entités n'est verrouillée, en interrogeant ses
`ControleEntite` enfants :

```python
def save(self, *args, **kwargs):
    if self.pk:
        ancien = MissionControle.tous.get(pk=self.pk)
        date_mission = self._meta.get_field("date_mission").to_python(self.date_mission)
        if ancien.date_mission != date_mission and self.controles_entites.filter(
            statut__gte=StatutMission.PV_GENERE
        ).exists():
            raise ValidationError("Impossible de modifier 'date_mission' : au moins un contrôle est verrouillé.")
    super().save(*args, **kwargs)
```

### b) Modèle enfant direct (`clean()`/`save()`/`delete()`) — pattern générique

Utilisé pour `PersonneInterrogee`, `MembreGroupeControle`, `ReponseTraitement`,
et les 5 `ReponsePageN` via `ReponsePageMixin` — chacun a une FK directe
(`controle` ou `reponse` → `controle`) vers `ControleEntite` :

```python
class ReponsePageMixin(models.Model):
    class Meta:
        abstract = True

    def clean(self):
        if self.reponse_id and self.reponse.est_verrouille:
            raise ValidationError("Contrôle verrouillé après génération du rapport.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.reponse_id and self.reponse.est_verrouille:
            raise ValidationError("Impossible de supprimer : contrôle verrouillé.")
        super().delete(*args, **kwargs)
```

⚠️ Piège avec les `ModelForm` : une contrainte DB (`UniqueConstraint`) qui
référence un champ **absent du formulaire** (ex. `controle` sur
`MembreGroupeControle`, fixé via `instance=` plutôt que saisi) n'est **pas**
vue par `form.is_valid()` — Django exclut de la validation les champs
absents du formulaire, `validate_constraints()` respecte cet exclude. La
violation ne se déclenche qu'au `.save()` réel : il faut l'attraper
explicitement dans la vue (`try/except ValidationError` autour de
`form.save()`), sinon c'est un 500 non géré — voir `membre_ajouter`
(`missions/views.py`) pour `un_seul_chef_par_controle`.

### c) Relation M2M avec `through` explicite (`MissionControle.entites_controlees`)

```python
class MissionControle(models.Model):
    entites_controlees = models.ManyToManyField(
        "entites.EntiteControlee", through="ControleEntite", related_name="missions",
    )

class ControleEntite(models.Model):
    mission = models.ForeignKey(MissionControle, on_delete=models.CASCADE, related_name="controles_entites")
    entite = models.ForeignKey("entites.EntiteControlee", on_delete=models.PROTECT, related_name="controles")
    statut = models.IntegerField(choices=StatutMission.choices, default=StatutMission.BROUILLON)
    # ... reste du circuit (PV, rapport, groupe, etc.)

    class Meta:
        unique_together = ("mission", "entite")

    @property
    def est_verrouillee(self):
        return self.statut >= StatutMission.PV_GENERE

    def delete(self, *args, **kwargs):
        if self.est_verrouillee:
            raise ValidationError("Impossible de retirer cette entité du contrôle : verrouillée.")
        super().delete(*args, **kwargs)
```

Avec un `through` explicite (contrairement à un `ManyToManyField` nu),
`ControleEntite` **est** le modèle pivot — `clean()`/`save()`/`delete()`
suffisent, pas besoin de signal `m2m_changed`. Condition : l'application ne
doit jamais appeler `.add()`/`.remove()`/`.set()` sur
`entites_controlees` pour des écritures (ces méthodes du manager M2M
contournent `ControleEntite.delete()`) — toujours créer/supprimer des
`ControleEntite` directement (`ControleEntite.objects.create(...)`,
`controle.delete()`). `entites_controlees` reste pratique en lecture
(`.all()`, `.filter()`, requêtes inverses `entite.missions`).

---

## 6. Traçabilité — simple_history + JournalAction

Installation :

```python
# settings.py
INSTALLED_APPS = [..., "simple_history"]
MIDDLEWARE = [..., "simple_history.middleware.HistoryRequestMiddleware"]
```

Sur chaque modèle suivi (`MissionControle`, `ReponsePage1..5`,
`PersonneInterrogee`, `MembreGroupeControle`) :

```python
from simple_history.models import HistoricalRecords

class ReponsePage1(ReponsePageMixin, models.Model):
    ...
    history = HistoricalRecords()
```

`JournalAction` pour les événements de workflow (pas les modifs de champ) —
rattaché à `ControleEntite`, pas à `MissionControle` (chaque entité a son
propre journal) :

```python
class TypeAction(models.TextChoices):
    CREATION = "creation", "Création du contrôle"
    QUESTIONNAIRE_COMPLETE = "questionnaire_complete", "Questionnaire complété"
    RAPPORT_GENERE = "rapport_genere", "Rapport généré"
    SCAN_UPLOAD = "scan_upload", "Scan signé uploadé"
    VALIDATION = "validation", "Contrôle validé"

class JournalAction(models.Model):
    controle = models.ForeignKey(ControleEntite, on_delete=models.CASCADE, related_name="journal")
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    type_action = models.CharField(max_length=30, choices=TypeAction.choices)
    details = models.JSONField(default=dict, blank=True)
    horodatage = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-horodatage"]
```

Helper d'écriture :

```python
def journaliser(controle, utilisateur, type_action, **details):
    JournalAction.objects.create(
        controle=controle, utilisateur=utilisateur,
        type_action=type_action, details=details,
    )
```

---

## 7. ReponseTraitement — pivot + création automatique

```python
class ReponseTraitement(models.Model):
    controle = models.ForeignKey(ControleEntite, on_delete=models.CASCADE, related_name="reponses")
    traitement = models.CharField(max_length=1, choices=Traitement.choices)

    class Meta:
        unique_together = ("controle", "traitement")

    @property
    def est_verrouille(self):
        return self.controle.est_verrouillee
```

Création automatique des 10 lignes + leurs 5 pages à la création du
`ControleEntite` — pas de `MissionControle` (missions/signals.py, connecté
dans `apps.py` → `ready()`) :

```python
@receiver(post_save, sender=ControleEntite)
def creer_reponses_traitements(sender, instance, created, **kwargs):
    if not created:
        return
    for code, _ in Traitement.choices:
        reponse = ReponseTraitement.objects.create(controle=instance, traitement=code)
        ReponsePage1.objects.create(reponse=reponse)
        ReponsePage2.objects.create(reponse=reponse)
        ReponsePage3.objects.create(reponse=reponse)
        ReponsePage4.objects.create(reponse=reponse)
        ReponsePage5.objects.create(reponse=reponse)
```

---

## 8. Formset par page (missions/forms.py + views.py)

```python
from django.forms import modelformset_factory

class ReponsePage1Form(forms.ModelForm):
    class Meta:
        model = ReponsePage1
        exclude = ["reponse"]

Page1FormSet = modelformset_factory(ReponsePage1, form=ReponsePage1Form, extra=0)
```

```python
@require_membre_controle
def questionnaire_page(request, controle_pk, page):
    controle = request.controle
    queryset = ReponsePage1.objects.filter(reponse__controle=controle).order_by("reponse__traitement")
    if page == 1:
        # Seuls les traitements cochés à la checkliste sont détaillés.
        queryset = queryset.filter(declaration_effectuee=True)

    if request.method == "POST":
        formset = Page1FormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            journaliser(controle, request.user, TypeAction.QUESTIONNAIRE_COMPLETE, page="page1")
            return redirect("missions:questionnaire_page", controle_pk=controle.pk, page=2)
    else:
        formset = Page1FormSet(queryset=queryset)

    return render(request, "missions/questionnaire_page1.html", {"controle": controle, "formset": formset})
```

Dans le template : `zip(formset.forms, queryset)` pour afficher le libellé
du traitement (`get_traitement_display`) à côté de chaque ligne, et masquer
en JS/HTMX les champs propres à un seul traitement (ex.
`type_objet_geolocalise` visible seulement sur la ligne j).
