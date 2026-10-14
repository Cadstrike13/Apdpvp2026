# Grille de contrôle en ligne — Document opérationnel

*Document 2 sur 3. Utilisé pendant le contrôle, à remplir point par point. Le rapport (Document 3) est généré à partir des résultats de cette grille — voir CLAUDE.md.*

Structure par ligne : **ID | Point contrôlé | Méthode | Fait observé | Preuve | Analyse | Conformité | Criticité | Suite proposée**

---

## Bloc A — Programmation (Phase 0)

| ID | Point contrôlé | Méthode |
|---|---|---|
| A01 | Origine du contrôle renseignée | Manuel |
| A02 | Niveau de contrôle défini (1/2/3) | Manuel |

## Bloc B — Environnement (Phase 0 bis)

| ID | Point contrôlé | Méthode |
|---|---|---|
| B01 | Profil navigateur vierge utilisé | Auto (log environnement) |
| B02 | Horloge synchronisée | Auto |
| B03 | Compte de test / données fictives déclarés | Manuel |

## Bloc C — Information des personnes (Phase 3)

| ID | Point contrôlé | Méthode |
|---|---|---|
| C01 | Politique de confidentialité disponible ? | Semi-auto |
| C02 | Identité du responsable indiquée ? | Semi-auto (LLM assisté) |
| C03 | Finalités indiquées ? | Semi-auto (LLM assisté) |
| C04 | Base juridique indiquée ? | Semi-auto (LLM assisté) |
| C05 | Durée de conservation indiquée ? | Semi-auto (LLM assisté) |
| C06 | Destinataires indiqués ? | Semi-auto (LLM assisté) |
| C07 | Transferts indiqués ? | Semi-auto (LLM assisté) |
| C08 | Droits et modalités d'exercice indiqués ? | Semi-auto (LLM assisté) |
| C09 | Contact DPO indiqué ? | Semi-auto (LLM assisté) |

## Bloc D — Cookies et autres traceurs (Phase 4)

| ID | Point contrôlé | Méthode |
|---|---|---|
| D01 | Traceurs déposés avant interaction | Auto |
| D02 | Traceurs déposés après acceptation | Auto |
| D03 | Traceurs déposés après refus | Auto |
| D04 | Traceurs déposés après modification du choix | Auto |
| D05 | Cookies déposés avant consentement ? | Auto |
| D06 | Traceurs tiers non déclarés détectés ? | Auto |
| D07 | localStorage/sessionStorage utilisés pour du suivi ? | Semi-auto |
| D08 | Fingerprinting détectable ? | Semi-auto |

## Bloc E — Consentement (Phase 5)

| ID | Point contrôlé | Méthode |
|---|---|---|
| E01 | Bannière présente | Auto |
| E02 | CMP identifiée | Auto |
| E03 | Refus aussi simple que l'acceptation ? | Manuel |
| E04 | Finalités distinguées (granularité) ? | Manuel |
| E05 | Choix modifiable et persistant ? | Semi-auto |

## Bloc F — Formulaires (Phase 6)

| ID | Point contrôlé | Méthode |
|---|---|---|
| F01 | Champs demandés justifiés par la finalité | Semi-auto |
| F02 | Case de consentement non pré-cochée | Auto |
| F03 | Transmission sécurisée (HTTPS/POST) | Auto |
| F04 | Message d'erreur non verbeux | Semi-auto |

## Bloc G — Comptes utilisateurs (Phase 7)

| ID | Point contrôlé | Méthode |
|---|---|---|
| G01 | Création de compte possible et testée | Manuel |
| G02 | Modification du profil/mot de passe testée | Manuel |
| G03 | Suppression de compte testée | Manuel |
| G04 | Consultation des données personnelles testée | Manuel |

## Bloc H — Sécurité observable (Phase 8)

| ID | Point contrôlé | Méthode |
|---|---|---|
| H01 | HTTPS complet | Auto |
| H02 | Redirection HTTP → HTTPS | Auto |
| H03 | Certificat TLS valide | Auto |
| H04 | En-têtes de sécurité présents | Auto |
| H05 | Fichiers/répertoires exposés (liste blanche) | Auto |
| H06 | Cookie de session Secure/HttpOnly | Auto |
| H07 | Risque technique sérieux suspecté (→ niveau 3) | Auto (signal) |

## Bloc I — CGU / CGV / mentions légales (Phase 9)

| ID | Point contrôlé | Méthode |
|---|---|---|
| I01 | CGU accessibles et complètes | Semi-auto (LLM assisté) |
| I02 | CGV accessibles et complètes (le cas échéant) | Semi-auto (LLM assisté) |
| I03 | Mentions légales présentes | Semi-auto |
| I04 | Cohérence CGU/CGV avec pratiques observées (D, E) | Manuel |

## Bloc J — Exercice des droits (Phase 10)

| ID | Point contrôlé | Méthode |
|---|---|---|
| J01 | Mécanisme d'exercice des droits existe | Semi-auto |
| J02 | Facilement accessible | Manuel |
| J03 | Modalités claires | Manuel |
| J04 | Procédure de suppression de compte existe | Manuel |

## Bloc K — Tiers et services externes (Phase 11)

| ID | Point contrôlé | Méthode |
|---|---|---|
| K01 | Services tiers détectés | Auto |
| K02 | Services tiers déclarés dans la politique | Manuel (croisement) |

---

## Légende Méthode

- **Auto** : renseigné automatiquement par un scan ; aucune qualification n'est créée
- **Semi-auto** : pré-rempli automatiquement, qualification par l'agent attendue
- **Manuel** : renseigné uniquement par l'agent

## Légende Conformité / Criticité (portées par le modèle `Qualification`)

**Conformité** : Conforme · Partiellement conforme · Non conforme · Non applicable
**Criticité** : Faible · Modérée · Élevée · Critique
