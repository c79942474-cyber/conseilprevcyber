# -*- coding: utf-8 -*-
"""EMPREINTE DE L'IA — les facteurs, les trois méthodes, l'ajustement fin, les
trajectoires.

MODULE PARTAGÉ À L'IDENTIQUE entre conseilprev (Sentinel) et conseilprevcyber,
sur le modèle de moe_dc — et, cette fois, TENU PAR UNE RÈGLE dans les deux
suites. La leçon vient d'à côté : `equipements_it.py` se déclare « partagé à
l'identique » depuis son en-tête, et les deux copies divergent de trente-six
lignes ; `base_carbone.py`, de trente-huit. Pire, l'écart n'est pas cosmétique :
le côté cyber a requalifié ses sources en « hypothèse du cabinet, pas une
mesure », pendant que Sentinel continuait d'annoncer des empreintes produit
constructeurs. Le même module, servi par deux sites, avec deux vérités — et
c'est le site le plus exposé qui portait la plus flatteuse. Un commentaire qui
dit « partagé » ne partage rien ; seule une règle le fait.

CE QUE CE MODULE DÉDOUBLONNE
────────────────────────────
Les facteurs physiques de l'empreinte vivaient dans `app.py` de Sentinel, entre
les lignes 16150 et 16430 : un PUE par modèle, une intensité carbone par pays,
une majoration de fabrication de 30 %, un kWh/Go. Le site cyber, lui, publie
PUE, WUE, carbone incorporé et eau avec formule, source et incertitude. Deux
jeux de facteurs pour la même physique, dans deux dépôts, sans rien qui les
compare. Ils sont ici, une fois.

CE QUE CE MODULE NE FAIT PAS
────────────────────────────
Il ne collecte rien et n'invente aucun volume. Les jetons viennent du décompte
renvoyé par l'interface du fournisseur ; les heures d'accélérateur d'un
ajustement fin sont DÉCLARÉES par celui qui lit sa console. Un volume absent
n'est pas estimé : `couverture()` le dit, et le total porte la marque.

LA DISCIPLINE DES FACTEURS
──────────────────────────
Chaque facteur est un enregistrement, pas un nombre nu. Il porte sa valeur, son
unité, sa NATURE — texte réglementaire, relevé, ou hypothèse du cabinet —, sa
source, la date à laquelle elle a été lue, et la date à laquelle elle est due
d'être révisée. `_verifier()` refuse le chargement du module si l'un d'eux
manque. Un facteur sans source ne sert pas : il se réclame de personne.

L'INDICATEUR QUI A DEMANDÉ UNE SOURCE, ET CE QU'ELLE DIT VRAIMENT
─────────────────────────────────────────────────────────────────
L'énergie primaire (MJ) suppose un coefficient de passage depuis l'électricité
finale. Celui retenu — 1,9 — vient du règlement délégué (UE) 2023/807 de la
Commission du 15 décembre 2022, dont l'annexe remplace la note 3 de l'annexe IV
de la directive 2012/27/UE. Le texte a été lu, et il impose trois réserves que
ce module écrit plutôt que de les taire :

  1. LE COEFFICIENT SERT À CALCULER DES ÉCONOMIES. Sa phrase exacte est
     « Applicable when energy savings are calculated in primary energy terms
     using a bottom-up approach based on final energy consumption ». L'employer
     pour convertir la consommation d'un parc en énergie primaire est une
     TRANSPOSITION : elle est cohérente avec la méthode de comptage annoncée
     (contenu énergétique physique pour le nucléaire, rendement de conversion
     pour les combustibles, équivalent direct pour les renouvelables non
     combustibles), mais ce n'est pas ce que la note dit.

  2. C'EST UN DÉFAUT, PAS UNE OBLIGATION. Les États membres « may apply a
     default coefficient of 1,9 or use the discretion to define a different
     coefficient, provided that they can justify it ». Un client qui a le sien
     doit pouvoir le substituer : `energie_primaire_mj` accepte un coefficient.

  3. IL EST RÉVISABLE TOUS LES QUATRE ANS. « By 25 December 2022 and every four
     years thereafter, the Commission shall revise the default coefficient on
     the basis of observed data. » La prochaine échéance est le 25 décembre
     2026 : le facteur porte cette date, et `etat()` la signale.

UN POINT OUVERT, ÉCRIT PLUTÔT QU'ESCAMOTÉ
─────────────────────────────────────────
La directive 2012/27/UE que ce règlement amende a été REFONDUE par la directive
(UE) 2023/1791. Le texte consolidé de la refonte fait 389 ko et n'a pas pu être
lu ici ; il n'est donc PAS établi qu'elle reproduise le 1,9 à l'identique. La
valeur reste celle du règlement délégué, lu verbatim ; la vérification de sa
reprise dans la refonte est un point ouvert, porté par le facteur lui-même.

CE QUI N'EST PAS ICI, ET POURQUOI
─────────────────────────────────
Les ressources abiotiques (kg Sb éq.) ne figurent pas. Elles font partie du jeu
d'indicateurs habituel, mais aucun facteur sourçable n'a été trouvé pour les
calculer : écrire l'indicateur sans lui reviendrait à publier un nombre qui ne
se réclame de personne. L'absence est déclarée dans `INDICATEURS`, avec ce
qu'il faudrait pour la combler.
"""
import os
from datetime import date

