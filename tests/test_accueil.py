"""L'accueil porte les deux métiers — et la page tient ce que le titre annonce.

CE QUI ÉTAIT EN CAUSE, ET CE N'ÉTAIT PAS LE TITRE. Le cabinet conduit deux
métiers : la cybersécurité industrielle, et l'ingénierie de projets de centres
de données — trois modules complets, maîtrise d'œuvre, bilan énergie-eau-carbone
et stratégie de développement durable. La page d'accueil n'en disait RIEN : zéro
occurrence de « centre de données », zéro de « ingénierie », zéro de « maîtrise
d'œuvre ». Un visiteur venu chercher de l'ingénierie repartait sans savoir
qu'elle existe.

POURQUOI CES TESTS NE SE CONTENTENT PAS DU TITRE. Changer le seul titre aurait
écrit un chèque que la page ne couvre pas : un visiteur qui lit « concevoir »
puis ne trouve que de la cybersécurité en dessous conclut à une promesse creuse,
ce qui coûte plus cher que le silence. On vérifie donc que le bandeau, le
chapeau, les étiquettes, un appel à l'action, une carte de domaine et la
méta-description nomment tous l'ingénierie — et qu'ils y CONDUISENT.
"""
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

PAGES_ING = ["/ingenierie-datacenter", "/datacenter",
             "/strategie-durable-datacenter"]


def accueil():
    with open(os.path.join(ICI, "index.html"), encoding="utf-8") as f:
        return f.read()


def sans_commentaires(h):
    """Les commentaires expliquent le défaut corrigé en le citant : les lire
    ferait trouver dans son explication ce qu'on cherche dans le contenu."""
    return re.sub(r"<!--.*?-->", " ", h, flags=re.S)


def h1():
    m = re.search(r"<h1>(.*?)</h1>", sans_commentaires(accueil()), re.S)
    assert m, "pas de H1"
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()


# ── 1. Le titre porte les deux métiers ─────────────────────────────────────

def test_le_titre_nomme_la_conception_ET_la_securite():
    t = h1().lower()
    assert "concevoir" in t, h1()
    assert "sécuris" in t, h1()


def test_le_titre_nomme_les_deux_objets():
    t = h1().lower()
    assert "industriel" in t, h1()
    assert "centres de données" in t, h1()


def test_le_bandeau_annonce_les_deux_metiers():
    h = sans_commentaires(accueil())
    bloc = h[h.index('class="eyebrow"'):h.index("</h1>")]
    assert "ngénierie de projets" in bloc, bloc[:160]
    assert "ybersécurité industrielle" in bloc, bloc[:160]


# ── 2. La page TIENT ce que le titre annonce ───────────────────────────────

def test_le_chapeau_parle_des_deux_metiers():
    """LE CONTRÔLE QUI COMPTE. Un titre qui promet et un chapeau qui ne parle
    que de cybersécurité est une promesse creuse — et une promesse creuse coûte
    plus cher que le silence."""
    h = sans_commentaires(accueil())
    lead = h[h.index('<p class="lead"'):h.index("</p>", h.index('<p class="lead"'))]
    assert "maîtrise d'œuvre" in lead, lead[:200]
    assert "IEC" in lead, "la cybersécurité doit rester nommée"


def test_les_etiquettes_portent_l_ingenierie():
    h = sans_commentaires(accueil())
    i = h.index('class="taglist"')
    bloc = h[i:h.index("</ul>", i)]
    assert "aîtrise d'œuvre" in bloc, bloc[:200]


@pytest.mark.parametrize("cible", PAGES_ING)
def test_l_accueil_conduit_a_chaque_page_d_ingenierie(cible):
    """Nommer une offre sans y conduire laisse le visiteur la chercher dans un
    menu qui ne la nomme pas non plus."""
    assert 'href="%s"' % cible in accueil(), cible


def test_un_appel_a_l_action_mene_a_l_ingenierie():
    """N'IMPORTE LAQUELLE des trois pages fait l'affaire, et c'est voulu :
    exiger nommément /ingenierie-datacenter obligerait le bandeau à pointer vers
    la seule des trois qui demande un compte. Ce qui compte est que le bandeau
    conduise au métier, pas qu'il conduise à une adresse précise."""
    h = sans_commentaires(accueil())
    i = h.index('class="actions"')
    bloc = h[i:h.index("</div>", i)]
    assert any('href="%s"' % p in bloc for p in PAGES_ING), bloc[:400]


def test_le_bloc_des_domaines_porte_une_carte_d_ingenierie():
    h = sans_commentaires(accueil())
    i = h.index("// Nos domaines")
    bloc = h[i:h.index("</section>", i)]
    titres = re.findall(r"<h3>(.*?)</h3>", bloc, re.S)
    assert any("ngénierie de centres de données" in t for t in titres), titres


