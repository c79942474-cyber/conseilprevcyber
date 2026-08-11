"""Data Center Sustainability & Decarbonisation — le cadre, et la frontière.

CE QUI A CHANGÉ. La page /datacenter portait un moteur de calcul et rien
d'autre. Un moteur répond à « combien » ; il ne répond jamais à « qu'est-ce
qu'on vise, comment le prouve-t-on, qui l'atteste » — les trois questions qui
font une démarche de développement durable, et les trois sous-dossiers que la
base documentaire range sous « Data center / Green Management ». La page les
porte désormais, et elle s'est OUVERTE.

CE QUE CES TESTS PROTÈGENT, ET LE SECOND POINT COMPTE AUTANT QUE LE PREMIER :

  1. LE CADRE NE PEUT PAS DÉRIVER DE LA BASE. Les trois axes citent des thèmes
     par leur nom. Un sous-dossier renommé — ou un QUATRIÈME ajouté — laisserait
     une page pointer dans le vide, sans erreur et sans trace. Le module refuse
     de se charger dans ce cas ; on le vérifie en cassant la correspondance.

  2. LA FRONTIÈRE OUVERT / FERMÉ. Ouvrir le calcul est voulu : il est
     déterministe, sans modèle de langage, sans écriture, et rien de ce qu'il
     produit n'appartient à un client. Ouvrir les PIÈCES ne l'est pas : ce sont
     les documents de travail du cabinet et de ses clients. Un test vérifie donc
     les deux sens — ce qui doit s'ouvrir s'ouvre, ce qui doit rester fermé le
     reste.

  3. LE CADRE NE PROMET PAS CE QUE LE MOTEUR NE PRODUIT PAS. Chaque axe annonce
     des grandeurs par leur CLÉ dans le résultat. Elles sont confrontées à une
     étude réelle : une clé annoncée et absente serait une promesse creuse.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import datacenter as dc  # noqa: E402
import durabilite as du  # noqa: E402
import rag_store  # noqa: E402
import app as A  # noqa: E402

PROFIL = {"puissance_it_kw": 50000, "pays": "FR",
          "refroidissement": "tour_evaporative", "taux_charge": 0.65}


@pytest.fixture
def client():
    """CONNECTÉ — depuis que la page demande un compte, un client anonyme ne
    mesurerait plus que la porte. La porte, elle, est éprouvée par les
    contrôles qui prennent la fixture `anonyme`."""
    A.app.config["TESTING"] = True
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["user_email"] = "recette@local.test"
    return c


# ── 1. Le cadre colle à la base documentaire ───────────────────────────────

def test_trois_axes_pour_trois_sous_dossiers():
    sous = [t for t in rag_store.THEMES
            if t.startswith(du.RACINE_VERTE + " / ")]
    assert len(sous) == 3
    assert len(du.AXES) == 3
    assert {a["theme"] for a in du.AXES} == set(sous)


def test_chaque_axe_cite_un_theme_qui_existe():
    connus = set(rag_store.THEMES)
    for a in du.AXES:
        assert a["theme"] in connus, a["theme"]


def test_le_module_refuse_un_theme_disparu(monkeypatch):
    """LE contrôle : un sous-dossier renommé doit FAIRE TOMBER le module, pas
    laisser la page pointer dans le vide."""
    amputes = [t for t in rag_store.THEMES
               if t != du.AXES[0]["theme"]]
    monkeypatch.setattr(rag_store, "THEMES", amputes)
    fautes = du._verifier()
    assert fautes, "un thème disparu n'a pas été détecté"
    assert any("thème absent" in f for f in fautes), fautes


def test_le_module_refuse_un_quatrieme_sous_dossier_non_repris(monkeypatch):
    """L'oubli inverse, et il est plus sournois : la base grandit, la page
    continue d'annoncer trois axes et en tait un."""
    monkeypatch.setattr(rag_store, "THEMES",
                        list(rag_store.THEMES)
                        + [du.RACINE_VERTE + " / Eau & biodiversité"])
    fautes = du._verifier()
    assert fautes
    assert any("sous-dossiers verts" in f for f in fautes), fautes


def test_la_sante_est_verte_en_etat_normal():
    assert du.sante()["problemes"] == []


# ── 2. Le cadre ne promet que ce que le moteur produit ─────────────────────

def test_toutes_les_grandeurs_annoncees_existent_dans_une_etude_reelle():
    etude = dc.etude(PROFIL)
    creuses = []
    for a in du.cadre(etude)["axes"]:
        creuses += [x["cle"] for x in a["calcule"] if not x["present"]]
    assert not creuses, "clés annoncées et absentes du résultat : %s" % creuses


