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
    # « 0,30 » et non « 0,3 » : la valeur exacte suit le même plancher de
    # deux décimales que l'affichage — la même valeur écrite de deux façons
    # dans la même infobulle ferait douter des deux. Ce qui est interdit
    # ici, c'est la traîne du binaire, pas le zéro de courtoisie.
    assert rendu.replace("\u202f", " ") == "0,30", rendu
    assert "0000" not in rendu, "la bavure du binaire est revenue : %r" % rendu


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


# ═══════════════════════════════════════════════════════════════════════════
#  L'ÉQUATION AVEC LES DONNÉES DEDANS — et elle se vérifie
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE CETTE PARTIE APPORTE. Les valeurs du moteur portaient leur formule et
# leurs entrées CÔTE À CÔTE : le lecteur devait faire la substitution de tête.
# Elle est faite au serveur — « E_total = 6 832,80 × 1,35 = 9 224,28 » — et,
# parce qu'une équation substituée est de l'arithmétique, ELLE EST CALCULÉE ET
# COMPARÉE À LA VALEUR. « L'équation décrit le calcul » cesse d'être une
# affirmation et devient une mesure.

import datacenter as D                                             # noqa: E402
import formules as F                                               # noqa: E402

PROFIL = {"puissance_it_kw": 1200, "taux_charge": 0.65, "nb_serveurs": 3000,
          "pays": "PL", "refroidissement": "eau_glacee",
          "part_evaporative": 0.7, "part_chaleur_reutilisee": 0.4,
          "temperature_rejet_c": 45}


def _tracees(etude=None):
    e = etude or D.etude(dict(PROFIL))
    for nom, bloc in e.items():
        if not isinstance(bloc, dict):
            continue
        for cle, t in bloc.items():
            if isinstance(t, dict) and "valeur" in t:
                yield "%s.%s" % (nom, cle), t


def test_les_deux_formateurs_du_site_disent_la_meme_chose():
    """DEUX IMPLÉMENTATIONS POUR UNE SEULE RÈGLE, C'EST UN RISQUE : celle du
    serveur (`formules.fr`) écrit les documents exportés, celle du navigateur
    (`nombres.js`) écrit l'écran. Le jour où elles divergent, le document ne
    dit plus ce que la page affiche."""
    valeurs = [3000, 0, 5857.4178, 13.9806, 1.1489, 0.8573, 12691.884, -42.5,
               1e6, 0.1 + 0.2, 99.999]
    py = [F.fr(v) for v in valeurs] + [F.exact(v) for v in valeurs]
    js = _formater([["fr", v] for v in valeurs] + [["exact", v] for v in valeurs])
    assert py == js, [(a, b) for a, b in zip(py, js) if a != b]


def test_chaque_valeur_tracee_porte_sa_valeur_exacte():
    """L'affichage est arrondi à deux décimales pour que la ligne se lise ; la
    valeur entière est là pour qu'elle se vérifie."""
    n = 0
    for nom, t in _tracees():
        assert t.get("exact") is not None, "%s n'a pas de valeur exacte" % nom
        n += 1
    assert n >= 20, "trop peu de valeurs tracées pour que la règle mesure"


def test_chaque_equation_chiffree_RETOMBE_sur_sa_valeur():
    """LA RÈGLE REFAIT LE CALCUL. Lire le drapeau `calcul_verifie` serait vert
    parce que le moteur le dit. On évalue l'équation affichée et on la compare
    à la valeur — une équation qui ne retombe pas dessus ne décrit pas ce
    calcul, et serait affichée avec l'assurance d'une preuve."""
    vus = 0
    for nom, t in _tracees():
        if not t.get("calcul"):
            continue
        vus += 1
        vf, retombe, ecart = F.verifier(t["calcul"], t["valeur"])
        assert vf, "%s : l'équation affichée n'est pas de l'arithmétique" % nom
        assert retombe, (
            "%s : l'équation « %s » donne un écart de %.1f %% avec la valeur"
            % (nom, t["calcul"], (ecart or 0) * 100))
        assert t.get("calcul_verifie") is True, nom
    assert vus >= 5, "trop peu d'équations chiffrées pour que la règle mesure"


