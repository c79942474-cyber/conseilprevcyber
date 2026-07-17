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
| `/` | `index.html` | Accueil (hero, domaines d'intervention, approche) |
| `/services` | `services.html` | Détail des prestations |
| `/contact` | `contact.html` | Formulaire (via `mailto`) + coordonnées |
| `/mentions-legales` | `mentions-legales.html` | Mentions légales (⚠️ champs `[À COMPLÉTER]`) |
| `/health` | — | Point de santé JSON |

## Structure

| Fichier | Rôle |
|---------|------|
| `app.py` | Application Flask (routes des pages + `/health`) |
| `index.html`, `services.html`, `contact.html`, `mentions-legales.html` | Pages du site |
| `styles.css` | Feuille de style partagée (thème cyber) |
| `requirements.txt` | Dépendances Python |
| `Procfile` | Commande de démarrage (`gunicorn app:app`) |
| `runtime.txt` | Version de Python |
| `render.yaml` | Blueprint de déploiement Render |

> **À faire avant mise en ligne** : compléter les champs `[À COMPLÉTER]` de `mentions-legales.html`
> (éditeur, SIRET, directeur de publication, adresse de l'hébergeur).

## Déploiement Render

1. Connecter ce dépôt à Render (dashboard → New → Blueprint).
2. Render lit `render.yaml`, construit et déploie automatiquement.
3. Chaque push sur `main` déclenche un redéploiement.

Point de santé exposé : `GET /health` → `{"status":"ok"}`.
