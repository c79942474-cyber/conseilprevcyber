"""Générateur de livrables CONSEILPREV — modèles + construction des prompts.

Chaque « type » de livrable définit un intitulé, une description et une trame de
sections. La génération est confiée à un LLM (voir assistant.generate) et ancrée
sur la base de connaissance RAG (voir rag_store) : le modèle s'appuie sur les
extraits internes fournis et sur les informations client saisies par le consultant.

Garde-fous (repris dans le prompt système) :
  - aucun fait, chiffre ou constat spécifique au client n'est inventé — toute
    information manquante est signalée « [à compléter] » ou posée en hypothèse ;
  - le texte normatif IEC n'est jamais reproduit mot pour mot (paraphrase) ;
  - le document produit est un BROUILLON, à relire et valider par un consultant.
"""

# Types de livrables : id -> métadonnées + trame de sections.
TYPES = [
    {
        "id": "synthese-62443",
        "groupe": "Conformité & risques",
        "label": "Synthèse de conformité IEC 62443",
        "desc": "État de conformité (zones & conduits, niveaux SL), écarts et recommandations priorisées.",
        "sections": [
            "Contexte & périmètre",
            "Cartographie zones & conduits",
            "Niveaux de sécurité cibles (SL-T)",
            "Écarts constatés",
            "Recommandations priorisées",
            "Prochaines étapes",
        ],
    },
    {
        "id": "cadrage-amoa",
        "groupe": "Cadrage & stratégie",
        "label": "Note de cadrage — AMOA SI Industriel",
        "desc": "Contexte, objectifs, périmètre, gouvernance, démarche et livrables attendus d'un projet SI industriel.",
        "sections": [
            "Contexte & enjeux",
            "Objectifs de la mission",
            "Périmètre (in / hors périmètre)",
            "Gouvernance & instances",
            "Démarche & jalons",
            "Livrables attendus",
            "Facteurs de risque & points d'attention",
        ],
    },
    {
        "id": "cadrage-amoa-ia-cyber",
        "groupe": "Cadrage & stratégie",
        "label": "Note de cadrage — AMOA intégration IA & Cyber SI",
        "desc": "Cadrage d'un programme de cyberdéfense augmentée par l'IA : exposition du SI, "
                "remédiation à l'échelle, SOC, gouvernance de crise et stratégie d'anticipation.",
        "sections": [
            "Contexte & enjeux (accélération des menaces par l'IA)",
            "Cartographie de l'exposition du SI & priorisation",
            "Chaînes de patching & capacité de remédiation",
            "SOC & cyberdéfense augmentée par l'IA",
            "Gouvernance & gestion de crise",
            "Stratégie d'anticipation (posture proactive)",
            "Gouvernance projet, jalons & comitologie",
            "Indicateurs de pilotage (TTD, MTTR, MTTP, taux d'automatisation)",
        ],
    },
    {
        "id": "analyse-ecarts-nis2",
        "groupe": "Conformité & risques",
        "label": "Analyse d'écarts NIS2",
        "desc": "Assujettissement, écarts par famille d'exigences (gouvernance, mesures de gestion "
                "des risques, notification 24 h/72 h, chaîne d'approvisionnement) et plan de mise "
                "en conformité priorisé — IT et OT.",
        "sections": [
            "Contexte & assujettissement (entité essentielle / importante)",
            "Périmètre analysé (SI, sites, filiales, OT)",
            "Gouvernance & responsabilité de la direction",
            "Écarts par famille de mesures de gestion des risques",
            "Notification d'incidents (24 h / 72 h / rapport final)",
            "Chaîne d'approvisionnement & prestataires",
            "Correspondance avec l'IEC 62443 (périmètre industriel)",
            "Plan de mise en conformité priorisé",
            "Indicateurs de suivi & jalons",
        ],
    },
    {
        "id": "plan-remediation",
        "groupe": "Conformité & risques",
        "label": "Plan de remédiation",
        "desc": "Risques priorisés, mesures d'atténuation, échéancier, responsabilités et indicateurs de suivi.",
        "sections": [
            "Rappel des risques identifiés",
            "Mesures priorisées (P1 / P2 / P3)",
            "Échéancier indicatif",
            "Responsabilités",
            "Indicateurs de suivi",
        ],
    },
    {
        "id": "pssi-ot",
        "groupe": "Politiques & organisation",
        "label": "Politique de sécurité SI industriel (PSSI OT) — trame",
        "desc": "Trame de politique de sécurité des systèmes industriels : principes, gouvernance et mesures par domaine.",
        "sections": [
            "Objet & périmètre",
            "Principes directeurs",
            "Gouvernance & rôles",
            "Gestion des accès & comptes",
            "Segmentation & architecture réseau",
            "Supervision & détection",
            "Gestion des correctifs (IEC 62443-2-3)",
            "Continuité & réponse à incident",
            "Sensibilisation & formation",
        ],
    },
    {
        "id": "analyse-risque",
        "groupe": "Conformité & risques",
        "label": "Synthèse d'analyse de risque (OT)",
        "desc": "Actifs essentiels, sources de risque, scénarios redoutés, évaluation et mesures de traitement.",
        "sections": [
            "Actifs essentiels & biens supports",
            "Sources de risque & menaces",
            "Scénarios redoutés",
            "Évaluation (vraisemblance × impact)",
            "Mesures de traitement",
            "Risques résiduels",
        ],
    },
    {
        "id": "sensibilisation",
        "groupe": "Politiques & organisation",
        "label": "Support de sensibilisation cyber OT",
        "desc": "Messages clés et bonnes pratiques pour les équipes terrain (exploitation, maintenance, automatismes).",
        "sections": [
            "Pourquoi la cybersécurité OT nous concerne",
            "Menaces courantes en environnement industriel",
            "Bonnes pratiques au quotidien",
            "Réflexes en cas d'incident",
            "À retenir",
        ],
    },
    {
        "id": "carto-exposition",
        "groupe": "Programme IA & SOC",
        "label": "Cartographie des expositions SI",
        "desc": "Recensement des actifs exposés (internet, tiers), qualification et matrice de "
                "priorisation des remédiations par exposition réelle.",
        "sections": [
            "Périmètre & méthode de recensement",
            "Inventaire des actifs exposés (internet / tiers)",
            "Qualification (criticité métier, données, surface d'attaque)",
            "Analyse des expositions critiques",
            "Matrice de priorisation des remédiations",
            "Synthèse direction & prochaines étapes",
        ],
    },
    {
        "id": "cible-soc-augmente",
        "groupe": "Programme IA & SOC",
        "label": "Modèle cible SOC augmenté (IA, SOAR, CTI)",
        "desc": "Cible d'un SOC augmenté par l'IA : architecture (détection, SOAR, CTI), cas "
                "d'usage, organisation, gouvernance des usages IA et trajectoire.",
        "sections": [
            "Contexte & limites du dispositif actuel",
            "Ambition & principes du SOC augmenté",
            "Architecture cible (détection, SOAR, CTI, IA)",
            "Cas d'usage IA prioritaires (tri, corrélation, réponse assistée)",
            "Organisation & compétences (rôles, supervision humaine)",
            "Gouvernance des usages IA (AI Act, journalisation, limites)",
            "Trajectoire de mise en œuvre",
            "Indicateurs (TTD, MTTR, taux d'automatisation)",
        ],
    },
    {
        "id": "roadmap-cyber",
        "groupe": "Cadrage & stratégie",
        "label": "Roadmap de transformation cyber",
        "desc": "Feuille de route de transformation : axes, trajectoire par horizon, jalons, "
                "dépendances, gouvernance et indicateurs d'avancement.",
        "sections": [
            "Vision & objectifs de transformation",
            "État de départ (synthèse des diagnostics)",
            "Axes de transformation",
            "Trajectoire par horizon (6 / 12 / 24 mois)",
            "Jalons, dépendances & prérequis",
            "Charge, budget & ressources",
            "Gouvernance de la roadmap",
            "Indicateurs d'avancement",
        ],
    },
    {
        "id": "strategie-ia-cyber",
        "groupe": "Cadrage & stratégie",
        "label": "Stratégie IA cyber groupe",
        "desc": "Doctrine d'emploi de l'IA en cyberdéfense au niveau groupe : principes, domaines "
                "d'application, gouvernance (AI Act, RGPD), articulation filiales et trajectoire.",
        "sections": [
            "Enjeux : l'IA côté attaque et côté défense",
            "Principes directeurs & doctrine d'emploi de l'IA",
            "Domaines d'application (détection, vulnérabilités, réponse, anticipation)",
            "Gouvernance & conformité (AI Act, RGPD, supervision humaine)",
            "Articulation groupe / filiales",
            "Trajectoire & investissements",
            "Risques & garde-fous",
            "Indicateurs de valeur",
        ],
    },
    {
        "id": "gouvernance-crise",
        "groupe": "Politiques & organisation",
        "label": "Plan de gouvernance & gestion de crise",
        "desc": "Gouvernance cyber et dispositif de crise : instances, seuils de déclenchement, "
                "cellule de crise, décision/communication, notification réglementaire, exercices.",
        "sections": [
            "Objectifs & périmètre",
            "Gouvernance cyber (instances, rôles, délégations)",
            "Seuils de déclenchement & niveaux de crise",
            "Organisation de crise (cellule, rôles, suppléances)",
            "Décision & communication (interne, externe, autorités)",
            "Articulation avec la notification réglementaire (NIS2 / DORA)",
            "Programme d'exercices & amélioration continue",
            "Fiches réflexes (trame)",
        ],
    },
    {
        "id": "plan-automatisation-patching",
        "groupe": "Programme IA & SOC",
        "label": "Plan d'automatisation du patching",
        "desc": "Industrialisation des chaînes de correctifs : goulots mesurés (MTTP), cible "
                "d'automatisation par étape, scénario « vague critique », outillage et jalons.",
        "sections": [
            "État des lieux des chaînes de patching",
            "Goulots d'étranglement & délais mesurés (MTTP)",
            "Cible d'automatisation par étape (veille → vérification)",
            "Priorisation par exposition & criticité",
            "Scénario « vague de vulnérabilités critiques » & mode dégradé",
            "Outillage & intégrations",
            "Jalons de mise en œuvre",
            "Indicateurs (MTTP, taux d'automatisation, couverture)",
        ],
    },
    {
        "id": "catalogue-cas-usage",
        "groupe": "Programme IA & SOC",
        "label": "Catalogue de cas d'usage (détection / réponse automatisée)",
        "desc": "Cas d'usage de détection et de réponse automatisée : fiche type, priorisation "
                "valeur × faisabilité, prérequis, supervision humaine et industrialisation.",
        "sections": [
            "Méthode de qualification des cas d'usage",
            "Modèle de fiche (déclencheur, données, action, supervision)",
            "Cas d'usage détection (tri, corrélation, chasse)",
            "Cas d'usage réponse automatisée (confinement, enrichissement, playbooks)",
            "Priorisation (valeur × faisabilité)",
            "Prérequis techniques & données",
            "Gouvernance & supervision humaine",
            "Feuille de route d'industrialisation",
        ],
    },
    {
        "id": "reporting-programme",
        "groupe": "Programme IA & SOC",
        "label": "Reporting programme & indicateurs",
        "desc": "Dispositif de pilotage : architecture des indicateurs (TTD, MTTR, MTTP, "
                "automatisation), tableaux de bord par audience, rituels et trame de rapport.",
        "sections": [
            "Objectifs du reporting & destinataires",
            "Architecture des indicateurs (stratégiques / opérationnels)",
            "Définitions & sources (TTD, MTTR, MTTP, automatisation, couverture)",
            "Tableaux de bord types (direction, programme, opérations)",
            "Rituels & comitologie",
            "Seuils d'alerte & escalade",
            "Trame de rapport mensuel",
        ],
    },

    # ======================================================================
    #  Conseil & transformation — livrables des offres stratégiques
    #  (pages /feuille-de-route, /operating-model, /maturite-ot)
    # ======================================================================

    # --- Thème : Feuille de route & trajectoire -----------------------------
    {
        "id": "fdr-pluriannuelle",
        "groupe": "Conseil — Feuille de route",
        "label": "Feuille de route pluriannuelle jalonnée (horizons & streams)",
        "desc": "Trajectoire de transformation OT cyber par horizons (0–6 / 6–18 / 18–36 mois) "
                "et par streams : jalons, dépendances, charge, budget et indicateurs d'avancement.",
        "sections": [
            "Vision & objectifs de transformation",
            "État de départ (synthèse des diagnostics)",
            "Horizon 1 — quick wins & fondations (0–6 mois)",
            "Horizon 2 — structuration (6–18 mois)",
            "Horizon 3 — cible & optimisation (18–36 mois)",
            "Streams & initiatives associées",
            "Jalons, dépendances & prérequis",
            "Charge, budget & ressources",
            "Gouvernance & pilotage de la trajectoire",
            "Indicateurs d'avancement",
        ],
    },
    {
        "id": "fdr-business-case",
        "groupe": "Conseil — Feuille de route",
        "label": "Business case / dossier de décision",
        "desc": "Dossier de décision pour l'instance dirigeante : options, analyse coûts/bénéfices, "
                "risques d'inaction, trajectoire d'investissement et recommandation.",
        "sections": [
            "Résumé décisionnel (executive summary)",
            "Contexte & enjeux",
            "Options envisagées",
            "Analyse coûts / bénéfices",
            "Risques d'inaction",
            "Investissement & trajectoire budgétaire",
            "Recommandation & décision demandée",
            "Prochaines étapes",
        ],
    },
    {
        "id": "fdr-plan-charge-budget",
        "groupe": "Conseil — Feuille de route",
        "label": "Plan de charge & budget pluriannuel",
        "desc": "Décomposition des charges (internes/externes) et du budget (CAPEX/OPEX) par stream "
                "et par horizon, plan de financement et scénarios.",
        "sections": [
            "Périmètre & hypothèses",
            "Décomposition par stream / chantier",
            "Charges internes / externes",
            "Budget par horizon (CAPEX / OPEX)",
            "Plan de financement",
            "Dépendances & prérequis",
            "Scénarios (ambition vs contrainte)",
            "Suivi budgétaire",
        ],
    },
    {
        "id": "fdr-trajectoire-conformite",
        "groupe": "Conseil — Feuille de route",
        "label": "Trajectoire de conformité NIS2 / IEC 62443",
        "desc": "Trajectoire de mise en conformité jalonnée : assujettissement, écarts prioritaires, "
                "jalons par horizon, mesures, preuves et indicateurs de conformité.",
        "sections": [
            "Cadre réglementaire & assujettissement",
            "État de conformité actuel",
            "Écarts prioritaires (NIS2 & IEC 62443)",
            "Jalons de conformité par horizon",
            "Mesures & responsabilités",
            "Preuves & documentation attendues",
            "Indicateurs de conformité",
            "Points de contrôle & audits",
        ],
    },
    {
        "id": "fdr-tableau-bord",
        "groupe": "Conseil — Feuille de route",
        "label": "Tableau de bord de pilotage (jalons, avancement, risques)",
        "desc": "Dispositif de pilotage de la trajectoire : indicateurs d'avancement, suivi des "
                "risques et du budget, points d'arbitrage et trame de reporting.",
        "sections": [
            "Objet & destinataires",
            "Indicateurs d'avancement (jalons, % de réalisation)",
            "Suivi des risques & alertes",
            "Suivi budgétaire",
            "Points de décision & arbitrages",
            "Rituels & comitologie",
            "Trame de reporting mensuel",
        ],
    },

    # --- Thème : Operating Model & gouvernance ------------------------------
    {
        "id": "om-charte-gouvernance",
        "groupe": "Conseil — Operating Model",
        "label": "Charte de gouvernance OT cyber (mandat, principes, instances)",
        "desc": "Charte fondatrice de la gouvernance de cybersécurité industrielle : mandat, "
                "principes directeurs, instances, rôles et processus de décision.",
        "sections": [
            "Objet & périmètre",
            "Mandat & rattachement",
            "Principes directeurs",
            "Instances & comitologie",
            "Rôles & responsabilités (synthèse)",
            "Processus de décision & escalade",
            "Articulation IT / OT / sûreté",
            "Révision & amélioration continue",
        ],
    },
    {
        "id": "om-raci-roles",
        "groupe": "Conseil — Operating Model",
        "label": "Matrice RACI & fiches de rôle (fonction OT Security)",
        "desc": "Matrice RACI des activités de sécurité OT et fiches de rôle de la fonction "
                "(OT Security Officer, référents de site, relais engineering), interfaces et dimensionnement.",
        "sections": [
            "Périmètre & activités couvertes",
            "Matrice RACI (activités × rôles)",
            "Rôle : OT Security Officer",
            "Rôles : référents cyber de site",
            "Rôles : relais engineering / opérations",
            "Interfaces & suppléances",
            "Dimensionnement (ETP indicatifs)",
        ],
    },
    {
        "id": "om-cartographie-processus",
        "groupe": "Conseil — Operating Model",
        "label": "Cartographie des processus & interfaces IT/OT/engineering/sûreté",
        "desc": "Recensement et description des processus de sécurité OT et de leurs interfaces "
                "avec l'IT, l'engineering, les opérations et la sûreté ; points de contrôle et risques d'interface.",
        "sections": [
            "Objet & méthode",
            "Inventaire des processus cyber OT",
            "Description des processus clés",
            "Interfaces IT ↔ OT",
            "Interfaces engineering & opérations",
            "Interfaces sûreté",
            "Points de contrôle & risques d'interface",
            "Plan d'amélioration",
        ],
    },
    {
        "id": "om-operating-model",
        "groupe": "Conseil — Operating Model",
        "label": "Document d'operating model (organisation cible & mécanismes d'exécution)",
        "desc": "Modèle opérationnel cible complet : organisation, rôles, processus, interfaces, "
                "pilotage, compétences et mécanismes d'exécution (build → run), avec trajectoire de mise en place.",
        "sections": [
            "Constat & ambition",
            "Dimensions du modèle cible",
            "Organisation cible & rôles",
            "Processus & rituels",
            "Interfaces & gouvernance",
            "Pilotage & indicateurs",
            "Compétences & culture",
            "Mécanismes d'exécution (build → run)",
            "Trajectoire de mise en place",
        ],
    },
    {
        "id": "om-comitologie-reporting",
        "groupe": "Conseil — Operating Model",
        "label": "Plan de comitologie & modèle de reporting (instances de direction)",
        "desc": "Cartographie des instances (de l'opérationnel au COMEX), mandats, ordres du jour "
                "types, modèle de reporting par audience et circuit de décision.",
        "sections": [
            "Objectifs & destinataires",
            "Cartographie des instances (opérationnel → COMEX)",
            "Fréquence, participants & mandats",
            "Ordre du jour type par instance",
            "Modèle de reporting par audience",
            "Indicateurs remontés",
            "Circuit de décision & escalade",
        ],
    },
    {
        "id": "om-plan-transition",
        "groupe": "Conseil — Operating Model",
        "label": "Plan de transition & de montée en compétence",
        "desc": "Passage de l'existant à l'organisation cible : étapes de transition, montée en "
                "charge, plan de formation, transfert de compétences et conduite du changement.",
        "sections": [
            "État de départ & cible",
            "Étapes de transition",
            "Plan de montée en charge",
            "Plan de formation & montée en compétence",
            "Transfert de compétences & autonomisation",
            "Conduite du changement",
            "Jalons & indicateurs",
            "Risques de transition",
        ],
    },

    # --- Thème : Maturité & assessment --------------------------------------
    {
        "id": "mat-radar",
        "groupe": "Conseil — Maturité",
        "label": "Radar de maturité par domaine (niveau atteint / cible)",
        "desc": "Évaluation de maturité par domaine sur une échelle 0–5, niveaux atteints et cibles, "
                "radar de synthèse et écarts — appuyée sur IEC 62443 ML / NIST CSF / C2M2.",
        "sections": [
            "Méthode & échelle de maturité (0–5)",
            "Domaines évalués",
            "Niveaux atteints par domaine",
            "Niveaux cibles & justification",
            "Radar de maturité (synthèse)",
            "Écarts par domaine",
            "Priorités de progression",
        ],
    },
    {
        "id": "mat-carto-ecarts",
        "groupe": "Conseil — Maturité",
        "label": "Cartographie des écarts prioritaires & impacts",
        "desc": "Analyse des écarts de maturité par domaine, impacts (métier, conformité, risque), "
                "priorisation gravité × effort et distinction quick wins / chantiers structurants.",
        "sections": [
            "Rappel de la méthode",
            "Écarts par domaine",
            "Analyse d'impact (métier, conformité, risque)",
            "Priorisation (gravité × effort)",
            "Quick wins vs chantiers structurants",
            "Recommandations",
            "Synthèse direction",
        ],
    },
    {
        "id": "mat-benchmark",
        "groupe": "Conseil — Maturité",
        "label": "Benchmark sectoriel",
        "desc": "Positionnement de la maturité OT cyber au regard du secteur : référentiel de "
                "comparaison, écarts vs bonnes pratiques, forces et points de vigilance.",
        "sections": [
            "Objet & méthode du benchmark",
            "Référentiel de comparaison (secteur)",
            "Positionnement par domaine",
            "Écarts vs médiane / bonnes pratiques",
            "Forces & points de vigilance",
            "Enseignements",
            "Recommandations de positionnement",
        ],
    },
    {
        "id": "mat-plan-montee",
        "groupe": "Conseil — Maturité",
        "label": "Plan de montée en maturité (actions séquencées, gains)",
        "desc": "Plan d'actions par domaine pour atteindre la maturité cible : séquencement, gains "
                "attendus, charge, responsabilités et indicateurs de progression.",
        "sections": [
            "Cible de maturité & ambition",
            "Actions par domaine",
            "Séquencement (court / moyen / long terme)",
            "Gains attendus par action",
            "Charge & prérequis",
            "Responsabilités",
            "Indicateurs de progression",
            "Jalons de réévaluation",
        ],
    },
    {
        "id": "mat-restitution-comex",
        "groupe": "Conseil — Maturité",
        "label": "Support de restitution COMEX / CODIR",
        "desc": "Support de restitution des résultats de l'assessment aux décideurs : messages clés, "
                "maturité globale, risques majeurs, comparaison sectorielle et décisions demandées.",
        "sections": [
            "Messages clés (executive summary)",
            "Où en êtes-vous (maturité globale)",
            "Points forts & risques majeurs",
            "Comparaison sectorielle",
            "Priorités & recommandations",
            "Trajectoire & investissements",
            "Décisions demandées",
        ],
    },
    {
        "id": "pca-pra-ot",
        "groupe": "Conseil — Continuité & crise OT",
        "label": "Plan de continuité / reprise OT (PCA-PRA)",
        "desc": "Analyse d'impact par procédé, objectifs de reprise (RTO/RPO), séquences de "
                "redémarrage par zone, modes dégradés et articulation HSE — IEC 62443 & NIS2 art. 21.",
        "sections": [
            "Contexte, périmètre & lignes critiques",
            "Analyse d'impact (BIA) par procédé",
            "Objectifs de reprise (RTO / RPO) par ligne",
            "Scénarios retenus (rançongiciel, perte supervision, perte console d'ingénierie)",
            "Séquences de redémarrage par zone & conduit",
            "Modes dégradés & marche manuelle",
            "Rôles, astreintes & seuils d'escalade (exploitation / HSE / juridique)",
            "Obligations de notification (NIS2 24 h / 72 h)",
            "Maintien en condition & calendrier d'exercices",
        ],
    },
    {
        "id": "politique-sauvegarde-configs",
        "groupe": "Conseil — Continuité & crise OT",
        "label": "Politique de sauvegarde des configurations d'automates",
        "desc": "Inventaire des éléments à sauvegarder (PLC, IHM, recettes, réseau), configuration "
                "de référence versionnée, fréquences, stockage hors ligne et tests de restauration — SR 7.3 / 7.4.",
        "sections": [
            "Périmètre : équipements & éléments de configuration couverts",
            "Configuration de référence (golden config) & versionnement",
            "Fréquences, déclencheurs (avant/après changement) & responsabilités",
            "Stockage : emplacements, génération hors ligne, chiffrement",
            "Tests de restauration : banc, critères, périodicité",
            "Registre des sauvegardes & preuves d'exécution",
            "Écarts connus & plan de mise à niveau",
        ],
    },
    {
        "id": "exercice-crise-ot",
        "groupe": "Conseil — Continuité & crise OT",
        "label": "Exercice de crise OT — scénario & compte rendu",
        "desc": "Scénario d'exercice sur table (rançongiciel atteignant la supervision), déroulé "
                "minuté, rôles, injections, grille d'observation et compte rendu avec actions correctives.",
        "sections": [
            "Objectifs de l'exercice & périmètre",
            "Scénario & chronologie des injections",
            "Participants & rôles (direction, exploitation, cyber, HSE, juridique, communication)",
            "Grille d'observation & critères d'évaluation",
            "Déroulé constaté (à compléter pendant l'exercice)",
            "Constats : ce qui a tenu, ce qui a manqué",
            "Actions correctives datées & porteurs",
            "Prochain exercice recommandé",
        ],
    },
    {
        "id": "procedure-moc",
        "groupe": "Conseil — Gestion des changements (MOC)",
        "label": "Procédure de gestion des changements (MOC) sécurité OT",
        "desc": "Circuit MOC en six étapes : demande & classement, grille d'impact cyber-sûreté, "
                "approbateurs par type et par zone, fenêtres, retour arrière, clôture documentaire — IEC 62443-2-1.",
        "sections": [
            "Objet, périmètre & articulation avec le MOC sûreté (HSE)",
            "Typologie des changements & classement (standard / normal / urgence)",
            "Grille d'analyse d'impact cyber & sûreté (zones, conduits, SL, SIS)",
            "Circuit d'approbation : approbateurs par type et par zone",
            "Fenêtres de maintenance & préparation (sauvegarde préalable, plan de retour arrière)",
            "Exécution, vérification & critères de succès",
            "Clôture : mise à jour des référentiels (inventaire, schémas, configuration de référence)",
            "Indicateurs : changements tracés, urgences, retours arrière",
        ],
    },
    {
        "id": "dossier-architecture-ot",
        "groupe": "Conseil — Architecture & détection",
        "label": "Dossier d'architecture technique OT (DAT)",
        "desc": "Architecture cible : zones et conduits, SL-T par zone, briques retenues "
                "(DMZ industrielle, rebonds, bastions, diodes) et justification de chacune — IEC 62443-3-2/3-3.",
        "sections": [
            "Contexte, périmètre & contraintes d'exploitation",
            "Architecture existante & écarts constatés",
            "Découpage en zones & conduits (IEC 62443-3-2)",
            "Niveaux de sécurité cibles (SL-T) par zone",
            "Architecture cible : schéma & flux autorisés par conduit",
            "Briques retenues & justification (DMZ, rebond, bastion, diode, filtrage)",
            "Accès distant & télémaintenance",
            "Durcissement des équipements (PLC, IHM, station d'ingénierie)",
            "Trajectoire de mise en œuvre & prérequis",
        ],
    },
    {
        "id": "deploiement-sonde-ot",
        "groupe": "Conseil — Architecture & détection",
        "label": "Plan de déploiement d'une sonde de détection OT",
        "desc": "Points de capture, dimensionnement, réglage des règles, cas d'usage de détection "
                "et intégration au SOC/CSIRT — pour Nozomi, Claroty, Dragos ou équivalent.",
        "sections": [
            "Objectifs de détection & périmètre couvert",
            "Points de capture : TAP, port miroir, contraintes par zone",
            "Architecture de collecte & dimensionnement",
            "Phase d'apprentissage & construction de la ligne de base",
            "Réglage : réduction des faux positifs, seuils, exclusions justifiées",
            "Cas d'usage de détection prioritaires",
            "Intégration SOC / CSIRT : remontée de logs, formats, astreinte",
            "Procédures d'escalade & articulation avec la réponse à incident",
            "Indicateurs & revue périodique",
        ],
    },
    {
        "id": "referentiel-durcissement",
        "groupe": "Conseil — Architecture & détection",
        "label": "Référentiel de durcissement par type d'actif",
        "desc": "Configuration de référence et mesures de durcissement pour automates (PLC), "
                "IHM, stations d'ingénierie et postes de supervision, avec les écarts assumés.",
        "sections": [
            "Périmètre & typologie des actifs couverts",
            "Automates (PLC) : services, ports, protection du programme, mode RUN/PROG",
            "IHM & postes opérateur",
            "Stations d'ingénierie : poste dédié, supports amovibles, comptes",
            "Postes de supervision & serveurs SCADA",
            "Comptes, mots de passe par défaut & accès à privilèges",
            "Écarts assumés & mesures compensatoires",
            "Vérification : contrôle de conformité et périodicité",
        ],
    },
    {
        "id": "plan-montee-competence",
        "groupe": "Conseil — Formation & compétences",
        "label": "Plan de montée en compétence — exploitation & maintenance",
        "desc": "Cartographie des compétences, parcours par population (opérateurs, maintenance, "
                "automaticiens, direction), calendrier et évaluation — exigence CSMS IEC 62443-2-1.",
        "sections": [
            "Populations concernées & compétences attendues",
            "État des lieux : évaluation initiale",
            "Parcours par population & modules retenus",
            "Calendrier & charge",
            "Modalités : sur site, en salle, exercices",
            "Évaluation avant / après & critères de réussite",
            "Indicateurs de suivi dans le CSMS",
        ],
    },
    # ── Gestion des changements (MOC) ──────────────────────────────────────
    # La procédure dit ce qu'il faut faire ; ces deux-là sont ce que les équipes
    # remplissent et ce qui prouve que la procédure tourne vraiment. Une
    # procédure sans formulaire ne s'applique pas, et sans registre elle ne
    # se démontre pas devant un auditeur.
    {
        "id": "moc-formulaire-impact",
        "groupe": "Conseil — Gestion des changements (MOC)",
        "label": "Formulaire de demande de changement & analyse d'impact",
        "desc": "Le document que remplit le demandeur : description du changement, actifs et zones "
                "touchés, analyse d'impact cyber et sûreté, plan de retour arrière, approbations. "
                "Utilisable tel quel en papier ou dans un outil de tickets.",
        "sections": [
            "Identification : demandeur, date, urgence, zone & conduits concernés",
            "Description du changement & justification métier",
            "Actifs touches : automates, IHM, reseaux, comptes, flux",
            "Analyse d'impact cyber : exposition, comptes, flux, journalisation",
            "Analyse d'impact sûreté : SIS, interlocks, arrêts d'urgence, procédé",
            "Préparation : sauvegarde préalable, fenêtre, personnels requis",
            "Plan de retour arrière & critères de déclenchement",
            "Tests de vérification après application & critères de succès",
            "Approbations : signataires par type de changement et par zone",
            "Clôture : référentiels mis à jour (inventaire, schémas, configuration de référence)",
        ],
    },
    {
        "id": "moc-registre-revue",
        "groupe": "Conseil — Gestion des changements (MOC)",
        "label": "Registre des changements & revue post-implémentation",
        "desc": "La trace qui prouve que le circuit tourne : registre des changements tracés, revue "
                "périodique des urgences et des retours arrière, écarts constatés et actions. "
                "C'est cette pièce que demande l'auditeur, pas la procédure seule.",
        "sections": [
            "Structure du registre : champs obligatoires & durée de conservation",
            "Rattachement à l'inventaire des actifs & aux zones",
            "Revue périodique : fréquence, participants, ordre du jour type",
            "Analyse des changements en urgence : étaient-ils justifiés ?",
            "Analyse des retours arrière : causes racines & enseignements",
            "Changements appliqués hors circuit : détection & traitement",
            "Indicateurs : part de changements tracés, délai moyen d'approbation, taux d'urgence",
            "Actions correctives datées & suivi jusqu'à clôture",
        ],
    },
    # ── Formation & competences ────────────────────────────────────────────
    # Le plan dit qui doit monter en compétence ; le programme dit ce qu'on
    # enseigne, et le dispositif d'évaluation dit ce qui a été acquis. Sans le
    # troisième, la formation est une dépense sans preuve.
    {
        "id": "form-programme-profils",
        "groupe": "Conseil — Formation & compétences",
        "label": "Programme de formation par profil & supports pédagogiques",
        "desc": "Le contenu réellement enseigné, décliné par profil (opérateurs, maintenance, "
                "automaticiens, IT, direction) : objectifs pédagogiques, durée, déroulé, cas "
                "pratiques issus du site, supports et pré-requis.",
        "sections": [
            "Profils visés & objectifs pédagogiques par profil",
            "Socle commun : ce que tout le monde doit savoir",
            "Module opérateurs & conduite : gestes quotidiens, alertes, remontée",
            "Module maintenance & automaticiens : consoles, supports amovibles, accès distants",
            "Module IT & réseaux : spécificités OT, zones et conduits, ce qui ne se fait pas",
            "Module direction & encadrement : arbitrages, crise, obligations réglementaires",
            "Cas pratiques basés sur le site : incidents plausibles, exercices",
            "Durée, format et rythme par module",
            "Supports remis & conditions de réutilisation interne",
            "Pré-requis, prolongements et parcours de certification",
        ],
    },
    {
        "id": "form-evaluation-habilitations",
        "groupe": "Conseil — Formation & compétences",
        "label": "Dispositif d'évaluation des acquis & suivi des habilitations",
        "desc": "Ce qui transforme une formation en compétence démontrable : évaluation avant/après, "
                "critères de réussite, matrice des habilitations par poste, périodicité de "
                "recyclage et pilotage des écarts.",
        "sections": [
            "Principe : ce qu'on évalue, et ce qu'on n'évalue pas",
            "Évaluation initiale : état des lieux avant formation",
            "Modalités d'évaluation par profil : QCM, mise en situation, observation terrain",
            "Critères de réussite & seuil de validation",
            "Matrice des habilitations : quelle compétence pour quel poste et quelle zone",
            "Périodicité de recyclage & événements déclencheurs (nouvel équipement, incident)",
            "Suivi des écarts : personnes non habilitées sur postes sensibles",
            "Traçabilité : conservation des preuves & articulation avec le CSMS (IEC 62443-2-1)",
            "Indicateurs : taux de couverture, taux de réussite, habilitations échues",
        ],
    },
    # ── Governance by Design IA ────────────────────────────────────────────
    # Les quatre volets de l'offre, plus le cadre de partenariat. Comme tous
    # les autres types, ils heritent SANS RIEN AJOUTER de la chaine complete :
    # build_prompts + retrieval_query (ancrage sur la base de connaissance)
    # -> assistant.generate (Mistral ou Claude) -> export DOCX / PDF depuis
    # l'espace administrateur. Ajouter un livrable, c'est ajouter une entree ici.
    {
        "id": "diagnostic-maturite-ia",
        "groupe": "Conseil — Gouvernance IA",
        "label": "Diagnostic de maturité IA de l'organisation",
        "desc": "Où se situe l'entreprise avant le déploiement : usages existants (déclarés et "
                "non déclarés), parties prenantes, risques organisationnels, préparation "
                "réglementaire ET opérationnelle.",
        "sections": [
            "Contexte, périmètre & méthode du diagnostic",
            "Cartographie des usages IA existants (déclarés)",
            "Usages non déclarés & IA génératives grand public (shadow AI)",
            "Analyse des parties prenantes",
            "Risques organisationnels identifiés",
            "Niveau de préparation réglementaire (AI Act, RGPD, sectoriel)",
            "Niveau de préparation opérationnelle (compétences, processus, outillage)",
            "Synthèse : niveau de maturité & écarts prioritaires",
            "Recommandations séquencées avant mise en production",
        ],
    },
    {
        "id": "charte-gouvernance-ia",
        "groupe": "Conseil — Gouvernance IA",
        "label": "Charte de gouvernance IA & comité",
        "desc": "Qui décide, qui contrôle, qui opère : mandat du comité de gouvernance IA, "
                "composition, fréquence, décisions qui lui reviennent et articulation avec les "
                "instances existantes.",
        "sections": [
            "Objet, périmètre & principes directeurs",
            "Comité de gouvernance IA : mandat & décisions réservées",
            "Composition, fréquence & quorum",
            "Articulation avec les instances existantes (COMEX, comité sécurité, DPO)",
            "Rôles : direction, métiers, IT, conformité/risque, juridique, sécurité, utilisateurs",
            "Escalade & arbitrage en cas de désaccord",
            "Revue annuelle de la charte",
        ],
    },
    {
        "id": "raci-ia",
        "groupe": "Conseil — Gouvernance IA",
        "label": "Matrice RACI IA & processus de validation des nouveaux usages",
        "desc": "Modèle de responsabilités par activité du cycle de vie d'un système d'IA, et "
                "circuit de validation d'un nouvel usage — de l'idée à la mise en production.",
        "sections": [
            "Périmètre : activités du cycle de vie couvertes",
            "Matrice RACI par activité (qualification, données, entraînement, validation, mise en production, suivi, retrait)",
            "Fiches de rôle & compétences attendues",
            "Processus de validation d'un nouvel usage : étapes & points de contrôle",
            "Critères de qualification du risque (AI Act) au point d'entrée",
            "Cas particuliers : IA générative, achat de solution, usage par un tiers",
            "Traçabilité des décisions & registre",
        ],
    },
    {
        "id": "compliance-by-design-ia",
        "groupe": "Conseil — Gouvernance IA",
        "label": "Dossier de conformité by design (AI Act, RGPD, cyber, sectoriel)",
        "desc": "Les exigences réglementaires prises en compte DÈS LA CONCEPTION plutôt que "
                "constatées après déploiement : classification AI Act, base légale et minimisation, "
                "sécurité, exigences sectorielles.",
        "sections": [
            "Description du système & finalité",
            "Classification AI Act & obligations applicables",
            "Protection des données : base légale, minimisation, durées, droits",
            "Analyse d'impact (AIPD / FRIA) : nécessité & périmètre",
            "Exigences de cybersécurité applicables au système et à ses données",
            "Exigences sectorielles spécifiques",
            "Exigences intégrées à la conception : ce qui est tranché AVANT le développement",
            "Points de contrôle par jalon projet",
            "Écarts résiduels & plan de traitement",
        ],
    },
    {
        "id": "politique-usage-ia",
        "groupe": "Conseil — Gouvernance IA",
        "label": "Politique interne d'usage de l'IA",
        "desc": "Le document opposable aux collaborateurs : usages autorisés, encadrés, interdits, "
                "données admissibles, supervision humaine, et conséquences du non-respect.",
        "sections": [
            "Objet, périmètre & personnes concernées",
            "Principes : supervision humaine, transparence, proportionnalité",
            "Usages autorisés, encadrés & interdits",
            "Données admissibles & données proscrites",
            "Obligation de déclaration d'un nouvel usage",
            "Responsabilité de l'utilisateur & vérification des productions",
            "Traitement des manquements",
            "Entrée en vigueur, diffusion & révision",
        ],
    },
    {
        "id": "regles-ia-generative",
        "groupe": "Conseil — Gouvernance IA",
        "label": "Règles d'utilisation des IA génératives",
        "desc": "Le cas le plus répandu et le moins encadré : outils autorisés, données que l'on "
                "n'y met jamais, vérification des productions, propriété intellectuelle et "
                "marquage des contenus (AI Act art. 50).",
        "sections": [
            "Outils autorisés & outils proscrits",
            "Données que l'on ne soumet jamais à un outil génératif",
            "Vérification obligatoire des productions & responsabilité de l'utilisateur",
            "Propriété intellectuelle : entrées et sorties",
            "Transparence & marquage des contenus générés (AI Act art. 50)",
            "Cas d'usage métier : ce qui est encouragé",
            "Signalement d'un incident ou d'une production problématique",
        ],
    },
    {
        "id": "suivi-performance-ia",
        "groupe": "Conseil — Gouvernance IA",
        "label": "Suivi des performances & gestion des évolutions du modèle",
        "desc": "Vivre avec le système une fois déployé : indicateurs de performance et d'équité, "
                "détection de dérive, seuils d'alerte, procédure de réentraînement et de retrait.",
        "sections": [
            "Indicateurs de performance retenus & seuils",
            "Indicateurs d'équité & de biais",
            "Détection de dérive (données et performance) : méthode & fréquence",
            "Seuils d'alerte & conduite à tenir",
            "Procédure d'évolution du modèle : réentraînement, validation, mise en production",
            "Procédure de suspension & de retrait",
            "Journalisation & conservation des preuves",
            "Revue périodique & compte rendu au comité de gouvernance",
        ],
    },
    {
        "id": "indicateurs-gouvernance-ia",
        "groupe": "Conseil — Gouvernance IA",
        "label": "Tableau de bord des indicateurs de gouvernance IA",
        "desc": "Ce que le comité regarde : couverture du registre, usages validés vs constatés, "
                "incidents, conformité documentaire, sensibilisation — avec cible et fréquence.",
        "sections": [
            "Destinataires & fréquence de publication",
            "Indicateurs de couverture (registre, systèmes qualifiés, usages déclarés)",
            "Indicateurs de conformité documentaire (AIPD/FRIA, notices, marquage)",
            "Indicateurs d'exploitation (performance, dérive, incidents)",
            "Indicateurs humains (sensibilisation, formations, déclarations spontanées)",
            "Cibles, seuils d'alerte & sens de lecture de chaque indicateur",
            "Sources de données & mode de collecte",
        ],
    },
    {
        "id": "partenariat-integrateur-ia",
        "groupe": "Conseil — Gouvernance IA",
        "label": "Cadre de partenariat intégrateur IA — répartition des responsabilités",
        "desc": "Pour les intégrateurs, éditeurs et fournisseurs IA : périmètres respectifs, "
                "interfaces, engagements réciproques et offre conjointe technologie + "
                "transformation + gouvernance.",
        "sections": [
            "Objet du partenariat & positionnement respectif",
            "Périmètre du partenaire : technologie, expertise technique, déploiement",
            "Périmètre du cabinet : gouvernance, conformité, maîtrise des risques, ancrage organisationnel",
            "Matrice de responsabilités à l'interface (qui répond de quoi devant le client)",
            "Modalités d'intervention conjointe & jalons partagés",
            "Engagements réciproques : confidentialité, non-sollicitation, propriété des livrables",
            "Offre conjointe : positionnement commercial & argumentaire client",
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  CENTRES DE DONNÉES BAS CARBONE
    #
    #  Ces livrables s'appuient sur datacenter.py, dont les résultats sont
    #  DÉTERMINISTES. La consigne au modèle est explicite là-dessus : il rédige
    #  autour des chiffres, il ne les produit pas et ne les corrige pas. Un
    #  dossier de centre de données se fait vérifier ligne à ligne par un bureau
    #  de contrôle ; un chiffre inventé s'y voit immédiatement, et discrédite
    #  tout le reste du document — y compris ce qui était juste.
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "dc-note-calcul",
        "groupe": "Centres de données",
        "label": "Note de calcul — énergie, eau et carbone",
        "desc": "Note d'ingénierie traçable : PUE, WUE de site et de source, CUE, ERE, "
                "carbone d'exploitation et incorporé. Chaque résultat porte sa formule, "
                "ses entrées, sa source normative et son incertitude.",
        "sections": [
            "Objet, périmètre et hypothèses de calcul",
            "Données d'entrée et leur provenance",
            "Bilan énergétique — PUE et décomposition des pertes",
            "Bilan eau — évaporation, purge, WUE de site et WUE de source",
            "Bilan carbone — exploitation localisée et marché, carbone incorporé",
            "Chaleur fatale — ERF, ERE et conditions de valorisation",
            "Incertitudes et sensibilité des résultats",
            "Limites de l'étude et travaux complémentaires nécessaires",
        ],
    },
    {
        "id": "dc-etude-conception",
        "groupe": "Centres de données",
        "label": "Étude de conception bas carbone",
        "desc": "Comparaison chiffrée des familles de refroidissement pour un site donné, "
                "arbitrage eau / énergie / carbone explicite, et conception retenue avec "
                "ses contreparties assumées.",
        "sections": [
            "Contexte, contraintes de site et exigences du maître d'ouvrage",
            "Climat, ressource en eau et mix électrique du site",
            "Familles de refroidissement examinées et critères d'exclusion",
            "Arbitrage eau / énergie / carbone — le compromis chiffré",
            "Conception retenue et justification",
            "Contreparties assumées et risques résiduels",
            "Trajectoire de performance sur la durée d'exploitation",
        ],
    },
    {
        "id": "dc-reponse-ao",
        "groupe": "Centres de données",
        "label": "Réponse à appel d'offres — volet environnemental",
        "desc": "Mémoire technique environnemental : engagements chiffrés sur PUE, WUE, "
                "carbone et chaleur fatale, méthode de mesure, et conformité au cadre "
                "européen (directive efficacité énergétique, EN 50600, ISO/IEC 30134).",
        "sections": [
            "Compréhension du besoin et des critères d'évaluation",
            "Engagements chiffrés et leur méthode de vérification",
            "Conception technique proposée",
            "Performance énergétique — PUE engagé et conditions de mesure",
            "Sobriété en eau — WUE engagé, saisonnalité, plan en tension hydrique",
            "Trajectoire carbone — exploitation et incorporé",
            "Valorisation de la chaleur fatale et preneur identifié",
            "Conformité réglementaire et normative",
            "Instrumentation, mesure et reporting annuel",
            "Ce sur quoi nous ne nous engageons pas, et pourquoi",
        ],
    },
    {
        "id": "dc-cctp",
        "groupe": "Centres de données",
        "label": "CCTP — clauses de performance environnementale",
        "desc": "Clauses techniques opposables : indicateurs, conditions de mesure, "
                "périodes de référence, pénalités et modalités de vérification. "
                "Un indicateur sans protocole de mesure n'est pas opposable.",
        "sections": [
            "Objet et documents de référence normatifs",
            "Indicateurs contractuels et leurs définitions exactes",
            "Protocole de mesure — points, périodicité, instruments, incertitude admise",
            "Périodes de référence et conditions d'exclusion",
            "Seuils, tolérances et pénalités",
            "Vérification, contre-mesure et arbitrage en cas de litige",
            "Obligations de reporting au titre de la directive efficacité énergétique",
        ],
    },
    {
        "id": "dc-etude-eau",
        "groupe": "Centres de données",
        "label": "Étude de sobriété hydrique",
        "desc": "Bilan d'eau complet — site et amont électrique —, saisonnalité des "
                "prélèvements, confrontation à la ressource locale et plan de réduction.",
        "sections": [
            "Ressource locale et contexte de stress hydrique",
            "Bilan d'eau du site — évaporation, purge, appoint",
            "Eau consommée en amont par la production électrique",
            "Saisonnalité — le prélèvement au pas mensuel, pas l'annuel",
            "Scénarios de réduction et arbitrage avec la consommation d'énergie",
            "Plan de fonctionnement dégradé en période de restriction",
            "Suivi, mesure et engagement auprès des autorités",
        ],
    },
    {
        "id": "dc-chaleur-fatale",
        "groupe": "Centres de données",
        "label": "Étude de valorisation de la chaleur fatale",
        "desc": "Gisement, niveaux de température, schémas de raccordement, économie du "
                "projet et conditions contractuelles avec le preneur de chaleur.",
        "sections": [
            "Gisement thermique et niveaux de température disponibles",
            "Preneurs potentiels et distance de raccordement",
            "Schémas techniques envisagés et relevage éventuel",
            "Bilan carbone du projet — chez le site et chez le preneur",
            "Économie du projet et partage de la valeur",
            "Conditions contractuelles et durée d'engagement",
            "Points bloquants et conditions de réussite",
        ],
    },
    {
        "id": "dc-conformite-eed",
        "groupe": "Centres de données",
        "label": "Dossier de conformité — reporting européen",
        "desc": "Assujettissement au titre de l'article 12 de la directive efficacité "
                "énergétique, grandeurs à déclarer, instrumentation nécessaire et "
                "calendrier de mise en conformité.",
        "sections": [
            "Assujettissement et périmètre de déclaration",
            "Grandeurs exigées et définitions normatives applicables",
            "État de l'instrumentation existante et écarts",
            "Plan d'instrumentation et coût associé",
            "Processus de collecte, de contrôle et de validation annuelle",
            "Calendrier de mise en conformité",
        ],
    },
    {
        "id": "dc-etat-art",
        "groupe": "Centres de données",
        "label": "État de l'art — technologies bas carbone",
        "desc": "Panorama des voies techniques : refroidissement liquide et immersion, "
                "rejet sec, pilotage bas carbone, réemploi. Maturité, conditions "
                "d'emploi et limites de chacune.",
        "sections": [
            "Cadre de l'étude et critères de maturité retenus",
            "Refroidissement liquide direct et immersion",
            "Rejet sec et stratégies sans eau",
            "Pilotage de charge sur signal carbone",
            "Allongement de durée de vie et réemploi",
            "Ce qui reste au stade de la recherche, et ce qui est déployable",
            "Recommandations d'emploi selon le contexte de site",
        ],
    },
]

_BY_ID = {t["id"]: t for t in TYPES}


# ═══════════════════════════════════════════════════════════════════════════
# RATTACHEMENT PAGE ↔ LIVRABLES — source de vérité unique
#
# Chaque page du menu « Conseil & transformation » expose SES livrables, et
# chacun porte son propre lien vers l'espace administrateur. Sans cette table,
# la page et le catalogue divergent en silence : on a vu une page annoncer six
# livrables en prose alors qu'un seul était réellement atteignable.
#
# La table dit quel groupe appartient à quelle page ; le générateur de bloc
# HTML et le test de cohérence lisent tous les deux ici. Ajouter un livrable au
# bon groupe suffit à le faire apparaître sur sa page — il n'y a rien d'autre
# à penser.
# ═══════════════════════════════════════════════════════════════════════════

PAGES_CONSEIL = [
    {"url": "/operating-model", "titre": "Operating Model & gouvernance",
     "groupe": "Conseil — Operating Model"},
    {"url": "/maturite-ot", "titre": "Assessment de maturité",
     "groupe": "Conseil — Maturité"},
    {"url": "/feuille-de-route", "titre": "Feuille de route",
     "groupe": "Conseil — Feuille de route"},
    {"url": "/continuite-ot", "titre": "Continuité & crise OT",
     "groupe": "Conseil — Continuité & crise OT"},
    {"url": "/gestion-des-changements", "titre": "Gestion des changements (MOC)",
     "groupe": "Conseil — Gestion des changements (MOC)"},
    {"url": "/architecture-cible", "titre": "Architecture cible OT",
     "groupe": "Conseil — Architecture & détection"},
    {"url": "/formation", "titre": "Formation & compétences",
     "groupe": "Conseil — Formation & compétences"},
    {"url": "/gouvernance-ia", "titre": "Governance by Design IA",
     "groupe": "Conseil — Gouvernance IA"},
]


def livrables_de_page(url):
    """Les livrables d'une page du menu Conseil & transformation, dans l'ordre
    du catalogue. Rend une liste vide si l'URL n'est pas une page conseil."""
    grp = next((p["groupe"] for p in PAGES_CONSEIL if p["url"] == url), None)
    if not grp:
        return []
    return [t for t in TYPES if t.get("groupe") == grp]


def sante_pages():
    """Aucune page conseil ne doit se retrouver sans livrable, et aucun groupe
    « Conseil — » ne doit exister sans page pour l'exposer : un livrable que
    personne ne peut atteindre depuis le site n'existe pas pour le client."""
    pb = []
    groupes_pages = {p["groupe"] for p in PAGES_CONSEIL}
    for p in PAGES_CONSEIL:
        n = len(livrables_de_page(p["url"]))
        if not n:
            pb.append("page %s : aucun livrable dans le groupe « %s »" % (p["url"], p["groupe"]))
    for t in TYPES:
        g = t.get("groupe", "")
        if g.startswith("Conseil — ") and g not in groupes_pages:
            pb.append("livrable %s : groupe « %s » sans page qui l'expose" % (t["id"], g))
    return {"ok": not pb, "problemes": pb,
            "pages": len(PAGES_CONSEIL), "livrables": len(TYPES),
            "livrables_conseil": sum(len(livrables_de_page(p["url"])) for p in PAGES_CONSEIL)}



def get_type(type_id):
    return _BY_ID.get(type_id)


def public_types():
    """Liste allégée pour l'UI (sans détail interne)."""
    return [{"id": t["id"], "label": t["label"], "desc": t["desc"],
             "groupe": t.get("groupe", "Autres"),
             "sections": t["sections"]} for t in TYPES]


SYSTEM_PROMPT = (
    "Tu es un consultant senior en cybersécurité industrielle (IT / OT / IIoT) chez "
    "CONSEILPREV. Tu rédiges des livrables professionnels en français, clairs, "
    "structurés et actionnables, à destination de responsables industriels (RSSI, "
    "RSSI OT, DSI, direction de site, méthodes/maintenance).\n\n"
    "Règles de rédaction :\n"
    "- Appuie-toi STRICTEMENT sur les informations client fournies et sur les extraits "
    "de la base de connaissance CONSEILPREV donnés en contexte. N'invente AUCUN fait, "
    "chiffre, nom, ni constat spécifique au client. Quand une information manque, écris "
    "« [à compléter] » ou formule une hypothèse explicitement signalée (« Hypothèse : … »).\n"
    "- Ne reproduis jamais le texte normatif IEC 62443 (ou autre) mot pour mot : "
    "reformule et cite la référence (ex. « selon l'approche zones & conduits de l'IEC 62443 »).\n"
    "- Reste factuel et mesuré ; pas de promesses commerciales ni de superlatifs.\n"
    "- Écris en Markdown : titres de section « ## », sous-titres « ### », listes à puces, "
    "et tableaux Markdown lorsque c'est pertinent (ex. écarts, mesures, planning).\n"
    "- Respecte exactement la structure de sections demandée, dans l'ordre.\n"
    "- Le document est un BROUILLON de travail destiné à être relu, complété et validé "
    "par un consultant : ne prétends pas qu'il est définitif.\n"
    "- Mise en forme : phrases complètes en paragraphes suivis (le rendu final est "
    "justifié), listes à puces pour les énumérations, et TABLEAU Markdown dès qu'une "
    "information est comparative ou multi-critères (écarts, mesures, responsabilités, "
    "jalons). Un tableau a toujours une ligne d'en-tête explicite et des cellules "
    "courtes : ne place jamais un paragraphe entier dans une cellule."
)


def dossier_documentaire(sources, choix_manuel=False):
    """Bloc de prompt décrivant les documents RÉELLEMENT retrouvés pour ce livrable.

    Sans lui, le modèle ne reçoit que des extraits anonymes : il ignore combien de
    documents distincts l'alimentent, lesquels le consultant a lui-même désignés,
    et sous quel intitulé exact les citer. Les citations dérivent alors vers des
    titres approximatifs, et rien ne distingue « la base ne dit rien sur ce point »
    de « je n'ai pas cherché ».

    `sources` : liste de dicts {title, theme, visibility, extraits}.
    `choix_manuel` : le consultant a-t-il désigné lui-même les documents ?
    """
    docs = [s for s in (sources or []) if (s.get("title") or "").strip()]
    if not docs:
        return (
            "\n\nDossier documentaire : AUCUN document de la base de connaissance ne "
            "correspond à cette demande. Rédige à partir des seules informations client "
            "ci-dessus et de tes connaissances générales du domaine, en signalant "
            "explicitement, dès l'introduction, que le contenu n'est adossé à aucune "
            "source interne et appelle une validation renforcée. N'invente aucune "
            "citation de document."
        )
    lignes = "\n".join(
        "%d. « %s » — thème : %s — visibilité : %s — %d extrait(s) fourni(s)"
        % (i, (s.get("title") or "").strip(),
           (s.get("theme") or "non classé").strip(),
           "interne" if s.get("visibility") == "internal" else "publique",
           int(s.get("extraits") or 1))
        for i, s in enumerate(docs, 1))
    origine = (
        "Ces documents ont été DÉSIGNÉS PAR LE CONSULTANT : ils font autorité pour ce "
        "livrable. Exploite-les en priorité et couvre-les tous ; si l'un d'eux ne "
        "concerne pas le sujet, dis-le plutôt que de l'ignorer silencieusement."
        if choix_manuel else
        "Ces documents ont été retenus AUTOMATIQUEMENT par pertinence dans la base. "
        "Rien ne garantit qu'ils couvrent tout le sujet : signale les angles morts."
    )
    return (
        "\n\nDossier documentaire mobilisé (%d document(s)) :\n%s\n\n%s\n\n"
        "Exigences de sourçage (elles priment sur le style) :\n"
        "- Cite la source entre crochets avec son intitulé EXACT tel qu'écrit ci-dessus, "
        "par exemple [%s], à l'endroit précis où tu t'appuies dessus — pas seulement en "
        "fin de section.\n"
        "- N'attribue jamais à un document une affirmation absente des extraits fournis ; "
        "en cas de doute, écris « À compléter : … ».\n"
        "- Ne cite aucun document absent de cette liste, même connu par ailleurs.\n"
        "- Termine le livrable par une section « ## Sources mobilisées » présentant, sous "
        "forme de tableau (Document | Thème | Apport dans ce livrable), les seuls "
        "documents que tu as effectivement utilisés.\n"
        "- Si une section de la trame n'est couverte par aucun extrait, écris-le "
        "franchement (« Aucun élément dans la base sur ce point — à compléter ») plutôt "
        "que de la meubler."
        % (len(docs), lignes, origine, (docs[0].get("title") or "").strip())
    )


# Les livrables de centre de données reposent sur une note de calcul produite
# par datacenter.py. Le modèle reçoit ces résultats comme des FAITS.
CONSIGNE_CALCUL = (
    "\n\nNOTE DE CALCUL — RÉSULTATS DÉTERMINISTES\n"
    "Les valeurs ci-dessous ont été calculées par le moteur d'ingénierie de "
    "CONSEILPREV, hors de toute intervention d'un modèle de langage. Elles sont "
    "des FAITS pour ce document.\n"
    "INTERDICTIONS ABSOLUES : ne recalcule aucune de ces valeurs ; ne les arrondis "
    "pas différemment ; ne les contredis pas ; n'en invente aucune autre du même "
    "type. Si un chiffre te paraît surprenant, écris pourquoi — ne le corrige pas. "
    "Ta tâche est d'EXPLIQUER et de METTRE EN PERSPECTIVE ces résultats, pas de les "
    "produire.\n"
    "Reprends chaque valeur avec son unité exacte, et cite sa source normative "
    "quand elle est donnée. Reproduis les avertissements dans la section consacrée "
    "aux limites : ce sont eux qui rendent le document défendable en comité "
    "technique.\n\n"
)


def _bloc_calcul(etude):
    """Met la note de calcul en forme pour le modèle, valeur par valeur.

    On donne la formule et la source AVEC le chiffre. Un modèle à qui l'on
    transmet « PUE 1,175 » brode ; un modèle à qui l'on transmet « PUE 1,175,
    formule E_total/E_IT, ISO/IEC 30134-2, incertitude ±4 % » reformule ce qu'on
    lui a dit. La différence est exactement celle qui se voit en relecture.
    """
    if not isinstance(etude, dict):
        return ""
    lignes = []

    def bloc(titre, section, cles):
        d = etude.get(section) or {}
        dispo = [(k, d[k]) for k in cles if isinstance(d.get(k), dict) and "valeur" in d[k]]
        if not dispo:
            return
        lignes.append("### " + titre)
        for _, v in dispo:
            ligne = "- **%s** : %s %s" % (v["nom"], v["valeur"], v["unite"])
            if v.get("formule"):
                ligne += "  \n  Formule : %s" % v["formule"]
            if v.get("source"):
                ligne += "  \n  Source : %s" % v["source"]
            if v.get("incertitude"):
                ligne += "  \n  Incertitude : %s" % v["incertitude"]
            lignes.append(ligne)

    bloc("Énergie", "energie", ["pue", "energie_it_MWh", "energie_totale_MWh",
                                "energie_non_it_MWh", "dcie"])
    bloc("Eau", "eau", ["evaporation_m3", "purge_m3", "appoint_m3",
                        "wue_site", "wue_source", "eau_amont_m3"])
    bloc("Carbone", "carbone", ["cue", "co2_exploitation_localise_t",
                                "co2_exploitation_marche_t", "ref",
                                "incorpore_serveurs_t", "incorpore_batiment_t",
                                "incorpore_technique_t", "empreinte_totale_t",
                                "part_incorpore_pct"])
    bloc("Chaleur fatale", "chaleur", ["erf", "ere", "energie_reutilisee_MWh"])

    lev = etude.get("leviers") or []
    if lev:
        lignes.append("### Leviers calculés, classés par gain carbone")
        for l in lev:
            lignes.append(
                "- **%s** — %s tCO2e/an, %s m³ d'eau/an, %s MWh/an, %s €/an  \n"
                "  Contrepartie : %s  \n  Condition : %s"
                % (l["titre"], l["gain_co2_t"], l["gain_eau_m3"],
                   l["gain_energie_MWh"], l["gain_euros"],
                   l["contrepartie"], l["condition"]))

    conf = etude.get("conformite") or []
    if conf:
        lignes.append("### Conformité")
        for c in conf:
            lignes.append("- %s — **%s** : %s (%s)"
                          % (c["sujet"], c["statut"], c["detail"], c.get("reference", "")))

    av = etude.get("avertissements") or []
    if av:
        lignes.append("### Avertissements à reproduire dans le document")
        for a in av:
            lignes.append("- " + a)

    return "\n".join(lignes)


def build_prompts(type_id, inputs, context=None):
    """Construit (system, user) pour la génération. `inputs` : dict client/secteur/…"""
    t = get_type(type_id)
    if not t:
        return None
    client = (inputs.get("client") or "").strip() or "[client à préciser]"
    secteur = (inputs.get("secteur") or "").strip() or "[secteur à préciser]"
    perimetre = (inputs.get("perimetre") or "").strip() or "[périmètre à préciser]"
    consignes = (inputs.get("consignes") or "").strip()
    sections = "\n".join("- " + s for s in t["sections"])

    user = (
        "Rédige le livrable suivant, en français, au format Markdown.\n\n"
        "Type de livrable : " + t["label"] + "\n"
        "Client / organisation : " + client + "\n"
        "Secteur d'activité : " + secteur + "\n"
        "Périmètre : " + perimetre + "\n"
    )
    if consignes:
        user += "Consignes particulières : " + consignes + "\n"
    # La note de calcul, quand elle existe, est posée AVANT la structure : le
    # modèle doit avoir les faits en tête au moment où il découvre le plan.
    bloc = _bloc_calcul(inputs.get("etude"))
    if bloc:
        user += CONSIGNE_CALCUL + bloc + "\n"
    user += (
        "\nStructure attendue (une section « ## » par point, dans cet ordre) :\n"
        + sections + "\n\n"
        "Commence par un titre « # " + t["label"] + " — " + client + " » suivi d'une "
        "courte ligne de métadonnées (secteur, périmètre, mention « Brouillon — à valider »). "
        "Puis développe chaque section. Termine par une note rappelant que le document "
        "est un brouillon généré avec l'aide de l'IA, à relire et valider."
    )
    return SYSTEM_PROMPT, user


def build_refine_prompts(type_id, inputs, previous, instructions):
    """Construit (system, user) pour AFFINER un livrable existant selon des ajustements."""
    t = get_type(type_id)
    if not t:
        return None
    client = (inputs.get("client") or "").strip() or "[client à préciser]"
    user = (
        "Tu vas AMÉLIORER un livrable existant selon des ajustements précis.\n\n"
        "Type de livrable : " + t["label"] + "\n"
        "Client / organisation : " + client + "\n\n"
        "Brouillon actuel (Markdown) :\n---\n" + (previous or "")[:12000] + "\n---\n\n"
        "Ajustements demandés :\n" + instructions + "\n\n"
        "Réécris le livrable COMPLET en français, au format Markdown, en appliquant ces "
        "ajustements et en conservant la structure et le contenu pertinent existant. "
        "Respecte les mêmes garde-fous : aucune invention de faits ou de chiffres "
        "spécifiques au client (« [à compléter] » si une information manque), paraphrase "
        "des normes, et conserve la mention « Brouillon — à valider »."
    )
    return SYSTEM_PROMPT, user


def retrieval_query(type_id, inputs):
    """Requête de récupération RAG pour ancrer le livrable."""
    t = get_type(type_id)
    parts = [t["label"] if t else "", inputs.get("secteur") or "",
             inputs.get("perimetre") or "", inputs.get("consignes") or ""]
    return " ".join(p for p in parts if p).strip()
