# PROGRESSION — APDPVP RH (rh_app)

État d'avancement de l'application **Ressources Humaines** du projet APDPVP 2026.
Stack : **Django 6** + **HTMX** + **Tailwind (CDN)** + **SQLite** (dev).

Dernière mise à jour : 2026-06-28.

---

## 1. Vue d'ensemble

Application RH modulaire (1 app Django par domaine), navigation **HTMX** sans rechargement,
soft delete généralisé, gestion des rôles/permissions, et génération de documents PDF.

```
rh_conf/         # configuration projet (settings, urls, wsgi/asgi)
core/            # socle : soft delete, managers, rôles, admin mixin, gestion des rôles (UI)
dashboard/       # tableau de bord + navigation latérale
employees/       # employés + départements
recruitment/     # offres d'emploi + candidats
leaves/          # demandes de congé
training/        # formations
documents/       # documents RH
actes/           # actes administratifs (nomenclature Gabon + PDF)
templates/       # base, partials, formulaire mutualisé, templates par app
```

---

## 2. Fonctionnalités livrées ✅

### Socle technique (`core`)
- **Soft delete** réutilisable (`SoftDeleteModel`) : `is_deleted`, `deleted_at` + horodatage `created_at`/`updated_at`.
  - Managers : `objects` (actifs uniquement) / `all_objects` (tout).
  - Méthodes : `delete()` (logique), `hard_delete()` (physique), `restore()`.
- **Admin** `SoftDeleteAdmin` : voit les supprimés, actions Supprimer / Restaurer / Supprimer définitivement.
- **Rôles** (groupes Django) : `admin`, `superuser`, `directeur`, `chef_service`, `agent_rh`, `usager`.
  - Commande `init_roles` (création + permissions).
  - **Onglet « Rôles »** : affecter / retirer un utilisateur à un rôle (HTMX), réservé admin/directeur.
  - Commande `seed_users` : comptes de démo (dont un superutilisateur `admin`).

### Authentification & sécurité
- **Login / logout** (vues Django, template `registration/login.html`).
- **Protection globale** via `LoginRequiredMiddleware` (toutes les vues exigent une connexion ; `login` exemptée).
- **Restriction par rôle** (`role_required`) : onglets **Rôles** et **Journal d'audit** réservés à admin / superuser / directeur.
- **Journal d'audit** (`AuditLog`, immuable) : enregistre automatiquement créations / modifications / suppressions (soft & hard) / restaurations + connexions / déconnexions / échecs, avec auteur, IP, diff des champs.
  - Capté via signaux + `AuditContextMiddleware` (utilisateur courant). Page **« Journal d'audit »** (filtre action + recherche) + admin lecture seule.
- **SSO JWT inter-services** (`core/jwt_utils.py`, `JWTAuthenticationMiddleware`) :
  - consomme un `Authorization: Bearer <token>` ou cookie `access_token` signé avec `JWT_SECRET_KEY` partagée, crée/synchronise l'utilisateur local (email, rôles, superuser).
  - endpoint `/roles/token/` pour émettre un token (utilisateur connecté).
  - Contrat de payload documenté dans `core/jwt_utils.py` (à respecter côté `auth_app`).
- **Liaison `Employee` ↔ compte `User`** (OneToOne) pour relier RH et connexion.
- **Unicité de l'email** garantie uniquement sur les employés **actifs** (contrainte conditionnelle `is_deleted=False`) → un email peut être réutilisé après suppression logique.

### Configuration

- Variables d'environnement via **python-dotenv** (`.env`, `.env.example`).
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `JWT_SECRET_KEY` (clé partagée inter-services, cf. CLAUDE.md).

### CRUD complet (création / modification / suppression soft + HTMX)
| Module | Modèle(s) | Particularités |
|---|---|---|
| Employés | `Department`, `Employee` | recherche temps réel, `date_naissance`, propriétés âge/ancienneté/anniversaires |
| Recrutement | `JobPosting`, `Candidate` | CRUD séparé offres + candidats |
| Congés | `LeaveRequest` | + approbation/refus HTMX (badge live) |
| Formations | `TrainingProgram` | participants (M2M) |
| Documents | `Document` | upload de fichier |
| Actes administratifs | `ActeAdministratif` | voir ci-dessous |

### Tableau de bord
- Cartes stats : employés actifs, congés en attente, offres ouvertes, actes administratifs.
- 🎂 Prochains anniversaires (≤ 30 j), 🏅 anniversaires de service.
- Prochaines formations, actes récents.

