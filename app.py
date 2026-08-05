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
import concurrent.futures as _futures
import gzip
import hashlib
import hmac
import json
import os
import io
import queue
import threading
import time
import zipfile

from urllib.parse import urlparse

import requests
from flask import (Flask, Response, jsonify, redirect, request, send_file,
                   send_from_directory, stream_with_context)

import assistant
import audit
import automation
import juridique
import livrables
import livrables_export
import playbook
import minimisation
import rgpd
from auth import admin_required, client_ip, current_user, guard, init_app as init_auth
from clients_store import (BASES_LEGALES, CATEGORIES_PIECES, STATUTS,
                           ClientsError, make_clients_store)
from cockpit_state import make_store, tag_for
from livrables_store import make_livrables_store
from rag_store import (RagError, THEMES, THEME_FAMILLES, FAMILLE_ENTREPRISES,
                       FAMILLE_ENGINEERING, build_context, dedupe as rag_dedupe,
                       diagnose as rag_diagnose, duplicate_groups,
                       extract_text as rag_extract_text,
                       formats_available, make_rag_store)

app = Flask(__name__)
HERE = os.path.dirname(os.path.abspath(__file__))

# Version applicative affichée dans l'admin (auto-test de la base de connaissance).
# Sert à vérifier d'un coup d'œil QUELLE version tourne réellement en production :
# si le numéro affiché est plus ancien que la version attendue, le déploiement n'a
# pas abouti — et aucun correctif récent n'est en ligne. À incrémenter à chaque
# correctif dont on veut pouvoir confirmer la mise en ligne.
APP_VERSION = "2026.07.29-08"

# Horodatage de démarrage du processus (voir /health : « demarre_depuis_s »).
_DEMARRAGE = time.time()

# --- Sécurité applicative (en-têtes, anti-CSRF, taille de requête) -------------
# Plafond de taille du corps d'une requête (anti-abus mémoire / DoS).
# Le chargement d'un document dans la base de connaissance (admin) envoie le
# fichier ENTIER en une seule requête : le plafond global doit donc l'accepter.
# Toutes les AUTRES routes restent bornées à un petit plafond (voir
# _limit_body_size plus bas) — la surface d'abus n'augmente pas pour le public.
RAG_UPLOAD_MAX = 32 * 1024 * 1024   # fichier (~30 Mo) + surcoût multipart
SMALL_BODY_MAX = 512 * 1024
app.config["MAX_CONTENT_LENGTH"] = RAG_UPLOAD_MAX
# Routes autorisées à recevoir un gros corps (upload d'un fichier entier,
# restauration d'une sauvegarde de la base de connaissance).
#
# Le dépôt de documents client y figure : il reçoit le fichier entier encodé en
# base64 dans une seule requête JSON. Sans cette déclaration, il retombait sur
# le plafond commun de 512 Ko — soit, l'inflation du base64 déduite, un fichier
# réel d'environ 380 Ko. Le plafond annoncé était de 30 Mo : l'écart entre ce
# qui est affiché et ce qui passe est exactement le genre de défaut qu'on
# découvre au premier document un peu lourd.
_LARGE_BODY_PATHS = {"/api/admin/rag/upload-file", "/api/admin/rag/restore",
                     "/api/datacenter/depot"}


class _IPRateLimiter:
    """Limiteur de débit par IP (fenêtre glissante, en mémoire). Distinct du
    « guard » d'échecs (anti-force brute) : ici on limite le VOLUME de requêtes
    — défense anti-DoS. Un attaquant qui martèle la connexion, l'upload ou
    l'admin est plafonné puis renvoyé en 429."""

    def __init__(self):
        self._hits = {}
        self._lock = threading.Lock()

    def over(self, key, limit, window):
        now = time.time()
        with self._lock:
            arr = [t for t in self._hits.get(key, []) if t > now - window]
            arr.append(now)
            self._hits[key] = arr
            if len(self._hits) > 8192:          # borne mémoire : purge des clés éteintes
                for k in [k for k, v in self._hits.items() if not v or v[-1] < now - 3600]:
                    self._hits.pop(k, None)
            return len(arr) > limit


_ip_rate = _IPRateLimiter()

# Plafonds par IP. Stricts sur les points sensibles (force brute / upload),
# généreux en famille pour ne pas gêner l'usage admin légitime.
_RATE_EXACT = {
    "/api/auth/login":            (12, 300),
    "/api/auth/register":         (6, 3600),
    "/api/auth/forgot":           (6, 3600),
    "/api/auth/reset":            (12, 3600),
    "/api/admin/rag/upload-file": (40, 60),
    "/api/admin/rag/restore":     (6, 300),
    "/api/admin/rag/backup":      (20, 300),
}
_RATE_FAMILY = (("/api/auth/", 80, 60), ("/api/admin/", 600, 60))

# Points protégés par jeton (server-to-server) : exemptés du contrôle d'origine
# CSRF, car authentifiés par un secret d'en-tête (X-Ingest-Token) et non par un
# cookie de session — donc non vulnérables au CSRF (qui exploite le cookie ambiant).
_CSRF_EXEMPT = {"/api/ingest", "/api/reset", "/api/maintenance/purge", "/api/rag/ingest"}

# En-tête maison posé par nos propres appels d'écriture (voir _same_origin_request).
# Un site tiers ne peut pas le poser sans pré-vérification CORS — que ce service
# n'accorde jamais : il constitue donc une preuve de même origine, utile quand le
# navigateur n'envoie ni « Origin » ni « Referer ».
_CSRF_HEADER = "X-CP-Same-Origin"
_CSRF_HEADER_VALUE = "1"

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


def _token_ok(provided, expected):
    """Comparaison en temps constant du jeton d'ingestion (hmac.compare_digest) :
    un attaquant ne peut pas reconstituer le jeton octet par octet en mesurant
    les délais de réponse."""
    return bool(expected) and hmac.compare_digest(provided or "", expected)


def _same_origin_request():
    """Vrai si la requête provient de notre propre origine (défense anti-CSRF).

    1. Si « Origin » ou « Referer » est présent, il DOIT désigner notre hôte —
       contrôle strict, inchangé.
    2. Si les DEUX sont absents, on accepte à la seule condition que la requête
       porte notre en-tête maison (_CSRF_HEADER). Ce cas n'est pas un laxisme :
       un navigateur envoie TOUJOURS « Origin » sur un POST inter-origines, y
       compris depuis un formulaire — leur absence conjointe caractérise donc une
       requête de MÊME origine émise par un navigateur durci (ou une extension de
       confidentialité qui supprime le référent), jamais une attaque CSRF. Et un
       en-tête personnalisé est justement ce qu'un site tiers ne peut PAS poser
       sans pré-vérification CORS, que ce service n'accorde à personne.

    Sans ce rattrapage, un tel navigateur voyait TOUTES ses requêtes d'écriture
    rejetées en 403 — pages consultables (GET) mais plus aucun chargement
    possible, sur tous les blocs à la fois."""
    src = request.headers.get("Origin") or request.headers.get("Referer") or ""
    if not src:
        return request.headers.get(_CSRF_HEADER) == _CSRF_HEADER_VALUE
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


@app.before_request
def _limit_body_size():
    """Plafond serré (512 Ko) sur TOUTES les routes sauf l'upload de fichier
    (admin), qui reçoit un document entier en une requête. Contrôle par
    l'en-tête Content-Length : rejet immédiat sans lire le corps."""
    cl = request.content_length
    if cl is None:
        return
    cap = RAG_UPLOAD_MAX if request.path in _LARGE_BODY_PATHS else SMALL_BODY_MAX
    if cl > cap:
        return jsonify(ok=False, error="requete_trop_grande",
                       message="Contenu trop volumineux."), 413


def _rate_limited(retry_after):
    resp = jsonify(ok=False, error="rate_limited",
                   message="Trop de requêtes. Réessayez dans un instant.")
    resp.status_code = 429
    resp.headers["Retry-After"] = str(int(retry_after))
    return resp


@app.before_request
def _rate_limit():
    """Limitation de débit par IP (anti-DoS + défense en profondeur anti-force
    brute) sur les surfaces sensibles : authentification et administration. Les
    pages publiques et les fichiers statiques ne sont pas concernés. L'indexation
    vectorielle (index-next), pilotée par le client en boucle serrée mais bornée
    et réservée à l'admin, est exemptée pour ne pas casser un gros chargement."""
    p = request.path
    if not (p.startswith("/api/auth/") or p.startswith("/api/admin/")):
        return
    ip = client_ip()
    rule = _RATE_EXACT.get(p)
    if rule and _ip_rate.over("x:%s:%s" % (p, ip), rule[0], rule[1]):
        return _rate_limited(rule[1])
    if p.endswith("/index-next"):
        return
    for prefix, lim, win in _RATE_FAMILY:
        if p.startswith(prefix):
            if _ip_rate.over("f:%s:%s" % (prefix, ip), lim, win):
                return _rate_limited(win)
            break


@app.after_request
def _security_headers(resp):
    for key, value in _SECURITY_HEADERS.items():
        resp.headers.setdefault(key, value)
    # Les API d'administration et d'authentification renvoient des données
    # sensibles : jamais de mise en cache (navigateur ou proxy) par défaut.
    p = request.path
    if p.startswith("/api/admin/") or p.startswith("/api/auth/"):
        resp.headers.setdefault("Cache-Control", "private, no-store")
    if _request_is_https():
        resp.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return resp


# Compression des réponses dynamiques JSON / texte / XML (listes de documents,
# historiques de livrables, contenus, sitemap…) : 70-90 % de réduction, donc
# des téléchargements et affichages nettement plus rapides. Les flux (SSE),
# les réponses déjà encodées (pages statiques pré-gzippées) et les binaires
# (docx/pdf/zip, déjà compressés) ne sont pas touchés.
_GZIP_MIN = 1400  # en dessous d'un paquet réseau, la compression ne gagne rien


@app.after_request
def _compress_text(resp):
    try:
        if (resp.status_code != 200 or resp.direct_passthrough or resp.is_streamed
                or resp.headers.get("Content-Encoding")):
            return resp
        mt = resp.mimetype or ""
        if not (mt.endswith("json") or mt.endswith("xml")
                or (mt.startswith("text/") and mt != "text/event-stream")):
            return resp
        if "gzip" not in (request.headers.get("Accept-Encoding") or "").lower():
            return resp
        data = resp.get_data()
        if len(data) < _GZIP_MIN:
            return resp
        gz = gzip.compress(data, 5)
        if len(gz) >= len(data):
            return resp
        resp.set_data(gz)
        resp.headers["Content-Encoding"] = "gzip"
        resp.headers["Content-Length"] = str(len(gz))
        resp.vary.add("Accept-Encoding")
    except Exception:
        pass
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

# Construction des stores persistants (PostgreSQL si DATABASE_URL, sinon mémoire).
# Base injoignable : chaque store attend l'échec de connexion (~quelques secondes)
# avant de basculer en mémoire. On lance les trois constructions BLOQUANTES en
# parallèle (la base RAG, elle, est déjà non bloquante) : le worker démarre en un
# seul délai au lieu de leur somme. Décisif pour les réveils « cold start » de
# l'hébergeur — sinon la première requête paraît « en chargement » tout le boot.
_boot_pool = _futures.ThreadPoolExecutor(max_workers=3)
_f_state = _boot_pool.submit(make_store)          # cockpit — voir cockpit_state.py
_f_liv = _boot_pool.submit(make_livrables_store)  # historique des livrables générés
_f_cli = _boot_pool.submit(make_clients_store)    # clients & prospects (RGPD)

# Base de connaissance RAG : repli mémoire + reconnexion de fond (jamais bloquant).
# Alimente l'assistant et les livrables ; gérée par l'administrateur (@admin_required).
rag = make_rag_store()

state = _f_state.result()
livrables_hist = _f_liv.result()
clients_db = _f_cli.result()
_boot_pool.shutdown(wait=False)


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


# automation.init ouvre son propre pool (bloquant ~quelques secondes si la base
# est coupée) puis démarre le planificateur de fond. On l'initialise EN TÂCHE DE
# FOND pour ne pas retarder le boot : la veille renvoie une liste vide le temps
# de l'initialisation (quelques secondes), puis se peuple normalement.
def _init_automation():
    automation.init(sender=SENDER, notify_to=NOTIFY_TO, rag=rag, clients=clients_db,
                    livrables=livrables_hist, cockpit=state,
                    summarize=_veille_summarize, generate_report=_report_generate,
                    dsn=os.environ.get("DATABASE_URL"))


threading.Thread(target=_init_automation, daemon=True).start()

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
    "/operating-model": "operating-model.html",
    "/maturite-ot": "maturite-ot.html",
    "/feuille-de-route": "feuille-de-route.html",
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
    "/continuite-ot": "continuite-ot.html",
    "/gestion-des-changements": "gestion-des-changements.html",
    "/architecture-cible": "architecture-cible.html",
    "/formation": "formation.html",
    "/gouvernance-ia": "gouvernance-ia.html",
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
    "/conformite": "conformite.html",
    "/nis2": "nis2.html",
    "/diagnostic": "diagnostic.html",
    "/veille": "veille.html",
    "/juridique": "juridique.html",
    "/relecture-contrat": "relecture-contrat.html",
    "/datacenter": "datacenter.html",
    "/ingenierie-datacenter": "ingenierie-datacenter.html",
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


# Offres conseil & transformation — pages vitrine publiques (comme /services).
@app.route("/operating-model")
def operating_model():
    return _page(PAGES["/operating-model"])


@app.route("/maturite-ot")
def maturite_ot():
    return _page(PAGES["/maturite-ot"])


@app.route("/feuille-de-route")
def feuille_de_route():
    return _page(PAGES["/feuille-de-route"])


@app.route("/continuite-ot")
def continuite_ot():
    return _page(PAGES["/continuite-ot"])


@app.route("/gestion-des-changements")
def gestion_des_changements():
    return _page(PAGES["/gestion-des-changements"])


@app.route("/architecture-cible")
def architecture_cible():
    return _page(PAGES["/architecture-cible"])


@app.route("/formation")
def formation():
    return _page(PAGES["/formation"])


@app.route("/gouvernance-ia")
def gouvernance_ia():
    return _page(PAGES["/gouvernance-ia"])


@app.route("/etudes-de-cas")
def etudes_de_cas():
    return _page(PAGES["/etudes-de-cas"])


@app.route("/referentiel")
@login_required
def referentiel():
    return _page(PAGES["/referentiel"])


@app.route("/analyse-de-risque")
@login_required
def analyse_de_risque():
    return _page(PAGES["/analyse-de-risque"])


@app.route("/secteurs")
def secteurs():
    return _page(PAGES["/secteurs"])


@app.route("/methodologie")
@login_required
def methodologie():
    return _page(PAGES["/methodologie"])


@app.route("/exigences-systeme")
@login_required
def exigences_systeme():
    return _page(PAGES["/exigences-systeme"])


@app.route("/exigences-composants")
@login_required
def exigences_composants():
    return _page(PAGES["/exigences-composants"])


@app.route("/exigences-prestataires")
@login_required
def exigences_prestataires():
    return _page(PAGES["/exigences-prestataires"])


@app.route("/developpement-securise")
@login_required
def developpement_securise():
    return _page(PAGES["/developpement-securise"])


@app.route("/technologies-securite")
@login_required
def technologies_securite():
    return _page(PAGES["/technologies-securite"])


@app.route("/programme-securite")
@login_required
def programme_securite():
    return _page(PAGES["/programme-securite"])


@app.route("/gestion-correctifs")
@login_required
def gestion_correctifs():
    return _page(PAGES["/gestion-correctifs"])


@app.route("/glossaire-62443")
@login_required
def glossaire_62443():
    return _page(PAGES["/glossaire-62443"])


@app.route("/metriques-62443")
@login_required
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


def _is_admin_request():
    """L'appelant est-il un administrateur connecté ? Même règle que
    admin_required (compte connecté + rôle « admin »), mais SANS bloquer : sert à
    élargir le périmètre documentaire, jamais à autoriser une action."""
    try:
        u = current_user()
        return bool(u) and (u.get("role") or "user") == "admin"
    except Exception:
        return False


def _minimiser(textes, mode):
    """Contrôle de minimisation avant tout envoi à un modèle (RGPD art. 5.1.c).

    `textes` est la liste des saisies de l'utilisateur — et elles seules : les
    documents de la base de connaissance sont choisis par CONSEILPREV, pas
    tapés dans un formulaire, et avertir à leur sujet serait un bruit que
    l'utilisateur ne peut pas corriger.

    `mode` vient du navigateur et vaut :
      ""         → premier envoi : on contrôle et, si besoin, on refuse en
                   décrivant ce qui a été trouvé ;
      "masquer"  → l'utilisateur demande le caviardage automatique ;
      "accepter" → l'utilisateur a lu l'avertissement et maintient l'envoi.

    Retourne (textes_a_utiliser, refus_ou_None, resume_pour_le_journal).
    Le contrôle est fait ICI et non dans le navigateur : un avertissement
    contournable en changeant d'onglet n'est pas une mesure de minimisation.
    """
    mode = (mode or "").strip().lower()
    joint = "\n".join(t for t in textes if t)
    res = minimisation.analyser(joint)
    resume = minimisation.resume_journal(res)
    if not res["total"]:
        return textes, None, resume
    if mode == "masquer":
        return ([minimisation.masquer(t) for t in textes], None,
                resume + " (caviardées)")
    if mode == "accepter":
        return textes, None, resume + " (maintenues par l'utilisateur)"
    refus = (jsonify(ok=False, error="donnees_personnelles",
                     minimisation=res, message=res["message"]), 200)
    return textes, refus, resume + " (envoi suspendu)"


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

    # Minimisation avant transmission : le dernier message de l'utilisateur est
    # contrôlé, et lui seul — les tours précédents ont déjà été validés, les
    # redemander à chaque envoi rendrait la conversation impraticable.
    mode_min = (data.get("minimisation") or "").strip().lower()
    dernier = ""
    try:
        dernier = assistant.last_user_message(messages) or ""
    except Exception:
        dernier = ""
    (dernier,), refus, _resume = _minimiser([dernier], mode_min)
    if refus:
        return refus
    if dernier and isinstance(messages, list):
        # Le caviardage doit porter sur ce qui part réellement au modèle.
        for m in reversed(messages):
            if isinstance(m, dict) and m.get("role") == "user":
                m["content"] = dernier
                break

    # Récupération RAG, dont le PÉRIMÈTRE DÉPEND DE QUI INTERROGE :
    #   - visiteur anonyme  -> documents publics uniquement (inchangé) ;
    #   - administrateur connecté -> publics ET internes.
    # C'est la bonne réponse au besoin « des réponses plus précises à partir de mes
    # livrables » : elle l'obtient SANS jamais rendre un document propriétaire
    # accessible au public. Basculer la visibilité des documents pour enrichir ses
    # propres réponses reviendrait à les exposer à tous les visiteurs — et le vrai
    # danger n'est pas la bascule, c'est l'oubli de la rebasculer.
    # Best-effort : une erreur de récupération ne casse jamais le chat.
    context = None
    interne_autorise = _is_admin_request()
    try:
        query = assistant.last_user_message(messages)
        if query:
            context = build_context(rag.search(query, k=5,
                                               public_only=not interne_autorise))
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
            "timeout": "Le modèle a mis trop de temps à répondre. Réessayez, ou essayez l'autre modèle.",
            "upstream": "L'assistant a rencontré une erreur. Réessayez, ou contactez-nous.",
        }
        return jsonify(ok=False, error=exc.code,
                       message=messages.get(exc.code, "Assistant indisponible pour le moment.")), exc.status
    # Après caviardage, on renvoie le texte RÉELLEMENT transmis : l'utilisateur
    # doit voir ce qui est parti, et la suite de la conversation doit repartir
    # de cette version — sinon le tour suivant renverrait l'original en clair.
    return jsonify(ok=True, reply=reply, model=model,
                   envoye=dernier if mode_min == "masquer" else None)


# ============================================================================
#  Conseil juridique assisté — services numériques, cyber IT/OT/ICS, IA
# ============================================================================
# Trois niveaux, volontairement séparés (voir juridique.py) :
#   1. la QUALIFICATION est déterministe — aucun modèle n'intervient, le
#      résultat est reproductible et chaque rattachement porte sa motivation ;
#   2. le CLAUSIER et les POINTS D'INTERPRÉTATION sont des données figées ;
#   3. seule l'ANALYSE fait appel à un modèle, cadrée par un référentiel fermé
#      et vérifiée a posteriori (détection des références inventées).
# L'accès est réservé aux comptes connectés : c'est une prestation de conseil,
# pas un contenu de vitrine.

@app.route("/juridique")
@login_required
def juridique_page():
    """Conseil juridique assisté (clients connectés et administrateur)."""
    return _page(PAGES["/juridique"])


@app.route("/api/juridique/config")
@login_required
def api_juridique_config():
    """Tout ce dont l'interface a besoin pour se construire : questionnaire,
    référentiel, clausier, amorces. Une seule définition côté serveur — une liste
    d'options recopiée dans le HTML finit toujours par diverger du moteur."""
    return jsonify(ok=True,
                   version_referentiel=juridique.VERSION_REFERENTIEL,
                   champs=juridique.PROFIL_CHAMPS,
                   referentiel=juridique.referentiel(),
                   domaines_clausier=juridique.DOMAINES_CLAUSIER,
                   suggestions=juridique.SUGGESTIONS,
                   avertissement=juridique.AVERTISSEMENT,
                   mention_ia=juridique.MENTION_IA,
                   models=assistant.available())


