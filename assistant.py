"""Assistant conversationnel CONSEILPREV Cyber — Claude (Anthropic) & Mistral.

Chat sécurisé, transparent (AI Act) et respectueux du RGPD :
  - aucune conversation n'est stockée côté serveur (minimisation des données) ;
  - les API Anthropic et Mistral n'utilisent pas les entrées pour l'entraînement ;
  - transmission chiffrée (HTTPS), limitation de débit et contrôle d'origine (app.py) ;
  - périmètre limité : cybersécurité industrielle IT/OT/IIoT et conformité
    (IEC 62443, NIS2, DORA, RGPD, AI Act).

Dégradation propre : si une clé d'API n'est pas configurée (ANTHROPIC_API_KEY /
MISTRAL_API_KEY), le modèle correspondant est signalé « non configuré » sans
faire planter l'application.
"""
import contextlib
import json
import logging
import os
import re
import threading

# Journalisation : uniquement des métadonnées techniques (codes HTTP, types
# d'erreur). Jamais de clé d'API ni de contenu de conversation (minimisation RGPD).
_log = logging.getLogger("assistant")

# --- Périmètre et posture de l'assistant (prompt système partagé) -------------
SYSTEM_PROMPT = (
    "Tu es « l'Assistant CONSEILPREV Cyber », un assistant IA spécialisé en "
    "cybersécurité industrielle (IT / OT / IIoT) et en conformité selon la série "
    "de normes IEC 62443, ainsi que les cadres NIS2, DORA, RGPD et le Règlement "
    "européen sur l'IA (AI Act).\n\n"
    "Périmètre :\n"
    "- Aider visiteurs et clients à comprendre la sécurité des systèmes industriels "
    "(automates/PLC, SCADA, DCS, capteurs, IIoT), la démarche IEC 62443 (zones & "
    "conduits, niveaux de sécurité SL, exigences fondamentales FR), l'analyse de "
    "risque, la segmentation, la supervision et la mise en conformité.\n"
    "- Orienter vers les services et ressources de CONSEILPREV Cyber : état des lieux, "
    "audit de conformité IEC 62443 (/audit-conformite), architecture & segmentation, "
    "supervision temps réel (/demo), remédiation, contact (/contact).\n"
    "- Rester STRICTEMENT dans ce périmètre. Pour toute question sans lien avec la "
    "cybersécurité industrielle ou la conformité, décline poliment et propose de recentrer.\n\n"
    "Règles :\n"
    "- Transparence : tu es une IA, pas un conseiller humain ; tes réponses ne "
    "constituent ni un audit, ni un avis juridique. Dis-le si on te le demande.\n"
    "- Tu es un assistant DÉFENSIF : n'aide jamais à des activités offensives "
    "(maliciel, exploitation, contournement de protections).\n"
    "- Ne demande jamais de données personnelles ou confidentielles ; si l'utilisateur "
    "en fournit, invite-le à ne pas le faire.\n"
    "- N'invente pas de faits, de chiffres ni de références. Reformule les normes "
    "(ne reproduis pas le texte normatif mot pour mot). En cas d'incertitude, dis-le "
    "et propose de contacter l'équipe.\n"
    "- Réponds en français par défaut (ou dans la langue de l'utilisateur), de façon "
    "directe, concise et structurée : donne directement la réponse utile.\n"
    # Cette ligne remplace un « ne dévoile pas ton raisonnement interne ». Une
    # consigne de cette forme-là — défendre au modèle de réfléchir, ou de le
    # montrer — fait FUIR le balisage interne dans la réponse au lieu de l'y
    # retenir. La consigne efficace est générique : on nomme ce qu'on ne veut
    # pas voir (des balises), pas ce qu'on interdit de faire (penser).
    "- N'inclus dans ta réponse aucune balise XML interne ou système.\n"
    "- Format : écris en texte clair et sobre, SANS Markdown — n'emploie ni « # » (titres), "
    "ni « * » ou « ** » (gras/italique), ni backticks. Pour une énumération, un simple "
    "tiret « - » en début de ligne. Privilégie des phrases courtes et des paragraphes aérés.\n"
    "- Quand c'est pertinent, termine par une piste d'action concrète (lancer un état "
    "des lieux, ouvrir l'audit de conformité, nous contacter)."
)

