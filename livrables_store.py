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

import repli_direct   # le repli en connexion directe, ecrit une fois

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
        # ── Le rattachement au projet ──────────────────────────────────────
        # Sans ces quatre champs, l'historique était une liste plate : pour
        # retrouver « ce qui a été produit pour le projet Amsterdam en phase
        # APD », il fallait lire les intitulés un par un et espérer que la même
        # orthographe ait été employée à chaque fois.
        "projet_id": (rec.get("projet_id") or "")[:32],
        "phase": (rec.get("phase") or "")[:12].upper(),
        "filiere": (rec.get("filiere") or "")[:8],
        # L'état du LIVRABLE, distinct du statut du projet : un projet en cours
        # porte des brouillons et des pièces visées, et les confondre ferait
        # croire un dossier prêt parce que le projet avance.
        "etat": (rec.get("etat") or "brouillon")[:16],
        # Le CODE de la pièce du registre. Il était jusqu'ici noyé dans
        # l'intitulé (« APD SPC-HVAC — spécification CVC ») : retrouver « la
        # pièce SPC-HVAC de ce projet » supposait de découper une chaîne, ce
        # qui marche jusqu'au jour où l'intitulé change.
        "piece": (rec.get("piece") or "")[:24].upper(),
        # LE NUMÉRO ET L'INDICE DU DOCUMENT. Ils étaient calculés à la
        # rédaction, rendus à l'écran, portés au cartouche du Word — et perdus
        # ICI, parce que ce dictionnaire est le schéma : ce qui n'y figure pas
        # n'est pas enregistré. La liste des documents du projet les redemande,
        # et l'indice est précisément la colonne qu'on cherche dans un registre.
        "numero": (rec.get("numero") or "")[:60],
        "indice": (rec.get("indice") or "")[:8],
        # Les visas : qui a validé ou rejeté, à quel titre, quand et pourquoi.
        # Une liste, pas un état unique — un document rejeté par un collègue
        # puis validé par le client a DEUX avis, et n'en garder qu'un ferait
        # disparaître celui qui gêne.
        "visas": [v for v in (rec.get("visas") or []) if isinstance(v, dict)][:60],
    }


def _visas_lus(rec):
    """Relit la colonne `visas` sérialisée. Un JSON illisible rend une liste
    vide plutôt qu'une exception : un avis perdu se voit et se refait ; une
    fiche qui ne s'ouvre plus bloque tout le dossier."""
    v = rec.get("visas")
    if isinstance(v, list):
        return rec
    try:
        rec["visas"] = json.loads(v) if v else []
    except (ValueError, TypeError):
        rec["visas"] = []
    if not isinstance(rec["visas"], list):
        rec["visas"] = []
    return rec


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

    def changer_etat(self, lid, etat):
        """Fait passer un livrable de brouillon à relu, visé ou obsolète.

        Nommée `changer_etat` et non `etat` : l'enveloppe de résilience porte
        déjà une méthode `etat()` — sa propre santé — et elle a priorité sur le
        magasin. Un magasin nommé pareil aurait été appelé en production sans
        rien changer, sans erreur, et sans que l'écran s'en aperçoive.

        Sans ce geste, la colonne « état » ne serait qu'une décoration : tout
        resterait éternellement brouillon, et un dossier entièrement visé se
        lirait comme un dossier entièrement à relire."""
        with self._lock:
            r = self._items.get(lid)
            if not r:
                return False
            r["etat"] = etat
            return True

    def viser(self, lid, visa):
        with self._lock:
            r = self._items.get(lid)
            if not r:
                return None
            r["visas"] = ((r.get("visas") or []) + [visa])[-60:]
            return list(r["visas"])

    def stats(self):
        with self._lock:
            return {"count": len(self._items)}

    @staticmethod
    def _meta(r):
        m = {k: r.get(k) for k in ("id", "type", "label", "client", "secteur",
                                   "model", "created_at", "parent_id",
                                   "projet_id", "phase", "filiere", "etat",
                                   "piece", "visas")}
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
    # Rattachement au projet, à la phase et à la filière (ajouts compatibles :
    # les enregistrements antérieurs restent lisibles, sans projet).
    "ALTER TABLE livrables ADD COLUMN IF NOT EXISTS projet_id TEXT",
    "ALTER TABLE livrables ADD COLUMN IF NOT EXISTS phase TEXT",
    "ALTER TABLE livrables ADD COLUMN IF NOT EXISTS filiere TEXT",
    "ALTER TABLE livrables ADD COLUMN IF NOT EXISTS etat TEXT",
    "CREATE INDEX IF NOT EXISTS livrables_projet_idx "
    "ON livrables (projet_id, phase, created_at DESC)",
    # Le code de pièce et les visas (ajouts compatibles).
    "ALTER TABLE livrables ADD COLUMN IF NOT EXISTS piece TEXT",
    "ALTER TABLE livrables ADD COLUMN IF NOT EXISTS visas TEXT",
    # Le numéro et l'indice du document, que réclame la liste des documents du
    # projet (ajouts compatibles : les enregistrements antérieurs restent
    # lisibles, à l'indice par défaut).
    "ALTER TABLE livrables ADD COLUMN IF NOT EXISTS numero TEXT",
    "ALTER TABLE livrables ADD COLUMN IF NOT EXISTS indice TEXT",
]


