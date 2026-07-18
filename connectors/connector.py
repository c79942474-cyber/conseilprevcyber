"""CLI unifiée des connecteurs du cockpit CONSEILPREV Cyber.

Sous-commandes :
  csv         Lit un fichier CSV et poste chaque ligne.
  syslog      Suit un fichier syslog ou écoute en UDP, parse et poste.
  otplatform  Interroge une plateforme OT (API REST) et poste les alertes.
  demo        Émet quelques événements synthétiques (test rapide, sans source).
  mock-ot     Lance une fausse plateforme OT pour tester `otplatform`.

Options communes :
  --target URL   Base du cockpit (déf. $COCKPIT_URL ou http://127.0.0.1:5000)
  --token TOK    Jeton d'ingestion (déf. $INGEST_TOKEN)
  --dry-run      Affiche sans envoyer
  --interval S   Pause entre deux envois (visualisation temps réel)

Exemples :
  python -m connectors.connector demo --dry-run
  python -m connectors.connector csv --file connectors/samples/events.csv --interval 1
  python -m connectors.connector syslog --listen 0.0.0.0:5514
  python -m connectors.connector otplatform --url http://127.0.0.1:8899/api/alerts --interval 3
"""
import argparse
import os
import signal
import sys
import time

# Imports robustes : fonctionne en module (-m) comme en script direct.
try:
    from . import core, csv_source, syslog_source, ot_platform_source, mock_ot
except ImportError:  # exécution directe : python connectors/connector.py
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from connectors import core, csv_source, syslog_source, ot_platform_source, mock_ot


# --------------------------------------------------------------------------- CSV
def cmd_csv(args):
    client = core.client_from_args(args)
    events = (row for row in csv_source.read_csv(args.file, delimiter=args.delimiter))
    core.send_all(client, events, interval=args.interval, loop=args.loop)


# ------------------------------------------------------------------------ SYSLOG
def cmd_syslog(args):
    client = core.client_from_args(args)
    if args.listen:
        host, _, port = args.listen.partition(":")
        lines = syslog_source.udp_listener(host or "0.0.0.0", int(port or 5514))
        client._log("Écoute syslog UDP sur %s:%s (Ctrl-C pour arrêter)…" % (host or "0.0.0.0", port or 5514))
    elif args.file:
        lines = syslog_source.follow_file(args.file, from_start=args.from_start)
        client._log("Suivi du fichier syslog %s (Ctrl-C pour arrêter)…" % args.file)
    else:
        print("Indiquez --listen HOST:PORT ou --file CHEMIN", file=sys.stderr)
        return 2

    def events():
        for ln in lines:
            evt = syslog_source.parse_syslog_line(ln)
            if not evt:
                continue
            if args.zone:
                evt["zone"] = args.zone
            if args.asset:
                evt["asset"] = args.asset
            yield evt

    core.send_all(client, events, interval=args.interval)


# -------------------------------------------------------------------- OT PLATFORM
def cmd_otplatform(args):
    client = core.client_from_args(args)
    headers = {}
    for h in args.header or []:
        k, _, v = h.partition(":")
        if k:
            headers[k.strip()] = v.strip()
    preset = ot_platform_source.PRESETS.get(args.preset or "generic",
                                            ot_platform_source.PRESETS["generic"])
    mapping = dict(preset["mapping"])
    for m in args.map or []:
        k, _, v = m.partition("=")
        if k:
            mapping[k.strip()] = v.strip()
    alerts_path = args.alerts_path or preset["alerts_path"]
    ctx = core.build_ssl_context(getattr(args, "cafile", None) or os.environ.get("COCKPIT_CAFILE"),
                                 getattr(args, "insecure", False))
    client._log("Interrogation de %s (preset=%s) toutes les %ss (Ctrl-C pour arrêter)…"
                % (args.url, args.preset or "generic", args.interval))
    events = ot_platform_source.poll(
        args.url, headers=headers, mapping=mapping, alerts_path=alerts_path,
        id_field=args.id_field, interval=args.interval, once=args.once, timeout=args.timeout, context=ctx)
    core.send_all(client, events)


