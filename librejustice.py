# -*- coding: utf-8 -*-
"""LIBREJUSTICE — LA JURISPRUDENCE QUI MANQUAIT À L'ANALYSE.

CE QUE CE MODULE DÉBLOQUE. Le référentiel de `juridique.py` compte trente-trois
textes documentés et ZÉRO décision de justice. Ce n'est pas un oubli : c'est une
règle écrite noir sur blanc dans SYSTEM_JURIDIQUE, et elle avait raison —

    « Ne cite JAMAIS de jurisprudence, de décision d'autorité ou de ligne
      directrice par un numéro ou une date que tu n'as pas sous les yeux. »

Un modèle à qui l'on demande une décision en invente une, et une décision
inventée est parfaitement crédible : une chambre, une date, un numéro de pourvoi
à la bonne forme. L'interdiction était la seule défense possible TANT QU'IL
N'Y AVAIT PAS DE CORPUS. Ce module fournit le corpus. L'interdiction ne tombe
pas pour autant : elle devient conditionnelle — le modèle peut citer les
décisions qu'il a SOUS LES YEUX, celles que ce module a rapportées, et aucune
autre. C'est `bloc_prompt()` qui les met sous ses yeux et
`verifier_jurisprudence()` qui vérifie ensuite qu'il n'en a pas ajouté.

COMMENT ON L'ATTEINT. LibreJustice expose un serveur MCP public sur
https://librejustice.fr/mcp. MCP n'est pas un protocole de plus : c'est du
JSON-RPC 2.0 sur HTTP, et un client tient en deux cents lignes. On n'ajoute donc
aucune dépendance — `requests`, déjà présent, suffit.

CE QUE CE MODULE NE FAIT PAS, ET POURQUOI. Il ne donne pas d'outils au modèle.
L'application appelle des outils MCP dépend du fournisseur (Claude et Mistral ne
les déclarent pas de la même façon) et surtout elle rend NON DÉTERMINISTE la
liste de ce que le modèle a consulté. On interroge donc le corpus AVANT, on
passe les décisions obtenues dans le message, et l'application sait exactement
lesquelles ont été montrées. C'est la condition du contrôle a posteriori : on ne
peut vérifier une citation contre une liste fermée que si la liste est fermée.

CE QUI N'A PAS PU ÊTRE VÉRIFIÉ D'ICI. L'accès anonyme. Le dépôt LibreJustice
annonce un serveur public en OAuth 2.1 avec enregistrement dynamique de client
— « aucune clé à configurer » — mais l'environnement d'où ce module a été écrit
ne joint pas librejustice.fr (le mandataire sortant refuse la connexion). Le
module est donc écrit pour les deux cas : il part sans jeton, et si le serveur
répond 401 il le DIT — `etat()['motif']` nomme alors OAuth au lieu de laisser
croire à une panne. Un jeton peut être fourni par LIBREJUSTICE_TOKEN.

UNE PANNE DU CORPUS NE DOIT JAMAIS BLOQUER UNE ANALYSE. Le conseil juridique
tient debout sans jurisprudence — il tenait debout avant ce module. Toute
fonction publique rend donc `{'ok': False, 'motif': ...}` au lieu de lever, le
délai est borné, et un disjoncteur coupe les tentatives après trois échecs
consécutifs : sans lui, un corpus injoignable ajouterait son délai d'expiration
à chaque analyse.
"""
import json
import os
import re
import threading
import time

import requests

# ═══════════════════════════════════════════════════════════════════════════
# 1. LA SOURCE, DÉCLARÉE
# ═══════════════════════════════════════════════════════════════════════════

SOURCE = "LibreJustice — https://librejustice.fr"
DEPOT = "https://github.com/librejustice/librejustice"
ENDPOINT = os.environ.get("LIBREJUSTICE_MCP", "https://librejustice.fr/mcp")
JETON = os.environ.get("LIBREJUSTICE_TOKEN", "").strip()
ACTIF = os.environ.get("LIBREJUSTICE", "1").strip().lower() not in ("0", "off", "non", "false")

