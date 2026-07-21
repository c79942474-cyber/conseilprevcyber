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

# --- Pièces jointes (preuves de consentement, contrats, historiques…) ---------
# Stockage BINAIRE uniquement (aucune extraction/analyse) ; chargées par
# morceaux (< plafond global de 512 Ko par requête), assemblées côté serveur.
CATEGORIES_PIECES = ("consentement", "contrat", "correspondance", "historique", "autre")
ALLOWED_DOC_EXT = {"pdf", "docx", "doc", "odt", "txt", "md", "eml", "png", "jpg", "jpeg"}
DOC_MAX_BYTES = int(os.environ.get("CLIENTS_DOC_MAX_MB", "15")) * 1024 * 1024
DOC_CHUNK_MAX = 480 * 1024
MAX_DOCS_PER_CLIENT = 100


class ClientsError(Exception):
    """Erreur métier portant un code interne + un statut HTTP (modèle RagError)."""

    def __init__(self, code, status=400):
        super().__init__(code)
        self.code = code
        self.status = status


def _doc_ext(filename):
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if ext not in ALLOWED_DOC_EXT:
        raise ClientsError("type_non_supporte", 415)
    return ext


def _clean_categorie(v):
    return v if v in CATEGORIES_PIECES else "autre"


def _safe_doc_filename(name, ext):
    """Nom d'affichage sûr : pas de séparateur de chemin, extension cohérente
    avec celle validée à l'ouverture du chargement ; vide si non conforme."""
    name = (name or "").strip().replace("\\", "/").split("/")[-1][:200]
    if not name or "." not in name:
        return ""
    if name.rsplit(".", 1)[-1].lower() != ext:
        return ""
    return name


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
        self._docs = {}       # client_id -> {doc_id: meta + data}
        self._uploads = {}    # upload_id -> {parts, ext, filename, cid}

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
            if not c:
                return None
            out = _decorate(dict(c))
            out["docs"] = len(self._docs.get(cid, {}))
            return out

    def list(self):
        with self._lock:
            items = sorted(self._items.values(), key=lambda c: c["updated_at"], reverse=True)
            out = [_decorate(dict(c)) for c in items[:LIST_LIMIT]]
            for c in out:
                c["docs"] = len(self._docs.get(c["id"], {}))
            return out

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
        """Droit à l'effacement (art. 17) : suppression définitive (fiche + pièces
        jointes) + journal anonymisé."""
        with self._lock:
            c = self._items.pop(cid, None)
            if not c:
                return False
            self._docs.pop(cid, None)
            for uid in [u for u, up in self._uploads.items() if up.get("cid") == cid]:
                self._uploads.pop(uid, None)
            for e in self._events:            # anonymise l'historique du client effacé
                if e["client_id"] == cid:
                    e["label"] = "[effacé]"
                    e["details"] = ""
        self._log(actor, motif, cid, "[effacé]", "ref=" + _ref_effacement(c))
        return True

    def export(self, cid, actor=""):
        """Portabilité (art. 20) : fiche complète + journal + pièces (métadonnées),
        format lisible par machine."""
        c = self.get(cid)
        if not c:
            return None
        self._log(actor, "export", cid, c["entreprise"], "art. 20 RGPD")
        return {"format": "JSON — export RGPD (art. 15 / art. 20)",
                "exported_at": _now_ms(), "client": c,
                "documents": self.docs_list(cid),
                "journal": self.events(client_id=cid, limit=EVENTS_LIMIT)}

    # -- pièces jointes (stockage binaire, chargé par morceaux) --
    def doc_upload_create(self, cid, filename, total_bytes):
        ext = _doc_ext(filename)
        if total_bytes and total_bytes > DOC_MAX_BYTES:
            raise ClientsError("fichier_trop_lourd", 413)
        with self._lock:
            if cid not in self._items:
                raise ClientsError("client_inconnu", 404)
            if len(self._docs.get(cid, {})) >= MAX_DOCS_PER_CLIENT:
                raise ClientsError("trop_de_pieces", 409)
            uid = uuid.uuid4().hex + "." + ext
            self._uploads[uid] = {"parts": {}, "ext": ext, "filename": filename, "cid": cid}
        return uid

    def doc_upload_chunk(self, upload_id, idx, data):
        if len(data) > DOC_CHUNK_MAX + 4096:
            raise ClientsError("morceau_trop_grand", 413)
        with self._lock:
            up = self._uploads.get(upload_id)
            if not up:
                raise ClientsError("upload_inconnu", 404)
            up["parts"][int(idx)] = data
            if sum(len(v) for v in up["parts"].values()) > DOC_MAX_BYTES:
                self._uploads.pop(upload_id, None)
                raise ClientsError("fichier_trop_lourd", 413)

    def doc_upload_finish(self, cid, upload_id, categorie, actor="", filename=""):
        with self._lock:
            up = self._uploads.pop(upload_id, None)
        if not up or up.get("cid") != cid:
            raise ClientsError("upload_inconnu", 404)
        data = b"".join(up["parts"][i] for i in sorted(up["parts"]))
        if not data:
            raise ClientsError("fichier_vide", 422)
        if len(data) > DOC_MAX_BYTES:
            raise ClientsError("fichier_trop_lourd", 413)
        did = uuid.uuid4().hex
        meta = {"id": did, "client_id": cid,
                "filename": (up["filename"] or _safe_doc_filename(filename, up["ext"])
                             or "piece-%s.%s" % (did[:8], up["ext"]))[:200],
                "ext": up["ext"], "categorie": _clean_categorie(categorie),
                "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                "uploaded_by": (actor or "")[:200], "created_at": _now_ms()}
        with self._lock:
            if cid not in self._items:
                raise ClientsError("client_inconnu", 404)
            self._docs.setdefault(cid, {})[did] = dict(meta, data=data)
            entreprise = self._items[cid]["entreprise"]
        self._log(actor, "piece_ajout", cid, entreprise,
                  "%s (%s)" % (meta["filename"], meta["categorie"]))
        return meta

    def docs_list(self, cid):
        with self._lock:
            docs = self._docs.get(cid, {})
            return [{k: v for k, v in d.items() if k != "data"}
                    for d in sorted(docs.values(), key=lambda d: d["created_at"], reverse=True)]

    def doc_get(self, cid, did, actor=""):
        with self._lock:
            d = self._docs.get(cid, {}).get(did)
            if not d:
                raise ClientsError("piece_inconnue", 404)
            entreprise = self._items[cid]["entreprise"] if cid in self._items else ""
            filename, data = d["filename"], d["data"]
        self._log(actor, "piece_telechargement", cid, entreprise, filename)
        return filename, data

    def doc_delete(self, cid, did, actor=""):
        with self._lock:
            docs = self._docs.get(cid, {})
            d = docs.pop(did, None)
            if not d:
                raise ClientsError("piece_inconnue", 404)
            entreprise = self._items[cid]["entreprise"] if cid in self._items else ""
        self._log(actor, "piece_suppression", cid, entreprise, d["filename"])
        return True

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
    # Pièces jointes (binaire) : supprimées AVEC la fiche (ON DELETE CASCADE = art. 17).
    """CREATE TABLE IF NOT EXISTS clients_docs (
        id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
        filename TEXT NOT NULL,
        ext TEXT,
        categorie TEXT,
        bytes BIGINT,
        sha256 TEXT,
        uploaded_by TEXT,
        created_at BIGINT,
        data BYTEA NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS clients_docs_client_idx ON clients_docs (client_id)",
    """CREATE TABLE IF NOT EXISTS clients_docs_uploads (
        upload_id TEXT NOT NULL,
        idx INT NOT NULL,
        data BYTEA NOT NULL,
        client_id TEXT,
        created_at BIGINT,
        PRIMARY KEY (upload_id, idx))""",
]

_DOC_META_COLS = ("id", "client_id", "filename", "ext", "categorie", "bytes",
                  "sha256", "uploaded_by", "created_at")


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
            if not r:
                return None
            out = self._row(r)
            out["docs"] = conn.execute("SELECT count(*) FROM clients_docs WHERE client_id=%s",
                                       (cid,)).fetchone()[0]
        return out

    def list(self):
        with self._pool.connection() as conn:
            rows = conn.execute("SELECT %s FROM clients ORDER BY updated_at DESC LIMIT %%s"
                                % self._COLS, (LIST_LIMIT,)).fetchall()
            counts = dict(conn.execute(
                "SELECT client_id, count(*) FROM clients_docs GROUP BY client_id").fetchall())
        out = [self._row(r) for r in rows]
        for c in out:
            c["docs"] = counts.get(c["id"], 0)
        return out

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
        """Droit à l'effacement (art. 17) : suppression définitive (fiche + pièces
        jointes, en cascade) + journal anonymisé."""
        with self._pool.connection() as conn:
            r = conn.execute("SELECT %s FROM clients WHERE id=%%s" % self._COLS,
                             (cid,)).fetchone()
            if not r:
                return False
            client = dict(zip(_CLIENT_KEYS, r))
            with conn.transaction():
                conn.execute("DELETE FROM clients WHERE id=%s", (cid,))  # cascade clients_docs
                conn.execute("DELETE FROM clients_docs_uploads WHERE client_id=%s", (cid,))
                conn.execute("UPDATE clients_events SET label='[effacé]',details='' "
                             "WHERE client_id=%s", (cid,))
            self._log(conn, actor, motif, cid, "[effacé]", "ref=" + _ref_effacement(client))
        return True

    def export(self, cid, actor=""):
        """Portabilité (art. 20) : fiche complète + journal + pièces (métadonnées),
        format lisible par machine."""
        c = self.get(cid)
        if not c:
            return None
        with self._pool.connection() as conn:
            self._log(conn, actor, "export", cid, c["entreprise"], "art. 20 RGPD")
        return {"format": "JSON — export RGPD (art. 15 / art. 20)",
                "exported_at": _now_ms(), "client": c,
                "documents": self.docs_list(cid),
                "journal": self.events(client_id=cid, limit=EVENTS_LIMIT)}

    # -- pièces jointes (stockage binaire, chargé par morceaux) --
    def doc_upload_create(self, cid, filename, total_bytes):
        ext = _doc_ext(filename)
        if total_bytes and total_bytes > DOC_MAX_BYTES:
            raise ClientsError("fichier_trop_lourd", 413)
        with self._pool.connection() as conn:
            if not conn.execute("SELECT 1 FROM clients WHERE id=%s", (cid,)).fetchone():
                raise ClientsError("client_inconnu", 404)
            n = conn.execute("SELECT count(*) FROM clients_docs WHERE client_id=%s",
                             (cid,)).fetchone()[0]
            if n >= MAX_DOCS_PER_CLIENT:
                raise ClientsError("trop_de_pieces", 409)
            # purge opportuniste des chargements inachevés (> 1 h)
            conn.execute("DELETE FROM clients_docs_uploads WHERE created_at < %s",
                         (_now_ms() - 3600_000,))
        return uuid.uuid4().hex + "." + ext

    def doc_upload_chunk(self, upload_id, idx, data, cid=None):
        if len(data) > DOC_CHUNK_MAX + 4096:
            raise ClientsError("morceau_trop_grand", 413)
        with self._pool.connection() as conn:
            total = conn.execute("SELECT COALESCE(SUM(octet_length(data)),0) "
                                 "FROM clients_docs_uploads WHERE upload_id=%s",
                                 (upload_id,)).fetchone()[0]
            if total + len(data) > DOC_MAX_BYTES:
                conn.execute("DELETE FROM clients_docs_uploads WHERE upload_id=%s", (upload_id,))
                raise ClientsError("fichier_trop_lourd", 413)
            conn.execute("INSERT INTO clients_docs_uploads(upload_id,idx,data,client_id,created_at) "
                         "VALUES(%s,%s,%s,%s,%s) ON CONFLICT (upload_id,idx) DO NOTHING",
                         (upload_id, int(idx), data, cid, _now_ms()))

    def doc_upload_finish(self, cid, upload_id, categorie, actor="", filename=""):
        ext = (upload_id.rsplit(".", 1)[-1] if "." in upload_id else "").lower()
        filename = _safe_doc_filename(filename, ext)
        with self._pool.connection() as conn:
            row = conn.execute("SELECT entreprise FROM clients WHERE id=%s", (cid,)).fetchone()
            if not row:
                raise ClientsError("client_inconnu", 404)
            entreprise = row[0]
            rows = conn.execute("SELECT data FROM clients_docs_uploads WHERE upload_id=%s "
                                "ORDER BY idx", (upload_id,)).fetchall()
            try:
                if not rows:
                    raise ClientsError("upload_inconnu", 404)
                data = b"".join(bytes(r[0]) for r in rows)
                if not data:
                    raise ClientsError("fichier_vide", 422)
                if len(data) > DOC_MAX_BYTES:
                    raise ClientsError("fichier_trop_lourd", 413)
                did = uuid.uuid4().hex
                filename = filename or "piece-%s.%s" % (did[:8], ext)
                conn.execute(
                    "INSERT INTO clients_docs(id,client_id,filename,ext,categorie,bytes,"
                    "sha256,uploaded_by,created_at,data) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (did, cid, filename, ext, _clean_categorie(categorie), len(data),
                     hashlib.sha256(data).hexdigest(), (actor or "")[:200], _now_ms(), data))
            finally:
                try:
                    conn.execute("DELETE FROM clients_docs_uploads WHERE upload_id=%s",
                                 (upload_id,))
                except Exception:
                    pass
            self._log(conn, actor, "piece_ajout", cid, entreprise,
                      "%s (%s)" % (filename, _clean_categorie(categorie)))
            r = conn.execute("SELECT %s FROM clients_docs WHERE id=%%s"
                             % ",".join(_DOC_META_COLS), (did,)).fetchone()
        return dict(zip(_DOC_META_COLS, r))

    def docs_list(self, cid):
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT %s FROM clients_docs WHERE client_id=%%s ORDER BY created_at DESC"
                % ",".join(_DOC_META_COLS), (cid,)).fetchall()
        return [dict(zip(_DOC_META_COLS, r)) for r in rows]

    def doc_get(self, cid, did, actor=""):
        with self._pool.connection() as conn:
            r = conn.execute("SELECT d.filename,d.data,c.entreprise FROM clients_docs d "
                             "JOIN clients c ON c.id=d.client_id "
                             "WHERE d.id=%s AND d.client_id=%s", (did, cid)).fetchone()
            if not r:
                raise ClientsError("piece_inconnue", 404)
            self._log(conn, actor, "piece_telechargement", cid, r[2], r[0])
        return r[0], bytes(r[1])

    def doc_delete(self, cid, did, actor=""):
        with self._pool.connection() as conn:
            r = conn.execute("SELECT d.filename,c.entreprise FROM clients_docs d "
                             "JOIN clients c ON c.id=d.client_id "
                             "WHERE d.id=%s AND d.client_id=%s", (did, cid)).fetchone()
            if not r:
                raise ClientsError("piece_inconnue", 404)
            conn.execute("DELETE FROM clients_docs WHERE id=%s AND client_id=%s", (did, cid))
            self._log(conn, actor, "piece_suppression", cid, r[1], r[0])
        return True

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
