# -*- coding: utf-8 -*-
"""Faux Stripe et faux Brevo : de VRAIS serveurs HTTP sur 127.0.0.1.

POURQUOI UN SERVEUR ET PAS UN FAUX MODULE. Le faux module `stripe` des essais
de test_formation_ia_paiement.py remplace la bibliothèque : il rend des `dict`
là où la bibliothèque 15.x rend des `StripeObject` — qui NE SONT PAS des dict
et n'ont pas de `.get()` —, et son `construct_event` accepte n'importe quelle
signature. Trois défauts réels (facture RaaS, changement d'offre, tarif du site
cyber) passaient ainsi au vert. Ici, la VRAIE bibliothèque `stripe` et le VRAI
`requests` de l'envoi Brevo parlent à un serveur local qui NOTE tout ce qu'il
reçoit : corps encodé, en-têtes (Authorization, Idempotency-Key, api-key),
chemin exact. C'est ce qu'on mesure.

Aucun accès réseau : écoute sur 127.0.0.1, port 0 par défaut (le système en
choisit un libre) ; `FAUX_STRIPE_PORT` / `FAUX_BREVO_PORT` imposent un port.

ÉTENDRE SANS TOUCHER CE FICHIER. Une règle qui a besoin d'une route de plus
l'enregistre sur l'instance :

    faux_stripe.route("GET", "/v1/customers", lambda r: (200, {...}))
    faux_stripe.route("GET", "/v1/subscriptions/", gestionnaire, prefixe=True)

Une route enregistrée passe AVANT les réponses par défaut ; `pannes` (statut
imposé) et `lenteurs` (secondes d'attente) passent avant tout.
"""
import hashlib
import hmac
import itertools
import json
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def signer_stripe(charge, secret, t=None):
    """L'en-tête `Stripe-Signature` tel que Stripe le calcule :
    t=<horodatage>,v1=HMAC-SHA256(secret, "<t>.<charge brute>")."""
    if isinstance(charge, str):
        charge = charge.encode("utf-8")
    t = int(time.time()) if t is None else int(t)
    mac = hmac.new(secret.encode("utf-8"), b"%d." % t + charge,
                   hashlib.sha256).hexdigest()
    return "t=%d,v1=%s" % (t, mac)


def evenement_stripe(objet, type_="checkout.session.completed", evt=None):
    """(identifiant, charge brute) d'une notification Stripe réaliste."""
    evt = evt or "evt_recette_%d" % int(time.time() * 1e6)
    charge = json.dumps({
        "id": evt, "object": "event", "api_version": "2026-05-27.dahlia",
        "created": int(time.time()), "livemode": False, "type": type_,
        "data": {"object": objet}}).encode("utf-8")
    return evt, charge


class Requete(object):
    def __init__(self, methode, chemin, requete, entetes, corps):
        self.methode = methode
        self.chemin = chemin
        self.requete = requete                    # paramètres d'URL (listes)
        self.entetes = entetes                    # noms en minuscules
        self.corps = corps                        # octets bruts
        self.form = {}
        self.json = None
        ct = entetes.get("content-type", "")
        if "application/x-www-form-urlencoded" in ct:
            self.form = {k: v[-1] for k, v in urllib.parse.parse_qs(
                corps.decode("utf-8"), keep_blank_values=True).items()}
        elif "json" in ct and corps:
            self.json = json.loads(corps.decode("utf-8"))

    def __repr__(self):
        return "<%s %s>" % (self.methode, self.chemin)


class _Gestionnaire(BaseHTTPRequestHandler):
    def log_message(self, *a):                               # silence
        pass

    def _traiter(self):
        n = int(self.headers.get("Content-Length") or 0)
        corps = self.rfile.read(n) if n else b""
        u = urllib.parse.urlsplit(self.path)
        r = Requete(self.command, u.path, urllib.parse.parse_qs(u.query),
                    {k.lower(): v for k, v in self.headers.items()}, corps)
        faux = self.server.faux
        with faux.verrou:
            faux.requetes.append(r)
        cle = "%s %s" % (r.methode, r.chemin)
        attente = faux.lenteurs.get(cle)
        if attente:
            time.sleep(attente)
        panne = faux.pannes.get(cle)
        if panne:
            statut, charge = panne
        else:
            statut, charge = faux._repondre(r)
        brut = charge if isinstance(charge, bytes) else json.dumps(charge).encode()
        self.send_response(statut)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(brut)))
        self.end_headers()
        self.wfile.write(brut)

    do_GET = do_POST = do_DELETE = _traiter


