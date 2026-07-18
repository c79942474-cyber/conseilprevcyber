# CONSEILPREV Cyber

Application web (Flask) — point de départ pour le projet **CONSEILPREV Cyber**, prête à déployer sur [Render](https://render.com).

## Stack

- **Python 3.11** · **Flask** · **Gunicorn**
- Déploiement : Render (Blueprint `render.yaml`)

## Développement local

```bash
pip install -r requirements.txt
python app.py
# → http://localhost:5000
```

## Pages

| Route | Fichier | Contenu |
|-------|---------|---------|
| `/` | `index.html` | Accueil (positionnement IT/OT/IIoT, domaines, approche) |
| `/services` | `services.html` | Objectifs, livrables et compétences (IEC 62443…) |
| `/etudes-de-cas` | `etudes-de-cas.html` | Références & missions (EDF, Renault, Atos/SGP, Alstom, GRDF, TechnipEnergies) |
| `/referentiel` | `referentiel.html` | Sommaire de la série IEC 62443 (hub vers les modules) |
| `/analyse-de-risque` | `analyse-de-risque.html` | 62443‑3‑2 : analyse de risque, zones & conduits, SL‑T, CRS (déroulé ZCR 1→7) |
| `/secteurs` | `secteurs.html` | Secteurs (énergie, eau, manufacturing, agro, chimie-pharma, logistique) |
| `/methodologie` | `methodologie.html` | Démarche en 6 phases + concepts IEC 62443‑1‑1 (FR, SL, défense en profondeur) |
| `/exigences-systeme` | `exigences-systeme.html` | 62443‑3‑3 : 7 FR, 51 exigences système (SR), niveaux SL 1‑4 |
| `/exigences-composants` | `exigences-composants.html` | 62443‑4‑2 : exigences composant (CR) par type SAR/EDR/HDR/NDR |
| `/exigences-prestataires` | `exigences-prestataires.html` | 62443‑2‑4 : programme des prestataires IACS, maturité CMMI‑SVC, profils |
| `/developpement-securise` | `developpement-securise.html` | 62443‑4‑1 : cycle de développement sécurisé (8 pratiques SDL), maturité CMMI‑DEV |
| `/technologies-securite` | `technologies-securite.html` | TR 62443‑3‑1 : panorama des technologies de sécurité IACS (6 familles) |
| `/programme-securite` | `programme-securite.html` | 62443‑2‑1 : programme de sécurité / CSMS (3 catégories, 19 éléments) |
| `/gestion-correctifs` | `gestion-correctifs.html` | Module patch management selon IEC 62443‑2‑3 (rôles, modèle d'états, mitigations) |
| `/glossaire-62443` | `glossaire-62443.html` | 62443‑1‑2 : glossaire de la série (17 termes reformulés) |
| `/metriques-62443` | `metriques-62443.html` | 62443‑1‑3 : métriques de conformité (méthodologie, 6 principes) |
| `/demo` | `demo.html` | Cockpit OT : mode **Démo** (données simulées) ⇄ mode **Temps réel** (flux SSE) — KPI, journal, zones, carte réseau, export PDF |
| `/ressources` | `ressources.html` | Ressources & références (ANSSI, CERT‑FR, ENISA, CISA, IEC, ISO, NIST, NIS2, DORA…) |
| `/faq` | `faq.html` | Questions fréquentes (OT/IACS, 62443, NIS2, zones & conduits, correctifs…) |
| `/about` | `about.html` | À propos (mission, engagements) |
| `/contact` | `contact.html` | Formulaire + coordonnées |
| `/mentions-legales` | `mentions-legales.html` | Mentions légales (société CONSEILPREV, hébergement Render Francfort) |
| `/api/contact` | — | POST — envoi du formulaire via Brevo |
| `/api/stream` | — | GET — flux Server‑Sent Events du cockpit temps réel |
| `/api/ingest` | — | POST — ingestion d'un événement OT (protégé par `INGEST_TOKEN`) |
| `/health` | — | Point de santé JSON |

## Structure

| Fichier | Rôle |
|---------|------|
| `app.py` | Application Flask (routes des pages, envoi email, flux SSE `/api/stream` + `/api/ingest`, `/health`) |
| `*.html` | Pages du site (accueil, services, études de cas, référentiel 62443 et ses modules, démo, ressources, FAQ, à propos, contact, mentions légales) |
| `styles.css` | Feuille de style partagée (thème cyber) |
| `requirements.txt` | Dépendances Python (Flask, Gunicorn, Requests) |
| `Procfile` | Commande de démarrage (`gunicorn app:app`) |
| `runtime.txt` | Version de Python |
| `render.yaml` | Blueprint de déploiement Render |

## Formulaire de contact (email via Brevo)

Le formulaire poste sur `POST /api/contact`, qui envoie un email via l'API transactionnelle
[Brevo](https://www.brevo.com). Configuration :

1. Créer une **clé API** dans Brevo (*SMTP & API → API Keys*).
2. La renseigner dans Render comme variable d'environnement **`BREVO_API_KEY`**
   (déjà déclarée dans `render.yaml` avec `sync:false`).
3. L'expéditeur utilisé est l'expéditeur **vérifié** `CONSEILPREV <christophe.cerf@i-aes.com>` ;
   les messages arrivent sur `christophe.cerf@outlook.com` (visiteur en `reply-to`).

> Tant que `BREVO_API_KEY` n'est pas définie, le formulaire **bascule automatiquement** sur un lien
> `mailto` côté client — le site reste fonctionnel.

## Cockpit de supervision OT (`/demo`)

Le cockpit propose deux modes, commutables par l'interrupteur en haut du tableau de bord :

- **Démo** (par défaut) : le navigateur génère des événements **simulés** (aucune donnée réelle).
- **Temps réel** : la page s'abonne au flux **SSE** `GET /api/stream` et affiche les événements poussés
  par les connecteurs d'ingestion.

Pour alimenter le mode temps réel, un connecteur poste des événements normalisés sur `POST /api/ingest` :

```bash
curl -X POST https://conseilprevcyber.onrender.com/api/ingest \
  -H "content-type: application/json" -H "X-Ingest-Token: $INGEST_TOKEN" \
  -d '{"asset":"Automate S7-1500","zone":"Supervision (SCADA)","type":"discovery","event":"Nouvel actif inventorié","severity":"info"}'
```

- L'ingestion est **protégée** par la variable `INGEST_TOKEN` (en‑tête `X-Ingest-Token`). Sans jeton
  configuré, `/api/ingest` renvoie `503` et le cockpit reste en mode démo.
- Le flux SSE exige un worker **multi‑thread** : le démarrage utilise `gunicorn -k gthread --threads 8`
  (voir `Procfile` / `render.yaml`). Le broker pub/sub est **en mémoire** (mono‑instance, sans persistance) —
  suffisant pour une démo / un pilote. Le cadrage complet (sources, stockage, industrialisation) est dans
  [`docs/integration-donnees-reelles.md`](docs/integration-donnees-reelles.md).

> Aucune donnée réelle ne doit transiter par la page de démonstration publique — voir la note de cadrage.

## Déploiement Render

1. Connecter ce dépôt à Render (dashboard → New → Blueprint).
2. Render lit `render.yaml`, construit et déploie automatiquement.
3. Chaque push sur `main` déclenche un redéploiement.

Point de santé exposé : `GET /health` → `{"status":"ok"}`.