def test_une_equation_qui_ne_retombe_pas_NE_S_AFFICHE_PAS(monkeypatch):
    """LE TÉMOIN, ET IL EST LE CŒUR DE LA GARANTIE. Une équation à moitié
    juste, présentée comme une vérification, est pire qu'aucune équation. On
    fausse le calcul du moteur et on vérifie que l'équation se retire en
    disant pourquoi."""
    vraie = D.energie

    def faussee(profil):
        r = vraie(profil)
        r["energie_totale_MWh"]["valeur"] *= 1.5
        return r

    monkeypatch.setattr(D, "energie", faussee)
    e = D.etude(dict(PROFIL))
    t = e["energie"]["energie_totale_MWh"]
    assert t.get("calcul") is None, (
        "une équation qui ne retombe pas sur sa valeur reste affichée")
    assert "ne retombe pas" in (t.get("calcul_incomplet") or ""), t


def test_une_substitution_incomplete_ne_s_affiche_pas_non_plus():
    """LA MOITIÉ SUBSTITUÉE DONNE L'ILLUSION D'UNE VÉRIFICATION. Seize valeurs
    du moteur ont une formule qui NOMME sa grandeur sans que les entrées en
    portent les termes : elles n'ont pas d'équation chiffrée, et elles le
    disent au lieu d'en montrer une à trous."""
    muettes = [(n, t) for n, t in _tracees()
               if t.get("formule") and not t.get("calcul")]
    assert muettes, "aucune valeur muette : la règle ne mesure rien"
    for nom, t in muettes:
        assert (t.get("calcul_incomplet") or "").strip(), (
            "%s se tait sans dire pourquoi" % nom)


def test_la_substitution_ne_confond_pas_un_symbole_avec_son_prefixe():
    """« E » NE DOIT PAS REMPLACER LE « E » DE « E_IT » : la substitution
    prendrait les symboles les plus courts d'abord et rendrait une équation
    méconnaissable."""
    # LE PREMIER CAS N'ÉPROUVAIT RIEN : la frontière de mot protège déjà « E »
    # dans « E_IT », puisque « _ » est un caractère de mot. Trier à l'envers ne
    # cassait rien, et la mutation survivait. LE VRAI CAS EST CELUI DES
    # SYMBOLES À ESPACES — et le moteur en a : « taux de charge » contient
    # « taux », qu'aucune frontière ne sépare.
    s = F.substituer("X = E_IT × E", {"E_IT (MWh)": 10, "E": 2}, 20)
    assert s["complet"] and "10" in s["calcul"] and "× 2" in s["calcul"], s

    s = F.substituer("X = taux de charge × taux",
                     {"taux de charge": 0.65, "taux": 2}, 1.3)
    assert s["complet"], s
    assert "0,65" in s["calcul"], (
        "« taux » a été substitué à l'intérieur de « taux de charge » : %s"
        % s["calcul"])
    assert "de charge" not in s["calcul"], (
        "le symbole long n'a pas été remplacé en entier : %s" % s["calcul"])


def test_la_substitution_ne_touche_pas_au_membre_de_gauche():
    """« 9 224,28 = 6 832,80 × 1,35 » perd le nom de ce qu'on calcule. La
    grandeur garde son nom, ses termes prennent leurs valeurs."""
    s = F.substituer("E_total = E_IT × PUE", {"E_IT (MWh)": 10, "PUE": 1.5}, 15)
    assert s["calcul"].startswith("E_total = "), s["calcul"]


