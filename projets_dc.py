"""Les projets d'ingénierie centre de données, et leur historique.

POURQUOI CE MODULE. L'historique des livrables existait déjà, mais à plat : une
liste de documents portant un nom de client en texte libre. Retrouver « ce qui a
été produit pour le projet Amsterdam, en phase APD » supposait de lire les
intitulés un par un et d'espérer que la même orthographe ait été employée à
chaque fois. Un projet est un OBJET : il a un identifiant, un propriétaire, une
filière, un statut, une date de dernière activité — et les livrables s'y
rattachent au lieu de le décrire.

LE PROPRIÉTAIRE EST STRUCTURANT. Chaque projet appartient au compte qui l'a
créé, et les lectures sont filtrées dessus. Sans ce filtre, deux clients
connectés au même service verraient l'historique l'un de l'autre — le genre de
défaut qui ne se voit qu'une fois, et une fois de trop.

Deux implémentations interchangeables, comme rag_store et livrables_store :
PostgreSQL si DATABASE_URL est défini, mémoire sinon.
"""
import json
import logging
import os
import threading
import time
import uuid

_log = logging.getLogger("projets_dc")

LIST_LIMIT = 400
MAX_PROJETS_PAR_COMPTE = 200

# Le statut d'un projet. Vocabulaire fermé : « en cours », « en_cours »,
# « EN COURS » écrits au fil de l'eau rendraient tout filtre inutile.
STATUTS = {
    "cadrage": {"nom": "Cadrage", "rang": 1,
                "aide": "Le projet est ouvert, les hypothèses ne sont pas arrêtées."},
    "en_cours": {"nom": "En cours", "rang": 2,
                 "aide": "Des phases sont franchies et des livrables produits."},
    "suspendu": {"nom": "Suspendu", "rang": 3,
                 "aide": "Arrêté temporairement ; l'historique reste consultable."},
    "livre": {"nom": "Livré", "rang": 4,
              "aide": "Le dossier a été remis. Les livrables restent accessibles "
                      "en lecture."},
    "archive": {"nom": "Archivé", "rang": 5,
                "aide": "Conservé pour mémoire, retiré des listes courantes."},
}
STATUT_DEFAUT = "cadrage"

# L'état d'un livrable dans le projet, distinct du statut du projet. Un projet
# « en cours » peut porter des brouillons ET des pièces visées : confondre les
# deux ferait croire qu'un dossier est prêt parce que le projet avance.
ETATS_LIVRABLE = {
    "brouillon": {"nom": "Brouillon", "rang": 1, "aide": "Produit, non relu."},
    "relu": {"nom": "Relu", "rang": 2,
             "aide": "Relu par un ingénieur, pas encore visé."},
    "vise": {"nom": "Visé", "rang": 3, "aide": "Visé et versé au dossier."},
    "obsolete": {"nom": "Obsolète", "rang": 4,
                 "aide": "Remplacé par une version postérieure."},
}
ETAT_DEFAUT = "brouillon"


def _ordre(vocabulaire):
    """Les clés d'un vocabulaire, dans l'ordre du CYCLE DE VIE.

    Un dictionnaire n'a pas d'ordre une fois sérialisé : Flask trie les clés,
    et la page recevait donc « archive, cadrage, en_cours, livre, suspendu ».
    Une liste déroulante bâtie sur cet ordre proposait « Archivé » en premier
    choix — et le premier choix est celui que le navigateur retient quand rien
    n'est sélectionné. Les projets naissaient archivés, donc invisibles dans
    leur propre liste, sans la moindre erreur nulle part.

    L'ordre est désormais porté par les données elles-mêmes, et servi à part.
    """
    return sorted(vocabulaire, key=lambda k: vocabulaire[k].get("rang", 99))


def _now_ms():
    return int(time.time() * 1000)


def _valid_id(v):
    return isinstance(v, str) and len(v) == 32 and all(
        c in "0123456789abcdef" for c in v)


def _clean(rec, partiel=False):
    """Normalise un projet entrant. `partiel` sert aux mises à jour."""
    out = {}
    if not partiel or "nom" in rec:
        nom = (rec.get("nom") or "").strip()[:160]
        if not nom:
            raise ProjetError("nom_manquant", 400,
                              "Un projet doit porter un nom.")
        out["nom"] = nom
    for champ, taille in (("client", 200), ("secteur", 80), ("perimetre", 80),
                          ("maitrise_ouvrage", 80), ("note", 2000)):
        if not partiel or champ in rec:
            out[champ] = (rec.get(champ) or "").strip()[:taille]
    if not partiel or "filiere" in rec:
        f = (rec.get("filiere") or "moe").strip()
        out["filiere"] = f if f in ("moe", "indus") else "moe"
    if not partiel or "statut" in rec:
        s = (rec.get("statut") or STATUT_DEFAUT).strip()
        out["statut"] = s if s in STATUTS else STATUT_DEFAUT
    if not partiel or "phase" in rec:
        out["phase"] = (rec.get("phase") or "").strip()[:12].upper()
    return out


