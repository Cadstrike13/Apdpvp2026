# Détail des champs — ReponseTraitement (5 pages)

Source : classeur Excel `Copie_de_Questionnaire_vf_10-05-2024.xlsx`, 5 feuilles
("Page 1" à "Page 5"), 10 lignes fixes (traitements a→j).

Les 10 traitements (`missions.models.Traitement`) :

| Code | Libellé |
|---|---|
| a | Gestion du personnel |
| b | Gestion des clients |
| c | Communication par transmission |
| d | Contrôle d'accès sans biométrie |
| e | Contrôle d'accès avec biométrie |
| f | Télé-vidéosurveillance |
| g | Vidéosurveillance |
| h | Transfert des données |
| i | Interconnexion |
| j | Géolocalisation |

Chaque `ReponseTraitement` (mission, traitement) a 5 sous-modèles en
`OneToOne` : `ReponsePage1` à `ReponsePage5`.

---

## Page 1 — Conformité déclarative (`ReponsePage1`)

| Champ | Type | Question source | Traitements concernés |
|---|---|---|---|
| `declaration_effectuee` | bool | Déclaration/autorisation/avis effectuée ? | tous |
| `numero_recepisse` | char | N° quittance/récépissé/autorisation/avis | tous |
| `raison_collecte` | text | Pour quelle raison collectez-vous les données ? | tous |
| `methode_consentement` | text | Méthode de consentement | tous |
| `droits_respectes` | bool | Droits des personnes respectés ? | tous |
| `dispositions_legales_derogatoires` | bool | Dispositions légales dérogatoires au droit des personnes ? | tous |
| `type_objet_geolocalise` | char | Appareil géolocalisé (véhicule, téléphone) | **j) uniquement** |
| `desactivation_geoloc_pause` | bool | Désactivation possible pendant la pause ? | **j) uniquement** |

## Page 2 — Vidéosurveillance & sous-traitance (`ReponsePage2`)

| Champ | Type | Question source | Traitements concernés |
|---|---|---|---|
| `nombre_cameras` | int (null) | Combien de caméras ? | **f)/g) uniquement** |
| `listing_cameras_disponible` | bool | Listing des caméras disponible ? | **f)/g) uniquement** |
| `contrat_sous_traitance` | bool | Contrat de sous-traitance en place ? | tous |
| `contrat_sous_traitance_fichier` | file | "Si oui présentez-le" | tous |
| `nombre_sous_traitants` | int (null) | Combien de sous-traitants ? | tous |
| `entites_destinataires` | text | Vers quelle(s) entité(s) les données sont transmises ? | tous |
| `sous_traitants_declares` | bool | Sous-traitant(s) déclaré(s) ? | tous |
| `transmission_support_physique` | bool | Moyen de transmission : support physique | tous |
| `transmission_mail` | bool | Moyen de transmission : mail | tous |
| `transmission_protocole` | bool | Moyen de transmission : protocole | tous |
| `transmission_autres` | char | Moyen de transmission : autres (précision) | tous |

## Page 3 — Nature des données collectées (`ReponsePage3`)

| Champ | Type | Question source | Traitements concernés |
|---|---|---|---|
| `donnees_identification` | bool | Catégorie : identification des personnes | tous |
| `donnees_comportement` | bool | Catégorie : comportement | tous |
| `donnees_professionnelles` | bool | Catégorie : données professionnelles | tous |
| `donnees_situation_financiere` | bool | Catégorie : situation financière | tous |
| `donnees_deplacements` | bool | Catégorie : déplacements des personnes | tous |
| `donnees_complementaires` | bool | Catégorie : données complémentaires | tous |
| `origine_donnees` | text | Origine des données | tous |
| `destinataires_donnees` | text | Destinataires des données | tous |
| `duree_conservation` | char | Durée de conservation | tous |

## Page 4 — Accès et transferts internationaux (`ReponsePage4`)

| Champ | Type | Question source | Traitements concernés |
|---|---|---|---|
| `personnes_habilitees_noms` | text | Personnes habilitées — noms | tous |
| `personnes_habilitees_fonctions` | text | Personnes habilitées — fonctions | tous |
| `entites_interconnexion` | text | Entité(s) vers lesquelles interconnectées | **i) uniquement** |
| `pays_transfert` | char | Pays vers lequel transférées | **h) uniquement** |
| `autorite_protection_pays` | char | Autorité de protection du pays destinataire | **h) uniquement** |
| `entite_destinataire_nom_adresse` | text | Nom/adresse de l'entité destinataire | **h) uniquement** |
| `empreinte_pouces_index` | bool | Empreinte : pouces/index | **e) uniquement** |
| `empreinte_palmaire` | bool | Empreinte : palmaire | **e) uniquement** |
| `empreinte_faciale` | bool | Empreinte : faciale | **e) uniquement** |
| `empreinte_autres` | char | Empreinte : autres | **e) uniquement** |

⚠️ **Ne pas confondre** `personnes_habilitees_*` (Page 4 — personnes ayant
accès aux données dans le cadre du traitement) avec le modèle
`PersonneInterrogee` (personnes interrogées pendant l'audit lui-même). Ce
sont deux concepts distincts.

## Page 5 — Mesures de sécurité (`ReponsePage5`)

| Champ | Type | Question source | Traitements concernés |
|---|---|---|---|
| `mesures_organisationnelles` | text | Politiques, formations, gestion des accès | tous |
| `mesures_techniques` | text | Cryptographie, pare-feu, détection d'intrusion | tous |

## Champ global (hors grille, niveau `MissionControle`)

`commentaires_observations` (text) — "Autres commentaires ou observations",
une seule zone en bas du questionnaire, pas répétée par traitement.

---

## Note pour le calcul de conformité (tâche à venir)

Les champs booléens ci-dessus (`declaration_effectuee`, `droits_respectes`,
`listing_cameras_disponible`, `sous_traitants_declares`, etc.) sont les
candidats naturels pour les règles de scoring par traitement. Les champs
« concernés uniquement par X » ne doivent pas pénaliser le score des
traitements où ils sont hors sujet — la règle de calcul devra ignorer les
champs non applicables au traitement évalué plutôt que les compter comme
« non conformes ».
