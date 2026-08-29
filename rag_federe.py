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

# ═══════════════════════════════════════════════════════════════════════════
#  PLUSIEURS PAIRS — parce que la maison en compte plus de deux
# ═══════════════════════════════════════════════════════════════════════════
# CE QUI A CHANGÉ. Le module a été écrit pour DEUX bases, et la maison en tient
# désormais trois. Un pair unique obligeait à choisir laquelle des deux autres
# on renonçait à interroger.
#
# LES VARIABLES SONT NUMÉROTÉES, ET C'EST DÉLIBÉRÉ. Un format compact —
# « nom|url|clé;nom|url|clé » — tiendrait dans une seule variable, et se
# saisirait de travers une fois sur deux dans une console d'hébergeur, sans
# message d'erreur. `RAG_PAIR2_URL` se lit, se corrige et se compare à
# `RAG_PAIR_URL` sans rien connaître d'un format.
#
# CHAQUE PAIR A SA PROPRE CLÉ. Une clé unique partagée par trois applications
# fait que la compromission d'une seule les ouvre toutes ; et la rotation de
# l'une oblige à redéployer les trois le même jour. À défaut de clé propre, le
# pair reprend celle du premier — ce qui reste le montage le plus simple, et
# doit rester possible.
PAIRS_MAX = 8


def _lire_pairs_supplementaires():
    out = []
    for i in range(2, PAIRS_MAX + 1):
        url = os.environ.get("RAG_PAIR%d_URL" % i, "").strip().rstrip("/")
        if not url:
            continue
        out.append({
            "nom": (os.environ.get("RAG_PAIR%d_NOM" % i, "").strip()
                    or ("base partenaire %d" % i)),
            "url": url,
            "cle": (os.environ.get("RAG_PAIR%d_CLE" % i, "").strip() or CLE),
        })
    return out


PAIRS_SUP = _lire_pairs_supplementaires()


def pairs():
    """Les pairs déclarés, dans l'ordre — le premier est celui d'origine.

    CALCULÉE À L'APPEL, jamais figée au chargement. Les variables historiques
    `RAG_PAIR_URL` / `RAG_PAIR_CLE` / `RAG_PAIR_NOM` restent le PREMIER pair :
    une installation existante continue de fonctionner sans rien changer, et
    les essais qui les remplacent à chaud voient leur remplacement.
    """
    out = []
    if PAIR:
        out.append({"nom": NOM_PAIR, "url": PAIR, "cle": CLE})
    for p in PAIRS_SUP:
        # UNE URL RÉPÉTÉE ENTRE `RAG_PAIR_URL` ET `RAG_PAIR2_URL` doublerait le
        # poids de cette base dans la fusion : elle apparaîtrait deux fois au
        # classement, et paraîtrait deux fois plus sûre.
        if p["url"] and p["url"] != PAIR:
            out.append(p)
    return out

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
# UN DISJONCTEUR PAR PAIR, ET C'EST LE POINT. Un état partagé ferait qu'une
# seule base en panne écarte les deux autres — la panne d'un pair coûterait la
# fédération entière, ce qui est exactement ce que le disjoncteur existe pour
# éviter. Le cache est clé par (pair, requête) pour la même raison.
_etats = {}
_etat = {"echecs": 0, "coupe_jusqu_a": 0.0, "motif": "", "derniere_reussite": 0.0}
_cache = {}


def _etat_de(url):
    """L'état d'un pair. Le premier pair partage l'état historique `_etat`,
    de sorte qu'un appelant qui l'inspecte voie encore ce qu'il voyait."""
    if url == PAIR:
        return _etat
    return _etats.setdefault(url, {"echecs": 0, "coupe_jusqu_a": 0.0,
                                   "motif": "", "derniere_reussite": 0.0})


def configure():
    """Vrai si AU MOINS UN pair est déclaré et le connecteur actif."""
    return bool(ACTIF and pairs())


def etat():
    """Ce que le connecteur dit de lui-même, sans rien tenter.

    Les clés historiques décrivent le PREMIER pair — une console qui les lit
    continue de fonctionner. `pairs` les donne tous, chacun avec son propre
    disjoncteur : une base en panne se voit, les autres aussi.
    """
    maintenant = time.time()
    liste = []
    for p in pairs():
        e = _etat_de(p["url"])
        liste.append({
            "nom": p["nom"], "url": p["url"], "cle": bool(p["cle"]),
            "coupe": maintenant < e["coupe_jusqu_a"],
            "motif": e["motif"],
            "derniere_reussite": e["derniere_reussite"] or None,
        })
    return {
        "actif": ACTIF,
        "pair": PAIR,
        "nom_pair": NOM_PAIR,
        "nom_local": NOM_LOCAL,
        "configure": configure(),
        "cle": bool(CLE),
        "coupe": maintenant < _etat["coupe_jusqu_a"],
        "motif": _etat["motif"],
        "derniere_reussite": _etat["derniere_reussite"] or None,
        "pairs": liste,
        "n_pairs": len(liste),
    }


