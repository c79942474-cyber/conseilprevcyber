# -*- coding: utf-8 -*-
"""L'accès s'achète — et la gratuité redevient un geste, tracé, jamais un défaut.

CE QUI ÉTAIT EN CAUSE, ET QUI SE LIT DANS LES JOURNAUX DU SERVEUR. Un compte est
créé, l'adresse est confirmée à la seconde suivante, et TRENTE-SIX SECONDES plus
tard le lien reçu par l'exploitant ouvre l'accès — gratuitement. Le demandeur qui
tente ensuite de régler s'entend répondre que « cette adresse ne peut pas ouvrir
de paiement » : `payable()` refuse un compte déjà ouvert. La caisse n'était pas
en panne, elle arrivait après la bataille. ON NE PEUT PAS ACHETER CE QU'ON VOUS A
DÉJÀ DONNÉ.

Trois causes, et chacune a sa règle ici :

  · L'ORDRE. La page atteinte après confirmation annonçait « votre accès sera
    actif après validation par notre équipe », et la page de tarif présentait la
    voie gratuite en premier comme « la voie habituelle, et elle ne coûte rien ».
    Le produit désignait lui-même la porte qui ne rapporte rien.
  · LE COURRIEL À L'EXPLOITANT ne disait pas ce que son bouton fait. « Il ne
    manque que votre accord pour ouvrir l'accès » : vrai, et muet sur le seul
    point qui engage — le demandeur n'a rien payé. Un geste gratuit qui ne se
    sait pas gratuit n'est pas une décision.
  · LE REFUS ÉTAIT AVEUGLE POUR TOUT LE MONDE. Le message identique pour
    « inconnue », « non confirmée » et « déjà ouverte » est juste : sans lui,
    cette route dirait qui a un compte ici. Mais celui qui a ouvert le lien
    reçu dans SA boîte a prouvé l'adresse — lui refuser le motif ne protège
    plus personne et lui cache la seule chose utile.

CE QUE CES RÈGLES NE FONT PAS. Aucune ne verrouille un libellé : la règle qui
gardait la page de tarif cherchait les mots « Validation par notre équipe » et
n'a rien su dire d'autre que leur disparition. Elles portent sur l'ÉTAT du
compte, sur la TRACE au registre, et sur l'ÉGALITÉ des refus entre eux.
"""
import io
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import audit                                                       # noqa: E402
import auth                                                        # noqa: E402
import app as A                                                    # noqa: E402

MDP = "MotDePasse!2026"
ENTETES = {"Origin": "http://localhost", "Referer": "http://localhost/connexion"}

ACHETEUR = "caisse.acheteur@example.com"
OUVERT = "caisse.deja.ouvert@example.com"
NON_CONFIRME = "caisse.non.confirme@example.com"
ABSENT = "caisse.jamais.vu@example.com"


def _desarmer():
    for k in ("register:127.0.0.1", "approve:127.0.0.1"):
        auth.guard.clear(k)
    A._ip_rate._hits.clear()
    A.guard.clear("paiement:127.0.0.1")


@pytest.fixture(autouse=True)
def _propre():
    _desarmer()
    yield
    _desarmer()
    for e in (ACHETEUR, OUVERT, NON_CONFIRME, ABSENT):
        try:
            auth.store.delete(e)
        except Exception:
            pass


@pytest.fixture
def caisse_allumee(monkeypatch):
    """SANS CETTE FIXTURE, TROIS RÈGLES DE CE FICHIER PASSAIENT À CÔTÉ.

    Aucune clé Stripe n'existe en recette : `/api/paiement/checkout` répondait
    `paiement_non_configure` AVANT même de regarder le compte, et les règles
    qui prétendent éprouver le motif du refus n'éprouvaient que l'absence de
    configuration. C'est exactement le défaut que ce fichier documente
    ailleurs — une règle verte pour une raison sans rapport avec ce qu'elle
    affirme. On allume donc la caisse, sans jamais ouvrir de socket.
    """
    import paiement
    monkeypatch.setattr(paiement, "configure", lambda: True)
    monkeypatch.setattr(paiement, "tarif",
                        lambda: {"montant": 49000, "devise": "eur",
                                 "affichage": "490,00\u00a0€", "recurrent": False})
    monkeypatch.setattr(paiement, "session_paiement",
                        lambda email, base: "https://checkout.stripe.test/c/recette")
    return paiement


