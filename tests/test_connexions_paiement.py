# -*- coding: utf-8 -*-
"""La connexion Stripe et Brevo de ce site, MESURÉE sur le fil — sans réseau.

CE QUE LES RÈGLES EXISTANTES NE VOYAIENT PAS. `test_paiement.py` signe pour de
bon, mais n'appelle jamais Stripe ; `test_ouverture_par_la_caisse.py` remplace
`tarif()` et `session_paiement()` par des lambdas ; le kit simulé de la recette
rend des dict là où la bibliothèque 15.x rend des `StripeObject`. Trois choses
restaient donc sans règle, et deux étaient cassées — puis deux autres défauts
sont apparus en mesurant la notification sur le fil :

  · `tarif()` rendait TOUJOURS None — un objet Stripe n'a pas de `.get()`,
    l'erreur était avalée. Aucun prix affiché, et le contrôle « prix
    récurrent » de la console aveugle ;
  · un refus de Brevo (400, 401, 402 crédits épuisés) rendait False sans
    trace, et un 503 passager perdait le courriel pour de bon ;
  · rien ne mesurait ce que la caisse ENVOIE (mode, prix, compte lié, adresses
    de retour) ni ce que la notification EXIGE (signature du vrai secret,
    paiement encaissé) ;
  · le compte Stripe est PARTAGÉ avec conseilprev : chaque vente de l'autre
    site laissait ici une trace « compte.paiement.inconnu », et celle dont la
    référence était une adresse connue ici ouvrait un accès (section 5) ;
  · un échec d'ouverture (magasin injoignable) était acquitté 200 : Stripe ne
    réémettait jamais, le client payé restait fermé (section 6).

Ici, la VRAIE bibliothèque `stripe` (api_base → faux serveur local) et le VRAI
transport HTTP de `auth.send_email` (BREVO_API_URL → faux serveur local). Les
notifications sont signées comme Stripe les signe et lues par le vrai
`stripe.Webhook.construct_event`, avec le secret que lit `paiement.py`. Chaque
message d'échec dit ce qui a été OBSERVÉ.
"""
import logging
import os
import sys
import time

import pytest
import stripe

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import app as A                                                    # noqa: E402
import auth                                                        # noqa: E402
import paiement                                                    # noqa: E402
from conftest import PRIX_RECETTE, SECRET_WEBHOOK_RECETTE          # noqa: E402
from faux_services import evenement_stripe, signer_stripe          # noqa: E402

ACHETEUR = "acheteur.connexions@example.test"
TAPEE_AU_PAIEMENT = "facturation.autre@example.test"
ENTETES = {"Origin": "http://localhost", "Referer": "http://localhost/connexion"}
UA_STRIPE = "Stripe/1.0 (+https://stripe.com/docs/webhooks)"
TARIF_ATTENDU = {"montant": 49000, "devise": "eur",
                 "affichage": "490,00 €", "recurrent": False}


def _poser(email, **champs):
    try:
        auth.store.delete(email)
    except Exception:
        pass
    fiche = {"email": email, "name": "Recette connexions", "org": "ACME",
             "password_hash": "x", "email_verified": True, "approved": False,
             "role": "user", "verify_token": None, "verify_expire": None,
             "approve_token": None, "approve_expire": None,
             "reset_token": None, "reset_expire": None,
             "created_at": 0, "last_login": None}
    fiche.update(champs)
    auth.store.create(fiche)
    return fiche


@pytest.fixture
def acheteur():
    """Un compte confirmé, pas encore ouvert — l'état exact où la caisse sert."""
    _poser(ACHETEUR)
    yield ACHETEUR
    try:
        auth.store.delete(ACHETEUR)
    except Exception:
        pass


@pytest.fixture
def envois_directs(monkeypatch):
    """Les courriels partent dans le fil de la requête : un fil détaché rendrait
    la main avant que le faux Brevo ait rien reçu, et la règle compterait zéro
    courriel pour une raison sans rapport avec ce qu'elle mesure."""
    class _Direct:
        def __init__(self, target=None, args=(), kwargs=None, daemon=None):
            self._t, self._a, self._k = target, args, kwargs or {}

        def start(self):
            self._t(*self._a, **self._k)
    monkeypatch.setattr(auth.threading, "Thread", _Direct)


def _caisse(client, email):
    return client.post("/api/paiement/checkout", headers=ENTETES,
                       json={"email": email, "professionnel": True,
                             "cgv": True, "renonciation": True})


