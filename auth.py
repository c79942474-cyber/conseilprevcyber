"""Authentification CONSEILPREV Cyber — inscription (validation admin) + connexion.

Inspiré du système de Sentinel : mots de passe hachés (werkzeug), sessions Flask,
captcha, protection anti-bruteforce, réponses anti-énumération, emails via Brevo.

Flux : inscription → l'utilisateur confirme son email → l'admin approuve (lien reçu
par email) → le compte peut se connecter. Les comptes non confirmés / non approuvés
ne peuvent pas se connecter. Seuls le cockpit et la supervision sont protégés ; le
contenu public reste ouvert.

Stockage : PostgreSQL si DATABASE_URL est défini (persistant), sinon fichier JSON local.
"""
import functools
import json
import os
import re
import secrets
import threading
import time
from datetime import datetime, timezone

import requests
from flask import (Blueprint, jsonify, redirect, request, send_from_directory, session)
from werkzeug.security import check_password_hash, generate_password_hash

HERE = os.path.dirname(os.path.abspath(__file__))
auth_bp = Blueprint("auth", __name__)

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "christophe.cerf@outlook.com")
SENDER = {"name": "CONSEILPREV Cyber", "email": "christophe.cerf@i-aes.com"}
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
VERIFY_VALIDITY_H = 48
RESET_VALIDITY_H = 2
_MS = 1000

# ---------------------------------------------------------------- utilitaires ---
def _now_ms():
    return int(time.time() * _MS)


def _base_url():
    return (os.environ.get("PUBLIC_BASE_URL") or request.url_root).rstrip("/")


def valid_email(email):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or ""))


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


guard = _RateGuard()


def _client_ip():
    xff = request.headers.get("X-Forwarded-For", "")
    return (xff.split(",")[0].strip() if xff else request.remote_addr) or "?"


# Alias public (réutilisé par app.py pour la limitation de débit du formulaire de contact).
client_ip = _client_ip


