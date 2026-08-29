# -*- coding: utf-8 -*-
"""CHAQUE LIVRABLE ÉTAIT ÉCRIT SUR LA MOITIÉ DE CE QUE LA MAISON SAIT.

CE QUI A DÉCLENCHÉ CE FICHIER. CONSEILPREV et CONSEILPREV Cyber tiennent chacun
sa base : le droit du numérique et l'IA d'un côté, l'ingénierie des centres de
données et la cybersécurité industrielle de l'autre. Une analyse juridique sur
la sécurité d'un système industriel puisait dans la première et ignorait la
seconde, alors que la matière y était.

CE QUE CES RÈGLES GARDENT, DANS L'ORDRE DE CE QUI FAIT MAL :

1. QUE LA FUSION SE FASSE PAR RANG, JAMAIS PAR SCORE. Les deux moteurs ne
   mesurent pas la même chose ; trier sur leurs valeurs classerait par
   générosité d'échelle, et la base au moteur le plus bavard occuperait tout le
   haut quelle que soit sa pertinence.
2. QUE CHAQUE FRAGMENT PORTE SA BASE, jusque dans le prompt et jusque dans les
   sources affichées. Un livrable reproduit les extraits MOT POUR MOT : sans
   cette mention, personne ne peut dire six mois plus tard d'où venait la
   phrase.
3. QU'AUCUN DOCUMENT INTERNE NE TRAVERSE. La limite est posée du côté qui sert :
   une restriction que l'appelant peut lever n'est pas une restriction.
4. QU'UNE PANNE DU PAIR NE COÛTE RIEN — ni exception, ni délai payé à chaque
   rédaction — ET QUE LE DOCUMENT LE DISE. Un livrable écrit sur une seule base
   aurait pu être différent.
"""
import re
import io
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import rag_federe  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# UN PAIR DE LABORATOIRE
# ═══════════════════════════════════════════════════════════════════════════

DISTANTS = [
    {"texte": "La segmentation en zones et conduits (IEC 62443) délimite les "
              "périmètres de sécurité d'une installation industrielle.",
     "document": "Guide 62443 — zones et conduits", "document_id": 41,
     "theme": "OT/ICS", "score": 0.91},
    {"texte": "Le PUE se mesure sur une année glissante, pas sur un point de "
              "fonctionnement nominal.",
     "document": "Note PUE — méthode", "document_id": 42,
     "theme": "Centres de données", "score": 0.77},
]


class _Pair(BaseHTTPRequestHandler):
    journal = []
    statut = 200
    lenteur = 0.0
    corps = None            # None = réponse normale

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        recu = json.loads(self.rfile.read(n) or b"{}")
        type(self).journal.append({"chemin": self.path, "corps": recu,
                                   "cle": self.headers.get("X-Rag-Cle")})
        if type(self).lenteur:
            time.sleep(type(self).lenteur)
        if type(self).statut != 200:
            self.send_response(type(self).statut)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":false}')
            return
        charge = (type(self).corps if type(self).corps is not None
                  else {"ok": True, "resultats": DISTANTS[:recu.get("top_k", 10)]})
        brut = json.dumps(charge, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(brut)))
        self.end_headers()
        self.wfile.write(brut)


@pytest.fixture
def pair(monkeypatch):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Pair)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    _Pair.journal = []
    _Pair.statut = 200
    _Pair.lenteur = 0.0
    _Pair.corps = None
    monkeypatch.setattr(rag_federe, "PAIR",
                        "http://127.0.0.1:%d" % srv.server_address[1])
    monkeypatch.setattr(rag_federe, "ACTIF", True)
    monkeypatch.setattr(rag_federe, "CLE", "cle-de-labo")
    monkeypatch.setattr(rag_federe, "NOM_PAIR", "CONSEILPREV Cyber")
    monkeypatch.setattr(rag_federe, "NOM_LOCAL", "CONSEILPREV")
    rag_federe.oublier()
    yield _Pair
    srv.shutdown()
    rag_federe.oublier()


LOCAUX = [
    {"texte": "L'article 32 du RGPD impose des mesures techniques adaptées au "
              "risque, sans en fixer la liste.",
     "document": "Note RGPD — sécurité", "document_id": 7, "score": 12.4},
    {"texte": "La directive NIS 2 rend l'organe de direction responsable de "
              "l'approbation des mesures de gestion du risque.",
     "document": "Fiche NIS 2", "document_id": 8, "score": 9.1},
]