# CE QUE LE CORPUS COUVRE. Écrit ici parce qu'un utilisateur qui ne trouve rien
# doit pouvoir distinguer « la question n'a pas de jurisprudence » de « cette
# juridiction n'est pas dans la base ».
COUVERTURE = (
    "Juridictions françaises (Cour de cassation, Conseil d'État, cours d'appel, "
    "tribunaux judiciaires, administratifs et des activités économiques), "
    "Conseil constitutionnel, CNDA, sanctions de la CNIL, CEDH et CJUE. "
    "Corpus construit sur les sources ouvertes (Judilibre, DILA/Légifrance, "
    "EUR-Lex) et mis à jour quotidiennement."
)

# LA RÉSERVE QUI ACCOMPAGNE CHAQUE DÉCISION RENDUE. Elle n'est pas décorative :
# une décision de cour d'appel citée sans son sort en cassation peut soutenir
# exactement l'inverse de ce qu'elle paraît dire.
RESERVE = (
    "Une décision ne vaut que par sa portée : vérifiez la formation, la "
    "publication et le sort de la décision en appel ou en cassation avant de "
    "vous en prévaloir. Une décision non publiée ne fait pas jurisprudence, et "
    "une décision cassée ne dit plus rien."
)

MENTION = ("Jurisprudence issue de LibreJustice (https://librejustice.fr), "
           "à partir des sources ouvertes Judilibre, DILA/Légifrance et EUR-Lex.")

# Délais. Une analyse juridique attend déjà un modèle ; elle n'attendra pas en
# plus un corpus lent. Ces valeurs sont des plafonds, pas des cibles.
DELAI_CONNEXION = 4
DELAI_LECTURE = 12
ECHECS_AVANT_COUPURE = 3
DUREE_COUPURE = 300          # secondes pendant lesquelles on cesse d'essayer
DUREE_CACHE = 3600           # une même question ne réinterroge pas le corpus

PROTOCOLE = "2025-06-18"

_OUTILS = ("search_decisions", "get_decision", "search_legal_texts", "get_legal_text")


# ═══════════════════════════════════════════════════════════════════════════
# 2. CLIENT MCP — JSON-RPC 2.0 SUR HTTP
# ═══════════════════════════════════════════════════════════════════════════
#
# Le transport « streamable HTTP » de MCP répond soit en application/json, soit
# en text/event-stream selon l'humeur du serveur pour une même requête. Les deux
# portent le même message JSON-RPC ; `_extraire` les ramène à un seul cas.

_verrou = threading.Lock()
_etat = {
    "session": None,        # identifiant de session MCP rendu par initialize
    "protocole": PROTOCOLE,
    "echecs": 0,
    "coupe_jusqu_a": 0.0,
    "motif": "",            # dernière raison d'échec, en clair
    "outils": (),           # outils réellement annoncés par le serveur
    "derniere_reussite": 0.0,
}
_cache = {}
_compteur = [0]


def _entetes():
    h = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": _etat["protocole"],
    }
    if _etat["session"]:
        h["Mcp-Session-Id"] = _etat["session"]
    if JETON:
        h["Authorization"] = "Bearer " + JETON
    return h


def _extraire(reponse):
    """Le message JSON-RPC, qu'il arrive seul ou dans un flux d'événements."""
    ctype = (reponse.headers.get("Content-Type") or "").lower()
    if "text/event-stream" in ctype:
        # On retient le DERNIER message porteur d'un résultat : un flux peut
        # commencer par des notifications de progression.
        dernier = None
        for ligne in reponse.text.splitlines():
            if not ligne.startswith("data:"):
                continue
            brut = ligne[5:].strip()
            if not brut or brut == "[DONE]":
                continue
            try:
                msg = json.loads(brut)
            except ValueError:
                continue
            if isinstance(msg, dict) and ("result" in msg or "error" in msg):
                dernier = msg
        return dernier
    try:
        return reponse.json()
    except ValueError:
        return None


