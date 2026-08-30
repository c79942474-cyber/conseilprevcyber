"""Chercher par point exigé, PUIS écrire — et non l'inverse.

CE QUI SE PASSAIT, ET QUI NE SE VOYAIT PAS. Une pièce déclare trois à six
points de contenu exigé. Sur le chemin AVEC modèle, la recherche par point
n'était pas seulement faite trop tard : elle n'était pas faite du tout. La
rédaction travaillait sur les extraits d'UNE SEULE requête générale, et rien ne
disait au modèle que la base ne parlait pas du quatrième point. Il l'écrivait
donc quand même, avec ce qu'il croit savoir.

C'EST LA DÉFAILLANCE LA PLUS COÛTEUSE, parce qu'elle ne se voit pas : une pièce
qui a l'air documentée et ne l'est pas ne se découvre qu'au visa.

LA RÈGLE QUI PROTÈGE LE BUDGET EST ICI AUSSI. Ce branchement ne doit ajouter
AUCUN appel de modèle — `couverture_documentaire` ne fait que des recherches.
Un faux modèle qui compte ses appels le vérifie : la facture ne bouge pas.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ingenierie_dc as ig                                          # noqa: E402
import rag_store                                                    # noqa: E402

PHASE, PIECE = "ESQ", "ESQ-01"


def _hit(did, texte, titre=None):
    return {"doc_id": did, "title": titre or ("Document " + did),
            "content": texte, "score": 1.0}


def _chercheur(par_requete=None, defaut=None):
    """Une base simulée : ce module ne connaît pas la vraie, et c'est voulu."""
    def _c(req, k):
        for motif, hits in (par_requete or {}).items():
            if motif.lower() in req.lower():
                return hits[:k]
        return list(defaut or [])[:k]
    return _c


# ── 1. La couverture rend ses extraits, à la demande seulement ─────────────

def test_sans_le_drapeau_la_structure_ne_change_pas():
    """Un appelant qui n'a rien demandé ne doit rien voir de neuf : la
    couverture reste un RAPPORT d'attribution, sans le texte des extraits."""
    c = ig.couverture_documentaire(PHASE, PIECE,
                                   _chercheur(defaut=[_hit("d1", "un texte")]))
    assert c and c["points"]
    for p in c["points"]:
        assert "extraits" not in p


def test_avec_le_drapeau_chaque_point_porte_ses_extraits_et_son_nom():
    c = ig.couverture_documentaire(PHASE, PIECE,
                                   _chercheur(defaut=[_hit("d1", "un texte")]),
                                   garder_extraits=True)
    for p in c["points"]:
        assert "extraits" in p
        for e in p["extraits"]:
            assert e.get("content"), "sans contenu, la rédaction n'a rien à lire"
            assert e.get("point") == p["point"], "l'extrait doit dire quel point il appuie"


def test_un_point_inconnu_porte_aussi_la_cle():
    """Une base muette ne doit pas produire deux formes de structure :
    l'appelant testerait deux fois la même chose, et oublierait un cas."""
    def _casse(req, k):
        raise RuntimeError("base absente")
    c = ig.couverture_documentaire(PHASE, PIECE, _casse, garder_extraits=True)
    assert all(p["etat"] == "inconnu" and p["extraits"] == [] for p in c["points"])


# ── 2. L'ordre : chaque point garde son appui sous la coupe du budget ──────

def test_le_premier_appui_de_chaque_point_passe_avant_le_second_appui_du_premier():
    """LE BUDGET DE CONTEXTE COUPE DANS L'ORDRE REÇU.

    Verser point après point — tous les extraits du premier, puis ceux du
    deuxième — laisserait les derniers points sans aucun appui dès que le
    budget se referme. Et ce sont justement les points qu'il faut soutenir.
    """
    couverture = {"points": [
        {"point": "A", "etat": "couvert",
         "extraits": [_hit("a1", "aa", ), _hit("a2", "bb")]},
        {"point": "B", "etat": "couvert", "extraits": [_hit("b1", "cc")]},
    ]}
    ordre = [h["doc_id"] for h in ig.extraits_pour_redaction(couverture)]
    assert ordre == ["a1", "b1", "a2"]


def test_les_extraits_de_la_requete_generale_viennent_apres():
    couverture = {"points": [{"point": "A", "etat": "couvert",
                              "extraits": [_hit("a1", "aa")]}]}
    ordre = [h["doc_id"] for h in
             ig.extraits_pour_redaction(couverture, [_hit("large", "zz")])]
    assert ordre == ["a1", "large"], "le large ne doit pas voler la place d'un appui"


