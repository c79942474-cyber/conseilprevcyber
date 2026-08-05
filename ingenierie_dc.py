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
        # Le CHIFFRAGE de cette phase n'est pas ici : ce moteur calcule
        # l'énergie, l'eau et le carbone, pas l'enveloppe d'investissement.
        # Celle-ci — décomposition par lot, exploitation, coût complet,
        # calendrier et avis motivé — est produite par conseilprev. Le dire
        # plutôt que de laisser croire que la faisabilité se boucle ici.
        "renvoi": {
            "titre": "Étude de faisabilité chiffrée et avis d'investissement",
            # Lien PROFOND : l'ancre ouvre directement le parcours guidé de
            # faisabilité. Sans elle, le lecteur atterrissait en haut d'une page
            # longue et devait retrouver seul la section qui le concerne — un
            # renvoi qu'il faut chercher est un renvoi qu'on abandonne.
            "url": "https://conseilprev.onrender.com/panorama#parcours=faisabilite",
            "quoi": "Enveloppe et décomposition par lot, exploitation, coût "
                    "complet, calendrier de raccordement, et l'avis motivé qui "
                    "en découle — avec, pour chaque constat, son fondement et "
                    "ce qui le renverserait.",
            "pourquoi": "Ce moteur-ci chiffre l'énergie, l'eau et le carbone. Il "
                        "ne chiffre pas l'investissement. Une faisabilité qui "
                        "ne porte pas d'enveloppe n'en est pas une.",
        },
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


# ═══════════════════════════════════════════════════════════════════════════
#  3 bis. LE REGISTRE DES PIÈCES
# ═══════════════════════════════════════════════════════════════════════════
# Le plan de l'étude dit CE QU'ON ÉCRIT. Le registre dit CE QU'ON REMET : notes,
# plans à leur échelle, tableaux, pièces contractuelles, procédures. Ce sont deux
# choses différentes, et confondre les deux fait livrer un rapport là où le
# marché attend seize pièces numérotées.
#
# Chaque pièce porte :
#   · son ÉMETTEUR — la maîtrise d'œuvre ne produit pas les plans d'exécution,
#     elle les vise. Attribuer une pièce au mauvais émetteur déplace une
#     responsabilité, et cela se paie au premier litige ;
#   · son TYPE — un plan au 1/50 et une note de calcul ne se relisent pas de la
#     même façon, ne se visent pas de la même façon, et ne s'archivent pas de la
#     même façon ;
#   · le fait qu'elle soit ALIMENTÉE PAR LE MOTEUR ou non. Celles qui le sont
#     héritent des grandeurs calculées et de leurs réserves de phase ; les autres
#     relèvent d'autres disciplines et sont listées pour mémoire, sans quoi le
#     registre laisserait croire que le moteur couvre tout le dossier.
#
# Ce registre relève de l'USAGE PROFESSIONNEL, pas d'un texte : la loi MOP fixe
# le contenu des éléments de mission, pas la nomenclature des pièces. Il se cale
# au marché de maîtrise d'œuvre, projet par projet.

TYPES_PIECE = {
    "note": {"nom": "Note", "aide": "Document de calcul ou de justification, rédigé."},
    "plan": {"nom": "Plan", "aide": "Pièce graphique cotée, à une échelle donnée."},
    "schema": {"nom": "Schéma", "aide": "Représentation de principe, non cotée."},
    "tableau": {"nom": "Tableau", "aide": "Données comparatives ou quantitatives structurées."},
    "contractuel": {"nom": "Pièce contractuelle",
                    "aide": "Pièce du marché, opposable une fois signée."},
    "procedure": {"nom": "Procédure", "aide": "Mode opératoire, essai ou contrôle."},
    "registre": {"nom": "Registre", "aide": "Suivi tenu dans la durée, daté et tracé."},
}

# Les émetteurs portent leur NOM et ce que le rôle engage. Le nom seul ne dit
# rien à qui découvre le vocabulaire — et se tromper d'émetteur déplace une
# responsabilité, ce qui se paie au premier litige.
EMETTEURS = {
    "moe": {"nom": "Maîtrise d'œuvre",
            "aide": "Conçoit, prescrit et contrôle. Elle produit les pièces de "
                    "conception et VISE celles de l'entreprise — elle ne les "
                    "rédige pas à sa place."},
    "bet": {"nom": "Bureau d'études spécialisé",
            "aide": "Intervient sur un domaine que la maîtrise d'œuvre ne couvre "
                    "pas seule — analyse de risques, acoustique, structure "
                    "complexe. Ses conclusions engagent sa propre responsabilité."},
    "mo": {"nom": "Maîtrise d'ouvrage",
           "aide": "Le donneur d'ordre. Il porte le programme, arrête le budget, "
                   "signe les marchés et prononce la réception. Certaines pièces "
                   "ne peuvent venir que de lui."},
    "entreprise": {"nom": "Entreprise de travaux",
                   "aide": "Exécute. Elle produit les études d'exécution et les "
                           "plans d'atelier, soumis au visa de la maîtrise "
                           "d'œuvre avant mise en fabrication."},
    "fournisseur": {"nom": "Fournisseur ou constructeur",
                    "aide": "Fournit un matériel et les données qui l'accompagnent : "
                            "courbes de performance, déclarations "
                            "environnementales, notices. Ces données remplacent "
                            "les ordres de grandeur du référentiel."},
    "epc": {"nom": "Contractant EPC",
            "aide": "Prend en charge ingénierie, achats et construction sous une "
                    "responsabilité unique. La conception de détail lui est "
                    "confiée — ce qui déplace la frontière des responsabilités "
                    "par rapport à une maîtrise d'œuvre classique."},
}


def _nom_emetteur(cle):
    e = EMETTEURS.get(cle)
    return (e or {}).get("nom", cle) if isinstance(e, dict) else (e or cle)


# ═══════════════════════════════════════════════════════════════════════════
#  3 ter. L'IDENTIFICATION DU PROJET
# ═══════════════════════════════════════════════════════════════════════════
# Ces trois listes n'entrent dans AUCUN calcul : elles cadrent la RÉDACTION.
# Elles vivent ici et non dans la page, pour la raison habituelle — une option
# recopiée dans le HTML finit par proposer un choix que le module ne sait plus
# interpréter.
#
# Chaque option porte ce qu'elle IMPLIQUE, et c'est la seule chose qui justifie
# une liste plutôt qu'un champ libre. « Colocation » tapé à la main n'est qu'un
# mot de plus dans le prompt ; l'option, elle, porte avec elle le fait que les
# indicateurs deviennent opposables aux clients hébergés et qu'il faut un
# sous-comptage par cage. C'est cela qui change le document produit.
#
# Le NOM du client reste en saisie libre : une liste de noms de clients n'a
# aucun sens et obligerait à choisir « Autre » à chaque projet.

MAITRISE_OUVRAGE = {
    "colocation": {
        "nom": "Opérateur de colocation",
        "implique": "Les indicateurs de performance deviennent opposables aux "
                    "clients hébergés, et pas seulement au maître d'ouvrage : les "
                    "pièces doivent prévoir le sous-comptage par cage ou par salle, "
                    "et le partage de responsabilité sur le PUE — l'exploitant ne "
                    "maîtrise pas la charge informatique de ses clients.",
    },
    "hyperscale": {
        "nom": "Opérateur hyperscale ou fournisseur de cloud",
        "implique": "Des standards internes de conception existent et priment "
                    "généralement sur les usages locaux : les spécifications s'y "
                    "réfèrent au lieu de les réécrire. La conception est répétable "
                    "d'un site à l'autre, et le délai de mise en service pèse plus "
                    "lourd que le coût unitaire.",
    },
    "entreprise": {
        "nom": "Entreprise pour son usage propre",
        "implique": "Le centre sert une seule activité : l'arbitrage entre "
                    "investissement et exploitation est interne, sans revente de "
                    "capacité. Les niveaux de disponibilité se justifient par "
                    "l'impact métier — à documenter — et non par une offre "
                    "commerciale.",
    },
    "fonds": {
        "nom": "Fonds d'infrastructure ou investisseur",
        "implique": "L'attente porte sur le coût complet et la valeur de sortie, "
                    "pas sur la technique pour elle-même. Les exigences "
                    "extra-financières des souscripteurs pèsent sur les pièces "
                    "environnementales, qui doivent être auditables par un tiers.",
    },
    "telecom": {
        "nom": "Opérateur de télécommunications",
        "implique": "La latence et les points de présence commandent l'implantation "
                    "avant le coût. Les pièces traitent l'interconnexion, les "
                    "chemins optiques redondants et la cohabitation avec des "
                    "équipements de transmission.",
    },
    "public": {
        "nom": "Maîtrise d'ouvrage publique",
        # La conséquence la plus lourde de la liste, et elle est juridique : elle
        # fait passer toute la séquence MOE de l'usage à l'obligation.
        "implique": "La loi MOP et le code de la commande publique s'appliquent : "
                    "les éléments de mission — ESQ, APS, APD, PRO, ACT, VISA, DET, "
                    "AOR — ne relèvent plus de l'usage mais de l'OBLIGATION, et "
                    "leur contenu est fixé par décret. Les seuils et procédures de "
                    "publicité conditionnent le calendrier de consultation.",
        "mop_obligatoire": True,
    },
    "souverain": {
        "nom": "Projet souverain ou de défense",
        "implique": "Des exigences de classification et d'homologation se "
                    "superposent à tout le reste et peuvent interdire certaines "
                    "fournitures. Les pièces prévoient le cloisonnement des "
                    "informations et une chaîne d'approvisionnement maîtrisée.",
    },
}

SECTEURS = {
    "colo_gros": {
        "nom": "Colocation de gros (wholesale)",
        "implique": "Des salles entières louées à un petit nombre de preneurs : la "
                    "conception se cale sur leurs exigences, souvent "
                    "contractualisées avant la construction.",
    },
    "colo_detail": {
        "nom": "Colocation de détail (retail)",
        "implique": "Beaucoup de clients, densités hétérogènes et remplissage "
                    "progressif : la pénalité de charge partielle est le premier "
                    "poste de perte des premières années.",
    },
    "hyperscale": {
        "nom": "Hyperscale et cloud public",
        "implique": "Densité élevée, conception répétable, exigences de délai "
                    "fortes. Le refroidissement liquide direct est souvent le point "
                    "de départ, pas une variante.",
    },
    "ia_hpc": {
        "nom": "Calcul intensif et intelligence artificielle",
        "implique": "Densité par baie très supérieure aux usages classiques : le "
                    "refroidissement liquide devient contraint et non choisi, et le "
                    "profil de charge est plus stable qu'en cloud généraliste.",
    },
    "entreprise": {
        "nom": "Salle informatique d'entreprise",
        "implique": "Puissance modeste, souvent en site occupé : les contraintes "
                    "d'intervention sans arrêt d'exploitation dominent la "
                    "conception.",
    },
    "edge": {
        "nom": "Edge et sites de proximité",
        "implique": "Faible puissance, nombreux sites, exploitation sans personnel "
                    "sur place : la télésurveillance et la standardisation priment "
                    "sur l'optimisation unitaire.",
    },
    "souverain": {
        "nom": "Cloud souverain ou hébergement qualifié",
        "implique": "Des exigences de qualification et de localisation des données "
                    "s'ajoutent : elles se traduisent en clauses, pas seulement en "
                    "choix techniques.",
    },
    "sante": {
        "nom": "Hébergement de données de santé",
        "implique": "L'hébergement de données de santé est soumis à certification : "
                    "traçabilité et disponibilité doivent figurer dans les pièces "
                    "contractuelles dès la consultation.",
    },
}

