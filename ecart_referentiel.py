# -*- coding: utf-8 -*-
"""Ce que la carte promet, et ce que le moteur produit vraiment.

LE DÉFAUT QUE CE MODULE CORRIGE. Chaque étape du cadre de décarbonation porte
un champ `apport_moteur` — `complet`, `partiel` ou `cadre_seul`. C'est une
DÉCLARATION, écrite à la main, et rien ne la vérifie. Une fonction retirée, un
calcul déplacé, et l'affirmation reste en place : la carte continue de
promettre ce que le moteur ne fait plus, et personne ne s'en aperçoit avant
qu'un client le demande. Une carte qui ne peut pas se tromper est une carte
qu'on ne relit jamais.

DEUX CHOSES QU'IL NE FAUT SURTOUT PAS CONFONDRE, et c'est le cœur du module.
Constater qu'une VALEUR SORT ne dit pas qu'elle SATISFAIT le texte. Le moteur
produit un PUE de conception ; le PUE au sens d'ISO/IEC 30134-2 demande douze
mois de mesure. L'étape « KPI » le dit déjà dans sa preuve — « un PUE issu
d'une plage de conception n'est pas un PUE au sens d'ISO/IEC 30134-2 : c'est
une hypothèse de dimensionnement ». Une sonde qui déclarerait l'exigence
couverte parce qu'un nombre apparaît ferait exactement la faute contre laquelle
cette étape met en garde. Ce module rend donc TOUJOURS deux colonnes : ce que
le moteur produit, et ce qui reste à produire — la preuve, que nul calcul ne
remplace.

L'ÉCART SE LIT DANS UN SEUL SENS SANS AMBIGUÏTÉ. Une étape déclarée `complet`
ou `partiel` dont rien ne sort est une RÉGRESSION : le moteur ne fait plus ce
que la carte annonce. L'inverse — une étape déclarée `cadre_seul` d'où des
valeurs sortent — n'est pas une faute : c'est souvent le cas légitime du PUE de
conception. On le signale comme matière disponible non déclarée, à relire, et
jamais comme un défaut : accuser à tort userait le rapport plus vite qu'un
silence.

POURQUOI LE PROFIL DE SONDE N'EST PAS CELUI DES VALEURS PAR DÉFAUT. Sur les
défauts, le gazole vaut zéro, la charge de frigorigène aussi — et le scope 1 ne
produit rien, non parce qu'il est cassé, mais parce qu'on ne lui a rien donné à
compter. Une sonde bâtie sur les défauts déclarerait cette étape en régression
à chaque passage. Le profil ci-dessous EXERCE le moteur : c'est ce qui
distingue une sonde d'un contrôle de présence.
"""
import datacenter as D
import decarbonation as DEC
import etat_art

VERSION = "2026-08-a"

# ── LE PROFIL QUI FAIT TRAVAILLER LE MOTEUR ────────────────────────────────
# Un centre de taille moyenne, refroidi avec une part évaporative, doté de
# groupes électrogènes et d'une charge de frigorigène : de quoi solliciter
# l'énergie, l'eau, le carbone d'exploitation, le carbone incorporé, la chaleur
# fatale ET les émissions directes. Les valeurs n'ont aucune portée d'étude —
# elles ne servent qu'à faire tourner les calculs.
PROFIL_SONDE = {
    "puissance_it_kw": 2000, "taux_charge": 0.6, "pays": "FR",
    "refroidissement": None,            # laissé au défaut du moteur
    "part_evaporative": 0.5, "cycles_concentration": 4,
    "part_renouvelable": 0.4, "part_chaleur_reutilisee": 0.2,
    "nb_serveurs": 3000, "gazole_m3_an": 40,
    "charge_frigorigene_kg": 120, "taux_fuite_frigorigene": 5,
}

