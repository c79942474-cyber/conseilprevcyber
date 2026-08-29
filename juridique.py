"""Conseil juridique assisté — services numériques, cybersécurité IT/OT/ICS et IA.

Module PARTAGÉ à l'identique par les deux sites (conseilprev et conseilprevcyber).
Il ne dépend que de la bibliothèque standard : aucune base, aucun appel réseau,
aucun service payant. C'est délibéré — il doit pouvoir être importé par n'importe
laquelle des deux applications et testé sans infrastructure.

── Pourquoi ce découpage ──────────────────────────────────────────────────────
Un assistant juridique qui se contente d'interroger un LLM produit des réponses
plausibles et invérifiables : c'est exactement ce qu'il ne faut pas en matière
réglementaire, où une référence d'article erronée décrédibilise tout le reste.
Le module sépare donc trois choses de nature différente :

  1. CE QUI EST CERTAIN — le référentiel des textes (numéro, CELEX, dates
     d'application, autorité). Données figées, vérifiables, jamais générées.
  2. CE QUI SE DÉDUIT — la qualification : quels textes s'appliquent à un profil
     donné. Règles explicites en Python, exécutées sans IA, avec la MOTIVATION de
     chaque rattachement. Deux exécutions sur le même profil donnent le même
     résultat, et ce résultat s'explique ligne à ligne devant un client.
  3. CE QUI S'INTERPRÈTE — l'analyse. Là seulement intervient le modèle de
     langage, cadré par un prompt qui lui impose de présenter PLUSIEURS lectures
     possibles du texte, de les rattacher à leurs conséquences pratiques, et de
     ne citer que des références figurant dans le référentiel ou dans les
     extraits fournis. Un contrôle a posteriori (`verifier_citations`) détecte
     les références inventées avant affichage.

── Cadre professionnel ────────────────────────────────────────────────────────
La loi n° 71-1130 du 31 décembre 1971 (art. 54 s.) réserve la consultation
juridique à titre habituel et rémunéré aux professions qu'elle énumère. Les
sorties de ce module sont donc construites comme une ANALYSE DOCUMENTAIRE
argumentée — état des textes, lectures possibles, risques, options — et non
comme un avis juridique se substituant à un avocat. L'avertissement est repris
automatiquement dans chaque réponse (voir AVERTISSEMENT), et l'origine
artificielle de la production est signalée conformément à l'article 50 du
Règlement (UE) 2024/1689.
"""

import functools
import re
import unicodedata

# LE CONNECTEUR DE JURISPRUDENCE, S'IL EST LÀ. Ce module est partagé à
# l'identique entre deux applications et sert aussi de brique isolée : il doit
# rester importable sans lui. Son absence n'est pas une dégradation silencieuse
# — elle ramène simplement au comportement antérieur, où AUCUNE décision ne
# pouvait être citée. L'import ne joint rien : `librejustice` n'ouvre une
# connexion que lorsqu'on l'interroge.
try:
    import librejustice
except ImportError:  # pragma: no cover — dépend du déploiement, pas du code
    librejustice = None

# Version du corpus de référence : à incrémenter à chaque mise à jour des textes.
# Elle est affichée dans les analyses — un client doit pouvoir savoir sur quel
# état du droit une note a été produite.
VERSION_REFERENTIEL = "2026.07"

EURLEX = "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:%s"
# Légifrance : les identifiants internes (LEGITEXT/JORFTEXT) ne sont pas
# devinables sans risque d'erreur. On pointe donc sur la recherche par intitulé,
# qui ne renvoie jamais vers un texte faux.
LEGIFRANCE = "https://www.legifrance.gouv.fr/search/all?tab_selection=all&query=%s"


# ═══════════════════════════════════════════════════════════════════════════
# 1. RÉFÉRENTIEL DES TEXTES — données figées, jamais générées
# ═══════════════════════════════════════════════════════════════════════════
#
# Champs :
#   id          — clé stable utilisée par les règles de qualification
#   titre       — intitulé court d'usage
#   officiel    — intitulé permettant de retrouver le texte sans ambiguïté
#   nature      — reglement | directive | loi | code | norme | referentiel
#   celex       — identifiant EUR-Lex (textes UE) ; construit l'URL officielle
#   domaines    — axes couverts : numerique, cyber, ia, ot, donnees, contrats
#   jalons      — dates d'application connues, en clair
#   autorite    — qui contrôle / sanctionne
#   portee      — à qui le texte s'adresse, en une phrase
#   a_verifier  — True quand l'état du texte bouge (transposition en cours…)
REFERENTIEL = [
    # ── Intelligence artificielle ─────────────────────────────────────────
    {
        "id": "ai-act",
        "titre": "IA Act",
        "officiel": "Règlement (UE) 2024/1689 établissant des règles harmonisées "
                    "concernant l'intelligence artificielle",
        "nature": "reglement", "celex": "32024R1689",
        "domaines": ["ia", "numerique"],
        "jalons": [
            "1er août 2024 — entrée en vigueur",
            "2 février 2025 — pratiques interdites (art. 5) et littératie en IA (art. 4)",
            "2 août 2025 — modèles à usage général (chap. V), gouvernance, sanctions",
            "2 août 2026 — application générale, dont l'art. 50 (transparence)",
            "2 décembre 2027 — systèmes à haut risque de l'annexe III "
            "(date fixée par le Digital Omnibus)",
            "2 août 2028 — systèmes à haut risque relevant de l'art. 6(1) "
            "(IA composant de sécurité d'un produit réglementé, annexe I)",
        ],
        "autorite": "Bureau de l'IA (Commission) ; en France, autorités de "
                    "surveillance du marché à désigner",
        "portee": "Fournisseurs, déployeurs, importateurs, distributeurs et "
                  "mandataires de systèmes d'IA mis sur le marché ou utilisés dans l'UE.",
    },
    {
        "id": "iso-42001",
        "titre": "ISO/IEC 42001:2023",
        "officiel": "ISO/IEC 42001:2023 — Système de management de l'intelligence artificielle",
        "nature": "norme", "domaines": ["ia"],
        "jalons": ["Publiée en décembre 2023"],
        "autorite": "Certification par organisme accrédité (volontaire)",
        "portee": "Organisations développant ou utilisant des systèmes d'IA : "
                  "exigences d'un système de management certifiable.",
    },
    {
        "id": "iso-23894",
        "titre": "ISO/IEC 23894:2023",
        "officiel": "ISO/IEC 23894:2023 — Management du risque lié à l'intelligence artificielle",
        "nature": "norme", "domaines": ["ia"],
        "jalons": ["Publiée en février 2023"],
        "autorite": "Référentiel volontaire",
        "portee": "Lignes directrices d'appréciation et de traitement du risque IA, "
                  "articulables avec l'ISO 31000.",
    },
    {
        "id": "nist-ai-rmf",
        "titre": "NIST AI RMF 1.0",
        "officiel": "NIST AI Risk Management Framework 1.0 (janvier 2023)",
        "nature": "referentiel", "domaines": ["ia"],
        "jalons": ["Publié en janvier 2023"],
        "autorite": "Référentiel volontaire (États-Unis), largement repris à l'international",
        "portee": "Cadre de gestion du risque IA en quatre fonctions "
                  "(GOVERN, MAP, MEASURE, MANAGE).",
    },

    # ── Données personnelles ──────────────────────────────────────────────
    {
        "id": "rgpd",
        "titre": "RGPD",
        "officiel": "Règlement (UE) 2016/679 relatif à la protection des personnes "
                    "physiques à l'égard du traitement des données à caractère personnel",
        "nature": "reglement", "celex": "32016R0679",
        "domaines": ["donnees", "numerique"],
        "jalons": ["25 mai 2018 — application"],
        "autorite": "CNIL (France) ; Comité européen de la protection des données",
        "portee": "Responsables de traitement et sous-traitants traitant des "
                  "données personnelles de personnes situées dans l'UE.",
    },
    {
        "id": "loi-78-17",
        "titre": "Loi Informatique et Libertés",
        "officiel": "Loi n° 78-17 du 6 janvier 1978 relative à l'informatique, "
                    "aux fichiers et aux libertés",
        "nature": "loi", "domaines": ["donnees"],
        "jalons": ["Refondue en 2018-2019 pour l'articulation avec le RGPD"],
        "autorite": "CNIL",
        "portee": "Complète le RGPD en droit français (marges nationales, "
                  "traitements régaliens, sanctions).",
    },
    {
        "id": "eprivacy",
        "titre": "Directive ePrivacy",
        "officiel": "Directive 2002/58/CE vie privée et communications électroniques",
        "nature": "directive", "celex": "32002L0058",
        "domaines": ["donnees", "numerique"],
        "jalons": ["Modifiée en 2009 ; en France, art. 82 de la loi 78-17"],
        "autorite": "CNIL",
        "portee": "Traceurs et cookies, communications électroniques, "
                  "prospection — régime distinct du RGPD.",
    },

    # ── Cybersécurité ─────────────────────────────────────────────────────
    {
        "id": "nis2",
        "titre": "NIS 2",
        "officiel": "Directive (UE) 2022/2555 concernant des mesures destinées à "
                    "assurer un niveau élevé commun de cybersécurité dans l'ensemble de l'Union",
        "nature": "directive", "celex": "32022L2555",
        "domaines": ["cyber", "numerique", "ot"],
        "jalons": [
            "16 janvier 2023 — entrée en vigueur",
            "17 octobre 2024 — date limite de transposition par les États membres",
        ],
        "autorite": "ANSSI (autorité nationale désignée en France)",
        "portee": "Entités essentielles et importantes des secteurs des annexes I "
                  "et II, au-delà de seuils de taille — avec des exceptions "
                  "sectorielles indépendantes de la taille.",
    },
    {
        "id": "nis2-fr",
        "titre": "Transposition française de NIS 2",
        "officiel": "Dispositif national de transposition de la directive (UE) 2022/2555 "
                    "(résilience des infrastructures critiques et cybersécurité)",
        "nature": "loi", "domaines": ["cyber"],
        "jalons": ["État d'avancement à vérifier sur Légifrance avant tout engagement"],
        "autorite": "ANSSI",
        "portee": "Détermine en droit français le périmètre exact des entités "
                  "régulées, les délais de déclaration et le régime de sanction.",
        "a_verifier": True,
    },
    {
        "id": "dora",
        "titre": "DORA",
        "officiel": "Règlement (UE) 2022/2554 sur la résilience opérationnelle "
                    "numérique du secteur financier",
        "nature": "reglement", "celex": "32022R2554",
        "domaines": ["cyber", "numerique", "contrats"],
        "jalons": ["17 janvier 2025 — application"],
        "autorite": "ACPR et AMF (France) ; AES au niveau européen",
        "portee": "Entités financières énumérées à l'art. 2 et prestataires tiers "
                  "de services TIC, dont ceux désignés critiques.",
    },
    {
        "id": "dora-directive",
        "titre": "Directive d'accompagnement DORA",
        "officiel": "Directive (UE) 2022/2556 modifiant les directives sectorielles "
                    "financières au titre de la résilience opérationnelle numérique",
        "nature": "directive", "celex": "32022L2556",
        "domaines": ["cyber"],
        "jalons": ["Transposée en parallèle de l'application de DORA"],
        "autorite": "ACPR, AMF",
        "portee": "Aligne les directives financières existantes sur DORA.",
    },
    {
        "id": "cra",
        "titre": "Cyber Resilience Act",
        "officiel": "Règlement (UE) 2024/2847 concernant des exigences horizontales "
                    "de cybersécurité pour les produits comportant des éléments numériques",
        "nature": "reglement", "celex": "32024R2847",
        "domaines": ["cyber", "numerique", "ot"],
        "jalons": [
            "10 décembre 2024 — entrée en vigueur",
            "11 septembre 2026 — obligations de signalement des vulnérabilités "
            "activement exploitées et des incidents graves",
            "11 décembre 2027 — application générale",
        ],
        "autorite": "Autorités de surveillance du marché ; ENISA pour les signalements",
        "portee": "Fabricants, importateurs et distributeurs de produits "
                  "comportant des éléments numériques mis sur le marché de l'Union.",
    },
    {
        "id": "cer",
        "titre": "Directive REC/CER",
        "officiel": "Directive (UE) 2022/2557 sur la résilience des entités critiques",
        "nature": "directive", "celex": "32022L2557",
        "domaines": ["cyber", "ot"],
        "jalons": ["17 octobre 2024 — date limite de transposition"],
        "autorite": "Autorités nationales désignées",
        "portee": "Volet physique et organisationnel, complémentaire de NIS 2 "
                  "sur le volet numérique.",
    },
    {
        "id": "csa",
        "titre": "Cybersecurity Act",
        "officiel": "Règlement (UE) 2019/881 relatif à l'ENISA et à la "
                    "certification de cybersécurité des technologies de l'information",
        "nature": "reglement", "celex": "32019R0881",
        "domaines": ["cyber"],
        "jalons": ["27 juin 2019 — application"],
        "autorite": "ENISA ; ANSSI comme autorité nationale de certification",
        "portee": "Cadre européen des schémas de certification de cybersécurité "
                  "(EUCC, EUCS…).",
    },
    {
        "id": "red-da",
        "titre": "Exigences cyber des équipements radio",
        "officiel": "Règlement délégué (UE) 2022/30 complétant la directive 2014/53/UE "
                    "(exigences essentielles de cybersécurité)",
        "nature": "reglement", "celex": "32022R0030",
        "domaines": ["cyber", "ot"],
        "jalons": ["1er août 2025 — application"],
        "autorite": "Autorités de surveillance du marché",
        "portee": "Équipements radio connectés : protection du réseau, des "
                  "données personnelles et contre la fraude.",
    },
    {
        "id": "lpm",
        "titre": "LPM 2024-2030",
        "officiel": "Loi n° 2023-703 du 1er août 2023 relative à la programmation "
                    "militaire pour les années 2024 à 2030",
        "nature": "loi", "domaines": ["cyber"],
        "jalons": ["Dispositions cyber applicables depuis 2023-2024"],
        "autorite": "ANSSI",
        "portee": "Pouvoirs de détection et de notification de l'ANSSI, "
                  "obligations des opérateurs et des éditeurs de logiciels.",
    },
    {
        "id": "oiv",
        "titre": "Dispositif OIV / SAIV",
        "officiel": "Code de la défense, art. L. 1332-1 s. — sécurité des activités "
                    "d'importance vitale et des systèmes d'information d'importance vitale",
        "nature": "code", "domaines": ["cyber", "ot"],
        "jalons": ["Arrêtés sectoriels ; régime antérieur à NIS 2 et maintenu"],
        "autorite": "SGDSN / ANSSI",
        "portee": "Opérateurs d'importance vitale : règles de sécurité, "
                  "homologation des SIIV, contrôles.",
    },
    {
        "id": "iso-27001",
        "titre": "ISO/IEC 27001:2022",
        "officiel": "ISO/IEC 27001:2022 — Systèmes de management de la sécurité de l'information",
        "nature": "norme", "domaines": ["cyber"],
        "jalons": ["Publiée en octobre 2022 ; transition depuis la version 2013 achevée"],
        "autorite": "Certification par organisme accrédité (volontaire)",
        "portee": "Référentiel de management de la sécurité, fréquemment exigé "
                  "contractuellement et reconnu comme preuve de diligence.",
    },
    {
        "id": "iso-27036",
        "titre": "ISO/IEC 27036",
        "officiel": "ISO/IEC 27036 — Sécurité de l'information dans les relations "
                    "avec les fournisseurs",
        "nature": "norme", "domaines": ["cyber", "contrats"],
        "jalons": ["Série en plusieurs parties"],
        "autorite": "Référentiel volontaire",
        "portee": "Cadre méthodologique directement mobilisable pour rédiger et "
                  "contrôler les exigences de sécurité d'un contrat fournisseur.",
    },
    {
        "id": "iec-62443",
        "titre": "IEC 62443",
        "officiel": "Série IEC 62443 — Sécurité des systèmes d'automatisation et "
                    "de commande industriels (IACS)",
        "nature": "norme", "domaines": ["ot", "cyber", "contrats"],
        "jalons": [
            "62443-2-1 — programme de sécurité de l'exploitant",
            "62443-2-4 — exigences applicables aux prestataires de services IACS",
            "62443-3-2 — analyse de risque, zones et conduits",
            "62443-3-3 — exigences système et niveaux de sécurité (SL)",
            "62443-4-1 — cycle de développement sécurisé",
            "62443-4-2 — exigences des composants",
        ],
        "autorite": "Référentiel volontaire ; certification IECEE / ISASecure",
        "portee": "Exploitants, intégrateurs, mainteneurs et fournisseurs de "
                  "composants d'installations industrielles.",
    },
    {
        "id": "iec-61508",
        "titre": "IEC 61508 / 61511",
        "officiel": "IEC 61508 et IEC 61511 — Sécurité fonctionnelle des systèmes "
                    "électriques/électroniques programmables",
        "nature": "norme", "domaines": ["ot"],
        "jalons": ["Référentiels de sûreté fonctionnelle (SIL)"],
        "autorite": "Référentiel volontaire ; exigé par certains régimes sectoriels",
        "portee": "Interface sûreté/sécurité : une mesure de cybersécurité ne "
                  "doit pas dégrader une fonction instrumentée de sécurité.",
    },
    {
        "id": "nist-800-82",
        "titre": "NIST SP 800-82 Rev. 3",
        "officiel": "NIST SP 800-82 Rev. 3 — Guide to Operational Technology Security (2023)",
        "nature": "referentiel", "domaines": ["ot", "cyber"],
        "jalons": ["Révision 3 publiée en 2023"],
        "autorite": "Référentiel volontaire",
        "portee": "Guide de référence pour la sécurisation des environnements OT/ICS.",
    },
    {
        "id": "nist-csf",
        "titre": "NIST CSF 2.0",
        "officiel": "NIST Cybersecurity Framework 2.0 (2024)",
        "nature": "referentiel", "domaines": ["cyber"],
        "jalons": ["Version 2.0 publiée en 2024 ; ajout de la fonction GOVERN"],
        "autorite": "Référentiel volontaire",
        "portee": "Cadre de pilotage de la cybersécurité, utile pour structurer "
                  "un plan de mise en conformité NIS 2.",
    },
    {
        "id": "ebios-rm",
        "titre": "EBIOS Risk Manager",
        "officiel": "Méthode EBIOS Risk Manager — ANSSI / Club EBIOS",
        "nature": "referentiel", "domaines": ["cyber", "ot"],
        "jalons": ["Méthode de référence en France"],
        "autorite": "ANSSI",
        "portee": "Analyse de risque par scénarios stratégiques et opérationnels ; "
                  "attendue par plusieurs régimes français.",
    },

    # ── Marché numérique, données et contrats ─────────────────────────────
    {
        "id": "data-act",
        "titre": "Data Act",
        "officiel": "Règlement (UE) 2023/2854 sur des règles harmonisées portant "
                    "sur l'équité de l'accès aux données et de leur utilisation",
        "nature": "reglement", "celex": "32023R2854",
        "domaines": ["donnees", "numerique", "contrats"],
        "jalons": ["12 septembre 2025 — application"],
        "autorite": "Autorités nationales compétentes à désigner",
        "portee": "Fabricants de produits connectés, fournisseurs de services "
                  "connexes et fournisseurs de services de traitement de données "
                  "(changement de fournisseur, clauses abusives).",
    },
    {
        "id": "dga",
        "titre": "Data Governance Act",
        "officiel": "Règlement (UE) 2022/868 portant sur la gouvernance européenne des données",
        "nature": "reglement", "celex": "32022R0868",
        "domaines": ["donnees"],
        "jalons": ["24 septembre 2023 — application"],
        "autorite": "Autorités nationales compétentes",
        "portee": "Réutilisation des données du secteur public, services "
                  "d'intermédiation de données, altruisme des données.",
    },
    {
        "id": "dsa",
        "titre": "DSA",
        "officiel": "Règlement (UE) 2022/2065 relatif à un marché unique des services numériques",
        "nature": "reglement", "celex": "32022R2065",
        "domaines": ["numerique"],
        "jalons": ["17 février 2024 — application générale"],
        "autorite": "Arcom (coordinateur pour les services numériques en France) ; Commission",
        "portee": "Services intermédiaires, hébergeurs et plateformes en ligne.",
    },
    {
        "id": "dma",
        "titre": "DMA",
        "officiel": "Règlement (UE) 2022/1925 relatif aux marchés contestables et "
                    "équitables dans le secteur numérique",
        "nature": "reglement", "celex": "32022R1925",
        "domaines": ["numerique"],
        "jalons": ["2 mai 2023 — application"],
        "autorite": "Commission européenne",
        "portee": "Contrôleurs d'accès désignés ; effets indirects sur les "
                  "entreprises utilisatrices.",
    },
    {
        "id": "lcen",
        "titre": "LCEN",
        "officiel": "Loi n° 2004-575 du 21 juin 2004 pour la confiance dans "
                    "l'économie numérique",
        "nature": "loi", "domaines": ["numerique"],
        "jalons": ["Modifiée à plusieurs reprises, notamment en 2024"],
        "autorite": "Juridictions de droit commun ; Arcom",
        "portee": "Statut des hébergeurs, commerce électronique, obligations "
                  "d'information des éditeurs de services en ligne.",
    },
    {
        "id": "resp-produits",
        "titre": "Responsabilité du fait des produits défectueux",
        "officiel": "Directive (UE) 2024/2853 relative à la responsabilité du fait "
                    "des produits défectueux",
        "nature": "directive", "celex": "32024L2853",
        "domaines": ["numerique", "ia", "contrats"],
        "jalons": ["9 décembre 2026 — date limite de transposition"],
        "autorite": "Juridictions de droit commun",
        "portee": "Étend le régime aux logiciels et aux systèmes d'IA ; "
                  "aménage la charge de la preuve au profit de la victime.",
    },
    {
        "id": "machines",
        "titre": "Règlement Machines",
        "officiel": "Règlement (UE) 2023/1230 relatif aux machines",
        "nature": "reglement", "celex": "32023R1230",
        "domaines": ["ot", "ia"],
        "jalons": ["20 janvier 2027 — application"],
        "autorite": "Autorités de surveillance du marché",
        "portee": "Machines et produits connexes, y compris les fonctions de "
                  "sécurité assurées par un logiciel ou une IA.",
    },
    {
        "id": "eidas2",
        "titre": "eIDAS 2",
        "officiel": "Règlement (UE) 2024/1183 modifiant le règlement (UE) n° 910/2014 "
                    "(cadre européen relatif à une identité numérique)",
        "nature": "reglement", "celex": "32024R1183",
        "domaines": ["numerique", "donnees"],
        "jalons": ["Déploiement progressif du portefeuille européen d'identité numérique"],
        "autorite": "ANSSI (organe de contrôle des prestataires de services de confiance)",
        "portee": "Identification électronique, signature, cachet, horodatage "
                  "et portefeuille d'identité.",
    },
    {
        "id": "loi-1971",
        "titre": "Périmètre du conseil juridique",
        "officiel": "Loi n° 71-1130 du 31 décembre 1971 portant réforme de certaines "
                    "professions judiciaires et juridiques (art. 54 et suivants)",
        "nature": "loi", "domaines": ["contrats"],
        "jalons": ["Régit qui peut délivrer une consultation juridique"],
        "autorite": "Ordres professionnels ; juridictions",
        "portee": "Encadre la fourniture, à titre habituel et rémunéré, de "
                  "consultations juridiques et de rédaction d'actes.",
    },
]