CLAUDE_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")
MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-large-latest")
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# ── QUEL FOURNISSEUR QUAND PERSONNE N'EN CHOISIT UN ──────────────────────────
# Claude d'abord. C'est le réglage du site, et il se lit ici plutôt que de se
# deviner à quatre endroits : jusqu'ici la veille, le rapport hebdomadaire et
# la qualification des demandes entrantes portaient « mistral » ÉCRIT EN DUR,
# et se taisaient donc sur un serveur où seul l'autre fournisseur a une clé.
# Un travail de fond qui renonce sans rien dire ne se remarque pas ; on ne
# voit que le résultat manquant, des semaines plus tard.
MODELES = ("claude", "mistral")

MAX_MSG_CHARS = 2000       # longueur maximale d'un message utilisateur
MAX_HISTORY = 12           # nombre de messages de contexte conservés
MAX_OUTPUT_TOKENS = 900    # réponse concise (bien en deçà des délais/coûts)

# Délais d'attente, dimensionnés par USAGE plutôt qu'une valeur unique pour tout.
# Un délai de 30 s convenait au chat (900 jetons) mais coupait la génération d'un
# livrable (3000 jetons, plusieurs dizaines de secondes) : le fournisseur était
# pourtant parfaitement joignable — l'application raccrochait avant la fin de la
# rédaction, en affichant « service momentanément injoignable », message qui
# désignait la mauvaise cause. Claude y échappait par accident : son SDK applique
# 600 s par défaut, là où requests n'applique aucun délai sans consigne explicite.
#
# Le budget total doit tenir sous le --timeout 120 de gunicorn (voir Procfile),
# faute de quoi c'est le worker entier qui est tué : recherche RAG (quelques
# secondes) + re-classement + génération ≈ 110 s au pire.
CONNECT_TIMEOUT = 10       # établissement de la connexion : un hôte réellement
                           # injoignable doit échouer vite
REQUEST_TIMEOUT = 30       # chat : réponse courte
RERANK_TIMEOUT = 20        # LLM-juge : sortie minuscule (une liste de numéros)
GEN_TIMEOUT = 85           # génération d'un livrable : document long


class AssistantError(Exception):
    """Erreur d'assistant portant un code interne + un statut HTTP."""

    def __init__(self, code, status=502):
        super().__init__(code)
        self.code = code
        self.status = status


# ── COMBIEN D'APPELS AU MODÈLE EN MÊME TEMPS ─────────────────────────────────
# LA contrainte de disponibilité du site, et elle ne se voit pas dans le code
# de l'assistant : le serveur tourne avec un nombre FINI de fils d'exécution
# (voir Procfile), et un appel au modèle en immobilise un jusqu'à quatre-vingt-
# cinq secondes. Huit rédactions lancées coup sur coup — ce que le registre
# invite à faire, il porte quarante boutons — et il ne reste plus un seul fil
# pour SERVIR LES PAGES. Le site entier se fige, pour tout le monde, à cause
# d'un service tiers lent.
#
# On borne donc les appels simultanés bien en dessous du nombre de fils. Au-
# delà, l'appel est refusé IMMÉDIATEMENT, avec le code « sature » : la
# rédaction retombe alors sur l'assemblage — plan, grandeurs, extraits — qui ne
# dépend d'aucun service extérieur. Personne n'attend, personne ne repart les
# mains vides, et il reste toujours des fils pour les pages.
#
# Réglable sans redéploiement de code par LLM_MAX_SIMULTANE.
try:
    MAX_SIMULTANE = max(1, int(os.environ.get("LLM_MAX_SIMULTANE") or 3))
except (TypeError, ValueError):
    MAX_SIMULTANE = 3
_PLACES = threading.BoundedSemaphore(MAX_SIMULTANE)


@contextlib.contextmanager
def _une_place():
    """Réserve une place d'appel, ou refuse tout de suite.

    Sans attente : faire patienter reviendrait à immobiliser le fil qu'on
    cherche justement à libérer."""
    if not _PLACES.acquire(blocking=False):
        _log.warning("assistant : %d appels déjà en cours — refus immédiat "
                     "pour garder des fils disponibles", MAX_SIMULTANE)
        raise AssistantError("sature", 503)
    try:
        yield
    finally:
        _PLACES.release()


