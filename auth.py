"""Authentification CONSEILPREV Cyber — inscription (validation admin) + connexion.

Inspiré du système de Sentinel : mots de passe hachés (werkzeug), sessions Flask,
captcha, protection anti-bruteforce, réponses anti-énumération, emails via Brevo.

Flux : inscription → l'utilisateur confirme son email → C'EST ALORS SEULEMENT que
l'administrateur est prévenu, avec un lien d'approbation valable trente jours →
il approuve → le client est prévenu que son accès est ouvert. Les comptes non
confirmés / non approuvés ne peuvent pas se connecter. Seuls le cockpit et la
supervision sont protégés ; le contenu public reste ouvert.

L'ORDRE DES DEUX PREMIÈRES ÉTAPES EST UN CHOIX DE SÉCURITÉ, pas de commodité :
prévenir l'administrateur dès l'inscription lui faisait recevoir des demandes
portant des adresses que personne n'avait prouvées, et lui demandait d'attendre
une confirmation dont rien ne l'avisait.

Stockage : PostgreSQL si DATABASE_URL est défini (persistant), sinon fichier JSON local.
"""
import functools
import html as html_lib
import json
import logging
import os
import re
import reglages   # un réglage illisible ne doit pas arrêter le service
import secrets
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone

import requests
from flask import (Blueprint, Response, jsonify, make_response, redirect, request,
                   send_from_directory, session)
from werkzeug.security import check_password_hash, generate_password_hash

HERE = os.path.dirname(os.path.abspath(__file__))
auth_bp = Blueprint("auth", __name__)

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "christophe.cerf@outlook.com")
# Portail d'accès (1re couche) : mot de passe unique protégeant l'entrée de la
# zone /admin, EN PLUS de la connexion par compte administrateur (2e couche).
# Défini sur Render ; s'il est vide, le portail est inactif (seule la connexion
# par compte protège alors — aucun risque de se verrouiller avant configuration).
ADMIN_GATE_PASSWORD = os.environ.get("ADMIN_GATE_PASSWORD", "").strip()
SENDER = {"name": "CONSEILPREV Cyber", "email": "christophe.cerf@i-aes.com"}
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
VERIFY_VALIDITY_H = 48
RESET_VALIDITY_H = 2
# LE JETON D'APPROBATION N'EXPIRAIT PAS, et c'était le seul des trois.
# Confirmation d'adresse : 48 h. Réinitialisation de mot de passe : 2 h.
# Approbation : illimitée — un courriel d'approbation vieux de deux ans
# ouvrait encore un compte. Un lien qui ne meurt jamais survit à la boîte
# qui l'a reçu : archive exportée, message transféré, messagerie reprise.
# Trente jours laissent largement le temps de répondre ; passé ce délai,
# l'approbation se fait depuis la page d'administration, qui exige une
# session administrateur.
APPROVE_VALIDITY_H = 24 * 30
_MS = 1000

# ---------------------------------------------------------------- utilitaires ---
def _now_ms():
    return int(time.time() * _MS)


def _base_url():
    return (os.environ.get("PUBLIC_BASE_URL") or request.url_root).rstrip("/")


def valid_email(email):
    # [^@\s] seul laisse passer <, >, ", ' : une adresse pourrait alors porter
    # du HTML jusqu'aux pages qui l'affichent sans échappement (ex. les pages
    # de confirmation d'admin_approve, plus bas).
    return bool(re.match(r"^[^@\s<>\"']+@[^@\s<>\"']+\.[^@\s<>\"']+$", email or ""))


def password_strength(pw):
    if len(pw or "") < 10:
        return False, "Le mot de passe doit faire au moins 10 caractères."
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return False, "Le mot de passe doit contenir des lettres et des chiffres."
    return True, ""


# --------------------------------------------------------- protection bruteforce
class _RateGuard:
    """Compteur en mémoire (par IP/clé) : blocage temporaire après trop d'échecs."""

    def __init__(self):
        self._fails = {}
        self._lock = threading.Lock()

    def blocked(self, key, limit=8, window=600):
        with self._lock:
            arr = [t for t in self._fails.get(key, []) if t > time.time() - window]
            self._fails[key] = arr
            return len(arr) >= limit

    def fail(self, key):
        with self._lock:
            self._fails.setdefault(key, []).append(time.time())

    def clear(self, key):
        with self._lock:
            self._fails.pop(key, None)

    def retry_after(self, key, limit=8, window=600):
        """Dans combien de secondes le blocage se lève, au plus tôt.

        POURQUOI CETTE MÉTHODE EXISTE. Un refus de cadence sans « Retry-After »
        fait réessayer en boucle : le client légitime devient lui-même la
        charge, et le compteur qu'il alimente repousse d'autant le moment où il
        repassera. Le refus doit donc dire QUAND revenir, et pour le dire il
        faut le calculer ici — c'est le seul endroit qui sait quand les échecs
        ont été comptés.

        LE CALCUL. Le blocage tient tant que `limit` échecs restent dans la
        fenêtre. Il se lève donc quand le `limit`-ième échec le plus RÉCENT
        sort de la fenêtre : c'est lui, et non le plus ancien de tous, qui
        ramène le compte sous la limite.

        LE MÊME VERROU QUE `blocked()`, et pas seulement par habitude : lue
        pendant qu'un autre fil élague la liste, la durée serait calculée sur
        un état intermédiaire — c'est-à-dire fausse, sans que rien ne le dise.

        FAUTE D'ÉCHEC DATÉ, on rend la fenêtre entière. Une durée trop longue
        fait patienter ; une durée trop courte fait revenir dans le mur, ce qui
        est exactement ce qu'on cherche à éviter.
        """
        with self._lock:
            arr = sorted(t for t in self._fails.get(key, [])
                         if t > time.time() - window)
            if len(arr) < limit:
                return int(window)
            # Les `limit` plus récents : le premier d'entre eux est celui dont
            # la sortie de fenêtre débloque.
            plus_ancien_retenu = arr[-limit]
            return max(1, int(plus_ancien_retenu + window - time.time()) + 1)


guard = _RateGuard()


def _refus_cadence(message, key, limit=8, window=600):
    """Le refus de cadence, avec le délai avant de revenir.

    ÉCRIT UNE FOIS. Les quatre portes de ce module refusaient chacune à leur
    façon, et aucune ne disait quand revenir : le client légitime réessayait
    en boucle et devenait lui-même la charge qui le maintenait dehors. Trois
    recopies de la même correction auraient divergé à la première retouche —
    et c'est celle qu'on oublie qui reste muette.

    LES BORNES SE PASSENT, elles ne sont pas devinées : chaque porte a les
    siennes, et un en-tête calculé sur d'autres annoncerait un délai qui n'est
    pas celui appliqué.
    """
    rep = jsonify(error=message)
    rep.status_code = 429
    rep.headers["Retry-After"] = str(guard.retry_after(key, limit, window))
    return rep


def _client_ip():
    # request.remote_addr est corrigé par ProxyFix (app.py) : X-Forwarded-For
    # n'est plus lu ici directement, parce que ce serait relire un en-tête que
    # l'appelant écrit lui-même — voir le commentaire près de app = Flask(...).
    return request.remote_addr or "?"


# Alias public (réutilisé par app.py pour la limitation de débit du formulaire de contact).
client_ip = _client_ip


# ------------------------------------------------------------------- stockage ---
_FIELDS = ["email", "name", "org", "password_hash", "email_verified", "approved",
           "role", "verify_token", "verify_expire", "approve_token",
           "approve_expire", "reset_token", "reset_expire", "created_at",
           "last_login"]


class _JsonStore:
    """Stockage fichier (dev / sans base). Non partagé, non durable sur Render."""

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _dump(self, d):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)

    def get(self, email):
        return self._load().get((email or "").lower())

    def get_by(self, field, value):
        for u in self._load().values():
            if u.get(field) and u[field] == value:
                return u
        return None

    def create(self, user):
        with self._lock:
            d = self._load()
            if user["email"] in d:
                return False
            d[user["email"]] = user
            self._dump(d)
            return True

    def update(self, email, **fields):
        with self._lock:
            d = self._load()
            u = d.get(email)
            if not u:
                return False
            u.update(fields)
            self._dump(d)
            return True

    def delete(self, email):
        with self._lock:
            d = self._load()
            if email not in d:
                return False
            del d[email]
            self._dump(d)
            return True

    def list_all(self):
        return sorted(self._load().values(), key=lambda u: u.get("created_at") or 0, reverse=True)


