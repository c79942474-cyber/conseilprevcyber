# -*- coding: utf-8 -*-
"""L'état de l'art — ce qui est publié, par qui, et ce que cela vaut.

POURQUOI CE MODULE EXISTE À CÔTÉ DU MOTEUR

Le moteur calcule à partir de constantes normatives. Il ne dit rien du marché :
ni la densité que prennent les baies d'IA, ni la part que le refroidissement
occupe dans une facture, ni les moratoires qui ferment des territoires entiers à
la construction. Ces faits-là décident pourtant d'un projet avant tout calcul —
et ils ne se déduisent d'aucune formule. Ils se CITENT.

LA RÈGLE QUI GOUVERNE CE FICHIER, ET ELLE EST LA SEULE QUI COMPTE

Un fait sans son auteur n'est pas un fait, c'est une rumeur. Chaque valeur
portée ici cite sa source, sa page et — c'est le point — la NATURE de cette
source. Trois des quatre documents versés sont publiés par des fournisseurs
d'infrastructure ; leurs chiffres sont utiles et leur intérêt n'est pas neutre.
Les afficher au même rang qu'une analyse indépendante tromperait le lecteur, et
un dossier bâti là-dessus se ferait démonter à la première contradiction.

CE QUE CE MODULE NE FAIT PAS

Il ne moyenne rien, ne consolide rien, ne conclut rien. Deux sources qui se
contredisent restent deux lignes contradictoires — la contradiction est
l'information. Et il ne verse aucun de ces chiffres dans le calcul : le moteur
tient ses constantes de normes, pas de livres blancs.

UNE MISE AU POINT QUI S'IMPOSE

Le fichier « DATA_CENTER_LCA » n'est PAS une analyse de cycle de vie. C'est un
guide de sélection de prestataire publié par Honeywell ; le sigle du nom de
fichier renvoie au « lifecycle » du projet, pas à l'ACV environnementale au sens
d'ISO 14040. Le lecteur qui l'appellerait « l'ACV » citerait dans un dossier une
source qui n'en est pas une. C'est écrit ici pour que personne ne s'y trompe.
"""
from datetime import datetime, timezone

VERSION = "2026-08-a"

# ═══════════════════════════════════════════════════════════════════════════
#  CE QUE VAUT UNE SOURCE — trois natures, et ce qu'on peut en faire
# ═══════════════════════════════════════════════════════════════════════════

NATURES = {
    "analyse_editeur": {
        "nom": "Analyse d'éditeur",
        "poids": "Cabinet d'analyse, sans matériel à vendre sur ce marché. "
                 "Citable dans un dossier ; les projections restent des "
                 "projections, et l'éditeur donne lui-même sa fourchette.",
    },
    "livre_blanc_fournisseur": {
        "nom": "Livre blanc de fournisseur",
        "poids": "Publié par un vendeur d'infrastructure. Les mesures "
                 "techniques y sont généralement fiables — il les tient de ses "
                 "propres déploiements — mais la sélection des faits sert une "
                 "offre. À citer en nommant l'auteur, jamais comme une source "
                 "neutre.",
    },
    "guide_fournisseur": {
        "nom": "Guide de sélection de prestataire",
        "poids": "Document commercial : il énonce les critères selon lesquels "
                 "son auteur souhaite être choisi. Utile comme grille de "
                 "questions, sans valeur probante sur un chiffre.",
    },
}

# ═══════════════════════════════════════════════════════════════════════════
#  LES QUATRE DOCUMENTS
# ═══════════════════════════════════════════════════════════════════════════