_INDEX = {t["id"]: t for t in REFERENTIEL}


def texte(ref_id):
    """Fiche d'un texte, ou None."""
    return _INDEX.get(ref_id)


def url_officielle(ref):
    """URL vers la source officielle. EUR-Lex pour les textes UE (identifiant
    CELEX, stable et non ambigu), recherche Légifrance sinon — on ne devine
    jamais un identifiant national, au risque de pointer vers un autre texte."""
    if isinstance(ref, str):
        ref = _INDEX.get(ref) or {}
    if ref.get("celex"):
        return EURLEX % ref["celex"]
    if ref.get("nature") in ("loi", "code"):
        from urllib.parse import quote
        return LEGIFRANCE % quote(ref.get("officiel", ref.get("titre", "")))
    return ""


def referentiel(domaine=None):
    """Textes du référentiel, éventuellement filtrés par domaine."""
    out = [t for t in REFERENTIEL if not domaine or domaine in t.get("domaines", [])]
    return [dict(t, url=url_officielle(t)) for t in out]


# ═══════════════════════════════════════════════════════════════════════════
# 2. QUALIFICATION DÉTERMINISTE — quels textes s'appliquent, et pourquoi
# ═══════════════════════════════════════════════════════════════════════════
#
# Aucun appel de modèle ici. Un client doit pouvoir contester le raisonnement :
# chaque rattachement porte sa motivation en clair et le niveau de certitude
# associé. C'est la différence entre « l'IA pense que NIS 2 s'applique » et
# « NIS 2 s'applique parce que votre secteur figure à l'annexe I et que vous
# dépassez le seuil de 250 salariés ».

# Secteurs de l'annexe I de la directive NIS 2 (entités hautement critiques).
SECTEURS_NIS2_ANNEXE_I = [
    "energie", "transports", "banque", "marches-financiers", "sante",
    "eau-potable", "eaux-usees", "infrastructure-numerique",
    "gestion-services-tic", "administration-publique", "espace",
]
# Secteurs de l'annexe II (autres secteurs critiques).
SECTEURS_NIS2_ANNEXE_II = [
    "poste-courrier", "dechets", "chimie", "alimentation",
    "fabrication", "numerique-fournisseurs", "recherche",
]

SECTEURS = [
    ("energie", "Énergie (électricité, gaz, pétrole, hydrogène, chaleur)", "I"),
    ("transports", "Transports (aérien, ferroviaire, maritime, routier)", "I"),
    ("banque", "Banque", "I"),
    ("marches-financiers", "Infrastructures des marchés financiers", "I"),
    ("sante", "Santé", "I"),
    ("eau-potable", "Eau potable", "I"),
    ("eaux-usees", "Eaux usées", "I"),
    ("infrastructure-numerique", "Infrastructure numérique (IXP, DNS, cloud, datacenters, CDN…)", "I"),
    ("gestion-services-tic", "Gestion de services TIC (MSP, MSSP)", "I"),
    ("administration-publique", "Administration publique", "I"),
    ("espace", "Espace", "I"),
    ("poste-courrier", "Services postaux et d'expédition", "II"),
    ("dechets", "Gestion des déchets", "II"),
    ("chimie", "Fabrication, production et distribution de produits chimiques", "II"),
    ("alimentation", "Production, transformation et distribution alimentaires", "II"),
    ("fabrication", "Fabrication (dispositifs médicaux, électronique, machines, véhicules…)", "II"),
    ("numerique-fournisseurs", "Fournisseurs numériques (places de marché, moteurs, réseaux sociaux)", "II"),
    ("recherche", "Recherche", "II"),
    ("autre", "Autre secteur", None),
]

# Rôles possibles dans une chaîne de valeur numérique. Un même acteur en cumule
# souvent plusieurs : la qualification doit les traiter indépendamment.
ROLES = [
    ("exploitant", "Exploitant / utilisateur final du système"),
    ("fournisseur-ia", "Fournisseur d'un système d'IA (mise sur le marché sous son nom)"),
    ("deployeur-ia", "Déployeur d'un système d'IA (utilisation sous sa propre autorité)"),
    ("fournisseur-gpai", "Fournisseur d'un modèle d'IA à usage général"),
    ("importateur", "Importateur ou distributeur de produits numériques"),
    ("fabricant", "Fabricant de produits comportant des éléments numériques"),
    ("prestataire-tic", "Prestataire de services TIC (infogérance, cloud, MSSP)"),
    ("integrateur-ot", "Intégrateur ou mainteneur d'installations industrielles (IACS)"),
    ("sous-traitant-rgpd", "Sous-traitant au sens du RGPD"),
    ("responsable-rgpd", "Responsable de traitement au sens du RGPD"),
    ("hebergeur", "Hébergeur ou intermédiaire en ligne"),
]

# Schéma du questionnaire, publié tel quel à l'interface : une seule définition,
# pas de liste d'options recopiée dans le HTML qui finirait par diverger.
PROFIL_CHAMPS = [
    {"id": "secteur", "label": "Secteur d'activité", "type": "choix",
     "options": [{"v": s[0], "l": s[1]} for s in SECTEURS],
     "aide": "Détermine le rattachement aux annexes I et II de la directive NIS 2."},
    {"id": "effectif", "label": "Effectif", "type": "choix",
     "options": [{"v": "moins-50", "l": "Moins de 50 salariés"},
                 {"v": "50-249", "l": "De 50 à 249 salariés"},
                 {"v": "250-plus", "l": "250 salariés ou plus"}],
     "aide": "Seuil de taille de NIS 2 (art. 2), fondé sur la recommandation 2003/361/CE."},
    {"id": "chiffre_affaires", "label": "Chiffre d'affaires annuel", "type": "choix",
     "options": [{"v": "moins-10", "l": "Moins de 10 M€"},
                 {"v": "10-50", "l": "De 10 à 50 M€"},
                 {"v": "plus-50", "l": "Plus de 50 M€"}]},
    {"id": "roles", "label": "Rôles exercés", "type": "multi",
     "options": [{"v": r[0], "l": r[1]} for r in ROLES],
     "aide": "Plusieurs rôles peuvent être cumulés ; chacun emporte ses propres obligations."},
    {"id": "donnees_personnelles", "label": "Traitement de données personnelles",
     "type": "bool"},
    {"id": "donnees_sensibles", "label": "Données sensibles ou infractions (art. 9 et 10 RGPD)",
     "type": "bool"},
    {"id": "systeme_ot", "label": "Systèmes industriels (OT / ICS / SCADA) dans le périmètre",
     "type": "bool"},
    {"id": "ia_usage", "label": "Usage d'intelligence artificielle", "type": "choix",
     "options": [{"v": "aucun", "l": "Aucun"},
                 {"v": "interne", "l": "Outils d'IA utilisés en interne"},
                 {"v": "integre", "l": "IA intégrée à un produit ou service fourni à des tiers"},
                 {"v": "securite", "l": "IA assurant une fonction de sécurité d'un produit réglementé"}]},
    {"id": "ia_annexe_iii", "label": "Usage relevant de l'annexe III de l'IA Act "
                                     "(emploi, crédit, éducation, infrastructures critiques, biométrie…)",
     "type": "bool"},
    {"id": "operateur_vital", "label": "Opérateur d'importance vitale (OIV) ou entité critique",
     "type": "bool"},
    {"id": "secteur_financier", "label": "Entité financière au sens de l'art. 2 de DORA",
     "type": "bool"},
    {"id": "produits_numeriques", "label": "Mise sur le marché de produits comportant "
                                           "des éléments numériques",
     "type": "bool"},
    {"id": "hors_ue", "label": "Transferts de données hors Union européenne", "type": "bool"},
]


def _vrai(profil, cle):
    v = profil.get(cle)
    return v is True or v == "true" or v == "oui" or v == 1 or v == "1"


def _roles(profil):
    r = profil.get("roles") or []
    if isinstance(r, str):
        r = [x.strip() for x in r.split(",") if x.strip()]
    return set(r)


def _taille_nis2(profil):
    """Classe de taille au sens de NIS 2 : « grande », « moyenne » ou « petite ».

    NIS 2 renvoie à la recommandation 2003/361/CE : est grande l'entreprise qui
    dépasse 250 salariés OU 50 M€ de chiffre d'affaires avec un bilan supérieur
    à 43 M€. Le bilan n'étant pas demandé au profil, le critère de chiffre
    d'affaires est traité comme un indice — le résultat est donc annoncé comme
    « à confirmer » et non comme acquis."""
    eff = profil.get("effectif")
    ca = profil.get("chiffre_affaires")
    if eff == "250-plus":
        return "grande", "effectif de 250 salariés ou plus"
    if ca == "plus-50":
        return "grande", "chiffre d'affaires supérieur à 50 M€ (bilan à confirmer)"
    if eff == "50-249" or ca == "10-50":
        return "moyenne", "entreprise de taille moyenne (50 à 249 salariés ou 10 à 50 M€)"
    return "petite", "sous les seuils de taille"