# ── 1. L'INTERROGATION ───────────────────────────────────────────────────

def test_le_pair_est_interroge_et_ses_fragments_reviennent(pair):
    r = rag_federe.interroger("zones et conduits", k=8)
    assert r["ok"], r["motif"]
    assert len(r["fragments"]) == 2
    assert r["fragments"][0]["document"] == "Guide 62443 — zones et conduits"


def test_chaque_fragment_distant_porte_la_base_du_pair(pair):
    for f in rag_federe.interroger("pue", k=8)["fragments"]:
        assert f["base"] == "CONSEILPREV Cyber", (
            "un fragment revient sans sa maison : recopié dans un livrable, il "
            "sera indiscernable d'un fragment local")


def test_la_cle_partagee_est_transmise(pair):
    rag_federe.interroger("question", k=4)
    assert pair.journal[0]["cle"] == "cle-de-labo", (
        "la clé n'est pas envoyée : le pair refusera")


def test_le_chemin_interroge_est_celui_de_la_recherche(pair):
    rag_federe.interroger("question", k=4)
    assert pair.journal[0]["chemin"] == "/api/rag/search"


def test_le_pair_n_est_pas_interroge_sans_url(monkeypatch):
    monkeypatch.setattr(rag_federe, "PAIR", "")
    rag_federe.oublier()
    r = rag_federe.interroger("question")
    assert r["ok"] is False and "RAG_PAIR_URL" in r["motif"]


def test_la_federation_se_desactive_par_variable_d_environnement(monkeypatch):
    monkeypatch.setattr(rag_federe, "ACTIF", False)
    rag_federe.oublier()
    r = rag_federe.interroger("question")
    assert r["ok"] is False and "désactiv" in r["motif"]


# ── 2. LA PANNE NE COÛTE RIEN, ET SE DIAGNOSTIQUE ───────────────────────

def test_un_pair_injoignable_ne_leve_pas(monkeypatch):
    monkeypatch.setattr(rag_federe, "PAIR", "http://127.0.0.1:9")
    monkeypatch.setattr(rag_federe, "ACTIF", True)
    rag_federe.oublier()
    r = rag_federe.interroger("question")
    assert r["ok"] is False and r["fragments"] == []
    assert r["motif"], "un échec sans motif ne se diagnostique pas"


def test_un_refus_nomme_la_cle_et_non_le_reseau(pair):
    """403 et « panne » ne se soignent pas pareil : l'un se règle en posant la
    même clé des deux côtés, l'autre en attendant."""
    pair.statut = 403
    r = rag_federe.interroger("question")
    assert r["ok"] is False and "RAG_PAIR_CLE" in r["motif"], r["motif"]


def test_un_delai_depasse_est_un_motif_pas_une_exception(pair, monkeypatch):
    pair.lenteur = 1.5
    monkeypatch.setattr(rag_federe, "DELAI_LECTURE", 0.3)
    r = rag_federe.interroger("question lente")
    assert r["ok"] is False and "délai" in r["motif"]


def test_le_disjoncteur_cesse_d_appeler_apres_trois_echecs(pair):
    """SANS LUI, L'UTILISATEUR PAIE LA PANNE À CHAQUE LIVRABLE : un pair
    injoignable ajoute son délai d'expiration à toutes les rédactions."""
    pair.statut = 500
    for i in range(rag_federe.ECHECS_AVANT_COUPURE):
        rag_federe.interroger("q%d" % i)
    avant = len(pair.journal)
    for i in range(4):
        assert rag_federe.interroger("autre %d" % i)["ok"] is False
    assert len(pair.journal) == avant, (
        "%d appels encore émis après la coupure" % (len(pair.journal) - avant))


def test_une_reponse_illisible_est_signalee_pour_ce_qu_elle_est(pair):
    pair.corps = {"ok": True, "autre_chose": []}
    r = rag_federe.interroger("question")
    assert r["ok"] is False and "liste de résultats" in r["motif"]


def test_deux_fois_la_meme_requete_n_interroge_le_pair_qu_une_fois(pair):
    rag_federe.interroger("clause de sécurité", k=6)
    n = len(pair.journal)
    rag_federe.interroger("clause de sécurité", k=6)
    assert len(pair.journal) == n, "le cache ne sert à rien"