def _appel(methode, params=None, notification=False):
    """Un aller-retour JSON-RPC. Rend (ok, resultat_ou_motif)."""
    _compteur[0] += 1
    corps = {"jsonrpc": "2.0", "method": methode}
    if params is not None:
        corps["params"] = params
    if not notification:
        corps["id"] = _compteur[0]
    try:
        r = requests.post(ENDPOINT, headers=_entetes(), json=corps,
                          timeout=(DELAI_CONNEXION, DELAI_LECTURE))
    except requests.exceptions.Timeout:
        return False, "le corpus n'a pas répondu dans le délai imparti"
    except requests.exceptions.RequestException as exc:
        return False, "corpus injoignable (%s)" % type(exc).__name__

    sid = r.headers.get("Mcp-Session-Id") or r.headers.get("mcp-session-id")
    if sid:
        _etat["session"] = sid

    if r.status_code == 401 or r.status_code == 403:
        # LE CAS QU'ON NE PEUT PAS DEVINER À L'AVANCE. Le dépôt annonce un accès
        # public ; si le serveur exige malgré tout un jeton, il faut le dire
        # précisément plutôt que de laisser croire à une panne réseau.
        return False, ("le corpus exige une autorisation OAuth : renseignez "
                       "LIBREJUSTICE_TOKEN (jeton porteur) — voir " + DEPOT)
    if r.status_code == 404 and _etat["session"]:
        # Session expirée côté serveur : on la jette, le prochain appel en
        # ouvrira une neuve.
        _etat["session"] = None
        return False, "session MCP expirée"
    if r.status_code >= 400:
        return False, "le corpus a répondu %d" % r.status_code
    if notification:
        return True, None

    msg = _extraire(r)
    if not isinstance(msg, dict):
        return False, "réponse du corpus illisible"
    if "error" in msg:
        err = msg["error"] or {}
        return False, "erreur du corpus : %s" % (err.get("message") or "sans motif")
    return True, msg.get("result")


def _ouvrir():
    """Poignée de main MCP. Le résultat est mémorisé : on ne réinitialise que
    lorsque la session tombe."""
    if _etat["session"] and _etat["outils"]:
        return True, None
    ok, res = _appel("initialize", {
        "protocolVersion": PROTOCOLE,
        "capabilities": {},
        "clientInfo": {"name": "conseilprev-juridique", "version": "1.0"},
    })
    if not ok:
        return False, res
    if isinstance(res, dict) and res.get("protocolVersion"):
        _etat["protocole"] = str(res["protocolVersion"])
    _appel("notifications/initialized", {}, notification=True)

    ok, res = _appel("tools/list")
    if not ok:
        return False, res
    noms = tuple(o.get("name") for o in (res or {}).get("tools", [])
                 if isinstance(o, dict))
    _etat["outils"] = noms
    manquants = [o for o in _OUTILS if o not in noms]
    if manquants:
        # UN SERVEUR QUI RÉPOND MAIS N'EXPOSE PLUS L'OUTIL ATTENDU. Le signaler
        # vaut mieux que d'appeler dans le vide et de rendre « aucun résultat » :
        # « rien trouvé » et « l'outil n'existe plus » ne se soignent pas pareil.
        return False, ("le corpus n'expose pas %s" % ", ".join(manquants))
    return True, None


def _outil(nom, arguments):
    """Appelle un outil MCP. Rend (ok, contenu_décodé_ou_motif)."""
    if not ACTIF:
        return False, "connecteur LibreJustice désactivé (LIBREJUSTICE=0)"
    with _verrou:
        if time.time() < _etat["coupe_jusqu_a"]:
            return False, _etat["motif"] or "corpus momentanément écarté"
        ok, motif = _ouvrir()
        if ok:
            ok, res = _appel("tools/call", {"name": nom, "arguments": arguments})
            if not ok:
                motif = res
        if not ok:
            _etat["echecs"] += 1
            _etat["motif"] = motif
            if _etat["echecs"] >= ECHECS_AVANT_COUPURE:
                # LE DISJONCTEUR. Sans lui, un corpus injoignable ajoute son
                # délai d'expiration à CHAQUE analyse — l'utilisateur paie la
                # panne autant de fois qu'il pose de questions.
                _etat["coupe_jusqu_a"] = time.time() + DUREE_COUPURE
            return False, motif
        _etat["echecs"] = 0
        _etat["motif"] = ""
        _etat["coupe_jusqu_a"] = 0.0
        _etat["derniere_reussite"] = time.time()
    return True, _contenu(res)


def _contenu(res):
    """Le contenu utile d'un résultat d'outil MCP.

    Un outil rend `content: [{type: 'text', text: '...'}]`, le texte portant
    presque toujours du JSON. On le décode quand c'est du JSON, on rend la
    chaîne sinon : un corpus qui change de forme de sortie ne doit pas faire
    tomber l'analyse."""
    if not isinstance(res, dict):
        return res
    if isinstance(res.get("structuredContent"), (dict, list)):
        return res["structuredContent"]
    morceaux = []
    for bloc in res.get("content") or []:
        if isinstance(bloc, dict) and bloc.get("type") == "text":
            morceaux.append(bloc.get("text") or "")
    texte = "\n".join(morceaux).strip()
    if not texte:
        return None
    try:
        return json.loads(texte)
    except ValueError:
        return texte


