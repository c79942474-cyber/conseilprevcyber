# -*- coding: utf-8 -*-
"""INGÉNIERIE DE PROJET — IA FACTORY. L'étude de faisabilité chiffrée d'une usine
d'intelligence artificielle pour un grand compte à infrastructure critique :
banque, assurance, marchés financiers, et les entités essentielles ou
importantes de la directive NIS2.

CE QUE CE MODULE FAIT, ET CE QU'IL REFUSE DE FAIRE

Il met en ordre une étude de faisabilité : les postes budgétaires, les
ressources, le planning et ses jalons, la conduite du changement, la migration
des systèmes, les exigences propres à chaque secteur — et il la CHIFFRE à
partir des quantités et des prix unitaires que le client lui donne. Il ne porte
AUCUN prix, aucun taux journalier, aucun coût d'infrastructure. C'est un choix,
et c'est le même que celui de l'économiste de centres de données (econome_dc) :
un ratio affiché ici serait une invention habillée en référentiel, et il
serait crédible, ce qui est pire.

IL NE NOMME AUCUNE ENTREPRISE NI AUCUNE PERSONNE. Les cas comparables sont
anonymisés — cas A, B, C, D — et décrits par ce qui compte pour l'étude : la
taille, le nombre de systèmes, ce qui a été publié et ce qui ne l'a pas été.
Les éditeurs des sources sont désignés par leur nature (autorité publique,
texte juridique, cabinet, média, fournisseur). Les ADRESSES des sources sont
conservées : une source sans adresse est une intention, pas une source, et un
lecteur doit pouvoir la rouvrir.

CE QU'IL PORTE À LA PLACE, ET QUI DÉCIDE VRAIMENT

  1. DES ANCRAGES PUBLICS, SOURCÉS, AVEC LEUR INCERTITUDE. Chaque chiffre porte
     sa source, la nature de cette source, et ce qu'il NE DIT PAS. Ce sont des
     ordres de grandeur pour situer une étude ; aucun n'est une estimation pour
     la vôtre.

  2. UNE STRUCTURE DE POSTES QUE LE NEUF NE CONNAÎT PAS. Une usine IA adossée à
     une migration de cœur n'a pas les mêmes postes qu'une usine IA sur socle
     stable : interfaces portées deux fois, recette en double, gel autour de la
     bascule. Chaque poste dit ce qu'il COUVRE et ce qu'il EXCLUT.

  3. DES POSTES PROPRES À CHAQUE SECTEUR. Un registre de prestataires TIC en
     banque, une validation actuarielle en assurance, un dossier de sûreté par
     composant de sécurité chez un opérateur d'infrastructure critique : ces
     postes n'apparaissent dans aucun ratio « d'usine IA », et ce sont eux qui
     font la différence entre une étude générique et une étude recevable.

  4. DES RELATIONS D'ORDRE, LÀ OÙ ON ATTENDRAIT UN COEFFICIENT. Le module ne
     propose pas de taux d'aléas : il compare celui qu'on saisit au dépassement
     DOCUMENTÉ des programmes comparables, et il signale l'écart.

  5. LES JALONS QUI NE SE NÉGOCIENT PAS. Les dates des textes — règlement sur
     l'IA tel que modifié en 2026, DORA, NIS2, Solvabilité II révisée — sont des
     jalons du planning qui ne bougent pas quand le projet glisse. Le planning
     les distingue des phases, qui glissent.

  6. LE COMPTE DE CE QUI MANQUE. Tout poste sans prix ressort `non_chiffre` avec
     sa raison, et la part non chiffrée de l'étude est publiée.

CE QUE LES SOURCES SONT, ET NE SONT PAS. Elles ont été obtenues par recherche
outillée depuis un poste dont le proxy refuse l'accès direct aux sites ; ce
qui est cité est l'EXTRAIT rendu par la recherche, pas la page lue. Chaque
source le dit (`lu: False`). Le registre compte cela au lieu de le lisser.

CE QU'IL NE FAIT PAS. Il ne qualifie aucun système au sens du règlement sur
l'IA — c'est une analyse juridique, dossier par dossier — et il ne remplace ni
un cadrage sur pièces, ni une consultation, ni un contrôleur de gestion. Il
met en ordre et il compte. Les quantités qu'on lui donne, il les croit.
"""
from datetime import date, timedelta

VERSION = "2026-09-b"

# ═══════════════════════════════════════════════════════════════════════════
#  1. LES SOURCES — obtenues, pas lues ; éditeurs désignés par leur nature
# ═══════════════════════════════════════════════════════════════════════════
#
# `nature` : officiel (une autorité ou un organisme public, l'émetteur
# lui-même), juridique (texte publié au Journal officiel), analyste (cabinet,
# éditeur de recherche, cabinet d'avocats), presse (média), fournisseur (un
# vendeur parlant de son offre). La nature commande le crédit qu'on accorde.

SOURCES = {
    # ── le cas A : un grand groupe bancaire coopératif, deux réseaux, deux SI ──
    "casA_programme_presse": {
        "titre": "Programme de plateforme technologique commune à deux réseaux bancaires — pilotage confié à un groupement de cabinets",
        "editeur": "Média spécialisé du conseil", "nature": "presse", "annee": 2025,
        "url": "https://www.consultor.fr/articles/le-bcg-en-duo-avec-wavestone-les-dessous-du-projet-si-de-bpce-a-800-millions-deuros",
        "lu": False, "reserve": "Extrait de recherche. L'enveloppe de 900 M€ citée dans le cas fourni "
                                 "(automne 2025) n'a pas été retrouvée dans une source ouverte : elle est "
                                 "portée comme borne haute non vérifiée.",
    },
    "casA_programme_cp": {
        "titre": "Communiqué : investissement dans une plateforme technologique commune aux deux réseaux du groupe",
        "editeur": "Groupe bancaire coopératif — espace presse", "nature": "officiel", "annee": 2025,
        "url": "https://newsroom.groupebpce.fr/actualites/le-groupe-bpce-lance-un-projet-de-plateforme-technologique-commune-aux-banques-populaires-et-aux-caisses-depargne-9ff31-7b707.html",
        "lu": False, "reserve": "Communiqué du 5 février 2025 ; page non lue (accès refusé par le proxy).",
    },
    "casA_ia_cp": {
        "titre": "Communiqué : un collaborateur sur deux utilise l'IA générative au quotidien",
        "editeur": "Groupe bancaire coopératif — espace presse", "nature": "officiel", "annee": 2026,
        "url": "https://newsroom.groupebpce.fr/actualites/le-groupe-bpce-accelere-l-adoption-de-l-intelligence-artificielle-generative-au-service-des-clients-des-conseillers-de-tous-les-collaborateurs-et-franchit-le-seuil-d-un-collaborateur-sur-deux-utilisant-l-ia-au-quotidien-dc22f-7b707.html",
        "lu": False, "reserve": "Extrait de recherche ; usage mensuel, agent vocal et formation repris de l'extrait.",
    },
    "casA_accord_social": {
        "titre": "Communiqué : accord de gestion des emplois et des parcours professionnels intégrant un volet sur l'IA",
        "editeur": "Groupe bancaire coopératif — espace presse", "nature": "officiel", "annee": 2025,
        "url": "https://newsroom.groupebpce.fr/actualites/le-groupe-bpce-signe-un-accord-sur-la-gestion-des-emplois-et-des-parcours-professionnels-integrant-de-maniere-inedite-un-volet-sur-lintelligence-artificielle-3cba1-7b707.html",
        "lu": False, "reserve": "Accord du 29 septembre 2025, triennal, rétroactif au 1er juillet 2025, signé par "
                                 "trois organisations représentatives (extrait).",
    },
    # ── le cas B : un grand groupe bancaire universel, plan IA triennal ──
    "casB_plan_cp": {
        "titre": "Communiqué : accélération de la transformation IA — plan triennal et entité IA mutualisée",
        "editeur": "Groupe bancaire universel — espace presse", "nature": "officiel", "annee": 2026,
        "url": "https://presse.credit-agricole.com/le-credit-agricole-accelere-sa-transformation-ia/?lang=fra",
        "lu": False, "reserve": "Annonce de juin 2026 ; ~500 M€ sur 2026-2028, entité IA dotée de 150 M€ "
                                 "et d'environ 150 personnes (extrait).",
    },
    # ── le cas C : deux banques universelles, objectifs et comptes publiés ──
    "casC_presse": {
        "titre": "Comment les grandes banques investissent dans l'IA",
        "editeur": "Média spécialisé des directions informatiques", "nature": "presse", "annee": 2026,
        "url": "https://www.cio-online.com/actualites/lire-comment-les-grandes-banques-investissent-dans-l-ia-16194.html",
        "lu": False, "reserve": "Objectif de valeur annuelle et compte de cas d'usage repris de l'extrait.",
    },
    # ── le cas D : une banque de détail, migration manquée ──
    "casD_revue": {
        "titre": "Revue indépendante de la migration informatique de 2018 — publication par le conseil d'administration",
        "editeur": "Banque de détail — espace presse", "nature": "officiel", "annee": 2019,
        "url": "https://www.tsb.co.uk/news-releases/slaughter-and-may.html",
        "lu": False, "reserve": "Coût > 330 M£, 232 jours avant retour à la normale, 1,9 M de clients privés "
                                 "d'accès, amendes des deux autorités britanniques en 2022 (extraits de couverture).",
    },
    # ── le secteur et ses autorités ──
    "fbf_emploi_2025": {
        "titre": "Solidité des marqueurs de l'emploi dans la banque en 2025",
        "editeur": "Fédération professionnelle des banques", "nature": "officiel", "annee": 2026,
        "url": "https://www.fbf.fr/fr/communique_de_presse/solidite-des-marqueurs-de-lemploi-dans-la-banque-en-2025/",
        "lu": False, "reserve": "368 800 salariés en 2025 (-0,7 %) (extrait).",
    },
    "bce_ia_newsletter": {
        "titre": "L'impact de l'IA sur la banque : cas d'usage en notation de crédit et détection de fraude",
        "editeur": "Banque centrale européenne — supervision bancaire", "nature": "officiel", "annee": 2025,
        "url": "https://www.bankingsupervision.europa.eu/press/supervisory-newsletters/newsletter/2025/html/ssm.nl251120_1.en.html",
        "lu": False, "reserve": "« Plus de 85 % des banques supervisées utilisent l'IA » (extrait).",
    },
    "bce_priorites_2026": {
        "titre": "Priorités de supervision 2026-2028",
        "editeur": "Banque centrale européenne — supervision bancaire", "nature": "officiel", "annee": 2025,
        "url": "https://www.bankingsupervision.europa.eu/framework/priorities/html/ssm.supervisory_priorities202511.en.html",
        "lu": False, "reserve": "Suivi des stratégies, de la gouvernance et de la gestion des risques IA (extrait).",
    },
    "acpr_reflexion_ia": {
        "titre": "Document de réflexion — Intelligence artificielle : enjeux pour le secteur financier",
        "editeur": "Autorité de contrôle prudentiel et de résolution", "nature": "officiel", "annee": 2018,
        "url": "https://acpr.banque-france.fr/document-de-reflexion-intelligence-artificielle-enjeux-pour-le-secteur-financier",
        "lu": False, "reserve": "Explicabilité, équité, cybersécurité ; l'autorité a intégré les risques IA au "
                                 "questionnaire de supervision 2025 (extraits).",
    },
    "acpr_autorite_ia": {
        "titre": "Rapport annuel 2025 de l'autorité prudentielle : l'autorité désignée pour le règlement sur l'IA en banque et assurance",
        "editeur": "Cabinet d'avocats international — note d'analyse", "nature": "analyste", "annee": 2026,
        "url": "https://www.skadden.com/insights/publications/2026/07/acpr-publishes-its-2025-annual-report",
        "lu": False, "reserve": "L'autorité prudentielle française est désignée pour faire appliquer le règlement "
                                 "sur l'IA aux systèmes à haut risque de la banque et de l'assurance ; une enquête "
                                 "auprès de 9 banques et 35 assureurs a servi à mettre à jour sa méthode "
                                 "d'évaluation (extrait).",
    },
    "bdf_rapport_ia_2025": {
        "titre": "Rapport sur les impacts juridiques et réglementaires de l'IA dans le secteur financier",
        "editeur": "Banque centrale nationale", "nature": "officiel", "annee": 2025,
        "url": "https://www.banque-france.fr/fr/system/files/2025-07/Rapport_68_F_V3.pdf",
        "lu": False, "reserve": "Document PDF non ouvert ; cité sur son titre et sa date (juillet 2025).",
    },
    "eiopa_opinion": {
        "titre": "Avis sur la gouvernance et la gestion des risques de l'intelligence artificielle (EIOPA-BoS-25-360)",
        "editeur": "Autorité européenne des assurances et des pensions professionnelles", "nature": "officiel", "annee": 2025,
        "url": "https://www.eiopa.europa.eu/publications/opinion-artificial-intelligence-governance-and-risk-management_en",
        "lu": False, "reserve": "Avis du 6 août 2025 adressé aux superviseurs nationaux : pas de règle nouvelle, une "
                                 "lecture des textes assurantiels existants (Solvabilité II, distribution, DORA, RGPD) "
                                 "à la lumière du règlement sur l'IA, proportionnée au risque (extrait).",
    },
    # ── les textes ──
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
        "lu": False, "reserve": "Règlement du 8 juillet 2026, en vigueur le 27 juillet 2026. Les dates reportées "
                                 "sont reprises d'analyses de cabinets (extraits), pas du texte.",
    },
    "omnibus_analyse": {
        "titre": "Entrée en vigueur du règlement de simplification modifiant le règlement sur l'IA",
        "editeur": "Cabinet d'avocats international — alerte", "nature": "analyste", "annee": 2026,
        "url": "https://www.whitecase.com/insight-alert/eu-ai-omnibus-enters-force-amending-ai-act",
        "lu": False, "reserve": "Annexe III reportée au 2 décembre 2027, annexe I au 2 août 2028 ; article 50 "
                                 "maintenu au 2 août 2026 (extrait).",
    },
    "annexe3_infra": {
        "titre": "Annexe III — obligations, champ et échéance du 2 décembre 2027",
        "editeur": "Éditeur juridique spécialisé", "nature": "analyste", "annee": 2026,
        "url": "https://www.regulation-ai.eu/en/annex-iii/",
        "lu": False, "reserve": "Point 2 de l'annexe III : composants de sécurité dans la gestion et l'exploitation "
                                 "d'infrastructures numériques critiques, du trafic routier, de l'eau, du gaz, du "
                                 "chauffage et de l'électricité ; les composants à finalité exclusivement de "
                                 "cybersécurité ne sont pas des composants de sécurité (extraits).",
    },
    "dora": {
        "titre": "Règlement (UE) 2022/2554 sur la résilience opérationnelle numérique du secteur financier (DORA)",
        "editeur": "Union européenne", "nature": "juridique", "annee": 2022,
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R2554",
        "lu": False, "reserve": "Applicable depuis le 17 janvier 2025 ; adresse officielle obtenue par le service juridique.",
    },
    "dora_directive": {
        "titre": "Directive (UE) 2022/2556 modifiant les directives sectorielles pour la résilience opérationnelle numérique",
        "editeur": "Union européenne", "nature": "juridique", "annee": 2022,
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2556",
        "lu": False, "reserve": "Le volet directive de DORA, qui touche notamment Solvabilité II et les directives bancaires.",
    },
    "nis2": {
        "titre": "Directive (UE) 2022/2555 concernant des mesures destinées à assurer un niveau élevé commun de cybersécurité (NIS 2)",
        "editeur": "Union européenne", "nature": "juridique", "annee": 2022,
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2555",
        "lu": False, "reserve": "Transposition au 17 octobre 2024 (article 41), application au 18 octobre 2024 ; "
                                 "notification des incidents importants en 24 h / 72 h / un mois (article 23).",
    },
    "cer": {
        "titre": "Directive (UE) 2022/2557 sur la résilience des entités critiques (REC)",
        "editeur": "Union européenne", "nature": "juridique", "annee": 2022,
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2557",
        "lu": False, "reserve": "Le volet résilience physique, transposé en France dans le même texte que NIS 2 (extrait).",
    },
    "nis2_france": {
        "titre": "Transposition de NIS 2 en France : loi, calendrier 2026 et obligations",
        "editeur": "Éditeur juridique spécialisé", "nature": "analyste", "annee": 2026,
        "url": "https://www.legiscope.com/blog/transposition-nis2-france.html",
        "lu": False, "reserve": "Au 6 août 2026, la loi de transposition n'était pas promulguée ; procédure "
                                 "d'infraction ouverte fin novembre 2024 ; environ 15 000 entités visées ; "
                                 "référentiel de l'agence nationale publié le 17 mars 2026 (extraits). État à "
                                 "vérifier au jour de la lecture.",
    },
    "nis2_incidents": {
        "titre": "Notification des incidents NIS 2 : le cadre 24 h / 72 h / un mois",
        "editeur": "Éditeur juridique spécialisé", "nature": "analyste", "annee": 2026,
        "url": "https://www.legiscope.com/blog/nis2-incident-reporting.html",
        "lu": False, "reserve": "Alerte précoce sous 24 h, notification sous 72 h, rapport final sous un mois (extrait).",
    },
    "solvency2": {
        "titre": "Directive 2009/138/CE sur l'accès aux activités de l'assurance et de la réassurance (Solvabilité II)",
        "editeur": "Union européenne", "nature": "juridique", "annee": 2009,
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32009L0138",
        "lu": False, "reserve": "Adresse officielle obtenue par le service juridique.",
    },
    "solvency2_2027": {
        "titre": "Solvabilité II — texte consolidé applicable au 30 janvier 2027 (directive (UE) 2025/2)",
        "editeur": "Union européenne", "nature": "juridique", "annee": 2027,
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02009L0138-20270130",
        "lu": False, "reserve": "La directive modificative (UE) 2025/2 est entrée en vigueur le 28 janvier 2025 et "
                                 "s'applique à compter du 30 janvier 2027 (extraits d'éditeurs juridiques).",
    },
    "ai_act_politique": {
        "titre": "Le règlement sur l'IA — page de politique de la Commission européenne",
        "editeur": "Commission européenne", "nature": "officiel", "annee": 2026,
        "url": "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai",
        "lu": False, "reserve": "Page de référence ; les orientations de l'agence européenne de cybersécurité sur la "
                                 "documentation de l'article 17 n'avaient pas été publiées en mai 2026 (extrait).",
    },
    # ── les analyses et les repères de marché ──
    "migration_benchmarks": {
        "titre": "Stratégie de cœur bancaire : durées, coûts et dépassements documentés",
        "editeur": "Cabinet de conseil en stratégie", "nature": "analyste", "annee": 2025,
        "url": "https://www.mckinsey.com/industries/financial-services/our-insights/banking-matters/core-systems-strategy-for-banks",
        "lu": False, "reserve": "Grande banque : 3 à 5 ans, 200 M$ à 1 Md$ ; dépassements ≥ 50 % fréquents ; la "
                                 "moitié des transformations de cœur n'atteignent pas leurs objectifs (chiffre d'un "
                                 "cabinet d'études, via couverture secondaire).",
    },
    "indice_ia_2026": {
        "titre": "Indice annuel de l'IA 2026 — chapitre économie",
        "editeur": "Institut universitaire de recherche sur l'IA", "nature": "analyste", "annee": 2026,
        "url": "https://hai.stanford.edu/ai-index/2026-ai-index-report/economy",
        "lu": False, "reserve": "88 % des organisations utilisent l'IA, 70 % l'IA générative ; gains de productivité "
                                 "~14 % sur des tâches de service client, ~26 % en développement (couverture secondaire).",
    },
    "ratios_equipes": {
        "titre": "Structure d'une équipe d'ingénierie IA : rôles, rattachements et repères",
        "editeur": "Cabinet de recrutement spécialisé", "nature": "analyste", "annee": 2026,
        "url": "https://www.kore1.com/building-an-ml-engineering-team-structure-that-scales-roles-reporting-and-benchmarks/",
        "lu": False, "reserve": "1 ingénieur plateforme pour 4 à 6 constructeurs de modèles ; 1 data engineer pour "
                                 "2 à 3 ML/DS en amorçage. Ratio d'usage, pas une mesure sectorielle.",
    },
    "projets_hors_prod": {
        "titre": "Part des projets IA d'entreprise n'atteignant pas la production (2025)",
        "editeur": "Cabinet d'études (via couverture secondaire)", "nature": "analyste", "annee": 2025,
        "url": None,
        "lu": False, "reserve": "« Plus de 55 % » : chiffre rencontré dans plusieurs extraits, adresse primaire non obtenue.",
    },
    "infra_prix": {
        "titre": "Guide d'achat d'une infrastructure de calcul IA — composants et prix indicatifs",
        "editeur": "Revendeur d'infrastructure", "nature": "fournisseur", "annee": 2026,
        "url": "https://www.trgdatacenters.com/resource/nvidia-dgx-buyers-guide-everything-you-need-to-know/",
        "lu": False, "reserve": "Grappe de calcul clé en main : 7 à 60 M$ selon la taille ; nœud unitaire 0,4 à 0,5 M$ "
                                 "(prix revendeur, indicatifs, hors bâtiment, énergie et exploitation).",
    },
    "jetons_prix": {
        "titre": "Grille tarifaire publique d'un fournisseur européen de modèles",
        "editeur": "Fournisseur de modèles", "nature": "fournisseur", "annee": 2026,
        "url": "https://mistral.ai/pricing/",
        "lu": False, "reserve": "Modèle de premier rang : ~0,5 $/M jetons en entrée, ~1,5 $/M en sortie ; -50 % en "
                                 "lot, -90 % sur entrée en cache (extraits). Tarif de fournisseur, périmé sans date.",
    },
    "iea_energy_ai": {
        "titre": "Énergie et IA",
        "editeur": "Agence internationale de l'énergie", "nature": "officiel", "annee": 2025,
        "url": "https://www.iea.org/reports/energy-and-ai",
        "lu": False, "reserve": "~945 TWh de consommation des centres de données en 2030 ; énergie par tâche IA "
                                 "divisée par ≥ 10 par an ces dernières années (extraits).",
    },
    "operating_model": {
        "titre": "2026 : l'année de l'échelle ou de l'échec pour l'IA d'entreprise",
        "editeur": "Média spécialisé des directions informatiques", "nature": "presse", "annee": 2026,
        "url": "https://www.cio.com/article/4106578/2026-the-year-of-scale-or-fail-in-enterprise-ai.html",
        "lu": False, "reserve": "Modèle hub-and-spoke dominant ; le centre porte plateforme, normes, gouvernance (extrait).",
    },

    # ── LES AUTRES SECTEURS : leurs autorités, et un contre-exemple hors finance ──
    #
    # POURQUOI CES SOURCES SONT ENTRÉES. Les quatre cas comparables venaient
    # TOUS de la banque. « Pour situer, pas pour caler » n'a de sens que si le
    # lecteur peut se situer : un assureur, une société de gestion ou un
    # hôpital n'avait aucun repère ici, et lisait quatre banques en se
    # demandant ce qu'il devait en retenir. Chaque secteur du module a
    # désormais le repère de SON autorité, mesuré sur SON périmètre.
    "assur_autorite_numerisation": {
        "titre": "Rapport sur la numérisation du secteur européen de l'assurance — enquête de suivi de marché",
        "editeur": "Autorité européenne des assurances et des pensions professionnelles",
        "nature": "officiel", "annee": 2024,
        "url": "https://www.eiopa.europa.eu/publications/eiopas-report-digitalisation-european-insurance-sector_en",
        "lu": False, "reserve": "Rapport du 30 avril 2024, sur l'enquête 2023. Extrait de recherche ; "
                                "page non lue (accès refusé par le proxy).",
    },
    "assur_cas_plateforme": {
        "titre": "Communiqué : plateforme d'IA générative interne d'un assureur composite, déploiement et cas d'usage recensés",
        "editeur": "Assureur composite européen — espace presse", "nature": "presse", "annee": 2025,
        "url": "https://www.allianz.com/en/mediacenter/news/articles/250218-ai-at-allianz-the-impact-of-allianzgpt.html",
        "lu": False, "reserve": "Extrait de recherche, relayé par la presse spécialisée. Communication "
                                "d'entreprise : ni audit ni chiffre contradictoire.",
    },
    "marches_autorite_adoption": {
        "titre": "Analyse de risque — adoption de l'IA et tendances sur les marchés de valeurs mobilières",
        "editeur": "Autorité européenne des marchés financiers", "nature": "officiel", "annee": 2026,
        "url": "https://www.esma.europa.eu/sites/default/files/2026-02/ESMA50-481369926-30599_TRV_Risk_Analysis_AI_adoption_and_trends_in_securities_markets.pdf",
        "lu": False, "reserve": "Enquête de l'été 2025, publiée en février 2026. Extrait de recherche ; "
                                "document non ouvert (accès refusé par le proxy).",
    },
    "sante_etat_preparation_ue": {
        "titre": "L'intelligence artificielle remodèle les systèmes de santé : état de préparation dans l'Union européenne",
        "editeur": "Bureau régional européen de l'organisation sanitaire mondiale",
        "nature": "officiel", "annee": 2026,
        "url": "https://www.who.int/europe/publications/i/item/WHO-EURO-2026-12707-52481-81471",
        "lu": False, "reserve": "Données collectées de juin 2024 à mars 2025 ; 27 États membres sur 27 "
                                "ont répondu. Extrait de recherche ; page non lue.",
    },
    "public_sanction_profilage": {
        "titre": "Sanction d'une administration fiscale pour traitement illicite et discriminatoire de la nationalité",
        "editeur": "Autorité nationale de protection des données", "nature": "officiel", "annee": 2021,
        "url": "https://www.autoriteitpersoonsgegevens.nl/en/current/tax-administration-fined-for-discriminatory-and-unlawful-data-processing",
        "lu": False, "reserve": "Décision du 7 décembre 2021. Extrait de recherche ; page non lue.",
    },
    "public_methodes_illicites": {
        "titre": "Constat d'illicéité et de discrimination dans les méthodes d'une administration fiscale",
        "editeur": "Autorité nationale de protection des données", "nature": "officiel", "annee": 2020,
        "url": "https://www.autoriteitpersoonsgegevens.nl/en/current/methods-used-by-dutch-tax-administration-unlawful-and-discriminatory",
        "lu": False, "reserve": "Enquête publiée en juillet 2020, antérieure à la sanction. Extrait de "
                                "recherche ; page non lue. Le nombre de familles touchées vient de la "
                                "couverture publique de l'affaire, pas de cette décision.",
    },
    "eurostat_ia_entreprises": {
        "titre": "Usage de l'intelligence artificielle dans les entreprises — par activité économique",
        "editeur": "Office statistique de l'Union européenne", "nature": "officiel", "annee": 2025,
        "url": "https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Use_of_artificial_intelligence_in_enterprises",
        "lu": False, "reserve": "Enquête sur l'usage des TIC, entreprises de 10 salariés et plus. Extrait "
                                "de recherche ; page non lue (accès refusé par le proxy).",
    },
}

