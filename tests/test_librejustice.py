# -*- coding: utf-8 -*-
"""L'ANALYSE JURIDIQUE S'INTERDISAIT LA JURISPRUDENCE FAUTE DE POUVOIR LA VÉRIFIER.

CE QUI A DÉCLENCHÉ CE FICHIER. `SYSTEM_JURIDIQUE` porte une interdiction
absolue : « Ne cite JAMAIS de jurisprudence [...] par un numéro ou une date que
tu n'as pas sous les yeux ». Elle avait raison — un modèle produit un numéro de
pourvoi de la bonne forme sans effort, et le référentiel ne comptait ZÉRO
décision sur trente-trois textes. Brancher LibreJustice lève cette interdiction ;
la lever sans contrôle serait pire que de la garder.

CE QUE CES RÈGLES GARDENT, DANS L'ORDRE DE CE QUI FAIT MAL :

1. QUE LA LEVÉE SOIT CONDITIONNELLE. L'interdiction reste dans le système ;
   l'autorisation est dans le message, et seulement quand des décisions ont
   été rapportées. Une analyse sans corpus doit se comporter exactement comme
   avant ce module.
2. QUE LE CONTRÔLE SOIT FAIT CONTRE CE QUI A ÉTÉ MONTRÉ. Vérifier une citation
   contre le corpus entier ne vérifierait rien : le modèle n'a vu que six
   décisions, il ne peut en citer que six.
3. QUE LE CLIENT MCP FONCTIONNE VRAIMENT. Un client de protocole écrit et jamais
   exécuté est une intention. Ces règles montent un serveur MCP local et font
   parler le vrai module avec — poignée de main, session, flux d'événements,
   erreurs comprises.
4. QU'UNE PANNE DU CORPUS NE COÛTE RIEN À L'ANALYSE. Ni exception, ni délai
   payé à chaque question.
"""
import importlib
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import librejustice  # noqa: E402
import juridique      # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# UN SERVEUR MCP DE LABORATOIRE
# ═══════════════════════════════════════════════════════════════════════════
#
# Il parle le protocole pour de bon : JSON-RPC 2.0, poignée de main, session,
# et les DEUX formes de réponse que le transport « streamable HTTP » autorise
# pour une même requête (application/json et text/event-stream). C'est cette
# alternance qui casse les clients écrits pour un seul cas.

DECISIONS = [
    {"title": "Cour de cassation, Chambre commerciale, 22 octobre 1996",
     "url": "https://librejustice.fr/decision/cc-1996-10-22-93-18632",
     "jurisdiction": "Cour de cassation", "jurisdictionCode": "cc",
     "chamber": "COMMERCIALE", "date": "1996-10-22", "number": "93-18.632",
     "publication": "PUBLIE_BULLETIN", "solution": "CASSATION",
     "aiSummary": "Résumé rédigé par une machine — jamais citable comme la parole de la cour."},
    {"title": "Cour d'appel de Paris, pôle 5, 12 mars 2019",
     "url": "https://librejustice.fr/decision/ca-paris-2019-03-12",
     "jurisdiction": "Cour d'appel de Paris", "jurisdictionCode": "ca_paris",
     "chamber": "P5.C4", "date": "2019-03-12", "number": "17/09876",
     "solution": "INFIRMATION", "appellateFate": "INFIRMATION — cassée le 3 juin 2021",
     "snippet": "passage de correspondance, possiblement le moyen d'une partie"},
]


