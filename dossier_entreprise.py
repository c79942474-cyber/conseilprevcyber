# -*- coding: utf-8 -*-
"""LE DOSSIER D'ENTREPRISE DE CONSEILPREV — ses qualifications, ses références,
sa note de méthode et son papier en-tête.

À QUI CE DOSSIER APPARTIENT, ET POURQUOI CELA COMMANDE TOUT LE RESTE. Ce sont
les qualifications et les références de CONSEILPREV, pas celles d'un client du
module. `ao_dc.remplir()` sert des CLIENTS qui préparent LEUR candidature :
faire entrer ce dossier là-dedans donnerait à un client les références d'un
autre — et lui permettrait de les déposer comme siennes. Tout ce que ce module
expose passe donc par `/api/admin/`, derrière `@admin_required`, et la
politique d'accès du site refuse de démarrer si une route de cette famille
n'est pas fermée à l'administrateur.

POURQUOI UNE TABLE ET NON QUATRE PDF. Les quatre documents d'origine sont
conservés sous `dossier_entreprise/origine/` — ils font foi de la
transcription. Mais un PDF ne se modifie pas : or ce dossier VIVRA, parce
qu'une qualification s'obtient, une référence se termine, un montant se
confirme. La table est donc la vérité, et le PDF l'origine.

CE QUI COMPTE VRAIMENT ICI : LES TROUS SONT DES DONNÉES. Les documents
d'origine portent en toutes lettres « [à compléter] », « référence à
préciser », « [client à préciser] », « attestation à joindre ». Un module qui
recopierait ces mentions dans un texte les rendrait invisibles au décompte. Ils
sont donc portés par un champ `manques`, énuméré, compté, et rendu à chaque
appel. UNE RÉFÉRENCE INCOMPLÈTE N'EST PAS UNE RÉFÉRENCE : la produire dans un
dossier de candidature en la comptant fait annoncer six références là où
l'acheteur en trouvera quatre.

CE MODULE NE PRODUIT AUCUN JUSTIFICATIF. Une attestation « à joindre » se
demande à l'organisme qui la délivre ; un certificat se scanne. Le module dit
ce qui manque et où cela se trouve — il ne fabrique ni l'un ni l'autre.
"""
import datetime
import os
import re

VERSION = "2026-08-a"

ICI = os.path.dirname(os.path.abspath(__file__))
DOSSIER_ORIGINE = os.path.join(ICI, "dossier_entreprise", "origine")

# La date à laquelle les quatre documents d'origine ont été établis et
# transcrits ici. Elle n'est pas décorative : une qualification « en cours » et
# une référence « en cours » vieillissent, et c'est cette date qui permet de
# dire depuis combien de temps.
ETABLI_LE = "2026-08-13"

# ── LES EXERCICES CLOS, ET D'OÙ CHAQUE MONTANT SORT ───────────────────────
# LE DC2 DEMANDE LE CHIFFRE D'AFFAIRES GLOBAL DES TROIS DERNIERS EXERCICES, et
# l'acheteur peut le confronter à la liasse. Un montant arrondi de mémoire se
# voit donc — et se voit du mauvais côté. Chaque ligne porte SA SOURCE : le
# document qui l'établit, et à quelle page ou rubrique il l'établit.
#
# ILS SONT RANGÉS PAR ANNÉE DÉCROISSANTE, ET C'EST LE RANG QUI FAIT n1/n2/n3.
# Écrire « ca_n1 = … » figerait le rang : le jour où l'exercice 2026 est clos,
# il faudrait décaler trois valeurs à la main, et rien ne dirait qu'on a
# oublié. Ici, une ligne s'ajoute en tête et les trois rangs suivent seuls.
EXERCICES = (
    {"annee": 2025, "ca": "7 496 €",
     "source": "attestation de présentation des comptes, BDO Rennes — "
               "exercice du 01/01/2025 au 31/12/2025"},
    {"annee": 2024, "ca": "21 800 €",
     "source": "attestation d'expert-comptable, BDO — exercice du "
               "01/01/2024 au 31/12/2024"},
    {"annee": 2023, "ca": "79 328 €",
     "source": "colonne 31/12/2023 du compte de résultat des états "
               "financiers 2024 (BDO, page 4) et soldes intermédiaires de "
               "gestion (page 15)"},
)

IDENTITE = {
    "raison_sociale": "CONSEILPREV SARL",
    "forme_juridique": "SARL",
    "capital": "8 000 €",
    "siren": "494 530 157",
    # LE SIRET A ÉTÉ TRANCHÉ PAR LE GÉRANT, PAS PAR UN CALCUL. Deux valeurs
    # circulaient — celle-ci et « 494 530 157 00010 » —, et les DEUX passent la
    # clé de Luhn : l'arithmétique ne pouvait pas départager, seul l'avis de
    # situation le pouvait. Elle est retenue sur déclaration du gérant du
    # 12/09/2026. La cohérence avec le SIREN et la clé restent vérifiées à
    # l'import : une faute de frappe se verrait.
    "siret": "494 530 157 00036",
    "exercices": EXERCICES,
    "tva": "FR 24 494 530 157",
    "adresse": "19 rue Auguste Chabrières, 75015 Paris",
    "telephone": "+33 6 60 69 21 45",
    "courriel": "christophe.cerf@i-aes.com",
    "representant_nom": "Christophe Cerf",
    "representant_qualite": "Gérant",
    "activite": "Conseil en gouvernance de l'intelligence artificielle et "
                "cybersécurité industrielle",
}

# ── LES QUATRE VOIES DE JUSTIFICATION, ET ELLES NE S'ÉQUIVALENT PAS ────────
# Le document d'origine les nomme lui-même. Un certificat de qualification est
# délivré par un organisme et se vérifie ; un certificat de capacité est une
# affirmation du candidat, appuyée sur des pièces ; une référence de travaux
# vaut par son objet ET son montant. Les confondre reviendrait à présenter une
# affirmation là où l'acheteur attend un document opposable.
VOIES_JUSTIFICATION = {
    "certificat_qualification": {
        "nom": "Certificat de qualification",
        "aide": "Délivré par un organisme qualificateur. Il se vérifie auprès "
                "de lui, et il a une date de validité.",
    },
    "certificat_capacite": {
        "nom": "Certificat de capacité",
        "aide": "Une attestation appuyée sur des pièces — certifications, "
                "formations, missions. Ce n'est pas un certificat "
                "d'organisme : les pièces se joignent.",
    },
    "reference_travaux": {
        "nom": "Référence de travaux",
        "aide": "Une mission conduite, avec son objet ET son montant € HT. "
                "Sans le montant, l'acheteur ne peut pas juger la taille.",
    },
    "sous_traitant_qualifie": {
        "nom": "Sous-traitant qualifié",
        "aide": "La qualification est portée par un tiers. Son engagement "
                "écrit se joint, et un DC4 le présente.",
    },
}

