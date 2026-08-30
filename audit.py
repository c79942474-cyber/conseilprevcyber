"""Journal d'audit des actions d'administration — traçabilité.

Le site journalisait déjà les opérations sur les fiches clients (obligation RGPD,
voir clients_store) mais RIEN sur l'administration elle-même : qui s'est connecté,
qui a chargé, supprimé ou rendu public un document, qui a purgé la base. Après
coup, il était impossible de répondre à « qui a fait ça, et quand ».

Principes tenus ici :
  - AJOUT SEUL. Aucune route ne modifie ni ne supprime une entrée : un journal
    qu'on peut réécrire ne prouve rien. La purge automatique ne retire que les
    entrées les plus anciennes, au-delà du plafond.
  - JAMAIS BLOQUANT. Une écriture de journal impossible ne doit pas faire échouer
    l'action de l'administrateur — on journalise l'échec et on continue.
  - AUCUN SECRET. On enregistre l'acteur, l'action, la cible et une adresse IP
    tronquée ; jamais de mot de passe, de jeton ni de contenu de document.
  - PSEUDONYMISATION DE L'IP. Le dernier octet (IPv4) ou les 80 derniers bits
    (IPv6) sont retirés : suffisant pour distinguer des accès, insuffisant pour
    identifier une personne — proportionnalité RGPD.
"""
import logging
import os
import reglages   # un réglage illisible ne doit pas arrêter le service
import threading
import time

_log = logging.getLogger("audit")

# Plafond du journal : la base est partagée avec les documents, un journal
# illimité finirait par manger l'espace utile. Les plus anciennes entrées sont
# retirées au-delà.
MAX_ENTREES = reglages.entier("AUDIT_MAX_ROWS", 20000, mini=1)

# DURÉE DE CONSERVATION — art. 5.1.e du RGPD. Le plafond de volume ci-dessus est
# une limite technique, pas une durée : sur un site peu sollicité, 20 000 entrées
# représentent plusieurs années, et une trace nominative conservée « jusqu'à ce
# que la place manque » n'a aucune durée de conservation au sens du règlement.
# Douze mois correspondent au repère retenu par la CNIL pour les journaux
# d'accès et de traçabilité : assez long pour instruire un incident découvert
# tardivement, assez court pour ne pas constituer un historique permanent des
# faits et gestes des utilisateurs. Les deux règles se cumulent : on efface ce
# qui est trop ANCIEN, et on plafonne ce qui est trop VOLUMINEUX.
RETENTION_JOURS = reglages.entier("AUDIT_RETENTION_JOURS", 365, mini=1)


def _limite_anciennete():
    """Horodatage (ms) avant lequel une entrée doit avoir disparu."""
    return int((time.time() - RETENTION_JOURS * 86400) * 1000)

_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS audit_journal (
        id BIGSERIAL PRIMARY KEY,
        ts BIGINT NOT NULL,
        acteur TEXT,
        role TEXT,
        action TEXT NOT NULL,
        cible TEXT,
        detail TEXT,
        ip TEXT,
        ok BOOLEAN NOT NULL DEFAULT TRUE)""",
    "CREATE INDEX IF NOT EXISTS audit_journal_ts_idx ON audit_journal(ts DESC)",
]


def anonymiser_ip(ip):
    """Tronque l'adresse : on garde le réseau, on jette l'hôte."""
    ip = (ip or "").strip()
    if not ip:
        return ""
    if ":" in ip:                                   # IPv6 : garde le préfixe /48
        parts = ip.split(":")
        return ":".join(parts[:3]) + "::" if len(parts) >= 3 else ip
    parts = ip.split(".")
    if len(parts) == 4:
        return ".".join(parts[:3]) + ".0"
    return ip


class _Memoire:
    """Repli non persistant : mieux qu'aucune trace pendant une panne de base."""
    persistent = False

    def __init__(self):
        self._lock = threading.Lock()
        self._rows = []

    def ajouter(self, rec):
        limite = _limite_anciennete()
        with self._lock:
            rec = dict(rec, id=len(self._rows) + 1)
            self._rows.append(rec)
            self._rows = [r for r in self._rows if r.get("ts", 0) >= limite]
            if len(self._rows) > MAX_ENTREES:
                del self._rows[:len(self._rows) - MAX_ENTREES]
        return True

    def purger(self):
        limite = _limite_anciennete()
        with self._lock:
            avant = len(self._rows)
            self._rows = [r for r in self._rows if r.get("ts", 0) >= limite]
            return avant - len(self._rows)

    def lire(self, limit=200, action=None, acteur=None):
        with self._lock:
            rows = list(reversed(self._rows))
        if action:
            rows = [r for r in rows if r.get("action") == action]
        if acteur:
            rows = [r for r in rows if r.get("acteur") == acteur]
        return rows[:limit]

    def compter(self):
        with self._lock:
            return len(self._rows)


