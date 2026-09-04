# -*- coding: utf-8 -*-
"""LA VEILLE RENDAIT UNE PAGE VIDE PENDANT QUE LA BASE RÉPONDAIT.

LE CONSTAT, daté du 4 septembre 2026. `/api/veille` répondait 200 en huit
secondes avec un corps de 1489 octets — la page, aucun élément — alors qu'une
requête directe à la base aboutissait dans la seconde, sur 27 connexions
ouvertes pour 103 autorisées. Ni le réseau, ni la base, ni un plafond : le
POOL. Après un incident de connexion, psycopg_pool se met en retrait et refuse
d'en ouvrir de nouvelles pendant plusieurs minutes ; les demandes attendent
leur délai puis échouent.

CE QUI REND CE DÉFAUT PARTICULIER, ET C'EST TOUT L'ENSEIGNEMENT. Le remède
existait DÉJÀ dans la maison, écrit deux fois, documenté par le même incident :
`auth.py` et `rag_store.py` basculent sur une connexion directe quand le pool
ne rend pas la main. `automation.py` était le seul des trois à ne pas l'avoir —
et c'est exactement pourquoi lui seul se voyait. Les deux autres se repliaient
en silence (le journal le disait, sous une autre étiquette, dans les mêmes
minutes) ; la veille, elle, attendait son délai et rendait une liste vide.

DEUX MÉCANISMES, ET LES CONFONDRE LAISSE LE TROU.

  Le pool à UNE SEULE connexion (max_size=1) condamnait le processus : une
  connexion perdue, et plus aucune opération ne passait. Il en accepte trois,
  et valide la connexion avant de la servir.

  LE REPLI DIRECT est l'autre moitié, et la seule qui tienne quand le pool
  boude entièrement. Aucun élargissement ne remplace le fait de savoir s'en
  passer.

CES RÈGLES N'EXISTAIENT POUR AUCUN DES TROIS MAGASINS. Le repli avait été livré
deux fois sans filet — c'est pourquoi la dernière porte manquante n'a été vue
que par un utilisateur, sur la page publique, un an plus tard.
"""
import io
import os
import re
import sys
import time

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import automation  # noqa: E402

SRC = io.open(os.path.join(ICI, "automation.py"), encoding="utf-8").read()


# ── Doublures : aucune base, aucune socket ──────────────────────────────────

class _FauxCurseur:
    def __init__(self, lignes):
        self._lignes = lignes

    def fetchall(self):
        return self._lignes

    def fetchone(self):
        return self._lignes[0] if self._lignes else None


class _FausseConnexion:
    def __init__(self, lignes=()):
        self.lignes = list(lignes)
        self.executions = []
        self.fermee = False

    def execute(self, sql, params=None):
        self.executions.append(sql)
        return _FauxCurseur(self.lignes)

    def close(self):
        self.fermee = True


class _PoolQuiBoude:
    """Le pool de production observé : il ne rend jamais la main."""

    def __init__(self):
        self.demandes = 0

    def getconn(self, timeout=None):
        self.demandes += 1
        raise TimeoutError("PoolTimeout")

    def putconn(self, conn):
        raise AssertionError("putconn sur une connexion jamais obtenue")


class _PoolQuiRepond:
    def __init__(self, conn):
        self.conn = conn
        self.demandes = 0
        self.rendus = 0
        self.dernier_timeout = None

    def getconn(self, timeout=None):
        self.demandes += 1
        self.dernier_timeout = timeout
        return self.conn

    def putconn(self, conn):
        self.rendus += 1


def _etat(pool=None, dsn="postgresql://exemple/base"):
    """Un _State assemblé à la main : __init__ ouvrirait une vraie connexion."""
    s = automation._State.__new__(automation._State)
    s._mem = {}
    s._pool = pool
    s._dsn = dsn
    s.replis_directs = 0
    s._pool_ko_jusqu = 0.0
    return s


@pytest.fixture
def direct(monkeypatch):
    """Remplace psycopg.connect : renvoie une connexion factice et la compte."""
    import psycopg
    ouvertes = []

    def _connect(dsn, **kw):
        c = _FausseConnexion(ouvertes and ouvertes[0].lignes or [])
        ouvertes.append(c)
        return c
    monkeypatch.setattr(psycopg, "connect", _connect)
    return ouvertes


# ── 1. Ce que le code ne fait plus ──────────────────────────────────────────

def test_aucune_operation_ne_passe_plus_directement_par_le_pool():
    """L'entonnoir est `_conn`. Une opération qui court-circuite le pool
    directement n'a pas de repli, et c'est celle-là qui rendra la page vide."""
    restes = re.findall(r"self\._pool\.connection\(\)", SRC)
    assert not restes, (
        "%d opération(s) passent encore par self._pool.connection() : elles "
        "n'ont aucun repli quand le pool boude" % len(restes))


