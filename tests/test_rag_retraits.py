"""Ce que la base ne collecte plus — et ce qu'elle en fait.

DEUX FAMILLES RETIRÉES, POUR DEUX RAISONS DIFFÉRENTES :

  · les TABLEAUX CSV, parce que le découpage les détruit. Un fragment de neuf
    cents caractères perd la ligne d'en-tête dès le deuxième morceau, et une
    suite de valeurs sans le nom de ses colonnes ne répond à aucune question ;
  · les BULLETINS DE VEILLE, parce qu'ils ont leur propre page et leur propre
    magasin. La base n'en recevait qu'une copie, qui occupait la majorité du
    fonds.

CE QUI EST ÉPROUVÉ :

  · la collecte s'arrête — au dépôt comme à la veille automatique ;
  · les feuilles de calcul restent lisibles AILLEURS : c'est la base
    documentaire qui les écarte, pas la plateforme ;
  · le résidu se COMPTE, il ne se cache pas. Un document invisible et présent
    est un fantôme que personne ne supprimera jamais ;
  · la suppression SIMULE par défaut, et ne vise que ce qui est déclaré
    retiré : une route qui accepterait « pdf » viderait le fonds avec la même
    syntaxe et sans plus d'avertissement ;
  · le repli mémoire compte et supprime comme la base.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import rag_store  # noqa: E402

from conftest import ORIGINE  # noqa: E402


def base():
    m = rag_store.MemoryRagStore()
    m.ingest_bytes("note technique.txt", ("texte utile " * 200).encode())
    m.ingest_bytes("veille-certfr-a.md", ("# bulletin " * 200).encode(),
                   title="[CERT-FR] Vulnérabilité", theme="Veille")
    # Un bulletin RECLASSÉ À LA MAIN : la console l'écarte du tableau sur son
    # titre, et le seul thème ne suffirait pas à le retrouver.
    m.ingest_bytes("autre.md", ("bulletin déplacé " * 200).encode(),
                   title="[CERT-FR] Reclassé", theme="Général")
    # Un CSV déjà en base, du temps où le format était collecté.
    d = m.ingest_bytes("tableau.txt", ("a;b;c;1,2;3,4 " * 200).encode())
    m._docs[d["id"]]["ext"] = "csv"
    return m


# ── 1. La collecte s'arrête ────────────────────────────────────────────────

def test_le_csv_n_est_plus_deposable():
    assert "csv" not in rag_store.ALLOWED_EXT
    assert "csv" not in rag_store.formats_deposables()
    with pytest.raises(rag_store.RagError):
        rag_store.MemoryRagStore().ingest_bytes("t.csv", b"a;b;c" * 300)


def test_le_selecteur_de_fichier_suit_le_serveur():
    """La liste des formats est DÉRIVÉE, jamais recopiée : retirer un format
    d'un seul endroit doit suffire, sinon le sélecteur continue de proposer un
    dépôt voué au refus — un refus survenu avant l'appel, donc sans
    explication possible."""
    for fichier in ("admin-base-connaissance.html",):
        with open(os.path.join(ICI, fichier), encoding="utf-8") as f:
            page = f.read()
        assert ".csv" not in page.split("<script")[0], (
            "%s propose encore le dépôt de .csv avant même la réponse du "
            "serveur" % fichier)


def test_la_veille_n_alimente_plus_la_base():
    import automation
    assert automation.VEILLE_VERS_RAG is False


def test_la_veille_continue_de_publier_sur_sa_page():
    """CE QUI N'EST PAS TOUCHÉ, et c'est l'essentiel : les bulletins ont leur
    propre magasin et leur propre page. Seule la COPIE vers la base
    documentaire s'arrête."""
    import automation
    import inspect
    src = inspect.getsource(automation.veille_refresh)
    # L'ajout au magasin de veille reste inconditionnel ; c'est l'ingestion
    # dans le RAG, et elle seule, qui est placée derrière le drapeau.
    i_publie = src.index("_state.veille_add(item)")
    i_garde = src.index("VEILLE_VERS_RAG")
    assert i_publie < i_garde, ("la publication sur la page de veille est "
                                "passée derrière le drapeau du RAG")


def test_les_feuilles_de_calcul_restent_lues_ailleurs():
    """C'est la base DOCUMENTAIRE qui écarte le CSV, pas la plateforme.
    L'analyse des pièces de marché et les contrats les traitent entiers, et
    doivent continuer de le faire."""
    import antivirus
    assert "csv" in antivirus.EXTENSIONS, (
        "le CSV a été retiré de la porte de sécurité PARTAGÉE : l'analyse des "
        "pièces de marché et les contrats le refuseraient aussi")
    assert rag_store.extract_text("csv", "a;b;c\n1;2;3".encode()), (
        "l'extracteur ne sait plus lire un CSV, alors que d'autres chemins "
        "s'en servent")


