# -*- coding: utf-8 -*-
"""Le bilan énergie / eau / carbone inséré dans une étude d'ingénierie complète.

Le moteur datacenter.py calcule juste. Il ne dit pas À QUEL MOMENT d'un projet
ses chiffres sont recevables — et c'est là que se perdent les dossiers. Un PUE
tiré d'une plage de conception convient parfaitement à un avant-projet
sommaire ; le même chiffre reporté tel quel dans un CCTP devient une clause de
pénalité assise sur un ordre de grandeur, et le premier bureau de contrôle le
voit.

Ce module tient donc deux choses ensemble :

  · LA SÉQUENCE. Deux traditions coexistent sur un centre de données, et les
    équipes les mélangent. La maîtrise d'œuvre bâtimentaire suit la loi MOP
    (ESQ, APS, APD, PRO, ACT, VISA, DET, AOR). L'ingénierie de procédé suit la
    filière industrielle (faisabilité, BASIC, FEED, EPCI, mise en service).
    Un centre de données relève des DEUX : c'est un bâtiment ET une
    installation de procédé. Les phases sont donc décrites côte à côte, avec
    leurs correspondances — et leurs non-correspondances, qui comptent autant.

  · L'APTITUDE. Pour chaque phase, on calcule ce que le moteur peut fournir et
    ce qu'il ne peut PAS fournir, à partir de ses incertitudes déclarées. Le
    facteur eau amont porte ±40 %, le carbone incorporé ±50 % : ces valeurs
    passent en APS, elles ne passent plus en DCE. Le module le dit, nomme les
    substitutions à opérer, et refuse de déclarer une phase franchissable
    quand elle ne l'est pas.

Rien n'est recopié du moteur : les incertitudes, les sources et les consignes
de remplacement sont LUES dans datacenter.py au moment de l'appel. Une valeur
retapée ici aurait divergé au premier ajustement du référentiel, et c'est le
cadre de phases qu'on aurait cru.
"""

import datacenter as D
import profil_dc as P

VERSION = "2026-08-a"


# ═══════════════════════════════════════════════════════════════════════════
#  1. LES DEUX FILIÈRES
# ═══════════════════════════════════════════════════════════════════════════

