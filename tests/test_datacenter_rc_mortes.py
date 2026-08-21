"""datacenter.html — 40 classes copiées de relecture-contrat.html, jamais
utilisées ici, sont retirées de son <style>.

LE DÉFAUT CORRIGÉ. Le <style> de cette page portait 44 classes `.rc-*` —
celles de relecture-contrat.html, copiées avec le reste de la feuille au
moment où les deux pages ont fusionné leur socle visuel. Seules quatre
survivent réellement sur CETTE page : `rc-socle`, `rc-sec` et `rc-etape`
(posées dans le HTML et lues par des scripts partagés — modules.js,
guide-etapes.js) et `rc-note` (posée par datacenter.js). Les 40 autres —
`rc-panneau`, `rc-onglets`, `rc-chat-tete`, `rc-msg`, etc. — ne
correspondent à AUCUN élément de cette page : plus de 11 Ko de CSS qui ne
peuvent jamais s'appliquer, et qu'un lecteur du fichier peut prendre pour
des styles actifs qu'il faudrait ménager en le modifiant.

CE QUE CE TEST NE VÉRIFIE PAS : le rendu visuel. Retirer une règle qui ne
correspond à AUCUN élément ne change rien à l'écran par construction — c'est
précisément ce qui distingue « mort » de « juste discret ». Le contrôle
porte donc sur ce qui reste défini, pas sur une capture d'écran.
"""
import os
import re
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

RESTENT = {"rc-socle", "rc-etape", "rc-sec", "rc-note"}
DISPARUES = {
    "rc-panneau", "rc-champs", "rc-lab", "rc-actions", "rc-fichier",
    "rc-nomfic", "rc-compteurs", "rc-cpt", "rc-synthese", "rc-onglets",
    "rc-colonnes", "rc-filtres", "rc-check", "rc-compte", "rc-t", "rc-niv",
    "rc-meta", "rc-corps", "rc-cit", "rc-pourquoi", "rc-chiffre", "rc-pos",
    "rc-repli", "rc-rouge", "rc-tbtn", "rc-inst", "rc-mvt", "rc-fleche",
    "rc-export", "rc-expbtn", "rc-chat-tete", "rc-ancre", "rc-focus",
    "rc-fil", "rc-msg", "rc-vide", "rc-sugg", "rc-saisie", "rc-pb",
}


def _html():
    with open(os.path.join(ICI, "datacenter.html"), encoding="utf-8") as f:
        return f.read()


def _style_block(html):
    return html[html.index("<style>") + 7: html.index("</style>")]


def test_les_quatre_classes_reellement_utilisees_restent_definies():
    style = _style_block(_html())
    defined = set(re.findall(r"\.(rc-[a-zA-Z0-9_-]+)", style))
    assert RESTENT <= defined, RESTENT - defined


def test_les_quarante_classes_copiees_de_relecture_contrat_ont_disparu():
    style = _style_block(_html())
    defined = set(re.findall(r"\.(rc-[a-zA-Z0-9_-]+)", style))
    survivantes = DISPARUES & defined
    assert not survivantes, (
        "ces classes copiées de relecture-contrat.html sont encore "
        "définies alors qu'aucun élément de cette page ne les porte : %s"
        % sorted(survivantes))


def test_le_style_a_perdu_plus_de_dix_kilo_octets():
    style = _style_block(_html())
    assert len(style) < 53000, (
        "le <style> ne s'est pas réellement allégé (%d octets) — "
        "la coupe des classes mortes ne s'est peut-être pas appliquée"
        % len(style))


def test_les_balises_et_les_accolades_restent_equilibrees():
    h = _html()
    assert h.count("<section") == h.count("</section>")
    assert h.count("<div") == h.count("</div>")
    style = _style_block(h)
    assert style.count("{") == style.count("}")
    assert style.count("/*") == style.count("*/")