def test_un_echec_n_est_pas_mis_en_cache(pair):
    """Mettre un échec en cache fige la panne une heure : le pair revenu,
    l'application continuerait de rédiger sur une seule base."""
    pair.statut = 500
    rag_federe.interroger("question unique")
    pair.statut = 200
    assert rag_federe.interroger("question unique")["ok"]


# ── 3. LA FUSION EST FAITE PAR RANG ─────────────────────────────────────

def test_les_deux_bases_sont_representees(pair):
    r = rag_federe.chercher("sécurité industrielle", LOCAUX, k=4)
    bases = {f["base"] for f in r["fragments"]}
    assert bases == {"CONSEILPREV", "CONSEILPREV Cyber"}, bases
    assert r["n_local"] == 2 and r["n_pair"] == 2


def test_un_score_local_ecrasant_ne_chasse_pas_le_pair():
    """LA RÈGLE QUI JUSTIFIE LA FUSION PAR RANG. Les scores locaux valent ici
    plus de 12, les distants moins de 1 — deux échelles sans rapport. Un tri par
    score mettrait toute la base locale devant, quelle que soit la pertinence
    réelle des fragments distants."""
    locaux = [dict(x, base=rag_federe.NOM_LOCAL) for x in LOCAUX]
    distants = [dict(x, base="CONSEILPREV Cyber") for x in DISTANTS]
    fusion = rag_federe.fusionner(locaux, distants, k=4)
    attendu = [rag_federe.NOM_LOCAL, "CONSEILPREV Cyber"] * 2
    assert [f["base"] for f in fusion] == attendu, (
        "la fusion n'alterne pas : %s" % [(f["base"], f["score"]) for f in fusion])


def test_a_rang_egal_la_base_locale_passe_devant():
    """LES ÉGALITÉS SONT LA RÈGLE, PAS L'EXCEPTION : deux listes de même
    longueur donnent exactement les mêmes poids rang par rang. Les départager
    par ordre alphabétique de document laisserait le TITRE décider quelle
    maison parle en premier — un classement sans raison, et qui bougerait au
    premier document renommé."""
    locaux = [{"texte": "zzz dernier alphabétiquement", "document": "Zèbre",
               "base": rag_federe.NOM_LOCAL, "score": 1}]
    distants = [{"texte": "aaa premier alphabétiquement", "document": "Abécédaire",
                 "base": "CONSEILPREV Cyber", "score": 99}]
    fusion = rag_federe.fusionner(locaux, distants, k=2)
    assert fusion[0]["base"] == rag_federe.NOM_LOCAL, (
        "le titre a décidé de l'ordre : %s" % [f["document"] for f in fusion])


def test_un_fragment_connu_des_deux_bases_remonte_et_le_dit():
    """C'est le fragment sur lequel on peut le plus s'appuyer : les deux maisons
    le documentent."""
    commun = {"texte": "Le PUE se mesure sur une année glissante.",
              "document": "Note PUE", "score": 1.0}
    locaux = [dict(x, base="A") for x in LOCAUX] + [dict(commun, base="A")]
    distants = [dict(commun, base="B")] + [dict(x, base="B") for x in DISTANTS]
    fusion = rag_federe.fusionner(locaux, distants, k=5)
    partage = [f for f in fusion if f.get("deux_bases")]
    assert partage, "le fragment commun n'est pas signalé"
    assert "A" in partage[0]["base"] and "B" in partage[0]["base"]


def test_la_fusion_ne_rend_pas_deux_fois_le_meme_extrait():
    locaux = [dict(x, base="A") for x in LOCAUX]
    fusion = rag_federe.fusionner(locaux, [dict(x, base="B") for x in locaux], k=8)
    assert len(fusion) == len(LOCAUX)


def test_une_liste_distante_vide_laisse_les_locaux_intacts():
    locaux = [dict(x, base="A") for x in LOCAUX]
    fusion = rag_federe.fusionner(locaux, [], k=8)
    assert [f["document"] for f in fusion] == [x["document"] for x in LOCAUX]


