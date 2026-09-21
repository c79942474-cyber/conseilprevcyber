#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════
# CONSTRUCTION DU SERVICE — LES DÉPENDANCES PYTHON, PUIS LE CLI CLAUDE CODE
# ══════════════════════════════════════════════════════════════════════════
#
# POURQUOI CE FICHIER EXISTE. `claude_agent_sdk` ne parle pas HTTP : il pilote
# l'exécutable Claude Code en sous-processus. L'image Python de Render n'en
# contient pas. Sans lui, `veille_chiffres_agent` ne peut pas chercher — et
# il le DIT au lieu de se replier sur un modèle sans accès au web, qui
# n'aurait pas retrouvé un document mais en aurait inventé un plausible.
#
# CE SCRIPT NE FAIT JAMAIS TOMBER LE BUILD POUR LE CLI. C'est la règle qui
# compte ici. Le site entier ne doit pas cesser d'être déployable parce qu'un
# binaire tiers n'a pas pu être téléchargé : la veille des chiffres attendra,
# le reste du site n'a pas de repli du tout. Seul `pip install` peut faire
# échouer ce script, exactement comme avant.
#
# IL NE SUPPOSE PAS L'INTERFACE DE L'INSTALLATEUR. Deux chemins sont essayés,
# et dans les deux cas le résultat est VÉRIFIÉ en exécutant `--version` plutôt
# qu'en supposant qu'un fichier est apparu au bon endroit. Le chemin retenu
# est écrit dans un fichier que le module relit au démarrage : aucune des deux
# parties n'a besoin de connaître les conventions de l'autre.

set -o pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOSSIER_CLI="$RACINE/.cli-claude"
MARQUEUR="$DOSSIER_CLI/CHEMIN"

echo "── Dépendances Python ────────────────────────────────────────────────"
pip install -r "$RACINE/requirements.txt" || exit 1

echo
echo "── Exécutable Claude Code (pour le SDK) ──────────────────────────────"

rm -rf "$DOSSIER_CLI"
mkdir -p "$DOSSIER_CLI"

# Un candidat n'est retenu que s'il RÉPOND. Un fichier présent mais non
# exécutable, ou compilé pour une autre architecture, ne vaut rien.
retenir_si_il_repond() {
  local chemin="$1"
  [ -n "$chemin" ] && [ -x "$chemin" ] || return 1
  local v
  v="$("$chemin" --version 2>/dev/null | head -1)" || return 1
  [ -n "$v" ] || return 1
  printf '%s' "$chemin" > "$MARQUEUR"
  echo "   ✓ Claude Code retenu : $chemin  ($v)"
  return 0
}

# 0. DÉJÀ PRÉSENT DANS L'IMAGE. Le cas du poste de développement, et celui
#    d'une image Render qui en embarquerait un un jour.
if retenir_si_il_repond "$(command -v claude 2>/dev/null)"; then
  exit 0
fi

# 1. PAR NPM, SI NODE EST LÀ. `--prefix` installe DANS le dossier du projet :
#    c'est lui qui survit jusqu'à l'exécution, pas $HOME.
if command -v npm >/dev/null 2>&1; then
  echo "   npm trouvé — installation de @anthropic-ai/claude-code"
  npm install --prefix "$DOSSIER_CLI" --no-audit --no-fund --loglevel=error \
      @anthropic-ai/claude-code >/dev/null 2>&1
  if retenir_si_il_repond "$DOSSIER_CLI/node_modules/.bin/claude"; then
    exit 0
  fi
  echo "   npm n'a pas produit d'exécutable utilisable."
else
  echo "   npm absent de cette image."
fi

# 2. PAR L'INSTALLATEUR NATIF — SANS SUPPOSER SON INTERFACE.
#    Je ne connais pas le nom de sa variable de destination, et l'inventer
#    produirait une installation silencieusement hors du projet. On lui donne
#    donc un $HOME à lui, dans le projet, puis on CHERCHE ce qu'il a posé.
FAUX_HOME="$DOSSIER_CLI/home"
mkdir -p "$FAUX_HOME"
echo "   Tentative par l'installateur natif (HOME=$FAUX_HOME)"
if curl -fsSL https://claude.ai/install.sh 2>/dev/null | HOME="$FAUX_HOME" bash >/dev/null 2>&1; then
  TROUVE="$(find "$FAUX_HOME" -type f -name claude -perm -u+x 2>/dev/null | head -1)"
  if retenir_si_il_repond "$TROUVE"; then
    exit 0
  fi
fi

# 3. AUCUN CHEMIN N'A ABOUTI — ET CE N'EST PAS UNE PANNE.
rm -f "$MARQUEUR"
echo "   ✗ Aucun exécutable Claude Code n'a pu être installé."
echo "     La qualification assistée servira par l'API Messages d'Anthropic,"
echo "     avec le même modèle. L'écran l'affiche ; rien d'autre n'est touché."
exit 0
