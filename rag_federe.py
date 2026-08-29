# -*- coding: utf-8 -*-
"""RAG FÉDÉRÉ — DEUX BASES, UNE SEULE RÉDACTION.

CE QUE CE MODULE RÉSOUT. CONSEILPREV et CONSEILPREV Cyber tiennent chacun sa
base documentaire, et chacune sait des choses que l'autre ignore : le droit du
numérique et l'IA d'un côté, l'ingénierie des centres de données et la
cybersécurité industrielle de l'autre. Un livrable rédigé sur une seule des deux
puise donc dans la moitié de ce que la maison sait. Ce module fait interroger les
deux, et rend un seul jeu de fragments.

L'ALTERNANCE N'EST PAS UN DÉTAIL DE PRÉSENTATION. Les deux moteurs ne calculent
pas leurs scores de la même façon — l'un mêle vecteurs et lexique, l'autre pondère
un TF-IDF — et leurs valeurs ne se comparent pas. Trier les fragments réunis sur
ces scores reviendrait à comparer des degrés Celsius à des Fahrenheit : la base
dont le moteur est le plus généreux occuperait tout le haut du classement. On
fusionne donc par RANG (fusion par rang réciproque), qui ne suppose rien des
échelles et garantit que les deux bases sont représentées.

CHAQUE FRAGMENT PORTE SA BASE. Ce n'est pas une étiquette de confort : un
livrable reproduit les extraits MOT POUR MOT, et un passage venu de l'autre
maison doit être reconnaissable dans le document où il atterrit. Sans cette
mention, personne ne peut dire, six mois plus tard, d'où sortait une phrase.

CE QUI NE TRAVERSE JAMAIS. Les documents marqués « interne ». Le pair ne sert que
du PUBLIC, et cette limite est posée du côté qui sert, pas du côté qui demande —
une restriction que l'appelant peut lever n'est pas une restriction. Un document
interne reste disponible à l'application qui le détient : la fédération ajoute ce
que l'autre maison publie, elle n'ouvre pas ses tiroirs.

UNE PANNE DU PAIR NE COÛTE RIEN. La rédaction tenait debout sur une seule base
avant ce module et y tient encore : délai borné, disjoncteur après trois échecs
consécutifs, cache d'une heure, et jamais d'exception vers l'appelant. Ce qui
change, c'est que le livrable SAIT qu'il n'a eu qu'une base — et peut le dire.
"""
import json
import os
import threading
import time

import requests

# ═══════════════════════════════════════════════════════════════════════════
# 1. LE PAIR, DÉCLARÉ
# ═══════════════════════════════════════════════════════════════════════════

PAIR = os.environ.get("RAG_PAIR_URL", "").strip().rstrip("/")
# LA CLÉ DIT QUI PEUT DEMANDER, PAS CE QUI EST SERVI. Elle réserve la recherche
# au pair attendu — un corpus « public » au sens de « montré sur le site » n'est
# pas pour autant offert en vrac par une API commode. Elle n'ouvre AUCUN document
# interne : cette limite-là est posée du côté qui sert, et rien de ce que
# l'appelant présente ne la lève.
CLE = os.environ.get("RAG_PAIR_CLE", "").strip()
NOM_PAIR = os.environ.get("RAG_PAIR_NOM", "").strip() or "base partenaire"
NOM_LOCAL = os.environ.get("RAG_NOM", "").strip() or "base locale"
ACTIF = (os.environ.get("RAG_FEDERE", "1").strip().lower()
         not in ("0", "off", "non", "false"))

CHEMIN = "/api/rag/search"

DELAI_CONNEXION = 4
DELAI_LECTURE = 12
ECHECS_AVANT_COUPURE = 3
DUREE_COUPURE = 300
DUREE_CACHE = 3600

# La constante de la fusion par rang réciproque. Soixante est la valeur de la
# publication d'origine (Cormack et al., 2009) et le choix courant : elle amortit
# l'écart entre les premiers rangs, de sorte qu'un deuxième d'une base ne soit
# pas écrasé par le premier de l'autre.
RRF_K = 60

_verrou = threading.Lock()
_etat = {"echecs": 0, "coupe_jusqu_a": 0.0, "motif": "", "derniere_reussite": 0.0}
_cache = {}


def configure():
    """Vrai si un pair est déclaré et le connecteur actif."""
    return bool(ACTIF and PAIR)


def etat():
    """Ce que le connecteur dit de lui-même, sans rien tenter."""
    return {
        "actif": ACTIF,
        "pair": PAIR,
        "nom_pair": NOM_PAIR,
        "nom_local": NOM_LOCAL,
        "configure": configure(),
        "cle": bool(CLE),
        "coupe": time.time() < _etat["coupe_jusqu_a"],
        "motif": _etat["motif"],
        "derniere_reussite": _etat["derniere_reussite"] or None,
    }


