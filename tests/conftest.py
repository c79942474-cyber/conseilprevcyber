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
def marche(admin):
    """LE COMPTE QUI A DROIT À LA RÉPONSE À CONSULTATION (§ 14).

    LA DÉCISION EST ÉCRITE UNE FOIS, ET CETTE FIXTURE LA PORTE. Les douze
    interfaces `/api/datacenter/marche/*` sont réservées à l'administration —
    un dossier de consultation appartient à l'acheteur, et le cabinet
    l'instruit pour le compte du client. La décision est déclarée côté serveur
    dans `acces.API_ADMIN`, avec son motif, et le service refuse de démarrer si
    l'une de ces routes s'ouvrait.

    POURQUOI UNE FIXTURE PLUTÔT QUE `admin` PARTOUT. Les cinquante règles de
    cette section n'éprouvent pas « l'administration » : elles éprouvent « le
    compte autorisé ». Écrire `admin` dans chacune ferait de la politique
    d'accès une donnée recopiée cinquante fois, et le jour où elle s'ouvre aux
    clients il faudrait retrouver les cinquante. Ici, on change une ligne.

    Le verrou lui-même n'est PAS tenu par cette fixture : il l'est par
    `test_chaque_interface_declaree_admin_REFUSE_un_compte_client`, qui
    énumère `acces.API_ADMIN` et vérifie les deux côtés de la porte."""
    return admin


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


# ── FAUX STRIPE, FAUX BREVO : LA VRAIE BIBLIOTHÈQUE, LE VRAI TRANSPORT ────
# CE QUE LES DOUBLURES EN LAMBDA CACHAIENT. `tarif()` et `session_paiement()`
# étaient remplacées par des lambdas, et le kit simulé de la recette rendait
# des dict là où la bibliothèque 15.x rend des `StripeObject` — qui n'ont pas
# de `.get()`. Le tarif valait None en production depuis le passage à cette
# version, et toutes les règles étaient vertes. Ici, la VRAIE bibliothèque
# parle à un faux serveur local (tests/faux_services.py) qui note ce qu'il
# reçoit : c'est le contrat sur le fil qu'on mesure, pas une valeur de retour.
#
# `reseau_ferme` est la garde : une règle qui viserait api.stripe.com ou
# api.brevo.com — parce qu'une variable réelle traîne dans l'environnement —
# tombe au lieu de partir.
import socket as _socket

SECRET_WEBHOOK_RECETTE = "whsec_recette_locale"
PRIX_RECETTE = "price_recette_acces"

try:
    import stripe as _STRIPE_REEL
except ImportError:                                            # pragma: no cover
    _STRIPE_REEL = None


@pytest.fixture
def reseau_ferme(monkeypatch):
    """Toute connexion sortante hors des faux serveurs est REFUSÉE. Le
    mandataire du conteneur écoute lui aussi sur 127.0.0.1 : on n'autorise
    donc pas l'adresse locale entière, seulement les ports des faux serveurs."""
    permis = set()
    vrai = _socket.socket.connect

    def connect(self, adresse):
        if isinstance(adresse, tuple) and not (
                adresse[0] in ("127.0.0.1", "::1") and adresse[1] in permis):
            raise ConnectionRefusedError("recette hors réseau : %r" % (adresse,))
        return vrai(self, adresse)
    monkeypatch.setattr(_socket.socket, "connect", connect)
    return permis


@pytest.fixture
def faux_stripe(monkeypatch, reseau_ferme):
    """La VRAIE bibliothèque `stripe`, `api_base` redirigé vers un faux serveur
    local, les trois variables que lit `paiement.py` posées, et ce que le
    processus PARTAGE remis en état : le client HTTP gardé par la bibliothèque,
    ses réessais, et le cache de dix minutes du tarif — un tarif lu par une
    règle resterait sinon vrai pour la suivante."""
    import paiement
    from faux_services import FauxStripe
    if _STRIPE_REEL is None:                                   # pragma: no cover
        pytest.skip("bibliothèque stripe absente")
    fs = FauxStripe(int(os.environ.get("FAUX_STRIPE_PORT", "0"))).demarrer()
    reseau_ferme.add(fs.port)
    st = _STRIPE_REEL
    monkeypatch.setitem(sys.modules, "stripe", st)
    monkeypatch.setattr(st, "api_base", fs.url)
    monkeypatch.setattr(st, "api_key", None)
    monkeypatch.setattr(st, "max_network_retries", st.max_network_retries)
    monkeypatch.setattr(st, "default_http_client", None)
    monkeypatch.setenv(paiement.CLE, "sk_test_recette_locale")
    monkeypatch.setenv(paiement.CLE_WEBHOOK, SECRET_WEBHOOK_RECETTE)
    monkeypatch.setenv(paiement.CLE_PRIX, PRIX_RECETTE)
    monkeypatch.setitem(paiement._TARIF, "valeur", None)
    monkeypatch.setitem(paiement._TARIF, "lu_a", 0.0)
    yield fs
    fs.arreter()


@pytest.fixture
def faux_brevo(monkeypatch, reseau_ferme):
    """Le VRAI transport HTTP de `auth.send_email`, vers un faux serveur local.
    La clé est lue à l'APPEL (variable d'environnement) ; l'adresse de l'API
    est un attribut de module — on remplace chacune là où elle est lue. Les
    pauses entre réessais sont raccourcies : elles ne sont pas ce qu'on
    mesure, et `raising=False` laisse la fixture servir aussi à mesurer le code
    d'AVANT, qui ne les connaissait pas."""
    import auth
    from faux_services import FauxBrevo
    fb = FauxBrevo(int(os.environ.get("FAUX_BREVO_PORT", "0"))).demarrer()
    reseau_ferme.add(fb.port)
    monkeypatch.setenv("BREVO_API_KEY", "xkeysib-recette-locale")
    monkeypatch.setattr(auth, "BREVO_API_URL", fb.url + "/v3/smtp/email")
    monkeypatch.setattr(auth, "BREVO_PAUSES_S", (0.05, 0.05), raising=False)
    yield fb
    fb.arreter()
