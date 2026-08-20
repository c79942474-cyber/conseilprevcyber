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


# ═══════════════════════════════════════════════════════════════════════════
#  COMBIEN DE SERVEURS ? — une dérivation, et ce qu'elle refuse de dériver
#
#  POURQUOI CE CALCUL EST ICI ET NON DANS LE MOTEUR. Le moteur tient ses
#  constantes de NORMES, et un contrôle lui interdit d'importer ce module :
#  un chiffre de livre blanc fournisseur entrerait sinon dans un résultat
#  présenté comme normatif sans que rien ne le signale. Les puissances par
#  serveur viennent précisément d'un livre blanc fournisseur. Elles restent
#  donc ici, avec leur source et la nature de cette source, et elles servent à
#  PROPOSER une valeur dans le formulaire — jamais à calculer un bilan.
#
#  CE QUE LE FORMULAIRE DEMANDAIT SANS AIDE. « Nombre de serveurs » était un
#  nombre nu. Qui ne connaît pas déjà son parc répond au hasard ou n'y touche
#  pas — et le module de balayage l'écrit sans détour : « aucune plage
#  défendable sans connaître la densité visée ». C'est exact, et la conséquence
#  n'est pas de se taire : c'est que chaque proposition doit DÉCLARER la
#  densité qu'elle suppose. Elle redevient alors défendable.
#
#  LE NOMBRE DE SERVEURS N'EST PAS UNE DONNÉE INDÉPENDANTE : c'est la puissance
#  informatique — la seule entrée indispensable du formulaire, donc déjà
#  saisie — divisée par la puissance d'un serveur. Seule la seconde manquait.
#
#  QUAND LA DIVISION EST UNE LECTURE, ET QUAND ELLE SERAIT UNE INVENTION. Le
#  fait « baies_kw » donne la puissance de la baie ET son nombre de nœuds pour
#  les baies de calcul : la division est alors une lecture. Pour la baie
#  d'entreprise et la baie B200, la source donne la baie SANS le nombre de
#  nœuds — rien n'en est tiré, et ce refus est publié comme le reste.
# ═══════════════════════════════════════════════════════════════════════════

# Le fait dont sortent les puissances par serveur, et donc la source à citer.
_SOURCE_SERVEURS = "penguin_five"

PUISSANCE_PAR_SERVEUR = {
    "volume": {
        "kw": 0.5,
        "nom": "serveur de volume (biprocesseur)",
        "obtention": "hypothese_du_moteur",
        "fait": None,
        "source": "Ce n'est pas un chiffre de ce dossier : c'est l'hypothèse "
                  "que le moteur emploie déjà lui-même pour estimer un parc "
                  "quand le champ reste vide. Elle est reprise ici pour que "
                  "le formulaire propose la même chose que le calcul.",
    },
    "gpu_a100": {
        "kw": 6.5,
        "nom": "nœud GPU de génération A100",
        "obtention": "derive",
        "fait": "baies_kw",
        "baie_kw": 13, "noeuds": 2,
        "source": "Baie A100 à deux nœuds, 13 kW.",
    },
    "gpu_h100": {
        "kw": 11.0,
        "nom": "nœud GPU de génération H100",
        "obtention": "derive",
        "fait": "baies_kw",
        "baie_kw": 22, "noeuds": 2,
        "source": "Baie H100 à deux nœuds 22 kW — et à quatre nœuds 44 kW, "
                  "qui donne la même puissance par nœud.",
    },
}

ORDRE_SERVEURS = ["volume", "gpu_a100", "gpu_h100"]

SERVEURS_SANS_DERIVATION = {
    "baie_entreprise": {
        "baie_kw": 8.6,
        "pourquoi": "La source donne 8,6 kW pour une baie d'entreprise, sans "
                    "dire combien de serveurs elle contient. Le remplissage "
                    "varie du simple au triple selon le format et la "
                    "ventilation : le supposer fabriquerait un compte "
                    "crédible et faux.",
    },
    "baie_b200": {
        "baie_kw": 57,
        "pourquoi": "La source donne 57 kW pour une baie B200, sans son "
                    "nombre de nœuds. C'est la génération où le nombre de "
                    "nœuds par baie devient précisément la question de "
                    "conception : le supposer serait y répondre à sa place.",
    },
}


