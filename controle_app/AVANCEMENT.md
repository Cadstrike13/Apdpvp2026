# État d'avancement — APDPVP Missions de contrôle

Dernière mise à jour : 2026-07-04.

## Fait

### Infrastructure projet
- Projet Django scaffoldé (`config/` : settings via `python-dotenv`, SQLite en dev
  / PostgreSQL en prod via `DB_ENGINE`), `requirements.txt`, `.env.example`.
- 5 apps : `core`, `entites`, `personnes`, `agents`, `missions`.
- Migrations générées et appliquées, `setup_groups` et `sync_agents` fonctionnels.

### Modèles (conformes à `CLAUDE.md` / `code_examples.md` / `reponse_traitement_fields.md`)
- `core` : `SoftDeleteMixin` + 3 managers (`objects`/`tous`/`corbeille`), `permissions.py`
  (`require_membre_mission`, `require_chef_mission`, `require_groupe`).
- `entites.EntiteControlee`, `personnes.Personne`/`Fonction`, `agents.AgentControleur`
  (+ provider mock/API, `sync_agents`).
- `missions` : `MissionControle` (verrouillage post-génération), `MembreGroupeControle`
  (un seul chef par mission), `PersonneInterrogee` (snapshot poste/service),
  `ReponseTraitement` + `ReponsePage1..5` (création auto par signal, tous les champs
  de la grille 10 traitements × 5 pages), `JournalAction`.
- `django-simple-history` sur les modèles verrouillables.

### Vues & templates (dashboard + questionnaire)
- Dashboard missions : liste, création (entité existante **ou nouvelle
  entité déclarée à la volée**), détail (groupe de contrôle, personnes
  interrogées, avancement par traitement, journal, accès au questionnaire).
- Questionnaire : un traitement à la fois — pastilles a→j + boutons
  Précédent/Suivant (`static/js/questionnaire.js`, générique, réutilisé aussi
  par la page Évaluation), au lieu du tableau large initial. Les champs
  propres à un seul traitement (géolocalisation, biométrie...) sont
  conditionnés côté serveur (`{% if ligne.reponse.traitement == "j" %}`), plus
  besoin de config JS par page. Vue générique paramétrée par page (1 à 5),
  formsets par page, navigation → `JournalAction` + progression du statut à
  la complétion de la page 5.
- **Ajout de personne interrogée** en modale : sélection d'une personne
  existante ou création à la volée (nom/prénom/email/téléphone) + poste et
  service au moment de la mission (auto-complétés depuis la `Fonction`
  connue si laissés vides).
- **Palette** bleu (actions principales/liens), vert (validation/succès),
  jaune-ambre (verrouillage/provisoire), blanc/gris (fond, neutre) — badges
  de statut colorés (`MissionControle.statut_css_classes`), champs de
  formulaire à fond gris clair passant au blanc au focus.
- **Responsive** : mise en page en cartes empilées sur mobile (plus de
  tableau large à faire défiler), en-tête et listes qui s'adaptent.
- Auth (login/logout via `django.contrib.auth`), Tailwind + htmx en CDN (pas de
  pipeline npm), `TailwindForm`/`TailwindModelForm` pour styliser les
  formulaires sans dupliquer les classes CSS.
- Flux testé de bout en bout via le client de test Django (login → création
  mission → 10 réponses générées → parcours des 5 pages → verrouillage → ajout
  membre/personne interrogée). Un bug réel a été trouvé et corrigé au passage :
  `request.mission` n'était pas posé pour les superusers dans
  `require_membre_mission`/`require_chef_mission` (corrigé dans `core/permissions.py`
  et dans `code_examples.md`).

### Clôture de mission

Circuit corrigé : le **procès-verbal (PV)** est généré en premier (verrouille
la mission), imprimé/signé/scanné, et c'est seulement à partir du PV signé que
le **rapport final** est généré — pas l'inverse.

- **PV réellement généré** : `missions/generate_pv.py` (fourni par
  l'utilisateur — python-docx + WeasyPrint) produit un vrai `.docx` (et
  `.pdf` si WeasyPrint est disponible sur la machine) à partir des données de
  la mission : entité, représentant, contrôleurs (`MembreGroupeControle`),
  personnes interrogées, et le tableau de conformité par traitement. Branché
  sur `pv_marquer_genere` (chef), qui verrouille la mission une fois le
  questionnaire complété (statut `questionnaire_complete` → `pv_genere`) et
  enregistre le document sur `MissionControle.pv_document`/`pv_document_pdf`.
  L'import de WeasyPrint est différé et tolère son absence (libs système
  Pango/Cairo/GObject non installées, ex. Windows sans GTK) — le `.docx` est
  toujours généré, le `.pdf` est alors simplement absent.
