"""Source « plateforme OT » : interroge une API REST (Nozomi, Claroty, Tenable.ot,
Microsoft Defender for IoT, SIEM…) et convertit les alertes/actifs en événements.

Les plateformes ayant chacune leur schéma, le mapping est configurable :
  - `alerts_path` : chemin (pointé) vers la liste dans la réponse JSON, ex. "result.alerts".
  - `mapping`     : dict {champ_cible: chemin_source}, ex. {"event": "name", "zone": "site"}.
Un preset générique est fourni pour un schéma courant {alerts:[{id,name,severity,...}]}.

Fonctionne en mode passif : simple lecture (GET) de l'API de la plateforme.
"""
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


def _http_get_json(url, headers, timeout):
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
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
         interval=10.0, once=False, timeout=10, verbose=True):
    """Interroge l'API périodiquement et génère les nouveaux enregistrements mappés.

    Dédoublonne sur `id_field` (ou le champ mappé `id`) pour ne pas re-poster.
    """
    import sys
    mapping = mapping or GENERIC_MAPPING
    seen = set()
    while True:
        try:
            data = _http_get_json(url, headers, timeout)
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
