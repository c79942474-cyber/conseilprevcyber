# -*- coding: utf-8 -*-
"""« 8 à rédiger ou à obtenir d'un tiers » — pourquoi les huit ne sont-elles
pas rédigées ?

LA QUESTION EST VENUE DE L'ÉCRAN, ET ELLE ÉTAIT FONDÉE. Le compte des
documents retenus ne connaissait que deux tas : ce que le module remplit, et
« à rédiger ou à obtenir d'un tiers ». Le second mélangeait trois gestes qui
n'ont rien de commun :

  · des pièces dont les rubriques se REPORTENT ici, mais dont aucun cerfa
    n'existe — le document reste à établir et à signer ;
  · des pièces dont l'atelier RÉDIGE un brouillon ;
  · des pièces qu'un greffe, un assureur ou l'URSSAF DÉLIVRE — et qu'aucun
    logiciel n'écrira jamais.

Mesuré sur le cas exact qui a fait poser la question — 12 documents retenus
sur 23 — les huit se répartissent 2 / 3 / 3. Le compte n'était pas faux : il
était muet là où il fallait qu'il parle. Un chiffre qui oblige le lecteur à
demander ce qu'il recouvre n'a pas fini son travail.

CES RÈGLES MESURENT DEUX CHOSES, ET AUCUNE N'EST UNE PRÉSENCE DE CLÉ :

  1. Que chaque catégorie dise ce que le MOTEUR fait réellement de la pièce.
     Une pièce rangée dans « l'atelier la rédige » doit sortir de
     `ao_redaction.pieces_redigeables` ; une pièce rangée dans « le module la
     remplit » doit avoir un modèle dans `ao_formulaires.MODELES`. Une table
     recopiée à la main passerait l'une et l'autre le jour où elle dérive —
     c'est exactement le défaut que ce dépôt a corrigé ailleurs : une règle
     verte pour une raison sans rapport avec ce qu'elle prétend.

  2. Que la PAGE affiche ces quatre comptes-là. Elles exécutent
     `aoSelectionRendre` et lisent le balisage produit ; chercher un nom de
     variable dans le fichier dirait qu'une ligne existe, pas qu'un nombre
     juste s'affiche.
"""
import html
import io
import json
import os
import re
import subprocess

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import ao_dc as A                                              # noqa: E402
import ao_formulaires as F                                     # noqa: E402
import ao_redaction as R                                       # noqa: E402

from test_ao_formulaires import _js_source                     # noqa: E402


CATEGORIES = ("remplissables", "au_report", "redigeables", "a_demander")


# --------------------------------------------------------------------------
# LES CAS, CONSTRUITS SUR DE VRAIES CITATIONS.
# --------------------------------------------------------------------------
def _selection(cles):
    """La sélection qu'un règlement de consultation nommant `cles` produit."""
    an = {"exigences": {c: {
        "repere": True, "libelle": c,
        "citation": {"fichier": "rc.pdf", "sigle": "RC",
                     "texte": "le candidat produit %s" % c, "part": .5},
    } for c in cles}}
    return A.selection(an)


# LE CAS QUI A FAIT POSER LA QUESTION : « 12 document(s) retenus sur 23 au
# catalogue — dont 4 que ce module remplit, et 8 à rédiger ou à obtenir d'un
# tiers. » Les clés ci-dessous le reproduisent exactement.
DOUZE = ["dc1", "dc2", "dc4", "acte_engagement", "atd_atp", "honneur",
         "memoire_technique", "dpgf", "references", "bilans", "cv",
         "attestations_assurances"]

# ET UN CAS OÙ LES QUATRE COMPTES DIFFÈRENT DEUX À DEUX (4 / 2 / 5 / 3). Sur
# le cas à douze, deux catégories valent 3 : une page qui les intervertirait
# afficherait les mêmes nombres et resterait verte.
DISTINCTS = DOUZE + ["qse", "moyens"]

# ET UN CAS SANS AUCUNE PIÈCE À DEMANDER À UN TIERS, pour éprouver qu'une
# catégorie vide se tait au lieu d'afficher un zéro.
SANS_TIERS = [c for c in DOUZE
              if c not in ("bilans", "cv", "attestations_assurances")]