def oublier():
    """Vide le cache et rouvre TOUS les disjoncteurs."""
    with _verrou:
        _cache.clear()
        _etats.clear()
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
    """Les fragments PUBLICS du PREMIER pair. Rend {ok, fragments, motif}.

    Conservée telle quelle : c'est le geste d'origine, et tout ce qui
    l'appelait continue de fonctionner. `interroger_tous` interroge la
    fédération entière.

    `ok` faux n'est pas une exception : c'est un pair injoignable, et la
    rédaction continue sur la base locale."""
    liste = pairs()
    if not ACTIF:
        return {"ok": False, "fragments": [],
                "motif": "fédération désactivée (RAG_FEDERE=0)"}
    if not liste:
        return {"ok": False, "fragments": [],
                "motif": "aucun pair déclaré (RAG_PAIR_URL absente)"}
    return interroger_pair(liste[0], query, k)


def interroger_pair(pair, query, k=8):
    """Les fragments publics d'UN pair, avec son cache et son disjoncteur.

    LE CACHE EST CLÉ PAR PAIR autant que par requête : deux bases qui
    répondent à la même question ne rendent pas la même chose, et une clé
    commune ferait servir la réponse de l'une pour l'autre — le défaut le plus
    difficile à voir de toute cette mécanique, puisque le résultat resterait
    plausible.
    """
    q = (query or "").strip()[:500]
    if not q:
        return {"ok": False, "fragments": [], "motif": "requête vide"}
    if not ACTIF:
        return {"ok": False, "fragments": [],
                "motif": "fédération désactivée (RAG_FEDERE=0)"}
    if not (pair or {}).get("url"):
        return {"ok": False, "fragments": [],
                "motif": "aucun pair déclaré (RAG_PAIR_URL absente)"}

    cle = (pair["url"], q, int(k))
    maintenant = time.time()
    entree = _cache.get(cle)
    if entree and maintenant - entree[0] < DUREE_CACHE:
        return entree[1]

    etat_pair = _etat_de(pair["url"])
    with _verrou:
        if maintenant < etat_pair["coupe_jusqu_a"]:
            return {"ok": False, "fragments": [],
                    "motif": etat_pair["motif"] or "pair momentanément écarté"}
    ok, res = _appel(q, k, pair)
    with _verrou:
        if ok:
            etat_pair.update({"echecs": 0, "motif": "", "coupe_jusqu_a": 0.0,
                              "derniere_reussite": time.time()})
        else:
            etat_pair["echecs"] += 1
            etat_pair["motif"] = res
            if etat_pair["echecs"] >= ECHECS_AVANT_COUPURE:
                # LE DISJONCTEUR, PAIR PAR PAIR. Sans lui, un pair injoignable
                # ajoute son délai d'expiration à CHAQUE livrable : l'utilisateur
                # paie la panne autant de fois qu'il rédige. Et partagé entre
                # pairs, il ferait écarter les bases qui répondent avec celle
                # qui ne répond plus.
                etat_pair["coupe_jusqu_a"] = time.time() + DUREE_COUPURE
    if not ok:
        return {"ok": False, "fragments": [], "motif": res}

    fragments = []
    for x in res:
        f = canoniser(x, pair["nom"])
        if f:
            fragments.append(f)
    sortie = {"ok": True, "fragments": fragments[:k], "motif": ""}
    _cache[cle] = (maintenant, sortie)
    return sortie


