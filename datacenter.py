"""Moteur d'ingénierie pour centres de données bas carbone.

CE QUE CE MODULE EST, ET CE QU'IL N'EST PAS
───────────────────────────────────────────
Il calcule, de façon DÉTERMINISTE et TRAÇABLE, le triptyque qui décide
aujourd'hui d'un appel d'offres de centre de données : l'énergie, l'eau et le
carbone — les trois étant couplés, ce qui est précisément la difficulté.

Il ne prétend PAS produire des calculs inédits. La thermodynamique du
refroidissement évaporatif est établie depuis un siècle, les indicateurs PUE,
WUE, CUE et ERE sont normalisés (ISO/IEC 30134), et présenter cela comme une
première serait démonté au premier comité technique — c'est-à-dire à l'endroit
exact où ce serait le plus coûteux.

Ce qui est rare, en revanche, et ce que ce module apporte :

  1. LE COUPLAGE. Baisser le PUE par du refroidissement évaporatif augmente la
     consommation d'eau ; passer au dry cooler supprime l'eau du site mais
     augmente l'électricité, donc l'eau consommée en amont par la production
     électrique — et sur un mix thermique, l'arbitrage peut s'inverser. Presque
     tous les dossiers traitent ces grandeurs séparément. Ici elles sont
     calculées ensemble, et l'arbitrage est explicite.

  2. L'EAU DE LA SOURCE. Le WUE de site est celui que tout le monde publie. Le
     WUE de source — l'eau prélevée pour produire l'électricité consommée —
     est souvent d'un ordre de grandeur supérieur et change les conclusions.

  3. LE CARBONE INCORPORÉ. Un centre très efficace en exploitation peut être
     dominé par le carbone de sa construction et de ses serveurs. Sur un mix
     décarboné, l'incorporé devient MAJORITAIRE : l'ignorer conduit à optimiser
     ce qui ne pèse plus.

  4. LA TRAÇABILITÉ. Chaque résultat porte sa formule, ses entrées, sa source
     normative et une incertitude. Un chiffre sans sa méthode n'est pas
     opposable dans une offre.

Aucun modèle de langage n'intervient dans ce fichier. Deux appels avec les
mêmes entrées donnent le même résultat, au chiffre près — c'est la condition
pour qu'une note de calcul puisse être annexée à une offre.
"""

import math

VERSION = "2026-08-a"

# ═══════════════════════════════════════════════════════════════════════════
#  RÉFÉRENTIEL — constantes physiques, facteurs et seuils réglementaires
#
#  Chaque entrée porte sa source et sa date. Une constante sans provenance est
#  une opinion déguisée en donnée : dans une réponse à appel d'offres, c'est la
#  première chose qu'un évaluateur technique attaque.
# ═══════════════════════════════════════════════════════════════════════════

CONSTANTES = {
    "chaleur_latente_eau_kJ_kg": {
        "valeur": 2442.0,
        "unite": "kJ/kg à 25 °C",
        "source": "Chaleur latente de vaporisation de l'eau, tables thermodynamiques usuelles",
        "note": "Varie de 2 501 kJ/kg à 0 °C à 2 406 kJ/kg à 40 °C. La valeur à "
                "25 °C est retenue comme moyenne d'exploitation ; l'écart sur la "
                "plage utile reste inférieur à 2 %.",
    },
    "eau_evaporee_par_kWh_thermique_L": {
        "valeur": 3600.0 / 2442.0,     # ≈ 1,474 L par kWh de chaleur rejetée
        "unite": "L/kWh thermique",
        "source": "Déduit : 1 kWh = 3 600 kJ ; 3 600 / 2 442",
        "note": "MAJORANT physique : c'est l'eau évaporée si TOUTE la chaleur "
                "part en chaleur latente. Une tour réelle en rejette une part en "
                "SENSIBLE — l'air ressort plus chaud — typiquement 20 à 25 % en "
                "conditions courantes, et jusqu'à 75-80 % par temps froid "
                "(ASHRAE Handbook, HVAC Systems & Equipment, ch. Cooling "
                "Towers). L'évaporation réelle est donc un peu PLUS FAIBLE ; le "
                "majorant est retenu pour dimensionner l'eau, où la prudence "
                "est de surestimer — jamais pour accuser un chiffre plus bas.",
    },
}

# Facteur eau de la production électrique (Energy Water Intensity Factor).
# C'est l'eau CONSOMMÉE (évaporée, non restituée), pas l'eau prélevée : la
# distinction change les résultats d'un facteur dix sur le nucléaire en circuit
# ouvert, et la confondre est l'erreur la plus fréquente des dossiers.
# Le NOM vit ici, avec la donnée, et non dans une seconde table. Les listes
# déroulantes affichaient le code ISO — « DE », « DK », « PL » — que le lecteur
# doit traduire de tête, et qui se confondent (« NO » norvégien lu comme un
# refus, « IT » comme l'informatique). Un code identifie ; il ne se lit pas.
EWIF_PAYS = {
    "FR": {"nom": "France", "valeur": 1.30,
           "mix": "nucléaire majoritaire, hydraulique",
           "note": "Forte évaporation des tours aéroréfrigérantes du parc nucléaire."},
    "DE": {"nom": "Allemagne", "valeur": 1.10,
           "mix": "renouvelables, gaz, charbon résiduel"},
    "SE": {"nom": "Suède", "valeur": 0.45,
           "mix": "hydraulique, nucléaire, éolien"},
    "NO": {"nom": "Norvège", "valeur": 0.30, "mix": "hydraulique quasi exclusif"},
    "FI": {"nom": "Finlande", "valeur": 0.55,
           "mix": "nucléaire, biomasse, hydraulique"},
    "IE": {"nom": "Irlande", "valeur": 0.55, "mix": "éolien, gaz"},
    "NL": {"nom": "Pays-Bas", "valeur": 0.80, "mix": "gaz, éolien offshore"},
    "ES": {"nom": "Espagne", "valeur": 1.00,
           "mix": "solaire, éolien, gaz, nucléaire"},
    "IT": {"nom": "Italie", "valeur": 1.05, "mix": "gaz, hydraulique, solaire"},
    "PL": {"nom": "Pologne", "valeur": 1.60, "mix": "charbon majoritaire"},
    "DK": {"nom": "Danemark", "valeur": 0.35, "mix": "éolien majoritaire"},
    # ── Les dix-sept autres États membres ──────────────────────────────────
    # MÊME NATURE, MÊME INCERTITUDE que les douze premiers : ce sont des ordres
    # de grandeur tirés de la littérature, à ±40 %, et EWIF_SOURCE dit déjà
    # qu'ils doivent être remplacés par le facteur du fournisseur ou du
    # gestionnaire de réseau. Les ajouter ne les rend pas plus sûrs — cela
    # évite seulement qu'un projet en Tchéquie ou au Portugal soit calculé sur
    # la moyenne européenne faute de trouver son pays dans la liste.
    "AT": {"nom": "Autriche", "valeur": 0.45,
           "mix": "hydraulique majoritaire, éolien"},
    "BE": {"nom": "Belgique", "valeur": 1.15, "mix": "nucléaire, gaz, éolien"},
    "BG": {"nom": "Bulgarie", "valeur": 1.45,
           "mix": "charbon, nucléaire, hydraulique"},
    "CY": {"nom": "Chypre", "valeur": 0.35,
           "mix": "fioul lourd, solaire",
           "note": "Centrales refroidies à l'eau de mer : la consommation "
                   "d'eau douce du mix est faible, ce que le seul facteur ne "
                   "montre pas."},
    "CZ": {"nom": "Tchéquie", "valeur": 1.50,
           "mix": "charbon, nucléaire à tours de refroidissement"},
    "EE": {"nom": "Estonie", "valeur": 1.20,
           "mix": "schistes bitumineux en recul, éolien"},
    "GR": {"nom": "Grèce", "valeur": 0.85, "mix": "gaz, solaire, lignite en recul"},
    "HR": {"nom": "Croatie", "valeur": 0.60,
           "mix": "hydraulique, gaz, importations"},
    "HU": {"nom": "Hongrie", "valeur": 1.25,
           "mix": "nucléaire à tours, gaz, solaire"},
    "LT": {"nom": "Lituanie", "valeur": 0.50,
           "mix": "éolien, importations, hydraulique"},
    "LU": {"nom": "Luxembourg", "valeur": 0.60,
           "mix": "très largement importé",
           "note": "Le mix consommé dépend surtout des pays voisins : le "
                   "facteur national a peu de sens ici, et c'est le contrat "
                   "de fourniture qui tranche."},
    "LV": {"nom": "Lettonie", "valeur": 0.40,
           "mix": "hydraulique majoritaire, gaz"},
    "MT": {"nom": "Malte", "valeur": 0.30,
           "mix": "gaz et interconnexion, refroidissement en eau de mer"},
    "PT": {"nom": "Portugal", "valeur": 0.60,
           "mix": "éolien, hydraulique, solaire, gaz"},
    "RO": {"nom": "Roumanie", "valeur": 1.00,
           "mix": "hydraulique, nucléaire, gaz, charbon"},
    "SI": {"nom": "Slovénie", "valeur": 1.10,
           "mix": "nucléaire, hydraulique, lignite"},
    "SK": {"nom": "Slovaquie", "valeur": 1.35,
           "mix": "nucléaire à tours de refroidissement, hydraulique"},
    # Ni un pays ni un choix par défaut anodin : une MOYENNE. Le nommer
    # « Union européenne » tout court laisserait croire à une implantation
    # européenne précise, alors que c'est le repli quand le pays n'est pas
    # arrêté — et le calcul le dit ensuite dans ses avertissements.
    "UE": {"nom": "Union européenne — moyenne, à défaut de pays arrêté",
           "valeur": 1.00,
           "mix": "moyenne européenne, à défaut de pays renseigné"},
}
def nom_pays(code):
    """Le nom en clair d'un code pays, et le code lui-même s'il est inconnu.

    Rendre le code brut vaut mieux que rendre vide : un lecteur peut encore
    reconnaître « PL », il ne peut rien faire d'une phrase amputée."""
    return (EWIF_PAYS.get(code) or {}).get("nom") or (code or "—")


EWIF_SOURCE = ("Ordres de grandeur convergents de la littérature sur l'intensité "
               "en eau de la production électrique (consommation, hors prélèvement "
               "restitué). À REMPLACER par la valeur du fournisseur ou de "
               "l'exploitant du réseau dès qu'elle est disponible : ces facteurs "
               "varient fortement selon la technologie de refroidissement des "
               "centrales, pas seulement selon le mix. RÉSERVE de méthode pour "
               "les mix hydrauliques (NO, SE, AT, LV…) : l'évaporation des "
               "retenues n'est PAS comptée ici — son attribution à l'électricité "
               "est contestée et peut décupler le facteur (Macknick et al., "
               "NREL) ; au fil de l'eau, l'effet est faible.")

# Intensité carbone du réseau, en gCO2e par kWh consommé. Moyenne annuelle.
# La moyenne annuelle ne convient PAS pour arbitrer un pilotage horaire : voir
# `avertissements` dans le résultat.
INTENSITE_RESEAU = {
    "FR": 56, "SE": 41, "NO": 30, "FI": 79, "DK": 151, "IE": 296,
    "DE": 344, "NL": 268, "ES": 158, "IT": 257, "PL": 635, "UE": 242,
    # Les dix-sept autres États membres, même nature et même réserve que
    # ci-dessus : moyennes annuelles approchées, à remplacer par la donnée
    # officielle du gestionnaire de réseau pour l'année de référence.
    "AT": 110, "BE": 130, "BG": 370, "CY": 600, "CZ": 410, "EE": 460,
    "GR": 330, "HR": 180, "HU": 200, "LT": 160, "LU": 110, "LV": 110,
    "MT": 400, "PT": 140, "RO": 240, "SI": 210, "SK": 110,
}

# Les deux tables sont indexées par le MÊME code : une clé présente d'un côté
# et pas de l'autre ferait retomber silencieusement sur la moyenne européenne
# pour l'une des deux grandeurs, sans que rien ne le signale. Contrôlé au
# chargement du module — c'est le seul moment où l'oubli est encore gratuit.
_ecart_pays = set(EWIF_PAYS) ^ set(INTENSITE_RESEAU)
if _ecart_pays:
    raise AssertionError(
        "Référentiel pays incohérent : %s figure dans une seule des deux "
        "tables (EWIF_PAYS / INTENSITE_RESEAU)." % ", ".join(sorted(_ecart_pays)))
del _ecart_pays
# Le MILLÉSIME est servi avec la donnée : l'évaluateur de cette page dit au
# client qu'« un facteur sans millésime ne se défend pas » — la règle vaut
# d'abord pour le moteur lui-même. Valeurs recoupées en août 2026 sur les
# jeux ouverts Ember (ember-energy.org) et l'indicateur AEE : FR 56 et
# UE 242 g/kWh sont les valeurs 2023 publiées ; quelques pays portent déjà
# leur valeur 2024 (DE 344 contre 371-381 en 2023) — d'où la fourchette.
INTENSITE_MILLESIME = "2023-2024"
INTENSITE_SOURCE = ("Moyennes annuelles location-based, millésime "
                    + INTENSITE_MILLESIME + " selon pays (dernier exercice "
                    "publié), arrondies — jeux ouverts Ember et Agence "
                    "européenne pour l'environnement. Pour une offre, utiliser "
                    "la donnée officielle du gestionnaire de réseau de l'année "
                    "de référence, ou le facteur contractuel du fournisseur "
                    "(approche « market-based », GHG Protocol Scope 2 Guidance).")

# Familles de refroidissement. Les plages recouvrent des conceptions réelles ;
# elles ne remplacent pas une étude de site, elles servent à cadrer et comparer.
REFROIDISSEMENT_SOURCE = ("Plages de conception à PLEINE charge, recoupées des "
                          "enquêtes annuelles Uptime Institute (moyenne mondiale "
                          "du parc installé ≈ 1,5-1,6, tirée vers le haut par "
                          "l'existant) et des retours de conception récents. "
                          "Elles cadrent une comparaison de familles ; la "
                          "machine retenue se juge sur sa courbe constructeur, "
                          "puis sur l'essai de performance.")
REFROIDISSEMENT = {
    "air_dx": {
        "nom": "Détente directe (DX) sur air",
        "pue_partiel": (1.35, 1.60),
        "eau_site": "nulle",
        "note": "Simple, sans eau, mais le plus consommateur. Encore majoritaire "
                "sur les petites salles.",
    },
    "eau_glacee": {
        "nom": "Eau glacée avec groupe froid",
        "pue_partiel": (1.25, 1.45),
        "eau_site": "faible à nulle si condenseur sec",
        "note": "Référence historique des grands sites.",
    },
    "free_cooling_air": {
        "nom": "Free cooling direct sur air extérieur",
        "pue_partiel": (1.10, 1.25),
        "eau_site": "nulle",
        "note": "Dépend entièrement du climat et de la température d'air admise "
                "en salle (classe ASHRAE). Filtration et humidité à maîtriser.",
    },
    "adiabatique": {
        "nom": "Free cooling indirect à assistance adiabatique",
        "pue_partiel": (1.08, 1.20),
        "eau_site": "modérée, saisonnière",
        "note": "L'eau n'est consommée que pendant les heures chaudes : le WUE "
                "annuel masque des pointes estivales, qui sont précisément le "
                "moment où la ressource est tendue.",
    },
    "tour_evaporative": {
        "nom": "Tour de refroidissement évaporative",
        "pue_partiel": (1.10, 1.25),
        "eau_site": "élevée, continue",
        "note": "Le meilleur compromis énergétique historique, et le plus "
                "exposé au risque eau.",
    },
    "liquide_dlc": {
        "nom": "Refroidissement liquide direct (DLC, plaques froides)",
        "pue_partiel": (1.05, 1.15),
        "eau_site": "nulle à faible selon le rejet",
        "note": "Capte 70 à 80 % de la chaleur au plus près du composant, à haute "
                "température — ce qui rend le rejet sec possible ET la chaleur "
                "réutilisable. Impose une densité et une conception serveur "
                "compatibles.",
    },
    "immersion": {
        "nom": "Immersion (monophasique)",
        "pue_partiel": (1.03, 1.10),
        "eau_site": "nulle à faible",
        "note": "Capte la quasi-totalité de la chaleur. Contraintes fortes de "
                "maintenance, de fluide et de garantie constructeur.",
    },
}