def _mem(cle, produire):
    """Cache à durée de vie. Deux analyses sur la même question n'interrogent
    le corpus qu'une fois."""
    maintenant = time.time()
    entree = _cache.get(cle)
    if entree and maintenant - entree[0] < DUREE_CACHE:
        return entree[1]
    valeur = produire()
    if valeur[0]:                     # on ne met en cache que les succès
        _cache[cle] = (maintenant, valeur)
    return valeur


def oublier():
    """Vide le cache et rouvre le disjoncteur. Utile après un changement de
    configuration, et employé par les contrôles."""
    with _verrou:
        _cache.clear()
        _etat.update({"session": None, "echecs": 0, "coupe_jusqu_a": 0.0,
                      "motif": "", "outils": ()})


# ═══════════════════════════════════════════════════════════════════════════
# 3. NORMALISATION DES DÉCISIONS
# ═══════════════════════════════════════════════════════════════════════════
#
# Le corpus rend ses champs dans sa forme à lui, et rien ne garantit qu'elle ne
# bougera pas. On ramène ce dont l'application a besoin — et RIEN DE PLUS : un
# aperçu (`snippet`, `aiSummary`) oriente une recherche, il ne dit pas ce que la
# décision juge, parce que le passage qui a déclenché la correspondance peut
# être l'argument d'une partie et non la solution de la cour.

CHAMPS_APERCU = ("aiSummary", "summary", "snippet", "extrait")


def _texte(x, *cles):
    for c in cles:
        v = x.get(c)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def normaliser(brut):
    """Une décision, dans la forme que l'application manipule."""
    if not isinstance(brut, dict):
        return None
    url = _texte(brut, "url", "link", "href")
    titre = _texte(brut, "title", "titre", "intitule")
    if not url and not titre:
        return None
    return {
        "titre": titre or url,
        "url": url,
        "juridiction": _texte(brut, "jurisdiction", "juridiction", "court"),
        "code_juridiction": _texte(brut, "jurisdictionCode", "jurisdiction_code"),
        "chambre": _texte(brut, "chamber", "chambre", "formation"),
        "date": _texte(brut, "date", "decisionDate", "dateDecision"),
        "numero": _texte(brut, "number", "numero", "docketNumber", "num"),
        "solution": _texte(brut, "solution", "outcome"),
        "publication": _texte(brut, "publication"),
        "sort": _texte(brut, "appellateFate", "appellate_fate"),
        "apercu": _texte(brut, *CHAMPS_APERCU),
        # L'APERÇU EST ÉTIQUETÉ COMME TEL. Un champ nommé « resume » finit un
        # jour cité comme la position de la cour ; « apercu » et le drapeau
        # ci-dessous rendent la confusion difficile.
        "apercu_non_citable": True,
    }


def _liste(res):
    """Le corpus peut rendre une liste, ou un objet qui la contient."""
    if isinstance(res, list):
        brut = res
    elif isinstance(res, dict):
        brut = None
        for c in ("results", "decisions", "hits", "items", "data"):
            if isinstance(res.get(c), list):
                brut = res[c]
                break
        if brut is None:
            brut = []
    else:
        return []
    out = []
    for x in brut:
        d = normaliser(x)
        if d:
            out.append(d)
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 4. INTERROGATION DU CORPUS
# ═══════════════════════════════════════════════════════════════════════════

FILTRES = ("jurisdiction_type", "jurisdiction_code", "chamber", "legal_domain",
           "legal_instrument", "legal_article", "date_from", "date_to",
           "publication", "solution", "procedure", "office", "sort", "mode")


