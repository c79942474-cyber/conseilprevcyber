# -*- coding: utf-8 -*-
"""Base Carbone® ADEME v22.0 — lue sur le fichier, jamais recopiée.

POURQUOI CE MODULE, ET CE QU'IL NE FAIT PAS.

La Base Carbone est la référence RÉGLEMENTAIRE française : c'est elle qu'un
bilan d'émissions de gaz à effet de serre (BEGES, article L229-25 du code de
l'environnement) doit employer. Ce module la met à portée des moteurs du site,
avec son millésime et son incertitude.

IL NE REMPLACE AUCUNE VALEUR. Et c'est le point le plus important de ce
fichier, parce que le réflexe inverse est naturel et il serait faux.

  MESURÉ À L'INTÉGRATION, AOÛT 2026. Les facteurs « Électricité / mix moyen »
  de la v22.0 portent une période de validité de DÉCEMBRE 2017 pour la plupart
  des pays, décembre 2019 pour six d'entre eux. Confrontés à INTENSITE_RESEAU
  (millésime 2023-2024, approche location-based), l'écart médian est de 37,7 %
  sur 28 pays : France 56 contre 79,1 (−29 %), Allemagne 344 contre 461
  (−25 %), Estonie 460 contre 1010 (−54 %).

  DEUX PAYS FONT EXCEPTION, ET DANS L'AUTRE SENS : la Norvège (30 contre 16,7)
  et la Suède (41 contre 29,6) sont ici plus ÉMETTRICES que ne le dit l'ADEME.
  Sur des réseaux hydrauliques et nucléaires, le facteur est petit et l'écart
  relatif s'emballe sans que l'écart absolu pèse — 13 gCO2e/kWh de différence
  sur la Norvège ne déplacent aucune décision d'implantation.

  LE DÉNOMINATEUR EST DIT, PARCE QU'IL CHANGE LE CHIFFRE. Tous les écarts de
  ce module rapportent la VALEUR EMPLOYÉE au FACTEUR ADEME, qui est ici la
  référence : (employé − ADEME) / ADEME. Rapporté à l'autre base, le même fait
  français s'énoncerait « +41 % » au lieu de « −29 % » — les deux sont exacts,
  et publier l'un à côté de l'autre sans dire lequel est lequel serait
  exactement le genre de flou que ce dépôt traque ailleurs.

  LE LUXEMBOURG EST LE POINT SENSIBLE DE CETTE TABLE-CI. INTENSITE_RESEAU le
  donne à 110 gCO2e/kWh, ce qui le classe 6e pays le plus propre des 28 ; la
  Base Carbone le donne à 410 (17e) et l'autre site du cabinet à 220 (15e).
  Neuf places d'écart sur un seul facteur, pour un pays qui importe l'essentiel
  de son électricité. Rien ici ne permet de trancher, et RIEN N'A DONC ÉTÉ
  RÉÉCRIT — mais une implantation envisagée au Luxembourg ne doit pas être
  arbitrée sur ce facteur seul tant qu'un gestionnaire de réseau n'a pas
  fourni la valeur de l'année de référence.

  AUCUNE DES DEUX N'EST FAUSSE. Les réseaux européens se sont décarbonés vite
  entre 2017 et 2024 ; la Base Carbone n'a pas encore repris ces millésimes
  pour l'électricité étrangère. Substituer l'un à l'autre RENDRAIT LE CALCUL
  MOINS JUSTE, pas plus :

    — pour un BEGES français, un bilan sectoriel opposable ou une déclaration
      qui cite l'ADEME, c'est le facteur ADEME qui fait foi, quel que soit son
      âge : c'est le propre d'une référence réglementaire ;
    — pour comparer des pays en 2026 ou dimensionner un projet neuf, un
      facteur de 2017 décrit un réseau qui n'existe plus.

  Le module SERT DONC LES DEUX, en nommant l'usage de chacun. Il refuse de
  trancher à la place du lecteur, parce que la bonne valeur dépend de ce qu'il
  produit — et lui seul le sait.

CE QU'IL LIT. Le fichier officiel tel que téléchargé, dans `donnees/ademe/`.
Rien n'est recopié dans ce code : un facteur qui changerait dans le fichier
change ici, et un facteur absent du fichier est absent ici. C'est la règle du
dépôt, et elle vaut d'autant plus pour une base réglementaire.
"""
import csv
import os
import threading
from datetime import datetime, timezone

