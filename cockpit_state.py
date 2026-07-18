"""État du cockpit OT : inventaire, alertes, score de risque, événements récents.

Deux implémentations interchangeables (même interface apply/snapshot/reset) :
  - CockpitState : en mémoire (défaut) — parfait pour la démo publique, sans base.
  - PostgresStore : persistant (PostgreSQL) — conserve l'inventaire et l'historique
    dans la durée. Activé dès que la variable d'environnement DATABASE_URL est définie.

make_store() choisit l'implémentation selon l'environnement.

Sémantique commune :
  - inventaire : tout événement portant un `asset` enregistre/actualise cet actif ;
    « actifs découverts » = nombre d'actifs distincts.
  - zones : chaque actif est rattaché à une zone ; le compteur d'une zone = actifs distincts.
  - statut de zone : crit -> alert, warn -> watch (sauf si déjà alert), info -> ok.
  - alertes actives = nombre de zones en statut « alert ».
  - score de risque : valeur courante [0..98] (crit +2, disc +0.4, info -1).
  - événements : 50 derniers (ordre chronologique).
"""
import os
import threading

# Zones IEC 62443 du cockpit (doivent correspondre à demo.html).
ZONES_META = [
    ("ent", "Entreprise (IT)", "Niv. 4-5"),
    ("dmz", "DMZ industrielle", "Niv. 3.5"),
    ("sup", "Supervision (SCADA)", "Niv. 3"),
    ("cel", "Cellule / Contrôle", "Niv. 2"),
    ("ter", "Terrain (capteurs)", "Niv. 0-1"),
]
_ZONE_ID_BY_NAME = {name: zid for zid, name, _ in ZONES_META}
MAX_EVENTS = 50


def tag_for(evt):
    """Catégorise un événement : disc / crit / warn / patch / info."""
    t = (evt.get("type") or "").lower()
    s = (evt.get("severity") or "").lower()
    if "patch" in t or "correctif" in t:
        return "patch"
    if "disc" in t or "découv" in t or "asset" in t or "inventaire" in t:
        return "disc"
    if "crit" in s or s in ("high", "élevé", "eleve"):
        return "crit"
    if "warn" in s or s in ("medium", "moyen") or "avert" in s:
        return "warn"
    return "info"


def _risk_delta(tag):
    return 2.0 if tag == "crit" else 0.4 if tag == "disc" else -1.0 if tag == "info" else 0.0


def _event_text(evt):
    text = evt.get("event") or evt.get("asset") or "Événement"
    if evt.get("zone"):
        text += " — " + evt["zone"]
    return text


class CockpitState:
    """État courant en mémoire (thread-safe). Non persistant."""

    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        with self._lock:
            self.risk = 50.0
            self.assets_zone = {}  # asset -> zone (dernière vue)
            self.zone_status = {zid: "ok" for zid, _, _ in ZONES_META}
            self.events = []

    def _zone_counts(self):
        counts = {zid: 0 for zid, _, _ in ZONES_META}
        for zone in self.assets_zone.values():
            zid = _ZONE_ID_BY_NAME.get(zone)
            if zid:
                counts[zid] += 1
        return counts

    def apply(self, evt):
        tag = tag_for(evt)
        with self._lock:
            asset = evt.get("asset") or ""
            zone = evt.get("zone") or ""
            if asset:
                self.assets_zone[asset] = zone
            zid = _ZONE_ID_BY_NAME.get(zone)
            if zid:
                if tag == "crit":
                    self.zone_status[zid] = "alert"
                elif tag == "warn" and self.zone_status[zid] != "alert":
                    self.zone_status[zid] = "watch"
                elif tag == "info":
                    self.zone_status[zid] = "ok"
            self.risk = min(98.0, max(0.0, self.risk + _risk_delta(tag)))
            self.events.append({"tag": tag, "text": _event_text(evt), "ts": evt.get("ts")})
            if len(self.events) > MAX_EVENTS:
                self.events = self.events[-MAX_EVENTS:]
            return dict(evt, tag=tag), self._snapshot_locked()

    def _snapshot_locked(self):
        counts = self._zone_counts()
        zones = [{"id": zid, "name": name, "level": lvl,
                  "count": counts[zid], "status": self.zone_status[zid]}
                 for zid, name, lvl in ZONES_META]
        alerts = sum(1 for z in zones if z["status"] == "alert")
        return {"assets": len(self.assets_zone), "alerts": alerts, "risk": round(self.risk),
                "zones": zones, "events": list(self.events)}

    def snapshot(self):
        with self._lock:
            return self._snapshot_locked()