def test_le_meme_passage_retenu_sur_deux_points_ne_coute_pas_deux_fois():
    partage = _hit("d9", "un passage commun")
    couverture = {"points": [
        {"point": "A", "etat": "couvert", "extraits": [dict(partage, point="A")]},
        {"point": "B", "etat": "couvert", "extraits": [dict(partage, point="B")]},
    ]}
    assert len(ig.extraits_pour_redaction(couverture)) == 1


def test_sans_couverture_les_extraits_generaux_passent_tels_quels():
    """L'absence de couverture ne doit rien casser : c'est le comportement
    d'avant, et il reste le repli."""
    larges = [_hit("x", "1"), _hit("y", "2")]
    assert ig.extraits_pour_redaction(None, larges) == larges


# ── 3. Ce que la base ne dit pas, nommé — et l'interdit qui va avec ────────

def test_les_points_sans_appui_sont_nommes_avec_l_interdiction_d_inventer():
    """UN MODÈLE QUI IGNORE LE TROU LE COMBLE ; À QUI ON LE NOMME, IL L'ANNONCE."""
    c = {"points": [{"point": "Contraintes de site relevées", "etat": "a_ecrire"},
                    {"point": "Parti d'implantation retenu", "etat": "couvert"}]}
    texte = ig.consigne_manques(c)
    assert "Contraintes de site relevées" in texte
    assert "Parti d'implantation retenu" not in texte, "ne nommer que ce qui manque"
    assert "inventez" in texte.lower()


def test_une_couverture_indeterminee_ne_se_dit_pas_comme_un_manque():
    """« La base n'a pas répondu » n'est pas « la base ne dit rien » : annoncer
    un trou qu'on n'a pas constaté ferait écrire une réserve fausse."""
    c = {"points": [{"point": "Un point", "etat": "inconnu"}]}
    texte = ig.consigne_manques(c)
    assert "INDÉTERMINÉE" in texte and "n'a rien rendu" not in texte


def test_rien_a_dire_ne_dit_rien():
    """Une consigne qui s'affiche toujours cesse d'être lue."""
    c = {"points": [{"point": "A", "etat": "couvert"}]}
    assert ig.consigne_manques(c) == ""


# ── 4. Le modèle doit LIRE à quel point l'extrait répond ───────────────────

def test_l_etiquette_du_contexte_porte_le_point():
    """SANS ELLE, L'ORDRE PAR POINT NE SERT À RIEN. Le modèle recevrait de
    meilleurs extraits sans savoir lequel appuie quoi, et referait de tête le
    rapprochement que la couverture vient de faire — ce rapprochement de tête
    étant exactement ce qui laisse un point traité de mémoire."""
    bloc, _ = rag_store.build_context_retenus(
        [dict(_hit("d1", "le contenu"), point="Contraintes de site relevées")])
    assert "pour : Contraintes de site relevées" in bloc


def test_un_extrait_sans_point_garde_son_etiquette_d_avant():
    bloc, _ = rag_store.build_context_retenus([_hit("d1", "le contenu")])
    assert "pour :" not in bloc


# ── 5. Le branchement, de bout en bout ─────────────────────────────────────

class _Journal:
    """Un modèle et une base simulés, QUI COMPTENT LEURS APPELS.

    Le comptage n'est pas décoratif : la règle qui protège le budget en dépend.
    """

    def __init__(self):
        self.recherches = []
        self.appels_modele = 0
        self.dernier_user = ""
        self.dernier_contexte = ""

    def search(self, req, k=8, public_only=False, doc_ids=None, **kw):
        self.recherches.append(req)
        if "implantation" in req.lower():
            return [_hit("imp", "Le parti d'implantation est en peigne.")]
        if "constructifs" in req.lower():
            return [_hit("cons", "Structure poteaux-poutres béton.")]
        # LA BASE NE DIT RIEN DE CE POINT-LÀ, et c'est le cas qui compte : sans
        # lui, la règle des manques ne vérifierait rien — tout serait couvert.
        if "contraintes de site" in req.lower():
            return []
        return [_hit("large", "Généralités sur le centre de données.")]

    def rerank(self, model, query, hits, k):
        self.appels_modele += 1
        return list(hits)[:k]

    def generate(self, model, system, user, context=None, **kw):
        self.appels_modele += 1
        self.dernier_user = user or ""
        self.dernier_contexte = context or ""
        return "Un texte de livrable.", "modele-simule"


