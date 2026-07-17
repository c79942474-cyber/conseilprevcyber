# Brancher le cockpit à des données réelles — note de cadrage

> **Statut :** cadrage / avant-projet. Le cockpit `/demo` actuel fonctionne avec des **données simulées**
> (aucune collecte réelle). Ce document décrit ce qu'il faudrait pour l'alimenter avec des données OT réelles.

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

1. **Connecteurs d'ingestion** — un module par source (webhook, API pull, écoute syslog), qui normalise
   vers un modèle commun `{asset, zone, type, event, severity, ts}`.
2. **Stockage** — une base (PostgreSQL / série temporelle) pour l'inventaire et l'historique des événements.
3. **API temps réel** — un endpoint `GET /api/stream` en **SSE** (Server-Sent Events) ou WebSocket poussant
   les nouveaux événements au cockpit. Flask supporte le SSE via une réponse `text/event-stream`.
4. **Adaptation du cockpit** — remplacer la boucle `setInterval` de `demo.html` par un abonnement au flux :

   ```js
   const es = new EventSource('/api/stream');
   es.onmessage = e => { const evt = JSON.parse(e.data); addEvent(evt.tag, evt.txt); /* maj KPI/zones */ };
   ```

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

- `app.py` : ajouter le blueprint d'ingestion + l'endpoint `/api/stream` (SSE).
- `requirements.txt` : ajouter la base (`psycopg[binary]`) et, si WebSocket, `flask-sock`.
- `demo.html` : basculer la simulation vers l'abonnement au flux (garder un **mode démo** de repli).
- Nouveau : dossier `connectors/` (un module par source) + schéma de base de données.

---

*Ce document est une base de discussion — les choix (sources, hébergement, outillage) se décident avec le
contexte réel du client.*
