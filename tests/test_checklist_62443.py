"""LA CHECKLIST IEC 62443 — et le mot qu’elle refuse d’employer.

CE QUE CE MODULE FAIT : il porte vingt-sept points en six sections, chacun
rattaché à la partie de la série qui le fonde, chacun disant la preuve qu’un
auditeur demandera. Il compte ce qui est coché.

CE QU’IL REFUSE : rendre un « niveau de maturité ». Ce n’est pas un scrupule de
vocabulaire. La CEI 62443-2-4 définit des NIVEAUX DE MATURITÉ (ML 1 à 4) pour
le programme d’un prestataire, la 62443-3-3 des NIVEAUX DE SÉCURITÉ (SL 1 à 4)
par exigence et par zone ; les deux se constatent sur preuves, pour un
périmètre donné. Un compte de cases n’est ni l’un ni l’autre. Afficher « 68 %
de maturité » emprunterait le vocabulaire de la norme pour désigner autre
chose — et ce chiffre-là finirait cité devant un auditeur qui demanderait sur
quelle évaluation il repose.

QUATRE PROPRIÉTÉS QUE CES CONTRÔLES GARDENT

  1. LE REFUS EST PUBLIÉ, et il NOMME ce qu’il refuse. Réduit à « ceci est
     indicatif », il ne protégerait plus de rien.
  2. CHAQUE POINT PORTE SA PREUVE. Une case cochée sans document derrière ne
     vaut rien.
  3. CHAQUE POINT CITE UNE PARTIE DÉCLARÉE de la série. Citer « 62443-2-3 »
     sans l’avoir déclarée ferait afficher une référence dont la page ne sait
     rien — c’était le cas, et la garde ne le voyait pas.
  4. UN POINT INCONNU EST REFUSÉ, pas ignoré : un total qui compterait des
     points inexistants ne se recouperait pas.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import app as A  # noqa: E402
import checklist_62443 as C  # noqa: E402
from conftest import ADMIN_EMAIL, _assurer_admin  # noqa: E402

H = {"Origin": "http://localhost", "Referer": "http://localhost/x"}


@pytest.fixture
def client():
    _assurer_admin()
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["user_email"] = ADMIN_EMAIL
    A._ip_rate._hits.clear()
    yield c
    A._ip_rate._hits.clear()


def _toutes():
    return [p["cle"] for s in C.SECTIONS for p in s["points"]]


# ═══════════════════════════════════════════════════════════════════════════
#  1. CE QUE LE COMPTE N’EST PAS
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_le_module_ne_rend_JAMAIS_un_niveau_de_maturite():
    """« Maturité » et « niveau de sécurité » sont des notions définies par la
    série. Les employer pour un compte de cases emprunterait leur autorité."""
    r = C.compter(["politique", "responsable"])
    # LA SOUS-CHAÎNE, PAS L’ÉGALITÉ DE CLÉ. Écrit « "niveau" not in r », ce
    # contrôle testait l’existence d’une clé nommée exactement « niveau » — et
    # laissait donc passer « niveau_maturite », qui est précisément la fuite
    # qu’il a pour objet d’empêcher. Vérifié par injection : le module pouvait
    # se mettre à rendre un niveau sans qu’un seul contrôle ne tombe.
    champs = " ".join(r.keys()).lower()
    for interdit in ("maturite", "maturité", "niveau", "score", "cotation",
                     "_ml", "_sl"):
        assert interdit not in champs, (interdit, sorted(r))
    # Le seul champ qui parle de maturité est celui qui la REFUSE, et il est
    # nommé pour ce qu’il fait.
    assert "ce_que_ce_n_est_pas" in r
    assert "part_cochee_pct" in r, "le pourcentage doit être NOMMÉ pour ce qu’il est"
    # …et aucune VALEUR rendue ne se présente comme un niveau.
    for cle, v in r.items():
        # `isinstance(True, int)` vaut vrai en Python : sans exclure les
        # booléens, ce contrôle attrapait le drapeau `ok`.
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        assert cle in ("faits", "sur", "part_cochee_pct"), (cle, v)


def test_LE_POINT_QUI_DECIDE_le_refus_NOMME_ce_qu_il_refuse():
    """Réduit à « ceci est indicatif », il ne protégerait plus de rien : c’est
    la confusion avec ML et SL qu’il a pour objet d’empêcher."""
    t = C.REFUS_MATURITE
    assert "ML 1 à 4" in t and "SL 1 à 4" in t
    assert "62443-2-4" in t and "62443-3-3" in t
    assert "sur preuves" in t
    # …et il voyage AVEC chaque réponse, pas seulement dans le référentiel.
    assert C.compter([])["ce_que_ce_n_est_pas"] == t
    assert C.referentiel()["refus_maturite"] == t


def test_le_pourcentage_est_publie_mais_NOMME_part_cochee():
    """Le taire ne l’empêcherait pas d’être recalculé de tête. Le nommer
    « part des points cochés » et non « maturité » lui donne son sens."""
    r = C.compter(["politique"])
    assert abs(r["part_cochee_pct"] - round(1 / 27 * 100, 1)) < 0.05
    assert r["faits"] == 1 and r["sur"] == 27


# ═══════════════════════════════════════════════════════════════════════════
#  2. LA LISTE
# ═══════════════════════════════════════════════════════════════════════════

def test_les_six_sections_et_les_vingt_sept_points_sont_LA():
    assert len(C.SECTIONS) == 6
    assert C.referentiel()["total"] == 27
    attendus = ["Gouvernance", "Architecture", "accès", "Protection",
                "Monitoring", "Fournisseurs"]
    for s, mot in zip(C.SECTIONS, attendus):
        assert mot in s["nom"], (s["nom"], mot)
    tailles = [len(s["points"]) for s in C.SECTIONS]
    assert tailles == [5, 5, 5, 5, 4, 3], tailles


def test_LE_POINT_QUI_DECIDE_chaque_point_dit_LA_PREUVE_attendue():
    """C’est ce qui distingue une liste utile d’une liste décorative : une case
    cochée sans document derrière est la première chose qu’un auditeur
    attaque."""
    for s in C.SECTIONS:
        for p in s["points"]:
            assert len(p["preuve"]) >= 40, (p["cle"], p["preuve"])
            # Une preuve qui commence par « à fournir » ne dit rien de ce
            # qu’il faut fournir.
            assert not p["preuve"].lower().startswith(("à fournir", "a fournir",
                                                       "à définir")), p["cle"]
            # Une preuve désigne un OBJET à montrer, pas une intention.
            assert not p["preuve"].lower().startswith("il faut"), p["cle"]


def test_LE_POINT_QUI_DECIDE_chaque_point_cite_une_partie_DECLAREE():
    """La garde ne portait que sur les sections : un point pouvait donc citer
    une partie non déclarée — « 62443-2-3 » l’a fait — et la page l’aurait
    affichée sans savoir de quoi elle parle."""
    for s in C.SECTIONS:
        assert s["partie"] in C.PARTIES, s["cle"]
        for p in s["points"]:
            assert p["rattachement"] in C.PARTIES, (p["cle"], p["rattachement"])
    for cle, d in C.PARTIES.items():
        assert cle.startswith("62443-") and d["titre"] and d["porte"]


def test_aucune_partie_n_est_declaree_sans_servir():
    """Une partie déclarée que nul point ne cite occuperait la page sans que
    rien ne la lise — c’est la faute que ce dépôt corrige ailleurs sur les
    quantités orphelines."""
    citees = {s["partie"] for s in C.SECTIONS}
    citees |= {p["rattachement"] for s in C.SECTIONS for p in s["points"]}
    assert set(C.PARTIES) == citees, set(C.PARTIES) ^ citees


def test_aucune_cle_de_point_en_double():
    cles = _toutes()
    assert len(cles) == len(set(cles)) == 27


# ═══════════════════════════════════════════════════════════════════════════
#  3. LE COMPTE
# ═══════════════════════════════════════════════════════════════════════════

def test_le_compte_par_section_se_REFAIT_a_la_main():
    r = C.compter(["politique", "responsable", "inventaire"])
    par = {s["cle"]: s for s in r["par_section"]}
    assert par["gouvernance"]["faits"] == 2 and par["gouvernance"]["sur"] == 5
    assert par["architecture"]["faits"] == 1
    assert par["protection"]["faits"] == 0
    assert sum(s["faits"] for s in r["par_section"]) == r["faits"] == 3


def test_LE_POINT_QUI_DECIDE_la_lecture_designe_les_sections_VIDES():
    """Un total global cache qu’une section entière est à zéro — et c’est là
    que se trouve l’écart, pas dans la moyenne."""
    r = C.compter(["politique", "responsable"])
    assert "AUCUN point coché" in r["lecture"]
    assert "Protection technique" in r["lecture"]
    # …et quand chaque section porte au moins un point, on ne le dit plus.
    une_par_section = [s["points"][0]["cle"] for s in C.SECTIONS]
    assert "AUCUN point coché" not in C.compter(une_par_section)["lecture"]


def test_ce_qui_RESTE_est_rendu_avec_sa_preuve():
    """C’est la liste qu’on emporte en réunion. Rendre seulement le compte
    obligerait à retrouver soi-même les vingt-quatre points restants."""
    r = C.compter(["politique"])
    gouv = next(s for s in r["par_section"] if s["cle"] == "gouvernance")
    assert len(gouv["restants"]) == 4
    assert all(x["preuve"] and x["rattachement"] for x in gouv["restants"])
    assert "politique" not in [x["cle"] for x in gouv["restants"]]


def test_LE_POINT_QUI_DECIDE_un_point_inconnu_est_REFUSE_pas_ignore():
    """Un total qui compterait des points inexistants ne se recouperait pas :
    on lirait 28 sur 27 sans savoir d’où vient le vingt-huitième."""
    r = C.compter(["politique", "point_invente"])
    assert r["ok"] is False and r["erreur"] == "points_inconnus"
    assert "point_invente" in r["message"]
    assert "faits" not in r
    assert len(r["connus"]) == 27


def test_les_deux_extremes_se_disent_differemment():
    vide = C.compter([])
    plein = C.compter(_toutes())
    assert vide["faits"] == 0 and "Rien n’est coché" in vide["lecture"]
    assert plein["faits"] == 27 and plein["part_cochee_pct"] == 100.0
    # …et même à 27 sur 27, la page renvoie aux preuves, pas au score.
    assert "preuves" in plein["lecture"]


# ═══════════════════════════════════════════════════════════════════════════
#  4. LES ROUTES
# ═══════════════════════════════════════════════════════════════════════════

def test_les_routes_servent_la_liste_et_le_compte(client):
    r = client.get("/api/62443/checklist")
    assert r.status_code == 200
    j = r.get_json()
    assert j["ok"] and j["referentiel"]["total"] == 27
    assert j["referentiel"]["refus_maturite"] == C.REFUS_MATURITE

    A._ip_rate._hits.clear()
    r2 = client.post("/api/62443/checklist/compter", headers=H,
                     json={"coches": ["politique", "mfa"]})
    assert r2.status_code == 200 and r2.get_json()["faits"] == 2

    A._ip_rate._hits.clear()
    r3 = client.post("/api/62443/checklist/compter", headers=H,
                     json={"coches": ["nawak"]})
    assert r3.status_code == 400
    assert r3.get_json()["erreur"] == "points_inconnus"


def test_la_page_est_ATTEIGNABLE_depuis_le_referentiel(client):
    """Un module qu’on ne trouve pas n’existe pas. La carte doit être sur la
    page du référentiel, pas seulement au pied de page."""
    assert client.get("/checklist-62443").status_code == 200
    ref = client.get("/referentiel").get_data(as_text=True)
    assert 'href="/checklist-62443"' in ref
    assert "Checklist de conformité" in ref


def test_la_page_porte_le_refus_AVANT_la_liste():
    """Une note sous vingt-sept cases ne se lit jamais."""
    with open(os.path.join(ICI, "checklist-62443.html"), encoding="utf-8") as f:
        page = f.read()
    assert page.index('id="ck-refus"') < page.index('id="ck-liste"')
    # …et la page ne promet nulle part une maturité.
    entete = page[:page.index("<script")]
    for interdit in ("niveau de maturité", "votre maturité", "score de maturité"):
        assert interdit not in entete.lower(), interdit


def test_la_page_ANNONCE_que_rien_n_est_conserve():
    """Une liste de vérification à moitié remplie décrit l’état réel d’une
    installation industrielle. Le lecteur doit savoir où elle reste."""
    with open(os.path.join(ICI, "checklist-62443.html"), encoding="utf-8") as f:
        page = f.read()
    assert "restent dans ce navigateur" in page
    assert "localStorage" in page and "/api/62443/checklist/compter" in page
