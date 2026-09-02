# -*- coding: utf-8 -*-
"""INGÉNIERIE DE PROJET — IA FACTORY. L'étude de faisabilité chiffrée d'une usine
d'intelligence artificielle pour un grand compte à infrastructure critique.

CE QUE CE MODULE FAIT, ET CE QU'IL REFUSE DE FAIRE

Il met en ordre une étude de faisabilité : les postes budgétaires, les
ressources, le planning et ses jalons, la conduite du changement, la migration
des systèmes — et il la CHIFFRE à partir des quantités et des prix unitaires que
le client lui donne. Il ne porte AUCUN prix, aucun taux journalier, aucun coût
d'infrastructure. C'est un choix, et c'est le même que celui de l'économiste
de centres de données (econome_dc) : un ratio affiché ici serait une invention
habillée en référentiel, et il serait crédible, ce qui est pire.

CE QU'IL PORTE À LA PLACE, ET QUI DÉCIDE VRAIMENT

  1. DES ANCRAGES PUBLICS, SOURCÉS, AVEC LEUR INCERTITUDE. Le programme Orion
     du groupe BPCE — 800 puis 900 millions d'euros, deux systèmes à unifier,
     cent mille salariés — l'entreprise IA du Crédit Agricole (150 personnes,
     150 millions), la migration manquée de TSB (330 millions de livres, 232
     jours). Chaque chiffre porte sa source, la NATURE de cette source, et ce
     qu'il ne dit pas. Ce sont des ordres de grandeur pour situer une étude ;
     aucun n'est une estimation pour la vôtre.

  2. UNE STRUCTURE DE POSTES QUE LE NEUF NE CONNAÎT PAS. Une usine IA adossée à
     une migration de cœur bancaire n'a pas les mêmes postes qu'une usine IA
     posée sur un système stable : interfaces à porter deux fois, recette en
     double, gel des développements pendant la bascule, coactivité de deux
     équipes de run. Ce sont ces postes qui font déraper, et un chiffrage
     construit sur un ratio « d'usine IA » ne les voit pas — il ne les
     sous-estime pas, il les IGNORE.

  3. DES RELATIONS D'ORDRE, LÀ OÙ ON ATTENDRAIT UN COEFFICIENT. Le module ne
     dit pas « prévoyez 20 % d'aléas ». Il met la provision choisie en regard
     du dépassement DOCUMENTÉ des programmes comparables, et il le signale
     quand elle lui est inférieure. Une comparaison à un chiffre sourcé se
     défend ; un pourcentage inventé, non.

  4. LES JALONS QUI NE SE NÉGOCIENT PAS. Les dates du règlement (UE) 2024/1689
     tel que modifié par le règlement (UE) 2026/1744 sont des jalons du
     planning, au même titre que les jalons projet — mais elles ne bougent pas
     quand le projet glisse. Le planning les distingue.

  5. LE COMPTE DE CE QUI MANQUE. Tout poste sans prix ressort `non_chiffre`
     avec sa raison, et la part non chiffrée de l'étude est publiée. Au-delà
     d'un certain point, un total cesse d'être une estimation pour devenir
     l'addition de ce qu'on savait déjà.

CE QUE LES SOURCES SONT, ET NE SONT PAS. Elles ont été obtenues par recherche
outillée depuis un poste dont le proxy refuse l'accès direct aux sites ; ce
qui est cité est l'EXTRAIT rendu par la recherche, pas la page lue. Chaque
source le dit (`lu: False`). Une adresse qu'on n'a pas pu ouvrir est une
adresse, pas une lecture — et le registre le compte au lieu de le lisser.

CE QU'IL NE FAIT PAS. Il ne remplace ni un cadrage sur pièces, ni une
consultation, ni l'avis d'un contrôleur de gestion. Il met en ordre et il
compte. Les quantités qu'on lui donne, il les croit.
"""
from datetime import date, timedelta

VERSION = "2026-09-a"

# ═══════════════════════════════════════════════════════════════════════════
#  1. LES SOURCES — obtenues, pas lues ; et le registre le dit
# ═══════════════════════════════════════════════════════════════════════════
#
# `nature` : officiel (l'émetteur lui-même), presse, analyste (cabinet,
# éditeur de recherche), fournisseur (un vendeur parlant de son offre),
# juridique (texte publié au Journal officiel). La nature commande le crédit :
# un chiffre de fournisseur sur son propre produit se lit avec la réserve qui
# convient.