PERIMETRES = {
    "salle": {
        "nom": "Une salle informatique",
        "implique": "Le périmètre s'arrête aux limites de la salle : les pièces "
                    "définissent précisément les interfaces avec les utilités du "
                    "bâtiment, qui ne sont pas au marché.",
    },
    "batiment": {
        "nom": "Un bâtiment complet",
        "implique": "Le périmètre couvre le clos, le couvert et toutes les "
                    "utilités : l'ensemble des lots techniques est au marché, et "
                    "les interfaces entre lots deviennent le point dur.",
    },
    "campus": {
        "nom": "Un campus de plusieurs bâtiments",
        "implique": "Un plan-masse directeur et une stratégie de phasage sont "
                    "nécessaires : les utilités mutualisées — poste source, "
                    "production de froid centralisée — se dimensionnent sur la "
                    "cible et non sur la première tranche.",
    },
    "extension": {
        "nom": "Extension d'un site en exploitation",
        "implique": "Le site fonctionne pendant les travaux : les pièces traitent "
                    "les phases de basculement, les coupures programmées et le "
                    "maintien de la disponibilité contractuelle.",
    },
    "retrofit": {
        "nom": "Reprise ou rénovation d'un existant",
        "implique": "Un diagnostic de l'existant conditionne tout le reste : "
                    "capacité structurelle, état des réseaux, repérage des "
                    "matériaux dangereux le cas échéant. Les hypothèses de "
                    "conception ne valent qu'après relevés.",
    },
    "modulaire": {
        "nom": "Modules préfabriqués ou conteneurisés",
        "implique": "Une part de la conception est transférée au fournisseur des "
                    "modules : les pièces spécifient des interfaces et des "
                    "performances garanties plutôt que des ouvrages, et des lots "
                    "entiers disparaissent du marché de travaux.",
    },
    "multi": {
        "nom": "Plusieurs sites d'un même programme",
        "implique": "Les pièces sont mutualisées puis déclinées par site : il faut "
                    "distinguer ce qui relève du programme de ce qui relève de "
                    "chaque implantation, sous peine de tout renégocier à chaque "
                    "site.",
    },
}

IDENTIFICATION = [
    {"id": "maitrise_ouvrage", "label": "Type de maîtrise d'ouvrage",
     "aide": "Qui porte le projet — cela change à qui les indicateurs sont "
             "opposables, et parfois le régime juridique de la mission.",
     "options": MAITRISE_OUVRAGE},
    {"id": "secteur", "label": "Segment de marché du centre",
     "aide": "Ce que le centre héberge — cela commande la densité, le profil de "
             "charge et le mode de refroidissement de départ.",
     "options": SECTEURS},
    {"id": "perimetre", "label": "Périmètre de l'opération",
     "aide": "Ce qui est au marché — cela décide quels lots existent et où passent "
             "les interfaces.",
     "options": PERIMETRES},
]

IDENTIFICATION_NOTE = (
    "Ces choix n'entrent dans AUCUN calcul : ils cadrent la rédaction des pièces. "
    "Chacun porte ce qu'il implique pour le dossier, et cette implication est "
    "transmise au rédacteur — c'est ce qui distingue une liste d'un champ libre. "
    "Le nom du client, lui, reste en saisie libre : une liste de noms n'aurait "
    "aucun sens.")


def _option(table, cle):
    """L'option choisie, ou None. On ne devine pas : une clé inconnue ne doit
    surtout pas retomber sur une valeur par défaut qui ferait rédiger la pièce
    sous une hypothèse que personne n'a choisie."""
    o = (table or {}).get(str(cle or "").strip())
    return o if isinstance(o, dict) else None


def contexte_projet(inputs):
    """Ce que les choix d'identification impliquent, prêt à être transmis.

    Renvoie les options reconnues et, séparément, les valeurs non reconnues :
    une clé inventée doit se voir, pas se perdre en silence.
    """
    inputs = dict(inputs or {})
    retenus, inconnus = [], []
    for champ in IDENTIFICATION:
        v = inputs.get(champ["id"])
        if not v:
            continue
        o = _option(champ["options"], v)
        if not o:
            inconnus.append({"champ": champ["id"], "valeur": str(v)[:40]})
            continue
        retenus.append({"champ": champ["id"], "label": champ["label"],
                        "cle": str(v), "nom": o["nom"], "implique": o["implique"],
                        "mop_obligatoire": bool(o.get("mop_obligatoire"))})
    return {"retenus": retenus, "inconnus": inconnus,
            "mop_obligatoire": any(r["mop_obligatoire"] for r in retenus),
            "note": IDENTIFICATION_NOTE}


