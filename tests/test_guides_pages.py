"""LE GUIDE DE PAGE — SUR TOUTES LES PAGES, ET PAS LE GUIDE GÉNÉRIQUE.

CE QUI A DÉCLENCHÉ CE FICHIER. `nav.js` pose sur chaque page un bouton
« Guide de la page ». Quand la page n'a pas d'entrée dans `GUIDES`, le bouton
s'ouvre quand même — sur `GUIDE_DEFAULT`, qui dit « utilisez le menu pour
naviguer ». Dix-sept pages tombaient là, dont les cinq consoles
d'administration et sept pages de conseil parmi les plus denses du site. Un
guide générique sur une page dense est PIRE qu'aucun guide : le bouton promet
une aide, la fenêtre s'ouvre, et le lecteur en conclut qu'il a lu l'aide.

Rien ne le signalait. C'est la propriété commune des trois défauts corrigés
ici : aucun ne produit d'erreur.

DEUXIÈME DÉFAUT : UN GABARIT SANS `nav.js`. `admin-rgpd.html` ne chargeait pas
le script du tout — donc ni navigation de page, ni bouton, pas même le guide
générique. Une page qui ne charge pas un script n'est pas une page en erreur.

TROISIÈME DÉFAUT, CELUI QUI CACHE LES DEUX AUTRES : LE COMPTAGE. `nav.js`
porte CINQ tables indexées par le même chemin — icônes, menu, résumés, fil
d'Ariane, guides. Un relevé qui les confond annonce une couverture complète là
où il n'y a que des icônes ; un relevé qui n'inspecte que le littéral rate les
entrées ajoutées par affectation. Ce fichier relève les deux formes, et
seulement dans la table des guides.

CE QUE CES CONTRÔLES NE PEUVENT PAS FAIRE. Juger qu'un guide décrit fidèlement
sa page — cela se vérifie en lisant la page, et c'est ce qui a été fait pour
chacun des dix-sept. Ils tiennent les propriétés structurelles : une page, un
guide ; un guide, une page ; un `nav.js` sur tout gabarit servi par une route ;
et des liens de guide qui mènent quelque part.
"""
import io
import json
import os
import re
import subprocess
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)