class _FauxServeur(object):
    def __init__(self, port=0):
        self.port_demande = port
        self.requetes = []
        self.verrou = threading.Lock()
        self.pannes = {}         # "POST /v1/..." -> (statut, corps)
        self.lenteurs = {}       # "GET /v1/..."  -> secondes
        self._routes = []        # (methode, chemin, prefixe, gestionnaire)
        self._n = itertools.count(1)

    def demarrer(self):
        self.serveur = ThreadingHTTPServer(("127.0.0.1", self.port_demande),
                                           _Gestionnaire)
        self.serveur.daemon_threads = True
        self.serveur.faux = self
        self.port = self.serveur.server_address[1]
        self.url = "http://127.0.0.1:%d" % self.port
        # poll_interval : shutdown() attend la fin d'un tour de boucle ; à
        # 0,5 s (défaut) chaque essai payait 0,5 s d'arrêt par serveur.
        self.fil = threading.Thread(target=self.serveur.serve_forever,
                                    kwargs={"poll_interval": 0.02}, daemon=True)
        self.fil.start()
        return self

    def arreter(self):
        self.serveur.shutdown()
        self.serveur.server_close()

    def route(self, methode, chemin, gestionnaire, prefixe=False):
        """Ajoute (ou remplace) une réponse : gestionnaire(requete) -> (statut, dict)."""
        self._routes.insert(0, (methode, chemin, prefixe, gestionnaire))

    def recues(self, methode=None, chemin=None, exact=False):
        """Les requêtes reçues, filtrées. `exact` : le chemin entier, pas un
        préfixe (« /v1/invoices » attraperait sinon « …/finalize »)."""
        with self.verrou:
            return [r for r in self.requetes
                    if (methode is None or r.methode == methode)
                    and (chemin is None
                         or (r.chemin == chemin if exact
                             else r.chemin.startswith(chemin)))]

    def _repondre(self, r):
        for methode, chemin, prefixe, g in self._routes:
            if methode == r.methode and (
                    r.chemin.startswith(chemin) if prefixe else r.chemin == chemin):
                return g(r)
        return self.repondre(r)