def rechercher(question, limite=6, **filtres):
    """Décisions pertinentes pour une question, en français.

    Rend {'ok', 'decisions', 'motif', 'requete'}. `ok` faux n'est pas une
    exception : c'est un corpus injoignable, et l'analyse continue sans lui.
    Une liste VIDE avec ok=True est une réponse à part entière — elle dit que
    la question n'a pas (encore) de jurisprudence dans ce corpus, ce qui est
    exactement le cas des textes de 2024 et 2025."""
    q = (question or "").strip()[:512]
    if not q:
        return {"ok": False, "decisions": [], "motif": "question vide", "requete": ""}
    args = {"query": q, "limit": max(1, min(int(limite or 6), 20))}
    for c in FILTRES:
        v = filtres.get(c)
        if v not in (None, "", []):
            args[c] = v
    cle = ("search_decisions", json.dumps(args, sort_keys=True, ensure_ascii=False))

    def produire():
        ok, res = _outil("search_decisions", args)
        if not ok:
            return (False, res, [])
        return (True, "", _liste(res))

    ok, motif, decisions = _mem(cle, produire)
    return {"ok": ok, "decisions": decisions, "motif": motif, "requete": q}


def lire(url):
    """Le texte intégral d'une décision.

    C'est la SEULE source dont on puisse tirer ce qu'une décision juge. Un
    aperçu de recherche ne le dit pas : le passage qui a déclenché la
    correspondance peut être le moyen d'une partie, que la cour écarte trois
    paragraphes plus loin."""
    u = (url or "").strip()
    if not u:
        return {"ok": False, "motif": "url absente"}
    cle = ("get_decision", u)

    def produire():
        ok, res = _outil("get_decision", {"url": u})
        if not ok:
            return (False, res, None)
        return (True, "", res)

    ok, motif, res = _mem(cle, produire)
    if not ok:
        return {"ok": False, "motif": motif}
    d = normaliser(res) if isinstance(res, dict) else None
    texte = ""
    if isinstance(res, dict):
        texte = _texte(res, "text", "texte", "content", "fullText", "body")
    return {"ok": True, "decision": d, "texte": texte, "brut": res, "motif": ""}


def rechercher_texte(question, code=None, limite=6, date=None, jurisdiction=None):
    """Articles de code répondant à une description, quand le numéro est inconnu.

    Le référentiel de `juridique.py` porte les textes européens et les normes ;
    il ne porte AUCUN article de code français. C'est ce que cette fonction
    ajoute — et la raison pour laquelle une analyse contractuelle pouvait parler
    de responsabilité sans jamais citer l'article 1231-1 du code civil."""
    q = (question or "").strip()[:512]
    if not q:
        return {"ok": False, "articles": [], "motif": "question vide"}
    args = {"query": q, "limit": max(1, min(int(limite or 6), 20))}
    if code:
        args["code"] = code
    if date:
        args["date"] = date
    if jurisdiction:
        args["jurisdiction"] = jurisdiction
    cle = ("search_legal_texts", json.dumps(args, sort_keys=True, ensure_ascii=False))

    def produire():
        ok, res = _outil("search_legal_texts", args)
        if not ok:
            return (False, res, [])
        return (True, "", _liste(res))

    ok, motif, articles = _mem(cle, produire)
    return {"ok": ok, "articles": articles, "motif": motif}


def lire_texte(url=None, code=None, article=None, date=None):
    """Un article dans sa version en vigueur à une date.

    LA DATE N'EST PAS UN LUXE. `juridique.py` répète que « le droit applicable
    dépend de la date d'appréciation » ; un article servi dans sa version du
    jour pour un litige de 2023 contredit cette règle en silence."""
    args = {}
    if url:
        args["url"] = url
    if code:
        args["code"] = code
    if article:
        args["article"] = str(article).lower()
    if date:
        args["date"] = date
    if not args:
        return {"ok": False, "motif": "ni url ni code+article"}
    cle = ("get_legal_text", json.dumps(args, sort_keys=True, ensure_ascii=False))

    def produire():
        ok, res = _outil("get_legal_text", args)
        if not ok:
            return (False, res, None)
        return (True, "", res)

    ok, motif, res = _mem(cle, produire)
    return {"ok": ok, "article": res, "motif": motif}


def declaration():
    """Les faits CONSTANTS du connecteur : ce qu'il est, pas comment il va.

    Séparé d'`etat()` pour une raison précise. La configuration d'interface est
    figée par processus dans l'une des deux applications ; y verser `motif`,
    `coupe` ou `derniere_reussite` afficherait pendant des heures un état
    constaté au démarrage. Un état qui bouge ne se met pas dans ce qui ne bouge
    pas."""
    return {
        "actif": ACTIF,
        "source": SOURCE,
        "depot": DEPOT,
        "couverture": COUVERTURE,
        "reserve": RESERVE,
        "mention": MENTION,
    }


