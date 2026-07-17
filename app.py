"""CONSEILPREV Cyber — application web Flask.

Sert les pages statiques du site, expose un point de santé pour Render et
traite le formulaire de contact via l'API transactionnelle Brevo.

Démarrage local :  python app.py
Production (Render) :  gunicorn app:app

Variables d'environnement :
  BREVO_API_KEY  — clé API Brevo (transactional email). Si absente, le
                   formulaire bascule côté client sur un lien mailto.
"""
import html as html_lib
import os

import requests
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__)
HERE = os.path.dirname(os.path.abspath(__file__))

# --- Configuration email (expéditeur vérifié Brevo) ---------------------------
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
SENDER = {"name": "CONSEILPREV", "email": "christophe.cerf@i-aes.com"}
NOTIFY_TO = "christophe.cerf@outlook.com"

# URL propre -> fichier HTML servi
PAGES = {
    "/": "index.html",
    "/services": "services.html",
    "/referentiel": "referentiel.html",
    "/secteurs": "secteurs.html",
    "/methodologie": "methodologie.html",
    "/exigences-systeme": "exigences-systeme.html",
    "/exigences-composants": "exigences-composants.html",
    "/programme-securite": "programme-securite.html",
    "/gestion-correctifs": "gestion-correctifs.html",
    "/demo": "demo.html",
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


@app.route("/referentiel")
def referentiel():
    return _page(PAGES["/referentiel"])


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


@app.route("/programme-securite")
def programme_securite():
    return _page(PAGES["/programme-securite"])


@app.route("/gestion-correctifs")
def gestion_correctifs():
    return _page(PAGES["/gestion-correctifs"])


@app.route("/demo")
def demo():
    return _page(PAGES["/demo"])


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


@app.route("/health")
def health():
    """Point de santé (utilisé par Render pour vérifier le service)."""
    return jsonify(status="ok", service="conseilprevcyber"), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
