"""Trente-six flux entraient, aucun ne sortait.

CE QUI EST PUBLIABLE, ET CE QUI NE L'EST PAS. Les titres et les chapeaux
appartiennent aux éditeurs — on n'en reprend que ce qu'ils mettent eux-mêmes
dans leurs flux pour être repris. Ce qui est À NOUS, c'est LE CLASSEMENT :
domaine, pays de l'émetteur, secteur, standard cité, caractère réglementaire.
C'est un travail original, et c'est la seule chose de ce flux qui ait de la
valeur pour un tiers.

CE QUE CE FLUX N'EST PAS. Ni STIX, ni TAXII, ni MISP : ces formats transportent
des indicateurs de compromission — empreintes, adresses, domaines malveillants.
Ce cabinet collecte de l'actualité réglementaire. Y faire passer une révision de
norme produirait quelque chose qu'aucun consommateur ne saurait exploiter.
"""
import os
import sys
import xml.etree.ElementTree as ET

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import acces                                                       # noqa: E402
import automation                                                  # noqa: E402

NS = "{http://www.w3.org/2005/Atom}"

ELEMENTS = [
    {"guid": "g1", "source": "cisa_ics", "published": 1756000000000,
     "title": "CISA publishes an IEC 62443 advisory for SCADA",
     "link": "https://exemple.gov/a1", "resume": "Siemens SIMATIC concerné."},
    {"guid": "g2", "source": "dcd", "published": 1756000100000,
     "title": "PUE des centres de données européens",
     "link": "javascript:alert(1)", "resume": "Un chapeau."},
]


@pytest.fixture
def flux(anonyme, monkeypatch):
    monkeypatch.setattr(automation, "veille_list", lambda limit=60: list(ELEMENTS))
    r = anonyme.get("/veille.xml")
    assert r.status_code == 200
    return r


def _entrees(flux):
    return ET.fromstring(flux.get_data()).findall(NS + "entry")


# ── 1. Un flux, donc lisible par une machine et sans compte ───────────────

def test_le_flux_est_ouvert_et_declare_comme_tel():
    """Un flux dont il faut un compte n'est pas un flux. La politique d'accès
    le déclare, et le contrôle au démarrage refuse toute divergence."""
    assert "/veille.xml" in acces.HORS_MENU_OUVERT


def test_le_flux_est_un_atom_bien_forme(flux):
    assert flux.headers["Content-Type"].startswith("application/atom+xml")
    racine = ET.fromstring(flux.get_data())
    assert racine.tag == NS + "feed"
    assert racine.find(NS + "id") is not None
    assert racine.find(NS + "updated") is not None


def test_robots_annonce_le_flux(anonyme):
    assert "/veille.xml" in anonyme.get("/robots.txt").get_data(as_text=True)


# ── 2. Ce qui fait la valeur du flux : le classement ──────────────────────

def test_chaque_entree_porte_nos_facettes_avec_leur_schema(flux):
    """SANS `scheme`, « FR » et « DORA » tomberaient dans le même sac et
    l'abonné ne pourrait plus filtrer sur un axe. C'est le mécanisme prévu par
    le format pour exactement cela."""
    e = _entrees(flux)[0]
    cats = {(c.get("scheme"), c.get("term")) for c in e.findall(NS + "category")}
    assert ("pays", "US") in cats
    assert ("standard", "IEC 62443") in cats
    assert ("domaine", "cyber_industriel") in cats
    assert ("entreprise", "Siemens") in cats
    assert ("nature", "reglementaire") in cats


def test_l_emetteur_est_nomme_comme_auteur(flux):
    """Le titre vient de l'éditeur : le flux doit dire de qui, sans quoi il
    s'attribuerait un texte qui n'est pas le sien."""
    e = _entrees(flux)[0]
    assert (e.find(NS + "author/" + NS + "name").text or "").strip()


def test_chaque_entree_renvoie_a_sa_source(flux):
    liens = _entrees(flux)[0].findall(NS + "link")
    assert [l.get("href") for l in liens] == ["https://exemple.gov/a1"]


# ── 3. Ce que le flux ne doit jamais laisser sortir ───────────────────────

def test_aucune_adresse_executable_ne_sort_du_flux(flux):
    """La garde est posée à l'entrée (`enrichir`) ; cette règle vérifie qu'elle
    tient jusqu'à la SORTIE. Un abonné qui reçoit `javascript:` dans un lecteur
    de flux court le même risque que sur la page."""
    assert b"javascript:" not in flux.get_data()


def test_une_entree_sans_adresse_est_publiee_SANS_LIEN_et_non_omise(flux):
    """Faire disparaître l'actualité par-dessus le marché priverait l'abonné de
    l'information ET de la raison de son absence."""
    entrees = _entrees(flux)
    assert len(entrees) == len(ELEMENTS), "une entrée a disparu"
    assert _entrees(flux)[1].findall(NS + "link") == []
    assert (entrees[1].find(NS + "title").text or "").strip()


def test_le_flux_repond_meme_quand_la_veille_est_muette(anonyme, monkeypatch):
    """Un flux qui rendrait une erreur ferait désabonner les agrégateurs, et le
    jour où la collecte repart personne ne revient."""
    def _casse(limit=60):
        raise RuntimeError("magasin absent")
    monkeypatch.setattr(automation, "veille_list", _casse)
    r = anonyme.get("/veille.xml")
    assert r.status_code == 200
    assert ET.fromstring(r.get_data()).tag == NS + "feed"
