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

import functools
import re
import time

import datacenter as D
import extraits as _X
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

# ── À QUEL TITRE NOUS RÉDIGEONS ────────────────────────────────────────────
# LA DIMENSION QUI MANQUAIT, ET CE QU'ELLE COÛTAIT. Les trois listes ci-dessus
# disent QUI PORTE le projet, CE QU'IL HÉBERGE et CE QUI EST AU MARCHÉ. Aucune
# ne disait à quel titre NOUS intervenons — et faute de la poser, la réponse
# était donnée quand même : le rédacteur écrit « en ingénieur de maîtrise
# d'œuvre », toujours, y compris quand le cabinet est mandaté en assistance à
# maîtrise d'ouvrage ou en revue d'une conception qui n'est pas la sienne.
#
# CE N'EST PAS UNE NUANCE DE VOCABULAIRE, C'EST UN ENGAGEMENT. Le registre des
# pièces le dit déjà à sa manière : la maîtrise d'œuvre PRESCRIT et VISE, elle
# ne rédige pas à la place de l'entreprise. Une note écrite au nom de la
# maîtrise d'œuvre alors que la mission est une AMO prescrit donc au nom d'un
# rôle que le contrat ne nous confie pas — et si le dossier part ainsi, c'est
# une responsabilité de conception que personne n'a vendue ni assurée.
#
# La mission ne change AUCUN calcul : elle change la personne qui parle, ce
# qu'elle peut affirmer, et ce qu'elle doit renvoyer à quelqu'un d'autre.
MISSIONS = {
    "moe": {
        "nom": "Maîtrise d'œuvre — conception et suivi de réalisation",
        "implique": "Nous concevons, prescrivons et contrôlons. La pièce est "
                    "PRESCRIPTIVE : elle fixe des exigences opposables à "
                    "l'entreprise et engage notre responsabilité de concepteur. "
                    "Elle ne rédige jamais à la place de l'entreprise — les "
                    "études d'exécution et les plans d'atelier restent les "
                    "siens, et nous les visons.",
    },
    "moe_conception": {
        "nom": "Maîtrise d'œuvre de conception seule — jusqu'au dossier de consultation",
        "implique": "Même posture prescriptive, mais la mission s'arrête à la "
                    "consultation : la pièce ne peut renvoyer à aucun acte de "
                    "suivi de chantier que nous n'assurerons pas — visa, "
                    "direction de l'exécution, réception. Ce qui relève de ces "
                    "phases doit être désigné comme À CONFIER, et non décrit "
                    "comme si nous devions le faire.",
    },
    "amo": {
        "nom": "Assistance à maîtrise d'ouvrage",
        "implique": "Nous sommes du côté du maître d'ouvrage et NE CONCEVONS "
                    "PAS. La pièce est un avis, une exigence de programme ou un "
                    "contrôle de ce qu'un tiers a produit — jamais une "
                    "prescription technique signée de notre main. Elle formule "
                    "ce que le maître d'ouvrage doit EXIGER, et laisse à la "
                    "maîtrise d'œuvre le comment.",
    },
    "bet": {
        "nom": "Bureau d'études spécialisé, dans la maîtrise d'œuvre d'un tiers",
        "implique": "Nous n'intervenons que sur notre discipline, à l'intérieur "
                    "d'une maîtrise d'œuvre que nous ne dirigeons pas. La pièce "
                    "doit nommer ses INTERFACES et dire explicitement ce "
                    "qu'elle NE couvre PAS : un silence sur une interface se lit "
                    "comme une prise en charge, et se découvre au montage.",
    },
    "epc": {
        "nom": "Ingénierie intégrée au contractant EPC",
        "implique": "La conception est dans le contrat de construction : la "
                    "pièce est INTERNE au contractant et n'est pas opposable à "
                    "lui-même. Ce qui est opposable, c'est l'engagement de "
                    "performance pris devant le maître d'ouvrage — la pièce doit "
                    "distinguer les deux, sans quoi une exigence interne se "
                    "retrouve citée comme un engagement contractuel.",
    },
    "audit": {
        "nom": "Audit ou revue technique d'une conception établie par un tiers",
        "implique": "Nous CONSTATONS, nous ne concevons pas. La pièce énonce des "
                    "écarts, leur criticité et ce qu'ils appellent — elle ne "
                    "réécrit pas la conception auditée et ne propose pas de "
                    "solution chiffrée qui nous en rendrait comptables. Chaque "
                    "constat cite la pièce examinée et son indice.",
    },
}

# LA MISSION PAR DÉFAUT, ÉCRITE PLUTÔT QUE SUBIE. Sans choix explicite, la
# rédaction reste celle de la maîtrise d'œuvre — c'est le cas le plus fréquent
# et c'était déjà le comportement. La différence est qu'il est maintenant NOMMÉ
# ici, et ANNONCÉ dans la pièce produite : une posture qu'on ne peut pas lire
# est une posture qu'on ne peut pas contester.
MISSION_DEFAUT = "moe"


def mission(inputs):
    """La mission retenue, et si elle a été CHOISIE ou seulement supposée."""
    cle = str((inputs or {}).get("mission") or "").strip()
    o = MISSIONS.get(cle)
    if o:
        return {"cle": cle, "nom": o["nom"], "implique": o["implique"],
                "choisie": True}
    d = MISSIONS[MISSION_DEFAUT]
    return {"cle": MISSION_DEFAUT, "nom": d["nom"], "implique": d["implique"],
            "choisie": False,
            "reserve": "La mission n'a pas été précisée : la pièce est rédigée "
                       "en maîtrise d'œuvre, posture par défaut. Si le cabinet "
                       "intervient en assistance à maîtrise d'ouvrage, en "
                       "cotraitance ou en revue, ce choix doit être corrigé "
                       "avant diffusion — il commande ce que la pièce engage."}


