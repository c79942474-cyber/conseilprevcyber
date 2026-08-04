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
        "note": "Borne PHYSIQUE basse de l'évaporatif pur. Aucune tour ne fait "
                "mieux : c'est l'eau qu'il faut évaporer pour évacuer la chaleur. "
                "Tout chiffre inférieur annoncé par un fournisseur signale soit "
                "un refroidissement partiellement sec, soit une erreur.",
    },
}

# Facteur eau de la production électrique (Energy Water Intensity Factor).
# C'est l'eau CONSOMMÉE (évaporée, non restituée), pas l'eau prélevée : la
# distinction change les résultats d'un facteur dix sur le nucléaire en circuit
# ouvert, et la confondre est l'erreur la plus fréquente des dossiers.
EWIF_PAYS = {
    "FR": {"valeur": 1.30, "mix": "nucléaire majoritaire, hydraulique",
           "note": "Forte évaporation des tours aéroréfrigérantes du parc nucléaire."},
    "DE": {"valeur": 1.10, "mix": "renouvelables, gaz, charbon résiduel"},
    "SE": {"valeur": 0.45, "mix": "hydraulique, nucléaire, éolien"},
    "NO": {"valeur": 0.30, "mix": "hydraulique quasi exclusif"},
    "FI": {"valeur": 0.55, "mix": "nucléaire, biomasse, hydraulique"},
    "IE": {"valeur": 0.55, "mix": "éolien, gaz"},
    "NL": {"valeur": 0.80, "mix": "gaz, éolien offshore"},
    "ES": {"valeur": 1.00, "mix": "solaire, éolien, gaz, nucléaire"},
    "IT": {"valeur": 1.05, "mix": "gaz, hydraulique, solaire"},
    "PL": {"valeur": 1.60, "mix": "charbon majoritaire"},
    "DK": {"valeur": 0.35, "mix": "éolien majoritaire"},
    "UE": {"valeur": 1.00, "mix": "moyenne européenne, à défaut de pays renseigné"},
}
EWIF_SOURCE = ("Ordres de grandeur convergents de la littérature sur l'intensité "
               "en eau de la production électrique (consommation, hors prélèvement "
               "restitué). À REMPLACER par la valeur du fournisseur ou de "
               "l'exploitant du réseau dès qu'elle est disponible : ces facteurs "
               "varient fortement selon la technologie de refroidissement des "
               "centrales, pas seulement selon le mix.")

# Intensité carbone du réseau, en gCO2e par kWh consommé. Moyenne annuelle.
# La moyenne annuelle ne convient PAS pour arbitrer un pilotage horaire : voir
# `avertissements` dans le résultat.
INTENSITE_RESEAU = {
    "FR": 56, "SE": 41, "NO": 30, "FI": 79, "DK": 151, "IE": 296,
    "DE": 344, "NL": 268, "ES": 158, "IT": 257, "PL": 635, "UE": 242,
}
INTENSITE_SOURCE = ("Ordres de grandeur de l'intensité carbone moyenne des mix "
                    "électriques européens. Pour une offre, utiliser la donnée "
                    "officielle du gestionnaire de réseau de l'année de référence, "
                    "ou le facteur contractuel du fournisseur (approche « market-based », "
                    "GHG Protocol Scope 2 Guidance).")

# Familles de refroidissement. Les plages recouvrent des conceptions réelles ;
# elles ne remplacent pas une étude de site, elles servent à cadrer et comparer.
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
                 "Environments. Plages d'air à l'entrée des équipements.")

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
                    "publiées du secteur. À REMPLACER par les déclarations "
                    "environnementales produit (FDES / EPD) des équipements "
                    "réellement retenus dès qu'elles sont disponibles : l'écart "
                    "entre un ordre de grandeur et une EPD peut atteindre un "
                    "facteur deux.")

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
        penalite = 0.0
        if taux < 0.60:
            penalite = (0.60 - taux) * 0.45
        pue = (pue_bas + pue_haut) / 2 + penalite
        origine = ("moyenne de la plage de conception de la famille retenue, "
                   "majorée de la pénalité de charge partielle")
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
            "±10 % (température d'air et d'eau réelles)",
            "Borne physique : aucune tour ne consomme moins pour la même chaleur."),
        "purge_m3": _tracer(
            "Eau de purge (déconcentration)", purge_m3, "m³/an",
            "V_purge = V_appoint − V_évap, avec V_appoint = V_évap × CoC/(CoC−1)",
            {"cycles de concentration": coc},
            "", "", "Augmenter les cycles réduit la purge mais durcit le "
                    "traitement d'eau et le risque d'entartrement."),
        "appoint_m3": _tracer(
            "Appoint d'eau total du site", appoint_m3, "m³/an",
            "V_appoint = V_évap × CoC / (CoC − 1)",
            {"V_évap (m³)": round(evaporation_m3, 1), "CoC": coc},
            "", "±15 %"),
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
        origine_i = f"moyenne annuelle du mix {pays}"
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
            INCORPORE_SOURCE, "±50 %", s["note"]),
        "incorpore_batiment_t": _tracer(
            "Carbone incorporé — bâtiment (amorti)", inc_batiment_t, "tCO2e/an",
            "= P_IT × kgCO2e par kW / durée de vie",
            {"P_IT (kW)": p_it, "kgCO2e/kW": b["valeur"], "durée de vie": b["duree_vie_ans"]},
            INCORPORE_SOURCE, "±50 %"),
        "incorpore_technique_t": _tracer(
            "Carbone incorporé — équipements techniques (amorti)", inc_technique_t,
            "tCO2e/an", "= P_IT × kgCO2e par kW / durée de vie",
            {"P_IT (kW)": p_it, "kgCO2e/kW": t["valeur"], "durée de vie": t["duree_vie_ans"]},
            INCORPORE_SOURCE, "±50 %"),
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
    if taux < 0.55:
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


def referentiel():
    """Le vocabulaire et les constantes, pour l'interface et la documentation."""
    return {
        "version": VERSION,
        "refroidissement": REFROIDISSEMENT,
        "classes_ashrae": CLASSES_ASHRAE,
        "ashrae_source": ASHRAE_SOURCE,
        "ewif": EWIF_PAYS,
        "ewif_source": EWIF_SOURCE,
        "intensite_reseau": INTENSITE_RESEAU,
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
     "aide": "Charge réelle moyenne rapportée à la puissance installée. "
             "Sous 0,55, la pénalité de charge partielle devient le premier poste de perte."},
    {"id": "pays", "label": "Pays d'implantation", "type": "liste",
     "options": sorted(EWIF_PAYS.keys())},
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