def interroger_tous(query, k=8):
    """Tous les pairs, EN PARALLÈLE. Rend {par_pair, fragments, ok, motifs}.

    EN PARALLÈLE, ET C'EST LE POINT. Trois pairs interrogés l'un après l'autre
    additionnent leurs délais : sur un pair lent, la rédaction attendrait trois
    fois. Les appels sont indépendants et bornés chacun par son propre délai ;
    les mener de front coûte trois fils et rend le pire des trois au lieu de
    leur somme.

    UNE PANNE NE COÛTE QUE SES DOCUMENTS. Chaque pair a son disjoncteur : les
    bases qui répondent répondent, celle qui est tombée est nommée dans les
    motifs, et le livrable pourra le dire.
    """
    liste = pairs()
    if not ACTIF or not liste:
        return {"par_pair": [], "fragments": [], "ok": False,
                "motifs": {}, "n_pairs": 0}
    if len(liste) == 1:
        r = interroger_pair(liste[0], query, k)
        return {"par_pair": [dict(r, nom=liste[0]["nom"])],
                "fragments": [r["fragments"]] if r["fragments"] else [],
                "ok": r["ok"],
                "motifs": {} if r["ok"] else {liste[0]["nom"]: r["motif"]},
                "n_pairs": 1}
    import concurrent.futures as _cf
    par_pair = [None] * len(liste)
    with _cf.ThreadPoolExecutor(max_workers=len(liste)) as ex:
        futurs = {ex.submit(interroger_pair, p, query, k): i
                  for i, p in enumerate(liste)}
        for f in _cf.as_completed(futurs):
            i = futurs[f]
            try:
                par_pair[i] = dict(f.result(), nom=liste[i]["nom"])
            except Exception:                            # pragma: no cover
                par_pair[i] = {"ok": False, "fragments": [],
                               "motif": "erreur interne du connecteur",
                               "nom": liste[i]["nom"]}
    return {
        "par_pair": par_pair,
        # L'ORDRE DES LISTES EST CELUI DE LA DÉCLARATION, pas celui des
        # réponses. Sans quoi la fusion départagerait les égalités selon qui a
        # répondu le plus vite ce jour-là, et la même rédaction rendrait deux
        # ordres différents à deux minutes d'intervalle.
        "fragments": [r["fragments"] for r in par_pair if r and r["fragments"]],
        "ok": any(r and r["ok"] for r in par_pair),
        "motifs": {r["nom"]: r["motif"] for r in par_pair
                   if r and not r["ok"] and r.get("motif")},
        "n_pairs": len(liste),
    }


