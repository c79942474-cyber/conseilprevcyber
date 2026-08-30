"""Les six axes de la veille, et ce qu'ils ont le droit d'affirmer.

CE QUI EST REMPLACÉ. La page classait par mots-clés dans son propre script :
« Microsoft & Windows », « Linux & Unix », « Bases de données », « Mobile ».
Ce sont les facettes d'un flux de VULNÉRABILITÉS — elles disent quel produit est
touché — et elles n'ont aucun sens devant un communiqué de la Commission ou une
révision de norme ISO.

CE QUI NE DOIT PAS ÊTRE RÉÉCRIT. Thèmes et standards viennent du vocabulaire de
la base documentaire ; les secteurs, de la page qui les publie. Deux
vocabulaires pour une seule maison, et c'est l'exemplaire qu'on oublie de
corriger qui reste en place — muet, puisqu'un filtre qui ne désigne rien ne
lève aucune erreur.
"""
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import automation                                                   # noqa: E402
import rag_store                                                    # noqa: E402
import veille_facettes as vf                                        # noqa: E402
import veille_sources                                               # noqa: E402


def _item(titre, resume="", source="certfr_avis"):
    return {"title": titre, "resume": resume, "source": source,
            "link": "https://x", "published": 0, "guid": titre}


# ── 1. Un seul vocabulaire pour toute la maison ────────────────────────────

def test_tous_les_standards_existent_dans_la_base_documentaire():
    """LA RÈGLE QUI EMPÊCHE DEUX VOCABULAIRES. Un standard nommé ici mais absent
    de `rag_store.THEMES` ferait un filtre de veille qui ne désigne aucun
    document — et rien ne le signalerait."""
    for nom, _ in vf.STANDARDS + vf.THEMES:
        assert nom in rag_store.THEMES, nom


def test_les_secteurs_sont_exactement_ceux_de_la_page_secteurs():
    """Un nom écrit à deux endroits finit toujours par diverger. Ici la
    divergence serait muette : le filtre proposerait un secteur que plus rien
    ne nomme, ou tairait celui qu'on vient d'ajouter à la page."""
    html = open(os.path.join(ICI, "secteurs.html"), encoding="utf-8").read()
    page = [re.sub(r"<[^>]*>", "", h).replace("&amp;", "&").strip()
            for h in re.findall(r"<h3[^>]*>.*?</h3>", html, re.S)]
    assert [n for n, _ in vf.SECTEURS] == page


# ── 2. Le pays est un fait, pas une déduction ──────────────────────────────

def test_le_pays_vient_de_l_emetteur_pas_du_texte():
    """Un communiqué de la Commission qui cite le Japon reste européen.

    Deviner le pays d'après une mention du texte donnerait un filtre qui range
    l'actualité européenne sous le pays qu'elle commente — et une facette bâtie
    sur une supposition trompe davantage qu'une facette absente.
    """
    it = _item("La Commission européenne examine les règles japonaises et américaines",
               "Japon, États-Unis, Royaume-Uni.", source="ec_numerique")
    assert vf.classer(it)["pays"] == "UE"


def test_le_meme_texte_change_de_pays_avec_sa_source():
    """Le pendant : si le pays ne suivait pas la source, la règle précédente
    resterait verte avec un pays constant."""
    titre = "Nouvelles lignes directrices sur la sécurité industrielle"
    assert vf.classer(_item(titre, source="certfr_avis"))["pays"] == "FR"
    assert vf.classer(_item(titre, source="cisa_ics"))["pays"] == "US"
    assert vf.classer(_item(titre, source="ncsc_uk"))["pays"] == "UK"


def test_un_element_dont_la_source_a_disparu_reste_affichable():
    """On ne fait pas disparaître de la page ce qui a été collecté hier parce
    qu'une clé a été renommée aujourd'hui."""
    enrichis = vf.enrichir([_item("Titre", source="flux_supprime")])
    assert len(enrichis) == 1
    assert enrichis[0]["facettes"]["pays"] is None
    assert enrichis[0]["emetteur"]


