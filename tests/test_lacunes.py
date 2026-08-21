"""Faire parler les sources — sans fabriquer de faits.

CE QUI ÉTAIT MANQUANT. L'état de l'art nommait quatre trous et n'offrait rien
pour les combler : le lecteur restait devant une liste de manques.

LE PIÈGE, ET IL EST DE FOND. La valeur de cette section tient à une chose :
chaque fait porte son AUTEUR, sa PAGE et la NATURE de sa source — son titre le
dit, « et qui le dit ». Une réponse produite par un modèle de langage n'a ni
auteur, ni page, ni éditeur : elle a un style. Versée au milieu des faits
cités, elle emprunte leur crédit sans en avoir la provenance. Un chiffre
plausible assorti d'une référence plausible est la faute la plus coûteuse
qu'un cabinet mette dans un dossier client : elle ne se voit qu'au moment où
un tiers va vérifier.

CE QUE CES TESTS VERROUILLENT — DANS CET ORDRE D'IMPORTANCE :

  1. les trois registres restent SÉPARÉS, et chacun dit s'il est citable ;
  2. les gisements ne portent AUCUNE valeur chiffrée : ce sont des endroits où
     chercher, pas des réponses, et un chiffre glissé là serait lu comme un
     fait sourcé alors que personne n'a ouvert le jeu de données ;
  3. la consigne donnée au modèle lui INTERDIT de répondre à la question ;
  4. l'absence est une réponse : sans document, on le dit au lieu de rapprocher
     un texte de force ;
  5. les extraits du corpus arrivent au modèle CLOS par garde_ia — un document
     empoisonné versé à la base ne doit pas ressortir avec ses consignes
     intactes par ce chemin-là.
"""
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import etat_art  # noqa: E402
import lacunes as L  # noqa: E402
from conftest import ADMIN_EMAIL, _assurer_admin  # noqa: E402

H = {"Origin": "http://localhost"}


@pytest.fixture
def client():
    import app
    _assurer_admin()
    app.app.config["TESTING"] = True
    c = app.app.test_client()
    with c.session_transaction() as s:
        s["user_email"] = ADMIN_EMAIL
    return c


def page():
    with open(os.path.join(ICI, "datacenter.html"), encoding="utf-8") as f:
        return f.read()


# ── 1. Le module se tient ──────────────────────────────────────────────────

def test_le_module_se_charge_sans_incoherence():
    assert L.sante()["problemes"] == []


def test_chaque_lacune_annoncee_par_la_page_peut_etre_instruite():
    """Une lacune sans moyen d'être instruite laisse le lecteur devant un mur.
    C'est ce que faisaient les quatre."""
    declarees = " ".join(etat_art.LACUNES)
    for cle, l in L.LACUNES.items():
        assert l["manque"] in declarees, cle
    assert len(L.LACUNES) >= len(etat_art.LACUNES)


def test_les_deux_enonces_du_meme_trou_ne_peuvent_pas_diverger():
    """DÉFAUT PRÉVENU. Deux formulations du même manque donneraient au lecteur
    deux versions, et il croirait à deux trous."""
    import copy
    sauve = copy.deepcopy(L.LACUNES)
    try:
        L.LACUNES["wue"]["manque"] = "Aucune donnée sur l'eau, formulation divergente"
        f = L._verifier()
        assert any("diverg" in x for x in f), f
    finally:
        L.LACUNES.clear()
        L.LACUNES.update(sauve)
    assert L._verifier() == []


@pytest.mark.parametrize("cle", sorted(L.LACUNES))
def test_chaque_lacune_dit_ce_qui_vaudra_preuve(cle):
    """Sans critère, on ne sait jamais si le trou est comblé — et n'importe
    quel document approchant fera l'affaire."""
    l = L.LACUNES[cle]
    assert len(l["preuve"]) >= 100, cle
    assert len(l["question"]) >= 80, cle
    assert l["question"].rstrip().endswith("?"), cle


@pytest.mark.parametrize("cle", sorted(L.LACUNES))
def test_chaque_lacune_dit_ce_qu_une_reponse_ne_reglera_pas(cle):
    """Un trou comblé qu'on croit tout régler en ouvre un autre en silence."""
    assert len(L.LACUNES[cle]["hors_portee"]) >= 80, cle


