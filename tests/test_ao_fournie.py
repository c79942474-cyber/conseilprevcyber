# -*- coding: utf-8 -*-
"""Le geste « je l'ai fournie hors outil » — et son intégrité.

CE QU'IL EST, ET CE QU'IL N'EST PAS. Une pièce bloquante que ce module ne peut
pas produire — les pouvoirs à obtenir, les références à écrire — restait un
blocage sans issue : aucun moyen de dire « je l'ai obtenue ». Ce geste le
permet. Mais il n'AFFIRME rien à la place de l'utilisateur : c'est LUI qui
déclare tenir la pièce, l'outil ne l'a pas vue, et l'écran le dit. C'est la même
règle que les déclarations sur l'honneur — jamais posée par le programme.

CES RÈGLES MESURENT L'EFFET, PAS LA PRÉSENCE D'UN DRAPEAU. Elles comparent l'état
AVEC et SANS le geste, sur un vrai remplissage, et vérifient qu'on ne peut pas
s'en servir pour contourner le remplissage honnête d'une pièce que l'outil sait,
lui, remplir.
"""
import io
import os
import re

import pytest

import ao_dc

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = io.open(os.path.join(ICI, "ingenierie-dc.js"), encoding="utf-8").read()

# Une bloquante NON remplissable, choisie sur le module lui-même : elle doit
# exister et être « à obtenir » ou « à rédiger », sinon la règle ne mesure rien.
def _une_bloquante_non_remplissable():
    r = ao_dc.remplir()
    for p in r["pieces"]:
        if p["bloquant"] and not p["mesurable"]:
            return p["cle"], p["nom"]
    raise AssertionError("aucune bloquante non remplissable : le module a changé")


def test_par_defaut_AUCUNE_piece_n_est_fournie():
    """LE TÉMOIN NÉGATIF. Sans le geste, rien n'est fourni — le programme ne
    l'invente jamais. Une mutation qui poserait « fournie » d'office tomberait
    ici."""
    r = ao_dc.remplir()
    assert not any(p.get("fournie") for p in r["pieces"]), (
        "une pièce ressort fournie sans qu'on l'ait affirmée")
    assert r["etat"]["bloquantes_fournies"] == []


def test_affirmer_fournie_RETIRE_la_bloquante_des_A_PRODUIRE_et_la_NOMME_ailleurs():
    """L'EFFET MESURÉ, DES DEUX CÔTÉS. Affirmer qu'une bloquante non
    remplissable est fournie doit la sortir de « à produire » ET la faire
    apparaître dans « fournies » — pas seulement l'une des deux."""
    cle, nom = _une_bloquante_non_remplissable()
    sans = ao_dc.remplir()["etat"]
    avec = ao_dc.remplir(fournies=[cle])["etat"]

    noms_sans = {x["nom"] for x in sans["bloquantes_a_produire"]}
    noms_avec = {x["nom"] for x in avec["bloquantes_a_produire"]}
    assert noms_sans - noms_avec == {nom}, (
        "le geste n'a pas retiré EXACTEMENT cette bloquante de « à produire » : "
        "%r" % (noms_sans - noms_avec))
    assert nom in avec["bloquantes_fournies"], (
        "la bloquante affirmée fournie n'est pas nommée dans « fournies » : "
        "elle disparaîtrait sans laisser de trace")
    assert nom not in sans["bloquantes_fournies"]


def test_une_piece_MESURABLE_affirmee_fournie_ne_change_RIEN():
    """LE CONTOURNEMENT INTERDIT. Une pièce que l'outil sait remplir (DC1) se
    remplit dans l'outil ; se dire « je l'ai fournie » pour la faire passer
    verte sauterait le remplissage honnête. Le module l'ignore."""
    r = ao_dc.remplir()
    mesurable = next(p["cle"] for p in r["pieces"] if p["mesurable"])
    avant = ao_dc.remplir()["etat"]
    apres = ao_dc.remplir(fournies=[mesurable])["etat"]
    assert not any(p["cle"] == mesurable and p["fournie"]
                   for p in ao_dc.remplir(fournies=[mesurable])["pieces"]), (
        "une pièce mesurable a été marquée fournie : contournement du "
        "remplissage")
    assert apres["bloquantes_fournies"] == avant["bloquantes_fournies"]
    assert apres["bloquantes_a_produire"] == avant["bloquantes_a_produire"]


def test_une_cle_inconnue_est_SANS_effet():
    """Une clé qui ne désigne aucune pièce ne doit produire aucune fournie —
    sinon le décompte se laisserait gonfler par n'importe quoi."""
    r = ao_dc.remplir(fournies=["cette_piece_n_existe_pas"])
    assert r["etat"]["bloquantes_fournies"] == []
    assert not any(p.get("fournie") for p in r["pieces"])