# Classes ASHRAE : température d'air admise à l'entrée des équipements. Élargir
# la plage est le levier le moins cher qui existe — il ne coûte aucun matériel —
# mais il engage la garantie constructeur, ce qui doit être écrit noir sur blanc.
CLASSES_ASHRAE = {
    "A1": {"plage_c": (15, 32), "note": "Serveurs d'entreprise, stockage. Le plus contraint."},
    "A2": {"plage_c": (10, 35), "note": "Serveurs volume. Plage courante."},
    "A3": {"plage_c": (5, 40), "note": "Autorise beaucoup plus de free cooling."},
    "A4": {"plage_c": (5, 45), "note": "Maximise le free cooling ; matériel qualifié requis."},
}
ASHRAE_SOURCE = ("ASHRAE TC 9.9, Thermal Guidelines for Data Processing "
                 "Environments. Les plages par classe sont les ADMISSIBLES ; "
                 "l'enveloppe RECOMMANDÉE, commune, reste 18-27 °C — exploiter "
                 "durablement au-delà se décide avec le constructeur, pas par "
                 "défaut.")

# Les incertitudes du référentiel, écrites UNE fois. Elles vivaient dans les
# chaînes des notes de calcul (« ±15 % », « ±50 % ») ; le jour où un évaluateur
# de chiffre annoncé en a eu besoin comme BORNES, les écrire une seconde fois
# aurait créé deux vérités — la note aurait pu dire ±15 quand le verdict
# jugeait à ±20. Une seule constante, deux usages : la phrase ET la borne.
# Part de la chaleur rejetée en LATENT par une tour, en moyenne ANNUELLE.
# 75-80 % en conditions courantes, bien moins par temps froid où le sensible
# domine (ASHRAE Handbook — HVAC Systems & Equipment, ch. Cooling Towers ;
# SPX, Cooling Tower Fundamentals). Le plancher annuel retenu, 0,60, couvre
# les climats froids : c'est LUI qui borne par le bas ce qu'une tour évapore
# pour une chaleur donnée — le tout-latent (1,0) borne par le haut. Juger un
# volume annoncé avec le majorant comme plancher accusait à tort tout
# fournisseur honnête dont la tour rejette du sensible.
PART_LATENTE_MIN = 0.60
INCERTITUDE_APPOINT = 0.15       # appoint total (purge, dérive), ±15 %
INCERTITUDE_INCORPORE = 0.50     # ordres de grandeur sectoriels, ±50 %

# Carbone incorporé. Amorti sur la durée de vie : c'est ce qui permet de le
# comparer à l'exploitation, et sans cet amortissement la comparaison n'a
# aucun sens.
INCORPORE = {
    "serveur_kgCO2e": {"valeur": 1200, "duree_vie_ans": 5,
                       "note": "Serveur biprocesseur de volume, fabrication et "
                               "transport. Varie du simple au triple selon la "
                               "configuration mémoire et stockage."},
    "batiment_kgCO2e_par_kW_IT": {"valeur": 2500, "duree_vie_ans": 25,
                                  "note": "Gros œuvre, second œuvre, hors "
                                          "équipements techniques."},
    "technique_kgCO2e_par_kW_IT": {"valeur": 1400, "duree_vie_ans": 15,
                                   "note": "Groupes froids, onduleurs, batteries, "
                                           "groupes électrogènes, distribution."},
}
INCORPORE_SOURCE = ("Ordres de grandeur issus des analyses de cycle de vie "
                    "publiées du secteur : base ouverte Boavizta, empreintes "
                    "produit publiées par les constructeurs (PCF Dell, HPE, "
                    "Lenovo), FDES de la base INIES pour la construction. "
                    "À REMPLACER par les déclarations environnementales produit "
                    "(FDES / EPD, ISO 14025) des équipements réellement retenus "
                    "dès qu'elles sont disponibles : l'écart entre un ordre de "
                    "grandeur et une EPD peut atteindre un facteur deux.")

# L'ANCRAGE MANAGEMENT : les grandeurs de ce moteur ne vivent pas seules.
# Le PUE calculé ici devient, en exploitation, un INDICATEUR DE PERFORMANCE
# ÉNERGÉTIQUE au sens de l'ISO 50001 ; les arbitrages eau-énergie-carbone
# deviennent des réponses aux questions centrales de l'ISO 26000. Nourri des
# deux guides versés à la base documentaire (livre blanc ISO 50001, guide
# RSE 2022) — paraphrasés, jamais recopiés.
MANAGEMENT = {
    "iso_50001": {
        "titre": "ISO 50001:2018 — système de management de l'énergie (SMÉn)",
        "apporte": "Le cadre qui fait VIVRE les grandeurs de cette étude en "
                   "exploitation : la revue énergétique (art. 6.3) identifie "
                   "les usages énergétiques significatifs — le refroidissement "
                   "d'un centre de données en est un par construction —, les "
                   "indicateurs de performance énergétique (art. 6.4) suivent "
                   "ce que l'étude a promis, et la situation énergétique de "
                   "référence (art. 6.5) fige le point de comparaison AVANT la "
                   "mise en service. Sans SER posée au départ, aucune "
                   "amélioration n'est démontrable ensuite.",
        "ipe_naturel": "Le PUE en catégorie ISO/IEC 30134-2 est l'IPÉ naturel "
                       "du site ; le WUE (30134-9) et le CUE le complètent — "
                       "les MÊMES grandeurs que cette étude, pas d'autres.",
        "exige": ["une équipe énergie nommée, portée par la direction — pas un "
                  "tableur orphelin",
                  "un plan de mesurage RÉPÉTABLE : mêmes points, mêmes "
                  "conditions, sinon la revue énergétique ne se compare pas "
                  "d'une année à l'autre",
                  "des audits internes réguliers et une documentation qui "
                  "prouve — c'est elle que l'auditeur externe lit",
                  "l'articulation avec les systèmes existants (ISO 9001, "
                  "14001, 45001) : un système intégré, pas un silo de plus"],
        "certifiable": "Oui — et la certification ISO 50001 dispense de "
                       "l'audit énergétique périodique de l'art. 11 EED.",
    },
    "iso_26000": {
        "titre": "ISO 26000:2010 — lignes directrices sur la responsabilité "
                 "sociétale",
        "apporte": "Le cadre AMONT de la stratégie : la responsabilité d'une "
                   "organisation vis-à-vis des impacts de ses décisions sur "
                   "la société et l'environnement — comportement éthique et "
                   "transparent, attentes des parties prenantes, intégration "
                   "dans toute l'organisation. Pour un centre de données, "
                   "deux questions centrales pèsent d'abord : l'environnement "
                   "(énergie, eau, carbone — les trois piliers de cette "
                   "étude) et les communautés et développement local — "
                   "l'acceptabilité de l'eau, du bruit et du foncier se joue "
                   "là, pas dans la salle serveurs.",
        "questions_centrales": [
            "gouvernance de l'organisation", "droits de l'homme",
            "relations et conditions de travail", "environnement",
            "loyauté des pratiques",
            "questions relatives aux consommateurs",
            "communautés et développement local"],
        "achats": "La loyauté des pratiques porte les ACHATS RESPONSABLES : "
                  "exiger les déclarations environnementales (ISO 14025, "
                  "EN 15804+A2) dans les marchés en est l'application directe "
                  "— la même exigence que l'évaluateur de carbone incorporé.",
        "certifiable": "Non — lignes directrices. La preuve passe par une "
                       "ÉVALUATION (AFAQ 26000, label LUCIE) et par des "
                       "outils : analyse de cycle de vie, bilan carbone — "
                       "ceux que cette étude prépare.",
    },
    "source": "Livre blanc ISO 50001 et guide RSE 2022 versés à la base "
              "documentaire du cabinet ; ISO 50001:2018 ; ISO 26000:2010. "
              "Textes des normes : AFNOR / ISO (voir sources consultables).",
}

# Seuils et obligations qui structurent une offre européenne.
CADRE_UE = {
    "eed_reporting": {
        "titre": "Directive efficacité énergétique (UE) 2023/1791, art. 12 — "
                 "et règlement délégué (UE) 2024/1364",
        "portee": "Centres de données dont la puissance informatique installée "
                  "atteint ou dépasse 500 kW.",
        "exige": ["consommation d'énergie totale", "PUE", "consommation d'eau et WUE",
                  "part d'énergie renouvelable (REF)", "chaleur fatale réutilisée (ERF)",
                  "trafic de données entrant et sortant", "quantité de données stockées",
                  "surface, puissance installée, taux d'utilisation"],
        "note": "Déclaration annuelle. Une offre qui ne prévoit pas la MESURE de "
                "ces grandeurs promet une conformité qu'elle ne pourra pas tenir : "
                "l'instrumentation se conçoit avant, pas après.",
    },
    "cndcp": {
        "titre": "Climate Neutral Data Centre Pact (engagement sectoriel volontaire)",
        "cibles": {
            "pue_climat_froid": 1.30,
            "pue_climat_tempere_chaud": 1.40,
            "wue_site_max": 0.40,
            "energie_sans_carbone": "100 %",
        },
        "note": "Engagement volontaire, non réglementaire. Il sert de repère de "
                "marché : un dossier qui s'en écarte doit le justifier.",
    },
    "eed_audit_smen": {
        "titre": "Directive efficacité énergétique (UE) 2023/1791, art. 11 — "
                 "audit énergétique et système de management de l'énergie",
        # Le livre blanc ISO 50001 versé à la base l'annonçait sous l'empire de
        # l'art. 8 de 2012/27/UE : le critère de TAILLE d'entreprise allait
        # devenir un critère de CONSOMMATION. C'est fait — et un centre de
        # données franchit ces seuils très tôt.
        "seuil_audit_tj": 10.0,
        "seuil_smen_tj": 85.0,
        "exige": ["au-delà de 10 TJ/an de consommation moyenne : audit "
                  "énergétique (EN 16247-1 / ISO 50002) d'ici octobre 2026, "
                  "puis tous les quatre ans",
                  "au-delà de 85 TJ/an : système de management de l'énergie "
                  "CERTIFIÉ ISO 50001 d'ici octobre 2027 — l'audit périodique "
                  "ne suffit plus"],
        "note": "Les seuils s'apprécient au niveau de l'ENTREPRISE, toutes "
                "activités confondues, en moyenne sur les trois derniers "
                "exercices : un site sous les seuils ne met pas l'entreprise "
                "hors du champ — et un seul centre de données suffit souvent "
                "à les franchir.",
    },
    "en50600": {
        "titre": "EN 50600 / EN 50600-4-x — indicateurs de performance",
        "note": "Définit PUE (4-2), REF (4-3), ERF (4-6). Le vocabulaire d'un "
                "cahier des charges européen s'y réfère : employer d'autres "
                "définitions rend les offres incomparables.",
    },
    "iso30134": {
        "titre": "ISO/IEC 30134 — indicateurs de performance clés",
        "parties": {"-2": "PUE", "-3": "REF", "-4": "ITEE", "-5": "ITEU",
                    "-6": "ERF", "-8": "CER", "-9": "WUE"},
    },
}


def fr(x, dec=None):
    """Un nombre écrit en français, pour les phrases composées ici.

    L'interface sait déjà mettre en forme les VALEURS ; mais ce module compose
    aussi des phrases — « plage de conception 1,1 – 1,25 », « repère 0,4 L/kWh » —
    et une virgule oubliée dans l'une d'elles suffit à faire passer une note de
    calcul pour une traduction automatique. C'est le genre de détail qu'un
    évaluateur remarque avant le contenu.
    """
    if x is None:
        return "—"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if dec is None:
        dec = 0 if abs(v) >= 100 else (1 if abs(v) >= 10 else 3)
    s = ("%%.%df" % dec) % v
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s.replace(".", ",")


def _plage(a, b):
    return {"min": round(a, 4), "max": round(b, 4)}


# ═══════════════════════════════════════════════════════════════════════════
#  LA CHARGE PARTIELLE — UN SEUL SEUIL, ÉCRIT UNE SEULE FOIS
#
#  CE QUI N'ALLAIT PAS. Ce coefficient portait DEUX seuils différents sans que
#  rien ne le dise. Le calcul appliquait sa pénalité sous 0,60 ; le texte d'aide
#  du champ, l'étiquette de la suggestion et la recommandation d'amélioration
#  annonçaient tous 0,55. Un lecteur qui saisissait 0,57 lisait donc qu'il était
#  au-dessus du seuil pendant que le moteur le pénalisait déjà.
#
#  ET UNE ZONE PLATE NON DÉCLARÉE. Au-dessus du point de conception, la pénalité
#  vaut zéro : 0,65, 0,80, 0,90 et 1,00 donnent EXACTEMENT le même PUE. Le
#  formulaire proposait pourtant « 0,80 — site mature, bien rempli » comme un
#  choix qui compte. On cliquait, rien ne bougeait, et on concluait au blocage.
#
#  LES DEUX SEUILS SONT DISTINCTS ET LE RESTENT — ils ne répondent pas à la même
#  question — mais ils sont désormais NOMMÉS, et tous les textes servis les
#  citent par calcul. Deux nombres écrits à la main dans quatre fichiers finissent
#  toujours par diverger ; un seul, dérivé, ne le peut pas.
# ═══════════════════════════════════════════════════════════════════════════

# En dessous, les auxiliaires ne suivent plus proportionnellement la charge et
# le PUE se dégrade. C'est le point de conception du modèle, pas une norme.
CHARGE_POINT_CONCEPTION = 0.60
# Pente de la dégradation, par point de charge manquant.
CHARGE_PENTE = 0.45
# Autre question, autre seuil : à partir de quand consolider les charges
# devient-il le premier levier d'amélioration à proposer.
CHARGE_CONSOLIDER = 0.55