class _PgStore:
    """Stockage PostgreSQL (persistant). Table `users`."""

    _LOCK_KEY = 907245
    # Attente maximale pour obtenir une connexion du pool avant de passer en
    # direct, et durée pendant laquelle on cesse ensuite de le solliciter.
    POOL_ACQUIS_S = 1.5
    POOL_GRACE_S = 60.0

    def __init__(self, dsn):
        import psycopg
        import psycopg.rows
        from psycopg_pool import ConnectionPool
        sep = "&" if "?" in dsn else "?"
        self._dsn = dsn + sep + "connect_timeout=10"
        self.replis_directs = 0        # nombre de fois où le pool n'a pas répondu
        self._pool_ko_jusqu = 0.0      # fin de la période de grâce (voir _conn)
        # prepare_threshold=None : compatibilité avec un pooler PgBouncer en mode
        # transaction (endpoint « -pooler » de Neon) — sans quoi les requêtes
        # préparées échouent (« prepared statement does not exist »). check :
        # valide la connexion avant usage (réveil à froid d'une base serverless).
        self._pool = ConnectionPool(self._dsn, min_size=1, max_size=3,
                                    kwargs={"autocommit": True, "row_factory": psycopg.rows.dict_row,
                                            "prepare_threshold": None},
                                    timeout=8, open=True,
                                    check=ConnectionPool.check_connection)
        try:
            self._init()
        except Exception:
            try:
                self._pool.close()
            except Exception:
                pass
            raise

    @contextmanager
    def _conn(self):
        """Connexion pour une opération, avec REPLI SUR UNE CONNEXION DIRECTE.

        Constat de production qui a motivé ce repli : la base répondait
        parfaitement — 6 connexions ouvertes sur 103 autorisées, une connexion
        directe établie dans la seconde — et pourtant toute lecture de compte
        échouait en « PoolTimeout ». Ce n'était donc ni le réseau, ni la base, ni
        un plafond : c'était le POOL. Après un incident de connexion, psycopg_pool
        se met en retrait et refuse d'en ouvrir de nouvelles pendant plusieurs
        minutes ; les demandes attendent alors leur délai puis échouent, alors
        qu'une simple connexion directe aboutirait immédiatement.

        Faire dépendre l'accès au site du bon vouloir d'un pool est un pari
        inutile : les requêtes de comptes sont minuscules et rares. Si le pool ne
        rend pas la main, on ouvre une connexion le temps de la requête. Plus
        lent de quelques dizaines de millisecondes, mais jamais bloqué.

        L'attente d'acquisition est COURTE et suivie d'une période de grâce : un
        pool en bonne santé répond en millisecondes, et sans cette précaution
        chaque opération repayait l'attente tant que le pool boudait — une page
        composée de plusieurs requêtes dépassait alors le délai du navigateur et
        l'utilisateur voyait « Service momentanément indisponible ».

        L'échec d'ACQUISITION est seul traité ici : une erreur survenant DANS la
        requête remonte normalement à l'appelant."""
        import psycopg
        import psycopg.rows
        try:
            if time.time() < self._pool_ko_jusqu:
                raise RuntimeError("pool en période de grâce")
            conn = self._pool.getconn(timeout=self.POOL_ACQUIS_S)
        except Exception as exc:
            self.replis_directs += 1
            self._pool_ko_jusqu = time.time() + self.POOL_GRACE_S
            logging.getLogger("auth").warning(
                "comptes : pool indisponible (%s) — connexion directe pour cette "
                "requête (%d au total).", type(exc).__name__, self.replis_directs)
            direct = psycopg.connect(self._dsn, autocommit=True,
                                     row_factory=psycopg.rows.dict_row,
                                     prepare_threshold=None)
            try:
                yield direct
            finally:
                try:
                    direct.close()
                except Exception:
                    pass
            return
        try:
            yield conn
        finally:
            try:
                self._pool.putconn(conn)
            except Exception:
                pass

    def _init(self):
        with self._conn() as c:
            c.execute("SELECT pg_advisory_lock(%s)", (self._LOCK_KEY,))
            try:
                c.execute("""CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT, org TEXT, password_hash TEXT,
                    email_verified BOOLEAN DEFAULT FALSE,
                    approved BOOLEAN DEFAULT FALSE,
                    role TEXT DEFAULT 'user',
                    verify_token TEXT, verify_expire BIGINT,
                    approve_token TEXT, approve_expire BIGINT,
                    reset_token TEXT, reset_expire BIGINT,
                    created_at BIGINT, last_login BIGINT)""")
                # CREATE TABLE IF NOT EXISTS NE MIGRE RIEN : une base déjà
                # déployée garderait son ancienne forme, et l'échéance
                # d'approbation resterait absente là où elle compte le plus.
                c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                          "approve_expire BIGINT")
            finally:
                c.execute("SELECT pg_advisory_unlock(%s)", (self._LOCK_KEY,))

    def get(self, email):
        with self._conn() as c:
            return c.execute("SELECT * FROM users WHERE email=%s", ((email or "").lower(),)).fetchone()

    # LES SEULES COLONNES QU'ON A LE DROIT D'INTERROGER PAR CE CHEMIN.
    # Un nom de colonne ne peut pas être passé en paramètre : il finit
    # forcément dans la chaîne SQL. La question n'est donc pas COMMENT
    # l'échapper — c'est de savoir d'où il vient. Les quatre appelants
    # d'aujourd'hui passent des littéraux ; rien n'empêchait le cinquième de
    # passer une valeur de requête, et ce chemin lit la table des COMPTES.
    # Une liste blanche coûte une ligne et retire l'arme.
    _CHAMPS_CHERCHABLES = ("verify_token", "approve_token", "reset_token",
                           "email")

    def get_by(self, field, value):
        if field not in self._CHAMPS_CHERCHABLES:
            raise ValueError("champ non interrogeable : %r" % (field,))
        with self._conn() as c:
            return c.execute("SELECT * FROM users WHERE %s=%%s" % field, (value,)).fetchone()

    def create(self, user):
        cols = [k for k in _FIELDS if k in user]
        ph = ", ".join(["%s"] * len(cols))
        with self._conn() as c:
            try:
                c.execute("INSERT INTO users (%s) VALUES (%s)" % (", ".join(cols), ph),
                          tuple(user[k] for k in cols))
                return True
            except Exception:
                return False

    def update(self, email, **fields):
        sets = ", ".join("%s=%%s" % k for k in fields)
        with self._conn() as c:
            c.execute("UPDATE users SET %s WHERE email=%%s" % sets,
                      tuple(fields.values()) + (email,))
            return True

    def delete(self, email):
        with self._conn() as c:
            c.execute("DELETE FROM users WHERE email=%s", (email,))
            return True

    def list_all(self):
        with self._conn() as c:
            return c.execute("SELECT * FROM users ORDER BY created_at DESC NULLS LAST").fetchall()


class ComptesIndisponibles(RuntimeError):
    """La base de comptes est configurée mais ne répond pas.

    Distincte d'une erreur technique quelconque : les appelants savent qu'il
    s'agit d'une indisponibilité passagère, à annoncer comme telle plutôt que de
    laisser croire à des identifiants erronés."""


def _classer_erreur_base(exc):
    """Traduit l'échec de connexion en une cause actionnable, SANS divulguer
    l'hôte ni le port — ce diagnostic est lu depuis une page publique.

    Dire « OperationalError » n'aide personne. Dire « base injoignable ou
    endormie » contre « identifiants refusés » contre « base inexistante »
    envoie vers trois gestes différents, et c'est tout l'intérêt."""
    m = " ".join(str(exc).split()).lower()
    if "too many" in m or "connection limit" in m or "pooltimeout" in m:
        return ("plafond de connexions atteint — des connexions sont ouvertes "
                "ailleurs, ou le plan de la base est saturé")
    if "password" in m or "authentication" in m or "role" in m and "does not exist" in m:
        return ("identifiants de base refusés — DATABASE_URL a probablement été "
                "régénérée ; recopiez l'URL interne depuis l'hébergeur")
    if "database" in m and ("does not exist" in m or "n'existe pas" in m):
        return ("base inexistante — supprimée, expirée ou renommée ; recréez-la "
                "et remettez DATABASE_URL à jour")
    if ("timeout" in m or "timed out" in m or "refused" in m
            or "could not translate" in m or "name or service not known" in m):
        return ("base injoignable ou endormie — si elle vient d'être réveillée, "
                "la reconnexion est automatique ; sinon vérifiez qu'elle existe "
                "toujours et que DATABASE_URL est à jour")
    if "ssl" in m:
        return "connexion SSL refusée — vérifiez le paramètre sslmode de DATABASE_URL"
    return "connexion refusée (%s) — voir les journaux du service" % type(exc).__name__


