# -*- coding: utf-8 -*-
"""
RETROUVER LA RÉFÉRENCE D'UN CHIFFRE — PROPOSÉ PAR UN AGENT, PRONONCÉ PAR
UNE PERSONNE.

═══ CE QUE CE MODULE NE FAIT PAS, ET POURQUOI ═════════════════════════════
Il ne rafraîchit aucune valeur. `chiffres_securite_ia` le dit déjà, et il a
raison : « 88 % des organisations rapportent un incident » existe dans une
enquête, à une date, et ne changera plus. Un agent qui prétendrait
« remettre à jour » ce nombre inventerait un mouvement qui n'existe pas.

═══ LE DÉFAUT QU'IL COMBLE, MESURÉ LE 21 SEPTEMBRE 2026 ══════════════════
Les six chiffres du bandeau étaient tous `frais` ce jour-là — rien à
remplacer avant mi-2027. Mais CINQ SUR SIX portaient `lien: None` et une
réserve `a_confirmer`, dont quatre renvoyant à une même « Enquête
sectorielle 2025 » sans référence ni adresse. Le module l'écrit lui-même :
« Un cabinet qui publie 7,2 % sans pouvoir dire d'où il vient se fait
reprendre au premier comité — et c'est la page entière qui perd son crédit,
pas la tuile. »

Le travail à faire n'est donc pas de re-mesurer : c'est de RETROUVER LE
DOCUMENT qu'un lecteur peut ouvrir. C'est une tâche dont on ne connaît pas
les étapes d'avance — combien de recherches, quels résultats ouvrir, cela
dépend de ce qui revient — et c'est ce qui justifie un agent plutôt qu'un
appel de modèle.

═══ LA VÉRIFICATION NE FAIT PAS CONFIANCE À L'AGENT ══════════════════════
L'agent rend une adresse et une phrase. Ce module ROUVRE L'ADRESSE LUI-MÊME
et vérifie que la phrase s'y trouve, mot pour mot, et qu'elle contient bien
le nombre en cause. Un agent qui citerait une page qu'il a mal lue, ou qui
rapporterait une phrase plausible d'une page réelle, est arrêté ici — et il
l'est SANS que le modèle ait son mot à dire, puisque le contrôle est une
lecture de texte.

═══ ET RIEN N'ENTRE DANS LE BANDEAU SANS UN NOM ══════════════════════════
Une source confirmée se superpose aux six chiffres comme le fait déjà le
compte MCP : elle est posée dans un magasin daté, jamais écrite dans le
source du module. `appliquer()` refuse sans le nom de la personne qui
décide, et ce nom voyage avec la source.

QUAND L'AGENT REVIENT BREDOUILLE, C'EST UN RÉSULTAT. Si aucun document
public ne porte « 88 % », le chiffre doit être retiré ou réécrit, pas
republié avec une attribution vague. Un refus nommé vaut mieux qu'une
référence de complaisance.
"""

import datetime
import json
import re
import threading
import unicodedata
import urllib.parse

import chiffres_securite_ia as socle

VERSION = "2026-09-a"


# ═══════════════════════════════════════════════════════════════════════
# 1. CE DONT CHAQUE CHIFFRE A BESOIN — DÉTERMINISTE, SANS MODÈLE
# ═══════════════════════════════════════════════════════════════════════

BESOINS = {
    "source_absente": {
        "nom": "Référence à établir",
        "pourquoi": "Le chiffre est publié sans adresse ouvrable, ou avec "
                    "une réserve écrite. Un lecteur ne peut pas le vérifier.",
        "urgent": True},
    "edition_suivante": {
        "nom": "Édition suivante à chercher",
        "pourquoi": "La mesure a passé sa péremption. Ce qui se cherche "
                    "n'est pas une nouvelle valeur du même rapport, mais le "
                    "rapport suivant.",
        "urgent": True},
    "se_recompte": {
        "nom": "Se recompte seul",
        "pourquoi": "Ce chiffre s'obtient d'un registre ouvert ; il a sa "
                    "propre fonction de comptage et n'a pas besoin d'un "
                    "agent pour être retrouvé.",
        "urgent": False},
    "rien": {
        "nom": "Rien à faire",
        "pourquoi": "La référence est établie et la mesure n'a pas passé "
                    "sa péremption.",
        "urgent": False},
}


