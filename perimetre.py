# -*- coding: utf-8 -*-
"""Ce qu'un compte client ouvre — lu sur le menu, jamais recopié.

POURQUOI PAS UNE LISTE ÉCRITE À LA MAIN. La page publique qui vend l'accès doit
dire ce que cet accès ouvre. Recopier les rubriques et leurs pages dans le HTML
donnerait un second exemplaire du menu, et c'est l'exemplaire qu'on oublie de
corriger qui reste : une page déplacée d'une rubrique à l'autre, une page
ajoutée, et la promesse commerciale décrit un site qui n'existe plus. Le menu
est la source ; on la lit.

CE QUI EST LU, ET COMMENT. `NAV_SECTIONS` dans `nav.js` — la même extraction que
la politique d'accès éprouve déjà dans ses essais. Chaque entrée est ensuite
croisée avec `acces.ouvert()` : c'est la politique elle-même qui dit ce qui
demande un compte, et non une appréciation portée ici.

QUAND LA LECTURE ÉCHOUE, ON NE REND RIEN. Un menu illisible (fichier déplacé,
structure changée) rendrait une liste vide ou tronquée. Servir « votre accès
ouvre 0 page » ou une liste amputée serait pire que se taire : l'appelant sait
distinguer une liste vide d'une absence, et la page n'affiche alors pas de
périmètre du tout.
"""
import os
import re
import threading

VERSION = "2026-08-a"

ICI = os.path.dirname(os.path.abspath(__file__))
MENU = "nav.js"

# Le bloc du tiroir : de « var NAV_SECTIONS » à sa fermeture. Les commentaires
# sont retirés avant l'extraction — une page citée dans une explication n'est
# pas une page du menu.
_DEBUT = "var NAV_SECTIONS"
_FIN = "\n  ];"
_SECTION = re.compile(r'\{\s*t:\s*"([^"]*)"\s*,\s*l:\s*\[(.*?)\]\s*\}', re.S)
_ENTREE = re.compile(r'\["(/[^"]*)"\s*,\s*"([^"]*)"\]')
_COMMENTAIRE = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)

_CACHE = {"valeur": None}
_VERROU = threading.Lock()


def _bloc(source):
    i = source.index(_DEBUT)
    return _COMMENTAIRE.sub("", source[i:source.index(_FIN, i)])


def rubriques(source=None):
    """Les rubriques du menu et leurs pages, dans l'ordre du menu.

    Rend `[]` quand le menu n'a pas pu être lu — l'appelant doit alors ne rien
    afficher, et surtout pas « aucune page ».
    """
    if source is None:
        with _VERROU:
            if _CACHE["valeur"] is not None:
                return [dict(r, pages=list(r["pages"])) for r in _CACHE["valeur"]]
    try:
        if source is None:
            with open(os.path.join(ICI, MENU), encoding="utf-8") as fh:
                source = fh.read()
        bloc = _bloc(source)
    except (OSError, ValueError):
        return []
    import acces
    out = []
    for titre, corps in _SECTION.findall(bloc):
        pages = [{"chemin": c, "titre": t, "ouverte": acces.ouvert(c)}
                 for c, t in _ENTREE.findall(corps)]
        if pages:
            out.append({"rubrique": titre, "pages": pages})
    if not out:
        return []
    with _VERROU:
        _CACHE["valeur"] = [dict(r, pages=list(r["pages"])) for r in out]
    return out


def ce_qui_est_vendu():
    """Les rubriques du menu qui demandent encore un compte, dans leur ordre.

    POURQUOI UNE FONCTION PLUTÔT QU'UNE PHRASE ÉCRITE DANS LES COURRIELS. Ils
    disaient « votre accès au cockpit de supervision » — le cockpit était UNE
    page sur les trente-quatre que l'accès ouvrait, et il est devenu gratuit le
    2 septembre 2026 : la phrase était fausse dans les deux régimes, d'abord
    par défaut, ensuite par excès. Un libellé recopié dans un courriel ne suit
    pas une politique d'accès ; une lecture, si.

    REND UNE LISTE VIDE QUAND LE MENU EST ILLISIBLE, et l'appelant doit alors
    se taire plutôt que d'inventer — même règle que le reste de ce module.
    """
    return [r["rubrique"] for r in rubriques()
            if any(not p["ouverte"] for p in r["pages"])]


def etat():
    """Le périmètre servi à la page : rubriques, et les deux comptes.

    Les deux comptes sont donnés séparément parce qu'ils répondent à deux
    questions différentes — « qu'est-ce que j'achète » et « qu'est-ce que je
    peux déjà lire sans rien demander ». Les additionner effacerait la seconde.
    """
    rub = rubriques()
    pages = [p for r in rub for p in r["pages"]]
    return {"version": VERSION, "rubriques": rub,
            "lisible": bool(rub),
            "n_client": sum(1 for p in pages if not p["ouverte"]),
            "n_ouvertes": sum(1 for p in pages if p["ouverte"])}