def qualifier(profil):
    """Textes applicables à un profil, avec la motivation de chaque rattachement.

    Renvoie {applicables, a_verifier, ecartes, synthese} où chaque élément porte
    `texte`, `motif`, `certitude` et `points` (obligations saillantes). Aucun
    modèle de langage n'intervient : le résultat est reproductible et opposable.
    """
    profil = profil or {}
    roles = _roles(profil)
    secteur = profil.get("secteur") or "autre"
    taille, motif_taille = _taille_nis2(profil)
    res, avec_reserve = [], []

    def retenir(ref_id, motif, certitude="certaine", points=None):
        t = _INDEX.get(ref_id)
        if not t:
            return
        item = {"id": ref_id, "titre": t["titre"], "officiel": t["officiel"],
                "nature": t["nature"], "url": url_officielle(t),
                "jalons": t.get("jalons", []), "autorite": t.get("autorite", ""),
                "motif": motif, "certitude": certitude, "points": points or []}
        (res if certitude == "certaine" else avec_reserve).append(item)

    # ── NIS 2 ────────────────────────────────────────────────────────────
    if secteur in SECTEURS_NIS2_ANNEXE_I:
        if taille == "grande":
            retenir("nis2", "Secteur de l'annexe I (entités hautement critiques) et "
                            + motif_taille + " : qualification d'entité ESSENTIELLE.",
                    "certaine",
                    ["Mesures de gestion des risques (art. 21), dont la sécurité de "
                     "la chaîne d'approvisionnement (art. 21.2.d)",
                     "Notification en trois temps : alerte précoce sous 24 h, "
                     "notification sous 72 h, rapport final sous un mois (art. 23)",
                     "Responsabilité des organes de direction : approbation des "
                     "mesures et formation (art. 20)",
                     "Supervision proactive : contrôles sur place possibles sans "
                     "soupçon préalable (art. 32)"])
        elif taille == "moyenne":
            retenir("nis2", "Secteur de l'annexe I et " + motif_taille +
                            " : qualification d'entité IMPORTANTE.", "certaine",
                    ["Mêmes mesures de gestion des risques (art. 21) et mêmes "
                     "délais de notification (art. 23) que les entités essentielles",
                     "Supervision a posteriori seulement (art. 33), et plafond de "
                     "sanction inférieur (art. 34)"])
        else:
            retenir("nis2", "Secteur de l'annexe I mais " + motif_taille +
                            " : hors champ par la taille, sauf exception "
                            "sectorielle indépendante de la taille (art. 2.2 : DNS, "
                            "registres de noms de domaine, prestataires de services "
                            "de confiance, communications électroniques, "
                            "administration publique, entité unique d'un service "
                            "essentiel).", "a_verifier")
    elif secteur in SECTEURS_NIS2_ANNEXE_II:
        if taille in ("grande", "moyenne"):
            retenir("nis2", "Secteur de l'annexe II (autres secteurs critiques) et "
                            + motif_taille + " : qualification d'entité IMPORTANTE.",
                    "certaine",
                    ["Mesures de gestion des risques (art. 21) et notification (art. 23)",
                     "Supervision a posteriori (art. 33)"])
        else:
            retenir("nis2", "Secteur de l'annexe II mais " + motif_taille +
                            " : hors champ par la taille, sous réserve des "
                            "exceptions de l'art. 2.2.", "a_verifier")
    if "prestataire-tic" in roles and secteur not in SECTEURS_NIS2_ANNEXE_I:
        retenir("nis2", "Prestataire de services TIC gérés : le secteur « gestion "
                        "de services TIC » figure à l'annexe I, indépendamment du "
                        "secteur de vos clients.", "a_verifier")
    if _INDEX.get("nis2") and any(x["id"] == "nis2" for x in res + avec_reserve):
        retenir("nis2-fr", "Le périmètre exact, les délais et les sanctions sont "
                           "fixés par le texte français de transposition : son état "
                           "doit être vérifié sur Légifrance avant tout engagement.",
                "a_verifier")

    # ── DORA ─────────────────────────────────────────────────────────────
    if _vrai(profil, "secteur_financier") or secteur in ("banque", "marches-financiers"):
        retenir("dora", "Entité financière relevant de l'art. 2 du règlement DORA.",
                "certaine",
                ["Cadre de gestion du risque lié aux TIC (art. 5 à 16)",
                 "Notification des incidents majeurs liés aux TIC (art. 17 à 23)",
                 "Tests de résilience opérationnelle numérique, dont TLPT pour les "
                 "entités désignées (art. 24 à 27)",
                 "Gestion du risque lié aux prestataires tiers de services TIC, "
                 "dont les clauses contractuelles obligatoires (art. 28 à 30)"])
        retenir("dora-directive", "Directive d'accompagnement alignant les "
                                  "directives financières sectorielles sur DORA.", "certaine")
    elif "prestataire-tic" in roles:
        retenir("dora", "Prestataire tiers de services TIC : DORA ne vous impose pas "
                        "directement ses obligations, mais vos clients financiers "
                        "doivent vous imposer les stipulations de l'art. 30 — et une "
                        "désignation comme prestataire critique (art. 31) entraînerait "
                        "une supervision directe.", "a_verifier",
                ["Anticiper les clauses obligatoires de l'art. 30.2 et 30.3",
                 "Droits d'accès, d'inspection et d'audit du client et du superviseur",
                 "Stratégies de sortie et assistance à la réversibilité"])

    # ── IA Act ───────────────────────────────────────────────────────────
    ia = profil.get("ia_usage") or "aucun"
    if "fournisseur-ia" in roles or ia == "integre":
        certitude = "certaine" if "fournisseur-ia" in roles else "a_verifier"
        retenir("ai-act", "Mise à disposition d'un système d'IA sur le marché de "
                          "l'Union sous votre nom ou votre marque : qualification de "
                          "FOURNISSEUR (art. 3.3).", certitude,
                ["Vérifier d'abord l'absence de pratique interdite (art. 5)",
                 "Déterminer la classification : haut risque au titre de l'art. 6(1) "
                 "(composant de sécurité d'un produit réglementé) ou de l'annexe III",
                 "Si haut risque : système de management de la qualité (art. 17), "
                 "documentation technique (art. 11 et annexe IV), gestion des risques "
                 "(art. 9), gouvernance des données (art. 10), enregistrement (art. 49), "
                 "évaluation de la conformité (art. 43), marquage CE",
                 "Obligations de transparence de l'art. 50 dès lors qu'il y a "
                 "interaction avec des personnes ou génération de contenus"])
    if "deployeur-ia" in roles or ia == "interne":
        retenir("ai-act", "Utilisation d'un système d'IA sous votre propre autorité : "
                          "qualification de DÉPLOYEUR (art. 3.4).",
                "certaine" if "deployeur-ia" in roles else "a_verifier",
                ["Littératie en IA du personnel concerné (art. 4), applicable "
                 "depuis le 2 février 2025",
                 "Usage conforme à la notice, contrôle humain effectif et "
                 "surveillance du fonctionnement (art. 26) pour le haut risque",
                 "Analyse d'impact sur les droits fondamentaux (art. 27) pour "
                 "certains déployeurs de systèmes de l'annexe III",
                 "Attention à l'art. 25 : modifier substantiellement un système, "
                 "y apposer sa marque ou en changer la destination fait basculer "
                 "le déployeur dans le statut de fournisseur"])
    if "fournisseur-gpai" in roles:
        retenir("ai-act", "Fourniture d'un modèle d'IA à usage général : chapitre V, "
                          "applicable depuis le 2 août 2025.", "certaine",
                ["Documentation technique et information des fournisseurs en aval (art. 53)",
                 "Politique de respect du droit d'auteur et résumé des contenus "
                 "d'entraînement (art. 53.1.c et d)",
                 "Obligations renforcées si risque systémique (art. 55)"])
    if _vrai(profil, "ia_annexe_iii"):
        retenir("ai-act", "Usage relevant d'un domaine de l'annexe III : présomption "
                          "de haut risque, sauf à démontrer et documenter une "
                          "dérogation de l'art. 6(3).", "certaine",
                ["La dérogation de l'art. 6(3) suppose une évaluation documentée "
                 "AVANT mise sur le marché, et un enregistrement (art. 49.2)",
                 "Elle est écartée d'office en cas de profilage de personnes physiques"])
    if ia == "securite":
        retenir("ai-act", "IA assurant une fonction de sécurité d'un produit couvert "
                          "par la législation d'harmonisation de l'annexe I : haut "
                          "risque au titre de l'art. 6(1), applicable au 2 août 2028.",
                "certaine")
        retenir("machines", "Une fonction de sécurité assurée par un logiciel ou une IA "
                            "relève également du règlement Machines.", "a_verifier")
    if ia != "aucun":
        retenir("iso-42001", "Référentiel volontaire structurant la gouvernance IA ; "
                             "utile comme preuve de diligence et comme trame de "
                             "mise en conformité.", "certaine")
        retenir("iso-23894", "Méthode d'appréciation du risque IA articulable avec "
                             "l'analyse de risque existante.", "certaine")

    # ── Données personnelles ─────────────────────────────────────────────
    if _vrai(profil, "donnees_personnelles") or roles & {"responsable-rgpd", "sous-traitant-rgpd"}:
        pts = ["Registre des activités de traitement (art. 30)",
               "Base légale et information des personnes (art. 6, 12 à 14)",
               "Sécurité des traitements (art. 32) et notification des violations "
               "(art. 33 et 34)"]
        if "sous-traitant-rgpd" in roles:
            pts.append("Contrat de sous-traitance conforme à l'art. 28.3, y compris "
                       "l'autorisation de la sous-traitance ultérieure (art. 28.2 et 28.4)")
        if _vrai(profil, "donnees_sensibles"):
            pts.append("Données de l'art. 9 ou 10 : condition de levée d'interdiction "
                       "à identifier, et analyse d'impact très probablement requise "
                       "(art. 35)")
        retenir("rgpd", "Traitement de données à caractère personnel.", "certaine", pts)
        retenir("loi-78-17", "Marges nationales et régime de sanction en droit français.",
                "certaine")
        if _vrai(profil, "hors_ue"):
            retenir("rgpd", "Transferts hors Union : chapitre V — mécanisme de "
                            "transfert et analyse d'impact du transfert.", "certaine",
                    ["Décision d'adéquation, clauses contractuelles types ou règles "
                     "d'entreprise contraignantes (art. 45 à 47)",
                     "Analyse d'impact du transfert et mesures supplémentaires "
                     "éventuelles"])

    # ── Produits, cyber transverse ───────────────────────────────────────
    if _vrai(profil, "produits_numeriques") or roles & {"fabricant", "importateur"}:
        retenir("cra", "Mise sur le marché de produits comportant des éléments "
                       "numériques.", "certaine",
                ["Exigences essentielles de sécurité et gestion des vulnérabilités "
                 "(annexe I)",
                 "Signalement à l'ENISA des vulnérabilités activement exploitées et "
                 "des incidents graves à compter du 11 septembre 2026",
                 "Support et correctifs pendant la période d'assistance annoncée",
                 "Nomenclature logicielle (SBOM) et évaluation de la conformité"])
        retenir("resp-produits", "Le nouveau régime de responsabilité du fait des "
                                 "produits couvre expressément les logiciels et les "
                                 "systèmes d'IA.", "certaine")
    if _vrai(profil, "operateur_vital"):
        retenir("oiv", "Opérateur d'importance vitale : régime français antérieur à "
                       "NIS 2 et maintenu, avec homologation des systèmes "
                       "d'information d'importance vitale.", "certaine")
        retenir("cer", "Volet physique et organisationnel de la résilience, "
                       "complémentaire de NIS 2.", "a_verifier")
        retenir("lpm", "Pouvoirs de détection et obligations de notification "
                       "renforcés.", "certaine")

    # ── OT / ICS ─────────────────────────────────────────────────────────
    if _vrai(profil, "systeme_ot") or "integrateur-ot" in roles:
        retenir("iec-62443", "Présence de systèmes d'automatisation et de commande "
                             "industriels dans le périmètre.", "certaine",
                ["62443-2-4 : exigences opposables aux prestataires de services IACS — "
                 "socle contractuel pour l'intégration et la maintenance",
                 "62443-3-2 : découpage en zones et conduits, niveaux de sécurité cibles",
                 "62443-4-1 et 4-2 : développement sécurisé et exigences des composants"])
        retenir("iec-61508", "Interface sûreté / sécurité : une mesure de "
                             "cybersécurité ne doit pas dégrader une fonction "
                             "instrumentée de sécurité.", "certaine")
        retenir("nist-800-82", "Guide de référence pour la sécurisation des "
                               "environnements OT.", "certaine")
        retenir("ebios-rm", "Méthode d'analyse de risque attendue par les régimes "
                            "français et adaptée aux scénarios industriels.", "certaine")

    # ── Contrats et marché ───────────────────────────────────────────────
    if roles & {"prestataire-tic", "fabricant", "integrateur-ot"} or _vrai(profil, "produits_numeriques"):
        retenir("data-act", "Produits connectés, services connexes ou services de "
                            "traitement de données : accès aux données, changement de "
                            "fournisseur et contrôle des clauses abusives.", "a_verifier",
                ["Chapitre sur le changement de fournisseur : suppression progressive "
                 "des frais de transfert et obligations d'assistance à la migration",
                 "Contrôle des clauses contractuelles abusives imposées "
                 "unilatéralement entre entreprises"])
        retenir("iso-27036", "Cadre méthodologique pour formuler et contrôler les "
                             "exigences de sécurité dans la relation fournisseur.",
                "certaine")
    if "hebergeur" in roles:
        retenir("dsa", "Service intermédiaire ou hébergeur : obligations de "
                       "signalement, de transparence et de traitement des "
                       "notifications.", "certaine")
        retenir("lcen", "Statut d'hébergeur et obligations d'information en droit "
                        "français.", "certaine")

    # Socle transverse : présent dès qu'il y a un enjeu cyber quelconque.
    if res or avec_reserve:
        retenir("iso-27001", "Référentiel de management de la sécurité : preuve de "
                             "diligence et trame de mise en conformité, régulièrement "
                             "exigé par les donneurs d'ordre.", "certaine")

    # Dédoublonnage : un même texte peut être retenu par plusieurs règles ; on
    # fusionne les motifs plutôt que d'afficher trois fois « RGPD ».
    def _fusion(liste):
        vu = {}
        for it in liste:
            if it["id"] in vu:
                if it["motif"] not in vu[it["id"]]["motifs"]:
                    vu[it["id"]]["motifs"].append(it["motif"])
                for p in it["points"]:
                    if p not in vu[it["id"]]["points"]:
                        vu[it["id"]]["points"].append(p)
            else:
                x = dict(it)
                x["motifs"] = [x.pop("motif")]
                vu[it["id"]] = x
        return list(vu.values())

    applicables = _fusion(res)
    ids_certains = {x["id"] for x in applicables}
    a_verifier = [x for x in _fusion(avec_reserve) if x["id"] not in ids_certains]

    return {
        "version_referentiel": VERSION_REFERENTIEL,
        "profil": profil,
        "taille_nis2": taille,
        "applicables": applicables,
        "a_verifier": a_verifier,
        "synthese": _synthese(applicables, a_verifier),
        "avertissement": AVERTISSEMENT,
    }


def _synthese(applicables, a_verifier):
    if not applicables and not a_verifier:
        return ("Aucun texte du référentiel n'est rattaché à ce profil en l'état. "
                "Complétez le questionnaire : le rattachement dépend surtout du "
                "secteur, de la taille et des rôles exercés.")
    n, m = len(applicables), len(a_verifier)
    p = "%d texte%s directement applicable%s" % (n, "s" if n > 1 else "", "s" if n > 1 else "")
    if m:
        p += " et %d à confirmer" % m
    return (p + ". Les rattachements « à confirmer » dépendent d'un élément que le "
            "questionnaire ne tranche pas seul (bilan comptable, exception "
            "sectorielle, état d'une transposition) : ils doivent être arbitrés "
            "au vu des pièces.")