class _Poignee(BaseHTTPRequestHandler):
    journal = []          # tout ce que le serveur a reçu
    sse = False           # répondre en flux d'événements plutôt qu'en JSON
    statut = 200          # forcer un code d'erreur
    lenteur = 0.0         # simuler un corpus lent
    outils = ("search_decisions", "get_decision",
              "search_legal_texts", "get_legal_text")

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        corps = json.loads(self.rfile.read(n) or b"{}")
        type(self).journal.append({
            "methode": corps.get("method"),
            "params": corps.get("params"),
            "session": self.headers.get("Mcp-Session-Id"),
            "protocole": self.headers.get("MCP-Protocol-Version"),
            "autorisation": self.headers.get("Authorization"),
            "accept": self.headers.get("Accept"),
        })
        if type(self).lenteur:
            time.sleep(type(self).lenteur)
        if type(self).statut != 200:
            self.send_response(type(self).statut)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"non")
            return

        m = corps.get("method")
        if m == "notifications/initialized":
            self.send_response(202)
            self.end_headers()
            return

        if m == "initialize":
            res = {"protocolVersion": "2025-06-18", "capabilities": {},
                   "serverInfo": {"name": "librejustice-labo", "version": "0"}}
            self._repondre(corps.get("id"), res, session="SESSION-LABO-1")
            return
        if m == "tools/list":
            self._repondre(corps.get("id"),
                           {"tools": [{"name": n} for n in type(self).outils]})
            return
        if m == "tools/call":
            p = corps.get("params") or {}
            nom = p.get("name")
            if nom == "search_decisions":
                charge = {"results": DECISIONS[:p.get("arguments", {}).get("limit", 10)]}
            elif nom == "get_decision":
                charge = dict(DECISIONS[0])
                charge["text"] = "Texte intégral de la décision, seule source de ce qu'elle juge."
            elif nom == "search_legal_texts":
                charge = {"results": [{"title": "Code civil, article 1231-1",
                                       "url": "https://librejustice.fr/texte/code-civil/1231-1"}]}
            else:
                charge = {"title": "Code civil, article 1231-1", "text": "Le débiteur est condamné…"}
            self._repondre(corps.get("id"),
                           {"content": [{"type": "text",
                                         "text": json.dumps(charge, ensure_ascii=False)}]})
            return
        self._repondre(corps.get("id"), None,
                       erreur={"code": -32601, "message": "méthode inconnue"})

    def _repondre(self, ident, resultat, erreur=None, session=None):
        msg = {"jsonrpc": "2.0", "id": ident}
        if erreur:
            msg["error"] = erreur
        else:
            msg["result"] = resultat
        brut = json.dumps(msg, ensure_ascii=False)
        self.send_response(200)
        if session:
            self.send_header("Mcp-Session-Id", session)
        if type(self).sse:
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            # Une notification de progression D'ABORD : un client qui retient le
            # premier message au lieu du dernier se trompe de charge utile.
            self.wfile.write(b'data: {"jsonrpc":"2.0","method":"notifications/progress"}\n\n')
            self.wfile.write(("data: " + brut + "\n\n").encode("utf-8"))
        else:
            self.send_header("Content-Type", "application/json")
            corps = brut.encode("utf-8")
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)


@pytest.fixture
def corpus(monkeypatch):
    """Un serveur MCP joignable, et le module branché dessus."""
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Poignee)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    _Poignee.journal = []
    _Poignee.sse = False
    _Poignee.statut = 200
    _Poignee.lenteur = 0.0
    _Poignee.outils = ("search_decisions", "get_decision",
                       "search_legal_texts", "get_legal_text")
    monkeypatch.setattr(librejustice, "ENDPOINT",
                        "http://127.0.0.1:%d/mcp" % srv.server_address[1])
    monkeypatch.setattr(librejustice, "ACTIF", True)
    librejustice.oublier()
    yield _Poignee
    srv.shutdown()
    librejustice.oublier()


# ═══════════════════════════════════════════════════════════════════════════
# 1. LE CLIENT MCP PARLE VRAIMENT LE PROTOCOLE
# ═══════════════════════════════════════════════════════════════════════════

def test_la_poignee_de_main_se_fait_dans_l_ordre_du_protocole(corpus):
    r = librejustice.rechercher("clause limitative de responsabilité")
    assert r["ok"], r["motif"]
    methodes = [x["methode"] for x in corpus.journal]
    assert methodes[:4] == ["initialize", "notifications/initialized",
                            "tools/list", "tools/call"], methodes