IDENTIFICATION = [
    {"id": "mission", "label": "À quel titre nous intervenons",
     "aide": "Notre rôle dans l'opération — cela ne change aucun calcul, mais "
             "cela change ce que la pièce peut prescrire et ce qu'elle engage.",
     "options": MISSIONS},
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
    "design_mgmt": {
        "nom": "Management du design et synthèse technique",
        "aide": "La coordination des études entre l'architecture, la structure "
                "et les lots techniques : exigences du client tenues, interfaces "
                "arbitrées, plans compatibles entre spécialités, production "
                "graphique cadrée, offres fournisseurs analysées, coûts agrégés.\n"
                "Elle ne produit aucune grandeur, mais c'est elle qui rend le "
                "calcul opposable : un PUE tenu par le lot CVC et démenti par le "
                "bilan de puissance du lot CFO n'est pas une valeur, c'est un "
                "écart d'interface que personne n'a relevé.",
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
    # ── Deux disciplines qui manquaient au registre ────────────────────────
    # Elles étaient traitées en passant — la supervision au titre du câblage
    # courants faibles, les réseaux de fluides au titre du froid. Aucune des
    # deux n'y tient : la première produit les MESURES sur lesquelles reposent
    # les indicateurs contractuels, la seconde porte des ouvrages enterrés
    # qu'on ne reprend pas après coulage.
    "supervision": {
        "nom": "Supervision technique, GTB/GTC et DCIM",
        "aide": "Gestion technique du bâtiment, supervision des installations, "
                "DCIM, comptage et sous-comptage, métrologie, alarmes et "
                "conduite.\nC'est elle qui FABRIQUE LA PREUVE : un PUE ou un "
                "WUE engagé au marché n'est démontrable que par les compteurs "
                "posés, leur classe de précision et leur emplacement. Une "
                "performance contractuelle sans plan de comptage est une "
                "clause invérifiable — donc inopposable.",
    },
    "fluides": {
        "nom": "Réseaux techniques et fluides",
        "aide": "Eau glacée, eau d'appoint et de purge, eau d'extinction, eau "
                "potable, eaux usées et pluviales, air comprimé, fioul, "
                "fourreaux et cheminements enterrés.\nElle porte les ouvrages "
                "qu'on ne reprend pas : un réseau enterré mal calé, une vanne "
                "d'isolement manquante ou un maillage absent transforment une "
                "redondance de production en point unique de défaillance, en "
                "aval de tout ce que les autres disciplines ont doublé.",
    },
}


def _nom_discipline(cle):
    d = DISCIPLINES.get(cle)
    return (d or {}).get("nom", cle) if isinstance(d, dict) else (d or cle)


# ═══════════════════════════════════════════════════════════════════════════
#  LE NIVEAU DE DISPONIBILITÉ, ET CE QU'IL COÛTE EN MATÉRIEL
# ═══════════════════════════════════════════════════════════════════════════
# POURQUOI ICI. Le moteur d'enveloppe de conseilprev (finance_dc) désigne la
# redondance comme le PREMIER multiplicateur de coût des lots électricité et
# froid — « passer de N+1 à 2N double des chaînes entières » — et laisse la
# question ouverte, à juste titre : il chiffre, il ne conçoit pas. C'est ici
# qu'elle se répond, parce que c'est une décision d'ingénierie.
#
# TROIS VOCABULAIRES QUE L'USAGE CONFOND, et qui ne disent pas la même chose :
#
#   · Le Tier de l'Uptime Institute qualifie une TOPOLOGIE d'installation. Il
#     ne certifie ni l'exploitation ni le résultat : un Tier IV mal exploité
#     tombe, et l'organisme distingue lui-même la certification de la
#     conception de celle de l'installation construite.
#
#   · La classe de disponibilité de l'EN 50600-1 est une norme européenne,
#     d'esprit voisin mais d'échelle propre. Les deux ne se traduisent pas
#     l'une dans l'autre — écrire « Tier III = classe 3 » est une facilité de
#     rédaction qui ne résiste pas à une revue.
#
#   · N, N+1, 2N décrivent un SCHÉMA DE REDONDANCE d'équipements. C'est une
#     définition arithmétique, pas un référentiel : elle se calcule.
#
# Ce que le module fait : il CALCULE le nombre d'unités installées et la marge
# qui en résulte. Ce qu'il ne fait pas : décerner un Tier. Un niveau se
# constate sur un dossier complet, par un tiers, jamais par un formulaire.

NIVEAUX_TIER = {
    "I": {
        "nom": "Tier I — capacité de base",
        "nature": "referentiel_externe",
        "chemins": "Un seul chemin de distribution, sans redondance.",
        "maintenance": "Toute intervention sur le chemin arrête l'informatique.",
        "defaut": "Toute panne d'un composant du chemin arrête l'informatique.",
        "consequence": "Aucune redondance exigée sur les chaînes de puissance "
                       "et de froid.",
        "schema_type": "N",
    },
    "II": {
        "nom": "Tier II — composants de capacité redondants",
        "nature": "referentiel_externe",
        "chemins": "Un seul chemin de distribution, composants redondants.",
        "maintenance": "L'arrêt du chemin reste nécessaire pour l'entretenir.",
        "defaut": "La panne d'un composant redondé est absorbée ; celle du "
                  "chemin ne l'est pas.",
        "consequence": "Redondance N+1 sur les composants, chemin unique.",
        "schema_type": "N+1",
    },
    "III": {
        "nom": "Tier III — maintenable sans interruption",
        "nature": "referentiel_externe",
        "chemins": "Plusieurs chemins de distribution, un seul actif.",
        "maintenance": "Tout composant et tout chemin s'entretient sans arrêter "
                       "l'informatique — c'est la définition même du niveau.",
        "defaut": "Un défaut non planifié peut encore provoquer une "
                  "interruption : maintenable n'est pas tolérant à la panne.",
        "consequence": "Redondance N+1 au minimum ET double chemin dont un "
                       "actif. Les deux, pas l'un des deux.",
        "schema_type": "N+1",
    },
    "IV": {
        "nom": "Tier IV — tolérant à la panne",
        "nature": "referentiel_externe",
        "chemins": "Plusieurs chemins de distribution actifs simultanément.",
        "maintenance": "Entretien sans interruption, comme le Tier III.",
        "defaut": "Un défaut unique, quel qu'il soit, est absorbé sans "
                  "interruption ; le compartimentage isole les chaînes.",
        "consequence": "Redondance 2N ou 2(N+1) et séparation physique des "
                       "chaînes — deux locaux, deux cheminements, deux sources.",
        "schema_type": "2N",
    },
}
# Le sous-titre du référentiel est nommé entre guillemets plutôt que
# introduit par deux-points : la ponctuation anglaise du titre original
# jurerait dans une phrase française, et le citer ainsi évite d'avoir à
# choisir entre une faute de typographie et une citation altérée.
TIER_SOURCE = ("Uptime Institute, référentiel Tier Standard « Topology » — les quatre niveaux "
               "qualifient la TOPOLOGIE de l'installation. Le niveau réel se "
               "constate sur dossier par l'organisme, jamais par un calcul : ce "
               "module dit ce qu'un niveau EXIGE, il ne le décerne pas.")

CLASSES_EN50600 = {
    "1": {"nom": "Classe 1 — sans redondance",
          "aide": "Aucune exigence de continuité ; l'interruption est admise."},
    "2": {"nom": "Classe 2 — redondance simple",
          "aide": "Composants redondants, chemin de distribution unique."},
    "3": {"nom": "Classe 3 — maintenable sans interruption",
          "aide": "L'entretien programmé ne coupe pas le service."},
    "4": {"nom": "Classe 4 — tolérant aux défauts",
          "aide": "Un défaut unique ne coupe pas le service."},
}
EN50600_SOURCE = ("EN 50600-1, classes de disponibilité 1 à 4. Norme européenne "
                  "d'esprit voisin du Tier, d'échelle PROPRE : les deux ne se "
                  "traduisent pas l'une dans l'autre, et « Tier III = classe 3 » "
                  "est une facilité qui ne résiste pas à une revue.")

# Le schéma de redondance : une DÉFINITION arithmétique, donc calculable.
# `sup` est le nombre d'unités ajoutées au besoin, `chaines` le nombre de
# chaînes complètes installées.
REDONDANCES = {
    "N": {"nom": "N — sans réserve", "sup": 0, "chaines": 1, "rang": 1,
          "aide": "Le strict besoin. La perte d'une unité réduit la capacité."},
    "N+1": {"nom": "N+1 — une unité de réserve", "sup": 1, "chaines": 1, "rang": 2,
            "aide": "Une unité de secours pour l'ensemble. Absorbe une panne "
                    "OU un entretien, pas les deux à la fois."},
    "N+2": {"nom": "N+2 — deux unités de réserve", "sup": 2, "chaines": 1, "rang": 3,
            "aide": "Absorbe un entretien programmé ET une panne simultanée."},
    "2N": {"nom": "2N — deux chaînes complètes", "sup": 0, "chaines": 2, "rang": 4,
           "aide": "Deux ensembles indépendants dimensionnés chacun pour la "
                   "totalité du besoin."},
    "2(N+1)": {"nom": "2(N+1) — deux chaînes, chacune avec réserve",
               "sup": 1, "chaines": 2, "rang": 5,
               "aide": "Deux chaînes complètes portant chacune une unité de "
                       "réserve. Le niveau le plus élevé couramment posé."},
}


def redondance(schema, n_besoin):
    """Combien d'unités installer, et quelle marge en résulte.

    Une arithmétique délibérément explicite : c'est le genre de compte qu'on
    croit évident et qu'on rate en réunion. Pour six groupes froid nécessaires,
    2(N+1) en installe QUATORZE — deux chaînes de sept — ni douze, ni sept. Le
    surdimensionnement qui en découle n'est pas un défaut, c'est le prix du
    niveau ; l'afficher évite qu'il soit découvert au chiffrage.

    `n_besoin` est le nombre d'unités que la charge exige, réserve exclue.
    """
    r = REDONDANCES.get(schema)
    try:
        n = int(n_besoin)
    except (TypeError, ValueError):
        n = 0
    if not r or n < 1:
        return None
    par_chaine = n + r["sup"]
    installees = par_chaine * r["chaines"]
    return {
        "schema": schema, "nom": r["nom"], "aide": r["aide"],
        "besoin": n,
        "par_chaine": par_chaine,
        "chaines": r["chaines"],
        "installees": installees,
        # La marge est la capacité installée rapportée au besoin, moins un.
        # Exprimée en pourcentage, elle se compare d'un schéma à l'autre.
        "marge_pct": round((installees / float(n) - 1.0) * 100.0, 1),
        "nature": "calcule",
        # Combien d'unités peuvent tomber sans perdre la charge.
        "perte_admissible": (r["sup"] + par_chaine) if r["chaines"] > 1 else r["sup"],
        "note": ("Le compte porte sur les UNITÉS, pas sur la puissance : deux "
                 "groupes de 1 MW ne remplacent pas un groupe de 2 MW dès que "
                 "la charge minimale de fonctionnement entre en jeu."),
    }


def disponibilite(tier=None, n_besoin=None, schema=None):
    """Le dossier de disponibilité : ce qu'un niveau exige, et ce qu'il installe.

    Rend TROIS choses distinctes, et les tient séparées à dessein — les
    confondre est l'erreur la plus fréquente sur ce sujet : ce que le
    référentiel externe EXIGE (nature `referentiel_externe`), ce que
    l'arithmétique de redondance INSTALLE (nature `calcule`), et ce que ni
    l'un ni l'autre ne garantit.
    """
    code = str(tier or "").upper().strip()
    t = NIVEAUX_TIER.get(code)
    # Sans schéma explicite, on prend celui que le niveau appelle — en le
    # DISANT, pour qu'il ne passe pas pour un choix du projet.
    sch, origine = schema, "saisi"
    if not sch and t:
        sch, origine = t["schema_type"], "deduit_du_niveau"
    calc = redondance(sch, n_besoin) if sch else None
    if calc:
        calc["origine_schema"] = origine
    return {
        "tier": dict(t, code=code) if t else None,
        "tier_source": TIER_SOURCE,
        "en50600_source": EN50600_SOURCE,
        "classes_en50600": CLASSES_EN50600,
        "schemas": REDONDANCES,
        "schemas_ordre": sorted(REDONDANCES, key=lambda k: REDONDANCES[k]["rang"]),
        "niveaux": NIVEAUX_TIER,
        "niveaux_ordre": ["I", "II", "III", "IV"],
        "redondance": calc,
        # Ce que le niveau NE dit pas. Écrit ici plutôt qu'en note de bas de
        # page : c'est la partie qui se perd en réunion, et c'est celle qui
        # coûte cher.
        "ne_garantit_pas": [
            "L'EXPLOITATION. Un niveau qualifie une topologie, pas des "
            "consignes, ni des astreintes, ni des essais périodiques. Une "
            "installation tolérante à la panne exploitée sans procédure de "
            "bascule tombe comme une autre.",
            "LE RACCORDEMENT. Deux arrivées issues du même poste source ne "
            "font pas deux sources. La question se pose au gestionnaire de "
            "réseau, et sa réponse est écrite, pas supposée.",
            "LES SERVITUDES COMMUNES. Un chemin de câbles unique, un local "
            "unique, une vanne d'isolement unique annulent la redondance en "
            "amont d'eux — c'est le point unique de défaillance que l'analyse "
            "de risques a pour objet de trouver.",
            "LA CAPACITÉ EN DÉFAUT. La chaîne restante doit tenir la charge à "
            "la température extérieure de dimensionnement, pas à la moyenne "
            "annuelle.",
        ],
    }


# ── Ce qu'on demande À LA BASE DE CONNAISSANCE ─────────────────────────────
#
# La recherche du magasin documentaire est lexicale : score TF-IDF sur les
# termes de la requête, plus un bonus de COUVERTURE — la part des termes
# distincts de la requête retrouvés dans l'extrait. Deux conséquences que
# l'intuition ne donne pas :
#
#   — un terme fréquent (« spécification », « technique », « projet ») ne
#     rapporte presque rien, son IDF étant faible ;
#   — pire, il FAIT BAISSER la couverture des extraits vraiment pertinents :
#     une note sur le free cooling qui ne contient pas le mot « avant-projet »
#     perd des points face à un extrait quelconque qui, lui, le contient.
#
# Chercher le TITRE du document à écrire est donc l'erreur exacte à éviter :
# on demande à la base des documents « de spécification » alors qu'on veut des
# documents sur le refroidissement. Chaque pièce déclare ici le vocabulaire de
# son SUJET — des termes rares, ceux qui distinguent un document utile d'un
# document quelconque.
_RECHERCHE_PIECE = {
    "SPC-MDL": "registre documentaire codification indexation des documents plan de "
               "production documentaire cycle de vie visa approbation diffusion "
               "transmittal indice de révision",
    "SPC-PHILO": "philosophie de conception design philosophy principes directeurs "
                 "niveau de redondance N+1 2N disponibilité concurrent maintainability "
                 "fault tolerant hypothèses de dimensionnement taux de disponibilité",
    "SPC-SAFETY": "analyse de risque HAZOP HAZID scénario redouté barrière de sécurité "
                  "LOPA mise en sécurité ATEX hydrogène local batteries arrêt d'urgence "
                  "sécurité des personnes gravité probabilité criticité",
    "SPC-STRUCT": "structure génie civil fondation plancher charge d'exploitation "
                  "surcharge sismique massif béton armé descente de charges dallage "
                  "portance faux plancher technique",
    "SPC-HVAC": "refroidissement free cooling groupe froid eau glacée confinement "
                "allée chaude allée froide température de soufflage delta T ASHRAE "
                "humidité relative détente directe adiabatique tour aéroréfrigérante "
                "PUE efficacité de refroidissement",
    "SPC-CFO": "haute tension poste de livraison transformateur onduleur ASI groupe "
               "électrogène TGBT sélectivité court-circuit régime de neutre jeu de "
               "barres rendement de chaîne puissance souscrite raccordement au réseau",
    "SPC-CFA": "courants faibles GTB GTC supervision technique câblage structuré "
               "chemin de câbles comptage divisionnaire compteur d'énergie sous-comptage "
               "fibre optique baie de brassage",
    "SPC-TEL": "opérateur télécom arrivée fibre adduction fourreau chemin redondant "
               "point de présence téléphonie liaison spécialisée diversité de parcours "
               "génie civil de télécommunication",
    "SPC-SSI": "sécurité incendie compartimentage désenfumage résistance au feu degré "
               "coupe-feu détection incendie alarme ICPE code du travail système de "
               "sécurité incendie mise en sécurité incendie",
    "SPC-EXT": "extinction automatique gaz inerte azote argon brouillard d'eau "
               "sprinkleur agent extincteur concentration d'extinction temps de décharge "
               "NFPA 2001 EN 15004 étanchéité du volume protégé surpression",
    "SPC-EAUINC": "besoin en eau d'extinction débit réserve incendie poteau incendie "
                  "bâche à eau hydrant D9 D9A surface de référence durée d'extinction "
                  "rétention des eaux d'extinction bassin de confinement",
    "SPC-SUR": "sûreté malveillance contrôle d'accès intrusion vidéoprotection "
               "périmètre clôture anti-intrusion badge sas gestion des visiteurs "
               "levée de doute",
    "SPC-EVAC": "évacuation dégagement issue de secours unité de passage balisage "
                "éclairage de sécurité point de rassemblement consigne de sécurité "
                "exercice d'évacuation plan d'intervention",
    "SPC-ITOT": "baie rack densité par baie kilowatt par baie serveur GPU réseau OT "
                "système de contrôle industriel SCADA automate segmentation IEC 62443 "
                "zone et conduit inventaire des équipements",
    "SPC-CONSO": "consommation électrique annuelle par consommateur auxiliaires PUE "
                 "WUE consommation d'eau évaporation purge appoint comptage "
                 "sous-comptage profil de charge pointe de prélèvement",
    "SPC-CHALEUR": "chaleur fatale récupération de chaleur réseau de chaleur "
                   "température de reprise pompe à chaleur échangeur taux de "
                   "récupération ERF preneur de chaleur puits de chaleur",
    "SPC-RSE": "responsabilité sociétale développement durable CSRD taxonomie "
               "européenne double matérialité parties prenantes empreinte "
               "environnementale reporting extra-financier",
    "SPC-BASCARB": "bâtiment bas carbone carbone incorporé analyse de cycle de vie "
                   "ACV FDES EPD RE2020 béton bas carbone matériau biosourcé réemploi "
                   "émissions évitées",
    "SPC-FORFAIT": "enveloppe d'investissement CAPEX OPEX décomposition par lot DPGF "
                   "ratio euro par mégawatt coût complet TCO analyse de sensibilité "
                   "aléas provision pour risque raccordement foncier",
    # ── Les quatorze spécifications ajoutées ──────────────────────────────
    # Même règle que ci-dessus : des termes RARES, ceux du sujet, jamais ceux
    # du titre du document à écrire.
    "SPC-TIER": "niveau de disponibilité Tier Uptime Institute EN 50600 classe "
                "redondance N+1 2N tolérance à la panne maintenabilité concurrente "
                "double chemin de distribution topologie",
    "SPC-HTA": "poste de livraison haute tension HTA cellule disjoncteur "
               "transformateur régime de neutre sélectivité courant de court-circuit "
               "boucle ouverte comptage tarifaire raccordement",
    # ── Management du design ──────────────────────────────────────────────
    # Le vocabulaire de la coordination, pas celui des disciplines : ces pièces
    # cherchent dans la base ce qui parle d'EXIGENCES et d'INTERFACES, non de
    # groupes froids ni de transformateurs.
    "SPC-BOD": "base de conception basis of design exigence client standard "
               "preneur programme technique cahier des charges matrice de "
               "conformité traçabilité exigence critère d'acceptation",
    "SPC-INTERF": "interface entre lots coordination architecture structure "
                  "réservation trémie charge d'exploitation emprise cheminement "
                  "donnée d'entrée échéance livrable interdépendance",
    "SPC-SYNTH": "synthèse technique superposition des plans conflit "
                 "encombrement plafond technique faux plancher gabarit de "
                 "maintenance altimétrie maquette numérique coordination "
                 "spatiale détection de collision",
    "SPC-PLANETU": "planning des études jalon revue de conception chemin "
                   "critique délai d'émission dépendance gel contractuel "
                   "échéance visa retour client",
    "SPC-PRODG": "production graphique échelle niveau de détail convention de "
                 "représentation cartouche nomenclature indice système de "
                 "coordonnées format d'échange maquette",
    "SPC-TQ": "question technique point ouvert demande de précision réponse "
              "criticité blocage décision hypothèse retenue",
    "SPC-DEROG": "dérogation écart au standard non-conformité concession "
                 "justification effet sur la disponibilité autorité "
                 "d'approbation",
    "SPC-CONSULT": "consultation fournisseur analyse des offres critère de "
                   "notation variante écart au cahier des charges comparaison "
                   "technique appel d'offres grille d'évaluation",
    "SPC-ATELIER": "atelier de travail réunion technique client expert décision "
                   "arbitrage compte rendu action échéance ordre du jour",
    "SPC-COUTAG": "estimation par lot agrégation budget ratio quantité "
                  "provision pour aléa écart au budget optimisation coût "
                  "d'investissement décomposition du prix",
    "SPC-VISA": "visa des études d'exécution avis observation refus délai de "
                "visa document d'entreprise reprise indice conformité au "
                "dossier de conception",
    "SPC-CONFORM": "conformité réglementaire norme applicable référentiel "
                   "autorisation administrative preuve de conformité "
                   "attestation contrôle technique exigence normative",
    # ── Courants forts : le domaine HTB et la sélectivité ──────────────────
    "SPC-HTB": "haute tension HTB poste source raccordement au réseau de "
               "transport transformateur de puissance jeu de barres tension de "
               "raccordement puissance souscrite convention de raccordement "
               "comptage courbe de charge consignation habilitation",
    "SPC-SELECT": "courant de court-circuit sélectivité plan de protection "
                  "réglage temporisation régime de neutre impédance arc "
                  "électrique îlotage retour au réseau note de calcul "
                  "électrique",
    "SPC-SECOURS": "onduleur UPS batterie autonomie groupe électrogène cuve fioul "
                   "démarrage black start banc de charge inverseur de source "
                   "essai en charge rétention",
    "SPC-SUPERV": "gestion technique du bâtiment GTB GTC DCIM supervision compteur "
                  "classe de précision sous-comptage point de mesure alarme "
                  "protocole BACnet Modbus historisation",
    "SPC-RESO": "réseau hydraulique vanne d'isolement maillage bouclage canalisation "
                "enterrée fourreau désenfumage pente regard purgeur expansion "
                "pression statique",
    "SPC-HD": "haute densité kilowatt par baie refroidissement liquide direct DLC "
              "plaque froide immersion porte arrière active CDU distribution "
              "collecteur GPU accélérateur calcul intensif",
    "SPC-RISQ": "analyse de risques point unique de défaillance SPOF AMDEC mode de "
                "défaillance criticité arbre de défaillance scénario de perte "
                "servitude commune maintenabilité",
    "SPC-50001": "ISO 50001 revue énergétique usage énergétique significatif "
                 "situation énergétique de référence indicateur de performance "
                 "énergétique EnPI périmètre de comptage audit énergétique "
                 "sobriété plan d'actions",
    "SPC-TCO": "valeur actuelle nette taux d'actualisation durée d'amortissement "
               "coût évité surcoût seuil d'inversion scénario comparé "
               "sensibilité aux hypothèses prix de l'énergie coût de possession",
    "SPC-AO": "réponse à appel d'offres mémoire technique soutenance critère "
              "d'attribution pondération variante exigence du cahier des charges "
              "engagement de performance",
    "SPC-INVEST": "décision d'engagement rentabilité échéancier de décaissement "
                  "hypothèse de commercialisation taux de remplissage montée en "
                  "charge provision pour risque comité d'engagement délai de "
                  "raccordement",
    "SPC-STD": "brique type catalogue d'équipements admis variante autorisée "
               "dérogation paramétrable réplication multi-sites adaptation "
               "locale industrialisation règle de mise à jour",
    "SPC-REX": "retour d'expérience incident constat de mise en service écart "
               "constaté leçon tirée amélioration continue base de connaissance "
               "capitalisation",
    "SPC-REVUE": "revue de conception jalon d'approbation registre des observations "
                 "levée de réserve arbitrage acté relevé de décision participant "
                 "ordre du jour",
}

# Filet de sécurité : une spécification ajoutée demain sans vocabulaire propre
# retombe sur celui de sa discipline plutôt que sur son titre. sante() la
# signale quand même — le filet évite la régression, il ne la dispense pas.
_RECHERCHE_DISCIPLINE = {
    "projet": "conduite de projet planning jalon interface entre lots maîtrise des "
              "modifications",
    "safety": "analyse de risque sécurité des personnes scénario redouté barrière de "
              "sécurité",
    "structure": "structure génie civil charge plancher fondation béton",
    "hvac": "refroidissement free cooling groupe froid eau glacée confinement "
            "température",
    "elec_cfo": "haute tension transformateur onduleur groupe électrogène TGBT "
                "puissance",
    "elec_cfa": "courants faibles GTB supervision câblage comptage",
    "telecom": "opérateur fibre adduction chemin redondant téléphonie",
    "incendie": "sécurité incendie compartimentage désenfumage détection ICPE",
    "extinction": "extinction automatique gaz brouillard d'eau sprinkleur agent "
                  "extincteur",
    "surete": "sûreté contrôle d'accès intrusion vidéoprotection malveillance",
    "itot": "baie densité serveur réseau OT système de contrôle industriel IEC 62443",
    "environnement": "énergie eau carbone PUE WUE empreinte environnementale ICPE",
    "supervision": "supervision GTB GTC DCIM comptage métrologie alarme conduite "
                   "point de mesure",
    "fluides": "réseau hydraulique vanne d'isolement maillage canalisation enterrée "
               "pompe appoint purge",
}


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

    # ── Management du design et synthèse technique ─────────────────────────
    # LE CHAÎNON QUI MANQUAIT. Le registre décrivait ce que chaque discipline
    # produit, et rien de ce qui les tient ensemble. Or c'est là que les
    # dossiers se perdent : un PUE tenu par le lot CVC et démenti par le bilan
    # de puissance du lot CFO n'est pas une valeur, c'est un écart d'interface
    # que personne n'a relevé. Ces pièces sont celles du design manager —
    # exigences client tenues, interfaces arbitrées, plans compatibles, offres
    # analysées, coûts agrégés.
    ("SPC-BOD", "Base de conception et matrice de conformité aux exigences client",
     "design_mgmt", "contractuel", "moe", True,
     {"ESQ": "principes", "APS": "emission", "APD": "maj", "PRO": "maj",
      "DCE": "gel", "EXE-VISA": "maj", "AOR": "as_built",
      "FAISA": "principes", "BASIC": "emission", "FEED": "gel",
      "EPCI": "maj", "CSU": "as_built"},
     ["Exigences reprises une à une du standard client, du BoD et de l'exhibit "
      "technique, avec leur référence d'origine",
      "État de conformité par exigence : tenue, tenue sous réserve, en écart",
      "Lot responsable de chaque exigence et pièce qui en porte la preuve",
      "Exigences contradictoires entre documents client, et l'arbitrage retenu",
      "Exigences non traçables à une pièce : ce sont les trous du dossier"]),
    ("SPC-INTERF", "Registre des interfaces entre lots architecture, structure et techniques",
     "design_mgmt", "registre", "moe", False,
     {"APS": "principes", "APD": "emission", "PRO": "maj", "DCE": "gel",
      "EXE-VISA": "maj", "AOR": "as_built",
      "BASIC": "principes", "FEED": "emission", "EPCI": "maj"},
     ["Une ligne par interface : lot émetteur, lot récepteur, donnée échangée",
      "Date d'échéance de la donnée et phase où elle devient bloquante",
      "Réservations, charges et emprises demandées à la structure et au génie civil",
      "Interfaces avec les tiers : concessionnaire, preneur, exploitant, voisinage",
      "Interfaces ouvertes à ce jour, et ce que chacune bloque en aval"]),
    ("SPC-SYNTH", "Synthèse technique et compatibilité des plans entre spécialités",
     "design_mgmt", "plan", "moe", False,
     {"APD": "principes", "PRO": "emission", "DCE": "maj",
      "EXE-VISA": "gel", "DET": "maj", "AOR": "as_built",
      "FEED": "principes", "EPCI": "emission", "CSU": "as_built"},
     ["Superposition des lots par zone et par niveau, aux mêmes altimétries",
      "Conflits relevés, classés par gravité et par lot à reprendre",
      "Réseaux en plafond technique et en faux plancher : priorités de passage",
      "Gabarits de maintenance, dégagements et chemins de sortie des équipements",
      "Conflits résolus, conflits acceptés et le motif de leur acceptation"]),
    ("SPC-PLANETU", "Planning des études et jalons de revue de conception",
     "design_mgmt", "registre", "moe", False,
     {"ESQ": "principes", "APS": "emission", "APD": "maj", "PRO": "maj",
      "DCE": "maj", "EXE-VISA": "maj",
      "FAISA": "principes", "BASIC": "emission", "FEED": "maj", "EPCI": "maj"},
     ["Échéance d'émission de chaque pièce, par lot et par phase",
      "Chaîne des dépendances : ce qu'une pièce attend d'une autre pour sortir",
      "Jalons de revue, de visa client et de gel contractuel",
      "Délais de retour attendus du client et des tiers, et l'effet de leur dépassement",
      "Retards constatés et pièces devenues critiques pour la phase suivante"]),
    ("SPC-PRODG", "Plan de production graphique et charte de représentation",
     "design_mgmt", "procedure", "moe", False,
     {"APS": "principes", "APD": "emission", "PRO": "maj", "DCE": "gel",
      "BASIC": "principes", "FEED": "emission", "EPCI": "maj"},
     ["Liste des documents graphiques attendus par lot, par phase et par zone",
      "Échelles, niveaux de détail et conventions de représentation par type de plan",
      "Règles de nommage, de cartouche et d'indice communes à tous les lots",
      "Origine commune, système de coordonnées et altimétrie de référence",
      "Formats d'échange et règles de partage de la maquette entre intervenants"]),
    ("SPC-TQ", "Registre des questions techniques et des points ouverts",
     "design_mgmt", "registre", "moe", False,
     {"APS": "principes", "APD": "emission", "PRO": "maj", "DCE": "maj",
      "EXE-VISA": "maj", "DET": "maj",
      "BASIC": "principes", "FEED": "emission", "EPCI": "maj", "CSU": "maj"},
     ["Une ligne par question : émetteur, destinataire, date, criticité",
      "Ce que la question bloque, et à quelle date la réponse devient critique",
      "Réponse apportée, sa source et la pièce qui l'intègre",
      "Questions restées sans réponse au gel, et l'hypothèse retenue à défaut",
      "Questions closes par une décision et non par une réponse technique"]),
    ("SPC-DEROG", "Registre des dérogations au standard et des écarts assumés",
     "design_mgmt", "registre", "moe", False,
     {"APD": "principes", "PRO": "emission", "DCE": "gel",
      "EXE-VISA": "maj", "AOR": "as_built",
      "FEED": "principes", "EPCI": "emission", "CSU": "as_built"},
     ["Exigence à laquelle il est dérogé et sa référence au standard client",
      "Motif technique ou économique de la dérogation, chiffré",
      "Effet sur la disponibilité, l'exploitabilité et la garantie",
      "Autorité qui accorde la dérogation, et sa date de décision",
      "Dérogations demandées et refusées, avec le motif du refus"]),
    ("SPC-CONSULT", "Dossier de consultation fournisseurs et analyse technique des offres",
     "design_mgmt", "tableau", "moe", True,
     {"APD": "principes", "PRO": "emission", "DCE": "maj", "ACT": "gel",
      "FEED": "principes", "EPCI": "emission"},
     ["Périmètre consulté, lots alloués et calendrier de consultation",
      "Grille d'analyse technique : critères, pondération et méthode de notation",
      "Écarts de chaque offre au cahier des charges, dits un par un",
      "Variantes proposées : ce qu'elles apportent et ce qu'elles suppriment",
      "Comparaison à performances égales, et non à prix affiché"]),
    ("SPC-ATELIER", "Ateliers techniques client et experts : décisions et suites",
     "design_mgmt", "registre", "moe", False,
     {"ESQ": "principes", "APS": "emission", "APD": "maj", "PRO": "maj",
      "DCE": "maj",
      "FAISA": "principes", "BASIC": "emission", "FEED": "maj", "EPCI": "maj"},
     ["Objet de l'atelier, participants et pièces mises à l'ordre du jour",
      "Décisions prises, leur portée et la pièce qui devra les porter",
      "Sujets renvoyés à une prochaine séance, et pourquoi ils ne sont pas tranchés",
      "Actions attribuées : responsable, échéance et preuve de clôture attendue",
      "Décisions revenant sur un choix antérieur, et l'effet sur les pièces gelées"]),
    ("SPC-COUTAG", "Agrégation financière des lots et écart au budget",
     "design_mgmt", "tableau", "moe", True,
     {"ESQ": "principes", "APS": "emission", "APD": "maj", "PRO": "maj",
      "DCE": "gel", "ACT": "recalage", "AOR": "as_built",
      "FAISA": "principes", "BASIC": "emission", "FEED": "maj", "EPCI": "recalage"},
     ["Estimation par lot technique et par lot architecture et structure",
      "Base de chiffrage de chaque lot : quantités, ratios et date des prix",
      "Provisions pour aléas et pour définition non arrêtée, distinguées",
      "Écart au budget de l'opération, par lot et par cause",
      "Décisions d'optimisation retenues, leur gain et leur effet technique"]),
    ("SPC-VISA", "Registre des visas d'études d'exécution",
     "design_mgmt", "registre", "moe", False,
     {"EXE-VISA": "emission", "DET": "maj", "AOR": "as_built",
      "EPCI": "emission", "CSU": "as_built"},
     ["Une ligne par document d'exécution reçu : lot, indice, date de réception",
      "Avis rendu — visé, visé avec observations, refusé — et son délai",
      "Observations formulées, et la pièce de conception qui les fonde",
      "Documents visés avec observations non levées à la reprise suivante",
      "Délais de visa dépassés, et l'effet sur le planning de l'entreprise"]),
    ("SPC-CONFORM", "Conformité réglementaire et normative du design",
     "design_mgmt", "note", "moe", False,
     {"APS": "principes", "APD": "emission", "PRO": "maj", "DCE": "gel",
      "EXE-VISA": "maj", "AOR": "as_built",
      "BASIC": "principes", "FEED": "emission", "EPCI": "maj", "CSU": "as_built"},
     ["Textes et référentiels applicables au projet, par domaine et par lot",
      "Exigence retenue quand deux référentiels se contredisent, et son motif",
      "Preuve de conformité attendue par exigence : calcul, essai ou attestation",
      "Autorisations administratives à obtenir et leur délai d'instruction",
      "Points où le design dépasse l'exigence, et ceux où il s'y tient au plus juste"]),

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
      "moteur d'enveloppe de conseilprev (module finance_dc), consultable sur "
      "https://conseilprev.onrender.com/panorama#s-finance — décomposition par "
      "lot, part de chacun, échéancier et écart entre pays. S'y référer et les "
      "citer avec cette adresse ; ne pas les retaper ici : deux tables qui "
      "divergent valent moins qu'une seule qu'on cite."]),

    # ═══════════════════════════════════════════════════════════════════════
    #  QUATORZE SPÉCIFICATIONS AJOUTÉES
    # ═══════════════════════════════════════════════════════════════════════
    # Le registre couvrait les disciplines de conception, pas les expertises
    # qui les commandent en amont ni celles qui les valorisent en aval. Il
    # manquait le niveau de disponibilité — qui décide de la moitié du coût des
    # lots techniques —, l'amont haute tension, l'énergie de secours, la
    # supervision qui fabrique la preuve des performances engagées, les réseaux
    # de fluides, la haute densité, l'analyse des points uniques de
    # défaillance, le management de l'énergie, l'arbitrage technico-économique,
    # et tout le versant offre : appel d'offres, dossier d'investissement,
    # standard réplicable, retour d'expérience, revue de conception.

    # ── Disponibilité : la décision qui commande les autres ───────────────
    ("SPC-TIER", "Dossier de niveau de disponibilité et de redondance",
     "projet", "note", "moe", True,
     {"ESQ": "principes", "APS": "emission", "APD": "maj", "PRO": "gel",
      "DCE": "gel", "AOR": "as_built",
      "FAISA": "principes", "BASIC": "emission", "FEED": "gel", "CSU": "as_built"},
     ["Niveau visé et référentiel invoqué — Tier de l'Uptime Institute OU "
      "classe EN 50600, en disant lequel : les deux échelles ne se traduisent "
      "pas l'une dans l'autre",
      "Schéma de redondance retenu par chaîne — N, N+1, N+2, 2N, 2(N+1) — et "
      "nombre d'unités RÉELLEMENT installées qui en découle",
      "Ce que le niveau exige : chemins de distribution, maintenabilité sans "
      "interruption, tolérance au défaut unique",
      "Capacité de la chaîne restante à la température extérieure de "
      "dimensionnement, et non à la moyenne annuelle",
      "Servitudes communes qui annulent la redondance en amont d'elles — "
      "local unique, cheminement unique, vanne unique, poste source unique",
      "Ce que le niveau NE garantit PAS : l'exploitation, les procédures de "
      "bascule et les essais périodiques, qui relèvent du contrat de service",
      "IMPORTANT : ce cadre dit ce qu'un niveau EXIGE et calcule ce qu'il "
      "installe ; il ne décerne aucun niveau. Une certification se constate "
      "sur dossier complet par l'organisme, jamais par un formulaire."]),

    # ── Électricité : l'amont et le secours, traités à part ───────────────
    ("SPC-HTA", "Spécification technique — poste de livraison et distribution HTA",
     "elec_cfo", "contractuel", "moe", True,
     {"APD": "emission", "PRO": "maj", "DCE": "gel", "EXE-VISA": "maj",
      "FEED": "emission", "EPCI": "maj"},
     ["Puissance souscrite, tension de raccordement et régime d'exploitation "
      "convenus avec le gestionnaire de réseau",
      "Architecture du poste : nombre d'arrivées, cellules, transformateurs, "
      "et INDÉPENDANCE RÉELLE des sources — deux arrivées depuis le même "
      "poste source ne font pas deux sources",
      "Régime de neutre retenu et sa conséquence sur la continuité de service",
      "Courants de court-circuit, sélectivité et plan de protection",
      "Comptage tarifaire, point de livraison et limite de prestation",
      "Délai de raccordement opposable et jalon projet qu'il commande"]),
    ("SPC-HTB", "Spécification technique — raccordement HTB et poste source client",
     "elec_cfo", "contractuel", "moe", True,
     {"APS": "principes", "APD": "emission", "PRO": "maj", "DCE": "gel",
      "EXE-VISA": "maj", "AOR": "as_built",
      "BASIC": "principes", "FEED": "emission", "EPCI": "maj", "CSU": "as_built"},
     ["Puissance de raccordement demandée et sa justification au bilan de puissance",
      "Tension de raccordement retenue et le motif du passage en HTB",
      "Architecture du poste source : arrivées, jeux de barres, transformateurs HTB/HTA",
      "Régime de neutre, courants de court-circuit et tenue des matériels",
      "Interface avec le gestionnaire de réseau de transport : étude, convention, délais",
      "Comptage, courbe de charge et engagements de puissance souscrite",
      "Consignation, accès, habilitations et exploitation du poste"]),
    ("SPC-SELECT", "Note de court-circuit, régime de neutre et sélectivité des protections",
     "elec_cfo", "note", "moe", True,
     {"APD": "principes", "PRO": "emission", "DCE": "maj", "EXE-VISA": "gel",
      "AOR": "as_built",
      "FEED": "principes", "EPCI": "emission", "CSU": "as_built"},
     ["Courants de court-circuit calculés en chaque point du réseau",
      "Régime de neutre par domaine de tension et sa justification",
      "Plan de protection : fonctions retenues, réglages et temporisations",
      "Sélectivité entre étages, du poste source jusqu'au départ terminal",
      "Comportement en secours : source de remplacement, îlotage, retour au réseau",
      "Énergie d'arc électrique et conséquences sur les équipements de protection",
      "Hypothèses de calcul et données constructeur retenues, avec leur source"]),
    ("SPC-SECOURS", "Spécification technique — énergie de secours, onduleurs et "
     "groupes électrogènes", "elec_cfo", "contractuel", "moe", True,
     {"APD": "emission", "PRO": "maj", "DCE": "gel", "EXE-VISA": "maj",
      "AOR": "as_built", "FEED": "emission", "EPCI": "maj", "CSU": "as_built"},
     ["Autonomie exigée des onduleurs et charge de référence qui la définit",
      "Technologie de stockage, local, ventilation et conséquence safety — "
      "un local batteries se ventile pour l'hydrogène",
      "Puissance, nombre et schéma de redondance des groupes électrogènes",
      "Autonomie en fioul, capacité de la cuve, rétention et rubrique ICPE "
      "applicable ; contrat de réapprovisionnement et délai garanti",
      "Séquence de basculement, temps de reprise et comportement en défaut "
      "de démarrage",
      "Essais en charge : banc de charge, périodicité, charge d'essai et "
      "consommation associée — elle pèse au bilan et s'oublie au calcul"]),

    # ── Supervision : la discipline qui fabrique la preuve ────────────────
    ("SPC-SUPERV", "Spécification technique — supervision, GTB/GTC et DCIM",
     "supervision", "contractuel", "moe", True,
     {"APS": "principes", "APD": "emission", "PRO": "maj", "DCE": "gel",
      "EXE-VISA": "maj", "AOR": "as_built",
      "BASIC": "principes", "FEED": "emission", "EPCI": "maj", "CSU": "as_built"},
     ["Architecture de supervision, protocoles et interfaces entre lots",
      "PLAN DE COMPTAGE : quel compteur, à quel point exact, de quelle classe "
      "de précision, pour quel indicateur — une performance engagée sans plan "
      "de comptage est une clause invérifiable, donc inopposable",
      "Périmètre de mesure du PUE et du WUE, et conformité au protocole retenu",
      "Historisation, pas de temps, durée de conservation et export des données",
      "Alarmes : hiérarchie, seuils, conduite à tenir et anti-avalanche",
      "Cybersécurité de la chaîne de supervision et segmentation vis-à-vis "
      "de l'informatique de production"]),

    # ── Fluides : les ouvrages qu'on ne reprend pas ───────────────────────
    ("SPC-RESO", "Spécification technique — réseaux techniques et fluides",
     "fluides", "contractuel", "moe", True,
     {"APD": "emission", "PRO": "maj", "DCE": "gel", "EXE-VISA": "maj",
      "FEED": "emission", "EPCI": "maj"},
     ["Inventaire des réseaux : eau glacée, appoint, purge, eau d'extinction, "
      "eau potable, eaux usées et pluviales, air comprimé, fioul",
      "Bouclage et maillage : où le réseau est en antenne, et ce qu'une "
      "antenne coûte à la redondance de production placée en amont",
      "Vannes d'isolement et sectionnement — leur absence transforme un "
      "entretien en interruption générale",
      "Traitement d'eau, filtration, appoint, purge et rejets",
      "Cheminements enterrés, fourreaux, regards et pentes : ouvrages non "
      "reprenables après coulage",
      "Calorifuge, expansion, pression statique et points hauts"]),

    # ── Haute densité, refroidissement liquide, charges IA ────────────────
    ("SPC-HD", "Étude de haute densité, refroidissement liquide et charges IA/HPC",
     "hvac", "note", "moe", True,
     {"ESQ": "principes", "APS": "emission", "APD": "maj", "PRO": "gel",
      "FAISA": "principes", "BASIC": "emission", "FEED": "maj"},
     ["Densité par baie visée, aujourd'hui et à l'horizon du projet, et part "
      "de la charge concernée",
      "Famille de refroidissement retenue par zone : air, porte arrière "
      "active, refroidissement liquide direct, immersion — et pourquoi le "
      "mélange plutôt que l'uniformité",
      "Boucle liquide : régimes de température, débits, CDU, collecteurs, "
      "qualité d'eau et compatibilité des matériaux",
      "Conséquence sur le PUE, sur la chaleur fatale récupérable et sur sa "
      "température — une boucle liquide en relève la valeur d'usage",
      "Charge au sol, encombrement et réservations propres aux baies denses",
      "Réversibilité : ce qui reste possible si la densité réelle s'écarte de "
      "l'hypothèse, dans un sens comme dans l'autre"]),

    # ── Risques de disponibilité, distincts du safety ─────────────────────
    ("SPC-RISQ", "Analyse des risques de disponibilité et des points uniques de "
     "défaillance", "projet", "note", "moe", True,
     {"APS": "principes", "APD": "emission", "PRO": "maj", "DCE": "gel",
      "AOR": "as_built", "BASIC": "principes", "FEED": "emission",
      "EPCI": "maj", "CSU": "as_built"},
     ["Périmètre : la DISPONIBILITÉ du service, distincte du safety qui traite "
      "des personnes et des procédés — les deux analyses ne se remplacent pas",
      "Recensement systématique des points uniques de défaillance, y compris "
      "les servitudes communes en aval des chaînes redondées",
      "Modes de défaillance, effets et criticité, avec la cotation retenue et "
      "son échelle",
      "Scénarios de perte : source, froid, réseau, eau, accès — et le "
      "comportement attendu de l'installation dans chacun",
      "Mesures de réduction retenues, écartées, et le motif de l'écart",
      "Risques résiduels assumés, et par qui ils le sont"]),

    # ── Management de l'énergie ───────────────────────────────────────────
    ("SPC-50001", "Système de management de l'énergie — cadrage ISO 50001",
     "environnement", "note", "moe", True,
     {"APD": "principes", "PRO": "emission", "AOR": "maj",
      "FEED": "principes", "EPCI": "emission", "CSU": "maj"},
     ["Périmètre et domaine d'application du système de management",
      "Revue énergétique : usages énergétiques significatifs et facteurs qui "
      "les influencent",
      "Situation énergétique de référence, et la période sur laquelle elle est "
      "établie",
      "Indicateurs de performance énergétique retenus, leur méthode de calcul "
      "et les compteurs qui les alimentent — renvoi au plan de comptage",
      "Objectifs, cibles et plan d'actions, avec le gain attendu par action",
      "Ce que la conception doit PRÉVOIR pour que le système soit tenable en "
      "exploitation : comptage, points de mesure, accès aux données",
      "IMPORTANT : ce document cadre la démarche. Il ne vaut pas certification, "
      "qui suppose un audit par un organisme accrédité."]),

    # ── Arbitrage technico-économique ─────────────────────────────────────
    ("SPC-TCO", "Arbitrage technico-économique et coût complet de possession",
     "projet", "note", "moe", True,
     {"ESQ": "principes", "APS": "emission", "APD": "maj", "PRO": "gel",
      "FAISA": "principes", "BASIC": "emission", "FEED": "maj"},
     ["Options réellement comparées, et le critère qui les départage",
      "Investissement et exploitation de chaque option sur la durée retenue",
      "Hypothèses financières explicites : durée, taux d'actualisation, "
      "prix de l'énergie et de l'eau, et leur origine",
      "Sensibilité du classement aux hypothèses — l'information utile n'est "
      "pas le coût, c'est le SEUIL à partir duquel le classement s'inverse",
      "Coûts non monétaires assumés : emprise, eau, carbone, délai",
      "Recommandation, et ce qui la ferait changer",
      "IMPORTANT : les ratios d'enveloppe, la décomposition par lot, les "
      "hypothèses d'exploitation et le calcul de coût complet sont publiés par "
      "le moteur de conseilprev (module finance_dc), consultable sur "
      "https://conseilprev.onrender.com/panorama#s-finance. S'y référer et le "
      "citer ; ne pas retaper ses valeurs ici."]),

    # ── Le versant offre ──────────────────────────────────────────────────
    ("SPC-AO", "Mémoire technique de réponse à appel d'offres",
     "projet", "note", "moe", True,
     {"ESQ": "principes", "APS": "emission", "APD": "maj",
      "FAISA": "principes", "BASIC": "emission", "FEED": "maj"},
     ["Lecture des critères d'attribution et de leur pondération — c'est elle "
      "qui commande le plan du mémoire, pas l'habitude de l'entreprise",
      "Réponse point par point aux exigences du cahier des charges, avec le "
      "renvoi à la pièce technique qui la porte",
      "Solution proposée et ce qui la distingue, en termes vérifiables",
      "Engagements de performance offerts, et les conditions de leur mesure",
      "Variantes proposées, leur recevabilité au regard du règlement, et le "
      "gain qu'elles apportent",
      "Points sur lesquels l'offre s'écarte du cahier des charges, dits "
      "explicitement — une réserve tue moins qu'une réserve découverte",
      "IMPORTANT : ce document est produit du côté du CANDIDAT. Il ne se "
      "confond pas avec les pièces DCE et ACT du registre, qui sont produites "
      "du côté du maître d'ouvrage et de sa maîtrise d'œuvre."]),
    ("SPC-INVEST", "Dossier d'investissement et décision d'engagement",
     "projet", "note", "moe", True,
     {"ESQ": "principes", "APS": "emission", "APD": "maj",
      "FAISA": "principes", "BASIC": "emission", "FEED": "maj"},
     ["Objet de la décision demandée, et son montant",
      "Hypothèses de commercialisation ou d'usage, et leur origine",
      "Échéancier de décaissement rapporté aux jalons du projet",
      "Sensibilité de la décision au délai de raccordement et à la vitesse de "
      "remplissage — les deux variables qui déplacent le plus le résultat",
      "Risques projet, leur provision, et ce qui les lèverait",
      "Alternatives examinées, y compris ne pas faire",
      "IMPORTANT : les ratios, l'échéancier et l'écart entre pays sont publiés "
      "par le moteur d'enveloppe de conseilprev (module finance_dc), "
      "https://conseilprev.onrender.com/panorama#s-finance — les citer plutôt "
      "que les retaper."]),

    # ── Industrialisation et boucle de retour ─────────────────────────────
    ("SPC-STD", "Standard de conception réplicable et règles de déploiement",
     "projet", "registre", "moe", False,
     {"APD": "principes", "PRO": "emission", "DCE": "maj", "AOR": "maj",
      "FEED": "principes", "EPCI": "emission", "CSU": "maj"},
     ["Briques types retenues et leur domaine d'emploi",
      "Ce qui est FIGÉ d'un site à l'autre, ce qui est paramétrable, et ce qui "
      "est libre — un standard qui ne distingue pas les trois n'est pas "
      "applicable",
      "Catalogue d'équipements admis et critères d'admission",
      "Procédure de dérogation : qui l'accorde, sur quel motif, et où elle "
      "est tracée",
      "Adaptations imposées par le site : climat, réseau, sol, réglementation "
      "locale",
      "Règle de mise à jour du standard, et ce qui la déclenche"]),
    ("SPC-REX", "Retour d'expérience et amélioration continue",
     "projet", "registre", "moe", False,
     {"DET": "principes", "AOR": "emission", "EPCI": "principes", "CSU": "emission"},
     ["Écarts constatés entre le dossier de conception et l'ouvrage réalisé",
      "Écarts entre performances calculées et performances MESURÉES à la "
      "réception, et l'explication de chacun",
      "Incidents de chantier et de mise en service, avec leur cause première",
      "Décisions de conception qui se sont révélées coûteuses en exploitation",
      "Leçons versées au standard de conception, et lesquelles ne l'ont pas "
      "été — avec le motif",
      "Ce qui doit remonter à la base de connaissance pour servir au projet "
      "suivant"]),
    ("SPC-REVUE", "Dossier de revue de conception",
     "projet", "registre", "moe", False,
     {"APS": "emission", "APD": "maj", "PRO": "maj", "DCE": "gel",
      "EXE-VISA": "maj", "BASIC": "emission", "FEED": "maj", "EPCI": "maj"},
     ["Objet et jalon de la revue, et ce qu'elle autorise à engager",
      "Documents soumis, leur indice, et les participants par discipline",
      "Observations formulées, leur criticité et leur destinataire",
      "Arbitrages actés, avec la personne qui les a pris",
      "Réserves émises, leur condition de levée et leur échéance",
      "Décision : conception approuvée, approuvée sous réserve, ou refusée — "
      "une revue qui ne conclut pas ne sert à rien"]),
]