class PostgresLivrablesStore:
    persistent = True
    _SCHEMA_LOCK = 907246

    _KW = {"autocommit": True, "prepare_threshold": None}

    def __init__(self, dsn):
        from psycopg_pool import ConnectionPool
        # prepare_threshold=None : compatibilité pooler PgBouncer (endpoint
        # « -pooler » de Neon). check : valide la connexion avant usage (réveil
        # à froid d'une base serverless).
        sep = "&" if "?" in dsn else "?"
        self._dsn = dsn + sep + "connect_timeout=10&client_encoding=UTF8"
        self._pool = ConnectionPool(self._dsn, min_size=1, max_size=2,
                                    kwargs=dict(self._KW),
                                    timeout=8, open=True,
                                    check=ConnectionPool.check_connection)
        try:
            self._init_schema()
        except Exception:
            try:
                self._pool.close()
            except Exception:
                pass
            raise

    def _conn(self):
        """Voir repli_direct : le pool d'abord, la connexion directe s'il boude."""
        return repli_direct.connexion(self, "livrables", _log, self._KW)

    def _init_schema(self):
        with self._conn() as conn:
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
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO livrables(id,type,label,client,secteur,perimetre,model,"
                "markdown,sources,created_at,parent_id,projet_id,phase,filiere,etat,"
                "piece,visas,numero,indice) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (lid, rec["type"], rec["label"], rec["client"], rec["secteur"],
                 rec["perimetre"], rec["model"], rec["markdown"],
                 json.dumps(rec["sources"], ensure_ascii=False), _now_ms(),
                 rec["parent_id"], rec["projet_id"], rec["phase"],
                 rec["filiere"], rec["etat"], rec["piece"],
                 json.dumps(rec["visas"], ensure_ascii=False),
                 rec["numero"], rec["indice"]))
        return lid

    def list(self):
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id,type,label,client,secteur,model,created_at,parent_id,"
                "projet_id,phase,filiere,etat,piece,visas,numero,indice,"
                "char_length(markdown) FROM livrables ORDER BY created_at DESC "
                "LIMIT %s", (LIST_LIMIT,)).fetchall()
        keys = ("id", "type", "label", "client", "secteur", "model", "created_at",
                "parent_id", "projet_id", "phase", "filiere", "etat", "piece",
                "visas", "numero", "indice", "chars")
        return [_visas_lus(dict(zip(keys, r))) for r in rows]

    def get(self, lid):
        # Le rattachement fait partie de l'enregistrement, pas seulement de sa
        # fiche : c'est sur `projet_id` que se vérifie le droit de reprendre un
        # document. L'omettre ici le laissait à None sur une base réelle, alors
        # que le magasin mémoire, lui, rendait le dictionnaire complet — le
        # contrôle passait donc au poste de travail et refusait tout en
        # production. Une colonne absente d'un SELECT ne se voit pas ; son
        # effet, si.
        with self._conn() as conn:
            r = conn.execute(
                "SELECT id,type,label,client,secteur,perimetre,model,markdown,sources,"
                "created_at,parent_id,projet_id,phase,filiere,etat,piece,visas,"
                "numero,indice FROM livrables WHERE id=%s", (lid,)).fetchone()
        if not r:
            return None
        keys = ("id", "type", "label", "client", "secteur", "perimetre", "model",
                "markdown", "sources", "created_at", "parent_id",
                "projet_id", "phase", "filiere", "etat", "piece", "visas",
                "numero", "indice")
        rec = _visas_lus(dict(zip(keys, r)))
        try:
            rec["sources"] = json.loads(rec["sources"]) if rec["sources"] else []
        except (ValueError, TypeError):
            rec["sources"] = []
        return rec

    def delete(self, lid):
        with self._conn() as conn:
            return conn.execute("DELETE FROM livrables WHERE id=%s", (lid,)).rowcount > 0

    def viser(self, lid, visa):
        """Ajoute un avis au livrable, sans écraser les précédents."""
        rec = self.get(lid)
        if not rec:
            return None
        visas = (rec.get("visas") or []) + [visa]
        visas = visas[-60:]
        with self._conn() as conn:
            conn.execute("UPDATE livrables SET visas=%s WHERE id=%s",
                         (json.dumps(visas, ensure_ascii=False), lid))
        return visas

    def changer_etat(self, lid, etat):
        with self._conn() as conn:
            return conn.execute("UPDATE livrables SET etat=%s WHERE id=%s",
                                (etat, lid)).rowcount > 0

    def stats(self):
        with self._conn() as conn:
            return {"count": conn.execute("SELECT count(*) FROM livrables").fetchone()[0]}