SOURCES = {
    "bpce_orion_consultor": {
        "titre": "Le BCG en duo avec Wavestone : les dessous du projet SI de BPCE à 800 millions d'euros",
        "editeur": "Consultor", "nature": "presse", "annee": 2025,
        "url": "https://www.consultor.fr/articles/le-bcg-en-duo-avec-wavestone-les-dessous-du-projet-si-de-bpce-a-800-millions-deuros",
        "lu": False, "reserve": "Extrait de recherche. L'enveloppe de 900 M€ citée dans le cas "
                                 "fourni (automne 2025, « La Lettre ») n'a pas été retrouvée dans "
                                 "une source ouverte : elle est portée comme borne haute non vérifiée.",
    },
    "bpce_orion_cp": {
        "titre": "Le Groupe BPCE investit dans une plateforme technologique commune aux Banques Populaires et aux Caisses d'Épargne",
        "editeur": "Groupe BPCE — espace presse", "nature": "officiel", "annee": 2025,
        "url": "https://newsroom.groupebpce.fr/actualites/le-groupe-bpce-lance-un-projet-de-plateforme-technologique-commune-aux-banques-populaires-et-aux-caisses-depargne-9ff31-7b707.html",
        "lu": False, "reserve": "Communiqué du 5 février 2025 ; page non lue (accès refusé par le proxy).",
    },
    "bpce_ia_cp": {
        "titre": "Le Groupe BPCE accélère l'adoption de l'IA générative et franchit le seuil d'un collaborateur sur deux utilisant l'IA au quotidien",
        "editeur": "Groupe BPCE — espace presse", "nature": "officiel", "annee": 2026,
        "url": "https://newsroom.groupebpce.fr/actualites/le-groupe-bpce-accelere-l-adoption-de-l-intelligence-artificielle-generative-au-service-des-clients-des-conseillers-de-tous-les-collaborateurs-et-franchit-le-seuil-d-un-collaborateur-sur-deux-utilisant-l-ia-au-quotidien-dc22f-7b707.html",
        "lu": False, "reserve": "Extrait de recherche ; chiffres MAiA, voicebot et formation repris de l'extrait.",
    },
    "bpce_gepp_cp": {
        "titre": "Accord GEPP intégrant de manière inédite un volet sur l'intelligence artificielle",
        "editeur": "Groupe BPCE — espace presse", "nature": "officiel", "annee": 2025,
        "url": "https://newsroom.groupebpce.fr/actualites/le-groupe-bpce-signe-un-accord-sur-la-gestion-des-emplois-et-des-parcours-professionnels-integrant-de-maniere-inedite-un-volet-sur-lintelligence-artificielle-3cba1-7b707.html",
        "lu": False, "reserve": "Accord du 29 septembre 2025, triennal, rétroactif au 1er juillet 2025 ; signataires CFE-CGC, CFDT, UNSA (extrait).",
    },
    "ca_ia_cp": {
        "titre": "Le Crédit Agricole accélère sa transformation IA",
        "editeur": "Crédit Agricole — espace presse", "nature": "officiel", "annee": 2026,
        "url": "https://presse.credit-agricole.com/le-credit-agricole-accelere-sa-transformation-ia/?lang=fra",
        "lu": False, "reserve": "Annonce de juin 2026 ; ~500 M€ sur 2026-2028, entreprise IA 150 M€ et ~150 personnes (extrait).",
    },
    "banques_ia_cio": {
        "titre": "Comment les grandes banques investissent dans l'IA",
        "editeur": "CIO Online", "nature": "presse", "annee": 2026,
        "url": "https://www.cio-online.com/actualites/lire-comment-les-grandes-banques-investissent-dans-l-ia-16194.html",
        "lu": False, "reserve": "Société Générale, BNP Paribas, JPMorgan : chiffres repris de l'extrait.",
    },
    "fbf_emploi_2025": {
        "titre": "Solidité des marqueurs de l'emploi dans la banque en 2025",
        "editeur": "Fédération bancaire française", "nature": "officiel", "annee": 2026,
        "url": "https://www.fbf.fr/fr/communique_de_presse/solidite-des-marqueurs-de-lemploi-dans-la-banque-en-2025/",
        "lu": False, "reserve": "368 800 salariés en 2025 (-0,7 %), 186 200 pour les banques AFB (extrait).",
    },
    "bce_ia_newsletter": {
        "titre": "AI's impact on banking: use cases for credit scoring and fraud detection",
        "editeur": "BCE — supervision bancaire", "nature": "officiel", "annee": 2025,
        "url": "https://www.bankingsupervision.europa.eu/press/supervisory-newsletters/newsletter/2025/html/ssm.nl251120_1.en.html",
        "lu": False, "reserve": "« Plus de 85 % des banques supervisées utilisent l'IA » (extrait).",
    },
    "bce_priorites_2026": {
        "titre": "Supervisory priorities 2026-28",
        "editeur": "BCE — supervision bancaire", "nature": "officiel", "annee": 2025,
        "url": "https://www.bankingsupervision.europa.eu/framework/priorities/html/ssm.supervisory_priorities202511.en.html",
        "lu": False, "reserve": "Suivi des stratégies, de la gouvernance et de la gestion des risques IA (extrait).",
    },
    "acpr_reflexion_ia": {
        "titre": "Document de réflexion — Intelligence artificielle : enjeux pour le secteur financier",
        "editeur": "ACPR", "nature": "officiel", "annee": 2018,
        "url": "https://acpr.banque-france.fr/document-de-reflexion-intelligence-artificielle-enjeux-pour-le-secteur-financier",
        "lu": False, "reserve": "Explicabilité, équité, cybersécurité ; l'ACPR a intégré les risques IA au questionnaire SREP 2025 (extraits).",
    },
    "bdf_rapport_ia_2025": {
        "titre": "Rapport sur les impacts juridiques et réglementaires de l'IA dans le secteur financier",
        "editeur": "Banque de France", "nature": "officiel", "annee": 2025,
        "url": "https://www.banque-france.fr/fr/system/files/2025-07/Rapport_68_F_V3.pdf",
        "lu": False, "reserve": "Document PDF non ouvert ; cité sur son titre et sa date (juillet 2025).",
    },
    "ai_act": {
        "titre": "Règlement (UE) 2024/1689 établissant des règles harmonisées concernant l'intelligence artificielle",
        "editeur": "Union européenne", "nature": "juridique", "annee": 2024,
        "url": "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32024R1689",
        "lu": False, "reserve": "Adresse officielle obtenue par le service juridique ; texte non relu ici.",
    },
    "ai_act_consolide": {
        "titre": "Règlement (UE) 2024/1689 — texte consolidé au 27 juillet 2026",
        "editeur": "Union européenne", "nature": "juridique", "annee": 2026,
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02024R1689-20260727",
        "lu": False, "reserve": "Consolidation intégrant le règlement (UE) 2026/1744.",
    },
    "omnibus_2026": {
        "titre": "Règlement (UE) 2026/1744 modifiant le règlement (UE) 2024/1689 (simplification)",
        "editeur": "Union européenne", "nature": "juridique", "annee": 2026,
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32026R1744",
        "lu": False, "reserve": "Règlement du 8 juillet 2026, en vigueur le 27 juillet 2026. Les dates "
                                 "reportées sont reprises d'analyses de cabinets (extraits), pas du texte.",
    },
    "omnibus_analyse": {
        "titre": "EU AI Omnibus enters into force, amending the AI Act",
        "editeur": "White & Case", "nature": "analyste", "annee": 2026,
        "url": "https://www.whitecase.com/insight-alert/eu-ai-omnibus-enters-force-amending-ai-act",
        "lu": False, "reserve": "Annexe III reportée au 2 décembre 2027, annexe I au 2 août 2028 ; article 50 maintenu au 2 août 2026 (extrait).",
    },
    "dora": {
        "titre": "Règlement (UE) 2022/2554 sur la résilience opérationnelle numérique du secteur financier (DORA)",
        "editeur": "Union européenne", "nature": "juridique", "annee": 2022,
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R2554",
        "lu": False, "reserve": "Applicable depuis le 17 janvier 2025 ; adresse officielle obtenue par le service juridique.",
    },
    "tsb_revue": {
        "titre": "TSB Board publishes independent review of 2018 IT Migration (Slaughter and May)",
        "editeur": "TSB Bank", "nature": "officiel", "annee": 2019,
        "url": "https://www.tsb.co.uk/news-releases/slaughter-and-may.html",
        "lu": False, "reserve": "Coût > 330 M£, 232 jours avant retour à la normale, 1,9 M de clients privés "
                                 "d'accès, amendes FCA/PRA 29,8 + 18,9 M£ en 2022 (extraits de couverture).",
    },
    "migration_benchmarks": {
        "titre": "Core systems strategy for banks",
        "editeur": "McKinsey & Company", "nature": "analyste", "annee": 2025,
        "url": "https://www.mckinsey.com/industries/financial-services/our-insights/banking-matters/core-systems-strategy-for-banks",
        "lu": False, "reserve": "Grande banque : 3 à 5 ans, 200 M$ à 1 Md$ ; dépassements ≥ 50 % fréquents ; "
                                 "50 % des transformations de cœur n'atteignent pas leurs objectifs (Gartner, "
                                 "via couverture secondaire).",
    },
    "stanford_2026": {
        "titre": "The 2026 AI Index Report — Economy",
        "editeur": "Stanford HAI", "nature": "analyste", "annee": 2026,
        "url": "https://hai.stanford.edu/ai-index/2026-ai-index-report/economy",
        "lu": False, "reserve": "88 % des organisations utilisent l'IA, 70 % l'IA générative ; gains de "
                                 "productivité ~14 % service client, ~26 % développement (couverture secondaire).",
    },
    "ratios_equipes": {
        "titre": "ML Engineering Team Structure That Scales: Roles, Reporting and Benchmarks",
        "editeur": "KORE1", "nature": "analyste", "annee": 2026,
        "url": "https://www.kore1.com/building-an-ml-engineering-team-structure-that-scales-roles-reporting-and-benchmarks/",
        "lu": False, "reserve": "1 ingénieur plateforme pour 4 à 6 constructeurs de modèles ; 1 data engineer "
                                 "pour 2 à 3 ML/DS en amorçage. Cabinet de recrutement : ratio d'usage, pas une mesure.",
    },
    "gartner_prod": {
        "titre": "Enterprise AI projects failing to reach production (2025)",
        "editeur": "Gartner (via couverture secondaire)", "nature": "analyste", "annee": 2025,
        "url": None,
        "lu": False, "reserve": "« Plus de 55 % des projets IA n'atteignent pas la production » : chiffre "
                                 "rencontré dans plusieurs extraits, adresse primaire non obtenue.",
    },
    "nvidia_dgx": {
        "titre": "NVIDIA DGX Components, Pricing, and other FAQs",
        "editeur": "TRG Datacenters", "nature": "fournisseur", "annee": 2026,
        "url": "https://www.trgdatacenters.com/resource/nvidia-dgx-buyers-guide-everything-you-need-to-know/",
        "lu": False, "reserve": "SuperPOD 7 à 60 M$ ; DGX H200 400 à 500 k$ (revendeur : prix indicatifs).",
    },
    "mistral_prix": {
        "titre": "Pricing — Mistral AI",
        "editeur": "Mistral AI", "nature": "fournisseur", "annee": 2026,
        "url": "https://mistral.ai/pricing/",
        "lu": False, "reserve": "Mistral Large ~0,5 $/M jetons en entrée, ~1,5 $/M en sortie ; -50 % en lot, "
                                 "-90 % sur entrée en cache (extraits). Tarif de fournisseur, périmé sans date.",
    },
    "iea_energy_ai": {
        "titre": "Energy and AI",
        "editeur": "Agence internationale de l'énergie", "nature": "officiel", "annee": 2025,
        "url": "https://www.iea.org/reports/energy-and-ai",
        "lu": False, "reserve": "~945 TWh de consommation des centres de données en 2030 ; énergie par tâche IA "
                                 "divisée par ≥ 10 par an ces dernières années (extraits).",
    },
    "operating_model": {
        "titre": "2026: The year of scale or fail in enterprise AI",
        "editeur": "CIO", "nature": "presse", "annee": 2026,
        "url": "https://www.cio.com/article/4106578/2026-the-year-of-scale-or-fail-in-enterprise-ai.html",
        "lu": False, "reserve": "Modèle hub-and-spoke dominant ; le centre porte plateforme, normes, gouvernance (extrait).",
    },
}


