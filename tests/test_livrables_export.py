"""livrables_export.py — _PDF_MAP ne perd plus les espaces insécables.

LE DÉFAUT CORRIGÉ. _PDF_MAP visait à traduire, pour le PDF de secours sans
police Unicode (Helvetica, encodage latin-1), deux espaces typographiques
qui ne s'écrivent pas comme un espace ASCII ordinaire : l'espace insécable
(U+00A0) et l'espace fine insécable française (U+202F, le séparateur de
milliers « 1 234,56 € »). Les deux clés du dictionnaire littéral avaient été
aplaties par un passage d'éditeur en deux espaces ASCII identiques — la
seconde écrasant la première dans le dict, si bien qu'aucun des deux
caractères visés n'y figurait plus.

Conséquence observable dans _pdf_txt(unicode_ok=False) : le passage final
`s.encode("latin-1", "ignore")` (ligne ~728) SUPPRIME silencieusement tout
caractère hors du répertoire latin-1 — dont U+202F, qui n'y figure pas — au
lieu de le remplacer par un espace. Un montant comme « 1 234,56 € » se
retrouvait donc collé : « 1234,56€ », un nombre différent à la lecture.
"""
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import livrables_export as le  # noqa: E402


def test_pdf_map_porte_les_deux_espaces_distincts():
    m = le._PDF_MAP
    assert m.get("\xa0") == " "
    assert m.get(" ") == " "
    espaces_ascii = [k for k, v in m.items() if v == " "]
    assert sorted(espaces_ascii) == sorted(["\xa0", " "]), (
        "les deux clés doivent rester DISTINCTES dans le dict, pas "
        "collabées en une seule entrée d'espace ASCII")


def test_espace_fine_insecable_ne_disparait_plus_dans_un_montant():
    """Le cas exact du défaut : un séparateur de milliers français."""
    brut = "1 234,56 €"
    resultat = le._pdf_txt(brut, unicode_ok=False)
    assert "1234,56" not in resultat, (
        "l'espace fine insécable a été supprimé au lieu d'être normalisé : "
        "le nombre a changé de valeur à la lecture")
    assert "1 234,56" in resultat


def test_espace_insecable_devient_un_espace_ascii_normal():
    resultat = le._pdf_txt("mille\xa0euros", unicode_ok=False)
    assert resultat == "mille euros"
    assert "\xa0" not in resultat