def available():
    """Modèles réellement configurés (clé d'API présente)."""
    claude = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if claude:
        try:
            import anthropic  # noqa: F401
        except ImportError:
            claude = False
    return {"claude": claude, "mistral": bool(os.environ.get("MISTRAL_API_KEY"))}


def preference():
    """Le fournisseur mis en avant dans les interfaces.

    Une PRÉFÉRENCE, pas une disponibilité : elle dit lequel présenter d'abord,
    et l'interface se charge d'annoncer « non configuré » le cas échéant.
    Surcharge par ASSISTANT_DEFAULT_MODEL, sans redéploiement.
    """
    v = (os.environ.get("ASSISTANT_DEFAULT_MODEL") or MODELES[0]).strip().lower()
    return v if v in MODELES else MODELES[0]


def defaut():
    """Le fournisseur employé quand l'appelant n'en choisit aucun. None si aucun
    n'est configuré.

    La préférence d'abord, la disponibilité ensuite — et pas l'inverse. Un
    appel de fond n'a personne devant lui pour corriger le tir : si on lui
    imposait la préférence même sans clé, il échouerait à chaque fois, en
    silence, alors qu'un fournisseur configuré attendait juste à côté.
    """
    dispo = available()
    prefere = preference()
    for m in (prefere,) + tuple(x for x in MODELES if x != prefere):
        if dispo.get(m):
            return m
    return None


def _clean_history(messages):
    """Ne garde que des tours user/assistant non vides, bornés, commençant ET
    finissant par user."""
    out = []
    for m in messages or []:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            out.append({"role": role, "content": content[:MAX_MSG_CHARS]})
    out = out[-MAX_HISTORY:]
    while out and out[0]["role"] != "user":
        out.pop(0)
    # ── ET ELLE FINIT SUR L'UTILISATEUR ───────────────────────────────────
    # L'historique arrive du navigateur : c'est une entrée que nous ne
    # maîtrisons pas. Terminée sur un tour d'assistant, elle ne demande plus
    # une réponse — elle demande de CONTINUER la phrase déjà commencée. Les
    # générations récentes de modèles la refusent d'emblée, par un HTTP 400
    # que rien ne distingue ensuite d'une panne du fournisseur ; celles qui
    # l'acceptent rallongent le tour précédent au lieu de répondre à la
    # question. Aucun des deux n'est ce qu'on veut, dans aucun cas.
    while out and out[-1]["role"] != "user":
        out.pop()
    return out


_FALLBACK = "Désolé, je n'ai pas pu formuler de réponse. Pouvez-vous reformuler votre question ?"


_GROUNDING = (
    "\n\nAncrage sur la base de connaissance (IMPORTANT) :\n"
    "- Fonde ta réponse en PRIORITÉ sur les extraits ci-dessus. Lorsque tu utilises "
    "un extrait, cite sa source entre crochets, par exemple [Titre — Thème].\n"
    "- Si les extraits ne couvrent pas la question, dis-le clairement (« La base de "
    "connaissance ne contient pas d'élément précis sur ce point ») et distingue "
    "nettement ce qui provient de la base de ce qui relève de connaissances générales "
    "à faire valider.\n"
    "- N'invente jamais de source, de chiffre ni de citation normative."
)


def _system(context):
    """Prompt système, augmenté du contexte RAG + des règles d'ancrage/citation
    (fiabilité : citer les sources, signaler les lacunes plutôt qu'inventer)."""
    if context:
        return SYSTEM_PROMPT + "\n\n" + context + _GROUNDING
    return SYSTEM_PROMPT