VERSION = "2026-08-a"

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "donnees", "ademe")
FICHIER = os.path.join(RACINE, "base_carbone_v22.csv")

# Le fichier de l'ADEME est publié en Windows-1252. Le lire en UTF-8 ne lève
# pas d'erreur partout : il abîme silencieusement les accents, et « Tchéquie »
# cesse alors de correspondre à « Tchéquie ». L'encodage est donc déclaré.
ENCODAGE = "cp1252"
SEPARATEUR = ";"

SOURCE = {
    "titre": "Base Carbone® — base de données publique de facteurs d'émission, v22.0",
    "editeur": "ADEME (Agence de la transition écologique)",
    "url": "https://base-empreinte.ademe.fr/",
    "nature": "referentiel",
    "note": "Référence RÉGLEMENTAIRE française : c'est elle qu'un bilan d'émissions "
            "de gaz à effet de serre (BEGES, art. L229-25 du code de "
            "l'environnement) doit employer. Les facteurs d'électricité "
            "étrangère de cette version portent une validité de 2017 à 2019 : "
            "ils font foi pour une déclaration, ils ne décrivent pas le réseau "
            "de 2026.",
}

# Les noms de pays tels que l'ADEME les écrit, vers le code à deux lettres
# employé partout ailleurs dans ce dépôt. Une correspondance explicite plutôt
# qu'une bibliothèque : trois orthographes coexistent dans le fichier
# (« Tchéquie » et « République tchèque »), et un rapprochement automatique les
# aurait manquées sans rien dire.
PAYS = {
    "France": "FR", "Allemagne": "DE", "Suède": "SE", "Irlande": "IE",
    "Espagne": "ES", "Pologne": "PL", "Pays-Bas": "NL", "Italie": "IT",
    "Finlande": "FI", "Grèce": "GR", "Belgique": "BE", "Danemark": "DK",
    "Autriche": "AT", "Portugal": "PT", "Tchéquie": "CZ",
    "République tchèque": "CZ", "Hongrie": "HU", "Roumanie": "RO",
    "Bulgarie": "BG", "Croatie": "HR", "Slovaquie": "SK", "Slovénie": "SI",
    "Estonie": "EE", "Lettonie": "LV", "Lituanie": "LT", "Luxembourg": "LU",
    "Malte": "MT", "Chypre": "CY", "Norvège": "NO", "Suisse": "CH",
    "Royaume-Uni": "GB", "Islande": "IS", "République Slovaque": "SK",
}

# LA CASSE DU FICHIER N'EST PAS STABLE, et s'y fier a coûté trois pays. La
# base écrit « République Tchèque » avec un T majuscule là où l'usage met une
# minuscule ; le rapprochement exact rendait donc la Tchéquie « absente de la
# Base Carbone », ce qui est faux et se serait lu comme un trou de la base
# plutôt que comme une faute de ce module. On compare sur une forme réduite.
_PAYS_REDUIT = {k.strip().lower(): v for k, v in PAYS.items()}


def _code_pays(nom):
    return _PAYS_REDUIT.get((nom or "").strip().lower())

_CACHE = {"lignes": None, "electricite": None}
_VERROU = threading.Lock()


def _nombre(v):
    """Le fichier écrit les décimales à la française. `float()` sur « 0,186 »
    ne lève pas : il rend 0.0 dans certains contextes et lève dans d'autres —
    des deux côtés, on perdrait la valeur sans le savoir."""
    if v is None:
        return None
    t = str(v).strip().replace(" ", "").replace(" ", "").replace(",", ".")
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def disponible():
    return os.path.exists(FICHIER)