class ProjetError(Exception):
    def __init__(self, code, status=400, detail=""):
        super().__init__(code)
        self.code = code
        self.status = status
        self.detail = detail or ""


# ============================================================================
#  Mémoire (repli non persistant)
# ============================================================================

class MemoryProjetsStore:
    def __init__(self):
        self._p = {}
        self._lock = threading.RLock()

    def creer(self, proprietaire, rec):
        r = _clean(rec)
        with self._lock:
            miens = [x for x in self._p.values() if x["proprietaire"] == proprietaire]
            if len(miens) >= MAX_PROJETS_PAR_COMPTE:
                raise ProjetError("trop_de_projets", 409,
                                  "Ce compte a atteint %d projets."
                                  % MAX_PROJETS_PAR_COMPTE)
            pid = uuid.uuid4().hex
            r.update(id=pid, proprietaire=proprietaire,
                     cree_le=_now_ms(), maj_le=_now_ms())
            self._p[pid] = r
            return dict(r)

    def lister(self, proprietaire, inclure_archives=False):
        with self._lock:
            out = [dict(x) for x in self._p.values()
                   if x["proprietaire"] == proprietaire
                   and (inclure_archives or x["statut"] != "archive")]
        return sorted(out, key=lambda x: -x["maj_le"])[:LIST_LIMIT]

    def obtenir(self, proprietaire, pid):
        with self._lock:
            r = self._p.get(pid)
            # Le contrôle de propriété est fait ICI et non dans la route :
            # une vérification posée dans l'appelant s'oublie au deuxième
            # appelant, et c'est ce jour-là qu'un client voit le dossier d'un
            # autre.
            return dict(r) if r and r["proprietaire"] == proprietaire else None

    def modifier(self, proprietaire, pid, rec):
        with self._lock:
            r = self._p.get(pid)
            if not r or r["proprietaire"] != proprietaire:
                return None
            r.update(_clean(rec, partiel=True))
            r["maj_le"] = _now_ms()
            return dict(r)

    def supprimer(self, proprietaire, pid):
        with self._lock:
            r = self._p.get(pid)
            if not r or r["proprietaire"] != proprietaire:
                return False
            del self._p[pid]
            return True

    def toucher(self, pid):
        """Marque une activité sur le projet. Appelé à chaque livrable produit :
        la date de dernière activité est ce qui trie utilement une liste de
        projets, et la recalculer à la lecture coûterait un parcours complet."""
        with self._lock:
            r = self._p.get(pid)
            if r:
                r["maj_le"] = _now_ms()

    def tous(self):
        with self._lock:
            return [dict(x) for x in self._p.values()]

    def restaurer(self, lignes):
        n = 0
        with self._lock:
            for r in lignes or []:
                if _valid_id(r.get("id")) and r.get("proprietaire"):
                    self._p[r["id"]] = dict(r)
                    n += 1
        return n


# ============================================================================
#  PostgreSQL
# ============================================================================

