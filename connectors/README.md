# Connecteurs d'ingestion — cockpit temps réel

Petits connecteurs qui alimentent le **mode Temps réel** du cockpit (`/demo`) en
postant des événements sur `POST /api/ingest`. Chaque source normalise ses données
vers le modèle commun :

```json
{ "asset": "Automate S7-1500", "zone": "Supervision (SCADA)",
  "type": "discovery", "event": "Nouvel actif inventorié",
  "severity": "info", "ts": 1712345678901 }
```

- `severity` : `critical` · `warning` · `info` (synonymes tolérés : high/medium/low, 0‑7…).
- `zone` : rattachée automatiquement aux 5 zones du cockpit (Entreprise (IT), DMZ
  industrielle, Supervision (SCADA), Cellule / Contrôle, Terrain (capteurs)) quand c'est possible.
- `type` : `discovery` / `patch` / `anomaly` / … (déduit du message si absent).
- `ts` : horodatage ms (ajouté si absent).

**Sans dépendance** : Python 3 standard uniquement (aucun `pip install`). Le connecteur
peut donc tourner sur un collecteur isolé.

## Configuration

| Variable / option | Rôle | Défaut |
|-------------------|------|--------|
| `--target` / `$COCKPIT_URL` | Base du cockpit | `http://127.0.0.1:5000` |
| `--token` / `$INGEST_TOKEN` | Jeton d'ingestion (en‑tête `X-Ingest-Token`) | — |
| `--dry-run` | Affiche les événements sans les envoyer | off |
| `--interval S` | Pause entre deux envois (visualisation temps réel) | 0 |

```bash
export COCKPIT_URL="https://conseilprevcyber.onrender.com"
export INGEST_TOKEN="votre-jeton"      # le même que dans Render
```

## 1. CSV / export

Lit un fichier CSV (colonnes `asset,zone,type,event,severity` — toutes optionnelles) :

```bash
python -m connectors.connector csv --file connectors/samples/events.csv --interval 1
```

Utile pour rejouer un export (inventaire, journal d'incidents) ou une liste d'actifs.

## 2. Syslog (fichier ou UDP)

Suivre un fichier syslog au fil de l'eau :

```bash
python -m connectors.connector syslog --file /var/log/syslog
```

Écouter directement les messages syslog en **UDP** (RFC 3164 / 5424) — pointez vos
switches / firewalls / IHM vers ce collecteur :

```bash
python -m connectors.connector syslog --listen 0.0.0.0:5514
```

La sévérité est déduite de la priorité `<PRI>` ; à défaut, des mots‑clés du message
(`denied`, `attack`, `scan`, `bloqué`…). Options `--zone` / `--asset` pour forcer.

## 3. Plateforme OT (API REST)

Interroge périodiquement l'API d'une plateforme OT/IDS (Nozomi, Claroty, Tenable.ot,
Microsoft Defender for IoT, un SIEM…) et poste les alertes. Le mapping est configurable :

```bash
python -m connectors.connector otplatform \
  --url https://plateforme.local/api/alerts \
  --header "Authorization: Bearer XXXX" \
  --alerts-path "result.alerts" \
  --map event=name --map asset=device --map zone=site --map severity=risk \
  --interval 10
```

- `--alerts-path` : chemin (pointé) vers la liste dans la réponse JSON.
- `--map champ=chemin` : associe un champ cible à une clé source (répétable).
- Dédoublonnage automatique sur `--id-field` (déf. `id`).
- Lecture seule (GET) — **mode passif**.

## Tester sans matériel (mock de plateforme OT)

Un serveur factice imite une plateforme OT (schéma type Nozomi/Claroty) :

```bash
# Terminal 1 — le site (mode threads requis par le SSE)
INGEST_TOKEN=demo gunicorn -k gthread --threads 8 app:app

# Terminal 2 — la fausse plateforme OT
python -m connectors.mock_ot --port 8899

# Terminal 3 — le connecteur qui la lit et alimente le cockpit
python -m connectors.connector otplatform \
  --url http://127.0.0.1:8899/api/alerts \
  --target http://127.0.0.1:8000 --token demo --interval 2
```

Ouvrez `/demo`, basculez sur **Temps réel** : les événements apparaissent en direct.

> Test rapide sans aucune source : `python -m connectors.connector demo --interval 1`.

## Sécurité

- Le jeton `INGEST_TOKEN` est un **secret** : passez‑le par variable d'environnement,
  jamais en clair dans un dépôt.
- Collecte **passive** par défaut (lecture d'API, écoute syslog) — cohérent IEC 62443.
- Ne faites transiter **aucune donnée réelle** par la démo publique : pour de vraies
  données, hébergez une instance privée (voir `docs/integration-donnees-reelles.md`).
