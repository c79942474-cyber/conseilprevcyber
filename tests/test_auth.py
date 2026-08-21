"""auth.py — une adresse ne doit plus pouvoir écrire du HTML dans une page.

LE DÉFAUT CORRIGÉ, EN DEUX MOITIÉS. valid_email() n'excluait que l'arobase et
les espaces : rien n'empêchait une adresse de contenir « < », « > », «"» ou
«'». Et admin_approve() insérait u["email"] tel quel — via un simple `%s` —
dans les trois pages HTML qu'il renvoie (refus, succès), sans jamais passer
par html_lib.escape() comme le font déjà _notify_admin/_send_verify/
_send_approved. Une adresse comme `x"><script>...</script>@evil.com`
aurait donc pu exécuter du script dans le navigateur de l'ADMINISTRATEUR au
moment où il ouvre le lien d'approbation reçu par courriel — la page la plus
sensible du site, puisque c'est elle qui décide qui entre.

Les deux moitiés se testent séparément : la première (la regex) empêche
qu'une TELLE adresse naisse par le formulaire d'inscription ; la seconde
(l'échappement) protège même les comptes déjà en base — créés avant ce
correctif, ou par un autre chemin que le formulaire — qui porteraient encore
une adresse hostile.
"""
import os
import sys

import pytest
from werkzeug.security import generate_password_hash

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import auth  # noqa: E402
import app as A  # noqa: E402

MDP = "MotDePasse!2026"
HOSTILE = 'x"><script>alert(1)</script>@evil.com'


@pytest.fixture
def client():
    return A.app.test_client()


def _poser_avec_jeton(email, *, confirmee):
    try:
        auth.store.delete(email)
    except Exception:
        pass
    u = {"email": email, "password_hash": generate_password_hash(MDP),
         "name": "Recette", "role": "user",
         "email_verified": confirmee, "approved": False,
         "approve_token": "jeton-de-test-" + str(abs(hash(email))),
         "approve_expire": auth._now_ms() + 3600 * auth._MS}
    auth.store.create(u)
    return u


def _oter(email):
    try:
        auth.store.delete(email)
    except Exception:
        pass


# ── 1. la source : une adresse hostile ne doit plus être acceptée ──────────

def test_valid_email_refuse_les_caracteres_significatifs_en_html():
    assert auth.valid_email(HOSTILE) is False
    assert auth.valid_email('a<b@example.com') is False
    assert auth.valid_email('a>b@example.com') is False
    assert auth.valid_email('a"b@example.com') is False
    assert auth.valid_email("a'b@example.com") is False


def test_valid_email_continue_daccepter_une_adresse_ordinaire():
    assert auth.valid_email("visiteur.recette@example.com") is True
    assert auth.valid_email("prenom.nom+tag@sous.domaine.fr") is True


# ── 2. le puits : même en base, une adresse hostile ne s'exécute plus ──────

def test_admin_approve_echappe_ladresse_dans_la_page_de_refus(client):
    """Compte non confirmé : c'est la branche 409 qui affiche l'adresse."""
    u = _poser_avec_jeton(HOSTILE, confirmee=False)
    r = client.get("/admin/approuver/%s" % u["approve_token"])
    corps = r.get_data(as_text=True)
    assert "<script>alert(1)</script>" not in corps, (
        "l'adresse hostile s'est retrouvée active dans la page de refus")
    assert "&lt;script&gt;" in corps
    _oter(HOSTILE)


def test_admin_approve_echappe_ladresse_dans_la_page_de_succes(client):
    """Compte déjà confirmé : c'est la branche 200 qui affiche l'adresse."""
    u = _poser_avec_jeton(HOSTILE, confirmee=True)
    r = client.get("/admin/approuver/%s" % u["approve_token"])
    corps = r.get_data(as_text=True)
    assert "<script>alert(1)</script>" not in corps, (
        "l'adresse hostile s'est retrouvée active dans la page de succès")
    assert "&lt;script&gt;" in corps
    _oter(HOSTILE)
