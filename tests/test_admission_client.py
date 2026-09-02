"""L'ADMISSION D'UN CLIENT — la chaîne entière, et ce qui la tient fermée.

CE QUI EST VÉRIFIÉ ICI, dans l'ordre où cela se produit :

    inscription  →  le client confirme son adresse  →  l'administrateur est
    prévenu à christophe.cerf@outlook.com  →  il approuve  →  le client est
    prévenu que son accès est ouvert  →  et alors seulement il peut entrer.

CINQ PROPRIÉTÉS QUE CES CONTRÔLES PROTÈGENT

  1. LE MOT DE PASSE N'EST JAMAIS EN CLAIR, nulle part : ni en base, ni dans une
     réponse d'interface, ni dans le journal.

  2. DEUX VERROUS CUMULATIFS, et aucun ne se contourne. Adresse confirmée ET
     accès approuvé : l'un sans l'autre laisse la porte fermée, avec un motif
     distinct — dire « identifiants incorrects » à quelqu'un dont le mot de
     passe est bon le ferait changer un mot de passe valide.

  3. L'ADMINISTRATEUR EST PRÉVENU APRÈS LA CONFIRMATION, pas avant. Prévenu au
     dépôt de la demande, il recevait des liens d'approbation portant des
     adresses que personne n'avait prouvées — et le message le priait d'attendre
     une confirmation dont rien ne l'avisait ensuite.

  4. TOUS LES LIENS MEURENT. La confirmation vit 48 h, la réinitialisation 2 h.
     L'approbation, elle, ne mourait JAMAIS : un courriel vieux de deux ans
     ouvrait encore un compte. Un lien sans échéance survit à la boîte qui l'a
     reçu — archive exportée, message transféré, messagerie reprise.

  5. LE FORMULAIRE NE DIT PAS QUI EXISTE. Une inscription sur une adresse déjà
     connue répond exactement comme une inscription nouvelle.
"""
import os
import sys
import time

import pytest
from werkzeug.security import generate_password_hash

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import auth  # noqa: E402
import app as A  # noqa: E402

MDP = "MotDePasse!2026"
ENTETES = {"Origin": "http://localhost", "Referer": "http://localhost/connexion"}
CLIENT = "client.admission@example.com"


@pytest.fixture(autouse=True)
def _compteurs_propres():
    """LES COMPTEURS SONT REMIS À ZÉRO AVANT **ET APRÈS** CHAQUE CONTRÔLE.

    Ce fichier éprouve exprès les limites de débit : il les fait donc sauter.
    Sans le nettoyage de sortie, il les laissait armées pour les fichiers
    suivants — cinq contrôles de la connexion sont tombés en 429 alors qu'ils
    attendaient 401 et 403, et rien dans leur message ne disait que la cause
    venait d'ailleurs. Une recette qui casse la suivante est pire qu'une
    recette absente."""
    _desarmer()
    yield
    _desarmer()


@pytest.fixture
def client():
    return A.app.test_client()


@pytest.fixture
def courriels(monkeypatch):
    """Les envois sont CAPTURÉS, jamais émis : une recette ne doit écrire à
    personne. On garde destinataire, objet et corps — c'est là que se lisent le
    lien et ce qu'il promet."""
    boite = []
    monkeypatch.setattr(auth, "send_email",
                        lambda to, name, sujet, html: boite.append(
                            {"a": to, "nom": name, "sujet": sujet, "html": html}) or True)
    # Les envois partent en fil d'exécution : on les rend synchrones pour que
    # le contrôle lise une boîte complète plutôt qu'une course.
    class _Direct:
        def __init__(self, target=None, args=(), kwargs=None, daemon=None):
            self._t, self._a, self._k = target, args, kwargs or {}

        def start(self):
            self._t(*self._a, **self._k)

    monkeypatch.setattr(auth.threading, "Thread", _Direct)
    monkeypatch.setattr(auth, "_check_captcha", lambda *a, **k: True)
    return boite