def test_l_ingenierie_est_en_TETE_des_domaines():
    """La poser en cinquième position la laisserait derrière quatre cartes de
    cybersécurité — c'est-à-dire ne pas corriger le déséquilibre que le titre
    vient d'annoncer corrigé."""
    h = sans_commentaires(accueil())
    i = h.index("// Nos domaines")
    bloc = h[i:h.index("</section>", i)]
    titres = re.findall(r"<h3>(.*?)</h3>", bloc, re.S)
    assert titres and "ngénierie de centres de données" in titres[0], titres[:2]


def test_la_meta_description_nomme_les_deux_metiers():
    """C'est elle qui décide, sur un moteur de recherche, de ce que le cabinet
    est réputé faire."""
    h = accueil()
    m = re.search(r'name="description" content="([^"]*)"', h)
    assert m, "pas de méta-description"
    d = m.group(1).lower()
    assert "centres de données" in d, d
    assert "maîtrise d'œuvre" in d, d
    assert "62443" in d, "la cybersécurité doit rester nommée"


# ── 3. Ne jamais promettre en vitrine ce qui demande un compte ─────────────

def pages_fermees():
    """Relevé sur app.py, jamais recopié : figer ici la liste des pages
    protégées, c'est écrire un contrôle qui reste vert le jour où l'une d'elles
    s'ouvre ou se ferme — c'est-à-dire le seul jour où il servait."""
    with open(os.path.join(ICI, "app.py"), encoding="utf-8") as f:
        s = f.read()
    fermees = set()
    for m in re.finditer(r'@app\.route\("(/[^"]*)"[^)]*\)\n((?:@[^\n]*\n)*)def ', s):
        if "login_required" in m.group(2):
            fermees.add(m.group(1))
    assert fermees, "aucune page protégée trouvée : la lecture d'app.py a dérivé"
    return fermees


def test_aucun_bouton_du_bandeau_ne_mene_a_un_mur_de_connexion():
    """LE CONTRÔLE QUI COMPTE. C'est la recette navigateur qui l'a trouvé : le
    bouton le plus en vue de la page pointait vers /ingenierie-datacenter, et un
    visiteur anonyme atterrissait sur /connexion. Accueillir un premier visiteur
    par un formulaire est exactement la promesse creuse que ce remaniement
    prétend corriger — en pire, car elle est en tête de page."""
    h = sans_commentaires(accueil())
    i = h.index('class="actions"')
    bloc = h[i:h.index("</div>", i)]
    liens = re.findall(r'href="(/[^"#]*)"', bloc)
    fermes = sorted(set(liens) & pages_fermees())
    assert not fermes, fermes


@pytest.mark.parametrize("cible", PAGES_ING)
def test_un_lien_vers_une_page_fermee_annonce_qu_elle_l_est(cible):
    """Ailleurs qu'en bandeau, un lien vers une page à compte reste utile — à
    condition de le dire. Un clic curieux qui tombe sur un formulaire fait
    croire au visiteur qu'il s'est trompé de bouton."""
    if cible not in pages_fermees():
        pytest.skip("%s est ouverte" % cible)
    h = sans_commentaires(accueil())
    for m in re.finditer(r'<a href="%s"[^>]*>(.*?)</a>' % re.escape(cible), h, re.S):
        libelle = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1)))
        assert "accès client" in libelle or "connexion" in libelle.lower(), libelle


# ── 4. Ce que le remaniement ne devait pas casser ──────────────────────────

def test_l_offre_historique_reste_entiere():
    """Ajouter un métier ne doit pas en effacer un autre : les quatre domaines
    de cybersécurité étaient là avant, ils y restent."""
    h = sans_commentaires(accueil())
    i = h.index("// Nos domaines")
    bloc = h[i:h.index("</section>", i)]
    for attendu in ("discovery réseau", "Architecture", "Analyse de risques",
                    "Supervision"):
        assert attendu in bloc, attendu


def test_aucune_carte_ne_porte_une_classe_sans_regle():
    """Une classe d'accent que la feuille de style ne connaît pas ne rend rien :
    la carte perdrait son liseré, et personne ne le verrait dans le code.

    Les règles vivent dans styles.css, pas dans la page — les chercher dans le
    seul index.html les aurait toutes déclarées manquantes, ce qui a bien failli
    me faire « corriger » un défaut inexistant."""
    utilisees = set(re.findall(r'<div class="card (a\d)"', accueil()))
    with open(os.path.join(ICI, "styles.css"), encoding="utf-8") as f:
        definies = set(re.findall(r"\.card\.(a\d)\s*\{", f.read()))
    assert utilisees, "plus aucune carte ne porte d'accent"
    assert utilisees <= definies, sorted(utilisees - definies)


def test_le_titre_tient_sur_deux_segments():
    """Le second segment est coloré : il doit porter un fragment qui a du sens
    seul. « industrielles et vos centres de données » n'en avait pas ; « et vos
    centres de données » nomme exactement ce qui s'ajoute à l'offre."""
    m = re.search(r'<h1>(.*?)<br>\s*<span class="grad">(.*?)</span></h1>',
                  sans_commentaires(accueil()), re.S)
    assert m, "le titre n'est plus en deux segments"
    colore = re.sub(r"\s+", " ", m.group(2)).strip()
    assert "centres de données" in colore, colore
