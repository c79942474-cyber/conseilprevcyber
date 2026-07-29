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
import math
import os
import re
import threading
from contextlib import contextmanager
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
ALLOWED_EXT = {"txt", "md", "csv", "log", "json", "pdf", "docx", "xlsx", "xlsm",
               "pptx", "pptm"}
VISIBILITIES = ("public", "internal")

# Thèmes proposés (autocomplétion à l'upload + filtre). Le champ reste en texte
# libre : cette liste ne fait qu'aider à catégoriser de façon cohérente pour
# retrouver les documents plus vite.
#
# Familles de thèmes — SOURCE UNIQUE du vocabulaire.
#
# THEMES en est dérivé par simple aplatissement : impossible qu'un thème existe
# dans une liste et pas dans l'autre. Les familles servent à l'interface, qui
# propose les domaines par groupes plutôt qu'en une seule rangée d'étiquettes
# devenue illisible — et qui sépare les ENTREPRISES du reste, car classer un
# document par client relève d'une autre intention que le classer par sujet.
THEME_FAMILLES = [
    ("Normes & réglementations", [
        # « Normes IEC » regroupe les normes CEI hors 62443 (61850, 62351,
        # 60870…). « IEC 62443 » et « Sûreté fonctionnelle (IEC 61508/61511) »
        # restent des entrées distinctes : des documents y sont déjà classés,
        # les fondre ici les rendrait introuvables.
        "Normes IEC",
        "IEC 62443",
        "ISO 27001 / 27002",
        "ISO Standards",
        "Normes",
        "NIST CSF / SP 800-82",
        "NIS2",
        "DORA",
        "RGPD",
        "AI Act",
        "Cyber Resilience Act",
        "Sûreté fonctionnelle (IEC 61508/61511)",
    ]),
    # ANSSI : famille à part entière (guides, référentiels de qualification,
    # méthodes). « Guides ANSSI » est conservé tel quel — des documents y sont
    # déjà classés et le retirer les rendrait orphelins.
    ("ANSSI", [
        "ANSSI",
        "ANSSI / Guides & recommandations",
        "ANSSI / Référentiels & qualification",
        "ANSSI / Méthodes (EBIOS RM)",
        "Guides ANSSI",
    ]),
    ("Architecture & technique OT/IT", [
        "Architecture & segmentation",
        "Inventaire & cartographie",
        "Analyse de risques",
        "Durcissement & configuration",
        "Gestion des correctifs",
        "Gestion des accès & identités",
        "Accès distant & télémaintenance",
        "Sécurité réseau & pare-feu",
        "Automates, SCADA & DCS",
        "SCADA",
        "IIoT & objets connectés",
        "Automotive",
        "Cryptographie & PKI",
        "Supervision & détection",
        "Réponse à incident",
        "Continuité & résilience (PRA/PCA)",
    ]),
    ("Gouvernance & organisation", [
        "Gouvernance & CSMS",
        "Sensibilisation & formation",
        "Gestion des prestataires",
        "Conformité & audit",
    ]),
    # Corpus juridique : alimente le conseil juridique assisté (voir juridique.py).
    # Les textes officiels n'ont pas vocation à être chargés ici — le référentiel
    # les identifie et renvoie aux sources officielles, toujours à jour. Ce qui a
    # de la valeur dans la base, ce sont les pièces PROPRES au cabinet et à ses
    # clients : contrats types, notes, positions d'autorité annotées, décisions.
    ("Juridique & contrats", [
        "Juridique / Textes & réglementation",
        "Juridique / Doctrine & lignes directrices",
        "Juridique / Contrats & clausiers",
        "Juridique / Contrats fournisseurs",
        "Juridique / Notes & consultations",
        "Juridique / Jurisprudence & sanctions",
        "Juridique / IA Act",
        "Juridique / NIS 2 & DORA",
        "Juridique / RGPD & données",
        "Juridique / Marchés & appels d'offres",
    ]),
    ("Métier & livrables", [
        "AMOA SI Industriel",
        "Cahier des charges & CCTP",
        "Plan de remédiation",
        "Études de cas",
    ]),
    # Sous-dossiers via « / », imbrication multi-niveaux. Cette famille a son
    # propre bloc de chargement dans l'admin : elle n'est pas proposée dans le
    # sélecteur général.
    ("Engineering", [
        "Engineering",
        "Engineering / Projet OWFarm",
        "Engineering / Projet OWFarm / BSH2 Package",
        "Engineering / Projet OWFarm / Safety",
        "Engineering / Projet OWFarm / Fire fighting",
        "Engineering / Projet OWFarm / Fire fighting / Watermist",
        "Engineering / Projet OWFarm / Rules",
        "Engineering / Projet OWFarm / Rules / DNV",
        "Engineering / Projet OWFarm / Rules / NFPA",
        "Engineering / Oil & Gas",
        "Engineering / Oil & Gas / GNL",
        "Engineering / Oil & Gas / GNL / LNG Guidance Projects",
        "Engineering / Oil & Gas / Safety",
        "Engineering / Oil & Gas / Rules",
    ]),
    # Ordre alphabétique : sans critère de tri évident (ni chronologie ni
    # importance), c'est le seul qui permette de trouver un nom sans le chercher.
    ("Entreprises & références", [
        "Alstom",
        "Atos",
        "EDF",
        "GRDF",
        "Renault",
        "SGP",
        "Technip",
    ]),
    ("Divers", [
        "Veille",
        "Général",
    ]),
]

# Vocabulaire à plat (validation des reclassements, autocomplétion).
THEMES = [t for _, ts in THEME_FAMILLES for t in ts]

# La famille dédiée aux entreprises est nommée ici plutôt que devinée côté
# interface : un nom recopié dans deux fichiers finit toujours par diverger.
FAMILLE_ENTREPRISES = "Entreprises & références"
FAMILLE_ENGINEERING = "Engineering"


class RagError(Exception):
    """Erreur RAG portant un code interne + un statut HTTP (+ détail sûr éventuel).

    `detail` est un message court, déjà assaini (ni URL ni mot de passe), destiné
    à être montré à l'administrateur pour comprendre une panne — p. ex. la vraie
    cause d'un échec d'enregistrement PostgreSQL."""

    def __init__(self, code, status=400, detail=""):
        super().__init__(code)
        self.code = code
        self.status = status
        self.detail = detail or ""


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
    if ext in ("xlsx", "xlsm"):
        try:
            import openpyxl
        except Exception:  # absent OU binding cassé : message propre, pas de 500 brut
            raise RagError("xlsx_support_absent", 500)
        try:
            wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        except Exception:
            raise RagError("xlsx_illisible", 422)
        # Chaque feuille est aplatie en lignes « cellule | cellule | … » : le
        # tableur devient un texte cherchable (recherche plein-texte ET vectorielle).
        parts = []
        try:
            for ws in wb.worksheets:
                parts.append("## " + (ws.title or "Feuille"))
                for row in ws.iter_rows(values_only=True):
                    cells = [str(c) for c in row if c is not None and str(c).strip() != ""]
                    if cells:
                        parts.append(" | ".join(cells))
        finally:
            try:
                wb.close()
            except Exception:
                pass
        return "\n".join(parts)
    if ext in ("pptx", "pptm"):
        try:
            from pptx import Presentation
        except Exception:  # absent OU binding cassé : message propre, pas de 500 brut
            raise RagError("pptx_support_absent", 500)
        try:
            prs = Presentation(io.BytesIO(data))
        except Exception:
            raise RagError("pptx_illisible", 422)
        # Texte de chaque diapositive (formes, tableaux) + notes du présentateur :
        # la présentation devient cherchable (plein-texte ET vectorielle).
        parts = []
        for i, slide in enumerate(prs.slides, 1):
            parts.append("## Diapositive %d" % i)
            for shape in slide.shapes:
                if shape.has_text_frame:
                    t = shape.text_frame.text.strip()
                    if t:
                        parts.append(t)
                if shape.has_table:
                    for row in shape.table.rows:
                        cells = [c.text.strip() for c in row.cells if c.text.strip()]
                        if cells:
                            parts.append(" | ".join(cells))
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes = slide.notes_slide.notes_text_frame.text.strip()
                if notes:
                    parts.append("Notes : " + notes)
        return "\n".join(parts)
    raise RagError("type_non_supporte", 415)


