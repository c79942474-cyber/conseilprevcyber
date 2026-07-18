"""Fausse plateforme OT pour tester le connecteur `otplatform` sans matériel.

Expose une petite API HTTP (stdlib) qui renvoie des alertes/actifs dans un schéma
proche de Nozomi/Claroty. À chaque appel de /api/alerts, quelques nouvelles alertes
(id incrémental) apparaissent, ce qui permet de valider le polling + le dédoublonnage.

    python -m connectors.mock_ot --port 8899
    # puis, dans un autre terminal :
    python -m connectors.connector otplatform --url http://127.0.0.1:8899/api/alerts \
        --target http://127.0.0.1:5000 --token "$INGEST_TOKEN"
"""
import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_DEVICES = [
    ("Automate S7-1500", "Cellule / Contrôle"),
    ("IHM Panel", "Cellule / Contrôle"),
    ("Station SCADA", "Supervision (SCADA)"),
    ("Serveur Historian", "Supervision (SCADA)"),
    ("Passerelle Modbus/TCP", "DMZ industrielle"),
    ("Switch industriel", "Terrain (capteurs)"),
    ("Capteur IIoT", "Terrain (capteurs)"),
    ("Débitmètre", "Terrain (capteurs)"),
    ("Firewall NGFW", "DMZ industrielle"),
    ("Poste ingénierie", "Entreprise (IT)"),
]
_ALERTS = [
    ("discovery", "info", "Nouvel actif détecté sur le segment"),
    ("anomaly", "critical", "Protocole en clair détecté (Modbus)"),
    ("anomaly", "critical", "Flux non autorisé Terrain -> IT"),
    ("threat", "critical", "Scan de ports depuis la DMZ"),
    ("vulnerability", "warning", "Firmware automate non à jour (CVE)"),
    ("policy", "warning", "Règle de flux non conforme à la matrice"),
    ("patch", "info", "Correctif « Approved » par le fournisseur"),
    ("info", "info", "Segmentation vérifiée entre zones"),
]

_counter = {"n": 0}


def _make_alerts(batch=3):
    out = []
    for _ in range(batch):
        i = _counter["n"]
        _counter["n"] += 1
        dev, zone = _DEVICES[i % len(_DEVICES)]
        atype, sev, name = _ALERTS[i % len(_ALERTS)]
        out.append({
            "id": "alert-%05d" % i,
            "device": dev,
            "zone": zone,
            "type": atype,
            "severity": sev,
            "name": name,
            "ts": int(time.time() * 1000),
        })
    return out


def _make_nozomi(batch=3):
    """Mêmes alertes, mais au format des champs Nozomi (pour tester --preset nozomi)."""
    # Nozomi exprime la gravité par un score numérique `risk` (0-10).
    risk = {"info": 2, "warning": 5, "critical": 9}
    return [{"id": a["id"], "appliance_host": a["device"], "zone": a["zone"],
             "type_id": a["type"], "name": a["name"], "risk": risk.get(a["severity"], 5),
             "record_created_at": a["ts"]} for a in _make_alerts(batch)]


# Inventaire « réseaux sans fil » (structure de la vue Wireless/Networks de Nozomi).
_WIFI = [
    ("Pharaoh", "802.11", True, -68), ("xfinitywifi", "802.11", True, -87),
    ("0x50a6", "802.15.4", True, -90), ("MariaFlores1", "802.11", True, -106),
    ("Porsche_WLAN_1232", "802.11", False, -88), ("Orange", "lora", False, -99),
]
_wcount = {"n": 0}


# Actifs OT (structure de la vue Assets / nodes de Nozomi, avec score de risque).
_NODES = [
    ("secrescontrollogix/first_controller", "Controller", "Cellule / Contrôle", "Rockwell Automation", 55),
    ("hmi-panelview-02", "HMI", "Cellule / Contrôle", "Rockwell Automation", 82),
    ("scada-server-01", "Server", "Supervision (SCADA)", "AVEVA", 41),
    ("flow-meter-14", "Sensor", "Terrain (capteurs)", "Endress+Hauser", 18),
    ("engineering-ws-03", "Workstation", "Entreprise (IT)", "Dell", 63),
]
_ncount = {"n": 0}


