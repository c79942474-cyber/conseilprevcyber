"""Cœur commun des connecteurs : client d'ingestion + normalisation.

Sans dépendance externe (urllib standard) — le connecteur peut tourner sur un
collecteur isolé avec un simple Python 3.
"""
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

USER_AGENT = "conseilprev-connector/1.0"


def build_ssl_context(cafile=None, insecure=False):
    """Contexte TLS pour les appels HTTPS. Vérifie les certificats par défaut.

    `cafile` : bundle CA d'entreprise éventuel. `insecure` : DÉSACTIVE la
    vérification (déconseillé — uniquement pour un lab, jamais en production).
    """
    ctx = ssl.create_default_context(cafile=cafile) if cafile else ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx

# Zones canoniques du cockpit (doivent correspondre à demo.html pour que la carte
# réseau se mette à jour). Les autres valeurs restent affichées telles quelles.
CANONICAL_ZONES = [
    "Entreprise (IT)",
    "DMZ industrielle",
    "Supervision (SCADA)",
    "Cellule / Contrôle",
    "Terrain (capteurs)",
]

# Mots-clés -> zone canonique (heuristique de rattachement).
_ZONE_HINTS = [
    (("entreprise", "corporate", "corp", "bureautique", " it ", "erp"), "Entreprise (IT)"),
    (("dmz",), "DMZ industrielle"),
    (("scada", "supervision", "hmi", "ihm", "historian", "opc"), "Supervision (SCADA)"),
    (("cellule", "contrôle", "controle", "control", "plc", "automate", "cell"), "Cellule / Contrôle"),
    (("terrain", "field", "capteur", "sensor", "rtu", "instrument"), "Terrain (capteurs)"),
]

# Synonymes de sévérité -> valeur normalisée comprise par le cockpit.
# NB : les valeurs numériques des plateformes OT sont des SCORES DE RISQUE
# (plus haut = plus grave), traités à part ci-dessous — à ne pas confondre avec
# la priorité syslog (où 0 = le plus grave), déjà convertie en texte par la source syslog.
_SEV_CRIT = {"critical", "crit", "high", "very-high", "very high", "severe", "fatal",
             "emergency", "alert", "error", "major", "élevé", "eleve", "critique"}
_SEV_WARN = {"warning", "warn", "medium", "moderate", "notice", "minor", "moyen", "avertissement"}
_SEV_INFO = {"info", "informational", "low", "debug", "faible", "none", "unknown", "ok"}


def guess_zone(text):
    """Rattache un libellé de zone libre à une zone canonique, sinon le renvoie tel quel."""
    if not text:
        return ""
    low = " " + str(text).lower() + " "
    for hints, zone in _ZONE_HINTS:
        if any(h in low for h in hints):
            return zone
    return str(text)


def normalize_severity(value):
    """Ramène une sévérité arbitraire à critical / warning / info.

    Textuel : critical/high/medium/low… (+ synonymes FR). Numérique : interprété
    comme un score de risque (plus haut = plus grave) — échelle 0-10 par défaut,
    0-100 si la valeur dépasse 10.
    """
    if value is None:
        return "info"
    s = str(value).strip().lower()
    if s in _SEV_CRIT:
        return "critical"
    if s in _SEV_WARN:
        return "warning"
    if s in _SEV_INFO:
        return "info"
    try:
        n = float(s.replace(",", "."))
    except ValueError:
        return s or "info"
    if n > 10:  # échelle 0-100
        return "critical" if n >= 70 else "warning" if n >= 40 else "info"
    return "critical" if n >= 7 else "warning" if n >= 4 else "info"  # échelle 0-10


def infer_type(text, default="event"):
    """Devine le type d'événement à partir du message (découverte / correctif / …)."""
    low = (text or "").lower()
    if any(k in low for k in ("nouvel actif", "new asset", "discovered", "découvert", "inventaire", "asset detected")):
        return "discovery"
    if any(k in low for k in ("patch", "correctif", "mise à jour", "firmware", "update")):
        return "patch"
    return default


def normalize_event(raw):
    """Construit un événement propre {asset, zone, type, event, severity, ts}.

    `raw` est un dict aux clés partielles ; les champs manquants sont comblés.
    """
    event_txt = str(raw.get("event") or raw.get("message") or raw.get("description") or "").strip()
    zone_in = raw.get("zone") or raw.get("site") or raw.get("segment") or ""
    evt = {
        "asset": str(raw.get("asset") or raw.get("device") or raw.get("host") or raw.get("source") or "").strip()[:120],
        "zone": guess_zone(zone_in)[:80],
        "type": str(raw.get("type") or infer_type(event_txt))[:40],
        "event": event_txt[:240] or "Événement",
        "severity": normalize_severity(raw.get("severity"))[:16],
    }
    ts = raw.get("ts")
    evt["ts"] = int(ts) if isinstance(ts, (int, float)) else int(time.time() * 1000)
    return evt