def test_la_session_rendue_par_le_serveur_est_reprise_ensuite(corpus):
    """Un serveur qui ouvre une session la RÉCLAME sur les appels suivants. Un
    client qui ne renvoie pas l'en-tête marche en développement, contre un
    serveur qui ne l'exige pas, et tombe en production."""
    assert librejustice.rechercher("responsabilité du prestataire")["ok"]
    apres = [x for x in corpus.journal if x["methode"] == "tools/call"]
    assert apres, "aucun appel d'outil n'a été émis"
    assert apres[0]["session"] == "SESSION-LABO-1", (
        "l'identifiant de session n'est pas renvoyé : le serveur ouvrira une "
        "session neuve à chaque appel, ou refusera")


def test_le_client_lit_aussi_les_reponses_en_flux_d_evenements(corpus):
    """Le transport autorise les DEUX formes pour la même requête. Celle-ci est
    servie en text/event-stream, précédée d'une notification de progression :
    un client qui retient le premier message rend la notification."""
    corpus.sse = True
    r = librejustice.rechercher("faute lourde du transporteur")
    assert r["ok"], r["motif"]
    assert len(r["decisions"]) == 2, (
        "le flux d'événements n'a pas été décodé : %r" % r)


@pytest.mark.parametrize("accept", ["application/json", "text/event-stream"])
def test_le_client_annonce_accepter_les_deux_formes(corpus, accept):
    librejustice.rechercher("obligation essentielle")
    assert accept in (corpus.journal[0]["accept"] or ""), (
        "le client n'annonce pas accepter %s : le serveur peut refuser" % accept)


def test_les_decisions_sont_normalisees(corpus):
    d = librejustice.rechercher("clause limitative")["decisions"][0]
    assert d["numero"] == "93-18.632"
    assert d["juridiction"] == "Cour de cassation"
    assert d["chambre"] == "COMMERCIALE"
    assert d["url"].startswith("https://librejustice.fr/decision/")


def test_le_sort_en_appel_est_conserve(corpus):
    """« INFIRMATION — cassée » est l'information qui décide si l'on peut se
    prévaloir d'une décision. La perdre en route revient à citer comme autorité
    ce qui ne fait plus autorité."""
    d = [x for x in librejustice.rechercher("q")["decisions"] if x["url"].endswith("03-12")][0]
    assert "INFIRMATION" in d["sort"], (
        "le sort de la décision en appel n'est pas remonté : %r" % d)


def test_lire_une_decision_rend_son_texte_integral(corpus):
    r = librejustice.lire("https://librejustice.fr/decision/cc-1996-10-22-93-18632")
    assert r["ok"], r["motif"]
    assert "Texte intégral" in r["texte"]


def test_la_recherche_de_textes_passe_le_code_demande(corpus):
    librejustice.rechercher_texte("réparation du préjudice contractuel", code="code-civil")
    appel = [x for x in corpus.journal if x["methode"] == "tools/call"][0]
    assert appel["params"]["arguments"]["code"] == "code-civil"


def test_la_date_de_consultation_d_un_article_est_transmise(corpus):
    """« Le droit applicable dépend de la date d'appréciation » est une règle du
    module juridique. Servir la version du jour pour un litige de 2019 la
    contredit en silence."""
    librejustice.lire_texte(code="code-civil", article="1231-1", date="2019-05-01")
    appel = [x for x in corpus.journal if x["methode"] == "tools/call"][0]
    assert appel["params"]["arguments"]["date"] == "2019-05-01"


# ═══════════════════════════════════════════════════════════════════════════
# 2. UNE PANNE DU CORPUS NE COÛTE RIEN À L'ANALYSE
# ═══════════════════════════════════════════════════════════════════════════