def _piece_discipline(entree, phase):
    """Une spécification vue depuis une phase donnée, avec le niveau attendu."""
    c, titre, disc, typ, emet, moteur, phases, contenu = entree
    niv = phases.get(phase)
    if not niv:
        return None
    t = TYPES_PIECE.get(typ) or {}
    n = NIVEAUX.get(niv) or {}
    rech, rech_orig = recherche_piece(c, disc)
    return {
        "code": c, "titre": titre,
        "type": typ, "type_nom": t.get("nom", typ), "type_aide": t.get("aide", ""),
        "emetteur": emet, "emetteur_nom": _nom_emetteur(emet),
        "moteur": bool(moteur),
        "contenu": list(contenu),
        "discipline": disc, "discipline_nom": _nom_discipline(disc),
        "niveau": niv, "niveau_nom": n.get("nom", niv), "niveau_aide": n.get("aide", ""),
        # Ce qui sera demandé À LA BASE pour rédiger cette pièce. Affiché : une
        # recherche qu'on ne voit pas ne se juge pas, et « adossé à la base de
        # connaissance » est une affirmation vérifiable ou creuse.
        "recherche": rech, "recherche_origine": rech_orig,
        # Où la même pièce apparaît ailleurs : sans cela, on croit avoir affaire
        # à un document neuf à chaque phase, et on en produit trois.
        "autres_phases": sorted(k for k in phases if k != phase),
    }


@functools.lru_cache(maxsize=32)
def pieces(code):
    """Le registre des pièces d'une phase, enrichi de ses libellés.

    MÉMOÏSÉE, ET C'EST SÛR PARCE QUE VÉRIFIÉ : pure sur des constantes de
    module, et aucun appelant ne mute les dictionnaires rendus —
    classer_pieces copie chaque pièce avant d'annoter. Bornée à 32 : le code
    de phase vient parfois de la requête, et un cache sans borne grossirait
    d'une entrée par code inconnu distinct, à la main d'un client connecté.

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
            # Une pièce de phase n'a pas de vocabulaire déclaré : elle se
            # rabat sur son titre, déjà spécifique (« Bilan de puissance
            # électrique »). L'origine le dit, plutôt que de le laisser croire.
            "recherche": recherche_piece(c, None)[0],
            "recherche_origine": recherche_piece(c, None)[1],
            "autres_phases": [],
        })
    for e in _PIECES_DISCIPLINE:
        p = _piece_discipline(e, code)
        if p:
            out.append(p)
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  CE QU'UNE PIÈCE PÈSE : OBLIGATOIRE, INDISPENSABLE, UTILE
# ═══════════════════════════════════════════════════════════════════════════
# Un registre de vingt-trois pièces présentées à plat se lit comme vingt-trois
# tâches équivalentes. Elles ne le sont pas : certaines sont imposées par un
# texte, d'autres conditionnent la décision de la phase, d'autres enrichissent
# le dossier quand le projet le mérite. Sans cette hiérarchie, le lecteur
# commence par la plus facile.
#
# LE CARACTÈRE EST DÉRIVÉ, JAMAIS SAISI. Cent quarante et une pièces annotées à
# la main diraient bientôt autre chose que le registre qu'elles décrivent. Il se
# calcule sur ce que la pièce porte déjà — son type, son niveau à CETTE phase,
# son émetteur — et sur le contexte du projet, car l'obligation en dépend : le
# contenu d'un élément de mission est fixé par décret en commande publique, et
# relève du contrat en privé. Une même pièce n'a donc pas le même caractère
# selon le maître d'ouvrage, et le prétendre serait faux.

CARACTERES = {
    "obligatoire": {
        "nom": "Obligatoire", "rang": 3, "couleur": "#F2A65A",
        "aide": "Un texte ou le marché l'impose. Son absence n'est pas un "
                "retard : elle empêche de franchir la phase ou expose le "
                "maître d'ouvrage.",
    },
    "indispensable": {
        "nom": "Indispensable", "rang": 2, "couleur": "#5BC8E8",
        "aide": "Aucun texte ne l'impose, mais la décision de la phase ne peut "
                "pas être prise sans elle. La sauter revient à décider sans "
                "l'élément qui fonde la décision.",
    },
    "utile": {
        "nom": "Utile", "rang": 1, "couleur": "#9FB3C8",
        "aide": "Elle enrichit le dossier et se justifie selon la complexité "
                "du projet. Son absence se rattrape.",
    },
}

# Les pièces que la RÉGLEMENTATION impose, indépendamment du contrat et du
# caractère public ou privé du maître d'ouvrage. Nommées une par une : c'est
# une liste courte et vérifiable, et la déduire d'un mot-clé du titre ferait
# entrer ou sortir des pièces au gré des reformulations.
_PIECES_REGLEMENTAIRES = {
    "APD-10": "Dossier de permis de construire — code de l'urbanisme.",
    "AOR-07": "Dossier d'intervention ultérieure sur l'ouvrage — code du "
              "travail, obligatoire à la réception.",
    "AOR-08": "Déclaration au titre de la directive européenne sur "
              "l'efficacité énergétique.",
    "SPC-SAFETY": "Analyse des risques pour les personnes, au titre de "
                  "l'obligation générale de sécurité de l'employeur et du "
                  "maître d'ouvrage.",
    "SPC-EVAC": "Plan d'évacuation et consignes — code du travail.",
}


def caractere_piece(pc, public=False):
    """Le poids d'une pièce à la phase où elle est demandée, et son fondement.

    Rend le caractère ET le motif : un badge « Obligatoire » sans fondement se
    discute en réunion et ne se tranche pas. Avec le motif, il se vérifie.

    `public` — maîtrise d'ouvrage publique. L'obligation en dépend réellement :
    en commande publique le contenu de l'élément de mission est fixé par
    décret ; en privé, la même pièce relève du contrat de maîtrise d'œuvre.
    """
    code = pc.get("code") or ""
    # 1. La réglementation, qui ne dépend ni du contrat ni du client.
    if code in _PIECES_REGLEMENTAIRES:
        return "obligatoire", _PIECES_REGLEMENTAIRES[code], "texte"
    # 2. Le marché. Une pièce contractuelle GELÉE devient opposable à cette
    #    phase : consulter ou signer sans elle expose immédiatement.
    if pc.get("type") == "contractuel" and pc.get("niveau") == "gel":
        return ("obligatoire",
                "Pièce du marché, gelée à cette phase : elle devient opposable "
                "et ne peut plus être complétée après signature.", "marche")
    # 3. La commande publique. Le décret fixe le contenu de l'élément de
    #    mission ; aucune de ses composantes n'est optionnelle.
    if public and not pc.get("discipline"):
        return ("obligatoire",
                "Maîtrise d'ouvrage publique : le contenu de l'élément de "
                "mission est fixé par décret et n'est pas négociable.", "decret")
    # 4. Sans elle, la phase ne décide pas. Deux cas : la pièce porte une
    #    grandeur du moteur — donc le chiffre sur lequel la décision s'appuie —
    #    ou c'est une pièce du marché en cours d'établissement.
    if pc.get("moteur"):
        return ("indispensable",
                "Elle porte les grandeurs calculées sur lesquelles la décision "
                "de phase s'appuie. Décider sans elle, c'est décider sans le "
                "chiffre.", "decision")
    if pc.get("type") == "contractuel":
        return ("indispensable",
                "Pièce du marché en cours d'établissement : ce qui n'y est pas "
                "écrit à la consultation ne se rattrape pas en chantier.",
                "decision")
    # 5. Le reste enrichit le dossier et s'ajuste à la complexité du projet.
    return ("utile",
            "Elle complète le dossier et se justifie selon la complexité du "
            "projet ; son absence se rattrape.", "usage")


# Le poids des signaux dans le classement. Écrits ici plutôt que dispersés dans
# le tri : c'est la seule façon de discuter l'ordre sans relire du code.
_POIDS_ORDRE = {
    "caractere": 100,      # multiplié par le rang du caractère (3, 2, 1)
    "gel": 24,             # elle devient opposable maintenant
    "contractuel": 16,     # pièce du marché
    "moteur": 10,          # elle porte une grandeur calculée
    "emission": 8,         # première émission : elle n'existe pas encore
    "nous": 4,             # la maîtrise d'œuvre la produit elle-même
}


def _importance(pc):
    """Le rang d'importance d'une pièce. Calculé, pour que l'ordre suive le
    registre plutôt qu'une liste tenue à part."""
    n = _POIDS_ORDRE["caractere"] * CARACTERES[pc["caractere"]]["rang"]
    if pc.get("niveau") == "gel":
        n += _POIDS_ORDRE["gel"]
    if pc.get("type") == "contractuel":
        n += _POIDS_ORDRE["contractuel"]
    if pc.get("moteur"):
        n += _POIDS_ORDRE["moteur"]
    if pc.get("niveau") == "emission":
        n += _POIDS_ORDRE["emission"]
    if pc.get("emetteur") == "moe":
        n += _POIDS_ORDRE["nous"]
    return n


def classer_pieces(liste, public=False):
    """Annote chaque pièce de son caractère et la classe par importance.

    L'ordre est DÉCROISSANT : ce qui bloque d'abord, ce qui enrichit ensuite.
    À importance égale, l'ordre du registre est conservé — un tri instable
    ferait bouger les cartes d'un affichage à l'autre sans que rien n'ait
    changé, et le lecteur croirait à une mise à jour.
    """
    out = []
    for i, p in enumerate(liste):
        q = dict(p)
        car, motif, fondement = caractere_piece(p, public)
        q["caractere"] = car
        q["caractere_nom"] = CARACTERES[car]["nom"]
        q["caractere_motif"] = motif
        q["caractere_fondement"] = fondement
        q["_rang_registre"] = i
        q["importance"] = _importance(q)
        out.append(q)
    out.sort(key=lambda x: (-x["importance"], x["_rang_registre"]))
    for i, q in enumerate(out):
        q["ordre"] = i + 1
        del q["_rang_registre"]
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  LE FIL DES GESTES : QUOI FAIRE, ET CE QUE ÇA DÉCLENCHE
# ═══════════════════════════════════════════════════════════════════════════
# POURQUOI ICI ET PAS DANS LA PAGE. Le parcours est une SÉQUENCE de décisions,
# et une séquence écrite dans du JavaScript se relit mal, ne se contrôle pas et
# se contredit dès qu'un écran change. Elle est donc déclarée en données : la
# page ne connaît que la règle générique « le premier geste non fait dont les
# préalables sont remplis ». Ajouter une étape demain, c'est ajouter une ligne
# ici — pas modifier un enchaînement de conditions.
#
# CHAQUE GESTE DIT TROIS CHOSES, et la troisième est celle qui manque partout :
# ce qu'il faut FAIRE, où le faire, et CE QUE CELA DÉCLENCHE. Un guide qui
# annonce l'étape sans dire ce qu'elle produit fait cliquer sans comprendre, et
# le lecteur s'arrête à la première décision qui l'engage.
#
# `fait_si` nomme l'état qui rend le geste accompli, `exige` ceux qu'il faut
# avoir avant. Les deux sont des CLÉS, pas du code : la page les calcule sur ce
# qu'elle voit, le module décide de l'ordre.

GESTES = [
    {
        "id": "projet",
        "fait_si": "projet",
        "exige": [],
        "titre": "Ouvrez un projet",
        "texte": "Un projet donne un destinataire à tout ce que vous allez "
                 "produire : les pièces s'y rattachent avec leur phase, leur "
                 "date et leur état.",
        "apres": "Vous retrouverez ensuite le dossier groupé par phase, vous "
                 "pourrez l'emporter en archive et y inviter un collègue.",
        "cible": "#ig-pj-sel",
        "ancre": "#ig-sec-projet",
        "fleche": "Section 1",
        "classe": "ig-bat",
    },
    {
        "id": "profil",
        "fait_si": "profil",
        "exige": [],
        "titre": "Renseignez la puissance informatique installée",
        "texte": "C'est la seule grandeur dont le calcul ne peut pas se "
                 "passer. Tout le reste a un défaut ; celle-là, non.",
        "apres": "La frise éprouve alors chaque phase contre votre profil et "
                 "montre le premier point d'arrêt — la seule information qui "
                 "commande une action.",
        "cible": "#ig-form [data-champ=\"puissance_it_kw\"]",
        "ancre": "#ig-form",
        "fleche": "Section 2",
        "classe": "ig-bat",
    },
    {
        "id": "phase",
        "fait_si": "phase",
        "exige": ["profil"],
        "titre": "Choisissez une phase dans la frise",
        "texte": "Le premier point d'arrêt est le seul qui commande une "
                 "action ; les phases suivantes sont là pour voir venir, pas "
                 "pour travailler en parallèle.",
        "apres": "Le registre des pièces de cette phase s'affiche, classé par "
                 "importance : ce qui bloque d'abord, ce qui enrichit ensuite.",
        "cible": "#ig-parcours .ig-p.stop, #ig-parcours .ig-p",
        "ancre": "#ig-parcours",
        "fleche": "Section 3",
        "classe": "ig-bat",
    },
    {
        "id": "disponibilite",
        "fait_si": "disponibilite",
        "exige": ["phase"],
        "titre": "Arrêtez le niveau de disponibilité visé",
        "texte": "Il commande le nombre de groupes froid, de chaînes onduleur "
                 "et de départs — donc la moitié du coût des lots techniques. "
                 "Le décider après avoir écrit les spécifications oblige à les "
                 "reprendre.",
        "apres": "Le nombre d'unités réellement installées est calculé, et le "
                 "niveau part avec TOUTES les pièces rédigées ensuite.",
        "cible": "#ig-tier",
        "ancre": "#ig-dispo",
        "fleche": "Section 2",
        "classe": "ig-bat",
    },
    {
        "id": "piece",
        "fait_si": "piece",
        "exige": ["phase"],
        "titre": "Rédigez la pièce la plus importante qui reste",
        "texte": "Le registre est classé : la première carte est celle qui "
                 "pèse le plus à cette phase. Commencer par la plus facile "
                 "laisse les obligatoires pour la fin.",
        "apres": "La pièce rejoint le dossier du projet, datée et rattachée à "
                 "sa phase ; vous pourrez la reprendre en Word ou en PDF.",
        "cible": "#ig-dossier .ig-grille .ig-pc:not(.fait) .ig-gen",
        "ancre": "#ig-dossier",
        "fleche": "Section 4",
        "classe": "ig-bat",
    },
    {
        "id": "visa",
        "fait_si": "visa",
        "exige": ["piece", "projet"],
        "titre": "Faites viser la pièce rédigée",
        "texte": "Rédigée ne veut pas dire acceptée. Le visa dit ce que le "
                 "client ou un collègue en a fait — et un rejet porte son "
                 "motif, sans quoi la pièce est reprise à l'identique.",
        "apres": "L'état de validation apparaît sur la carte et dans "
                 "l'archive ; un refus non levé empêche la remise.",
        "cible": "#ig-dossier .ig-visa",
        "ancre": "#ig-dossier",
        "fleche": "Section 4",
        "classe": "ig-bat",
    },
    {
        "id": "obligatoires",
        "fait_si": "obligatoires_faites",
        "exige": ["phase"],
        "titre": "Traitez les pièces obligatoires qui restent",
        "texte": "Une pièce obligatoire manquante n'est pas un retard : elle "
                 "empêche de franchir la phase ou expose le maître d'ouvrage. "
                 "Le compte est affiché dans le rail, à droite du registre.",
        "apres": "Quand il n'en reste aucune, la phase peut être remise et la "
                 "flèche de phase suivante s'ouvre.",
        "cible": "#ig-dossier .ig-c-obligatoire:not(.fait) .ig-gen",
        "ancre": "#ig-dossier",
        "fleche": "Section 4",
        "classe": "ig-bat",
    },
    {
        "id": "phase_suivante",
        "fait_si": "fin",
        "exige": ["obligatoires_faites"],
        "titre": "Passez à la phase suivante",
        "texte": "Les pièces obligatoires de cette phase sont rédigées. La "
                 "suivante de la même filière vous attend — pas la suivante "
                 "par ordre alphabétique.",
        "apres": "Le registre se recalcule sur la nouvelle phase, avec son "
                 "propre niveau d'exigence : une même spécification n'engage "
                 "pas la même chose d'une phase à l'autre.",
        "cible": "#ig-fl-phase",
        "ancre": "#ig-rail",
        "fleche": "À droite",
        "classe": "ig-bat",
    },
]

GESTE_FIN = {
    "titre": "Vous êtes au bout de la séquence",
    "texte": "La dernière phase de la filière est atteinte et ses pièces "
             "obligatoires sont rédigées.",
    "apres": "Il reste à emporter le dossier complet en archive, et à faire "
             "viser ce qui ne l'est pas encore. Un dossier n'est clos que "
             "lorsque ses pièces le sont.",
}


