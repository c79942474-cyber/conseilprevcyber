# -*- coding: utf-8 -*-
"""UN SEUL CHEMIN POUR REMPLIR UN FORMULAIRE OFFICIEL — et c'est `/piece`.

LE DOUBLON, MESURÉ. `/marche/formulaire` prenait un MODÈLE (« dc1 »),
`/marche/piece` une PIÈCE (« dc1 », « acte_engagement »). Les noms différaient ;
le travail, non : les deux appelaient `ao_dc.remplir`,
`ao_formulaires.valeurs_pour` et `ao_formulaires.remplir_document`, et
rendaient le MÊME fichier sous le MÊME nom — « dc1-projet-non-signe.docx ».
`ao_formulaires.MODELES[m]["piece"]` faisait déjà le pont entre les deux
vocabulaires.

POURQUOI CE N'EST PAS UN DOUBLON DE CONFORT. Deux chemins vers un seul
résultat divergent au premier ajout — une case de plus repérée dans un modèle,
une garde ajoutée d'un seul côté — et c'est celui qu'on oublie qui rend un
formulaire d'hier à un acheteur. `/piece` était déjà le plus complet des deux :
il rend en outre les cases vides, le reste à renseigner et le caractère
bloquant de la pièce.

CE QUE CES RÈGLES TIENNENT :

  · la route dédiée n'existe plus, et rien ne la réclame — ni le code, ni la
    politique d'accès ;
  · `/piece` rend bien, pour les quatre modèles, le fichier que rendait
    `/formulaire` — mesuré par un appel réel, pas par lecture du source ;
  · la page ne recopie PAS la correspondance modèle → pièce : elle la reçoit
    du serveur, sinon les deux tables divergeraient à leur tour ;
  · le message de la page survit à l'absence d'`ignores`, que `/piece` ne
    rend pas.
"""
import io
import json
import os
import re

import pytest

import acces
import ao_formulaires

PIECE = "/api/datacenter/marche/piece"
DISPARUE = "/api/datacenter/marche/formulaire"
ORIGINE = {"Origin": "http://localhost"}
FICHE = {"raison_sociale": "ESSAI SARL", "siret": "494 530 157 00036"}


def _lire(nom):
    ici = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return io.open(os.path.join(ici, nom), encoding="utf-8").read()


def _js():
    return _lire("ingenierie-dc.js")


# ═══════════════════════════════════════════════════════════════════════════
#  1. LA ROUTE DÉDIÉE A DISPARU
# ═══════════════════════════════════════════════════════════════════════════

def test_la_route_formulaire_n_existe_plus(marche):
    assert marche.post(DISPARUE, json={"modele": "dc1"},
                       headers=ORIGINE).status_code == 404
    assert '"%s"' % DISPARUE not in _lire("app.py")
    assert DISPARUE not in acces.API_ADMIN


def test_la_page_n_appelle_plus_que_piece():
    """LA PREMIÈRE ÉCRITURE DE CETTE RÈGLE ÉTAIT FAUSSE : « /marche/formulaire »
    est un PRÉFIXE de « /marche/formulaires », qui existe toujours et que la
    page appelle. Elle tombait donc sur du code parfaitement sain. On cherche
    désormais la chaîne CITÉE, guillemet fermant compris."""
    js = _js()
    assert '"%s"' % DISPARUE not in js, (
        "la page appelle encore la route supprimée")
    assert "X-Remplissage" not in js, (
        "la page lit encore l'en-tête de la route supprimée")
    i = js.index("function aoFormulaireRemplir(")
    corps = js[i:i + 2200]
    assert PIECE in corps, "le geste n'appelle pas /piece"
    assert 'r.headers.get("X-Piece")' in corps


# ═══════════════════════════════════════════════════════════════════════════
#  2. /piece REND BIEN CE QUE /formulaire RENDAIT — APPEL RÉEL
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("modele", sorted(ao_formulaires.MODELES))
def test_piece_rend_le_formulaire_de_chaque_modele(marche, modele):
    cle = ao_formulaires.MODELES[modele]["piece"]
    r = marche.post(PIECE, json={"piece": cle, "fiche": FICHE,
                                 "analyse": None, "saisies": {},
                                 "format": "docx"}, headers=ORIGINE)
    assert r.status_code == 200, (modele, r.status_code)
    # LE NOM DU FICHIER EST CELUI QUE RENDAIT LA ROUTE SUPPRIMÉE : c'est ce
    # que l'opérateur reconnaît, et ce qu'il dépose chez l'acheteur.
    assert ("%s-projet-non-signe.docx" % modele
            in r.headers.get("Content-Disposition", "")), modele
    rap = json.loads(r.headers.get("X-Piece") or "{}")
    for k in ("places", "non_places", "sans_ancre", "maj"):
        assert k in rap, "« %s » manque au rapport de %s" % (k, modele)
    assert isinstance(rap["places"], int), (
        "le compte des rubriques placées n'est plus un nombre : le message de "
        "la page afficherait une liste")


def test_le_pont_modele_piece_vient_du_serveur_et_n_est_pas_recopie():
    """S'il était recopié dans la page, les deux tables divergeraient — et
    c'est la copie oubliée qui enverrait le mauvais formulaire."""
    js = _js()
    i = js.index("function aoFormulaireRemplir(")
    corps = js[i:i + 2200]
    # LA RÈGLE PORTE SUR LA PROVENANCE, pas sur une mise en forme : la
    # première écriture exigeait les trois marques dans une seule instruction
    # (`[^;]`), et tombait sur un code qui les répartit sur deux lignes.
    assert "AO_FORMULAIRES" in corps and ".modeles" in corps, (
        "la page ne lit plus la table des modèles du serveur")
    assert re.search(r"piece\s*=\s*\(piece && piece\.piece\)", corps), (
        "la clé de pièce n'est plus tirée de la table du serveur")
    assert re.search(r"piece:\s*piece\b", corps), (
        "ce n'est pas cette clé qui part dans la requête")
    # LA RÈGLE MESURE LE CODE, PAS LA PROSE. La première écriture cherchait
    # « acte_engagement » dans le bloc entier — et le trouvait dans le
    # commentaire qui EXPLIQUE pourquoi la correspondance ne doit pas être
    # recopiée. Une règle satisfaite ou mise en échec par un commentaire ne
    # mesure rien.
    code = re.sub(r"/\*[\s\S]*?\*/", " ", corps)
    for dur in ("acte_engagement", "attri1"):
        assert dur not in code, (
            "la correspondance est recopiée en dur dans la page : " + dur)


def test_le_serveur_publie_bien_cette_correspondance(marche):
    j = marche.get("/api/datacenter/marche/formulaires").get_json()
    assert j["ok"] is True
    for cle, m in j["modeles"].items():
        assert m.get("piece"), "« %s » ne dit pas quelle pièce il remplit" % cle
        assert m["piece"] == ao_formulaires.MODELES[cle]["piece"]


# ═══════════════════════════════════════════════════════════════════════════
#  3. LE MESSAGE SURVIT À CE QUE /piece NE REND PAS
# ═══════════════════════════════════════════════════════════════════════════

def test_le_message_ne_leve_pas_sur_l_absence_d_ignores():
    """`/formulaire` rendait `ignores`, `/piece` non. Sans garde, le message
    lèverait et l'opérateur verrait « Le formulaire n'a pas pu être rempli »
    sur un formulaire pourtant téléchargé."""
    js = _js()
    i = js.index("function aoFormulaireRemplir(")
    corps = js[i:i + 2600]
    assert "(etat.ignores || [])" in corps, (
        "l'absence d'`ignores` n'est pas gardée")
