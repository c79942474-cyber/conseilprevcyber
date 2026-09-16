# -*- coding: utf-8 -*-
"""LE LIVRABLE QUI MANQUAIT À L'INTERSECTION — carbone d'un programme d'IA.

MESURÉ SUR LE CATALOGUE : neuf livrables de gouvernance IA, aucun sur
l'empreinte ; des livrables carbone de centre de données, aucun sur l'IA. Le
trou était exactement là où se pose la seule question qu'un comité pose avant
de financer un programme d'IA — ce qu'il coûte en émissions, ce qu'il évite
ailleurs, et quand le net repasse sous le point de départ.

ET IL LUI FALLAIT SON PROPRE GROUPE. Le mettre dans « Conseil — Gouvernance
IA » l'aurait privé de toute matière carbone : les thèmes de ce groupe sont
l'AI Act, le RGPD, la gouvernance. Y ajouter les thèmes du carbone aurait fait
puiser les neuf autres livrables dans des analyses de cycle de vie qui ne leur
servent à rien — une charte de gouvernance écrite avec des notes de PUE serait
moins bonne, pas meilleure. Le défaut de pointage se corrige dans un sens ; il
se crée aussi bien dans l'autre.
"""
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import livrables                                                 # noqa: E402
import rag_store                                                 # noqa: E402


def test_le_livrable_de_bascule_EXISTE_et_atteint_le_carbone():
    """LA RÈGLE QUI PORTE LE TOUR. Un livrable dont le groupe ne désigne
    aucune matière carbone se rédigerait sans fonds — et cela ne se verrait
    pas : le texte sort, il est simplement générique."""
    t = livrables.get_type("ia-bascule-carbone")
    assert t, "le dossier de décision carbone d'un programme d'IA n'existe pas"
    _g, themes = livrables.themes_du_type("ia-bascule-carbone")
    assert themes, "ce livrable n'interroge aucun thème"
    carbone = [x for x in themes if "Carbone" in x or "Efficacité" in x
               or "Énergie" in x]
    assert len(carbone) >= 3, (
        "le groupe de ce livrable ne désigne pas la matière carbone : %s"
        % themes)


def test_les_themes_de_ce_groupe_EXISTENT_dans_la_base():
    """UN THÈME MAL ORTHOGRAPHIÉ NE RAMÈNE RIEN, EN SILENCE. La garde du
    module le vérifie au chargement ; on le mesure aussi ici, parce que ce
    groupe est neuf et que c'est au premier jour qu'on se trompe."""
    declares = set()
    for _f, ts in rag_store.THEME_FAMILLES:
        declares |= set(ts)
    _g, themes = livrables.themes_du_type("ia-bascule-carbone")
    for x in themes:
        assert x in declares, "« %s » n'existe pas dans rag_store" % x


def test_la_trame_EXIGE_la_mesure_avant_de_chiffrer():
    """UN ABATTEMENT ANNONCÉ ET JAMAIS CONSTATÉ EST LA FORME LA PLUS COURANTE
    DE L'ÉCOBLANCHIMENT. La section qui exige la mesure vient AVANT celle qui
    chiffre la trajectoire : dans l'autre ordre, on chiffre puis on cherche
    comment le justifier."""
    t = livrables.get_type("ia-bascule-carbone")
    s = t["sections"]
    mesure = next(i for i, x in enumerate(s) if "MESUR" in x.upper())
    chiffre = next(i for i, x in enumerate(s) if "Trajectoire" in x)
    assert mesure < chiffre, s
    # ET LA RÉSERVE EST UNE SECTION, pas une note de bas de page.
    assert any("déclaré" in x and "mesuré" in x for x in s), s


def test_la_trame_pose_la_question_du_RETOURNEMENT():
    """CE QUE LE CALCUL A MONTRÉ ET QU'AUCUNE PUBLICATION NE DIT : la bascule
    peut ne pas tenir. L'abattement plafonne quand l'empreinte compose. Une
    trame qui s'arrêterait à « année de bascule » ferait lire un gain acquis
    là où il est temporaire."""
    s = livrables.get_type("ia-bascule-carbone")["sections"]
    assert any("tient" in x.lower() for x in s), s
    assert any("freiner" in x.lower() or "relancer" in x.lower() for x in s), s


def test_les_NEUF_livrables_de_gouvernance_IA_restent_SANS_carbone():
    """LE DÉFAUT DE POINTAGE SE CRÉE DANS LES DEUX SENS.

    Il aurait été plus simple d'ajouter les thèmes du carbone au groupe
    existant. Les neuf chartes, RACI et politiques d'usage y auraient alors
    puisé des analyses de cycle de vie — et seraient sorties moins bonnes,
    sans que rien ne le signale."""
    _g, themes = livrables.themes_du_type("charte-gouvernance-ia")
    assert not [x for x in themes if "Carbone" in x or "Efficacité" in x], themes
