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
import os

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
    "directe, concise et structurée. Ne dévoile pas ton raisonnement interne : donne "
    "directement la réponse utile.\n"
    "- Quand c'est pertinent, termine par une piste d'action concrète (lancer un état "
    "des lieux, ouvrir l'audit de conformité, nous contacter)."
)

CLAUDE_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")
MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-large-latest")
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

MAX_MSG_CHARS = 2000       # longueur maximale d'un message utilisateur
MAX_HISTORY = 12           # nombre de messages de contexte conservés
MAX_OUTPUT_TOKENS = 900    # réponse concise (bien en deçà des délais/coûts)
REQUEST_TIMEOUT = 30


class AssistantError(Exception):
    """Erreur d'assistant portant un code interne + un statut HTTP."""

    def __init__(self, code, status=502):
        super().__init__(code)
        self.code = code
        self.status = status


def available():
    """Modèles réellement configurés (clé d'API présente)."""
    claude = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if claude:
        try:
            import anthropic  # noqa: F401
        except ImportError:
            claude = False
    return {"claude": claude, "mistral": bool(os.environ.get("MISTRAL_API_KEY"))}


def _clean_history(messages):
    """Ne garde que des tours user/assistant non vides, bornés, commençant par user."""
    out = []
    for m in messages or []:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            out.append({"role": role, "content": content[:MAX_MSG_CHARS]})
    out = out[-MAX_HISTORY:]
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out


_FALLBACK = "Désolé, je n'ai pas pu formuler de réponse. Pouvez-vous reformuler votre question ?"


def _ask_claude(history):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise AssistantError("not_configured", 503)
    try:
        import anthropic
    except ImportError:
        raise AssistantError("not_configured", 503)
    client = anthropic.Anthropic()  # lit ANTHROPIC_API_KEY dans l'environnement
    try:
        # Opus 4.8 : en omettant « thinking », le modèle répond sans phase de
        # réflexion (latence réduite) ; le prompt système impose une réponse directe.
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=SYSTEM_PROMPT,
            messages=history,
        )
    except anthropic.APIConnectionError:
        raise AssistantError("network", 502)
    except anthropic.RateLimitError:
        raise AssistantError("busy", 429)
    except anthropic.APIStatusError:
        raise AssistantError("upstream", 502)
    text = "".join(
        getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text"
    ).strip()
    return text or _FALLBACK


def _ask_mistral(history):
    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        raise AssistantError("not_configured", 503)
    import requests
    payload = {
        "model": MISTRAL_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + history,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": 0.3,
    }
    try:
        r = requests.post(
            MISTRAL_API_URL, timeout=REQUEST_TIMEOUT,
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
            json=payload)
    except requests.RequestException:
        raise AssistantError("network", 502)
    if r.status_code == 429:
        raise AssistantError("busy", 429)
    if r.status_code != 200:
        raise AssistantError("upstream", 502)
    try:
        text = (r.json()["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError, ValueError):
        raise AssistantError("upstream", 502)
    return text or _FALLBACK


def answer(model, messages):
    """Renvoie (réponse, id_modèle) pour le modèle demandé (« claude » ou « mistral »)."""
    history = _clean_history(messages)
    if not history:
        raise AssistantError("empty", 400)
    if model == "mistral":
        return _ask_mistral(history), MISTRAL_MODEL
    return _ask_claude(history), CLAUDE_MODEL