# ── LES QUALIFICATIONS PROFESSIONNELLES ───────────────────────────────────
QUALIFICATIONS = [
    {"annexe": "A1", "cle": "ai_act",
     "intitule": "Gouvernance de l'intelligence artificielle — conformité au "
                 "Règlement (UE) 2024/1689 (AI Act)",
     "voie": "certificat_capacite",
     "appui": "Expertise du dirigeant (certification AIGP, IAPP, en cours) et "
              "missions de mise en conformité AI Act.",
     "manques": ["Attestation de capacité à joindre.",
                 "Certification AIGP annoncée « en cours » : dire où elle en "
                 "est, ou retirer la mention."]},
    {"annexe": "A2", "cle": "iso_42001",
     "intitule": "Système de management de l'intelligence artificielle — "
                 "ISO/IEC 42001",
     "voie": "reference_travaux",
     "appui": "Conception et déploiement de cadres de gouvernance IA "
              "conformes ISO/IEC 42001.",
     "manques": ["Référence à préciser : client, objet, montant € HT."]},
    {"annexe": "A3", "cle": "iso_27001",
     "intitule": "Sécurité de l'information — ISO/IEC 27001",
     "voie": "certificat_capacite",
     "appui": "Maîtrise du référentiel ISO/IEC 27001 et module Gouvernance de "
              "la sécurité (CISM Cert Prep 1).",
     "manques": ["Attestation à joindre."]},
    {"annexe": "A4", "cle": "iec_62443",
     "intitule": "Cybersécurité des systèmes industriels OT / ICS — IEC 62443",
     "voie": "certificat_capacite",
     "appui": "Certifications Cybersecurity for Industrial Control Systems "
              "(U.S. DHS).",
     "manques": ["Certificats à joindre.",
                 "Référence de mission à préciser : objet, montant € HT."]},
    {"annexe": "A5", "cle": "nis2",
     "intitule": "Conformité à la directive NIS 2",
     "voie": "reference_travaux",
     "appui": "Élaboration de cadres de conformité NIS 2.",
     "manques": ["Référence à préciser : client, objet, montant € HT."]},
    {"annexe": "A6", "cle": "dora",
     "intitule": "Résilience opérationnelle numérique — Règlement DORA",
     "voie": "certificat_capacite",
     "appui": "Expertise DORA appliquée au secteur financier.",
     "manques": ["Éléments justificatifs à joindre."]},
    {"annexe": "A7", "cle": "rgpd",
     "intitule": "Protection des données à caractère personnel — RGPD",
     "voie": "certificat_capacite",
     "appui": "Référent cybersécurité TPE/PME et pratique RGPD.",
     "manques": ["Attestation à joindre."]},
    {"annexe": "A8", "cle": "ebios_rm",
     "intitule": "Analyse et gestion des risques cyber — méthode EBIOS Risk "
                 "Manager",
     "voie": "reference_travaux",
     "appui": "Conduite d'analyses de risques EBIOS RM.",
     "manques": ["Référence à préciser : client, objet, montant € HT, EN "
                 "QUALITÉ DE CONSEILPREV — une mission conduite à titre "
                 "individuel ne se porte pas au crédit de la société."]},
    {"annexe": "A9", "cle": "cyber_ics",
     "intitule": "Cybersécurité des systèmes de contrôle industriels — "
                 "menaces courantes (CYBER ICS)",
     "voie": "certificat_capacite",
     "appui": "Certification Cybersecurity for Industrial Control Systems, "
              "Current Threats (U.S. DHS).",
     "manques": ["Certificat à joindre."]},
]

# ── LES RÉFÉRENCES DE MISSIONS ────────────────────────────────────────────
# `porte_par` DIT QUI A CONDUIT LA MISSION, et ce n'est pas un détail de
# présentation : une mission conduite à titre individuel ne se porte pas au
# crédit de la société sans le dire. Le document d'origine le signale lui-même
# — « le cadre contractuel de chaque référence est à confirmer ».
REFERENCES = [
    {"annexe": "R1", "cle": "edf_surete_si",
     "nom": "Mission Sûreté du SI — DSI Énergie", "client": "EDF SA",
     "montant": "150 k€ HT", "periode": "2022–2024", "part": "en propre",
     "objet": "Sûreté de fonctionnement des datacenters et réseaux, études de "
              "cybersécurité et revues d'architectures des SI, analyse des "
              "risques EBIOS RM.",
     "manques": []},
    {"annexe": "R2", "cle": "renault_vehicule_connecte",
     "nom": "Cyber Consulting & Risk Management — Véhicule connecté",
     "client": "Renault Group", "montant": "92 k€ HT", "periode": "2021–2022",
     "part": "en propre",
     "objet": "Mapping WP.29 / CSMS, Roadsecurity Plan ISO/SAE 21434, "
              "exigences UNECE R155/R156, volet PIA/AIPD/RGPD. Certification "
              "ISO/SAE 21434 first-to-market ; −30 % d'incidents.",
     "manques": []},
    {"annexe": "R3", "cle": "grand_paris_express",
     "nom": "Ingénieur Réseau & Sécurité — Grand Paris Express",
     "client": "Atos — Société du Grand Paris (avec EGIS & SETEC)",
     "montant": "50 k€ HT", "periode": "2021–2022",
     "part": "en propre, en cotraitance",
     "objet": "Réseau multi-services et systèmes de surveillance des espaces, "
              "lignes 15, 16 et 17 ; analyses EBIOS RM.",
     "manques": []},
    {"annexe": "R4", "cle": "siem_montreal",
     "nom": "Contrat SIEM — Réseau Express Métropolitain (Montréal)",
     "client": "Alstom / Airbus (avec Atos)", "montant": "110 k€ HT",
     "periode": None, "part": "en propre",
     "objet": "Pilotage de lots : WP1.1 (DAT), WP2.1 (pré-intégration SIEM), "
              "conception de la plateforme d'hébergement, évaluation de "
              "l'analyse de risque système.",
     "manques": []},
    {"annexe": "R5", "cle": "grdf_biomethane",
     "nom": "Cybersécurité du SI Industriel — Projet Biométhane",
     "client": "GRDF", "montant": "100 k€ HT", "periode": None,
     "part": "en propre",
     "objet": "Rédaction de la PSSI industrielle, analyses de risques EBIOS "
              "et MCS, cartographie du SI industriel, détection d'incident, "
              "analyse d'écarts LPM/NIS. Corpus : ISO 27001, NIST SP "
              "800-82/53, ANSSI, IEC 62443.",
     "manques": []},
    {"annexe": "R6", "cle": "technip_sci",
     "nom": "Ingénieur cybersécurité des systèmes de contrôle industriel",
     "client": "TechnipEnergies", "montant": "130 k€ HT",
     "periode": "2014–2020", "part": "en propre",
     "objet": "Conception, architectures et supervision des SCI (PLC, HMI, "
              "SCADA, DCS). Projets Karish & Tanin FPSO, GTLA, Manaseer MCC, "
              "Martin Linge, Motiva FEED, US Gas Cap.",
     "manques": []},
    {"annexe": "R7", "cle": "assurance_ia_cyberdefense",
     "nom": "Direction de projet AMOA — Intégration IA & cyberdéfense",
     "client": "Groupe d'assurance international (référence anonymisée)",
     "montant": "50 k€ HT", "periode": None, "part": "en propre",
     "objet": "Structuration d'un programme groupe multi-filiales : "
              "cartographie de l'exposition, chaînes de patching, SOC "
              "augmenté par l'IA, gouvernance et gestion de crise. Pilotage "
              "TTD, MTTR, MTTP.",
     "manques": ["Mission en cours : dire l'avancement, pas seulement la "
                 "date de début.",
                 "Client anonymisé — une référence dont le maître d'ouvrage "
                 "n'est pas nommé ne se vérifie pas : obtenir l'accord de "
                 "citation, ou l'annoncer explicitement comme anonymisée."]},
    {"annexe": "R8", "cle": "eolien_offshore_ot",
     "nom": "Management de la sécurité OT — Sous-station offshore (parc "
            "éolien)",
     "client": None, "montant": "120 k€ HT", "periode": None,
     "part": "en propre, en qualité de prestataire de services IACS",
     "objet": "Schéma de sécurité OT de la sous-station offshore : exigences "
              "IEC 62443 et ISO 27000, security levels, architecture OT "
              "système et composant, plan de management OT (EPCI), cascade "
              "fournisseurs.",
     "manques": []},
]