# CE QUI EST PLAT, ET CE QUI NE L'EST PAS — ÉCRIT UNE FOIS.
#
# Au-dessus du point de conception, la pénalité s'annule : LE PUE cesse de
# varier. Le reste, lui, ne cesse pas. L'énergie annuelle, les volumes d'eau et
# le carbone d'exploitation sont PROPORTIONNELS à la charge réelle, puisque
# c'est elle qui fixe la puissance appelée. Seuls les RATIOS — PUE, WUE, CUE —
# restent constants, et c'est normal : ce sont des rapports.
#
# LA VERSION PRÉCÉDENTE DE CETTE PHRASE ÉTAIT FAUSSE, et coûteuse. Elle disait
# « changer cette valeur ne changera pas le résultat ». Le lecteur laissait donc
# le taux à sa valeur par défaut pour un site qui tourne à 0,85, et repartait
# avec une énergie annuelle sous-estimée de 30 % et un carbone sous-estimé de
# 11 %. Le défaut venait d'une sur-correction : on venait de corriger l'inverse
# — un formulaire qui semblait bloqué parce que le PUE ne bougeait pas — et on
# a étendu au résultat entier ce qui n'était vrai que du PUE.
#
# Les quatre textes servis lisent désormais cette constante. Une phrase écrite à
# la main dans quatre fichiers finit toujours par diverger ; une seule, lue, ne
# le peut pas.
PLATEAU_PUE = ("le PUE ne varie plus avec la charge — mais l'énergie, l'eau "
               "et le carbone restent proportionnels à elle, et cette valeur "
               "compte donc toujours")


def penalite_charge(taux):
    """La pénalité de PUE due à la charge partielle. Zéro au-dessus du point de
    conception : ce modèle ne récompense pas un site mieux rempli, faute de
    terme pour le chiffrer — et une pénalité négative inventée vaudrait moins
    que ce silence, qui est au moins déclaré."""
    t = float(taux)
    if t >= CHARGE_POINT_CONCEPTION:
        return 0.0
    return (CHARGE_POINT_CONCEPTION - t) * CHARGE_PENTE


def _tracer(nom, valeur, unite, formule, entrees, source="", incertitude="",
            note="", bande=None):
    """Un résultat qui se défend tout seul.

    Le format est imposé : dans une note de calcul annexée à une offre, un
    chiffre nu appelle la question « d'où sort-il ? », et ne pas pouvoir y
    répondre en séance coûte le marché.

    `bande` porte l'encadrement EN DONNÉE quand il en existe un. L'incertitude
    reste une phrase, faite pour être lue ; un graphique qui doit la tracer
    devrait sinon la réanalyser au caractère près, et une virgule déplacée dans
    la rédaction casserait le tracé.
    """
    out = {
        "nom": nom,
        "valeur": round(valeur, 4) if isinstance(valeur, float) else valeur,
        "unite": unite,
        "formule": formule,
        "entrees": entrees,
        "source": source,
        "incertitude": incertitude,
        "note": note,
    }
    if bande is not None:
        out["bande"] = bande
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  1. ÉNERGIE
# ═══════════════════════════════════════════════════════════════════════════

def energie(profil):
    """PUE, consommation totale, décomposition des pertes.

    On calcule le PUE à partir de la conception (famille de refroidissement,
    rendements) plutôt que de le recevoir en entrée : un PUE annoncé sans sa
    décomposition n'est pas vérifiable, et c'est le premier point que conteste
    un évaluateur.
    """
    p_it = float(profil.get("puissance_it_kw") or 0)
    taux = float(profil.get("taux_charge") or 0.65)
    heures = float(profil.get("heures_an") or 8760)

    fam = profil.get("refroidissement") or "eau_glacee"
    ref = REFROIDISSEMENT.get(fam) or REFROIDISSEMENT["eau_glacee"]
    pue_bas, pue_haut = ref["pue_partiel"]

    # Un PUE fourni par le maître d'ouvrage prime : c'est un engagement
    # contractuel, pas une hypothèse. On le conserve tel quel et on le SIGNALE.
    pue_impose = profil.get("pue_cible")
    if pue_impose:
        pue = float(pue_impose)
        origine = "PUE cible imposé par le cahier des charges"
        bande = _plage(pue, pue)
    else:
        # La charge partielle dégrade le PUE : les auxiliaires ne suivent pas
        # proportionnellement. Ignorer cet effet est l'erreur la plus courante
        # des dossiers — et la plus visible en exploitation, où le PUE réel
        # dépasse systématiquement le PUE de conception.
        penalite = penalite_charge(taux)
        pue = (pue_bas + pue_haut) / 2 + penalite
        origine = ("moyenne de la plage de conception de la famille retenue, "
                   "majorée de la pénalité de charge partielle" if penalite
                   # AU-DESSUS DU POINT DE CONCEPTION, LE MODÈLE EST PLAT, et il
                   # doit le DIRE. Sans cette phrase, le lecteur qui passe de
                   # 0,65 à 0,80 voit un PUE rigoureusement identique et conclut
                   # que le formulaire est bloqué — ce qui est exactement ce qui
                   # a été signalé. Le modèle ne prétend pas qu'un site mieux
                   # rempli ne gagne rien : il n'a pas de terme pour le chiffrer,
                   # et une pénalité négative inventée serait pire que ce silence.
                   else ("moyenne de la plage de conception de la famille "
                         "retenue — au-dessus de " + fr(CHARGE_POINT_CONCEPTION)
                         + " de charge, ce modèle n'applique aucune pénalité et "
                         + PLATEAU_PUE))
        bande = _plage(pue_bas + penalite, pue_haut + penalite)

    p_moy = p_it * taux
    e_it = p_moy * heures / 1000.0                 # MWh/an
    e_tot = e_it * pue
    e_non_it = e_tot - e_it

    res = {
        "pue": _tracer(
            "PUE — Power Usage Effectiveness", pue, "sans unité",
            "PUE = Énergie totale du site / Énergie des équipements informatiques",
            {"famille": ref["nom"], "plage de conception": fr(pue_bas) + " – " + fr(pue_haut),
             "taux de charge": taux, "origine": origine},
            "ISO/IEC 30134-2 ; EN 50600-4-2",
            "plage de conception " + fr(bande["min"]) + " – " + fr(bande["max"]),
            ref["note"], bande=bande),
        "energie_it_MWh": _tracer(
            "Énergie informatique annuelle", e_it, "MWh/an",
            "E_IT = P_IT × taux de charge × heures / 1000",
            {"P_IT (kW)": p_it, "taux de charge": taux, "heures": heures},
            "", "±5 % (mesure de la charge réelle)"),
        "energie_totale_MWh": _tracer(
            "Énergie totale annuelle du site", e_tot, "MWh/an",
            "E_total = E_IT × PUE",
            {"E_IT (MWh)": round(e_it, 1), "PUE": round(pue, 3)},
            "", "±" + fr((bande["max"] - bande["min"]) / max(pue, 0.01) * 100 / 2, 1) + " % (dispersion du PUE)"),
        "energie_non_it_MWh": _tracer(
            "Énergie des auxiliaires (froid, onduleurs, éclairage)", e_non_it, "MWh/an",
            "E_non_IT = E_total − E_IT",
            {"E_total (MWh)": round(e_tot, 1), "E_IT (MWh)": round(e_it, 1)}),
        "dcie": _tracer(
            "DCiE — rendement d'infrastructure", 100.0 / pue, "%",
            "DCiE = 100 / PUE",
            {"PUE": round(pue, 3)},
            "The Green Grid",
            note="Inverse du PUE. Certains cahiers des charges l'exigent encore."),
        "famille": ref,
    }
    return res


# ═══════════════════════════════════════════════════════════════════════════
#  2. EAU — le calcul que presque personne ne mène jusqu'au bout
# ═══════════════════════════════════════════════════════════════════════════