# ── 2. Les gisements ne répondent pas, ils indiquent ───────────────────────

@pytest.mark.parametrize("cle", sorted(L.LACUNES))
def test_au_moins_deux_gisements_par_lacune(cle):
    """Un gisement unique se lit comme LA réponse."""
    assert len(L.LACUNES[cle]["gisements"]) >= 2, cle


def test_aucun_gisement_ne_porte_de_valeur_chiffree():
    """LE CONTRÔLE QUI COMPTE ICI. Un chiffre écrit dans « contient » serait lu
    comme un fait sourcé — alors que personne n'a ouvert le jeu de données."""
    for cle, l in L.LACUNES.items():
        for g in l["gisements"]:
            assert not re.search(L._VALEUR, g["contient"]), (cle, g["instrument"])


def test_le_garde_attrape_une_valeur_glissee_dans_un_gisement():
    """Prouvé plutôt qu'affirmé : on injecte, on vérifie que ça tombe."""
    import copy
    sauve = copy.deepcopy(L.LACUNES)
    try:
        L.LACUNES["wue"]["gisements"][0]["contient"] = "Un WUE moyen de 1,8 m³/MWh."
        f = L._verifier()
        assert any("valeur chiffree" in x for x in f), f
    finally:
        L.LACUNES.clear()
        L.LACUNES.update(sauve)
    assert L._verifier() == []


def test_le_seuil_de_couverture_a_son_champ_et_reste_permis():
    """« Centres de 500 kW et plus » ne répond à aucune question : il dit QUI
    est dans la base, ce que le lecteur doit savoir avant de s'y fier. Le
    mélanger au contenu obligerait à relâcher le garde — et c'est par là que
    passerait, un jour, une vraie valeur."""
    eed = [g for g in L.LACUNES["wue"]["gisements"] if "1364" in g["instrument"]]
    assert eed, "le gisement le plus direct sur cette lacune a disparu"
    assert "500 kW" in eed[0].get("perimetre", "")
    assert not re.search(L._VALEUR, eed[0]["contient"])


@pytest.mark.parametrize("cle", sorted(L.LACUNES))
def test_chaque_gisement_dit_ce_qu_il_ne_regle_pas(cle):
    for g in L.LACUNES[cle]["gisements"]:
        assert len(g["reserve"]) >= 40, (cle, g["instrument"])


def test_aucune_adresse_web_dans_les_gisements():
    """Une adresse ne survit pas à une refonte de site, et une adresse morte
    fait douter de la référence — qui, elle, reste juste."""
    for cle, l in L.LACUNES.items():
        for g in l["gisements"]:
            for champ in ("organisme", "instrument", "contient", "reserve"):
                assert "http" not in g[champ].lower(), (cle, champ)


# ── 3. Ce que le modèle n'a PAS le droit de faire ──────────────────────────

def test_la_consigne_interdit_au_modele_de_repondre():
    """Sans cette interdiction, un modèle à qui l'on soumet une lacune la
    comble — c'est ce qu'on lui a appris à faire.

    LE CONTRÔLE EST BILATÉRAL, ET LA PREMIÈRE VERSION NE L'ÉTAIT PAS. Elle ne
    cherchait que des marques d'interdiction. J'ai remplacé « N'avance AUCUN
    chiffre » par « Complète librement avec ce que tu sais, AUCUN chiffre » —
    une consigne de sens INVERSE — et le test est resté vert : la sous-chaîne
    « AUCUN chiffre » avait survécu. Chercher la présence d'une formule ne dit
    rien de ce que la phrase demande. On exige donc aussi l'ABSENCE des
    formules qui autoriseraient ce qu'on interdit."""
    c = L.CONSIGNE_LECTURE
    assert "NE RÉPONDS PAS" in c
    assert "N'avance AUCUN chiffre" in c, "l'interdiction, pas seulement le mot"
    assert "N'utilise PAS tes connaissances générales" in c
    assert "n'est PAS citable" in c
    # Ce qui ne doit JAMAIS apparaître : la permission de compléter.
    for permission in ("Complète librement", "complète librement",
                       "avec ce que tu sais", "utilise tes connaissances",
                       "tu peux compléter"):
        assert permission not in c, permission


