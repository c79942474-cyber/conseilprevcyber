"""CONSEILPREV Cyber — application web Flask.

Sert les pages statiques du site, expose un point de santé pour Render,
traite le formulaire de contact via l'API transactionnelle Brevo et alimente
le cockpit de supervision OT (démo + flux temps réel SSE).

Démarrage local :  python app.py
Production (Render) :  gunicorn -k gthread --threads 8 --timeout 120 app:app

Variables d'environnement :
  BREVO_API_KEY        — clé API Brevo (transactional email). Si absente, le
                         formulaire bascule côté client sur un lien mailto.
  INGEST_TOKEN         — jeton partagé protégeant POST /api/ingest (et /api/reset).
                         Si absent, l'ingestion est désactivée et le cockpit
                         reste en mode démo (données simulées).
  DATABASE_URL         — (optionnel) URL PostgreSQL. Si défini, l'inventaire et
                         l'historique du cockpit sont persistés ; sinon en mémoire.
  REDIS_URL            — (optionnel) URL Redis. Si défini, les événements sont
                         diffusés à toutes les instances via pub/sub (multi-instance,
                         haute dispo). Sinon, diffusion locale (une seule instance).
  REDIS_CHANNEL        — (optionnel) nom du canal Redis (défaut : cockpit:events).
  FLASK_SECRET_KEY     — clé de signature des sessions (comptes). À DÉFINIR en prod
                         (sinon les sessions sont invalidées à chaque redémarrage).
  ADMIN_EMAIL          — email qui reçoit les demandes d'accès à approuver
                         (défaut : christophe.cerf@outlook.com).
  PUBLIC_BASE_URL      — URL publique du site (pour les liens des emails, ex.
                         https://conseilprevcyber.onrender.com). Sinon déduit de la requête.
  EVENT_RETENTION_DAYS — (optionnel) purge des événements plus vieux que N jours.
  EVENT_MAX_ROWS       — (optionnel) ne conserver que les N derniers événements.
  EVENT_ARCHIVE_PATH   — (optionnel) archive JSONL des événements purgés (cible durable).
  MAINTENANCE_INTERVAL_HOURS — (optionnel) période de la purge auto (défaut : 6 h).

  Base de connaissance RAG (administration réservée à l'admin) — voir rag_store.py :
  DATABASE_URL         — (réutilisé) si défini, la base de connaissance est persistée
                         (PostgreSQL) et utilise pgvector si l'extension est disponible ;
                         sinon repli plein-texte (PostgreSQL) ou lexical (mémoire).
  MISTRAL_API_KEY      — (réutilisé) active les embeddings « mistral-embed » (recherche
                         sémantique). Absent : repli sur la recherche plein-texte.
  RAG_MAX_FILE_MB      — (optionnel) taille max d'un document chargé (défaut : 30 Mo).
"""
import base64
import binascii
import html as html_lib
import gzip
import hashlib
import json
import os
import io
import queue
import threading
import time
import zipfile

from urllib.parse import urlparse

import requests
from flask import Flask, Response, jsonify, request, send_file, send_from_directory

import assistant
import automation
import livrables
import livrables_export
import rgpd
from auth import admin_required, client_ip, current_user, guard, init_app as init_auth
from clients_store import (BASES_LEGALES, CATEGORIES_PIECES, STATUTS,
                           ClientsError, make_clients_store)
from cockpit_state import make_store, tag_for
from livrables_store import make_livrables_store
from rag_store import (RagError, THEMES, build_context, dedupe as rag_dedupe,
                       duplicate_groups, make_rag_store)

app = Flask(__name__)
HERE = os.path.dirname(os.path.abspath(__file__))

# --- Sécurité applicative (en-têtes, anti-CSRF, taille de requête) -------------
# Plafond de taille du corps d'une requête (anti-abus mémoire / DoS).
app.config["MAX_CONTENT_LENGTH"] = 512 * 1024

# Points protégés par jeton (server-to-server) : exemptés du contrôle d'origine
# CSRF, car authentifiés par un secret d'en-tête (X-Ingest-Token) et non par un
# cookie de session — donc non vulnérables au CSRF (qui exploite le cookie ambiant).
_CSRF_EXEMPT = {"/api/ingest", "/api/reset", "/api/maintenance/purge", "/api/rag/ingest"}

# En-têtes de sécurité appliqués à toutes les réponses. La CSP autorise le style
# et le script « inline » (site statique : nombreux <style>/<script> intégrés),
# mais verrouille le reste : pas de ressource tierce, pas d'iframe (anti-clickjacking),
# pas d'objet, formulaires et base-uri limités à l'origine.
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), interest-cohort=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Content-Security-Policy": (
        "default-src 'self'; base-uri 'self'; form-action 'self'; "
        "frame-ancestors 'none'; object-src 'none'; "
        "img-src 'self' data:; font-src 'self' data:; "
        "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
        "connect-src 'self'"
    ),
}


def _request_is_https():
    return request.is_secure or request.headers.get("X-Forwarded-Proto", "") == "https"


def _same_origin_request():
    """Vrai si la requête provient de notre propre origine (défense anti-CSRF)."""
    src = request.headers.get("Origin") or request.headers.get("Referer") or ""
    if not src:
        return False
    return urlparse(src).netloc == request.host


