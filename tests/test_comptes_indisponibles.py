"""Quand la base de comptes ne répond pas, chaque point d'entrée doit le DIRE.

Ce test naît d'un incident réel : « Mot de passe oublié » répondait « Le serveur
a rencontré une erreur », parce que la route laissait remonter l'exception du
magasin et que le gestionnaire d'erreur générique la traduisait en 500. Sur les
neuf routes du système de comptes, une seule — la connexion — savait quoi dire.

Ce que le test vérifie n'est donc pas « ça ne plante pas », mais trois choses
précises :
  1. le code est 503 et non 500 — le serveur va bien, c'est la base qui dort,
     et 503 porte Retry-After là où 500 dit « n'insistez pas » ;
  2. le message nomme la cause, en français, sans divulguer l'hôte ni le port ;
  3. rien n'est présenté comme réussi. En particulier « mot de passe oublié »
     ne doit PAS répondre son message générique rassurant : l'utilisateur
     attendrait un email qui n'arrivera jamais.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)


@pytest.fixture()
def client_base_morte(monkeypatch):
    """Un client Flask dont le magasin de comptes est configuré mais injoignable.

    On ne coupe pas un vrai PostgreSQL : on place le magasin dans l'état exact
    où il se trouve quand la base dort — DSN présent, connexion absente, et
    prochaine tentative repoussée pour que le test ne dépende pas du réseau.
    """
    os.chdir(ICI)
    os.environ.pop("DATABASE_URL", None)
    import auth
    import app as appmod

    monkeypatch.setattr(auth.store, "_dsn", "postgresql://base-endormie/exemple")
    monkeypatch.setattr(auth.store, "_pg", None)
    monkeypatch.setattr(auth.store, "_last_try", 9e18)
    appmod.app.config["TESTING"] = True
    return appmod.app.test_client()


# En-têtes d'une requête venue de la page elle-même : sans eux, le contrôle
# d'origine répond 403 avant que la route ne soit atteinte, et le test
# mesurerait le pare-feu au lieu du comportement visé.
ENTETES = {"Origin": "http://localhost", "Referer": "http://localhost/"}

POINTS_API = [
    ("/api/auth/forgot", {"email": "christophe.cerf@outlook.com"}),
    ("/api/auth/reset", {"token": "jeton-quelconque", "password": "MotDePasse123"}),
    ("/api/auth/login", {"email": "x@exemple.fr", "password": "MotDePasse123"}),
]

POINTS_PAGE = ["/reinitialiser/jeton-quelconque", "/verifier-email/jeton-quelconque"]


@pytest.mark.parametrize("chemin,corps", POINTS_API)
def test_api_annonce_indisponibilite(client_base_morte, chemin, corps):
    r = client_base_morte.post(chemin, json=corps, headers=ENTETES)
    assert r.status_code == 503, f"{chemin} répond {r.status_code} au lieu de 503"
    d = r.get_json() or {}
    texte = (d.get("message") or d.get("error") or "").lower()
    assert "injoignable" in texte, f"{chemin} ne nomme pas la cause : {texte!r}"
    # Le diagnostic est lu depuis une page publique : il ne doit pas décrire
    # l'infrastructure.
    assert "postgres" not in texte and "5432" not in texte


@pytest.mark.parametrize("chemin", POINTS_PAGE)
def test_page_annonce_indisponibilite(client_base_morte, chemin):
    r = client_base_morte.get(chemin, headers=ENTETES)
    assert r.status_code == 503, f"{chemin} répond {r.status_code} au lieu de 503"
    assert r.headers.get("Retry-After"), f"{chemin} n'invite pas à réessayer"
    assert b"injoignable" in r.data


def test_mot_de_passe_oublie_ne_ment_pas(client_base_morte):
    """Le piège de cette route : sa réponse normale est volontairement
    générique — « si un compte existe, vous recevrez un lien » — pour ne pas
    révéler quels emails sont enregistrés. La servir pendant une panne serait
    pourtant un mensonge : aucun email ne partira, et l'utilisateur attendra.
    """
    r = client_base_morte.post("/api/auth/forgot",
                               json={"email": "christophe.cerf@outlook.com"},
                               headers=ENTETES)
    d = r.get_json() or {}
    assert r.status_code == 503
    assert d.get("ok") is False
    assert "si un compte existe" not in (d.get("message") or "").lower()


def test_erreur_de_code_reste_une_erreur_de_code(client_base_morte, monkeypatch):
    """Le garde-fou du garde-fou.

    Traduire toute exception du magasin en « base injoignable » habillerait un
    bug en incident passager : il ne serait jamais corrigé, et le journal ne
    porterait plus la trace. Seules les erreurs de CONNEXION sont traduites.
    """
    import auth

    def get_defaillant(email):
        raise KeyError("colonne inexistante — défaut de code, pas de réseau")

    monkeypatch.setattr(auth.store, "_pg", object())      # magasin « connecté »
    monkeypatch.setattr(auth.store, "_actif", lambda: type("M", (), {
        "get": staticmethod(get_defaillant)})())
    with pytest.raises(KeyError):
        auth.store.get("x@exemple.fr")
