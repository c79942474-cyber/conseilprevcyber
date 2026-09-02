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
import math
import json
import os
import io
import queue
import threading
import time
import zipfile

from urllib.parse import urlparse

import requests
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import (Flask, Response, abort, jsonify, redirect, request,
                   send_file, send_from_directory, stream_with_context)

import acces          # qui voit quoi — la politique d'accès, écrite une fois
import assistant
import audit
import automation
import juridique
import librejustice   # corpus de jurisprudence, branché par MCP — voir le module
import livrables
import rag_federe   # la base sœur, mêlée à la nôtre — voir le module
import reglages   # un réglage illisible ne doit pas arrêter le service
import veille_facettes   # les six axes de la veille — voir le module
import veille_sources    # le catalogue des flux, et leur santé
import livrables_export
import playbook
import minimisation
import conformite_mesures
import rgpd
from auth import admin_required, client_ip, current_user, guard, init_app as init_auth
from clients_store import (BASES_LEGALES, CATEGORIES_PIECES, STATUTS,
                           ClientsError, make_clients_store)
import csp          # la politique de contenu, calculée sur ce qui est servi
from cockpit_state import make_store, tag_for
from livrables_store import make_livrables_store
from rag_store import (RagError, THEMES, THEME_FAMILLES, FAMILLE_ENTREPRISES,
                       FAMILLE_ENGINEERING, build_context, build_context_retenus,
                       dedupe as rag_dedupe,
                       diagnose as rag_diagnose, duplicate_groups,
                       extract_text as rag_extract_text,
                       formats_available, make_rag_store)

app = Flask(__name__)
# Render place l'application derrière SON PROPRE proxy, qui AJOUTE la vraie IP
# du client à droite de X-Forwarded-For — un en-tête que l'appelant, lui,
# contrôle intégralement. Sans ce correctif, request.remote_addr valait la
# première valeur de l'en-tête, c'est-à-dire exactement celle qu'un attaquant
# écrit : chaque limiteur de débit keyé sur l'IP (connexion, portail admin,
# formulaire de contact…) s'annulait en incrémentant un octet par requête.
# x_for=1 : on ne fait confiance qu'À UN SEUL relais, celui de Render, et
# request.remote_addr redevient la dernière valeur de la chaîne — celle que
# l'appelant ne peut pas écrire.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
HERE = os.path.dirname(os.path.abspath(__file__))

# Version applicative affichée dans l'admin (auto-test de la base de connaissance).
# Sert à vérifier d'un coup d'œil QUELLE version tourne réellement en production :
# si le numéro affiché est plus ancien que la version attendue, le déploiement n'a
# pas abouti — et aucun correctif récent n'est en ligne. À incrémenter à chaque
# correctif dont on veut pouvoir confirmer la mise en ligne.
APP_VERSION = "2026.08.06-01"

# LE COMMIT RÉELLEMENT EN LIGNE. Un numéro de version tenu à la main répond mal
# à la seule question qui se pose après un déploiement — « la correction est-
# elle en ligne ? » — parce qu'on oublie de l'incrémenter, et parce qu'il ne
# dit pas LAQUELLE des corrections est passée. L'hébergeur, lui, injecte le
# commit déployé dans l'environnement : c'est une réponse qui ne peut pas
# mentir. Sans elle, on devine en observant le comportement, et on confond une
# correction absente avec une correction inopérante — deux causes qui
# n'appellent pas du tout le même geste.
_COMMIT = (os.environ.get("RENDER_GIT_COMMIT")
           or os.environ.get("GIT_COMMIT") or "")[:12]
_BRANCHE = os.environ.get("RENDER_GIT_BRANCH") or ""

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
    # Mettre en page un document coûte du temps de calcul — une centaine de
    # pages de PDF tiennent un fil pendant plusieurs secondes. Le plafond est
    # large pour l'usage réel (on n'exporte pas trente fois par minute) et
    # ferme pour l'abus, qui figerait le site pour tout le monde.
    "/api/datacenter/piece/export":      (30, 60),
    "/api/datacenter/ingenierie/export": (30, 60),
    # LES QUATRE POINTS À JETON. Le compteur d'ÉCHECS (voir `_jeton_refus`)
    # arrête la force brute ; il ne borne pas une inondation menée AVEC le bon
    # jeton — un connecteur en boucle, ou un secret ayant fuité. Ces plafonds
    # sont larges pour l'usage réel d'une automatisation et fermes pour l'abus.
    # /api/rag/ingest est le plus serré des quatre : il ÉCRIT dans la base de
    # connaissance, et c'est le chemin d'empoisonnement le plus court du site.
    "/api/rag/ingest":         (60, 60),
    "/api/ingest":             (240, 60),
    "/api/reset":              (10, 3600),
    "/api/maintenance/purge":  (10, 3600),
    # LES EXPORTS HORS FAMILLE SURVEILLÉE. Mettre en page un document tient un
    # fil pendant plusieurs secondes ; ceux-ci étaient les seuls à ne porter
    # aucun plafond, alors que leurs jumeaux de /api/datacenter/ en ont un.
    "/api/juridique/export":   (30, 60),
    "/api/playbook/export":    (30, 60),
    "/api/62443/checklist/emporter": (30, 60),
    "/api/maturite-ot/emporter":     (30, 60),
}
_RATE_EXACT.update({
    # ── DEUX JETONS QUI SE FORÇAIENT EN AVEUGLE ─────────────────────────────
    # Ces deux points vérifient un jeton d'en-tête, et rien d'autre. Ils
    # tombaient hors des trois familles surveillées : un attaquant pouvait donc
    # essayer des jetons SANS AUCUNE LIMITE, aussi vite que le réseau le
    # permettait. Un secret qu'on peut essayer sans être compté n'est plus un
    # secret, c'est un délai.
    #
    # « /api/rag/ingest » écrit DANS LA BASE DE CONNAISSANCE : le jeton forcé
    # y verse ce qu'il veut, et ce qu'on y verse ressort dans les réponses de
    # l'assistant et dans les livrables. C'est le chemin d'empoisonnement le
    # plus court du site.
    "/api/rag/ingest": (30, 300),
    "/api/ingest":     (600, 60),   # flux d'événements OT : légitimement dense
})

_RATE_FAMILY = (("/api/auth/", 80, 60), ("/api/admin/", 600, 60),
                # Le calcul de durabilite est desormais OUVERT, sans compte. Il
                # ne coute ni modele de langage ni ecriture, mais il coute du
                # temps processeur : une etude enchaine energie, eau, carbone,
                # chaleur, conformite et leviers. Ouvrir une surface de calcul
                # sans plafond revient a offrir un amplificateur a qui veut
                # saturer le service. Le plafond est large pour l'usage reel —
                # personne ne relance une etude cent fois par minute a la main —
                # et il ne genera qu'une boucle automatique.
                ("/api/datacenter/", 120, 60),
                # LES AUTRES SURFACES DE CALCUL, découvertes au relevé du
                # 29 août : quatre-vingt-sept routes POST, douze sans aucun
                # plafond. Une checklist 62443, une évaluation de maturité OT
                # et une qualification juridique coûtent chacune du temps
                # processeur sans écrire ni appeler de modèle — c'est-à-dire
                # exactement le profil qu'on amplifie pour saturer un service.
                ("/api/62443/", 120, 60),
                ("/api/maturite-ot/", 120, 60),
                ("/api/juridique/", 120, 60),
                ("/api/playbook/", 120, 60))

# Points protégés par jeton (server-to-server) : exemptés du contrôle d'origine
# CSRF, car authentifiés par un secret d'en-tête (X-Ingest-Token) et non par un
# cookie de session — donc non vulnérables au CSRF (qui exploite le cookie ambiant).
_CSRF_EXEMPT = {"/api/ingest", "/api/reset", "/api/maintenance/purge", "/api/rag/ingest",
                # RECHERCHE FÉDÉRÉE — appel serveur à serveur depuis CONSEILPREV.
                # Exemptée pour une raison différente des précédentes : elle ne
                # lit AUCUN cookie et n'écrit rien, donc il n'y a pas de session
                # à détourner. Elle est réservée par clé partagée et ne sert que
                # des documents publics (voir api_rag_search_federe).
                "/api/rag/search",
                # STRIPE N'ENVOIE NI « Origin » NI « Referer », et ne peut
                # pas porter notre en-tête maison. Sans cette ligne,
                # chaque notification de paiement serait rejetée en 403 :
                # les paiements passeraient, aucun accès ne s'ouvrirait, et
                # Stripe réessaierait pendant trois jours. L'exemption est
                # celle que ce garde nomme déjà — authentifié par secret,
                # pas par cookie : ici, la signature de la charge.
                "/api/stripe/webhook"}

# En-tête maison posé par nos propres appels d'écriture (voir _same_origin_request).
# Un site tiers ne peut pas le poser sans pré-vérification CORS — que ce service
# n'accorde jamais : il constitue donc une preuve de même origine, utile quand le
# navigateur n'envoie ni « Origin » ni « Referer ».
_CSRF_HEADER = "X-CP-Same-Origin"
_CSRF_HEADER_VALUE = "1"

# En-têtes de sécurité appliqués à toutes les réponses.
#
# `script-src` N'ADMET PLUS L'EXÉCUTION EN LIGNE. Tant qu'elle l'admettait,
# l'échappement était la seule défense contre l'injection de balisage : un seul
# oubli — il y en avait un sur les liens de flux — devenait directement
# exploitable. Les pages qui portent des scripts intégrés reçoivent leur propre
# politique, avec les EMPREINTES de ces scripts, posée par `_serve_fast` ; le
# crochet ci-dessous emploie `setdefault` et ne l'écrase donc pas.
#
# `style-src` garde l'exécution en ligne, délibérément : un style ne s'exécute
# pas, et mille trente-quatre attributs `style=` pour un risque marginal serait
# un mauvais échange.
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), interest-cohort=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Content-Security-Policy": csp.sans_script_en_ligne(),
}


def _request_is_https():
    return request.is_secure or request.headers.get("X-Forwarded-Proto", "") == "https"


def _token_ok(provided, expected):
    """Comparaison en temps constant du jeton d'ingestion (hmac.compare_digest) :
    un attaquant ne peut pas reconstituer le jeton octet par octet en mesurant
    les délais de réponse.

    UN JETON PEUT AUSSI CONTENIR DU NON-ASCII, et `compare_digest` LÈVE dans ce
    cas au lieu de rendre faux : la route rendrait 500 sur une vérification
    d'authentification, ce qui envoie chercher une panne au lieu d'une clé mal
    formée. Un jeton qu'on ne peut pas comparer n'est pas un jeton valide."""
    if not expected:
        return False
    try:
        return hmac.compare_digest(provided or "", expected)
    except TypeError:
        app.logger.error("Jeton d'ingestion non ASCII : comparaison impossible, "
                         "tout appel sera refusé.")
        return False


# ── LA FORCE BRUTE SUR LES JETONS ──────────────────────────────────────────
# `compare_digest` empêche de reconstituer le secret au CHRONOMÈTRE. Il
# n'empêche pas de l'essayer, et le relevé du 29 août l'a montré : les quatre
# points à jeton — dont /api/rag/ingest, qui ÉCRIT DANS LA BASE DE
# CONNAISSANCE — n'étaient comptés nulle part. Le commentaire du limiteur
# affirmait pourtant que c'était fait ; les chemins n'ont jamais été ajoutés à
# la table. Un secret qu'on peut essayer sans être compté n'est plus un secret,
# c'est un délai.
#
# ON COMPTE LES ÉCHECS, PAS LES APPELS. Une automatisation légitime présente
# toujours le bon jeton : la plafonner gênerait le seul usage régulier de ces
# points. Un attaquant, lui, ne produit QUE des échecs. Le compteur est donc
# remis à zéro par une réussite — sans quoi une seule faute de frappe
# interdirait la journée à un connecteur qui marche.
_JETON_ESSAIS = 8          # échecs tolérés par IP
_JETON_FENETRE = 900       # avant remise à zéro (15 min)


def _jeton_refus(fourni, attendu, famille):
    """None si le jeton passe ; la réponse de refus sinon.

    Rend 429 quand le compteur est plein — et non 401 : dire « jeton invalide »
    à la neuvième tentative apprendrait à l'attaquant que sa cadence n'a pas été
    remarquée."""
    cle = "jeton:%s:%s" % (famille, client_ip())
    if guard.blocked(cle, limit=_JETON_ESSAIS, window=_JETON_FENETRE):
        app.logger.warning("JETON_FORCE_BRUTE %s sur %s", client_ip(), famille)
        return _rate_limited(_JETON_FENETRE)
    if not _token_ok(fourni, attendu):
        guard.fail(cle)
        return jsonify(ok=False, error="unauthorized"), 401
    guard.clear(cle)
    return None


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
    # LES POINTS EXACTS SONT TESTÉS MÊME HORS DES FAMILLES SURVEILLÉES. Le
    # filtre d'entrée ne retenait que trois préfixes, et laissait donc passer
    # sans compteur les deux points d'ingestion protégés par un simple jeton —
    # c'est-à-dire ceux dont le secret pouvait être essayé indéfiniment.
    #
    # LE FILTRE EST DÉRIVÉ DE LA TABLE, il n'est plus recopié. Les trois
    # préfixes étaient écrits ici À LA MAIN : ajouter une famille à
    # `_RATE_FAMILY` sans penser à cette ligne créait un plafond qui n'était
    # jamais atteint — une protection qui a l'air posée et ne compte rien. Le
    # relevé du 29 août a trouvé quatre familles dans ce cas.
    if not (p in _RATE_EXACT or any(p.startswith(f[0]) for f in _RATE_FAMILY)):
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
_GZIP_MAX = 8_388_608  # au-delà, on ne met pas la réponse entière en mémoire


@app.after_request
def _compress_text(resp):
    try:
        if resp.status_code != 200 or resp.headers.get("Content-Encoding"):
            return resp
        # `is_streamed` RECOUVRE DEUX CHOSES QU'IL NE FAUT PAS CONFONDRE, et
        # les confondre coûte cher. Une réponse de `send_from_directory` a
        # pour corps un FileWrapper, objet sans longueur : Werkzeug la déclare
        # `is_streamed` alors que c'est un simple fichier sur disque, borné et
        # lisible. Un vrai flux (générateur, SSE) l'est aussi, mais lui ne doit
        # jamais être rassemblé en mémoire.
        #
        # ÉCARTER LES DEUX D'UN BLOC — ce que faisait la version d'avant —
        # revient à ne jamais comprimer un fichier statique, sans qu'aucune
        # erreur ne le signale. Ici la conséquence était nulle, parce que les
        # assets passent par `_serve_fast` qui les gzippe lui-même ; sur les
        # deux sites voisins, où le même code servait les fichiers par
        # `send_from_directory`, elle valait 2,3 Mo par première visite. Le
        # piège est retiré plutôt que laissé en embuscade pour la prochaine
        # route qui servira un fichier.
        fichier = resp.direct_passthrough
        if resp.is_streamed and not fichier:
            return resp
        mt = resp.mimetype or ""
        if not (mt.endswith("json") or mt.endswith("xml")
                or (mt.startswith("text/") and mt != "text/event-stream")):
            return resp
        if "gzip" not in (request.headers.get("Accept-Encoding") or "").lower():
            return resp
        # Sortir du mode passe-plat : sans cela Werkzeug refuse de lire le
        # corps. `get_data` transforme le FileWrapper en séquence et enregistre
        # sa fermeture — le descripteur de fichier n'est pas perdu.
        resp.direct_passthrough = False
        data = resp.get_data()
        if len(data) < _GZIP_MIN or len(data) > _GZIP_MAX:
            return resp
        gz = gzip.compress(data, 5)
        if len(gz) >= len(data):
            return resp
        # `set_data` remet Content-Length sur la longueur du corps compressé.
        # Ne pas contourner cet appel : une assignation directe de
        # `resp.response` laisserait la longueur d'origine, et le client
        # attendrait indéfiniment des octets qui ne viennent pas.
        resp.set_data(gz)
        resp.headers["Content-Encoding"] = "gzip"
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