def _desarmer():
    """DEUX LIMITEURS DE DÉBIT PROTÈGENT CES ROUTES, et c'est voulu : celui
    d'`auth` compte les échecs par identifiant, celui de l'application compte
    les requêtes par IP sur toute la famille /api/auth/. Une recette qui n'en
    remettrait qu'un à zéro se ferait refouler par l'autre — et lirait le refus
    comme un défaut du produit."""
    auth.guard.clear("register:127.0.0.1")
    auth.guard.clear("approve:127.0.0.1")
    A._ip_rate._hits.clear()


def _oter(*emails):
    for e in emails:
        try:
            auth.store.delete(e)
        except Exception:
            pass


def _inscrire(client, email=CLIENT, mdp=MDP):
    _desarmer()
    return client.post("/api/auth/register", headers=ENTETES,
                       json={"email": email, "name": "Client Recette",
                             "org": "ACME", "password": mdp, "captcha": "4"})


def _connexion(client, email=CLIENT, mdp=MDP):
    _desarmer()
    auth.guard.clear("login:127.0.0.1:%s" % email)
    return client.post("/api/auth/login", headers=ENTETES,
                       json={"email": email, "password": mdp})


# ═══════════════════════════════════════════════════════════════════════════
#  1. LE MOT DE PASSE
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_le_mot_de_passe_n_est_jamais_stocke_en_clair(client, courriels):
    _oter(CLIENT)
    try:
        assert _inscrire(client).status_code == 200
        u = auth.store.get(CLIENT)
        assert u, "le compte n'a pas été créé"
        assert MDP not in str(u), "le mot de passe apparaît en clair dans la fiche"
        h = u["password_hash"]
        assert MDP not in h
        # scrypt : le paramétrage est celui de werkzeug, et il est nommé dans
        # l'empreinte. Un stockage en clair ou en MD5 se verrait ici.
        assert h.startswith("scrypt:"), h.split("$")[0]
        from werkzeug.security import check_password_hash
        assert check_password_hash(h, MDP)
        assert not check_password_hash(h, MDP + "x")
    finally:
        _oter(CLIENT)


def test_un_mot_de_passe_trop_faible_est_REFUSE_avec_son_motif(client, courriels):
    _oter(CLIENT)
    try:
        for faible, attendu in (("court1", "10 caractères"),
                                ("quesdeslettres", "lettres et des chiffres"),
                                ("1234567890", "lettres et des chiffres")):
            r = _inscrire(client, mdp=faible)
            assert r.status_code == 400, faible
            assert attendu in r.get_json()["error"], (faible, r.get_json())
            assert auth.store.get(CLIENT) is None, "un compte a été créé quand même"
    finally:
        _oter(CLIENT)


def test_une_adresse_mal_formee_est_REFUSEE(client, courriels):
    r = client.post("/api/auth/register", headers=ENTETES,
                    json={"email": "pas-une-adresse", "name": "X",
                          "password": MDP, "captcha": "4"})
    assert r.status_code == 400
    assert "email" in r.get_json()["error"].lower()


