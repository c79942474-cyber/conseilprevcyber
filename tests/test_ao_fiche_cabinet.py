# -*- coding: utf-8 -*-
"""« Charger la fiche du cabinet » — et l'écran qui contredisait son résultat.

LE DÉFAUT, MESURÉ EN NAVIGATEUR. `_ao_charge()` verse DÉJÀ la fiche du cabinet
comme socle côté serveur : le SIRET, le SIREN, la TVA et les trois chiffres
d'affaires atteignent les formulaires de l'État à chaque appel. Mais les champs
de l'écran lisent le stockage du navigateur, et affichaient donc
« non renseigné » sur des valeurs que le serveur allait employer.

POURQUOI C'EST PIRE QU'UN SIMPLE MANQUE. Un écran qui dit le contraire de ce
qu'il produit fait ressaisir à la main ce qui était déjà là — ou, plus
sûrement, pousser une valeur approximative PAR-DESSUS une valeur vérifiée. Le
SIRET affiché vide invite à le retaper de mémoire, et c'est ainsi qu'un chiffre
faux entre dans un DC1 déposé chez un acheteur.

CE QUE CES RÈGLES TIENNENT :

  · L'ORDRE. La saisie de l'écran l'emporte sur le dossier, ici comme côté
    serveur. Les deux divergeraient si l'un des deux s'inversait, et c'est
    l'écran qui aurait tort sans qu'on le sache.

  · LE VERROU. Ce sont les données du CABINET : dénomination, SIRET, chiffres
    d'affaires, signataire. La route est fermée à l'administration, et la
    politique d'accès le déclare avec son motif.

  · CE QUI MANQUE EST NOMMÉ. Le RCS, le code NAF, l'effectif et l'assurance ne
    sont pas au dossier. Annoncer « fiche chargée » sans le dire ferait croire
    la fiche complète — et c'est au dépôt des plis qu'on s'en apercevrait.
"""
import re

import pytest

import acces
import dossier_entreprise


ROUTE = "/api/datacenter/marche/fiche-cabinet"


def _js():
    import io, os
    ici = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return io.open(os.path.join(ici, "ingenierie-dc.js"), encoding="utf-8").read()


# ── 1. LE VERROU ───────────────────────────────────────────────────────────

def test_la_route_est_fermee_a_l_administration(connecte, anonyme):
    """Les données du cabinet ne sortent que vers qui répond POUR lui."""
    for client, attendu in ((anonyme, (401, 302, 403)), (connecte, (403,))):
        r = client.get(ROUTE)
        assert r.status_code in attendu, (r.status_code, attendu)


def test_la_politique_d_acces_la_declare_avec_son_motif():
    """UNE ROUTE FERMÉE SANS DÉCISION ÉCRITE est une fermeture qu'on lèvera
    par distraction. Le motif doit nommer ce qui sort."""
    assert ROUTE in acces.API_ADMIN, (
        "la route n'est pas déclarée : le service démarrerait avec une "
        "interface fermée que personne n'a décidée")
    motif = acces.API_ADMIN[ROUTE]

    # ELLE EXIGE UN MOTIF PROPRE, PAS LE MOTIF COMMUN.
    #
    # LA PREMIÈRE VERSION SE CONTENTAIT DE « SIRET ou cabinet » quelque part
    # dans le texte — et le motif générique de la famille contient déjà le mot
    # « cabinet ». La mutation qui remplaçait le motif détaillé par le
    # générique y survivait donc : la règle passait pour une raison sans
    # rapport avec ce qu'elle prétendait.
    #
    # CE QUI SE MESURE : cette route expose autre chose que ses sœurs. Elles
    # rendent le dossier d'un ACHETEUR ; celle-ci rend l'identité du CABINET
    # lui-même. Son motif doit donc dire quelque chose de plus, et nommer ce
    # qui sort — sans quoi la décision d'accès ne se relit pas.
    assert motif != acces._MOTIF_MARCHE, (
        "le motif est celui de toute la famille : il ne dit pas que CETTE "
        "route sort l'identité du cabinet")
    propre = motif.replace(acces._MOTIF_MARCHE, "")
    nommes = [m for m in ("SIRET", "chiffres d'affaires", "dénomination",
                          "signataire") if m in propre]
    assert len(nommes) >= 2, (
        "le motif propre à cette route ne nomme pas ce qui en sort — relevé : "
        "%r dans %r" % (nommes, propre.strip()))


def test_elle_rend_la_fiche_ET_ce_qui_lui_manque(marche):
    r = marche.get(ROUTE)
    assert r.status_code == 200, r.status_code
    j = r.get_json()
    assert j["ok"] is True
    etat = dossier_entreprise.fiche_candidat()
    assert j["fiche"] == etat["fiche"]
    assert j["fournis"] == etat["fournis"]
    assert j["attendus"] == etat["attendus"]
    assert j["fournis"] < j["attendus"], (
        "la route annonce une fiche complète : le témoin est cassé, ou le "
        "dossier a été complété sans que cette règle le sache")
    manquants = {m["cle"] for m in j["manques"]}
    assert manquants, "aucun manque nommé"
    for m in j["manques"]:
        assert m.get("ou_trouver"), (
            "« %s » manque sans dire où le chercher" % m["cle"])