def couverture_sources():
    """Ce qu'un lecteur peut rouvrir, et ce que l'auteur a lu : deux comptes.
    Ici la seconde réponse est NON pour toutes — et l'écrire vaut mieux que le
    laisser croire."""
    n = len(SOURCES)
    avec = sum(1 for s in SOURCES.values() if s.get("url"))
    lues = sum(1 for s in SOURCES.values() if s.get("lu"))
    par_nature = {}
    for s in SOURCES.values():
        par_nature[s["nature"]] = par_nature.get(s["nature"], 0) + 1
    return {"total": n, "avec_adresse": avec, "lues": lues,
            "part_avec_adresse": round(avec / n, 3) if n else 0.0,
            "par_nature": dict(sorted(par_nature.items())),
            "limite": "Aucune page n'a été ouverte depuis ce poste : les chiffres sont ceux des "
                      "extraits de recherche. Un lecteur doit rouvrir la source avant de s'en "
                      "prévaloir. Les éditeurs sont désignés par leur nature ; les adresses, "
                      "elles, nomment nécessairement les sites."}


# ═══════════════════════════════════════════════════════════════════════════
#  2. LES ANCRAGES — des ordres de grandeur pour SITUER, jamais pour estimer
# ═══════════════════════════════════════════════════════════════════════════

