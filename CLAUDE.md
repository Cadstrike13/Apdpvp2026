# CLAUDE.md — Infrastructure Docker · APDPVP 2026

Ce fichier décrit l'infrastructure de déploiement du projet APDPVP 2026 : réseau Docker, volumes, Traefik et organisation par service. Il sert de référence pour toute modification ou ajout d'un service.

---

## Vue d'ensemble

```
Internet
    │
    ▼
[Traefik] ── réseau : traefik_net (commun à tous les services)
    │
    ├── auth.apdpvp.local  ──► auth_app      (Django, port 8000)
    ├── rh.apdpvp.local    ──► rh_app        (Django, port 8001)  ◄── apdpvp-rh (React)
    ├── missions.apdpvp.local ─► missions_controle (Django)
    ├── depanage.apdpvp.local ─► depanage_demo    (Spring Boot, port 8083)
    └── questure.apdpvp.local ─► Questure         (Spring Boot, port 8082)
```

---

## Réseaux Docker

Chaque application possède son propre réseau isolé. Traefik est connecté à tous via un réseau commun.

| Réseau            | Rôle                                      | Services connectés                        |
|-------------------|-------------------------------------------|-------------------------------------------|
| `traefik_net`     | Réseau commun — entrée Traefik            | traefik + tous les services               |
| `auth_net`        | Réseau isolé de auth_app                  | auth_app                                  |
| `rh_net`          | Réseau isolé de rh_app + frontend         | rh_app, apdpvp-rh                         |
| `depanage_net`    | Réseau isolé de depanage_demo             | depanage_demo                             |
| `questure_net`    | Réseau isolé de Questure                  | questure                                  |
| `missions_net`    | Réseau isolé de missions_controle         | missions_controle                         |

> **Règle** : un service n'est jamais connecté au réseau isolé d'un autre service. La communication inter-services passe uniquement par les tokens JWT, pas par appel réseau direct.

---

## Traefik

Un seul fichier `traefik.yml` (ou `docker-compose.traefik.yml`) partagé par tous les services.

### Routage

| Hôte                       | Service cible       | Port interne |
|----------------------------|---------------------|--------------|
| `apdpvp.local`             | auth_app            | 8000         |
| `auth.apdpvp.local`        | auth_app            | 8000         |
| `rh.apdpvp.local`          | rh_app              | 8001         |
| `app.apdpvp.local`         | apdpvp-rh (React)   | 3000         |
| `depanage.apdpvp.local`    | depanage_demo       | 8083         |
| `questure.apdpvp.local`    | questure            | 8082         |
| `missions.apdpvp.local`    | missions_controle   | 8002         |

### Labels Traefik type (à appliquer sur chaque service)

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.<service>.rule=Host(`<subdomain>.apdpvp.local`)"
  - "traefik.http.routers.<service>.entrypoints=web"
  - "traefik.http.services.<service>.loadbalancer.server.port=<port>"
  - "traefik.docker.network=traefik_net"
```

---

## Volumes par service

### auth_app (Django SSO)

| Volume                  | Chemin conteneur           | Contenu                        |
|-------------------------|----------------------------|--------------------------------|
| `auth_db`               | `/app/db/auth.sqlite3`     | Base de données SQLite         |
| `auth_media`            | `/app/media/`              | Photos de profil (`avatars/`)  |
| `auth_static`           | `/app/staticfiles/`        | Fichiers statiques collectés   |

### rh_app (Django RH)

| Volume                  | Chemin conteneur           | Contenu                             |
|-------------------------|----------------------------|-------------------------------------|
| `rh_db`                 | `/app/db/rh.sqlite3`       | Base de données SQLite              |
| `rh_media`              | `/app/media/`              | Documents RH uploadés               |
| `rh_static`             | `/app/staticfiles/`        | Fichiers statiques collectés        |

### depanage_demo (Spring Boot)

| Volume                  | Chemin conteneur           | Contenu                             |
|-------------------------|----------------------------|-------------------------------------|
| `depanage_db`           | `/app/data/depanage.db`    | Base de données SQLite              |
| `depanage_uploads`      | `/app/uploads/`            | Fichiers uploadés / rapports générés|

### Questure (Spring Boot)

| Volume                  | Chemin conteneur           | Contenu                             |
|-------------------------|----------------------------|-------------------------------------|
| `questure_db`           | `/app/data/questure.db`    | Base de données SQLite              |
| `questure_uploads`      | `/app/uploads/`            | Fichiers générés / exports          |

### missions_controle (Django — en développement)

| Volume                  | Chemin conteneur           | Contenu                        |
|-------------------------|----------------------------|--------------------------------|
| `missions_db`           | `/app/db/missions.sqlite3` | Base de données SQLite         |

### apdpvp-rh (React / Vite)

Pas de volume persistant. Le frontend est une image statique construite (`npm run build`) et servie via Nginx ou directement par Traefik. Données persistantes gérées via Supabase (externe).

---

## Variables d'environnement partagées

Ces variables doivent être cohérentes entre tous les services :

```env
# Clé JWT — identique sur tous les services
JWT_SECRET_KEY=django-insecure-zpiod...