def test_un_corpus_injoignable_ne_leve_pas(monkeypatch):
    monkeypatch.setattr(librejustice, "ENDPOINT", "http://127.0.0.1:9/mcp")
    monkeypatch.setattr(librejustice, "ACTIF", True)
    librejustice.oublier()
    r = librejustice.rechercher("n'importe quoi")
    assert r["ok"] is False and r["decisions"] == []
    assert r["motif"], "un échec sans motif ne se diagnostique pas"


def test_une_autorisation_refusee_nomme_oauth(corpus):
    """401 et « panne réseau » ne se soignent pas pareil : l'un se règle en
    posant un jeton, l'autre en attendant. Le motif doit les distinguer."""
    corpus.statut = 401
    r = librejustice.rechercher("question")
    assert r["ok"] is False
    assert "OAuth" in r["motif"] and "LIBREJUSTICE_TOKEN" in r["motif"], r["motif"]


def test_le_disjoncteur_cesse_d_appeler_apres_trois_echecs(corpus):
    """SANS LUI, L'UTILISATEUR PAIE LA PANNE À CHAQUE QUESTION. Un corpus qui ne
    répond plus ajoute son délai d'expiration à toutes les analyses suivantes."""
    corpus.statut = 500
    for _ in range(librejustice.ECHECS_AVANT_COUPURE):
        librejustice.rechercher("question %d" % time.time())
    avant = len(corpus.journal)
    for i in range(5):
        r = librejustice.rechercher("encore une autre question %d" % i)
        assert r["ok"] is False
    assert len(corpus.journal) == avant, (
        "%d appels ont encore été émis après la coupure"
        % (len(corpus.journal) - avant))


def test_le_disjoncteur_se_reouvre_quand_on_le_lui_demande(corpus):
    corpus.statut = 500
    for i in range(librejustice.ECHECS_AVANT_COUPURE):
        librejustice.rechercher("q%d" % i)
    corpus.statut = 200
    assert librejustice.disponible()["ok"], (
        "le disjoncteur ne se rouvre pas : le corpus reste écarté cinq minutes "
        "après être revenu")


def test_un_delai_depasse_est_un_motif_pas_une_exception(corpus, monkeypatch):
    corpus.lenteur = 1.5
    monkeypatch.setattr(librejustice, "DELAI_LECTURE", 0.3)
    r = librejustice.rechercher("question lente")
    assert r["ok"] is False and "délai" in r["motif"]


def test_un_outil_disparu_est_signale_pour_ce_qu_il_est(corpus):
    """« Le corpus n'expose plus search_decisions » et « rien trouvé » sont deux
    diagnostics opposés. Les confondre laisse une panne passer pour un silence
    de la jurisprudence."""
    corpus.outils = ("get_decision",)
    r = librejustice.rechercher("question")
    assert r["ok"] is False
    assert "search_decisions" in r["motif"], r["motif"]


def test_le_connecteur_se_desactive_par_variable_d_environnement(monkeypatch):
    monkeypatch.setattr(librejustice, "ACTIF", False)
    librejustice.oublier()
    r = librejustice.rechercher("question")
    assert r["ok"] is False and "désactiv" in r["motif"]


def test_deux_fois_la_meme_question_n_interroge_le_corpus_qu_une_fois(corpus):
    librejustice.rechercher("clause pénale et clause limitative")
    n = len([x for x in corpus.journal if x["methode"] == "tools/call"])
    librejustice.rechercher("clause pénale et clause limitative")
    assert len([x for x in corpus.journal if x["methode"] == "tools/call"]) == n, (
        "la question a été reposée au corpus : le cache ne sert à rien")


def test_un_echec_n_est_pas_mis_en_cache(corpus):
    """Mettre un échec en cache fige une panne pendant une heure. Le corpus
    revenu, l'application continuerait de répondre « indisponible »."""
    corpus.statut = 500
    librejustice.rechercher("question unique")
    corpus.statut = 200
    r = librejustice.rechercher("question unique")
    assert r["ok"], "l'échec précédent a été mémorisé : %r" % r["motif"]