def serveurs_possibles(puissance_it_kw):
    """Le nombre de serveurs que porte une puissance informatique donnée.

    UN COMPTE PAR PROFIL, chacun disant la puissance par serveur qu'il suppose
    et d'où elle vient. C'est ce qui rend la proposition défendable : ce n'est
    pas « environ tant de serveurs », c'est « tant de serveurs SI ce sont des
    nœuds H100 ».
    """
    try:
        p = float(puissance_it_kw or 0)
    except (TypeError, ValueError):
        p = 0.0
    commun = {
        "sans_derivation": SERVEURS_SANS_DERIVATION,
        "source": SOURCES[_SOURCE_SERVEURS],
        "nature_source": NATURES[SOURCES[_SOURCE_SERVEURS]["nature"]]["nom"],
    }
    if p <= 0:
        return dict(commun, ok=False, erreur="puissance_absente",
                    message="Le nombre de serveurs se déduit de la puissance "
                            "informatique : saisissez-la d'abord.")
    profils = []
    for cle in ORDRE_SERVEURS:
        d = PUISSANCE_PAR_SERVEUR[cle]
        profils.append({
            "cle": cle, "nom": d["nom"], "kw_par_serveur": d["kw"],
            "obtention": d["obtention"], "source": d["source"],
            # Un demi-serveur n'existe pas ; on n'annonce pas non plus zéro
            # quand la puissance suffit à en porter au moins un.
            "nombre": max(1, int(round(p / d["kw"]))),
        })
    return dict(commun, ok=True, puissance_it_kw=p, profils=profils,
                lecture="Ces comptes ne sont pas des ordres de grandeur : "
                        "chacun est la puissance informatique divisée par la "
                        "puissance d'un serveur du profil nommé. D'un profil à "
                        "l'autre le compte varie d'un facteur vingt — c'est le "
                        "profil qu'il faut choisir, pas le nombre.",
                reserve="La puissance informatique porte AUSSI le stockage et "
                        "le réseau, que ce partage ignore : le compte obtenu "
                        "est un haut de fourchette.")


def _verifier_serveurs():
    """LA DÉRIVATION DOIT RESTER UNE DIVISION, et rester raccrochée à son fait.

    Deux dérives, toutes deux silencieuses : qu'on retouche une puissance par
    serveur sans toucher la baie dont elle sort, et que le fait sourcé change
    de chiffre sans que cette table suive — la page citerait alors une source
    qui ne dit plus ce qu'on lui fait dire.
    """
    fautes = []
    if set(ORDRE_SERVEURS) != set(PUISSANCE_PAR_SERVEUR):
        fautes.append("l'ordre des profils de serveur ne les couvre pas")
    par_cle = {f["cle"]: f for f in FAITS}
    for cle in ORDRE_SERVEURS:
        d = PUISSANCE_PAR_SERVEUR[cle]
        for champ in ("kw", "nom", "obtention", "source"):
            if not d.get(champ):
                fautes.append("profil serveur %s sans %s" % (cle, champ))
        if d["obtention"] != "derive":
            continue
        attendu = d["baie_kw"] / float(d["noeuds"])
        if abs(attendu - d["kw"]) > 1e-9:
            fautes.append(
                "le profil %s annonce %s kW par serveur, mais sa baie de %s kW "
                "à %d nœuds en donne %s — une dérivation qui ne se refait pas "
                "n'est plus une dérivation"
                % (cle, d["kw"], d["baie_kw"], d["noeuds"], attendu))
        f = par_cle.get(d["fait"])
        if not f:
            fautes.append("le profil %s s'appuie sur le fait %s, absent"
                          % (cle, d["fait"]))
            continue
        if ("%d kW" % d["baie_kw"]) not in f["enonce"]:
            fautes.append(
                "le profil %s s'appuie sur une baie de %s kW que le fait « %s » "
                "ne mentionne plus" % (cle, d["baie_kw"], d["fait"]))
    for cle, d in SERVEURS_SANS_DERIVATION.items():
        if len(d.get("pourquoi", "")) < 40:
            fautes.append("le refus de dériver %s n'est pas motivé" % cle)
    return fautes


# LE CONTRÔLE COURT ICI, et non avec celui de la bibliographie : celui-là
# s'exécute plus haut dans le fichier, avant que ces fonctions existent —
# l'appeler là-bas levait un NameError au chargement du module.
_FAUTES_SERVEURS = _verifier_serveurs()
if _FAUTES_SERVEURS:
    raise RuntimeError("etat_art — dérivation du nombre de serveurs "
                       "incohérente : " + " ; ".join(_FAUTES_SERVEURS))


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
        # Les profils de serveur voyagent AVEC l'état de l'art, pas avec le
        # référentiel du moteur : c'est là qu'est leur source, et c'est ainsi
        # que la page peut dire d'où vient chaque compte qu'elle propose.
        "puissance_par_serveur": PUISSANCE_PAR_SERVEUR,
        "ordre_serveurs": ORDRE_SERVEURS,
        "serveurs_sans_derivation": SERVEURS_SANS_DERIVATION,
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
