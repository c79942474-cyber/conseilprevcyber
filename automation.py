"""Automatisation temps réel CONSEILPREV — planificateur et travaux de fond.

Un planificateur léger (thread démon) exécute des travaux périodiques, chacun
best-effort et isolé (une erreur n'arrête jamais la boucle) :

  - auto-surveillance : alerte email si un magasin bascule en mode mémoire
    (base injoignable) — et signale le retour à la normale ;
  - purge RGPD automatique des fiches clients expirées (art. 5.1.e) + alerte
    30 jours avant échéance ;
  - indexation RAG autonome : les documents en attente d'embeddings sont
    indexés côté serveur (plus besoin de garder la console ouverte) ;
  - veille CERT-FR : lecture périodique des flux officiels (alertes + avis),
    résumé par LLM (best-effort), publication sur /veille et alimentation
    automatique de la base de connaissance (thème « Veille ») ;
  - alertes critiques du cockpit : agrégées et envoyées par email avec
    anti-rafale (au plus un envoi par heure) ;
  - rapport hebdomadaire : synthèse d'activité générée chaque lundi matin,
    déposée dans l'historique des livrables et envoyée par email.

L'état persistant (dernier envoi, éléments de veille déjà vus…) est stocké
dans PostgreSQL si DATABASE_URL est défini, sinon en mémoire. Aucune donnée
personnelle n'est journalisée. Désactivation globale : AUTOMATION_DISABLED=1.
"""
import base64
import hashlib
import html as html_lib
import json
import logging
import os
import re
import threading
import time
import xml.etree.ElementTree as ET

import requests

_log = logging.getLogger("automation")

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
VEILLE_FEEDS = [
    ("alerte", "https://www.cert.ssi.gouv.fr/alerte/feed/"),
    ("avis", "https://www.cert.ssi.gouv.fr/avis/feed/"),
]
VEILLE_MAX_ITEMS = 200
# Texte complet des bulletins (base de connaissance exploitable) : on récupère
# le contenu intégral du bulletin CERT-FR (JSON officiel, sinon HTML) plutôt que
# le seul résumé RSS. Désactivable (VEILLE_FULLTEXT=0) ; nombre max de bulletins
# récupérés en entier par passage (borne le temps du job en arrière-plan).
_VEILLE_FULLTEXT = os.environ.get("VEILLE_FULLTEXT", "1").strip().lower() not in ("0", "false", "no")
_VEILLE_FULLTEXT_MAX = int(os.environ.get("VEILLE_FULLTEXT_MAX", "25"))
ALERT_COOLDOWN_S = int(os.environ.get("ALERTES_COOLDOWN_MIN", "60")) * 60


def _now_ms():
    return int(time.time() * 1000)