@app.before_request
def _csrf_guard():
    """Bloque les requêtes d'état d'origine tierce (CSRF) sur les points à cookie.

    Défense en profondeur : cookies SameSite=Lax + contrôle d'origine. Les points
    protégés par jeton (ingestion, reset, purge) sont exemptés — authentifiés par
    secret et non par cookie de session.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    if request.path in _CSRF_EXEMPT:
        return
    if not _same_origin_request():
        return jsonify(ok=False, error="csrf",
                       message="Origine de la requête non autorisée."), 403


@app.after_request
def _security_headers(resp):
    for key, value in _SECURITY_HEADERS.items():
        resp.headers.setdefault(key, value)
    if _request_is_https():
        resp.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return resp


@app.errorhandler(413)
def _too_large(_err):
    """Corps de requête au-dessus de MAX_CONTENT_LENGTH : réponse JSON propre
    (sinon Flask renvoie une page HTML qui casse le `response.json()` du client,
    p. ex. l'upload par morceaux de la base de connaissance)."""
    return jsonify(ok=False, error="requete_trop_grande",
                   message="Contenu trop volumineux pour une seule requête."), 413


@app.errorhandler(500)
@app.errorhandler(502)
@app.errorhandler(503)
@app.errorhandler(504)
def _api_error_json(err):
    """Sur les routes /api/, renvoie une erreur JSON propre plutôt qu'une page HTML
    (sinon un client qui attend du JSON échoue avec « Unexpected token '<' »).
    L'exception réelle reste journalisée par Flask — visible dans les logs Render."""
    code = getattr(err, "code", 500) or 500
    if request.path.startswith("/api/"):
        app.logger.warning("Erreur %s renvoyée sur %s", code, request.path)
        return jsonify(ok=False, error="erreur_serveur",
                       message="Le serveur a rencontré une erreur. Réessayez dans un instant."), code
    return err

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


class EventBus:
    """Bus d'événements du cockpit, compatible **multi-instance** (haute dispo).

    - Sans REDIS_URL : diffusion locale uniquement (une seule instance).
    - Avec REDIS_URL : chaque événement est publié sur un canal Redis ; toutes les
      instances y sont abonnées et le rediffusent à LEURS clients SSE. Le fan-out
      local passe donc toujours par Redis (y compris pour l'instance émettrice),
      ce qui évite les doublons et traite toutes les instances de façon uniforme.

    L'état (instantané d'ouverture) reste cohérent entre instances via la base
    PostgreSQL partagée (voir cockpit_state.py).
    """

    def __init__(self):
        self._local = _Broker()
        self._redis = None
        self._channel = os.environ.get("REDIS_CHANNEL", "cockpit:events")
        url = os.environ.get("REDIS_URL")
        if not url:
            return
        # Redis injoignable NE DOIT PAS empêcher le démarrage : on bascule en
        # diffusion locale (mono-instance) et on journalise clairement.
        try:
            import redis  # dépendance chargée uniquement si REDIS_URL est défini
            client = redis.Redis.from_url(
                url, socket_keepalive=True, socket_connect_timeout=5,
                socket_timeout=5, health_check_interval=30)
            client.ping()  # vérifie l'accès avec un timeout court
            self._redis = client
            threading.Thread(target=self._subscribe_loop, daemon=True).start()
            app.logger.info("EventBus : Redis connecté (canal %s)", self._channel)
        except Exception as exc:
            self._redis = None
            app.logger.warning(
                "EventBus : Redis injoignable (%s) — repli en diffusion LOCALE "
                "(mono-instance). Vérifiez REDIS_URL (URL interne, même région).", exc)

    def subscribe(self):
        return self._local.subscribe()

    def unsubscribe(self, q):
        self._local.unsubscribe(q)

    def publish(self, data):
        if self._redis is not None:
            try:
                self._redis.publish(self._channel, json.dumps(data))
                return
            except Exception:
                pass  # Redis indisponible : repli sur la diffusion locale
        self._local.publish(data)

    def _subscribe_loop(self):
        while True:
            try:
                pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
                pubsub.subscribe(self._channel)
                for msg in pubsub.listen():
                    if msg.get("type") != "message":
                        continue
                    try:
                        payload = json.loads(msg["data"])
                    except (ValueError, TypeError):
                        continue
                    self._local.publish(payload)
            except Exception:
                time.sleep(2)  # perte de connexion Redis : on retente


broker = EventBus()

# État du cockpit : persistant (PostgreSQL) si DATABASE_URL est défini, sinon en
# mémoire. Voir cockpit_state.py.
state = make_store()

# Base de connaissance RAG : persistante (PostgreSQL + pgvector si disponible) si
# DATABASE_URL est défini, sinon en mémoire. Alimente l'assistant et les livrables.
# Voir rag_store.py. Gérée uniquement par l'administrateur (routes @admin_required).
rag = make_rag_store()

# Historique des livrables générés (persistant si DATABASE_URL). Voir livrables_store.py.
livrables_hist = make_livrables_store()

# Gestion des clients & prospects — conforme RGPD (persistante si DATABASE_URL).
# Voir clients_store.py (journal d'audit, conservation, export, effacement).
clients_db = make_clients_store()


# --- Automatisation temps réel (planificateur de fond) — voir automation.py ----
def _veille_summarize(titre, description):
    """Résumé LLM d'un bulletin CERT-FR (best-effort ; None si indisponible)."""
    try:
        text, _m = assistant.generate(
            "mistral",
            "Tu résumes des bulletins CERT-FR pour des responsables industriels. "
            "Réponds en 2 à 3 phrases factuelles en français : nature de la menace, "
            "produits concernés, action recommandée. Pas de titre, pas de liste.",
            "Titre : %s\n\nContenu : %s" % (titre, (description or "")[:1500]),
            max_tokens=220)
        return (text or "").strip() or None
    except Exception:
        return None


def _report_generate(data):
    """Rapport hebdomadaire rédigé par LLM (best-effort ; None si indisponible)."""
    try:
        text, _m = assistant.generate(
            "mistral",
            "Tu rédiges un rapport hebdomadaire interne (Markdown) pour CONSEILPREV. "
            "Structure : ## Synthèse, ## Chiffres clés (tableau Markdown), "
            "## Points d'attention. Factuel et concis : uniquement les données fournies, "
            "aucune invention.",
            "Données de la semaine (JSON) :\n" + json.dumps(data, ensure_ascii=False, indent=2),
            max_tokens=900)
        return text
    except Exception:
        return None


automation.init(sender=SENDER, notify_to=NOTIFY_TO, rag=rag, clients=clients_db,
                livrables=livrables_hist, cockpit=state,
                summarize=_veille_summarize, generate_report=_report_generate,
                dsn=os.environ.get("DATABASE_URL"))

# --- Rétention de l'historique ------------------------------------------------
# Purge périodique des événements au-delà d'un âge (EVENT_RETENTION_DAYS) et/ou
# d'un nombre de lignes (EVENT_MAX_ROWS). Archivage JSONL optionnel avant suppression
# (EVENT_ARCHIVE_PATH — cible durable requise, cf. DEPLOY.md). Sans ces variables,
# aucune purge (l'historique complet est conservé).
_RETENTION_DAYS = float(os.environ.get("EVENT_RETENTION_DAYS") or 0) or None
_MAX_ROWS = int(os.environ.get("EVENT_MAX_ROWS") or 0) or None
_ARCHIVE_PATH = os.environ.get("EVENT_ARCHIVE_PATH") or None
_MAINTENANCE_HOURS = float(os.environ.get("MAINTENANCE_INTERVAL_HOURS") or 6)


def _start_maintenance():
    if not (_RETENTION_DAYS or _MAX_ROWS):
        return

    def loop():
        while True:
            time.sleep(max(0.1, _MAINTENANCE_HOURS) * 3600)
            try:
                n = state.purge(retention_days=_RETENTION_DAYS, max_rows=_MAX_ROWS,
                                archive_path=_ARCHIVE_PATH)
                if n:
                    app.logger.info("maintenance : %d événement(s) purgé(s)", n)
            except Exception:
                app.logger.exception("maintenance : échec de la purge")

    threading.Thread(target=loop, daemon=True).start()


_start_maintenance()

# --- Authentification (comptes : inscription + validation admin + connexion) ---
# Système de comptes (voir auth.py) : sessions, mots de passe hachés, emails Brevo.
# Le contenu public reste ouvert ; seuls le cockpit temps réel et la supervision
# (protégés par @login_required plus bas) exigent un compte connecté.
login_required = init_auth(app)

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
    "/assistant": "assistant.html",
    "/audit-conformite": "audit-conformite.html",
    "/tendances": "tendances.html",
    "/connecter": "connecter.html",
    "/guide-integration": "guide-integration.html",
    "/ressources": "ressources.html",
    "/faq": "faq.html",
    "/about": "about.html",
    "/vos-projets": "vos-projets.html",
    "/contact": "contact.html",
    "/mentions-legales": "mentions-legales.html",
    "/politique-confidentialite": "politique-confidentialite.html",
    "/nis2": "nis2.html",
    "/diagnostic": "diagnostic.html",
    "/veille": "veille.html",
}


# --- Service rapide des fichiers statiques (< 200 ms) -------------------------
# Les pages et les assets partagés (styles.css, nav.js, emblem.svg) sont des
# fichiers identiques pour tous les visiteurs : aucune donnée personnelle
# dedans (la personnalisation passe par les API). On les garde donc en mémoire,
# pré-compressés en gzip une seule fois, avec un ETag fort. Deux gains décisifs
# pour la navigation entre pages :
#   1. compression gzip (Flask/Render n'en applique aucune par défaut) —
#      styles.css 29→8 Ko, nav.js 54→16 Ko, pages ~30 % de leur taille ;
#   2. revalidation par ETag : un clic sur une page déjà vue renvoie un 304
#      sans corps (~quelques ms) au lieu de la re-télécharger, et les assets
#      partagés (cache navigateur) ne repartent plus sur le réseau à chaque page.
# Le cache se reconstruit tout seul si le fichier change (nouveau déploiement :
# le process redémarre et la clé mtime+taille change).
_STATIC_CACHE = {}
_STATIC_CACHE_LOCK = threading.Lock()


