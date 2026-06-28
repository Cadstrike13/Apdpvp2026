"""
Nomenclature des actes / documents administratifs RH — adaptée au Gabon.

Organismes gabonais référencés :
  - CNSS   : Caisse Nationale de Sécurité Sociale
  - CNAMGS : Caisse Nationale d'Assurance Maladie et de Garantie Sociale
  - IRPP   : Impôt sur le Revenu des Personnes Physiques
  - ONE    : Office National de l'Emploi

Choix groupés (optgroup) : [(categorie, [(code, libelle), ...]), ...]
"""

TYPE_ACTE_CHOICES = [
    ("1. Embauche / Contrat", [
        ("contrat_travail", "Contrat de travail (copie signée)"),
        ("promesse_embauche", "Promesse d'embauche / lettre d'engagement"),
        ("avenant_contrat", "Avenant au contrat"),
        ("fiche_poste", "Fiche de poste / description de fonction"),
        ("lettre_nomination", "Lettre de nomination / affectation"),
        ("convention_collective", "Convention collective applicable"),
        ("reglement_interieur", "Règlement intérieur"),
        ("charte_informatique", "Charte informatique / sécurité"),
        ("clause_confidentialite", "Clause de confidentialité / non-concurrence"),
        ("dossier_embauche", "Dossier administratif d'embauche"),
    ]),
    ("2. Administratifs personnels", [
        ("attestation_travail", "Attestation / certificat de travail"),
        ("attestation_emploi", "Attestation d'emploi"),
        ("presence", "Attestation de présence"),
        ("attestation_salaire", "Attestation de salaire"),
        ("attestation_anciennete", "Attestation d'ancienneté"),
        ("attestation_fonction", "Attestation de fonction"),
        ("attestation_visa", "Attestation pour ambassade / visa"),
        ("attestation_revenu", "Attestation de revenu"),
        ("lettre_recommandation", "Lettre de recommandation"),
        ("certificat_employeur", "Certificat employeur"),
        ("releve_carriere", "Relevé de carrière interne"),
    ]),
    ("3. Paie / rémunération", [
        ("bulletin_paie", "Bulletin de paie"),
        ("duplicata_bulletin", "Duplicata de bulletin de paie"),
        ("historique_salaires", "Historique des salaires"),
        ("releve_primes", "Relevé des primes"),
        ("detail_heures_sup", "Détail des heures supplémentaires"),
        ("etat_retenues", "État des retenues salariales"),
        ("avantages_nature", "Relevé des avantages en nature"),
        ("attestation_remuneration", "Attestation de rémunération annuelle"),
        ("solde_tout_compte", "Solde de tout compte"),
    ]),
    ("4. Congés / absences / temps", [
        ("solde_conges", "Solde de congés payés"),
        ("historique_conges", "Historique des congés"),
        ("releve_absences", "Relevé des absences"),
        ("autorisation_absence", "Autorisation / justificatif d'absence"),
        ("planning_horaire", "Planning horaire"),
        ("feuille_presence", "Feuille de présence / pointage"),
        ("conge_sans_solde", "Autorisation de congé sans solde"),
        ("conge_maternite", "Congé maternité / paternité"),
        ("conge_parental", "Congé parental"),
        ("validation_teletravail", "Validation télétravail"),
    ]),
    ("5. Protection sociale / santé (CNSS, CNAMGS)", [
        ("affiliation_cnss", "Affiliation CNSS"),
        ("affiliation_cnamgs", "Affiliation CNAMGS (assurance maladie)"),
        ("carte_assure", "Carte d'assuré / mutuelle"),
        ("notice_garanties", "Notice de garanties / prévoyance"),
        ("declaration_at", "Déclaration d'accident de travail"),
        ("maladie_professionnelle", "Déclaration de maladie professionnelle"),
        ("visite_medicale", "Certificat de visite médicale"),
        ("aptitude_medicale", "Certificat d'aptitude médicale"),
        ("dossier_retraite", "Dossier retraite / pension (CNSS)"),
    ]),
    ("6. Formation / carrière / mobilité", [
        ("plan_formation", "Plan de formation"),
        ("historique_formations", "Historique des formations suivies"),
        ("certificat_formation", "Certificat de formation"),
        ("demande_formation", "Demande de formation"),
        ("bilan_competences", "Bilan de compétences"),
        ("plan_carriere", "Plan de carrière"),
        ("mobilite_interne", "Dossier de mobilité interne"),
        ("lettre_promotion", "Lettre de promotion"),
        ("decision_augmentation", "Décision d'augmentation"),
        ("changement_grade", "Changement de grade / échelon"),
    ]),
    ("7. Évaluation / performance", [
        ("entretien_annuel", "Entretien annuel d'évaluation"),
        ("objectifs_annuels", "Objectifs annuels"),
        ("compte_rendu_evaluation", "Compte rendu d'évaluation"),
        ("rapport_performance", "Rapport de performance"),
        ("plan_amelioration", "Plan d'amélioration de performance (PIP)"),
        ("felicitation", "Lettre de félicitations"),
    ]),
    ("8. Discipline / contentieux", [
        ("demande_explication", "Demande d'explication"),
        ("avertissement", "Avertissement"),
        ("blame", "Blâme"),
        ("mise_en_demeure", "Mise en demeure"),
        ("convocation_disciplinaire", "Convocation disciplinaire"),
        ("pv_entretien", "Procès-verbal d'entretien disciplinaire"),
        ("mise_a_pied", "Mise à pied"),
        ("notification_sanction", "Notification de sanction"),
        ("dossier_disciplinaire", "Dossier disciplinaire"),
    ]),
    ("9. Fin de contrat / départ", [
        ("lettre_demission", "Lettre de démission"),
        ("accuse_demission", "Accusé de réception de démission"),
        ("lettre_licenciement", "Lettre de licenciement"),
        ("fin_cdd", "Notification de fin de CDD"),
        ("certificat_travail_depart", "Certificat de travail (départ)"),
        ("recu_solde", "Reçu pour solde de tout compte"),
        ("attestation_chomage", "Attestation pour l'ONE (chômage)"),
        ("clearance", "Mainlevée / clearance form"),
        ("exit_interview", "Compte rendu d'entretien de départ"),
    ]),
    ("10. Avantages sociaux", [
        ("tickets_repas", "Tickets repas / carte restaurant"),
        ("pret_employeur", "Dossier de prêt employeur"),
        ("logement_fonction", "Logement de fonction"),
        ("vehicule_fonction", "Véhicule de fonction"),
        ("dotation_materiel", "Dotation de matériel"),
        ("remboursement_transport", "Remboursement transport"),
        ("note_frais", "Note de frais"),
    ]),
    ("11. Fiscalité / obligations légales", [
        ("declaration_fiscale", "Déclaration fiscale annuelle"),
        ("releve_imposable", "Relevé annuel imposable"),
        ("certificat_irpp", "Certificat de retenue à la source (IRPP)"),
        ("cotisations_cnss", "Justificatif de cotisations CNSS"),
    ]),
    ("12. Données personnelles", [
        ("dossier_rh_complet", "Dossier RH complet"),
        ("consentement_donnees", "Consentement / autorisation de traitement des données"),
    ]),
    ("13. Documents collectifs", [
        ("accord_entreprise", "Accord d'entreprise"),
        ("note_service", "Note de service"),
        ("pv_delegues", "PV délégués du personnel"),
        ("politique_rh", "Politique RH (congés, télétravail, harcèlement…)"),
        ("grille_salariale", "Grille salariale"),
    ]),
    ("14. Documents internes (accès limité)", [
        ("budget_formation", "Budget formation"),
        ("bilan_social", "Bilan social"),
        ("rapport_social", "Rapport social annuel"),
        ("autre", "Autre"),
    ]),
]

# Statut : pour ces statuts, la pièce jointe (document signé scanné) est obligatoire
STATUTS_PIECE_REQUISE = ("emis", "signe", "archive")
