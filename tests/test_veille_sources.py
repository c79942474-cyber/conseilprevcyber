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

# LES SEULES SOURCES DONT ON REPRENDRA LE CORPS. La liste est écrite ici EN
# ENTIER, et c'est délibéré : c'est une autorisation, et une autorisation ne se
# déduit pas d'un champ qu'on pourrait changer par mégarde. Faire entrer une
# source dans cet ensemble demande de toucher cette règle — donc de le vouloir.
#
# La première version de cette règle ne citait que six clés choisies à la main.
# Une mutation a reclassé « France Datacenter » en source officielle — ce qui
# lui ouvrait le droit de reprise — et la règle est restée verte : elle ne
# regardait pas cette source-là. Une autorisation vérifiée par échantillon
# n'est pas vérifiée.
REPRISE_AUTORISEE = {
    "certfr_alerte", "certfr_avis", "anssi", "cisa_avis", "cisa_ics",
    "ncsc_uk", "enisa", "cnil", "ec_numerique", "nist", "ico_uk",
    "iso", "iec", "nist_csrc", "eba", "esma", "edpb", "iea", "cre",
    "ademe", "rte",
}


def test_le_texte_integral_n_est_permis_qu_aux_sources_institutionnelles():
    """C'est une limite de DROIT, pas de technique : rien n'empêche de
    télécharger un article de presse, mais en reprendre le corps n'est plus de
    l'agrégation. La règle porte sur LE CATALOGUE ENTIER."""
    permises = {s["cle"] for s in veille_sources.SOURCES
                if veille_sources.texte_integral_permis(s["cle"])}
    assert permises == REPRISE_AUTORISEE, (
        "reprise ouverte à tort : %s ; refusée à tort : %s"
        % (sorted(permises - REPRISE_AUTORISEE),
           sorted(REPRISE_AUTORISEE - permises)))


def test_aucune_redaction_ne_figure_parmi_les_sources_reprises():
    """Le pendant, dit dans l'autre sens : tout ce qui est une rédaction — ou
    une association professionnelle — reste au titre, au lien et au chapeau."""
    for cle in ("dcd", "dcf", "dck", "the_record", "iapp", "carbon_brief",
                "securityweek_ics", "industrial_cyber", "dcmag", "lemagit_dc",
                "lmi_dc", "france_datacenter", "uptime", "oecd_ai",
                "green_software"):
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


# ── 5. Ce qu'un catalogue qui grossit fait au planificateur ────────────────

def test_les_sources_francaises_de_la_filiere_sont_au_catalogue():
    """Ce sont elles qui couvrent ce qui se décide EN FRANCE — implantations,
    raccordements, investissements européens dans le calcul pour l'IA."""
    cles = {s["cle"] for s in veille_sources.SOURCES}
    for cle in ("dcmag", "lemagit_dc", "lmi_dc", "france_datacenter"):
        assert cle in cles, cle
    fr = [s for s in veille_sources.sources(domaine="centres_donnees")
          if s["pays"] == "FR"]
    assert len(fr) >= 6


def test_l_ordre_de_passage_commence_par_la_moins_recemment_interrogee():
    """SANS CET ORDRE, LA QUEUE DU CATALOGUE NE SERAIT JAMAIS LUE.

    Un passage borné par son budget qui repartirait toujours du début lirait
    éternellement les mêmes premières sources. Les dernières ne remonteraient
    aucune erreur : elles seraient simplement absentes de la page.
    """
    veille_sources.noter_succes("certfr_avis", 3)      # interrogée à l'instant
    ordre = [s["cle"] for s in veille_sources.ordre_de_passage()]
    assert ordre[-1] == "certfr_avis"
    assert len(ordre) == len(veille_sources.SOURCES)