# ═══════════════════════════════════════════════════════════════════════════
#  2. LA CHAÎNE D'ADMISSION, DE BOUT EN BOUT
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_la_chaine_complete_dans_son_ordre(client, courriels):
    """Le contrôle central : les quatre étapes, leurs deux courriels, leurs deux
    destinataires, et la porte qui ne s'ouvre qu'au bout."""
    _oter(CLIENT)
    try:
        # ── 1. Inscription : le client seul est écrit, l'admin n'est PAS dérangé.
        assert _inscrire(client).status_code == 200
        assert len(courriels) == 1, [c["sujet"] for c in courriels]
        assert courriels[0]["a"] == CLIENT
        assert "Confirmez" in courriels[0]["sujet"]
        u = auth.store.get(CLIENT)
        assert u["email_verified"] is False and u["approved"] is False
        assert not u.get("approve_token"), (
            "un jeton d'approbation existe avant que l'adresse soit prouvée")

        # …et la porte est fermée, sur le motif de la confirmation.
        r = _connexion(client)
        assert r.status_code == 403 and "Confirmez" in r.get_json()["error"]

        # ── 2. Le client confirme son adresse.
        lien = u["verify_token"]
        r = client.get("/verifier-email/%s" % lien)
        assert r.status_code == 302 and "verifie=1" in r.headers["Location"]
        u = auth.store.get(CLIENT)
        assert u["email_verified"] is True
        assert u["verify_token"] is None, "le lien de confirmation reste utilisable"

        # ── 3. C'EST ALORS SEULEMENT que l'administrateur est prévenu.
        assert len(courriels) == 2, [c["sujet"] for c in courriels]
        admin = courriels[1]
        assert admin["a"] == auth.ADMIN_EMAIL == "christophe.cerf@outlook.com"
        assert CLIENT in admin["sujet"]
        assert "confirmée" in admin["html"], (
            "le message ne dit pas que l'adresse est prouvée")
        # LE COURRIEL DIT CE QUE LE CLIC FAIT. Il annonçait « il ne manque que
        # votre accord pour ouvrir l'accès » — muet sur le seul point qui
        # engage : le demandeur n'a rien réglé, et le bouton ouvre quand même.
        # La règle ne cherche pas une phrase mais les DEUX faits qui la
        # rendent décidable : que rien n'a été payé, et que le geste est
        # gratuit. Sans eux, l'exploitant clique sans savoir qu'il offre.
        assert "n'a rien payé" in admin["html"], (
            "le courriel ne dit pas que le demandeur n'a rien réglé")
        assert "sans paiement" in admin["html"], (
            "le courriel ne dit pas que le bouton ouvre gratuitement")
        assert "ACME" in admin["html"] and "Client Recette" in admin["html"]
        jeton = auth.store.get(CLIENT)["approve_token"]
        assert jeton and jeton in admin["html"], "le lien d'approbation manque"
        assert auth.store.get(CLIENT)["approve_expire"] > auth._now_ms()

        # …et la porte reste fermée, sur l'autre motif.
        r = _connexion(client)
        assert r.status_code == 403 and "validation" in r.get_json()["error"]

        # ── 4. L'exploitant OUVRE GRATUITEMENT. Ce n'est plus « approuver » :
        #      c'est offrir un accès vendu, et le registre doit pouvoir le
        #      compter sans lire de la prose.
        import audit
        avant = len(audit.lire(limit=500, action="compte.gratuite"))
        r = client.get("/admin/approuver/%s" % jeton)
        assert r.status_code == 200
        u = auth.store.get(CLIENT)
        assert u["approved"] is True
        assert u["approve_token"] is None, "le lien d'approbation reste utilisable"
        # LA RÈGLE PORTE SUR L'ÉTAT ET SUR LA TRACE, PAS SUR UN MOT. Elle
        # exigeait « approuvé » dans la page : le libellé a changé, la règle
        # est tombée, et rien de ce qu'elle prétendait garder n'avait bougé.
        # Une règle qui verrouille un libellé empêche de dire la vérité
        # suivante.
        gratuites = audit.lire(limit=500, action="compte.gratuite")
        assert len(gratuites) == avant + 1, (
            "l'ouverture gratuite n'est pas tracée comme telle")
        assert gratuites[0]["cible"] == CLIENT

        # ── 5. Le client est prévenu, à SON adresse — et il sait qu'on lui a
        #      OFFERT l'accès. Lire « approuvé » lui faisait croire qu'il avait
        #      acheté : il attendait une facture qui ne viendrait jamais.
        assert len(courriels) == 3, [c["sujet"] for c in courriels]
        avis = courriels[2]
        assert avis["a"] == CLIENT
        assert "ouvert" in avis["sujet"]
        assert "offert" in avis["html"], (
            "le bénéficiaire ne sait pas que son accès lui a été offert")
        assert "/connexion" in avis["html"]

        # ── 6. …et la porte s'ouvre enfin.
        r = _connexion(client)
        assert r.status_code == 200 and r.get_json()["ok"] is True
    finally:
        _oter(CLIENT)


# ═══════════════════════════════════════════════════════════════════════════
#  1bis. LE COURRIEL D'APPROBATION N'EXÉCUTE PAS CE QUE LE DEMANDEUR ÉCRIT
# ═══════════════════════════════════════════════════════════════════════════
#
# LE DÉFAUT CORRIGÉ. name/org ne sont bornés qu'en LONGUEUR à l'inscription,
# jamais en caractères. Non échappés dans le courriel HTML adressé à
# l'administrateur, un attaquant sans compte préalable pouvait y placer son
# propre bouton « Approuver cet accès », rendu AU-DESSUS du vrai — sur le seul
# écran où se décide l'admission de tout le site.