def _session(email, **extra):
    """Une session de paiement telle que Stripe la met dans la notification :
    l'adresse TAPÉE au paiement diffère du compte lié, à dessein."""
    o = {"id": "cs_test_recette", "object": "checkout.session", "mode": "payment",
         "status": "complete", "payment_status": "paid", "amount_total": 49000,
         "currency": "eur", "client_reference_id": email,
         "customer_details": {"email": TAPEE_AU_PAIEMENT},
         "metadata": {"site": "conseilprevcyber"}}
    o.update(extra)
    return o


def _notifier(client, charge, signature=None):
    """POST de la notification comme Stripe la poste : sans Origin, avec son
    User-Agent. `signature` None : signée du secret de recette ; False : sans
    en-tête."""
    h = {"User-Agent": UA_STRIPE, "Content-Type": "application/json; charset=utf-8"}
    if signature is not False:
        h["Stripe-Signature"] = signature or signer_stripe(charge, SECRET_WEBHOOK_RECETTE)
    return client.post("/api/stripe/webhook", data=charge, headers=h)


def _courriels(fb):
    return [(q.json["to"][0]["email"], q.json["subject"])
            for q in fb.recues("POST", "/v3/smtp/email")]


def _lignes(caplog):
    return [r.getMessage() for r in caplog.records
            if r.name == "auth" and r.levelno >= logging.WARNING]


# ══════════════════════════════════════════════════════════════════════════
#  1. LA CAISSE : CE QUE LE SITE ENVOIE À STRIPE
# ══════════════════════════════════════════════════════════════════════════

def test_la_caisse_recoit_le_contrat_attendu(anonyme, faux_stripe, faux_brevo, acheteur):
    """Mode « payment » (un prix récurrent la ferait échouer), LE prix
    configuré, le compte lié par NOUS dans `client_reference_id`, les deux
    adresses de retour, et la clé de recette en autorisation."""
    r = _caisse(anonyme, acheteur)
    j = r.get_json()
    assert r.status_code == 200 and j.get("ok") is True, (
        "la route répond %s %s" % (r.status_code, j))
    assert j["url"].startswith(faux_stripe.url), (
        "l'URL rendue au navigateur n'est pas celle de la caisse ouverte : %s" % j["url"])
    envois = faux_stripe.recues("POST", "/v1/checkout/sessions")
    assert len(envois) == 1, "%d ouverture(s) de caisse reçue(s) par Stripe" % len(envois)
    q = envois[0]
    assert q.entetes.get("authorization") == "Bearer sk_test_recette_locale", (
        "autorisation envoyée : %r" % q.entetes.get("authorization"))
    assert q.entetes.get("content-type") == "application/x-www-form-urlencoded"
    assert q.entetes.get("stripe-version") == stripe.api_version, q.entetes.get("stripe-version")
    assert q.entetes.get("idempotency-key"), (
        "aucune Idempotency-Key : un réessai réseau ouvrirait deux caisses")
    base = A._base_url()
    attendu = {"mode": "payment",
               "line_items[0][price]": PRIX_RECETTE,
               "line_items[0][quantity]": "1",
               "client_reference_id": acheteur,
               "customer_email": acheteur,
               "success_url": base + "/connexion?paye=1",
               "cancel_url": base + "/connexion?paye=0",
               # LA MARQUE DU SITE : le compte Stripe est partagé avec
               # conseilprev, et c'est elle que la notification exige.
               "metadata[site]": "conseilprevcyber"}
    ecarts = {k: (q.form.get(k), v) for k, v in attendu.items() if q.form.get(k) != v}
    assert not ecarts, "champs envoyés à Stripe (observé, attendu) : %s" % ecarts
    assert auth.store.get(acheteur)["approved"] is False, (
        "ouvrir une caisse a ouvert l'accès : seule la notification signée le peut")


def test_une_panne_de_stripe_ferme_la_caisse_sans_500(anonyme, faux_stripe, faux_brevo,
                                                     acheteur):
    """Stripe répond 500 : le visiteur lit « momentanément indisponible » (502),
    pas une erreur interne, et l'accès n'a pas bougé."""
    faux_stripe.pannes["POST /v1/checkout/sessions"] = (
        500, {"error": {"type": "api_error", "message": "panne simulée"}})
    r = _caisse(anonyme, acheteur)
    assert r.status_code == 502 and r.get_json().get("error") == "caisse_indisponible", (
        "la route répond %s %s" % (r.status_code, r.get_json()))
    assert faux_stripe.recues("POST", "/v1/checkout/sessions"), "Stripe n'a pas été appelé"
    assert auth.store.get(acheteur)["approved"] is False


# ══════════════════════════════════════════════════════════════════════════
#  2. LA NOTIFICATION : LE SEUL CHEMIN QUI OUVRE, ET CE QU'IL EXIGE
# ══════════════════════════════════════════════════════════════════════════