@app.route("/api/juridique/qualification", methods=["POST"])
@login_required
def api_juridique_qualification():
    """Qualification réglementaire d'un profil. Aucun appel de modèle : la
    réponse est identique à chaque exécution et opposable telle quelle."""
    data = request.get_json(silent=True) or {}
    profil = data.get("profil") if isinstance(data.get("profil"), dict) else data
    try:
        res = juridique.qualifier(profil)
    except Exception:
        app.logger.exception("qualification juridique")
        return jsonify(ok=False, error="qualification_echec",
                       message="La qualification a échoué."), 500
    audit.journaliser("juridique.qualification",
                      cible=str((profil or {}).get("secteur") or "-"),
                      detail="%d texte(s) applicable(s), %d à confirmer"
                             % (len(res["applicables"]), len(res["a_verifier"])))
    return jsonify(ok=True, **res)


@app.route("/api/juridique/clausier")
@login_required
def api_juridique_clausier():
    """Clausier fournisseurs, filtrable par domaine et par criticité."""
    return jsonify(ok=True,
                   domaines=juridique.DOMAINES_CLAUSIER,
                   clauses=juridique.clausier(
                       domaine=(request.args.get("domaine") or "").strip() or None,
                       criticite=(request.args.get("criticite") or "").strip() or None),
                   avertissement=juridique.AVERTISSEMENT)


@app.route("/api/juridique/controverses")
@login_required
def api_juridique_controverses():
    """Points d'interprétation ouverts — plusieurs lectures, jamais une seule."""
    ids = [x for x in (request.args.get("textes") or "").split(",") if x.strip()]
    return jsonify(ok=True, points=juridique.controverses(ids or None))


def _juridique_extraits(question, profil):
    """Extraits de la base documentaire pertinents pour la question.

    Le périmètre suit l'identité de l'appelant (documents internes réservés à
    l'administrateur), comme partout ailleurs. Best-effort : une base
    momentanément indisponible dégrade la précision, elle ne bloque pas
    l'analyse — le référentiel des textes suffit à produire une réponse utile.
    """
    try:
        requete = " ".join(x for x in [
            question,
            (profil or {}).get("secteur") or "",
        ] if x)[:500]
        hits = rag.search(requete, k=6, public_only=not _is_admin_request())
        if not hits:
            return "", []
        blocs, sources = [], []
        for i, h in enumerate(hits, start=1):
            blocs.append("[%d] %s\n%s" % (i, str(h.get("title") or "")[:120],
                                          str(h.get("text") or "")[:900]))
            sources.append({"n": i, "titre": str(h.get("title") or "")[:140],
                            "theme": h.get("theme"), "doc_id": h.get("doc_id")})
        return "\n\n".join(blocs), sources
    except Exception:
        return "", []


_JURIDIQUE_ERREURS = {
    "not_configured": "Ce modèle n'est pas activé. Essayez l'autre modèle.",
    "auth": "Le service d'IA a refusé la clé configurée.",
    "empty": "La question est vide.",
    "busy": "Service très sollicité. Réessayez dans un instant.",
    "network": "Service d'IA momentanément injoignable. Réessayez dans un instant.",
    "timeout": "L'analyse a dépassé le délai. Réessayez, ou réduisez le contrat soumis.",
    "upstream": "L'analyse a échoué. Réessayez, ou contactez-nous.",
}


@app.route("/api/juridique/analyse", methods=["POST"])
@login_required
def api_juridique_analyse():
    """Analyse juridique argumentée : qualification, textes, LECTURES POSSIBLES,
    risque, recommandation, réserves.

    La qualification déterministe est calculée d'abord et transmise au modèle :
    il ne décide pas de ce qui s'applique, il l'explique et l'interprète.
    """
    ckey = "jur:%s" % client_ip()
    if guard.blocked(ckey, limit=12, window=600):
        return jsonify(ok=False, error="rate_limited",
                       message="Trop d'analyses en peu de temps. Patientez quelques minutes."), 429
    guard.fail(ckey)

    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify(ok=False, error="question_vide",
                       message="Posez une question."), 400
    if len(question) > 4000:
        question = question[:4000]
    profil = data.get("profil") if isinstance(data.get("profil"), dict) else None
    model = "mistral" if data.get("model") == "mistral" else "claude"

    (question,), refus, resume_min = _minimiser([question], data.get("minimisation"))
    if refus:
        return refus

    qual = juridique.qualifier(profil) if profil else None
    textes_ids = None
    if qual:
        textes_ids = [x["id"] for x in qual["applicables"]] + \
                     [x["id"] for x in qual["a_verifier"]]
    extraits, sources = _juridique_extraits(question, profil)
    user = juridique.prompt_analyse(question, profil=profil, extraits=extraits,
                                    textes_ids=textes_ids)
    try:
        texte, used = assistant.generate(model, juridique.SYSTEM_JURIDIQUE, user,
                                         max_tokens=3200)
    except assistant.AssistantError as exc:
        return jsonify(ok=False, error=exc.code,
                       message=_JURIDIQUE_ERREURS.get(
                           exc.code, "Analyse indisponible pour le moment.")), exc.status

    res = juridique.post_traiter(texte, textes_ids)
    audit.journaliser("juridique.analyse", cible=used,
                      detail="%d extrait(s) cité(s), %d référence(s) suspecte(s) ; "
                             "minimisation : %s"
                             % (len(sources), len(res["citations"]["suspectes"]),
                                resume_min),
                      ok=not res["citations"]["suspectes"])
    return jsonify(ok=True, model=used, sources=sources,
                   qualification=qual, **res)


@app.route("/api/juridique/contrat", methods=["POST"])
@login_required
def api_juridique_contrat():
    """Revue d'un contrat de services fournisseur, clause par clause.

    Le contrat est analysé EN MÉMOIRE et n'est jamais conservé : un contrat
    fournisseur est une pièce sensible, et rien n'oblige à le stocker pour le
    relire. Deux entrées possibles : texte collé, ou fichier PDF/DOCX/TXT.
    """
    ckey = "jurc:%s" % client_ip()
    if guard.blocked(ckey, limit=6, window=600):
        return jsonify(ok=False, error="rate_limited",
                       message="Trop d'analyses de contrat. Patientez quelques minutes."), 429
    guard.fail(ckey)

    texte_contrat, profil, domaines, model, mode_min = "", None, None, "claude", ""
    fichier = request.files.get("fichier")
    if fichier is not None:
        nom = (fichier.filename or "").lower()
        ext = nom.rsplit(".", 1)[-1] if "." in nom else ""
        if ext not in ("pdf", "docx", "txt", "md"):
            return jsonify(ok=False, error="format_refuse",
                           message="Formats acceptés : PDF, DOCX, TXT, MD."), 400
        blob = fichier.read(6 * 1024 * 1024 + 1)
        if len(blob) > 6 * 1024 * 1024:
            return jsonify(ok=False, error="trop_gros",
                           message="Fichier trop volumineux (6 Mo maximum)."), 400
        try:
            texte_contrat = rag_extract_text(ext, blob) or ""
        except Exception:
            texte_contrat = ""
        if not texte_contrat.strip():
            return jsonify(ok=False, error="illisible",
                           message="Aucun texte n'a pu être extrait de ce fichier "
                                   "(document scanné ?). Collez le texte à la place."), 400
        profil = _json_champ(request.form.get("profil"))
        domaines = _json_champ(request.form.get("domaines"))
        model = "mistral" if request.form.get("model") == "mistral" else "claude"
        mode_min = request.form.get("minimisation") or ""
    else:
        data = request.get_json(silent=True) or {}
        texte_contrat = (data.get("texte") or "").strip()
        profil = data.get("profil") if isinstance(data.get("profil"), dict) else None
        domaines = data.get("domaines") if isinstance(data.get("domaines"), list) else None
        model = "mistral" if data.get("model") == "mistral" else "claude"
        mode_min = data.get("minimisation") or ""

    if len(texte_contrat.strip()) < 200:
        return jsonify(ok=False, error="contrat_vide",
                       message="Fournissez le texte du contrat (200 caractères minimum)."), 400

    # C'est ici que la minimisation compte le plus : un contrat porte des
    # signataires, des adresses et parfois un RIB, dont AUCUN n'est utile à
    # l'analyse des clauses. Sur un PDF, l'utilisateur ne peut pas corriger sa
    # saisie — le caviardage automatique est la seule option praticable, et il
    # est proposé plutôt qu'imposé.
    (texte_contrat,), refus, resume_min = _minimiser([texte_contrat], mode_min)
    if refus:
        return refus

    user = juridique.prompt_contrat(texte_contrat, profil=profil, domaines=domaines)
    try:
        texte, used = assistant.generate(model, juridique.SYSTEM_JURIDIQUE, user,
                                         max_tokens=4000)
    except assistant.AssistantError as exc:
        return jsonify(ok=False, error=exc.code,
                       message=_JURIDIQUE_ERREURS.get(
                           exc.code, "Analyse indisponible pour le moment.")), exc.status

    res = juridique.post_traiter(texte)
    audit.journaliser("juridique.contrat", cible=used,
                      detail="%d caractères analysés, %d référence(s) suspecte(s) ; "
                             "minimisation : %s"
                             % (len(texte_contrat), len(res["citations"]["suspectes"]),
                                resume_min),
                      ok=not res["citations"]["suspectes"])
    return jsonify(ok=True, model=used, caracteres=len(texte_contrat), **res)


@app.route("/api/juridique/arbitrage", methods=["POST"])
@login_required
def api_juridique_arbitrage():
    """Note d'arbitrage : synthétiser un dossier et préparer la décision.

    Ce qu'attend un comité de direction n'est pas « que dit le droit » mais
    « que décide-t-on, qui décide, avant quand ». Trois choses sont donc
    produites, et une seule vient du modèle :
      - le ROUTAGE (qui tranche, qui est consulté) — moteur de règles, car
        lorsqu'un texte réserve une décision à un organe, s'en écarter est un
        manquement et non un choix d'organisation ;
      - les ÉCHÉANCES réglementaires — elles commandent le calendrier ;
      - la SYNTHÈSE, les OPTIONS et la RECOMMANDATION — le modèle, sur les
        seules pièces réellement fournies.

    Le dossier se compose de sources cumulables : des documents DÉSIGNÉS dans la
    base de connaissance, un texte collé, et le contexte saisi. Les documents
    désignés sont lus INTÉGRALEMENT et non recherchés par similarité : quand on
    soumet un contrat à un comité, on ne veut pas les trois passages les plus
    ressemblants, on veut la pièce.
    """
    ckey = "jura:%s" % client_ip()
    if guard.blocked(ckey, limit=8, window=600):
        return jsonify(ok=False, error="rate_limited",
                       message="Trop de notes d'arbitrage en peu de temps. "
                               "Patientez quelques minutes."), 429
    guard.fail(ckey)

    data = request.get_json(silent=True) or {}
    objet = (data.get("objet") or "").strip()
    if not objet:
        return jsonify(ok=False, error="objet_vide",
                       message="Indiquez la décision à préparer."), 400
    objet = objet[:2000]
    profil = data.get("profil") if isinstance(data.get("profil"), dict) else None
    dossier = data.get("dossier") if isinstance(data.get("dossier"), dict) else {}
    contexte = (data.get("contexte") or "").strip()[:6000]
    colle = (data.get("texte") or "").strip()

    # Les trois saisies du demandeur sont contrôlées ensemble ; les documents
    # DÉSIGNÉS dans la base ne le sont pas — ils sont choisis par CONSEILPREV
    # et l'utilisateur n'a aucun moyen de les corriger.
    (objet, contexte, colle), refus, resume_min = _minimiser(
        [objet, contexte, colle], data.get("minimisation"))
    if refus:
        return refus
    dossier["objet"] = objet

    doc_ids = [str(d) for d in (data.get("doc_ids") or [])
               if _rag_valid_doc_id(str(d))][:12]
    model = "mistral" if data.get("model") == "mistral" else "claude"

    # ── Constitution du dossier ─────────────────────────────────────────
    extraits, pieces, n = [], [], 0
    interne = _is_admin_request()
    try:
        catalogue = {d["id"]: d for d in rag.list_documents()}
    except Exception:
        catalogue = {}
    for doc_id in doc_ids:
        meta = catalogue.get(doc_id)
        if not meta:
            continue
        # Un document interne ne devient pas lisible parce qu'on l'a désigné :
        # le périmètre suit l'identité de l'appelant, ici comme ailleurs.
        if meta.get("visibility") == "internal" and not interne:
            continue
        try:
            # document_text renvoie {title, filename, theme, text} : c'est le
            # texte réassemblé des fragments indexés qui nous intéresse.
            texte = (rag.document_text(doc_id, limit=24000) or {}).get("text") or ""
        except Exception:
            app.logger.exception("arbitrage : pièce %r illisible", doc_id)
            continue
        if not texte.strip():
            continue
        n += 1
        extraits.append("[%d] %s (%s)\n%s"
                        % (n, str(meta.get("title") or "Document")[:140],
                           meta.get("theme") or "non classé", texte[:24000]))
        pieces.append({"n": n, "titre": str(meta.get("title") or "Document")[:140],
                       "theme": meta.get("theme"), "doc_id": doc_id,
                       "origine": "document désigné"})
    if colle:
        n += 1
        extraits.append("[%d] Pièce collée par le demandeur\n%s" % (n, colle[:24000]))
        pieces.append({"n": n, "titre": "Pièce collée", "origine": "saisie"})

    # Aucune pièce désignée : on complète par une recherche sur l'objet plutôt
    # que de laisser la note sans matière. L'origine est renvoyée à l'interface —
    # une pièce choisie n'a pas le même poids qu'un extrait retrouvé.
    if not extraits:
        try:
            for h in rag.search(objet, k=6, public_only=not interne):
                n += 1
                extraits.append("[%d] %s (extrait retrouvé automatiquement)\n%s"
                                % (n, str(h.get("title") or "")[:140],
                                   str(h.get("text") or "")[:1200]))
                pieces.append({"n": n, "titre": str(h.get("title") or "")[:140],
                               "theme": h.get("theme"), "doc_id": h.get("doc_id"),
                               "origine": "recherche automatique"})
        except Exception:
            pass

    routage = juridique.router(profil, dossier)
    textes_ids = ([x["id"] for x in routage["qualification"]["applicables"]]
                  + [x["id"] for x in routage["qualification"]["a_verifier"]])
    user = juridique.prompt_arbitrage(
        objet, contexte=contexte,
        extraits="\n\n".join(extraits) if extraits else None,
        profil=profil, dossier=dossier, textes_ids=textes_ids)
    try:
        texte, used = assistant.generate(model, juridique.SYSTEM_ARBITRAGE, user,
                                         max_tokens=4000)
    except assistant.AssistantError as exc:
        return jsonify(ok=False, error=exc.code,
                       message=_JURIDIQUE_ERREURS.get(
                           exc.code, "Note indisponible pour le moment.")), exc.status

    res = juridique.post_traiter(texte, textes_ids)
    audit.journaliser("juridique.arbitrage", cible=used,
                      detail="%d pièce(s), %d décideur(s), %d échéance(s), "
                             "%d référence(s) suspecte(s) ; minimisation : %s"
                             % (len(pieces), len(routage["decisions"]),
                                len(routage["echeances"]),
                                len(res["citations"]["suspectes"]), resume_min),
                      ok=not res["citations"]["suspectes"])
    return jsonify(ok=True, model=used, pieces=pieces, routage=routage, **res)


@app.route("/api/juridique/export", methods=["POST"])
@login_required
def api_juridique_export():
    """Exporte une production juridique en Word ou PDF, prête à diffuser.

    Le document remis au comité doit porter le routage et les échéances : à
    l'écran on les affiche à part pour distinguer ce qui est déduit d'un texte
    de ce qui est rédigé par un modèle, mais dans un document qui circule, une
    note privée du tableau « qui tranche, avant quand » perd exactement ce qui
    la rendait actionnable.

    Les parties déterministes sont RECALCULÉES ici, jamais reprises de ce que le
    navigateur renvoie : un document qui sort de l'entreprise et porte une
    répartition des rôles ne doit pas dépendre de ce qu'un formulaire a bien
    voulu transmettre.
    """
    data = request.get_json(silent=True) or {}
    texte = (data.get("texte") or "").strip()
    if not texte:
        return jsonify(ok=False, error="vide",
                       message="Aucun contenu à exporter."), 400
    type_doc = (data.get("type") or "analyse").strip()
    if type_doc not in juridique.TYPES_DOCUMENT:
        type_doc = "analyse"
    fmt = (data.get("format") or "docx").strip().lower()
    if fmt not in ("docx", "pdf"):
        fmt = "docx"
    objet = (data.get("objet") or "").strip()[:300]
    profil = data.get("profil") if isinstance(data.get("profil"), dict) else None
    dossier = data.get("dossier") if isinstance(data.get("dossier"), dict) else {}
    if objet:
        dossier.setdefault("objet", objet)
    pieces = [p for p in (data.get("pieces") or []) if isinstance(p, dict)][:40]

    routage = qual = None
    if type_doc == "arbitrage":
        routage = juridique.router(profil, dossier)
        qual = routage["qualification"]
    elif profil:
        qual = juridique.qualifier(profil)

    md = juridique.document_markdown(
        type_doc, texte, objet=objet, routage=routage, qualification=qual,
        pieces=pieces, citations=juridique.verifier_citations(texte),
        modele=str(data.get("model") or "")[:40], date=time.strftime("%d/%m/%Y"))
    meta = {"label": juridique.TYPES_DOCUMENT[type_doc]["titre"],
            "client": str(data.get("client") or "")[:120],
            "perimetre": objet, "model": str(data.get("model") or "")[:40],
            "date": time.strftime("%d/%m/%Y"),
            "sources": [{"title": p.get("titre"), "theme": p.get("origine")}
                        for p in pieces]}
    try:
        if fmt == "pdf":
            blob = livrables_export.build_pdf(md, meta)
            mimetype = "application/pdf"
        else:
            blob = livrables_export.build_docx(md, meta)
            mimetype = ("application/vnd.openxmlformats-officedocument"
                        ".wordprocessingml.document")
    except Exception:
        app.logger.exception("export juridique")
        return jsonify(ok=False, error="export_echec",
                       message="La mise en page a échoué."), 500
    audit.journaliser("juridique.export", cible=type_doc,
                      detail="%s · %d caractères · %d pièce(s)"
                             % (fmt, len(texte), len(pieces)))
    return send_file(io.BytesIO(blob),
                     download_name=juridique.nom_fichier(type_doc, objet) + "." + fmt,
                     as_attachment=True, mimetype=mimetype)


@app.route("/api/juridique/dossier-documents")
@login_required
def api_juridique_dossier_documents():
    """Documents versables à un dossier d'arbitrage.

    Périmètre lié à l'identité, comme partout : un client connecté ne voit que
    les documents publics, l'administrateur voit aussi les documents internes.
    On ne renvoie que ce qui sert à choisir — jamais le contenu.
    """
    interne = _is_admin_request()
    try:
        docs = rag.list_documents()
    except Exception:
        return jsonify(ok=False, error="base_indisponible",
                       message="Base de connaissance momentanément indisponible."), 503
    out = [{"id": d["id"], "title": d.get("title"), "theme": d.get("theme"),
            "visibility": d.get("visibility"), "bytes": d.get("bytes"),
            "status": d.get("status")}
           for d in docs
           if d.get("status") == "ready"
           and (interne or d.get("visibility") != "internal")]
    return jsonify(ok=True, documents=out, interne=interne)


@app.route("/api/juridique/instances")
@login_required
def api_juridique_instances():
    """Catalogue des instances et des natures de dossier, pour l'interface."""
    return jsonify(ok=True, instances=juridique.INSTANCES,
                   natures=[{"v": v, "l": l} for v, l in juridique.NATURES_DOSSIER],
                   delais=juridique.DELAIS,
                   suggestions=juridique.SUGGESTIONS_ARBITRAGE)


def _json_champ(valeur):
    """Champ JSON transmis dans un formulaire multipart, ou None."""
    if not valeur:
        return None
    try:
        v = json.loads(valeur)
        return v if isinstance(v, (dict, list)) else None
    except Exception:
        return None


# ============================================================================
#  Relecture contractuelle assistée — playbook, écarts, validations
# ============================================================================
# La différence avec /api/juridique/contrat, qui reste en place : là-bas un
# modèle LIT le contrat et rend un avis ; ici un moteur de règles rend le
# VERDICT, et le modèle n'intervient qu'ensuite, pour expliquer et rédiger.
#
# Cette séparation n'est pas une préférence d'architecture, c'est ce qui rend
# l'outil utilisable en négociation : le juriste qui relit la version 5 doit
# obtenir exactement le même verdict que sur la version 4 pour les clauses qui
# n'ont pas bougé. Un modèle ne garantit pas cela ; une règle écrite, si.
#
# Conséquence utile : l'analyse, la comparaison de versions et le circuit de
# validation fonctionnent SANS clé d'API. Seul le chat en a besoin.
#
# Le contrat n'est jamais conservé. Il est analysé en mémoire et repart avec la
# réponse ; le chat le renvoie à chaque tour, ce qui coûte quelques millisecondes
# de recalcul et évite à la fois de le stocker et de croire un verdict fabriqué
# côté navigateur.