@pytest.fixture
def courriels(monkeypatch):
    """Les envois sont capturés, jamais émis, et rendus synchrones."""
    boite = []
    monkeypatch.setattr(auth, "send_email",
                        lambda to, name, sujet, html: boite.append(
                            {"a": to, "sujet": sujet, "html": html}) or True)

    class _Direct:
        def __init__(self, target=None, args=(), kwargs=None, daemon=None):
            self._t, self._a, self._k = target, args, kwargs or {}

        def start(self):
            self._t(*self._a, **self._k)

    monkeypatch.setattr(auth.threading, "Thread", _Direct)
    monkeypatch.setattr(auth, "_check_captcha", lambda *a, **k: True)
    return boite


def _poser(email, **champs):
    try:
        auth.store.delete(email)
    except Exception:
        pass
    fiche = {"email": email, "name": "Recette caisse", "org": "ACME",
             "password_hash": "x", "email_verified": False, "approved": False,
             "role": "user", "verify_token": None, "verify_expire": None,
             "approve_token": None, "reset_token": None, "reset_expire": None,
             "created_at": 0, "last_login": None}
    fiche.update(champs)
    auth.store.create(fiche)
    return fiche


def _caisse(client, email):
    _desarmer()
    return client.post("/api/paiement/checkout", headers=ENTETES,
                       json={"email": email, "professionnel": True,
                             "cgv": True, "renonciation": True})


# ═══════════════════════════════════════════════════════════════════════════
#  1. L'ADRESSE PROUVÉE, ET CE QU'ELLE AUTORISE
# ═══════════════════════════════════════════════════════════════════════════

def test_la_confirmation_pose_l_adresse_prouvee_dans_la_session(courriels):
    """Le jeton vient d'être consommé : son porteur tient la boîte. C'est la
    SEULE preuve d'adresse dont dispose un visiteur qui n'a pas encore de
    compte ouvert — il ne peut pas se connecter, il n'a donc pas de session de
    compte."""
    client = A.app.test_client()
    _poser(NON_CONFIRME, verify_token="jeton-de-recette",
           verify_expire=auth._now_ms() + 3600 * 1000)
    r = client.get("/verifier-email/jeton-de-recette")
    assert r.status_code == 302
    r = client.get("/api/paiement/adresse-confirmee")
    assert r.status_code == 200
    assert r.get_json()["email"] == NON_CONFIRME


def test_un_visiteur_qui_n_a_rien_prouve_n_obtient_aucune_adresse():
    """La route est ouverte — elle doit l'être, l'acheteur n'a pas de compte —
    et elle ne rend donc RIEN à qui n'a rien prouvé. Une route ouverte qui
    rendrait l'adresse d'un autre serait un annuaire."""
    r = A.app.test_client().get("/api/paiement/adresse-confirmee")
    assert r.status_code == 200 and r.get_json()["email"] is None


def test_l_adresse_confirmee_n_est_jamais_mise_en_cache():
    """Cette réponse dépend de la session ; l'autre route de paiement non. Le
    préfixe /api/paiement/ n'est pas couvert par la règle globale, qui ne vise
    que /api/admin/ et /api/auth/ : sans en-tête explicite, un cache partagé
    servirait l'adresse d'un visiteur au suivant."""
    r = A.app.test_client().get("/api/paiement/adresse-confirmee")
    assert "no-store" in (r.headers.get("Cache-Control") or "")


# ═══════════════════════════════════════════════════════════════════════════
#  2. LE REFUS : PRÉCIS POUR QUI A PROUVÉ, IDENTIQUE POUR TOUS LES AUTRES
# ═══════════════════════════════════════════════════════════════════════════

def test_un_acces_deja_ouvert_s_entend_dire_qu_il_n_a_rien_a_payer(caisse_allumee, courriels):
    """LE DÉFAUT EXACT, REPRODUIT. Un compte ouvert gratuitement qui tente de
    régler recevait « cette adresse ne peut pas ouvrir de paiement » — exact,
    et parfaitement inutilisable : rien n'y dit que l'accès est déjà là."""
    client = A.app.test_client()
    _poser(OUVERT, verify_token="jeton-ouvert",
           verify_expire=auth._now_ms() + 3600 * 1000)
    client.get("/verifier-email/jeton-ouvert")          # l'adresse est prouvée
    auth.store.update(OUVERT, approved=True)            # …puis l'accès est offert
    j = _caisse(client, OUVERT).get_json()
    assert j["error"] == "acces_deja_ouvert", j
    assert "déjà ouvert" in j["message"]