def _charger():
    """Le fichier, lu une fois et gardé. Huit méga-octets relus à chaque
    requête coûteraient plus que tout le reste de la page."""
    if _CACHE["lignes"] is not None:
        return _CACHE["lignes"]
    with _VERROU:
        if _CACHE["lignes"] is not None:
            return _CACHE["lignes"]
        if not disponible():
            _CACHE["lignes"] = []
            return _CACHE["lignes"]
        with open(FICHIER, encoding=ENCODAGE, newline="") as f:
            _CACHE["lignes"] = list(csv.DictReader(f, delimiter=SEPARATEUR))
        return _CACHE["lignes"]


def electricite():
    """Les facteurs « Électricité / mix moyen », par pays et par frontière.

    DEUX FRONTIÈRES COEXISTENT DANS LA BASE, et les confondre fausse tout :
    « consommation » intègre les importations, l'autre décrit la production
    nationale. Pour un site raccordé au réseau d'un pays importateur, l'écart
    dépasse le facteur deux (Lituanie : 337 en production, 139 en consommation).
    On rend les deux, étiquetées.
    """
    if _CACHE["electricite"] is not None:
        return _CACHE["electricite"]
    out = {}
    for x in _charger():
        if (x.get("Nom base français") or "").strip() != "Électricité":
            continue
        if "mix moyen" not in (x.get("Nom attribut français") or ""):
            continue
        if (x.get("Type Ligne") or "") != "Elément":
            continue
        pays = _code_pays(x.get("Sous-localisation géographique français"))
        if not pays:
            continue
        v = _nombre(x.get("Total poste non décomposé"))
        if v is None:
            continue
        frontiere = (x.get("Nom frontière français") or "").strip() or "production"
        cle = "consommation" if frontiere.startswith("consommation") else "production"
        entree = {
            "g_kwh": round(v * 1000.0, 1),      # la base publie en kgCO2e/kWh
            "frontiere": cle,
            "validite": (x.get("Période de validité") or "").strip() or None,
            "incertitude_pct": _nombre(x.get("Incertitude")),
            "identifiant": (x.get("Identifiant de l'élément") or "").strip(),
        }
        # DEUX LIGNES POUR LA MÊME FRONTIÈRE : on garde la plus récente. Sans
        # cette règle, l'ordre du fichier déciderait, ce qui n'est pas une
        # méthode.
        vieux = out.setdefault(pays, {}).get(cle)
        if vieux is None or (entree["validite"] or "") > (vieux["validite"] or ""):
            out[pays][cle] = entree
    _CACHE["electricite"] = out
    return out


def facteur(pays, frontiere="production"):
    """Le facteur ADEME d'un pays, ou None. Jamais d'estimation de repli : un
    pays absent de la base est absent, et le dire vaut mieux que l'inventer."""
    e = electricite().get((pays or "").upper())
    if not e:
        return None
    return e.get(frontiere) or e.get("production") or e.get("consommation")


def poste(nom_base, attribut=None):
    """Un poste NOMMÉ de la base — « Serveurs informatiques », par exemple.

    L'électricité n'est pas le seul facteur d'émission que ces moteurs
    emploient : le carbone incorporé des machines et du bâti en est un autre,
    et il pèse lourd sur un centre de données. Cette fonction ouvre le reste de
    la base sans rien y recopier.

    ELLE REND UNE LISTE, PAS UNE VALEUR. Un poste porte souvent plusieurs
    éléments — un bâtiment industriel à structure béton et un autre à structure
    métallique n'ont pas la même empreinte, et les moyenner produirait un
    chiffre que personne n'a publié.
    """
    cible = (nom_base or "").strip().lower()
    out = []
    for x in _charger():
        if (x.get("Nom base français") or "").strip().lower() != cible:
            continue
        if (x.get("Type Ligne") or "") != "Elément":
            continue
        att = (x.get("Nom attribut français") or "").strip()
        if attribut and attribut.lower() not in att.lower():
            continue
        v = _nombre(x.get("Total poste non décomposé"))
        if v is None:
            continue
        out.append({
            "poste": (x.get("Nom base français") or "").strip(),
            "attribut": att or None,
            "valeur": v,
            "unite": (x.get("Unité français") or "").strip() or None,
            "incertitude_pct": _nombre(x.get("Incertitude")),
            "validite": (x.get("Période de validité") or "").strip() or None,
            "identifiant": (x.get("Identifiant de l'élément") or "").strip(),
        })
    return out