# ═══════════════════════════════════════════════════════════════════════════
# 3. CLAUSIER FOURNISSEURS — exigences contractuelles fondées article par article
# ═══════════════════════════════════════════════════════════════════════════
#
# Chaque clause porte son fondement : c'est ce qui permet de la défendre en
# négociation (« ce n'est pas une exigence de confort, elle découle de l'art. 28.3
# du RGPD ») et de justifier son abandon lorsqu'elle n'a pas de fondement.
CLAUSIER = [
    {
        "id": "perimetre-securite", "domaine": "Socle", "criticite": "haute",
        "titre": "Définition du périmètre de sécurité et des systèmes couverts",
        "fondement": ["NIS 2, art. 21.2.d", "IEC 62443-2-4", "ISO/IEC 27036"],
        "objectif": "Délimiter sans ambiguïté les systèmes, interfaces et données "
                    "que le prestataire prend en charge.",
        "modele": "Le Prestataire assure les Services sur le périmètre décrit en "
                  "Annexe [n], laquelle identifie les systèmes, réseaux, zones et "
                  "conduits concernés ainsi que les interfaces avec les systèmes du "
                  "Client. Toute évolution du périmètre fait l'objet d'un avenant "
                  "et d'une réévaluation des risques.",
        "risque": "Sans périmètre écrit, chaque incident donne lieu à une "
                  "discussion sur le point de savoir qui devait couvrir la zone "
                  "concernée — au moment précis où il faut agir.",
    },
    {
        "id": "mesures-techniques", "domaine": "Socle", "criticite": "haute",
        "titre": "Mesures techniques et organisationnelles minimales",
        "fondement": ["RGPD, art. 32", "NIS 2, art. 21.2", "DORA, art. 30.2",
                      "IEC 62443-2-4"],
        "objectif": "Fixer un socle vérifiable plutôt qu'un engagement d'« état de l'art ».",
        "modele": "Le Prestataire met en œuvre a minima les mesures décrites en "
                  "Annexe Sécurité, dont : cloisonnement réseau, authentification "
                  "multifacteur pour tout accès d'administration, chiffrement des "
                  "données en transit et au repos, journalisation conservée [n] mois, "
                  "gestion des correctifs selon les délais de l'Annexe, et sauvegardes "
                  "testées. Ces mesures constituent un plancher contractuel ; leur "
                  "évolution ne peut qu'élever le niveau de protection.",
        "risque": "La formule « état de l'art » sans annexe est inexploitable en "
                  "contentieux : elle ne permet ni de constater un manquement ni "
                  "de le chiffrer.",
    },
    {
        "id": "notification-incident", "domaine": "Incidents", "criticite": "haute",
        "titre": "Notification des incidents dans des délais compatibles avec vos propres obligations",
        "fondement": ["NIS 2, art. 23", "RGPD, art. 33.2", "DORA, art. 19", "CRA"],
        "objectif": "Recevoir l'information assez tôt pour tenir vos propres délais "
                    "réglementaires.",
        "modele": "Le Prestataire informe le Client de tout incident de sécurité "
                  "affectant les Services sans délai injustifié et au plus tard dans "
                  "les [8] heures suivant sa détection, par [canal], avec les "
                  "éléments permettant au Client de satisfaire ses propres obligations "
                  "de notification. Il fournit les compléments d'analyse au fil de "
                  "l'investigation et un rapport final sous [15] jours.",
        "risque": "Une alerte précoce est due sous 24 h au titre de NIS 2 et une "
                  "notification sous 72 h au titre du RGPD : un délai fournisseur de "
                  "48 h rend ces obligations matériellement intenables.",
    },
    {
        "id": "cooperation-crise", "domaine": "Incidents", "criticite": "haute",
        "titre": "Coopération en gestion de crise et préservation des preuves",
        "fondement": ["NIS 2, art. 21.2.b", "DORA, art. 30.3", "RGPD, art. 28.3.f"],
        "objectif": "Obtenir des moyens, pas seulement une information.",
        "modele": "Le Prestataire participe aux cellules de crise du Client, met à "
                  "disposition les ressources techniques nécessaires à "
                  "l'investigation, préserve les journaux et éléments de preuve "
                  "pendant [n] mois et s'abstient de toute action susceptible "
                  "d'altérer les traces sans accord écrit du Client.",
        "risque": "Un prestataire qui réinstalle un serveur compromis « pour rétablir "
                  "le service » détruit les preuves nécessaires à la qualification "
                  "de l'incident et à sa notification.",
    },
    {
        "id": "audit", "domaine": "Contrôle", "criticite": "haute",
        "titre": "Droit d'audit et d'inspection, y compris par le régulateur",
        "fondement": ["RGPD, art. 28.3.h", "DORA, art. 30.3.e", "NIS 2, art. 21.2.d"],
        "objectif": "Pouvoir vérifier, et permettre à l'autorité de vérifier.",
        "modele": "Le Client, ses auditeurs mandatés et les autorités compétentes "
                  "disposent d'un droit d'audit et d'inspection sur pièces et sur "
                  "place, [n] fois par an et sans limitation en cas d'incident, "
                  "moyennant un préavis de [15] jours ouvrés, ramené à [24] heures "
                  "en cas d'incident de sécurité. Le Prestataire répond aux "
                  "questionnaires de sécurité sous [20] jours.",
        "risque": "Une clause limitée à « la production d'un rapport de "
                  "certification » ne satisfait ni l'art. 28.3.h du RGPD ni "
                  "l'art. 30.3.e de DORA, qui exigent un accès effectif.",
    },
    {
        "id": "sous-traitance", "domaine": "Chaîne", "criticite": "haute",
        "titre": "Encadrement de la sous-traitance ultérieure",
        "fondement": ["RGPD, art. 28.2 et 28.4", "DORA, art. 30.2.a", "NIS 2, art. 21.2.d"],
        "objectif": "Garder la maîtrise de la chaîne au-delà du premier rang.",
        "modele": "Le Prestataire ne recourt à un sous-traitant ultérieur qu'après "
                  "information écrite du Client, qui dispose d'un délai de [30] jours "
                  "pour s'y opposer pour un motif tenant à la sécurité ou à la "
                  "conformité. Il impose contractuellement à ses sous-traitants des "
                  "obligations au moins équivalentes et demeure pleinement "
                  "responsable de leur exécution. La liste des sous-traitants et "
                  "leurs localisations est tenue à jour en Annexe.",
        "risque": "L'essentiel des incidents de chaîne d'approvisionnement provient "
                  "du deuxième ou du troisième rang, hors de tout engagement direct.",
    },
    {
        "id": "localisation", "domaine": "Données", "criticite": "haute",
        "titre": "Localisation des données et des traitements",
        "fondement": ["RGPD, chap. V", "DORA, art. 30.2.b"],
        "objectif": "Maîtriser les transferts et l'exposition aux droits étrangers.",
        "modele": "Les Données sont hébergées et traitées exclusivement au sein de "
                  "[l'Union européenne]. Tout transfert hors de cette zone, y compris "
                  "un accès distant depuis un pays tiers à des fins de support, est "
                  "subordonné à l'accord écrit préalable du Client et à la mise en "
                  "place d'un mécanisme de transfert valide.",
        "risque": "Un support opéré depuis un pays tiers constitue un transfert au "
                  "sens du chapitre V, même sans copie de données.",
    },
    {
        "id": "acces-distant", "domaine": "OT", "criticite": "haute",
        "titre": "Accès distant et télémaintenance des installations industrielles",
        "fondement": ["IEC 62443-2-4", "IEC 62443-3-3 (SR 1.13, SR 2.6)",
                      "NIS 2, art. 21.2.i"],
        "objectif": "Encadrer le vecteur d'intrusion le plus fréquent en OT.",
        "modele": "Tout accès distant aux systèmes industriels transite par le "
                  "dispositif d'accès du Client, est nominatif, authentifié par "
                  "double facteur, ouvert à la demande pour une durée déterminée, "
                  "journalisé et enregistré. Le Prestataire s'interdit tout accès "
                  "permanent, tout modem ou routeur non déclaré et tout compte "
                  "partagé.",
        "risque": "Les liaisons de télémaintenance laissées ouvertes constituent la "
                  "porte d'entrée la plus courante vers les automates.",
    },
    {
        "id": "correctifs-ot", "domaine": "OT", "criticite": "moyenne",
        "titre": "Gestion des correctifs en environnement industriel",
        "fondement": ["IEC 62443-2-4", "CRA", "NIS 2, art. 21.2.e"],
        "objectif": "Concilier disponibilité de production et traitement des vulnérabilités.",
        "modele": "Le Prestataire qualifie les correctifs de sécurité sur plateforme "
                  "de test dans un délai de [30] jours à compter de leur publication, "
                  "notifie au Client les vulnérabilités critiques affectant les "
                  "équipements fournis sous [72] heures, et propose une mesure de "
                  "contournement lorsque l'application d'un correctif est impossible "
                  "sans arrêt de production.",
        "risque": "Sans engagement de qualification, un automate reste vulnérable "
                  "des années au motif que le correctif « n'est pas validé constructeur ».",
    },
    {
        "id": "surete-securite", "domaine": "OT", "criticite": "haute",
        "titre": "Non-régression de la sûreté fonctionnelle",
        "fondement": ["IEC 61511", "IEC 62443-3-2"],
        "objectif": "Empêcher qu'une mesure de cybersécurité dégrade une fonction de sécurité.",
        "modele": "Toute mesure de cybersécurité affectant un système instrumenté de "
                  "sécurité fait l'objet d'une analyse d'impact sur la sûreté "
                  "fonctionnelle, documentée et validée conjointement avant "
                  "déploiement. En cas de conflit, la fonction de sécurité prévaut et "
                  "une mesure compensatoire est recherchée.",
        "risque": "Un durcissement mal maîtrisé peut inhiber un arrêt d'urgence : le "
                  "risque déplacé est alors un risque humain.",
    },
    {
        "id": "ia-fournisseur", "domaine": "IA", "criticite": "haute",
        "titre": "Usage d'intelligence artificielle par le prestataire",
        "fondement": ["Règlement (UE) 2024/1689, art. 25 et 50", "RGPD, art. 28.3.a"],
        "objectif": "Savoir si une IA intervient, et à quelles conditions.",
        "modele": "Le Prestataire déclare en Annexe tout système d'IA utilisé dans "
                  "l'exécution des Services, sa finalité et son fournisseur. Il "
                  "s'interdit d'utiliser les Données du Client pour entraîner, "
                  "réentraîner ou améliorer un modèle sans accord écrit préalable. "
                  "Il informe le Client de toute modification substantielle au sens "
                  "de l'art. 25 du règlement (UE) 2024/1689 et fournit les éléments "
                  "nécessaires au respect des obligations de transparence de l'art. 50.",
        "risque": "L'usage non déclaré d'un service d'IA transforme une prestation "
                  "en transfert de données et peut faire basculer le client dans le "
                  "statut de fournisseur au sens de l'art. 25.",
    },
    {
        "id": "ia-responsabilites", "domaine": "IA", "criticite": "moyenne",
        "titre": "Répartition des rôles au sens de l'IA Act",
        "fondement": ["Règlement (UE) 2024/1689, art. 3, 16, 25 et 26"],
        "objectif": "Qualifier expressément qui est fournisseur et qui est déployeur.",
        "modele": "Les Parties conviennent que le Prestataire agit en qualité de "
                  "fournisseur au sens de l'art. 3.3 du règlement (UE) 2024/1689 et "
                  "le Client en qualité de déployeur au sens de l'art. 3.4. Le "
                  "Prestataire fournit la notice d'utilisation, les informations de "
                  "l'art. 13 et l'assistance nécessaire au contrôle humain de "
                  "l'art. 26. Toute évolution de cette qualification est notifiée "
                  "sans délai.",
        "risque": "La qualification n'est pas disponible : elle découle des faits. "
                  "Une clause contraire ne lie pas l'autorité, mais elle organise la "
                  "charge de la preuve et les recours entre les parties.",
    },
    {
        "id": "reversibilite", "domaine": "Sortie", "criticite": "haute",
        "titre": "Réversibilité et assistance à la migration",
        "fondement": ["Data Act, chapitre sur le changement de fournisseur",
                      "DORA, art. 28.8", "RGPD, art. 28.3.g"],
        "objectif": "Pouvoir sortir sans dépendre du bon vouloir du prestataire.",
        "modele": "À l'expiration ou à la résiliation du Contrat, le Prestataire "
                  "assure pendant [6] mois une assistance à la réversibilité "
                  "comprenant l'export des Données dans un format structuré et "
                  "couramment utilisé, la documentation des paramétrages et le "
                  "transfert de connaissance. Il restitue puis supprime les Données "
                  "et en atteste par écrit. Aucun frais de transfert de données ne "
                  "peut être facturé au-delà de ce que permet le règlement (UE) 2023/2854.",
        "risque": "Une réversibilité non préparée fait durer un contrat non "
                  "satisfaisant faute de pouvoir en sortir — et le prix de sortie "
                  "se négocie alors en position de faiblesse.",
    },
    {
        "id": "continuite", "domaine": "Continuité", "criticite": "haute",
        "titre": "Continuité d'activité et objectifs de reprise",
        "fondement": ["NIS 2, art. 21.2.c", "DORA, art. 11 et 12", "ISO 22301"],
        "objectif": "Traduire la continuité en engagements chiffrés et testés.",
        "modele": "Le Prestataire garantit un délai maximal d'interruption admissible "
                  "(RTO) de [n] heures et une perte de données maximale admissible "
                  "(RPO) de [n] heures. Il teste son plan de continuité au moins une "
                  "fois par an, en communique les résultats au Client et associe "
                  "celui-ci à un test conjoint tous les [n] ans.",
        "risque": "Un RTO annoncé mais jamais testé est une hypothèse, pas un "
                  "engagement — la première crise réelle en fait la démonstration.",
    },
    {
        "id": "responsabilite", "domaine": "Responsabilité", "criticite": "haute",
        "titre": "Plafond de responsabilité et exclusions",
        "fondement": ["Code civil, art. 1231-1 s.", "RGPD, art. 82", "Data Act "
                      "(clauses abusives entre entreprises)"],
        "objectif": "Éviter un plafond qui rend l'engagement de sécurité illusoire.",
        "modele": "La responsabilité du Prestataire est plafonnée à [x] fois le "
                  "montant des sommes versées au titre des [12] derniers mois. Ce "
                  "plafond est porté à [y] en cas de manquement aux obligations de "
                  "sécurité et de protection des données, et ne s'applique ni en cas "
                  "de faute lourde ou dolosive, ni aux dommages corporels, ni aux "
                  "sanctions administratives supportées par le Client du fait d'un "
                  "manquement imputable au Prestataire.",
        "risque": "Un plafond fixé à trois mois de redevance face à un risque de "
                  "sanction en pourcentage du chiffre d'affaires mondial revient à "
                  "conserver l'intégralité du risque tout en payant la prestation.",
    },
    {
        "id": "assurance", "domaine": "Responsabilité", "criticite": "moyenne",
        "titre": "Assurance cyber et responsabilité civile professionnelle",
        "fondement": ["Pratique de place ; exigé par plusieurs régimes sectoriels"],
        "objectif": "S'assurer que le plafond de responsabilité est solvable.",
        "modele": "Le Prestataire justifie annuellement d'une police d'assurance "
                  "couvrant sa responsabilité civile professionnelle et les risques "
                  "cyber à hauteur de [n] € par sinistre, et informe le Client de "
                  "toute résiliation ou modification substantielle.",
        "risque": "Un plafond de responsabilité élevé face à une société sans "
                  "assurance et sans fonds propres n'a aucune valeur pratique.",
    },
    {
        "id": "certifications", "domaine": "Contrôle", "criticite": "moyenne",
        "titre": "Certifications, attestations et maintien dans le temps",
        "fondement": ["Cybersecurity Act", "ISO/IEC 27001", "IEC 62443-2-4",
                      "SecNumCloud (le cas échéant)"],
        "objectif": "Obtenir une preuve maintenue, pas un certificat à la signature.",
        "modele": "Le Prestataire maintient pendant toute la durée du Contrat les "
                  "certifications listées en Annexe, communique chaque renouvellement "
                  "ainsi que le périmètre certifié, et informe le Client sous [15] "
                  "jours de toute suspension, retrait ou réduction de périmètre.",
        "risque": "Un certificat produit lors de l'appel d'offres peut couvrir un "
                  "périmètre sans rapport avec la prestation, ou avoir expiré.",
    },
    {
        "id": "personnel", "domaine": "Socle", "criticite": "moyenne",
        "titre": "Habilitation, formation et gestion des départs",
        "fondement": ["NIS 2, art. 21.2.g et 21.2.i", "RGPD, art. 28.3.b",
                      "IEC 62443-2-4"],
        "objectif": "Traiter le facteur humain, principal vecteur résiduel.",
        "modele": "Le Prestataire s'assure que les personnes intervenant sur les "
                  "systèmes du Client sont formées à la sécurité, tenues à une "
                  "obligation de confidentialité et habilitées selon le niveau requis. "
                  "Il notifie tout départ ou changement d'affectation dans les [24] "
                  "heures afin que les accès soient révoqués.",
        "risque": "Les comptes de prestataires partis restent actifs des mois : "
                  "c'est un constat récurrent des audits.",
    },
    {
        "id": "sbom", "domaine": "Chaîne", "criticite": "moyenne",
        "titre": "Nomenclature logicielle et suivi des vulnérabilités des composants",
        "fondement": ["CRA, annexe I", "NIS 2, art. 21.2.e", "IEC 62443-4-1"],
        "objectif": "Savoir ce qui compose la solution le jour où une bibliothèque est compromise.",
        "modele": "Le Prestataire fournit et tient à jour une nomenclature logicielle "
                  "(SBOM) au format [CycloneDX / SPDX] couvrant les composants "
                  "logiciels et leurs dépendances, et notifie au Client toute "
                  "vulnérabilité affectant ces composants selon la criticité.",
        "risque": "Sans nomenclature, l'annonce d'une faille majeure dans une "
                  "bibliothèque répandue laisse plusieurs jours d'incertitude sur "
                  "l'exposition réelle.",
    },
    {
        "id": "donnees-usage", "domaine": "Données", "criticite": "haute",
        "titre": "Limitation d'usage des données du client",
        "fondement": ["RGPD, art. 28.3.a", "Data Act", "Secret des affaires"],
        "objectif": "Interdire les usages secondaires non consentis.",
        "modele": "Le Prestataire traite les Données exclusivement sur instruction "
                  "documentée du Client et pour les seules finalités du Contrat. Il "
                  "s'interdit tout usage à des fins propres, notamment "
                  "d'amélioration de produit, de statistiques commercialisées, "
                  "d'entraînement de modèles ou de constitution de référentiels, "
                  "y compris sous forme agrégée ou anonymisée, sans accord écrit "
                  "distinct.",
        "risque": "La mention « données agrégées et anonymisées » couvre en pratique "
                  "des usages très étendus, dont la réversibilité est souvent "
                  "impossible une fois le modèle entraîné.",
    },
    {
        "id": "sla-securite", "domaine": "Contrôle", "criticite": "moyenne",
        "titre": "Indicateurs de sécurité et pénalités associées",
        "fondement": ["Pratique contractuelle ; DORA, art. 30.2.d"],
        "objectif": "Rendre l'engagement de sécurité mesurable et sanctionnable.",
        "modele": "Le Prestataire rend compte trimestriellement des indicateurs "
                  "définis en Annexe (délai de correction des vulnérabilités "
                  "critiques, taux de couverture des correctifs, délai de "
                  "notification, résultats des tests). Le non-respect ouvre droit aux "
                  "pénalités de l'Annexe, sans préjudice du droit à réparation.",
        "risque": "Une obligation de sécurité sans indicateur ni pénalité n'est "
                  "jamais priorisée face à une obligation de disponibilité qui, elle, "
                  "en comporte.",
    },
    {
        "id": "changement-controle", "domaine": "Chaîne", "criticite": "moyenne",
        "titre": "Changement de contrôle et transfert du contrat",
        "fondement": ["Pratique contractuelle ; DORA, art. 28.7"],
        "objectif": "Ne pas se retrouver lié à un acteur que l'on n'aurait pas retenu.",
        "modele": "Le Prestataire informe le Client de tout changement de contrôle, "
                  "de tout transfert d'activité et de tout changement de localisation "
                  "des traitements. Le Client peut résilier sans indemnité dans un "
                  "délai de [90] jours lorsque ce changement affecte la sécurité, la "
                  "conformité ou la souveraineté des Données.",
        "risque": "Le rachat d'un prestataire par un acteur soumis à une "
                  "législation extraterritoriale modifie l'analyse de transfert sans "
                  "qu'aucune donnée n'ait bougé.",
    },
]

