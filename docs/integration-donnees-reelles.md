# Brancher le cockpit à des données réelles — note de cadrage

> **Statut :** cadrage / avant-projet. Le cockpit `/demo` fonctionne par défaut avec des **données simulées**
> (aucune collecte réelle). Ce document décrit ce qu'il faudrait pour l'alimenter avec des données OT réelles.
>
> **Déjà en place (brique « API temps réel » du schéma ci-dessous) :** le cockpit sait basculer en mode
> **Temps réel** et s'abonner au flux **SSE `GET /api/stream`** ; un point d'ingestion **`POST /api/ingest`**
> (protégé par `INGEST_TOKEN`) permet à un connecteur d'y pousser des événements normalisés. Reste à
> construire les **connecteurs**, le **stockage** et l'**industrialisation** décrits ci-dessous.

## 1. Principe

Le cockpit actuel est une **vitrine** : le navigateur génère lui-même des événements. Pour afficher un
environnement réel, il faut ajouter trois briques entre le terrain et la page :

```
[ Terrain / OT ]  →  [ Collecte ]  →  [ Backend + stockage ]  →  [ API temps réel ]  →  [ Cockpit web ]
   automates,          sonde passive     normalisation,            WebSocket / SSE        (déjà en place,
   capteurs, IHM,      SPAN/TAP, agents  inventaire, alertes       /api/stream            à connecter)
   switches
```

Principe directeur OT : **priorité au passif**. On observe sans injecter de trafic sur les réseaux de
production ; toute sonde active est validée au cas par cas.

## 2. Sources de données possibles

| Source | Usage | Mode |
|--------|-------|------|
| Sonde passive OT (SPAN/TAP) | Discovery, inventaire, flux, anomalies | Passif ✅ |
| Plateformes OT (Nozomi, Claroty, Tenable.ot, Microsoft Defender for IoT) | Inventaire + détection déjà normalisés (API) | Passif ✅ |
| Syslog / SNMP (switches, firewalls) | Événements réseau, état des équipements | Passif ✅ |
| Firewalls NGFW | Journaux de flux, règles, conduits | Passif ✅ |
| SIEM / collecteur existant | Corrélation, alertes | Passif ✅ |
| Scan actif (Nmap, requêtes protocoles OT) | Complément d'inventaire | Actif ⚠️ (encadré) |

## 3. Composants à ajouter au projet

1. **Connecteurs d'ingestion** ✅ *implémentation de référence* (`connectors/`) — un module par source
   (CSV/export, syslog fichier + écoute UDP, plateforme OT via API REST), qui normalise vers le modèle
   commun `{asset, zone, type, event, severity, ts}` et poste sur `/api/ingest`. Sans dépendance (Python
   standard) ; un mock de plateforme OT (`connectors/mock_ot.py`) permet de tester de bout en bout.
2. **Stockage** ✅ *implémenté* — persistance PostgreSQL (activée par `DATABASE_URL`) : tables `events`
   (série temporelle horodatée, convertible en hypertable TimescaleDB), `assets` (inventaire),
   `zone_status`, `meta`. L'état survit aux redémarrages ; sans `DATABASE_URL`, repli en mémoire.
   Voir `cockpit_state.py`.
3. **API temps réel** ✅ *implémentée* — endpoint `GET /api/stream` en **SSE** (Server-Sent Events) poussant
   les nouveaux événements au cockpit (réponse `text/event-stream`, broker pub/sub en mémoire, keep-alive).
   Ingestion via `POST /api/ingest` (jeton `INGEST_TOKEN`). Nécessite un worker à threads
   (`gunicorn -k gthread`). Le broker mémoire est mono-instance : pour du multi-worker/multi-instance,
   remplacer par un bus partagé (Redis pub/sub, NATS…).
4. **Adaptation du cockpit** ✅ *implémentée* — `demo.html` propose un interrupteur **Démo ⇄ Temps réel**.
   En temps réel, la boucle `setInterval` est arrêtée et la page s'abonne au flux :

   ```js
   const es = new EventSource('/api/stream');
   es.onmessage = e => { const evt = JSON.parse(e.data); applyLive(evt); /* addEvent + maj KPI/zones */ };
   ```

   Le mode **Démo reste le mode par défaut** (repli si aucune donnée réelle n'est branchée).

## 4. Trajectoire proposée

| Phase | Objectif | Livrable |
|-------|----------|----------|
| **POC** (2-3 sem.) | 1 source (ex. export d'une plateforme OT), flux SSE, cockpit connecté en lecture seule | Démo sur données réelles anonymisées |
| **Pilote** (1 site) | Sonde passive + syslog, inventaire persistant, alertes | Cockpit pilote + tableau de bord d'inventaire |
| **Industrialisation** | Multi-sites, RBAC, rétention, supervision 24/7 | Service supervisé, procédures d'exploitation |

## 5. Sécurité & confidentialité de la collecte

- Collecte **passive** par défaut ; sondes actives validées explicitement.
- Flux de collecte **cloisonné** (zone de supervision dédiée, conduits maîtrisés — cohérent IEC 62443).
- Données sensibles (topologie, vulnérabilités) : chiffrement en transit et au repos, accès restreint (RBAC),
  hébergement à définir selon la sensibilité (le PoC public actuel est hébergé sur Render).
- Aucune donnée réelle ne doit transiter par la page de démonstration publique.

## 6. Impact sur le dépôt actuel

- `app.py` : ✅ endpoints `/api/stream` (SSE, avec instantané d'ouverture) + `/api/ingest` (jeton) +
  `/api/state` + `/api/reset` ; broker pub/sub + état courant (inventaire, alertes, événements récents).
  ✅ **authentification HTTP Basic** optionnelle (instance privée) via `COCKPIT_AUTH_USER/PASSWORD`.
- `cockpit_state.py` : ✅ état **persistant PostgreSQL** (`DATABASE_URL`) ou en mémoire (repli).
- `Procfile` / `render.yaml` : ✅ démarrage en worker à threads (`gunicorn -k gthread --threads 8`) requis par le SSE.
- `demo.html` : ✅ interrupteur Démo ⇄ Temps réel, abonnement `EventSource`, **mode démo** de repli conservé.
- `render.yaml` : ✅ variables `INGEST_TOKEN`, `DATABASE_URL`, `COCKPIT_AUTH_*` (sync:false) déclarées.
- `connectors/` : ✅ connecteurs de référence (CSV, syslog/CEF, plateforme OT avec presets éditeurs),
  durcis (TLS vérifié, validation, dédoublonnage borné, arrêt propre SIGTERM) + mock de test + kit de
  déploiement (`connectors/deploy/`).
- **Reste à faire** : remplacement du broker mémoire par un bus partagé (Redis/NATS) pour du
  **multi-instance** à haute disponibilité ; rétention/archivage de l'historique ; supervision du
  connecteur (métriques, alerting).

---

*Ce document est une base de discussion — les choix (sources, hébergement, outillage) se décident avec le
contexte réel du client.*