def etat():
    """Ce que le connecteur peut dire de lui-même, sans rien tenter."""
    return {
        "actif": ACTIF,
        "endpoint": ENDPOINT,
        "jeton": bool(JETON),
        "source": SOURCE,
        "depot": DEPOT,
        "couverture": COUVERTURE,
        "reserve": RESERVE,
        "mention": MENTION,
        "outils": list(_etat["outils"]),
        "coupe": time.time() < _etat["coupe_jusqu_a"],
        "motif": _etat["motif"],
        "derniere_reussite": _etat["derniere_reussite"] or None,
    }


def disponible():
    """Interroge réellement le corpus. À n'appeler que sur demande explicite —
    une page d'accueil qui teste une dépendance externe la teste à chaque
    visiteur."""
    ok, motif = (True, None)
    with _verrou:
        _etat["coupe_jusqu_a"] = 0.0
        _etat["echecs"] = 0
        ok, motif = _ouvrir()
    return {"ok": bool(ok), "motif": "" if ok else (motif or ""),
            "outils": list(_etat["outils"])}


# ═══════════════════════════════════════════════════════════════════════════
# 5. LES POINTS D'INTERPRÉTATION, ADOSSÉS AU CORPUS
# ═══════════════════════════════════════════════════════════════════════════
#
# `juridique.CONTROVERSES` pose huit questions ouvertes et en donne deux
# lectures. Aucune ne cite de décision, et pour une raison de fond : elles
# portent sur des textes de 2022 à 2024 dont le contentieux n'a pas commencé.
#
# CE QU'ON PEUT INTERROGER MALGRÉ TOUT. Sept de ces huit questions ont une
# QUESTION SOUS-JACENTE plus ancienne, elle abondamment jugée : qui répond d'un
# produit qu'on a modifié, ce qu'un plafond de responsabilité peut couvrir, quand
# une norme non obligatoire devient l'état de l'art opposable. Chaque requête
# ci-dessous vise cette question-là, et `vise` dit laquelle — pour qu'un lecteur
# sache qu'on lui montre un ANALOGUE et non une décision sur le texte lui-même.
#
# UNE RÉPONSE VIDE EST UNE RÉPONSE. Si le corpus ne rend rien, la controverse
# reste ce qu'elle est : deux lectures et un arbitrage. On n'ira pas chercher
# ailleurs une décision qui « ferait l'affaire ».

