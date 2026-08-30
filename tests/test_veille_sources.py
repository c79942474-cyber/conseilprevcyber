"""Lire ce que le monde publie, et savoir quand on ne le lit pas.

TROIS DÉFAUTS QUE CES RÈGLES TIENNENT, ET AUCUN NE LEVAIT D'EXCEPTION.

  · Le lecteur n'itérait que sur `item`, la balise de RSS. Un flux **Atom**
    emploie `entry`, dans un espace de noms : la boucle ne trouvait rien et
    rendait une liste vide. Une source américaine entière pouvait manquer à la
    page sans qu'une seule ligne de journal ne le dise.
  · La date était tronquée à vingt-cinq caractères — ce qui COUPE le décalage
    horaire — puis interprétée dans le fuseau du serveur. Invisible sur deux
    flux français ; jusqu'à un jour d'écart sur des sources réparties du Japon à
    la Californie, et une veille se lit par ordre de fraîcheur.
  · Une adresse fausse rend une liste vide exactement comme un flux calme. Sans
    comptage, une veille amputée de sa moitié ressemble à une veille qui va bien.

Le catalogue a été écrit HORS LIGNE : plusieurs adresses seront fausses. Ces
règles ne prétendent donc pas qu'elles répondent — aucune ne touche au réseau.
Elles garantissent que le jour où l'une ne répond pas, cela SE VOIT.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import automation                                                   # noqa: E402
import veille_sources                                               # noqa: E402


ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Flux Atom</title>
  <entry>
    <id>urn:uuid:GUID</id>
    <title>CISA publishes an ICS advisory</title>
    <link rel="alternate" href="https://exemple.gov/avis/1"/>
    <updated>2026-08-26T09:12:00Z</updated>
    <summary>Siemens SIMATIC est concerné.</summary>
  </entry>
</feed>"""

RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel>
  <item><guid>GUID</guid><title>Avis de sécurité</title>
    <link>https://exemple.fr/avis/1</link>
    <pubDate>Tue, 26 Aug 2026 11:12:00 +0200</pubDate>
    <description>Un texte de chapeau.</description></item>
</channel></rss>"""


@pytest.fixture(autouse=True)
def etat_vierge():
    veille_sources.reinitialiser()
    yield
    veille_sources.reinitialiser()


# ── 1. Lire les deux formats du monde des flux ─────────────────────────────

def test_un_flux_atom_rend_des_elements():
    """LA RÈGLE QUI MANQUAIT. Sans elle, un flux Atom rendait zéro élément, en
    silence, et la page affichait simplement moins de choses."""
    items = automation._parse_feed("cisa_ics", ATOM)
    assert len(items) == 1
    assert items[0]["title"] == "CISA publishes an ICS advisory"
    # Atom porte l'adresse en ATTRIBUT : la lire comme du texte rendait une
    # chaîne vide, donc un élément sans lien, donc un élément écarté.
    assert items[0]["link"] == "https://exemple.gov/avis/1"
    assert "SIMATIC" in items[0]["description"]


def test_un_flux_rss_rend_toujours_des_elements():
    """Le pendant : élargir le lecteur ne doit pas casser ce qu'il lisait."""
    items = automation._parse_feed("certfr_avis", RSS)
    assert len(items) == 1 and items[0]["link"] == "https://exemple.fr/avis/1"


def test_le_meme_instant_dans_trois_fuseaux_se_classe_au_meme_rang():
    """LE DÉFAUT QUE DEUX FLUX FRANÇAIS NE POUVAIENT PAS RÉVÉLER.

    11h12 à Paris (+0200), 18h12 à Tokyo (+0900) et 09h12 UTC sont le MÊME
    instant. Une veille se lit par ordre de fraîcheur : les confondre d'un jour
    met en tête ce qui devrait être en bas.
    """
    paris = automation._parse_feed("a", RSS)[0]["published"]
    tokyo = automation._parse_feed("a", RSS.replace(
        "Tue, 26 Aug 2026 11:12:00 +0200", "Tue, 26 Aug 2026 18:12:00 +0900"))[0]["published"]
    utc = automation._parse_feed("a", ATOM)[0]["published"]
    assert paris == tokyo == utc


def test_une_date_sans_fuseau_est_lue_en_temps_universel():
    """La seule lecture honnête d'une date sans fuseau. La lire dans le fuseau
    du serveur ferait dépendre le classement de l'endroit où tourne le site."""
    a = automation._date_en_ms("2026-08-26T09:12:00")
    b = automation._date_en_ms("2026-08-26T09:12:00Z")
    assert a == b