def couverture_sources():
    """Ce qu'un lecteur peut réellement rouvrir, et ce qu'on a réellement lu.

    Deux comptes distincts, parce qu'ils répondent à deux questions : « puis-je
    ouvrir cette adresse » et « l'auteur l'a-t-il ouverte ». Ici la seconde
    réponse est NON pour toutes — et l'écrire vaut mieux que le laisser
    croire."""
    n = len(SOURCES)
    avec = sum(1 for s in SOURCES.values() if s.get("url"))
    lues = sum(1 for s in SOURCES.values() if s.get("lu"))
    par_nature = {}
    for s in SOURCES.values():
        par_nature[s["nature"]] = par_nature.get(s["nature"], 0) + 1
    return {"total": n, "avec_adresse": avec, "lues": lues,
            "part_avec_adresse": round(avec / n, 3) if n else 0.0,
            "par_nature": dict(sorted(par_nature.items())),
            "limite": "Aucune page n'a été ouverte depuis ce poste : les chiffres sont ceux "
                      "des extraits de recherche. Un lecteur doit rouvrir la source avant "
                      "de s'en prévaloir."}


# ═══════════════════════════════════════════════════════════════════════════
#  2. LES ANCRAGES — des ordres de grandeur pour SITUER, jamais pour estimer
# ═══════════════════════════════════════════════════════════════════════════
#
# Chaque ancrage porte : la valeur (ou une fourchette), l'unité, la source,
# et surtout `ne_dit_pas` — ce que le chiffre laisse hors de son périmètre.
# C'est cette dernière ligne qui empêche de le reporter tel quel dans une
# étude qui ne porte pas sur le même objet.