def test_une_notification_signee_du_vrai_secret_ouvre_le_compte_et_confirme_la_commande(
        anonyme, faux_stripe, faux_brevo, acheteur, envois_directs):
    """Signée du secret que lit `paiement.py`, vérifiée par la vraie
    bibliothèque : l'accès s'ouvre sur l'adresse LIÉE (pas celle tapée au
    paiement), l'acheteur reçoit la confirmation de commande avec le montant
    SIGNÉ et la référence, l'exploitant est averti."""
    _, charge = evenement_stripe(_session(acheteur))
    r = _notifier(anonyme, charge)
    assert r.status_code == 200 and r.get_json() == {"ok": True, "traite": True}, (
        "la notification répond %s %s" % (r.status_code, r.get_json()))
    assert auth.store.get(acheteur)["approved"] is True, (
        "signature acceptée, et pourtant l'accès n'est pas ouvert")
    assert auth.store.get(TAPEE_AU_PAIEMENT) is None, (
        "l'adresse tapée au paiement a fait naître un compte")
    partis = faux_brevo.recues("POST", "/v3/smtp/email")
    a_l_acheteur = [q for q in partis if q.json["to"][0]["email"] == acheteur]
    assert len(a_l_acheteur) == 1, "courriels partis : %s" % _courriels(faux_brevo)
    corps = a_l_acheteur[0].json["htmlContent"]
    assert "490,00" in corps and "cs_test_recette" in corps, (
        "la confirmation ne porte ni le montant signé ni la référence : %s" % corps[:300])
    assert [q for q in partis if q.json["to"][0]["email"] == auth.ADMIN_EMAIL], (
        "l'exploitant n'est pas averti de l'ouverture : %s" % _courriels(faux_brevo))


@pytest.mark.parametrize("cas", ["alteree", "autre_secret", "perimee", "sans_v1", "absente"])
def test_une_signature_invalide_est_refusee_et_n_ouvre_rien(anonyme, faux_stripe, faux_brevo,
                                                            acheteur, envois_directs, cas):
    """Cinq façons d'imiter Stripe, toutes refusées en 400 : charge modifiée
    APRÈS signature, autre secret, horodatage hors des 300 s de tolérance,
    en-tête sans schéma v1, en-tête absent. Rien n'est ouvert, rien ne part."""
    _, charge = evenement_stripe(_session(acheteur))
    t = int(time.time())
    if cas == "alteree":
        signature = signer_stripe(charge, SECRET_WEBHOOK_RECETTE)
        charge = charge.replace(b'"livemode": false', b'"livemode": true')
    elif cas == "autre_secret":
        signature = signer_stripe(charge, "whsec_un_autre_point_de_reception")
    elif cas == "perimee":
        signature = signer_stripe(charge, SECRET_WEBHOOK_RECETTE, t=t - 301)
    elif cas == "sans_v1":
        signature = "t=%d,v0=%s" % (t, "0" * 64)
    else:
        signature = False
    r = _notifier(anonyme, charge, signature)
    assert r.status_code == 400 and r.get_json().get("error") == "signature_invalide", (
        "%s : la notification répond %s %s" % (cas, r.status_code, r.get_json()))
    assert auth.store.get(acheteur)["approved"] is False, (
        "%s : la signature est refusée et l'accès est ouvert quand même" % cas)
    assert not _courriels(faux_brevo), (
        "%s : des courriels sont partis : %s" % (cas, _courriels(faux_brevo)))


def test_un_paiement_non_encaisse_n_ouvre_rien(anonyme, faux_stripe, faux_brevo,
                                                acheteur, envois_directs):
    """`checkout.session.completed` arrive avec `payment_status: unpaid` pour un
    moyen différé (prélèvement) : l'argent n'est pas là. Acquittée (200) pour
    que Stripe ne la réémette pas, mais rien n'est ouvert."""
    _, charge = evenement_stripe(_session(acheteur, payment_status="unpaid"))
    r = _notifier(anonyme, charge)
    assert r.status_code == 200 and r.get_json() == {"ok": True, "traite": False}, (
        "la notification répond %s %s" % (r.status_code, r.get_json()))
    assert auth.store.get(acheteur)["approved"] is False, (
        "un paiement « unpaid » a ouvert l'accès")
    assert not _courriels(faux_brevo), "des courriels sont partis : %s" % _courriels(faux_brevo)