ATTAQUANT = "attaquant.injection@example.com"


def test_LE_POINT_QUI_DECIDE_un_nom_ou_une_organisation_hostile_n_execute_rien(client, courriels):
    """Le nom et l'organisation peuvent contenir du balisage — le formulaire ne
    l'interdit pas — mais ce balisage doit arriver LITTÉRAL dans le courriel de
    l'administrateur, jamais interprété."""
    _oter(ATTAQUANT)
    try:
        piege = ('</li></ul><a href="https://evil.example/portail">'
                 'Approuver cet accès</a><ul><li>')
        r = client.post("/api/auth/register", headers=ENTETES,
                        json={"email": ATTAQUANT,
                              "name": '<img src=x onerror=alert(1)>',
                              "org": piege, "password": MDP, "captcha": "4"})
        assert r.status_code == 200, r.get_json()

        u = auth.store.get(ATTAQUANT)
        r = client.get("/verifier-email/%s" % u["verify_token"])
        assert r.status_code == 302

        assert len(courriels) == 2, [c["sujet"] for c in courriels]
        admin = courriels[1]
        assert admin["a"] == auth.ADMIN_EMAIL

        # Rien de ce qui a été écrit par le demandeur ne doit survivre comme
        # balisage actif dans le courriel de l'administrateur.
        assert "<img" not in admin["html"], (
            "la balise du demandeur est passée telle quelle : elle s'exécuterait "
            "dans le client de messagerie de l'administrateur")
        assert 'href="https://evil.example/portail"' not in admin["html"], (
            "le faux bouton du demandeur reste un vrai lien cliquable")

        # …et ce qui a été écrit reste LISIBLE, sous sa forme échappée : on
        # informe l'administrateur, on ne fait pas disparaître la tentative.
        assert "&lt;img" in admin["html"]
        assert "&lt;/li&gt;&lt;/ul&gt;&lt;a href=" in admin["html"]

        # Le vrai bouton d'approbation, lui, reste bien un vrai lien.
        jeton = auth.store.get(ATTAQUANT)["approve_token"]
        assert jeton in admin["html"]
    finally:
        _oter(ATTAQUANT)


def test_LE_POINT_QUI_DECIDE_l_administrateur_n_est_pas_prevenu_a_l_inscription(client, courriels):
    """Prévenu au dépôt de la demande, il recevait des liens d'approbation
    portant des adresses que personne n'avait prouvées : n'importe qui pouvait
    faire tomber dans sa boîte une demande au nom d'un tiers."""
    _oter(CLIENT)
    try:
        _inscrire(client)
        destinataires = [c["a"] for c in courriels]
        assert auth.ADMIN_EMAIL not in destinataires, destinataires
        assert destinataires == [CLIENT]
    finally:
        _oter(CLIENT)


def test_SANS_CE_CONTRASTE_le_controle_precedent_ne_prouverait_rien(client, courriels):
    """Il faut que l'administrateur soit prévenu QUELQUE PART, sinon « il n'est
    pas prévenu à l'inscription » serait vrai d'un système qui ne le prévient
    jamais."""
    _oter(CLIENT)
    try:
        _inscrire(client)
        client.get("/verifier-email/%s" % auth.store.get(CLIENT)["verify_token"])
        assert auth.ADMIN_EMAIL in [c["a"] for c in courriels]
    finally:
        _oter(CLIENT)


# ═══════════════════════════════════════════════════════════════════════════
#  3. LES LIENS MEURENT
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_le_lien_d_approbation_EXPIRE(client, courriels):
    """Il ne mourait jamais, seul des trois. Un lien sans échéance survit à la
    boîte qui l'a reçu."""
    _oter(CLIENT)
    try:
        _inscrire(client)
        client.get("/verifier-email/%s" % auth.store.get(CLIENT)["verify_token"])
        jeton = auth.store.get(CLIENT)["approve_token"]
        # On fait vieillir le lien d'une seconde de trop.
        auth.store.update(CLIENT, approve_expire=auth._now_ms() - 1000)
        _desarmer()
        r = client.get("/admin/approuver/%s" % jeton)
        assert r.status_code == 200          # page « lien expiré »
        assert "expir" in r.get_data(as_text=True).lower()
        assert auth.store.get(CLIENT)["approved"] is False, (
            "un lien périmé a tout de même ouvert le compte")
    finally:
        _oter(CLIENT)