class _ResilientUserStore:
    """Magasin de comptes qui se REBRANCHE tout seul sur PostgreSQL.

    Défaut corrigé ici, et il était grave : le choix du magasin se faisait UNE
    SEULE FOIS au démarrage. Si la base n'était pas joignable à cet instant —
    redémarrage du service pendant un hoquet, base encore en train de se
    réveiller — l'application basculait définitivement sur un fichier JSON. Or ce
    fichier est ÉPHÉMÈRE sur l'hébergement : il repart vide à chaque déploiement.
    Résultat, plus personne ne pouvait se connecter, y compris l'administrateur,
    y compris une fois la base revenue — et la seule issue était un redéploiement
    manuel. Chaque redémarrage rejouait ce tirage.

    Ici : la connexion est tentée EN TÂCHE DE FOND (le service démarre donc
    instantanément, jamais bloqué par une base lente — un démarrage qui traîne
    fait échouer la sonde de l'hébergeur, qui redémarre, ce qui relance le cycle),
    puis retentée périodiquement tant qu'elle échoue. Dès que la base répond,
    l'application y revient d'elle-même, sans redéploiement.
    """
    RETRY_MIN = 20.0        # délai minimal entre deux tentatives de rebranchement

    def __init__(self, dsn, chemin_json):
        self._dsn = dsn
        self._pg = None
        self._json = _JsonStore(chemin_json)
        self._lock = threading.Lock()
        self._last_try = 0.0
        self._connecting = False
        # Cause du dernier échec de connexion. Elle n'était nulle part : quand
        # la connexion se refusait, /health annonçait « repli_fichier » sans
        # dire POURQUOI, et il fallait aller lire les journaux de l'hébergeur
        # pour distinguer une base endormie d'une URL périmée. Un diagnostic
        # qu'on ne peut pas consulter depuis dehors ne sert qu'à celui qui a
        # déjà les journaux sous les yeux.
        self._derniere_erreur = ""
        self._derniere_erreur_le = 0.0
        if dsn:
            self._connecter_en_fond()

    # -- connexion ---------------------------------------------------------
    def _connecter_en_fond(self):
        with self._lock:
            if self._connecting or self._pg is not None:
                return
            self._connecting = True
            self._last_try = time.time()
        threading.Thread(target=self._essayer, daemon=True).start()

    def _essayer(self):
        erreur = ""
        try:
            pg = _PgStore(self._dsn)
        except Exception as exc:
            logging.getLogger("auth").warning(
                "comptes : PostgreSQL injoignable (%s) — repli fichier, "
                "nouvelle tentative dans %ds.", type(exc).__name__, int(self.RETRY_MIN))
            # /health est PUBLIC : on n'y recopie pas le message brut, qui
            # contient l'hôte et le port de la base. On le CLASSE en une cause
            # actionnable — ce qui est de toute façon plus utile qu'une trace,
            # puisque ce qu'on veut savoir est quoi faire ensuite.
            erreur = _classer_erreur_base(exc)
            pg = None
        with self._lock:
            self._connecting = False
            if pg is not None:
                self._pg = pg
                self._derniere_erreur = ""
                logging.getLogger("auth").info("comptes : PostgreSQL connecté.")
            else:
                self._derniere_erreur = erreur
                self._derniere_erreur_le = time.time()

    def _actif(self):
        """Magasin à utiliser maintenant, en relançant une tentative si l'heure
        est venue. La tentative est asynchrone : elle ne retarde jamais la
        requête en cours.

        Quand un DATABASE_URL est configuré et que la base ne répond pas, on
        LÈVE plutôt que de servir le fichier de repli. Ce fichier est une copie
        d'ombre que personne ne tient à jour : y authentifier reviendrait à
        accepter un compte peut-être révoqué depuis, et — le fichier étant vide
        sur l'hébergement — à répondre « identifiants incorrects » à quelqu'un
        dont le mot de passe est parfaitement valide. Mieux vaut dire la vérité :
        la base est injoignable. Le fichier ne sert donc qu'en l'ABSENCE totale
        de base configurée (poste de développement)."""
        if self._pg is not None:
            return self._pg
        if self._dsn:
            if (time.time() - self._last_try) > self.RETRY_MIN:
                self._connecter_en_fond()
            raise ComptesIndisponibles(
                "base de comptes injoignable (rebranchement automatique en cours)")
        return self._json

    @property
    def mode(self):
        return "postgres" if self._pg is not None else ("repli_fichier" if self._dsn
                                                        else "fichier")

    def etat(self):
        """État lisible depuis /health, CAUSE COMPRISE.

        Quand plus personne ne peut se connecter — administrateur inclus — le
        diagnostic ne doit pas être derrière la connexion. Ces champs disent
        s'il faut attendre (la base se réveille), vérifier DATABASE_URL (URL
        périmée ou base supprimée), ou libérer des connexions."""
        pg = self._pg is not None
        return {
            "mode": self.mode,
            "persistant": pg or not self._dsn,
            "base_configuree": bool(self._dsn),
            "cause": "" if pg else (self._derniere_erreur or
                                    ("connexion en cours" if self._connecting else "")),
            "prochain_essai_s": (0 if pg or not self._dsn else
                                 max(0, int(self.RETRY_MIN - (time.time() - self._last_try)))),
        }

    def reconnecter(self):
        """Tentative immédiate et SYNCHRONE (bouton d'administration)."""
        with self._lock:
            self._pg = None
            self._last_try = time.time()
        self._essayer()
        return self._pg is not None

    # -- délégation --------------------------------------------------------
    def _appel(self, methode, *args, **kwargs):
        """Exécute sur le magasin actif ; si PostgreSQL échoue en cours de route,
        on le lâche (une nouvelle connexion sera tentée) et on relaie l'erreur.

        La NATURE de l'erreur relayée compte. Une connexion coupée et une
        requête fautive n'appellent pas la même réponse : la première est une
        indisponibilité passagère, à annoncer comme telle et à réessayer ; la
        seconde est un défaut du code, qui doit rester visible en 500 et dans
        les journaux. Confondre les deux, c'est soit habiller un bug en
        « réessayez dans un instant » — et il ne sera jamais corrigé —, soit
        faire passer une base endormie pour une panne du site.

        Seules les erreurs de CONNEXION sont donc traduites en
        ComptesIndisponibles. Tout le reste remonte intact."""
        cible = self._actif()          # peut lever ComptesIndisponibles
        try:
            return getattr(cible, methode)(*args, **kwargs)
        except Exception as exc:
            connexion_perdue = False
            if cible is self._pg:
                with self._lock:
                    self._pg = None
                    self._last_try = 0.0        # rebranchement au prochain accès
                try:
                    import psycopg
                    connexion_perdue = isinstance(
                        exc, (psycopg.OperationalError, psycopg.InterfaceError))
                except Exception:               # noqa: BLE001
                    connexion_perdue = False
            if connexion_perdue:
                logging.getLogger("auth").warning(
                    "comptes : connexion perdue pendant « %s » — %s", methode,
                    _classer_erreur_base(exc))
                raise ComptesIndisponibles(
                    "base de comptes injoignable (connexion perdue en cours de requête)"
                ) from exc
            raise

    def get(self, email):
        return self._appel("get", email)

    def get_by(self, field, value):
        return self._appel("get_by", field, value)

    def create(self, user):
        return self._appel("create", user)

    def update(self, email, **fields):
        return self._appel("update", email, **fields)

    def delete(self, email):
        return self._appel("delete", email)

    def list_all(self):
        return self._appel("list_all")


def _make_store():
    dsn = (os.environ.get("DATABASE_URL") or "").strip()
    if dsn.startswith("postgres://"):
        dsn = "postgresql://" + dsn[len("postgres://"):]
    return _ResilientUserStore(dsn, os.path.join(HERE, "users_db.json"))


store = _make_store()


# ---------------------------------------------------------------------- emails --
def send_email(to_email, to_name, subject, html):
    key = os.environ.get("BREVO_API_KEY")
    if not key:
        import logging
        logging.getLogger("auth").warning("BREVO_API_KEY absente — email non envoyé : %s", subject)
        return False
    try:
        r = requests.post(BREVO_API_URL, timeout=12,
                          headers={"api-key": key, "accept": "application/json",
                                   "content-type": "application/json"},
                          json={"sender": SENDER, "to": [{"email": to_email, "name": to_name or to_email}],
                                "subject": subject, "htmlContent": html})
        return r.status_code in (200, 201)
    except requests.RequestException:
        return False


