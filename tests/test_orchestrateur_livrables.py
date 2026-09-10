# -*- coding: utf-8 -*-
"""L'orchestrateur agentique de rédaction de livrables : un agent PAR SUJET,
réutilisé, avec un levier de rapidité DÉCLARÉ.

CE QUE CES RÈGLES TIENNENT. Que l'orchestrateur route chaque sujet vers SES
thèmes de la base — IEC 62443 vers le référentiel 62443, un lot de data center
vers son aiguillage —, qu'il RÉUTILISE l'agent d'une demande à l'autre, que le
mode rapide saute bien le juge (et le DISE), et que la génération PILOTE son
re-classement par ce plan. Le module d'orchestration est PUR : ces règles
tournent sans clé ni réseau.
"""
import io
import os

import orchestrateur_livrables as orch
import livrables

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = io.open(os.path.join(ICI, "app.py"), encoding="utf-8").read()


def test_l_orchestrateur_route_un_sujet_de_REFERENTIEL_vers_ses_docs():
    """IEC 62443, l'exemple demandé. Un livrable de synthèse 62443 doit
    ramener le référentiel « IEC 62443 » dans son plan — l'agent n'est pas
    réservé aux centres de données, il route par le SUJET."""
    o = orch.Orchestrateur()
    p = o.plan("synthese-62443", inputs={"secteur": "énergie"})
    assert "IEC 62443" in p["themes_groupe"], (
        "l'agent 62443 ne route pas vers le référentiel IEC 62443 : %r"
        % p["themes_groupe"])
    # ET LE TÉMOIN : un sujet sans référentiel désigné n'invente pas de thème.
    tid_nu = next((t["id"] for t in livrables.TYPES
                   if not livrables.themes_du_type(t["id"])[1]), None)
    if tid_nu:
        assert o.plan(tid_nu)["themes_groupe"] == []


def test_un_agent_de_data_center_porte_son_aiguillage_de_stade():
    """Le sujet « lot de data center » route, lui, vers la famille et le
    sous-dossier de son STADE — l'aiguillage bâti précédemment, vu à travers
    l'agent."""
    o = orch.Orchestrateur()
    p = o.plan("dc-note-calcul", phase="AOR", piece="AOR-01")
    assert any("Mise en service" in t for t in p["sous_dossiers"]), (
        "l'agent d'un livrable de réception (AOR) ne route pas vers la mise "
        "en service : %r" % p["sous_dossiers"])


def test_le_mode_rapide_SAUTE_le_juge_et_le_DIT():
    """LE LEVIER DE RAPIDITÉ, MESURÉ ET DÉCLARÉ. En mode rapide, le plan pose
    reclasser=False (un appel modèle de moins) ET nomme le compromis. En mode
    normal, reclasser=True et aucun compromis caché."""
    o = orch.Orchestrateur()
    lent = o.plan("synthese-62443")
    rapide = o.plan("synthese-62443", rapide=True)
    assert lent["reclasser"] is True and lent["compromis"] == "", lent
    assert rapide["reclasser"] is False, "le mode rapide n'allège rien"
    assert rapide["compromis"], (
        "le mode rapide saute le juge SANS le dire : un compromis caché")
    assert "rappel" in rapide["compromis"].lower()


def test_l_agent_est_REUTILISE_d_une_demande_a_l_autre():
    """LA FLUIDITÉ : un même sujet rend le MÊME agent, sans le reconstruire.
    C'est ce que le cache de l'orchestrateur apporte — un orchestrateur créé
    par requête n'aurait aucun cache."""
    o = orch.Orchestrateur()
    a = o.agent("synthese-62443")
    b = o.agent("synthese-62443")
    assert a is b, "deux demandes du même sujet reconstruisent l'agent"
    o.agent("synthese-62443", rapide=True)   # une variante distincte
    o.agent("dc-note-calcul", phase="APD", piece="APD-04")
    assert o.taille_cache() == 3, (
        "le cache ne distingue pas les variantes (sujet, rapide, pièce) : %d"
        % o.taille_cache())


def test_l_orchestration_est_PURE_aucun_modele_aucun_rag():
    """LA PROPRIÉTÉ QUI REND CES RÈGLES POSSIBLES SANS CLÉ. Le module
    n'importe ni `rag_store` ni `assistant`, et n'appelle aucun modèle : il
    DIT quoi interroger, il ne l'interroge pas."""
    src = io.open(os.path.join(ICI, "orchestrateur_livrables.py"),
                  encoding="utf-8").read()
    for interdit in ("import rag_store", "import assistant", ".search(",
                     ".generate(", ".rerank("):
        assert interdit not in src, (
            "l'orchestrateur touche à l'impur (%s) : il cesserait d'être "
            "mesurable sans clé, et mêlerait pilotage et exécution" % interdit)


def test_la_generation_PILOTE_son_reclassement_par_le_plan():
    """SANS CE BRANCHEMENT, L'ORCHESTRATEUR NE PILOTE RIEN. La génération doit
    lire le plan de l'agent et n'appeler le juge QUE si le plan le demande —
    sinon le mode rapide n'allège jamais rien."""
    assert "orchestrateur_livrables.ORCHESTRATEUR.plan(" in APP, (
        "la génération ne demande pas son plan à l'orchestrateur")
    # Le re-classement est conditionné au plan, pas inconditionnel.
    i = APP.index("if plan_agent[\"reclasser\"] else brut")
    fen = APP[i - 160:i + 40]
    assert "assistant.rerank(model, query, brut, 8)" in fen, (
        "le re-classement n'est plus piloté par le plan de l'agent : %r" % fen)
    # ET LE PLAN REMONTE AU CLIENT — l'orchestration se voit.
    assert "agent=plan_agent," in APP, (
        "le plan de l'agent n'est pas rendu au client : le pilotage est "
        "invisible")