# Langue
LANGUAGE_CODE=fr-fr

# Mode
DEBUG=False
```

Chaque service dispose ensuite de ses propres variables (ex: `DATABASE_URL`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`).

---

## Structure Docker recommandée

```
apdpvp_2026/
├── traefik/
│   ├── traefik.yml              # Configuration Traefik (entrypoints, providers)
│   └── docker-compose.yml       # Service Traefik + réseau traefik_net
│
├── auth_app/
│   ├── Dockerfile
│   └── docker-compose.yml       # auth_app + volumes + réseaux auth_net, traefik_net
│
├── rh_app/
│   ├── Dockerfile
│   └── docker-compose.yml       # rh_app + volumes + réseaux rh_net, traefik_net
│
├── apdpvp-rh/
│   ├── Dockerfile
│   └── docker-compose.yml       # Frontend React + réseaux rh_net, traefik_net
│
├── depanage_demo/
│   ├── Dockerfile
│   └── docker-compose.yml       # depanage + volumes + réseaux depanage_net, traefik_net
│
├── Questure/
│   ├── Dockerfile
│   └── docker-compose.yml       # questure + volumes + réseaux questure_net, traefik_net
│
└── missions_controle/
    ├── Dockerfile
    └── docker-compose.yml       # missions + volumes + réseaux missions_net, traefik_net
```

---

## Règles d'infrastructure

1. **Un `docker-compose.yml` par service** — chaque application est déployable indépendamment.
2. **Traefik est démarré en premier** — il crée le réseau `traefik_net` (externe) que tous les autres rejoignent.
3. **Les réseaux isolés (`*_net`) sont internes** — déclarés dans le `docker-compose.yml` du service concerné.
4. **`traefik_net` est externe** — déclaré `external: true` dans chaque `docker-compose.yml`.
5. **Les volumes sont nommés** (pas de bind-mount en production) pour permettre la portabilité.
6. **La clé JWT est identique partout** — à gérer via un fichier `.env` racine ou un secret Docker.

---

## Démarrage de l'infrastructure

```bash
# 1. Démarrer Traefik (crée traefik_net)
cd traefik && docker compose up -d

# 2. Démarrer les services (dans n'importe quel ordre)
cd auth_app         && docker compose up -d
cd rh_app           && docker compose up -d
cd apdpvp-rh        && docker compose up -d
cd depanage_demo    && docker compose up -d
cd Questure         && docker compose up -d
cd missions_controle && docker compose up -d
```

---

## Checklist — ajouter un nouveau service

- [ ] Créer un `Dockerfile` dans le dossier du service
- [ ] Créer un `docker-compose.yml` avec ses volumes, son réseau isolé (`<service>_net`) et `traefik_net` en externe
- [ ] Ajouter les labels Traefik avec le bon sous-domaine (`<service>.apdpvp.local`)
- [ ] Déclarer les volumes nommés pour la BDD et les fichiers uploadés
- [ ] Ajouter la variable `JWT_SECRET_KEY` partagée
- [ ] Mettre à jour ce fichier (`CLAUDE.md`) avec le nouveau service