# ---------------------------------------------------------------------------- DEMO
def cmd_demo(args):
    client = core.client_from_args(args)
    sample = [
        {"asset": "Automate S7-1500", "zone": "Supervision (SCADA)", "type": "discovery",
         "event": "Nouvel actif inventorié", "severity": "info"},
        {"asset": "IHM Panel", "zone": "Cellule / Contrôle", "type": "anomaly",
         "event": "Protocole en clair détecté (Modbus)", "severity": "critical"},
        {"asset": "Firewall NGFW", "zone": "DMZ industrielle", "type": "policy",
         "event": "Règle de flux non conforme à la matrice", "severity": "warning"},
        {"asset": "Serveur Historian", "zone": "Supervision (SCADA)", "type": "patch",
         "event": "Correctif « Installed »", "severity": "info"},
        {"asset": "Capteur IIoT", "zone": "Terrain (capteurs)", "type": "discovery",
         "event": "Nouvel actif inventorié", "severity": "info"},
    ]
    core.send_all(client, sample, interval=args.interval if args.interval else 1.0, loop=args.loop)


def cmd_mock_ot(args):
    mock_ot.main(["--host", args.host, "--port", str(args.port)])


def cmd_presets(args):
    print(ot_platform_source.preset_summary())


# ----------------------------------------------------------------------------- CLI
def build_parser():
    p = argparse.ArgumentParser(prog="connector", description="Connecteurs d'ingestion du cockpit OT.")
    # options communes (parent)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--target", default=None, help="URL du cockpit (déf. $COCKPIT_URL ou localhost:5000)")
    common.add_argument("--token", default=None, help="Jeton d'ingestion (déf. $INGEST_TOKEN)")
    common.add_argument("--timeout", type=float, default=10, help="Timeout HTTP (s)")
    common.add_argument("--dry-run", action="store_true", help="Afficher sans envoyer")
    common.add_argument("--interval", type=float, default=0.0, help="Pause entre envois (s)")
    common.add_argument("--cafile", default=None, help="Bundle CA d'entreprise pour la vérification TLS")
    common.add_argument("--insecure", action="store_true",
                        help="Désactiver la vérification TLS (déconseillé — lab uniquement)")

    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("csv", parents=[common], help="Lire un CSV et poster")
    c.add_argument("--file", required=True)
    c.add_argument("--delimiter", default=",")
    c.add_argument("--loop", action="store_true", help="Rejouer en boucle")
    c.set_defaults(func=cmd_csv)

    s = sub.add_parser("syslog", parents=[common], help="Suivre un fichier syslog ou écouter en UDP")
    s.add_argument("--file", help="Fichier syslog à suivre (tail -f)")
    s.add_argument("--listen", help="Écoute UDP HOST:PORT (ex. 0.0.0.0:5514)")
    s.add_argument("--from-start", action="store_true", help="Lire le fichier depuis le début")
    s.add_argument("--zone", help="Forcer la zone de tous les événements")
    s.add_argument("--asset", help="Forcer l'actif de tous les événements")
    s.set_defaults(func=cmd_syslog)

    o = sub.add_parser("otplatform", parents=[common], help="Interroger une plateforme OT (API REST)")
    o.add_argument("--url", required=True, help="URL de l'API d'alertes")
    o.add_argument("--preset", choices=sorted(ot_platform_source.PRESETS.keys()),
                   help="Préréglage éditeur (nozomi, claroty, tenable_ot, defender_iot, generic)")
    o.add_argument("--header", action="append", help="En-tête HTTP 'Clé: valeur' (répétable)")
    o.add_argument("--alerts-path", default=None, help="Chemin JSON de la liste (déf. selon le preset)")
    o.add_argument("--id-field", default="id", help="Champ identifiant pour le dédoublonnage")
    o.add_argument("--map", action="append", help="Mapping champ=chemin (répétable), ex. event=name")
    o.add_argument("--once", action="store_true", help="Un seul appel puis quitter")
    o.set_defaults(func=cmd_otplatform)

    d = sub.add_parser("demo", parents=[common], help="Émettre quelques événements synthétiques")
    d.add_argument("--loop", action="store_true", help="Rejouer en boucle")
    d.set_defaults(func=cmd_demo)

    m = sub.add_parser("mock-ot", help="Lancer une fausse plateforme OT (test)")
    m.add_argument("--host", default="127.0.0.1")
    m.add_argument("--port", type=int, default=8899)
    m.set_defaults(func=cmd_mock_ot)

    pp = sub.add_parser("presets", help="Lister les préréglages de plateforme OT disponibles")
    pp.set_defaults(func=cmd_presets)

    return p


def _install_sigterm():
    """Arrêt propre sur SIGTERM (systemd / Docker) : on le traite comme un Ctrl-C."""
    def handler(signum, frame):
        raise KeyboardInterrupt()
    try:
        signal.signal(signal.SIGTERM, handler)
    except Exception:
        pass


def main(argv=None):
    _install_sigterm()
    args = build_parser().parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
