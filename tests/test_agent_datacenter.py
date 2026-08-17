"""L'agent data center : segmentation, récupération filtrée, refus, contrôle.

La propriété qui fait la valeur de cet agent n'est pas de savoir rédiger — tout
modèle sait rédiger. C'est de savoir REFUSER : quand le corpus ne couvre pas la
demande, il lève au lieu de produire. Un générateur qui répond toujours produit,
sur un corpus vide, un document plausible et faux, c'est-à-dire exactement ce
qu'on ne peut pas remettre à un client.

Les tests marqués « défaut corrigé » verrouillent des corrections apportées à
l'intégration : sans eux, rien n'empêcherait de les réintroduire, et chacune
échouait en silence.
"""
import json
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import agent_datacenter as A  # noqa: E402


def faux_embed(dim=8):
    """Vectorisation déterministe et sans réseau.

    On projette le texte sur quelques termes-clés : deux textes qui parlent du
    même sujet obtiennent des vecteurs proches, ce qui suffit à éprouver le
    seuil de similarité et le refus — sans dépendre d'un service externe, donc
    sans qu'une panne de réseau fasse échouer la recette.
    """
    axes = ["pue", "eau", "chaleur", "carbone", "raccordement", "eed", "gpu", "cooling"]

    def embed(textes):
        out = []
        for t in textes:
            p = A._normalise(t)
            v = [float(p.count(a)) for a in axes[:dim]]
            out.append(v if any(v) else [1.0] + [0.0] * (dim - 1))
        return out
    return embed


DOC = """Le site présente un PUE annuel de 1,42 pour une charge IT de 1 850 kW.

La tour aerorefrigerante consomme 12 400 m3 d'eau par an, soit un WUE de 0,77.

Le raccordement prévoit une puissance souscrite de 4 MW avec onduleur redondant.

La chaleur fatale alimenterait un reseau de chaleur voisin via pompe a chaleur.

Le rapportage EED article 12 impose une declaration annuelle au registre europeen."""


# ── 1. Défauts corrigés à l'intégration ────────────────────────────────────

def test_apostrophe_typographique_ne_casse_pas_le_controle():
    """DÉFAUT CORRIGÉ. Les gabarits écrivent « donnees d'entree » avec
    l'apostrophe droite ; un modèle rédigeant en français écrit « données
    d'entrée » avec la typographique. Les deux chaînes normalisées ne se
    ressemblaient pas : la section était déclarée manquante alors qu'elle était
    là. Conséquence en chaîne — une régénération payée pour rien, puis un
    livrable correct marqué non conforme, puis un journal de transparence qui
    enregistre un défaut qui n'a jamais existé.
    """
    section = "Perimetre et donnees d'entree"
    redige = "## Périmètre et données d’entrée\n\nLe site consomme 11 388 MWh [S1]."
    assert A._normalise(section)[:28] in A._normalise(redige)
    assert A.deterministic_check(redige, [section], ["S1"]) == []


def test_tirets_et_espaces_multiples_aussi():
    """Même famille : un modèle remplace « - » par « – » et double les espaces."""
    section = "Actions a court terme, moins de douze mois"
    redige = "## Actions a court  terme, moins de douze mois\n\n3 actions [S1]."
    assert A.deterministic_check(redige, [section], ["S1"]) == []


def test_lot_de_vecteurs_incomplet_est_refuse():
    """DÉFAUT CORRIGÉ. zip s'arrête au plus court : un lot incomplet laissait
    des passages sans vecteur. Indexés, donc comptés — mais cosine renvoyait
    0.0 pour eux, donc introuvables. Le corpus paraissait complet et la
    récupération ne les proposait jamais.
    """
    idx = A.CorpusIndex()
    with pytest.raises(A.EmbeddingIndisponible):
        idx.add_document(DOC, "doc.pdf", "2026-01",
                         lambda ts: [[1.0] * 8 for _ in ts[:-1]])
    assert idx.passages == [], "des passages ont été indexés malgré le refus"


def test_vecteur_vide_est_refuse():
    idx = A.CorpusIndex()
    with pytest.raises(A.EmbeddingIndisponible):
        idx.add_document(DOC, "doc.pdf", "2026-01", lambda ts: [[] for _ in ts])
    assert idx.passages == []