# ── LES ATTESTATIONS — CE QUI PROUVE CE QUE LES DÉCLARATIONS AFFIRMENT ─────
# POURQUOI ELLES ENTRENT ICI. Les six rubriques de déclaration des formulaires
# ne sont JAMAIS pré-remplies, et rien de ce qui suit ne les remplira : une
# attestation ne signe pas à la place de qui affirme. Ce qu'elle fait est
# autre chose, et c'est ce qui manquait — elle met la PREUVE sous les yeux de
# qui va affirmer, avec sa date de péremption. On automatise la preuve, jamais
# l'affirmation.
#
# AUCUNE DATE N'EST INVENTÉE ICI. Le module ne sait pas quelles attestations
# CONSEILPREV détient aujourd'hui ni jusqu'à quand : les champs partent donc
# VIDES, et `manques` dit ce qu'il faut obtenir. Une date plausible écrite en
# dur ferait croire à une couverture qui n'existe pas — exactement le défaut
# que les `manques` des références servent à éviter.
#
# CE QU'UNE ATTESTATION COUVRE EST DÉCLARÉ, JAMAIS DEVINÉ. `couvre` nomme les
# rubriques de déclaration que la pièce soutient. Une attestation qui ne
# couvrirait rien serait un document de plus dans un classeur ; celle qui
# prétendrait tout couvrir ferait passer une affirmation sans preuve.
ATTESTATIONS = [
    {"annexe": "T1", "cle": "vigilance_urssaf",
     "nom": "Attestation de vigilance URSSAF",
     "organisme": "URSSAF",
     "delivree_le": None, "valable_jusqu_au": None,
     "couvre": ("d_fiscal_social", "d_obligatoires"),
     "renouvellement_mois": 6,
     "manques": ["attestation à demander sur urssaf.fr, espace employeur",
                 "date de délivrance et date de fin de validité à porter ici"]},

    {"annexe": "T2", "cle": "regularite_fiscale",
     "nom": "Attestation de régularité fiscale",
     "organisme": "Direction générale des finances publiques",
     "delivree_le": None, "valable_jusqu_au": None,
     "couvre": ("d_fiscal_social", "d_obligatoires"),
     "renouvellement_mois": 12,
     "manques": ["attestation à demander sur impots.gouv.fr, espace "
                 "professionnel",
                 "date de délivrance et date de fin de validité à porter ici"]},

    {"annexe": "T3", "cle": "extrait_kbis",
     "nom": "Extrait Kbis",
     "organisme": "Greffe du tribunal de commerce",
     "delivree_le": None, "valable_jusqu_au": None,
     # Le Kbis prouve l'absence de liquidation judiciaire — un cas
     # d'exclusion FACULTATIF (art. L2141-7 s. CCP) — et il porte la situation
     # de l'entreprise que les interdictions obligatoires visent aussi.
     "couvre": ("d_facultatives", "d_obligatoires"),
     "renouvellement_mois": 3,
     "manques": ["extrait à demander (monidenum.fr ou greffe)",
                 "date de délivrance à porter ici"]},

    {"annexe": "T4", "cle": "casier_dirigeant",
     "nom": "Bulletin n° 3 du casier judiciaire du dirigeant",
     "organisme": "Casier judiciaire national",
     "delivree_le": None, "valable_jusqu_au": None,
     # C'est la pièce des interdictions OBLIGATOIRES : les condamnations
     # visées aux art. L2141-1 et L2141-4 CCP. Elle ne se joint presque
     # jamais au dossier — elle se tient, pour que l'affirmation soit faite en
     # connaissance de cause plutôt que de mémoire.
     "couvre": ("d_obligatoires",),
     "renouvellement_mois": 12,
     "manques": ["bulletin à demander sur casier-judiciaire.justice.gouv.fr",
                 "date de délivrance à porter ici"]},

    {"annexe": "T5", "cle": "assurance_rc_pro",
     "nom": "Attestation d'assurance responsabilité civile professionnelle",
     "organisme": "Assureur",
     "delivree_le": None, "valable_jusqu_au": None,
     "couvre": ("d_facultatives",),
     "renouvellement_mois": 12,
     "manques": ["attestation à demander à l'assureur",
                 "montants de garantie et date d'échéance à porter ici"]},
]

# ── CE QUE CHAQUE DÉCLARATION EXIGE COMME PREUVE, ET CE QUI N'EN A PAS ─────
# DEUX CAS N'ONT AUCUNE ATTESTATION, ET LE DIRE EST LE POINT :
#   · l'engagement de l'acte d'engagement (B1) n'affirme aucun fait — il
#     ENGAGE. Aucune pièce ne peut le « prouver » : il se lit, puis il se
#     signe ;
#   · la déclaration du SOUS-TRAITANT (DC4, cadre K1) porte sur le
#     sous-traitant. Aucune attestation de CONSEILPREV ne la soutient — c'est
#     au sous-traitant de fournir les siennes. Faire couvrir celle-là par nos
#     propres pièces serait la faute la plus facile à commettre ici.
PREUVES_ATTENDUES = {
    "d_exclusion":     ("vigilance_urssaf", "regularite_fiscale",
                        "extrait_kbis", "casier_dirigeant"),
    "d_obligatoires":  ("vigilance_urssaf", "regularite_fiscale",
                        "casier_dirigeant"),
    "d_facultatives":  ("extrait_kbis", "assurance_rc_pro"),
    "d_fiscal_social": ("vigilance_urssaf", "regularite_fiscale"),
    "d_engagement":    (),
    "d_exclusion_st":  (),
}

# Pourquoi les deux ensembles vides le sont — dit ici, pour qu'une lecture du
# code ne conclue pas à un oubli.
SANS_PREUVE_INTERNE = {
    "d_engagement": "N'affirme aucun fait : engage. Rien ne le prouve, il se "
                    "lit puis se signe.",
    "d_exclusion_st": "Porte sur le SOUS-TRAITANT. Les attestations de "
                      "CONSEILPREV ne la soutiennent pas — le sous-traitant "
                      "fournit les siennes.",
}

