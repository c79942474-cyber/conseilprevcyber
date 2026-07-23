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
]

_BY_ID = {t["id"]: t for t in TYPES}


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
    "par un consultant : ne prétends pas qu'il est définitif."
)


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
