# -*- coding: utf-8 -*-
"""Ce que le règlement NOMME, repéré dans le dossier déposé — jamais décidé.

CE QUE CECI AJOUTE, ET SA LIMITE ASSUMÉE. Les cartes de candidature et d'offre
listaient le catalogue sans dire lesquelles CE règlement demande. `exigees()`
repère, dans le texte déposé, les pièces que le RG nomme — avec la citation qui
l'a déclenché. « Repérée », pas « exigée » : la liste qui fait foi est celle du
règlement de la consultation, et une pièce non repérée y renvoie.

CES RÈGLES MESURENT DES DEUX CÔTÉS, sur un règlement écrit comme les vrais.
Le rappel (les pièces nommées ressortent repérées) NE SUFFIT PAS : une règle
qui n'exigerait que cela passerait avec un détecteur qui dit « oui » à tout.
On mesure donc AUSSI la précision — une pièce que le RG ne nomme pas ne doit
pas ressortir repérée — et l'ancrage : chaque citation vient VRAIMENT du texte.
"""
import io
import os
import re

import pytest

import ao_dc

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = io.open(os.path.join(ICI, "ingenierie-dc.js"), encoding="utf-8").read()

# UN RÈGLEMENT ÉCRIT COMME LES VRAIS : une section « composition du dossier »
# qui NOMME cinq pièces, et n'en nomme pas d'autres. Les deux ensembles servent :
# les nommées doivent être repérées, les autres NON.
RC = u"""RÈGLEMENT DE LA CONSULTATION
Article 5 - Composition du dossier de candidature.
Le candidat produit à l'appui de sa candidature :
- une lettre de candidature (formulaire DC1) ;
- une déclaration du candidat (formulaire DC2) ;
- les attestations d'assurance responsabilité civile professionnelle ;
- la liste des principales références de moins de trois ans ;
- une attestation de régularité fiscale et sociale.
"""
NOMMEES = ("dc1", "dc2", "attestations_assurances", "references",
           "regularite_fiscale_sociale")
# Non nommées par CE règlement : la sous-traitance, l'organigramme, le mémoire
# technique. Un détecteur qui les « repérerait » quand même sur-affirmerait.
NON_NOMMEES = ("dc4", "organigramme", "memoire_technique", "moyens", "qse")


def _analyse():
    return ao_dc.analyser([{"nom": "01_RC.pdf", "texte": RC}])


def test_les_pieces_NOMMEES_sont_reperees_avec_leur_citation():
    """LE RAPPEL. Chaque pièce que le règlement nomme ressort repérée, et sa
    citation est le passage qui l'a déclenchée — vérifiable sur la pièce."""
    ex = _analyse()["exigences"]
    for cle in NOMMEES:
        assert ex[cle]["repere"], "« %s » nommée au RC mais non repérée" % cle
        cit = ex[cle]["citation"]
        assert cit and cit["texte"], "« %s » repérée sans citation" % cle
        assert cit["texte"] in RC, (
            "la citation de « %s » ne vient pas du texte déposé : %r"
            % (cle, cit["texte"]))
        assert cit["fichier"] == "01_RC.pdf", cit


def test_une_piece_NON_nommee_n_est_PAS_reperee():
    """LA PRÉCISION, ET C'EST ELLE QUI MANQUAIT À UN SIMPLE « NON VIDE ». Ce
    que le règlement ne nomme pas ne doit pas ressortir repéré : une pastille
    verte à tort ferait produire une pièce inutile et croire un dû qui n'existe
    pas. Sans ce témoin, un détecteur qui dit toujours « oui » passerait."""
    ex = _analyse()["exigences"]
    for cle in NON_NOMMEES:
        assert not ex[cle]["repere"], (
            "« %s » repérée alors que le règlement ne la nomme pas — "
            "sur-affirmation" % cle)
        assert ex[cle]["citation"] is None, cle


def test_CHAQUE_piece_du_catalogue_a_son_entree():
    """Une pièce muette se lit « non repérée », elle ne DISPARAÎT pas : sinon
    la carte ne saurait pas l'afficher, et l'absence passerait pour un oubli."""
    ex = _analyse()["exigences"]
    cles = ({p["cle"] for p in ao_dc.DOSSIER_CANDIDATURE}
            | {p["cle"] for p in ao_dc.DOSSIER_OFFRE})
    manquantes = cles - set(ex)
    assert not manquantes, "pièces sans entrée d'exigence : %s" % manquantes
    for cle in cles:
        assert "repere" in ex[cle], cle