ANCRAGES = [
    {"cle": "casA_budget", "nom": "Cas A — enveloppe du programme de plateforme commune",
     "min": 750, "max": 900, "unite": "M€", "source": "casA_programme_presse",
     "ne_dit_pas": "Ni la part de l'IA dans l'enveloppe, ni la répartition build/run, ni ce qui "
                   "relève de la migration des deux SI plutôt que de la plateforme."},
    {"cle": "casA_horizon", "nom": "Cas A — horizon annoncé du programme",
     "min": 4, "max": 4, "unite": "ans", "source": "casA_programme_presse",
     "ne_dit_pas": "Un horizon annoncé au lancement ; les repères de migration de cœur documentent "
                   "des dépassements de 50 % et plus."},
    {"cle": "casA_effectif", "nom": "Cas A — effectif du groupe",
     "min": 100000, "max": 100000, "unite": "salariés", "source": "casA_ia_cp",
     "ne_dit_pas": "Ordre de grandeur (« quelque 100 000 »)."},
    {"cle": "casA_usage_quotidien", "nom": "Cas A — part des salariés utilisant l'IA générative au quotidien",
     "min": 0.5, "max": 0.5, "unite": "part", "source": "casA_ia_cp",
     "ne_dit_pas": "« Au quotidien » n'est pas défini ; l'usage moyen relevé est de 40 sollicitations "
                   "par mois et par utilisateur (extrait)."},
    {"cle": "casA_conseillers", "nom": "Cas A — part des conseillers utilisateurs",
     "min": 0.75, "max": 0.75, "unite": "part", "source": "casA_programme_presse",
     "ne_dit_pas": "Chiffre du cas fourni, non retrouvé dans un extrait officiel."},
    {"cle": "casA_appels", "nom": "Cas A — appels traités de bout en bout par un agent vocal",
     "min": 1000000, "max": 1000000, "unite": "appels/an", "source": "casA_ia_cp",
     "ne_dit_pas": "Sur 12 millions d'appels reçus (cas fourni) ; ni le taux de résolution ni la "
                   "satisfaction ne sont publiés."},
    {"cle": "casA_formes", "nom": "Cas A — collaborateurs formés à l'IA",
     "min": 45000, "max": 45000, "unite": "salariés", "source": "casA_accord_social",
     "ne_dit_pas": "Ni la durée ni le contenu de la formation."},
    {"cle": "casB_plan", "nom": "Cas B — plan IA triennal 2026-2028",
     "min": 500, "max": 500, "unite": "M€", "source": "casB_plan_cp",
     "ne_dit_pas": "« Près de 500 M€ » ; périmètre groupe (banque, assurance, gestion d'actifs)."},
    {"cle": "casB_entite_ia", "nom": "Cas B — entité IA mutualisée (socle)",
     "min": 150, "max": 150, "unite": "M€", "source": "casB_plan_cp",
     "ne_dit_pas": "Effectif visé ~150 personnes ; le chiffre couvre-t-il l'infrastructure ? Non dit."},
    {"cle": "casB_entite_ia_etp", "nom": "Cas B — effectif de l'entité IA",
     "min": 150, "max": 150, "unite": "ETP", "source": "casB_plan_cp",
     "ne_dit_pas": "Cible à un an ; la ventilation par rôle n'est pas publiée."},
    {"cle": "casC_valeur", "nom": "Cas C — objectif de valeur annuelle créée par l'IA et la donnée",
     "min": 500, "max": 500, "unite": "M€/an", "source": "casC_presse",
     "ne_dit_pas": "« Valeur » n'est pas « économie » : la méthode de mesure n'est pas publiée."},
    {"cle": "casC_cas", "nom": "Cas C — cas d'usage IA en production",
     "min": 1000, "max": 1000, "unite": "cas d'usage", "source": "casC_presse",
     "ne_dit_pas": "750 à l'automne 2023 ; la taille d'un « cas d'usage » n'est pas définie."},
    {"cle": "fbf_effectif", "nom": "Secteur bancaire français — effectif 2025",
     "min": 368800, "max": 368800, "unite": "salariés", "source": "fbf_emploi_2025",
     "ne_dit_pas": "CDI + CDD + alternants ; -0,7 % sur un an."},
    {"cle": "bce_usage", "nom": "Banques supervisées par la BCE utilisant l'IA",
     "min": 0.85, "max": 1.0, "unite": "part", "source": "bce_ia_newsletter",
     "ne_dit_pas": "« Utiliser l'IA » couvre un pilote comme une production à l'échelle."},
    {"cle": "acpr_enquete", "nom": "Établissements interrogés par l'autorité prudentielle pour sa méthode d'évaluation des systèmes d'IA",
     "min": 44, "max": 44, "unite": "établissements", "source": "acpr_autorite_ia",
     "ne_dit_pas": "9 banques et 35 assureurs ; les résultats de l'enquête ne sont pas dans l'extrait."},
    {"cle": "casD_cout", "nom": "Cas D — coût de la migration manquée (2018)",
     "min": 330, "max": 400, "unite": "M£", "source": "casD_revue",
     "ne_dit_pas": "330 M£ de coûts de remédiation ; > 400 M£ avec les amendes de 2022."},
    {"cle": "casD_duree", "nom": "Cas D — jours avant retour à la normale",
     "min": 232, "max": 232, "unite": "jours", "source": "casD_revue",
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
     "ne_dit_pas": "Chiffre d'un cabinet d'études rapporté par un tiers ; définition de l'échec non précisée."},
    {"cle": "ia_hors_prod", "nom": "Projets IA d'entreprise n'atteignant pas la production",
     "min": 0.55, "max": 0.55, "unite": "part", "source": "projets_hors_prod",
     "ne_dit_pas": "Adresse primaire non obtenue : à confirmer avant de s'en prévaloir."},
    {"cle": "ratio_plateforme", "nom": "Ingénieurs plateforme par constructeur de modèles",
     "min": 1 / 6, "max": 1 / 4, "unite": "ETP/ETP", "source": "ratios_equipes",
     "ne_dit_pas": "Ratio d'usage d'un cabinet de recrutement, pas une mesure sectorielle."},
    {"cle": "ratio_data", "nom": "Data engineers par ML/DS (amorçage)",
     "min": 1 / 3, "max": 1 / 2, "unite": "ETP/ETP", "source": "ratios_equipes",
     "ne_dit_pas": "Passe à 1:1 – 1:2 en croissance selon la complexité des données."},
    {"cle": "adoption_orgs", "nom": "Organisations utilisant l'IA dans au moins une fonction",
     "min": 0.88, "max": 0.88, "unite": "part", "source": "indice_ia_2026",
     "ne_dit_pas": "Enquête déclarative mondiale ; 70 % pour l'IA générative."},
    {"cle": "gain_service_client", "nom": "Gain de productivité mesuré — tâches de service client",
     "min": 0.14, "max": 0.14, "unite": "part", "source": "indice_ia_2026",
     "ne_dit_pas": "Couverture secondaire ; études sur des tâches, pas sur des postes."},
    {"cle": "gain_dev", "nom": "Gain de productivité mesuré — développement logiciel",
     "min": 0.26, "max": 0.26, "unite": "part", "source": "indice_ia_2026",
     "ne_dit_pas": "Gain sur tâches instrumentées, non transposable à un service entier."},
    {"cle": "grappe_calcul", "nom": "Grappe de calcul IA clé en main — prix indicatif",
     "min": 7, "max": 60, "unite": "M$", "source": "infra_prix",
     "ne_dit_pas": "Selon la taille ; hors bâtiment, énergie, refroidissement et exploitation."},
    {"cle": "noeud_calcul", "nom": "Nœud de calcul IA — prix indicatif unitaire",
     "min": 0.4, "max": 0.5, "unite": "M$", "source": "infra_prix",
     "ne_dit_pas": "Prix revendeur ; les générations se succèdent en moins d'un an."},
    {"cle": "jetons", "nom": "Modèle de premier rang — prix par million de jetons (entrée / sortie)",
     "min": 0.5, "max": 1.5, "unite": "$/M jetons", "source": "jetons_prix",
     "ne_dit_pas": "Tarif public au jour de la recherche ; -50 % en lot, -90 % sur entrée en cache."},
    {"cle": "energie_par_tache", "nom": "Énergie par tâche IA — rythme d'amélioration",
     "min": 10, "max": 10, "unite": "× par an", "source": "iea_energy_ai",
     "ne_dit_pas": "« Au moins un ordre de grandeur par an ces dernières années » ; pas une garantie."},

    # ── ASSURANCE ──
    {"cle": "assur_non_vie", "nom": "Assureurs non-vie utilisant déjà l'IA dans la chaîne de valeur",
     "min": 0.5, "max": 0.5, "unite": "part", "source": "assur_autorite_numerisation",
     "ne_dit_pas": "« Environ la moitié » : l'extrait ne donne ni l'effectif interrogé ni la "
                   "définition d'« utiliser ». Enquête 2023, publiée en 2024."},
    {"cle": "assur_vie", "nom": "Assureurs vie utilisant déjà l'IA dans la chaîne de valeur",
     "min": 0.24, "max": 0.25, "unite": "part", "source": "assur_autorite_numerisation",
     "ne_dit_pas": "Deux formulations circulent — « 24 % » et « un quart » : la borne les couvre "
                   "toutes deux plutôt que de trancher sur un extrait."},
    {"cle": "assur_cas_utilisateurs", "nom": "Cas E — salariés utilisant la plateforme d'IA générative interne",
     "min": 60000, "max": 60000, "unite": "salariés", "source": "assur_cas_plateforme",
     "ne_dit_pas": "« Plus de 60 000 » début 2025 ; la fréquence d'usage n'est pas publiée."},
    {"cle": "assur_cas_effectif", "nom": "Cas E — effectif du groupe",
     "min": 158000, "max": 158000, "unite": "salariés", "source": "assur_cas_plateforme",
     "ne_dit_pas": "Cible de déploiement annoncée ; l'effectif est celui du groupe, pas du périmètre outillé."},
    {"cle": "assur_cas_usages", "nom": "Cas E — cas d'usage IA recensés dans le groupe",
     "min": 900, "max": 900, "unite": "cas d'usage", "source": "assur_cas_plateforme",
     "ne_dit_pas": "« Recensés » n'est pas « en production » : la part réellement servie n'est pas "
                   "publiée, et la taille d'un cas d'usage n'est pas définie."},

    # ── MARCHÉS, GESTION D'ACTIFS ──
    {"cle": "marches_en_prod", "nom": "Acteurs de marché déclarant l'IA en production ou en développement",
     "min": 0.28, "max": 0.28, "unite": "part", "source": "marches_autorite_adoption",
     "ne_dit_pas": "Enquête déclarative de l'été 2025 ; « en production OU en développement » "
                   "réunit deux états très différents."},
    {"cle": "marches_experimentent", "nom": "Acteurs de marché expérimentant ou prévoyant de le faire sous douze mois",
     "min": 0.22, "max": 0.22, "unite": "part", "source": "marches_autorite_adoption",
     "ne_dit_pas": "Une intention déclarée n'est pas un déploiement."},
    {"cle": "marches_sans_investissement", "nom": "Acteurs de marché n'ayant fait aucun investissement IA en 2024",
     "min": 0.36, "max": 0.36, "unite": "part", "source": "marches_autorite_adoption",
     "ne_dit_pas": "LE CHIFFRE QUI MANQUE PARTOUT AILLEURS : plus d'un tiers n'a rien engagé. "
                   "L'extrait ne dit pas si ces acteurs sont les plus petits."},

    # ── SANTÉ, ENTITÉ ESSENTIELLE ──
    {"cle": "sante_diagnostic", "nom": "États membres de l'UE employant l'IA en aide au diagnostic",
     "min": 0.75, "max": 0.75, "unite": "part", "source": "sante_etat_preparation_ue",
     "ne_dit_pas": "« Le pays emploie » ne dit ni combien d'établissements, ni à quelle échelle. "
                   "Données de juin 2024 à mars 2025."},
    {"cle": "sante_agents", "nom": "États membres employant des agents conversationnels avec les patients",
     "min": 0.63, "max": 0.63, "unite": "part", "source": "sante_etat_preparation_ue",
     "ne_dit_pas": "Usage relevant de l'obligation d'information de l'article 50 : le texte du "
                   "rapport n'en traite pas."},
    {"cle": "sante_postes_dedies", "nom": "États membres ayant créé des postes dédiés IA et données en santé",
     "min": 0.5, "max": 0.5, "unite": "part", "source": "sante_etat_preparation_ue",
     "ne_dit_pas": "« Près de la moitié » ; ni le nombre de postes ni leur rattachement."},
    {"cle": "sante_reponses", "nom": "Taux de réponse de l'enquête sur les vingt-sept États membres",
     "min": 1.0, "max": 1.0, "unite": "part", "source": "sante_etat_preparation_ue",
     "ne_dit_pas": "Un taux de réponse complet ne dit rien de la comparabilité des déclarations."},

    # ── ADMINISTRATION PUBLIQUE — LE CONTRE-EXEMPLE ALGORITHMIQUE ──
    {"cle": "public_amende", "nom": "Cas G — sanction pour traitement illicite et discriminatoire de la nationalité",
     "min": 2.75, "max": 2.75, "unite": "M€", "source": "public_sanction_profilage",
     "ne_dit_pas": "Décision du 7 décembre 2021. L'amende est sans commune mesure avec le coût "
                   "de la réparation aux familles, qui n'est pas dans cette décision."},
    {"cle": "public_familles", "nom": "Cas G — familles accusées à tort de fraude",
     "min": 26000, "max": 35000, "unite": "familles", "source": "public_methodes_illicites",
     "ne_dit_pas": "Les deux bornes circulent (26 000 accusées, 35 000 dont les droits fondamentaux "
                   "ont été atteints) ; elles ne recouvrent pas le même ensemble. Chiffres de la "
                   "couverture publique, pas de la décision."},
    {"cle": "public_double_nationalite", "nom": "Cas G — personnes encore enregistrées comme binationales en mai 2018",
     "min": 1400000, "max": 1400000, "unite": "personnes", "source": "public_sanction_profilage",
     "ne_dit_pas": "La donnée aurait dû être effacée depuis janvier 2014 : quatre ans de conservation "
                   "indue d'un attribut servant d'indicateur de risque."},

    # ── TOUS SECTEURS — L'ÉCART ENTRE ACTIVITÉS, QUI EST LE VRAI REPÈRE ──
    {"cle": "ue_entreprises_2025", "nom": "Entreprises de l'UE (10 salariés et plus) utilisant l'IA",
     "min": 0.2, "max": 0.2, "unite": "part", "source": "eurostat_ia_entreprises",
     "ne_dit_pas": "20,0 % en 2025 contre 13,5 % en 2024. « Utiliser » couvre un outil acheté "
                   "comme un modèle entraîné."},
    {"cle": "ue_secteur_haut", "nom": "Activité la plus équipée — information et communication",
     "min": 0.6252, "max": 0.6252, "unite": "part", "source": "eurostat_ia_entreprises",
     "ne_dit_pas": "Le secteur qui VEND l'outillage est aussi celui qui l'emploie : ce n'est pas "
                   "un repère transposable."},
    {"cle": "ue_secteur_bas", "nom": "Activité la moins équipée — construction",
     "min": 0.1079, "max": 0.1079, "unite": "part", "source": "eurostat_ia_entreprises",
     "ne_dit_pas": "Un rapport de près de six entre le haut et le bas de l'échelle : c'est cet "
                   "écart, et non la moyenne, qui situe une organisation."},
]


# ═══════════════════════════════════════════════════════════════════════════
#  3. LES QUANTITÉS ET LES PRIX — et où un client les trouve réellement
# ═══════════════════════════════════════════════════════════════════════════

QUANTITES = {
    "effectif": {"nom": "Effectif concerné", "unite": "salariés",
                 "ou": "Bilan social ou base de données économiques et sociales ; périmètre des entités qui "
                       "auront accès à l'usine."},
    "n_metiers": {"nom": "Lignes métier à accompagner", "unite": "métiers",
                  "ou": "Organigramme de premier niveau : distribution, crédit ou souscription, sinistres, "
                        "conformité, risques, RH, IT, relation client, exploitation."},
    "n_cas_usage": {"nom": "Cas d'usage visés en production à l'horizon", "unite": "cas",
                    "ou": "Portefeuille arbitré par le comité IA ; à défaut, la liste des pilotes déjà menés. "
                          "Un cas d'usage non nommé n'est pas un cas d'usage."},
    "n_cas_haut_risque": {"nom": "Dont cas relevant de l'annexe III du règlement (UE) 2024/1689",
                          "unite": "cas",
                          "ou": "Évaluation de solvabilité, notation de crédit, tarification vie et santé, "
                                "recrutement, composants de sécurité d'infrastructures critiques : la "
                                "qualification est juridique, elle se fait dossier par dossier."},
    "etp_par_cas": {"nom": "Constructeurs de modèles par cas d'usage (ETP)", "unite": "ETP/cas",
                    "ou": "Vos pilotes déjà menés : personnes réellement mobilisées sur un cas jusqu'à la "
                          "production, pas l'effectif nominal de l'équipe."},
    "n_si_source": {"nom": "Systèmes d'information à unifier", "unite": "SI",
                    "choix": [(1, "Un seul socle, stable"),
                              (2, "Deux systèmes (migration de cœur en cours)"),
                              (3, "Trois ou plus")],
                    "ou": "Cartographie applicative ; 1 si l'usine se pose sur un socle stable, 2 ou plus "
                          "si elle accompagne une migration de cœur."},
    "n_interfaces": {"nom": "Interfaces à porter vers le socle IA", "unite": "interfaces",
                     "ou": "Cartographie des flux ; compter celles qui devront exister DEUX fois pendant "
                           "une migration."},
    "volume_appels": {"nom": "Appels entrants par an", "unite": "appels/an",
                      "ou": "Statistiques du centre de relation client."},
    "part_appels_ia": {"nom": "Part visée d'appels traités de bout en bout par l'IA", "unite": "part",
                       "choix": [(0.05, "Un vingtième"), (0.1, "Un dixième"),
                                 (0.25, "Un quart"), (0.5, "La moitié")],
                       "ou": "Objectif du comité ; le cas A publie 1 million sur 12 (ancrage, pas cible)."},
    "part_formes": {"nom": "Part des salariés à former", "unite": "part",
                    "choix": [(0.25, "Un quart"), (0.5, "La moitié"),
                              (0.75, "Trois quarts"), (1, "Tous")],
                    "ou": "Accord social ou plan de développement des compétences ; cas A : ~45 000 sur "
                          "~100 000 (ancrage)."},
    "heures_formation": {"nom": "Heures de formation par salarié formé", "unite": "h",
                         "ou": "Catalogue de formation ; distinguer socle commun et parcours métier."},
    "duree_mois": {"nom": "Horizon de l'étude", "unite": "mois",
                   "choix": [(12, "Un an"), (24, "Deux ans"), (36, "Trois ans"),
                             (48, "Quatre ans"), (60, "Cinq ans")],
                   "ou": "Plan stratégique ; le cas A annonce quatre ans (ancrage)."},
    "tokens_mois": {"nom": "Volume d'inférence prévu", "unite": "M jetons/mois",
                    "ou": "Relevés des pilotes (console du fournisseur) ; non instruit s'il n'y en a pas."},
    "jours_cadrage": {"nom": "Jours de cadrage et de gouvernance", "unite": "jours",
                      "ou": "Votre lettre de mission ou devis de conseil ; le module n'en invente pas."},
    "jours_pmo_mois": {"nom": "Jours de pilotage par mois", "unite": "jours/mois",
                       "ou": "Dispositif retenu (pilotage principal + contre-pilotage)."},
    "jours_par_cas": {"nom": "Jours de développement par cas d'usage", "unite": "jours/cas",
                      "ou": "Vos pilotes : jours réellement consommés jusqu'à la production."},
    "jours_recette_interface": {"nom": "Jours de recette par interface", "unite": "jours/interface",
                                "ou": "Retours de la dernière migration ; le cas D documente ce que coûte "
                                      "une recette insuffisante."},
}