def test_chaque_lecture_de_la_base_est_gardee_par_le_dsn_et_non_par_le_pool():
    """LE DÉFAUT DE FOND. Tant que la condition était « si j'ai un pool », un
    pool non construit condamnait l'état à la mémoire pour toute la vie du
    processus — alors que la base était joignable en direct."""
    assert "if self._pool:" not in SRC, (
        "une méthode conditionne encore l'accès à la base à l'existence du "
        "pool : sans pool, elle retombe en mémoire au lieu d'aller en direct"
    )
    assert SRC.count("if self._dsn:") >= 4, (
        "les méthodes de lecture/écriture ne se gardent plus sur le DSN")


def test_le_pool_n_est_plus_limite_a_une_seule_connexion():
    """max_size=1 : une connexion perdue, et le processus entier n'a plus
    d'accès à la base jusqu'à son redémarrage."""
    bloc = SRC[SRC.index("ConnectionPool("):][:400]
    m = re.search(r"max_size=(\d+)", bloc)
    assert m and int(m.group(1)) >= 2, bloc[:200]


def test_la_connexion_est_validee_avant_d_etre_servie():
    """Sans `check`, une connexion morte est distribuée telle quelle."""
    bloc = SRC[SRC.index("ConnectionPool("):][:400]
    assert "check=" in bloc, bloc[:200]


# ── 2. Le repli, éprouvé et non déclaré ─────────────────────────────────────

def test_quand_le_pool_ne_repond_pas_on_ouvre_une_connexion_directe(direct):
    pool = _PoolQuiBoude()
    s = _etat(pool)
    with s._conn() as c:
        c.execute("SELECT 1")
    assert pool.demandes == 1, "le pool n'a pas même été sollicité"
    assert len(direct) == 1, "aucune connexion directe n'a été ouverte"
    assert direct[0].fermee, "la connexion directe n'a pas été refermée"
    assert s.replis_directs == 1


def test_LA_VEILLE_REND_SES_LIGNES_MEME_QUAND_LE_POOL_BOUDE(monkeypatch):
    """LA RÈGLE QUI AURAIT ÉVITÉ TOUT CECI. Le reste décrit un mécanisme ;
    celle-ci décrit ce que l'utilisateur a vu — une page de veille vide alors
    que la base contenait ses éléments."""
    import psycopg
    lignes = [("g1", "CERT-FR", "Titre", "https://exemple/1", 1000, "résumé")]
    conn = _FausseConnexion(lignes)
    monkeypatch.setattr(psycopg, "connect", lambda dsn, **kw: conn)
    s = _etat(_PoolQuiBoude())
    items = s.veille_list(limit=10)
    assert items and items[0]["title"] == "Titre", (
        "la veille rend une liste vide alors que la base répond : c'est "
        "exactement le défaut du 3 septembre")


def test_apres_un_echec_le_pool_n_est_plus_sollicite_pendant_la_grace(direct):
    """Sans période de grâce, chaque opération repaie l'attente : une page
    composée de plusieurs requêtes dépasse le délai du navigateur — le repli
    fonctionne, mais trop tard pour servir à quelque chose."""
    pool = _PoolQuiBoude()
    s = _etat(pool)
    for _ in range(3):
        with s._conn() as c:
            c.execute("SELECT 1")
    assert pool.demandes == 1, (
        "le pool a été sollicité %d fois : la période de grâce ne joue pas"
        % pool.demandes)
    assert s.replis_directs == 3


def test_la_grace_finit_par_expirer(direct):
    """Une grâce qui ne s'éteint jamais transformerait un incident passager en
    connexion directe définitive."""
    pool = _PoolQuiBoude()
    s = _etat(pool)
    with s._conn() as c:
        c.execute("SELECT 1")
    s._pool_ko_jusqu = time.time() - 1
    with s._conn() as c:
        c.execute("SELECT 1")
    assert pool.demandes == 2


def test_l_attente_d_acquisition_est_courte():
    """Un pool en bonne santé répond en millisecondes. Attendre huit secondes
    avant de basculer, c'est le défaut qu'on corrige, pas le remède."""
    assert automation._State.POOL_ACQUIS_S <= 2.0
    assert automation._State.POOL_GRACE_S >= 10.0


def test_le_delai_court_est_bien_celui_qui_est_passe_au_pool():
    """Une constante que personne ne lit ne protège de rien."""
    pool = _PoolQuiRepond(_FausseConnexion())
    s = _etat(pool)
    with s._conn():
        pass
    assert pool.dernier_timeout == automation._State.POOL_ACQUIS_S


def test_la_connexion_du_pool_est_toujours_rendue():
    """Une connexion non rendue est exactement ce qui a vidé le pool."""
    pool = _PoolQuiRepond(_FausseConnexion())
    s = _etat(pool)
    with s._conn():
        pass
    assert pool.rendus == 1
    # Et même si l'opération échoue.
    with pytest.raises(ValueError):
        with s._conn():
            raise ValueError("erreur dans la requête")
    assert pool.rendus == 2