def _static_entry(filename):
    """Entrée de cache {raw, gz, etag} du fichier, reconstruite s'il change."""
    path = os.path.join(HERE, filename)
    st = os.stat(path)
    key = (st.st_mtime_ns, st.st_size)
    ent = _STATIC_CACHE.get(filename)
    if ent is not None and ent["key"] == key:
        return ent
    with _STATIC_CACHE_LOCK:
        ent = _STATIC_CACHE.get(filename)
        if ent is not None and ent["key"] == key:
            return ent
        with open(path, "rb") as fh:
            raw = fh.read()
        ent = {
            "key": key,
            "raw": raw,
            "gz": gzip.compress(raw, 9),
            "etag": '"cp-%s"' % hashlib.sha256(raw).hexdigest()[:24],
        }
        _STATIC_CACHE[filename] = ent
        return ent


def _serve_fast(filename, cache_control, mimetype="text/html; charset=utf-8",
                gzippable=True):
    """Sert un fichier depuis le cache mémoire, gzippé si le navigateur
    l'accepte, avec ETag fort + honoré via If-None-Match (304 sans corps).
    Repli transparent sur send_from_directory si le fichier est illisible."""
    try:
        ent = _static_entry(filename)
    except OSError:
        return send_from_directory(HERE, filename, mimetype=mimetype)
    if ent["etag"] in (request.headers.get("If-None-Match") or ""):
        resp = Response(status=304, mimetype=mimetype)
    else:
        use_gz = gzippable and "gzip" in (
            request.headers.get("Accept-Encoding") or "").lower()
        body = ent["gz"] if use_gz else ent["raw"]
        resp = Response(body, mimetype=mimetype)
        if use_gz:
            resp.headers["Content-Encoding"] = "gzip"
        resp.headers["Content-Length"] = str(len(body))
    resp.headers["ETag"] = ent["etag"]
    resp.headers["Cache-Control"] = cache_control
    if gzippable:
        resp.headers["Vary"] = "Accept-Encoding"
    return resp


# Politiques de cache : pages publiques revalidables (fraîcheur garantie par
# l'ETag), assets partagés gardés 5 min côté navigateur pour ne pas repartir
# sur le réseau entre deux pages.
_CC_PAGE = "public, max-age=300, must-revalidate"
_CC_ADMIN = "private, no-cache, must-revalidate"
_CC_ASSET = "public, max-age=300"
_CC_IMAGE = "public, max-age=86400"


def _page(filename):
    return _serve_fast(filename, _CC_PAGE)


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


@app.route("/assistant")
def assistant_page():
    """Assistant IA conversationnel (Claude / Mistral) — cybersécurité industrielle & conformité."""
    return _page(PAGES["/assistant"])


@app.route("/api/assistant/config")
def api_assistant_config():
    """Modèles configurés + modèle par défaut de l'UI (surcharge via ASSISTANT_DEFAULT_MODEL)."""
    default = (os.environ.get("ASSISTANT_DEFAULT_MODEL") or "mistral").strip().lower()
    if default not in ("claude", "mistral"):
        default = "mistral"
    return jsonify(models=assistant.available(), default=default)


@app.route("/api/assistant/selftest")
def api_assistant_selftest():
    """Diagnostic : ping minimal de chaque modèle, renvoie le statut technique
    (code HTTP, type d'erreur). Aucun secret ni contenu. Limité par IP."""
    ckey = "selftest:%s" % client_ip()
    if guard.blocked(ckey, limit=6, window=600):
        return jsonify(ok=False, error="rate_limited",
                       message="Trop de tests en peu de temps. Réessayez dans quelques minutes."), 429
    guard.fail(ckey)
    return jsonify(results=assistant.selftest())


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Point d'entrée du chat sécurisé. Sans état : aucune conversation n'est stockée.

    Protégé par le contrôle d'origine (before_request) + limitation de débit par IP.
    """
    ckey = "chat:%s" % client_ip()
    if guard.blocked(ckey, limit=20, window=600):
        return jsonify(ok=False, error="rate_limited",
                       message="Trop de messages en peu de temps. Merci de patienter quelques minutes."), 429
    guard.fail(ckey)

    data = request.get_json(silent=True) or {}
    model = "mistral" if data.get("model") == "mistral" else "claude"
    messages = data.get("messages")

    # Récupération RAG : on ancre la réponse sur la base de connaissance (documents
    # PUBLICS uniquement). Best-effort : une erreur de récupération ne casse jamais le chat.
    context = None
    try:
        query = assistant.last_user_message(messages)
        if query:
            context = build_context(rag.search(query, k=5, public_only=True))
    except Exception:
        context = None

    try:
        reply, used_model = assistant.answer(model, messages, context=context)
    except assistant.AssistantError as exc:
        messages = {
            "not_configured": "Ce modèle n'est pas encore activé. Essayez l'autre modèle, ou "
                              "écrivez-nous via la page Contact.",
            "auth": "Le service d'IA a refusé la clé d'accès configurée. Vérifiez la clé API "
                    "du modèle dans le tableau de bord (sans espace ni guillemet), puis réessayez.",
            "empty": "Votre message est vide.",
            "busy": "L'assistant est très sollicité pour le moment. Réessayez dans un instant.",
            "network": "Service d'IA momentanément injoignable. Réessayez dans un instant.",
            "upstream": "L'assistant a rencontré une erreur. Réessayez, ou contactez-nous.",
        }
        return jsonify(ok=False, error=exc.code,
                       message=messages.get(exc.code, "Assistant indisponible pour le moment.")), exc.status
    return jsonify(ok=True, reply=reply, model=model)


@app.route("/audit-conformite")
def audit_conformite():
    """Étude & audit de conformité IEC 62443 (mode démo public ; temps réel via compte)."""
    return _page(PAGES["/audit-conformite"])


@app.route("/tendances")
@login_required
def tendances():
    return _page(PAGES["/tendances"])


@app.route("/connecter")
@login_required
def connecter():
    """Page « Connecter votre plateforme » : l'entrée pour brancher une source réelle."""
    return _page(PAGES["/connecter"])


@app.route("/guide-integration")
@login_required
def guide_integration():
    """Guide d'intégration détaillé (pas-à-pas professionnel du branchement)."""
    return _page(PAGES["/guide-integration"])


@app.route("/telecharger/connecteur.zip")
@login_required
def download_connector():
    """Archive zip du connecteur (Python standard, sans dépendance) + guide de déploiement."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        base = os.path.join(HERE, "connectors")
        for root, _dirs, files in os.walk(base):
            for name in sorted(files):
                if name.endswith((".pyc", ".pyo")) or "__pycache__" in root:
                    continue
                full = os.path.join(root, name)
                z.write(full, os.path.relpath(full, HERE))
    buf.seek(0)
    return send_file(buf, mimetype="application/zip", as_attachment=True,
                     download_name="conseilprev-connecteur.zip")


@app.route("/api/admin/ingest-token")
@admin_required
def api_admin_ingest_token():
    """Révèle le jeton d'ingestion à l'administrateur (pour la page Connecter)."""
    return jsonify(configured=bool(INGEST_TOKEN), token=INGEST_TOKEN or "")


@app.route("/ressources")
@login_required
def ressources():
    return _page(PAGES["/ressources"])


@app.route("/faq")
def faq():
    return _page(PAGES["/faq"])


@app.route("/about")
def about():
    return _page(PAGES["/about"])


@app.route("/vos-projets")
@login_required
def vos_projets():
    """Formulaire détaillé de soumission de projet cyber industriel (IT/OT/IIoT)."""
    return _page(PAGES["/vos-projets"])


@app.route("/contact")
def contact():
    return _page(PAGES["/contact"])


@app.route("/mentions-legales")
def mentions_legales():
    return _page(PAGES["/mentions-legales"])


@app.route("/politique-confidentialite")
def politique_confidentialite():
    return _page(PAGES["/politique-confidentialite"])


@app.route("/nis2")
def nis2():
    return _page(PAGES["/nis2"])


@app.route("/diagnostic")
def diagnostic():
    return _page(PAGES["/diagnostic"])


@app.route("/veille")
def veille():
    return _page(PAGES["/veille"])


@app.route("/styles.css")
def styles():
    return _serve_fast("styles.css", _CC_ASSET, mimetype="text/css; charset=utf-8")


@app.route("/nav.js")
def nav_js():
    """Script partagé de l'en-tête responsive (menu « burger » sur mobile)."""
    return _serve_fast("nav.js", _CC_ASSET,
                       mimetype="text/javascript; charset=utf-8")