# Les quantités que seul un secteur demande. Elles portent leur secteur ; le
# formulaire ne montre que celles du secteur choisi.
QUANTITES_SECTEUR = {
    "n_fournisseurs_ia": {"secteurs": ("banque", "assurance", "marches"), "unite": "fournisseurs",
                          "nom": "Fournisseurs de modèles et de plateformes IA (prestataires TIC)",
                          "ou": "Registre d'information DORA ; un fournisseur de modèle accessible par interface "
                                "est un prestataire de services TIC."},
    "jours_registre_fournisseur": {"secteurs": ("banque", "assurance", "marches"), "unite": "jours/fournisseur",
                                   "nom": "Jours d'instruction du registre par fournisseur",
                                   "ou": "Votre fonction conformité : contrat, sous-traitance, localisation, sortie."},
    "jours_test_resilience_cas": {"secteurs": ("banque", "assurance", "marches"), "unite": "jours/cas",
                                  "nom": "Jours de tests de résilience par cas d'usage en production",
                                  "ou": "Programme de tests DORA ; un système d'IA en production entre dans le périmètre testé."},
    "n_modeles_tarifaires": {"secteurs": ("assurance",), "unite": "modèles",
                             "nom": "Modèles de tarification ou de provisionnement touchés",
                             "ou": "Fonction actuarielle : inventaire des modèles ; un modèle assisté par IA reste un modèle."},
    "jours_validation_modele": {"secteurs": ("assurance",), "unite": "jours/modèle",
                                "nom": "Jours de validation indépendante par modèle",
                                "ou": "Politique de validation des modèles ; second regard actuariel."},
    "jours_orsa_ia": {"secteurs": ("assurance",), "unite": "jours",
                      "nom": "Jours d'intégration des systèmes d'IA à l'évaluation interne des risques",
                      "ou": "Fonction gestion des risques : l'évaluation interne (ORSA) doit couvrir les risques "
                            "des systèmes d'IA, selon l'avis de l'autorité européenne de 2025."},
    "n_cas_composant_securite": {"secteurs": ("nis2",), "unite": "cas",
                                 "nom": "Dont cas qualifiés « composant de sécurité » d'une infrastructure critique",
                                 "ou": "Annexe III, point 2 : un système dont la défaillance menace directement "
                                       "l'intégrité physique ou la sécurité des personnes ; la cybersécurité seule "
                                       "n'en fait pas un."},
    "jours_safety_case": {"secteurs": ("nis2",), "unite": "jours/cas",
                          "nom": "Jours de dossier de sûreté par composant de sécurité",
                          "ou": "Votre ingénierie sûreté de fonctionnement : analyse de risques, exigences, preuves."},
    "jours_procedure_incidents": {"secteurs": ("nis2",), "unite": "jours",
                                  "nom": "Jours d'intégration des incidents IA à la chaîne de notification 24 h / 72 h / un mois",
                                  "ou": "Votre procédure de gestion d'incidents ; un incident d'un système d'IA "
                                        "qui touche un service essentiel est un incident important."},
    "n_zones_ot": {"secteurs": ("nis2",), "unite": "zones",
                   "nom": "Zones OT avec lesquelles le socle IA échange",
                   "ou": "Modèle de zones et conduits IEC 62443 ; compter les conduits, pas les équipements."},
    "jours_segmentation_zone": {"secteurs": ("nis2",), "unite": "jours/zone",
                                "nom": "Jours de conception et de recette d'un conduit vers une zone OT",
                                "ou": "Architecture cible OT : DMZ industrielle, bastion, diode ; retours du dernier projet."},
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
                      "ou": "Devis fournisseur ; les prix publics d'une grappe clé en main (7 à 60 M$) situent, "
                            "ils ne chiffrent pas."},
    "cout_outillage_an": {"nom": "Outillage MLOps / LLMOps et licences", "unite": "€/an",
                          "ou": "Devis éditeurs ; licences par utilisateur incluses ici."},
    "cout_securite_an": {"nom": "Sécurité et supervision du socle", "unite": "€/an",
                         "ou": "RSSI : centre de supervision, tests d'intrusion, revue de code modèle."},
    "prix_M_jetons": {"nom": "Prix par million de jetons (moyenne entrée/sortie)", "unite": "€/M jetons",
                      "ou": "Tarif contractuel ; les grilles publiques (0,5 / 1,5 $) situent."},
    "cout_heure_formation": {"nom": "Coût d'une heure de formation par salarié", "unite": "€/h",
                             "ou": "Service formation : coût complet, temps salarié inclus."},
    "cout_interface": {"nom": "Coût de portage d'une interface", "unite": "€/interface",
                       "ou": "Bordereau de votre intégrateur ; retours de la dernière migration."},
    "cout_audit_cas": {"nom": "Coût d'un dossier de conformité annexe III", "unite": "€/cas",
                       "ou": "Devis de l'organisme ou du cabinet ; inclut la documentation technique et "
                             "l'évaluation de conformité."},
}



# ═══════════════════════════════════════════════════════════════════════════
#  3 bis. LES EXEMPLES — pour partir d'un ordre de grandeur, jamais pour s'en
#         contenter
# ═══════════════════════════════════════════════════════════════════════════
#
# CE QU'UN FORMULAIRE VIDE DEMANDE VRAIMENT. Vingt-cinq cases à remplir, sans
# aucun repère, posent au client une question qu'il ne peut pas trancher : « ce
# que j'écris est-il vraisemblable ? » Il renonce, ou il écrit n'importe quoi —
# et un chiffrage bâti sur n'importe quoi a l'air d'un chiffrage.
#
# ET CE QU'ILS NE DOIVENT SURTOUT PAS DEVENIR. Ce module publie qu'il NE PORTE
# AUCUN PRIX : il chiffre les vôtres. Un exemple qu'on laisserait en place se
# retrouverait dans une étude exportée, présenté comme le chiffre du client.
# Trois garde-fous, et le troisième est le seul qui compte vraiment :
#
#   1. rien n'est pré-sélectionné — la liste s'ouvre sur « non renseigné » ;
#   2. chaque exemple dit D'OÙ IL VIENT, et ce qu'il vaut :
#        · « ancrage »  — traçable à une source du module, vérifiable ;
#        · « cabinet »  — ordre de grandeur d'usage, AUCUNE source publique,
#                         à remplacer impérativement ;
#        · « scénario » — une hypothèse de taille, qui n'affirme rien du monde ;
#   3. LE CHIFFRAGE COMPTE CE QUI EST RESTÉ UN EXEMPLE. `valeurs_dexemple()`
#      rapproche ce que le client a saisi des exemples offerts : une valeur
#      identique à un exemple est signalée AVANT les totaux. Sans ce troisième
#      point, les deux premiers ne seraient que des précautions d'affichage.
#
# UN EXEMPLE « ancrage » DOIT DÉSIGNER UN ANCRAGE QUI EXISTE : sinon il se
# réclame d'une source qu'on ne peut pas rouvrir, c'est-à-dire d'une intention.
# `_verifier_exemples()` refuse au chargement.

PROVENANCES = {
    "ancrage": "Traçable à une source du module — rouvrez-la avant de vous en prévaloir.",
    "cabinet": "Ordre de grandeur d'usage du cabinet, AUCUNE source publique. "
               "À remplacer par votre devis ou votre grille.",
    "scenario": "Hypothèse de taille, pour situer l'ordre de grandeur. "
                "N'affirme rien sur le monde.",
}

EXEMPLES = {
    # ── les quantités : des scénarios de taille, et ce que les cas publient ──
    "effectif": [
        {"valeur": 800, "libelle": "Entreprise de taille intermédiaire", "provenance": "scenario"},
        {"valeur": 5000, "libelle": "Grande entreprise, un seul réseau", "provenance": "scenario"},
        {"valeur": 100000, "libelle": "Groupe multi-réseaux — effectif du cas A",
         "provenance": "ancrage", "ancrage": "casA_effectif"},
    ],
    "n_metiers": [
        {"valeur": 4, "libelle": "Périmètre restreint (distribution, risques, IT, conformité)",
         "provenance": "scenario"},
        {"valeur": 9, "libelle": "Organigramme complet de premier niveau", "provenance": "scenario"},
    ],
    "n_cas_usage": [
        {"valeur": 5, "libelle": "Premier portefeuille arbitré", "provenance": "scenario"},
        {"valeur": 30, "libelle": "Usine installée, plusieurs métiers servis", "provenance": "scenario"},
        {"valeur": 1000, "libelle": "Compte annoncé par le cas C — à citer, pas à viser",
         "provenance": "ancrage", "ancrage": "casC_cas"},
    ],
    "n_cas_haut_risque": [
        {"valeur": 0, "libelle": "Aucun cas d'annexe III identifié à ce stade", "provenance": "scenario"},
        {"valeur": 2, "libelle": "Deux cas qualifiés (par exemple solvabilité et recrutement)",
         "provenance": "scenario"},
    ],
    "etp_par_cas": [
        {"valeur": 0.5, "libelle": "Un cas simple, mi-temps jusqu'en production", "provenance": "cabinet"},
        {"valeur": 1.5, "libelle": "Un cas courant, une personne et demie", "provenance": "cabinet"},
        {"valeur": 3, "libelle": "Un cas lourd (données à reprendre, intégration métier)",
         "provenance": "cabinet"},
    ],
    "n_interfaces": [
        {"valeur": 15, "libelle": "Socle stable, quelques flux à porter", "provenance": "scenario"},
        {"valeur": 120, "libelle": "Migration en cours : les flux existent DEUX fois", "provenance": "scenario"},
    ],
    "volume_appels": [
        {"valeur": 500000, "libelle": "Centre de relation client de taille moyenne", "provenance": "scenario"},
        {"valeur": 12000000, "libelle": "Volume du cas A (12 millions reçus)",
         "provenance": "ancrage", "ancrage": "casA_appels"},
    ],
    "heures_formation": [
        {"valeur": 2, "libelle": "Sensibilisation de socle", "provenance": "scenario"},
        {"valeur": 7, "libelle": "Une journée par salarié formé", "provenance": "scenario"},
        {"valeur": 21, "libelle": "Parcours métier (trois jours)", "provenance": "scenario"},
    ],
    "duree_mois": [
        {"valeur": 12, "libelle": "Un exercice", "provenance": "scenario"},
        {"valeur": 36, "libelle": "Plan triennal — horizon du cas B",
         "provenance": "ancrage", "ancrage": "casB_plan"},
        {"valeur": 48, "libelle": "Horizon annoncé du programme du cas A",
         "provenance": "ancrage", "ancrage": "casA_horizon"},
    ],

    "tokens_mois": [
        {"valeur": 20, "libelle": "Assistant de rédaction pour quelques centaines d'utilisateurs",
         "provenance": "cabinet"},
        {"valeur": 400, "libelle": "Assistant généralisé et traitements par lots", "provenance": "cabinet"},
    ],
    "jours_cadrage": [
        {"valeur": 40, "libelle": "Cadrage court, périmètre déjà arbitré", "provenance": "cabinet"},
        {"valeur": 120, "libelle": "Cadrage complet avec gouvernance à installer", "provenance": "cabinet"},
    ],
    "jours_pmo_mois": [
        {"valeur": 5, "libelle": "Pilotage léger, un quart de temps", "provenance": "cabinet"},
        {"valeur": 20, "libelle": "Pilotage dédié, un temps plein", "provenance": "cabinet"},
    ],
    "jours_par_cas": [
        {"valeur": 60, "libelle": "Cas simple, données disponibles", "provenance": "cabinet"},
        {"valeur": 200, "libelle": "Cas lourd, intégration métier et reprise de données",
         "provenance": "cabinet"},
    ],
    "jours_recette_interface": [
        {"valeur": 5, "libelle": "Interface simple, contrat stable", "provenance": "cabinet"},
        {"valeur": 20, "libelle": "Interface métier, recette croisée pendant une migration",
         "provenance": "cabinet"},
    ],

    # ── les quantités propres à un secteur : elles n'apparaissent que s'il est choisi ──
    "n_fournisseurs_ia": [
        {"valeur": 3, "libelle": "Socle resserré, un fournisseur principal", "provenance": "scenario"},
        {"valeur": 12, "libelle": "Plusieurs modèles et plateformes en parallèle", "provenance": "scenario"},
    ],
    "jours_registre_fournisseur": [
        {"valeur": 3, "libelle": "Fournisseur déjà au registre, mise à jour", "provenance": "cabinet"},
        {"valeur": 10, "libelle": "Entrée complète, fonction critique", "provenance": "cabinet"},
    ],
    "jours_test_resilience_cas": [
        {"valeur": 5, "libelle": "Test intégré à la campagne existante", "provenance": "cabinet"},
        {"valeur": 20, "libelle": "Scénario dédié au système d'IA", "provenance": "cabinet"},
    ],
    "n_modeles_tarifaires": [
        {"valeur": 4, "libelle": "Quelques modèles de tarification touchés", "provenance": "scenario"},
        {"valeur": 20, "libelle": "Portefeuille complet vie et non-vie", "provenance": "scenario"},
    ],
    "jours_validation_modele": [
        {"valeur": 15, "libelle": "Validation indépendante d'un modèle documenté", "provenance": "cabinet"},
        {"valeur": 45, "libelle": "Modèle structurant, revue actuarielle complète", "provenance": "cabinet"},
    ],
    "jours_orsa_ia": [
        {"valeur": 20, "libelle": "Rattachement des systèmes d'IA à l'évaluation existante",
         "provenance": "cabinet"},
        {"valeur": 60, "libelle": "Chapitre dédié, première année", "provenance": "cabinet"},
    ],
    "n_cas_composant_securite": [
        {"valeur": 0, "libelle": "Aucun composant de sécurité identifié", "provenance": "scenario"},
        {"valeur": 3, "libelle": "Trois cas qualifiés composants de sécurité", "provenance": "scenario"},
    ],
    "jours_safety_case": [
        {"valeur": 30, "libelle": "Dossier de sûreté sur une fonction bien bornée", "provenance": "cabinet"},
        {"valeur": 90, "libelle": "Fonction critique, démonstration complète", "provenance": "cabinet"},
    ],
    "jours_procedure_incidents": [
        {"valeur": 15, "libelle": "Rattachement à la chaîne d'alerte existante", "provenance": "cabinet"},
        {"valeur": 45, "libelle": "Chaîne à construire, exercices inclus", "provenance": "cabinet"},
    ],
    "n_zones_ot": [
        {"valeur": 2, "libelle": "Deux zones industrielles raccordées", "provenance": "scenario"},
        {"valeur": 10, "libelle": "Parc étendu, plusieurs sites", "provenance": "scenario"},
    ],
    "jours_segmentation_zone": [
        {"valeur": 20, "libelle": "Conduit simple vers une zone déjà segmentée", "provenance": "cabinet"},
        {"valeur": 60, "libelle": "Segmentation à reprendre, recette sur site", "provenance": "cabinet"},
    ],

    # ── les prix : c'est ici que la prudence se paie ──
    "tjm_conseil": [
        {"valeur": 900, "libelle": "Cadrage et pilotage, profil confirmé", "provenance": "cabinet"},
        {"valeur": 1500, "libelle": "Associé ou expert rare, mission courte", "provenance": "cabinet"},
    ],
    "tjm_interne": [
        {"valeur": 450, "libelle": "Cadre mobilisé, coût complet chargé", "provenance": "cabinet"},
        {"valeur": 700, "libelle": "Expert interne rare", "provenance": "cabinet"},
    ],
    "cout_etp_ia": [
        {"valeur": 95000, "libelle": "Constructeur de modèles confirmé, coût chargé", "provenance": "cabinet"},
        {"valeur": 140000, "libelle": "Profil senior ou lead", "provenance": "cabinet"},
    ],
    "cout_etp_plateforme": [
        {"valeur": 85000, "libelle": "Ingénieur plateforme confirmé, coût chargé", "provenance": "cabinet"},
        {"valeur": 125000, "libelle": "Profil senior ou lead", "provenance": "cabinet"},
    ],
    "cout_infra_an": [
        {"valeur": 250000, "libelle": "Socle mutualisé, consommation maîtrisée", "provenance": "cabinet"},
        {"valeur": 2000000, "libelle": "Socle dédié, entraînement inclus", "provenance": "cabinet"},
        {"valeur": 6500000, "libelle": "Grappe clé en main d'entrée de gamme (7 M$, achat — pas un loyer)",
         "provenance": "ancrage", "ancrage": "grappe_calcul"},
    ],
    "cout_outillage_an": [
        {"valeur": 120000, "libelle": "Outillage et licences, périmètre restreint", "provenance": "cabinet"},
        {"valeur": 600000, "libelle": "Chaîne complète, licences par utilisateur incluses",
         "provenance": "cabinet"},
    ],
    "cout_securite_an": [
        {"valeur": 150000, "libelle": "Supervision adossée au centre existant", "provenance": "cabinet"},
        {"valeur": 500000, "libelle": "Supervision dédiée au socle IA", "provenance": "cabinet"},
    ],
    "prix_M_jetons": [
        {"valeur": 0.5, "libelle": "Entrée d'un modèle de premier rang, tarif public bas",
         "provenance": "ancrage", "ancrage": "jetons"},
        {"valeur": 1.5, "libelle": "Sortie d'un modèle de premier rang, tarif public haut",
         "provenance": "ancrage", "ancrage": "jetons"},
    ],
    "cout_heure_formation": [
        {"valeur": 60, "libelle": "Module en ligne, temps salarié inclus", "provenance": "cabinet"},
        {"valeur": 180, "libelle": "Présentiel animé, temps salarié inclus", "provenance": "cabinet"},
    ],
    "cout_interface": [
        {"valeur": 15000, "libelle": "Interface simple, contrat stable", "provenance": "cabinet"},
        {"valeur": 60000, "libelle": "Interface métier, reprise de données", "provenance": "cabinet"},
    ],
    "cout_audit_cas": [
        {"valeur": 40000, "libelle": "Dossier annexe III, contrôle interne", "provenance": "cabinet"},
        {"valeur": 120000, "libelle": "Dossier avec évaluation par un organisme tiers",
         "provenance": "cabinet"},
    ],
}


