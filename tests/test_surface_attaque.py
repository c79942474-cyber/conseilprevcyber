# -*- coding: utf-8 -*-
"""DOUZE ROUTES D'ÉCRITURE N'ÉTAIENT COMPTÉES NULLE PART.

RELEVÉ DU 29 AOÛT 2026. Quatre-vingt-sept routes POST ; douze sans aucun
plafond, ni global ni local. Parmi elles, LES QUATRE POINTS À JETON — dont
`/api/rag/ingest`, qui écrit dans la base de connaissance et constitue le chemin
d'empoisonnement le plus court du site.

CE QUI REND CE DÉFAUT PARTICULIER. Il était réputé corrigé. Le commentaire du
limiteur dit, mot pour mot, que les points exacts sont testés hors des familles
« parce que le filtre laissait passer sans compteur les deux points d'ingestion
protégés par un simple jeton ». Le mécanisme avait bien été posé ; les chemins
n'ont jamais été ajoutés à la table. Une protection décrite et non appliquée est
pire qu'une protection absente : on ne la cherche plus.

DEUX MÉCANISMES, DEUX MENACES DIFFÉRENTES — et les confondre laisse un trou.

  `hmac.compare_digest` empêche de reconstituer le secret AU CHRONOMÈTRE. Il
  n'empêche pas de l'essayer.

  LE COMPTEUR D'ÉCHECS empêche de l'essayer. Il compte les échecs et non les
  appels : une automatisation légitime présente toujours le bon jeton, et la
  plafonner gênerait le seul usage régulier de ces points ; un attaquant ne
  produit QUE des échecs.

  LE PLAFOND DE DÉBIT empêche l'inondation menée AVEC le bon jeton — connecteur
  en boucle, ou secret ayant fuité. Aucun des deux autres ne l'arrête.

CE QUE CES RÈGLES GARDENT. Que le compte des routes non plafonnées reste à ZÉRO,
route par route, y compris celle qu'on écrira dans six mois — c'est la seule
forme qui tienne, une liste nommée se périmant au premier ajout.
"""
import ast
import io
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

SRC = io.open(os.path.join(ICI, "app.py"), encoding="utf-8").read()
H = {"Origin": "http://localhost"}


@pytest.fixture
def client():
    import app
    app.app.config["TESTING"] = True
    return app.app.test_client()


# LA REMISE À ZÉRO DES COMPTEURS A DÉMÉNAGÉ, et elle est devenue automatique.
# Elle vivait ici, réservée aux deux règles qui forcent une porte à jeton. Le
# piège qu'elle décrivait — des compteurs globaux au processus, une seule
# adresse pour toute la suite — ne concernait pourtant pas que ce fichier : il
# a rattrapé plus tard trois fichiers du centre de données, qui passaient
# chacun seul et échouaient ensemble sur des règles sans rapport avec la
# cadence. Une protection réservée à ceux qui connaissent le piège laisse
# tomber le prochain. Voir `compteurs_de_cadence_neufs` dans conftest.py.
@pytest.fixture
def compteurs_neufs(compteurs_de_cadence_neufs):
    """Conservée comme nom : les règles ci-dessous la citent, et le nom dit
    ce dont elles ont besoin."""
    yield


def _table(nom, fin):
    d = SRC.index("%s = " % nom)
    return SRC[d:SRC.index(fin, d)]


EXACT = set(re.findall(r'"(/api/[^"]+)":', _table("_RATE_EXACT", "\n}")))
FAMILLES = re.findall(r'\("(/api/[^"]+)",', _table("_RATE_FAMILY", "\n\n"))


def _routes_post():
    """Toute route POST déclarée, avec son nœud. Relevé sur l'ARBRE : une
    recherche textuelle des décorateurs raterait celles écrites autrement."""
    out = []
    for n in ast.parse(SRC).body:
        if not isinstance(n, ast.FunctionDef):
            continue
        rt = [d for d in n.decorator_list
              if isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "route"]
        if not rt or not rt[0].args:
            continue
        methodes = []
        for kw in rt[0].keywords:
            if kw.arg == "methods":
                methodes = [e.value for e in kw.value.elts]
        if "POST" in methodes:
            out.append((rt[0].args[0].value, n))
    return out


def _plafonnee(chemin, noeud):
    return (chemin in EXACT
            or any(chemin.startswith(f) for f in FAMILLES)
            or "blocked" in ast.dump(noeud))