# ── LA NOTE DE MÉTHODE — STRATÉGIE DD DES CENTRES DE DONNÉES ──────────────
NOTE_DD = {
    "titre": "Stratégie de développement durable des centres de données",
    "sous_titre": "Cadre méthodologique et livrables — offre de conseil "
                  "CONSEILPREV",
    "volets": [
        {"numero": 1, "titre": "Comprendre la durabilité et l'approche "
                               "commerciale"},
        {"numero": 2, "titre": "Approche technologique et opérationnelle"},
        {"numero": 3, "titre": "Mise en œuvre et pilotage"},
    ],
    "indicateurs": [
        {"cle": "PUE", "objet": "Énergie totale rapportée à l'énergie des "
                                "équipements informatiques",
         "norme": "ISO/IEC 30134-2"},
        {"cle": "WUE", "objet": "Consommation d'eau rapportée à l'énergie "
                                "informatique", "norme": "ISO/IEC 30134-9"},
        {"cle": "REF", "objet": "Part d'énergie d'origine renouvelable",
         "norme": "ISO/IEC 30134-3"},
        {"cle": "ERF", "objet": "Part d'énergie réutilisée, notamment la "
                                "chaleur fatale", "norme": "ISO/IEC 30134-6"},
        {"cle": "ITEU / ITEE", "objet": "Taux d'utilisation et efficacité des "
                                        "équipements informatiques",
         "norme": "ISO/IEC 30134-4 et 30134-5"},
        {"cle": "Émissions", "objet": "Bilan des émissions de gaz à effet de "
                                      "serre, périmètres 1, 2 et 3",
         "norme": "GHG Protocol, Bilan Carbone"},
    ],
    "livrables": [
        {"cle": "L1", "phase": "Cadrage", "nom": "Note de cadrage et enjeux"},
        {"cle": "L2", "phase": "Cadrage",
         "nom": "Analyse des exigences applicables"},
        {"cle": "L3", "phase": "Référentiel",
         "nom": "Diagnostic et référence de performance"},
        {"cle": "L4", "phase": "Référentiel",
         "nom": "Cartographie des risques et contraintes"},
        {"cle": "L5", "phase": "Argumentaire", "nom": "Analyse de rentabilité"},
        {"cle": "L6", "phase": "Argumentaire",
         "nom": "Charte durable et ancrage RSE"},
        {"cle": "L7", "phase": "Technique",
         "nom": "Plan d'optimisation technique"},
        {"cle": "L8", "phase": "Technique",
         "nom": "Plan de supervision et d'automatisation"},
        {"cle": "L9", "phase": "Mise en œuvre",
         "nom": "Stratégie durable et feuille de route"},
        {"cle": "L10", "phase": "Mise en œuvre",
         "nom": "Dispositif de suivi et de reporting"},
        {"cle": "L11", "phase": "Reconnaissance", "nom": "Dossier de "
                                                         "certification"},
    ],
    "manques": [
        "Le document renvoie lui-même la vérification du calendrier "
        "réglementaire à la date de la mission : « le détail des obligations "
        "applicables et leur calendrier sont à vérifier au regard de l'état "
        "du droit ». Cette vérification n'est pas faite ici.",
    ],
}

# ── LE PAPIER EN-TÊTE ─────────────────────────────────────────────────────
# LES CHAMPS SONT DÉCLARÉS, PAS DEVINÉS DANS LE TEXTE. Un gabarit dont on
# chercherait les crochets à l'exécution laisserait passer un « [Corps du
# courrier] » oublié dans un courrier envoyé.
PAPIER_ENTETE = {
    "bandeau": "C O N S E I L P R E V",
    "accroche": IDENTITE["activite"],
    "champs": ["date", "destinataire", "adresse_destinataire", "objet",
               "corps"],
    "formule": "Je vous prie d'agréer, Madame, Monsieur, l'expression de mes "
               "salutations distinguées.",
    "signataire": "%s\n%s, %s" % (IDENTITE["representant_nom"],
                                  IDENTITE["representant_qualite"],
                                  "CONSEILPREV"),
    "pied": "CONSEILPREV SARL au capital de %s — SIREN %s — TVA %s\n"
            "%s — %s — %s" % (
                IDENTITE["capital"], IDENTITE["siren"], IDENTITE["tva"],
                IDENTITE["adresse"], IDENTITE["telephone"],
                IDENTITE["courriel"]),
}

# ── CE QUE CHAQUE DOCUMENT COUVRE DU DOSSIER DE CANDIDATURE ───────────────
# LA CORRESPONDANCE EST DÉCLARÉE ICI, jamais devinée sur les mots : un module
# qui rapprocherait « qualifications » de « aptitude technique » par
# ressemblance de vocabulaire finirait par rapprocher n'importe quoi.
DOCUMENTS = {
    "qualifications": {
        "nom": "Qualifications d'une entreprise",
        "fichier": "qualifications.pdf",
        "couvre": ["atd_atp"],
        "aide": "Les neuf qualifications professionnelles et la voie par "
                "laquelle chacune se justifie. Elle NE remplace PAS les "
                "attestations : elle dit lesquelles joindre.",
    },
    "references": {
        "nom": "Références d'une entreprise",
        "fichier": "references.pdf",
        "couvre": ["references"],
        "aide": "Les missions conduites, avec client, montant, période et "
                "part réellement tenue.",
    },
    "note_dd": {
        "nom": "Stratégie de développement durable des centres de données",
        "fichier": "strategie-dd-datacenters.pdf",
        "couvre": ["qse", "moyens"],
        "aide": "La démarche, les référentiels mobilisés et les onze "
                "livrables. Sert de note de méthode ; elle ne vaut pas "
                "certificat.",
    },
    "papier_entete": {
        "nom": "Papier en-tête",
        "fichier": "papier-entete.pdf",
        "couvre": [],
        "aide": "Le gabarit des courriers. Il ne couvre aucune pièce par "
                "lui-même : il porte celles qui s'écrivent.",
    },
}


# ── CE QUI SE CORRIGE, ET CE QUI NE SE CORRIGE PAS ────────────────────────
# UNE TABLE N'EST PAS UN PDF : ce dossier vivra, parce qu'une qualification
# s'obtient, une période se retrouve, un client donne son accord de citation.
# Les corrections sont donc des DONNÉES, appliquées par-dessus la table
# déclarée — la table reste l'origine, la correction dit ce qui a bougé depuis.
#
# LES TROUS NE SE CORRIGENT PAS DIRECTEMENT, ILS SE COMBLENT. Renseigner le
# client de R8 le fait disparaître du décompte tout seul, parce que le manque
# est DÉDUIT du champ. Pouvoir effacer un manque sans remplir le champ
# permettrait de faire passer pour complète une référence qui ne l'est pas —
# et c'est exactement ce que ce module existe pour empêcher.
CHAMPS_CORRIGIBLES = {
    "identite": tuple(sorted(IDENTITE)),
    "qualifications": ("intitule", "voie", "appui", "manques"),
    "references": ("nom", "client", "montant", "periode", "part", "objet",
                   "manques"),
    # `couvre` n'est PAS corrigible : ce qu'une attestation prouve relève du
    # droit, pas de la saisie. Laisser corriger ce champ permettrait de faire
    # couvrir une déclaration par n'importe quelle pièce — et l'affirmation
    # passerait alors sans preuve, en ayant l'air prouvée.
    "attestations": ("nom", "organisme", "delivree_le", "valable_jusqu_au",
                     "manques"),
}


