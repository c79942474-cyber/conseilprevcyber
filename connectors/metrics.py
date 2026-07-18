"""Supervision du connecteur : petit serveur HTTP exposant des métriques Prometheus.

Expose (format texte Prometheus 0.0.4) :
  - conseilprev_connector_events_sent_total          (counter)
  - conseilprev_connector_events_failed_total        (counter)
  - conseilprev_connector_last_success_timestamp_seconds (gauge)
  - conseilprev_connector_start_timestamp_seconds    (gauge)
  - conseilprev_connector_up                         (gauge, toujours 1 tant que vivant)

et un point de liveness `/healthz`. Prometheus scrute `/metrics` ; l'alerting se
fait ensuite sur l'absence de scrape (connecteur mort), l'augmentation de
`..._events_failed_total`, ou la fraîcheur de `..._last_success_timestamp_seconds`.

Sans dépendance (http.server standard).
"""
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def render_metrics(client):
    now = int(time.time())
    m = [
        "# HELP conseilprev_connector_events_sent_total Événements envoyés avec succès.",
        "# TYPE conseilprev_connector_events_sent_total counter",
        "conseilprev_connector_events_sent_total %d" % client.sent,
        "# HELP conseilprev_connector_events_failed_total Événements en échec définitif.",
        "# TYPE conseilprev_connector_events_failed_total counter",
        "conseilprev_connector_events_failed_total %d" % client.failed,
        "# HELP conseilprev_connector_last_success_timestamp_seconds Dernier envoi réussi (epoch s).",
        "# TYPE conseilprev_connector_last_success_timestamp_seconds gauge",
        "conseilprev_connector_last_success_timestamp_seconds %d" % int(client.last_success_ts),
        "# HELP conseilprev_connector_start_timestamp_seconds Démarrage du connecteur (epoch s).",
        "# TYPE conseilprev_connector_start_timestamp_seconds gauge",
        "conseilprev_connector_start_timestamp_seconds %d" % int(client.started_ts),
        "# HELP conseilprev_connector_up Connecteur vivant.",
        "# TYPE conseilprev_connector_up gauge",
        "conseilprev_connector_up 1",
        "# HELP conseilprev_connector_scrape_timestamp_seconds Horodatage de ce scrape.",
        "# TYPE conseilprev_connector_scrape_timestamp_seconds gauge",
        "conseilprev_connector_scrape_timestamp_seconds %d" % now,
    ]
    return "\n".join(m) + "\n"


class _Handler(BaseHTTPRequestHandler):
    client = None  # renseigné par la sous-classe créée dans start_metrics_server

    def _send(self, body, code=200, ctype="text/plain; version=0.0.4; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/metrics"):
            self._send(render_metrics(self.client))
        elif self.path.startswith("/healthz"):
            self._send("ok\n")
        else:
            self._send("not found\n", code=404)

    def log_message(self, *args):
        pass  # silencieux


def start_metrics_server(client, host="0.0.0.0", port=9109):
    """Démarre le serveur de métriques en tâche de fond ; renvoie l'instance serveur."""
    handler = type("_BoundHandler", (_Handler,), {"client": client})
    srv = ThreadingHTTPServer((host, port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