# ── 3. Ce qui est reconnu, et ce qui ne l'est pas ──────────────────────────

def test_un_element_non_classe_reste_dans_la_liste():
    """Les facettes FILTRENT quand on les demande ; elles ne trient pas en
    amont. Un communiqué que nos motifs ne savent pas lire est exactement celui
    qu'il ne faut pas cacher."""
    enrichis = vf.enrichir([_item("Communiqué", "Texte sans aucun mot connu.",
                                  source="oecd_ai")])
    f = enrichis[0]["facettes"]
    assert enrichis and f["themes"] == [] and f["standards"] == []
    assert f["secteurs"] == [] and f["entreprises"] == []


def test_les_quatre_sujets_demandes_sont_reconnus():
    cas = [
        ("Nouvelle version de la norme IEC 62443-3-3 pour les systèmes SCADA",
         "standards", "IEC 62443"),
        ("Le règlement européen sur l'IA entre en application",
         "standards", "AI Act"),
        ("DORA : l'EBA publie ses normes techniques de résilience",
         "standards", "DORA"),
        ("Les centres de données devront publier leur PUE et leur WUE",
         "themes", "Data center / Efficacité & indicateurs (PUE, WUE, CUE, ERE)"),
    ]
    for titre, axe, attendu in cas:
        assert attendu in vf.classer(_item(titre))[axe], titre


def test_une_entreprise_citee_est_reconnue():
    f = vf.classer(_item("Siemens corrige une faille dans SIMATIC ; Schneider suit"))
    assert "Siemens" in f["entreprises"] and "Schneider Electric" in f["entreprises"]


def test_l_axe_reglementaire_se_fonde_d_abord_sur_l_emetteur():
    """Un communiqué de la CNIL est réglementaire parce qu'il vient de la CNIL,
    pas parce qu'il contient un mot."""
    assert vf.classer(_item("Bilan annuel", source="cnil"))["reglementaire"] is True
    assert vf.classer(_item("Bilan annuel", source="dcd"))["reglementaire"] is False
    # …mais un texte de presse qui annonce un acte normatif l'est aussi.
    assert vf.classer(_item("La directive entre en vigueur au 1er janvier",
                            source="dcd"))["reglementaire"] is True


def test_les_facettes_sont_comptees_et_ordonnees():
    """TROIS STANDARDS D'EFFECTIFS DIFFÉRENTS, ET C'EST LE POINT.

    La première version de cette règle n'en produisait qu'un : la liste des
    effectifs valait `[2]`, triée quoi qu'il arrive. Elle a survécu à la
    suppression du tri — elle ne l'éprouvait pas. Une liste déroulante se lit du
    haut : l'ordre est la moitié de son utilité.
    """
    items = vf.enrichir([
        _item("IEC 62443 et SCADA", source="certfr_avis"),
        _item("IEC 62443 en pratique", source="cisa_ics"),
        _item("IEC 62443 et NIS2", source="enisa"),
        _item("NIS2 : la transposition avance", source="cnil"),
        _item("Le règlement DORA s'applique", source="eba"),
        _item("PUE des centres de données", source="dcd"),
    ])
    fa = vf.facettes(items)
    standards = {x["valeur"]: x["n"] for x in fa["standards"]}
    assert standards.get("IEC 62443") == 3
    assert standards.get("NIS2") == 2
    assert standards.get("DORA") == 1
    assert {x["valeur"] for x in fa["pays"]} == {"FR", "US", "UE", "monde"}
    # Les plus fréquents d'abord.
    effectifs = [x["n"] for x in fa["standards"]]
    assert effectifs == sorted(effectifs, reverse=True), effectifs
    assert fa["standards"][0]["valeur"] == "IEC 62443"


# ── 4. Le coût des résumés ─────────────────────────────────────────────────

class _Compteur:
    def __init__(self):
        self.appels = 0

    def __call__(self, titre, description):
        self.appels += 1
        return "résumé " + titre