def test_une_date_illisible_ne_fait_pas_disparaitre_l_element():
    """Une date qu'on ne sait pas lire vaut « maintenant » — l'élément reste
    publié. L'écarter perdrait une actualité pour un défaut de format."""
    items = automation._parse_feed("a", RSS.replace(
        "Tue, 26 Aug 2026 11:12:00 +0200", "hier après-midi"))
    assert len(items) == 1 and items[0]["published"] > 0


# ── 2. Un flux muet doit se voir ───────────────────────────────────────────

def test_jamais_joint_ne_se_confond_pas_avec_devenu_muet():
    """LA DISTINCTION QUI ORIENTE LE DIAGNOSTIC. « Jamais joint » désigne une
    adresse à corriger ; « muet » une panne à attendre. Les confondre enverrait
    corriger ce qui marche."""
    veille_sources.noter_succes("cisa_ics", 0)          # a répondu, rien rendu
    veille_sources.noter_succes("certfr_avis", 3)       # a rendu
    for _ in range(veille_sources.MUET_APRES):
        veille_sources.noter_succes("certfr_avis", 0)   # puis s'est tu
    par_cle = {l["cle"]: l for l in veille_sources.etat()["sources"]}
    assert par_cle["cisa_ics"]["sante"] == "jamais_joint"
    assert par_cle["certfr_avis"]["sante"] == "muet"


def test_un_flux_qui_repond_est_sain_et_ne_figure_pas_a_regarder():
    veille_sources.noter_succes("certfr_avis", 12)
    e = veille_sources.etat()
    par_cle = {l["cle"]: l for l in e["sources"]}
    assert par_cle["certfr_avis"]["sante"] == "ok"
    assert par_cle["certfr_avis"]["elements"] == 12
    assert "certfr_avis" not in [l["cle"] for l in e["sources"]
                                 if l["sante"] in ("muet", "jamais_joint")]


def test_un_flux_injoignable_porte_sa_cause():
    veille_sources.noter_echec("iso", "timeout")
    par_cle = {l["cle"]: l for l in veille_sources.etat()["sources"]}
    assert par_cle["iso"]["echecs"] == 1 and "timeout" in par_cle["iso"]["erreur"]


def test_le_catalogue_dit_ce_qui_a_ete_eprouve():
    """Une adresse écrite n'est pas une adresse qui répond. Le catalogue ne doit
    pas laisser croire le contraire — seuls les flux déjà en production sont
    déclarés éprouvés."""
    eprouves = [s["cle"] for s in veille_sources.SOURCES if s["eprouve"]]
    assert set(eprouves) == {"certfr_alerte", "certfr_avis"}


# ── 3. Le droit de reprise, source par source ──────────────────────────────

def test_le_texte_integral_n_est_permis_que_pour_les_sources_officielles():
    """C'est une limite de DROIT, pas de technique : rien n'empêche de
    télécharger un article de presse, mais en reprendre le corps n'est plus de
    l'agrégation."""
    assert veille_sources.texte_integral_permis("certfr_avis") is True
    assert veille_sources.texte_integral_permis("iso") is True
    for cle in ("dcd", "the_record", "iapp", "carbon_brief"):
        assert veille_sources.texte_integral_permis(cle) is False, cle


def test_une_source_inconnue_n_ouvre_aucun_droit():
    assert veille_sources.texte_integral_permis("source_disparue") is False


# ── 4. Le catalogue tient ce qu'il annonce ─────────────────────────────────

def test_chaque_domaine_annonce_a_des_sources():
    """Un filtre qui propose un choix ne rendant jamais rien fait douter de la
    page, pas du choix."""
    for domaine in veille_sources.DOMAINES:
        assert veille_sources.sources(domaine=domaine), domaine


def test_le_catalogue_couvre_les_quatre_sujets_demandes():
    d = {dom: len(veille_sources.sources(domaine=dom))
         for dom in veille_sources.DOMAINES}
    for dom, n in d.items():
        assert n >= 4, "%s ne compte que %d source(s)" % (dom, n)


def test_les_pays_demandes_sont_couverts():
    couverts = {s["pays"] for s in veille_sources.SOURCES}
    for pays in ("FR", "US", "UK", "UE", "monde"):
        assert pays in couverts, pays


def test_la_presse_specialisee_est_reellement_presente():
    """Vous avez demandé d'orienter vers la presse spécialisée : une règle le
    tient, sinon la liste redeviendrait purement institutionnelle au premier
    remaniement."""
    presse = [s for s in veille_sources.SOURCES
              if s["nature"] == "presse_specialisee"]
    assert len(presse) >= 6
    domaines = {s["domaine"] for s in presse}
    assert "centres_donnees" in domaines and "cyber_industriel" in domaines