def test_LE_POINT_QUI_DECIDE_une_adresse_confirmee_obtient_bien_une_caisse(
        caisse_allumee, courriels):
    """LA QUESTION POSÉE, ET LA SEULE RÉPONSE QUI VAILLE. Toutes les autres
    règles de ce fichier éprouvent des REFUS ; celle-ci éprouve le passage.
    Sans elle, on pourrait fermer la caisse à tout le monde et garder ce
    fichier au vert — une suite qui ne teste que les refus certifie une porte
    murée.

    Le parcours est celui du visiteur : inscription, confirmation d'adresse,
    règlement. Rien n'est approuvé entre-temps, et c'est tout l'enjeu — c'est
    l'ouverture gratuite arrivant AVANT qui refermait la caisse.
    """
    client = A.app.test_client()
    _poser(ACHETEUR, verify_token="jeton-passage",
           verify_expire=auth._now_ms() + 3600 * 1000)
    assert client.get("/verifier-email/jeton-passage").status_code == 302
    assert auth.store.get(ACHETEUR)["approved"] is False, (
        "le compte est déjà ouvert : la caisse n'a plus rien à vendre")
    r = _caisse(client, ACHETEUR)
    j = r.get_json()
    assert r.status_code == 200 and j["ok"] is True, j
    assert j["url"].startswith("https://"), j
    # LA CAISSE N'OUVRE RIEN PAR ELLE-MÊME. Seule la notification signée le
    # fait : un appel à cette adresse ne promeut personne.
    assert auth.store.get(ACHETEUR)["approved"] is False


def test_le_refus_reste_le_meme_pour_les_trois_cas_quand_rien_n_est_prouve(caisse_allumee):
    """L'ANTI-ORACLE, ÉPROUVÉ EN COMPARANT LES REFUS ENTRE EUX plutôt qu'en
    relisant une phrase. Trois comptes dans trois états différents, un visiteur
    qui n'a rien prouvé : les trois réponses doivent être INDISCERNABLES. Une
    règle qui se contenterait de vérifier la présence du message vague passerait
    encore le jour où l'un des trois cas se met à répondre autre chose."""
    _poser(OUVERT, email_verified=True, approved=True)
    _poser(NON_CONFIRME, email_verified=False, approved=False)
    reponses = []
    for adresse in (OUVERT, NON_CONFIRME, ABSENT):
        client = A.app.test_client()          # aucun lien de confirmation ouvert
        r = _caisse(client, adresse)
        reponses.append((r.status_code, r.get_data(as_text=True)))
    assert reponses[0] == reponses[1] == reponses[2], (
        "les trois refus se distinguent : la route dit qui a un compte ici")
    assert "compte_non_eligible" in reponses[0][1]


def test_la_preuve_ne_vaut_que_pour_l_adresse_prouvee(caisse_allumee, courriels):
    """Prouver SON adresse n'ouvre pas le motif exact sur CELLE D'UN AUTRE.
    Sans cette égalité stricte, il suffirait d'un compte à soi pour interroger
    l'état de n'importe quel autre."""
    client = A.app.test_client()
    _poser(NON_CONFIRME, verify_token="jeton-tiers",
           verify_expire=auth._now_ms() + 3600 * 1000)
    client.get("/verifier-email/jeton-tiers")
    _poser(OUVERT, email_verified=True, approved=True)
    j = _caisse(client, OUVERT).get_json()
    assert j["error"] == "compte_non_eligible", j


# ═══════════════════════════════════════════════════════════════════════════
#  3. LA GRATUITÉ EST NOMMÉE À CELUI QUI L'ACCORDE, ET À CELUI QUI LA REÇOIT
# ═══════════════════════════════════════════════════════════════════════════

def test_le_courriel_a_l_exploitant_dit_que_le_bouton_ouvre_sans_paiement(courriels):
    """Les deux faits qui rendent le geste décidable : le demandeur n'a rien
    réglé, et le bouton ouvre quand même."""
    _poser(ACHETEUR, verify_token="jeton-avis",
           verify_expire=auth._now_ms() + 3600 * 1000)
    A.app.test_client().get("/verifier-email/jeton-avis")
    admin = [c for c in courriels if c["a"] == auth.ADMIN_EMAIL]
    assert admin, [c["a"] for c in courriels]
    assert "n'a rien payé" in admin[-1]["html"]
    assert "sans paiement" in admin[-1]["html"]