- **Évaluation par traitement** (`ReponseTraitement.evaluation` : conformité
  totale/partielle/non conforme/constatation préoccupante, + observations
  contrôleur/entité) — saisie manuelle par le chef via la page dédiée
  (`/missions/<pk>/evaluation/`) après le questionnaire et avant la
  génération du PV ; verrouillée comme le reste une fois le PV généré.
  Alimente le tableau 3 du procès-verbal.
- **Suggestion de verdict** (`ReponseTraitement.suggestion_verdict()`) :
  calcul indicatif à partir d'une checklist de 10 critères concrets
  (`CRITERES_CONFORMITE` dans `missions/models.py` — déclaration effectuée,
  droits respectés, contrat/sous-traitants déclarés si sous-traitance,
  listing caméras pour f/g, mesures organisationnelles/techniques,
  personnes habilitées, durée de conservation, autorité de protection pour
  h), seuils 100/70/40 % → CTO/CPA/NC/CPR. Affiché sur la page Évaluation à
  côté de chaque traitement avec le détail des critères et un bouton
  « Reprendre la suggestion » qui pré-remplit le verdict sans l'imposer — le
  contrôleur reste seul responsable de la saisie finale. Les champs
  purement descriptifs (catégories de données, moyen de transmission...) ne
  sont volontairement pas notés.
- **Informations du PV** (`InfosPVForm`, section dédiée sur la fiche
  mission) : mode (in situ/en ligne), nom du représentant de l'entité,
  heure du contrôle, numéro/organe de délibération, lieu/date/heure de
  signature — champs nécessaires à `generate_pv()` qui n'existaient dans
  aucun autre modèle.
- **Upload du scan du PV signé** : champ `MissionControle.scan_signe`,
  extensions autorisées PDF/JPG/PNG, 10 Mo max
  (`core/validators.ValidateurTailleFichier`, réutilisé aussi sur
  `ReponsePage2.contrat_sous_traitance_fichier`). Vue `scan_uploader` (chef
  uniquement), transition vers `pv_scan_uploade`.
- **Génération du rapport final** : action provisoire `rapport_marquer_genere`
  (chef), possible seulement une fois le PV signé uploadé (`pv_scan_uploade` →
  `rapport_genere`) — toujours pas de vrai générateur Word (bloqué sur le
  template) ; le message affiché précise explicitement que la génération
  automatique est en cours de développement.
- **Upload du rapport signé** : même principe que le PV — champ
  `MissionControle.rapport_signe` (mêmes contraintes de format/taille), vue
  `rapport_uploader` (chef), transition `rapport_genere` → `rapport_scan_uploade`.
- **Validation de mission par le chef** (`mission_valider`, statut
  `rapport_scan_uploade` → `validee`) — nécessite maintenant que le rapport
  signé ait été uploadé, pas seulement généré.
- **`commentaires_observations`** éditable depuis la fiche mission
  (`observations_modifier`), toujours modifiable même après verrouillage —
  champ non listé dans les éléments immuables.
- `questionnaire_page` fait maintenant progresser `MissionControle.statut`
  vers `questionnaire_complete` à la complétion de la page 5 (avant, le statut
  restait bloqué à `brouillon`).

### Suite de tests automatisés (102 tests, `python manage.py test`, ~98% de
couverture des lignes hors migrations — mesuré avec `coverage.py` en local,
pas ajouté aux dépendances du projet)

- `entites` : comportement soft-delete/restauration/hard-delete, y compris
  au niveau bulk (`queryset.supprimer()`/`.restaurer()`).