REQUETES_CONTROVERSES = {
    "ai-act-6-3": {
        "requete": "système automatisé d'aide à la décision en matière de "
                   "recrutement ou d'évaluation des salariés, portée réelle du "
                   "contrôle humain sur la décision finale",
        "vise": "L'article 6(3) écarte la qualification de haut risque quand le "
                "système n'influence pas de manière déterminante la décision. La "
                "même appréciation — l'humain décide-t-il encore ? — est jugée de "
                "longue date sur les décisions automatisées.",
        "filtres": {},
    },
    "ai-act-25-modif": {
        "requete": "celui qui modifie ou intègre un produit avant sa mise sur le "
                   "marché assume-t-il les obligations du fabricant",
        "vise": "L'article 25 fait basculer le déployeur en fournisseur par la "
                "modification substantielle. Le droit des produits juge depuis "
                "longtemps quand l'intégrateur devient producteur.",
        "filtres": {},
    },
    "nis2-chaine": {
        "requete": "manquement du prestataire informatique à son obligation de "
                   "sécurité, responsabilité après une intrusion ou un "
                   "rançongiciel chez le client",
        "vise": "L'article 21.2.d impose d'agir sur la chaîne d'approvisionnement "
                "sans dire comment. Ce que les juges retiennent déjà contre un "
                "prestataire dessine le contenu exigible.",
        "filtres": {},
    },
    "nis2-dirigeants": {
        "requete": "responsabilité personnelle du dirigeant pour un manquement "
                   "aux obligations de sécurité de la société, effet d'une "
                   "délégation de pouvoirs",
        "vise": "L'article 20 rend l'organe de direction responsable de "
                "l'approbation des mesures. La portée d'une délégation de "
                "pouvoirs est une question ancienne et tranchée.",
        "filtres": {},
    },
    "rgpd-llm-role": {
        "requete": "critère de distinction entre responsable de traitement et "
                   "sous-traitant, détermination des finalités et des moyens du "
                   "traitement",
        "vise": "La qualification du fournisseur de modèle se joue sur le critère "
                "de l'article 4(8) du RGPD, que la CJUE et la CNIL appliquent "
                "depuis des années à d'autres prestataires.",
        "filtres": {"jurisdiction_type": ["CJUE", "CNIL", "CE"]},
    },
    "cra-ai-act": {
        "requete": "marquage CE apposé sans évaluation de conformité régulière, "
                   "conséquences pour le fabricant et le distributeur",
        "vise": "La question du cumul CRA / IA Act est neuve ; celle de ce que "
                "vaut un marquage CE mal obtenu ne l'est pas.",
        "filtres": {},
    },
    "plafond-sanctions": {
        "requete": "clause limitative de responsabilité écartée en cas de faute "
                   "lourde ou de manquement à une obligation essentielle du contrat",
        "vise": "Avant de savoir si un plafond peut couvrir une amende "
                "administrative, il faut savoir quand un plafond tient. C'est la "
                "jurisprudence la mieux établie des huit.",
        "filtres": {"legal_instrument": ["code-civil"]},
    },
    "62443-opposabilite": {
        "requete": "opposabilité d'une norme technique non obligatoire, état de "
                   "l'art retenu pour apprécier la faute ou le défaut",
        "vise": "La 62443 n'est obligatoire nulle part. La question de savoir "
                "quand une norme volontaire devient le standard de diligence "
                "exigible est jugée en responsabilité comme en construction.",
        "filtres": {},
    },
}


def pour_controverse(cid, limite=4):
    """Décisions éclairant un point d'interprétation ouvert.

    Rend toujours `vise` : le lecteur doit savoir que la décision porte sur la
    question SOUS-JACENTE et non sur le texte de la controverse. Sans cette
    mention, on lui laisserait croire qu'un arrêt a tranché l'article 25 de
    l'IA Act — ce qu'aucun arrêt n'a fait à ce jour."""
    spec = REQUETES_CONTROVERSES.get(cid)
    if not spec:
        return {"ok": False, "decisions": [], "motif": "point d'interprétation inconnu",
                "vise": ""}
    r = rechercher(spec["requete"], limite=limite, **spec.get("filtres", {}))
    r["vise"] = spec["vise"]
    r["analogie"] = True
    return r


# ═══════════════════════════════════════════════════════════════════════════
# 6. CE QU'ON MET SOUS LES YEUX DU MODÈLE — ET CE QU'ON VÉRIFIE ENSUITE
# ═══════════════════════════════════════════════════════════════════════════

# LA CLAUSE QUI LÈVE L'INTERDICTION, ET SEULEMENT POUR CES DÉCISIONS-LÀ.
# SYSTEM_JURIDIQUE interdit de citer une décision. Cette interdiction reste le
# défaut : elle n'est levée que dans les analyses où des décisions ont
# effectivement été rapportées, et uniquement pour celles-ci. C'est pourquoi la
# levée est écrite dans le MESSAGE UTILISATEUR et non dans le système : un
# message sans jurisprudence ne la porte pas.
CONSIGNE = (
    "JURISPRUDENCE VÉRIFIÉE — ces décisions ont été rapportées du corpus "
    "LibreJustice et sont sous tes yeux. Par exception à la règle générale, tu "
    "PEUX citer celles-ci, et UNIQUEMENT celles-ci, par leur intitulé et leur "
    "numéro tels qu'ils figurent ci-dessous. Toute autre décision reste "
    "interdite. Règles de citation :\n"
    "  - n'écris jamais qu'une décision « juge que » sur la foi de l'aperçu : "
    "l'aperçu est un extrait de correspondance, qui peut être le moyen d'une "
    "partie et non la solution retenue ;\n"
    "  - indique la juridiction, la formation et la date ; signale une décision "
    "non publiée pour ce qu'elle est ;\n"
    "  - lorsque le sort en appel ou en cassation est indiqué, dis-le : une "
    "décision infirmée ne fonde rien ;\n"
    "  - ces décisions portent le plus souvent sur une question VOISINE et non "
    "sur le texte en cause — dis en quoi elle éclaire, ne présente pas "
    "l'analogie comme une solution acquise."
)