### Actes administratifs (`actes`)
- **Nomenclature complète adaptée au Gabon** : 14 catégories / 105 types (CNSS, CNAMGS, IRPP, ONE…), menu groupé (`optgroup`).
- **Pièce jointe = document signé scanné** (PDF/JPG/PNG), **obligatoire** dès le statut Émis / Signé / Archivé.
- **Référence auto** `ACT-<année>-NNN` générée si laissée vide (commande `backfill_references` pour l'existant).
- **Export PDF** imprimable (mise en page officielle) à signer puis re-scanner.
- Recherche + filtre par type (HTMX).

---

## 3. Données de démo
Fixture unique : `employees/fixtures/demo.json` (37 objets) — départements, 8 employés (avec dates de naissance),
offres, candidats, congés, formations, documents, 5 actes administratifs.

```bash
python manage.py loaddata demo
```

---

## 4. Commandes utiles

```bash
python manage.py runserver 8001        # lancer (port RH, cf. CLAUDE.md)
python manage.py loaddata demo         # (re)charger les données de démo
python manage.py init_roles            # créer rôles + permissions
python manage.py seed_users            # comptes de démo (mdp : apdpvp2026)
python manage.py seed_referentiels     # catégories pro, statuts agent, postes, types de contrat
python manage.py seed_agents_details   # enrichit les agents démo (matricules, contrats, diplômes...)
python manage.py seed_remuneration     # taux CNSS/CNAMGS + salaire de base par agent
python manage.py generer_rappels       # génère les rappels J-30 (à planifier quotidiennement)
python manage.py backfill_references   # référencer les actes sans référence
```

Séquence complète de (re)construction de la démo :
`flush` → `loaddata demo` → `init_roles` → `seed_users` → `seed_referentiels` →
`seed_agents_details` → `seed_remuneration` → `generer_rappels`.

## Modules récents (spec « Infos RH »)

- **Actes** : ajout `attestation_conge` et `attestation_stage`.
- **Carrière** (`carriere`) : évaluations + avancements (met à jour la catégorie de l'agent) + génération de **fiches de poste PDF**.
- **Rappels** (`rappels`) : moteur J-30 (`generer_rappels`) — anniversaires, anniversaires de service, fins de contrat, congés à venir, avancements à examiner ; badge de navigation + bandeau d'alertes sur le dashboard ; idempotent.
- **Rémunérations** (`remuneration`, réservé admin/directeur/chef de service) : historique des salaires, primes, avances, taux de cotisation (CNSS/CNAMGS), **calcul des droits** (brut → cotisations → net) + **bulletin de paie PDF**.

Comptes de démo : `admin` (superuser), `directeur`, `chef.rh`, `agent.rh1`, `agent.rh2`, `usager1` (mot de passe `apdpvp2026`).

---

## 5. Réalisé récemment ✅

- [x] **Authentification & protection des vues** (login/logout, `LoginRequiredMiddleware`, restriction onglet Rôles/Audit aux admins/directeurs).
- [x] **Intégration JWT inter-services** (PyJWT, middleware de consommation + endpoint d'émission, clé `JWT_SECRET_KEY` partagée).
- [x] **Liaison `Employee` ↔ compte `User`** (OneToOne).
- [x] **Unicité de l'email** seulement sur les employés actifs (contrainte conditionnelle soft-delete).
- [x] **Journal d'audit** (`AuditLog`) automatique + page de consultation.

## 6. Reste à faire / pistes 🔜

- [ ] Côté `auth_app` : émettre des JWT conformes au contrat (même `JWT_SECRET_KEY`, payload `core/jwt_utils.py`).
- [ ] Recherche/filtre HTMX sur les autres listes (déjà sur employés, actes, audit).
- [ ] Pagination des listes.
- [ ] **Dockerisation** (Dockerfile + docker-compose, réseau `rh_net`/`traefik_net`, cf. CLAUDE.md).
- [ ] Remplacer Tailwind CDN par un build, passer SQLite → PostgreSQL en prod.
- [ ] Tests automatisés (actuellement validés manuellement via le client de test).
- [ ] Changer le mot de passe de démo et les `SECRET_KEY`/`JWT_SECRET_KEY`.

---

## 7. Dépendances (`requirements.txt`)

django, django-htmx, django-crispy-forms, crispy-tailwind, pillow, python-dotenv, xhtml2pdf, PyJWT.
