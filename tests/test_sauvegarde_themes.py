"""La sauvegarde doit rendre le CHEMIN COMPLET du thème, pas son début.

CE QUI EST EN JEU. La base de connaissance range les documents dans une
arborescence : « Engineering / Projet OWFarm / Fire fighting / Watermist ».
Ce chemin n'est pas décoratif — c'est lui que le générateur de livrables
interroge pour aller chercher les bonnes sources, et lui que l'administrateur
lit pour savoir ce qu'il détient.

Or le thème est écrit dans le magasin AVEC UNE COUPE À 80 CARACTÈRES. Le plus
long chemin déclaré aujourd'hui en fait 55 : rien n'est coupé. Mais une coupe
n'avertit pas. Le jour où un niveau de plus est ajouté — un dossier « Essais »
sous Watermist, une révision sous Rules — le chemin est tranché en son milieu,
et il en sort un thème qui N'EXISTE PAS dans le vocabulaire :

    « Engineering / Projet OWFarm / Fire fighting / Watermist / Essais de qua »

Le document est alors rangé dans un dossier fantôme. Il ne remonte plus dans sa
famille, le générateur ne le trouve plus, et RIEN NE LE DIT : ni erreur, ni
message, ni compteur. On ne s'en aperçoit qu'en constatant qu'un livrable ne
cite plus une pièce qu'on sait posséder — des semaines plus tard.

CE QUE CES TESTS VERROUILLENT, DONC, EST MOINS LA SAUVEGARDE D'AUJOURD'HUI QUE
CELLE DE DEMAIN : que tout thème déclaré tienne dans la place prévue, avec une
marge annoncée, et qu'un aller-retour sauvegarde → restauration rende le chemin
identique au caractère près.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import rag_store as R  # noqa: E402

# La coupe appliquée à l'écriture du thème, dans les deux magasins. Nommée ici
# pour que le test dise CE QU'IL VÉRIFIE et non un nombre nu.
COUPE = 80

PROFOND = "Engineering / Projet OWFarm / Fire fighting / Watermist"


def magasin(tmp_path):
    """Un magasin mémoire isolé, sur son propre fichier."""
    os.environ["RAG_MEMORY_FILE"] = str(tmp_path / "rag.json")
    m = R.MemoryRagStore(reason="recette")
    m._docs, m._chunks, m._blobs = {}, {}, {}
    return m


def piece(nom="note.txt", texte="Brouillard d'eau : essais de qualification."):
    return nom, texte.encode("utf-8")


# ── 1. Le vocabulaire tient dans la place prévue ────────────────────────────

def test_aucun_theme_declare_n_est_coupe_par_la_limite():
    """Le contrôle qui vaut pour l'avenir : un thème plus long qu'il n'y a de
    place serait rangé sous un nom tronqué, donc introuvable, EN SILENCE."""
    trop_longs = [(t, len(t)) for t in R.THEMES if len(t) > COUPE]
    assert not trop_longs, (
        "ces thèmes seraient tranchés à l'écriture et rangés sous un nom qui "
        "n'existe pas : %s" % trop_longs)


def test_la_marge_restante_est_connue_et_annoncee():
    """Une limite qu'on ne mesure jamais se franchit sans bruit. On veut savoir
    de combien on approche, pas seulement qu'on n'y est pas encore."""
    plus_long = max(R.THEMES, key=len)
    marge = COUPE - len(plus_long)
    assert marge > 0, plus_long
    # Un niveau d'arborescence coûte environ « / » + un mot : une quinzaine de
    # caractères. En dessous, l'ajout suivant coupe, et ce test le dira AVANT.
    assert marge >= 15, (
        "plus que %d caractères de marge sous la limite de %d (le plus long "
        "thème est « %s ») : le prochain niveau d'arborescence sera tronqué. "
        "Relever la coupe dans rag_store._ingest, aux DEUX magasins."
        % (marge, COUPE, plus_long))


def test_le_chemin_profond_de_reference_est_bien_declare():
    """Sans lui, les tests suivants éprouveraient un thème inventé."""
    assert PROFOND in R.THEMES
    assert PROFOND.count(" / ") == 3, "quatre niveaux attendus"


# ── 2. L'aller-retour rend le chemin intact ─────────────────────────────────

def test_le_theme_profond_est_ecrit_en_entier(tmp_path):
    m = magasin(tmp_path)
    nom, data = piece()
    d = m.ingest_bytes(nom, data, title="Essais brouillard d'eau", theme=PROFOND)
    assert d["theme"] == PROFOND, d["theme"]


def test_la_sauvegarde_porte_le_chemin_complet(tmp_path, monkeypatch):
    """C'est le point demandé : ce qui SORT doit porter les quatre niveaux, et
    pas seulement la famille ni seulement la feuille."""
    m = magasin(tmp_path)
    m.ingest_bytes(*piece(), title="Essais brouillard d'eau", theme=PROFOND)

    import app as A
    monkeypatch.setattr(A, "rag", m)
    dump = A._rag_export()

    assert dump["count"] == 1, dump
    t = dump["documents"][0]["theme"]
    assert t == PROFOND, t
    # Les deux façons de perdre le chemin, nommées : garder la racine, ou ne
    # garder que la feuille. Un « in » suffirait à laisser passer les deux.
    assert t != "Engineering", "la famille seule ne dit pas où ranger"
    assert t != "Watermist", "la feuille seule ne se rattache à rien"


def test_restaurer_replace_le_document_au_meme_endroit(tmp_path, monkeypatch):
    """Sauvegarder puis restaurer dans une base VIDE doit rendre l'arborescence
    telle quelle : c'est la seule chose qu'on demande à une sauvegarde."""
    source = magasin(tmp_path / "a")
    source.ingest_bytes(*piece(), title="Essais brouillard d'eau", theme=PROFOND)

    import app as A
    monkeypatch.setattr(A, "rag", source)
    dump = A._rag_export()

    cible = magasin(tmp_path / "b")
    monkeypatch.setattr(A, "rag", cible)
    for it in dump["documents"]:
        import base64
        cible.ingest_bytes(it["filename"], base64.b64decode(it["content_b64"]),
                           title=it["title"], theme=it["theme"],
                           visibility=it["visibility"])

    rendus = cible.list_documents()
    assert len(rendus) == 1, rendus
    assert rendus[0]["theme"] == PROFOND, rendus[0]["theme"]


def test_un_theme_trop_long_serait_coupe_et_c_est_bien_le_risque(tmp_path):
    """LA DÉMONSTRATION DU RISQUE, pas un souhait. On écrit délibérément un
    chemin plus long que la place et on constate qu'il ressort tranché, sans la
    moindre erreur. C'est ce que le premier test de ce fichier interdit
    d'atteindre par accident."""
    m = magasin(tmp_path)
    long = PROFOND + " / Essais de qualification et rapports d'essais associés"
    assert len(long) > COUPE
    d = m.ingest_bytes(*piece(), title="x", theme=long)
    assert d["theme"] != long, "si cette coupe disparaît, relever aussi COUPE ici"
    assert len(d["theme"]) == COUPE
    assert d["theme"] not in R.THEMES, (
        "le document est rangé sous un nom absent du vocabulaire — c'est "
        "exactement la panne muette que le premier test prévient")


# ── 3. Ce que la restauration ne doit pas inventer ──────────────────────────

def test_un_document_sans_theme_ne_prend_pas_celui_du_precedent(tmp_path):
    """Un thème vide devient « Général » — une valeur par défaut ASSUMÉE. Ce
    qu'on interdit, c'est qu'il hérite du document d'à côté : une pièce rangée
    par erreur dans un dossier plausible est pire qu'une pièce sans dossier,
    parce qu'elle ne se cherche plus."""
    m = magasin(tmp_path)
    m.ingest_bytes("a.txt", b"Premier document sur le brouillard d'eau.",
                   title="A", theme=PROFOND)
    d = m.ingest_bytes("b.txt", b"Second document, sans theme declare du tout.",
                       title="B", theme="")
    assert d["theme"] == "Général", d["theme"]
    assert d["theme"] != PROFOND


@pytest.mark.parametrize("famille", [f for f, _ in R.THEME_FAMILLES])
def test_chaque_famille_a_au_moins_un_theme(famille):
    """Une famille vide s'affiche comme un dossier ouvrable qui ne contient
    rien : le lecteur croit à une base incomplète là où c'est le vocabulaire
    qui l'est."""
    assert R.themes_famille(famille), famille
