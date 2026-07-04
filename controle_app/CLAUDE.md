# APDPVP — Missions de contrôle

## Contexte
Application Django pour l'Autorité de Protection des Données Personnelles
et de la Vie Privée (Gabon). Gère les missions de contrôle : création,
questionnaire d'audit (5 pages, 10 types de traitements), génération de
rapport Word/PDF, signature, validation.

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
missions/     # MissionControle, MembreGroupeControle, PersonneInterrogee,
              # ReponseTraitement + ReponsePage1..5, JournalAction,
              # views.py (dashboard + questionnaire + clôture), forms.py
entites/      # EntiteControlee
personnes/    # Personne, Fonction (une personne peut avoir des fonctions
              # dans plusieurs EntiteControlee)
agents/       # AgentControleur, AgentProvider (Mock/Api)
templates/    # base.html (Tailwind + htmx en CDN), index.html,
              # registration/login.html, missions/*.html
```

Dashboard et questionnaire sont servis sous `/missions/` ; `/` est une page
d'accueil publique qui redirige vers `/missions/` si déjà connecté.

## Conventions spécifiques au projet
(pas de rappel du Django standard — uniquement ce qui n'est pas déductible du code)

- **Managers** : pattern à 3 managers sur les modèles avec `SoftDeleteMixin`
  (`objects` = actifs, `tous` = tout, `corbeille` = supprimés).
- **Circuit de clôture** : à la fin du questionnaire, un **procès-verbal (PV)**
  est généré en premier — c'est lui qui verrouille la mission. Le PV est
  imprimé, signé, puis son scan est uploadé. C'est seulement à partir du PV
  signé que le **rapport final** est généré (jamais l'inverse) ; le rapport
  suit le même aller-retour (imprimé, signé, scan uploadé) avant validation.
  Statuts dans l'ordre : `questionnaire_complete` → `pv_genere` →
  `pv_scan_uploade` → `rapport_genere` → `rapport_scan_uploade` → `validee`.
- **Verrouillage post-génération** : dès que `mission.est_verrouillee` est vrai
  (statut ≥ `pv_genere`), les éléments suivants deviennent immuables :
  `date_mission`, `entite_controlee`, `PersonneInterrogee`,
  `MembreGroupeControle`, toutes les `ReponsePage1..5`.
  Appliqué via `clean()`/`save()`/`delete()` sur chaque modèle concerné —
  jamais seulement au niveau des vues.
- **Traçabilité** : `django-simple-history` sur les modèles de réponses
  (modifications champ par champ) + `JournalAction` pour les événements de
  workflow (création mission, PV généré, scan uploadé, rapport généré,
  validation).
- **Permissions** : groupes Django (`Administrateur` / `Chef de mission` /
  `Agent contrôleur`) définis dans `core/permissions.py`, combinés à des
  permissions contextuelles par mission (`require_membre_mission`,
  `require_chef_mission`) — un agent peut remplir le questionnaire de
  n'importe quelle mission dont il est membre, mais seul le chef de la
  mission peut la valider.
- **Groupe de contrôle** : une mission a un seul chef (`MembreGroupeControle.role`,
  contrainte DB `un_seul_chef_par_mission`) et un ou plusieurs agents.
- **ReponseTraitement** : une ligne pivot par `(mission, traitement)` créée
  automatiquement à la création de la mission (signal `post_save`), avec 5
  sous-modèles en `OneToOne` (un par page du questionnaire d'origine).
  Certains champs ne sont pertinents que pour certains traitements
  (géolocalisation, biométrie, vidéosurveillance, interconnexion,
  transfert) — voir `reponse_traitement_fields.md`.

## Documents de référence (progressive disclosure)

### Détail des champs du questionnaire — `reponse_traitement_fields.md`
**À lire quand :** travail sur `ReponsePage1` à `ReponsePage5`, le formulaire
HTMX du questionnaire, ou l'analyse de conformité par traitement.

### Exemples de code du projet — `code_examples.md`
**À lire quand :** besoin de rester cohérent avec les patterns déjà établis
(SoftDeleteMixin, permissions, signaux de verrouillage, managers, formsets).
Ne pas réinventer ces patterns — les reproduire.

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
- [ ] **Règles de calcul de conformité automatique** par traitement (a→j) à
      partir des réponses `ReponsePage1..5` — pour l'instant le verdict
      (CTO/CPA/NC/CPR) est saisi manuellement par le contrôleur, pas déduit
      des réponses au questionnaire.
- [ ] Spécification de l'API agents en production (`ApiAgentProvider`) : URL,
      authentification, format JSON réel — `AGENTS_SOURCE=mock` reste actif
      par défaut
- [ ] Déploiement (même infra VPS/Docker/Traefik qu'Institut Prométhée, ou séparé ?)

## Décisions déjà tranchées (ne pas rouvrir sans raison)

- JSONField écarté au profit d'un schéma relationnel (traçabilité/intégrité)
- Soft-delete uniquement sur les modèles "catalogue"
  (`EntiteControlee`, `AgentControleur`, `Personne`, `MissionControle`) —
  pas sur `PersonneInterrogee`/`MembreGroupeControle`/`ReponseTraitement`
  (déjà protégés par le verrouillage post-génération)
- `django-simple-history` + `JournalAction` (double dispositif : champ par
  champ / événements métier), pas de solution unique