def test_le_pair_muet_ne_prive_pas_la_redaction(monkeypatch):
    monkeypatch.setattr(rag_federe, "PAIR", "http://127.0.0.1:9")
    monkeypatch.setattr(rag_federe, "ACTIF", True)
    rag_federe.oublier()
    r = rag_federe.chercher("question", LOCAUX, k=4)
    assert len(r["fragments"]) == 2 and r["n_pair"] == 0
    assert r["pair_ok"] is False


# ── 4. LA PROVENANCE SURVIT AU PASSAGE ──────────────────────────────────

def test_le_bloc_de_prompt_nomme_la_base_de_chaque_extrait(pair):
    r = rag_federe.chercher("sécurité", LOCAUX, k=4)
    bloc = rag_federe.bloc_prompt(r["fragments"])
    # Chaque ligne d'en-tête nomme SA maison. On les relève une par une plutôt
    # que de chercher les noms dans le bloc entier : « CONSEILPREV » est une
    # sous-chaîne de « CONSEILPREV Cyber », et un test qui l'ignore se satisfait
    # de quatre extraits venus tous du même côté.
    entetes = [l.split(" — ")[-1] for l in bloc.splitlines() if l.startswith("[")]
    assert sorted(entetes) == ["CONSEILPREV", "CONSEILPREV",
                               "CONSEILPREV Cyber", "CONSEILPREV Cyber"], entetes
    for i in range(1, 5):
        assert "[%d]" % i in bloc


def test_les_sources_portent_la_base(pair):
    r = rag_federe.chercher("sécurité", LOCAUX, k=4)
    src = rag_federe.sources(r["fragments"])
    assert all(s["base"] for s in src)
    assert {s["base"] for s in src} == {"CONSEILPREV", "CONSEILPREV Cyber"}


def test_la_traduction_de_vocabulaire_preserve_la_base(pair):
    """Les deux applications nomment les champs différemment. La provenance ne
    doit pas se perdre dans la traduction — c'est précisément le moment où on
    l'oublierait."""
    r = rag_federe.chercher("sécurité", LOCAUX, k=4)
    for h in rag_federe.en_forme(r["fragments"], texte="content", titre="title",
                                 ident="doc_id"):
        assert h["base"], "un fragment traduit a perdu sa base"
        assert h["content"] and h["title"]


@pytest.mark.parametrize("champ_texte,champ_titre", [
    ("texte", "document"),          # vocabulaire CONSEILPREV
    ("content", "title"),           # vocabulaire CONSEILPREV Cyber
    ("chunk_text", "nom_fichier"),  # vocabulaire du magasin
    ("extrait", "titre"),           # vocabulaire de la couche Sentinel
])
def test_les_quatre_vocabulaires_sont_reconnus(champ_texte, champ_titre):
    """Aucune des deux maisons ne renomme ses champs pour ce module : il les
    reconnaît tous, sans quoi brancher la fédération demanderait de toucher des
    dizaines d'appels qui marchent."""
    f = rag_federe.canoniser({champ_texte: "un extrait", champ_titre: "un titre",
                              "score": 1}, "X")
    assert f and f["texte"] == "un extrait" and f["document"] == "un titre"


def test_un_nom_contenu_dans_l_autre_ne_fausse_pas_le_compte(monkeypatch):
    """LE PIÈGE QU'ON S'EST POSÉ SOI-MÊME, et les noms retenus le posent :
    « CONSEILPREV » est contenu dans « CONSEILPREV Cyber ». Un comptage par
    `in` classait chaque fragment distant comme local — un livrable écrit
    entièrement sur la base sœur annonçait quatre extraits maison. Le défaut a
    été trouvé pour de bon, et cette règle le tient fermé."""
    monkeypatch.setattr(rag_federe, "NOM_LOCAL", "MAISON")
    monkeypatch.setattr(rag_federe, "NOM_PAIR", "MAISON Cyber")
    assert rag_federe.bases_de({"base": "MAISON Cyber"}) == {"MAISON Cyber"}
    assert "MAISON" not in rag_federe.bases_de({"base": "MAISON Cyber"})
    # Le compte lui-même, sur une fusion fabriquée : deux fragments, un de
    # chaque maison, et le total doit être un partout.
    fusion = rag_federe.fusionner(
        [{"texte": "a", "document": "A", "base": "MAISON"}],
        [{"texte": "b", "document": "B", "base": "MAISON Cyber"}], k=4)
    n_local = sum(1 for f in fusion if "MAISON" in rag_federe.bases_de(f))
    n_pair = sum(1 for f in fusion if "MAISON Cyber" in rag_federe.bases_de(f))
    assert (n_local, n_pair) == (1, 1), (n_local, n_pair)


