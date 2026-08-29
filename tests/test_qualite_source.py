"""Ce que vaut une source — et ce que le classement a le droit d'en faire.

CE QUI EST ÉPROUVÉ. Les propriétés qui séparent un classement défendable d'un
oracle :

  · le reclassement CORRIGE, il ne renverse pas — une source normative très en
    dessous dans la pertinence ne remonte pas en tête ;
  · une nature INDÉTERMINÉE ne pénalise rien. C'est la propriété qui protège le
    fonds existant, entièrement non qualifié : sans elle, la mise en service de
    ce module ferait sortir des résultats la totalité de la base ;
  · la péremption dépend du SUJET, pas de la date seule ;
  · rien n'est écarté en silence — un extrait déclassé reste au dossier avec
    son motif ;
  · une déduction non concluante rend « indéterminé », jamais une supposition ;
  · le repli mémoire rend exactement les mêmes clés que la base, sinon le tri
    changerait de comportement le jour d'une panne.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import qualite_source as Q  # noqa: E402
import rag_store           # noqa: E402


def hit(titre, nature="indetermine", date=None, theme="Data center",
        doc_id=None, content=""):
    return {"doc_id": doc_id or titre, "title": titre, "theme": theme,
            "nature": nature, "date_source": date, "content": content,
            "score": 0.5}


# ── 1. Le module tient ──────────────────────────────────────────────────────

def test_le_module_se_charge_sans_faute_de_structure():
    assert Q._verifier() == []


def test_indetermine_ne_deplace_rien_dans_aucun_sens():
    """LA PROPRIÉTÉ QUI PROTÈGE LE FONDS EXISTANT. La base n'est pas
    qualifiée : ses neuf cents documents sont tous « indéterminés ». Si cette
    nature pénalisait, la mise en service du classement les ferait tous
    reculer d'un coup — et la qualification aurait dégradé exactement ce
    qu'elle prétend améliorer."""
    assert Q.NATURES["indetermine"]["deplacement"] == 0
    d, raisons = Q._deplacement(hit("x"), {})
    assert d == 0 and raisons == []


def test_un_corpus_non_qualifie_sort_dans_l_ordre_de_la_recherche():
    """La régression qui compte le plus, éprouvée sur un corpus entier : tant
    que rien n'est qualifié, le reclassement est INERTE."""
    corpus = [hit("doc %d" % i) for i in range(12)]
    classes = Q.classer(corpus, {"contractuel": True})
    assert [c["rang_final"] for c in classes] == list(range(12))
    assert [c["title"] for c in classes] == [h["title"] for h in corpus]
    assert not any(c["deplace"] for c in classes)
    assert "aucun" in Q.lecture_classement(classes).lower()


# ── 2. Le reclassement corrige, il ne renverse pas ──────────────────────────

def test_une_norme_passe_devant_une_plaquette_a_pertinence_comparable():
    classes = Q.classer([hit("plaquette", "document_commercial"),
                         hit("norme", "norme")], {})
    assert [c["title"] for c in classes] == ["norme", "plaquette"]


def test_une_norme_tres_en_dessous_ne_remonte_pas_en_tete():
    """LE RECLASSEMENT CORRIGE, IL NE RENVERSE PAS. Le déplacement est borné :
    la recherche reste maîtresse du sujet, et l'autorité départage à
    pertinence comparable. Sans cette borne, le classement d'autorité
    remplacerait le classement de pertinence — et la base rendrait la norme la
    plus autorisée quelle que soit la question posée."""
    corpus = [hit("pertinent %d" % i) for i in range(10)]
    corpus.append(hit("norme lointaine", "norme"))
    classes = Q.classer(corpus, {})
    place = next(c["rang_final"] for c in classes
                 if c["title"] == "norme lointaine")
    assert place > 0, "la norme a pris la tête sur sa seule nature"
    assert place >= 10 - Q.DEPLACEMENT_MAX


def test_le_deplacement_est_borne_dans_les_deux_sens():
    for nature in Q.NATURES:
        d, _ = Q._deplacement(hit("x", nature), {"contractuel": True})
        assert abs(d) <= Q.DEPLACEMENT_MAX, nature