# ── UNE RÉPONSE DIRECTE, DEMANDÉE À CHAQUE APPEL ────────────────────────────
# max_tokens ne plafonne pas la réponse : il plafonne le RAISONNEMENT PRÉALABLE
# PLUS la réponse. Nos budgets sont taillés au plus juste sur le texte attendu
# — neuf cents jetons pour une réponse de chat, trois mille pour un livrable —
# et sur le --timeout 120 de gunicorn, qui ne laisse pas de marge.
#
# Or le raisonnement étendu s'active de lui-même, sans qu'on le demande, sur
# les générations récentes de modèles ; il n'était pas actif sur les
# précédentes. Un budget dimensionné pour du texte se retrouve alors mangé par
# le raisonnement, et ce qui revient est un texte COUPÉ EN PLEIN MILIEU : pas
# d'erreur, pas de trace, rien qui le distingue d'une réponse simplement
# courte. Un livrable amputé de sa moitié part au dossier comme les autres.
#
# On ne s'en remet donc pas au défaut du modèle — il a déjà changé une fois, il
# rechangera. On demande une réponse directe à chaque appel. C'est aussi ce qui
# rend ANTHROPIC_MODEL sûr à changer sans relire ce fichier.
_REPONSE_DIRECTE = {"type": "disabled"}

# … MAIS TOUS LES MODÈLES NE L'ACCEPTENT PAS, et c'est un fait d'exécution, pas
# de documentation : certaines gammes refusent la consigne par un HTTP 400, quel
# que soit le reste de la requête. Un réglage qu'on croit protecteur devient
# alors le seul motif d'échec — l'assistant ne répond plus DU TOUT, et l'écran
# n'affiche qu'« une erreur ».
#
# On ne pariait donc plus : on demande, et si le modèle refuse, on s'en remet à
# ses réglages par défaut pour la suite de la vie du processus. Le budget de
# jetons est alors relevé, parce que sans notre consigne le raisonnement le
# partage avec le texte — c'est exactement ce que la consigne évitait.
_CONSIGNE_REFUSEE = False
_MARGE_RAISONNEMENT = 3    # de quoi loger le raisonnement EN PLUS du texte
_PLAFOND_JETONS = 12000    # borne dure : au-delà, c'est le délai qui casse


# TOUS LES 400 NE SE VALENT PAS, et confondre deux causes sous un même code
# coûte cher. Le fournisseur répond « 400 » aussi bien quand la REQUÊTE est
# fautive que quand le COMPTE n'a plus de crédit. Or les deux appellent des
# gestes opposés : la première se corrige dans le code, la seconde chez le
# fournisseur, et rien de ce qu'on enverra n'y changera quoi que ce soit.
#
# Sans cette distinction, un compte à sec passait pour un modèle qui refuse nos
# réglages : on retirait le garde-fou pour rien, on le laissait retiré jusqu'au
# redémarrage — donc encore après le rechargement du compte — et on écrivait au
# journal une cause fausse.
_SOLDE_EPUISE = re.compile(r"credit balance|plans\s*&\s*billing|"
                           r"insufficient\s+credit", re.I)


def _est_solde(msg):
    """Le 400 vient-il du compte plutôt que de la requête ?"""
    return bool(_SOLDE_EPUISE.search(msg or ""))


def _detail_api(exc):
    """Ce que le fournisseur a RÉELLEMENT répondu : (type, message).

    Sans cela, la journalisation ne portait que le code HTTP — et un 400 dit
    précisément quel champ il refuse. On jetait la seule phrase qui désigne la
    cause. Aucun secret : ni clé, ni contenu de conversation.
    """
    corps, genre = getattr(exc, "body", None), ""
    if isinstance(corps, dict) and isinstance(corps.get("error"), dict):
        genre = corps["error"].get("type") or ""
    msg = (getattr(exc, "message", "") or "").strip().replace("\n", " ")
    return genre, msg[:300]