# ═══════════════════════════════════════════════════════════════════════════
# 3. LA LEVÉE DE L'INTERDICTION EST CONDITIONNELLE
# ═══════════════════════════════════════════════════════════════════════════

def test_l_interdiction_generale_reste_dans_le_systeme():
    """ELLE EST LE DÉFAUT, ET DOIT LE RESTER. Le prompt système sert TOUTES les
    analyses, y compris celles où aucune décision n'a été rapportée — la plupart,
    tant que le corpus reste muet sur des textes de 2024."""
    s = juridique.SYSTEM_JURIDIQUE
    assert "Ne cite JAMAIS de jurisprudence" in s, (
        "l'interdiction a été retirée du prompt système : une analyse sans "
        "corpus peut de nouveau inventer un arrêt")


def test_l_autorisation_n_est_pas_dans_le_systeme():
    """Si la levée était écrite dans le système, elle vaudrait AUSSI pour les
    analyses sans décision rapportée — c'est-à-dire exactement là où elle est
    dangereuse."""
    assert "PEUX citer celles-ci" not in juridique.SYSTEM_JURIDIQUE, (
        "l'autorisation de citer est passée dans le prompt système : elle "
        "s'applique désormais même sans jurisprudence sous les yeux")


def test_sans_decision_le_message_ne_leve_rien():
    p = juridique.prompt_analyse("Notre plafond de responsabilité tient-il ?")
    assert "JURISPRUDENCE VÉRIFIÉE" not in p


def test_avec_des_decisions_le_message_les_met_sous_les_yeux():
    d = [librejustice.normaliser(x) for x in DECISIONS]
    p = juridique.prompt_analyse("Notre plafond tient-il ?", jurisprudence=d)
    assert "JURISPRUDENCE VÉRIFIÉE" in p
    assert "93-18.632" in p
    assert "https://librejustice.fr/decision/" in p


def test_l_apercu_est_transmis_marque_comme_non_citable():
    """UN APERÇU N'EST PAS UNE SOLUTION. Le passage qui a déclenché la
    correspondance peut être le moyen d'une partie, que la cour écarte trois
    paragraphes plus loin. Le transmettre sans le marquer invite au contresens."""
    d = [librejustice.normaliser(x) for x in DECISIONS]
    bloc = librejustice.bloc_prompt(d)
    assert "Résumé rédigé par une machine" in bloc, "l'aperçu n'est pas transmis"
    i = bloc.index("Résumé rédigé par une machine")
    entete = bloc[max(0, i - 120):i]
    assert "NON CITABLE" in entete, (
        "l'aperçu est transmis sans avertissement : il sera cité comme la "
        "position de la cour")


def test_le_bloc_dit_le_sort_de_la_decision():
    d = [librejustice.normaliser(x) for x in DECISIONS]
    bloc = librejustice.bloc_prompt(d)
    assert "SORT DE CETTE DÉCISION" in bloc and "cassée" in bloc


def test_le_bloc_est_vide_sans_decision():
    assert librejustice.bloc_prompt([]) == ""
    assert librejustice.bloc_prompt(None) == ""


def test_l_arbitrage_recoit_la_meme_matiere_que_l_analyse():
    """Une note d'arbitrage se lit en comité de direction. Il n'y a aucune raison
    qu'elle soit moins étayée qu'une analyse."""
    d = [librejustice.normaliser(x) for x in DECISIONS]
    p = juridique.prompt_arbitrage("Faut-il accepter le plafond proposé ?",
                                   jurisprudence=d)
    assert "JURISPRUDENCE VÉRIFIÉE" in p and "93-18.632" in p


# ═══════════════════════════════════════════════════════════════════════════
# 4. LE CONTRÔLE PORTE SUR CE QUI A ÉTÉ MONTRÉ
# ═══════════════════════════════════════════════════════════════════════════