# ── 1. LE COMPTE RESTE À ZÉRO ────────────────────────────────────────────

def test_aucune_route_d_ecriture_n_est_sans_plafond():
    """LA RÈGLE QUI AURAIT ÉVITÉ TOUT CECI, et la seule forme qui tienne : elle
    énumère, elle ne nomme pas. Une liste de chemins connus se périme au premier
    ajout, et c'est l'ajout qu'on oublie de protéger."""
    nues = [c for c, n in _routes_post() if not _plafonnee(c, n)]
    assert not nues, (
        "%d route(s) POST sans aucun plafond, ni global ni local :\n  - %s"
        % (len(nues), "\n  - ".join(sorted(nues))))


def test_le_releve_couvre_bien_toutes_les_routes():
    """Une règle qui n'inspecte rien passe toujours. Si le relevé rendait une
    liste vide, la règle précédente serait verte sur un service entièrement
    ouvert."""
    routes = _routes_post()
    assert len(routes) >= 80, (
        "le relevé ne trouve que %d routes POST : la lecture de l'arbre est "
        "cassée, et le contrôle ne garde plus rien" % len(routes))


def test_le_filtre_d_entree_est_derive_de_la_table():
    """LE DÉFAUT DE FOND. Les préfixes surveillés étaient recopiés À LA MAIN
    dans le filtre d'entrée : ajouter une famille sans penser à cette ligne
    posait un plafond qui n'était jamais atteint. Une protection qui a l'air
    posée et ne compte rien est le pire des deux mondes."""
    d = SRC.index("def _rate_limit()")
    corps = SRC[d:SRC.index("\n@app.after_request", d)]
    assert "_RATE_FAMILY" in corps, (
        "le filtre d'entrée ne consulte pas la table des familles : il la "
        "recopie, et la copie divergera")
    for prefixe in FAMILLES:
        assert '"%s"' % prefixe not in corps.split("for prefix")[0], (
            "le préfixe « %s » est encore écrit en dur dans le filtre" % prefixe)


@pytest.mark.parametrize("chemin", [
    "/api/rag/ingest", "/api/ingest", "/api/reset", "/api/maintenance/purge",
])
def test_chaque_point_a_jeton_porte_un_plafond_de_debit(chemin):
    """Le compteur d'échecs n'arrête pas une inondation menée AVEC le bon jeton.
    Deux mécanismes, deux menaces."""
    assert chemin in EXACT, (
        "« %s » n'a pas de plafond de débit : un connecteur en boucle, ou un "
        "secret ayant fuité, sature le service" % chemin)


def test_l_ecriture_dans_la_base_est_la_plus_serree():
    """`/api/rag/ingest` écrit dans la base de connaissance : c'est le chemin
    d'empoisonnement le plus court du site, et il doit être plus fermé que la
    télémétrie qui ne fait qu'ajouter une ligne d'état."""
    d = SRC.index("_RATE_EXACT = ")
    bloc = SRC[d:SRC.index("\n}", d)]
    def limite(chemin):
        m = re.search(r'"%s":\s*\((\d+),\s*(\d+)\)' % re.escape(chemin), bloc)
        assert m, "pas de plafond pour %s" % chemin
        return int(m.group(1)) / int(m.group(2))
    assert limite("/api/rag/ingest") < limite("/api/ingest"), (
        "l'écriture dans la base est aussi permissive que la télémétrie")


# ── 2. LE COMPTEUR D'ESSAIS SUR LES JETONS ───────────────────────────────

def _jeton_refus():
    d = SRC.index("def _jeton_refus")
    return SRC[d:SRC.index("\n\n\n", d)]


def test_les_essais_de_jeton_sont_comptes():
    """UN SECRET QU'ON PEUT ESSAYER SANS ÊTRE COMPTÉ N'EST PLUS UN SECRET,
    c'est un délai. La comparaison en temps constant protège du chronomètre,
    pas du nombre."""
    corps = _jeton_refus()
    assert "guard.blocked" in corps and "guard.fail" in corps


def test_une_reussite_remet_le_compteur_a_zero():
    """Sans cela, une seule faute de frappe dans la configuration d'un
    connecteur lui interdirait le quart d'heure suivant — et l'exploitant
    conclurait à une panne."""
    assert "guard.clear" in _jeton_refus(), (
        "le compteur n'est jamais remis à zéro : un connecteur qui se corrige "
        "reste bloqué")