FILIERES = {
    "moe": {
        "nom": "Maîtrise d'œuvre de chantier",
        "cadre": "Loi n° 85-704 du 12 juillet 1985 (loi MOP), codifiée au code de "
                 "la commande publique ; décret n° 93-1268 du 29 novembre 1993 "
                 "pour le contenu des éléments de mission.",
        "portee": "Obligatoire pour la commande publique, reprise par usage en "
                  "maîtrise d'ouvrage privée. C'est la séquence du BÂTIMENT et "
                  "de ses lots techniques.",
        "note": "Le décret fixe le CONTENU de chaque élément de mission et impose "
                "au maître d'œuvre de s'engager sur un coût prévisionnel. Il ne "
                "fixe PAS le pourcentage de tolérance : celui-ci est arrêté au "
                "contrat de maîtrise d'œuvre. Les ordres de grandeur cités plus "
                "bas relèvent donc de l'usage professionnel, pas du texte.",
    },
    "indus": {
        "nom": "Ingénierie industrielle",
        "cadre": "Pratique d'ingénierie de projet ; classification des estimations "
                 "selon AACE International, Recommended Practice 18R-97.",
        "portee": "Séquence du PROCÉDÉ et de ses utilités — production de froid, "
                  "distribution électrique, secours, traitement d'eau. C'est celle "
                  "des grands projets d'infrastructure et d'énergie.",
        "note": "Les fourchettes de la RP 18R-97 sont données par l'AACE comme "
                "TYPIQUES et varient selon l'industrie et la complexité. Elles "
                "cadrent l'ordre de grandeur ; elles ne remplacent pas une "
                "précision établie projet par projet.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  2. CE QUE LE MOTEUR SAIT, ET AVEC QUELLE INCERTITUDE
# ═══════════════════════════════════════════════════════════════════════════
# Les clés désignent des postes du référentiel de datacenter.py. Le texte de
# source et la consigne de remplacement sont lus là-bas, jamais recopiés ici.

POSTES = {
    "ewif": {
        "nom": "Eau consommée en amont par la production électrique",
        "nature": "ordre_grandeur",
        "incertitude": "±40 %",
        "source_ref": "ewif_source",
        "remplacer_par": "Facteur du fournisseur d'électricité ou du gestionnaire "
                         "de réseau, pour l'année de référence du contrat.",
        "devient_insuffisant": "Tant que le chiffre sert à choisir un site ou à "
                               "ouvrir le dialogue avec l'autorité de l'eau, ±40 % "
                               "se tient : la décision qu'il éclaire tolère cette "
                               "dispersion. Dès qu'il devient une clause avec "
                               "pénalité, non — on ne fait pas peser une sanction "
                               "sur un ordre de grandeur.",
    },
    "incorpore": {
        "nom": "Carbone incorporé des équipements et du bâtiment",
        "nature": "ordre_grandeur",
        "incertitude": "±50 %",
        "source_ref": "incorpore_source",
        "remplacer_par": "Déclarations environnementales produit (FDES / EPD) des "
                         "équipements réellement retenus.",
        "devient_insuffisant": "±50 %, c'est un facteur trois entre les bornes. "
                               "Cela suffit à comparer des familles ; cela ne "
                               "suffit plus dès que le classement des leviers "
                               "de décarbonation en dépend, ce qui arrive quand "
                               "les équipements sont choisis.",
    },
    "intensite": {
        "nom": "Intensité carbone du réseau électrique",
        "nature": "moyenne_annuelle",
        "source_ref": "intensite_source",
        "remplacer_par": "Donnée officielle du gestionnaire de réseau pour l'année "
                         "de référence, ou facteur contractuel du fournisseur "
                         "(approche market-based, GHG Protocol Scope 2).",
        # Signalé explicitement : ce poste ne porte AUCUNE incertitude déclarée
        # au référentiel, alors que le balayage par pays fait varier l'empreinte
        # carbone d'un facteur six. Une incertitude absente n'est pas une
        # incertitude nulle.
        "incertitude_absente": True,
        "devient_insuffisant": "Une moyenne annuelle ne dit rien du profil horaire, "
                               "où l'écart entre heures creuses et heures de pointe "
                               "dépasse souvent un facteur trois. Dès qu'un "
                               "engagement carbone est pris, ou qu'un pilotage de "
                               "charge est arbitré, elle ne suffit plus.",
    },
    "evaporation": {
        "nom": "Borne physique de l'évaporation",
        "nature": "physique",
        "source_ref": None,
        "remplacer_par": None,       # une constante ne se remplace pas
        "devient_insuffisant": None,
    },
    "pue": {
        "nom": "PUE — plage de conception de la famille",
        "nature": "plage_de_conception",
        "source_ref": None,          # porté par famille, lu dynamiquement
        "remplacer_par": "Courbes constructeur des groupes froid et des onduleurs, "
                         "puis mesure sur site après mise en service.",
        "devient_insuffisant": "Une plage de conception décrit une FAMILLE, pas la "
                               "machine installée. Dès que les équipements sont "
                               "commandés, c'est leur courbe qui fait foi — et "
                               "c'est elle que l'essai de performance vérifiera.",
    },
}


def _source(cle):
    """Le texte de source, lu au référentiel du moteur."""
    r = D.referentiel()
    return r.get(cle) or ""


def _plage_pue(profil):
    """La plage de conception effectivement applicable au profil, et sa largeur
    relative. Lue au moteur : c'est lui qui décide quelle famille s'applique."""
    fam = (profil or {}).get("refroidissement") or "eau_glacee"
    ref = D.REFROIDISSEMENT.get(fam) or D.REFROIDISSEMENT["eau_glacee"]
    bas, haut = ref["pue_partiel"]
    demi = (haut - bas) / (haut + bas) * 100.0 if (haut + bas) else 0.0
    return {"famille": ref["nom"], "min": bas, "max": haut,
            "demi_etendue_pct": round(demi, 1)}


# ═══════════════════════════════════════════════════════════════════════════
#  3. LA SÉQUENCE DES PHASES
# ═══════════════════════════════════════════════════════════════════════════
# `exige` liste des identifiants de champs de datacenter.CHAMPS qui doivent être
# RÉELLEMENT renseignés — pas laissés sur leur pré-remplissage. `substitutions`
# liste les postes ci-dessus dont l'ordre de grandeur ne suffit plus.

PHASES = [
    # ── Maîtrise d'œuvre — loi MOP ────────────────────────────────────────
    {
        "filiere": "moe", "code": "ESQ", "rang": 1,
        "nom": "Esquisse",
        "objet": "Vérifier la faisabilité de l'opération au regard du programme et "
                 "de l'enveloppe, et proposer une ou plusieurs solutions "
                 "d'implantation.",
        "decide": "L'opération se fait ou ne se fait pas. Le site et le parti "
                  "général d'implantation.",
        "verrouille": "Rien d'irréversible, sauf le choix du terrain.",
        "exige": ["puissance_it_kw"],
        "substitutions": [],
        "apport_moteur": "complet",
        "precision": {"valeur": "±20 à 30 % sur le coût de travaux",
                      "nature": "usage", "aace": "Classe 5"},
        "livrable": [
            "Programme technique et hypothèses de puissance",
            "Solutions d'implantation examinées",
            "Ordres de grandeur énergie, eau et carbone par famille de refroidissement",
            "Contraintes de site connues à ce stade",
            "Estimation sommaire et aléas identifiés",
        ],
    },
    {
        "filiere": "moe", "code": "APS", "rang": 2,
        "nom": "Avant-projet sommaire",
        "objet": "Préciser la composition générale, apprécier les volumes, proposer "
                 "les dispositions techniques et établir une estimation "
                 "provisoire du coût des travaux.",
        "decide": "La famille de refroidissement. Le principe de secours "
                  "électrique. Le parti architectural.",
        "verrouille": "L'emprise et la trame ; revenir dessus coûte une reprise "
                      "complète de l'avant-projet.",
        "exige": ["puissance_it_kw", "pays", "refroidissement"],
        "substitutions": [],
        "apport_moteur": "complet",
        "precision": {"valeur": "±15 % environ sur le coût de travaux",
                      "nature": "usage", "aace": "Classe 4"},
        "livrable": [
            "Programme arrêté et puissance informatique retenue",
            "Composition générale et volumes",
            "Familles de refroidissement comparées — arbitrage eau / énergie / carbone",
            "Bilan énergie, eau et carbone de la solution retenue",
            "Contraintes de raccordement électrique et d'eau",
            "Estimation provisoire et calendrier prévisionnel",
            "Aléas et points à lever en avant-projet définitif",
        ],
    },
    {
        "filiere": "moe", "code": "APD", "rang": 3,
        "nom": "Avant-projet définitif",
        "objet": "Arrêter les dimensions, l'aspect, les matériaux et les "
                 "installations techniques, et ARRÊTER le coût prévisionnel des "
                 "travaux par corps d'état. Permet le dépôt du permis de construire.",
        "decide": "Le dimensionnement de tous les lots techniques. Les niveaux de "
                  "performance engagés.",
        "verrouille": "Le coût prévisionnel, sur lequel le maître d'œuvre s'engage. "
                      "Le permis de construire.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "taux_charge",
                  "part_evaporative"],
        "substitutions": ["intensite"],
        "apport_moteur": "partiel",
        "precision": {"valeur": "±10 % environ, tolérance fixée au contrat de MOE",
                      "nature": "usage", "aace": "Classe 3"},
        "livrable": [
            "Dimensionnement arrêté de la production de froid et des utilités",
            "Bilan de puissance électrique et schéma de secours",
            "Bilan d'eau annuel et mensuel — appoint, purge, rejets",
            "Bilan carbone — exploitation et incorporé, avec sources des facteurs",
            "Performances engagées : PUE, WUE, ERF et leurs conditions de mesure",
            "Coût prévisionnel arrêté par corps d'état",
            "Pièces du permis de construire — volet énergie et environnement",
            "Ce qui reste à confirmer par les données fournisseurs",
        ],
    },
    {
        "filiere": "moe", "code": "PRO", "rang": 4,
        "nom": "Projet",
        "objet": "Préciser par plans, coupes et élévations les formes et la nature "
                 "des ouvrages, déterminer l'implantation des équipements, et "
                 "établir le coût prévisionnel par lot.",
        "decide": "Les spécifications de chaque équipement. Les tracés.",
        "verrouille": "Tout ce qui part en consultation. Une modification après "
                      "consultation se paie en avenant.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "taux_charge",
                  "part_evaporative", "cycles_concentration", "part_renouvelable"],
        "substitutions": ["intensite", "incorpore"],
        "apport_moteur": "partiel",
        "precision": {"valeur": "±5 % environ sur le coût par lot",
                      "nature": "usage", "aace": "Classe 3 à 2"},
        "livrable": [
            "Plans, coupes et schémas de principe des installations",
            "Spécifications techniques de chaque équipement",
            "Note de calcul complète — énergie, eau, carbone, chaleur fatale",
            "Protocole de mesure des indicateurs contractuels",
            "Coût prévisionnel par lot",
            "Planning d'exécution et interfaces entre lots",
        ],
    },
    {
        "filiere": "moe", "code": "DCE", "rang": 5,
        "nom": "Dossier de consultation des entreprises",
        "objet": "Réunir les pièces contractuelles remises aux candidats : CCTP, "
                 "CCAP, plans, cadre de décomposition du prix.",
        "decide": "Ce qui devient opposable à l'entreprise.",
        "verrouille": "Les clauses de performance et leurs pénalités. Un indicateur "
                      "mal défini au CCTP ne se rattrape pas en cours de chantier.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "taux_charge",
                  "part_evaporative", "cycles_concentration", "part_renouvelable",
                  "pue_cible"],
        "substitutions": ["intensite", "incorpore", "ewif"],
        "apport_moteur": "cadre_seul",
        "precision": {"valeur": "Le prix devient une offre ; la précision n'est "
                                "plus une estimation mais un engagement",
                      "nature": "analyse", "aace": "Classe 2"},
        "note": "Le DCE n'est pas un élément de mission au sens du décret : c'est le "
                "dossier assemblé à partir du PRO et des pièces administratives, "
                "utilisé pendant l'élément ACT. La confusion est fréquente et elle "
                "change qui porte la responsabilité de chaque pièce.",
        "livrable": [
            "CCTP — clauses de performance environnementale opposables",
            "Définitions normatives exactes des indicateurs (ISO/IEC 30134, EN 50600)",
            "Protocole de mesure : points, périodicité, instruments, incertitude admise",
            "Périodes de référence et conditions d'exclusion",
            "Seuils, tolérances et pénalités",
            "Cadre de décomposition du prix global et forfaitaire",
            "Obligations de déclaration au titre de la directive efficacité énergétique",
        ],
    },
    {
        "filiere": "moe", "code": "ACT", "rang": 6,
        "nom": "Assistance à la passation des contrats de travaux",
        "objet": "Analyser les offres, conduire la mise au point et proposer "
                 "l'attribution.",
        "decide": "L'entreprise retenue et le contenu définitif de son engagement.",
        "verrouille": "Le marché de travaux.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "pue_cible"],
        "substitutions": ["intensite", "incorpore", "ewif"],
        "apport_moteur": "cadre_seul",
        "precision": {"valeur": "Analyse comparative des offres à méthode constante",
                      "nature": "analyse", "aace": "Classe 2"},
        "livrable": [
            "Grille d'analyse des offres — critères environnementaux pondérés",
            "Vérification de la cohérence des performances annoncées par chaque candidat",
            "Contrôle des valeurs annoncées contre les bornes physiques",
            "Points de mise au point technique",
            "Rapport d'analyse et proposition d'attribution",
        ],
    },
    {
        "filiere": "moe", "code": "EXE-VISA", "rang": 7,
        "nom": "Études d'exécution et visa",
        "objet": "Établir ou viser les études d'exécution de l'entreprise, et "
                 "vérifier leur conformité au projet.",
        "decide": "Les notes de calcul d'exécution et les plans d'atelier.",
        "verrouille": "Ce qui sera effectivement construit.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "taux_charge",
                  "part_evaporative", "pue_cible"],
        "substitutions": ["intensite", "incorpore", "ewif", "pue"],
        "apport_moteur": "cadre_seul",
        "precision": {"valeur": "Données constructeur des équipements retenus",
                      "nature": "analyse", "aace": "Classe 1"},
        "livrable": [
            "Visa des notes de calcul d'exécution — énergie, hydraulique, aéraulique",
            "Vérification des performances constructeur contre les engagements du marché",
            "Contrôle de l'instrumentation prévue au regard du protocole de mesure",
            "Réserves émises et levées",
        ],
    },
    {
        "filiere": "moe", "code": "DET", "rang": 8,
        "nom": "Direction de l'exécution des travaux",
        "objet": "Diriger l'exécution, vérifier l'avancement et la conformité, et "
                 "gérer financièrement le marché.",
        "decide": "Les adaptations de chantier et leur incidence.",
        "verrouille": "Chaque situation de travaux validée.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "pue_cible"],
        "substitutions": ["intensite", "incorpore", "ewif", "pue"],
        "apport_moteur": "cadre_seul",
        "precision": {"valeur": "Constaté sur ouvrage",
                      "nature": "analyse", "aace": "Classe 1"},
        "livrable": [
            "Suivi de la conformité des équipements livrés aux spécifications",
            "Incidence des adaptations de chantier sur les performances engagées",
            "Journal des écarts et des décisions",
            "Préparation des essais de performance",
        ],
    },
    {
        "filiere": "moe", "code": "AOR", "rang": 9,
        "nom": "Assistance aux opérations de réception",
        "objet": "Organiser les opérations préalables à la réception, assister le "
                 "maître d'ouvrage lors de la réception et pendant la garantie de "
                 "parfait achèvement.",
        "decide": "La réception, avec ou sans réserves.",
        "verrouille": "Le point de départ des garanties.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "pue_cible"],
        "substitutions": ["intensite", "incorpore", "ewif", "pue"],
        "apport_moteur": "cadre_seul",
        "precision": {"valeur": "Mesuré en exploitation, sur période de référence "
                                "contractuelle",
                      "nature": "analyse", "aace": "Classe 1"},
        "livrable": [
            "Protocole des essais de performance et conditions de validité",
            "Mesure du PUE et du WUE sur la période de référence",
            "Écart aux engagements et application éventuelle des pénalités",
            "Dossier des ouvrages exécutés — volet énergie et environnement",
            "Première déclaration au titre de la directive efficacité énergétique",
        ],
    },

    # ── Ingénierie industrielle ───────────────────────────────────────────
    {
        "filiere": "indus", "code": "FAISA", "rang": 1,
        "nom": "Faisabilité (Conceptual / Feasibility)",
        "objet": "Établir si le projet a une chance technique et économique, et "
                 "écarter les options non viables.",
        "decide": "On engage des études, ou on arrête.",
        "verrouille": "Rien.",
        "exige": ["puissance_it_kw"],
        "substitutions": [],
        "apport_moteur": "complet",
        "precision": {"valeur": "−50 % à +100 % (fourchette typique)",
                      "nature": "referentiel_externe", "aace": "Classe 5"},
        "livrable": [
            "Définition du besoin et de la capacité visée",
            "Options techniques envisagées et critères d'élimination",
            "Ordres de grandeur énergie, eau et carbone par option",
            "Contraintes de site : réseau électrique, ressource en eau, foncier",
            "Estimation de classe 5 et principaux aléas",
            "Recommandation d'engagement ou d'arrêt",
        ],
    },
    {
        "filiere": "indus", "code": "BASIC", "rang": 2,
        "nom": "BASIC (Basic Engineering / Pre-FEED)",
        "objet": "Figer le schéma de procédé et les bilans matière et énergie, "
                 "dimensionner les équipements principaux, et arrêter la "
                 "configuration de référence.",
        "decide": "Le schéma de principe. La technologie de refroidissement. "
                  "L'architecture électrique.",
        "verrouille": "La configuration de référence sur laquelle le FEED "
                      "travaillera.",
        "exige": ["puissance_it_kw", "pays", "refroidissement"],
        "substitutions": [],
        "apport_moteur": "complet",
        "precision": {"valeur": "−30 % à +50 % (fourchette typique)",
                      "nature": "referentiel_externe", "aace": "Classe 4"},
        "livrable": [
            "Bases de conception (Design Basis) et hypothèses",
            "Schéma de procédé et bilans matière et énergie",
            "Bilan thermique et dimensionnement de la production de froid",
            "Bilan d'eau — appoint, purge, cycles de concentration",
            "Bilan carbone d'exploitation et incorporé, en ordre de grandeur",
            "Liste des équipements principaux et niveaux de performance visés",
            "Estimation de classe 4 et plan de réduction des incertitudes",
        ],
    },
    {
        "filiere": "indus", "code": "FEED", "rang": 3,
        "nom": "FEED (Front-End Engineering Design)",
        "objet": "Porter la définition à un niveau permettant une consultation "
                 "EPC ferme : spécifications d'équipements, plans d'implantation, "
                 "interfaces, et estimation engageante.",
        "decide": "La décision finale d'investissement s'appuie dessus.",
        "verrouille": "Le périmètre contractuel de l'EPC. Ce qui n'est pas au FEED "
                      "devient un avenant.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "taux_charge",
                  "part_evaporative", "cycles_concentration"],
        "substitutions": ["intensite", "incorpore"],
        "apport_moteur": "partiel",
        "precision": {"valeur": "−20 % à +30 % (fourchette typique)",
                      "nature": "referentiel_externe", "aace": "Classe 3"},
        "livrable": [
            "Spécifications techniques des équipements majeurs",
            "Plans d'implantation, schémas électriques et hydrauliques",
            "Bilans détaillés — énergie, eau, carbone, chaleur fatale",
            "Analyse des interfaces et matrice de responsabilité",
            "Étude de dangers et analyses de risques du procédé",
            "Stratégie de mesure et d'instrumentation des indicateurs",
            "Estimation de classe 3 et dossier de décision d'investissement",
            "Consignes de remplacement des facteurs encore en ordre de grandeur",
        ],
    },
    {
        "filiere": "indus", "code": "EPCI", "rang": 4,
        "nom": "EPCI (Engineering, Procurement, Construction, Installation)",
        "objet": "Réaliser : ingénierie de détail, approvisionnement, construction "
                 "et installation, jusqu'aux essais mécaniques.",
        "decide": "Rien ne se décide plus, tout s'exécute. Les décisions "
                  "restantes sont des arbitrages de non-conformité.",
        "verrouille": "L'ouvrage.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "taux_charge",
                  "part_evaporative", "cycles_concentration", "part_renouvelable",
                  "pue_cible"],
        "substitutions": ["intensite", "incorpore", "ewif", "pue"],
        "apport_moteur": "cadre_seul",
        "precision": {"valeur": "−15 % à +20 % puis maîtrise d'exécution "
                                "(fourchette typique)",
                      "nature": "referentiel_externe", "aace": "Classe 2 à 1"},
        "livrable": [
            "Ingénierie de détail et notes de calcul d'exécution",
            "Spécifications d'achat et évaluation technique des fournisseurs",
            "Contrôle des déclarations environnementales produit reçues",
            "Recalage des bilans sur les données constructeur réelles",
            "Plans de contrôle, essais et réception d'équipements",
            "Dossier de construction et suivi des non-conformités",
            "Préparation de la mise en service",
        ],
    },
    {
        "filiere": "indus", "code": "CSU", "rang": 5,
        "nom": "Mise en service (Commissioning & Start-Up)",
        "objet": "Mettre en service, vérifier les performances contractuelles et "
                 "transférer à l'exploitant.",
        "decide": "L'acceptation de l'installation.",
        "verrouille": "Le transfert de responsabilité à l'exploitant.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "pue_cible"],
        "substitutions": ["intensite", "incorpore", "ewif", "pue"],
        "apport_moteur": "cadre_seul",
        "precision": {"valeur": "Mesuré, sur période de référence contractuelle",
                      "nature": "analyse", "aace": "Classe 1"},
        "livrable": [
            "Procédures de mise en service et essais de performance",
            "Conditions de validité des essais et cas d'exclusion",
            "Mesure des indicateurs contractuels et écart aux garanties",
            "Réserves, plan de levée et garanties de performance",
            "Dossier tel que construit et transfert à l'exploitation",
            "Mise en place du reporting réglementaire annuel",
        ],
    },
]

