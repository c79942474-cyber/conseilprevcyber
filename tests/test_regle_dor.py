# -*- coding: utf-8 -*-
"""LA RÈGLE D'OR DES NOMBRES : on n'arrondit pas sous deux décimales.

CE QUI SE PASSAIT, ET QUI SE MESURE. Quatre copies quasi identiques du même
formateur vivaient dans quatre scripts, toutes avec le même barème : zéro
décimale au-dessus de cent, une entre dix et cent, trois en dessous. Sur les
valeurs réelles du moteur :

     5 857,4178 tCO2e/an   s'affichait « 5 857 »
    12 691,884  m³/an      s'affichait « 12 692 »
        13,9806 %          s'affichait « 14,0 »
         1,1489            s'affichait « 1,1 »

La dernière ligne a coûté une carte publique : la décomposition affichait
« 1,1 × 15,5 = 17,8 », et 1,1 × 15,5 fait 17,05. Un lecteur qui vérifie conclut
que le calcul est faux — sur la seule ligne dont l'intérêt est d'être
vérifiable.

CE QUE CES RÈGLES GARDENT, ET POURQUOI CE SONT DES PROPRIÉTÉS.

  — UN ENTIER RESTE UN ENTIER. « 3 000,00 serveurs » n'est pas plus exact que
    « 3 000 » : c'est la même valeur, écrite plus mal. La règle interdit
    d'ARRONDIR sous deux décimales ; elle n'oblige pas à inventer des décimales
    sur un nombre qui n'en a pas.
  — UN DÉCIMAL NE DESCEND JAMAIS SOUS DEUX. Y compris quand l'appelant demande
    moins : sinon le paramètre servirait à contourner la règle depuis
    n'importe quel appel.
  — AUCUN SCRIPT NE REFAIT SON BARÈME. C'est la duplication qui avait produit
    le défaut, et c'est elle qui le referait.
  — LA VALEUR EXACTE RESTE ACCESSIBLE. Deux décimales à l'écran pour que la
    ligne se lise ; la valeur entière dans l'infobulle pour qu'elle se
    vérifie. C'est la seule combinaison qui tienne les deux moitiés de la
    règle.
"""
import io
import json
import os
import re
import subprocess
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

MODULE = "nombres.js"

# Les scripts qui affichent des nombres calculés.
SCRIPTS = ["datacenter.js", "decarbonation-dc.js", "equipements-it.js",
           "ingenierie-dc.js", "ia-factory.js", "impact-client.js"]

# Les pages qui les portent.
PAGES = {"datacenter.html": "datacenter.js",
         "ingenierie-ia-factory.html": "ia-factory.js",
         "etudes-de-cas.html": "impact-client.js",
         "ingenierie-datacenter.html": "ingenierie-dc.js"}


def _src(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


def _formater(appels):
    """Ce que `nombres.js` rend RÉELLEMENT, obtenu en l'exécutant.

    Lire le fichier et y chercher « minimumFractionDigits » serait vert pour
    une option morte. On exécute, et on lit ce qui sort — comme le navigateur.
    """
    prog = (_src(MODULE)
            + "\nconst N = (typeof window !== 'undefined' ? window : this).CPNombres;"
            + "\nconst a = JSON.parse(process.env.CP_APPELS);"
            + "\nprocess.stdout.write(JSON.stringify("
            + "a.map(x => N[x[0]].apply(null, x.slice(1)))));\n")
    env = dict(os.environ, CP_APPELS=json.dumps(appels))
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60, env=env)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


# ── 1. Le barème ───────────────────────────────────────────────────────────

def test_un_entier_reste_un_entier():
    """Il n'est pas arrondi, il est EXACT : lui coller deux décimales
    l'écrirait plus mal sans le rendre plus juste."""
    rendus = _formater([["fr", 3000], ["fr", 0], ["fr", 1000000], ["fr", -42],
                        ["fr", 12]])
    for r in rendus:
        assert "," not in r, "un entier reçoit des décimales : %r" % r
    assert rendus[0].replace(" ", " ").replace(" ", " ") == "3 000"


@pytest.mark.parametrize("valeur", [5857.4178, 13.9806, 1.1489, 0.8573,
                                    12691.884, -42.5, 0.1, 99.999])
def test_un_decimal_ne_descend_jamais_sous_deux_decimales(valeur):
    """LE CŒUR DE LA RÈGLE. C'est cette ligne-là qui manquait, et son absence
    a produit une multiplication publique qui ne tombait pas juste."""
    rendu = _formater([["fr", valeur]])[0]
    assert "," in rendu, "« %s » perd toute décimale : %r" % (valeur, rendu)
    decimales = rendu.split(",")[1]
    assert len(decimales) >= 2, (
        "« %s » s'affiche %r — moins de deux décimales" % (valeur, rendu))