def test_un_pool_non_construit_ne_condamne_pas_la_base(direct):
    """psycopg_pool absent ou en échec : on va en direct, on ne bascule pas en
    mémoire. La base est joignable, l'état doit y rester."""
    s = _etat(pool=None)
    with s._conn() as c:
        c.execute("SELECT 1")
    assert len(direct) == 1


def test_sans_base_du_tout_l_etat_reste_en_memoire():
    """Le repli ultime, inchangé : sans DSN, aucune socket n'est ouverte."""
    s = _etat(pool=None, dsn=None)
    s.set("cle", "valeur")
    assert s.get("cle") == "valeur"
    assert s.veille_list() == []


# ── 3. Le démarrage, que les doublures ci-dessus contournent ────────────────

def test_au_demarrage_un_pool_impossible_ne_bascule_pas_en_memoire(monkeypatch):
    """LE CHEMIN QUI CONDAMNAIT LE PROCESSUS. La construction du pool et
    l'accès à la base étaient le même geste : un pool qui ne se construit pas
    renvoyait l'état en mémoire pour toute la vie du processus, alors que la
    base répondait."""
    import psycopg
    import psycopg_pool
    conn = _FausseConnexion()
    monkeypatch.setattr(psycopg_pool, "ConnectionPool",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("pool KO")))
    monkeypatch.setattr(psycopg, "connect", lambda dsn, **kw: conn)
    s = automation._State("postgresql://exemple/base")
    assert s._pool is None
    assert s._dsn, "la base a été abandonnée alors qu'elle répond en direct"
    assert any("CREATE TABLE" in x for x in conn.executions), (
        "le schéma n'a pas été créé par la connexion directe")


def test_au_demarrage_une_base_vraiment_injoignable_donne_la_memoire(monkeypatch):
    """Le repli ultime doit rester : ni pool, ni connexion directe, on sert
    quand même — en mémoire, et en le disant au journal."""
    import psycopg
    import psycopg_pool

    def _refus(*a, **k):
        raise RuntimeError("base injoignable")
    monkeypatch.setattr(psycopg_pool, "ConnectionPool", _refus)
    monkeypatch.setattr(psycopg, "connect", _refus)
    s = automation._State("postgresql://exemple/base")
    assert s._pool is None and s._dsn is None
    s.set("cle", "valeur")
    assert s.get("cle") == "valeur"


# ── 4. La propriété, sur tous les magasins à pool ───────────────────────────

def _modules_a_pool():
    """Tout module qui construit un pool. Relevé, jamais nommé : le prochain
    magasin écrit dans six mois doit tomber dans ce filet lui aussi."""
    out = []
    for nom in sorted(os.listdir(ICI)):
        if not nom.endswith(".py"):
            continue
        src = io.open(os.path.join(ICI, nom), encoding="utf-8").read()
        if "ConnectionPool(" in src:
            out.append((nom, src))
    return out


def _a_le_repli(src):
    return "getconn(timeout=" in src and "psycopg.connect(" in src


def test_le_releve_des_magasins_a_pool_trouve_bien_quelque_chose():
    """Une règle qui n'inspecte rien passe toujours."""
    assert len(_modules_a_pool()) >= 5


def test_les_trois_magasins_deja_repliables_le_restent():
    """auth et rag_store portaient déjà le remède ; automation les rejoint.
    Le leur retirer ramènerait l'incident, à l'identique."""
    for nom in ("auth.py", "rag_store.py", "automation.py"):
        src = io.open(os.path.join(ICI, nom), encoding="utf-8").read()
        assert _a_le_repli(src), (
            "%s a perdu son repli en connexion directe" % nom)


def test_le_nombre_de_magasins_SANS_repli_ne_grandit_pas():
    """CE QUE CETTE RÈGLE DIT, ET CE QU'ELLE NE DIT PAS.

    Quatre magasins n'ont toujours pas le repli — clients, livrables, cockpit
    et audit. Ce n'est pas un oubli de ce tour : c'est un constat, posé ici
    pour qu'il soit VU. Le corriger touche trente et un points d'appel sur des
    chemins de données sensibles (dont les fiches clients), et cela se décide,
    cela ne se glisse pas dans un correctif de veille.

    La règle interdit seulement que le compte AUGMENTE. Un magasin neuf qui
    naîtrait sans repli la ferait tomber — et c'est le seul moment où quelqu'un
    peut encore choisir en connaissance de cause.
    """
    sans = sorted(n for n, src in _modules_a_pool() if not _a_le_repli(src))
    assert len(sans) <= 4, (
        "un magasin de plus est né sans repli en connexion directe : %s" % sans)