def oublier():
    """Vide le cache et rouvre le disjoncteur."""
    with _verrou:
        _cache.clear()
        _etat.update({"echecs": 0, "coupe_jusqu_a": 0.0, "motif": ""})


# ═══════════════════════════════════════════════════════════════════════════
# 2. LA FORME CANONIQUE
# ═══════════════════════════════════════════════════════════════════════════
#
# Les deux applications nomment les mêmes choses différemment — `texte` ici,
# `content` là ; `document` ici, `title` là. On ne choisit pas un camp : on
# traduit à l'entrée et à la sortie, et le module ne connaît qu'une forme.
#
# `base` est le seul champ que les deux ignoraient, et le seul qui compte
# vraiment ici : sans lui, un fragment fédéré est indiscernable d'un fragment
# local une fois recopié dans un livrable.

CHAMPS_TEXTE = ("texte", "content", "chunk_text", "extrait")
CHAMPS_TITRE = ("document", "title", "titre", "nom_fichier")
CHAMPS_ID = ("document_id", "doc_id", "id")


def _premier(d, cles, defaut=""):
    for c in cles:
        v = d.get(c)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if v not in (None, "") and not isinstance(v, str):
            return v
    return defaut


def canoniser(brut, base):
    """Un fragment, quelle que soit la maison qui l'a rendu."""
    if not isinstance(brut, dict):
        return None
    texte = _premier(brut, CHAMPS_TEXTE)
    if not texte:
        return None
    try:
        score = float(brut.get("score") or 0.0)
    except (TypeError, ValueError):
        score = 0.0
    return {
        "texte": texte,
        "document": _premier(brut, CHAMPS_TITRE, "document sans titre"),
        "document_id": _premier(brut, CHAMPS_ID, ""),
        "score": score,
        "theme": _premier(brut, ("theme",)),
        "famille": _premier(brut, ("famille",)),
        "base": base,
    }


def _cle(f):
    """Deux bases n'ont pas le même espace d'identifiants : c'est le CONTENU
    qui dit si deux fragments sont le même. Cent vingt caractères suffisent à
    distinguer deux extraits d'un même document sans confondre deux copies du
    même passage."""
    return " ".join((f.get("texte") or "").split())[:120].lower()


# ═══════════════════════════════════════════════════════════════════════════
# 3. INTERROGATION DU PAIR
# ═══════════════════════════════════════════════════════════════════════════

def interroger(query, k=8):
    """Les fragments PUBLICS du pair. Rend {ok, fragments, motif}.

    `ok` faux n'est pas une exception : c'est un pair injoignable, et la
    rédaction continue sur la base locale."""
    q = (query or "").strip()[:500]
    if not q:
        return {"ok": False, "fragments": [], "motif": "requête vide"}
    if not ACTIF:
        return {"ok": False, "fragments": [],
                "motif": "fédération désactivée (RAG_FEDERE=0)"}
    if not PAIR:
        return {"ok": False, "fragments": [],
                "motif": "aucun pair déclaré (RAG_PAIR_URL absente)"}

    cle = (q, int(k))
    maintenant = time.time()
    entree = _cache.get(cle)
    if entree and maintenant - entree[0] < DUREE_CACHE:
        return entree[1]

    with _verrou:
        if maintenant < _etat["coupe_jusqu_a"]:
            return {"ok": False, "fragments": [],
                    "motif": _etat["motif"] or "pair momentanément écarté"}
    ok, res = _appel(q, k)
    with _verrou:
        if ok:
            _etat.update({"echecs": 0, "motif": "", "coupe_jusqu_a": 0.0,
                          "derniere_reussite": time.time()})
        else:
            _etat["echecs"] += 1
            _etat["motif"] = res
            if _etat["echecs"] >= ECHECS_AVANT_COUPURE:
                # LE DISJONCTEUR. Sans lui, un pair injoignable ajoute son délai
                # d'expiration à CHAQUE livrable : l'utilisateur paie la panne
                # autant de fois qu'il rédige.
                _etat["coupe_jusqu_a"] = time.time() + DUREE_COUPURE
    if not ok:
        return {"ok": False, "fragments": [], "motif": res}

    fragments = []
    for x in res:
        f = canoniser(x, NOM_PAIR)
        if f:
            fragments.append(f)
    sortie = {"ok": True, "fragments": fragments[:k], "motif": ""}
    _cache[cle] = (maintenant, sortie)
    return sortie