_PLAYBOOK_ERREURS = dict(_JURIDIQUE_ERREURS)
_PLAYBOOK_ERREURS["timeout"] = ("Le modèle a dépassé le délai. Reposez la question "
                                "sur un thème précis : la réponse sera plus rapide.")


def _texte_soumis(champ_fichier, champ_texte, mini=200):
    """Le texte d'une version : collé, ou extrait d'un fichier déposé.

    Renvoie (texte, refus, depuis_fichier). `depuis_fichier` compte : quand le
    texte vient d'un PDF, le navigateur ne l'a PAS — il faut le lui rendre, sinon
    le chat n'a plus de contrat à commenter et l'export n'a plus rien à
    recalculer.
    """
    f = request.files.get(champ_fichier)
    depuis_fichier = f is not None
    if f is not None:
        nom = (f.filename or "").lower()
        ext = nom.rsplit(".", 1)[-1] if "." in nom else ""
        if ext not in ("pdf", "docx", "txt", "md"):
            return None, (jsonify(ok=False, error="format_refuse",
                                  message="Formats acceptés : PDF, DOCX, TXT, MD."), 400), False
        blob = f.read(6 * 1024 * 1024 + 1)
        if len(blob) > 6 * 1024 * 1024:
            return None, (jsonify(ok=False, error="trop_gros",
                                  message="Fichier trop volumineux (6 Mo maximum)."), 400), False
        try:
            texte = rag_extract_text(ext, blob) or ""
        except Exception:
            texte = ""
        if not texte.strip():
            return None, (jsonify(ok=False, error="illisible",
                                  message="Aucun texte n'a pu être extrait de ce fichier "
                                          "(document scanné ?). Collez le texte à la place."),
                          400), False
    else:
        # `_corps()` et non `request.get_json` : une comparaison peut arriver en
        # multipart (fichier pour la version d'avant, texte collé pour celle
        # d'après). Lire le JSON d'une requête multipart renvoie None, et la
        # version collée disparaissait en silence.
        texte = str(_corps().get(champ_texte) or "")
    if len(texte.strip()) < mini:
        return None, (jsonify(ok=False, error="version_vide",
                              message="Fournissez le texte de la version "
                                      "(%d caractères minimum)." % mini), 400), depuis_fichier
    return texte, None, depuis_fichier


def _corps():
    """Champs du corps, que la requête soit en JSON ou en multipart."""
    if request.files:
        return {k: v for k, v in request.form.items()}
    return request.get_json(silent=True) or {}


def _domaines_demandes(corps):
    d = corps.get("domaines")
    if isinstance(d, str):
        d = _json_champ(d)
    if not isinstance(d, list):
        return None
    valides = [x for x in d if x in juridique.DOMAINES_CLAUSIER]
    return valides or None


@app.route("/relecture-contrat")
@login_required
def relecture_contrat_page():
    """Relecture assistée d'un contrat, version par version."""
    return _page(PAGES["/relecture-contrat"])


@app.route("/api/playbook/config")
@login_required
def api_playbook_config():
    """Le playbook lui-même : ce que l'entreprise accepte, jusqu'où, et qui tranche."""
    dispo = assistant.available()
    return jsonify(ok=True,
                   version=playbook.VERSION_PLAYBOOK,
                   version_referentiel=juridique.VERSION_REFERENTIEL,
                   themes=playbook.themes(),
                   niveaux=playbook.niveaux(),
                   domaines=playbook.domaines(),
                   instances=juridique.INSTANCES,
                   suggestions=playbook.SUGGESTIONS,
                   models=dispo,
                   # `any(...)` et non `bool(dispo)` : available() renvoie un
                   # dictionnaire {claude: False, mistral: False}, et un
                   # dictionnaire non vide est vrai. L'interface aurait donc
                   # annoncé un chat disponible sur une instance sans aucune clé,
                   # et l'utilisateur aurait découvert la panne en posant sa
                   # première question.
                   chat_disponible=any(dispo.values()),
                   avertissement=juridique.AVERTISSEMENT,
                   mention_ia=juridique.MENTION_IA,
                   sante=playbook.sante())


@app.route("/api/playbook/analyse", methods=["POST"])
@login_required
def api_playbook_analyse():
    """Verdict déterministe d'une version. Aucun modèle n'est appelé ici."""
    ckey = "pbana:%s" % client_ip()
    if guard.blocked(ckey, limit=40, window=600):
        return jsonify(ok=False, error="rate_limited",
                       message="Trop d'analyses en peu de temps. Patientez un instant."), 429
    guard.fail(ckey)

    texte, refus, depuis_fichier = _texte_soumis("fichier", "texte")
    if refus:
        return refus
    corps = _corps()
    (texte,), refus_min, resume_min = _minimiser([texte], corps.get("minimisation") or "")
    if refus_min:
        return refus_min

    res = playbook.analyser(texte, domaines_retenus=_domaines_demandes(corps))
    ci = playbook.circuit(res)
    audit.journaliser("playbook.analyse", cible=playbook.VERSION_PLAYBOOK,
                      detail="%d caractères, %d thèmes, %d ligne(s) rouge(s), "
                             "%d point(s) à valider ; minimisation : %s"
                             % (len(texte), len(res["themes"]),
                                res["compte"]["ligne-rouge"], ci["n_points"], resume_min),
                      ok=not res["bloquants"])
    # Le texte RÉELLEMENT analysé revient au navigateur dans deux cas : quand le
    # caviardage l'a modifié (le tour suivant renverrait sinon l'original en
    # clair), et quand il vient d'un fichier (le navigateur ne l'a jamais eu, et
    # sans lui le chat n'aurait aucun contrat à commenter). C'est le texte de
    # l'utilisateur qui lui revient : il n'a jamais été stocké nulle part.
    rendre = depuis_fichier or (corps.get("minimisation") or "") == "masquer"
    return jsonify(ok=True, analyse=res, circuit=ci,
                   texte_retenu=texte if rendre else None)


@app.route("/api/playbook/comparer", methods=["POST"])
@login_required
def api_playbook_comparer():
    """Ce qui a bougé entre deux versions — la question de la négociation."""
    ckey = "pbcmp:%s" % client_ip()
    if guard.blocked(ckey, limit=30, window=600):
        return jsonify(ok=False, error="rate_limited",
                       message="Trop de comparaisons en peu de temps. Patientez un instant."), 429
    guard.fail(ckey)

    avant, refus, _f1 = _texte_soumis("fichier_avant", "avant")
    if refus:
        return refus
    apres, refus, _f2 = _texte_soumis("fichier_apres", "apres")
    if refus:
        return refus
    corps = _corps()
    (avant, apres), refus_min, resume_min = _minimiser(
        [avant, apres], corps.get("minimisation") or "")
    if refus_min:
        return refus_min

    cmp_ = playbook.comparer(avant, apres, domaines_retenus=_domaines_demandes(corps))
    ci = playbook.circuit(cmp_["apres"])
    audit.journaliser("playbook.comparer", cible=playbook.VERSION_PLAYBOOK,
                      detail="%d recul(s), %d progrès, %d inchangé(s) ; minimisation : %s"
                             % (cmp_["n_recul"], cmp_["n_progres"],
                                cmp_["n_inchange"], resume_min),
                      ok=cmp_["n_recul"] == 0)
    return jsonify(ok=True, comparaison=cmp_, circuit=ci)


@app.route("/api/playbook/chat", methods=["POST"])
@login_required
def api_playbook_chat():
    """L'assistant de relecture. Il reçoit les verdicts comme des faits.

    L'analyse est REFAITE ici à partir du texte transmis : c'est ce qui garantit
    que le contexte remis au modèle correspond à un vrai passage du moteur, et
    non à un objet JSON qu'un navigateur aurait pu forger. Cela coûte quelques
    millisecondes et retire une confiance mal placée.
    """
    ckey = "pbchat:%s" % client_ip()
    if guard.blocked(ckey, limit=25, window=600):
        return jsonify(ok=False, error="rate_limited",
                       message="Trop de messages en peu de temps. Patientez un instant."), 429
    guard.fail(ckey)

    data = request.get_json(silent=True) or {}
    model = "mistral" if data.get("model") == "mistral" else "claude"
    messages = data.get("messages")
    texte = str(data.get("texte") or "")
    focus = str(data.get("theme") or "").strip() or None
    if focus not in {c["id"] for c in juridique.CLAUSIER}:
        focus = None

    dernier = ""
    try:
        dernier = assistant.last_user_message(messages) or ""
    except Exception:
        dernier = ""
    if not dernier.strip():
        return jsonify(ok=False, error="empty", message="Votre message est vide."), 400
    (dernier,), refus, _r = _minimiser([dernier], data.get("minimisation") or "")
    if refus:
        return refus
    if isinstance(messages, list):
        for m in reversed(messages):
            if isinstance(m, dict) and m.get("role") == "user":
                m["content"] = dernier
                break

    analyse = playbook.analyser(texte, domaines_retenus=_domaines_demandes(data)) \
        if len(texte.strip()) >= 200 else None

    # La base de connaissance interne complète le playbook : positions déjà
    # négociées, notes de doctrine, décisions du comité. Best-effort — une
    # récupération en échec ne doit pas priver le relecteur de sa réponse.
    extraits = None
    try:
        extraits = build_context(rag.search(dernier, k=4,
                                            public_only=not _is_admin_request()))
    except Exception:
        extraits = None

    contexte = playbook.contexte_chat(analyse, focus=focus, extraits=extraits)
    try:
        reply, used = assistant.answer(model, messages, context=contexte)
    except assistant.AssistantError as exc:
        return jsonify(ok=False, error=exc.code,
                       message=_PLAYBOOK_ERREURS.get(
                           exc.code, "Assistant indisponible pour le moment.")), exc.status

    # Même garde-fou que sur l'analyse juridique : un modèle qui cite un texte
    # inexistant produit une réponse crédible et fausse. Le contrôle est
    # déterministe et ne coûte rien.
    ctrl = juridique.verifier_citations(reply)
    audit.journaliser("playbook.chat", cible=used,
                      detail="thème %s · %d thème(s) en contexte · %d référence(s) suspecte(s)"
                             % (focus or "—", len(analyse["themes"]) if analyse else 0,
                                len(ctrl["suspectes"])),
                      ok=not ctrl["suspectes"])
    return jsonify(ok=True, reply=reply, model=used, citations=ctrl,
                   ancre=bool(analyse),
                   envoye=dernier if (data.get("minimisation") or "") == "masquer" else None)


@app.route("/api/playbook/export", methods=["POST"])
@login_required
def api_playbook_export():
    """La note de relecture, en Word ou en PDF.

    Les verdicts sont RECALCULÉS depuis le texte, jamais repris du navigateur :
    une note qui circule en interne et fonde une décision d'engagement ne doit
    pas dépendre de ce qu'un formulaire a bien voulu transmettre.
    """
    data = request.get_json(silent=True) or {}
    texte = str(data.get("texte") or "")
    if len(texte.strip()) < 200:
        return jsonify(ok=False, error="version_vide",
                       message="Aucune version à documenter."), 400
    fmt = (data.get("format") or "docx").strip().lower()
    if fmt not in ("docx", "pdf"):
        fmt = "docx"
    objet = str(data.get("objet") or "").strip()[:300]
    domaines = _domaines_demandes(data)

    analyse = playbook.analyser(texte, domaines_retenus=domaines)
    ci = playbook.circuit(analyse)
    comparaison = None
    precedent = str(data.get("precedent") or "")
    if len(precedent.strip()) >= 200:
        comparaison = playbook.comparer(precedent, texte, domaines_retenus=domaines)
    echange = [m for m in (data.get("echange") or []) if isinstance(m, dict)][:24]

    md = playbook.note_markdown(analyse, objet=objet, circuit_=ci,
                                comparaison=comparaison, echange=echange)
    meta = {"label": "Note de relecture contractuelle",
            "client": str(data.get("client") or "")[:120],
            "perimetre": objet or "contrat de services numériques",
            "model": str(data.get("model") or "")[:40],
            "date": time.strftime("%d/%m/%Y"),
            "sources": [{"title": "Playbook contractuel v" + playbook.VERSION_PLAYBOOK,
                         "theme": "référentiel interne"}]}
    try:
        if fmt == "pdf":
            blob = livrables_export.build_pdf(md, meta)
            mimetype = "application/pdf"
        else:
            blob = livrables_export.build_docx(md, meta)
            mimetype = ("application/vnd.openxmlformats-officedocument"
                        ".wordprocessingml.document")
    except Exception:
        app.logger.exception("export relecture")
        return jsonify(ok=False, error="export_echec",
                       message="La mise en page a échoué."), 500

    import re as _re
    base = _re.sub(r"[^A-Za-z0-9]+", "-", (objet or "relecture")).strip("-").lower()[:60]
    audit.journaliser("playbook.export", cible=fmt,
                      detail="%d thèmes · %d ligne(s) rouge(s) · %d point(s) à valider"
                             % (len(analyse["themes"]), analyse["compte"]["ligne-rouge"],
                                ci["n_points"]))
    return send_file(io.BytesIO(blob),
                     download_name="note-relecture-%s.%s" % (base or "contrat", fmt),
                     as_attachment=True, mimetype=mimetype)


# ══════════════════════════════════════════════════════════════════════════
#  CENTRES DE DONNÉES BAS CARBONE — moteur d'ingénierie
#
#  Même partage des rôles que la relecture contractuelle : le MOTEUR calcule,
#  le modèle rédige autour. Ici l'enjeu est plus dur encore — une note de calcul
#  se fait vérifier ligne à ligne par un bureau de contrôle, et un chiffre
#  inventé y est repéré immédiatement. datacenter.py ne contient aucun appel à
#  un modèle de langage : l'étude complète fonctionne sans aucune clé d'API.
# ══════════════════════════════════════════════════════════════════════════

import datacenter    # noqa: E402
import profil_dc     # noqa: E402  — analyse le moteur ci-dessus, ne le double pas
import ingenierie_dc  # noqa: E402  — situe ses résultats dans la séquence projet


@app.route("/datacenter")
@login_required
def datacenter_page():
    """Études d'ingénierie de centres de données (comptes connectés)."""
    return _page(PAGES["/datacenter"])


@app.route("/ingenierie-datacenter")
@login_required
def ingenierie_datacenter_page():
    """Le même calcul, replacé dans la séquence projet — MOE et ingénierie."""
    return _page(PAGES["/ingenierie-datacenter"])


@app.route("/api/datacenter/referentiel")
@login_required
def api_datacenter_referentiel():
    """Vocabulaire, constantes et cadre réglementaire.

    Une seule définition côté serveur : une liste d'options recopiée dans le
    HTML finit toujours par diverger du moteur qui, lui, calcule."""
    return jsonify(ok=True, referentiel=datacenter.referentiel(),
                   champs=datacenter.CHAMPS)


def _profil_datacenter(data):
    """Nettoie les entrées. Les nombres reçus en texte sont convertis ici, une
    fois pour toutes : plus bas, une chaîne dans un calcul lève, et l'étude
    entière échouerait sur une virgule décimale."""
    profil = {}
    for champ in datacenter.CHAMPS:
        cid = champ["id"]
        if cid not in data or data[cid] in ("", None):
            continue
        brut = data[cid]
        if champ["type"] == "nombre":
            try:
                profil[cid] = float(str(brut).replace(",", ".").strip())
            except (TypeError, ValueError):
                continue
        else:
            profil[cid] = str(brut).strip()[:40]
    return profil


@app.route("/api/datacenter/etude", methods=["POST"])
@login_required
def api_datacenter_etude():
    """L'étude complète. Déterministe : deux appels identiques, même résultat."""
    data = request.get_json(silent=True) or {}
    profil = _profil_datacenter(data)
    if not profil.get("puissance_it_kw"):
        return jsonify(ok=False, error="puissance_absente",
                       message="La puissance informatique installée est nécessaire : "
                               "toutes les grandeurs en dépendent."), 400
    if profil["puissance_it_kw"] <= 0 or profil["puissance_it_kw"] > 5_000_000:
        return jsonify(ok=False, error="puissance_invraisemblable",
                       message="Puissance hors du domaine du calculable."), 400
    try:
        res = datacenter.etude(profil)
    except Exception:
        app.logger.exception("étude datacenter")
        return jsonify(ok=False, error="calcul_echec",
                       message="Le calcul a échoué."), 500
    audit.journaliser("datacenter.etude",
                      cible=str(profil.get("refroidissement") or "?"),
                      detail="%s kW · PUE %s · WUE site %s"
                             % (profil["puissance_it_kw"],
                                res["energie"]["pue"]["valeur"],
                                res["eau"]["wue_site"]["valeur"]))
    return jsonify(ok=True, etude=res)


@app.route("/api/datacenter/profil", methods=["POST"])
@login_required
def api_datacenter_profil():
    """Ce que le profil laisse encore ouvert, AVANT de lancer l'étude.

    L'étape 1 promet que « renseigner davantage resserre les incertitudes ».
    Cette route la vérifie plutôt que de la faire croire : elle rejoue l'étude
    en balayant le domaine de chaque champ vide et mesure ce qui reste
    indéterminé. Le coût est celui d'une centaine d'appels au moteur, soit
    quelques millisecondes — il n'y a pas d'entrée/sortie derrière.
    """
    data = request.get_json(silent=True) or {}
    profil = _profil_datacenter(data)
    if not profil.get("puissance_it_kw"):
        return jsonify(ok=False, error="puissance_absente",
                       message="La puissance informatique installée est nécessaire."), 400
    try:
        return jsonify(ok=True, apercu=profil_dc.apercu(profil))
    except Exception:
        app.logger.exception("aperçu profil datacenter")
        return jsonify(ok=False, error="calcul",
                       message="L'aperçu du profil n'a pas pu être établi."), 500


@app.route("/api/datacenter/comparer", methods=["POST"])
@login_required
def api_datacenter_comparer():
    """La même installation, toutes familles de refroidissement confondues.

    C'est ce tableau qui rend l'arbitrage lisible : on y voit d'un coup que le
    gain de PUE d'un évaporatif se paie en mètres cubes, et que le rejet sec
    fait l'inverse. Séparés, les deux chiffres laissent conclure à côté.
    """
    data = request.get_json(silent=True) or {}
    profil = _profil_datacenter(data)
    if not profil.get("puissance_it_kw"):
        return jsonify(ok=False, error="puissance_absente",
                       message="La puissance informatique installée est nécessaire."), 400
    lignes = []
    for famille in datacenter.REFROIDISSEMENT:
        p = dict(profil)
        p["refroidissement"] = famille
        p.pop("pue_cible", None)          # sinon toutes les familles se valent
        p.pop("part_evaporative", None)   # on veut la valeur propre à chacune
        r = datacenter.etude(p)
        lignes.append({
            "famille": famille,
            "nom": datacenter.REFROIDISSEMENT[famille]["nom"],
            "pue": r["energie"]["pue"]["valeur"],
            "energie_totale_MWh": r["energie"]["energie_totale_MWh"]["valeur"],
            "eau_site_m3": r["eau"]["appoint_m3"]["valeur"],
            "wue_site": r["eau"]["wue_site"]["valeur"],
            "wue_source": r["eau"]["wue_source"]["valeur"],
            "co2_exploitation_t": r["carbone"]["co2_exploitation_localise_t"]["valeur"],
            "empreinte_totale_t": r["carbone"]["empreinte_totale_t"]["valeur"],
            "temperature_rejet_c": r["chaleur"]["temperature_rejet_c"],
            "note": datacenter.REFROIDISSEMENT[famille]["note"],
        })
    lignes.sort(key=lambda x: x["empreinte_totale_t"])
    return jsonify(ok=True, lignes=lignes,
                   lecture="Classement par empreinte totale, carbone incorporé compris. "
                           "Le WUE de SOURCE, et non le WUE de site, est la colonne à "
                           "regarder pour arbitrer entre évaporatif et rejet sec.")


@app.route("/api/datacenter/ingenierie")
@login_required
def api_datacenter_ingenierie():
    """Le cadre de phases : deux filières, leurs correspondances, et les postes
    du référentiel dont l'ordre de grandeur cesse de suffire en cours de projet."""
    return jsonify(ok=True, referentiel=ingenierie_dc.referentiel())


@app.route("/api/datacenter/ingenierie/parcours", methods=["POST"])
@login_required
def api_datacenter_ingenierie_parcours():
    """Où l'on passe et où l'on bute, sur toute une filière.

    Le premier point de blocage est la seule information qui commande une
    action : les phases suivantes servent à voir venir, pas à travailler en
    parallèle.
    """
    data = request.get_json(silent=True) or {}
    profil = _profil_datacenter(data)
    if not profil.get("puissance_it_kw"):
        return jsonify(ok=False, error="puissance_absente",
                       message="La puissance informatique installée est nécessaire."), 400
    fil = (data.get("filiere") or "").strip()
    filieres = [fil] if fil in ingenierie_dc.FILIERES else list(ingenierie_dc.FILIERES)
    try:
        return jsonify(ok=True,
                       parcours={f: ingenierie_dc.parcours(profil, f) for f in filieres},
                       correspondances=ingenierie_dc.CORRESPONDANCES)
    except Exception:
        app.logger.exception("parcours ingénierie datacenter")
        return jsonify(ok=False, error="calcul",
                       message="Le parcours n'a pas pu être établi."), 500