_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS projets_dc (
        id TEXT PRIMARY KEY,
        proprietaire TEXT NOT NULL,
        nom TEXT NOT NULL,
        client TEXT,
        secteur TEXT,
        perimetre TEXT,
        maitrise_ouvrage TEXT,
        filiere TEXT,
        phase TEXT,
        statut TEXT,
        note TEXT,
        cree_le BIGINT,
        maj_le BIGINT)""",
    "CREATE INDEX IF NOT EXISTS projets_dc_prop_idx "
    "ON projets_dc (proprietaire, maj_le DESC)",
]

_COLS = ("id,proprietaire,nom,client,secteur,perimetre,maitrise_ouvrage,"
         "filiere,phase,statut,note,cree_le,maj_le")


def _row(r):
    if not r:
        return None
    k = _COLS.split(",")
    return dict(zip(k, r))


class PostgresProjetsStore:
    def __init__(self, dsn):
        import psycopg
        self._psycopg = psycopg
        self._dsn = dsn
        with self._conn() as c:
            for s in _SCHEMA:
                c.execute(s)

    def _conn(self):
        return self._psycopg.connect(self._dsn, autocommit=True)

    def creer(self, proprietaire, rec):
        r = _clean(rec)
        with self._conn() as c:
            n = c.execute("SELECT COUNT(*) FROM projets_dc WHERE proprietaire=%s",
                          (proprietaire,)).fetchone()[0]
            if n >= MAX_PROJETS_PAR_COMPTE:
                raise ProjetError("trop_de_projets", 409,
                                  "Ce compte a atteint %d projets."
                                  % MAX_PROJETS_PAR_COMPTE)
            pid = uuid.uuid4().hex
            t = _now_ms()
            c.execute(
                "INSERT INTO projets_dc (" + _COLS + ") VALUES "
                "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (pid, proprietaire, r["nom"], r["client"], r["secteur"],
                 r["perimetre"], r["maitrise_ouvrage"], r["filiere"],
                 r["phase"], r["statut"], r["note"], t, t))
            return _row(c.execute("SELECT " + _COLS + " FROM projets_dc WHERE id=%s",
                                  (pid,)).fetchone())

    def lister(self, proprietaire, inclure_archives=False):
        q = ("SELECT " + _COLS + " FROM projets_dc WHERE proprietaire=%s"
             + ("" if inclure_archives else " AND statut<>'archive'")
             + " ORDER BY maj_le DESC LIMIT %s")
        with self._conn() as c:
            return [_row(x) for x in c.execute(q, (proprietaire, LIST_LIMIT)).fetchall()]

    def obtenir(self, proprietaire, pid):
        with self._conn() as c:
            return _row(c.execute(
                "SELECT " + _COLS + " FROM projets_dc WHERE id=%s AND proprietaire=%s",
                (pid, proprietaire)).fetchone())

    def modifier(self, proprietaire, pid, rec):
        r = _clean(rec, partiel=True)
        if not r:
            return self.obtenir(proprietaire, pid)
        sets = ", ".join("%s=%%s" % k for k in r) + ", maj_le=%s"
        vals = list(r.values()) + [_now_ms(), pid, proprietaire]
        with self._conn() as c:
            c.execute("UPDATE projets_dc SET " + sets
                      + " WHERE id=%s AND proprietaire=%s", vals)
        return self.obtenir(proprietaire, pid)

    def supprimer(self, proprietaire, pid):
        with self._conn() as c:
            return c.execute("DELETE FROM projets_dc WHERE id=%s AND proprietaire=%s",
                             (pid, proprietaire)).rowcount > 0

    def toucher(self, pid):
        with self._conn() as c:
            c.execute("UPDATE projets_dc SET maj_le=%s WHERE id=%s", (_now_ms(), pid))

    def tous(self):
        with self._conn() as c:
            return [_row(x) for x in c.execute(
                "SELECT " + _COLS + " FROM projets_dc").fetchall()]

    def restaurer(self, lignes):
        n = 0
        with self._conn() as c:
            for r in lignes or []:
                if not _valid_id(r.get("id")) or not r.get("proprietaire"):
                    continue
                c.execute(
                    "INSERT INTO projets_dc (" + _COLS + ") VALUES "
                    "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT (id) DO UPDATE SET nom=EXCLUDED.nom,"
                    "statut=EXCLUDED.statut,phase=EXCLUDED.phase,"
                    "note=EXCLUDED.note,maj_le=EXCLUDED.maj_le",
                    tuple(r.get(k) for k in _COLS.split(",")))
                n += 1
        return n


def _migrer(mem, pg):
    """Reverse le contenu mémoire dans PostgreSQL quand la base redevient
    joignable. Sans cela, les projets créés pendant une coupure disparaîtraient
    au redéploiement suivant — silencieusement."""
    lignes = mem.tous()
    if not lignes:
        return 0
    n = pg.restaurer(lignes)
    _log.info("Projets : %d enregistrement(s) reversés en base.", n)
    return n


def make_projets_store():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return MemoryProjetsStore()
    if dsn.startswith("postgres://"):
        dsn = "postgresql://" + dsn[len("postgres://"):]
    from resilience import MagasinResilient
    return MagasinResilient("Projets ingénierie",
                            lambda: PostgresProjetsStore(dsn),
                            MemoryProjetsStore(), migrer=_migrer)


def referentiel():
    """Les vocabulaires fermés, servis à la page plutôt que recopiés dedans."""
    return {"statuts": STATUTS, "statut_defaut": STATUT_DEFAUT,
            "statuts_ordre": _ordre(STATUTS),
            "etats_livrable": ETATS_LIVRABLE, "etat_defaut": ETAT_DEFAUT,
            "etats_ordre": _ordre(ETATS_LIVRABLE),
            "max_par_compte": MAX_PROJETS_PAR_COMPTE}