# (code, titre, type, émetteur, alimentée par le moteur, [ce qu'elle doit contenir])
_PIECES = {
    "ESQ": [
        ("ESQ-01", "Notice d'intention architecturale et technique", "note", "moe", False,
         ["Parti d'implantation retenu", "Principes constructifs envisagés",
          "Contraintes de site relevées"]),
        ("ESQ-02", "Plan de masse d'implantation (1/500)", "plan", "moe", False,
         ["Emprise et accès", "Poste de livraison et servitudes",
          "Réserves foncières pour extension"]),
        ("ESQ-03", "Schéma de principe de la production de froid", "schema", "moe", True,
         ["Famille de refroidissement envisagée", "Circuit de rejet de chaleur",
          "Principe d'appoint et de secours"]),
        ("ESQ-04", "Tableau des surfaces et des puissances", "tableau", "moe", True,
         ["Puissance informatique installée par salle", "Densité au mètre carré",
          "Surfaces techniques et de servitude"]),
        ("ESQ-05", "Estimation sommaire au ratio", "tableau", "moe", False,
         ["Ratio retenu en euros par kW informatique", "Provision pour aléas",
          "Bornes haute et basse assumées"]),
    ],
    "APS": [
        ("APS-01", "Notice descriptive sommaire par lot", "note", "moe", False,
         ["Dispositions techniques par lot", "Niveaux de performance visés",
          "Interfaces identifiées entre lots"]),
        ("APS-02", "Plans de niveau (1/200)", "plan", "moe", False,
         ["Distribution des salles et locaux techniques",
          "Cheminements principaux de fluides et de câbles", "Zones de maintenance"]),
        ("APS-03", "Plan de masse avec réseaux et accès (1/500)", "plan", "moe", False,
         ["Raccordements électrique et hydraulique", "Accès pompiers et livraisons",
          "Implantation des groupes froid et des groupes électrogènes"]),
        ("APS-04", "Schémas de principe CVC, électricité et secours", "schema", "moe", True,
         ["Architecture de production et de distribution de froid",
          "Architecture électrique et niveau de redondance",
          "Principe de secours et d'autonomie"]),
        ("APS-05", "Tableau comparatif des familles de refroidissement", "tableau", "moe", True,
         ["PUE, WUE de site et WUE de source par famille",
          "Carbone d'exploitation et incorporé", "Contreparties assumées de chaque famille"]),
        ("APS-06", "Bilan de puissance prévisionnel", "note", "moe", True,
         ["Puissance informatique et auxiliaires", "Foisonnement retenu",
          "Puissance à souscrire au raccordement"]),
        ("APS-07", "Estimation provisoire par lot", "tableau", "moe", False,
         ["Montant par lot technique", "Aléas et provisions",
          "Écarts par rapport à l'enveloppe du programme"]),
        ("APS-08", "Planning prévisionnel — jalons", "tableau", "moe", False,
         ["Jalons d'études et d'autorisations", "Délais de raccordement concessionnaires",
          "Chemin critique identifié"]),
    ],
    "APD": [
        ("APD-01", "Notice descriptive détaillée par lot", "note", "moe", False,
         ["Nature et qualité des matériaux et équipements",
          "Performances unitaires exigées", "Limites de prestation par lot"]),
        ("APD-02", "Plans de niveau, coupes et façades (1/100)", "plan", "moe", False,
         ["Implantation cotée des équipements techniques",
          "Coupes sur locaux techniques et gaines", "Traitement acoustique et bardages"]),
        ("APD-03", "Plans de réservations et de charges", "plan", "moe", False,
         ["Réservations en dalle et en voile", "Charges d'exploitation par zone",
          "Points de levage et accès de maintenance"]),
        ("APD-04", "Note de calcul thermique et dimensionnement du froid", "note", "moe", True,
         ["Charge thermique à évacuer", "Dimensionnement de la production et du rejet",
          "PUE de conception et pénalité de charge partielle"]),
        ("APD-05", "Bilan de puissance électrique définitif", "note", "moe", True,
         ["Bilan par tableau et par usage", "Régime de neutre et sélectivité",
          "Dimensionnement du secours et autonomie"]),
        ("APD-06", "Bilan d'eau annuel et mensuel", "note", "moe", True,
         ["Évaporation, purge et appoint", "Cycles de concentration retenus",
          "Saisonnalité du prélèvement et pointe estivale"]),
        ("APD-07", "Bilan carbone — exploitation et incorporé", "note", "moe", True,
         ["Carbone d'exploitation localisé et marché",
          "Carbone incorporé amorti par poste", "Source et incertitude de chaque facteur"]),
        ("APD-08", "Tableau des performances engagées", "tableau", "moe", True,
         ["PUE, WUE de site, WUE de source, ERF",
          "Conditions de mesure de chaque indicateur",
          "Tolérance proposée et période de référence"]),
        ("APD-09", "Coût prévisionnel arrêté par corps d'état", "tableau", "moe", False,
         ["Montant par corps d'état", "Tolérance contractuelle de l'engagement",
          "Options et variantes chiffrées"]),
        ("APD-10", "Pièces graphiques et notice du permis de construire", "contractuel", "moe", False,
         ["Insertion paysagère et volumétrie", "Notice énergie et environnement",
          "Étude d'impact ou examen au cas par cas, si requis"]),
    ],
    "PRO": [
        ("PRO-01", "CCTP par lot", "contractuel", "moe", False,
         ["Spécifications techniques par équipement",
          "Exigences de mise en œuvre et d'essais", "Documents à fournir par l'entreprise"]),
        ("PRO-02", "Plans d'ensemble (1/50) et détails (1/20)", "plan", "moe", False,
         ["Implantation définitive et cotée", "Détails de raccordement et de traversée",
          "Calepinage des locaux techniques"]),
        ("PRO-03", "Schémas hydrauliques et aérauliques cotés", "schema", "moe", True,
         ["Débits, températures et pressions à chaque tronçon",
          "Organes de réglage et de comptage", "Points de mesure des indicateurs"]),
        ("PRO-04", "Schémas unifilaires électriques", "schema", "moe", False,
         ["Distribution depuis la livraison jusqu'aux baies",
          "Comptage divisionnaire et points de mesure du PUE",
          "Sélectivité et régime de neutre"]),
        ("PRO-05", "Note de calcul complète — énergie, eau, carbone, chaleur", "note", "moe", True,
         ["Chaque grandeur avec sa formule et ses entrées",
          "Sources normatives et incertitudes",
          "Facteurs restant en ordre de grandeur"]),
        ("PRO-06", "Protocole de mesure des indicateurs", "procedure", "moe", True,
         ["Points de mesure, instruments et classes de précision",
          "Périodicité et méthode d'intégration",
          "Incertitude admise et conditions d'exclusion"]),
        ("PRO-07", "Cadre de décomposition du prix (DPGF)", "contractuel", "moe", False,
         ["Décomposition par lot et par ouvrage élémentaire",
          "Quantités et unités", "Postes en prix unitaires"]),
        ("PRO-08", "Tableau des interfaces entre lots", "tableau", "moe", False,
         ["Limite de prestation de chaque interface",
          "Lot responsable de la fourniture et de la pose",
          "Ordre d'intervention"]),
        ("PRO-09", "Planning d'exécution détaillé", "tableau", "moe", False,
         ["Tâches par lot et durées", "Contraintes d'enclenchement",
          "Jalons de mise en service"]),
    ],
    "DCE": [
        ("DCE-01", "Règlement de la consultation", "contractuel", "mo", False,
         ["Critères de jugement et leur pondération",
          "Pièces à remettre et forme des offres", "Calendrier de la consultation"]),
        ("DCE-02", "Acte d'engagement", "contractuel", "mo", False,
         ["Identification des parties et du marché",
          "Prix et forme du prix", "Délais et pénalités de retard"]),
        ("DCE-03", "CCAP", "contractuel", "mo", False,
         ["Ordre de préséance des pièces", "Modalités de règlement et de révision",
          "Garanties, réception et pénalités"]),
        ("DCE-04", "CCTP par lot — clauses de performance", "contractuel", "moe", True,
         ["Définitions normatives exactes des indicateurs",
          "Protocole de mesure opposable",
          "Seuils, tolérances et pénalités de performance"]),
        ("DCE-05", "DPGF, DQE et bordereau de prix unitaires", "contractuel", "moe", False,
         ["Décomposition exhaustive du prix global et forfaitaire",
          "Quantitatif estimatif pour comparaison des offres",
          "Prix unitaires pour les travaux modificatifs"]),
        ("DCE-06", "Plans du dossier de consultation", "plan", "moe", False,
         ["Jeu de plans complet et indicé",
          "Nomenclature et cartouche normalisé", "Liste des plans avec leurs indices"]),
        ("DCE-07", "Planning contractuel", "contractuel", "moe", False,
         ["Délai global et délais partiels",
          "Jalons contractuels assortis de pénalités", "Périodes de préparation"]),
        ("DCE-08", "Cadre de mémoire technique environnemental", "contractuel", "moe", True,
         ["Trame imposée aux candidats pour comparer à méthode constante",
          "Engagements chiffrés attendus et leur justification",
          "Pièces justificatives exigées (EPD, courbes constructeur)"]),
        ("DCE-09", "Tableau des indicateurs contractuels et pénalités", "tableau", "moe", True,
         ["Indicateur, valeur engagée, tolérance",
          "Période de référence et conditions d'exclusion",
          "Barème de pénalité et plafond"]),
    ],
    "ACT": [
        ("ACT-01", "Tableau d'ouverture des plis", "tableau", "mo", False,
         ["Candidats et complétude des offres",
          "Pièces manquantes et régularisations", "Recevabilité"]),
        ("ACT-02", "Grille d'analyse multicritères", "tableau", "moe", False,
         ["Critères et sous-critères pondérés",
          "Notation par candidat et justification", "Classement obtenu"]),
        ("ACT-03", "Tableau comparatif des performances annoncées", "tableau", "moe", True,
         ["PUE, WUE et carbone annoncés par chaque candidat",
          "Contrôle de cohérence contre les bornes physiques",
          "Écarts inexpliqués à faire lever"]),
        ("ACT-04", "PV de mise au point technique", "note", "moe", False,
         ["Points éclaircis avec le candidat pressenti",
          "Adaptations acceptées et leur incidence",
          "Engagements confirmés par écrit"]),
        ("ACT-05", "Rapport d'analyse des offres et proposition d'attribution", "note", "moe", False,
         ["Analyse technique et financière", "Motif du choix",
          "Réserves à lever avant notification"]),
    ],
    "EXE-VISA": [
        ("EXE-01", "Registre des documents d'exécution et de leurs visas", "registre", "moe", False,
         ["Document, indice, date de remise et de visa",
          "Statut du visa et observations", "Délais de visa contractuels"]),
        ("EXE-02", "Plans d'exécution", "plan", "entreprise", False,
         ["Plans d'atelier et de montage cotés",
          "Carnets de réservations définitifs", "Plans de cheminement et de repérage"]),
        ("EXE-03", "Notes de calcul d'exécution", "note", "entreprise", False,
         ["Dimensionnement définitif sur équipements retenus",
          "Équilibrage hydraulique et aéraulique",
          "Vérification des hypothèses de conception"]),
        ("EXE-04", "Fiches techniques et courbes constructeur", "note", "fournisseur", True,
         ["Courbes de rendement à charge partielle",
          "Consommations d'eau et conditions de fonctionnement",
          "Déclarations environnementales produit"]),
        ("EXE-05", "Tableau de contrôle — performances constructeur contre marché",
         "tableau", "moe", True,
         ["Valeur engagée au marché et valeur constructeur",
          "Écart et incidence sur les indicateurs",
          "Décision : accepté, réservé, refusé"]),
        ("EXE-06", "Registre des observations et réserves de visa", "registre", "moe", False,
         ["Observation émise et pièce concernée",
          "Réponse de l'entreprise", "Date de levée"]),
    ],
    "DET": [
        ("DET-01", "Comptes rendus de chantier", "registre", "moe", False,
         ["Avancement par lot et écarts au planning",
          "Décisions prises et diffusées", "Points bloquants et responsables"]),
        ("DET-02", "Registre des ordres de service", "registre", "moe", False,
         ["Objet, date et incidence de chaque ordre",
          "Incidence financière et de délai", "Notification et accusé de réception"]),
        ("DET-03", "États d'avancement et situations de travaux", "tableau", "moe", False,
         ["Avancement physique par poste de la décomposition",
          "Montant proposé au paiement", "Retenues appliquées"]),
        ("DET-04", "Registre des non-conformités", "registre", "moe", False,
         ["Non-conformité relevée et pièce concernée",
          "Traitement retenu et acceptation éventuelle", "Date de levée"]),
        ("DET-05", "Tableau de suivi des incidences sur les performances", "tableau", "moe", True,
         ["Adaptation de chantier et grandeur touchée",
          "Incidence chiffrée sur l'indicateur engagé",
          "Décision et accord du maître d'ouvrage"]),
    ],
    "AOR": [
        ("AOR-01", "Protocole des essais de performance", "procedure", "moe", True,
         ["Grandeurs mesurées et méthode",
          "Conditions de validité et cas d'exclusion",
          "Durée de la période de référence"]),
        ("AOR-02", "PV des opérations préalables à la réception", "contractuel", "moe", False,
         ["Constats par lot", "Réserves relevées et cotées",
          "Ouvrages non achevés"]),
        ("AOR-03", "Liste des réserves et plan de levée", "tableau", "moe", False,
         ["Réserve, lot, délai de levée", "Responsable désigné",
          "État de levée à date"]),
        ("AOR-04", "Rapport de mesure des indicateurs", "note", "moe", True,
         ["PUE et WUE mesurés sur la période de référence",
          "Comparaison aux valeurs engagées",
          "Incertitude de mesure et conclusion"]),
        ("AOR-05", "PV de réception", "contractuel", "mo", False,
         ["Décision de réception, avec ou sans réserves",
          "Date d'effet et point de départ des garanties",
          "Réserves annexées"]),
        ("AOR-06", "Dossier des ouvrages exécutés", "registre", "entreprise", True,
         ["Plans conformes à l'exécution",
          "Notices d'exploitation et de maintenance",
          "Note de calcul recalée sur les équipements installés"]),
        ("AOR-07", "Dossier d'intervention ultérieure sur l'ouvrage", "registre", "moe", False,
         ["Accès et moyens de maintenance prévus",
          "Risques résiduels signalés", "Dispositifs de sécurité en place"]),
        ("AOR-08", "Première déclaration au titre de la directive efficacité énergétique",
         "contractuel", "mo", True,
         ["Les grandeurs exigées par le règlement",
          "Méthode de collecte et de contrôle",
          "Périmètre déclaré et exclusions"]),
    ],
    "FAISA": [
        ("FAI-01", "Expression du besoin (Statement of Requirements)", "note", "mo", False,
         ["Capacité informatique visée et trajectoire",
          "Niveau de disponibilité attendu", "Contraintes de calendrier"]),
        ("FAI-02", "Note de concept et options examinées", "note", "moe", False,
         ["Options techniques envisagées",
          "Critères d'élimination appliqués", "Option de référence retenue"]),
        ("FAI-03", "Tableau comparatif des options", "tableau", "moe", True,
         ["Énergie, eau et carbone par option",
          "Ordres de grandeur assumés et incertitudes",
          "Contreparties de chaque option"]),
        ("FAI-04", "Note de contraintes de site", "note", "moe", True,
         ["Capacité de raccordement électrique",
          "Ressource en eau et contexte de tension hydrique",
          "Contraintes foncières et réglementaires"]),
        ("FAI-05", "Estimation de classe 5", "tableau", "moe", False,
         ["Montant et fourchette assumée",
          "Base et méthode d'estimation", "Aléas principaux"]),
        ("FAI-06", "Recommandation d'engagement ou d'arrêt", "note", "moe", False,
         ["Conclusion motivée", "Conditions de poursuite",
          "Travaux à engager en phase suivante"]),
    ],
    "BASIC": [
        ("BAS-01", "Bases de conception (Design Basis)", "note", "moe", True,
         ["Hypothèses de site, de climat et de charge",
          "Codes et normes applicables",
          "Niveaux de performance et de disponibilité visés"]),
        ("BAS-02", "Schéma de procédé (PFD)", "schema", "moe", True,
         ["Boucles de production et de distribution de froid",
          "Circuits de rejet et d'appoint d'eau",
          "Flux d'énergie principaux"]),
        ("BAS-03", "Bilans matière et énergie", "note", "moe", True,
         ["Bilan thermique global",
          "Bilan d'eau — évaporation, purge, appoint",
          "Bilan électrique et PUE de conception"]),
        ("BAS-04", "Liste préliminaire des équipements", "tableau", "moe", False,
         ["Repère, service et capacité de chaque équipement",
          "Nombre et redondance", "Encombrement estimé"]),
        ("BAS-05", "Plot plan préliminaire", "plan", "moe", False,
         ["Implantation des blocs fonctionnels",
          "Distances de sécurité et accès", "Réserves d'extension"]),
        ("BAS-06", "Synthèse des utilités", "tableau", "moe", True,
         ["Électricité, eau, air comprimé, secours",
          "Débits et puissances de pointe", "Points de raccordement"]),
        ("BAS-07", "Estimation de classe 4 et plan de réduction des incertitudes",
         "tableau", "moe", True,
         ["Montant et fourchette", "Postes les plus incertains",
          "Données à acquérir avant le FEED"]),
    ],
    "FEED": [
        ("FEE-01", "Bases de conception mises à jour", "note", "moe", True,
         ["Écarts par rapport au BASIC et leur motif",
          "Hypothèses confirmées ou levées",
          "Facteurs encore en ordre de grandeur"]),
        ("FEE-02", "Schémas de tuyauterie et d'instrumentation (P&ID)", "schema", "moe", True,
         ["Équipements, lignes et instruments repérés",
          "Organes de sécurité et de régulation",
          "Points de mesure des indicateurs contractuels"]),
        ("FEE-03", "Schéma unifilaire général", "schema", "moe", False,
         ["Architecture depuis la livraison jusqu'aux charges",
          "Redondance et sources de secours", "Comptage et supervision"]),
        ("FEE-04", "Fiches techniques des équipements majeurs", "tableau", "moe", True,
         ["Conditions de service et performances exigées",
          "Consommations d'eau et d'énergie garanties",
          "Documents fournisseur à remettre"]),
        ("FEE-05", "Plot plan et plans d'implantation", "plan", "moe", False,
         ["Implantation définitive des équipements",
          "Cheminements principaux et zones de maintenance",
          "Contraintes de levage et de remplacement"]),
        ("FEE-06", "Avant-métré (Material Take-Off)", "tableau", "moe", False,
         ["Quantités par discipline",
          "Base de l'avant-métré et taux de croissance retenu",
          "Postes non métrés et provisions"]),
        ("FEE-07", "Matrice cause-effet et arrêts d'urgence", "tableau", "moe", False,
         ["Causes détectées et actions déclenchées",
          "Niveaux d'arrêt et acquittement",
          "Essais de vérification prévus"]),
        ("FEE-08", "Rapport d'analyse de risques (HAZOP)", "note", "bet", False,
         ["Nœuds étudiés et déviations examinées",
          "Actions retenues et responsables",
          "Risques résiduels acceptés"]),
        ("FEE-09", "Matrice de responsabilité et interfaces", "tableau", "moe", False,
         ["Limite de fourniture par interface",
          "Responsable de la conception et de la mise en œuvre",
          "Documents échangés à chaque interface"]),
        ("FEE-10", "Stratégie d'instrumentation et de mesure", "procedure", "moe", True,
         ["Points de mesure nécessaires aux indicateurs",
          "Classes de précision et incertitude résultante",
          "Acquisition, archivage et intégrité de la donnée"]),
        ("FEE-11", "Bilans détaillés — énergie, eau, carbone, chaleur fatale", "note", "moe", True,
         ["Chaque bilan avec ses entrées et ses sources",
          "Sensibilité aux hypothèses restantes",
          "Consignes de remplacement des facteurs"]),
        ("FEE-12", "Estimation de classe 3 et dossier de décision d'investissement",
         "tableau", "moe", True,
         ["Coût d'investissement et d'exploitation",
          "Fourchette et aléas", "Éléments de décision et sensibilités"]),
        ("FEE-13", "Dossier de consultation EPC (ITB)", "contractuel", "moe", True,
         ["Périmètre confié et limites de prestation",
          "Garanties de performance exigées et méthode de vérification",
          "Trame de réponse imposée aux soumissionnaires"]),
    ],
    "EPCI": [
        ("EPC-01", "Ingénierie de détail", "plan", "epc", False,
         ["Isométriques de tuyauterie et notes de flexibilité",
          "Cheminements et bordereaux de câbles",
          "Plans de génie civil et de charpente"]),
        ("EPC-02", "Spécifications d'achat", "contractuel", "epc", True,
         ["Exigences techniques et de performance par équipement",
          "Documents et essais exigés du fournisseur",
          "Déclarations environnementales produit à remettre"]),
        ("EPC-03", "Registre des documents fournisseurs", "registre", "epc", False,
         ["Document attendu, reçu, commenté, approuvé",
          "Délais et retards", "Impact des retards sur le montage"]),
        ("EPC-04", "Contrôle des déclarations environnementales reçues", "tableau", "moe", True,
         ["Facteur de référentiel remplacé par la donnée réelle",
          "Écart constaté et incidence sur le bilan",
          "Pièce justificative et sa date"]),
        ("EPC-05", "Recalage des bilans sur les données constructeur", "note", "moe", True,
         ["Bilans recalculés avec les valeurs réelles",
          "Écart aux valeurs contractuelles",
          "Conséquence sur les garanties"]),
        ("EPC-06", "Plans de contrôle et d'essais (ITP)", "procedure", "epc", False,
         ["Points d'arrêt et points d'inspection",
          "Critères d'acceptation et documents de preuve",
          "Intervenants et notification"]),
        ("EPC-07", "Dossier de construction", "registre", "epc", False,
         ["Procédures de montage et de soudage",
          "Qualifications des intervenants", "Traçabilité des matériaux"]),
        ("EPC-08", "Registre des non-conformités et dérogations", "registre", "epc", False,
         ["Non-conformité, cause et traitement",
          "Dérogation demandée et décision", "Incidence sur la garantie"]),
        ("EPC-09", "Liste des réserves de fin de montage (punch list)", "tableau", "epc", False,
         ["Réserve, catégorie et criticité",
          "Bloquante ou non pour la mise en service", "Délai de levée"]),
    ],
    "CSU": [
        ("CSU-01", "Procédures de mise en service", "procedure", "epc", False,
         ["Séquence de mise en service par système",
          "Prérequis et consignations", "Critères de passage à l'étape suivante"]),
        ("CSU-02", "Check-lists de pré-mise en service", "procedure", "epc", False,
         ["Contrôles mécaniques, électriques et instrumentation",
          "Essais à vide et rinçages", "Constats et signatures"]),
        ("CSU-03", "Procédure d'essai de performance", "procedure", "moe", True,
         ["Grandeurs mesurées et instruments utilisés",
          "Conditions de validité, durée et charge d'essai",
          "Méthode de calcul et incertitude"]),
        ("CSU-04", "Rapport d'essais et écart aux garanties", "note", "moe", True,
         ["Résultats mesurés indicateur par indicateur",
          "Écart aux garanties contractuelles",
          "Conclusion : accepté, réserve, pénalité"]),
        ("CSU-05", "Certificats d'acceptation mécanique et de prise en charge",
         "contractuel", "mo", False,
         ["Systèmes acceptés et date d'effet",
          "Réserves annexées", "Transfert de responsabilité et de risque"]),
        ("CSU-06", "Dossier tel que construit (as-built)", "registre", "epc", True,
         ["Plans et schémas conformes à l'exécution",
          "Fiches équipements et paramètres de réglage",
          "Bilans recalés sur l'installation réelle"]),
        ("CSU-07", "Dossier de transfert à l'exploitation", "registre", "epc", False,
         ["Manuels d'exploitation et de maintenance",
          "Plan de maintenance préventive et pièces de rechange",
          "Formation des équipes d'exploitation"]),
        ("CSU-08", "Mise en place du reporting réglementaire annuel", "procedure", "mo", True,
         ["Grandeurs à déclarer et leur source de mesure",
          "Processus de collecte, contrôle et validation",
          "Calendrier et responsable désigné"]),
    ],
}


