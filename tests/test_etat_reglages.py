"""Un réglage ignoré ne doit pas être un réglage invisible.

CE QUE LE CORRECTIF PRÉCÉDENT A LAISSÉ OUVERT. Depuis `reglages.py`, une
variable illisible ne fait plus tomber le service : on retombe sur le défaut
et on l'écrit au journal. Mais les journaux de l'hébergeur sont éphémères et
personne ne les ouvre. L'exploitant croit sa valeur prise, elle ne l'est pas,
et rien à l'écran ne le contredit — on avait échangé une panne bruyante contre
un silence.

LA FRONTIÈRE QUE CES RÈGLES GARDENT. `/health` est PUBLIC : il publie des
CONSÉQUENCES et des nombres. La console d'administration, elle, nomme les
variables et donne le geste. Une extension distraite du premier vers le second
est exactement la faute que la règle `test_health_ne_nomme_aucune_variable`
existe pour arrêter.

ET DANS LES DEUX CAS, JAMAIS UNE VALEUR — y compris pour ce qui MANQUE : on
rend la commande qui fabrique une clé, jamais une clé.
"""
import ast
import io
import os

import pytest

from conftest import ADMIN_EMAIL

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

POISON = "7b8877af6257c0df78118046e5321a1f"


@pytest.fixture
def memoire_vierge(monkeypatch):
    """Une mémoire de refus propre : les modules en ont déjà rempli une."""
    import reglages
    monkeypatch.setattr(reglages, "_REFUSES", [])
    return reglages


# ── 1. Ce que la mémoire retient, et ce qu'elle ne retient jamais ──────────

def test_un_reglage_ecarte_est_retenu_avec_sa_forme_attendue(memoire_vierge, monkeypatch):
    monkeypatch.setenv("X_MEM", POISON)
    memoire_vierge.entier("X_MEM", 2000)
    retenus = memoire_vierge.refuses()
    assert [r["variable"] for r in retenus] == ["X_MEM"]
    assert retenus[0]["attendu"] == "un nombre entier"


def test_la_valeur_n_entre_jamais_dans_la_memoire(memoire_vierge, monkeypatch):
    """La règle du module, éprouvée sur sa NOUVELLE surface.

    Le journal ne montrait déjà pas la valeur. Une mémoire consultable depuis
    une page rouvrirait la même plaie si elle la portait : c'est par là que la
    clé de l'incident est partie dans les journaux de l'hébergeur.
    """
    monkeypatch.setenv("X_MEM", POISON)
    memoire_vierge.entier("X_MEM", 1)
    memoire_vierge.reel("X_MEM", 1.0)
    memoire_vierge.booleen("X_MEM", False)
    assert POISON not in repr(memoire_vierge.refuses())


def test_une_variable_absente_n_est_pas_retenue(memoire_vierge, monkeypatch):
    """Non renseigné n'est pas une faute — sinon la page listerait tout ce que
    l'exploitant n'a délibérément pas réglé, et ne serait plus lue."""
    monkeypatch.delenv("X_ABSENT", raising=False)
    memoire_vierge.entier("X_ABSENT", 5)
    assert memoire_vierge.refuses() == []


def test_une_variable_lue_deux_fois_ne_compte_qu_une_fois(memoire_vierge, monkeypatch):
    """Une lecture faite À L'APPEL se répète à chaque appel. Sans filtre, le
    compte publié mesurerait le trafic et non le nombre de réglages à
    corriger — et grimperait tout seul, ce qui ferait chercher une panne."""
    monkeypatch.setenv("X_MEM", POISON)
    for _ in range(5):
        memoire_vierge.entier("X_MEM", 1)
    assert len(memoire_vierge.refuses()) == 1


def test_la_memoire_rendue_ne_se_laisse_pas_modifier(memoire_vierge, monkeypatch):
    """`refuses()` rend des copies : un appelant qui trie ou vide sa liste ne
    doit pas effacer le diagnostic pour les suivants."""
    monkeypatch.setenv("X_MEM", POISON)
    memoire_vierge.entier("X_MEM", 1)
    memoire_vierge.refuses().clear()
    assert len(memoire_vierge.refuses()) == 1


