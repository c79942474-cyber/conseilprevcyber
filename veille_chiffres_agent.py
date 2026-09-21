# -*- coding: utf-8 -*-
"""
L'AGENT QUI CHERCHE UNE RÉFÉRENCE — ET LA LAISSE QU'IL PORTE.

═══ CE QUI CHANGE PAR RAPPORT À LA QUALIFICATION ASSISTÉE ═════════════════
Là-bas, `allowed_tools` est VIDE : les lignes du registre voyagent en
données et l'agent n'a rien à ouvrir. Ici, les outils SONT le sujet — on lui
demande d'aller lire le web, et lui refuser la lecture viderait la tâche de
son contenu. La liste n'est donc pas vide : elle est FERMÉE À DEUX.

  WebSearch, WebFetch — et rien d'autre.

Read, Write, Edit, Bash restent refusés nommément, pour la même raison
qu'ailleurs : un agent qui peut écrire sur le serveur peut changer ce que le
cabinet publie sans qu'une personne l'ait décidé.

═══ PLUSIEURS TOURS, ET C'EST JUSTIFIÉ ═══════════════════════════════════
La qualification tient en un tour : lire une déclaration, répondre en JSON.
Celle-ci n'en tient pas — chercher, lire un résultat, reformuler parce qu'il
ne dit rien, lire le suivant. Combien de tours dépend de ce qui revient,
et c'est précisément ce qui justifie un agent plutôt qu'un appel de modèle.
Le plafond existe quand même : une recherche sans fond coûte sans rendre.

═══ PAS DE REPLI PAR L'API ═══════════════════════════════════════════════
`qualification_moteur` se replie sur l'API Messages quand l'exécutable
manque, parce que la tâche ne demandait aucun outil. Ici le repli n'aurait
aucun sens : un modèle sans accès au web ne peut pas retrouver un document,
il peut seulement en inventer un plausible. Sans agent, ce module dit qu'il
ne peut pas chercher — et c'est la bonne réponse.

═══ ET LA VÉRIFICATION NE PASSE PAS PAR LUI ══════════════════════════════
`ouvrir_page()` rouvre l'adresse citée avec `urllib`, hors de l'agent. Si
l'agent s'était trompé de page, ou avait rapporté une phrase qui n'y est
pas, c'est ce module-ci qui l'arrête — sans consulter aucun modèle.
"""

import html as _html
import os
import re
import urllib.request

VERSION = "2026-09-a"

MODELE = os.environ.get("VEILLE_CHIFFRES_MODELE", "claude-sonnet-5")

# DEUX OUTILS, NOMMÉS. Le web se lit ; le disque ne se touche pas.
OUTILS_AUTORISES = ["WebSearch", "WebFetch"]

OUTILS_INTERDITS = [
    "Read", "Write", "Edit", "NotebookEdit", "Bash", "BashOutput",
    "Glob", "Grep", "Task", "TodoWrite",
]

# Chercher, lire, reformuler, relire. Au-delà, la recherche tourne en rond.
TOURS_MAX = 8

# Une page de rapport dépasse rarement ce volume en texte utile, et au-delà
# on paierait pour du pied de page.
PAGE_MAX_OCTETS = 800_000
DELAI = 30


# OÙ LE BUILD A POSÉ L'EXÉCUTABLE. Le SDK pilote Claude Code en
# sous-processus ; `build.sh` l'installe dans le dossier du projet et écrit
# ici le chemin qui a répondu à `--version`.
MARQUEUR_CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            ".cli-claude", "CHEMIN")


def chemin_cli():
    """Où est l'exécutable Claude Code, ou None.

    PREMIÈRE ÉCRITURE, ET POURQUOI ELLE ÉTAIT FAUSSE. Elle important
    `qualification_moteur` — un module de l'AUTRE dépôt. L'import échouait
    silencieusement ici et retombait sur `shutil.which`, si bien que la
    résolution paraissait marcher sur ma machine et n'aurait rien résolu en
    ligne. Un dépôt ne se repose pas sur un fichier qu'il n'a pas.
    """
    import shutil
    declare = (os.environ.get("VEILLE_CLI_CHEMIN") or "").strip()
    if declare and os.path.exists(declare):
        return declare
    try:
        with open(MARQUEUR_CLI, encoding="utf-8") as f:
            pose = f.read().strip()
        if pose and os.path.exists(pose):
            return pose
    except Exception:
        pass
    trouve = shutil.which("claude")
    if trouve:
        return trouve
    for chemin in (os.path.expanduser("~/.npm-global/bin/claude"),
                   "/usr/local/bin/claude",
                   os.path.expanduser("~/.local/bin/claude")):
        if os.path.exists(chemin):
            return chemin
    return None


