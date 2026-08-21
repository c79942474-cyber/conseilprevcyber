"""gouvernance-ia.html ne dit plus deux fois la même promesse.

LE DÉFAUT CORRIGÉ. Le bloc « Livrables » est généré par
outils/generer_blocs_livrables.py — marqué LIVRABLES:DEBUT/FIN — et porte
déjà sa propre promesse (« rédigeable par l'IA… brouillon structuré… relu,
corrigé et validé par un consultant ») et la liste complète des neuf
livrables. Juste AVANT ce bloc, une section écrite à la main répétait la
MÊME promesse en termes presque identiques, suivie d'une liste plus courte
des mêmes livrables regroupés par volet — un texte que personne ne maintient
plus une fois le générateur en place, et qui finit par diverger de lui.

Comparaison avec les sept autres pages qui portent le même bloc généré
(architecture-cible.html, continuite-ot.html, feuille-de-route.html,
formation.html, gestion-des-changements.html, maturite-ot.html,
operating-model.html) : aucune ne répète la promesse ou la liste avant le
bloc généré — leur section manuscrite porte un contenu propre à la page.
gouvernance-ia.html est le seul à avoir dérivé.
"""
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)


def _html():
    with open(os.path.join(ICI, "gouvernance-ia.html"), encoding="utf-8") as f:
        return f.read()


def test_la_promesse_ia_brouillon_consultant_napparait_quune_seule_fois():
    h = _html()
    assert h.count("est relu") == 1, (
        "la promesse « rédigé par l'IA, relu et validé par un consultant » "
        "est encore répétée avant le bloc généré")


def test_la_liste_par_volets_a_disparu_le_bloc_genere_reste_seul():
    h = _html()
    assert "<strong>Volet 1</strong>" not in h
    assert "<strong>Volet 2</strong>" not in h
    assert h.lower().count("matrice raci ia") == 1, (
        "un livrable nommé deux fois signale que l'ancienne liste manuscrite "
        "est revenue à côté du bloc généré")


def test_le_cadre_reglementaire_reste_ecrit_avant_le_bloc_genere():
    """Ce que la coupe ne devait PAS emporter : la citation du cadre légal ne
    figure nulle part dans le bloc généré, elle est propre à cette page."""
    h = _html()
    i = h.index("LIVRABLES:DEBUT")
    avant = h[:i]
    assert "AI Act" in avant and "RGPD" in avant and "ISO/IEC 42001" in avant


def test_le_bloc_genere_est_toujours_intact():
    h = _html()
    assert h.count("<!-- LIVRABLES:DEBUT") == 1
    assert h.count("<!-- LIVRABLES:FIN -->") == 1
    assert "liv-promesse" in h
    assert h.count('class="liv-i"') == 9


def test_les_balises_restent_equilibrees():
    h = _html()
    assert h.count("<section") == h.count("</section>")
    assert h.count("<div") == h.count("</div>")