def test_aucune_source_n_est_laissee_de_cote_sur_plusieurs_passages():
    """La propriété qui compte : à budget serré, ce qui est sauté aujourd'hui
    passe EN TÊTE demain. On simule des passages de trois sources chacun et on
    vérifie que le catalogue entier finit par être vu."""
    vues = set()
    par_passage = 3
    for _ in range(len(veille_sources.SOURCES) // par_passage + 2):
        for src in veille_sources.ordre_de_passage()[:par_passage]:
            veille_sources.noter_succes(src["cle"], 1)
            vues.add(src["cle"])
    assert vues == {s["cle"] for s in veille_sources.SOURCES}


def test_un_passage_lent_s_arrete_a_son_budget(monkeypatch):
    """CE QUE LA COLLECTE NE DOIT PAS FAIRE : bloquer le planificateur.

    `_loop` appelle les travaux l'un après l'autre dans un seul fil. Un passage
    de veille qui durerait douze minutes retarderait d'autant le rebranchement
    de la base — prévu toutes les trois minutes précisément pour qu'une base
    revenue soit reprise sans que personne n'attende.
    """
    import time as _time
    monkeypatch.setattr(automation, "VEILLE_BUDGET_S", 1)
    appels = []

    def _lent(url):
        appels.append(url)
        _time.sleep(0.35)
        return "<rss version='2.0'><channel></channel></rss>"

    automation.init(start=False)
    debut = _time.time()
    automation.veille_refresh(fetcher=_lent)
    duree = _time.time() - debut
    assert len(appels) < len(veille_sources.SOURCES), "le budget n'a rien borné"
    assert duree < 10, "le passage a duré %.1f s malgré son budget" % duree


# ═══════════════════════════════════════════════════════════════════════════
#  UNE RÉPONSE QUI N'EST PAS UN FLUX N'EST PAS UNE MOISSON NULLE
# ═══════════════════════════════════════════════════════════════════════════
#
# CE QUI S'EST RÉELLEMENT PASSÉ EN PRODUCTION, et qui a motivé ces règles. La
# page de veille n'affichait rien. La collecte tournait pourtant : elle allait
# au bout de ses trente-six sources en dix-sept secondes sur un budget de cent
# quatre-vingts, sans être interrompue. Seize sources rendaient une erreur HTTP
# — 404 après redirection, ou 403 d'un pare-feu applicatif. LES VINGT AUTRES
# RÉPONDAIENT 200 SANS RIEN RENDRE, et ce cas-là était enregistré comme une
# RÉUSSITE à zéro élément.
#
# Deux états qui appellent deux gestes opposés se retrouvaient donc sous le
# même libellé : « ce flux n'a rien publié cette semaine », qui demande
# d'attendre, et « cette adresse ne sert pas un flux », qui demande de la
# corriger. Les confondre revient à attendre indéfiniment une correction que
# personne ne sait devoir faire — c'est exactement ce qui s'est produit.

import automation as _auto                                        # noqa: E402


def test_une_page_html_qui_repond_200_nest_pas_un_flux():
    """LE CAS EXACT DE LA PRODUCTION. Un pare-feu applicatif sert une page
    d'attente avec un code 200. Elle est parfois du XML parfaitement valide —
    donc le lecteur ne lève RIEN — et elle ne contient ni `item` ni `entry` :
    zéro élément, zéro erreur, zéro trace.
    """
    attente = ("<html><head><title>Just a moment...</title></head>"
               "<body><div id='cf'>Verifying you are human.</div></body></html>")
    # Le témoin qui donne son sens au reste : cette page se parse SANS erreur.
    import xml.etree.ElementTree as ET
    ET.fromstring(attente)                       # ne lève pas — c'est le piège
    assert _auto._parse_feed("x", attente) == [], (
        "le lecteur ne doit rien tirer d'une page d'attente")
    assert _auto._pourquoi_pas_un_flux(attente), (
        "une page d'attente qui répond 200 doit être reconnue comme n'étant "
        "PAS un flux — sans quoi elle passe pour un flux sans nouveauté")


def test_un_vrai_flux_vide_reste_un_succes():
    """LA SYMÉTRIE, ET C'EST ELLE QUI REND LA RÈGLE UTILE. Un flux qui n'a
    rien publié cette semaine est un flux EN BONNE SANTÉ. Le refuser ferait
    signaler une adresse à corriger là où il n'y a rien à corriger, et userait
    l'alerte là où elle est méritée.
    """
    for vide in ('<rss version="2.0"><channel><title>t</title></channel></rss>',
                 '<feed xmlns="http://www.w3.org/2005/Atom"><title>t</title></feed>'):
        assert _auto._pourquoi_pas_un_flux(vide) is None, (
            "un flux authentique et vide doit rester un succès : %s" % vide[:40])
        assert _auto._parse_feed("x", vide) == []


def test_le_collecteur_compte_un_echec_et_non_une_moisson_nulle(monkeypatch):
    """LA PROPRIÉTÉ, MESURÉE SUR LE COLLECTEUR ET NON SUR LE DISCRIMINANT.
    Vérifier la fonction seule ne dirait pas si le collecteur s'en sert : c'est
    au bout de la chaîne que l'état d'une source se décide.
    """
    import veille_sources as VS
    VS.reinitialiser()
    _auto.init(dsn=None, start=False)
    _auto.veille_refresh(fetcher=lambda url: "<html><body>rien</body></html>")
    lignes = {l["cle"]: l for l in VS.etat()["sources"]}
    sains = [c for c, l in lignes.items() if l["sante"] == "ok"]
    assert not sains, (
        "%d source(s) passent pour saines alors qu'aucune n'a servi de flux : "
        "%s" % (len(sains), sains[:5]))
    assert all(l["erreur"] for l in lignes.values()), (
        "une source qui n'a pas servi de flux doit porter la RAISON, sinon "
        "l'exploitant voit un tableau vide et ne sait pas quoi corriger")


def test_le_collecteur_de_flux_annonce_ce_qu_il_vient_chercher():
    """QUATRE 403 VENAIENT DE SITES QUI PUBLIENT POURTANT EN LIBRE ACCÈS —
    CISA, IEA, IEC, SecurityWeek. Un agent qui ne déclare pas ce qu'il accepte
    est ce qu'un pare-feu applicatif écarte en premier.

    La règle borne DEUX propriétés, et pas la chaîne exacte : l'agent doit
    nommer la maison — se faire passer pour un navigateur empêcherait un
    éditeur de nous joindre ou de nous limiter proprement — et il doit annoncer
    qu'il vient chercher un flux.
    """
    e = _auto._ENTETES_FLUX
    ua = e.get("User-Agent", "")
    assert "conseilprevcyber" in ua.lower(), (
        "le collecteur doit se nommer : %r" % ua)
    accept = e.get("Accept", "")
    assert "rss" in accept and "atom" in accept, (
        "le collecteur doit annoncer qu'il attend un flux, pas n'importe quoi "
        ": %r" % accept)


def test_ne_pas_avoir_repondu_et_avoir_repondu_autre_chose_ne_se_comptent_pas_pareil():
    """« ON NE SAIT PAS » N'EST PAS « ON SAIT QUE C'EST ZÉRO », et une première
    version de ce correctif confondait les deux — c'est une règle existante qui
    l'a relevé, en exigeant un compte de 0 là où je laissais None.

    Une adresse qui ne répond pas (404, 403, coupure) ne fournit AUCUNE mesure :
    le compte doit rester None. Une adresse qui répond autre chose qu'un flux
    en fournit une, et elle vaut zéro. Un tableau qui écrirait « — » dans les
    deux cas ferait chercher une panne réseau là où l'adresse est simplement
    fausse.
    """
    import veille_sources as VS
    cle = VS.SOURCES[0]["cle"]

    VS.reinitialiser()
    VS.noter_echec(cle, "404 Not Found")
    muet = {l["cle"]: l for l in VS.etat()["sources"]}[cle]
    assert muet["elements"] is None, (
        "une adresse qui n'a pas répondu n'a fourni aucun compte : %r"
        % muet["elements"])

    VS.reinitialiser()
    VS.noter_echec(cle, "la racine est <html>", a_repondu=True)
    repondu = {l["cle"]: l for l in VS.etat()["sources"]}[cle]
    assert repondu["elements"] == 0, (
        "une adresse qui a répondu autre chose qu'un flux a bien été comptée, "
        "et le compte est zéro : %r" % repondu["elements"])

    assert muet["erreur"] and repondu["erreur"], (
        "les deux cas doivent porter leur raison — c'est elle qui dit à "
        "l'exploitant lequel des deux gestes accomplir")