def test_un_fragment_des_deux_bases_compte_pour_les_deux():
    f = {"base": "CONSEILPREV + CONSEILPREV Cyber"}
    assert rag_federe.bases_de(f) == {"CONSEILPREV", "CONSEILPREV Cyber"}


def test_un_fragment_sans_texte_est_ecarte():
    assert rag_federe.canoniser({"document": "titre seul"}, "X") is None
    assert rag_federe.canoniser("pas un dictionnaire", "X") is None


# ── 5. LE DOCUMENT DIT SUR QUOI IL A ÉTÉ ÉCRIT ──────────────────────────

def test_la_mention_compte_les_deux_bases(pair):
    m = rag_federe.mention(rag_federe.chercher("sécurité", LOCAUX, k=4))
    assert "CONSEILPREV" in m and "CONSEILPREV Cyber" in m
    assert "2" in m


def test_la_mention_dit_quand_le_pair_n_a_pas_repondu(monkeypatch):
    """LA MENTION LA PLUS UTILE DES TROIS. Un livrable écrit sans une base
    aurait pu être différent, et le lecteur est le seul à pouvoir en décider.

    LA RÈGLE PORTE SUR LA PROPRIÉTÉ, PAS SUR UN MOT. Elle exigeait le mot
    « SEULE » — juste tant qu'il n'y avait que deux bases, faux dès qu'il y en
    a trois : on peut en avoir interrogé deux sur trois, et « seule » serait
    alors un mensonge. Ce qui doit tenir est que la base absente soit NOMMÉE et
    que la conséquence soit dite."""
    monkeypatch.setattr(rag_federe, "PAIR", "http://127.0.0.1:9")
    monkeypatch.setattr(rag_federe, "ACTIF", True)
    rag_federe.oublier()
    m = rag_federe.mention(rag_federe.chercher("question", LOCAUX, k=4))
    assert rag_federe.NOM_PAIR in m, "la base absente n'est pas nommée"
    assert "n'a pas pu être interrogée" in m
    assert "aurait pu être différent" in m


def test_la_mention_distingue_le_pair_muet_du_pair_absent(pair):
    """« Interrogée, elle n'a rien rendu » et « injoignable » ne se soignent pas
    pareil, et ne se lisent pas pareil dans un document."""
    pair.corps = {"ok": True, "resultats": []}
    m = rag_federe.mention(rag_federe.chercher("sujet inconnu", LOCAUX, k=4))
    assert "n'a rien rendu" in m
    assert "n'a pas pu être interrogée" not in m, (
        "une base muette est présentée comme injoignable : les deux ne se "
        "soignent pas pareil")


def test_une_cle_accentuee_est_refusee_avec_son_motif(pair, monkeypatch):
    """UN EN-TÊTE HTTP NE TRANSPORTE QUE DE L'ASCII, et la bibliothèque lève à
    l'envoi. Ce module promet de ne jamais laisser passer d'exception vers la
    rédaction : une clé mal choisie doit donc rendre un MOTIF, pas planter le
    livrable. Et le motif doit dire quoi corriger — « erreur d'encodage »
    enverrait chercher du côté du réseau."""
    monkeypatch.setattr(rag_federe, "CLE", "clé-secrète")
    rag_federe.oublier()
    r = rag_federe.interroger("question")
    assert r["ok"] is False
    assert "non ASCII" in r["motif"] and "hexadécimale" in r["motif"], r["motif"]
    assert not pair.journal, (
        "l'appel a été tenté malgré une clé inutilisable : le délai est payé "
        "pour rien")


def test_une_cle_ascii_ordinaire_passe(pair, monkeypatch):
    monkeypatch.setattr(rag_federe, "CLE", "a3f9c2d1e8b7")
    rag_federe.oublier()
    assert rag_federe.interroger("question")["ok"]
    assert pair.journal[0]["cle"] == "a3f9c2d1e8b7"


