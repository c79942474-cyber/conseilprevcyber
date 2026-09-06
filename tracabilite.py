# -*- coding: utf-8 -*-
"""Quels moteurs tracent leurs calculs — et lesquels ne tracent RIEN.

CE QUE CE MODULE MESURE, ET POURQUOI IL A FALLU L'ÉCRIRE. Le site affirme que
« chaque résultat porte sa formule et ses entrées ». C'est vrai du moteur
énergie / eau / carbone. Ce ne l'est pas de tous, et l'affirmation générale
couvrait les exceptions : un lecteur qui ouvre une page sans infobulle croit
que la fonction est cassée, alors qu'elle n'a jamais existé pour ce moteur-là.

UNE ÉQUATION TRACÉE N'EST PAS UNE FORMULE ÉCRITE. Quatre degrés, et les
confondre est exactement ce que ce module empêche :

  1. AUCUNE TRACE — un nombre nu. Rien ne dit d'où il sort.
  2. TRACE SANS FORMULE — un nom, une valeur, une unité, parfois une source.
     Honnête, mais on ne peut pas refaire le calcul.
  3. FORMULE SANS ENTRÉES — « E_total = E_IT × PUE ». On lit la méthode, on ne
     peut pas la vérifier sur CE cas : les nombres manquent.
  4. ÉQUATION SUBSTITUABLE — formule ET entrées, donc « E_total = 6 833,10 ×
     1,35 = 9 224,28 ». C'est le seul degré qui permet de CONTESTER un résultat
     sans lire le code.

Le décompte porte sur le degré 4, et les trois autres sont rendus à part : dire
« 40 % tracé » en mélangeant les degrés ferait passer une méthode lisible pour
une équation vérifiable.

ON MESURE EN FAISANT TOURNER LES MOTEURS, jamais en lisant leur source. Compter
les occurrences de « formule » dans un fichier dirait ce que le code CONTIENT,
pas ce que l'utilisateur REÇOIT — et c'est ce qu'il reçoit qui est en cause. Un
moteur dont les traces ne sortent pas de la fonction compte donc pour zéro,
comme il le doit.
"""
VERSION = "2026-09-a"

# Un profil plausible et complet, celui d'un centre de données de 12 MW. Il
# n'est pas là pour être juste — il est là pour être ACCEPTÉ par tous les
# moteurs, afin qu'aucun ne compte zéro parce qu'il a refusé l'entrée.
PROFIL = {
    "puissance_it_kw": 12000.0,
    "taux_charge": 0.65,
    "pays": "FR",
    "refroidissement": "air_free_cooling",
    "classe_ashrae": "A1",
    "part_evaporative": 0.3,
    "cycles_concentration": 4.0,
    "part_renouvelable": 0.4,
    "part_chaleur_reutilisee": 0.15,
    "pue_cible": 1.25,
    "intensite_reseau_g": 56.0,
    "nb_serveurs": 9000,
}

# ── LES MOTEURS, DÉCLARÉS UN PAR UN, AVEC LEUR VRAI APPEL ─────────────────
# ÉNUMÉRÉS, JAMAIS DÉDUITS. Déduire la liste des modules du dossier ferait
# entrer d'office le prochain moteur écrit — et c'est précisément le moteur
# neuf, non encore tracé, qu'on veut voir apparaître dans la colonne « aucune
# équation » plutôt que d'y échapper.
#
# CHAQUE APPEL EST ÉCRIT, PAS DEVINÉ. Une première version essayait quelques
# signatures au hasard : douze moteurs sur quinze sont sortis « non
# joignables », et la mesure ne disait plus rien de la traçabilité — seulement
# de mes suppositions. Les signatures réelles diffèrent trop (certains veulent
# le résultat énergie, d'autres des quantités, d'autres rien) pour qu'un
# essai générique ait un sens.


def _contexte():
    """Ce que plusieurs moteurs prennent en entrée : l'étude énergie.

    Calculée UNE FOIS. La recalculer par moteur multiplierait le temps de la
    mesure sans rien changer au résultat.
    """
    import datacenter
    return {"energie": datacenter.energie(PROFIL)}