def db_identity(dsn):
    """Identité LISIBLE de la base visée : hôte + hébergeur reconnu. Jamais
    d'identifiant (ni utilisateur, ni mot de passe).

    Sert à savoir d'un coup d'œil SUR QUELLE BASE on travaille. Changer
    DATABASE_URL ne déplace aucune donnée : après une bascule, la nouvelle base
    est logiquement vide, ce qui donne l'impression que les documents ont
    disparu. Afficher l'hébergeur et l'hôte lève l'ambiguïté immédiatement."""
    try:
        from urllib.parse import urlparse
        host = (urlparse(dsn).hostname or "").strip()
    except Exception:
        host = ""
    if not host:
        return {"host": "", "provider": ""}
    h = host.lower()
    if "neon.tech" in h or ".neon." in h:
        provider = "Neon"
    elif h.startswith("dpg-"):
        provider = "Render (réseau privé)"
    elif ".render.com" in h:
        provider = "Render (accès externe)"
    elif h in ("localhost", "127.0.0.1", "::1"):
        provider = "locale"
    else:
        provider = "hébergeur non reconnu"
    return {"host": host, "provider": provider}


def formats_available():
    """Formats réellement lisibles par CE serveur.

    Chaque format bureautique dépend d'une bibliothèque optionnelle (pypdf,
    python-docx, openpyxl, python-pptx). Si l'une manque ou que son binding est
    cassé, le chargement échoue par un « …_support_absent » — alors que le
    fichier, lui, est parfaitement valide. Exposer l'information permet de le
    CONSTATER dans l'admin avant même d'essayer, au lieu de le déduire d'un
    échec. Les formats texte (txt, md, csv, log, json) sont toujours lisibles."""
    def ok(module):
        try:
            __import__(module)
            return True
        except Exception:
            return False
    return {"texte": True, "pdf": ok("pypdf"), "docx": ok("docx"),
            "xlsx": ok("openpyxl"), "pptx": ok("pptx")}


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


def _insert_chunks(conn, doc_id, chunks, batch=200):
    """Insère les fragments par lots via un INSERT multi-lignes (une requête par
    lot). Contrairement à executemany (qui, en psycopg 3, passe en mode PIPELINE),
    ceci n'utilise NI requête préparée NI pipeline — condition de compatibilité
    avec un pooler PgBouncer en mode transaction (endpoint « -pooler » de Neon),
    où pipeline/préparé font échouer l'écriture. Reste rapide : ~200 fragments par
    requête, donc très peu d'allers-retours même pour un gros PDF."""
    n = len(chunks)
    for start in range(0, n, batch):
        part = chunks[start:start + batch]
        values = ",".join(["(%s,%s,%s,to_tsvector('french',%s))"] * len(part))
        params = []
        for j, c in enumerate(part):
            params.extend((doc_id, start + j, c, c))
        conn.execute("INSERT INTO rag_chunks(doc_id,ordinal,content,tsv) VALUES " + values, params)


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

# Mots-outils français (≥ 3 lettres ; les mots de 1-2 lettres sont déjà écartés
# par _tokens). Retirés des requêtes ET du score lexical : ils sont fréquents et
# non discriminants, donc ils diluent la pertinence s'ils comptent comme des
# correspondances. On n'y met AUCUN terme métier (risque, audit, réseau, système…).
_STOPWORDS = frozenset("""
les des une aux dans pour avec sur par plus ces ses son qui que quoi
dont mais donc car pas est sont ete etre avoir fait faire leur leurs nos
vos notre votre cette cet ceux celle celles comme entre sous vers chez sans
alors ainsi aussi tres peu tout tous toute toutes autre autres meme encore deja
lors selon afin doit peut cela ceci elle elles ils lui eux nous vous ont avait
avaient sera seront quand puis été être très même déjà où
""".split())


def _tokens(text):
    return [t for t in _TOKEN_RE.findall((text or "").lower()) if len(t) > 2]


def _query_terms(query):
    """Termes significatifs d'une requête : tokens sans mots-outils. Repli sur
    tous les tokens si la requête n'est faite que de mots-outils (ex. « où ? »)."""
    toks = _tokens(query)
    kept = [t for t in toks if t not in _STOPWORDS]
    return kept or toks


def _rrf(lists, k_rrf=60):
    """Reciprocal Rank Fusion : fusionne plusieurs listes classées (ex. lexicale
    + vectorielle) en UN classement robuste, indépendant de l'échelle des scores
    de chaque moteur. score(d) = Σ 1/(k_rrf + rang_d). Méthode éprouvée (TREC,
    moteurs hybrides) : capte à la fois les correspondances de mots et de sens.
    Clé de fusion = contenu du fragment ; conserve la 1re occurrence rencontrée
    (les listes sont passées par ordre de priorité)."""
    scores, keep = {}, {}
    for lst in lists:
        for rank, r in enumerate(lst):
            key = r[0]
            scores[key] = scores.get(key, 0.0) + 1.0 / (k_rrf + rank + 1)
            keep.setdefault(key, r)
    return [keep[key] for key in sorted(scores, key=lambda x: scores[x], reverse=True)]


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
            # « reason » garde la cause RÉELLE du repli : un repli sur disque
            # après un échec de connexion RESTE un repli, même s'il est durable
            # (recherche lexicale, pas vectorielle). L'écraser par « disk »
            # masquait la panne dans la console.
            return {"persistent": True, "mode": "lexical", "durable": "disque",
                    "embeddings": False, "vector": False, "reason": self._reason}
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
                # Contenu déjà présent : on NE crée pas de doublon, mais on met à
                # jour le thème / le titre s'ils ont changé — sinon recharger le
                # même fichier pour lui attribuer un AUTRE thème serait ignoré en
                # silence (le nouveau thème « ne marcherait pas »).
                changed = False
                with self._lock:
                    m = self._docs.get(existing["id"], existing)
                    nt = (theme or "").strip()[:80]
                    if nt and nt != m.get("theme"):
                        m["theme"] = nt; changed = True
                    ntl = (title or "").strip()[:300]
                    if ntl and ntl != m.get("title"):
                        m["title"] = ntl; changed = True
                    if changed:
                        m["updated_at"] = _now_ms(); self._save()
                    out = dict(m)
                out["deduped"] = True; out["updated"] = changed
                return out
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

    def set_visibility(self, doc_id, visibility):
        """Bascule public <-> interne. « public » expose le document à
        l'assistant de TOUS les visiteurs : à n'utiliser qu'en connaissance."""
        with self._lock:
            d = self._docs.get(doc_id)
            if not d:
                raise RagError("document_inconnu", 404)
            d["visibility"] = "public" if visibility == "public" else "internal"
            d["updated_at"] = _now_ms()
            self._save()
        return True

    def set_theme(self, doc_id, theme):
        """Reclasse un document (change son thème / sous-dossier)."""
        with self._lock:
            d = self._docs.get(doc_id)
            if not d:
                raise RagError("document_inconnu", 404)
            d["theme"] = theme
            d["updated_at"] = _now_ms()
            self._save()
        return True

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
        """Recherche lexicale pondérée (repli sans base). Score = TF-IDF sur les
        termes de la requête (les termes rares pèsent davantage) + bonus de
        couverture (part des termes distincts trouvés) + bonus de phrase exacte,
        normalisé par la longueur du chunk. Bien plus pertinent qu'un simple
        recouvrement d'ensembles — sans réindexation (calcul à la volée)."""
        qterms = _query_terms(query)
        if not qterms:
            return []
        qset = set(qterms)
        phrase = " ".join(qterms)
        multi = len(qset) > 1
        doc_ids = set(doc_ids) if doc_ids else None
        # Passe unique : collecte des chunks candidats + fréquence documentaire
        # (df) de chaque terme sur l'ensemble parcouru → IDF.
        cand = []            # (meta, content, {term: tf}, taille)
        df = {t: 0 for t in qset}
        n_chunks = 0
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
                    n_chunks += 1
                    tf = {}
                    for t in ctok:
                        if t in qset:
                            tf[t] = tf.get(t, 0) + 1
                    if not tf:
                        continue
                    for t in tf:
                        df[t] += 1
                    cand.append((meta, ch["content"], tf, len(set(ctok))))
        if not cand:
            return []
        n_chunks = max(1, n_chunks)

        def idf(t):
            # IDF lissé : un terme présent partout ≈ 0 ; un terme rare ≈ élevé.
            return math.log(1.0 + n_chunks / (1.0 + df.get(t, 0)))

        results = []
        for meta, content, tf, uniq in cand:
            s = 0.0
            for t, c in tf.items():
                s += idf(t) * (1.0 + math.log(c))          # TF-IDF (TF sub-linéaire)
            s *= (len(tf) / len(qset)) ** 0.5              # bonus de couverture
            s /= (uniq ** 0.5)                             # normalisation longueur
            if multi and phrase in content.lower():        # bonus de phrase exacte
                s *= 1.6
            results.append((s, meta, content))
        results.sort(key=lambda r: r[0], reverse=True)
        top = results[:k]
        norm = top[0][0] or 1.0                            # score 0-1 lisible
        return [{"doc_id": m["id"], "title": m["title"], "theme": m["theme"],
                 "visibility": m["visibility"], "content": c, "score": round(s / norm, 4)}
                for s, m, c in top]


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
    # Réglages de la base, saisis depuis l'admin. Sert aujourd'hui à mémoriser la
    # CAPACITÉ du plan d'hébergement : PostgreSQL ne la connaît pas (le quota est
    # imposé au-dessus de lui), et la faire dépendre d'une variable
    # d'environnement obligeait à passer par le tableau de bord de l'hébergeur
    # puis à redéployer. Ici, l'information est saisie une fois dans l'interface
    # et survit aux redéploiements.
    """CREATE TABLE IF NOT EXISTS rag_settings (
        k TEXT PRIMARY KEY,
        v TEXT)""",
]