@app.route("/api/datacenter/ingenierie/dossier", methods=["POST"])
@login_required
def api_datacenter_ingenierie_dossier():
    """Le plan de l'étude pour une phase, avec ce que le moteur y verse
    légitimement et ce qui reste à produire ailleurs."""
    data = request.get_json(silent=True) or {}
    profil = _profil_datacenter(data)
    code = str(data.get("phase") or "").strip().upper()[:12]
    try:
        d = ingenierie_dc.dossier(profil, code)
    except Exception:
        app.logger.exception("dossier ingénierie datacenter")
        return jsonify(ok=False, error="calcul",
                       message="Le dossier n'a pas pu être établi."), 500
    if not d.get("connu"):
        return jsonify(ok=False, error="phase_inconnue",
                       message=d.get("motif", "Phase inconnue.")), 404
    return jsonify(ok=True, dossier=d)


@app.route("/api/datacenter/ingenierie/export", methods=["POST"])
@login_required
def api_datacenter_ingenierie_export():
    """L'étude de phase en Word ou PDF.

    Le document porte les valeurs du moteur là où la phase les admet, et la
    mention « À PRODUIRE » là où elle ne les admet plus. C'est cette distinction
    qui fait la différence entre un sommaire et un plan de travail : sans elle,
    un chiffre provisoire traverse tout le projet sans que personne ne le
    remplace.
    """
    data = request.get_json(silent=True) or {}
    profil = _profil_datacenter(data)
    code = str(data.get("phase") or "").strip().upper()[:12]
    if not profil.get("puissance_it_kw"):
        return jsonify(ok=False, error="puissance_absente",
                       message="La puissance informatique installée est nécessaire."), 400
    d = ingenierie_dc.dossier(profil, code)
    if not d.get("connu"):
        return jsonify(ok=False, error="phase_inconnue",
                       message=d.get("motif", "Phase inconnue.")), 404
    fmt = (data.get("format") or "docx").strip().lower()
    if fmt not in ("docx", "pdf"):
        fmt = "docx"
    md = _etude_phase_markdown(d, str(data.get("client") or "").strip()[:120])
    meta = {"label": "%s — %s" % (d["code"], d["nom"]),
            "client": str(data.get("client") or "")[:120],
            "perimetre": "%s kW informatiques · %s" % (
                round(profil["puissance_it_kw"]), d["filiere_nom"]),
            "date": time.strftime("%d/%m/%Y"),
            "sources": [{"title": "Moteur d'ingénierie CONSEILPREV v" + datacenter.VERSION,
                         "theme": "calcul déterministe"},
                        {"title": "Cadre de phases v" + ingenierie_dc.VERSION,
                         "theme": ingenierie_dc.FILIERES[d["filiere"]]["cadre"]}]}
    try:
        if fmt == "pdf":
            blob = livrables_export.build_pdf(md, meta)
            mimetype = "application/pdf"
        else:
            blob = livrables_export.build_docx(md, meta)
            mimetype = ("application/vnd.openxmlformats-officedocument"
                        ".wordprocessingml.document")
    except Exception:
        app.logger.exception("export étude de phase")
        return jsonify(ok=False, error="export_echec",
                       message="La mise en page a échoué."), 500
    audit.journaliser("datacenter.ingenierie.export", cible=d["code"],
                      detail="%s · %s" % (fmt, d["filiere"]))
    return send_file(io.BytesIO(blob),
                     download_name="etude-%s.%s" % (d["code"].lower(), fmt),
                     as_attachment=True, mimetype=mimetype)


# Le registre en ligne, adressable phase par phase et pièce par pièce. Un
# livrable qui écrit « repris en APD » sans dire où le lire oblige le lecteur à
# retrouver la filière, la phase et la ligne : autant ne pas l'écrire.
BASE_INGENIERIE = "https://conseilprevcyber.onrender.com/ingenierie-datacenter"


def _lien_piece(code_phase, code_piece=None):
    u = "%s#phase=%s" % (BASE_INGENIERIE, code_phase)
    return u + ("&piece=%s" % code_piece if code_piece else "")


def _ameliorations(d):
    """Ce qui améliorerait CE livrable, déduit de ce qui lui manque.

    Calculé, pas rédigé : une liste de conseils écrite une fois pour toutes
    dirait la même chose d'une esquisse et d'un dossier de consultation, alors
    que ce qui manque n'y est pas du tout de même nature. Chaque proposition
    nomme le geste, ce qu'il apporte, et se range par effet décroissant.
    """
    props = []
    # 1. Les entrées ouvertes, par effet mesuré sur les grandeurs.
    pires = {}
    for g in d.get("grandeurs") or []:
        o = g.get("entrees_ouvertes") or {}
        for c in o.get("champs", []):
            pct = c.get("etendue_pct") or 0
            if pct > (pires.get(c["id"], (0, None, None))[0]):
                pires[c["id"]] = (pct, c["label"], g["nom"])
    for pct, label, sur in sorted(pires.values(), reverse=True):
        props.append({
            "poids": pct,
            "geste": "Renseigner « %s »" % label,
            "gain": "Resserre « %s », dont %s %% d'étendue subsistent du seul "
                    "fait de ce champ." % (sur, datacenter.fr(pct)),
        })
    # 2. Les substitutions dues à cette phase : elles ne resserrent pas une
    #    fourchette, elles débloquent une grandeur — effet différent, et qu'on
    #    ne peut donc pas comparer en pourcentage. Rang fixe au-dessus du reste.
    for s in d["aptitude"].get("substitutions_a_faire") or []:
        props.append({
            "poids": 1000,
            "geste": "Remplacer « %s » par une donnée réelle" % s["nom"],
            "gain": "Débloque les grandeurs qui en dépendent. %s"
                    % (s.get("remplacer_par") or ""),
        })
    props.sort(key=lambda p: -p["poids"])
    # 3. Les entrées dont l'effet n'est PAS chiffré ici — un pays, une famille
    #    de refroidissement ne se balaient pas sur un intervalle. Elles font
    #    groupe à part au lieu de finir en bas d'un classement par effet : le
    #    pays commande l'intensité carbone et le facteur eau, et le ranger
    #    dernier le ferait passer pour négligeable. Un classement qui mélange
    #    le mesuré et le non mesuré ment sur le non mesuré.
    deja = {p["geste"] for p in props}
    non_chiffres = []
    for m in d["aptitude"].get("entrees_manquantes") or []:
        g = "Renseigner « %s »" % m["label"]
        if g in deja:
            continue
        non_chiffres.append({
            "geste": g,
            "gain": "Exigée pour franchir la phase ; état actuel : %s. Son effet "
                    "n'est pas chiffrable par balayage — c'est un choix, pas un "
                    "réglage." % (m.get("pourquoi") or "non renseignée"),
        })
    return props, non_chiffres


def _etude_phase_markdown(d, client=""):
    """L'étude de phase en Markdown.

    Écrite ici plutôt que par le modèle : ce document dit ce qui est acquis et
    ce qui ne l'est pas, et cette frontière-là ne se rédige pas, elle se
    calcule. Le modèle pourra développer chaque section ensuite — il reçoit
    alors ce plan comme un ensemble de faits qu'il n'a pas le droit de
    contredire.
    """
    L = []
    A = L.append
    A("# Étude %s — %s" % (d["code"], d["nom"]))
    A("")
    A("*%s*" % d["filiere_nom"])
    if client:
        A("")
        A("**Client** — %s" % client)
    A("")

    # ── Sommaire ────────────────────────────────────────────────────────
    # Dérivé du contenu réel, pas écrit à la main : un sommaire recopié
    # survit à la suppression du chapitre qu'il annonce, et le lecteur
    # cherche une page qui n'existe plus. Les chapitres conditionnels
    # (registre, améliorations) n'y figurent que s'ils sont produits.
    pcs_ = d.get("pieces") or []
    ap_ = d["aptitude"]
    recevables_ = [g for g in d["grandeurs"] if g["statut"] == "recevable"]
    a_remp_ = [g for g in d["grandeurs"] if g["statut"] != "recevable"]
    plan = [("1. Objet et position dans la séquence", [])]
    sc2 = []
    if recevables_:
        sc2.append("Grandeurs recevables à ce stade")
    if a_remp_:
        sc2.append("Grandeurs NON recevables en l'état — à produire")
    sc2.append("Ce qui reste ouvert par les entrées non renseignées")
    plan.append(("2. Ce que le moteur verse à ce dossier", sc2))
    sc3 = []
    if ap_["entrees_manquantes"]:
        sc3.append("Entrées à renseigner")
    if ap_["substitutions_a_faire"]:
        sc3.append("Facteurs à remplacer par une donnée réelle")
    plan.append(("3. Ce qui manque pour franchir la phase", sc3))
    plan.append(("4. Plan de l'étude", []))
    if pcs_:
        plan.append(("5. Registre des pièces à fournir",
                     ["Tableau récapitulatif", "Contenu exigé de chaque pièce"]))
    n_ = 6 if pcs_ else 5
    plan.append(("%d. Améliorer et optimiser ce livrable" % n_,
                 ["Ce qui resserrerait le plus les fourchettes",
                  "Ce qui reste à développer et à corriger"]))
    plan.append(("%d. Traçabilité" % (n_ + 1), []))
    A("## Sommaire")
    A("")
    for titre, sous in plan:
        A("- **%s**" % titre)
        for s in sous:
            A("    - %s" % s)
    A("")
    A("---")
    A("")
    A("## 1. Objet et position dans la séquence")
    A("")
    A(d["objet"])
    A("")
    A("- **Ce que cette phase décide** — %s" % d["decide"])
    A("- **Ce qu'elle verrouille** — %s" % d["verrouille"])
    A("- **Précision attendue** — %s (%s ; %s)" % (
        d["precision"]["valeur"], d["precision"]["nature"], d["precision"]["aace"]))
    if d.get("note"):
        A("- **Précision de vocabulaire** — %s" % d["note"])
    for c in d.get("correspondance") or []:
        autre = c["indus"] if d["filiere"] == "moe" else c["moe"]
        A("- **Correspondance dans l'autre filière** — %s (accord %s). %s"
          % (autre, c["accord"], c["ecart"]))
    A("")
    A("---")
    A("")

    A("## 2. Ce que le moteur verse à ce dossier")
    A("")
    A(d["apport_texte"])
    A("")
    recevables = recevables_
    a_remp = a_remp_

    def _ligne_grandeur(g, indicative=False):
        """Une grandeur, son incertitude de moteur ET son étendue résiduelle.

        Les deux ensemble, jamais l'une sans l'autre : l'incertitude publiée
        par le moteur ne couvre que la dispersion de ses propres facteurs. Ne
        montrer qu'elle laissait lire « énergie annuelle, ±7,4 % » sur un
        chiffre que le seul taux de charge, non renseigné, déplace de 58 %.
        """
        base = "- **%s** — %s%s %s" % (
            g["nom"], "valeur indicative " if indicative else "",
            datacenter.fr(g["valeur"]), g["unite"])
        if g["incertitude"]:
            base += " (%s)" % g["incertitude"]
        return base

    if recevables:
        A("### Grandeurs recevables à ce stade")
        A("")
        A("« Recevable » signifie que le niveau de définition correspond à "
          "celui attendu par la phase — **non que la valeur soit arrêtée**.")
        A("")
        for g in recevables:
            A(_ligne_grandeur(g))
        A("")
    if a_remp:
        A("### Grandeurs NON recevables en l'état — à produire")
        A("")
        for g in a_remp:
            A(_ligne_grandeur(g, indicative=True)
              + ". Bloquée par : %s." % ", ".join(g["postes_bloquants"]))
        A("")

    # ── L'étendue que les entrées non renseignées laissent ouverte ───────
    # Le chapitre le plus important du document, et celui qui manquait. Sans
    # lui, l'étude affichait une incertitude quatre fois trop étroite sur un
    # chiffre présenté comme acquis, et listait deux pages plus loin l'entrée
    # qui en décidait.
    ouverts = [(g, g.get("entrees_ouvertes") or {}) for g in d["grandeurs"]]
    ouverts = [(g, o) for g, o in ouverts if o.get("mesuree")]
    zeros = [g for g in d["grandeurs"] if g.get("zero_sans_incertitude")]
    A("### Ce qui reste ouvert par les entrées non renseignées")
    A("")
    if ouverts:
        A("**À lire avant les chiffres ci-dessus.** L'incertitude affichée par "
          "le moteur ne couvre que la dispersion de ses propres facteurs. Les "
          "champs laissés sur leur valeur par défaut en ajoutent une autre, "
          "souvent plus large. Chaque champ est balayé **seul** sur sa plage "
          "plausible, les autres restant en l'état : **les étendues ne "
          "s'additionnent pas**, et le champ le plus lourd est celui à "
          "renseigner en premier.")
        A("")
        A("| Grandeur | Champ non renseigné | Plage balayée | Étendue |")
        A("| --- | --- | --- | --- |")
        for g, o in ouverts:
            for c in o["champs"]:
                etendue = ("**%s %%**" % datacenter.fr(c["etendue_pct"])
                           if c["etendue_pct"] is not None
                           else "**de %s**" % c["etendue_absolue"])
                A("| %s | %s | %s | %s |"
                  % (g["nom"], c["label"], c["plage"], etendue))
        A("")
        pire = max(ouverts, key=lambda x: (x[1].get("dominant_pct") or 0))
        if (pire[1].get("dominant_pct") or 0) > 0:
            A("**Point à corriger en priorité** — renseigner « %s » resserre "
              "« %s », dont l'étendue résiduelle atteint %s %%. C'est le seul "
              "geste qui change l'ordre de grandeur du dossier."
              % (pire[1]["dominant"], pire[0]["nom"],
                 datacenter.fr(pire[1]["dominant_pct"])))
            A("")
    else:
        A("Aucune entrée du moteur n'est restée sur sa valeur par défaut : les "
          "incertitudes affichées ci-dessus sont les seules qui subsistent de "
          "son côté.")
        A("")
    if zeros:
        A("**Grandeurs affichées à zéro, sans incertitude déclarée** — un zéro "
          "nu se lit comme une certitude. Il vient ici du mode retenu, où le "
          "poste ne joue pas ; **à confirmer** avant toute reprise dans une "
          "pièce contractuelle : %s." % ", ".join(g["nom"] for g in zeros))
        A("")

    ap = ap_
    A("---")
    A("")
    A("## 3. Ce qui manque pour franchir la phase")
    A("")
    A(ap["verdict"])
    A("")
    if ap["entrees_manquantes"]:
        A("### Entrées à renseigner")
        A("")
        for m in ap["entrees_manquantes"]:
            A("- **%s**%s — %s%s" % (
                m["label"], (" (%s)" % m["unite"]) if m["unite"] else "",
                m["pourquoi"],
                "" if m["origine"] == "propre" else " ; dette d'une phase antérieure"))
        A("")
    if ap["substitutions_a_faire"]:
        A("### Facteurs à remplacer par une donnée réelle")
        A("")
        for s in ap["substitutions_a_faire"]:
            A("**%s** — %s%s" % (s["nom"], s["nature"],
                                 (", %s" % s["incertitude"]) if s["incertitude"] else ""))
            A("")
            if s.get("devient_insuffisant"):
                A("  Pourquoi à ce stade : %s" % s["devient_insuffisant"])
            A("  À remplacer par : %s" % s["remplacer_par"])
            if s.get("incertitude_absente"):
                A("  Réserve : ce poste ne porte aucune incertitude déclarée au "
                  "référentiel. Une incertitude absente n'est pas une incertitude "
                  "nulle.")
            if s.get("source"):
                A("  Source actuelle : %s" % s["source"])
            A("")
    if not ap["entrees_manquantes"] and not ap["substitutions_a_faire"]:
        A("Rien ne manque du côté du moteur. Les autres disciplines du dossier "
          "restent à produire.")
        A("")

    A("---")
    A("")
    A("## 4. Plan de l'étude")
    A("")
    for i, s in enumerate(d["sections"], 1):
        A("%d. %s" % (i, s))
    A("")
    if d.get("renvoi"):
        rv = d["renvoi"]
        A("**Ce que cette phase attend d'ailleurs** — %s : [%s](%s)."
          % (rv.get("pourquoi", "").rstrip("."), rv.get("quoi", "voir le module"),
             rv.get("url", "")))
        A("")
    A("---")
    A("")

    # Le plan dit ce qu'on écrit ; le registre dit ce qu'on REMET. Une étude de
    # phase qui ne porterait que le plan laisserait le lecteur composer lui-même
    # la liste des pièces — c'est-à-dire en oublier.
    pcs = d.get("pieces") or []
    if pcs:
        r = d.get("resume_pieces") or {}
        A("## 5. Registre des pièces à fournir")
        A("")
        A("%d pièces — %d propres à la phase et %d spécifications de discipline. "
          "%d sont alimentées par le calcul énergie / eau / carbone ; les autres "
          "relèvent d'autres disciplines et figurent pour mémoire."
          % (r.get("total", len(pcs)), r.get("propres_a_la_phase", 0),
             r.get("specifications_de_discipline", 0),
             r.get("alimentees_par_le_moteur", 0)))
        A("")
        A("Chaque code renvoie à sa fiche dans le registre en ligne. Les pièces "
          "reprises d'une phase à l'autre portent, sous leur contenu, le lien "
          "vers **le même document à son indice suivant** — c'est ainsi qu'on "
          "évite d'en produire trois.")
        A("")
        A("| Code | Pièce | Type | Émetteur | Niveau attendu | Calcul |")
        A("| --- | --- | --- | --- | --- | --- |")
        for p in pcs:
            A("| [%s](%s) | %s | %s | %s | %s | %s |"
              % (p["code"], _lien_piece(d["code"], p["code"]), p["titre"],
                 p["type_nom"], p["emetteur_nom"],
                 p.get("niveau_nom") or "—", "oui" if p["moteur"] else "—"))
        A("")
        A("### Contenu exigé de chaque pièce")
        A("")
        for p in pcs:
            A("**[%s](%s) — %s** (%s ; %s)"
              % (p["code"], _lien_piece(d["code"], p["code"]), p["titre"],
                 p["type_nom"], p["emetteur_nom"]))
            if p.get("niveau_nom"):
                # Le niveau attendu, écrit à côté du contenu : c'est lui qui dit
                # jusqu'où descendre, et une même spécification n'engage pas la
                # même chose à l'avant-projet et à la consultation.
                A("")
                A("*%s — %s*" % (p["niveau_nom"], p["niveau_aide"]))
                if p.get("autres_phases"):
                    # LE lien entre livrables. Chaque phase où la pièce revient
                    # est cliquable et ouvre le registre sur cette phase, la
                    # pièce mise en évidence — sans cela le lecteur devait
                    # retrouver la filière, la phase et la ligne à la main.
                    A("")
                    A("*Document unique, repris en %s : c'est un indice de la "
                      "même pièce, pas un document neuf.*"
                      % ", ".join("[%s](%s)" % (q, _lien_piece(q, p["code"]))
                                  for q in p["autres_phases"]))
            A("")
            for c in p["contenu"]:
                A("- %s" % c)
            A("")
        A("*%s*" % d.get("note_registre", ""))
        A("")

    # ── Améliorer et optimiser ce livrable ──────────────────────────────
    A("---")
    A("")
    A("## %d. Améliorer et optimiser ce livrable" % n_)
    A("")
    props, non_chiffres = _ameliorations(d)
    A("### Ce qui resserrerait le plus les fourchettes")
    A("")
    if props:
        A("Classé par effet décroissant sur ce dossier-ci. Les gestes sans "
          "pourcentage débloquent une grandeur au lieu de resserrer une "
          "fourchette : les deux effets ne se comparent pas.")
        A("")
        for i, p in enumerate(props, 1):
            A("%d. **%s** — %s" % (i, p["geste"], p["gain"].strip()))
        A("")
    else:
        A("Rien ne manque du côté du moteur pour cette phase. L'amélioration "
          "porte désormais sur les disciplines que le calcul n'alimente pas.")
        A("")
    if non_chiffres:
        # Groupe séparé, et dit comme tel : les ranger avec les précédents
        # les ferait paraître moins lourds parce qu'ils sont moins mesurables.
        A("**Également requis, sans effet chiffrable par balayage.** Ce sont "
          "des choix de projet et non des réglages : leur poids peut dépasser "
          "celui des champs ci-dessus, il ne s'exprime simplement pas en "
          "pourcentage.")
        A("")
        for p in non_chiffres:
            A("- **%s** — %s" % (p["geste"], p["gain"]))
        A("")

    A("### Ce qui reste à développer et à corriger")
    A("")
    r_ = d.get("resume_pieces") or {}
    non_alim = max(0, r_.get("total", len(pcs)) - r_.get("alimentees_par_le_moteur", 0))
    A("- **À développer** — %d pièce%s du registre ne %s alimentée%s par le "
      "calcul : leur contenu relève d'autres disciplines et **reste entièrement "
      "à écrire**."
      % (non_alim, "s" if non_alim > 1 else "", "sont pas" if non_alim > 1
         else "est pas", "s" if non_alim > 1 else ""))
    if a_remp:
        A("- **À corriger avant diffusion** — %s %s présentée%s avec une valeur "
          "indicative. **Aucune ne doit être reprise dans une pièce "
          "contractuelle en l'état.**"
          % (len(a_remp), "grandeurs sont" if len(a_remp) > 1
             else "grandeur est", "s" if len(a_remp) > 1 else ""))
    if zeros:
        A("- **À confirmer** — %s affichée%s à zéro sans incertitude déclarée."
          % (", ".join(g["nom"] for g in zeros), "s" if len(zeros) > 1 else ""))
    A("- **À relire** — ce document est un **brouillon** produit par un calcul "
      "déterministe. Les chiffres ne sont pas à réécrire ; les commentaires qui "
      "les accompagnent sont à adapter au projet.")
    A("")
    A("**Optimisation propre à cette phase** — %s Le geste qui y prépare est "
      "décrit ci-dessus, dans l'ordre où il produit le plus d'effet."
      % d["verrouille"])
    A("")
    A("---")
    A("")

    A("## %d. Traçabilité" % (n_ + 1))
    A("")
    A("- Registre en ligne de cette phase : [%s](%s)"
      % (d["code"], _lien_piece(d["code"])))
    A("- Moteur de calcul : datacenter v%s" % d["version_moteur"])
    A("- Cadre de phases : ingenierie_dc v%s" % ingenierie_dc.VERSION)
    A("- Cadre de référence de la filière : %s"
      % ingenierie_dc.FILIERES[d["filiere"]]["cadre"])
    A("")
    A("Aucun modèle de langage n'intervient dans les valeurs ci-dessus : elles "
      "sont produites par un calcul déterministe. Deux exécutions avec les mêmes "
      "entrées donnent le même résultat, au chiffre près.")
    return "\n".join(L)