# ── CE QUE CHAQUE ÉTAPE DEVRAIT FAIRE SORTIR ───────────────────────────────
# `grandeurs` : chemins dans la sortie de `datacenter.etude()`.
# `hors_calcul` : l'étape n'attend AUCUNE grandeur, et dit pourquoi. C'est un
# état à part entière, jamais un écart : exiger d'un moteur qu'il produise une
# note de périmètre signée fabriquerait un manque qui n'en est pas un.
SONDES = {
    "PERIM": {"hors_calcul": "Une note de périmètre signée et opposable n'est "
                             "pas une grandeur : elle nomme des exclusions et "
                             "les motive."},
    "REF": {"grandeurs": ["carbone.empreinte_totale_t",
                          "energie.energie_totale_MWh"]},
    "INV": {"grandeurs": ["carbone.co2_exploitation_localise_t",
                          "carbone.co2_exploitation_marche_t",
                          "carbone.incorpore_serveurs_t",
                          "carbone.incorpore_batiment_t",
                          "carbone.incorpore_technique_t",
                          "carbone.empreinte_totale_t"],
            "postes": ["scope1"]},
    "KPI": {"grandeurs": ["energie.pue", "energie.dcie", "eau.wue_site",
                          "eau.wue_source", "carbone.cue", "carbone.ref",
                          "chaleur.erf", "chaleur.ere"]},
    "DECL": {"hors_calcul": "La déclaration réglementaire est un dépôt auprès "
                            "d'une autorité, pas un calcul : le moteur en "
                            "fournit la matière, il ne la dépose pas."},
    "VERIF": {"hors_calcul": "La vérification est le travail d'un tiers "
                             "accrédité. Un moteur qui se vérifierait lui-même "
                             "ne vérifierait rien."},
    "DIAG": {"grandeurs": ["carbone.part_incorpore_pct",
                           "carbone.empreinte_totale_t"]},
    "CIBLE": {"grandeurs": ["carbone.empreinte_totale_t"]},
    "EVIT": {"listes": ["leviers"]},
    "REDUI": {"grandeurs": ["energie.pue", "eau.evaporation_m3", "chaleur.erf"],
              "listes": ["leviers"]},
    "SUBST": {"grandeurs": ["carbone.co2_exploitation_marche_t",
                            "carbone.ref"]},
    "RESID": {"hors_calcul": "La neutralisation des émissions résiduelles ne "
                             "porte AUCUN paramètre du moteur — le module le "
                             "pose déjà en règle : un levier de compensation "
                             "ne réduit rien qui se calcule ici."},
}

# ── CE QUE LE FONDS NE DOCUMENTE PAS, ET LE TEXTE QUI L'EXIGE ─────────────
# LE CROISEMENT LE PLUS UTILE DU RAPPORT. Une lacune déclarée par l'état de
# l'art dit qu'on ne SAIT pas ; le texte rattaché dit qu'on DEVRAIT savoir ; et
# `lacunes.py` dit déjà où chercher au-dehors. Les trois séparément sont des
# constats ; ensemble, c'est une instruction de travail.
#
# La clé de gauche reprend la lacune de `etat_art.LACUNES` par son INDEX, et
# une règle vérifie que le texte visé existe : deux tables qui divergeraient
# donneraient au lecteur deux versions du même trou.
CROISEMENTS = [
    {"lacune": 0, "textes": ["iso14040", "ghg_scope3"], "etape": "INV",
     "dit": "Le moteur chiffre le carbone incorporé des serveurs, du bâtiment "
            "et des lots techniques. Ce qui manque n'est pas le calcul : c'est "
            "l'étude conduite selon ISO 14040 qui en établirait les frontières "
            "et l'unité fonctionnelle."},
    {"lacune": 1, "textes": ["iso30134"], "etape": "KPI",
     "dit": "Le WUE de site et le WUE de source sortent du moteur. Aucune "
            "donnée de terrain européenne ne permet encore de les confronter "
            "au réel."},
    {"lacune": 2, "textes": ["code_conduite", "iso30134"], "etape": "REDUI",
     "dit": "Le refroidissement liquide n'a pas de retour d'exploitation "
            "chiffré : le gain annoncé reste une comparaison technologique."},
    {"lacune": 3, "textes": ["eed_art12", "ddadue"], "etape": "DECL",
     "dit": "Le cadre français du raccordement et de l'effacement ne se déduit "
            "pas d'une moyenne européenne."},
    {"lacune": 4, "textes": ["ghg_corp", "fgas"], "etape": "INV",
     "dit": "Le moteur calcule le scope 1 des groupes électrogènes et des "
            "fuites de frigorigène. Ce qui manque est le carbone de la "
            "production sur site RECOMMANDÉE ailleurs : déplacer une "
            "consommation du réseau vers des machines à combustion transfère "
            "des émissions du scope 2 vers le scope 1, où aucun contrat de "
            "fourniture ne les efface."},
    {"lacune": 5, "textes": ["deee", "agec"], "etape": "REDUI",
     "dit": "La fin de vie et le réemploi entrent désormais au référentiel ; "
            "rien dans le fonds ne les documente encore."},
]