@pytest.fixture
def deux_flux(monkeypatch):
    """Deux sources seulement : les règles portent sur le comportement, pas sur
    la taille du catalogue du jour."""
    monkeypatch.setattr(veille_sources, "SOURCES", [
        veille_sources.source("certfr_avis"), veille_sources.source("cisa_ics")])
    veille_sources.reinitialiser()
    yield
    veille_sources.reinitialiser()


def _flux(url):
    marque = url.rsplit("/", 2)[-2]
    return """<?xml version="1.0"?><rss version="2.0"><channel>
      <item><guid>%s-1</guid><title>Un avis</title><link>https://x/1</link>
      <pubDate>Tue, 26 Aug 2026 11:12:00 +0200</pubDate>
      <description>Chapeau publié par la source.</description></item>
      <item><guid>%s-2</guid><title>Un autre avis</title><link>https://x/2</link>
      <pubDate>Tue, 26 Aug 2026 12:12:00 +0200</pubDate>
      <description>Second chapeau.</description></item>
    </channel></rss>""" % (marque, marque)


def test_resumes_eteints_aucun_appel_au_modele(deux_flux, monkeypatch):
    """LA RÈGLE QUI PROTÈGE LE BUDGET. Chaque élément déclenchait un appel ; sur
    une trentaine de flux mondiaux, c'est l'actualité du monde entier prélevée
    sur le budget qui sert AUSSI à rédiger les livrables."""
    compteur = _Compteur()
    monkeypatch.setattr(automation, "VEILLE_RESUME", False)
    automation.init(summarize=compteur, start=False)
    nouveaux = automation.veille_refresh(fetcher=_flux)
    assert nouveaux == 4, "les éléments doivent bien être collectés"
    assert compteur.appels == 0
    # …et ce qui s'affiche est le chapeau de la source, pas un vide.
    assert automation.veille_list(limit=4)[0]["resume"]


def test_resumes_allumes_le_plafond_par_passage_est_tenu(deux_flux, monkeypatch):
    compteur = _Compteur()
    monkeypatch.setattr(automation, "VEILLE_RESUME", True)
    monkeypatch.setattr(automation, "VEILLE_RESUME_MAX", 3)
    automation.init(summarize=compteur, start=False)
    automation.veille_refresh(fetcher=_flux)
    assert compteur.appels == 3, "quatre éléments, trois appels : le plafond tient"


def test_au_dela_du_plafond_l_element_garde_le_chapeau_de_sa_source(deux_flux, monkeypatch):
    """Le plafond ne doit pas faire disparaître les éléments suivants — sinon
    borner la dépense bornerait aussi la veille."""
    monkeypatch.setattr(automation, "VEILLE_RESUME", True)
    monkeypatch.setattr(automation, "VEILLE_RESUME_MAX", 1)
    automation.init(summarize=_Compteur(), start=False)
    assert automation.veille_refresh(fetcher=_flux) == 4
    assert all(i["resume"] for i in automation.veille_list(limit=4))


def test_la_collecte_note_la_sante_de_chaque_flux(deux_flux):
    automation.init(start=False)
    automation.veille_refresh(fetcher=_flux)
    par_cle = {l["cle"]: l for l in veille_sources.etat()["sources"]}
    assert par_cle["certfr_avis"]["elements"] == 2
    assert par_cle["cisa_ics"]["sante"] == "ok"


def test_un_flux_illisible_est_compte_comme_muet_pas_ignore(deux_flux):
    """Une adresse qui rend une page d'accueil au lieu d'un flux : le lecteur
    n'en tire rien, rien ne lève, et sans ce comptage la source disparaîtrait
    de la page sans que personne ne le sache."""
    automation.init(start=False)
    automation.veille_refresh(fetcher=lambda url: "<html><body>Bienvenue</body></html>")
    par_cle = {l["cle"]: l for l in veille_sources.etat()["sources"]}
    assert par_cle["certfr_avis"]["elements"] == 0
    assert par_cle["certfr_avis"]["sante"] == "jamais_joint"