def test_le_rejeu_de_la_notification_n_ouvre_et_n_avertit_qu_une_fois(
        anonyme, faux_stripe, faux_brevo, acheteur, envois_directs):
    """Stripe réémet tant qu'il n'est pas acquitté, et rejoue sur demande : la
    même charge signée deux fois n'ouvre qu'une fois et n'écrit qu'une fois."""
    _, charge = evenement_stripe(_session(acheteur))
    assert _notifier(anonyme, charge).get_json()["traite"] is True
    n = len(_courriels(faux_brevo))
    r2 = _notifier(anonyme, charge)
    assert r2.status_code == 200 and r2.get_json()["traite"] is False, (
        "le rejeu répond %s %s" % (r2.status_code, r2.get_json()))
    assert len(_courriels(faux_brevo)) == n, (
        "le rejeu a renvoyé %d courriel(s)" % (len(_courriels(faux_brevo)) - n))


# ══════════════════════════════════════════════════════════════════════════
#  3. LE TARIF : LU CHEZ STRIPE, PAR LA VRAIE BIBLIOTHÈQUE
# ══════════════════════════════════════════════════════════════════════════

def test_le_tarif_est_lu_chez_stripe_avec_la_vraie_bibliotheque(faux_stripe):
    """LE DÉFAUT MESURÉ : Stripe répondait 200, et `tarif()` rendait None —
    `.get()` n'existe pas sur un objet Stripe 15.x, l'erreur était avalée."""
    t = paiement.tarif()
    lus = faux_stripe.recues("GET", "/v1/prices/" + PRIX_RECETTE, exact=True)
    assert t == TARIF_ATTENDU, (
        "tarif() rend %r alors que Stripe a répondu %d fois à GET /v1/prices/%s"
        % (t, len(lus), PRIX_RECETTE))
    assert len(lus) == 1, "%d lecture(s) du prix pour un seul tarif" % len(lus)
    assert lus[0].entetes.get("authorization") == "Bearer sk_test_recette_locale", (
        "autorisation envoyée : %r" % lus[0].entetes.get("authorization"))


def test_la_page_recoit_un_tarif_affichable(anonyme, faux_stripe):
    j = anonyme.get("/api/paiement/etat").get_json()
    assert j["configure"] is True, j
    assert (j.get("tarif") or {}).get("affichage") == "490,00 €", (
        "la page reçoit tarif=%r : aucun montant ne s'affiche" % (j.get("tarif"),))


def test_un_prix_recurrent_est_signale_par_la_console(admin, faux_stripe):
    """La caisse s'ouvre en `mode="payment"` : un prix récurrent la fait
    échouer à chaque tentative, sans que rien ne l'explique. La console le
    signale — à condition de pouvoir lire le prix."""
    faux_stripe.prix[PRIX_RECETTE] = {
        "id": PRIX_RECETTE, "object": "price", "active": True, "unit_amount": 4900,
        "currency": "eur", "recurring": {"interval": "month", "interval_count": 1}}
    r = admin.get("/api/admin/reglages")
    assert r.status_code == 200, r.status_code
    ecartes = [e for e in r.get_json()["ecartes"] if e["variable"] == paiement.CLE_PRIX]
    assert len(ecartes) == 1, (
        "la console ne signale pas le prix récurrent ; écarts signalés : %s"
        % [e["variable"] for e in r.get_json()["ecartes"]])
    assert "RÉCURRENT" in ecartes[0]["consequence"], ecartes[0]


def test_un_prix_unique_n_est_pas_signale_comme_recurrent(admin, faux_stripe):
    """La règle d'à côté doit DISCRIMINER : signaler tout prix la satisferait."""
    r = admin.get("/api/admin/reglages")
    ecartes = [e for e in r.get_json()["ecartes"] if e["variable"] == paiement.CLE_PRIX]
    assert ecartes == [], "un prix à paiement unique est signalé : %s" % ecartes


def test_le_tarif_est_garde_dix_minutes_puis_relu(faux_stripe):
    """Un aller-retour Stripe par affichage de page se paierait en latence chez
    le visiteur ; un cache sans fin cacherait un tarif changé."""
    assert paiement.tarif() == TARIF_ATTENDU
    paiement.tarif()
    n = len(faux_stripe.recues("GET", "/v1/prices/"))
    assert n == 1, "%d lectures chez Stripe pour deux affichages : le cache ne tient pas" % n
    assert paiement.TARIF_TTL_S == 600, paiement.TARIF_TTL_S
    with paiement._VERROU_TARIF:
        paiement._TARIF["lu_a"] = time.time() - paiement.TARIF_TTL_S - 1
    paiement.tarif()
    n = len(faux_stripe.recues("GET", "/v1/prices/"))
    assert n == 2, (
        "%d lecture(s) après l'expiration des dix minutes : un tarif changé chez "
        "Stripe resterait invisible" % n)


