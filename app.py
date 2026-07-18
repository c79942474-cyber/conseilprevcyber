"""CONSEILPREV Cyber — application web Flask.

Sert les pages statiques du site, expose un point de santé pour Render,
traite le formulaire de contact via l'API transactionnelle Brevo et alimente
le cockpit de supervision OT (démo + flux temps réel SSE).

Démarrage local :  python app.py
Production (Render) :  gunicorn -k gthread --threads 8 --timeout 120 app:app

Variables d'environnement :
  BREVO_API_KEY  — clé API Brevo (transactional email). Si absente, le
                   formulaire bascule côté client sur un lien mailto.
  INGEST_TOKEN   — jeton partagé protégeant POST /api/ingest (flux temps réel
                   du cockpit). Si absent, l'ingestion est désactivée et le
                   cockpit reste en mode démo (données simulées).
"""
import html as html_lib
import json
import os
import queue
import threading
import time

import requests
from flask import Flask, Response, jsonify, request, send_from_directory

app = Flask(__name__)
HERE = os.path.dirname(os.path.abspath(__file__))

# --- Configuration email (expéditeur vérifié Brevo) ---------------------------
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
SENDER = {"name": "CONSEILPREV", "email": "christophe.cerf@i-aes.com"}
NOTIFY_TO = "christophe.cerf@outlook.com"

# --- Flux temps réel du cockpit (SSE) -----------------------------------------
# Jeton protégeant l'ingestion : sans lui, /api/ingest est fermé (503) et le
# cockpit /demo reste en mode démonstration (données simulées).
INGEST_TOKEN = os.environ.get("INGEST_TOKEN")


