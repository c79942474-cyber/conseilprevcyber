# -*- coding: utf-8 -*-
"""LES DIX CHAMPS DE L'ÉTUDE PORTAIENT CHACUN AU MOINS UN DÉFAUT.

RELEVÉ DU 29 AOÛT 2026, en interrogeant réellement le service — pas en lisant
le code. Sur les dix champs numériques du formulaire d'étude :

  · TROIS faisaient LEVER le calcul sur « nan » ou « inf » (500) ;
  · SEPT faisaient rendre un corps contenant `NaN` ou `Infinity` — qui n'est
    PAS du JSON valide : la page ne pouvait même pas lire l'erreur, elle voyait
    son `JSON.parse` échouer et n'affichait rien ;
  · NEUF acceptaient une valeur NÉGATIVE sans un mot.

LE TROISIÈME EST LE PIRE, et de loin. Les deux premiers font du bruit : une
page blanche se remarque. Le troisième est silencieux — un taux de charge de
−99, une part renouvelable de −99, un PUE cible de −99 entraient dans le calcul
et rendaient une étude complète, d'apparence normale, que le lecteur emportait
en croyant avoir chiffré son projet. Le module le disait déjà de lui-même à
propos d'un autre défaut : « le résultat était IDENTIQUE à celui d'une saisie
valide ».

`nan` ET `inf` SONT DES NOMBRES POUR PYTHON. `float("nan")` réussit, `float("inf")`
aussi, et `float("1e400")` rend l'infini sans lever. Un contrôle qui se contente
d'un `try: float(...)` les laisse donc tous passer.

CE QUE CES RÈGLES GARDENT. Le compte à ZÉRO, champ par champ, pour tout champ
présent ET pour celui qu'on ajoutera : elles énumèrent le référentiel au lieu de
nommer une liste, parce que c'est l'ajout qu'on oublie de borner.

ET LA DISTINCTION QUI COMPTE : le DOMAINE n'est pas la PLAGE OBSERVÉE. Un centre
de 15 kW sort du cadrage du cabinet et se calcule très bien — la note
l'accompagne. Refuser ce calcul-là serait un défaut symétrique, et une règle le
garde aussi.
"""
import json
import math
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import datacenter  # noqa: E402

H = {"Origin": "http://localhost", "Content-Type": "application/json"}
CHAMPS_NOMBRE = [c for c in datacenter.CHAMPS if c["type"] == "nombre"]
IDS = [c["id"] for c in CHAMPS_NOMBRE]


def _etude(client, **champs):
    corps = dict({"puissance_it_kw": 1000}, **champs)
    return client.post("/api/datacenter/etude", headers=H, data=json.dumps(corps))


def test_le_referentiel_compte_bien_des_champs_numeriques():
    """Une règle qui n'énumère rien passe toujours. Si le relevé rendait une
    liste vide, tout ce fichier serait vert sur un formulaire sans aucun
    contrôle."""
    assert len(IDS) >= 8, (
        "seulement %d champs numériques relevés : la lecture du référentiel "
        "est cassée et les contrôles ne gardent plus rien" % len(IDS))


# ── 1. AUCUNE VALEUR NON FINIE N'ENTRE DANS UN CALCUL ────────────────────

@pytest.mark.parametrize("champ", IDS)
@pytest.mark.parametrize("valeur", ["nan", "inf", "-inf", "1e400", "NaN", "Infinity"])
def test_aucune_valeur_non_finie_n_est_lue(champ, valeur):
    """`float()` accepte « nan » et « inf » : ce sont des nombres pour Python.
    Un contrôle qui se contente d'un `try: float(...)` les laisse tous passer,
    et ils traversent alors le calcul entier."""
    ch = next(c for c in CHAMPS_NOMBRE if c["id"] == champ)
    import app
    v, motif = app._lire_nombre(valeur, ch)
    assert v is None and motif, (
        "« %s » est accepté pour %s : la valeur entre dans le calcul" % (valeur, champ))