def besoin(chiffre, aujourdhui=None):
    """De quoi ce chiffre a besoin, et pourquoi.

    L'ORDRE COMPTE. Un chiffre sans référence n'a pas besoin qu'on lui
    cherche une édition suivante : il a besoin qu'on trouve la PREMIÈRE.
    Chercher la suivante d'un rapport qu'on ne sait pas nommer reviendrait à
    demander à l'agent de deviner le point de départ.
    """
    c = chiffre if isinstance(chiffre, dict) else {}
    if c.get("recomptable"):
        return dict(BESOINS["se_recompte"], cle="se_recompte")
    if not (c.get("lien") or "").strip() or (c.get("a_confirmer") or "").strip():
        return dict(BESOINS["source_absente"], cle="source_absente")
    f = socle.fraicheur(c, aujourdhui)
    if f.get("etat") in ("a_revoir", "perime", "inconnu"):
        return dict(BESOINS["edition_suivante"], cle="edition_suivante",
                    etat=f.get("etat"), age_jours=f.get("age_jours"))
    return dict(BESOINS["rien"], cle="rien")


def vue(cle, aujourdhui=None):
    """Le chiffre TEL QU'IL EST SERVI — référence validée comprise.

    LE DÉFAUT QUE CETTE FONCTION CORRIGE A ÉTÉ MESURÉ. `besoin()` lisait la
    table `CHIFFRES` du socle, c'est-à-dire le chiffre tel qu'il a été
    ÉCRIT — sans la référence posée après coup. Un chiffre dont la source
    venait d'être validée continuait donc de figurer parmi ceux « à
    tracer » : l'agent serait reparti chercher ce qu'on venait de trouver,
    et l'écran aurait montré du travail déjà fait.
    """
    for c in socle.chiffres(aujourdhui):
        if c.get("cle") == cle:
            return c
    return None


def a_tracer(aujourdhui=None):
    """Les chiffres qui attendent quelque chose, dans l'ordre d'urgence."""
    dus = []
    for c in socle.chiffres(aujourdhui):
        b = besoin(c, aujourdhui)
        if b["urgent"]:
            dus.append({"cle": c["cle"], "affiche": c.get("affiche"),
                        "dit": c.get("dit"), "besoin": b})
    return dus


# ═══════════════════════════════════════════════════════════════════════
# 2. CE QU'UNE RÉPONSE DOIT PORTER
# ═══════════════════════════════════════════════════════════════════════

CHAMPS = (
    {"cle": "lien", "nom": "Adresse du document", "obligatoire": True,
     "pourquoi": "Une source sans adresse est une intention, pas une "
                 "source : le lecteur doit pouvoir la rouvrir."},
    {"cle": "editeur", "nom": "Éditeur", "obligatoire": True,
     "pourquoi": "Qui publie décide de ce que vaut le chiffre : une "
                 "autorité publique et un fournisseur ne s'opposent pas de "
                 "la même façon."},
    {"cle": "titre", "nom": "Titre du document", "obligatoire": True,
     "pourquoi": "Une adresse seule vieillit et casse ; le titre permet de "
                 "retrouver le document ailleurs."},
    {"cle": "publie_le", "nom": "Date de publication", "obligatoire": True,
     "pourquoi": "Sans elle, impossible de dire si c'est bien l'édition "
                 "suivante ou la même qu'on relit."},
    {"cle": "citation", "nom": "Phrase citée", "obligatoire": True,
     "pourquoi": "C'est elle qui est vérifiée contre la page : sans "
                 "citation, la référence n'est pas contrôlable."},
    {"cle": "echantillon", "nom": "Échantillon", "obligatoire": False,
     "pourquoi": "Une décimale sur un chiffre d'enquête suppose un "
                 "échantillon nommé ; l'absence se dit."},
)

_CHAMPS = {c["cle"]: c for c in CHAMPS}
CITATION_MIN = 20
CITATION_MAX = 400
SEUIL_FRAGILE = 0.75