def test_theme_retire_du_referentiel_ne_fait_pas_tomber_la_generation():
    """DÉFAUT CORRIGÉ. Un index construit sous une version antérieure du
    vocabulaire porte des thèmes disparus. L'indexation directe THEMES[theme]
    levait une KeyError et faisait échouer la génération entière — alors que le
    passage reste parfaitement citable.
    """
    p = A.Passage(id="x", source="vieux.pdf", theme="theme_disparu", theme_score=3,
                  published_on="2024-01", text="Un extrait encore valable.")
    contexte, sources = A.build_context([(p, 0.9)])
    assert "vieux.pdf" in contexte
    assert "theme_disparu" in contexte
    assert sources[0]["marker"] == "S1"


def test_critique_injoignable_nest_pas_un_livrable_mauvais():
    """DÉFAUT CORRIGÉ. Une panne du service d'évaluation produisait un score de
    zéro, donc « non conforme », donc deux régénérations inutiles, et un
    journal affirmant un défaut de qualité jamais constaté. Le doute doit se
    lire comme un doute.
    """
    idx = A.CorpusIndex()
    idx.add_document(DOC, "doc.pdf", "2026-01", faux_embed())

    appels = {"n": 0}

    def complete(system, user, temperature=0.2):
        appels["n"] += 1
        if "evaluez" in system.lower():
            raise RuntimeError("service d'évaluation injoignable")
        return ("## Perimetre et donnees d'entree\nPUE 1,42 [S1].\n"
                "## Situation de reference chiffree\n12 400 m3 [S1].\n"
                "## Ecarts au regard des exigences applicables\n4 MW [S1].\n"
                "## Risques et points de vigilance\n1 risque [S1].\n"
                "## Conclusion et suites recommandees\n3 suites [S1].\n")

    # Seuil abaissé : ce test porte sur le CRITIQUE, pas sur la similarité.
    # Le laisser à sa valeur réelle le ferait échouer sur un refus de corpus,
    # c'est-à-dire pour une raison qui n'est pas celle qu'on éprouve.
    agent = A.DataCenterAgent(idx, faux_embed(), complete,
                              journal_path=os.devnull, min_passages=1,
                              threshold=0.0)
    res = agent.generate("conseils_specifiques", "diagnostic",
                         "Diagnostic energie et carbone du site de Marseille.")
    assert res["controle"]["concluant"] is False
    # Une seule tentative : régénérer n'aurait pas réparé le critique.
    assert res["tentatives"] == 1
    assert res["livrable"], "le brouillon doit être rendu, pas jeté"


# ── 2. Le refus, qui est la propriété centrale ─────────────────────────────

def test_refus_quand_le_corpus_ne_couvre_pas():
    idx = A.CorpusIndex()
    agent = A.DataCenterAgent(idx, faux_embed(), lambda s, u, t=0.2: "",
                              journal_path=os.devnull)
    with pytest.raises(A.InsufficientContext):
        agent.generate("transformation", "diagnostic",
                       "Diagnostic complet du site, energie et carbone.")


def test_page_inconnue_est_refusee():
    idx = A.CorpusIndex()
    with pytest.raises(ValueError):
        idx.search([1.0] * 8, "page_qui_nexiste_pas")


def test_passage_non_classe_nest_jamais_indexe():
    """Un passage que le vocabulaire ne reconnaît pas ne peut pas contaminer un
    livrable : il n'entre pas dans le corpus."""
    idx = A.CorpusIndex()
    n = idx.add_document("Le chat dort sur le tapis. Il fait beau aujourd'hui.",
                         "hors-sujet.txt", "2026-01", faux_embed())
    assert n == 0
    assert idx.passages == []


def test_une_page_ne_voit_que_ses_themes():
    idx = A.CorpusIndex()
    idx.add_document("La consommation d'eau de la tour aerorefrigerante atteint "
                     "12 400 m3, soit un WUE de 0,77 L/kWh.",
                     "eau.pdf", "2026-01", faux_embed())
    assert idx.passages and idx.passages[0].theme == "eau"
    v = faux_embed()(["consommation d'eau WUE"])[0]
    # « eau » appartient à conseils_bas_carbone mais pas à transformation.
    assert idx.search(v, "conseils_bas_carbone", threshold=0.0)
    assert idx.search(v, "transformation", threshold=0.0) == []


# ── 3. Traçabilité et journal ──────────────────────────────────────────────

def test_reference_inventee_est_detectee():
    """Le contrôle qui protège du plus grave : une citation vers une source qui
    n'existe pas donne au lecteur l'illusion d'une vérification possible."""
    d = A.deterministic_check("## Titre\nAffirmation [S9], 12 %.", ["Titre"], ["S1"])
    assert any("inexistantes" in x for x in d)


