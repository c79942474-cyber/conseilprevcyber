"""Un réglage illisible ne doit pas valoir un service arrêté.

CE QUI EST ARRIVÉ, ET QUE CES RÈGLES EMPÊCHENT DE REVENIR. Une clé collée dans
la mauvaise case de la console d'hébergement a atteint `RAG_LISTE_MAX`.
`int()` a levé AU CHARGEMENT du module — avant toute journalisation, avant
toute route, avant que l'application existe. Gunicorn n'a pas démarré. Le site
entier est resté indisponible parce qu'un plafond d'affichage de la console
d'administration avait reçu une valeur qui n'était pas un nombre.

Et l'exception a fait une seconde victime : elle a imprimé LA CLÉ EN CLAIR
dans les journaux de construction de l'hébergeur, où elle demeure.

DEUX FAMILLES DE RÈGLES, ET ELLES NE SE REMPLACENT PAS :

  · les règles de COMPORTEMENT éprouvent que la conversion tolérante fait ce
    qu'elle promet — l'environnement empoisonné, les modules se chargent
    quand même, chaque constante vaut son défaut ;
  · la règle de STRUCTURE parcourt l'arbre syntaxique de tout le dépôt et
    vérifie qu'AUCUN convertisseur qui lève ne reçoit jamais une valeur
    d'environnement. Elle seule attrape la vingtième lecture, celle qui sera
    écrite le mois prochain et que la table ci-dessous ne connaîtra pas.

Ni l'une ni l'autre ne regarde le TEXTE du code : la première mesure un
résultat, la seconde une forme d'arbre. Renommer, reformater, réécrire les
commentaires ne les fait pas bouger ; retirer une garde les tue.
"""
import ast
import io
import json
import os
import subprocess
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import reglages  # noqa: E402


# La valeur qui a cassé la production avait la forme d'un secret. Toutes les
# règles qui suivent l'emploient telle quelle : ce qu'on éprouve, ce n'est pas
# seulement qu'elle est refusée, c'est qu'elle ne RESSORT nulle part.
POISON = "7b8877af6257c0df78118046e5321a1f"


# ── 1. Ce que fait le lecteur tolérant ─────────────────────────────────────

def test_valeur_illisible_rend_le_defaut(monkeypatch):
    monkeypatch.setenv("X_ESSAI", POISON)
    assert reglages.entier("X_ESSAI", 2000) == 2000
    assert reglages.reel("X_ESSAI", 1.5) == 1.5


def test_le_refus_nomme_la_variable(monkeypatch, caplog):
    """Sans le nom, l'exploitant ne peut pas savoir QUEL réglage est ignoré."""
    monkeypatch.setenv("RAG_LISTE_MAX", POISON)
    with caplog.at_level("WARNING", logger="reglages"):
        reglages.entier("RAG_LISTE_MAX", 2000)
    assert any("RAG_LISTE_MAX" in r.getMessage() for r in caplog.records)


def test_la_valeur_refusee_n_apparait_jamais_au_journal(monkeypatch, caplog):
    """LA RÈGLE LA PLUS CHÈRE DE L'INCIDENT.

    La valeur qui a fait tomber le service était un secret, et la trace l'a
    imprimée en clair là où elle reste consultable. Le journal nomme la
    variable et la forme attendue ; jamais ce que la variable contenait.
    """
    monkeypatch.setenv("X_SECRET", POISON)
    with caplog.at_level("WARNING", logger="reglages"):
        reglages.entier("X_SECRET", 2000)
        reglages.reel("X_SECRET", 2.0)
        reglages.booleen("X_SECRET", False)
    assert caplog.records, "un réglage ignoré doit se dire"
    for enregistrement in caplog.records:
        assert POISON not in enregistrement.getMessage()
        assert POISON not in str(enregistrement.args or ())


def test_variable_absente_ou_vide_ne_reproche_rien(monkeypatch, caplog):
    """Non renseigné n'est pas une faute : le défaut s'applique, en silence.

    Avertir ici noierait le seul message qui compte sous des dizaines
    d'avertissements sans objet.
    """
    monkeypatch.delenv("X_ABSENT", raising=False)
    monkeypatch.setenv("X_VIDE", "   ")
    with caplog.at_level("WARNING", logger="reglages"):
        assert reglages.entier("X_ABSENT", 7) == 7
        assert reglages.entier("X_VIDE", 7) == 7
        assert reglages.booleen("X_ABSENT", True) is True
    assert not caplog.records