_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS events (
        id BIGSERIAL PRIMARY KEY, ts BIGINT NOT NULL,
        asset TEXT, zone TEXT, type TEXT, event TEXT, severity TEXT, tag TEXT)""",
    "CREATE INDEX IF NOT EXISTS events_ts_idx ON events (id DESC)",
    """CREATE TABLE IF NOT EXISTS assets (
        asset TEXT PRIMARY KEY, zone TEXT, first_seen BIGINT, last_seen BIGINT)""",
    "CREATE TABLE IF NOT EXISTS zone_status (id TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'ok')",
    "CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v DOUBLE PRECISION)",
]


class PostgresStore:
    """État persistant sur PostgreSQL. Interface identique à CockpitState.

    La table `events` est une série temporelle (horodatage `ts`) : elle peut être
    convertie en hypertable TimescaleDB si l'extension est disponible, sans changer le code.
    """

    def __init__(self, dsn):
        from psycopg_pool import ConnectionPool
        self._pool = ConnectionPool(dsn, min_size=1, max_size=4,
                                    kwargs={"autocommit": True}, open=True)
        self._init_schema()

    def _init_schema(self):
        with self._pool.connection() as conn:
            for stmt in _SCHEMA:
                conn.execute(stmt)
            for zid, _, _ in ZONES_META:
                conn.execute("INSERT INTO zone_status(id,status) VALUES(%s,'ok') "
                             "ON CONFLICT (id) DO NOTHING", (zid,))
            conn.execute("INSERT INTO meta(k,v) VALUES('risk',50) ON CONFLICT (k) DO NOTHING")

    def apply(self, evt):
        tag = tag_for(evt)
        asset = evt.get("asset") or ""
        zone = evt.get("zone") or ""
        zid = _ZONE_ID_BY_NAME.get(zone)
        ts = evt.get("ts")
        delta = _risk_delta(tag)
        with self._pool.connection() as conn:
            with conn.transaction():
                conn.execute(
                    "INSERT INTO events(ts,asset,zone,type,event,severity,tag) "
                    "VALUES(%s,%s,%s,%s,%s,%s,%s)",
                    (ts, asset or None, zone or None, evt.get("type"),
                     evt.get("event"), evt.get("severity"), tag))
                if asset:
                    conn.execute(
                        "INSERT INTO assets(asset,zone,first_seen,last_seen) VALUES(%s,%s,%s,%s) "
                        "ON CONFLICT (asset) DO UPDATE SET last_seen=EXCLUDED.last_seen, zone=EXCLUDED.zone",
                        (asset, zone or None, ts, ts))
                if zid:
                    if tag == "crit":
                        conn.execute("UPDATE zone_status SET status='alert' WHERE id=%s", (zid,))
                    elif tag == "warn":
                        conn.execute("UPDATE zone_status SET status='watch' WHERE id=%s AND status<>'alert'", (zid,))
                    elif tag == "info":
                        conn.execute("UPDATE zone_status SET status='ok' WHERE id=%s", (zid,))
                if delta:
                    conn.execute("UPDATE meta SET v=LEAST(98,GREATEST(0,v+%s)) WHERE k='risk'", (delta,))
            snap = self._snapshot(conn)
        return dict(evt, tag=tag), snap

    def _snapshot(self, conn):
        assets = conn.execute("SELECT count(*) FROM assets").fetchone()[0]
        counts = {zid: 0 for zid, _, _ in ZONES_META}
        for zone, c in conn.execute("SELECT zone,count(*) FROM assets GROUP BY zone").fetchall():
            zid = _ZONE_ID_BY_NAME.get(zone or "")
            if zid:
                counts[zid] = c
        statuses = dict(conn.execute("SELECT id,status FROM zone_status").fetchall())
        zones = [{"id": zid, "name": name, "level": lvl,
                  "count": counts[zid], "status": statuses.get(zid, "ok")}
                 for zid, name, lvl in ZONES_META]
        alerts = sum(1 for z in zones if z["status"] == "alert")
        risk_row = conn.execute("SELECT v FROM meta WHERE k='risk'").fetchone()
        risk = round(risk_row[0]) if risk_row else 50
        rows = conn.execute(
            "SELECT tag,event,asset,zone,ts FROM events ORDER BY id DESC LIMIT %s",
            (MAX_EVENTS,)).fetchall()
        events = []
        for tag, ev, asset, zone, ts in reversed(rows):
            text = (ev or asset or "Événement") + ((" — " + zone) if zone else "")
            events.append({"tag": tag, "text": text, "ts": ts})
        return {"assets": assets, "alerts": alerts, "risk": risk, "zones": zones, "events": events}

    def snapshot(self):
        with self._pool.connection() as conn:
            return self._snapshot(conn)

    def reset(self):
        with self._pool.connection() as conn:
            with conn.transaction():
                conn.execute("TRUNCATE events")
                conn.execute("TRUNCATE assets")
                conn.execute("UPDATE zone_status SET status='ok'")
                conn.execute("UPDATE meta SET v=50 WHERE k='risk'")


def make_store():
    """Retourne un store persistant si DATABASE_URL est défini, sinon en mémoire."""
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return CockpitState()
    if dsn.startswith("postgres://"):  # normalisation (Heroku/Render historique)
        dsn = "postgresql://" + dsn[len("postgres://"):]
    return PostgresStore(dsn)
