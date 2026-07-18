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
import datetime
import json
import logging
import os
import threading
import time


def _day_utc(ts_ms):
    return datetime.datetime.fromtimestamp((ts_ms or 0) / 1000,
                                           tz=datetime.timezone.utc).strftime("%Y-%m-%d")

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
    """Catégorise un événement : disc / crit / warn / patch / info.

    Sévérité textuelle (crit/high/medium/low…) ou numérique (score de risque,
    plus haut = plus grave : échelle 0-10, ou 0-100 si > 10).
    """
    t = (evt.get("type") or "").lower()
    s = (evt.get("severity") or "").lower()
    if "patch" in t or "correctif" in t:
        return "patch"
    if "disc" in t or "découv" in t or "asset" in t or "inventaire" in t:
        return "disc"
    if "crit" in s or s in ("high", "very-high", "very high", "major", "élevé", "eleve"):
        return "crit"
    if "warn" in s or s in ("medium", "minor", "moyen") or "avert" in s:
        return "warn"
    try:
        n = float(s.replace(",", "."))
        if n > 10:
            return "crit" if n >= 70 else "warn" if n >= 40 else "info"
        return "crit" if n >= 7 else "warn" if n >= 4 else "info"
    except ValueError:
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

    def purge(self, retention_days=None, max_rows=None, archive_path=None):
        """Élague l'historique en mémoire (déjà borné à MAX_EVENTS)."""
        with self._lock:
            before = len(self.events)
            if retention_days:
                cutoff = int((time.time() - retention_days * 86400) * 1000)
                self.events = [e for e in self.events if (e.get("ts") or 0) >= cutoff]
            if max_rows and len(self.events) > max_rows:
                self.events = self.events[-max_rows:]
            return before - len(self.events)

    def trends(self, days=14):
        """Agrège l'historique en mémoire (limité aux MAX_EVENTS derniers)."""
        since = int((time.time() - days * 86400) * 1000)
        by_day, by_tag, by_zone = {}, {}, {}
        with self._lock:
            evs = [e for e in self.events if (e.get("ts") or 0) >= since]
            total_all = len(self.events)
        for e in evs:
            tag = e.get("tag", "info")
            d = _day_utc(e.get("ts"))
            by_day.setdefault(d, {})
            by_day[d][tag] = by_day[d].get(tag, 0) + 1
            by_tag[tag] = by_tag.get(tag, 0) + 1
            text = e.get("text", "")
            zone = text.split(" — ")[-1] if " — " in text else "—"
            by_zone[zone] = by_zone.get(zone, 0) + 1
        return {"days": days, "by_day": by_day, "by_tag": by_tag, "by_zone": by_zone,
                "total": len(evs), "total_all": total_all}


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
        # connect_timeout borne l'attente si la base est injoignable (échoue vite).
        sep = "&" if "?" in dsn else "?"
        dsn = dsn + sep + "connect_timeout=5"
        self._pool = ConnectionPool(dsn, min_size=1, max_size=4,
                                    kwargs={"autocommit": True}, timeout=8, open=True)
        try:
            self._init_schema()
        except Exception:
            # Ferme le pool pour stopper ses threads de reconnexion (sinon spam de
            # logs « error connecting in 'pool-1' ») avant de remonter l'échec.
            try:
                self._pool.close()
            except Exception:
                pass
            raise

    # Verrou consultatif : sérialise la création du schéma entre instances
    # concurrentes (sinon deux « CREATE ... IF NOT EXISTS » simultanés se heurtent
    # dans le catalogue Postgres). Clé arbitraire mais stable.
    _SCHEMA_LOCK = 907243

    def _init_schema(self):
        with self._pool.connection() as conn:
            conn.execute("SELECT pg_advisory_lock(%s)", (self._SCHEMA_LOCK,))
            try:
                for stmt in _SCHEMA:
                    conn.execute(stmt)
                for zid, _, _ in ZONES_META:
                    conn.execute("INSERT INTO zone_status(id,status) VALUES(%s,'ok') "
                                 "ON CONFLICT (id) DO NOTHING", (zid,))
                conn.execute("INSERT INTO meta(k,v) VALUES('risk',50) ON CONFLICT (k) DO NOTHING")
            finally:
                conn.execute("SELECT pg_advisory_unlock(%s)", (self._SCHEMA_LOCK,))

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

    _PURGE_LOCK = 907244

    def purge(self, retention_days=None, max_rows=None, archive_path=None):
        """Élague la table `events` (rétention par âge et/ou par nombre de lignes).

        Archive éventuellement les lignes supprimées en JSONL avant de les effacer.
        Protégé par un verrou consultatif non bloquant : en multi-instance, une
        seule instance purge à la fois (les autres passent leur tour).
        """
        with self._pool.connection() as conn:
            got = conn.execute("SELECT pg_try_advisory_lock(%s)", (self._PURGE_LOCK,)).fetchone()[0]
            if not got:
                return 0
            try:
                ids = set()
                if retention_days:
                    cutoff = int((time.time() - float(retention_days) * 86400) * 1000)
                    ids.update(r[0] for r in conn.execute(
                        "SELECT id FROM events WHERE ts < %s", (cutoff,)).fetchall())
                if max_rows:
                    ids.update(r[0] for r in conn.execute(
                        "SELECT id FROM events ORDER BY id DESC OFFSET %s", (int(max_rows),)).fetchall())
                if not ids:
                    return 0
                ids = list(ids)
                if archive_path:
                    self._archive(conn, ids, archive_path)
                conn.execute("DELETE FROM events WHERE id = ANY(%s)", (ids,))
                return len(ids)
            finally:
                conn.execute("SELECT pg_advisory_unlock(%s)", (self._PURGE_LOCK,))

    def _archive(self, conn, ids, path):
        rows = conn.execute(
            "SELECT ts,asset,zone,type,event,severity,tag FROM events WHERE id = ANY(%s) ORDER BY id",
            (ids,)).fetchall()
        with open(path, "a", encoding="utf-8") as f:
            for ts, asset, zone, typ, ev, sev, tag in rows:
                f.write(json.dumps({"ts": ts, "asset": asset, "zone": zone, "type": typ,
                                    "event": ev, "severity": sev, "tag": tag},
                                   ensure_ascii=False) + "\n")

    def trends(self, days=14):
        """Agrège l'historique persisté (comptages par jour, par catégorie, par zone)."""
        since = int((time.time() - float(days) * 86400) * 1000)
        with self._pool.connection() as conn:
            by_day = {}
            for day, tag, c in conn.execute(
                    "SELECT to_char(to_timestamp(ts/1000.0),'YYYY-MM-DD') d, COALESCE(tag,'info') t, "
                    "count(*) FROM events WHERE ts>=%s GROUP BY d,t", (since,)).fetchall():
                by_day.setdefault(day, {})[tag] = c
            by_tag = {t: c for t, c in conn.execute(
                "SELECT COALESCE(tag,'info'), count(*) FROM events WHERE ts>=%s GROUP BY 1",
                (since,)).fetchall()}
            by_zone = {(z or "—"): c for z, c in conn.execute(
                "SELECT zone, count(*) FROM events WHERE ts>=%s GROUP BY 1 ORDER BY 2 DESC",
                (since,)).fetchall()}
            total = conn.execute("SELECT count(*) FROM events WHERE ts>=%s", (since,)).fetchone()[0]
            total_all = conn.execute("SELECT count(*) FROM events").fetchone()[0]
        return {"days": days, "by_day": by_day, "by_tag": by_tag, "by_zone": by_zone,
                "total": total, "total_all": total_all}


def make_store():
    """Retourne un store persistant si DATABASE_URL est défini, sinon en mémoire.

    Si PostgreSQL est injoignable au démarrage, on NE crashe PAS : repli en mémoire
    avec un avertissement (le service reste disponible ; corriger DATABASE_URL puis
    redéployer pour retrouver la persistance).
    """
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return CockpitState()
    if dsn.startswith("postgres://"):  # normalisation (Heroku/Render historique)
        dsn = "postgresql://" + dsn[len("postgres://"):]
    try:
        return PostgresStore(dsn)
    except Exception as exc:
        logging.getLogger("cockpit").warning(
            "PostgreSQL injoignable (%s) — repli en mémoire (état NON persistant). "
            "Vérifiez DATABASE_URL (URL interne, même région).", exc)
        return CockpitState()