VERSION = "2026-09-a"

# ═══════════════════════════════════════════════════════════════════════════
#  1. LA NATURE D'UN FACTEUR — trois, et elles ne valent pas la même chose
# ═══════════════════════════════════════════════════════════════════════════

NATURES = {
    "texte_reglementaire": "Valeur fixée par un texte publié, citée avec sa référence.",
    "releve": "Valeur relevée auprès d'une source interrogeable, avec sa date.",
    "hypothese_cabinet": "Choix de milieu de plage du cabinet. Pas une mesure, "
                         "pas un relevé : à remplacer par une valeur du client "
                         "dès qu'elle existe.",
}

#: Ce qu'un facteur doit porter pour être servi. `_verifier()` le fait respecter.
CHAMPS_FACTEUR = ("valeur", "unite", "nature", "source")


def _env(nom, defaut):
    """Un facteur peut être remplacé par l'environnement — et cesse alors
    d'être celui qui est déclaré ici. La substitution est donc TRACÉE :
    `etat()` la signale, sans quoi la page citerait une source pour une valeur
    qui n'en vient plus."""
    brut = os.environ.get(nom, "")
    if brut == "":
        return float(defaut), False
    try:
        return float(brut), True
    except (TypeError, ValueError):
        return float(defaut), False


_PEF, _PEF_SUBST = _env("EMPREINTE_PEF_ELEC", 1.9)
_FAB, _FAB_SUBST = _env("EMPREINTE_FABRICATION_PCT", 30.0)

#: 1 kWh = 3,6 MJ. Ce n'est pas un facteur, c'est une définition d'unité :
#: elle ne se source pas et ne se périme pas.
MJ_PAR_KWH = 3.6

FACTEURS = {
    "pef_electricite": {
        "valeur": _PEF, "unite": "sans", "nature": "texte_reglementaire",
        "libelle": "Coefficient de passage électricité finale → énergie primaire",
        "source": "Règlement délégué (UE) 2023/807 de la Commission du 15 décembre "
                  "2022 révisant le coefficient d'énergie primaire pour "
                  "l'électricité, annexe — remplace la note 3 de l'annexe IV de la "
                  "directive 2012/27/UE. CELEX 32023R0807.",
        "url": "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32023R0807",
        "releve_le": "2026-09-08", "revision_due": "2026-12-25",
        "substitue": _PEF_SUBST,
        "reserve": "Le texte vise le calcul d'ÉCONOMIES d'énergie en primaire par "
                   "approche ascendante. L'employer sur une consommation est une "
                   "transposition assumée. C'est en outre un coefficient PAR DÉFAUT, "
                   "qu'un État membre peut remplacer en le justifiant.",
        "point_ouvert": "La directive 2012/27/UE amendée a été refondue par la "
                        "directive (UE) 2023/1791 ; la reprise du 1,9 dans la "
                        "refonte n'a pas été vérifiée.",
    },
    "fabrication_pct": {
        "valeur": _FAB, "unite": "% des émissions d'usage", "nature": "hypothese_cabinet",
        "libelle": "Majoration forfaitaire des impacts incorporés (méthode C)",
        "source": "HYPOTHÈSE DU CABINET, PAS UNE MESURE. Ordre de grandeur calé sur "
                  "l'approche Boavizta, simplifié en pourcentage ajouté à l'usage. "
                  "À REMPLACER par une analyse de cycle de vie du matériel réel — "
                  "`equipements_it` porte déjà les empreintes produit par poste.",
        "url": "", "releve_le": "2026-09-08", "revision_due": "2027-09-08",
        "substitue": _FAB_SUBST,
        "reserve": "Une majoration en pourcentage ne distingue ni le calcul, ni le "
                   "stockage, ni le réseau : elle rend un ordre de grandeur, pas un "
                   "cycle de vie.",
        "point_ouvert": "",
    },
    "reseau_kwh_go": {
        "valeur": 0.06, "unite": "kWh/Go", "nature": "hypothese_cabinet",
        "libelle": "Intensité énergétique du transport de données",
        "source": "HYPOTHÈSE DU CABINET. Ordre de grandeur usuel de la littérature "
                  "sur l'intensité énergétique des réseaux fixes, dont les valeurs "
                  "publiées s'étalent sur plus d'un ordre de grandeur selon le "
                  "périmètre retenu (cœur seul, ou cœur + accès + terminal).",
        "url": "", "releve_le": "2026-09-08", "revision_due": "2027-09-08",
        "substitue": False, "reserve": "", "point_ouvert": "",
    },
    "hebergement_wh_req": {
        "valeur": 0.15, "unite": "Wh/requête servie", "nature": "hypothese_cabinet",
        "libelle": "Énergie d'hébergement d'une requête HTTP (instance + PUE)",
        "source": "HYPOTHÈSE DU CABINET, calée sur la consommation observée d'une "
                  "instance de la plateforme rapportée au nombre de requêtes servies.",
        "url": "", "releve_le": "2026-09-08", "revision_due": "2027-09-08",
        "substitue": False, "reserve": "", "point_ouvert": "",
    },
}