def test_la_demande_porte_la_question_et_ce_qui_vaudrait_preuve():
    s, u = L.prompt_lecture(L.get("wue"), "EXTRAITS ICI")
    assert "QUESTION À INSTRUIRE" in u
    assert "CE QUI VAUDRAIT PREUVE" in u
    assert "CE QUI RESTE OUVERT" in s
    assert "EXTRAITS ICI" in u


def test_la_demande_ne_reclot_pas_un_contexte_deja_clos():
    """build_context clôt déjà les extraits. Une seconde clôture emboîtée
    apprendrait au modèle que la première n'était pas sérieuse."""
    import garde_ia
    s, u = L.prompt_lecture(L.get("acv"), "contexte")
    assert garde_ia.OUVRE not in u


def test_la_mention_non_citable_dit_pourquoi():
    m = L.MENTION_NON_CITABLE
    assert "ni auteur" in m and "ni page" in m
    assert "ne se cite pas" in m
    assert "Ce qui se cite" in m, "il faut dire ce qui, LUI, se cite"


# ── 4. La route : trois registres, jamais mélangés ─────────────────────────

def test_le_referentiel_est_ouvert_et_ne_contient_aucun_extrait(client):
    """Ce référentiel est PUBLIC : il ne doit porter que des questions, des
    thèmes de recherche et des gisements — jamais un document du cabinet.

    LE CONTRÔLE EST STRUCTUREL, ET LA PREMIÈRE VERSION NE L'ÉTAIT PAS. Elle
    cherchait le mot « extrait » dans la réponse et tombait sur la mention
    « produite à partir des extraits ci-dessus », qui est du texte
    d'avertissement. Chercher un mot dans du JSON éprouve le vocabulaire ; on
    veut éprouver la STRUCTURE."""
    r = client.get("/api/datacenter/lacunes")
    assert r.status_code == 200
    j = r.get_json()
    assert j["ok"] and len(j["referentiel"]["lacunes"]) == len(L.LACUNES)
    for l in j["referentiel"]["lacunes"]:
        assert "extrait" not in l, l["cle"]
        assert "documents" not in l, l["cle"]
        assert set(l) <= {"cle", "titre", "manque", "question", "requete",
                          "themes", "preuve", "gisements", "hors_portee"}, sorted(l)


def test_la_recherche_dans_la_base_reste_fermee():
    """Elle porte sur des documents INTERNES du cabinet."""
    import app
    c = app.app.test_client()
    r = c.post("/api/datacenter/lacune/wue", headers=H, json={})
    assert r.status_code == 401, r.status_code


def test_une_lacune_inconnue_le_dit(client):
    r = client.post("/api/datacenter/lacune/inventee", headers=H, json={})
    assert r.status_code == 404


def test_les_trois_registres_sortent_separes_et_etiquetes(client):
    r = client.post("/api/datacenter/lacune/wue", headers=H,
                    json={"lecture": False})
    assert r.status_code == 200, r.data[:200]
    j = r.get_json()
    assert j["interne"]["citable"] is True
    assert j["lecture"]["citable"] is False
    assert "non consult" in j["gisements_note"].lower()
    # Les trois sont des CLÉS DISTINCTES : rien ne peut se mélanger par
    # inadvertance à la lecture du JSON.
    assert set(j) >= {"interne", "lecture", "gisements", "gisements_note"}


def test_la_lecture_assistee_ne_porte_jamais_de_documents(client):
    """Si un jour le registre 2 se mettait à porter des « sources », elles
    seraient produites par le modèle et sans provenance."""
    r = client.post("/api/datacenter/lacune/acv", headers=H, json={"lecture": False})
    j = r.get_json()
    assert set(j["lecture"]) <= {"texte", "modele", "motif", "citable", "mention"}
    assert "documents" not in j["lecture"]


def test_sans_document_l_absence_est_dite_au_lieu_d_etre_comblee(client):
    """L'ABSENCE EST UNE RÉPONSE. Sur une base vide — le cas de la recette —
    on doit lire qu'il n'y a rien, et non un document rapproché de force."""
    r = client.post("/api/datacenter/lacune/liquide", headers=H, json={})
    j = r.get_json()
    if j["interne"]["n"] == 0:
        assert not j["lecture"]["texte"], (
            "rien à lire, donc rien ne doit être écrit")
        assert j["lecture"]["motif"], "et le motif doit le dire"