SOURCES = {
    "deloitte2024": {
        "titre": "Durabilité des centres de données — l'IA générative et la "
                 "consommation d'électricité",
        "editeur": "Deloitte, Centre pour la technologie, les médias et les "
                   "télécommunications",
        "date": "19 novembre 2024",
        "nature": "analyse_editeur",
        "note": "La seule des quatre qui traite la durabilité pour elle-même. "
                "C'est aussi la seule qui donne ses hypothèses ET son scénario "
                "défavorable, ce qui permet de la contredire.",
    },
    "penguin_five": {
        "titre": "Five Critical Design Considerations for AI Infrastructure",
        "editeur": "Penguin Solutions",
        "date": "juillet 2025",
        "nature": "livre_blanc_fournisseur",
        "note": "Le plus utile des trois documents fournisseurs pour la "
                "conception : il chiffre la puissance des baies par génération "
                "de calculateur, ce qui commande tout le reste.",
    },
    "penguin_efficient": {
        "titre": "Efficient Infrastructure Design Underpins AI Factory Success",
        "editeur": "Penguin Solutions",
        "date": "août 2025",
        "nature": "livre_blanc_fournisseur",
        "note": "Essentiellement stratégique et commercial. Ses chiffres portent "
                "sur le MARCHÉ de l'IA, pas sur l'empreinte des installations : "
                "rien n'y alimente un calcul d'énergie, d'eau ou de carbone.",
    },
    "honeywell_cycle": {
        "titre": "Selecting a Data Center Lifecycle Solution Provider",
        "editeur": "Honeywell",
        "date": "sans millésime imprimé",
        "nature": "guide_fournisseur",
        "note": "MISE AU POINT NÉCESSAIRE : malgré le sigle « LCA » du nom de "
                "fichier, ce document n'est PAS une analyse de cycle de vie au "
                "sens d'ISO 14040. « Lifecycle » y désigne le cycle du PROJET — "
                "conception, intégration, exploitation, maintenance. Sa matière "
                "environnementale tient en une page et reste qualitative.",
    },
}

# ═══════════════════════════════════════════════════════════════════════════
#  LES FAITS — chacun avec sa source, sa page, et ce qu'il touche ICI
#
#  `touche` désigne le paramètre du moteur que le fait éclaire. C'est ce qui
#  distingue une revue de presse d'un état de l'art utile : on ne cite que ce
#  qui change une décision de conception, et on dit laquelle.
# ═══════════════════════════════════════════════════════════════════════════

