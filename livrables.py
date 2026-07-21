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
]

_BY_ID = {t["id"]: t for t in TYPES}


def get_type(type_id):
    return _BY_ID.get(type_id)


def public_types():
    """Liste allégée pour l'UI (sans détail interne)."""
    return [{"id": t["id"], "label": t["label"], "desc": t["desc"],
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