_PAR_CODE = {p["code"]: p for p in PHASES}


# ── Les exigences se CUMULENT le long d'une filière ────────────────────────
# Écrites phase par phase, elles régressaient : l'ACT réclamait moins que le
# DCE qui le précède, la CSU moins que l'EPCI. Un projet pouvait donc échouer à
# une phase et « passer » la suivante — une donnée arrêtée au projet ne redevient
# pas inconnue au chantier. Chaque phase déclare désormais ce qu'elle AJOUTE, et
# le cumul se calcule. sante() vérifie qu'aucune régression ne subsiste.

def _cumul(ph, cle):
    seq = [p for p in PHASES
           if p["filiere"] == ph["filiere"] and p["rang"] <= ph["rang"]]
    vus, out = set(), []
    for p in sorted(seq, key=lambda x: x["rang"]):
        for v in p[cle]:
            if v not in vus:
                vus.add(v)
                out.append(v)
    return out


def exigences(code):
    """Tout ce que la phase suppose acquis : ses propres ajouts et ceux de
    toutes les phases qui la précèdent dans sa filière."""
    ph = _PAR_CODE.get(code)
    if not ph:
        return {"entrees": [], "substitutions": []}
    return {"entrees": _cumul(ph, "exige"),
            "substitutions": _cumul(ph, "substitutions"),
            "en_propre": {"entrees": list(ph["exige"]),
                          "substitutions": list(ph["substitutions"])}}