def _appel(query, k):
    """Un aller-retour HTTP. Rend (ok, liste_ou_motif)."""
    entetes = {"Content-Type": "application/json",
               "User-Agent": "conseilprev-rag-federe/1.0"}
    if CLE:
        # UN EN-TÊTE HTTP NE TRANSPORTE QUE DE L'ASCII. Une clé accentuée fait
        # lever la bibliothèque au moment de l'envoi — une exception, là où ce
        # module promet de n'en jamais laisser passer vers la rédaction. On
        # refuse donc avant, avec le motif qui dit quoi corriger.
        try:
            CLE.encode("ascii")
        except UnicodeEncodeError:
            return False, ("la clé RAG_PAIR_CLE contient un caractère non "
                           "ASCII : employez une valeur hexadécimale ou base64")
        entetes["X-Rag-Cle"] = CLE
    try:
        r = requests.post(
            PAIR + CHEMIN,
            json={"query": query, "top_k": min(int(k), 10)},
            headers=entetes,
            timeout=(DELAI_CONNEXION, DELAI_LECTURE))
    except requests.exceptions.Timeout:
        return False, "le pair n'a pas répondu dans le délai imparti"
    except requests.exceptions.RequestException as exc:
        return False, "pair injoignable (%s)" % type(exc).__name__
    if r.status_code == 401 or r.status_code == 403:
        # 403 ET « panne » ne se soignent pas pareil : l'un se règle en posant
        # la même clé des deux côtés, l'autre en attendant. Le motif doit les
        # distinguer, sinon on cherche un réseau qui va bien.
        return False, ("le pair refuse la requête (%d) : la clé partagée "
                       "RAG_PAIR_CLE est-elle la même des deux côtés ?"
                       % r.status_code)
    if r.status_code >= 400:
        return False, "le pair a répondu %d" % r.status_code
    try:
        j = r.json()
    except ValueError:
        return False, "réponse du pair illisible"
    for champ in ("resultats", "results", "fragments", "hits"):
        if isinstance(j.get(champ), list):
            return True, j[champ]
    return False, "réponse du pair sans liste de résultats"


# ═══════════════════════════════════════════════════════════════════════════
# 4. LA FUSION
# ═══════════════════════════════════════════════════════════════════════════

def fusionner(locaux, distants, k=8):
    """Les deux listes mêlées par RANG, jamais par score.

    POURQUOI PAS PAR SCORE. Les deux moteurs ne mesurent pas la même chose :
    l'un mêle vecteurs et lexique, l'autre pondère un TF-IDF. Un tri sur ces
    valeurs classerait par générosité d'échelle, et la base au moteur le plus
    bavard occuperait tout le haut — quelle que soit sa pertinence réelle.

    La fusion par rang réciproque ne suppose rien des échelles : chaque
    fragment vaut 1/(RRF_K + son rang) dans sa propre liste, et un fragment
    présent dans les DEUX bases cumule les deux — ce qui est exactement le
    signal qu'on veut faire remonter.
    """
    poids = {}
    fragments = {}
    for liste in (locaux or [], distants or []):
        for rang, f in enumerate(liste):
            if not f:
                continue
            c = _cle(f)
            if not c:
                continue
            poids[c] = poids.get(c, 0.0) + 1.0 / (RRF_K + rang + 1)
            if c not in fragments:
                fragments[c] = dict(f)
            elif fragments[c].get("base") != f.get("base"):
                # LE FRAGMENT QUE LES DEUX MAISONS CONNAISSENT. Le dire vaut
                # mieux que de choisir arbitrairement une provenance : c'est le
                # fragment sur lequel on peut le plus s'appuyer.
                fragments[c]["base"] = "%s + %s" % (fragments[c]["base"], f["base"])
                fragments[c]["deux_bases"] = True
    # LES ÉGALITÉS SONT LA RÈGLE, PAS L'EXCEPTION : deux listes de même longueur
    # donnent exactement les mêmes poids rang par rang. Les départager par ordre
    # alphabétique de document reviendrait à laisser le titre décider de la
    # maison qui parle en premier. On préfère la base LOCALE : elle est la
    # matière première de l'application, le pair la complète.
    def _rang(c):
        return (-poids[c], 0 if fragments[c].get("base") == NOM_LOCAL else 1,
                fragments[c]["document"])
    out = []
    for c in sorted(poids, key=_rang)[:k]:
        f = fragments[c]
        f["score_fusion"] = round(poids[c], 6)
        out.append(f)
    return out


def bases_de(fragment):
    """Les maisons d'où vient un fragment — une, ou les deux.

    COMPARER PAR SOUS-CHAÎNE NE MARCHE PAS, et c'est un piège qu'on a posé
    soi-même : « CONSEILPREV » est contenu dans « CONSEILPREV Cyber », de sorte
    qu'un `in` compte chaque fragment distant comme local. Le champ est donc
    découpé sur son séparateur et comparé à l'identique."""
    brut = (fragment or {}).get("base") or ""
    return {x.strip() for x in brut.split("+") if x.strip()}