def test_le_tri_est_stable_a_deplacement_egal():
    """Sans stabilité, deux extraits également qualifiés changeraient de place
    d'un appel à l'autre, et la pièce ne serait pas reproductible.

    LES TITRES SONT VOLONTAIREMENT DANS LE DÉSORDRE ALPHABÉTIQUE. Une première
    version de cette règle employait « a », « b », « c » — déjà triés — et
    survivait donc à un tri secondaire sur le titre, qui n'est pas la
    stabilité mais un autre ordre déterministe. Ce qui doit être conservé est
    l'ordre de la RECHERCHE, quel qu'il soit."""
    # LES QUATRE DOIVENT ARRIVER À ÉGALITÉ, sinon la clé principale les
    # départage et la stabilité n'est jamais sollicitée. On compose donc des
    # déplacements qui compensent exactement le rang d'entrée : chacun vise la
    # même place, et seul l'ordre d'arrivée peut les distinguer.
    corpus = [hit("zulu", "indetermine"),           # rang 0, +0
              hit("alpha", "note_projet"),          # rang 1, +1
              hit("mike", "retour_exploitation"),   # rang 2, +2
              hit("bravo", "norme")]                # rang 3, +3
    attendu = [h["title"] for h in corpus]
    assert attendu != sorted(attendu), "l'ordre d'entrée doit contredire " \
                                       "l'ordre alphabétique, sans quoi un " \
                                       "tri sur le titre passerait pour stable"
    for _ in range(5):
        classes = Q.classer(corpus, {})
        assert len({c["deplacement"] - c["rang_initial"] for c in classes}) == 1
        assert [c["title"] for c in classes] == attendu


# ── 3. La péremption dépend du sujet ───────────────────────────────────────

def test_une_source_ancienne_recule_sur_un_sujet_perissable():
    vieux = hit("note 2015", "note_projet", "2015",
                "Data center / Réglementation UE (EED, taxonomie, CSRD)")
    d, raisons = Q._deplacement(vieux, {})
    assert any(r["motif"] == "peremption" for r in raisons)
    assert d < Q.NATURES["note_projet"]["deplacement"]


def test_la_meme_source_ancienne_ne_recule_pas_sur_un_sujet_stable():
    """LA FAUTE QUE LA TABLE DE PÉREMPTION EMPÊCHE. Une fraîcheur uniforme se
    trompe dans les deux sens : elle laisse passer une note périmée sur un
    texte modifié chaque année, et déclasse une note sur le transfert
    thermique, dont le contenu n'a pas bougé."""
    stable = hit("note 2015", "note_projet", "2015",
                 "Data center / Thermique & refroidissement")
    d, raisons = Q._deplacement(stable, {})
    assert not any(r["motif"] == "peremption" for r in raisons)
    assert d == Q.NATURES["note_projet"]["deplacement"]


def test_un_theme_sans_regle_de_peremption_ne_deplace_rien():
    """Ne pas savoir à quelle vitesse un sujet se périme n'autorise pas à
    supposer qu'il se périme vite."""
    assert Q.PEREMPTION_DEFAUT["recul"] == 0
    d, raisons = Q._deplacement(
        hit("x", "note_projet", "1998", "Sujet non cartographié"), {})
    assert not any(r["motif"] == "peremption" for r in raisons)


def test_une_source_sans_date_n_est_pas_traitee_comme_ancienne():
    """Une date absente n'est pas une date lointaine : c'est une inconnue, et
    la traiter comme un défaut punirait un document au motif qu'on ne sait
    rien de lui."""
    d, raisons = Q._deplacement(
        hit("x", "norme", None,
            "Data center / Réglementation UE (EED, taxonomie, CSRD)"), {})
    assert not any(r["motif"] == "peremption" for r in raisons)


def test_les_motifs_de_peremption_designent_des_themes_reels():
    """UN INTITULÉ RECOPIÉ DE TRAVERS NE DÉCLENCHERAIT RIEN, sans erreur — et
    personne ne s'en apercevrait. C'est une règle d'essai et non un contrôle de
    chargement : le module de qualification est importé PAR la base, et lui
    demander ses thèmes au chargement fermerait un cycle d'imports."""
    connus = rag_store.THEMES
    for regle in Q.PEREMPTION:
        for m in regle["motifs"]:
            assert any(m.lower() in t.lower() for t in connus), (
                "%s : le motif « %s » ne reconnaît aucun thème de la base"
                % (regle["cle"], m))