def prochain_geste(etat):
    """Le premier geste non accompli dont les préalables sont remplis.

    Une règle générique, appliquée à des données — et non huit conditions
    écrites à la main. La différence se voit au neuvième écran : ici on ajoute
    une ligne, là on relit un enchaînement pour deviner où l'insérer.

    `etat` est un dictionnaire de booléens produit par la page à partir de ce
    qu'elle voit. Une clé absente vaut « pas fait » : un guide qui supposerait
    l'étape accomplie ferait sauter la seule qui manquait.
    """
    etat = {k: bool(v) for k, v in (etat or {}).items()}
    for g in GESTES:
        if etat.get(g["fait_si"]):
            continue
        if all(etat.get(k) for k in g["exige"]):
            return dict(g, reste=[x["id"] for x in GESTES
                                  if not etat.get(x["fait_si"])
                                  and x["id"] != g["id"]])
    return None


def gestes_referentiel():
    """Le fil complet, servi à la page : elle rend, elle ne réécrit pas."""
    return {"gestes": GESTES, "fin": GESTE_FIN,
            "etats": sorted({g["fait_si"] for g in GESTES}
                            | {k for g in GESTES for k in g["exige"]})}


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


# ── Le conseil de phase ────────────────────────────────────────────────────
#
# Ce que le référentiel dit déjà : ce que la phase DÉCIDE et ce qu'elle
# VERROUILLE. Ce sont des faits de cadre. Ce qu'il ne disait pas : ce qui se
# passe mal à cette phase-là, en pratique, et le geste qui l'évite.
#
# Table à part plutôt que clé de plus dans PHASES : les entrées de phase sont
# déjà longues, et un conseil n'est pas de même nature qu'une exigence — il
# n'entre dans aucun calcul, il ne conditionne aucun franchissement. Les mêler
# laisserait croire que le module refuse une phase parce qu'un conseil n'a pas
# été suivi.
#
# Chaque conseil dit UNE chose et nomme le geste. « Approfondir l'étude » n'est
# pas un conseil ; « geler la densité par baie avant de dimensionner le froid »
# en est un.
CONSEILS_PHASE = {
    # ── Maîtrise d'œuvre ──────────────────────────────────────────────────
    "ESQ": {
        "titre": "Choisissez le terrain en dernier, pas en premier",
        "texte": "L'esquisse ne verrouille presque rien — sauf le terrain, et "
                 "c'est lui qui commande le raccordement électrique, l'accès à "
                 "l'eau et le régime ICPE.\n\nLe geste : demandez au "
                 "gestionnaire de réseau la file d'attente de raccordement AVANT "
                 "de signer une promesse de vente. Un délai de raccordement se "
                 "découvre en général trop tard, et il ne se rattrape pas.",
    },
    "APS": {
        "titre": "Arrêtez la densité par baie avant de dimensionner le froid",
        "texte": "Toute l'aéraulique découle de la densité admise en salle, et "
                 "l'écart entre 8 et 30 kW par baie change la famille de "
                 "refroidissement, pas seulement sa taille.\n\nLe geste : faites "
                 "écrire la densité cible et la densité maximale dans la "
                 "philosophie générale, à cette phase. Un projet qui reporte ce "
                 "choix redessine sa distribution de froid en avant-projet "
                 "définitif.",
    },
    "APD": {
        "titre": "C'est ici que le permis se joue, pas plus tard",
        "texte": "L'avant-projet définitif porte le dossier de permis de "
                 "construire. Les groupes électrogènes, les tours "
                 "aéroréfrigérantes et les cuves de combustible y entrent — et "
                 "ce sont eux qui attirent l'instruction.\n\nLe geste : faites "
                 "vérifier l'implantation des équipements bruyants et le régime "
                 "ICPE applicable avant le dépôt. Un équipement ajouté après "
                 "coup se paie en permis modificatif, donc en mois.",
    },
    "PRO": {
        "titre": "Descendez au tracé, pas seulement au principe",
        "texte": "Le projet est la dernière phase où les tracés se corrigent sans "
                 "conséquence contractuelle. Deux arrivées opérateurs déclarées "
                 "redondantes mais passant dans le même fourreau ne font qu'un "
                 "seul chemin.\n\nLe geste : exigez les tracés réels — "
                 "électricité, fluides, télécoms — et vérifiez la séparation "
                 "physique sur plan, pas sur la note d'intention.",
    },
    "DCE": {
        "titre": "Toute exigence doit porter sa méthode de contrôle",
        "texte": "Le dossier de consultation rend les exigences opposables. Une "
                 "exigence sans méthode de vérification ne se fait pas "
                 "respecter : elle se discute.\n\nLe geste : relisez chaque "
                 "performance exigée en vous demandant « qui mesure, avec quel "
                 "appareil, dans quelles conditions, et à quelle date ». Un PUE "
                 "garanti sans conditions de mesure n'engage personne.",
    },
    "ACT": {
        "titre": "Comparez les écarts, pas seulement les prix",
        "texte": "Les offres se distinguent moins par leur montant que par ce "
                 "qu'elles excluent. Un écart de dix pour cent cache souvent une "
                 "prestation renvoyée en option.\n\nLe geste : reconstituez "
                 "chaque offre au même périmètre avant de comparer, en listant "
                 "les exclusions. C'est le seul travail d'analyse qui change une "
                 "décision d'attribution.",
    },
    "EXE-VISA": {
        "titre": "Un visa n'est pas une approbation de conception",
        "texte": "Viser une étude d'exécution, c'est vérifier sa conformité au "
                 "marché — pas reprendre la conception à son compte. La nuance "
                 "décide de qui répond d'un défaut.\n\nLe geste : formulez les "
                 "visas par référence explicite à la pièce contractuelle "
                 "concernée. Un visa sans référence transfère la responsabilité "
                 "sans que personne ne l'ait voulu.",
    },
    "DET": {
        "titre": "Consignez les écarts au fil de l'eau",
        "texte": "Ce qui n'est pas relevé pendant les travaux ne se retrouve pas "
                 "à la réception : les ouvrages sont fermés, et la preuve avec "
                 "eux.\n\nLe geste : imposez la photographie des réseaux avant "
                 "fermeture, avec repérage. C'est la pièce qui manque toujours "
                 "au dossier d'exploitation, et personne ne peut la reconstituer "
                 "après.",
    },
    "AOR": {
        "titre": "La réception se prépare six mois avant, pas le jour même",
        "texte": "Un essai de performance suppose une charge, un protocole et un "
                 "appareillage. Aucun des trois ne s'improvise, et la charge "
                 "informatique réelle n'est presque jamais disponible au moment "
                 "voulu.\n\nLe geste : faites écrire le protocole d'essai et le "
                 "moyen de charge dans le marché, à la consultation. À la "
                 "réception, il est trop tard pour en discuter.",
    },
    # ── Ingénierie industrielle ───────────────────────────────────────────
    "FAISA": {
        "titre": "Un chiffre de faisabilité n'est pas un budget",
        "texte": "La faisabilité travaille à ±30 ou ±50 %. Reporter ce montant "
                 "dans un plan de financement sans sa fourchette produit un "
                 "engagement que rien ne soutient.\n\nLe geste : présentez "
                 "toujours l'enveloppe avec sa classe d'estimation et la part "
                 "non chiffrée. Au-delà d'un quart d'enveloppe non chiffrée, ce "
                 "n'est plus une estimation.",
    },
    "BASIC": {
        "titre": "Figez les bases de conception avant les équipements",
        "texte": "Les bases de conception — climat, charge, redondance, régimes "
                 "de température — commandent tout le reste. Les laisser "
                 "ouvertes pendant qu'on choisit des machines produit un "
                 "dimensionnement qui ne se justifie plus.\n\nLe geste : émettez "
                 "un document de bases de conception daté et visé, et traitez "
                 "toute évolution ultérieure comme une modification.",
    },
    "FEED": {
        "titre": "Ce qui n'est pas au FEED devient un avenant",
        "texte": "Le FEED fixe le périmètre contractuel de l'EPC. Chaque "
                 "interface non décrite deviendra une réclamation, au prix du "
                 "contractant et non du marché.\n\nLe geste : passez la matrice "
                 "de responsabilité interface par interface, et faites nommer "
                 "pour chacune qui conçoit, qui fournit, qui installe et qui "
                 "essaie. Quatre colonnes, jamais trois.",
    },
    "EPCI": {
        "titre": "Les garanties de performance se mesurent ou n'existent pas",
        "texte": "Un contrat EPCI porte des garanties — PUE, disponibilité, "
                 "délai. Sans protocole de mesure annexé, elles ne sont pas "
                 "exécutables.\n\nLe geste : annexez le protocole d'essai au "
                 "contrat, avec les conditions de charge, la période de mesure "
                 "et le traitement des conditions climatiques exceptionnelles. "
                 "Une garantie contestable est une garantie perdue.",
    },
    "CSU": {
        "titre": "Ne réceptionnez pas sans les données d'exploitation",
        "texte": "La mise en service livre l'installation ; elle doit aussi "
                 "livrer de quoi la tenir. Un site remis sans comptage "
                 "divisionnaire ni consignes ne se pilote pas.\n\nLe geste : "
                 "conditionnez la réception à la remise du dossier "
                 "d'exploitation, des courbes d'essai et des accès aux systèmes "
                 "de supervision. Ce qui n'est pas obtenu à ce moment ne "
                 "s'obtient plus.",
    },
}


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

