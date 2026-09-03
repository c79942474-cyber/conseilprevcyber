# -*- coding: utf-8 -*-
"""L'équation avec les données dedans — et le format des nombres, côté serveur.

CE QUE CE MODULE RÉSOUT. Les moteurs de ce site tracent leurs valeurs : chacune
porte sa FORMULE (« E_total = E_IT × PUE ») et ses ENTRÉES ({« E_IT (MWh) » :
6 833,10 ; « PUE » : 1,35}). Les deux étaient affichées côte à côte, et le
lecteur devait faire la substitution de tête. Elle se fait ici :

    E_total = 6 833,10 × 1,35 = 9 224,28

C'est cette ligne-là qu'on relit, et c'est elle qui permet de contester un
résultat sans lire le code.

ELLE DIT QUAND ELLE N'A PAS PU. Un symbole de la formule qui ne trouve pas son
entrée laisse un trou. Afficher « E_total = E_IT × 1,35 = 9 224,28 » serait pire
que de ne rien afficher : la moitié substituée donne l'illusion d'une
vérification. La substitution rend donc CE QU'ELLE N'A PAS REMPLACÉ, et
l'appelant décide — ici, on n'affiche pas.

LE FORMAT SUIT LA RÈGLE D'OR DU SITE, la même que `nombres.js` : un entier reste
un entier, un décimal ne descend jamais sous deux décimales. Deux
implémentations pour une seule règle, c'est un risque — une règle du dépôt
compare donc les deux sur les mêmes valeurs.
"""
import re

VERSION = "2026-09-a"

PLANCHER = 2          # jamais moins de deux décimales sur un décimal

# L'espace fine insécable, séparateur des milliers en typographie française.
_FINE = " "


def est_entier(x):
    try:
        return float(x) == int(float(x))
    except (TypeError, ValueError, OverflowError):
        return False


def fr(x, dec=None):
    """Le nombre tel qu'on l'AFFICHE — règle d'or comprise.

    `dec` permet d'en demander PLUS, jamais moins : sinon le paramètre
    servirait à contourner la règle depuis n'importe quel appel.
    """
    if x is None or x == "":
        return "—"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if v != v or v in (float("inf"), float("-inf")):
        return str(x)
    d = 0 if est_entier(v) else max(PLANCHER, PLANCHER if dec is None else dec)
    s = "{:,.{d}f}".format(v, d=d).replace(",", _FINE).replace(".", ",")
    return s


def exact(x):
    """Le nombre tel qu'il EST — sans arrondi, et sans les bavures du binaire.

    0,1 + 0,2 doit se lire « 0,3 » et non « 0,30000000000000004 » : cette
    seconde écriture ferait douter d'un calcul juste, ce qui est l'inverse du
    but recherché.
    """
    if x is None or x == "":
        return "—"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if est_entier(v):
        return fr(v)
    s = repr(round(v, 12))
    if "e" in s or "E" in s:
        s = "{:.12f}".format(v).rstrip("0")
    ent, _, dec = s.partition(".")
    dec = dec.rstrip("0")
    # AU MOINS DEUX, comme l'affichage : « 6 832,8 » à côté de « 6 832,80 »
    # est la même valeur écrite de deux façons, et cela fait douter des deux.
    dec = (dec + "00")[:max(PLANCHER, len(dec))]
    signe = "-" if ent.startswith("-") else ""
    ent = ent.lstrip("-")
    groupe = "{:,}".format(int(ent)).replace(",", _FINE)
    return signe + groupe + ("," + dec if dec else "")


# ═══════════════════════════════════════════════════════════════════════════
#  LA SUBSTITUTION
# ═══════════════════════════════════════════════════════════════════════════
# LE SYMBOLE N'EST PAS LA CLÉ. Les entrées portent leur unité entre
# parenthèses — « E_IT (MWh) » — parce que c'est ainsi qu'elles se lisent dans
# le détail. La formule, elle, ne connaît que « E_IT ». On enlève donc la
# parenthèse finale pour retrouver le symbole, et on garde l'unité pour la
# rendre à côté.