# ── 2. /health : les conséquences, jamais les noms ─────────────────────────

# Les variables que CE chantier pourrait laisser fuir sur la page publique.
# `BREVO_API_KEY` n'y figure pas : elle est nommée par /health depuis bien
# avant, pour une autre fonction, et son absence s'observe de toute façon de
# l'extérieur en tentant une inscription. La règle garde la frontière que ce
# chantier ouvre, pas celles qu'il n'a pas créées.
VARIABLES_A_NE_PAS_PUBLIER = (
    "RAG_LISTE_MAX", "RAG_MAX_FILE_MB", "RAG_RECONNECT_INTERVAL", "DEPOT_MAX_MB",
    "CLAMAV_PORT", "AUDIT_MAX_ROWS", "AUDIT_RETENTION_JOURS", "AUTH_CACHE_TTL",
    "VEILLE_FULLTEXT_MAX", "ALERTES_COOLDOWN_MIN", "VEILLE_INTERVAL_HOURS",
    "CLIENTS_DOC_MAX_MB", "RECONNECT_MIN_S", "RECONNECT_MAX_S",
    "LLM_MAX_SIMULTANE", "EVENT_RETENTION_DAYS", "EVENT_MAX_ROWS",
    "MAINTENANCE_INTERVAL_HOURS", "FLASK_SECRET_KEY", "ADMIN_PASSWORD",
    "RAG_ACCESS_KEY",
)


def test_health_sans_cle_de_session_le_dit_et_se_declare_degrade(anonyme, monkeypatch):
    """Même critère que le courriel, déjà tenu par /health : totale ET
    silencieuse. Sans clé, chaque processus signe avec la sienne — il y en a
    deux, ils recyclent, et l'utilisateur est déconnecté par intermittence sans
    qu'aucun message ne le dise."""
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    j = anonyme.get("/health").get_json()
    assert j["sessions"] == "non persistantes"
    # ON NOMME LA CAUSE, ON NE REGARDE PAS LE DRAPEAU. Neuf contrôles peuvent
    # lever « degraded », et l'environnement d'essai en réunit déjà trois :
    # une règle qui ne lirait que `status` resterait verte même si ce
    # contrôle-ci disparaissait entièrement. Elle l'a d'ailleurs été.
    assert "sessions" in j["degrade_par"]
    assert j["status"] == "degraded"
    assert "déconnexions" in j["cause_sessions"]


def test_health_avec_cle_de_session_ne_degrade_pas_de_ce_fait(anonyme, monkeypatch):
    """Le pendant : une règle qui ne verrait que le manque resterait verte si
    le site se déclarait dégradé en permanence."""
    monkeypatch.setenv("FLASK_SECRET_KEY", "x" * 64)
    j = anonyme.get("/health").get_json()
    assert j["sessions"] == "persistantes"
    assert "sessions" not in j.get("degrade_par", [])
    assert "cause_sessions" not in j


def test_health_publie_un_compte_de_reglages_ecartes(anonyme, monkeypatch):
    import reglages
    monkeypatch.setattr(reglages, "refuses",
                        lambda: [{"variable": "RAG_LISTE_MAX", "attendu": "un nombre entier"},
                                 {"variable": "AUDIT_MAX_ROWS", "attendu": "un nombre entier"}])
    assert anonyme.get("/health").get_json()["reglages_ignores"] == 2


def test_health_ne_nomme_aucune_variable(anonyme, monkeypatch):
    """LA RÈGLE QUI GARDE LA FRONTIÈRE.

    /health est public. Publier le NOM d'un réglage écarté n'apprend rien à
    l'exploitant — qui a la console — et renseigne un tiers sur la
    configuration du service. Le compte suffit à faire ouvrir la console ; les
    noms restent derrière un compte administrateur.
    """
    import reglages
    monkeypatch.setattr(reglages, "refuses",
                        lambda: [{"variable": v, "attendu": "un nombre entier"}
                                 for v in VARIABLES_A_NE_PAS_PUBLIER])
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    corps = anonyme.get("/health").get_data(as_text=True)
    presents = [v for v in VARIABLES_A_NE_PAS_PUBLIER if v in corps]
    assert not presents, "nommées sur une page publique : " + ", ".join(presents)


