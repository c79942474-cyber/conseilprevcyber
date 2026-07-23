"""Base de connaissance RAG CONSEILPREV — stockage, indexation, recherche.

Objectif : une base documentaire administrable (chargement / suppression) qui
alimente en temps réel l'assistant conversationnel et, à terme, la génération de
livrables. Les documents sont découpés en « chunks », indexés, puis recherchés
par similarité pour fournir au LLM un contexte fiable et sourcé.

Deux implémentations interchangeables (même interface) :
  - PostgresRagStore : persistant (PostgreSQL), activé si DATABASE_URL est défini.
      • recherche vectorielle si l'extension pgvector est disponible (embeddings
        Mistral « mistral-embed »), sinon repli automatique sur la recherche
        plein-texte native de PostgreSQL (tsvector/tsquery, configuration française) ;
  - MemoryRagStore : en mémoire (repli si pas de base) — recherche lexicale simple.

Chargement rapide de fichiers lourds (inspiré du site de référence) :
  - l'upload est DÉCOUPLÉ de l'indexation : le fichier est reçu par morceaux
    (< 512 Ko, sous la limite globale de l'app), assemblé, extrait puis découpé —
    réponse immédiate ; l'embedding est ensuite réalisé par petits lots pilotés
    par le CLIENT (index-next), afin de ne jamais bloquer l'unique worker Gunicorn.

Sécurité :
  - les routes appelantes sont réservées à l'administrateur (@admin_required) ;
  - validation d'extension et de taille, noms de fichiers jamais utilisés comme
    chemins disque, requêtes SQL entièrement paramétrées ;
  - drapeau de visibilité par document : « public » (assistant + livrables) ou
    « interne » (livrables uniquement, jamais exposé à l'assistant public).
"""
import base64
import io
import hashlib
import json
import logging
import os
import re
import threading
import time
import uuid

_log = logging.getLogger("rag")

# --- Paramètres ---------------------------------------------------------------
EMBED_URL = "https://api.mistral.ai/v1/embeddings"
EMBED_MODEL = os.environ.get("MISTRAL_EMBED_MODEL", "mistral-embed")
EMBED_DIM = 1024               # dimension de mistral-embed
EMBED_BATCH = 10               # chunks embarqués par appel index-next (pilotage client)
EMBED_TIMEOUT = 60

CHUNK_CHARS = 900              # taille cible d'un chunk (caractères)
CHUNK_OVERLAP = 150            # recouvrement entre chunks
MAX_FILE_BYTES = int(os.environ.get("RAG_MAX_FILE_MB", "30")) * 1024 * 1024
MAX_CHUNK_UPLOAD = 480 * 1024  # taille max d'un morceau reçu (< MAX_CONTENT_LENGTH)
ALLOWED_EXT = {"txt", "md", "csv", "log", "json", "pdf", "docx"}
VISIBILITIES = ("public", "internal")

# Thèmes suggérés (l'admin peut en saisir d'autres).
# Thèmes proposés (autocomplétion à l'upload + filtre). Le champ reste en
# texte libre : cette liste ne fait qu'aider à catégoriser de façon cohérente
# pour retrouver les documents plus vite. Organisée par familles.
THEMES = [
    # — Normes & réglementations —
    "IEC 62443",
    "ISO 27001 / 27002",
    "NIST CSF / SP 800-82",
    "Guides ANSSI",
    "NIS2",
    "DORA",
    "RGPD",
    "AI Act",
    "Cyber Resilience Act",
    "Sûreté fonctionnelle (IEC 61508/61511)",
    # — Architecture & technique OT/IT —
    "Architecture & segmentation",
    "Inventaire & cartographie",
    "Analyse de risques",
    "Durcissement & configuration",
    "Gestion des correctifs",
    "Gestion des accès & identités",
    "Accès distant & télémaintenance",
    "Sécurité réseau & pare-feu",
    "Automates, SCADA & DCS",
    "IIoT & objets connectés",
    "Cryptographie & PKI",
    "Supervision & détection",
    "Réponse à incident",
    "Continuité & résilience (PRA/PCA)",
    # — Gouvernance & organisation —
    "Gouvernance & CSMS",
    "Sensibilisation & formation",
    "Gestion des prestataires",
    "Conformité & audit",
    # — Métier & livrables —
    "AMOA SI Industriel",
    "Cahier des charges & CCTP",
    "Plan de remédiation",
    "Études de cas",
    "Veille",
    "Général",
]


class RagError(Exception):
    """Erreur RAG portant un code interne + un statut HTTP."""

    def __init__(self, code, status=400):
        super().__init__(code)
        self.code = code
        self.status = status


# --- Extraction de texte ------------------------------------------------------
def _decode(data):
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def extract_text(ext, data):
    """Extrait le texte brut d'un fichier selon son extension."""
    ext = (ext or "").lower().lstrip(".")
    if ext in ("txt", "md", "csv", "log", "json"):
        return _decode(data)
    if ext == "pdf":
        try:
            from pypdf import PdfReader
        except Exception:  # absent OU binding cassé : message propre, pas de 500 brut
            raise RagError("pdf_support_absent", 500)
        try:
            reader = PdfReader(io.BytesIO(data))
            return "\n\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
            raise RagError("pdf_illisible", 422)
    if ext == "docx":
        try:
            import docx
        except Exception:  # absent OU binding cassé : message propre, pas de 500 brut
            raise RagError("docx_support_absent", 500)
        try:
            document = docx.Document(io.BytesIO(data))
            parts = [p.text for p in document.paragraphs]
            for table in document.tables:
                for row in table.rows:
                    parts.append(" | ".join(c.text for c in row.cells))
            return "\n".join(parts)
        except Exception:
            raise RagError("docx_illisible", 422)
    raise RagError("type_non_supporte", 415)


