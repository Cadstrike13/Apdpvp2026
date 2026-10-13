# CLAUDE.md — app `controle_en_ligne`

Contexte pour Claude Code lors du travail sur cette app. La méthodologie de
référence est `GUIDE_CONTROLE_EN_LIGNE.md` (source de vérité juridique et
fonctionnelle, à versionner ici) ; la grille opérationnelle est
`GRILLE_CONTROLE.md` (IDs A01 à K02). Ne jamais s'écarter du guide sans le
mettre à jour en même temps que le code.

## Ce que fait cette app

Contrôle en ligne APDPVP : vérifications à distance de la conformité d'un
site ou d'une application web (cartographie, cookies et traceurs,
consentement, sécurité observable, CGU/CGV, formulaires, comptes, exercice
des droits, services tiers).

Elle tourne dans le service `controle_en_ligne_app` (base SQLite propre,
cf. `CLAUDE.md` racine). Le socle `core` du service (AgentProvider,
ResponsableTraitement, SoftDeleteMixin, JournalAction) reprend les noms du
projet missions_controle pour faciliter un éventuel rapprochement.

## Principes non négociables

1. **Non-intrusif** — aucun scan ne contourne une authentification,
   n'exploite une faille, ne soumet un formulaire ni ne devine d'URL.
   La cartographie suit seulement les liens publiés par la page d'accueil
   (profondeur 1, 40 pages, robots.txt respecté par défaut).
   `CHEMINS_LISTE_BLANCHE` (`services/scanner_securite.py`) est une liste
   fermée : ne jamais la transformer en exploration de répertoires.
2. **Fait ≠ Qualification** — un constat (`ConstatBase` et ses sous-classes)
   ne porte que des faits. Le jugement de l'agent vit dans le modèle
   `Qualification` : analyse, conformité, criticité, suite proposée,
   validation, agent signataire, date. Les scans ne créent **jamais** de
   `Qualification`. Conformité et criticité restent deux axes indépendants :
   ne jamais les fusionner en une « cotation ».
3. **La validation est un verrou** — `MissionControleEnLigne.tous_constats_valides()`
   exige au moins un constat et une qualification validée pour chacun, tous
   modèles de constat confondus (`modeles_constat()` les trouve seuls : un
   nouveau constat hérite de `ConstatBase` et entre dans le verrou sans autre
   code). Une qualification validée doit avoir conformité, agent et date, et
   une criticité sauf « Non applicable » : `clean()` et une contrainte en base
   l'imposent. Aucune tâche Celery ne fait passer une mission en `validee`.
4. **Le travail de l'agent n'est jamais écrasé** — une relance des scans
   remplace les constats sans qualification, conserve ceux qu'un agent a
   commencé à qualifier, et ne réécrit pas les faits d'un constat unique
   déjà qualifié (le nouveau relevé reste dans la preuve).
5. **Niveau 3 (technique approfondi) = hors périmètre auto** —
   `risque_technique_suspecte` est un signal, pas un déclencheur.
6. **Minimisation** — les valeurs de cookies et de stockage ne sont jamais
   conservées (`tasks._purger`) ; la cartographie ne garde que URL, titres et
   indices, pas le contenu des pages.
7. **Preuve** — chaque scan réussi produit une `PreuveCapture` JSON
   horodatée dont l'empreinte SHA-256 est figée au premier enregistrement.

## Structure

```
controle_en_ligne/
  models.py        # Qualification, ConstatBase, mission, 10 constats, preuves, suivi
  tasks.py         # lancer_scans_automatiques : cartographie → sécurité → cookies → tiers
  admin.py         # validation agent : qualification en ligne sous chaque constat
  services/
    scanner_cartographie.py  # requests + bs4, écrit et testé
    scanner_securite.py      # EMPLACEMENT : copier la version opérationnelle
    scanner_cookies.py       # EMPLACEMENT : copier la version opérationnelle
    scanner_tiers.py         # EMPLACEMENT : copier la version opérationnelle
  tests/           # qualification, verrou, orchestration, cartographie (site local)
  GRILLE_CONTROLE.md
```

## Traceurs de type inconnu

Un traceur dont le scanner renvoie un `type_traceur` hors de
`ConstatCookie.TYPES_TRACEUR` est **répertorié**, jamais ignoré :
`type_traceur="non_classe"`, type d'origine dans `type_brut`, et un
`fait_observe` qui demande à l'agent de le classer. Il entre dans le verrou
de clôture comme tout constat.

## Gestion des échecs

Chaque scan tourne dans sa transaction. Un échec est consigné dans
`mission.erreurs_scan` et au journal, les tests liés passent à
`execute=False`, les scans suivants continuent, et la mission reste en
`en_cours` (au lieu de `terminee`) tant qu'un scan a échoué.

## Mapping grille ↔ modèles

| Bloc | Modèle | Collecte |
|---|---|---|
| A | `MissionControleEnLigne` | saisie |
| B | `EnvironnementControle` | saisie |
| C | `ConstatInformation` | à écrire (`scanner_legal.py` + LLM) |
| D | `ConstatCookie` | auto |
| E | `ConstatConsentement` | à écrire |
| F | `ConstatFormulaire`, `ConstatDonnees` | à écrire (`scanner_formulaire.py`) |
| G | `ConstatCompte` | saisie |
| H | `ConstatSecurite` | auto |
| I | `ConstatLegal` | à écrire (`scanner_legal.py` + LLM) |
| J | `ConstatDroits` | saisie |
| K | `ConstatTiers` | auto |
| — | `PageIdentifiee` (cartographie) | auto |
| — | `Qualification` | agent uniquement |

## Tests

```
DEBUG=1 python manage.py test controle_en_ligne
```

La cartographie est testée contre un site servi en local : aucun test
n'appelle Internet.

## À faire

- Versionner les scanners sécurité, cookies et tiers (remplacer les emplacements).
- `services/scanner_formulaire.py`, `services/scanner_legal.py` (pré-analyse LLM auto-hébergé).
- Authentification par jeton JWT d'auth_app (aujourd'hui : comptes Django locaux).
- Génération du rapport (pipeline WeasyPrint du procès-verbal).
- Versionner `GUIDE_CONTROLE_EN_LIGNE.md` dans ce dossier.
