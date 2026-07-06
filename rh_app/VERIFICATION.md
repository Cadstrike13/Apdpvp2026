# VÉRIFICATION — rh_app vs spec « Infos RH »

Confrontation de l'état actuel de `rh_app` à la spécification métier fournie.
Légende : ✅ présent · ⚠️ partiel · ❌ absent

---

## 0. Architecture (rappel)

- **Login + dashboard portail** (regroupant les apps et infos du compte) → **`auth_app`** (SSO).
- `rh_app` **consomme** l'identité via **JWT** (`JWTAuthenticationMiddleware` + `JWT_SECRET_KEY` partagée) — déjà en place.
- ⚠️ La page de login ajoutée dans `rh_app` (`/login/`) fait **doublon** avec `auth_app` : à conserver seulement comme secours de développement, ou à retirer une fois `auth_app` opérationnel.

---

## 1. Données d'un Agent — ✅ RÉALISÉ

> Refonte effectuée : champs identité/contacts/dossier/matricules ajoutés sur `Employee`,
> modèles de référence (`CategorieProfessionnelle`, `StatutAgent`, `Poste`, `TypeContrat`)
> et liés (`Diplome`, `Contrat`, `Affectation`, `Evaluation`) créés.
> Contraintes d'unicité conditionnelles sur les 3 matricules (actifs uniquement).
> Données peuplées via `seed_referentiels` + `seed_agents_details`.

Le tableau ci-dessous reste l'état cible (tout est désormais ✅, sauf mention contraire).

| Champ spec | État | Détail / action |
|---|---|---|
| Nom / prénom / date naissance | ✅ | présents |
| Statut matrimonial | ❌ | ajouter (choices : célibataire/marié/divorcé/veuf) |
| Nombre d'enfants | ❌ | ajouter (entier) |
| Téléphone (2 numéros + urgence) | ❌ | ajouter `tel1`, `tel2`, `tel_urgence` |
| Email | ✅ | présent (unique sur actifs) |
| CV (file) | ❌ | ajouter `FileField` |
| Lettre de motivation (file) | ❌ | ajouter `FileField` |
| Diplômes (PDF, M2M) | ❌ | nouveau modèle `Diplome` + M2M |
| Matricule CNSS (unique) | ❌ | ajouter, unique |
| Matricule CNAMGS (unique) | ❌ | ajouter, unique |
| Matricule APDPVP (unique) | ❌ | ajouter, unique |
| Catégorie pro (FK) | ❌ | nouveau modèle `CategorieProfessionnelle` |
| Date d'embauche (immuable) | ✅ | présent (rendre non éditable après création) |
| Formations internes (M2M) | ⚠️ | existe via `TrainingProgram.participants` (relation inverse) |
| Évaluations (M2M) | ❌ | nouveau modèle `Evaluation` |
| Statut agent (stage/actif/congé/absent/licencié) (FK) | ⚠️ | actuel = `actif/inactif` seulement → modèle `StatutAgent` |
| Postes (affectations multiples, M2M) | ⚠️ | actuel = `poste` texte unique → modèle `Poste` + M2M `Affectation` |
| Statut du contrat (CDI/CDD/Stage/mandat, M2M) | ❌ | nouveau modèle `Contrat` (historique) |

➡️ **Refonte du modèle Agent nécessaire** + modèles de référence : `CategorieProfessionnelle`, `StatutAgent`, `Poste`, `Contrat`, `Diplome`, `Evaluation`.

---

## 2. Actes

Nomenclature actuelle : 14 catégories / 105 types. Couverture des actes attendus :

| Acte attendu | État |
|---|---|
| Attestation d'emploi | ✅ `attestation_emploi` |
| Présence au poste | ✅ `presence` |
| Attestation de congé | ❌ à ajouter |
| Attestation de stage | ❌ à ajouter |
| Attestation de fin de contrat | ✅ `certificat_travail_depart` / `fin_cdd` |
| Attestation de licenciement | ✅ `lettre_licenciement` |
| Autorisation d'absence | ✅ `autorisation_absence` |

➡️ Ajouter `attestation_conge` et `attestation_stage` à la nomenclature. (Pièce jointe scannée + génération PDF déjà en place.)

---

## 3. Données / Rappels (J-21 ou J-30)

| Rappel | État |
|---|---|
| Signalement de congé | ❌ |
| Fin de contrat | ❌ |
| Changement de catégorie pro (avancement) | ❌ |
| Anniversaire | ⚠️ affiché sur le dashboard, mais pas de **rappel proactif** (J-21/J-30) |

➡️ **Moteur de rappels absent.** Prévoir un modèle `Rappel`/`Notification` + une commande planifiée (cron) calculant les échéances à J-21/J-30, et un affichage « alertes » sur le tableau de bord.

---

## 4. Recrutement (demandes d'emploi & stages)

| Besoin | État |
|---|---|
| Classer dossiers stagiaires | ⚠️ `Candidate` existe, pas de distinction stage/emploi |
| Classer dossiers demandes d'emploi | ⚠️ idem |
| Champ priorité (important, etc.) | ❌ à ajouter |

➡️ Ajouter `type_demande` (emploi/stage) + `priorite` sur `Candidate` (ou modèle dédié `Candidature`).

---

## 5. Rémunérations

| Besoin | État |
|---|---|
| Gestion des primes | ❌ |
| Gestion des salaires | ⚠️ champ `salaire` unique sur Employee, pas d'historique |
| Calcul des droits | ❌ |
| Cotisations sociales (CNSS / CNAMGS) | ❌ |
| Avances sur salaire | ❌ |
| Allocation des congés | ❌ |

➡️ **Module `remuneration` à créer** : `Salaire` (historique), `Prime`, `AvanceSalaire`, `Cotisation`, calculs de droits.

---

## 6. Gestion de carrière

| Besoin | État |
|---|---|
| Historique de l'agent | ⚠️ partiel via `AuditLog` (technique), pas de vue carrière métier |
| Générer les fiches de poste | ❌ |
| Formations internes | ✅ `TrainingProgram` |
| Évaluations | ❌ |
| Avancements | ❌ |

➡️ **Module `carriere` à créer** : `Evaluation`, `Avancement`, génération de fiche de poste (PDF, comme les actes), vue « parcours » de l'agent.

---

## 7. Synthèse

| Domaine | Couverture |
|---|---|
| Socle (auth, rôles, audit, soft delete, JWT, actes + PDF) | ✅ solide |
| Données Agent (spec complète) | ✅ refonte réalisée |
| Actes | ✅ complet (attestation_conge + attestation_stage ajoutés) |
| Rappels / notifications | ✅ moteur J-30 + dashboard |
| Rémunérations | ✅ salaires/primes/avances/cotisations + calcul des droits + bulletin PDF |
| Carrière (évaluations, avancements, fiches de poste) | ✅ + fiche de poste PDF |
| Recrutement (stage/emploi + priorité) | ✅ type de demande, priorité, classement, candidature spontanée |

### Ordre d'implémentation
1. ✅ Refonte du modèle Agent + modèles de référence.
2. ✅ Actes manquants.
3. ✅ Carrière (évaluations, avancements, fiches de poste).
4. ✅ Moteur de rappels (J-30).
5. ✅ Rémunérations.
6. ✅ Recrutement (priorité + type de demande + classement + candidature spontanée).

**Toutes les briques de la spec « Infos RH » sont implémentées.**