@app.route("/emblem.svg")
def emblem_svg():
    """Emblème CONSEILPREV (bouclier géométrique) — logo vectoriel de l'en-tête."""
    return _serve_fast("emblem.svg", _CC_ASSET, mimetype="image/svg+xml")


@app.route("/og-cover.png")
def og_cover():
    """Image de partage social (Open Graph / Twitter Card) — 1200×630."""
    # PNG déjà compressé : pas de gzip, mais cache navigateur (rarement modifié).
    return _serve_fast("og-cover.png", _CC_IMAGE, mimetype="image/png",
                       gzippable=False)


@app.route("/emblem.png")
def emblem_png():
    """Emblème CONSEILPREV en PNG (logo pour données structurées / partage)."""
    return _serve_fast("emblem.png", _CC_IMAGE, mimetype="image/png",
                       gzippable=False)


# --- Référencement (robots.txt + sitemap.xml) ---------------------------------
# Pages publiques uniquement : on exclut les pages nécessitant un compte.
_SITEMAP_EXCLUDE = {"/tendances", "/connecter", "/guide-integration"}
_SITEMAP_TOP = {"/", "/services", "/vos-projets", "/contact", "/etudes-de-cas", "/about"}


def _base_url():
    b = (os.environ.get("PUBLIC_BASE_URL") or "").strip().rstrip("/")
    return b or "https://conseilprevcyber.onrender.com"


@app.route("/robots.txt")
def robots_txt():
    """Directives d'exploration : pages publiques ouvertes, zones privées fermées."""
    base = _base_url()
    body = "\n".join([
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /api/",
        "Disallow: /connexion",
        "Disallow: /inscription",
        "Disallow: /mot-de-passe-oublie",
        "Disallow: /reinitialiser",
        "Disallow: /verifier-email",
        "Disallow: /telecharger/",
        "",
        "Sitemap: %s/sitemap.xml" % base,
        "",
    ])
    return Response(body, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    """Plan du site (pages publiques indexables)."""
    base = _base_url()
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path in PAGES:
        if path in _SITEMAP_EXCLUDE:
            continue
        loc = base + ("/" if path == "/" else path)
        priority = "1.0" if path == "/" else ("0.8" if path in _SITEMAP_TOP else "0.6")
        parts.append("  <url><loc>%s</loc><changefreq>monthly</changefreq>"
                     "<priority>%s</priority></url>" % (loc, priority))
    parts.append("</urlset>")
    return Response("\n".join(parts), mimetype="application/xml")


# ============================================================================
#  Base de connaissance RAG — administration (réservée à l'administrateur)
# ============================================================================
# Toutes ces routes sont protégées par @admin_required : seul le compte admin
# (ADMIN_EMAIL) peut charger, indexer, lister, télécharger ou supprimer des
# documents. Les identifiants sont validés (défense contre les chemins/injections).

def _rag_hex(s, length=32):
    return isinstance(s, str) and len(s) == length and all(c in "0123456789abcdef" for c in s)


def _rag_valid_doc_id(s):
    return _rag_hex(s)


def _rag_valid_upload_id(s):
    if not isinstance(s, str) or "/" in s or "\\" in s:
        return False
    base, _, ext = s.partition(".")
    return _rag_hex(base) and (ext == "" or (1 <= len(ext) <= 8 and ext.isalnum()))


@app.route("/admin")
@app.route("/admin/")
@admin_required
def admin_home():
    """Tableau de bord d'administration : liens vers toutes les zones admin."""
    return _serve_fast("admin.html", _CC_ADMIN)


@app.route("/admin/base-connaissance")
@admin_required
def admin_rag_page():
    """Console d'administration de la base de connaissance RAG."""
    return _serve_fast("admin-base-connaissance.html", _CC_ADMIN)


@app.route("/api/admin/rag/documents", methods=["GET"])
@admin_required
def api_rag_list():
    """Liste des documents + statistiques + capacités (mode de recherche actif)."""
    return jsonify(ok=True, documents=rag.list_documents(), stats=rag.stats(),
                   capabilities=rag.capabilities(), themes=THEMES)


def _dup_doc_summary(d):
    """Résumé d'un document pour l'aperçu des doublons (champs utiles à l'admin)."""
    return {k: d.get(k) for k in ("id", "title", "filename", "theme",
                                  "visibility", "bytes", "nb_chunks", "created_at")}


@app.route("/api/admin/rag/duplicates", methods=["GET"])
@admin_required
def api_rag_duplicates():
    """Aperçu des doublons (contenu identique) SANS rien supprimer : pour chaque
    groupe, le document conservé et ceux qui seraient retirés."""
    groups = duplicate_groups(rag)
    out = [{"keep": _dup_doc_summary(g["keep"]),
            "remove": [_dup_doc_summary(d) for d in g["remove"]]} for g in groups]
    removable = sum(len(g["remove"]) for g in groups)
    return jsonify(ok=True, groups=out, removable=removable)


@app.route("/api/admin/rag/dedupe", methods=["POST"])
@admin_required
def api_rag_dedupe():
    """Supprime les doublons en conservant un exemplaire par contenu."""
    report = rag_dedupe(rag)
    return jsonify(ok=True, **report)


@app.route("/api/admin/rag/reconnect", methods=["POST"])
@admin_required
def api_rag_reconnect():
    """Force un essai de reconnexion à PostgreSQL (repli mémoire → persistant)
    sans redéploiement. Sans effet si le store n'est pas résilient (aucune
    DATABASE_URL) — renvoie alors simplement l'état courant."""
    fn = getattr(rag, "reconnect", None)
    reconnected = bool(fn()) if callable(fn) else False
    return jsonify(ok=True, reconnected=reconnected,
                   capabilities=rag.capabilities(), stats=rag.stats())


@app.route("/api/admin/rag/upload/init", methods=["POST"])
@admin_required
def api_rag_upload_init():
    """Ouvre une session d'upload par morceaux (fichiers lourds)."""
    data = request.get_json(silent=True) or {}
    filename = (data.get("filename") or "").strip()
    if not filename:
        return jsonify(ok=False, error="filename_manquant"), 400
    try:
        upload_id = rag.create_upload(filename, int(data.get("total_bytes") or 0))
    except (RagError,) as exc:
        return jsonify(ok=False, error=exc.code), exc.status
    except (TypeError, ValueError):
        return jsonify(ok=False, error="taille_invalide"), 400
    return jsonify(ok=True, upload_id=upload_id)


@app.route("/api/admin/rag/upload/chunk", methods=["POST"])
@admin_required
def api_rag_upload_chunk():
    """Reçoit un morceau brut (< MAX_CONTENT_LENGTH) et l'assemble côté serveur."""
    upload_id = (request.args.get("upload_id") or "").strip()
    if not _rag_valid_upload_id(upload_id):
        return jsonify(ok=False, error="upload_invalide"), 400
    try:
        idx = int(request.args.get("idx"))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="idx_invalide"), 400
    data = request.get_data(cache=False)
    if not data:
        return jsonify(ok=False, error="morceau_vide"), 400
    try:
        rag.add_chunk(upload_id, idx, data)
    except RagError as exc:
        return jsonify(ok=False, error=exc.code), exc.status
    return jsonify(ok=True)