def _envoi_claude(client, system, messages, max_tokens, timeout):
    """Envoie la requête — et retombe sur les réglages du modèle s'il refuse les
    nôtres. Renvoie la réponse du SDK, laisse remonter ses exceptions."""
    global _CONSIGNE_REFUSEE
    import anthropic

    def _tenter(direct):
        kw = {"model": CLAUDE_MODEL, "messages": messages, "timeout": timeout,
              "max_tokens": max_tokens if direct
              else min(max_tokens * _MARGE_RAISONNEMENT, _PLAFOND_JETONS)}
        if system:
            kw["system"] = system
        if direct:
            kw["thinking"] = _REPONSE_DIRECTE
        # La place est prise AUTOUR de l'appel réseau, et de lui seul : c'est
        # lui qui immobilise le fil d'exécution, pas la construction du client.
        with _une_place():
            return client.messages.create(**kw)

    if _CONSIGNE_REFUSEE:
        return _tenter(False)
    try:
        return _tenter(True)
    except anthropic.APIStatusError as exc:
        # 400 SEULEMENT. Une clé refusée, un quota, une panne : ce n'est pas la
        # consigne qui est en cause, et réessayer masquerait la vraie cause.
        if getattr(exc, "status_code", None) != 400:
            raise
        genre, msg = _detail_api(exc)
        # Le compte, pas la requête : le second envoi échouerait à l'identique,
        # et retirer le garde-fou sur ce motif-là le laisserait retiré même une
        # fois le compte rechargé.
        if _est_solde(msg):
            raise
        _log.error("Claude : le modèle « %s » refuse la consigne de réponse "
                   "directe (HTTP 400, type=%s) : %s — on s'en remet à ses "
                   "réglages par défaut, budget de jetons relevé en conséquence.",
                   CLAUDE_MODEL, genre or "?", msg or "(sans message)")
        _CONSIGNE_REFUSEE = True
        return _tenter(False)

# Le revers de la consigne précédente : privé de sa phase de raisonnement, le
# modèle écrit parfois son brouillon dans la réponse, entre des balises
# internes. Le prompt système le lui déconseille (voir SYSTEM_PROMPT) ; ceci
# rattrape le cas où il le fait quand même, plutôt que de le laisser arriver
# jusqu'au lecteur. On retire le bloc ENTIER, pas seulement les balises :
# n'ôter que le marquage laisserait le brouillon lisible en tête de réponse.
_BLOC_INTERNE = re.compile(
    r"<\s*(antml:thinking|thinking)\b[^>]*>.*?<\s*/\s*\1\s*>", re.S | re.I)
_BALISE_INTERNE = re.compile(r"<\s*/?\s*(?:antml:thinking|thinking)\b[^>]*>", re.I)


def _sans_balise_interne(txt):
    """Retire un éventuel brouillon balisé. Sans effet sur un texte normal."""
    return _BALISE_INTERNE.sub("", _BLOC_INTERNE.sub("", txt or "")).strip()