# ------------------------------------------------------------------- stockage ---
_FIELDS = ["email", "name", "org", "password_hash", "email_verified", "approved",
           "role", "verify_token", "verify_expire", "approve_token",
           "reset_token", "reset_expire", "created_at", "last_login"]


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

    def __init__(self, dsn):
        import psycopg
        import psycopg.rows
        from psycopg_pool import ConnectionPool
        sep = "&" if "?" in dsn else "?"
        self._pool = ConnectionPool(dsn + sep + "connect_timeout=5", min_size=1, max_size=3,
                                    kwargs={"autocommit": True, "row_factory": psycopg.rows.dict_row},
                                    timeout=8, open=True)
        try:
            self._init()
        except Exception:
            try:
                self._pool.close()
            except Exception:
                pass
            raise

    def _init(self):
        with self._pool.connection() as c:
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
                    approve_token TEXT,
                    reset_token TEXT, reset_expire BIGINT,
                    created_at BIGINT, last_login BIGINT)""")
            finally:
                c.execute("SELECT pg_advisory_unlock(%s)", (self._LOCK_KEY,))

    def get(self, email):
        with self._pool.connection() as c:
            return c.execute("SELECT * FROM users WHERE email=%s", ((email or "").lower(),)).fetchone()

    def get_by(self, field, value):
        with self._pool.connection() as c:
            return c.execute("SELECT * FROM users WHERE %s=%%s" % field, (value,)).fetchone()

    def create(self, user):
        cols = [k for k in _FIELDS if k in user]
        ph = ", ".join(["%s"] * len(cols))
        with self._pool.connection() as c:
            try:
                c.execute("INSERT INTO users (%s) VALUES (%s)" % (", ".join(cols), ph),
                          tuple(user[k] for k in cols))
                return True
            except Exception:
                return False

    def update(self, email, **fields):
        sets = ", ".join("%s=%%s" % k for k in fields)
        with self._pool.connection() as c:
            c.execute("UPDATE users SET %s WHERE email=%%s" % sets,
                      tuple(fields.values()) + (email,))
            return True

    def delete(self, email):
        with self._pool.connection() as c:
            c.execute("DELETE FROM users WHERE email=%s", (email,))
            return True

    def list_all(self):
        with self._pool.connection() as c:
            return c.execute("SELECT * FROM users ORDER BY created_at DESC NULLS LAST").fetchall()


def _make_store():
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        if dsn.startswith("postgres://"):
            dsn = "postgresql://" + dsn[len("postgres://"):]
        try:
            return _PgStore(dsn)
        except Exception:
            import logging
            logging.getLogger("auth").warning("users: PostgreSQL injoignable — repli fichier JSON.")
    return _JsonStore(os.path.join(HERE, "users_db.json"))


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


def _send_verify(user):
    url = "%s/verifier-email/%s" % (_base_url(), user["verify_token"])
    send_email(user["email"], user["name"], "Confirmez votre adresse email — CONSEILPREV Cyber",
               _shell("Confirmez votre email",
                      "<p>Bonjour %s,</p><p>Pour finaliser votre demande d'accès au cockpit CONSEILPREV Cyber, "
                      "confirmez votre adresse email :</p>%s<p>Ce lien est valable %d heures. Après confirmation, "
                      "votre accès sera validé par notre équipe.</p>"
                      % (user["name"] or "", _btn(url, "Confirmer mon email"), VERIFY_VALIDITY_H)))


def _notify_admin(user):
    url = "%s/admin/approuver/%s" % (_base_url(), user["approve_token"])
    send_email(ADMIN_EMAIL, "Admin",
               "Nouvelle demande d'accès cockpit — %s" % user["email"],
               _shell("Nouvelle demande d'accès",
                      "<p>Une demande de compte a été déposée :</p>"
                      "<ul><li><b>Nom :</b> %s</li><li><b>Organisation :</b> %s</li>"
                      "<li><b>Email :</b> %s</li></ul>"
                      "<p>Après confirmation de son email par l'utilisateur, approuvez l'accès :</p>%s"
                      "<p style=\"color:#8a9ab0;font-size:12px\">Gérer tous les comptes : "
                      "<a href=\"%s/admin/comptes\">%s/admin/comptes</a></p>"
                      % (user["name"] or "—", user["org"] or "—", user["email"],
                         _btn(url, "Approuver cet accès"), _base_url(), _base_url())))


def _send_approved(user):
    url = "%s/connexion" % _base_url()
    send_email(user["email"], user["name"], "Votre accès cockpit est activé — CONSEILPREV Cyber",
               _shell("Accès activé",
                      "<p>Bonjour %s,</p><p>Votre accès au cockpit de supervision CONSEILPREV Cyber a été "
                      "<b>approuvé</b>. Vous pouvez maintenant vous connecter :</p>%s"
                      % (user["name"] or "", _btn(url, "Se connecter"))))


def _send_reset(user):
    url = "%s/reinitialiser/%s" % (_base_url(), user["reset_token"])
    send_email(user["email"], user["name"], "Réinitialisation de votre mot de passe — CONSEILPREV Cyber",
               _shell("Réinitialiser le mot de passe",
                      "<p>Vous avez demandé à réinitialiser votre mot de passe. Ce lien est valable %d heures :</p>"
                      "%s<p>Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.</p>"
                      % (RESET_VALIDITY_H, _btn(url, "Choisir un nouveau mot de passe"))))


# ------------------------------------------------------------------- sessions ---
def current_user():
    email = session.get("user_email")
    if not email:
        return None
    u = store.get(email)
    if not u or not (u.get("email_verified") and u.get("approved")):
        return None
    return u


def login_required(f):
    @functools.wraps(f)
    def wrap(*a, **k):
        if not current_user():
            if request.path.startswith("/api/"):
                return jsonify(error="Authentification requise."), 401
            return redirect("/connexion?next=" + request.path)
        return f(*a, **k)
    return wrap


def admin_required(f):
    @functools.wraps(f)
    def wrap(*a, **k):
        u = current_user()
        if not u:
            if request.path.startswith("/api/"):
                return jsonify(error="Authentification requise."), 401
            return redirect("/connexion?next=" + request.path)
        if (u.get("role") or "user") != "admin":
            if request.path.startswith("/api/"):
                return jsonify(error="Accès réservé à l'administrateur."), 403
            return "<meta charset='utf-8'><p style='font-family:Arial;margin:60px auto;max-width:480px;text-align:center'>Accès réservé à l'administrateur.</p>", 403
        return f(*a, **k)
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


# --------------------------------------------------------------------- routes ---
@auth_bp.route("/connexion")
def page_login():
    if current_user():
        return redirect(request.args.get("next") or "/demo")
    return send_from_directory(HERE, "connexion.html")


@auth_bp.route("/inscription")
def page_register():
    return send_from_directory(HERE, "inscription.html")


@auth_bp.route("/mot-de-passe-oublie")
def page_forgot():
    return send_from_directory(HERE, "mot-de-passe-oublie.html")


@auth_bp.route("/api/auth/captcha")
def api_captcha():
    return jsonify(question=_new_captcha("reg"))


@auth_bp.route("/api/auth/register", methods=["POST"])
def api_register():
    d = request.get_json(silent=True) or {}
    # Anti-abus : limite les demandes d'inscription par IP (anti-flood d'emails).
    rk = "register:%s" % _client_ip()
    if guard.blocked(rk, limit=8, window=900):
        return jsonify(error="Trop de demandes. Réessayez dans quelques minutes."), 429
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
        "approve_token": secrets.token_urlsafe(32),
        "reset_token": None, "reset_expire": None,
        "created_at": _now_ms(), "last_login": None,
    }
    if not store.create(user):
        return generic
    threading.Thread(target=_send_verify, args=(user,), daemon=True).start()
    threading.Thread(target=_notify_admin, args=(user,), daemon=True).start()
    return generic


@auth_bp.route("/verifier-email/<token>")
def verify_email(token):
    u = store.get_by("verify_token", token)
    if not u or (u.get("verify_expire") or 0) < _now_ms():
        return send_from_directory(HERE, "lien-expire.html")
    store.update(u["email"], email_verified=True, verify_token=None, verify_expire=None)
    return redirect("/connexion?verifie=1")


@auth_bp.route("/admin/approuver/<token>")
def admin_approve(token):
    u = store.get_by("approve_token", token)
    if not u:
        return send_from_directory(HERE, "lien-expire.html")
    store.update(u["email"], approved=True, approve_token=None)
    u["approved"] = True
    threading.Thread(target=_send_approved, args=(u,), daemon=True).start()
    return ("<meta charset='utf-8'><div style=\"font-family:Arial;max-width:520px;margin:60px auto;"
            "text-align:center;color:#1c2530\"><h1>✅ Accès approuvé</h1>"
            "<p>Le compte <b>%s</b> est activé. L'utilisateur a été prévenu par email.</p></div>" % u["email"])


@auth_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    pw = d.get("password") or ""
    key = "login:%s:%s" % (_client_ip(), email)
    if guard.blocked(key):
        return jsonify(error="Trop de tentatives. Réessayez dans quelques minutes."), 429
    u = store.get(email)
    if not u or not u.get("password_hash") or not check_password_hash(u["password_hash"], pw):
        guard.fail(key)
        return jsonify(error="Identifiants incorrects."), 401
    if not u.get("email_verified"):
        return jsonify(error="Confirmez d'abord votre email (lien reçu à l'inscription)."), 403
    if not u.get("approved"):
        return jsonify(error="Votre accès est en attente de validation par notre équipe."), 403
    guard.clear(key)
    session.clear()
    session["user_email"] = email
    session.permanent = True
    store.update(email, last_login=_now_ms())
    return jsonify(ok=True, name=u.get("name") or "")


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


@auth_bp.route("/api/auth/forgot", methods=["POST"])
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
        u = store.get(email)
        threading.Thread(target=_send_reset, args=(u,), daemon=True).start()
    return generic


@auth_bp.route("/reinitialiser/<token>")
def page_reset(token):
    u = store.get_by("reset_token", token)
    if not u or (u.get("reset_expire") or 0) < _now_ms():
        return send_from_directory(HERE, "lien-expire.html")
    return send_from_directory(HERE, "reinitialiser.html")


@auth_bp.route("/api/auth/reset", methods=["POST"])
def api_reset():
    d = request.get_json(silent=True) or {}
    # Anti-abus : limite les tentatives de réinitialisation par IP (anti-bruteforce de jeton).
    rk = "reset:%s" % _client_ip()
    if guard.blocked(rk, limit=10, window=900):
        return jsonify(error="Trop de tentatives. Réessayez plus tard."), 429
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
    return send_from_directory(HERE, "admin-comptes.html")


@auth_bp.route("/api/admin/users")
@admin_required
def api_admin_users():
    return jsonify(users=[_public_user(u) for u in store.list_all()])


@auth_bp.route("/api/admin/users/<path:email>", methods=["PATCH", "DELETE"])
@admin_required
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
        store.update(email, approved=True, approve_token=None)
        u = store.get(email)
        threading.Thread(target=_send_approved, args=(u,), daemon=True).start()
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

    - Si le compte ADMIN_EMAIL existe : on s'assure qu'il a le rôle admin.
    - Sinon, si ADMIN_PASSWORD est défini : on le crée déjà vérifié + approuvé.
    """
    email = (ADMIN_EMAIL or "").strip().lower()
    if not valid_email(email):
        return
    u = store.get(email)
    if u:
        if (u.get("role") or "user") != "admin":
            store.update(email, role="admin")
        return
    pw = os.environ.get("ADMIN_PASSWORD")
    if not pw:
        return
    store.create({
        "email": email, "name": "Administrateur", "org": "CONSEILPREV",
        "password_hash": generate_password_hash(pw),
        "email_verified": True, "approved": True, "role": "admin",
        "verify_token": None, "verify_expire": None, "approve_token": None,
        "reset_token": None, "reset_expire": None,
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
        SESSION_COOKIE_SECURE=bool(os.environ.get("PUBLIC_BASE_URL", "").startswith("https")),
        PERMANENT_SESSION_LIFETIME=7 * 24 * 3600,
    )
    app.register_blueprint(auth_bp)
    try:
        _bootstrap_admin()
    except Exception:
        import logging
        logging.getLogger("auth").exception("bootstrap admin impossible")
    return login_required