FAITS = [
    # ── Ce que pèse le parc, et vers quoi il va ────────────────────────────
    {"cle": "part_mondiale", "famille": "trajectoire",
     "enonce": "Les centres de données représenteraient environ 2 % de la "
               "consommation mondiale d'électricité en 2025, soit 536 TWh.",
     "source": "deloitte2024", "page": 1, "touche": None},
    {"cle": "doublement_2030", "famille": "trajectoire",
     "enonce": "Cette consommation pourrait doubler pour atteindre environ "
               "1 065 TWh en 2030 — et dépasser 1 300 TWh si les gains "
               "d'efficacité attendus ne se matérialisent pas.",
     "source": "deloitte2024", "page": 1, "touche": None,
     "reserve": "L'éditeur donne les deux branches. Retenir la basse sans la "
                "haute serait choisir la nouvelle qui arrange."},
    {"cle": "marche_ia", "famille": "trajectoire",
     "enonce": "La dépense mondiale en IA atteindrait 632 milliards de dollars "
               "en 2028, en croissance de 29 % par an (IDC, cité).",
     "source": "penguin_efficient", "page": 3, "touche": None,
     "reserve": "Ce chiffre mesure un MARCHÉ, pas une empreinte. Il explique "
                "pourquoi la question se pose maintenant ; il ne dit rien de ce "
                "que consommera l'installation. C'est le seul apport de ce "
                "document à une lecture de durabilité — le reste y est "
                "stratégique et commercial."},
    {"cle": "irlande", "famille": "territoire",
     "enonce": "En Irlande, les centres de données consomment déjà un cinquième "
               "de l'électricité du pays. Le raccordement de nouveaux sites y a "
               "été suspendu, puis la position a été revue.",
     "source": "deloitte2024", "page": 5, "touche": "pays"},
    {"cle": "amsterdam", "famille": "territoire",
     "enonce": "Amsterdam a suspendu la construction de nouveaux centres de "
               "données au nom du développement urbain durable.",
     "source": "deloitte2024", "page": 5, "touche": "pays"},
    {"cle": "singapour_26", "famille": "territoire",
     "enonce": "Singapour impose de relever progressivement la température "
               "d'exploitation à 26 °C ou plus. Moins de froid à produire, donc "
               "moins d'électricité — au prix d'une durée de vie des puces "
               "raccourcie.",
     "source": "deloitte2024", "page": 5, "touche": "classe_ashrae",
     "reserve": "L'arbitrage est explicite dans la source : le gain d'énergie "
                "se paie en renouvellement matériel, donc en carbone incorporé "
                "— que ce moteur ne chiffre pas."},

    # ── Où part l'électricité, dans le bâtiment ────────────────────────────
    {"cle": "repartition", "famille": "energie",
     "enonce": "Répartition de la consommation d'un centre : serveurs environ "
               "40 %, refroidissement 38 à 40 %, conditionnement d'énergie 8 à "
               "10 %, réseau et stockage environ 5 % chacun, éclairage 1 à 2 %.",
     "source": "deloitte2024", "page": 3, "touche": "refroidissement"},
    {"cle": "air_40", "famille": "energie",
     "enonce": "Le refroidissement à air seul peut représenter jusqu'à 40 % de "
               "la consommation électrique d'un centre.",
     "source": "deloitte2024", "page": 6, "touche": "refroidissement"},
    {"cle": "liquide_90", "famille": "energie",
     "enonce": "Le refroidissement liquide permettrait de réduire cette "
               "consommation jusqu'à 90 % par rapport à l'air, et de supporter "
               "des baies de 50 à 100 kW ou davantage — en supprimant "
               "éventuellement les groupes froids.",
     "source": "deloitte2024", "page": 6, "touche": "refroidissement",
     "reserve": "La même source ajoute que la technologie reste peu déployée à "
                "l'échelle mondiale. Un chiffre de laboratoire n'est pas un "
                "retour d'exploitation."},

    {"cle": "sur_sous_refroidir", "famille": "energie",
     "enonce": "Le réglage juste est un équilibre : ne pas sous-refroidir, et "
               "ne pas gaspiller non plus. Une gestion technique de bâtiment "
               "pilotant le froid et la ventilation agit directement sur le "
               "PUE, et la chaleur fatale valorisée réduit à la fois la facture "
               "et l'empreinte carbone.",
     "source": "honeywell_cycle", "page": 8,
     "touche": "part_chaleur_reutilisee",
     "reserve": "QUALITATIF. Ce document n'avance aucun chiffre à l'appui, et "
                "c'est le seul passage environnemental de ses quatorze pages. "
                "À prendre comme un rappel de conception, pas comme une mesure."},

    # ── La densité, qui commande tout le reste ─────────────────────────────
    {"cle": "baies_kw", "famille": "densite",
     "enonce": "Puissance par baie selon la génération : baie d'entreprise "
               "8,6 kW ; A100 à deux nœuds 13 kW ; H100 à deux nœuds 22 kW ; "
               "H100 à quatre nœuds 44 kW ; baie B200 57 kW.",
     "source": "penguin_five", "page": 13, "touche": "puissance_it_kw"},
    {"cle": "densite_moyenne", "famille": "densite",
     "enonce": "La densité moyenne passerait de 36 kW par baie en 2023 à 50 kW "
               "en 2027.",
     "source": "deloitte2024", "page": 4, "touche": "puissance_it_kw"},
    {"cle": "puces_watts", "famille": "densite",
     "enonce": "Puissance par puce : 150 à 200 W pour un processeur classique ; "
               "400 W pour un accélérateur jusqu'en 2022 ; 700 W en 2023 ; "
               "1 200 W attendus pour la génération suivante.",
     "source": "deloitte2024", "page": 4, "touche": "puissance_it_kw"},
    {"cle": "limite_puissance", "famille": "densite",
     "enonce": "35 % des centres de données se heurtent à une limite de "
               "puissance du fait des charges d'IA (Uptime Institute, cité).",
     "source": "penguin_five", "page": 12, "touche": "puissance_it_kw",
     "reserve": "Chiffre REPRIS par le fournisseur, pas produit par lui : "
                "l'auteur réel est l'Uptime Institute, à vérifier à la source."},
    {"cle": "puissance_commande", "famille": "densite",
     "enonce": "Le profil de puissance disponible — emplacement des arrivées, "
               "type et régularité du courant — dicte l'implantation physique "
               "du plateau, et non l'inverse. À puissance contrainte, on passe "
               "de baies à quatre nœuds à des baies à deux nœuds : plus de "
               "surface, plus d'obturateurs, même capacité de calcul.",
     "source": "penguin_five", "page": 12, "touche": "puissance_it_kw"},

    # ── L'eau ──────────────────────────────────────────────────────────────
    {"cle": "eau_site", "famille": "eau",
     "enonce": "Un centre peut consommer plus de 50 millions de gallons d'eau "
               "par an — une eau qui ne retourne ni à la nappe, ni au réservoir, "
               "ni au réseau dont elle provient.",
     "source": "deloitte2024", "page": 6, "touche": "part_evaporative"},

    # ── Ce que coûte un modèle ─────────────────────────────────────────────
    {"cle": "entrainement", "famille": "charge",
     "enonce": "L'entraînement de modèles de plus de 175 milliards de "
               "paramètres a consommé entre 324 et 1 287 MWh par exécution — et "
               "un modèle est réentraîné plusieurs fois.",
     "source": "deloitte2024", "page": 4, "touche": "taux_charge"},
    {"cle": "requete", "famille": "charge",
     "enonce": "Une requête d'IA générative consomme 10 à 100 fois plus "
               "d'électricité qu'une recherche internet classique.",
     "source": "deloitte2024", "page": 4, "touche": None},
    {"cle": "puces_efficaces", "famille": "charge",
     "enonce": "Une nouvelle génération d'accélérateurs réalise un entraînement "
               "en 90 jours pour 8,6 GWh, soit moins du dixième de l'énergie de "
               "la génération précédente pour la même tâche.",
     "source": "deloitte2024", "page": 7, "touche": None,
     "reserve": "Gain d'efficacité par unité de travail. Il ne réduit la "
                "consommation totale que si le volume de travail ne croît pas "
                "davantage — ce que la même source juge peu probable."},

    # ── Ce qui se perd ailleurs que dans la thermique ──────────────────────
    {"cle": "attente_reseau", "famille": "exploitation",
     "enonce": "Jusqu'à 30 % du temps d'horloge d'un entraînement est passé à "
               "attendre le réseau : une seule liaison lente ralentit la grappe "
               "entière.",
     "source": "penguin_five", "page": 16, "touche": "taux_charge"},
    {"cle": "grappes_utilisation", "famille": "exploitation",
     "enonce": "Les petites grappes atteignent plus de 90 % d'utilisation dès "
               "l'installation ; les grandes tombent entre 10 et 90 %, et "
               "reviennent vers 90 % après réglage du réseau et du logiciel "
               "(analyse Meta, citée).",
     "source": "penguin_five", "page": 16, "touche": "taux_charge",
     "reserve": "C'est le lien direct avec le taux de charge de ce formulaire : "
                "une grappe mal réglée fait tourner des auxiliaires "
                "dimensionnés pour une charge qui n'arrive pas."},
]