ANCRAGES = [
    {"cle": "orion_budget", "nom": "Programme Orion (BPCE) — enveloppe globale",
     "min": 750, "max": 900, "unite": "M€", "source": "bpce_orion_consultor",
     "ne_dit_pas": "Ni la part de l'IA dans l'enveloppe, ni la répartition build/run, ni "
                   "ce qui relève de la migration Equinoxe/MySys plutôt que de la plateforme."},
    {"cle": "orion_horizon", "nom": "Programme Orion — horizon annoncé",
     "min": 4, "max": 4, "unite": "ans", "source": "bpce_orion_consultor",
     "ne_dit_pas": "Un horizon annoncé au lancement ; les benchmarks de migration de cœur "
                   "documentent des dépassements de 50 % et plus."},
    {"cle": "bpce_effectif", "nom": "Groupe BPCE — effectif",
     "min": 100000, "max": 100000, "unite": "salariés", "source": "bpce_ia_cp",
     "ne_dit_pas": "Ordre de grandeur (« quelque 100 000 »)."},
    {"cle": "bpce_usage_quotidien", "nom": "BPCE — part des salariés utilisant l'IA générative au quotidien",
     "min": 0.5, "max": 0.5, "unite": "part", "source": "bpce_ia_cp",
     "ne_dit_pas": "« Au quotidien » n'est pas défini ; l'usage moyen relevé est de 40 sollicitations "
                   "par mois et par utilisateur (extrait)."},
    {"cle": "bpce_conseillers", "nom": "BPCE — part des conseillers bancaires utilisateurs",
     "min": 0.75, "max": 0.75, "unite": "part", "source": "bpce_orion_consultor",
     "ne_dit_pas": "Chiffre du cas fourni (« La Lettre »), non retrouvé dans un extrait officiel."},
    {"cle": "bpce_appels", "nom": "BPCE — appels traités de bout en bout par un agent vocal",
     "min": 1000000, "max": 1000000, "unite": "appels/an", "source": "bpce_ia_cp",
     "ne_dit_pas": "Sur 12 millions d'appels reçus (cas fourni) ; le taux de résolution et la "
                   "satisfaction ne sont pas publiés."},
    {"cle": "bpce_formes", "nom": "BPCE — collaborateurs formés à l'IA",
     "min": 45000, "max": 45000, "unite": "salariés", "source": "bpce_gepp_cp",
     "ne_dit_pas": "Ni la durée ni le contenu de la formation."},
    {"cle": "ca_plan", "nom": "Crédit Agricole — plan IA 2026-2028",
     "min": 500, "max": 500, "unite": "M€", "source": "ca_ia_cp",
     "ne_dit_pas": "« Près de 500 M€ » ; périmètre groupe (banque, assurance, gestion d'actifs)."},
    {"cle": "ca_entreprise_ia", "nom": "Crédit Agricole — « Entreprise IA » (socle mutualisé)",
     "min": 150, "max": 150, "unite": "M€", "source": "ca_ia_cp",
     "ne_dit_pas": "Effectif visé ~150 personnes ; le chiffre couvre-t-il l'infrastructure ? Non dit."},
    {"cle": "ca_entreprise_ia_etp", "nom": "Crédit Agricole — effectif de l'entreprise IA",
     "min": 150, "max": 150, "unite": "ETP", "source": "ca_ia_cp",
     "ne_dit_pas": "Cible « l'an prochain » ; la ventilation par rôle n'est pas publiée."},
    {"cle": "sg_valeur", "nom": "Société Générale — objectif de valeur créée par l'IA et la donnée",
     "min": 500, "max": 500, "unite": "M€/an", "source": "banques_ia_cio",
     "ne_dit_pas": "« Valeur » n'est pas « économie » : la méthode de mesure n'est pas publiée."},
    {"cle": "bnp_cas", "nom": "BNP Paribas — cas d'usage IA en production",
     "min": 1000, "max": 1000, "unite": "cas d'usage", "source": "banques_ia_cio",
     "ne_dit_pas": "750 à l'automne 2023 ; la taille d'un « cas d'usage » n'est pas définie."},
    {"cle": "fbf_effectif", "nom": "Secteur bancaire français — effectif 2025",
     "min": 368800, "max": 368800, "unite": "salariés", "source": "fbf_emploi_2025",
     "ne_dit_pas": "CDI + CDD + alternants ; -0,7 % sur un an."},
    {"cle": "bce_usage", "nom": "Banques supervisées par la BCE utilisant l'IA",
     "min": 0.85, "max": 1.0, "unite": "part", "source": "bce_ia_newsletter",
     "ne_dit_pas": "« Utiliser l'IA » couvre un pilote comme une production à l'échelle."},
    {"cle": "tsb_cout", "nom": "TSB 2018 — coût de la migration manquée",
     "min": 330, "max": 400, "unite": "M£", "source": "tsb_revue",
     "ne_dit_pas": "330 M£ de coûts de remédiation ; > 400 M£ avec les amendes FCA/PRA de 2022."},
    {"cle": "tsb_duree", "nom": "TSB 2018 — jours avant retour à la normale",
     "min": 232, "max": 232, "unite": "jours", "source": "tsb_revue",
     "ne_dit_pas": "1,9 million de clients privés d'accès en ligne ; 80 000 clients perdus."},
    {"cle": "migration_duree", "nom": "Migration de cœur bancaire, grande banque — durée",
     "min": 3, "max": 5, "unite": "ans", "source": "migration_benchmarks",
     "ne_dit_pas": "De la planification à l'achèvement ; hors dépassements."},
    {"cle": "migration_cout", "nom": "Migration de cœur bancaire, grande banque — coût",
     "min": 200, "max": 1000, "unite": "M$", "source": "migration_benchmarks",
     "ne_dit_pas": "Fourchette d'analyste ; ne distingue pas build et run."},
    {"cle": "migration_depassement", "nom": "Programmes de remplacement de cœur — dépassement fréquent",
     "min": 0.5, "max": 0.5, "unite": "part du budget initial", "source": "migration_benchmarks",
     "ne_dit_pas": "« Souvent ≥ 50 % » : ni médiane ni distribution publiées dans l'extrait."},
    {"cle": "migration_echec", "nom": "Transformations de cœur n'atteignant pas leurs objectifs",
     "min": 0.5, "max": 0.5, "unite": "part", "source": "migration_benchmarks",
     "ne_dit_pas": "Chiffre Gartner rapporté par un tiers ; définition de l'échec non précisée."},
    {"cle": "ia_hors_prod", "nom": "Projets IA d'entreprise n'atteignant pas la production",
     "min": 0.55, "max": 0.55, "unite": "part", "source": "gartner_prod",
     "ne_dit_pas": "Adresse primaire non obtenue : à confirmer avant de s'en prévaloir."},
    {"cle": "ratio_plateforme", "nom": "Ingénieurs plateforme par constructeur de modèles",
     "min": 1 / 6, "max": 1 / 4, "unite": "ETP/ETP", "source": "ratios_equipes",
     "ne_dit_pas": "Ratio d'usage d'un cabinet de recrutement, pas une mesure sectorielle."},
    {"cle": "ratio_data", "nom": "Data engineers par ML/DS (amorçage)",
     "min": 1 / 3, "max": 1 / 2, "unite": "ETP/ETP", "source": "ratios_equipes",
     "ne_dit_pas": "Passe à 1:1 – 1:2 en croissance selon la complexité des données."},
    {"cle": "adoption_orgs", "nom": "Organisations utilisant l'IA dans au moins une fonction",
     "min": 0.88, "max": 0.88, "unite": "part", "source": "stanford_2026",
     "ne_dit_pas": "Enquête déclarative mondiale ; 70 % pour l'IA générative."},
    {"cle": "gain_service_client", "nom": "Gain de productivité mesuré — tâches de service client",
     "min": 0.14, "max": 0.14, "unite": "part", "source": "stanford_2026",
     "ne_dit_pas": "Couverture secondaire du rapport ; études sur des tâches, pas sur des postes."},
    {"cle": "gain_dev", "nom": "Gain de productivité mesuré — développement logiciel",
     "min": 0.26, "max": 0.26, "unite": "part", "source": "stanford_2026",
     "ne_dit_pas": "Idem : gain sur tâches instrumentées, non transposable à un service entier."},
    {"cle": "superpod", "nom": "NVIDIA DGX SuperPOD — prix indicatif",
     "min": 7, "max": 60, "unite": "M$", "source": "nvidia_dgx",
     "ne_dit_pas": "Selon la taille ; hors bâtiment, énergie, refroidissement et exploitation."},
    {"cle": "dgx_h200", "nom": "NVIDIA DGX H200 — prix indicatif unitaire",
     "min": 0.4, "max": 0.5, "unite": "M$", "source": "nvidia_dgx",
     "ne_dit_pas": "Prix revendeur ; les générations se succèdent en moins d'un an."},
    {"cle": "jetons_mistral", "nom": "Mistral Large — prix par million de jetons (entrée / sortie)",
     "min": 0.5, "max": 1.5, "unite": "$/M jetons", "source": "mistral_prix",
     "ne_dit_pas": "Tarif public au jour de la recherche ; -50 % en lot, -90 % sur entrée en cache."},
    {"cle": "energie_par_tache", "nom": "Énergie par tâche IA — rythme d'amélioration",
     "min": 10, "max": 10, "unite": "× par an", "source": "iea_energy_ai",
     "ne_dit_pas": "« Au moins un ordre de grandeur par an ces dernières années » ; pas une garantie."},
]


# ═══════════════════════════════════════════════════════════════════════════
#  3. LES QUANTITÉS — et où un client les trouve réellement
# ═══════════════════════════════════════════════════════════════════════════