MOTIFS = {
    "chiffre_inconnu": "Ce chiffre n'existe pas au bandeau.",
    "rien_a_chercher": "Ce chiffre n'attend rien : sa référence est "
                       "établie et sa mesure n'a pas vieilli.",
    "reponse_vide": "L'agent n'a rien renvoyé.",
    "reponse_illisible": "La réponse de l'agent n'est pas un objet JSON "
                         "exploitable.",
    "reference_incomplete": "La réponse ne porte pas tous les champs sans "
                            "lesquels une référence ne se vérifie pas.",
    "aucune_source_publique": "L'agent n'a trouvé aucun document public "
                              "portant ce chiffre. Ce n'est pas un échec de "
                              "recherche : c'est un résultat, et il dit que "
                              "le chiffre n'est pas défendable en l'état.",
    "lien_invalide": "L'adresse n'est pas une adresse web absolue.",
    "lien_injoignable": "L'adresse n'a pas pu être rouverte : une source "
                        "qu'on ne peut pas ouvrir n'en est pas une.",
    "citation_trop_courte": "La phrase citée est trop courte pour être "
                            "vérifiable.",
    "citation_introuvable": "La phrase citée ne se retrouve pas dans la "
                            "page : elle n'est pas vérifiable.",
    "citation_sans_le_chiffre": "La phrase citée ne contient pas le nombre "
                                "en cause : elle parle d'autre chose.",
    "date_illisible": "La date de publication n'est pas lisible.",
    "date_impossible": "Le document serait publié avant la mesure qu'il "
                       "rapporte.",
    "edition_pas_plus_recente": "Ce document n'est pas plus récent que la "
                                "mesure en place : ce n'est pas l'édition "
                                "suivante, c'est la même.",
}


# ═══════════════════════════════════════════════════════════════════════
# 3. LA DEMANDE FAITE À L'AGENT
# ═══════════════════════════════════════════════════════════════════════

PROMPT_SYSTEME = (
    "Tu cherches la REFERENCE PUBLIQUE d'un chiffre deja publie : le "
    "document qu'un lecteur peut ouvrir et ou ce chiffre figure.\n"
    "Regles absolues :\n"
    "1. Tu reponds UNIQUEMENT par un objet JSON, sans texte avant ni "
    "apres, sans bloc de code.\n"
    "2. Le champ \"citation\" est une phrase COPIEE MOT POUR MOT de la page "
    "que tu as ouverte, et elle doit contenir le nombre en cause. La page "
    "sera ROUVERTE et la phrase recherchee telle quelle : une "
    "reformulation, meme exacte, fait rejeter ta reponse.\n"
    "3. Tu n'inventes aucune adresse. Si tu n'as pas ouvert la page, tu ne "
    "la cites pas.\n"
    "4. Si tu ne trouves pas de document public portant ce chiffre, reponds "
    "{\"trouve\": false, \"cherche\": \"<ce que tu as essaye>\"}. C'est une "
    "reponse utile : elle dit que le chiffre n'est pas defendable en "
    "l'etat. N'invente jamais une reference approchante."
)


def demande(chiffre, aujourdhui=None):
    """Le message envoyé à l'agent — il dit CE QU'ON CHERCHE, pas ce qu'on
    espère trouver."""
    c = chiffre if isinstance(chiffre, dict) else {}
    b = besoin(c, aujourdhui)
    lignes = [
        "Chiffre publie : %s" % (c.get("affiche") or c.get("valeur")),
        "Ce qu'il affirme : %s" % (c.get("dit") or ""),
        "Date de la mesure rapportee : %s" % (c.get("mesure_le") or "inconnue"),
        "Source annoncee (a confirmer) : %s" % (c.get("source") or "aucune"),
    ]
    if c.get("a_confirmer"):
        lignes.append("Reserve ecrite par le cabinet : %s" % c["a_confirmer"])
    lignes.append("")
    if b["cle"] == "edition_suivante":
        lignes.append("CE QU'ON CHERCHE : l'edition SUIVANTE de ce rapport, "
                      "publiee APRES le %s. Un document plus ancien ou de la "
                      "meme date ne repond pas." % (c.get("mesure_le") or "?"))
    else:
        lignes.append("CE QU'ON CHERCHE : le document public d'origine, "
                      "ouvrable, ou ce chiffre figure.")
    lignes += [
        "",
        "Reponds par cet objet JSON exactement :",
        '{"trouve": true, "lien": "<adresse https complete>", '
        '"editeur": "<qui publie>", "titre": "<titre du document>", '
        '"publie_le": "AAAA-MM-JJ", '
        '"citation": "<phrase copiee mot pour mot, contenant le nombre>", '
        '"echantillon": "<taille et nature de l\'echantillon, ou null>"}',
    ]
    return "\n".join(lignes)