class IngestClient:
    """Poste des événements normalisés sur /api/ingest (avec en-tête X-Ingest-Token)."""

    def __init__(self, base_url, token, timeout=10, dry_run=False, verbose=True, retries=3,
                 cafile=None, insecure=False, overrides=None):
        self.url = base_url.rstrip("/") + "/api/ingest"
        self.token = token
        self.timeout = timeout
        self.dry_run = dry_run
        self.verbose = verbose
        self.retries = retries
        self.overrides = overrides or {}  # valeurs constantes appliquées à chaque événement
        self.sent = 0
        self.failed = 0
        self.started_ts = time.time()
        self.last_success_ts = 0.0
        self._ctx = build_ssl_context(cafile, insecure)
        if insecure:
            self._log("ATTENTION : vérification TLS désactivée (--insecure). À éviter en production.")

    def _log(self, *args):
        if self.verbose:
            print(*args, file=sys.stderr, flush=True)

    def post(self, raw_event):
        evt = normalize_event(dict(raw_event, **self.overrides) if self.overrides else raw_event)
        line = "[{sev:^8}] {zone:<20} {asset:<22} {event}".format(
            sev=evt["severity"], zone=evt["zone"] or "-", asset=evt["asset"] or "-", event=evt["event"])
        if self.dry_run:
            self._log("DRY-RUN  " + line)
            self.sent += 1
            return True

        payload = json.dumps(evt).encode("utf-8")
        headers = {"content-type": "application/json", "X-Ingest-Token": self.token or "",
                   "User-Agent": USER_AGENT}
        delay = 1.0
        for attempt in range(1, self.retries + 1):
            try:
                req = urllib.request.Request(self.url, data=payload, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout, context=self._ctx) as resp:
                    if resp.status in (200, 201):
                        self.sent += 1
                        self.last_success_ts = time.time()
                        self._log("OK   " + line)
                        return True
                    self._log("HTTP %s  %s" % (resp.status, line))
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")[:200]
                if e.code in (401, 403):
                    self._log("AUTH %s — jeton INGEST_TOKEN invalide ou absent (%s)" % (e.code, body))
                    self.failed += 1
                    return False  # inutile de réessayer
                if e.code == 503:
                    self._log("503  ingestion désactivée côté serveur (INGEST_TOKEN non défini) — %s" % body)
                    self.failed += 1
                    return False
                self._log("HTTP %s  %s — %s" % (e.code, line, body))
            except urllib.error.URLError as e:
                self._log("RESEAU %s (tentative %d/%d)" % (e.reason, attempt, self.retries))
            if attempt < self.retries:
                time.sleep(delay)
                delay *= 2
        self.failed += 1
        return False

    def summary(self):
        self._log("--- %d événement(s) envoyé(s), %d échec(s) ---" % (self.sent, self.failed))


def client_from_args(args):
    """Construit un IngestClient depuis les options CLI communes (+ variables d'env)."""
    base = args.target or os.environ.get("COCKPIT_URL", "http://127.0.0.1:5000")
    token = args.token or os.environ.get("INGEST_TOKEN", "")
    if not base.startswith(("http://", "https://")):
        raise SystemExit("Cible invalide (--target / $COCKPIT_URL) : doit commencer par http:// ou https://")
    if base.startswith("http://") and not any(h in base for h in ("127.0.0.1", "localhost")):
        print("Attention : cible en HTTP non chiffré (hors localhost). Préférez HTTPS en production.",
              file=sys.stderr)
    if not token and not args.dry_run:
        print("Attention : aucun jeton (--token ou $INGEST_TOKEN). Le serveur refusera l'ingestion "
              "(401/503). Utilisez --dry-run pour tester sans envoyer.", file=sys.stderr)
    cafile = getattr(args, "cafile", None) or os.environ.get("COCKPIT_CAFILE")
    insecure = getattr(args, "insecure", False)
    overrides = {}
    for item in getattr(args, "set", None) or []:
        k, _, v = item.partition("=")
        if k:
            overrides[k.strip()] = v.strip()
    return IngestClient(base, token, timeout=args.timeout, dry_run=args.dry_run,
                        cafile=cafile, insecure=insecure, overrides=overrides)


def send_all(client, events, interval=0.0, loop=False):
    """Envoie un itérable d'événements, avec pause optionnelle et boucle optionnelle."""
    try:
        while True:
            for evt in events() if callable(events) else events:
                client.post(evt)
                if interval:
                    time.sleep(interval)
            if not loop:
                break
    except KeyboardInterrupt:
        pass
    finally:
        client.summary()