class PostgresRagStore:
    persistent = True
    _SCHEMA_LOCK = 907245
    # Attente maximale pour obtenir une connexion du pool avant de passer en
    # direct, et durée pendant laquelle on cesse ensuite de le solliciter.
    POOL_ACQUIS_S = 1.5
    POOL_GRACE_S = 60.0

    def __init__(self, dsn):
        from psycopg_pool import ConnectionPool
        # DSN d'ORIGINE conservé (avant ajout des paramètres) : sert à afficher
        # dans l'admin SUR QUELLE BASE on travaille (hôte seul, jamais d'identifiant).
        self._identity = db_identity(dsn)
        sep = "&" if "?" in dsn else "?"
        # client_encoding=UTF8 : les libellés accentués (thèmes, contenu) sont
        # toujours transmis en UTF-8, quel que soit l'encodage du serveur.
        # connect_timeout=10 : tolère le réveil à froid d'une base « serverless »
        # (Neon gratuit se met en veille après ~5 min d'inactivité et prend 1-3 s
        # à se réveiller) sans trop attendre si l'hôte est réellement injoignable.
        # keepalives : empêche un pare-feu / NAT de couper une connexion inactive.
        dsn = (dsn + sep + "connect_timeout=10&client_encoding=UTF8"
               "&keepalives=1&keepalives_idle=30&keepalives_interval=10&keepalives_count=3")
        # check=check_connection : une base serverless en veille rend la connexion
        # gardée en cache « morte ». Le pool la VALIDE (SELECT 1) avant de la prêter
        # et la remplace au besoin — supprime le « ça marche, puis ça échoue après
        # une pause » caractéristique de Neon/serverless.
        # prepare_threshold=None : désactive les requêtes préparées côté serveur.
        # C'est LA condition de compatibilité avec un pooler en mode transaction
        # (endpoint « -pooler » de Neon, PgBouncer) : sans cela, une requête
        # préparée sur une connexion puis rejouée sur une autre échoue (« prepared
        # statement does not exist ») et fait échouer l'enregistrement. Sans effet
        # notable sur une connexion directe.
        self._dsn = dsn
        self.replis_directs = 0
        self._pool_ko_jusqu = 0.0        # fin de la période de grâce (voir _conn)
        # timeout : plafond d'acquisition PAR DÉFAUT du pool. Les opérations de
        # service l'outrepassent via _conn() (POOL_ACQUIS_S = 1,5 s), mais
        # _init_schema() ouvre sa connexion SANS timeout explicite et hérite
        # donc de cette valeur. Sur une base « serverless » réveillée à froid,
        # la construction a besoin de cette marge — on la conserve.
        self._pool = ConnectionPool(dsn, min_size=1, max_size=4,
                                    kwargs={"autocommit": True, "prepare_threshold": None},
                                    timeout=12, open=True,
                                    check=ConnectionPool.check_connection)
        self.vector_mode = False
        try:
            self._init_schema()
        except Exception:
            try:
                self._pool.close()
            except Exception:
                pass
            raise

    @contextmanager
    def _conn(self):
        """Connexion pour une opération, avec REPLI SUR UNE CONNEXION DIRECTE.

        Même remède que pour le magasin de comptes, et pour la même raison,
        observée en production : la base répondait parfaitement (une connexion
        directe s'établissait dans la seconde) pendant que toute opération
        échouait en « PoolTimeout ». Après un incident, psycopg_pool se met en
        retrait et refuse d'ouvrir de nouvelles connexions pendant plusieurs
        minutes ; les demandes attendent leur délai puis échouent.

        Ici l'enjeu est plus lourd que pour les comptes : c'est la CONSTRUCTION
        du magasin qui passait par le pool. Un seul PoolTimeout à cet instant
        condamnait toute la base de connaissance au mode mémoire — documents non
        conservés — alors que la base était joignable. Le repli direct supprime
        cette condamnation.

        Deux réglages tirés d'un défaut de la première version de ce repli :
        l'attente d'acquisition était de 12 s, si bien qu'une page composée de
        plusieurs opérations payait 12 s CHACUNE avant de basculer en direct —
        la requête dépassait alors le délai du navigateur et l'utilisateur voyait
        « Service momentanément indisponible ». Le repli fonctionnait, mais trop
        tard pour servir à quelque chose. D'où :
          - une attente COURTE (un pool en bonne santé répond en millisecondes ;
            au-delà d'une seconde et demie, il n'est pas en état) ;
          - une PÉRIODE DE GRÂCE après un échec, pendant laquelle on va
            directement au but sans même solliciter le pool. Sans elle, chaque
            opération repaie l'attente tant que le pool boude.

        Seul l'échec d'ACQUISITION est traité : une erreur survenant DANS la
        requête remonte normalement à l'appelant."""
        import psycopg
        try:
            if time.time() < self._pool_ko_jusqu:
                raise RuntimeError("pool en période de grâce")
            conn = self._pool.getconn(timeout=self.POOL_ACQUIS_S)
        except Exception as exc:
            self.replis_directs += 1
            self._pool_ko_jusqu = time.time() + self.POOL_GRACE_S
            _log.warning("RAG : pool indisponible (%s) — connexion directe pour "
                         "cette opération (%d au total).",
                         type(exc).__name__, self.replis_directs)
            direct = psycopg.connect(self._dsn, autocommit=True, prepare_threshold=None)
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

    def _init_schema(self):
        with self._conn() as conn:
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
                    # Index vectoriel : recherche en millisecondes à l'échelle de
                    # milliers de documents (sans lui, pgvector fait un balayage
                    # séquentiel). HNSW d'abord (meilleur rappel, aucun entraînement) ;
                    # repli IVFFlat ; sinon balayage. Opérateur cosinus (<=>) →
                    # classe d'opérateurs vector_cosine_ops. Best-effort : un échec
                    # d'index ne casse jamais l'ingestion ni la recherche.
                    self._ensure_vector_index(conn)
                except Exception as exc:
                    self.vector_mode = False
                    _log.info("pgvector indisponible (%s) — recherche plein-texte.",
                              type(exc).__name__)
            finally:
                conn.execute("SELECT pg_advisory_unlock(%s)", (self._SCHEMA_LOCK,))

    @staticmethod
    def _ensure_vector_index(conn):
        """Crée l'index de recherche vectorielle s'il n'existe pas (idempotent).
        HNSW (pgvector ≥ 0.5) de préférence, repli IVFFlat, sinon aucun (balayage).
        Chaque tentative est isolée : un échec est journalisé, jamais propagé."""
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS rag_chunks_embedding_hnsw "
                         "ON rag_chunks USING hnsw (embedding vector_cosine_ops)")
            return
        except Exception as exc:
            _log.info("Index HNSW indisponible (%s) — tentative IVFFlat.", type(exc).__name__)
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS rag_chunks_embedding_ivf "
                         "ON rag_chunks USING ivfflat (embedding vector_cosine_ops) "
                         "WITH (lists=100)")
        except Exception as exc:
            _log.info("Aucun index vectoriel (%s) — recherche vectorielle par balayage.",
                      type(exc).__name__)

    def capabilities(self):
        emb = self.vector_mode and embeddings_available()
        ident = getattr(self, "_identity", None) or {}
        return {"persistent": True,
                "mode": "vectoriel" if emb else "texte_integral",
                "embeddings": emb, "vector": self.vector_mode,
                "host": ident.get("host", ""), "provider": ident.get("provider", "")}

    # -- upload par morceaux (assemblé en base : robuste multi-instance) --
    def create_upload(self, filename, total_bytes):
        ext = validate_ext(filename)
        if total_bytes and total_bytes > MAX_FILE_BYTES:
            raise RagError("fichier_trop_lourd", 413)
        uid = uuid.uuid4().hex
        # purge opportuniste des uploads inachevés (> 1 h)
        try:
            with self._conn() as conn:
                conn.execute("DELETE FROM rag_uploads WHERE created_at < %s",
                             (_now_ms() - 3600_000,))
        except Exception:
            pass
        return uid + "." + ext

    def add_chunk(self, upload_id, idx, data):
        if len(data) > MAX_CHUNK_UPLOAD + 4096:
            raise RagError("morceau_trop_grand", 413)
        with self._conn() as conn:
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
        with self._conn() as conn:
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
        with self._conn() as conn:
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
            existing = self._row_to_dict(existing)
            if dedupe == "skip":
                # Idem que le repli mémoire : recharger un contenu identique met à
                # jour le thème / le titre au lieu de les ignorer silencieusement.
                nt = (theme or "").strip()[:80]
                ntl = (title or "").strip()[:300]
                sets, params = [], []
                if nt and nt != existing.get("theme"):
                    sets.append("theme=%s"); params.append(nt); existing["theme"] = nt
                if ntl and ntl != existing.get("title"):
                    sets.append("title=%s"); params.append(ntl); existing["title"] = ntl
                changed = bool(sets)
                if changed:
                    params += [_now_ms(), existing["id"]]
                    conn.execute("UPDATE rag_documents SET " + ",".join(sets) +
                                 ",updated_at=%s WHERE id=%s", params)
                existing["deduped"] = True; existing["updated"] = changed
                return existing
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
                # Insertion des fragments par lots via un INSERT multi-lignes —
                # sans pipeline ni requête préparée, donc compatible avec le pooler
                # PgBouncer de Neon (voir _insert_chunks).
                _insert_chunks(conn, doc_id, chunks)
        except Exception as exc:
            _log.exception("RAG : échec d'enregistrement (%s, %d fragments, %d octets)",
                           filename, len(chunks), len(data))
            # Détail assaini (ni URL ni mot de passe) : l'administrateur voit la
            # vraie cause (ex. « prepared statement… » d'un pooler PgBouncer,
            # « permission denied », « SSL connection closed ») au lieu d'un
            # message opaque — indispensable pour diagnostiquer sans les logs.
            raise RagError("traitement_echec", 500, detail=_sanitize_pg_error(exc))
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
        with self._conn() as conn:
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
            except Exception:
                # Panne INATTENDUE du service d'embeddings (réponse illisible,
                # coupure réseau…) : même repli gracieux que ci-dessus, plutôt
                # qu'un 500 qui ferait passer un document DÉJÀ ENREGISTRÉ pour
                # un chargement en échec.
                _log.exception("RAG : embeddings indisponibles (document %s)", doc_id)
                conn.execute("UPDATE rag_documents SET status='ready',"
                             "mode='texte_integral',error=%s,updated_at=%s WHERE id=%s",
                             ("embeddings_indisponibles", _now_ms(), doc_id))
                return {"done": True, "indexed": done, "total": nb,
                        "degraded": "embeddings_indisponibles"}
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
        with self._conn() as conn:
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
        with self._conn() as conn:
            rows = conn.execute("SELECT %s FROM rag_documents ORDER BY created_at DESC "
                                "LIMIT 500" % self._COLS).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_blob(self, doc_id):
        with self._conn() as conn:
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
        with self._conn() as conn:
            meta = conn.execute("SELECT title,filename,theme FROM rag_documents "
                                "WHERE id=%s", (doc_id,)).fetchone()
            if not meta:
                raise RagError("document_inconnu", 404)
            rows = conn.execute("SELECT content FROM rag_chunks WHERE doc_id=%s "
                                "ORDER BY ordinal", (doc_id,)).fetchall()
        text = "\n\n".join(r[0] for r in rows)
        return {"title": meta[0], "filename": meta[1], "theme": meta[2],
                "text": text[:limit]}

    def set_visibility(self, doc_id, visibility):
        """Bascule public <-> interne, prise en compte IMMÉDIATEMENT : la
        visibilité est lue à chaque recherche, aucun cache ni réindexation."""
        v = "public" if visibility == "public" else "internal"
        with self._conn() as conn:
            n = conn.execute("UPDATE rag_documents SET visibility=%s,updated_at=%s "
                             "WHERE id=%s", (v, _now_ms(), doc_id)).rowcount
        if not n:
            raise RagError("document_inconnu", 404)
        return True

    def set_theme(self, doc_id, theme):
        """Reclasse un document. Seul le classement change : le texte, les
        fragments et les embeddings sont conservés — aucune réindexation."""
        with self._conn() as conn:
            n = conn.execute("UPDATE rag_documents SET theme=%s,updated_at=%s "
                             "WHERE id=%s", (theme, _now_ms(), doc_id)).rowcount
        if not n:
            raise RagError("document_inconnu", 404)
        return True

    def delete_document(self, doc_id):
        with self._conn() as conn:
            n = conn.execute("DELETE FROM rag_documents WHERE id=%s", (doc_id,)).rowcount
        if not n:
            raise RagError("document_inconnu", 404)
        return True

    # --- Occupation disque -----------------------------------------------------
    # Une base hébergée a un plafond (512 Mo sur l'offre gratuite Neon). Une fois
    # atteint, PostgreSQL refuse TOUTE écriture : les pages s'affichent encore
    # (lectures) mais plus aucun document ne se charge. Sans visibilité sur
    # l'occupation, la panne est indéchiffrable — d'où cet inventaire, puis la
    # purge ciblée ci-dessous.
    _TABLES = ("rag_blobs", "rag_chunks", "rag_documents", "rag_uploads")

    def get_setting(self, key, default=None):
        """Lecture d'un réglage. Best-effort : un réglage absent (ou une table
        pas encore créée sur une base antérieure) ne doit jamais faire échouer
        l'appelant."""
        try:
            with self._conn() as conn:
                row = conn.execute("SELECT v FROM rag_settings WHERE k=%s",
                                   (key,)).fetchone()
            return row[0] if row else default
        except Exception:
            return default

    def set_setting(self, key, value):
        """Écriture d'un réglage. `value` à None efface l'entrée."""
        with self._conn() as conn:
            if value is None:
                conn.execute("DELETE FROM rag_settings WHERE k=%s", (key,))
            else:
                conn.execute("INSERT INTO rag_settings (k,v) VALUES (%s,%s) "
                             "ON CONFLICT (k) DO UPDATE SET v=EXCLUDED.v",
                             (key, str(value)))
        return True

    def capacity_bytes(self):
        """Capacité déclarée du plan, en octets, ou None si inconnue.

        Deux sources, dans cet ordre : le réglage saisi dans l'admin (mémorisé en
        base, donc valable pour tous les workers et conservé au redéploiement),
        puis la variable d'environnement DB_DISK_GB (conservée pour ne rien
        casser là où elle est déjà définie)."""
        for source, brut in (("reglage", self.get_setting("capacity_gb")),
                             ("variable", os.environ.get("DB_DISK_GB"))):
            try:
                gb = float((brut or "").strip() or 0)
            except Exception:
                continue
            if gb > 0:
                return int(gb * 1024 ** 3), source
        return None, None

    def storage_report(self):
        """Occupation par table + postes récupérables (fichiers d'origine,
        résidus de chargements interrompus, bulletins de veille).

        La CAPACITÉ totale, elle, échappe à PostgreSQL : le quota est imposé par
        l'hébergeur, le moteur ne le connaît pas. Sans point de comparaison,
        l'occupation reste un chiffre nu et la saturation n'arrive jamais que par
        surprise — sous la forme d'un refus d'écriture. Elle se déclare donc
        depuis le panneau d'administration (page de la base chez l'hébergeur →
        « Storage »), et le panneau affiche alors un pourcentage, avec alerte
        avant le mur."""
        out = {"tables": [], "total_bytes": 0}
        try:
            out["capacity_bytes"], out["capacity_source"] = self.capacity_bytes()
        except Exception:
            out["capacity_bytes"], out["capacity_source"] = None, None
        with self._conn() as conn:
            try:
                out["db_bytes"] = conn.execute(
                    "SELECT pg_database_size(current_database())").fetchone()[0]
            except Exception:
                out["db_bytes"] = None
            for t in self._TABLES:
                try:
                    n = conn.execute("SELECT count(*) FROM %s" % t).fetchone()[0]
                    b = conn.execute("SELECT pg_total_relation_size(%s)", (t,)).fetchone()[0]
                except Exception:
                    continue
                out["tables"].append({"table": t, "lignes": n, "octets": int(b or 0)})
                out["total_bytes"] += int(b or 0)
            def _scalar(sql, params=()):
                try:
                    return conn.execute(sql, params).fetchone()[0] or 0
                except Exception:
                    return 0
            out["recuperable"] = {
                # Fichiers d'origine : utiles seulement au bouton « télécharger ».
                # Les supprimer ne retire NI le texte NI l'indexation.
                "fichiers_origine": int(_scalar(
                    "SELECT COALESCE(sum(octet_length(data)),0) FROM rag_blobs")),
                # Morceaux de chargements jamais terminés (voie de repli).
                "chargements_interrompus": int(_scalar(
                    "SELECT COALESCE(sum(octet_length(data)),0) FROM rag_uploads")),
                # Bulletins CERT-FR : re-téléchargeables à volonté.
                "veille": int(_scalar(
                    "SELECT COALESCE(sum(octet_length(c.content)),0) FROM rag_chunks c "
                    "JOIN rag_documents d ON d.id=c.doc_id WHERE d.theme='Veille'")),
                "veille_documents": int(_scalar(
                    "SELECT count(*) FROM rag_documents WHERE theme='Veille'")),
            }
        return out

    def verify_integrity(self, limit=5000):
        """Recalcule l'empreinte des fichiers d'origine et la compare à celle
        enregistrée au chargement.

        Une corruption silencieuse du stockage ne se voit pas autrement : le
        document continue de s'afficher et d'alimenter l'assistant. On lit les
        blobs un par un plutôt qu'en bloc — un contrôle d'intégrité qui saturerait
        la mémoire du service serait un remède pire que le mal."""
        alteres, verifies, sans_blob = [], 0, 0
        with self._conn() as conn:
            ids = [r[0] for r in conn.execute(
                "SELECT id FROM rag_documents ORDER BY created_at DESC LIMIT %s",
                (int(limit),)).fetchall()]
            for did in ids:
                row = conn.execute(
                    "SELECT d.title, d.sha256, b.data FROM rag_documents d "
                    "LEFT JOIN rag_blobs b ON b.doc_id=d.id WHERE d.id=%s",
                    (did,)).fetchone()
                if not row:
                    continue
                titre, attendu, data = row[0], row[1], row[2]
                if data is None or not attendu:
                    # Fichier d'origine purgé volontairement : rien à comparer,
                    # ce n'est pas une anomalie.
                    sans_blob += 1
                    continue
                verifies += 1
                if hashlib.sha256(bytes(data)).hexdigest() != attendu:
                    alteres.append({"id": did, "title": titre})
        return {"verifies": verifies, "sans_fichier": sans_blob, "alteres": alteres}

    def purge_storage(self, scopes):
        """Libère de la place. `scopes` : sous-ensemble de {'uploads', 'veille',
        'blobs'}. Rien n'est supprimé qui ne soit reconstituable :
          - uploads : résidus de chargements interrompus (aucune valeur) ;
          - veille  : bulletins CERT-FR (re-téléchargeables) ;
          - blobs   : fichiers d'origine — les documents restent cherchables et
                      exploitables, seul le téléchargement de l'original est perdu.
        Un VACUUM suit pour rendre l'espace réutilisable (VACUUM FULL est écarté :
        il réécrit la table, donc réclame de la place… précisément ce qui manque)."""
        scopes = {s for s in (scopes or []) if s in ("uploads", "veille", "blobs")}
        if not scopes:
            raise RagError("rien_a_purger", 400)
        avant = self.storage_report()
        detail = {}
        with self._conn() as conn:
            if "uploads" in scopes:
                detail["chargements_interrompus"] = conn.execute(
                    "DELETE FROM rag_uploads").rowcount
            if "veille" in scopes:
                detail["veille_documents"] = conn.execute(
                    "DELETE FROM rag_documents WHERE theme='Veille'").rowcount
            if "blobs" in scopes:
                detail["fichiers_origine"] = conn.execute(
                    "DELETE FROM rag_blobs").rowcount
        # VACUUM exige l'autocommit (hors transaction).
        vacuum_ok = True
        try:
            with self._conn() as conn:
                conn.autocommit = True
                for t in self._TABLES:
                    conn.execute("VACUUM (ANALYZE) %s" % t)
        except Exception as exc:
            vacuum_ok = False
            _log.warning("RAG : VACUUM après purge impossible (%s)", _sanitize_pg_error(exc))
        apres = self.storage_report()
        return {"avant": avant, "apres": apres, "supprime": detail,
                "vacuum": vacuum_ok,
                "libere_octets": max(0, (avant.get("total_bytes") or 0)
                                     - (apres.get("total_bytes") or 0))}

    def stats(self):
        with self._conn() as conn:
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
        with self._conn() as conn:
            lex = self._fulltext(conn, query, clause, params, k * 4)
            # Recherche HYBRIDE : quand les embeddings sont disponibles, fusionner
            # le plein-texte (lexical, mots) ET le vectoriel (sémantique, sens) par
            # Reciprocal Rank Fusion — combinaison éprouvée, robuste, qui capte les
            # deux signaux. Repli plein-texte seul si les embeddings échouent.
            if self.vector_mode and embeddings_available():
                try:
                    vec = self._vector(conn, query, clause, params, k * 4)
                    fused = _rrf([vec, lex])
                    if fused:
                        return [self._hit(r) for r in fused[:k]]
                except RagError:
                    pass
        return [self._hit(r) for r in lex[:k]]

    def _vector(self, conn, query, clause, params, limit):
        """Liste classée par similarité sémantique (cosinus, index HNSW)."""
        qvec = _vec_literal(embed_texts([query])[0])
        sql = ("SELECT c.content,d.id,d.title,d.theme,d.visibility,"
               "1-(c.embedding <=> %s::vector) AS score "
               "FROM rag_chunks c JOIN rag_documents d ON d.id=c.doc_id "
               "WHERE c.embedding IS NOT NULL AND " + clause +
               " ORDER BY c.embedding <=> %s::vector LIMIT %s")
        return list(conn.execute(sql, [qvec] + params + [qvec, limit]).fetchall())

    def _fulltext(self, conn, query, clause, params, limit):
        """Liste classée par pertinence plein-texte français. Précision d'abord
        (tous les termes, ts_rank_cd) ; complétée par un rappel OR (au moins un
        terme) si trop peu de résultats stricts."""
        sql = ("SELECT c.content,d.id,d.title,d.theme,d.visibility,"
               "ts_rank_cd(c.tsv, plainto_tsquery('french',%s)) AS score "
               "FROM rag_chunks c JOIN rag_documents d ON d.id=c.doc_id "
               "WHERE c.tsv @@ plainto_tsquery('french',%s) AND " + clause +
               " ORDER BY score DESC LIMIT %s")
        rows = list(conn.execute(sql, [query, query] + params + [limit]).fetchall())
        if len(rows) < limit:
            terms = _query_terms(query)
            if terms:
                or_q = " | ".join(terms)   # termes alphanumériques : sûrs pour to_tsquery
                sql2 = ("SELECT c.content,d.id,d.title,d.theme,d.visibility,"
                        "ts_rank_cd(c.tsv, to_tsquery('french',%s)) AS score "
                        "FROM rag_chunks c JOIN rag_documents d ON d.id=c.doc_id "
                        "WHERE c.tsv @@ to_tsquery('french',%s) AND " + clause +
                        " ORDER BY score DESC LIMIT %s")
                seen = set(r[0] for r in rows)
                for r in conn.execute(sql2, [or_q, or_q] + params + [limit * 2]).fetchall():
                    if r[0] not in seen:
                        rows.append(r)
                        seen.add(r[0])
                    if len(rows) >= limit:
                        break
        return rows

    @staticmethod
    def _hit(r):
        return {"content": r[0], "doc_id": r[1], "title": r[2], "theme": r[3],
                "visibility": r[4], "score": round(float(r[5]), 4)}


