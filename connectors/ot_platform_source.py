"""Source « plateforme OT » : interroge une API REST (Nozomi, Claroty, Tenable.ot,
Microsoft Defender for IoT, SIEM…) et convertit les alertes/actifs en événements.

Les plateformes ayant chacune leur schéma, le mapping est configurable :
  - `alerts_path` : chemin (pointé) vers la liste dans la réponse JSON, ex. "result.alerts".
  - `mapping`     : dict {champ_cible: chemin_source}, ex. {"event": "name", "zone": "site"}.
Un preset générique est fourni pour un schéma courant {alerts:[{id,name,severity,...}]}.

Fonctionne en mode passif : simple lecture (GET) de l'API de la plateforme.
"""
import collections
import json
import time
import urllib.error
import urllib.request

# Mapping par défaut (schéma générique de type Nozomi/Claroty simplifié).
GENERIC_MAPPING = {
    "id": "id",
    "asset": "device",
    "zone": "zone",
    "type": "type",
    "event": "name",
    "severity": "severity",
    "ts": "ts",
}

# Presets par éditeur : libellé, chemin de la liste d'alertes, correspondance des champs.
# ⚠ Points de départ — À CONFIRMER avec la version et la doc API de votre plateforme
# (les schémas évoluent entre versions). Les chemins pointés (« properties.deviceName »)
# sont résolus par _dig ; tout champ se surcharge ensuite avec --map champ=chemin.
PRESETS = {
    "generic": {
        "label": "Schéma générique {alerts:[{id,device,zone,type,name,severity,ts}]}",
        "alerts_path": "alerts", "mapping": GENERIC_MAPPING,
    },
    "nozomi": {
        "label": "Nozomi Networks — Guardian / Vantage (alertes, query=alerts)",
        "alerts_path": "result",
        "mapping": {"id": "id", "asset": "appliance_host", "zone": "zone",
                    "type": "type_id", "event": "name", "severity": "risk",
                    "ts": "record_created_at"},
    },
    "nozomi_wireless": {
        "label": "Nozomi — réseaux sans fil / inventaire (query=wireless_networks) — utiliser --set type=discovery",
        "alerts_path": "result",
        "mapping": {"id": "id", "asset": "name", "zone": "site_name",
                    "event": "name", "ts": "record_created_at"},
    },
    "claroty": {
        "label": "Claroty — CTD / xDome",
        "alerts_path": "objects",
        "mapping": {"id": "resource_id", "asset": "hostname", "zone": "site_name",
                    "type": "category", "event": "description", "severity": "severity",
                    "ts": "timestamp"},
    },
    "tenable_ot": {
        "label": "Tenable OT Security (ex-Indegy)",
        "alerts_path": "events",
        "mapping": {"id": "id", "asset": "asset_name", "zone": "network_segment",
                    "type": "type", "event": "title", "severity": "severity", "ts": "time"},
    },
    "defender_iot": {
        "label": "Microsoft Defender for IoT",
        "alerts_path": "value",
        "mapping": {"id": "id", "asset": "properties.deviceName", "zone": "properties.zone",
                    "type": "properties.alertType", "event": "properties.alertDisplayName",
                    "severity": "properties.severity", "ts": "properties.startTimeUtc"},
    },
    "dragos": {
        "label": "Dragos Platform (notifications)",
        "alerts_path": "data",
        "mapping": {"id": "id", "asset": "asset_hostname", "zone": "zone",
                    "type": "type", "event": "summary", "severity": "severity",
                    "ts": "created_at"},
    },
    "armis": {
        "label": "Armis Centrix",
        "alerts_path": "data.results",
        "mapping": {"id": "alertId", "asset": "deviceName", "zone": "site",
                    "type": "type", "event": "title", "severity": "severity", "ts": "time"},
    },
    "forescout": {
        "label": "Forescout — eyeInspect / SilentDefense",
        "alerts_path": "alerts",
        "mapping": {"id": "id", "asset": "host", "zone": "network",
                    "type": "category", "event": "name", "severity": "severity",
                    "ts": "timestamp"},
    },
    "cisco_cyber_vision": {
        "label": "Cisco Cyber Vision",
        "alerts_path": "events",
        "mapping": {"id": "id", "asset": "device", "zone": "group",
                    "type": "category", "event": "label", "severity": "severity",
                    "ts": "datetime"},
    },
}


def preset_summary():
    """Texte listant les presets disponibles (pour la commande `presets`)."""
    lines = ["Presets disponibles (--preset) — mappings à confirmer selon votre version d'API :"]
    for name in sorted(PRESETS):
        p = PRESETS[name]
        m = p["mapping"]
        lines.append("  %-18s %s" % (name, p.get("label", "")))
        lines.append("      alerts-path=%s  event<-%s  asset<-%s  zone<-%s  severity<-%s"
                     % (p["alerts_path"], m.get("event"), m.get("asset"),
                        m.get("zone"), m.get("severity")))
    return "\n".join(lines)


class _BoundedSeen:
    """Ensemble d'identifiants déjà vus, borné (évite une croissance mémoire infinie)."""

    def __init__(self, cap=5000):
        self.cap = cap
        self._set = set()
        self._order = collections.deque()

    def __contains__(self, key):
        return key in self._set

    def add(self, key):
        if key in self._set:
            return
        self._set.add(key)
        self._order.append(key)
        if len(self._order) > self.cap:
            self._set.discard(self._order.popleft())


def _dig(obj, path):
    """Extrait obj[a][b][c] pour un chemin 'a.b.c' (renvoie None si absent)."""
    if not path:
        return None
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _http_get_json(url, headers, timeout, context=None):
    hs = dict(headers or {})
    hs.setdefault("User-Agent", "conseilprev-connector/1.0")
    req = urllib.request.Request(url, headers=hs, method="GET")
    with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def map_record(record, mapping):
    """Applique le mapping {cible: chemin} à un enregistrement de la plateforme."""
    out = {}
    for target, src_path in mapping.items():
        val = _dig(record, src_path)
        if val is not None:
            out[target] = val
    return out


def poll(url, headers=None, mapping=None, alerts_path="alerts", id_field="id",
         interval=10.0, once=False, timeout=10, verbose=True, context=None):
    """Interroge l'API périodiquement et génère les nouveaux enregistrements mappés.

    Dédoublonne sur `id_field` (ou le champ mappé `id`) pour ne pas re-poster.
    Le suivi des identifiants vus est borné pour éviter toute fuite mémoire.
    """
    import sys
    mapping = mapping or GENERIC_MAPPING
    seen = _BoundedSeen()
    while True:
        try:
            data = _http_get_json(url, headers, timeout, context=context)
        except urllib.error.HTTPError as e:
            if verbose:
                print("Plateforme HTTP %s : %s" % (e.code, e.reason), file=sys.stderr)
            data = None
        except urllib.error.URLError as e:
            if verbose:
                print("Plateforme injoignable : %s" % e.reason, file=sys.stderr)
            data = None

        records = _dig(data, alerts_path) if (data is not None and alerts_path) else data
        if isinstance(records, dict):
            records = records.get("items") or records.get("data") or []
        if isinstance(records, list):
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                rid = rec.get(id_field, _dig(rec, mapping.get("id", "id")))
                key = json.dumps(rid, sort_keys=True) if rid is not None else json.dumps(rec, sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                yield map_record(rec, mapping)

        if once:
            break
        time.sleep(interval)