def test_l_en_tete_du_connecteur_passe_le_filtre_anti_robot():
    """LA PANNE QUI SERAIT RESTÉE MUETTE. Ce site bloque les robots par leur
    en-tête d'agent et répond 404 pour ne pas révéler le blocage. Un connecteur
    dont l'agent tomberait sur la liste noire recevrait donc « le pair a répondu
    404 » — un diagnostic qui envoie chercher une route absente — et chaque
    livrable serait rédigé sur une seule base sans que personne ne sache
    pourquoi.

    Vérifié pour de bon lors du branchement : `curl` est sur la liste, et le
    premier essai a bien été bloqué. L'agent du connecteur, lui, passe — cette
    règle le maintient tel, et attrapera la règle trop large qu'on ajoutera un
    jour."""
    src = io.open(rag_federe.__file__, encoding='utf-8').read()
    m = re.search(r'"User-Agent":\s*"([^"]+)"', src)
    assert m, "le connecteur n'annonce aucun agent : un agent vide est bloqué"
    agent = m.group(1)
    import app  # noqa: E402
    filtre = getattr(app, 'is_bot_blocked', None)
    if filtre is None:
        # LE FICHIER EST PARTAGÉ PAR LES DEUX APPLICATIONS et une seule porte ce
        # filtre. On saute plutôt que d'inventer une vérification : ici, le
        # filtre est chez le PAIR, et c'est sa copie de cette règle qui le garde.
        pytest.skip("cette application n'a pas de filtre anti-robot par agent ; "
                    "la règle est tenue par la copie du dépôt qui en a un")
    assert not filtre(agent), (
        "l'agent « %s » est sur la liste noire : la fédération recevra des 404 "
        "et se taira" % agent)
    assert len(agent) >= 10, (
        "un agent de moins de dix caractères est écarté par le contrôle de "
        "moisson : « %s »" % agent)


def test_sans_aucun_extrait_la_mention_le_dit():
    assert "Aucun extrait" in rag_federe.mention(
        {"n_local": 0, "n_pair": 0, "pair_ok": True, "motif": ""})


# ══════════════════════════════════════════════════════════════════════════
#  6. TROIS BASES — la maison en compte plus de deux
# ══════════════════════════════════════════════════════════════════════════
# CE QUI CHANGE AVEC LE TROISIÈME PAIR, et qu'aucune règle ne couvrait :
#
#   · un disjoncteur PARTAGÉ ferait qu'une base en panne écarte les autres —
#     la panne d'un pair coûterait la fédération entière, ce que le
#     disjoncteur existe précisément pour éviter ;
#   · un cache clé sur la seule requête servirait la réponse d'une base pour
#     une autre. C'est le défaut le plus difficile à voir de toute cette
#     mécanique, puisque le résultat resterait plausible ;
#   · les égalités de rang sont la RÈGLE avec des listes de même longueur :
#     il faut un ordre déclaré, sinon la même rédaction rend deux ordres
#     différents à deux minutes d'intervalle.


class _PairB(_Pair):
    """Un second pair, avec son propre journal et son propre corps."""
    journal = []
    statut = 200
    lenteur = 0.0
    corps = None


@pytest.fixture
def trois_bases(monkeypatch):
    """Un local et DEUX pairs, chacun avec son serveur et sa clé."""
    srvs, ports = [], []
    for cls in (_Pair, _PairB):
        s = ThreadingHTTPServer(("127.0.0.1", 0), cls)
        threading.Thread(target=s.serve_forever, daemon=True).start()
        cls.journal = []
        cls.statut = 200
        cls.lenteur = 0.0
        cls.corps = None
        srvs.append(s)
        ports.append(s.server_address[1])
    monkeypatch.setattr(rag_federe, "PAIR", "http://127.0.0.1:%d" % ports[0])
    monkeypatch.setattr(rag_federe, "CLE", "cle-un")
    monkeypatch.setattr(rag_federe, "NOM_PAIR", "CONSEILPREV Cyber")
    monkeypatch.setattr(rag_federe, "NOM_LOCAL", "CONSEILPREV")
    monkeypatch.setattr(rag_federe, "ACTIF", True)
    monkeypatch.setattr(rag_federe, "PAIRS_SUP",
                        [{"nom": "CONSEILPREV IA",
                          "url": "http://127.0.0.1:%d" % ports[1],
                          "cle": "cle-deux"}])
    rag_federe.oublier()
    yield {"a": _Pair, "b": _PairB, "ports": ports}
    for s in srvs:
        s.shutdown()
    rag_federe.oublier()