#: Énergie par millier de jetons de sortie (Wh) : (basse, centrale, haute).
#: Les trois valeurs sont l'incertitude, pas une précision : les publier sans
#: la fourchette laisserait croire à une mesure.
WH_1K_JETONS = {
    "petit": (0.05, 0.30, 0.80),
    "moyen": (0.30, 1.50, 4.00),
    "grand": (1.00, 4.00, 12.00),
}
WH_1K_SOURCE = ("HYPOTHÈSE DU CABINET, calée sur les ordres de grandeur publiés par "
                "les travaux disponibles (EcoLogits, ML.ENERGY, communications de "
                "fournisseurs). Aucun fournisseur ne publie la consommation réelle "
                "d'une requête : ces valeurs sont des plages, et c'est pour cela "
                "qu'elles en portent trois.")

#: La puissance d'un accélérateur est DÉCLARÉE. Ces entrées sont des repères
#: nommés par leur propre valeur — un « 700 W » ne prétend désigner aucun
#: matériel précis, ce qui évite d'inventer une fiche technique.
PUISSANCE_ACCELERATEUR = {"300": 300.0, "500": 500.0, "700": 700.0, "1200": 1200.0}
PUISSANCE_SOURCE = ("Repères nommés par leur valeur : le nom EST la puissance "
                    "déclarée, en watts. Ils ne désignent aucun modèle de matériel "
                    "et ne remplacent pas la valeur de la fiche technique du parc.")


def _verifier():
    """Le module refuse de se charger si un facteur ne se réclame de personne.

    CE QUE CETTE GARDE PREND, ET QU'AUCUNE RÈGLE D'ESSAI NE PRENDRAIT AUSSI TÔT :
    un facteur ajouté à la va-vite, sans source, servi en production le temps
    qu'une revue le remarque."""
    for cle, f in FACTEURS.items():
        for champ in CHAMPS_FACTEUR:
            if not f.get(champ):
                raise RuntimeError("empreinte_ia : le facteur %r n'a pas de %s" % (cle, champ))
        if f["nature"] not in NATURES:
            raise RuntimeError("empreinte_ia : nature inconnue pour %r : %r" % (cle, f["nature"]))
        if f["nature"] == "texte_reglementaire" and not f.get("url"):
            raise RuntimeError("empreinte_ia : %r se dit réglementaire sans adresse" % cle)
        for d in ("releve_le", "revision_due"):
            date.fromisoformat(f[d])
    for classe, plage in WH_1K_JETONS.items():
        if not (len(plage) == 3 and plage[0] <= plage[1] <= plage[2]):
            raise RuntimeError("empreinte_ia : plage incohérente pour %r" % classe)
    for nom, w in PUISSANCE_ACCELERATEUR.items():
        if float(nom) != w:
            raise RuntimeError("empreinte_ia : le repère %r n'a pas sa propre valeur (%s)"
                               % (nom, w))


_verifier()


# ═══════════════════════════════════════════════════════════════════════════
#  2. LES INDICATEURS — quatre servis, un déclaré absent
# ═══════════════════════════════════════════════════════════════════════════

