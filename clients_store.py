"""Gestion des clients & prospects — conforme RGPD (inspirée du module Sentinel).

Registre clients B2B minimal (art. 5.1.c — minimisation) avec les garanties RGPD :
  - base légale documentée par fiche (art. 6) et preuve de consentement (art. 7) ;
  - droit de rectification via la modification de fiche (art. 16) ;
  - droit à l'effacement : suppression définitive + journal ANONYMISÉ (art. 17) ;
  - portabilité : export JSON complet de la fiche et de son journal (art. 20) ;
  - limitation de conservation : durée paramétrable par fiche, détection des
    fiches expirées et purge (art. 5.1.e) ;
  - accountability : journal horodaté de toutes les opérations (art. 5.2).

Deux implémentations interchangeables (même interface), sur le modèle de
rag_store / livrables_store :
  - PostgresClientsStore : persistant (PostgreSQL) si DATABASE_URL est défini ;
  - MemoryClientsStore : en mémoire sinon (non persistant).

Réservé à l'administrateur (routes appelantes protégées par @admin_required).
"""
import hashlib
import logging
import os
import threading
import time
import uuid

_log = logging.getLogger("clients")

LIST_LIMIT = 500
EVENTS_LIMIT = 200
MONTH_MS = 30 * 24 * 3600 * 1000          # mois ≈ 30 jours (durée de conservation)
DEFAULT_RETENTION_MONTHS = 36             # prospects B2B : 3 ans après dernier contact (repère CNIL)

STATUTS = ("prospect", "actif", "termine", "archive")
BASES_LEGALES = ("interet_legitime", "contrat", "mesures_precontractuelles",
                 "consentement", "obligation_legale")


def _now_ms():
    return int(time.time() * 1000)


def _valid_id(v):
    return isinstance(v, str) and len(v) == 32 and all(c in "0123456789abcdef" for c in v)


def _ref_effacement(client):
    """Référence pseudonymisée d'un client effacé : permet de PROUVER l'effacement
    (accountability) sans conserver aucune donnée personnelle en clair."""
    basis = (client.get("email") or client.get("id") or "").lower()
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def _clean(rec, partial=False):
    """Normalise et borne les champs entrants. En mode partial (PATCH), seuls
    les champs présents sont renvoyés."""
    out = {}

    def put(key, value):
        out[key] = value

    if not partial or "entreprise" in rec:
        put("entreprise", (rec.get("entreprise") or "").strip()[:200])
    if not partial or "contact" in rec:
        put("contact", (rec.get("contact") or "").strip()[:200])
    if not partial or "email" in rec:
        email = (rec.get("email") or "").strip().lower()[:200]
        put("email", email if ("@" in email and "." in email.split("@")[-1]) else "")
    if not partial or "telephone" in rec:
        tel = (rec.get("telephone") or "").strip()[:40]
        put("telephone", "".join(c for c in tel if c.isdigit() or c in "+ .-()"))
    if not partial or "secteur" in rec:
        put("secteur", (rec.get("secteur") or "").strip()[:120])
    if not partial or "statut" in rec:
        s = (rec.get("statut") or "").strip()
        put("statut", s if s in STATUTS else "prospect")
    if not partial or "base_legale" in rec:
        b = (rec.get("base_legale") or "").strip()
        put("base_legale", b if b in BASES_LEGALES else "interet_legitime")
    if not partial or "consentement" in rec:
        put("consentement", bool(rec.get("consentement")))
    if not partial or "consent_source" in rec:
        put("consent_source", (rec.get("consent_source") or "").strip()[:200])
    if not partial or "retention_months" in rec:
        try:
            months = int(rec.get("retention_months") or DEFAULT_RETENTION_MONTHS)
        except (TypeError, ValueError):
            months = DEFAULT_RETENTION_MONTHS
        put("retention_months", min(max(months, 1), 120))
    if not partial or "notes" in rec:
        put("notes", (rec.get("notes") or "").strip()[:4000])
    return out


def _decorate(c):
    """Ajoute les champs calculés de conservation (art. 5.1.e)."""
    ref = c.get("last_activity") or c.get("updated_at") or c.get("created_at") or _now_ms()
    months = c.get("retention_months") or DEFAULT_RETENTION_MONTHS
    c["expire_at"] = ref + months * MONTH_MS
    c["expired"] = _now_ms() > c["expire_at"]
    return c