DOMAINES_CLAUSIER = ["Socle", "Incidents", "Contrôle", "Chaîne", "Données",
                     "OT", "IA", "Continuité", "Sortie", "Responsabilité"]


def clausier(domaine=None, criticite=None):
    """Clauses du clausier, filtrées le cas échéant."""
    out = CLAUSIER
    if domaine:
        out = [c for c in out if c["domaine"] == domaine]
    if criticite:
        out = [c for c in out if c["criticite"] == criticite]
    return [dict(c) for c in out]


# ═══════════════════════════════════════════════════════════════════════════
# 4. POINTS D'INTERPRÉTATION OUVERTS
# ═══════════════════════════════════════════════════════════════════════════
#
# Ce que le client attend d'un conseil, ce n'est pas une réponse péremptoire :
# c'est de savoir OÙ le texte est discuté, quelles lectures s'affrontent et ce
# que chacune coûte. Ces points sont fournis au modèle comme matière première :
# il doit les mobiliser quand la question les touche, plutôt que trancher.
CONTROVERSES = [
    {
        "id": "ai-act-6-3",
        "textes": ["ai-act"],
        "question": "Jusqu'où peut-on invoquer la dérogation de l'art. 6(3) pour "
                    "un système relevant pourtant d'un domaine de l'annexe III ?",
        "lectures": [
            {"nom": "Lecture stricte", "these":
             "La dérogation ne joue que pour des fonctions manifestement "
             "accessoires ; dès que la sortie du système alimente la décision, "
             "elle est écartée.",
             "consequence": "Traiter le système comme haut risque et engager la "
                            "documentation complète."},
            {"nom": "Lecture fonctionnelle", "these":
             "La dérogation joue dès lors que le système n'exerce aucune influence "
             "déterminante sur le résultat de la décision, ce qui s'apprécie au cas "
             "par cas.",
             "consequence": "Documenter l'évaluation avant mise sur le marché et "
                            "procéder à l'enregistrement prévu à l'art. 49.2."},
        ],
        "arbitrage": "Le point commun aux deux lectures est la charge de la preuve : "
                     "elle pèse sur celui qui invoque la dérogation. Une évaluation "
                     "documentée avant mise sur le marché est donc utile dans les "
                     "deux cas, et le profilage de personnes physiques exclut la "
                     "dérogation sans discussion.",
    },
    {
        "id": "ai-act-25-modif",
        "textes": ["ai-act"],
        "question": "À partir de quand un déployeur qui adapte un système d'IA "
                    "devient-il fournisseur au sens de l'art. 25 ?",
        "lectures": [
            {"nom": "Lecture par la destination", "these":
             "Seul un changement de destination ou une modification substantielle "
             "au sens de l'art. 3.23 fait basculer le statut ; le paramétrage et "
             "l'affinage sur données propres n'y suffisent pas.",
             "consequence": "Le déployeur conserve ses obligations de l'art. 26."},
            {"nom": "Lecture par la maîtrise", "these":
             "Dès lors que l'adaptation modifie le comportement du système au point "
             "d'en altérer les performances déclarées, le déployeur assume la "
             "responsabilité du fournisseur.",
             "consequence": "Bascule vers les obligations du chapitre III, "
                            "section 2 — documentation, conformité, marquage."},
        ],
        "arbitrage": "Le risque étant asymétrique, l'usage est de documenter "
                     "précisément la nature des adaptations et de faire porter au "
                     "contrat l'obligation du fournisseur d'origine de notifier tout "
                     "élément susceptible de déclencher la bascule.",
    },
    {
        "id": "nis2-chaine",
        "textes": ["nis2"],
        "question": "Que doit-on exactement imposer à ses fournisseurs au titre de "
                    "l'art. 21.2.d ?",
        "lectures": [
            {"nom": "Lecture par l'analyse de risque", "these":
             "Le texte impose d'apprécier le risque fournisseur et d'en tirer des "
             "mesures proportionnées ; il n'impose pas de clause type.",
             "consequence": "Une cartographie des fournisseurs critiques et des "
                            "exigences différenciées suffisent."},
            {"nom": "Lecture par la cascade contractuelle", "these":
             "L'effectivité de l'obligation suppose de répercuter les exigences par "
             "contrat jusqu'aux rangs pertinents de la chaîne.",
             "consequence": "Revue contractuelle systématique et avenants sur le "
                            "parc fournisseurs."},
        ],
        "arbitrage": "L'écart porte moins sur le principe que sur la profondeur. Une "
                     "position défendable consiste à segmenter : cascade "
                     "contractuelle complète pour les fournisseurs critiques, "
                     "exigences allégées et vérifiées par questionnaire au-delà.",
    },
    {
        "id": "nis2-dirigeants",
        "textes": ["nis2"],
        "question": "Quelle est la portée réelle de la responsabilité des organes de "
                    "direction (art. 20) ?",
        "lectures": [
            {"nom": "Lecture formelle", "these":
             "L'obligation porte sur l'approbation des mesures et le suivi de leur "
             "mise en œuvre ; elle est satisfaite par une délibération documentée.",
             "consequence": "Formaliser l'approbation en conseil et tracer la "
                            "formation des dirigeants."},
            {"nom": "Lecture par l'effectivité", "these":
             "L'approbation d'un dispositif manifestement insuffisant, ou son "
             "absence de suivi, engage personnellement les dirigeants.",
             "consequence": "Documenter les arbitrages de moyens et les risques "
                            "acceptés, pas seulement la décision."},
        ],
        "arbitrage": "Les deux lectures convergent sur un point opérationnel : ce "
                     "qui protège n'est pas l'approbation elle-même mais la trace "
                     "de l'instruction — risques présentés, options écartées, "
                     "moyens alloués.",
    },
    {
        "id": "rgpd-llm-role",
        "textes": ["rgpd", "ai-act"],
        "question": "Le fournisseur d'un grand modèle de langage est-il sous-traitant "
                    "au sens de l'art. 28 du RGPD ?",
        "lectures": [
            {"nom": "Sous-traitance", "these":
             "Le fournisseur traite les données pour le compte du client et sur ses "
             "instructions : le régime de l'art. 28 s'applique intégralement.",
             "consequence": "Contrat de sous-traitance, encadrement de la "
                            "sous-traitance ultérieure, droit d'audit effectif."},
            {"nom": "Responsabilité conjointe ou autonome", "these":
             "Dès lors que le fournisseur détermine seul des finalités propres — "
             "amélioration du modèle, sécurité, statistiques — il agit comme "
             "responsable pour ces traitements.",
             "consequence": "Cartographier traitement par traitement et prévoir un "
                            "double régime dans le contrat."},
        ],
        "arbitrage": "La qualification suit les faits et non la clause. La démarche "
                     "sûre consiste à interdire contractuellement tout usage propre "
                     "des données : la question du double régime disparaît alors "
                     "d'elle-même.",
    },
    {
        "id": "rgpd-22-humain",
        "textes": ["rgpd", "ai-act"],
        "question": "À partir de quand une revue humaine suffit-elle à faire sortir "
                    "une décision du champ de l'art. 22 du RGPD ?",
        "lectures": [
            {"nom": "Lecture formelle", "these":
             "Dès qu'un agent valide la décision avant son exécution, celle-ci n'est "
             "plus fondée EXCLUSIVEMENT sur un traitement automatisé : la première "
             "des trois conditions cumulatives tombe et l'art. 22 ne s'applique pas.",
             "consequence": "Un point de validation dans le flux, et le régime de "
                            "l'art. 22 est réputé écarté."},
            {"nom": "Lecture substantielle", "these":
             "L'intervention ne compte que si elle est SIGNIFICATIVE : un humain "
             "compétent, qui accède aux données et aux motifs, comprend la logique du "
             "score et dispose du pouvoir réel de confirmer, modifier ou annuler. Une "
             "validation qui entérine le calcul sans pouvoir le contredire laisse la "
             "décision dans le champ de l'article.",
             "consequence": "Documenter la compétence du réviseur, son accès aux "
                            "éléments, son pouvoir de réformation et la traçabilité de "
                            "chaque revue — faute de quoi les garanties du § 3 restent "
                            "dues."},
        ],
        "arbitrage": "La lecture substantielle est celle des autorités. Le contrôle "
                     "utile n'est pas « y a-t-il un humain ? » mais « peut-on démontrer "
                     "qu'il comprend, réexamine et peut modifier ? ». La charge de la "
                     "preuve pèse sur le responsable de traitement : sans trace de "
                     "revue, l'intervention est réputée absente. Le raisonnement vaut "
                     "au-delà du crédit — assurance, fraude, notation client, accès à "
                     "un service, désactivation de compte.",
    },
    {
        "id": "cra-ai-act",
        "textes": ["cra", "ai-act"],
        "question": "Un produit industriel intégrant de l'IA doit-il subir deux "
                    "évaluations de conformité ?",
        "lectures": [
            {"nom": "Cumul", "these":
             "Les deux règlements poursuivent des objectifs distincts — sécurité du "
             "produit numérique d'une part, risques de l'IA d'autre part — et "
             "s'appliquent cumulativement.",
             "consequence": "Deux référentiels d'exigences, une documentation "
                            "technique consolidée."},
            {"nom": "Intégration", "these":
             "L'IA Act prévoit l'articulation avec la législation d'harmonisation "
             "existante afin d'éviter la duplication : une procédure unique peut "
             "couvrir les deux volets.",
             "consequence": "Évaluation intégrée, sous réserve que tous les points "
                            "de contrôle soient couverts."},
        ],
        "arbitrage": "En pratique, la documentation technique se construit une fois "
                     "et se présente deux fois. Le point de vigilance est la "
                     "traçabilité de la couverture : montrer, exigence par exigence, "
                     "où elle est traitée.",
    },
    {
        "id": "plafond-sanctions",
        "textes": ["nis2", "rgpd", "dora"],
        "question": "Une clause plafonnant la responsabilité du prestataire peut-elle "
                    "couvrir les sanctions administratives infligées au client ?",
        "lectures": [
            {"nom": "Liberté contractuelle", "these":
             "Entre professionnels, le plafond est valable et s'applique, sauf faute "
             "lourde ou dolosive.",
             "consequence": "Le client conserve le risque au-delà du plafond."},
            {"nom": "Limite d'ordre public", "these":
             "Une clause qui vide de sa substance l'obligation essentielle de "
             "sécurité peut être réputée non écrite, et le contrôle des clauses "
             "abusives entre entreprises se renforce.",
             "consequence": "Le plafond peut être écarté par le juge sur "
                            "l'obligation de sécurité."},
        ],
        "arbitrage": "L'issue étant incertaine, la pratique consiste à prévoir un "
                     "plafond spécifique et rehaussé pour les manquements à la "
                     "sécurité et à la protection des données, adossé à une "
                     "assurance justifiée — plutôt qu'à parier sur l'issue d'un litige.",
    },
    {
        "id": "62443-opposabilite",
        "textes": ["iec-62443", "nis2"],
        "question": "Une norme volontaire comme l'IEC 62443 devient-elle contraignante "
                    "par l'effet de NIS 2 ?",
        "lectures": [
            {"nom": "Norme de moyen", "these":
             "NIS 2 impose un résultat — des mesures appropriées et proportionnées — "
             "sans imposer de référentiel ; l'IEC 62443 n'est qu'un moyen parmi "
             "d'autres de l'atteindre.",
             "consequence": "Liberté de référentiel, à charge de démontrer "
                            "l'adéquation."},
            {"nom": "Standard de diligence", "these":
             "En environnement industriel, l'IEC 62443 constitue l'état de l'art "
             "reconnu : s'en écarter suppose de justifier une alternative au moins "
             "équivalente.",
             "consequence": "Le référentiel devient la référence implicite du "
                            "contrôle et de l'expertise judiciaire."},
        ],
        "arbitrage": "L'écart est faible en pratique : l'entité qui s'appuie sur "
                     "l'IEC 62443 démontre sa diligence plus facilement, celle qui "
                     "s'en écarte doit produire la démonstration d'équivalence.",
    },
]


def controverses(texte_ids=None):
    """Points d'interprétation ouverts, éventuellement restreints à des textes."""
    if not texte_ids:
        return [dict(c) for c in CONTROVERSES]
    s = set(texte_ids)
    return [dict(c) for c in CONTROVERSES if s & set(c["textes"])]


# ═══════════════════════════════════════════════════════════════════════════
# 5. AVERTISSEMENTS ET PROMPTS
# ═══════════════════════════════════════════════════════════════════════════

AVERTISSEMENT = (
    "Analyse documentaire produite avec l'assistance d'un système d'intelligence "
    "artificielle, sur la base du référentiel de textes version %s. Elle a pour "
    "objet d'éclairer une décision — état des textes, lectures possibles, risques "
    "et options — et ne constitue pas une consultation juridique au sens de la loi "
    "n° 71-1130 du 31 décembre 1971. Les références citées doivent être vérifiées "
    "sur les sources officielles indiquées avant tout engagement. Pour un acte "
    "juridique, un contentieux ou une décision à enjeu, l'intervention d'un avocat "
    "reste nécessaire." % VERSION_REFERENTIEL
)

MENTION_IA = (
    "Contenu généré par un système d'IA — information donnée au titre de "
    "l'article 50 du règlement (UE) 2024/1689."
)

SYSTEM_JURIDIQUE = """Tu es juriste senior en droit du numérique, spécialisé en cybersécurité (IT, OT/ICS), en intelligence artificielle et en contrats de services numériques. Tu rédiges pour un dirigeant, un DSI, un RSSI ou un juriste d'entreprise : précis, sans jargon inutile, orienté décision.

MÉTHODE IMPOSÉE — tu suis cet ordre, sans exception :
1. QUALIFICATION — reformule la situation en termes juridiques : qui est qui (fournisseur, déployeur, sous-traitant, entité essentielle…), quel objet, quel territoire, quelle date d'appréciation.
2. TEXTES APPLICABLES — cite uniquement des textes figurant dans le RÉFÉRENTIEL AUTORISÉ ci-dessous ou dans les EXTRAITS fournis. Pour chacun : la référence exacte, l'article pertinent, ce qu'il impose.
3. LECTURES POSSIBLES — c'est le cœur de ton travail. Lorsque le texte n'est pas univoque, expose au moins deux lectures défendables. Pour chacune : son fondement (lettre du texte, finalité, position d'autorité, pratique de place), sa conséquence concrète, et ce qu'elle coûte si elle est retenue à tort. N'invente jamais un consensus qui n'existe pas ; ne masque jamais une incertitude derrière une affirmation.
4. RISQUE — apprécie le risque réel : nature (sanction administrative, responsabilité civile, contentieux, réputation), ordre de grandeur lorsqu'il est fixé par le texte, probabilité de contrôle, délai.
5. RECOMMANDATION — une position argumentée, assumée, avec ses conditions. Si deux options sont soutenables, dis laquelle tu retiendrais et pourquoi ; ne renvoie pas le lecteur à son propre arbitrage sans l'éclairer.
6. À FAIRE — actions concrètes, ordonnées, avec l'acteur et l'échéance quand ils se déduisent du texte.
7. RÉSERVES — ce que tu ne peux pas trancher en l'état, quelles pièces ou quelle vérification y répondraient.

RÈGLES ABSOLUES :
- N'INVENTE JAMAIS une référence. Pas de numéro d'article, de considérant, de décision ou de date qui ne figure pas dans le référentiel autorisé ou dans les extraits. Si la réponse suppose un texte que tu n'as pas, écris-le : « ce point suppose de vérifier [texte] ».
- Ne cite JAMAIS de jurisprudence, de décision d'autorité ou de ligne directrice par un numéro ou une date que tu n'as pas sous les yeux. Tu peux mentionner l'existence d'une position, sans lui prêter une référence précise.
- Distingue systématiquement ce qui est OBLIGATOIRE (texte contraignant), ce qui est ATTENDU (position d'autorité, état de l'art) et ce qui est PRUDENT (pratique).
- Quand une date d'application est en cause, indique-la : le droit applicable dépend de la date d'appréciation.
- Quand un texte est en cours de transposition ou d'évolution, signale-le et recommande la vérification.
- Écris en français, en texte structuré avec des intertitres courts. Pas de flatterie, pas de préambule sur ce que tu vas faire.
- N'utilise pas de tableau lorsque deux phrases suffisent ; utilise-en un pour comparer des lectures ou des obligations parallèles.

Tu termines TOUJOURS par la section RÉSERVES, puis rien d'autre : l'avertissement légal est ajouté par l'application, ne le reproduis pas."""


