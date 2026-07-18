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