def test_un_reglage_ecarte_ne_rend_pas_le_service_degrade(anonyme, monkeypatch):
    """« Dégradé » veut dire que le service ne rend pas le service. Un réglage
    écarté, c'est l'INTENTION de l'exploitant qui n'est pas appliquée — le site
    fonctionne, sur ses défauts. Confondre les deux userait le mot jusqu'à ce
    qu'il ne fasse plus lever personne."""
    import reglages
    monkeypatch.setenv("FLASK_SECRET_KEY", "x" * 64)
    monkeypatch.setattr(reglages, "refuses",
                        lambda: [{"variable": "RAG_LISTE_MAX", "attendu": "un nombre entier"}])
    j = anonyme.get("/health").get_json()
    assert j["reglages_ignores"] == 1
    assert "reglages" not in j.get("degrade_par", [])


# ── 3. La console : les noms, et le geste ─────────────────────────────────

def test_la_console_des_reglages_est_reservee_a_l_administrateur(anonyme, connecte):
    """Elle nomme des variables d'environnement : c'est précisément ce que la
    page publique s'interdit."""
    assert anonyme.get("/api/admin/reglages").status_code in (401, 403, 302)
    assert connecte.get("/api/admin/reglages").status_code in (401, 403, 302)


def test_la_console_nomme_les_reglages_ecartes_avec_le_geste(admin, monkeypatch):
    import reglages
    monkeypatch.setattr(reglages, "refuses",
                        lambda: [{"variable": "RAG_LISTE_MAX", "attendu": "un nombre entier"}])
    j = admin.get("/api/admin/reglages").get_json()
    ecarte = [e for e in j["ecartes"] if e["variable"] == "RAG_LISTE_MAX"]
    assert ecarte, "la console doit nommer ce que la page publique compte"
    assert ecarte[0]["attendu"] == "un nombre entier"
    assert ecarte[0]["geste"], "dire ce qui ne va pas sans dire quoi faire ne sert à rien"


def test_admin_password_est_signale_inerte_quand_le_compte_existe(admin, monkeypatch):
    """CE QUI REND CE CAS COÛTEUX : on croit avoir tourné un mot de passe qu'on
    n'a pas tourné. `_bootstrap_admin` rend la main dès que le compte existe,
    AVANT de lire la variable — qui reste alors en clair chez l'hébergeur, sans
    aucun usage."""
    import auth
    monkeypatch.setenv("ADMIN_PASSWORD", POISON)
    monkeypatch.setattr(auth, "ADMIN_EMAIL", ADMIN_EMAIL)
    j = admin.get("/api/admin/reglages").get_json()
    inerte = [e for e in j["inertes"] if e["variable"] == "ADMIN_PASSWORD"]
    assert inerte
    assert POISON not in repr(j)


def test_admin_password_n_est_pas_signale_quand_le_compte_n_existe_pas(admin, monkeypatch):
    """Elle sert alors RÉELLEMENT — elle crée le compte au premier démarrage.
    La signaler inerte enverrait supprimer la seule variable qui ouvre la
    porte, et c'est un piège dont on ne sort pas seul."""
    import auth
    monkeypatch.setenv("ADMIN_PASSWORD", POISON)
    monkeypatch.setattr(auth, "ADMIN_EMAIL", "personne@inexistant.test")
    j = admin.get("/api/admin/reglages").get_json()
    assert not [e for e in j["inertes"] if e["variable"] == "ADMIN_PASSWORD"]


def test_rag_access_key_est_signalee_inerte(admin, monkeypatch):
    monkeypatch.setenv("RAG_ACCESS_KEY", POISON)
    j = admin.get("/api/admin/reglages").get_json()
    assert [e for e in j["inertes"] if e["variable"] == "RAG_ACCESS_KEY"]
    assert POISON not in repr(j)


