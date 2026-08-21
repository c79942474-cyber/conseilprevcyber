"""L'état de l'art — un fait sans son auteur est une rumeur.

CE QUE CE MODULE APPORTE À LA PAGE. Le moteur calcule à partir de constantes
normatives ; il ne dit rien du marché. Les faits qui décident d'un projet avant
tout calcul — la densité que prennent les baies d'IA, la part que prend le
refroidissement, les moratoires qui ferment un territoire — ne se déduisent
d'aucune formule. Ils se CITENT. C'est ce que fait `etat_art`.

CE QUE CES TESTS PROTÈGENT, ET LE DEUXIÈME POINT EST LE VRAI SUJET :

  1. AUCUN FAIT ORPHELIN, AUCUNE SOURCE MUETTE. Une valeur sans auteur ne
     serait plus citable ; une source listée que personne ne cite gonflerait la
     bibliographie sans rien apporter. Les deux sont vérifiés en CASSANT la
     correspondance, pas en la contemplant.

  2. LA HIÉRARCHIE DES SOURCES NE PEUT PAS S'EFFACER. Trois des quatre
     documents sont publiés par des fournisseurs d'infrastructure. Leurs
     mesures sont utiles, leur intérêt n'est pas neutre. Le jour où l'affichage
     cesserait de le dire, la page présenterait un argumentaire commercial au
     même rang qu'une analyse indépendante — sans erreur visible, sans trace,
     et un dossier bâti là-dessus se ferait démonter à la première
     contradiction. Ce qui protège le lecteur ici, ce n'est pas le chiffre :
     c'est l'étiquette qui l'accompagne, et les réserves.

  3. LE FICHIER « LCA » N'EST PAS UNE ACV. Le nom de fichier ment ; la mise au
     point est écrite dans le module ET portée jusqu'à la page. Un test la
     garde, parce qu'elle est exactement le genre de phrase qu'une relecture
     rapide supprime en la prenant pour un commentaire de travail.

  4. LA FRONTIÈRE AVEC LE MOTEUR. Ces chiffres ne doivent alimenter aucun
     calcul : le moteur tient ses constantes de normes, pas de livres blancs.
     Un test vérifie que le moteur n'importe pas ce module — la seule façon
     dont la frontière pourrait céder sans qu'on le voie.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import datacenter as dc  # noqa: E402
import etat_art as ea  # noqa: E402
import app as A  # noqa: E402
from conftest import ADMIN_EMAIL, _assurer_admin  # noqa: E402


@pytest.fixture
def client():
    """CONNECTÉ — depuis que la page demande un compte, un client anonyme ne
    mesurerait plus que la porte. La porte, elle, est éprouvée par les
    contrôles qui prennent la fixture `anonyme`."""
    _assurer_admin()
    A.app.config["TESTING"] = True
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["user_email"] = ADMIN_EMAIL
    return c


# ── 1. Aucun fait orphelin, aucune source muette ───────────────────────────

def test_chaque_fait_cite_une_source_connue():
    for f in ea.FAITS:
        assert f["source"] in ea.SOURCES, f["cle"]


def test_chaque_fait_cite_une_page():
    """Une source sans page n'est pas vérifiable : c'est une citation d'allure,
    pas une citation."""
    for f in ea.FAITS:
        assert isinstance(f["page"], int) and f["page"] > 0, f["cle"]


def test_le_module_refuse_un_fait_dont_la_source_n_existe_pas(monkeypatch):
    """LE contrôle du premier point : on casse la correspondance et on exige
    que le module la voie."""
    monkeypatch.setattr(ea, "FAITS", list(ea.FAITS) + [
        {"cle": "inventé", "famille": "eau", "enonce": "…",
         "source": "source_qui_n_existe_pas", "page": 1, "touche": None}])
    fautes = ea._verifier()
    assert any("source inconnue" in f for f in fautes), fautes


def test_le_module_refuse_une_source_que_personne_ne_cite(monkeypatch):
    """L'oubli inverse, et le plus courant : on verse un document dans la
    bibliographie, on n'en tire finalement rien, et il reste là — donnant à la
    page l'apparence d'une base plus large qu'elle n'est."""
    monkeypatch.setattr(ea, "FAITS",
                        [f for f in ea.FAITS if f["source"] != "honeywell_cycle"])
    fautes = ea._verifier()
    assert any("citée par aucun fait" in f for f in fautes), fautes


def test_le_module_refuse_deux_faits_de_meme_cle(monkeypatch):
    doublon = dict(ea.FAITS[0])
    monkeypatch.setattr(ea, "FAITS", list(ea.FAITS) + [doublon])
    fautes = ea._verifier()
    assert any("dupliquée" in f for f in fautes), fautes


def test_la_sante_est_verte_en_etat_normal():
    assert ea.sante()["problemes"] == []


# ── 2. La hiérarchie des sources ne peut pas s'effacer ─────────────────────

def test_les_documents_de_fournisseur_sont_declares_comme_tels():
    """Trois des quatre sources sont publiées par un vendeur d'infrastructure.
    Aucune ne doit passer pour une analyse indépendante."""
    fournisseurs = {"penguin_five", "penguin_efficient", "honeywell_cycle"}
    for cle in fournisseurs:
        nature = ea.SOURCES[cle]["nature"]
        assert nature != "analyse_editeur", cle
        assert "fournisseur" in nature or "guide" in nature, (cle, nature)


def test_ce_que_vaut_chaque_nature_est_ecrit_et_non_pas_seulement_nomme():
    """Étiqueter « livre blanc » sans dire ce qu'on peut en faire ne prévient
    personne."""
    for cle, n in ea.NATURES.items():
        assert n["nom"], cle
        assert len(n["poids"]) > 80, cle


def test_la_nature_accompagne_chaque_fait_jusqu_a_la_page():
    """Le contrôle qui compte : la hiérarchie doit survivre au passage dans
    `etat()`. Un affichage qui perdrait l'étiquette en chemin remettrait les
    quatre sources au même rang, sans lever la moindre erreur."""
    for g in ea.etat()["groupes"]:
        for f in g["faits"]:
            assert f["source"]["nature"] in ea.NATURES
            assert f["source"]["nature_nom"], f["cle"]
            assert f["source"]["editeur"], f["cle"]


def test_les_reserves_survivent_a_l_affichage():
    """Les réserves sont la partie honnête de cet état de l'art : elles disent
    qu'un chiffre est repris d'un tiers, qu'une branche défavorable existe,
    qu'une mesure est de laboratoire. Les perdre laisserait les chiffres nus et
    plus affirmatifs qu'ils ne sont."""
    portees = {f["cle"] for f in ea.FAITS if f.get("reserve")}
    assert len(portees) >= 8
    vues = {f["cle"] for g in ea.etat()["groupes"] for f in g["faits"]
            if f.get("reserve")}
    assert vues == portees, portees - vues