def _verifier_exemples():
    """Refuse au chargement plutôt qu'à l'affichage.

    TROIS FAÇONS DE MENTIR SANS S'EN APERCEVOIR, et une garde pour chacune :
    un exemple posé sur un champ qui n'existe pas ne s'afficherait jamais ; une
    provenance inconnue ne dirait rien au lecteur ; et un exemple « ancrage »
    qui désigne un ancrage absent se réclame d'une source qu'on ne peut pas
    rouvrir — c'est-à-dire d'une intention."""
    cles_ancrages = {a["cle"] for a in ANCRAGES}
    for champ, liste in EXEMPLES.items():
        if champ not in QUANTITES and champ not in PRIX and champ not in QUANTITES_SECTEUR:
            raise ValueError("exemples posés sur un champ inconnu : %s" % champ)
        for ex in liste:
            if ex["provenance"] not in PROVENANCES:
                raise ValueError("provenance inconnue pour %s : %s" % (champ, ex["provenance"]))
            if ex["provenance"] == "ancrage":
                if ex.get("ancrage") not in cles_ancrages:
                    raise ValueError("l'exemple « %s » de %s se réclame d'un ancrage absent : %r"
                                     % (ex["libelle"], champ, ex.get("ancrage")))
            elif "ancrage" in ex:
                raise ValueError("l'exemple « %s » de %s désigne un ancrage sans s'en réclamer"
                                 % (ex["libelle"], champ))


_verifier_exemples()


def valeurs_dexemple(quantites, prix):
    """Les saisies restées ÉGALES à un exemple offert.

    C'EST LA SEULE GARDE QUI COMPTE. Les deux autres — ne rien
    pré-sélectionner, dire d'où vient chaque exemple — ne protègent que le
    moment de la saisie. Celle-ci protège l'étude EXPORTÉE : un client qui
    n'aurait rien remplacé repartirait sinon avec les ordres de grandeur du
    cabinet présentés comme les siens.

    Elle ne prétend pas lire dans les pensées : une valeur peut coïncider avec
    un exemple parce que c'est la bonne. Elle SIGNALE, elle n'accuse pas."""
    saisi = {}
    saisi.update({k: _nombre(v) for k, v in (quantites or {}).items()})
    saisi.update({k: _nombre(v) for k, v in (prix or {}).items()})
    out = []
    for champ, liste in EXEMPLES.items():
        v = saisi.get(champ)
        if v is None:
            continue
        for ex in liste:
            if abs(float(ex["valeur"]) - v) < 1e-9:
                d = QUANTITES.get(champ) or QUANTITES_SECTEUR.get(champ) or PRIX[champ]
                out.append({"champ": champ, "nom": d["nom"], "unite": d["unite"],
                            "valeur": ex["valeur"], "libelle": ex["libelle"],
                            "provenance": ex["provenance"],
                            "dit": PROVENANCES[ex["provenance"]],
                            "a_remplacer": ex["provenance"] == "cabinet"})
                break
    out.sort(key=lambda x: (not x["a_remplacer"], x["champ"]))
    return out

# ═══════════════════════════════════════════════════════════════════════════
#  4. LES POSTES — la structure qui reçoit vos prix ; chacun dit ce qu'il couvre
# ═══════════════════════════════════════════════════════════════════════════

GROUPES = [
    ("cadrage", "1 · Cadrage, gouvernance et pilotage"),
    ("socle", "2 · Socle plateforme (infrastructure, outillage, sécurité)"),
    ("usine", "3 · Usine IA — l'équipe centrale (hub)"),
    ("cas", "4 · Cas d'usage métier (spokes)"),
    ("changement", "5 · Conduite du changement et formation"),
    ("migration", "6 · Migration et intégration des systèmes"),
    ("conformite", "7 · Conformité et maîtrise des risques"),
    ("secteur", "8 · Exigences propres au secteur"),
    ("run", "9 · Exploitation (run) sur l'horizon"),
    ("aleas", "10 · Provision pour aléas"),
]


def _annees(q):
    return (q.get("duree_mois") or 0) / 12.0


POSTES = [
    {"cle": "cadrage_initial", "groupe": "cadrage", "nom": "Cadrage et étude de faisabilité",
     "formule": "jours_cadrage × tjm_conseil",
     "calc": lambda q, p: q["jours_cadrage"] * p["tjm_conseil"],
     "besoin": ["jours_cadrage", "tjm_conseil"],
     "couvre": "Note de cadrage, portefeuille de cas d'usage arbitré, qualification juridique dossier "
               "par dossier, cette étude chiffrée sur vos entrées.",
     "exclut": "Toute étude d'architecture détaillée : elle relève du socle."},
    {"cle": "pilotage", "groupe": "cadrage", "nom": "Pilotage et contre-pilotage sur l'horizon",
     "formule": "jours_pmo_mois × duree_mois × tjm_conseil",
     "calc": lambda q, p: q["jours_pmo_mois"] * q["duree_mois"] * p["tjm_conseil"],
     "besoin": ["jours_pmo_mois", "duree_mois", "tjm_conseil"],
     "couvre": "Coordination des lots, suivi du calendrier et de la trajectoire financière, audit des "
               "arbitrages techniques et budgétaires, comitologie.",
     "exclut": "Le pilotage interne du client (chefs de projet métier), compté en coût interne dans "
               "les cas d'usage.",
     "note": "Le cas A sépare un pilotage principal et un lot d'accompagnement du changement : deux "
             "dispositifs, deux lignes."},
    {"cle": "infra", "groupe": "socle", "nom": "Infrastructure IA",
     "formule": "cout_infra_an × années",
     "calc": lambda q, p: p["cout_infra_an"] * _annees(q),
     "besoin": ["cout_infra_an", "duree_mois"],
     "couvre": "Calcul (grappe sur site ou cloud souverain qualifié), stockage, réseau, hébergement, "
               "énergie et refroidissement s'ils sont facturés.",
     "exclut": "Les jetons d'inférence achetés à un fournisseur de modèles : ils sont au run."},
    {"cle": "outillage", "groupe": "socle", "nom": "Outillage MLOps / LLMOps et licences",
     "formule": "cout_outillage_an × années",
     "calc": lambda q, p: p["cout_outillage_an"] * _annees(q),
     "besoin": ["cout_outillage_an", "duree_mois"],
     "couvre": "Registre de modèles, chaîne de livraison, évaluation, observabilité, gestion des "
               "invites, licences par utilisateur des assistants.",
     "exclut": "Le développement des cas d'usage eux-mêmes."},
    {"cle": "securite", "groupe": "socle", "nom": "Sécurité et supervision du socle",
     "formule": "cout_securite_an × années",
     "calc": lambda q, p: p["cout_securite_an"] * _annees(q),
     "besoin": ["cout_securite_an", "duree_mois"],
     "couvre": "Centre de supervision, tests d'intrusion, revue de code modèle, filtrage des entrées "
               "et des sorties, journalisation exigée par le règlement sur l'IA.",
     "exclut": "La segmentation vers les zones OT chez un opérateur d'infrastructure : poste sectoriel."},
    {"cle": "equipe_modeles", "groupe": "usine", "nom": "Constructeurs de modèles",
     "formule": "n_cas_usage × etp_par_cas × cout_etp_ia × années",
     "calc": lambda q, p: q["n_cas_usage"] * q["etp_par_cas"] * p["cout_etp_ia"] * _annees(q),
     "besoin": ["n_cas_usage", "etp_par_cas", "cout_etp_ia", "duree_mois"],
     "couvre": "Data scientists, ingénieurs ML, ingénieurs d'invites, sur toute la durée.",
     "exclut": "Les profils métier détachés : ils sont dans les cas d'usage."},
    {"cle": "equipe_plateforme", "groupe": "usine", "nom": "Ingénieurs plateforme et data",
     "formule": "n_cas_usage × etp_par_cas × (ratio_plateforme + ratio_data) × cout_etp_plateforme × années",
     "calc": lambda q, p: _dim(q)["plateforme"]["max"] * p["cout_etp_plateforme"] * _annees(q),
     "besoin": ["n_cas_usage", "etp_par_cas", "cout_etp_plateforme", "duree_mois"],
     "couvre": "Ingénieurs plateforme, data engineers, fiabilité et exploitation du socle.",
     "exclut": "Rien de l'infrastructure elle-même, qui est au poste précédent.",
     "note": "Chiffré sur la borne HAUTE des ratios sourcés (1 pour 4, 1 pour 2) : sous-dimensionner "
             "la plateforme est le goulot documenté."},
    {"cle": "cas_usage", "groupe": "cas", "nom": "Développement des cas d'usage",
     "formule": "n_cas_usage × jours_par_cas × tjm_interne",
     "calc": lambda q, p: q["n_cas_usage"] * q["jours_par_cas"] * p["tjm_interne"],
     "besoin": ["n_cas_usage", "jours_par_cas", "tjm_interne"],
     "couvre": "Le temps des métiers et des équipes projet : cadrage du cas, données, recette "
               "fonctionnelle, mise en production, mesure.",
     "exclut": "Le temps des constructeurs de modèles, compté dans l'usine."},
    {"cle": "formation", "groupe": "changement", "nom": "Formation des salariés",
     "formule": "effectif × part_formes × heures_formation × cout_heure_formation",
     "calc": lambda q, p: q["effectif"] * q["part_formes"] * q["heures_formation"] * p["cout_heure_formation"],
     "besoin": ["effectif", "part_formes", "heures_formation", "cout_heure_formation"],
     "couvre": "Socle commun (usage, limites, données, article 4), puis parcours par métier ; le temps "
               "salarié si votre coût horaire l'inclut.",
     "exclut": "La formation des constructeurs de modèles (grille RH)."},
    {"cle": "ambassadeurs", "groupe": "changement", "nom": "Réseau d'ambassadeurs métier",
     "formule": "n_metiers × jours_par_cas × tjm_interne",
     "calc": lambda q, p: q["n_metiers"] * q["jours_par_cas"] * p["tjm_interne"],
     "besoin": ["n_metiers", "jours_par_cas", "tjm_interne"],
     "couvre": "Un relais par métier, formé avant les autres, mobilisé à hauteur d'un cas d'usage.",
     "exclut": "Le management de proximité, dont le temps n'est pas isolé ici.",
     "note": "C'est la convention retenue, écrite ici pour être discutée."},
    {"cle": "interfaces", "groupe": "migration", "nom": "Portage des interfaces",
     "formule": "n_interfaces × cout_interface × (2 si n_si_source > 1, sinon 1)",
     "calc": lambda q, p: q["n_interfaces"] * p["cout_interface"] * (2 if q.get("n_si_source", 1) > 1 else 1),
     "besoin": ["n_interfaces", "cout_interface"],
     "couvre": "Connexion du socle IA aux systèmes de gestion, référentiels, canaux.",
     "exclut": "La migration du cœur lui-même, qui a son propre programme.",
     "note": "PORTÉES DEUX FOIS pendant une migration de cœur : une fois vers l'ancien socle, une "
             "fois vers le nouveau. C'est le poste que le neuf ne connaît pas."},
    {"cle": "recette", "groupe": "migration", "nom": "Recette des interfaces",
     "formule": "n_interfaces × jours_recette_interface × tjm_interne",
     "calc": lambda q, p: q["n_interfaces"] * q["jours_recette_interface"] * p["tjm_interne"],
     "besoin": ["n_interfaces", "jours_recette_interface", "tjm_interne"],
     "couvre": "Jeux d'essai, recette fonctionnelle et technique, non-régression après bascule.",
     "exclut": "Les tests de résilience réglementaires (poste sectoriel)."},
    {"cle": "conformite_annexe3", "groupe": "conformite", "nom": "Dossiers de conformité annexe III",
     "formule": "n_cas_haut_risque × cout_audit_cas",
     "calc": lambda q, p: q["n_cas_haut_risque"] * p["cout_audit_cas"],
     "besoin": ["n_cas_haut_risque", "cout_audit_cas"],
     "couvre": "Documentation technique, système de gestion des risques, gouvernance des données, "
               "surveillance humaine, journalisation, évaluation de conformité, enregistrement.",
     "exclut": "La transparence de l'article 50, qui relève du développement de chaque cas."},
    {"cle": "inference", "groupe": "run", "nom": "Inférence (jetons)",
     "formule": "tokens_mois × 12 × années × prix_M_jetons",
     "calc": lambda q, p: q["tokens_mois"] * 12 * _annees(q) * p["prix_M_jetons"],
     "besoin": ["tokens_mois", "prix_M_jetons", "duree_mois"],
     "couvre": "Les appels aux modèles en exploitation, sur l'horizon.",
     "exclut": "L'entraînement ou l'ajustement fin de modèles, à chiffrer au socle s'il a lieu."},
]

# Les postes que seul un secteur connaît. Ils entrent dans le chiffrage quand le
# secteur est choisi ; ils portent leur groupe « secteur » et leurs entrées.
POSTES_SECTEUR = [
    {"cle": "registre_dora", "groupe": "secteur", "secteurs": ("banque", "assurance", "marches"),
     "nom": "Registre des prestataires TIC incluant les fournisseurs de modèles (DORA)",
     "formule": "n_fournisseurs_ia × jours_registre_fournisseur × tjm_interne",
     "calc": lambda q, p: q["n_fournisseurs_ia"] * q["jours_registre_fournisseur"] * p["tjm_interne"],
     "besoin": ["n_fournisseurs_ia", "jours_registre_fournisseur", "tjm_interne"],
     "couvre": "Instruction contractuelle, sous-traitance en chaîne, localisation des données, "
               "stratégie de sortie, inscription au registre d'information.",
     "exclut": "La négociation commerciale des contrats."},
    {"cle": "tests_resilience", "groupe": "secteur", "secteurs": ("banque", "assurance", "marches"),
     "nom": "Tests de résilience opérationnelle numérique incluant les systèmes d'IA (DORA)",
     "formule": "n_cas_usage × jours_test_resilience_cas × tjm_interne",
     "calc": lambda q, p: q["n_cas_usage"] * q["jours_test_resilience_cas"] * p["tjm_interne"],
     "besoin": ["n_cas_usage", "jours_test_resilience_cas", "tjm_interne"],
     "couvre": "Scénarios de panne du fournisseur de modèle, dégradation, bascule vers un mode "
               "dégradé, rejeu des incidents.",
     "exclut": "Les tests de pénétration fondés sur la menace, qui ont leur propre programme."},
    {"cle": "validation_actuarielle", "groupe": "secteur", "secteurs": ("assurance",),
     "nom": "Validation actuarielle indépendante des modèles assistés par IA",
     "formule": "n_modeles_tarifaires × jours_validation_modele × tjm_interne",
     "calc": lambda q, p: q["n_modeles_tarifaires"] * q["jours_validation_modele"] * p["tjm_interne"],
     "besoin": ["n_modeles_tarifaires", "jours_validation_modele", "tjm_interne"],
     "couvre": "Second regard sur la tarification et le provisionnement, explicabilité, équité, "
               "dérive, conformément à l'avis de l'autorité européenne de 2025.",
     "exclut": "L'évaluation de conformité annexe III, comptée au groupe 7."},
    {"cle": "orsa_ia", "groupe": "secteur", "secteurs": ("assurance",),
     "nom": "Intégration des systèmes d'IA à l'évaluation interne des risques et à la solvabilité",
     "formule": "jours_orsa_ia × tjm_interne",
     "calc": lambda q, p: q["jours_orsa_ia"] * p["tjm_interne"],
     "besoin": ["jours_orsa_ia", "tjm_interne"],
     "couvre": "Cartographie des risques des systèmes d'IA, appétence, scénarios, gouvernance du "
               "système de gestion des risques.",
     "exclut": "Le calcul du capital de solvabilité lui-même."},
    {"cle": "safety_case", "groupe": "secteur", "secteurs": ("nis2",),
     "nom": "Dossier de sûreté par composant de sécurité d'infrastructure critique",
     "formule": "n_cas_composant_securite × jours_safety_case × tjm_interne",
     "calc": lambda q, p: q["n_cas_composant_securite"] * q["jours_safety_case"] * p["tjm_interne"],
     "besoin": ["n_cas_composant_securite", "jours_safety_case", "tjm_interne"],
     "couvre": "Analyse de risques, exigences de sûreté, preuves, mode de repli sûr, surveillance "
               "humaine effective.",
     "exclut": "Le dossier de conformité annexe III, qui s'y ajoute (groupe 7)."},
    {"cle": "notification_incidents", "groupe": "secteur", "secteurs": ("nis2",),
     "nom": "Chaîne de notification 24 h / 72 h / un mois intégrant les incidents des systèmes d'IA",
     "formule": "jours_procedure_incidents × tjm_interne",
     "calc": lambda q, p: q["jours_procedure_incidents"] * p["tjm_interne"],
     "besoin": ["jours_procedure_incidents", "tjm_interne"],
     "couvre": "Qualification d'un incident IA en incident important, alerte précoce, notification, "
               "rapport final, exercices.",
     "exclut": "L'outillage de détection, compté à la sécurité du socle."},
    {"cle": "segmentation_ot", "groupe": "secteur", "secteurs": ("nis2",),
     "nom": "Segmentation et conduits entre le socle IA et les zones OT (IEC 62443)",
     "formule": "n_zones_ot × jours_segmentation_zone × tjm_interne",
     "calc": lambda q, p: q["n_zones_ot"] * q["jours_segmentation_zone"] * p["tjm_interne"],
     "besoin": ["n_zones_ot", "jours_segmentation_zone", "tjm_interne"],
     "couvre": "Conception des conduits, DMZ industrielle, bastion ou diode, recette, exigences "
               "composants.",
     "exclut": "Les équipements eux-mêmes, au bordereau du lot."},
]