def test_le_parametre_ne_permet_pas_de_descendre_SOUS_le_plancher():
    """SANS CE VERROU, la règle se contourne depuis n'importe quel appel : il
    suffit de passer zéro. Le paramètre sert à en demander PLUS, jamais moins."""
    for demande in (0, 1):
        rendu = _formater([["fr", 5857.4178, demande]])[0]
        assert len(rendu.split(",")[1]) >= 2, (
            "fr(x, %d) contourne le plancher : %r" % (demande, rendu))
    plus = _formater([["fr", 5857.4178, 4]])[0]
    assert len(plus.split(",")[1]) == 4, (
        "le paramètre ne permet plus de demander davantage : %r" % plus)


def test_un_montant_ne_perd_pas_ses_centimes():
    """Sur un chiffrage à sept lots, sept arrondis à l'euro font une erreur
    qu'aucune ligne ne montre."""
    rendu = _formater([["euro", 1234.56], ["euro", 1000]])
    assert "1 234,56" in rendu[0].replace(" ", " ").replace(" ", " "), rendu[0]
    assert "," not in rendu[1], "un montant entier reçoit des centimes : %r" % rendu[1]


# ── 2. La valeur exacte reste accessible ───────────────────────────────────

def test_la_valeur_exacte_ne_perd_rien():
    """Deux décimales à l'écran pour que la ligne se lise, la valeur entière
    à côté pour qu'elle se vérifie."""
    rendus = _formater([["exact", 5857.4178], ["exact", 13.9806],
                        ["exact", 12691.884]])
    for attendu, rendu in zip(("4178", "9806", "884"), rendus):
        assert rendu.endswith(attendu), (attendu, rendu)


def test_la_valeur_exacte_ne_montre_pas_les_bavures_du_binaire():
    """0,1 + 0,2 ne doit pas se lire « 0,30000000000000004 » : cela ferait
    douter d'un calcul juste, ce qui est exactement l'inverse du but."""
    rendu = _formater([["exact", 0.1 + 0.2]])[0]
    assert rendu.replace(" ", " ") == "0,3", rendu


# ── 3. Plus aucun script ne refait son barème ──────────────────────────────

@pytest.mark.parametrize("script", SCRIPTS)
def test_aucun_script_ne_refait_l_echelle_de_decimales(script):
    """C'EST LA DUPLICATION QUI AVAIT PRODUIT LE DÉFAUT, et c'est elle qui le
    referait. Le barème « au-dessus de cent, zéro décimale » est parti de tous
    les scripts : il n'existe plus qu'à un seul endroit, et ce n'est aucun
    d'eux."""
    s = _src(script)
    # CE QU'ON CHERCHE EST L'ÉCHELLE, PAS `toFixed`. Ma première version
    # interdisait `toFixed(0)` tout court et tombait sur `datacenter.js`, où il
    # sert à poser l'abscisse d'un texte SVG : une coordonnée en pixels à deux
    # décimales est du bruit, pas une valeur affichée. Une règle qui confond la
    # géométrie et le nombre lu par l'utilisateur interdit du code juste.
    echelles = [
        (r">=\s*100\s*\?[^;]{0,90}toFixed\(0\)", "au-dessus de cent, zéro décimale"),
        (r">=\s*100\s*\?[^;]{0,90}Math\.round", "au-dessus de cent, arrondi entier"),
        (r">=\s*10\s*\?[^;]{0,90}toFixed\(1\)", "entre dix et cent, une décimale"),
    ]
    for motif, quoi in echelles:
        assert not re.search(motif, s, re.S), (
            "%s refait l'échelle de décimales : %s" % (script, quoi))
    for option in ("maximumFractionDigits: 0",
                   "maximumFractionDigits: dec == null ? 0 : dec",
                   "maximumFractionDigits: dec == null ? 1 : dec"):
        assert option not in s, (
            "%s formate en dessous du plancher : « %s »" % (script, option))


def _fonction(source, nom):
    """Le corps exact d'une fonction, par comptage d'accolades."""
    i = source.index("\n  function %s(" % nom) + 1
    j = source.index("{", i)
    p, k = 1, j + 1
    while p:
        if source[k] == "{":
            p += 1
        elif source[k] == "}":
            p -= 1
        k += 1
    return source[i:k]


# Le nom du formateur dans chaque script — ils ne s'appellent pas tous `fr`.
FORMATEURS = {"datacenter.js": "fr", "decarbonation-dc.js": "fr",
              "equipements-it.js": "fr", "ingenierie-dc.js": "fr",
              "ia-factory.js": "nombre", "impact-client.js": "nb"}