_CLIENT_KEYS = ("id", "entreprise", "contact", "email", "telephone", "secteur",
                "statut", "base_legale", "consentement", "consent_date",
                "consent_source", "retention_months", "notes",
                "created_at", "updated_at", "last_activity")
_EVENT_KEYS = ("id", "ts", "actor", "action", "client_id", "label", "details")


# ============================================================================
#  Mémoire (repli non persistant)
# ============================================================================
class MemoryClientsStore:
    persistent = False

    def __init__(self):
        self._lock = threading.RLock()
        self._items = {}
        self._events = []
        self._eid = 0

    # -- journal (accountability, art. 5.2) --
    def _log(self, actor, action, client_id, label, details=""):
        with self._lock:
            self._eid += 1
            self._events.append({"id": self._eid, "ts": _now_ms(),
                                 "actor": (actor or "")[:200], "action": action,
                                 "client_id": client_id, "label": (label or "")[:200],
                                 "details": (details or "")[:400]})
            del self._events[:-2000]

    def events(self, client_id=None, limit=EVENTS_LIMIT):
        with self._lock:
            evs = [e for e in self._events if client_id is None or e["client_id"] == client_id]
            return [dict(e) for e in sorted(evs, key=lambda e: e["id"], reverse=True)[:limit]]

    # -- CRUD --
    def create(self, rec, actor=""):
        rec = _clean(rec)
        if not rec.get("entreprise"):
            return None
        cid = uuid.uuid4().hex
        now = _now_ms()
        rec.update(id=cid, created_at=now, updated_at=now, last_activity=now,
                   consent_date=now if rec.get("consentement") else None)
        with self._lock:
            self._items[cid] = rec
        self._log(actor, "creation", cid, rec["entreprise"])
        if rec.get("consentement"):
            self._log(actor, "consentement", cid, rec["entreprise"],
                      "accordé — " + (rec.get("consent_source") or "non précisé"))
        return _decorate(dict(rec))

    def get(self, cid):
        with self._lock:
            c = self._items.get(cid)
            return _decorate(dict(c)) if c else None

    def list(self):
        with self._lock:
            items = sorted(self._items.values(), key=lambda c: c["updated_at"], reverse=True)
            return [_decorate(dict(c)) for c in items[:LIST_LIMIT]]

    def update(self, cid, rec, actor=""):
        changes = _clean(rec, partial=True)
        with self._lock:
            c = self._items.get(cid)
            if not c:
                return None
            consent_before = c.get("consentement")
            c.update(changes)
            if not c.get("entreprise"):
                c["entreprise"] = "(sans nom)"
            now = _now_ms()
            c["updated_at"] = now
            c["last_activity"] = now
            consent_after = c.get("consentement")
            if "consentement" in changes and consent_after != consent_before:
                c["consent_date"] = now
            snapshot = dict(c)
        self._log(actor, "modification", cid, snapshot["entreprise"])
        if "consentement" in changes and consent_after != consent_before:
            self._log(actor, "consentement", cid, snapshot["entreprise"],
                      ("accordé — " + (snapshot.get("consent_source") or "non précisé"))
                      if consent_after else "retiré")
        return _decorate(snapshot)

    def delete(self, cid, actor="", motif="effacement"):
        """Droit à l'effacement (art. 17) : suppression définitive + journal anonymisé."""
        with self._lock:
            c = self._items.pop(cid, None)
            if not c:
                return False
            for e in self._events:            # anonymise l'historique du client effacé
                if e["client_id"] == cid:
                    e["label"] = "[effacé]"
                    e["details"] = ""
        self._log(actor, motif, cid, "[effacé]", "ref=" + _ref_effacement(c))
        return True

    def export(self, cid, actor=""):
        """Portabilité (art. 20) : fiche complète + journal, format lisible par machine."""
        c = self.get(cid)
        if not c:
            return None
        self._log(actor, "export", cid, c["entreprise"], "art. 20 RGPD")
        return {"format": "JSON — export RGPD (art. 15 / art. 20)",
                "exported_at": _now_ms(), "client": c,
                "journal": self.events(client_id=cid, limit=EVENTS_LIMIT)}

    def purge_expired(self, actor=""):
        """Limitation de conservation (art. 5.1.e) : efface les fiches expirées."""
        expired = [c["id"] for c in self.list() if c["expired"]]
        for cid in expired:
            self.delete(cid, actor=actor, motif="purge_conservation")
        return len(expired)

    def stats(self):
        clients = self.list()
        return {"total": len(clients),
                "actifs": sum(1 for c in clients if c["statut"] == "actif"),
                "prospects": sum(1 for c in clients if c["statut"] == "prospect"),
                "consentements": sum(1 for c in clients if c["consentement"]),
                "expires": sum(1 for c in clients if c["expired"])}


