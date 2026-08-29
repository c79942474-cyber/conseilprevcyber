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


# ── LA FIXTURE « admin » NE FAISAIT QUE ROUVRIR UNE SESSION SUR ADMIN_EMAIL ─
# sans jamais forcer le rôle, contrairement à _assurer_client() ci-dessus.
# Sur un poste où users_db.json (hors dépôt) donne déjà le rôle admin à ce
# compte, le défaut ne se voyait pas ; sur un clone frais, où ce fichier
# n'existe pas du tout, le compte est introuvable et la session n'ouvre rien.
# Dans les deux cas, la fixture ne GARANTISSAIT rien de ce que son nom promet.
def _assurer_admin():
    """Un compte confirmé et approuvé, de rôle « admin » — symétrique de
    _assurer_client(), pour la même raison : une fixture doit fabriquer l'état
    qu'elle promet, pas espérer qu'il traîne déjà quelque part sur le poste."""
    import auth
    u = auth.store.get(ADMIN_EMAIL)
    if u:
        if (u.get("role") != "admin" or not u.get("approved")
                or not u.get("email_verified")):
            auth.store.update(ADMIN_EMAIL, role="admin", approved=True,
                              email_verified=True)
        return
    auth.store.create({
        "email": ADMIN_EMAIL, "name": "Admin de recette", "org": "Essai",
        "password_hash": "x", "email_verified": True, "approved": True,
        "role": "admin", "verify_token": None, "verify_expire": None,
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
    _assurer_admin()
    return _client(ADMIN_EMAIL)


@pytest.fixture
def client_dc():
    """Un client validé, pour les formulaires de calcul du centre de données.

    Distinct de `connecte` par le nom seulement — mais le nom compte : un
    fichier qui éprouve les SAISIES doit dire qu'il lui faut une porte ouverte,
    pas emprunter une fixture dont il ignore ce qu'elle garantit."""
    _assurer_client()
    return _client(CLIENT_EMAIL)


# ── LES COMPTEURS DE CADENCE SONT GLOBAUX AU PROCESSUS ─────────────────────
# CE QUI SE PASSAIT, ET POURQUOI ON NE LE VOYAIT QU'À LA SUITE COMPLÈTE. Le
# plafond de cadence par adresse est un compteur de processus, et toute la
# suite tourne sous une seule adresse — 127.0.0.1. La famille
# « /api/datacenter/ » admet cent vingt requêtes par minute : deux fichiers
# d'essais qui la sollicitent chacun soixante fois épuisent le quota, et le
# SECOND lit 429 là où il attendait 200. Chacun passe seul ; ensemble, le
# dernier échoue — sur une règle qui n'a rien à voir avec la cadence, ce qui
# envoie chercher un défaut là où il n'y en a pas.
#
# CE QUE CETTE REMISE À ZÉRO N'ÉTEINT PAS. Aucune règle de cadence : celles
# qui éprouvent un plafond CONSTRUISENT leur propre quota à l'intérieur d'une
# seule fonction d'essai, et le plafond y joue exactement comme en production.
# Ce qui disparaît est l'héritage ENTRE essais, qui n'est pas une propriété du
# service mais un artefact de la suite.
#
# ELLE EST AUTOMATIQUE, ET C'EST LE POINT. Réservée aux fichiers qui la
# demandent — c'était le cas avant, dans un seul d'entre eux —, elle protège
# ceux qui connaissent le piège et laisse tomber le prochain, c'est-à-dire
# celui qui ne saura pas pourquoi il échoue.
@pytest.fixture(autouse=True)
def compteurs_de_cadence_neufs():
    """LES DEUX COMPTEURS, et pas seulement celui d'adresse.

    Le service en porte deux, indépendants : le plafond par adresse posé avant
    la requête, et le compteur d'ÉCHECS de `auth.py`. Ne vider que le premier
    laissait le second s'accumuler sur toute la session — et un essai
    d'inscription lancé en fin de suite trouvait la porte déjà fermée par des
    échecs vieux de trois cents autres essais. Le service se comportait alors
    autrement qu'au premier appel d'un processus neuf, c'est-à-dire autrement
    qu'en production, et une règle qui constate lequel des deux plafonds
    répond concluait l'inverse de la vérité.
    """
    import app
    import auth
    def _vider():
        with auth.guard._lock:
            auth.guard._fails.clear()
        with app._ip_rate._lock:
            app._ip_rate._hits.clear()
    _vider()
    yield
    _vider()