@app.route("/api/admin/rag/upload/finish", methods=["POST"])
@admin_required
def api_rag_upload_finish():
    """Assemble, extrait, découpe et enregistre le document. Réponse immédiate ;
    l'indexation (embeddings) est ensuite pilotée par le client via index-next."""
    data = request.get_json(silent=True) or {}
    upload_id = (data.get("upload_id") or "").strip()
    if not _rag_valid_upload_id(upload_id):
        return jsonify(ok=False, error="upload_invalide"), 400
    try:
        doc = rag.finish_upload(upload_id, (data.get("title") or "").strip(),
                                (data.get("theme") or "").strip(),
                                (data.get("visibility") or "public").strip())
    except RagError as exc:
        return jsonify(ok=False, error=exc.code), exc.status
    return jsonify(ok=True, document=doc)


@app.route("/api/admin/rag/documents/<doc_id>/index-next", methods=["POST"])
@admin_required
def api_rag_index_next(doc_id):
    """Indexe le prochain lot de chunks (piloté par le client : ne bloque pas le worker)."""
    if not _rag_valid_doc_id(doc_id):
        return jsonify(ok=False, error="document_invalide"), 400
    try:
        return jsonify(ok=True, **rag.index_next(doc_id))
    except RagError as exc:
        return jsonify(ok=False, error=exc.code), exc.status


@app.route("/api/admin/rag/documents/<doc_id>/reindex", methods=["POST"])
@admin_required
def api_rag_reindex(doc_id):
    """Régénère les embeddings d'un document (ex. après activation de MISTRAL_API_KEY) :
    le repasse en 'indexing' ; le client relance ensuite index-next pour l'indexer."""
    if not _rag_valid_doc_id(doc_id):
        return jsonify(ok=False, error="document_invalide"), 400
    try:
        return jsonify(ok=True, **rag.reindex(doc_id))
    except RagError as exc:
        return jsonify(ok=False, error=exc.code), exc.status


@app.route("/api/admin/rag/documents/<doc_id>", methods=["DELETE"])
@admin_required
def api_rag_delete(doc_id):
    """Supprime un document et tous ses chunks (et son fichier d'origine)."""
    if not _rag_valid_doc_id(doc_id):
        return jsonify(ok=False, error="document_invalide"), 400
    try:
        rag.delete_document(doc_id)
    except RagError as exc:
        return jsonify(ok=False, error=exc.code), exc.status
    return jsonify(ok=True)


@app.route("/api/admin/rag/documents/<doc_id>/download", methods=["GET"])
@admin_required
def api_rag_download(doc_id):
    """Télécharge le fichier d'origine (administrateur uniquement)."""
    if not _rag_valid_doc_id(doc_id):
        return jsonify(ok=False, error="document_invalide"), 400
    try:
        filename, data = rag.get_blob(doc_id)
    except RagError as exc:
        return jsonify(ok=False, error=exc.code), exc.status
    return send_file(io.BytesIO(data), download_name=filename, as_attachment=True)


@app.route("/api/admin/rag/documents/<doc_id>/content", methods=["GET"])
@admin_required
def api_rag_content(doc_id):
    """Contenu texte lisible d'un document (pour la lecture en ligne dans la
    console) — fonctionne pour tous les formats, y compris les bulletins de veille."""
    if not _rag_valid_doc_id(doc_id):
        return jsonify(ok=False, error="document_invalide"), 400
    try:
        info = rag.document_text(doc_id)
    except RagError as exc:
        return jsonify(ok=False, error=exc.code), exc.status
    return jsonify(ok=True, **info)


# ============================================================================
#  Génération de livrables (LLM ancré sur la base de connaissance) — admin
# ============================================================================
# Le générateur produit un BROUILLON à relire/valider par un consultant. Il
# s'appuie sur la base de connaissance RAG : documents PUBLICS ET INTERNES
# (usage interne, contrairement à l'assistant public). Réservé à l'administrateur.

_ASSISTANT_MSG = {
    "not_configured": "Aucun modèle d'IA n'est activé (clé API manquante). Configurez "
                      "MISTRAL_API_KEY ou ANTHROPIC_API_KEY, puis réessayez.",
    "auth": "Le service d'IA a refusé la clé configurée. Vérifiez-la, puis réessayez.",
    "busy": "Le service d'IA est très sollicité. Réessayez dans un instant.",
    "network": "Service d'IA momentanément injoignable. Réessayez dans un instant.",
    "upstream": "La génération a échoué. Réessayez, ou changez de modèle.",
    "empty": "Requête vide.",
}


@app.route("/admin/livrables")
@admin_required
def admin_livrables_page():
    """Console de génération de livrables (réservée à l'administrateur)."""
    return _serve_fast("admin-livrables.html", _CC_ADMIN)


@app.route("/api/admin/livrables/types", methods=["GET"])
@admin_required
def api_livrables_types():
    """Types de livrables disponibles + modèles d'IA configurés."""
    return jsonify(ok=True, types=livrables.public_types(), models=assistant.available())


def _livrables_run(type_id, data, system, user, extra_query=""):
    """Ancre le prompt sur la base de connaissance (documents publics + internes),
    génère le livrable, l'enregistre dans l'historique et renvoie la réponse JSON.
    Partagé par la génération et l'affinage."""
    model = "mistral" if data.get("model") == "mistral" else "claude"
    query = (livrables.retrieval_query(type_id, data) + " " + extra_query).strip()
    # Documents de référence choisis manuellement (facultatif) ; sinon récupération auto.
    doc_ids = [d for d in (data.get("doc_ids") or []) if _rag_valid_doc_id(d)]
    # Version parente (chaînage des itérations) — présent lors d'un affinage.
    parent_id = data.get("parent_id")
    parent_id = parent_id if _rag_valid_doc_id(parent_id) else None
    hits = []
    try:
        hits = rag.search(query, k=8 if doc_ids else 6, public_only=False,
                          doc_ids=doc_ids or None)
    except Exception:
        hits = []
    context = build_context(hits, max_chars=6000)

    try:
        text, used_model = assistant.generate(model, system, user, context=context)
    except assistant.AssistantError as exc:
        return jsonify(ok=False, error=exc.code,
                       message=_ASSISTANT_MSG.get(exc.code, "Génération indisponible.")), exc.status

    sources = [{"title": h.get("title"), "theme": h.get("theme"),
                "visibility": h.get("visibility")} for h in hits]

    # Enregistrement dans l'historique (best-effort : n'interrompt jamais la réponse).
    saved_id = None
    try:
        t = livrables.get_type(type_id)
        saved_id = livrables_hist.save({
            "type": type_id, "label": t["label"] if t else type_id,
            "client": data.get("client"), "secteur": data.get("secteur"),
            "perimetre": data.get("perimetre"), "model": used_model,
            "markdown": text, "sources": sources, "parent_id": parent_id})
    except Exception:
        saved_id = None

    return jsonify(ok=True, document=text, model=model, sources=sources, id=saved_id)


@app.route("/api/admin/livrables/generate", methods=["POST"])
@admin_required
def api_livrables_generate():
    """Génère un livrable ancré sur la base de connaissance (documents publics + internes)."""
    ckey = "gen:%s" % client_ip()
    if guard.blocked(ckey, limit=12, window=600):
        return jsonify(ok=False, error="rate_limited",
                       message="Trop de générations en peu de temps. Patientez quelques minutes."), 429
    guard.fail(ckey)
    data = request.get_json(silent=True) or {}
    type_id = (data.get("type") or "").strip()
    prompts = livrables.build_prompts(type_id, data)
    if not prompts:
        return jsonify(ok=False, error="type_inconnu", message="Type de livrable inconnu."), 400
    system, user = prompts
    return _livrables_run(type_id, data, system, user)