# ── L'axe DISCIPLINE ───────────────────────────────────────────────────────
# Les pièces ci-dessus appartiennent à une phase et à une seule. Les
# spécifications techniques, elles, traversent le projet : une spécification CVC
# s'émet à l'avant-projet définitif, se met à jour au projet et se gèle à la
# consultation. Les recopier dans chaque phase en ferait trois documents
# distincts qui divergeraient — c'est un document unique, à des indices
# différents.
#
# Chaque spécification déclare donc les phases où elle est produite ET le NIVEAU
# attendu à chacune. Le niveau n'est pas cosmétique : il dit à l'ingénieur — et
# au modèle qui rédige — jusqu'où descendre. Une spécification de consultation
# qui resterait au niveau de l'avant-projet laisse des exigences non mesurables,
# et une exigence non mesurable n'est pas opposable.

NIVEAUX = {
    "principes": {"nom": "Principes", "aide": "Parti retenu et exigences de niveau, "
                                              "sans dimensionnement."},
    "emission": {"nom": "Première émission", "aide": "Exigences dimensionnées, "
                                                     "performances visées, interfaces."},
    "maj": {"nom": "Mise à jour", "aide": "Descente au niveau de l'ouvrage : "
                                          "matériels, tracés, essais."},
    "gel": {"nom": "Gel contractuel", "aide": "Devient opposable : chaque exigence "
                                              "mesurable et assortie de sa méthode de contrôle."},
    "recalage": {"nom": "Recalage", "aide": "Repris sur les données réelles des "
                                            "équipements retenus."},
    "as_built": {"nom": "Tel que construit", "aide": "Conforme à l'exécution, "
                                                     "versé au dossier d'exploitation."},
}

# Chaque discipline porte son explication ICI, à la source. Le glossaire la
# reprend au lieu de la réécrire : une définition recopiée à côté de la table
# qu'elle décrit finit par ne plus décrire la même chose.
# La seconde phrase de chaque aide dit le rapport de la discipline AU CALCUL
# énergie / eau / carbone — c'est la question que pose cette page, et une
# discipline qui n'y touche pas le dit aussi clairement.
DISCIPLINES = {
    "projet": {
        "nom": "Conduite de projet",
        "aide": "Planning, interfaces entre lots, maîtrise des modifications et "
                "registre documentaire — ce qui tient l'opération, pas ce qui la "
                "conçoit.\nElle ne produit aucune grandeur physique, mais c'est "
                "elle qui date le gel : le calcul n'a de valeur contractuelle "
                "qu'une fois la version figée et tracée.",
    },
    "safety": {
        "nom": "Safety — sécurité des personnes et des procédés",
        "aide": "Analyse de risque, philosophie générale de sécurité, scénarios "
                "redoutés, mise en sécurité — les accidents, par opposition aux "
                "actes malveillants qui relèvent de la sûreté.\nElle contraint le "
                "calcul plus qu'elle ne s'en nourrit : un local batteries ventilé "
                "pour l'hydrogène, un groupe froid à l'arrêt en scénario de mise "
                "en sécurité, ce sont des consommations que la moyenne ignore.",
    },
    "structure": {
        "nom": "Structure et génie civil",
        "aide": "Fondations, planchers, charges d'exploitation, sismique, massifs "
                "de groupes électrogènes, cheminements enterrés.\nElle porte "
                "l'essentiel du carbone incorporé du bâtiment — le poste que le "
                "moteur annonce à ±50 %, et celui que les FDES des matériaux "
                "réellement retenus viendront resserrer.",
    },
    "hvac": {
        "nom": "CVC, traitement d'air et froid",
        "aide": "Production et distribution de froid, traitement d'air, "
                "confinement des allées, régulation, heures de free cooling.\n"
                "C'est la discipline qui fabrique le PUE et le WUE de site : la "
                "plage de conception retenue ici décide la consommation non "
                "informatique et le mode d'évacuation de la chaleur.",
    },
    "elec_cfo": {
        "nom": "Électricité courants forts",
        "aide": "Raccordement au réseau, postes de livraison, transformateurs, "
                "onduleurs, groupes électrogènes, distribution jusqu'aux baies, "
                "sélectivité et courts-circuits.\nElle fixe la puissance "
                "souscrite — la seule grandeur d'entrée dont le calcul ne peut "
                "pas se passer — et les rendements de chaîne qui pèsent sur le "
                "PUE au même titre que le froid.",
    },
    "elec_cfa": {
        "nom": "Électricité courants faibles",
        "aide": "Détection, GTB, supervision technique, câblage structuré, "
                "comptage divisionnaire, vidéo et contrôle d'accès côté câblage."
                "\nSans comptage par poste installé par cette discipline, la "
                "consommation par consommateur reste une hypothèse de calcul et "
                "ne devient jamais une mesure.",
    },
    "telecom": {
        "nom": "Téléphonie et réseaux de communication",
        "aide": "Arrivées opérateurs, chemins de fibre redondants et physiquement "
                "distincts, téléphonie, liaisons de sécurité et d'astreinte.\n"
                "Sans effet sur le bilan énergétique, mais déterminante pour "
                "l'implantation : deux arrivées empruntant le même fourreau ne "
                "font qu'un seul chemin, quel que soit le contrat.",
    },
    "incendie": {
        "nom": "Prévention et sécurité incendie",
        "aide": "Compartimentage, désenfumage, évacuation, résistance au feu, "
                "conformité au code du travail et au régime ICPE applicable.\n"
                "Elle impose des volumes et des débits d'air que le calcul ne "
                "prévoit pas de lui-même : un désenfumage dimensionné après coup "
                "rouvre la conception aéraulique.",
    },
    "extinction": {
        "nom": "Extinction automatique",
        "aide": "Choix du principe — gaz, brouillard d'eau, sprinkleur —, "
                "dimensionnement, et besoins en eau d'extinction associés.\n"
                "C'est le poste d'eau que le WUE ne voit pas : une réserve "
                "d'extinction ne se consomme pas en exploitation, mais elle se "
                "négocie avec la même autorité de l'eau que le refroidissement.",
    },
    "surete": {
        "nom": "Sûreté et contrôle d'accès",
        "aide": "Intrusion, périmètre, contrôle d'accès, vidéoprotection, "
                "gestion des visiteurs — les actes malveillants, par opposition "
                "aux accidents traités par la safety.\nElle ne pèse pas sur le "
                "bilan, mais elle conditionne l'accès aux locaux techniques où "
                "se relèvent les compteurs qui, eux, l'alimentent.",
    },
    "itot": {
        "nom": "Équipements IT / OT / systèmes de contrôle industriel",
        "aide": "Charge informatique elle-même, baies, densité, et systèmes de "
                "contrôle industriel de l'installation — avec la séparation "
                "entre réseaux de gestion technique et réseaux de production.\n"
                "C'est la source de la puissance informatique : tout le calcul "
                "part d'elle, et sa densité par baie décide de ce que le froid "
                "devra évacuer.",
    },
    "environnement": {
        "nom": "Environnement, énergie et RSE",
        "aide": "Bilan énergie, eau et carbone, dossier ICPE, chaleur fatale "
                "récupérable, bâtiment bas carbone, rapportage extra-financier."
                "\nC'est la discipline qui porte le calcul lui-même : elle "
                "consolide ce que les autres produisent et répond des chiffres "
                "déclarés à l'extérieur.",
    },
}