def _normalize(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Retire l'octet NUL (0x00) et les autres caractères de contrôle qu'un PDF/DOCX
    # peut contenir dans son texte extrait : PostgreSQL les refuse dans une colonne
    # texte / un tsvector (sinon DataError « cannot contain NUL » → échec du chargement).
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text, size=CHUNK_CHARS, overlap=CHUNK_OVERLAP):
    """Découpe en fenêtres glissantes (~size caractères, avec recouvrement),
    en respectant autant que possible les frontières de mots."""
    text = _normalize(text)
    if not text:
        return []
    chunks = []
    i, n = 0, len(text)
    while i < n:
        end = min(i + size, n)
        if end < n:
            # recule jusqu'à un espace pour ne pas couper un mot
            sp = text.rfind(" ", i + int(size * 0.6), end)
            if sp != -1:
                end = sp
        piece = text[i:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        i = max(end - overlap, i + 1)
    return chunks


# --- Embeddings (Mistral) -----------------------------------------------------
def embeddings_available():
    return bool(os.environ.get("MISTRAL_API_KEY"))


def embed_texts(texts):
    """Renvoie la liste d'embeddings (un par texte) via Mistral, ou lève RagError."""
    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        raise RagError("embeddings_non_configures", 503)
    import requests
    try:
        r = requests.post(
            EMBED_URL, timeout=EMBED_TIMEOUT,
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
            json={"model": EMBED_MODEL, "input": texts})
    except requests.RequestException:
        raise RagError("embeddings_reseau", 502)
    if r.status_code != 200:
        _log.warning("Mistral embeddings : HTTP %s", r.status_code)
        raise RagError("embeddings_upstream", 502)
    try:
        return [row["embedding"] for row in r.json()["data"]]
    except (KeyError, TypeError, ValueError):
        raise RagError("embeddings_illisible", 502)


def _vec_literal(vec):
    """Format littéral pgvector : '[0.1,0.2,...]'."""
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


# --- Aides communes -----------------------------------------------------------
def _now_ms():
    return int(time.time() * 1000)


def validate_ext(filename):
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if ext not in ALLOWED_EXT:
        raise RagError("type_non_supporte", 415)
    return ext


def _clean_visibility(v):
    return v if v in VISIBILITIES else "public"


_TOKEN_RE = re.compile(r"[0-9a-zàâäéèêëîïôöùûüç]+", re.I)


def _tokens(text):
    return [t for t in _TOKEN_RE.findall((text or "").lower()) if len(t) > 2]


# ============================================================================
#  Implémentation en mémoire (repli sans base — recherche lexicale)
# ============================================================================
class MemoryRagStore:
    persistent = False

    def __init__(self, reason="memory"):
        # reason : pourquoi le repli mémoire est actif — « no_database_url »
        # (variable absente) ou « db_connection_failed » (définie mais injoignable).
        self._reason = reason
        self._lock = threading.RLock()
        self._docs = {}      # id -> dict(meta)
        self._chunks = {}    # id -> list[dict(ordinal, content, tokens)]
        self._blobs = {}     # id -> bytes
        self._uploads = {}   # upload_id -> {idx: bytes, meta}
        # Persistance disque optionnelle (sans PostgreSQL) : si RAG_DISK_PATH est
        # défini ET pointe vers un emplacement DURABLE (disque Render monté,
        # volume auto-hébergé…), la base survit aux redémarrages / redéploiements.
        self._disk = (os.environ.get("RAG_DISK_PATH") or "").strip() or None
        self.persistent = bool(self._disk)
        if self._disk:
            self._load()

    def capabilities(self):
        if self._disk:
            return {"persistent": True, "mode": "lexical",
                    "embeddings": False, "vector": False, "reason": "disk"}
        return {"persistent": False, "mode": "lexical",
                "embeddings": False, "vector": False, "reason": self._reason}

    # -- persistance disque optionnelle (repli durable sans PostgreSQL) --
    def _load(self):
        try:
            if not os.path.isfile(self._disk):
                return
            with open(self._disk, "r", encoding="utf-8") as f:
                payload = json.load(f)
            self._docs = payload.get("docs") or {}
            self._chunks = payload.get("chunks") or {}
            self._blobs = {k: base64.b64decode(v)
                           for k, v in (payload.get("blobs") or {}).items()}
            _log.info("RAG : %d document(s) rechargé(s) depuis %s",
                      len(self._docs), self._disk)
        except Exception:
            _log.warning("RAG : snapshot disque illisible (%s) — démarrage à vide",
                         self._disk, exc_info=True)
            self._docs, self._chunks, self._blobs = {}, {}, {}

    def _save(self):
        if not self._disk:
            return
        try:
            payload = {"v": 1, "docs": self._docs, "chunks": self._chunks,
                       "blobs": {k: base64.b64encode(v).decode("ascii")
                                 for k, v in self._blobs.items()}}
            d = os.path.dirname(self._disk)
            if d and not os.path.isdir(d):
                os.makedirs(d, exist_ok=True)
            tmp = self._disk + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            os.replace(tmp, self._disk)
        except Exception:
            _log.warning("RAG : échec d'écriture du snapshot disque (%s)",
                         self._disk, exc_info=True)

    # -- upload par morceaux --
    def create_upload(self, filename, total_bytes):
        ext = validate_ext(filename)
        if total_bytes and total_bytes > MAX_FILE_BYTES:
            raise RagError("fichier_trop_lourd", 413)
        uid = uuid.uuid4().hex
        with self._lock:
            self._uploads[uid] = {"parts": {}, "ext": ext, "filename": filename}
        return uid

    def add_chunk(self, upload_id, idx, data):
        with self._lock:
            up = self._uploads.get(upload_id)
            if not up:
                raise RagError("upload_inconnu", 404)
            up["parts"][int(idx)] = data
            total = sum(len(v) for v in up["parts"].values())
            if total > MAX_FILE_BYTES:
                self._uploads.pop(upload_id, None)
                raise RagError("fichier_trop_lourd", 413)

    def finish_upload(self, upload_id, title, theme, visibility):
        with self._lock:
            up = self._uploads.pop(upload_id, None)
        if not up:
            raise RagError("upload_inconnu", 404)
        data = b"".join(up["parts"][i] for i in sorted(up["parts"]))
        return self._ingest(up["filename"], up["ext"], data, title, theme, visibility)

    def ingest_bytes(self, filename, data, title="", theme="", visibility="public"):
        """Ingestion directe (API / automatisations) : mêmes validations que l'upload.
        Idempotent : si le contenu est déjà présent, renvoie le document existant."""
        ext = validate_ext(filename)
        return self._ingest(filename, ext, data, title, theme, visibility, dedupe="skip")

    def _ingest(self, filename, ext, data, title, theme, visibility, dedupe="reject"):
        if not data:
            raise RagError("fichier_vide", 422)
        if len(data) > MAX_FILE_BYTES:
            raise RagError("fichier_trop_lourd", 413)
        # Anti-doublon : contenu déjà présent (même empreinte SHA-256) ? On teste
        # AVANT l'extraction de texte (coûteuse) — inutile de la faire pour rien.
        digest = hashlib.sha256(data).hexdigest()
        with self._lock:
            existing = next((m for m in self._docs.values()
                             if m.get("sha256") == digest), None)
        if existing is not None:
            if dedupe == "skip":
                return dict(existing)
            raise RagError("doublon", 409)
        text = extract_text(ext, data)
        chunks = chunk_text(text)
        if not chunks:
            raise RagError("aucun_texte", 422)
        doc_id = uuid.uuid4().hex
        meta = {
            "id": doc_id, "title": (title or filename).strip()[:300],
            "filename": filename, "ext": ext, "theme": (theme or "Général").strip()[:80],
            "visibility": _clean_visibility(visibility), "bytes": len(data),
            "sha256": digest, "nb_chunks": len(chunks),
            "chunks_indexed": len(chunks), "status": "ready", "mode": "lexical",
            "error": None, "created_at": _now_ms(), "updated_at": _now_ms(),
        }
        with self._lock:
            self._docs[doc_id] = meta
            self._chunks[doc_id] = [
                {"ordinal": i, "content": c, "tokens": _tokens(c)}
                for i, c in enumerate(chunks)]
            self._blobs[doc_id] = data
            self._save()
        return dict(meta)

    def index_next(self, doc_id, batch=EMBED_BATCH):
        # recherche lexicale : rien à indexer
        with self._lock:
            meta = self._docs.get(doc_id)
        if not meta:
            raise RagError("document_inconnu", 404)
        return {"done": True, "indexed": meta["nb_chunks"], "total": meta["nb_chunks"]}

    def reindex(self, doc_id):
        # Store en mémoire (lexical) : aucune recherche vectorielle possible.
        with self._lock:
            if doc_id not in self._docs:
                raise RagError("document_inconnu", 404)
        raise RagError("embeddings_non_configures", 409)

    def list_documents(self):
        with self._lock:
            return [dict(m) for m in sorted(self._docs.values(),
                                            key=lambda d: d["created_at"], reverse=True)]

    def get_blob(self, doc_id):
        with self._lock:
            if doc_id not in self._blobs:
                raise RagError("document_inconnu", 404)
            return self._docs[doc_id]["filename"], self._blobs[doc_id]

    def document_text(self, doc_id, limit=200000):
        """Texte lisible du document (fragments indexés réassemblés) — pour la
        lecture en ligne dans la console, tous formats confondus."""
        with self._lock:
            meta = self._docs.get(doc_id)
            if not meta:
                raise RagError("document_inconnu", 404)
            chunks = sorted(self._chunks.get(doc_id, []), key=lambda c: c["ordinal"])
        text = "\n\n".join(c["content"] for c in chunks)
        return {"title": meta.get("title"), "filename": meta.get("filename"),
                "theme": meta.get("theme"), "text": text[:limit]}

    def delete_document(self, doc_id):
        with self._lock:
            if doc_id not in self._docs:
                raise RagError("document_inconnu", 404)
            self._docs.pop(doc_id, None)
            self._chunks.pop(doc_id, None)
            self._blobs.pop(doc_id, None)
            self._save()
        return True

    def stats(self):
        with self._lock:
            docs = list(self._docs.values())
            themes = {}
            for d in docs:
                themes[d["theme"]] = themes.get(d["theme"], 0) + 1
            return {"documents": len(docs),
                    "chunks": sum(len(c) for c in self._chunks.values()),
                    "themes": themes, "mode": "lexical",
                    "storage": {"db_bytes": None,
                                "rag_bytes": sum(len(b) for b in self._blobs.values())}}

    def search(self, query, k=5, public_only=True, theme=None, doc_ids=None):
        qtok = _tokens(query)
        if not qtok:
            return []
        qset = set(qtok)
        doc_ids = set(doc_ids) if doc_ids else None
        results = []
        with self._lock:
            for doc_id, chunks in self._chunks.items():
                meta = self._docs[doc_id]
                if doc_ids and doc_id not in doc_ids:
                    continue
                if public_only and meta["visibility"] != "public":
                    continue
                if theme and meta["theme"] != theme:
                    continue
                for ch in chunks:
                    ctok = ch["tokens"]
                    if not ctok:
                        continue
                    inter = qset.intersection(ctok)
                    if not inter:
                        continue
                    score = len(inter) / (len(qset) ** 0.5 * len(set(ctok)) ** 0.5)
                    results.append((score, meta, ch["content"]))
        results.sort(key=lambda r: r[0], reverse=True)
        return [{"doc_id": m["id"], "title": m["title"], "theme": m["theme"],
                 "visibility": m["visibility"], "content": c, "score": round(s, 4)}
                for s, m, c in results[:k]]


# ============================================================================
#  Implémentation PostgreSQL (persistante)
# ============================================================================
_BASE_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS rag_documents (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        filename TEXT NOT NULL,
        ext TEXT,
        theme TEXT,
        visibility TEXT NOT NULL DEFAULT 'public',
        bytes BIGINT,
        sha256 TEXT,
        nb_chunks INT NOT NULL DEFAULT 0,
        chunks_indexed INT NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'processing',
        mode TEXT,
        error TEXT,
        created_at BIGINT,
        updated_at BIGINT)""",
    """CREATE TABLE IF NOT EXISTS rag_chunks (
        id BIGSERIAL PRIMARY KEY,
        doc_id TEXT NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
        ordinal INT NOT NULL,
        content TEXT NOT NULL,
        tsv tsvector)""",
    "CREATE INDEX IF NOT EXISTS rag_chunks_doc_idx ON rag_chunks(doc_id)",
    "CREATE INDEX IF NOT EXISTS rag_chunks_tsv_idx ON rag_chunks USING GIN(tsv)",
    """CREATE TABLE IF NOT EXISTS rag_blobs (
        doc_id TEXT PRIMARY KEY REFERENCES rag_documents(id) ON DELETE CASCADE,
        data BYTEA NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS rag_uploads (
        upload_id TEXT NOT NULL,
        idx INT NOT NULL,
        data BYTEA NOT NULL,
        created_at BIGINT,
        PRIMARY KEY (upload_id, idx))""",
]


class PostgresRagStore:
    persistent = True
    _SCHEMA_LOCK = 907245

    def __init__(self, dsn):
        from psycopg_pool import ConnectionPool
        sep = "&" if "?" in dsn else "?"
        # client_encoding=UTF8 : les libellés accentués (thèmes, contenu) sont
        # toujours transmis en UTF-8, quel que soit l'encodage du serveur.
        dsn = dsn + sep + "connect_timeout=5&client_encoding=UTF8"
        self._pool = ConnectionPool(dsn, min_size=1, max_size=4,
                                    kwargs={"autocommit": True}, timeout=8, open=True)
        self.vector_mode = False
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
                for stmt in _BASE_SCHEMA:
                    conn.execute(stmt)
                # Tente pgvector ; sinon, repli plein-texte (déjà en place via tsv).
                try:
                    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    conn.execute("ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS "
                                 "embedding vector(%d)" % EMBED_DIM)
                    self.vector_mode = True
                except Exception as exc:
                    self.vector_mode = False
                    _log.info("pgvector indisponible (%s) — recherche plein-texte.",
                              type(exc).__name__)
            finally:
                conn.execute("SELECT pg_advisory_unlock(%s)", (self._SCHEMA_LOCK,))

    def capabilities(self):
        emb = self.vector_mode and embeddings_available()
        return {"persistent": True,
                "mode": "vectoriel" if emb else "texte_integral",
                "embeddings": emb, "vector": self.vector_mode}

    # -- upload par morceaux (assemblé en base : robuste multi-instance) --
    def create_upload(self, filename, total_bytes):
        ext = validate_ext(filename)
        if total_bytes and total_bytes > MAX_FILE_BYTES:
            raise RagError("fichier_trop_lourd", 413)
        uid = uuid.uuid4().hex
        # purge opportuniste des uploads inachevés (> 1 h)
        try:
            with self._pool.connection() as conn:
                conn.execute("DELETE FROM rag_uploads WHERE created_at < %s",
                             (_now_ms() - 3600_000,))
        except Exception:
            pass
        return uid + "." + ext

    def add_chunk(self, upload_id, idx, data):
        if len(data) > MAX_CHUNK_UPLOAD + 4096:
            raise RagError("morceau_trop_grand", 413)
        with self._pool.connection() as conn:
            total = conn.execute("SELECT COALESCE(SUM(octet_length(data)),0) "
                                 "FROM rag_uploads WHERE upload_id=%s",
                                 (upload_id,)).fetchone()[0]
            if total + len(data) > MAX_FILE_BYTES:
                conn.execute("DELETE FROM rag_uploads WHERE upload_id=%s", (upload_id,))
                raise RagError("fichier_trop_lourd", 413)
            conn.execute("INSERT INTO rag_uploads(upload_id,idx,data,created_at) "
                         "VALUES(%s,%s,%s,%s) ON CONFLICT (upload_id,idx) DO NOTHING",
                         (upload_id, int(idx), data, _now_ms()))

    def finish_upload(self, upload_id, title, theme, visibility):
        ext = (upload_id.rsplit(".", 1)[-1] if "." in upload_id else "").lower()
        with self._pool.connection() as conn:
            rows = conn.execute("SELECT data FROM rag_uploads WHERE upload_id=%s "
                                "ORDER BY idx", (upload_id,)).fetchall()
            if not rows:
                raise RagError("upload_inconnu", 404)
            data = b"".join(bytes(r[0]) for r in rows)
            filename = title if (title and "." in title) else (title or "document") + "." + ext
            try:
                meta = self._ingest(conn, filename, ext, data, title, theme, visibility)
            finally:
                # Nettoyage best-effort : si la connexion vient d'être perdue (grosse
                # écriture), ne pas transformer un succès en erreur — la purge auto
                # (> 1 h) de create_upload rattrapera ces restes.
                try:
                    conn.execute("DELETE FROM rag_uploads WHERE upload_id=%s", (upload_id,))
                except Exception:
                    _log.warning("RAG : nettoyage de l'upload %s reporté (purge auto).", upload_id)
        return meta

    def ingest_bytes(self, filename, data, title="", theme="", visibility="public"):
        """Ingestion directe (API / automatisations) : mêmes validations que l'upload.
        Idempotent : si le contenu est déjà présent, renvoie le document existant."""
        ext = validate_ext(filename)
        with self._pool.connection() as conn:
            return self._ingest(conn, filename, ext, data, title, theme, visibility,
                                dedupe="skip")

    def _ingest(self, conn, filename, ext, data, title, theme, visibility, dedupe="reject"):
        if not data:
            raise RagError("fichier_vide", 422)
        if len(data) > MAX_FILE_BYTES:
            raise RagError("fichier_trop_lourd", 413)
        # Anti-doublon : contenu déjà présent (même empreinte SHA-256) ? On teste
        # AVANT l'extraction de texte (coûteuse) — inutile de la faire pour rien.
        digest = hashlib.sha256(data).hexdigest()
        existing = conn.execute(
            "SELECT " + self._COLS + " FROM rag_documents WHERE sha256=%s LIMIT 1",
            (digest,)).fetchone()
        if existing is not None:
            if dedupe == "skip":
                return self._row_to_dict(existing)
            raise RagError("doublon", 409)
        text = extract_text(ext, data)
        chunks = chunk_text(text)
        if not chunks:
            raise RagError("aucun_texte", 422)
        doc_id = uuid.uuid4().hex
        emb_on = self.vector_mode and embeddings_available()
        status = "indexing" if emb_on else "ready"
        mode = "vectoriel" if emb_on else "texte_integral"
        indexed = 0 if emb_on else len(chunks)
        now = _now_ms()
        # ESSENTIEL (métadonnées + fragments cherchables) : dans une transaction.
        # Toute erreur est journalisée et renvoyée PROPREMENT (jamais de 500 opaque).
        # Le contenu texte est déjà nettoyé (NUL, caractères de contrôle).
        try:
            with conn.transaction():
                conn.execute(
                    "INSERT INTO rag_documents(id,title,filename,ext,theme,visibility,bytes,"
                    "sha256,nb_chunks,chunks_indexed,status,mode,created_at,updated_at) "
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (doc_id, (title or filename).strip()[:300], filename, ext,
                     (theme or "Général").strip()[:80], _clean_visibility(visibility),
                     len(data), digest, len(chunks), indexed,
                     status, mode, now, now))
                # Insertion groupée des fragments (executemany, mode pipeline psycopg) :
                # un seul aller-retour groupé au lieu d'un par fragment — bien plus rapide
                # pour les gros PDF/DOCX (évite d'approcher le délai d'expiration du worker).
                with conn.cursor() as cur:
                    cur.executemany(
                        "INSERT INTO rag_chunks(doc_id,ordinal,content,tsv) "
                        "VALUES(%s,%s,%s,to_tsvector('french',%s))",
                        [(doc_id, i, c, c) for i, c in enumerate(chunks)])
        except Exception:
            _log.exception("RAG : échec d'enregistrement (%s, %d fragments, %d octets)",
                           filename, len(chunks), len(data))
            raise RagError("traitement_echec", 500)
        # BEST-EFFORT : le fichier d'origine ne sert QU'AU téléchargement, pas à la
        # recherche. S'il ne peut être stocké (taille, quota disque de la base…), le
        # document reste pleinement indexé et cherchable — on renonce juste à pouvoir
        # re-télécharger l'original. Cela évite qu'un gros blob fasse échouer tout l'upload.
        try:
            conn.execute("INSERT INTO rag_blobs(doc_id,data) VALUES(%s,%s)", (doc_id, data))
        except Exception:
            _log.warning("RAG : fichier d'origine non conservé pour %s (%d octets) — "
                         "document indexé et cherchable malgré tout.", doc_id, len(data))
        # Métadonnées construites localement (aucune requête supplémentaire) : la
        # réponse reste correcte même si la connexion a été perdue après le commit.
        return {
            "id": doc_id, "title": (title or filename).strip()[:300],
            "filename": filename, "ext": ext, "theme": (theme or "Général").strip()[:80],
            "visibility": _clean_visibility(visibility), "bytes": len(data),
            "sha256": digest, "nb_chunks": len(chunks), "chunks_indexed": indexed,
            "status": status, "mode": mode, "error": None,
            "created_at": now, "updated_at": now,
        }

    def index_next(self, doc_id, batch=EMBED_BATCH):
        """Embarque le prochain lot de chunks (piloté par le client). En mode
        plein-texte, rien à faire. En cas d'échec d'embedding, repli plein-texte."""
        with self._pool.connection() as conn:
            row = conn.execute("SELECT status,nb_chunks,chunks_indexed FROM rag_documents "
                               "WHERE id=%s", (doc_id,)).fetchone()
            if not row:
                raise RagError("document_inconnu", 404)
            status, nb, done = row
            if status != "indexing" or not self.vector_mode:
                return {"done": True, "indexed": nb, "total": nb}
            rows = conn.execute(
                "SELECT id,content FROM rag_chunks WHERE doc_id=%s AND embedding IS NULL "
                "ORDER BY ordinal LIMIT %s", (doc_id, batch)).fetchall()
            if not rows:
                conn.execute("UPDATE rag_documents SET status='ready',mode='vectoriel',"
                             "chunks_indexed=nb_chunks,updated_at=%s WHERE id=%s",
                             (_now_ms(), doc_id))
                return {"done": True, "indexed": nb, "total": nb}
            try:
                vecs = embed_texts([c for _, c in rows])
            except RagError as exc:
                # Repli gracieux : le document reste cherchable en plein-texte.
                conn.execute("UPDATE rag_documents SET status='ready',"
                             "mode='texte_integral',error=%s,updated_at=%s WHERE id=%s",
                             (exc.code, _now_ms(), doc_id))
                return {"done": True, "indexed": done, "total": nb, "degraded": exc.code}
            with conn.transaction():
                for (cid, _), vec in zip(rows, vecs):
                    conn.execute("UPDATE rag_chunks SET embedding=%s::vector WHERE id=%s",
                                 (_vec_literal(vec), cid))
                done = conn.execute(
                    "UPDATE rag_documents SET chunks_indexed=chunks_indexed+%s,"
                    "updated_at=%s WHERE id=%s RETURNING chunks_indexed",
                    (len(rows), _now_ms(), doc_id)).fetchone()[0]
                if done >= nb:
                    conn.execute("UPDATE rag_documents SET status='ready' WHERE id=%s", (doc_id,))
            return {"done": done >= nb, "indexed": done, "total": nb}

    def reindex(self, doc_id):
        """Régénère la recherche vectorielle d'un document : efface ses embeddings et
        le repasse en 'indexing' pour qu'index_next les recalcule (ex. après avoir
        activé MISTRAL_API_KEY sur des documents déjà chargés en plein-texte)."""
        with self._pool.connection() as conn:
            row = conn.execute("SELECT nb_chunks FROM rag_documents WHERE id=%s",
                               (doc_id,)).fetchone()
            if not row:
                raise RagError("document_inconnu", 404)
            if not (self.vector_mode and embeddings_available()):
                raise RagError("embeddings_non_configures", 409)
            with conn.transaction():
                conn.execute("UPDATE rag_chunks SET embedding=NULL WHERE doc_id=%s", (doc_id,))
                conn.execute("UPDATE rag_documents SET status='indexing',mode='vectoriel',"
                             "chunks_indexed=0,error=NULL,updated_at=%s WHERE id=%s",
                             (_now_ms(), doc_id))
        return {"done": False, "indexed": 0, "total": row[0]}

    _COLS = ("id,title,filename,ext,theme,visibility,bytes,sha256,nb_chunks,"
             "chunks_indexed,status,mode,error,created_at,updated_at")

    def _doc_row(self, conn, doc_id):
        r = conn.execute("SELECT %s FROM rag_documents WHERE id=%%s" % self._COLS,
                         (doc_id,)).fetchone()
        return self._row_to_dict(r) if r else None

    def _row_to_dict(self, r):
        keys = self._COLS.split(",")
        return dict(zip(keys, r))

    def list_documents(self):
        with self._pool.connection() as conn:
            rows = conn.execute("SELECT %s FROM rag_documents ORDER BY created_at DESC "
                                "LIMIT 500" % self._COLS).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_blob(self, doc_id):
        with self._pool.connection() as conn:
            r = conn.execute("SELECT d.filename,b.data FROM rag_blobs b "
                             "JOIN rag_documents d ON d.id=b.doc_id WHERE b.doc_id=%s",
                             (doc_id,)).fetchone()
            if not r:
                # Document présent mais original non conservé (stockage best-effort) ?
                if conn.execute("SELECT 1 FROM rag_documents WHERE id=%s",
                                (doc_id,)).fetchone():
                    raise RagError("original_indisponible", 410)
                raise RagError("document_inconnu", 404)
        return r[0], bytes(r[1])

    def document_text(self, doc_id, limit=200000):
        """Texte lisible du document (fragments indexés réassemblés) — pour la
        lecture en ligne dans la console, tous formats confondus."""
        with self._pool.connection() as conn:
            meta = conn.execute("SELECT title,filename,theme FROM rag_documents "
                                "WHERE id=%s", (doc_id,)).fetchone()
            if not meta:
                raise RagError("document_inconnu", 404)
            rows = conn.execute("SELECT content FROM rag_chunks WHERE doc_id=%s "
                                "ORDER BY ordinal", (doc_id,)).fetchall()
        text = "\n\n".join(r[0] for r in rows)
        return {"title": meta[0], "filename": meta[1], "theme": meta[2],
                "text": text[:limit]}

    def delete_document(self, doc_id):
        with self._pool.connection() as conn:
            n = conn.execute("DELETE FROM rag_documents WHERE id=%s", (doc_id,)).rowcount
        if not n:
            raise RagError("document_inconnu", 404)
        return True

    def stats(self):
        with self._pool.connection() as conn:
            docs = conn.execute("SELECT count(*) FROM rag_documents").fetchone()[0]
            chunks = conn.execute("SELECT count(*) FROM rag_chunks").fetchone()[0]
            themes = {}
            for theme, c in conn.execute(
                    "SELECT theme,count(*) FROM rag_documents GROUP BY theme "
                    "ORDER BY 2 DESC").fetchall():
                themes[theme or "Général"] = c
            # Occupation disque (surveillance de la limite de stockage de la base) :
            # taille totale de la base + part des tables RAG (fragments, originaux…).
            storage = None
            try:
                db_b = conn.execute(
                    "SELECT pg_database_size(current_database())").fetchone()[0]
                rag_b = conn.execute(
                    "SELECT COALESCE(SUM(pg_total_relation_size(c.oid)),0) "
                    "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                    "WHERE n.nspname='public' AND c.relkind='r' "
                    "AND c.relname LIKE 'rag\\_%'").fetchone()[0]
                storage = {"db_bytes": int(db_b), "rag_bytes": int(rag_b)}
            except Exception:
                pass
        return {"documents": docs, "chunks": chunks, "themes": themes,
                "mode": self.capabilities()["mode"], "storage": storage}

    def search(self, query, k=5, public_only=True, theme=None, doc_ids=None):
        query = (query or "").strip()
        if not query:
            return []
        where = ["d.status='ready'"]
        params = []
        if public_only:
            where.append("d.visibility='public'")
        if theme:
            where.append("d.theme=%s")
            params.append(theme)
        if doc_ids:
            where.append("d.id = ANY(%s)")
            params.append(list(doc_ids))
        clause = " AND ".join(where)
        with self._pool.connection() as conn:
            # Recherche vectorielle si des embeddings existent et que la requête s'embarque.
            if self.vector_mode and embeddings_available():
                try:
                    qvec = _vec_literal(embed_texts([query])[0])
                    sql = ("SELECT c.content,d.id,d.title,d.theme,d.visibility,"
                           "1-(c.embedding <=> %s::vector) AS score "
                           "FROM rag_chunks c JOIN rag_documents d ON d.id=c.doc_id "
                           "WHERE c.embedding IS NOT NULL AND " + clause +
                           " ORDER BY c.embedding <=> %s::vector LIMIT %s")
                    rows = conn.execute(sql, [qvec] + params + [qvec, k]).fetchall()
                    if rows:
                        return [self._hit(r) for r in rows]
                except RagError:
                    pass  # repli plein-texte ci-dessous
            # Recherche plein-texte (français).
            sql = ("SELECT c.content,d.id,d.title,d.theme,d.visibility,"
                   "ts_rank(c.tsv, plainto_tsquery('french',%s)) AS score "
                   "FROM rag_chunks c JOIN rag_documents d ON d.id=c.doc_id "
                   "WHERE c.tsv @@ plainto_tsquery('french',%s) AND " + clause +
                   " ORDER BY score DESC LIMIT %s")
            rows = conn.execute(sql, [query, query] + params + [k]).fetchall()
        return [self._hit(r) for r in rows]

    @staticmethod
    def _hit(r):
        return {"content": r[0], "doc_id": r[1], "title": r[2], "theme": r[3],
                "visibility": r[4], "score": round(float(r[5]), 4)}


# Délai minimal entre deux essais de reconnexion automatiques (secondes).
_RECONNECT_MIN_INTERVAL = float(os.environ.get("RAG_RECONNECT_INTERVAL", "20"))


class ResilientRagStore:
    """Enveloppe résiliente autour de PostgreSQL — corrige le blocage « mode
    mémoire jusqu'au prochain redéploiement ».

    Problème résolu : auparavant, le choix du moteur était fait une seule fois
    au démarrage. Si la base était momentanément injoignable à cet instant (base
    froide sur Render, blip réseau, base qui se réveille), l'application restait
    bloquée en mémoire (non persistante) pour toute la durée du process — la
    seule issue était un redéploiement manuel.

    Ici, si la connexion échoue, on sert temporairement en mémoire MAIS on
    retente la connexion à chaque consultation de la base (chargement de la page
    admin) et sur demande explicite (bouton « Reconnecter »). La persistance se
    rétablit donc automatiquement, sans redéploiement, dès que la base redevient
    joignable. Aucune reconnexion n'est tentée au milieu d'une séquence d'upload
    (on ne change pas de moteur en cours de route)."""

    def __init__(self, dsn):
        self._dsn = dsn
        self._pg = None
        # Repli mémoire : DATABASE_URL est défini mais la connexion a échoué.
        self._mem = MemoryRagStore(reason="db_connection_failed")
        self._last_try = 0.0
        self._last_error = ""
        self._lock = threading.Lock()
        # Un seul essai au démarrage : ne pas rallonger le boot si la base est
        # froide (chaque essai peut bloquer ~5-8 s). Le rétablissement se fait
        # ensuite tout seul au 1er chargement de la page admin (self-healing).
        self._try_connect(attempts=1)

    @staticmethod
    def _sanitize_error(exc):
        """Message d'erreur affichable dans l'admin : jamais de secret.
        On retire toute URL de connexion et tout fragment password=… que le
        driver pourrait inclure, et on borne la longueur."""
        msg = " ".join(str(exc).split())
        msg = re.sub(r"postgres(?:ql)?://\S+", "postgresql://…", msg)
        msg = re.sub(r"password=\S+", "password=…", msg)
        return msg[:300]

    def _probe_error(self):
        """Erreur libpq précise via une connexion directe : le pool n'expose
        qu'un délai générique (« couldn't get a connection after N sec ») qui
        ne dit pas si l'hôte est introuvable, l'authentification refusée ou la
        base suspendue. Renvoie "" si la connexion directe passe."""
        try:
            import psycopg
            conn = psycopg.connect(self._dsn, connect_timeout=5)
            conn.close()
            return ""
        except Exception as exc:
            return self._sanitize_error(exc)

    def _try_connect(self, attempts=1):
        for i in range(attempts):
            try:
                pg = PostgresRagStore(self._dsn)
                self._pg = pg
                self._last_error = ""
                _log.info("RAG : PostgreSQL connecté (%s).", pg.capabilities()["mode"])
                return True
            except Exception as exc:
                self._pg = None
                self._last_error = self._probe_error() or self._sanitize_error(exc)
                _log.warning("RAG : PostgreSQL injoignable (essai %d/%d : %s).",
                             i + 1, attempts, self._last_error)
                if i + 1 < attempts:
                    time.sleep(1.5)
        return False

    def _maybe_reconnect(self):
        if self._pg is not None:
            return
        if time.time() - self._last_try < _RECONNECT_MIN_INTERVAL:
            return
        with self._lock:
            if self._pg is None and time.time() - self._last_try >= _RECONNECT_MIN_INTERVAL:
                self._last_try = time.time()
                self._try_connect(attempts=1)

    def _store(self):
        return self._pg if self._pg is not None else self._mem

    def reconnect(self):
        """Essai de reconnexion immédiat (bouton admin). Renvoie True si connecté."""
        with self._lock:
            self._last_try = time.time()
            self._try_connect(attempts=1)
        return self._pg is not None

    # Opérations de consultation : occasion de retenter la connexion.
    def capabilities(self):
        self._maybe_reconnect()
        caps = self._store().capabilities()
        # En repli mémoire : joindre la cause exacte du dernier échec de
        # connexion (assainie) pour un diagnostic immédiat dans l'admin.
        if self._pg is None and self._last_error:
            caps = dict(caps)
            caps["detail"] = self._last_error
        return caps

    def list_documents(self):
        self._maybe_reconnect()
        return self._store().list_documents()

    def stats(self):
        self._maybe_reconnect()
        return self._store().stats()

    def __getattr__(self, name):
        # Toutes les autres méthodes (upload, recherche, suppression…) : délègue
        # au moteur actif SANS tenter de reconnexion (pas de changement de moteur
        # au milieu d'une séquence d'upload). Les attributs internes (préfixe _)
        # ne sont jamais délégués (évite toute récursion).
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._store(), name)


def make_rag_store():
    """Store persistant si DATABASE_URL est défini, sinon en mémoire (non persistant).

    Avec DATABASE_URL, on renvoie une enveloppe résiliente (ResilientRagStore)
    qui se rétablit toute seule si la base était injoignable au démarrage."""
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        _log.info("RAG : pas de DATABASE_URL — base de connaissance en mémoire (non persistante).")
        return MemoryRagStore(reason="no_database_url")
    if dsn.startswith("postgres://"):
        dsn = "postgresql://" + dsn[len("postgres://"):]
    return ResilientRagStore(dsn)


# --- Déduplication des documents ----------------------------------------------
# Un doublon = deux documents au contenu identique (même empreinte SHA-256).
# À défaut d'empreinte (cas rare), on retombe sur (nom de fichier + taille).
def _dup_key(d):
    sha = (d.get("sha256") or "").strip()
    if sha:
        return "h:" + sha
    return "fb:%s:%d" % ((d.get("filename") or "").lower(), int(d.get("bytes") or 0))


def duplicate_groups(store):
    """Renvoie les groupes de documents en doublon (contenu identique).

    Pour chaque groupe on désigne le document à CONSERVER — le mieux indexé,
    puis le plus ancien (l'original) — et les autres, supprimables. Ne renvoie
    que les groupes d'au moins deux documents. Aucune suppression ici."""
    by_key = {}
    for d in store.list_documents():
        by_key.setdefault(_dup_key(d), []).append(d)
    groups = []
    for items in by_key.values():
        if len(items) < 2:
            continue
        ordered = sorted(items, key=lambda d: (
            -(d.get("chunks_indexed") or 0),               # le mieux indexé d'abord
            0 if d.get("status") == "ready" else 1,        # puis « prêt »
            d.get("created_at") or 0))                     # puis le plus ancien
        groups.append({"keep": ordered[0], "remove": ordered[1:]})
    groups.sort(key=lambda g: -len(g["remove"]))
    return groups


def dedupe(store, dry_run=False):
    """Détecte les doublons et (si dry_run=False) supprime les copies en trop,
    en conservant un exemplaire par contenu. Renvoie un compte-rendu."""
    groups = duplicate_groups(store)
    removable = sum(len(g["remove"]) for g in groups)
    removed = errors = 0
    if not dry_run:
        for g in groups:
            for d in g["remove"]:
                try:
                    store.delete_document(d["id"])
                    removed += 1
                except RagError:
                    errors += 1
    return {"groups": len(groups), "removable": removable,
            "removed": removed, "errors": errors}


# --- Contexte pour le LLM -----------------------------------------------------
def build_context(hits, max_chars=3500):
    """Assemble les extraits récupérés en un bloc de contexte sourcé pour le LLM."""
    if not hits:
        return ""
    out, total = [], 0
    for h in hits:
        block = "[%s] %s" % (h.get("title") or "Document", (h.get("content") or "").strip())
        if total + len(block) > max_chars:
            break
        out.append(block)
        total += len(block)
    if not out:
        return ""
    return ("Extraits de la base de connaissance CONSEILPREV (source interne fiable ; "
            "cite le titre entre crochets si tu t'en sers, et ignore les extraits non "
            "pertinents) :\n\n" + "\n\n---\n\n".join(out))