def bloc_prompt(decisions, vise=None):
    """Le bloc numéroté transmis au modèle. Vide si rien n'a été rapporté —
    et alors l'interdiction générale s'applique, telle quelle."""
    decisions = [d for d in (decisions or []) if d]
    if not decisions:
        return ""
    out = [CONSIGNE]
    if vise:
        out.append("Ce que ces décisions éclairent : %s" % vise)
    out.append("")
    for i, d in enumerate(decisions, 1):
        ligne = "[J%d] %s" % (i, d.get("titre") or "sans intitulé")
        detail = " ; ".join(x for x in (
            d.get("juridiction"), d.get("chambre"), d.get("date"),
            ("n° " + d["numero"]) if d.get("numero") else "",
            d.get("publication"), d.get("solution")) if x)
        if detail:
            ligne += "\n     %s" % detail
        if d.get("sort"):
            ligne += "\n     SORT DE CETTE DÉCISION : %s" % d["sort"]
        if d.get("url"):
            ligne += "\n     %s" % d["url"]
        if d.get("apercu"):
            ligne += ("\n     Aperçu (NON CITABLE comme position de la cour) : %s"
                      % d["apercu"][:600])
        out.append(ligne)
    out.append("")
    out.append("Réserve à reprendre si tu t'appuies sur l'une d'elles : " + RESERVE)
    return "\n".join(out)


# Les formes sous lesquelles une décision se cite en France. On ne cherche pas à
# les reconnaître toutes : on cherche à attraper les NUMÉROS, parce qu'un numéro
# est précisément ce qu'un modèle fabrique de plus crédible.
_RE_POURVOI = re.compile(r"n[°o]\s*(\d{2}-\d{2}[.\-]?\d{3})", re.I)
_RE_REQUETE = re.compile(r"(?:req(?:uête)?\.?\s*)n[°o]\s*(\d{5,7})", re.I)
_RE_ECLI = re.compile(r"\bECLI:[A-Z]{2}:[A-Z0-9]{1,7}:\d{4}:[A-Z0-9.]{1,25}\b")
_RE_CJUE = re.compile(r"\b(?:aff(?:aire)?\.?\s*)?C[-‑]\s?(\d{1,3}/\d{2})\b")


def _cles_citations(texte):
    """Les identifiants de décisions présents dans un texte, normalisés."""
    t = texte or ""
    cles = set()
    for m in _RE_POURVOI.finditer(t):
        cles.add(("pourvoi", re.sub(r"[.\-]", "", m.group(1))))
    for m in _RE_REQUETE.finditer(t):
        cles.add(("requête", m.group(1)))
    for m in _RE_ECLI.finditer(t):
        cles.add(("ECLI", m.group(0).upper()))
    for m in _RE_CJUE.finditer(t):
        cles.add(("CJUE", m.group(1)))
    return cles


def verifier_jurisprudence(reponse, decisions):
    """Les décisions citées qui n'étaient pas sous les yeux du modèle.

    C'EST LE CONTRÔLE QUI JUSTIFIE TOUT LE RESTE. On a levé une interdiction ;
    on ne l'a levée que pour une liste fermée ; il faut donc pouvoir dire quand
    le modèle en est sorti. Un numéro de pourvoi cité mais absent des décisions
    rapportées est signalé — pas masqué, pas corrigé en silence.

    Sans jurisprudence rapportée, TOUTE citation de décision est suspecte :
    l'interdiction générale n'a pas été levée pour cette analyse."""
    montrees = set()
    for d in decisions or []:
        if not d:
            continue
        blob = " ".join(str(d.get(c) or "") for c in ("titre", "numero", "url"))
        montrees |= _cles_citations(blob)
        if d.get("numero"):
            montrees.add(("pourvoi", re.sub(r"[.\-]", "", d["numero"])))
            montrees.add(("requête", re.sub(r"[.\-]", "", d["numero"])))
    citees = _cles_citations(reponse)
    suspectes = [{"type": t, "cle": c} for (t, c) in sorted(citees - montrees)]
    return {
        "ok": not suspectes,
        "suspectes": suspectes,
        "montrees": len(montrees),
        "corpus": SOURCE if decisions else "",
    }