def _nom_discipline(cle):
    d = DISCIPLINES.get(cle)
    return (d or {}).get("nom", cle) if isinstance(d, dict) else (d or cle)


# (code, titre, discipline, type, émetteur, moteur, {phase: niveau}, [contenu])
_PIECES_DISCIPLINE = [
    # ── Conduite de projet ────────────────────────────────────────────────
    ("SPC-MDL", "Liste des livrables du projet (registre documentaire)", "projet",
     "registre", "moe", False,
     {"ESQ": "principes", "APS": "emission", "APD": "maj", "PRO": "maj",
      "DCE": "gel", "EXE-VISA": "maj", "AOR": "as_built",
      "FAISA": "principes", "BASIC": "emission", "FEED": "maj",
      "EPCI": "maj", "CSU": "as_built"},
     ["Une ligne par pièce : code, intitulé, discipline, émetteur, phase",
      "Indice en cours, date d'émission et statut de visa",
      "Destinataires et circuit d'approbation de chaque pièce",
      "Pièces conditionnelles et l'événement qui les déclenche"]),
    ("SPC-PHILO", "Philosophie générale de conception (Design Philosophy)", "projet",
     "note", "moe", True,
     {"ESQ": "principes", "APS": "emission", "APD": "maj", "PRO": "gel",
      "FAISA": "principes", "BASIC": "emission", "FEED": "gel"},
     ["Intentions de conception et hiérarchie des objectifs",
      "Niveau de disponibilité visé et principe de redondance retenu",
      "Arbitrages structurants assumés — eau contre énergie, capex contre opex",
      "Règles de conception communes à toutes les disciplines",
      "Hypothèses climatiques et de charge, et leur origine"]),

    # ── Safety ────────────────────────────────────────────────────────────
    ("SPC-SAFETY", "Safety concept et spécification safety", "safety",
     "contractuel", "moe", False,
     {"APS": "principes", "APD": "emission", "PRO": "maj", "DCE": "gel",
      "BASIC": "principes", "FEED": "emission", "EPCI": "maj"},
     ["Périmètre safety et interfaces avec la sûreté et l'incendie",
      "Analyse des risques pour les personnes et les équipements",
      "Fonctions instrumentées de sécurité et niveaux d'intégrité visés",
      "Arrêts d'urgence, consignations et modes dégradés",
      "Essais périodiques et preuves à conserver"]),

    # ── Structure ─────────────────────────────────────────────────────────
    ("SPC-STRUCT", "Spécification technique — structure et génie civil", "structure",
     "contractuel", "moe", False,
     {"APD": "emission", "PRO": "maj", "DCE": "gel", "EXE-VISA": "maj",
      "FEED": "emission", "EPCI": "maj"},
     ["Charges d'exploitation par zone et surcharges d'équipements",
      "Résistance au feu exigée et compartimentage structurel",
      "Contraintes sismiques et de vent applicables au site",
      "Réservations, trémies et reprises en sous-œuvre",
      "Tolérances dimensionnelles et de planéité des dalles techniques"]),

    # ── CVC ───────────────────────────────────────────────────────────────
    ("SPC-HVAC", "Spécification technique — CVC, traitement d'air et froid", "hvac",
     "contractuel", "moe", True,
     {"APS": "principes", "APD": "emission", "PRO": "maj", "DCE": "gel",
      "EXE-VISA": "recalage", "BASIC": "principes", "FEED": "emission",
      "EPCI": "recalage"},
     ["Charge thermique à évacuer et profil de charge retenu",
      "Régimes de température, débits et pressions par boucle",
      "Classe ASHRAE admise en salle et conséquence sur le free cooling",
      "Redondance, secours et comportement en défaut",
      "Performances exigées : PUE de conception, WUE, conditions de mesure",
      "Traitement d'eau, cycles de concentration et rejets"]),

    # ── Électricité ───────────────────────────────────────────────────────
    ("SPC-CFO", "Spécification technique — électricité courants forts", "elec_cfo",
     "contractuel", "moe", True,
     {"APS": "principes", "APD": "emission", "PRO": "maj", "DCE": "gel",
      "EXE-VISA": "recalage", "BASIC": "principes", "FEED": "emission",
      "EPCI": "recalage"},
     ["Bilan de puissance par tableau et par usage",
      "Architecture de distribution et niveau de redondance",
      "Alimentation sans coupure, autonomie et gestion des batteries",
      "Groupes électrogènes, réserve de combustible et essais en charge",
      "Régime de neutre, sélectivité et courants de court-circuit",
      "Comptage divisionnaire aux points de mesure du PUE"]),
    ("SPC-CFA", "Spécification technique — électricité courants faibles", "elec_cfa",
     "contractuel", "moe", False,
     {"APD": "emission", "PRO": "maj", "DCE": "gel", "EXE-VISA": "maj",
      "FEED": "emission", "EPCI": "maj"},
     ["Gestion technique du bâtiment et supervision d'infrastructure",
      "Métrologie : points de mesure, précision, acquisition et archivage",
      "Détection incendie et report d'alarmes",
      "Câblage structuré des locaux techniques et repérage",
      "Interfaces avec les systèmes de sûreté et d'exploitation"]),
    ("SPC-TEL", "Spécification technique — téléphonie et réseaux de communication",
     "telecom", "contractuel", "moe", False,
     {"APD": "emission", "PRO": "maj", "DCE": "gel", "FEED": "emission", "EPCI": "maj"},
     ["Arrivées opérateurs, cheminements séparés et redondance",
      "Téléphonie d'exploitation et postes de sécurité",
      "Couverture radio des équipes d'intervention et des secours",
      "Interphonie des sas et liaisons de sûreté",
      "Séparation stricte des réseaux d'exploitation et des réseaux clients"]),

    # ── Incendie ──────────────────────────────────────────────────────────
    ("SPC-SSI", "Spécification technique — prévention et sécurité incendie",
     "incendie", "contractuel", "moe", False,
     {"APS": "principes", "APD": "emission", "PRO": "maj", "DCE": "gel",
      "EXE-VISA": "maj", "BASIC": "principes", "FEED": "emission", "EPCI": "maj"},
     ["Classement de l'établissement et textes applicables",
      "Compartimentage, degrés coupe-feu et traversées",
      "Détection — technologie, sensibilité, zones de détection",
      "Désenfumage et mise en sécurité",
      "Accès et moyens des services de secours",
      "Scénarios de mise en sécurité et matrice cause-effet"]),
    ("SPC-EXT", "Spécification technique — systèmes d'extinction", "extinction",
     "contractuel", "moe", False,
     {"APD": "emission", "PRO": "maj", "DCE": "gel", "EXE-VISA": "maj",
      "FEED": "emission", "EPCI": "maj"},
     ["Agent retenu par local et justification du choix",
      "Concentration d'extinction, temps d'imprégnation et de maintien",
      "Étanchéité des volumes protégés et essai d'intégrité",
      "Commandes, temporisations et sécurité des personnes",
      "Réarmement, réapprovisionnement et essais périodiques"]),
    ("SPC-EAUINC", "Note de calcul des besoins en eau d'extinction", "incendie",
     "note", "moe", False,
     {"APD": "emission", "PRO": "maj", "DCE": "gel", "FEED": "emission"},
     ["Risque retenu et référentiel de calcul applicable",
      "Débit et durée exigés par le référentiel, aire de calcul",
      "Volume de la réserve et conditions de réalimentation",
      "Poteaux et bouches, pression et débit disponibles au réseau public",
      "Rétention des eaux d'extinction et convention de rejet",
      "Écart entre besoin calculé et ressource disponible sur site"]),

    # ── Sûreté ────────────────────────────────────────────────────────────
    ("SPC-SUR", "Spécification technique — sûreté et contrôle d'accès", "surete",
     "contractuel", "moe", False,
     {"APD": "emission", "PRO": "maj", "DCE": "gel", "EXE-VISA": "maj",
      "FEED": "emission", "EPCI": "maj"},
     ["Zonage de sûreté et niveaux d'habilitation",
      "Périmétrie, détection d'intrusion et délais de réaction",
      "Contrôle d'accès, sas et gestion des visiteurs",
      "Vidéoprotection : couverture, durée de conservation, base légale",
      "Poste de sûreté, main courante et procédures d'escalade",
      "Durcissement des locaux techniques sensibles"]),
    ("SPC-EVAC", "Plan d'évacuation et notice d'exploitation en sécurité",
     "incendie", "plan", "moe", False,
     {"PRO": "emission", "DCE": "maj", "AOR": "gel", "EPCI": "emission",
      "CSU": "gel"},
     ["Cheminements d'évacuation et points de rassemblement",
      "Signalétique, éclairage de sécurité et balisage",
      "Consignes par local et effectifs à évacuer",
      "Organisation des exercices et périodicité",
      "Particularité des salles sous extinction automatique"]),

    # ── IT / OT ───────────────────────────────────────────────────────────
    ("SPC-ITOT", "Liste et spécification des équipements IT / OT / SCI", "itot",
     "tableau", "moe", False,
     {"APD": "emission", "PRO": "maj", "DCE": "gel", "EXE-VISA": "recalage",
      "FEED": "emission", "EPCI": "recalage", "CSU": "as_built"},
     ["Inventaire par système : repère, fonction, criticité",
      "Séparation des domaines IT, OT et systèmes de contrôle industriel",
      "Interfaces et protocoles entre domaines, sens des flux autorisés",
      "Exigences de cybersécurité applicables par zone et conduit",
      "Cycle de vie, obsolescence et politique de mise à jour",
      "Ce qui est fourni par le maître d'ouvrage et ce qui est au marché"]),

    # ── Environnement et énergie ──────────────────────────────────────────
    ("SPC-CONSO", "Étude de consommation — énergie par consommateur, eau par poste",
     "environnement", "note", "moe", True,
     {"APD": "emission", "PRO": "maj", "DCE": "gel", "AOR": "recalage",
      "FEED": "emission", "EPCI": "maj", "CSU": "recalage"},
     ["Consommation électrique annuelle décomposée par consommateur",
      "Part informatique et part des auxiliaires, et leur évolution avec la charge",
      "Consommation d'eau totale et par poste : évaporation, purge, appoint, sanitaire",
      "Eau consommée en amont par la production électrique",
      "Profil saisonnier et pointe de prélèvement",
      "Points de comptage permettant de vérifier chaque poste après mise en service"]),
    ("SPC-CHALEUR", "Étude de chaleur fatale récupérable", "environnement",
     "note", "moe", True,
     {"APS": "principes", "APD": "emission", "PRO": "maj", "DCE": "gel",
      "BASIC": "principes", "FEED": "emission"},
     ["Gisement thermique et niveaux de température disponibles",
      "Preneurs potentiels, distance et saisonnalité de leur besoin",
      "Schémas de raccordement et relevage éventuel",
      "ERF atteignable et incidence sur le PUE",
      "Économie du projet et partage de la valeur",
      "Conditions contractuelles et durée d'engagement du preneur"]),
    ("SPC-RSE", "Étude RSE et développement durable", "environnement",
     "note", "moe", True,
     {"APS": "principes", "APD": "emission", "PRO": "maj", "DCE": "gel",
      "AOR": "recalage", "FEED": "emission", "CSU": "recalage"},
     ["Enjeux retenus et parties prenantes concernées",
      "Trajectoire énergie, eau et carbone avec ses jalons",
      "Insertion locale : emploi, nuisances, concertation",
      "Obligations de déclaration applicables et calendrier",
      "Indicateurs suivis, méthode de mesure et périodicité",
      "Ce qui est engagé et ce qui reste une intention"]),
    ("SPC-BASCARB", "Étude bâtiment bas carbone et matériaux", "environnement",
     "note", "moe", True,
     {"APD": "emission", "PRO": "maj", "DCE": "gel", "EPCI": "recalage",
      "FEED": "emission"},
     ["Carbone incorporé par lot et par matériau, amorti sur la durée de vie",
      "Comparaison des variantes constructives examinées",
      "Réemploi, matériaux biosourcés et contenu recyclé",
      "Déclarations environnementales produit exigées des fournisseurs",
      "Fin de vie, démontabilité et réversibilité du bâtiment",
      "Écart entre l'ordre de grandeur de conception et les données réelles"]),
    ("SPC-FORFAIT", "Étude globale forfaitaire et décomposition par poste",
     "projet", "tableau", "moe", True,
     {"APS": "principes", "APD": "emission", "PRO": "maj", "DCE": "gel",
      "FAISA": "principes", "BASIC": "emission", "FEED": "maj", "EPCI": "recalage"},
     ["Enveloppe globale et décomposition lot par lot",
      "Part de chaque lot et fourchette assumée",
      "Postes à renseigner localement — foncier, raccordement, instruction",
      "Coût d'exploitation annuel et coût complet sur la durée retenue",
      "Sensibilité de l'enveloppe aux hypothèses de conception",
      "IMPORTANT : la structure des lots et leurs parts sont publiées par le "
      "moteur d'enveloppe de conseilprev (module finance_dc). S'y référer et "
      "les citer — ne pas les retaper ici : deux tables qui divergent valent "
      "moins qu'une seule qu'on cite."]),
]