# La page est un littéral plutôt qu'un gabarit : elle doit s'afficher même si
# c'est le chargement des gabarits qui a échoué. Le chemin demandé y entre
# ÉCHAPPÉ et par simple substitution — le passer à un moteur de gabarit
# reviendrait à faire évaluer une chaîne que le visiteur contrôle.
_PAGE_404 = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Page introuvable — CONSEILPREV</title>
<meta name="robots" content="noindex">
<style>
 body{margin:0;background:#0e1116;color:#e8edf3}
 .e404{max-width:640px;margin:12vh auto;padding:0 24px;line-height:1.6;
   font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}
 .e404 h1{font-size:clamp(23px,4vw,33px);line-height:1.2;margin:0 0 14px;
   font-weight:600}
 .e404 .adr{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;
   word-break:break-all;opacity:.7;margin:0 0 22px}
 .e404 ul{padding-left:20px;margin:6px 0 26px}
 .e404 li{margin:5px 0}
 .e404 a{color:#7cc0f5}
 @media (prefers-color-scheme:light){
   body{background:#f7f9fc;color:#16212c} .e404 a{color:#1d4e79}
 }
</style></head>
<body><main class="e404">
 <h1>Cette page n'existe pas — ou n'existe plus.</h1>
 <p class="adr">%(chemin)s</p>
 <p>Le lien est peut-être ancien : le site a été réorganisé depuis. Voici les
    entrées principales, pour ne pas vous laisser sur un cul-de-sac.</p>
 <ul>
   <li><a href="/">Accueil</a></li>
   <li><a href="/ingenierie-datacenter">Ingénierie de centres de données</a></li>
   <li><a href="/audit-conformite">Audit de conformité IEC 62443</a></li>
   <li><a href="/gouvernance-ia">Gouvernance de l'IA</a></li>
   <li><a href="/contact">Nous écrire</a></li>
 </ul>
 <p>Si vous êtes arrivé ici depuis un lien de notre part,
    <a href="/contact">signalez-le nous</a> : c'est à nous de le corriger.</p>
</main></body></html>"""


@app.errorhandler(404)
def _introuvable(_err):
    """UNE ADRESSE INCONNUE DOIT RESTER SUR LE SITE.

    DÉFAUT CORRIGÉ. Aucun gestionnaire 404 n'existait : toute adresse
    inconnue — un lien vieilli, une coquille, un signet d'une arborescence
    précédente — rendait la page d'erreur par défaut du serveur. En anglais,
    sans en-tête ni pied de page, et surtout SANS UN SEUL LIEN : le visiteur
    n'avait d'autre issue que le bouton « retour ». Sur le site d'un cabinet
    qui vend de la rigueur, c'est la page qui dit le contraire.

    Les routes d'API gardent une réponse JSON : un client qui attend du JSON
    échouerait sur « Unexpected token '<' », et une page d'excuses en HTML ne
    lui apprendrait rien.
    """
    if request.path.startswith("/api/"):
        return jsonify(ok=False, error="introuvable",
                       message="Cette adresse d'API n'existe pas."), 404
    return _PAGE_404 % {"chemin": html_lib.escape(request.path)}, 404


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
# Les projets d'ingénierie du client. Construit après les autres magasins et
# non dans le pool de démarrage : il n'est sollicité qu'à la première visite de
# la page d'ingénierie, et le faire attendre au démarrage retarderait tout le
# site pour une table de treize colonnes.
import projets_dc  # noqa: E402
projets_db = projets_dc.make_projets_store()
_boot_pool.shutdown(wait=False)


# --- Automatisation temps réel (planificateur de fond) — voir automation.py ----
#
# LE FOURNISSEUR N'EST PLUS ÉCRIT EN DUR ICI. Ces trois travaux tournent seuls,
# sans personne devant l'écran : nommer un fournisseur en dur, c'était les
# éteindre en silence le jour où c'est L'AUTRE qui a une clé. Le résumé de
# veille, le rapport hebdomadaire et la qualification des demandes entrantes
# retombaient alors sur leur repli — pas de résumé, pas de rapport, pas de
# qualification — sans qu'aucune alerte ne le signale : on ne s'en aperçoit
# qu'à ce qui manque, des semaines plus tard. assistant.defaut() suit la
# configuration réelle du serveur.
def _veille_summarize(titre, description):
    """Résumé LLM d'un bulletin CERT-FR (best-effort ; None si indisponible)."""
    try:
        text, _m = assistant.generate(
            assistant.defaut(),
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
            assistant.defaut(),
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
    import auth as _auth_mod
    automation.init(sender=SENDER, notify_to=NOTIFY_TO, rag=rag, clients=clients_db,
                    livrables=livrables_hist, cockpit=state,
                    summarize=_veille_summarize, generate_report=_report_generate,
                    dsn=os.environ.get("DATABASE_URL"), auth=_auth_mod)


threading.Thread(target=_init_automation, daemon=True).start()

# --- Rétention de l'historique ------------------------------------------------
# Purge périodique des événements au-delà d'un âge (EVENT_RETENTION_DAYS) et/ou
# d'un nombre de lignes (EVENT_MAX_ROWS). Archivage JSONL optionnel avant suppression
# (EVENT_ARCHIVE_PATH — cible durable requise, cf. DEPLOY.md). Sans ces variables,
# aucune purge (l'historique complet est conservé).
# Le `or None` final n'est pas un ornement : ZÉRO signifie « aucune purge ».
# Le perdre allumerait une purge de lui-même sur une base de production.
_RETENTION_DAYS = reglages.reel("EVENT_RETENTION_DAYS", 0, mini=0) or None
_MAX_ROWS = reglages.entier("EVENT_MAX_ROWS", 0, mini=0) or None
_ARCHIVE_PATH = os.environ.get("EVENT_ARCHIVE_PATH") or None
_MAINTENANCE_HOURS = reglages.reel("MAINTENANCE_INTERVAL_HOURS", 6, mini=0.1)


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
    "/acces": "acces.html",
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
    "/checklist-62443": "checklist-62443.html",
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
    "/cgv": "cgv.html",
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
    "/strategie-durable-datacenter": "strategie-durable-datacenter.html",
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
# RLock, pas Lock : la construction d'une entrée HTML lit l'ETag de chaque
# asset qu'elle référence, donc _static_entry se rappelle lui-même sous le
# verrou. Un Lock simple s'interbloquerait à la première page servie par un
# worker frais, quand rien n'est encore en cache.
_STATIC_CACHE_LOCK = threading.RLock()

# LES ASSETS PARTAGÉS SONT VERSIONNÉS DANS LES PAGES. Sans cela, max-age=300
# oblige chaque navigation à revalider CHAQUE fichier passé cinq minutes :
# /datacenter, c'est neuf allers-retours (styles.css + sept scripts + emblème)
# pour neuf 304, à 50-150 ms l'aller-retour vers Render. Avec « ?v=<empreinte> »
# réécrit dans le HTML au moment de la mise en cache, l'URL change quand LE
# CONTENU change : l'asset peut alors être gardé un an (`immutable`), et la
# fraîcheur reste garantie par la page elle-même, revalidée en ≤ 300 s, qui
# référence les nouvelles empreintes dès qu'un fichier change.
_ASSETS_VERSIONNES = (
    "styles.css", "nav.js", "parcours.js", "modules.js", "transmettre.js",
    "datacenter.js", "dc-profil.js", "markdown.js", "ingenierie-dc.js",
    "decarbonation-dc.js", "strategie-dd.js", "equipements-it.js", "emblem.svg",
)
_CC_IMMUABLE = "public, max-age=31536000, immutable"


def _empreinte(etag):
    """Le fragment court de l'ETag — ce qui voyage dans « ?v= »."""
    return etag.strip('"').replace("cp-", "")[:16]


def _versionner_html(raw):
    """Réécrit src="/x.js" et href="/x.css" en « /x.js?v=<empreinte> ».

    Seuls les assets de la liste sont touchés : réécrire une URL au hasard
    versionnerait des routes qui ne savent pas l'être. Un asset illisible est
    simplement laissé tel quel — la page doit se servir même si un fichier
    manque, c'est le comportement d'avant."""
    texte = raw.decode("utf-8")
    for nom in _ASSETS_VERSIONNES:
        if ('"/%s"' % nom) not in texte:
            continue
        try:
            frag = _empreinte(_static_entry(nom)["etag"])
        except OSError:
            continue
        texte = texte.replace('"/%s"' % nom, '"/%s?v=%s"' % (nom, frag))
    return texte.encode("utf-8")


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
        if filename.endswith(".html"):
            raw = _versionner_html(raw)
        ent = {
            "key": key,
            "raw": raw,
            "gz": gzip.compress(raw, 9),
            "etag": '"cp-%s"' % hashlib.sha256(raw).hexdigest()[:24],
            # LA POLITIQUE SE CALCULE ICI, ET NULLE PART AILLEURS : c'est le
            # seul endroit où les octets RÉELLEMENT SERVIS sont connus —
            # `_versionner_html` est déjà passé. Une empreinte prise sur le
            # fichier d'origine serait juste pour un document que personne ne
            # reçoit, et le navigateur refuserait le script sans qu'aucune
            # erreur ne remonte.
            "csp": csp.pour(raw) if filename.endswith(".html") else None,
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
    # L'URL versionnée du contenu COURANT est immuable : son adresse change
    # avec son contenu. Un « ?v= » périmé (vieille page en cache quelque part)
    # retombe sur la politique courte et sert quand même le contenu à jour —
    # jamais une erreur, jamais un contenu figé à tort.
    if request.args.get("v") == _empreinte(ent["etag"]):
        cache_control = _CC_IMMUABLE
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
    # LA POLITIQUE DE CETTE PAGE, avec les empreintes de SES scripts intégrés.
    # Posée ici, elle précède le crochet d'en-têtes, qui emploie `setdefault`
    # et laisse donc celle-ci en place. Une page sans script intégré n'en
    # reçoit pas : la politique globale, plus stricte, lui suffit.
    if ent.get("csp"):
        resp.headers["Content-Security-Policy"] = ent["csp"]
    resp.headers["Cache-Control"] = cache_control
    if gzippable:
        resp.headers["Vary"] = "Accept-Encoding"
    return resp


# ── Réponses JSON figées ──────────────────────────────────────────────────
# Toute une famille de routes GET sert des RÉFÉRENTIELS : des constantes de
# module, identiques d'une requête à l'autre jusqu'au prochain déploiement.
# Chacune re-sérialisait et re-gzippait son corps à chaque appel — 18 ms CPU
# pour le seul cadre d'ingénierie (642 Ko) — et, sans ETag, re-téléchargeait
# tout à chaque visite. Ici : sérialisé UNE fois par processus, 304 ensuite.
_FIGES = {}
_FIGES_LOCK = threading.Lock()


def _json_fige(cle, builder, cache_control="private, max-age=600, must-revalidate"):
    """Sert le JSON de `builder()` mémoïsé, avec ETag + 304 et gzip pré-calculé.

    À N'UTILISER QUE pour un corps déterministe par processus : le builder ne
    sera plus rappelé. Une route paramétrée doit inclure ses paramètres dans
    `cle`, sinon elle servirait la réponse d'un autre appel."""
    ent = _FIGES.get(cle)
    if ent is None:
        with _FIGES_LOCK:
            ent = _FIGES.get(cle)
            if ent is None:
                raw = json.dumps(builder(), ensure_ascii=False,
                                 separators=(",", ":")).encode("utf-8")
                ent = {
                    "raw": raw,
                    "gz": gzip.compress(raw, 9),
                    "etag": '"j-%s"' % hashlib.sha256(raw).hexdigest()[:24],
                }
                _FIGES[cle] = ent
    if ent["etag"] in (request.headers.get("If-None-Match") or ""):
        resp = Response(status=304, mimetype="application/json")
    else:
        use_gz = "gzip" in (request.headers.get("Accept-Encoding") or "").lower()
        body = ent["gz"] if use_gz else ent["raw"]
        resp = Response(body, mimetype="application/json")
        if use_gz:
            resp.headers["Content-Encoding"] = "gzip"
        resp.headers["Content-Length"] = str(len(body))
    resp.headers["ETag"] = ent["etag"]
    resp.headers["Cache-Control"] = cache_control
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


@app.route("/checklist-62443")
def checklist_62443_page():
    return _page(PAGES["/checklist-62443"])


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
    return jsonify(models=assistant.available(), default=assistant.preference())


@app.route("/api/assistant/selftest")
@admin_required
def api_assistant_selftest():
    """Diagnostic : ping minimal de chaque modèle, renvoie le statut technique
    (code HTTP, type d'erreur). Aucun secret ni contenu. Limité par IP.

    RÉSERVÉE À L'ADMINISTRATEUR, et pas seulement par principe : chaque appel
    DÉPENSE le crédit du propriétaire du compte de facturation. La borne par
    IP restait la seule protection, et elle est faite pour freiner un abus, pas
    pour désigner qui a le droit. Le seul appelant est la console
    d'administration, elle-même derrière ce rôle : le resserrement ne retire
    l'accès à personne qui l'utilisait."""
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
            # Ni la clé ni le modèle : le compte du fournisseur est à sec.
            # Réessayer n'y changera rien, et la seule chose utile à dire au
            # visiteur est qu'il peut basculer sur l'autre modèle.
            "credit": "Ce modèle n'est plus approvisionné chez son fournisseur. "
                      "Essayez l'autre modèle, ou écrivez-nous via la page Contact.",
            "empty": "Votre message est vide.",
            "busy": "L'assistant est très sollicité pour le moment. Réessayez dans un instant.",
            "network": "Service d'IA momentanément injoignable. Réessayez dans un instant.",
            "timeout": "Le modèle a mis trop de temps à répondre. Réessayez, ou essayez l'autre modèle.",
            "upstream": "L'assistant a rencontré une erreur. Réessayez, ou contactez-nous.",
            "sature": "Plusieurs demandes sont déjà en cours sur ce serveur. "
                      "Pour qu'il continue de répondre à tout le monde, "
                      "celle-ci n'a pas attendu : réessayez dans un instant.",
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
def juridique_page():
    """Conseil juridique assisté (clients connectés et administrateur)."""
    return _page(PAGES["/juridique"])


@app.route("/api/juridique/config")
def api_juridique_config():
    """Tout ce dont l'interface a besoin pour se construire : questionnaire,
    référentiel, clausier, amorces. Une seule définition côté serveur — une liste
    d'options recopiée dans le HTML finit toujours par diverger du moteur."""
    # Figé par processus : tout est constant de module, et assistant.available()
    # ne lit que des variables d'environnement, stables au démarrage.
    return _json_fige("juridique-config", lambda: dict(
        ok=True,
        version_referentiel=juridique.VERSION_REFERENTIEL,
        champs=juridique.PROFIL_CHAMPS,
        referentiel=juridique.referentiel(),
        domaines_clausier=juridique.DOMAINES_CLAUSIER,
        suggestions=juridique.SUGGESTIONS,
        avertissement=juridique.AVERTISSEMENT,
        mention_ia=juridique.MENTION_IA,
        # Les faits CONSTANTS du corpus de jurisprudence, pas son état : cette
        # réponse est figée par processus, et un état constaté au démarrage
        # serait encore affiché des heures plus tard. L'état vivant se demande
        # sur /api/juridique/corpus.
        corpus_jurisprudence=librejustice.declaration(),
        models=assistant.available()))


@app.route("/api/juridique/qualification", methods=["POST"])
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
def api_juridique_clausier():
    """Clausier fournisseurs, filtrable par domaine et par criticité."""
    return jsonify(ok=True,
                   domaines=juridique.DOMAINES_CLAUSIER,
                   clauses=juridique.clausier(
                       domaine=(request.args.get("domaine") or "").strip() or None,
                       criticite=(request.args.get("criticite") or "").strip() or None),
                   avertissement=juridique.AVERTISSEMENT)


@app.route("/api/juridique/controverses")
def api_juridique_controverses():
    """Points d'interprétation ouverts — plusieurs lectures, jamais une seule."""
    ids = [x for x in (request.args.get("textes") or "").split(",") if x.strip()]
    return jsonify(ok=True, points=juridique.controverses(ids or None))


@app.route("/api/juridique/jurisprudence")
def api_juridique_jurisprudence():
    """Jurisprudence adossée à un point d'interprétation, ou à une question libre.

    `?point=<id>` interroge le corpus avec la requête arrêtée pour cette
    controverse, `?q=<question>` avec celle du lecteur. Le champ `vise` n'est pas
    un ornement : aucune juridiction ne s'est prononcée sur l'article 25 de
    l'IA Act, et les décisions rendues portent sur la question SOUS-JACENTE —
    qui répond d'un produit qu'on a modifié. Le dire est la différence entre un
    éclairage et une affirmation fausse."""
    point = (request.args.get("point") or "").strip()
    question = (request.args.get("q") or "").strip()
    if point:
        r = librejustice.pour_controverse(point)
    elif question:
        r = librejustice.rechercher(question, limite=6)
    else:
        return jsonify(ok=False,
                       message="Indiquez un point d'interprétation ou une question."), 400
    r["ok_requete"] = bool(r.get("ok"))
    r.update(ok=True, **librejustice.declaration())
    return jsonify(r)


@app.route("/api/juridique/corpus")
def api_juridique_corpus():
    """État du connecteur de jurisprudence. `?test=1` interroge RÉELLEMENT le
    corpus : un état déclaré n'est pas un état constaté, et c'est exactement la
    distinction dont un exploitant a besoin."""
    etat = librejustice.etat()
    if request.args.get("test") in ("1", "true", "oui"):
        etat["essai"] = librejustice.disponible()
    return jsonify(ok=True, corpus=etat)


def _juridique_jurisprudence(question, profil=None, limite=5):
    """Décisions du corpus LibreJustice éclairant la question posée.

    MÊME DISCIPLINE QUE `_juridique_extraits`, ET POUR LA MÊME RAISON : un
    corpus externe momentanément injoignable dégrade la précision d'une analyse,
    il ne l'empêche pas. Le conseil tenait debout sans jurisprudence avant que ce
    connecteur existe.

    REND AUSSI L'ÉTAT, ET C'EST TOUT LE POINT. Une liste vide a deux causes
    qui ne se soignent pas pareil : le corpus a répondu et ne connaît rien sur
    la question, ou le corpus n'a pas répondu du tout. Jeter le motif en route
    laissait la page incapable de les distinguer — elle n'affichait rien dans
    les deux cas, et le lecteur concluait qu'aucune décision n'existe.

    Ce qui est rendu ici est exactement ce que le modèle verra, et exactement ce
    contre quoi ses citations seront vérifiées. La liste doit donc être portée
    jusqu'à `post_traiter` : la contrôler contre autre chose que ce qui a été
    montré ne contrôlerait rien."""
    try:
        requete = " ".join(x for x in [
            question, (profil or {}).get("secteur") or ""] if x)[:500]
        r = librejustice.rechercher(requete, limite=limite)
        if not r.get("ok"):
            app.logger.info("LIBREJUSTICE_INDISPONIBLE: %s", r.get("motif"))
            return [], {"ok": False, "motif": r.get("motif") or ""}
        return (r.get("decisions") or []), {"ok": True, "motif": ""}
    except Exception as exc:
        app.logger.info("LIBREJUSTICE_ERREUR: %s", exc)
        return [], {"ok": False, "motif": "erreur du connecteur (%s)"
                                          % type(exc).__name__}


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
    "sature": "Plusieurs analyses sont déjà en cours sur ce serveur. Pour "
              "qu'il continue de répondre à tout le monde, celle-ci n'a pas "
              "attendu : réessayez dans un instant.",
}


@app.route("/api/juridique/analyse", methods=["POST"])
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
    decisions, corpus = _juridique_jurisprudence(question, profil)
    user = juridique.prompt_analyse(question, profil=profil, extraits=extraits,
                                    textes_ids=textes_ids,
                                    jurisprudence=decisions)
    try:
        texte, used = assistant.generate(model, juridique.SYSTEM_JURIDIQUE, user,
                                         max_tokens=3200)
    except assistant.AssistantError as exc:
        return jsonify(ok=False, error=exc.code,
                       message=_JURIDIQUE_ERREURS.get(
                           exc.code, "Analyse indisponible pour le moment.")), exc.status

    res = juridique.post_traiter(texte, textes_ids, jurisprudence=decisions)
    # UNE DÉCISION INVENTÉE SE JOURNALISE COMME UNE RÉFÉRENCE INVENTÉE. Le
    # journal servait déjà à repérer les inventions du modèle ; une citation de
    # jurisprudence hors de la liste montrée est la même faute, et la plus
    # crédible des deux.
    hors_liste = res.get("jurisprudence", {}).get("suspectes") or []
    audit.journaliser("juridique.analyse", cible=used,
                      detail="%d extrait(s) cité(s), %d décision(s) rapportée(s), "
                             "%d référence(s) suspecte(s), %d décision(s) hors "
                             "liste ; minimisation : %s"
                             % (len(sources), len(decisions),
                                len(res["citations"]["suspectes"]), len(hors_liste),
                                resume_min),
                      ok=not res["citations"]["suspectes"] and not hors_liste)
    return jsonify(ok=True, model=used, sources=sources,
                   qualification=qual, decisions=decisions, corpus=corpus, **res)


@app.route("/api/juridique/contrat", methods=["POST"])
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
        # ── L'ANALYSE ANTIVIRALE, QUI MANQUAIT ICI ──────────────────────────
        # Tous les autres dépôts du site la traversent : la base de
        # connaissance, la restauration de sauvegarde, le versement de pièces.
        # CELUI-CI, non. Un contrat déposé par n'importe quel compte était
        # ouvert et son texte extrait sans le moindre contrôle — donc un PDF à
        # action automatique, une archive piégée ou un OOXML à macro passaient
        # par la porte que toutes les autres surveillent. C'est la porte qu'on
        # oublie qu'on emprunte.
        #
        # REFUS SI LE MODULE MANQUE, comme partout ailleurs : une porte absente
        # qui laisse passer est pire que pas de porte, parce que personne ne
        # s'en aperçoit.
        try:
            import antivirus
        except Exception:                                   # noqa: BLE001
            app.logger.error("AV_INDISPONIBLE: relecture de contrat")
            return jsonify(ok=False, error="analyse_indisponible",
                           message="L'analyse des fichiers est momentanément "
                                   "indisponible. Collez le texte à la place."), 503
        verdict = antivirus.analyser(fichier.filename or "contrat", blob)
        if not verdict.get("accepte"):
            audit.journaliser("juridique.contrat.refus_av",
                              cible=verdict.get("code") or "refus",
                              detail=(verdict.get("motif") or "")[:200])
            return jsonify(ok=False, error="analyse_refus",
                           message=verdict.get("motif")
                                   or "Fichier refusé par l'analyse."), 422
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
    decisions, corpus = _juridique_jurisprudence(objet, profil)
    user = juridique.prompt_arbitrage(
        objet, contexte=contexte,
        extraits="\n\n".join(extraits) if extraits else None,
        profil=profil, dossier=dossier, textes_ids=textes_ids,
        jurisprudence=decisions)
    try:
        texte, used = assistant.generate(model, juridique.SYSTEM_ARBITRAGE, user,
                                         max_tokens=4000)
    except assistant.AssistantError as exc:
        return jsonify(ok=False, error=exc.code,
                       message=_JURIDIQUE_ERREURS.get(
                           exc.code, "Note indisponible pour le moment.")), exc.status

    res = juridique.post_traiter(texte, textes_ids, jurisprudence=decisions)
    hors_liste = res.get("jurisprudence", {}).get("suspectes") or []
    audit.journaliser("juridique.arbitrage", cible=used,
                      detail="%d pièce(s), %d décideur(s), %d échéance(s), "
                             "%d décision(s) rapportée(s), %d référence(s) "
                             "suspecte(s), %d décision(s) hors liste ; "
                             "minimisation : %s"
                             % (len(pieces), len(routage["decisions"]),
                                len(routage["echeances"]), len(decisions),
                                len(res["citations"]["suspectes"]),
                                len(hors_liste), resume_min),
                      ok=not res["citations"]["suspectes"] and not hors_liste)
    return jsonify(ok=True, model=used, pieces=pieces, routage=routage,
                   decisions=decisions, corpus=corpus, **res)


@app.route("/api/juridique/export", methods=["POST"])
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
            # Le corps du document EST la réponse du modèle : marquage dû.
            "ia": True,
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
def api_juridique_instances():
    """Catalogue des instances et des natures de dossier, pour l'interface."""
    return _json_fige("juridique-instances", lambda: dict(
        ok=True, instances=juridique.INSTANCES,
        natures=[{"v": v, "l": l} for v, l in juridique.NATURES_DOSSIER],
        delais=juridique.DELAIS,
        suggestions=juridique.SUGGESTIONS_ARBITRAGE))


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
def relecture_contrat_page():
    """Relecture assistée d'un contrat, version par version."""
    return _page(PAGES["/relecture-contrat"])


@app.route("/api/playbook/config")
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
            # La note porte l'avertissement d'assistance de `juridique` et,
            # quand il est joint, l'échange avec l'assistant. On la marque sans
            # chercher à distinguer une note sans échange : ce serait exact,
            # mais l'avertissement imprimé dans le corps dirait alors le
            # contraire du marquage.
            "ia": True,
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
import durabilite    # noqa: E402  — le cadre vert, adosse aux trois sous-dossiers de la base
import checklist_62443  # noqa: E402  — la liste de verification 62443
import parcours_62443  # noqa: E402  — l'ordre dans lequel prendre ce qui reste
import maturite_ot   # noqa: E402  — l'auto-evaluation declarative, pas un assessment
import etat_art      # noqa: E402  — les faits publies, chacun avec son auteur et ce qu'il vaut
import profil_dc     # noqa: E402  — analyse le moteur ci-dessus, ne le double pas
import ingenierie_dc  # noqa: E402  — situe ses résultats dans la séquence projet
import technique_dc  # noqa: E402  — le vocabulaire du métier, servi aux infobulles
import icpe_dc       # noqa: E402  — crible les rubriques, ne classe pas le site
import travaux_dc    # noqa: E402  — l'ordre des opérations de chantier et ses tiers
import ao_dc         # noqa: E402  — lit le dossier marché, prépare la candidature
import programme_dc  # noqa: E402  — consolide un portefeuille de sites, pas un projet
import tier_dc       # noqa: E402  — qualifie une topologie, ne décerne aucun niveau
import reseau_dc     # noqa: E402  — chiffre un raccordement effaçable, ne prédit aucun délai
import econome_dc     # l'economiste de la construction : quantites x prix
import decarbonation  # noqa: E402  — les situe dans la hiérarchie d'atténuation
import ecart_referentiel  # noqa: E402  — ce que la carte promet vs ce que le moteur produit
import strategie_dd  # noqa: E402  — le livrable d'ouverture, quatre perspectives
import equipements_it  # noqa: E402  — PARTAGÉ À L'IDENTIQUE avec Sentinel
import transmission  # noqa: E402  — ce qui doit voyager AVEC le document qui sort
import lacunes      # noqa: E402  — instruire les trous, sans fabriquer de faits
# Le nettoyage des extraits et des titres de sources. Nommé « extraits_mod » :
# « extraits » désigne déjà, dans une douzaine de fonctions de ce fichier, la
# liste des passages retrouvés — les confondre aurait écrasé l'un par l'autre.
import extraits as extraits_mod  # noqa: E402


@app.route("/datacenter")
@login_required
def datacenter_page():
    """Data Center Sustainability & Decarbonisation — page reservee aux comptes.

    LA PAGE SUIT LA POLITIQUE DU SITE : depuis que toutes les pages du menu
    demandent un compte (voir /api/acces), elle aussi. Le cadre, la methode et
    le calcul restent ce qu'ils etaient : un moteur deterministe, sans modele
    de langage, sans ecriture — deux executions identiques donnent le meme
    resultat, et rien de ce qu'il produit n'appartient a un client.

    CE QUI RESTE PLUS FERME ENCORE, ET POURQUOI. Les pieces : la base
    documentaire du cabinet, les livrables rediges, le suivi de projet, les
    exports. Ce sont les documents de travail du cabinet et de ses clients ;
    les publier reviendrait a publier le travail des seconds.
    """
    return _page(PAGES["/datacenter"])


@app.route("/ingenierie-datacenter")
@login_required
def ingenierie_datacenter_page():
    """Le même calcul, replacé dans la séquence projet — MOE et ingénierie."""
    return _page(PAGES["/ingenierie-datacenter"])


@app.route("/decarbonation-datacenter")
def decarbonation_datacenter_page():
    """FUSIONNEE dans /datacenter — redirection permanente.

    La decarbonation avait sa page ; celle-ci refaisait le meme formulaire,
    lisait le meme profil et renvoyait vers les memes voisines. Deux pages qui
    partagent leur sujet finissent par se contredire : l'une est mise a jour,
    l'autre non, et le lecteur ne sait plus laquelle fait foi.

    L'adresse est conservee en 301 plutot que supprimee : elle a figure dans un
    sitemap et dans des echanges, et une adresse publiee qui repond 404 fait
    perdre le lecteur au lieu de le deplacer.
    """
    return redirect("/datacenter#dc-sec-deca", code=301)


@app.route("/strategie-durable-datacenter")
@login_required
def strategie_durable_datacenter_page():
    """Le questionnaire des quatre perspectives, et le livrable d'ouverture
    d'etude qui en decoule.

    Page reservee aux comptes, comme le reste du menu. Le questionnaire ne
    conserve rien pour autant : les reponses transitent vers le calcul et n'y
    sont pas ecrites. L'EXPORT du livrable, lui, reste ferme — le document
    porte le nom du client, son site et ses arbitrages.
    """
    return _page(PAGES["/strategie-durable-datacenter"])


@app.route("/api/datacenter/referentiel")
@login_required
def api_datacenter_referentiel():
    """Vocabulaire, constantes et cadre réglementaire.

    Une seule définition côté serveur : une liste d'options recopiée dans le
    HTML finit toujours par diverger du moteur qui, lui, calcule."""
    # Le compte des thèmes de la base est DÉRIVÉ, pas écrit dans la page. Il y
    # était : « seize thèmes », vrai le jour où on l'a tapé, faux depuis que la
    # famille en porte vingt-cinq — neuf de management ajoutés sans que
    # personne ne pense à corriger la phrase. Un lecteur cherchant un HAZOP en
    # concluait qu'il n'était pas couvert.
    # LA TECHNIQUE VOYAGE AVEC LE RÉFÉRENTIEL, et non par un second appel. Le
    # formulaire de choix des fluides est construit à partir de cette réponse ;
    # servir l'explication d'un mode de refroidissement séparément ferait
    # afficher la liste avant les explications, c'est-à-dire au moment exact où
    # le lecteur choisit.
    return _json_fige("dc-referentiel", lambda: dict(
        ok=True, referentiel=datacenter.referentiel(),
        champs=datacenter.CHAMPS,
        technique=technique_dc.referentiel(),
        reseau=reseau_dc.referentiel(),
        base=_themes_datacenter()))


def _themes_datacenter():
    """Ce que la base de connaissance couvre pour les centres de données."""
    try:
        # Import local : le module n'est pas lié au niveau global (seules
        # `make_store` et `RagError` le sont), et l'y ajouter pour un compte
        # ferait charger la base au démarrage sans nécessité.
        import rag_store as _rs
        familles = dict(_rs.THEME_FAMILLES)
    except Exception:
        return None
    liste = familles.get("Centres de données") or []
    techniques = [x for x in liste if "Management" not in x]
    return {
        "famille": "Centres de données",
        "themes": len(liste),
        "techniques": len(techniques),
        "management": len(liste) - len(techniques),
    }


def _lire_nombre(brut, champ):
    """Un nombre, ou le motif du refus. Rend (valeur, None) ou (None, motif).

    TROIS REFUS, ET ILS NE DISENT PAS LA MÊME CHOSE au lecteur.

    ILLISIBLE — « abc », « 75 % ». Le champ n'entre pas dans le calcul, et le
    message le dit : c'est le comportement d'origine, il était juste.

    NON FINI — « nan », « inf », « 1e400 ». `float()` les accepte : ce sont des
    nombres pour Python. Ils traversaient donc tout le calcul. Trois champs
    faisaient lever l'étude, sept faisaient rendre un corps contenant `NaN`,
    qui n'est PAS du JSON valide : la page ne pouvait même pas lire l'erreur,
    elle voyait un `JSON.parse` échouer. On les refuse à l'entrée.

    HORS DOMAINE — un taux de charge de −99, un PUE de 0,5. C'est le refus le
    plus important des trois, parce que c'est le seul qui était SILENCIEUX :
    l'étude revenait complète et d'apparence normale, calculée sur une grandeur
    qui n'existe pas. Neuf champs sur dix étaient dans ce cas.

    LE DOMAINE N'EST PAS LA PLAGE OBSERVÉE, et cette distinction se garde : un
    centre de 15 kW sort du cadrage du cabinet et se calcule très bien — la
    note l'accompagne. Sortir du DOMAINE, c'est autre chose : il n'y a rien à
    calculer.
    """
    try:
        valeur = float(str(brut).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None, ("« %s » n'a pas pu être lu comme un nombre : ce champ "
                      "n'a pas été pris en compte." % str(brut)[:40])
    if not math.isfinite(valeur):
        return None, ("« %s » n'est pas une valeur finie : ce champ n'a pas été "
                      "pris en compte." % str(brut)[:40])
    d = champ.get("domaine")
    if d:
        bas, haut = d.get("min"), d.get("max")
        trop_bas = (valeur <= bas) if d.get("strict_min") else (valeur < bas)
        if bas is not None and trop_bas:
            return None, ("« %s » est hors du domaine de cette grandeur (%s) : "
                          "ce champ n'a pas été pris en compte."
                          % (str(brut)[:40], d["pourquoi"]))
        if haut is not None and valeur > haut:
            return None, ("« %s » est hors du domaine de cette grandeur (%s) : "
                          "ce champ n'a pas été pris en compte."
                          % (str(brut)[:40], d["pourquoi"]))
    return valeur, None


def _profil_datacenter(data, rejets=None):
    """Nettoie les entrees. Les nombres recus en texte sont convertis ici, une
    fois pour toutes : plus bas, une chaine dans un calcul leve, et l'etude
    entiere echouerait sur une virgule decimale.

    CE QUI ETAIT AVALE EN SILENCE. Une valeur illisible tombait dans un
    `continue` muet : le champ disparaissait, l'etude repartait sur la valeur
    par defaut, et le resultat etait IDENTIQUE a celui d'une saisie valide.
    Mesure : « 75 % » tape dans un champ note « 0-1 » -- la faute la plus
    naturelle qui soit -- produisait une etude complete calculee sur 0,65, sans
    que rien ne le signale. Le lecteur croyait avoir chiffre son projet.

    Passer une liste en `rejets` la fait remplir de ce qui n'a pas ete lu, pour
    que l'appelant le publie. Un champ absent ou vide n'est PAS un rejet :
    c'est un choix, et il se respecte sans commentaire.
    """
    profil = {}
    for champ in datacenter.CHAMPS:
        cid = champ["id"]
        if cid not in data or data[cid] in ("", None):
            continue
        brut = data[cid]
        if champ["type"] == "nombre":
            valeur, motif = _lire_nombre(brut, champ)
            if motif:
                if rejets is not None:
                    rejets.append({
                        "champ": cid,
                        "label": champ.get("label") or cid,
                        "saisi": str(brut)[:40],
                        "message": motif,
                    })
                continue
            profil[cid] = valeur
        else:
            profil[cid] = str(brut).strip()[:40]
    return profil


def _lecture_rejets(rejets):
    """Ce qu'il faut LIRE quand des champs ont ete ecartes."""
    if not rejets:
        return None
    return ("%d champ(s) n'ont pas été lus et n'entrent donc pas dans ce "
            "résultat : %s. Le calcul est reparti sur les valeurs par défaut "
            "pour eux — ce n'est pas votre projet qui a été chiffré sur ces "
            "postes." % (len(rejets), ", ".join(r["label"] for r in rejets)))


@app.route("/api/datacenter/etude", methods=["POST"])
@login_required
def api_datacenter_etude():
    """L'étude complète. Déterministe : deux appels identiques, même résultat."""
    data = request.get_json(silent=True) or {}
    rejets = []
    profil = _profil_datacenter(data, rejets)
    if not profil.get("puissance_it_kw"):
        # SI C'EST LA PUISSANCE ELLE-MEME QUI N'A PAS ETE LUE, on ne dit pas
        # « champ necessaire » a quelqu'un qui vient de le remplir : on lui dit
        # que ce qu'il a tape n'a pas pu etre lu.
        illisible = next((r for r in rejets
                          if r["champ"] == "puissance_it_kw"), None)
        if illisible:
            return jsonify(ok=False, error="puissance_illisible",
                           message=illisible["message"], rejets=rejets), 400
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
    # CE QUI N'A PAS ETE LU VOYAGE AVEC LE RESULTAT. Tu, le resultat serait
    # exact et trompeur : identique a celui d'une saisie valide.
    return jsonify(ok=True, etude=res, rejets=rejets,
                   lecture_rejets=_lecture_rejets(rejets))


@app.route("/api/datacenter/evaluer", methods=["POST"])
@login_required
def api_datacenter_evaluer():
    """Juger un chiffre ANNONCÉ — un PUE de plaquette, un facteur d'émission
    de contrat — avec les plages du référentiel, les mêmes que l'étude.

    C'est le geste qui PRÉCÈDE les études que le moteur ne fait pas : avant de
    payer une simulation TMY ou une étude de pilotage horaire, on vérifie que
    le chiffre sur la table est physiquement recevable. Un refus (PUE < 1,
    facteur négatif) est une réponse, pas une erreur : il est servi en 200
    avec son motif, parce que c'est le verdict lui-même."""
    data = request.get_json(silent=True) or {}
    genre = str(data.get("type") or "").strip()
    if genre == "pue":
        r = datacenter.evaluer_pue(data.get("pue"),
                                   refroidissement=data.get("refroidissement"),
                                   taux_charge=data.get("taux_charge"))
    elif genre == "intensite":
        r = datacenter.evaluer_intensite(
            data.get("facteur_g"), pays=data.get("pays"),
            heures_basses_g=data.get("heures_basses_g"),
            part_differable_pct=data.get("part_differable_pct"),
            energie_mwh_an=data.get("energie_mwh_an"))
    elif genre == "eau":
        # L'eau se juge contre le profil COMPLET : l'appoint de référence est
        # recalculé par le même moteur que l'étude, avec le nettoyage de
        # profil commun — jamais un profil brut du client.
        r = datacenter.evaluer_eau(_profil_datacenter(data.get("profil") or {}),
                                   data.get("volume_annuel_m3"),
                                   pointe_jour_m3=data.get("pointe_jour_m3"))
    elif genre == "incorpore":
        r = datacenter.evaluer_incorpore(data.get("poste"),
                                         data.get("valeur_kg"),
                                         duree_vie_ans=data.get("duree_vie_ans"))
    else:
        return jsonify(ok=False, error="type_inconnu",
                       message="type attendu : pue, intensite, eau ou incorpore."), 400
    audit.journaliser("datacenter.evaluer", cible=genre,
                      detail=str(r.get("verdict") or r.get("motif", ""))[:80])
    return jsonify(ok=True, evaluation=r)


@app.route("/api/datacenter/equipements", methods=["POST"])
@login_required
def api_datacenter_equipements():
    """La nomenclature informatique : quantités, prix indicatifs, scope 3, et
    le point de bascule de l'allongement de durée de vie.

    Le module est PARTAGÉ à l'identique avec Sentinel : l'enveloppe
    d'investissement et l'empreinte environnementale doivent lire les mêmes
    quantités, sans quoi l'écart se découvre en comité.

    Un refus — densité inconnue, pays dont le mix n'est pas au référentiel,
    allongement au-delà du domaine — est servi en 200 avec son motif : c'est
    le verdict, pas une panne.
    """
    data = request.get_json(silent=True) or {}
    n = equipements_it.nomenclature(data.get("puissance_it_kw"),
                                    densite=data.get("densite"),
                                    duree_vie_serveur=data.get("duree_vie_serveur"))
    if not n.get("ok"):
        return jsonify(ok=True, nomenclature=n)

    part = equipements_it.part_investissement(
        n, enveloppe_travaux_eur=data.get("enveloppe_travaux_eur"),
        perimetre=data.get("perimetre") or "propre")

    prolong = None
    if data.get("duree_cible") is not None:
        prolong = equipements_it.prolongation(
            data.get("puissance_it_kw"),
            duree_base=data.get("duree_base"),
            duree_cible=data.get("duree_cible"),
            pays=data.get("pays") or "FR",
            intensite_g=data.get("intensite_g"),
            densite=data.get("densite"),
            pue=data.get("pue") or 1.0,
            derive_an=data.get("derive_an"))

    scope3 = equipements_it.bilan_scope3(
        n, prolong if (prolong and prolong.get("ok")) else None)

    audit.journaliser("datacenter.equipements",
                      cible=str(data.get("puissance_it_kw"))[:20],
                      detail=str(n.get("baies"))[:40])
    return jsonify(ok=True, nomenclature=n, part=part,
                   prolongation=prolong, scope3=scope3)


@app.route("/api/datacenter/equipements/referentiel")
@login_required
def api_datacenter_equipements_referentiel():
    """Les hypothèses chiffrées du module, publiées pour être contestées."""
    return _json_fige("dc-equipements-ref",
                      lambda: dict(ok=True,
                                   referentiel=equipements_it.referentiel()))


@app.route("/api/datacenter/durabilite")
@login_required
def api_datacenter_durabilite():
    """Le cadre de durabilite : trois axes, leurs textes, ce qu'on en calcule.

    OUVERT, comme le calcul qu'il encadre. Il ne sert AUCUN document : les
    pieces de la base documentaire restent reservees aux comptes connectes. Ce
    qui sort ici, c'est le cadre et la methode — de quoi juger l'outil sans
    avoir a s'inscrire pour le decouvrir.
    """
    try:
        # Figé par processus. L'horodatage « genere » date désormais
        # l'assemblage du référentiel dans ce processus, pas la requête —
        # ce qui est plus juste : le contenu, lui, ne change qu'au déploiement.
        return _json_fige("dc-durabilite",
                          lambda: dict(ok=True, cadre=durabilite.cadre()))
    except Exception:
        app.logger.exception("cadre de durabilite")
        return jsonify(ok=False, error="cadre_indisponible",
                       message="Le cadre n'a pas pu etre etabli."), 503


@app.route("/api/62443/checklist")
def api_62443_checklist():
    """La liste de verification IEC 62443 : six sections, vingt-sept points.

    CE QUE CETTE ROUTE NE REND PAS. Aucun niveau de maturite ni de securite.
    La 62443-2-4 definit des niveaux de maturite (ML 1 a 4) et la 62443-3-3 des
    niveaux de securite (SL 1 a 4) ; les deux se constatent sur preuves, par
    exigence et par perimetre. Un compte de cases n'est ni l'un ni l'autre, et
    la reponse le dit dans ses propres champs plutot qu'en note de bas de page.
    """
    return _json_fige("62443-checklist",
                      lambda: dict(ok=True,
                                   referentiel=checklist_62443.referentiel()))


@app.route("/api/62443/checklist/compter", methods=["POST"])
def api_62443_checklist_compter():
    """Compte ce qui est coche, section par section, et ce qui reste.

    Une cle inconnue est REFUSEE plutot qu'ignoree : un total qui compterait
    des points inexistants ne se recouperait pas.
    """
    data = request.get_json(silent=True) or {}
    r = checklist_62443.compter(data.get("coches"))
    return jsonify(r) if r.get("ok") else (jsonify(r), 400)


@app.route("/api/62443/checklist/parcours", methods=["POST"])
def api_62443_checklist_parcours():
    """OU EN EST CE CLIENT, ET DANS QUEL ORDRE PRENDRE CE QUI RESTE.

    CE QUE CETTE ROUTE NE REND PAS, ET C'EST DIT DANS SES PROPRES CHAMPS :
    aucun niveau de maturite ni de securite. Un compte de cases n'est ni un ML
    au sens de la 62443-2-4 ni un SL au sens de la 62443-3-3 — les deux se
    constatent sur preuves, par exigence et par perimetre. Ce qui est rendu a
    la place est un etat de preparation et un ordre : quel point bloque
    combien d'autres, et ce qui peut etre engage des maintenant.

    L'ORDRE VIENT D'UNE TABLE DE PREALABLES ECRITE A LA MAIN, motivee arete
    par arete dans `parcours_62443` — un jugement de ce cabinet, assume comme
    tel plutot que deguise en derivation.
    """
    data = request.get_json(silent=True) or {}
    r = parcours_62443.parcours(data.get("coches"))
    return jsonify(r) if r.get("ok") else (jsonify(r), 400)


@app.route("/api/62443/checklist/emporter", methods=["POST"])
def api_62443_checklist_emporter():
    """La liste, l'etat et le parcours — en PDF ou en Word.

    LE DOCUMENT CIRCULE SANS SA PAGE. Il est transfere, imprime, joint a un
    comite de pilotage, relu six mois plus tard par quelqu'un qui n'a jamais
    vu ce site. Il porte donc la reserve sur les niveaux de maturite AVANT
    les chiffres, et non en note de bas de page : `parcours_62443.markdown`
    la place en tete du document.
    """
    data = request.get_json(silent=True) or {}
    fmt = str(data.get("format") or "pdf").lower()
    if fmt not in ("pdf", "docx"):
        return jsonify(ok=False, error="format_inconnu",
                       message="Formats servis : pdf, docx."), 400

    # LA MEME PORTE QUE L'ECRAN. `markdown` appelle `parcours`, qui appelle
    # `compter` : une cle inconnue est refusee ici comme elle l'est la, et le
    # motif du refus est le meme. Un format de sortie ne doit jamais devenir
    # le chemin de contournement d'un controle.
    verif = checklist_62443.compter(data.get("coches"))
    if not verif.get("ok"):
        return jsonify(verif), 400

    md = parcours_62443.markdown(data.get("coches"),
                                 titre=str(data.get("titre") or "").strip()[:120] or None)
    meta = {"label": "Checklist IEC 62443 — état et parcours",
            "client": str(data.get("client") or "")[:120],
            # AUCUN MODÈLE ICI : le document est un calcul sur les cases que le
            # client a cochées. Le marquer « généré par IA » serait une
            # déclaration fausse, et la marque ne vaut que si elle est rare.
            "ia": False,
            "referentiel": "Parcours IEC 62443 CONSEILPREV v" + parcours_62443.VERSION,
            "perimetre": str(data.get("perimetre") or "").strip()[:300]
                         or "installation industrielle",
            "date": time.strftime("%d/%m/%Y")}
    try:
        if fmt == "pdf":
            blob = livrables_export.build_pdf(md, meta)
            mimetype = "application/pdf"
        else:
            blob = livrables_export.build_docx(md, meta)
            mimetype = ("application/vnd.openxmlformats-officedocument"
                        ".wordprocessingml.document")
    except Exception:
        app.logger.exception("export checklist 62443")
        return jsonify(ok=False, error="export_echec",
                       message="La mise en page a échoué."), 500
    audit.journaliser("checklist62443.export", cible=fmt,
                      detail="%d point(s) coché(s) sur %d"
                             % (verif["faits"], verif["sur"]))
    return send_file(io.BytesIO(blob),
                     download_name="checklist-62443-%s.%s"
                                   % (time.strftime("%Y-%m-%d"), fmt),
                     as_attachment=True, mimetype=mimetype)


@app.route("/api/maturite-ot/referentiel")
def api_maturite_ot_referentiel():
    """L'ECHELLE, LES SIX DOMAINES ET LEURS CIBLES — de quoi dresser le
    formulaire sans le recopier dans la page.

    CE QUE CETTE ROUTE N'EST PAS. Elle ne rend aucun assessment. Un assessment
    se conduit : entretiens, releves, preuves examinees, contradiction. Ce qui
    est structure ici est une AUTO-EVALUATION DECLARATIVE, et la reserve
    voyage dans la reponse plutot qu'a cote.
    """
    return _json_fige("maturite-ot-referentiel",
                      lambda: dict(ok=True,
                                   referentiel=maturite_ot.referentiel()))


@app.route("/api/maturite-ot/evaluer", methods=["POST"])
def api_maturite_ot_evaluer():
    """L'ECART A LA CIBLE, DOMAINE PAR DOMAINE, ET LE CHEMIN DEGRE PAR DEGRE.

    LE NIVEAU N'EST PAS CALCULE, IL EST DECLARE — c'est ce qui separe cette
    route de `checklist/parcours`, qui refuse d'en rendre un. Ici quelqu'un
    choisit, parmi six descriptions concretes, celle qui correspond a ce qu'il
    peut MONTRER ; le module ordonne les ecarts et ne note personne.

    UN DOMAINE NON RENSEIGNE N'EST PAS ZERO. La reponse les rend `null` et les
    liste dans `manquants` : les compter pour zero ferait dire au radar que le
    client n'a rien alors qu'il n'a rien DIT.
    """
    data = request.get_json(silent=True) or {}
    r = maturite_ot.plan(data.get("niveaux"), data.get("cibles"))
    if not r.get("ok"):
        return jsonify(r), 400
    r["livrables"] = maturite_ot.livrables(data.get("niveaux"),
                                           data.get("cibles"))["livrables"]
    return jsonify(r)


@app.route("/api/maturite-ot/emporter", methods=["POST"])
def api_maturite_ot_emporter():
    """L'auto-evaluation, l'ecart et le plan — en PDF ou en Word.

    LE DOCUMENT CIRCULE SANS SA PAGE. Il porte donc en premiere ligne ce
    qu'il n'est pas : `maturite_ot.markdown` place `REFUS_ASSESSMENT` avant
    tout chiffre. Un lecteur qui ne verra jamais ce site doit savoir, avant de
    lire un degre, que personne n'est venu le verifier.
    """
    data = request.get_json(silent=True) or {}
    fmt = str(data.get("format") or "pdf").lower()
    if fmt not in ("pdf", "docx"):
        return jsonify(ok=False, error="format_inconnu",
                       message="Formats servis : pdf, docx."), 400

    # LA MEME PORTE QUE L'ECRAN. Un domaine inconnu est refuse ici comme il
    # l'est a l'ecran, et pour le meme motif : un format de sortie ne doit
    # jamais devenir le chemin de contournement d'un controle.
    verif = maturite_ot.evaluer(data.get("niveaux"), data.get("cibles"))
    if not verif.get("ok"):
        return jsonify(verif), 400
    # UN DOCUMENT SANS UNE SEULE REPONSE NE DIRAIT RIEN. Le servir quand meme
    # produirait un livrable vide qui circulerait comme les autres.
    if not verif.get("repondus"):
        return jsonify(ok=False, error="rien_de_declare",
                       message="Aucun domaine n'est renseigne : il n'y a rien "
                               "a emporter."), 400

    md = maturite_ot.markdown(data.get("niveaux"), data.get("cibles"),
                              titre=str(data.get("titre") or "").strip()[:120]
                                    or None)
    # L'INTITULE PART DANS L'EN-TETE DE CHAQUE PAGE ET DANS LES PROPRIETES DU
    # FICHIER : il porte donc ses accents, comme tous les autres livrables. Un
    # « Auto-evaluation de maturite OT » en tete d'un document dont le corps
    # est accentue se lit comme une chaine qui n'a pas ete relue.
    meta = {"label": "Auto-évaluation de maturité OT",
            "client": str(data.get("client") or "")[:120],
            # Les réponses sont celles du client, le score est un calcul.
            "ia": False,
            "referentiel": "Maturité OT CONSEILPREV v" + maturite_ot.VERSION,
            "perimetre": str(data.get("perimetre") or "").strip()[:300]
                         or "installation industrielle",
            "date": time.strftime("%d/%m/%Y")}
    try:
        if fmt == "pdf":
            blob = livrables_export.build_pdf(md, meta)
            mimetype = "application/pdf"
        else:
            blob = livrables_export.build_docx(md, meta)
            mimetype = ("application/vnd.openxmlformats-officedocument"
                        ".wordprocessingml.document")
    except Exception:
        app.logger.exception("export maturite OT")
        return jsonify(ok=False, error="export_echec",
                       message="La mise en page a échoué."), 500
    audit.journaliser("maturiteot.export", cible=fmt,
                      detail="%d domaine(s) renseigné(s) sur %d"
                             % (verif["repondus"], verif["sur"]))
    return send_file(io.BytesIO(blob),
                     download_name="auto-evaluation-maturite-ot-%s.%s"
                                   % (time.strftime("%Y-%m-%d"), fmt),
                     as_attachment=True, mimetype=mimetype)


@app.route("/api/datacenter/etat-art")
@login_required
def api_datacenter_etat_art():
    """L'etat de l'art : les faits publies, groupes, chacun avec son auteur, sa
    page et LA NATURE de cette source.

    Page reservee aux comptes, comme le reste du menu. Trois des quatre
    documents sont publies par des fournisseurs d'infrastructure : leurs
    mesures sont utiles, leur interet n'est pas neutre, et chaque ligne servie
    le dit. Aucun de ces chiffres n'entre dans le calcul — le moteur tient ses
    constantes de normes, pas de livres blancs.
    """
    try:
        return _json_fige("dc-etat-art",
                          lambda: dict(ok=True, etat=etat_art.etat()))
    except Exception:
        app.logger.exception("etat de l'art datacenter")
        return jsonify(ok=False, error="etat_indisponible",
                       message="L'etat de l'art n'a pas pu etre etabli."), 503


# ══════════════════════════════════════════════════════════
#  FAIRE PARLER LES SOURCES — combler les lacunes SANS fabriquer de faits
# ══════════════════════════════════════════════════════════
# L'etat de l'art nomme quatre trous et n'offrait rien pour les combler. On
# ouvre trois registres, JAMAIS MELANGES :
#
#   1. ce que le cabinet DETIENT DEJA — recherche reelle dans la base, titres
#      et themes reels, donc citable ;
#   2. une LECTURE ASSISTEE de ces extraits — non citable, et elle le dit ;
#   3. ou chercher AU-DEHORS — gisements nommes dans le module, jamais demandes
#      au modele.
#
# LE PIEGE EST DE FOND. Une reponse de modele n'a ni auteur, ni page, ni
# editeur. Versee au milieu des faits cites, elle emprunte leur credit sans en
# avoir la provenance — et un chiffre plausible assorti d'une reference
# plausible est la faute la plus couteuse qu'un cabinet mette dans un dossier.


@app.route("/api/datacenter/lacunes")
@login_required
def api_datacenter_lacunes():
    """Les lacunes et par quoi les instruire, SANS rien consulter.

    OUVERT : ce referentiel ne contient que des questions, des thèmes de
    recherche et des gisements nommes. Aucun extrait, aucun document.
    """
    try:
        return _json_fige("dc-lacunes",
                          lambda: dict(ok=True, referentiel=lacunes.referentiel()))
    except Exception:                                       # noqa: BLE001
        app.logger.exception("referentiel des lacunes")
        return jsonify(ok=False, error="lacunes_indisponibles",
                       message="Le referentiel n'a pas pu etre etabli."), 503


@app.route("/api/datacenter/lacune/<cle>", methods=["POST"])
@login_required
def api_datacenter_lacune(cle):
    """Instruit UNE lacune : la base du cabinet, puis une lecture assistee.

    FERME. La recherche porte sur des documents INTERNES du cabinet : leurs
    titres et leurs extraits n'ont pas a etre publics.

    LA LECTURE ASSISTEE EST OPTIONNELLE ET LE RESTE. Sans cle de modele
    configuree, ou si l'appel echoue, la route rend quand meme les documents
    trouves — ce sont eux qui completent reellement les quatre sources. Faire
    dependre le registre citable de la disponibilite du modele serait perdre le
    solide pour l'accessoire.
    """
    l = lacunes.get(cle)
    if not l:
        return jsonify(ok=False, error="lacune_inconnue",
                       message="Lacune inconnue."), 404
    data = request.get_json(silent=True) or {}

    # ── 1. CE QUE LE CABINET DETIENT ──────────────────────────────────────
    # Les themes d'abord, la recherche libre ensuite : une recherche par
    # pertinence seule ne connait pas le SUJET du dossier, et remonte volontiers
    # une note d'architecture reseau devant une fiche de groupe froid.
    hits, vus = [], set()
    try:
        for th in (l["themes"] + [None]):
            if len(hits) >= 8:
                break
            for h in (rag.search(l["requete"], k=4, public_only=False,
                                 theme=th) or []):
                cid = (h.get("id"), h.get("ordinal"))
                if cid in vus:
                    continue
                vus.add(cid)
                hits.append(h)
    except Exception:                                       # noqa: BLE001
        app.logger.exception("recherche lacune %s", cle)
        hits = []

    internes = [{
        "titre": extraits_mod.titre_document(h.get("title")),
        "theme": h.get("theme") or "",
        "visibilite": h.get("visibility") or "",
        # L'EXTRAIT, PAS LE DOCUMENT. De quoi juger sur pièce s'il faut ouvrir
        # le document — pas de quoi s'en passer.
        "extrait": (h.get("content") or "").strip()[:600],
    } for h in hits]

    # ── 2. LA LECTURE ASSISTEE ────────────────────────────────────────────
    lecture, modele, motif = "", "", ""
    if hits and data.get("lecture") is not False:
        # Le contexte passe par build_context : c'est lui qui CLOT les extraits
        # et qui interdit au modele de leur obeir. Un document empoisonne verse
        # a la base sortirait sinon ici, avec ses consignes intactes.
        contexte = rag.build_context(hits, max_chars=6000)
        system, user = lacunes.prompt_lecture(l, contexte)
        try:
            lecture, modele = assistant.generate(
                str(data.get("model") or "claude"), system, user, context=None)
        except Exception as e:                              # noqa: BLE001
            app.logger.warning("lecture assistee indisponible (%s) : %s", cle, e)
            motif = ("La lecture assistée n'est pas disponible pour le moment. "
                     "Les documents ci-dessus, eux, sont bien ceux de la base "
                     "et se citent tels quels.")
    elif not hits:
        motif = ("Aucun document de la base ne répond à cette question. Rien "
                 "n'est proposé à la lecture : il n'y a rien à lire.")

    return jsonify(
        ok=True,
        lacune={k: l[k] for k in ("cle", "titre", "manque", "question",
                                  "preuve", "hors_portee")},
        interne={"documents": internes, "n": len(internes),
                 "citable": True,
                 "note": "Documents de la base du cabinet. Ils portent un titre "
                         "et un thème : c'est une provenance, et ils se citent."},
        lecture={"texte": lecture, "modele": modele, "motif": motif,
                 "citable": False,
                 "mention": lacunes.MENTION_NON_CITABLE},
        gisements=l["gisements"],
        gisements_note="Gisements de données ouvertes NON CONSULTÉS : ce sont "
                       "des endroits où chercher, pas des réponses.")


@app.route("/api/datacenter/ecart-referentiel")
@login_required
def api_datacenter_ecart_referentiel():
    """L'écart entre ce que le cadre annonce et ce que le moteur produit.

    FERMÉE COMME TOUTE LA FAMILLE `/api/datacenter/`, et le contrôle de
    politique d'accès l'a rappelé au premier chargement. Je l'avais ouverte en
    raisonnant sur son CONTENU — elle ne rend aucune donnée de client, juste un
    profil de sonde sans portée d'étude. Mais la règle de la maison ne porte pas
    sur le contenu : « fermer la page sans fermer son interface ne protège
    rien ». Les pages du centre de données demandent un compte ; leurs
    interfaces aussi, sans exception à plaider.

    ELLE NE DÉCLARE AUCUNE CONFORMITÉ. La colonne « reste à produire » est
    rendue pour chaque étape, y compris quand tout sort : douze mois de mesure,
    une note signée, un vérificateur tiers ne se remplacent par aucun calcul.
    """
    try:
        return jsonify(ok=True, **ecart_referentiel.analyse())
    except Exception:
        app.logger.exception("écart au référentiel")
        return jsonify(ok=False, error="sonde_indisponible"), 502


@app.route("/api/datacenter/decarbonation")
@login_required
def api_datacenter_decarbonation():
    """Le cadre de decarbonation : deux voies, la hierarchie d'attenuation et
    ses leviers, les textes cites avec leur portee.

    OUVERT, comme le reste de la page dont il depend. Ce cadre ne decerne
    aucune conformite ni aucune neutralite : ces qualifications se constatent
    sur dossier complet par un verificateur accredite.
    """
    try:
        return _json_fige("dc-decarbonation",
                          lambda: dict(ok=True, referentiel=decarbonation.referentiel()))
    except Exception:
        app.logger.exception("referentiel decarbonation")
        return jsonify(ok=False, error="referentiel_indisponible",
                       message="Le cadre de decarbonation n'a pas pu etre etabli."), 503


@app.route("/api/datacenter/decarbonation/parcours", methods=["POST"])
@login_required
def api_datacenter_decarbonation_parcours():
    """Ou l'on passe et ou l'on bute, sur une voie ou sur les deux.

    Le premier point de blocage est la seule information qui commande une
    action ; les etapes suivantes servent a voir venir.
    """
    data = request.get_json(silent=True) or {}
    profil = _profil_datacenter(data)
    if not profil.get("puissance_it_kw"):
        return jsonify(ok=False, error="puissance_absente",
                       message="La puissance informatique installée est nécessaire."), 400
    v = (data.get("voie") or "").strip()
    voies = [v] if v in decarbonation.VOIES else list(decarbonation.VOIES)
    try:
        return jsonify(ok=True,
                       parcours={x: decarbonation.parcours(profil, x) for x in voies},
                       rendez_vous=decarbonation.RENDEZ_VOUS)
    except Exception:
        app.logger.exception("parcours decarbonation")
        return jsonify(ok=False, error="calcul",
                       message="Le parcours n'a pas pu être établi."), 500


# ══════════════════════════════════════════════════════════
#  LE BORDEREAU DE TRANSMISSION — ce qui voyage AVEC le document
# ══════════════════════════════════════════════════════════
# Un document se lit correctement SUR LA PAGE : elle dit la phase, la tolérance,
# ce qui reste à produire. Le fichier, lui, part seul. Aux achats, une enveloppe
# d'avant-projet devient un budget ; à l'exploitation, une valeur de conception
# devient une consigne. Personne n'a menti — le contexte est resté ici.
#
# Le bordereau le fait voyager avec le fichier. Optionnel : sans destinataire
# demandé, l'export ne change pas d'un octet.


@app.route("/api/transmission")
@login_required
def api_transmission():
    """Le vocabulaire des fonctions destinataires, et ce que le lien ne porte pas.

    OUVERT : il ne décrit que des fonctions et des mises en garde, rien d'un
    dossier. Servi par une route à lui parce que TROIS pages s'en servent — le
    greffer sur le référentiel de l'une d'elles obligerait les deux autres à
    charger un référentiel qui ne les concerne pas.
    """
    return _json_fige("transmission", lambda: dict(
        ok=True, destinataires=transmission.destinataires(),
        natures=transmission.natures(),
        exclus=transmission.EXCLUS,
        version=transmission.VERSION))


def _poser_bordereau(md, meta, nature, data):
    """Pose le bordereau en tête du document, si le client en demande un.

    NE FAIT JAMAIS ÉCHOUER L'EXPORT. Une fonction inconnue sort du bordereau et
    y est nommée ; le document, lui, part quand même. Un export qui échoue parce
    qu'une clé a bougé prive le client de son document — et il recommencera sans
    bordereau, ce qui est exactement ce qu'on cherchait à éviter.

    REFUSE CE QUI RESSEMBLE À UNE PERSONNE. Le champ attend une clé de fonction.
    Un nom accepté « pour être serviable » ferait entrer le document au registre
    des traitements, et personne ne l'aurait décidé.
    """
    dest = str((data or {}).get("destinataire") or "").strip()[:40]
    if not dest:
        return md, None
    if transmission.nominatif(dest):
        return md, {"refuses": [{
            "champ": "destinataire", "valeur": "(écarté)",
            "motif": "la transmission désigne une FONCTION, jamais une "
                     "personne — rien de nominatif ne circule"}],
            "markdown": "", "destinataire": None,
            "exclus": transmission.EXCLUS}
    md2, b = transmission.poser(md, nature, dest, {
        "phase": meta.get("phase"), "indice": meta.get("indice"),
        "client": meta.get("client"), "perimetre": meta.get("perimetre"),
        "date": meta.get("date")})
    if b and b.get("destinataire"):
        # Le cartouche du document le porte aussi : le bordereau est en page de
        # garde, et une page de garde se détache d'un tirage agrafé.
        meta["destinataire"] = b["destinataire"]
    return md2, b


@app.route("/api/datacenter/decarbonation/dossier", methods=["POST"])
@login_required
def api_datacenter_decarbonation_dossier():
    """Le plan de l'etude pour une etape, avec ce que le moteur y verse
    legitimement et ce qui doit venir de la mesure, du contrat ou du tiers
    verificateur."""
    data = request.get_json(silent=True) or {}
    profil = _profil_datacenter(data)
    code = str(data.get("etape") or "").strip().upper()[:12]
    try:
        d = decarbonation.dossier(profil, code, data)
    except Exception:
        app.logger.exception("dossier decarbonation")
        return jsonify(ok=False, error="calcul",
                       message="Le dossier n'a pas pu être établi."), 500
    if not d.get("connu"):
        return jsonify(ok=False, error="etape_inconnue",
                       message=d.get("motif", "Étape inconnue.")), 404
    return jsonify(ok=True, dossier=d)


def _dossier_decarbonation_markdown(d, client=""):
    """Le dossier d'une étape de décarbonation, en Markdown.

    Écrit ici et non par un modèle, pour la même raison que l'étude de phase :
    ce document sépare ce que le moteur peut verser de ce qui doit venir de la
    mesure, du contrat ou du vérificateur — et cette frontière-là se calcule,
    elle ne se rédige pas.

    CE QUE L'ÉTAPE VERROUILLE VIENT AVANT CE QU'ELLE PRODUIT. Un lecteur qui
    découvre au dernier chapitre qu'une décision de périmètre oblige à
    recalculer toutes les années publiées a déjà pris la décision.
    """
    L = []
    A = L.append
    A("# %s — %s" % (d["code"], d["nom"]))
    A("")
    A("*Voie « %s » · rang %s de la séquence*"
      % (d.get("voie_nom") or d.get("voie"), d.get("rang") or "—"))
    if client:
        A("")
        A("**Client** — %s" % client)
    A("")

    A("## 1. Objet de l'étape")
    A("")
    A(d["objet"])
    A("")
    A("**Ce qui s'y décide.** %s" % d["decide"])
    A("")
    A("**Ce qu'elle verrouille.** %s" % d["verrouille"])
    A("")
    A("**La preuve attendue.** %s" % d["preuve"])
    A("")

    A("## 2. Ce que le moteur verse à ce dossier")
    A("")
    A(d.get("apport_texte") or "")
    A("")
    recevables = [g for g in d.get("grandeurs") or [] if g["statut"] == "recevable"]
    autres = [g for g in d.get("grandeurs") or [] if g["statut"] != "recevable"]
    if recevables:
        A("### Grandeurs recevables à ce stade")
        A("")
        A("| Grandeur | Valeur | Unité | Incertitude |")
        A("|---|---|---|---|")
        for g in recevables:
            A("| %s | %s | %s | %s |"
              % (g["nom"], g.get("valeur"), g.get("unite") or "",
                 g.get("incertitude") or "—"))
        A("")
    if autres:
        # LE CHAPITRE QUI COMPTE. Une grandeur non recevable présentée comme un
        # résultat traverse tout le projet sans que personne ne la remplace.
        A("### Grandeurs NON recevables en l'état — à produire")
        A("")
        A("| Grandeur | Valeur indicative | Ce qui la bloque |")
        A("|---|---|---|")
        for g in autres:
            A("| %s | %s %s | %s |"
              % (g["nom"], g.get("valeur"), g.get("unite") or "",
                 ", ".join(g.get("postes_bloquants") or []) or "non instruit"))
        A("")

    ap = d.get("aptitude") or {}
    A("## 3. Ce qui manque pour franchir l'étape")
    A("")
    A(ap.get("verdict") or "")
    A("")
    for titre, cle in (("Entrées à renseigner", "entrees_manquantes"),
                       ("Facteurs à remplacer par une donnée réelle",
                        "substitutions_a_faire")):
        items = ap.get(cle) or []
        if items:
            A("**%s.**" % titre)
            for x in items:
                A("- %s" % (x.get("nom") if isinstance(x, dict) else x))
            A("")

    sections = d.get("sections") or []
    if sections:
        A("## 4. Plan de l'étude")
        A("")
        for i, s in enumerate(sections, 1):
            A("%d. %s" % (i, s if isinstance(s, str) else s.get("nom", "")))
        A("")

    textes = d.get("textes") or []
    if textes:
        A("## 5. Ce que les textes exigent, et jusqu'où")
        A("")
        for t in textes:
            A("**%s** — %s" % (t.get("nom"), t.get("dit")))
            A("")
            A("*Portée : %s.* %s" % (t.get("portee_texte") or t.get("portee"),
                                     t.get("reserve") or ""))
            A("")

    rdv = d.get("rendez_vous") or []
    if rdv:
        A("## 6. Ce que cette étape attend d'une autre voie")
        A("")
        for r in rdv:
            A("- **%s ↔ %s** — %s"
              % (r.get("inventaire"), r.get("trajectoire"), r.get("lien")))
        A("")

    # Ancrage management : le plan d'actions de cette étape a un système qui
    # le porte en exploitation — sans lui, la trajectoire reste un document.
    m50 = datacenter.MANAGEMENT["iso_50001"]
    A("## Ancrage dans le management de l'énergie (ISO 50001)")
    A("")
    A(m50["apporte"])
    A("")
    A("**Indicateurs.** %s" % m50["ipe_naturel"])
    A("")
    A("Ce que la mise en œuvre exige — et que cette étape peut préparer :")
    A("")
    for x in m50["exige"]:
        A("- " + x)
    A("")
    A("**Certification.** %s Les seuils d'assujettissement de l'art. 11 EED "
      "(10 TJ/an : audit ; 85 TJ/an : SMÉn certifié), calculés pour ce "
      "profil, figurent dans la note de calcul de l'étude." % m50["certifiable"])
    A("")

    A("---")
    A("")
    A("*Moteur de décarbonation CONSEILPREV v%s. Document de travail : les "
      "grandeurs signalées « à produire » ne sont pas acquises.*"
      % d.get("version_moteur", decarbonation.VERSION))
    return "\n".join(L)


@app.route("/api/datacenter/decarbonation/export", methods=["POST"])
@login_required
def api_datacenter_decarbonation_export():
    """Le dossier d'étape de décarbonation, en Word ou PDF.

    IL MANQUAIT. La note de calcul, l'étude de phase, la pièce et la stratégie
    s'exportaient toutes ; la trajectoire, non. Elle s'affichait, et le seul
    moyen de l'emporter était de sélectionner le texte à l'écran — c'est-à-dire
    de perdre les tableaux, la distinction entre grandeur recevable et grandeur
    à produire, et les réserves des textes. Un résultat qui ne sort pas du site
    n'est pas un livrable.

    FERMÉ comme les autres exports : le document porte le nom du client et le
    profil de son projet.
    """
    data = request.get_json(silent=True) or {}
    profil = _profil_datacenter(data)
    code = str(data.get("etape") or "").strip().upper()[:12]
    if not profil.get("puissance_it_kw"):
        return jsonify(ok=False, error="puissance_absente",
                       message="La puissance informatique installée est nécessaire."), 400
    try:
        d = decarbonation.dossier(profil, code, data)
    except Exception:
        app.logger.exception("export dossier decarbonation")
        return jsonify(ok=False, error="calcul",
                       message="Le dossier n'a pas pu être établi."), 500
    if not d.get("connu"):
        return jsonify(ok=False, error="etape_inconnue",
                       message=d.get("motif", "Étape inconnue.")), 404
    fmt = (data.get("format") or "docx").strip().lower()
    if fmt not in ("docx", "pdf"):
        fmt = "docx"
    client = str(data.get("client") or "").strip()[:120]
    md = _dossier_decarbonation_markdown(d, client)
    meta = {"label": "%s — %s" % (d["code"], d["nom"]),
            "numero": "DECARB-%s" % d["code"],
            "phase": "Décarbonation, voie « %s »"
                     % (d.get("voie_nom") or d.get("voie")),
            "indice": "01",
            "client": client,
            "ia": False,
            "referentiel": "Moteur de décarbonation CONSEILPREV v" + decarbonation.VERSION,
            "perimetre": "%s kW informatiques" % round(profil["puissance_it_kw"]),
            "date": time.strftime("%d/%m/%Y"),
            "statut": "Document de travail — grandeurs « à produire » non acquises",
            "sources": [{"title": "Moteur de décarbonation CONSEILPREV v"
                                  + decarbonation.VERSION,
                         "theme": "hiérarchie d'atténuation"},
                        {"title": "Moteur d'ingénierie CONSEILPREV v"
                                  + datacenter.VERSION,
                         "theme": "calcul déterministe"}]}
    md, bord = _poser_bordereau(md, meta, "trajectoire", data)
    try:
        if fmt == "pdf":
            blob = livrables_export.build_pdf(md, meta)
            mimetype = "application/pdf"
        else:
            blob = livrables_export.build_docx(md, meta)
            mimetype = ("application/vnd.openxmlformats-officedocument"
                        ".wordprocessingml.document")
    except Exception:
        app.logger.exception("mise en page dossier decarbonation")
        return jsonify(ok=False, error="mise_en_page",
                       message="Le document n'a pas pu être mis en page."), 500
    nom = _safe_download_name("decarbonation-%s.%s" % (d["code"].lower(), fmt))
    resp = Response(blob, mimetype=mimetype)
    resp.headers["Content-Disposition"] = 'attachment; filename="%s"' % nom
    resp.headers["Cache-Control"] = "no-store"
    if bord and bord.get("refuses"):
        # LE REFUS SE DIT, ET IL ARRIVE AVEC LE FICHIER. Un bordereau tombé en
        # silence rend le document sans ses réserves, et le client croit les
        # avoir transmises.
        resp.headers["X-Bordereau"] = "refus"
    return resp


@app.route("/api/datacenter/strategie/questionnaire")
@login_required
def api_datacenter_strategie_questionnaire():
    """Ce qu'on demande au client : trois perspectives sur quatre.

    La quatrieme — la science — n'est pas demandee. La recueillir comme une
    opinion rendrait indetectables les ecarts entre perception et realite, qui
    sont l'apport central de la methode.
    """
    try:
        return _json_fige("dc-strategie-questionnaire",
                          lambda: dict(ok=True, questionnaire=strategie_dd.questionnaire()))
    except Exception:
        app.logger.exception("questionnaire strategie DD")
        return jsonify(ok=False, error="questionnaire_indisponible",
                       message="Le questionnaire n'a pas pu être établi."), 503


@app.route("/api/datacenter/strategie", methods=["POST"])
@login_required
def api_datacenter_strategie():
    """La strategie de developpement durable, calculee depuis les reponses.

    OUVERT comme le reste de la page : le calcul est deterministe, sans modele
    de langage, et les reponses ne sont pas conservees — elles transitent, elles
    ne sont pas ecrites.
    """
    data = request.get_json(silent=True) or {}
    profil = _profil_datacenter(data.get("profil") or {})
    try:
        s = strategie_dd.strategie(data, profil)
    except Exception:
        app.logger.exception("strategie DD datacenter")
        return jsonify(ok=False, error="calcul",
                       message="La stratégie n'a pas pu être établie."), 500
    return jsonify(ok=True, strategie=s)


@app.route("/api/datacenter/strategie/export", methods=["POST"])
@login_required
def api_datacenter_strategie_export():
    """Le livrable d'ouverture en Word ou PDF.

    FERME, comme les autres exports : le document porte le nom du client, son
    site et ses arbitrages. C'est une piece de dossier, pas une page publique.
    """
    data = request.get_json(silent=True) or {}
    profil = _profil_datacenter(data.get("profil") or {})
    try:
        s = strategie_dd.strategie(data, profil)
        md = strategie_dd.markdown(s)
    except Exception:
        app.logger.exception("export strategie DD")
        return jsonify(ok=False, error="calcul",
                       message="La stratégie n'a pas pu être établie."), 500
    fmt = (data.get("format") or "docx").strip().lower()
    if fmt not in ("docx", "pdf"):
        fmt = "docx"
    projet = s["identite"]["projet"] or "Centre de données"
    meta = {"label": "Stratégie de développement durable — %s" % projet,
            "numero": "STRAT-DD",
            "phase": "Ouverture d'étude",
            "indice": "01",
            "client": s["identite"]["organisation"],
            "ia": False,
            "referentiel": "Méthode des quatre perspectives v" + strategie_dd.VERSION,
            "perimetre": s["identite"]["site"] or projet,
            "date": time.strftime("%d/%m/%Y"),
            "sources": [
                {"title": "Méthode des quatre perspectives — strategie_dd v"
                          + strategie_dd.VERSION,
                 "theme": "raison d'être, parties prenantes, science, valeur"},
                {"title": "Moteur d'ingénierie CONSEILPREV v" + datacenter.VERSION,
                 "theme": "calcul déterministe"},
            ]}
    md, bord = _poser_bordereau(md, meta, "strategie_dd", data)
    try:
        if fmt == "pdf":
            blob = livrables_export.build_pdf(md, meta)
            mimetype = "application/pdf"
        else:
            blob = livrables_export.build_docx(md, meta)
            mimetype = ("application/vnd.openxmlformats-officedocument"
                        ".wordprocessingml.document")
    except Exception:
        app.logger.exception("export stratégie DD")
        return jsonify(ok=False, error="export_echec",
                       message="La mise en page a échoué."), 500
    audit.journaliser("datacenter.strategie.export", cible="STRAT-DD",
                      detail="%s · %d enjeu(x) retenu(s)" % (fmt, len(s["retenus"])))
    return send_file(io.BytesIO(blob),
                     download_name="strategie-dd.%s" % fmt,
                     as_attachment=True, mimetype=mimetype)


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


import repartition_honoraires  # noqa: E402  — tableau de répartition MOE
import moe_dc  # noqa: E402  — barème d'honoraires de maîtrise d'œuvre,
              # partagé à l'identique avec conseilprev (Sentinel)


@app.route("/api/datacenter/moe/repartition", methods=["POST"])
@login_required
def api_datacenter_moe_repartition():
    """Le tableau de répartition des honoraires, en données ou en classeur.

    POURQUOI CETTE ROUTE EXISTE. Le tableau de situation des honoraires est la
    pièce que la maîtrise d'ouvrage réclame au moment de contractualiser :
    phases MOP en lignes, cotraitants en colonnes. Il était jusqu'ici rempli à
    la main depuis le calcul affiché à l'écran — c'est-à-dire recopié, avec ce
    que la recopie coûte.

    LA MÊME GARDE QUE LE CALCUL QU'IL MET EN FORME. Ce tableau ne montre rien
    de plus que `/api/datacenter/moe` ; lui ouvrir une porte plus large
    reviendrait à publier par le classeur ce que la page refuse à l'écran.

    `?format=xlsx` rend le classeur ; sans quoi les mêmes données en JSON, pour
    que la page montre à l'écran EXACTEMENT ce qui sera téléchargé.
    """
    d = request.get_json(silent=True) or {}
    try:
        mission = (d.get("mission") or ingenierie_dc.MISSION_DEFAUT).strip()
        p = moe_dc.portee(mission)
        if not p["couvre"]:
            return jsonify(ok=False, error="hors_portee", mission=mission,
                           dit=p["dit"]), 400
        trav = d.get("travaux_meur")
        if isinstance(trav, (int, float)):
            trav = [float(trav), float(trav)]
        if not isinstance(trav, (list, tuple)) or len(trav) != 2:
            return jsonify(ok=False, error="travaux_meur attendu : [bas, haut]"), 400
        trav = [max(0.0, float(trav[0])), max(0.0, float(trav[1]))]
        if trav[1] <= 0:
            return jsonify(ok=False, error="montant de travaux nul"), 400
        try:
            pt = d.get("part_technique")
            pt = None if pt in (None, "") else float(pt)
        except (TypeError, ValueError):
            pt = None
        demandees = d.get("phases")
        phases = ([x for x in (demandees or []) if x in p["phases"]]
                  if demandees is not None else p["phases"])
        cote = "bas" if (d.get("cote") == "bas") else "haut"
        # À L'EURO PRÈS, PARCE QUE CE TABLEAU RÉPARTIT AU LIEU D'AFFICHER.
        # Le barème arrondit au millier — bonne granularité pour lire un ordre
        # de grandeur, mais ce tableau additionne soixante-cinq montants ainsi
        # arrondis : la somme s'écartait de la base contractuelle de 1,21 % sur
        # un projet de 2 M€ de travaux. Dans une pièce qui sert à payer, ce
        # n'est plus un arrondi.
        with moe_dc.precision_fine():
            r = moe_dc.honoraires_directs(trav, part_technique=pt, phases=phases,
                                          missions=d.get("missions"),
                                          taux_perso=d.get("taux_perso") or None)
        if not r.get("ok"):
            return jsonify(r), 400
        operation = str(d.get("operation") or "")[:120]
        reference = str(d.get("reference") or "")[:60]
        if (request.args.get("format") or "") != "xlsx":
            out = repartition_honoraires.etat(r, cote, operation, reference)
            out["mission"] = mission
            return jsonify(out)
        blob = repartition_honoraires.octets(r, cote, operation, reference)
        return send_file(io.BytesIO(blob),
                         download_name="repartition-honoraires-moe.xlsx",
                         as_attachment=True,
                         mimetype="application/vnd.openxmlformats-"
                                  "officedocument.spreadsheetml.sheet")
    except Exception as e:  # noqa: BLE001
        app.logger.error("MOE_REPARTITION_ERR: %s", e)
        return jsonify(ok=False, error="tableau indisponible"), 500


@app.route("/api/datacenter/moe/engagement", methods=["POST"])
@login_required
def api_datacenter_moe_engagement():
    """Ce que la maîtrise d'œuvre ENGAGE — pas seulement ce qu'elle coûte.

    moe_dc.engagement(), plafond_penalite() et penalite_retard() calculent le
    seuil de tolérance, le plafond légal de pénalité (15 % des honoraires
    postérieurs à l'attribution, art. 30.II du décret 93-1268) et la pénalité
    de retard journalière — mais rien ne les appelait : deux offres au même
    montant ne portent pas la même promesse si leurs taux de tolérance
    diffèrent, et la page ne le montrait nulle part.

    LA MÊME GARDE QUE LE CALCUL QU'ELLE ENGAGE. Le plafond se déduit de la
    rémunération phase par phase ; cette route recalcule donc le chiffrage
    elle-même plutôt que de faire confiance à un résultat renvoyé par le
    client, exactement comme /moe/repartition.
    """
    d = request.get_json(silent=True) or {}
    try:
        mission = (d.get("mission") or ingenierie_dc.MISSION_DEFAUT).strip()
        p = moe_dc.portee(mission)
        if not p["couvre"]:
            return jsonify(ok=False, error="hors_portee", mission=mission,
                           dit=p["dit"]), 400
        trav = d.get("travaux_meur")
        if isinstance(trav, (int, float)):
            trav = [float(trav), float(trav)]
        if not isinstance(trav, (list, tuple)) or len(trav) != 2:
            return jsonify(ok=False, error="travaux_meur attendu : [bas, haut]"), 400
        trav = [max(0.0, float(trav[0])), max(0.0, float(trav[1]))]
        if trav[1] <= 0:
            return jsonify(ok=False, error="montant de travaux nul"), 400
        try:
            pt = d.get("part_technique")
            pt = None if pt in (None, "") else float(pt)
        except (TypeError, ValueError):
            pt = None
        demandees = d.get("phases")
        phases = ([x for x in (demandees or []) if x in p["phases"]]
                  if demandees is not None else p["phases"])
        resultat = moe_dc.honoraires_directs(
            trav, part_technique=pt, phases=phases, missions=d.get("missions"),
            taux_perso=d.get("taux_perso") or None)
        if not resultat.get("ok"):
            return jsonify(resultat), 400

        def _nombre(cle):
            v = d.get(cle)
            if v in (None, ""):
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        cout_meur = _nombre("cout_meur")
        if cout_meur is None:
            return jsonify(ok=False, error="cout_absent",
                           message="Le coût prévisionnel ou de réalisation est "
                                   "requis pour situer un seuil de tolérance."), 400

        eng = moe_dc.engagement(
            cout_meur, _nombre("taux_tolerance_pct"),
            cout_reference_meur=_nombre("cout_reference_meur"),
            taux_penalite_pct=_nombre("taux_penalite_pct"),
            resultat=resultat, cle=d.get("cle") or "cout_realisation")
        # AUCUN TAUX N'EST PROPOSÉ, PAR CHOIX DU MODÈLE : engagement() refuse
        # alors sans planter, avec un message qui le dit. Ce n'est pas une
        # erreur de la requête — la traiter en 400 aurait bloqué la pénalité
        # de retard, demandée séparément, pour une information qu'elle n'a
        # jamais réclamée. Seul un identifiant d'engagement inconnu, un bug
        # d'appelant plutôt qu'un taux qui reste à négocier, reste un 400.
        if eng.get("erreur") == "engagement_inconnu":
            return jsonify(eng), 400
        out = {"ok": True, "engagement": eng, "mission": mission}

        phase_retard = d.get("phase_retard")
        jours_retard = _nombre("jours_retard")
        if phase_retard and jours_retard is not None:
            out["retard"] = moe_dc.penalite_retard(resultat, phase_retard, jours_retard)
        return jsonify(out)
    except Exception as e:  # noqa: BLE001
        app.logger.error("MOE_ENGAGEMENT_ERR: %s", e)
        return jsonify(ok=False, error="engagement_indisponible"), 500


@app.route("/api/datacenter/moe", methods=["GET", "POST"])
@login_required
def api_datacenter_moe():
    """Le prix de la maîtrise d'œuvre, selon la mission et les phases confiées.

    EN GET : le barème — treize missions, cinq groupes de phases traduits dans
    le vocabulaire de la loi MOP, et ce que chaque groupe recouvre.

    EN POST : le chiffrage. CETTE PAGE NE CALCULE PAS L'ENVELOPPE — elle le dit
    déjà en toutes lettres et renvoie vers conseilprev pour cela. Le montant des
    TRAVAUX est donc une entrée, pas un résultat : le module ne le reconstitue
    pas, et sans lui il ne rend rien.

    LE BARÈME NE CHIFFRE QUE DE LA MAÎTRISE D'ŒUVRE. Pour une assistance à
    maîtrise d'ouvrage, un bureau d'études dans la MOE d'un tiers, une
    ingénierie EPC ou un audit, il refuse — un nombre faux et crédible est la
    pire des deux combinaisons."""
    if request.method == "GET":
        def _bareme():
            ref = moe_dc.referentiel()
            ref["ok"] = True
            ref["sante"] = moe_dc.sante()
            return ref
        return _json_fige("dc-moe-bareme", _bareme)

    d = request.get_json(silent=True) or {}
    mission = (d.get("mission") or ingenierie_dc.MISSION_DEFAUT).strip()
    p = moe_dc.portee(mission)
    if not p["couvre"]:
        return jsonify(ok=False, error="hors_portee", mission=mission,
                       message=p["dit"]), 200

    trav = d.get("travaux_meur") or []
    try:
        trav = [float(x) for x in trav][:2]
    except (TypeError, ValueError):
        trav = []
    if len(trav) == 1:
        trav = [trav[0], trav[0]]
    if len(trav) != 2 or min(trav) <= 0:
        return jsonify(ok=False, error="travaux_absents",
                       message="Indiquez le montant des travaux : ce module "
                               "chiffre l'énergie, l'eau et le carbone, pas "
                               "l'investissement. L'enveloppe se calcule sur "
                               "conseilprev, et son montant se reporte ici.",
                       renvoi=ingenierie_dc.PHASES[0].get("renvoi")
                       if ingenierie_dc.PHASES else None), 400

    pt = d.get("part_technique")
    try:
        pt = None if pt in (None, "") else float(pt)
    except (TypeError, ValueError):
        pt = None
    # Le client peut restreindre encore, mais jamais élargir au-delà de ce que
    # sa mission couvre : proposer l'assistance aux contrats à qui a pris une
    # conception seule lui ferait payer une phase qu'il n'a pas confiée.
    demandees = d.get("phases")
    phases = ([x for x in (demandees or []) if x in p["phases"]]
              if demandees is not None else p["phases"])
    r = moe_dc.honoraires_directs(trav, part_technique=pt, phases=phases,
                                  missions=d.get("missions"),
                                  taux_perso=d.get("taux_perso") or None)
    if not r.get("ok"):
        return jsonify(r), 400
    r["mission"] = mission
    r["portee"] = p
    r["consequences"] = moe_dc.consequences(r["phases_retenues"])
    r["version"] = moe_dc.VERSION
    return jsonify(r)


@app.route("/api/datacenter/ingenierie")
@login_required
def api_datacenter_ingenierie():
    """Le cadre de phases : deux filières, leurs correspondances, et les postes
    du référentiel dont l'ordre de grandeur cesse de suffire en cours de projet."""
    # Le plus gros JSON du site (642 Ko, 125 Ko gz) : re-sérialisé et re-gzippé
    # à chaque visite de /ingenierie-datacenter, il coûtait 18 ms de CPU sous
    # GIL par requête. Figé par processus, revalidé par ETag : 304 sans corps.
    return _json_fige("dc-ingenierie",
                      lambda: dict(ok=True, referentiel=ingenierie_dc.referentiel()))


@app.route("/api/datacenter/economiste")
@login_required
def api_datacenter_economiste():
    """Le referentiel de l'economiste : natures d'operation, postes, quantites.

    Il ne porte AUCUN prix, et c'est le point : le referentiel du cabinet ne
    contient aucune operation livree publiant a la fois sa capacite et son
    investissement, donc aucun ratio ne peut en etre tire. La route sert la
    structure ; les prix viennent du bordereau du client.
    """
    return jsonify(ok=True, referentiel=econome_dc.referentiel())


@app.route("/api/datacenter/economiste/chiffrer", methods=["POST"])
@login_required
def api_datacenter_economiste_chiffrer():
    """Le chiffrage d'une operation : quantite x prix unitaire, poste par poste.

    Un poste sans prix ressort `non_chiffree` avec sa raison plutot que zero :
    un zero muet ferait croire que le poste n'est pas du.
    """
    data = request.get_json(silent=True) or {}
    r = econome_dc.chiffrer(data.get("operation"),
                            data.get("quantites"),
                            data.get("prix_unitaires"),
                            data.get("provision_pct"),
                            data.get("provenances"))
    if not r.get("ok"):
        return jsonify(r), 400
    return jsonify(r)


@app.route("/api/datacenter/economiste/maitrise-oeuvre", methods=["POST"])
@login_required
def api_datacenter_economiste_moe():
    """Le pont : le chiffrage des travaux prolonge par celui de la MOE.

    CE QUE CETTE ROUTE APPORTE, et qu'aucune des deux ne pouvait donner seule :
    la part technique des travaux devient une CONSEQUENCE du chiffrage au lieu
    d'une hypothese a 70 %, dont le bareme dit lui-meme qu'elle pese plus lourd
    que n'importe quel taux -- les taux etant inverses entre clos-couvert et lot
    technique. Et les missions proposees suivent la nature de l'operation : une
    rehabilitation ne paie pas de VRD sur un batiment qu'elle ne touche pas.

    Les deux incompletudes -- postes sans prix, missions sans taux -- remontent
    cote a cote et ne sont jamais fondues en un indicateur unique.
    """
    data = request.get_json(silent=True) or {}
    c = econome_dc.chiffrer(data.get("operation"),
                            data.get("quantites"),
                            data.get("prix_unitaires"),
                            data.get("provision_pct"),
                            data.get("provenances"))
    if not c.get("ok"):
        return jsonify(c), 400
    r = econome_dc.avec_maitrise_oeuvre(c,
                                        phases=data.get("phases"),
                                        missions=data.get("missions"),
                                        taux_perso=data.get("taux_perso"))
    if not r.get("ok"):
        # Un refus motive n'est pas une panne : une maintenance annuelle NE
        # PORTE PAS d'honoraires au pourcentage, et le dire est le service rendu.
        return jsonify(r), 400
    r["chiffrage"] = c
    return jsonify(r)


@app.route("/api/datacenter/economiste/missions", methods=["GET"])
@login_required
def api_datacenter_economiste_missions():
    """Les missions proposees pour une nature d'operation, et POURQUOI.

    Trois etats, et le troisieme est le plus utile : retenue, ecartee avec sa
    raison, ou retenue MAIS a qualifier -- le module dit alors ce qui decide
    (categorie du SSI, classement ICPE) et refuse de trancher a la place.
    """
    r = econome_dc.missions_pour(request.args.get("operation"))
    return jsonify(r) if r.get("ok") else (jsonify(r), 400)


@app.route("/api/datacenter/economiste/parcours", methods=["GET"])
@login_required
def api_datacenter_economiste_parcours():
    """Le parcours du chiffrage : dans quel ordre s'y prendre, et ce que ça
    engage — avec les comptes de CETTE nature d'operation.

    Sans parametre, le parcours porte les comptes d'ensemble et le referentiel
    le sert deja. Avec une nature, les comptes portent sur ce qu'elle demande :
    annoncer « cinq quantites » a qui n'en remplira que trois ferait chercher
    deux chiffres qui ne seront jamais demandes.
    """
    r = econome_dc.parcours(request.args.get("operation") or None)
    return jsonify(r) if r.get("ok") else (jsonify(r), 400)


@app.route("/api/datacenter/ingenierie/disponibilite", methods=["POST"])
@login_required
def api_datacenter_disponibilite():
    """Ce qu'un niveau de disponibilité EXIGE, et ce que la redondance INSTALLE.

    Les deux sont rendus séparément, et c'est tout l'objet de la route : le
    référentiel externe dit ce qu'il faut atteindre, l'arithmétique dit combien
    d'unités cela représente. Les confondre fait annoncer « Tier IV » sur un
    dossier qui a compté N+1 groupes froid — l'erreur se voit au chiffrage, six
    mois plus tard.

    Aucun niveau n'est décerné ici : une certification se constate sur dossier
    complet par l'organisme, jamais par un formulaire.
    """
    data = request.get_json(silent=True) or {}
    try:
        d = ingenierie_dc.disponibilite(data.get("tier"),
                                        data.get("n_unites"),
                                        data.get("schema"))
    except Exception:
        app.logger.exception("disponibilité datacenter")
        return jsonify(ok=False, error="calcul"), 500
    return jsonify(ok=True, disponibilite=d)


@app.route("/api/datacenter/ingenierie/parcours", methods=["POST"])
@login_required
def api_datacenter_ingenierie_parcours():
    """Où l'on passe et où l'on bute, sur toute une filière.

    Le premier point de blocage est la seule information qui commande une
    action : les phases suivantes servent à voir venir, pas à travailler en
    parallèle.
    """
    data = request.get_json(silent=True) or {}
    rejets = []
    profil = _profil_datacenter(data, rejets)
    if not profil.get("puissance_it_kw"):
        illisible = next((r for r in rejets
                          if r["champ"] == "puissance_it_kw"), None)
        if illisible:
            return jsonify(ok=False, error="puissance_illisible",
                           message=illisible["message"], rejets=rejets), 400
        return jsonify(ok=False, error="puissance_absente",
                       message="La puissance informatique installée est nécessaire."), 400
    fil = (data.get("filiere") or "").strip()
    filieres = [fil] if fil in ingenierie_dc.FILIERES else list(ingenierie_dc.FILIERES)
    try:
        return jsonify(ok=True,
                       parcours={f: ingenierie_dc.parcours(profil, f) for f in filieres},
                       rejets=rejets,
                       lecture_rejets=_lecture_rejets(rejets),
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
        d = ingenierie_dc.dossier(profil, code, data)
    except Exception:
        app.logger.exception("dossier ingénierie datacenter")
        return jsonify(ok=False, error="calcul",
                       message="Le dossier n'a pas pu être établi."), 500
    if not d.get("connu"):
        return jsonify(ok=False, error="phase_inconnue",
                       message=d.get("motif", "Phase inconnue.")), 404
    return jsonify(ok=True, dossier=d)


# ═══════════════════════════════════════════════════════════════════════════
#  LE CRIBLAGE ICPE, LA PHASE TRAVAUX ET LE DOSSIER MARCHÉ
# ═══════════════════════════════════════════════════════════════════════════
# QUATRE ROUTES QUI PROLONGENT L'INGÉNIERIE, et qui ne calculent presque rien :
# elles servent des tables et un criblage. Elles sont en POST parce qu'elles
# prennent le profil du projet, pas parce qu'elles écrivent quoi que ce soit —
# aucune n'a d'effet de bord, et deux appels identiques rendent le même
# résultat.


def _profil_reseau(data, rejets=None):
    """Les entrées propres à l'étude de raccordement.

    MÊME LECTEUR DE NOMBRE, MÊME RAISON que pour le criblage réglementaire :
    une valeur illisible doit RESSORTIR dans les rejets, pas disparaître. Une
    part d'effacement saisie « 30 » pour trente pour cent doit se voir
    refuser, et non se ramener en silence à un — ce qui rendrait un résultat
    plausible sur une saisie fausse.
    """
    profil = {}
    for champ in reseau_dc.CHAMPS:
        cid = champ["id"]
        if cid not in data or data[cid] in ("", None):
            continue
        brut = data[cid]
        if champ["type"] == "nombre":
            valeur, motif = _lire_nombre(brut, champ)
            if motif:
                if rejets is not None:
                    rejets.append({"champ": cid,
                                   "label": champ.get("label") or cid,
                                   "saisi": str(brut)[:40], "message": motif})
                continue
            profil[cid] = valeur
        else:
            profil[cid] = str(brut)[:40]
    # La répartition des charges n'est pas un champ simple : c'est un dict de
    # parts, et le module la valide lui-même — y compris le cas où elle ne
    # somme pas à un, qui n'est pas une erreur bénigne.
    rep = data.get("repartition_charges")
    if isinstance(rep, dict):
        profil["repartition_charges"] = rep
    return profil


def _profil_icpe(data, rejets=None):
    """Les entrées propres au criblage ICPE, lues comme celles du moteur.

    LE MÊME LECTEUR DE NOMBRE que le reste du site, et pour la même raison :
    une valeur illisible doit RESSORTIR, pas disparaître dans un champ absent.
    Un criblage reparti sur un champ silencieusement écarté annoncerait
    « aucune rubrique atteinte » à quelqu'un qui vient de saisir une puissance.
    """
    profil = {}
    for champ in icpe_dc.CHAMPS:
        cid = champ["id"]
        if cid not in data or data[cid] in ("", None):
            continue
        brut = data[cid]
        if champ["type"] == "nombre":
            valeur, motif = _lire_nombre(brut, champ)
            if motif:
                if rejets is not None:
                    rejets.append({"champ": cid,
                                   "label": champ.get("label") or cid,
                                   "saisi": str(brut)[:40], "message": motif})
                continue
            profil[cid] = valeur
        elif champ["type"] == "booleen":
            # Une case décochée vaut FAUX ; une question non posée vaut
            # ABSENT. Les confondre ferait retenir le seuil le plus élevé pour
            # un local batteries au plomb dont personne n'a rien dit — et le
            # seuil le plus élevé est ici le plus permissif.
            profil[cid] = brut if isinstance(brut, bool) else (
                str(brut).strip().lower() in ("1", "true", "oui", "on"))
        else:
            profil[cid] = str(brut).strip()[:40]
    return profil


@app.route("/api/datacenter/icpe", methods=["POST"])
@login_required
def api_datacenter_icpe():
    """Le criblage ICPE du projet : quelles rubriques, quel régime, quel délai.

    CE QUE LA ROUTE REND ET QUI N'EST PAS LE RÉGIME. Les rubriques dont la
    grandeur n'est pas saisie ressortent à part, avec le nom de ce qui manque.
    Une donnée absente n'est pas un seuil non atteint, et un régime prononcé
    sur trois rubriques criblées et deux inconnues est un PLANCHER, pas un
    classement.
    """
    data = request.get_json(silent=True) or {}
    rejets = []
    # Les deux profils se rejoignent : le criblage a besoin du mode de
    # refroidissement et de la puissance informatique, qui vivent au moteur, et
    # de ses propres puissances et volumes. Les lire séparément puis les fondre
    # évite de dupliquer une définition de champ.
    profil = dict(_profil_datacenter(data, rejets))
    profil.update(_profil_icpe(data, rejets))
    try:
        r = icpe_dc.rubriques_du_projet(profil)
    except Exception:
        app.logger.exception("criblage ICPE datacenter")
        return jsonify(ok=False, error="calcul",
                       message="Le criblage n'a pas pu être établi."), 500
    c = r["criblage"]
    return jsonify(ok=True, rubriques=r["rubriques"], criblage=c,
                   mission=icpe_dc.consequences_mission(c["regime_site"]),
                   champs=icpe_dc.CHAMPS,
                   rejets=rejets, lecture=_lecture_rejets(rejets))


@app.route("/api/datacenter/tier", methods=["POST"])
@login_required
def api_datacenter_tier():
    """La qualification Tier : ce que la topologie décrite permettrait de
    revendiquer, et ce qui l'en empêche.

    AUCUN NIVEAU N'EST DÉCERNÉ ICI, et la réponse le répète. La certification
    est délivrée par l'Uptime Institute sur dossier, séparément pour les
    documents de conception et pour l'ouvrage construit. Cette route dit ce
    qu'une topologie permettrait de revendiquer, sur les seules données
    saisies — ce qui est déjà tout ce dont on a besoin en revue de conception,
    et rien de plus.

    CE QU'ELLE REND ET QUI N'EST PAS LE NIVEAU : le sous-système LIMITANT.
    « Votre site est de niveau I » n'aide personne ; « il est de niveau I parce
    que la distribution mécanique l'est » se traite en une réunion.
    """
    data = request.get_json(silent=True) or {}
    sous = data.get("sous_systemes")
    if not isinstance(sous, dict):
        return jsonify(ok=False, error="sous_systemes_manquants",
                       message="La note de chaque sous-système est nécessaire.",
                       sous_systemes=tier_dc.SOUS_SYSTEMES,
                       niveaux=tier_dc.ORDRE), 400
    # Le refroidissement vient du profil du moteur : c'est lui qui décide si
    # l'eau d'appoint est un sous-système à noter ou hors périmètre. Le
    # redemander à part le ferait diverger de la famille réellement retenue.
    profil = _profil_datacenter(data)
    profil.update(_profil_icpe(data))
    evaporatif = (profil.get("refroidissement") or "") in (
        "tour_evaporative", "adiabatique")
    try:
        q = tier_dc.qualifier(sous, evaporatif)
        vise = str(data.get("vise") or "").upper().strip()
        ecart = tier_dc.ecart_au_vise(sous, vise, evaporatif) if vise else None
        groupes = None
        if data.get("groupe_classe"):
            groupes = tier_dc.capacite_qualifiante_groupes(
                data.get("groupes_puissance_elec_kw"),
                data.get("groupe_classe"),
                data.get("groupe_certifiee_kw"))
        auto = tier_dc.autonomie(profil)
    except Exception:
        app.logger.exception("qualification Tier datacenter")
        return jsonify(ok=False, error="calcul",
                       message="La qualification n'a pas pu être établie."), 500
    return jsonify(ok=True, qualification=q, ecart=ecart, groupes=groupes,
                   autonomie=auto, referentiel=tier_dc.referentiel())


@app.route("/api/datacenter/reseau", methods=["POST"])
@login_required
def api_datacenter_reseau():
    """Le raccordement, le calcul non servi qu'il entraîne, et ce que la
    production sur site déclenche ailleurs.

    LES QUATRE RÉSULTATS PARTENT ENSEMBLE, et c'est le point de cette route.
    Pris séparément, chacun se lit à l'avantage de la décision déjà prise :
    le délai gagné sans le calcul perdu, le calcul perdu sans le délai gagné,
    la production sur site sans son régime administratif. La décision se prend
    sur les quatre, ou elle se prend mal.

    RIEN N'EST DEVINÉ. Une grandeur absente fait ressortir un résultat
    « incomplet » qui NOMME ce qui manque, et non un chiffre calculé sur des
    valeurs par défaut. Sur ce sujet, une valeur par défaut deviendrait la
    réponse : personne ne conteste un formulaire déjà rempli.
    """
    data = request.get_json(silent=True) or {}
    rejets = []
    profil = _profil_reseau(data, rejets)
    # Les grandeurs du criblage réglementaire voyagent avec : la production
    # sur site s'ajoute aux groupes de secours déjà déclarés, et c'est le
    # CUMUL qui décide du régime. Les demander à part les ferait diverger.
    profil.update(_profil_icpe(data, rejets))
    refroidissement = _profil_datacenter(data).get("refroidissement")
    if refroidissement:
        profil["refroidissement"] = refroidissement
    try:
        etude = reseau_dc.etudier(profil)
    except Exception:
        app.logger.exception("étude de raccordement datacenter")
        return jsonify(ok=False, error="calcul",
                       message="L'étude n'a pas pu être établie."), 500
    return jsonify(ok=True, etude=etude, rejets=rejets,
                   referentiel=reseau_dc.referentiel())


@app.route("/api/datacenter/travaux", methods=["POST"])
@login_required
def api_datacenter_travaux():
    """L'organisation de la phase travaux : opérations, acteurs, points d'arrêt.

    LE PLAN S'ADAPTE À DEUX CHOSES SEULEMENT — la nature des travaux et
    l'existence d'une mission de commissioning —, et il le dit. Une opération
    de commissioning non commandée ne disparaît pas du plan : elle y reste avec
    la mention de qui devra l'assumer, parce que la retirer serait exactement
    ce qui produit une réception sans essais intégrés.
    """
    data = request.get_json(silent=True) or {}
    nature = str(data.get("nature_travaux") or "").strip().lower()[:20] or None
    if nature and nature not in technique_dc.NATURES_TRAVAUX:
        return jsonify(ok=False, error="nature_inconnue",
                       message="Nature de travaux inconnue : %s." % nature,
                       natures=sorted(technique_dc.NATURES_TRAVAUX)), 400
    cx = data.get("commissioning")
    try:
        p = travaux_dc.plan(nature, avec_commissioning=(cx is not False))
    except Exception:
        app.logger.exception("plan travaux datacenter")
        return jsonify(ok=False, error="calcul",
                       message="Le plan n'a pas pu être établi."), 500
    return jsonify(ok=True, plan=p,
                   nature_detail=(technique_dc.NATURES_TRAVAUX.get(nature)
                                  if nature else None),
                   natures=technique_dc.NATURES_TRAVAUX,
                   natures_note=technique_dc.NATURES_NOTE)


@app.route("/api/datacenter/marche/analyser", methods=["POST"])
@admin_required
def api_datacenter_marche_analyser():
    """L'analyse du dossier de consultation déposé, pièce par pièce.

    VERROU D'ADMINISTRATION, comme le dépôt : les documents analysés sont des
    pièces de marché d'un client, et leur contenu ressort dans la réponse sous
    forme de citations. Ouvrir cette lecture à tout compte connecté reviendrait
    à servir un dossier de consultation à qui a une session.

    DEUX SOURCES POSSIBLES. Des documents déjà versés à la base, désignés par
    leur identifiant, ou des fichiers transmis pour analyse SANS DÉPÔT. La
    seconde est le cas courant : on lit un dossier de consultation avant de
    décider s'il vaut la peine d'être conservé, et les pièces d'une
    consultation à laquelle on ne répondra pas n'ont rien à faire dans la base
    de connaissance.

    UN FICHIER TRANSMIS PASSE PAR L'ANALYSE ANTIVIRUS avant d'être lu, comme
    au dépôt. Le fichier n'est pas conservé — mais il est ouvert par des
    extracteurs de texte, et un extracteur qui ouvre un fichier hostile est
    exactement ce contre quoi cette porte existe.
    """
    ckey = "marche:%s" % client_ip()
    if guard.blocked(ckey, limit=30, window=600):
        return jsonify(ok=False, error="rate_limited",
                       message="Trop d'analyses en peu de temps. "
                               "Patientez un instant."), 429
    guard.fail(ckey)
    import antivirus
    import rag_store as _rs
    data = request.get_json(silent=True) or {}
    docs, ignores = [], []
    for d in (data.get("documents") or [])[:40]:
        if not isinstance(d, dict):
            continue
        nom = str(d.get("nom") or d.get("filename") or "").strip()[:200]
        if not nom:
            continue
        ext = str(d.get("extension") or "").strip().lower()[:8]
        if not ext and "." in nom:
            ext = "." + nom.rsplit(".", 1)[-1].lower()
        texte = d.get("texte")
        if texte is None and d.get("contenu"):
            try:
                octets = base64.b64decode(d["contenu"], validate=True)
            except Exception:
                ignores.append({"fichier": nom,
                                "pourquoi": "Le contenu transmis n'est pas "
                                            "décodable."})
                continue
            verdict = antivirus.analyser(nom, octets)
            audit.journaliser(
                "marche.porte", cible=nom[:120],
                detail=("accepté" if verdict["accepte"]
                        else "REFUSÉ:" + verdict.get("code", "?")))
            if not verdict["accepte"]:
                ignores.append({"fichier": nom, "pourquoi": verdict["motif"]})
                continue
            try:
                texte = _rs.extract_text(ext.lstrip("."), octets)
            except Exception as exc:
                # LE MOTIF RÉEL, pas un message passe-partout : le cas le plus
                # fréquent est le PDF scanné, qui franchit l'analyse et ne
                # porte aucun texte. « Illisible » ferait recommencer à
                # l'identique ; le dire fait fournir une version océrisée.
                texte = None
                ignores.append({
                    "fichier": nom,
                    "pourquoi": ("Aucun texte n'a pu être extrait de ce "
                                 "fichier (%s). Un plan ou un document scanné "
                                 "franchit l'analyse sans porter de texte : "
                                 "fournissez une version avec couche texte."
                                 % getattr(exc, "code", type(exc).__name__))})
                continue
        elif texte is None and d.get("document_id"):
            try:
                texte = rag.document_text(str(d["document_id"])[:80],
                                          limit=400000)
            except Exception:
                texte = None
                ignores.append({"fichier": nom,
                                "pourquoi": "Le texte de ce document n'a pas "
                                            "pu être relu depuis la base."})
                continue
        docs.append({"nom": nom, "texte": str(texte or "")[:400000],
                     "extension": ext})
    if not docs:
        return jsonify(ok=False, error="aucun_document",
                       message="Aucun document analysable.",
                       ignores=ignores), 400
    try:
        a = ao_dc.analyser(docs)
    except Exception:
        app.logger.exception("analyse dossier marché")
        return jsonify(ok=False, error="analyse",
                       message="L'analyse n'a pas pu être conduite."), 500
    audit.journaliser("marche.analyse", cible="%d document(s)" % len(docs),
                      detail=", ".join(d["nom"][:40] for d in docs)[:400])
    if ignores:
        a["ignores"] = ignores
    return jsonify(ok=True, analyse=a)


# Le pont entre une pièce du dossier de candidature et le livrable qui la
# rédige. Écrit ici, en un seul endroit : la page l'affiche, elle ne le
# reconstitue pas. Toutes les pièces n'y sont pas — un formulaire ne se rédige
# pas, un justificatif s'obtient — et c'est précisément ce que la table dit.
_AO_REDACTION = {
    "equipe": "ao-note-equipe",
    "organigramme": "ao-organigramme",
    "repartition_competences": "ao-repartition-groupement",
    "references": "ao-references",
    "moyens": "ao-moyens-procedures",
    "qse": "ao-qse",
    "conventions": "ao-conventions-collectives",
}


@app.route("/api/datacenter/programme", methods=["POST"])
@login_required
def api_datacenter_programme():
    """La vue de programme : ce qui s'additionne, ce qui se pondère, ce qui ne
    se consolide pas.

    POURQUOI CETTE ROUTE NE VA CHERCHER AUCUNE DONNÉE. Elle consolide ce qu'on
    lui donne, et rien d'autre. Aller lire les projets enregistrés serait
    commode et faux : un programme n'est pas l'ensemble des projets d'un
    compte, c'est un périmètre que quelqu'un décide — et deux programmes
    peuvent partager un site.

    CE QU'ELLE REND ET QUI N'EST PAS UN TOTAL : le nombre de sites que chaque
    total couvre, et le nom de ceux qui manquent. Un CAPEX calculé sur quatre
    sites sur sept est un sous-total, et le présenter autrement est la façon la
    plus rapide de perdre la confiance d'un comité exécutif.
    """
    data = request.get_json(silent=True) or {}
    sites = data.get("sites")
    if not isinstance(sites, list):
        return jsonify(ok=False, error="sites_manquants",
                       message="La liste des sites du programme est "
                               "nécessaire.",
                       champs=programme_dc.CHAMPS_SITE), 400
    if len(sites) > 200:
        # Un programme de plus de deux cents sites existe ; il ne se pilote pas
        # depuis un formulaire. Le dire vaut mieux que de servir une page qui
        # met trente secondes à s'afficher.
        return jsonify(ok=False, error="trop_de_sites",
                       message="Au-delà de deux cents sites, cette vue n'est "
                               "plus lisible : découpez le programme en "
                               "sous-portefeuilles."), 400
    try:
        vue = programme_dc.consolider(sites)
    except Exception:
        app.logger.exception("consolidation de programme")
        return jsonify(ok=False, error="calcul",
                       message="La consolidation n'a pas pu être établie."), 500
    return jsonify(ok=True, programme=vue,
                   kpi=programme_dc.KPI,
                   champs=programme_dc.CHAMPS_SITE,
                   natures=programme_dc.NATURES_SITE,
                   parties_prenantes=programme_dc.PARTIES_PRENANTES,
                   international=programme_dc.INTERNATIONAL,
                   zero_defaut=programme_dc.ZERO_DEFAUT)


@app.route("/api/datacenter/marche/candidature", methods=["POST"])
@login_required
def api_datacenter_marche_candidature():
    """Le dossier de candidature à produire, dans l'ordre où l'on s'y prend.

    L'ORDRE N'EST PAS CELUI DU RÈGLEMENT DE CONSULTATION : ce qui a un délai
    d'obtention passe en premier, parce que c'est la seule chose qu'on ne
    rattrape pas la dernière nuit.
    """
    data = request.get_json(silent=True) or {}
    analyse = data.get("analyse") if isinstance(data.get("analyse"), dict) else None
    try:
        p = ao_dc.plan_reponse(analyse, groupement=bool(data.get("groupement")))
    except Exception:
        app.logger.exception("plan de candidature")
        return jsonify(ok=False, error="calcul",
                       message="Le plan n'a pas pu être établi."), 500
    # Le lien pièce → livrable se fait ICI plutôt que dans la page : une page
    # qui devinerait quel livrable rédige quelle pièce se tromperait le jour où
    # l'un des deux changerait de nom.
    p["redaction"] = [{"piece": cle, "type": tid,
                       "label": (livrables.get_type(tid) or {}).get("label")}
                      for cle, tid in _AO_REDACTION.items()
                      if livrables.get_type(tid)]
    return jsonify(ok=True, plan=p, pieces_marche=ao_dc.PIECES_MARCHE)


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
    d = ingenierie_dc.dossier(profil, code, data)
    if not d.get("connu"):
        return jsonify(ok=False, error="phase_inconnue",
                       message=d.get("motif", "Phase inconnue.")), 404
    fmt = (data.get("format") or "docx").strip().lower()
    if fmt not in ("docx", "pdf"):
        fmt = "docx"
    md = _etude_phase_markdown(d, str(data.get("client") or "").strip()[:120])
    meta = {"label": "Étude de phase %s, %s" % (d["code"], d["nom"]),
            "numero": "ETUDE-%s" % d["code"],
            "phase": "%s, %s" % (d["code"], d["nom"]),
            "indice": "01",
            "client": str(data.get("client") or "")[:120],
            "ia": False,
            "referentiel": "Cadre de phases CONSEILPREV v" + ingenierie_dc.VERSION,
            "perimetre": "%s kW informatiques · %s" % (
                round(profil["puissance_it_kw"]), d["filiere_nom"]),
            "date": time.strftime("%d/%m/%Y"),
            "sources": [{"title": "Moteur d'ingénierie CONSEILPREV v" + datacenter.VERSION,
                         "theme": "calcul déterministe"},
                        {"title": "Cadre de phases v" + ingenierie_dc.VERSION,
                         "theme": ingenierie_dc.FILIERES[d["filiere"]]["cadre"]}]}
    md, bord = _poser_bordereau(md, meta, "etude_phase", data)
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


@app.route("/api/datacenter/piece/export", methods=["POST"])
@login_required
def api_datacenter_piece_export():
    """Une pièce rédigée, en Word ou en PDF, à l'en-tête CONSEILPREV.

    L'étude de phase s'exportait ; la pièce, non. Elle s'affichait, et le seul
    moyen de l'emporter était de sélectionner le texte à l'écran — c'est-à-dire
    de perdre le titrage, les tableaux et l'en-tête. Un document qui ne sort pas
    du site n'est pas un livrable.

    Le corps porte le MARKDOWN affiché, et non le code de la pièce : le
    document rendu peut avoir été écrit par le modèle, puis retouché. Le
    reconstruire à partir du registre produirait un autre document que celui
    que le lecteur a sous les yeux, et c'est celui-là qu'il veut emporter.
    """
    data = request.get_json(silent=True) or {}
    md = (data.get("markdown") or "").strip()
    if not md:
        return jsonify(ok=False, error="vide",
                       message="Aucun document à mettre en page."), 400
    if len(md) > 400_000:
        return jsonify(ok=False, error="trop_long",
                       message="Document trop volumineux pour la mise en page."), 413
    fmt = (data.get("format") or "docx").strip().lower()
    if fmt not in ("docx", "pdf"):
        fmt = "docx"
    code_phase = str(data.get("phase") or "").strip().upper()[:12]
    code_piece = str(data.get("piece") or "").strip().upper()[:24]
    pc = ingenierie_dc.piece(code_phase, code_piece) or {}
    profil = _profil_datacenter(data)
    d = ingenierie_dc.dossier(profil, code_phase, data) if code_phase else {}
    # L'OBJET, pas le code : le numéro du document porte déjà « SPC-SAFETY »,
    # et le répéter deux lignes plus bas donne un cartouche qui bégaie.
    label = pc["titre"] if pc else (code_piece or "Pièce d'ingénierie")
    meta = {"type": pc.get("code") or code_piece, "label": label,
            "client": str(data.get("client") or "")[:120],
            # La pièce sort du moteur (« trame-… ») ou d'un modèle : le
            # marquage suit la MÊME décision que la ligne « Établi par ».
            "ia": _redige_par_modele(data.get("model")),
            "referentiel": "Moteur d'ingénierie CONSEILPREV v" + ingenierie_dc.VERSION,
            # LE CARTOUCHE. Numéro, phase et indice viennent de la rédaction :
            # sans eux, deux tirages du même document sortent identiques, et
            # c'est la date du fichier qui fait foi — elle change à chaque copie.
            "numero": str(data.get("numero")
                          or ("%s-%s" % (pc["code"], code_phase) if pc else ""))[:60],
            "phase": ("%s, %s" % (code_phase, d["nom"])) if d.get("nom")
                     else code_phase,
            "indice": str(data.get("indice") or "")[:8],
            "statut": str(data.get("statut") or "")[:80],
            "discipline": pc.get("discipline_nom") or "",
            "emetteur": pc.get("emetteur_nom") or "",
            "perimetre": "%s%s" % (
                ("%s kW informatiques" % round(profil["puissance_it_kw"]))
                if profil.get("puissance_it_kw") else "",
                (" · %s" % d["filiere_nom"]) if d.get("filiere_nom") else ""),
            "date": time.strftime("%d/%m/%Y"),
            # « Établi par » se lit chez le client : « trame-moteur_seul » est
            # un code interne, pas un auteur. On nomme ce qui a réellement
            # composé le document.
            "model": _auteur_document(data.get("model")),
            "sources": [s for s in (data.get("sources") or [])
                        if isinstance(s, dict)][:40]
            or [{"title": "Moteur d'ingénierie CONSEILPREV v" + datacenter.VERSION,
                 "theme": "calcul déterministe"},
                {"title": "Cadre de phases v" + ingenierie_dc.VERSION,
                 "theme": "registre des pièces"}]}
    md, bord = _poser_bordereau(md, meta, "piece", data)
    try:
        if fmt == "pdf":
            blob = livrables_export.build_pdf(md, meta)
            mimetype = "application/pdf"
        else:
            blob = livrables_export.build_docx(md, meta)
            mimetype = ("application/vnd.openxmlformats-officedocument"
                        ".wordprocessingml.document")
    except Exception:
        app.logger.exception("export pièce d'ingénierie")
        return jsonify(ok=False, error="export_echec",
                       message="La mise en page a échoué."), 500
    audit.journaliser("datacenter.piece.export",
                      cible="%s/%s" % (code_phase, code_piece), detail=fmt)
    return send_file(io.BytesIO(blob),
                     download_name="%s.%s" % (
                         _nom_fichier(pc.get("code") or code_piece or "piece"), fmt),
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

    eco = d.get("ecoconception")
    if eco:
        A("## %d. Écoconception de la phase (ISO 14006 · ISO/TR 14062)" % (n_ + 1))
        A("")
        A("**Le geste.** %s" % eco["geste"])
        A("")
        A("**La preuve à verser au dossier.** %s" % eco["preuve"])
        A("")
        A("*Fondement : %s. %s*"
          % (eco["clause"], ingenierie_dc.ECOCONCEPTION["direction"]))
        A("")
        n_ += 1

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
            "ia": False,
            "referentiel": "Moteur d'ingénierie CONSEILPREV v" + datacenter.VERSION,
            "perimetre": "%s kW informatiques · %s" % (
                round(profil["puissance_it_kw"]),
                datacenter.REFROIDISSEMENT.get(
                    profil.get("refroidissement") or "eau_glacee", {}).get("nom", "")),
            "date": time.strftime("%d/%m/%Y"),
            "sources": [{"title": "Moteur d'ingénierie CONSEILPREV v" + datacenter.VERSION,
                         "theme": "calcul déterministe"}]}
    md, bord = _poser_bordereau(md, meta, "note_calcul", data)
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
    import rag_store as _rs
    try:
        return _rs.embed_texts(list(textes))
    except _rs.RagError as exc:
        raise agent_datacenter.EmbeddingIndisponible(str(exc)) from exc


def _agent_dc_complete(system, user, temperature=0.2):
    """Complétion, branchée sur l'assistant existant.

    assistant.generate() choisit le fournisseur et gère le repli. La
    température demandée par l'agent n'y est pas exposée : on la documente au
    lieu de la taire, parce qu'un agent qui croit piloter un paramètre qu'il ne
    pilote pas produit des résultats qu'on n'explique plus.
    """
    modele = assistant.defaut()
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
    import rag_store as _rs
    data = request.get_json(silent=True) or {}
    themes = data.get("themes")
    if not isinstance(themes, list) or not themes:
        # Par défaut, toute la famille « Centres de données » de la base.
        themes = [t for t in _rs.THEMES if t.startswith("Data center")]
    agent = _agent_dc()
    total, docs, erreurs = 0, 0, []
    for theme in themes[:40]:
        try:
            hits = rag.search("data center énergie eau carbone",
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
    import rag_store as _rs
    agent = _agent_dc()
    par_theme = {}
    for p in agent.index.passages:
        par_theme[p.theme] = par_theme.get(p.theme, 0) + 1
    dispo = assistant.available()
    return jsonify(ok=True,
                   passages=len(agent.index.passages),
                   par_theme=par_theme,
                   corpus_version=agent_datacenter.CORPUS_VERSION,
                   vectorisation=_rs.embeddings_available(),
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
def audit_conformite():
    """Étude & audit de conformité IEC 62443 (mode démo public ; temps réel via compte)."""
    return _page(PAGES["/audit-conformite"])


@app.route("/tendances")
def tendances():
    return _page(PAGES["/tendances"])


@app.route("/connecter")
def connecter():
    """Page « Connecter votre plateforme » : l'entrée pour brancher une source réelle."""
    return _page(PAGES["/connecter"])


@app.route("/guide-integration")
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
def ressources():
    return _page(PAGES["/ressources"])


@app.route("/faq")
def faq():
    return _page(PAGES["/faq"])


@app.route("/about")
def about():
    return _page(PAGES["/about"])


@app.route("/vos-projets")
def vos_projets():
    """Formulaire détaillé de soumission de projet cyber industriel (IT/OT/IIoT)."""
    return _page(PAGES["/vos-projets"])


@app.route("/contact")
def contact():
    return _page(PAGES["/contact"])


@app.route("/cgv")
def cgv():
    """Conditions générales de vente.

    OUVERTE, ET C'EST UNE CONDITION DE VALIDITÉ. Des conditions de vente
    inaccessibles avant l'achat ne sont pas opposables à l'acheteur : les
    enfermer derrière le compte qu'elles servent à vendre les priverait de
    tout effet.
    """
    return _page(PAGES["/cgv"])


@app.route("/mentions-legales")
def mentions_legales():
    return _page(PAGES["/mentions-legales"])


@app.route("/politique-confidentialite")
def politique_confidentialite():
    return _page(PAGES["/politique-confidentialite"])


@app.route("/acces")
def page_acces():
    """Comment obtenir un accès : le périmètre, le prix, les deux voies.

    OUVERTE, ET C'EST LE POINT. Une page qui vend l'accès derrière l'accès ne
    vend rien. Elle ne divulgue que ce qu'un visiteur voit déjà — les entrées
    du tiroir — et le prix, qui n'est un secret pour personne.
    """
    return _page(PAGES["/acces"])


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


@app.route("/fond-hero.js")
def fond_hero_js():
    """Bascule affiche → vidéo du fond de bandeau (voir le fichier)."""
    return _serve_fast("fond-hero.js", _CC_ASSET,
                       mimetype="text/javascript; charset=utf-8")


@app.route("/parcours.js")
def parcours_js():
    """Parcours guidés par rôle — données et interface, partagés par toutes les pages."""
    return _serve_fast("parcours.js", _CC_ASSET,
                       mimetype="text/javascript; charset=utf-8")


@app.route("/piliers-dc.js")
def piliers_dc_js():
    """Le bandeau des trois piliers centres de donnees, partage par les trois
    pages qu'il relie.

    Elles se citaient de loin en loin — et pas toutes : l'ingenierie ne
    renvoyait pas une seule fois vers la strategie. Rien ne disait dans quel
    ORDRE les prendre, ni ce que chacune attend de la precedente. Ecrit une
    fois : trois copies auraient diverge, et c'est justement l'enchainement
    qu'elles doivent dire d'une seule voix.
    """
    return _serve_fast("piliers-dc.js", _CC_ASSET,
                       mimetype="text/javascript; charset=utf-8")


@app.route("/guide-etapes.js")
def guide_etapes_js():
    """Parcours guide des etapes numerotees, partage par toutes les pages qui
    font remplir quelque chose.

    UN SEUL FICHIER, ET C'EST LE POINT. Une page portait deja un parcours ;
    quatre autres en avaient besoin. Recopie cinq fois, il aurait diverge des
    la premiere retouche — c'est exactement ce qui venait d'arriver au bloc
    `.mod-bloc`, dont les trois copies ont fait d'une ligne fautive un defaut
    de trois pages. Les etapes, elles, ne sont pas dans ce fichier : il les lit
    sur la page qui le charge.
    """
    return _serve_fast("guide-etapes.js", _CC_ASSET,
                       mimetype="text/javascript; charset=utf-8")


@app.route("/modules.js")
def modules_js():
    """Encadrement et signalement des modules numerotes, partages par les trois
    pages d'ingenierie de centres de donnees. Un seul module : recopie trois
    fois, la regle du battement aurait diverge — et c'est celle qu'on ne
    remarque pas qui reste en clignotant."""
    return _serve_fast("modules.js", _CC_ASSET,
                       mimetype="text/javascript; charset=utf-8")


@app.route("/transmettre.js")
def transmettre_js():
    """Le choix du destinataire d'un document, partagé par les trois pages
    d'ingénierie de centres de données. Un seul module : recopié trois fois, le
    vocabulaire aurait divergé au premier ajout."""
    return _serve_fast("transmettre.js", _CC_ASSET,
                       mimetype="text/javascript; charset=utf-8")


@app.route("/equipements-it.js")
def equipements_it_js():
    """Affichage de la nomenclature informatique.

    Route publique : le script ne porte aucune donnée, seulement l'affichage.
    Ce sont les API qu'il appelle qui exigent une session."""
    return _serve_fast("equipements-it.js", _CC_ASSET,
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


@app.route("/markdown.js")
def markdown_js():
    """Rendu Markdown partagé par la console des livrables et la lecture d'une
    pièce d'ingénierie. Écrit une fois : deux moteurs de rendu recopiés
    finiraient par afficher le même document de deux façons."""
    return _serve_fast("markdown.js", _CC_ASSET,
                       mimetype="text/javascript; charset=utf-8")


@app.route("/ingenierie-dc.js")
def ingenierie_dc_js():
    """Interface du cadre de phases. Même règle que ci-dessus : route publique,
    aucune donnée dans le fichier — ce sont les API qu'il appelle qui exigent
    une session."""
    return _serve_fast("ingenierie-dc.js", _CC_ASSET,
                       mimetype="text/javascript; charset=utf-8")


@app.route("/decarbonation-dc.js")
def decarbonation_dc_js():
    """Interface de la plateforme de decarbonation. Aucune donnee dans le
    fichier : il derive tout du referentiel servi par les API."""
    return _serve_fast("decarbonation-dc.js", _CC_ASSET,
                       mimetype="text/javascript; charset=utf-8")


@app.route("/strategie-dd.js")
def strategie_dd_js():
    """Interface du questionnaire des quatre perspectives. Aucune donnee dans
    le fichier : il derive tout du questionnaire servi par l'API, y compris la
    liste des perspectives qui se notent."""
    return _serve_fast("strategie-dd.js", _CC_ASSET,
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


# ══════════════════════════════════════════════════════════════════════════
# LES MÉDIAS DU FOND — ET POURQUOI ILS NE PASSENT PAS PAR `_serve_fast`
# ══════════════════════════════════════════════════════════════════════════
# `_serve_fast` lit le fichier ENTIER en mémoire, le garde par processus, et
# répond toujours 200. C'est exactement ce qu'il faut pour un script de
# quelques dizaines de kilo-octets. Pour une vidéo de fond, c'est faux deux
# fois :
#
#   1. QUELQUES MÉGA-OCTETS RÉSIDENTS PAR PROCESSUS. Le service tourne avec
#      plusieurs workers ; le fichier serait gardé autant de fois.
#
#   2. ET SURTOUT, PAS DE REQUÊTE PARTIELLE. Un navigateur qui lit une vidéo
#      demande des TRANCHES (`Range: bytes=…`). Safari, sur iOS comme sur
#      macOS, commence par demander les premiers octets : si le serveur
#      répond 200 avec tout le fichier au lieu de 206 avec la tranche, il
#      considère que la source ne sait pas se positionner et REFUSE DE LIRE.
#      La vidéo ne démarre jamais, sans message d'erreur — juste un fond noir.
#
# `send_from_directory(conditional=True)` délègue à Werkzeug, qui sait
# répondre 206 et poser `Accept-Ranges` et `Content-Range`. Le crochet de
# compression, lui, ne touche que `text/*`, `json` et `xml` : une vidéo n'y
# passe pas — et une vidéo gzippée serait de toute façon plus lourde.
_MEDIA = os.path.join(HERE, "media")

#: Ce qui peut sortir de `media/`. Une liste blanche plutôt qu'une liste noire :
#: le jour où quelqu'un dépose une sauvegarde ou un fichier de configuration
#: dans ce dossier, il ne devient pas téléchargeable par accident.
_MEDIA_TYPES = {
    ".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".avif": "image/avif",
    ".mp4": "video/mp4", ".webm": "video/webm",
}


@app.route("/media/<nom>")
def media(nom):
    """Sert une image ou une vidéo de fond, en autorisant les tranches."""
    nom = str(nom or "")
    # `<nom>` sans convertisseur ne peut pas contenir de « / » : Werkzeug ne
    # ferait pas correspondre la route. Le contrôle reste, parce qu'une route
    # qu'on élargirait un jour en `<path:nom>` rendrait le trou béant sans que
    # rien ne le rappelle.
    if ".." in nom or "/" in nom or "\\" in nom:
        abort(404)
    ext = os.path.splitext(nom)[1].lower()
    if ext not in _MEDIA_TYPES:
        abort(404)
    if not os.path.isfile(os.path.join(_MEDIA, nom)):
        abort(404)
    resp = send_from_directory(_MEDIA, nom, mimetype=_MEDIA_TYPES[ext],
                               conditional=True)
    # L'affiche et la vidéo ne changent qu'à une mise en ligne. Un cache long
    # évite de retélécharger plusieurs méga-octets à chaque visite.
    resp.headers["Cache-Control"] = _CC_IMAGE
    resp.headers.setdefault("Accept-Ranges", "bytes")
    return resp


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


# Le périmètre d'exploration, écrit UNE fois : le groupe « * » et chaque robot
# d'IA reçoivent LES MÊMES règles. Dans le protocole robots, un groupe nommé
# REMPLACE le groupe générique — un « User-agent: GPTBot » qui ne répéterait
# pas les Disallow ouvrirait /admin/ à ce seul robot.
_ROBOTS_REGLES = [
    "Allow: /",
    "Disallow: /admin/",
    "Disallow: /api/",
    "Disallow: /connexion",
    "Disallow: /inscription",
    "Disallow: /mot-de-passe-oublie",
    "Disallow: /reinitialiser",
    "Disallow: /verifier-email",
    "Disallow: /telecharger/",
]
# Les robots des moteurs génératifs, EXPLICITEMENT admis sur le périmètre
# public (GEO) : être cité par ChatGPT, Gemini, Perplexity ou Claude commence
# par les laisser lire. Les nommer un à un rend la politique lisible et
# testable — et survit à un futur resserrement du groupe « * ».
_ROBOTS_IA = [
    "GPTBot", "OAI-SearchBot", "ChatGPT-User",          # OpenAI / ChatGPT
    "ClaudeBot", "Claude-User", "Claude-SearchBot",     # Anthropic / Claude
    "anthropic-ai",
    "PerplexityBot", "Perplexity-User",                 # Perplexity
    "Google-Extended",                                  # Gemini (au-delà de Googlebot)
    "CCBot",                                            # Common Crawl, corpus commun
]


@app.route("/robots.txt")
def robots_txt():
    """Directives d'exploration : pages publiques ouvertes — aux moteurs
    classiques ET aux moteurs génératifs — zones privées fermées à tous."""
    base = _base_url()

    def groupe(ua):
        return "\n".join(["User-agent: %s" % ua] + _ROBOTS_REGLES)

    body = "\n".join(
        [groupe("*"), "",
         "# Moteurs generatifs (GEO) : memes regles que le web classique —",
         "# tout le public est citable, rien du prive n'est offert.", ""]
        + [groupe(b) + "\n" for b in _ROBOTS_IA]
        + ["Sitemap: %s/sitemap.xml" % base,
           "# Flux de veille (Atom) : %s/veille.xml" % base,
           "# Resume du site pour les assistants : %s/llms.txt" % base,
           ""])
    return Response(body, mimetype="text/plain")


@app.route("/llms.txt")
def llms_txt():
    """Le résumé du site pour les assistants (convention llmstxt.org) : qui
    nous sommes, ce que chaque page publique contient, ce que les studios
    réservés calculent — pour qu'un moteur qui ne peut pas les lire puisse
    quand même les DÉCRIRE exactement. Aucune adresse privée n'y figure."""
    b = _base_url()
    corps = """# ConseilPrev Cyber

> Cabinet de conseil français : cybersécurité industrielle (OT/IACS, IEC 62443),
> gouvernance et conformité (NIS2, ISO 27001, AI Act, RGPD) et ingénierie de
> centres de données — énergie, eau, carbone, coûts de maîtrise d'œuvre.
> Contenus en français. Dirigé par Christophe Alain Cerf.

Les études et calculateurs sont réservés aux comptes clients ; les pages
ci-dessous sont publiques et citables.

## Pages publiques

- [Accueil]({b}/) : présentation du cabinet et des deux plateformes
- [Services]({b}/services) : conseil OT/IACS, GRC cyber, gouvernance de l'IA
- [Secteurs]({b}/secteurs) : industrie, énergie, nucléaire, aéronautique
- [Études de cas]({b}/etudes-de-cas) : missions types et livrables
- [FAQ]({b}/faq) : OT/IACS, IEC 62443, NIS2, studios data centre — questions-réponses citables
- [Veille]({b}/veille) : actualités réglementaires, nouveaux standards et normes
- [Ressources]({b}/ressources) : guides et documents publics
- [Conformité]({b}/conformite) : RGPD et transparence AI Act (art. 50)
- [Vos projets]({b}/vos-projets) · [À propos]({b}/about) · [Contact]({b}/contact)

## Studios réservés aux clients — ce qu'ils calculent

- Étude data centre : énergie (PUE par famille de refroidissement, pénalité de
  charge partielle), eau (WUE de site ET de source, bilan de masse de tour),
  carbone (CUE, incorporé amorti) — ISO/IEC 30134, EN 50600, GHG Protocol
  Scope 2, moyennes d'intensité millésimées.
- Évaluateurs de chiffres annoncés : un PUE de plaquette, un facteur
  d'émission, un volume d'eau ou un carbone incorporé fournisseur est situé
  dans les plages du référentiel, avec les pièces à exiger (ISO 14025,
  EN 15804+A2, IEC 62430).
- Stratégie de développement durable, ingénierie et phases (MOP/RIBA),
  prix de maîtrise d'œuvre, relecture de contrats, continuité OT.

## Site frère

- [ConseilPrev — Sentinel](https://conseilprev.onrender.com) : gouvernance de
  l'IA, conformité AI Act, et études data centre côté investisseur (enveloppe
  d'investissement, panorama, empreinte du parc).
""".replace("{b}", b)
    r = Response(corps, mimetype="text/plain; charset=utf-8")
    r.headers["Cache-Control"] = "public, max-age=3600"
    return r


@app.route("/veille.xml")
def veille_atom():
    """Le flux sortant de la veille — Atom.

    TRENTE-SIX FLUX ENTRENT, AUCUN NE SORTAIT. Ce qui est publiable ici n'est
    pas le contenu : les titres et les chapeaux appartiennent aux éditeurs, et
    l'on n'en reprend que ce qu'ils mettent eux-mêmes dans leurs flux pour être
    repris. Ce qui est À NOUS, c'est LE CLASSEMENT — domaine, pays de
    l'émetteur, secteur, standard cité, caractère réglementaire. C'est un
    travail original, et c'est lui qui a de la valeur pour un tiers : un abonné
    peut filtrer « réglementaire + centres de données + France » sans nous
    appeler.

    LES FACETTES SONT DES `<category>`, mécanisme prévu par le format pour
    exactement cela — chacune avec son `scheme`, faute de quoi « FR » (un pays)
    et « DORA » (un standard) se liraient dans le même sac.

    CE QUE CE FLUX N'EST PAS : ni STIX, ni TAXII, ni MISP. Ces formats
    transportent des indicateurs de compromission — empreintes, adresses,
    domaines malveillants. Nous collectons de l'actualité réglementaire ; y
    faire passer une révision de norme produirait quelque chose qu'aucun
    consommateur ne saurait exploiter.
    """
    import veille_facettes as _vf
    base = _base_url()
    try:
        items = _vf.enrichir(automation.veille_list(limit=60))
    except Exception:
        app.logger.exception("flux de veille")
        items = []

    def esc(t):
        return (str(t or "").replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))

    def iso(ms):
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime((ms or 0) / 1000.0))

    maj = iso(max([i.get("published") or 0 for i in items] or [0]))
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<feed xmlns="http://www.w3.org/2005/Atom">',
             "  <title>Veille CONSEILPREV Cyber — actualités réglementaires, "
             "nouveaux standards et normes</title>",
             "  <subtitle>Cybersécurité industrielle, gouvernance de l'IA, GRC "
             "et centres de données. Les textes viennent des éditeurs ; le "
             "classement est le nôtre.</subtitle>",
             '  <link rel="alternate" href="%s/veille"/>' % esc(base),
             '  <link rel="self" href="%s/veille.xml"/>' % esc(base),
             "  <id>%s/veille.xml</id>" % esc(base),
             "  <updated>%s</updated>" % maj]
    for it in items:
        f = it.get("facettes") or {}
        parts.append("  <entry>")
        parts.append("    <title>%s</title>" % esc(it.get("title")))
        # UNE ENTRÉE SANS ADRESSE RECEVABLE EST PUBLIÉE SANS LIEN, jamais
        # omise : `enrichir` a déjà écarté les schémas qui s'exécutent, et
        # faire disparaître l'actualité par-dessus le marché priverait
        # l'abonné de l'information ET de la raison de son absence.
        if it.get("link"):
            parts.append('    <link rel="alternate" href="%s"/>' % esc(it["link"]))
        parts.append("    <id>%s</id>" % esc(it.get("guid") or it.get("link")
                                             or it.get("title")))
        parts.append("    <updated>%s</updated>" % iso(it.get("published")))
        parts.append("    <author><name>%s</name></author>"
                     % esc(it.get("emetteur") or "source"))
        for schema, valeurs in (("domaine", [it.get("domaine")]),
                                ("pays", [f.get("pays")]),
                                ("theme", f.get("themes") or []),
                                ("standard", f.get("standards") or []),
                                ("secteur", f.get("secteurs") or []),
                                ("entreprise", f.get("entreprises") or [])):
            for v in valeurs:
                if v:
                    parts.append('    <category scheme="%s" term="%s"/>'
                                 % (schema, esc(v)))
        if f.get("reglementaire"):
            parts.append('    <category scheme="nature" term="reglementaire"/>')
        parts.append("    <summary>%s</summary>" % esc(it.get("resume")))
        parts.append("  </entry>")
    parts.append("</feed>")
    return Response("\n".join(parts), mimetype="application/atom+xml")


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
        # Sans JavaScript, cette bannière est le SEUL retour possible : elle
        # affichait le code technique nu (« type_non_supporte »), qui ne dit pas
        # quoi faire. On sert le motif lisible, le code restant en second pour le
        # diagnostic.
        banner = ("<div class=\"warn\" style=\"border-color:rgba(248,113,113,.55);"
                  "background:rgba(248,113,113,.12)\"><span>⛔</span><div>Échec du "
                  "chargement : <b>%s</b><br><span class=\"sub\">code %s%s</span>"
                  "</div></div>"
                  % (html_lib.escape(_motif_depot(code, detail)),
                     html_lib.escape(code),
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
    # Ce que le dépôt accepte RÉELLEMENT (indexation ∩ analyse préalable) : le
    # sélecteur de fichier de la console s'en sert. Sans cela il proposait des
    # formats voués au refus, et en écartait un que le serveur accepte — un
    # refus survenu avant l'appel, donc sans explication possible.
    import rag_store as _rs
    depos = _rs.formats_deposables()
    # LA LISTE EST BORNÉE, ET LA CONSOLE DOIT LE SAVOIR. Elle l'était déjà —
    # cinq cents documents, en dur dans la requête — mais rien ne le disait :
    # sur une base plus grande, la console affichait un compteur calculé sur ce
    # qu'elle avait reçu à côté d'un tableau de bord qui comptait en base, et
    # les deux nombres divergeaient sans explication. On rend donc le TOTAL
    # avec la liste, et l'appelant compare.
    try:
        limite = int(request.args.get("limit") or _rs.LISTE_MAX)
    except (TypeError, ValueError):
        limite = _rs.LISTE_MAX
    try:
        depart = int(request.args.get("offset") or 0)
    except (TypeError, ValueError):
        depart = 0
    try:
        st = rag.stats()
        docs = rag.list_documents(limit=limite, offset=depart)
        return jsonify(ok=True, documents=docs, stats=st,
                       total=st.get("documents"), listes=len(docs),
                       offset=max(0, depart), limite=limite,
                       tronque=bool(st.get("documents") is not None
                                    and len(docs) + max(0, depart)
                                    < st["documents"]),
                       capabilities=rag.capabilities(), themes=THEMES,
                       familles=_familles_payload(), formats=formats_available(),
                       formats_deposables=depos, natures=_natures_payload())
    except Exception:
        try:
            caps = rag.capabilities()
        except Exception:
            caps = {"persistent": False, "mode": "lexical", "reason": "db_connection_failed"}
        return jsonify(ok=True, documents=[],
                       stats={"documents": 0, "chunks": 0, "themes": {}, "storage": None},
                       total=0, listes=0, offset=0, limite=0, tronque=False,
                       capabilities=caps, themes=THEMES,
                       familles=_familles_payload(), formats=formats_available(),
                       formats_deposables=depos)


def _natures_payload():
    """Le vocabulaire des natures de source, ou une liste vide.

    SERVI AVEC LA LISTE DES DOCUMENTS, comme les thèmes : une console qui
    écrirait ses propres libellés divergerait du module au premier ajout, et
    proposerait une qualification que la base refuserait.
    """
    try:
        import qualite_source
        return qualite_source.natures()
    except Exception:                                    # pragma: no cover
        return []


@app.route("/api/admin/rag/nature", methods=["POST"])
@admin_required
def api_rag_nature():
    """Corrige la qualification d'un ou plusieurs documents — nature et date.

    POURQUOI CETTE ROUTE EXISTE. La nature est DEVINÉE au dépôt, sur le titre
    et les premières pages. Elle se trompe : un livre blanc qui s'annonce
    « guide complet », une note de projet dont le titre ne dit rien. Sans
    correction possible, l'erreur se figerait dans le classement de tous les
    livrables à venir, et personne ne saurait pourquoi tel document ne remonte
    jamais.

    AUCUNE RÉINDEXATION : ni le texte, ni les fragments, ni les vecteurs ne
    changent. Seul l'ordre de sortie change — c'est immédiat et sans risque,
    exactement comme le reclassement par thème.
    """
    import qualite_source as _qs
    data = request.get_json(silent=True) or {}
    nature = (data.get("nature") or "").strip().lower()
    date_source = data.get("date_source")
    ids = data.get("ids")
    if nature not in _qs.NATURES:
        return jsonify(ok=False, error="nature_inconnue",
                       message="Nature inconnue — choisissez-en une dans la "
                               "liste.",
                       natures=_qs.natures()), 400
    if not isinstance(ids, list) or not ids:
        return jsonify(ok=False, error="aucun_document",
                       message="Aucun document à qualifier."), 400
    qualifies = echecs = 0
    for doc_id in ids[:2000]:
        if not _rag_valid_doc_id(str(doc_id)):
            echecs += 1
            continue
        try:
            rag.set_nature(str(doc_id), nature, date_source)
            qualifies += 1
        except RagError:
            echecs += 1
        except Exception:
            app.logger.exception("qualification : échec pour %r", doc_id)
            echecs += 1
    audit.journaliser("rag.nature", cible=nature,
                      detail="%d document(s) qualifié(s), %d échec(s)"
                             % (qualifies, echecs))
    return jsonify(ok=True, nature=nature, qualifies=qualifies, echecs=echecs)


@app.route("/api/admin/rag/retirer", methods=["POST"])
@admin_required
def api_rag_retirer():
    """Retire de la base documentaire une famille qu'elle ne collecte plus.

    DEUX FAMILLES, DEUX RAISONS DIFFÉRENTES, et il vaut mieux les distinguer :

      · `csv` — un tableau découpé en fragments de neuf cents caractères perd
        sa ligne d'en-tête dès le deuxième morceau. Ce qui reste dans l'index
        est une suite de valeurs dont on ne sait plus de quelles colonnes elles
        viennent : le fragment pèse sur chaque recherche et ne peut répondre à
        rien. Les feuilles de calcul restent lues ENTIÈRES par l'analyse des
        pièces de marché et par les contrats — c'est la base documentaire qui
        les écarte, pas la plateforme ;
      · `veille` — les bulletins CERT-FR ont leur propre magasin et leur
        propre page. La base n'en recevait qu'une copie, qui a fini par
        occuper la majorité du fonds. La page de veille n'est pas touchée.

    SIMULATION PAR DÉFAUT. Sans `confirmer`, la route COMPTE ce qui partirait
    et ne supprime rien : la décision se prend sur un nombre, pas sur une
    intention. Avec `confirmer`, la suppression est IRRÉVERSIBLE — le texte,
    les fragments et le fichier d'origine partent ensemble.
    """
    import rag_store as _rs
    data = request.get_json(silent=True) or {}
    famille = (data.get("famille") or "").strip().lower()
    confirmer = bool(data.get("confirmer"))
    familles = sorted(_rs.EXT_RETIREES) + ["veille"]
    if famille not in familles:
        return jsonify(ok=False, error="famille_inconnue",
                       message="Famille inconnue — choisissez-en une dans la "
                               "liste.", familles=familles), 400
    try:
        if famille == "veille":
            res = rag.supprimer_veille(simuler=not confirmer)
        else:
            res = rag.supprimer_extension(famille, simuler=not confirmer)
    except RagError as exc:
        return jsonify(ok=False, error=exc.args[0],
                       message="Suppression impossible."), 400
    except Exception:
        app.logger.exception("retrait de famille %r", famille)
        return jsonify(ok=False, error="suppression",
                       message="La suppression n'a pas pu être menée."), 500
    if confirmer:
        # JOURNALISÉ PARCE QU'IRRÉVERSIBLE. Un retrait de plusieurs centaines
        # de documents doit laisser une trace datée et nominative : sans elle,
        # personne ne peut dire six mois plus tard pourquoi le fonds a maigri.
        audit.journaliser("rag.retirer", cible=famille,
                          detail="%d document(s), %d fragment(s) supprimés"
                                 % (res.get("documents", 0),
                                    res.get("fragments", 0)))
    return jsonify(ok=True, **res)


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


@app.route("/api/rag/search", methods=["POST"])
def api_rag_search_federe():
    """La base de CONSEILPREV Cyber, ouverte à l'application sœur.

    DEUX LIMITES, ET ELLES NE FONT PAS LA MÊME CHOSE.

    La CLÉ dit qui peut demander. Un corpus « public » au sens de « montré sur
    le site » n'est pas pour autant offert en vrac par une API commode ; la
    recherche est donc réservée au pair attendu. Sans clé configurée, la route
    REFUSE au lieu de servir : une protection qui s'annule quand on oublie de
    la régler n'en est pas une.

    `public_only=True` dit ce qui est servi, et rien de ce que l'appelant
    présente ne le lève. La raison est écrite ailleurs dans ce fichier et vaut
    encore ici : un livrable reproduit les extraits MOT POUR MOT, et un
    document marqué interne recopié dans une pièce qui sort du site serait une
    fuite, pas une commodité. La clé ouvre la porte ; elle n'ouvre pas les
    tiroirs.
    """
    # PLUSIEURS CLÉS ACCEPTÉES, ET C'EST UNE SÉPARATION, PAS UN CONFORT.
    # `RAG_PAIR_CLE` faisait double emploi : la clé avec laquelle ce serveur
    # SERT, et celle avec laquelle il APPELLE son pair. Tant qu'il n'y avait
    # que deux applications, la confusion était sans conséquence — les deux
    # valeurs devaient de toute façon coïncider. À trois, elle impose une clé
    # unique partagée par toute la maison : compromettre une application les
    # ouvre toutes, et faire tourner une clé oblige à redéployer les trois le
    # même jour.
    #
    # `RAG_CLES_SERVIES` porte donc les clés que CE serveur accepte — une par
    # appelant si on le souhaite. À défaut, on retombe sur `RAG_PAIR_CLE` :
    # une installation existante continue de fonctionner sans rien changer.
    brut = (os.environ.get("RAG_CLES_SERVIES", "").strip()
            or os.environ.get("RAG_PAIR_CLE", "").strip())
    # Séparées par virgule, point-virgule ou espace — sans expression
    # régulière : `re` n'est pas importé ici, et l'y ajouter pour découper une
    # liste de trois valeurs coûterait plus qu'il ne rapporte.
    attendues = [x for x in brut.replace(";", " ").replace(",", " ").split() if x]
    if not attendues:
        return jsonify(ok=False, error="federation_non_configuree",
                       message="La recherche fédérée n'est pas configurée sur "
                               "ce serveur (RAG_PAIR_CLE absente)."), 403
    fournie = (request.headers.get("X-Rag-Cle") or "").strip()
    # `hmac.compare_digest` LÈVE sur des chaînes non ASCII — un accent ou un
    # emoji dans la clé configurée, et la route rend 500 au lieu de refuser.
    # L'exploitant lirait « erreur du serveur » là où le diagnostic est
    # « votre clé contient un caractère interdit ». On le dit.
    #
    # ET ON LES COMPARE TOUTES, SANS SORTIR À LA PREMIÈRE QUI CORRESPOND : une
    # sortie anticipée ferait varier le temps de réponse avec le RANG de la clé
    # valide, ce qui est précisément le genre de fuite que la comparaison en
    # temps constant existe pour fermer.
    egales = False
    try:
        for attendue in attendues:
            egales = hmac.compare_digest(fournie, attendue) or egales
    except TypeError:
        app.logger.error("Une clé de fédération contient un caractère non "
                         "ASCII : la comparaison est impossible, la "
                         "fédération refusera tout appel.")
        return jsonify(ok=False, error="cle_non_ascii",
                       message="La clé de fédération configurée contient un "
                               "caractère non ASCII. Employez une valeur "
                               "hexadécimale ou base64."), 403
    if not egales:
        return jsonify(ok=False, error="cle_invalide",
                       message="Clé de fédération invalide."), 403

    ckey = "ragfed:%s" % client_ip()
    if guard.blocked(ckey, limit=120, window=600):
        return jsonify(ok=False, error="rate_limited",
                       message="Trop de recherches fédérées."), 429
    guard.fail(ckey)

    data = request.get_json(silent=True) or {}
    q = (data.get("query") or "").strip()
    if not q:
        return jsonify(ok=False, error="query_vide",
                       message="query requis."), 400
    try:
        k = max(1, min(int(data.get("top_k") or 8), 10))
    except (TypeError, ValueError):
        k = 8
    try:
        hits = rag.search(q[:500], k=k, public_only=True)
    except Exception:
        app.logger.exception("recherche fédérée")
        return jsonify(ok=False, error="recherche_echec",
                       message="Recherche indisponible."), 500
    # On ne rend QUE ce dont le pair a besoin pour rédiger. `visibility` n'a pas
    # à voyager : tout ce qui sort d'ici est public par construction, et le
    # champ laisserait croire qu'il pourrait en être autrement.
    return jsonify(ok=True, resultats=[
        {"texte": h.get("content") or "", "document": h.get("title") or "",
         "document_id": h.get("doc_id"), "theme": h.get("theme") or "",
         "score": h.get("score")}
        for h in hits])


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


@app.route("/api/admin/rag/visibility-lot", methods=["POST"])
@admin_required
def api_rag_visibility_lot():
    """Bascule la visibilité de TOUS les documents d'un ou plusieurs thèmes.

    À quoi cela sert : la recherche d'un compte ordinaire est bornée aux
    documents PUBLICS. Une base majoritairement interne fait donc tomber les
    livrables des clients en « moteur seul » — exacts, mais sans une seule
    citation. Ouvrir thème par thème, document par document, n'est pas tenable
    à quatre cent cinquante-neuf.

    TROIS PRÉCAUTIONS, et la première est celle qui compte :

      · ESSAI D'ABORD. `essai: true` compte sans rien changer, pour que
        l'interface annonce « 187 documents vont devenir publics » AVANT le
        geste. Un basculement en lot dont on découvre la portée après coup ne
        se défait pas d'un clic : il faut rouvrir chaque document.

      · AUCUN THÈME IMPLICITE. Une liste vide ne veut pas dire « tous » ; elle
        est refusée. Rendre publics quatre cent cinquante-neuf documents par
        l'oubli d'un paramètre est exactement l'accident à empêcher.

      · LES THÈMES SONT VÉRIFIÉS contre le référentiel. Un thème inventé ne
        toucherait rien, mais la réponse dirait « 0 modifié » — indiscernable
        d'un thème réellement vide. On nomme donc ce qui n'a pas été reconnu.
    """
    data = request.get_json(silent=True) or {}
    v = (data.get("visibility") or "").strip().lower()
    if v not in ("public", "internal"):
        return jsonify(ok=False, error="visibilite_invalide"), 400
    demandes = data.get("themes")
    if isinstance(demandes, str):
        demandes = [demandes]
    demandes = [str(t).strip() for t in (demandes or []) if str(t).strip()][:60]
    if not demandes:
        return jsonify(ok=False, error="theme_absent",
                       message="Indiquez au moins un thème. Aucun thème ne "
                               "signifie « aucun document », jamais « tous »."), 400
    import rag_store as _rs
    # Un thème est recevable s'il est au vocabulaire OU s'il porte réellement
    # des documents. La saisie libre est permise au chargement : un thème créé
    # à la main est absent du vocabulaire et parfaitement réel, et le refuser
    # laisserait ses documents en arrière d'une bascule qui paraîtrait faite.
    # Le contrôle sert à rattraper les fautes de frappe, pas à écarter le réel.
    try:
        en_base = set(rag.stats().get("themes") or {})
    except Exception:
        en_base = set()
    connus = [t for t in demandes if t in _rs.THEMES or t in en_base]
    inconnus = [t for t in demandes if not (t in _rs.THEMES or t in en_base)]
    if not connus:
        return jsonify(ok=False, error="theme_inconnu", inconnus=inconnus,
                       message="Aucun thème reconnu : %s."
                               % ", ".join(inconnus[:6])), 400
    essai = bool(data.get("essai"))
    try:
        n = rag.visibilite_par_themes(connus, v, essai=essai)
    except RagError as exc:
        return jsonify(ok=False, error=exc.code,
                       detail=getattr(exc, "detail", "")), exc.status
    except Exception as exc:
        app.logger.exception("visibilité en lot : échec")
        return jsonify(ok=False, error="visibilite_echec",
                       detail=_exc_detail(exc)), 500
    if not essai:
        audit.journaliser("document.visibilite.lot",
                          cible=", ".join(connus)[:120],
                          detail="%s · %d document(s)" % (v, n))
    return jsonify(ok=True, visibility=v, themes=connus, inconnus=inconnus,
                   essai=essai, modifies=n)


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
        d = rag_diagnose()
        # Ce qui passe RÉELLEMENT les deux portes — indexation ET analyse
        # préalable. Le sélecteur de fichier de la page s'en sert : sans cela
        # il invitait à choisir des formats que l'analyse refuse ensuite.
        import rag_store as _rs
        d["formats_deposables"] = _rs.formats_deposables()
        return jsonify(ok=True, **d)
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


# ── POURQUOI UN DOCUMENT EST REFUSÉ ──────────────────────────────────────────
# Un code technique seul — « pdf_illisible », « type_non_supporte » — ne dit pas
# quoi faire, et c'est précisément ce qu'on cherchait à savoir. Ces motifs
# étaient écrits pour le seul dépôt client ; la console d'administration, elle,
# renvoyait le code nu. Un même refus se lisait donc à deux endroits, et
# n'expliquait qu'à l'un des deux.
#
# Écrits ICI et partagés : deux copies auraient divergé au premier ajout.
_MOTIFS_DEPOT = {
    "pdf_illisible": "Ce PDF ne contient aucun texte extractible — c'est le cas "
                     "des plans et des documents scannés. L'indexation a besoin "
                     "de texte : fournissez une version avec couche texte (OCR) "
                     "ou le fichier source (Word, tableur).",
    "fichier_vide": "Le fichier est vide : il ne contient aucun octet.",
    "fichier_trop_lourd": "Le fichier dépasse le plafond de dépôt.",
    "requete_trop_grande": "Le fichier dépasse ce que le serveur accepte en une "
                           "requête. Découpez-le, ou déposez la version source "
                           "plutôt que l'export.",
    "type_non_supporte": "Ce format ne contient pas de texte indexable — une "
                         "image, un plan DWG ou un ancien format Office (.doc, "
                         ".xls) ne peut pas alimenter la base. Convertissez-le "
                         "en PDF avec couche texte, en Word ou en tableur.",
    "doublon": "Ce document est déjà présent, à l'identique : rien n'a été "
               "ajouté, et rien n'a été perdu.",
    "analyse_refus": "L'analyse préalable a refusé ce fichier.",
    "analyse_indisponible": "L'analyse préalable des fichiers est momentanément "
                            "indisponible sur le serveur. Réessayez dans un "
                            "instant : aucun document n'a été perdu.",
    "traitement_echec": "Le document n'a pas pu être traité par le serveur.",
    "fichier_manquant": "Aucun fichier n'a été joint à l'envoi.",
    # Le fichier est LISIBLE mais vide de texte : le distinguer d'un fichier
    # illisible évite de chercher une corruption là où il n'y en a pas.
    "aucun_texte": "Aucun texte exploitable n'a été trouvé — s'il s'agit d'un "
                   "PDF scanné (image), il n'a pas de couche texte : "
                   "ré-exportez-le avec OCR (texte reconnu), ou fournissez la "
                   "version Word / tableur.",
    "docx_illisible": "Ce document Word est illisible ou protégé par mot de "
                      "passe. Enregistrez-en une copie sans protection.",
    "xlsx_illisible": "Ce classeur Excel est illisible ou protégé par mot de "
                      "passe. Enregistrez-en une copie sans protection.",
    "pptx_illisible": "Cette présentation PowerPoint est illisible ou protégée "
                      "par mot de passe. Enregistrez-en une copie sans "
                      "protection.",
    # « support absent » : la bibliothèque de lecture manque SUR LE SERVEUR. Le
    # fichier n'est pas en cause — le dire, sinon on cherche du côté du fichier.
    "pdf_support_absent": "La lecture des PDF est indisponible sur le serveur "
                          "(bibliothèque absente) : le fichier n'est pas en "
                          "cause. Déposez une version Word ou texte en "
                          "attendant le redéploiement.",
    "docx_support_absent": "La lecture des documents Word est indisponible sur "
                           "le serveur (bibliothèque absente) : le fichier "
                           "n'est pas en cause. Déposez une version PDF ou "
                           "texte en attendant le redéploiement.",
    "xlsx_support_absent": "La lecture des classeurs Excel est indisponible sur "
                           "le serveur (bibliothèque absente) : le fichier "
                           "n'est pas en cause. Déposez un export CSV en "
                           "attendant le redéploiement.",
    "pptx_support_absent": "La lecture des présentations PowerPoint est "
                           "indisponible sur le serveur (bibliothèque "
                           "absente) : le fichier n'est pas en cause. Déposez "
                           "un export PDF en attendant le redéploiement.",
    "base_indisponible": "La base de connaissance est momentanément injoignable "
                         "(réveil à froid). Réessayez dans quelques secondes : "
                         "le document sera alors enregistré durablement.",
    "erreur_serveur": "Erreur du serveur pendant le traitement. Réessayez dans "
                      "un instant.",
}


def _motif_depot(code, detail=""):
    """Le motif lisible d'un refus, avec repli sur le détail technique."""
    motif = _MOTIFS_DEPOT.get(code)
    # Refuser un format sans dire lesquels sont acceptés, c'est laisser
    # l'utilisateur deviner. La liste est DÉRIVÉE de ce que ce déploiement
    # accepte réellement — jamais recopiée, sinon elle ment un jour.
    if code == "type_non_supporte":
        import rag_store as _rs
        formats = _rs.formats_deposables()
        if formats:
            motif += " Formats acceptés : %s." % ", ".join(
                "." + e for e in formats)
    return (motif or (detail or "").strip()
            or "Le document n'a pas pu être enregistré (%s)." % code)


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
            ok=False, error=exc.code, detail=getattr(exc, "detail", ""),
            message=_motif_depot(exc.code, getattr(exc, "detail", ""))), exc.status)
    except Exception as exc:
        # Trace complète côté serveur (logs Render) + cause réelle ASSAINIE
        # renvoyée à l'admin : un « traitement_echec » opaque devient
        # auto-diagnostiquant (ex. cause PostgreSQL réelle vs simple transitoire).
        app.logger.exception("upload-file : échec du traitement de %r", f.filename)
        return _fin("traitement_echec", _exc_detail(exc)) or (jsonify(
            ok=False, error="traitement_echec", detail=_exc_detail(exc),
            message=_motif_depot("traitement_echec", _exc_detail(exc))), 500)
    # Le registre déclare « journal des chargements, suppressions et
    # changements de visibilité » — la suppression et la visibilité étaient
    # tracées, le CHARGEMENT non, sur le chemin d'empoisonnement le plus court
    # de l'assistant. Qui a chargé quoi, quand : c'est la question d'après
    # incident, et elle n'avait pas de réponse.
    audit.journaliser("document.chargement",
                      cible=str(doc.get("id") or "")[:60],
                      detail=(doc.get("title") or f.filename or "")[:120])
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
    audit.journaliser("document.chargement",
                      cible=str(doc.get("id") or "")[:60],
                      detail=(doc.get("title") or doc.get("filename") or "")[:120])
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

# Ce que le lecteur DOIT comprendre quand la rédaction échoue.
#
# « La génération a échoué. Réessayez, ou changez de modèle » était le message
# le plus fréquent, et le moins utile : il ne dit pas ce qui a échoué, et il
# conseille de changer de modèle même lorsqu'aucun n'est configuré — auquel cas
# l'autre échouera pareil. Chaque cause porte désormais son CONSTAT, sa CAUSE
# probable et le GESTE qui la lève ; le conseil de bascule est ajouté par
# `_conseil_modele()`, et seulement quand un autre modèle est réellement prêt.
_ASSISTANT_MSG = {
    "not_configured": "Aucun modèle d'IA n'est activé sur ce serveur : la clé "
                      "d'API est absente. La rédaction est donc impossible, "
                      "quel que soit le modèle choisi. Le registre, les "
                      "calculs et les exports restent utilisables. Pour "
                      "l'activer : renseigner ANTHROPIC_API_KEY ou "
                      "MISTRAL_API_KEY dans la configuration du service.",
    "auth": "Le service d'IA a refusé la clé configurée : elle est erronée, "
            "expirée, ou sans autorisation sur ce modèle. Réessayer n'y "
            "changera rien tant qu'elle n'est pas corrigée.",
    # À distinguer de « auth » : la clé est BONNE, et le modèle aussi. C'est le
    # compte qui n'a plus de crédit — un geste de facturation, pas de
    # configuration, et aucun réglage de ce serveur n'y peut quoi que ce soit.
    "credit": "Le compte du fournisseur d'IA n'a plus de crédit : la clé et le "
              "modèle sont pourtant valides. Aucune rédaction n'aboutira tant "
              "que le compte n'est pas rechargé — le document ci-dessous a été "
              "assemblé sans modèle. L'autre modèle, s'il est configuré et "
              "approvisionné, y parvient.",
    "busy": "Le service d'IA est saturé et a refusé la demande (quota ou "
            "limite de débit). Ce n'est pas une panne : réessayez dans une "
            "minute.",
    "network": "Le service d'IA est injoignable depuis ce serveur — réseau, "
               "proxy ou coupure côté fournisseur. Rien ne lui a été transmis, "
               "et le document a été assemblé sans lui : rien n'est perdu.",
    "timeout": "Le modèle a dépassé le délai accordé pour ce document. Le "
               "service répond, il est simplement plus lent que le délai : "
               "une pièce longue peut demander un second essai.",
    # Formulé par ce que le lecteur peut FAIRE, et non par ce qui s'est cassé
    # chez notre fournisseur. Ce qu'il a besoin de savoir tient en deux points :
    # ce n'est pas la configuration de ce serveur, et un second essai passe
    # souvent. Le code d'échec et le modèle tenté partent avec la réponse et au
    # journal, pour qui diagnostique.
    "upstream": "La rédaction automatique n'a pas abouti, et la cause n'est "
                "pas dans la configuration de ce serveur. Réessayer dans un "
                "instant suffit souvent ; l'autre modèle, s'il est configuré, "
                "y parvient en général.",
    "empty": "La demande était vide : rien n'a été envoyé au modèle.",
    # Notre propre garde, pas une panne du fournisseur : trop de rédactions
    # étaient déjà en cours. Le dire ainsi évite de faire chercher la cause
    # chez le fournisseur — et de le faire réessayer alors que la file est
    # pleine.
    "sature": "Plusieurs rédactions étaient déjà en cours sur ce serveur. "
              "Pour que le site continue de répondre à tout le monde, "
              "celle-ci n'a pas attendu son tour : relancez-la dans un "
              "instant pour obtenir un texte rédigé.",
}

# Ce qui reste possible malgré l'échec. Écrit à part parce que c'est la seule
# partie qui rassure : un échec de rédaction n'empêche ni de calculer, ni de
# consulter le registre, ni d'exporter l'étude de phase.
_ASSISTANT_REPLI = ("Le calcul, le registre des pièces et les exports Word/PDF "
                    "de l'étude de phase restent disponibles.")


def _conseil_modele(modele_tente):
    """Le conseil de bascule, et seulement s'il a un sens.

    « Changez de modèle » sur un serveur où aucun modèle n'est configuré envoie
    le lecteur refaire exactement la même chose et échouer pareil. On ne le
    propose donc que si l'AUTRE fournisseur est réellement prêt.
    """
    dispo = assistant.available()
    autre = "mistral" if modele_tente == "claude" else "claude"
    if dispo.get(autre):
        return (" L'autre modèle (%s) est configuré et disponible : vous pouvez "
                "le choisir." % autre)
    if not any(dispo.values()):
        return " Aucun autre modèle n'est configuré : changer de modèle ne changerait rien."
    return ""


@app.route("/admin/livrables")
@admin_required
def admin_livrables_page():
    """Console de génération de livrables (réservée à l'administrateur)."""
    return _serve_fast("admin-livrables.html", _CC_ADMIN)


@app.route("/api/admin/livrables/types", methods=["GET"])
@admin_required
def api_livrables_types():
    """Types de livrables, modèles d'IA configurés, et périmètres types.

    Les périmètres voyagent AVEC les types, sur l'appel que la page fait déjà :
    une route de plus pour dix-huit chaînes ajouterait un aller-retour, une
    gestion d'erreur et un état « la liste n'est pas encore arrivée » — pour un
    vocabulaire qui ne bouge qu'au rythme des versions."""
    return jsonify(ok=True, types=livrables.public_types(),
                   models=assistant.available(),
                   perimetres=livrables.perimetres())


def _famille_prioritaire(type_id):
    """La famille de la base à interroger EN PREMIER pour ce livrable.

    Un livrable de centre de données doit puiser d'abord dans les documents de
    centres de données : sur une base de plusieurs centaines de pièces, une
    note d'architecture réseau bien tournée peut sortir devant une fiche
    technique de groupe froid alors que c'est la seconde qui compte pour un
    CCTP de production frigorifique. Le classement par pertinence seule ne
    connaît pas le SUJET du dossier ; la famille, si.

    Déduite du livrable, jamais imposée à tous : prioriser les centres de
    données dans une synthèse IEC 62443 la desservirait exactement autant.

      · pièces du registre d'ingénierie (« dc-piece-… ») → centres de données ;
      · types de la console dont le groupe porte le même nom → idem ;
      · tout autre groupe de la console → les thèmes que livrables.GROUPE_THEMES
        lui désigne (validés au chargement contre la base) ;
      · le reste → aucune priorité, classement par pertinence seule.

    Rend (nom de famille ou de groupe, liste de thèmes) ou (None, []).
    """
    import rag_store as _rs
    if str(type_id or "").startswith("dc-piece-"):
        return _rs.FAMILLE_DATACENTER, _rs.themes_famille(_rs.FAMILLE_DATACENTER)
    t = livrables.get_type(type_id) or {}
    # Les deux vocabulaires portent le même intitulé de famille — c'est ce qui
    # rend la correspondance vérifiable plutôt que devinée. S'ils divergent un
    # jour, `themes_famille` rend une liste vide et la priorité disparaît
    # simplement : aucun document n'est perdu, le classement redevient celui de
    # la pertinence seule.
    if t.get("groupe") == _rs.FAMILLE_DATACENTER:
        return _rs.FAMILLE_DATACENTER, _rs.themes_famille(_rs.FAMILLE_DATACENTER)
    # La priorité par thème vaut désormais pour TOUS les groupes de la console,
    # pas seulement les centres de données : un livrable NIS2 puisait sinon par
    # pertinence seule, et une fiche technique bien tournée sortait devant le
    # guide ANSSI du sujet. Même mécanique : un ordre, jamais un filtre.
    return livrables.themes_du_type(type_id)


def _hits_priorises(query, k, public_only, themes, elargir=None):
    """Les extraits, famille prioritaire d'abord, le reste ensuite.

    `elargir` est la recherche générale (déjà faite, ou None pour la faire
    ici) : on garde ses résultats pour COMPLÉTER, jamais pour remplacer. Une
    famille qui ne répond pas ne doit pas priver le livrable du reste de la
    base — la priorité est un ordre, pas un filtre.
    """
    prio = []
    if themes:
        try:
            prio = rag.search(query, k=k, public_only=public_only, theme=themes)
        except Exception:
            prio = []
    reste = elargir
    if reste is None:
        try:
            reste = rag.search(query, k=k, public_only=public_only)
        except Exception:
            reste = []
    # Dédoublonnage sur le contenu du fragment, pas sur le document : un même
    # document peut légitimement fournir deux extraits différents, et les
    # confondre en écarterait un.
    vus = {(h.get("doc_id"), (h.get("content") or "")[:120]) for h in prio}
    for h in reste:
        cle = (h.get("doc_id"), (h.get("content") or "")[:120])
        if cle in vus:
            continue
        vus.add(cle)
        prio.append(h)
    return prio[:k]


def _federer(query, hits, k=8, doc_ids=None):
    """Les extraits de la base sœur, mêlés à ceux d'ici.

    APPELÉ EN DERNIER, ET UNE SEULE FOIS. Le classement local encode un savoir
    que le pair ne peut pas reproduire — la famille du type, le sous-dossier de
    la pièce, le re-classement par juge. Fédérer AVANT le détruirait ; fédérer
    à chaque étape de la chaîne interrogerait le pair trois fois par livrable.

    UNE SÉLECTION MANUELLE N'EST PAS FÉDÉRÉE. Quand l'utilisateur a désigné des
    documents, il a dit lesquels : y ajouter d'autres bases contredirait son
    choix, et c'est le seul cas où la fédération serait une nuisance.

    Rend (hits, resume). `resume` porte le compte par base et l'état du pair :
    c'est ce qui permet au livrable de dire sur quoi il a été écrit — et
    surtout de dire quand il n'a eu qu'une base.
    """
    if doc_ids or not rag_federe.configure():
        return hits, None
    try:
        res = rag_federe.chercher(query, hits, k=k)
    except Exception:
        app.logger.exception("fédération RAG")
        return hits, None
    if not res["fragments"]:
        return hits, res
    return rag_federe.en_forme(res["fragments"]), res


def _extraits_pour(query, doc_ids=None, public_only=False):
    """Les extraits de la base, sans re-classement par modèle.

    Le re-classement demande un modèle de langage ; ici il n'y en a pas. On
    prend donc les meilleurs résultats de la recherche lexicale, ce qui est
    précisément ce que le magasin sait faire seul.

    `public_only` n'est pas un réglage de confort : la trame reproduit les
    extraits MOT POUR MOT. Un document interne retrouvé pour un compte
    ordinaire se retrouverait recopié dans un livrable qui sort du site."""
    try:
        if doc_ids:
            return rag.search(query, k=8, public_only=public_only, doc_ids=doc_ids)
        return rag.search(query, k=8, public_only=public_only)
    except Exception:
        return []


def _trame_sans_modele(type_id, data, extra_query, label, dispo,
                       public_only=False, echec=None, documentaire=False):
    """La pièce assemblée quand aucun modèle n'est disponible — ou quand la
    rédaction par modèle est DÉBRANCHÉE par choix (`documentaire=True`).

    Le document reste EXACT — plan du registre, chiffres du moteur, manques
    calculés, extraits reproduits tels quels — et il porte en tête ce qu'il
    est. C'est un document de travail complet, pas un livrable rédigé.
    """
    # Même complément que le chemin avec modèle : la fiche du projet ouvert
    # remplit les champs laissés vides (client, secteur…), et sa matière entre
    # dans la requête documentaire. La trame est un document remis — elle n'a
    # pas moins droit au contexte du projet que la version rédigée.
    _completer_depuis_projet(data)
    phase = str(data.get("phase") or "").strip().upper()[:12]
    code = str(data.get("piece") or "").strip().upper()[:16]
    profil = _profil_datacenter(data)
    query = (livrables.retrieval_query(type_id, data) + " " + extra_query).strip()
    doc_ids = [d for d in (data.get("doc_ids") or []) if _rag_valid_doc_id(d)]
    if doc_ids:
        # Sélection manuelle : elle EST la priorité, et rien ne doit la
        # réordonner par-dessus.
        hits = _extraits_pour(query, doc_ids, public_only)
        famille = None
    else:
        famille, themes = _famille_prioritaire(type_id)
        hits = _hits_priorises(query, 8, public_only, themes,
                               elargir=_extraits_pour(query, None, public_only))
        # LE BON SOUS-DOSSIER PASSE DEVANT LA FAMILLE. La famille dit « c'est
        # un document de centre de données » ; le sous-dossier dit « c'est LE
        # thème de cette pièce ». Pour un CCTP de production frigorifique, la
        # note thermique doit sortir devant la note carbone — toutes deux sont
        # de la famille, une seule est du sujet. Même mécanique que la
        # famille : un ordre, jamais un filtre — appliquée par-dessus.
        pc0 = ingenierie_dc.piece(phase, code) if (phase and code) else None
        if pc0:
            sous = ingenierie_dc.sous_dossiers(pc0["code"],
                                               pc0.get("discipline"))
            if sous:
                hits = _hits_priorises(query, 8, public_only, sous,
                                       elargir=hits)
    hits, _fed = _federer(query, hits, 8, doc_ids)

    # ── CHERCHER PAR POINT EXIGÉ, PUIS ASSEMBLER ─────────────────────────
    # La couverture était calculée ICI AUSSI, mais APRÈS la trame : elle ne
    # servait qu'à l'annexe, et la trame était assemblée sur les extraits
    # d'une seule requête générale. Elle remonte avant, et le MÊME objet sert
    # aux deux — la base n'est plus interrogée deux fois par pièce.
    couverture = None
    if phase and code:
        def _chercher(req, k):
            if doc_ids:
                return _extraits_pour(req, doc_ids, public_only)[:k]
            return rag.search(req, k=k, public_only=public_only)
        try:
            couverture = ingenierie_dc.couverture_documentaire(
                phase, code, _chercher, data, garder_extraits=True)
        except Exception:
            app.logger.exception("couverture documentaire")
        # Sélection manuelle : la couverture dit ce qui manque, elle ne
        # réordonne pas ce que vous avez choisi.
        if couverture and not doc_ids:
            hits = ingenierie_dc.extraits_pour_redaction(couverture, hits)

    if documentaire:
        # Le modèle n'a pas manqué : il est débranché. Le dire avec les mots
        # de l'indisponibilité enverrait vérifier une configuration intacte.
        mode = "documentaire" if hits else "documentaire_seul"
    else:
        mode = ingenierie_dc.mode_redaction(False, hits)
    m = ingenierie_dc.MODES_REDACTION[mode]
    # La cause, portée JUSQUE DANS le document. Une trame reçue alors qu'un
    # modèle est configuré ressemble sinon à une panne du site : on relance, on
    # obtient la même chose, et on ne sait toujours pas s'il faut changer de
    # modèle ou attendre.
    note = None
    if echec:
        note = ("**Le modèle « %s » n'a pas répondu** (%s). %s Le document a "
                "donc été assemblé sans lui, à partir du moteur et de la base."
                % (echec.get("modele") or "?", echec.get("error") or "cause "
                   "non qualifiée", (echec.get("message") or "").strip()))
    texte = None
    try:
        # D'abord la pièce de phase — plan du registre, grandeurs, manques
        # calculés. Elle n'existe que si la demande en porte une.
        texte = ingenierie_dc.trame_piece(profil, phase, code, hits, data, note,
                                          mode=mode)
    except Exception:
        app.logger.exception("trame sans modèle : pièce")

    # La couverture — calculée plus haut, AVANT l'assemblage — est versée au
    # document. C'est le même objet : la pièce est assemblée sur ce que le
    # dossier de sources déclare, et non l'inverse.
    if couverture and texte:
        texte += "\n\n" + ingenierie_dc.couverture_markdown(couverture)
    if not texte:
        # Puis le livrable de la console : soixante-sept types, chacun avec son
        # plan. Sans ce second essai, la console refusait purement et
        # simplement dès qu'aucune clé n'était configurée — alors que le plan
        # existait, que la base répondait et que la note de calcul était là.
        try:
            texte = livrables.trame(type_id, data, hits, m["nom"], m["aide"], note)
        except Exception:
            app.logger.exception("trame sans modèle : livrable")
    if not texte:
        # Ni pièce connue, ni type connu : là, on refuse vraiment, avec la
        # cause. Deviner un plan serait pire que de refuser.
        return jsonify(ok=False, error="not_configured", modele=None,
                       modeles_disponibles=dispo,
                       message=_ASSISTANT_MSG["not_configured"],
                       repli=_ASSISTANT_REPLI), 503
    sources, rang = [], {}
    for h in hits:
        did = h.get("doc_id")
        if did in rang:
            sources[rang[did]]["extraits"] += 1
            continue
        rang[did] = len(sources)
        # LE TITRE EST NETTOYÉ ICI, une fois pour toutes. Nettoyé au seul
        # moment de composer le document, l'écran continuait d'afficher le nom
        # de fichier brut pendant que le livrable citait la référence — deux
        # vérités pour la même source, et celle qu'on lit à l'écran est celle
        # qu'on recopie dans un courriel.
        sources.append({"title": extraits_mod.titre_document(h.get("title")),
                        "theme": h.get("theme"),
                        "visibility": h.get("visibility"), "extraits": 1})
    projet_id = _projet_du_compte(data.get("projet_id"))
    # L'intitulé, et il ne peut PAS rester vide : c'est lui qu'on lit dans la
    # liste de l'historique. « APD SPC-HVAC » vaut pour une pièce de phase ;
    # un livrable de console n'a ni l'une ni l'autre, et se retrouvait
    # enregistré sous un espace — introuvable autrement qu'en ouvrant chaque
    # ligne une par une.
    intitule = (label or ("%s %s" % (phase, code)).strip()).strip()
    if not intitule:
        t = livrables.get_type(type_id)
        intitule = (t["label"] if t else "") or type_id
    saved_id = None
    try:
        pc = ingenierie_dc.piece(phase, code) or {}
        saved_id = livrables_hist.save({
            "type": type_id,
            "label": intitule,
            "client": data.get("client"), "secteur": data.get("secteur"),
            "perimetre": data.get("perimetre"),
            # Le « modèle » enregistré nomme le mode : relu six mois plus tard,
            # un document doit dire par quoi il a été produit.
            # Relu six mois plus tard, un document doit dire par quoi il a été
            # produit — et, s'il y a lieu, que le modèle avait échoué.
            "model": ("trame-%s-apres-echec-%s"
                      % (mode, echec.get("error") or "?"))[:60]
                     if echec else "trame-" + mode,
            "markdown": texte, "sources": sources,
            "projet_id": projet_id, "phase": phase,
            "filiere": (data.get("filiere") or ""),
            "piece": code,
            "numero": (data.get("numero") or ""),
            "indice": (data.get("indice") or ""),
            "etat": "brouillon"})
        if projet_id:
            try:
                projets_db.toucher(projet_id)
            except Exception:
                pass
    except Exception:
        saved_id = None
    audit.journaliser("datacenter.trame", cible="%s/%s" % (phase, code),
                      detail=mode + (" · après échec %s" % echec.get("error")
                                     if echec else ""))
    return jsonify(ok=True, document=texte, model="trame-" + mode,
                   echec_modele=echec,
                   mode=mode, mode_nom=ingenierie_dc.MODES_REDACTION[mode]["nom"],
                   mode_aide=ingenierie_dc.MODES_REDACTION[mode]["aide"],
                   sans_modele=True, sources=sources, id=saved_id,
                   corpus="public" if public_only else "complet",
                   famille_prioritaire=famille,
                   # La couverture point par point, servie AUSSI hors du
                   # document : l'écran la montre avant qu'on ouvre le Word,
                   # là où l'on décide encore de verser une pièce à la base.
                   couverture=couverture,
                   # Le cartouche du Word et du PDF s'en sert : sans eux, deux
                   # versions du même document sortent identiques.
                   numero=data.get("numero") or "", indice=data.get("indice") or "",
                   phase=phase,
                   modeles_disponibles=dispo)


def _livrables_run(type_id, data, system, user, extra_query="", label=None,
                   public_only=False):
    """Ancre le prompt sur la base de connaissance (documents publics + internes),
    génère le livrable, l'enregistre dans l'historique et renvoie la réponse JSON.
    Partagé par la génération, l'affinage et les pièces de dossier de projet.

    `label` sert aux documents qui ne figurent pas dans livrables.TYPES — les
    pièces de phase sont au nombre de cent-huit, et les verser au menu déroulant
    de la console le rendrait inutilisable. Sans ce paramètre, l'historique les
    enregistrait sous leur identifiant technique.
    """
    model = "mistral" if data.get("model") == "mistral" else "claude"
    # ── Refuser TÔT plutôt qu'à la fin ────────────────────────────────────
    # Sans clé d'API, l'échec était certain dès la première ligne : on
    # construisait quand même les prompts, on interrogeait la base
    # documentaire, on attendait, et on annonçait « la génération a échoué »
    # après coup. Un échec connu d'avance doit se dire d'avance — l'attente
    # n'apporte rien, et la faire subir laisse croire à une panne passagère.
    dispo = assistant.available()
    # ── Le modèle demandé n'est pas configuré ──────────────────────────────
    # Si l'AUTRE l'est, on le dit sans basculer d'office : une bascule
    # silencieuse masquerait le fait que le modèle choisi n'est pas celui qui a
    # écrit, et c'est au lecteur de trancher.
    if not dispo.get(model):
        autre = "mistral" if model == "claude" else "claude"
        if dispo.get(autre):
            # ON NE BASCULE PAS D'OFFICE — une bascule silencieuse masquerait
            # QUI a écrit, et c'est une information qu'on ne retrouve plus
            # après coup. Mais ne pas basculer n'oblige pas à rendre la main
            # vide : le plan, les grandeurs et les extraits ne dépendent pas du
            # modèle. On assemble donc, en disant les deux choses — le modèle
            # demandé n'est pas là, l'autre l'est et reste à un clic.
            msg = ("Le modèle « %s » n'est pas configuré sur ce serveur. "
                   "Le modèle « %s » l'est : choisissez-le pour faire rédiger "
                   "cette pièce." % (model, autre))
            r = _trame_sans_modele(
                type_id, data, extra_query, label, dispo, public_only,
                {"error": "modele_indisponible", "modele": model,
                 "message": msg})
            if not (isinstance(r, tuple)
                    or (hasattr(r, "status_code") and r.status_code != 200)):
                return r
            return jsonify(
                ok=False, error="modele_indisponible", modele=model,
                modeles_disponibles=dispo, message=msg,
                repli=_ASSISTANT_REPLI), 503
        # Aucun modèle : on ne rend PAS la main vide. Le plan de la pièce est
        # au registre, les grandeurs viennent du moteur, les extraits de la
        # base — le modèle rédige autour de tout cela, il ne le produit pas.
        # On assemble donc la trame, et on dit très clairement qu'elle n'est
        # pas rédigée : présenter une trame comme un livrable fini serait la
        # seule vraie faute ici.
        return _trame_sans_modele(type_id, data, extra_query, label, dispo,
                                  public_only)
    query = (livrables.retrieval_query(type_id, data) + " " + extra_query).strip()
    # Documents de référence choisis manuellement (facultatif) ; sinon récupération auto.
    doc_ids = [d for d in (data.get("doc_ids") or []) if _rag_valid_doc_id(d)]
    # Version parente (chaînage des itérations) — présent lors d'un affinage.
    parent_id = data.get("parent_id")
    parent_id = parent_id if _rag_valid_doc_id(parent_id) else None
    hits = []
    famille = None
    # Initialisé AVANT le try : la branche d'exception saute l'affectation, et
    # un `fed` non défini transformerait un échec de recherche — rattrapé,
    # bénin — en NameError qui emporte toute la génération.
    fed = None
    try:
        if doc_ids:
            # Documents choisis manuellement : on respecte la sélection (pas de
            # re-classement qui écarterait des extraits voulus) — mais le
            # périmètre de visibilité, lui, ne se choisit pas depuis le
            # navigateur : désigner un identifiant de document n'est pas une
            # autorisation de le lire.
            hits = rag.search(query, k=8, public_only=public_only, doc_ids=doc_ids)
        else:
            # Récupération LARGE puis re-classement par LLM-juge → les 8 extraits
            # les plus pertinents avant génération (précision accrue). Repli sûr
            # (sans clé API ou en cas d'échec : simple troncature).
            large = assistant.rerank(model, query,
                                     rag.search(query, k=24,
                                                public_only=public_only), 8)
            # LA FAMILLE PASSE DEVANT, et APRÈS le re-classement : le juge
            # ordonne par pertinence, la famille par sujet. Le faire avant
            # laisserait le juge défaire l'ordre qu'on vient de poser — c'est
            # précisément son travail que de réordonner.
            famille, themes = _famille_prioritaire(type_id)
            hits = _hits_priorises(query, 8, public_only, themes, elargir=large)
            # LE SOUS-DOSSIER DE LA PIÈCE PASSE DEVANT LA FAMILLE — même
            # mécanique que sur le chemin documentaire (_trame_sans_modele),
            # qui l'avait et que ce chemin n'avait pas : rebrancher le modèle
            # faisait PERDRE la précision fine. Pour un CCTP de production
            # frigorifique, la note thermique doit sortir devant la note
            # carbone — toutes deux sont de la famille, une seule est du sujet.
            ph0 = str(data.get("phase") or "").strip().upper()[:12]
            pi0 = str(data.get("piece") or "").strip().upper()[:16]
            pc0 = ingenierie_dc.piece(ph0, pi0) if (ph0 and pi0) else None
            if pc0:
                sous = ingenierie_dc.sous_dossiers(pc0["code"],
                                                   pc0.get("discipline"))
                if sous:
                    hits = _hits_priorises(query, 8, public_only, sous,
                                           elargir=hits)
        hits, fed = _federer(query, hits, 8, doc_ids)
    except Exception:
        hits = []
    # ── CHERCHER PAR POINT EXIGÉ, PUIS ÉCRIRE ────────────────────────────
    # CE QUI SE PASSAIT AVANT, ET QUI NE SE VOYAIT PAS. La pièce déclare trois
    # à six points de contenu exigé. La rédaction recevait les extraits d'UNE
    # SEULE requête générale : le quatrième point n'avait jamais fait l'objet
    # d'une recherche, et rien ne disait au modèle que la base n'en parlait
    # pas. Il l'écrivait donc quand même, avec ce qu'il croit savoir — une
    # pièce qui a l'air documentée sans l'être, ce qui ne se découvre qu'au
    # visa.
    #
    # CELA NE COÛTE AUCUN APPEL DE MODÈLE : `couverture_documentaire` ne fait
    # que des recherches. Trois à six requêtes de plus, sur un chemin qui fait
    # déjà un appel au juge de reclassement.
    couverture = None
    _ph = str(data.get("phase") or "").strip().upper()[:12]
    _pi = str(data.get("piece") or "").strip().upper()[:16]
    if _ph and _pi:
        def _chercher_point(req, k):
            if doc_ids:
                return rag.search(req, k=k, public_only=public_only,
                                  doc_ids=doc_ids)
            return rag.search(req, k=k, public_only=public_only)
        try:
            couverture = ingenierie_dc.couverture_documentaire(
                _ph, _pi, _chercher_point, data, garder_extraits=True)
        except Exception:
            # La couverture est un APPUI, jamais une condition : une base qui
            # ne répond pas ne doit pas empêcher d'écrire.
            app.logger.exception("couverture avant rédaction")
            couverture = None
        # UNE SÉLECTION MANUELLE NE SE FAIT PAS RÉORDONNER. Vous avez dit
        # quels documents : la couverture reste calculée — elle dira quels
        # points exigés ces documents-là ne couvrent pas —, mais l'ordre des
        # extraits reste le vôtre. Même doctrine que pour la fédération.
        if couverture and not doc_ids:
            hits = ingenierie_dc.extraits_pour_redaction(couverture, hits)
    # LES SOURCES SONT BÂTIES SUR LES EXTRAITS RÉELLEMENT INCLUS. Le budget
    # coupe, la déduplication écarte : construire la liste nominative sur les
    # huit hits COMPLETS faisait ordonner au modèle de « couvrir » et citer des
    # documents dont aucun extrait n'avait atteint le prompt — une invitation
    # directe à la citation inventée. Le budget passe aussi de 6000 à 9000 :
    # huit extraits de ~900 caractères plus leurs étiquettes y tiennent.
    context, retenus = build_context_retenus(hits, max_chars=9000)

    # Regroupement des extraits par DOCUMENT : le modèle reçoit ainsi la liste
    # nominative de ce qui l'alimente (et non des extraits anonymes), et la même
    # liste sert à sourcer le document exporté. Une seule source de vérité.
    sources, rang = [], {}
    for h in retenus:
        did = h.get("doc_id")
        if did in rang:
            sources[rang[did]]["extraits"] += 1
            continue
        rang[did] = len(sources)
        # LE TITRE EST NETTOYÉ ICI, une fois pour toutes. Nettoyé au seul
        # moment de composer le document, l'écran continuait d'afficher le nom
        # de fichier brut pendant que le livrable citait la référence — deux
        # vérités pour la même source, et celle qu'on lit à l'écran est celle
        # qu'on recopie dans un courriel.
        sources.append({"title": extraits_mod.titre_document(h.get("title")),
                        "theme": h.get("theme"),
                        # LA BASE SUIT LA SOURCE JUSQU'À L'ÉCRAN ET À L'EXPORT.
                        # Elle est déjà dans l'étiquette que lit le modèle ; si
                        # elle s'arrêtait là, le lecteur du livrable verrait une
                        # liste de documents sans savoir lesquels viennent de
                        # l'autre maison.
                        "base": h.get("base") or "",
                        "visibility": h.get("visibility"), "extraits": 1})
    user = user + livrables.dossier_documentaire(sources, choix_manuel=bool(doc_ids))
    # CE QUE LA BASE NE DIT PAS, NOMMÉ AU MODÈLE. Sans cela, il comble le trou ;
    # avec, il l'annonce. C'est la moitié utile du branchement.
    if couverture:
        user += ingenierie_dc.consigne_manques(couverture)

    try:
        text, used_model = assistant.generate(model, system, user, context=context)
    except assistant.AssistantError as exc:
        # ── LE MODÈLE A ÉCHOUÉ : ON NE REND PAS LA MAIN VIDE ─────────────────
        # « Si l'IA ne fonctionne pas, alors seulement avec la base » — la
        # règle valait déjà pour un modèle ABSENT ; elle vaut tout autant pour
        # un modèle qui répond par une erreur. Le plan est au registre, les
        # grandeurs au moteur, les extraits à la base : tout ce qui ne dépend
        # pas du modèle est là, et le refuser ne protège de rien.
        #
        # La cause N'EST PAS ESCAMOTÉE pour autant : elle part dans la réponse
        # ET s'inscrit en tête du document. Une trame rendue sans dire pourquoi,
        # alors qu'un modèle est configuré, ferait relancer indéfiniment sans
        # savoir s'il faut changer de modèle ou attendre.
        message = (_ASSISTANT_MSG.get(exc.code, "La rédaction a échoué pour "
                                      "une raison que le serveur n'a pas su "
                                      "qualifier.")
                   + _conseil_modele(model))
        app.logger.warning("rédaction : modèle %s en échec (%s) — repli sur la "
                           "trame", model, exc.code)
        echec = {"error": exc.code, "modele": model, "message": message}
        r = _trame_sans_modele(type_id, data, extra_query, label,
                               assistant.available(), public_only, echec)
        # La trame n'a pas pu être bâtie non plus (type et pièce inconnus) :
        # là seulement, on refuse, et avec la cause du modèle.
        if isinstance(r, tuple) or (hasattr(r, "status_code")
                                    and r.status_code != 200):
            return jsonify(
                ok=False, error=exc.code, modele=model,
                modeles_disponibles=assistant.available(),
                message=message, repli=_ASSISTANT_REPLI), exc.status
        return r

    # Le projet de rattachement vient du CLIENT : on ne le croit pas sur parole.
    # Un identifiant est un identifiant, pas une autorisation — recopié depuis
    # une autre session, il verserait ce document dans l'historique d'un tiers,
    # qui le lirait et le sauvegarderait avec les siens. On le fait donc valider
    # par le magasin, qui filtre sur le propriétaire ; s'il ne le reconnaît pas,
    # le livrable est produit quand même, mais SANS rattachement.
    projet_id = _projet_du_compte(data.get("projet_id"))

    # Enregistrement dans l'historique (best-effort : n'interrompt jamais la réponse).
    saved_id = None
    try:
        t = livrables.get_type(type_id)
        saved_id = livrables_hist.save({
            "type": type_id, "label": (t["label"] if t else None) or label or type_id,
            "client": data.get("client"), "secteur": data.get("secteur"),
            "perimetre": data.get("perimetre"), "model": used_model,
            "markdown": text, "sources": sources, "parent_id": parent_id,
            # Le rattachement au projet, à la phase et à la filière. Sans lui,
            # le livrable rejoint une liste plate et n'est plus retrouvable
            # autrement qu'en lisant les intitulés un par un.
            "projet_id": projet_id,
            "phase": (data.get("phase") or ""),
            "filiere": (data.get("filiere") or ""),
            "piece": (data.get("piece") or ""),
            # Le numéro et l'indice étaient calculés, rendus à l'écran, portés
            # au cartouche du Word — et perdus à l'enregistrement. La liste des
            # documents du projet les redemande, et c'est exactement la colonne
            # qu'on cherche dans un registre.
            "numero": (data.get("numero") or ""),
            "indice": (data.get("indice") or ""),
            "etat": "brouillon"})
        # La génération elle-même est journalisée — métadonnées seules,
        # jamais le contenu : les analyses juridiques, le playbook et l'agent
        # tracent déjà les leurs, celle-ci partait au modèle sans trace.
        audit.journaliser("livrable.generation", cible=(type_id or "")[:80],
                          detail="%s, %d source(s)" % (used_model, len(sources)))
        # La date de dernière activité du projet suit ce qui y est produit :
        # c'est elle qui trie utilement une liste de projets.
        if projet_id:
            try:
                projets_db.toucher(projet_id)
            except Exception:
                pass
    except Exception:
        saved_id = None

    mode = ingenierie_dc.mode_redaction(True, hits)
    return jsonify(ok=True, document=text, model=used_model, sources=sources,
                   id=saved_id, mode=mode,
                   mode_nom=ingenierie_dc.MODES_REDACTION[mode]["nom"],
                   mode_aide=ingenierie_dc.MODES_REDACTION[mode]["aide"],
                   corpus="public" if public_only else "complet",
                   # SUR QUOI LE DOCUMENT A ÉTÉ ÉCRIT. La mention est due même
                   # quand tout va bien — et surtout quand la base sœur n'a pas
                   # répondu : le livrable aurait alors pu être différent, et le
                   # lecteur est le seul à pouvoir en décider.
                   bases=(rag_federe.mention(fed) if fed else None),
                   bases_detail=({"n_local": fed["n_local"], "n_pair": fed["n_pair"],
                                  "pair_ok": fed["pair_ok"], "motif": fed["motif"]}
                                 if fed else None),
                   famille_prioritaire=famille,
                   numero=data.get("numero") or "", indice=data.get("indice") or "",
                   phase=(data.get("phase") or "").strip().upper()[:12],
                   sans_modele=False)


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
    # LE PROJET OUVERT ENTRE DANS LE PROMPT — avant sa construction, pas après
    # la génération. Le magasin porte nom, client, secteur, périmètre, filière,
    # phase, note de cadrage ; le formulaire, souvent, rien : le document
    # sortait avec « [client à préciser] » pendant que la fiche du projet
    # disait le client. Les champs SAISIS gardent la main — seuls les vides
    # sont complétés — et la propriété du projet est vérifiée par le magasin.
    bloc_projet = _completer_depuis_projet(data)
    prompts = livrables.build_prompts(type_id, data)
    if not prompts:
        return jsonify(ok=False, error="type_inconnu", message="Type de livrable inconnu."), 400
    system, user = prompts
    if bloc_projet:
        user += bloc_projet
    return _livrables_run(type_id, data, system, user)


def _redige_par_modele(model):
    """Un modèle de langage a-t-il écrit ce document ?

    LA MÊME DÉCISION QUE `_auteur_document`, PRISE UNE SEULE FOIS. Elle sert
    maintenant à deux choses — le cartouche « Établi par » et le marquage de
    l'article 50.2 dans les propriétés du fichier — et deux exemplaires
    divergeraient : c'est celui qu'on oublie de corriger qui resterait, et le
    document dirait « moteur » sur sa page de garde pendant que ses propriétés
    diraient « généré par IA ».

    Seul un code `trame-*` PROUVE qu'aucun modèle n'est intervenu : c'est le
    moteur qui l'écrit lui-même à l'assemblage. Un code vide ou inconnu ne
    prouve rien, et vaut donc VRAI — un marquage en trop se corrige, un
    marquage manquant est une obligation du fournisseur qu'on a perdue sans
    que personne le voie.
    """
    return not (model or "").strip().startswith("trame-")


def _auteur_document(model):
    """Qui a établi le document, en clair pour le cartouche.

    L'historique enregistre un code technique — « trame-moteur_seul »,
    « claude-sonnet-4 ». Il a sa place dans la traçabilité, pas dans la ligne
    « Établi par » d'un document remis à un client.
    """
    m = (model or "").strip()
    if not m:
        return ""
    if not _redige_par_modele(m):
        return "Moteur d'ingénierie CONSEILPREV %s" % ingenierie_dc.VERSION
    return "Rédaction assistée (%s), relue par un ingénieur" % m


def _indice_piece(projet_id, phase, code):
    """L'indice de cette émission, compté sur les versions déjà au dossier.

    Deux chiffres, comme sur un plan : « 01 » pour la première émission, « 02 »
    pour la reprise après relecture. Compté et non demandé : personne ne tient
    à jour un numéro de version à la main, et un indice saisi finit toujours
    par redire celui du tirage précédent.

    Hors projet, l'indice reste « 01 » : le document n'entre dans aucune
    séquence, et prétendre le contraire lui donnerait une histoire qu'il n'a
    pas.
    """
    if not projet_id:
        return "01"
    try:
        n = sum(1 for r in livrables_hist.list()
                if r.get("projet_id") == projet_id
                and (r.get("phase") or "") == phase
                and (r.get("piece") or "") == code)
    except Exception:
        app.logger.exception("indice de pièce")
        return "01"
    return "%02d" % (n + 1)


def _rediger_piece():
    """Rédige une pièce du registre de phase, ancrée sur la base de connaissance.

    Deux portes mènent ici, et elles ne donnent pas accès au même corpus :

      · /api/datacenter/piece — tout compte connecté. C'est la porte du CLIENT,
        celui qui monte son dossier. Sa recherche est bornée aux documents
        PUBLICS de la base. Ce n'est pas un réglage de confort : la trame
        reproduit les extraits mot pour mot, et un document interne retrouvé
        pour un compte ordinaire se retrouverait recopié dans un livrable qui
        sort du site. « Interne » veut dire exactement cela.

      · /api/admin/datacenter/piece — administrateur. Base entière, publics et
        internes, comme la console de rédaction.

    Le REGISTRE, lui, reste consultable par tout compte connecté — c'est la
    référence, et la garder derrière un verrou la rendrait inutile.

    Les prompts sont construits par ingenierie_dc : ils portent la frontière
    entre grandeurs acquises et grandeurs à produire, et cette frontière est
    calculée, pas rédigée.
    """
    admin = _is_admin_request()
    # Deux compteurs distincts. Une rédaction par modèle coûte des jetons ;
    # borner l'adresse seule laisserait un bureau entier derrière un même
    # routeur se partager douze rédactions, et un compte seul en consommer
    # autant qu'il veut en changeant de réseau. Le compte est ce qu'on cherche
    # à limiter, l'adresse ce qui reste quand il n'y a pas mieux.
    for ckey, lim in (("gen:%s" % client_ip(), 12 if admin else 20),
                      ("genc:%s" % (_proprietaire() or "-"), 12 if admin else 20)):
        if guard.blocked(ckey, limit=lim, window=600):
            return jsonify(ok=False, error="rate_limited",
                           message="Trop de rédactions en peu de temps. "
                                   "Patientez quelques minutes."), 429
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
    # L'INDICE, calculé sur ce qui existe déjà. Une reprise après relecture est
    # une nouvelle version du MÊME document, pas un document de plus : sans
    # indice, deux tirages se ressemblent à s'y méprendre une fois imprimés, et
    # c'est la date du fichier qui fait foi — elle change à chaque copie.
    data["indice"] = _indice_piece(data.get("projet_id"), phase, code)
    data["numero"] = "%s-%s" % (pc["code"], phase)
    audit.journaliser("datacenter.piece", cible="%s/%s" % (phase, code),
                      detail="%s · corpus %s · indice %s"
                             % (pc["titre"][:100],
                                "complet" if admin else "public",
                                data["indice"]))
    type_id = "dc-piece-%s-%s" % (phase.lower(), code.lower())
    label = "%s %s — %s" % (phase, pc["code"], pc["titre"])
    # ── LA RÉDACTION PAR MODÈLE EST DÉBRANCHÉE SUR CETTE PAGE, par choix ──
    # Le moteur compose le cadre exigentiel — ce qu'une pièce doit contenir —
    # et le texte documentaire vient des documents chargés dans la base,
    # cherchés d'abord dans les sous-dossiers du thème de la pièce. Aucun
    # jeton d'API n'est consommé, aucune prose n'est générée : tout ce qui est
    # dans la pièce se vérifie à sa source.
    #
    # INGENIERIE_REDACTION=modele rebranche le modèle sans redéploiement de
    # code — le jour où la rédaction assistée redevient voulue ici. La
    # console d'administration et le chat, eux, ne changent pas de régime.
    if (os.environ.get("INGENIERIE_REDACTION") or "documentaire") \
            .strip().lower() != "modele":
        return _trame_sans_modele(type_id, data, requete, label,
                                  assistant.available(),
                                  public_only=not admin, documentaire=True)
    return _livrables_run(type_id, data, system, user, extra_query=requete,
                          label=label, public_only=not admin)


@app.route("/api/datacenter/piece", methods=["POST"])
@login_required
def api_datacenter_piece_client():
    """La porte du client : rédiger les pièces de SON dossier.

    Le registre, le calcul et le dossier lui étaient déjà ouverts ; seule
    l'écriture restait réservée, au motif qu'elle consomme des jetons d'API.
    L'argument ne tient plus dans les deux cas où il n'y en a pas : sans
    modèle, la pièce est assemblée à partir du moteur et de la base, et ne
    coûte rien. Il reste vrai quand un modèle écrit — d'où le compteur par
    compte, et non par adresse.

    Ce qui reste réservé : le corpus interne (cf. _rediger_piece), le dépôt de
    documents dans la base, et la console d'administration.
    """
    return _rediger_piece()


@app.route("/api/admin/datacenter/piece", methods=["POST"])
@admin_required
def api_datacenter_piece():
    """La même rédaction, sur la base ENTIÈRE — publics et internes."""
    return _rediger_piece()


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
        # La promesse de cette route — « exactement les mêmes étapes que
        # _livrables_run » — omettait la priorité par famille : pour un type
        # « Centres de données », l'aperçu classait autrement que la
        # génération, précisément le mensonge que la route dit empêcher.
        famille, themes = _famille_prioritaire(type_id)
        hits = _hits_priorises(query, 8, False, themes, elargir=hits)
        # L'APERÇU FÉDÈRE AUSSI, et c'est la raison d'être de cette route :
        # elle promet « exactement les mêmes étapes que la génération ». Un
        # aperçu qui montrerait la seule base locale annoncerait des sources
        # que le livrable n'aurait pas, et en tairait d'autres qu'il aurait.
        hits, _fed = _federer(query, hits, 8, None)
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
    return jsonify(ok=True, query=query, documents=docs, extraits=len(hits),
                   famille_prioritaire=famille)


# ═══════════════════════════════════════════════════════════════════════════
#  LES PROJETS D'INGÉNIERIE, ET LEUR HISTORIQUE
# ═══════════════════════════════════════════════════════════════════════════
# Le propriétaire d'un projet est le compte connecté, et c'est le MAGASIN qui
# filtre dessus — pas la route. Une vérification posée dans l'appelant s'oublie
# au deuxième appelant, et c'est ce jour-là qu'un client voit le dossier d'un
# autre.

def _proprietaire():
    u = current_user() or {}
    return (u.get("email") or "").strip().lower()


def _completer_depuis_projet(data):
    """Complète les champs VIDES de `data` depuis la fiche du projet ouvert, et
    rend le bloc « Contexte du projet » à joindre au prompt (ou "").

    C'est l'adaptation au projet CHOISI : le magasin sait le client, le
    secteur, la filière, la phase et la note de cadrage — les redemander au
    formulaire faisait générer des documents à trous sur des projets
    entièrement renseignés. Trois règles :

      · le formulaire GARDE LA MAIN : une saisie explicite n'est jamais
        écrasée, seuls les champs vides sont complétés ;
      · la propriété est vérifiée par le MAGASIN (même règle que le
        rattachement d'historique) : un identifiant de projet arrive du
        navigateur, donc de n'importe qui ;
      · l'échec est silencieux : un projet illisible rend le comportement
        d'avant — le document se génère sur le seul formulaire.
    """
    pid = (data.get("projet_id") or "").strip()
    if not pid or not projets_dc._valid_id(pid):
        return ""
    prop = _proprietaire()
    if not prop:
        return ""
    try:
        p = projets_db.obtenir(prop, pid)
    except Exception:
        return ""
    if not p:
        return ""
    for cle in ("client", "secteur", "perimetre", "filiere", "phase"):
        if not str(data.get(cle) or "").strip() and str(p.get(cle) or "").strip():
            data[cle] = p[cle]
    lignes = []
    def _l(nom, v):
        v = str(v or "").strip()
        if v:
            lignes.append("- %s : %s" % (nom, v[:240]))
    _l("Nom du projet", p.get("nom"))
    _l("Client", p.get("client"))
    _l("Secteur", p.get("secteur"))
    _l("Périmètre", p.get("perimetre"))
    _l("Maîtrise d'ouvrage", p.get("maitrise_ouvrage"))
    _l("Filière", {"moe": "maîtrise d'œuvre (vocabulaire loi MOP)",
                   "indus": "ingénierie industrielle (FEED/EPC)"}
       .get(p.get("filiere"), p.get("filiere")))
    _l("Phase courante", p.get("phase"))
    _l("Note de cadrage", p.get("note"))
    if not lignes:
        return ""
    return ("\n\nContexte du projet ouvert — repris de son dossier, à refléter "
            "dans le document sans rien inventer au-delà :\n"
            + "\n".join(lignes) + "\n")


def _projet_du_compte(pid):
    """Rend l'identifiant de projet s'il appartient au compte connecté, sinon "".

    Le rattachement d'un livrable arrive dans le corps de la requête, donc du
    navigateur, donc de n'importe qui sait écrire une requête. Le passer tel
    quel au magasin classerait un document dans le dossier d'un tiers — et une
    fois classé, il se lit dans son historique et part dans sa sauvegarde. On
    ne renvoie pas d'erreur pour autant : le document vient d'être payé en
    jetons d'API, le perdre pour un identifiant douteux serait pire que de le
    rendre non rattaché.
    """
    pid = (pid or "").strip()
    if not projets_dc._valid_id(pid):
        return ""
    prop = _proprietaire()
    if not prop:
        return ""
    try:
        return pid if projets_db.obtenir(prop, pid) else ""
    except Exception:
        return ""


@app.route("/api/datacenter/projets", methods=["GET", "POST"])
@login_required
def api_projets():
    """Liste les projets du compte, ou en crée un."""
    prop = _proprietaire()
    if not prop:
        return jsonify(ok=False, error="non_identifie"), 401
    if request.method == "GET":
        arch = request.args.get("archives") == "1"
        return jsonify(ok=True, projets=projets_db.lister(prop, arch),
                       referentiel=projets_dc.referentiel())
    data = request.get_json(silent=True) or {}
    try:
        p = projets_db.creer(prop, data)
    except projets_dc.ProjetError as exc:
        return jsonify(ok=False, error=exc.code, message=exc.detail), exc.status
    audit.journaliser("projet.creation", cible=p["id"][:32], detail=p["nom"][:120])
    return jsonify(ok=True, projet=p)


@app.route("/api/datacenter/projets/<pid>", methods=["GET", "PATCH", "DELETE"])
@login_required
def api_projet(pid):
    """Un projet et son historique — ou sa mise à jour, ou sa suppression."""
    prop = _proprietaire()
    if not prop or not projets_dc._valid_id(pid):
        return jsonify(ok=False, error="projet_invalide"), 400
    if request.method == "DELETE":
        # Le projet part ; ses livrables RESTENT. Supprimer un dossier de
        # projet effacerait des documents que le client a peut-être remis à un
        # tiers — on ne détruit pas ce qu'on a produit pour quelqu'un.
        if not projets_db.supprimer(prop, pid):
            return jsonify(ok=False, error="introuvable"), 404
        audit.journaliser("projet.suppression", cible=pid[:32])
        return jsonify(ok=True, livrables_conserves=True)
    if request.method == "PATCH":
        data = request.get_json(silent=True) or {}
        try:
            p = projets_db.modifier(prop, pid, data)
        except projets_dc.ProjetError as exc:
            return jsonify(ok=False, error=exc.code, message=exc.detail), exc.status
        if not p:
            return jsonify(ok=False, error="introuvable"), 404
        return jsonify(ok=True, projet=p)
    p = projets_db.obtenir(prop, pid)
    if not p:
        return jsonify(ok=False, error="introuvable"), 404
    return jsonify(ok=True, projet=p, historique=_historique_projet(pid))


def _horodatage():
    """L'instant, en ISO 8601 UTC. Écrit ici plutôt qu'importé de datetime dans
    la route : ce module ne l'importe pas, et une route qui plante au premier
    appel sur un import manquant est un défaut qu'aucun test de syntaxe ne
    voit."""
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _nom_fichier(nom):
    """Un nom de fichier sûr, tiré du nom du projet."""
    import re as _re
    return _re.sub(r"[^A-Za-z0-9_-]+", "-", nom or "")[:40].strip("-") or "sans-nom"


def _historique_projet(pid):
    """Les livrables du projet, GROUPÉS PAR PHASE et datés.

    Groupés ici et non dans la page : le regroupement est la seule chose qui
    rend cet historique lisible — une liste plate de quarante documents ne dit
    pas où en est le dossier. Et il se calcule à partir du même registre de
    phases que la frise, donc l'ordre est celui du projet, pas l'ordre
    alphabétique.
    """
    tous = [x for x in livrables_hist.list() if x.get("projet_id") == pid]
    rang = {p["code"]: p["rang"] for p in ingenierie_dc.PHASES}
    noms = {p["code"]: p["nom"] for p in ingenierie_dc.PHASES}
    par_phase = {}
    for x in tous:
        par_phase.setdefault(x.get("phase") or "—", []).append(x)
    groupes = []
    for code in sorted(par_phase, key=lambda c: (rang.get(c, 999), c)):
        items = sorted(par_phase[code], key=lambda r: -(r.get("created_at") or 0))
        groupes.append({
            "phase": code, "phase_nom": noms.get(code, "Hors phase"),
            "n": len(items),
            "dernier": items[0].get("created_at") if items else None,
            "livrables": items,
        })
    # L'ordre du vocabulaire est servi À PART du vocabulaire : une fois
    # sérialisé, un dictionnaire est trié par clé, et « obsolète » se
    # retrouverait entre « brouillon » et « relu ».
    return {"total": len(tous), "phases": groupes,
            "etats": projets_dc.ETATS_LIVRABLE,
            "etats_ordre": projets_dc._ordre(projets_dc.ETATS_LIVRABLE)}


@app.route("/api/datacenter/projets/<pid>/sauvegarde", methods=["GET"])
@login_required
def api_projet_sauvegarde(pid):
    """La sauvegarde d'un projet : le dossier ET tous ses livrables, en un fichier.

    Le contenu COMPLET des livrables, pas seulement leurs intitulés : une
    sauvegarde qui ne garderait que la liste ne permettrait pas de reconstituer
    le dossier, ce qui est précisément ce qu'on attend d'elle. Servie en
    téléchargement, jamais affichée — un dossier de projet n'a pas à transiter
    par le presse-papier.
    """
    prop = _proprietaire()
    if not prop or not projets_dc._valid_id(pid):
        return jsonify(ok=False, error="projet_invalide"), 400
    p = projets_db.obtenir(prop, pid)
    if not p:
        return jsonify(ok=False, error="introuvable"), 404
    complets = []
    for m in livrables_hist.list():
        if m.get("projet_id") != pid:
            continue
        d = livrables_hist.get(m["id"])
        if d:
            complets.append(d)
    charge = {
        "format": "conseilprev.projet-dc.v1",
        "exporte_le": _horodatage(),
        "moteur": {"ingenierie_dc": ingenierie_dc.VERSION,
                   "datacenter": datacenter.VERSION},
        "projet": p,
        "livrables": complets,
    }
    audit.journaliser("projet.sauvegarde", cible=pid[:32],
                      detail="%d livrable(s)" % len(complets))
    corps = json.dumps(charge, ensure_ascii=False, indent=1).encode("utf-8")
    nom = "projet-%s-%s.json" % (_nom_fichier(p["nom"]), _horodatage()[:10])
    resp = Response(corps, mimetype="application/json; charset=utf-8")
    resp.headers["Content-Disposition"] = 'attachment; filename="%s"' % nom
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Cache-Control"] = "private, no-store"
    return resp


@app.route("/api/datacenter/projets/<pid>/plan", methods=["POST"])
@login_required
def api_projet_plan(pid):
    """Le registre d'une phase CONFRONTÉ à ce que le projet a déjà produit.

    Le registre seul dit ce qu'il FAUT remettre ; l'historique dit ce qui a été
    ÉCRIT. Les lire côte à côte, sur deux écrans, c'est le travail que personne
    ne fait — et c'est pourquoi un dossier part avec une pièce obligatoire
    manquante que tout le monde croyait faite.

    Rend donc, pièce par pièce : son caractère, si elle est rédigée, dans quel
    état, et ce que le client ou les collègues en ont dit. Puis la SUITE : la
    prochaine pièce à traiter et la prochaine phase, pour que le dossier
    avance sans qu'on ait à chercher par où continuer.
    """
    prop = _proprietaire()
    if not prop or not projets_dc._valid_id(pid):
        return jsonify(ok=False, error="projet_invalide"), 400
    projet = projets_db.obtenir(prop, pid)
    if not projet:
        return jsonify(ok=False, error="introuvable"), 404
    data = request.get_json(silent=True) or {}
    phase = str(data.get("phase") or "").strip().upper()[:12]
    profil = _profil_datacenter(data)
    try:
        d = ingenierie_dc.dossier(profil, phase, data)
    except Exception:
        app.logger.exception("plan de phase")
        return jsonify(ok=False, error="calcul"), 500
    if not d.get("connu"):
        return jsonify(ok=False, error="phase_inconnue"), 404
    if not d.get("disponible"):
        return jsonify(ok=True, disponible=False, motif=d.get("motif"))

    # Ce qui existe déjà, indexé par code de pièce. On garde le PLUS RÉCENT :
    # une pièce reprise à un nouvel indice ne doit pas afficher l'état de son
    # brouillon d'origine.
    produits = {}
    for m in livrables_hist.list():
        if m.get("projet_id") != pid or not m.get("piece"):
            continue
        c = m["piece"]
        if c not in produits or (m.get("created_at") or 0) > (produits[c].get("created_at") or 0):
            produits[c] = m

    pieces, faits, restants = [], [], []
    for pc in d["pieces"]:
        q = dict(pc)
        m = produits.get(pc["code"])
        if m:
            v = projets_dc.synthese_visas(m.get("visas"))
            q["livrable"] = {
                "id": m["id"], "created_at": m.get("created_at"),
                "etat": m.get("etat") or "brouillon", "label": m.get("label"),
                "visa": v,
            }
            q["fait"] = True
            faits.append(q)
        else:
            q["livrable"] = None
            q["fait"] = False
            restants.append(q)
        pieces.append(q)

    # La suite du parcours. Calculée, pas devinée : la prochaine pièce est la
    # plus importante qui reste, et la prochaine phase celle qui suit dans la
    # séquence de la MÊME filière — pas la suivante par ordre alphabétique.
    suite = {"piece": None, "phase": None, "fin": False, "bloquantes": []}
    bloquantes = [x for x in restants if x["caractere"] == "obligatoire"]
    suite["bloquantes"] = [x["code"] for x in bloquantes]
    if restants:
        p0 = restants[0]
        suite["piece"] = {"code": p0["code"], "titre": p0["titre"],
                          "caractere": p0["caractere"],
                          "caractere_nom": p0["caractere_nom"]}
    seq = [x for x in ingenierie_dc.PHASES if x["filiere"] == d["filiere"]]
    seq.sort(key=lambda x: x["rang"])
    rangs = [x["code"] for x in seq]
    if phase in rangs:
        i = rangs.index(phase)
        if i + 1 < len(rangs):
            nxt = seq[i + 1]
            suite["phase"] = {"code": nxt["code"], "nom": nxt["nom"],
                              "objet": nxt["objet"]}
        else:
            # Dernière phase de la filière : le dire, plutôt que de laisser une
            # flèche pointer dans le vide.
            suite["fin"] = True
            suite["fin_texte"] = ("Dernière phase de la filière %s. Le dossier "
                                  "est complet quand ses pièces le sont."
                                  % d["filiere_nom"])
    return jsonify(ok=True, disponible=True, phase=phase,
                   phase_nom=d["nom"], filiere=d["filiere"],
                   pieces=pieces, suite=suite,
                   avancement={
                       "total": len(pieces), "faits": len(faits),
                       "restants": len(restants),
                       "obligatoires": sum(1 for x in pieces
                                           if x["caractere"] == "obligatoire"),
                       "obligatoires_restants": len(bloquantes),
                       "valides_client": sum(
                           1 for x in faits
                           if (x["livrable"]["visa"] or {}).get("etat") == "valide_client"),
                       "rejetes": sum(
                           1 for x in faits
                           if str((x["livrable"]["visa"] or {}).get("etat", "")).startswith("rejete")),
                   },
                   caracteres=ingenierie_dc.CARACTERES,
                   etats_visa=projets_dc.ETATS_VISA,
                   etats=projets_dc.ETATS_LIVRABLE,
                   etats_ordre=projets_dc._ordre(projets_dc.ETATS_LIVRABLE))


@app.route("/api/datacenter/projets/<pid>/livrable/<lid>/visa", methods=["POST"])
@login_required
def api_projet_visa(pid, lid):
    """Enregistre un avis : validé ou rejeté, par le client ou par un collègue.

    L'avis s'AJOUTE, il ne remplace pas. Un document rejeté puis corrigé garde
    la trace du refus et du motif ; l'écraser ferait disparaître la raison pour
    laquelle la pièce a été reprise, qui est précisément ce qu'on cherche six
    mois plus tard.

    Un rejet SANS MOTIF est refusé. « Rejeté » seul fait recommencer à
    l'identique — c'est le pire des retours, celui qui coûte deux fois.
    """
    prop = _proprietaire()
    if not prop or not projets_dc._valid_id(pid) or not _rag_hex(lid):
        return jsonify(ok=False, error="reference_invalide"), 400
    if not projets_db.obtenir(prop, pid):
        return jsonify(ok=False, error="introuvable"), 404
    rec = livrables_hist.get(lid)
    if not rec or rec.get("projet_id") != pid:
        return jsonify(ok=False, error="introuvable"), 404
    data = request.get_json(silent=True) or {}
    role = (data.get("role") or "").strip()
    decision = (data.get("decision") or "").strip()
    motif = (data.get("motif") or "").strip()[:800]
    if role not in projets_dc.ROLES_VISA:
        return jsonify(ok=False, error="role_inconnu",
                       message="Rôle inconnu."), 400
    if decision not in projets_dc.DECISIONS_VISA:
        return jsonify(ok=False, error="decision_inconnue",
                       message="Décision inconnue."), 400
    if decision == "rejete" and len(motif) < 5:
        return jsonify(ok=False, error="motif_manquant",
                       message="Un rejet doit porter son motif : sans lui, la "
                               "pièce est reprise à l'identique."), 400
    visa = {"par": prop, "role": role, "decision": decision, "motif": motif,
            "le": int(time.time() * 1000)}
    visas = livrables_hist.viser(lid, visa)
    if visas is None:
        return jsonify(ok=False, error="introuvable"), 404
    projets_db.toucher(pid)
    audit.journaliser("projet.visa", cible="%s/%s" % (pid[:8], lid[:8]),
                      detail="%s %s" % (role, decision))
    return jsonify(ok=True, visa=visa,
                   synthese=projets_dc.synthese_visas(visas))


@app.route("/api/datacenter/projets/<pid>/collaborateurs",
           methods=["GET", "POST", "DELETE"])
@login_required
def api_projet_collaborateurs(pid):
    """Inviter un collègue sur le projet, ou l'en retirer.

    SEUL LE PROPRIÉTAIRE INVITE, et le magasin le fait respecter — un collègue
    qui pourrait s'ajouter des collègues ferait du partage une porte qui
    s'élargit toute seule.

    L'invitation ne crée aucun compte et n'accorde rien par elle-même : l'accès
    se prouve par une session ouverte avec cette adresse. Une adresse inscrite
    ici sans compte correspondant ne donne donc rien, ce qui est le
    comportement voulu.
    """
    prop = _proprietaire()
    if not prop or not projets_dc._valid_id(pid):
        return jsonify(ok=False, error="projet_invalide"), 400
    projet = projets_db.obtenir(prop, pid)
    if not projet:
        return jsonify(ok=False, error="introuvable"), 404
    if request.method == "GET":
        return jsonify(ok=True, collaborateurs=projet.get("collaborateurs") or [],
                       proprietaire=projet.get("proprietaire"),
                       je_suis_proprietaire=projet.get("proprietaire") == prop,
                       max=projets_dc.MAX_COLLABORATEURS)
    if projet.get("proprietaire") != prop:
        return jsonify(ok=False, error="non_proprietaire",
                       message="Seul le propriétaire du projet invite ou "
                               "retire un collègue."), 403
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()[:200]
    liste = list(projet.get("collaborateurs") or [])
    if request.method == "DELETE":
        liste = [x for x in liste if x != email]
    else:
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            return jsonify(ok=False, error="email_invalide",
                           message="Adresse électronique invalide."), 400
        if email == prop:
            return jsonify(ok=False, error="deja_proprietaire",
                           message="Vous êtes déjà propriétaire de ce projet."), 400
        if email in liste:
            return jsonify(ok=False, error="deja_invite",
                           message="Ce collègue est déjà invité."), 400
        if len(liste) >= projets_dc.MAX_COLLABORATEURS:
            return jsonify(ok=False, error="trop_de_collaborateurs",
                           message="Ce projet a atteint %d collègues."
                                   % projets_dc.MAX_COLLABORATEURS), 409
        liste.append(email)
    p = projets_db.modifier(prop, pid, {"collaborateurs": liste})
    if not p:
        return jsonify(ok=False, error="introuvable"), 404
    lien = request.url_root.rstrip("/") + "/ingenierie-datacenter"
    envoye = False
    if request.method == "POST":
        envoye = _mail_projet(
            email, "Invitation sur le projet « %s »" % p["nom"],
            "<p><b>%s</b> vous invite sur le projet <b>%s</b>.</p>"
            "<p>Connectez-vous avec cette adresse pour retrouver le dossier, "
            "son historique par phase et les pièces à produire.</p>"
            "<p><a href=\"%s\">Ouvrir le projet</a></p>"
            % (_echappe(prop), _echappe(p["nom"]), lien))
    audit.journaliser("projet.collaborateur", cible=pid[:32],
                      detail="%s %s" % (request.method.lower(), email[:60]))
    return jsonify(ok=True, collaborateurs=p.get("collaborateurs") or [],
                   lien=lien, courriel_envoye=envoye,
                   courriel_configure=bool(os.environ.get("BREVO_API_KEY")))


@app.route("/api/datacenter/projets/<pid>/envoyer", methods=["POST"])
@login_required
def api_projet_envoyer(pid):
    """Signale une pièce, ou tout un dossier de phase, à un collègue du projet.

    L'envoi ne transporte AUCUN document : il pointe le projet. Une pièce
    d'ingénierie part en pièce jointe et se retrouve six mois plus tard dans
    une boîte, à un indice périmé, pendant que le dossier a bougé. Le lien
    ramène à la version courante — c'est la seule qui vaille.

    Le destinataire doit être invité sur le projet. Prévenir quelqu'un qui ne
    peut pas ouvrir le dossier serait une politesse inutile.
    """
    prop = _proprietaire()
    if not prop or not projets_dc._valid_id(pid):
        return jsonify(ok=False, error="projet_invalide"), 400
    projet = projets_db.obtenir(prop, pid)
    if not projet:
        return jsonify(ok=False, error="introuvable"), 404
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()[:200]
    autorises = set(projet.get("collaborateurs") or []) | {projet.get("proprietaire")}
    if email not in autorises:
        return jsonify(ok=False, error="non_invite",
                       message="Ce collègue n'est pas invité sur le projet. "
                               "Invitez-le d'abord : sans accès, il recevrait "
                               "un lien qu'il ne peut pas ouvrir."), 400
    phase = str(data.get("phase") or "").strip().upper()[:12]
    piece = str(data.get("piece") or "").strip().upper()[:24]
    mot = (data.get("message") or "").strip()[:800]
    lien = request.url_root.rstrip("/") + "/ingenierie-datacenter"
    if phase:
        lien += "#phase=" + phase + ("&piece=" + piece if piece else "")
    quoi = ("la pièce <b>%s</b> de la phase <b>%s</b>" % (_echappe(piece), _echappe(phase))
            if piece else
            ("le dossier de la phase <b>%s</b>" % _echappe(phase) if phase
             else "le dossier"))
    envoye = _mail_projet(
        email, "Projet « %s » — à relire" % projet["nom"],
        "<p><b>%s</b> vous signale %s du projet <b>%s</b>.</p>"
        "%s<p><a href=\"%s\">Ouvrir</a></p>"
        % (_echappe(prop), quoi, _echappe(projet["nom"]),
           ("<p>%s</p>" % _echappe(mot)) if mot else "", lien))
    audit.journaliser("projet.envoi", cible=pid[:32], detail=email[:60])
    return jsonify(ok=True, courriel_envoye=envoye, lien=lien,
                   courriel_configure=bool(os.environ.get("BREVO_API_KEY")))


@app.route("/api/datacenter/projets/<pid>/dossier.zip", methods=["GET"])
@login_required
def api_projet_zip(pid):
    """Tout le dossier en une archive : un fichier Word par livrable.

    Le format Word plutôt que le Markdown de la sauvegarde : celle-ci sert à
    RECHARGER le projet, l'archive sert à le LIRE et à le transmettre. Deux
    besoins, deux formats — servir du Markdown à qui veut relire un CCTP le
    ferait convertir à la main.

    Le paramètre `phase` restreint à une phase. Sans lui, tout le projet.
    """
    prop = _proprietaire()
    if not prop or not projets_dc._valid_id(pid):
        return jsonify(ok=False, error="projet_invalide"), 400
    projet = projets_db.obtenir(prop, pid)
    if not projet:
        return jsonify(ok=False, error="introuvable"), 404
    phase = (request.args.get("phase") or "").strip().upper()[:12]
    metas = [m for m in livrables_hist.list()
             if m.get("projet_id") == pid and (not phase or m.get("phase") == phase)]
    if not metas:
        return jsonify(ok=False, error="vide",
                       message="Aucun livrable à archiver pour ce périmètre."), 404
    tampon = io.BytesIO()
    noms = set()
    ajoutes, echecs = 0, []
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        for m in metas:
            rec = livrables_hist.get(m["id"])
            if not rec or not (rec.get("markdown") or "").strip():
                continue
            base = "%s/%s-%s" % (rec.get("phase") or "hors-phase",
                                 rec.get("piece") or "piece",
                                 _nom_fichier(rec.get("label") or "livrable"))
            # Deux pièces peuvent porter le même intitulé à des indices
            # différents ; sans ce suffixe l'une écraserait l'autre dans
            # l'archive, silencieusement.
            nom = base
            n = 2
            while nom + ".docx" in noms:
                nom = "%s-%d" % (base, n)
                n += 1
            noms.add(nom + ".docx")
            meta = {"type": rec.get("type"), "label": rec.get("label"),
                    "client": rec.get("client"), "secteur": rec.get("secteur"),
                    # Le code du rédacteur vient du MAGASIN, écrit au moment de
                    # la génération : c'est la source sûre.
                    "ia": _redige_par_modele(rec.get("model")),
                    "referentiel": "Moteur d'ingénierie CONSEILPREV v" + ingenierie_dc.VERSION,
                    "perimetre": rec.get("perimetre"), "model": rec.get("model"),
                    "date": time.strftime("%d/%m/%Y"),
                    "sources": [x for x in (rec.get("sources") or [])
                                if isinstance(x, dict)][:40]}
            try:
                z.writestr(nom + ".docx",
                           livrables_export.build_docx(rec["markdown"], meta))
                ajoutes += 1
            except Exception:
                # Une mise en page qui échoue ne doit pas emporter l'archive
                # entière : on verse le texte source et on le DIT dans le
                # bordereau, plutôt que de rendre un ZIP amputé sans un mot.
                z.writestr(nom + ".md", rec["markdown"].encode("utf-8"))
                echecs.append(rec.get("label") or rec["id"])
        z.writestr("BORDEREAU.txt", _bordereau(projet, metas, phase, echecs)
                   .encode("utf-8"))
    if not ajoutes and not echecs:
        return jsonify(ok=False, error="vide"), 404
    corps = tampon.getvalue()
    nom_zip = "projet-%s%s-%s.zip" % (_nom_fichier(projet["nom"]),
                                      ("-" + phase) if phase else "",
                                      _horodatage()[:10])
    audit.journaliser("projet.archive", cible=pid[:32],
                      detail="%d livrable(s)%s" % (ajoutes,
                                                   " · " + phase if phase else ""))
    resp = Response(corps, mimetype="application/zip")
    resp.headers["Content-Disposition"] = 'attachment; filename="%s"' % nom_zip
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Cache-Control"] = "private, no-store"
    return resp


def _bordereau(projet, metas, phase, echecs):
    """Le bordereau de l'archive : ce qu'elle contient, et ce qui a résisté.

    Une archive sans bordereau oblige à ouvrir chaque fichier pour savoir ce
    qu'on a reçu — et surtout ne dit pas ce qui MANQUE."""
    lignes = ["DOSSIER DE PROJET — %s" % projet["nom"],
              "Exporté le %s" % _horodatage(),
              "Périmètre : %s" % (phase or "toutes phases"),
              "%d livrable(s)" % len(metas), ""]
    for m in sorted(metas, key=lambda x: (x.get("phase") or "", -(x.get("created_at") or 0))):
        v = projets_dc.synthese_visas(m.get("visas"))
        lignes.append("- [%s] %s — %s · %s"
                      % (m.get("phase") or "—", m.get("piece") or "—",
                         m.get("label") or "", v["nom"]))
    if echecs:
        lignes += ["", "MISE EN PAGE ÉCHOUÉE — versés en texte source (.md) :"]
        lignes += ["  - %s" % x for x in echecs]
    return "\n".join(lignes) + "\n"


def _echappe(v):
    """Échappement HTML pour le corps des courriels. Un nom de projet contenant
    une balise ne doit pas se retrouver interprété chez le destinataire."""
    return (str(v or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _mail_projet(email, sujet, html):
    """Envoie un courriel de projet, et dit honnêtement s'il est parti.

    Sans clé d'API configurée, rien n'est envoyé et la réponse le dit : la page
    affiche alors le lien à transmettre soi-même. Annoncer « invitation
    envoyée » sur un serveur qui n'a pas de quoi l'envoyer serait la pire des
    confirmations — celle qu'on ne vérifie jamais.
    """
    try:
        import auth as _auth
        return bool(_auth.send_email(email, email, sujet, _auth._shell(sujet, html)))
    except Exception:
        app.logger.warning("courriel de projet non envoyé : %s", email[:60])
        return False


@app.route("/api/datacenter/projets/<pid>/livrable/<lid>", methods=["PATCH"])
@login_required
def api_projet_livrable_etat(pid, lid):
    """Fait passer un livrable de brouillon à relu, visé ou obsolète.

    Sans ce geste, l'état affiché dans l'historique serait une décoration : tout
    resterait éternellement « brouillon », et un dossier entièrement visé se
    lirait comme un dossier entièrement à relire. Le vocabulaire est fermé —
    un état libre rendrait tout regroupement inutile dès la deuxième saisie.
    """
    prop = _proprietaire()
    if not prop or not projets_dc._valid_id(pid) or not _rag_hex(lid):
        return jsonify(ok=False, error="reference_invalide"), 400
    etat = (request.get_json(silent=True) or {}).get("etat") or ""
    if etat not in projets_dc.ETATS_LIVRABLE:
        return jsonify(ok=False, error="etat_inconnu",
                       message="État de livrable inconnu."), 400
    if not projets_db.obtenir(prop, pid):
        return jsonify(ok=False, error="introuvable"), 404
    rec = livrables_hist.get(lid)
    if not rec or rec.get("projet_id") != pid:
        return jsonify(ok=False, error="introuvable"), 404
    if not livrables_hist.changer_etat(lid, etat):
        return jsonify(ok=False, error="introuvable"), 404
    projets_db.toucher(pid)
    audit.journaliser("projet.livrable.etat", cible="%s/%s" % (pid[:8], lid[:8]),
                      detail=etat)
    return jsonify(ok=True, etat=etat, historique=_historique_projet(pid))


@app.route("/api/datacenter/projets/<pid>/livrable/<lid>.<fmt>", methods=["GET"])
@login_required
def api_projet_livrable(pid, lid, fmt):
    """Un livrable du projet, remis en Word ou en PDF à son PROPRIÉTAIRE.

    La reprise d'un document de l'historique existait déjà, mais derrière le
    verrou d'administration : celui qui a commandé le dossier ne pouvait pas
    récupérer ses propres pièces autrement qu'en réclamant l'export complet.
    Ici l'autorisation ne vient pas du rôle mais du RATTACHEMENT — le projet
    appartient au compte, et le livrable appartient au projet. Les deux liens
    sont vérifiés, dans cet ordre ; l'identifiant du livrable seul n'ouvre
    rien.
    """
    prop = _proprietaire()
    if not prop or not projets_dc._valid_id(pid) or not _rag_hex(lid):
        return jsonify(ok=False, error="reference_invalide"), 400
    if fmt not in ("docx", "pdf", "md"):
        return jsonify(ok=False, error="format_inconnu"), 400
    if not projets_db.obtenir(prop, pid):
        return jsonify(ok=False, error="introuvable"), 404
    rec = livrables_hist.get(lid)
    # Le second lien : un livrable d'un AUTRE projet répond 404, pas 403 — on
    # ne confirme pas l'existence d'un document qu'on n'a pas à connaître.
    if not rec or rec.get("projet_id") != pid:
        return jsonify(ok=False, error="introuvable"), 404
    md = (rec.get("markdown") or "").strip()
    if not md:
        return jsonify(ok=False, error="vide"), 404
    base = _nom_fichier(rec.get("label") or rec.get("type") or "livrable")
    if fmt == "md":
        resp = Response(md.encode("utf-8"), mimetype="text/markdown; charset=utf-8")
    else:
        meta = {"type": rec.get("type"), "label": rec.get("label") or rec.get("type"),
                "client": rec.get("client"), "secteur": rec.get("secteur"),
                "ia": _redige_par_modele(rec.get("model")),
                "referentiel": "Moteur d'ingénierie CONSEILPREV v" + ingenierie_dc.VERSION,
                "perimetre": rec.get("perimetre"), "model": rec.get("model"),
                "date": time.strftime("%d/%m/%Y"),
                "sources": [s for s in (rec.get("sources") or [])
                            if isinstance(s, dict)][:40]}
        try:
            if fmt == "pdf":
                blob, mt = livrables_export.build_pdf(md, meta), "application/pdf"
            else:
                blob = livrables_export.build_docx(md, meta)
                mt = ("application/vnd.openxmlformats-officedocument"
                      ".wordprocessingml.document")
        except Exception:
            return jsonify(ok=False, error="export_echec",
                           message="La mise en page a échoué."), 500
        resp = Response(blob, mimetype=mt)
    audit.journaliser("projet.livrable", cible="%s/%s" % (pid[:8], lid[:8]),
                      detail=fmt)
    resp.headers["Content-Disposition"] = ('attachment; filename="%s.%s"'
                                           % (base, fmt))
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Cache-Control"] = "private, no-store"
    return resp


@app.route("/api/datacenter/projets/<pid>/documents.<fmt>", methods=["GET"])
@login_required
def api_projet_documents(pid, fmt):
    """La liste des documents du projet : le registre de ce qui est VISÉ.

    Elle ne se confond pas avec le dossier. Le dossier porte tout ce qui a été
    produit, brouillons compris — c'est un plan de travail. La liste ne porte
    que ce qui a été visé : elle engage. Y verser un brouillon ferait figurer
    au registre contractuel un document que personne n'a relu, et c'est la
    faute qui coûte le plus cher, parce qu'on ne la découvre qu'au moment où
    quelqu'un s'en prévaut.

    404 tant qu'aucun document n'est visé : une liste vide n'est pas un
    registre, c'est un document qui ferait croire qu'il n'y a rien à attendre.
    """
    prop = _proprietaire()
    if not prop or not projets_dc._valid_id(pid):
        return jsonify(ok=False, error="reference_invalide"), 400
    if fmt not in ("docx", "pdf", "md", "json"):
        return jsonify(ok=False, error="format_inconnu"), 400
    projet = projets_db.obtenir(prop, pid)
    if not projet:
        return jsonify(ok=False, error="introuvable"), 404
    liv = [x for x in livrables_hist.list() if x.get("projet_id") == pid]
    md = ingenierie_dc.liste_documents(projet, liv, projets_dc.ETATS_LIVRABLE)
    if not md:
        return jsonify(ok=False, error="aucun_vise",
                       message="Aucun document de ce projet n'est visé. La "
                               "liste s'ouvre au premier visa."), 404
    vises = len([x for x in liv
                 if (x.get("etat") or "") in ingenierie_dc.ETATS_ENGAGEANTS])
    if fmt == "json":
        return jsonify(ok=True, document=md, vises=vises, total=len(liv),
                       projet=projet.get("nom") or "")
    base = _nom_fichier("liste-documents-%s" % (projet.get("nom") or pid[:8]))
    if fmt == "md":
        resp = Response(md.encode("utf-8"),
                        mimetype="text/markdown; charset=utf-8")
    else:
        meta = {"type": "LDD", "label": "Liste des documents du projet",
                "numero": "LDD-%s" % (projet.get("nom") or "")[:24],
                "client": projet.get("client") or "",
                "perimetre": projet.get("nom") or "",
                "date": time.strftime("%d/%m/%Y"),
                # « Moteur d'ingénierie » n'est PAS un modèle de langage : le
                # registre est une liste tirée du magasin.
                "ia": False,
                "referentiel": "Moteur d'ingénierie CONSEILPREV v" + ingenierie_dc.VERSION,
                "model": "Moteur d'ingénierie CONSEILPREV %s"
                         % ingenierie_dc.VERSION,
                "statut": "Registre des documents visés",
                "sources": []}
        try:
            if fmt == "pdf":
                blob, mt = livrables_export.build_pdf(md, meta), "application/pdf"
            else:
                blob = livrables_export.build_docx(md, meta)
                mt = ("application/vnd.openxmlformats-officedocument"
                      ".wordprocessingml.document")
        except Exception:
            return jsonify(ok=False, error="export_echec",
                           message="La mise en page a échoué."), 500
        resp = Response(blob, mimetype=mt)
    audit.journaliser("projet.documents", cible=pid[:8],
                      detail="%s · %d visé(s)" % (fmt, vises))
    resp.headers["Content-Disposition"] = ('attachment; filename="%s.%s"'
                                           % (base, fmt))
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Cache-Control"] = "private, no-store"
    return resp


@app.route("/api/datacenter/redaction/etat", methods=["GET"])
@login_required
def api_redaction_etat():
    """Ce que vaut la chaîne de RÉDACTION en ce moment.

    Le même principe que pour le dépôt de documents, appliqué à ce qui écrit :
    celui qui va lancer une rédaction a le droit de savoir, AVANT de cliquer,
    CE QUI VA SORTIR. Pas seulement « ça marche » ou « ça ne marche pas » —
    les deux sources se complètent et se remplacent, et le résultat n'est pas
    le même selon celles qui répondent.

    QUATRE MODES, et aucun ne rend la main vide :

      · modèle + base   — le modèle rédige, ancré sur les documents retrouvés ;
      · modèle seul     — il rédige à partir du calcul, sans source citée ;
      · base seule      — la trame est assemblée, extraits reproduits tels quels ;
      · moteur seul     — plan et grandeurs assemblés : un point de départ.

    Annoncer « INDISPONIBLE » quand aucun modèle n'est configuré serait
    désormais faux : la pièce sort quand même, et c'est ce qu'elle EST qui
    change. Une trame assemblée présentée comme une pièce rédigée serait la
    seule vraie faute possible ici — d'où le mode dit d'avance, et redit en
    tête du document.
    """
    dispo = assistant.available()
    prets = [k for k, v in dispo.items() if v]
    admin = _is_admin_request()
    total = None
    try:
        s = rag.stats()
        total = s.get("documents", 0)
        # CE QUE CE LECTEUR-LÀ peut atteindre, et non ce que contient la base.
        # Annoncer quatre cent cinquante-neuf documents à qui n'en verra que
        # les publics promet des sources qui ne viendront pas, et fait
        # découvrir un livrable sans références une fois écrit.
        docs = total if admin else s.get("publics", 0)
    except Exception:
        docs = None
    # `docs is None` — la base est injoignable : on la compte pour absente, et
    # la consigne ci-dessous le dit plutôt que de laisser croire à un choix.
    mode = ingenierie_dc.mode_redaction(bool(prets), bool(docs))
    m = ingenierie_dc.MODES_REDACTION[mode]
    if prets:
        resume = ("La rédaction est disponible : %s. Chaque pièce est écrite à "
                  "partir du calcul et de la base de connaissance, puis "
                  "enregistrée dans le dossier du projet."
                  % " et ".join(prets))
    else:
        resume = ("Aucun modèle de langage n'est configuré sur ce serveur. La "
                  "rédaction ne s'arrête pas pour autant : la pièce est "
                  "ASSEMBLÉE — plan du registre, grandeurs du moteur, entrées "
                  "manquantes%s — puis enregistrée dans le dossier. Elle est "
                  "exacte et complète quant aux faits ; elle n'est pas rédigée."
                  % (", extraits de la base" if docs else ""))
    return jsonify(ok=True, etat={
        "modeles": dispo,
        "modeles_prets": prets,
        # `disponible` répond à « puis-je cliquer et obtenir une pièce ? ».
        # La réponse est oui dans les quatre modes ; ce qui varie est le mode.
        # `modele_disponible` répond à « qui écrit ? » — c'est une autre
        # question, et les confondre est ce qui faisait annoncer une panne là
        # où il n'y avait qu'une configuration absente.
        "disponible": True,
        "modele_disponible": bool(prets),
        "mode": mode,
        "mode_nom": m["nom"],
        # Le mode annoncé ici est une PRÉVISION, faite sur ce que la base
        # contient. Celui du document est un CONSTAT, fait sur ce que la
        # recherche a réellement ramené pour SON sujet : une base peuplée qui
        # ne répond pas sur une pièce donnée fait retomber ce document-là sur
        # le moteur seul. Le dire ici évite que l'écart passe pour une panne.
        "mode_aide": m["aide"] + (
            " Sur une pièce dont le sujet ne trouve rien dans la base, ce "
            "document-là retombera sur le moteur seul, et le dira."
            if docs else ""),
        "documents_base": docs,
        # Le total, à côté de l'accessible : sans lui, un client verrait « 45
        # documents » sans savoir qu'il en existe quatre cents autres, et ne
        # penserait pas à demander qu'on lui en ouvre.
        "documents_total": total,
        "corpus": "complet" if admin else "public",
        "corpus_nom": ("Base entière — documents publics et internes" if admin
                       else "Documents publics de la base"),
        # Une base vide ne bloque pas la rédaction : le modèle écrit à partir
        # du calcul seul. Mais le document ne citera aucune source, et le dire
        # AVANT évite de découvrir un livrable sans références après coup.
        "base_vide": docs == 0,
        "resume": resume,
        "repli": _ASSISTANT_REPLI,
        "consignes": [
            "Le modèle n'invente aucun chiffre : les grandeurs viennent du "
            "moteur déterministe et lui sont interdites de recalcul.",
            ("Base de connaissance injoignable : la pièce se rédige quand "
             "même, sur le seul calcul, et ne citera aucune source."
             if docs is None else
             "Sans document dans la base de connaissance, la pièce reste "
             "rédigeable mais ne citera aucune source."),
            ("Sans modèle, la trame est assemblée sans reformulation : les "
             "extraits sont reproduits mot pour mot, avec leur source."
             if not prets else
             "Les deux sources se complètent : si la base ne répond pas, le "
             "modèle rédige seul ; s'il n'est pas configuré, la base sert "
             "seule."),
            "Une rédaction qui échoue n'enregistre rien : le dossier du projet "
            "reste dans l'état où il était.",
        ],
    })


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
    # L'analyse admet des images et des plans DWG ; le dépôt, lui, INDEXE le
    # document dans la base de connaissance, qui a besoin de texte. Annoncer la
    # liste de l'analyse revenait à inviter au dépôt d'un fichier refusé deux
    # étapes plus loin. On annonce ce qui franchit les DEUX portes.
    import rag_store as _rs
    e["extensions_admises"] = _rs.formats_deposables()
    e["extensions_analyse"] = sorted(antivirus.EXTENSIONS)
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
        return jsonify(ok=False, error=exc.code,
                       message=_motif_depot(exc.code,
                                            getattr(exc, "detail", ""))), exc.status
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

    Ouvert à tout compte connecté : consulter ce que la base contient ne
    consomme pas de jetons d'API et ne produit rien.

    SUR LE MÊME CORPUS QUE LA RÉDACTION, et c'est la moitié de l'affaire. Cet
    aperçu cherchait sur la base ENTIÈRE pendant que la rédaction d'un compte
    ordinaire se borne aux documents publics. Deux conséquences, chacune
    suffisante :

      · il nommait à un client des documents INTERNES — un intitulé dit déjà
        beaucoup (« Audit X — écarts majeurs », « Contrat Y — remise 14 % ») ;
      · il annonçait des sources que la pièce ne citerait jamais, alors que sa
        raison d'être est de ne pas pouvoir mentir sur ce qui sera mobilisé.
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
    public_only = not _is_admin_request()
    # Même ordre que la rédaction, famille prioritaire comprise. Un aperçu qui
    # classerait autrement annoncerait des sources dans un ordre que le
    # document ne suivrait pas — et son seul intérêt est d'être fidèle.
    famille, themes = _famille_prioritaire(
        "dc-piece-%s-%s" % (phase.lower(), code.lower()))
    try:
        hits = _hits_priorises(
            query, 8, public_only, themes,
            elargir=assistant.rerank(model, query,
                                     rag.search(query, k=24,
                                                public_only=public_only), 8))
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
                   corpus="public" if public_only else "complet",
                   famille_prioritaire=famille,
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
    # Générer puis effacer ne doit pas être un chemin sans trace : le journal
    # garde QUE le document a existé — jamais son contenu.
    audit.journaliser("livrable.suppression", cible=lid)
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
            # Le générateur retombe sur une trame assemblée quand aucun modèle
            # ne répond ; le code rendu à l'écran est renvoyé ici tel quel.
            "ia": _redige_par_modele(data.get("model")),
            "referentiel": "Base de connaissance CONSEILPREV",
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
#  Automatisations exposées : veille mondiale, ingestion documentaire, pack mission
# ============================================================================

@app.route("/api/paiement/etat")
def api_paiement_etat():
    """Le paiement est-il proposé, et à quel prix ? Aucune clé n'en sort.

    La page a besoin de le savoir AVANT d'afficher un bouton : un bouton qui
    mène à « paiement non configuré » vaut moins qu'un bouton absent.

    LE TARIF EST LU CHEZ STRIPE, jamais recopié dans une page — sinon le jour
    où il change, la page annonce un montant et la caisse en encaisse un autre.
    Il vaut `null` quand on n'a pas pu le lire, et la page n'affiche alors aucun
    montant : un prix qu'on ne peut pas prouver n'est pas un prix.
    """
    import paiement
    return jsonify(ok=True, configure=paiement.configure(),
                   tarif=paiement.tarif())


@app.route("/api/paiement/adresse-confirmee")
def api_paiement_adresse_confirmee():
    """L'adresse que CET appelant a confirmée, pour préremplir la caisse.

    POURQUOI UNE ROUTE À PART plutôt qu'un champ de plus dans `/etat` : cette
    réponse dépend de la session, l'autre non. Les mêler ferait d'une réponse
    publique et mise en cache une réponse personnelle — et un cache partagé
    servirait l'adresse d'un visiteur au suivant.

    ELLE NE RÉVÈLE RIEN : elle rend ce que l'appelant a lui-même prouvé en
    ouvrant le lien reçu dans sa boîte. Sans cela il devait retaper son adresse
    sur la page atteinte à la seconde même où il venait de cliquer dessus.
    """
    import auth as _auth
    rep = jsonify(ok=True, email=_auth.adresse_confirmee())
    # PAS DE MISE EN CACHE. Le préfixe /api/paiement/ n'est pas couvert par la
    # règle globale, qui ne vise que /api/admin/ et /api/auth/ : l'écrire ici
    # est le seul moyen d'être sûr.
    rep.headers["Cache-Control"] = "private, no-store"
    return rep


@app.route("/api/paiement/checkout", methods=["POST"])
def api_paiement_checkout():
    """Ouvre une caisse Stripe pour un compte confirmé mais pas encore ouvert.

    OUVERTE SANS SESSION, ET C'EST NÉCESSAIRE : un compte non approuvé ne peut
    pas se connecter (auth : 403). Exiger d'être connecté pour payer rendrait
    la caisse inatteignable par ceux-là mêmes à qui elle s'adresse.

    CE QU'ELLE NE FAIT PAS : ouvrir un accès. Elle ne fait qu'ouvrir une
    caisse. L'accès ne s'ouvre que sur la notification signée — un appel à
    cette adresse ne promeut personne.
    """
    import paiement
    if not paiement.configure():
        return jsonify(ok=False, error="paiement_non_configure",
                       message="Le paiement en ligne n'est pas activé sur ce "
                               "serveur."), 503
    email = ((request.get_json(silent=True) or {}).get("email") or "").strip().lower()
    ckey = "paiement:%s" % client_ip()
    if guard.blocked(ckey, limit=10, window=600):
        return jsonify(ok=False, error="rate_limited"), 429
    guard.fail(ckey)
    import auth as _auth
    # ON NE DIT PAS SI LE COMPTE EXISTE. Un message distinct pour « inconnu »,
    # « non confirmé » et « déjà ouvert » ferait de cette adresse un moyen de
    # savoir qui a un compte ici, sans en avoir un soi-même.
    if not _auth.payable(email):
        # LE FLOU EST JUSTE POUR UN INCONNU, ET SEULEMENT POUR LUI. Un message
        # distinct par cas ferait de cette adresse un moyen de savoir qui a un
        # compte ici. Mais celui qui a ouvert le lien reçu dans sa boîte a
        # PROUVÉ l'adresse : lui répondre en aveugle ne protège plus personne
        # et cache la seule chose utile. C'est ce qui s'est produit — un compte
        # déjà ouvert gratuitement s'est vu répondre « cette adresse ne peut
        # pas ouvrir de paiement », exact et illisible.
        if _auth.adresse_confirmee() == email:
            motif = _auth.motif_non_payable(email)
            if motif == _auth.MOTIF_DEJA_OUVERT:
                return jsonify(ok=False, error="acces_deja_ouvert",
                               message="Votre accès est déjà ouvert : il n'y a "
                                       "rien à payer. Connectez-vous avec votre "
                                       "adresse et votre mot de passe."), 400
            if motif == _auth.MOTIF_NON_CONFIRMEE:
                return jsonify(ok=False, error="adresse_non_confirmee",
                               message="Votre adresse n'est pas confirmée. "
                                       "Ouvrez le lien reçu par courriel, puis "
                                       "revenez régler."), 400
            if motif == _auth.MOTIF_INCONNUE:
                return jsonify(ok=False, error="compte_absent",
                               message="Aucun compte ne porte cette adresse. "
                                       "Créez-en un, puis confirmez l'adresse "
                                       "avant de régler."), 400
        return jsonify(ok=False, error="compte_non_eligible",
                       message="Cette adresse ne peut pas ouvrir de paiement. "
                               "Vérifiez d'avoir confirmé votre adresse, ou "
                               "que votre accès n'est pas déjà actif."), 400
    # ── LA RENONCIATION AU DROIT DE RÉTRACTATION, EXIGÉE ICI ──────────────
    # L'accès s'ouvre dès la confirmation du paiement. Un consommateur ne perd
    # son droit de rétractation que s'il a DEMANDÉ expressément cette exécution
    # immédiate et RECONNU expressément qu'il le perdrait (art. L221-25 et
    # L221-28, 13°). Une case cochée dans la page ne prouve rien : c'est le
    # serveur qui refuse d'ouvrir la caisse sans elle, et le journal qui en
    # garde la trace. Sans cette trace, la renonciation n'est pas opposable —
    # et une renonciation non opposable ne vaut pas mieux que pas de
    # renonciation.
    charge = request.get_json(silent=True) or {}
    # LA QUALITÉ SE DÉCLARE À LA VENTE, PAS À L'INSCRIPTION. Les conditions
    # réservent l'offre aux professionnels ; c'est le contrat qui doit en porter
    # la déclaration, et l'inscription n'est pas un contrat. Le chemin gratuit
    # par validation manuelle n'est pas une vente non plus : il ne demande rien
    # de tel, et les conditions ne le régissent pas.
    if charge.get("professionnel") is not True:
        return jsonify(ok=False, error="qualite_non_declaree",
                       message="L'accès est vendu aux professionnels : vous "
                               "devez déclarer commander pour les besoins de "
                               "votre activité."), 400
    if charge.get("cgv") is not True:
        return jsonify(ok=False, error="conditions_non_acceptees",
                       message="Vous devez accepter les conditions générales "
                               "de vente pour commander."), 400
    if charge.get("renonciation") is not True:
        return jsonify(ok=False, error="renonciation_absente",
                       message="Pour que l'accès s'ouvre dès le paiement, vous "
                               "devez demander son exécution immédiate et "
                               "reconnaître la perte du droit de rétractation "
                               "qui en découle."), 400
    # DEUX CONSENTEMENTS, DEUX TRACES. Les séparer à l'écran sans les séparer
    # au journal serait cosmétique : c'est la trace, et elle seule, qui rend
    # l'un ou l'autre opposable.
    audit.journaliser("paiement.qualite", cible=email,
                      detail="commande déclarée à titre professionnel")
    audit.journaliser("paiement.conditions", cible=email,
                      detail="conditions %s acceptées" % paiement.VERSION_CGV)
    audit.journaliser("paiement.renonciation", cible=email,
                      detail="exécution immédiate demandée · conditions %s"
                             % paiement.VERSION_CGV)
    url = paiement.session_paiement(email, _base_url())
    if not url:
        return jsonify(ok=False, error="caisse_indisponible",
                       message="Le paiement est momentanément indisponible."), 502
    return jsonify(ok=True, url=url)


@app.route("/api/stripe/webhook", methods=["POST"])
def api_stripe_webhook():
    """La notification de paiement — le SEUL chemin qui ouvre un accès.

    ON REND TOUJOURS 200, y compris quand on n'a rien fait. Stripe réémet une
    notification tant qu'elle n'est pas acquittée : rendre 500 sur une adresse
    inconnue déclencherait trois jours de réessais pour un cas qui ne
    s'arrangera pas tout seul. Ce qui ne peut pas être traité est TRACÉ — un
    paiement ne doit pas disparaître en silence.

    Les seuls refus sont 400 : charge non signée, ou signature invalide. Là,
    dire non est la réponse juste.
    """
    # UN PLAFOND, MÊME ICI — et il a fallu que la règle de surface d'attaque me
    # le rappelle. Ce point est ouvert et non authentifié par session : sans
    # plafond, n'importe qui peut le marteler, et chaque charge coûte une
    # vérification de signature.
    #
    # LARGE, ET CE N'EST PAS DE LA TIÉDEUR. Stripe peut envoyer une rafale —
    # rejeux, rattrapage après une panne — et toutes ses requêtes partagent
    # quelques adresses. Un plafond serré transformerait un rattrapage
    # légitime en paiements perdus. Un refus reste d'ailleurs récupérable :
    # Stripe réémet ce qui n'est pas acquitté, alors qu'un flot non borné, lui,
    # ne se rattrape pas.
    ckey = "stripe-webhook:%s" % client_ip()
    if guard.blocked(ckey, limit=240, window=60):
        return jsonify(ok=False, error="rate_limited"), 429
    guard.fail(ckey)
    import paiement
    ev = paiement.lire_evenement(request.get_data(),
                                 request.headers.get("Stripe-Signature", ""))
    if ev is None:
        return jsonify(ok=False, error="signature_invalide"), 400
    email = paiement.compte_a_ouvrir(ev)
    if not email:
        # Stripe émet des dizaines de sortes d'événements ; n'en retenir qu'une
        # est ce qui empêche une session simplement CRÉÉE d'ouvrir un accès.
        return jsonify(ok=True, traite=False)
    try:
        import auth as _auth
        # LES DÉTAILS VIENNENT DE L'ÉVÉNEMENT QU'ON VIENT DE VÉRIFIER, jamais
        # d'un second appel : la signature n'a été contrôlée que sur celui-ci.
        ouvert = _auth.ouvrir_par_paiement(email, _base_url(),
                                           commande=paiement.details_commande(ev))
    except Exception:
        app.logger.exception("ouverture par paiement")
        ouvert = False
    return jsonify(ok=True, traite=bool(ouvert))


@app.route("/api/veille")
def api_veille():
    """La veille (publique) : éléments récents, DÉJÀ CLASSÉS, et leurs facettes.

    POURQUOI LE CLASSEMENT SE FAIT ICI ET LE FILTRAGE LÀ-BAS. Le vocabulaire —
    thèmes, standards, secteurs — est celui de la maison, tenu dans
    `veille_facettes` qui l'adosse à `rag_store.THEMES`. Le recopier dans le
    script de la page en ferait un second vocabulaire, et c'est l'exemplaire
    qu'on oublie de corriger qui reste. Le filtrage, lui, reste dans la page :
    il doit être instantané, et six axes cumulables sur soixante éléments ne
    valent pas un aller-retour réseau.
    """
    limite = reglages.entier("VEILLE_PAGE", 120, mini=1, maxi=400)
    try:
        limite = max(1, min(int(request.args.get("limit") or limite), 400))
    except (TypeError, ValueError):
        pass
    items = veille_facettes.enrichir(automation.veille_list(limit=limite))
    domaine = (request.args.get("domaine") or "").strip()
    pays = (request.args.get("pays") or "").strip()
    if domaine:
        items = [i for i in items if i.get("domaine") == domaine]
    if pays:
        items = [i for i in items if (i.get("facettes") or {}).get("pays") == pays]
    return jsonify(ok=True, items=items, facettes=veille_facettes.facettes(items),
                   # DE QUOI DIRE LA VÉRITÉ QUAND LA LISTE EST VIDE, et rien de
                   # plus : un booléen et un horodatage. Les noms de sources et
                   # leurs erreurs restent dans l'espace d'administration.
                   collecte=automation.veille_collecte(),
                   # LA MENTION DE TRANSPARENCE DOIT DÉCRIRE LA RÉALITÉ. Elle
                   # ne s'affiche que si des résumés sont RÉELLEMENT produits :
                   # annoncer une génération par IA là où l'on recopie le
                   # chapeau du régulateur est une mention fausse, et une
                   # mention fausse vaut moins que pas de mention.
                   resume_ia=bool(automation.VEILLE_RESUME),
                   sources=veille_sources.referentiel())


@app.route("/api/admin/veille/sante")
@admin_required
def api_veille_sante():
    """Ce que chaque flux a réellement rapporté.

    Le catalogue a été écrit hors ligne : certaines adresses seront fausses. Un
    flux muet ne lève aucune erreur — il rend une liste vide, et la page affiche
    simplement moins de choses. Cette table est le seul endroit où cela se voit,
    et elle distingue « jamais joint » (adresse à corriger) de « devenu muet »
    (panne à attendre)."""
    return jsonify(ok=True, **veille_sources.etat())


@app.route("/api/admin/veille/refresh", methods=["POST"])
@admin_required
def api_veille_refresh():
    """Relance la collecte, ET rend la santé du passage qu'elle vient de faire.

    POURQUOI LA SANTÉ EST RENDUE ICI PLUTÔT QUE RELUE ENSUITE. L'état des flux
    vit en mémoire de PROCESSUS (`veille_sources._etats`), et le service tourne
    avec plusieurs ouvriers gunicorn : un second appel à /api/admin/veille/sante
    peut tomber sur un ouvrier qui n'a rien collecté, et rendre un tableau vide
    qui se lirait comme « rien n'a jamais tourné ». En rendant le relevé dans la
    réponse du passage, collecte et constat ont lieu au même endroit : la
    réponse est cohérente par construction.

    Sans cette relance, le seul moyen de voir un résultat était d'attendre le
    passage automatique — trois minutes après un démarrage, puis toutes les six
    heures. La route existait déjà ; rien ne l'appelait.
    """
    try:
        nouveaux = automation.veille_refresh()
    except Exception:
        app.logger.exception("veille : relance manuelle")
        return jsonify(ok=False, error="veille_echec"), 502
    return jsonify(ok=True, nouveaux=nouveaux, **veille_sources.etat())


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
    refus = _jeton_refus(request.headers.get("X-Ingest-Token"), token, "rag-ingest")
    if refus:
        return refus
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
    audit.journaliser("document.chargement",
                      cible=str(doc.get("id") or "")[:60],
                      detail="ingestion par jeton — " + (doc.get("title") or filename or "")[:100])
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


@app.route("/admin/rgpd")
@admin_required
def admin_rgpd_page():
    """Tableau de bord RGPD + transparence IA Act : les controles MESURES
    d'un cote, le dossier declaratif de l'autre, et le renvoi vers la gestion
    des clients — qui existe deja et n'est pas dupliquee ici."""
    return _serve_fast("admin-rgpd.html", _CC_ADMIN)


@app.route("/api/admin/clients", methods=["GET"])
@admin_required
def api_clients_list():
    # LA CONSULTATION EST TRACÉE — c'est l'accès le plus fréquent aux données
    # personnelles, et le seul qui ne laissait rien : l'export et le
    # téléchargement de pièce s'inscrivent, la lecture des fiches complètes
    # (email, téléphone, notes) non. Dédupliquée par acteur et par heure pour
    # que chaque rafraîchissement d'écran ne devienne pas une ligne de bruit.
    clients = clients_db.list()
    try:
        acteur = (current_user() or {}).get("email") or "?"
        heure = int(time.time() // 3600)
        if _CONSULT_VUES.get(acteur) != heure:
            _CONSULT_VUES[acteur] = heure
            audit.journaliser("clients.consultation",
                              detail="%d fiche(s)" % len(clients))
    except Exception:
        pass
    return jsonify(ok=True, clients=clients, stats=clients_db.stats(),
                   options={"statuts": list(STATUTS), "bases": list(BASES_LEGALES),
                            "categories_pieces": list(CATEGORIES_PIECES)})


_CONSULT_VUES = {}


@app.route("/api/admin/clients/verify", methods=["POST"])
@admin_required
def api_clients_verify():
    """Recalcule l'empreinte SHA-256 de toutes les pièces clients — le pendant
    de la vérification de la base de connaissance, que le registre déclarait
    « vérifiable à la demande » sans restreindre à la base. Une preuve de
    consentement ou un contrat altéré en base doit se VOIR, pas se servir."""
    try:
        r = clients_db.docs_verify(actor=(current_user() or {}).get("email") or "")
    except ClientsError as exc:
        return jsonify(ok=False, error=exc.code), exc.status
    audit.journaliser("clients.verification",
                      detail="%d pièce(s), %d écart(s)" % (r["total"], len(r["ecarts"])),
                      ok=not r["ecarts"])
    return jsonify(ok=True, **r)


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
    # LA MESURE, A COTE DU DECLARATIF. rgpd.etat() est un dossier de
    # constantes ; conformite_mesures relit l'etat reel du site a chaque
    # appel. Les controles n'entrent PAS dans /api/conformite (public) :
    # publier ses non-conformites en continu n'est pas un devoir de
    # transparence, l'admin les recoit et agit.
    try:
        etat["controles_mesures"] = conformite_mesures.etat(clients_db, app)
    except Exception as _e:
        etat["controles_mesures"] = {"erreur": str(_e)[:120]}
    return jsonify(ok=True, **etat)


@app.route("/api/base-carbone", methods=["GET"])
@login_required
def api_base_carbone():
    """La Base Carbone ADEME, et la confrontation de nos facteurs aux siens.

    FERMÉE PAR DÉFAUT, ET C'EST LE CONTRÔLE DE DÉMARRAGE QUI L'A EXIGÉ : posée
    ouverte, elle a fait REFUSER LE DÉMARRAGE au serveur — « /api/base-carbone
    est ouverte : fermer la page sans fermer son interface ne protège rien ».
    La base de l'ADEME est publique, mais ce que cette route publie en plus ne
    l'est pas : la table de facteurs du cabinet et l'écart qui la sépare de la
    référence. C'est de la matière d'étude, elle suit le compte client.

    ELLE NE REMPLACE RIEN, et c'est le point. L'ADEME fait foi pour un bilan
    d'émissions français opposable (BEGES, art. L229-25) ; INTENSITE_RESEAU
    décrit le réseau de l'exercice en cours. La route sert les deux et nomme
    l'usage de chacune plutôt que de trancher à la place du lecteur.

    `?table=reseau` ajoute la confrontation ligne à ligne d'INTENSITE_RESEAU.
    """
    try:
        import base_carbone
        if not base_carbone.disponible():
            return jsonify(ok=False,
                           erreur="Base Carbone absente du depot"), 503
        out = {"ok": True, "version": base_carbone.VERSION,
               "source": base_carbone.SOURCE,
               "electricite": base_carbone.electricite()}
        if (request.args.get("table") or "") == "reseau":
            import datacenter
            out["confrontation"] = base_carbone.confronter(
                datacenter.INTENSITE_RESEAU,
                (request.args.get("frontiere") or "production"))
        return jsonify(**out)
    except Exception as e:  # noqa: BLE001
        app.logger.error("BASE_CARBONE_ERR: %s", e)
        return jsonify(ok=False, erreur="base indisponible"), 503


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
            assistant.defaut(),
            "Tu qualifies une demande entrante pour un cabinet de cybersécurité "
            "industrielle. Réponds UNIQUEMENT un objet JSON compact : "
            '{"secteur":"...","urgence":"faible|moyenne|haute","resume":"une phrase factuelle"} '
            "sans aucun autre texte.",
            # MINIMISÉ AVANT L'ENVOI. Un visiteur met souvent son téléphone ou
            # son adresse dans le corps du message : la qualification
            # secteur/urgence n'en a pas besoin, et le registre ne déclarait
            # pas le fournisseur de modèle comme destinataire du texte brut.
            # Les marqueurs « [TELEPHONE RETIRE] » restent lisibles au modèle.
            "Sujet choisi : %s\nMessage :\n%s" % (
                minimisation.masquer(sujet), minimisation.masquer(msg[:1200])),
            max_tokens=160)
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
    refus = _jeton_refus(request.headers.get("X-Ingest-Token"), INGEST_TOKEN, "cockpit")
    if refus:
        return refus

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
def api_state():
    """Instantané de l'état courant du cockpit (inventaire, alertes, événements récents)."""
    return jsonify(state.snapshot())


@app.route("/api/assets")
def api_assets():
    """Inventaire des actifs connus du cockpit (pour l'étude de conformité)."""
    return jsonify(assets=state.inventory())


@app.route("/api/trends")
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
    refus = _jeton_refus(request.headers.get("X-Ingest-Token"), INGEST_TOKEN, "cockpit")
    if refus:
        return refus
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
    refus = _jeton_refus(request.headers.get("X-Ingest-Token"), INGEST_TOKEN, "cockpit")
    if refus:
        return refus
    days = request.args.get("retention_days", type=float) or _RETENTION_DAYS
    max_rows = request.args.get("max_rows", type=int) or _MAX_ROWS
    deleted = state.purge(retention_days=days or None, max_rows=max_rows or None,
                          archive_path=_ARCHIVE_PATH)
    return jsonify(ok=True, deleted=deleted)


def _degrade(etat, quoi):
    """Marque l'état dégradé EN NOMMANT ce qui l'a dégradé.

    NEUF CONTRÔLES POUVAIENT LEVER LE MÊME DRAPEAU, et le lecteur n'avait que
    le drapeau. « degraded » disait qu'une chose allait mal parmi neuf, sans
    dire laquelle : la supervision alertait, et le diagnostic recommençait à
    zéro. Les clés `cause`, `cause_courriel`, `cause_sessions` existaient déjà
    mais chacune pour un contrôle, sans qu'aucune liste ne dise lesquels ont
    effectivement mordu.

    C'est aussi ce qui rend chaque contrôle ÉPROUVABLE séparément : sur un
    environnement d'essai où trois autres causes sont déjà réunies, une règle
    qui ne regarde que le drapeau reste verte quoi qu'on fasse au contrôle
    qu'elle prétend surveiller.
    """
    etat["status"] = "degraded"
    if quoi not in etat.setdefault("degrade_par", []):
        etat["degrade_par"].append(quoi)


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


@app.route("/api/admin/reglages")
@admin_required
def api_admin_reglages():
    """L'état des réglages d'environnement : écartés, inertes, absents.

    POURQUOI CETTE ROUTE EXISTE, ET PAS SEULEMENT LE JOURNAL. Un réglage
    écarté ne coûte plus le service — il retombe sur son défaut — mais il
    disparaît : les journaux de l'hébergeur sont éphémères et personne ne les
    ouvre. L'exploitant croit sa valeur prise, elle ne l'est pas, et aucun
    écran ne le contredit.

    POURQUOI ICI ET PAS DANS /health. Cette route nomme des variables ; /health
    est public et ne doit pas le faire. Le partage est celui que /health tient
    déjà pour les causes de base de données : dehors la conséquence, dedans le
    détail.

    AUCUNE VALEUR N'EN SORT, y compris pour les variables ABSENTES : on rend la
    commande qui en fabrique une, jamais une clé. Une clé qui traverse un écran
    de diagnostic n'est plus une clé — c'est la leçon exacte de l'incident qui
    a fait naître ce module.
    """
    ecartes = []
    try:
        for r in reglages.refuses():
            ecartes.append({
                "variable": r["variable"], "attendu": r["attendu"],
                "consequence": "la valeur par défaut s'applique ; la valeur "
                               "saisie est sans effet",
                "geste": "corrigez la variable chez l'hébergeur, ou supprimez-la"})
    except Exception:
        ecartes = []

    # ── CE QUI EST POSÉ ET NE SERT À RIEN ─────────────────────────────────
    # Un secret inutile n'est pas neutre : il se lit dans la console de
    # l'hébergeur, il part dans les sauvegardes de configuration, et il se
    # copie d'un service à l'autre. Il porte le risque d'un secret sans en
    # rendre l'usage.
    inertes = []
    if os.environ.get("ADMIN_PASSWORD"):
        # ADMIN_PASSWORD ne sert QU'À CRÉER le compte au tout premier
        # démarrage : dès que le compte existe, auth._bootstrap_admin() rend la
        # main AVANT de la lire. La changer ne change donc plus rien — et
        # croire le contraire est le piège, car on croit avoir tourné un
        # mot de passe qu'on n'a pas tourné.
        try:
            import auth as _auth_r
            existe = bool(_auth_r.store.get((_auth_r.ADMIN_EMAIL or "").strip().lower()))
        except Exception:
            existe = None      # base muette : on ne PROUVE rien, on se tait
        if existe:
            inertes.append({
                "variable": "ADMIN_PASSWORD",
                "consequence": "le compte administrateur existe déjà : cette "
                               "variable n'est plus lue. La modifier ne change "
                               "aucun mot de passe",
                "geste": "changez le mot de passe DANS l'application, puis "
                         "supprimez la variable chez l'hébergeur"})
    if os.environ.get("RAG_ACCESS_KEY"):
        # La fédération lit RAG_PAIR_CLE (appel) et RAG_CLES_SERVIES (service).
        # RAG_ACCESS_KEY n'est lue nulle part ici — un essai le vérifie et
        # retirera cette mention d'elle-même si le code venait à la lire.
        inertes.append({
            "variable": "RAG_ACCESS_KEY",
            "consequence": "aucun code de ce service ne lit cette variable ; "
                           "la fédération utilise RAG_PAIR_CLE et "
                           "RAG_CLES_SERVIES",
            "geste": "supprimez-la ici — et régénérez-la là où elle sert"})

    # ── CE QUI MANQUE, ET CE QUE ÇA COÛTE ─────────────────────────────────
    absents = []
    if not os.environ.get("FLASK_SECRET_KEY", "").strip():
        absents.append({
            "variable": "FLASK_SECRET_KEY",
            "consequence": "chaque processus signe les sessions avec une clé "
                           "qu'il tire lui-même. Il y en a deux, et ils "
                           "recyclent en cours de service : un cookie signé "
                           "par l'un n'est pas reconnu par l'autre, et "
                           "l'utilisateur est déconnecté par intermittence, "
                           "sans message",
            "geste": "python3 -c \"import secrets; print(secrets.token_hex(32))\"",
            "reserve": "exécutez la commande CHEZ VOUS et collez le résultat "
                       "directement chez l'hébergeur : une clé qui passe par "
                       "un écran, une conversation ou un journal est à jeter"})

    # ── UNE CAPACITÉ ÉTEINTE QUI NE DISAIT PAS QU'ELLE L'ÉTAIT ────────────
    # Le paiement s'éteint EN SILENCE, et c'est voulu côté visiteur : un bouton
    # qui mène à « paiement non configuré » vaut moins qu'un bouton absent.
    # Mais côté exploitant, ce silence est un piège — on refait tout le
    # parcours (inscription, courriel, confirmation) en cherchant une caisse
    # qui n'a jamais été allumée, et aucun écran ne le dit.
    #
    # LE CAS DANGEREUX N'EST PAS ZÉRO SUR TROIS, C'EST DEUX SUR TROIS : la clé
    # est bien posée, on croit avoir configuré, et rien ne s'allume parce que
    # `paiement.configure()` exige les trois ensemble. C'est pourquoi on compte
    # ce qui est posé au lieu de se contenter de « non configuré ».
    try:
        import paiement as _pay
        trois = (_pay.CLE, _pay.CLE_WEBHOOK, _pay.CLE_PRIX)
        posees = [v for v in trois if (os.environ.get(v) or "").strip()]
        manque = [v for v in trois if v not in posees]
    except Exception:
        posees, manque = [], []
    if manque:
        absents.append({
            "variable": " · ".join(manque),
            "consequence":
                "le paiement en ligne est éteint : le bloc « Ouvrir mon accès "
                "maintenant » de /connexion reste caché, /api/paiement/etat "
                "répond « configure: false », et chaque compte attend votre "
                "validation manuelle"
                + ("" if not posees else
                   " — ATTENTION : %d valeur(s) sur 3 sont DÉJÀ posées. Les "
                   "trois sont exigées ensemble ; une configuration partielle "
                   "ne s'allume pas et ne prévient pas" % len(posees)),
            "geste": "posez les trois chez l'hébergeur : clé secrète (sk_…), "
                     "secret de signature du webhook (whsec_…), identifiant "
                     "de prix (price_…)",
            "reserve": "commencez en mode TEST — clé sk_test_… et carte "
                       "4242 4242 4242 4242 — avant toute clé de production. "
                       "L'ACHAT SE FAIT EN FENÊTRE PRIVÉE : le site n'ouvre "
                       "qu'une session par navigateur, et le compte acheteur "
                       "ne peut pas cohabiter avec le vôtre"})

    # ── UNE CONFIGURATION COMPLÈTE QUI NE PEUT PAS MARCHER ────────────────
    # La caisse s'ouvre en `mode="payment"` : un prix Stripe RÉCURRENT la fait
    # échouer à chaque tentative. Les trois variables sont pourtant là, le
    # panneau est muet, la page affiche son bouton — et le visiteur lit
    # « paiement momentanément indisponible » sans que personne sache pourquoi.
    # C'est le pire des cas : tout paraît en ordre.
    if not manque:
        try:
            import paiement as _pay2
            t = _pay2.tarif()
        except Exception:
            t = None
        if t and t.get("recurrent"):
            ecartes.append({
                "variable": _pay2.CLE_PRIX,
                "attendu": "un prix à paiement unique",
                "consequence": "le prix configuré est RÉCURRENT (abonnement), "
                               "alors que la caisse s'ouvre en paiement unique : "
                               "chaque tentative échoue, et le visiteur ne lit "
                               "que « paiement momentanément indisponible »",
                "geste": "créez dans Stripe un prix « unique » (one-off) pour ce "
                         "produit et remplacez l'identifiant, ou vendez un "
                         "abonnement — ce que ce service ne sait pas encore faire"})

    return jsonify(ok=True, ecartes=ecartes, inertes=inertes, absents=absents,
                   total=len(ecartes) + len(inertes) + len(absents))


# LA SONDE RÉPOND SUR LES DEUX CHEMINS, ET CE N'EST PAS DE LA COMPLAISANCE.
#
# CE QUI EST ARRIVÉ. Le journal de production, le 27 août à 13 h 00 :
#
#     "GET /api/health HTTP/1.1" 404 81 "-" "Render/1.0"
#
# Render sondait `/api/health`. Ce service n'a jamais servi que `/health` —
# `render.yaml` le déclare ainsi. Mais `render.yaml` ne vaut qu'à la CRÉATION
# du service : le réglage du tableau de bord, lui, l'emporte pour un service
# existant, et il pointait ailleurs. Résultat : sonde en échec, service
# déclaré en panne, trafic coupé. Le site fonctionnait parfaitement.
#
# POURQUOI UN ALIAS PLUTÔT QU'UN RÉGLAGE À CORRIGER. Corriger le tableau de
# bord règle le cas d'aujourd'hui et laisse le piège en place : ces deux noms
# se confondent, ils circulent tous les deux dans les notes d'exploitation, et
# la prochaine personne qui recréera le service ou changera ce champ aura une
# chance sur deux de le remettre. Une sonde de vie n'a AUCUNE raison d'être
# difficile à atteindre : c'est le seul point de l'application dont
# l'indisponibilité coupe tout le reste. Les deux noms mènent donc au même
# endroit, et le tableau de bord peut porter l'un ou l'autre.
@app.route("/api/health")
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
            # Le commit déployé, quand l'hébergeur le fournit. C'est ce qui
            # permet de répondre « oui » ou « non » à « le correctif est-il en
            # ligne ? » sans avoir à l'éprouver au comportement.
            "commit": _COMMIT or None, "branche": _BRANCHE or None,
            "demarre_depuis_s": int(time.time() - _DEMARRAGE)}
    try:
        caps = rag.capabilities()
        etat["base"] = "connectee" if caps.get("persistent") else "degradee"
        etat["recherche"] = caps.get("mode")
        if not caps.get("persistent"):
            _degrade(etat, "base")
            etat["cause"] = caps.get("reason") or "base_indisponible"
    except Exception:
        _degrade(etat, "base")
        etat["base"] = "inconnue"
    # Magasin de comptes : simple lecture d'un attribut en mémoire, aucune requête.
    try:
        import auth as _auth
        etat["comptes"] = getattr(_auth.store, "mode", "inconnu")
        if etat["comptes"] != "postgres":
            _degrade(etat, "comptes")
    except Exception:
        etat["comptes"] = "inconnu"
    # ── LE COURRIEL, ET POURQUOI IL EST DEVENU CRITIQUE ────────────────────
    # Depuis que les pages du menu demandent un compte, TOUT le parcours
    # d'accès passe par trois courriels : la confirmation d'adresse au client,
    # la demande de validation à l'administrateur, l'activation au client. Sans
    # clef d'envoi, send_email() renvoie faux et journalise un avertissement —
    # personne ne reçoit rien, le visiteur attend un lien qui ne viendra pas, et
    # l'administrateur ignore qu'une demande dort. La panne est totale ET
    # silencieuse : c'est la pire des deux, et c'est pourquoi elle est ici.
    try:
        import auth as _auth
        pret = bool(os.environ.get("BREVO_API_KEY"))
        etat["courriel"] = "configure" if pret else "SANS_CLEF"
        etat["courriel_admin"] = _auth.ADMIN_EMAIL
        if not pret:
            _degrade(etat, "courriel")
            etat["cause_courriel"] = (
                "BREVO_API_KEY absente : aucune inscription ne peut aboutir — "
                "ni confirmation d'adresse, ni notification à l'administrateur")
    except Exception:
        etat["courriel"] = "inconnu"
    # ── LA SIGNATURE DES SESSIONS, ET POURQUOI ELLE EST ICI ───────────────
    # Même critère que le courriel ci-dessus : totale ET silencieuse.
    # Sans FLASK_SECRET_KEY, auth.init_app retombe sur une clé tirée au hasard
    # À CHAQUE PROCESSUS. Il y en a deux (gunicorn.conf.py : workers = 2), et
    # ils recyclent en cours de service (max_requests = 8000) : un cookie signé
    # par l'un n'est pas reconnu par l'autre, Flask traite alors la session
    # comme vide — sans erreur — et l'utilisateur se retrouve déconnecté sans
    # motif visible, par intermittence. Rien dans les journaux, rien à l'écran.
    if os.environ.get("FLASK_SECRET_KEY", "").strip():
        etat["sessions"] = "persistantes"
    else:
        etat["sessions"] = "non persistantes"
        _degrade(etat, "sessions")
        etat["cause_sessions"] = (
            "clé de signature absente : chaque processus tire la sienne, "
            "et les sessions sont perdues d'un processus à l'autre comme à "
            "chaque redémarrage — déconnexions intermittentes")
    # ── LES RÉGLAGES ÉCARTÉS : UN COMPTE, ET RIEN DE PLUS ─────────────────
    # /health EST PUBLIC. Nommer ici les variables d'un service apprendrait à
    # un tiers ce que l'exploitant sait déjà ; le compte suffit à faire ouvrir
    # la console d'administration, qui elle est derrière un compte admin et
    # peut donc les nommer, avec le geste à faire.
    #
    # ET CE N'EST PAS UN ÉTAT DÉGRADÉ. Le service rend exactement le service
    # attendu, sur ses valeurs par défaut : c'est l'INTENTION de l'exploitant
    # qui n'est pas appliquée, pas le service qui manque. Confondre les deux
    # userait le mot « dégradé » jusqu'à ce qu'il ne fasse plus lever personne.
    try:
        etat["reglages_ignores"] = len(reglages.refuses())
    except Exception:
        etat["reglages_ignores"] = None
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
                _degrade(etat, "magasin:comptes")
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
                _degrade(etat, "magasin:" + nom)
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
            _degrade(etat, "playbook")
            etat["playbook"]["cause"] = (sp["motifs_casses"] or sp["sans_regle"]
                                         or sp["instances_inconnues"])[:3]
    except Exception:
        etat["playbook"] = {"ok": None, "cause": "état non lisible"}

    if request.args.get("detail") == "1":
        etat.update(_sonde_detaillee())
        if etat.get("comptes_lecture", "").startswith("echec"):
            _degrade(etat, "lecture_comptes")
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


@app.route("/api/acces")
def api_acces():
    """Les pages qui demandent un compte — pour les SIGNALER avant le clic.

    POURQUOI CETTE ROUTE EXISTE. Vingt-six liens de la seule page d'accueil
    mènent à une page réservée, et les pieds de page des quarante autres
    portent les mêmes. Les étiqueter à la main, c'était quarante fichiers à
    corriger, puis un de plus à chaque page ajoutée — et c'est le lien qu'on
    oublie qui surprend le visiteur. La liste est donc servie une fois, et
    nav.js marque les liens partout d'un seul geste.

    RIEN N'EST DIVULGUÉ ICI, et c'est ce qui autorise à la laisser ouverte :
    elle ne dit pas ce que CONTIENNENT les pages, seulement lesquelles
    demandent un compte — ce qu'un visiteur apprendrait de toute façon en
    cliquant. La servir lui épargne le clic.

    CACHEABLE UNE HEURE, ET PUBLIQUEMENT : la réponse ne dépend ni de la
    session ni du visiteur, et ne change qu'au déploiement. Elle était pourtant
    la requête la plus fréquente du site — nav.js l'appelle à CHAQUE page, et
    chaque appel réitérait app.url_map et re-gzippait le corps. Le marquage 🔒
    peut rester périmé au pire une heure après un déploiement qui change la
    politique — cosmétique : la protection réelle est côté serveur, sur chaque
    route."""
    def _liste():
        reels = _acces_reels()
        fermees = sorted(c for c, e in reels.items() if e != "direct")
        # LES DEUX NIVEAUX SONT DISTINGUÉS, et ce n'est pas un détail.
        # DÉFAUT CORRIGÉ : la route les fondait en une seule liste « client »,
        # si bien que nav.js ne pouvait pas signaler à un client CONNECTÉ les
        # pages qui lui restent fermées. Il voyait donc des liens sans marque
        # menant à un refus — le seul endroit du site où un lien ment.
        # Rien de plus n'est divulgué : dire qu'une page demande le rôle
        # administrateur, c'est dire ce qu'un clic apprendrait de toute façon.
        return dict(ok=True, client=fermees,
                    admin=sorted(c for c, e in reels.items() if e == "admin"),
                    note="« client » : toute page demandant un compte validé, "
                         "administration comprise. « admin » : le sous-ensemble "
                         "réservé au rôle administrateur.")
    return _json_fige("acces", _liste,
                      cache_control="public, max-age=3600")


@app.route("/api/acces/perimetre")
def api_acces_perimetre():
    """Ce qu'un compte client ouvre, par rubrique — pour la page qui le vend.

    POURQUOI UNE ROUTE À PART, ET PAS UN CHAMP DE PLUS SUR /api/acces. Cette
    dernière est la requête la plus fréquente du site : nav.js l'appelle à
    CHAQUE page pour marquer les liens. Y verser les rubriques et leurs
    libellés ferait payer à quarante pages le détail dont une seule a besoin.
    Deux sujets, deux routes.

    RIEN DE PLUS N'EST DIVULGUÉ : ce sont les entrées du menu, que tout
    visiteur voit déjà dans le tiroir, et le fait qu'elles demandent un compte
    — ce que /api/acces dit par ailleurs. La page de vente doit pouvoir décrire
    ce qu'elle vend.

    Même cache d'une heure, et pour la même raison : la réponse ne dépend ni de
    la session ni du visiteur, et ne change qu'au déploiement.
    """
    import perimetre
    return _json_fige("acces-perimetre", lambda: dict(ok=True, **perimetre.etat()),
                      cache_control="public, max-age=3600")


# ─────────────────────────── LA POLITIQUE D'ACCÈS EST-ELLE APPLIQUÉE ? ──────
# À EXÉCUTER EN DERNIER, et ce n'est pas un détail d'ordonnancement : tant que
# toutes les routes ne sont pas déclarées, le relevé est incomplet — et un
# contrôle incomplet sur un sujet d'accès est pire que pas de contrôle, parce
# qu'il rassure.

def _menu_chemins():
    """Les chemins que le menu latéral propose, lus dans nav.js.

    La règle porte sur « les pages du menu latéral » : c'est donc le menu qui
    dit ce qui doit être décidé, et le recopier ici en ferait une seconde
    source de vérité qui divergerait au premier ajout de page.

    UN SEUL LECTEUR EN PRODUCTION. L'extraction vivait ici ET dans `perimetre`,
    qui sert la page de vente : deux analyseurs du même fichier, dont un seul
    aurait été corrigé le jour où le menu change de forme. Les essais, eux,
    gardent leur propre lecture — une règle qui réutiliserait ce lecteur
    resterait verte s'il cassait."""
    import perimetre
    chemins = {p["chemin"] for r in perimetre.rubriques() for p in r["pages"]}
    if len(chemins) < 30:
        raise RuntimeError(
            "politique d'accès : le menu n'a livré que %d entrées — la lecture "
            "de nav.js a dérivé, et un menu vide validerait n'importe quoi"
            % len(chemins))
    return chemins


def _acces_reels():
    """La protection RÉELLE de chaque page, relevée sur les décorateurs posés.

    On lit `admin_gated` puis `auth_gated`, que admin_required et
    login_required apposent respectivement (`admin_gated` implique
    `auth_gated`, jamais l'inverse). Lire les décorateurs plutôt qu'une liste
    tenue à la main OU qu'un préfixe d'URL est tout l'intérêt de ce contrôle :
    c'est l'état effectif du site, celui qu'un visiteur rencontre — une route
    /admin/… à laquelle on aurait oublié de poser @admin_required doit être vue
    comme telle, pas comme « admin » parce que son chemin le laisse croire."""
    reels = {}
    for rule in app.url_map.iter_rules():
        chemin = str(rule.rule)
        if chemin.startswith("/api/") or "<" in chemin:
            continue

        # Seules les PAGES sont soumises à la politique. Les fichiers servis —
        # feuille de style, scripts, images — sont demandés par le navigateur
        # sans session : les fermer casserait jusqu'aux pages ouvertes.
        if chemin not in PAGES and not chemin.startswith("/admin"):
            continue
        vue = app.view_functions.get(rule.endpoint)
        if getattr(vue, "admin_gated", False):
            reels[chemin] = "admin"
        elif getattr(vue, "auth_gated", False):
            reels[chemin] = "client"
        else:
            reels[chemin] = "direct"
    return reels


def _acces_api_reels():
    """La protection RÉELLE de chaque interface de programmation.

    Les chemins à paramètre (« <pid> ») sont ramenés à leur forme déclarée : la
    politique nomme des interfaces, pas des instances. Comme pour les pages, on
    distingue « admin_gated » de « auth_gated » : sans ce distinguo, une
    interface /api/admin/… protégée par le seul @login_required — donc
    accessible à N'IMPORTE QUEL compte client — se lisait « client », un statut
    que la politique déclare justement fermé pour toute la famille /api/admin/,
    et l'écart passait inaperçu faute de branche pour le comparer."""
    reels = {}
    for rule in app.url_map.iter_rules():
        chemin = str(rule.rule)
        if not chemin.startswith("/api/"):
            continue
        vue = app.view_functions.get(rule.endpoint)
        if getattr(vue, "admin_gated", False):
            reels[chemin] = "admin"
        elif getattr(vue, "auth_gated", False):
            reels[chemin] = "client"
        else:
            reels[chemin] = "direct"
    return reels


def _verifier_politique_acces():
    ecarts = (acces.verifier_application(_acces_reels(), _menu_chemins())
              + acces.verifier_api(_acces_api_reels()))
    if ecarts:
        raise RuntimeError("La politique d'accès n'est pas appliquée :\n  - "
                           + "\n  - ".join(ecarts))


def _verifier_liens_maturite():
    """UN LIEN VERS UNE PAGE QUI N'EXISTE PAS DOIT FAIRE ECHOUER LE DEMARRAGE,
    pas partir en production.

    `maturite_ot` declare ou chaque domaine se traite sur ce site, et le
    deroule d'un assessment renvoie vers six pages. Le module ne peut pas
    verifier ces chemins lui-meme : `app` l'importe, et l'inverse ferait un
    cycle. La verification se fait donc ici, au seul endroit qui connaisse a
    la fois les chemins declares et les pages reellement servies.

    C'EST LA MEME REGLE QUE LA POLITIQUE D'ACCES CI-DESSUS, et pour la meme
    raison : un ecart entre ce qu'on annonce et ce qu'on sert ne se decouvre
    pas au clic d'un visiteur.
    """
    manquants = []
    for cle, liens in maturite_ot.RESSOURCES.items():
        for l in liens:
            if l["chemin"] not in PAGES:
                manquants.append("domaine %s -> %s" % (cle, l["chemin"]))
    for e in maturite_ot.DEROULE:
        if e["chemin"] and e["chemin"] not in PAGES:
            manquants.append("deroule %s -> %s" % (e["n"], e["chemin"]))
    for h in maturite_ot.HORS_PORTEE:
        if h["chemin"] not in PAGES:
            manquants.append("hors portee %s -> %s" % (h["nom"], h["chemin"]))
    if manquants:
        raise RuntimeError("Maturite OT renvoie vers des pages inexistantes :"
                           "\n  - " + "\n  - ".join(manquants))


_verifier_politique_acces()
_verifier_liens_maturite()


if __name__ == "__main__":
    port = reglages.entier("PORT", 5000, mini=1, maxi=65535)
    app.run(host="0.0.0.0", port=port, debug=False)