def _shell(title, body):
    return (
        '<div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:0 auto;'
        'color:#1c2530;background:#f5f8fb;border-radius:14px;overflow:hidden;border:1px solid #e2e8f0">'
        '<div style="background:linear-gradient(135deg,#0f7a86,#12a3b3);padding:22px 28px;color:#fff">'
        '<div style="font-weight:800;font-size:18px;letter-spacing:-.01em">CONSEILPREV <span style="opacity:.8">Cyber</span></div></div>'
        '<div style="padding:26px 28px">'
        '<h1 style="font-size:19px;margin:0 0 14px">%s</h1>%s'
        '<p style="margin-top:26px;color:#8a9ab0;font-size:12px">Cybersécurité industrielle IT / OT / IIoT — '
        'ce message est automatique, merci de ne pas y répondre.</p></div></div>' % (title, body))


def _btn(url, label):
    return ('<p style="margin:20px 0"><a href="%s" style="background:#12a3b3;color:#fff;text-decoration:none;'
            'padding:12px 22px;border-radius:8px;font-weight:600;display:inline-block">%s</a></p>'
            '<p style="color:#8a9ab0;font-size:12px;word-break:break-all">Ou copiez ce lien : %s</p>' % (url, label, url))


def _send_verify(user, base=None):
    base = base or _base_url()
    url = "%s/verifier-email/%s" % (base, user["verify_token"])
    # CE QUE LE COURRIEL PROMET DOIT EXISTER SUR CE SERVEUR-LÀ. La phrase sur
    # le règlement en ligne n'est écrite QUE si le paiement est réellement
    # configuré : annoncer une porte qui n'existe pas coûte plus cher qu'un
    # délai d'attente annoncé franchement.
    suite = ("Ce lien est valable %d heures. Après confirmation, votre accès "
             "sera validé par notre équipe." % VERIFY_VALIDITY_H)
    try:
        import paiement
        if paiement.configure():
            suite = ("Ce lien est valable %d heures. Après confirmation, votre "
                     "accès sera validé par notre équipe — ou vous pourrez "
                     "l'ouvrir immédiatement en réglant en ligne, depuis la "
                     "page de connexion." % VERIFY_VALIDITY_H)
    except Exception:
        pass
    send_email(user["email"], user["name"], "Confirmez votre adresse email — CONSEILPREV Cyber",
               _shell("Confirmez votre email",
                      "<p>Bonjour %s,</p><p>Pour finaliser votre demande d'accès au cockpit CONSEILPREV Cyber, "
                      "confirmez votre adresse email :</p>%s<p>%s</p>"
                      % (html_lib.escape(user["name"] or ""), _btn(url, "Confirmer mon email"), suite)))