def _make_nodes(batch=3):
    out = []
    for _ in range(batch):
        i = _ncount["n"]
        _ncount["n"] += 1
        label, typ, zone, vendor, risk = _NODES[i % len(_NODES)]
        out.append({
            "id": "node-%05d" % i,
            "label": label,
            "type": typ,
            "zone": zone,
            "vendor": vendor,
            "risk": risk,
            "vulnerabilities": (i % 5) * 4,
            "record_created_at": int(time.time() * 1000),
        })
    return out


# Claroty xDome — alertes et actifs (réponses enveloppées dans "results").
_CL_ALERTS = [
    ("Unauthorized asset communication", "Network", "High", "hmi-panel-3", "Cellule / Contrôle"),
    ("New OT protocol command", "Anomaly", "Medium", "plc-line-2", "Cellule / Contrôle"),
    ("Suspicious external connection", "Threat", "Critical", "hist-01", "Supervision (SCADA)"),
    ("Baseline deviation", "Anomaly", "Low", "rtu-07", "Terrain (capteurs)"),
]
_CL_DEVICES = [
    ("plc-line-2", "PLC", "Cellule / Contrôle", 78),
    ("hmi-panel-3", "HMI", "Cellule / Contrôle", 52),
    ("hist-01", "Server", "Supervision (SCADA)", 34),
    ("rtu-07", "RTU", "Terrain (capteurs)", 15),
]
_clc = {"a": 0, "d": 0}


def _make_claroty_alerts(batch=3):
    out = []
    for _ in range(batch):
        i = _clc["a"]; _clc["a"] += 1
        name, cat, sev, dev, zone = _CL_ALERTS[i % len(_CL_ALERTS)]
        out.append({"id": "cl-alert-%05d" % i, "description": name, "category": cat,
                    "severity": sev, "device_name": dev, "zone": zone,
                    "detected_time": int(time.time() * 1000)})
    return out


def _make_claroty_devices(batch=4):
    out = []
    for _ in range(batch):
        i = _clc["d"]; _clc["d"] += 1
        name, atype, zone, risk = _CL_DEVICES[i % len(_CL_DEVICES)]
        out.append({"id": "cl-dev-%05d" % i, "name": name, "asset_type": atype,
                    "zone": zone, "risk_score": risk, "last_seen": int(time.time() * 1000)})
    return out


# Tenable OT Security — événements et actifs.
_TEN_EVENTS = [
    ("Unauthorized PLC configuration change", "Policy", "High", "PLC-Line1", "Zone-Cell"),
    ("New asset detected on network", "AssetDiscovery", "Info", "RTU-22", "Zone-Field"),
    ("Suspicious SCADA command", "IntrusionDetection", "Critical", "HMI-01", "Zone-Supervision"),
]
_TEN_ASSETS = [
    ("PLC-Line1", "PLC", "Zone-Cell", 74), ("HMI-01", "HMI", "Zone-Supervision", 58),
    ("RTU-22", "RTU", "Zone-Field", 22), ("Hist-DB", "Server", "Zone-Supervision", 40),
]
# Defender for IoT — alertes capteur (sévérités Minor/Major/Critical) et actifs.
_DEF_ALERTS = [
    ("Unauthorized Internet Connectivity", "Anomaly", "Major", "hmi-2", "Production"),
    ("New Asset Detected", "Discovery", "Minor", "plc-7", "Production"),
    ("Firmware Change Detected", "ProtocolViolation", "Critical", "rtu-3", "Field"),
    ("Suspicious Traffic", "Malware", "Warning", "ws-eng", "IT"),
]
_DEF_DEVICES = [
    ("plc-7", "PLC", "Production", "High"), ("hmi-2", "HMI", "Production", "Medium"),
    ("rtu-3", "RTU", "Field", "Low"), ("ws-eng", "Workstation", "IT", "High"),
]
_tdc = {"te": 0, "ta": 0, "da": 0, "dd": 0}


