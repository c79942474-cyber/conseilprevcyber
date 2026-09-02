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


# ── 5. L'IP qui compte les échecs n'est pas celle que l'appelant écrit ─────
#
# LE DÉFAUT (constat bloquant de l'audit) : _client_ip() prenait la PREMIÈRE
# valeur de X-Forwarded-For, sans liste de relais de confiance. Render ajoute
# la vraie IP à DROITE de ce que le client envoie : la position [0] était donc
# exactement celle qu'un attaquant écrit. Corrigé par ProxyFix(x_for=1) posé
# sur app.wsgi_app, qui ne fait confiance qu'à la DERNIÈRE valeur — celle que
# seul le relais de Render ajoute.

def test_le_compteur_anti_bruteforce_ignore_le_prefixe_ecrit_par_lappelant():
    """AVANT LE CORRECTIF, ce test échouait : huit essais sous huit préfixes
    d'en-tête différents ouvraient huit compteurs neufs, et le neuvième
    passait toujours. Le préfixe est ce qu'un attaquant écrit ; le suffixe est
    ce que Render ajoute et lui seul contrôle — seul le suffixe doit compter."""
    email = "cible.bruteforce@example.com"
    _poser(email)
    cle = "login:203.0.113.55:%s" % email
    auth.guard.clear(cle)
    try:
        for i in range(8):
            r = A.app.test_client().post(
                "/api/auth/login", headers={**ENTETES,
                    "X-Forwarded-For": "%d.%d.%d.%d, 203.0.113.55" % (i, i, i, i)},
                json={"email": email, "password": "mauvais mot de passe"})
            assert r.status_code == 401, (
                "l'essai %d aurait dû être un simple échec, pas %r" % (i, r.get_json()))
        r = A.app.test_client().post(
            "/api/auth/login", headers={**ENTETES,
                "X-Forwarded-For": "255.255.255.255, 203.0.113.55"},
            json={"email": email, "password": "mauvais mot de passe"})
        assert r.status_code == 429, (
            "le neuvième essai, sous un NEUVIÈME préfixe d'en-tête, aurait dû "
            "être bloqué : c'est le suffixe ajouté par le relais qui fixe le "
            "compteur, pas le préfixe que l'appelant écrit")
    finally:
        auth.guard.clear(cle)
        _oter(email)


def test_deux_relais_distincts_ne_partagent_pas_le_meme_compteur():
    """Symétrique du test précédent : la correction ne doit pas non plus
    mélanger deux clients réels distincts sous une même clé."""
    email = "autre.cible@example.com"
    _poser(email)
    cle_a = "login:203.0.113.10:%s" % email
    cle_b = "login:203.0.113.20:%s" % email
    auth.guard.clear(cle_a)
    auth.guard.clear(cle_b)
    try:
        for _ in range(8):
            r = A.app.test_client().post(
                "/api/auth/login", headers={**ENTETES,
                    "X-Forwarded-For": "1.2.3.4, 203.0.113.10"},
                json={"email": email, "password": "mauvais mot de passe"})
            assert r.status_code == 401
        r = A.app.test_client().post(
            "/api/auth/login", headers={**ENTETES,
                "X-Forwarded-For": "1.2.3.4, 203.0.113.20"},
            json={"email": email, "password": "mauvais mot de passe"})
        assert r.status_code == 401, (
            "un relais différent (203.0.113.20) a hérité du blocage d'un "
            "autre (203.0.113.10) : les deux clés se sont mélangées")
    finally:
        auth.guard.clear(cle_a)
        auth.guard.clear(cle_b)
        _oter(email)


# ── 6. /connexion ne renvoie pas où l'appelant le lui dit ──────────────────
#
# LE DÉFAUT (constat sérieux de l'audit). Un client déjà connecté qui rouvrait
# /connexion?next=... repartait vers l'adresse donnée SANS AUCUN CONTRÔLE — y
# compris hors du site. Pire, le cas d'un visiteur NON connecté : il voit la
# vraie page sur le vrai domaine, se connecte pour de bon, et c'est APRÈS ce
# succès que le navigateur l'expédie vers une copie qui lui redemande son mot
# de passe. _safe_admin_next existait déjà, commenté « anti-open-redirect »,
# mais n'était appliqué qu'au portail admin.

def test_next_absolu_ou_protocole_relatif_est_ignore(client):
    """Un client déjà connecté qui rouvre /connexion?next=... ne doit jamais
    repartir hors du site."""
    _poser(VISITEUR, email_verified=True, approved=True, role="user")
    with client.session_transaction() as s:
        s["user_email"] = VISITEUR
    try:
        for hostile in ("https://evil.example/phishing", "//evil.example/phishing",
                        "http://evil.example", "/\\evil.example"):
            r = client.get("/connexion", query_string={"next": hostile})
            assert r.status_code in (301, 302, 303, 307, 308), hostile
            # LA RÈGLE LIT LA DESTINATION DÉCLARÉE, elle ne la recopie pas.
            # Elle exigeait « /demo » : le jour où l'atterrissage a changé de
            # page — décision délibérée — elle est tombée en désignant un défaut
            # d'anti-open-redirect qui n'existait pas. Ce qu'elle garde est que
            # l'on reparte sur LE DÉFAUT DU SITE, quel qu'il soit, et jamais
            # au-dehors : les deux moitiés sont vérifiées.
            assert r.headers["Location"] == auth.ACCUEIL, (
                hostile, r.headers["Location"])
            assert "evil.example" not in r.headers["Location"], hostile
    finally:
        _oter(VISITEUR)


def test_next_interne_est_respecte(client):
    """Le contrôle ne doit pas non plus casser l'usage normal : un chemin
    interne légitime doit rester suivi."""
    _poser(VISITEUR, email_verified=True, approved=True, role="user")
    with client.session_transaction() as s:
        s["user_email"] = VISITEUR
    try:
        r = client.get("/connexion", query_string={"next": "/vos-projets"})
        assert r.headers["Location"] == "/vos-projets"
    finally:
        _oter(VISITEUR)


def test_la_page_applique_le_meme_controle_cote_client():
    """La moitié qui compte le plus : le visiteur NON connecté voit la vraie
    page, saisit ses VRAIS identifiants, et c'est APRÈS ce succès que le script
    déciderait de la destination. Le contrôle serveur seul ne le couvre pas."""
    with open(os.path.join(ICI, "connexion.html"), encoding="utf-8") as f:
        html = f.read()
    assert "charAt(1)!=='/'" in html or 'charAt(1)!=="/"' in html, (
        "connexion.html doit refuser next=//... côté client, avant "
        "location.href — c'est ce chemin-là qui sert le visiteur non connecté")