# ═══════════════════════════════════════════════════════════════════════════
#  5. LES SECTEURS — textes, jalons, cas d'usage typés, et ce qui est propre à chacun
# ═══════════════════════════════════════════════════════════════════════════
#
# La classe d'un cas d'usage n'est PAS une qualification juridique : c'est la
# case où la question se pose. Le vocabulaire est fermé pour que le lecteur
# sache ce qu'il lit.

CLASSES_CAS = {
    "haut_risque_annexe_III": "Relève, sauf exception, de l'annexe III : dossier de conformité, "
                              "surveillance humaine, enregistrement — échéance 2 décembre 2027.",
    "a_qualifier": "La classe dépend de la finalité et de l'effet sur les personnes : analyse "
                   "juridique dossier par dossier.",
    "transparence_art_50": "Interaction avec des personnes ou contenu généré : obligations de "
                           "transparence en vigueur depuis le 2 août 2026.",
    "hors_composant_securite": "Finalité de cybersécurité seule : n'est pas un composant de sécurité "
                               "au sens de l'annexe III, point 2.",
    "minimal": "Aucune obligation spécifique du règlement, hors maîtrise de l'IA (article 4) et "
               "droit commun.",
}

SECTEURS = {
    "banque": {
        "nom": "Banque de détail et de financement",
        "resume": "Le secteur où l'IA est déjà partout — plus de 85 % des banques supervisées "
                  "l'utilisent — et où deux textes commandent le calendrier : DORA depuis janvier "
                  "2025, le règlement sur l'IA pour la notation de crédit et l'évaluation de "
                  "solvabilité au 2 décembre 2027.",
        "textes": ["dora", "ai_act", "omnibus_2026", "omnibus_analyse", "bce_priorites_2026",
                   "bce_ia_newsletter", "acpr_autorite_ia", "acpr_reflexion_ia", "bdf_rapport_ia_2025"],
        "autorites": "Superviseur bancaire européen pour les établissements importants ; autorité "
                     "prudentielle nationale, désignée pour le règlement sur l'IA en banque et assurance.",
        "jalons": [],
        "cas_usage": [
            {"nom": "Évaluation de solvabilité et notation de crédit des personnes physiques",
             "classe": "haut_risque_annexe_III", "pourquoi": "Annexe III, point 5 b."},
            {"nom": "Agent vocal ou conversationnel de relation client",
             "classe": "transparence_art_50", "pourquoi": "Interaction directe avec des personnes."},
            {"nom": "Détection de fraude aux paiements", "classe": "a_qualifier",
             "pourquoi": "Exclue de l'annexe III lorsqu'elle sert à détecter la fraude financière ; "
                         "à vérifier dossier par dossier."},
            {"nom": "Scoring d'alertes de lutte contre le blanchiment", "classe": "a_qualifier",
             "pourquoi": "Effet sur les personnes (gel, déclaration) : la finalité décide."},
            {"nom": "Assistant du conseiller (résumés, rédaction, recherche documentaire)",
             "classe": "minimal", "pourquoi": "Aide à la rédaction sans décision automatisée."},
        ],
        "propre": "Le registre DORA des prestataires TIC accueille chaque fournisseur de modèle ; "
                  "les tests de résilience couvrent les systèmes d'IA en production.",
    },
    "assurance": {
        "nom": "Assurance et réassurance",
        "resume": "L'avis de l'autorité européenne du 6 août 2025 ne crée pas de règle : il lit "
                  "Solvabilité II, la distribution, DORA et le RGPD à la lumière du règlement sur "
                  "l'IA. Solvabilité II révisée s'applique au 30 janvier 2027 ; la tarification vie "
                  "et santé relève de l'annexe III.",
        "textes": ["eiopa_opinion", "solvency2", "solvency2_2027", "dora", "dora_directive",
                   "ai_act", "omnibus_analyse", "acpr_autorite_ia"],
        "autorites": "Autorité européenne des assurances ; autorité prudentielle nationale.",
        "jalons": [
            {"date": "2027-01-30", "texte": "Solvabilité II révisée — directive (UE) 2025/2 applicable",
             "source": "solvency2_2027",
             "porte": "Proportionnalité, risques nouveaux, supervision transfrontière : la gouvernance "
                      "des systèmes d'IA s'inscrit dans le système de gestion des risques révisé."},
        ],
        "cas_usage": [
            {"nom": "Tarification et évaluation des risques en assurance vie et santé",
             "classe": "haut_risque_annexe_III", "pourquoi": "Annexe III, point 5 c."},
            {"nom": "Tarification dommages (automobile, habitation)", "classe": "a_qualifier",
             "pourquoi": "Hors point 5 c ; l'équité et l'explicabilité restent exigées par l'avis de 2025."},
            {"nom": "Tri et règlement automatisé des sinistres", "classe": "a_qualifier",
             "pourquoi": "Décision à effet sur les personnes ; surveillance humaine attendue."},
            {"nom": "Détection de fraude aux sinistres", "classe": "a_qualifier",
             "pourquoi": "Même logique que la fraude bancaire : la finalité décide."},
            {"nom": "Assistant de souscription et de gestion", "classe": "minimal",
             "pourquoi": "Aide à la décision sans décision automatisée."},
        ],
        "propre": "Validation actuarielle indépendante des modèles assistés ; intégration des "
                  "systèmes d'IA à l'évaluation interne des risques et de la solvabilité.",
    },
    "marches": {
        "nom": "Marchés, gestion d'actifs, infrastructures de marché",
        "resume": "DORA s'applique en tant que règlement spécial ; les infrastructures de marché "
                  "figurent aussi à l'annexe I de NIS 2. Peu de cas relèvent de l'annexe III du "
                  "règlement sur l'IA ; la question est celle de la résilience et de la traçabilité.",
        "textes": ["dora", "dora_directive", "nis2", "ai_act", "omnibus_analyse"],
        "autorites": "Autorité des marchés ; autorité prudentielle pour les établissements concernés.",
        "jalons": [],
        "cas_usage": [
            {"nom": "Surveillance des abus de marché — priorisation d'alertes", "classe": "a_qualifier",
             "pourquoi": "Effet sur des personnes physiques possible ; traçabilité exigée."},
            {"nom": "Recherche et synthèse documentaire", "classe": "minimal",
             "pourquoi": "Aide à l'analyse."},
            {"nom": "Négociation algorithmique assistée", "classe": "a_qualifier",
             "pourquoi": "Encadrée par le droit des marchés ; le règlement sur l'IA s'y ajoute rarement."},
        ],
        "propre": "Tests de résilience et registre des prestataires, comme en banque ; la double "
                  "appartenance DORA / NIS 2 se règle par la primauté de DORA (règlement spécial).",
    },
    "nis2": {
        "nom": "Infrastructures critiques — entités essentielles et importantes (NIS 2)",
        "resume": "Dix-huit secteurs, dont l'énergie, les transports, la santé, l'eau et les "
                  "infrastructures numériques. En France, la loi de transposition n'était pas "
                  "promulguée au 6 août 2026, mais la directive s'applique dans ses échéances "
                  "et le référentiel de l'agence nationale est publié. Un système d'IA « composant "
                  "de sécurité » d'une infrastructure critique relève de l'annexe III.",
        "textes": ["nis2", "cer", "nis2_france", "nis2_incidents", "annexe3_infra", "ai_act",
                   "omnibus_analyse", "ai_act_politique"],
        "autorites": "Agence nationale de la sécurité des systèmes d'information ; autorités "
                     "sectorielles.",
        "jalons": [
            {"date": "2024-10-17", "texte": "NIS 2 — date limite de transposition (article 41)",
             "source": "nis2",
             "porte": "Dépassée en France ; procédure d'infraction ouverte. L'obligation de "
                      "l'entité ne dépend pas du retard de la loi nationale pour ce qui est "
                      "directement applicable, et l'agence nationale a publié son référentiel."},
            {"date": "2024-10-18", "texte": "NIS 2 — mesures de gestion des risques (article 21) et notification des incidents (article 23)",
             "source": "nis2_incidents",
             "porte": "Alerte précoce sous 24 h, notification sous 72 h, rapport final sous un mois : "
                      "un incident d'un système d'IA qui touche un service essentiel entre dans "
                      "cette chaîne."},
        ],
        "cas_usage": [
            {"nom": "Pilotage ou protection en temps réel d'un réseau (électricité, gaz, chaleur, eau)",
             "classe": "haut_risque_annexe_III",
             "pourquoi": "Annexe III, point 2 : composant de sécurité dont la défaillance menace "
                         "l'intégrité physique ou la sécurité des personnes."},
            {"nom": "Maintenance prédictive d'équipements", "classe": "a_qualifier",
             "pourquoi": "Un outil de planification sans action directe sur le procédé n'est pas un "
                         "composant de sécurité ; un déclencheur d'arrêt en est un."},
            {"nom": "Gestion du trafic routier", "classe": "haut_risque_annexe_III",
             "pourquoi": "Annexe III, point 2, nommément."},
            {"nom": "Détection d'anomalies OT au centre de supervision", "classe": "hors_composant_securite",
             "pourquoi": "Finalité de cybersécurité seule : exclue de la notion de composant de sécurité."},
            {"nom": "Assistant documentaire des exploitants", "classe": "minimal",
             "pourquoi": "Aide à la consultation de procédures."},
        ],
        "propre": "Dossier de sûreté par composant de sécurité ; chaîne de notification 24 h / 72 h / "
                  "un mois ; segmentation IEC 62443 entre le socle IA et les zones OT.",
        "secteurs_annexe_I": ["énergie", "transports", "banque", "infrastructures des marchés financiers",
                              "santé", "eau potable", "eaux usées", "infrastructures numériques",
                              "gestion des services TIC", "administration publique", "espace"],
        "secteurs_annexe_II": ["services postaux", "gestion des déchets", "produits chimiques",
                               "alimentation", "fabrication", "fournisseurs numériques", "recherche"],
    },
}


def _nombre(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and f >= 0 else None


def _dim(q):
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
    q = {k: _nombre(v) for k, v in (quantites or {}).items()}
    if not q.get("n_cas_usage") or not q.get("etp_par_cas"):
        return {"instruit": False,
                "manque": [k for k in ("n_cas_usage", "etp_par_cas") if not q.get(k)],
                "dit": "Sans le nombre de cas d'usage et l'effectif par cas, aucune équipe ne se "
                       "dimensionne — et le module refuse d'en poser une par défaut."}
    d = _dim(q)
    total_min = d["constructeurs"]["min"] + d["plateforme"]["min"]
    total_max = d["constructeurs"]["max"] + d["plateforme"]["max"]
    ca = [a for a in ANCRAGES if a["cle"] == "casB_entite_ia_etp"][0]
    return {"instruit": True, "roles": d,
            "total": {"min": round(total_min, 1), "max": round(total_max, 1)},
            "ancrage": {"nom": ca["nom"], "valeur": ca["max"], "unite": ca["unite"],
                        "ne_dit_pas": ca["ne_dit_pas"]},
            "dit": "Fourchette issue des ratios sourcés ; à comparer à l'entité IA du cas B "
                   "(~150 ETP) pour situer, pas pour caler."}


def _postes_pour(secteur):
    base = list(POSTES)
    if secteur in SECTEURS:
        base += [p for p in POSTES_SECTEUR if secteur in p["secteurs"]]
    return base


def quantites_pour(secteur):
    """Les quantités à saisir : les communes, plus celles du secteur choisi."""
    out = dict(QUANTITES)
    if secteur in SECTEURS:
        for k, v in QUANTITES_SECTEUR.items():
            if secteur in v["secteurs"]:
                out[k] = {kk: vv for kk, vv in v.items() if kk != "secteurs"}
    return out


def chiffrer(quantites, prix, provision_pct=None, secteur=None):
    """Le chiffrage, poste par poste, secteur compris — et le compte de ce qui
    n'est pas chiffré. Un poste dont une entrée manque ressort `non_chiffre`
    avec la liste de ce qui manque ; il n'est pas compté à zéro."""
    q = {k: _nombre(v) for k, v in (quantites or {}).items()}
    p = {k: _nombre(v) for k, v in (prix or {}).items()}
    secteur = secteur if secteur in SECTEURS else None
    attendues = quantites_pour(secteur)
    lignes, sous_total, non_chiffres = [], 0.0, []
    for poste in _postes_pour(secteur):
        manque = [k for k in poste["besoin"]
                  if (k in attendues and q.get(k) is None) or (k in PRIX and p.get(k) is None)]
        ligne = {"cle": poste["cle"], "groupe": poste["groupe"], "nom": poste["nom"],
                 "formule": poste["formule"], "note": poste.get("note"),
                 "couvre": poste.get("couvre"), "exclut": poste.get("exclut"),
                 "sectoriel": "secteurs" in poste}
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
    prov = _nombre(provision_pct)
    depassement = [a for a in ANCRAGES if a["cle"] == "migration_depassement"][0]
    alertes, provision = [], None
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
    if secteur is None:
        alertes.append("Aucun secteur choisi : les postes propres au secteur ne sont pas dans "
                       "cette structure, et l'étude est de ce fait incomplète.")
    return {"ok": True, "version": VERSION, "secteur": secteur, "lignes": lignes,
            "par_groupe": par_groupe, "sous_total": round(sous_total, 2),
            "provision": provision, "provision_pct": prov,
            "total": round(sous_total + (provision or 0.0), 2) if prov is not None else None,
            "n_postes": n, "n_non_chiffres": len(non_chiffres), "part_non_chiffree": part_nc,
            "alertes": alertes, "dimensionnement": dimensionnement(q)}


# ═══════════════════════════════════════════════════════════════════════════
#  6. LE PLANNING — phases (glissent), jalons réglementaires (ne glissent pas)
# ═══════════════════════════════════════════════════════════════════════════

PHASES = [
    {"cle": "faisabilite", "nom": "Cadrage et faisabilité", "mois_min": 2, "mois_max": 4,
     "activites": ["Entretiens par ligne métier", "Inventaire des pilotes et de leurs consommations réelles",
                   "Qualification juridique dossier par dossier", "Choix du secteur et de ses exigences",
                   "Chiffrage sur quantités et prix du client"],
     "entree": "Mandat de la direction générale ; accès aux pilotes et au contrôle de gestion.",
     "sortie": "Portefeuille arbitré, étude chiffrée avec sa part non chiffrée, décision d'engager.",
     "livrables": ["Note de cadrage", "Portefeuille de cas d'usage arbitré",
                   "Qualification annexe III dossier par dossier", "Cette étude chiffrée"],
     "jalon": "Décision d'engager (comité de direction)"},
    {"cle": "socle", "nom": "Socle et gouvernance", "mois_min": 3, "mois_max": 6,
     "activites": ["Architecture de plateforme et choix d'hébergement", "Chaîne de livraison et registre de modèles",
                   "Charte, comité et registre des systèmes d'IA", "Ouverture de la négociation sociale",
                   "Registre des prestataires TIC ou dossier de sûreté selon le secteur"],
     "entree": "Décision d'engager ; équipe centrale recrutée ou détachée au moins pour moitié.",
     "sortie": "Socle en service avec sa supervision ; premier cas déployable ; gouvernance réunie une fois.",
     "livrables": ["Plateforme (infrastructure, MLOps/LLMOps, sécurité)", "Charte IA et comité",
                   "Registre des systèmes d'IA", "Accord social ouvert"],
     "jalon": "Socle en service, premier cas déployable"},
    {"cle": "pilotes", "nom": "Pilotes (3 à 5 cas d'usage)", "mois_min": 4, "mois_max": 6,
     "activites": ["Un cas par métier prioritaire, en production supervisée", "Mesure d'adoption et de valeur",
                   "Relevé des jours, ETP et jetons réellement consommés", "Premier exercice de notification d'incident"],
     "entree": "Socle en service ; ambassadeurs formés.",
     "sortie": "Retours d'expérience chiffrés qui remplacent les hypothèses de l'étude.",
     "livrables": ["Cas en production supervisée", "Mesure d'adoption et de valeur",
                   "Retours d'expérience chiffrés (jours, ETP, jetons)"],
     "jalon": "Go / no-go d'industrialisation"},
    {"cle": "industrialisation", "nom": "Industrialisation — vague 1", "mois_min": 6, "mois_max": 12,
     "activites": ["Chaîne de livraison outillée de bout en bout", "Cas d'usage par métier",
                   "Formation socle déployée", "Dossiers annexe III ouverts pour les cas concernés"],
     "entree": "Go d'industrialisation ; étude re-chiffrée sur les retours des pilotes.",
     "sortie": "Part de salariés utilisateurs mesurée ; premiers dossiers de conformité déposés.",
     "livrables": ["Chaîne de livraison outillée", "Cas d'usage en production par métier",
                   "Formation socle déployée"],
     "jalon": "Part de salariés utilisateurs mesurée (cible à fixer)"},
    {"cle": "generalisation", "nom": "Généralisation", "mois_min": 12, "mois_max": 24,
     "activites": ["Essaimage dans l'ensemble des métiers", "Run stabilisé, FinOps de l'IA",
                   "Revue de conformité annuelle", "Renégociation des fournisseurs à l'échelle"],
     "entree": "Vague 1 en production ; run mesuré.",
     "sortie": "Objectifs du plan stratégique tenus ou révisés, avec leurs mesures.",
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
     "source": "omnibus_analyse", "porte": "Notation de crédit, solvabilité, tarification vie et santé, "
                                          "composants de sécurité d'infrastructures : dossiers à jour avant cette date."},
    {"date": "2028-08-02", "texte": "Systèmes à haut risque de l'annexe I — date reportée par le règlement (UE) 2026/1744",
     "source": "omnibus_analyse", "porte": "IA intégrée à des produits couverts par la législation "
                                          "d'harmonisation : machines, dispositifs médicaux, véhicules."},
]


# LES QUATRE ÉTATS D'UN JALON, ET LE QUATRIÈME EST UNE CORRECTION.
#
# LE DÉFAUT. La page forçait `avant_fin_projet: true` au chargement, avant tout
# chiffrage : la colonne « État » annonçait donc « tombe pendant le projet »
# pour des dates que PERSONNE n'avait comparées à une fin de projet — il n'y en
# avait pas encore. Une affirmation là où il n'y a pas de mesure, sur la seule
# colonne que le lecteur regarde pour savoir ce qui le concerne.
#
# « en attente » dit ce qui est vrai avant le chiffrage : la date est à venir,
# et sa place dans le calendrier se décidera quand il y aura un calendrier.
#
# LES LIBELLÉS VIVENT ICI, pas dans le script : ils servent à la fois de texte
# de colonne et d'intitulé de groupe dans le menu. Recopiés, les deux
# dériveraient — et le menu proposerait un groupe que la table ne nomme plus.
ETATS_JALON = [
    {"cle": "vigueur", "nom": "En vigueur"},
    {"cle": "pendant", "nom": "Tombe pendant le projet"},
    {"cle": "apres", "nom": "Après le projet"},
    {"cle": "attente", "nom": "À venir — replacé au chiffrage"},
]


def etat_jalon(jalon):
    """L'état d'un jalon, calculé ICI et pas dans deux endroits.

    Il était calculé par une expression conditionnelle dans le script, et par
    `planning()` côté serveur : deux arithmétiques pour une même colonne."""
    if jalon.get("passe"):
        return "vigueur"
    avant = jalon.get("avant_fin_projet")
    if avant is None:
        return "attente"
    return "pendant" if avant else "apres"

def jalons_pour(secteur):
    """Les jalons communs et ceux du secteur, fondus et triés par date."""
    j = list(JALONS_REGLEMENTAIRES)
    if secteur in SECTEURS:
        j += SECTEURS[secteur]["jalons"]
    return sorted(j, key=lambda x: x["date"])


def planning(quantites, debut=None, secteur=None):
    q = {k: _nombre(v) for k, v in (quantites or {}).items()}
    secteur = secteur if secteur in SECTEURS else None
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
                    "activites": ph["activites"], "entree": ph["entree"], "sortie": ph["sortie"],
                    "livrables": ph["livrables"], "jalon": ph["jalon"]})
    migration = None
    if (q.get("n_si_source") or 1) > 1:
        migration = dict(MIGRATION, debut=d0.isoformat(),
                         fin_tot=(d0 + timedelta(days=int(MIGRATION["mois_min"] * 30.44))).isoformat(),
                         fin_tard=(d0 + timedelta(days=int(MIGRATION["mois_max"] * 30.44))).isoformat())
    fin_projet_tard = cur_max
    regl = []
    for j in jalons_pour(secteur):
        dj = date.fromisoformat(j["date"])
        regl.append(dict(j, passe=dj <= d0, avant_fin_projet=dj <= fin_projet_tard,
                         nature="reglementaire"))
    return {"debut": d0.isoformat(), "secteur": secteur, "phases": out,
            "fin_projet": {"tot": cur_min.isoformat(), "tard": cur_max.isoformat()},
            "migration": migration, "jalons_reglementaires": regl,
            "dit": "Les phases sont des durées d'usage, à ±50 %. Les jalons réglementaires sont des "
                   "dates de textes : ils tombent où ils tombent, projet en retard ou non."}