@app.route("/api/admin/livrables/refine", methods=["POST"])
@admin_required
def api_livrables_refine():
    """Affine (régénère) un livrable existant selon des ajustements — ancré RAG, historisé."""
    ckey = "gen:%s" % client_ip()
    if guard.blocked(ckey, limit=12, window=600):
        return jsonify(ok=False, error="rate_limited",
                       message="Trop de générations en peu de temps. Patientez quelques minutes."), 429
    guard.fail(ckey)
    data = request.get_json(silent=True) or {}
    type_id = (data.get("type") or "").strip()
    previous = (data.get("previous") or "").strip()
    instructions = (data.get("instructions") or "").strip()
    if not previous:
        return jsonify(ok=False, error="sans_base", message="Aucun livrable à affiner."), 400
    if not instructions:
        return jsonify(ok=False, error="sans_consigne",
                       message="Précisez les ajustements souhaités."), 400
    prompts = livrables.build_refine_prompts(type_id, data, previous, instructions)
    if not prompts:
        return jsonify(ok=False, error="type_inconnu", message="Type de livrable inconnu."), 400
    system, user = prompts
    return _livrables_run(type_id, data, system, user, extra_query=instructions)


@app.route("/api/admin/livrables/history", methods=["GET"])
@admin_required
def api_livrables_history():
    """Liste des livrables générés (métadonnées, sans le contenu)."""
    return jsonify(ok=True, items=livrables_hist.list(), stats=livrables_hist.stats())


@app.route("/api/admin/livrables/history/<lid>", methods=["GET"])
@admin_required
def api_livrables_history_get(lid):
    """Récupère un livrable enregistré (contenu complet) pour reconsultation / ré-export."""
    if not _rag_hex(lid):
        return jsonify(ok=False, error="id_invalide"), 400
    rec = livrables_hist.get(lid)
    if not rec:
        return jsonify(ok=False, error="introuvable"), 404
    return jsonify(ok=True, item=rec)


@app.route("/api/admin/livrables/history/<lid>", methods=["DELETE"])
@admin_required
def api_livrables_history_delete(lid):
    """Supprime un livrable de l'historique."""
    if not _rag_hex(lid):
        return jsonify(ok=False, error="id_invalide"), 400
    if not livrables_hist.delete(lid):
        return jsonify(ok=False, error="introuvable"), 404
    return jsonify(ok=True)


@app.route("/api/admin/livrables/export", methods=["POST"])
@admin_required
def api_livrables_export():
    """Exporte un livrable (Markdown) en document Word (.docx) mis en page CONSEILPREV."""
    data = request.get_json(silent=True) or {}
    md = (data.get("markdown") or "").strip()
    if not md:
        return jsonify(ok=False, error="vide", message="Aucun contenu à exporter."), 400
    try:
        blob = livrables_export.build_docx(md, {"type": data.get("type"),
                                                "client": data.get("client")})
    except Exception:
        return jsonify(ok=False, error="export_echec",
                       message="La mise en page a échoué."), 500
    type_id = (data.get("type") or "livrable")
    if not type_id or not all(c.isalnum() or c in "-_" for c in type_id):
        type_id = "livrable"
    return send_file(
        io.BytesIO(blob), download_name=type_id + ".docx", as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


# ============================================================================
#  Automatisations exposées : veille CERT-FR, ingestion documentaire, pack mission
# ============================================================================

@app.route("/api/veille")
def api_veille():
    """Veille CERT-FR (publique) : derniers bulletins, résumés automatiquement."""
    return jsonify(ok=True, items=automation.veille_list(limit=60))


@app.route("/api/admin/veille/refresh", methods=["POST"])
@admin_required
def api_veille_refresh():
    """Relance manuelle de la collecte (sinon : automatique, périodique)."""
    try:
        return jsonify(ok=True, nouveaux=automation.veille_refresh())
    except Exception:
        return jsonify(ok=False, error="veille_echec"), 502


@app.route("/api/rag/ingest", methods=["POST"])
def api_rag_ingest_token():
    """Ingestion documentaire par API (automatisations externes, server-to-server).

    Protégée par jeton (X-Ingest-Token = RAG_INGEST_TOKEN, défaut : INGEST_TOKEN).
    Corps JSON : {filename, title?, theme?, visibility?, content_base64}.
    Limité par le plafond global de requête (~350 Ko de fichier par appel) —
    au-delà, passer par la console d'administration (chargement par morceaux).
    """
    token = os.environ.get("RAG_INGEST_TOKEN") or INGEST_TOKEN
    if not token:
        return jsonify(ok=False, error="not_configured"), 503
    if request.headers.get("X-Ingest-Token") != token:
        return jsonify(ok=False, error="unauthorized"), 401
    data = request.get_json(silent=True) or {}
    filename = (data.get("filename") or "").strip()
    b64 = data.get("content_base64") or ""
    if not filename or not b64:
        return jsonify(ok=False, error="parametres_manquants"), 400
    try:
        blob = base64.b64decode(b64, validate=True)
    except (ValueError, binascii.Error):
        return jsonify(ok=False, error="base64_invalide"), 400
    try:
        doc = rag.ingest_bytes(filename, blob, title=(data.get("title") or "").strip(),
                               theme=(data.get("theme") or "").strip(),
                               visibility=(data.get("visibility") or "public").strip())
    except RagError as exc:
        return jsonify(ok=False, error=exc.code), exc.status
    return jsonify(ok=True, document=doc)


# --- Pack mission : génération en chaîne des 8 livrables du programme --------
_PACK_TYPES = ["carto-exposition", "cible-soc-augmente", "roadmap-cyber",
               "strategie-ia-cyber", "gouvernance-crise", "plan-automatisation-patching",
               "catalogue-cas-usage", "reporting-programme"]
_pack_lock = threading.Lock()
_pack_status = {"running": False, "done": 0, "total": len(_PACK_TYPES),
                "current": "", "errors": [], "ids": []}


def _pack_worker(data, model):
    """Génère les 8 livrables en arrière-plan (jamais dans le cycle requête)."""
    for tid in _PACK_TYPES:
        t = livrables.get_type(tid)
        with _pack_lock:
            _pack_status["current"] = t["label"] if t else tid
        try:
            system, user = livrables.build_prompts(tid, data)
            try:
                hits = rag.search(livrables.retrieval_query(tid, data), k=6, public_only=False)
            except Exception:
                hits = []
            text, used = assistant.generate(model, system, user,
                                            context=build_context(hits, max_chars=6000))
            sources = [{"title": h.get("title"), "theme": h.get("theme"),
                        "visibility": h.get("visibility")} for h in hits]
            lid = livrables_hist.save({"type": tid, "label": t["label"] if t else tid,
                                       "client": data.get("client"),
                                       "secteur": data.get("secteur"),
                                       "perimetre": data.get("perimetre"), "model": used,
                                       "markdown": text, "sources": sources})
            with _pack_lock:
                _pack_status["ids"].append(lid)
        except Exception as exc:
            with _pack_lock:
                _pack_status["errors"].append({"type": tid,
                                               "erreur": str(getattr(exc, "code", "erreur"))})
        with _pack_lock:
            _pack_status["done"] += 1
    with _pack_lock:
        _pack_status["running"] = False
        _pack_status["current"] = ""


@app.route("/api/admin/livrables/pack-mission", methods=["POST"])
@admin_required
def api_pack_mission():
    """Lance la génération en chaîne des 8 livrables du programme AMOA IA/Cyber."""
    global _pack_status
    data = request.get_json(silent=True) or {}
    model = "mistral" if data.get("model") == "mistral" else "claude"
    if not assistant.available().get(model):
        return jsonify(ok=False, error="not_configured",
                       message=_ASSISTANT_MSG["not_configured"]), 503
    with _pack_lock:
        if _pack_status["running"]:
            return jsonify(ok=False, error="deja_en_cours",
                           message="Un pack est déjà en cours de génération."), 409
        _pack_status = {"running": True, "done": 0, "total": len(_PACK_TYPES),
                        "current": "", "errors": [], "ids": []}
    threading.Thread(target=_pack_worker, args=(dict(data), model), daemon=True).start()
    return jsonify(ok=True, total=len(_PACK_TYPES))


@app.route("/api/admin/livrables/pack-mission", methods=["GET"])
@admin_required
def api_pack_mission_status():
    """Avancement de la génération du pack (sondé par la console)."""
    with _pack_lock:
        return jsonify(ok=True, **{k: (list(v) if isinstance(v, list) else v)
                                   for k, v in _pack_status.items()})


# ============================================================================
#  Gestion des clients & prospects — conforme RGPD + AI Act art. 50 (admin)
# ============================================================================
# Inspirée du module « Gestion des clients » de Sentinel : fiches minimales
# (art. 5.1.c), base légale et consentement documentés (art. 6-7), rectification
# (art. 16), effacement avec journal anonymisé (art. 17), export/portabilité
# (art. 20), conservation limitée et purge (art. 5.1.e), journal d'audit
# (art. 5.2). Le registre des traitements (art. 30) et les mesures de
# transparence IA (AI Act art. 50) sont servis depuis rgpd.py.

def _actor():
    return (current_user() or {}).get("email") or "admin"


@app.route("/admin/clients")
@admin_required
def admin_clients_page():
    """Console de gestion des clients (réservée à l'administrateur)."""
    return _serve_fast("admin-clients.html", _CC_ADMIN)


@app.route("/api/admin/clients", methods=["GET"])
@admin_required
def api_clients_list():
    return jsonify(ok=True, clients=clients_db.list(), stats=clients_db.stats(),
                   options={"statuts": list(STATUTS), "bases": list(BASES_LEGALES),
                            "categories_pieces": list(CATEGORIES_PIECES)})


@app.route("/api/admin/clients", methods=["POST"])
@admin_required
def api_clients_create():
    data = request.get_json(silent=True) or {}
    client = clients_db.create(data, actor=_actor())
    if not client:
        return jsonify(ok=False, error="entreprise_requise",
                       message="Le nom de l'entreprise est requis."), 400
    return jsonify(ok=True, client=client)


@app.route("/api/admin/clients/<cid>", methods=["PATCH"])
@admin_required
def api_clients_update(cid):
    if not _rag_hex(cid):
        return jsonify(ok=False, error="id_invalide"), 400
    client = clients_db.update(cid, request.get_json(silent=True) or {}, actor=_actor())
    if not client:
        return jsonify(ok=False, error="introuvable"), 404
    return jsonify(ok=True, client=client)


@app.route("/api/admin/clients/<cid>", methods=["DELETE"])
@admin_required
def api_clients_delete(cid):
    """Droit à l'effacement (art. 17) : suppression définitive, journal anonymisé."""
    if not _rag_hex(cid):
        return jsonify(ok=False, error="id_invalide"), 400
    if not clients_db.delete(cid, actor=_actor()):
        return jsonify(ok=False, error="introuvable"), 404
    return jsonify(ok=True)


@app.route("/api/admin/clients/<cid>/export", methods=["GET"])
@admin_required
def api_clients_export(cid):
    """Droit d'accès / portabilité (art. 15 / 20) : export complet de la fiche.
    JSON seul s'il n'y a pas de pièce jointe ; sinon ZIP = export.json + pièces."""
    if not _rag_hex(cid):
        return jsonify(ok=False, error="id_invalide"), 400
    data = clients_db.export(cid, actor=_actor())
    if not data:
        return jsonify(ok=False, error="introuvable"), 404
    blob = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    docs = data.get("documents") or []
    if not docs:
        return send_file(io.BytesIO(blob), download_name="client-%s-export-rgpd.json" % cid[:8],
                         as_attachment=True, mimetype="application/json")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("export.json", blob)
        for d in docs:
            try:
                fname, fdata = clients_db.doc_get(cid, d["id"], actor=_actor())
                z.writestr("pieces/%s-%s" % (d["id"][:8], fname), fdata)
            except ClientsError:
                continue
    buf.seek(0)
    return send_file(buf, download_name="client-%s-export-rgpd.zip" % cid[:8],
                     as_attachment=True, mimetype="application/zip")


@app.route("/api/admin/clients/<cid>/docs/init", methods=["POST"])
@admin_required
def api_clients_doc_init(cid):
    """Ouvre le chargement par morceaux d'une pièce jointe (PDF, Word…)."""
    if not _rag_hex(cid):
        return jsonify(ok=False, error="id_invalide"), 400
    data = request.get_json(silent=True) or {}
    filename = (data.get("filename") or "").strip()
    if not filename:
        return jsonify(ok=False, error="filename_manquant"), 400
    try:
        upload_id = clients_db.doc_upload_create(cid, filename, int(data.get("total_bytes") or 0))
    except ClientsError as exc:
        return jsonify(ok=False, error=exc.code), exc.status
    except (TypeError, ValueError):
        return jsonify(ok=False, error="taille_invalide"), 400
    return jsonify(ok=True, upload_id=upload_id)


@app.route("/api/admin/clients/<cid>/docs/chunk", methods=["POST"])
@admin_required
def api_clients_doc_chunk(cid):
    """Reçoit un morceau brut de la pièce (< plafond global de requête)."""
    if not _rag_hex(cid):
        return jsonify(ok=False, error="id_invalide"), 400
    upload_id = (request.args.get("upload_id") or "").strip()
    if not _rag_valid_upload_id(upload_id):
        return jsonify(ok=False, error="upload_invalide"), 400
    try:
        idx = int(request.args.get("idx"))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="idx_invalide"), 400
    data = request.get_data(cache=False)
    if not data:
        return jsonify(ok=False, error="morceau_vide"), 400
    try:
        if clients_db.persistent:
            clients_db.doc_upload_chunk(upload_id, idx, data, cid=cid)
        else:
            clients_db.doc_upload_chunk(upload_id, idx, data)
    except ClientsError as exc:
        return jsonify(ok=False, error=exc.code), exc.status
    return jsonify(ok=True)