INDICATEURS = [
    {"cle": "electricite", "libelle": "Électricité", "unite": "kWh", "servi": True,
     "manque": ""},
    {"cle": "ges", "libelle": "Émissions de GES", "unite": "kg CO₂ éq.", "servi": True,
     "manque": ""},
    {"cle": "eau", "libelle": "Eau", "unite": "m³ éq.", "servi": True,
     "manque": ""},
    {"cle": "energie_primaire", "libelle": "Énergie primaire", "unite": "MJ", "servi": True,
     "manque": ""},
    # L'ABSENCE EST DÉCLARÉE, PAS TUE. Un indicateur qu'on retire sans le dire
    # laisse croire qu'il a été jugé nul ; celui-ci n'a pas de facteur.
    {"cle": "ressources", "libelle": "Ressources", "unite": "kg Sb éq.", "servi": False,
     "manque": "Aucun facteur d'épuisement abiotique sourçable n'a été retenu. "
               "Le calculer demande soit une base ACV donnant l'ADP par "
               "équipement, soit la fiche d'empreinte produit du constructeur. "
               "Sans elle, l'indicateur serait un nombre sans auteur."},
]


def indicateurs_servis():
    return [i for i in INDICATEURS if i["servi"]]


def indicateurs_absents():
    return [i for i in INDICATEURS if not i["servi"]]


# ═══════════════════════════════════════════════════════════════════════════
#  3. LES CONVERSIONS SOURCÉES
# ═══════════════════════════════════════════════════════════════════════════

def energie_primaire_mj(kwh, coefficient=None):
    """Énergie primaire, en MJ, depuis l'électricité finale.

    MJ = kWh × coefficient × 3,6

    Le coefficient par défaut est celui du règlement délégué (UE) 2023/807 ;
    un client qui dispose du coefficient national justifié de son État membre
    le passe ici — c'est exactement la latitude que le texte prévoit."""
    if kwh is None:
        return None
    c = float(FACTEURS["pef_electricite"]["valeur"] if coefficient is None else coefficient)
    return float(kwh) * c * MJ_PAR_KWH


def _eau_dc():
    """Le référentiel eau, s'il est présent dans ce dépôt.

    IL N'EST PAS RECOPIÉ ICI, ET C'EST LE POINT. L'EWIF a une seule définition,
    dans `eau_dc` ; la dupliquer pour rendre ce module autonome créerait
    exactement le doublon qu'il existe pour supprimer. Là où le module manque,
    l'eau est déclarée indisponible avec son motif — visiblement, pas en
    silence."""
    try:
        import eau_dc
        return eau_dc
    except ImportError:
        return None


def eau_m3(kwh, pays="FR"):
    """Eau consommée en amont par l'électricité, en m³.

    m³ = kWh × EWIF (L/kWh) ÷ 1 000. L'EWIF est l'eau CONSOMMÉE — évaporée, non
    restituée — et non l'eau prélevée : `eau_dc` insiste, et confondre les deux
    change le résultat d'un facteur dix sur un parc nucléaire."""
    w = _eau_dc()
    if w is None:
        return {"nature": "indisponible", "m3": None, "ewif": None,
                "motif": "le référentiel eau (eau_dc) n'est pas présent dans ce "
                         "dépôt : l'eau n'est pas calculée plutôt qu'approchée"}
    if kwh is None:
        return {"nature": "indisponible", "m3": None, "ewif": None,
                "motif": "aucune électricité estimée — aucune eau dérivable"}
    e = w.ewif_pays(pays)
    return {"nature": e["nature"], "m3": float(kwh) * e["valeur"] / 1000.0,
            "ewif": e["valeur"], "ewif_national": e["national"],
            "incertitude": w.EWIF_INCERTITUDE,
            "formule": "kWh × %s L/kWh ÷ 1 000" % e["valeur"], "motif": None}


# ═══════════════════════════════════════════════════════════════════════════
#  4. L'INFÉRENCE — les trois méthodes, sur les mêmes données d'usage
# ═══════════════════════════════════════════════════════════════════════════
#
# CE QUE LES TROIS MÉTHODES SERVENT À MONTRER. Un chiffre d'empreinte n'a de
# sens qu'accompagné de son périmètre. Les calculer en parallèle sur les mêmes
# données permet de publier leur ÉCART — qui ne dit pas qu'une valeur est
# fausse, mais mesure la sensibilité du résultat au choix de périmètre. C'est
# précisément ce qu'examine un auditeur.
#
# CE MODULE N'OUVRE AUCUNE SOCKET. Les intensités carbone lui sont PASSÉES :
# le relevé temps réel (RTE, ENTSO-E) reste dans l'application, où il a un
# cache et une tâche de fond. Un module de calcul qui interroge le réseau ne
# se teste pas — il se moque.

