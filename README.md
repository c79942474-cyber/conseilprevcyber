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
| `/referentiel` | `referentiel.html` | Sommaire de la série IEC 62443 (hub vers les 5 modules) |
| `/secteurs` | `secteurs.html` | Secteurs (énergie, eau, manufacturing, agro, chimie-pharma, logistique) |
| `/methodologie` | `methodologie.html` | Démarche en 6 phases + concepts IEC 62443‑1‑1 (FR, SL, défense en profondeur) |
| `/exigences-systeme` | `exigences-systeme.html` | 62443‑3‑3 : 7 FR, 51 exigences système (SR), niveaux SL 1‑4 |
| `/exigences-composants` | `exigences-composants.html` | 62443‑4‑2 : exigences composant (CR) par type SAR/EDR/HDR/NDR |
| `/exigences-prestataires` | `exigences-prestataires.html` | 62443‑2‑4 : programme des prestataires IACS, maturité CMMI‑SVC, profils |
| `/developpement-securise` | `developpement-securise.html` | 62443‑4‑1 : cycle de développement sécurisé (8 pratiques SDL), maturité CMMI‑DEV |
| `/programme-securite` | `programme-securite.html` | 62443‑2‑1 : programme de sécurité / CSMS (3 catégories, 19 éléments) |
| `/gestion-correctifs` | `gestion-correctifs.html` | Module patch management selon IEC 62443‑2‑3 (rôles, modèle d'états, mitigations) |
| `/demo` | `demo.html` | Cockpit OT **temps réel** : KPI, journal, zones, carte réseau, export PDF (démo, données simulées) |
| `/about` | `about.html` | À propos (mission, engagements) |
| `/contact` | `contact.html` | Formulaire + coordonnées |
| `/mentions-legales` | `mentions-legales.html` | Mentions légales (⚠️ champs `[À COMPLÉTER]`) |
| `/api/contact` | — | POST — envoi du formulaire via Brevo |
| `/health` | — | Point de santé JSON |

## Structure

| Fichier | Rôle |
|---------|------|
| `app.py` | Application Flask (routes des pages, envoi email, `/health`) |
| `index.html`, `services.html`, `about.html`, `contact.html`, `mentions-legales.html` | Pages du site |
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

> **À compléter avant mise en ligne** : les champs `[À COMPLÉTER]` de `mentions-legales.html`
> (éditeur, SIRET, directeur de publication, adresse de l'hébergeur) et le bloc personnalisable de `about.html`.

## Déploiement Render

1. Connecter ce dépôt à Render (dashboard → New → Blueprint).
2. Render lit `render.yaml`, construit et déploie automatiquement.
3. Chaque push sur `main` déclenche un redéploiement.

Point de santé exposé : `GET /health` → `{"status":"ok"}`.
