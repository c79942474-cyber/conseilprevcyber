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

# Presets par éditeur : chemin de la liste d'alertes + correspondance des champs.
# ⚠ Exemples de départ — À CONFIRMER avec la version et la doc API de votre plateforme.
# Les chemins pointés (« properties.deviceName ») sont résolus par _dig.
PRESETS = {
    "generic": {"alerts_path": "alerts", "mapping": GENERIC_MAPPING},
    "nozomi": {
        "alerts_path": "result",
        "mapping": {"id": "id", "asset": "appliance_host", "zone": "zone",
                    "type": "type_id", "event": "name", "severity": "severity",
                    "ts": "record_created_at"},
    },
    "claroty": {
        "alerts_path": "objects",
        "mapping": {"id": "resource_id", "asset": "hostname", "zone": "site_name",
                    "type": "category", "event": "description", "severity": "severity",
                    "ts": "timestamp"},
    },
    "tenable_ot": {
        "alerts_path": "events",
        "mapping": {"id": "id", "asset": "asset_name", "zone": "network_segment",
                    "type": "type", "event": "title", "severity": "severity", "ts": "time"},
    },
    "defender_iot": {
        "alerts_path": "value",
        "mapping": {"id": "id", "asset": "properties.deviceName", "zone": "properties.zone",
                    "type": "properties.alertType", "event": "properties.alertDisplayName",
                    "severity": "properties.severity", "ts": "properties.startTimeUtc"},
    },
}


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