def test_le_siret_et_les_trois_exercices_sortent_bien_par_cette_route(marche):
    """LA RÈGLE DÉCISIVE DU VOLET SERVEUR. Sans elle, la route pourrait rendre
    une fiche amputée et le geste écrirait des champs vides — ce qui est
    exactement l'état d'avant, avec un bouton de plus."""
    f = marche.get(ROUTE).get_json()["fiche"]
    for cle in ("siret", "siren", "tva", "ca_n1", "ca_n2", "ca_n3"):
        assert str(f.get(cle) or "").strip(), (
            "« %s » ne sort pas de la route : le geste ne pourra pas l'écrire"
            % cle)


# ── 2. LE GESTE, DANS LA PAGE ──────────────────────────────────────────────

def test_le_bouton_existe_et_appelle_la_route():
    """ELLE LIT LE SOURCE PARCE QUE LE BRANCHEMENT EST UNE CHAÎNE : bouton →
    écouteur → fonction → route. Le vérifier en navigateur est fait par le
    banc ; ici on tient les quatre maillons ensemble, pour qu'en casser un se
    voie sans rouvrir un navigateur."""
    js = _js()
    assert 'id="ig-ao-cab-go"' in js, "le bouton n'est plus dessiné"
    assert 'aoFicheCabinet' in js, "la fonction a disparu"
    assert re.search(r'\$\("#ig-ao-cab-go"[^)]*\)[\s\S]{0,120}'
                     r'addEventListener\("click", aoFicheCabinet\)', js), (
        "le bouton n'est plus branché sur la fonction")
    i = js.index("function aoFicheCabinet")
    corps = js[i:i + 2600]
    assert ROUTE in corps, "la fonction n'appelle plus la route"
    assert "credentials" in corps, (
        "l'appel n'emporte pas la session : une route fermée répondrait 401")


def test_le_geste_n_ECRASE_pas_ce_qui_est_deja_saisi():
    """L'ORDRE, MESURÉ SUR LE CODE QUI L'APPLIQUE.

    Une consultation peut demander une variante — un établissement secondaire,
    un autre signataire — et celui qui l'a tapée en sait plus que le dossier.
    C'est le même ordre que côté serveur, où le socle passe DERRIÈRE la saisie.
    """
    js = _js()
    i = js.index("function aoFicheCabinet")
    corps = js[i:i + 2600]
    assert re.search(r'if \(String\(AO_FICHE\[k\] \|\| ""\)\.trim\(\)\)'
                     r'[\s\S]{0,60}return', corps), (
        "la garde qui préserve la saisie a disparu : le dossier écraserait ce "
        "que l'opérateur vient de taper")
    assert "gardes" in corps, (
        "les saisies conservées ne sont plus comptées : l'opérateur ne saurait "
        "pas que le geste n'a pas tout écrit")


def test_le_message_dit_ce_qui_MANQUE_au_dossier():
    """« Fiche chargée » sans la suite ferait croire la fiche complète."""
    js = _js()
    i = js.index("function aoFicheCabinet")
    corps = js[i:i + 2600]
    assert "manques" in corps, "la route rend les manques, le geste les jette"
    assert "absents" in corps, corps[:200]
    assert "s'inventent pas" in corps or "inventent pas" in corps, (
        "le message ne dit pas que ces champs ne s'inventent pas")


def test_la_fiche_est_REDESSINEE_avant_que_le_message_parle():
    """LE DÉFAUT QUE J'AI ÉCRIT PUIS MESURÉ. Les champs portent les anciennes
    valeurs dans leur attribut `value` : sans redessin, on annoncerait « 16
    valeurs écrites » au-dessus de seize champs restés vides. Et `aoRemplir`
    ne redessine la fiche que si elle est VIDE — donc c'est ici, et nulle part
    ailleurs, que le redessin doit se faire."""
    js = _js()
    i = js.index("function aoFicheCabinet")
    corps = js[i:i + 2600]
    j_rendre = corps.index("aoFicheRendre")
    j_msg = corps.index("valeur(s) écrite(s)")
    assert j_rendre < j_msg, (
        "le message est posé avant le redessin : il annoncerait des valeurs "
        "que les champs ne portent pas encore")
    # ET LE TÉMOIN : `aoRemplir` garde bien sa condition de vacuité, sinon le
    # redessin d'ici serait redondant et la règle mesurerait du vide.
    assert re.search(r'if \(!\$\("#ig-ao-fiche"\)\.innerHTML\) aoFicheRendre',
                     js), (
        "`aoRemplir` redessine désormais la fiche sans condition : cette règle "
        "ne mesure plus rien, et le message pourrait être effacé")