def test_les_courriels_nomment_CE_QUI_EST_VENDU_et_ne_le_recopient_pas(courriels):
    """« VOTRE ACCÈS AU COCKPIT DE SUPERVISION » ÉTAIT FAUX DEUX FOIS.

    D'abord par défaut : le cockpit était UNE page sur les trente-quatre que
    l'accès ouvrait — le courriel nommait un trente-quatrième de ce qu'il
    livrait. Puis par excès : le 2 septembre 2026 le site s'est ouvert, le
    cockpit est devenu libre, et le courriel a continué de le vendre.

    UN LIBELLÉ RECOPIÉ DANS UN COURRIEL NE SUIT PAS UNE POLITIQUE D'ACCÈS. Les
    deux courriels lisent donc le menu croisé avec la politique. La règle
    vérifie qu'ils nomment ce qui est réellement réservé — et le fait pour les
    DEUX, celui de confirmation d'adresse comme celui d'ouverture, parce que
    corriger l'un et oublier l'autre est exactement ce qui s'était produit
    ailleurs cette semaine.
    """
    import perimetre
    import unicodedata

    def pur(t):
        return "".join(c for c in unicodedata.normalize("NFD", t)
                       if unicodedata.category(c) != "Mn").lower()

    vendues = perimetre.ce_qui_est_vendu()
    assert vendues, "le menu est illisible : la règle ne compare rien"

    u = _poser(ACHETEUR, verify_token="jeton-libelle",
               verify_expire=auth._now_ms() + 3600 * 1000)
    auth._send_verify(u, base="http://localhost")                # 1. confirmation
    auth._send_approved(dict(u, email_verified=True),
                        base="http://localhost")                 # 2. ouverture

    au_client = [c for c in courriels if c["a"] == ACHETEUR]
    assert len(au_client) >= 2, [c["sujet"] for c in courriels]
    for message in au_client:
        corps = pur(message["html"])
        for rubrique in vendues:
            mots = [m for m in re.findall(r"[^\W\d_]{6,}", pur(rubrique))]
            assert any(m in corps for m in mots), (
                "ce courriel ne nomme pas ce qui est vendu (%s) : %s"
                % (rubrique, message["sujet"]))
        assert "cockpit" not in corps, (
            "le courriel vend encore le cockpit, qui est libre depuis "
            "l'ouverture : %s" % message["sujet"])


def test_le_courriel_au_beneficiaire_suit_le_chemin_et_ne_le_devine_pas(courriels):
    """« Offert » n'est pas une nuance de ton : un bénéficiaire qui lit
    « approuvé » croit avoir acheté, attend une facture qui ne viendra pas, et
    ne sait pas qu'il doit ce compte à un geste. Le paramètre est explicite —
    l'appelant sait par où il est passé, cette fonction ne peut que le
    supposer."""
    u = _poser(ACHETEUR, email_verified=True, approved=True)
    auth._send_approved(u, base="http://localhost", gratuit=True)
    auth._send_approved(u, base="http://localhost", gratuit=False)
    offert, vendu = courriels[-2]["html"], courriels[-1]["html"]
    assert "offert" in offert
    assert "offert" not in vendu, (
        "un accès réglé est annoncé comme offert : le client attend une facture")


@pytest.mark.parametrize("porte", ["lien", "console"])
def test_les_deux_portes_gratuites_tracent_la_meme_action(porte, admin, courriels):
    """LES TROIS PORTES ÉCRIVAIENT TROIS CHOSES DIFFÉRENTES — et la console
    d'administration, rien du tout. Un accès offert dont rien ne dit qu'il l'a
    été ne se distingue plus, six mois après, d'un accès vendu. `compte.gratuite`
    est une ACTION à part, comptable sans lire de la prose : `compte.approbation`
    assorti d'un membre de phrase demandait de tenir ce membre de phrase figé."""
    avant = len(audit.lire(limit=500, action="compte.gratuite"))
    if porte == "lien":
        _poser(ACHETEUR, email_verified=True, approve_token="jeton-gratuit",
               approve_expire=auth._now_ms() + 3600 * 1000)
        r = A.app.test_client().get("/admin/approuver/jeton-gratuit")
    else:
        _poser(ACHETEUR, email_verified=True)
        r = admin.patch("/api/admin/users/%s" % ACHETEUR, headers=ENTETES,
                        json={"action": "approve"})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert auth.store.get(ACHETEUR)["approved"] is True
    trace = audit.lire(limit=500, action="compte.gratuite")
    assert len(trace) == avant + 1, "cette porte n'a rien tracé"
    assert trace[0]["cible"] == ACHETEUR