def test_la_mention_de_rag_access_key_se_retire_d_elle_meme(admin):
    """UNE AFFIRMATION QUI DOIT POUVOIR SE PÉRIMER TOUTE SEULE.

    La console affirme qu'aucun code ne lit `RAG_ACCESS_KEY`. Le jour où un
    module la lira, cette phrase deviendra fausse — et une console qui ment
    fait supprimer une variable qui sert. On ne se fie donc pas au souvenir :
    on relit l'arbre syntaxique du dépôt, et cette règle tombe le jour où
    l'affirmation cesse d'être vraie.
    """
    lue = []
    for nom in sorted(os.listdir(ICI)):
        if not nom.endswith(".py") or nom.startswith("test_"):
            continue
        arbre = ast.parse(io.open(os.path.join(ICI, nom), encoding="utf-8").read())
        # LE DIAGNOSTIC LUI-MÊME NOMME LA VARIABLE — c'est son travail. Ce
        # qu'on cherche, c'est une lecture qui lui donne un EFFET ailleurs.
        # Sans cette exception, la règle s'accuserait elle-même et ne dirait
        # plus rien du monde qu'elle est censée surveiller.
        diagnostic = [(n.lineno, n.end_lineno) for n in ast.walk(arbre)
                      if isinstance(n, ast.FunctionDef)
                      and n.name == "api_admin_reglages"]
        for n in ast.walk(arbre):
            if not isinstance(n, ast.Constant) or n.value != "RAG_ACCESS_KEY":
                continue
            if any(d <= n.lineno <= f for d, f in diagnostic):
                continue
            lue.append("%s:%d" % (nom, n.lineno))
    assert not lue, (
        "RAG_ACCESS_KEY est désormais lue en " + ", ".join(sorted(set(lue)))
        + " : retirez sa mention « inerte » de /api/admin/reglages")


def test_ce_qui_manque_rend_la_commande_et_jamais_la_cle(admin, monkeypatch):
    """La console dit comment fabriquer la clé ; elle ne la fabrique pas.

    Une clé engendrée par le serveur et affichée à l'écran aurait traversé un
    journal d'accès, un cache de navigateur et une capture d'écran avant
    d'arriver dans la case de l'hébergeur. C'est la faute exacte que ce
    chantier est né pour ne pas répéter.
    """
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    j = admin.get("/api/admin/reglages").get_json()
    manque = [e for e in j["absents"] if e["variable"] == "FLASK_SECRET_KEY"]
    assert manque
    assert "secrets" in manque[0]["geste"] and "token_hex" in manque[0]["geste"]
    assert manque[0]["reserve"], "la commande sans la mise en garde invite à la coller ici"


def test_la_console_se_tait_quand_tout_est_en_ordre(admin, monkeypatch):
    """Un panneau qui parle en permanence n'est plus lu le jour où il a quelque
    chose à dire."""
    import reglages
    monkeypatch.setattr(reglages, "refuses", lambda: [])
    monkeypatch.setenv("FLASK_SECRET_KEY", "x" * 64)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("RAG_ACCESS_KEY", raising=False)
    j = admin.get("/api/admin/reglages").get_json()
    assert j["total"] == 0


def test_le_diagnostic_des_modeles_est_reserve_a_l_administrateur(connecte):
    """Chaque essai DÉPENSE le crédit du compte de facturation. La borne par
    adresse freine un abus ; elle ne dit pas qui a le droit."""
    assert connecte.get("/api/assistant/selftest").status_code in (401, 403, 302)


def test_le_drapeau_degrade_nomme_toujours_sa_cause(anonyme):
    """L'invariant du marqueur : « dégradé » et « pourquoi » vont ensemble.

    Un contrôle ajouté demain qui lèverait le drapeau sans se nommer rendrait
    la liste incomplète — donc trompeuse, ce qui est pire que de ne pas
    l'avoir : on lirait « deux causes » là où il y en a trois.
    """
    j = anonyme.get("/health").get_json()
    if j["status"] == "degraded":
        assert j.get("degrade_par"), "dégradé sans dire par quoi"
    else:
        assert not j.get("degrade_par"), "une cause nommée sans drapeau levé"