# ============================================================================
#  PostgreSQL (persistant)
# ============================================================================
_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS clients (
        id TEXT PRIMARY KEY,
        entreprise TEXT NOT NULL,
        contact TEXT,
        email TEXT,
        telephone TEXT,
        secteur TEXT,
        statut TEXT,
        base_legale TEXT,
        consentement BOOLEAN DEFAULT FALSE,
        consent_date BIGINT,
        consent_source TEXT,
        retention_months INT DEFAULT 36,
        notes TEXT,
        created_at BIGINT,
        updated_at BIGINT,
        last_activity BIGINT)""",
    "CREATE INDEX IF NOT EXISTS clients_updated_idx ON clients (updated_at DESC)",
    """CREATE TABLE IF NOT EXISTS clients_events (
        id BIGSERIAL PRIMARY KEY,
        ts BIGINT,
        actor TEXT,
        action TEXT,
        client_id TEXT,
        label TEXT,
        details TEXT)""",
    "CREATE INDEX IF NOT EXISTS clients_events_ts_idx ON clients_events (ts DESC)",
]


class PostgresClientsStore:
    persistent = True
    _SCHEMA_LOCK = 907247

    def __init__(self, dsn):
        from psycopg_pool import ConnectionPool
        sep = "&" if "?" in dsn else "?"
        dsn = dsn + sep + "connect_timeout=5&client_encoding=UTF8"
        self._pool = ConnectionPool(dsn, min_size=1, max_size=2,
                                    kwargs={"autocommit": True}, timeout=8, open=True)
        try:
            self._init_schema()
        except Exception:
            try:
                self._pool.close()
            except Exception:
                pass
            raise

    def _init_schema(self):
        with self._pool.connection() as conn:
            conn.execute("SELECT pg_advisory_lock(%s)", (self._SCHEMA_LOCK,))
            try:
                for stmt in _SCHEMA:
                    conn.execute(stmt)
            finally:
                conn.execute("SELECT pg_advisory_unlock(%s)", (self._SCHEMA_LOCK,))

    def _log(self, conn, actor, action, client_id, label, details=""):
        conn.execute(
            "INSERT INTO clients_events(ts,actor,action,client_id,label,details) "
            "VALUES(%s,%s,%s,%s,%s,%s)",
            (_now_ms(), (actor or "")[:200], action, client_id,
             (label or "")[:200], (details or "")[:400]))

    def events(self, client_id=None, limit=EVENTS_LIMIT):
        with self._pool.connection() as conn:
            if client_id:
                rows = conn.execute(
                    "SELECT id,ts,actor,action,client_id,label,details FROM clients_events "
                    "WHERE client_id=%s ORDER BY id DESC LIMIT %s",
                    (client_id, limit)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id,ts,actor,action,client_id,label,details FROM clients_events "
                    "ORDER BY id DESC LIMIT %s", (limit,)).fetchall()
        return [dict(zip(_EVENT_KEYS, r)) for r in rows]

    def _row(self, r):
        return _decorate(dict(zip(_CLIENT_KEYS, r)))

    _COLS = ",".join(_CLIENT_KEYS)

    def create(self, rec, actor=""):
        rec = _clean(rec)
        if not rec.get("entreprise"):
            return None
        cid = uuid.uuid4().hex
        now = _now_ms()
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO clients(id,entreprise,contact,email,telephone,secteur,statut,"
                "base_legale,consentement,consent_date,consent_source,retention_months,"
                "notes,created_at,updated_at,last_activity) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (cid, rec["entreprise"], rec["contact"], rec["email"], rec["telephone"],
                 rec["secteur"], rec["statut"], rec["base_legale"], rec["consentement"],
                 now if rec.get("consentement") else None, rec["consent_source"],
                 rec["retention_months"], rec["notes"], now, now, now))
            self._log(conn, actor, "creation", cid, rec["entreprise"])
            if rec.get("consentement"):
                self._log(conn, actor, "consentement", cid, rec["entreprise"],
                          "accordé — " + (rec.get("consent_source") or "non précisé"))
        return self.get(cid)

    def get(self, cid):
        with self._pool.connection() as conn:
            r = conn.execute("SELECT %s FROM clients WHERE id=%%s" % self._COLS,
                             (cid,)).fetchone()
        return self._row(r) if r else None

    def list(self):
        with self._pool.connection() as conn:
            rows = conn.execute("SELECT %s FROM clients ORDER BY updated_at DESC LIMIT %%s"
                                % self._COLS, (LIST_LIMIT,)).fetchall()
        return [self._row(r) for r in rows]

    def update(self, cid, rec, actor=""):
        changes = _clean(rec, partial=True)
        with self._pool.connection() as conn:
            r = conn.execute("SELECT %s FROM clients WHERE id=%%s" % self._COLS,
                             (cid,)).fetchone()
            if not r:
                return None
            current = dict(zip(_CLIENT_KEYS, r))
            consent_before = current.get("consentement")
            current.update(changes)
            if not current.get("entreprise"):
                current["entreprise"] = "(sans nom)"
            now = _now_ms()
            current["updated_at"] = now
            current["last_activity"] = now
            consent_after = current.get("consentement")
            consent_changed = "consentement" in changes and consent_after != consent_before
            if consent_changed:
                current["consent_date"] = now
            conn.execute(
                "UPDATE clients SET entreprise=%s,contact=%s,email=%s,telephone=%s,"
                "secteur=%s,statut=%s,base_legale=%s,consentement=%s,consent_date=%s,"
                "consent_source=%s,retention_months=%s,notes=%s,updated_at=%s,"
                "last_activity=%s WHERE id=%s",
                (current["entreprise"], current["contact"], current["email"],
                 current["telephone"], current["secteur"], current["statut"],
                 current["base_legale"], current["consentement"], current["consent_date"],
                 current["consent_source"], current["retention_months"], current["notes"],
                 now, now, cid))
            self._log(conn, actor, "modification", cid, current["entreprise"])
            if consent_changed:
                self._log(conn, actor, "consentement", cid, current["entreprise"],
                          ("accordé — " + (current.get("consent_source") or "non précisé"))
                          if consent_after else "retiré")
        return _decorate(current)

    def delete(self, cid, actor="", motif="effacement"):
        """Droit à l'effacement (art. 17) : suppression définitive + journal anonymisé."""
        with self._pool.connection() as conn:
            r = conn.execute("SELECT %s FROM clients WHERE id=%%s" % self._COLS,
                             (cid,)).fetchone()
            if not r:
                return False
            client = dict(zip(_CLIENT_KEYS, r))
            with conn.transaction():
                conn.execute("DELETE FROM clients WHERE id=%s", (cid,))
                conn.execute("UPDATE clients_events SET label='[effacé]',details='' "
                             "WHERE client_id=%s", (cid,))
            self._log(conn, actor, motif, cid, "[effacé]", "ref=" + _ref_effacement(client))
        return True

    def export(self, cid, actor=""):
        """Portabilité (art. 20) : fiche complète + journal, format lisible par machine."""
        c = self.get(cid)
        if not c:
            return None
        with self._pool.connection() as conn:
            self._log(conn, actor, "export", cid, c["entreprise"], "art. 20 RGPD")
        return {"format": "JSON — export RGPD (art. 15 / art. 20)",
                "exported_at": _now_ms(), "client": c,
                "journal": self.events(client_id=cid, limit=EVENTS_LIMIT)}

    def purge_expired(self, actor=""):
        """Limitation de conservation (art. 5.1.e) : efface les fiches expirées."""
        expired = [c["id"] for c in self.list() if c["expired"]]
        for cid in expired:
            self.delete(cid, actor=actor, motif="purge_conservation")
        return len(expired)

    def stats(self):
        clients = self.list()
        return {"total": len(clients),
                "actifs": sum(1 for c in clients if c["statut"] == "actif"),
                "prospects": sum(1 for c in clients if c["statut"] == "prospect"),
                "consentements": sum(1 for c in clients if c["consentement"]),
                "expires": sum(1 for c in clients if c["expired"])}


def make_clients_store():
    """Store persistant si DATABASE_URL est défini, sinon en mémoire."""
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return MemoryClientsStore()
    if dsn.startswith("postgres://"):
        dsn = "postgresql://" + dsn[len("postgres://"):]
    try:
        return PostgresClientsStore(dsn)
    except Exception as exc:
        _log.warning("Clients : PostgreSQL injoignable (%s) — repli mémoire.", exc)
        return MemoryClientsStore()
