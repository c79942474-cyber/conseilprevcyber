# -*- coding: utf-8 -*-
"""L'indexation vectorielle se termine, même quand un document résiste.

CE QUI SE PASSAIT. Une exception sur UN document faisait sortir du passage :
tous les documents derrière lui n'étaient jamais touchés. Mesuré avant
correction, sur trois documents dont le premier échoue toujours — dix passages,
dix tentatives, TOUTES sur le même : les deux autres n'avaient pas avancé d'un
lot. La vectorisation ne finissait donc jamais, et rien ne le disait :
l'exception était avalée sans une ligne de journal.

CES RÈGLES MESURENT LE RÉSULTAT, pas la présence d'un `try`. Elles font tourner
le travail contre un magasin double et regardent ce qui a avancé.
"""
import logging
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import automation                                                # noqa: E402

ECHECS = automation.ECHECS_AVANT_MISE_DE_COTE


class RagDouble:
    """Un magasin qui indexe en trois lots — et qui peut casser à volonté."""

    persistent = True

    def __init__(self, docs, casse=(), lots=3):
        self.docs = list(docs)
        self.casse = set(casse)
        self.restant = {d: lots for d in docs}
        self.appels = []

    def list_documents(self):
        return [{"id": d, "status": "indexing"}
                for d in self.docs if self.restant[d] > 0]

    def index_next(self, doc_id):
        self.appels.append(doc_id)
        if doc_id in self.casse:
            raise RuntimeError("chunk illisible")
        self.restant[doc_id] -= 1
        return {"done": self.restant[doc_id] <= 0}


@pytest.fixture
def passages(monkeypatch):
    """Un compteur d'échecs neuf à chaque règle, et le magasin injecté."""
    monkeypatch.setattr(automation, "_echecs_index", {})

    def lancer(rag, n=10):
        monkeypatch.setitem(automation._deps, "rag", rag)
        for _ in range(n):
            automation.job_index_rag()
        return rag
    return lancer


def test_trois_documents_sains_sont_TOUS_indexes(passages):
    """Le témoin positif. Sans lui, un travail qui ne ferait rien du tout
    passerait les règles suivantes sans qu'on s'en aperçoive."""
    r = passages(RagDouble(["a", "b", "c"]))
    assert r.restant == {"a": 0, "b": 0, "c": 0}, r.restant


def test_un_document_qui_ECHOUE_ne_bloque_plus_les_autres_DES_LE_PREMIER_PASSAGE(
        passages):
    """LA RÈGLE CENTRALE — et elle a dû être reprise.

    Sa première version lançait DIX passages et vérifiait qu'à la fin les
    autres documents étaient indexés. Elle passait, mais pour la mauvaise
    raison : au bout de trois passages le document fautif est MIS DE CÔTÉ, et
    les suivants avancent alors même si l'échec faisait toujours sortir du
    passage. Une mutation remettant le `return` ne faisait donc rien tomber —
    la seconde protection masquait l'absence de la première.

    On mesure donc le PREMIER passage : dans le même passage, l'échec d'un
    document doit laisser les autres avancer.
    """
    r = passages(RagDouble(["mauvais", "b", "c"], casse={"mauvais"}), n=1)
    assert r.appels.count("mauvais") == 1, r.appels
    assert "b" in r.appels and "c" in r.appels, (
        "un échec fait encore sortir du passage : seuls %s ont été touchés"
        % sorted(set(r.appels)))
    assert r.restant["b"] < 3 and r.restant["c"] < 3, r.restant


def test_un_document_qui_echoue_TROP_est_mis_de_cote(passages):
    """Sinon il consommerait le budget à chaque passage et retarderait les
    autres indéfiniment — l'arrêt aurait changé de forme, pas disparu."""
    r = passages(RagDouble(["mauvais", "b"], casse={"mauvais"}), n=12)
    assert r.appels.count("mauvais") == automation.ECHECS_AVANT_MISE_DE_COTE, (
        r.appels.count("mauvais"))
    etat = automation.index_rag_etat()
    assert etat["mis_de_cote"] == ["mauvais"], etat


def test_un_SUCCES_efface_les_echecs_passes(passages):
    """Ce sont les échecs CONSÉCUTIFS qui condamnent, pas leur total : une
    panne d'embeddings de trois minutes ne doit pas condamner un document."""
    # ASSEZ D'ÉCHECS POUR CONDAMNER LE DOCUMENT S'ILS S'ADDITIONNAIENT. Avec
    # seulement deux échecs, le seuil de trois n'était pas atteint et le
    # document aboutissait de toute façon : la règle ne distinguait rien, et
    # une mutation retirant la remise à zéro survivait.
    r = RagDouble(["a"], lots=3)
    appels = {"n": 0}
    vrai = r.index_next

    def capricieux(doc_id):
        appels["n"] += 1
        if appels["n"] % 2 == 1:                 # un échec sur deux : 1, 3, 5…
            raise RuntimeError("réseau")
        return vrai(doc_id)

    r.index_next = capricieux
    passages(r, n=14)
    assert appels["n"] - r.restant.get("a", 0) >= 2 * ECHECS, (
        "l'essai ne produit pas assez d'échecs pour éprouver la remise à zéro")
    assert r.restant["a"] == 0, (
        "un document intermittent n'aboutit pas : les échecs s'additionnent "
        "au lieu d'être effacés par chaque succès")
    assert automation.index_rag_etat()["mis_de_cote"] == [], (
        automation.index_rag_etat())


def test_l_echec_est_JOURNALISE_avec_l_identifiant(passages, caplog):
    """Le silence était le vrai défaut ; l'arrêt n'en était que la
    conséquence visible. Deux mois sans un mot, c'est ce qui rend un blocage
    invisible."""
    with caplog.at_level(logging.ERROR, logger="automation"):
        passages(RagDouble(["mauvais", "b"], casse={"mauvais"}), n=4)
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "mauvais" in messages, "l'échec ne nomme pas le document"
    assert "indexation" in messages.lower(), messages[:200]


def test_l_etat_de_l_indexation_est_SERVI_a_la_console(passages, admin):
    """Un document mis de côté reste « en cours » dans la liste : sans cette
    information, la console montre un document qui n'avancera plus."""
    passages(RagDouble(["mauvais"], casse={"mauvais"}), n=6)
    r = admin.get("/api/admin/rag/documents",
                  headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.status_code
    j = r.get_json()
    assert "indexation" in j, "l'état de l'indexation n'est pas servi"
    assert j["indexation"]["seuil"] == automation.ECHECS_AVANT_MISE_DE_COTE


def test_une_base_injoignable_ne_leve_pas_et_le_dit(passages, caplog):
    class Muet:
        persistent = True
        def list_documents(self):
            raise RuntimeError("base injoignable")
    with caplog.at_level(logging.ERROR, logger="automation"):
        passages(Muet(), n=2)
    # « OU caplog.records » RENDAIT CETTE RÈGLE TOUJOURS VRAIE : n'importe
    # quelle ligne de journal la satisfaisait, y compris une venue d'ailleurs.
    # On exige le message du travail lui-même.
    messages = [r.getMessage() for r in caplog.records
                if r.name == "automation"]
    assert any("liste des documents" in m for m in messages), messages