def _index(table, champ_cle):
    return {x[champ_cle]: i for i, x in enumerate(table)}


def appliquer(corrections=None):
    """La table corrigée, et le journal de ce qui a été REFUSÉ.

    UNE CORRECTION QUI NE DÉSIGNE RIEN EST REFUSÉE ET NOMMÉE, jamais ignorée.
    Une correction avalée en silence fait croire à une modification qui n'a
    pas eu lieu — et c'est au moment de déposer le dossier qu'on s'en aperçoit.

    LA CIBLE S'ÉCRIT « table.repère.champ » : « references.R8.client »,
    « qualifications.A1.appui », « identite.siret ». Le repère est l'annexe,
    parce que c'est lui qui figure sur le document d'origine et sur les pièces
    jointes — une clé interne ne se retrouve nulle part sur le papier.
    """
    qualifications = [dict(x, manques=list(x["manques"]))
                      for x in QUALIFICATIONS]
    references = [dict(x, manques=list(x["manques"])) for x in REFERENCES]
    attestations = [dict(x, manques=list(x["manques"])) for x in ATTESTATIONS]
    identite = dict(IDENTITE)
    refuses = []
    par_table = {"qualifications": (qualifications,
                                    _index(qualifications, "annexe")),
                 "references": (references, _index(references, "annexe")),
                 "attestations": (attestations,
                                  _index(attestations, "annexe"))}

    for cible, valeur in sorted((corrections or {}).items()):
        morceaux = str(cible).split(".")
        table = morceaux[0]
        if table == "identite":
            if len(morceaux) != 2 or morceaux[1] not in CHAMPS_CORRIGIBLES["identite"]:
                refuses.append({"cible": cible, "motif": "champ_inconnu"})
                continue
            identite[morceaux[1]] = valeur
            continue
        if table not in par_table or len(morceaux) != 3:
            refuses.append({"cible": cible, "motif": "cible_illisible"})
            continue
        lignes, index = par_table[table]
        repere, champ = morceaux[1], morceaux[2]
        if repere not in index:
            refuses.append({"cible": cible, "motif": "repere_inconnu"})
            continue
        if champ not in CHAMPS_CORRIGIBLES[table]:
            refuses.append({"cible": cible, "motif": "champ_non_corrigible"})
            continue
        if champ == "manques":
            if not isinstance(valeur, list) or any(
                    not isinstance(x, str) for x in valeur):
                refuses.append({"cible": cible, "motif": "manques_mal_formes"})
                continue
        elif champ == "voie" and valeur not in VOIES_JUSTIFICATION:
            refuses.append({"cible": cible, "motif": "voie_inconnue"})
            continue
        elif champ in ("delivree_le", "valable_jusqu_au"):
            # UNE DATE MAL FORMÉE EST REFUSÉE, PAS AVALÉE. Rangée telle
            # quelle, elle se lirait ensuite comme absente : l'attestation
            # paraîtrait manquante alors qu'elle a été saisie, et personne ne
            # saurait que la saisie n'avait pas pris.
            if valeur is not None and _date(valeur) is None:
                refuses.append({"cible": cible, "motif": "date_illisible"})
                continue
        lignes[index[repere]][champ] = valeur
    # LA SIGNATURE A CHANGÉ, DÉLIBÉRÉMENT : elle rendait quatre valeurs, elle
    # en rend cinq depuis que les attestations sont corrigibles. Un appelant
    # non mis à jour lève une ValueError au dépaquetage — bruyant, donc sûr.
    return qualifications, references, identite, attestations, refuses


def _sans_valeur(x):
    return x is None or not str(x).strip()


def _date(x):
    """Une date ISO (AAAA-MM-JJ) en objet `date`, ou None.

    NE LÈVE JAMAIS. Un champ mal saisi devient un manque compté, pas une
    exception : l'état du dossier doit se calculer même quand une ligne est
    abîmée, sinon une seule faute de frappe rendrait tout le dossier illisible
    au moment précis où on en a besoin.
    """
    if not x:
        return None
    try:
        return datetime.date(*[int(v) for v in str(x).strip()[:10].split("-")])
    except (ValueError, TypeError):
        return None


def _aujourdhui(aujourdhui=None):
    """La date du jour, ou celle qu'on impose. L'argument existe POUR LES
    RÈGLES : sans lui, une règle sur la péremption deviendrait fausse le jour
    où l'attestation d'essai périme, et personne ne saurait pourquoi."""
    d = _date(aujourdhui) if aujourdhui else None
    return d or datetime.date.today()


def etat_attestations(aujourdhui=None, table=None):
    """Chaque attestation : absente, périmée, ou valide — et pour combien de jours.

    ON MESURE LA VALIDITÉ, ON NE LA CONSTATE PAS. Une attestation « présente »
    ne veut rien dire : une attestation de vigilance URSSAF de l'an dernier est
    présente et sans valeur. C'est la date d'échéance comparée à aujourd'hui
    qui décide, et c'est elle qui est rendue.
    """
    jour = _aujourdhui(aujourdhui)
    lignes, valides, perimees, absentes = [], [], [], []
    for a in (table if table is not None else ATTESTATIONS):
        fin = _date(a.get("valable_jusqu_au"))
        debut = _date(a.get("delivree_le"))
        if fin is None:
            etat, jours = ("absente", None)
        elif fin < jour:
            etat, jours = ("perimee", (fin - jour).days)
        else:
            etat, jours = ("valide", (fin - jour).days)
        ligne = {"annexe": a.get("annexe"), "cle": a.get("cle"),
                 "nom": a.get("nom"), "organisme": a.get("organisme"),
                 "delivree_le": debut.isoformat() if debut else None,
                 "valable_jusqu_au": fin.isoformat() if fin else None,
                 "couvre": list(a.get("couvre") or ()),
                 "etat": etat, "jours": jours,
                 "manques": list(a.get("manques") or [])}
        lignes.append(ligne)
        {"valide": valides, "perimee": perimees,
         "absente": absentes}[etat].append(a.get("cle"))
    return {"lignes": lignes, "total": len(lignes),
            "valides": valides, "perimees": perimees, "absentes": absentes,
            "jour": jour.isoformat()}


# Les trois états d'une déclaration au regard de ses preuves. « prouvee » n'est
# PAS le contraire de « incomplete » : un troisième état existe, et le
# confondre avec l'un des deux est l'erreur que cette énumération empêche.
COUVERTURES = ("prouvee", "incomplete", "sans_preuve_interne")


