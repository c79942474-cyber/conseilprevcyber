"""CONSEILPREV Cyber — application web Flask.

Sert les pages statiques du site et expose un point de santé pour Render.
Démarrage local :  python app.py
Production (Render) :  gunicorn app:app
"""
import os

from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)
HERE = os.path.dirname(os.path.abspath(__file__))

# URL propre -> fichier HTML servi
PAGES = {
    "/": "index.html",
    "/services": "services.html",
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


@app.route("/contact")
def contact():
    return _page(PAGES["/contact"])


@app.route("/mentions-legales")
def mentions_legales():
    return _page(PAGES["/mentions-legales"])


@app.route("/styles.css")
def styles():
    return send_from_directory(HERE, "styles.css", mimetype="text/css")


@app.route("/health")
def health():
    """Point de santé (utilisé par Render pour vérifier le service)."""
    return jsonify(status="ok", service="conseilprevcyber"), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
