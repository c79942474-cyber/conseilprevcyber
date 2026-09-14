# -*- coding: utf-8 -*-
"""LES TROIS TEMPS DU § 14 — et l'ordre de la page remis dans le sens du geste.

LE DÉFAUT, VISIBLE À L'ŒIL NU UNE FOIS NOMMÉ. La section portait neuf gestes
mis bout à bout, et son ordre contredisait l'ordre du travail : « Tout remplir
automatiquement » — l'atelier — venait AVANT le dépôt du dossier de
consultation, alors qu'il ne peut rien faire sans lui. Le bouton restait donc
inerte en tête de section, avec une phrase pour expliquer pourquoi.

CE QUE CES RÈGLES TIENNENT, et pourquoi elles ne se contentent pas de compter
trois intertitres :

  · l'ORDRE des trois temps, mesuré sur leur position dans la page ;
  · la POSITION de l'atelier : après le dépôt ET après la fiche, parce que
    c'est ce qui rend le bouton utilisable au moment où on le voit ;
  · le numéro est porté par la page, pas par une puce CSS : c'est une
    information — ces trois temps sont un ordre — et il doit survivre à la
    lecture d'un lecteur d'écran.
"""
import io
import os
import re

import pytest


def _lire(nom):
    ici = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return io.open(os.path.join(ici, nom), encoding="utf-8").read()


def _section():
    h = _lire("ingenierie-datacenter.html")
    d = h.index('<div class="rc-etape"><span class="n">14</span>')
    f = h.index('<div class="rc-etape"><span class="n">15</span>', d)
    return h[d:f]


def _temps():
    """Les trois intertitres, dans l'ordre où la page les pose."""
    return re.findall(r'<h3 class="ig-ao-temps[^"]*"><span>(\d)</span>([^<]+)</h3>',
                      _section())


def test_la_section_porte_bien_trois_temps_numerotes():
    t = _temps()
    assert len(t) == 3, "relevé : %r" % (t,)
    assert [n for n, _ in t] == ["1", "2", "3"], (
        "les temps ne se suivent pas : %r" % ([n for n, _ in t],))


# UNE RÈGLE RETIRÉE, ET LA RAISON EST ÉCRITE ICI PLUTÔT QUE PERDUE.
# J'avais posé « chaque intertitre commence par un verbe », éprouvé sur le
# suffixe du premier mot. C'est un contrôle SYNTAXIQUE : il tombait sur
# « Tout produire » — un titre parfaitement clair — et il aurait laissé
# passer n'importe quel nom finissant en -er. Une règle qui se satisfait
# d'une terminaison ne mesure pas si un titre dit quoi faire. Plutôt que de
# tordre le texte pour la satisfaire, elle est retirée : les six qui restent
# mesurent l'ORDRE et la POSITION, qui sont, eux, vérifiables.


def test_l_atelier_vient_APRES_le_depot_et_APRES_la_fiche():
    """LE POINT DE TOUT LE REGROUPEMENT. Un atelier placé avant le dépôt est
    un bouton inerte au moment où on le lit."""
    sec = _section()
    atelier = sec.index('id="ao-atelier-bloc"')
    depot = sec.index('id="ig-ao-depot"')
    fiche = sec.index('id="ig-ao-fiche"')
    assert depot < atelier, "l'atelier est proposé avant le dépôt du dossier"
    assert fiche < atelier, "l'atelier est proposé avant la fiche à compléter"


def test_le_troisieme_temps_precede_immediatement_l_atelier():
    """Un intertitre « Tout produire » posé loin de l'atelier annoncerait un
    geste qu'on ne trouve pas sous lui."""
    sec = _section()
    troisieme = sec.index('<span>3</span>')
    atelier = sec.index('id="ao-atelier-bloc"')
    assert troisieme < atelier
    entre = sec[troisieme:atelier]
    assert '<h3 class="ig-ao-temps' not in entre, (
        "un autre temps s'est glissé entre le titre et l'atelier")
    assert entre.count("<div") <= 2, (
        "l'atelier n'est plus sous son intertitre : %d blocs les séparent"
        % entre.count("<div"))


def test_le_numero_est_dans_la_page_et_non_dans_la_feuille():
    """UNE PUCE CSS NE SE LIT PAS À VOIX HAUTE. Ces trois temps sont un ordre :
    le numéro est une information, et il doit être dans le texte."""
    css = _lire("styles.css")
    i = css.index(".ig-ao-temps")
    bloc = css[i:i + 1400]
    assert "counter-increment" not in bloc and "content:" not in bloc, (
        "le numéro est généré par la feuille de style : un lecteur d'écran "
        "ne l'annoncera pas")
    for n, _t in _temps():
        assert n.isdigit()


def test_la_classe_des_temps_est_definie():
    """LA PREMIÈRE ÉCRITURE CHERCHAIT LA CHAÎNE N'IMPORTE OÙ — et
    « .ig-ao-temps > span » la satisfaisait. Renommer le bloc principal y
    survivait donc : les intertitres perdaient leur mise en forme et la règle
    restait verte. On exige désormais un BLOC DE RÈGLE à ce sélecteur exact."""
    css = _lire("styles.css")
    assert re.search(r"(?m)^\.ig-ao-temps\s*\{", css), (
        "les intertitres sont posés sans bloc de style propre : ils "
        "passeraient pour des sous-titres ordinaires")
    # ET LE TÉMOIN : la page emploie bien cette classe, sinon la règle
    # garderait un style que plus personne ne porte.
    assert 'class="ig-ao-temps' in _section()


def test_les_trois_temps_ne_paraissent_pas_au_visiteur_sans_droit():
    """Toute la section est un outil interne : ses blocs portent `ig-ao-op`,
    et les intertitres ne doivent pas faire exception."""
    for m in re.finditer(r'<h3 class="(ig-ao-temps[^"]*)"', _section()):
        assert "ig-ao-op" in m.group(1), (
            "un intertitre reste visible sans droit : " + m.group(1))