def encadre(valeur, ref):
    """La valeur employée tient-elle DANS l'incertitude déclarée par l'ADEME ?

    C'est la seule question qui vaille pour un ordre de grandeur : deux
    chiffres qui diffèrent d'un facteur deux ne se contredisent pas si la
    référence annonce ±80 %. On rend donc l'intervalle, la réponse, et de
    combien on en sort — jamais un verdict « juste / faux ».
    """
    v0 = ref.get("valeur")
    inc = ref.get("incertitude_pct")
    if v0 is None or valeur is None:
        return None
    if not inc:
        # SANS INCERTITUDE DÉCLARÉE, ON N'EN INVENTE PAS. L'encadrement est
        # alors impossible, et le dire vaut mieux que supposer un ±50 % maison.
        return {"encadre": None, "bas": None, "haut": None,
                "dit": "La référence ne déclare pas d'incertitude : il n'y a "
                       "pas d'intervalle dans lequel encadrer la valeur."}
    bas, haut = v0 * (1 - inc / 100.0), v0 * (1 + inc / 100.0)
    dedans = bas <= valeur <= haut
    if dedans:
        ecart = 0.0
    else:
        ecart = (valeur - haut) / haut * 100.0 if valeur > haut \
            else (valeur - bas) / bas * 100.0
    return {
        "encadre": dedans, "bas": round(bas, 1), "haut": round(haut, 1),
        "depassement_pct": round(ecart, 1),
        "dit": ("La valeur employée (%s) tient dans l'intervalle déclaré par "
                "l'ADEME [%s ; %s], à ±%s %%." % (valeur, round(bas, 1),
                                                  round(haut, 1), inc)
                if dedans else
                "La valeur employée (%s) SORT de l'intervalle déclaré par "
                "l'ADEME [%s ; %s] (±%s %%), de %.0f %%."
                % (valeur, round(bas, 1), round(haut, 1), inc, abs(ecart))),
    }


def comparer(pays, valeur_g_kwh, frontiere="production"):
    """Confronte une valeur employée par un moteur au facteur réglementaire.

    NE REND PAS UN VERDICT « juste / faux ». Les deux références décrivent des
    choses différentes ; ce qui se mesure, c'est l'écart, et ce qui s'écrit,
    c'est l'usage auquel chacune répond."""
    ref = facteur(pays, frontiere)
    if ref is None or valeur_g_kwh is None:
        return {"pays": pays, "connu": False,
                "dit": "Ce pays ne figure pas dans la Base Carbone v22.0 pour "
                       "l'électricité : aucune comparaison n'est possible."}
    ecart = valeur_g_kwh - ref["g_kwh"]
    rel = (ecart / ref["g_kwh"] * 100.0) if ref["g_kwh"] else None
    return {
        "pays": pays, "connu": True,
        "employe_g_kwh": valeur_g_kwh,
        "ademe_g_kwh": ref["g_kwh"],
        "frontiere": ref["frontiere"],
        "validite_ademe": ref["validite"],
        "incertitude_ademe_pct": ref["incertitude_pct"],
        "ecart_g_kwh": round(ecart, 1),
        "ecart_pct": round(rel, 1) if rel is not None else None,
        # LE SUJET DE LA PHRASE EST LA VALEUR EMPLOYÉE, ET LE DÉNOMINATEUR EST
        # LE FACTEUR ADEME. C'est la seule façon de faire dire à la phrase ce
        # que le calcul calcule. La rédaction inverse — « le facteur ADEME est
        # inférieur de X % à la valeur employée » — a produit un énoncé
        # impossible, mesuré sur l'Islande : « inférieur de 14 900 % », alors
        # qu'un manque plafonne à 100 %. Le rapport (30 − 0,2) / 0,2 dit de
        # combien la valeur employée DÉPASSE la référence, pas l'inverse ; et
        # un dépassement, lui, peut valoir 14 900 %. La même inversion sous-
        # estimait la France : la phrase annonçait 43 % là où sa propre
        # grammaire — un écart rapporté à la valeur employée — valait 76 %.
        "dit": ("La valeur employée ici (%s gCO2e/kWh) est %s de %.0f %% au "
                "facteur réglementaire ADEME (%s gCO2e/kWh, validité %s). "
                "Aucune des deux n'est fausse : la seconde fait foi pour un "
                "bilan réglementaire français, la première décrit le réseau de "
                "l'année en cours. Le choix dépend de ce que vous produisez."
                % (valeur_g_kwh,
                   "supérieure" if ecart > 0 else "inférieure",
                   abs(rel) if rel is not None else 0,
                   ref["g_kwh"], ref["validite"] or "non datée")),
    }