@pytest.mark.parametrize("champ", IDS)
def test_aucun_champ_ne_fait_lever_le_calcul(client_dc, champ):
    """LA RÈGLE QUI EXÉCUTE. Les précédentes inspectent le lecteur ; celle-ci
    envoie réellement l'étude et regarde ce que le service rend."""
    for valeur in ("nan", "inf"):
        r = _etude(client_dc, **{champ: valeur})
        assert r.status_code < 500, (
            "%s = %s fait lever le calcul (%d)" % (champ, valeur, r.status_code))


@pytest.mark.parametrize("champ", IDS)
def test_aucune_reponse_ne_contient_de_json_invalide(client_dc, champ):
    """`NaN` et `Infinity` ne sont pas du JSON (RFC 8259). Le navigateur ne
    voit pas une erreur : il voit son `JSON.parse` lever, et la page reste
    vide sans que rien n'explique pourquoi."""
    for valeur in ("nan", "inf", "1e400"):
        r = _etude(client_dc, **{champ: valeur})
        brut = r.get_data(as_text=True)
        assert "NaN" not in brut and "Infinity" not in brut, (
            "%s = %s produit un corps que JSON.parse refusera" % (champ, valeur))
        # Et on le vérifie pour de bon, avec un analyseur strict — la recherche
        # de chaîne ci-dessus raterait une forme écrite autrement.
        json.loads(brut, parse_constant=_refuser_constante)


def _refuser_constante(nom):
    raise AssertionError("le corps contient la constante non standard « %s »" % nom)


# ── 2. LE REFUS HORS DOMAINE EST EXPLICITE, JAMAIS SILENCIEUX ────────────

@pytest.mark.parametrize("champ", IDS)
def test_une_valeur_negative_est_refusee_et_dite(client_dc, champ):
    """LE DÉFAUT LE PLUS COÛTEUX DES TROIS, parce qu'il ne faisait aucun bruit :
    l'étude revenait complète et d'apparence normale, calculée sur une grandeur
    qui n'existe pas."""
    r = _etude(client_dc, **{champ: -99})
    j = r.get_json() or {}
    if r.status_code == 400:
        return  # refus franc de la route : le champ est essentiel
    rejets = j.get("rejets") or []
    assert any(x["champ"] == champ for x in rejets), (
        "%s = −99 est entré dans le calcul sans un mot : l'étude rendue est "
        "d'apparence normale" % champ)


@pytest.mark.parametrize("champ,valeur", [
    ("taux_charge", 1.5),
    ("part_evaporative", 2),
    ("part_renouvelable", 1.01),
    ("part_chaleur_reutilisee", 3),
    ("pue_cible", 0.5),
    ("cycles_concentration", 0.5),
])
def test_les_grandeurs_bornees_par_leur_definition_le_sont(client_dc, champ, valeur):
    """Une part dépasse rarement 1 par accident : c'est presque toujours un
    pourcentage tapé dans un champ qui attend un rapport. Un PUE sous 1 dirait
    que le centre PRODUIT de l'énergie."""
    r = _etude(client_dc, **{champ: valeur})
    j = r.get_json() or {}
    if r.status_code == 400:
        return
    assert any(x["champ"] == champ for x in (j.get("rejets") or [])), (
        "%s = %s a été accepté alors que sa définition l'interdit" % (champ, valeur))


@pytest.mark.parametrize("champ", [c["id"] for c in CHAMPS_NOMBRE
                                   if (c.get("domaine") or {}).get("strict_min")])
