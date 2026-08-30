"""Les réglages lus dans l'environnement, sans faire tomber le service.

CE QUE CE MODULE EMPÊCHE, ET C'EST ARRIVÉ EN PRODUCTION. Une variable
numérique mal renseignée — une clé collée dans la mauvaise case de la console
d'hébergement — fait lever `int()` AU CHARGEMENT du module. L'exception
remonte avant toute journalisation, avant toute route, avant même que
l'application existe : le serveur ne démarre pas, et le déploiement échoue sur
une trace d'importation de quarante lignes où rien ne dit qu'il s'agit d'un
réglage. Le service est à terre pour une valeur qui n'aurait dû changer qu'un
plafond d'affichage.

UNE VALEUR DE RÉGLAGE ILLISIBLE NE VAUT PAS UN SERVICE ARRÊTÉ. On retombe sur
le défaut, et on le DIT — dans les journaux, où l'exploitant le trouvera en
cherchant pourquoi son réglage n'a pas pris effet.

LA VALEUR N'EST JAMAIS JOURNALISÉE, et c'est la leçon la plus coûteuse de
l'incident. Celle qui l'a provoqué était une clé secrète : l'exception l'a
imprimée EN CLAIR dans les journaux de construction de l'hébergeur, où elle
demeure. Le message nomme la variable et la forme attendue ; jamais ce que la
variable contenait.

POURQUOI UN MODULE ET NON UNE FONCTION RECOPIÉE. Le motif existait déjà —
`gunicorn.conf.py` le porte depuis l'origine — et n'avait jamais été appliqué
ailleurs. Vingt lectures numériques d'environnement se faisaient sans garde,
dans neuf fichiers. Recopier la fonction dans chacun en aurait fait neuf
versions qui divergeraient ; ce module n'a aucune dépendance et se laisse
importer par tous, y compris les plus bas.
"""
import logging
import os

VERSION = "2026-08-a"

_log = logging.getLogger("reglages")


def _refus(nom, attendu, motif):
    """Journalise un réglage écarté SANS jamais montrer sa valeur."""
    _log.warning("Réglage %s ignoré (%s) — %s attendu. La valeur par défaut "
                 "s'applique ; corrigez la variable d'environnement.",
                 nom, motif, attendu)


def entier(nom, defaut, mini=None, maxi=None):
    """Un entier lu dans l'environnement, ou le défaut.

    `mini` et `maxi` BORNENT plutôt qu'ils ne refusent : un plafond
    d'affichage réglé à zéro est une erreur de saisie, pas une demande de
    n'afficher rien, et retomber sur le défaut serait plus surprenant que de
    ramener à la borne.
    """
    brut = os.environ.get(nom)
    if brut is None or not str(brut).strip():
        valeur = defaut
    else:
        try:
            valeur = int(str(brut).strip())
        except (TypeError, ValueError):
            _refus(nom, "un nombre entier", "valeur non numérique")
            valeur = defaut
    if mini is not None and valeur < mini:
        valeur = mini
    if maxi is not None and valeur > maxi:
        valeur = maxi
    return valeur


def reel(nom, defaut, mini=None, maxi=None):
    """Un nombre décimal lu dans l'environnement, ou le défaut."""
    brut = os.environ.get(nom)
    if brut is None or not str(brut).strip():
        valeur = float(defaut)
    else:
        try:
            valeur = float(str(brut).strip().replace(",", "."))
        except (TypeError, ValueError):
            _refus(nom, "un nombre", "valeur non numérique")
            valeur = float(defaut)
    if mini is not None and valeur < mini:
        valeur = float(mini)
    if maxi is not None and valeur > maxi:
        valeur = float(maxi)
    return valeur


def booleen(nom, defaut=False):
    """Un drapeau lu dans l'environnement.

    LES DEUX SENS SONT NOMMÉS. Un drapeau qui ne reconnaîtrait que « 1 »
    traiterait « oui », « true » et « on » comme faux — c'est-à-dire comme un
    refus délibéré, alors que c'est une acceptation mal orthographiée.
    """
    brut = (os.environ.get(nom) or "").strip().lower()
    if not brut:
        return bool(defaut)
    if brut in ("1", "oui", "on", "true", "vrai", "yes"):
        return True
    if brut in ("0", "non", "off", "false", "faux", "no"):
        return False
    _refus(nom, "oui/non", "valeur non reconnue")
    return bool(defaut)