def _modele(cle):
    """Le modèle de formulaire qui produit CETTE pièce, s'il en existe un."""
    for _c, m in F.MODELES.items():
        if (m.get("piece") or _c) == cle:
            return m
    return None


def _par_cle(remplissage):
    return {p["cle"]: p for p in (remplissage or {}).get("pieces") or []}


# --------------------------------------------------------------------------
# 1. LE MOTEUR : QUATRE CATÉGORIES QUI PARTITIONNENT, ET QUI DISENT VRAI.
# --------------------------------------------------------------------------
@pytest.mark.parametrize("cles", [DOUZE, DISTINCTS, SANS_TIERS, []])
def test_les_quatre_categories_partitionnent_exactement_les_retenues(cles):
    """Un document retenu tombe dans une catégorie et une seule.

    SANS CETTE PROPRIÉTÉ, LE COMPTE AFFICHÉ NE VEUT RIEN DIRE : une pièce
    comptée deux fois gonfle le total, une pièce oubliée fait disparaître un
    document du dossier à déposer — et c'est le second qui coûte cher.
    """
    s = _selection(cles)
    retenues = {x["cle"] for x in s["lignes"] if x["retenue"]}
    listes = {c: s[c] for c in CATEGORIES}

    for c, v in listes.items():
        assert len(set(v)) == len(v), "%s contient un doublon : %r" % (c, v)

    union = set()
    for c, v in listes.items():
        double = union & set(v)
        assert not double, "%s recouvre une autre catégorie : %r" % (c, double)
        union |= set(v)

    assert union == retenues, (
        "les quatre catégories ne couvrent pas les retenues : manquent %r, "
        "en trop %r" % (retenues - union, union - retenues))
    assert sum(len(v) for v in listes.values()) == s["retenues"]


def test_chaque_categorie_dit_ce_que_LE_MOTEUR_fait_vraiment_de_la_piece():
    """Le rangement est ÉPROUVÉ contre le comportement, pas contre une table.

    C'EST LA RÈGLE QUI COMPTE. `selection()` déduit les quatre listes de
    `voie()` ; si un jour quelqu'un les recopie à la main — ou déplace une
    pièce d'une nature à l'autre sans y penser — la page annoncerait un
    brouillon que l'atelier refuse d'écrire, ou un cerfa que rien ne remplit.
    Ici, chaque appartenance est confrontée à ce que font `MODELES`,
    `remplir()` et `pieces_redigeables()` — les trois seuls endroits qui
    décident réellement.
    """
    s = _selection(DISTINCTS)
    rap = A.remplir(None)
    pieces = _par_cle(rap)
    redigeables = {p["cle"] for p in R.pieces_redigeables(rap)}

    for cle in s["remplissables"]:
        assert _modele(cle), (
            "%s est annoncée « remplie sur le cerfa officiel » alors "
            "qu'aucun modèle de ao_formulaires ne la produit" % cle)

    for cle in s["au_report"]:
        assert not _modele(cle), (
            "%s a un modèle : elle se remplit SUR son cerfa, pas « sans cerfa "
            "à joindre »" % cle)
        assert cle not in redigeables, (
            "%s part à l'atelier : elle n'est pas « à établir et signer »"
            % cle)
        assert len(pieces[cle].get("rubriques") or []) > 0, (
            "%s est annoncée « rubriques reportées ici » sans aucune rubrique"
            % cle)

    for cle in s["redigeables"]:
        assert cle in redigeables, (
            "%s est annoncée rédigée par l'atelier alors que "
            "ao_redaction.pieces_redigeables ne la retient pas : le bouton "
            "promis ne produirait rien" % cle)

    for cle in s["a_demander"]:
        assert not _modele(cle), "%s a un modèle : le module la remplit" % cle
        assert cle not in redigeables, (
            "%s est annoncée « à demander à un tiers » alors que l'atelier "
            "sait la rédiger : on ferait attendre un délai pour rien" % cle)
        assert not (pieces[cle].get("rubriques") or []), (
            "%s porte des rubriques : elle se reporte ici, au moins en "
            "partie" % cle)