QUANTITES = {
    "effectif": {"nom": "Effectif concerné", "unite": "salariés",
                 "ou": "Bilan social ou BDESE ; périmètre des entités qui auront accès à l'usine."},
    "n_metiers": {"nom": "Lignes métier à accompagner", "unite": "métiers",
                  "ou": "Organigramme de premier niveau : banque de détail, crédit, conformité, "
                        "risques, RH, IT, relation client, etc."},
    "n_cas_usage": {"nom": "Cas d'usage visés en production à l'horizon", "unite": "cas",
                    "ou": "Portefeuille arbitré par le comité IA ; à défaut, la liste des pilotes déjà "
                          "menés. Un cas d'usage non nommé n'est pas un cas d'usage."},
    "n_cas_haut_risque": {"nom": "Dont cas relevant de l'annexe III du règlement (UE) 2024/1689",
                          "unite": "cas",
                          "ou": "Évaluation de solvabilité, notation de crédit, tarification "
                                "d'assurance vie et santé, recrutement : la qualification est juridique, "
                                "elle se fait dossier par dossier."},
    "etp_par_cas": {"nom": "Constructeurs de modèles par cas d'usage (ETP)", "unite": "ETP/cas",
                    "ou": "Vos pilotes déjà menés : personnes réellement mobilisées sur un cas "
                          "jusqu'à la production, pas l'effectif nominal de l'équipe."},
    "n_si_source": {"nom": "Systèmes d'information à unifier", "unite": "SI",
                    "ou": "Cartographie applicative ; 1 si l'usine se pose sur un socle stable, "
                          "2 ou plus si elle accompagne une migration de cœur."},
    "n_interfaces": {"nom": "Interfaces à porter vers le socle IA", "unite": "interfaces",
                     "ou": "Cartographie des flux ; compter celles qui devront exister DEUX fois "
                           "pendant une migration."},
    "volume_appels": {"nom": "Appels entrants par an", "unite": "appels/an",
                      "ou": "Statistiques du centre de relation client."},
    "part_appels_ia": {"nom": "Part visée d'appels traités de bout en bout par l'IA", "unite": "part",
                       "ou": "Objectif du comité ; BPCE publie 1 million sur 12 (ancrage, pas cible)."},
    "part_formes": {"nom": "Part des salariés à former", "unite": "part",
                    "ou": "Accord GEPP ou plan de développement des compétences ; BPCE : ~45 000 "
                          "sur ~100 000 (ancrage)."},
    "heures_formation": {"nom": "Heures de formation par salarié formé", "unite": "h",
                         "ou": "Catalogue de formation ; distinguer socle commun et parcours métier."},
    "duree_mois": {"nom": "Horizon de l'étude", "unite": "mois",
                   "ou": "Plan stratégique ; Orion annonce quatre ans (ancrage)."},
    "tokens_mois": {"nom": "Volume d'inférence prévu", "unite": "M jetons/mois",
                    "ou": "Relevés des pilotes (console du fournisseur) ; non instruit s'il n'y en a pas."},
    "jours_cadrage": {"nom": "Jours de cadrage et de gouvernance", "unite": "jours",
                      "ou": "Votre lettre de mission ou devis de conseil ; le module n'en invente pas."},
    "jours_pmo_mois": {"nom": "Jours de pilotage par mois", "unite": "jours/mois",
                       "ou": "Dispositif PMO retenu (pilotage principal + contre-pilotage)."},
    "jours_par_cas": {"nom": "Jours de développement par cas d'usage", "unite": "jours/cas",
                      "ou": "Vos pilotes : jours réellement consommés jusqu'à la production."},
    "jours_recette_interface": {"nom": "Jours de recette par interface", "unite": "jours/interface",
                                "ou": "Retours de la dernière migration ; TSB documente ce que coûte "
                                      "une recette insuffisante."},
}

PRIX = {
    "tjm_conseil": {"nom": "Taux journalier conseil (cadrage, pilotage)", "unite": "€/jour",
                    "ou": "Vos marchés de conseil en cours ; grille d'achats."},
    "tjm_interne": {"nom": "Coût journalier chargé d'un salarié mobilisé", "unite": "€/jour",
                    "ou": "Contrôle de gestion : coût complet chargé / jours ouvrés."},
    "cout_etp_ia": {"nom": "Coût annuel chargé d'un constructeur de modèles", "unite": "€/an",
                    "ou": "Grille RH data science / ML engineering, chargée."},
    "cout_etp_plateforme": {"nom": "Coût annuel chargé d'un ingénieur plateforme / data", "unite": "€/an",
                            "ou": "Grille RH, chargée."},
    "cout_infra_an": {"nom": "Socle d'infrastructure IA (cloud souverain ou sur site)", "unite": "€/an",
                      "ou": "Devis fournisseur ; les prix publics de SuperPOD (7 à 60 M$) situent, "
                            "ils ne chiffrent pas."},
    "cout_outillage_an": {"nom": "Outillage MLOps / LLMOps et licences", "unite": "€/an",
                          "ou": "Devis éditeurs ; licences par utilisateur incluses ici."},
    "cout_securite_an": {"nom": "Sécurité et supervision du socle", "unite": "€/an",
                         "ou": "RSSI : SOC, tests d'intrusion, revue de code modèle."},
    "prix_M_jetons": {"nom": "Prix par million de jetons (moyenne entrée/sortie)", "unite": "€/M jetons",
                      "ou": "Tarif contractuel ; les tarifs publics (Mistral Large 0,5 / 1,5 $) situent."},
    "cout_heure_formation": {"nom": "Coût d'une heure de formation par salarié", "unite": "€/h",
                             "ou": "Service formation : coût complet, temps salarié inclus."},
    "cout_interface": {"nom": "Coût de portage d'une interface", "unite": "€/interface",
                       "ou": "Bordereau de votre intégrateur ; retours de la dernière migration."},
    "cout_audit_cas": {"nom": "Coût d'un dossier de conformité annexe III", "unite": "€/cas",
                       "ou": "Devis de l'organisme ou du cabinet ; inclut la documentation technique "
                             "et l'évaluation de conformité."},
}


# ═══════════════════════════════════════════════════════════════════════════
#  4. LES POSTES — la structure qui reçoit vos prix, groupe par groupe
# ═══════════════════════════════════════════════════════════════════════════
#
# Chaque poste déclare sa FORMULE en clair et les clés qu'elle consomme. Le
# calcul ne fait que l'exécuter ; il ne complète rien.

GROUPES = [
    ("cadrage", "1 · Cadrage, gouvernance et pilotage"),
    ("socle", "2 · Socle plateforme (infrastructure, outillage, sécurité)"),
    ("usine", "3 · Usine IA — l'équipe centrale (hub)"),
    ("cas", "4 · Cas d'usage métier (spokes)"),
    ("changement", "5 · Conduite du changement et formation"),
    ("migration", "6 · Migration et intégration des systèmes"),
    ("conformite", "7 · Conformité et maîtrise des risques"),
    ("run", "8 · Exploitation (run) sur l'horizon"),
    ("aleas", "9 · Provision pour aléas"),
]


def _annees(q):
    return (q.get("duree_mois") or 0) / 12.0