# ── 4. Le caractère de la pièce ────────────────────────────────────────────

def test_une_source_commerciale_recule_plus_sur_une_piece_contractuelle():
    plaquette = hit("plaquette", "document_commercial")
    libre, _ = Q._deplacement(plaquette, {"contractuel": False})
    gelee, _ = Q._deplacement(plaquette, {"contractuel": True})
    assert gelee < libre


def test_une_norme_ne_recule_pas_sur_une_piece_contractuelle():
    """Le recul contractuel vise l'origine commerciale, pas l'ancienneté ni
    l'autorité : une norme n'a aucune raison d'y perdre des rangs."""
    d1, _ = Q._deplacement(hit("n", "norme"), {"contractuel": False})
    d2, _ = Q._deplacement(hit("n", "norme"), {"contractuel": True})
    assert d1 == d2


def test_un_document_qui_nomme_le_projet_remonte():
    d0, _ = Q._deplacement(hit("Note générale"), {"client": "ACME"})
    d1, _ = Q._deplacement(hit("Note ACME lot CFO"), {"client": "ACME"})
    assert d1 > d0


# ── 5. La déduction ne suppose jamais ──────────────────────────────────────

@pytest.mark.parametrize("titre,attendu", [
    ("NF EN 50600-2-3 — contrôle des ambiances", "norme"),
    ("Décret n° 2023-1211 modifiant la nomenclature", "reglementaire"),
    ("Livre blanc — bâtir des applis IA", "livre_blanc_fournisseur"),
    ("CCTP lot courants forts", "note_projet"),
    ("Retour d'expérience mise en service", "retour_exploitation"),
    ("Brochure gamme 2025", "document_commercial"),
])
def test_la_nature_se_devine_au_titre(titre, attendu):
    r = Q.deviner(titre, titre + ".pdf", "")
    assert r["nature"] == attendu, (titre, r["nature"])
    assert r["confiance"] == "titre"


def test_un_titre_muet_rend_indetermine_et_non_une_supposition():
    r = Q.deviner("Document", "doc.pdf", "Un texte quelconque, sans indice.")
    assert r["nature"] == "indetermine"
    assert r["confiance"] == "aucune"


def test_l_ordre_de_deduction_empeche_de_classer_un_livre_blanc_en_norme():
    """UN TEXTE RÉGLEMENTAIRE CITE DES NORMES ; UN LIVRE BLANC CITE LES DEUX.
    Chercher « norme » en premier classerait la moitié de la base en norme, et
    l'autorité accordée ensuite ferait remonter des plaquettes devant des
    décrets."""
    r = Q.deviner("Livre blanc — conformité ISO 27001 et NF EN 50600",
                  "wp.pdf", "")
    assert r["nature"] == "livre_blanc_fournisseur"


def test_une_annee_isolee_dans_le_corps_ne_fait_pas_une_date():
    """Un document technique cite des années par dizaines — millésimes de
    normes, années de référence. En retenir une au hasard donnerait une date
    fausse, et une date fausse déplace un document sans motif."""
    r = Q.deviner("Note", "n.pdf", "Selon la norme de 2005 et le décret de "
                                   "2011, la valeur de 1998 reste retenue.")
    assert r["date_source"] is None
    avec = Q.deviner("Note", "n.pdf", "© 2024 — édition révisée. Selon la "
                                      "norme de 2005…")
    assert avec["date_source"] == "2024"


def test_une_annee_future_n_est_pas_une_date_de_publication():
    r = Q.deviner("Référence 2199 du catalogue", "x.pdf", "")
    assert r["date_source"] is None


# ── 6. Les divergences de valeurs ──────────────────────────────────────────

def test_deux_sources_qui_donnent_deux_valeurs_sont_signalees():
    d = Q.divergences([
        {"doc_id": "a", "title": "A", "content": "La cuve fait 120 m³."},
        {"doc_id": "b", "title": "B", "content": "Rétention de 185 m³."}])
    assert d and d["divergences"][0]["unite"] == "m³"


def test_un_meme_document_qui_donne_une_plage_n_est_pas_en_contradiction():
    """Un document qui donne deux valeurs donne une plage, un avant et un
    après, une série. C'est entre SOURCES que l'écart interroge."""
    assert Q.divergences([{"doc_id": "a", "title": "A",
                           "content": "entre 50 m³ et 90 m³"}]) is None