def test_les_trois_liens_portent_TOUS_une_echeance():
    """Ce que le contrôle précédent vérifie sur un cas, celui-ci le vérifie sur
    la règle : aucun des trois jetons ne doit être perpétuel."""
    for nom, heures in (("VERIFY_VALIDITY_H", auth.VERIFY_VALIDITY_H),
                        ("RESET_VALIDITY_H", auth.RESET_VALIDITY_H),
                        ("APPROVE_VALIDITY_H", auth.APPROVE_VALIDITY_H)):
        assert isinstance(heures, int) and 0 < heures <= 24 * 90, (nom, heures)
    # …et chaque échéance a bien un champ pour la porter.
    for champ in ("verify_expire", "reset_expire", "approve_expire"):
        assert champ in auth._FIELDS, champ


def test_un_jeton_d_approbation_INVENTE_ne_marche_pas(client, courriels):
    _desarmer()
    r = client.get("/admin/approuver/jeton-invente-de-toutes-pieces")
    assert "expir" in r.get_data(as_text=True).lower()


def test_la_route_d_approbation_est_LIMITEE_en_debit(client, courriels):
    """Elle est ouverte et non authentifiée — c'est le principe d'un lien reçu
    par courriel. Une porte ouverte sans compteur ne se voit pas s'ouvrir."""
    _desarmer()
    codes = [client.get("/admin/approuver/x%d" % i).status_code for i in range(24)]
    assert 429 in codes, codes
    _desarmer()


def test_approuver_un_compte_NON_CONFIRME_est_refuse(client, courriels):
    """Cas des comptes antérieurs à ce changement, qui portent encore un jeton
    frappé à l'inscription. L'approuver n'ouvrirait rien — la connexion
    resterait refusée — mais le compte serait marqué approuvé et
    l'administrateur croirait avoir fait son travail."""
    _oter(CLIENT)
    try:
        _inscrire(client)
        # On reconstitue l'ancien état : jeton d'approbation sans confirmation.
        auth.store.update(CLIENT, approve_token="ancien-jeton",
                          approve_expire=auth._now_ms() + 3600 * 1000)
        _desarmer()
        r = client.get("/admin/approuver/ancien-jeton")
        assert r.status_code == 409
        assert "non confirmée" in r.get_data(as_text=True).lower()
        assert auth.store.get(CLIENT)["approved"] is False
    finally:
        _oter(CLIENT)


# ═══════════════════════════════════════════════════════════════════════════
#  4. CE QUE LE FORMULAIRE NE DIT PAS
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_une_adresse_deja_connue_repond_COMME_une_inconnue(client, courriels):
    """Sinon le formulaire devient un annuaire : on y teste des adresses jusqu'à
    savoir lesquelles ont un compte."""
    _oter(CLIENT)
    try:
        r1 = _inscrire(client)
        n1 = len(courriels)
        r2 = _inscrire(client)          # la même, une seconde fois
        assert r1.status_code == r2.status_code == 200
        assert r1.get_json() == r2.get_json(), (r1.get_json(), r2.get_json())
        # …et le second dépôt n'écrase rien ni ne renvoie de courriel.
        assert len(courriels) == n1, "un second courriel est parti"
    finally:
        _oter(CLIENT)


def test_le_captcha_est_EXIGE_a_l_inscription(client, monkeypatch):
    """Sans lui, un script ouvre autant de demandes qu'il veut."""
    monkeypatch.setattr(auth, "send_email", lambda *a, **k: True)
    auth.guard.clear("register:127.0.0.1")
    r = client.post("/api/auth/register", headers=ENTETES,
                    json={"email": "sans.captcha@example.com", "name": "X",
                          "password": MDP, "captcha": "reponse-fausse"})
    assert r.status_code == 400
    assert "vérification" in r.get_json()["error"].lower()
    assert auth.store.get("sans.captcha@example.com") is None