MOTEURS = [
    {"cle": "energie", "nom": "Énergie — PUE, consommation, pertes",
     "page": "/ingenierie-datacenter",
     "lancer": lambda c: __import__("datacenter").energie(PROFIL)},
    {"cle": "eau", "nom": "Eau — WUE, prélèvement, rejet",
     "page": "/ingenierie-datacenter",
     "lancer": lambda c: __import__("datacenter").eau(PROFIL, c["energie"])},
    {"cle": "carbone", "nom": "Carbone — scopes 1, 2 et 3",
     "page": "/ingenierie-datacenter",
     "lancer": lambda c: __import__("datacenter").carbone(PROFIL, c["energie"])},
    {"cle": "chaleur", "nom": "Chaleur fatale — gisement et valorisation",
     "page": "/ingenierie-datacenter",
     "lancer": lambda c: __import__("datacenter").chaleur(PROFIL, c["energie"])},
    {"cle": "scope1", "nom": "Scope 1 — groupes électrogènes et fluides",
     "page": "/ingenierie-datacenter",
     "lancer": lambda c: __import__("datacenter").scope1(PROFIL)},
    {"cle": "densite", "nom": "Densité — kW par baie, plancher, transport",
     "page": "/ingenierie-datacenter",
     "lancer": lambda c: __import__("densite_dc").salle(18.0)},
    {"cle": "financement", "nom": "Financement — sources et enveloppe",
     "page": "/ingenierie-datacenter",
     "lancer": lambda c: __import__("financement_dc").etude(
         enveloppe_eur=180e6, puissance_it_kw=PROFIL["puissance_it_kw"])},
    {"cle": "econome", "nom": "Économiste — chiffrage de l'ouvrage",
     "page": "/ingenierie-datacenter",
     "lancer": lambda c: __import__("econome_dc").chiffrer(
         __import__("econome_dc").operations()[0]["cle"])},
    {"cle": "moe", "nom": "Maîtrise d'œuvre — honoraires et missions",
     "page": "/ingenierie-datacenter",
     # `enveloppe_meur` est un ENCADREMENT (bas, haut), pas un montant : le
     # barème s'applique sur une fourchette. Passer un flottant faisait lever
     # « 'float' object is not iterable » — et la mesure le disait.
     "lancer": lambda c: __import__("moe_dc").honoraires(
         {c: 1.0 / len(__import__("moe_dc").LOTS_TECHNIQUE)
          for c in __import__("moe_dc").LOTS_TECHNIQUE}, (150.0, 210.0))},
    {"cle": "icpe", "nom": "ICPE — rubriques et seuils",
     "page": "/ingenierie-datacenter",
     "lancer": lambda c: __import__("icpe_dc").cribler(PROFIL)},
    {"cle": "equipements", "nom": "Équipements IT — parc et renouvellement",
     "page": "/ingenierie-datacenter",
     "lancer": lambda c: __import__("equipements_it").bilan_scope3(
         __import__("equipements_it").nomenclature(PROFIL["puissance_it_kw"]))},
    {"cle": "decarbonation", "nom": "Décarbonation — trajectoire et jalons",
     "page": "/decarbonation-datacenter",
     # Le référentiel nomme ses « étapes », pas ses « phases » : le mot
     # emprunté au moteur voisin faisait lever un KeyError.
     "lancer": lambda c: __import__("decarbonation").dossier(
         PROFIL, __import__("decarbonation").referentiel()["etapes"][0]["code"])},
    {"cle": "impact_client", "nom": "Client Impact — la comparaison",
     "page": "/etudes-de-cas",
     "lancer": lambda c: __import__("impact_client").comparer()},
    {"cle": "ia_factory", "nom": "IA Factory — postes, phases, jalons",
     "page": "/ingenierie-ia-factory",
     "lancer": lambda c: __import__("ia_factory").chiffrer(
         __import__("ia_factory").quantites_pour(None),
         __import__("ia_factory").referentiel()["prix"])},
]
# NOTE — `finops_ia` NE FIGURE PAS ICI, et l'absence est délibérée : ce module
# vit dans l'autre dépôt. L'avoir inscrit une première fois faisait dire à la
# mesure « module absent » pour un moteur qui n'a jamais eu à être ici.


def _trace(x):
    """Est-ce une trace ? Un dict qui porte au moins un nom et une valeur."""
    return (isinstance(x, dict) and "valeur" in x
            and ("nom" in x or "unite" in x or "formule" in x))