def _bloc_referentiel(textes):
    """Liste des références AUTORISÉES, transmise au modèle. C'est le garde-fou
    principal : le modèle ne dispose que de cette matière pour citer."""
    lignes = []
    for t in textes:
        t = _INDEX.get(t) if isinstance(t, str) else t
        if not t:
            continue
        jal = " ; ".join(t.get("jalons", [])[:4])
        lignes.append("- %s — %s%s" % (t["titre"], t["officiel"],
                                       (" (%s)" % jal) if jal else ""))
    return "\n".join(lignes)


def _bloc_jurisprudence(decisions):
    """Les décisions rapportées, mises sous les yeux du modèle.

    Le connecteur est OPTIONNEL : `juridique.py` est partagé à l'identique entre
    deux applications, et doit rester importable dans celle qui ne l'embarque
    pas. Sans lui, il n'y a simplement pas de bloc — donc pas de levée
    d'interdiction, ce qui est l'état antérieur et un état sûr."""
    if not decisions or librejustice is None:
        return ""
    if isinstance(decisions, str):
        return decisions
    vise = None
    if isinstance(decisions, dict):
        vise = decisions.get("vise")
        decisions = decisions.get("decisions") or []
    return librejustice.bloc_prompt(decisions, vise=vise)


def _bloc_controverses(textes_ids):
    c = controverses(textes_ids)
    if not c:
        return ""
    out = ["POINTS D'INTERPRÉTATION OUVERTS connus sur ces textes — mobilise-les "
           "si la question les touche, en présentant les lectures et non une "
           "conclusion tranchée :"]
    for x in c:
        out.append("• %s" % x["question"])
        for l in x["lectures"]:
            out.append("   – %s : %s → %s" % (l["nom"], l["these"], l["consequence"]))
        out.append("   – Arbitrage usuel : %s" % x["arbitrage"])
    return "\n".join(out)


def prompt_analyse(question, profil=None, extraits=None, textes_ids=None,
                   jurisprudence=None):
    """Construit le message utilisateur d'une analyse juridique.

    `extraits` : passages issus de la base documentaire (RAG), déjà numérotés.
    `textes_ids` : identifiants du référentiel retenus par la qualification ;
    à défaut, tout le référentiel est autorisé — mais un périmètre restreint
    donne des réponses nettement plus précises.
    `jurisprudence` : décisions rapportées du corpus LibreJustice pour CETTE
    question. Leur présence lève, pour elles seules, l'interdiction de citer une
    décision posée par SYSTEM_JURIDIQUE ; leur absence la laisse entière. La
    levée est écrite ici et non dans le système précisément pour cela : un
    message sans décisions ne la porte pas.
    """
    qual = qualifier(profil) if profil else None
    if not textes_ids and qual:
        textes_ids = [x["id"] for x in qual["applicables"]] + \
                     [x["id"] for x in qual["a_verifier"]]
    textes_ids = textes_ids or [t["id"] for t in REFERENTIEL]

    parties = []
    if qual:
        parties.append("QUALIFICATION DÉTERMINISTE déjà établie par l'application "
                       "(règles explicites, sans IA) — reprends-la, ne la refais pas :")
        for x in qual["applicables"]:
            parties.append("- [applicable] %s : %s" % (x["titre"], " ".join(x["motifs"])))
        for x in qual["a_verifier"]:
            parties.append("- [à confirmer] %s : %s" % (x["titre"], " ".join(x["motifs"])))
        parties.append("")

    parties.append("RÉFÉRENTIEL AUTORISÉ — seules ces références peuvent être citées :")
    parties.append(_bloc_referentiel(textes_ids))
    parties.append("")

    bc = _bloc_controverses(textes_ids)
    if bc:
        parties.append(bc)
        parties.append("")

    bj = _bloc_jurisprudence(jurisprudence)
    if bj:
        parties.append(bj)
        parties.append("")

    if extraits:
        parties.append("EXTRAITS DE LA BASE DOCUMENTAIRE — prioritaires sur tes "
                       "connaissances générales ; cite-les entre crochets [1], [2] :")
        parties.append(extraits if isinstance(extraits, str) else "\n\n".join(extraits))
        parties.append("")

    parties.append("QUESTION POSÉE :")
    parties.append(str(question or "").strip()[:4000])
    return "\n".join(parties)


def prompt_contrat(texte_contrat, profil=None, domaines=None):
    """Analyse d'un contrat de services fournisseur, clause par clause.

    Le clausier sert de grille : le modèle ne cherche pas « ce qui lui semble
    manquer », il vérifie une liste fermée dont chaque entrée porte son
    fondement. Une revue est ainsi reproductible d'un contrat à l'autre.
    """
    grille = [c for c in CLAUSIER if not domaines or c["domaine"] in domaines]
    lignes = []
    for c in grille:
        lignes.append("• [%s] %s (criticité %s)\n   fondement : %s\n   objectif : %s"
                      % (c["id"], c["titre"], c["criticite"],
                         " ; ".join(c["fondement"]), c["objectif"]))
    qual = qualifier(profil) if profil else None
    ctx = ""
    if qual:
        ctx = ("CONTEXTE DU CLIENT (qualification déterministe) : "
               + " ; ".join("%s — %s" % (x["titre"], x["motifs"][0])
                            for x in qual["applicables"][:8]) + "\n\n")
    return (ctx +
            "GRILLE D'ANALYSE — vérifie le contrat point par point sur cette liste "
            "fermée, dans cet ordre :\n" + "\n".join(lignes) +
            "\n\nPour CHAQUE point de la grille, indique :\n"
            "  - PRÉSENT / PARTIEL / ABSENT, avec la citation exacte de la clause "
            "du contrat qui le traite (entre guillemets, telle quelle) ;\n"
            "  - si PARTIEL ou ABSENT : l'écart précis, le risque encouru par le "
            "client, et une formulation de remplacement prête à négocier ;\n"
            "  - lorsque la clause existe mais est défavorable, les deux lectures "
            "possibles de sa portée et laquelle un juge retiendrait vraisemblablement.\n"
            "Termine par : les TROIS points à obtenir en priorité, les points "
            "négociables, et ce qui peut être concédé sans risque.\n\n"
            "CONTRAT SOUMIS :\n" + str(texte_contrat or "")[:60000])


# ═══════════════════════════════════════════════════════════════════════════
# 6. CONTRÔLE DES CITATIONS — détection des références inventées
# ═══════════════════════════════════════════════════════════════════════════
#
# Dernière ligne de défense, et la plus utile : un modèle qui invente
# « Règlement (UE) 2023/1234 » produit un texte parfaitement crédible. On extrait
# donc toutes les références normatives de la réponse et on les confronte au
# référentiel. Ce contrôle est déterministe et ne coûte rien.

_RE_UE = re.compile(
    r"(?:R[eè]glement|Directive)\s*(?:d[ée]l[ée]gu[ée]\s*)?\((?:UE|CE)\)\s*"
    r"(?:n[°o]\s*)?(\d{4}/\d{1,4}|\d{1,4}/\d{4})", re.I)
_RE_LOI = re.compile(r"[Ll]oi\s+n[°o]\s*(\d{2,4}-\d{1,5})")
_RE_ISO = re.compile(r"ISO(?:/IEC)?\s*(\d{4,5})", re.I)
_RE_IEC = re.compile(r"(?:IEC|CEI)\s*(\d{4,5})", re.I)