def test_l_ecart_retenu_entre_deux_sources_est_le_plus_faible():
    """L'ÉCART LE PLUS PARLANT EST CELUI DES VALEURS LES PLUS PROCHES. Deux
    documents qui donnent chacun une plage ne se contredisent pas si leurs
    plages se recouvrent ; retenir l'écart maximal ferait crier à la
    contradiction chaque fois qu'une source donne un minimum et un maximum,
    et les signalements cesseraient d'être lus."""
    assert Q.divergences([
        {"doc_id": "a", "title": "A", "content": "de 100 m³ à 200 m³"},
        {"doc_id": "b", "title": "B", "content": "de 190 m³ à 300 m³"}]) is None
    d = Q.divergences([
        {"doc_id": "a", "title": "A", "content": "de 100 m³ à 120 m³"},
        {"doc_id": "b", "title": "B", "content": "de 250 m³ à 300 m³"}])
    assert d and d["divergences"][0]["unite"] == "m³"


def test_un_arrondi_de_redaction_n_est_pas_une_divergence():
    assert Q.divergences([
        {"doc_id": "a", "title": "A", "content": "3 000 kW"},
        {"doc_id": "b", "title": "B", "content": "3 050 kW"}]) is None


def test_deux_unites_ecrites_autrement_sont_bien_comparees():
    """« m3 » et « m³ » sont la même unité. Sans normalisation, deux documents
    qui l'écrivent différemment ne seraient jamais comparés, et la divergence
    resterait invisible."""
    d = Q.divergences([{"doc_id": "a", "title": "A", "content": "120 m3"},
                       {"doc_id": "b", "title": "B", "content": "185 m³"}])
    assert d and d["divergences"][0]["unite"] == "m³"


# ── 7. La base rend ce que le classement attend ────────────────────────────

def test_le_repli_memoire_rend_les_memes_cles_que_la_base():
    """Sinon le tri changerait de comportement le jour d'une panne,
    c'est-à-dire le jour où personne ne le vérifie."""
    m = rag_store.MemoryRagStore()
    m.ingest_bytes("NF EN 50600 climatisation 2019.txt",
                   ("Norme NF EN 50600 pour la climatisation. " * 40).encode())
    h = m.search("climatisation", k=1)
    assert h and {"nature", "date_source"} <= set(h[0])
    assert h[0]["nature"] == "norme" and h[0]["date_source"] == "2019"


def test_la_nature_se_corrige_et_la_correction_tient():
    m = rag_store.MemoryRagStore()
    d = m.ingest_bytes("Guide complet.txt", ("Un guide. " * 120).encode())
    m.set_nature(d["id"], "note_projet", "2021")
    h = m.search("guide", k=1)[0]
    assert h["nature"] == "note_projet" and h["date_source"] == "2021"


@pytest.mark.parametrize("nature,date", [("inventee", None),
                                         ("norme", "vers 2020"),
                                         ("norme", "21")])
def test_une_qualification_invalide_est_refusee(nature, date):
    """Une nature inventée serait neutre au classement mais s'afficherait dans
    la console comme une qualification faite : ni classée, ni signalée comme à
    classer, c'est le pire des deux états."""
    m = rag_store.MemoryRagStore()
    d = m.ingest_bytes("x.txt", ("texte " * 200).encode())
    with pytest.raises(rag_store.RagError):
        m.set_nature(d["id"], nature, date)


def test_la_liste_de_documents_est_bornee_mais_paginable():
    """LE DÉFAUT CONSTATÉ EN EXPLOITATION : le plafond était figé à 500 et
    muet. Sur une base plus grande, la console affichait un compteur calculé
    sur ce qu'elle avait reçu à côté d'un tableau de bord compté en base — et
    ses actions en lot ne portaient que sur la partie visible."""
    m = rag_store.MemoryRagStore()
    for i in range(8):
        m.ingest_bytes("doc%d.txt" % i, (("texte %d " % i) * 200).encode())
    assert len(m.list_documents(limit=3)) == 3
    premiers = [d["id"] for d in m.list_documents(limit=3)]
    suivants = [d["id"] for d in m.list_documents(limit=3, offset=3)]
    assert not set(premiers) & set(suivants)
    assert len(m.list_documents()) == 8