def test_les_quatre_categories_sont_toutes_peuplees_sur_un_dossier_complet():
    """Le témoin. Une catégorie toujours vide rendrait la règle précédente
    vide de sens pour elle : on ne saurait pas qu'elle range bien, seulement
    qu'elle ne range rien."""
    s = _selection(DISTINCTS)
    vides = [c for c in CATEGORIES if not s[c]]
    assert not vides, vides
    tailles = [len(s[c]) for c in CATEGORIES]
    assert len(set(tailles)) == 4, (
        "deux catégories du cas témoin ont le même compte (%r) : une page qui "
        "les intervertirait afficherait les mêmes nombres" % (tailles,))


def test_le_cas_qui_a_fait_poser_la_question_y_repond_maintenant():
    """12 sur 23, dont 4 remplis — et les huit autres, enfin nommées."""
    s = _selection(DOUZE)
    assert (s["retenues"], s["catalogue"]) == (12, 23)
    assert len(s["remplissables"]) == 4
    assert len(s["a_produire"]) == 8, (
        "le cas de l'écran n'est plus reproduit : la règle ne répond plus à "
        "la question posée")
    assert [len(s[c]) for c in ("au_report", "redigeables", "a_demander")] \
        == [2, 3, 3], (
        "les huit ne se répartissent plus 2 / 3 / 3 : %r"
        % {c: s[c] for c in ("au_report", "redigeables", "a_demander")})
    # ET LES TROIS SOUS-LISTES REDÉCOUPENT « À PRODUIRE », elles ne s'y
    # ajoutent pas : le total resterait juste tout en comptant deux fois.
    assert set(s["au_report"]) | set(s["redigeables"]) | set(s["a_demander"]) \
        == set(s["a_produire"])


# --------------------------------------------------------------------------
# 2. LA PAGE, EXÉCUTÉE.
# --------------------------------------------------------------------------
def _rendu(sel):
    """Le balisage que `aoSelectionRendre` produit RÉELLEMENT sur `sel`."""
    prog = (_js_source("esc", "aoSelectionRendre")
            + "\nvar AO_SELECTION = null;"
            + "\nfunction aoSelectionBrancher() {}"
            + "\nvar zone = { innerHTML: '' };"
            + "\nfunction $(s){ return s === '#ig-ao-retenus' ? zone : null; }"
            + "\naoSelectionRendre(JSON.parse(process.env.SEL));"
            + "\nprocess.stdout.write(zone.innerHTML);\n")
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60, env=dict(os.environ, SEL=json.dumps(sel)))
    assert out.returncode == 0, out.stderr[-2000:]
    return html.unescape(out.stdout)


def _comptes(h):
    """Les (nombre, phrase) de la liste des espèces, dans l'ordre affiché."""
    m = re.search(r'<ul class="[^"]*\big-ao-quatre\b[^"]*">(.*?)</ul>', h, re.S)
    if not m:
        return []
    return [(int(n), re.sub(r"\s+", " ", t).strip())
            for n, t in re.findall(r"<li><b>(\d+)</b>(.*?)</li>", m.group(1),
                                   re.S)]


def test_la_page_affiche_les_quatre_comptes_du_moteur_et_leur_somme():
    """Elle ne recalcule rien : les quatre nombres affichés SONT ceux de la
    sélection, et ils s'additionnent au total annoncé juste au-dessus."""
    s = _selection(DISTINCTS)
    h = _rendu(s)
    lus = _comptes(h)
    assert len(lus) == 4, (
        "la page n'affiche pas quatre espèces de documents : %r" % (lus,))
    assert [n for n, _t in lus] == [len(s[c]) for c in CATEGORIES], (
        "les nombres affichés ne sont pas ceux du moteur : %r contre %r"
        % ([n for n, _t in lus], [len(s[c]) for c in CATEGORIES]))
    assert sum(n for n, _t in lus) == s["retenues"]
    assert "<b>%d document(s)</b> retenus sur %d au catalogue" \
        % (s["retenues"], s["catalogue"]) in h


