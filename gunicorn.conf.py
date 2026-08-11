"""Réglage du serveur — la disponibilité tient ici, pas dans le code applicatif.

Ce qu'on cherche à éviter : que le site cesse de répondre À TOUT LE MONDE
parce que quelques requêtes lentes occupent tous les fils d'exécution. Une
rédaction assistée peut immobiliser un fil jusqu'à quatre-vingt-cinq
secondes ; le registre d'ingénierie porte quarante boutons « Rédiger », et
rien n'empêche d'en lancer plusieurs de suite.

TROIS DÉFENSES, et elles se complètent :

  · CE FICHIER élargit la capacité — plusieurs processus, plusieurs fils. Deux
    processus valent mieux qu'un pour une autre raison encore : si l'un meurt,
    l'autre sert pendant que le premier redémarre.

  · L'ASSISTANT borne les appels simultanés au modèle (LLM_MAX_SIMULTANE, trois
    par défaut) bien en dessous du nombre de fils. Sans cette borne, élargir la
    capacité ne ferait que déplacer le point de rupture : il resterait toujours
    un nombre de rédactions qui bloque tout.

  · LA RÉDACTION SE REPLIE sur l'assemblage — plan, grandeurs, extraits — qui
    ne dépend d'aucun service extérieur. Refusée faute de place, une pièce sort
    quand même.

Tout est réglable par variables d'environnement : ajuster la capacité ne doit
pas demander de toucher au code, ni de savoir le lire.
"""
import os


def _entier(nom, defaut, mini=1):
    try:
        return max(mini, int(os.environ.get(nom) or defaut))
    except (TypeError, ValueError):
        return defaut


# Fils par processus. Le travail est très majoritairement en ATTENTE (base,
# modèle, réseau) : des fils, pas des cœurs.
threads = _entier("WEB_THREADS", 16)

# Processus. Deux par défaut : la mémoire double, mais un incident dans l'un
# ne coupe plus le service. Ramener à 1 si l'instance est trop petite.
workers = _entier("WEB_WORKERS", 2)

worker_class = "gthread"

# Au-delà, gunicorn tue le fil. Doit rester AU-DESSUS du budget de l'assistant
# (85 s de génération + recherche documentaire), sans quoi c'est le serveur qui
# raccroche avant que le client ait sa réponse — et la cause affichée désigne
# alors le mauvais coupable.
timeout = _entier("WEB_TIMEOUT", 120)

# File d'attente des connexions en instance : un pic ne doit pas se traduire
# par des connexions refusées avant même d'être lues.
backlog = _entier("WEB_BACKLOG", 512)

# Un processus qui a beaucoup servi est recyclé — filet contre une fuite de
# mémoire lente, sans coupure visible. Le décalage aléatoire évite que tous les
# processus se recyclent au même instant.
# À 800, un processus se recyclait toutes les ~90 pages vues (~9 requêtes par
# page) : chaque recyclage ré-importe l'application, re-vérifie la politique
# d'accès et repart cache vide — relecture disque et gzip niveau 9 de chaque
# asset, à capacité réduite de moitié pendant ce temps. Le filet reste, dix
# fois plus lâche.
max_requests = _entier("WEB_MAX_REQUESTS", 8000)
max_requests_jitter = _entier("WEB_MAX_REQUESTS_JITTER", 1200, mini=0)

# Redémarrage propre : on laisse aux requêtes en cours le temps de finir.
graceful_timeout = _entier("WEB_GRACEFUL", 30)

# Connexions maintenues ouvertes entre deux requêtes : évite de refaire la
# poignée de main TLS à chaque appel d'API de la page.
keepalive = _entier("WEB_KEEPALIVE", 5)

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("WEB_LOGLEVEL") or "info"