def _piece_discipline(entree, phase):
    """Une spécification vue depuis une phase donnée, avec le niveau attendu."""
    c, titre, disc, typ, emet, moteur, phases, contenu = entree
    niv = phases.get(phase)
    if not niv:
        return None
    t = TYPES_PIECE.get(typ) or {}
    n = NIVEAUX.get(niv) or {}
    return {
        "code": c, "titre": titre,
        "type": typ, "type_nom": t.get("nom", typ), "type_aide": t.get("aide", ""),
        "emetteur": emet, "emetteur_nom": _nom_emetteur(emet),
        "moteur": bool(moteur),
        "contenu": list(contenu),
        "discipline": disc, "discipline_nom": _nom_discipline(disc),
        "niveau": niv, "niveau_nom": n.get("nom", niv), "niveau_aide": n.get("aide", ""),
        # Où la même pièce apparaît ailleurs : sans cela, on croit avoir affaire
        # à un document neuf à chaque phase, et on en produit trois.
        "autres_phases": sorted(k for k in phases if k != phase),
    }


def pieces(code):
    """Le registre des pièces d'une phase, enrichi de ses libellés.

    Deux origines réunies ici : les pièces PROPRES à la phase et les
    spécifications de DISCIPLINE dues à cette phase, chacune avec le niveau
    attendu. On ne renvoie pas les tuples bruts : le type et l'émetteur y sont
    des clés, et une interface qui afficherait « moe » ou « contractuel »
    obligerait le lecteur à traduire ce que le module sait déjà dire.
    """
    out = []
    for c, titre, typ, emet, moteur, contenu in _PIECES.get(code, []):
        t = TYPES_PIECE.get(typ) or {}
        out.append({
            "code": c, "titre": titre,
            "type": typ, "type_nom": t.get("nom", typ), "type_aide": t.get("aide", ""),
            "emetteur": emet, "emetteur_nom": _nom_emetteur(emet),
            "moteur": bool(moteur),
            "contenu": list(contenu),
            "discipline": None, "discipline_nom": "",
            "niveau": None, "niveau_nom": "", "niveau_aide": "",
            "autres_phases": [],
        })
    for e in _PIECES_DISCIPLINE:
        p = _piece_discipline(e, code)
        if p:
            out.append(p)
    return out


def _resume_pieces(liste):
    """Le compte par type, émetteur et discipline. Dérivé, jamais écrit à la
    main : un registre s'allonge et les comptes figés se démentent au premier
    ajout."""
    par_type, par_emetteur, par_discipline = {}, {}, {}
    for p in liste:
        par_type[p["type_nom"]] = par_type.get(p["type_nom"], 0) + 1
        par_emetteur[p["emetteur_nom"]] = par_emetteur.get(p["emetteur_nom"], 0) + 1
        if p.get("discipline_nom"):
            par_discipline[p["discipline_nom"]] = par_discipline.get(p["discipline_nom"], 0) + 1
    return {
        "total": len(liste),
        "alimentees_par_le_moteur": sum(1 for p in liste if p["moteur"]),
        "propres_a_la_phase": sum(1 for p in liste if not p.get("discipline")),
        "specifications_de_discipline": sum(1 for p in liste if p.get("discipline")),
        "par_type": par_type,
        "par_emetteur": par_emetteur,
        "par_discipline": par_discipline,
    }


NOTE_REGISTRE = (
    "Ce registre relève de l'usage professionnel, pas d'un texte : la loi MOP fixe "
    "le contenu des éléments de mission, pas la nomenclature des pièces. Il se cale "
    "au marché de maîtrise d'œuvre, projet par projet. Les pièces marquées comme "
    "alimentées par le moteur héritent des grandeurs calculées ET des réserves de "
    "leur phase ; les autres relèvent d'autres disciplines et sont listées pour "
    "mémoire — sans elles, le registre laisserait croire que ce moteur couvre tout "
    "le dossier.")


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
            "renvoi": p.get("renvoi"),
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
    pcs = pieces(code)

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
        # Ce que cette phase attend d'AILLEURS. Une phase qui ne dirait pas où
        # se trouve son chiffrage laisserait croire qu'elle se boucle ici.
        "renvoi": ph.get("renvoi"),
        "sections": ph["livrable"],
        # Le plan dit ce qu'on écrit ; le registre dit ce qu'on REMET. Les
        # confondre fait livrer un rapport là où le marché attend des pièces
        # numérotées, chacune avec son émetteur.
        "pieces": pcs,
        "resume_pieces": _resume_pieces(pcs),
        "note_registre": NOTE_REGISTRE,
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


# ═══════════════════════════════════════════════════════════════════════════
#  6. LA RÉDACTION D'UNE PIÈCE
# ═══════════════════════════════════════════════════════════════════════════
# Les prompts sont construits ICI et non dans la page : ils portent la frontière
# entre ce qui est acquis et ce qui ne l'est pas, et cette frontière est calculée
# par ce module. La construire ailleurs reviendrait à demander au modèle de
# décider ce qu'il a le droit d'affirmer.

# Ce qu'un modèle peut produire, selon le type de pièce. Le dire évite la
# promesse la plus tentante et la plus fausse : NON, une IA ne dessine pas un
# plan d'exécution. Ce qu'elle rédige, c'est la SPÉCIFICATION de la pièce
# graphique — ce qu'elle doit montrer, à quelle échelle, avec quelles
# conventions —, que le projeteur exécute ensuite.
FORME_ATTENDUE = {
    "note": "une note rédigée, en paragraphes suivis, avec ses calculs et ses sources",
    "tableau": "un TABLEAU Markdown avec une ligne d'en-tête explicite et des "
               "cellules courtes, précédé d'une phrase qui dit ce qu'il compare",
    "plan": "la SPÉCIFICATION de la pièce graphique — ce qu'elle doit montrer, à "
            "quelle échelle, avec quelles conventions de représentation et quel "
            "cartouche. N'affirme jamais produire le plan lui-même : il est "
            "dessiné par un projeteur à partir de cette spécification",
    "schema": "la SPÉCIFICATION du schéma — organes à représenter, grandeurs à "
              "porter, conventions et repérage. N'affirme jamais produire le "
              "schéma lui-même",
    "contractuel": "une pièce contractuelle, en articles numérotés, rédigée pour "
                   "être opposable : chaque exigence mesurable, vérifiable et "
                   "assortie de sa méthode de contrôle",
    "procedure": "un mode opératoire en étapes numérotées, avec ses prérequis, "
                 "ses critères d'acceptation et ses points d'arrêt",
    "registre": "la TRAME du registre — colonnes, règles de tenue, périodicité "
                "et responsable —, sous forme de tableau Markdown, et non un "
                "registre pré-rempli de données inventées",
}