def test_une_borne_stricte_refuse_bien_la_borne_elle_meme(champ):
    """LA MUTATION QUI A SURVÉCU, et ce qu'elle laissait passer. Remplacer le
    « <= » par un « < » rendait la borne LARGE : un taux de charge de ZÉRO
    devenait acceptable, et l'étude rendait un PUE de 1,35 et un WUE de 0,2654
    — un dossier complet, d'apparence normale, sur un centre qui ne consomme
    rien. Le PUE d'une charge nulle est un rapport 0/0 : il n'a pas de valeur,
    et surtout pas celle-là.

    La règle porte sur la BORNE elle-même, pas sur une valeur choisie : c'est
    le seul point où le large et le strict se distinguent."""
    ch = next(c for c in CHAMPS_NOMBRE if c["id"] == champ)
    import app
    borne = ch["domaine"]["min"]
    v, motif = app._lire_nombre(borne, ch)
    assert v is None and motif, (
        "%s accepte la valeur %s alors que sa borne est stricte : la grandeur "
        "n'a pas de sens à cette valeur, et l'étude la calcule quand même"
        % (champ, borne))
    # Et juste au-dessus, elle passe : une borne stricte ne doit pas devenir
    # un refus d'un intervalle entier.
    v2, _ = app._lire_nombre(borne + 1e-6, ch)
    assert v2 is not None, (
        "%s refuse aussi une valeur au-dessus de sa borne : la borne stricte "
        "est devenue une exclusion trop large" % champ)


@pytest.mark.parametrize("champ", IDS)
def test_chaque_refus_dit_pourquoi(champ):
    """« Champ ignoré » n'aide personne à corriger. Le motif doit nommer la
    raison — c'est ce qui distingue un message d'un constat."""
    ch = next(c for c in CHAMPS_NOMBRE if c["id"] == champ)
    import app
    _, motif = app._lire_nombre(-99, ch)
    if motif is None:
        pytest.skip("ce champ admet les valeurs négatives")
    assert len(motif) > 40 and "n'a pas été pris en compte" in motif, motif


# ── 3. LE DOMAINE N'EST PAS LA PLAGE OBSERVÉE ────────────────────────────

def test_une_valeur_hors_plage_observee_reste_calculable(client_dc):
    """LE DÉFAUT SYMÉTRIQUE, et il serait aussi grave. Un centre de 15 kW sort
    du cadrage du cabinet — la plage observée commence à 20 — et c'est une
    installation parfaitement réelle. La note l'accompagne ; refuser le calcul
    priverait son auteur d'un résultat juste."""
    r = _etude(client_dc, puissance_it_kw=15)
    assert r.status_code == 200, (
        "une puissance hors de la plage OBSERVÉE est refusée : le cadrage du "
        "cabinet a été confondu avec le domaine physique")
    assert not (r.get_json() or {}).get("rejets")


def test_les_deux_notions_restent_distinctes_dans_le_referentiel():
    """Si `domaine` recopiait `plage_observee`, la distinction disparaîtrait
    en silence et le cadrage deviendrait une interdiction."""
    for c in CHAMPS_NOMBRE:
        d, p = c.get("domaine"), c.get("plage_observee")
        if not (d and p):
            continue
        assert (d.get("min"), d.get("max")) != (p.get("bas"), p.get("haut")), (
            "%s : le domaine physique est identique au cadrage observé — l'un "
            "des deux ne dit plus ce qu'il prétend" % c["id"])


def test_chaque_domaine_dit_pourquoi_il_borne():
    """Une borne sans raison est un chiffre qu'on n'ose plus toucher. Celle qui
    porte sa justification se discute — et se corrige."""
    for c in CHAMPS_NOMBRE:
        d = c.get("domaine")
        assert d, "le champ %s n'a pas de domaine déclaré" % c["id"]
        assert len(d.get("pourquoi") or "") > 25, (
            "%s : le domaine ne dit pas pourquoi il borne" % c["id"])


def test_le_domaine_voyage_avec_le_champ():
    """Le formulaire pose ses `min`/`max` depuis la même source que le serveur.
    Une seconde table côté page divergerait, et c'est la page qui laisserait
    passer."""
    r = [c for c in CHAMPS_NOMBRE if "domaine" in c]
    assert len(r) == len(CHAMPS_NOMBRE), (
        "%d champs sur %d portent leur domaine : la page ne pourra pas borner "
        "les autres" % (len(r), len(CHAMPS_NOMBRE)))