ETATS = {
    "conforme": "ce que la carte annonce, le moteur le produit",
    "regression": "la carte annonce une contribution du moteur, rien ne sort",
    "sous_declare": "des valeurs sortent que la carte n'annonce pas",
    "hors_calcul": "l'étape n'attend aucune grandeur, et dit pourquoi",
}


def _grandeur(etude, chemin):
    """La valeur au bout d'un chemin « groupe.grandeur », ou None."""
    groupe, _, nom = chemin.partition(".")
    bloc = (etude or {}).get(groupe)
    if not isinstance(bloc, dict):
        return None
    g = bloc.get(nom)
    if isinstance(g, dict) and g.get("valeur") is not None:
        return g
    return None


def _postes(etude, groupe):
    """Les postes d'un bloc qui n'a pas la forme d'un dictionnaire de grandeurs.

    `scope1` rend `{calcule, complet, postes: [...]}`. Une sonde qui ne
    connaîtrait que la première forme déclarerait cette étape en régression
    alors qu'elle calcule — une accusation fausse, qui use le rapport plus vite
    qu'un silence.
    """
    bloc = (etude or {}).get(groupe)
    if not isinstance(bloc, dict):
        return []
    return [p for p in (bloc.get("postes") or [])
            if isinstance(p, dict) and p.get("valeur") is not None]


def sonder(profil=None):
    """Ce que le moteur produit RÉELLEMENT, étape par étape."""
    etude = D.etude(dict(PROFIL_SONDE, **(profil or {})))
    lignes = []
    for e in DEC.ETAPES:
        code = e["code"]
        sonde = SONDES.get(code) or {}
        declare = e.get("apport_moteur")
        if sonde.get("hors_calcul"):
            dit = sonde["hors_calcul"]
            # UNE REMARQUE, PAS UN VERDICT. Une étape qui n'attend aucune
            # grandeur et qui annonce pourtant une contribution « complète » du
            # moteur n'est pas fautive — le moteur y apporte les ENTRÉES, pas
            # un résultat. Mais le mot « complet » se lira comme une promesse
            # de calcul par qui n'ouvre pas le détail, et cela mérite d'être
            # dit une fois plutôt que découvert en réunion.
            if declare in ("complet", "partiel"):
                dit += (" La carte annonce pourtant « %s » : le moteur y "
                        "apporte des ENTRÉES, aucun résultat." % declare)
            lignes.append({"code": code, "nom": e["nom"], "declare": declare,
                           "etat": "hors_calcul", "produit": [],
                           "attendu": [], "manquant": [],
                           "dit": dit,
                           "reste_a_produire": e.get("preuve") or "",
                           "textes": list(e.get("textes") or [])})
            continue
        attendu = list(sonde.get("grandeurs") or [])
        produit, manquant = [], []
        for chemin in attendu:
            g = _grandeur(etude, chemin)
            if g is None:
                manquant.append(chemin)
            else:
                produit.append({"chemin": chemin, "nom": g.get("nom"),
                                "unite": g.get("unite"),
                                "source": g.get("source")})
        for groupe in sonde.get("postes") or []:
            for p in _postes(etude, groupe):
                produit.append({"chemin": groupe, "nom": p.get("nom"),
                                "unite": p.get("unite"),
                                "source": p.get("source")})
        for nom in sonde.get("listes") or []:
            if etude.get(nom):
                produit.append({"chemin": nom, "nom": nom,
                                "unite": "%d entrée(s)" % len(etude[nom]),
                                "source": "moteur"})
        if declare in ("complet", "partiel") and not produit:
            etat, dit = "regression", (
                "La carte annonce « %s » et le moteur ne rend aucune grandeur "
                "pour cette étape." % declare)
        elif declare == "cadre_seul" and produit:
            etat, dit = "sous_declare", (
                "La carte annonce « cadre seul » alors que le moteur produit "
                "%d grandeur(s). Ce n'est PAS forcément une faute : une valeur "
                "de conception n'est pas une valeur déclarable. À relire, pas "
                "à corriger d'office." % len(produit))
        else:
            etat, dit = "conforme", ""
        lignes.append({"code": code, "nom": e["nom"], "declare": declare,
                       "etat": etat, "produit": produit, "attendu": attendu,
                       "manquant": manquant, "dit": dit,
                       # CE QU'AUCUN CALCUL NE REMPLACE. Toujours rendu, même
                       # quand tout sort : c'est la colonne qui empêche de lire
                       # « une valeur existe » comme « le texte est satisfait ».
                       "reste_a_produire": e.get("preuve") or "",
                       "textes": list(e.get("textes") or [])})
    return lignes


