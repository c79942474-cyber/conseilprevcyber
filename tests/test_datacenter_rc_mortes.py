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


def test_aucune_classe_rc_n_est_definie_sans_etre_employee():
    """LA LISTE FIXE EN A MANQUÉ UNE QUARANTE-ET-UNIÈME. `rc-chat` était
    définie dans la feuille, absente des quatre gardées ET des quarante
    retirées — donc surveillée par personne. Elle n'était portée par aucun
    élément de la page ni posée par aucun script.

    Une liste nommée ne garde que ce qu'on a pensé à y écrire. Celle-ci
    ÉNUMÈRE ce qui est défini et vérifie que chacune sert : elle attrapera la
    quarante-deuxième sans qu'on ait à la prévoir."""
    h = _html()
    style = _style_block(h)
    hors_style = h[:h.index("<style>")] + h[h.index("</style>"):]
    scripts = ""
    for nom in sorted(os.listdir(ICI)):
        if nom.endswith(".js"):
            with open(os.path.join(ICI, nom), encoding="utf-8") as f:
                scripts += f.read()
    mortes = [c for c in sorted(set(re.findall(r"\.(rc-[a-zA-Z0-9_-]+)", style)))
              if c not in hors_style and c not in scripts]
    assert not mortes, (
        "classe(s) définie(s) dans le <style> et portée(s) par aucun élément "
        "ni posée(s) par aucun script : %s" % ", ".join(mortes))


def test_les_regles_rc_pesent_ce_que_pese_ce_qui_sert():
    """LA MESURE PORTE SUR CE QU'ELLE PROTÈGE, et plus sur la feuille entière.

    La règle d'origine plafonnait le <style> COMPLET à 53 000 octets pour
    prouver que la coupe s'était appliquée. C'était un cliquet : elle échouait
    à la première fonctionnalité ajoutée — la validation des saisies l'a fait
    passer à 54 679 — alors que rien de mort n'était revenu. Et elle ne
    protégeait rien que les deux règles voisines ne protègent mieux : ce sont
    elles qui disent si une classe morte est revenue.

    Ce qui se mesure ici est donc le poids des règles `rc-*` SEULES : quatre
    classes vivantes ne pèsent pas onze kilo-octets, et le retour du bloc
    copié se verrait aussitôt."""
    style = _style_block(_html())
    octets = sum(len(m.group(0))
                 for m in re.finditer(r"\.rc-[^{]*\{[^}]*\}", style))
    assert octets < 4000, (
        "les règles rc-* pèsent %d octets pour %d classes vivantes : le bloc "
        "copié de relecture-contrat.html est-il revenu ?"
        % (octets, len(RESTENT)))


def test_les_balises_et_les_accolades_restent_equilibrees():
    h = _html()
    assert h.count("<section") == h.count("</section>")
    assert h.count("<div") == h.count("</div>")
    style = _style_block(h)
    assert style.count("{") == style.count("}")
    assert style.count("/*") == style.count("*/")