def _appel(query, k, pair=None):
    """Un aller-retour HTTP vers un pair. Rend (ok, liste_ou_motif)."""
    url = (pair or {}).get("url") or PAIR
    cle_pair = (pair or {}).get("cle") if pair else CLE
    entetes = {"Content-Type": "application/json",
               "User-Agent": "conseilprev-rag-federe/1.0"}
    if cle_pair:
        # UN EN-TÊTE HTTP NE TRANSPORTE QUE DE L'ASCII. Une clé accentuée fait
        # lever la bibliothèque au moment de l'envoi — une exception, là où ce
        # module promet de n'en jamais laisser passer vers la rédaction. On
        # refuse donc avant, avec le motif qui dit quoi corriger.
        try:
            cle_pair.encode("ascii")
        except UnicodeEncodeError:
            return False, ("la clé RAG_PAIR_CLE contient un caractère non "
                           "ASCII : employez une valeur hexadécimale ou base64")
        entetes["X-Rag-Cle"] = cle_pair
    try:
        r = requests.post(
            url + CHEMIN,
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
    return fusionner_n([locaux or [], distants or []], k)


def fusionner_n(listes, k=8):
    """N listes mêlées par RANG. Même règle, autant de bases qu'on veut.

    LA FUSION PAR RANG SUPPORTE N LISTES SANS RIEN CHANGER, et c'est
    précisément sa vertu : chaque fragment vaut 1/(K + son rang) dans SA liste,
    et les contributions s'additionnent. Un fragment que trois bases connaissent
    cumule trois fois — ce qui est exactement le signal qu'on veut faire
    remonter, et qu'aucun tri par score ne rendrait.

    L'ORDRE DES LISTES DÉPARTAGE LES ÉGALITÉS, et elles sont la règle : trois
    listes de même longueur donnent les mêmes poids rang par rang. La base
    locale d'abord — elle est la matière première de l'application —, puis les
    pairs dans l'ordre où ils sont déclarés. Départager sur le titre laisserait
    l'alphabet décider quelle maison parle en premier.
    """
    ordre = {}
    poids = {}
    fragments = {}
    for rang_liste, liste in enumerate(listes or []):
        for rang, f in enumerate(liste):
            if not f:
                continue
            c = _cle(f)
            if not c:
                continue
            poids[c] = poids.get(c, 0.0) + 1.0 / (RRF_K + rang + 1)
            if c not in fragments:
                fragments[c] = dict(f)
                ordre[c] = rang_liste
            elif f.get("base") and f["base"] not in bases_de(fragments[c]):
                # LE FRAGMENT QUE PLUSIEURS MAISONS CONNAISSENT. Le dire vaut
                # mieux que de choisir arbitrairement une provenance : c'est le
                # fragment sur lequel on peut le plus s'appuyer.
                fragments[c]["base"] = "%s + %s" % (fragments[c]["base"], f["base"])
                fragments[c]["deux_bases"] = True
    # LES ÉGALITÉS SONT LA RÈGLE, PAS L'EXCEPTION : des listes de même longueur
    # donnent exactement les mêmes poids rang par rang. Les départager par ordre
    # alphabétique de document reviendrait à laisser le titre décider de la
    # maison qui parle en premier. On départage par l'ORDRE DES LISTES — la
    # locale d'abord, puis les pairs tels qu'ils sont déclarés —, et le titre ne
    # sert que de dernier recours, pour que le résultat reste reproductible.
    def _rang(c):
        return (-poids[c], ordre.get(c, 99), fragments[c]["document"])
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
    """Le geste complet : TOUS les pairs, puis la fusion avec le local.

    `locaux` sont les fragments de la base locale, DÉJÀ trouvés et déjà classés
    par l'appelant — on ne les recalcule pas, chaque application sachant mieux
    que ce module comment interroger la sienne.

    Rend le compte PAR BASE : c'est ce qui permet à un livrable de dire sur
    quoi il a été écrit, et surtout quelles bases n'ont pas répondu. Les clés
    `pair_ok`, `motif`, `n_local` et `n_pair` décrivent encore le premier pair,
    pour que ce qui les lisait continue de fonctionner.
    """
    locaux = [canoniser(x, NOM_LOCAL) for x in (locaux or [])]
    locaux = [x for x in locaux if x]
    tous = interroger_tous(query, k)
    fusion = fusionner_n([locaux] + tous["fragments"], k)
    par_base = {}
    for f in fusion:
        for b in bases_de(f):
            par_base[b] = par_base.get(b, 0) + 1
    premier = (tous["par_pair"] or [{}])[0]
    return {
        "fragments": fusion,
        "pair_ok": tous["ok"],
        "motif": premier.get("motif") or "; ".join(
            "%s : %s" % (n, m) for n, m in (tous["motifs"] or {}).items()),
        "n_local": par_base.get(NOM_LOCAL, 0),
        "n_pair": par_base.get(NOM_PAIR, 0),
        "par_base": par_base,
        "motifs": tous["motifs"],
        "n_pairs": tous["n_pairs"],
        "pairs_ok": [r["nom"] for r in tous["par_pair"] if r and r["ok"]],
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
    doit savoir quelles bases ont été consultées — et surtout lesquelles ne
    l'ont pas été, parce que le document aurait pu être différent.

    CHAQUE BASE MUETTE EST NOMMÉE. Avec trois bases, « la fédération a
    partiellement échoué » ne dit rien d'exploitable : c'est le NOM de la base
    absente qui permet de juger si le document est complet sur son sujet.
    """
    par_base = res.get("par_base")
    if par_base is None:
        par_base = {NOM_LOCAL: res.get("n_local", 0),
                    NOM_PAIR: res.get("n_pair", 0)}
    presentes = [(b, n) for b, n in par_base.items() if n]
    if not presentes:
        return "Aucun extrait documentaire n'a été retrouvé pour cette rédaction."
    presentes.sort(key=lambda x: (0 if x[0] == NOM_LOCAL else 1, x[0]))
    compte = ", ".join("%d de %s" % (n, b) for b, n in presentes)
    phrase = "Rédigé à partir de %s." % compte
    motifs = res.get("motifs") or {}
    if motifs:
        return phrase + (" %s n'a pas pu être interrogée (%s). Le document "
                         "aurait pu être différent."
                         % (" ni ".join(sorted(motifs)),
                            " ; ".join("%s" % m for m in motifs.values())))
    muettes = [p["nom"] for p in pairs()
               if p["nom"] not in par_base and p["nom"] != NOM_LOCAL]
    if muettes:
        return phrase + (" %s %s été interrogée%s et n'%s rien rendu sur ce "
                         "sujet." % (", ".join(muettes),
                                     "ont" if len(muettes) > 1 else "a",
                                     "s" if len(muettes) > 1 else "",
                                     "ont" if len(muettes) > 1 else "a"))
    return phrase


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