def croisements():
    """Les lacunes du fonds, le texte qui les exige, et l'étape concernée."""
    sortie = []
    for c in CROISEMENTS:
        sortie.append({
            "lacune": etat_art.LACUNES[c["lacune"]],
            "textes": [{"cle": t, "nom": DEC.TEXTES[t]["nom"],
                        "portee": DEC.TEXTES[t]["portee"]}
                       for t in c["textes"]],
            "etape": c["etape"], "dit": c["dit"]})
    return sortie


def analyse(profil=None):
    lignes = sonder(profil)
    compte = {}
    for l in lignes:
        compte[l["etat"]] = compte.get(l["etat"], 0) + 1
    return {"version": VERSION, "etapes": lignes, "resume": compte,
            "regressions": [l["code"] for l in lignes
                            if l["etat"] == "regression"],
            "croisements": croisements(),
            "reserve": "Une grandeur qui sort n'est pas une exigence "
                       "satisfaite : la colonne « reste à produire » dit ce "
                       "qu'aucun calcul ne remplace — douze mois de mesure, "
                       "une note signée, un vérificateur tiers."}


def glossaire():
    return {
        "sonde": "l'exécution RÉELLE du moteur sur un profil qui l'exerce — "
                 "pas un contrôle de présence de fonction",
        "regression": "la carte annonce une contribution du moteur, et rien "
                      "n'en sort : le seul écart qui se lit sans ambiguïté",
        "sous_declare": "des valeurs sortent que la carte n'annonce pas — à "
                        "relire, jamais un défaut : une valeur de conception "
                        "n'est pas une valeur déclarable",
        "hors_calcul": "l'étape n'attend aucune grandeur ; l'exiger "
                       "fabriquerait un manque qui n'en est pas un",
        "reste_a_produire": "ce qu'aucun calcul ne remplace — c'est la preuve "
                            "que le texte demande",
    }


def referentiel():
    return {"version": VERSION, "etapes": len(SONDES), "etats": ETATS,
            "croisements": len(CROISEMENTS),
            "profil_sonde": sorted(PROFIL_SONDE)}


def _verifier():
    fautes = []
    codes = {e["code"] for e in DEC.ETAPES}
    for code in SONDES:
        if code not in codes:
            fautes.append("sonde d'une étape inconnue : %s" % code)
    for code in codes:
        if code not in SONDES:
            fautes.append("étape sans sonde : %s — elle passerait pour "
                          "conforme sans avoir été regardée" % code)
    for code, s in SONDES.items():
        if not (s.get("grandeurs") or s.get("postes") or s.get("listes")
                or s.get("hors_calcul")):
            fautes.append("sonde %s : ni grandeur attendue ni motif de "
                          "hors-calcul" % code)
        if s.get("hors_calcul") and (s.get("grandeurs") or s.get("postes")):
            fautes.append("sonde %s : hors calcul ET grandeurs attendues" % code)
    for c in CROISEMENTS:
        if not 0 <= c["lacune"] < len(etat_art.LACUNES):
            fautes.append("croisement : lacune %r inconnue" % c["lacune"])
        for t in c["textes"]:
            if t not in DEC.TEXTES:
                fautes.append("croisement : texte inconnu %s" % t)
        if c["etape"] not in codes:
            fautes.append("croisement : étape inconnue %s" % c["etape"])
    vues = [c["lacune"] for c in CROISEMENTS]
    for i in range(len(etat_art.LACUNES)):
        if i not in vues:
            fautes.append("lacune %d déclarée par l'état de l'art et croisée "
                          "avec aucun texte : elle resterait un constat sans "
                          "instruction" % i)
    return fautes


_FAUTES = _verifier()
if _FAUTES:                                              # pragma: no cover
    raise RuntimeError("ecart_referentiel : incohérent — " + " ; ".join(_FAUTES))