def test_les_demandes_d_inscription_sont_LIMITEES_par_adresse_IP(client, courriels):
    _desarmer()
    codes = []
    for i in range(10):
        codes.append(client.post("/api/auth/register", headers=ENTETES,
                                 json={"email": "flood%d@example.com" % i,
                                       "name": "X", "password": MDP,
                                       "captcha": "4"}).status_code)
    assert 429 in codes, codes
    auth.guard.clear("register:127.0.0.1")
    for i in range(10):
        _oter("flood%d@example.com" % i)


def test_la_fiche_publique_d_un_compte_ne_porte_ni_empreinte_ni_jeton():
    """C'est elle que l'interface d'administration affiche. Un jeton qui
    passerait par là ouvrirait un compte à qui lit la page."""
    u = {"email": "x@example.com", "name": "X", "org": "O",
         "password_hash": "scrypt:32768:8:1$secret", "email_verified": True,
         "approved": True, "role": "user", "verify_token": "V", "approve_token": "A",
         "approve_expire": 1, "reset_token": "R", "created_at": 1, "last_login": 2}
    vue = auth._public_user(u)
    interdits = ("password_hash", "verify_token", "approve_token",
                 "approve_expire", "reset_token", "reset_expire")
    for k in interdits:
        assert k not in vue, k
    assert "secret" not in str(vue) and "A" not in str(vue.values())


# ═══════════════════════════════════════════════════════════════════════════
#  5. LA SESSION
# ═══════════════════════════════════════════════════════════════════════════

def test_le_cookie_de_session_est_HTTPONLY_SAMESITE_et_HTTPS_par_defaut():
    """Trois attributs, trois risques distincts : le vol par script, l'envoi
    depuis un autre site, et le transport en clair."""
    c = A.app.config
    assert c["SESSION_COOKIE_HTTPONLY"] is True
    assert c["SESSION_COOKIE_SAMESITE"] == "Lax"
    # En recette, COOKIE_NON_SECURISE=1 assouplit volontairement l'attribut :
    # ce qui doit tenir, c'est que le défaut soit HTTPS et que l'assouplissement
    # exige une demande EXPLICITE.
    assouplissement = os.environ.get("COOKIE_NON_SECURISE", "")
    if assouplissement != "1":
        assert c["SESSION_COOKIE_SECURE"] is True
    assert c["SESSION_COOKIE_NAME"] == "cpc_session"


def test_la_deconnexion_VIDE_la_session(client, courriels):
    _oter(CLIENT)
    try:
        _inscrire(client)
        client.get("/verifier-email/%s" % auth.store.get(CLIENT)["verify_token"])
        auth.store.update(CLIENT, approved=True)
        assert _connexion(client).status_code == 200
        assert client.get("/api/auth/me").get_json()["authenticated"] is True
        assert client.post("/api/auth/logout", headers=ENTETES).status_code == 200
        assert client.get("/api/auth/me").get_json()["authenticated"] is False
    finally:
        _oter(CLIENT)


def test_la_connexion_est_LIMITEE_apres_une_serie_d_echecs(client, courriels):
    _oter(CLIENT)
    try:
        _inscrire(client)
        client.get("/verifier-email/%s" % auth.store.get(CLIENT)["verify_token"])
        auth.store.update(CLIENT, approved=True)
        cle = "login:127.0.0.1:%s" % CLIENT
        auth.guard.clear(cle)
        codes = []
        for _ in range(10):
            codes.append(client.post("/api/auth/login", headers=ENTETES,
                                     json={"email": CLIENT,
                                           "password": "mauvais"}).status_code)
        assert 429 in codes, codes
        # …et le bon mot de passe reste refusé tant que le blocage court : c'est
        # le point d'une limitation, sinon elle ne coûte rien à l'attaquant.
        assert _connexion.__wrapped__ if False else True
        r = client.post("/api/auth/login", headers=ENTETES,
                        json={"email": CLIENT, "password": MDP})
        assert r.status_code == 429
        auth.guard.clear(cle)
    finally:
        _oter(CLIENT)