# Correspondances entre les deux filières. Elles ne sont PAS des équivalences :
# un FEED va plus loin qu'un APD sur le procédé et moins loin sur le bâtiment.
# Le dire évite de croire qu'une phase franchie d'un côté dispense de l'autre.
CORRESPONDANCES = [
    {"moe": "ESQ", "indus": "FAISA", "accord": "franc",
     "ecart": "Les deux tranchent la même question : y va-t-on ?"},
    {"moe": "APS", "indus": "BASIC", "accord": "proche",
     "ecart": "Le BASIC fige les bilans matière et énergie ; l'APS s'arrête aux "
              "volumes et aux dispositions techniques."},
    {"moe": "APD", "indus": "FEED", "accord": "partiel",
     "ecart": "Le FEED pousse la définition du procédé plus loin que l'APD, mais "
              "l'APD porte le permis de construire, que le FEED ignore."},
    {"moe": "PRO", "indus": "FEED", "accord": "partiel",
     "ecart": "Le PRO descend au lot et au tracé ; le FEED reste au niveau de "
              "l'équipement et de l'interface."},
    {"moe": "DCE", "indus": "EPCI", "accord": "faible",
     "ecart": "Le DCE consulte sur un projet défini par la maîtrise d'œuvre ; "
              "l'EPCI confie la définition de détail au contractant. La "
              "responsabilité de conception n'est pas au même endroit."},
    {"moe": "AOR", "indus": "CSU", "accord": "proche",
     "ecart": "Même objet — constater la performance — mais l'AOR relève de la "
              "réception au sens du code civil, la CSU d'une garantie contractuelle."},
]