def test_les_bornes_ramenent_au_lieu_de_refuser(monkeypatch):
    """Un plafond réglé à zéro est une faute de frappe, pas une demande de
    n'afficher rien — et retomber sur le défaut surprendrait davantage que de
    ramener à la borne, car la valeur saisie serait alors sans effet."""
    monkeypatch.setenv("X_BORNE", "0")
    assert reglages.entier("X_BORNE", 2000, mini=1) == 1
    monkeypatch.setenv("X_BORNE", "999999")
    assert reglages.entier("X_BORNE", 2000, maxi=10000) == 10000
    monkeypatch.setenv("X_BORNE", "-4")
    assert reglages.reel("X_BORNE", 30.0, mini=1) == 1.0


def test_une_valeur_valide_est_bien_prise(monkeypatch):
    """Le lecteur tolérant doit rester un lecteur : une règle qui ne verrait
    que le refus resterait verte si la fonction rendait TOUJOURS le défaut."""
    monkeypatch.setenv("X_OK", "500")
    assert reglages.entier("X_OK", 2000) == 500
    monkeypatch.setenv("X_OK", "2,5")
    assert reglages.reel("X_OK", 1.0) == 2.5   # la virgule décimale française
    monkeypatch.setenv("X_OK", " 12 ")
    assert reglages.entier("X_OK", 0) == 12


def test_le_drapeau_reconnait_les_deux_sens(monkeypatch, caplog):
    """Un drapeau qui n'admettrait que « 1 » traiterait « oui » comme faux —
    c'est-à-dire comme un refus délibéré, alors que c'est une acceptation."""
    for vrai in ("1", "oui", "on", "true", "VRAI", "yes"):
        monkeypatch.setenv("X_D", vrai)
        assert reglages.booleen("X_D", False) is True, vrai
    for faux in ("0", "non", "off", "false", "FAUX", "no"):
        monkeypatch.setenv("X_D", faux)
        assert reglages.booleen("X_D", True) is False, faux
    monkeypatch.setenv("X_D", "peut-être")
    with caplog.at_level("WARNING", logger="reglages"):
        assert reglages.booleen("X_D", True) is True
    assert caplog.records, "une valeur non reconnue doit se dire"


# ── 2. La régression : l'environnement empoisonné, tout se charge ──────────

# (module, attribut, variable d'environnement, valeur attendue une fois la
#  variable rendue illisible). C'EST CETTE TABLE QUI PILOTE LA RÈGLE : une
#  seule ligne rendue à `int(os.environ…)` fait tomber l'essai.
REGLAGES = (
    ("rag_store",     "LISTE_MAX",               "RAG_LISTE_MAX",              2000),
    ("rag_store",     "MAX_FILE_BYTES",          "RAG_MAX_FILE_MB",            30 * 1024 * 1024),
    ("rag_store",     "_RECONNECT_MIN_INTERVAL", "RAG_RECONNECT_INTERVAL",     20.0),
    ("antivirus",     "MAX_OCTETS",              "DEPOT_MAX_MB",               20 * 1024 * 1024),
    ("audit",         "MAX_ENTREES",             "AUDIT_MAX_ROWS",             20000),
    ("audit",         "RETENTION_JOURS",         "AUDIT_RETENTION_JOURS",      365),
    ("auth",          "_USER_CACHE_TTL",         "AUTH_CACHE_TTL",             300.0),
    ("automation",    "_VEILLE_FULLTEXT_MAX",    "VEILLE_FULLTEXT_MAX",        25),
    ("automation",    "ALERT_COOLDOWN_S",        "ALERTES_COOLDOWN_MIN",       3600),
    ("clients_store", "DOC_MAX_BYTES",           "CLIENTS_DOC_MAX_MB",         15 * 1024 * 1024),
    ("resilience",    "DELAI_MIN",               "RECONNECT_MIN_S",            30.0),
    ("resilience",    "DELAI_MAX",               "RECONNECT_MAX_S",            300.0),
    ("assistant",     "MAX_SIMULTANE",           "LLM_MAX_SIMULTANE",          3),
    # Zéro y signifie « aucune purge » : le défaut ressort None, et c'est le
    # `or None` du site qui porte ce sens — pas le lecteur.
    ("app",           "_RETENTION_DAYS",         "EVENT_RETENTION_DAYS",       None),
    ("app",           "_MAX_ROWS",               "EVENT_MAX_ROWS",             None),
    ("app",           "_MAINTENANCE_HOURS",      "MAINTENANCE_INTERVAL_HOURS", 6.0),
)