class _Postgres:
    """Accès PostgreSQL au journal, à empreinte de connexions NULLE au repos.

    Chaque module de l'application ouvre son propre pool (documents, comptes,
    clients, livrables, cockpit, automatisation) : autant de connexions retenues
    en permanence, et les offres d'hébergement plafonnent ce nombre. Le journal
    n'écrit qu'à l'occasion d'une action d'administration — quelques fois par
    jour : lui réserver une connexion permanente serait payer cher un usage rare.
    D'où min_size=0 (rien tant qu'on ne s'en sert pas), max_size=1 (jamais plus
    d'une), fermeture après 60 s d'inactivité, et création DIFFÉRÉE au premier
    besoin (importer le module ne coûte donc aucune connexion)."""
    persistent = True

    def __init__(self, dsn):
        sep = "&" if "?" in dsn else "?"
        self._dsn = dsn + sep + "connect_timeout=10&client_encoding=UTF8"
        self._pool = None
        self._schema_ok = False
        self._lock = threading.Lock()

    def _p(self):
        with self._lock:
            if self._pool is None:
                from psycopg_pool import ConnectionPool
                self._pool = ConnectionPool(
                    self._dsn, min_size=0, max_size=1, max_idle=60,
                    kwargs={"autocommit": True, "prepare_threshold": None},
                    timeout=8, open=True, check=ConnectionPool.check_connection)
            if not self._schema_ok:
                with self._pool.connection() as c:
                    for stmt in _SCHEMA:
                        c.execute(stmt)
                self._schema_ok = True
        return self._pool

    def ajouter(self, rec):
        with self._p().connection() as c:
            c.execute("INSERT INTO audit_journal (ts,acteur,role,action,cible,detail,ip,ok) "
                      "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                      (rec["ts"], rec["acteur"], rec["role"], rec["action"],
                       rec["cible"], rec["detail"], rec["ip"], rec["ok"]))
            # Durée de conservation d'abord (art. 5.1.e), plafond de volume
            # ensuite : l'un est une obligation, l'autre une précaution.
            c.execute("DELETE FROM audit_journal WHERE ts < %s", (_limite_anciennete(),))
            # Élagage : on ne conserve que les MAX_ENTREES plus récentes.
            c.execute("DELETE FROM audit_journal WHERE id < "
                      "(SELECT COALESCE(MIN(id),0) FROM (SELECT id FROM audit_journal "
                      " ORDER BY id DESC LIMIT %s) t)", (MAX_ENTREES,))
        return True

    def purger(self):
        with self._p().connection() as c:
            cur = c.execute("DELETE FROM audit_journal WHERE ts < %s",
                            (_limite_anciennete(),))
            return cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0

    def lire(self, limit=200, action=None, acteur=None):
        clauses, params = [], []
        if action:
            clauses.append("action=%s")
            params.append(action)
        if acteur:
            clauses.append("acteur=%s")
            params.append(acteur)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(max(1, min(int(limit or 200), 1000)))
        with self._p().connection() as c:
            rows = c.execute(
                "SELECT id,ts,acteur,role,action,cible,detail,ip,ok FROM audit_journal"
                + where + " ORDER BY id DESC LIMIT %s", tuple(params)).fetchall()
        cols = ("id", "ts", "acteur", "role", "action", "cible", "detail", "ip", "ok")
        return [dict(zip(cols, r)) for r in rows]

    def compter(self):
        with self._p().connection() as c:
            return c.execute("SELECT count(*) FROM audit_journal").fetchone()[0]


def _creer():
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        if dsn.startswith("postgres://"):
            dsn = "postgresql://" + dsn[len("postgres://"):]
        try:
            return _Postgres(dsn)
        except Exception:
            _log.warning("journal d'audit : PostgreSQL injoignable — repli mémoire "
                         "(les traces ne survivront pas au redémarrage).")
    return _Memoire()


store = _creer()


def journaliser(action, cible="", detail="", ok=True, acteur=None, role=None, ip=None):
    """Enregistre une action. Best-effort : ne lève jamais.

    `acteur`/`role`/`ip` sont déduits de la requête en cours quand ils ne sont pas
    fournis — utile pour journaliser une tentative de connexion, où il n'y a pas
    encore de session."""
    try:
        if acteur is None or role is None:
            try:
                import auth
                u = auth.current_user()
            except Exception:
                u = None
            if acteur is None:
                acteur = (u or {}).get("email") or "anonyme"
            if role is None:
                role = (u or {}).get("role") or "-"
        if ip is None:
            try:
                from flask import request
                # request.remote_addr est corrigé par ProxyFix (app.py) : ne
                # pas relire X-Forwarded-For ici, sous peine de journaliser
                # une adresse que l'auteur de la requête a écrite lui-même.
                ip = request.remote_addr or ""
            except Exception:
                ip = ""
        store.ajouter({"ts": int(time.time() * 1000), "acteur": str(acteur)[:200],
                       "role": str(role)[:40], "action": str(action)[:80],
                       "cible": str(cible or "")[:300], "detail": str(detail or "")[:500],
                       "ip": anonymiser_ip(ip), "ok": bool(ok)})
    except Exception:
        # Un journal qui casse l'application serait pire que pas de journal.
        _log.warning("journal d'audit : écriture impossible (action %r).", action)


def lire(limit=200, action=None, acteur=None):
    try:
        return store.lire(limit=limit, action=action, acteur=acteur)
    except Exception:
        _log.warning("journal d'audit : lecture impossible.")
        return []


def purger():
    """Efface les entrées au-delà de la durée de conservation. Ne lève jamais.

    Appelée par la tâche quotidienne d'automatisation. Retourne le nombre
    d'entrées effacées, ou 0 si la purge n'a pas pu s'exécuter.
    """
    try:
        return int(store.purger() or 0)
    except Exception:
        _log.warning("journal d'audit : purge impossible.")
        return 0


def etat():
    """Nombre d'entrées + persistance, pour l'affichage d'administration."""
    base = {"persistant": getattr(store, "persistent", False),
            "plafond": MAX_ENTREES, "retention_jours": RETENTION_JOURS}
    try:
        return dict(base, entrees=store.compter())
    except Exception:
        return dict(base, entrees=None)