def _claude_call(system, messages, max_tokens, timeout=REQUEST_TIMEOUT):
    """Appel bas niveau à Claude (Anthropic). Renvoie le texte (peut être vide).

    `timeout` explicite : sans lui le SDK applique 600 s, bien au-delà du
    --timeout 120 de gunicorn — le worker serait tué avant que le client n'ait
    la moindre réponse."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise AssistantError("not_configured", 503)
    try:
        import anthropic
    except ImportError:
        raise AssistantError("not_configured", 503)
    client = anthropic.Anthropic()  # lit ANTHROPIC_API_KEY dans l'environnement
    try:
        resp = _envoi_claude(client, system, messages, max_tokens, timeout)
    except anthropic.APITimeoutError:
        # À placer AVANT APIConnectionError, dont il hérite.
        _log.warning("Claude : délai dépassé (%s s, %s jetons demandés)", timeout, max_tokens)
        raise AssistantError("timeout", 504)
    except anthropic.APIConnectionError as exc:
        _log.warning("Claude : connexion impossible (%s)", type(exc).__name__)
        raise AssistantError("network", 502)
    except anthropic.RateLimitError:
        raise AssistantError("busy", 429)
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
        # Clé absente/erronée ou non autorisée. On journalise le code HTTP, jamais la clé.
        _log.error("Claude : authentification refusée (HTTP %s). Vérifier "
                   "ANTHROPIC_API_KEY (valeur exacte, sans espace ni guillemet).",
                   getattr(exc, "status_code", "?"))
        raise AssistantError("auth", 502)
    except anthropic.APIStatusError as exc:
        # LE MESSAGE DU FOURNISSEUR, pas seulement son code. « type » n'existe
        # pas sur cette exception — l'ancienne journalisation écrivait donc
        # « type=None » à chaque fois, et la seule phrase qui désigne le champ
        # refusé partait à la poubelle.
        genre, msg = _detail_api(exc)
        if _est_solde(msg):
            # Une cause à part entière : rien n'est cassé, le compte est à sec.
            # La ranger sous « erreur amont » enverrait chercher une panne
            # là où il n'y a qu'une ligne de facturation à régler.
            _log.error("Claude : le compte Anthropic n'a plus de crédit — "
                       "aucun appel n'aboutira tant qu'il n'est pas rechargé "
                       "(console Anthropic, Plans & Billing). Message : %s", msg)
            raise AssistantError("credit", 503)
        _log.error("Claude : réponse en erreur (HTTP %s, type=%s, modèle=%s) : %s",
                   getattr(exc, "status_code", "?"), genre or "?", CLAUDE_MODEL,
                   msg or "(sans message)")
        raise AssistantError("upstream", 502)
    # ── CE QUE DIT LA FIN DE LA RÉPONSE ───────────────────────────────────
    # Un refus du modèle n'est pas une erreur HTTP : la requête réussit, et le
    # contenu revient vide. Sans ce contrôle, cette réponse-là traversait tout
    # l'appel sans jamais être distinguée d'un silence, et la pièce partait
    # VIDE au dossier — enregistrée, numérotée, exportable. Traitée comme un
    # échec amont, elle bascule au contraire sur l'assemblage, qui rend un
    # document réel : plan, grandeurs, extraits.
    fin = getattr(resp, "stop_reason", None)
    if fin == "refusal":
        _log.error("Claude : demande déclinée par le modèle (stop_reason=refusal)")
        raise AssistantError("upstream", 502)
    texte = _sans_balise_interne("".join(
        getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text"
    ))
    if fin == "max_tokens":
        # Le texte est utilisable mais TRONQUÉ. On le rend quand même — le
        # perdre serait pire — et on laisse la trace qui permet de retrouver
        # la cause : c'est le budget, pas le fournisseur.
        _log.warning("Claude : réponse coupée au plafond de %s jetons — texte "
                     "tronqué. Relever le budget de cet appel si cela se répète.",
                     max_tokens)
    return texte


def _mistral_call(system, messages, max_tokens, timeout=REQUEST_TIMEOUT):
    """Appel bas niveau à Mistral. Renvoie le texte (peut être vide).

    `timeout` : délai de LECTURE, à dimensionner selon la longueur attendue de
    la réponse (voir REQUEST_TIMEOUT / RERANK_TIMEOUT / GEN_TIMEOUT)."""
    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        raise AssistantError("not_configured", 503)
    import requests
    payload = {
        "model": MISTRAL_MODEL,
        "messages": [{"role": "system", "content": system}] + messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    try:
        # Même borne que pour Claude : c'est l'appel réseau qui immobilise le
        # fil, et c'est lui qu'on compte.
        with _une_place():
            r = requests.post(
                MISTRAL_API_URL, timeout=(CONNECT_TIMEOUT, timeout),
                headers={"Authorization": "Bearer " + key,
                         "Content-Type": "application/json"},
                json=payload)
    except requests.Timeout:
        # Distinct de « injoignable » : le service répond, il est simplement plus
        # lent que le délai accordé. Confondre les deux envoie chercher la panne
        # du mauvais côté (réseau, pare-feu) au lieu du bon (délai, longueur).
        _log.warning("Mistral : délai dépassé (%s s, %s jetons demandés)", timeout, max_tokens)
        raise AssistantError("timeout", 504)
    except requests.RequestException as exc:
        _log.warning("Mistral : connexion impossible (%s)", type(exc).__name__)
        raise AssistantError("network", 502)
    if r.status_code == 429:
        raise AssistantError("busy", 429)
    if r.status_code in (401, 403):
        _log.error("Mistral : authentification refusée (HTTP %s). Vérifier "
                   "MISTRAL_API_KEY (valeur exacte, sans espace ni guillemet).", r.status_code)
        raise AssistantError("auth", 502)
    if r.status_code != 200:
        # Le corps de la réponse, pas seulement son code : c'est là que le
        # fournisseur dit ce qu'il refuse. Même règle que côté Claude, et même
        # cas particulier — un compte à sec n'est pas une panne.
        corps = (r.text or "").strip().replace("\n", " ")[:300]
        if _est_solde(corps):
            _log.error("Mistral : le compte n'a plus de crédit — aucun appel "
                       "n'aboutira tant qu'il n'est pas rechargé. Message : %s", corps)
            raise AssistantError("credit", 503)
        _log.error("Mistral : réponse en erreur (HTTP %s, modèle=%s) : %s",
                   r.status_code, MISTRAL_MODEL, corps or "(sans message)")
        raise AssistantError("upstream", 502)
    try:
        return (r.json()["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError, ValueError):
        _log.error("Mistral : réponse illisible (JSON inattendu)")
        raise AssistantError("upstream", 502)


def _ask_claude(history, context=None):
    return _claude_call(_system(context), history, MAX_OUTPUT_TOKENS) or _FALLBACK


def _ask_mistral(history, context=None):
    return _mistral_call(_system(context), history, MAX_OUTPUT_TOKENS) or _FALLBACK


def answer(model, messages, context=None):
    """Renvoie (réponse, id_modèle) pour le modèle demandé (« claude » ou « mistral »).

    `context` (optionnel) : extraits de la base de connaissance RAG à injecter dans
    le prompt système pour ancrer la réponse sur des sources internes fiables.
    """
    history = _clean_history(messages)
    if not history:
        raise AssistantError("empty", 400)
    if model == "mistral":
        return _ask_mistral(history, context), MISTRAL_MODEL
    return _ask_claude(history, context), CLAUDE_MODEL


def last_user_message(messages):
    """Dernier message utilisateur (pour la requête de récupération RAG)."""
    for m in reversed(messages or []):
        if m.get("role") == "user" and (m.get("content") or "").strip():
            return m["content"].strip()
    return ""


GEN_MAX_TOKENS = 3000

_GEN_GROUNDING = (
    "\n\nAncrage & sourcing du livrable (IMPORTANT) :\n"
    "- Appuie-toi en priorité sur les extraits de la base de connaissance ci-dessus ; "
    "cite la source entre crochets [Titre — Thème] là où tu t'en sers.\n"
    "- Signale explicitement les points NON couverts par la base sous la forme "
    "« À compléter : … » plutôt que de les inventer — ce livrable est un brouillon "
    "à valider par un consultant.\n"
    "- N'invente ni chiffre, ni référence normative, ni citation."
)


def rerank(model, query, hits, top_k):
    """Re-classement des extraits par pertinence via un LLM-juge (précision
    accrue avant génération). Renvoie AU PLUS top_k extraits, du plus au moins
    pertinent. Repli sûr : sans clé API, sur peu d'extraits, ou en cas d'échec,
    renvoie les hits d'origine tronqués — la recherche reste toujours fonctionnelle."""
    hits = list(hits or [])
    if len(hits) <= top_k or not (os.environ.get("MISTRAL_API_KEY")
                                  or os.environ.get("ANTHROPIC_API_KEY")):
        return hits[:top_k] if top_k else hits
    cand = hits[:24]                                    # borne le coût du juge
    listing = "\n".join("[%d] %s" % (i, (h.get("content") or "").replace("\n", " ")[:350])
                        for i, h in enumerate(cand))
    system = ("Tu es un moteur de re-classement d'extraits documentaires. On te donne "
              "une question et des extraits numérotés. Réponds UNIQUEMENT par un tableau "
              "JSON des numéros des extraits vraiment utiles pour répondre, du plus au "
              "moins pertinent, au maximum %d éléments. Aucun autre texte. Ex. : [3,0,7]." % top_k)
    user = "Question : %s\n\nExtraits :\n%s" % ((query or "")[:600], listing)
    try:
        out = (_mistral_call if model == "mistral" else _claude_call)(
            system, [{"role": "user", "content": user}], 120, timeout=RERANK_TIMEOUT)
        m = re.search(r"\[[\d,\s]*\]", out or "")
        order = json.loads(m.group(0)) if m else []
    except Exception:
        return hits[:top_k]
    picked, used = [], set()
    for i in order:
        if isinstance(i, int) and 0 <= i < len(cand) and i not in used:
            picked.append(cand[i]); used.add(i)
        if len(picked) >= top_k:
            break
    for i, h in enumerate(cand):                        # complète si le juge en renvoie peu
        if len(picked) >= top_k:
            break
        if i not in used:
            picked.append(h); used.add(i)
    return picked[:top_k]