def test_un_prix_sans_montant_n_affiche_rien(faux_stripe):
    """Un prix « à la carte » (`unit_amount` nul) n'a pas de montant : on
    préfère ne rien dire plutôt qu'annoncer zéro — et ne rien garder."""
    faux_stripe.prix[PRIX_RECETTE] = {
        "id": PRIX_RECETTE, "object": "price", "active": True, "unit_amount": None,
        "currency": "eur", "recurring": None, "custom_unit_amount": {"minimum": 1000}}
    t = paiement.tarif()
    assert t is None, "un prix sans montant donne un tarif : %r" % (t,)
    assert paiement._TARIF["valeur"] is None, "un tarif vide a été mis en cache"


def test_une_panne_de_stripe_laisse_le_tarif_vide_et_n_est_pas_gardee(anonyme, faux_stripe):
    """La page vit sans prix pendant la panne ; dès que Stripe répond, le prix
    revient — l'échec n'a pas pris la place du tarif dans le cache."""
    faux_stripe.pannes["GET /v1/prices/" + PRIX_RECETTE] = (
        500, {"error": {"type": "api_error", "message": "panne simulée"}})
    r = anonyme.get("/api/paiement/etat")
    assert r.status_code == 200, r.status_code
    assert r.get_json()["tarif"] is None and r.get_json()["configure"] is True, r.get_json()
    del faux_stripe.pannes["GET /v1/prices/" + PRIX_RECETTE]
    t = paiement.tarif()
    assert t == TARIF_ATTENDU, "après la panne, tarif() rend %r : l'échec a été gardé" % (t,)


# ══════════════════════════════════════════════════════════════════════════
#  4. BREVO : LE CONTRAT, LE REFUS JOURNALISÉ, LE RÉESSAI BORNÉ
# ══════════════════════════════════════════════════════════════════════════

def test_l_envoi_brevo_porte_le_contrat_attendu(faux_brevo):
    ok = auth.send_email("client@example.test", "Client Essai", "Sujet — é", "<p>Corps</p>")
    assert ok is True, "send_email rend %r" % (ok,)
    recus = faux_brevo.recues("POST", "/v3/smtp/email")
    assert len(recus) == 1, "%d envoi(s) reçus" % len(recus)
    q = recus[0]
    assert q.entetes.get("api-key") == "xkeysib-recette-locale", q.entetes.get("api-key")
    assert q.entetes.get("content-type") == "application/json", q.entetes.get("content-type")
    assert q.entetes.get("accept") == "application/json", q.entetes.get("accept")
    assert q.json == {"sender": auth.SENDER,
                      "to": [{"email": "client@example.test", "name": "Client Essai"}],
                      "subject": "Sujet — é", "htmlContent": "<p>Corps</p>"}, q.json


@pytest.mark.parametrize("statut,code", [(400, "invalid_parameter"),
                                         (401, "unauthorized"),
                                         (402, "not_enough_credits")])
def test_un_refus_definitif_est_journalise_sans_adresse_et_sans_reessai(
        faux_brevo, caplog, statut, code):
    """LE DÉFAUT MESURÉ : un 400, un 401 (clé révoquée) ou un 402 (les 300
    envois du jour épuisés) rendait False sans AUCUNE trace. Le journal dit
    désormais le statut et le code de Brevo — sans l'adresse, que le sujet
    peut porter — et ne rejoue pas une faute qui ne s'arrangera pas seule."""
    faux_brevo.pannes["POST /v3/smtp/email"] = (
        statut, {"code": code, "message": "refus simulé pour client@example.test"})
    with caplog.at_level(logging.WARNING, logger="auth"):
        ok = auth.send_email("client@example.test", "Client",
                             "Accès ouvert par paiement — client@example.test", "<p/>")
    assert ok is False, "send_email rend %r sur un %d" % (ok, statut)
    n = len(faux_brevo.recues("POST", "/v3/smtp/email"))
    assert n == 1, "%d envoi(s) pour un refus définitif %d : rejouer une faute ne la corrige pas" % (n, statut)
    lignes = _lignes(caplog)
    assert any(str(statut) in l and code in l for l in lignes), (
        "le refus HTTP %d (%s) n'est pas journalisé ; journal : %s" % (statut, code, lignes))
    texte = "\n".join(lignes)
    assert "client@example.test" not in texte, "l'adresse est en clair dans le journal : %s" % texte
    assert "xkeysib" not in texte, "la clé est dans le journal"


