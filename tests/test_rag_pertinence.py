# La pertinence du RAG : ce que la génération PROMET doit être ce qu'elle FAIT.
#
# Trois défauts corrigés ici, chacun avec le test qui l'aurait attrapé :
#   · la priorité par thème n'existait que pour les centres de données — les
#     soixante autres types puisaient par pertinence seule ;
#   · la requête de récupération ne portait aucun terme technique du sujet
#     (label générique + champs souvent vides) ;
#   · le « dossier documentaire » ordonnait au modèle de citer des documents
#     dont AUCUN extrait n'avait atteint le prompt (budget coupé, doublons
#     écartés) — une invitation à la citation inventée.
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import livrables      # noqa: E402
import rag_store      # noqa: E402


# ── La priorité par thème couvre TOUS les groupes de la console ────────────

def test_chaque_groupe_de_la_console_a_ses_themes():
    groupes = {t.get("groupe") for t in livrables.TYPES}
    groupes.discard(rag_store.FAMILLE_DATACENTER)   # chemin dédié, déjà couvert
    sans = sorted(g for g in groupes if g not in livrables.GROUPE_THEMES)
    assert not sans, "groupes sans thèmes prioritaires : %s" % ", ".join(sans)


def test_les_themes_declares_existent_dans_la_base():
    connus = set(rag_store.THEMES)
    for g, ts in livrables.GROUPE_THEMES.items():
        inconnus = [t for t in ts if t not in connus]
        assert not inconnus, "%s : %s" % (g, inconnus)


def test_un_type_nis2_recoit_une_priorite():
    g, ts = livrables.themes_du_type("analyse-ecarts-nis2")
    assert g == "Conformité & risques"
    assert "NIS2" in ts and "Guides ANSSI" in ts


def test_un_type_inconnu_ne_recoit_rien():
    assert livrables.themes_du_type("type-fantome") == (None, [])


# ── La requête de récupération porte le vocabulaire du sujet ───────────────

def test_les_mots_cles_passent_en_tete_de_la_requete():
    q = livrables.retrieval_query("pssi-ot", {})
    assert q.startswith("politique sécurité systèmes industriels"), q[:80]
    assert "IEC 62443-2-1" in q


def test_un_gabarit_non_rempli_est_ecarte_de_la_requete():
    q = livrables.retrieval_query("pssi-ot", {"secteur": "[secteur à préciser]"})
    assert "[secteur" not in q


def test_un_type_sans_mots_cles_garde_son_label():
    t = [x for x in livrables.TYPES if not x.get("mots_cles")][0]
    q = livrables.retrieval_query(t["id"], {})
    assert t["label"] in q


# ── Les sources annoncées sont les extraits réellement inclus ──────────────

def _hits(n, taille=800):
    return [{"content": ("%d-" % i) + "x" * taille, "title": "Doc %d" % i,
             "theme": "T", "doc_id": i} for i in range(n)]


def test_le_budget_coupe_et_les_retenus_le_disent():
    bloc, retenus = rag_store.build_context_retenus(_hits(8), max_chars=2000)
    assert 0 < len(retenus) < 8, "le budget de 2000 ne peut pas tenir 8 × 800"
    # Chaque retenu est réellement dans le bloc — au moins son étiquette.
    for h in retenus:
        assert h["title"] in bloc


def test_un_doublon_est_ecarte_des_retenus():
    h = _hits(2)
    h[1]["content"] = h[0]["content"]          # même début : dédupliqué
    _, retenus = rag_store.build_context_retenus(h, max_chars=50000)
    assert [x["doc_id"] for x in retenus] == [0]


def test_build_context_reste_compatible():
    assert isinstance(rag_store.build_context(_hits(2), 50000), str)