PROFILS_MODELE = [
    ("claude",        {"classe": "grand", "pays": "US", "pue": 1.20, "fournisseur": "Anthropic"}),
    ("mistral-large", {"classe": "grand", "pays": "FR", "pue": 1.15, "fournisseur": "Mistral AI"}),
    ("mistral-embed", {"classe": "petit", "pays": "FR", "pue": 1.15, "fournisseur": "Mistral AI"}),
    ("mistral",       {"classe": "moyen", "pays": "FR", "pue": 1.15, "fournisseur": "Mistral AI"}),
]
PROFIL_INCONNU = {"classe": "moyen", "pays": "EU", "pue": 1.20, "fournisseur": "Autre"}


def profil(modele):
    """Le profil d'un modèle, ou celui du milieu de plage s'il est inconnu.

    UN MODÈLE INCONNU N'EST PAS UN MODÈLE GRATUIT : il reçoit la classe
    moyenne, et `connu` dit que c'est un repli — sans quoi un parc entier de
    modèles non profilés se chiffrerait sans que rien ne le signale."""
    m = str(modele or "").lower()
    for cle, p in PROFILS_MODELE:
        if cle in m:
            d = dict(p)
            d["connu"] = True
            return d
    d = dict(PROFIL_INCONNU)
    d["connu"] = False
    return d


def inference(modele, jetons_sortie, intensite_usage, intensite_hebergement,
              intensite_fixe=None, pays_eau=None):
    """L'empreinte d'un appel de modèle, selon les trois méthodes.

    A — facteurs statiques : usage seul, intensité fixe, ni PUE ni fabrication.
    B — paramétrique : PUE appliqué, intensité passée, fourchette.
    C — cycle de vie étendu : B + incorporé + hébergement de la requête.

    Les quatre indicateurs servis ne sont dérivés QUE de la méthode C : ce
    serait mentir que de donner une eau ou une énergie primaire à un périmètre
    qui ne compte ni le matériel ni l'hébergement."""
    p = profil(modele)
    bas, central, haut = WH_1K_JETONS.get(p["classe"], WH_1K_JETONS["moyen"])
    k = max(0.0, float(jetons_sortie or 0)) / 1000.0
    fixe = float(intensite_fixe if intensite_fixe is not None else intensite_usage)

    wh_a = central * k
    g_a = wh_a / 1000.0 * fixe

    pue = float(p.get("pue") or 1.2)
    wh_b, wh_b_min, wh_b_max = central * k * pue, bas * k * pue, haut * k * pue
    g_b = wh_b / 1000.0 * float(intensite_usage)
    g_b_min = wh_b_min / 1000.0 * float(intensite_usage)
    g_b_max = wh_b_max / 1000.0 * float(intensite_usage)

    heb_wh = float(FACTEURS["hebergement_wh_req"]["valeur"])
    wh_c = wh_b + heb_wh
    fab = 1.0 + max(0.0, float(FACTEURS["fabrication_pct"]["valeur"])) / 100.0
    g_heb = heb_wh / 1000.0 * float(intensite_hebergement)
    g_c, g_c_min, g_c_max = g_b * fab + g_heb, g_b_min * fab + g_heb, g_b_max * fab + g_heb

    eau = eau_m3(wh_c / 1000.0, pays_eau or p["pays"])
    return {"classe": p["classe"], "pays": p["pays"], "fournisseur": p["fournisseur"],
            "profil_connu": p["connu"], "pue": pue,
            "wh_a": wh_a, "g_a": g_a,
            "wh_b": wh_b, "g_b": g_b, "g_b_min": g_b_min, "g_b_max": g_b_max,
            "wh_c": wh_c, "g_c": g_c, "g_c_min": g_c_min, "g_c_max": g_c_max,
            "mj_c": energie_primaire_mj(wh_c / 1000.0),
            "eau_c": eau}


# ═══════════════════════════════════════════════════════════════════════════
#  5. L'AJUSTEMENT FIN — déclaré, amorti, jamais estimé
# ═══════════════════════════════════════════════════════════════════════════
#
# POURQUOI IL MANQUAIT, ET CE QUE ÇA COÛTAIT. Le journal d'empreinte ne compte
# que des appels d'inférence : chaque requête est enregistrée avec son décompte
# de jetons. Un entraînement fin n'est pas une requête — c'est une campagne de
# calcul, parfois de plusieurs jours, qui ne passe par aucune interface
# journalisée. L'omettre ne fausse pas le bilan de quelques pour cent : sur un
# parc qui affine ses modèles, c'est souvent le terme DOMINANT.
#
# CE QU'ON NE PEUT PAS DEVINER. Ni les heures d'accélérateur, ni leur nombre,
# ni leur puissance, ni le PUE du centre où la campagne a tourné. Tout cela se
# lit sur une console de facturation ou se demande au fournisseur. Le module
# ne les estime donc pas : il les exige, et dit lesquels manquent.

