"""Ce que le connecteur de jurisprudence dit quand il ne peut pas servir.

LE DÉFAUT CORRIGÉ ICI EST UN DÉFAUT DE DIAGNOSTIC, pas de fonctionnement. Le
corpus LibreJustice répond — il refuse. Son refus est un 401 : il exige une
autorisation OAuth 2.1 avec enregistrement dynamique de client, un flux conçu
pour un client interactif où quelqu'un consent dans son navigateur. Ce module
est un appelant sans écran ; il ne sait pas la négocier.

Le message rendait cela par « renseignez LIBREJUSTICE_TOKEN (jeton porteur) ».
Or LibreJustice ne délivre AUCUN jeton statique. Le diagnostic prescrivait donc
une action impossible — et un diagnostic qu'on suit sans pouvoir aboutir coûte
plus cher qu'un diagnostic muet.

CE QUI EST ÉPROUVÉ :

  · le refus ne réclame plus un jeton qui n'existe pas ;
  · il DIT ce qui manque réellement — le protocole, pas un réglage ;
  · l'adresse des métadonnées d'autorisation, que le refus porte lui-même dans
    son en-tête, est lue et rendue au lieu d'être jetée ;
  · un jeton FOURNI et refusé se distingue d'un jeton absent : les deux ne se
    soignent pas pareil ;
  · une analyse sans jurisprudence dit POURQUOI — l'absence de décision et
    l'absence de corpus ne sont pas le même fait.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import librejustice as L  # noqa: E402


class _Reponse:
    """Un refus du corpus, avec ou sans en-tête d'autorisation."""

    def __init__(self, statut=401, entetes=None):
        self.status_code = statut
        self.headers = entetes or {}
        self.text = ""

    def json(self):
        return {}


# ── 1. L'en-tête du refus est lu ───────────────────────────────────────────

@pytest.mark.parametrize("entete,attendu", [
    ('Bearer resource_metadata="https://librejustice.fr/.well-known/oauth-protected-resource"',
     "https://librejustice.fr/.well-known/oauth-protected-resource"),
    ('Bearer as_uri="https://librejustice.fr/as"', "https://librejustice.fr/as"),
    ('Bearer realm="x"', ""),
    ("", ""),
])
def test_l_adresse_d_autorisation_se_lit_dans_le_refus(entete, attendu):
    """LE REFUS PORTAIT LA RÉPONSE, ET PERSONNE NE LA LISAIT. La norme veut
    qu'un 401 nomme l'adresse de ses métadonnées d'autorisation — c'est
    précisément ce qu'il faut consulter pour savoir si un accès sans humain est
    possible."""
    assert L._serveur_autorisation({"WWW-Authenticate": entete}) == attendu


def test_l_en_tete_est_lu_quelle_que_soit_sa_casse():
    """Les serveurs ne s'accordent pas sur la casse des en-têtes, et une
    bibliothèque qui normalise ici peut ne pas normaliser là."""
    url = 'Bearer resource_metadata="https://x.test/m"'
    assert L._serveur_autorisation({"www-authenticate": url}) == "https://x.test/m"


def test_une_adresse_absente_rend_une_chaine_vide_et_non_none():
    """Cette valeur part dans un message d'exploitation : un « None » au milieu
    d'une phrase française est une fuite de mécanique."""
    assert L._serveur_autorisation({}) == ""
    assert L._serveur_autorisation(None) == ""


# ── 2. Le refus ne prescrit plus l'impossible ──────────────────────────────

def _refus(monkeypatch, entetes=None, jeton=""):
    monkeypatch.setattr(L, "JETON", jeton)
    monkeypatch.setattr(L, "ACTIF", True)
    monkeypatch.setattr(L.requests, "post",
                        lambda *a, **k: _Reponse(401, entetes))
    L.oublier() if hasattr(L, "oublier") else None
    ok, motif = L._appel("initialize", {})
    return ok, motif


def test_le_refus_ne_reclame_plus_un_jeton_qui_n_existe_pas(monkeypatch):
    """LibreJustice annonce « OAuth 2.1 avec enregistrement dynamique de
    client : aucune clé à configurer ». Demander un jeton porteur envoie
    chercher pendant des heures ce que personne ne délivre."""
    ok, motif = _refus(monkeypatch)
    assert ok is False
    assert "AUCUN JETON STATIQUE" in motif
    assert "renseignez LIBREJUSTICE_TOKEN" not in motif


def test_le_refus_nomme_ce_qui_manque_vraiment(monkeypatch):
    """Ce qui manque est un PROTOCOLE, pas un réglage. Un exploitant qui lit
    « exige une autorisation » cherche une variable d'environnement."""
    _ok, motif = _refus(monkeypatch)
    for attendu in ("OAuth 2.1", "enregistrement dynamique", "échange de jeton"):
        assert attendu in motif, attendu


def test_le_refus_propose_les_deux_issues_reelles(monkeypatch):
    _ok, motif = _refus(monkeypatch)
    assert "client_credentials" in motif
    assert "UNE FOIS" in motif


def test_le_refus_rend_l_adresse_d_autorisation_quand_elle_est_annoncee(monkeypatch):
    _ok, motif = _refus(monkeypatch, {
        "WWW-Authenticate": 'Bearer resource_metadata="https://librejustice.fr/.well-known/x"'})
    assert "https://librejustice.fr/.well-known/x" in motif
    assert L.etat()["autorisation"] == "https://librejustice.fr/.well-known/x"