def sdk_disponible():
    """Le SDK et son exécutable sont-ils là ?

    Mesuré, jamais supposé — et ici l'absence n'a pas de repli : elle
    interdit la recherche au lieu de la remplacer par une invention.
    """
    try:
        import claude_agent_sdk  # noqa: F401
    except Exception:
        return False
    return chemin_cli() is not None


def options_sdk(systeme_prompt=""):
    """Les options EXACTES passées au SDK, rendues telles quelles pour
    qu'une règle les mesure plutôt que de lire le code source."""
    from claude_agent_sdk import ClaudeAgentOptions
    reglages = dict(
        allowed_tools=list(OUTILS_AUTORISES),
        disallowed_tools=list(OUTILS_INTERDITS),
        system_prompt=systeme_prompt,
        model=MODELE,
        max_turns=TOURS_MAX,
        setting_sources=[],
    )
    reglages["cli_path"] = chemin_cli()
    return ClaudeAgentOptions(**reglages)


def _texte_des_messages(messages):
    morceaux = []
    for m in messages:
        for bloc in getattr(m, "content", None) or []:
            t = getattr(bloc, "text", None)
            if t:
                morceaux.append(t)
    return "".join(morceaux)


def chercher(demande, systeme_prompt):
    """Lance l'agent et rend (ok, texte). Aucun repli."""
    if not sdk_disponible():
        return False, "agent_indisponible"
    import asyncio
    from claude_agent_sdk import query

    async def _aller():
        recus = []
        async for m in query(prompt=demande,
                             options=options_sdk(systeme_prompt)):
            recus.append(m)
        return recus

    try:
        messages = asyncio.run(_aller())
    except Exception as e:
        return False, "agent_en_echec: %s" % str(e)[:200]
    t = _texte_des_messages(messages)
    return (True, t) if t.strip() else (False, "reponse_vide")


# ═══════════════════════════════════════════════════════════════════════
# LA RELECTURE INDÉPENDANTE DE LA PAGE
# ═══════════════════════════════════════════════════════════════════════

_BALISES_MUETTES = re.compile(
    r"<(script|style|noscript)[^>]*>.*?</\1>", re.S | re.I)
_BALISE = re.compile(r"<[^>]+>")


def _en_texte(brut):
    """Le texte lisible d'une page. Grossier, et il doit l'être.

    Un extracteur savant rendrait un texte plus propre — et différent de
    celui que l'agent a lu. Ce qu'on veut ici n'est pas la meilleure
    lecture : c'est la plus littérale, pour que « la phrase est-elle dans
    la page » ait une réponse et non une appréciation.
    """
    t = _BALISES_MUETTES.sub(" ", brut)
    t = _BALISE.sub(" ", t)
    return _html.unescape(t)


def ouvrir_page(adresse, ouvrir=None):
    """Rouvre l'adresse citée, hors de l'agent.

    C'est le contrôle qui rend la vérification indépendante du modèle : si
    l'agent a cité une page qu'il a mal lue, c'est ici que ça se voit.
    """
    ouvrir = ouvrir or (lambda u: urllib.request.urlopen(
        urllib.request.Request(u, headers={
            "User-Agent": "Mozilla/5.0 (compatible; CONSEILPREV-veille/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.8",
        }), timeout=DELAI))
    with ouvrir(adresse) as r:
        brut = r.read(PAGE_MAX_OCTETS)
    if isinstance(brut, bytes):
        brut = brut.decode("utf-8", "replace")
    return _en_texte(brut)


def etat():
    return {
        "version": VERSION,
        "modele": MODELE,
        "agent_disponible": sdk_disponible(),
        "chemin_cli": chemin_cli(),
        "outils_autorises": list(OUTILS_AUTORISES),
        "outils_interdits": list(OUTILS_INTERDITS),
        "tours_max": TOURS_MAX,
        "repli": None,
        "repli_texte": "Aucun. Un modèle sans accès au web ne retrouve pas "
                       "un document : il en invente un plausible.",
    }


def _verifier():
    assert OUTILS_AUTORISES == ["WebSearch", "WebFetch"], OUTILS_AUTORISES
    for interdit in ("Read", "Write", "Edit", "Bash"):
        assert interdit in OUTILS_INTERDITS, interdit
        assert interdit not in OUTILS_AUTORISES, interdit
    assert TOURS_MAX > 1, "chercher demande plus d'un tour"
    assert TOURS_MAX <= 20, "au-delà, la recherche tourne en rond"
    assert MODELE.strip()
    assert PAGE_MAX_OCTETS > 10_000


_verifier()