A_DECLARER_FIN = {
    "heures_accelerateur": "Durée de la campagne, en heures d'accélérateur cumulées.",
    "nombre_accelerateurs": "Combien d'accélérateurs ont tourné en parallèle.",
    "puissance_w": "Puissance unitaire déclarée, en watts (fiche technique du parc, "
                   "ou l'un des repères de PUISSANCE_ACCELERATEUR).",
    "pue": "Rendement du centre de données où la campagne a tourné.",
    "amorti_mois": "Sur combien de mois de service le modèle affiné est amorti.",
}


def ajustement_fin(declaration, intensite_usage, pays_eau="EU"):
    """L'empreinte d'un ajustement fin, amortie sur la durée de service.

    L'AMORTISSEMENT EST LE POINT DÉLICAT, ET IL EST ÉCRIT. Un entraînement est
    un coût UNIQUE ; le rapporter à un mois d'usage suppose une durée de
    service, qui est une décision, pas une mesure. Le module rend donc les
    deux : le total de la campagne, et sa part mensuelle — jamais la seconde
    sans la première."""
    d = declaration or {}
    manquants = [c for c in A_DECLARER_FIN if not d.get(c)]
    if manquants:
        return {"nature": "incomplet", "wh": None, "g_co2": None,
                "manquants": sorted(manquants),
                "motif": "un ajustement fin ne s'estime pas : %d champ(s) à déclarer"
                         % len(manquants)}
    heures = float(d["heures_accelerateur"])
    n = float(d["nombre_accelerateurs"])
    watts = float(d["puissance_w"])
    pue = float(d["pue"])
    mois = float(d["amorti_mois"])
    if min(heures, n, watts, pue, mois) <= 0:
        return {"nature": "incomplet", "wh": None, "g_co2": None,
                "manquants": [], "motif": "une valeur déclarée est nulle ou négative"}
    wh = heures * n * watts * pue
    kwh = wh / 1000.0
    g = kwh * float(intensite_usage)
    return {"nature": "declare", "wh": wh, "kwh": kwh, "g_co2": g,
            "mj": energie_primaire_mj(kwh), "eau": eau_m3(kwh, pays_eau),
            "wh_mois": wh / mois, "g_co2_mois": g / mois, "amorti_mois": mois,
            "formule": "%s h × %s accélérateurs × %s W × PUE %s"
                       % (heures, n, watts, pue),
            "manquants": [], "motif": None}


# ═══════════════════════════════════════════════════════════════════════════
#  6. LES TRAJECTOIRES — deux axes déclarés, quatre leviers, cinq repères
# ═══════════════════════════════════════════════════════════════════════════
#
# CE QUE CE MOTEUR EST, ET CE QU'IL N'EST PAS. Il projette une empreinte de
# base selon DEUX taux annuels déclarés — la croissance des usages et le gain
# d'efficacité — et rien d'autre. Il ne prédit pas : il compose deux hypothèses
# et rend ce qu'elles donnent.
#
# LES CINQ SCÉNARIOS NOMMÉS SONT DES REPÈRES DU CABINET. Leurs intitulés
# reprennent une lecture courante du sujet ; les TAUX, eux, sont des choix de
# milieu de plage posés ici, et non les valeurs d'un référentiel publié. Aucune
# source ne les fixe, et le module ne prétend pas le contraire : le plan
# d'adoption d'un client remplace le repère dès qu'il existe.

AXES = {
    "adoption": {"libelle": "Croissance annuelle des usages",
                 "unite": "%/an", "sens": "augmente l'empreinte"},
    "efficacite": {"libelle": "Gain d'efficacité annuel",
                   "unite": "%/an", "sens": "réduit l'empreinte"},
}