# ═══════════════════════════════════════════════════════════════════════
# 4. LA VÉRIFICATION — ELLE ROUVRE LA PAGE ELLE-MÊME
# ═══════════════════════════════════════════════════════════════════════

def _texte(v):
    return "" if v is None else str(v).strip()


def _sans_accent(t):
    return "".join(x for x in unicodedata.normalize("NFD", t)
                   if unicodedata.category(x) != "Mn")


def _normaliser(t):
    """Ce qui permet de comparer une citation à la page dont elle est tirée.

    Les accents, la casse, les espaces et les apostrophes typographiques ne
    sont pas des faits. L'ORTHOGRAPHE DES MOTS, ELLE, EST GARDÉE — c'est
    justement ce qu'on vérifie.
    """
    t = _sans_accent(_texte(t)).lower()
    for a, b in (("’", "'"), ("‘", "'"), ("«", '"'),
                 ("»", '"'), ("–", "-"), ("—", "-"),
                 (" ", " "), (" ", " ")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def ecritures_du_nombre(valeur):
    """Les façons dont un même nombre peut s'écrire dans une phrase.

    « 7,2 » et « 7.2 » sont le même chiffre ; « 88.0 » ne s'écrit jamais
    ainsi dans une phrase. Sans cette table, le contrôle du nombre
    refuserait des citations justes — et on le désactiverait.
    """
    try:
        v = float(valeur)
    except (TypeError, ValueError):
        return set()
    formes = set()
    if v == int(v):
        formes.add(str(int(v)))
    else:
        t = ("%g" % v)
        formes.add(t)
        formes.add(t.replace(".", ","))
    return formes


def _contient_le_nombre(citation, valeur):
    """Le nombre figure-t-il dans la phrase, en tant que NOMBRE ?

    « 13 » est contenu dans « 2013 », et une citation parlant d'une année
    passerait sans cette précaution.
    """
    t = _normaliser(citation)
    for forme in ecritures_du_nombre(valeur):
        motif = r"(?<![0-9.,])" + re.escape(forme) + r"(?![0-9])"
        if re.search(motif, t):
            return True
    return False


def _jour(v):
    if isinstance(v, datetime.date):
        return v
    t = _texte(v)
    if not t:
        return None
    try:
        return datetime.date(*(int(x) for x in t.split("-")[:3]))
    except (TypeError, ValueError):
        return None


def _extraire_json(brut):
    t = _texte(brut)
    if not t:
        return None
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t).strip()
    try:
        o = json.loads(t)
        return o if isinstance(o, dict) else None
    except Exception:
        pass
    d, f = t.find("{"), t.rfind("}")
    if d < 0 or f <= d:
        return None
    try:
        o = json.loads(t[d:f + 1])
        return o if isinstance(o, dict) else None
    except Exception:
        return None


def _refus(motif, detail=None, bredouille=False, cherche=None):
    return {"trouve": False, "a_completer": True, "motif": motif,
            "motif_texte": MOTIFS.get(motif, motif), "detail": detail,
            "bredouille": bredouille, "cherche": cherche,
            "statut": "en_attente", "appui": 0.0, "fragile": True,
            "lien": None, "editeur": None, "titre": None,
            "publie_le": None, "citation": None, "echantillon": None}