@pytest.mark.parametrize("script", SCRIPTS)
def test_le_formateur_de_chaque_page_OBEIT_a_la_regle(script):
    """CHERCHER UNE FORME DANS LE FICHIER NE SUFFIT PAS, et une mutation l'a
    montré : ma première version interdisait le barème écrit en ternaire, et
    survivait à exactement le même barème écrit en `if`. Une règle qui décrit
    la formulation qu'elle a retirée n'éprouve rien.

    ON EXÉCUTE DONC LE FORMATEUR DE LA PAGE, avec le module partagé réellement
    chargé, et on lit ce qu'il rend."""
    prog = (_src(MODULE)
            + "\nconst w = (typeof window !== 'undefined' ? window : this);"
            + "\nglobalThis.window = w;"
            + "\n" + _fonction(_src(script), FORMATEURS[script])
            + "\nconst f = " + FORMATEURS[script] + ";"
            + "\nprocess.stdout.write(JSON.stringify("
            + "[f(5857.4178), f(13.9806), f(1.1489), f(3000), f(5857.4178, 0)]));\n")
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60)
    assert out.returncode == 0, out.stderr
    rendus = json.loads(out.stdout)
    for r in rendus[:3]:
        assert "," in r and len(r.split(",")[1]) >= 2, (
            "le formateur de %s descend sous deux décimales : %r" % (script, r))
    assert "," not in rendus[3], (
        "le formateur de %s ajoute des décimales à un entier : %r"
        % (script, rendus[3]))
    assert len(rendus[4].split(",")[1]) >= 2, (
        "le formateur de %s laisse contourner le plancher par son paramètre : "
        "%r" % (script, rendus[4]))


@pytest.mark.parametrize("script", SCRIPTS)
def test_chaque_formateur_delegue_au_module_partage(script):
    """BORNÉ AU CORPS DU FORMATEUR, et pas au fichier : « CPNombres » figure
    aussi dans la fonction voisine `exact()`, et ma première version se
    satisfaisait d'elle pendant que le formateur, lui, avait cessé de
    déléguer."""
    corps = _fonction(_src(script), FORMATEURS[script])
    assert "CPNombres" in corps, (
        "le formateur de %s ne passe plus par le module partagé" % script)
    assert 'typeof window !== "undefined"' in corps, (
        "le formateur de %s appelle `window` sans garde : les règles de ce "
        "dépôt exécutent ce code dans Node, où `window` n'existe pas et lève"
        % script)


@pytest.mark.parametrize("page,script", sorted(PAGES.items()))
def test_chaque_page_charge_le_module_AVANT_le_script_qui_l_emploie(page, script):
    """Chargé après, il n'est pas là quand le script s'exécute : le repli
    prend la main et le barème redevient local sans que rien ne le signale."""
    h = _src(page)
    # ON CHERCHE LA BALISE, PAS LE NOM. Ma première version comparait les
    # positions des chaînes « /nombres.js » et « /impact-client.js » — et
    # trouvait la seconde dans un commentaire HTML placé plus haut dans la
    # page. La règle accusait un ordre de chargement parfaitement correct.
    a = '<script src="/nombres.js"'
    b = '<script src="/%s"' % script
    assert a in h, "%s ne charge pas le module partagé" % page
    assert b in h, "%s ne charge pas %s" % (page, script)
    assert h.index(a) < h.index(b), (
        "%s charge le module APRÈS %s" % (page, script))


def test_le_module_est_servi_et_versionne():
    """Un script référencé mais non servi rend la page inerte, et rien ne le
    signale côté serveur."""
    a = _src("app.py")
    assert '@app.route("/nombres.js")' in a, "le module n'est pas servi"
    # LA LISTE DE VERSIONNEMENT N'EST PAS LA LISTE DE SERVICE, et confondre les
    # deux a déjà rendu une page entièrement inerte dans ce dépôt. Ma première
    # version cherchait « "nombres.js", » dans TOUT app.py — et le trouvait
    # dans l'appel `_serve_fast("nombres.js", …)`. Elle était verte pour la
    # route pendant que le versionnement pouvait disparaître.
    i = a.index("_ASSETS_VERSIONNES = (")
    liste = a[i:a.index(")", i)]
    assert '"nombres.js"' in liste, (
        "le module n'est pas dans _ASSETS_VERSIONNES : son URL ne changera pas "
        "quand son contenu changera, et les navigateurs garderont l'ancien "
        "barème pendant un an")


def test_le_plancher_est_ecrit_UNE_FOIS():
    """Deux planchers divergeraient, et c'est le plus bas qui gagnerait."""
    s = _src(MODULE)
    assert s.count("var PLANCHER = ") == 1
    assert re.search(r"var PLANCHER = 2\b", s), "le plancher n'est plus deux"


@pytest.mark.parametrize("script", SCRIPTS)
def test_TOUT_appel_au_module_partage_est_garde(script):
    """LA RÈGLE PRÉCÉDENTE NE REGARDAIT QUE LE FORMATEUR NOMMÉ, et une mutation
    a franchi la porte par la fonction d'à côté : `euro()` dans ia-factory.js
    appelait `window.CPNombres` sans garde. En navigateur cela marche ; dans
    Node, où les règles de ce dépôt exécutent ce code, `window` lève une
    ReferenceError et emporte le script entier.

    On vérifie donc CHAQUE occurrence, pas une fonction choisie."""
    src = _src(script)
    i, nus = 0, []
    while True:
        i = src.find("window.CPNombres", i)
        if i < 0:
            break
        amont = src[max(0, i - 90):i]
        if 'typeof window !== "undefined"' not in amont:
            nus.append(src[max(0, i - 40):i + 30].replace("\n", " "))
        i += 1
    assert not nus, (
        "%s appelle le module partagé sans garde de contexte : %s"
        % (script, nus[:2]))