def eau(profil, res_energie):
    """WUE de site ET WUE de source, avec le détail de l'évaporation.

    Le WUE de site est celui qu'on publie. Le WUE de SOURCE — l'eau consommée
    en amont pour produire l'électricité — est régulièrement supérieur d'un
    ordre de grandeur, et c'est lui qui décide de l'arbitrage entre un
    refroidissement évaporatif et un refroidissement sec. Un dossier qui ne
    présente que le WUE de site conclut souvent à l'inverse de ce qu'il faut
    faire.
    """
    e_it = res_energie["energie_it_MWh"]["valeur"]
    e_tot = res_energie["energie_totale_MWh"]["valeur"]
    pue = res_energie["pue"]["valeur"]

    fam = profil.get("refroidissement") or "eau_glacee"
    # Part de la chaleur rejetée par voie évaporative sur l'année. C'est LE
    # paramètre de conception : il porte tout le compromis eau/énergie.
    part_evap = profil.get("part_evaporative")
    if part_evap is None:
        part_evap = {"tour_evaporative": 0.90, "adiabatique": 0.25,
                     "eau_glacee": 0.10, "air_dx": 0.0, "free_cooling_air": 0.0,
                     "liquide_dlc": 0.05, "immersion": 0.0}.get(fam, 0.10)
    part_evap = max(0.0, min(1.0, float(part_evap)))

    # Cycles de concentration : nombre de fois que l'eau circule avant purge.
    # Plus il est élevé, moins on purge — mais plus l'eau se minéralise, et le
    # traitement devient contraignant. 4 à 6 est la pratique courante.
    coc = float(profil.get("cycles_concentration") or 4.0)
    coc = max(1.5, coc)

    # Toute l'énergie du site finit en chaleur à évacuer. C'est une identité,
    # pas une approximation : un centre de données ne produit aucun travail
    # mécanique utile — il ne fait que déplacer de l'information.
    chaleur_MWh = e_tot
    chaleur_evap_MWh = chaleur_MWh * part_evap

    l_par_kwh = CONSTANTES["eau_evaporee_par_kWh_thermique_L"]["valeur"]
    evaporation_m3 = chaleur_evap_MWh * 1000.0 * l_par_kwh / 1000.0
    # Appoint total = évaporation × CoC/(CoC−1) : il faut remplacer l'eau
    # évaporée ET l'eau purgée pour maintenir la concentration.
    appoint_m3 = evaporation_m3 * coc / (coc - 1.0)
    purge_m3 = appoint_m3 - evaporation_m3

    wue_site = (appoint_m3 * 1000.0) / (e_it * 1000.0) if e_it else 0.0

    pays = (profil.get("pays") or "UE").upper()
    ewif = (EWIF_PAYS.get(pays) or EWIF_PAYS["UE"])["valeur"]
    # WUE_source = WUE_site + EWIF × PUE : l'eau du site, plus l'eau qu'a coûté
    # chaque kWh acheté, rapportée au kWh informatique.
    wue_source = wue_site + ewif * pue
    eau_amont_m3 = (e_tot * 1000.0 * ewif) / 1000.0

    return {
        "part_evaporative": part_evap,
        "evaporation_m3": _tracer(
            "Eau évaporée", evaporation_m3, "m³/an",
            "V_évap = E_rejetée_évaporatif × 1 kWh / chaleur latente",
            {"chaleur rejetée par voie évaporative (MWh)": round(chaleur_evap_MWh, 1),
             "L évaporés par kWh thermique": round(l_par_kwh, 3),
             "part évaporative": part_evap},
            CONSTANTES["eau_evaporee_par_kWh_thermique_L"]["source"],
            "majorant tout-latent ; l'évaporation réelle est plus faible "
            "d'autant que la part sensible monte — jusqu'à −%s %% en moyenne "
            "annuelle (climat froid)" % fr((1 - PART_LATENTE_MIN) * 100),
            "Majorant physique : tout-latent. Une tour réelle rejette aussi du "
            "sensible ; retenu tel quel pour DIMENSIONNER l'eau, par prudence."),
        "purge_m3": _tracer(
            "Eau de purge (déconcentration)", purge_m3, "m³/an",
            "V_purge = V_appoint − V_évap, avec V_appoint = V_évap × CoC/(CoC−1)",
            {"cycles de concentration": coc},
            "Bilan de masse d'une tour ouverte — ASHRAE Handbook, HVAC "
            "Systems & Equipment, ch. Cooling Towers",
            "", "Augmenter les cycles réduit la purge mais durcit le "
                "traitement d'eau et le risque d'entartrement."),
        "appoint_m3": _tracer(
            "Appoint d'eau total du site", appoint_m3, "m³/an",
            "V_appoint = V_évap × CoC / (CoC − 1)",
            {"V_évap (m³)": round(evaporation_m3, 1), "CoC": coc},
            "Bilan de masse d'une tour ouverte — ASHRAE Handbook, HVAC "
            "Systems & Equipment, ch. Cooling Towers",
            "±%s %%" % fr(INCERTITUDE_APPOINT * 100)),
        "wue_site": _tracer(
            "WUE de site", wue_site, "L/kWh_IT",
            "WUE_site = Volume d'eau du site / Énergie informatique",
            {"appoint (m³)": round(appoint_m3, 1), "E_IT (MWh)": round(e_it, 1)},
            "ISO/IEC 30134-9",
            "", "Repère de marché : ≤ " + fr(CADRE_UE["cndcp"]["cibles"]["wue_site_max"])
                + " L/kWh (Climate Neutral Data Centre Pact)."),
        "wue_source": _tracer(
            "WUE de source (site + amont électrique)", wue_source, "L/kWh_IT",
            "WUE_source = WUE_site + EWIF × PUE",
            {"WUE_site": round(wue_site, 3), "EWIF (L/kWh)": ewif,
             "PUE": round(pue, 3), "pays": pays},
            EWIF_SOURCE,
            "±40 % (dispersion des facteurs eau de production)",
            "C'est ce chiffre, et non le WUE de site, qui doit arbitrer entre "
            "évaporatif et sec. Un dry cooler affiche un WUE de site nul tout "
            "en consommant plus d'eau à la source si le mix est thermique."),
        "eau_amont_m3": _tracer(
            "Eau consommée en amont par la production électrique", eau_amont_m3, "m³/an",
            "V_amont = E_total × EWIF",
            {"E_total (MWh)": round(e_tot, 1), "EWIF": ewif},
            EWIF_SOURCE, "±40 %"),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  3. CARBONE — exploitation ET incorporé
# ═══════════════════════════════════════════════════════════════════════════

def carbone(profil, res_energie):
    """CUE, émissions d'exploitation et carbone incorporé amorti.

    Le point qui change les décisions : sur un mix décarboné, l'incorporé
    devient MAJORITAIRE. Optimiser le PUE d'un site français à 1,15 pendant que
    la fabrication des serveurs pèse deux fois l'exploitation, c'est se tromper
    de combat — et un évaluateur technique le verra.
    """
    e_it = res_energie["energie_it_MWh"]["valeur"]
    e_tot = res_energie["energie_totale_MWh"]["valeur"]
    pue = res_energie["pue"]["valeur"]
    p_it = float(profil.get("puissance_it_kw") or 0)

    pays = (profil.get("pays") or "UE").upper()
    intensite = profil.get("intensite_reseau_g")
    origine_i = "valeur fournie (contrat d'électricité ou donnée du gestionnaire)"
    if intensite is None:
        intensite = INTENSITE_RESEAU.get(pays, INTENSITE_RESEAU["UE"])
        # Le NOM du pays, pas son code : cette phrase se lit dans la note de
        # calcul et dans les livrables exportés, où « moyenne annuelle du mix
        # PL » oblige le lecteur à traduire — et invite à se tromper.
        origine_i = "moyenne annuelle du mix %s" % nom_pays(pays)
    intensite = float(intensite)

    # Part d'énergie sans carbone contractualisée (REF). Elle réduit le Scope 2
    # « market-based », jamais le « location-based » — les deux se déclarent, et
    # les confondre est une non-conformité de reporting.
    ref_renouv = max(0.0, min(1.0, float(profil.get("part_renouvelable") or 0.0)))

    co2_local_t = e_tot * intensite / 1000.0
    co2_marche_t = co2_local_t * (1.0 - ref_renouv)
    cue = (co2_local_t * 1000.0) / (e_it * 1000.0) if e_it else 0.0

    # Incorporé, amorti linéairement.
    n_serv = profil.get("nb_serveurs")
    if n_serv is None:
        # À défaut, on estime par la puissance : ~0,5 kW par serveur en charge.
        n_serv = int(p_it / 0.5) if p_it else 0
    s = INCORPORE["serveur_kgCO2e"]
    b = INCORPORE["batiment_kgCO2e_par_kW_IT"]
    t = INCORPORE["technique_kgCO2e_par_kW_IT"]
    inc_serveurs_t = (n_serv * s["valeur"] / s["duree_vie_ans"]) / 1000.0
    inc_batiment_t = (p_it * b["valeur"] / b["duree_vie_ans"]) / 1000.0
    inc_technique_t = (p_it * t["valeur"] / t["duree_vie_ans"]) / 1000.0
    inc_total_t = inc_serveurs_t + inc_batiment_t + inc_technique_t

    total_t = co2_marche_t + inc_total_t
    part_inc = (inc_total_t / total_t * 100.0) if total_t else 0.0

    return {
        "cue": _tracer(
            "CUE — Carbon Usage Effectiveness", cue, "kgCO2e/kWh_IT",
            "CUE = Émissions du site / Énergie informatique  (= PUE × intensité réseau)",
            {"intensité réseau (gCO2e/kWh)": intensite, "PUE": round(pue, 3),
             "origine": origine_i},
            "The Green Grid ; ISO/IEC 30134 (famille)",
            "±20 % (moyenne annuelle contre profil horaire réel)"),
        "co2_exploitation_localise_t": _tracer(
            "Émissions d'exploitation — approche localisée (location-based)",
            co2_local_t, "tCO2e/an",
            "CO2 = E_total × intensité du réseau",
            {"E_total (MWh)": round(e_tot, 1), "intensité (g/kWh)": intensite},
            "GHG Protocol Scope 2 Guidance",
            note="Ce que le site fait réellement émettre au réseau. À déclarer "
                 "TOUJOURS, même quand un contrat vert existe."),
        "co2_exploitation_marche_t": _tracer(
            "Émissions d'exploitation — approche marché (market-based)",
            co2_marche_t, "tCO2e/an",
            "CO2_marché = CO2_localisé × (1 − part d'énergie sans carbone)",
            {"part renouvelable contractualisée": ref_renouv},
            "GHG Protocol Scope 2 Guidance",
            note="Un contrat d'origine renouvelable réduit ce chiffre, pas les "
                 "émissions physiques du réseau. Présenter le seul chiffre marché "
                 "comme l'empreinte du site est une omission que les évaluateurs "
                 "sérieux relèvent."),
        "ref": _tracer(
            "REF — part d'énergie renouvelable", ref_renouv * 100, "%",
            "REF = Énergie renouvelable / Énergie totale",
            {"part contractualisée": ref_renouv},
            "ISO/IEC 30134-3 ; EN 50600-4-3",
            note="Exigé au titre du reporting de la directive efficacité énergétique."),
        "incorpore_serveurs_t": _tracer(
            "Carbone incorporé — serveurs (amorti)", inc_serveurs_t, "tCO2e/an",
            "= nb serveurs × kgCO2e par serveur / durée de vie",
            {"nb serveurs": n_serv, "kgCO2e/serveur": s["valeur"],
             "durée de vie (ans)": s["duree_vie_ans"]},
            INCORPORE_SOURCE,
            "±%s %%" % fr(INCERTITUDE_INCORPORE * 100), s["note"]),
        "incorpore_batiment_t": _tracer(
            "Carbone incorporé — bâtiment (amorti)", inc_batiment_t, "tCO2e/an",
            "= P_IT × kgCO2e par kW / durée de vie",
            {"P_IT (kW)": p_it, "kgCO2e/kW": b["valeur"], "durée de vie": b["duree_vie_ans"]},
            INCORPORE_SOURCE,
            "±%s %%" % fr(INCERTITUDE_INCORPORE * 100)),
        "incorpore_technique_t": _tracer(
            "Carbone incorporé — équipements techniques (amorti)", inc_technique_t,
            "tCO2e/an", "= P_IT × kgCO2e par kW / durée de vie",
            {"P_IT (kW)": p_it, "kgCO2e/kW": t["valeur"], "durée de vie": t["duree_vie_ans"]},
            INCORPORE_SOURCE,
            "±%s %%" % fr(INCERTITUDE_INCORPORE * 100)),
        "empreinte_totale_t": _tracer(
            "Empreinte annuelle totale (exploitation marché + incorporé)",
            total_t, "tCO2e/an",
            "= CO2_marché + incorporé amorti",
            {"exploitation (t)": round(co2_marche_t, 1),
             "incorporé (t)": round(inc_total_t, 1)},
            note="Le périmètre complet. C'est celui que demandent les acheteurs "
                 "publics européens depuis que les critères environnementaux sont "
                 "pondérés."),
        "part_incorpore_pct": _tracer(
            "Part du carbone incorporé dans l'empreinte totale", part_inc, "%",
            "= incorporé / (exploitation + incorporé)",
            {"incorporé (t)": round(inc_total_t, 1), "total (t)": round(total_t, 1)},
            note="Au-delà de 50 %, allonger la durée de vie du matériel et "
                 "réemployer pèsent plus que tout gain de PUE."),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  4. CHALEUR FATALE
# ═══════════════════════════════════════════════════════════════════════════

def chaleur(profil, res_energie):
    """ERF et ERE. La chaleur d'un centre de données n'est pas un déchet.

    Le verrou n'est pas thermique, il est contractuel et géographique : il faut
    un réseau de chaleur à moins de quelques kilomètres et un preneur engagé sur
    quinze ans. Un dossier qui promet la réutilisation sans nommer le preneur
    promet ce qu'il ne maîtrise pas.
    """
    e_tot = res_energie["energie_totale_MWh"]["valeur"]
    e_it = res_energie["energie_it_MWh"]["valeur"]
    pue = res_energie["pue"]["valeur"]

    part = max(0.0, min(1.0, float(profil.get("part_chaleur_reutilisee") or 0.0)))
    fam = profil.get("refroidissement") or "eau_glacee"
    # Température de rejet : c'est elle qui décide de la valorisation possible.
    t_rejet = profil.get("temperature_rejet_c")
    if t_rejet is None:
        t_rejet = {"liquide_dlc": 55, "immersion": 50, "eau_glacee": 35,
                   "tour_evaporative": 32, "adiabatique": 30,
                   "free_cooling_air": 28, "air_dx": 35}.get(fam, 35)
    t_rejet = float(t_rejet)

    e_reuse = e_tot * part
    erf = part
    ere = pue * (1.0 - erf)

    if t_rejet >= 60:
        valorisation = ("Injection directe possible dans un réseau de chaleur "
                        "basse température (4e génération).")
    elif t_rejet >= 45:
        valorisation = ("Injection possible après relevage par pompe à chaleur, "
                        "au coefficient de performance favorable.")
    elif t_rejet >= 30:
        valorisation = ("Valorisation possible mais coûteuse : pompe à chaleur "
                        "obligatoire, dont la consommation doit être déduite du gain.")
    else:
        valorisation = ("Température trop basse pour une valorisation économique "
                        "hors usage de proximité (serres, piscines, séchage).")

    return {
        "erf": _tracer(
            "ERF — Energy Reuse Factor", erf * 100, "%",
            "ERF = Énergie réutilisée / Énergie totale",
            {"part réutilisée": part, "E_total (MWh)": round(e_tot, 1)},
            "ISO/IEC 30134-6 ; EN 50600-4-6",
            note="Exigé au titre du reporting de la directive efficacité énergétique."),
        "ere": _tracer(
            "ERE — Energy Reuse Effectiveness", ere, "sans unité",
            "ERE = PUE × (1 − ERF)",
            {"PUE": round(pue, 3), "ERF": round(erf, 3)},
            "The Green Grid",
            note="Peut descendre SOUS 1 si la réutilisation dépasse les pertes "
                 "d'infrastructure. Ce n'est pas une anomalie de calcul : c'est "
                 "ce qui justifie l'implantation près d'un réseau de chaleur."),
        "energie_reutilisee_MWh": _tracer(
            "Énergie thermique réutilisée", e_reuse, "MWh/an",
            "= E_total × ERF", {"E_total (MWh)": round(e_tot, 1), "ERF": round(erf, 3)}),
        "temperature_rejet_c": t_rejet,
        "valorisation": valorisation,
        "equivalent_logements": int(e_reuse / 10.0) if e_reuse else 0,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  5. LEVIERS — classés par ce qu'ils rapportent, pas par ce qu'ils coûtent
# ═══════════════════════════════════════════════════════════════════════════

def leviers(profil, res):
    """Les actions possibles, chiffrées, avec leurs contreparties.

    Chaque levier porte son EFFET INVERSE quand il en a un. Un levier présenté
    sans sa contrepartie est un argument commercial, pas une recommandation
    d'ingénierie — et dans un appel d'offres, c'est ce qui distingue les deux.
    """
    out = []
    e_it = res["energie"]["energie_it_MWh"]["valeur"]
    e_tot = res["energie"]["energie_totale_MWh"]["valeur"]
    pue = res["energie"]["pue"]["valeur"]
    fam = profil.get("refroidissement") or "eau_glacee"
    pays = (profil.get("pays") or "UE").upper()
    intensite = float(profil.get("intensite_reseau_g")
                      or INTENSITE_RESEAU.get(pays, INTENSITE_RESEAU["UE"]))
    prix = float(profil.get("prix_electricite_eur_mwh") or 110.0)

    def ajoute(titre, gain_mwh, gain_eau_m3, contrepartie, condition, fondement,
               difficulte="moyenne"):
        gain_co2 = gain_mwh * intensite / 1000.0
        out.append({
            "titre": titre,
            "gain_energie_MWh": round(gain_mwh, 1),
            "gain_eau_m3": round(gain_eau_m3, 1),
            "gain_co2_t": round(gain_co2, 1),
            "gain_euros": round(gain_mwh * prix, 0),
            "contrepartie": contrepartie,
            "condition": condition,
            "fondement": fondement,
            "difficulte": difficulte,
        })

    # -- Élargir la plage de température admise ------------------------------
    classe = profil.get("classe_ashrae") or "A2"
    if classe in ("A1", "A2"):
        cible = "A3"
        gain_pue = 0.06 if classe == "A2" else 0.10
        gain = e_it * gain_pue
        ajoute(f"Passer de la classe ASHRAE {classe} à {cible}",
               gain, gain * 0.4,
               "Engage la garantie constructeur : à faire valider par écrit, "
               "équipement par équipement, AVANT l'engagement contractuel.",
               "Matériel qualifié pour la plage élargie.",
               ASHRAE_SOURCE, "faible")

    # -- Refroidissement liquide --------------------------------------------
    if fam not in ("liquide_dlc", "immersion"):
        pue_cible = sum(REFROIDISSEMENT["liquide_dlc"]["pue_partiel"]) / 2
        if pue > pue_cible:
            gain = e_it * (pue - pue_cible)
            ajoute("Refroidissement liquide direct (plaques froides)",
                   gain, gain * 1.2,
                   "Impose une conception serveur compatible et une reprise "
                   "complète de la distribution hydraulique. Non rétrofitable "
                   "sans arrêt.",
                   "Densité supérieure à 20 kW par baie pour que l'économie "
                   "couvre l'investissement.",
                   "ASHRAE Liquid Cooling Guidelines ; retours d'exploitation du secteur",
                   "élevée")

    # -- Sortir de l'évaporatif, ou y entrer : l'arbitrage se calcule --------
    part_evap = res["eau"]["part_evaporative"]
    if part_evap > 0.3:
        eau_evitee = res["eau"]["appoint_m3"]["valeur"] * 0.8
        surcout = e_it * 0.08
        ajoute("Basculer vers un rejet sec (dry cooler) sur la majorité de l'année",
               -surcout, eau_evitee,
               "Coûte environ " + fr(surcout, 0) + " MWh/an de plus, soit "
               + fr(surcout * intensite / 1000.0, 1) + " tCO2e — et une part "
               "de cette énergie consomme de l'eau à la source.",
               "Pertinent en zone de stress hydrique, ou si le mix électrique "
               "est peu intensif en eau.",
               "Arbitrage eau/énergie ; comparer au WUE de SOURCE, pas au WUE de site.",
               "moyenne")
    elif part_evap < 0.1 and pays in ("SE", "NO", "FI", "DK"):
        ajoute("Assistance adiabatique limitée aux heures chaudes",
               e_it * 0.05, -50.0,
               "Introduit une consommation d'eau saisonnière et un traitement "
               "d'eau (risque légionelles à encadrer).",
               "Climat froid : peu d'heures concernées, donc gain énergétique "
               "réel et consommation d'eau faible.",
               "Conception classique du free cooling indirect assisté.",
               "faible")

    # -- Chaleur fatale ------------------------------------------------------
    if res["chaleur"]["erf"]["valeur"] < 5:
        e_valorisable = e_tot * 0.30
        ajoute("Raccordement à un réseau de chaleur (30 % de l'énergie valorisée)",
               0.0, 0.0,
               "Ne réduit PAS la consommation du centre : le gain carbone est "
               "chez le preneur, en chaleur fossile évitée. À ne pas compter "
               "deux fois dans le bilan du site.",
               "Réseau à moins de 3 km et preneur engagé sur la durée "
               "d'amortissement. Sans preneur nommé, l'engagement ne vaut rien.",
               "ISO/IEC 30134-6 ; directive efficacité énergétique art. 26",
               "élevée")
        out[-1]["gain_co2_t"] = round(e_valorisable * 0.20, 1)
        out[-1]["note_gain"] = ("Estimé sur une chaleur fossile évitée à "
                                "200 gCO2e/kWh chez le preneur — à remplacer par "
                                "le facteur réel du réseau.")

    # -- Durée de vie du matériel : le levier que le carbone incorporé impose -
    part_inc = res["carbone"]["part_incorpore_pct"]["valeur"]
    if part_inc > 30:
        gain_inc = res["carbone"]["incorpore_serveurs_t"]["valeur"] * 0.28
        out.append({
            "titre": "Allonger la durée de vie des serveurs de 5 à 7 ans",
            "gain_energie_MWh": 0.0,
            "gain_eau_m3": 0.0,
            "gain_co2_t": round(gain_inc, 1),
            "gain_euros": 0.0,
            "contrepartie": "Rendement par watt dégradé sur les dernières années, "
                            "et risque de panne croissant. Le gain net doit être "
                            "recalculé avec la consommation réelle du parc vieillissant.",
            "condition": "Charges peu sensibles à la performance unitaire.",
            "fondement": "Amortissement du carbone incorporé sur une durée plus longue.",
            "difficulte": "faible",
            "note_gain": "Le carbone incorporé représente " + fr(part_inc, 0) + " % de "
                         "l'empreinte : à ce niveau, ce levier pèse plus que "
                         "tout gain de PUE réaliste.",
        })

    # -- Taux de charge : le gisement invisible ------------------------------
    taux = float(profil.get("taux_charge") or 0.65)
    if taux < CHARGE_CONSOLIDER:
        gain = e_it * 0.12
        ajoute("Consolider les charges pour remonter le taux d'utilisation",
               gain, gain * 0.8,
               "Réduit la marge de tolérance aux pics ; à border par une étude "
               "de capacité.",
               "Taux actuel de " + fr(taux * 100, 0) + " % : les auxiliaires sont "
               "dimensionnés pour une charge qui n'arrive jamais.",
               "Effet de la charge partielle sur le rendement des auxiliaires.",
               "moyenne")

    out.sort(key=lambda x: (x["gain_co2_t"], x["gain_eau_m3"]), reverse=True)
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  6. CONFORMITÉ ET AVERTISSEMENTS
# ═══════════════════════════════════════════════════════════════════════════

def _point_eed_art11(res):
    """L'article 11 de l'EED, jugé sur l'énergie que l'étude vient de calculer.

    TJ = MWh × 3,6 / 1000 — une conversion, pas un modèle. Les seuils
    s'apprécient au niveau de l'ENTREPRISE : un site au-dessus la met dedans
    à lui seul ; un site en dessous ne l'en sort pas, et le point le dit."""
    e_tot = res["energie"]["energie_totale_MWh"]["valeur"]
    tj = e_tot * 3.6 / 1000.0
    c = CADRE_UE["eed_audit_smen"]
    if tj >= c["seuil_smen_tj"]:
        statut = "assujetti — SMÉn ISO 50001"
        detail = ("Consommation calculée : %s MWh/an soit %s TJ/an — ce seul "
                  "site dépasse le seuil de %s TJ : système de management de "
                  "l'énergie CERTIFIÉ ISO 50001 exigé (échéance octobre 2027). "
                  "La revue énergétique, les IPÉ et la situation de référence "
                  "se posent dès la conception — après, la référence est "
                  "perdue." % (fr(e_tot, 0), fr(tj, 1), fr(c["seuil_smen_tj"])))
    elif tj >= c["seuil_audit_tj"]:
        statut = "assujetti — audit énergétique"
        detail = ("Consommation calculée : %s MWh/an soit %s TJ/an — au-dessus "
                  "du seuil de %s TJ : audit énergétique EN 16247-1 / "
                  "ISO 50002 (échéance octobre 2026, puis tous les quatre "
                  "ans). Une certification ISO 50001 en dispense — et le seuil "
                  "SMÉn de %s TJ s'apprécie sur l'ENTREPRISE entière, autres "
                  "activités comprises."
                  % (fr(e_tot, 0), fr(tj, 1), fr(c["seuil_audit_tj"]),
                     fr(c["seuil_smen_tj"])))
    else:
        statut = "sous les seuils — site seul"
        detail = ("Consommation calculée : %s MWh/an soit %s TJ/an, sous le "
                  "seuil d'audit de %s TJ. ATTENTION : les seuils s'apprécient "
                  "au niveau de l'entreprise, toutes activités confondues — ce "
                  "site s'ADDITIONNE au reste, il ne s'en isole pas."
                  % (fr(e_tot, 0), fr(tj, 1), fr(c["seuil_audit_tj"])))
    return {"sujet": "Audit énergétique et SMÉn (EED, art. 11)",
            "statut": statut, "detail": detail, "reference": c["titre"]}


def conformite(profil, res):
    """Confrontation aux seuils réglementaires et aux repères de marché."""
    p_it = float(profil.get("puissance_it_kw") or 0)
    pue = res["energie"]["pue"]["valeur"]
    wue = res["eau"]["wue_site"]["valeur"]
    pays = (profil.get("pays") or "UE").upper()
    froid = pays in ("SE", "NO", "FI", "DK", "IE")
    cible_pue = (CADRE_UE["cndcp"]["cibles"]["pue_climat_froid"] if froid
                 else CADRE_UE["cndcp"]["cibles"]["pue_climat_tempere_chaud"])
    cible_wue = CADRE_UE["cndcp"]["cibles"]["wue_site_max"]

    points = [
        {"sujet": "Reporting européen (directive efficacité énergétique, art. 12)",
         "statut": "assujetti" if p_it >= 500 else "hors seuil",
         "detail": ("Puissance informatique installée : " + fr(p_it, 0) + " kW. "
                    "Le seuil est de 500 kW.") +
                   (" Déclaration annuelle obligatoire ; l'instrumentation doit "
                    "être prévue dès la conception." if p_it >= 500 else
                    " Sous le seuil aujourd'hui — à revérifier à chaque extension."),
         "reference": CADRE_UE["eed_reporting"]["titre"]},
        _point_eed_art11(res),
        {"sujet": "PUE — repère de marché",
         "statut": "conforme" if pue <= cible_pue else "écart",
         "detail": ("PUE calculé " + fr(pue, 3) + " ; repère " + fr(cible_pue)
                    + (" (climat froid)." if froid else " (climat tempéré ou chaud).")),
         "reference": CADRE_UE["cndcp"]["titre"]},
        {"sujet": "WUE de site — repère de marché",
         "statut": "conforme" if wue <= cible_wue else "écart",
         "detail": "WUE de site calculé " + fr(wue, 3) + " L/kWh ; repère " + fr(cible_wue) + ".",
         "reference": CADRE_UE["cndcp"]["titre"]},
    ]
    return points


# ═══════════════════════════════════════════════════════════════════════════
#  LES ÉVALUATEURS — juger un chiffre ANNONCÉ, pas produire la donnée locale
# ═══════════════════════════════════════════════════════════════════════════
# Deux limites du moteur portent une réponse professionnelle : la simulation
# de site pour le PUE, l'étude horaire pour le carbone. Le moteur ne mènera
# jamais ces études — mais il peut faire le geste qui les PRÉCÈDE chez le BE
# fluides et l'énergéticien : juger si un chiffre annoncé est recevable, et
# dire quoi exiger avant de le contractualiser.
#
# LA RÈGLE : ces évaluateurs REJUGENT avec les mêmes fonctions que le calcul
# — plages de famille, pénalité de charge partielle, moyennes nationales.
# Aucune donnée nouvelle n'est inventée ; toute entrée invalide est REFUSÉE
# avec son motif, jamais corrigée en silence.

def evaluer_pue(pue_annonce, refroidissement=None, taux_charge=None):
    """Un PUE annoncé est-il recevable pour cette famille, À CE taux de charge ?

    Le geste du BE fluides devant une fiche produit ou un engagement de
    contrat : situer le chiffre dans la plage de conception de la famille,
    puis le confronter à la charge RÉELLE — l'erreur la plus courante des
    dossiers est un PUE promis à pleine charge pour un site qui tournera des
    années à 40 %.
    """
    try:
        pue = float(pue_annonce)
    except (TypeError, ValueError):
        return {"ok": False, "motif": "PUE illisible : un nombre est attendu."}
    if pue < 1.0:
        return {"ok": False,
                "motif": "Un PUE inférieur à 1 est physiquement impossible : "
                         "l'énergie totale du site CONTIENT celle de "
                         "l'informatique. Ce chiffre n'est pas un PUE — "
                         "demander ce qui a été mesuré, et sur quel périmètre."}
    fam = refroidissement or "eau_glacee"
    ref = REFROIDISSEMENT.get(fam)
    if not ref:
        return {"ok": False,
                "motif": "Famille de refroidissement inconnue : " + str(fam)
                         + ". Connues : " + ", ".join(sorted(REFROIDISSEMENT))}
    taux = float(taux_charge if taux_charge is not None else 0.65)
    if not (0.05 <= taux <= 1.0):
        return {"ok": False,
                "motif": "Taux de charge hors bornes (5 % à 100 %)."}

    bas, haut = ref["pue_partiel"]
    pen = penalite_charge(taux)
    att_bas, att_haut = bas + pen, haut + pen

    if pue < bas:
        verdict, lecture = "sous_plage", (
            "SOUS la plage de conception de la famille (%s – %s à pleine "
            "charge) : physiquement suspect pour cette technologie. Ce chiffre "
            "sort d'un climat exceptionnel, d'un périmètre partiel, ou d'une "
            "plaquette." % (fr(bas), fr(haut)))
    elif pue < att_bas:
        verdict, lecture = "plausible_pleine_charge", (
            "Plausible à PLEINE charge — mais à %s de charge, la même "
            "conception rend %s – %s : les auxiliaires ne suivent pas "
            "proportionnellement. Un engagement pris sur ce chiffre sera "
            "dépassé dès la première année d'exploitation." %
            (fr(taux), fr(att_bas), fr(att_haut)))
    elif pue <= att_haut:
        verdict, lecture = "coherent", (
            "Cohérent avec la plage de conception de la famille À CE taux de "
            "charge (%s – %s). Reste à vérifier ce que le chiffre PROMET : "
            "méthode, périmètre, année météo." % (fr(att_bas), fr(att_haut)))
    else:
        verdict, lecture = "au_dessus", (
            "AU-DESSUS de la plage attendue (%s – %s) : marge prudente, "
            "conception datée, ou contraintes de site réelles. En appel "
            "d'offres, demander la décomposition poste par poste — c'est "
            "parfois le chiffre le plus honnête de la consultation." %
            (fr(att_bas), fr(att_haut)))

    return {
        "ok": True, "verdict": verdict, "lecture": lecture,
        "pue_annonce": pue,
        "famille": ref["nom"],
        "plage_pleine_charge": [bas, haut],
        "taux_charge": taux,
        "penalite_charge": round(pen, 3),
        "plage_attendue": [round(att_bas, 3), round(att_haut, 3)],
        "exigences": [
            "La méthode de mesure : ISO/IEC 30134-2 — catégorie, périmètre, "
            "année complète. Un PUE sans sa catégorie ne se compare à rien.",
            "À QUEL taux de charge le chiffre est promis, et sur quelle année "
            "météo (fichier TMY).",
            "Si le refroidissement est évaporatif : les heures de free-cooling "
            "comptées sur la température HUMIDE, pas la sèche.",
            "Des pénalités assises sur la MESURE en exploitation, pas sur la "
            "note de conception.",
            "Le suivi dans un SMÉn ISO 50001 : le PUE promis devient un IPÉ "
            "(art. 6.4) avec sa situation énergétique de référence (art. 6.5) "
            "posée AVANT la mise en service — sans SER, la dérive ne se "
            "prouvera jamais.",
        ],
        "nature": "calcule",
        "exige_de": "du BE fluides",
        "source": "plages de conception du référentiel + pénalité de charge "
                  "partielle — le MÊME calcul que l'étude, pas un second "
                  "barème",
    }


def evaluer_intensite(facteur_g, pays=None, heures_basses_g=None,
                      part_differable_pct=None, energie_mwh_an=None):
    """Un facteur d'émission annoncé est-il recevable pour ce réseau ?

    Le geste de l'énergéticien : situer le facteur face à la moyenne
    location-based du pays, nommer ce qu'un écart signifie (market-based,
    périmètre), et BORNER le gain d'un pilotage horaire quand le client
    apporte ses propres données — jamais l'inverse.
    """
    try:
        f = float(facteur_g)
    except (TypeError, ValueError):
        return {"ok": False, "motif": "Facteur illisible : g/kWh attendu."}
    if f < 0:
        return {"ok": False, "motif": "Un facteur négatif n'existe pas en "
                                      "comptabilité carbone de réseau."}
    p = (pays or "FR").upper()
    moyenne = INTENSITE_RESEAU.get(p)
    if moyenne is None:
        return {"ok": False,
                "motif": "Pays inconnu du référentiel : " + p + ". Connus : "
                         + ", ".join(sorted(INTENSITE_RESEAU))}

    if f < 0.5 * moyenne:
        verdict, lecture = "market_based_probable", (
            ("Très en dessous de la moyenne location-based du réseau (%s "
             "g/kWh, millésime %s) : c'est presque sûrement un facteur "
             "CONTRACTUEL (market-based, GHG Protocol Scope 2). Légitime — "
             "mais le réseau physique, lui, reste à %s g : exiger le DOUBLE "
             "reporting, et vérifier si les garanties d'origine sont "
             "annuelles ou horaires. Une garantie annuelle couvre aussi les "
             "heures où le réseau est au charbon.")
            % (fr(moyenne), INTENSITE_MILLESIME, fr(moyenne)))
    elif f <= 1.5 * moyenne:
        verdict, lecture = "coherent_location", (
            ("Cohérent avec la moyenne location-based du pays (%s g/kWh, "
             "millésime %s — celui du référentiel). Préciser l'année de "
             "référence du VÔTRE : les mixes bougent, et un facteur sans "
             "millésime ne se défend pas.") % (fr(moyenne), INTENSITE_MILLESIME))
    else:
        verdict, lecture = "au_dessus", (
            "Supérieur à la moyenne nationale (%s g/kWh) : mix local "
            "particulier, ou périmètre qui inclut les groupes de secours "
            "(scope 1) dans un chiffre présenté comme du scope 2. Demander le "
            "périmètre exact." % fr(moyenne))

    res = {
        "ok": True, "verdict": verdict, "lecture": lecture,
        "facteur_annonce_g": f, "pays": p,
        "moyenne_location_g": moyenne,
        "exigences": [
            "L'année de référence et le périmètre du facteur (scope 2 seul ?).",
            "Le double reporting Scope 2 : market-based ET location-based "
            "(GHG Protocol).",
            "La granularité des garanties d'origine : annuelle ou horaire.",
            "Le profil horaire du réseau : éCO2mix (RTE) ou ENTSO-E, pour "
            "l'étude de pilotage.",
        ],
        "nature": "calcule",
        "exige_de": "de l'énergéticien",
        "source": "moyennes nationales du référentiel — les mêmes que l'étude",
    }

    # LE GAIN D'UN PILOTAGE HORAIRE, BORNÉ — et seulement si le client apporte
    # SES données. g/kWh et t/GWh sont la même unité : l'écart moyenne-creux
    # se lit directement en tonnes par GWh déplacé.
    if heures_basses_g is not None and str(heures_basses_g).strip() != "":
        try:
            hb = float(heures_basses_g)
        except (TypeError, ValueError):
            return {"ok": False, "motif": "Facteur des heures basses illisible."}
        ecart = max(0.0, moyenne - hb)
        borne = {
            "ecart_g_kwh": round(ecart, 1),
            "tonnes_par_gwh_deplace": round(ecart, 1),
            "lecture": ("Chaque GWh déplacé vers les heures basses économise "
                        "AU PLUS %s tCO2e — au plus, parce que la moyenne des "
                        "heures restantes remonte à mesure qu'on déplace."
                        % fr(round(ecart, 1)))
            if ecart > 0 else
            ("Aucun gain : le facteur d'heures basses fourni n'est pas "
             "inférieur à la moyenne du réseau."),
        }
        if energie_mwh_an and part_differable_pct:
            try:
                e = float(energie_mwh_an)
                part = float(part_differable_pct) / 100.0
            except (TypeError, ValueError):
                return {"ok": False, "motif": "Énergie ou part différable illisible."}
            if 0 < part <= 1 and e > 0:
                borne["tonnes_an_max"] = round(e * 1000.0 * part * ecart / 1e6, 1)
                borne["hypotheses"] = ("%s MWh/an, %s %% différables — vos "
                                       "valeurs, pas les nôtres"
                                       % (fr(e), fr(part * 100)))
        res["pilotage"] = borne
    return res


def evaluer_eau(profil, volume_annuel_m3, pointe_jour_m3=None):
    """Un volume d'eau ANNUEL annoncé est-il recevable pour ce profil ?

    Le geste du BE fluides avant l'étude de profil mensuel : recalculer
    l'appoint avec le MÊME moteur que l'étude — plancher physique
    d'évaporation compris — et situer le chiffre annoncé. Puis, si le dossier
    annonce aussi son jour de pointe, éprouver son arithmétique : c'est la
    POINTE que jugent l'autorisation de prélèvement et l'étiage, jamais la
    moyenne — et c'est exactement ce que ce moteur, sans climat local, ne
    peut PAS établir. Il peut en revanche dire quand le chiffre posé sur la
    table est impossible.
    """
    p = dict(profil or {})
    if not p.get("puissance_it_kw"):
        return {"ok": False,
                "motif": "La référence se calcule avec VOTRE profil : "
                         "renseignez au moins la puissance informatique "
                         "installée (étape 2). Sans elle, juger un volume "
                         "d'eau reviendrait à comparer à un site imaginaire."}
    try:
        vol = float(volume_annuel_m3)
    except (TypeError, ValueError):
        return {"ok": False, "motif": "Volume annuel illisible : m³/an attendus."}
    if vol < 0:
        return {"ok": False, "motif": "Un volume d'eau négatif n'existe pas."}

    res_e = energie(p)
    w = eau(p, res_e)
    appoint = w["appoint_m3"]["valeur"]
    evap = w["evaporation_m3"]["valeur"]
    fam = REFROIDISSEMENT.get(p.get("refroidissement") or "eau_glacee",
                              REFROIDISSEMENT["eau_glacee"])
    plancher = evap * PART_LATENTE_MIN
    plafond = appoint * (1.0 + INCERTITUDE_APPOINT)

    if appoint == 0:
        # Famille à rejet sec : le calcul ne prévoit AUCUN appoint.
        if vol == 0:
            verdict, lecture = "coherent_etude", (
                "Cohérent : cette famille rejette sa chaleur à sec, le calcul "
                "ne prévoit aucun appoint de refroidissement. Reste l'eau que "
                "le calcul ne porte pas : humidification, lavage, réseau "
                "incendie — à lister, pas à deviner.")
        else:
            verdict, lecture = "au_dessus_etude", (
                "Le calcul ne prévoit AUCUN appoint pour cette famille (rejet "
                "sec) : les %s m³ annoncés couvrent d'autres usages — "
                "humidification, lavage adiabatique, appoints process. "
                "Demander la décomposition poste par poste." % fr(vol))
    elif vol < plancher:
        verdict, lecture = "sous_borne_physique", (
            "SOUS le plancher physique (%s m³/an = évaporation tout-latent "
            "%s m³ × part latente annuelle minimale %s) : même une tour qui "
            "rejette le maximum de sensible évapore davantage pour cette "
            "chaleur. Soit la part évaporative réelle est plus faible que "
            "celle du profil — une AUTRE conception —, soit le chiffre exclut "
            "la purge, soit c'est une plaquette. Demander le périmètre "
            "exact : évaporation, purge, appoints."
            % (fr(round(plancher, 1)), fr(evap), fr(PART_LATENTE_MIN)))
    elif vol <= plafond:
        verdict, lecture = "coherent_etude", (
            "Cohérent avec l'appoint que l'étude calcule pour VOTRE profil "
            "(%s m³/an, ±%s %%). L'annuel est recevable — c'est la POINTE "
            "qu'il reste à établir : profil mensuel sur météo locale, "
            "confronté à l'autorisation de prélèvement et à l'étiage."
            % (fr(appoint), fr(INCERTITUDE_APPOINT * 100)))
    else:
        verdict, lecture = "au_dessus_etude", (
            "AU-DESSUS de l'appoint calculé (%s m³/an, ±%s %%) : marge "
            "prudente, cycles de concentration plus bas que déclarés, ou "
            "usages hors refroidissement agrégés dans le même compteur. "
            "Demander la décomposition — et des compteurs séparés en "
            "exploitation." % (fr(appoint), fr(INCERTITUDE_APPOINT * 100)))

    res = {
        "ok": True, "verdict": verdict, "lecture": lecture,
        "volume_annonce_m3": vol,
        "famille": fam["nom"],
        "reference": {
            "appoint_m3": round(appoint, 1),
            "evaporation_m3": round(evap, 1),
            "plancher_m3": round(plancher, 1),
            "part_latente_min": PART_LATENTE_MIN,
            "part_evaporative": w["part_evaporative"],
            "incertitude_pct": INCERTITUDE_APPOINT * 100,
        },
        "exigences": [
            "Le périmètre du volume : évaporation, purge, humidification, "
            "process — poste par poste, pas un total nu.",
            "Le profil MENSUEL de consommation sur météo locale (le moteur "
            "travaille en annuel : c'est sa limite déclarée), confronté à "
            "l'autorisation de prélèvement et à l'étiage — agence de l'eau, "
            "arrêtés sécheresse (ISO 14046, ISO 46001).",
            "Le WUE de site promis en catégorie ISO/IEC 30134-9, et le WUE de "
            "SOURCE en regard : l'arbitrage sec/évaporatif est un compromis "
            "eau/énergie — la pensée cycle de vie de l'IEC 62430, pas une "
            "course au WUE de site nul.",
            "Le stockage tampon dimensionné en PRO pour tenir un arrêté "
            "sécheresse sans délester, et des compteurs séparés par usage.",
        ],
        "nature": "calcule",
        "exige_de": "du BE fluides",
        "source": "le MÊME calcul d'appoint que l'étude — plancher physique "
                  "d'évaporation compris — pas un second barème",
    }

    # LE JOUR DE POINTE, si le dossier l'annonce. Le moteur ne connaît pas le
    # climat local : il ne juge QUE l'arithmétique — le maximum d'une série ne
    # peut pas être sous sa moyenne — et nomme qui doit établir le reste.
    if pointe_jour_m3 is not None and str(pointe_jour_m3).strip() != "":
        try:
            pointe = float(pointe_jour_m3)
        except (TypeError, ValueError):
            return {"ok": False, "motif": "Pointe journalière illisible : m³/jour attendus."}
        moy_jour = vol / 365.0
        if pointe < moy_jour:
            bloc = {"recevable": False, "facteur": round(pointe / moy_jour, 2) if moy_jour else 0,
                    "jour_moyen_m3": round(moy_jour, 2),
                    "lecture": ("Arithmétiquement impossible : le jour de pointe "
                                "(%s m³) est SOUS le jour moyen (%s m³ = annuel/365). "
                                "Le maximum d'une série ne peut pas être sous sa "
                                "moyenne — l'un des deux chiffres du dossier est faux."
                                % (fr(pointe), fr(moy_jour)))}
        elif moy_jour and pointe == moy_jour and w["part_evaporative"] > 0:
            bloc = {"recevable": False, "facteur": 1.0,
                    "jour_moyen_m3": round(moy_jour, 2),
                    "lecture": ("Un facteur de pointe de 1,0 suppose 365 jours "
                                "IDENTIQUES : incompatible avec un refroidissement "
                                "évaporatif, dont la consommation suit la chaleur "
                                "et le climat. Ce dossier prétend ne pas voir l'été.")}
        else:
            fac = pointe / moy_jour if moy_jour else 0.0
            bloc = {"recevable": True, "facteur": round(fac, 2),
                    "jour_moyen_m3": round(moy_jour, 2),
                    "lecture": ("Le dossier suppose un facteur de pointe de %s "
                                "(jour moyen %s m³). L'arithmétique tient ; la "
                                "VALEUR, elle, ne peut venir que du profil mensuel "
                                "sur météo locale — c'est ce facteur que "
                                "l'autorisation de prélèvement doit couvrir, pas "
                                "la moyenne." % (fr(fac), fr(moy_jour)))}
        res["pointe"] = bloc
    return res


def evaluer_incorpore(poste, valeur_kg, duree_vie_ans=None):
    """Un carbone incorporé annoncé est-il recevable pour ce poste ?

    Le geste de l'AMO carbone devant une déclaration fournisseur : situer le
    chiffre dans l'ordre de grandeur sectoriel du référentiel — le MÊME que
    l'étude, avec la MÊME incertitude — puis exiger ce qui permet de conclure :
    la déclaration de type III vérifiée (ISO 14025), ses modules (EN 15804+A2
    pour la construction), son unité fonctionnelle (ISO 14040/14044). L'ordre
    de grandeur ne départage JAMAIS deux offres ; la déclaration, oui — et
    l'écoconception (IEC 62430, art. 5.6) fait de son obtention une exigence,
    pas une faveur.
    """
    ref = INCORPORE.get(str(poste or ""))
    if not ref:
        return {"ok": False,
                "motif": "Poste inconnu du référentiel : " + str(poste)
                         + ". Connus : " + ", ".join(sorted(INCORPORE))}
    try:
        val = float(valeur_kg)
    except (TypeError, ValueError):
        return {"ok": False, "motif": "Valeur illisible : kgCO2e attendus."}
    if val <= 0:
        return {"ok": False,
                "motif": "Un incorporé nul ou négatif ne se constate que par "
                         "crédit biogénique ou module D agrégé au reste. "
                         "EN 15804+A2 les déclare SÉPARÉMENT : demander les "
                         "modules A1-A3 seuls — le stockage biogénique se "
                         "déclare à part, il ne s'efface pas du dossier."}

    bas = ref["valeur"] * (1.0 - INCERTITUDE_INCORPORE)
    haut = ref["valeur"] * (1.0 + INCERTITUDE_INCORPORE)
    if val < bas:
        verdict, lecture = "sous_plage_sectorielle", (
            "SOUS l'ordre de grandeur sectoriel (%s kgCO2e, ±%s %%) : possible "
            "— c'est tout l'intérêt d'une écoconception réelle — mais cela ne "
            "se PLAIDE pas, cela se déclare : ISO 14025 type III vérifiée par "
            "tierce partie, modules et unité fonctionnelle comparables. Sans "
            "la déclaration, ce chiffre est un argument commercial."
            % (fr(ref["valeur"]), fr(INCERTITUDE_INCORPORE * 100)))
    elif val <= haut:
        verdict, lecture = "coherent_secteur", (
            "Dans l'ordre de grandeur sectoriel (%s kgCO2e, ±%s %%) — et c'est "
            "PRÉCISÉMENT pourquoi la déclaration produit reste exigée : à "
            "±%s %%, l'ordre de grandeur ne départage pas deux offres. La "
            "substitution se fait déclaration par déclaration, et le "
            "classement des leviers se recalcule après chacune."
            % (fr(ref["valeur"]), fr(INCERTITUDE_INCORPORE * 100),
               fr(INCERTITUDE_INCORPORE * 100)))
    else:
        verdict, lecture = "au_dessus_secteur", (
            "AU-DESSUS de l'ordre sectoriel (%s kgCO2e, ±%s %%) : configuration "
            "lourde, périmètre plus large (transport A4, mise en œuvre A5), ou "
            "déclaration honnête là où les autres offres citent une plaquette. "
            "Demander les modules pour comparer à périmètre ÉGAL avant "
            "d'écarter l'offre — c'est parfois la meilleure."
            % (fr(ref["valeur"]), fr(INCERTITUDE_INCORPORE * 100)))

    res = {
        "ok": True, "verdict": verdict, "lecture": lecture,
        "valeur_annonce_kg": val,
        "reference": {"valeur_kg": ref["valeur"],
                      "duree_vie_ans": ref["duree_vie_ans"],
                      "incertitude_pct": INCERTITUDE_INCORPORE * 100,
                      "note": ref["note"]},
        "exigences": [
            "La déclaration environnementale de type III (ISO 14025), vérifiée "
            "par tierce partie, programme et vérificateur nommés — FDES base "
            "INIES pour la construction, EPD pour les équipements.",
            "Les modules déclarés (EN 15804+A2) : A1-A3 au minimum, et le "
            "périmètre EXACT de tout chiffre comparé — jamais un total sans "
            "ses modules.",
            "L'unité fonctionnelle et les frontières du système (ISO "
            "14040/14044) — pour un serveur : configuration mémoire et "
            "stockage, sans quoi l'écart du simple au triple est normal.",
            "L'exigence portée AUX MARCHÉS dès l'ACT : l'échange d'informations "
            "dans la chaîne de valeur est une exigence d'écoconception "
            "(IEC 62430, art. 5.6) — si le fournisseur ne déclare pas, "
            "l'acheteur doit obtenir l'information autrement, pas y renoncer.",
            "La démarche outillée côté projet : revues d'écoconception aux "
            "jalons (IEC 62430, art. 5.5 ; ISO 14006 pour l'ancrage au "
            "système de management ; NF X30-264 et ISO/TR 14062 pour la "
            "méthode), et recalcul du classement des leviers après chaque "
            "substitution.",
        ],
        "nature": "calcule",
        "exige_de": "de l'AMO carbone",
        "source": "ordres de grandeur sectoriels du référentiel — les MÊMES "
                  "que l'étude, avec la même incertitude",
    }
    if duree_vie_ans is not None and str(duree_vie_ans).strip() != "":
        try:
            dv = float(duree_vie_ans)
        except (TypeError, ValueError):
            return {"ok": False, "motif": "Durée de vie illisible : années attendues."}
        if dv <= 0 or dv > 60:
            return {"ok": False, "motif": "Durée de vie hors du plausible (0 à 60 ans)."}
        res["amorti"] = {
            "annonce_kg_an": round(val / dv, 1),
            "reference_kg_an": round(ref["valeur"] / ref["duree_vie_ans"], 1),
            "duree_vie_annonce_ans": dv,
            "duree_vie_reference_ans": ref["duree_vie_ans"],
            "lecture": ("Amorti sur %s ans : %s kgCO2e/an, contre %s kgCO2e/an "
                        "pour le référentiel (%s ans). Allonger la durée de vie "
                        "RÉELLE est le premier levier dès que l'incorporé domine "
                        "l'empreinte — et il se prouve en exploitation, pas en "
                        "plaquette." % (fr(dv), fr(round(val / dv, 1)),
                                        fr(round(ref["valeur"] / ref["duree_vie_ans"], 1)),
                                        fr(ref["duree_vie_ans"]))),
        }
    return res


def avertissements(profil, res):
    """Ce que le calcul NE dit pas. Volontairement placé dans le résultat.

    Un moteur qui ne déclare pas ses limites les fait porter par son lecteur,
    qui ne les connaît pas. En réponse à appel d'offres, l'omission se retourne
    au moment de la vérification.
    """
    av = []
    if profil.get("intensite_reseau_g") is None:
        av.append("L'intensité carbone employée est une MOYENNE ANNUELLE de mix "
                  "national. Elle ne permet pas d'arbitrer un pilotage horaire "
                  "des charges : pour cela il faut un profil horaire, où l'écart "
                  "entre heures creuses et heures de pointe dépasse souvent un "
                  "facteur trois.")
    if not profil.get("pue_cible"):
        av.append("Le PUE est ESTIMÉ à partir de la famille de refroidissement et "
                  "du taux de charge. Il ne remplace pas une simulation "
                  "thermo-aéraulique du site, seule capable de tenir compte du "
                  "climat local heure par heure.")
    av.append("Les facteurs de carbone incorporé sont des ordres de grandeur "
              "sectoriels (±50 %). Dès que les équipements sont choisis, les "
              "remplacer par leurs déclarations environnementales produit : "
              "l'écart peut atteindre un facteur deux et changer le classement "
              "des leviers.")
    if res["eau"]["part_evaporative"] > 0:
        av.append("La consommation d'eau est annualisée. Or elle se concentre "
                  "sur les heures chaudes — c'est-à-dire au moment où la "
                  "ressource est la plus tendue. Un WUE annuel conforme peut "
                  "masquer un prélèvement estival inacceptable localement : "
                  "vérifier la disponibilité au pas mensuel.")
    av.append("Aucun modèle de langage n'intervient dans ces calculs. Les "
              "commentaires rédigés ailleurs dans le dossier peuvent l'être ; "
              "les chiffres de cette note, non.")
    return av


# ═══════════════════════════════════════════════════════════════════════════
#  API PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════

def etude(profil):
    """L'étude complète d'un profil. Point d'entrée unique."""
    profil = dict(profil or {})
    res = {}
    res["energie"] = energie(profil)
    res["eau"] = eau(profil, res["energie"])
    res["carbone"] = carbone(profil, res["energie"])
    res["chaleur"] = chaleur(profil, res["energie"])
    res["leviers"] = leviers(profil, res)
    res["conformite"] = conformite(profil, res)
    res["avertissements"] = avertissements(profil, res)
    res["version"] = VERSION
    res["profil"] = profil
    return res


# ═══════════════════════════════════════════════════════════════════════════
# LES SOURCES CONSULTABLES — où aller vérifier soi-même, avec le lien
# ═══════════════════════════════════════════════════════════════════════════
# Le référentiel cite ses sources en toutes lettres, mais aucune n'était
# CLIQUABLE : le lecteur qui voulait vérifier retapait un nom d'organisme dans
# un moteur de recherche. Chaque entrée porte ici le lien officiel.
#
# LA RÈGLE DES LIENS : la RACINE du site officiel, jamais un lien profond. Un
# chemin vers une page précise pourrit en quelques mois — les sites de normes
# réorganisent sans redirection — et un lien mort au milieu d'un référentiel
# discrédite tout ce qui l'entoure. La racine, elle, est stable depuis des
# décennies. Le champ `verifier` dit quoi chercher une fois sur place : c'est
# lui qui remplace le lien profond, sans en partager la fragilité.
# Cette règle est VÉRIFIÉE à l'import : une entrée avec un chemin est refusée.
SOURCES_CONSULTABLES = [
    {"cle": "ashrae", "organisme": "ASHRAE",
     "nature": "norme professionnelle",
     "porte": "Les plages thermiques d'admission des équipements (TC 9.9) — "
              "celles que ce moteur emploie pour les classes A1 à A4.",
     "lien": "https://www.ashrae.org",
     "verifier": "Thermal Guidelines for Data Processing Environments, "
                 "édition en vigueur, avant d'engager une garantie sur un "
                 "élargissement de plage."},
    {"cle": "iso", "organisme": "ISO",
     "nature": "norme internationale",
     "porte": "La série ISO/IEC 30134 : définitions normalisées du PUE, du "
              "WUE, de l'ERF — ce qui rend ces indicateurs opposables dans "
              "un contrat.",
     "lien": "https://www.iso.org",
     "verifier": "ISO/IEC 30134, la partie correspondant à l'indicateur que "
                 "vous contractualisez (30134-2 pour le PUE)."},
    {"cle": "cenelec", "organisme": "CEN/CENELEC",
     "nature": "norme européenne",
     "porte": "La série EN 50600 — conception, exploitation et indicateurs "
              "des centres de données ; référence des certifications "
              "européennes de site.",
     "lien": "https://www.cencenelec.eu",
     "verifier": "EN 50600, la partie visée par votre certificateur ; les "
                 "granularités de disponibilité y sont définies."},
    {"cle": "green_grid", "organisme": "The Green Grid",
     "nature": "consortium professionnel",
     "porte": "L'origine du PUE et du WUE : les documents fondateurs qui "
              "fixent ce que ces ratios comptent — et ce qu'ils ne comptent "
              "pas.",
     "lien": "https://www.thegreengrid.org",
     "verifier": "Les livres blancs PUE et WUE ; la définition des "
                 "périmètres de mesure (catégories 1 à 3)."},
    {"cle": "uptime", "organisme": "Uptime Institute",
     "nature": "institut privé",
     "porte": "L'enquête annuelle mondiale — PUE moyens constatés, causes "
              "d'incidents — et la classification Tier.",
     "lien": "https://uptimeinstitute.com",
     "verifier": "Le Global Data Center Survey de l'année : c'est une enquête "
                 "DÉCLARATIVE auprès d'exploitants, pas une mesure — la "
                 "citer comme telle."},
    {"cle": "dg_ener", "organisme": "Commission européenne — DG Énergie",
     "nature": "réglementation",
     "porte": "La directive efficacité énergétique (EED refonte) : "
              "l'obligation de déclaration des centres de données au-dessus "
              "de 500 kW, et le schéma européen de notation en préparation.",
     "lien": "https://energy.ec.europa.eu",
     "verifier": "Le règlement délégué 2024/1364 sur la déclaration des "
                 "centres de données, et son portail de dépôt."},
    {"cle": "cndcp", "organisme": "Climate Neutral Data Centre Pact",
     "nature": "engagement sectoriel",
     "porte": "Les cibles d'auto-régulation du secteur européen — PUE, part "
              "renouvelable, eau, économie circulaire — reprises par ce "
              "moteur comme repères.",
     "lien": "https://www.climateneutraldatacentre.net",
     "verifier": "Les cibles par échéance et la liste des signataires : un "
                 "engagement volontaire n'engage que ceux qui y figurent."},
    {"cle": "iea", "organisme": "Agence internationale de l'énergie (IEA)",
     "nature": "organisation internationale",
     "porte": "Les analyses de référence sur la consommation électrique des "
              "centres de données et son évolution — l'échelle macro qui "
              "manque aux fiches produit.",
     "lien": "https://www.iea.org",
     "verifier": "Le rapport Energy and AI et les données Data Centres and "
                 "Data Transmission Networks."},
    {"cle": "ademe", "organisme": "ADEME",
     "nature": "agence publique française",
     "porte": "Les facteurs d'émission réglementaires français — dont "
              "l'intensité carbone à employer pour un bilan opposable en "
              "France.",
     "lien": "https://www.ademe.fr",
     "verifier": "La Base Empreinte pour les facteurs d'émission, et les "
                 "avis techniques sur le refroidissement."},
    {"cle": "rte", "organisme": "RTE",
     "nature": "gestionnaire de réseau",
     "porte": "L'intensité carbone du réseau français heure par heure, et "
              "les conditions de raccordement — le poste dont le DÉLAI "
              "décide souvent du calendrier du projet.",
     "lien": "https://www.rte-france.com",
     "verifier": "éCO2mix pour l'intensité horaire constatée ; la file "
                 "d'attente de raccordement de votre région."},
    {"cle": "afnor", "organisme": "AFNOR",
     "nature": "organisme de normalisation",
     "porte": "Les normes d'écoconception qui outillent l'AMO carbone : "
              "NF EN IEC 62430 (principes et exigences), NF EN ISO 14006 "
              "(écoconception dans le système de management), NF X30-264 "
              "(démarche), ISO/TR 14062 (intégration en conception) — et "
              "les NF EN 15804+A2 des FDES.",
     "lien": "https://www.afnor.org",
     "verifier": "l'édition EN VIGUEUR de chaque norme avant de la citer "
                 "dans un marché — une norme se remplace, un contrat reste."},
    {"cle": "ember", "organisme": "Ember",
     "nature": "données ouvertes",
     "porte": "Les intensités carbone annuelles des mix électriques, "
              "millésimées et téléchargeables — la provenance des moyennes "
              "nationales de ce moteur, et le premier endroit où vérifier "
              "qu'elles n'ont pas vieilli.",
     "lien": "https://ember-energy.org",
     "verifier": "l'intensité de VOTRE pays pour l'année de référence de "
                 "l'offre — et remplacer la moyenne du moteur si elle date."},
    {"cle": "boavizta", "organisme": "Boavizta",
     "nature": "association — méthodologie et données ouvertes",
     "porte": "L'empreinte environnementale des équipements numériques : "
              "méthode et données ouvertes pour le carbone incorporé des "
              "serveurs — le gisement de substitution des ordres de grandeur "
              "de ce moteur, en attendant les PCF constructeur.",
     "lien": "https://boavizta.org",
     "verifier": "la fiche du serveur retenu (configuration mémoire et "
                 "stockage comprise) et la version de la méthode employée."},
    {"cle": "inies", "organisme": "INIES (Alliance HQE-GBC)",
     "nature": "base de données publique",
     "porte": "Les déclarations environnementales des produits de "
              "construction pour la France : FDES (EN 15804+A2, ISO 14025) "
              "vérifiées par tierce partie — le gisement où la substitution "
              "des ordres de grandeur du carbone incorporé se fait, "
              "déclaration par déclaration.",
     "lien": "https://www.inies.fr",
     "verifier": "la FDES du produit RETENU (pas une FDES générique du même "
                 "type), sa date de validité et ses modules déclarés."},
]


def _verifier_sources():
    fautes = []
    cles = [x["cle"] for x in SOURCES_CONSULTABLES]
    if len(SOURCES_CONSULTABLES) < 8:
        fautes.append("moins de huit sources consultables")
    if len(set(cles)) != len(cles):
        fautes.append("clé de source dupliquée")
    liens = [x["lien"] for x in SOURCES_CONSULTABLES]
    if len(set(liens)) != len(liens):
        fautes.append("lien dupliqué")
    for x in SOURCES_CONSULTABLES:
        for champ in ("organisme", "nature", "porte", "lien", "verifier"):
            if not str(x.get(champ) or "").strip():
                fautes.append("source %s : champ %s vide" % (x["cle"], champ))
        lien = x["lien"]
        if not lien.startswith("https://"):
            fautes.append("source %s : lien non https" % x["cle"])
        # LA RÈGLE ANTI-POURRISSEMENT : racine du site, rien après le domaine.
        reste = lien[len("https://"):]
        if "/" in reste.rstrip("/"):
            fautes.append("source %s : lien profond refusé (%s)" % (x["cle"], lien))
    return fautes


_F_SOURCES = _verifier_sources()
if _F_SOURCES:
    raise AssertionError("SOURCES_CONSULTABLES : " + " | ".join(_F_SOURCES))


# ═══════════════════════════════════════════════════════════════════════════
# LES LIMITES DU MOTEUR — et, pour chacune, COMMENT Y RÉPONDRE
# ═══════════════════════════════════════════════════════════════════════════
# La page listait quatre limites en points secs : le lecteur repartait avec
# quatre trous et rien pour les combler. Analyse faite, DEUX de ces limites
# sont déjà levables ICI — le moteur accepte la donnée réelle (`pue_cible`,
# `intensite_reseau_g`) et `avertissements()` retire alors la réserve du
# résultat — et les deux autres relèvent d'études que ce moteur ne fera
# jamais honnêtement à distance.
#
# ON N'EFFACE AUCUNE LIMITE VRAIE : une étude qui ne dit que ses forces est
# une plaquette, et c'est le guide même de cette section. Ce qui change :
# chaque limite porte désormais SA RÉPONSE — la norme qui l'encadre, le calcul
# à commander, qui le mène, à quelle phase — et, quand une saisie la lève dans
# ce moteur, le champ exact qui la lève.
LIMITES = [
    {"cle": "pue_climat",
     "quoi": "Le PUE est estimé par famille de refroidissement et taux de "
             "charge, pas par le climat local heure par heure.",
     "moteur_fait": "Un PUE par famille avec sa courbe de charge partielle — "
                    "l'ordre de grandeur d'avant-projet.",
     "leve_par": "pue_cible",
     "leve_note": "Renseignez le PUE issu de votre simulation dans le champ "
                  "PUE cible : le moteur l'emploie tel quel et la réserve "
                  "disparaît du résultat.",
     "normes": ["ISO/IEC 30134-2 (PUE)", "EN 50600-4-2",
                "ASHRAE Thermal Guidelines (plages d'admission)",
                "ISO 50001 (SMÉn — IPÉ et situation de référence)"],
     "calcul": "Simulation thermique dynamique du site sur une année météo "
               "type (fichier TMY), au pas horaire ; compter les heures de "
               "free-cooling sur la température HUMIDE — pas la sèche — dès "
               "que le refroidissement est évaporatif.",
     "qui": "BE fluides / CVC",
     "quand": "APD au plus tard — avant qu'une garantie de PUE entre au "
              "contrat."},
    {"cle": "eau_pointe",
     "quoi": "L'eau est annualisée, alors que la consommation se concentre "
             "sur les heures chaudes — quand la ressource est tendue.",
     "moteur_fait": "La consommation annuelle par famille, la part "
                    "évaporative, et la confrontation aux repères publiés.",
     "leve_par": None,
     "leve_note": "Aucune saisie ne la lève ici : la pointe dépend du site, "
                  "de son autorisation de prélèvement et de l'étiage local.",
     "normes": ["ISO/IEC 30134-9 (WUE)", "ISO 14046 (empreinte eau)",
                "ISO 46001 (management de l'efficacité hydrique)",
                "NF EN IEC 62430 (écoconception — compromis eau/énergie)",
                "code de l'environnement — autorisation de prélèvement"],
     "calcul": "Profil mensuel de consommation à partir des données météo "
               "locales ; le confronter au débit autorisé et à l'étiage "
               "(agence de l'eau, BRGM) ; dimensionner le stockage tampon "
               "pour tenir les arrêtés sécheresse sans délester.",
     "qui": "BE fluides et exploitant, avec l'agence de l'eau",
     "quand": "Faisabilité pour l'autorisation ; PRO pour le stockage."},
    {"cle": "carbone_incorpore",
     "quoi": "Les facteurs de carbone incorporé sont des ordres de grandeur "
             "sectoriels à ±50 %.",
     "moteur_fait": "Des facteurs sectoriels amortis sur la durée de vie, "
                    "comparables poste à poste avec l'exploitation.",
     "leve_par": None,
     "leve_note": "Pas d'entrée par équipement ici : la substitution se fait "
                  "dans l'étude, déclaration par déclaration, dès que les "
                  "produits sont choisis.",
     "normes": ["EN 15804+A2 (EPD / FDES, base INIES)",
                "ISO 14025 (déclarations de type III)",
                "ISO 14040/14044 (ACV)",
                "ITU-T L.1410 (équipements TIC)",
                "NF EN IEC 62430 (exigences d'écoconception)",
                "ISO 14006 · NF X30-264 · ISO/TR 14062 (démarche)"],
     "calcul": "Substituer chaque facteur sectoriel par la déclaration "
               "environnementale du produit retenu (modules A1-A3 et suivants "
               "pertinents), amortie sur SA durée de vie ; recalculer le "
               "classement des leviers — l'écart peut l'inverser. Conduire "
               "cette substitution en démarche d'écoconception : exigence "
               "écrite aux marchés, revues aux jalons, capitalisation en "
               "revue de projet (IEC 62430, ISO 14006, NF X30-264).",
     "qui": "AMO carbone avec les acheteurs",
     "quand": "Dès l'ACT : les déclarations s'exigent dans les marchés, pas "
              "après signature."},
    {"cle": "carbone_horaire",
     "quoi": "L'intensité carbone employée est une moyenne annuelle : elle ne "
             "permet pas d'arbitrer un pilotage horaire des charges.",
     "moteur_fait": "La moyenne annuelle par pays, et la distinction "
                    "market-based / location-based en piste de remplacement.",
     "leve_par": "intensite_reseau_g",
     "leve_note": "Renseignez le facteur de VOTRE contrat ou de votre année "
                  "de référence : la réserve tombe du résultat. Le pilotage "
                  "horaire, lui, reste une étude à part.",
     "normes": ["GHG Protocol — Scope 2 Guidance",
                "données horaires RTE éCO2mix / ENTSO-E",
                "24/7 Carbon-Free Energy Compact"],
     "calcul": "Croiser la courbe de charge IT horaire avec l'intensité "
               "horaire du réseau sur une année ; chiffrer le gain d'un "
               "décalage des charges différables ; en tirer le facteur "
               "effectif à contractualiser (PPA, garanties horaires).",
     "qui": "Énergéticien avec l'exploitant",
     "quand": "Dès le PRO si un PPA se négocie ; sinon en exploitation."},
]


def _verifier_limites():
    fautes = []
    cles = [x["cle"] for x in LIMITES]
    if len(set(cles)) != len(cles):
        fautes.append("clé de limite dupliquée")
    champs_profil = {c["id"] for c in CHAMPS}
    for x in LIMITES:
        for champ in ("quoi", "moteur_fait", "leve_note", "calcul", "qui", "quand"):
            if not str(x.get(champ) or "").strip():
                fautes.append("limite %s : champ %s vide" % (x["cle"], champ))
        if not x.get("normes"):
            fautes.append("limite %s : aucune norme" % x["cle"])
        # UNE LIMITE « LEVABLE » DOIT L'ÊTRE PAR UN CHAMP QUI EXISTE : nommer
        # un champ disparu enverrait le lecteur chercher une case absente.
        if x["leve_par"] is not None and x["leve_par"] not in champs_profil:
            fautes.append("limite %s : champ de levée inconnu %s"
                          % (x["cle"], x["leve_par"]))
    return fautes


def referentiel():
    """Le vocabulaire et les constantes, pour l'interface et la documentation."""
    return {
        "version": VERSION,
        "sources_consultables": SOURCES_CONSULTABLES,
        "limites": LIMITES,
        "refroidissement": REFROIDISSEMENT,
        "refroidissement_source": REFROIDISSEMENT_SOURCE,
        "classes_ashrae": CLASSES_ASHRAE,
        "ashrae_source": ASHRAE_SOURCE,
        "ewif": EWIF_PAYS,
        "ewif_source": EWIF_SOURCE,
        "intensite_reseau": INTENSITE_RESEAU,
        "intensite_millesime": INTENSITE_MILLESIME,
        "management": MANAGEMENT,
        "intensite_source": INTENSITE_SOURCE,
        "incorpore": INCORPORE,
        "incorpore_source": INCORPORE_SOURCE,
        "cadre_ue": CADRE_UE,
        "constantes": CONSTANTES,
    }


CHAMPS = [
    {"id": "puissance_it_kw", "label": "Puissance informatique installée", "unite": "kW",
     "type": "nombre", "requis": True},
    {"id": "taux_charge", "label": "Taux de charge moyen", "unite": "0–1",
     "type": "nombre", "defaut": 0.65,
     # Les deux seuils sont CALCULÉS depuis les constantes du moteur : écrits à
     # la main, ils annonçaient 0,55 quand le calcul appliquait 0,60.
     "aide": "Charge réelle moyenne rapportée à la puissance installée. "
             "Sous " + fr(CHARGE_POINT_CONCEPTION) + ", le PUE se dégrade — "
             + fr(CHARGE_PENTE) + " point de PUE par point de charge manquant ; "
             "au-dessus, " + PLATEAU_PUE + ". Sous " + fr(CHARGE_CONSOLIDER)
             + ", consolider "
             "les charges devient le premier levier proposé."},
    # Trié sur le NOM affiché, pas sur le code : trier « Allemagne, Danemark,
    # Espagne… » par « DE, DK, ES… » donne un ordre qui n'est alphabétique pour
    # personne. La moyenne européenne ferme la liste — c'est un repli, pas un
    # pays, et le placer entre deux pays le ferait choisir par erreur.
    {"id": "pays", "label": "Pays d'implantation", "type": "liste",
     "options": sorted((k for k in EWIF_PAYS if k != "UE"),
                       key=lambda k: EWIF_PAYS[k]["nom"]) + ["UE"],
     "aide": "Il commande le facteur eau de la production électrique et "
             "l'intensité carbone du réseau — deux grandeurs qui varient d'un "
             "facteur cinq d'un pays à l'autre."},
    {"id": "refroidissement", "label": "Famille de refroidissement", "type": "liste",
     "options": list(REFROIDISSEMENT.keys())},
    {"id": "classe_ashrae", "label": "Classe ASHRAE admise", "type": "liste",
     "options": list(CLASSES_ASHRAE.keys()), "defaut": "A2"},
    {"id": "part_evaporative", "label": "Part de chaleur rejetée par évaporation",
     "unite": "0–1", "type": "nombre",
     "aide": "Laisser vide pour la valeur par défaut de la famille retenue."},
    {"id": "cycles_concentration", "label": "Cycles de concentration de la tour",
     "type": "nombre", "defaut": 4},
    {"id": "part_renouvelable", "label": "Part d'énergie sans carbone contractualisée",
     "unite": "0–1", "type": "nombre", "defaut": 0.0},
    {"id": "part_chaleur_reutilisee", "label": "Part de chaleur fatale réutilisée",
     "unite": "0–1", "type": "nombre", "defaut": 0.0},
    {"id": "pue_cible", "label": "PUE imposé par le cahier des charges",
     "type": "nombre", "aide": "Laisser vide pour un PUE calculé depuis la conception."},
    {"id": "intensite_reseau_g", "label": "Intensité carbone du contrat",
     "unite": "gCO2e/kWh", "type": "nombre",
     "aide": "Laisser vide pour la moyenne nationale."},
    {"id": "nb_serveurs", "label": "Nombre de serveurs", "type": "nombre"},
    {"id": "prix_electricite_eur_mwh", "label": "Prix de l'électricité",
     "unite": "€/MWh", "type": "nombre", "defaut": 110},
]


# ── Des VALEURS PROPOSÉES, pour ne pas laisser le lecteur seul ─────────────
# Neuf champs sur treize sont des nombres libres. Devant « Cycles de
# concentration de la tour », qui ne sait pas déjà répond au hasard ou n'y
# touche pas — et un champ laissé sur son pré-remplissage compte comme non
# renseigné, donc bloque la phase sans que personne ne sache pourquoi.
#
# CHAQUE PROPOSITION PORTE CE QU'ELLE EST. Un nombre nu se recopie sans
# réfléchir ; « 0,55 — seuil sous lequel la pénalité de charge partielle
# devient le premier poste de perte » se choisit. La nature suit la même
# convention que partout ailleurs : un seuil réglementaire n'est pas un ordre
# de grandeur, et un ordre de grandeur n'est pas une mesure.
#
# CE NE SONT PAS DES LISTES FERMÉES. Ces grandeurs sont continues : imposer un
# choix parmi cinq valeurs interdirait la valeur réelle du projet, qui est
# précisément celle qu'on cherche à obtenir. Les propositions guident, elles ne
# contraignent pas.
SUGGESTIONS = {
    "puissance_it_kw": [
        {"valeur": 100, "nom": "salle serveurs d'entreprise",
         "nature": "ordre_grandeur"},
        {"valeur": 500, "nom": "seuil de déclaration européenne (EED art. 12)",
         "nature": "referentiel_externe"},
        {"valeur": 2000, "nom": "site de colocation courant",
         "nature": "ordre_grandeur"},
        {"valeur": 10000, "nom": "grand site",
         "nature": "ordre_grandeur"},
        {"valeur": 40000, "nom": "campus hyperscale",
         "nature": "ordre_grandeur"},
    ],
    # Les étiquettes disent ce que chaque valeur FAIT au calcul. « 0,80 — site
    # mature, bien rempli » laissait attendre un effet ; il n'y en a aucun, et
    # le taire faisait passer un modèle plat pour un formulaire bloqué.
    "taux_charge": [
        {"valeur": CHARGE_CONSOLIDER,
         "nom": "sous ce seuil, consolider les charges est le premier levier",
         "nature": "seuil"},
        {"valeur": CHARGE_POINT_CONCEPTION,
         "nom": "point de conception — sous cette valeur, le PUE se dégrade ; "
                "au-dessus, il ne bouge plus",
         "nature": "seuil"},
        {"valeur": 0.65, "nom": "valeur par défaut du formulaire — déjà "
                                "au-dessus du point de conception, donc sans "
                                "effet sur le PUE, mais elle fixe l'énergie "
                                "appelée",
         "nature": "hypothese"},
        # L'écart est CALCULÉ depuis les deux valeurs proposées. Écrit à la
        # main il annonçait « un quart » là où le rapport donne 23 % — et il
        # aurait menti davantage au premier ajustement de la valeur par défaut.
        {"valeur": 0.80, "nom": "site mature, bien rempli — même PUE que 0,65, "
                                "mais " + fr(round((0.80 / 0.65 - 1) * 100))
                                + " % d'énergie annuelle en plus : c'est le "
                                "RATIO qui est plat, pas la facture",
         "nature": "ordre_grandeur"},
    ],
    "part_evaporative": [
        {"valeur": 0.0, "nom": "aucune évaporation — refroidissement sec",
         "nature": "definition"},
        {"valeur": 0.5, "nom": "assistance adiabatique saisonnière",
         "nature": "ordre_grandeur"},
        {"valeur": 1.0, "nom": "tour évaporative en fonctionnement continu",
         "nature": "definition"},
    ],
    "cycles_concentration": [
        {"valeur": 3, "nom": "eau dure ou traitement limité — purge fréquente",
         "nature": "ordre_grandeur"},
        {"valeur": 4, "nom": "valeur par défaut du formulaire",
         "nature": "hypothese"},
        {"valeur": 6, "nom": "traitement d'eau poussé — purge réduite",
         "nature": "ordre_grandeur"},
    ],
    "part_renouvelable": [
        {"valeur": 0.0, "nom": "aucun contrat sans carbone", "nature": "definition"},
        {"valeur": 0.5, "nom": "moitié de la consommation contractualisée",
         "nature": "ordre_grandeur"},
        {"valeur": 1.0, "nom": "totalité contractualisée — à justifier par le contrat",
         "nature": "definition"},
    ],
    "part_chaleur_reutilisee": [
        {"valeur": 0.0, "nom": "aucun preneur de chaleur", "nature": "definition"},
        {"valeur": 0.1, "nom": "réseau de chaleur en projet, taux prudent",
         "nature": "ordre_grandeur"},
        {"valeur": 0.3, "nom": "preneur engagé et proche — haut de ce qui s'observe",
         "nature": "ordre_grandeur"},
    ],
    "prix_electricite_eur_mwh": [
        {"valeur": 80, "nom": "contrat long terme favorable",
         "nature": "ordre_grandeur"},
        {"valeur": 110, "nom": "valeur par défaut du formulaire",
         "nature": "hypothese"},
        {"valeur": 180, "nom": "marché tendu ou petit volume",
         "nature": "ordre_grandeur"},
    ],
}

# Ce qu'on OBSERVE réellement, par opposition à ce qui est saisissable. Une
# valeur hors de cette plage n'est pas refusée — le calcul reste juste, et
# c'est au projet de savoir s'il est hors norme — mais elle est SIGNALÉE.
# Sans ce garde-fou, une puissance de 500 000 kW passe sans un mot, et le
# lecteur ne saura qu'au chiffrage qu'il a saisi cinq cents mégawatts.
PLAGES_OBSERVEES = {
    "puissance_it_kw": {
        "bas": 20, "haut": 200000,
        "note": "Au-delà de 200 MW informatiques, on décrit un campus de "
                "plusieurs bâtiments : le calcul reste juste, mais un bilan "
                "unique perd son sens — chaque tranche a son raccordement, son "
                "refroidissement et son échéancier.",
        "note_bas": "Sous 20 kW, il s'agit d'un local technique plutôt que "
                    "d'un centre de données : les ratios du référentiel ne "
                    "sont pas établis à cette échelle.",
    },
    "taux_charge": {"bas": 0.30, "haut": 1.0,
                    "note": "Un taux de charge supérieur à 1 n'a pas de sens : "
                            "c'est une charge rapportée à la puissance installée.",
                    "note_bas": "Sous 0,30, l'installation est très largement "
                                "surdimensionnée — vérifiez qu'il s'agit bien "
                                "d'une moyenne annuelle."},
    "cycles_concentration": {"bas": 2, "haut": 10,
                             "note": "Au-delà de 10 cycles, l'entartrage et la "
                                     "corrosion deviennent le sujet principal.",
                             "note_bas": "Sous 2 cycles, la purge dépasse "
                                         "l'évaporation : le poste eau est "
                                         "dominé par le rejet."},
    "pue_cible": {"bas": 1.02, "haut": 2.5,
                  "note": "Un PUE au-delà de 2,5 décrit une installation "
                          "ancienne ou très dégradée.",
                  "note_bas": "Sous 1,02, le PUE ne laisse plus de place aux "
                              "auxiliaires : vérifiez le périmètre de mesure."},
}


# ── Le LIBELLÉ des options, servi avec le champ ────────────────────────────
# Les pages construisaient le nom elles-mêmes, avec un cas particulier écrit
# deux fois : « si le champ est le refroidissement, aller chercher le nom dans
# telle table ». Un troisième champ à nommer aurait fait une troisième copie,
# et le pays affichait donc son code ISO faute d'avoir la sienne.
#
# Le champ porte désormais ses libellés. La page ne sait plus dans quelle table
# regarder — elle n'a plus à le savoir.
_LIBELLES_OPTIONS = {
    "refroidissement": lambda k: (REFROIDISSEMENT.get(k) or {}).get("nom"),
    "pays": lambda k: (EWIF_PAYS.get(k) or {}).get("nom"),
    # La classe ASHRAE garde son code — c'est ainsi qu'elle se nomme dans les
    # documents — mais gagne sa plage : « A2 » seul n'apprend rien, « A2 —
    # 10 à 35 °C » situe immédiatement ce qu'elle autorise en free cooling.
    "classe_ashrae": lambda k: (
        "%s — %d à %d °C" % (k, (CLASSES_ASHRAE[k]["plage_c"][0]),
                             (CLASSES_ASHRAE[k]["plage_c"][1]))
        if (CLASSES_ASHRAE.get(k) or {}).get("plage_c") else None),
}

for _c in CHAMPS:
    # Les propositions et la plage observée voyagent AVEC le champ, comme les
    # libellés d'options : la page n'a pas à savoir dans quelle table chercher.
    if _c["id"] in SUGGESTIONS:
        _c["suggestions"] = SUGGESTIONS[_c["id"]]
    if _c["id"] in PLAGES_OBSERVEES:
        _c["plage_observee"] = PLAGES_OBSERVEES[_c["id"]]
    _f = _LIBELLES_OPTIONS.get(_c["id"])
    if _f and _c.get("options"):
        # Le code reste la CLÉ envoyée au moteur ; seul l'affichage change. Un
        # libellé transmis à la place d'un code ferait échouer la recherche au
        # référentiel, silencieusement, sur la valeur par défaut.
        _c["options_nom"] = {k: (_f(k) or k) for k in _c["options"]}
del _c, _f


# Le contrôle des limites court APRÈS la définition de CHAMPS : il vérifie
# qu'une limite « levable » nomme un champ du profil qui existe vraiment.
_F_LIMITES = _verifier_limites()
if _F_LIMITES:
    raise AssertionError("LIMITES : " + " | ".join(_F_LIMITES))