def _normaliser(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


@functools.lru_cache(maxsize=1)
def _references_connues():
    """Toutes les références citables, sous forme normalisée.

    Mémoïsée : pure, sans argument, sur un référentiel constant de module —
    et rappelée à chaque analyse, chaque contrat, chaque export. Les trois
    ensembles rendus ne sont jamais mutés par les appelants (tests
    d'appartenance seulement)."""
    ue, lois, normes = set(), set(), set()
    for t in REFERENTIEL:
        blob = t.get("officiel", "") + " " + t.get("titre", "")
        for m in _RE_UE.finditer(blob):
            ue.add(_num_ue(m.group(1)))
        for m in _RE_LOI.finditer(blob):
            lois.add(m.group(1))
        for m in _RE_ISO.finditer(blob):
            normes.add(m.group(1))
        for m in _RE_IEC.finditer(blob):
            normes.add(m.group(1))
        if t.get("celex"):
            # 32024R1689 -> 2024/1689
            c = t["celex"]
            if len(c) >= 9:
                ue.add("%s/%s" % (c[1:5], c[6:].lstrip("0")))
    return ue, lois, normes


def _num_ue(n):
    """« 2024/1689 » et « 910/2014 » désignent la même chose selon l'époque :
    on ramène tout à année/numéro pour comparer."""
    a, b = n.split("/")
    if len(a) == 4 and a.isdigit() and int(a) > 1950:
        return "%s/%s" % (a, b.lstrip("0"))
    return "%s/%s" % (b, a.lstrip("0"))


# Références citables sans figurer au référentiel : textes généraux dont la
# mention est banale et sans risque (codes français, normes de la série 62443).
_TOLERES_NORMES = {"62443", "61508", "61511", "27001", "27002", "27005", "27036",
                   "27017", "27018", "27701", "22301", "31000", "42001", "23894",
                   "9001", "62351", "61850", "42005", "5338"}


def verifier_citations(reponse, textes_ids=None):
    """Confronte les références citées au référentiel.

    Renvoie {ok, suspectes, connues}. `suspectes` liste les références qui ne
    correspondent à aucun texte connu : ce sont les candidates à l'invention, à
    signaler à l'utilisateur plutôt qu'à masquer.
    """
    txt = reponse or ""
    ue_ok, lois_ok, normes_ok = _references_connues()
    if textes_ids:
        # Restreindre au périmètre autorisé rendrait le contrôle plus sévère,
        # mais signalerait à tort une référence exacte hors périmètre. On
        # contrôle donc l'EXISTENCE, pas la pertinence.
        pass
    suspectes, connues = [], []
    for m in _RE_UE.finditer(txt):
        n = _num_ue(m.group(1))
        (connues if n in ue_ok else suspectes).append(
            {"type": "texte européen", "brut": m.group(0), "cle": n})
    for m in _RE_LOI.finditer(txt):
        n = m.group(1)
        (connues if n in lois_ok else suspectes).append(
            {"type": "loi française", "brut": m.group(0), "cle": n})
    for rx, lib in ((_RE_ISO, "norme ISO"), (_RE_IEC, "norme IEC")):
        for m in rx.finditer(txt):
            n = m.group(1)
            ok = n in normes_ok or n in _TOLERES_NORMES
            (connues if ok else suspectes).append(
                {"type": lib, "brut": m.group(0), "cle": n})
    # Dédoublonnage : une même référence citée dix fois ne vaut qu'un signalement.
    def uniq(lst):
        vu, out = set(), []
        for x in lst:
            k = (x["type"], x["cle"])
            if k not in vu:
                vu.add(k)
                out.append(x)
        return out
    suspectes, connues = uniq(suspectes), uniq(connues)
    return {"ok": not suspectes, "suspectes": suspectes, "connues": connues}


def post_traiter(reponse, textes_ids=None, jurisprudence=None):
    """Réponse enrichie : contrôle des citations + avertissements réglementaires.

    `jurisprudence` : les décisions effectivement montrées au modèle. Le contrôle
    des décisions citées n'a de sens que contre cette liste — et il vaut AUSSI
    quand elle est vide : sans décision rapportée, l'interdiction générale n'a
    pas été levée, et tout numéro de pourvoi apparaissant dans la réponse est,
    par construction, inventé."""
    ctrl = verifier_citations(reponse, textes_ids)
    out = {
        "texte": reponse,
        "citations": ctrl,
        "avertissement": AVERTISSEMENT,
        "mention_ia": MENTION_IA,
        "version_referentiel": VERSION_REFERENTIEL,
    }
    if librejustice is not None:
        decisions = jurisprudence
        if isinstance(decisions, dict):
            decisions = decisions.get("decisions") or []
        out["jurisprudence"] = librejustice.verifier_jurisprudence(reponse, decisions)
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 7. QUESTIONS FRÉQUENTES — amorces proposées à l'utilisateur
# ═══════════════════════════════════════════════════════════════════════════
SUGGESTIONS = [
    {"groupe": "IA Act", "q": "Notre outil d'IA de tri de candidatures relève-t-il "
                              "de l'annexe III, et pouvons-nous invoquer la dérogation "
                              "de l'art. 6(3) ?"},
    {"groupe": "IA Act", "q": "Nous affinons un modèle du marché sur nos propres "
                              "données : devenons-nous fournisseur au sens de l'art. 25 ?"},
    {"groupe": "NIS 2", "q": "Sommes-nous entité essentielle ou importante, et "
                             "qu'est-ce que cela change concrètement ?"},
    {"groupe": "NIS 2", "q": "Que devons-nous exiger de nos fournisseurs au titre de "
                             "la sécurité de la chaîne d'approvisionnement ?"},
    {"groupe": "Contrats", "q": "Notre prestataire d'infogérance refuse le droit "
                                "d'audit sur place et propose son rapport de "
                                "certification : est-ce suffisant ?"},
    {"groupe": "Contrats", "q": "Le plafond de responsabilité proposé couvre-t-il "
                                "les sanctions que nous encourrions du fait du "
                                "prestataire ?"},
    {"groupe": "OT / ICS", "q": "La télémaintenance de nos automates par le "
                                "constructeur est-elle conforme à nos obligations ?"},
    {"groupe": "OT / ICS", "q": "L'IEC 62443 nous est-elle opposable alors qu'il "
                                "s'agit d'une norme volontaire ?"},
    {"groupe": "Données", "q": "Notre prestataire peut-il utiliser nos données pour "
                               "entraîner ses modèles si elles sont anonymisées ?"},
    {"groupe": "Données", "q": "Un support technique assuré depuis un pays tiers "
                               "constitue-t-il un transfert de données ?"},
    {"groupe": "Produits", "q": "Nous intégrons un composant logiciel tiers dans un "
                                "équipement industriel : quelles obligations au titre "
                                "du Cyber Resilience Act ?"},
    {"groupe": "DORA", "q": "Nous sommes prestataire d'un établissement financier : "
                            "quelles clauses DORA vont nous être imposées ?"},
]


# ═══════════════════════════════════════════════════════════════════════════
# 8. NOTE D'ARBITRAGE — préparer une décision, pas seulement l'éclairer
# ═══════════════════════════════════════════════════════════════════════════
#
# Une analyse juridique répond à « qu'est-ce que dit le droit ? ». Ce n'est pas
# la question d'un comité de direction : la sienne est « que décide-t-on, qui
# décide, et avant quand ? ». Entre les deux, il y a les heures passées à
# éplucher un dossier, à en extraire ce qui compte et à le mettre en forme.
#
# Trois choses sont produites ici, et une seule vient du modèle :
#
#   1. LE ROUTAGE — qui tranche, qui doit être consulté, qui est informé. Cela
#      ne s'invente pas : quand le texte réserve une décision à un organe
#      précis, s'en écarter est un manquement, pas un choix d'organisation.
#      L'article 20 de NIS 2 impose que l'organe de direction APPROUVE les
#      mesures de gestion des risques ; l'article 38.1 du RGPD impose que le
#      délégué soit associé « en temps utile » ; l'article 28.8 de DORA réserve
#      l'approbation des stratégies de sortie. Un modèle de langage qui
#      distribuerait ces rôles au jugé produirait une note crédible et fausse.
#      C'est donc un moteur de règles, comme la qualification.
#
#   2. LES ÉCHÉANCES — 24 h, 72 h, un mois. Une échéance réglementaire ne se
#      négocie pas avec l'agenda des participants : elle commande la réunion.
#      Elle est donc calculée, datée quand un point de départ est fourni, et
#      placée en tête de la note.
#
#   3. LA SYNTHÈSE, LES OPTIONS, LA RECOMMANDATION — là seulement intervient le
#      modèle, sur le dossier réellement fourni, avec obligation de citer ses
#      sources et d'assumer une position.

# --- Instances : qui peut trancher quoi -----------------------------------
INSTANCES = {
    "organe-direction": {
        "libelle": "Organe de direction (conseil, comité exécutif)",
        "role": "Approuve ce que le texte lui réserve expressément et assume le "
                "risque résiduel accepté. Sa responsabilité peut être engagée "
                "personnellement.",
    },
    "direction-generale": {
        "libelle": "Direction générale",
        "role": "Arbitre l'équilibre risque / coût / délai et engage "
                "l'organisation vis-à-vis des tiers.",
    },
    "direction-juridique": {
        "libelle": "Direction juridique",
        "role": "Qualifie la situation, fixe la position contractuelle et la "
                "stratégie face à une autorité ou à un contradicteur.",
    },
    "dpo": {
        "libelle": "Délégué à la protection des données",
        "role": "Doit être associé en temps utile à toute question touchant aux "
                "données personnelles (art. 38.1 du RGPD). Consulté — il ne "
                "décide pas, et son avis divergent doit être tracé.",
    },
    "rssi": {
        "libelle": "RSSI / responsable de la sécurité",
        "role": "Apprécie le risque technique, propose les mesures et instruit "
                "l'acceptation d'un écart.",
    },
    "dsi": {
        "libelle": "DSI",
        "role": "Se prononce sur la faisabilité, le calendrier et les ressources.",
    },
    "surete": {
        "libelle": "Responsable sûreté de fonctionnement",
        "role": "Se prononce dès qu'une mesure touche une fonction instrumentée "
                "de sécurité. En cas de conflit, la sûreté prévaut.",
    },
    "metier": {
        "libelle": "Direction métier concernée",
        "role": "Porte l'impact opérationnel et la priorisation.",
    },
    "achats": {
        "libelle": "Direction des achats",
        "role": "Conduit la négociation fournisseur et la sortie de contrat.",
    },
    "avocat": {
        "libelle": "Avocat / conseil externe",
        "role": "Nécessaire pour un acte juridique, un contentieux ou une "
                "position à fort enjeu (loi n° 71-1130 du 31 décembre 1971).",
    },
    "autorite": {
        "libelle": "Autorité compétente",
        "role": "Destinataire d'une notification ou d'une consultation "
                "préalable. Ce n'est pas un arbitrage interne : c'est une "
                "échéance qui s'impose au calendrier.",
    },
}

# --- Nature du dossier : ce sur quoi porte l'arbitrage ---------------------
NATURES_DOSSIER = [
    ("incident-securite", "Incident de sécurité en cours ou récent"),
    ("violation-donnees", "Violation de données à caractère personnel"),
    ("mesure-securite", "Mesure de sécurité à décider, ou écart à accepter"),
    ("contrat-fournisseur", "Contrat fournisseur : signature, renouvellement, avenant"),
    ("sortie-reversibilite", "Sortie de contrat, réversibilité, changement de prestataire"),
    ("projet-ia", "Mise en service d'un système d'intelligence artificielle"),
    ("modification-ia", "Modification d'un système d'IA existant"),
    ("nouveau-traitement", "Nouveau traitement de données personnelles"),
    ("transfert-donnees", "Transfert de données hors Union européenne"),
    ("produit-numerique", "Produit comportant des éléments numériques mis sur le marché"),
    ("audit-controle", "Contrôle d'une autorité, audit client ou certification"),
    ("contentieux", "Litige, mise en demeure, contentieux"),
    ("appel-offres", "Appel d'offres, cahier des charges, réponse à consultation"),
]

# --- Échéances réglementaires ---------------------------------------------
# Une échéance ne se négocie pas avec l'agenda des participants : elle commande
# la réunion. Celles dont la durée exacte dépend de normes techniques encore
# mouvantes portent `a_verifier` — mieux vaut une échéance signalée à confirmer
# qu'un chiffre faux affiché avec aplomb.
DELAIS = [
    {"id": "rgpd-33", "declencheur": "violation-donnees", "duree": "72 heures",
     "quoi": "Notification de la violation à l'autorité de contrôle",
     "fondement": "RGPD, art. 33.1", "depart": "prise de connaissance de la violation",
     "autorite": "CNIL"},
    {"id": "rgpd-34", "declencheur": "violation-donnees", "duree": "dans les meilleurs délais",
     "quoi": "Communication aux personnes concernées si risque élevé pour leurs droits",
     "fondement": "RGPD, art. 34", "depart": "constat du risque élevé",
     "autorite": "—"},
    {"id": "nis2-23-alerte", "declencheur": "incident-securite", "duree": "24 heures",
     "quoi": "Alerte précoce au CSIRT / à l'autorité compétente",
     "fondement": "Directive (UE) 2022/2555, art. 23",
     "depart": "prise de connaissance de l'incident important", "autorite": "ANSSI"},
    {"id": "nis2-23-notif", "declencheur": "incident-securite", "duree": "72 heures",
     "quoi": "Notification d'incident (appréciation initiale, gravité, impact)",
     "fondement": "Directive (UE) 2022/2555, art. 23",
     "depart": "prise de connaissance de l'incident important", "autorite": "ANSSI"},
    {"id": "nis2-23-final", "declencheur": "incident-securite", "duree": "1 mois",
     "quoi": "Rapport final",
     "fondement": "Directive (UE) 2022/2555, art. 23",
     "depart": "notification d'incident", "autorite": "ANSSI"},
    {"id": "dora-19", "declencheur": "incident-securite", "duree": "délais fixés par les normes techniques",
     "quoi": "Notification d'un incident majeur lié aux TIC",
     "fondement": "Règlement (UE) 2022/2554, art. 19",
     "depart": "classification de l'incident comme majeur", "autorite": "ACPR / AMF",
     "a_verifier": True},
    {"id": "cra-14", "declencheur": "produit-numerique",
     "duree": "alerte précoce puis notification puis rapport final",
     "quoi": "Signalement d'une vulnérabilité activement exploitée ou d'un incident grave",
     "fondement": "Règlement (UE) 2024/2847, art. 14 — applicable au 11 septembre 2026",
     "depart": "prise de connaissance", "autorite": "ENISA / autorité de surveillance",
     "a_verifier": True},
    {"id": "ai-act-73", "declencheur": "projet-ia", "duree": "sans retard indu",
     "quoi": "Signalement d'un incident grave par le fournisseur d'un système à haut risque",
     "fondement": "Règlement (UE) 2024/1689, art. 73",
     "depart": "établissement du lien de causalité", "autorite": "Autorité de surveillance du marché",
     "a_verifier": True},
    {"id": "rgpd-36", "declencheur": "nouveau-traitement", "duree": "avant la mise en œuvre",
     "quoi": "Consultation préalable de l'autorité si le risque résiduel reste élevé",
     "fondement": "RGPD, art. 36", "depart": "achèvement de l'analyse d'impact",
     "autorite": "CNIL"},
    {"id": "ai-act-6-3", "declencheur": "projet-ia", "duree": "avant la mise sur le marché",
     "quoi": "Documenter l'évaluation invoquant la dérogation, puis enregistrer le système",
     "fondement": "Règlement (UE) 2024/1689, art. 6(3) et 49.2",
     "depart": "décision de mise sur le marché", "autorite": "—"},
]


def _n(dossier):
    n = (dossier or {}).get("natures") or []
    if isinstance(n, str):
        n = [x.strip() for x in n.split(",") if x.strip()]
    return set(n)


def router(profil=None, dossier=None):
    """Qui tranche, qui est consulté, qui est informé — et avant quand.

    Aucun appel de modèle. Chaque ligne porte son fondement : c'est ce qui
    permet de dire « ce n'est pas notre organisation qui l'exige, c'est
    l'article 20 de NIS 2 » — et de le tenir en réunion.
    """
    profil, dossier = profil or {}, dossier or {}
    natures = _n(dossier)
    qual = qualifier(profil)
    textes = {x["id"] for x in qual["applicables"]}
    reserve = {x["id"] for x in qual["a_verifier"]}
    roles = _roles(profil)
    enjeu = (dossier.get("enjeu") or "moyen").lower()
    lignes = []

    def arbitrer(decideur, motif, fondement, consultes=(), informes=(), quand=""):
        lignes.append({"decideur": decideur,
                       "decideur_libelle": INSTANCES[decideur]["libelle"],
                       "role": INSTANCES[decideur]["role"],
                       "motif": motif, "fondement": fondement,
                       "consultes": [{"id": c, "libelle": INSTANCES[c]["libelle"]}
                                     for c in consultes if c in INSTANCES],
                       "informes": [{"id": i, "libelle": INSTANCES[i]["libelle"]}
                                    for i in informes if i in INSTANCES],
                       "quand": quand})

    # ── Ce que le texte réserve expressément ────────────────────────────
    if "nis2" in textes and natures & {"mesure-securite", "incident-securite"}:
        arbitrer("organe-direction",
                 "Les mesures de gestion des risques relèvent de l'approbation de "
                 "l'organe de direction, qui en supervise la mise en œuvre. "
                 "Accepter un écart sur ces mesures, c'est une décision qui lui "
                 "revient — et dont il répond personnellement.",
                 "Directive (UE) 2022/2555, art. 20",
                 consultes=("rssi", "direction-juridique"),
                 informes=("dsi", "metier"),
                 quand="Avant toute mise en œuvre, et par délibération tracée : "
                       "ce qui protège n'est pas l'approbation, c'est la trace de "
                       "l'instruction — risques présentés, options écartées, moyens alloués.")
    if "dora" in textes and "sortie-reversibilite" in natures:
        arbitrer("organe-direction",
                 "La stratégie de sortie applicable aux prestataires tiers de "
                 "services TIC relève de l'organe de direction.",
                 "Règlement (UE) 2022/2554, art. 28.8",
                 consultes=("direction-juridique", "rssi", "achats"),
                 informes=("dsi",))
    if "rgpd" in textes and natures & {"nouveau-traitement", "transfert-donnees",
                                       "violation-donnees", "projet-ia"}:
        arbitrer("direction-juridique",
                 "Le délégué à la protection des données doit être associé en "
                 "temps utile — non pas informé après coup. Il est CONSULTÉ, il "
                 "ne décide pas : un avis divergent doit être tracé et motivé.",
                 "RGPD, art. 38.1",
                 consultes=("dpo",), informes=("direction-generale",))

    # ── Situations d'urgence ────────────────────────────────────────────
    if "violation-donnees" in natures:
        arbitrer("direction-generale",
                 "Une violation de données enclenche une horloge de 72 heures qui "
                 "prime sur le calendrier interne. La décision de notifier — ou de "
                 "motiver l'absence de notification — ne peut pas attendre le "
                 "prochain comité.",
                 "RGPD, art. 33 et 34",
                 consultes=("dpo", "direction-juridique", "rssi"),
                 informes=("metier", "autorite"),
                 quand="Sous 72 heures à compter de la prise de connaissance.")
    if "incident-securite" in natures and ("nis2" in textes or "nis2" in reserve):
        arbitrer("direction-generale",
                 "L'alerte précoce est due sous 24 heures. Le point à trancher "
                 "n'est pas « faut-il notifier » mais « qui signe et sur quels "
                 "éléments », l'appréciation pouvant être complétée ensuite.",
                 "Directive (UE) 2022/2555, art. 23",
                 consultes=("rssi", "direction-juridique"),
                 informes=("dsi", "autorite"),
                 quand="Sous 24 heures — l'arbitrage doit être organisé en amont, "
                       "pas improvisé le jour de l'incident.")

    # ── Intelligence artificielle ───────────────────────────────────────
    if "projet-ia" in natures and "ai-act" in textes:
        arbitrer("direction-generale",
                 "Mise en service d'un système d'IA : la classification commande "
                 "tout le reste. Si l'annexe III est en cause, la dérogation de "
                 "l'art. 6(3) doit être documentée AVANT mise sur le marché — "
                 "après, elle n'est plus invocable.",
                 "Règlement (UE) 2024/1689, art. 6, 26 et 49",
                 consultes=("direction-juridique", "dpo", "rssi", "metier"),
                 informes=("dsi",),
                 quand="Avant mise en service. Une dérogation invoquée sans "
                       "évaluation préalable écrite est indéfendable.")
    if "modification-ia" in natures:
        arbitrer("direction-juridique",
                 "Modifier un système d'IA, y apposer sa marque ou en changer la "
                 "destination fait basculer le déployeur dans le statut de "
                 "fournisseur, avec l'ensemble des obligations correspondantes. "
                 "L'arbitrage porte sur ce basculement, pas sur la modification.",
                 "Règlement (UE) 2024/1689, art. 25",
                 consultes=("dsi", "rssi"), informes=("direction-generale",))

    # ── Contrats et chaîne d'approvisionnement ──────────────────────────
    if natures & {"contrat-fournisseur", "sortie-reversibilite", "appel-offres"}:
        cons = ["direction-juridique", "rssi"]
        if "rgpd" in textes:
            cons.append("dpo")
        arbitrer("achats",
                 "Négociation fournisseur : les exigences de sécurité, d'audit et "
                 "de réversibilité se gagnent AVANT signature. Après, elles se "
                 "rachètent — et au prix du fournisseur.",
                 "NIS 2, art. 21.2.d ; RGPD, art. 28 ; DORA, art. 30",
                 consultes=cons, informes=("direction-generale", "metier"))
    if "produit-numerique" in natures and "cra" in textes:
        arbitrer("direction-generale",
                 "Produit comportant des éléments numériques : les obligations de "
                 "signalement et de support conditionnent la mise sur le marché "
                 "et engagent la responsabilité du fabricant.",
                 "Règlement (UE) 2024/2847",
                 consultes=("direction-juridique", "rssi", "dsi"),
                 informes=("metier",))

    # ── Environnement industriel ────────────────────────────────────────
    if _vrai(profil, "systeme_ot") and natures & {"mesure-securite", "incident-securite",
                                                  "contrat-fournisseur"}:
        arbitrer("rssi",
                 "Une mesure de cybersécurité qui touche une fonction "
                 "instrumentée de sécurité ne se tranche pas entre spécialistes "
                 "de la sécurité seulement. La règle d'arbitrage est écrite : en "
                 "cas de conflit, la fonction de sûreté prévaut et une mesure "
                 "compensatoire est recherchée.",
                 "IEC 61511 ; IEC 62443-3-2",
                 consultes=("surete", "metier"), informes=("direction-generale",))

    # ── Contentieux et contrôles ────────────────────────────────────────
    if natures & {"contentieux", "audit-controle"} or enjeu == "eleve":
        arbitrer("avocat",
                 "Acte juridique, contentieux ou position à fort enjeu : "
                 "l'intervention d'un avocat n'est pas une précaution de style, "
                 "c'est le régime applicable à la consultation juridique.",
                 "Loi n° 71-1130 du 31 décembre 1971",
                 consultes=("direction-juridique",),
                 informes=("direction-generale",))

    # ── Défaut ──────────────────────────────────────────────────────────
    if not lignes:
        arbitrer("direction-juridique",
                 "Aucune règle ne réserve cette décision à un organe particulier : "
                 "elle relève de la direction juridique, la direction générale "
                 "étant informée.",
                 "Répartition interne des compétences",
                 informes=("direction-generale",))

    # Un même décideur peut être désigné par plusieurs règles : on fusionne les
    # motifs plutôt que de faire figurer trois fois « Direction générale ».
    fusion = {}
    for l in lignes:
        d = l["decideur"]
        if d in fusion:
            f = fusion[d]
            f["motifs"].append(l["motif"])
            for k in ("fondement",):
                if l[k] not in f["fondements"]:
                    f["fondements"].append(l[k])
            for c in l["consultes"]:
                if c not in f["consultes"]:
                    f["consultes"].append(c)
            for i in l["informes"]:
                if i not in f["informes"]:
                    f["informes"].append(i)
            if l["quand"] and l["quand"] not in f["quand"]:
                f["quand"].append(l["quand"])
        else:
            fusion[d] = {"decideur": d, "decideur_libelle": l["decideur_libelle"],
                         "role": l["role"], "motifs": [l["motif"]],
                         "fondements": [l["fondement"]],
                         "consultes": list(l["consultes"]),
                         "informes": list(l["informes"]),
                         "quand": [l["quand"]] if l["quand"] else []}
    # Ordre de présentation : du plus contraint au moins contraint.
    ordre = ["organe-direction", "direction-generale", "avocat", "achats",
             "direction-juridique", "rssi", "dsi", "metier", "surete"]
    decisions = sorted(fusion.values(),
                       key=lambda x: ordre.index(x["decideur"])
                       if x["decideur"] in ordre else 99)

    echeances = [dict(d) for d in DELAIS if d["declencheur"] in natures]

    return {
        "version_referentiel": VERSION_REFERENTIEL,
        "objet": (dossier.get("objet") or "").strip(),
        "natures": sorted(natures),
        "decisions": decisions,
        "echeances": echeances,
        "qualification": qual,
        "synthese_routage": _synthese_routage(decisions, echeances),
        "avertissement": AVERTISSEMENT,
    }


def _synthese_routage(decisions, echeances):
    if not decisions:
        return "Aucun arbitrage identifié."
    qui = decisions[0]["decideur_libelle"]
    p = "L'arbitrage revient en premier lieu à : %s." % qui
    if len(decisions) > 1:
        p += " %d autre(s) instance(s) doivent se prononcer ou être consultées." % (len(decisions) - 1)
    dures = [e for e in echeances if not e.get("a_verifier")]
    if dures:
        p += (" ATTENTION : %d échéance(s) réglementaire(s) s'imposent au calendrier, "
              "dont « %s » sous %s." % (len(dures), dures[0]["quoi"], dures[0]["duree"]))
    return p


SYSTEM_ARBITRAGE = """Tu prépares une NOTE D'ARBITRAGE destinée à un comité de direction, un comité juridique ou une réunion de négociation. Ton lecteur dispose de dix minutes et doit ressortir avec une décision prise.

Ce n'est PAS une consultation juridique développée : c'est un document de décision. Tu synthétises un dossier, tu fais ressortir ce qui peut faire perdre, tu poses les options avec leurs conséquences, et tu recommandes.

STRUCTURE IMPOSÉE, dans cet ordre exact :

## Décision à prendre
Une seule phrase, à l'infinitif ou à l'impératif. Ce que le comité doit trancher, pas le contexte.

## L'essentiel
Cinq lignes maximum. Ce que le lecteur retient s'il ne lit rien d'autre : la situation, l'enjeu chiffré ou qualifié, l'échéance, le sens de ta recommandation.

## Le dossier
Synthèse factuelle des pièces fournies. Cite tes sources entre crochets [1], [2]. Distingue ce qui est ÉTABLI par les pièces de ce qui est DÉCLARÉ sans preuve au dossier, et de ce qui MANQUE. Ne développe pas le droit ici.

## Points critiques
Classés du plus grave au moins grave. Pour chacun : le fait, la conséquence concrète, et le texte qui la fonde. Un point critique est ce qui peut faire perdre — pas ce qui est inhabituel. Trois à six points ; si tu en as davantage, c'est que tu n'as pas trié.

## Options
Deux à quatre options réellement praticables, en tableau : Option | Ce qu'on fait | Conséquence juridique | Risque résiduel | Coût / délai | Réversibilité. Ne présente pas une fausse option pour faire nombre. L'inaction est une option si elle est défendable : dis-le alors franchement.

## Recommandation
Celle que tu retiendrais, et pourquoi. Assume : une note qui renvoie le comité à son propre arbitrage sans l'éclairer n'a servi à rien. Précise les conditions auxquelles elle tient, et ce qui la ferait changer.

## Ce qui manque pour décider
Tableau : Pièce ou information manquante | Qui la détient | Pour quand. S'il ne manque rien, écris-le.

## Points de négociation
Uniquement si le dossier s'y prête. Trois colonnes : ce qui doit être obtenu, ce qui est négociable, ce qui peut être concédé sans risque. Sinon, omets entièrement cette section.

## Réserves
Ce que tu ne peux pas trancher en l'état, et ce qui y répondrait.

RÈGLES ABSOLUES :
- Le ROUTAGE DES DÉCISIONS et les ÉCHÉANCES te sont fournis, calculés par l'application. Reprends-les tels quels, n'en invente aucun autre, ne redistribue pas les rôles. Si tu estimes qu'un autre acteur devrait se prononcer, dis-le en Réserves.
- N'invente JAMAIS une référence : pas de numéro d'article, de considérant ou de date absent du référentiel autorisé ou des extraits fournis.
- N'invente JAMAIS un fait du dossier. Si une information usuelle est absente, elle va dans « Ce qui manque pour décider ». Une note d'arbitrage bâtie sur des faits supposés fait prendre une décision fausse — c'est pire que pas de note.
- Chiffre ce qui est chiffrable (délais, plafonds, durées) ; écris « non chiffrable en l'état » sinon, jamais un ordre de grandeur inventé.
- Écris dense. Pas de formule de politesse, pas d'introduction sur ce que tu vas faire, pas de conclusion qui répète.
- Français, phrases courtes, ton de professionnel qui engage sa signature.

Tu termines par la section Réserves, puis rien d'autre : l'avertissement légal est ajouté par l'application."""


def _bloc_routage(rt):
    """Routage et échéances transmis au modèle — pour qu'il les reprenne, pas
    pour qu'il les recalcule."""
    out = ["ROUTAGE DES DÉCISIONS — calculé par l'application selon des règles "
           "explicites. À REPRENDRE TEL QUEL dans la note, sans redistribution :"]
    for d in rt["decisions"]:
        out.append("• DÉCIDE : %s" % d["decideur_libelle"])
        out.append("   fondement : %s" % " ; ".join(d["fondements"]))
        for m in d["motifs"]:
            out.append("   motif : %s" % m)
        if d["consultes"]:
            out.append("   consultés : %s" % ", ".join(c["libelle"] for c in d["consultes"]))
        if d["informes"]:
            out.append("   informés : %s" % ", ".join(i["libelle"] for i in d["informes"]))
        for q in d["quand"]:
            out.append("   quand : %s" % q)
    if rt["echeances"]:
        out.append("")
        out.append("ÉCHÉANCES RÉGLEMENTAIRES applicables — elles commandent le "
                   "calendrier de la réunion, place-les en tête de la note :")
        for e in rt["echeances"]:
            out.append("• %s — %s (à compter de : %s) — %s%s"
                       % (e["quoi"], e["duree"], e["depart"], e["fondement"],
                          " [DURÉE À CONFIRMER]" if e.get("a_verifier") else ""))
    return "\n".join(out)


def prompt_arbitrage(objet, contexte=None, extraits=None, profil=None,
                     dossier=None, textes_ids=None, jurisprudence=None):
    """Construit le message utilisateur d'une note d'arbitrage.

    `extraits` : passages des pièces du dossier, déjà numérotés [1], [2]…
    `contexte` : éléments saisis par l'utilisateur et absents des pièces.
    `jurisprudence` : décisions rapportées du corpus, mêmes règles que pour
    l'analyse — citables parce qu'elles sont sous les yeux du modèle, et elles
    seules.
    """
    dossier = dict(dossier or {})
    if objet:
        dossier.setdefault("objet", objet)
    rt = router(profil, dossier)
    if not textes_ids:
        textes_ids = ([x["id"] for x in rt["qualification"]["applicables"]]
                      + [x["id"] for x in rt["qualification"]["a_verifier"]])
    textes_ids = textes_ids or [t["id"] for t in REFERENTIEL]

    p = ["DÉCISION À PRÉPARER :", str(objet or "").strip()[:2000], ""]

    p.append("QUALIFICATION RÉGLEMENTAIRE déjà établie par l'application "
             "(règles explicites, sans IA) — reprends-la, ne la refais pas :")
    for x in rt["qualification"]["applicables"]:
        p.append("- [applicable] %s : %s" % (x["titre"], " ".join(x["motifs"])))
    for x in rt["qualification"]["a_verifier"]:
        p.append("- [à confirmer] %s : %s" % (x["titre"], " ".join(x["motifs"])))
    p.append("")

    p.append(_bloc_routage(rt))
    p.append("")

    p.append("RÉFÉRENTIEL AUTORISÉ — seules ces références peuvent être citées :")
    p.append(_bloc_referentiel(textes_ids))
    p.append("")

    bc = _bloc_controverses(textes_ids)
    if bc:
        p.append(bc)
        p.append("")

    bj = _bloc_jurisprudence(jurisprudence)
    if bj:
        p.append(bj)
        p.append("")

    if contexte and str(contexte).strip():
        p.append("ÉLÉMENTS FOURNIS PAR LE DEMANDEUR (hors pièces du dossier) — "
                 "à traiter comme DÉCLARÉS et non établis, sauf corroboration "
                 "par une pièce :")
        p.append(str(contexte).strip()[:6000])
        p.append("")

    if extraits and str(extraits).strip():
        p.append("PIÈCES DU DOSSIER — c'est la matière de ta synthèse. Cite-les "
                 "entre crochets [1], [2]. Ce qui n'y figure pas n'est PAS un fait "
                 "établi :")
        p.append(extraits if isinstance(extraits, str) else "\n\n".join(extraits))
    else:
        p.append("PIÈCES DU DOSSIER : AUCUNE pièce n'a été fournie. Signale-le dès "
                 "« L'essentiel », construis la note sur le seul cadre "
                 "réglementaire, et fais figurer en tête de « Ce qui manque pour "
                 "décider » les pièces indispensables à un arbitrage éclairé.")
    return "\n".join(p)


# Amorces propres à l'arbitrage : ce qu'un dirigeant demande réellement.
SUGGESTIONS_ARBITRAGE = [
    {"groupe": "Incident", "q": "Notre prestataire nous signale une intrusion sur "
                                "son infrastructure : que devons-nous décider, dans "
                                "quel ordre et avant quand ?"},
    {"groupe": "Fournisseur", "q": "Faut-il signer en l'état le contrat "
                                   "d'infogérance, ou bloquer la signature sur les "
                                   "clauses d'audit et de réversibilité ?"},
    {"groupe": "IA", "q": "Pouvons-nous mettre en service notre outil de scoring "
                          "avant le 2 août 2026, et à quelles conditions ?"},
    {"groupe": "Sortie", "q": "Sortir du contrat maintenant en payant l'indemnité, "
                              "ou aller au terme en sécurisant la réversibilité ?"},
    {"groupe": "Écart", "q": "Pouvons-nous accepter de reporter d'un an la "
                             "segmentation du réseau industriel, et qui doit en "
                             "porter la décision ?"},
    {"groupe": "Contrôle", "q": "L'autorité nous demande des éléments sous quinze "
                                "jours : que produisons-nous, et que gardons-nous ?"},
]


# ═══════════════════════════════════════════════════════════════════════════
# 9. DOCUMENT REMIS — ce qui part en réunion
# ═══════════════════════════════════════════════════════════════════════════
#
# À l'écran, le routage déterministe et la note rédigée sont deux blocs
# distincts : c'est voulu, on voit ce qui est déduit d'un texte et ce qui est
# rédigé par un modèle. Dans le document remis au comité, ils doivent au
# contraire tenir ENSEMBLE — sans le tableau « qui tranche, avant quand », la
# note perd exactement ce qui la rendait actionnable.
#
# Le document est donc recomposé ici, à partir des données reconstruites côté
# serveur. Rien de ce que le navigateur renvoie n'est repris tel quel pour les
# parties déterministes : la qualification et le routage sont RECALCULÉS. Un
# document qui sort de l'entreprise et porte une répartition des rôles ne doit
# pas dépendre de ce qu'un formulaire a bien voulu renvoyer.

TYPES_DOCUMENT = {
    "arbitrage": {"titre": "Note d'arbitrage",
                  "sous_titre": "Document préparatoire à la décision"},
    "analyse": {"titre": "Analyse juridique",
                "sous_titre": "Qualification, lectures possibles et recommandation"},
    "contrat": {"titre": "Revue de contrat",
                "sous_titre": "Analyse clause par clause au regard de la grille d'exigences"},
    "qualification": {"titre": "Qualification réglementaire",
                      "sous_titre": "Textes applicables et motivation du rattachement"},
}


def _tab(entetes, lignes):
    """Tableau Markdown. Les cellules vides sont remplies par un tiret : une
    colonne qui saute décale toute la ligne à la conversion."""
    if not lignes:
        return ""
    def cell(x):
        x = str(x if x is not None else "").replace("|", "/").replace("\n", " ").strip()
        return x or "—"
    out = ["| " + " | ".join(cell(e) for e in entetes) + " |",
           "| " + " | ".join("---" for _ in entetes) + " |"]
    for l in lignes:
        out.append("| " + " | ".join(cell(c) for c in l) + " |")
    return "\n".join(out)


def _bloc_qualification_md(qual):
    if not qual:
        return ""
    lignes = []
    for x in qual.get("applicables", []):
        lignes.append([x["titre"], " ".join(x["motifs"]), "Applicable"])
    for x in qual.get("a_verifier", []):
        lignes.append([x["titre"], " ".join(x["motifs"]), "À confirmer"])
    if not lignes:
        return ""
    return ("## Textes applicables\n\n"
            "*Qualification calculée par règles explicites, sans intelligence "
            "artificielle : le même profil donne toujours le même résultat.*\n\n"
            + _tab(["Texte", "Pourquoi il s'applique", "Statut"], lignes) + "\n")


def _bloc_routage_md(rt):
    if not rt or not rt.get("decisions"):
        return ""
    out = ["## Qui tranche, et avant quand", "",
           "*" + rt.get("synthese_routage", "") + "*", ""]
    if rt.get("echeances"):
        out += ["### Échéances réglementaires", "",
                "Elles commandent le calendrier de la réunion : elles ne se "
                "négocient pas avec l'agenda des participants.", "",
                _tab(["Délai", "Ce qui est dû", "À compter de", "Fondement", "Autorité"],
                     [[e["duree"] + (" (à confirmer)" if e.get("a_verifier") else ""),
                       e["quoi"], e["depart"], e["fondement"], e.get("autorite")]
                      for e in rt["echeances"]]), ""]
    out += ["### Répartition des décisions", "",
            _tab(["Instance", "Fondement", "Consultés", "Informés", "Quand"],
                 [[d["decideur_libelle"], " ; ".join(d["fondements"]),
                   ", ".join(c["libelle"] for c in d["consultes"]),
                   ", ".join(i["libelle"] for i in d["informes"]),
                   " ".join(d["quand"])]
                  for d in rt["decisions"]]), ""]
    for d in rt["decisions"]:
        out.append("**%s** — %s" % (d["decideur_libelle"], d["role"]))
        for m in d["motifs"]:
            out.append("")
            out.append(m)
        out.append("")
    return "\n".join(out)


def _bloc_pieces_md(pieces):
    if not pieces:
        return ("## Pièces du dossier\n\n"
                "**Aucune pièce n'a été versée au dossier.** La note repose sur le "
                "seul cadre réglementaire : la section « Ce qui manque pour décider » "
                "doit être lue en premier.\n")
    return ("## Pièces du dossier\n\n"
            + _tab(["#", "Pièce", "Origine"],
                   [[p.get("n"), p.get("titre"), p.get("origine")] for p in pieces])
            + "\n\n*Une pièce désignée a été lue intégralement ; un extrait "
              "retrouvé automatiquement n'a pas le même poids.*\n")


def _bloc_citations_md(ctrl):
    if not ctrl:
        return ""
    if ctrl.get("ok"):
        return ("## Contrôle des références\n\n"
                "Les %d référence(s) normative(s) citées correspondent à des textes "
                "du référentiel. Ce contrôle vérifie l'EXISTENCE des textes cités, "
                "non la pertinence de leur application : la lecture reste à valider.\n"
                % len(ctrl.get("connues") or []))
    return ("## Contrôle des références — ATTENTION\n\n"
            "Les références suivantes ne figurent PAS au référentiel et doivent être "
            "tenues pour non fiables tant qu'elles n'ont pas été vérifiées sur la "
            "source officielle : %s.\n\nLe reste du document demeure exploitable.\n"
            % ", ".join(s["brut"] for s in ctrl["suspectes"]))


def document_markdown(type_doc, texte, objet=None, routage=None, qualification=None,
                      pieces=None, citations=None, modele=None, date=None):
    """Document complet, prêt pour l'export Word ou PDF.

    L'ordre suit celui d'une lecture en réunion : ce qui engage (échéances,
    répartition des décisions) AVANT la rédaction, et les annexes de contrôle
    après. Un dirigeant qui n'ouvre que la première page doit y trouver
    l'échéance et le nom de l'instance qui doit trancher.
    """
    t = TYPES_DOCUMENT.get(type_doc) or TYPES_DOCUMENT["analyse"]
    out = ["# " + t["titre"], "", "*" + t["sous_titre"] + "*", ""]
    if objet:
        out += ["**Objet : " + str(objet).strip() + "**", ""]
    meta = []
    if date:
        meta.append("Date : " + str(date))
    meta.append("Référentiel : version " + VERSION_REFERENTIEL)
    if modele:
        meta.append("Rédaction assistée par : " + str(modele))
    out += [" · ".join(meta), "", "---", ""]

    bq = _bloc_qualification_md(qualification)
    if bq:
        out += [bq, ""]
    br = _bloc_routage_md(routage)
    if br:
        out += [br, ""]
    if bq or br:
        out += ["---", ""]

    out += [str(texte or "").strip(), "", "---", ""]
    out += [_bloc_pieces_md(pieces), ""]
    bc = _bloc_citations_md(citations)
    if bc:
        out += [bc, ""]
    out += ["## Portée de ce document", "", AVERTISSEMENT, "", MENTION_IA, ""]
    return "\n".join(out)


def nom_fichier(type_doc, objet=None):
    """Nom de fichier lisible et sans surprise : accents retirés, ponctuation
    remplacée, longueur bornée. Un nom qui casse au téléchargement fait perdre
    plus de temps qu'il n'en fait gagner."""
    t = TYPES_DOCUMENT.get(type_doc) or TYPES_DOCUMENT["analyse"]
    base = t["titre"]
    if objet:
        base += " - " + str(objet)
    base = _normaliser(base)
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return (base[:70] or "document-juridique")
