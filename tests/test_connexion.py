"""La connexion — et le piège qui enfermait le propriétaire dehors.

LE DÉFAUT. `_bootstrap_admin()` ne posait que le RÔLE sur le compte
ADMIN_EMAIL. Or un compte né du formulaire public a `email_verified` et
`approved` à faux, et la connexion refuse dans les deux cas. Le propriétaire du
site se retrouvait donc administrateur ET bloqué à la porte, sans recours :
il ne peut pas se valider lui-même (la page d'administration refuse de modifier
son propre compte — bonne règle), il ne peut pas y accéder sans être connecté,
et il ne lui restait que le lien d'approbation reçu par courriel, c'est-à-dire
dépendre d'un envoi qui peut ne jamais arriver.

CE QUE CES TESTS PROTÈGENT, ET DANS LES DEUX SENS :

  1. Le propriétaire entre. Quel que soit l'état dans lequel son compte a été
     créé, le démarrage le remet en état d'ouvrir sa propre porte.
  2. PERSONNE D'AUTRE n'entre. C'est la moitié du contrôle qui compte vraiment :
     lever deux verrous pour un compte ne doit rien lever pour les autres. Un
     visiteur non confirmé et non validé reste refusé, avec son motif.
  3. Les quatre issues de la connexion restent distinctes et nommées. Un
     « identifiants incorrects » envoyé à quelqu'un dont le mot de passe est bon
     le ferait changer un mot de passe valide — c'est ce qu'il faut éviter.
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
ENTETES = {"Origin": "http://localhost", "Referer": "http://localhost/connexion"}
VISITEUR = "visiteur.recette@example.com"


def _poser(email, **etat):
    try:
        auth.store.delete(email)
    except Exception:
        pass
    u = {"email": email, "password_hash": generate_password_hash(MDP),
         "name": "Recette", "email_verified": False, "approved": False,
         "role": "user"}
    u.update(etat)
    auth.store.create(u)


def _oter(*emails):
    for e in emails:
        try:
            auth.store.delete(e)
        except Exception:
            pass


@pytest.fixture
def client():
    return A.app.test_client()


def _connexion(client, email, mdp=MDP):
    return client.post("/api/auth/login", headers=ENTETES,
                       json={"email": email, "password": mdp})


# ── 1. Le propriétaire doit pouvoir entrer chez lui ────────────────────────

def test_le_proprietaire_inscrit_par_le_formulaire_peut_entrer(client):
    """LE contrôle : c'est exactement le scénario qui bloquait."""
    _poser(auth.ADMIN_EMAIL)                    # ni confirmé, ni validé
    auth._bootstrap_admin()
    r = _connexion(client, auth.ADMIN_EMAIL)
    assert r.status_code == 200, r.get_json()
    _oter(auth.ADMIN_EMAIL)


def test_le_bootstrap_leve_les_deux_verrous_et_pose_le_role():
    _poser(auth.ADMIN_EMAIL)
    auth._bootstrap_admin()
    u = auth.store.get(auth.ADMIN_EMAIL)
    assert u["role"] == "admin"
    assert u["email_verified"] is True
    assert u["approved"] is True
    _oter(auth.ADMIN_EMAIL)


def test_un_compte_proprietaire_deja_en_ordre_n_est_pas_reecrit():
    """On ne réécrit que ce qui manque : une écriture inutile à chaque
    démarrage userait la base et brouillerait l'audit."""
    _poser(auth.ADMIN_EMAIL, email_verified=True, approved=True, role="admin")
    avant = dict(auth.store.get(auth.ADMIN_EMAIL))
    auth._bootstrap_admin()
    assert auth.store.get(auth.ADMIN_EMAIL) == avant
    _oter(auth.ADMIN_EMAIL)


# ── 2. …et personne d'autre ────────────────────────────────────────────────

def test_le_bootstrap_ne_touche_a_aucun_autre_compte():
    """La moitié du contrôle qui compte vraiment."""
    _poser(VISITEUR)
    avant = dict(auth.store.get(VISITEUR))
    auth._bootstrap_admin()
    assert auth.store.get(VISITEUR) == avant, (
        "un compte ordinaire a été modifié par le démarrage")
    _oter(VISITEUR)


def test_un_visiteur_non_confirme_reste_refuse(client):
    _poser(VISITEUR)
    auth._bootstrap_admin()
    r = _connexion(client, VISITEUR)
    assert r.status_code == 403
    assert "Confirmez" in r.get_json()["error"]
    _oter(VISITEUR)


def test_un_visiteur_confirme_mais_non_valide_reste_refuse(client):
    _poser(VISITEUR, email_verified=True)
    r = _connexion(client, VISITEUR)
    assert r.status_code == 403
    assert "validation" in r.get_json()["error"]
    _oter(VISITEUR)


# ── 3. Les quatre issues restent distinctes ────────────────────────────────

def test_les_quatre_issues_sont_nommees_et_distinctes(client):
    """Un mot de passe bon refusé pour un AUTRE motif ferait changer un mot de
    passe valide. Chaque refus doit dire sa vraie raison."""
    _poser(VISITEUR)
    r1 = _connexion(client, VISITEUR)
    auth.store.update(VISITEUR, email_verified=True)
    r2 = _connexion(client, VISITEUR)
    auth.store.update(VISITEUR, approved=True)
    r3 = _connexion(client, VISITEUR)
    r4 = _connexion(client, VISITEUR, mdp="faux")

    assert (r1.status_code, r2.status_code) == (403, 403)
    assert r3.status_code == 200 and r3.get_json()["ok"] is True
    assert r4.status_code == 401
    motifs = {r1.get_json()["error"], r2.get_json()["error"],
              r4.get_json()["error"]}
    assert len(motifs) == 3, "deux refus différents portent le même motif"
    _oter(VISITEUR)


def test_un_compte_inconnu_ne_revele_pas_qu_il_est_inconnu(client):
    """Le même message que pour un mot de passe faux : sinon la page devient un
    oracle qui dit quelles adresses ont un compte."""
    _oter(VISITEUR)
    r = _connexion(client, VISITEUR)
    assert r.status_code == 401
    assert r.get_json()["error"] == "Identifiants incorrects."


# ── 4. La page, elle, doit savoir répondre ─────────────────────────────────

def test_la_page_distingue_une_erreur_serveur_d_une_panne_reseau():
    """« Erreur réseau » sur une réponse HTML d'hébergeur envoyait chercher le
    problème du mauvais côté."""
    with open(os.path.join(ICI, "connexion.html"), encoding="utf-8") as f:
        html = f.read()
    assert "Le serveur a répondu une erreur (HTTP" in html
    assert "n’a pas répondu" in html
    assert "JSON.parse" in html, (
        "la réponse doit être lue en texte puis analysée, sinon une page HTML "
        "lève et se fait passer pour une panne de réseau")


def test_la_page_empeche_le_double_essai():
    """Chaque tentative compte au compteur anti-bruteforce : un second clic
    involontaire fait bloquer pour « trop de tentatives »."""
    with open(os.path.join(ICI, "connexion.html"), encoding="utf-8") as f:
        html = f.read()
    assert "if(enCours) return;" in html
    assert "bouton.disabled=true" in html
