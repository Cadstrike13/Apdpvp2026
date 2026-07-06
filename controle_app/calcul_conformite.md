# Calcul de conformité — suggestion de verdict par traitement

Ce document explique la logique implémentée dans
`ReponseTraitement.suggestion_verdict()` (`missions/models.py`). À lire
avant de modifier la checklist, les seuils, ou d'implémenter un vrai calcul
de conformité automatique (voir `AVANCEMENT.md`).

## Ce que ce n'est pas

**Ce n'est pas un verdict officiel.** Le contrôleur reste seul responsable
du verdict final (CTO/CPA/NC/CPR) saisi sur la page Évaluation
(`/missions/<pk>/evaluation/`). Le calcul décrit ici ne fait qu'afficher une
**suggestion indicative** à côté de chaque traitement, avec le détail des
critères, et un bouton « Reprendre la suggestion » qui pré-remplit le
formulaire sans jamais soumettre à sa place.

La checklist et les seuils ci-dessous ont été proposés à dire d'expertise
technique, **sans validation par un profil juridique/métier de l'APDPVP** —
voir la tâche correspondante dans `AVANCEMENT.md`.

## Pourquoi une checklist plutôt qu'un calcul sur tous les champs

Le questionnaire (`ReponsePage1..5`, voir `reponse_traitement_fields.md`)
contient deux types de champs :

- des champs **descriptifs** (catégories de données collectées, moyen de
  transmission, type d'objet géolocalisé...) : cocher « email » comme moyen
  de transmission n'est ni conforme ni non conforme, c'est juste une
  information. Les noter pénaliserait ou avantagerait arbitrairement des
  traitements selon leur nature plutôt que selon leur conformité réelle.
- des champs qui sont de vrais **signaux de conformité** (une déclaration
  a-t-elle été faite ? les droits sont-ils respectés ? les mesures de
  sécurité sont-elles documentées ?).

`CRITERES_CONFORMITE` (`missions/models.py`) ne retient que la seconde
catégorie.

## La checklist

| # | Critère | Champ(s) | Condition « respecté » | Traitements concernés | Applicable si |
|---|---|---|---|---|---|
| 1 | Déclaration effectuée | `page1.declaration_effectuee` | `True` | tous | toujours |
| 2 | Droits des personnes respectés | `page1.droits_respectes` | `True` | tous | toujours |
| 3 | Contrat de sous-traitance en place | `page2.contrat_sous_traitance` | `True` | tous | `nombre_sous_traitants > 0` |
| 4 | Sous-traitant(s) déclaré(s) | `page2.sous_traitants_declares` | `True` | tous | `nombre_sous_traitants > 0` |
| 5 | Listing des caméras disponible | `page2.listing_cameras_disponible` | `True` | f, g uniquement | traitement ∈ {f, g} |
| 6 | Mesures organisationnelles documentées | `page5.mesures_organisationnelles` | non vide | tous | toujours |
| 7 | Mesures techniques documentées | `page5.mesures_techniques` | non vide | tous | toujours |
| 8 | Personnes habilitées identifiées | `page4.personnes_habilitees_noms` | non vide | tous | toujours |
| 9 | Durée de conservation définie | `page3.duree_conservation` | non vide | tous | toujours |
| 10 | Autorité de protection du pays destinataire documentée | `page4.autorite_protection_pays` | non vide | h uniquement | traitement = h |

**Un critère non applicable à un traitement n'entre pas dans le
dénominateur** — ex. pour le traitement « a) Gestion du personnel », seuls
les critères 1, 2, 6, 7, 8, 9 comptent (6 au total, sauf si des
sous-traitants sont déclarés, auquel cas 3 et 4 s'ajoutent).

## Calcul du score et seuils

```
score (%) = (critères respectés / critères applicables) × 100
```

| Score | Verdict suggéré |
|---|---|
| 100 % | Conformité totale (CTO) |
| 70 % – 99 % | Conformité partielle (CPA) |
| 40 % – 69 % | Non conforme (NC) |
| < 40 % | Constatation préoccupante (CPR) |

Ces paliers (100/70/40) sont arbitraires — aucune référence officielle n'a
été fournie. À ajuster si l'APDPVP dispose d'une grille de notation propre.

## Limites connues

- **Ambiguïté des booléens** : un champ à `False` peut vouloir dire « non
  conforme » ou « pas encore répondu » — il n'existe pas de suivi « champ
  touché » distinct (même limite que `pourcentage_complete`, voir
  `AVANCEMENT.md`).
- **Critères fixes, non pondérés** : chaque critère compte pour 1, quelle
  que soit sa gravité réelle (ex. l'absence de mesures de sécurité et
  l'absence de durée de conservation documentée pèsent pareil).
- **Aucun critère « bloquant »** : un seul manquement grave (ex. transfert
  de données sans autorité de protection documentée) ne force pas
  automatiquement un CPR — il ne fait que baisser le score comme les autres.
- **Aucun total applicable = 0** : si aucun critère ne s'applique à un
  traitement (n'arrive pas avec la checklist actuelle, tous les traitements
  ont au moins les 6 critères communs), la fonction renvoie `verdict: None`
  plutôt qu'une division par zéro.

## Où adapter le code

- Checklist et seuils : `CRITERES_CONFORMITE`, `COULEURS_VERDICT` dans
  `missions/models.py`, juste avant la classe `ReponseTraitement`.
- Calcul : `ReponseTraitement.suggestion_verdict()`.
- Affichage + bouton « Reprendre la suggestion » :
  `templates/missions/evaluation.html`.
- Tests : `missions/tests/test_models.py`, classe `SuggestionVerdictTests`.