# ── LA ROUTE : le geste voyage jusqu'au calcul, avec la session autorisée ──
ORIGINE = {"Origin": "http://localhost"}


def test_la_route_de_remplissage_TIENT_COMPTE_du_geste(marche):
    """CE QUE MESURE LA VOIE HTTP, ET QU'AUCUN APPEL DIRECT NE MESURE : que la
    route lit bien « fournies » et le passe au calcul. On éprouve l'écart à
    travers la vraie route, décorateurs et bornes compris."""
    cle, nom = _une_bloquante_non_remplissable()

    def produire(fournies):
        rep = marche.post("/api/datacenter/marche/remplir",
                          json={"fournies": fournies}, headers=ORIGINE)
        assert rep.status_code == 200, (rep.status_code, rep.data[:300])
        return rep.get_json()["remplissage"]["etat"]

    e0, e1 = produire([]), produire([cle])
    a0 = {x["nom"] for x in e0["bloquantes_a_produire"]}
    a1 = {x["nom"] for x in e1["bloquantes_a_produire"]}
    assert a0 - a1 == {nom}, (a0 - a1)
    assert nom in e1["bloquantes_fournies"] and nom not in e0["bloquantes_fournies"]


# ── LA PAGE : le geste est offert, honnête, et sans persistance trompeuse ──

def test_le_geste_est_offert_SUR_les_bloquantes_non_remplissables():
    """Le bouton n'apparaît que là où il a un sens : dans le bloc des pièces
    NON mesurables (`if (!p.mesurable)`), et sous condition `p.bloquant`."""
    assert 'data-fournie="' in JS, "le geste « fournie » n'est pas rendu"
    # Le bouton vit dans la branche non-mesurable, gardée par bloquant.
    bloc = JS[JS.index("if (!p.mesurable)"):]
    bloc = bloc[:bloc.index("h += '<dl class=\"ig-ao-rb\">")]
    assert "data-fournie=" in bloc, (
        "le geste n'est pas dans le bloc des pièces non remplissables")
    assert "if (p.bloquant)" in bloc, (
        "le geste n'est pas réservé aux bloquantes")


def test_le_geste_DIT_qu_il_n_est_pas_verifie():
    """L'INTÉGRITÉ, À L'ÉCRAN, ET SUR LA BONNE PASTILLE. La carte ne doit jamais
    laisser croire que l'outil a constaté la pièce.

    Chercher « non vérifié » n'importe où dans le fichier ne suffit pas : la
    ligne de synthèse dit « non vérifiée » (féminin), qui contient le masculin
    comme sous-chaîne — retirer la mention de la pastille de la CARTE laissait
    la règle verte. On borne donc la recherche à la pastille `ig-ao-fo-m`,
    celle qui s'affiche SUR la pièce affirmée fournie."""
    i = JS.index("ig-ao-fo-m")
    pastille = JS[i:i + 220]
    assert "affirmé par vous" in pastille, pastille
    assert "non vérifié" in pastille, (
        "la pastille de la carte affirmée fournie ne dit plus « non vérifié » : "
        "elle laisserait croire que l'outil a constaté la pièce")


def test_le_geste_POSTE_les_fournies_a_la_route():
    """Le remplissage envoie la liste des fournies, sinon le serveur ne peut
    pas en tenir compte."""
    corps = JS[JS.index('"/api/datacenter/marche/remplir"'):]
    corps = corps[:corps.index("}).then")]
    assert "fournies: Object.keys(AO_FOURNIES)" in corps, (
        "le corps de /remplir n'envoie pas les fournies")


def test_les_fournies_ne_SURVIVENT_PAS_a_un_rechargement():
    """LA SÛRETÉ CONTRE UNE FAUSSE AFFIRMATION. Persisté, un « fourni » posé
    pour une consultation reparaîtrait sur la suivante — affirmant une pièce
    qu'on n'a pas. `AO_FOURNIES` reste en mémoire : jamais lu dans le stockage
    local, à la différence de `AO_SAISIES`."""
    assert re.search(r"var AO_FOURNIES = \{\}", JS), "AO_FOURNIES non déclaré"
    # Aucune lecture de AO_FOURNIES depuis localStorage.
    assert not re.search(r"AO_FOURNIES\s*=\s*JSON\.parse", JS), (
        "AO_FOURNIES est rechargé du stockage local : une affirmation "
        "fournie pourrait fuir d'une consultation à l'autre")
    assert "ao-fournies" not in JS, (
        "une clé de stockage local pour les fournies est apparue")