@pytest.mark.parametrize("statut", [429, 500, 503])
def test_un_refus_passager_est_rejoue_deux_fois_au_plus(faux_brevo, statut):
    """Cadence (429) ou panne (5xx) : ce qui peut s'arranger seul est rejoué —
    deux fois, pas plus. Un courriel d'activation perdu sur un 503 passager ne
    revient jamais : rien en amont ne rejoue un envoi manqué."""
    faux_brevo.pannes["POST /v3/smtp/email"] = (statut, {"code": "temporaire"})
    ok = auth.send_email("client@example.test", "Client", "Sujet", "<p/>")
    assert ok is False, "send_email rend %r après trois %d" % (ok, statut)
    n = len(faux_brevo.recues("POST", "/v3/smtp/email"))
    assert n == 3, "%d envoi(s) reçus pour un %d : attendu 1 essai + 2 réessais" % (n, statut)


def test_un_envoi_qui_aboutit_au_second_essai_rend_vrai(faux_brevo):
    reponses = [(502, {"code": "bad_gateway"})]

    def gestionnaire(_r):
        return reponses.pop() if reponses else (201, {"messageId": "<ok@smtp-relay.mailin.fr>"})
    faux_brevo.route("POST", "/v3/smtp/email", gestionnaire)
    ok = auth.send_email("client@example.test", "Client", "Sujet", "<p/>")
    n = len(faux_brevo.recues("POST", "/v3/smtp/email"))
    assert ok is True, "un 502 passager a perdu le courriel (%d envoi(s), rend %r)" % (n, ok)
    assert n == 2, "%d envoi(s) reçus" % n


def test_un_delai_depasse_est_rejoue_puis_journalise(faux_brevo, caplog, monkeypatch):
    """Brevo qui ne répond pas dans le délai n'est pas un refus : on rejoue,
    puis on le dit."""
    monkeypatch.setattr(auth, "BREVO_DELAI_S", 0.2, raising=False)
    faux_brevo.lenteurs["POST /v3/smtp/email"] = 0.8
    with caplog.at_level(logging.WARNING, logger="auth"):
        ok = auth.send_email("client@example.test", "Client", "Sujet", "<p/>")
    n = len(faux_brevo.recues("POST", "/v3/smtp/email"))
    assert ok is False, "send_email rend %r alors que Brevo n'a jamais répondu" % (ok,)
    assert n == 3, "%d envoi(s) reçus : attendu 1 essai + 2 réessais" % n
    lignes = _lignes(caplog)
    assert any("Timeout" in l for l in lignes), "le délai dépassé n'est pas journalisé : %s" % lignes


def test_sans_cle_rien_ne_part_et_le_journal_le_dit(faux_brevo, caplog, monkeypatch):
    monkeypatch.delenv("BREVO_API_KEY", raising=False)
    with caplog.at_level(logging.WARNING, logger="auth"):
        ok = auth.send_email("client@example.test", "Client", "Sujet", "<p/>")
    assert ok is False
    assert not faux_brevo.recues("POST", "/v3/smtp/email"), "un envoi est parti sans clé"
    assert any("BREVO_API_KEY" in l for l in _lignes(caplog)), _lignes(caplog)


def test_la_garde_reseau_refuse_toute_connexion_hors_des_faux_serveurs(
        faux_brevo, monkeypatch):
    """La garde est ce qui rend ces règles sûres : une adresse qui n'est pas
    celle d'un faux serveur est refusée à la connexion — l'envoi échoue vite,
    sans avoir rien envoyé nulle part."""
    monkeypatch.setattr(auth, "BREVO_API_URL", "http://127.0.0.1:9/v3/smtp/email")
    debut = time.time()
    ok = auth.send_email("client@example.test", "Client", "Sujet", "<p/>")
    assert ok is False, "send_email rend %r vers un port qui n'est pas un faux serveur" % (ok,)
    assert not faux_brevo.requetes, "le faux serveur a reçu quelque chose : %s" % faux_brevo.requetes
    assert time.time() - debut < 5, "la garde a laissé l'envoi attendre le réseau"


# ══════════════════════════════════════════════════════════════════════════
#  5. LA RÉCEPTION CROISÉE : LE COMPTE STRIPE EST PARTAGÉ AVEC CONSEILPREV
# ══════════════════════════════════════════════════════════════════════════
#
# CE QUI A ÉTÉ MESURÉ. Le point de réception de ce site reçoit TOUS les
# `checkout.session.completed` du compte — formations et abonnements Sentinel
# de conseilprev compris. Le code d'avant ne regardait que `client_reference_
# id` : une session Sentinel (référence « 42 ») ou une formation IA (référence
# « FIA-2026-0042 ») laissait une trace d'audit « compte.paiement.inconnu » à
# chaque vente de l'autre site ; et une session de l'autre site dont la
# référence ÉTAIT une adresse connue ici OUVRAIT un accès payé ailleurs.