def _migrer(mem, pg):
    """Verse l'historique écrit pendant la panne dans la base retrouvée.

    DEUX PIÈGES, tous deux découverts en éprouvant la reprise sur une vraie
    base plutôt qu'en la relisant :

    `list()` ne renvoie que des MÉTADONNÉES — le markdown en est absent. Migrer
    depuis cette liste aurait recopié des enregistrements vides, que `save()`
    rejette en silence (il retourne None sans lever). On serait passé en base
    avec un historique intact en apparence et vide en fait. On repasse donc par
    `get()` pour chaque entrée.

    `save()` RÉATTRIBUE un identifiant. Les identifiants changent donc à la
    reprise. C'est acceptable ici — rien ne pointe vers un livrable par son
    identifiant hors de la console, et la filiation `parent_id` est recopiée
    telle quelle — mais il fallait le constater plutôt que le supposer.

    Un `save()` qui retourne None est compté comme un ÉCHEC : sans cela, la
    perte serait silencieuse, ce qui est exactement le défaut qu'on corrige."""
    repris = echecs = 0
    for meta in list(mem.list()):
        lid = meta.get("id")
        rec = mem.get(lid) if lid else None
        if not rec:
            echecs += 1
            continue
        try:
            if pg.save(dict(rec)):
                repris += 1
            else:
                echecs += 1
                _log.warning("Historique livrables : entrée %r refusée par la base.",
                             str(lid)[:40])
        except Exception:
            echecs += 1
            _log.warning("Historique livrables : entrée %r non reprise.", str(lid)[:40])
    return repris, echecs


def make_livrables_store():
    """Store persistant si DATABASE_URL est défini, sinon en mémoire.

    ENVELOPPÉ : sans cela, une base momentanément absente au démarrage
    condamnait l'historique à la mémoire pour toute la vie du processus — donc
    à disparaître au redéploiement suivant, sans que rien ne le signale."""
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return MemoryLivrablesStore()
    if dsn.startswith("postgres://"):
        dsn = "postgresql://" + dsn[len("postgres://"):]
    from resilience import MagasinResilient
    return MagasinResilient("Historique livrables",
                            lambda: PostgresLivrablesStore(dsn),
                            MemoryLivrablesStore(), migrer=_migrer)