SCENARIOS = [
    {"cle": "progression_reguliere", "nom": "Progression régulière",
     "adoption": 15.0, "efficacite": 5.0, "lecture": "Adoption modérée · efficacité limitée"},
    {"cle": "adoption_sans_limites", "nom": "Adoption sans limites",
     "adoption": 40.0, "efficacite": 5.0, "lecture": "Adoption forte · efficacité limitée"},
    {"cle": "sobriete_efficacite", "nom": "Sobriété et efficacité",
     "adoption": 15.0, "efficacite": 20.0, "lecture": "Adoption modérée · efficacité élevée"},
    {"cle": "percee_technologique", "nom": "Percée technologique",
     "adoption": 40.0, "efficacite": 20.0, "lecture": "Adoption forte · efficacité élevée"},
    {"cle": "expansion_maitrisee", "nom": "Expansion maîtrisée",
     "adoption": 25.0, "efficacite": 12.0, "lecture": "Adoption soutenue · efficacité moyenne"},
]
SCENARIOS_SOURCE = ("REPÈRES DU CABINET, PAS UN RÉFÉRENTIEL. Les intitulés reprennent "
                    "une lecture courante du sujet ; les taux sont des choix de milieu "
                    "de plage posés ici. Le plan d'adoption du client les remplace.")

LEVIERS_2030 = [
    {"cle": "modeles", "nom": "Modèles", "agit_sur": "efficacite",
     "quoi": "Taille du modèle appelé, mise en cache, requête bornée, modèle par étape.",
     "porte": "Le seul levier que le client actionne seul, sans rien changer d'autre."},
    {"cle": "materiel", "nom": "Matériel", "agit_sur": "efficacite",
     "quoi": "Génération d'accélérateurs, durée de vie, taux de charge.",
     "porte": "Agit sur l'usage ET sur l'incorporé — allonger la durée de vie déplace "
              "la fabrication sur davantage d'années de service."},
    {"cle": "mix_electrique", "nom": "Mix électrique", "agit_sur": "ges",
     "quoi": "Localisation des centres, contrats d'origine, décarbonation du réseau.",
     "porte": "Ne change RIEN à l'électricité consommée ni à l'énergie primaire : "
              "il ne déplace que les émissions. Le confondre avec un gain "
              "d'efficacité est l'erreur la plus commune."},
    {"cle": "efficacite_centres", "nom": "Efficacité des centres de données",
     "agit_sur": "efficacite",
     "quoi": "PUE, famille de refroidissement, récupération de chaleur.",
     "porte": "Agit sur le petit facteur : un PUE de 1,6 ramené à 1,2 retire 25 % de "
              "l'énergie d'infrastructure, pas 25 % du total."},
]


def trajectoire(base_annuelle, adoption, efficacite, depuis, jusqu_a=2030):
    """Projection d'une empreinte annuelle, année par année.

    Chaque année : × (1 + adoption/100) × (1 − efficacité/100). Les deux taux
    se composent, ils ne s'additionnent pas — et c'est ce qui fait qu'une
    adoption de 40 % ne s'annule pas avec une efficacité de 40 %."""
    if base_annuelle is None or jusqu_a < depuis:
        return {"nature": "indisponible", "points": [],
                "motif": "aucune base annuelle, ou horizon antérieur à l'origine"}
    a, e = float(adoption) / 100.0, float(efficacite) / 100.0
    if e >= 1.0:
        return {"nature": "indisponible", "points": [],
                "motif": "un gain d'efficacité de 100 % ou plus n'a pas de sens"}
    facteur = (1.0 + a) * (1.0 - e)
    points, v = [], float(base_annuelle)
    for an in range(int(depuis), int(jusqu_a) + 1):
        points.append({"annee": an, "valeur": v})
        v *= facteur
    fin = points[-1]["valeur"]
    return {"nature": "projete", "points": points,
            "facteur_annuel": facteur, "base": float(base_annuelle),
            "multiple": fin / float(base_annuelle) if base_annuelle else None,
            "adoption": float(adoption), "efficacite": float(efficacite),
            "motif": None}


def trajectoires(base_annuelle, depuis, jusqu_a=2030):
    """Les cinq repères, sur la même base — c'est l'écart entre eux qui informe,
    pas l'un d'eux pris seul."""
    out = []
    for s in SCENARIOS:
        t = trajectoire(base_annuelle, s["adoption"], s["efficacite"], depuis, jusqu_a)
        t.update({"cle": s["cle"], "nom": s["nom"], "lecture": s["lecture"]})
        out.append(t)
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  7. LA COUVERTURE, ET L'ÉTAT DU MODULE
# ═══════════════════════════════════════════════════════════════════════════