def couverture(cle_declaration, aujourdhui=None, table=None):
    """Ce qui prouve une déclaration, ce qui manque, et ce qui ne se prouve pas.

    LE PIÈGE QUE CETTE FONCTION ÉVITE. Deux déclarations n'attendent AUCUNE
    attestation de CONSEILPREV : l'engagement de l'acte d'engagement, qui
    n'affirme aucun fait, et la déclaration du sous-traitant, qui porte sur un
    tiers. Une liste d'attentes vide rendrait « tout est là » — donc
    « prouvée » — pour la raison exactement inverse de celle qui compte. Elles
    reçoivent donc un état À ELLES, et l'affirmation devra les traiter comme
    telles au lieu de les laisser passer pour prouvées.
    """
    etat = etat_attestations(aujourdhui, table)
    par_cle = {l["cle"]: l for l in etat["lignes"]}
    attendues = list(PREUVES_ATTENDUES.get(cle_declaration, ()))
    if cle_declaration not in PREUVES_ATTENDUES:
        return {"cle": cle_declaration, "etat": "incomplete",
                "motif": "declaration_inconnue", "attendues": [],
                "valides": [], "manquantes": [], "jour": etat["jour"]}
    if not attendues:
        return {"cle": cle_declaration, "etat": "sans_preuve_interne",
                "motif": SANS_PREUVE_INTERNE.get(cle_declaration, ""),
                "attendues": [], "valides": [], "manquantes": [],
                "jour": etat["jour"]}
    valides = [c for c in attendues
               if (par_cle.get(c) or {}).get("etat") == "valide"]
    manquantes = [{"cle": c,
                   "nom": (par_cle.get(c) or {}).get("nom", c),
                   "etat": (par_cle.get(c) or {}).get("etat", "inconnue"),
                   "jours": (par_cle.get(c) or {}).get("jours")}
                  for c in attendues if c not in valides]
    return {"cle": cle_declaration,
            "etat": "prouvee" if not manquantes else "incomplete",
            "motif": "", "attendues": attendues, "valides": valides,
            "manquantes": manquantes, "jour": etat["jour"]}


def etat_qualifications(table=None):
    """Les neuf qualifications, et ce qui manque à chacune."""
    lignes = []
    for q in (QUALIFICATIONS if table is None else table):
        lignes.append(dict(q, complete=not q["manques"],
                           voie_nom=VOIES_JUSTIFICATION[q["voie"]]["nom"]))
    return {"total": len(lignes),
            "completes": sum(1 for x in lignes if x["complete"]),
            "a_completer": sum(1 for x in lignes if not x["complete"]),
            "manques": sum(len(x["manques"]) for x in lignes),
            "lignes": lignes}


def etat_references(minimum=None, table=None):
    """Les références, et combien sont RÉELLEMENT utilisables.

    UNE RÉFÉRENCE INCOMPLÈTE N'EST PAS UNE RÉFÉRENCE, et c'est la mesure qui
    compte : annoncer huit références là où l'acheteur en trouvera quatre
    documentées fait perdre plus qu'un dossier — cela fait douter du reste.

    `minimum` VIENT DU DOSSIER DE CANDIDATURE, jamais d'un chiffre écrit ici :
    la pièce s'appelle « Références — six au minimum », et c'est elle qui fixe
    la barre. Le recopier créerait une seconde vérité.
    """
    # LES TROUS STRUCTURELS SONT DÉDUITS DES CHAMPS, JAMAIS RECOPIÉS À LA
    # MAIN. La première rédaction portait « Période à compléter » dans
    # `manques` ET laissait `periode` à None : le même trou ressortait deux
    # fois, et le décompte des manques enflait tout seul. `manques` ne porte
    # donc plus que ce qu'aucun champ ne peut exprimer — un client anonymisé,
    # une mission en cours.
    lignes = []
    for r in (REFERENCES if table is None else table):
        trous = []
        if _sans_valeur(r["client"]):
            trous.append("Client non nommé — une référence dont le maître "
                         "d'ouvrage n'est pas nommé ne se vérifie pas.")
        if _sans_valeur(r["periode"]):
            trous.append("Période non renseignée — c'est sur elle que "
                         "l'acheteur juge l'antériorité.")
        if _sans_valeur(r["montant"]):
            trous.append("Montant non renseigné — c'est sur lui que "
                         "l'acheteur juge la taille.")
        trous += list(r["manques"])
        lignes.append(dict(r, manques=trous, complete=not trous))
    utilisables = sum(1 for x in lignes if x["complete"])
    etat = {"total": len(lignes), "utilisables": utilisables,
            "a_completer": len(lignes) - utilisables, "lignes": lignes}
    if minimum is not None:
        etat["minimum"] = minimum
        etat["manque_au_minimum"] = max(0, minimum - utilisables)
        etat["atteint"] = utilisables >= minimum
    return etat


def minimum_references(nom_piece):
    """Le minimum exigé, LU sur le nom de la pièce du dossier de candidature.

    « Références — six au minimum » : le chiffre est écrit en toutes lettres
    là-bas. Le recopier ici en ferait une seconde vérité, qui divergerait le
    jour où l'une des deux serait corrigée. Un nom qui cesserait de porter un
    nombre rend `None` — et l'état des références ne prétend alors à aucune
    barre plutôt que d'en inventer une.
    """
    mots = {"deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6,
            "sept": 7, "huit": 8, "neuf": 9, "dix": 10}
    bas = (nom_piece or "").lower()
    if "minimum" not in bas and "au moins" not in bas:
        return None
    for mot, valeur in mots.items():
        if re.search(r"\b%s\b" % mot, bas):
            return valeur
    m = re.search(r"\b(\d{1,2})\b", bas)
    return int(m.group(1)) if m else None


def etat(pieces_candidature=None, corrections=None, aujourdhui=None):
    """Le dossier entier : ce qu'il porte, ce qui lui manque, ce qu'il couvre.

    `pieces_candidature` est la liste des pièces de `ao_dc.DOSSIER_CANDIDATURE`
    — passée en argument plutôt qu'importée, pour que ce module reste mesurable
    sans dépendre de l'autre.
    """
    par_cle = {p["cle"]: p for p in (pieces_candidature or [])}
    mini = minimum_references(
        (par_cle.get("references") or {}).get("nom"))
    qualifications, references, identite, attestations, refuses = \
        appliquer(corrections)
    q = etat_qualifications(qualifications)
    r = etat_references(mini, references)
    t = etat_attestations(aujourdhui, attestations)
    # LA COUVERTURE DES SIX DÉCLARATIONS, ÉNUMÉRÉE — pas échantillonnée. Elle
    # dit, pour chacune, si la preuve est là, périmée, ou si la déclaration
    # n'en attend aucune de nous. Elle NE REMPLIT RIEN : aucune de ces six
    # rubriques ne reçoit jamais de valeur, quelle que soit la couverture.
    couvertures = [couverture(c, aujourdhui, attestations)
                   for c in sorted(PREUVES_ATTENDUES)]
    documents = []
    for cle, d in DOCUMENTS.items():
        couvre = [{"cle": c, "nom": (par_cle.get(c) or {}).get("nom") or c}
                  for c in d["couvre"]]
        inconnues = [c for c in d["couvre"] if par_cle and c not in par_cle]
        documents.append({
            "cle": cle, "nom": d["nom"], "aide": d["aide"],
            "fichier": d["fichier"],
            "present": os.path.exists(os.path.join(DOSSIER_ORIGINE,
                                                   d["fichier"])),
            "couvre": couvre, "couvre_inconnues": inconnues,
        })
    documents.sort(key=lambda x: x["cle"])
    return {
        "version": VERSION, "etabli_le": ETABLI_LE,
        "identite": identite, "corrections_refusees": refuses,
        "corrigibles": {k: list(v) for k, v in CHAMPS_CORRIGIBLES.items()},
        "qualifications": q, "references": r, "note_dd": NOTE_DD,
        "attestations": t, "couvertures": couvertures,
        "sans_preuve_interne": dict(SANS_PREUVE_INTERNE),
        "papier_entete": PAPIER_ENTETE, "documents": documents,
        "voies": VOIES_JUSTIFICATION,
        # Ce qui reste à faire compte AUSSI les attestations absentes ou
        # périmées : les omettre ferait annoncer un dossier prêt alors que
        # rien ne prouve ce qu'il faudra affirmer.
        "a_completer": (q["a_completer"] + r["a_completer"]
                        + len(t["absentes"]) + len(t["perimees"])),
        "note": NOTE_DOSSIER,
    }


