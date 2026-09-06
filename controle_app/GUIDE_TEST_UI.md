# Guide de test manuel — UI/UX

Ce guide sert à tester dans un navigateur ce que la suite automatisée
(`python manage.py test`, 44 tests) vérifie déjà côté logique — ici l'objectif
est le rendu, la navigation et le ressenti d'utilisation.

## 1. Préparer l'environnement

```
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_dev             # comptes + agents + entité de démo (DEBUG uniquement)
python manage.py runserver
```

Ouvrir `http://127.0.0.1:8000/`.

## 2. Comptes de test avec des rôles différents

`seed_dev` crée directement 3 comptes avec des identifiants fixes (voir
`core/management/commands/seed_dev.py` et `CLAUDE.md`) :

| Compte       | Mot de passe | Rôle                                                                  |
|--------------|--------------|------------------------------------------------------------------------|
| `admin`      | `admin1234`  | Superuser (bypass toutes permissions)                                  |
| `chef_test`  | `test1234`   | Lié à l'agent mock AG-001 (Obiang Marie), groupe « Chef de mission »   |
| `agent_test` | `test1234`   | Lié à l'agent mock AG-002 (Ndong Paul), groupe « Agent contrôleur »    |

Une entité de démo « ACME SA (démo) » est aussi créée. L'UI change selon le
rôle (bouton "Marquer rapport généré", upload scan et validation ne sont
visibles que pour le **chef de mission**) — utiliser `chef_test` et
`agent_test` pour comparer, `admin` pour débloquer rapidement un état.

Utiliser 3 fenêtres de navigation différentes (ou navigation privée) pour
être connecté simultanément en `admin`, `chef_test` et `agent_test`. La
commande est idempotente : la relancer ne duplique rien.

## 3. Page d'accueil (`/`)

- [ ] Non connecté : page d'accueil publique visible, bouton « Se connecter »
  visible, pas de redirection immédiate.
- [ ] Connecté : `/` redirige automatiquement vers le tableau de bord des
  missions (`/missions/`).
- [ ] Le logo/titre en haut à gauche ramène toujours à `/`.

## 4. Connexion / déconnexion

- [ ] `/accounts/login/` : formulaire simple, message d'erreur clair si
  identifiants invalides.
- [ ] Après connexion, redirection vers le tableau de bord.
- [ ] Bouton « Déconnexion » dans l'en-tête, ramène à la page de connexion.
- [ ] Tenter d'accéder à une URL de mission sans être connecté →
  redirection vers `/accounts/login/?next=...`.

## 5. Créer une mission (connecté en `admin`)

1. `/admin/entites/entitecontrolee/` → créer une entité (« ACME SA »).
2. Tableau de bord (`/missions/`) → « Nouvelle mission » → sélectionner
   l'entité, une date, valider.
3. Vérifier : redirection vers la fiche mission, statut « Brouillon ».

- [ ] Formulaire de création clair, champ date au format calendrier natif.
- [ ] Message d'erreur si un champ obligatoire manque.

## 6. Fiche mission — groupe de contrôle et personnes interrogées

Sur la fiche mission :

- [ ] Ajouter Obiang Marie comme **chef de mission** → apparaît dans la
  liste « Groupe de contrôle ».
- [ ] Tenter d'ajouter un second chef → doit échouer (message d'erreur
  affiché en haut de page, contrainte « un seul chef par mission »).
- [ ] Ajouter une personne interrogée (créer une `Personne` via `/admin/`
  au besoin) → apparaît dans « Personnes interrogées ».
- [ ] Section « Commentaires / observations » : taper un texte, enregistrer,
  recharger la page → le texte est conservé.

## 7. Questionnaire — les 5 pages

Depuis la fiche mission, cliquer « Page 1 ».

- [ ] Navigation Page 1 → 5 via les liens en haut (page active mise en
  évidence).
- [ ] **Page 1** : les colonnes « Appareil géolocalisé » et
  « Désactivation pendant la pause » ne sont visibles/actives que sur la
  ligne « Géolocalisation » (traitement j) — vérifier que le JS masque bien
  les cellules des 9 autres lignes.
- [ ] **Page 2** : « Nb caméras » et « Listing caméras » visibles seulement
  sur les lignes « Télé-vidéosurveillance » (f) et « Vidéosurveillance » (g).
- [ ] **Page 4** : colonnes empreintes visibles seulement sur « Contrôle
  d'accès avec biométrie » (e), interconnexion seulement sur « i »,
  transfert seulement sur « h ».
- [ ] Remplir quelques champs sur chaque page, cliquer « Enregistrer et
  continuer » → passage à la page suivante, données conservées si on
  revient en arrière.