# Ce que les quatre documents NE DISENT PAS — et qu'un lecteur pourrait croire
# y trouver. Une bibliographie qui ne liste que ce qu'elle apporte laisse
# supposer qu'elle couvre le reste.
LACUNES = [
    "Aucune analyse de cycle de vie au sens d'ISO 14040 — malgré le nom de "
    "fichier d'un des documents. Le carbone incorporé de la construction et des "
    "serveurs n'est chiffré nulle part dans ces quatre sources.",
    "Aucune donnée de terrain sur le WUE réel des installations européennes : "
    "l'eau n'est abordée que par un ordre de grandeur nord-américain.",
    "Aucun retour d'exploitation chiffré sur le refroidissement liquide : la "
    "réduction annoncée jusqu'à 90 % est une comparaison technologique, et la "
    "source elle-même signale que le déploiement reste marginal.",
    "Rien sur la fin de vie des équipements ni sur le réemploi — alors que le "
    "renouvellement accéléré des accélérateurs, que plusieurs de ces documents "
    "présentent comme un gain d'efficacité, se paie précisément là.",
]


def _verifier():
    fautes = []
    for f in FAITS:
        if f["source"] not in SOURCES:
            fautes.append("fait %s : source inconnue %s" % (f["cle"], f["source"]))
    for s, v in SOURCES.items():
        if v["nature"] not in NATURES:
            fautes.append("source %s : nature inconnue %s" % (s, v["nature"]))
    cles = [f["cle"] for f in FAITS]
    if len(set(cles)) != len(cles):
        fautes.append("clé de fait dupliquée")
    # Une source citée par aucun fait n'a rien à faire dans la bibliographie :
    # elle donnerait du volume sans rien apporter.
    citees = {f["source"] for f in FAITS}
    orphelines = [s for s in SOURCES if s not in citees]
    if orphelines:
        fautes.append("source citée par aucun fait : %s" % ", ".join(orphelines))
    return fautes