def verifier(chiffre, brut, ouvrir, aujourdhui=None):
    """La réponse de l'agent tient-elle devant la page qu'elle cite ?

    `ouvrir(adresse) -> texte` est INJECTÉE, comme `compter_mcp` le fait
    déjà pour le registre MCP : ce module n'ouvre aucune connexion par
    lui-même, et la vérification s'éprouve sans réseau.
    """
    demande_ = chiffre if isinstance(chiffre, dict) else {}
    if demande_.get("cle") not in socle.CHIFFRES_PAR_CLE:
        return _refus("chiffre_inconnu", detail=demande_.get("cle"))
    # ON VÉRIFIE CONTRE LE CHIFFRE SERVI, pas contre celui passé par
    # l'appelant : sinon une référence déjà validée se re-validerait.
    c = vue(demande_["cle"], aujourdhui) or demande_
    b = besoin(c, aujourdhui)
    if not b["urgent"]:
        return _refus("rien_a_chercher", detail=b["cle"])

    o = _extraire_json(brut)
    if o is None:
        return _refus("reponse_vide" if not _texte(brut) else "reponse_illisible")

    # BREDOUILLE EST UNE RÉPONSE, PAS UN ÉCHEC. Elle dit que le chiffre
    # n'est pas défendable en l'état, ce qui est une information que
    # personne n'avait.
    if o.get("trouve") is False:
        return _refus("aucune_source_publique", bredouille=True,
                      cherche=_texte(o.get("cherche")) or None)

    manquants = [ch["cle"] for ch in CHAMPS
                 if ch["obligatoire"] and not _texte(o.get(ch["cle"]))]
    if manquants:
        return _refus("reference_incomplete", detail=", ".join(manquants))

    lien = _texte(o.get("lien"))
    u = urllib.parse.urlparse(lien)
    if u.scheme not in ("http", "https") or not u.netloc:
        return _refus("lien_invalide", detail=lien[:120])

    publie = _jour(o.get("publie_le"))
    if publie is None:
        return _refus("date_illisible", detail=_texte(o.get("publie_le"))[:40])
    mesure = _jour(c.get("mesure_le"))
    if mesure and publie < mesure:
        return _refus("date_impossible",
                      detail="publié %s, mesure %s" % (publie, mesure))
    if b["cle"] == "edition_suivante" and mesure and publie <= mesure:
        return _refus("edition_pas_plus_recente",
                      detail="publié %s, mesure en place %s" % (publie, mesure))

    citation = _texte(o.get("citation"))[:CITATION_MAX]
    if len(citation) < CITATION_MIN:
        return _refus("citation_trop_courte", detail=citation)
    if not _contient_le_nombre(citation, c.get("valeur")):
        return _refus("citation_sans_le_chiffre", detail=citation[:160])

    # LE CONTRÔLE QUI COMPTE : on rouvre la page. L'agent n'est pas cru sur
    # parole, et ce contrôle-ci ne consulte aucun modèle.
    try:
        page = ouvrir(lien)
    except Exception as e:
        return _refus("lien_injoignable", detail=str(e)[:160])
    if not _texte(page):
        return _refus("lien_injoignable", detail="page vide")
    if _normaliser(citation) not in _normaliser(page):
        return _refus("citation_introuvable", detail=citation[:160])

    presents = sum(1 for ch in CHAMPS if _texte(o.get(ch["cle"])))
    appui = round(presents / float(len(CHAMPS)), 2)

    return {
        "trouve": True, "a_completer": False, "motif": None,
        "motif_texte": None, "detail": None, "bredouille": False,
        "cherche": None, "statut": "en_attente",
        "lien": lien,
        "editeur": _texte(o.get("editeur"))[:200],
        "titre": _texte(o.get("titre"))[:300],
        "publie_le": publie.isoformat(),
        "citation": citation,
        "echantillon": _texte(o.get("echantillon"))[:200] or None,
        "appui": appui,
        "fragile": appui < SEUIL_FRAGILE,
        "besoin": b["cle"],
    }


# ═══════════════════════════════════════════════════════════════════════
# 5. LA DÉCISION — LE MAGASIN EST CELUI DU SOCLE
# ═══════════════════════════════════════════════════════════════════════
# PREMIÈRE ÉCRITURE, ET POURQUOI ELLE ÉTAIT FAUSSE. Ce module tenait son
# propre magasin de sources et sa propre fonction `chiffres()` qui les
# superposait. Le bandeau public, lui, appelle `chiffres_securite_ia` — il
# n'aurait donc rien vu des références validées, et deux vérités auraient
# coexisté pour une même page. Le magasin vit désormais là où vivent déjà
# les chiffres, à côté du décompte MCP qui se superpose de la même façon.

