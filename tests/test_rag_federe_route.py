# -*- coding: utf-8 -*-
"""LA PORTE QUE LA FÉDÉRATION OUVRE DANS NOTRE BASE.

CONSEILPREV interroge désormais la base de CONSEILPREV Cyber pour rédiger ses
livrables. C'est une porte de plus dans un service qui n'en avait aucune de ce
genre, et elle doit être tenue par deux verrous DIFFÉRENTS :

  LA CLÉ dit QUI peut demander. Un corpus « public » au sens de « montré sur le
  site » n'est pas pour autant offert en vrac par une API commode.

  `public_only` dit CE QUI est servi, et rien de ce que l'appelant présente ne
  le lève. Un livrable reproduit les extraits MOT POUR MOT : un document marqué
  interne recopié dans une pièce qui sort du site serait une fuite, pas une
  commodité. La clé ouvre la porte ; elle n'ouvre pas les tiroirs.

CE QUE CES RÈGLES GARDENT EN PLUS. Que la route ÉCHOUE FERMÉE : sans clé
configurée, elle refuse au lieu de servir. Une protection qui s'annule quand on
oublie de la régler n'en est pas une — et c'est exactement l'état d'un serveur
fraîchement déployé.
"""
import ast
import io
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import acces  # noqa: E402

H = {"Origin": "http://localhost"}
SRC = io.open(os.path.join(ICI, "app.py"), encoding="utf-8").read()


@pytest.fixture
def client():
    import app
    app.app.config["TESTING"] = True
    return app.app.test_client()


def _route():
    """Le corps de la vue fédérée, borné à la FONCTION et non à un nombre de
    caractères : une fenêtre comptée ignore les frontières du texte, et six
    lignes de commentaire ajoutées plus haut la font mentir."""
    d = SRC.index("def api_rag_search_federe")
    suite = re.search(r"\n(?=def |class |@app\.route)", SRC[d:])
    return SRC[d:d + (suite.start() if suite else len(SRC) - d)]


def _vue_ast(nom):
    """La vue, sous forme d'arbre. Ce qu'on veut vérifier ici est ce que le
    code FAIT, et le texte du fichier contient aussi ce qu'il DIT."""
    for n in ast.walk(ast.parse(SRC)):
        if isinstance(n, ast.FunctionDef) and n.name == nom:
            return n
    pytest.fail("la vue « %s » a disparu" % nom)


# ── 1. ELLE ÉCHOUE FERMÉE ───────────────────────────────────────────────

def test_sans_cle_configuree_la_route_refuse(client, monkeypatch):
    """L'ÉTAT D'UN SERVEUR FRAÎCHEMENT DÉPLOYÉ. Servir « en attendant » livrerait
    tout le corpus public à qui trouve l'adresse, et personne ne s'en
    apercevrait puisque tout marcherait."""
    monkeypatch.delenv("RAG_PAIR_CLE", raising=False)
    r = client.post("/api/rag/search", json={"query": "pue"}, headers=H)
    assert r.status_code == 403, r.status_code
    assert r.get_json()["error"] == "federation_non_configuree"


def test_une_cle_absente_est_refusee(client, monkeypatch):
    monkeypatch.setenv("RAG_PAIR_CLE", "la-bonne-cle")
    r = client.post("/api/rag/search", json={"query": "pue"}, headers=H)
    assert r.status_code == 403 and r.get_json()["error"] == "cle_invalide"


def test_une_mauvaise_cle_est_refusee(client, monkeypatch):
    monkeypatch.setenv("RAG_PAIR_CLE", "la-bonne-cle")
    h = dict(H, **{"X-Rag-Cle": "presque-la-bonne"})
    r = client.post("/api/rag/search", json={"query": "pue"}, headers=h)
    assert r.status_code == 403


def test_la_cle_est_comparee_en_temps_constant():
    """Une comparaison ordinaire s'arrête au premier caractère différent : le
    temps de réponse dit alors combien de caractères sont justes, et la clé se
    devine caractère par caractère."""
    assert "hmac.compare_digest" in _route(), (
        "la clé est comparée avec « == » : elle se devine au chronomètre")


def test_la_bonne_cle_passe(client, monkeypatch):
    monkeypatch.setenv("RAG_PAIR_CLE", "la-bonne-cle")
    h = dict(H, **{"X-Rag-Cle": "la-bonne-cle"})
    r = client.post("/api/rag/search", json={"query": "pue"}, headers=h)
    assert r.status_code == 200, r.get_json()
    j = r.get_json()
    assert j["ok"] is True and isinstance(j["resultats"], list)