@app.route("/api/datacenter/export", methods=["POST"])
@login_required
def api_datacenter_export():
    """La note de calcul en Word ou PDF, recalculée côté serveur.

    Comme pour la relecture contractuelle : un document qui sort du cabinet et
    porte des engagements chiffrés ne doit pas dépendre de ce qu'un formulaire a
    bien voulu transmettre.
    """
    data = request.get_json(silent=True) or {}
    profil = _profil_datacenter(data)
    if not profil.get("puissance_it_kw"):
        return jsonify(ok=False, error="puissance_absente",
                       message="La puissance informatique installée est nécessaire."), 400
    fmt = (data.get("format") or "docx").strip().lower()
    if fmt not in ("docx", "pdf"):
        fmt = "docx"
    res = datacenter.etude(profil)
    md = _note_calcul_markdown(res, str(data.get("client") or "").strip()[:120])
    meta = {"label": "Note de calcul — centre de données",
            "client": str(data.get("client") or "")[:120],
            "perimetre": "%s kW informatiques · %s" % (
                round(profil["puissance_it_kw"]),
                datacenter.REFROIDISSEMENT.get(
                    profil.get("refroidissement") or "eau_glacee", {}).get("nom", "")),
            "date": time.strftime("%d/%m/%Y"),
            "sources": [{"title": "Moteur d'ingénierie CONSEILPREV v" + datacenter.VERSION,
                         "theme": "calcul déterministe"}]}
    try:
        if fmt == "pdf":
            blob = livrables_export.build_pdf(md, meta)
            mimetype = "application/pdf"
        else:
            blob = livrables_export.build_docx(md, meta)
            mimetype = ("application/vnd.openxmlformats-officedocument"
                        ".wordprocessingml.document")
    except Exception:
        app.logger.exception("export note de calcul")
        return jsonify(ok=False, error="export_echec",
                       message="La mise en page a échoué."), 500
    audit.journaliser("datacenter.export", cible=fmt,
                      detail="%s kW" % round(profil["puissance_it_kw"]))
    return send_file(io.BytesIO(blob), download_name="note-calcul-datacenter." + fmt,
                     as_attachment=True, mimetype=mimetype)


def _note_calcul_markdown(res, client=""):
    """La note de calcul en Markdown, chaque valeur avec sa formule.

    Écrite ici et non par un modèle : c'est le document opposable. Le modèle
    intervient sur les livrables rédigés, qui l'entourent — jamais sur elle.
    """
    L = ["# Note de calcul — centre de données",
         "", "*Document produit par le moteur d'ingénierie CONSEILPREV "
         "v%s. Aucun modèle de langage n'intervient dans ces calculs : deux "
         "exécutions avec les mêmes entrées donnent le même résultat.*" % datacenter.VERSION, ""]
    if client:
        L += ["**Client :** " + client, ""]

    L += ["## Données d'entrée", ""]
    for champ in datacenter.CHAMPS:
        v = res["profil"].get(champ["id"])
        if v not in (None, ""):
            L.append("- %s : **%s** %s" % (champ["label"], datacenter.fr(v)
                      if champ["type"] == "nombre" else v, champ.get("unite", "")))
    L.append("")

    for titre, section, cles in [
        ("Bilan énergétique", "energie",
         ["pue", "energie_it_MWh", "energie_totale_MWh", "energie_non_it_MWh", "dcie"]),
        ("Bilan eau", "eau",
         ["evaporation_m3", "purge_m3", "appoint_m3", "wue_site", "wue_source", "eau_amont_m3"]),
        ("Bilan carbone", "carbone",
         ["cue", "co2_exploitation_localise_t", "co2_exploitation_marche_t", "ref",
          "incorpore_serveurs_t", "incorpore_batiment_t", "incorpore_technique_t",
          "empreinte_totale_t", "part_incorpore_pct"]),
        ("Chaleur fatale", "chaleur", ["erf", "ere", "energie_reutilisee_MWh"]),
    ]:
        L += ["## " + titre, ""]
        d = res.get(section) or {}
        for cle in cles:
            v = d.get(cle)
            if not isinstance(v, dict) or "valeur" not in v:
                continue
            L.append("### %s" % v["nom"])
            L.append("")
            L.append("**%s %s**" % (datacenter.fr(v["valeur"]), v["unite"]))
            L.append("")
            if v.get("formule"):
                L.append("- Formule : %s" % v["formule"])
            if v.get("entrees"):
                L.append("- Entrées : " + " · ".join(
                    "%s = %s" % (k, datacenter.fr(x) if isinstance(x, (int, float))
                                 else x)
                    for k, x in v["entrees"].items()))
            if v.get("source"):
                L.append("- Source : %s" % v["source"])
            if v.get("incertitude"):
                L.append("- Incertitude : %s" % v["incertitude"])
            if v.get("note"):
                L.append("- %s" % v["note"])
            L.append("")

    lev = res.get("leviers") or []
    if lev:
        L += ["## Leviers, classés par gain carbone", "",
              "| Levier | tCO2e/an | m³ eau/an | MWh/an | €/an | Difficulté |",
              "|---|---:|---:|---:|---:|---|"]
        for x in lev:
            L.append("| %s | %s | %s | %s | %s | %s |" % (
                x["titre"], datacenter.fr(x["gain_co2_t"]), datacenter.fr(x["gain_eau_m3"]),
                datacenter.fr(x["gain_energie_MWh"]), datacenter.fr(x["gain_euros"], 0),
                x["difficulte"]))
        L.append("")
        L.append("Chaque levier porte une contrepartie ; elles sont détaillées "
                 "ci-dessous, parce qu'un levier présenté sans la sienne est un "
                 "argument commercial, pas une recommandation d'ingénierie.")
        L.append("")
        for x in lev:
            L += ["### " + x["titre"], "",
                  "- Contrepartie : %s" % x["contrepartie"],
                  "- Condition : %s" % x["condition"],
                  "- Fondement : %s" % x["fondement"], ""]

    conf = res.get("conformite") or []
    if conf:
        L += ["## Conformité et repères de marché", "",
              "| Sujet | Statut | Détail |", "|---|---|---|"]
        for c in conf:
            L.append("| %s | %s | %s |" % (c["sujet"], c["statut"], c["detail"]))
        L.append("")

    av = res.get("avertissements") or []
    if av:
        L += ["## Limites de cette note", "",
              "Ce que le calcul ne dit pas est aussi important que ce qu'il dit. "
              "Ces réserves font partie de la note ; les retirer la rendrait "
              "indéfendable en comité technique.", ""]
        for a in av:
            L.append("- " + a)
        L.append("")
    return "\n".join(L)


# ══════════════════════════════════════════════════════════════════════════
#  AGENT DATA CENTER — livrables rédigés depuis le corpus documentaire
#
#  Deuxième brique, complémentaire du moteur de calcul ci-dessus et non
#  redondante avec lui. Le moteur CALCULE des grandeurs physiques ; l'agent
#  RÉDIGE des livrables à partir des documents chargés dans la base de
#  connaissance, en citant ses sources passage par passage et en refusant de
#  produire quand le corpus ne couvre pas la demande.
#
#  Ce refus est la propriété qui compte. Un générateur qui répond toujours
#  produit, sur un corpus vide, un document plausible et faux — c'est-à-dire
#  exactement ce qu'on ne peut pas remettre à un client.
# ══════════════════════════════════════════════════════════════════════════

import agent_datacenter  # noqa: E402

_AGENT_DC_INDEX_PATH = os.path.join(HERE, "corpus_datacenter.json")
_AGENT_DC = None
_AGENT_DC_LOCK = threading.Lock()


def _agent_dc_embed(textes):
    """Vectorisation, branchée sur le magasin existant.

    On réutilise rag_store plutôt que de rouvrir une connexion à Mistral : la
    clé, le modèle, la dimension et le délai d'attente y sont déjà décidés, et
    deux endroits qui appellent le même service finissent par diverger sur l'un
    de ces quatre paramètres — le jour où l'un change.
    """
    try:
        return rag_store.embed_texts(list(textes))
    except Exception as exc:  # noqa: BLE001
        raise agent_datacenter.EmbeddingIndisponible(str(exc)) from exc


def _agent_dc_complete(system, user, temperature=0.2):
    """Complétion, branchée sur l'assistant existant.

    assistant.generate() choisit le fournisseur et gère le repli. La
    température demandée par l'agent n'y est pas exposée : on la documente au
    lieu de la taire, parce qu'un agent qui croit piloter un paramètre qu'il ne
    pilote pas produit des résultats qu'on n'explique plus.
    """
    dispo = assistant.available()
    modele = "claude" if dispo.get("claude") else ("mistral" if dispo.get("mistral") else None)
    if not modele:
        raise RuntimeError("Aucun fournisseur de modèle configuré.")
    texte, _ = assistant.generate(modele, system, user)
    return texte or ""


def _agent_dc():
    """L'agent, construit une seule fois et à la demande.

    Construction paresseuse : l'index se charge depuis le disque, et sur un
    corpus volumineux cette lecture ne doit pas retarder le démarrage du site.
    """
    global _AGENT_DC
    if _AGENT_DC is None:
        with _AGENT_DC_LOCK:
            if _AGENT_DC is None:
                index = agent_datacenter.CorpusIndex(_AGENT_DC_INDEX_PATH)
                _AGENT_DC = agent_datacenter.DataCenterAgent(
                    index, _agent_dc_embed, _agent_dc_complete,
                    journal_path=os.path.join(HERE, "journal_agent_datacenter.jsonl"))
    return _AGENT_DC


@app.route("/api/datacenter/agent/indexer", methods=["POST"])
@admin_required
def api_agent_dc_indexer():
    """Alimente le corpus de l'agent depuis la base de connaissance.

    Réservé à l'administrateur : indexer, c'est décider de ce que l'agent aura
    le droit de citer. Ce n'est pas une action de lecture.
    """
    data = request.get_json(silent=True) or {}
    themes = data.get("themes")
    if not isinstance(themes, list) or not themes:
        # Par défaut, toute la famille « Centres de données » de la base.
        themes = [t for t in rag_store.THEMES if t.startswith("Data center")]
    agent = _agent_dc()
    total, docs, erreurs = 0, 0, []
    for theme in themes[:40]:
        try:
            hits = rag_store.store.search("data center énergie eau carbone",
                                          k=60, public_only=False, theme=theme)
        except Exception as exc:  # noqa: BLE001
            erreurs.append("%s : %s" % (theme, exc))
            continue
        for h in hits:
            texte = (h.get("text") or h.get("contenu") or "").strip()
            if len(texte) < 200:
                continue
            try:
                n = agent.index.add_document(
                    texte, h.get("title") or h.get("source") or theme,
                    str(h.get("created_at") or "")[:10], _agent_dc_embed)
            except agent_datacenter.EmbeddingIndisponible as exc:
                return jsonify(ok=False, error="vectorisation_indisponible",
                               message=str(exc)), 503
            total += n
            docs += 1
    try:
        agent.index.save()
    except Exception:
        app.logger.exception("sauvegarde du corpus agent")
        return jsonify(ok=False, error="corpus_non_sauvegarde",
                       message="Les passages sont en mémoire mais n'ont pas pu "
                               "être écrits : ils seront perdus au redémarrage."), 500
    audit.journaliser("agent_datacenter.indexation", cible=str(len(themes)) + " thème(s)",
                      detail="%d passage(s) retenus sur %d extrait(s)" % (total, docs))
    return jsonify(ok=True, passages_ajoutes=total, extraits_lus=docs,
                   passages_total=len(agent.index.passages), erreurs=erreurs)


@app.route("/api/datacenter/agent/etat", methods=["GET"])
@login_required
def api_agent_dc_etat():
    """Ce que l'agent peut faire AUJOURD'HUI, et ce qui lui manque.

    Publié plutôt que deviné : un corpus vide et un service de vectorisation
    absent produisent le même refus côté utilisateur, et appellent deux gestes
    opposés — charger des documents, ou configurer une clé.
    """
    agent = _agent_dc()
    par_theme = {}
    for p in agent.index.passages:
        par_theme[p.theme] = par_theme.get(p.theme, 0) + 1
    dispo = assistant.available()
    return jsonify(ok=True,
                   passages=len(agent.index.passages),
                   par_theme=par_theme,
                   corpus_version=agent_datacenter.CORPUS_VERSION,
                   vectorisation=rag_store.embeddings_available(),
                   redaction=bool(dispo.get("claude") or dispo.get("mistral")),
                   seuil=agent.threshold,
                   passages_minimum=agent.min_passages)


# Le blueprint de l'agent, derrière le même verrou que le reste du conseil.
# Le module reste agnostique : c'est ici, et seulement ici, que le système de
# comptes du site entre en jeu.
#
# On passe la FONCTION _agent_dc et non un agent déjà construit : le blueprint
# s'enregistre à l'import, alors que l'agent charge son corpus depuis le disque.
# Construire l'un pour enregistrer l'autre ferait payer cette lecture à chaque
# démarrage du site, y compris quand personne n'ouvrira la page.
app.register_blueprint(
    agent_datacenter.build_blueprint(_agent_dc, garde=login_required))


@app.route("/audit-conformite")
@login_required
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


_CONNECTOR_ZIP = {}  # cache mémoire : {"key": signature fichiers, "data": bytes}


@app.route("/telecharger/connecteur.zip")
@login_required
def download_connector():
    """Archive zip du connecteur (Python standard, sans dépendance) + guide de
    déploiement. L'archive est construite une seule fois puis servie depuis la
    mémoire (reconstruite si un fichier source change), avec ETag + 304."""
    base = os.path.join(HERE, "connectors")
    sig = []
    for root, _dirs, files in os.walk(base):
        for name in sorted(files):
            if name.endswith((".pyc", ".pyo")) or "__pycache__" in root:
                continue
            full = os.path.join(root, name)
            st = os.stat(full)
            sig.append((os.path.relpath(full, HERE), st.st_mtime_ns, st.st_size))
    key = hashlib.sha256(repr(sorted(sig)).encode()).hexdigest()[:24]
    ent = _CONNECTOR_ZIP.get("zip")
    if ent is None or ent["key"] != key:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for rel, _mt, _sz in sig:
                z.write(os.path.join(HERE, rel), rel)
        ent = {"key": key, "data": buf.getvalue()}
        _CONNECTOR_ZIP["zip"] = ent
    etag = '"z-%s"' % key
    cache = {"ETag": etag, "Cache-Control": "private, max-age=0, must-revalidate"}
    if etag in (request.headers.get("If-None-Match") or ""):
        return Response(status=304, headers=cache)
    resp = send_file(io.BytesIO(ent["data"]), mimetype="application/zip",
                     as_attachment=True, download_name="conseilprev-connecteur.zip")
    for k, v in cache.items():
        resp.headers[k] = v
    return resp


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


@app.route("/conformite")
def conformite():
    """Dossier de conformité RGPD & IA Act, rendu depuis rgpd.py via /api/conformite."""
    return _page(PAGES["/conformite"])


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


@app.route("/parcours.js")
def parcours_js():
    """Parcours guidés par rôle — données et interface, partagés par toutes les pages."""
    return _serve_fast("parcours.js", _CC_ASSET,
                       mimetype="text/javascript; charset=utf-8")


@app.route("/datacenter.js")
def datacenter_js():
    """Interface de l'étude de centre de données.

    Fichier séparé et non script inline : il fait 300 lignes, et la page qui l'a
    servi de modèle portait déjà 27 000 caractères de script inline — au point
    qu'en la recopiant, on a d'abord embarqué le moteur d'une AUTRE page. Un
    fichier nommé se voit ; un bloc inline se recopie par accident.

    Route publique : le script ne contient aucune donnée, seulement l'affichage.
    Ce sont les API qu'il appelle qui exigent une session.
    """
    return _serve_fast("datacenter.js", _CC_ASSET,
                       mimetype="text/javascript; charset=utf-8")


@app.route("/dc-profil.js")
def dc_profil_js():
    """Le profil d'installation porté d'une page à l'autre.

    Fichier partagé par /datacenter et /ingenierie-datacenter, et non recopié
    dans chacune : les deux pages construisent le même formulaire depuis le
    même référentiel, et deux copies de la logique de transport divergeraient
    au premier champ ajouté.

    Route publique : rien d'autre que de l'affichage et un magasin de session
    côté navigateur. Aucune donnée du site n'y figure.
    """
    return _serve_fast("dc-profil.js", _CC_ASSET,
                       mimetype="text/javascript; charset=utf-8")