def test_l_avertissement_dit_l_essentiel_avant_le_premier_chiffre():
    a = ea.etat()["avertissement"]
    assert "fournisseur" in a
    assert "n'entre dans le calcul" in a


# ── 3. Le fichier « LCA » n'est pas une ACV ────────────────────────────────

def test_la_mise_au_point_sur_le_faux_ACV_est_ecrite():
    """Le nom de fichier dit « LCA » ; le document est un guide de sélection de
    prestataire. Un lecteur qui le citerait comme l'ACV du dossier citerait une
    source qui n'en est pas une."""
    note = ea.SOURCES["honeywell_cycle"]["note"]
    assert "ISO 14040" in note
    assert "n'est PAS une analyse de cycle de vie" in note
    assert ea.SOURCES["honeywell_cycle"]["nature"] == "guide_fournisseur"


def test_l_absence_d_ACV_est_declaree_comme_lacune():
    """La mise au point sur un document ne suffit pas : il faut dire que le
    carbone incorporé n'est chiffré NULLE PART dans les quatre."""
    assert any("ISO 14040" in l for l in ea.LACUNES)


def test_les_lacunes_disent_ce_que_la_base_ne_couvre_pas():
    """Une bibliographie qui ne liste que ses apports laisse croire qu'elle
    couvre le reste."""
    assert len(ea.LACUNES) >= 4
    for l in ea.LACUNES:
        assert len(l) > 60, l