@app.route("/api/admin/clients/<cid>/docs/finish", methods=["POST"])
@admin_required
def api_clients_doc_finish(cid):
    """Assemble la pièce, l'enregistre et journalise l'ajout (art. 5.2)."""
    if not _rag_hex(cid):
        return jsonify(ok=False, error="id_invalide"), 400
    data = request.get_json(silent=True) or {}
    upload_id = (data.get("upload_id") or "").strip()
    if not _rag_valid_upload_id(upload_id):
        return jsonify(ok=False, error="upload_invalide"), 400
    try:
        doc = clients_db.doc_upload_finish(cid, upload_id, (data.get("categorie") or "").strip(),
                                           actor=_actor(),
                                           filename=(data.get("filename") or "").strip())
    except ClientsError as exc:
        return jsonify(ok=False, error=exc.code), exc.status
    return jsonify(ok=True, doc=doc)


@app.route("/api/admin/clients/<cid>/docs", methods=["GET"])
@admin_required
def api_clients_docs_list(cid):
    if not _rag_hex(cid):
        return jsonify(ok=False, error="id_invalide"), 400
    return jsonify(ok=True, docs=clients_db.docs_list(cid),
                   categories=list(CATEGORIES_PIECES))


@app.route("/api/admin/clients/<cid>/docs/<did>/download", methods=["GET"])
@admin_required
def api_clients_doc_download(cid, did):
    """Télécharge une pièce (opération journalisée — art. 5.2)."""
    if not (_rag_hex(cid) and _rag_hex(did)):
        return jsonify(ok=False, error="id_invalide"), 400
    try:
        filename, data = clients_db.doc_get(cid, did, actor=_actor())
    except ClientsError as exc:
        return jsonify(ok=False, error=exc.code), exc.status
    return send_file(io.BytesIO(data), download_name=filename, as_attachment=True)


@app.route("/api/admin/clients/<cid>/docs/<did>", methods=["DELETE"])
@admin_required
def api_clients_doc_delete(cid, did):
    """Supprime une pièce jointe (journalisé)."""
    if not (_rag_hex(cid) and _rag_hex(did)):
        return jsonify(ok=False, error="id_invalide"), 400
    try:
        clients_db.doc_delete(cid, did, actor=_actor())
    except ClientsError as exc:
        return jsonify(ok=False, error=exc.code), exc.status
    return jsonify(ok=True)


