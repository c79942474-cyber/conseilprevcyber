"""Source syslog : suit un fichier syslog ou écoute en UDP, et parse les lignes.

Deux modes :
  - follow_file(path)      : équivalent « tail -f » (nouvelles lignes ajoutées).
  - udp_listener(host,port): serveur syslog UDP (RFC 3164 / 5424, parse tolérant).

Chaque ligne est convertie en dict {asset(host), zone, event(message), severity}
prêt pour core.normalize_event. La sévérité provient de la priorité <PRI> quand
elle est présente, sinon d'une heuristique sur le message.
"""
import re
import socket
import time

# <PRI> = facility*8 + severity (RFC 5424). severity 0..7.
_PRI_RE = re.compile(r"^<(\d{1,3})>")
# RFC 3164 : <PRI>Mmm dd hh:mm:ss host tag: message
_RFC3164_RE = re.compile(
    r"^<\d{1,3}>(?:\w{3}\s+\d+\s+\d+:\d+:\d+)\s+(?P<host>\S+)\s+(?P<msg>.*)$")
# RFC 5424 : <PRI>1 TIMESTAMP host app procid msgid [sd] message
_RFC5424_RE = re.compile(
    r"^<\d{1,3}>1\s+\S+\s+(?P<host>\S+)\s+(?P<app>\S+)\s+\S+\s+\S+\s+(?:\[.*?\]|-)\s*(?P<msg>.*)$")

_SEV_NAMES = {0: "critical", 1: "critical", 2: "critical", 3: "critical",
              4: "warning", 5: "info", 6: "info", 7: "info"}

_ATTACK_HINTS = ("denied", "deny", "drop", "reject", "attack", "malware", "exploit",
                 "unauthorized", "intrusion", "scan", "brute", "anomal", "refus", "bloqué")


def parse_syslog_line(line):
    """Transforme une ligne syslog brute en dict d'événement (ou None si vide)."""
    line = (line or "").strip()
    if not line:
        return None

    severity = None
    m = _PRI_RE.match(line)
    if m:
        pri = int(m.group(1))
        severity = _SEV_NAMES.get(pri & 0x07, "info")

    host, msg = "", line
    m5 = _RFC5424_RE.match(line)
    m3 = _RFC3164_RE.match(line)
    if m5:
        host, msg = m5.group("host"), m5.group("msg")
    elif m3:
        host, msg = m3.group("host"), m3.group("msg")
    else:
        # Pas de format reconnu : on retire juste un éventuel <PRI> en tête.
        msg = _PRI_RE.sub("", line).strip()

    # Sévérité de repli via mots-clés si <PRI> absent.
    if severity is None:
        severity = "critical" if any(h in msg.lower() for h in _ATTACK_HINTS) else "info"

    return {"asset": host, "event": msg, "severity": severity, "zone": host}


def follow_file(path, from_start=False, poll=0.5):
    """Génère les lignes d'un fichier au fil de l'eau (comme « tail -f »)."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        if not from_start:
            f.seek(0, 2)  # fin de fichier : on ne lit que les nouvelles lignes
        while True:
            line = f.readline()
            if line:
                yield line
            else:
                time.sleep(poll)


def udp_listener(host="0.0.0.0", port=5514, bufsize=8192):
    """Écoute des messages syslog en UDP et génère chaque datagramme (texte)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    try:
        while True:
            data, addr = sock.recvfrom(bufsize)
            text = data.decode("utf-8", "replace")
            for ln in text.splitlines() or [text]:
                yield ln
    finally:
        sock.close()