def test_chaque_axe_dit_aussi_ce_qu_il_ne_calcule_pas():
    """Un cadre qui ne dit que ses forces est une plaquette."""
    for a in du.AXES:
        assert len(a["non_calcule"]) > 60, a["cle"]


def test_chaque_axe_cite_des_textes_avec_leur_portee():
    for a in du.AXES:
        assert a["textes"], a["cle"]
        for t in a["textes"]:
            assert t["nom"] and t["porte"]


def test_le_cadre_sans_etude_ne_pretend_rien_verifier():
    """Sans étude, « present » vaut None — pas False, qui accuserait à tort, ni
    True, qui affirmerait sans avoir regardé."""
    for a in du.cadre()["axes"]:
        for x in a["calcule"]:
            assert x["present"] is None


# ── 3. La frontière ouvert / fermé ─────────────────────────────────────────

# CE QUI DEMANDE UN COMPTE — la liste s'appelait « OUVERTS » et disait le
# contraire de la politique actuelle. La renommer était le minimum : un nom qui
# ment se relit sans qu'on le voie.
CLIENT_GET = ["/datacenter", "/api/datacenter/durabilite",
              "/api/datacenter/referentiel"]
FERMES_POST = ["/api/datacenter/profil",
               "/api/datacenter/ingenierie/parcours",
               "/api/datacenter/ingenierie/dossier",
               "/api/datacenter/ingenierie/export"]


@pytest.mark.parametrize("chemin", CLIENT_GET)
def test_le_client_connecte_y_accede(client, chemin):
    r = client.get(chemin)
    assert r.status_code == 200, (chemin, r.status_code)


@pytest.mark.parametrize("chemin", CLIENT_GET)
def test_ET_LE_VISITEUR_ANONYME_NON(anonyme, chemin):
    """LA MOITIÉ QUI PROTÈGE. Vérifier qu'un client connecté accède ne dit rien
    de ce que voit celui qui n'a pas de compte : c'est le second contrôle, et
    lui seul, qui distingue une page protégée d'une page ouverte."""
    r = anonyme.get(chemin)
    assert r.status_code in (302, 401), (chemin, r.status_code)


def test_le_calcul_lui_meme_sert_le_client_connecte(client):
    r = client.post("/api/datacenter/etude",
                    headers={"Origin": "http://localhost"},
                    json={"puissance_it_kw": 50000, "pays": "FR"})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True


@pytest.mark.parametrize("chemin", FERMES_POST)
def test_ce_qui_doit_rester_ferme_le_reste(anonyme, chemin):
    """LA FIXTURE A CHANGÉ, ET C'EST TOUT LE CONTRÔLE. Ce test prenait
    `client` ; depuis que `client` est connecté, il aurait mesuré ce qu'un
    client atteint — pas ce qu'un inconnu se voit refuser, qui est la seule
    question posée ici."""
    r = anonyme.post(chemin, headers={"Origin": "http://localhost"}, json={})
    assert r.status_code == 401, (chemin, r.status_code)


def test_la_base_documentaire_reste_reservee(connecte):
    """Réservée à l'administrateur : un compte client validé ne l'atteint pas.
    Éprouvé avec un vrai compte de rôle « user » — le compte de recette porte
    le rôle admin, et l'employer ici aurait prouvé l'inverse sans le dire."""
    r = connecte.get("/admin/base-connaissance")
    assert r.status_code in (302, 401, 403), r.status_code


def test_le_calcul_ouvert_est_plafonne():
    """Ouvrir une surface de calcul sans plafond, c'est offrir un
    amplificateur : le limiteur doit couvrir la famille désormais publique."""
    prefixes = [p for p, _, _ in A._RATE_FAMILY]
    assert "/api/datacenter/" in prefixes


# ── 4. Le titre, et ce qu'il ne devait pas perdre ──────────────────────────

def _page():
    with open(os.path.join(ICI, "datacenter.html"), encoding="utf-8") as f:
        return f.read()


def test_le_titre_est_le_nouveau():
    h = _page()
    assert "Data Center Sustainability &amp; Decarbonisation" in h


def test_l_ancien_titre_reste_en_sous_titre():
    """Le nouveau dit le SUJET, l'ancien dit la MÉTHODE. Perdre le second
    rendrait la page indistinguable de n'importe quelle plaquette verte."""
    h = _page()
    assert "Énergie, eau et carbone — calculés ensemble" in h


def test_la_page_ouverte_est_indexable():
    """Elle était `noindex` parce qu'elle était fermée. La laisser ainsi
    reviendrait à l'ouvrir pour personne."""
    h = _page()
    assert 'content="index, follow"' in h
    assert 'content="noindex' not in h