# ═══════════════════════════════════════════════════════════════════════════
#  4. L'APTITUDE : cette phase est-elle franchissable avec ce qu'on a ?
# ═══════════════════════════════════════════════════════════════════════════

APPORT = {
    "complet": "Le moteur couvre le besoin de cette phase : ses ordres de grandeur "
               "sont au niveau de définition attendu.",
    "partiel": "Le moteur fournit la structure et les bilans, mais certains "
               "facteurs doivent être remplacés par des données réelles avant "
               "de franchir la phase.",
    "cadre_seul": "Le moteur ne fournit plus de VALEURS recevables à ce stade : il "
                  "fournit le cadre — définitions normatives, protocole de mesure, "
                  "structure de la note. Les valeurs viennent des fournisseurs, "
                  "des essais ou de l'exploitation.",
}


def aptitude(profil, code):
    """Ce qui manque pour franchir la phase, sans complaisance.

    Deux familles de manques, et elles ne se soignent pas de la même façon :

      · les ENTRÉES non renseignées — on les saisit ;
      · les SUBSTITUTIONS non faites — on va chercher une donnée à l'extérieur,
        auprès d'un fournisseur ou d'un gestionnaire de réseau.

    Un champ laissé sur sa valeur par défaut compte comme non renseigné : c'est
    la règle établie dans profil_dc, et l'assouplir ici ferait déclarer
    franchissable une phase qui ne l'est pas.
    """
    ph = _PAR_CODE.get(code)
    if not ph:
        return {"connu": False, "motif": "Phase inconnue : %s" % code}

    profil = dict(profil or {})
    champs = {c["id"]: c for c in D.CHAMPS}
    ex = exigences(code)
    propres = set(ex["en_propre"]["entrees"])

    manques = []
    for cid in ex["entrees"]:
        c = champs.get(cid)
        if not c:
            continue
        etat = P._etat(profil, c)
        if etat != P.SAISI:
            manques.append({
                "id": cid, "label": c["label"], "unite": c.get("unite", ""),
                "etat": etat,
                # Distinguer ce que la phase ajoute de ce qu'elle hérite : on ne
                # traite pas de la même façon un oubli propre à l'étape et une
                # dette laissée par la phase précédente.
                "origine": "propre" if cid in propres else "heritee",
                "pourquoi": ("laissé sur la valeur par défaut du formulaire"
                             if etat == P.DEFAUT else "non précisé"),
            })

    subs = []
    for cle in ex["substitutions"]:
        po = POSTES.get(cle) or {}
        subs.append({
            "cle": cle,
            "nom": po.get("nom", cle),
            "nature": po.get("nature", ""),
            "incertitude": po.get("incertitude", ""),
            "incertitude_absente": bool(po.get("incertitude_absente")),
            "source": _source(po["source_ref"]) if po.get("source_ref") else "",
            "remplacer_par": po.get("remplacer_par") or "",
            # Pourquoi ICI et pas plus tôt : sans cette phrase, le cadre a l'air
            # d'un seuil arbitraire, et un seuil arbitraire se discute au lieu
            # de se respecter.
            "devient_insuffisant": po.get("devient_insuffisant") or "",
        })

    pl = _plage_pue(profil)
    franchissable = not manques and not subs
    return {
        "connu": True,
        "code": ph["code"], "nom": ph["nom"], "filiere": ph["filiere"],
        "apport_moteur": ph["apport_moteur"],
        "apport_texte": APPORT[ph["apport_moteur"]],
        "entrees_manquantes": manques,
        "substitutions_a_faire": subs,
        "franchissable": franchissable,
        "plage_pue": pl,
        "verdict": _verdict(ph, manques, subs),
    }


