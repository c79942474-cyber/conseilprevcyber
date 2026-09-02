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
import unicodedata


def _sans_accents(texte):
    """« ingénierie » et « ingenierie » sont le même mot pour une règle.

    Sans cette normalisation, la comparaison entre le nom d'une rubrique du
    menu et la phrase de l'accueil échouerait sur un accent — et ferait croire
    à une divergence de périmètre là où il n'y a qu'une graphie."""
    return "".join(c for c in unicodedata.normalize("NFD", texte)
                   if unicodedata.category(c) != "Mn")

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


def bandeau():
    h = sans_commentaires(accueil())
    i = h.index('class="actions"')
    return h[i:h.index("</div>", i)]


def test_le_bandeau_offre_une_action_REELLEMENT_ouverte():
    """LE CONTRÔLE QUI COMPTE, et il a changé de forme avec la politique.

    Il interdisait d'abord tout lien fermé dans le bandeau — la règle tenait
    tant qu'une page d'ingénierie restait ouverte. Depuis que les pages du menu
    demandent un compte, elle exigerait de vider le bandeau de ce qu'il
    présente. La règle utile est ailleurs : peu importe combien de boutons
    mènent à un compte, il en faut AU MOINS UN qu'un inconnu puisse suivre.
    Sans lui, le premier écran du site est un mur, et le visiteur repart."""
    liens = set(re.findall(r'href="(/[^"#]*)"', bandeau()))
    ouverts = sorted(liens - pages_fermees())
    assert ouverts, sorted(liens)


def test_le_bandeau_conduit_a_la_creation_d_un_acces():
    """Dire « réservé aux clients » sans dire comment le devenir laisse le
    visiteur devant une porte sans sonnette."""
    assert '/inscription' in bandeau(), bandeau()[:400]


def test_la_page_explique_le_regime_d_acces_AVANT_les_boutons():
    """L'apprendre bouton par bouton coûte au visiteur un aller-retour par
    clic ; le lire une fois lui coûte une phrase.

    LA RÈGLE CHERCHAIT LE MOT « RÉSERVÉ », ET C'EST TOUT CE QU'ELLE GARDAIT.
    Elle est restée verte pendant que la note affirmait « les outils de calcul
    et le cockpit sont réservés aux clients » — le cockpit était devenu libre.
    Un mot présent ne dit pas qu'il désigne la bonne chose.

    ELLE LIT MAINTENANT CE QUI EST RÉELLEMENT FERMÉ. La note doit nommer la
    rubrique que la politique réserve encore : si le périmètre change et que la
    phrase ne suit pas, la règle tombe — ce qui est précisément ce qui n'était
    pas arrivé."""
    import perimetre
    h = sans_commentaires(accueil())
    i = h.index('class="acces-note"')
    brut = h[i:h.index("</p>", i)]
    note = _sans_accents(re.sub(r"<[^>]+>", " ", brut).lower())
    vendues = perimetre.ce_qui_est_vendu()
    assert vendues, "le menu est illisible : la règle ne compare rien"
    for rubrique in vendues:
        mots = [m for m in re.findall(r"[^\W\d_]{6,}", _sans_accents(rubrique.lower()))]
        assert any(m in note for m in mots), (
            "la note ne nomme pas ce qui demande encore un compte (%s)"
            % rubrique, note)
    assert "compte" in note, note
    assert "/inscription" in brut, brut


def test_les_liens_mis_en_avant_le_disent_EN_TOUTES_LETTRES():
    """Là où le visiteur décide — le bandeau et les cartes de domaines —, un
    cadenas ne suffit pas : ce sont les liens sur lesquels repose la conversion,
    et ils portent le mot."""
    h = sans_commentaires(accueil())
    zones = [h[h.index('class="actions"'):h.index("</div>", h.index('class="actions"'))]]
    i = h.index("// Nos domaines")
    zones.append(h[i:h.index("</section>", i)])
    fermees = pages_fermees()
    muets = []
    for zone in zones:
        for m in re.finditer(r'<a href="(/[^"#?]*)"[^>]*>(.*?)</a>', zone, re.S):
            if m.group(1) not in fermees:
                continue
            lib = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2)))
            if "accès client" not in lib:
                muets.append((m.group(1), lib.strip()[:50]))
    assert not muets, muets


def test_les_AUTRES_liens_sont_marques_par_le_script_partage():
    """LA LEÇON DE CE REMANIEMENT. Vingt-six liens de cette seule page mènent à
    une page réservée, et les pieds de page des quarante autres portent les
    mêmes. Les étiqueter à la main, c'était quarante fichiers à corriger puis un
    de plus à chaque page ajoutée — et c'est le lien qu'on aurait oublié qui
    aurait surpris le visiteur.

    Le marquage vient donc de la politique elle-même, servie par /api/acces et
    posée par nav.js sur tout le site. Ce test éprouve le MATÉRIAU ; que le
    cadenas apparaisse réellement, et pas pour un client connecté, est éprouvé
    dans le vrai document par recette_acces.js — un test qui lit le fichier ne
    verrait pas une branche devenue inatteignable."""
    with open(os.path.join(ICI, "nav.js"), encoding="utf-8") as f:
        js = f.read()
    assert "/api/acces" in js, "nav.js ne demande pas la politique au serveur"
    assert "ac-cle" in js and "accès client" in js
    assert "moi.authenticated" in js, (
        "un client connecté ne doit pas voir « réservé » sur des pages qui lui "
        "sont ouvertes")
    assert "initAcces()" in js[js.index("function init()"):], (
        "le marquage doit être appelé au démarrage de chaque page")
    # PAS D'ASSERTION SUR L'ORDRE DES APPELS. J'en avais écrit une — initDrawer
    # avant initAcces — en croyant qu'elle protégeait le marquage du menu. Je
    # l'ai éprouvée en inversant les deux appels : le nombre d'entrées marquées
    # n'a pas bougé, parce que le marquage a lieu dans la réponse d'un fetch,
    # donc après la fin de init() dans tous les cas. Ce contrôle passait pour
    # une raison sans rapport avec ce qu'il prétendait vérifier, et il aurait
    # dispensé de chercher la vraie garantie — qui est dans recette_acces.js,
    # laquelle compte les entrées marquées du tiroir dans le vrai document.


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