def test_l_evaluateur_refuse_tout_ce_qui_n_est_pas_de_l_arithmetique():
    """L'ÉVALUATION EST FERMÉE PAR CONSTRUCTION : ni nom à résoudre, ni appel
    possible. Une expression qui n'est pas faite de chiffres et de quatre
    opérateurs fait renoncer."""
    for hostile in ("__import__('os').system('id')", "open('/etc/passwd')",
                    "1+1;print(2)", "a + b", "PUE × 2"):
        # LE GARDE-FOU EST ÉPROUVÉ POUR LUI-MÊME, et pas seulement le résultat
        # final : l'évaluation se fait déjà sans aucun nom résoluble, donc ces
        # expressions rendraient None même sans filtre — la mutation qui le
        # retirait survivait. On vérifie que le filtre REFUSE, en amont.
        assert F._en_python(hostile) is None, (
            "le filtre laisse passer « %s » : il ne reste que le bac à sable"
            % hostile)
        assert F.evaluer(hostile) is None, hostile
    assert abs(F.evaluer("1 200 × 0,65 × 8 760 / 1000") - 6832.8) < 1e-6


def test_l_infobulle_RENDUE_porte_reellement_les_cinq_choses():
    """CHERCHER « v.exact » DANS LA FONCTION NE SUFFIT PAS, et une mutation l'a
    montré : `if (false) l.push(…)` garde le mot et perd la ligne. On exécute
    `bulleCalcul` sur une valeur réelle du moteur et on lit ce qu'elle rend."""
    t = D.etude(dict(PROFIL))["energie"]["energie_totale_MWh"]
    prog = ('const esc = s => String(s == null ? "" : s);'
            + "\nconst fr = x => String(x);"
            + "\n" + _fonction(_src("datacenter.js"), "bulleCalcul")
            + "\nprocess.stdout.write(bulleCalcul(JSON.parse(process.env.CP_T)));")
    env = dict(os.environ, CP_T=json.dumps(t))
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60, env=env)
    assert out.returncode == 0, out.stderr
    h = out.stdout
    for etiquette in ("Équation", "Avec vos données", "Valeur exacte",
                      "Incertitude", "Source"):
        assert etiquette in h, "l'infobulle rendue ne porte pas « %s »" % etiquette
    assert t["exact"] in h, (
        "la valeur exacte n'est pas dans l'infobulle rendue")
    assert t["calcul"] in h, "l'équation chiffrée n'est pas rendue"
    assert t["source"][:30] in h, "la source n'est pas rendue"


def test_l_infobulle_porte_les_cinq_choses_et_s_ouvre_au_clavier():
    """UNE SEULE QUI MANQUE, et le chiffre redevient un chiffre qu'on croit sur
    parole. Et une infobulle qui n'existe qu'au passage de la souris exclut
    ceux qui n'en ont pas."""
    js = _src("datacenter.js")
    bloc = _fonction(js, "bulleCalcul")
    for attendu in ("v.formule", "v.calcul", "v.exact", "v.incertitude",
                    "v.source"):
        assert attendu in bloc, (
            "l'infobulle ne porte pas « %s »" % attendu)
    assert "v.calcul_incomplet" in bloc, (
        "l'infobulle ne dit pas pourquoi l'équation manque")
    h = _src("datacenter.html")
    assert ".dc-b-h:focus .dc-bulle" in h, (
        "l'infobulle ne s'ouvre pas au focus : elle exclut le clavier")
    assert ".dc-b-h:hover .dc-bulle" in h
    # Le porteur est un BOUTON : un div ne se focalise pas au clavier.
    assert '<button type="button" class="dc-val-v dc-b-h"' in js, (
        "la valeur n'est pas un bouton : l'infobulle sera inatteignable")
    assert 'aria-describedby=' in js and 'role="tooltip"' in js


def test_les_entrees_de_l_infobulle_suivent_la_meme_regle_que_l_equation():
    """« 1200 » et « 0.65 » à côté d'une équation qui écrit « 1 200 » et
    « 0,65 » : deux écritures du même nombre dans la même infobulle font
    douter des deux."""
    bloc = _fonction(_src("datacenter.js"), "bulleCalcul")
    assert 'typeof x === "number" ? fr(x)' in bloc, (
        "les entrées de l'infobulle sont rendues brutes")