class FauxStripe(_FauxServeur):
    """Imite les routes de l'API v1 que le code appelle.

    Les sessions de paiement créées sont GARDÉES (`sessions`) : leur relecture
    rend ce qui a été créé ; `payer(id)` la fait passer à « complete / paid ».
    Les abonnements sont gardés dans `abonnements` (id -> dict) ; un abonnement
    inconnu est actif, au prix `price_ancien`.
    """

    def __init__(self, port=0):
        super(FauxStripe, self).__init__(port)
        self.points = []           # /v1/webhook_endpoints
        self.remboursements = {}   # Idempotency-Key -> remboursement
        self.sessions = {}         # id -> checkout.session
        self.abonnements = {}      # id -> subscription
        self.prix = {}             # id -> price (défaut : 490 € ponctuel)
        self.compte = {"id": "acct_recette", "object": "account",
                       "charges_enabled": True, "payouts_enabled": True,
                       "details_submitted": True, "livemode": False,
                       "settings": {"dashboard": {"display_name": "CONSEILPREV"}}}

    def payer(self, sid, **extra):
        s = self.sessions[sid]
        s.update({"status": "complete", "payment_status": "paid",
                  "payment_intent": "pi_%s" % sid})
        s.update(extra)
        return s

    def _abonnement(self, sid):
        return self.abonnements.setdefault(sid, {
            "id": sid, "object": "subscription", "status": "active",
            "metadata": {},
            "items": {"object": "list", "data": [
                {"id": "si_%s" % sid, "object": "subscription_item",
                 "current_period_end": int(time.time()) + 30 * 86400,
                 "price": {"id": "price_ancien", "object": "price",
                           "unit_amount": 4900, "currency": "eur",
                           "recurring": {"interval": "month"}}}]}})

    def repondre(self, r):
        f, p = r.form, r.chemin
        if r.methode == "POST" and p == "/v1/checkout/sessions":
            i = next(self._n)
            sid = "cs_test_%d" % i
            meta = {k[9:-1]: v for k, v in f.items() if k.startswith("metadata[")}
            s = {"id": sid, "object": "checkout.session",
                 "url": "%s/pay/%s" % (self.url, sid),
                 "mode": f.get("mode"), "status": "open",
                 "payment_status": "unpaid", "metadata": meta,
                 "client_reference_id": f.get("client_reference_id"),
                 "customer": f.get("customer"),
                 "customer_email": f.get("customer_email"),
                 "success_url": f.get("success_url"),
                 "cancel_url": f.get("cancel_url"),
                 "expires_at": int(f["expires_at"]) if f.get("expires_at")
                 else int(time.time()) + 86400,
                 "amount_total": None, "subscription": None,
                 "payment_intent": None}
            self.sessions[sid] = s
            return 200, s
        if r.methode == "GET" and p.startswith("/v1/checkout/sessions/"):
            sid = p.rsplit("/", 1)[1]
            if sid in self.sessions:
                return 200, self.sessions[sid]
            return 200, {"id": sid, "object": "checkout.session",
                         "payment_intent": "pi_test_%s" % sid,
                         "payment_status": "paid", "status": "complete",
                         "metadata": {}}
        if r.methode == "POST" and p == "/v1/refunds":
            cle = r.entetes.get("idempotency-key")
            if cle not in self.remboursements:
                self.remboursements[cle] = {
                    "id": "re_test_%d" % next(self._n), "object": "refund",
                    "amount": int(f.get("amount") or 0),
                    "payment_intent": f.get("payment_intent"),
                    "status": "succeeded"}
            return 200, self.remboursements[cle]
        if p == "/v1/webhook_endpoints":
            if r.methode == "POST":
                ev = [v for k, v in sorted(f.items()) if k.startswith("enabled_events[")]
                we = {"id": "we_test_%d" % next(self._n), "object": "webhook_endpoint",
                      "url": f.get("url"), "enabled_events": ev,
                      "api_version": f.get("api_version"), "status": "enabled",
                      "secret": "whsec_recette_%d" % next(self._n)}
                self.points.append(we)
                return 200, we
            return 200, {"object": "list", "url": "/v1/webhook_endpoints",
                         "has_more": False,
                         "data": [dict(w, secret=None) for w in self.points]}
        if r.methode == "GET" and p == "/v1/account":
            return 200, self.compte
        if r.methode == "POST" and p == "/v1/tax_rates":
            return 200, {"id": "txr_test_%d" % next(self._n), "object": "tax_rate",
                         "percentage": float(f.get("percentage") or 0)}
        if r.methode == "GET" and p.startswith("/v1/tax_rates/"):
            return 200, {"id": p.rsplit("/", 1)[1], "object": "tax_rate",
                         "percentage": 20.0, "inclusive": False, "active": True}
        if r.methode == "POST" and p == "/v1/invoiceitems":
            return 200, {"id": "ii_test_%d" % next(self._n), "object": "invoiceitem",
                         "invoice": f.get("invoice"),
                         "amount": int(f.get("amount") or 0)}
        if r.methode == "POST" and p == "/v1/invoices":
            return 200, {"id": "in_test_%d" % next(self._n), "object": "invoice",
                         "status": "draft", "metadata": {
                             k[9:-1]: v for k, v in f.items()
                             if k.startswith("metadata[")}}
        if r.methode == "POST" and p.startswith("/v1/invoices/") and p.endswith("/finalize"):
            return 200, {"id": p.split("/")[3], "object": "invoice", "status": "open"}
        if p.startswith("/v1/subscriptions/"):
            sid = p.rsplit("/", 1)[1]
            a = self._abonnement(sid)
            if r.methode == "DELETE":
                a["status"] = "canceled"
            elif r.methode == "POST" and f.get("items[0][price]"):
                a["items"]["data"][0]["price"] = dict(
                    a["items"]["data"][0]["price"], id=f["items[0][price]"])
            return 200, a
        if r.methode == "GET" and p.startswith("/v1/prices/"):
            pid = p.rsplit("/", 1)[1]
            return 200, self.prix.get(pid, {
                "id": pid, "object": "price", "active": True,
                "unit_amount": 49000, "currency": "eur", "recurring": None})
        return 404, {"error": {"type": "invalid_request_error",
                               "message": "Unrecognized request URL (%s: %s)"
                                          % (r.methode, p)}}


class FauxBrevo(_FauxServeur):
    """Imite POST /v3/smtp/email, POST /v3/contacts, GET /v3/senders et
    GET /v3/account — l'expéditeur vérifié et l'offre gratuite du compte réel,
    relevés le 24 septembre 2026 (300 envois par jour)."""

    def __init__(self, port=0):
        super(FauxBrevo, self).__init__(port)
        self.expediteurs = [{"id": 1, "name": "CONSEILPREV",
                             "email": "christophe.cerf@i-aes.com", "active": True}]
        self.credits = 300

    def repondre(self, r):
        if r.methode == "POST" and r.chemin == "/v3/smtp/email":
            return 201, {"messageId": "<recette-%d@smtp-relay.mailin.fr>" % next(self._n)}
        if r.methode == "POST" and r.chemin == "/v3/contacts":
            return 201, {"id": next(self._n)}
        if r.methode == "GET" and r.chemin == "/v3/senders":
            return 200, {"senders": self.expediteurs}
        if r.methode == "GET" and r.chemin == "/v3/account":
            return 200, {"email": "compte@exemple.test",
                         "plan": [{"type": "free", "creditsType": "sendLimit",
                                   "credits": self.credits}]}
        return 404, {"code": "not_found", "message": "Invalid route"}