def chercher(query, locaux, k=8):
    """Le geste complet : le pair, puis la fusion avec ce que l'appelant a déjà.

    `locaux` sont les fragments de la base locale, DÉJÀ trouvés et déjà classés
    par l'appelant — on ne les recalcule pas, chaque application sachant mieux
    que ce module comment interroger la sienne.

    Rend {fragments, pair_ok, motif, n_local, n_pair} : le compte par base est
    ce qui permet à un livrable de dire sur quoi il a été écrit."""
    locaux = [canoniser(x, NOM_LOCAL) for x in (locaux or [])]
    locaux = [x for x in locaux if x]
    r = interroger(query, k)
    fusion = fusionner(locaux, r["fragments"], k)
    return {
        "fragments": fusion,
        "pair_ok": r["ok"],
        "motif": r["motif"],
        "n_local": sum(1 for f in fusion if NOM_LOCAL in bases_de(f)),
        "n_pair": sum(1 for f in fusion if NOM_PAIR in bases_de(f)),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 5. CE QUE LE DOCUMENT EN DIT
# ═══════════════════════════════════════════════════════════════════════════

def en_forme(fragments, texte="content", titre="title", ident="doc_id"):
    """Les fragments rendus dans le VOCABULAIRE DE L'APPELANT.

    Les deux applications nomment les mêmes champs différemment, et tout leur
    code de rédaction est écrit dans leur propre vocabulaire. Traduire ici coûte
    trois lignes ; renommer là-bas toucherait des dizaines d'appels et
    casserait des trames qui marchent.

    `base` et `score_fusion` sont AJOUTÉS, jamais retirés : c'est la provenance,
    et elle doit survivre au passage — un extrait recopié mot pour mot dans un
    livrable sans sa maison d'origine est intraçable."""
    out = []
    for f in fragments or []:
        d = {texte: f.get("texte") or "", titre: f.get("document") or "",
             ident: f.get("document_id"), "score": f.get("score"),
             "theme": f.get("theme") or "",
             "base": f.get("base") or "", "score_fusion": f.get("score_fusion")}
        if f.get("deux_bases"):
            d["deux_bases"] = True
        if f.get("famille"):
            d["famille"] = f["famille"]
        out.append(d)
    return out


def mention(res):
    """La phrase qui accompagne un livrable : sur quoi il a été écrit.

    ELLE EST DUE MÊME QUAND TOUT VA BIEN. Un lecteur qui reçoit un document
    doit savoir si la seconde base a été consultée — et surtout quand elle ne
    l'a pas été, parce que le document aurait pu être différent."""
    n_l, n_p = res.get("n_local", 0), res.get("n_pair", 0)
    if not (n_l or n_p):
        return "Aucun extrait documentaire n'a été retrouvé pour cette rédaction."
    if res.get("pair_ok"):
        if n_p:
            return ("Rédigé à partir de %d extrait%s de %s et %d de %s."
                    % (n_l, "s" if n_l > 1 else "", NOM_LOCAL, n_p, NOM_PAIR))
        return ("Rédigé à partir de %d extrait%s de %s ; %s a été interrogée et "
                "n'a rien rendu sur ce sujet."
                % (n_l, "s" if n_l > 1 else "", NOM_LOCAL, NOM_PAIR))
    return ("Rédigé à partir de %d extrait%s de %s SEULE : %s n'a pas pu être "
            "interrogée (%s). Le document aurait pu être différent."
            % (n_l, "s" if n_l > 1 else "", NOM_LOCAL, NOM_PAIR,
               res.get("motif") or "cause non qualifiée"))


def bloc_prompt(fragments, numeroter=True):
    """Les extraits mis sous les yeux du modèle, chacun avec SA BASE.

    Le modèle cite entre crochets ; le numéro doit donc suffire à retrouver
    d'où vient le passage — y compris de quelle maison."""
    out = []
    for i, f in enumerate(fragments or [], 1):
        tete = "[%d] " % i if numeroter else ""
        out.append("%s%s — %s\n%s" % (tete, f.get("document") or "document",
                                      f.get("base") or "?", f.get("texte") or ""))
    return "\n\n".join(out)


def sources(fragments):
    """La liste des sources, pour l'interface et pour l'export."""
    out = []
    for i, f in enumerate(fragments or [], 1):
        out.append({"n": i, "titre": f.get("document") or "document",
                    "base": f.get("base") or "", "theme": f.get("theme") or "",
                    "deux_bases": bool(f.get("deux_bases"))})
    return out
