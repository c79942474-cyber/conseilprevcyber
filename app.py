"""CONSEILPREV Cyber — application web Flask.

Sert la page d'accueil statique et expose un point de santé pour Render.
Démarrage local :  python app.py
Production (Render) :  gunicorn app:app
"""
import os

from flask import Flask, jsonify, send_from_directory

app = Flask(__name__, static_folder=".", static_url_path="")


@app.route("/")
def index():
    """Page d'accueil."""
    return send_from_directory(".", "index.html")


@app.route("/health")
def health():
    """Point de santé (utilisé par Render pour vérifier le service)."""
    return jsonify(status="ok", service="conseilprevcyber"), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