SYSTEM_PIECE = (
    "Tu es un ingénieur de maîtrise d'œuvre et d'ingénierie de projet chez CONSEILPREV, "
    "spécialisé dans les centres de données. Tu rédiges une PIÈCE de dossier de projet "
    "en français, destinée à être versée à un dossier qui sera relu par un bureau de "
    "contrôle, un maître d'ouvrage ou un contractant.\n\n"
    "Règles absolues :\n"
    "- Les grandeurs chiffrées te sont FOURNIES par un moteur de calcul déterministe. "
    "Tu ne les recalcules pas, tu ne les arrondis pas autrement, tu ne les contredis "
    "pas. Reprends-les telles quelles, avec leur unité et leur incertitude.\n"
    "- Une grandeur signalée « À PRODUIRE » n'est PAS acquise. Ne la présente jamais "
    "comme un résultat : cite-la comme valeur indicative, rappelle ce qui la bloque, "
    "et indique par quoi elle doit être remplacée. C'est la règle la plus importante "
    "de ce document — un chiffre provisoire présenté comme acquis traverse tout le "
    "projet sans que personne ne le remplace.\n"
    "- N'invente AUCUN fait, chiffre, nom, référence de plan ni constat propre au "
    "projet. Quand une information manque, écris « [à compléter] ».\n"
    "- Appuie-toi sur les extraits de la base de connaissance CONSEILPREV fournis en "
    "contexte, et cite les documents dont tu tires une affirmation.\n"
    "- Ne reproduis aucun texte normatif mot pour mot : reformule et cite la référence.\n"
    "- Respecte le niveau de définition de la phase. Une pièce d'avant-projet ne "
    "descend pas au détail d'exécution, et une pièce de consultation ne laisse "
    "aucune exigence non mesurable.\n"
    "- Le document est un BROUILLON de travail, à relire et valider par un ingénieur. "
    "Ne prétends pas qu'il est définitif.\n"
    "- Écris en Markdown : « ## » pour les sections, « ### » pour les sous-sections, "
    "listes à puces, et tableaux Markdown dès qu'une information est comparative ou "
    "multi-critères."
)


def piece(code_phase, code_piece):
    for p in pieces(code_phase):
        if p["code"] == code_piece:
            return p
    return None


def prompts_piece(profil, code_phase, code_piece, inputs=None):
    """(system, user, requête_de_recherche) pour rédiger une pièce.

    Renvoie None si la phase ou la pièce est inconnue — on refuse de deviner :
    un code de pièce mal orthographié doit échouer bruyamment, pas produire un
    document plausible sous un mauvais intitulé.
    """
    inputs = dict(inputs or {})
    d = dossier(profil, code_phase)
    if not d.get("connu") or not d.get("disponible"):
        return None
    pc = piece(code_phase, code_piece)
    if not pc:
        return None

    client = (inputs.get("client") or "").strip() or "[client à préciser]"
    consignes = (inputs.get("consignes") or "").strip()
    # Les choix d'identification et surtout ce qu'ils IMPLIQUENT. Transmettre la
    # seule étiquette — « colocation » — reviendrait à n'avoir rien gagné sur un
    # champ libre : c'est l'implication qui change le document.
    ctx = contexte_projet(inputs)
    ctx_par_champ = {r["champ"]: r for r in ctx["retenus"]}
    secteur = (ctx_par_champ.get("secteur") or {}).get("nom") or "[segment à préciser]"
    perimetre = (ctx_par_champ.get("perimetre") or {}).get("nom") or "[périmètre à préciser]"

    u = []
    A = u.append
    A("Rédige la pièce suivante, en français, au format Markdown.\n")
    A("PIÈCE — %s : %s" % (pc["code"], pc["titre"]))
    A("Type de pièce : %s (%s)" % (pc["type_nom"], pc["type_aide"]))
    A("Émetteur de la pièce : %s" % pc["emetteur_nom"])
    if pc.get("discipline_nom"):
        A("Discipline : %s" % pc["discipline_nom"])
    if pc.get("niveau_nom"):
        # Le NIVEAU commande la profondeur. Sans lui, le modèle écrit la même
        # chose à l'esquisse et à la consultation : trop détaillé d'un côté,
        # pas opposable de l'autre.
        A("Niveau attendu à CETTE phase : %s — %s"
          % (pc["niveau_nom"], pc["niveau_aide"]))
        if pc["niveau"] == "gel":
            A("Cette pièce devient OPPOSABLE à cette phase. Chaque exigence doit "
              "être mesurable, assortie de sa méthode de contrôle et de son "
              "critère d'acceptation. Une exigence qualitative (« de bonne "
              "qualité », « performant ») n'a pas sa place ici.")
        elif pc["niveau"] == "principes":
            A("À ce stade, on n'attend QUE le parti retenu et les exigences de "
              "niveau. Ne descends pas au dimensionnement : un détail donné trop "
              "tôt se fige et coûte une reprise.")
        elif pc["niveau"] in ("recalage", "as_built"):
            A("Cette version se recale sur les données RÉELLES des équipements "
              "retenus. Là où tu ne disposes que de valeurs de conception, dis-le "
              "explicitement et signale ce qui reste à recaler.")
    if pc.get("autres_phases"):
        A("Document unique, repris à d'autres phases (%s) : c'est un INDICE de "
          "la même pièce, pas un document neuf. Rappelle en tête l'indice et la "
          "phase d'émission." % ", ".join(pc["autres_phases"]))
    if pc["emetteur"] not in ("moe", "mo"):
        # Une pièce que la maîtrise d'œuvre ne produit pas mais reçoit : la
        # rédiger comme si on l'avait produite déplacerait une responsabilité.
        A("ATTENTION — cette pièce n'est pas produite par la maîtrise d'œuvre mais "
          "par %s. Rédige donc la SPÉCIFICATION de ce qui est attendu de cet "
          "émetteur : contenu exigé, format, critères d'acceptation et délai. "
          "N'écris pas le document à sa place." % pc["emetteur_nom"])
    A("Forme attendue : %s." % FORME_ATTENDUE.get(pc["type"], "une note rédigée"))
    A("")
    A("PHASE — %s (%s), filière %s" % (d["code"], d["nom"], d["filiere_nom"]))
    A("Objet de la phase : %s" % d["objet"])
    A("Ce que la phase décide : %s" % d["decide"])
    A("Ce qu'elle verrouille : %s" % d["verrouille"])
    A("Niveau de précision attendu : %s (%s ; %s)"
      % (d["precision"]["valeur"], d["precision"]["nature"], d["precision"]["aace"]))
    A("")
    A("PROJET — client : %s · segment : %s · périmètre : %s"
      % (client, secteur, perimetre))
    if ctx["retenus"]:
        A("")
        A("CE QUE LE CONTEXTE DU PROJET IMPOSE — à prendre en compte dans la "
          "rédaction, chaque point vient d'un choix explicite du lecteur :")
        for r in ctx["retenus"]:
            A("- %s (%s) — %s" % (r["label"], r["nom"], r["implique"]))
    if ctx["mop_obligatoire"] and d["filiere"] == "moe":
        # La conséquence la plus lourde, répétée ici : en commande publique la
        # séquence n'est plus un usage, et une pièce rédigée comme en privé
        # expose le maître d'ouvrage.
        A("")
        A("RAPPEL IMPÉRATIF — la maîtrise d'ouvrage est publique : le contenu de "
          "cet élément de mission est fixé par décret et n'est pas négociable. "
          "Ne présente aucune de ses composantes comme optionnelle ou comme "
          "relevant d'un usage.")
    if ctx["inconnus"]:
        A("")
        A("Valeurs d'identification non reconnues, à ignorer plutôt qu'à "
          "interpréter : %s"
          % ", ".join("%s = %s" % (x["champ"], x["valeur"]) for x in ctx["inconnus"]))
    if consignes:
        A("")
        A("Consignes particulières : %s" % consignes)
    A("")

    if pc["moteur"]:
        A("GRANDEURS CALCULÉES — elles viennent du moteur déterministe. Reprends-les "
          "telles quelles.")
        A("")
        for g in d["grandeurs"]:
            marque = "RECEVABLE À CE STADE" if g["statut"] == "recevable" else "À PRODUIRE"
            ligne = "- %s : %s %s [%s]" % (g["nom"], D.fr(g["valeur"]), g["unite"], marque)
            if g.get("incertitude"):
                ligne += " — incertitude : %s" % g["incertitude"]
            if g["statut"] != "recevable":
                ligne += " — BLOQUÉE PAR : %s" % ", ".join(g["postes_bloquants"])
            A(ligne)
        A("")
        subs = d["aptitude"]["substitutions_a_faire"]
        if subs:
            A("FACTEURS À REMPLACER avant de franchir cette phase — à mentionner "
              "explicitement dans la pièce, avec leur consigne de remplacement :")
            A("")
            for s in subs:
                A("- %s (%s%s). Pourquoi à ce stade : %s À remplacer par : %s"
                  % (s["nom"], s["nature"],
                     ", " + s["incertitude"] if s["incertitude"] else "",
                     s["devient_insuffisant"], s["remplacer_par"]))
            A("")
        manques = d["aptitude"]["entrees_manquantes"]
        if manques:
            A("DONNÉES DE PROJET NON RENSEIGNÉES — écris « [à compléter] » là où "
              "elles seraient nécessaires, et ne les invente pas : %s"
              % ", ".join(m["label"] for m in manques))
            A("")
    else:
        A("Cette pièce n'est PAS alimentée par le moteur de calcul énergie / eau / "
          "carbone : elle relève d'une autre discipline. N'y reporte aucune grandeur "
          "chiffrée de performance environnementale sans l'avoir reçue explicitement ; "
          "renvoie plutôt aux pièces qui les portent.")
        A("")

    A("CONTENU EXIGÉ — développe chacun de ces points, dans cet ordre :")
    for c in pc["contenu"]:
        A("- %s" % c)
    A("")
    A("Commence par un titre « # %s — %s » suivi d'une ligne de métadonnées "
      "(phase, émetteur, client, mention « Brouillon — à valider »). Termine par une "
      "note rappelant que la pièce est un brouillon produit avec l'aide de l'IA à "
      "partir d'un calcul déterministe, à relire et valider par un ingénieur."
      % (pc["code"], pc["titre"]))

    requete = " ".join([pc["titre"], d["nom"], d["filiere_nom"], "centre de données",
                        secteur, perimetre, consignes]).strip()
    return SYSTEM_PIECE, "\n".join(u), requete


# ═══════════════════════════════════════════════════════════════════════════
#  7. LE GLOSSAIRE
# ═══════════════════════════════════════════════════════════════════════════
# Cette page est dense en vocabulaire de métier : ESQ, APD, DCE, FEED, EPCI,
# gel contractuel, classe 3, accord partiel. Chacun de ces mots est exact, et
# aucun n'est explicite pour qui ne l'a pas déjà pratiqué. Une page qui les
# aligne sans les expliquer ne s'adresse qu'à ceux qui n'en avaient pas besoin.
#
# Le glossaire est SERVI, pas écrit dans la page : les mêmes définitions
# alimentent l'infobulle et, le jour venu, une aide en ligne ou un export.
# Recopier une définition dans le HTML en ferait une seconde, qui divergerait.
#
# Une famille par type d'étiquette, une clé par valeur — la page n'a qu'un
# attribut à poser (data-info="famille:clé") et une seule fonction de recherche.
# C'est ce qui permet d'en couvrir douze sortes sans douze mécanismes.

ACCORDS = {
    "franc": {"nom": "Accord franc",
              "aide": "Les deux phases tranchent la même question, au même moment "
                      "du projet."},
    "proche": {"nom": "Accord proche",
               "aide": "Même objet, périmètres voisins. Les livrables se recouvrent "
                       "largement, mais pas les régimes juridiques."},
    "partiel": {"nom": "Accord partiel",
                "aide": "Les phases se recouvrent sur une partie du contenu "
                        "seulement. Franchir l'une laisse ouvert ce que l'autre "
                        "traite en propre : c'est là que les dossiers se croient "
                        "complets sans l'être."},
    "faible": {"nom": "Accord faible",
               "aide": "Même position dans la séquence, logiques différentes. La "
                       "responsabilité de conception n'est pas au même endroit, et "
                       "confondre les deux se paie en avenants."},
}