def _lire(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


NAV = _lire("nav.js")
APP = _lire("app.py")


# ── LA TABLE DES GUIDES, ET ELLE SEULE ───────────────────────────────────

def _table_des_guides():
    """Le littéral `var GUIDES = {…}` plus les affectations `GUIDES["…"] = …`.
    Les quatre autres tables de nav.js indexées par le même chemin sont hors
    de ce périmètre : les y confondre ferait passer une icône pour un guide."""
    d = NAV.index("var GUIDES = {")
    f = NAV.index("\n  };", d) + 4
    return NAV[d:f]


TABLE = _table_des_guides()

# Les deux écritures d'une entrée : au littéral, et par affectation.
LITTERAL = [m.group(2) for m in re.finditer(r'^\s{4}(["\'])(/[^"\']*)\1\s*:\s*\{',
                                            TABLE, re.M)]
AFFECTEES = re.findall(r'GUIDES\[\s*["\'](/[^"\']*)["\']\s*\]\s*=', NAV)
CLES = LITTERAL + AFFECTEES


# ── LES PAGES DU SITE, D'APRÈS LES ROUTES ────────────────────────────────

STATIQUE = re.compile(r'\.(js|css|png|jpe?g|webp|svg|xml|txt|ico|json|webmanifest|mp4|webm|pdf|zip)$')


def _routes():
    """(chemin, corps du gestionnaire) pour chaque route déclarée."""
    out = []
    morceaux = re.split(r'(?=@app\.route)', APP)
    for b in morceaux:
        chemins = re.findall(r'@app\.route\(\s*["\']([^"\']+)["\']', b)
        if not chemins:
            continue
        for c in chemins:
            out.append((c, b))
    return out


def _pages():
    """Les routes qui servent une PAGE : ni API, ni fichier, ni redirection,
    ni sonde. La redirection se reconnaît à son gestionnaire, pas à une liste
    de noms écrite ici — une liste de noms est exactement ce qui a divergé."""
    pages = []
    for chemin, corps in _routes():
        if chemin.startswith("/api/") or "<" in chemin:
            continue
        if STATIQUE.search(chemin) or chemin.startswith("/media"):
            continue
        if chemin in ("/health",):
            continue
        if re.search(r'\breturn redirect\(', corps):
            continue
        pages.append(chemin.rstrip("/") or "/")
    return sorted(set(pages))


PAGES = _pages()


def _resolu(chemin):
    """La règle d'`initGuide()`, rejouée : la barre oblique finale est retirée,
    et les liens de réinitialisation retombent sur le mot de passe oublié."""
    p = chemin.rstrip("/") or "/"
    if p.startswith("/reinitialiser/"):
        p = "/mot-de-passe-oublie"
    return p in CLES


# ── UNE CLÉ, UN GUIDE ────────────────────────────────────────────────────

def test_aucune_clé_de_guide_répétée():
    """`GUIDES` est un littéral d'objet JavaScript : une clé répétée n'y lève
    rien, la dernière gagne, et le guide écrit en premier disparaît."""
    vus, doubles = set(), []
    for c in CLES:
        (doubles.append(c) if c in vus else vus.add(c))
    assert not doubles, (
        "clés répétées dans GUIDES — la dernière écrase les précédentes en "
        "silence : %s" % ", ".join(sorted(set(doubles))))


def test_le_relevé_voit_les_deux_écritures():
    """Si ce contrôle ne voyait qu'une des deux formes, tous les autres
    compteraient faux. Il dit alors qu'il ne prouve plus rien."""
    assert LITTERAL, "plus aucune entrée au littéral : le relevé doit être revu"
    assert AFFECTEES, "plus aucune entrée par affectation : le relevé doit être revu"


def test_le_relevé_ne_confond_pas_les_tables_de_nav():
    """nav.js porte plusieurs tables indexées par le même chemin. Confondre
    l'une d'elles avec la table des guides annoncerait une couverture qu'aucun
    guide ne rend."""
    autres = len(re.findall(r'^\s{4}["\']/[^"\']*["\']\s*:', NAV, re.M)) - len(LITTERAL)
    assert autres > 0, (
        "nav.js ne porte plus qu'une table indexée par chemin : la précaution "
        "de ce fichier n'a plus d'objet, et sa lecture doit être reprise")
    assert len(CLES) < len(re.findall(r'^\s{4}["\']/[^"\']*["\']\s*:', NAV, re.M)) + len(AFFECTEES)


# ── UNE PAGE, UN GUIDE ───────────────────────────────────────────────────

def test_chaque_page_a_son_guide():
    nues = sorted(p for p in PAGES if not _resolu(p))
    assert not nues, (
        "pages qui tombent sur GUIDE_DEFAULT — « utilisez le menu pour "
        "naviguer » — au lieu d'un guide écrit : %s" % ", ".join(nues))


def test_aucun_guide_sans_page():
    """Un guide dont la route a disparu ne s'ouvre jamais, et sa présence fait
    croire à une couverture qu'il ne rend pas."""
    connus = set(PAGES) | {"/mot-de-passe-oublie", "/connexion", "/inscription",
                           "/admin/comptes"}
    fantomes = sorted(c for c in CLES if c not in connus)
    assert not fantomes, (
        "guides écrits pour un chemin qui n'est plus servi : %s"
        % ", ".join(fantomes))


def test_les_pages_d_authentification_gardent_leur_guide():
    """Elles ne sont pas déclarées dans app.py mais dans auth.py : la liste
    d'exception du contrôle précédent doit rester justifiée."""
    auth = _lire("auth.py")
    for chemin in ("/connexion", "/inscription", "/mot-de-passe-oublie", "/admin/comptes"):
        assert re.search(r'route\(\s*["\']%s["\']' % re.escape(chemin), auth), (
            "%s n'est plus servi par auth.py : l'exception du contrôle "
            "« aucun guide sans page » n'est plus fondée" % chemin)
        assert chemin in CLES


def _source_des_guides():
    """Les deux littéraux et les affectations, extraits tels quels de nav.js.
    Rien n'est recopié : un guide corrigé ici et pas là-bas éprouverait un site
    imaginaire."""
    d = NAV.index("var REF_LINKS")
    f = NAV.index("var GUIDE_DEFAULT")
    g = NAV.index("\n\n", f)
    affect = []
    for m in re.finditer(r'^  GUIDES\[', NAV, re.M):
        affect.append(NAV[m.start():NAV.index("};", m.start()) + 2])
    return NAV[d:g] + "\n" + "\n".join(affect)


def _resolution(chemins):
    """La résolution TELLE QUE LE NAVIGATEUR L'EXÉCUTE, pour une liste de
    chemins. Chercher le nom `GUIDE_DEFAULT` dans le fichier ne prouverait
    rien : le renommer à sa déclaration laisserait le nom présent à son point
    d'usage, et l'assertion passerait sur un script cassé."""
    code = (_source_des_guides() + "\n"
            + "var demandes = " + json.dumps(chemins) + ";\n"
            + "var out = {};\n"
            + "demandes.forEach(function(c){\n"
            + "  var p = c.replace(/\\/+$/, '') || '/';\n"
            + "  if (/^\\/reinitialiser\\//.test(p)) p = '/mot-de-passe-oublie';\n"
            + "  var g = GUIDES[p] || GUIDE_DEFAULT;\n"
            + "  out[c] = { t: g.t, p: g.p, s: g.s, k: g.k, l: g.l };\n"
            + "});\n"
            + "console.log(JSON.stringify(out));\n")
    r = subprocess.run(["node", "-e", code], capture_output=True, text=True)
    assert r.returncode == 0, "nav.js n'est plus évaluable : %s" % r.stderr[-500:]
    return json.loads(r.stdout)


RENDUS = _resolution(PAGES + ["/page-qui-n-existe-pas"])
REPLI = RENDUS["/page-qui-n-existe-pas"]


def test_une_page_inconnue_reçoit_quand_même_un_guide():
    """Le repli doit RESTER OPÉRANT : une page ajoutée demain, avant qu'on lui
    écrive son guide, doit ouvrir quelque chose plutôt que rien."""
    assert REPLI["t"], "une page inconnue n'obtient plus aucun guide"
    assert isinstance(REPLI["s"], list) and len(REPLI["s"]) >= 2, (
        "le guide de repli n'indique plus quoi faire : %r" % (REPLI["s"],))


@pytest.mark.parametrize("chemin", PAGES)
def test_aucune_page_du_site_ne_tombe_sur_le_repli(chemin):
    """Et ce repli ne doit servir à AUCUNE page d'aujourd'hui. La comparaison
    porte sur le guide RÉELLEMENT RENDU, pas sur la table."""
    assert RENDUS[chemin]["t"] != REPLI["t"], (
        "%s tombe sur le guide générique — « %s »" % (chemin, REPLI["t"]))


@pytest.mark.parametrize("chemin", PAGES)
def test_le_guide_rendu_indique_quoi_faire(chemin):
    """Deux étapes au minimum. Un guide qui n'indique rien à faire occupe le
    bouton sans rien rendre — c'est le défaut que ce fichier corrige."""
    g = RENDUS[chemin]
    assert len(g["s"] or []) >= 2, (
        "%s : %d étape(s) rendue(s)" % (chemin, len(g["s"] or [])))


# ── LE BOUTON EXISTE SUR CHAQUE GABARIT SERVI ────────────────────────────

def _gabarits_servis():
    """Les fichiers HTML que le serveur nomme — dans app.py, dans le registre
    PAGES, ou dans auth.py. Le relevé porte sur ce que le CODE désigne, et non
    sur le contenu du dossier : un gabarit laissé là sans être servi n'a pas à
    porter de bouton."""
    servis = set(re.findall(r'["\']([a-z0-9][\w.-]*\.html)["\']', APP))
    servis.update(re.findall(r'["\']([a-z0-9][\w.-]*\.html)["\']', _lire("auth.py")))
    return sorted(f for f in servis if os.path.exists(os.path.join(ICI, f)))


GABARITS = _gabarits_servis()


def test_le_relevé_des_gabarits_n_est_pas_vide():
    assert len(GABARITS) >= 50, (
        "seulement %d gabarits relevés : la lecture des routes a cessé de "
        "fonctionner et les contrôles suivants ne prouvent plus rien"
        % len(GABARITS))


@pytest.mark.parametrize("gabarit", GABARITS)
def test_tout_gabarit_servi_charge_nav(gabarit):
    """Sans `nav.js`, pas de bouton — donc pas même le guide générique."""
    assert "/nav.js" in _lire(gabarit), (
        "%s ne charge pas nav.js : ni navigation de page ni bouton « Guide "
        "de la page », et rien ne le signale" % gabarit)


def test_aucun_gabarit_du_dossier_n_échappe_au_relevé():
    """Si un fichier HTML cessait d'être nommé par le serveur, il sortirait du
    relevé sans que rien ne le dise — et la couverture ci-dessus deviendrait
    une couverture partielle qui s'annonce complète."""
    presents = sorted(f for f in os.listdir(ICI) if f.endswith(".html"))
    hors = sorted(set(presents) - set(GABARITS))
    assert not hors, (
        "gabarits présents dans le dépôt mais que le code ne nomme jamais — "
        "ils sortent silencieusement du contrôle de couverture : %s"
        % ", ".join(hors))


def test_le_bouton_est_posé_même_sans_en_tête():
    """`initGuide()` insère la barre après `<header>`. Un gabarit sans en-tête
    ne doit pas perdre son bouton pour autant."""
    i = NAV.index("function initGuide()")
    corps = NAV[i:i + 3000]
    assert "document.body.insertBefore" in corps, (
        "le repli sans <header> a disparu : un gabarit sans en-tête n'aurait "
        "plus de bouton, sans erreur")


# ── LE GUIDE DIT QUELQUE CHOSE ───────────────────────────────────────────

def _entrees():
    """(clé, corps) pour chaque guide, quelle que soit son écriture."""
    out = []
    bornes = [(m.group(2), m.start()) for m in
              re.finditer(r'^\s{4}(["\'])(/[^"\']*)\1\s*:\s*\{', TABLE, re.M)]
    for n, (cle, i) in enumerate(bornes):
        j = bornes[n + 1][1] if n + 1 < len(bornes) else len(TABLE)
        out.append((cle, TABLE[i:j]))
    for m in re.finditer(r'GUIDES\[\s*["\'](/[^"\']*)["\']\s*\]\s*=', NAV):
        f = NAV.index("};", m.end())
        out.append((m.group(1), NAV[m.end():f]))
    return out


ENTREES = _entrees()


@pytest.mark.parametrize("cle,corps", ENTREES, ids=[c for c, _ in ENTREES])
def test_un_guide_a_un_titre_un_chapeau_et_des_étapes(cle, corps):
    t = re.search(r'\bt:\s*"([^"]*)"', corps)
    p = re.search(r'\bp:\s*"([^"]*)"', corps)
    assert t and len(t.group(1).strip()) >= 3, "guide %s sans titre" % cle
    assert p and len(p.group(1).strip()) >= 40, (
        "guide %s : chapeau absent ou trop court pour situer la page" % cle)
    etapes = re.findall(r'"([^"]{20,})"', corps[corps.index("s:"):corps.index("k:")]
                        if "s:" in corps and "k:" in corps else "")
    assert len(etapes) >= 2, (
        "guide %s : %d étape(s). Un guide qui n'indique pas quoi faire ne "
        "sert qu'à occuper le bouton." % (cle, len(etapes)))


ROUTES_CONNUES = set(PAGES) | {"/mot-de-passe-oublie", "/connexion", "/inscription",
                               "/admin/comptes"}


@pytest.mark.parametrize("cle,corps", ENTREES, ids=[c for c, _ in ENTREES])
def test_les_liens_d_un_guide_mènent_quelque_part(cle, corps):
    """Un guide qui renvoie vers une page supprimée envoie le lecteur dans le
    mur — et c'est le guide qui l'y a envoyé."""
    liens = re.findall(r'\[\s*"[^"]*",\s*"(/[^"]*)"\s*\]', corps)
    morts = [x for x in liens if (x.split("#")[0].rstrip("/") or "/") not in ROUTES_CONNUES]
    assert not morts, "guide %s : liens vers des pages inexistantes — %s" % (cle, morts)