# ── 4. La frontière avec le moteur ─────────────────────────────────────────

def test_aucun_chiffre_de_l_etat_de_l_art_n_alimente_le_moteur():
    """Le moteur tient ses constantes de normes. S'il venait à importer ce
    module, un chiffre de livre blanc pourrait entrer dans un calcul présenté
    comme normatif — et rien ne le signalerait."""
    with open(os.path.join(ICI, "datacenter.py"), encoding="utf-8") as f:
        src = f.read()
    assert "etat_art" not in src


def test_chaque_fait_relie_au_moteur_nomme_un_champ_qui_existe():
    """`touche` est ce qui distingue une revue de presse d'un état de l'art
    utile : il dit quelle décision de conception le fait éclaire. Un champ
    renommé dans le moteur laisserait ces renvois pointer dans le vide."""
    champs = {c["id"] for c in dc.CHAMPS}
    for f in ea.FAITS:
        if f.get("touche"):
            assert f["touche"] in champs, (f["cle"], f["touche"])


def test_le_lien_avec_le_moteur_n_est_pas_decoratif():
    """S'il ne restait qu'un ou deux renvois, la promesse « on ne cite que ce
    qui change une décision » ne tiendrait plus."""
    relies = [f for f in ea.FAITS if f.get("touche")]
    assert len(relies) >= 12
    assert len({f["touche"] for f in relies}) >= 5


# ── 5. Rien ne se perd entre le module et la page ──────────────────────────

def test_tous_les_faits_sont_affiches_une_fois_et_une_seule():
    """Un fait rangé dans une famille sans nom, ou dans aucun groupe,
    disparaîtrait de la page sans erreur."""
    cles = [f["cle"] for g in ea.etat()["groupes"] for f in g["faits"]]
    assert sorted(cles) == sorted(f["cle"] for f in ea.FAITS)


def test_chaque_famille_porte_un_nom_lisible():
    for fam in ea.familles():
        assert fam in ea.FAMILLES_NOM, fam
        assert ea.FAMILLES_NOM[fam] != fam


# ── 6. La route est ouverte, et elle sert bien l'état de l'art ─────────────

def test_la_route_demande_un_compte(anonyme):
    """L'état de l'art suit sa page : /datacenter demande désormais un compte,
    et le laisser lisible en /api rendrait cette fermeture décorative."""
    assert anonyme.get("/api/datacenter/etat-art").status_code == 401


def test_la_route_sert_le_client_connecte(client):
    r = client.get("/api/datacenter/etat-art")
    assert r.status_code == 200, r.status_code
    j = r.get_json()
    assert j["ok"] is True
    assert j["etat"]["n_faits"] == len(ea.FAITS)


def test_la_route_sert_les_natures_et_les_lacunes(client):
    """Servir les faits sans les natures ni les lacunes reviendrait à publier
    les chiffres en taisant ce qu'ils valent."""
    j = client.get("/api/datacenter/etat-art").get_json()["etat"]
    assert set(j["natures"]) == set(ea.NATURES)
    assert j["lacunes"] == ea.LACUNES


def test_la_page_porte_la_section_et_la_mise_au_point():
    with open(os.path.join(ICI, "datacenter.html"), encoding="utf-8") as f:
        h = f.read()
    assert 'id="dc-sec-art"' in h
    assert "/api/datacenter/etat-art" in h