def dossier(profil, code, inputs=None):
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
    # Le registre est CLASSÉ par importance décroissante et annoté de ce que
    # chaque pièce pèse. Présenté à plat, il se lit comme une liste de tâches
    # équivalentes, et le lecteur commence par la plus facile.
    pcs = classer_pieces(pieces(code),
                         public=bool(contexte_projet(inputs or {})
                                     .get("mop_obligatoire")))

    # Les grandeurs que le moteur peut verser au dossier, avec leur statut à ce
    # stade. « recevable » ne veut pas dire « juste » : cela veut dire que le
    # niveau de définition correspond à celui attendu par la phase.
    grandeurs = []
    # LE BALAYAGE DES ENTRÉES OUVERTES EST FAIT UNE FOIS, PAS SIX. Le profil
    # balayé ne dépend que du champ ouvert et du point — jamais de la grandeur
    # qu'on lit ensuite dans l'étude. Refait par grandeur, le même appel à
    # D.etude() partait 91 fois là où 16 suffisent (mesuré sur DCE/AOR), à
    # chaque clic de phase et à chaque export. Le try/except point par point
    # est conservé : une étude qui échoue saute SON point, pas le dossier.
    etudes_balayees = {}
    for m in (a.get("entrees_manquantes") or []):
        if m.get("id") not in _PLAGES_PLAUSIBLES:
            continue
        bas, haut = _PLAGES_PLAUSIBLES[m["id"]]
        for i in range(_N_BALAYAGE):
            x = bas + (haut - bas) * i / float(_N_BALAYAGE - 1)
            p2 = dict(profil)
            p2[m["id"]] = x
            try:
                etudes_balayees[(m["id"], i)] = (x, D.etude(p2))
            except Exception:
                continue
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
        ouvert = _etendue_entrees_ouvertes(profil, a, sec, champ, v.get("valeur"),
                                           etudes=etudes_balayees)
        grandeurs.append({
            "nom": v["nom"], "valeur": v["valeur"], "unite": v["unite"],
            "incertitude": v.get("incertitude", ""),
            "statut": "a_remplacer" if bloquants else "recevable",
            "postes_bloquants": [s["nom"] for s in bloquants],
            # Ce que les entrées ENCORE PAR DÉFAUT font à cette grandeur. Sans
            # cela, l'étude annonçait « énergie annuelle recevable, ±7,4 % » et
            # déclarait deux paragraphes plus bas que le taux de charge n'était
            # pas renseigné — alors que ce seul paramètre la déplace de ±31 %.
            # Une incertitude quatre fois trop étroite sur un chiffre présenté
            # comme acquis est pire qu'une incertitude absente.
            "entrees_ouvertes": ouvert,
            # Une grandeur nulle sans incertitude se lit comme une certitude.
            # Elle vient presque toujours d'un mode où le poste ne joue pas —
            # il faut le dire, pas laisser un zéro nu.
            "zero_sans_incertitude": (
                not v.get("incertitude") and not ouvert.get("mesuree")
                and isinstance(v.get("valeur"), (int, float))
                and float(v.get("valeur")) == 0.0),
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


# Les valeurs à balayer pour un champ resté sur son pré-remplissage. On ne
# balaie PAS toute la plage admissible du formulaire : on prend l'intervalle
# dans lequel une installation réelle se situe. Un taux de charge de 0,05 est
# saisissable, il n'est pas plausible, et l'inclure produirait une fourchette si
# large que personne ne la lirait.
_PLAGES_PLAUSIBLES = {
    "taux_charge": (0.45, 0.85),
    "part_evaporation": (0.55, 0.95),
    "cycles_concentration": (3.0, 8.0),
    "part_chaleur_reutilisee": (0.0, 0.30),
    "pue_cible": (1.15, 1.55),
}
# Combien de points par champ. Trois suffisent pour des réponses monotones, et
# datacenter.etude() coûte 0,06 ms : le balayage complet reste sous la
# milliseconde, donc il n'y a aucune raison de le faire moins bien.
_N_BALAYAGE = 5


def _etendue_entrees_ouvertes(profil, apt, sec, champ, valeur_actuelle,
                              etudes=None):
    """De combien cette grandeur bouge encore, du seul fait des entrées non saisies.

    C'est la réponse à la question qu'un lecteur se pose devant un chiffre
    « recevable » : de quoi dépend-il encore ? L'incertitude publiée par le
    moteur ne couvre que la dispersion de ses propres facteurs — la plage de
    conception du PUE, la dispersion des facteurs eau. Elle ne dit rien des
    champs que personne n'a remplis, qui pèsent souvent davantage.

    Chaque champ est balayé SEUL, les autres restant à leur valeur courante :
    les étendues ne s'additionnent donc pas, et le champ le plus lourd est celui
    qu'il faut renseigner en premier. C'est la seule information actionnable.
    """
    vide = {"mesuree": False, "champs": []}
    if not isinstance(valeur_actuelle, (int, float)) or not profil.get("puissance_it_kw"):
        return vide
    ouverts = [m for m in (apt.get("entrees_manquantes") or [])
               if m.get("id") in _PLAGES_PLAUSIBLES]
    if not ouverts:
        return vide
    champs, gmin, gmax = [], float(valeur_actuelle), float(valeur_actuelle)
    for m in ouverts:
        bas, haut = _PLAGES_PLAUSIBLES[m["id"]]
        vals, cmin, cmax = [], None, None
        for i in range(_N_BALAYAGE):
            # Étude pré-balayée par l'appelant quand elle existe : le profil
            # balayé ne dépend que (champ, point), et la recalculer ici pour
            # chaque grandeur multipliait le même travail par six. Une étude
            # absente du pré-balayage (échec point par point) est simplement
            # sautée — même geste que le try/except historique.
            if etudes is not None:
                pre = etudes.get((m["id"], i))
                if pre is None:
                    continue
                x, e2 = pre
                w = (e2.get(sec) or {}).get(champ)
            else:
                x = bas + (haut - bas) * i / float(_N_BALAYAGE - 1)
                p2 = dict(profil)
                p2[m["id"]] = x
                try:
                    w = (D.etude(p2).get(sec) or {}).get(champ)
                except Exception:
                    continue
            if not w or not isinstance(w.get("valeur"), (int, float)):
                continue
            y = float(w["valeur"])
            vals.append(y)
            if cmin is None or y < cmin:
                cmin, bas_pour = y, x
            if cmax is None or y > cmax:
                cmax, haut_pour = y, x
        if not vals or cmin is None:
            continue
        # Un champ qui ne déplace pas la grandeur n'a rien à faire dans la
        # liste : « Cycles de concentration : 0 % » sous l'énergie annuelle
        # occupe une ligne pour dire qu'il n'y a rien à dire, et noie le champ
        # qui, lui, compte.
        if abs(cmax - cmin) <= 1e-9:
            continue
        gmin, gmax = min(gmin, cmin), max(gmax, cmax)
        ref = abs(float(valeur_actuelle))
        # Le pourcentage n'a de sens que rapporté à une valeur non nulle. Sur
        # une grandeur affichée à 0 qui peut monter, on donne l'étendue en
        # clair — « de 0 à 30 % » — au lieu d'un pourcentage de zéro.
        pct = round(100.0 * (cmax - cmin) / ref, 1) if ref > 1e-9 else None
        champs.append({
            "id": m["id"], "label": m["label"],
            "min": round(cmin, 4), "max": round(cmax, 4),
            "min_pour": round(bas_pour, 3), "max_pour": round(haut_pour, 3),
            "plage": "%s – %s" % (_fr_nombre(bas), _fr_nombre(haut)),
            "etendue_pct": pct,
            # Toujours renseignée, elle : c'est elle qu'on affiche quand le
            # pourcentage n'existe pas.
            "etendue_absolue": "%s – %s" % (_fr_nombre(cmin), _fr_nombre(cmax)),
        })
    if not champs:
        return vide
    # Tri par poids décroissant. Les champs sans pourcentage (grandeur affichée
    # à zéro) passent en tête : « de 0 à 30 % » est un écart total, pas un
    # écart nul, et le classer au fond serait exactement l'erreur inverse.
    champs.sort(key=lambda c: (0, 0) if c["etendue_pct"] is None
                else (1, -c["etendue_pct"]))
    dominant = champs[0]
    return {
        "mesuree": True,
        "champs": champs,
        "min": round(gmin, 4), "max": round(gmax, 4),
        "dominant": dominant["label"],
        "dominant_pct": dominant["etendue_pct"],
        "dominant_etendue": dominant["etendue_absolue"],
        "note": "Étendue due aux seules entrées non renseignées, chacune balayée "
                "seule sur sa plage plausible. Elles ne s'additionnent pas : le "
                "champ le plus lourd est celui à renseigner en premier.",
    }


def _fr_nombre(x):
    """Un nombre à la française, sans zéros inutiles. 0.45 -> « 0,45 »."""
    s = ("%.3f" % float(x)).rstrip("0").rstrip(".")
    return s.replace(".", ",") or "0"


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
    # LE TITRE N'EST PLUS ÉCRIT ICI, ET C'EST VOULU. Cette consigne annonçait
    # « un ingénieur de maîtrise d'œuvre » quelle que soit la mission réelle.
    # Quand le cabinet intervient en assistance à maîtrise d'ouvrage ou en revue,
    # elle CONTREDISAIT la demande — et une consigne système l'emporte sur elle.
    # La pièce prescrivait alors au nom d'un rôle que le contrat ne confie pas.
    "Tu es un ingénieur d'ingénierie de projet chez CONSEILPREV, spécialisé dans les "
    "centres de données. Tu rédiges une PIÈCE de dossier de projet en français, "
    "destinée à être versée à un dossier qui sera relu par un bureau de contrôle, un "
    "maître d'ouvrage ou un contractant.\n\n"
    "Règles absolues :\n"
    "- LE TITRE AUQUEL TU ÉCRIS t'est indiqué dans la demande — maîtrise d'œuvre, "
    "assistance à maîtrise d'ouvrage, bureau d'études d'une discipline, ingénierie "
    "d'un contractant, ou revue d'une conception établie par un tiers. Il commande ce "
    "que la pièce peut PRESCRIRE et ce qu'elle ENGAGE, et tu ne t'en écartes jamais : "
    "une pièce qui prescrit au nom d'un rôle qui n'est pas le nôtre crée une "
    "responsabilité que personne n'a acceptée.\n"
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
    "multi-critères.\n\n"
    # ── Forme du document ────────────────────────────────────────────────
    # Ces règles ne sont pas cosmétiques : une pièce de dossier sans sommaire
    # ni hiérarchie se relit mal en comité, et un lecteur qui ne voit pas ce
    # qui reste à développer croit le document fini.
    "Forme imposée du document :\n"
    "1. Commence par le titre « # CODE — Intitulé », puis une ligne de "
    "métadonnées (phase, émetteur, client, mention « Brouillon — à valider »).\n"
    "2. Fais suivre d'un chapitre « ## Sommaire » listant TES chapitres et "
    "sous-chapitres, en reprenant leurs intitulés EXACTS. Un sommaire qui "
    "annonce un chapitre absent est une faute.\n"
    "3. Sépare les chapitres par une ligne « --- » : le document est lu "
    "imprimé, et un chapitre qui commence au milieu d'un paragraphe se manque.\n"
    "4. Numérote les chapitres (« ## 1. … ») et les sous-chapitres.\n"
    "5. Mets en **gras** — et seulement en gras — trois choses : les valeurs "
    "et exigences dimensionnantes, les points **à développer** par le "
    "consultant, les points **à corriger ou à confirmer** avant diffusion. "
    "Un document tout en gras ne signale plus rien.\n"
    "6. Termine par un chapitre « ## Améliorer et optimiser ce livrable » "
    "qui dit, pour CETTE pièce : ce qui manque pour la clore, ce qui la "
    "rendrait opposable, et une optimisation possible au regard de la demande "
    "du projet. Sois précis : « préciser le régime de température » et non "
    "« approfondir l'étude ».\n"
    "7. Quand tu cites une autre pièce du dossier, écris son code entre "
    "crochets suivi de son adresse, sous la forme "
    "[SPC-HVAC](https://conseilprevcyber.onrender.com/ingenierie-datacenter"
    "#phase=PHASE&piece=SPC-HVAC), en remplaçant PHASE par le code de la "
    "phase où elle est due. Un renvoi sans adresse oblige le lecteur à "
    "chercher.\n\n"
    "Langue : français soigné. Relis-toi avant de rendre — orthographe, "
    "accords, ligatures (œ dans « œuvre », « nœud »), apostrophes typographiques, "
    "espace insécable avant « : », « ; », « ! », « ? » et « % ». Vérifie que "
    "chaque nombre que tu écris est cohérent avec ceux qui te sont fournis : "
    "tu n'as pas le droit d'en produire de nouveaux, donc tout écart est une "
    "erreur de recopie."
)


def piece(code_phase, code_piece):
    for p in pieces(code_phase):
        if p["code"] == code_piece:
            return p
    return None


def recherche_piece(code_piece, discipline=None):
    """Le vocabulaire de recherche d'une pièce, et d'où il vient.

    Renvoie (termes, origine) — l'origine sert à l'afficher : un lecteur qui
    voit ce qui a été demandé à la base peut juger si la réponse valait quelque
    chose. Une recherche muette laisse croire que la base a été interrogée.
    """
    v = _RECHERCHE_PIECE.get(code_piece)
    if v:
        return v, "piece"
    v = _RECHERCHE_DISCIPLINE.get(discipline or "")
    if v:
        return v, "discipline"
    return "", "titre"


# ── LE BON SOUS-DOSSIER DE LA BASE, PAR DISCIPLINE ───────────────────────────
# La base range les documents de centres de données en sous-dossiers — les
# thèmes de la famille « Centres de données » de rag_store. Cette table dit
# lesquels interroger EN PREMIER pour chaque discipline du registre.
#
# C'est une carte, pas un filtre : les sous-dossiers nommés passent devant, le
# reste de la famille complète, puis le reste de la base — une pièce ne perd
# jamais une source parce que la carte l'aurait mal rangée. Mais l'ordre
# compte : sur une base de plusieurs centaines de documents, la note thermique
# qui nourrit un CCTP de production frigorifique doit sortir devant la note
# carbone, même mieux écrite.
#
# Les intitulés sont EXACTEMENT ceux de rag_store.THEME_FAMILLES. Une recette
# les confronte au vocabulaire réel : un intitulé recopié de travers ne
# remonterait simplement aucun document, sans erreur — la recette le voit,
# l'exploitation non.
SOUS_DOSSIERS_DISCIPLINE = {
    "hvac": ("Data center / Thermique & refroidissement",
             "Data center / Refroidissement liquide & immersion",
             "Data center / Efficacité & indicateurs (PUE, WUE, CUE, ERE)"),
    "fluides": ("Data center / Eau & stress hydrique",
                "Data center / Refroidissement liquide & immersion",
                "Data center / Thermique & refroidissement"),
    "elec_cfo": ("Data center / Énergie & électricité",),
    # Courants faibles, télécoms : pas de sous-dossier dédié — la conception
    # d'ensemble est ce qui s'en approche le plus, et le reste de la famille
    # complète.
    "elec_cfa": ("Data center / Conception & architecture",),
    "telecom": ("Data center / Conception & architecture",),
    "supervision": ("Data center / Retours d'exploitation & mesures",
                    "Data center / Efficacité & indicateurs (PUE, WUE, CUE, ERE)"),
    "itot": ("Data center / Conception & architecture",
             "Data center / Efficacité & indicateurs (PUE, WUE, CUE, ERE)"),
    "safety": ("Data center / Safety Management",
               "Data center / Safety Management / Analyse de risques & HAZOP",
               "Data center / Safety Management / Incendie & détection",
               "Data center / Safety Management / Consignation & travaux",
               "Data center / Safety Management / Plans d'urgence & exercices"),
    "surete": ("Data center / Safety Management",
               "Data center / Conception & architecture"),
    "incendie": ("Data center / Safety Management / Incendie & détection",
                 "Data center / Safety Management / Analyse de risques & HAZOP"),
    "extinction": ("Data center / Safety Management / Incendie & détection",),
    "structure": ("Data center / Conception & architecture",
                  "Data center / Études de site & implantation"),
    "environnement": ("Data center / Carbone & analyse de cycle de vie",
                      "Data center / Eau & stress hydrique",
                      "Data center / Réglementation UE (EED, taxonomie, CSRD)",
                      "Data center / Chaleur fatale & réseaux de chaleur",
                      "Data center / Green Management"),
    # Les deux disciplines qui LIVRENT plutôt qu'elles ne conçoivent : leurs
    # pièces — planning d'études, visas, dérogations, questions techniques,
    # consultations, coût complet — se nourrissent des documents de réalisation
    # avant ceux de conception.
    "projet": ("Data center / Réalisation & gouvernance de projet",
               "Data center / Appels d'offres & CCTP",
               "Data center / Qualité & non-conformités",
               "Data center / Normes (EN 50600, ISO/IEC 30134, ASHRAE)"),
    "design_mgmt": ("Data center / Réalisation & gouvernance de projet",
                    "Data center / Conception & architecture",
                    "Data center / Qualité & non-conformités",
                    "Data center / Normes (EN 50600, ISO/IEC 30134, ASHRAE)",
                    "Data center / Appels d'offres & CCTP"),
}

# Quelques pièces cherchent AILLEURS que leur discipline : une consultation
# fournisseurs se nourrit de fiches techniques, pas de la note de calcul du
# lot. Nommées pièce par pièce parce que l'exception se justifie une à une —
# une règle générale « le type consultation va aux fournisseurs » se serait
# appliquée à des pièces qu'on n'a pas relues.
_SOUS_DOSSIERS_PIECE = {
    "SPC-CONSULT": ("Data center / Fournisseurs & fiches techniques",),
    "SPC-SELECT": ("Data center / Fournisseurs & fiches techniques",),
    "SPC-CONFORM": ("Data center / Normes (EN 50600, ISO/IEC 30134, ASHRAE)",
                    "Data center / Réglementation UE (EED, taxonomie, CSRD)"),
    # Les pièces qui se jouent au chantier, pas à la planche à dessin. Le visa
    # d'exécution et le registre des dérogations relèvent du contrôle ; le
    # planning des études et le coût complet, du pilotage.
    "SPC-VISA": ("Data center / Qualité & non-conformités",
                 "Data center / Mise en service & essais"),
    "SPC-DEROG": ("Data center / Qualité & non-conformités",),
    "SPC-TQ": ("Data center / Qualité & non-conformités",),
    "SPC-PLANETU": ("Data center / Réalisation & gouvernance de projet",),
    "SPC-COUTAG": ("Data center / Réalisation & gouvernance de projet",),
    "SPC-TCO": ("Data center / Réalisation & gouvernance de projet",),
    "SPC-MDL": ("Data center / Réalisation & gouvernance de projet",),
}


def sous_dossiers(code_piece, discipline=None):
    """Les sous-dossiers de la base à interroger EN PREMIER pour cette pièce.

    L'exception de la pièce d'abord, la carte de la discipline ensuite — dans
    cet ordre et sans doublon. Liste vide si rien n'est cartographié :
    l'appelant retombe alors sur la famille entière, ce qui est le comportement
    d'avant cette carte.
    """
    out = list(_SOUS_DOSSIERS_PIECE.get((code_piece or "").strip().upper(), ()))
    for t in SOUS_DOSSIERS_DISCIPLINE.get((discipline or "").strip(), ()):
        if t not in out:
            out.append(t)
    return out


def requete_piece(code_phase, code_piece, inputs=None):
    """Ce qu'on demande À LA BASE — distinct de ce qu'on demande au modèle.

    Ne porte QUE des termes qui peuvent retrouver un document utile :

    — pas le nom de la phase ni celui de la filière. « Avant-projet sommaire »,
      « Maîtrise d'œuvre de chantier » ne figurent dans aucun document technique
      sur le refroidissement, et leur présence dans la requête abaisse la
      couverture des extraits qui, eux, traitent du sujet ;
    — pas les libellés de remplissage. Sans identification saisie, la requête
      partait chercher « segment », « périmètre » et « préciser », qui sont les
      mots de « [segment à préciser] » — quatre termes parasites, toujours.

    Le titre ne sert qu'en dernier recours, pour les pièces de phase qui ne
    déclarent pas de vocabulaire propre : il est alors le seul signal
    disponible, et il est déjà spécifique (« Bilan de puissance électrique »).
    """
    inputs = dict(inputs or {})
    pc = piece(code_phase, code_piece)
    if not pc:
        return ""
    termes, origine = recherche_piece(pc["code"], pc.get("discipline"))
    bouts = [termes] if origine != "titre" else [pc["titre"]]
    bouts.append("centre de données")
    # Le contexte projet, mais SEULEMENT s'il a été choisi : contexte_projet ne
    # rend que les champs réellement renseignés, ce qui écarte de lui-même les
    # libellés de remplissage.
    for r in contexte_projet(inputs).get("retenus", []):
        if r.get("champ") in ("secteur", "perimetre") and r.get("nom"):
            bouts.append(r["nom"])
    bouts.extend(termes_ingenierie(pc, inputs))
    c = (inputs.get("consignes") or "").strip()
    if c:
        bouts.append(c)
    return " ".join(b for b in bouts if b).strip()


# Ce que chaque choix d'ingénierie apporte à la recherche, et pour QUELLES
# pièces. Un terme n'aide que là où il discrimine : « free cooling » sur une
# spécification de refroidissement ramène le bon document ; sur la notice de
# sécurité incendie, il déplace la recherche vers un sujet qui n'est pas le
# sien et fait remonter du hors-sujet à la place de la matière utile.
#
# La correspondance se fait sur la DISCIPLINE de la pièce, déjà portée par le
# registre : lister les cent-huit codes un par un aurait divergé au premier
# ajout de pièce.
_INGENIERIE_UTILE = {
    "refroidissement": ("hvac", "fluides", "environnement", "elec_cfo",
                        "structure", "projet"),
    "classe_ashrae": ("hvac", "itot"),
    "pays": ("environnement", "elec_cfo", "fluides", "projet"),
}


def termes_ingenierie(pc, inputs):
    """Les choix d'ingénierie du client, traduits en mots de la base.

    Une recherche qui ne porte que le sujet de la pièce ramène la littérature
    générale du centre de données : elle est vraie, et sans intérêt, parce
    qu'elle ne sait rien de CE projet. Le client a pourtant déjà arrêté ce qui
    discrimine — la famille de refroidissement, la classe ASHRAE admise, le
    pays d'implantation — et ces choix décident quels documents de la base
    parlent réellement de son installation. Une spécification thermique sur un
    site en free cooling indirect n'a pas à être documentée par la littérature
    des tours évaporatives.

    On transmet le NOM du référentiel, jamais la clé : la base contient
    « free cooling indirect à assistance adiabatique », et nulle part
    « adiabatique » au sens de notre identifiant interne.
    """
    disc = pc.get("discipline") or ""
    out = []
    fam = str(inputs.get("refroidissement") or "").strip()
    if fam and disc in _INGENIERIE_UTILE["refroidissement"]:
        out.append((D.REFROIDISSEMENT.get(fam) or {}).get("nom"))
    cl = str(inputs.get("classe_ashrae") or "").strip().upper()
    if cl and disc in _INGENIERIE_UTILE["classe_ashrae"]:
        out.append("classe ASHRAE %s" % cl)
    pays = str(inputs.get("pays") or "").strip().upper()
    if pays and disc in _INGENIERIE_UTILE["pays"]:
        out.append(_nom_pays(pays))
    return [t for t in out if t]


def _nom_pays(code):
    """Le nom du pays, lu au référentiel du moteur — jamais retapé ici.

    Le retaper aurait fait deux listes de vingt-neuf pays à tenir à jour, et
    la seconde aurait divergé au premier ajout.
    """
    v = (getattr(D, "EWIF_PAYS", None) or {}).get(code) or {}
    return v.get("nom") or code


# ═══════════════════════════════════════════════════════════════════════════
#  ÉCRIRE SANS MODÈLE DE LANGAGE : LA TRAME ASSEMBLÉE
# ═══════════════════════════════════════════════════════════════════════════
# POURQUOI. Une clé d'API absente, un service saturé, un quota épuisé — et la
# rédaction s'arrêtait net. C'était honnête mais trop sévère : l'essentiel du
# document ne vient pas du modèle. Le plan de la pièce est au registre, les
# grandeurs viennent du moteur déterministe, les manques sont calculés, et les
# extraits sortent de la base de connaissance. Le modèle RÉDIGE autour de tout
# cela ; il ne le produit pas.
#
# CE QUE LA TRAME EST, ET CE QU'ELLE N'EST PAS. C'est un document de travail
# complet et exact : plan, chiffres, sources, ce qui reste à produire. Ce n'est
# pas une prose rédigée, et elle le DIT en tête — présenter une trame comme un
# livrable fini serait la seule vraie faute ici, celle qui ferait remettre au
# client un document qu'on croit écrit.
#
# QUATRE COMBINAISONS, et aucune ne rend la main vide :
#   modèle + base     → le modèle rédige, ancré sur les extraits ;
#   modèle sans base  → le modèle rédige, sans source à citer, et le dit ;
#   base sans modèle  → cette trame, avec les extraits en annexe ;
#   ni l'un ni l'autre→ cette trame, sur le seul moteur.

MODES_REDACTION = {
    "modele_et_base": {
        "nom": "Rédigé par le modèle, ancré sur la base",
        "aide": "Le modèle rédige autour des grandeurs du moteur, avec "
                "interdiction de recalculer, et cite les documents retrouvés.",
    },
    "modele_sans_base": {
        "nom": "Rédigé par le modèle, sans source citée",
        "aide": "Aucun document de la base n'a été retrouvé pour ce sujet : le "
                "texte s'appuie sur le calcul et sur le plan de la pièce, sans "
                "référence documentaire.",
    },
    "base_sans_modele": {
        "nom": "Composé par le moteur, ancré sur la base",
        "aide": "Aucun modèle de langage n'était disponible. Le moteur compose "
                "le document lui-même : objet et portée contractuelle de la "
                "pièce, trajectoire d'une phase à l'autre, interfaces, et les "
                "extraits retrouvés rattachés au point qu'ils documentent. Les "
                "points restés sans matière sont nommés un par un.",
    },
    "moteur_seul": {
        "nom": "Composé par le moteur seul",
        "aide": "Ni modèle de langage, ni document dans la base pour ce sujet. "
                "Le moteur compose ce qu'il sait de la pièce, sa portée, sa "
                "trajectoire, ses interfaces et ses manques, puis nomme ce "
                "qui reste à rédiger. Tout y est vérifiable ; rien n'y est "
                "prose.",
    },
    # ── Les deux modes de la rédaction DOCUMENTAIRE ──────────────────────────
    # Mêmes documents que « base_sans_modele », mais la cause diffère du tout
    # au tout : ici le modèle n'a pas manqué, il est DÉBRANCHÉ par choix. Dire
    # « aucun modèle n'était disponible » sur un serveur où la clé est bonne
    # enverrait l'exploitant vérifier une configuration qui n'a rien.
    "documentaire": {
        "nom": "Composé par le moteur, sur les documents de la base",
        "aide": "La rédaction par modèle d'IA est désactivée sur cette page. "
                "Le moteur compose le cadre exigentiel — objet, portée, "
                "contenu exigé, interfaces, grandeurs — et le texte "
                "documentaire vient des documents chargés dans la base, "
                "cherchés d'abord dans les sous-dossiers du thème "
                "correspondant à la pièce, cités mot pour mot et attribués.",
    },
    "documentaire_seul": {
        "nom": "Composé par le moteur — la base n'a rien fourni sur ce sujet",
        "aide": "La rédaction par modèle d'IA est désactivée, et aucun "
                "document de la base ne répond au sujet de cette pièce. "
                "Déposez les documents attendus dans les sous-dossiers du "
                "thème correspondant (console d'administration, base de "
                "connaissance) : la prochaine composition les citera.",
    },
}


def mode_redaction(modele_disponible, extraits):
    """Lequel des quatre modes s'applique, avant même d'essayer."""
    if modele_disponible:
        return "modele_et_base" if extraits else "modele_sans_base"
    return "base_sans_modele" if extraits else "moteur_seul"


def _fr_val(g):
    v = D.fr(g.get("valeur"))
    u = g.get("unite") or ""
    return ("%s %s" % (v, u)).strip()


# ── Rattacher la matière au point qu'elle documente ─────────────────────────
# Une pièce arrivait en deux blocs : le plan d'un côté, tous les extraits de
# l'autre, en annexe. Le lecteur devait faire lui-même l'appariement — et un
# document qui laisse ce travail-là n'est pas assemblé, il est empilé. Les
# rapprochements ci-dessous sont MÉCANIQUES et vérifiables : ils reposent sur
# les mots des textes du registre, jamais sur une table écrite à côté qui
# divergerait du registre au premier ajout de pièce.

def _sans_accents(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").lower()


_MOTS_VIDES = {
    "avec", "dans", "pour", "leur", "leurs", "elle", "elles", "cette", "entre",
    "chaque", "toute", "toutes", "selon", "autre", "autres", "niveau",
    "niveaux", "point", "points", "ainsi", "celle", "celles", "celui",
}


def _mots_cles(txt):
    """Les mots porteurs d'un texte court, sans accents ni mots outils.

    Le pluriel est ramené au singulier : « régime » et « régimes » désignent la
    même chose, et sans cela un extrait sur le régime d'eau glacée ne
    rejoignait jamais le point « Régimes de température » qu'il documente.
    """
    bruts = _sans_accents(txt).replace("'", " ").replace("-", " ").split()
    mots = set()
    for m in bruts:
        m = m.strip(".,;:()«»\"")
        if len(m) < 5 or m in _MOTS_VIDES:
            continue
        if len(m) >= 6 and m[-1] in "sx":
            m = m[:-1]
        mots.add(m)
    return mots


def _interfaces_piece(pc, liste):
    """Les pièces que celle-ci NOMME, retrouvées dans la phase courante.

    Le contenu exigé cite des disciplines en toutes lettres — « interfaces avec
    la sûreté et l'incendie ». Ces disciplines existent au registre, et les
    pièces qui les portent sont dans la même phase : l'interface se retrouve
    donc par le texte, sans table d'adjacence à tenir à jour.
    """
    mots = set()
    for c in pc.get("contenu") or []:
        mots |= _mots_cles(c)
    vises = {cle for cle, nom in DISCIPLINES.items()
             if cle != pc.get("discipline")
             and (_mots_cles(nom if isinstance(nom, str) else nom.get("nom", ""))
                  & mots)}
    return [p for p in liste
            if p.get("discipline") in vises and p["code"] != pc["code"]]


def _ranger_extraits(contenu, extraits):
    """Chaque extrait sous le point qu'il documente ; le reste en annexe.

    Ce qui compte n'est pas le NOMBRE de mots communs mais leur pouvoir de
    séparation. Un mot présent dans un seul point le désigne ; le même mot
    présent dans quatre points ne désigne rien. On pèse donc double le mot
    discriminant, et on exige un score de 2 : soit un mot propre à un point,
    soit deux mots partagés. Compter les mots à égalité laissait « régime
    d'eau glacée » en annexe faute d'un second mot, et aurait rapproché
    n'importe quel document parlant d'« essais » du point sur les essais.
    """
    par_point = {i: [] for i in range(len(contenu))}
    reste = []
    cles = [_mots_cles(c) for c in contenu]
    # Combien de points chaque mot touche : c'est ce qui fait sa valeur.
    portee = {}
    for k in cles:
        for m in k:
            portee[m] = portee.get(m, 0) + 1
    for h in extraits:
        txt = (h.get("content") or h.get("text") or h.get("extrait") or "")
        if not txt.strip():
            continue
        mots = _mots_cles(txt[:1200])
        scores = [(sum(2 if portee.get(m) == 1 else 1 for m in (k & mots)), i)
                  for i, k in enumerate(cles)]
        n, i = max(scores) if scores else (0, 0)
        partage = len(cles[i] & mots) if cles else 0
        # DEUX MOTS, OU UN MOT QUI PÈSE. Le score seul suffisait à rattacher une
        # page entière sur l'empreinte carbone de la filière au point
        # « Périmètre safety », pour le seul mot « périmètre » : un mot
        # discriminant vaut double, et le seuil de deux était atteint. Ce qui
        # manquait, c'est la PART que ce mot représente dans l'extrait. Un mot
        # sur trois dit de quoi parle la phrase ; un mot sur vingt-cinq ne dit
        # rien du paragraphe.
        assez = partage >= 2 or (partage and partage / float(len(mots)) >= 0.15)
        if n >= 2 and assez:
            par_point[i].append(h)
        else:
            reste.append(h)
    return par_point, reste


# UNE SEULE COPIE DU NETTOYAGE. Ce découpage vivait ici et nulle part
# ailleurs : la console des livrables, elle, recopiait le contenu brut de la
# base, tronqué à 1800 signes. Deux chaînes de livrables, deux qualités de
# citation, et le défaut ne se voyait que dans l'une des deux. Le module
# extraits.py porte désormais la règle, et les deux la lisent.
_phrases_entieres = _X.phrases_entieres


def _bloc_extraits(A, hits, ecartes=None):
    """Les extraits d'un point, remis en état, reproduits et attribués.

    Remis en état : les lettres détachées de leur mot par l'extraction du PDF
    retrouvent leur place, les items d'une liste retrouvent leur ligne, et ce
    qui ne se répare pas — un tableau aplati, une série à la précision du
    tableur — ne part pas au livrable. `ecartes` recueille les motifs, que le
    chapitre de traçabilité rend au relecteur : un écart tu ne se distingue
    pas d'une perte.

    L'attribution est portée DANS la citation, à sa dernière ligne : posée en
    dehors, elle revenait au ras de la marge tandis que le texte cité restait
    en retrait, et rien ne disait plus lequel des deux extraits elle désignait.
    """
    vus = []
    for h in hits:
        brut = (h.get("content") or h.get("text") or h.get("extrait") or "")
        paras = _X.paragraphes(brut)
        if not paras:
            motif = _X.motif_rejet(_X.phrases_entieres(_X.reparer(brut)) or brut)
            if ecartes is not None and motif:
                ecartes.append((_X.titre_document(h.get("title")), motif))
            continue
        txt = " ".join(paras)
        # DÉDOUBLONNAGE. Les fragments de la base se chevauchent : deux hits
        # voisins d'un même document reprennent le même passage à quelques mots
        # près, et le livrable citait deux fois la même chose.
        empreinte = _mots_cles(txt[:400])
        if any(len(empreinte & v) >= max(4, int(0.6 * len(empreinte)))
               for v in vus):
            continue
        vus.append(empreinte)
        A("")
        # Chaque paragraphe dans sa propre ligne de citation, séparés par un
        # « > » seul : recollés, les items d'une liste se retrouveraient en un
        # seul bloc à l'affichage après avoir été séparés ici.
        for i, p in enumerate(paras):
            if i:
                A(">")
            A("> " + p.replace("\n", "\n> "))
        A(">")
        A("> *Source : %s%s.*"
          % (_X.titre_document(h.get("title")),
             (" (thème %s)" % h["theme"]) if h.get("theme") else ""))


def trame_piece(profil, code_phase, code_piece, extraits=None, inputs=None,
                note=None, mode=None):
    """La pièce assemblée SANS modèle de langage.

    Tout ce qui est ici est vrai et vérifiable : le plan vient du registre, les
    chiffres du moteur déterministe, les manques du contrôle d'aptitude, les
    extraits de la base. Rien n'est inventé — c'est précisément ce qu'un modèle
    absent ne peut pas garantir et ce que cette trame garantit par construction.

    `mode` (facultatif) : le mode de rédaction à tracer dans le document, quand
    l'appelant le connaît mieux que nous — « documentaire » quand le modèle est
    débranché par choix et non manquant. Sans lui, on déduit comme avant.

    Renvoie None si la phase ou la pièce est inconnue : on refuse de deviner,
    comme prompts_piece.
    """
    d = dossier(profil, code_phase, inputs)
    if not d.get("connu") or not d.get("disponible"):
        return None
    pc = piece(code_phase, code_piece)
    if not pc:
        return None
    extraits = extraits or []
    inputs = dict(inputs or {})
    client = (inputs.get("client") or "").strip() or "[client à préciser]"
    if mode not in MODES_REDACTION:
        mode = "base_sans_modele" if extraits else "moteur_seul"
    m = MODES_REDACTION[mode]

    contenu = pc.get("contenu") or []
    par_point, hors = _ranger_extraits(contenu, extraits)
    # Parmi les non rattachés, ceux qui parlent quand même du sujet : on les
    # reconnaît au vocabulaire avec lequel la pièce a interrogé la base.
    _termes, _orig = recherche_piece(pc["code"], pc.get("discipline"))
    _vocab = _mots_cles(_termes or pc["titre"]) | _mots_cles(pc["titre"])
    voisins = [h for h in hors
               if _mots_cles((h.get("content") or h.get("text")
                              or h.get("extrait") or "")[:1200]) & _vocab]
    ecartes = len(hors) - len(voisins)
    # Ceux que l'extraction a rendus illisibles — tableau aplati, série à la
    # précision du tableur, renvoi à une figure absente. Recueillis au fil de
    # l'écriture des chapitres et rendus au relecteur en traçabilité : un
    # écart tu ne se distingue pas d'une perte.
    illisibles = []
    docu = [i for i in range(len(contenu)) if par_point.get(i)]
    interfaces = _interfaces_piece(pc, d.get("pieces") or [])
    caractere, motif, _fondement = caractere_piece(pc)
    a = d.get("aptitude") or {}
    # La trajectoire de la pièce : où elle naît, où elle est reprise, où elle
    # devient opposable. Relue au registre phase par phase plutôt que recopiée.
    #
    # SÉPARÉE PAR FILIÈRE, et c'est tout l'enjeu : les deux séquences sont
    # parallèles, pas successives. Mélangées, elles faisaient lire « gelée au
    # DCE » sur un projet industriel — où le DCE n'existe pas. Une pièce
    # annoncée opposable à une phase que le projet ne traversera jamais.
    fil = {p["code"]: p["filiere"] for p in PHASES}
    rang = {p["code"]: p["rang"] for p in PHASES}
    etapes, ailleurs = [], []
    for ph in [code_phase] + list(pc.get("autres_phases") or []):
        q = piece(ph, code_piece)
        if not q:
            continue
        (etapes if fil.get(ph) == d["filiere"] else ailleurs).append(
            (ph, q.get("niveau"), q.get("niveau_nom") or "—"))
    etapes = sorted({e[0]: e for e in etapes}.values(),
                    key=lambda e: rang.get(e[0], 99))
    ailleurs = sorted({e[0]: e for e in ailleurs}.values(),
                      key=lambda e: rang.get(e[0], 99))
    gel = next((e for e in etapes if e[1] == "gel"), None)
    gel_ailleurs = next((e for e in ailleurs if e[1] == "gel"), None)

    L = []
    A = L.append
    A("# %s %s" % (pc["code"], pc["titre"]))
    A("")
    # PAS DE CARTOUCHE ICI. Il est composé à l'export, où il porte en plus le
    # client, le périmètre et le statut : l'écrire aussi dans le corps le
    # faisait paraître deux fois sur la même page, une fois complet et une fois
    # amputé. Ne reste que la ligne d'identification, pour le fichier Markdown
    # et pour la lecture à l'écran, qui n'ont pas de cartouche.
    A("%s, indice %s, phase %s, projet %s, émis le %s."
      % (pc["code"], str(inputs.get("indice") or "01"), d["code"], client,
         time.strftime("%d/%m/%Y")))
    A("")
    # CE QUI N'A PAS SA PLACE DANS LE DOCUMENT. « Aucun modèle de langage
    # n'était disponible », « le modèle claude n'a pas répondu (upstream),
    # l'autre modèle est configuré, vous pouvez le choisir » : ce sont des
    # nouvelles de NOTRE outillage. Elles servent à celui qui relance la
    # rédaction, et elles sont dites à l'écran, où elles arrivent. Sur un
    # document remis à un client, elles ne disent rien de la pièce et
    # discréditent tout ce qui suit. Le mode de production reste tracé au
    # chapitre Traçabilité, où on va le chercher quand on en a besoin.
    #
    # L'état point par point, CALCULÉ. « Ce document n'est pas rédigé » était
    # vrai mais grossier : il mettait au même rang le point que la base
    # documente et celui sur lequel il n'existe rien. Le lecteur ne savait pas
    # par où commencer, alors que le document, lui, le sait.
    if contenu:
        reste = len(contenu) - len(docu)
        A("> **État de la pièce.** %s documenté%s par la base sur les %d "
          "exigés ; %s. Le détail est porté sous chaque point : ce qui est "
          "écrit ici est vérifiable, ce qui manque est nommé."
          % (_pluriel(len(docu), "point", "points"),
             "s" if len(docu) > 1 else "", len(contenu),
             ("%s à rédiger" % _pluriel(reste, "point reste", "points restent"))
             if reste else "aucun ne reste à rédiger"))
        A(">")
    # Le statut, en toutes lettres et au même endroit que dans l'étude de
    # phase. Un document composé par le moteur se relit et se complète ; le
    # remettre en l'état reste la seule vraie faute possible ici.
    A("> **Statut : brouillon d'ingénierie, à relire et à compléter.** Les "
      "faits portés ici sont vérifiables un par un : ils viennent du registre "
      "des pièces, du moteur de calcul et de la base documentaire. Ce n'est "
      "pas pour autant une rédaction : ce document ne se remet pas tel quel.")
    A("")

    # ── Sommaire, DÉRIVÉ du contenu réellement produit ──────────────────────
    # Les sous-paragraphes y figurent numérotés, comme dans le corps : un
    # sommaire qui n'annonce que les chapitres oblige à parcourir le document
    # pour trouver le point qu'on cherche — c'est-à-dire à ne pas s'en servir.
    sous1 = ["1.1 Nature et responsabilité", "1.2 Ce que cela implique"]
    if etapes:
        sous1.append("1.3 Trajectoire dans la filière %s" % d["filiere_nom"])
    plan = [("1. Objet de la pièce et ce qu'elle engage", sous1)]
    plan.append(("2. Contenu exigé, point par point",
                 ["2.%d %s" % (i + 1, c) for i, c in enumerate(contenu)]))
    n = 3
    if interfaces:
        plan.append(("%d. Interfaces avec les autres pièces de la phase" % n, []))
        n += 1
    # Le sommaire l'annonce aussi : un chapitre absent du sommaire ne se trouve
    # pas, et la numérotation qui suit décalerait de un.
    if referentiels(pc.get("discipline")):
        plan.append(("%d. Référentiels applicables à cette pièce" % n, []))
        n += 1
    plan.append(("%d. Ce que le moteur apporte à cette pièce" % n, []))
    n += 1
    sous = []
    if a.get("entrees_manquantes"):
        sous.append("%d.1 Entrées à renseigner" % n)
    if a.get("substitutions_a_faire"):
        sous.append("%d.%d Facteurs à remplacer par une donnée réelle"
                    % (n, len(sous) + 1))
    if sous:
        plan.append(("%d. Ce qui manque pour franchir la phase" % n, sous))
        n += 1
    if voisins:
        plan.append(("%d. Autres extraits sur le sujet de la pièce" % n, []))
        n += 1
    plan.append(("%d. Indices du document" % n, []))
    n += 1
    plan.append(("%d. Traçabilité" % n, []))
    A("## Sommaire")
    A("")
    for titre, ss in plan:
        A("- %s" % titre)
        for s in ss:
            A("    - %s" % s)
    A("")
    A("---")
    A("")

    # ── 1. Objet ───────────────────────────────────────────────────────────
    # RÉDIGÉ, PAS PONCTUÉ. Ces cinq faits sortaient en puces « Rubrique — tiret
    # — valeur » : à l'export, une colonne de tirets qui ne se lit pas. Ce qui
    # se dit en une phrase est écrit en une phrase ; ce qui se compare est mis
    # en tableau. Aucun tiret ne remplace plus un verbe.
    A("## 1. Objet de la pièce et ce qu'elle engage")
    A("")
    A("### 1.1 Nature et responsabilité")
    A("")
    # LES DONNÉES S'ALIGNENT. Ces six faits sortaient en phrases « Libellé :
    # valeur. » les unes sous les autres : pour comparer deux pièces il fallait
    # relire deux paragraphes au lieu de parcourir deux colonnes. Un tableau
    # les met au même fer, et la valeur décisive y est mise en évidence.
    A("| Rubrique | Valeur |")
    A("| --- | --- |")
    A("| Nature | **%s** |" % (pc.get("type_nom") or "pièce du dossier"))
    A("| Ce qu'elle engage | %s |" % (pc.get("type_aide") or "selon le marché"))
    A("| Émetteur | **%s** |" % (pc.get("emetteur_nom") or "désigné au marché"))
    A("| Caractère à la phase %s | **%s** |"
      % (code_phase, (CARACTERES[caractere]["nom"] if caractere in CARACTERES
                      else caractere).lower()))
    A("| Fondement de ce caractère | %s |" % motif)
    if pc.get("niveau_nom"):
        A("| Niveau attendu | **%s** |" % pc["niveau_nom"].lower())
        A("| Ce que ce niveau demande | %s |" % (pc.get("niveau_aide") or ""))
    A("| Alimentée par le calcul | **%s** |"
      % ("oui" if pc.get("moteur") else "non"))
    A("")
    A("### 1.2 Ce que cela implique")
    A("")
    if pc.get("moteur"):
        A("Elle porte des grandeurs du moteur de calcul, reprises au "
          "chapitre 4. Les chiffres qui y figurent engagent la décision de "
          "phase.")
    else:
        A("Son contenu se démontre par **l'analyse de la discipline**, et non "
          "par les bilans énergie, eau et carbone : aucun chiffre du moteur "
          "n'y est repris.")
    A("")
    if etapes:
        A("### 1.3 Trajectoire dans la filière %s" % d["filiere_nom"])
        A("")
        A("Cette pièce ne naît pas à cette phase et ne s'y termine pas.")
        A("")
        A("| Phase | Niveau attendu | Phase en cours |")
        A("| --- | --- | --- |")
        for code, _niv, niv_nom in etapes:
            A("| %s | %s | %s |"
              % (code, niv_nom, "oui" if code == code_phase else ""))
        A("")
        if gel and gel[0] != code_phase:
            A("Elle est **gelée à la phase %s**. Ce qui n'y figure pas devient un "
              "avenant, si bien que ce qui s'écrit ici engage au-delà de la "
              "phase en cours." % gel[0])
            A("")
        elif gel:
            A("Elle est **gelée à cette phase même**. Elle devient opposable "
              "en l'état et ne se complète plus après signature.")
            A("")
        else:
            A("Aucune phase de cette filière ne la gèle. Son caractère "
              "opposable vient du contrat et non de la séquence : c'est au "
              "marché de dire à quel indice elle engage.")
            A("")
        if ailleurs:
            A("Dans l'autre filière, la même pièce suit la séquence %s.%s"
              % (", puis ".join("%s en %s" % (c, nom.lower())
                                for c, _n, nom in ailleurs),
                 " Elle y est gelée au %s." % gel_ailleurs[0]
                 if gel_ailleurs else ""))
            A("")

    # ── 2. Le contenu, point par point ─────────────────────────────────────
    A("---")
    A("")
    A("## 2. Contenu exigé, point par point")
    A("")
    if not contenu:
        A("Le registre ne détaille pas le contenu de cette pièce.")
        A("")
    for i, c in enumerate(contenu):
        A("### 2.%d %s" % (i + 1, c))
        A("")
        hits = par_point.get(i) or []
        liens = [p for p in interfaces if _mots_cles(c) & _mots_cles(
            _nom_discipline(p.get("discipline")))]
        if liens:
            A("Ce point ouvre une interface avec %s."
              % ", ".join("%s (%s)" % (p["code"], p["titre"]) for p in liens[:4]))
            A("")
        if hits:
            A("La base de connaissance documente ce point. Les extraits "
              "ci-dessous sont reproduits mot pour mot, sans reformulation.")
            _bloc_extraits(A, hits, illisibles)
            A("")
            A("**À faire :** reprendre ces éléments au niveau de la **%s** "
              "attendue ici." % (pc.get("niveau_nom") or "définition").lower())
        else:
            A("**À rédiger.** Aucun document de la base ne répond à ce point "
              "pour la requête utilisée, reprise au chapitre Traçabilité.")
        A("")

    # ── 3. Interfaces ──────────────────────────────────────────────────────
    k = 3
    if interfaces:
        A("---")
        A("")
        A("## %d. Interfaces avec les autres pièces de la phase" % k)
        A("")
        A("Ces pièces sont retrouvées par les disciplines que le contenu "
          "exigé nomme lui-même. Elles existent à la même phase et traitent le "
          "même objet par l'autre bout : une exigence écrite ici et absente de "
          "là-bas est un trou d'interface.")
        A("")
        A("| Code | Pièce | Discipline | Niveau à cette phase |")
        A("| --- | --- | --- | --- |")
        for p in interfaces:
            A("| %s | %s | %s | %s |"
              % (p["code"], p["titre"], p.get("discipline_nom") or "",
                 p.get("niveau_nom") or ""))
        A("")
        k += 1

    # ── Les référentiels applicables ───────────────────────────────────────
    # « Conforme aux normes en vigueur » est la formule qui ne vaut rien : elle
    # ne dit pas lesquelles, ne se vérifie pas, et se retrouve dans tous les
    # CCTP. Un référentiel n'a de portée que nommé, avec ce qu'il régit ET ce
    # qu'il n'atteste pas — cette seconde colonne évite les malentendus les
    # plus coûteux du métier, à commencer par le « Tier III » qu'on s'attribue.
    refs = referentiels(pc.get("discipline"))
    if refs:
        A("---")
        A("")
        A("## %d. Référentiels applicables à cette pièce" % k)
        A("")
        A("Retenus par la discipline de la pièce. La version applicable au "
          "marché se cite au dossier de conformité réglementaire : recopiée "
          "ici, elle deviendrait fausse sans prévenir.")
        A("")
        A("| Référentiel | Ce qu'il régit | Ce qu'il n'atteste pas |")
        A("| --- | --- | --- |")
        for r in refs:
            A("| **%s** | %s | %s |" % (r["nom"], r["portee"], r["atteste_pas"]))
        A("")
        k += 1

    # ── 4. Le moteur ───────────────────────────────────────────────────────
    A("---")
    A("")
    A("## %d. Ce que le moteur apporte à cette pièce" % k)
    A("")
    if pc.get("moteur"):
        A("Cette pièce porte des grandeurs calculées. Elles viennent du "
          "moteur déterministe : elles ne se recalculent pas et ne "
          "s'arrondissent pas autrement.")
        A("")
        A("| Grandeur | Valeur | Incertitude | Statut à cette phase |")
        A("| --- | --- | --- | --- |")
        for g in d.get("grandeurs") or []:
            A("| %s | %s | %s | %s |"
              % (g["nom"], _fr_val(g), g.get("incertitude") or "sans objet",
                 "recevable" if g.get("statut") == "recevable"
                 else "à produire"))
        A("")
    else:
        # Recopier ici les six grandeurs du dossier serait un remplissage :
        # aucune ne se rapporte à cette pièce, et les afficher laisserait
        # croire qu'elle en répond.
        porteuses = [p["code"] for p in (d.get("pieces") or []) if p.get("moteur")]
        A("Le registre classe cette pièce hors calcul. Son contenu se "
          "démontre par l'analyse de la discipline et non par les bilans "
          "énergie, eau et carbone : les chiffres du moteur ne sont donc pas "
          "repris ici. Ils appartiennent aux %s de la phase qui les portent%s."
          % (_pluriel(len(porteuses), "pièce", "pièces"),
             (", dont " + ", ".join(porteuses[:6])) if porteuses else ""))
        A("")
        A("L'étude de phase les rassemble toutes : c'est là qu'il faut les "
          "lire.")
        A("")
    k += 1

    # ── 5. Ce qui manque ───────────────────────────────────────────────────
    if a.get("entrees_manquantes") or a.get("substitutions_a_faire"):
        A("---")
        A("")
        A("## %d. Ce qui manque pour franchir la phase" % k)
        A("")
        if a.get("entrees_manquantes"):
            A("### %d.1 Entrées à renseigner" % k)
            A("")
            for x in a["entrees_manquantes"]:
                A("- %s%s : %s%s"
                  % (x["label"], (" (%s)" % x["unite"]) if x.get("unite") else "",
                     x.get("pourquoi") or "non renseigné",
                     "" if x.get("origine") == "propre"
                     else ", dette d'une phase antérieure"))
            A("")
        if a.get("substitutions_a_faire"):
            A("### %d.%d Facteurs à remplacer par une donnée réelle"
              % (k, 2 if a.get("entrees_manquantes") else 1))
            A("")
            for x in a["substitutions_a_faire"]:
                A("- %s (%s%s) : %s"
                  % (x["nom"], x.get("nature") or "",
                     (", " + x["incertitude"]) if x.get("incertitude") else "",
                     x.get("remplacer_par") or "à remplacer par la donnée réelle"))
            A("")
        k += 1

    # ── 6. Ce qui concerne la pièce sans répondre à un point ───────────────
    # L'ANNEXE EXISTE, MAIS ELLE TRIE. Elle versait tout ce que la recherche
    # avait rendu : sur une pièce safety, deux pages sur l'empreinte carbone de
    # la filière, citant une étude tierce sans le moindre rapport. Ce n'était
    # pas de la matière, c'était le bruit de la recherche — et le remettre à un
    # client discrédite les extraits qui, eux, documentent vraiment.
    #
    # Le tri se fait sur le VOCABULAIRE DE LA PIÈCE, celui-là même qui a servi
    # à interroger la base : un extrait qui n'en partage pas un mot ne parle
    # pas du sujet, quoi qu'ait rendu la recherche.
    if voisins:
        A("---")
        A("")
        A("## %d. Autres extraits sur le sujet de la pièce" % k)
        A("")
        A("Ces extraits concernent le sujet sans répondre précisément à l'un "
          "des points exigés. Ils sont reproduits mot pour mot et restent à "
          "verser au bon chapitre lors de la relecture.")
        for h in voisins:
            _bloc_extraits(A, [h], illisibles)
        A("")
        k += 1

    # ── 7. Indices ─────────────────────────────────────────────────────────
    # LE SUIVI DES VERSIONS, dans le document lui-même. Deux tirages du même
    # livrable se ressemblent à s'y méprendre une fois imprimés : sans ce
    # tableau, c'est la date du fichier qui fait foi — et elle change à chaque
    # copie.
    A("---")
    A("")
    A("## %d. Indices du document" % k)
    A("")
    A("| Indice | Date | Objet de la révision | Établi par |")
    A("| --- | --- | --- | --- |")
    for r in (inputs.get("revisions") or []):
        A("| %s | %s | %s | %s |"
          % (r.get("indice") or "", r.get("date") or "",
             r.get("objet") or "", r.get("par") or ""))
    A("| %s | %s | %s | %s |"
      % (str(inputs.get("indice") or "01"), time.strftime("%d/%m/%Y"),
         "Première émission" if str(inputs.get("indice") or "01") in ("01", "1")
         else "Reprise après relecture",
         "Moteur d'ingénierie %s" % VERSION))
    A("")
    A("Les indices antérieurs restent au dossier du projet. Un indice ne se "
      "réécrit pas : une correction donne l'indice suivant.")
    A("")
    k += 1

    # ── 8. Traçabilité ─────────────────────────────────────────────────────
    A("---")
    A("")
    A("## %d. Traçabilité" % k)
    A("")
    termes, origine = recherche_piece(pc["code"], pc.get("discipline"))
    A("| Élément | Valeur |")
    A("| --- | --- |")
    A("| Assemblé le | %s |" % time.strftime("%d/%m/%Y"))
    A("| Moteur | %s |" % VERSION)
    A("| Mode de rédaction | %s |" % m["nom"])
    A("| Demandé à la base | %s |" % (termes or pc["titre"]))
    A("| Origine du vocabulaire | %s |"
      % {"piece": "propre à la pièce",
         "discipline": "propre à la discipline",
         "titre": "titre de la pièce, faute de vocabulaire déclaré"
         }.get(origine, origine))
    # OÙ la base a été interrogée d'abord. « Choisi dans le bon sous-dossier »
    # est une affirmation vérifiable ou creuse : la ligne donne au relecteur de
    # quoi la vérifier.
    sd = sous_dossiers(pc["code"], pc.get("discipline"))
    if sd:
        A("| Sous-dossiers interrogés d'abord | %s |"
          % " · ".join(s.replace("Data center / ", "") for s in sd))
        # ET LEUR RÉPONSE, EN TOUTES LETTRES. Sans cette ligne, voir que les
        # sous-dossiers attendus n'ont rien donné demandait de COMPARER deux
        # lignes — celle des sous-dossiers et les thèmes des documents cités.
        # C'est exactement la question qu'on se pose devant une pièce maigre
        # (« la base safety a-t-elle servi ? »), et le document doit y
        # répondre seul. Un extrait compte pour un sous-dossier s'il en vient
        # ou vient d'un de ses enfants — la carte nomme parfois le parent.
        dedans = [h for h in extraits
                  if any((h.get("theme") or "") == s
                         or (h.get("theme") or "").startswith(s + " / ")
                         for s in sd)]
        if dedans:
            reps = []
            for h in dedans:
                t = (h.get("theme") or "").replace("Data center / ", "")
                if t not in reps:
                    reps.append(t)
            A("| Réponse des sous-dossiers | %d des %d extraits en viennent "
              "(%s) |" % (len(dedans), len(extraits), " · ".join(reps)))
        elif extraits:
            A("| Réponse des sous-dossiers | Les sous-dossiers attendus n'ont "
              "rien fourni — recherche élargie à la famille, puis à toute la "
              "base : les documents cités viennent d'ailleurs. Déposez les "
              "documents attendus dans les sous-dossiers nommés ci-dessus : "
              "la pièce les citera d'abord. |")
        else:
            A("| Réponse des sous-dossiers | rien — ni eux, ni le reste de la "
              "base, pour la requête reprise ci-dessus |")
    A("| Extraits retrouvés | %d, dont %d rattachés à un point |"
      % (len(extraits), len(extraits) - len(hors)))
    # LES DOCUMENTS, nommés avec leur sous-dossier. Les citations les attribuent
    # déjà un à un au fil du texte ; cette ligne les rassemble, parce que c'est
    # elle qu'on lit pour répondre à « sur quoi cette pièce s'appuie-t-elle ? »
    # sans relire la pièce.
    _docs_mob, _vus_mob = [], set()
    for _h in extraits:
        _t = _X.titre_document(_h.get("title"))
        if not _t or _t in _vus_mob:
            continue
        _vus_mob.add(_t)
        _docs_mob.append("%s%s" % (_t, (" (%s)" % _h["theme"])
                                   if _h.get("theme") else ""))
    if _docs_mob:
        A("| Documents mobilisés | %s |" % " · ".join(_docs_mob))
    if voisins:
        A("| Extraits sur le sujet | %d, sans réponse précise à un point |"
          % len(voisins))
    if ecartes:
        A("| Extraits écartés | %d, hors du sujet de la pièce |" % ecartes)
    if illisibles:
        A("| Extraits illisibles | %d, écartés — voir ci-dessous |"
          % len(illisibles))
    A("| Reste à rédiger | %d point sur %d |"
      % (len(contenu) - len(docu), len(contenu)))
    A("")
    # CE QUI A ÉTÉ ÉCARTÉ, ET POURQUOI. Un tableau aplati par l'extraction d'un
    # PDF ne se reconstruit pas : ses lignes et ses colonnes ont disparu, et
    # les réinventer serait fabriquer une donnée. Le fragment sort donc du
    # livrable — mais le relecteur doit savoir qu'il existe, dans quel
    # document, et qu'il vaut peut-être la peine d'aller le lire à la source.
    if illisibles:
        A("Extraits retrouvés mais illisibles une fois sortis de leur PDF. Ils "
          "ne figurent pas dans ce document ; la source les porte encore.")
        A("")
        A("| Document | Ce qui a empêché de le citer |")
        A("| --- | --- |")
        vus_ill = set()
        for titre, motif in illisibles:
            if (titre, motif[:40]) in vus_ill:
                continue
            vus_ill.add((titre, motif[:40]))
            A("| %s | %s |" % (titre, motif))
        A("")
    # La ligne « Mode de rédaction » du tableau suffit à tracer la production.
    # Le paragraphe d'aide qui la suivait parlait de nos modèles de langage et
    # de leur disponibilité : une nouvelle de notre outillage, qui n'a rien à
    # faire dans un document remis.
    return "\n".join(L)


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
    # ── À QUEL TITRE CETTE PIÈCE EST ÉCRITE ───────────────────────────────
    # Placé AVANT le reste du contexte, parce que cela commande la personne qui
    # parle : prescrire en maîtrise d'œuvre, exiger en assistance à maîtrise
    # d'ouvrage ou constater en revue ne produisent pas le même document, et le
    # rédacteur doit le savoir avant de lire la moindre exigence de contenu.
    m = mission(inputs)
    A("")
    A("À QUEL TITRE TU ÉCRIS — %s. %s" % (m["nom"], m["implique"]))
    if not m["choisie"]:
        # L'HYPOTHÈSE SE DIT, DANS LE DOCUMENT. Une posture supposée qui ne se
        # lit nulle part est une posture que le relecteur ne peut pas
        # contester : il croit lire un choix là où il n'y a qu'un défaut.
        A("Cette posture n'a PAS été choisie : c'est la valeur par défaut. "
          "Porte-la explicitement dans la ligne de métadonnées du document, "
          "sous la forme « Rédigé en maîtrise d'œuvre (posture par défaut, à "
          "confirmer) », afin que le relecteur puisse la corriger.")
    if ctx["retenus"]:
        A("")
        A("CE QUE LE CONTEXTE DU PROJET IMPOSE — à prendre en compte dans la "
          "rédaction, chaque point vient d'un choix explicite du lecteur :")
        for r in ctx["retenus"]:
            # La mission vient d'être énoncée en tête, avec son défaut éventuel :
            # la redire ici la noierait au milieu des autres cadrages, alors
            # qu'elle ne se lit pas comme eux — elle dit QUI PARLE, pas ce que le
            # projet impose.
            if r["champ"] == "mission":
                continue
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
    # ── Le niveau de disponibilité visé ───────────────────────────────────
    # Transmis à TOUTES les pièces, pas seulement au dossier de disponibilité :
    # c'est la décision qui commande le nombre de groupes froid, de chaînes
    # onduleur, de départs et de vannes. Une spécification CVC rédigée sans
    # savoir qu'on vise 2(N+1) décrit une installation qui n'existera pas.
    dispo = disponibilite(inputs.get("tier"),
                          inputs.get("n_unites"),
                          inputs.get("schema_redondance"))
    if dispo["tier"] or dispo["redondance"]:
        A("")
        A("NIVEAU DE DISPONIBILITÉ VISÉ — décision de projet, à respecter dans "
          "toute la pièce :")
        if dispo["tier"]:
            t_ = dispo["tier"]
            A("- Niveau visé : %s" % t_["nom"])
            A("- Chemins de distribution : %s" % t_["chemins"])
            A("- Entretien : %s" % t_["maintenance"])
            A("- Comportement au défaut : %s" % t_["defaut"])
            A("- Ce que le niveau exige : %s" % t_["consequence"])
        r_ = dispo["redondance"]
        if r_:
            A("- Schéma de redondance : %s%s"
              % (r_["nom"],
                 " (déduit du niveau visé, non saisi)"
                 if r_.get("origine_schema") == "deduit_du_niveau" else ""))
            A("- Pour %d unité(s) nécessaire(s), ce schéma en installe %d "
              "(%d chaîne(s) de %d) — marge de capacité installée %+.1f %%, "
              "%d unité(s) peuvent tomber sans perte de charge. [CALCULÉ]"
              % (r_["besoin"], r_["installees"], r_["chaines"],
                 r_["par_chaine"], r_["marge_pct"], r_["perte_admissible"]))
            A("- %s" % r_["note"])
        A("- Ce que ce niveau NE garantit PAS, à ne jamais présenter comme "
          "acquis : %s" % " ".join(dispo["ne_garantit_pas"]))
        A("- Le niveau visé est une EXIGENCE de projet. Ce cadre ne décerne "
          "aucune certification : %s" % dispo["tier_source"])
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

    return SYSTEM_PIECE, "\n".join(u), requete_piece(code_phase, code_piece, inputs)


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


ORIGINES_RECHERCHE = {
    "piece": {
        "nom": "vocabulaire propre à la pièce",
        "aide": "Les termes techniques dont les documents doivent informer cette "
                "pièce — déclarés au référentiel, un par pièce.\n\nLa recherche "
                "documentaire est lexicale : un terme fréquent ne rapporte rien et "
                "fait même BAISSER le score des extraits pertinents, qui doivent "
                "alors contenir des mots inutiles pour garder leur couverture. "
                "Chercher « spécification technique » ramenait des documents sur "
                "les spécifications ; on cherche donc le sujet.",
    },
    "discipline": {
        "nom": "vocabulaire de la discipline",
        "aide": "Cette pièce ne déclare pas de vocabulaire propre : elle utilise "
                "celui de sa discipline.\n\nCela fonctionne, mais ne distingue pas "
                "deux pièces d'une même discipline — la chaleur fatale et le "
                "bâtiment bas carbone relèvent toutes deux de l'environnement et "
                "n'appellent pas les mêmes documents. Le contrôle de santé le "
                "signale.",
    },
    "titre": {
        "nom": "à défaut, son intitulé",
        "aide": "Aucun vocabulaire n'est déclaré : la recherche se rabat sur "
                "l'intitulé de la pièce.\n\nAcceptable pour les pièces de phase, "
                "dont le titre est déjà spécifique — « Bilan de puissance "
                "électrique » désigne son sujet. Ce serait insuffisant pour une "
                "spécification de discipline, dont le titre commence par les mots "
                "les plus communs du métier.",
    },
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
            # Le conseil de terrain vient EN TÊTE : c'est ce qu'un lecteur
            # cherche en survolant un sigle qu'il connaît déjà. L'objet et les
            # verrous suivent, pour celui qui ne le connaît pas.
            "aide": ((("Conseil — %s\n%s\n\n"
                       % (CONSEILS_PHASE[p["code"]]["titre"],
                          CONSEILS_PHASE[p["code"]]["texte"]))
                      if p["code"] in CONSEILS_PHASE else "")
                     + "%s\n\nCe qu'elle décide : %s\nCe qu'elle verrouille : %s"
                     % (p["objet"], p["decide"], p["verrouille"])),
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
        "recherche": ORIGINES_RECHERCHE,
        "statut": STATUTS_GRANDEUR,
        "aace": CLASSES_AACE,
        "nature": NATURES_PRECISION,
        "moteur": MOTEUR_BADGE,
        "poste": {k: {"nom": v["nom"], "aide": _aide_poste(v)}
                  for k, v in POSTES.items()},
        # Le poids d'une pièce, et surtout ce qui le FONDE. Un badge
        # « Obligatoire » sans motif se discute en réunion et ne se tranche pas.
        "caractere": {k: {"nom": v["nom"], "aide": v["aide"]}
                      for k, v in CARACTERES.items()},
        # Le vocabulaire de la disponibilité, DÉRIVÉ du référentiel et non
        # réécrit : « Tier III » se lit sur trois pages du dossier, et trois
        # définitions différentes du même sigle valent moins qu'une seule.
        "tier": {k: {
            "nom": v["nom"],
            "aide": ("Chemins — %s\nEntretien — %s\nDéfaut — %s\n\nCe que le "
                     "niveau exige : %s\n\n%s"
                     % (v["chemins"], v["maintenance"], v["defaut"],
                        v["consequence"], TIER_SOURCE)),
        } for k, v in NIVEAUX_TIER.items()},
        "redondance": {k: {
            "nom": v["nom"],
            "aide": ("%s\n\nPour N unités nécessaires, ce schéma en installe "
                     "%s%s. Le compte porte sur les UNITÉS, pas sur la "
                     "puissance."
                     % (v["aide"],
                        ("N" if not v["sup"] else "N+%d" % v["sup"]),
                        ("" if v["chaines"] == 1
                         else " par chaîne, sur %d chaînes complètes"
                              % v["chaines"]))),
        } for k, v in REDONDANCES.items()},
    }


# ═══════════════════════════════════════════════════════════════════════════
#  8. LE PARCOURS GUIDÉ — par rôle et par thème
# ═══════════════════════════════════════════════════════════════════════════
#
# POURQUOI. La page tient un cadre de quatorze phases et un registre de cent
# vingt-sept pièces. C'est juste, et c'est illisible en arrivant : un
# investisseur, un ingénieur CVC et un acheteur n'y cherchent pas la même
# chose et ne devraient pas la parcourir dans le même ordre. Une table des
# matières répond « où est quoi » ; elle ne répond pas « par où je commence ».
#
# CE QUI EST ÉCRIT ET CE QUI EST CALCULÉ. Cinq rôles portent chacun une
# SÉQUENCE — quelles sections, dans quel ordre, quoi y faire. Six thèmes
# portent chacun un PÉRIMÈTRE — quelles disciplines, quels postes du
# référentiel. Le croisement des deux n'est pas rédigé : il est CALCULÉ sur le
# registre réel. Trente textes écrits à la main diraient bientôt autre chose
# que le registre qu'ils prétendent décrire ; un calcul suit le registre.

ROLES_GUIDE = [
    {
        "id": "investisseur",
        "couleur": "#E8B44A",
        "icone": "◆",
        "nom": "Maître d'ouvrage · investisseur",
        "question": "Ce projet tient-il, et à partir de quand puis-je m'engager ?",
        "cherche": "Le moment où le chiffre cesse d'être indicatif — et ce qu'il "
                   "faut avoir produit pour y arriver.",
        "phases_cles": ["FAISA", "ESQ", "APS"],
        "filiere": "indus",
        "fin": "Vous savez ce que la phase suivante exige, et ce qu'elle "
               "verrouille. C'est de cela que se décide un engagement, pas d'un "
               "montant isolé.",
    },
    {
        "id": "moe",
        "couleur": "#22D3EE",
        "icone": "▤",
        "nom": "Maîtrise d'œuvre",
        "question": "Que dois-je produire, à quelle phase, et à quel niveau ?",
        "cherche": "Le plan de production documentaire, avec les niveaux "
                   "d'émission attendus phase par phase.",
        "phases_cles": ["APS", "APD", "PRO", "DCE"],
        "filiere": "moe",
        "fin": "Vous tenez la liste des pièces de la phase, leur niveau attendu "
               "et celles que le calcul alimente. C'est un plan de charge, pas "
               "une intention.",
    },
    {
        "id": "discipline",
        "couleur": "#7FD4A8",
        "icone": "⌁",
        "nom": "Ingénieur de discipline",
        "question": "Que dois-je écrire pour ma discipline, et avec quelles données ?",
        "cherche": "Sa spécification, le niveau attendu à la phase courante, et "
                   "les grandeurs que le moteur lui fournit déjà.",
        "phases_cles": ["APS", "APD", "PRO"],
        "filiere": "moe",
        "fin": "Vous savez ce que votre spécification doit contenir, ce que le "
               "calcul vous donne, et ce qu'il vous faudra chercher ailleurs.",
    },
    {
        "id": "acheteur",
        "couleur": "#E69FC2",
        "icone": "§",
        "nom": "Acheteur · contractant",
        "question": "Sur quoi puis-je engager quelqu'un, et avec quelle tolérance ?",
        "cherche": "La classe de précision de la phase et ce qui devient "
                   "opposable au moment du gel contractuel.",
        "phases_cles": ["DCE", "ACT", "EPCI"],
        "filiere": "moe",
        "fin": "Vous savez quelle tolérance la phase autorise et ce qui, dans le "
               "dossier, est assez arrêté pour porter une pénalité.",
    },
    {
        "id": "exploitant",
        "couleur": "#9FB4F2",
        "icone": "◈",
        "nom": "Exploitant · futur exploitant",
        "question": "Qu'est-ce que je récupère, et saurai-je le vérifier ?",
        "cherche": "Les pièces remises à la réception, et les points de comptage "
                   "sans lesquels aucune consommation ne se contrôle.",
        "phases_cles": ["AOR", "CSU", "DET"],
        "filiere": "moe",
        "fin": "Vous savez ce que le dossier d'exploitation doit contenir pour "
               "que les engagements pris soient vérifiables après la mise en "
               "service — et non seulement déclarés.",
    },
]

THEMES_GUIDE = [
    {
        "id": "energie",
        "couleur": "#F2A65A",
        "icone": "⚡",
        "nom": "Énergie et rendement",
        "question": "Combien l'installation consommera-t-elle, et de quoi cela dépend-il ?",
        # PAS toute la discipline environnement : la RSE et le bâtiment bas
        # carbone en relèvent et ne parlent pas d'énergie. On nomme les pièces,
        # dont la charge informatique — elle EST la source de la consommation,
        # et la laisser dehors au motif qu'elle relève d'une autre discipline
        # serait suivre le classement plutôt que le sujet.
        "disciplines": ["hvac", "elec_cfo", "supervision"],
        "pieces_sup": ["SPC-ITOT", "SPC-CONSO", "SPC-CHALEUR", "SPC-HD",
                       "SPC-50001"],
        "postes": ["pue", "intensite"],
        "piege": "Le PUE est une plage de conception avant d'être une mesure. "
                 "L'écrire au contrat avant d'avoir les courbes constructeur, "
                 "c'est s'engager sur une famille d'installations, pas sur la "
                 "sienne.",
    },
    {
        "id": "eau",
        "couleur": "#5BC8E8",
        "icone": "≈",
        "nom": "Eau",
        "question": "Quelle eau, prélevée où, et qu'est-ce que le WUE ne dit pas ?",
        # L'eau d'extinction relève de la discipline incendie, dont le reste
        # (compartimentage, désenfumage) n'est pas un sujet d'eau ; la chaleur
        # fatale y entre parce que récupérer la chaleur change le mode
        # d'évacuation, donc l'eau. On nomme donc les pièces plutôt que
        # d'élargir le thème à des disciplines entières.
        "disciplines": ["hvac", "extinction", "fluides"],
        "pieces_sup": ["SPC-EAUINC", "SPC-CONSO", "SPC-CHALEUR"],
        "postes": ["ewif", "evaporation"],
        "piege": "Le WUE ne compte que l'eau du site. L'eau consommée en amont "
                 "par la production électrique peut l'emporter, et la réserve "
                 "d'extinction ne figure ni dans l'un ni dans l'autre.",
    },
    {
        "id": "carbone",
        "couleur": "#8FD48F",
        "icone": "◐",
        "nom": "Carbone et RSE",
        "question": "Quelle empreinte, et lequel des leviers pèse vraiment ?",
        # La structure porte l'essentiel du carbone incorporé ; le reste est
        # nommé pièce par pièce, pour la même raison qu'ailleurs — l'extinction
        # et la CVC relèvent de l'environnement sans être des sujets carbone.
        "disciplines": ["structure"],
        "pieces_sup": ["SPC-BASCARB", "SPC-RSE", "SPC-CONSO", "SPC-CHALEUR"],
        "postes": ["incorpore", "intensite"],
        "piege": "Le carbone incorporé est annoncé à ±50 %, soit un facteur "
                 "trois entre les bornes. Il suffit à comparer des familles ; "
                 "il ne suffit plus à classer des leviers de décarbonation.",
    },
    {
        "id": "securite",
        "couleur": "#F39F7D",
        "icone": "▲",
        "nom": "Sécurité et incendie",
        "question": "Quels scénarios, quelle extinction, et combien d'eau pour l'éteindre ?",
        "disciplines": ["safety", "incendie", "extinction", "surete"],
        "postes": [],
        "piege": "La safety traite les accidents, la sûreté les actes "
                 "malveillants : deux analyses, deux dossiers. Les confondre "
                 "laisse un des deux sans titulaire.",
    },
    {
        "id": "disponibilite",
        "couleur": "#C1A8EB",
        "icone": "⏻",
        # Le thème ne s'appelle plus « électrique » : la redondance du froid
        # tombe aussi vite que celle de la puissance, et une vanne d'isolement
        # manquante annule l'une comme l'autre.
        "nom": "Disponibilité et redondance",
        "question": "Quel niveau visé, quelle redondance, et qu'est-ce qui "
                    "l'annule en aval ?",
        "disciplines": ["elec_cfo", "elec_cfa", "itot", "telecom", "fluides"],
        # Le niveau se décide dans la philosophie générale, avant toute étude
        # de discipline ; le dossier de disponibilité l'arrête et en tire le
        # nombre d'unités ; l'analyse de risques cherche ce qui le contredit.
        "pieces_sup": ["SPC-PHILO", "SPC-TIER", "SPC-HTA", "SPC-SECOURS",
                       "SPC-RISQ", "SPC-SUPERV"],
        "postes": ["pue"],
        "piege": "Deux arrivées qui empruntent le même fourreau ne font qu'un "
                 "seul chemin. La redondance se vérifie sur le tracé, pas sur "
                 "le contrat.",
    },
    {
        "id": "cout",
        "couleur": "#E8C86A",
        "icone": "€",
        "nom": "Coût et enveloppe",
        "question": "Que vaut l'enveloppe, et quelle part n'est pas encore chiffrée ?",
        # PAS toute la discipline environnement : la RSE et le bâtiment bas
        # carbone en relèvent aussi et ne sont pas des sujets de coût. On nomme
        # l'étude de consommation, qui porte l'OPEX, et rien de plus.
        "disciplines": ["projet"],
        "pieces_sup": ["SPC-CONSO", "SPC-FORFAIT", "SPC-TCO", "SPC-INVEST",
                       "SPC-AO"],
        "postes": ["incorpore"],
        "piege": "Au-delà d'un quart d'enveloppe non chiffrée, le total n'est "
                 "plus une estimation : c'est une addition de ce qu'on sait "
                 "déjà, présentée comme un montant.",
    },
]

# Les cinq étapes de la page, dans son ordre. Le rôle ne change pas cet ordre —
# une section 3 lue avant la section 1 ne calcule rien — il change ce qu'on y
# fait et pourquoi. Le libellé et l'ancre sont écrits ici une fois : la page les
# reçoit, elle ne les redevine pas.
_ETAPES_PAGE = [
    {"ancre": "ig-form", "section": 1, "titre": "Le profil de l'installation"},
    {"ancre": "ig-parcours", "section": 2, "titre": "Où vous en êtes dans la séquence"},
    {"ancre": "ig-dossier", "section": 3, "titre": "L'étude de la phase retenue"},
    {"ancre": "ig-correspondances", "section": 4, "titre": "Les deux filières face à face"},
    {"ancre": "ig-limites", "section": 5, "titre": "Ce que ce cadre ne fait pas"},
]

# Ce qu'on fait à chaque section, selon le rôle. Cinq rôles × cinq sections :
# vingt-cinq consignes, écrites — c'est la part qui ne se déduit pas. Ce qui se
# déduit, ce sont les CHIFFRES, calculés plus bas sur le registre réel.
_CONSIGNES = {
    "investisseur": [
        ("Ne renseignez que la puissance informatique. Tout le reste a une "
         "valeur par défaut, signalée comme telle.",
         "Un premier ordre de grandeur en une saisie — et l'aveu, en clair, de "
         "ce qui n'est encore qu'une hypothèse."),
        ("Basculez sur la filière ingénierie et lisez la faisabilité. C'est la "
         "seule phase qui ne suppose aucune étude préalable.",
         "Vous voyez d'un coup ce que le calcul peut porter maintenant, et à "
         "partir de quelle phase il ne suffira plus."),
        ("Ouvrez la phase de faisabilité et lisez la précision attendue avant "
         "les chiffres eux-mêmes.",
         "Une classe d'estimation dit ce que le montant vaut. Sans elle, un "
         "chiffre à ±50 % se lit comme un devis."),
        ("Comparez les deux filières : votre projet suivra l'une ou l'autre "
         "selon qu'il est passé en marché public ou en contrat industriel.",
         "Les jalons de décision ne tombent pas aux mêmes moments — savoir "
         "lequel s'applique évite de croire une décision encore ouverte."),
        ("Lisez ce que le cadre refuse de faire.",
         "Un outil qui annonce ses limites vous dit où chercher l'expertise "
         "qu'il ne remplace pas."),
    ],
    "moe": [
        ("Renseignez la puissance, puis autant de champs que vous en tenez : "
         "chaque champ rempli resserre les incertitudes.",
         "Les fourchettes se referment à mesure que le projet se précise — "
         "c'est ce resserrement que le maître d'ouvrage regarde."),
        ("Parcourez la frise de maîtrise d'œuvre et repérez la première phase "
         "non franchissable.",
         "Elle vous dit exactement ce qui manque, sans avoir à l'inventorier "
         "à la main."),
        ("Ouvrez la phase courante et lisez le registre : les pièces sont "
         "groupées par type, chacune avec son émetteur et son contenu exigé.",
         "Un plan de production documentaire daté, et non une liste de bonnes "
         "intentions."),
        ("Regardez les correspondances : un projet mené en EPCI n'attend pas "
         "les mêmes pièces au même moment.",
         "Les accords faibles sont signalés — ce sont eux qui font les "
         "malentendus d'interface."),
        ("Lisez les limites avant de contractualiser sur ce cadre.",
         "Le registre relève de l'usage professionnel, pas d'un texte "
         "opposable : la nuance se dit avant, pas après."),
    ],
    "discipline": [
        ("Renseignez la puissance et, si vous les connaissez, les paramètres "
         "de votre discipline — ils remplacent les valeurs par défaut.",
         "Le calcul travaille alors sur vos hypothèses, pas sur des moyennes."),
        ("Choisissez la phase où vous êtes attendu. Le niveau d'émission de "
         "votre spécification en dépend.",
         "« Première émission » et « gel contractuel » n'engagent pas la même "
         "chose sous le même intitulé."),
        ("Dans le registre, repérez votre spécification : elle porte son "
         "niveau, son contenu exigé et les autres phases où elle revient.",
         "Vous produisez UN document indicé, pas trois documents distincts."),
        ("Vérifiez à quelle phase de l'autre filière votre spécification "
         "tombe : les interfaces se jouent là.",
         "Une discipline qui livre au bon moment dans la mauvaise filière "
         "livre en retard."),
        ("Lisez ce que le moteur ne calcule pas dans votre discipline.",
         "Ce qui n'est pas alimenté par le calcul devra venir de vous — "
         "autant le savoir avant."),
    ],
    "acheteur": [
        ("Renseignez le profil aussi complètement que possible : une "
         "consultation se prépare sur des hypothèses tenues.",
         "Les incertitudes affichées deviennent les tolérances que vous "
         "négocierez."),
        ("Allez jusqu'à la phase de consultation. Les exigences y sont "
         "cumulées depuis le début de la séquence.",
         "Rien de ce qui a été arrêté plus tôt ne redevient ouvert — c'est "
         "précisément ce qui rend un dossier consultable."),
        ("Lisez la précision attendue et sa classe d'estimation avant "
         "d'ouvrir le registre.",
         "Elle vous dit quelle tolérance est défendable, et à partir de quand "
         "une pénalité repose sur autre chose qu'un ordre de grandeur."),
        ("Regardez la colonne EPCI : en contrat industriel, la responsabilité "
         "de la conception de détail change de côté.",
         "Ce déplacement de frontière est ce qui distingue les deux montages, "
         "bien plus que le vocabulaire."),
        ("Lisez les limites : le pourcentage de tolérance de MOE n'est pas "
         "fixé par la loi.",
         "Ce qui relève de l'usage se négocie ; le présenter comme "
         "réglementaire ferme une discussion qui devait rester ouverte."),
    ],
    "exploitant": [
        ("Renseignez le profil tel qu'il sera exploité, pas tel qu'il a été "
         "vendu — charge réelle comprise.",
         "L'écart entre les deux est la première source de dérive après mise "
         "en service."),
        ("Allez jusqu'à la réception, ou à la mise en service en filière "
         "industrielle.",
         "C'est là que le dossier vous est remis, et là qu'il est trop tard "
         "pour demander ce qui n'a pas été prévu."),
        ("Dans le registre, cherchez les pièces au niveau « tel que "
         "construit » et les points de comptage.",
         "Sans comptage installé, aucune consommation par poste ne se "
         "vérifie : elle reste une hypothèse de conception."),
        ("Comparez avec la mise en service industrielle : les essais de "
         "performance n'y portent pas sur les mêmes objets.",
         "Vous saurez quoi réclamer selon le montage choisi."),
        ("Lisez les limites : le moteur donne des ordres de grandeur, pas des "
         "garanties de performance.",
         "Une garantie se mesure sur site ; elle ne se déduit pas d'un "
         "référentiel."),
    ],
}


def _pluriel(n, singulier, pluriel):
    """« 1 pièce », « 3 pièces » — et jamais « 1 pièces ».

    Le défaut paraît vétilleux ; il ne l'est pas. Un compte mal accordé dans un
    document remis à un client est la première chose qu'on remarque, et elle
    jette le doute sur tout le reste.
    """
    return "%d %s" % (n, pluriel if n > 1 else singulier)


def _role_guide(rid):
    for r in ROLES_GUIDE:
        if r["id"] == rid:
            return r
    return None


def _theme_guide(tid):
    for t in THEMES_GUIDE:
        if t["id"] == tid:
            return t
    return None


def guide(role_id, theme_id, profil=None, code_phase=None):
    """Le parcours d'un rôle sur un thème, avec ce que le registre en dit.

    Renvoie None si le rôle ou le thème est inconnu : une combinaison mal
    orthographiée doit échouer, pas produire un parcours plausible qui ne
    correspond à rien.

    Les CHIFFRES sont recalculés sur le registre à chaque appel. C'est le point
    de la conception : trente croisements rédigés à la main diraient bientôt
    autre chose que le registre qu'ils décrivent, et personne ne s'en
    apercevrait — un texte ne se dément pas tout seul.
    """
    r = _role_guide(role_id)
    t = _theme_guide(theme_id)
    if not r or not t:
        return None
    profil = dict(profil or {})
    fil = r["filiere"]
    # La phase de travail : celle que l'utilisateur regarde si elle appartient
    # à la filière du rôle, sinon la première phase clé du rôle qui existe.
    connues = {p["code"]: p for p in PHASES}
    ph = code_phase if code_phase in connues else None
    if not ph or connues[ph]["filiere"] != fil:
        ph = next((c for c in r["phases_cles"] if c in connues), None)
    if not ph:
        ph = next(p["code"] for p in PHASES if p["filiere"] == fil)

    # ── Le croisement, calculé ────────────────────────────────────────────
    # Les pièces de la phase qui relèvent des disciplines du thème, et la part
    # que le calcul alimente. Rien de tout cela n'est écrit : si une pièce est
    # ajoutée demain à la discipline « extinction », le thème « eau » la
    # comptera sans qu'on y touche.
    sup = set(t.get("pieces_sup") or [])

    def _du_theme(p):
        return p.get("discipline") in t["disciplines"] or p["code"] in sup

    du_theme = [p for p in pieces(ph) if _du_theme(p)]
    alimentees = [p for p in du_theme if p.get("moteur")]
    # Ce que le thème représente sur l'ENSEMBLE du projet. On compte les
    # occurrences et les phases, pas les documents distincts : ce dernier
    # chiffre valait le même que celui de la phase courante et se lisait comme
    # une contradiction — « 6 ici, 6 en tout » ne dit rien de plus.
    occurrences, phases_concernees = 0, set()
    for q in PHASES:
        n = sum(1 for p in pieces(q["code"]) if _du_theme(p))
        occurrences += n
        if n:
            phases_concernees.add(q["code"])
    d = dossier(profil, ph) if profil.get("puissance_it_kw") else {}
    # Les postes du thème et leur état à cette phase : recevable, ou remplacé.
    postes_etat = []
    # Hissé : exigences(ph) refait deux cumuls triés à chaque appel, pour un
    # résultat invariant dans cette boucle. Ne pas muter — d'autres l'utilisent.
    subs = set(exigences(ph).get("substitutions") or [])
    for cle in t["postes"]:
        v = POSTES.get(cle)
        if not v:
            continue
        substitue = cle in subs
        postes_etat.append({
            "cle": cle, "nom": v["nom"],
            "incertitude": v.get("incertitude") or "",
            "incertitude_absente": bool(v.get("incertitude_absente")),
            "substitue": substitue,
            "remplacer_par": v.get("remplacer_par") or "",
        })
    grandeurs_bloquees = [g["nom"] for g in (d.get("grandeurs") or [])
                          if g.get("statut") != "recevable"]

    etapes = []
    for i, e in enumerate(_ETAPES_PAGE):
        faire, gain = _CONSIGNES[r["id"]][i]
        chiffres = []
        if e["ancre"] == "ig-parcours":
            chiffres.append("Filière %s · phase de travail %s"
                            % (FILIERES[fil]["nom"], ph))
        if e["ancre"] == "ig-dossier":
            chiffres.append(_pluriel(len(du_theme),
                                     "pièce de ce thème à cette phase",
                                     "pièces de ce thème à cette phase"))
            if du_theme:
                chiffres.append("%d alimentée%s par le calcul"
                                % (len(alimentees),
                                   "s" if len(alimentees) > 1 else ""))
            chiffres.append("%d au long du projet, sur %s"
                            % (occurrences,
                               _pluriel(len(phases_concernees), "phase", "phases")))
            if grandeurs_bloquees:
                chiffres.append(_pluriel(len(grandeurs_bloquees),
                                         "grandeur à produire ailleurs",
                                         "grandeurs à produire ailleurs"))
        if e["ancre"] == "ig-correspondances":
            autre = "indus" if fil == "moe" else "moe"
            chiffres.append("À rapprocher de la filière %s"
                            % FILIERES[autre]["nom"])
        etapes.append({
            "n": i + 1, "ancre": e["ancre"], "section": e["section"],
            "titre": e["titre"], "faire": faire, "gain": gain,
            "chiffres": chiffres,
        })

    return {
        "role": {k: r[k] for k in ("id", "couleur", "icone", "nom", "question",
                                   "cherche", "fin")},
        "theme": {k: t[k] for k in ("id", "couleur", "icone", "nom", "question",
                                    "piege")},
        # Le conseil de la phase de travail, remonté au parcours : c'est
        # l'accompagnement demandé — un mot au moment où l'on y est.
        "conseil": CONSEILS_PHASE.get(ph),
        "filiere": fil, "filiere_nom": FILIERES[fil]["nom"],
        "phase": ph, "phase_nom": connues[ph]["nom"],
        "etapes": etapes,
        "disciplines": [{"cle": c, "nom": _nom_discipline(c)}
                        for c in t["disciplines"]],
        "postes": postes_etat,
        "pieces_du_theme": [{"code": p["code"], "titre": p["titre"],
                             "discipline_nom": p["discipline_nom"],
                             "niveau_nom": p.get("niveau_nom") or "",
                             "moteur": bool(p.get("moteur"))}
                            for p in du_theme],
        "occurrences_projet": occurrences,
        "phases_concernees": sorted(phases_concernees),
        "profil_renseigne": bool(profil.get("puissance_it_kw")),
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
            # `defaut_nom` n'est servi QUE pour les champs qui s'appliquent
            # faute de choix. La page s'en sert pour nommer l'option vide :
            # « non précisé » sur un champ qui agit quand même ferait croire à
            # une absence là où il y a une valeur — et c'est justement le
            # défaut qu'on vient de corriger sur la mission.
            {"id": c["id"], "label": c["label"], "aide": c["aide"],
             "defaut_nom": (MISSIONS[MISSION_DEFAUT]["nom"]
                            if c["id"] == "mission" else ""),
             "options": [{"cle": k, "nom": v["nom"], "implique": v["implique"]}
                         for k, v in c["options"].items()]}
            for c in IDENTIFICATION],
        "identification_note": IDENTIFICATION_NOTE,
        # Le fil des gestes : la page rend la séquence, elle ne la réécrit pas.
        # Une séquence dupliquée dans du JavaScript se contredit au premier
        # écran ajouté, et c'est celle de l'écran que le lecteur suivrait.
        "gestes": gestes_referentiel(),
        # Le référentiel de disponibilité : les niveaux, les schémas et leur
        # ordre. Le CALCUL du nombre d'unités n'y figure pas — il dépend du
        # besoin saisi et se demande à `disponibilite()`, qui distingue ce que
        # le référentiel exige de ce que l'arithmétique installe.
        "disponibilite": {
            "niveaux": NIVEAUX_TIER,
            "niveaux_ordre": ["I", "II", "III", "IV"],
            "tier_source": TIER_SOURCE,
            "classes_en50600": CLASSES_EN50600,
            "en50600_source": EN50600_SOURCE,
            "schemas": REDONDANCES,
            "schemas_ordre": sorted(REDONDANCES,
                                    key=lambda k: REDONDANCES[k]["rang"]),
        },
        # Le parcours guidé : les rôles et les thèmes sont servis, la page ne
        # les réécrit pas. Le CROISEMENT, lui, se demande — il se calcule sur
        # le profil et la phase courants et n'aurait aucun sens figé ici.
        "guide_roles": [{k: r[k] for k in ("id", "couleur", "icone", "nom",
                                           "question", "cherche")}
                        for r in ROLES_GUIDE],
        "guide_themes": [{k: t[k] for k in ("id", "couleur", "icone", "nom",
                                            "question")}
                         for t in THEMES_GUIDE],
        # Le conseil de phase, servi avec le cadre : la frise l'affiche au
        # survol. Écrit au référentiel et non dans la page — un conseil recopié
        # dans le HTML cesse de suivre la phase qu'il commente.
        "conseils_phase": CONSEILS_PHASE,
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

    # Le vocabulaire de recherche. Une spécification de discipline ajoutée sans
    # le sien retomberait sur celui de sa discipline — ce qui MARCHE, mais ne
    # distingue plus la chaleur fatale du bâtiment bas carbone, tous deux
    # « environnement ». Le filet évite la panne, il ne dispense pas d'écrire.
    specs_sans_vocabulaire = sorted(
        e[0] for e in _PIECES_DISCIPLINE if e[0] not in _RECHERCHE_PIECE)
    # Et le vocabulaire déclaré doit être CHERCHABLE : une recherche vidée par
    # les mots-outils ne ramènerait rien.
    vocabulaires_creux = sorted(
        c for c, v in _RECHERCHE_PIECE.items() if len(v.split()) < 6)
    disciplines_sans_repli = sorted(set(DISCIPLINES) - set(_RECHERCHE_DISCIPLINE))

    # Le fil des gestes. Quatre façons de le casser en silence : un geste sans
    # cible pointerait dans le vide ; un geste qui n'annonce pas ce qu'il
    # DÉCLENCHE ferait cliquer sans comprendre ; deux gestes sur le même état
    # rendraient le second inatteignable ; un préalable qu'aucun geste ne
    # produit bloquerait le fil pour toujours.
    gestes_sans_cible = sorted(g["id"] for g in GESTES
                               if not (g.get("cible") or "").strip()
                               or not (g.get("ancre") or "").strip())
    gestes_muets = sorted(g["id"] for g in GESTES
                          if len((g.get("texte") or "").strip()) < 40
                          or len((g.get("apres") or "").strip()) < 40
                          or not (g.get("titre") or "").strip())
    vus_ = {}
    for g in GESTES:
        vus_.setdefault(g["fait_si"], []).append(g["id"])
    gestes_etat_partage = sorted("%s:%s" % (k, ",".join(v))
                                 for k, v in vus_.items() if len(v) > 1)
    produits_ = {g["fait_si"] for g in GESTES}
    gestes_prealable_orphelin = sorted(
        "%s:%s" % (g["id"], k) for g in GESTES for k in g["exige"]
        if k not in produits_)
    # Et le fil doit ABOUTIR : parcouru en accomplissant chaque geste, il doit
    # se terminer. Un fil qui boucle laisserait le lecteur tourner sans fin.
    _e, _vus, gestes_boucle = {}, [], []
    for _ in range(len(GESTES) + 2):
        _g = prochain_geste(_e)
        if not _g:
            break
        if _g["id"] in _vus:
            gestes_boucle = [_g["id"]]
            break
        _vus.append(_g["id"])
        _e[_g["fait_si"]] = True
    else:
        gestes_boucle = ["fil non terminé"]
    gestes_inatteignables = sorted({g["id"] for g in GESTES} - set(_vus))

    # Le parcours guidé. Trois façons de le casser en silence : nommer une
    # pièce qui n'existe pas, nommer une discipline inconnue, ou définir un
    # thème dont le périmètre ne ramène rien — l'utilisateur choisirait alors
    # un thème vide sans qu'aucune erreur ne se produise.
    codes_connus = {x["code"] for q in PHASES for x in pieces(q["code"])}
    guide_pieces_inconnues, guide_disciplines_inconnues, guide_themes_vides = [], [], []
    for t_ in THEMES_GUIDE:
        guide_pieces_inconnues += sorted(
            "%s:%s" % (t_["id"], c) for c in (t_.get("pieces_sup") or [])
            if c not in codes_connus)
        guide_disciplines_inconnues += sorted(
            "%s:%s" % (t_["id"], c) for c in t_["disciplines"]
            if c not in DISCIPLINES)
        sup_ = set(t_.get("pieces_sup") or [])
        n_ = sum(1 for q in PHASES for x in pieces(q["code"])
                 if x.get("discipline") in t_["disciplines"] or x["code"] in sup_)
        if not n_:
            guide_themes_vides.append(t_["id"])
    # Chaque rôle doit porter une consigne par section de la page, sinon le
    # parcours lèverait une IndexError au premier affichage.
    guide_roles_incomplets = sorted(
        r_["id"] for r_ in ROLES_GUIDE
        if len(_CONSIGNES.get(r_["id"], [])) != len(_ETAPES_PAGE))
    guide_postes_inconnus = sorted(
        "%s:%s" % (t_["id"], c) for t_ in THEMES_GUIDE
        for c in t_["postes"] if c not in POSTES)
    # Le conseil de phase et la couleur d'identité : deux ajouts qui se
    # dégradent en silence. Une phase sans conseil rend une infobulle plus
    # pauvre que les autres sans que rien ne le signale ; deux rôles de même
    # couleur ne s'identifient plus, et c'est toute la raison d'être de la
    # couleur.
    phases_sans_conseil = sorted(p_["code"] for p_ in PHASES
                                 if p_["code"] not in CONSEILS_PHASE)
    conseils_orphelins = sorted(c for c in CONSEILS_PHASE
                                if c not in {p_["code"] for p_ in PHASES})
    conseils_creux = sorted(
        c for c, v in CONSEILS_PHASE.items()
        if len((v.get("texte") or "")) < 120 or not (v.get("titre") or "").strip())
    _coul = [r_["id"] for r_ in ROLES_GUIDE if not r_.get("couleur")] + \
            [t_["id"] for t_ in THEMES_GUIDE if not t_.get("couleur")]
    _vues = {}
    for x_ in list(ROLES_GUIDE) + list(THEMES_GUIDE):
        _vues.setdefault(x_.get("couleur"), []).append(x_["id"])
    couleurs_partagees = sorted(", ".join(v) for v in _vues.values() if len(v) > 1)

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
        "guide_roles": len(ROLES_GUIDE),
        "guide_themes": len(THEMES_GUIDE),
        "guide_pieces_inconnues": guide_pieces_inconnues,
        "guide_disciplines_inconnues": guide_disciplines_inconnues,
        "guide_themes_vides": guide_themes_vides,
        "guide_roles_incomplets": guide_roles_incomplets,
        "guide_postes_inconnus": guide_postes_inconnus,
        "phases_sans_conseil": phases_sans_conseil,
        "conseils_sur_phase_inexistante": conseils_orphelins,
        "conseils_trop_courts": conseils_creux,
        "guide_sans_couleur": sorted(_coul),
        "guide_couleurs_partagees": couleurs_partagees,
        "specifications_sans_vocabulaire": specs_sans_vocabulaire,
        "vocabulaires_de_recherche_creux": vocabulaires_creux,
        "disciplines_sans_vocabulaire_de_repli": disciplines_sans_repli,
        "glossaire_familles": len(g_),
        "glossaire_definitions": sum(len(v) for v in g_.values()),
        "gestes_sans_cible": gestes_sans_cible,
        "gestes_sans_consequence": gestes_muets,
        "gestes_etat_partage": gestes_etat_partage,
        "gestes_prealable_orphelin": gestes_prealable_orphelin,
        "gestes_boucle": gestes_boucle,
        "gestes_inatteignables": gestes_inatteignables,
        "gestes": len(GESTES),
        "glossaire_sans_explication": glossaire_muet,
        "franchissables_profil_minimal": [
            e["code"] for e in parcours(p, "moe")["etapes"] if e["franchissable"]
        ] + [
            e["code"] for e in parcours(p, "indus")["etapes"] if e["franchissable"]
        ],
        "moteur": D.VERSION,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  LES RÉFÉRENTIELS APPLICABLES À UN CENTRE DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════════
# POURQUOI UNE TABLE. « Conforme aux normes en vigueur » est la formule qui ne
# vaut rien : elle ne dit pas lesquelles, ne se vérifie pas, et se retrouve
# dans tous les CCTP. Un référentiel n'a de portée que nommé, avec ce qu'il
# régit ET ce qu'il n'atteste pas — c'est cette seconde colonne qui évite les
# malentendus les plus coûteux du métier.
#
# DEUX CONFUSIONS QUE CETTE TABLE EXISTE POUR ÉVITER :
#
#   · « Tier III » n'est pas un niveau qu'on s'attribue. C'est une
#     certification délivrée par l'Uptime Institute, distincte selon qu'elle
#     porte sur les documents de conception ou sur l'ouvrage construit. Un
#     dossier « conçu selon les principes Tier III » n'est pas certifié, et
#     l'écrire autrement dans une plaquette est un risque contractuel.
#
#   · Un référentiel de conception ne vaut pas autorisation administrative.
#     Respecter l'EN 50600 ne dispense d'aucun arrêté préfectoral, et une
#     rubrique ICPE se déclare quel que soit le niveau de disponibilité visé.
#
# LES VERSIONS NE SONT PAS FIGÉES ICI. Elles changent, et une version recopiée
# devient fausse sans prévenir. La table nomme le référentiel et sa portée ;
# la pièce de conformité demande, elle, de citer l'indice applicable au projet
# à la date du marché.

REFERENTIELS_DC = {
    "uptime": {
        "nom": "Uptime Institute — Tier Standard",
        "autorite": "Uptime Institute (organisme privé)",
        "portee": "Topologie de redondance des chaînes d'alimentation et de "
                  "refroidissement, et exploitabilité. Quatre niveaux, dont la "
                  "maintenabilité sans interruption et la tolérance à la panne "
                  "unique.",
        "atteste_pas": "Ni la performance énergétique, ni la sécurité incendie, "
                       "ni la conformité réglementaire française. La "
                       "certification porte séparément sur les documents de "
                       "conception et sur l'ouvrage construit : l'une ne vaut "
                       "pas l'autre.",
        "disciplines": ("projet", "design_mgmt", "elec_cfo", "hvac"),
    },
    "tia942": {
        "nom": "ANSI/TIA-942 — infrastructure de télécommunication des centres de données",
        "autorite": "Telecommunications Industry Association",
        "portee": "Aménagement des espaces, câblage structuré, chemins de "
                  "câbles, redondance des liaisons, et classement du site par "
                  "niveaux.",
        "atteste_pas": "Les niveaux de ce texte et ceux de l'Uptime Institute "
                       "ne sont pas les mêmes et ne s'échangent pas : les "
                       "citer indifféremment dans un même dossier est une "
                       "source d'écart au moment de la recette.",
        "disciplines": ("telecom", "elec_cfa", "itot", "design_mgmt"),
    },
    "ashrae": {
        "nom": "ASHRAE TC 9.9 — Thermal Guidelines for Data Processing Environments",
        "autorite": "ASHRAE",
        "portee": "Enveloppes de température et d'humidité admises en salle, "
                  "par classe de matériel. C'est le texte qui fixe jusqu'où "
                  "l'air extérieur peut refroidir sans machine frigorifique.",
        "atteste_pas": "Ce sont des recommandations de bonne pratique, pas une "
                       "obligation. La classe admise est un CHOIX de projet, "
                       "qui engage le constructeur du matériel informatique "
                       "autant que le concepteur.",
        "disciplines": ("hvac", "itot", "environnement", "design_mgmt"),
    },
    "en50600": {
        "nom": "EN 50600 / ISO-IEC 22237 — installations et infrastructures de centres de données",
        "autorite": "CENELEC, transposée à l'international par ISO/IEC",
        "portee": "Série complète : construction, distribution électrique, "
                  "contrôle d'ambiance, câblage, sûreté physique, exploitation, "
                  "et les indicateurs d'efficacité dont le PUE.",
        "atteste_pas": "Une classe de disponibilité y est déclarée par le "
                       "concepteur : ce n'est pas une certification par un "
                       "tiers, contrairement à ce que la ressemblance des "
                       "échelles laisse croire.",
        "disciplines": ("projet", "design_mgmt", "elec_cfo", "hvac",
                        "environnement", "surete", "telecom"),
    },
    "eed": {
        "nom": "Directive européenne sur l'efficacité énergétique — déclaration des centres de données",
        "autorite": "Union européenne, transposition nationale",
        "portee": "Obligation de déclaration annuelle des consommations et des "
                  "indicateurs environnementaux au-delà d'un seuil de puissance "
                  "informatique installée, sur un modèle commun européen.",
        "atteste_pas": "C'est une obligation de DÉCLARER, non un seuil de "
                       "performance à tenir. Elle impose en revanche de savoir "
                       "mesurer, ce qui se prépare au stade de la conception "
                       "du comptage et non à la mise en service.",
        "disciplines": ("environnement", "supervision", "projet", "design_mgmt"),
    },
    "nfc13100": {
        "nom": "NF C 13-100 — postes de livraison raccordés à un réseau public de distribution",
        "autorite": "AFNOR / UTE",
        "portee": "Le poste de livraison HTA alimenté par le distributeur : "
                  "conception, protection, comptage, accès et exploitation.",
        "atteste_pas": "Ne couvre pas les installations privées en aval du "
                       "point de livraison, ni les raccordements au réseau de "
                       "transport.",
        "disciplines": ("elec_cfo",),
    },
    "nfc13200": {
        "nom": "NF C 13-200 — installations électriques à haute tension",
        "autorite": "AFNOR / UTE",
        "portee": "Les installations privées haute tension, du poste de "
                  "livraison jusqu'aux transformateurs : dimensionnement, "
                  "protections, mise à la terre, distances et locaux.",
        "atteste_pas": "Ne se substitue pas aux prescriptions du gestionnaire "
                       "de réseau, qui s'imposent au point de livraison et "
                       "peuvent être plus contraignantes.",
        "disciplines": ("elec_cfo",),
    },
    "nfc15100": {
        "nom": "NF C 15-100 — installations électriques à basse tension",
        "autorite": "AFNOR / UTE",
        "portee": "Toute la distribution basse tension : sections, protections, "
                  "régimes de neutre, sélectivité, canalisations.",
        "atteste_pas": "Les règles d'exploitation et d'intervention sous "
                       "tension relèvent d'un autre texte.",
        "disciplines": ("elec_cfo", "elec_cfa"),
    },
    "nfc18510": {
        "nom": "NF C 18-510 — opérations sur les ouvrages et installations électriques",
        "autorite": "AFNOR",
        "portee": "Habilitations, consignations, zones d'environnement et "
                  "distances de sécurité. C'est ce texte qui définit les "
                  "domaines de tension — dont la frontière entre HTA et HTB.",
        "atteste_pas": "Ne dit rien de la conception : c'est un texte "
                       "d'exploitation, qui contraint pourtant le design par "
                       "les accès et les dégagements qu'il impose.",
        "disciplines": ("elec_cfo", "safety", "projet"),
    },
    "cei60909": {
        "nom": "CEI 60909 — calcul des courants de court-circuit",
        "autorite": "Commission électrotechnique internationale",
        "portee": "La méthode de calcul des courants de court-circuit sur "
                  "laquelle s'appuient le choix des matériels et le plan de "
                  "protection.",
        "atteste_pas": "Une méthode de calcul, pas un niveau de performance : "
                       "ce sont les hypothèses retenues qui font la valeur du "
                       "résultat, et elles doivent être écrites.",
        "disciplines": ("elec_cfo",),
    },
    "iso8528": {
        "nom": "ISO 8528 — groupes électrogènes entraînés par moteur à combustion",
        "autorite": "Organisation internationale de normalisation",
        "portee": "Classes de performance, régimes d'utilisation et conditions "
                  "de déclaration de puissance. C'est ce qui distingue une "
                  "puissance de secours d'une puissance continue.",
        "atteste_pas": "Ne traite ni du stockage du combustible, ni des rejets "
                       "atmosphériques, ni du bruit — trois sujets qui relèvent "
                       "de la réglementation des installations classées.",
        "disciplines": ("elec_cfo", "environnement"),
    },
    "icpe": {
        "nom": "Installations classées pour la protection de l'environnement",
        "autorite": "Préfecture, sur nomenclature nationale",
        "portee": "Régime applicable au site selon les rubriques atteintes — "
                  "notamment les batteries d'accumulateurs, les moteurs de "
                  "secours, le stockage de combustible et les fluides "
                  "frigorigènes.",
        "atteste_pas": "Une rubrique se déclare quel que soit le niveau de "
                       "disponibilité visé, et le délai d'instruction ne se "
                       "négocie pas : c'est un jalon de planning, pas une "
                       "formalité de fin de chantier.",
        "disciplines": ("environnement", "safety", "elec_cfo", "projet",
                        "design_mgmt"),
    },
}


def referentiels(discipline=None):
    """Les référentiels applicables, filtrés sur une discipline s'il y a lieu.

    Rendus dans l'ordre de la table, qui va du cadre de conception au cadre
    réglementaire : c'est l'ordre dans lequel on les ouvre sur un projet.
    """
    out = []
    for cle, r in REFERENTIELS_DC.items():
        if discipline and discipline not in r["disciplines"]:
            continue
        out.append(dict(r, cle=cle))
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  LA LISTE DES DOCUMENTS DU PROJET
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE C'EST. Sur un projet d'ingénierie, la liste des documents — la LDD —
# est elle-même une pièce contractuelle. Elle dit ce qui existe, à quel indice,
# émis par qui, pour quelle phase, et à quel titre chacun engage. C'est le
# document qu'ouvre en premier un bureau de contrôle, un repreneur d'affaire ou
# un exploitant six mois après la livraison.
#
# POURQUOI ELLE NE SE CONFOND PAS AVEC LE DOSSIER. Le dossier du projet porte
# TOUT ce qui a été produit, brouillons compris — c'est un plan de travail. La
# liste, elle, ne porte que ce qui a été VISÉ : elle engage. Y verser un
# brouillon ferait figurer au registre contractuel un document que personne n'a
# relu, et c'est la faute qui coûte le plus cher, parce qu'on ne la découvre
# qu'au moment où quelqu'un s'en prévaut.
#
# CE QUI RESTE DEHORS EST DIT. La liste annonce le nombre de documents encore
# au brouillon et à la relecture : un registre qui tairait leur existence
# laisserait croire le dossier complet.

ETATS_ENGAGEANTS = ("vise",)


def liste_documents(projet, livrables, etats=None):
    """Le registre contractuel des documents visés d'un projet, en Markdown.

    `livrables` : les enregistrements du magasin d'historique, tels quels.
    `etats` : le vocabulaire des états, pour les nommer — lu au référentiel des
    projets et non recopié ici, sans quoi les deux auraient divergé.

    Renvoie None si aucun document n'est visé : une liste vide n'est pas un
    registre, c'est un document qui ferait croire qu'il n'y a rien à attendre.
    """
    etats = etats or {}
    tous = list(livrables or [])
    vises = [x for x in tous if (x.get("etat") or "") in ETATS_ENGAGEANTS]
    if not vises:
        return None

    nom_projet = (projet or {}).get("nom") or "projet sans nom"
    client = (projet or {}).get("client") or ""
    rang = {p["code"]: p["rang"] for p in PHASES}
    noms_phase = {p["code"]: p["nom"] for p in PHASES}

    L = []
    A = L.append
    A("# Liste des documents — %s" % nom_projet)
    A("")
    A("Registre des documents visés du projet%s, arrêté le %s."
      % ((", pour %s" % client) if client else "", time.strftime("%d/%m/%Y")))
    A("")
    A("> **Ce registre ne porte que les documents visés.** Un document au "
      "brouillon ou en relecture n'engage personne et n'a pas sa place ici ; "
      "le dossier du projet, lui, les porte tous.")
    A("")

    A("## 1. Ce que porte ce registre")
    A("")
    A("| Rubrique | Valeur |")
    A("| --- | --- |")
    A("| Projet | **%s** |" % nom_projet)
    if client:
        A("| Client | **%s** |" % client)
    A("| Documents visés | **%d** |" % len(vises))
    for cle in ("relu", "brouillon"):
        n = len([x for x in tous if (x.get("etat") or "brouillon") == cle])
        if n:
            A("| Non encore visés, à l'état « %s » | %d |"
              % ((etats.get(cle) or {}).get("nom", cle).lower(), n))
    A("| Phases représentées | %d |"
      % len({(x.get("phase") or "—") for x in vises}))
    A("| Arrêté le | %s |" % time.strftime("%d/%m/%Y"))
    A("| Établi par | Moteur d'ingénierie CONSEILPREV %s |" % VERSION)
    A("")

    # PAR PHASE, dans l'ordre de la séquence — et non par date. Un registre se
    # lit en suivant l'avancement du projet ; trié par date de production, il
    # mélangerait une note d'esquisse reprise tardivement avec les pièces du
    # dossier de consultation.
    par_phase = {}
    for x in vises:
        par_phase.setdefault(x.get("phase") or "—", []).append(x)
    n = 2
    for code in sorted(par_phase, key=lambda c: (rang.get(c, 999), c)):
        items = par_phase[code]
        A("## %d. Phase %s — %s"
          % (n, code, noms_phase.get(code, "hors phase")))
        A("")
        A("| Numéro | Indice | Intitulé | Discipline | Émetteur | Visé le |")
        A("| --- | --- | --- | --- | --- | --- |")
        for x in sorted(items, key=lambda r: (r.get("numero") or "",
                                              r.get("label") or "")):
            pc = piece(x.get("phase") or "", x.get("piece") or "") or {}
            A("| %s | %s | %s | %s | %s | %s |"
              % (x.get("numero") or x.get("piece") or "—",
                 x.get("indice") or "01",
                 x.get("label") or x.get("type") or "document",
                 pc.get("discipline_nom") or _nom_discipline(pc.get("discipline"))
                 or "—",
                 pc.get("emetteur_nom") or "—",
                 _jour(x.get("vise_at") or x.get("created_at"))))
        A("")
        # CE QUE CETTE PHASE GÈLE. Un registre qui ne dirait pas quelles pièces
        # deviennent opposables à la phase où elles sont visées laisserait
        # croire que tout reste modifiable.
        geles = [x for x in items
                 if (piece(x.get("phase") or "", x.get("piece") or "") or {})
                 .get("gel")]
        if geles:
            A("Gelées à cette phase, donc opposables en l'état : %s."
              % ", ".join(sorted({x.get("numero") or x.get("piece") or "?"
                                  for x in geles})))
            A("")
        n += 1

    A("## %d. Ce que ce registre n'atteste pas" % n)
    A("")
    A("Le visa porte sur le contenu du document à la date où il a été donné. "
      "Il ne vaut pas réception des ouvrages, ni conformité d'exécution, ni "
      "quitus sur les phases suivantes.")
    A("")
    manquants = len(tous) - len(vises)
    if manquants:
        A("**%d document%s du dossier ne figure%s pas ici**, faute de visa. "
          "Le dossier du projet les porte, à leur état."
          % (manquants, "s" if manquants > 1 else "",
             "nt" if manquants > 1 else ""))
        A("")
    return "\n".join(L)


def _jour(ts):
    """Une date lisible depuis un horodatage, ou un tiret."""
    try:
        return time.strftime("%d/%m/%Y", time.localtime(float(ts)))
    except (TypeError, ValueError):
        return "—"
