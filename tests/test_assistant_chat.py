# -*- coding: utf-8 -*-
"""Le chat cesse de citer ses sources, et /api/chat refuse une conversation
malformée avant toute dépense.

DEUX CHANGEMENTS, DEUX RAISONS DIFFÉRENTES.

  1. RÉFÉRENCES. Le chat public affichait, entre crochets, le titre et le
     thème de l'extrait interne utilisé pour répondre — un détail
     d'implémentation (« il existe une base de connaissance, voici comment
     elle est rangée ») que rien ne demandait de montrer à un visiteur. La
     consigne du chat (assistant._GROUNDING) cesse d'exiger ces crochets ;
     celle des livrables (assistant._GEN_GROUNDING, utilisée par generate())
     les garde intacts : un rapport signé pour un consultant doit pouvoir
     dire d'où vient chaque affirmation, un message de chat non.

  2. FORME DE LA CONVERSATION. « messages » vient tel quel du navigateur :
     rien ne garantissait que c'était une liste de dictionnaires. Une chaîne,
     un nombre ou un dictionnaire à la place atteignaient _clean_history, qui
     appelle .get() sur chaque élément sans s'en protéger — et qu'aucun except
     de la route ne rattrape (seul AssistantError l'est) — après avoir déjà
     déclenché une recherche RAG payée pour rien. /api/chat referme la porte
     en tête de fonction, avant toute dépense, tout en laissant passer une
     conversation absente ou vide : c'est un cas déjà traité plus loin.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import assistant  # noqa: E402

H = {"Origin": "http://localhost"}


@pytest.fixture
def client():
    import app
    app.app.config["TESTING"] = True
    return app.app.test_client()


@pytest.fixture
def sans_cle(monkeypatch):
    """Aucun fournisseur configuré : un appel qui atteint assistant.answer
    échoue de façon déterministe (503 « not_configured »), ce qui distingue
    sans ambiguïté « la validation a laissé passer » de « le modèle a répondu »."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)


# ── 1. Le chat ne cite plus ses sources ─────────────────────────────────────

def test_la_consigne_du_chat_n_exige_plus_de_citation():
    assert "cite sa source entre crochets" not in assistant._GROUNDING


def test_la_consigne_du_chat_proscrit_explicitement_titre_theme_et_crochets():
    assert "SANS" in assistant._GROUNDING
    assert "citer leur titre" in assistant._GROUNDING
    assert "crochets" in assistant._GROUNDING


def test_la_consigne_garde_le_refus_d_inventer_et_le_signalement_des_lacunes():
    """Le changement porte sur la CITATION, pas sur la fiabilité : ces deux
    garde-fous n'ont aucune raison de bouger."""
    assert "N'invente jamais" in assistant._GROUNDING
    assert "ne contient pas d'élément précis" in assistant._GROUNDING


def test_les_livrables_gardent_leurs_citations():
    """DÉFAUT À NE PAS INTRODUIRE : un rapport signé sans provenance de ses
    affirmations est un livrable dégradé, pas un chat perfectionné."""
    assert "cite la source entre crochets" in assistant._GEN_GROUNDING


def test_le_prompt_systeme_du_chat_porte_bien_la_nouvelle_consigne():
    """_system() est le SEUL chemin par lequel _GROUNDING atteint le modèle :
    une correction du texte qui n'y serait pas branchée ne changerait rien
    à ce que le modèle reçoit réellement."""
    txt = assistant._system("un contexte RAG quelconque")
    assert "citer leur titre" in txt and "crochets" in txt
    assert txt.index("un contexte RAG quelconque") < txt.index("citer leur titre"), (
        "la consigne doit suivre les extraits, pas les précéder")


def test_sans_contexte_rag_le_systeme_ne_porte_aucune_consigne_d_ancrage():
    """Rien à ancrer, rien à ne pas citer : le prompt système reste nu."""
    assert assistant._system(None) == assistant.SYSTEM_PROMPT
    assert assistant._system("") == assistant.SYSTEM_PROMPT


# ── 2. /api/chat refuse une conversation malformée avant toute dépense ─────

@pytest.mark.parametrize("mauvais", [
    "juste une chaine",
    "",                                               # chaîne vide : itérer dessus ne lève pas
    {"role": "user", "content": "salut"},           # un dict, pas une liste
    ["salut"],                                       # une liste de chaînes
    [{"role": "user", "content": "ok"}, "intrus"],    # un élément valide, un intrus
    123,
], ids=["chaine", "chaine_vide", "dict", "liste_de_chaines", "liste_mixte", "entier"])
def test_une_conversation_malformee_est_refusee_en_400(client, mauvais):
    r = client.post("/api/chat", headers=H, json={"messages": mauvais})
    assert r.status_code == 400, r.status_code
    j = r.get_json()
    assert j["ok"] is False
    assert j["error"] == "format_invalide"


def test_le_refus_de_forme_n_appelle_jamais_la_recherche_rag(client, monkeypatch):
    """LA DÉMONSTRATION, pas la déclaration. Si la validation était posée
    après la recherche RAG — ou contournée par un chemin oublié — cette
    règle le verrait : rag.search est armé pour lever à la moindre visite."""
    import app

    def _explose(*a, **k):
        raise AssertionError("rag.search a été appelé malgré une conversation malformée")
    monkeypatch.setattr(app.rag, "search", _explose)
    r = client.post("/api/chat", headers=H, json={"messages": "juste une chaine"})
    assert r.status_code == 400


@pytest.mark.parametrize("absent", [{}, {"messages": None}],
                         ids=["cle_absente", "explicitement_null"])
def test_une_conversation_absente_n_est_pas_un_format_invalide(client, sans_cle, absent):
    """CE QUE LA VALIDATION NE DOIT PAS CASSER. « messages » manquant ou nul
    est la conversation VIDE, pas une conversation MALFORMÉE : elle continue
    de traverser jusqu'à assistant.answer, qui la refuse pour une raison
    différente (message vide) et avec un message différent."""
    r = client.post("/api/chat", headers=H, json=absent)
    j = r.get_json()
    assert j.get("error") != "format_invalide", j


def test_une_conversation_bien_formee_atteint_le_modele(client, sans_cle):
    """Une liste de dictionnaires valides n'est PAS un format invalide : la
    requête doit progresser jusqu'à assistant.answer, qui échoue ici pour une
    tout autre raison (aucun fournisseur configuré, 503) — la preuve que le
    400 « format_invalide » ne s'est pas déclenché à tort."""
    r = client.post("/api/chat", headers=H,
                    json={"messages": [{"role": "user", "content": "Bonjour"}]})
    j = r.get_json()
    assert j.get("error") != "format_invalide", j
    assert r.status_code == 503, r.status_code
    assert j["error"] == "not_configured"