def _charger(env_sup, demandes):
    """Charge des modules dans un interpréteur NEUF, comme le fait le serveur.

    Un `importlib.reload` en cours d'essai ne reproduirait pas la panne : ce
    qui est tombé en production, c'est un PREMIER chargement. Le sous-processus
    n'écrit pas de bytecode — un `.pyc` périmé a déjà fait survivre une
    mutation à sa restauration.
    """
    script = (
        "import json, sys\n"
        "sortie = {}\n"
        "for mod, attr in %r:\n"
        "    m = __import__(mod)\n"
        "    sortie[mod + '.' + attr] = getattr(m, attr)\n"
        "sys.stdout.write('@@' + json.dumps(sortie))\n" % (list(demandes),)
    )
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(env_sup)
    r = subprocess.run([sys.executable, "-c", script], cwd=ICI, env=env,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, (
        "le chargement a échoué — c'est exactement la panne de production :\n"
        + r.stderr[-2000:])
    return json.loads(r.stdout.split("@@", 1)[1]), r.stderr


def test_environnement_empoisonne_le_service_demarre_quand_meme():
    """LA RÈGLE QUI AURAIT ARRÊTÉ L'INCIDENT.

    Toutes les variables numériques reçoivent la valeur qui a cassé la
    production. Chaque module doit se charger, et chaque constante valoir son
    défaut : un réglage illisible coûte le réglage, jamais le service.
    """
    poison = {var: POISON for _, _, var, _ in REGLAGES}
    valeurs, journal = _charger(poison, [(m, a) for m, a, _, _ in REGLAGES])
    for module, attribut, variable, defaut in REGLAGES:
        obtenu = valeurs["%s.%s" % (module, attribut)]
        assert obtenu == defaut, (
            "%s.%s vaut %r au lieu du défaut %r : la garde de %s manque"
            % (module, attribut, obtenu, defaut, variable))
    # Et rien de tout cela n'a laissé le secret dans les journaux.
    assert POISON not in journal


def test_chaque_variable_refusee_est_nommee_au_demarrage():
    """Un service qui repart en ignorant un réglage sans le dire est pire
    qu'un service qui tombe : personne ne cherchera plus jamais pourquoi le
    réglage n'a pas d'effet."""
    poison = {var: POISON for _, _, var, _ in REGLAGES}
    _, journal = _charger(poison, [(m, a) for m, a, _, _ in REGLAGES])
    for _, _, variable, _ in REGLAGES:
        assert variable in journal, "%s ignorée sans le dire" % variable


def test_une_valeur_valide_traverse_jusqu_au_module():
    """Le pendant de la règle précédente : si le chargement rendait toujours
    le défaut, l'environnement empoisonné serait vert et le réglage mort."""
    valeurs, _ = _charger({"RAG_LISTE_MAX": "750", "AUDIT_MAX_ROWS": "99"},
                          [("rag_store", "LISTE_MAX"), ("audit", "MAX_ENTREES")])
    assert valeurs["rag_store.LISTE_MAX"] == 750
    assert valeurs["audit.MAX_ENTREES"] == 99


def test_le_plafond_de_liste_ne_depasse_pas_le_plafond_dur():
    valeurs, _ = _charger({"RAG_LISTE_MAX": "999999"},
                          [("rag_store", "LISTE_MAX"), ("rag_store", "LISTE_PLAFOND")])
    assert valeurs["rag_store.LISTE_MAX"] == valeurs["rag_store.LISTE_PLAFOND"]


# ── 3. La conjonction : deux réglages justes séparément, faux ensemble ─────

def test_le_plafond_de_recul_ne_passe_pas_sous_son_plancher():
    """AUCUNE DES DEUX VARIABLES N'EST FAUTIVE — LEUR ORDRE L'EST.

    Le recul vaut `min(DELAI_MIN * 2**n, DELAI_MAX)`. Inversés, ce minimum
    s'effondre en une constante PLUS COURTE que le plancher : la garde contre
    le martèlement d'une base absente se retourne en martèlement, et rien dans
    l'une ou l'autre valeur prise seule ne le laisse voir.
    """
    valeurs, _ = _charger({"RECONNECT_MIN_S": "120", "RECONNECT_MAX_S": "30"},
                          [("resilience", "DELAI_MIN"), ("resilience", "DELAI_MAX")])
    mini = valeurs["resilience.DELAI_MIN"]
    maxi = valeurs["resilience.DELAI_MAX"]
    assert mini == 120.0, "la valeur saisie doit être prise"
    for echecs in range(1, 7):
        recul = min(mini * (2 ** (echecs - 1)), maxi)
        assert recul >= mini, (
            "après %d échecs, le recul retombe à %s s, sous le plancher de %s s"
            % (echecs, recul, mini))


# ── 4. Les lectures faites À L'APPEL, que le chargement ne couvre pas ──────

def test_un_port_antivirus_illisible_ne_leve_pas(monkeypatch):
    """Un ClamAV mal configuré rend « indisponible » — le verdict honnête.

    Une exception, elle, remonterait au dépôt de fichier : le port mal saisi
    ferait échouer le dépôt au lieu de faire échouer l'analyse.
    """
    import antivirus
    monkeypatch.setenv("CLAMAV_HOST", "127.0.0.1")
    monkeypatch.setenv("CLAMAV_PORT", POISON)
    monkeypatch.delenv("CLAMAV_SOCKET", raising=False)
    verdict, _detail = antivirus._clamav_flux(b"contenu", delai=0.5)
    assert verdict == "indisponible"


# ── 5. La règle de structure : elle attrape la lecture pas encore écrite ───

# `gunicorn.conf.py` est exécuté par Gunicorn AVANT que le répertoire de
# l'application soit garanti sur le chemin d'import : un `import reglages` y
# échangerait une panne connue contre une panne de démarrage plus obscure.
# Il porte donc sa propre garde, et l'exception est nommée ici pour que la
# duplication reste un choix visible.
GARDE_LOCALE = {"gunicorn.conf.py"}


def _fichiers_du_depot():
    for nom in sorted(os.listdir(ICI)):
        if nom.endswith(".py") and not nom.startswith("test_"):
            yield nom


class _Chercheur(ast.NodeVisitor):
    """Repère `int(...)` / `float(...)` dont l'argument touche `os.environ`."""

    def __init__(self):
        self.trouves = []

    def visit_Call(self, node):
        f = node.func
        if isinstance(f, ast.Name) and f.id in ("int", "float") and node.args:
            for sous in ast.walk(node.args[0]):
                if isinstance(sous, ast.Attribute) and sous.attr == "environ":
                    self.trouves.append(node.lineno)
                    break
                if (isinstance(sous, ast.Attribute) and sous.attr in ("get", "getenv")
                        and isinstance(sous.value, ast.Name) and sous.value.id == "os"):
                    self.trouves.append(node.lineno)
                    break
        self.generic_visit(node)


def test_aucun_convertisseur_qui_leve_ne_recoit_l_environnement():
    """LA RÈGLE QUI SURVIT À CE CHANTIER.

    La table plus haut connaît dix-neuf lectures. Elle ne connaîtra jamais la
    vingtième. Celle-ci parcourt l'arbre syntaxique : elle n'examine ni un mot
    ni une ligne, mais la FORME de l'appel — un convertisseur qui lève, nourri
    d'une valeur d'environnement. C'est précisément ce qui a arrêté le site.
    """
    fautes = []
    for nom in _fichiers_du_depot():
        if nom in GARDE_LOCALE:
            continue
        source = io.open(os.path.join(ICI, nom), encoding="utf-8").read()
        c = _Chercheur()
        c.visit(ast.parse(source))
        fautes += ["%s:%d" % (nom, l) for l in c.trouves]
    assert not fautes, (
        "lecture(s) numérique(s) d'environnement sans garde — une valeur mal "
        "saisie y arrête le service : " + ", ".join(fautes))


def test_la_regle_de_structure_voit_vraiment_la_faute():
    """Une règle qui ne verrait rien resterait verte sur un dépôt entier.

    On lui soumet la ligne exacte qui a cassé la production.
    """
    c = _Chercheur()
    c.visit(ast.parse('LISTE_MAX = int(os.environ.get("RAG_LISTE_MAX", "2000"))'))
    assert c.trouves == [1]
    c = _Chercheur()
    c.visit(ast.parse('X = float(os.getenv("Y") or 0)'))
    assert c.trouves == [1]
    c = _Chercheur()
    c.visit(ast.parse('X = reglages.entier("RAG_LISTE_MAX", 2000)'))
    assert c.trouves == []