def couverture(systemes):
    """Ce qui est déclaré, et ce qui manque — AVANT tout montant.

    Le total d'un parc à moitié déclaré n'est pas « approximatif », il est
    faux : il ne compte que ce qu'on lui a donné. La couverture se lit donc
    d'abord."""
    total = len(systemes or [])
    avec_volume = avec_fin = 0
    manque_volume, manque_fin = [], []
    for s in (systemes or []):
        nom = s.get("nom") or s.get("id") or "?"
        if s.get("volume_sortie_mois"):
            avec_volume += 1
        else:
            manque_volume.append(nom)
        d = s.get("ajustement_fin") or {}
        if d and not [c for c in A_DECLARER_FIN if not d.get(c)]:
            avec_fin += 1
        elif d:
            manque_fin.append(nom)
    return {"systemes": total,
            "volume_declare": avec_volume, "volume_manquant": sorted(manque_volume),
            "ajustement_declare": avec_fin, "ajustement_incomplet": sorted(manque_fin),
            "chiffrable": avec_volume, "part": (avec_volume / total) if total else 0.0}


def etat(aujourdhui=None):
    """Ce que le module sait de lui-même : facteurs dus à révision, valeurs
    substituées par l'environnement, indicateurs absents, eau disponible."""
    j = aujourdhui or date.today()
    dus = [{"cle": c, "libelle": f["libelle"], "revision_due": f["revision_due"]}
           for c, f in FACTEURS.items() if date.fromisoformat(f["revision_due"]) <= j]
    subs = [c for c, f in FACTEURS.items() if f.get("substitue")]
    ouverts = [{"cle": c, "point": f["point_ouvert"]}
               for c, f in FACTEURS.items() if f.get("point_ouvert")]
    return {"version": VERSION, "facteurs": len(FACTEURS),
            "revision_due": dus, "substitues": subs, "points_ouverts": ouverts,
            "indicateurs_servis": [i["cle"] for i in indicateurs_servis()],
            "indicateurs_absents": [i["cle"] for i in indicateurs_absents()],
            "eau_disponible": _eau_dc() is not None,
            "scenarios": len(SCENARIOS), "leviers": len(LEVIERS_2030)}


# ═══════════════════════════════════════════════════════════════════════════
#  8. LE JUMEAU — ce qu'une règle peut garder, et ce qu'elle ne peut pas
# ═══════════════════════════════════════════════════════════════════════════
#
# CE QU'UNE RÈGLE DANS CE DÉPÔT NE PEUT PAS FAIRE. Elle ne peut pas lire
# l'autre dépôt : les deux sont des copies de travail distinctes, et l'intégration
# n'en voit qu'une. Prétendre garder l'identité depuis ici serait écrire une
# règle qui passe pour une raison sans rapport avec ce qu'elle prétend — le
# défaut qu'on corrige partout ailleurs.
#
# CE QU'ELLE PEUT FAIRE, ET QUI SUFFIT À RENDRE LA DÉRIVE VISIBLE. Le fichier
# porte l'empreinte de son propre contenu. Modifier une copie sans la
# re-tamponner fait tomber la règle du dépôt modifié, tout de suite. Et les deux
# empreintes déclarées se comparent d'un coup d'œil, ou par
# `outils/verifier_jumeaux.py`, qui est le seul endroit à voir les deux.
#
# POURQUOI CE MÉCANISME ET PAS UN COMMENTAIRE. `equipements_it.py` annonce
# depuis son en-tête qu'il est « PARTAGÉ À L'IDENTIQUE » ; ses deux copies
# divergent de trente-six lignes, et l'écart n'est pas cosmétique : l'une
# requalifie ses sources en hypothèses du cabinet, l'autre continue d'annoncer
# des empreintes produit constructeurs. Le même module, deux vérités, et c'est
# le site le plus exposé qui portait la plus flatteuse.

import hashlib
import re as _re

JUMEAU = {
    "depots": ("conseilprev", "conseilprevcyber"),
    "fichier": "empreinte_ia.py",
    "empreinte": "80ad6d6323d2240a",
    "porte": "Les facteurs, leurs sources, les trois méthodes, l'ajustement fin "
             "et les trajectoires. Tout ce qui se calcule des deux côtés.",
}


def _sans_empreinte(texte):
    """Le texte, l'empreinte déclarée mise à blanc — sans quoi elle se
    référencerait elle-même et ne pourrait jamais tomber juste."""
    return _re.sub(r'"empreinte": "[0-9a-f]*"', '"empreinte": ""', texte, count=1)


def empreinte_du_fichier(chemin=None):
    """L'empreinte de ce fichier tel qu'il est sur le disque."""
    c = chemin or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               JUMEAU["fichier"])
    with open(c, "rb") as f:
        brut = f.read().decode("utf-8")
    return hashlib.sha256(_sans_empreinte(brut).encode("utf-8")).hexdigest()[:16]