def test_une_requete_vide_est_refusee(client, monkeypatch):
    monkeypatch.setenv("RAG_PAIR_CLE", "k")
    r = client.post("/api/rag/search", json={"query": "  "},
                    headers=dict(H, **{"X-Rag-Cle": "k"}))
    assert r.status_code == 400


# ── 2. ELLE NE SERT QUE DU PUBLIC ───────────────────────────────────────

def test_la_recherche_est_bornee_au_public_sans_condition():
    """LA LIMITE EST POSÉE DU CÔTÉ QUI SERT. Un `public_only` calculé à partir
    de quoi que ce soit d'envoyé par l'appelant serait une restriction que
    l'appelant peut lever — c'est-à-dire pas une restriction."""
    # SUR L'ARBRE, PAS SUR LE TEXTE. La première version cherchait
    # « public_only=True » dans le corps — et l'a trouvé dans la DOCSTRING, qui
    # explique justement la règle. Une règle satisfaite par le commentaire qui
    # la décrit ne garde rien : elle survivrait au retrait du code.
    vue = _vue_ast("api_rag_search_federe")
    appels = [n for n in ast.walk(vue)
              if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Attribute) and n.func.attr == "search"]
    assert appels, "la vue fédérée n'interroge aucune base"
    for a in appels:
        kw = {k.arg: k.value for k in a.keywords}
        assert "public_only" in kw, (
            "un appel de recherche sans périmètre : le défaut du magasin "
            "déciderait à la place de la route")
        v = kw["public_only"]
        assert isinstance(v, ast.Constant) and v.value is True, (
            "le périmètre est calculé (%s) : il peut donc être influencé par "
            "ce que l'appelant envoie" % ast.dump(v)[:80])


def test_la_visibilite_ne_voyage_pas():
    """Rendre le champ laisserait croire qu'il pourrait valoir autre chose que
    « public » — et inviterait un appelant à le demander."""
    corps = _route()
    bloc = corps[corps.index("return jsonify(ok=True"):]
    assert "visibility" not in bloc, (
        "la visibilité est renvoyée au pair alors que tout ce qui sort est "
        "public par construction")


def test_la_reponse_porte_ce_qu_il_faut_pour_rediger():
    corps = _route()
    bloc = corps[corps.index("return jsonify(ok=True"):]
    for champ in ("texte", "document", "document_id", "theme", "score"):
        assert '"%s"' % champ in bloc, "la réponse ne porte pas « %s »" % champ


# ── 3. ELLE EST DÉCLARÉE DANS LA POLITIQUE D'ACCÈS ──────────────────────

def test_la_route_est_nommee_dans_la_politique():
    """LE DÉMARRAGE L'A REFUSÉE, ET IL AVAIT RAISON. Une interface ouverte que
    la politique ne nomme pas ne se distingue pas d'un oubli — c'est
    exactement pourquoi la liste existe."""
    assert "/api/rag/search" in acces.API_JETON, (
        "la recherche fédérée n'est pas déclarée : le contrôle de démarrage "
        "la traitera comme une route oubliée")
    assert acces.api_statut("/api/rag/search") == "jeton"
    assert "RAG_PAIR_CLE" in acces.API_JETON["/api/rag/search"], (
        "le motif ne dit pas ce qui protège la route")


def test_elle_est_exemptee_du_controle_d_origine():
    """Un appel serveur à serveur ne porte pas d'origine de navigateur. Sans
    l'exemption, la route répondrait 403 à son seul appelant légitime — et le
    diagnostic ressemblerait à une clé fausse."""
    import app
    assert "/api/rag/search" in app._CSRF_EXEMPT


def test_l_exemption_d_origine_est_justifiee_dans_le_code():
    """Les autres exemptions le sont parce qu'elles portent un jeton d'écriture.
    Celle-ci l'est pour une raison différente — aucun cookie lu, rien d'écrit —
    et cette différence doit être écrite là où quelqu'un la relira."""
    d = SRC.index("_CSRF_EXEMPT = {")
    bloc = SRC[d:SRC.index("}", d)]
    assert "cookie" in bloc.lower(), (
        "l'exemption de /api/rag/search est posée sans dire pourquoi elle est "
        "sans danger")


# ── 4. LE DÉBIT EST BORNÉ ───────────────────────────────────────────────