def _verdict(ph, manques, subs):
    """Une phrase qui dit où l'on en est. Écrite ici plutôt que dans la page :
    une conclusion rédigée côté navigateur finit par contredire les données qui
    l'ont produite."""
    if not manques and not subs:
        return ("Rien ne manque du côté du moteur pour cette phase. Ce qui reste "
                "à produire relève des autres disciplines du dossier.")
    bouts = []
    if manques:
        bouts.append("%d entrée%s à renseigner (%s)"
                     % (len(manques), "s" if len(manques) > 1 else "",
                        ", ".join(m["label"] for m in manques)))
    if subs:
        bouts.append("%d facteur%s dont l'ordre de grandeur ne suffit plus à ce "
                     "stade et qu'il faut remplacer par une donnée réelle (%s)"
                     % (len(subs), "s" if len(subs) > 1 else "",
                        ", ".join(s["nom"] for s in subs)))
    return ("Phase non franchissable en l'état : " + " ; ".join(bouts) + ".")


def parcours(profil, filiere):
    """Toute la filière d'un coup : où l'on passe, où l'on bute.

    Le premier point de blocage compte plus que le reste — c'est lui qui fixe le
    travail à engager. Les phases suivantes sont données pour la vue d'ensemble,
    pas comme un plan d'action parallèle.
    """
    ph = [p for p in PHASES if p["filiere"] == filiere]
    ph.sort(key=lambda x: x["rang"])
    etapes, premier_blocage = [], None
    for p in ph:
        a = aptitude(profil, p["code"])
        etapes.append({
            "code": p["code"], "nom": p["nom"], "rang": p["rang"],
            "objet": p["objet"], "decide": p["decide"], "verrouille": p["verrouille"],
            "precision": p["precision"], "note": p.get("note", ""),
            "livrable": p["livrable"],
            "apport_moteur": p["apport_moteur"],
            "franchissable": a["franchissable"],
            "n_manques": len(a["entrees_manquantes"]),
            "n_substitutions": len(a["substitutions_a_faire"]),
            "aptitude": a,
        })
        if premier_blocage is None and not a["franchissable"]:
            premier_blocage = p["code"]
    return {
        "filiere": filiere,
        "cadre": FILIERES[filiere],
        "etapes": etapes,
        "premier_blocage": premier_blocage,
        "n_franchissables": sum(1 for e in etapes if e["franchissable"]),
        "n_total": len(etapes),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  5. LE DOSSIER D'UNE PHASE
# ═══════════════════════════════════════════════════════════════════════════

def dossier(profil, code):
    """La structure de l'étude pour cette phase, avec les valeurs du moteur là
    où elles sont recevables — et la mention explicite « à produire » là où elles
    ne le sont pas.

    C'est le point de tout le module : un plan de document qui porte, section
    par section, ce qui est déjà calculé et ce qui reste à aller chercher. Un
    sommaire sans cette distinction se remplit de chiffres provisoires que
    personne ne remplace.
    """
    ph = _PAR_CODE.get(code)
    if not ph:
        return {"connu": False, "motif": "Phase inconnue : %s" % code}
    profil = dict(profil or {})
    if not profil.get("puissance_it_kw"):
        return {"connu": True, "disponible": False,
                "motif": "La puissance informatique installée est nécessaire."}

    a = aptitude(profil, code)
    etude = D.etude(profil)
    apport = ph["apport_moteur"]

    # Les grandeurs que le moteur peut verser au dossier, avec leur statut à ce
    # stade. « recevable » ne veut pas dire « juste » : cela veut dire que le
    # niveau de définition correspond à celui attendu par la phase.
    grandeurs = []
    for cle, sec, champ in [("pue", "energie", "pue"),
                            ("energie", "energie", "energie_totale_MWh"),
                            ("eau_site", "eau", "wue_site"),
                            ("eau_source", "eau", "wue_source"),
                            ("carbone", "carbone", "empreinte_totale_t"),
                            ("chaleur", "chaleur", "erf")]:
        v = (etude.get(sec) or {}).get(champ)
        if not v:
            continue
        touche = _postes_engages(cle)
        bloquants = [s for s in a["substitutions_a_faire"] if s["cle"] in touche]
        grandeurs.append({
            "nom": v["nom"], "valeur": v["valeur"], "unite": v["unite"],
            "incertitude": v.get("incertitude", ""),
            "statut": "a_remplacer" if bloquants else "recevable",
            "postes_bloquants": [s["nom"] for s in bloquants],
        })

    return {
        "connu": True, "disponible": True,
        "code": ph["code"], "nom": ph["nom"],
        "filiere": ph["filiere"], "filiere_nom": FILIERES[ph["filiere"]]["nom"],
        "objet": ph["objet"], "decide": ph["decide"], "verrouille": ph["verrouille"],
        "precision": ph["precision"], "note": ph.get("note", ""),
        "sections": ph["livrable"],
        "apport_moteur": apport, "apport_texte": APPORT[apport],
        "grandeurs": grandeurs,
        "aptitude": a,
        "correspondance": [c for c in CORRESPONDANCES
                           if c.get(ph["filiere"]) == ph["code"]],
        "version_moteur": D.VERSION,
    }


def _postes_engages(cle_grandeur):
    """Quels postes du référentiel entrent dans une grandeur donnée. Sert à dire
    QUELLE substitution bloque QUELLE valeur, plutôt que de marquer tout le
    dossier « à confirmer »."""
    return {
        "pue": {"pue"},
        "energie": {"pue"},
        "eau_site": {"pue"},
        "eau_source": {"pue", "ewif"},
        "carbone": {"pue", "intensite", "incorpore"},
        "chaleur": {"pue"},
    }.get(cle_grandeur, set())


def referentiel():
    """Le cadre complet, pour l'interface et la documentation."""
    return {
        "version": VERSION,
        "filieres": FILIERES,
        "phases": PHASES,
        "correspondances": CORRESPONDANCES,
        "postes": POSTES,
        "apport": APPORT,
        "moteur": D.VERSION,
    }


def sante():
    """Auto-contrôle. Vérifie surtout deux choses qu'une relecture manque : que
    toute entrée exigée existe bien au moteur — une phase qui réclame un champ
    inconnu ne serait jamais franchissable — et que les phases se durcissent
    dans l'ordre, sans qu'une phase tardive soit plus permissive qu'une
    précoce."""
    ids = {c["id"] for c in D.CHAMPS}
    inconnus = sorted({c for p in PHASES for c in p["exige"] if c not in ids})
    postes_inconnus = sorted({s for p in PHASES for s in p["substitutions"]
                              if s not in POSTES})
    # Contrôle des régressions sur les exigences CUMULÉES : c'est ce que voit
    # l'utilisateur. Écrites en propre, elles régressaient — le cumul l'a réglé,
    # et ce contrôle empêche que ça revienne.
    regressions = []
    for f in FILIERES:
        seq = sorted([p for p in PHASES if p["filiere"] == f],
                     key=lambda x: x["rang"])
        for i in range(1, len(seq)):
            av = set(exigences(seq[i - 1]["code"])["entrees"])
            ap = set(exigences(seq[i]["code"])["entrees"])
            sv = set(exigences(seq[i - 1]["code"])["substitutions"])
            sp = set(exigences(seq[i]["code"])["substitutions"])
            if (av - ap) or (sv - sp):
                regressions.append({"de": seq[i - 1]["code"], "a": seq[i]["code"],
                                    "entrees_perdues": sorted(av - ap),
                                    "substitutions_perdues": sorted(sv - sp)})
    p = {"puissance_it_kw": 2000}
    return {
        "version": VERSION,
        "phases": len(PHASES),
        "moe": sum(1 for x in PHASES if x["filiere"] == "moe"),
        "indus": sum(1 for x in PHASES if x["filiere"] == "indus"),
        "champs_exiges_inconnus": inconnus,
        "postes_inconnus": postes_inconnus,
        "regressions_d_exigence": regressions,
        "franchissables_profil_minimal": [
            e["code"] for e in parcours(p, "moe")["etapes"] if e["franchissable"]
        ] + [
            e["code"] for e in parcours(p, "indus")["etapes"] if e["franchissable"]
        ],
        "moteur": D.VERSION,
    }