def test_le_compteur_plein_ne_dit_pas_que_le_jeton_est_faux():
    """Répondre « jeton invalide » à la neuvième tentative apprend à
    l'attaquant que sa cadence n'a pas été remarquée. Le 429 ne dit rien du
    secret."""
    # SUR L'ARBRE, PAS SUR LE TEXTE. La première version cherchait « 401 » dans
    # le corps de la fonction — et l'a trouvé dans la DOCSTRING, qui dit
    # justement « rend 429 et non 401 ». Troisième fois que la prose satisfait
    # une règle écrite pour le code.
    import app
    fonction = None
    for n in ast.parse(SRC).body:
        if isinstance(n, ast.FunctionDef) and n.name == "_jeton_refus":
            fonction = n
    assert fonction, "la fonction _jeton_refus a disparu"
    # Le premier `if` du corps (après la docstring) doit être celui du compteur,
    # et son retour ne doit pas être un 401.
    tests = [x for x in fonction.body if isinstance(x, ast.If)]
    assert tests, "aucune condition dans _jeton_refus"
    premier = ast.dump(tests[0])
    assert "blocked" in premier, (
        "le compteur n'est pas consulté EN PREMIER : la comparaison a lieu "
        "avant, et la cadence n'est donc jamais coupée")
    assert "401" not in premier, (
        "le refus pour cadence rend un 401 : il apprend à l'attaquant que sa "
        "cadence n'a pas été remarquée")


def test_les_quatre_points_passent_par_le_compteur():
    """Un cinquième point à jeton écrit dans six mois doit passer par là aussi ;
    cette règle attrape l'appel direct qui contournerait le compteur."""
    directs = re.findall(r"if not _token_ok\(request\.headers", SRC)
    assert not directs, (
        "%d point(s) comparent le jeton sans passer par le compteur d'essais"
        % len(directs))
    assert SRC.count("_jeton_refus(request.headers") == 4, (
        "le nombre de points à jeton a changé : %d au lieu de 4 — le nouveau "
        "est-il compté ?" % SRC.count("_jeton_refus(request.headers"))


def test_un_jeton_non_ascii_refuse_au_lieu_de_lever():
    """`hmac.compare_digest` LÈVE sur du non-ASCII. Un jeton accentué dans la
    configuration ferait rendre 500 à une vérification d'authentification — un
    diagnostic qui envoie chercher une panne au lieu d'une clé mal formée."""
    import app
    assert app._token_ok("x", "jeton-accentué") is False, (
        "la comparaison lève au lieu de refuser")


# ── 3. LE COMPORTEMENT, PAS SEULEMENT LE CODE ────────────────────────────

def test_un_jeton_faux_finit_par_etre_refuse_pour_cadence(client, monkeypatch, compteurs_neufs):
    """LA RÈGLE QUI EXÉCUTE. Les précédentes lisent le fichier ; celle-ci force
    réellement la porte et vérifie qu'elle se ferme."""
    import app
    monkeypatch.setattr(app, "INGEST_TOKEN", "le-vrai-jeton")
    codes = []
    for _ in range(app._JETON_ESSAIS + 2):
        r = client.post("/api/reset", headers=dict(H, **{"X-Ingest-Token": "faux"}))
        codes.append(r.status_code)
    assert 401 in codes, "aucun refus d'authentification : la porte est ouverte"
    assert codes[-1] == 429, (
        "après %d échecs le service répond encore %s : le jeton peut être "
        "essayé indéfiniment" % (app._JETON_ESSAIS + 2, codes[-1]))


def test_le_bon_jeton_passe_et_efface_les_echecs(client, monkeypatch, compteurs_neufs):
    import app
    monkeypatch.setattr(app, "INGEST_TOKEN", "le-vrai-jeton")
    for _ in range(3):
        client.post("/api/reset", headers=dict(H, **{"X-Ingest-Token": "faux"}))
    r = client.post("/api/reset", headers=dict(H, **{"X-Ingest-Token": "le-vrai-jeton"}))
    assert r.status_code == 200, r.status_code
    assert not app.guard.blocked("jeton:cockpit:127.0.0.1", limit=1, window=900), (
        "les échecs antérieurs n'ont pas été effacés par la réussite")