def test_SANS_dossier_rien_n_est_repere():
    """LE TÉMOIN NÉGATIF. Hors dossier analysé, on ne peut rien dire de ce que
    le RC exige : `exigences_actives` est faux et aucune pièce n'est repérée.
    Une pastille affichée sans dossier serait une affirmation sans source."""
    p = ao_dc.plan_reponse(None)
    o = ao_dc.offre()
    assert p["exigences_actives"] is False
    assert o["exigences_actives"] is False
    assert not any(x.get("repere") for x in p["pieces"])
    assert not any(x.get("repere") for x in o["pieces"])


def test_le_plan_et_l_offre_PORTENT_le_repere_de_l_analyse():
    """LE BRANCHEMENT. Sans lui, le calcul serait juste et l'écran muet. Le
    plan de candidature ET le dossier d'offre reçoivent, pièce par pièce, le
    repérage et sa citation."""
    an = _analyse()
    p = {x["cle"]: x for x in ao_dc.plan_reponse(an)["pieces"]}
    assert p["dc1"]["repere"] and p["dc1"]["citation_exigence"]
    # organigramme est une pièce de candidature NON nommée par ce RC.
    assert p["organigramme"]["repere"] is False
    # dc4 vit au dossier d'OFFRE, pas au plan de candidature — et n'est pas
    # nommé par ce RC.
    o = {x["cle"]: x for x in ao_dc.offre(analyse=an)["pieces"]}
    assert "repere" in o["acte_engagement"]
    assert o["dc4"]["repere"] is False


def test_les_marqueurs_visent_des_pieces_REELLES():
    """Un marqueur qui viserait une pièce inexistante ne repérerait jamais rien
    et personne ne le verrait — le contrôle d'import l'interdit, cette règle le
    redit sur la table elle-même."""
    cles = ({p["cle"] for p in ao_dc.DOSSIER_CANDIDATURE}
            | {p["cle"] for p in ao_dc.DOSSIER_OFFRE})
    for cle in ao_dc.EXIGENCES:
        assert cle in cles, "EXIGENCES vise une pièce inconnue : %s" % cle


# ── LA VOIE HTTP : le repère voyage jusqu'à la page ────────────────────────
ORIGINE = {"Origin": "http://localhost"}


def test_la_route_candidature_REND_le_repere(marche):
    """À travers la vraie route, décorateurs compris : POSTer l'analyse rend un
    plan et un dossier d'offre dont les pièces portent le repérage."""
    an = _analyse()
    rep = marche.post("/api/datacenter/marche/candidature",
                      json={"analyse": an, "groupement": False}, headers=ORIGINE)
    assert rep.status_code == 200, (rep.status_code, rep.data[:300])
    j = rep.get_json()
    plan = {x["cle"]: x for x in j["plan"]["pieces"]}
    assert j["plan"]["exigences_actives"] is True
    assert plan["dc1"]["repere"] is True
    offre = {x["cle"]: x for x in j["dossier_offre"]["pieces"]}
    assert "repere" in offre["acte_engagement"]


# ── LA PAGE : la pastille, honnête et conditionnelle ───────────────────────

def _fn(nom):
    i = JS.index("function " + nom + "(")
    j = JS.find("\n  function ", i + 1)
    return JS[i:(j if j > 0 else len(JS))]


def test_la_pastille_distingue_repere_et_non_repere_ET_seulement_avec_dossier():
    """La pastille verte et la pastille mate sont deux rendus distincts, et
    aucune ne s'affiche hors dossier (`if (!actives) return ""`). Sans cette
    garde, une pastille paraîtrait sur un écran qui n'a rien analysé."""
    corps = _fn("aoExigence")
    assert 'if (!actives) return ""' in corps, (
        "la pastille s'afficherait même sans dossier analysé")
    assert "piece.repere" in corps
    assert "ig-ao-ex-oui" in corps and "ig-ao-ex-non" in corps


def test_la_pastille_non_reperee_N_AFFIRME_PAS_l_absence():
    """L'INTÉGRITÉ À L'ÉCRAN. « Non repérée » ne doit jamais se lire « non
    exigée » : le règlement de la consultation fait foi, et la pastille le
    dit."""
    corps = _fn("aoExigence")
    assert "fait foi" in corps, (
        "la pastille « non repérée » n'explique pas que le RC tranche")
    assert "non exig" not in corps.lower(), (
        "la pastille affirme « non exigée » : ce n'est pas ce que le repérage "
        "mesure")


def test_LES_DEUX_cartes_appellent_la_pastille():
    """Candidature ET offre : si une seule branchait la pastille, l'autre
    dossier resterait muet sur ce que le RC demande."""
    assert "aoExigence(p.exigences_actives, x)" in _fn("aoCandRendre"), (
        "les cartes de candidature n'affichent pas le repérage")
    assert "aoExigence(o.exigences_actives, p)" in _fn("offreRendre"), (
        "les cartes d'offre n'affichent pas le repérage")