def generate(model, system, user, context=None, max_tokens=GEN_MAX_TOKENS):
    """Génère un document (livrable) en un seul tour, ancré sur `context` (RAG).

    Renvoie (texte_markdown, id_modèle). `model` : « claude » ou « mistral »."""
    full_system = system + (("\n\n" + context + _GEN_GROUNDING) if context else "")
    messages = [{"role": "user", "content": user}]
    if model == "mistral":
        return (_mistral_call(full_system, messages, max_tokens,
                              timeout=GEN_TIMEOUT) or _FALLBACK), MISTRAL_MODEL
    return (_claude_call(full_system, messages, max_tokens,
                         timeout=GEN_TIMEOUT) or _FALLBACK), CLAUDE_MODEL


# --- Diagnostic (self-test) ---------------------------------------------------
# Appel minimal par fournisseur pour révéler la cause réelle d'un échec (clé,
# modèle, crédit). Ne renvoie QUE des métadonnées techniques : jamais la clé,
# jamais de contenu de conversation.

def _selftest_claude():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {"configured": False, "ok": False, "detail": "ANTHROPIC_API_KEY absente"}
    try:
        import anthropic
    except ImportError:
        return {"configured": False, "ok": False, "detail": "paquet anthropic non installé"}
    try:
        # MÊME CHEMIN que les appels réels, repli compris : un diagnostic qui
        # interroge autrement que l'application peut réussir là où elle échoue,
        # et inversement — il désignerait alors la mauvaise cause. C'est arrivé.
        _envoi_claude(anthropic.Anthropic(), None,
                      [{"role": "user", "content": "ping"}], 4, REQUEST_TIMEOUT)
    except anthropic.APIConnectionError:
        return {"configured": True, "ok": False, "model": CLAUDE_MODEL, "detail": "réseau injoignable"}
    except anthropic.APIStatusError as exc:
        # Le message du fournisseur EST le diagnostic : sur un 400 il nomme le
        # champ refusé, sur un 404 le modèle introuvable. Le taire obligeait à
        # deviner à partir du seul code HTTP.
        genre, msg = _detail_api(exc)
        # Le compte à sec mérite sa phrase à lui, en français et avec le geste :
        # le message d'origine est exact mais laisse croire à un défaut de
        # configuration, alors que la clé et le modèle sont bons.
        if _est_solde(msg):
            msg = ("le compte Anthropic n'a plus de crédit — la clé et le "
                   "modèle sont bons. Rechargez le compte (console Anthropic, "
                   "Plans & Billing) : aucun appel n'aboutira avant.")
        return {"configured": True, "ok": False, "model": CLAUDE_MODEL,
                "status": getattr(exc, "status_code", None),
                "type": genre or None, "detail": msg or None}
    return {"configured": True, "ok": True, "model": CLAUDE_MODEL,
            "detail": "OK — réglages du modèle" if _CONSIGNE_REFUSEE else "OK"}


def _selftest_mistral():
    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        return {"configured": False, "ok": False, "detail": "MISTRAL_API_KEY absente"}
    import requests
    try:
        r = requests.post(
            MISTRAL_API_URL, timeout=(CONNECT_TIMEOUT, REQUEST_TIMEOUT),
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
            json={"model": MISTRAL_MODEL, "max_tokens": 4,
                  "messages": [{"role": "user", "content": "ping"}]})
    except requests.Timeout:
        return {"configured": True, "ok": False, "model": MISTRAL_MODEL,
                "detail": "délai dépassé sur un appel minimal (4 jetons)"}
    except requests.RequestException:
        return {"configured": True, "ok": False, "model": MISTRAL_MODEL, "detail": "réseau injoignable"}
    return {"configured": True, "ok": r.status_code == 200, "model": MISTRAL_MODEL,
            "status": r.status_code}


def selftest():
    """Diagnostic par fournisseur (statuts techniques uniquement, aucun secret)."""
    return {"claude": _selftest_claude(), "mistral": _selftest_mistral()}