def _notify_admin(user, base=None):
    # name/org/email SONT ÉCRITS PAR LE DEMANDEUR, et n'arrivent ici qu'après
    # confirmation de l'adresse — pas après approbation. Non échappés, ils
    # inséreraient du HTML de son choix dans le courriel adressé à
    # l'administrateur, au-dessus du vrai bouton « Approuver cet accès ».
    base = base or _base_url()
    url = "%s/admin/approuver/%s" % (base, user["approve_token"])
    nom = html_lib.escape(user["name"] or "—")
    org = html_lib.escape(user["org"] or "—")
    email = html_lib.escape(user["email"])
    send_email(ADMIN_EMAIL, "Admin",
               "Accès à approuver (adresse confirmée) — %s" % user["email"],
               _shell("Nouvelle demande d'accès",
                      "<p>Une demande de compte a été déposée, et "
                      "<b>l'adresse a été confirmée</b> par son titulaire :</p>"
                      "<ul><li><b>Nom :</b> %s</li><li><b>Organisation :</b> %s</li>"
                      "<li><b>Email :</b> %s</li></ul>"
                      "<p>Il ne manque que votre accord pour ouvrir l'accès :</p>%s"
                      "<p style=\"color:#8a9ab0;font-size:12px\">Ce lien est valable "
                      "%d jours. Passé ce délai, l'approbation se fait depuis la page "
                      "d'administration : <a href=\"%s/admin/comptes\">%s/admin/comptes</a></p>"
                      % (nom, org, email,
                         _btn(url, "Approuver cet accès"),
                         APPROVE_VALIDITY_H // 24, base, base)))


def _send_approved(user, base=None):
    base = base or _base_url()
    url = "%s/connexion" % base
    send_email(user["email"], user["name"], "Votre accès cockpit est activé — CONSEILPREV Cyber",
               _shell("Accès activé",
                      "<p>Bonjour %s,</p><p>Votre accès au cockpit de supervision CONSEILPREV Cyber a été "
                      "<b>approuvé</b>. Vous pouvez maintenant vous connecter :</p>%s"
                      % (html_lib.escape(user["name"] or ""), _btn(url, "Se connecter"))))


def _send_reset(user, base=None):
    base = base or _base_url()
    url = "%s/reinitialiser/%s" % (base, user["reset_token"])
    send_email(user["email"], user["name"], "Réinitialisation de votre mot de passe — CONSEILPREV Cyber",
               _shell("Réinitialiser le mot de passe",
                      "<p>Vous avez demandé à réinitialiser votre mot de passe. Ce lien est valable %d heures :</p>"
                      "%s<p>Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.</p>"
                      % (RESET_VALIDITY_H, _btn(url, "Choisir un nouveau mot de passe"))))


# ------------------------------------------------------------------- sessions ---
# Dernier profil lu avec succès, par email. Sert UNIQUEMENT de filet quand la
# base devient injoignable en cours de vie : sans lui, la moindre coupure faisait
# lever current_user(), et TOUTE page authentifiée répondait 500 — le site
# entier paraissait planté alors que seule la base hoquetait.
# La validité est volontairement courte : pendant une panne, un compte
# fraîchement révoqué reste accepté au plus quelques minutes. C'est le prix,
# assumé et borné, pour ne pas transformer un incident de base en panne totale.
_USER_CACHE = {}
_USER_CACHE_TTL = reglages.reel("AUTH_CACHE_TTL", 300, mini=0)


def current_user():
    email = session.get("user_email")
    if not email:
        return None
    try:
        u = store.get(email)
        if u:
            _USER_CACHE[email] = (time.time(), dict(u))
        else:
            _USER_CACHE.pop(email, None)
    except Exception:
        # Base injoignable : on repart du dernier profil connu, s'il est récent.
        logging.getLogger("auth").warning(
            "comptes : base injoignable — profil en cache pour la session en cours.")
        cached = _USER_CACHE.get(email)
        if not cached or (time.time() - cached[0]) > _USER_CACHE_TTL:
            return None
        u = cached[1]
    if not u or not (u.get("email_verified") and u.get("approved")):
        return None
    return u


def comptes_requis(f):
    """Traduit une base de comptes injoignable en refus LISIBLE, pas en 500.

    Le constat qui a motivé ce décorateur : sur les neuf routes du système de
    comptes, une seule — la connexion — savait quoi dire quand la base ne
    répondait pas. Les huit autres laissaient l'exception remonter, et
    l'utilisateur lisait « Le serveur a rencontré une erreur ». C'est faux sur
    le fond : le serveur va très bien, c'est la base qui dort. Et c'est nuisible
    en pratique — « erreur serveur » invite à signaler une panne, « base
    momentanément injoignable, réessayez » invite à réessayer, ce qui suffit
    presque toujours.

    Un 503 est ici plus qu'une convention : il porte Retry-After, que les
    navigateurs et les sondes savent lire, là où un 500 dit « n'insistez pas ».
    """
    @functools.wraps(f)
    def wrap(*a, **k):
        try:
            return f(*a, **k)
        except ComptesIndisponibles as exc:
            logging.getLogger("auth").warning(
                "comptes injoignables sur %s : %s", request.path, exc)
            if request.path.startswith("/api/"):
                rep = jsonify(ok=False, error="comptes_indisponibles",
                              message="Base de comptes momentanément injoignable. "
                                      "Réessayez dans un instant.")
            else:
                rep = make_response(send_from_directory(HERE, "base-injoignable.html"))
            rep.status_code = 503
            rep.headers["Retry-After"] = "30"
            return rep
    return wrap


def login_required(f):
    @functools.wraps(f)
    def wrap(*a, **k):
        if not current_user():
            if request.path.startswith("/api/"):
                return jsonify(error="Authentification requise."), 401
            return redirect("/connexion?next=" + request.path)
        return f(*a, **k)
    wrap.auth_gated = True  # repère : page protégée (exclue du sitemap public)
    return wrap


def admin_required(f):
    @functools.wraps(f)
    def wrap(*a, **k):
        # Couche 1 — portail mot de passe (actif seulement si ADMIN_GATE_PASSWORD
        # est défini). Précède la connexion par compte : double sécurité.
        if ADMIN_GATE_PASSWORD and not session.get("admin_gate_ok"):
            if request.path.startswith("/api/"):
                return jsonify(error="Portail administrateur verrouillé."), 401
            return redirect("/admin/acces?next=" + request.path)
        # Couche 2 — compte administrateur (e-mail + mot de passe, rôle admin).
        u = current_user()
        if not u:
            if request.path.startswith("/api/"):
                return jsonify(error="Authentification requise."), 401
            return redirect("/connexion?next=" + request.path)
        if (u.get("role") or "user") != "admin":
            if request.path.startswith("/api/"):
                return jsonify(error="Accès réservé à l'administrateur."), 403
            # UN REFUS N'EST PAS UN CUL-DE-SAC. Ici, quelqu'un EST connecté —
            # ce n'est simplement pas l'administrateur. Ce qui était rendu était
            # un fragment HTML nu : pas de feuille de style, pas d'en-tête, et
            # surtout pas le tiroir de `nav.js` qui porte le bouton
            # « Déconnexion ». Or `/connexion` renvoie AILLEURS tout visiteur
            # déjà connecté (voir `page_login`) : il n'existait donc, depuis
            # cette page, aucun chemin visible pour changer de compte. Le cas
            # n'est pas théorique — l'exploitant qui tient un compte de recette
            # sur son propre site tombe dessus dès qu'il ouvre /admin sans
            # avoir quitté ce compte, et rien ne lui dit lequel il porte.
            #
            # LE CODE NE CHANGE PAS : 403. La politique d'accès et ses essais
            # lisent un refus ; une page d'administration qui répondrait 302
            # vers une page publique serait plus difficile à auditer.
            rep = _page("acces-administrateur.html")
            rep.status_code = 403
            # NE JAMAIS METTRE CE CORPS EN CACHE. Il est servi SOUS l'adresse
            # demandée : mémorisé pour `/admin`, il se réafficherait après une
            # connexion réussie en administrateur, et le refus survivrait à sa
            # propre cause.
            rep.headers["Cache-Control"] = "no-store"
            return rep
        return f(*a, **k)
    wrap.auth_gated = True   # repère : page protégée (exclue du sitemap public)
    wrap.admin_gated = True  # repère PLUS FIN que auth_gated (que login_required
    # pose aussi) : seul lui distingue « exige une session » de « exige le rôle
    # admin ». Sans ce second repère, la politique d'accès (acces.py) ne pouvait
    # lire sur le décorateur QUE « protégée », jamais « protégée par admin » —
    # et se rabattait sur le préfixe /admin de l'URL, qu'un oubli de décorateur
    # ne contredit jamais.
    return wrap


# -------------------------------------------------------------------- captcha ---
def _new_captcha(slot):
    a, b = secrets.randbelow(8) + 2, secrets.randbelow(8) + 2
    session["cap_%s" % slot] = a + b
    return "%d + %d = ?" % (a, b)


def _check_captcha(slot, answer):
    try:
        return int(answer) == session.get("cap_%s" % slot)
    except (ValueError, TypeError):
        return False


def _safe_next(value, default):
    """N'autorise qu'un chemin INTERNE (anti open-redirect).

    LE DÉFAUT CORRIGÉ. `next` revenait tel quel dans un redirect() : une
    adresse absolue (`https://evil.example/...`) ou une adresse protocole-
    relative (`//evil.example/...`, que le navigateur résout comme externe)
    partait telle quelle. Un lien /connexion?next=... envoyé à un client déjà
    connecté l'expédiait hors du site en un seul saut, DEPUIS le domaine
    légitime — et pour qui n'est pas connecté, la connexion réussit d'abord,
    sur la vraie page, avant l'envoi vers la copie de l'attaquant.

    Un seul « / » en tête, jamais deux : "/x" passe, "//evil.example" et
    "/\\evil.example" (que certains navigateurs traitent comme "//") non.
    """
    nxt = value or default
    if not nxt.startswith("/") or nxt.startswith("//") or nxt.startswith("/\\"):
        return default
    return nxt


# --------------------------------------------------------------------- routes ---
# ── LES PAGES SERVIES D'ICI, ET LEUR POLITIQUE DE CONTENU ────────────────
# Elles ne passent pas par `_serve_fast` : sans ce passage, elles recevraient
# la politique GLOBALE, qui n'admet plus l'exécution des scripts intégrés — et
# la page de connexion tomberait le jour du déploiement, sans erreur serveur,
# sans rien dans les journaux. Cinq des sept en portent un.
#
# L'empreinte est prise sur le FICHIER TEL QUEL : contrairement au chemin
# rapide, aucune transformation n'est appliquée ici, et c'est bien ce
# fichier-là que le navigateur reçoit.
def _page(nom):
    rep = make_response(send_from_directory(HERE, nom))
    try:
        import csp
        with open(os.path.join(HERE, nom), "rb") as fh:
            rep.headers["Content-Security-Policy"] = csp.pour(fh.read())
    except (OSError, ImportError):
        # Une politique absente laisse s'appliquer la globale : la page se
        # dégrade, elle ne s'ouvre pas davantage.
        pass
    return rep


@auth_bp.route("/connexion")
def page_login():
    if current_user():
        return redirect(_safe_next(request.args.get("next"), "/demo"))
    return _page("connexion.html")


def _safe_admin_next(value):
    """N'autorise qu'un chemin interne de la zone admin (anti open-redirect)."""
    nxt = _safe_next(value, "/admin")
    if not nxt.startswith("/admin") or nxt.startswith("/admin/acces"):
        return "/admin"
    return nxt


_ADMIN_GATE_TEMPLATE = (
    "<!doctype html><html lang=\"fr\"><head><meta charset=\"utf-8\">"
    "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
    "<title>Accès administrateur — CONSEILPREV Cyber</title>"
    "<meta name=\"robots\" content=\"noindex,nofollow\">"
    "<link rel=\"icon\" href=\"/emblem.svg\" type=\"image/svg+xml\">"
    "<link rel=\"stylesheet\" href=\"/styles.css\">"
    "<style>"
    "body{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}"
    ".gate{width:100%;max-width:384px;background:linear-gradient(180deg,var(--panel),var(--bg2));"
    "border:1px solid var(--line);border-radius:16px;padding:30px 28px}"
    ".gate .em{display:flex;align-items:center;gap:9px;margin-bottom:20px;font-weight:700;color:var(--ink)}"
    ".gate h1{font-size:19px;margin:0 0 5px}"
    ".gate .sub{font-size:13px;color:var(--muted2);margin:0 0 20px}"
    ".gate label{display:block;font-family:var(--mono);font-size:11px;letter-spacing:.08em;"
    "text-transform:uppercase;color:var(--muted2);margin-bottom:7px}"
    ".gate input{width:100%;padding:12px 13px;border-radius:10px;border:1px solid var(--line);"
    "background:rgba(0,0,0,.18);color:var(--ink);font-size:15px;box-sizing:border-box}"
    ".gate input:focus{outline:2px solid var(--cyan);outline-offset:1px;border-color:var(--cyan)}"
    ".gate button{width:100%;margin-top:16px;padding:12px;border:none;border-radius:10px;cursor:pointer;"
    "font-weight:700;font-size:14px;color:#04121A;background:linear-gradient(135deg,var(--cyan),var(--teal))}"
    ".gate .err{color:var(--danger);font-size:12.5px;margin-top:13px}"
    ".gate .nb{font-size:11.5px;color:var(--muted2);margin-top:18px;border-top:1px solid var(--line);padding-top:13px}"
    "</style></head><body>"
    "<form class=\"gate\" method=\"post\" action=\"/admin/acces\" autocomplete=\"off\">"
    "<div class=\"em\"><img src=\"/emblem.svg\" width=\"26\" height=\"26\" alt=\"\">CONSEILPREV"
    " <span style=\"opacity:.6\">Cyber</span></div>"
    "<h1>Accès administrateur</h1>"
    "<p class=\"sub\">Zone réservée. Saisissez le mot de passe d'accès.</p>"
    "<label for=\"pw\">Mot de passe d'accès</label>"
    "<input id=\"pw\" name=\"password\" type=\"password\" autofocus required autocomplete=\"current-password\">"
    "<input type=\"hidden\" name=\"next\" value=\"__NEXT__\">"
    "<button type=\"submit\">Continuer →</button>"
    "__ERR__"
    "<div class=\"nb\">Une connexion par compte administrateur sera ensuite demandée.</div>"
    "</form></body></html>"
)


def _admin_gate_html(nxt, error):
    esc = (nxt or "/admin").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
    err = ('<div class="err">' + error + '</div>') if error else ""
    return _ADMIN_GATE_TEMPLATE.replace("__NEXT__", esc).replace("__ERR__", err)


@auth_bp.route("/admin/acces", methods=["GET", "POST"])
def admin_gate():
    """Portail mot de passe (1re couche) devant la zone /admin."""
    nxt = _safe_admin_next(request.values.get("next"))
    # Portail non configuré : ne pas ajouter de couche (le compte protège déjà).
    if not ADMIN_GATE_PASSWORD:
        return redirect(nxt)
    if session.get("admin_gate_ok"):
        return redirect(nxt)
    error = ""
    if request.method == "POST":
        key = "admingate:%s" % _client_ip()
        if guard.blocked(key):
            error = "Trop de tentatives. Réessayez dans quelques minutes."
        elif secrets.compare_digest(request.form.get("password") or "", ADMIN_GATE_PASSWORD):
            guard.clear(key)
            session["admin_gate_ok"] = True
            # Franchi et daté. Le compteur d'échecs vit en mémoire, par
            # processus : perdu au redémarrage, invisible d'un worker à
            # l'autre. Le journal, lui, permet de VOIR une campagne de force
            # brute sur la porte qui protège toute la zone d'administration —
            # l'IP anonymisée y est ajoutée d'office.
            _tracer("admin_gate.ok", "")
            return redirect(nxt)
        else:
            guard.fail(key)
            _tracer("admin_gate.echec", "", ok=False)
            error = "Mot de passe incorrect."
    return Response(_admin_gate_html(nxt, error), mimetype="text/html")


@auth_bp.route("/inscription")
def page_register():
    return _page("inscription.html")


@auth_bp.route("/mot-de-passe-oublie")
def page_forgot():
    return _page("mot-de-passe-oublie.html")


@auth_bp.route("/api/auth/captcha")
def api_captcha():
    return jsonify(question=_new_captcha("reg"))


@auth_bp.route("/api/auth/register", methods=["POST"])
@comptes_requis
def api_register():
    d = request.get_json(silent=True) or {}
    # Anti-abus : limite les demandes d'inscription par IP (anti-flood d'emails).
    rk = "register:%s" % _client_ip()
    if guard.blocked(rk, limit=8, window=900):
        return _refus_cadence("Trop de demandes. Réessayez dans quelques minutes.",
                              rk, limit=8, window=900)
    guard.fail(rk)
    email = (d.get("email") or "").strip().lower()[:200]
    name = (d.get("name") or "").strip()[:120]
    org = (d.get("org") or "").strip()[:160]
    pw = d.get("password") or ""
    if not _check_captcha("reg", d.get("captcha")):
        return jsonify(error="Réponse de vérification incorrecte."), 400
    if not valid_email(email):
        return jsonify(error="Adresse email invalide."), 400
    if not name:
        return jsonify(error="Nom requis."), 400
    ok, msg = password_strength(pw)
    if not ok:
        return jsonify(error=msg), 400
    # Réponse générique même si l'email existe déjà (anti-énumération).
    generic = jsonify(ok=True, message="Demande enregistrée. Vérifiez votre boîte mail pour confirmer votre email.")
    if store.get(email):
        return generic
    user = {
        "email": email, "name": name, "org": org,
        "password_hash": generate_password_hash(pw),
        "email_verified": False, "approved": False, "role": "user",
        "verify_token": secrets.token_urlsafe(32),
        "verify_expire": _now_ms() + VERIFY_VALIDITY_H * 3600 * _MS,
        # PAS DE JETON D'APPROBATION TANT QUE L'ADRESSE N'EST PAS PROUVÉE. Il
        # est frappé à la confirmation, et pas avant — voir `verify_email`.
        "approve_token": None, "approve_expire": None,
        "reset_token": None, "reset_expire": None,
        "created_at": _now_ms(), "last_login": None,
    }
    if not store.create(user):
        return generic
    threading.Thread(target=_send_verify, args=(user, _base_url()), daemon=True).start()
    return generic


@auth_bp.route("/verifier-email/<token>")
@comptes_requis
def verify_email(token):
    u = store.get_by("verify_token", token)
    if not u or (u.get("verify_expire") or 0) < _now_ms():
        return _page("lien-expire.html")
    # L'ADMINISTRATEUR EST PRÉVENU ICI, ET NON À L'INSCRIPTION.
    #
    # Il l'était au dépôt de la demande, avec son lien d'approbation : n'importe
    # qui pouvait donc faire tomber dans sa boîte une demande portant l'adresse
    # d'un tiers, et le message lui-même le priait d'attendre une confirmation
    # que rien ne lui signalait. Il approuvait à l'aveugle — la connexion
    # refusait ensuite, faute d'adresse confirmée, mais le compte était marqué
    # approuvé et l'administrateur croyait avoir fait son travail.
    #
    # Prévenir à la confirmation change trois choses : l'adresse est prouvée
    # avant qu'on demande une décision, le lien reçu est immédiatement
    # utilisable, et une vague de fausses inscriptions ne remplit plus la boîte
    # de l'exploitant — seules les adresses réelles y arrivent.
    jeton = secrets.token_urlsafe(32)
    store.update(u["email"], email_verified=True, verify_token=None,
                 verify_expire=None, approve_token=jeton,
                 approve_expire=_now_ms() + APPROVE_VALIDITY_H * 3600 * _MS)
    u = dict(u, email_verified=True, approve_token=jeton)
    threading.Thread(target=_notify_admin, args=(u, _base_url()), daemon=True).start()
    return redirect("/connexion?verifie=1")


@auth_bp.route("/admin/approuver/<token>")
@comptes_requis
def admin_approve(token):
    # Le jeton fait 256 bits : il ne se devine pas. La limite de débit n'est
    # donc pas là contre la force brute, mais contre l'usage d'une route
    # ouverte comme oracle — et parce qu'une porte sans compteur ne se voit
    # pas s'ouvrir.
    rk = "approve:%s" % _client_ip()
    if guard.blocked(rk, limit=20, window=600):
        # Une page, pas du JSON — mais le même devoir : dire quand revenir.
        # `make_response` est le seul moyen de poser un en-tête sur un corps
        # rendu sous forme de chaîne.
        rep = make_response(
            "<meta charset='utf-8'><p style=\"font-family:Arial;text-align:center;"
            "margin-top:60px\">Trop de tentatives. Réessayez dans quelques minutes.</p>",
            429)
        rep.headers["Retry-After"] = str(guard.retry_after(rk, 20, 600))
        return rep
    guard.fail(rk)
    u = store.get_by("approve_token", token)
    if not u or (u.get("approve_expire") or 0) < _now_ms():
        # UN LIEN QUI NE MEURT JAMAIS SURVIT À LA BOÎTE QUI L'A REÇU. Passé le
        # délai, l'approbation reste possible depuis la page d'administration,
        # qui exige une session administrateur.
        return _page("lien-expire.html")
    if not u.get("email_verified"):
        # Ne devrait plus arriver — le jeton n'est frappé qu'à la confirmation —
        # mais un compte antérieur à ce changement porte encore un jeton frappé
        # à l'inscription. On refuse plutôt que d'approuver une adresse dont
        # personne n'a prouvé qu'elle appartient au demandeur.
        _tracer("compte.approbation.refus", u["email"],
                "adresse non confirmée", ok=False)
        return ("<meta charset='utf-8'><div style=\"font-family:Arial;max-width:520px;"
                "margin:60px auto;text-align:center;color:#1c2530\">"
                "<h1>Adresse non confirmée</h1><p>Le compte <b>%s</b> n'a pas encore "
                "confirmé son adresse. L'approuver maintenant ne lui ouvrirait rien : "
                "la connexion resterait refusée. Vous serez prévenu dès la "
                "confirmation.</p></div>" % html_lib.escape(u["email"])), 409
    store.update(u["email"], approved=True, approve_token=None, approve_expire=None)
    u["approved"] = True
    _tracer("compte.approbation", u["email"], "par lien d'approbation")
    threading.Thread(target=_send_approved, args=(u, _base_url()), daemon=True).start()
    return ("<meta charset='utf-8'><div style=\"font-family:Arial;max-width:520px;margin:60px auto;"
            "text-align:center;color:#1c2530\"><h1>✅ Accès approuvé</h1>"
            "<p>Le compte <b>%s</b> est activé. L'utilisateur a été prévenu par email.</p></div>"
            % html_lib.escape(u["email"]))


def payable(email):
    """Ce compte peut-il ouvrir une caisse ? (existe, confirmé, pas déjà ouvert)

    LA CONFIRMATION D'ADRESSE EST UNE CONDITION, exactement comme pour
    l'approbation manuelle : `admin_approve` refuse déjà d'approuver une
    adresse non confirmée parce que « l'approuver maintenant ne lui ouvrirait
    rien ». Encaisser un paiement pour un accès qui ne marchera pas serait pire
    encore — le client aurait payé.
    """
    try:
        u = store.get((email or "").strip().lower())
    except Exception:
        return None
    if not u or not u.get("email_verified") or u.get("approved"):
        return None
    return u


def ouvrir_par_paiement(email, base=None):
    """Ouvre l'accès après un paiement dont la signature a été vérifiée.

    APPELÉE UNIQUEMENT DEPUIS LA NOTIFICATION SIGNÉE. Il n'existe aucune route
    qui ouvre un accès : un client ne peut donc pas se promouvoir en appelant
    une adresse.

    IDEMPOTENTE, parce que Stripe REJOUE. Une notification est réémise jusqu'à
    ce qu'elle soit acquittée ; sans cette garde, le courriel d'activation
    partirait plusieurs fois pour un seul paiement. Rend True seulement quand
    l'ouverture a RÉELLEMENT eu lieu — l'appelant s'en sert pour ne notifier
    qu'une fois.
    """
    email = (email or "").strip().lower()
    u = store.get(email) if email else None
    if not u:
        # UNE ADRESSE INCONNUE N'EST PAS AVALÉE : un paiement encaissé pour un
        # compte introuvable doit laisser une trace, sans quoi il disparaît.
        _tracer("compte.paiement.inconnu", email,
                "paiement reçu pour une adresse absente du magasin", ok=False)
        return False
    if u.get("approved"):
        _tracer("compte.paiement.rejeu", email, "accès déjà ouvert")
        return False
    if not u.get("email_verified"):
        _tracer("compte.paiement.refus", email, "adresse non confirmée", ok=False)
        return False
    store.update(email, approved=True, approve_token=None, approve_expire=None)
    u["approved"] = True
    # LA VOIE D'OUVERTURE EST TRACÉE. Le filtre manuel du propriétaire disparaît
    # pour un compte payé : le registre doit au moins dire par où il est entré.
    _tracer("compte.approbation", email, "par paiement")
    threading.Thread(target=_send_approved, args=(u, base), daemon=True).start()
    threading.Thread(target=_avertir_ouverture_payee, args=(u, base),
                     daemon=True).start()
    return True


def _avertir_ouverture_payee(user, base=None):
    """Vous dire ce qui s'est RÉELLEMENT passé.

    Le courriel de demande d'accès dit « Il ne manque que votre accord ». Sur un
    compte ouvert par paiement, cette phrase serait fausse : l'accès est déjà
    ouvert, et vous n'avez rien accordé. On envoie donc un autre message, qui
    dit l'ouverture et rappelle où la reprendre.
    """
    base = base or _base_url()
    send_email(ADMIN_EMAIL, "Admin",
               "Accès ouvert par paiement — %s" % user["email"],
               _shell("Accès ouvert par paiement",
                      "<p>Un paiement a ouvert l'accès de <b>%s</b> "
                      "(%s, %s). <b>Vous n'avez rien à valider</b> : le compte "
                      "est déjà actif.</p><p>Pour le suspendre ou le "
                      "supprimer : <a href=\"%s/admin/comptes\">%s/admin/comptes</a></p>"
                      % (html_lib.escape(user["email"]),
                         html_lib.escape(user.get("name") or "—"),
                         html_lib.escape(user.get("org") or "—"), base, base)))


def _tracer(action, email, detail="", ok=True, role="-"):
    """Trace une tentative de connexion dans le journal d'audit.

    Import différé et enveloppé : la traçabilité ne doit jamais empêcher
    quelqu'un de se connecter, ni créer de dépendance circulaire avec app.py."""
    try:
        import audit
        audit.journaliser(action, cible=email, detail=detail, ok=ok,
                          acteur=email or "anonyme", role=role)
    except Exception:
        pass


@auth_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    pw = d.get("password") or ""
    key = "login:%s:%s" % (_client_ip(), email)
    if guard.blocked(key):
        return _refus_cadence("Trop de tentatives. Réessayez dans quelques minutes.",
                              key)
    # Lecture du compte TOLÉRANTE AUX PANNES. Auparavant, une base injoignable
    # faisait remonter l'exception telle quelle : le visiteur attendait le délai
    # du pool puis recevait un « erreur_serveur » opaque, qui laissait croire à
    # un problème d'identifiants ou à un site cassé. current_user() se protégeait
    # déjà ainsi ; la connexion, elle, était restée sans filet.
    depuis_cache = False
    try:
        u = store.get(email)
        if u:
            _USER_CACHE[email] = (time.time(), dict(u))
        else:
            _USER_CACHE.pop(email, None)
    except Exception:
        logging.getLogger("auth").warning(
            "connexion : base de comptes injoignable — repli sur le cache.")
        cached = _USER_CACHE.get(email)
        if not cached or (time.time() - cached[0]) > _USER_CACHE_TTL:
            # Rien de récent en mémoire : on le DIT, plutôt que de renvoyer
            # « identifiants incorrects » (faux, et qui ferait changer un mot de
            # passe pourtant valide) ou une erreur serveur (illisible).
            return jsonify(error="Base de comptes momentanément injoignable. "
                                 "Réessayez dans un instant."), 503
        # Le profil en cache porte les mêmes champs que la base — empreinte du
        # mot de passe comprise : la vérification reste entière, seule la
        # fraîcheur de la lecture est dégradée, et bornée par AUTH_CACHE_TTL.
        u = cached[1]
        depuis_cache = True
    if not u or not u.get("password_hash") or not check_password_hash(u["password_hash"], pw):
        guard.fail(key)
        _tracer("connexion.echec", email, "identifiants incorrects", ok=False)
        return jsonify(error="Identifiants incorrects."), 401
    if not u.get("email_verified"):
        _tracer("connexion.refus", email, "email non confirmé", ok=False)
        return jsonify(error="Confirmez d'abord votre email (lien reçu à l'inscription)."), 403
    if not u.get("approved"):
        _tracer("connexion.refus", email, "compte non validé", ok=False)
        return jsonify(error="Votre accès est en attente de validation par notre équipe."), 403
    guard.clear(key)
    session.clear()
    session["user_email"] = email
    session.permanent = True
    # Horodatage de dernière connexion : confort de suivi, jamais un motif
    # d'échec. Une écriture impossible ne doit pas annuler une authentification
    # déjà acquise.
    try:
        store.update(email, last_login=_now_ms())
    except Exception:
        logging.getLogger("auth").warning(
            "connexion : dernière connexion non enregistrée (base indisponible).")
    _tracer("connexion.reussie", email,
            "profil en cache (base injoignable)" if depuis_cache else "",
            role=u.get("role") or "user")
    return jsonify(ok=True, name=u.get("name") or "", degrade=depuis_cache)


@auth_bp.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify(ok=True)


@auth_bp.route("/api/auth/me")
def api_me():
    u = current_user()
    return jsonify(authenticated=bool(u), name=(u or {}).get("name") or "",
                   email=(u or {}).get("email") or "",
                   role=(u or {}).get("role") or "user")


@auth_bp.route("/api/auth/export")
@login_required
@comptes_requis
def api_export_compte():
    """Les données du compte connecté, en JSON téléchargeable — droit d'accès
    et portabilité (art. 15 et 20 RGPD).

    Le registre déclarait « export structuré et lisible par machine (JSON)
    des données d'un compte » — seule la fiche CLIENT avait une route, et
    réservée à l'administrateur. Un utilisateur connecté n'avait aucun moyen
    outillé d'obtenir SES données. Contenu : la vue publique du compte
    (jamais de hash ni de jeton) et les entrées du journal d'audit qui LE
    concernent — l'IP y est déjà anonymisée. L'exercice du droit est lui-même
    tracé, comme l'export d'une fiche client l'est déjà."""
    u = current_user()
    entrees = []
    try:
        import audit
        entrees = audit.lire(limit=200, acteur=u.get("email"))
    except Exception:
        entrees = []
    _tracer("compte.export", u.get("email") or "")
    corps = json.dumps({
        "compte": _public_user(u),
        "journal": entrees,
        "note": ("Export établi à la demande du titulaire du compte — "
                 "art. 15 (accès) et 20 (portabilité) du RGPD. Les adresses "
                 "IP du journal sont anonymisées à l'écriture."),
    }, ensure_ascii=False, indent=2)
    rep = Response(corps, mimetype="application/json")
    rep.headers["Content-Disposition"] = 'attachment; filename="mes-donnees.json"'
    rep.headers["Cache-Control"] = "no-store"
    return rep


@auth_bp.route("/api/auth/forgot", methods=["POST"])
@comptes_requis
def api_forgot():
    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()[:200]
    generic = jsonify(ok=True, message="Si un compte existe, un email de réinitialisation a été envoyé.")
    # Anti-abus : coupe l'email-bombing par IP (réponse générique, aucune fuite).
    fk = "forgot:%s" % _client_ip()
    if guard.blocked(fk, limit=6, window=900):
        return generic
    guard.fail(fk)
    if not valid_email(email):
        return generic
    u = store.get(email)
    if u and u.get("approved"):
        store.update(email, reset_token=secrets.token_urlsafe(32),
                     reset_expire=_now_ms() + RESET_VALIDITY_H * 3600 * _MS)
        _tracer("motdepasse.demande", email)
        u = store.get(email)
        threading.Thread(target=_send_reset, args=(u, _base_url()), daemon=True).start()
    return generic


@auth_bp.route("/reinitialiser/<token>")
@comptes_requis
def page_reset(token):
    u = store.get_by("reset_token", token)
    if not u or (u.get("reset_expire") or 0) < _now_ms():
        return _page("lien-expire.html")
    return _page("reinitialiser.html")


@auth_bp.route("/api/auth/reset", methods=["POST"])
@comptes_requis
def api_reset():
    d = request.get_json(silent=True) or {}
    # Anti-abus : limite les tentatives de réinitialisation par IP (anti-bruteforce de jeton).
    rk = "reset:%s" % _client_ip()
    if guard.blocked(rk, limit=10, window=900):
        return _refus_cadence("Trop de tentatives. Réessayez plus tard.",
                              rk, limit=10, window=900)
    guard.fail(rk)
    token = (d.get("token") or "").strip()
    pw = d.get("password") or ""
    ok, msg = password_strength(pw)
    if not ok:
        return jsonify(error=msg), 400
    u = store.get_by("reset_token", token)
    if not u or (u.get("reset_expire") or 0) < _now_ms():
        return jsonify(error="Lien invalide ou expiré."), 410
    store.update(u["email"], password_hash=generate_password_hash(pw),
                 reset_token=None, reset_expire=None)
    # LE geste classique de prise de contrôle d'un compte : sans trace, un
    # incident ne se date pas et ne se corrèle pas aux connexions. Le jeton,
    # lui, n'apparaît jamais au journal.
    _tracer("motdepasse.reinitialise", u["email"])
    return jsonify(ok=True)


# ------------------------------------------------------------ administration ---
def _public_user(u):
    """Vue « sûre » d'un utilisateur (jamais de hash ni de jetons)."""
    return {"email": u.get("email"), "name": u.get("name"), "org": u.get("org"),
            "email_verified": bool(u.get("email_verified")), "approved": bool(u.get("approved")),
            "role": u.get("role") or "user", "created_at": u.get("created_at"),
            "last_login": u.get("last_login")}


@auth_bp.route("/admin/comptes")
@admin_required
def page_admin_users():
    return _page("admin-comptes.html")


@auth_bp.route("/api/admin/users")
@admin_required
@comptes_requis
def api_admin_users():
    return jsonify(users=[_public_user(u) for u in store.list_all()])


@auth_bp.route("/api/admin/users/<path:email>", methods=["PATCH", "DELETE"])
@admin_required
@comptes_requis
def api_admin_user_update(email):
    email = (email or "").strip().lower()
    me = current_user()
    target = store.get(email)
    if not target:
        return jsonify(error="Compte introuvable."), 404
    # Garde-fou : l'admin ne peut ni se suspendre ni se supprimer lui-même.
    if email == me["email"]:
        return jsonify(error="Vous ne pouvez pas modifier votre propre compte ici."), 400

    if request.method == "DELETE":
        store.delete(email)
        return jsonify(ok=True)

    d = request.get_json(silent=True) or {}
    action = d.get("action")
    if action == "approve":
        store.update(email, approved=True, approve_token=None, approve_expire=None)
        u = store.get(email)
        threading.Thread(target=_send_approved, args=(u, _base_url()), daemon=True).start()
    elif action == "suspend":
        store.update(email, approved=False)
    elif action == "make_admin":
        store.update(email, role="admin")
    elif action == "make_user":
        store.update(email, role="user")
    else:
        return jsonify(error="Action inconnue."), 400
    return jsonify(ok=True, user=_public_user(store.get(email)))


def _bootstrap_admin():
    """Crée / promeut le compte admin depuis ADMIN_EMAIL (+ ADMIN_PASSWORD au 1er lancement).

    - Si le compte ADMIN_EMAIL existe : on s'assure qu'il a le rôle admin, ET
      qu'il peut effectivement entrer.
    - Sinon, si ADMIN_PASSWORD est défini : on le crée déjà vérifié + approuvé.

    LE PIÈGE QUI ENFERMAIT LE PROPRIÉTAIRE DEHORS. Cette fonction ne posait que
    le RÔLE. Or un compte créé par le formulaire public naît `email_verified` et
    `approved` à faux, et la connexion refuse dans les deux cas. Le propriétaire
    du site se retrouvait donc administrateur ET bloqué à la porte, sans recours :

      · il ne peut pas se valider lui-même — la page d'administration refuse
        explicitement de modifier son propre compte, et c'est une bonne règle ;
      · il ne peut pas atteindre cette page, puisqu'il faut être connecté ;
      · il ne lui restait que le lien d'approbation reçu par courriel, c'est-à-
        dire dépendre d'un envoi qui peut ne jamais arriver — SMTP non
        configuré, message en indésirables, adresse d'expédition refusée.

    Les deux verrous existent pour filtrer les VISITEURS, pas l'exploitant. Et
    ADMIN_EMAIL est une variable d'environnement : qui la contrôle contrôle déjà
    le déploiement. Les lever pour ce seul compte n'ouvre donc rien qui ne soit
    déjà ouvert, et referme un piège dont on ne sort pas seul.
    """
    email = (ADMIN_EMAIL or "").strip().lower()
    if not valid_email(email):
        return
    u = store.get(email)
    if u:
        manquants = {}
        if (u.get("role") or "user") != "admin":
            manquants["role"] = "admin"
        if not u.get("email_verified"):
            manquants["email_verified"] = True
        if not u.get("approved"):
            manquants["approved"] = True
        if manquants:
            store.update(email, **manquants)
            logging.getLogger("auth").info(
                "compte proprietaire remis en etat d'entrer : %s",
                ", ".join(sorted(manquants)))
        return
    pw = os.environ.get("ADMIN_PASSWORD")
    if not pw:
        return
    store.create({
        "email": email, "name": "Administrateur", "org": "CONSEILPREV",
        "password_hash": generate_password_hash(pw),
        "email_verified": True, "approved": True, "role": "admin",
        "verify_token": None, "verify_expire": None, "approve_token": None,
        "approve_expire": None, "reset_token": None, "reset_expire": None,
        "created_at": _now_ms(), "last_login": None,
    })


def init_app(app):
    """Configure la session et enregistre les routes d'authentification."""
    app.secret_key = (os.environ.get("FLASK_SECRET_KEY", "").strip()
                      or "cpcyber-dev-" + secrets.token_hex(16))
    app.config.update(
        SESSION_COOKIE_NAME="cpc_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # Cookie de session RÉSERVÉ À HTTPS PAR DÉFAUT.
        #
        # Auparavant l'attribut dépendait de PUBLIC_BASE_URL, une variable
        # facultative : non renseignée en production — c'est le cas ici, elle est
        # déclarée « sync: false » dans render.yaml — le cookie repartait sans
        # l'attribut Secure et pouvait donc voyager en clair. Un réglage de
        # confidentialité ne doit pas dépendre du fait qu'on ait pensé à définir
        # une variable : on inverse la charge, c'est sûr par défaut et il faut
        # une demande EXPLICITE pour l'assouplir (développement local en http).
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_NON_SECURISE", "") != "1",
        PERMANENT_SESSION_LIFETIME=7 * 24 * 3600,
    )
    app.register_blueprint(auth_bp)
    # Amorçage du compte admin EN TÂCHE DE FOND, et seulement une fois la base
    # réellement connectée. Deux raisons : le démarrage ne doit jamais attendre
    # la base (un service lent à démarrer fait échouer la sonde de l'hébergeur,
    # qui redémarre — et le cycle recommence) ; et créer l'admin dans le fichier
    # de repli, éphémère, donnerait un compte qui disparaît au déploiement
    # suivant tout en masquant le vrai problème.
    threading.Thread(target=_bootstrap_admin_differe, daemon=True).start()
    return login_required


def _bootstrap_admin_differe(essais=30, pause=4.0):
    """Attend que le magasin de comptes soit sur PostgreSQL (2 min au plus),
    puis amorce le compte administrateur. Sans base, on renonce en le disant."""
    for _ in range(essais):
        if getattr(store, "mode", "") == "postgres":
            try:
                _bootstrap_admin()
            except Exception:
                logging.getLogger("auth").exception("amorçage du compte admin impossible")
            return
        time.sleep(pause)
    logging.getLogger("auth").warning(
        "amorçage du compte admin abandonné : base de comptes toujours injoignable.")