# Délai minimal entre deux essais de reconnexion automatiques (secondes).
_RECONNECT_MIN_INTERVAL = float(os.environ.get("RAG_RECONNECT_INTERVAL", "20"))


def _sanitize_pg_error(exc):
    """Message d'erreur affichable : URLs et password=… masqués, longueur bornée."""
    msg = " ".join(str(exc).split())
    msg = re.sub(r"postgres(?:ql)?://\S+", "postgresql://…", msg)
    msg = re.sub(r"password=\S+", "password=…", msg)
    return msg[:300]


def diagnose(dsn=None):
    """Diagnostic pas-à-pas de la connexion PostgreSQL (admin uniquement).

    Chaque étape isole une cause distincte — variable absente, caractère
    parasite, URL invalide, DNS (mauvaise région / base supprimée), TCP
    (base suspendue / Access Control), session PostgreSQL (mot de passe,
    SSL, base inexistante), écriture. Aucun secret n'est exposé : seuls
    l'hôte, le port et des messages assainis sortent d'ici."""
    import socket
    from urllib.parse import urlparse
    steps = []

    def step(name, ok, info=""):
        steps.append({"etape": name, "ok": bool(ok), "info": (info or "")[:220]})

    raw = os.environ.get("DATABASE_URL") if dsn is None else dsn
    if not raw:
        step("variable", False, "DATABASE_URL absente de l'environnement")
        return {"steps": steps, "conclusion":
                "Définissez DATABASE_URL (champ « Internal Database URL » de la base) "
                "dans l'onglet Environment du service, puis laissez Render redéployer."}
    step("variable", True, "définie (%d caractères)" % len(raw))

    clean = raw.strip()
    if clean != raw or any(c in raw for c in ("\n", "\r", '"', "'")) or " " in clean:
        step("format", False, "espace, guillemet ou retour à la ligne détecté dans la valeur")
    else:
        step("format", True, "aucun caractère parasite")
    if clean.startswith("postgres://"):
        clean = "postgresql://" + clean[len("postgres://"):]

    try:
        u = urlparse(clean)
        host, port = u.hostname or "", u.port or 5432
    except Exception as exc:
        step("url", False, _sanitize_pg_error(exc))
        return {"steps": steps, "conclusion":
                "La valeur n'est pas une URL PostgreSQL lisible — recopiez le champ "
                "« Internal Database URL » tel quel."}
    if not host:
        step("url", False, "aucun hôte dans l'URL")
        return {"steps": steps, "conclusion":
                "L'URL ne contient pas d'hôte (forme attendue : postgresql://user:mot@hôte/base) "
                "— recopiez le champ « Internal Database URL » tel quel."}
    kind = ("external" if ".render.com" in host
            else "internal" if host.startswith("dpg-") else "other")
    step("url", True, "%s:%s (%s)" % (host, port,
         {"external": "URL externe — soumise à l'Access Control",
          "internal": "URL interne — même région obligatoire",
          "other": "hôte personnalisé"}[kind]))

    t0 = time.time()
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        ips = sorted({i[4][0] for i in infos})
        step("dns", True, "%s (%d ms)" % (", ".join(ips[:4]), (time.time() - t0) * 1000))
    except Exception as exc:
        step("dns", False, _sanitize_pg_error(exc))
        return {"steps": steps, "conclusion":
                "Le nom d'hôte ne se résout pas : URL interne d'une base située dans une AUTRE "
                "région, ou base supprimée. Ouvrez la page de la base voulue (statut Available, "
                "même région que le service) et recopiez SON « Internal Database URL »."}

    t0 = time.time()
    try:
        sock = socket.create_connection((host, port), timeout=6)
        sock.close()
        step("tcp", True, "port ouvert (%d ms)" % ((time.time() - t0) * 1000))
    except Exception as exc:
        step("tcp", False, _sanitize_pg_error(exc))
        if kind == "external":
            concl = ("Le serveur ne répond pas sur l'URL externe : l'Access Control de la base "
                     "bloque ce service. Remplacez DATABASE_URL par l'« Internal Database URL » "
                     "(base dans la même région), ou ajoutez 0.0.0.0/0 dans Access Control.")
        else:
            # Le nom a été résolu juste avant : l'hôte EXISTE. Un délai d'attente à
            # l'ouverture TCP ne signifie donc pas « adresse inconnue » mais « rien
            # n'accepte la connexion ». Sur une URL interne Render, trois causes,
            # par ordre de fréquence — la première est la plus souvent oubliée.
            concl = ("Le nom est bien résolu (l'hôte existe) mais aucune connexion n'est "
                     "acceptée. Sur une URL interne, vérifiez dans cet ordre : "
                     "1) la RÉGION — le réseau privé Render est cloisonné par région : "
                     "la base et le service web doivent être dans la MÊME (le nom se "
                     "résout quand même d'une région à l'autre, mais la connexion "
                     "n'aboutit jamais) ; comparez la région affichée sur la page de la "
                     "base et sur celle du service ; "
                     "2) le STATUT de la base — elle doit être « Available » (une base "
                     "en cours de création ou suspendue résout déjà mais n'accepte pas "
                     "encore) ; "
                     "3) l'URL — recopiez l'« Internal Database URL » de CETTE base. "
                     "Dépannage immédiat si les régions diffèrent : utilisez l'« External "
                     "Database URL » (elle fonctionne entre régions), en autorisant "
                     "l'accès dans Access Control.")
        return {"steps": steps, "conclusion": concl}

    try:
        import psycopg
        t0 = time.time()
        conn = psycopg.connect(clean, connect_timeout=8)
        try:
            ver = (conn.execute("SELECT version()").fetchone() or [""])[0]
            conn.execute("CREATE TEMP TABLE _cp_diag(t int)")
            conn.execute("DROP TABLE _cp_diag")
        finally:
            conn.close()
        step("session", True, "%s (%d ms)" % (str(ver).split(" on ")[0][:60],
                                              (time.time() - t0) * 1000))
        step("ecriture", True, "table temporaire créée puis supprimée")
        # Connexions consommées / plafond du serveur. C'est LA cause qu'aucune
        # autre étape ne révèle : quand le plafond est atteint, la base est
        # parfaitement saine — DNS, TCP et session passent — mais toute nouvelle
        # connexion est refusée, et l'application se croit « injoignable ».
        # L'application ouvre un pool par module (documents, comptes, clients,
        # livrables, cockpit, automatisation, audit), multiplié par le nombre de
        # workers : le compte monte vite.
        try:
            conn = psycopg.connect(clean, connect_timeout=8)
            try:
                used = conn.execute("SELECT count(*) FROM pg_stat_activity "
                                    "WHERE datname = current_database()").fetchone()[0]
                cap = int(conn.execute("SHOW max_connections").fetchone()[0])
            finally:
                conn.close()
            pct = (used * 100 // cap) if cap else 0
            step("connexions", pct < 85,
                 "%d connexions ouvertes sur %d autorisées (%d %%)%s"
                 % (used, cap, pct,
                    " — plafond proche : c'est ce qui fait échouer les nouvelles "
                    "connexions" if pct >= 85 else ""))
        except Exception as exc:
            step("connexions", True, "non mesurable (%s)" % _sanitize_pg_error(exc)[:80])
    except Exception as exc:
        msg = _sanitize_pg_error(exc)
        step("session", False, msg)
        low = msg.lower()
        if "password" in low or "authentification" in low or "authentication" in low:
            concl = ("Le serveur répond mais refuse les identifiants : l'URL mélange "
                     "probablement deux bases (mot de passe d'une autre base). Recopiez "
                     "l'« Internal Database URL » complète de la base visée, d'un seul bloc.")
        elif "ssl" in low or "tls" in low:
            concl = "Négociation SSL en échec — utilisez l'URL fournie par Render telle quelle."
        elif "does not exist" in low:
            concl = ("Connexion OK mais la base nommée dans l'URL n'existe pas sur ce serveur — "
                     "l'URL mélange deux bases. Recopiez l'URL complète d'une seule base.")
        else:
            concl = "Le port répond mais la session PostgreSQL échoue : " + msg
        return {"steps": steps, "conclusion": concl}

    return {"steps": steps, "conclusion":
            "Connexion PostgreSQL opérationnelle. Cliquez « ↻ Reconnecter la base » pour "
            "rétablir la persistance de la base de connaissance sans redéployer, puis faites "
            "un Manual Deploy (Deploy latest commit) pour rebrancher aussi comptes, cockpit, "
            "historique livrables et clients."}


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

    # Attente maximale du bouton « forcer un essai » quand un cycle de fond est
    # déjà en vol : au-delà, on rend la main plutôt que de faire patienter le
    # navigateur jusqu'à son propre délai.
    ATTENTE_BOUTON_S = 25.0

    def __init__(self, dsn):
        self._dsn = dsn
        self._pg = None
        self.recherches_a_vide = 0
        # Repli mémoire (durable si RAG_DISK_PATH est défini) : DATABASE_URL est
        # défini mais la connexion a échoué.
        self._mem = MemoryRagStore(reason="db_connection_failed")
        self._last_try = 0.0
        self._last_error = ""
        self._lock = threading.Lock()
        self._reconnecting = False
        # Connexion tentée EN TÂCHE DE FOND : le worker démarre instantanément et
        # sert depuis le repli ; il bascule sur PostgreSQL dès qu'il est joignable.
        # Aucune requête n'est jamais bloquée par une base froide/injoignable
        # (chaque essai peut bloquer ~10-20 s). self-healing sans redéploiement.
        #
        # Le rattrapage est tenté MÊME si le repli est durable (RAG_DISK_PATH).
        # La version précédente s'en dispensait, avec un raisonnement qui ne
        # tient pas : un repli sur disque ne perd rien, mais il ne fait que de
        # la recherche LEXICALE, il ne se partage pas entre instances, et il ne
        # se sauvegarde pas comme la base. Surtout, il déclarait persistent=True
        # — donc le bandeau d'alerte de la console disparaissait. Régler
        # RAG_DISK_PATH, qui est précisément le remède que ce bandeau
        # recommande, désactivait à la fois la reconnexion et l'alerte : la
        # dégradation devenait définitive ET silencieuse.
        self._last_try = time.time()
        self._reconnecting = True
        threading.Thread(target=self._bg_connect, daemon=True).start()

    @staticmethod
    def _sanitize_error(exc):
        """Message d'erreur affichable dans l'admin : jamais de secret."""
        return _sanitize_pg_error(exc)

    def _target_info(self):
        """Hôte:port visé (jamais les identifiants) + nature de l'URL.
        Décisif pour un timeout : une URL interne (dpg-…-a) exige base et
        service dans la même région ; une URL externe (….render.com) passe
        par l'Access Control de la base (liste d'IP autorisées)."""
        try:
            from urllib.parse import urlparse
            u = urlparse(self._dsn)
            host, port = u.hostname or "", u.port or 5432
            if not host:
                return "", ""
            if ".render.com" in host:
                kind = "external"
            elif host.startswith("dpg-"):
                kind = "internal"
            else:
                kind = "other"
            return "%s:%s" % (host, port), kind
        except Exception:
            return "", ""

    def _probe_error(self):
        """Erreur libpq précise via une connexion directe : le pool n'expose
        qu'un délai générique (« couldn't get a connection after N sec ») qui
        ne dit pas si l'hôte est introuvable, l'authentification refusée ou la
        base suspendue. Renvoie "" si la connexion directe passe."""
        try:
            import psycopg
            conn = psycopg.connect(self._dsn, connect_timeout=8)
            conn.close()
            return ""
        except Exception as exc:
            return self._sanitize_error(exc)

    def _try_connect(self, attempts=1, probe=True):
        for i in range(attempts):
            try:
                pg = PostgresRagStore(self._dsn)
                # ORDRE IMPORTANT : la base est branchée AVANT la reprise du
                # repli (la migration écrit à travers `self._pg`), mais la
                # bascule n'est ACQUISE qu'une fois la reprise réussie. Un
                # échec partiel nous ramène au repli, sans avoir rien perdu :
                # les documents non repris y sont toujours.
                self._pg = pg
                _, echecs = self._migrer_repli()
                if echecs:
                    self._pg = None
                    self._last_error = (
                        "base jointe, mais %d document(s) du repli n'ont pas pu y "
                        "être versés — on reste en mémoire pour ne rien perdre" % echecs)
                    _log.warning("RAG : bascule annulée — %s.", self._last_error)
                    return False
                # Le repli n'est PAS vidé : il n'est plus consulté (`_store`
                # renvoie désormais PostgreSQL) et le garder coûte quelques
                # mégaoctets pour le temps du process. En échange, si la base
                # retombe dans la minute, les documents sont encore là.
                self._last_error = ""
                _log.info("RAG : PostgreSQL connecté (%s).", pg.capabilities()["mode"])
                return True
            except Exception as exc:
                self._pg = None
                # `probe` (sonde libpq directe) précise la cause pour la bannière,
                # mais double le temps : réservé au fond (jamais dans la requête).
                self._last_error = ((self._probe_error() if probe else "")
                                    or self._sanitize_error(exc))
                _log.warning("RAG : PostgreSQL injoignable (essai %d/%d : %s).",
                             i + 1, attempts, self._last_error)
                if i + 1 < attempts:
                    # Attente progressive (1,5 s → 20 s max) : couvre la fenêtre de
                    # démarrage d'une base qui n'accepte pas encore les connexions,
                    # sans la marteler si elle est durablement injoignable.
                    time.sleep(min(1.5 * (2 ** i), 20))
        return False

    def _bg_connect(self, attempts=6):
        """Connexion en tâche de fond, avec PLUSIEURS essais espacés.

        Un seul essai ne suffit pas au démarrage : après un déploiement, le
        service web et la base redémarrent de concert et la base n'accepte pas
        encore les connexions pendant quelques dizaines de secondes. L'unique
        tentative échouait alors, et l'application restait en repli mémoire alors
        que la base devenait joignable l'instant d'après."""
        try:
            self._try_connect(attempts=attempts, probe=True)
        finally:
            self._reconnecting = False

    def _migrer_repli(self):
        """Verse dans PostgreSQL les documents déposés pendant la panne.

        C'EST LA SORTIE D'UNE IMPASSE, et non un raffinement. La version
        précédente devait choisir entre deux maux dès qu'un document avait été
        chargé en mode dégradé : basculer sur la base et MASQUER ce document, ou
        rester en mémoire et ne jamais guérir. Elle choisissait le second — donc
        la reconnexion automatique s'arrêtait définitivement au premier
        chargement, exactement quand l'administrateur en avait le plus besoin.
        Le message « la connexion est retentée automatiquement » devenait faux
        sans que rien ne le signale.

        Il n'y a pas à choisir : on RECOPIE. L'ingestion est idempotente
        (empreinte SHA-256, `dedupe="skip"`), un document déjà présent en base
        n'est donc pas dupliqué, et l'opération est rejouable sans dommage.

        Un document qui ne passe pas est CONSERVÉ en mémoire et l'échec est
        journalisé : mieux vaut une bascule partielle et signalée qu'une bascule
        propre qui perd une pièce en silence. La bascule n'a lieu que si TOUT ce
        qui devait passer est passé — sinon on reste en repli, avec la raison.

        Retourne (migres, echecs)."""
        migres = echecs = 0
        try:
            docs = list(self._mem.list_documents())
        except Exception:
            return 0, 0
        for d in docs:
            doc_id = d.get("id")
            if not doc_id:
                continue
            try:
                nom, data = self._mem.get_blob(doc_id)
            except Exception:
                # Sans contenu d'origine, rien à recopier : le document a été
                # ingéré autrement (veille) ou le repli est incomplet.
                continue
            try:
                self._pg.ingest_bytes(nom, data,
                                      title=d.get("title") or "",
                                      theme=d.get("theme") or "",
                                      visibility=d.get("visibility") or "internal")
                migres += 1
            except Exception as exc:
                echecs += 1
                _log.warning("RAG : document %r non repris en base (%s).",
                             (d.get("title") or nom)[:80], type(exc).__name__)
        if migres or echecs:
            _log.info("RAG : reprise du repli — %d document(s) versé(s) en base, "
                      "%d échec(s).", migres, echecs)
        return migres, echecs

    def _intervalle(self):
        """Délai minimal entre deux essais de rattrapage.

        Le repli DURABLE (disque) ne perd rien : on peut y patienter plus
        longtemps entre deux essais, sans pour autant renoncer à rattraper la
        base — c'est la différence entre « moins pressé » et « jamais », et
        c'est cette confusion qui rendait la dégradation définitive."""
        if getattr(self._mem, "persistent", False):
            return _RECONNECT_MIN_INTERVAL * 6
        return _RECONNECT_MIN_INTERVAL

    def _maybe_reconnect(self):
        """Déclenche une reconnexion EN TÂCHE DE FOND (jamais bloquante). La
        requête courante est toujours servie immédiatement depuis le repli."""
        if self._pg is not None or self._reconnecting:
            return
        if time.time() - self._last_try < self._intervalle():
            return
        with self._lock:
            if (self._pg is not None or self._reconnecting
                    or time.time() - self._last_try < self._intervalle()):
                return
            self._last_try = time.time()
            self._reconnecting = True
            threading.Thread(target=self._bg_connect, daemon=True).start()

    def _store(self):
        return self._pg if self._pg is not None else self._mem

    def _read(self, method, *args, **kwargs):
        """Opération de LECTURE tolérante aux pannes. Si le moteur PostgreSQL
        échoue EN COURS DE VIE (connexion perdue, pooler qui coupe, base
        suspendue…), on assainit l'erreur pour le diagnostic, on repasse en
        repli mémoire (ce qui déclenche une reconnexion en tâche de fond) et on
        renvoie le résultat mémoire — jamais de 500 opaque. Les RagError
        (erreurs métier) sont laissées telles quelles."""
        store = self._store()
        try:
            return getattr(store, method)(*args, **kwargs)
        except RagError:
            raise
        except Exception as exc:
            if store is not self._pg:
                raise
            # UN SEUL ÉCHEC NE SUFFIT PLUS À DÉCROCHER. La version précédente
            # abandonnait la base au premier incident : une coupure de
            # connexion par le pooler, un réveil à froid, une microcoupure
            # réseau, et la console affichait « 0 document » sous un bandeau
            # alarmant alors que la base était intacte et que le repli, lui,
            # était vide. On rejoue donc l'opération une fois — le pool renvoie
            # alors une connexion neuve, ce qui suffit dans l'immense majorité
            # des cas — et on ne déclasse que si l'échec se confirme.
            premiere = _sanitize_pg_error(exc)
            try:
                res = getattr(store, method)(*args, **kwargs)
                _log.info("RAG : « %s » a échoué (%s) puis abouti au second essai — "
                          "incident passager, la base est conservée.", method, premiere)
                return res
            except RagError:
                raise
            except Exception as exc2:
                self._last_error = _sanitize_pg_error(exc2)
            _log.warning("RAG : requête PostgreSQL « %s » échouée deux fois — "
                         "repli mémoire (%s).", method, self._last_error)
            self._pg = None
            self.recherches_a_vide = 0
            return getattr(self._mem, method)(*args, **kwargs)

    def reconnect(self):
        """Essai de reconnexion immédiat et SYNCHRONE (bouton admin : l'utilisateur
        accepte d'attendre). Sonde désactivée pour borner le délai (~12 s max).
        Renvoie True si connecté.

        SI UN ESSAI DE FOND EST DÉJÀ EN COURS, on l'ATTEND au lieu de rendre la
        main aussitôt. La version précédente répondait « toujours en mémoire »
        en 0,000 s dès qu'un cycle tournait — or un cycle dure de 50 s à près de
        3 minutes, si bien qu'un administrateur qui appuyait sur le bouton
        pendant ce temps recevait un échec instantané et concluait que la
        reconnexion ne marchait pas, alors qu'elle était en train de réussir."""
        fin = time.time() + self.ATTENTE_BOUTON_S
        while True:
            with self._lock:
                if not self._reconnecting:
                    self._reconnecting = True
                    break
            if self._pg is not None or time.time() >= fin:
                return self._pg is not None
            time.sleep(0.25)
        try:
            self._last_try = time.time()
            self._try_connect(attempts=1, probe=False)
        finally:
            self._reconnecting = False
        return self._pg is not None

    # Opérations de consultation : occasion de retenter la connexion.
    def capabilities(self):
        self._maybe_reconnect()
        caps = self._store().capabilities()
        # En repli mémoire : joindre la cause exacte du dernier échec de
        # connexion (assainie) et l'hôte visé pour un diagnostic immédiat
        # dans l'admin — jamais d'identifiant.
        if self._pg is None and self._last_error:
            caps = dict(caps)
            caps["detail"] = self._last_error
            target, kind = self._target_info()
            if target:
                caps["target"] = target
                caps["target_kind"] = kind
        return caps

    def list_documents(self):
        self._maybe_reconnect()
        return self._read("list_documents")

    def stats(self):
        self._maybe_reconnect()
        return self._read("stats")

    def search(self, *args, **kwargs):
        # Lecture tolérante : une panne de la base ne casse ni l'assistant, ni
        # les livrables, ni l'explorateur — on sert depuis le repli.
        #
        # La recherche EST le chemin le plus fréquenté du magasin — bien plus
        # que la console d'administration. L'omettre du rattrapage revenait à
        # ne retenter la connexion que lorsqu'un administrateur ouvrait une
        # page : sur un site consulté sans administrateur connecté, la base
        # pouvait rester perdue des heures après son rétablissement.
        self._maybe_reconnect()
        res = self._read("search", *args, **kwargs)
        # Un repli qui ne renvoie RIEN alors que la base contenait des documents
        # se traduit, en bout de chaîne, par une réponse d'assistant sans
        # sources. Ce n'est pas une recherche infructueuse, c'est une panne :
        # elle doit laisser une trace.
        if self._pg is None and not res:
            self.recherches_a_vide += 1
            if self.recherches_a_vide in (1, 10, 100) or self.recherches_a_vide % 500 == 0:
                _log.warning("RAG : recherche sans résultat en mode repli "
                             "(%d depuis la bascule) — réponses sans sources.",
                             self.recherches_a_vide)
        return res

    def _write(self, method, *args, **kwargs):
        """Opération d'ÉCRITURE TOLÉRANTE aux pannes EN COURS DE VIE.

        Le chemin de LECTURE (_read) sait déjà basculer en repli mémoire ;
        les ÉCRITURES, elles, passaient par __getattr__ SANS filet. Résultat :
        une panne PostgreSQL transitoire — connexion coupée par le pooler
        (Neon « -pooler »), base « serverless » réveillée à froid, suspension
        après inactivité — faisait échouer l'opération par un 500 opaque, alors
        même que la page (lectures) s'affichait normalement.

        Ici : si le moteur PostgreSQL échoue, on tente UNE reconnexion synchrone
        puis on réessaie. Les écritures concernées sont rejouables sans dégât :
        l'ingestion est idempotente (dédoublonnage par empreinte SHA-256) et
        l'indexation reprend au premier fragment non encore vectorisé. Une
        reconnexion réveille en général la base « serverless » → l'opération
        aboutit DURABLEMENT. Si la base reste injoignable, on lève une erreur
        CLAIRE et ré-essayable (base_indisponible) plutôt que d'écrire
        silencieusement en mémoire (ce qui perdrait le document au prochain
        redémarrage). Les RagError métier (fichier illisible…) passent telles
        quelles."""
        store = self._store()
        try:
            return getattr(store, method)(*args, **kwargs)
        except RagError:
            raise
        except Exception as exc:
            if store is not self._pg:
                # Le repli mémoire lui-même a échoué : rien à récupérer.
                raise
            self._last_error = _sanitize_pg_error(exc)
            _log.warning("RAG : écriture PostgreSQL « %s » échouée — reconnexion "
                         "+ réessai (%s).", method, self._last_error)
            self._pg = None
            if self.reconnect() and self._pg is not None:
                try:
                    return getattr(self._pg, method)(*args, **kwargs)
                except RagError:
                    raise
                except Exception as exc2:
                    self._last_error = _sanitize_pg_error(exc2)
                    _log.warning("RAG : réessai « %s » échoué (%s).",
                                 method, self._last_error)
                    self._pg = None
            raise RagError("base_indisponible", 503, self._last_error)

    def ingest_bytes(self, *args, **kwargs):
        """Chargement d'un document, tolérant aux pannes (voir _write)."""
        return self._write("ingest_bytes", *args, **kwargs)

    def set_theme(self, *args, **kwargs):
        """Reclassement d'un document, tolérant aux pannes (voir _write)."""
        return self._write("set_theme", *args, **kwargs)

    def set_visibility(self, *args, **kwargs):
        """Bascule de visibilité, tolérante aux pannes (voir _write)."""
        return self._write("set_visibility", *args, **kwargs)

    def set_setting(self, *args, **kwargs):
        """Enregistrement d'un réglage, tolérant aux pannes (voir _write)."""
        return self._write("set_setting", *args, **kwargs)

    def index_next(self, *args, **kwargs):
        """Indexation vectorielle d'un lot, tolérante aux pannes (voir _write).

        Chemin particulièrement exposé : un document volumineux demande des
        DIZAINES d'appels successifs (EMBED_BATCH fragments par appel), soit
        plusieurs dizaines de secondes pendant lesquelles la base « serverless »
        peut couper. Sans filet, cette coupure faisait apparaître un chargement
        en ÉCHEC alors que le document était déjà enregistré."""
        return self._write("index_next", *args, **kwargs)

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


def duplicate_groups(store, docs=None):
    """Renvoie les groupes de documents en doublon (contenu identique).

    Pour chaque groupe on désigne le document à CONSERVER — le mieux indexé,
    puis le plus ancien (l'original) — et les autres, supprimables. Ne renvoie
    que les groupes d'au moins deux documents. Aucune suppression ici.

    `docs` restreint l'analyse à un sous-ensemble déjà filtré (p. ex. les seuls
    documents Engineering) : le dédoublonnage reste alors cantonné à ce
    périmètre et ne peut pas toucher au reste de la base."""
    by_key = {}
    for d in (store.list_documents() if docs is None else docs):
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


def dedupe(store, dry_run=False, docs=None):
    """Détecte les doublons et (si dry_run=False) supprime les copies en trop,
    en conservant un exemplaire par contenu. Renvoie un compte-rendu.

    `docs` limite l'opération à un périmètre donné (voir duplicate_groups)."""
    groups = duplicate_groups(store, docs=docs)
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
    """Assemble les extraits récupérés en un bloc de contexte sourcé pour le LLM.

    - déduplication des extraits quasi identiques (recouvrement des chunks) pour
      ne pas gaspiller le budget de contexte ;
    - étiquette de source enrichie « [Titre — Thème] » afin que le modèle puisse
      citer précisément et pondérer selon le domaine."""
    if not hits:
        return ""
    out, total, seen = [], 0, set()
    for h in hits:
        content = (h.get("content") or "").strip()
        if not content:
            continue
        key = re.sub(r"\s+", " ", content[:160].lower())
        if key in seen:
            continue
        seen.add(key)
        label = h.get("title") or "Document"
        theme = h.get("theme")
        if theme and theme not in ("Général", "Veille"):
            label += " — " + theme
        block = "[%s] %s" % (label, content)
        if total + len(block) > max_chars:
            remain = max_chars - total
            if remain > 300:                       # remplir le budget restant proprement
                cut = block[:remain]
                cut = cut[:cut.rfind(" ")] if " " in cut else cut
                out.append(cut)
            break
        out.append(block)
        total += len(block)
    if not out:
        return ""
    return ("Extraits de la base de connaissance CONSEILPREV (source interne fiable ; "
            "cite le titre entre crochets si tu t'en sers, et ignore les extraits non "
            "pertinents) :\n\n" + "\n\n---\n\n".join(out))
