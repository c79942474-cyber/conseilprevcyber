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

## 4. Brancher votre plateforme (8 éditeurs préconfigurés)

Un **préréglage** `--preset` fixe d'emblée `--alerts-path` et le mapping des champs ;
tout reste surchargeable avec `--map champ=chemin`. Voir les mappings exacts avec
`python -m connectors.connector presets`.

> ⚠️ Les endpoints / champs ci-dessous sont des **points de départ réalistes** : ils
> varient selon la **version** et l'édition (on-prem vs cloud) de chaque produit —
> confirmez-les avec la doc API de votre instance. La sévérité est gérée quelle qu'en
> soit la forme : texte (`High`/`Medium`/`Low`, `Critical`, `Very-High`…) **ou** score
> numérique de risque (0-10 ou 0-100, plus haut = plus grave).

| Éditeur | `--preset` | Mode conseillé | Endpoint type | Authentification |
|---|---|---|---|---|
| Nozomi (Guardian/Vantage) | `nozomi` | API **ou** CEF | `/api/open/query/do?query=alerts` (`result`) | `Authorization: Bearer` ou clé de session |
| Claroty (CTD/xDome) | `claroty` | API **ou** CEF | `/api/v1/alerts` (`objects`) | `Authorization: Bearer` |
| Tenable OT Security | `tenable_ot` | API | `/v1/events` (`events`) | `X-ApiKeys: accessKey=…;secretKey=…` |
| Microsoft Defender for IoT | `defender_iot` | **CEF** (capteur) ou Graph API | Graph `/v1.0/security/alerts_v2` (`value`) | Azure AD `Bearer` |
| Dragos Platform | `dragos` | API | `/api/v1/notifications` (`data`) | `Authorization: Bearer` / API-Token |
| Armis Centrix | `armis` | API | `/api/v1/alerts/` (`data.results`) | jeton d'accès (via secret key) |
| Forescout (eyeInspect) | `forescout` | API **ou** CEF | Command Center API (`alerts`) | jeton |
| Cisco Cyber Vision | `cisco_cyber_vision` | API | `/api/3.0/events` (`events`) | `x-token-id` |

**Exemple — pull API (Nozomi)** :
```bash
python -m connectors.connector otplatform --preset nozomi \
  --url "https://guardian/api/open/query/do?query=alerts" \
  --header "Authorization: Bearer $TOKEN" --interval 10 --metrics-port 9109
```

**Nozomi expose trois flux utiles** (requêtes N2QL sur Guardian) :

- **Actifs OT** (`query=nodes`, preset `nozomi_assets`) — *recommandé*. Chaque actif
  arrive avec son **score de risque** (0-100) mappé sur la sévérité : risque ≥ 70 →
  critique, 40-69 → avertissement, < 40 → info. Alimente l'inventaire ET pondère les zones.

```bash
python -m connectors.connector otplatform --preset nozomi_assets \
  --url "https://guardian/api/open/query/do?query=nodes" \
  --header "Authorization: Bearer $TOKEN" --interval 30 --metrics-port 9109
```

- **Alertes** (`query=alerts`, preset `nozomi`) — sécurité (alertes actives). La gravité
  est le score numérique `risk` — géré automatiquement.
- **Réseaux sans fil** (`query=wireless_networks`, preset `nozomi_wireless`) — inventaire
  Wi-Fi/IIoT. Pas des alertes : on force `type=discovery` et on choisit la zone avec `--set` :

```bash
python -m connectors.connector otplatform --preset nozomi_wireless \
  --url "https://guardian/api/open/query/do?query=wireless_networks" \
  --header "Authorization: Bearer $TOKEN" \
  --set type=discovery --set "zone=Terrain (capteurs)" \
  --interval 30 --metrics-port 9110
```

> *Autres tables Nozomi exploitables de la même façon si besoin :* `vulnerabilities`
> (CVE par actif), `sessions`, `variables`. Le Threat Intelligence (CVE/malware/acteurs)
> relève plutôt de la gestion de vulnérabilités que du flux temps réel du cockpit.

> `--set CHAMP=VALEUR` force une valeur constante sur chaque événement (utile quand la
> source n'a pas de champ `type`/`severity`, ou pour rattacher tout un flux à une zone
> du cockpit). Le cockpit a **5 zones fixes** (modèle IEC) : les sites/zones Nozomi
> (ex. « Miramar ») n'y correspondent pas automatiquement — d'où le `--set zone=…`.

**Exemple — plateforme au schéma imbriqué (Armis, `data.results`)** — déjà géré par le preset :
```bash
python -m connectors.connector otplatform --preset armis \
  --url "https://<tenant>.armis.com/api/v1/alerts/" \
  --header "Authorization: $ARMIS_TOKEN" --interval 15
```

**Exemple — push syslog/CEF (recommandé pour Defender for IoT, aussi possible Nozomi/Claroty/Forescout)** :
```bash
# Sur le collecteur : écouter le CEF (le connecteur décode nom, sévérité, hôte, zone)
python -m connectors.connector syslog --listen 0.0.0.0:5514 --metrics-port 9109
# Sur la plateforme : créer une règle de transfert syslog/CEF -> IP_collecteur:5514
```