def test_une_decision_montree_peut_etre_citee():
    d = [librejustice.normaliser(x) for x in DECISIONS]
    c = librejustice.verifier_jurisprudence(
        "Voir Cass. com., 22 octobre 1996, n° 93-18.632.", d)
    assert c["ok"], c["suspectes"]


@pytest.mark.parametrize("cite", [
    "n° 12-34.567",                       # forme d'un pourvoi
    "req. n° 449209",                     # forme d'un recours administratif
    "ECLI:FR:CCASS:2021:CO00456",         # identifiant européen
    "aff. C-311/18",                      # affaire de la CJUE
])
def test_une_decision_non_montree_est_signalee(cite):
    """C'EST LA RÈGLE QUI JUSTIFIE D'AVOIR LEVÉ L'INTERDICTION. On n'a pas rendu
    la citation libre : on l'a ouverte à une liste fermée, et il faut pouvoir
    dire quand le modèle en est sorti."""
    d = [librejustice.normaliser(x) for x in DECISIONS]
    c = librejustice.verifier_jurisprudence("Il résulte de %s que…" % cite, d)
    assert not c["ok"], "%s n'a pas été signalée alors qu'elle n'a pas été montrée" % cite


def test_sans_corpus_toute_decision_citee_est_suspecte():
    """L'interdiction n'a pas été levée pour cette analyse : un numéro de
    pourvoi qui apparaît quand même a forcément été fabriqué."""
    c = librejustice.verifier_jurisprudence("Cass. com. n° 09-11.841", [])
    assert not c["ok"] and c["montrees"] == 0


def test_la_ponctuation_du_numero_ne_fait_pas_echouer_le_controle():
    """« 93-18.632 » et « 93-18632 » désignent le même pourvoi. Un contrôle qui
    les distingue signale la décision qu'il a lui-même fournie."""
    d = [librejustice.normaliser(x) for x in DECISIONS]
    for forme in ("n° 93-18.632", "n° 93-18632"):
        assert librejustice.verifier_jurisprudence("Voir %s." % forme, d)["ok"], forme


def test_post_traiter_porte_le_controle_de_jurisprudence():
    d = [librejustice.normaliser(x) for x in DECISIONS]
    r = juridique.post_traiter("Voir n° 93-18.632 et n° 99-99.999.", None,
                               jurisprudence=d)
    assert "jurisprudence" in r
    assert r["jurisprudence"]["ok"] is False
    assert [x["cle"] for x in r["jurisprudence"]["suspectes"]] == ["9999999"]


def test_le_controle_des_textes_n_a_pas_ete_abime():
    """Le contrôle des références normatives existait avant ; l'ajout ne doit
    pas l'avoir remplacé."""
    r = juridique.post_traiter("Le règlement (UE) 2024/1689 et le règlement (UE) 2099/9999.")
    assert r["citations"]["ok"] is False
    assert [x["cle"] for x in r["citations"]["suspectes"]] == ["2099/9999"]


# ═══════════════════════════════════════════════════════════════════════════
# 5. LES POINTS D'INTERPRÉTATION SONT TOUS ADOSSÉS AU CORPUS
# ═══════════════════════════════════════════════════════════════════════════

def test_chaque_point_d_interpretation_a_sa_requete():
    """Huit controverses, huit requêtes. Une controverse ajoutée sans requête
    afficherait un onglet « jurisprudence » vide sans que rien ne le signale."""
    attendus = {c["id"] for c in juridique.CONTROVERSES}
    couverts = set(librejustice.REQUETES_CONTROVERSES)
    assert attendus <= couverts, (
        "point(s) d'interprétation sans requête de jurisprudence : %s"
        % ", ".join(sorted(attendus - couverts)))
    assert couverts <= attendus, (
        "requête(s) visant un point d'interprétation qui n'existe plus : %s"
        % ", ".join(sorted(couverts - attendus)))