DECISIONS = {
    "valider": {"nom": "Retenir cette référence", "pose": True},
    "ecarter": {"nom": "Écarter", "pose": False},
}


def appliquer(chiffre, proposition, decision, qui, motif=None, le=None):
    """LA SEULE PORTE VERS LE BANDEAU — ET ELLE EXIGE UN NOM.

    Une référence posée change ce qu'une page publique affirme de ses
    sources. Sans le nom d'une personne, ce serait un programme qui décide
    de ce que le cabinet déclare savoir.
    """
    p = proposition if isinstance(proposition, dict) else {}
    qui = _texte(qui)
    if not qui:
        return {"ok": False, "motif": "decideur_absent",
                "motif_texte": "Aucune personne identifiée ne porte cette "
                               "décision : le bandeau ne bouge pas."}
    if decision not in DECISIONS:
        return {"ok": False, "motif": "decision_inconnue",
                "motif_texte": "La décision doit être « valider » ou "
                               "« écarter »."}
    if p.get("statut") != "en_attente":
        return {"ok": False, "motif": "deja_decidee",
                "motif_texte": "Cette proposition a déjà reçu une décision."}
    if not DECISIONS[decision]["pose"]:
        return {"ok": True, "statut": "ecartee", "decide_par": qui,
                "pose": None, "motif_decision": _texte(motif) or None}
    if p.get("a_completer") or not p.get("lien"):
        return {"ok": False, "motif": "rien_a_valider",
                "motif_texte": "Cette proposition ne porte aucune référence "
                               "vérifiée."}

    cle = (chiffre or {}).get("cle")
    champs = {k: p.get(k) for k in
              ("lien", "editeur", "titre", "publie_le", "citation",
               "echantillon")}
    pose = socle.poser_source(cle, champs, qui, le)
    if pose is None:
        return {"ok": False, "motif": "chiffre_inconnu",
                "motif_texte": MOTIFS["chiffre_inconnu"]}
    return {"ok": True, "statut": "validee", "decide_par": qui,
            "motif_decision": _texte(motif) or None, "pose": pose}


def referentiel(aujourdhui=None):
    return {
        "version": VERSION,
        "besoins": {k: dict(v) for k, v in BESOINS.items()},
        "champs": [dict(c) for c in CHAMPS],
        "motifs": dict(MOTIFS),
        "decisions": {k: dict(v) for k, v in DECISIONS.items()},
        "a_tracer": a_tracer(aujourdhui),
        "seuil_fragile": SEUIL_FRAGILE,
        "citation_min": CITATION_MIN,
    }


# ═══════════════════════════════════════════════════════════════════════
# 6. LE RÉFÉRENTIEL SE CONTREDIT-IL ? CONTRÔLÉ À L'IMPORT
# ═══════════════════════════════════════════════════════════════════════

def _verifier():
    assert set(BESOINS) >= {"source_absente", "edition_suivante", "rien"}
    for b in BESOINS.values():
        assert b["pourquoi"].strip(), "un besoin ne dit pas pourquoi"
    urgents = [k for k, v in BESOINS.items() if v["urgent"]]
    assert urgents, "aucun besoin n'appelle de travail"
    assert not BESOINS["rien"]["urgent"]

    cles = [c["cle"] for c in CHAMPS]
    assert len(cles) == len(set(cles)), "deux champs portent la même clé"
    for nom in ("lien", "citation", "publie_le"):
        assert _CHAMPS[nom]["obligatoire"], "%s doit être obligatoire" % nom
    for c in CHAMPS:
        assert c["pourquoi"].strip(), "le champ %s ne dit pas pourquoi" % c["cle"]

    assert any(d["pose"] for d in DECISIONS.values())
    assert any(not d["pose"] for d in DECISIONS.values())
    assert 0.0 < SEUIL_FRAGILE <= 1.0
    assert CITATION_MIN >= 10 and CITATION_MAX > CITATION_MIN

    # Les clés visées existent bien au bandeau.
    assert socle.CHIFFRES, "le bandeau ne porte aucun chiffre"


_verifier()