class _Broker:
    """Diffuseur pub/sub en mémoire pour le flux Server-Sent Events.

    Chaque client SSE obtient sa propre file ; publish() y dépose l'événement.
    Suffisant pour une démo / un pilote mono-instance (pas de persistance,
    pas de partage entre workers — voir docs/integration-donnees-reelles.md).
    """

    def __init__(self):
        self._subs = set()
        self._lock = threading.Lock()

    def subscribe(self):
        q = queue.Queue(maxsize=200)
        with self._lock:
            self._subs.add(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            self._subs.discard(q)

    def publish(self, data):
        with self._lock:
            subs = list(self._subs)
        for q in subs:
            try:
                q.put_nowait(data)
            except queue.Full:
                pass  # client trop lent : on saute l'événement pour ne pas bloquer


broker = _Broker()

# --- État courant du cockpit (inventaire + alertes + événements récents) -------
# Les 5 zones IEC 62443 du cockpit (doivent correspondre à demo.html).
ZONES_META = [
    ("ent", "Entreprise (IT)", "Niv. 4-5"),
    ("dmz", "DMZ industrielle", "Niv. 3.5"),
    ("sup", "Supervision (SCADA)", "Niv. 3"),
    ("cel", "Cellule / Contrôle", "Niv. 2"),
    ("ter", "Terrain (capteurs)", "Niv. 0-1"),
]
_ZONE_ID_BY_NAME = {name: zid for zid, name, _ in ZONES_META}


def _tag_for(evt):
    """Catégorise un événement (disc/crit/warn/patch/info) — miroir de la logique cockpit."""
    t = (evt.get("type") or "").lower()
    s = (evt.get("severity") or "").lower()
    if "patch" in t or "correctif" in t:
        return "patch"
    if "disc" in t or "découv" in t or "asset" in t or "inventaire" in t:
        return "disc"
    if "crit" in s or s in ("high", "élevé", "eleve"):
        return "crit"
    if "warn" in s or s in ("medium", "moyen") or "avert" in s:
        return "warn"
    return "info"


class CockpitState:
    """État courant alimenté par les événements ingérés (thread-safe).

    Permet à un cockpit fraîchement ouvert d'afficher immédiatement l'inventaire,
    les alertes actives et les derniers événements (instantané), avant de recevoir
    les nouveautés en flux. En mémoire (mono-instance), comme le broker.
    """

    MAX_EVENTS = 50

    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        with self._lock:
            self.assets = 0
            self.alerts = 0
            self.risk = 50.0
            self.zones = {zid: {"id": zid, "name": name, "level": lvl, "count": 0, "status": "ok"}
                          for zid, name, lvl in ZONES_META}
            self.events = []  # ordre chronologique (ancien -> récent)

    def apply(self, evt):
        """Applique un événement normalisé ; renvoie (événement enrichi du tag, instantané)."""
        tag = _tag_for(evt)
        with self._lock:
            zone = self.zones.get(_ZONE_ID_BY_NAME.get(evt.get("zone", "")))
            if tag == "disc":
                if zone:
                    zone["count"] += 1
                self.assets += 1
                self.risk = min(98.0, self.risk + 0.4)
            elif tag == "crit":
                self.alerts += 1
                if zone:
                    zone["status"] = "alert"
                self.risk = min(98.0, self.risk + 2)
            elif tag == "warn":
                if zone:
                    zone["status"] = "watch"
            elif tag == "info":
                self.alerts = max(0, self.alerts - 1)
                self.risk = max(0.0, self.risk - 1)
                if zone:
                    zone["status"] = "ok"
            # patch : trace sans impact sur les compteurs
            text = evt.get("event") or evt.get("asset") or "Événement"
            if evt.get("zone"):
                text += " — " + evt["zone"]
            self.events.append({"tag": tag, "text": text, "ts": evt.get("ts")})
            if len(self.events) > self.MAX_EVENTS:
                self.events = self.events[-self.MAX_EVENTS:]
            return dict(evt, tag=tag), self._snapshot_locked()

    def _snapshot_locked(self):
        return {
            "assets": self.assets,
            "alerts": self.alerts,
            "risk": round(self.risk),
            "zones": [dict(z) for z in self.zones.values()],
            "events": list(self.events),
        }

    def snapshot(self):
        with self._lock:
            return self._snapshot_locked()


state = CockpitState()

# URL propre -> fichier HTML servi
PAGES = {
    "/": "index.html",
    "/services": "services.html",
    "/etudes-de-cas": "etudes-de-cas.html",
    "/referentiel": "referentiel.html",
    "/analyse-de-risque": "analyse-de-risque.html",
    "/secteurs": "secteurs.html",
    "/methodologie": "methodologie.html",
    "/exigences-systeme": "exigences-systeme.html",
    "/exigences-composants": "exigences-composants.html",
    "/exigences-prestataires": "exigences-prestataires.html",
    "/developpement-securise": "developpement-securise.html",
    "/technologies-securite": "technologies-securite.html",
    "/programme-securite": "programme-securite.html",
    "/gestion-correctifs": "gestion-correctifs.html",
    "/glossaire-62443": "glossaire-62443.html",
    "/metriques-62443": "metriques-62443.html",
    "/demo": "demo.html",
    "/ressources": "ressources.html",
    "/faq": "faq.html",
    "/about": "about.html",
    "/contact": "contact.html",
    "/mentions-legales": "mentions-legales.html",
}


def _page(filename):
    return send_from_directory(HERE, filename)


@app.route("/")
def index():
    return _page(PAGES["/"])


@app.route("/services")
def services():
    return _page(PAGES["/services"])


@app.route("/etudes-de-cas")
def etudes_de_cas():
    return _page(PAGES["/etudes-de-cas"])


@app.route("/referentiel")
def referentiel():
    return _page(PAGES["/referentiel"])


@app.route("/analyse-de-risque")
def analyse_de_risque():
    return _page(PAGES["/analyse-de-risque"])


@app.route("/secteurs")
def secteurs():
    return _page(PAGES["/secteurs"])


@app.route("/methodologie")
def methodologie():
    return _page(PAGES["/methodologie"])


@app.route("/exigences-systeme")
def exigences_systeme():
    return _page(PAGES["/exigences-systeme"])


@app.route("/exigences-composants")
def exigences_composants():
    return _page(PAGES["/exigences-composants"])


@app.route("/exigences-prestataires")
def exigences_prestataires():
    return _page(PAGES["/exigences-prestataires"])


@app.route("/developpement-securise")
def developpement_securise():
    return _page(PAGES["/developpement-securise"])


@app.route("/technologies-securite")
def technologies_securite():
    return _page(PAGES["/technologies-securite"])


@app.route("/programme-securite")
def programme_securite():
    return _page(PAGES["/programme-securite"])


@app.route("/gestion-correctifs")
def gestion_correctifs():
    return _page(PAGES["/gestion-correctifs"])


@app.route("/glossaire-62443")
def glossaire_62443():
    return _page(PAGES["/glossaire-62443"])


@app.route("/metriques-62443")
def metriques_62443():
    return _page(PAGES["/metriques-62443"])


@app.route("/demo")
def demo():
    return _page(PAGES["/demo"])


@app.route("/ressources")
def ressources():
    return _page(PAGES["/ressources"])


@app.route("/faq")
def faq():
    return _page(PAGES["/faq"])


@app.route("/about")
def about():
    return _page(PAGES["/about"])


@app.route("/contact")
def contact():
    return _page(PAGES["/contact"])


@app.route("/mentions-legales")
def mentions_legales():
    return _page(PAGES["/mentions-legales"])


@app.route("/styles.css")
def styles():
    return send_from_directory(HERE, "styles.css", mimetype="text/css")


@app.route("/api/contact", methods=["POST"])
def api_contact():
    """Traite le formulaire de contact et envoie un email via Brevo."""
    data = request.get_json(silent=True) or request.form

    # Anti-spam : champ piège (honeypot). Rempli => bot => on accepte sans agir.
    if (data.get("site") or "").strip():
        return jsonify(ok=True)

    nom = (data.get("nom") or "").strip()
    email = (data.get("email") or "").strip()
    org = (data.get("org") or "").strip()
    sujet = (data.get("sujet") or "Contact").strip()
    msg = (data.get("msg") or "").strip()

    if not nom or "@" not in email or not msg:
        return jsonify(ok=False, error="invalid", message="Champs requis manquants ou email invalide."), 400

    api_key = os.environ.get("BREVO_API_KEY")
    if not api_key:
        # Pas encore configuré : le client basculera sur mailto.
        return jsonify(ok=False, error="not_configured"), 503

    def esc(value):
        return html_lib.escape(value)

    body_html = (
        f"<p><strong>Nom :</strong> {esc(nom)}</p>"
        f"<p><strong>Organisation :</strong> {esc(org) or '—'}</p>"
        f"<p><strong>Email :</strong> {esc(email)}</p>"
        f"<p><strong>Sujet :</strong> {esc(sujet)}</p>"
        f"<hr><p>{esc(msg).replace(chr(10), '<br>')}</p>"
    )
    payload = {
        "sender": SENDER,
        "to": [{"email": NOTIFY_TO, "name": "CONSEILPREV Cyber"}],
        "replyTo": {"email": email, "name": nom},
        "subject": f"[Contact site] {sujet}",
        "htmlContent": body_html,
    }
    try:
        resp = requests.post(
            BREVO_API_URL,
            json=payload,
            headers={"api-key": api_key, "accept": "application/json", "content-type": "application/json"},
            timeout=12,
        )
    except requests.RequestException:
        return jsonify(ok=False, error="network", message="Impossible de joindre le service d'envoi."), 502

    if resp.status_code in (200, 201):
        return jsonify(ok=True)
    return jsonify(ok=False, error="send_failed", status=resp.status_code), 502


@app.route("/api/stream")
def api_stream():
    """Flux Server-Sent Events du cockpit (mode « Temps réel »).

    Diffuse les événements poussés via POST /api/ingest. Un commentaire
    « keep-alive » est émis périodiquement pour maintenir la connexion à
    travers les proxies. Nécessite un worker à threads (gunicorn -k gthread).
    """

    def gen():
        q = broker.subscribe()
        try:
            # Instantané d'ouverture : le cockpit affiche l'état courant tout de suite.
            snap = json.dumps(state.snapshot(), ensure_ascii=False)
            yield "event: snapshot\ndata: " + snap + "\n\n"
            while True:
                try:
                    payload = q.get(timeout=15)
                    yield "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"
                except queue.Empty:
                    yield ": keep-alive\n\n"
        except GeneratorExit:  # client déconnecté
            pass
        finally:
            broker.unsubscribe(q)

    resp = Response(gen(), mimetype="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"  # désactive le buffering côté proxy
    resp.headers["Connection"] = "keep-alive"
    return resp


@app.route("/api/ingest", methods=["POST"])
def api_ingest():
    """Reçoit un événement OT normalisé et le diffuse au cockpit temps réel.

    Protégé par le jeton INGEST_TOKEN (en-tête X-Ingest-Token). Sans jeton
    configuré, l'ingestion est désactivée : le cockpit reste en mode démo.

    Corps attendu (JSON) : {asset, zone, type, event, severity, ts}
    """
    if not INGEST_TOKEN:
        return jsonify(ok=False, error="not_configured"), 503
    if request.headers.get("X-Ingest-Token") != INGEST_TOKEN:
        return jsonify(ok=False, error="unauthorized"), 401

    data = request.get_json(silent=True) or {}
    evt = {
        "asset": str(data.get("asset", ""))[:120],
        "zone": str(data.get("zone", ""))[:80],
        "type": str(data.get("type", "event"))[:40],
        "event": str(data.get("event", ""))[:240],
        "severity": str(data.get("severity", "info")).lower()[:16],
        "ts": data.get("ts") or int(time.time() * 1000),
    }
    enriched, snap = state.apply(evt)
    broker.publish({"event": enriched, "state": snap})
    return jsonify(ok=True)


@app.route("/api/state")
def api_state():
    """Instantané de l'état courant du cockpit (inventaire, alertes, événements récents)."""
    return jsonify(state.snapshot())


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Réinitialise l'état du cockpit (protégé par INGEST_TOKEN)."""
    if not INGEST_TOKEN:
        return jsonify(ok=False, error="not_configured"), 503
    if request.headers.get("X-Ingest-Token") != INGEST_TOKEN:
        return jsonify(ok=False, error="unauthorized"), 401
    state.reset()
    broker.publish({"reset": True, "state": state.snapshot()})
    return jsonify(ok=True)


@app.route("/health")
def health():
    """Point de santé (utilisé par Render pour vérifier le service)."""
    return jsonify(status="ok", service="conseilprevcyber"), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