def test_livrable_sans_source_ni_chiffre_est_sanctionne():
    d = A.deterministic_check("## Titre\nUne affirmation sans rien.", ["Titre"], ["S1"])
    assert any("Aucune reference" in x for x in d)
    assert any("Aucune valeur chiffree" in x for x in d)


def test_journal_porte_les_empreintes_et_les_sources(tmp_path):
    """Le journal fonde la transparence de l'article 50. Il doit permettre de
    rejouer une génération : quelle demande, quel corpus, quelles sources."""
    idx = A.CorpusIndex()
    idx.add_document(DOC, "doc.pdf", "2026-01", faux_embed())
    jp = str(tmp_path / "journal.jsonl")
    agent = A.DataCenterAgent(
        idx, faux_embed(),
        lambda s, u, t=0.2: ('{"exactitude_reglementaire":5,"chiffrage":5,'
                             '"tracabilite":5,"absence_affirmation_non_sourcee":5,'
                             '"defauts":[]}' if "evaluez" in s.lower() else
                             "## Perimetre et donnees d'entree\nPUE 1,42 [S1].\n"
                             "## Situation de reference chiffree\n12 400 m3 [S1].\n"
                             "## Ecarts au regard des exigences applicables\n4 MW [S1].\n"
                             "## Risques et points de vigilance\n1 point [S1].\n"
                             "## Conclusion et suites recommandees\n3 suites [S1].\n"),
        journal_path=jp, min_passages=1, threshold=0.0)
    res = agent.generate("conseils_specifiques", "diagnostic",
                         "Diagnostic energie et carbone du site de Marseille.")
    assert res["controle"]["conforme"] is True
    lignes = [json.loads(x) for x in open(jp, encoding="utf-8") if x.strip()]
    assert len(lignes) == 1
    e = lignes[0]
    assert e["corpus_version"] == A.CORPUS_VERSION
    assert len(e["empreinte_demande"]) == 16
    assert len(e["empreinte_livrable"]) == 16
    assert e["sources"] and e["sources"][0]["marker"] == "S1"
    assert e["controle_concluant"] is True


def test_index_survit_a_un_aller_retour_disque(tmp_path):
    chemin = str(tmp_path / "corpus.json")
    a = A.CorpusIndex(chemin)
    a.add_document(DOC, "doc.pdf", "2026-01", faux_embed())
    a.save()
    b = A.CorpusIndex(chemin)
    assert len(b.passages) == len(a.passages)
    assert b.passages[0].embedding == a.passages[0].embedding


def test_ecriture_atomique_ne_laisse_pas_de_fichier_tronque(tmp_path):
    """DÉFAUT CORRIGÉ. Une coupure au milieu du json.dump laissait un fichier
    illisible, que le prochain chargement refusait : le corpus entier
    disparaissait au redémarrage suivant."""
    chemin = str(tmp_path / "corpus.json")
    idx = A.CorpusIndex(chemin)
    idx.add_document(DOC, "doc.pdf", "2026-01", faux_embed())
    idx.save()
    assert not os.path.exists(chemin + ".tmp"), "fichier provisoire laissé en place"
    json.load(open(chemin, encoding="utf-8"))       # ne doit pas lever


# ── 4. Intégration au site ─────────────────────────────────────────────────

def test_le_blueprint_est_ferme_par_defaut_sur_ce_site():
    """Le module d'origine exposait /generer sans aucun contrôle : il faisait
    travailler un modèle et livrait une étude à qui la demandait. Sur ce site,
    app.py passe le verrou des comptes."""
    import app as appmod
    c = appmod.app.test_client()
    r = c.post("/api/datacenter/agent/generer",
               json={"page": "transformation", "livrable": "diagnostic",
                     "demande": "Un diagnostic complet du site de Marseille."},
               headers={"Origin": "http://localhost", "Referer": "http://localhost/"})
    assert r.status_code in (401, 403), f"route ouverte : {r.status_code}"


def test_aucune_collision_de_route():
    """Le site expose déjà un moteur de calcul sous /api/datacenter. Deux règles
    Flask sur la même URL ne lèvent pas d'erreur : la première gagne, l'autre
    est silencieusement morte."""
    import app as appmod
    urls = [str(r) for r in appmod.app.url_map.iter_rules() if "datacenter" in str(r)]
    assert len(urls) == len(set(urls)), "URL en double : " + str(
        sorted(u for u in urls if urls.count(u) > 1))
    assert "/api/datacenter/etude" in urls          # moteur de calcul
    assert "/api/datacenter/agent/generer" in urls  # agent documentaire