NOTE_DOSSIER = (
    "CE DOSSIER EST CELUI DE CONSEILPREV, et il ne sort pas de "
    "l'administration : les pièces qu'il porte ne sont servies à aucun client "
    "du module. Il DIT ce qui manque, il ne le produit pas — une attestation "
    "se demande à l'organisme qui la délivre, un certificat se scanne, un "
    "montant se confirme au contrat. Une référence dont le client, la période "
    "ou le montant manque n'est pas comptée comme utilisable : annoncer six "
    "références là où l'acheteur en trouvera quatre documentées fait douter "
    "de tout le reste du dossier.")


# ══ LA FICHE DE CANDIDATURE, TIRÉE DU DOSSIER PLUTÔT QUE RETAPÉE ═════════
#
# CE QUE CETTE PORTE CHANGE. Les vingt-trois pièces d'une réponse comptent
# soixante-quatre rubriques ; trente-huit d'entre elles viennent de l'identité
# du candidat, c'est-à-dire des vingt champs de `ao_dc.CHAMPS_CANDIDAT`. Ces
# vingt champs ne dépendent PAS de la consultation : ce sont ceux de
# CONSEILPREV, et ils sont déjà écrits ici. Les retaper à chaque consultation
# était la plus grosse part du travail manuel restant.
#
# ELLE NE SERT QUE L'ADMINISTRATION, et cela n'a rien d'accessoire : ce sont
# les données de CONSEILPREV. La réponse à consultation est désormais un outil
# interne — déclaré dans `acces.API_ADMIN` —, ce qui rend ce report légitime.
# Le jour où la section s'ouvrirait à des clients, cette porte devrait rester
# fermée : un client répond avec SON identité, jamais avec celle du cabinet.
#
# CE QU'ELLE NE FAIT PAS, ET LE DIT. Dix champs sur vingt ne sont pas portés
# par les documents d'origine — le SIRET y figure explicitement comme absent.
# Les inventer produirait un DC1 faux ; les taire ferait croire le formulaire
# complet. Ils ressortent donc NOMMÉS, avec l'endroit où les trouver, comme les
# attestations le font déjà.

# Où chaque champ manquant se trouve. Écrit ici plutôt que dans l'écran : c'est
# une propriété du champ, pas de la page qui l'affiche.
OU_TROUVER = {
    "siret": "sur l'avis de situation INSEE (avis-situation-sirene.insee.fr)",
    "rcs": "sur l'extrait Kbis, mention « RCS » suivie de la ville et du numéro",
    "naf": "sur l'avis de situation INSEE, code APE/NAF à quatre chiffres et "
           "une lettre",
    "effectif": "effectif moyen annuel — bilan social ou déclaration sociale "
                "nominative",
    # Ces trois-là se déduisent d'`EXERCICES` : ils ne manquent que si le
    # dossier porte moins de trois exercices clos. Le dire ainsi plutôt que
    # « liasse fiscale » envoie au bon endroit — le module, pas le classeur.
    "ca_n1": "chiffre d'affaires du dernier exercice clos — à porter dans "
             "EXERCICES, avec la source qui l'établit",
    "ca_n2": "chiffre d'affaires de l'avant-dernier exercice clos — à porter "
             "dans EXERCICES, avec sa source",
    "ca_n3": "chiffre d'affaires du troisième exercice clos — à porter dans "
             "EXERCICES, avec sa source",
    "assurance_compagnie": "sur l'attestation de responsabilité civile "
                           "professionnelle en cours",
    "assurance_police": "numéro de police, sur la même attestation",
    "assurance_echeance": "date d'échéance, sur la même attestation",
}

def _rangs_exercices(exercices):
    """Les trois derniers exercices clos, rangés : {ca_n1, ca_n2, ca_n3}.

    ELLE NE LIT PAS L'HORLOGE. « Le dernier exercice clos » est le plus récent
    de ceux que le dossier PORTE, pas celui que le calendrier suggère : si
    l'exercice 2026 est clos mais pas encore versé ici, le rappeler ne le ferait
    pas exister, et un `datetime.now()` ferait simplement rendre un document
    différent selon le jour où on le demande.

    ELLE REND MOINS DE TROIS RANGS PLUTÔT QUE DE COMPLÉTER. Deux exercices
    portés donnent deux rangs ; le troisième ressort alors comme MANQUANT, avec
    l'endroit où le trouver — ce qui se corrige — au lieu d'un montant recopié
    du précédent, qui ne se voit pas.
    """
    lignes = [x for x in (exercices or [])
              if isinstance(x, dict) and x.get("annee") is not None
              and str(x.get("ca") or "").strip()]
    lignes.sort(key=lambda x: -int(x["annee"]))
    return {"ca_n%d" % (i + 1): x["ca"] for i, x in enumerate(lignes[:3])}


def _verifier_identite():
    """Les contrôles d'intégrité de l'identité, passés à l'import.

    POURQUOI À L'IMPORT ET NON DANS UNE RÈGLE. Un SIRET incohérent avec son
    SIREN part dans un DC1 déposé chez un acheteur. Le module doit refuser de
    démarrer, pas attendre qu'on lance la suite de tests.
    """
    siren = re.sub(r"\D", "", IDENTITE["siren"] or "")
    siret = re.sub(r"\D", "", IDENTITE["siret"] or "")
    if siret:
        if not siret.startswith(siren):
            raise AssertionError(
                "SIRET %s : ne commence pas par le SIREN %s" % (siret, siren))
        if len(siret) != 14:
            raise AssertionError("SIRET %s : %d chiffres au lieu de 14"
                                 % (siret, len(siret)))
        if not _luhn(siret):
            raise AssertionError("SIRET %s : clé de contrôle fausse" % siret)
    annees = [x["annee"] for x in EXERCICES]
    if annees != sorted(annees, reverse=True) or len(set(annees)) != len(annees):
        raise AssertionError(
            "EXERCICES : les années doivent être distinctes et décroissantes, "
            "lues %r" % (annees,))
    for x in EXERCICES:
        if not str(x.get("source") or "").strip():
            raise AssertionError(
                "Exercice %s : un montant sans source ne se vérifie pas."
                % x.get("annee"))