POSTES = [
    {"cle": "cadrage_initial", "groupe": "cadrage", "nom": "Cadrage et étude de faisabilité",
     "formule": "jours_cadrage × tjm_conseil",
     "calc": lambda q, p: q["jours_cadrage"] * p["tjm_conseil"],
     "besoin": ["jours_cadrage", "tjm_conseil"]},
    {"cle": "pilotage", "groupe": "cadrage", "nom": "Pilotage et contre-pilotage sur l'horizon",
     "formule": "jours_pmo_mois × duree_mois × tjm_conseil",
     "calc": lambda q, p: q["jours_pmo_mois"] * q["duree_mois"] * p["tjm_conseil"],
     "besoin": ["jours_pmo_mois", "duree_mois", "tjm_conseil"],
     "note": "Orion sépare pilotage principal (BCG + Wavestone) et lot d'accompagnement "
             "(BPCE Consulting + Very Up) : deux dispositifs, deux lignes."},
    {"cle": "infra", "groupe": "socle", "nom": "Infrastructure IA",
     "formule": "cout_infra_an × années",
     "calc": lambda q, p: p["cout_infra_an"] * _annees(q),
     "besoin": ["cout_infra_an", "duree_mois"]},
    {"cle": "outillage", "groupe": "socle", "nom": "Outillage MLOps / LLMOps et licences",
     "formule": "cout_outillage_an × années",
     "calc": lambda q, p: p["cout_outillage_an"] * _annees(q),
     "besoin": ["cout_outillage_an", "duree_mois"]},
    {"cle": "securite", "groupe": "socle", "nom": "Sécurité et supervision du socle",
     "formule": "cout_securite_an × années",
     "calc": lambda q, p: p["cout_securite_an"] * _annees(q),
     "besoin": ["cout_securite_an", "duree_mois"]},
    {"cle": "equipe_modeles", "groupe": "usine", "nom": "Constructeurs de modèles",
     "formule": "n_cas_usage × etp_par_cas × cout_etp_ia × années",
     "calc": lambda q, p: q["n_cas_usage"] * q["etp_par_cas"] * p["cout_etp_ia"] * _annees(q),
     "besoin": ["n_cas_usage", "etp_par_cas", "cout_etp_ia", "duree_mois"]},
    {"cle": "equipe_plateforme", "groupe": "usine", "nom": "Ingénieurs plateforme et data",
     # LA FORMULE NOMME SES DEUX ENTRÉES. Elle disait « constructeurs », un mot
     # dérivé qui cachait n_cas_usage et etp_par_cas : le lecteur lisait un
     # texte, le calcul consommait deux quantités qu'il ne nommait pas. C'est
     # la règle texte/calcul qui l'a relevé.
     "formule": "n_cas_usage × etp_par_cas × (ratio_plateforme + ratio_data) × cout_etp_plateforme × années",
     "calc": lambda q, p: _dim(q)["plateforme"]["max"] * p["cout_etp_plateforme"] * _annees(q),
     "besoin": ["n_cas_usage", "etp_par_cas", "cout_etp_plateforme", "duree_mois"],
     "note": "Chiffré sur la borne HAUTE des ratios sourcés (1 pour 4, 1 pour 2) : sous-dimensionner "
             "la plateforme est le goulot documenté."},
    {"cle": "cas_usage", "groupe": "cas", "nom": "Développement des cas d'usage",
     "formule": "n_cas_usage × jours_par_cas × tjm_interne",
     "calc": lambda q, p: q["n_cas_usage"] * q["jours_par_cas"] * p["tjm_interne"],
     "besoin": ["n_cas_usage", "jours_par_cas", "tjm_interne"]},
    {"cle": "formation", "groupe": "changement", "nom": "Formation des salariés",
     "formule": "effectif × part_formes × heures_formation × cout_heure_formation",
     "calc": lambda q, p: q["effectif"] * q["part_formes"] * q["heures_formation"] * p["cout_heure_formation"],
     "besoin": ["effectif", "part_formes", "heures_formation", "cout_heure_formation"]},
    {"cle": "ambassadeurs", "groupe": "changement", "nom": "Réseau d'ambassadeurs métier",
     "formule": "n_metiers × jours_par_cas × tjm_interne",
     "calc": lambda q, p: q["n_metiers"] * q["jours_par_cas"] * p["tjm_interne"],
     "besoin": ["n_metiers", "jours_par_cas", "tjm_interne"],
     "note": "Un relais par métier, mobilisé à hauteur d'un cas d'usage : c'est la convention "
             "retenue, écrite ici pour être discutée."},
    {"cle": "interfaces", "groupe": "migration", "nom": "Portage des interfaces",
     "formule": "n_interfaces × cout_interface × (2 si n_si_source > 1, sinon 1)",
     "calc": lambda q, p: q["n_interfaces"] * p["cout_interface"] * (2 if q.get("n_si_source", 1) > 1 else 1),
     "besoin": ["n_interfaces", "cout_interface"],
     "note": "PORTÉES DEUX FOIS pendant une migration de cœur : une fois vers l'ancien socle, "
             "une fois vers le nouveau. C'est le poste que le neuf ne connaît pas."},
    {"cle": "recette", "groupe": "migration", "nom": "Recette des interfaces",
     "formule": "n_interfaces × jours_recette_interface × tjm_interne",
     "calc": lambda q, p: q["n_interfaces"] * q["jours_recette_interface"] * p["tjm_interne"],
     "besoin": ["n_interfaces", "jours_recette_interface", "tjm_interne"]},
    {"cle": "conformite_annexe3", "groupe": "conformite", "nom": "Dossiers de conformité annexe III",
     "formule": "n_cas_haut_risque × cout_audit_cas",
     "calc": lambda q, p: q["n_cas_haut_risque"] * p["cout_audit_cas"],
     "besoin": ["n_cas_haut_risque", "cout_audit_cas"]},
    {"cle": "inference", "groupe": "run", "nom": "Inférence (jetons)",
     "formule": "tokens_mois × 12 × années × prix_M_jetons",
     "calc": lambda q, p: q["tokens_mois"] * 12 * _annees(q) * p["prix_M_jetons"],
     "besoin": ["tokens_mois", "prix_M_jetons", "duree_mois"]},
]