# ═══════════════════════════════════════════════════════════════════════════
#  7. LE CHANGEMENT ET LA MIGRATION — ce qui se décide
# ═══════════════════════════════════════════════════════════════════════════

LEVIERS_CHANGEMENT = [
    {"cle": "accord_social", "nom": "Un accord social dédié, signé avant le déploiement",
     "ancrage": "casA_accord_social", "publics": "Direction, représentants du personnel, DRH",
     "mesure": "Accord signé et daté ; clauses sur l'IA nommées.",
     "dit": "Le cas A a intégré un volet IA à son accord triennal sur les emplois et les parcours, "
            "signé à l'unanimité des organisations représentatives. Un déploiement sans cadre "
            "négocié se paie en adoption — et en contentieux."},
    {"cle": "formation_socle", "nom": "Un socle de formation pour tous, puis des parcours par métier",
     "ancrage": "casA_formes", "publics": "Tous les salariés, puis chaque métier",
     "mesure": "Part de salariés formés ; heures par salarié ; évaluation à froid.",
     "dit": "Environ 45 000 formés sur 100 000 dans le cas A au moment où l'usage quotidien atteint "
            "un salarié sur deux. La corrélation n'est pas une causalité ; l'ordre, lui, est clair."},
    {"cle": "mesure_adoption", "nom": "Une mesure d'adoption publiée, pas un objectif affiché",
     "ancrage": "casA_usage_quotidien", "publics": "Comité IA, management",
     "mesure": "Part d'utilisateurs quotidiens ET sollicitations par utilisateur et par mois.",
     "dit": "« 40 sollicitations par mois et par utilisateur » est une mesure ; « 50 % d'utilisateurs » "
            "en est une autre. Fixez les deux, et publiez-les en interne à cadence fixe."},
    {"cle": "ambassadeurs", "nom": "Un relais par métier, formé avant les autres",
     "ancrage": None, "publics": "Un référent par ligne métier",
     "mesure": "Référents nommés et formés avant le premier pilote de leur métier.",
     "dit": "La ressource rare n'est ni le data scientist ni le processeur graphique : c'est la "
            "personne qui connaît le métier ET l'outil. Elle se forme, elle ne se recrute pas."},
    {"cle": "article_4", "nom": "La maîtrise de l'IA (article 4) comme obligation de moyens, tracée",
     "ancrage": "omnibus_analyse", "publics": "Tous les utilisateurs de systèmes d'IA",
     "mesure": "Registre des actions de formation, par population et par système.",
     "dit": "Le règlement 2026/1744 reformule l'article 4 en obligation de prendre des mesures : "
            "moins exigeant sur le résultat, toujours contraignant sur la trace."},
]

# CE QUI SOUTIENT UN LEVIER — l'axe que le chapô de la page promettait déjà.
#
# « Chacun avec son public, sa mesure, et l'ancrage public qui le soutient — ou
# la mention qu'il s'agit d'une convention du cabinet » : la page l'annonçait,
# et rien ne permettait de trier là-dessus. C'est pourtant la seule question
# qui décide de ce qu'un levier vaut dans une discussion : est-ce que je peux
# le montrer, ou est-ce que je dois l'assumer ?
#
# LE CALCUL VIT ICI, PAS DANS LE SCRIPT. Le script décidait déjà de la mention
# affichée par une cascade — ancrage, puis source, puis « convention » ; le
# menu aurait fait une seconde cascade, et deux cascades pour un même verdict
# divergent. `soutien_levier` est désormais la seule.
SOUTIENS_LEVIER = [
    {"cle": "ancre", "nom": "Adossé à une source publique"},
    {"cle": "convention", "nom": "Convention du cabinet, à discuter"},
]


def soutien_levier(levier):
    """« ancre » si le levier désigne un ancrage OU une source qui existe ;
    « convention » sinon. La cascade est celle que la page applique déjà pour
    choisir la mention qu'elle affiche."""
    cle = levier.get("ancrage")
    if not cle:
        return "convention"
    if any(a["cle"] == cle for a in ANCRAGES) or cle in SOURCES:
        return "ancre"
    return "convention"


def _verifier_soutiens():
    """UN LEVIER QUI DÉSIGNE UN ANCRAGE ABSENT SE DIRAIT « ADOSSÉ » sans
    l'être : il ressortirait dans le groupe des leviers montrables, et la page
    afficherait « convention du cabinet » juste en dessous. Deux verdicts
    contraires sur la même ligne."""
    connus = {a["cle"] for a in ANCRAGES} | set(SOURCES)
    for liste, nom in ((LEVIERS_CHANGEMENT, "levier"), (PRINCIPES_MIGRATION, "principe")):
        for l in liste:
            cle = l.get("ancrage")
            if cle and cle not in connus:
                raise ValueError("le %s « %s » désigne un ancrage absent : %r"
                                 % (nom, l["nom"], cle))

PRINCIPES_MIGRATION = [
    {"cle": "pas_de_big_bang", "nom": "Pas de bascule unique", "ancrage": "casD_revue",
     "geste": "Découper la bascule par périmètre et par population ; répéter la répétition générale.",
     "dit": "Le cas D : une bascule en un événement, une recette insuffisante, 232 jours de "
            "perturbation, plus de 330 M£. La revue indépendante nomme la méthode, pas la malchance."},
    {"cle": "interfaces_deux_fois", "nom": "Compter chaque interface deux fois", "ancrage": "migration_benchmarks",
     "geste": "Lister les interfaces qui vivront vers l'ancien ET le nouveau socle ; les chiffrer deux fois.",
     "dit": "Pendant une migration de cœur, l'usine IA consomme l'ancien socle ET le nouveau. "
            "Le poste existe dans ce module ; il n'existe dans aucun ratio."},
    {"cle": "gel", "nom": "Un gel des évolutions IA autour de la bascule, daté", "ancrage": None,
     "geste": "Fixer les dates de gel au planning, les communiquer aux métiers, prévoir le rattrapage.",
     "dit": "Une semaine de gel coûte des jours ; une régression sur un cas en production pendant "
            "la bascule coûte la confiance. Le gel se planifie, il ne se subit pas."},
    {"cle": "provision", "nom": "Une provision alignée sur le dépassement documenté", "ancrage": "migration_depassement",
     "geste": "Saisir une provision et lire l'alerte du chiffrage si elle est inférieure au documenté.",
     "dit": "Les remplacements de cœur dépassent souvent de 50 % et plus. Ce module ne propose "
            "pas de taux ; il signale quand le vôtre est inférieur à ce chiffre."},
]


_verifier_soutiens()   # refuse au chargement, pas à l'affichage


def comparables():
    """LES CAS COMPARABLES — pour situer, pas pour caler.

    ILS VENAIENT TOUS DE LA BANQUE, ET C'ÉTAIT LE DÉFAUT. Quatre cas, un seul
    secteur : un assureur, une société de gestion ou un établissement de santé
    lisait quatre banques en se demandant ce qu'il devait en retenir. « Situer »
    suppose un repère dans SON activité, sinon la comparaison se fait au hasard
    — ou ne se fait pas.

    CHAQUE SECTEUR DU MODULE A DÉSORMAIS LE REPÈRE DE SON AUTORITÉ, mesuré sur
    son périmètre : le superviseur bancaire pour la banque, l'autorité des
    assurances pour l'assurance, celle des marchés pour la gestion, et l'état
    de préparation des systèmes de santé pour les entités essentielles. S'y
    ajoutent un cas d'entreprise hors banque, un contre-exemple pris dans
    l'administration publique, et l'écart entre activités — qui est le repère
    le plus utile de tous.

    CHAQUE CAS PORTE SON SECTEUR, et la page s'en sert pour les ranger. Un cas
    dont le secteur ne serait pas un secteur du module ne se rangerait nulle
    part : `secteurs_comparables()` le refuse."""
    idx = {a["cle"]: a for a in ANCRAGES}
    def a(cle):
        x = idx[cle]
        return {"nom": x["nom"], "min": x["min"], "max": x["max"], "unite": x["unite"],
                "source": x["source"], "ne_dit_pas": x["ne_dit_pas"]}
    return [
        {"secteur": "banque",
         "organisation": "Cas A — grand groupe bancaire coopératif : deux réseaux, deux systèmes d'information, une usine IA",
         "chiffres": [a("casA_budget"), a("casA_horizon"), a("casA_effectif"),
                      a("casA_usage_quotidien"), a("casA_appels"), a("casA_formes")],
         "lecon": "Un socle commun décidé pour porter l'IA ; l'adoption a précédé le socle. "
                  "La migration des deux SI est le risque dominant, pas l'IA."},
        {"secteur": "banque",
         "organisation": "Cas B — grand groupe bancaire universel : plan IA triennal et entité IA mutualisée",
         "chiffres": [a("casB_plan"), a("casB_entite_ia"), a("casB_entite_ia_etp")],
         "lecon": "Le seul cas français qui publie à la fois un budget de socle et un effectif "
                  "de socle : le ratio le plus proche d'une usine IA de groupe."},
        {"secteur": "banque",
         "organisation": "Cas C — deux banques universelles : objectifs de valeur et comptes de cas d'usage",
         "chiffres": [a("casC_valeur"), a("casC_cas")],
         "lecon": "Des objectifs de valeur et des comptes de cas d'usage — sans définition publiée "
                  "de l'un ni de l'autre. À citer, pas à recopier."},
        {"secteur": "banque",
         "organisation": "Cas D — banque de détail : la migration manquée de 2018",
         "chiffres": [a("casD_cout"), a("casD_duree")],
         "lecon": "Le contre-exemple documenté par une revue indépendante : bascule unique, "
                  "recette insuffisante, gouvernance."},
        {"secteur": "assurance",
         "organisation": "Cas E — assureur composite européen : une plateforme d'IA générative interne, et le recensement des cas",
         "chiffres": [a("assur_cas_utilisateurs"), a("assur_cas_effectif"), a("assur_cas_usages"),
                      a("assur_non_vie"), a("assur_vie")],
         "lecon": "Neuf cents cas d'usage RECENSÉS, et aucune part publiée de ce qui tourne "
                  "réellement : le compte de cas d'usage est un indicateur d'activité, pas de "
                  "valeur. Le repère de secteur est plus sobre — la moitié des assureurs non-vie, "
                  "un quart des assureurs vie, et l'écart entre les deux tient à la nature du "
                  "risque tarifé, pas à la maturité technique."},
        {"secteur": "marches",
         "organisation": "Cas F — marchés et gestion d'actifs : ce que déclare le secteur à son autorité",
         "chiffres": [a("marches_en_prod"), a("marches_experimentent"),
                      a("marches_sans_investissement")],
         "lecon": "LE SEUL SECTEUR QUI PUBLIE SON TAUX D'ABSTENTION : plus d'un tiers des acteurs "
                  "n'a rien investi dans l'IA en 2024. Un chiffre qu'aucune communication "
                  "d'entreprise ne donnera jamais, et qui replace les annonces des autres cas."},
        {"secteur": "nis2",
         "organisation": "Cas G — systèmes de santé des vingt-sept États membres : l'IA déjà en service, la gouvernance en retard",
         "chiffres": [a("sante_diagnostic"), a("sante_agents"), a("sante_postes_dedies"),
                      a("sante_reponses")],
         "lecon": "Trois pays sur quatre emploient l'IA en aide au diagnostic, deux sur trois des "
                  "agents conversationnels — mais seulement la moitié a créé les postes qui les "
                  "tiennent. L'écart entre l'usage et la fonction qui en répond est le risque "
                  "propre aux entités essentielles."},
        {"secteur": "nis2",
         "organisation": "Cas H — administration fiscale : un profilage de risque auto-apprenant, et sa sanction",
         "chiffres": [a("public_familles"), a("public_amende"), a("public_double_nationalite")],
         "lecon": "LE CONTRE-EXEMPLE QUI N'EST PAS UNE PANNE INFORMATIQUE. Rien n'est tombé : le "
                  "système a fonctionné comme il avait été conçu, avec la nationalité pour "
                  "indicateur de risque et sans réexamen humain utile. C'est exactement ce que le "
                  "règlement sur l'IA classe en haut risque — et le coût pour les familles est "
                  "sans commune mesure avec l'amende."},
        {"secteur": "tous",
         "organisation": "Repère inter-sectoriel : l'écart entre activités, qui situe mieux qu'une moyenne",
         "chiffres": [a("ue_entreprises_2025"), a("ue_secteur_haut"), a("ue_secteur_bas")],
         "lecon": "Une entreprise européenne sur cinq emploie l'IA — mais près de deux sur trois "
                  "dans l'information et la communication contre une sur dix dans la construction. "
                  "Se comparer à la moyenne n'apprend rien ; se comparer à SON activité, si."},
    ]