def parcourir(objet, _vus=None):
    """Toutes les traces d'un résultat, à toute profondeur.

    LES CYCLES SONT COUPÉS. Un moteur qui rendrait un objet se référençant
    lui-même ferait tourner la mesure à l'infini — et la mesure doit rendre un
    chiffre même sur un moteur mal fichu, sinon elle ne mesure rien du tout.
    """
    _vus = _vus if _vus is not None else set()
    if id(objet) in _vus:
        return []
    out = []
    if isinstance(objet, dict):
        _vus.add(id(objet))
        if _trace(objet):
            out.append(objet)
        for v in objet.values():
            out.extend(parcourir(v, _vus))
    elif isinstance(objet, (list, tuple)):
        _vus.add(id(objet))
        for v in objet:
            out.extend(parcourir(v, _vus))
    return out


def _degre(t):
    """Le degré de traçabilité d'UNE trace. Voir l'en-tête du module."""
    f = str(t.get("formule") or "").strip()
    e = t.get("entrees")
    if f and isinstance(e, dict) and e:
        return "equation"
    if f:
        return "formule_seule"
    return "trace_seule"


def _lancer(m, contexte):
    """Fait tourner un moteur, ou dit pourquoi il n'a pas tourné.

    UN MOTEUR QUI LÈVE N'EST PAS UN MOTEUR SANS ÉQUATION : c'est un moteur
    qu'on n'a pas su appeler, et le distinguer évite d'accuser le code d'un
    défaut qui est dans cette mesure-ci. La distinction a servi dès le premier
    passage — douze moteurs sur quinze étaient « non joignables » parce que
    j'avais deviné leurs signatures.
    """
    try:
        return m["lancer"](contexte), ""
    except Exception as e:                           # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, str(e)[:140])


def _ligne(m, **compte):
    """La ligne de rapport d'un moteur, SANS son appel.

    `lancer` est une fonction : la laisser dans le rapport rendrait celui-ci
    non sérialisable en JSON, et la route qui le sert échouerait — sur un
    module dont le seul rôle est de dire la vérité sur les autres.
    """
    out = {"cle": m["cle"], "nom": m["nom"], "page": m["page"],
           "traces": 0, "equations": 0, "formules_seules": 0,
           "traces_seules": 0}
    out.update(compte)
    return out


def mesurer():
    """Chaque moteur, ses traces, et son degré le plus haut."""
    contexte = _contexte()
    lignes = []
    for m in MOTEURS:
        res, motif = _lancer(m, contexte)
        if res is None:
            lignes.append(_ligne(m, joignable=False, motif=motif))
            continue
        traces = parcourir(res)
        degres = [_degre(t) for t in traces]
        lignes.append(_ligne(
            m, joignable=True, motif="", traces=len(traces),
            equations=degres.count("equation"),
            formules_seules=degres.count("formule_seule"),
            traces_seules=degres.count("trace_seule")))
    return lignes


def etat():
    """Ce que le site peut affirmer de sa traçabilité — et ce qu'il ne peut pas.

    LA LISTE DES MOTEURS SANS ÉQUATION EST LE PRODUIT DE CETTE FONCTION, pas
    une note d'accompagnement. Un pourcentage global lu seul ferait croire à
    une couverture uniforme ; ce sont les NOMS qui disent où l'infobulle ne
    s'ouvrira pas.
    """
    lignes = mesurer()
    joignables = [x for x in lignes if x["joignable"]]
    sans = [x for x in joignables if x["equations"] == 0]
    return {
        "version": VERSION,
        "moteurs": len(lignes),
        "joignables": len(joignables),
        "non_joignables": [{"cle": x["cle"], "motif": x["motif"]}
                           for x in lignes if not x["joignable"]],
        "avec_equation": [x["cle"] for x in joignables if x["equations"]],
        "sans_equation": [{"cle": x["cle"], "nom": x["nom"], "page": x["page"],
                           "traces": x["traces"],
                           "formules_seules": x["formules_seules"]}
                          for x in sans],
        "equations": sum(x["equations"] for x in joignables),
        "formules_seules": sum(x["formules_seules"] for x in joignables),
        "traces_seules": sum(x["traces_seules"] for x in joignables),
        "lignes": lignes,
        "note": NOTE,
    }


NOTE = (
    "« Tracé » se dit de quatre choses différentes, et une seule permet de "
    "contester un résultat sans lire le code : l'équation SUBSTITUÉE, celle "
    "qui porte les nombres du cas. Une formule sans ses entrées se lit, ne se "
    "vérifie pas. Les moteurs nommés ci-dessous n'en produisent aucune : leurs "
    "valeurs peuvent être justes, elles ne sont pas OPPOSABLES en séance. "
    "C'est une limite du site, dite ici plutôt que découverte devant un "
    "évaluateur.")
