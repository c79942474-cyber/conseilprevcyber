# -*- coding: utf-8 -*-
"""LES MODULES PARTAGÉS ENTRE LES DEUX DÉPÔTS, COMPARÉS POUR DE VRAI.

POURQUOI CET OUTIL EST DEHORS ET PAS DANS LES ESSAIS. Une règle d'essai ne voit
qu'un dépôt : celui où elle tourne. Elle peut vérifier qu'un module porte
l'empreinte de son propre contenu — et elle le fait —, mais elle ne peut pas
savoir ce que l'autre copie contient. Cet outil-ci est le seul endroit qui voit
les deux, parce qu'il est lancé là où les deux sont présents.

CE QU'IL A TROUVÉ LE 8 SEPTEMBRE 2026, ET QUI A MOTIVÉ TOUT LE RESTE :

    equipements_it.py    36 lignes d'écart — et l'écart n'est pas cosmétique :
                         la copie cyber requalifie ses sources en « HYPOTHÈSE
                         DU CABINET, PAS UNE MESURE », celle de Sentinel
                         annonce encore des empreintes produit constructeurs
                         et la base Boavizta. Le même module, deux vérités, et
                         c'est le site le plus exposé qui portait la plus
                         flatteuse.
    base_carbone.py      38 lignes d'écart.
    moe_dc.py            identique — par discipline, aucune règle ne le tenait.

USAGE :  python3 outils/verifier_jumeaux.py <dépôt A> <dépôt B>
"""
import hashlib
import io
import os
import sys

# LA LISTE N'EST PAS ICI : elle est dans `jumeaux.py`, avec les empreintes et
# les divergences assumées. En recopier une seconde ici aurait créé le doublon
# que cet outil existe pour trouver — et il aurait été le premier à ne pas se
# voir lui-même.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import jumeaux as _J                                                # noqa: E402

JUMEAUX = tuple(_J.JUMEAUX)
ASSUMES = dict(_J.DIVERGENTS_ASSUMES)


def _empreinte(chemin):
    if not os.path.exists(chemin):
        return None
    brut = io.open(chemin, encoding="utf-8").read()
    return hashlib.sha256(brut.encode("utf-8")).hexdigest()[:16]


def comparer(a, b):
    """Rend, par module : présent des deux côtés, identique, et l'écart en
    lignes quand il y en a un."""
    out = []
    for nom in JUMEAUX:
        pa, pb = os.path.join(a, nom), os.path.join(b, nom)
        ea, eb = _empreinte(pa), _empreinte(pb)
        ecart = None
        if ea and eb and ea != eb:
            la = io.open(pa, encoding="utf-8").read().split("\n")
            lb = io.open(pb, encoding="utf-8").read().split("\n")
            import difflib
            ecart = sum(1 for d in difflib.unified_diff(la, lb, n=0)
                        if d[:1] in "+-" and d[:3] not in ("+++", "---"))
        out.append({"module": nom, "a": ea, "b": eb,
                    "present": bool(ea and eb), "identique": bool(ea and ea == eb),
                    "ecart_lignes": ecart})
    return out


def main():
    if len(sys.argv) != 3:
        print(__doc__.strip().splitlines()[-1])
        return 2
    a, b = sys.argv[1], sys.argv[2]
    res = comparer(a, b)
    faux = 0
    for nom, raison in sorted(ASSUMES.items()):
        print("  ASSUMÉ      %-22s divergence voulue — %s" % (nom, raison[:64] + "…"))
    for r in res:
        if not r["present"]:
            print("  ABSENT      %-22s %s" % (r["module"],
                  "manque dans A" if not r["a"] else "manque dans B"))
            faux += 1
        elif r["identique"]:
            print("  IDENTIQUE   %-22s %s" % (r["module"], r["a"]))
        else:
            print("  DIVERGENT   %-22s %s ≠ %s — %d ligne(s)"
                  % (r["module"], r["a"], r["b"], r["ecart_lignes"]))
            faux += 1
    print("\n%d module(s) sur %d en écart." % (faux, len(res)))
    return 1 if faux else 0


if __name__ == "__main__":
    sys.exit(main())
