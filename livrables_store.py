"""Historique des livrables générés — stockage CRUD.

Chaque livrable produit par le générateur (voir livrables.py / assistant.generate)
est enregistré ici afin d'être reconsulté, ré-exporté (Word / PDF) ou supprimé.

Deux implémentations interchangeables (même interface), sur le modèle de
cockpit_state / rag_store :
  - PostgresLivrablesStore : persistant (PostgreSQL) si DATABASE_URL est défini ;
  - MemoryLivrablesStore : en mémoire sinon (non persistant).

Réservé à l'administrateur (les routes appelantes sont protégées par @admin_required).
"""
import json
import logging
import os
import threading
import time
import uuid

_log = logging.getLogger("livrables")

MAX_MARKDOWN = 200_000   # garde-fou de taille (caractères)
LIST_LIMIT = 300


def _now_ms():
    return int(time.time() * 1000)


def _valid_id(v):
    return isinstance(v, str) and len(v) == 32 and all(c in "0123456789abcdef" for c in v)


def _clean(rec):
    """Normalise et borne un enregistrement entrant."""
    md = (rec.get("markdown") or "").strip()
    if len(md) > MAX_MARKDOWN:
        md = md[:MAX_MARKDOWN]
    sources = rec.get("sources") or []
    if not isinstance(sources, list):
        sources = []
    pid = rec.get("parent_id")
    return {
        "type": (rec.get("type") or "")[:80],
        "label": (rec.get("label") or rec.get("type") or "Livrable")[:200],
        "client": (rec.get("client") or "")[:200],
        "secteur": (rec.get("secteur") or "")[:200],
        "perimetre": (rec.get("perimetre") or "")[:400],
        "model": (rec.get("model") or "")[:80],
        "markdown": md,
        "sources": sources,
        "parent_id": pid if _valid_id(pid) else None,
    }


# ============================================================================
#  Mémoire (repli non persistant)
# ============================================================================
class MemoryLivrablesStore:
    persistent = False

    def __init__(self):
        self._lock = threading.RLock()
        self._items = {}

    def save(self, rec):
        rec = _clean(rec)
        if not rec["markdown"]:
            return None
        lid = uuid.uuid4().hex
        rec.update(id=lid, created_at=_now_ms())
        with self._lock:
            self._items[lid] = rec
        return lid

    def list(self):
        with self._lock:
            items = sorted(self._items.values(), key=lambda r: r["created_at"], reverse=True)
            return [self._meta(r) for r in items[:LIST_LIMIT]]

    def get(self, lid):
        with self._lock:
            r = self._items.get(lid)
            return dict(r) if r else None

    def delete(self, lid):
        with self._lock:
            return self._items.pop(lid, None) is not None

    def stats(self):
        with self._lock:
            return {"count": len(self._items)}

    @staticmethod
    def _meta(r):
        m = {k: r[k] for k in ("id", "type", "label", "client", "secteur",
                               "model", "created_at", "parent_id")}
        m["chars"] = len(r.get("markdown") or "")
        return m


# ============================================================================
#  PostgreSQL (persistant)
# ============================================================================
_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS livrables (
        id TEXT PRIMARY KEY,
        type TEXT,
        label TEXT,
        client TEXT,
        secteur TEXT,
        perimetre TEXT,
        model TEXT,
        markdown TEXT NOT NULL,
        sources TEXT,
        created_at BIGINT)""",
    "CREATE INDEX IF NOT EXISTS livrables_created_idx ON livrables (created_at DESC)",
    # Ajout du chaînage de versions (compatible bases existantes).
    "ALTER TABLE livrables ADD COLUMN IF NOT EXISTS parent_id TEXT",
]


class PostgresLivrablesStore:
    persistent = True
    _SCHEMA_LOCK = 907246

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

    def save(self, rec):
        rec = _clean(rec)
        if not rec["markdown"]:
            return None
        lid = uuid.uuid4().hex
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO livrables(id,type,label,client,secteur,perimetre,model,"
                "markdown,sources,created_at,parent_id) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (lid, rec["type"], rec["label"], rec["client"], rec["secteur"],
                 rec["perimetre"], rec["model"], rec["markdown"],
                 json.dumps(rec["sources"], ensure_ascii=False), _now_ms(),
                 rec["parent_id"]))
        return lid

    def list(self):
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT id,type,label,client,secteur,model,created_at,parent_id,"
                "char_length(markdown) FROM livrables ORDER BY created_at DESC "
                "LIMIT %s", (LIST_LIMIT,)).fetchall()
        keys = ("id", "type", "label", "client", "secteur", "model", "created_at",
                "parent_id", "chars")
        return [dict(zip(keys, r)) for r in rows]

    def get(self, lid):
        with self._pool.connection() as conn:
            r = conn.execute(
                "SELECT id,type,label,client,secteur,perimetre,model,markdown,sources,"
                "created_at,parent_id FROM livrables WHERE id=%s", (lid,)).fetchone()
        if not r:
            return None
        keys = ("id", "type", "label", "client", "secteur", "perimetre", "model",
                "markdown", "sources", "created_at", "parent_id")
        rec = dict(zip(keys, r))
        try:
            rec["sources"] = json.loads(rec["sources"]) if rec["sources"] else []
        except (ValueError, TypeError):
            rec["sources"] = []
        return rec

    def delete(self, lid):
        with self._pool.connection() as conn:
            return conn.execute("DELETE FROM livrables WHERE id=%s", (lid,)).rowcount > 0

    def stats(self):
        with self._pool.connection() as conn:
            return {"count": conn.execute("SELECT count(*) FROM livrables").fetchone()[0]}


def make_livrables_store():
    """Store persistant si DATABASE_URL est défini, sinon en mémoire."""
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return MemoryLivrablesStore()
    if dsn.startswith("postgres://"):
        dsn = "postgresql://" + dsn[len("postgres://"):]
    try:
        return PostgresLivrablesStore(dsn)
    except Exception as exc:
        _log.warning("Historique livrables : PostgreSQL injoignable (%s) — repli mémoire.", exc)
        return MemoryLivrablesStore()