def _luhn(chiffres):
    """La clé de contrôle SIREN/SIRET. Elle ne prouve pas que le numéro EXISTE
    — seulement qu'il n'a pas été mal recopié. Les deux SIRET qui circulaient
    pour ce cabinet la passaient tous les deux : c'est bien un garde-fou de
    frappe, pas une vérification d'identité."""
    total, double = 0, False
    for ch in reversed(str(chiffres)):
        d = int(ch)
        if double:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        double = not double
    return total % 10 == 0


_ADRESSE = re.compile(r"^\s*(.+?)\s*,\s*(\d{5})\s+(.+?)\s*$")


def _scinder_adresse(brut):
    """« 19 rue X, 75015 Paris » → les trois champs du formulaire.

    ELLE REFUSE PLUTÔT QUE DE DEVINER. Une adresse qui ne se laisse pas
    découper rend (None, None, None) : le champ ressort alors comme manquant,
    ce qui se corrige, au lieu d'un code postal inventé, qui ne se voit pas.
    """
    m = _ADRESSE.match(str(brut or ""))
    return (m.group(1), m.group(2), m.group(3)) if m else (None, None, None)


def fiche_candidat(identite=None):
    """La fiche AO du cabinet : ce que le dossier fournit, et ce qui manque.

    Rend {fiche, manques, fournis, attendus} — `fiche` ne porte QUE des valeurs
    réelles, jamais une chaîne vide qui passerait pour une réponse.
    """
    ident = dict(identite if identite is not None else IDENTITE)
    rue, cp, ville = _scinder_adresse(ident.get("adresse"))
    rangs = _rangs_exercices(ident.get("exercices"))
    brut = {
        "raison_sociale": ident.get("raison_sociale"),
        "forme_juridique": ident.get("forme_juridique"),
        "siret": ident.get("siret"),
        # LE SIREN ET LA TVA ÉTAIENT DÉTENUS ET N'ARRIVAIENT NULLE PART.
        #
        # CE QUI A ÉTÉ MESURÉ. `IDENTITE` porte le SIREN « 494 530 157 » et le
        # numéro de TVA « FR 24 494 530 157 » — vérifiés cohérents entre eux
        # par la règle de clé. Cette fonction ne les recopiait simplement pas :
        # ils ne franchissaient jamais la porte de la fiche candidat, et les
        # cases SIREN et TVA des formulaires de l'État restaient vides sur un
        # dossier qui contient les deux valeurs. En aval, `ao_dc.derive()` sait
        # les déduire — mais À PARTIR DU SIRET, qui manque. Deux chemins vers
        # la même valeur, tous deux coupés.
        #
        # ILS SONT ICI ET NON DÉDUITS : une valeur déclarée l'emporte sur une
        # valeur calculée, parce qu'elle est vérifiable sur un document. La
        # déduction reste, pour le jour où le SIRET sera porté.
        "siren": ident.get("siren"),
        "tva": ident.get("tva"),
        "capital": ident.get("capital"),
        "rcs": ident.get("rcs"),
        "naf": ident.get("naf"),
        "adresse": rue,
        "code_postal": cp,
        "ville": ville,
        "telephone": ident.get("telephone"),
        "courriel": ident.get("courriel"),
        "representant_nom": ident.get("representant_nom"),
        "representant_qualite": ident.get("representant_qualite"),
        "effectif": ident.get("effectif"),
        # LE RANG SE CALCULE, IL NE SE RECOPIE PAS — voir `EXERCICES`. Une
        # correction explicite (« identite.ca_n1 ») l'emporte quand même :
        # c'est la seule façon de rattraper un exercice non encore porté ici
        # sans attendre une mise à jour du module.
        "ca_n1": ident.get("ca_n1") or rangs.get("ca_n1"),
        "ca_n2": ident.get("ca_n2") or rangs.get("ca_n2"),
        "ca_n3": ident.get("ca_n3") or rangs.get("ca_n3"),
        "assurance_compagnie": ident.get("assurance_compagnie"),
        "assurance_police": ident.get("assurance_police"),
        "assurance_echeance": ident.get("assurance_echeance"),
    }
    fiche = {k: str(v).strip() for k, v in brut.items()
             if v is not None and str(v).strip()}
    manques = [{"cle": k,
                "ou_trouver": OU_TROUVER.get(k, "à porter au dossier "
                                                "d'entreprise")}
               for k in brut if k not in fiche]
    return {"fiche": fiche, "manques": manques,
            "fournis": len(fiche), "attendus": len(brut)}


def entete_markdown(objet="", destinataire="", reference="", aujourdhui=None):
    """L'en-tête CONSEILPREV, en Markdown, prêt à coiffer un document.

    POURQUOI ICI ET PAS DANS `ao_dc`. Le papier à en-tête est une donnée du
    CABINET : son bandeau, son accroche, son signataire et son pied de page
    vivent avec l'identité, et changent avec elle. `ao_dc` compose des pièces
    de marché ; il n'a pas à connaître le capital social ni le numéro de TVA.

    CE QUI NE LE REÇOIT JAMAIS : les quatre formulaires de l'État. Le DC1, le
    DC2, le DC4 et l'ATTRI1 sortent tels que le ministère les publie ; leur
    coller un en-tête d'entreprise en ferait des fac-similés, refusés à
    l'ouverture des plis — ou pire, acceptés et faux. La distinction est tenue
    par `ao_dc.markdown_piece`, et une règle la mesure.
    """
    d = _aujourdhui(aujourdhui)
    L = ["**%s**" % PAPIER_ENTETE["bandeau"], "",
         "*%s*" % PAPIER_ENTETE["accroche"], "",
         "---", ""]
    if destinataire:
        L += [str(destinataire), ""]
    L.append("%s, le %s" % (IDENTITE["adresse"].rsplit(" ", 1)[-1],
                            d.strftime("%d/%m/%Y")))
    L.append("")
    if objet:
        L += ["**Objet — %s**" % objet, ""]
    if reference:
        L += ["**Référence de la consultation — %s**" % reference, ""]
    L += ["---", ""]
    return L


def pied_markdown():
    """Le pied de page du papier à en-tête : la formule, la signature, les
    mentions légales. Séparé de l'en-tête parce qu'il se pose APRÈS le corps."""
    return ["", "---", "", PAPIER_ENTETE["formule"], "",
            PAPIER_ENTETE["signataire"].replace("\n", "  \n"), "",
            "---", "", "*%s*" % PAPIER_ENTETE["pied"].replace("\n", " — ")]


# LA GARDE PASSE À L'IMPORT, PAS DANS UNE RÈGLE. Un SIRET incohérent avec son
# SIREN, ou un montant sans source, partiraient dans un DC1 déposé chez un
# acheteur. Le module refuse de démarrer plutôt que d'attendre la suite.
_verifier_identite()