SECTEUR_TOUS = "tous"


def secteurs_comparables():
    """Les secteurs présents dans les cas, dans l'ordre des secteurs du module.

    ET LE CONTRÔLE QUI VA AVEC : un cas dont le secteur n'existe pas ne se
    rangerait dans aucun groupe du menu — il disparaîtrait de la page sans que
    rien ne le signale. On refuse au chargement plutôt que de le perdre."""
    connus = set(SECTEURS) | {SECTEUR_TOUS}
    inconnus = sorted({c["secteur"] for c in comparables()} - connus)
    if inconnus:
        raise ValueError("cas comparables rattachés à un secteur inconnu : %s" % inconnus)
    presents = {c["secteur"] for c in comparables()}
    ordre = [k for k in SECTEURS if k in presents]
    if SECTEUR_TOUS in presents:
        ordre.append(SECTEUR_TOUS)
    return ordre


def nom_secteur_comparable(cle):
    """Le libellé d'un secteur pour le menu des cas."""
    if cle == SECTEUR_TOUS:
        return "Tous secteurs"
    return SECTEURS[cle]["nom"]


secteurs_comparables()   # refuse au chargement, pas à l'affichage

# ═══════════════════════════════════════════════════════════════════════════
#  8. LE PARCOURS GUIDÉ — par rôle, vers les sections de la page
# ═══════════════════════════════════════════════════════════════════════════
#
# Les rôles vivent ICI, pas dans la page : c'est ce que fait déjà l'ingénierie
# Data Center. Une étape vise une SECTION de la page par son identifiant ; une
# règle vérifie que chaque section visée existe.

PARCOURS = [
    {"id": "dg", "nom": "Direction générale, comité exécutif",
     "vient_pour": "Décider d'engager, et savoir ce que l'étude ne dit pas.",
     "etapes": [
         {"section": "s-ancrages", "faire": "Lisez les cas comparables et, pour chaque chiffre, ce qu'il ne dit pas.",
          "obtenir": "L'ordre de grandeur, sans le prendre pour une estimation."},
         {"section": "s-chiffrage", "faire": "Regardez d'abord la part non chiffrée, puis le sous-total.",
          "obtenir": "Le degré de confiance réel du chiffrage."},
         {"section": "s-planning", "faire": "Repérez les jalons réglementaires qui tombent pendant le projet.",
          "obtenir": "Les dates qui ne se négocient pas."},
         {"section": "s-offre", "faire": "Parcourez les sept lots et ce que chacun consomme.",
          "obtenir": "Ce que vous achetez, dans l'ordre du projet."}]},
    {"id": "dsi", "nom": "DSI, directeur de programme",
     "vient_pour": "Dimensionner le socle et tenir la migration.",
     "etapes": [
         {"section": "s-secteur", "faire": "Choisissez le secteur : il ajoute ses postes et ses jalons.",
          "obtenir": "Une structure complète, pas une structure générique."},
         {"section": "s-saisie", "faire": "Renseignez systèmes à unifier, interfaces, cas d'usage, effectif par cas.",
          "obtenir": "Les entrées qui commandent le socle et la migration."},
         {"section": "s-chiffrage", "faire": "Lisez les groupes socle, usine et migration, et le dimensionnement.",
          "obtenir": "L'équipe centrale en fourchette, les interfaces comptées deux fois s'il y a migration."},
         {"section": "s-migration", "faire": "Confrontez votre plan de bascule aux quatre principes.",
          "obtenir": "Ce qui fait déraper, nommé avant de dérape."},
         {"section": "s-planning", "faire": "Posez la date de début et lisez le calendrier.",
          "obtenir": "Fin au plus tôt, au plus tard, et la migration en parallèle."}]},
    {"id": "metier", "nom": "Directeur métier",
     "vient_pour": "Savoir quels cas d'usage engager, et ce qu'ils exigent.",
     "etapes": [
         {"section": "s-secteur", "faire": "Lisez les cas d'usage typiques du secteur et leur classe.",
          "obtenir": "Ce qui relève de l'annexe III, ce qui se qualifie, ce qui est minimal."},
         {"section": "s-saisie", "faire": "Renseignez cas d'usage, jours par cas et effectif par cas sur vos pilotes réels.",
          "obtenir": "Un chiffrage assis sur ce que vous avez déjà mesuré."},
         {"section": "s-changement", "faire": "Parcourez les cinq leviers et leurs mesures.",
          "obtenir": "Ce que l'adoption demande à votre métier."},
         {"section": "s-chiffrage", "faire": "Lisez le groupe des cas d'usage et celui du changement.",
          "obtenir": "Le coût de votre périmètre, et ce qui n'est pas encore chiffré."}]},
    {"id": "daf", "nom": "Direction financière, contrôle de gestion",
     "vient_pour": "Chiffrer sans se faire raconter d'histoire.",
     "etapes": [
         {"section": "s-saisie", "faire": "Renseignez les prix unitaires depuis vos grilles et devis.",
          "obtenir": "Un chiffrage sur VOS prix, pas sur un ratio."},
         {"section": "s-chiffrage", "faire": "Saisissez une provision et lisez l'alerte si elle est sous le dépassement documenté.",
          "obtenir": "Une provision confrontée à un chiffre sourcé."},
         {"section": "s-ancrages", "faire": "Pour chaque ancrage, lisez ce qu'il ne dit pas avant de le citer.",
          "obtenir": "Des ordres de grandeur utilisables en comité, avec leur réserve."}]},
    {"id": "risques", "nom": "RSSI, conformité, gestion des risques",
     "vient_pour": "Tenir les textes et leurs dates.",
     "etapes": [
         {"section": "s-secteur", "faire": "Lisez les textes du secteur, ses autorités et ses jalons propres.",
          "obtenir": "Le corpus qui s'applique à vous, avec ses adresses."},
         {"section": "s-conformite", "faire": "Lisez ce que l'étude retient de chaque texte.",
          "obtenir": "Les obligations qui commandent le calendrier."},
         {"section": "s-planning", "faire": "Repérez les jalons passés, ceux qui tombent pendant le projet.",
          "obtenir": "Ce qui est déjà exigible."},
         {"section": "s-sources", "faire": "Rouvrez les sources : aucune n'a été lue depuis ce poste.",
          "obtenir": "La vérification qui vous appartient."}]},
    {"id": "drh", "nom": "Direction des ressources humaines",
     "vient_pour": "Former, négocier, mesurer l'adoption.",
     "etapes": [
         {"section": "s-changement", "faire": "Lisez les cinq leviers, leurs publics et leurs mesures.",
          "obtenir": "Un plan de conduite du changement avec ses indicateurs."},
         {"section": "s-saisie", "faire": "Renseignez effectif, part à former, heures par salarié.",
          "obtenir": "Le poste formation, chiffré sur votre coût horaire."},
         {"section": "s-chiffrage", "faire": "Lisez le groupe conduite du changement.",
          "obtenir": "Ce que la formation et le réseau d'ambassadeurs coûtent."}]},
]


# ═══════════════════════════════════════════════════════════════════════════
#  9. LES DIX BLOCS — et ce qui fait passer chacun du bleu au vert
# ═══════════════════════════════════════════════════════════════════════════
#
# UN BLOC QUI VERDIT SANS QUE RIEN NE SE SOIT PASSÉ EST UN MENSONGE VISUEL,
# et c'est le piège de tout indicateur d'avancement. Deux natures de bloc,
# donc, et elles ne se valident pas de la même façon :
#
#   · `mesure` — la page CONSTATE. Un secteur choisi, des entrées
#     renseignées, un chiffrage sans poste manquant, un calendrier construit.
#     Le vert dit un fait vérifiable, et il repart au bleu si le fait cesse.
#
#   · `lecture` — la page ne peut RIEN constater. Personne ne sait si un
#     lecteur a lu. Le vert est alors une DÉCLARATION du lecteur, obtenue par
#     une case à cocher, et le libellé le dit : « J'ai lu ». Faire verdir un
#     bloc au défilement prétendrait mesurer une lecture ; ce serait faux, et
#     faux de la pire façon — de façon crédible.
#
# `critere` est le texte affiché : le lecteur doit savoir ce qui reste à
# faire pour passer au vert, sinon l'indicateur informe sans instruire.

SECTIONS = [
    {"id": "s-secteur", "numero": 1, "nom": "Votre secteur", "nature": "mesure",
     "critere": "Choisissez un secteur : il ajoute ses postes, ses jalons et ses cas d'usage.",
     "aide": "Sans secteur, l'étude reste générique — elle ignore le registre des prestataires "
             "TIC, la validation actuarielle ou le dossier de sûreté selon le cas."},
    {"id": "s-ancrages", "numero": 2, "nom": "Les cas comparables", "nature": "lecture",
     "critere": "Lisez les quatre cas et, pour chaque chiffre, ce qu'il ne dit pas.",
     "aide": "Ces ordres de grandeur situent une étude ; aucun n'est une estimation pour la "
             "vôtre. Les citer sans leur réserve serait les transformer en promesse."},
    {"id": "s-saisie", "numero": 3, "nom": "Vos quantités, vos prix", "nature": "mesure",
     "critere": "Renseignez toutes les quantités attendues et tous les prix unitaires.",
     "aide": "Chaque entrée dit où la trouver. Une entrée qu'on ne sait pas où chercher est "
             "une entrée qui sera inventée."},
    {"id": "s-chiffrage", "numero": 4, "nom": "Le chiffrage", "nature": "mesure",
     "critere": "Lancez le chiffrage, et n'ayez plus aucun poste non chiffré.",
     "aide": "Un poste sans prix n'est pas compté à zéro : il ressort « non chiffré » avec sa "
             "raison. Le bloc reste bleu tant qu'il en reste un."},
    {"id": "s-planning", "numero": 5, "nom": "Le planning et ses jalons", "nature": "mesure",
     "critere": "Le calendrier se construit au chiffrage, à partir de la date de début.",
     "aide": "Les phases glissent avec le projet ; les jalons réglementaires, non. C'est "
             "pourquoi ils ne sont pas dans la même liste."},
    {"id": "s-changement", "numero": 6, "nom": "La conduite du changement", "nature": "lecture",
     "critere": "Prenez connaissance des cinq leviers, de leur public et de leur mesure.",
     "aide": "La ressource rare est la personne qui connaît le métier ET l'outil. Elle se "
             "forme, elle ne se recrute pas."},
    {"id": "s-migration", "numero": 7, "nom": "La migration des systèmes", "nature": "lecture",
     "critere": "Confrontez votre plan de bascule aux quatre principes.",
     "aide": "Une usine IA adossée à une migration de cœur hérite de l'aléa de la migration. "
             "Le contre-exemple est documenté par une revue indépendante."},
    {"id": "s-conformite", "numero": 8, "nom": "La conformité", "nature": "lecture",
     "critere": "Prenez connaissance des textes qui commandent votre calendrier.",
     "aide": "La qualification d'un système se fait dossier par dossier, dès le cadrage. Ce "
             "module ne qualifie rien : c'est une analyse juridique."},
    {"id": "s-offre", "numero": 9, "nom": "Les sept lots", "nature": "lecture",
     "critere": "Parcourez les lots et ce que chacun consomme dans le chiffrage.",
     "aide": "Aucun prix dans ce tableau : les jours se saisissent au bloc 3, sur votre grille."},
    {"id": "s-sources", "numero": 10, "nom": "Les sources", "nature": "lecture",
     "critere": "Rouvrez les sources : aucune n'a été lue depuis le poste qui a bâti ce module.",
     "aide": "Une source qu'on ne peut pas rouvrir est une intention, pas une source. Le "
             "registre compte les adresses joignables au lieu de lisser."},
]


def etat_blocs(quantites, prix, secteur=None, chiffrage=None):
    """L'état des blocs que la page peut CONSTATER — les autres se déclarent.

    Rendu au serveur plutôt que calculé dans la page : le critère de validation
    d'un bloc est une décision, et une décision recopiée dans un script dérive
    de celle du module au premier poste ajouté."""
    q = {k: _nombre(v) for k, v in (quantites or {}).items()}
    p = {k: _nombre(v) for k, v in (prix or {}).items()}
    secteur = secteur if secteur in SECTEURS else None
    attendues = quantites_pour(secteur)
    manquantes = ([k for k in attendues if q.get(k) is None]
                  + [k for k in PRIX if p.get(k) is None])
    out = {}
    for sec in SECTIONS:
        if sec["nature"] != "mesure":
            out[sec["id"]] = {"nature": "lecture", "valide": None,
                              "dit": "À déclarer lu : la page ne peut pas constater une lecture."}
            continue
        if sec["id"] == "s-secteur":
            ok = secteur is not None
            dit = ("Secteur retenu." if ok else "Aucun secteur choisi.")
        elif sec["id"] == "s-saisie":
            ok = not manquantes
            dit = ("Toutes les entrées sont renseignées." if ok
                   else "%d entrée(s) manquante(s) sur %d."
                        % (len(manquantes), len(attendues) + len(PRIX)))
            # UNE ENTRÉE RENSEIGNÉE N'EST PAS UNE ENTRÉE À VOUS. Le bloc reste
            # vert — une valeur peut coïncider avec un exemple parce que c'est
            # la bonne — mais il le DIT, sinon l'étude exportée présenterait les
            # ordres de grandeur du cabinet comme les chiffres du client.
            a_remplacer = [x for x in valeurs_dexemple(quantites, prix) if x["a_remplacer"]]
            if a_remplacer:
                dit += (" %d valeur(s) sont encore un ordre de grandeur du cabinet, "
                        "à remplacer par les vôtres." % len(a_remplacer))
        elif sec["id"] == "s-chiffrage":
            ok = bool(chiffrage) and chiffrage.get("n_non_chiffres") == 0
            dit = ("Tous les postes sont chiffrés." if ok
                   else ("%d poste(s) non chiffré(s)." % chiffrage["n_non_chiffres"]
                         if chiffrage else "Chiffrage pas encore lancé."))
        elif sec["id"] == "s-planning":
            ok = bool(chiffrage)
            dit = ("Calendrier construit." if ok else "Le calendrier se construit au chiffrage.")
        else:
            ok, dit = False, ""
        out[sec["id"]] = {"nature": "mesure", "valide": bool(ok), "dit": dit}
    return out


def referentiel():
    """Tout ce que la page affiche. Rien n'est recopié dans la page."""
    return {"version": VERSION,
            "quantites": QUANTITES, "quantites_secteur": QUANTITES_SECTEUR, "prix": PRIX,
            "groupes": GROUPES,
            "postes": [{k: v for k, v in p.items() if k != "calc"} for p in POSTES],
            "postes_secteur": [{k: v for k, v in p.items() if k != "calc"} for p in POSTES_SECTEUR],
            "secteurs": SECTEURS, "classes_cas": CLASSES_CAS,
            "ancrages": ANCRAGES, "sources": SOURCES,
            # LES EXEMPLES VIENNENT D'ICI, comme tout le reste. Recopiés dans le
            # script, ils deviendraient un second barème — et c'est le plus
            # visible qui serait cru.
            "exemples": EXEMPLES, "provenances": PROVENANCES,
            "couverture_sources": couverture_sources(),
            "phases": PHASES, "migration": MIGRATION,
            "jalons_reglementaires": JALONS_REGLEMENTAIRES,
            "etats_jalon": ETATS_JALON,
            "leviers_changement": LEVIERS_CHANGEMENT,
            "soutiens_levier": SOUTIENS_LEVIER,
            "principes_migration": PRINCIPES_MIGRATION,
            "comparables": comparables(),
            # L'ORDRE ET LES LIBELLÉS DES GROUPES VIENNENT D'ICI. Recopiés dans le
            # script, ils divergeraient le jour où un secteur entre au module — et
            # c'est le menu, le plus visible, qui serait cru.
            "secteurs_comparables": [{"cle": k, "nom": nom_secteur_comparable(k)}
                                     for k in secteurs_comparables()],
            "parcours": PARCOURS, "sections": SECTIONS,
            "limite": "Ce module ne porte aucun prix : il chiffre les vôtres. Ses ancrages "
                      "situent ; ils n'estiment pas. Ses sources ont été obtenues, pas lues. Il ne "
                      "nomme ni entreprise ni personne ; ses adresses nomment nécessairement des sites."}


def sante():
    return {"module": "ia_factory", "version": VERSION,
            "postes": len(POSTES), "postes_secteur": len(POSTES_SECTEUR),
            "secteurs": len(SECTEURS), "ancrages": len(ANCRAGES),
            "sources": len(SOURCES), "phases": len(PHASES),
            "jalons_reglementaires": len(JALONS_REGLEMENTAIRES), "roles": len(PARCOURS),
            "sections": len(SECTIONS)}