SESSIONS_CONSEILPREV = {
    # La formation IA : référence = numéro de commande, adresse renseignée.
    "formation_ia": dict(
        id="cs_test_formation_ia", client_reference_id="FIA-2026-0042",
        customer_email=ACHETEUR, customer_details={"email": ACHETEUR},
        metadata={"type": "formation-ia", "commande": "FIA-2026-0042", "resa_id": "7"}),
    # L'abonnement Sentinel : référence = identifiant client, marque du site.
    "sentinel_pro": dict(
        id="cs_test_sentinel_pro", mode="subscription", client_reference_id="42",
        customer_email=ACHETEUR, customer_details={"email": ACHETEUR},
        amount_total=4900,
        metadata={"client_id": "42", "plan": "pro", "site": "conseilprev"}),
    # Le cas qui OUVRAIT : une session de l'autre site dont la référence est
    # une adresse qui a un compte ICI.
    "reference_egale_a_un_compte_ici": dict(
        id="cs_test_formation", client_reference_id=ACHETEUR,
        customer_email=ACHETEUR, customer_details={"email": ACHETEUR},
        metadata={"type": "formation", "inscription_id": "12", "session_id": "3"}),
}


@pytest.fixture
def traces(monkeypatch):
    """Les traces d'audit écrites par l'ouverture — (action, cible, ok)."""
    vues = []
    vrai = auth._tracer

    def espion(action, email, detail="", ok=True, role="-"):
        vues.append((action, email, ok))
        return vrai(action, email, detail, ok=ok, role=role)
    monkeypatch.setattr(auth, "_tracer", espion)
    return vues


@pytest.mark.parametrize("cas", sorted(SESSIONS_CONSEILPREV))
def test_une_vente_de_conseilprev_est_acquittee_sans_effet_ni_trace(
        anonyme, faux_stripe, faux_brevo, acheteur, envois_directs, traces, cas):
    """Acquittée 200 — sinon Stripe réessaierait trois jours ce qui ne nous
    regarde pas —, sans ouvrir, sans écrire, sans trace d'audit, et sans
    appel à Stripe : la marque de l'autre site suffit à décider."""
    _, charge = evenement_stripe(_session(acheteur, **SESSIONS_CONSEILPREV[cas]))
    r = _notifier(anonyme, charge)
    assert r.status_code == 200 and r.get_json() == {"ok": True, "traite": False}, (
        "%s : la notification répond %s %s" % (cas, r.status_code, r.get_json()))
    assert auth.store.get(acheteur)["approved"] is False, (
        "%s : une vente de conseilprev a ouvert un accès ICI" % cas)
    assert traces == [], "%s : traces d'audit parasites : %s" % (cas, traces)
    assert not _courriels(faux_brevo), (
        "%s : des courriels sont partis : %s" % (cas, _courriels(faux_brevo)))
    assert not faux_stripe.requetes, (
        "%s : Stripe a été interrogé pour rien : %s" % (cas, faux_stripe.requetes))


def _lignes_de_caisse(faux_stripe, sid, prix):
    """GET /v1/checkout/sessions/<sid>/line_items rend UNE ligne au prix donné."""
    def gestionnaire(r):
        return 200, {"object": "list", "has_more": False,
                     "url": "/v1/checkout/sessions/%s/line_items" % sid,
                     "data": [{"id": "li_1", "object": "item", "quantity": 1,
                               "amount_total": 49000, "currency": "eur",
                               "price": {"id": prix, "object": "price",
                                         "unit_amount": 49000, "currency": "eur"}}]}
    faux_stripe.route("GET", "/v1/checkout/sessions/%s/line_items" % sid, gestionnaire)


def test_une_caisse_ouverte_avant_la_marque_est_reconnue_a_son_prix(
        anonyme, faux_stripe, faux_brevo, acheteur, envois_directs):
    """UNE CAISSE VIT 24 HEURES. Celles ouvertes avant la mise en ligne de la
    marque n'en portent aucune (`metadata` vide) : on lit alors sa ligne chez
    Stripe, et c'est LE prix de ce site qui la fait reconnaître — sans quoi un
    paiement encaissé le jour du déploiement n'ouvrirait rien."""
    _lignes_de_caisse(faux_stripe, "cs_test_ancienne", PRIX_RECETTE)
    _, charge = evenement_stripe(_session(acheteur, id="cs_test_ancienne", metadata={}))
    r = _notifier(anonyme, charge)
    assert r.status_code == 200 and r.get_json() == {"ok": True, "traite": True}, (
        "la notification répond %s %s" % (r.status_code, r.get_json()))
    assert auth.store.get(acheteur)["approved"] is True
    lus = faux_stripe.recues("GET", "/v1/checkout/sessions/cs_test_ancienne/line_items")
    assert len(lus) == 1, "%d lecture(s) de la ligne de caisse" % len(lus)