@pytest.fixture
def journal(monkeypatch):
    import app as application
    j = _Journal()
    monkeypatch.setattr(application.rag, "search", j.search)
    monkeypatch.setattr(application.assistant, "available",
                        lambda: {"claude": True, "mistral": False})
    monkeypatch.setattr(application.assistant, "rerank", j.rerank)
    monkeypatch.setattr(application.assistant, "generate", j.generate)
    return j


def _rediger(journal, **extra):
    import app as application
    data = {"phase": PHASE, "piece": PIECE, "client": "Essai"}
    data.update(extra)
    with application.app.test_request_context("/"):
        application._livrables_run("note-esq", data, "SYS", "USER")
    return journal


def test_la_recherche_se_fait_point_par_point_avant_de_rediger(journal):
    """LA RÈGLE CENTRALE. Une seule requête générale laissait le quatrième
    point exigé sans la moindre recherche."""
    j = _rediger(journal)
    assert len(j.recherches) > 1, "une seule requête : la couverture n'a pas tourné"
    pc = ig.piece(PHASE, PIECE)
    for point in pc["contenu"]:
        assert any(point.lower() in r.lower() for r in j.recherches), point


def test_le_contexte_dit_au_modele_quel_point_chaque_extrait_appuie(journal):
    j = _rediger(journal)
    assert "pour : " in j.dernier_contexte
    assert "Parti d'implantation retenu" in j.dernier_contexte


def test_les_points_sans_appui_sont_nommes_au_modele(journal):
    """Le point « Contraintes de site relevées » ne trouve rien dans la base
    simulée : le modèle doit l'apprendre AVANT d'écrire, pas après."""
    j = _rediger(journal)
    assert "Contraintes de site relevées" in j.dernier_user
    assert "inventez" in j.dernier_user.lower()


def test_le_branchement_n_ajoute_aucun_appel_de_modele(journal):
    """LA RÈGLE QUI PROTÈGE LE BUDGET.

    `couverture_documentaire` ne fait que des RECHERCHES. Trois requêtes de
    plus ne coûtent rien ; trois appels de modèle de plus coûteraient le prix
    d'une rédaction à chaque pièce.
    """
    j = _rediger(journal)
    assert j.appels_modele == 2, (
        "un juge de reclassement et une génération, pas davantage — %d appels"
        % j.appels_modele)


def test_une_selection_manuelle_n_est_pas_reordonnee(journal, monkeypatch):
    """Vous avez dit quels documents : la couverture dit ce qu'ils ne couvrent
    pas, elle ne va pas en chercher d'autres à leur place."""
    import app as application
    vus = {}
    vraie = ig.extraits_pour_redaction
    monkeypatch.setattr(ig, "extraits_pour_redaction",
                        lambda c, comp=None: vus.setdefault("appele", True) or vraie(c, comp))
    _rediger(journal, doc_ids=["a" * 32])
    assert "appele" not in vus, "l'ordre choisi par l'utilisateur a été refait"


def test_une_base_muette_n_empeche_pas_d_ecrire(journal, monkeypatch):
    """La couverture est un APPUI, jamais une condition."""
    import app as application

    def _casse(*a, **k):
        raise RuntimeError("base absente")

    monkeypatch.setattr(application.rag, "search", _casse)
    j = _rediger(journal)
    assert j.appels_modele >= 1, "la génération doit avoir eu lieu malgré tout"


def test_le_chemin_sans_modele_n_interroge_la_base_qu_une_fois_par_point(journal):
    """LA COUVERTURE ÉTAIT CALCULÉE DEUX FOIS : une pour l'annexe, tandis que
    la trame, elle, était assemblée sur les extraits d'une requête générale.

    On compte les RECHERCHES plutôt que les appels à la fonction : une première
    version de cette règle comptait les appels et restait verte parce que le
    bloc d'annexe n'était pas atteint dans les conditions de l'essai. Elle
    passait pour une raison qui n'avait rien à voir avec ce qu'elle affirmait.
    Le nombre de requêtes portant un point exigé, lui, est observable quoi
    qu'il advienne de la trame.
    """
    import app as application
    with application.app.test_request_context("/"):
        application._trame_sans_modele(
            "note-esq", {"phase": PHASE, "piece": PIECE}, "", None,
            {"claude": False, "mistral": False})
    pc = ig.piece(PHASE, PIECE)
    for point in pc["contenu"]:
        vues = [r for r in journal.recherches if point.lower() in r.lower()]
        assert len(vues) == 1, (
            "« %s » a été cherché %d fois — la couverture tourne en double"
            % (point, len(vues)))