def _nombre(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and f >= 0 else None


def _dim(q):
    """Le dimensionnement de l'équipe centrale, dérivé des seuls ratios sourcés."""
    n = _nombre(q.get("n_cas_usage")) or 0
    k = _nombre(q.get("etp_par_cas")) or 0
    constructeurs = n * k
    r_pl = [a for a in ANCRAGES if a["cle"] == "ratio_plateforme"][0]
    r_da = [a for a in ANCRAGES if a["cle"] == "ratio_data"][0]
    return {
        "constructeurs": {"min": constructeurs, "max": constructeurs,
                          "dit": "n_cas_usage × etp_par_cas — les deux viennent de vous."},
        "plateforme": {"min": constructeurs * (r_pl["min"] + r_da["min"]),
                       "max": constructeurs * (r_pl["max"] + r_da["max"]),
                       "dit": "ingénieurs plateforme (1 pour 4 à 6) + data engineers (1 pour 2 à 3)",
                       "source": "ratios_equipes"},
    }


def dimensionnement(quantites):
    """L'équipe centrale en ETP, avec la fourchette que les ratios impliquent.

    Ne rend rien si les deux quantités manquent : une équipe « de zéro » n'est
    pas une équipe, c'est une case vide."""
    q = {k: _nombre(v) for k, v in (quantites or {}).items()}
    if not q.get("n_cas_usage") or not q.get("etp_par_cas"):
        return {"instruit": False,
                "manque": [k for k in ("n_cas_usage", "etp_par_cas") if not q.get(k)],
                "dit": "Sans le nombre de cas d'usage et l'effectif par cas, aucune équipe ne se "
                       "dimensionne — et le module refuse d'en poser une par défaut."}
    d = _dim(q)
    total_min = d["constructeurs"]["min"] + d["plateforme"]["min"]
    total_max = d["constructeurs"]["max"] + d["plateforme"]["max"]
    ca = [a for a in ANCRAGES if a["cle"] == "ca_entreprise_ia_etp"][0]
    return {"instruit": True, "roles": d,
            "total": {"min": round(total_min, 1), "max": round(total_max, 1)},
            "ancrage": {"nom": ca["nom"], "valeur": ca["max"], "unite": ca["unite"],
                        "ne_dit_pas": ca["ne_dit_pas"]},
            "dit": "Fourchette issue des ratios sourcés ; à comparer à l'entreprise IA du "
                   "Crédit Agricole (~150 ETP) pour situer, pas pour caler."}


def chiffrer(quantites, prix, provision_pct=None):
    """Le chiffrage, poste par poste — et le compte de ce qui n'est pas chiffré.

    Un poste dont une entrée manque ressort `non_chiffre` avec la liste de ce
    qui manque. Il n'est pas compté à zéro : un zéro muet ferait croire que le
    poste n'est pas dû."""
    q = {k: _nombre(v) for k, v in (quantites or {}).items()}
    p = {k: _nombre(v) for k, v in (prix or {}).items()}
    lignes, sous_total, non_chiffres = [], 0.0, []
    for poste in POSTES:
        manque = [k for k in poste["besoin"]
                  if (k in QUANTITES and q.get(k) is None) or (k in PRIX and p.get(k) is None)]
        ligne = {"cle": poste["cle"], "groupe": poste["groupe"], "nom": poste["nom"],
                 "formule": poste["formule"], "note": poste.get("note")}
        if manque:
            ligne.update(statut="non_chiffre", manque=manque, montant=None)
            non_chiffres.append(ligne)
        else:
            try:
                m = float(poste["calc"](q, p))
            except (KeyError, TypeError, ZeroDivisionError):
                m = None
            if m is None:
                ligne.update(statut="non_chiffre", manque=poste["besoin"], montant=None)
                non_chiffres.append(ligne)
            else:
                ligne.update(statut="chiffre", montant=round(m, 2), manque=[])
                sous_total += m
        lignes.append(ligne)
    par_groupe = {}
    for l in lignes:
        g = par_groupe.setdefault(l["groupe"], {"chiffre": 0.0, "non_chiffres": 0})
        if l["statut"] == "chiffre":
            g["chiffre"] += l["montant"]
        else:
            g["non_chiffres"] += 1
    # LA PROVISION : comparée au dépassement DOCUMENTÉ, jamais proposée.
    prov = _nombre(provision_pct)
    depassement = [a for a in ANCRAGES if a["cle"] == "migration_depassement"][0]
    alertes = []
    provision = None
    if prov is None:
        alertes.append("Aucune provision pour aléas n'est saisie : le total ci-dessous est un "
                       "sous-total, pas un budget.")
    else:
        provision = round(sous_total * prov, 2)
        if (q.get("n_si_source") or 1) > 1 and prov < depassement["min"]:
            alertes.append(
                "La provision saisie (%.0f %%) est inférieure au dépassement fréquemment documenté "
                "des programmes de remplacement de cœur (≥ %.0f %%, source %s). Une usine IA "
                "adossée à une migration hérite de l'aléa de la migration."
                % (prov * 100, depassement["min"] * 100, depassement["source"]))
    n = len(lignes)
    part_nc = round(len(non_chiffres) / n, 3) if n else 0.0
    if non_chiffres:
        alertes.append("%d poste(s) sur %d ne sont pas chiffrés : le total est l'addition de ce "
                       "que vous saviez déjà, pas une estimation." % (len(non_chiffres), n))
    return {"ok": True, "version": VERSION, "lignes": lignes, "par_groupe": par_groupe,
            "sous_total": round(sous_total, 2), "provision": provision,
            "provision_pct": prov,
            "total": round(sous_total + (provision or 0.0), 2) if prov is not None else None,
            "n_postes": n, "n_non_chiffres": len(non_chiffres), "part_non_chiffree": part_nc,
            "alertes": alertes, "dimensionnement": dimensionnement(q)}


# ═══════════════════════════════════════════════════════════════════════════
#  5. LE PLANNING — phases du projet, et jalons qui ne se négocient pas
# ═══════════════════════════════════════════════════════════════════════════
#
# Les durées de phases sont l'USAGE DU CABINET : elles sont marquées comme
# telles (`nature: propre`) avec une incertitude de ±50 %. Les jalons
# réglementaires viennent des textes ; ils ne bougent pas avec le projet.

PHASES = [
    {"cle": "faisabilite", "nom": "Cadrage et faisabilité", "mois_min": 2, "mois_max": 4,
     "livrables": ["Note de cadrage", "Portefeuille de cas d'usage arbitré",
                   "Qualification annexe III dossier par dossier", "Cette étude chiffrée"],
     "jalon": "Décision d'engager (comité de direction)"},
    {"cle": "socle", "nom": "Socle et gouvernance", "mois_min": 3, "mois_max": 6,
     "livrables": ["Plateforme (infrastructure, MLOps/LLMOps, sécurité)", "Charte IA et comité",
                   "Registre des systèmes d'IA", "Accord social (type GEPP) ouvert"],
     "jalon": "Socle en service, premier cas déployable"},
    {"cle": "pilotes", "nom": "Pilotes (3 à 5 cas d'usage)", "mois_min": 4, "mois_max": 6,
     "livrables": ["Cas en production supervisée", "Mesure d'adoption et de valeur",
                   "Retours d'expérience chiffrés (jours, ETP, jetons)"],
     "jalon": "Go / no-go d'industrialisation"},
    {"cle": "industrialisation", "nom": "Industrialisation — vague 1", "mois_min": 6, "mois_max": 12,
     "livrables": ["Chaîne de livraison outillée", "Cas d'usage en production par métier",
                   "Formation socle déployée"],
     "jalon": "Part de salariés utilisateurs mesurée (cible à fixer)"},
    {"cle": "generalisation", "nom": "Généralisation", "mois_min": 12, "mois_max": 24,
     "livrables": ["Essaimage dans l'ensemble des métiers", "Run stabilisé, FinOps de l'IA",
                   "Revue de conformité annuelle"],
     "jalon": "Objectifs du plan stratégique tenus ou révisés"},
]

MIGRATION = {"nom": "Migration de cœur (si n_si_source > 1)", "mois_min": 36, "mois_max": 60,
             "source": "migration_benchmarks",
             "dit": "3 à 5 ans documentés pour une grande banque ; l'usine IA la chevauche, elle "
                    "ne l'attend pas — mais elle porte ses interfaces deux fois."}

JALONS_REGLEMENTAIRES = [
    {"date": "2025-01-17", "texte": "DORA — règlement (UE) 2022/2554 applicable",
     "source": "dora", "porte": "Registre des prestataires TIC, tests de résilience, gestion des incidents : "
                                "un fournisseur de modèle est un prestataire TIC."},
    {"date": "2025-02-02", "texte": "Règlement (UE) 2024/1689 — pratiques interdites (article 5)",
     "source": "ai_act", "porte": "Applicable ; à vérifier sur chaque cas d'usage avant tout pilote."},
    {"date": "2025-08-02", "texte": "Règlement (UE) 2024/1689 — obligations des fournisseurs de modèles à usage général",
     "source": "ai_act", "porte": "Vos fournisseurs ; à exiger contractuellement."},
    {"date": "2026-08-02", "texte": "Règlement (UE) 2024/1689 — transparence (article 50), maintenu par le règlement 2026/1744",
     "source": "omnibus_analyse", "porte": "Marquage lisible par machine et information des personnes : "
                                          "en vigueur, y compris pour un agent vocal."},
    {"date": "2027-12-02", "texte": "Systèmes à haut risque de l'annexe III — date reportée par le règlement (UE) 2026/1744",
     "source": "omnibus_analyse", "porte": "Notation de crédit, solvabilité, tarification assurance : "
                                          "dossiers de conformité à jour avant cette date."},
    {"date": "2028-08-02", "texte": "Systèmes à haut risque de l'annexe I — date reportée par le règlement (UE) 2026/1744",
     "source": "omnibus_analyse", "porte": "IA intégrée à des produits couverts par la législation "
                                          "d'harmonisation : rarement le cas d'une banque."},
]


def planning(quantites, debut=None):
    """Les phases posées bout à bout à partir d'une date, et les jalons
    réglementaires placés dans le même calendrier — marqués comme tels.

    Les phases glissent si le projet glisse ; les jalons réglementaires, non.
    C'est pour cela qu'ils ne sont pas dans la même liste."""
    q = {k: _nombre(v) for k, v in (quantites or {}).items()}
    d0 = debut or date.today()
    if isinstance(d0, str):
        d0 = date.fromisoformat(d0)
    out, cur_min, cur_max = [], d0, d0
    for ph in PHASES:
        deb_min, deb_max = cur_min, cur_max
        cur_min = deb_min + timedelta(days=int(ph["mois_min"] * 30.44))
        cur_max = deb_max + timedelta(days=int(ph["mois_max"] * 30.44))
        out.append({"cle": ph["cle"], "nom": ph["nom"], "nature": "propre",
                    "incertitude": "±50 % (usage du cabinet, pas une mesure)",
                    "mois_min": ph["mois_min"], "mois_max": ph["mois_max"],
                    "debut_tot": deb_min.isoformat(), "fin_tot": cur_min.isoformat(),
                    "fin_tard": cur_max.isoformat(),
                    "livrables": ph["livrables"], "jalon": ph["jalon"]})
    migration = None
    if (q.get("n_si_source") or 1) > 1:
        migration = dict(MIGRATION, debut=d0.isoformat(),
                         fin_tot=(d0 + timedelta(days=int(MIGRATION["mois_min"] * 30.44))).isoformat(),
                         fin_tard=(d0 + timedelta(days=int(MIGRATION["mois_max"] * 30.44))).isoformat())
    fin_projet_tard = cur_max
    regl = []
    for j in JALONS_REGLEMENTAIRES:
        dj = date.fromisoformat(j["date"])
        regl.append(dict(j, passe=dj <= d0, avant_fin_projet=dj <= fin_projet_tard,
                         nature="reglementaire"))
    return {"debut": d0.isoformat(), "phases": out,
            "fin_projet": {"tot": cur_min.isoformat(), "tard": cur_max.isoformat()},
            "migration": migration, "jalons_reglementaires": regl,
            "dit": "Les phases sont des durées d'usage, à ±50 %. Les jalons réglementaires sont des "
                   "dates de textes : ils tombent où ils tombent, projet en retard ou non."}


# ═══════════════════════════════════════════════════════════════════════════
#  6. LA CONDUITE DU CHANGEMENT ET LA MIGRATION — ce qui se décide, pas ce qui se chiffre
# ═══════════════════════════════════════════════════════════════════════════

LEVIERS_CHANGEMENT = [
    {"cle": "accord_social", "nom": "Un accord social dédié, signé avant le déploiement",
     "ancrage": "bpce_gepp_cp",
     "dit": "BPCE a intégré un volet IA à son accord GEPP triennal, signé à l'unanimité des "
            "organisations représentatives. Un déploiement sans cadre négocié se paie en "
            "adoption — et en contentieux."},
    {"cle": "formation_socle", "nom": "Un socle de formation pour tous, puis des parcours par métier",
     "ancrage": "bpce_formes",
     "dit": "~45 000 formés sur ~100 000 chez BPCE au moment où l'usage quotidien atteint un "
            "salarié sur deux. La corrélation n'est pas une causalité ; l'ordre, lui, est clair."},
    {"cle": "mesure_adoption", "nom": "Une mesure d'adoption publiée, pas un objectif affiché",
     "ancrage": "bpce_usage_quotidien",
     "dit": "« 40 sollicitations par mois et par utilisateur » est une mesure ; « 50 % d'utilisateurs » "
            "en est une autre. Fixez les deux, et publiez-les en interne à cadence fixe."},
    {"cle": "ambassadeurs", "nom": "Un relais par métier, formé avant les autres",
     "ancrage": None,
     "dit": "La ressource rare n'est ni le data scientist ni le GPU : c'est la personne qui "
            "connaît le métier ET l'outil. Elle se forme, elle ne se recrute pas."},
    {"cle": "article_4", "nom": "La maîtrise de l'IA (article 4) comme obligation de moyens, tracée",
     "ancrage": "omnibus_analyse",
     "dit": "Le règlement 2026/1744 reformule l'article 4 en obligation de prendre des mesures : "
            "moins exigeant sur le résultat, toujours contraignant sur la trace."},
]

PRINCIPES_MIGRATION = [
    {"cle": "pas_de_big_bang", "nom": "Pas de bascule unique",
     "ancrage": "tsb_revue",
     "dit": "TSB : une bascule en un événement, une recette insuffisante, 232 jours de "
            "perturbation, > 330 M£. La revue indépendante nomme la méthode, pas la malchance."},
    {"cle": "interfaces_deux_fois", "nom": "Compter chaque interface deux fois",
     "ancrage": "migration_benchmarks",
     "dit": "Pendant une migration de cœur, l'usine IA consomme l'ancien socle ET le nouveau. "
            "Le poste existe dans ce module ; il n'existe dans aucun ratio."},
    {"cle": "gel", "nom": "Un gel des évolutions IA autour de la bascule, daté",
     "ancrage": None,
     "dit": "Une semaine de gel coûte des jours ; une régression sur un cas en production "
            "pendant la bascule coûte la confiance. Le gel se planifie, il ne se subit pas."},
    {"cle": "provision", "nom": "Une provision alignée sur le dépassement documenté",
     "ancrage": "migration_depassement",
     "dit": "Les remplacements de cœur dépassent souvent de 50 % et plus. Ce module ne propose "
            "pas de taux ; il signale quand le vôtre est inférieur à ce chiffre."},
]


def comparables():
    """Les cas publics, avec leur source et ce qu'ils ne disent pas."""
    idx = {a["cle"]: a for a in ANCRAGES}
    def a(cle):
        x = idx[cle]
        return {"nom": x["nom"], "min": x["min"], "max": x["max"], "unite": x["unite"],
                "source": x["source"], "ne_dit_pas": x["ne_dit_pas"]}
    return [
        {"organisation": "Groupe BPCE — programme Orion et usine IA",
         "chiffres": [a("orion_budget"), a("orion_horizon"), a("bpce_effectif"),
                      a("bpce_usage_quotidien"), a("bpce_appels"), a("bpce_formes")],
         "lecon": "Un socle commun décidé pour porter l'IA ; l'adoption a précédé le socle. "
                  "La migration de deux SI est le risque dominant, pas l'IA."},
        {"organisation": "Crédit Agricole — plan IA et « Entreprise IA »",
         "chiffres": [a("ca_plan"), a("ca_entreprise_ia"), a("ca_entreprise_ia_etp")],
         "lecon": "Le seul cas français qui publie à la fois un budget de socle et un effectif "
                  "de socle : le ratio le plus proche d'une usine IA de groupe."},
        {"organisation": "Société Générale et BNP Paribas",
         "chiffres": [a("sg_valeur"), a("bnp_cas")],
         "lecon": "Des objectifs de valeur et des comptes de cas d'usage — sans définition publiée "
                  "de l'un ni de l'autre. À citer, pas à recopier."},
        {"organisation": "TSB (2018) — la migration manquée",
         "chiffres": [a("tsb_cout"), a("tsb_duree")],
         "lecon": "Le contre-exemple documenté par une revue indépendante : bascule unique, "
                  "recette insuffisante, gouvernance."},
    ]


def referentiel():
    """Tout ce que la page affiche. Rien n'est recopié dans la page."""
    return {"version": VERSION,
            "quantites": QUANTITES, "prix": PRIX,
            "groupes": GROUPES,
            "postes": [{k: v for k, v in p.items() if k != "calc"} for p in POSTES],
            "ancrages": ANCRAGES, "sources": SOURCES,
            "couverture_sources": couverture_sources(),
            "phases": PHASES, "migration": MIGRATION,
            "jalons_reglementaires": JALONS_REGLEMENTAIRES,
            "leviers_changement": LEVIERS_CHANGEMENT,
            "principes_migration": PRINCIPES_MIGRATION,
            "comparables": comparables(),
            "limite": "Ce module ne porte aucun prix : il chiffre les vôtres. Ses ancrages "
                      "situent ; ils n'estiment pas. Ses sources ont été obtenues, pas lues."}


def sante():
    return {"module": "ia_factory", "version": VERSION,
            "postes": len(POSTES), "ancrages": len(ANCRAGES),
            "sources": len(SOURCES), "phases": len(PHASES),
            "jalons_reglementaires": len(JALONS_REGLEMENTAIRES)}