def test_chaque_requete_dit_ce_qu_elle_vise():
    """SANS CE CHAMP, ON MENT. Aucune juridiction ne s'est prononcée sur
    l'article 25 de l'IA Act ; les décisions rendues portent sur la question
    voisine — qui répond d'un produit modifié. Montrer l'une pour l'autre sans
    le dire fait croire que le point est tranché."""
    for cid, spec in librejustice.REQUETES_CONTROVERSES.items():
        assert spec.get("vise", "").strip(), "%s ne dit pas ce qu'il vise" % cid
        assert len(spec["vise"]) > 60, (
            "%s : « %s » n'explique pas l'analogie" % (cid, spec["vise"]))
        assert spec.get("requete", "").strip(), "%s n'a pas de requête" % cid


def test_la_declaration_ne_porte_aucun_etat_qui_bouge():
    """L'UNE DES DEUX APPLICATIONS FIGE SA CONFIGURATION PAR PROCESSUS. Y verser
    « le corpus est écarté » ou « dernière réussite à 7h52 » afficherait pendant
    des heures un état constaté une seule fois, au démarrage."""
    d = librejustice.declaration()
    for volatil in ("motif", "coupe", "derniere_reussite", "outils", "jeton"):
        assert volatil not in d, (
            "declaration() porte « %s », qui change en cours d'exécution — figée "
            "dans une configuration, elle mentira" % volatil)
    assert d["source"] and d["couverture"] and d["reserve"]


def test_pour_controverse_marque_l_analogie(corpus):
    r = librejustice.pour_controverse("plafond-sanctions")
    assert r["ok"], r["motif"]
    assert r["analogie"] is True
    assert r["vise"]


def test_un_point_inconnu_ne_rend_pas_de_decisions_au_hasard(corpus):
    r = librejustice.pour_controverse("point-qui-n-existe-pas")
    assert r["ok"] is False and r["decisions"] == []
    assert len(corpus.journal) == 0, "le corpus a été interrogé pour rien"


def test_les_filtres_de_requete_sont_transmis(corpus):
    """La qualification responsable/sous-traitant se juge à la CJUE et à la
    CNIL. Interroger tout le corpus rendrait des décisions de baux."""
    librejustice.pour_controverse("rgpd-llm-role")
    appel = [x for x in corpus.journal if x["methode"] == "tools/call"][0]
    assert "CJUE" in appel["params"]["arguments"]["jurisdiction_type"]


# ═══════════════════════════════════════════════════════════════════════════
# 6. LE MODULE JURIDIQUE RESTE AUTONOME
# ═══════════════════════════════════════════════════════════════════════════

def test_juridique_s_importe_sans_le_connecteur(monkeypatch):
    """`juridique.py` est partagé à l'identique entre deux applications et sert
    aussi de brique isolée. Un import dur du connecteur le casserait là où il
    n'est pas déployé — et le casserait au chargement, pas à l'usage."""
    reel = librejustice
    monkeypatch.setitem(sys.modules, "librejustice", None)
    try:
        m = importlib.reload(juridique)
        assert m.librejustice is None
        p = m.prompt_analyse("question", jurisprudence=[{"titre": "x"}])
        assert "JURISPRUDENCE VÉRIFIÉE" not in p, (
            "sans connecteur, aucune levée d'interdiction ne doit passer")
        assert "jurisprudence" not in m.post_traiter("texte")
    finally:
        monkeypatch.undo()
        sys.modules["librejustice"] = reel
        importlib.reload(juridique)


def test_le_connecteur_n_ouvre_aucune_connexion_a_l_import(monkeypatch):
    """Un module qui joint un service externe au chargement fait payer ce
    service à chaque démarrage de worker, et fait échouer le démarrage quand le
    service est en panne."""
    appels = []
    monkeypatch.setattr(librejustice.requests, "post",
                        lambda *a, **k: appels.append(a) or (_ for _ in ()).throw(AssertionError))
    importlib.reload(librejustice)
    assert appels == []
    importlib.reload(juridique)