def _make_tenable_events(batch=3):
    out = []
    for _ in range(batch):
        i = _tdc["te"]; _tdc["te"] += 1
        title, typ, sev, asset, seg = _TEN_EVENTS[i % len(_TEN_EVENTS)]
        out.append({"id": "ten-ev-%05d" % i, "title": title, "type": typ, "severity": sev,
                    "asset_name": asset, "network_segment": seg, "time": int(time.time() * 1000)})
    return out


def _make_tenable_assets(batch=4):
    out = []
    for _ in range(batch):
        i = _tdc["ta"]; _tdc["ta"] += 1
        name, typ, seg, risk = _TEN_ASSETS[i % len(_TEN_ASSETS)]
        out.append({"id": "ten-as-%05d" % i, "name": name, "type": typ,
                    "network_segment": seg, "risk": risk, "last_seen": int(time.time() * 1000)})
    return out


def _make_defender_alerts(batch=3):
    out = []
    for _ in range(batch):
        i = _tdc["da"]; _tdc["da"] += 1
        name, engine, sev, dev, zone = _DEF_ALERTS[i % len(_DEF_ALERTS)]
        out.append({"id": "def-al-%05d" % i, "name": name, "engine": engine, "severity": sev,
                    "sourceDeviceName": dev, "zone": zone, "timeReceived": int(time.time() * 1000)})
    return out


def _make_defender_devices(batch=4):
    out = []
    for _ in range(batch):
        i = _tdc["dd"]; _tdc["dd"] += 1
        name, typ, zone, risk = _DEF_DEVICES[i % len(_DEF_DEVICES)]
        out.append({"id": "def-dev-%05d" % i, "name": name, "type": typ,
                    "zone": zone, "riskLevel": risk, "lastSeen": int(time.time() * 1000)})
    return out


def _make_wireless(batch=4):
    out = []
    for _ in range(batch):
        i = _wcount["n"]
        _wcount["n"] += 1
        name, proto, enabled, rssi = _WIFI[i % len(_WIFI)]
        out.append({
            "id": "wnet-%05d" % i,
            "name": name,
            "protocol": proto,
            "enabled": enabled,
            "avg_rssi": rssi,
            "avg_noise": None,
            "avg_snr": None,
            "network_domain_name": "Miramar",
            "site_name": "Miramar",
            "record_created_at": int(time.time() * 1000),
        })
    return out


class _Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/alerts"):
            self._json({"alerts": _make_alerts(batch=3)})
        elif self.path.startswith("/api/nozomi_wireless"):
            self._json({"result": _make_wireless(batch=4)})
        elif self.path.startswith("/api/nozomi_nodes"):
            self._json({"result": _make_nodes(batch=5)})
        elif self.path.startswith("/api/claroty_alerts"):
            self._json({"results": _make_claroty_alerts(batch=3)})
        elif self.path.startswith("/api/claroty_devices"):
            self._json({"results": _make_claroty_devices(batch=4)})
        elif self.path.startswith("/api/tenable_events"):
            self._json({"events": _make_tenable_events(batch=3)})
        elif self.path.startswith("/api/tenable_assets"):
            self._json({"assets": _make_tenable_assets(batch=4)})
        elif self.path.startswith("/api/defender_alerts"):
            self._json({"alerts": _make_defender_alerts(batch=4)})
        elif self.path.startswith("/api/defender_devices"):
            self._json({"devices": _make_defender_devices(batch=4)})
        elif self.path.startswith("/api/nozomi"):
            self._json({"result": _make_nozomi(batch=3)})
        elif self.path.startswith("/api/assets"):
            self._json({"assets": [{"id": "asset-%03d" % i, "device": d, "zone": z}
                                   for i, (d, z) in enumerate(_DEVICES)]})
        elif self.path in ("/", "/health"):
            self._json({"status": "ok", "service": "mock-ot"})
        else:
            self._json({"error": "not_found"}, code=404)

    def log_message(self, *args):
        pass  # silencieux


def main(argv=None):
    p = argparse.ArgumentParser(description="Fausse plateforme OT (test du connecteur otplatform).")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8899)
    args = p.parse_args(argv)
    srv = ThreadingHTTPServer((args.host, args.port), _Handler)
    print("Mock OT en écoute sur http://%s:%d  (/api/alerts, /api/assets)" % (args.host, args.port))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