_FAUTES = _verifier()
if _FAUTES:
    raise RuntimeError("etat_art — bibliographie incohérente : " + " ; ".join(_FAUTES))


def familles():
    """Les familles de faits, dans l'ordre où elles se lisent."""
    vues, out = set(), []
    for f in FAITS:
        if f["famille"] not in vues:
            vues.add(f["famille"])
            out.append(f["famille"])
    return out


FAMILLES_NOM = {
    "trajectoire": "Ce que pèse le parc, et vers quoi il va",
    "territoire": "Ce que les territoires ont déjà décidé",
    "energie": "Où part l'électricité, dans le bâtiment",
    "densite": "La densité, qui commande tout le reste",
    "eau": "L'eau",
    "charge": "Ce que coûte un modèle",
    "exploitation": "Ce qui se perd ailleurs que dans la thermique",
}


def etat():
    """L'état de l'art, prêt à afficher : les faits, groupés, chacun avec son
    auteur et ce que vaut cet auteur."""
    groupes = []
    for fam in familles():
        groupes.append({
            "cle": fam,
            "nom": FAMILLES_NOM.get(fam, fam),
            "faits": [{
                "cle": f["cle"], "enonce": f["enonce"], "touche": f.get("touche"),
                "reserve": f.get("reserve"),
                "source": {
                    "cle": f["source"],
                    "editeur": SOURCES[f["source"]]["editeur"],
                    "titre": SOURCES[f["source"]]["titre"],
                    "date": SOURCES[f["source"]]["date"],
                    "page": f["page"],
                    "nature": SOURCES[f["source"]]["nature"],
                    "nature_nom": NATURES[SOURCES[f["source"]]["nature"]]["nom"],
                },
            } for f in FAITS if f["famille"] == fam],
        })
    return {
        "version": VERSION,
        "genere": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "natures": NATURES,
        "sources": SOURCES,
        "groupes": groupes,
        "lacunes": LACUNES,
        "n_faits": len(FAITS),
        "avertissement":
            "Aucun de ces chiffres n'entre dans le calcul de cette page : le "
            "moteur tient ses constantes de normes, pas de livres blancs. Ils "
            "servent à situer un projet dans un marché, et à savoir quelles "
            "questions poser. Trois des quatre sources sont publiées par des "
            "fournisseurs d'infrastructure — leurs mesures sont utiles, leur "
            "intérêt n'est pas neutre, et chaque ligne le dit.",
    }


def sante():
    par_nature = {}
    for s in SOURCES.values():
        par_nature[s["nature"]] = par_nature.get(s["nature"], 0) + 1
    return {"module": "etat_art", "version": VERSION,
            "sources": len(SOURCES), "faits": len(FAITS),
            "familles": len(familles()),
            "par_nature": par_nature,
            "faits_avec_reserve": sum(1 for f in FAITS if f.get("reserve")),
            "faits_relies_au_moteur": sum(1 for f in FAITS if f.get("touche")),
            "lacunes": len(LACUNES),
            "problemes": _verifier()}
