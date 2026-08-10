"""Les parcours guidés « centres de données », et le profil qui arrive d'ailleurs.

DEUX AJOUTS, ET ILS SE TIENNENT :

  1. LES TROIS PAGES SONT GUIDÉES. Elles tombaient sur le guide générique —
     « utilisez le menu pour naviguer » — alors que ce sont les plus denses du
     site. Un guide générique sur une page complexe est pire qu'aucun guide :
     il fait croire au lecteur qu'il a lu l'aide. Et deux parcours les
     traversent dans l'ordre du projet.

  2. UN PROFIL PEUT ARRIVER D'UNE AUTRE ÉTUDE, par un lien. Il est alors
     VALIDÉ contre les champs réels du moteur, et DÉCLARÉ : un formulaire qui
     se remplit tout seul sans dire d'où viennent ses valeurs laisse le lecteur
     les prendre pour des valeurs par défaut, et il ne les vérifie pas.

Le contrat de ce lien appartient aux DEUX sites : les noms des paramètres sont
les identifiants des champs de ce formulaire-ci, et l'autre site les écrit dans
l'URL. S'ils divergent, le lien continue de fonctionner et ne pré-remplit plus
rien — une panne silencieuse. Les tests ci-dessous figent notre moitié.
"""
import os
import re
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import datacenter as dc  # noqa: E402

PAGES_DC = ["/strategie-durable-datacenter", "/datacenter",
            "/ingenierie-datacenter"]


def _lire(nom):
    with open(os.path.join(ICI, nom), encoding="utf-8") as f:
        return f.read()


# ── 1. Les trois pages sont guidées ────────────────────────────────────────

def test_chaque_page_datacenter_a_son_guide():
    nav = _lire("nav.js")
    for p in PAGES_DC:
        assert 'GUIDES["%s"]' % p in nav, p


def test_aucun_guide_ne_se_contente_du_generique():
    """Un guide qui redirait « utilisez le menu » n'aurait rien apporté."""
    nav = _lire("nav.js")
    for p in PAGES_DC:
        i = nav.index('GUIDES["%s"]' % p)
        bloc = nav[i:i + 2600]
        assert "Utilisez le menu pour naviguer" not in bloc, p
        # Des étapes, des notions et des liens : les trois colonnes du panneau.
        assert bloc.count('", "') > 3, p


def test_les_trois_pages_portent_le_module_de_parcours():
    """Une page sans le module sort du fil au milieu du parcours."""
    for nom in ("strategie-durable-datacenter.html", "datacenter.html",
                "ingenierie-datacenter.html"):
        assert "/parcours.js" in _lire(nom), nom


# ── 2. Les deux parcours traversent les trois pages, dans l'ordre ──────────

def _parcours():
    """Le registre est lu DANS le module, jamais recopié : un parcours ajouté
    ici et absent là-bas testerait un site imaginaire."""
    import json
    import subprocess
    out = subprocess.run(
        ["node", "-e",
         "const m=require('%s/parcours.js');"
         "process.stdout.write(JSON.stringify(m.PARCOURS));" % ICI],
        capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_deux_parcours_client_couvrent_les_trois_pages():
    dcp = [p for p in _parcours() if p["id"].startswith("dc-")]
    assert len(dcp) == 2, [p["id"] for p in dcp]
    for p in dcp:
        urls = [e["url"] for e in p["etapes"]]
        assert set(urls) == set(PAGES_DC), (p["id"], urls)


def test_le_parcours_projet_suit_l_ordre_du_projet():
    """On choisit AVANT de calculer, on calcule AVANT de s'engager. L'ordre
    inverse produit un livrable d'ouverture écrit après coup."""
    p = [x for x in _parcours() if x["id"] == "dc-projet"][0]
    assert [e["url"] for e in p["etapes"]] == PAGES_DC


def test_chaque_etape_dit_quoi_faire_ce_qu_on_gagne_et_le_piege():
    for p in [x for x in _parcours() if x["id"].startswith("dc-")]:
        for e in p["etapes"]:
            for champ in ("action", "gain", "tip"):
                assert len(e[champ]) > 60, (p["id"], e["url"], champ)


def test_les_trois_pages_sont_ponderees_dans_la_table_des_axes():
    """Sans entrée dans AXES_URL, un parcours qui les traverse ne pondère
    rien — et la personnalisation par secteur devient muette."""
    nav = _lire("parcours.js")
    for p in PAGES_DC:
        assert '"%s": [' % p in nav, p


# ── 3. Le profil qui arrive d'un lien ──────────────────────────────────────

def test_les_champs_transmissibles_existent_tous_dans_le_moteur():
    """LE contrat avec l'autre site. Un nom qui n'existe plus ici ne casse pas
    le lien : il le rend silencieusement inopérant."""
    js = _lire("decarbonation-dc.js")
    m = re.search(r'var REPRISE = \[(.*?)\];', js, re.S)
    assert m, "la liste des champs repris est introuvable"
    champs = re.findall(r'"([^"]+)"', m.group(1))
    assert champs, champs
    connus = {c["id"] for c in dc.CHAMPS}
    for cid in champs:
        assert cid in connus, cid


def test_la_reprise_ne_porte_rien_de_nominatif():
    """Une URL se copie et se journalise : le profil technique seul."""
    js = _lire("decarbonation-dc.js")
    m = re.search(r'var REPRISE = \[(.*?)\];', js, re.S)
    champs = re.findall(r'"([^"]+)"', m.group(1))
    for interdit in ("client", "projet", "site", "nom", "email", "societe"):
        assert not any(interdit in c for c in champs), (interdit, champs)


def test_la_page_porte_la_zone_de_declaration():
    """Sans elle, le formulaire se remplirait sans dire d'où viennent ses
    valeurs — et le lecteur les prendrait pour des valeurs par défaut."""
    h = _lire("datacenter.html")
    assert 'id="dc-repris"' in h
    assert "#dc-repris" in h  # le style existe aussi


def test_la_reprise_valide_avant_d_appliquer():
    """Une option inconnue posée dans un menu déroulant donnerait au moteur une
    valeur qu'il ne connaît pas."""
    js = _lire("decarbonation-dc.js")
    assert "refuses" in js
    assert "inconnu du référentiel" in js
    assert "n’est pas un nombre" in js


def test_la_reprise_ne_lance_pas_le_calcul_toute_seule():
    """Un résultat affiché avant que le lecteur n'ait vu ses entrées est un
    résultat qu'il n'a pas vérifiées."""
    js = _lire("decarbonation-dc.js")
    i = js.index("function reprendreProfil")
    bloc = js[i:js.index("function libelleDe") if "function libelleDe" in js[i:] else i + 4000]
    assert "dc-lancer" not in bloc
    assert "Vérifiez-les" in js
