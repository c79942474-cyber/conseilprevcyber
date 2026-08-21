"""La route qui rend ENFIN moe_dc.engagement()/plafond_penalite()/
penalite_retard() atteignables — le défaut d'articulation corrigé.

LE DÉFAUT. moe_dc.py chiffrait ce que la maîtrise d'œuvre COÛTE, avec une
route pour cela (/api/datacenter/moe). Il calculait aussi, dans le même
fichier, avec ses formules sourcées et ses tests unitaires propres
(test_moe_engagement.py), ce qu'elle ENGAGE : le seuil de tolérance, le
plafond légal de pénalité (art. 30.II du décret 93-1268), la pénalité de
retard journalière. Mais AUCUNE route ne les appelait — zéro appelant en
production. Le module tenait, ses formules étaient justes, et rien ne
pouvait jamais les faire tourner pour un vrai visiteur.

CE QUE CES CONTRÔLES VÉRIFIENT : la route existe, elle est fermée comme sa
voisine /moe/repartition, elle recalcule le chiffrage plutôt que de faire
confiance au client, et le plafond de l'article 30.II s'applique réellement
— pas seulement dans le module, maintenant depuis la route aussi.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from conftest import ORIGINE  # noqa: E402  — POST sans origine déclarée : refusé


def test_la_route_est_FERMEE_au_visiteur_sans_compte(anonyme):
    r = anonyme.post("/api/datacenter/moe/engagement", headers=ORIGINE,
                     json={"travaux_meur": [38, 42], "cout_meur": 40.0})
    assert r.status_code in (401, 403), r.status_code


def test_la_route_sert_lengagement_au_client(connecte):
    r = connecte.post("/api/datacenter/moe/engagement", headers=ORIGINE,
                      json={"travaux_meur": [38, 42], "cout_meur": 40.0,
                            "taux_tolerance_pct": 5.0})
    assert r.status_code == 200, r.status_code
    d = r.get_json()
    assert d["ok"] is True
    eng = d["engagement"]
    assert eng["ok"] is True
    assert eng["seuil_meur"] == 42.0, eng["seuil_meur"]


def test_LE_POINT_QUI_DECIDE_le_plafond_de_larticle_30_II_sapplique_depuis_la_route(connecte):
    """Le même cas que test_moe_engagement.py, mais tel qu'un vrai visiteur le
    déclenche : par la route, pas en appelant le module directement."""
    r = connecte.post("/api/datacenter/moe/engagement", headers=ORIGINE,
                      json={"travaux_meur": [38, 42], "cout_meur": 40.0,
                            "taux_tolerance_pct": 5.0,
                            "cout_reference_meur": 90.0,
                            "taux_penalite_pct": 20.0})
    assert r.status_code == 200, r.get_json()
    pen = r.get_json()["engagement"]["penalite"]
    assert pen["plafonnee"] is True
    assert pen["brute_meur"] > 10 * pen["retenue_meur"], (
        "le cas d'essai ne montre plus l'utilité du plafond : %s" % pen)


def test_un_cout_absent_est_refuse(connecte):
    r = connecte.post("/api/datacenter/moe/engagement", headers=ORIGINE,
                      json={"travaux_meur": [38, 42]})
    assert r.status_code == 400
    assert r.get_json()["error"] == "cout_absent"


def test_une_mission_HORS_PORTEE_est_refusee_avec_sa_raison(connecte):
    r = connecte.post("/api/datacenter/moe/engagement", headers=ORIGINE,
                      json={"travaux_meur": [38, 42], "cout_meur": 40.0,
                            "mission": "amo"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "hors_portee"


def test_le_retard_est_calcule_meme_sans_taux_de_tolerance_fourni(connecte):
    """LE POINT QUI DÉCIDE. Le retard est une question SÉPARÉE de l'engagement
    de coût : la poser sans taux de tolérance (que le modèle laisse en blanc)
    ne doit pas la bloquer. engagement() se refuse gracieusement (taux_absent,
    ok=False) SANS empêcher le calcul du retard demandé à côté."""
    r = connecte.post("/api/datacenter/moe/engagement", headers=ORIGINE,
                      json={"travaux_meur": [38, 42], "cout_meur": 40.0,
                            "phase_retard": "exe", "jours_retard": 10})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert d["engagement"]["ok"] is False
    assert d["engagement"]["erreur"] == "taux_absent"
    retard = d.get("retard")
    assert retard is not None and retard["ok"] is True
    assert retard["jours"] == 10
    assert retard["montant_meur"] > 0


def test_sans_phase_de_retard_la_cle_retard_est_absente(connecte):
    """Le retard est une question à part : la poser sans réponse ne doit pas
    produire un objet vide ou trompeur — il doit simplement ne pas être là."""
    r = connecte.post("/api/datacenter/moe/engagement", headers=ORIGINE,
                      json={"travaux_meur": [38, 42], "cout_meur": 40.0,
                            "taux_tolerance_pct": 5.0})
    assert r.status_code == 200
    assert "retard" not in r.get_json()


def test_un_identifiant_dengagement_inconnu_reste_refuse(connecte):
    """Contrairement au taux manquant, une CLÉ d'engagement inconnue est une
    erreur d'appelant : elle reste un 400."""
    r = connecte.post("/api/datacenter/moe/engagement", headers=ORIGINE,
                      json={"travaux_meur": [38, 42], "cout_meur": 40.0,
                            "taux_tolerance_pct": 5.0, "cle": "n_existe_pas"})
    assert r.status_code == 400
    assert r.get_json()["erreur"] == "engagement_inconnu"