# ============================================================================
#  État clé/valeur persistant (PostgreSQL si possible, sinon mémoire)
# ============================================================================
class _State:
    def __init__(self, dsn):
        self._mem = {}
        self._pool = None
        if dsn:
            try:
                from psycopg_pool import ConnectionPool
                sep = "&" if "?" in dsn else "?"
                dsn = dsn + sep + "connect_timeout=5&client_encoding=UTF8"
                self._pool = ConnectionPool(dsn, min_size=1, max_size=1,
                                            kwargs={"autocommit": True}, timeout=8, open=True)
                with self._pool.connection() as conn:
                    conn.execute("""CREATE TABLE IF NOT EXISTS automation_state (
                        key TEXT PRIMARY KEY, value TEXT)""")
                    conn.execute("""CREATE TABLE IF NOT EXISTS veille_items (
                        guid TEXT PRIMARY KEY,
                        source TEXT, title TEXT, link TEXT,
                        published BIGINT, resume TEXT, created_at BIGINT)""")
            except Exception as exc:
                _log.warning("automation : état en mémoire (PostgreSQL injoignable : %s)", exc)
                self._pool = None

    def get(self, key, default=None):
        if self._pool:
            try:
                with self._pool.connection() as conn:
                    r = conn.execute("SELECT value FROM automation_state WHERE key=%s",
                                     (key,)).fetchone()
                return r[0] if r else default
            except Exception:
                pass
        return self._mem.get(key, default)

    def set(self, key, value):
        self._mem[key] = value
        if self._pool:
            try:
                with self._pool.connection() as conn:
                    conn.execute(
                        "INSERT INTO automation_state(key,value) VALUES(%s,%s) "
                        "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (key, str(value)))
            except Exception:
                pass

    # -- veille --
    def veille_add(self, item):
        if self._pool:
            try:
                with self._pool.connection() as conn:
                    conn.execute(
                        "INSERT INTO veille_items(guid,source,title,link,published,resume,created_at) "
                        "VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (guid) DO NOTHING",
                        (item["guid"], item["source"], item["title"], item["link"],
                         item["published"], item["resume"], _now_ms()))
                    conn.execute(
                        "DELETE FROM veille_items WHERE guid IN (SELECT guid FROM veille_items "
                        "ORDER BY published DESC OFFSET %s)", (VEILLE_MAX_ITEMS,))
                return
            except Exception:
                pass
        lst = self._mem.setdefault("_veille", [])
        if not any(x["guid"] == item["guid"] for x in lst):
            lst.append(dict(item, created_at=_now_ms()))
            lst.sort(key=lambda x: x["published"], reverse=True)
            del lst[VEILLE_MAX_ITEMS:]

    def veille_has(self, guid):
        if self._pool:
            try:
                with self._pool.connection() as conn:
                    return bool(conn.execute("SELECT 1 FROM veille_items WHERE guid=%s",
                                             (guid,)).fetchone())
            except Exception:
                pass
        return any(x["guid"] == guid for x in self._mem.get("_veille", []))

    def veille_list(self, limit=60):
        if self._pool:
            try:
                with self._pool.connection() as conn:
                    rows = conn.execute(
                        "SELECT guid,source,title,link,published,resume FROM veille_items "
                        "ORDER BY published DESC LIMIT %s", (limit,)).fetchall()
                keys = ("guid", "source", "title", "link", "published", "resume")
                return [dict(zip(keys, r)) for r in rows]
            except Exception:
                pass
        return [dict(x) for x in self._mem.get("_veille", [])[:limit]]


# ============================================================================
#  Contexte global du module (rempli par init)
# ============================================================================
_deps = {}
_state = None
_started = False
_crit_lock = threading.Lock()
_crit_buffer = []


def notify_admin(subject, html_body):
    """Email à l'administrateur via Brevo (best-effort). Renvoie True si envoyé."""
    api_key = os.environ.get("BREVO_API_KEY")
    to = _deps.get("notify_to")
    sender = _deps.get("sender")
    if not (api_key and to and sender):
        return False
    try:
        r = requests.post(
            BREVO_API_URL,
            json={"sender": sender, "to": [{"email": to, "name": "CONSEILPREV"}],
                  "subject": subject, "htmlContent": html_body},
            headers={"api-key": api_key, "accept": "application/json",
                     "content-type": "application/json"}, timeout=12)
        return r.status_code in (200, 201)
    except requests.RequestException:
        return False


# ============================================================================
#  Travaux périodiques
# ============================================================================
def job_surveillance():
    """Alerte si un magasin est en mode mémoire (dégradé) — et au retour à la normale."""
    parts = []
    for name in ("rag", "clients", "livrables"):
        store = _deps.get(name)
        if store is not None and not getattr(store, "persistent", True):
            parts.append(name)
    mode = ",".join(parts) or "ok"
    previous = _state.get("sante.mode", "ok")
    if mode == previous:
        return
    _state.set("sante.mode", mode)
    if mode != "ok":
        notify_admin(
            "⚠️ Site en mode dégradé — base de données injoignable",
            "<p>Les magasins suivants fonctionnent <b>en mémoire</b> (données non "
            "persistées) : <b>%s</b>.</p><p>Vérifiez DATABASE_URL et l'état de la base "
            "PostgreSQL dans Render, puis redéployez si besoin.</p>" % html_lib.escape(mode))
    elif previous != "ok":
        notify_admin("✅ Site rétabli — persistance PostgreSQL active",
                     "<p>Tous les magasins sont repassés en mode persistant.</p>")


def job_purge_rgpd():
    """Purge quotidienne des fiches clients expirées (art. 5.1.e) + préavis 30 j."""
    clients = _deps.get("clients")
    if clients is None:
        return
    today = time.strftime("%Y-%m-%d")
    if _state.get("rgpd.last_purge") == today:
        return
    _state.set("rgpd.last_purge", today)
    n = clients.purge_expired(actor="automate")
    soon = [c for c in clients.list()
            if 0 < c.get("expire_at", 0) - _now_ms() < 30 * 24 * 3600 * 1000]
    if n or soon:
        rows = "".join("<li>%s — expire le %s</li>" % (
            html_lib.escape(c["entreprise"]),
            time.strftime("%d/%m/%Y", time.localtime(c["expire_at"] / 1000))) for c in soon[:20])
        notify_admin(
            "🧹 RGPD — conservation des fiches clients",
            ("<p><b>%d</b> fiche(s) expirée(s) purgée(s) automatiquement "
             "(journal pseudonymisé conservé).</p>" % n if n else "")
            + ("<p>Fiches arrivant à échéance sous 30 jours :</p><ul>%s</ul>"
               "<p>Prolongez la conservation (si la relation a repris) ou laissez la "
               "purge automatique faire son travail.</p>" % rows if soon else ""))


def job_index_rag():
    """Indexation vectorielle autonome des documents en attente (côté serveur)."""
    rag = _deps.get("rag")
    if rag is None or not getattr(rag, "persistent", False):
        return
    try:
        pending = [d for d in rag.list_documents() if d.get("status") == "indexing"]
    except Exception:
        return
    budget = 30                                  # lots max par passage (≈300 chunks)
    for doc in pending:
        while budget > 0:
            budget -= 1
            try:
                out = rag.index_next(doc["id"])
            except Exception:
                return
            if out.get("done") or out.get("degraded"):
                break
        if budget <= 0:
            return


def _strip_html(text):
    return re.sub(r"<[^>]+>", " ", text or "").replace("&nbsp;", " ").strip()


def _parse_feed(source, xml_text):
    """Extrait (guid, title, link, published, description) d'un flux RSS CERT-FR."""
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for it in root.iter("item"):
        def _t(tag):
            el = it.find(tag)
            return (el.text or "").strip() if el is not None and el.text else ""
        guid = _t("guid") or _t("link")
        if not guid:
            continue
        published = _now_ms()
        pub = _t("pubDate")
        if pub:
            try:
                published = int(time.mktime(time.strptime(pub[:25].strip(),
                                                          "%a, %d %b %Y %H:%M:%S"))) * 1000
            except (ValueError, OverflowError):
                pass
        items.append({"guid": guid, "source": source, "title": _t("title")[:300],
                      "link": _t("link")[:400], "published": published,
                      "description": _strip_html(_t("description"))[:2000]})
    return items


def _fetch_url(url, timeout=12):
    r = requests.get(url, timeout=timeout,
                     headers={"User-Agent": "conseilprevcyber-veille/1.0"})
    r.raise_for_status()
    return r.text


def _fetch_feed(url):
    return _fetch_url(url, timeout=20)


def _certfr_json_text(obj):
    """Extrait le texte lisible d'un bulletin CERT-FR au format JSON officiel.
    Cible le contenu intégral (champ « content ») ; à défaut, recompose à partir
    des champs utiles (résumé, systèmes affectés, CVE)."""
    if not isinstance(obj, dict):
        return ""
    content = obj.get("content")
    if isinstance(content, str) and len(content.strip()) > 60:
        return content.strip()
    bits = []
    for k in ("title", "summary", "description"):
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            bits.append(v.strip())
    for k, label in (("affected_systems", "Systèmes affectés"), ("cves", "CVE")):
        v = obj.get(k)
        if isinstance(v, list):
            names = []
            for x in v:
                if isinstance(x, str):
                    names.append(x)
                elif isinstance(x, dict):
                    names.append(x.get("name") or x.get("product")
                                 or x.get("cve") or x.get("description") or "")
            names = [n for n in names if n]
            if names:
                bits.append(label + " : " + ", ".join(names[:60]))
    return "\n\n".join(bits).strip()


_HTML_DROP = re.compile(r"(?is)<(script|style|nav|header|footer|aside|form|noscript)\b.*?</\1>")
_HTML_NL = re.compile(r"(?i)</(p|div|li|h[1-6]|tr|section|article)\s*>|<br\s*/?>")


def _html_to_text(html):
    """Convertit une page HTML en texte lisible (best-effort, sans dépendance) :
    retire scripts/nav/pied de page, privilégie le contenu principal, transforme
    les balises de bloc en sauts de ligne, décode les entités."""
    if not html:
        return ""
    html = _HTML_DROP.sub(" ", html)
    m = re.search(r"(?is)<(article|main)\b[^>]*>(.*?)</\1>", html)
    if m:
        html = m.group(2)
    html = _HTML_NL.sub("\n", html)
    text = re.sub(r"<[^>]+>", " ", html)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n[ \t]*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _fetch_bulletin_text(link, fetcher=None):
    """Texte complet d'un bulletin CERT-FR : JSON officiel de préférence, sinon
    page HTML. Best-effort — renvoie None si indisponible."""
    if not link or not _VEILLE_FULLTEXT:
        return None
    fetcher = fetcher or _fetch_url
    base = link.rstrip("/")
    try:                                   # 1) API JSON officielle : <lien>/json/
        txt = _certfr_json_text(json.loads(fetcher(base + "/json/")))
        if txt and len(txt) > 80:
            return txt[:40000]
    except Exception:
        pass
    try:                                   # 2) repli : page HTML du bulletin
        txt = _html_to_text(fetcher(link))
        if txt and len(txt) > 120:
            return txt[:40000]
    except Exception:
        pass
    return None


def veille_refresh(fetcher=None):
    """Lit les flux, résume les nouveautés (LLM best-effort), publie + alimente le RAG.
    Renvoie le nombre de nouveaux éléments."""
    feed_fetcher = fetcher or _fetch_feed
    # fetcher personnalisé (tests) réutilisé aussi pour les bulletins ; sinon le
    # récupérateur de bulletin utilise son défaut (timeout plus court).
    bulletin_fetcher = fetcher
    summarize = _deps.get("summarize")
    rag = _deps.get("rag")
    new_count = 0
    fulltext_budget = _VEILLE_FULLTEXT_MAX          # borne les récupérations/passage
    for source, url in VEILLE_FEEDS:
        try:
            xml_text = feed_fetcher(url)
        except Exception as exc:
            _log.warning("veille : flux %s injoignable (%s)", source, exc)
            continue
        for item in _parse_feed(source, xml_text)[:30]:
            if _state.veille_has(item["guid"]):
                continue
            resume = None
            if summarize:
                try:
                    resume = summarize(item["title"], item["description"])
                except Exception:
                    resume = None
            item["resume"] = (resume or item["description"][:500]).strip()
            _state.veille_add(item)
            new_count += 1
            # Alimente la base de connaissance (thème Veille, public) — best-effort.
            if rag is not None:
                try:
                    # Contenu intégral du bulletin (base exploitable) ; à défaut,
                    # le résumé. On borne le nombre de récupérations par passage.
                    body = item["resume"]
                    if fulltext_budget > 0:
                        fulltext_budget -= 1
                        full = _fetch_bulletin_text(item["link"], bulletin_fetcher)
                        if full:
                            body = full
                    md = ("# %s\n\nSource : CERT-FR (%s) — %s\n\n%s\n" %
                          (item["title"], source, item["link"], body))
                    slug = hashlib.sha256(item["guid"].encode()).hexdigest()[:10]
                    rag.ingest_bytes("veille-certfr-%s.md" % slug, md.encode("utf-8"),
                                     title="[CERT-FR] " + item["title"][:260],
                                     theme="Veille", visibility="public")
                except Exception:
                    pass
    if new_count:
        _state.set("veille.last_new", str(_now_ms()))
    return new_count


def veille_list(limit=60):
    return _state.veille_list(limit=limit) if _state else []


def job_veille():
    veille_refresh()


def record_critical(evt):
    """Appelé par l'ingestion cockpit pour chaque événement critique (anti-rafale)."""
    with _crit_lock:
        _crit_buffer.append({"asset": evt.get("asset", ""), "zone": evt.get("zone", ""),
                             "event": evt.get("event", ""), "ts": evt.get("ts")})
        del _crit_buffer[:-100]


def job_alertes():
    """Envoie au plus un email d'alerte agrégé par heure."""
    with _crit_lock:
        if not _crit_buffer:
            return
        last = float(_state.get("alertes.last_sent", "0") or 0)
        if time.time() - last < ALERT_COOLDOWN_S:
            return
        batch = list(_crit_buffer)
        _crit_buffer.clear()
    _state.set("alertes.last_sent", str(time.time()))
    rows = "".join("<li><b>%s</b> · zone %s — %s</li>" % (
        html_lib.escape(e["asset"] or "?"), html_lib.escape(e["zone"] or "?"),
        html_lib.escape(e["event"] or "")) for e in batch[:15])
    more = len(batch) - 15
    notify_admin(
        "🚨 Cockpit — %d événement(s) critique(s)" % len(batch),
        "<p>Événements critiques reçus par le cockpit :</p><ul>%s</ul>%s"
        "<p>Détail en temps réel : /demo · tendances : /tendances</p>"
        % (rows, ("<p>… et %d de plus.</p>" % more) if more > 0 else ""))


def _default_report(data):
    lines = ["# Rapport hebdomadaire — CONSEILPREV Cyber", "",
             "_Généré automatiquement — brouillon à relire._", ""]
    for section, values in data.items():
        lines.append("## " + section)
        if isinstance(values, dict):
            for k, v in values.items():
                lines.append("- **%s** : %s" % (k, v))
        else:
            lines.append(str(values))
        lines.append("")
    return "\n".join(lines)


def job_rapport_hebdo():
    """Chaque lundi ≥ 7 h : synthèse d'activité → historique livrables + email."""
    now = time.localtime()
    week = time.strftime("%G-W%V", now)
    if now.tm_wday != 0 or now.tm_hour < 7 or _state.get("rapport.week") == week:
        return
    _state.set("rapport.week", week)
    data = {}
    try:
        cockpit = _deps.get("cockpit")
        if cockpit is not None:
            t = cockpit.trends(days=7)
            total = sum(d.get("total", 0) for d in t.get("days", [])) if isinstance(t, dict) else 0
            data["Cockpit (7 jours)"] = {"événements": total}
    except Exception:
        pass
    for label, name, fn in (("Base de connaissance", "rag", "stats"),
                            ("Livrables", "livrables", "stats"),
                            ("Clients & prospects", "clients", "stats")):
        try:
            obj = _deps.get(name)
            if obj is not None:
                s = getattr(obj, fn)()
                data[label] = {k: v for k, v in s.items() if not isinstance(v, dict)}
        except Exception:
            pass
    data["Veille CERT-FR"] = {"éléments suivis": len(veille_list(limit=200))}

    md = None
    gen = _deps.get("generate_report")
    if gen:
        try:
            md = gen(data)
        except Exception:
            md = None
    md = md or _default_report(data)
    saved = None
    hist = _deps.get("livrables")
    if hist is not None:
        try:
            saved = hist.save({"type": "reporting-programme",
                               "label": "Rapport hebdomadaire automatique (%s)" % week,
                               "client": "CONSEILPREV — interne", "model": "automate",
                               "markdown": md, "sources": []})
        except Exception:
            saved = None
    notify_admin("📊 Rapport hebdomadaire — %s" % week,
                 "<p>Le rapport d'activité de la semaine est disponible dans "
                 "l'historique des livrables%s.</p>"
                 % (" (id %s)" % saved if saved else ""))


# ============================================================================
#  Planificateur
# ============================================================================
_JOBS = []


def _register_jobs():
    veille_hours = float(os.environ.get("VEILLE_INTERVAL_HOURS") or 6)
    _JOBS[:] = [
        {"name": "surveillance", "every": 3600, "fn": job_surveillance, "first": 90},
        {"name": "purge_rgpd", "every": 6 * 3600, "fn": job_purge_rgpd, "first": 300},
        {"name": "index_rag", "every": 120, "fn": job_index_rag, "first": 60},
        {"name": "veille", "every": veille_hours * 3600, "fn": job_veille, "first": 180},
        {"name": "alertes", "every": 300, "fn": job_alertes, "first": 120},
        {"name": "rapport_hebdo", "every": 3600, "fn": job_rapport_hebdo, "first": 600},
    ]
    now = time.time()
    for job in _JOBS:
        job["next"] = now + job["first"]


def _loop():
    while True:
        time.sleep(30)
        now = time.time()
        for job in _JOBS:
            if now < job["next"]:
                continue
            job["next"] = now + job["every"]
            try:
                job["fn"]()
            except Exception:
                _log.exception("automation : échec du travail %s", job["name"])


def init(sender=None, notify_to=None, rag=None, clients=None, livrables=None,
         cockpit=None, summarize=None, generate_report=None, dsn=None, start=True):
    """Initialise le contexte et démarre le planificateur (sauf AUTOMATION_DISABLED=1)."""
    global _state, _started
    _deps.update(sender=sender, notify_to=notify_to, rag=rag, clients=clients,
                 livrables=livrables, cockpit=cockpit, summarize=summarize,
                 generate_report=generate_report)
    _state = _State(dsn)
    _register_jobs()
    if _started or not start or os.environ.get("AUTOMATION_DISABLED") == "1":
        return
    _started = True
    threading.Thread(target=_loop, daemon=True).start()
    _log.info("automation : planificateur démarré (%d travaux)", len(_JOBS))