def test_le_debit_est_borne():
    """Une recherche coûte une lecture de la base à chaque appel. Sans plafond,
    un pair en boucle — ou quelqu'un qui a la clé — épuise le service."""
    corps = _route()
    assert "guard.blocked" in corps and "guard.fail" in corps, (
        "la route fédérée n'est pas comptée : la clé devient un droit illimité")


def test_une_cle_configuree_non_ascii_refuse_au_lieu_de_planter(client, monkeypatch):
    """`hmac.compare_digest` LÈVE sur des chaînes non ASCII. Une clé accentuée
    posée dans la configuration rendait donc 500 — « erreur du serveur » — là où
    le diagnostic est « votre clé contient un caractère interdit ». Un 500 sur
    une route d'authentification envoie chercher une panne qui n'existe pas."""
    monkeypatch.setenv("RAG_PAIR_CLE", "clé-secrète")
    h = dict(H, **{"X-Rag-Cle": "clé-secrète"})
    r = client.post("/api/rag/search", json={"query": "pue"}, headers=h)
    assert r.status_code == 403, (
        "la route rend %d : la comparaison a levé au lieu de refuser"
        % r.status_code)
    assert r.get_json()["error"] == "cle_non_ascii"
    assert "hexad" in r.get_json()["message"], (
        "le message ne dit pas quoi employer à la place")


# ── Plusieurs clés servies : une par appelant ──────────────────────────────
# LA CONFUSION QUE CE BLOC ÉPROUVE. `RAG_PAIR_CLE` faisait double emploi : la
# clé avec laquelle ce serveur SERT, et celle avec laquelle il APPELLE son
# pair. À deux applications, la confusion était sans conséquence. À trois, elle
# impose une clé unique partagée par toute la maison — compromettre une
# application les ouvre toutes.

def test_plusieurs_cles_servies_sont_acceptees(client, monkeypatch):
    monkeypatch.setenv("RAG_CLES_SERVIES", "cle-de-A, cle-de-B ; cle-de-C")
    monkeypatch.setenv("RAG_PAIR_CLE", "")
    for cle in ("cle-de-A", "cle-de-B", "cle-de-C"):
        r = client.post("/api/rag/search", json={"query": "sécurité"},
                        headers={"X-Rag-Cle": cle})
        assert r.status_code == 200, (cle, r.status_code)


def test_une_cle_absente_de_la_liste_est_refusee(client, monkeypatch):
    monkeypatch.setenv("RAG_CLES_SERVIES", "cle-de-A cle-de-B")
    monkeypatch.setenv("RAG_PAIR_CLE", "")
    r = client.post("/api/rag/search", json={"query": "sécurité"},
                    headers={"X-Rag-Cle": "cle-de-Z"})
    assert r.status_code == 403
    assert r.get_json()["error"] == "cle_invalide"


def test_la_cle_historique_reste_acceptee_seule(client, monkeypatch):
    """Une installation existante ne déclare que `RAG_PAIR_CLE` : elle doit
    continuer de fonctionner sans que personne n'ait rien à changer."""
    monkeypatch.delenv("RAG_CLES_SERVIES", raising=False)
    monkeypatch.setenv("RAG_PAIR_CLE", "cle-historique")
    r = client.post("/api/rag/search", json={"query": "sécurité"},
                    headers={"X-Rag-Cle": "cle-historique"})
    assert r.status_code == 200


def test_la_comparaison_ne_sort_pas_a_la_premiere_cle_valide():
    """UNE SORTIE ANTICIPÉE FERAIT VARIER LE TEMPS DE RÉPONSE avec le RANG de
    la clé valide dans la liste — précisément la fuite que la comparaison en
    temps constant existe pour fermer.

    Éprouvé sur la forme de la boucle : l'accumulation par `or egales` la
    parcourt entière, un `break` ou un `return` ne le ferait pas."""
    import os
    import re as _re
    ici = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(ici, "app.py"), encoding="utf-8") as f:
        src = f.read()
    i = src.index("def api_rag_search_federe(")
    corps = src[i:i + 4000]
    boucle = corps[corps.index("for attendue in attendues"):]
    boucle = boucle[:boucle.index("except TypeError")]
    assert "or egales" in boucle
    assert not _re.search(r"\b(break|return)\b", boucle), (
        "la boucle de comparaison sort par anticipation : le temps de réponse "
        "révélerait le rang de la clé valide")