**Ajuster un champ** si votre version diffère (ex. la zone est dans `site` au lieu de `zone`) :
```bash
python -m connectors.connector otplatform --preset nozomi --url … --map zone=site --map asset=host
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
  disponibilité 24/7 multi-instance, prévoir un bus partagé (Redis/NATS) — voir
  `docs/integration-donnees-reelles.md`.
- **TLS** : la vérification des certificats est active par défaut. Pour une PKI
  interne, `--cafile /chemin/ca.pem` (ou `COCKPIT_CAFILE`). `--insecure` existe
  pour un lab uniquement — jamais en production.

## 6. Persistance (conserver l'inventaire et l'historique)

Par défaut l'état du cockpit est **en mémoire** (perdu au redémarrage). Pour le
conserver dans la durée, définir **`DATABASE_URL`** (PostgreSQL) côté cockpit :

```bash
# Render : créer une base « Postgres » puis coller son URL interne dans la variable
# d'environnement DATABASE_URL du service (dashboard) — le schéma se crée tout seul.
DATABASE_URL=postgresql://user:pass@host:5432/cockpit
```

- Tables créées automatiquement : `events` (série temporelle horodatée),
  `assets` (inventaire), `zone_status`, `meta`. La table `events` peut devenir une
  **hypertable TimescaleDB** si l'extension est disponible, sans changer le code.
- Sans `DATABASE_URL`, rien ne change : l'état reste en mémoire (parfait pour la démo).

## 7. Instance privée (authentification)

Pour une instance qui reçoit de **vraies** données, protéger tout le site par
authentification HTTP Basic en définissant côté cockpit :

```bash
COCKPIT_AUTH_USER=exploitant
COCKPIT_AUTH_PASSWORD=un-mot-de-passe-fort
```

- Tout le site (pages, `/api/state`, `/api/stream`) passe alors derrière la
  fenêtre de connexion du navigateur.
- **Exemptés** : `/health` (sonde Render) et les endpoints machine `/api/ingest`,
  `/api/reset` — déjà protégés par `INGEST_TOKEN`, pour que les connecteurs restent
  simples (ils n'envoient que le jeton, pas d'identifiants Basic).
- Non défini ⇒ site public (la démo). À combiner avec HTTPS (fourni par Render).

## 8. Haute disponibilité (multi-instance)

Pour tenir plusieurs instances derrière un load-balancer, deux briques partagées :

- **État partagé** : `DATABASE_URL` (PostgreSQL) — toutes les instances lisent/écrivent
  le même inventaire et le même historique (l'instantané d'ouverture est donc cohérent
  quelle que soit l'instance qui répond).
- **Bus d'événements partagé** : `REDIS_URL` (Redis pub/sub) — un événement ingéré sur
  **n'importe quelle** instance est rediffusé à **toutes** les instances, donc à tous les
  cockpits connectés, où qu'ils soient. Canal configurable via `REDIS_CHANNEL`
  (défaut `cockpit:events`).

```bash
DATABASE_URL=postgresql://…    # état partagé (obligatoire en multi-instance)
REDIS_URL=redis://…            # bus d'événements partagé (Render « Key Value »)
```

Sans `REDIS_URL`, la diffusion est locale (une seule instance) — c'est le mode par défaut.
Le fan-out passe systématiquement par Redis (y compris pour l'instance émettrice), ce qui
garantit une diffusion **exactement une fois** par client, sans doublon. *(Alternative au
choix : un bus NATS ; l'abstraction `EventBus` de `app.py` se transpose directement.)*

## 9. Rétention et archivage de l'historique

La table `events` peut être élaguée automatiquement (côté cockpit) :

```bash
EVENT_RETENTION_DAYS=90                  # purge au-delà de 90 jours
EVENT_MAX_ROWS=500000                    # et/ou ne garder que N lignes
EVENT_ARCHIVE_PATH=/data/archive.jsonl   # archive JSONL avant suppression (volume durable)
MAINTENANCE_INTERVAL_HOURS=6             # période de la purge auto (défaut 6 h)
```

- Purge auto en tâche de fond ; en **multi-instance**, une seule instance purge à la fois
  (verrou consultatif). À la demande : `POST /api/maintenance/purge?max_rows=…&retention_days=…`
  (en-tête `X-Ingest-Token`).
- `EVENT_ARCHIVE_PATH` doit pointer un stockage **durable** (volume, pas le disque éphémère
  de Render). Pour une archive froide (S3…), planifier l'export du JSONL vers l'objet.

## 10. Supervision du connecteur (Prometheus / alerting)

Le connecteur expose des métriques avec `--metrics-port` (sur n'importe quelle sous-commande) :

```bash
python -m connectors.connector otplatform --preset nozomi --url … --metrics-port 9109
# -> /metrics (format Prometheus) et /healthz sur le port 9109
```

Scrape Prometheus :
```yaml
scrape_configs:
  - job_name: conseilprev-connector
    static_configs:
      - targets: ['collecteur.interne:9109']
```

Règles d'alerte (exemples) :
```yaml
groups:
  - name: conseilprev-connector
    rules:
      - alert: ConnecteurOTInjoignable
        expr: up{job="conseilprev-connector"} == 0
        for: 5m
        labels: { severity: critical }
        annotations: { summary: "Connecteur OT injoignable (scrape en échec)" }
      - alert: ConnecteurOTSansEnvoi
        expr: time() - conseilprev_connector_last_success_timestamp_seconds > 900
        for: 10m
        labels: { severity: warning }
        annotations: { summary: "Aucun événement envoyé depuis plus de 15 min" }
      - alert: ConnecteurOTEchecs
        expr: increase(conseilprev_connector_events_failed_total[15m]) > 0
        for: 5m
        labels: { severity: warning }
        annotations: { summary: "Échecs d'envoi vers le cockpit" }
```

Le service systemd peut ajouter `--metrics-port ${METRICS_PORT}` à `ExecStart` (voir
`connector.env.example`).