@app.route("/api/admin/clients/journal", methods=["GET"])
@admin_required
def api_clients_journal():
    """Journal des opérations sur les données clients (accountability, art. 5.2)."""
    return jsonify(ok=True, events=clients_db.events(limit=80))


@app.route("/api/admin/clients/purge-expired", methods=["POST"])
@admin_required
def api_clients_purge():
    """Limitation de conservation (art. 5.1.e) : purge des fiches expirées."""
    return jsonify(ok=True, purged=clients_db.purge_expired(actor=_actor()))


@app.route("/api/admin/rgpd/registre", methods=["GET"])
@admin_required
def api_rgpd_registre():
    """Registre des activités de traitement (art. 30) + mesures AI Act art. 50."""
    return jsonify(ok=True, version=rgpd.VERSION, registre=rgpd.REGISTRE, art50=rgpd.ART50)


@app.route("/offre-conseilprev-cyber.pdf")
def offre_pdf():
    """Plaquette PDF de l'offre cybersécurité industrielle (téléchargement direct)."""
    return send_from_directory(HERE, "offre-conseilprev-cyber.pdf",
                               mimetype="application/pdf")


def _send_ack(api_key, email, nom, sujet, msg):
    """Accusé de réception au demandeur (best-effort : n'interrompt jamais le flux).

    La notification interne est déjà partie ; si cet envoi échoue, on l'ignore.
    """
    prenom = (nom.split()[0] if nom.split() else "").strip()
    hi = html_lib.escape
    ack_html = (
        f"<p>Bonjour {hi(prenom)},</p>"
        "<p>Merci pour votre message. Nous avons bien reçu votre demande "
        f"«&nbsp;<strong>{hi(sujet)}</strong>&nbsp;» et reviendrons vers vous "
        "sous 48&nbsp;h ouvrées.</p>"
        "<p>Pour rappel, voici les éléments transmis&nbsp;:</p>"
        "<blockquote style=\"border-left:3px solid #22d3ee;padding-left:12px;color:#555\">"
        f"{hi(msg).replace(chr(10), '<br>')}</blockquote>"
        "<p>À très bientôt,<br>L'équipe CONSEILPREV Cyber<br>"
        "<span style=\"color:#888;font-size:13px\">Cybersécurité industrielle IT / OT / IIoT</span></p>"
    )
    try:
        requests.post(
            BREVO_API_URL,
            json={
                "sender": SENDER,
                "to": [{"email": email, "name": nom}],
                "replyTo": {"email": NOTIFY_TO, "name": "CONSEILPREV Cyber"},
                "subject": "Bien reçu — CONSEILPREV Cyber",
                "htmlContent": ack_html,
            },
            headers={"api-key": api_key, "accept": "application/json", "content-type": "application/json"},
            timeout=12,
        )
    except requests.RequestException:
        pass


def _classify_contact(sujet, msg):
    """Qualification LLM de la demande (best-effort ; None si indisponible)."""
    try:
        text, _m = assistant.generate(
            "mistral",
            "Tu qualifies une demande entrante pour un cabinet de cybersécurité "
            "industrielle. Réponds UNIQUEMENT un objet JSON compact : "
            '{"secteur":"...","urgence":"faible|moyenne|haute","resume":"une phrase factuelle"} '
            "sans aucun autre texte.",
            "Sujet choisi : %s\nMessage :\n%s" % (sujet, msg[:1200]), max_tokens=160)
        import re as _re
        m = _re.search(r"\{.*\}", text or "", _re.S)
        return json.loads(m.group(0)) if m else None
    except Exception:
        return None


def _contact_to_prospect(nom, email, org, sujet, msg):
    """Crée / actualise automatiquement la fiche prospect (module clients RGPD).

    Base légale : mesures précontractuelles (art. 6.1.b) — la personne nous a
    contactés d'elle-même. Dédoublonnage par email : une fiche existante est
    mise à jour (note ajoutée, dernière activité), jamais dupliquée. L'opération
    est journalisée (acteur « automate ») et intégralement best-effort : aucun
    échec ici n'affecte le traitement du message de contact.
    """
    try:
        quali = _classify_contact(sujet, msg) or {}
        note = "[Contact site] %s — %s" % (sujet, (quali.get("resume") or msg[:300]).strip())
        if quali.get("urgence"):
            note += " (urgence : %s)" % quali["urgence"]
        existing = next((c for c in clients_db.list()
                         if (c.get("email") or "").lower() == email.lower()), None)
        if existing:
            merged = (note + "\n" + (existing.get("notes") or "").strip())[:4000]
            clients_db.update(existing["id"], {"notes": merged}, actor="automate")
        else:
            clients_db.create({
                "entreprise": (org or "(à qualifier)")[:200], "contact": nom,
                "email": email, "secteur": (quali.get("secteur") or "")[:120],
                "statut": "prospect", "base_legale": "mesures_precontractuelles",
                "notes": note[:4000],
            }, actor="automate")
    except Exception:
        app.logger.exception("prospect auto : échec (sans impact sur le contact)")


@app.route("/api/contact", methods=["POST"])
def api_contact():
    """Traite le formulaire de contact et envoie un email via Brevo."""
    data = request.get_json(silent=True) or request.form

    # Anti-abus : limite le nombre d'envois par IP (anti-spam / anti-flood).
    ckey = "contact:%s" % client_ip()
    if guard.blocked(ckey, limit=8, window=900):
        return jsonify(ok=False, error="rate_limited",
                       message="Trop d'envois. Réessayez dans quelques minutes."), 429
    guard.fail(ckey)

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
        _send_ack(api_key, email, nom, sujet, msg)  # accusé de réception (best-effort)
        threading.Thread(target=_contact_to_prospect,        # fiche prospect automatique
                         args=(nom, email, org, sujet, msg), daemon=True).start()
        return jsonify(ok=True)
    return jsonify(ok=False, error="send_failed", status=resp.status_code), 502


@app.route("/api/stream")
@login_required
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
    if tag_for(evt) == "crit":                      # alerte email agrégée (anti-rafale)
        automation.record_critical(evt)
    return jsonify(ok=True)


@app.route("/api/state")
@login_required
def api_state():
    """Instantané de l'état courant du cockpit (inventaire, alertes, événements récents)."""
    return jsonify(state.snapshot())


@app.route("/api/assets")
@login_required
def api_assets():
    """Inventaire des actifs connus du cockpit (pour l'étude de conformité)."""
    return jsonify(assets=state.inventory())


@app.route("/api/trends")
@login_required
def api_trends():
    """Agrégats de tendance de l'historique (par jour, catégorie, zone)."""
    days = request.args.get("days", default=14, type=int) or 14
    days = max(1, min(days, 90))
    return jsonify(state.trends(days=days))


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


@app.route("/api/maintenance/purge", methods=["POST"])
def api_purge():
    """Élague l'historique des événements (rétention). Protégé par INGEST_TOKEN.

    Paramètres (query) : retention_days, max_rows. À défaut, valeurs des variables
    d'environnement EVENT_RETENTION_DAYS / EVENT_MAX_ROWS.
    """
    if not INGEST_TOKEN:
        return jsonify(ok=False, error="not_configured"), 503
    if request.headers.get("X-Ingest-Token") != INGEST_TOKEN:
        return jsonify(ok=False, error="unauthorized"), 401
    days = request.args.get("retention_days", type=float) or _RETENTION_DAYS
    max_rows = request.args.get("max_rows", type=int) or _MAX_ROWS
    deleted = state.purge(retention_days=days or None, max_rows=max_rows or None,
                          archive_path=_ARCHIVE_PATH)
    return jsonify(ok=True, deleted=deleted)


@app.route("/health")
def health():
    """Point de santé (utilisé par Render pour vérifier le service)."""
    return jsonify(status="ok", service="conseilprevcyber"), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