STATUTS_GRANDEUR = {
    "recevable": {"nom": "Recevable à ce stade",
                  "aide": "Le niveau de définition de cette valeur correspond à ce "
                          "que la phase attend. Cela ne dit pas qu'elle est juste : "
                          "cela dit qu'elle est admissible ici."},
    "a_remplacer": {"nom": "À produire",
                    "aide": "La valeur affichée est indicative. Un poste du "
                            "référentiel qu'elle utilise n'a plus le niveau de "
                            "définition exigé par cette phase : il faut une donnée "
                            "réelle avant de la porter au dossier."},
}

CLASSES_AACE = {
    "Classe 5": {"nom": "Classe 5", "aide": "Estimation de cadrage : 0 à 2 % du "
                 "projet défini. Fourchette typique de −50 % à +100 %."},
    "Classe 4": {"nom": "Classe 4", "aide": "Faisabilité aboutie : 1 à 15 % défini. "
                 "Fourchette typique de −30 % à +50 %."},
    "Classe 3": {"nom": "Classe 3", "aide": "Base d'une décision d'investissement : "
                 "10 à 40 % défini. Fourchette typique de −20 % à +30 %."},
    "Classe 2": {"nom": "Classe 2", "aide": "Base d'une offre ferme : 30 à 70 % "
                 "défini. Fourchette typique de −15 % à +20 %."},
    "Classe 1": {"nom": "Classe 1", "aide": "Estimation de contrôle : 50 à 100 % "
                 "défini. Fourchette typique de −10 % à +15 %."},
}

NATURES_PRECISION = {
    "usage": {"nom": "Usage professionnel",
              "aide": "Pratique de place, pas règle de droit. Le décret impose au "
                      "maître d'œuvre de s'engager sur un coût prévisionnel ; il "
                      "n'en fixe pas le pourcentage, arrêté au contrat."},
    "referentiel_externe": {"nom": "Référentiel externe",
                            "aide": "Fourchette publiée par une organisation tierce "
                                    "— ici l'AACE — donnée comme TYPIQUE et variable "
                                    "selon l'industrie. Elle cadre un ordre de "
                                    "grandeur ; elle ne remplace pas une précision "
                                    "établie projet par projet."},
    "analyse": {"nom": "Analyse",
                "aide": "Position d'ingénieur, tenue par le raisonnement exposé à "
                        "côté. Elle se discute — et c'est pour cela qu'elle est "
                        "signalée comme telle plutôt que présentée en norme."},
}

MOTEUR_BADGE = {
    "oui": {"nom": "Alimentée par le calcul",
            "aide": "Cette pièce reçoit les grandeurs du moteur énergie / eau / "
                    "carbone ET les réserves de sa phase : ce qui est acquis, ce qui "
                    "reste à produire, et par quoi le remplacer."},
    "non": {"nom": "Hors calcul",
            "aide": "Cette pièce relève d'une autre discipline. Elle figure au "
                    "registre pour mémoire — sans elle, le registre laisserait "
                    "croire que ce moteur couvre tout le dossier."},
}


_NATURE_POSTE = {
    "ordre_grandeur": "Ordre de grandeur : la valeur situe, elle ne mesure pas.",
    "moyenne_annuelle": "Moyenne annuelle : elle lisse le profil horaire.",
    "physique": "Constante physique : elle ne dépend d'aucun choix de projet.",
    "plage_de_conception": "Plage de conception : elle décrit une famille "
                           "d'installations, pas une machine.",
}


def _aide_poste(v):
    """L'explication d'un poste du référentiel.

    Elle commence par ce que le poste EST — sa nature, son incertitude —, car
    tous les postes en ont une, puis ajoute quand il cesse de suffire et par
    quoi le remplacer, pour ceux à qui cela s'applique. Une constante physique
    ne se remplace pas et ne devient pas insuffisante : elle le dit, au lieu
    de rendre une infobulle vide qui n'apprend rien de plus que l'étiquette
    déjà lisible à l'écran.
    """
    bouts = []
    nat = _NATURE_POSTE.get(v.get("nature"))
    inc = v.get("incertitude")
    tete = nat or ""
    if inc:
        tete = (tete + " Incertitude déclarée : %s." % inc).strip()
    elif v.get("incertitude_absente"):
        tete = (tete + " Aucune incertitude n'est déclarée au référentiel — "
                       "absente ne veut pas dire nulle.").strip()
    if tete:
        bouts.append(tete)
    if v.get("devient_insuffisant"):
        bouts.append("Quand il ne suffit plus : " + v["devient_insuffisant"])
    if v.get("remplacer_par"):
        bouts.append("À remplacer par : " + v["remplacer_par"])
    elif not v.get("devient_insuffisant"):
        bouts.append("Rien ne vient la remplacer en cours de projet : elle "
                     "borne le résultat quelle que soit la phase.")
    return "\n\n".join(bouts)


def glossaire():
    """Toutes les familles d'étiquettes de la page, avec leur explication.

    Les familles qui existaient déjà — types de pièce, niveaux, apport du
    moteur, postes du référentiel — sont REPRISES ici et non recopiées : une
    définition dupliquée est une définition qui divergera.
    """
    return {
        "phase": {p["code"]: {
            "nom": "%s — %s" % (p["code"], p["nom"]),
            "aide": "%s\n\nCe qu'elle décide : %s\nCe qu'elle verrouille : %s"
                    % (p["objet"], p["decide"], p["verrouille"]),
        } for p in PHASES},
        "filiere": {k: {"nom": v["nom"], "aide": v["portee"] + " " + v["note"]}
                    for k, v in FILIERES.items()},
        "emetteur": EMETTEURS,
        "type_piece": TYPES_PIECE,
        "niveau": NIVEAUX,
        "discipline": DISCIPLINES,
        "apport": {k: {"nom": k.replace("_", " "), "aide": v}
                   for k, v in APPORT.items()},
        "accord": ACCORDS,
        "statut": STATUTS_GRANDEUR,
        "aace": CLASSES_AACE,
        "nature": NATURES_PRECISION,
        "moteur": MOTEUR_BADGE,
        "poste": {k: {"nom": v["nom"], "aide": _aide_poste(v)}
                  for k, v in POSTES.items()},
    }


def referentiel():
    """Le cadre complet, pour l'interface et la documentation."""
    return {
        "version": VERSION,
        "filieres": FILIERES,
        "phases": PHASES,
        "correspondances": CORRESPONDANCES,
        "postes": POSTES,
        "apport": APPORT,
        # Le registre complet, toutes phases : une interface qui ne verrait que
        # la phase affichée ne permettrait pas de préparer un plan de production
        # documentaire, qui est justement ce qu'on regarde en début de projet.
        "types_piece": TYPES_PIECE,
        "emetteurs": EMETTEURS,
        # Les listes d'identification, servies au lieu d'être écrites dans la
        # page : une option recopiée dans le HTML finit par proposer un choix
        # que le module ne sait plus interpréter.
        "identification": [
            {"id": c["id"], "label": c["label"], "aide": c["aide"],
             "options": [{"cle": k, "nom": v["nom"], "implique": v["implique"]}
                         for k, v in c["options"].items()]}
            for c in IDENTIFICATION],
        "identification_note": IDENTIFICATION_NOTE,
        "formes_attendues": FORME_ATTENDUE,
        "pieces": {p["code"]: pieces(p["code"]) for p in PHASES},
        "note_registre": NOTE_REGISTRE,
        # Le glossaire, servi avec le cadre : une page dense en sigles qui ne
        # les explique pas ne s'adresse qu'à ceux qui n'en avaient pas besoin.
        "glossaire": glossaire(),
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
    # Le registre : chaque phase doit en avoir un, les codes doivent être
    # uniques d'un bout à l'autre — un code réutilisé casse la traçabilité au
    # moment même où elle sert — et les types et émetteurs doivent exister.
    tous = [x for p_ in PHASES for x in pieces(p_["code"])]
    # Un code identifie UNE pièce. Une spécification de discipline revient à
    # plusieurs phases sous le même code — c'est voulu, c'est le même document
    # à un autre indice. On vérifie donc l'unicité PAR PHASE, et la cohérence
    # d'intitulé d'une phase à l'autre : deux titres différents sous un même
    # code feraient croire à deux documents.
    doublons, titres = [], {}
    for p_ in PHASES:
        vus = [x["code"] for x in pieces(p_["code"])]
        doublons += sorted({p_["code"] + "/" + c for c in vus if vus.count(c) > 1})
    for x in tous:
        titres.setdefault(x["code"], set()).add(x["titre"])
    titres_incoherents = sorted(c for c, t in titres.items() if len(t) > 1)

    sans_registre = [p_["code"] for p_ in PHASES if not pieces(p_["code"])]
    types_inconnus = sorted({x["type"] for x in tous if x["type"] not in TYPES_PIECE})
    emet_inconnus = sorted({x["emetteur"] for x in tous if x["emetteur"] not in EMETTEURS})
    sans_contenu = [x["code"] for x in tous if not x["contenu"]]
    disc_inconnues = sorted({x["discipline"] for x in tous
                             if x.get("discipline") and x["discipline"] not in DISCIPLINES})
    niv_inconnus = sorted({x["niveau"] for x in tous
                           if x.get("niveau") and x["niveau"] not in NIVEAUX})
    # Une spécification déclarée sur une phase qui n'existe pas ne s'afficherait
    # jamais : la faute est silencieuse, donc elle se contrôle.
    connues = {p_["code"] for p_ in PHASES}
    phases_fantomes = sorted({ph for e in _PIECES_DISCIPLINE for ph in e[6]
                              if ph not in connues})

    # Le glossaire : une entrée sans explication produit une infobulle qui
    # répète l'étiquette déjà lisible à l'écran — un survol pour rien. Le cas
    # s'est produit sur douze disciplines et sur un poste dont, à juste titre,
    # rien ne devient insuffisant. Contrôlé ici pour ne pas revenir.
    g_ = glossaire()
    glossaire_muet = sorted(
        "%s:%s" % (fam, cle)
        for fam, entrees in g_.items()
        for cle, e in entrees.items()
        if not (e or {}).get("aide", "").strip() or not (e or {}).get("nom", "").strip())

    p = {"puissance_it_kw": 2000}
    return {
        "version": VERSION,
        "phases": len(PHASES),
        "moe": sum(1 for x in PHASES if x["filiere"] == "moe"),
        "indus": sum(1 for x in PHASES if x["filiere"] == "indus"),
        "champs_exiges_inconnus": inconnus,
        "postes_inconnus": postes_inconnus,
        "regressions_d_exigence": regressions,
        "pieces_occurrences": len(tous),
        "pieces_distinctes": len(titres),
        "specifications_de_discipline": len(_PIECES_DISCIPLINE),
        "pieces_alimentees_moteur": sum(1 for x in tous if x["moteur"]),
        "pieces_codes_doublons": doublons,
        "pieces_titres_incoherents": titres_incoherents,
        "phases_sans_registre": sans_registre,
        "pieces_types_inconnus": types_inconnus,
        "pieces_emetteurs_inconnus": emet_inconnus,
        "pieces_sans_contenu": sans_contenu,
        "disciplines_inconnues": disc_inconnues,
        "niveaux_inconnus": niv_inconnus,
        "specifications_sur_phase_inexistante": phases_fantomes,
        "glossaire_familles": len(g_),
        "glossaire_definitions": sum(len(v) for v in g_.values()),
        "glossaire_sans_explication": glossaire_muet,
        "franchissables_profil_minimal": [
            e["code"] for e in parcours(p, "moe")["etapes"] if e["franchissable"]
        ] + [
            e["code"] for e in parcours(p, "indus")["etapes"] if e["franchissable"]
        ],
        "moteur": D.VERSION,
    }