def test_une_caisse_sans_marque_a_un_autre_prix_est_ignoree(
        anonyme, faux_stripe, faux_brevo, acheteur, envois_directs, traces):
    """Sans marque ET à un autre prix (un lien de paiement créé à la main dans
    le tableau de bord, par exemple) : ce n'est pas une vente de ce site."""
    _lignes_de_caisse(faux_stripe, "cs_test_lien", "price_formation_conseilprev")
    _, charge = evenement_stripe(_session(acheteur, id="cs_test_lien", metadata={}))
    r = _notifier(anonyme, charge)
    assert r.status_code == 200 and r.get_json() == {"ok": True, "traite": False}, (
        "la notification répond %s %s" % (r.status_code, r.get_json()))
    assert auth.store.get(acheteur)["approved"] is False, (
        "une caisse à un autre prix a ouvert un accès")
    assert traces == [], "traces d'audit parasites : %s" % traces


def test_une_caisse_sans_marque_illisible_repond_500_pour_etre_rejouee(
        anonyme, faux_stripe, faux_brevo, acheteur, envois_directs):
    """Stripe ne rend pas la ligne : on ne SAIT pas si la vente est la nôtre.
    L'acquitter la perdrait pour de bon ; 500 la fait réémettre par Stripe."""
    faux_stripe.pannes["GET /v1/checkout/sessions/cs_test_ancienne/line_items"] = (
        500, {"error": {"type": "api_error", "message": "panne simulée"}})
    _, charge = evenement_stripe(_session(acheteur, id="cs_test_ancienne", metadata={}))
    r = _notifier(anonyme, charge)
    assert r.status_code == 500, (
        "la notification répond %s %s : Stripe ne la réémettra pas"
        % (r.status_code, r.get_json()))
    assert auth.store.get(acheteur)["approved"] is False
    del faux_stripe.pannes["GET /v1/checkout/sessions/cs_test_ancienne/line_items"]
    _lignes_de_caisse(faux_stripe, "cs_test_ancienne", PRIX_RECETTE)
    r = _notifier(anonyme, charge)
    assert r.status_code == 200 and r.get_json()["traite"] is True, (
        "la réémission répond %s %s" % (r.status_code, r.get_json()))


# ══════════════════════════════════════════════════════════════════════════
#  6. UN ÉCHEC D'OUVERTURE N'EST PAS ACQUITTÉ
# ══════════════════════════════════════════════════════════════════════════

def test_un_echec_d_ouverture_repond_500_puis_la_reemission_ouvre(
        anonyme, faux_stripe, faux_brevo, acheteur, envois_directs, monkeypatch, caplog):
    """LE DÉFAUT MESURÉ : le magasin de comptes lève (base injoignable), la
    notification répondait 200 `traite: false` — Stripe tenait le paiement
    pour livré et ne réémettait JAMAIS. Payé, fermé, et rien pour rattraper.
    Désormais 500 et une ligne de journal ; l'ouverture étant idempotente, la
    réémission de Stripe ouvre l'accès une fois la base revenue."""
    vrai = auth.store.update

    def en_panne(*a, **k):
        raise RuntimeError("magasin injoignable")
    monkeypatch.setattr(auth.store, "update", en_panne)
    _, charge = evenement_stripe(_session(acheteur))
    with caplog.at_level(logging.ERROR):
        r = _notifier(anonyme, charge)
    assert r.status_code == 500, (
        "la notification répond %s %s : Stripe ne la réémettra jamais"
        % (r.status_code, r.get_json()))
    assert auth.store.get(acheteur)["approved"] is False
    erreurs = [x for x in caplog.records if x.levelno >= logging.ERROR]
    assert erreurs, "l'échec d'ouverture n'est pas journalisé"
    assert acheteur not in "\n".join(x.getMessage() for x in erreurs), (
        "l'adresse de l'acheteur est en clair dans le journal")
    monkeypatch.setattr(auth.store, "update", vrai)
    r = _notifier(anonyme, charge)
    assert r.status_code == 200 and r.get_json() == {"ok": True, "traite": True}, (
        "la réémission répond %s %s" % (r.status_code, r.get_json()))
    assert auth.store.get(acheteur)["approved"] is True
