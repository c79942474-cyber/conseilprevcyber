# -*- coding: utf-8 -*-
"""LA FICHE DU CABINET — VERSÉE PAR L'ANALYSE, ET NON PAR UN GESTE DE PLUS.

CE QUI A CHANGÉ, ET POURQUOI. La fiche était servie par une route à part,
`/marche/fiche-cabinet`, appelée par un bouton « Charger la fiche du cabinet ».
Or `_ao_charge()` la verse DÉJÀ comme socle à chaque remplissage : l'écran
demandait au serveur ce que le serveur employait de toute façon, et
l'opérateur devait y penser. Un aller-retour de trop, un bouton de trop, et
une cause de plus pour que l'écran contredise le résultat.

Elle part désormais avec `/marche/analyser`, dans la même réponse. La route
dédiée est supprimée — et ces règles le MESURENT, parce qu'une route morte
qu'on oublie de retirer reste une surface ouverte.

CE QUE CES RÈGLES TIENNENT :

  · L'ORDRE. Le dossier ne recouvre jamais une saisie, ici comme côté serveur.
    Les deux divergeraient si l'un des deux s'inversait, et c'est l'écran qui
    aurait tort sans qu'on le sache.

  · LE VERROU ET SON MOTIF. Ce sont les données du CABINET : dénomination,
    SIRET, chiffres d'affaires, signataire. Le motif a déménagé avec elles,
    sur `/analyser`, et il doit toujours nommer ce qui sort.

  · CE QUI MANQUE EST NOMMÉ. Le RCS, le code NAF, l'effectif et l'assurance ne
    sont pas au dossier. Annoncer « fiche versée » sans le dire ferait croire
    la fiche complète — et c'est au dépôt des plis qu'on s'en apercevrait.
"""
import base64
import io
import os
import re

import pytest

import acces
import dossier_entreprise

ROUTE = "/api/datacenter/marche/analyser"
DISPARUE = "/api/datacenter/marche/fiche-cabinet"


def _js():
    ici = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return io.open(os.path.join(ici, "ingenierie-dc.js"), encoding="utf-8").read()


def _src(nom):
    ici = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return io.open(os.path.join(ici, nom), encoding="utf-8").read()


def _piece(texte):
    return {"nom": "reglement-de-consultation.txt",
            "contenu": base64.b64encode(texte.encode("utf-8")).decode("ascii")}


CONSULTATION = (
    "RÈGLEMENT DE LA CONSULTATION\n\n"
    "Acheteur : Commune d'Essai. Objet : travaux de mise en sécurité d'un "
    "centre de données. Procédure adaptée. Les candidats remettent les "
    "formulaires DC1 et DC2 dûment complétés, ainsi qu'une attestation "
    "d'assurance de responsabilité civile professionnelle en cours de "
    "validité. La date limite de remise des plis est fixée au 30 juin.\n")


# Le site refuse les écritures sans en-tête d'origine : la sonde en porte un,
# comme le ferait un navigateur.
ORIGINE = {"Origin": "http://localhost"}


def _analyse(client):
    return client.post(ROUTE, json={"documents": [_piece(CONSULTATION)]},
                       headers=ORIGINE)


# ═══════════════════════════════════════════════════════════════════════════
#  1. LA ROUTE DÉDIÉE A DISPARU — ET RIEN NE LA RÉCLAME PLUS
# ═══════════════════════════════════════════════════════════════════════════

def test_la_route_dediee_n_existe_plus(marche):
    """Une route morte qu'on oublie de retirer reste une surface ouverte."""
    assert marche.get(DISPARUE).status_code == 404
    assert DISPARUE not in _src("app.py"), (
        "la route est encore déclarée dans app.py")
    assert DISPARUE not in acces.API_ADMIN, (
        "la politique d'accès déclare encore une route qui n'existe pas")


def test_la_page_ne_porte_plus_le_geste():
    js = _js()
    for vestige in ("ig-ao-cab-go", "aoFicheCabinet", DISPARUE):
        assert vestige not in js, "vestige du geste supprimé : " + vestige
    sans_prose = re.sub(r"/\*[\s\S]*?\*/", " ", js)
    assert "Charger la fiche du cabinet" not in sans_prose, (
        "le libellé du bouton est encore dans le CODE")


# ═══════════════════════════════════════════════════════════════════════════
#  2. LE VERROU A SUIVI LA DONNÉE
# ═══════════════════════════════════════════════════════════════════════════

def test_l_analyse_est_fermee_a_l_administration(connecte, anonyme):
    """Les données du cabinet ne sortent que vers qui répond POUR lui."""
    for client, attendu in ((anonyme, (401, 302, 403)), (connecte, (403,))):
        assert _analyse(client).status_code in attendu


def test_la_politique_declare_ce_que_l_analyse_sort_desormais():
    """UNE ROUTE FERMÉE SANS DÉCISION ÉCRITE est une fermeture qu'on lèvera
    par distraction. Le motif doit nommer ce qui sort — et le motif générique
    de la famille ne suffit pas, puisqu'il vaut pour les quinze autres."""
    assert ROUTE in acces.API_ADMIN
    motif = acces.API_ADMIN[ROUTE]
    assert motif != acces._MOTIF_MARCHE, (
        "le motif est celui de toute la famille : il ne dit pas que CETTE "
        "route sort désormais l'identité du cabinet")
    propre = motif.replace(acces._MOTIF_MARCHE, "")
    nommes = [m for m in ("SIRET", "chiffres d'affaires", "dénomination",
                          "signataire") if m in propre]
    assert len(nommes) >= 2, (
        "le motif propre ne nomme pas ce qui en sort — relevé : %r" % nommes)


