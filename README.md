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

## Structure

| Fichier | Rôle |
|---------|------|
| `app.py` | Application Flask (page d'accueil + `/health`) |
| `index.html` | Page d'accueil (statique, autonome) |
| `requirements.txt` | Dépendances Python |
| `Procfile` | Commande de démarrage (`gunicorn app:app`) |
| `runtime.txt` | Version de Python |
| `render.yaml` | Blueprint de déploiement Render |

## Déploiement Render

1. Connecter ce dépôt à Render (dashboard → New → Blueprint).
2. Render lit `render.yaml`, construit et déploie automatiquement.
3. Chaque push sur `main` déclenche un redéploiement.

Point de santé exposé : `GET /health` → `{"status":"ok"}`.