@app.route("/ingenierie-dc.js")
def ingenierie_dc_js():
    """Interface du cadre de phases. Même règle que ci-dessus : route publique,
    aucune donnée dans le fichier — ce sont les API qu'il appelle qui exigent
    une session."""
    return _serve_fast("ingenierie-dc.js", _CC_ASSET,
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
# Pages publiques uniquement : on exclut celles qui nécessitent un compte. Les
# pages protégées sont détectées automatiquement (décorateur @login_required /
# @admin_required, repère `auth_gated`) : aucune liste à tenir à jour à la main
# quand on protège une nouvelle page. `_SITEMAP_EXCLUDE` reste pour d'éventuelles
# exclusions manuelles (pages publiques mais non indexables).
_SITEMAP_EXCLUDE = set()
_SITEMAP_TOP = {"/", "/services", "/contact", "/etudes-de-cas", "/about"}


def _auth_gated_paths():
    """Chemins des pages protégées par connexion (exclus du sitemap public)."""
    gated = set()
    for rule in app.url_map.iter_rules():
        view = app.view_functions.get(rule.endpoint)
        if view is not None and getattr(view, "auth_gated", False):
            gated.add(str(rule.rule))
    return gated


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
    exclude = _SITEMAP_EXCLUDE | _auth_gated_paths()
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path in PAGES:
        if path in exclude:
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
    """Console d'administration de la base de connaissance RAG.

    Retour d'un chargement par formulaire classique (paramètre « up ») : le
    résultat est inséré DANS LA PAGE côté serveur. Indispensable pour que la
    confirmation reste visible quand le JavaScript est indisponible — c'est
    précisément le cas où ce mode de chargement sert de secours."""
    code = (request.args.get("up") or "").strip()
    if not code:
        return _serve_fast("admin-base-connaissance.html", _CC_ADMIN)
    titre = (request.args.get("t") or "")[:120]
    detail = (request.args.get("d") or "")[:160]
    if code == "ok":
        banner = ("<div class=\"warn\" style=\"border-color:rgba(52,211,153,.55);"
                  "background:rgba(52,211,153,.12)\"><span>✅</span><div>Document "
                  "<b>%s</b> chargé et enregistré.</div></div>" % html_lib.escape(titre))
    else:
        banner = ("<div class=\"warn\" style=\"border-color:rgba(248,113,113,.55);"
                  "background:rgba(248,113,113,.12)\"><span>⛔</span><div>Échec du "
                  "chargement : <b>%s</b>%s</div></div>"
                  % (html_lib.escape(code),
                     (" — " + html_lib.escape(detail)) if detail else ""))
    try:
        raw = _static_entry("admin-base-connaissance.html")["raw"].decode("utf-8")
    except Exception:
        return _serve_fast("admin-base-connaissance.html", _CC_ADMIN)
    marqueur = '<div id="notice"></div>'
    html = raw.replace(marqueur, marqueur + banner, 1) if marqueur in raw else raw
    resp = Response(html, mimetype="text/html; charset=utf-8")
    resp.headers["Cache-Control"] = "private, no-store"   # page personnalisée
    return resp


def _familles_payload():
    """Vocabulaire groupé par famille, tel que l'interface le proposera.

    Transmis en plus de `themes` (liste à plat, qui reste la référence pour la
    validation) : sans lui, le navigateur devrait redéclarer quels thèmes sont
    des entreprises et lesquels sont des domaines — une classification recopiée
    dans deux fichiers finit toujours par diverger de l'originale."""
    return {"groupes": [{"nom": nom, "themes": list(themes)}
                        for nom, themes in THEME_FAMILLES],
            "entreprises": FAMILLE_ENTREPRISES,
            "engineering": FAMILLE_ENGINEERING}


@app.route("/api/admin/rag/documents", methods=["GET"])
@admin_required
def api_rag_list():
    """Liste des documents + statistiques + capacités (mode de recherche actif).

    Tolérant aux pannes : si la base a un souci passager, on renvoie une réponse
    EXPLOITABLE (liste vide + capacités dégradées portant la cause) pour que la
    console affiche le bandeau de diagnostic — jamais un 500 opaque « Service
    indisponible »."""
    try:
        return jsonify(ok=True, documents=rag.list_documents(), stats=rag.stats(),
                       capabilities=rag.capabilities(), themes=THEMES,
                       familles=_familles_payload(), formats=formats_available())
    except Exception:
        try:
            caps = rag.capabilities()
        except Exception:
            caps = {"persistent": False, "mode": "lexical", "reason": "db_connection_failed"}
        return jsonify(ok=True, documents=[],
                       stats={"documents": 0, "chunks": 0, "themes": {}, "storage": None},
                       capabilities=caps, themes=THEMES,
                       familles=_familles_payload(), formats=formats_available())


@app.route("/api/admin/rag/search", methods=["POST"])
@admin_required
def api_rag_search():
    """Explorer / tester la base de connaissance : renvoie les extraits les plus
    pertinents pour une question — exactement ce que l'assistant et les livrables
    reçoivent comme contexte. Admin : documents publics ET internes."""
    data = request.get_json(silent=True) or {}
    q = (data.get("query") or "").strip()
    if not q:
        return jsonify(ok=False, error="query_vide",
                       message="Saisissez une question."), 400
    # Périmètre de recherche (comme la console Sentinel) : documents et/ou veille
    # CERT-FR. Par défaut, les deux. On récupère un peu large puis on filtre selon
    # le périmètre, afin de renvoyer les 6 meilleurs extraits DU périmètre demandé.
    src = data.get("sources") or {}
    want_docs = src.get("docs", True)
    want_veille = src.get("veille", True)
    if not want_docs and not want_veille:
        return jsonify(ok=True, hits=[])
    try:
        hits = rag.search(q[:500], k=18, public_only=False)
    except Exception:
        return jsonify(ok=False, error="recherche_echec",
                       message="Recherche indisponible."), 500

    def _is_veille(h):
        return (h.get("theme") == "Veille"
                or str(h.get("title") or "").startswith("[CERT-FR]"))
    if not (want_docs and want_veille):
        hits = [h for h in hits
                if (_is_veille(h) if want_veille else not _is_veille(h))]
    return jsonify(ok=True, hits=hits[:6])


@app.route("/api/admin/rag/eval", methods=["POST"])
@admin_required
def api_rag_eval():
    """Mini-harnais d'évaluation du retrieval : pour chaque cas {query, expect},
    mesure si un extrait contenant « expect » remonte dans le top-k et à quel
    rang. Renvoie hit@k (part des cas trouvés) et MRR (rang réciproque moyen) —
    pour objectiver chaque réglage du RAG (avant/après)."""
    data = request.get_json(silent=True) or {}
    cases = data.get("cases") or []
    try:
        k = min(max(int(data.get("k") or 8), 1), 20)
    except (TypeError, ValueError):
        k = 8
    results, hit, rr_sum = [], 0, 0.0
    for c in cases[:50]:
        q = (c.get("query") or "").strip()
        expect = (c.get("expect") or "").strip().lower()
        if not q or not expect:
            continue
        try:
            hits = rag.search(q[:500], k=k, public_only=False)
        except Exception:
            hits = []
        rank = 0
        for i, h in enumerate(hits):
            hay = ((h.get("content") or "") + " " + (h.get("title") or "")
                   + " " + (h.get("theme") or "")).lower()
            if expect in hay:
                rank = i + 1
                break
        results.append({"query": q, "expect": c.get("expect"), "rank": rank,
                        "top": (hits[0].get("title") if hits else None)})
        if rank:
            hit += 1
            rr_sum += 1.0 / rank
    n = len(results)
    return jsonify(ok=True, k=k, n=n,
                   hit_rate=round(hit / n, 3) if n else 0,
                   mrr=round(rr_sum / n, 3) if n else 0,
                   results=results)


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
    """Supprime les doublons en conservant un exemplaire par contenu.

    Un périmètre peut être demandé (« engineering ») : le dédoublonnage ne
    touche alors qu'à ce corpus, jamais au reste de la base."""
    data = request.get_json(silent=True) or {}
    scope = (data.get("scope") or "").strip().lower()
    docs = _rag_scope_docs(scope) if scope else None
    report = rag_dedupe(rag, docs=docs)
    return jsonify(ok=True, scope=scope or "tout", **report)


@app.route("/api/admin/rag/retheme", methods=["POST"])
@admin_required
def api_rag_retheme():
    """Reclasse des documents dans un autre thème / sous-dossier.

    Seul le classement change : texte, fragments et embeddings sont conservés,
    donc AUCUNE réindexation n'est nécessaire — ranger 18 documents est immédiat
    et sans risque, là où les recharger un à un coûterait un temps considérable.

    Le thème visé est validé contre le vocabulaire THEMES : impossible d'inventer
    un dossier au passage, la nomenclature reste maîtrisée."""
    data = request.get_json(silent=True) or {}
    theme = (data.get("theme") or "").strip()
    ids = data.get("ids")
    if theme not in THEMES:
        return jsonify(ok=False, error="theme_inconnu",
                       message="Thème inconnu — choisissez-en un dans la liste."), 400
    if not isinstance(ids, list) or not ids:
        return jsonify(ok=False, error="aucun_document",
                       message="Aucun document à reclasser."), 400
    deplaces = inchanges = echecs = 0
    for doc_id in ids[:2000]:
        if not _rag_valid_doc_id(str(doc_id)):
            echecs += 1
            continue
        try:
            rag.set_theme(str(doc_id), theme)
            deplaces += 1
        except RagError:
            echecs += 1
        except Exception:
            app.logger.exception("retheme : échec pour %r", doc_id)
            echecs += 1
    return jsonify(ok=True, theme=theme, deplaces=deplaces,
                   inchanges=inchanges, echecs=echecs)


@app.route("/api/admin/rag/documents/<doc_id>/visibility", methods=["POST"])
@admin_required
def api_rag_visibility(doc_id):
    """Bascule un document entre « interne » et « public ».

    Effet IMMÉDIAT : la visibilité est relue à chaque recherche, sans cache ni
    réindexation. Rendre un document « public », c'est autoriser l'assistant à
    le citer à n'importe quel visiteur — l'appel est donc réservé à l'admin, et
    l'interface demande confirmation dans ce sens."""
    if not _rag_valid_doc_id(doc_id):
        return jsonify(ok=False, error="document_invalide"), 400
    data = request.get_json(silent=True) or {}
    v = (data.get("visibility") or "").strip().lower()
    if v not in ("public", "internal"):
        return jsonify(ok=False, error="visibilite_invalide"), 400
    try:
        rag.set_visibility(doc_id, v)
    except RagError as exc:
        return jsonify(ok=False, error=exc.code,
                       detail=getattr(exc, "detail", "")), exc.status
    except Exception as exc:
        app.logger.exception("visibility : échec pour %r", doc_id)
        return jsonify(ok=False, error="visibilite_echec", detail=_exc_detail(exc)), 500
    audit.journaliser("document.visibilite", cible=doc_id, detail=v)
    return jsonify(ok=True, visibility=v)


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


@app.route("/api/admin/rag/storage", methods=["POST"])
@admin_required
def api_rag_storage():
    """Occupation disque de la base de connaissance + postes récupérables.

    Une base hébergée a un plafond (512 Mo sur l'offre gratuite Neon). Atteint,
    il fait échouer TOUTE écriture : la page s'affiche encore mais plus aucun
    document ne se charge. Rendre l'occupation visible évite que cette panne se
    reproduise sans qu'on comprenne pourquoi."""
    fn = getattr(rag, "storage_report", None)
    if not callable(fn):
        return jsonify(ok=False, error="indisponible",
                       message="Occupation disponible uniquement avec PostgreSQL."), 409
    try:
        return jsonify(ok=True, **fn())
    except Exception as exc:
        return jsonify(ok=False, error="storage_echec", detail=_exc_detail(exc)), 500


@app.route("/api/admin/rag/storage/capacity", methods=["POST"])
@admin_required
def api_rag_capacity():
    """Déclare la capacité du plan d'hébergement, en Go (0 pour l'oublier).

    PostgreSQL ignore son propre quota : il est imposé au-dessus de lui. Sans
    cette valeur, l'occupation reste un chiffre nu — on ne sait pas si l'on est
    à 5 % ou à 95 %, et la saturation n'arrive que par surprise, sous la forme
    d'un refus d'écriture. La saisir ici plutôt que par une variable
    d'environnement évite un aller-retour par le tableau de bord de l'hébergeur
    suivi d'un redéploiement ; la valeur est mémorisée en base, donc partagée
    par tous les workers et conservée d'un déploiement à l'autre."""
    if not callable(getattr(rag, "storage_report", None)):
        return jsonify(ok=False, error="indisponible",
                       message="Réglage disponible uniquement avec PostgreSQL."), 409
    data = request.get_json(silent=True) or {}
    try:
        gb = float(str(data.get("gb", "")).replace(",", ".").strip() or 0)
    except (TypeError, ValueError):
        return jsonify(ok=False, error="valeur_invalide"), 400
    # Borne haute volontairement large (100 To) : elle n'existe que pour écarter
    # une saisie aberrante, pas pour présumer du plan de l'hébergeur.
    if gb < 0 or gb > 100000:
        return jsonify(ok=False, error="valeur_invalide"), 400
    try:
        rag.set_setting("capacity_gb", None if gb == 0 else ("%g" % gb))
    except RagError as exc:
        return jsonify(ok=False, error=exc.code,
                       detail=getattr(exc, "detail", "")), exc.status
    except Exception as exc:
        app.logger.exception("capacity : échec d'enregistrement")
        return jsonify(ok=False, error="capacite_echec", detail=_exc_detail(exc)), 500
    try:
        return jsonify(ok=True, **rag.storage_report())
    except Exception:
        return jsonify(ok=True)


@app.route("/api/admin/comptes/reconnecter", methods=["POST"])
@admin_required
def api_comptes_reconnecter():
    """Rebranche immédiatement le magasin de comptes sur PostgreSQL.

    Le rebranchement est déjà automatique (nouvelle tentative toutes les 20 s) ;
    ce bouton évite d'attendre quand on sait que la base vient de revenir."""
    import auth as _auth
    fn = getattr(_auth.store, "reconnecter", None)
    if not callable(fn):
        return jsonify(ok=False, error="indisponible"), 409
    try:
        ok = bool(fn())
    except Exception as exc:
        return jsonify(ok=False, error="reconnexion_echec", detail=_exc_detail(exc)), 500
    audit.journaliser("comptes.reconnexion", detail=getattr(_auth.store, "mode", ""), ok=ok)
    return jsonify(ok=ok, mode=getattr(_auth.store, "mode", ""))


@app.route("/api/admin/audit", methods=["GET"])
@admin_required
def api_audit():
    """Journal d'audit : qui a fait quoi, quand, depuis quel réseau.

    Lecture seule — aucune route ne permet de modifier ni d'effacer une entrée.
    Un journal réinscriptible ne prouverait rien."""
    try:
        limit = int(request.args.get("limit", 200))
    except (TypeError, ValueError):
        limit = 200
    action = (request.args.get("action") or "").strip()[:80] or None
    return jsonify(ok=True, entrees=audit.lire(limit=limit, action=action),
                   etat=audit.etat())


@app.route("/api/admin/rag/verify", methods=["POST"])
@admin_required
def api_rag_verify():
    """Contrôle d'INTÉGRITÉ : recalcule l'empreinte SHA-256 des fichiers d'origine
    conservés et la compare à celle enregistrée au chargement.

    Une empreinte qui ne correspond plus signale une altération du stockage — une
    corruption silencieuse ne se voit pas autrement : le document continue de
    s'afficher et d'alimenter l'assistant comme si de rien n'était."""
    fn = getattr(rag, "verify_integrity", None)
    if not callable(fn):
        return jsonify(ok=False, error="indisponible",
                       message="Vérification disponible uniquement avec PostgreSQL."), 409
    try:
        res = fn()
    except Exception as exc:
        app.logger.exception("verify : échec")
        audit.journaliser("base.verification", detail="echec", ok=False)
        return jsonify(ok=False, error="verif_echec", detail=_exc_detail(exc)), 500
    audit.journaliser("base.verification",
                      detail="%s vérifiés, %s altérés" % (res.get("verifies", 0),
                                                          len(res.get("alteres", []))),
                      ok=not res.get("alteres"))
    return jsonify(ok=True, **res)


@app.route("/api/admin/rag/purge", methods=["POST"])
@admin_required
def api_rag_purge():
    """Libère de la place en supprimant UNIQUEMENT du reconstituable :
    résidus de chargements interrompus, bulletins de veille, fichiers d'origine
    (les documents restent cherchables ; seul le téléchargement de l'original
    est perdu). Les documents et leur indexation ne sont jamais touchés."""
    fn = getattr(rag, "purge_storage", None)
    if not callable(fn):
        return jsonify(ok=False, error="indisponible",
                       message="Purge disponible uniquement avec PostgreSQL."), 409
    data = request.get_json(silent=True) or {}
    scopes = data.get("scopes") or []
    if not isinstance(scopes, list):
        return jsonify(ok=False, error="scopes_invalides"), 400
    try:
        res = fn(scopes)
    except RagError as exc:
        audit.journaliser("base.purge", cible=",".join(map(str, scopes)),
                          detail=exc.code, ok=False)
        return jsonify(ok=False, error=exc.code,
                       detail=getattr(exc, "detail", "")), exc.status
    except Exception as exc:
        app.logger.exception("purge : échec")
        audit.journaliser("base.purge", cible=",".join(map(str, scopes)),
                          detail="purge_echec", ok=False)
        return jsonify(ok=False, error="purge_echec", detail=_exc_detail(exc)), 500
    audit.journaliser("base.purge", cible=",".join(map(str, scopes)),
                      detail="%s octets libérés" % res.get("libere_octets", 0))
    return jsonify(ok=True, **res)


@app.route("/api/admin/rag/selftest", methods=["POST"])
@admin_required
def api_rag_selftest():
    """AUTO-TEST du chargement, exécuté SUR LE SERVEUR (production comprise).

    Un échec de chargement peut venir de n'importe quelle étape : lecture du
    format (bibliothèque absente), découpage, écriture en base, relecture. Vu
    du navigateur, tout se ressemble — d'où des diagnostics à l'aveugle. Ici, on
    rejoue le pipeline COMPLET sur des documents minuscules générés à la volée
    (texte, puis PDF et Word si les bibliothèques sont là) et on renvoie le
    résultat étape par étape. Les documents de test sont supprimés derrière.

    Aucun secret n'est exposé : les causes techniques passent par _exc_detail."""
    etapes = []

    def etape(nom, ok, info="", bloquant=True):
        """`bloquant=False` : étape purement informative, qui ne pèse pas sur le
        verdict (p. ex. impossible de FABRIQUER un PDF de test — cela ne dit rien
        de la capacité à LIRE les PDF de l'utilisateur, qui relève de pypdf)."""
        etapes.append({"etape": nom, "ok": bool(ok), "info": (info or "")[:200],
                       "bloquant": bool(bloquant)})

    # 1. État du moteur (persistance, mode de recherche) et formats lisibles.
    try:
        caps = rag.capabilities()
        etape("moteur", True, "%s%s" % (caps.get("mode", "?"),
              "" if caps.get("persistent") else " — NON persistant (repli mémoire)"))
    except Exception as exc:
        caps = {}
        etape("moteur", False, _exc_detail(exc))
    fmts = formats_available()
    manquants = [k for k in ("pdf", "docx", "xlsx", "pptx") if not fmts.get(k)]
    etape("formats lisibles", not manquants,
          "tous disponibles" if not manquants
          else "bibliothèque absente pour : " + ", ".join(manquants))

    # 2. Pipeline complet sur des documents jetables, un par format disponible.
    corpus = [("txt", "autotest.txt",
               b"Auto-test de la base de connaissance. "
               b"Ce document jetable verifie l extraction, le decoupage et l ecriture.")]
    if fmts.get("pdf"):
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("helvetica", size=12)
            pdf.multi_cell(0, 8, "Auto-test PDF de la base de connaissance. "
                                 "Verification de la lecture du format PDF.")
            corpus.append(("pdf", "autotest.pdf", bytes(pdf.output())))
        except Exception as exc:
            etape("génération d'un PDF de test", False,
                  "ignoré — le générateur fpdf2 est indisponible ici ; sans effet sur la "
                  "LECTURE de vos PDF (assurée par pypdf, testée ci-dessus). " + _exc_detail(exc),
                  bloquant=False)
    if fmts.get("docx"):
        try:
            import docx as _docx
            doc = _docx.Document()
            doc.add_paragraph("Auto-test Word de la base de connaissance. "
                              "Verification de la lecture du format .docx.")
            buf = io.BytesIO()
            doc.save(buf)
            corpus.append(("docx", "autotest.docx", buf.getvalue()))
        except Exception as exc:
            etape("génération d'un document Word de test", False,
                  "ignoré — générateur indisponible ; sans effet sur la LECTURE de vos "
                  "documents Word. " + _exc_detail(exc), bloquant=False)

    crees = []
    for ext, nom, data in corpus:
        try:
            d = rag.ingest_bytes(nom, data, title="[auto-test] %s" % ext,
                                 theme="Général", visibility="internal")
            nb = int(d.get("nb_chunks") or 0)
            if nb <= 0:
                etape("chargement %s" % ext, False, "aucun fragment produit")
            else:
                crees.append(d.get("id"))
                etape("chargement %s" % ext, True, "%d fragment(s)" % nb)
        except RagError as exc:
            etape("chargement %s" % ext, False,
                  "%s %s" % (exc.code, getattr(exc, "detail", "") or ""))
        except Exception as exc:
            etape("chargement %s" % ext, False, _exc_detail(exc))

    # 3. Relecture : le document chargé est-il bien visible dans la liste ?
    try:
        ids = {d.get("id") for d in rag.list_documents()}
        manque = [i for i in crees if i not in ids]
        etape("relecture", not manque,
              "documents de test retrouvés" if not manque else "document écrit mais absent de la liste")
    except Exception as exc:
        etape("relecture", False, _exc_detail(exc))

    # 4. Ménage : les documents de test ne doivent pas rester dans la base.
    restes = 0
    for doc_id in crees:
        try:
            rag.delete_document(doc_id)
        except Exception:
            restes += 1
    etape("nettoyage", restes == 0,
          "documents de test supprimés" if not restes
          else "%d document(s) de test non supprimé(s)" % restes)

    ok = all(e["ok"] for e in etapes if e["bloquant"])
    if ok:
        concl = ("Le chargement fonctionne de bout en bout sur le serveur. Si l'interface "
                 "échoue malgré tout, videz le cache du navigateur (Ctrl+Maj+R) et réessayez.")
    elif manquants:
        concl = ("Le serveur ne sait pas lire : " + ", ".join(manquants) + ". La bibliothèque "
                 "correspondante manque au service — relancez un déploiement (Manual Deploy → "
                 "Clear build cache & deploy). Vos fichiers ne sont pas en cause.")
    else:
        premier = next((e for e in etapes if not e["ok"] and e["bloquant"]), None)
        concl = ("Échec à l'étape « %s » : %s" % (premier["etape"], premier["info"])) if premier else "Échec."
    return jsonify(ok=True, version=APP_VERSION, reussi=ok, etapes=etapes, conclusion=concl)


@app.route("/api/admin/rag/diagnose", methods=["POST"])
@admin_required
def api_rag_diagnose():
    """Diagnostic pas-à-pas de la connexion PostgreSQL (variable → format →
    URL → DNS → TCP → session → écriture). Aucun secret exposé."""
    try:
        return jsonify(ok=True, **rag_diagnose())
    except Exception:
        return jsonify(ok=False, error="diagnostic_echec"), 500


def _exc_detail(exc, limit=180):
    """Résumé COURT et ASSAINI d'une exception, sûr à renvoyer à l'admin :
    type + message tronqué, sans URL de connexion ni mot de passe. Rend un échec
    de traitement AUTO-DIAGNOSTIQUANT (la vraie cause s'affiche dans l'admin) sans
    avoir à ouvrir les logs Render, et sans exposer de secret."""
    import re as _re
    msg = "%s: %s" % (type(exc).__name__, exc)
    msg = _re.sub(r"postgres(?:ql)?://\S+", "«dsn»", msg, flags=_re.I)
    msg = _re.sub(r"(?i)(password|pwd|token|api[_-]?key)\s*=\s*\S+", r"\1=«…»", msg)
    msg = " ".join(msg.split())
    return (msg[:limit] + "…") if len(msg) > limit else msg


@app.route("/api/admin/rag/upload-file", methods=["POST"])
@admin_required
def api_rag_upload_file():
    """Chargement d'un document en UNE seule requête (multipart) — fiable et
    rapide : extraction, découpage et enregistrement se font côté serveur en un
    seul appel (aucun aller-retour init → morceaux → finish). C'est la voie
    normale de chargement ; le flux par morceaux ci-dessous reste un repli pour
    des cas particuliers. L'indexation vectorielle éventuelle (PostgreSQL +
    embeddings) reste pilotée par le client via index-next, comme avant.

    Idempotent : recharger un contenu déjà présent renvoie le document existant
    (aucun doublon) au lieu d'échouer — comportement volontairement robuste."""
    # Envoi par formulaire HTML classique (sans JavaScript) : on conclut par une
    # REDIRECTION vers la page, message en paramètre — motif « Post/Redirect/Get ».
    # C'est ce qui rend le chargement possible même si le script de la page est
    # indisponible ou en erreur : le navigateur seul suffit.
    form_post = bool(request.form.get("_redirect"))

    def _fin(code, detail="", titre=""):
        if not form_post:
            return None
        from urllib.parse import urlencode
        q = {"up": code}
        if titre:
            q["t"] = titre[:120]
        if detail:
            q["d"] = detail[:160]
        return redirect("/admin/base-connaissance?" + urlencode(q), code=303)

    f = request.files.get("file")
    if f is None or not (f.filename or "").strip():
        return _fin("fichier_manquant") or (jsonify(
            ok=False, error="fichier_manquant", message="Aucun fichier fourni."), 400)
    data = f.read()
    try:
        doc = rag.ingest_bytes(
            f.filename, data,
            title=(request.form.get("title") or "").strip(),
            theme=(request.form.get("theme") or "").strip(),
            visibility=(request.form.get("visibility") or "public").strip())
    except RagError as exc:
        return _fin(exc.code, getattr(exc, "detail", "")) or (jsonify(
            ok=False, error=exc.code, detail=getattr(exc, "detail", "")), exc.status)
    except Exception as exc:
        # Trace complète côté serveur (logs Render) + cause réelle ASSAINIE
        # renvoyée à l'admin : un « traitement_echec » opaque devient
        # auto-diagnostiquant (ex. cause PostgreSQL réelle vs simple transitoire).
        app.logger.exception("upload-file : échec du traitement de %r", f.filename)
        return _fin("traitement_echec", _exc_detail(exc)) or (jsonify(
            ok=False, error="traitement_echec", detail=_exc_detail(exc)), 500)
    return _fin("ok", "", doc.get("title") or f.filename) or jsonify(ok=True, document=doc)


@app.route("/api/admin/rag/upload/init", methods=["POST"])
@admin_required
def api_rag_upload_init():
    """Ouvre une session d'upload par morceaux (repli ; fichiers hors requête unique)."""
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
        return jsonify(ok=False, error=exc.code,
                       detail=getattr(exc, "detail", "")), exc.status
    except Exception as exc:
        # L'indexation vectorielle est un POST-TRAITEMENT : le document est déjà
        # enregistré et cherchable en plein-texte. Une panne ici (base coupée en
        # cours d'indexation…) ne doit JAMAIS faire passer le chargement pour un
        # échec — on le signale comme « dégradé » et le client propose de
        # vectoriser plus tard (bouton « ⟳ Vectoriser »).
        app.logger.exception("index-next : échec pour le document %r", doc_id)
        return jsonify(ok=True, done=True, degraded="indexation_indisponible",
                       detail=_exc_detail(exc))


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
        audit.journaliser("document.suppression", cible=doc_id, detail=exc.code, ok=False)
        return jsonify(ok=False, error=exc.code), exc.status
    audit.journaliser("document.suppression", cible=doc_id)
    return jsonify(ok=True)


def _safe_download_name(name, fallback="document"):
    """Nom de fichier sûr pour l'en-tête Content-Disposition : pas de chemin
    (anti-traversée côté poste client), pas de caractère de contrôle ni de
    guillemet (anti-injection d'en-tête), longueur bornée."""
    name = (name or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(c for c in name if c.isprintable() and c not in '"<>|')
    name = name.strip().lstrip(".")
    return name[:120] or fallback


def _blob_response(filename, data):
    """Réponse de téléchargement d'un blob : nom assaini, type neutre
    (application/octet-stream : jamais interprété par le navigateur, le poste
    choisit l'application par l'extension), ETag fort + 304 (un re-clic sur un
    document déjà téléchargé ne refait pas transiter le fichier)."""
    etag = '"b-%s"' % hashlib.sha256(data).hexdigest()[:24]
    cache = {"ETag": etag, "Cache-Control": "private, max-age=0, must-revalidate"}
    if etag in (request.headers.get("If-None-Match") or ""):
        return Response(status=304, headers=cache)
    resp = send_file(io.BytesIO(data), download_name=_safe_download_name(filename),
                     as_attachment=True, mimetype="application/octet-stream")
    for key, value in cache.items():
        resp.headers[key] = value
    return resp


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
    return _blob_response(filename, data)


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


# ---------------------------------------------------------------------------
#  Sauvegarde / restauration de la base de connaissance (anti-crash) — admin
# ---------------------------------------------------------------------------
# La base gratuite (PostgreSQL ou repli mémoire) peut être perdue lors d'un
# incident : un export téléchargeable (documents + contenu) permet de tout
# restaurer par un simple import, sans dépendre de la base. Bulletins de veille
# CERT-FR exclus (re-collectables automatiquement).
def _rag_is_veille(d):
    return (d.get("theme") == "Veille"
            or str(d.get("title") or "").startswith("[CERT-FR]"))


def _rag_is_engineering(d):
    """Document d'ingénierie : thème « Engineering » ou l'un de ses sous-dossiers.
    Même règle que la liste autonome de l'admin, afin que sauvegarde et
    dédoublonnage portent EXACTEMENT sur ce que l'utilisateur voit."""
    t = d.get("theme") or ""
    return t == "Engineering" or t.startswith("Engineering / ")


def _rag_scope_docs(scope):
    """Documents du périmètre demandé (« engineering » ou tout, hors veille)."""
    docs = [d for d in rag.list_documents() if not _rag_is_veille(d)]
    if (scope or "").strip().lower() == "engineering":
        return [d for d in docs if _rag_is_engineering(d)]
    return docs


def _rag_doc_export(d, eng_only):
    """Une entrée de sauvegarde, ou None si le document n'est pas exportable."""
    if _rag_is_veille(d):
        return None
    if eng_only and not _rag_is_engineering(d):
        return None
    did = d.get("id")
    filename = d.get("filename") or ((d.get("title") or "document") + ".txt")
    try:
        filename, data = rag.get_blob(did)
    except Exception:
        try:
            data = (rag.document_text(did).get("text") or "").encode("utf-8")
        except Exception:
            return None
        if not filename.lower().endswith(".txt"):
            filename += ".txt"
    if not data:
        return None
    return {"title": d.get("title"), "filename": filename,
            "theme": d.get("theme"), "visibility": d.get("visibility"),
            "content_b64": base64.b64encode(data).decode("ascii")}


def _rag_export_flux(scope=None):
    """Sauvegarde ÉCRITE AU FIL DE L'EAU, document par document.

    POURQUOI CE N'EST PLUS CONSTRUIT EN MÉMOIRE
    La version précédente accumulait tout avant d'envoyer quoi que ce soit :
    les octets bruts de chaque fichier, puis leur base64, puis la chaîne JSON
    complète, puis son encodage UTF-8, puis une copie dans un BytesIO pour le
    téléchargement. Soit environ CINQ FOIS le poids du corpus en mémoire vive
    au même instant. Sur une instance à 512 Mo, une base de cent mégaoctets
    suffisait à déclencher le redémarrage automatique — et l'utilisateur voyait
    « exceeded its memory limit » au lieu de son fichier.

    Ici, chaque document est encodé, envoyé, puis oublié : la mémoire occupée
    ne dépasse jamais le plus gros document. La sauvegarde d'un corpus d'un
    gigaoctet passe sur la même instance.

    `count` est écrit à la FIN, et non au début : on ne connaît le nombre de
    documents réellement exportés qu'une fois le dernier lu — certains sont
    écartés en chemin (blob illisible). C'est du JSON valide, et le seul
    lecteur qui s'en sert ne le lit qu'à titre indicatif."""
    eng_only = (scope or "").strip().lower() == "engineering"
    yield ('{"version":1,"app":"conseilprevcyber-rag","created_at":%d,"documents":['
           % int(time.time() * 1000))
    n = 0
    for d in rag.list_documents():
        entree = _rag_doc_export(d, eng_only)
        if not entree:
            continue
        yield ("," if n else "") + json.dumps(entree, ensure_ascii=False)
        n += 1
        del entree                      # rendre la place avant le suivant
    yield '],"count":%d}' % n


def _rag_export(scope=None):
    """Sauvegarde complète en mémoire. Conservée pour un appel programmatique
    sur un petit périmètre ; le téléchargement, lui, passe par le flux."""
    eng_only = (scope or "").strip().lower() == "engineering"
    out = [e for e in (_rag_doc_export(d, eng_only) for d in rag.list_documents()) if e]
    return {"version": 1, "app": "conseilprevcyber-rag",
            "created_at": int(time.time() * 1000), "count": len(out), "documents": out}


@app.route("/api/admin/rag/backup", methods=["GET"])
@admin_required
def api_rag_backup():
    """Télécharge une sauvegarde complète (JSON) de la base de connaissance.

    Réponse en FLUX : le fichier part au fur et à mesure qu'il se fabrique.
    Pas d'ETag ici — le calculer supposerait d'avoir tout le contenu sous la
    main, ce qui est précisément ce qu'on refuse de faire. Une sauvegarde ne se
    re-télécharge de toute façon pas assez souvent pour qu'un cache serve.

    `?probe=1` ne télécharge rien : il confirme que la session est encore
    ouverte. La console s'en sert AVANT de lancer le téléchargement, sinon une
    session expirée ferait enregistrer la réponse d'erreur sous le nom du
    fichier attendu — et l'utilisateur croirait tenir une sauvegarde là où il
    n'a que quarante octets disant « Authentification requise »."""
    scope = (request.args.get("scope") or "").strip().lower()
    if request.args.get("probe"):
        try:
            n = int((rag.stats() or {}).get("documents") or 0)
        except Exception:                                  # noqa: BLE001
            n = -1
        return jsonify(ok=True, documents=n)
    jour = time.strftime("%Y-%m-%d", time.gmtime())
    nom = ("conseilprevcyber-rag-engineering-backup-%s.json" % jour
           if scope == "engineering" else "conseilprevcyber-rag-backup-%s.json" % jour)
    resp = Response(stream_with_context(_rag_export_flux(scope)),
                    mimetype="application/octet-stream")
    resp.headers["Content-Disposition"] = ('attachment; filename="%s"'
                                           % _safe_download_name(nom))
    resp.headers["Cache-Control"] = "no-store"
    # Certains relais tamponnent une reponse sans longueur connue, ce qui
    # annulerait le benefice du flux : on leur demande explicitement de ne pas.
    resp.headers["X-Accel-Buffering"] = "no"
    return resp


@app.route("/api/admin/rag/restore", methods=["POST"])
@admin_required
def api_rag_restore():
    """Restaure les documents d'une sauvegarde (idempotent : un document déjà
    présent est ignoré, jamais dupliqué). Ré-ingestion complète (ré-extraction,
    re-découpage) — robuste quel que soit le moteur de recherche actif."""
    f = request.files.get("file")
    raw = f.read() if f is not None else request.get_data(cache=False)
    try:
        payload = json.loads((raw or b"").decode("utf-8"))
        items = payload.get("documents")
        assert isinstance(items, list)
    except Exception:
        return jsonify(ok=False, error="backup_illisible",
                       message="Fichier de sauvegarde invalide ou illisible."), 400
    restored = skipped = failed = 0
    for it in items:
        try:
            data = base64.b64decode((it.get("content_b64") or "").encode("ascii"))
            if not data:
                skipped += 1
                continue
            doc = rag.ingest_bytes(it.get("filename") or "document.txt", data,
                                   title=(it.get("title") or "").strip(),
                                   theme=(it.get("theme") or "").strip(),
                                   visibility=(it.get("visibility") or "public").strip())
            if doc.get("deduped"):
                skipped += 1
            else:
                restored += 1
        except Exception:
            failed += 1
    return jsonify(ok=True, restored=restored, skipped=skipped, failed=failed,
                   total=len(items))


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
    "timeout": "Le modèle a mis trop de temps à rédiger ce livrable (le service reste "
               "joignable). Réessayez, ou choisissez l'autre modèle — les vitesses "
               "diffèrent d'un fournisseur à l'autre.",
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


def _livrables_run(type_id, data, system, user, extra_query="", label=None):
    """Ancre le prompt sur la base de connaissance (documents publics + internes),
    génère le livrable, l'enregistre dans l'historique et renvoie la réponse JSON.
    Partagé par la génération, l'affinage et les pièces de dossier de projet.

    `label` sert aux documents qui ne figurent pas dans livrables.TYPES — les
    pièces de phase sont au nombre de cent-huit, et les verser au menu déroulant
    de la console le rendrait inutilisable. Sans ce paramètre, l'historique les
    enregistrait sous leur identifiant technique.
    """
    model = "mistral" if data.get("model") == "mistral" else "claude"
    query = (livrables.retrieval_query(type_id, data) + " " + extra_query).strip()
    # Documents de référence choisis manuellement (facultatif) ; sinon récupération auto.
    doc_ids = [d for d in (data.get("doc_ids") or []) if _rag_valid_doc_id(d)]
    # Version parente (chaînage des itérations) — présent lors d'un affinage.
    parent_id = data.get("parent_id")
    parent_id = parent_id if _rag_valid_doc_id(parent_id) else None
    hits = []
    try:
        if doc_ids:
            # Documents choisis manuellement : on respecte la sélection (pas de
            # re-classement qui écarterait des extraits voulus).
            hits = rag.search(query, k=8, public_only=False, doc_ids=doc_ids)
        else:
            # Récupération LARGE puis re-classement par LLM-juge → les 8 extraits
            # les plus pertinents avant génération (précision accrue). Repli sûr
            # (sans clé API ou en cas d'échec : simple troncature).
            hits = assistant.rerank(model, query,
                                    rag.search(query, k=24, public_only=False), 8)
    except Exception:
        hits = []
    context = build_context(hits, max_chars=6000)

    # Regroupement des extraits par DOCUMENT : le modèle reçoit ainsi la liste
    # nominative de ce qui l'alimente (et non des extraits anonymes), et la même
    # liste sert à sourcer le document exporté. Une seule source de vérité.
    sources, rang = [], {}
    for h in hits:
        did = h.get("doc_id")
        if did in rang:
            sources[rang[did]]["extraits"] += 1
            continue
        rang[did] = len(sources)
        sources.append({"title": h.get("title"), "theme": h.get("theme"),
                        "visibility": h.get("visibility"), "extraits": 1})
    user = user + livrables.dossier_documentaire(sources, choix_manuel=bool(doc_ids))

    try:
        text, used_model = assistant.generate(model, system, user, context=context)
    except assistant.AssistantError as exc:
        return jsonify(ok=False, error=exc.code,
                       message=_ASSISTANT_MSG.get(exc.code, "Génération indisponible.")), exc.status

    # Enregistrement dans l'historique (best-effort : n'interrompt jamais la réponse).
    saved_id = None
    try:
        t = livrables.get_type(type_id)
        saved_id = livrables_hist.save({
            "type": type_id, "label": (t["label"] if t else None) or label or type_id,
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


@app.route("/api/admin/datacenter/piece", methods=["POST"])
@admin_required
def api_datacenter_piece():
    """Rédige une pièce du registre de phase, ancrée sur la base de connaissance.

    Même verrou que la génération de livrables : la rédaction consomme des jetons
    d'API et écrit dans l'historique. Le REGISTRE, lui, reste consultable par tout
    compte connecté — c'est la référence, et la garder derrière le verrou
    d'administration la rendrait inutile à qui monte un dossier.

    Les prompts sont construits par ingenierie_dc : ils portent la frontière entre
    grandeurs acquises et grandeurs à produire, et cette frontière est calculée,
    pas rédigée.
    """
    ckey = "gen:%s" % client_ip()
    if guard.blocked(ckey, limit=12, window=600):
        return jsonify(ok=False, error="rate_limited",
                       message="Trop de générations en peu de temps. Patientez quelques minutes."), 429
    guard.fail(ckey)
    data = request.get_json(silent=True) or {}
    profil = _profil_datacenter(data)
    phase = str(data.get("phase") or "").strip().upper()[:12]
    code = str(data.get("piece") or "").strip().upper()[:16]
    if not profil.get("puissance_it_kw"):
        return jsonify(ok=False, error="puissance_absente",
                       message="La puissance informatique installée est nécessaire."), 400
    try:
        prompts = ingenierie_dc.prompts_piece(profil, phase, code, data)
    except Exception:
        app.logger.exception("prompts pièce datacenter")
        return jsonify(ok=False, error="calcul",
                       message="La pièce n'a pas pu être préparée."), 500
    if not prompts:
        return jsonify(ok=False, error="piece_inconnue",
                       message="Phase ou pièce inconnue."), 404
    system, user, requete = prompts
    pc = ingenierie_dc.piece(phase, code)
    audit.journaliser("datacenter.piece", cible="%s/%s" % (phase, code),
                      detail=pc["titre"][:120])
    return _livrables_run("dc-piece-%s-%s" % (phase.lower(), code.lower()),
                          data, system, user, extra_query=requete,
                          label="%s %s — %s" % (phase, pc["code"], pc["titre"]))


@app.route("/api/admin/livrables/preview-docs", methods=["POST"])
@admin_required
def api_livrables_preview_docs():
    """Documents que la sélection AUTOMATIQUE retiendrait pour le type courant.

    Le sélecteur « Documents de référence » liste toute la base et ne bouge pas
    quand on change de type — ce qui laisse croire que le type n'influence rien.
    Il l'influence en réalité côté serveur, au moment de la génération. Cette
    route rend ce mécanisme visible en rejouant EXACTEMENT les mêmes étapes que
    _livrables_run (même requête, même k, même re-classement), de sorte que
    l'aperçu ne puisse pas mentir sur ce qui sera réellement mobilisé."""
    ckey = "prev:%s" % client_ip()
    if guard.blocked(ckey, limit=30, window=600):
        return jsonify(ok=False, error="rate_limited",
                       message="Trop d'aperçus en peu de temps. Patientez un instant."), 429
    guard.fail(ckey)
    data = request.get_json(silent=True) or {}
    type_id = (data.get("type") or "").strip()
    if not livrables.get_type(type_id):
        return jsonify(ok=False, error="type_inconnu", message="Type de livrable inconnu."), 400
    model = "mistral" if data.get("model") == "mistral" else "claude"
    query = livrables.retrieval_query(type_id, data)
    try:
        hits = assistant.rerank(model, query,
                                rag.search(query, k=24, public_only=False), 8)
    except Exception as exc:
        return jsonify(ok=False, error="apercu_echec", detail=_exc_detail(exc)), 500
    # Un document peut fournir plusieurs extraits : on regroupe par document en
    # conservant l'ordre de pertinence et en comptant les extraits retenus.
    docs, rang = [], {}
    for h in hits:
        did = h.get("doc_id")
        if did in rang:
            docs[rang[did]]["extraits"] += 1
            continue
        rang[did] = len(docs)
        docs.append({"id": did, "title": h.get("title"), "theme": h.get("theme"),
                     "visibility": h.get("visibility"), "extraits": 1})
    return jsonify(ok=True, query=query, documents=docs, extraits=len(hits))


@app.route("/api/datacenter/depot/etat", methods=["GET"])
@login_required
def api_depot_etat():
    """Ce que vaut la chaîne d'analyse en ce moment.

    Affiché AVANT le dépôt : celui qui confie un document a le droit de savoir
    ce qui lui sera réellement appliqué. Écrire « analyse antivirus » sur un
    serveur qui n'en a pas serait la pire des assurances — celle qui ne se
    vérifie jamais.
    """
    import antivirus
    e = antivirus.etat()
    # Deux plafonds réglés à deux endroits : celui du document (antivirus) et
    # celui du corps de requête (ici). Ils divergeront un jour — autant que la
    # page le sache et le dise, plutôt que de laisser un dépôt échouer au
    # transport avec un message parlant de la requête et non du document.
    e["transport_suffisant"] = (
        antivirus.MAX_OCTETS * antivirus.SURCOUT_BASE64 <= RAG_UPLOAD_MAX)
    if not e["transport_suffisant"]:
        e["resume"] += (" ATTENTION : le plafond de dépôt (%d Mo) dépasse ce que "
                        "le serveur accepte en une requête ; les fichiers les "
                        "plus gros échoueront au transport."
                        % (antivirus.MAX_OCTETS // (1024 * 1024)))
    return jsonify(ok=True, etat=e)


@app.route("/api/datacenter/depot", methods=["POST"])
@admin_required
def api_depot_verser():
    """Dépose un document client, après analyse.

    Verrou d'administration, et non simple session : un document déposé
    alimente les études et peut être versé à la base de connaissance. Ouvrir ce
    geste à tout compte connecté reviendrait à laisser n'importe qui écrire
    dans ce qui nourrit les livrables.

    Le document est enregistré en visibilité INTERNE : il ne devient pas
    public du seul fait d'avoir été déposé.
    """
    import antivirus
    ckey = "depot:%s" % client_ip()
    if guard.blocked(ckey, limit=30, window=600):
        return jsonify(ok=False, error="rate_limited",
                       message="Trop de dépôts en peu de temps. Patientez un instant."), 429
    guard.fail(ckey)
    data = request.get_json(silent=True) or {}
    nom = (data.get("filename") or "").strip()[:200]
    b64 = data.get("contenu") or ""
    if not nom or not b64:
        return jsonify(ok=False, error="incomplet",
                       message="Nom de fichier et contenu sont nécessaires."), 400
    try:
        import base64
        octets = base64.b64decode(b64, validate=True)
    except Exception:
        return jsonify(ok=False, error="contenu_illisible",
                       message="Le contenu transmis n'est pas décodable."), 400
    verdict = antivirus.analyser(nom, octets)
    audit.journaliser("depot.analyse", cible=nom[:120],
                      detail="%s · portes=%s"
                             % ("accepté" if verdict["accepte"] else
                                "REFUSÉ:" + verdict.get("code", "?"),
                                ",".join(verdict.get("portes") or [])))
    if not verdict["accepte"]:
        return jsonify(ok=False, error="analyse_refus", analyse=verdict,
                       message=verdict["motif"]), 422
    try:
        doc = rag.ingest_bytes(nom, octets,
                               title=(data.get("titre") or nom).strip()[:200],
                               theme=(data.get("theme") or "datacenter").strip()[:60],
                               visibility="internal")
    except RagError as exc:
        # Le motif RÉEL, pas un message passe-partout. « Le document n'a pas pu
        # être enregistré » fait recommencer à l'identique ; « ce PDF ne contient
        # aucun texte extractible » dit quoi faire. Le cas le plus fréquent est
        # le plan ou le document scanné : il est légitime, et le dépôt le refuse
        # aujourd'hui parce qu'il passe par l'indexation de la base de
        # connaissance, qui a besoin de texte.
        _MOTIFS = {
            "pdf_illisible": "Ce PDF ne contient aucun texte extractible — c'est "
                             "le cas des plans et des documents scannés. Le dépôt "
                             "passe par l'indexation documentaire, qui a besoin de "
                             "texte : fournissez une version avec couche texte "
                             "(OCR) ou le fichier source.",
            "fichier_vide": "Le fichier est vide.",
            "fichier_trop_lourd": "Le fichier dépasse le plafond de dépôt.",
            "type_non_supporte": "Ce format n'est pas indexable par la base de "
                                 "connaissance.",
            "doublon": "Ce document est déjà présent, à l'identique.",
        }
        return jsonify(ok=False, error=exc.code,
                       message=_MOTIFS.get(exc.code)
                       or getattr(exc, "detail", "")
                       or "Le document n'a pas pu être enregistré (%s)." % exc.code
                       ), exc.status
    audit.journaliser("depot.verse", cible=str(doc.get("id"))[:80],
                      detail=nom[:120])
    return jsonify(ok=True, document=doc, analyse=verdict)


@app.route("/api/datacenter/ingenierie/guide", methods=["POST"])
@login_required
def api_datacenter_guide():
    """Le parcours d'un rôle sur un thème, avec ce que le registre en dit.

    Calculé à chaque appel plutôt que servi figé : les chiffres qu'il porte —
    pièces du thème à cette phase, part alimentée par le calcul, grandeurs
    encore à produire — dépendent du profil saisi et de la phase regardée. Les
    figer reviendrait à afficher les chiffres d'un autre projet.
    """
    data = request.get_json(silent=True) or {}
    role = str(data.get("role") or "").strip()[:32]
    theme = str(data.get("theme") or "").strip()[:32]
    phase = str(data.get("phase") or "").strip().upper()[:12] or None
    profil = _profil_datacenter(data)
    try:
        g = ingenierie_dc.guide(role, theme, profil, phase)
    except Exception:
        app.logger.exception("guide ingénierie datacenter")
        return jsonify(ok=False, error="calcul",
                       message="Le parcours n'a pas pu être établi."), 500
    if not g:
        return jsonify(ok=False, error="inconnu",
                       message="Rôle ou thème inconnu."), 404
    return jsonify(ok=True, guide=g)


@app.route("/api/datacenter/ingenierie/apercu", methods=["POST"])
@login_required
def api_datacenter_piece_apercu():
    """Ce que la base de connaissance apporterait à cette pièce — avant de rédiger.

    « Adossé à la base de connaissance » est une affirmation ; celle-ci la rend
    vérifiable. On rejoue EXACTEMENT les étapes de _livrables_run — même requête,
    même k, même re-classement — de sorte que l'aperçu ne puisse pas mentir sur ce
    qui sera réellement mobilisé.

    Ouvert à tout compte connecté, contrairement à la rédaction : consulter ce
    que la base contient ne consomme pas de jetons d'API et ne produit rien. Ce
    qui coûte, c'est d'écrire — et c'est cela qui reste derrière le verrou
    d'administration.
    """
    ckey = "apercupc:%s" % client_ip()
    if guard.blocked(ckey, limit=40, window=600):
        return jsonify(ok=False, error="rate_limited",
                       message="Trop d'aperçus en peu de temps. Patientez un instant."), 429
    guard.fail(ckey)
    data = request.get_json(silent=True) or {}
    phase = str(data.get("phase") or "").strip().upper()[:12]
    code = str(data.get("piece") or "").strip().upper()[:16]
    pc = ingenierie_dc.piece(phase, code)
    if not pc:
        return jsonify(ok=False, error="piece_inconnue",
                       message="Phase ou pièce inconnue."), 404
    query = ingenierie_dc.requete_piece(phase, code, data)
    model = "mistral" if data.get("model") == "mistral" else "claude"
    try:
        hits = assistant.rerank(model, query,
                                rag.search(query, k=24, public_only=False), 8)
    except Exception:
        # Un aperçu qui échoue ne doit pas passer pour une base vide : les deux
        # se ressemblent à l'écran et n'appellent pas la même réaction.
        app.logger.exception("aperçu pièce datacenter")
        return jsonify(ok=False, error="apercu_echec",
                       message="La base n'a pas pu être interrogée."), 500
    docs, rang = [], {}
    for h in hits:
        did = h.get("doc_id")
        if did in rang:
            docs[rang[did]]["extraits"] += 1
            continue
        rang[did] = len(docs)
        docs.append({"title": h.get("title"), "theme": h.get("theme"),
                     "visibility": h.get("visibility"), "extraits": 1})
    return jsonify(ok=True, query=query, documents=docs, extraits=len(hits),
                   origine=pc.get("recherche_origine"),
                   piece="%s — %s" % (pc["code"], pc["titre"]))


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
    """Exporte un livrable (Markdown) en Word (.docx) ou PDF mis en page CONSEILPREV.

    Corps JSON : {markdown, type, client, format?} — format « docx » (défaut) ou « pdf »."""
    data = request.get_json(silent=True) or {}
    md = (data.get("markdown") or "").strip()
    if not md:
        return jsonify(ok=False, error="vide", message="Aucun contenu à exporter."), 400
    fmt = (data.get("format") or "docx").strip().lower()
    if fmt not in ("docx", "pdf"):
        fmt = "docx"
    # Ces informations existaient côté application mais n'atteignaient pas le
    # document : `meta` était transmis puis ignoré par les deux constructeurs.
    # Elles alimentent désormais le bloc de garde et l'annexe des sources.
    t = livrables.get_type((data.get("type") or "").strip())
    srcs = [s for s in (data.get("sources") or []) if isinstance(s, dict)][:40]
    meta = {"type": data.get("type"),
            "label": t["label"] if t else (data.get("type") or "Livrable"),
            "client": data.get("client"), "secteur": data.get("secteur"),
            "perimetre": data.get("perimetre"), "model": data.get("model"),
            "date": time.strftime("%d/%m/%Y"),
            "sources": srcs}
    try:
        if fmt == "pdf":
            blob = livrables_export.build_pdf(md, meta)
            mimetype = "application/pdf"
        else:
            blob = livrables_export.build_docx(md, meta)
            mimetype = ("application/vnd.openxmlformats-officedocument"
                        ".wordprocessingml.document")
    except Exception:
        return jsonify(ok=False, error="export_echec",
                       message="La mise en page a échoué."), 500
    type_id = (data.get("type") or "livrable")
    if not type_id or not all(c.isalnum() or c in "-_" for c in type_id):
        type_id = "livrable"
    return send_file(
        io.BytesIO(blob), download_name=type_id + "." + fmt, as_attachment=True,
        mimetype=mimetype)


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
    if not _token_ok(request.headers.get("X-Ingest-Token"), token):
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


# Formats de pièces jointes clients acceptés (documents contractuels) : tout le
# reste est refusé dès l'ouverture de l'upload — pas d'exécutable ni de page
# web dans les dossiers clients.
_PIECES_EXT = {"pdf", "doc", "docx", "odt", "rtf", "txt", "md", "csv",
               "xls", "xlsx", "png", "jpg", "jpeg"}


def _piece_ext_ok(filename):
    return "." in filename and filename.rsplit(".", 1)[-1].lower() in _PIECES_EXT


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
    if not _piece_ext_ok(filename):
        return jsonify(ok=False, error="format_non_autorise",
                       message="Formats acceptés : PDF, Word (doc/docx), ODT, RTF, "
                               "texte (txt/md), CSV, Excel (xls/xlsx), PNG/JPG."), 400
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
    filename = (data.get("filename") or "").strip()
    if filename and not _piece_ext_ok(filename):
        return jsonify(ok=False, error="format_non_autorise",
                       message="Format de fichier non autorisé."), 400
    try:
        doc = clients_db.doc_upload_finish(cid, upload_id, (data.get("categorie") or "").strip(),
                                           actor=_actor(), filename=filename)
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
    return _blob_response(filename, data)


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
    """Dossier de conformité complet : registre, classification IA Act, mesures,
    droits, analyse d'impact et actions ouvertes.

    Réservé à l'administration parce qu'il porte les ACTIONS ouvertes — la part
    du dossier qui dit ce qui reste à faire. La version publique (/api/conformite)
    présente les mêmes faits sans cette feuille de route interne.
    """
    etat = rgpd.etat()
    etat["journal"] = audit.etat()          # durée de conservation réellement appliquée
    return jsonify(ok=True, **etat)


@app.route("/api/conformite", methods=["GET"])
def api_conformite():
    """Dossier de conformité, version publique — même source, sans les actions.

    Publier le registre est un choix : l'art. 30 n'oblige pas à le rendre public.
    Mais un client à qui l'on vend de la conformité est fondé à vérifier celle du
    prestataire, et un registre qu'on accepte de publier est un registre qu'on
    tient à jour.
    """
    etat = rgpd.etat()
    etat.pop("actions", None)
    return jsonify(ok=True, **etat)


@app.route("/offre-conseilprev-cyber.pdf")
def offre_pdf():
    """Plaquette PDF de l'offre (publique) — servie depuis le cache mémoire avec
    ETag/304 et cache navigateur 24 h (un PDF est déjà compressé : pas de gzip)."""
    return _serve_fast("offre-conseilprev-cyber.pdf", _CC_IMAGE,
                       mimetype="application/pdf", gzippable=False)


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
    if not _token_ok(request.headers.get("X-Ingest-Token"), INGEST_TOKEN):
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
    if not _token_ok(request.headers.get("X-Ingest-Token"), INGEST_TOKEN):
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
    if not _token_ok(request.headers.get("X-Ingest-Token"), INGEST_TOKEN):
        return jsonify(ok=False, error="unauthorized"), 401
    days = request.args.get("retention_days", type=float) or _RETENTION_DAYS
    max_rows = request.args.get("max_rows", type=int) or _MAX_ROWS
    deleted = state.purge(retention_days=days or None, max_rows=max_rows or None,
                          archive_path=_ARCHIVE_PATH)
    return jsonify(ok=True, deleted=deleted)


def _cause_publique(txt):
    """Cause d'indisponibilité montrable sur une page publique : on retire ce
    qui DÉSIGNE la base (hôte, adresse IP, port, URL, mot de passe) et on garde
    ce qui l'EXPLIQUE (refusée, délai dépassé, plafond atteint)."""
    import re as _re                     # `re` n'est pas importé au niveau module
    t = " ".join(str(txt or "").split())
    t = _re.sub(r"postgres(?:ql)?://\S+", "la base", t)
    t = _re.sub(r"password=\S+", "password=…", t)
    t = _re.sub(r'\bat\s+"[^"]+"\s*(\([^)]*\))?', "at …", t)   # at "hote" (10.0.0.5)
    t = _re.sub(r"\bport\s+\d+", "port …", t)
    t = _re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "…", t)        # adresses IPv4 restantes
    t = _re.sub(r"\b[\w-]+\.(?:com|net|org|io|dev|internal)\b", "…", t)
    return " ".join(t.split())[:220]


@app.route("/health")
def health():
    """Point de santé (utilisé par Render pour vérifier le service).

    Renvoie l'état RÉEL des dépendances, et non un « ok » inconditionnel qui
    n'apprenait rien : on voit désormais si la base répond, si la recherche est
    vectorielle ou plein-texte, et quelle version est en ligne.

    Le code reste 200 tant que le site SERT ses pages, même base injoignable :
    l'application sait fonctionner en mode dégradé, et répondre 503 ferait
    redémarrer l'instance en boucle sur un simple hoquet de la base — on
    remplacerait une gêne par une coupure. L'état dégradé est dans le corps, à
    la disposition de la supervision."""
    # Ancienneté du processus : c'est le moyen le plus simple de CONSTATER des
    # redémarrages à répétition depuis l'extérieur. Si ce compteur repart de zéro
    # à chaque consultation, l'instance redémarre — et tout ce qui vit en mémoire
    # (caches, session de secours) est perdu à chaque fois.
    etat = {"status": "ok", "service": "conseilprevcyber", "version": APP_VERSION,
            "demarre_depuis_s": int(time.time() - _DEMARRAGE)}
    try:
        caps = rag.capabilities()
        etat["base"] = "connectee" if caps.get("persistent") else "degradee"
        etat["recherche"] = caps.get("mode")
        if not caps.get("persistent"):
            etat["status"] = "degraded"
            etat["cause"] = caps.get("reason") or "base_indisponible"
    except Exception:
        etat["status"] = "degraded"
        etat["base"] = "inconnue"
    # Magasin de comptes : simple lecture d'un attribut en mémoire, aucune requête.
    try:
        import auth as _auth
        etat["comptes"] = getattr(_auth.store, "mode", "inconnu")
        if etat["comptes"] != "postgres":
            etat["status"] = "degraded"
    except Exception:
        etat["comptes"] = "inconnu"
    # État par magasin, AVEC LA CAUSE. Sans lui, un mode dégradé se constatait
    # mais ne se diagnostiquait pas : « la connexion échoue » envoyait vérifier
    # DATABASE_URL alors qu'elle était correcte. Ces champs disent quoi
    # regarder — plafond de connexions, base suspendue, URL périmée — et à
    # quand le prochain essai automatique.
    magasins = {}
    # Le magasin de COMPTES figure ici comme les autres. Il en était absent, et
    # c'était le plus gênant : c'est le seul dont la panne empêche de se
    # connecter pour aller consulter le diagnostic. Sa cause doit donc être
    # lisible sans compte, depuis cette page publique.
    try:
        import auth as _auth_etat
        if hasattr(_auth_etat.store, "etat"):
            magasins["comptes"] = _auth_etat.store.etat()
            if not magasins["comptes"].get("persistant", True):
                etat["status"] = "degraded"
    except Exception:
        magasins["comptes"] = {"persistant": None, "cause": "état non lisible"}
    for nom, mag in (("documents", rag), ("clients", clients_db),
                     ("livrables", livrables_hist)):
        try:
            if hasattr(mag, "etat"):
                magasins[nom] = mag.etat()
            else:
                magasins[nom] = {"persistant": bool(getattr(mag, "persistent", False)),
                                 "cause": str(getattr(mag, "_last_error", "") or "")[:200]}
            if not magasins[nom].get("persistant", True):
                etat["status"] = "degraded"
        except Exception:
            magasins[nom] = {"persistant": None, "cause": "état non lisible"}
    # /health est PUBLIC. Les causes remontées telles quelles par les pilotes
    # PostgreSQL nomment l'hôte et le port de la base — « connection to server
    # at "dpg-….render.com" (10.0.0.5), port 5432 failed ». Cela désigne à
    # n'importe qui la cible à attaquer, sans rien apprendre à l'exploitant que
    # « connexion refusée » ne dise déjà. On assainit ici, à la publication :
    # une seule place, valable aussi pour les magasins ajoutés plus tard.
    for m in magasins.values():
        if isinstance(m, dict) and m.get("cause"):
            m["cause"] = _cause_publique(m["cause"])
    etat["magasins"] = magasins

    # Le playbook contractuel se contrôle lui-même : un motif cassé ou un thème
    # du clausier sans règle ferait taire une détection EN SILENCE, et un
    # contrat passerait pour propre parce qu'on ne l'a pas regardé. C'est
    # exactement le genre de panne qui ne se voit pas à l'usage.
    try:
        sp = playbook.sante()
        etat["playbook"] = {"version": sp["version"], "ok": sp["ok"],
                            "themes": "%d/%d" % (sp["themes_outilles"], sp["themes_clausier"]),
                            "motifs": sp["motifs"]}
        if not sp["ok"]:
            etat["status"] = "degraded"
            etat["playbook"]["cause"] = (sp["motifs_casses"] or sp["sans_regle"]
                                         or sp["instances_inconnues"])[:3]
    except Exception:
        etat["playbook"] = {"ok": None, "cause": "état non lisible"}

    if request.args.get("detail") == "1":
        etat.update(_sonde_detaillee())
        if etat.get("comptes_lecture", "").startswith("echec"):
            etat["status"] = "degraded"
    return jsonify(**etat), 200


_SONDE = {"ts": 0.0, "res": {}}
_SONDE_TTL = 30.0


def _sonde_detaillee():
    """Sonde approfondie de /health?detail=1 : tente réellement une lecture de la
    base de comptes et compte les connexions ouvertes.

    Elle existe pour une situation précise et pénible : quand la base de comptes
    ne répond plus, PERSONNE ne peut se connecter — donc personne ne peut ouvrir
    le diagnostic d'administration, qui se trouve justement derrière la
    connexion. Sans sonde publique, on reste dehors sans savoir pourquoi.

    Deux précautions. Le résultat est mis en cache 30 s : sans cela, rafraîchir
    la page suffirait à faire marteler la base — on offrirait un levier de
    nuisance sur la ressource déjà en peine. Et il ne sort d'ici QUE des états et
    des nombres : jamais un hôte, une URL, un identifiant, ni la moindre donnée
    de compte."""
    now = time.time()
    if now - _SONDE["ts"] < _SONDE_TTL and _SONDE["res"]:
        return dict(_SONDE["res"], mesure="en cache (< 30 s)")
    def _cause(exc):
        """Cause EXPLOITABLE mais muette sur l'infrastructure.

        _exc_detail suffit sur les routes d'administration, mais pas ici : les
        messages de psycopg citent l'hôte et le port en clair (« connection to
        server at "dpg-…", port 5432 »), et cette sonde est PUBLIQUE. On ne
        publie donc que le TYPE de l'erreur — assez pour distinguer un délai
        d'attente d'un refus, jamais assez pour cartographier le service."""
        return type(exc).__name__

    res = {}
    try:
        import auth as _auth
        t0 = time.time()
        # Adresse volontairement inexistante : on teste le CHEMIN d'accès, pas un
        # compte réel — aucune information sur les comptes ne peut fuir.
        _auth.store.get("sonde-disponibilite@invalide.local")
        res["comptes_lecture"] = "ok (%d ms)" % ((time.time() - t0) * 1000)
    except Exception as exc:
        res["comptes_lecture"] = "echec : %s" % _cause(exc)
    # Nombre de fois où le pool n'a pas rendu la main et où l'on est passé par
    # une connexion directe. Un compteur qui grimpe désigne le pool, et non la
    # base : c'est la distinction que la sonde précédente ne permettait pas.
    try:
        n = getattr(getattr(_auth.store, "_pg", None), "replis_directs", None)
        if n is not None:
            res["replis_directs"] = n
    except Exception:
        pass
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        res["connexions"] = "DATABASE_URL absente de l'environnement"
    else:
        try:
            import psycopg
            with psycopg.connect(dsn, connect_timeout=6, autocommit=True) as c:
                used = c.execute("SELECT count(*) FROM pg_stat_activity "
                                 "WHERE datname=current_database()").fetchone()[0]
                cap = int(c.execute("SHOW max_connections").fetchone()[0])
            res["connexions"] = "%d/%d" % (used, cap)
            if cap and used * 100 // cap >= 85:
                res["alerte"] = ("plafond de connexions proche : c'est ce qui fait "
                                 "échouer les nouvelles connexions")
        except Exception as exc:
            res["connexions"] = "non mesurable : %s" % _cause(exc)
    _SONDE["ts"], _SONDE["res"] = now, res
    return dict(res, mesure="à l'instant")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