def test_le_chemin_payant_ne_se_compte_pas_avec_les_gratuites(courriels):
    """Les deux voies mènent au même état ; le registre doit encore pouvoir les
    séparer. Sans quoi « combien d'accès avons-nous offerts ? » n'a plus de
    réponse."""
    _poser(ACHETEUR, email_verified=True)
    avant = len(audit.lire(limit=500, action="compte.gratuite"))
    assert auth.ouvrir_par_paiement(
        ACHETEUR, base="http://localhost",
        commande={"reference": "cs_test", "montant": 49000, "devise": "eur"}) is True
    assert len(audit.lire(limit=500, action="compte.gratuite")) == avant, (
        "un accès RÉGLÉ est compté parmi les accès offerts")


# ═══════════════════════════════════════════════════════════════════════════
#  4. LES PAGES N'ENVOIENT PLUS ATTENDRE
# ═══════════════════════════════════════════════════════════════════════════

def _src(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


def test_la_page_de_connexion_n_envoie_plus_attendre_apres_la_confirmation():
    """LA MOITIÉ QUI PORTE EST L'INTERDICTION. Exiger une phrase la fige et
    empêche la suivante d'être vraie ; interdire la promesse d'attente ne peut
    barrer qu'une reformulation de la même faute. Le visiteur atteint cette
    page à la seconde où il a cliqué son lien : ce qu'on lui montre là décide
    de tout le reste."""
    import re
    page = _src("connexion.html")
    debut = page.index("if(q.get('verifie'))")
    # LES COMMENTAIRES SONT ÔTÉS AVANT LA LECTURE. Sans cela, la règle lit
    # l'explication de la correction — qui CITE la phrase interdite pour dire
    # pourquoi elle l'est — et refuse la page corrigée. Une règle qui prend le
    # commentaire pour le code est le défaut que ce fichier combat, retourné
    # contre lui-même.
    message = re.sub(r"/\*.*?\*/", "", page[debut:page.index("}", debut)], flags=re.S)
    for promesse in ("notre équipe", "sera actif", "validation"):
        assert promesse not in message, (
            "la page renvoie encore le visiteur attendre une validation")
    assert "égl" in message, "elle ne dit pas non plus quoi faire"


def test_la_page_de_connexion_ne_fait_pas_retaper_l_adresse_confirmee():
    """Redemander l'adresse sur la page atteinte en cliquant le lien envoyé à
    cette adresse-là était une friction posée juste devant la caisse."""
    page = _src("connexion.html")
    assert "/api/paiement/adresse-confirmee" in page
    assert "payerMail" in page[page.index("/api/paiement/adresse-confirmee"):]


def test_AUCUNE_page_publique_n_annonce_plus_une_validation_par_l_equipe():
    """LA RÈGLE PORTE SUR TOUTES LES PAGES, ET NON SUR CELLES QU'ON A PENSÉ À
    CITER. Deux règles nommaient `inscription.html` et `connexion.html` ; la
    même promesse dormait sur l'ACCUEIL, où un commentaire annonçait même la
    correction qu'elle n'avait pas reçue. Une liste figée cesse de décrire le
    site dès qu'on y ajoute une page — celle-ci les lit toutes.

    Les commentaires HTML sont ôtés : ils CITENT la phrase interdite pour dire
    pourquoi elle l'est.
    """
    import glob
    import re
    fautives = {}
    for chemin in sorted(glob.glob(os.path.join(ICI, "*.html"))):
        texte = io.open(chemin, encoding="utf-8").read()
        # DEUX SYNTAXES DE COMMENTAIRE, PARCE QUE CES FICHIERS PORTENT TROIS
        # LANGAGES. Ne retirer que `<!-- -->` laissait la règle buter sur une
        # explication écrite en commentaire JavaScript — elle refusait la page
        # corrigée à cause du texte qui dit pourquoi elle l'a été.
        for motif in (r"<!--.*?-->", r"/\*.*?\*/"):
            texte = re.sub(motif, "", texte, flags=re.S)
        trouvees = [p for p in ("validé par notre équipe",
                                "validée par notre équipe",
                                "validation par notre équipe",
                                "validation manuelle des accès")
                    if p in texte]
        if trouvees:
            fautives[os.path.basename(chemin)] = trouvees
    assert not fautives, (
        "des pages annoncent encore une validation par l'équipe : %s" % fautives)


def test_l_inscription_annonce_le_reglement_et_non_une_validation():
    """La première page que voit un acheteur ne doit pas lui apprendre qu'il
    peut ne pas payer."""
    tete = _src("inscription.html")
    tete = tete[:tete.index("</form>")]
    assert "validé par notre équipe" not in tete
    assert "validation manuelle des accès" not in tete