# ── 2. Le résidu se compte, il ne se cache pas ─────────────────────────────

def test_le_residu_est_compte_et_non_masque():
    """UN DOCUMENT INVISIBLE ET PRÉSENT EST UN FANTÔME : il occupe la place,
    pèse sur la recherche, et personne ne le supprimera jamais puisque aucun
    écran ne le montre."""
    r = base().stats()["residus"]
    assert r["csv"] == 1
    assert r["veille"] == 2, "le bulletin reclassé à la main n'est pas compté"


def test_une_base_nettoyee_ne_declare_aucun_residu():
    m = rag_store.MemoryRagStore()
    m.ingest_bytes("note.txt", ("texte " * 300).encode())
    assert m.stats()["residus"] == {}


# ── 3. La suppression ──────────────────────────────────────────────────────

def test_la_suppression_simule_par_defaut():
    """Un appel écrit de travers COMPTE au lieu de détruire."""
    m = base()
    r = m.supprimer_extension("csv")
    assert r["simule"] is True and r["documents"] == 1
    assert m.stats()["residus"]["csv"] == 1, "la simulation a supprimé"


def test_la_suppression_confirmee_retire_tout_le_document():
    m = base()
    avant = m.stats()["documents"]
    r = m.supprimer_veille(simuler=False)
    assert r["documents"] == 2
    assert m.stats()["documents"] == avant - 2
    assert "veille" not in m.stats()["residus"]
    # Fragments et fichier d'origine partent avec le document.
    assert not any("[CERT-FR]" in (d.get("title") or "")
                   for d in m.list_documents())


def test_la_suppression_par_extension_ne_vise_que_le_retire():
    """UNE ROUTE QUI ACCEPTERAIT N'IMPORTE QUELLE EXTENSION viderait le fonds
    d'un mot : « pdf » supprimerait l'essentiel de la base, avec la même
    syntaxe et sans plus d'avertissement."""
    m = base()
    for interdit in ("pdf", "docx", "txt", "md", ""):
        with pytest.raises(rag_store.RagError):
            m.supprimer_extension(interdit, simuler=False)
    assert m.stats()["documents"] == 4, "un format non retiré a été supprimé"


def test_le_bulletin_reclasse_est_supprime_comme_les_autres():
    """DEUX CRITÈRES POUR LE CACHER, UN SEUL POUR LE SUPPRIMER : c'est ainsi
    qu'on fabrique un fantôme. La console écarte du tableau ce qui porte le
    thème OU le préfixe de titre ; la suppression doit employer le même
    critère, sinon le reclassé survit sans jamais se montrer."""
    m = base()
    m.supprimer_veille(simuler=False)
    restants = [d["title"] for d in m.list_documents()]
    assert not [t for t in restants if t.startswith(rag_store.PREFIXE_VEILLE)]


def test_le_repli_memoire_et_la_base_declarent_les_memes_cles():
    """Un repli qui compte autrement ferait afficher deux états différents
    pour la même situation, selon que la base répond ou non — et c'est le jour
    où elle ne répond pas que personne ne le vérifie."""
    assert "residus" in rag_store.MemoryRagStore().stats()
    import inspect
    src = inspect.getsource(rag_store.PostgresRagStore.stats)
    assert '"residus": residus' in src


# ── 4. La route : simulation, confirmation, journal ────────────────────────

def test_un_visiteur_ordinaire_ne_supprime_rien(connecte):
    r = connecte.post("/api/admin/rag/retirer",
                             json={"famille": "csv", "confirmer": True},
                             headers=ORIGINE)
    assert r.status_code in (401, 403)


def test_la_route_simule_sans_confirmation(admin):
    j = admin.post("/api/admin/rag/retirer",
                          json={"famille": "veille"},
                          headers=ORIGINE).get_json()
    assert j["ok"] is True and j["simule"] is True


def test_une_famille_inconnue_est_refusee_et_dit_lesquelles(admin):
    r = admin.post("/api/admin/rag/retirer",
                          json={"famille": "pdf", "confirmer": True},
                          headers=ORIGINE)
    assert r.status_code == 400
    j = r.get_json()
    assert j["error"] == "famille_inconnue"
    assert "veille" in j["familles"] and "pdf" not in j["familles"]
