# APDPVP — Missions de contrôle

## Contexte
Application Django pour l'Autorité de Protection des Données Personnelles
et de la Vie Privée (Gabon). Gère les missions de contrôle : une mission
(créée par l'admin) regroupe une ou plusieurs entités contrôlées, chacune
avec son propre groupe de contrôle, sa checkliste de traitements déclarés,
son questionnaire d'audit (5 pages, 10 types de traitements), sa génération
de PV/rapport Word/PDF, sa signature et sa validation — indépendamment des
autres entités de la même mission (voir `ControleEntite` ci-dessous).

Projet distinct et sans lien avec l'application Institut Prométhée.

## Setup

```
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
cp .env.example .env                                # puis éditer SECRET_KEY etc.
python manage.py migrate
python manage.py seed_dev          # comptes + agents + entité de démo (DEBUG uniquement, voir plus bas)
python manage.py runserver
```

## Commandes
```
python manage.py runserver
python manage.py test
python manage.py setup_groups      # crée les groupes/permissions Django
python manage.py sync_agents       # synchronise les agents (mock en dev, API en prod)
python manage.py seed_missions     # 60 missions de démo (1 entité chacune) réparties sur 3 ans (DEBUG uniquement, appelle seed_dev)
python manage.py seed2             # 11 missions de démo couvrant chaque statut du circuit + 2 multi-entités,
                                    # entités sectorisées, ordre de mission joint (DEBUG uniquement, appelle seed_dev)
```

Config Django dans `config/` (settings via `python-dotenv`, lit `.env` à la
racine). Base SQLite par défaut en dev (`db/missions.sqlite3`), PostgreSQL en
prod via `DB_ENGINE=postgresql` + `DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`
(voir `.env.example`).

## Comptes de test (dev local uniquement)

`python manage.py seed_dev` (refuse de tourner si `DEBUG=False`) crée des
identifiants fixes pour tester manuellement les permissions par rôle — voir
`core/management/commands/seed_dev.py` et `GUIDE_TEST_UI.md` :

| Compte       | Mot de passe | Rôle                                                                 |
|--------------|--------------|------------------------------------------------------------------------|
| `admin`      | `admin1234`  | Superuser (bypass toutes permissions)                                  |
| `chef_test`  | `test1234`   | Lié à l'agent mock AG-001 (Obiang Marie), groupe « Chef de mission »   |
| `agent_test` | `test1234`   | Lié à l'agent mock AG-002 (Ndong Paul), groupe « Agent contrôleur »    |

Idempotent (relançable sans dupliquer). Crée aussi une entité de démo
« ACME SA (démo) ».

## Structure
```
config/       # settings.py (python-dotenv), urls.py, wsgi.py, asgi.py
core/         # SoftDeleteMixin, permissions.py, validators.py, seed_dev,
              # vue index (page d'accueil publique à "/")
missions/     # MissionControle (conteneur admin) ; ControleEntite (le
              # circuit complet d'UNE entité — statut, groupe, PV/rapport) ;
              # MembreGroupeControle, PersonneInterrogee, ReponseTraitement +
              # ReponsePage1..5, JournalAction — tous rattachés à
              # ControleEntite, pas à MissionControle ; views.py
              # (dashboard + questionnaire + clôture), forms.py
entites/      # EntiteControlee
personnes/    # Personne, Fonction (une personne peut avoir des fonctions
              # dans plusieurs EntiteControlee)
agents/       # AgentControleur, AgentProvider (Mock/Api)
templates/    # base.html (Tailwind + htmx en CDN), index.html,
              # registration/login.html, missions/*.html
```

Dashboard et questionnaire sont servis sous `/missions/` ; `/` est une page
d'accueil publique qui redirige vers `/missions/` si déjà connecté.

`/missions/<mission_pk>/` est la **vue d'ensemble** de la mission (liste des
entités, chacune avec son statut et son groupe — gérée par l'admin).
`/missions/controles/<controle_pk>/` est **l'espace de travail d'une
entité** (checkliste, questionnaire, évaluation, PV/rapport/validation) —
rempli par les membres du groupe de contrôle de CETTE entité.

## Conventions spécifiques au projet
(pas de rappel du Django standard — uniquement ce qui n'est pas déductible du code)

- **Managers** : pattern à 3 managers sur les modèles avec `SoftDeleteMixin`
  (`objects` = actifs, `tous` = tout, `corbeille` = supprimés) — uniquement
  `MissionControle`, `EntiteControlee`, `AgentControleur`, `Personne`
  (modèles "catalogue", voir Décisions déjà tranchées).
- **MissionControle vs ControleEntite** : `MissionControle` est un conteneur
  administratif créé par l'admin (date, ordre de mission, entités
  concernées) — il n'a **pas** de statut propre stocké.
  `MissionControle.entites_controlees` est un `ManyToManyField` vers
  `EntiteControlee` **via `through="ControleEntite"`** : une ligne
  `ControleEntite` (mission, entite) porte tout le reste — statut, groupe de
  contrôle, checkliste/questionnaire, évaluation, PV/rapport/signatures.
  Chaque entité progresse dans son **propre circuit indépendant** ; deux
  entités de la même mission peuvent être à des statuts différents.
  `MissionControle.statut_general` (propriété calculée, jamais stockée) =
  le minimum des statuts de ses `ControleEntite` — vue agrégée pour le
  suivi/les statistiques uniquement, jamais utilisée pour des décisions de
  permission ou de workflow.
- **Circuit de clôture** (par `ControleEntite`) : à la fin du questionnaire,
  un **procès-verbal (PV)** est généré en premier — c'est lui qui verrouille
  ce contrôle. Le PV est imprimé, signé, puis son scan est uploadé. C'est
  seulement à partir du PV signé que le **rapport final** est généré (jamais
  l'inverse) ; le rapport suit le même aller-retour (imprimé, signé, scan
  uploadé) avant validation. Statuts dans l'ordre : `questionnaire_complete`
  → `pv_genere` → `pv_scan_uploade` → `rapport_genere` →
  `rapport_scan_uploade` → `validee`.
- **Verrouillage post-génération** : dès que `controle.est_verrouillee` est
  vrai (statut ≥ `pv_genere`), les éléments suivants deviennent immuables :
  `MissionControle.date_mission` (si au moins un `ControleEntite` de la
  mission est verrouillé), `PersonneInterrogee`, `MembreGroupeControle`,
  toutes les `ReponsePage1..5`, et le `ControleEntite` lui-même devient
  non supprimable (retirer l'entité de la mission). Appliqué via
  `clean()`/`save()`/`delete()` sur chaque modèle concerné — jamais
  seulement au niveau des vues (voir `code_examples.md` §5, y compris le
  cas `ManyToManyField` avec `through` explicite : plus besoin de signal
  `m2m_changed`, `ControleEntite.delete()` suffit).
- **Création de mission réservée à l'admin** : `mission_create` est protégée
  par `@require_groupe(GROUPE_ADMINISTRATEUR)` (superuser ou groupe
  « Administrateur ») — crée la mission et un `ControleEntite` (statut
  `BROUILLON`) par entité sélectionnée/déclarée, sans groupe de contrôle
  assigné. L'admin affecte ensuite le groupe de chaque entité (et peut en
  ajouter d'autres via `entite_ajouter`) depuis `/missions/<mission_pk>/`.
- **Traçabilité** : `django-simple-history` sur les modèles de réponses
  (modifications champ par champ) + `JournalAction` (rattaché à
  `ControleEntite`) pour les événements de workflow (création du contrôle,
  PV généré, scan uploadé, rapport généré, validation).
- **Permissions** : groupes Django (`Administrateur` / `Chef de mission` /
  `Agent contrôleur`) définis dans `core/permissions.py`, combinés à des
  permissions contextuelles **par `ControleEntite`**
  (`require_membre_controle`, `require_chef_controle`, posent
  `request.controle`) — un agent peut remplir le questionnaire de n'importe
  quel contrôle d'entité dont il est membre, mais seul le chef de CE
  contrôle peut le valider ; pas de chef global de mission. `mission_detail`
  (vue d'ensemble) reste accessible à l'admin ou à tout membre d'au moins un
  des contrôles de la mission (logique inline dans la vue, pas de décorateur
  dédié).
- **Groupe de contrôle** : chaque `ControleEntite` a un seul chef
  (`MembreGroupeControle.role`, contrainte DB `un_seul_chef_par_controle`)
  et un ou plusieurs agents. ⚠️ Cette contrainte référence `controle`, un
  champ absent de `MembreGroupeControleForm` — Django exclut donc les
  champs absents du formulaire de la validation par `form.is_valid()`
  (`validate_constraints` respecte cet `exclude`), la violation ne se
  déclenche qu'au `.save()` : `membre_ajouter` doit attraper ce
  `ValidationError` explicitement (pas seulement `if form.is_valid()`).
- **ReponseTraitement** : une ligne pivot par `(controle, traitement)` créée
  automatiquement à la création du `ControleEntite` (signal `post_save`),
  avec 5 sous-modèles en `OneToOne` (un par page du questionnaire
  d'origine). Certains champs ne sont pertinents que pour certains
  traitements (géolocalisation, biométrie, vidéosurveillance,
  interconnexion, transfert) — voir `reponse_traitement_fields.md`.
- **Checkliste des traitements déclarés** (`questionnaire_checklist`, avant
  la page 1) : coche `ReponsePage1.declaration_effectuee` pour chacun des 10
  traitements — les pages 1 à 5 ne détaillent ensuite que les traitements
  cochés (`questionnaire_page` filtre sur `declaration_effectuee=True`). Les
  traitements non cochés sont directement classés `evaluation=NC` (sauf s'ils
  ont déjà une évaluation — jamais écrasée), cohérent avec la règle « tout
  traitement non déclaré est non conforme » de `suggestion_verdict()`. La
  page d'évaluation (`evaluation_page`) continue elle de lister les 10
  traitements, déclarés ou non.

## Documents de référence (progressive disclosure)

### Détail des champs du questionnaire — `reponse_traitement_fields.md`
**À lire quand :** travail sur `ReponsePage1` à `ReponsePage5`, le formulaire
HTMX du questionnaire, ou l'analyse de conformité par traitement.

### Exemples de code du projet — `code_examples.md`
**À lire quand :** besoin de rester cohérent avec les patterns déjà établis
(SoftDeleteMixin, permissions, signaux de verrouillage, managers, formsets).
Ne pas réinventer ces patterns — les reproduire.

### Suggestion de conformité — `calcul_conformite.md`
**À lire quand :** modification de `CRITERES_CONFORMITE`/des seuils dans
`missions/models.py`, ou implémentation d'un vrai calcul de conformité
automatique. Explique la checklist, les seuils CTO/CPA/NC/CPR et pourquoi
certains champs du questionnaire ne sont volontairement pas notés.

## Tâches en attente

Voir `AVANCEMENT.md` pour le détail à jour de ce qui est fait/pas fait.

- [x] **Génération du procès-verbal** — `missions/generate_pv.py` (fourni par
      l'utilisateur, python-docx + WeasyPrint) génère un vrai `.docx` (et
      `.pdf` si WeasyPrint est disponible) à partir des données de la
      mission ; branché sur `pv_marquer_genere`. Verdict par traitement
      (conformité totale/partielle/non conforme/constatation préoccupante) +
      observations saisis manuellement via la page « Évaluation »
      (`ReponseTraitement.evaluation`) — pas de calcul automatique.
- [ ] **Template du rapport final Word** (distinct du PV, toujours en
      attente) + son parseur. `rapport_marquer_genere` (vue chef) ne fait
      encore que changer le statut sans document généré — étape provisoire
      à remplacer.
- [x] **Suggestion de conformité** par traitement (a→j) —
      `ReponseTraitement.suggestion_verdict()` calcule un verdict indicatif
      (CTO/CPA/NC/CPR, seuils 100/70/40 %) à partir d'une checklist de
      champs signifiants (`CRITERES_CONFORMITE`), affiché sur la page
      Évaluation avec bouton « Reprendre la suggestion ». Le contrôleur
      reste seul responsable du verdict final saisi — jamais appliqué
      automatiquement. Checklist et seuils à ajuster si besoin (voir
      `AVANCEMENT.md`).
- [ ] Spécification de l'API agents en production (`ApiAgentProvider`) : URL,
      authentification, format JSON réel — `AGENTS_SOURCE=mock` reste actif
      par défaut
- [ ] Déploiement (même infra VPS/Docker/Traefik qu'Institut Prométhée, ou séparé ?)

## Décisions déjà tranchées (ne pas rouvrir sans raison)

- JSONField écarté au profit d'un schéma relationnel (traçabilité/intégrité)
- Soft-delete uniquement sur les modèles "catalogue"
  (`EntiteControlee`, `AgentControleur`, `Personne`, `MissionControle`) —
  pas sur `ControleEntite`/`PersonneInterrogee`/`MembreGroupeControle`/
  `ReponseTraitement` (déjà protégés par le verrouillage post-génération)
- Un seul chef par `ControleEntite`, jamais de chef global de mission —
  chaque entité contrôlée est auditée par un groupe qui lui est propre
- `django-simple-history` + `JournalAction` (double dispositif : champ par
  champ / événements métier), pas de solution unique