_UNITE = re.compile(r"\s*\(([^()]*)\)\s*$")


def _symbole(cle):
    """(symbole, unité) — « E_IT (MWh) » donne (« E_IT », « MWh »)."""
    m = _UNITE.search(cle or "")
    if not m:
        return (cle or "").strip(), None
    return (cle or "")[:m.start()].strip(), m.group(1).strip()


def _lisible(v):
    """Une entrée telle qu'elle s'écrit dans l'équation."""
    if isinstance(v, bool):
        return "oui" if v else "non"
    if isinstance(v, (int, float)):
        return fr(v)
    return str(v)


def substituer(formule, entrees, resultat=None, unite=None):
    """L'équation avec les données dedans.

    Rend un dict : `calcul` (la ligne à lire), `complet` (tous les symboles
    ont-ils été remplacés), `manquants` (ceux qui ne l'ont pas été) et
    `inutilises` (les entrées que la formule ne nomme pas — signe que le texte
    et le calcul ont divergé).

    ON NE SUBSTITUE QUE LA PARTIE DROITE. « E_total = E_IT × PUE » : remplacer
    à gauche donnerait « 9 224,28 = 6 833,10 × 1,35 », qui perd le nom de ce
    qu'on calcule. La grandeur garde son nom, ses termes prennent leurs
    valeurs.
    """
    formule = (formule or "").strip()
    entrees = entrees or {}
    if not formule:
        return {"calcul": None, "complet": False, "manquants": [],
                "inutilises": sorted(entrees), "pourquoi": "aucune formule"}

    gauche, sep, droite = formule.partition("=")
    if not sep:
        gauche, droite = "", formule

    # LES PLUS LONGS D'ABORD : sans cela « E » remplacerait le « E » de
    # « E_IT » et produirait une équation méconnaissable.
    paires = [(_symbole(k)[0], _symbole(k)[1], v) for k, v in entrees.items()]
    paires.sort(key=lambda p: -len(p[0]))

    faits, reste = [], droite
    for sym, un, val in paires:
        if not sym:
            continue
        motif = re.compile(r"(?<![\w²³])" + re.escape(sym) + r"(?![\w²³])")
        if motif.search(reste):
            reste = motif.sub(_lisible(val).replace("\\", ""), reste)
            faits.append(sym)

    inutilises = sorted(s for s, _u, _v in paires if s and s not in faits)

    # CE QUI RESTE DE SYMBOLIQUE. On cherche les mots qui ressemblent encore à
    # une grandeur : lettres, éventuellement souligné et chiffres, et qui ne
    # sont pas des unités ni des mots de liaison.
    _MOTS = {"de", "du", "des", "la", "le", "les", "et", "ou", "par", "sur",
             "en", "au", "aux", "si", "sinon", "avec", "sans", "total", "an",
             "h", "kW", "kWh", "MWh", "m", "L", "g", "kg", "t", "%", "min",
             "max", "moyenne", "somme", "nombre"}
    manquants = [m for m in re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9_]{1,}", reste)
                 if m not in _MOTS and not m.isdigit()]

    calcul = ((gauche.strip() + " = ") if gauche.strip() else "") + reste.strip()
    if resultat is not None:
        calcul += " = " + fr(resultat) + ((" " + unite) if unite else "")
    return {
        "calcul": calcul,
        "complet": not manquants,
        "manquants": manquants,
        "inutilises": inutilises,
        "pourquoi": None if not manquants else (
            "des grandeurs de la formule n'ont pas d'entrée : %s"
            % ", ".join(manquants[:4])),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  L'ÉQUATION SUBSTITUÉE SE VÉRIFIE — elle ne se croit pas
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE CETTE PARTIE CHANGE, ET C'EST BEAUCOUP. Une équation substituée est de
# l'ARITHMÉTIQUE : « 1 200 × 0,65 × 8 760 / 1000 ». On peut donc la calculer et
# comparer au résultat que le moteur affiche. « L'équation décrit le calcul »
# cesse d'être une affirmation et devient une MESURE — et une équation qui ne
# retombe pas sur sa valeur est une équation fausse, affichée avec l'assurance
# d'une preuve.
#
# L'ÉVALUATION EST FERMÉE PAR CONSTRUCTION. On n'accepte que des chiffres, des
# séparateurs, quatre opérateurs et des parenthèses ; tout le reste fait
# renoncer. Il n'y a pas de nom à résoudre, donc rien à exécuter.

_ARITH = re.compile(r"^[\d\s,.\u202f\u00a0()+\-*/×÷−–—]+$")


def _en_python(expr):
    """L'expression telle qu'un évaluateur la comprend, ou None."""
    e = (expr or "").strip()
    if not e or not _ARITH.match(e):
        return None
    for a, b in (("×", "*"), ("÷", "/"), ("−", "-"), ("–", "-"), ("—", "-")):
        e = e.replace(a, b)
    # Les séparateurs de milliers partent, la virgule décimale devient point.
    e = e.replace(_FINE, "").replace("\u00a0", "").replace(" ", "")
    e = e.replace(",", ".")
    return e


def evaluer(expr):
    """La valeur de l'expression, ou None si elle n'est pas de l'arithmétique."""
    e = _en_python(expr)
    if e is None:
        return None
    try:
        return float(eval(e, {"__builtins__": {}}, {}))     # noqa: S307
    except Exception:
        return None


def verifier(calcul, valeur, tolerance=0.02):
    """(vérifiable, retombe, écart) — l'équation substituée redonne-t-elle la
    valeur affichée ?

    LA TOLÉRANCE N'EST PAS DE LA COMPLAISANCE : l'équation est écrite avec les
    entrées ARRONDIES à deux décimales, donc son résultat ne peut pas coller au
    centième près sur des grandeurs à cinq chiffres. On compare en RELATIF, et
    2 % laisse passer l'arrondi d'affichage sans laisser passer une formule
    fausse — un facteur oublié se voit à 100 %.
    """
    if calcul is None or valeur is None:
        return False, False, None
    droite = calcul.split("=")[-1] if "=" in calcul else calcul
    # Le membre juste avant le résultat final, quand il y en a un.
    parts = [p for p in calcul.split("=") if p.strip()]
    candidat = parts[-2] if len(parts) >= 3 else droite
    v = evaluer(candidat)
    if v is None:
        return False, False, None
    try:
        cible = float(valeur)
    except (TypeError, ValueError):
        return False, False, None
    ecart = abs(v - cible) / max(abs(cible), 1e-9)
    return True, ecart <= tolerance, ecart


def bulle(trace):
    """Ce qu'une infobulle de calcul doit porter, à partir d'une valeur tracée.

    CINQ CHOSES, ET PAS UNE DE MOINS : l'équation, la même avec les données, le
    résultat EXACT (l'affichage est arrondi, celui-ci ne l'est pas),
    l'incertitude, la source. Une seule qui manque, et le chiffre redevient un
    chiffre qu'on croit sur parole.
    """
    if not isinstance(trace, dict) or "valeur" not in trace:
        return None
    s = substituer(trace.get("formule"), trace.get("entrees"),
                   trace.get("valeur"), trace.get("unite"))
    return {
        "nom": trace.get("nom"),
        "formule": trace.get("formule"),
        # UNE SUBSTITUTION INCOMPLÈTE NE S'AFFICHE PAS. La moitié substituée
        # donne l'illusion d'une vérification, ce qui est pire qu'aucune.
        "calcul": s["calcul"] if s["complet"] else None,
        "calcul_incomplet": None if s["complet"] else s["pourquoi"],
        "exact": exact(trace.get("valeur")),
        "unite": trace.get("unite"),
        "incertitude": trace.get("incertitude"),
        "source": trace.get("source"),
        "note": trace.get("note"),
    }