- `personnes` : `Fonction` multi-entités, contrainte d'unicité.
- `agents` : sélection du provider (mock/api), `ApiAgentProvider.fetch_agents()`
  (requête mockée), `sync_from_source` (idempotence, pas de résurrection
  silencieuse d'un agent soft-supprimé), commande `sync_agents`.
- `core` : `est_dans_groupe`/`require_groupe`, `ValidateurTailleFichier`
  (rejet fichier trop volumineux + égalité pour la stabilité des migrations),
  commandes `setup_groups` et `seed_dev` (création, garde `DEBUG=False`,
  idempotence).
- `missions` : signal de création des 10 réponses, verrouillage
  post-génération (chaque modèle protégé, y compris la suppression réussie
  quand la mission n'est *pas* verrouillée), contrainte un seul chef,
  permissions (`require_membre_mission`/`require_chef_mission`, redirection
  anonyme, refus 403, régression superuser), parcours complet du
  questionnaire (y compris 404 sur page inconnue, formset invalide),
  parcours de clôture complet (PV → scan → rapport → scan rapport →
  validation) avec tous les gardes de statut et rejets d'extension, échec de
  génération du PV (exception `generate_pv` mockée) sans verrouiller la
  mission, sauvegarde du PDF quand disponible, suggestion de conformité
  (checklist, seuils, critères conditionnels/spécifiques par traitement).
- Trois bugs réels trouvés et corrigés pendant l'écriture des tests :
  1. `request.mission` jamais posé pour un superuser dans
     `require_membre_mission`/`require_chef_mission` (déjà documenté ci-dessous).
  2. `MissionControle.save()` comparait `date_mission` sans normaliser son type
     (une valeur non encore passée par `full_clean()`, ex. une chaîne
     `"2026-07-01"`, était vue à tort comme une modification par rapport à la
     valeur en base) — corrigé par un `to_python()` explicite.
  3. `ReponsePageMixin.clean()`/`.delete()` plantait (`RelatedObjectDoesNotExist`,
     500) au lieu de renvoyer une erreur de formulaire propre, si un
     formset de questionnaire recevait un `TOTAL_FORMS` supérieur au nombre
     réel de lignes (management form trafiqué côté client) — corrigé en
     vérifiant `self.reponse_id` avant d'accéder à `self.reponse`.

### Documentation
- `CLAUDE.md` et `AGENTS.md` nettoyés (liens cassés vers `docs/` corrigés,
  duplication entre les deux fichiers réduite).

## Hypothèses prises faute de spec (à valider)

- `StatutMission` : 9 statuts ordonnés (brouillon → planifiée → en cours →
  questionnaire complété → **PV généré** → **PV signé uploadé** → rapport
  généré → **rapport signé uploadé** → validée) ; `est_verrouillee` = statut
  ≥ PV généré. Le rapport final se base sur le PV signé, donc généré après
  lui — pas avant. Le rapport suit le même circuit de signature que le PV
  avant validation.
- `EntiteControlee` : seul le champ `nom` existe (repris tel quel de
  `code_examples.md`) — pas d'adresse, secteur d'activité ou contact.
- `Personne` : nom, prénom, email, téléphone.
- `AgentControleur` lié à un `User` Django via `OneToOneField` nullable.
- Permissions : ajout d'un membre au groupe de contrôle réservé au chef de mission
  (`require_chef_mission`), ajout d'une personne interrogée ouvert à tout membre
  (`require_membre_mission`) — non explicitement spécifié dans `CLAUDE.md`.

## Reste à faire

- [ ] **Faire valider la checklist et les seuils de la suggestion de
      conformité** par un profil métier/juridique (10 critères et paliers
      100/70/40 % choisis à dire d'expert technique, pas de référence
      officielle fournie — voir « Fait » ci-dessus). Le verdict reste de
      toute façon saisi manuellement, donc pas bloquant.
- [ ] **Score global de conformité de l'entité contrôlée** (au-delà du
      verdict par traitement) — non demandé pour l'instant.
- [ ] **Génération réelle du rapport final Word/PDF** à partir du PV signé —
      `rapport_marquer_genere` reste un simple verrou provisoire sans document
      généré (le PV, lui, est déjà réellement généré — voir plus haut).
- [ ] **WeasyPrint en production** : vérifier que les libs système
      (Pango/Cairo/GObject, cf. `missions/generate_pv.py`) sont bien
      installées dans l'image Docker de déploiement pour que le PDF du PV
      soit généré (le `.docx` fonctionne déjà partout).
- [ ] **Spécification de l'API agents en production** (`ApiAgentProvider`) :
      URL réelle, schéma d'authentification, format JSON — toujours en
      attente, `AGENTS_SOURCE=mock` reste actif par défaut.
- [ ] Déploiement (infra Docker/Traefik — voir `CLAUDE.md` racine du monorepo).