# ── 5. LA PROVENANCE DES QUANTITÉS ─────────────────────────────────────────
#
# DÉFAUT CORRIGÉ. Le prompt système ORDONNE au modèle de n'employer que les
# extraits et de ne jamais inventer une valeur. Rien ne le VÉRIFIAIT : un
# livrable pouvait citer [S1] correctement — le contrôle des marqueurs passait
# — et poser à côté un chiffre absent du corpus. C'est le défaut le plus
# coûteux qu'un livrable puisse porter, parce qu'il a l'apparence exacte du
# travail sourcé et qu'il tombe à la première vérification du client.
#
# Le contrôle ne vise que les QUANTITÉS : un nombre portant une unité, ou un
# nombre à décimales. Un identifiant — « directive 2023/1791 », « IEC 62443 »
# — n'est pas une quantité et ne se source pas comme un débit d'eau.

_CTX = (
    "[S1] Le site présente un PUE annuel de 1,42 pour une charge IT de 1 850 kW.\n"
    "[S2] La tour consomme 12 400 m3 d'eau par an, soit un WUE de 0,77.\n"
    "[S3] Le raccordement prévoit une puissance souscrite de 4 MW.\n"
    "[S4] Le rapportage EED article 12 impose une déclaration annuelle."
)
_BRIEF = "Diagnostic du site de Marseille, 4,2 MW souscrits."


def test_les_quantites_des_extraits_passent():
    assert A.chiffres_hors_source(
        "PUE de 1,42 [S1], appoint 12 400 m3/an [S2], WUE 0,77.", _CTX, _BRIEF) == []


def test_un_arrondi_nest_pas_une_invention():
    """Le modèle qui écrit « 1,4 » pour un extrait à « 1,42 » n'invente rien.
    Le lui reprocher rendrait le contrôle inutilisable, donc désactivé."""
    assert A.chiffres_hors_source("PUE d'environ 1,4 [S1].", _CTX, _BRIEF) == []


def test_un_chiffre_de_la_demande_client_est_une_source_legitime():
    assert A.chiffres_hors_source("Le site souscrit 4,2 MW [S3].", _CTX, _BRIEF) == []


def test_LE_POINT_QUI_DECIDE_un_chiffre_invente_est_signale():
    d = A.chiffres_hors_source(
        "PUE 1,42 [S1] et une consommation de 38 900 m3/an [S2].", _CTX, _BRIEF)
    assert d == [38900.0]


def test_un_pourcentage_invente_est_signale():
    """La frontière de mot échouait après « % », « € » et « °C » : ces
    unités-là ne sont pas des caractères de mot, et tout pourcentage inventé
    passait le contrôle. Mesuré, puis corrigé."""
    assert A.chiffres_hors_source(
        "PUE 1,42 [S1], soit 27 % au-dessus du repère.", _CTX, _BRIEF) == [27.0]
    assert A.chiffres_hors_source("Budget de 4,7 M€ [S1].", _CTX, _BRIEF) == [4.7]
    assert A.chiffres_hors_source("Soufflage à 24 °C [S1].", _CTX, _BRIEF) == [24.0]


def test_un_identifiant_normatif_nest_pas_une_quantite():
    assert A.chiffres_hors_source(
        "Directive 2023/1791, IEC 62443, EN 50600-4-2 [S4].", _CTX, _BRIEF) == []


def test_un_denombrement_de_redaction_nest_pas_une_mesure():
    assert A.chiffres_hors_source(
        "3 suites [S1], 1 risque majeur [S2].", _CTX, _BRIEF) == []


def test_une_valeur_en_fin_de_phrase_est_bien_lue():
    """La garde en aval écartait « 0,77. » — donc la moitié des extraits — et
    le contrôle signalait alors comme inventées des valeurs bel et bien
    sourcées."""
    assert 0.77 in A._quantites("soit un WUE de 0,77.")


def test_le_controle_deterministe_porte_le_defaut():
    d = A.deterministic_check(
        "## Perimetre et donnees d'entree\nConsommation 38 900 m3/an [S1].\n",
        ["Perimetre et donnees d'entree"], ["S1"], _CTX, _BRIEF)
    assert any("Quantites absentes des extraits" in x for x in d)
    assert any("38" in x for x in d)


def test_sans_contexte_le_controle_ne_sanctionne_rien():
    """Sans extraits fournis, toute quantité paraîtrait inventée : un appelant
    qui ne les passe pas obtiendrait un livrable rejeté pour une raison
    fausse."""
    d = A.deterministic_check(
        "## Perimetre et donnees d'entree\nConsommation 38 900 m3/an [S1].\n",
        ["Perimetre et donnees d'entree"], ["S1"])
    assert not any("Quantites absentes" in x for x in d)