def test_le_document_trouve_porte_sa_provenance(tmp_path, monkeypatch):
    """CE QUI REND LE REGISTRE 1 CITABLE : un titre et un thème. Sans eux, ce
    ne serait qu'un extrait anonyme — exactement ce qu'on reproche au modèle."""
    import app
    import rag_store as R
    os.environ["RAG_MEMORY_FILE"] = str(tmp_path / "rag.json")
    m = R.MemoryRagStore(reason="recette")
    m._docs, m._chunks, m._blobs = {}, {}, {}
    m.ingest_bytes(
        "wue.txt",
        ("Relevés d'exploitation : le WUE mesuré sur nos installations "
         "européennes en refroidissement évaporatif, water usage effectiveness "
         "par climat et par saison, consommation d'eau annuelle.").encode("utf-8"),
        title="Relevés WUE Europe",
        theme="Data center / Eau & stress hydrique")
    monkeypatch.setattr(app, "rag", m)

    _assurer_admin()
    c = app.app.test_client()
    with c.session_transaction() as s:
        s["user_email"] = ADMIN_EMAIL
    j = c.post("/api/datacenter/lacune/wue", headers=H,
               json={"lecture": False}).get_json()
    assert j["interne"]["n"] >= 1, j["interne"]
    d = j["interne"]["documents"][0]
    assert d["titre"], "un extrait sans titre n'est pas citable"
    assert d["theme"], "ni sans thème"
    assert d["extrait"], "et il faut de quoi juger sur pièce"


def test_les_extraits_arrivent_clos_au_modele():
    """Un document empoisonné versé à la base ne doit pas ressortir avec ses
    consignes intactes par CE chemin-là non plus. La route passe par
    build_context, qui clôt — on le vérifie sur la route, pas sur le module."""
    src = open(os.path.join(ICI, "app.py"), encoding="utf-8").read()
    i = src.index('def api_datacenter_lacune(')
    bloc = src[i:i + 4200]
    assert "build_context" in bloc
    assert "prompt_lecture" in bloc
    assert bloc.index("build_context") < bloc.index("assistant.generate")


def test_la_lecture_indisponible_ne_prive_pas_des_documents():
    """Faire dépendre le registre CITABLE de la disponibilité du modèle serait
    perdre le solide pour l'accessoire."""
    src = open(os.path.join(ICI, "app.py"), encoding="utf-8").read()
    i = src.index('def api_datacenter_lacune(')
    bloc = src[i:i + 4600]
    j = bloc.index("assistant.generate")
    assert "except Exception" in bloc[j:j + 400]
    assert "se citent tels quels" in bloc[j:j + 900]


# ── 5. La page : le registre se voit avant qu'on recopie ───────────────────

def test_la_page_pose_un_bouton_par_lacune():
    h = page()
    assert "data-lac-go" in h
    assert "/api/datacenter/lacune/" in h


def test_la_page_distingue_les_trois_registres():
    h = page()
    for c in ("dc-reg citable", "dc-reg lecture", "dc-reg gisement"):
        assert c in h, c


def test_la_page_etiquette_ce_qui_se_cite_et_ce_qui_ne_se_cite_pas():
    """Un lecteur qui recopie dans un dossier doit le voir d'un coup d'œil, pas
    le déduire d'une couleur."""
    h = page()
    assert ">citable<" in h
    assert ">non citable<" in h
    assert ">non consulté<" in h


def test_la_couleur_ne_porte_pas_seule_le_registre():
    """Trois teintes qui distinguent seules seraient perdues pour un lecteur
    daltonien, et sur un tirage en noir et blanc."""
    h = page()
    i = h.index(".dc-reg.citable")
    assert "dc-reg-b" in h, "chaque registre porte une étiquette en toutes lettres"
    assert h.index("1 · Dans les documents du cabinet") > 0
    assert h.index("2 · Lecture assistée") > 0
    assert h.index("3 · Où chercher hors du cabinet") > 0
    assert i > 0
