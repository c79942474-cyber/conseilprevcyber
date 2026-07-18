# Connecter le cockpit à une plateforme OT — en réel, automatisé

Ce guide explique comment alimenter le cockpit **en continu** depuis une vraie
plateforme OT (Nozomi, Claroty, Tenable.ot, Microsoft Defender for IoT, un SIEM…).

## 1. Architecture — où tourne quoi

```
   RÉSEAU OT / SUPERVISION (interne)                 HÉBERGEMENT DU COCKPIT
 ┌───────────────────────────────────┐            ┌───────────────────────────┐
 │  Plateforme OT (Nozomi/Claroty/…)  │            │  Instance du site (Flask) │
 │        │  API REST (lecture)       │            │   /api/ingest  (jeton)    │
 │        ▼                           │  HTTPS     │        ▲                  │
 │   Connecteur (ce dépôt)  ──────────┼───────────▶│   /api/stream (SSE)       │
 │   systemd / Docker, 24/7           │  sortant   │        ▼                  │
 └───────────────────────────────────┘            │   /demo  (Temps réel)     │
                                                   └───────────────────────────┘
```

Deux règles importantes :

1. **Le connecteur tourne côté OT**, au plus près de la plateforme (zone de
   supervision / DMZ industrielle) : c'est le seul endroit d'où l'API de la
   plateforme est joignable. Il n'ouvre que des connexions **sortantes** en HTTPS
   vers le cockpit — aucun flux entrant vers l'OT.
2. **Pour de vraies données, visez une instance PRIVÉE du site** (`COCKPIT_URL`
   interne, accès restreint), **pas la démo publique** sur Render. La topologie et
   les vulnérabilités sont sensibles : elles ne doivent pas transiter par une page
   publique. La démo publique reste en mode « Démo » (données simulées).

## 2. Deux styles d'intégration

| Style | Comment | Connecteur |
|-------|---------|-----------|
| **Pull (API REST)** | Le connecteur interroge l'API de la plateforme toutes les N s | `otplatform` |
| **Push (syslog/CEF)** | La plateforme *émet* ses alertes en syslog vers le connecteur | `syslog --listen` |

Le **push syslog/CEF** est souvent le plus simple : la majorité des plateformes OT
savent forwarder leurs alertes en **CEF** (Common Event Format), que le connecteur
`syslog` décode nativement (nom d'alerte, sévérité, hôte, zone).

## 3. Mise en service automatisée (systemd)

```bash
# 1) Déposer le code (Python standard, aucune dépendance) et la config
sudo mkdir -p /etc/conseilprev /opt/conseilprev
sudo cp -r connectors /opt/conseilprev/
sudo cp connectors/deploy/connector.env.example /etc/conseilprev/connector.env
sudo nano /etc/conseilprev/connector.env      # COCKPIT_URL, INGEST_TOKEN, OT_API_URL…
sudo chmod 600 /etc/conseilprev/connector.env # le fichier contient des secrets

# 2) Installer et démarrer le service
sudo cp connectors/deploy/conseilprev-connector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now conseilprev-connector

# 3) Suivre
journalctl -u conseilprev-connector -f
```

Le service redémarre tout seul en cas de coupure (`Restart=always`) et au boot.
Variante **Docker** : voir `connectors/deploy/Dockerfile`.

## 4. Régler le mapping selon la plateforme

Chaque plateforme a son schéma JSON : on l'ajuste avec `--alerts-path` (où se trouve
la liste) et `--map champ=chemin` (correspondance des champs). Exemples de départ —
**à confirmer avec la version et la doc API de votre plateforme** :

**Nozomi (Guardian / Vantage)** — pull
```bash
python -m connectors.connector otplatform \
  --url "https://guardian/api/open/query/do?query=alerts" \
  --header "Authorization: Bearer $TOKEN" \
  --alerts-path "result" \
  --map event=name --map asset=appliance_host --map zone=zone --map severity=severity --map id=id
```

**Claroty (CTD / xDome)** — pull
```bash
python -m connectors.connector otplatform \
  --url "https://ctd/api/v1/alerts" --header "Authorization: Bearer $TOKEN" \
  --alerts-path "objects" \
  --map event=description --map asset=hostname --map zone=site_name --map severity=severity --map id=resource_id
```

**Tenable.ot** — pull
```bash
python -m connectors.connector otplatform \
  --url "https://tenableot/v1/events" --header "X-ApiKeys: accessKey=$AK; secretKey=$SK" \
  --alerts-path "events" \
  --map event=title --map asset=asset_name --map severity=severity --map id=id
```

**Microsoft Defender for IoT** — push (syslog/CEF, recommandé)
```bash
# Côté connecteur : écouter le CEF
python -m connectors.connector syslog --listen 0.0.0.0:5514
# Côté Defender for IoT : configurer un « Forwarding rule » syslog CEF -> IP:5514 du collecteur
```

Le connecteur normalise ensuite vers `{asset, zone, type, event, severity, ts}` et
rattache automatiquement la zone aux 5 zones du cockpit quand c'est possible.

## 5. Sécurité (à valider avec l'exploitant)

- **Passif / lecture seule** : jeton d'API **read-only** côté plateforme ; le
  connecteur ne fait que lire (GET) ou recevoir (syslog). Aucune écriture vers l'OT.
- **Cloisonnement** : connecteur dans une zone de supervision dédiée ; seul un flux
  **sortant HTTPS** vers le cockpit est ouvert (conduit maîtrisé, cohérent IEC 62443).
- **Secrets** : `INGEST_TOKEN` et le jeton plateforme via `EnvironmentFile` (chmod 600) ;
  jamais dans le dépôt. Rotation régulière.
- **Confidentialité** : instance du cockpit **privée** pour les données réelles,
  chiffrement en transit (TLS) et accès restreint (RBAC). La démo publique ne reçoit
  aucune donnée réelle.
- **Robustesse** : le broker SSE est en mémoire (mono-instance). Pour de la
  disponibilité 24/7 multi-instance, prévoir un bus partagé (Redis/NATS) et un
  stockage — voir `docs/integration-donnees-reelles.md`.