def test_la_page_distingue_le_brouillon_de_l_atelier_du_delai_d_un_tiers():
    """LA DISTINCTION QUI MANQUAIT. « À rédiger ou à obtenir d'un tiers »
    réunissait le geste que ce module fait et celui qu'il ne fera jamais. Les
    deux phrases doivent porter des nombres différents, et le bon chacune —
    les intervertir ferait attendre un délai de greffe pour un mémoire
    technique."""
    s = _selection(DISTINCTS)
    lus = dict((t, n) for n, t in _comptes(_rendu(s)))
    atelier = [t for t in lus if "atelier" in t]
    tiers = [t for t in lus if "tiers" in t]
    assert len(atelier) == 1, ("aucune phrase ne nomme l'atelier", list(lus))
    assert len(tiers) == 1, ("aucune phrase ne nomme le tiers", list(lus))
    assert lus[atelier[0]] == len(s["redigeables"]), (
        "la ligne de l'atelier ne porte pas le compte des rédigeables")
    assert lus[tiers[0]] == len(s["a_demander"]), (
        "la ligne du tiers ne porte pas le compte des pièces à demander")
    # ET LE TAS UNIQUE A DISPARU : aucune ligne ne porte les huit ensemble.
    assert len(s["a_produire"]) not in lus.values(), (
        "une ligne affiche encore le total « à produire » d'un bloc : %r"
        % (lus,))


def test_une_categorie_vide_se_tait_au_lieu_d_afficher_un_zero():
    """« 0 à demander à un tiers » ferait chercher une pièce qui n'existe pas
    — et les trois autres espèces resteraient noyées dans une ligne morte."""
    s = _selection(SANS_TIERS)
    assert not s["a_demander"], "le cas témoin n'a plus de catégorie vide"
    lus = _comptes(_rendu(s))
    assert [n for n, _t in lus] == [len(s[c]) for c in CATEGORIES
                                    if s[c]], (
        "la page ne montre pas exactement les catégories peuplées : %r"
        % (lus,))
    assert all(n > 0 for n, _t in lus), lus
    assert not any("tiers" in t for _n, t in lus), (
        "la page parle encore d'un tiers alors qu'aucune pièce n'en dépend")


def test_les_quatre_phrases_sont_distinctes():
    """Deux lignes de même libellé porteraient deux nombres sans dire lequel
    va où : le lecteur lirait deux fois la même chose et en déduirait un
    doublon."""
    lus = _comptes(_rendu(_selection(DISTINCTS)))
    phrases = [t for _n, t in lus]
    assert len(set(phrases)) == len(phrases), phrases
    for t in phrases:
        assert len(t) > 20, ("une phrase ne dit pas le geste attendu", t)


def test_la_liste_des_especes_est_reellement_habillee_par_la_feuille():
    """La classe que la PAGE pose est celle que la FEUILLE définit.

    Sans elle, les quatre gestes sortent en puces système collées au
    paragraphe et se lisent comme la suite de la phrase précédente — le
    lecteur retrouve exactement le bloc indistinct qu'on vient de défaire.

    LA CLASSE EST LUE SUR LE RENDU, PAS ÉCRITE ICI : la chercher des deux
    côtés sous un nom recopié laisserait passer une page qui en pose une
    autre. Et le sélecteur est ancré en début de ligne — `.ig-ao-quatre > li`
    suffirait à contenter un simple « la chaîne est présente » alors que la
    liste elle-même n'aurait aucune mise en forme.
    """
    h = _rendu(_selection(DISTINCTS))
    m = re.search(r'<ul class="([^"]+)">\s*<li><b>', h)
    assert m, "la liste des espèces ne porte aucune classe"
    css = io.open(os.path.join(ICI, "styles.css"), encoding="utf-8").read()
    propres = [c for c in m.group(1).split() if c != "note"]
    assert propres, "la liste n'a que la classe générique « note »"
    for c in propres:
        assert re.search(r"(?m)^\.%s\s*\{" % re.escape(c), css), (
            "la page pose la classe %r sur la liste des espèces, et la "
            "feuille ne la définit pas" % c)