def test_les_trois_bases_sont_declarees_et_ordonnees(trois_bases):
    noms = [p["nom"] for p in rag_federe.pairs()]
    assert noms == ["CONSEILPREV Cyber", "CONSEILPREV IA"]
    assert rag_federe.configure() is True
    assert rag_federe.etat()["n_pairs"] == 2


def test_chaque_pair_recoit_sa_propre_cle(trois_bases):
    """UNE CLÉ PAR PAIR. Une clé unique partagée par trois applications fait que
    la compromission d'une seule les ouvre toutes, et que la rotation de l'une
    oblige à redéployer les trois le même jour."""
    rag_federe.interroger_tous("question", k=4)
    assert trois_bases["a"].journal[-1]["cle"] == "cle-un"
    assert trois_bases["b"].journal[-1]["cle"] == "cle-deux"


def test_les_deux_pairs_sont_interroges_et_leurs_fragments_reviennent(trois_bases):
    r = rag_federe.chercher("zones et conduits", LOCAUX, k=8)
    bases = set()
    for f in r["fragments"]:
        bases |= rag_federe.bases_de(f)
    assert bases == {"CONSEILPREV", "CONSEILPREV Cyber", "CONSEILPREV IA"}
    assert r["par_base"]["CONSEILPREV IA"] > 0


def test_un_pair_en_panne_ne_prive_pas_des_autres(trois_bases, monkeypatch):
    """LA PROPRIÉTÉ QUI JUSTIFIE UN DISJONCTEUR PAR PAIR. Une base tombée ne
    doit coûter que ses documents — pas ceux des deux autres."""
    monkeypatch.setattr(rag_federe, "PAIRS_SUP",
                        [{"nom": "CONSEILPREV IA",
                          "url": "http://127.0.0.1:9", "cle": "cle-deux"}])
    rag_federe.oublier()
    r = rag_federe.chercher("question", LOCAUX, k=8)
    assert r["par_base"].get("CONSEILPREV Cyber", 0) > 0, (
        "la base qui répond a été écartée avec celle qui ne répond plus")
    assert "CONSEILPREV IA" in r["motifs"]
    m = rag_federe.mention(r)
    assert "CONSEILPREV IA" in m and "aurait pu être différent" in m


def test_le_disjoncteur_d_un_pair_n_ecarte_pas_les_autres(trois_bases, monkeypatch):
    monkeypatch.setattr(rag_federe, "PAIRS_SUP",
                        [{"nom": "CONSEILPREV IA",
                          "url": "http://127.0.0.1:9", "cle": "x"}])
    rag_federe.oublier()
    for i in range(rag_federe.ECHECS_AVANT_COUPURE + 1):
        rag_federe.interroger_tous("q%d" % i, k=2)
    par_pair = {p["nom"]: p for p in rag_federe.etat()["pairs"]}
    assert par_pair["CONSEILPREV IA"]["coupe"] is True
    assert par_pair["CONSEILPREV Cyber"]["coupe"] is False
    # Et la base saine répond toujours, disjoncteur de l'autre ouvert ou non.
    assert rag_federe.interroger_tous("encore", k=2)["ok"] is True


def test_le_cache_ne_sert_pas_la_reponse_d_une_base_pour_une_autre(trois_bases):
    """LE DÉFAUT LE PLUS DIFFICILE À VOIR DE TOUTE CETTE MÉCANIQUE. Une clé de
    cache portant la seule requête ferait servir la réponse du premier pair
    pour le second : le résultat resterait plausible, et rien ne signalerait
    que la seconde base n'a jamais été lue."""
    trois_bases["a"].corps = {"ok": True, "resultats": [
        {"texte": "réponse de la première base", "document": "A", "id": 1}]}
    trois_bases["b"].corps = {"ok": True, "resultats": [
        {"texte": "réponse de la seconde base", "document": "B", "id": 2}]}
    def textes_de(r):
        return {f["texte"] for liste in r["fragments"] for f in liste}

    attendu = {"réponse de la première base", "réponse de la seconde base"}
    assert textes_de(rag_federe.interroger_tous("même question", k=4)) == attendu
    assert len(trois_bases["a"].journal) == 1
    assert len(trois_bases["b"].journal) == 1

    # LE SECOND APPEL EST CELUI QUI COMPTE, et la première version de cette
    # règle ne le faisait pas. Les pairs étant interrogés EN PARALLÈLE, les
    # deux requêtes partent avant qu'aucune réponse ne soit mise en cache :
    # au premier tour, une clé de cache commune ne se voit pas. C'est au
    # second, quand les deux bases lisent la même entrée, que l'une se met à
    # servir la réponse de l'autre.
    assert textes_de(rag_federe.interroger_tous("même question", k=4)) == attendu
    assert len(trois_bases["a"].journal) == 1, "le cache du premier pair n'a pas servi"
    assert len(trois_bases["b"].journal) == 1, "le cache du second pair n'a pas servi"