- [ ] Page 5 : le bouton devient « Enregistrer et terminer le
  questionnaire » → redirection vers la fiche mission, statut passé à
  « Questionnaire complété ».
- [ ] Une entrée apparaît dans le « Journal » de la fiche mission.

## 8. Évaluation, génération du PV et clôture

Connecté en `chef_test`, sur une mission dont `chef_test` est le chef.

Circuit : questionnaire complété → évaluation par traitement → informations
du PV renseignées → procès-verbal (PV) **réellement généré**
(`.docx`, `.pdf` si WeasyPrint est installé) → imprimé/signé/scanné →
rapport final généré à partir du PV signé → mission validée.

- [ ] Sur la fiche mission, cliquer « Évaluer les traitements » → une page
  en cartes (comme le questionnaire) permet de choisir un verdict
  (Conformité totale/partielle/Non conforme/Constatation préoccupante) et de
  saisir des observations contrôleur/entité pour chacun des 10 traitements.
  Enregistrer.
- [ ] Remplir la section « Informations du procès-verbal » (mode, nom du
  représentant, heure du contrôle, délibération, lieu/date/heure de
  signature) — ces champs sont repris tels quels dans le document généré.
- [ ] Se connecter en `agent_test` : la section « Procès-verbal, rapport &
  clôture » **n'apparaît pas** sur la fiche mission (visible seulement au chef).
- [ ] Se connecter en `chef_test` : la section apparaît, avec le bouton
  « Générer le procès-verbal ».
- [ ] Cliquer dessus → un lien « télécharger (.docx) » apparaît (et
  « télécharger (.pdf) » si WeasyPrint est installé sur la machine —
  sinon c'est normal qu'il soit absent, voir limites connues). Ouvrir le
  `.docx` et vérifier que le nom de l'entité, le représentant, les
  contrôleurs, les personnes interrogées et le tableau de conformité par
  traitement correspondent bien à ce qui a été saisi.
- [ ] La mission passe en lecture seule (bandeau « Mission verrouillée » sur
  la fiche et sur les pages du questionnaire, boutons « Enregistrer »
  masqués) — y compris sur la page Évaluation.
- [ ] Essayer de rouvrir une page du questionnaire → les champs sont non
  éditables (formulaire affiché mais bouton d'enregistrement absent).
- [ ] Uploader un scan avec une mauvaise extension (ex. `.exe`) → message
  d'erreur, rien n'est enregistré.
- [ ] Uploader un fichier de plus de 10 Mo → message d'erreur sur la taille.
- [ ] Uploader un PDF valide → lien « télécharger » apparaît, statut passe
  à « Procès-verbal signé uploadé ».
- [ ] Bouton « Marquer le rapport comme généré » apparaît seulement après
  l'upload du PV signé → cliquer → message précisant que la génération
  automatique est en cours de développement, statut passe à « Rapport généré ».
- [ ] Bouton « Uploader le rapport signé » apparaît après la génération du
  rapport → mêmes contrôles que pour le PV (extension, taille) → statut passe
  à « Rapport signé uploadé ».
- [ ] Bouton « Valider la mission » apparaît seulement après l'upload du
  rapport signé → cliquer → statut « Validée ».

## 9. Cas d'erreurs et permissions à vérifier

- [ ] `agent_test` non membre d'une mission tente d'ouvrir sa fiche →
  page 403 (Django par défaut, à améliorer visuellement si besoin).
- [ ] `agent_test` tente une action réservée au chef (ex. poster sur l'URL
  de validation) → 403.
- [ ] Formulaire d'ajout de membre avec un agent déjà présent → message
  d'erreur (contrainte d'unicité mission/agent).

## 10. Responsive / rendu général

- [ ] Réduire la fenêtre à une largeur mobile : le questionnaire s'affiche en
  cartes empilées une colonne (plus de tableau large à défiler), l'en-tête et
  les autres pages restent lisibles.
- [ ] Vérifier que Tailwind (CDN) et htmx (CDN) se chargent bien — ouvrir la
  console navigateur, aucune erreur 404 sur ces scripts (nécessite une
  connexion internet, pas de fallback offline pour l'instant).

## Limites connues à ne pas signaler comme bug

- Les boutons « Marquer le procès-verbal comme généré » et « Marquer le
  rapport comme généré » sont des étapes **provisoires** (pas de vrai document
  généré) — normal tant que les modèles ne sont pas fournis.
- Aucun calcul de conformité n'est encore affiché (pas de score).
- L'API agents réelle n'est pas branchée (`sync_agents` utilise toujours le
  mock).

Voir [AVANCEMENT.md](AVANCEMENT.md) pour la liste à jour de ce qui reste à
faire.