def confronter(table, frontiere="production"):
    """Confronte une table entière {pays: g/kWh} à la Base Carbone."""
    lignes = [comparer(p, v, frontiere) for p, v in sorted((table or {}).items())]
    connues = [x for x in lignes if x["connu"]]
    ecarts = sorted(abs(x["ecart_pct"]) for x in connues if x["ecart_pct"] is not None)
    # LA MOYENNE DES ÉCARTS RELATIFS EST DÉTRUITE PAR UN DÉNOMINATEUR QUASI NUL,
    # et c'est mesuré : l'Islande est à 0,2 gCO2e/kWh dans la base — géothermie
    # et hydraulique — contre 30 ici. L'écart relatif y vaut 14 900 %, ce qui
    # est arithmétiquement exact et statistiquement vide ; il tirait la moyenne
    # de 42 à 522 %. La MÉDIANE est l'énoncé honnête ; la moyenne reste servie,
    # avec ce qui la déforme, plutôt que retirée en silence.
    def _med(v):
        if not v:
            return None
        m = len(v) // 2
        return round(v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2.0, 1)
    quasi_nuls = [x["pays"] for x in connues if (x["ademe_g_kwh"] or 0) < 5]
    moyenne = round(sum(ecarts) / len(ecarts), 1) if ecarts else None

    # LA PHRASE S'ADAPTE À CE QU'ELLE A MESURÉ, au lieu de raconter toujours la
    # même histoire. Rédigée sur la table de l'autre site, qui contient
    # l'Islande, elle affirmait la déformation même quand il n'y avait rien
    # pour déformer : sur INTENSITE_RESEAU, qui ne descend pas sous 30
    # gCO2e/kWh, elle produisait « la moyenne est tirée par AUCUN PAYS, dont le
    # facteur ADEME est proche de zéro ». C'était faux et illisible, et cela ne
    # s'est vu qu'en confrontant une deuxième table — un défaut latent ne se
    # révèle qu'au deuxième cas d'emploi.
    if not ecarts:
        lecture = "aucune comparaison possible"
    elif quasi_nuls:
        lecture = ("Écart MÉDIAN de %s %% sur %d pays. La moyenne (%s %%) est "
                   "tirée par %s, dont le facteur ADEME est proche de zéro : un "
                   "écart relatif y est exact et sans portée."
                   % (_med(ecarts), len(connues), moyenne, ", ".join(quasi_nuls)))
    else:
        lecture = ("Écart MÉDIAN de %s %% sur %d pays, moyenne %s %%. Aucun "
                   "facteur ADEME n'est ici proche de zéro : la moyenne n'est "
                   "déformée par aucun dénominateur minuscule, et les deux "
                   "énoncés se valent."
                   % (_med(ecarts), len(connues), moyenne))

    return {
        "lignes": lignes,
        "pays_compares": len(connues),
        "pays_absents": [x["pays"] for x in lignes if not x["connu"]],
        "ecart_median_pct": _med(ecarts),
        "ecart_moyen_pct": moyenne,
        "ecart_max_pct": round(max(ecarts), 1) if ecarts else None,
        "references_quasi_nulles": quasi_nuls,
        "lecture": lecture,
        "source": SOURCE,
    }


def sante():
    e = electricite()
    return {
        "module": "base_carbone", "version": VERSION,
        "fichier_present": disponible(),
        "lignes": len(_charger()),
        "pays_electricite": len(e),
        "genere": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