def test_les_pairs_sont_interroges_en_parallele(trois_bases):
    """Trois pairs interrogés l'un après l'autre additionnent leurs délais. Sur
    un pair lent, la rédaction attendrait trois fois — et l'utilisateur paierait
    la lenteur de chacun."""
    trois_bases["a"].lenteur = 0.4
    trois_bases["b"].lenteur = 0.4
    t0 = time.time()
    rag_federe.interroger_tous("question", k=2)
    ecoule = time.time() - t0
    assert ecoule < 0.75, ("les pairs semblent interrogés en série : %.2f s "
                           "pour deux appels de 0,4 s" % ecoule)


def test_un_fragment_connu_des_trois_bases_le_dit(trois_bases):
    commun = {"texte": "Le même passage, partout.", "document": "Commun",
              "document_id": 42}
    f = rag_federe.fusionner_n([
        [dict(commun, base="CONSEILPREV")],
        [dict(commun, base="CONSEILPREV Cyber")],
        [dict(commun, base="CONSEILPREV IA")]], k=4)
    assert len(f) == 1, "le même extrait est rendu plusieurs fois"
    assert rag_federe.bases_de(f[0]) == {"CONSEILPREV", "CONSEILPREV Cyber",
                                         "CONSEILPREV IA"}


def test_a_rang_egal_l_ordre_des_bases_departage_et_reste_stable():
    """LES ÉGALITÉS SONT LA RÈGLE avec des listes de même longueur : chaque
    fragment vaut exactement le même poids rang par rang. Sans ordre déclaré,
    la même rédaction rendrait deux classements différents à deux minutes
    d'intervalle."""
    def frag(nom, base):
        return {"texte": "t" + nom, "document": nom, "document_id": nom,
                "base": base}
    listes = [[frag("zz", "CONSEILPREV")],
              [frag("aa", "CONSEILPREV Cyber")],
              [frag("mm", "CONSEILPREV IA")]]
    attendu = ["zz", "aa", "mm"]
    for _ in range(5):
        assert [f["document"] for f in
                rag_federe.fusionner_n(listes, k=5)] == attendu
    assert attendu != sorted(attendu), (
        "l'ordre de déclaration doit contredire l'ordre alphabétique, sans "
        "quoi un tri sur le titre passerait pour un ordre de bases")


def test_la_mention_nomme_chaque_base_absente(trois_bases, monkeypatch):
    monkeypatch.setattr(rag_federe, "PAIRS_SUP",
                        [{"nom": "CONSEILPREV IA",
                          "url": "http://127.0.0.1:9", "cle": "x"}])
    rag_federe.oublier()
    m = rag_federe.mention(rag_federe.chercher("question", LOCAUX, k=4))
    assert "CONSEILPREV IA" in m
    assert "CONSEILPREV" in m


def test_un_pair_declare_deux_fois_n_est_interroge_qu_une_fois(monkeypatch):
    """Une URL répétée entre `RAG_PAIR_URL` et `RAG_PAIR2_URL` doublerait le
    poids de cette base dans la fusion — elle apparaîtrait deux fois dans le
    classement, et paraîtrait deux fois plus sûre."""
    monkeypatch.setattr(rag_federe, "PAIR", "http://exemple.test")
    monkeypatch.setattr(rag_federe, "PAIRS_SUP",
                        [{"nom": "Doublon", "url": "http://exemple.test",
                          "cle": "x"}])
    assert [p["url"] for p in rag_federe.pairs()] == ["http://exemple.test"]