# ═══════════════════════════════════════════════════════════════════════════
#  3. L'ANALYSE REND LA FICHE, ET CE QUI LUI MANQUE
# ═══════════════════════════════════════════════════════════════════════════

def test_l_analyse_joint_la_fiche_ET_ce_qui_lui_manque(marche):
    j = _analyse(marche).get_json()
    assert j["ok"] is True
    cab = j.get("cabinet")
    assert cab, "l'analyse ne joint pas la fiche du cabinet"
    etat = dossier_entreprise.fiche_candidat()
    assert cab["fiche"] == etat["fiche"]
    assert cab["fournis"] == etat["fournis"]
    assert cab["attendus"] == etat["attendus"]
    assert cab["fournis"] < cab["attendus"], (
        "l'analyse annonce une fiche complète : le témoin est cassé, ou le "
        "dossier a été complété sans que cette règle le sache")
    assert {m["cle"] for m in cab["manques"]}, "aucun manque nommé"
    for m in cab["manques"]:
        assert m.get("ou_trouver"), (
            "« %s » manque sans dire où le chercher" % m["cle"])


def test_le_siret_et_les_trois_exercices_sortent_bien_par_l_analyse(marche):
    """LA RÈGLE DÉCISIVE DU VOLET SERVEUR. Sans elle, l'analyse pourrait
    joindre une fiche amputée et la page écrirait des champs vides — ce qui
    est exactement l'état d'avant, sans même un bouton pour s'en plaindre."""
    f = _analyse(marche).get_json()["cabinet"]["fiche"]
    for cle in ("siret", "siren", "tva", "ca_n1", "ca_n2", "ca_n3"):
        assert str(f.get(cle) or "").strip(), (
            "« %s » ne sort pas de l'analyse" % cle)


def test_un_dossier_illisible_n_emporte_pas_l_analyse():
    """L'analyse est le travail cher de cette route ; la fiche est un
    supplément. Son échec doit coûter la fiche, et rien d'autre."""
    corps = _src("app.py")
    i = corps.index("def api_datacenter_marche_analyser(")
    f = corps.index("@app.route(", i)
    bloc = corps[i:f]
    assert re.search(r"try:\s*\n\s*cab = dossier_entreprise\.fiche_candidat\(\)"
                     r"\s*\n\s*except Exception:[\s\S]{0,200}cab = None", bloc), (
        "la lecture du dossier n'est pas isolée : elle peut emporter l'analyse")


# ═══════════════════════════════════════════════════════════════════════════
#  4. LE VERSEMENT, DANS LA PAGE
# ═══════════════════════════════════════════════════════════════════════════

def _corps_js(nom):
    js = _js()
    i = js.index("function %s(" % nom)
    j = js.index("\n  }", i)
    return js[i:j]


def test_l_analyse_verse_la_fiche_des_qu_elle_arrive():
    js = _js()
    assert re.search(r"AO_ANALYSE = j\.analyse;[\s\S]{0,400}"
                     r"aoCabinetVerser\(j\.cabinet\)", js), (
        "la réponse de l'analyse ne verse pas la fiche du cabinet")


def test_le_versement_n_ECRASE_pas_ce_qui_est_deja_saisi():
    """L'ORDRE, MESURÉ SUR LE CODE QUI L'APPLIQUE. Une consultation peut
    demander une variante — un établissement secondaire, un autre signataire —
    et celui qui l'a tapée en sait plus que le dossier."""
    corps = _corps_js("aoCabinetVerser")
    assert re.search(r'if \(String\(AO_FICHE\[k\] \|\| ""\)\.trim\(\)\)'
                     r'[\s\S]{0,60}return', corps), (
        "la garde qui préserve la saisie a disparu : le dossier écraserait ce "
        "que l'opérateur vient de taper")
    assert "gardes" in corps, (
        "les saisies conservées ne sont plus comptées : l'opérateur ne saurait "
        "pas que le versement n'a pas tout écrit")


def test_le_message_dit_ce_qui_MANQUE_au_dossier():
    """« Fiche versée » sans la suite ferait croire la fiche complète."""
    corps = _corps_js("aoCabinetTexte")
    assert "manques" in corps, "l'analyse rend les manques, la page les jette"
    assert "absents" in corps
    assert "inventent pas" in corps, (
        "le message ne dit pas que ces champs ne s'inventent pas")


def test_la_fiche_deja_dessinee_est_REDESSINEE():
    """LE DÉFAUT MESURÉ EN NAVIGATEUR, ET IL SURVIT AU CHANGEMENT DE GESTE.
    Les champs portent les anciennes valeurs dans leur attribut `value` : sans
    redessin, on annoncerait « 16 valeurs versées » au-dessus de seize champs
    restés vides. Et `aoRemplir` ne redessine la fiche que si elle est VIDE —
    donc c'est ici, et nulle part ailleurs, que le redessin doit se faire."""
    corps = _corps_js("aoCabinetVerser")
    assert re.search(r"if \(AO_REMPLI\)[\s\S]{0,80}aoFicheRendre\(AO_REMPLI\)",
                     corps), "la fiche déjà dessinée n'est pas redessinée"
    assert re.search(r'if \(!\$\("#ig-ao-fiche"\)\.innerHTML\) aoFicheRendre',
                     _js()), (
        "`aoRemplir` redessine désormais sans condition : cette règle "
        "mesurerait du vide")