def test_un_jeton_fourni_et_refuse_se_distingue_d_un_jeton_absent(monkeypatch):
    """LES DEUX NE SE SOIGNENT PAS PAREIL : l'un demande d'obtenir un accès,
    l'autre de renouveler celui qu'on a. Les confondre envoie refaire une
    démarche déjà faite."""
    _ok, sans = _refus(monkeypatch, jeton="")
    _ok2, avec = _refus(monkeypatch, jeton="jeton-de-labo")
    assert "REFUSÉ le jeton fourni" in avec
    assert "REFUSÉ le jeton fourni" not in sans
    assert "AUCUN JETON STATIQUE" not in avec


def test_l_etat_dit_que_le_connecteur_ne_negocie_pas_oauth():
    """Dit une fois pour toutes, dans l'état : sans cette ligne, un exploitant
    conclut qu'il lui manque un réglage alors qu'il lui manque un protocole."""
    assert L.etat()["oauth_negocie"] is False


# ── 3. Le verrou n'est pas réentrant ───────────────────────────────────────

def test_un_refus_du_corpus_ne_fige_pas_l_application(monkeypatch):
    """LE DÉFAUT LE PLUS COÛTEUX DE CE MODULE, ET IL A ÉTÉ INTRODUIT ICI.

    `_appel` s'exécute DÉJÀ sous `_verrou` : `_outil` et `disponible` le
    prennent avant d'appeler `_ouvrir`, qui appelle `_appel`. Or
    `threading.Lock` n'est pas réentrant. Reprendre le verrou dans la branche
    du refus bloquait le fil sur lui-même — et le premier 401 du corpus figeait
    l'application, sans erreur, sans trace, sans fin.

    ÉPROUVÉ SUR LE TEMPS, parce qu'un interblocage ne lève rien : il ne se
    constate qu'à l'absence de réponse. Une suite qui se fige ne rapporte même
    pas d'échec — elle se fait tuer par un délai, et personne ne sait où."""
    import threading

    monkeypatch.setattr(L, "ACTIF", True)
    monkeypatch.setattr(L, "JETON", "")
    monkeypatch.setattr(
        L.requests, "post",
        lambda *a, **k: _Reponse(401, {
            "WWW-Authenticate": 'Bearer resource_metadata="https://x.test/m"'}))

    resultat = {}
    fini = threading.Event()

    def essai():
        try:
            resultat["r"] = L.disponible()
        finally:
            fini.set()

    threading.Thread(target=essai, daemon=True).start()
    assert fini.wait(10), ("le connecteur s'est bloqué sur son propre verrou : "
                           "un refus du corpus fige l'application")
    assert resultat["r"]["ok"] is False


def test_le_refus_reste_lisible_apres_plusieurs_appels(monkeypatch):
    """Un interblocage ne se voit parfois qu'au deuxième passage, quand l'état
    conservé du premier change le chemin pris."""
    import threading

    monkeypatch.setattr(L, "ACTIF", True)
    monkeypatch.setattr(L, "JETON", "")
    monkeypatch.setattr(L.requests, "post", lambda *a, **k: _Reponse(401))
    for _ in range(3):
        fini = threading.Event()
        threading.Thread(target=lambda: (L.disponible(), fini.set()),
                         daemon=True).start()
        assert fini.wait(10), "blocage au rappel"


# ── 4. L'état du corpus atteint la page ────────────────────────────────────

def test_toute_recherche_de_jurisprudence_rend_aussi_son_etat():
    """UNE LISTE VIDE A DEUX CAUSES QUI NE SE SOIGNENT PAS PAREIL. Jeter le
    motif en route laissait la page incapable de les distinguer : elle
    n'affichait rien dans les deux cas, et le lecteur concluait qu'aucune
    décision n'existe — un fait juridique, là où il n'y avait qu'une panne de
    raccordement."""
    import app
    decisions, etat = app._juridique_jurisprudence("question quelconque")
    assert isinstance(decisions, list)
    assert set(etat) >= {"ok", "motif"}
    # Le corpus est fermé sur cet environnement : l'état doit le dire, et le
    # motif doit être renseigné plutôt que vide.
    if not etat["ok"]:
        assert etat["motif"], "un échec sans motif n'apprend rien"


def test_chaque_appel_au_corpus_transmet_son_etat_a_la_reponse():
    """L'INVARIANT DE CÂBLAGE. Deux routes interrogent le corpus ; chacune doit
    porter l'état jusqu'à la réponse, sinon la page en est privée sur l'une des
    deux sans que rien ne le signale.

    On lie deux comptes qui doivent bouger ensemble : le nombre d'appels au
    corpus, et le nombre de réponses qui transmettent son état. Une route
    ajoutée demain sans le câblage fait diverger les deux."""
    import re as _re
    with open(os.path.join(ICI, "app.py"), encoding="utf-8") as f:
        src = f.read()
    appels = len(_re.findall(r"=\s*_juridique_jurisprudence\(", src))
    transmis = len(_re.findall(r"corpus=corpus", src))
    assert appels >= 2, "moins d'appels que prévu : la règle ne prouve rien"
    assert transmis == appels, (
        "%d route(s) interrogent le corpus, %d transmettent son état"
        % (appels, transmis))
