"""Fixtures partagées — un visiteur anonyme, un client connecté, un admin.

POURQUOI CES TROIS-LÀ, ET POURQUOI ELLES SONT ICI. Depuis que les pages du
menu demandent un compte, presque tout contrôle porte sur DEUX questions
distinctes qu'on confondait tant que le site était ouvert :

  · la porte tient-elle ? — c'est `anonyme` qui l'éprouve ;
  · derrière la porte, le calcul est-il juste ? — c'est `connecte`.

Les recopier dans chaque fichier laisserait chacun dériver de son côté, et
c'est l'exemplaire qu'on oublie de mettre à jour qui reste vert en ne
vérifiant plus rien.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

# En-tête d'origine : le site refuse les écritures qui n'en portent pas.
ORIGINE = {"Origin": "http://localhost"}


def _client(email=None):
    import app
    app.app.config["TESTING"] = True
    c = app.app.test_client()
    if email:
        with c.session_transaction() as s:
            s["user_email"] = email
    return c


# ── LE COMPTE CLIENT N'EST PAS LE COMPTE DE RECETTE ────────────────────────
# Le compte « recette@local.test » que les tests employaient pour se connecter
# porte le rôle ADMINISTRATEUR. Tout ce qu'il prouvait, c'était « un admin y
# arrive » — jamais « un client validé y arrive », qui est pourtant la question
# que pose la politique d'accès. Le piège est silencieux : la fixture s'appelle
# « connecté », le test passe, et l'on croit avoir éprouvé le cas ordinaire.
CLIENT_EMAIL = "cliente.validee@example.test"
ADMIN_EMAIL = "recette@local.test"


def _assurer_client():
    """Un compte confirmé et approuvé, de rôle « user » — le cas ordinaire."""
    import auth
    u = auth.store.get(CLIENT_EMAIL)
    if u:
        if (u.get("role") or "user") != "user" or not u.get("approved"):
            auth.store.update(CLIENT_EMAIL, role="user", approved=True,
                              email_verified=True)
        return
    auth.store.create({
        "email": CLIENT_EMAIL, "name": "Cliente validée", "org": "Essai",
        "password_hash": "x", "email_verified": True, "approved": True,
        "role": "user", "verify_token": None, "verify_expire": None,
        "approve_token": None, "reset_token": None, "reset_expire": None,
        "created_at": 0, "last_login": None,
    })


@pytest.fixture
def anonyme():
    """Le visiteur sans compte — celui contre qui la politique est écrite."""
    return _client()


@pytest.fixture
def connecte():
    """Un CLIENT : adresse confirmée, accès validé, aucun pouvoir d'admin."""
    _assurer_client()
    return _client(CLIENT_EMAIL)


@pytest.fixture
def admin():
    """L'administrateur, qui doit atteindre tout le site sans exception."""
    return _client(ADMIN_EMAIL)
