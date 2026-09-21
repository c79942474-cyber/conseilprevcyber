# -*- coding: utf-8 -*-
"""LES CHIFFRES DE LA SÉCURITÉ DE L'IA — ET CE QUI LES REND CITABLES.

═══ POURQUOI UN MODULE, ET PAS SIX NOMBRES DANS LE GABARIT ═══════════════
Un bandeau de chiffres est la partie d'une page qui vieillit le plus vite et
qui se voit le moins vieillir. « 88 % » reste parfaitement lisible trois ans
après l'enquête qui l'a produite ; rien dans sa typographie ne dit qu'il date.
Écrits en dur dans le HTML, ces six nombres auraient été justes le jour de
leur pose et faux ensuite, sans que personne ne puisse dire quand la bascule
a eu lieu.

CHAQUE CHIFFRE PORTE DONC QUATRE CHOSES et non une : sa valeur, sa SOURCE, la
date de ce qu'il MESURE, et la date à laquelle on l'a vérifié pour la dernière
fois. Le module en déduit un âge, et la page affiche l'âge.

═══ CE QUE « TENIR À JOUR » VEUT DIRE ICI, HONNÊTEMENT ═══════════════════
Les six chiffres ne sont pas de même nature, et les confondre produirait une
promesse intenable.

  • UN SEUL EST RE-MESURABLE : le nombre de serveurs au registre public MCP.
    Il s'obtient en paginant un registre ouvert, donc il se recompte — et il
    se recompte SEUL, par le fil périodique en bas de fichier.

  • LES CINQ AUTRES SONT DES CHIFFRES DE RAPPORT. Aucune interface publique
    ne sert « 88 % des organisations rapportent un incident » : ce nombre
    existe dans une enquête, à une date, et il ne changera plus. On ne le
    rafraîchit pas — on le REMPLACE, quand l'édition suivante paraît. Ce qui
    s'automatise, ce n'est pas leur valeur : c'est leur VIEILLISSEMENT, et
    l'avertissement qui tombe quand ils passent la péremption.

Prétendre l'inverse — une table de chiffres « mise à jour en continu » qui ne
se met à jour que par une main — est exactement le genre d'affirmation qu'une
direction vérifie une fois, et cesse ensuite de croire sur le reste de la page.

═══ LA SOURCE EST UN CHAMP OBLIGATOIRE, ET SON ABSENCE SE DIT ═══════════
La garde en bas de fichier refuse un chiffre sans source ni date. Mais un
chiffre dont la source n'est pas ENCORE établie ne disparaît pas pour autant :
il porte `a_confirmer`, et la page l'affiche comme tel. Un cabinet qui publie
« 7,2 % » sans pouvoir dire d'où il vient se fait reprendre au premier comité
— et c'est la page entière qui perd son crédit, pas la tuile.
"""
import datetime
import json
import threading
import urllib.parse
import urllib.request


# ═══════════════════════════════════════════════════════════════════════════
#  LE TEMPS — INJECTÉ, JAMAIS PRIS À L'HORLOGE DANS UN CALCUL
# ═══════════════════════════════════════════════════════════════════════════

def _jour(valeur, defaut=None):
    if isinstance(valeur, datetime.date):
        return valeur
    t = str(valeur or "").strip()
    if not t:
        return defaut
    try:
        return datetime.date(*(int(x) for x in t.split("-")))
    except (TypeError, ValueError):
        return defaut


def _aujourdhui(valeur=None):
    return _jour(valeur) or datetime.date.today()


# ═══════════════════════════════════════════════════════════════════════════
#  LA PÉREMPTION — UN SEUIL PAR NATURE DE CHIFFRE
# ═══════════════════════════════════════════════════════════════════════════
#
# POURQUOI DEUX SEUILS ET NON UN. Un décompte de registre public bouge toutes
# les semaines : à trente jours il est déjà discutable. Une enquête annuelle
# reste la référence jusqu'à l'édition suivante : lui appliquer trente jours
# ferait clignoter en permanence un chiffre parfaitement valide, et on
# apprendrait à ignorer le signal — ce qui coûte plus cher que de ne pas
# l'avoir mis.

PEREMPTION = {
    "registre": 30,     # un décompte ouvert, qui se recompte
    "enquete": 400,     # une enquête : valable jusqu'à l'édition suivante
    "prevision": 550,   # une prévision datée, valable jusqu'à son échéance
}

ETATS = {
    "frais": "À jour",
    "a_revoir": "À revérifier",
    "perime": "Périmé — à remplacer",
}


# ═══════════════════════════════════════════════════════════════════════════
#  LES SIX CHIFFRES
# ═══════════════════════════════════════════════════════════════════════════
#
# L'ORDRE N'EST PAS DÉCORATIF. Il raconte une seule chose, dans l'ordre où
# elle se démontre : ça arrive (88), on ne le voit pas (82), personne n'en
# répond (7,2), on ne l'encadre pas (13), la surface se standardise (MCP), et
# voilà ce que ça coûte (40). Trier par valeur décroissante aurait fait un
# classement de nombres ; trier ainsi fait une démonstration.

CHIFFRES = (
    {"cle": "incidents",
     "valeur": 88.0, "unite": "%", "affiche": "88 %",
     "dit": "des organisations rapportent un incident de sécurité lié à un "
            "agent IA sur douze mois",
     "nature": "enquete",
     "source": "Enquête sectorielle 2025 sur la sécurité des agents IA",
     "lien": None,
     "mesure_le": "2025-12-31",
     "verifie_le": "2026-09-19",
     "a_confirmer": "L'enquête exacte et son échantillon restent à nommer : "
                    "le chiffre a été transmis sans sa référence."},
    {"cle": "shadow_agents",
     "valeur": 82.0, "unite": "%", "affiche": "82 %",
     "dit": "ont découvert un agent ou un flux IA inconnu de leur équipe de "
            "sécurité",
     "nature": "enquete",
     "source": "Enquête sectorielle 2025 sur la sécurité des agents IA",
     "lien": None,
     "mesure_le": "2025-12-31",
     "verifie_le": "2026-09-19",
     "a_confirmer": "Même enquête que le chiffre précédent, et même réserve : "
                    "la référence reste à établir."},
    {"cle": "responsable",
     "valeur": 7.2, "unite": "%", "affiche": "7,2 %",
     "dit": "seulement ont désigné un responsable formel du comportement de "
            "leurs agents",
     "nature": "enquete",
     "source": "Enquête sectorielle 2025 sur la sécurité des agents IA",
     "lien": None,
     "mesure_le": "2025-12-31",
     "verifie_le": "2026-09-19",
     "a_confirmer": "Une décimale sur un chiffre d'enquête suppose un "
                    "échantillon nommé : sans lui, « 7,2 » se défend moins "
                    "bien que « moins de 10 »."},
    {"cle": "gouvernance",
     "valeur": 13.0, "unite": "%", "affiche": "13 %",
     "dit": "estiment disposer d'une gouvernance adéquate de leurs systèmes "
            "agentiques",
     "nature": "enquete",
     "source": "Enquête sectorielle 2025 sur la sécurité des agents IA",
     "lien": None,
     "mesure_le": "2025-12-31",
     "verifie_le": "2026-09-19",
     "a_confirmer": "Déclaratif : ce chiffre mesure ce que les répondants "
                    "ESTIMENT, pas ce qui est en place. La nuance change ce "
                    "qu'on peut en conclure, et la référence reste à établir."},
    # ── LE SEUL QUI SE RECOMPTE ──────────────────────────────────────────
    {"cle": "mcp",
     "valeur": None, "unite": "", "affiche": None,
     "dit": "serveurs au registre public MCP : le point de passage des agents "
            "vers les outils se standardise",
     "nature": "registre",
     "source": "Registre public Model Context Protocol",
     "lien": "https://registry.modelcontextprotocol.io",
     "mesure_le": None,
     "verifie_le": None,
     "a_confirmer": None,
     # CE CHIFFRE-LÀ SE MESURE. La valeur ci-dessus est nulle à dessein :
     # elle est remplie par `rafraichir_mcp()`, et une valeur de repli écrite
     # ici aurait été servie en silence le jour où le registre devient
     # injoignable — un chiffre faux valant mieux qu'un trou, croit-on, jusqu'à
     # ce qu'on s'aperçoive que personne ne savait qu'il était faux.
     "recomptable": True,
     "compte": "noms de serveurs distincts en statut actif"},
    {"cle": "abandons",
     "valeur": 40.0, "unite": "%", "affiche": "plus de 40 %",
     "dit": "des projets d'IA agentique seraient abandonnés d'ici fin 2027, "
            "par écart de gouvernance et de maîtrise des coûts",
     "nature": "prevision",
     "source": "Gartner",
     "lien": None,
     "mesure_le": "2025-06-25",
     "verifie_le": "2026-09-19",
     "a_confirmer": "La prévision est bien de Gartner ; la publication exacte "
                    "reste à citer, et le site du cabinet n'est pas "
                    "atteignable depuis l'environnement de construction."},
)

CHIFFRES_PAR_CLE = {c["cle"]: c for c in CHIFFRES}


# ═══════════════════════════════════════════════════════════════════════════
#  LE COMPTE DU REGISTRE MCP — MÉMORISÉ, ET DATÉ
# ═══════════════════════════════════════════════════════════════════════════

REGISTRE_MCP = "https://registry.modelcontextprotocol.io/v0/servers"
_PAGE = 100
_PAGES_MAX = 3000

_ETAT_MCP = {"valeur": None, "le": None, "motif": None}
_VERROU = threading.Lock()


def compter_mcp(pages_max=_PAGES_MAX, page=_PAGE, ouvrir=None):
    """Le nombre de serveurs distincts ACTIFS au registre public.

    CE QUI EST COMPTÉ EST DIT, parce que trois comptes différents sortent du
    même registre : les entrées (un serveur y figure une fois par version),
    les noms distincts, et les noms distincts encore actifs. L'écart entre le
    premier et le dernier se chiffre en dizaines de milliers — annoncer « des
    serveurs » sans dire lequel des trois on compte, c'est publier un nombre
    que personne ne peut reproduire.
    """
    ouvrir = ouvrir or (lambda u: urllib.request.urlopen(u, timeout=45))
    noms, curseur, pages = set(), None, 0
    while pages < pages_max:
        q = {"limit": str(page)}
        if curseur:
            q["cursor"] = curseur
        try:
            with ouvrir(REGISTRE_MCP + "?" + urllib.parse.urlencode(q)) as r:
                d = json.loads(r.read().decode("utf-8"))
        except Exception as e:                      # noqa: BLE001
            # ON REND CE QU'ON A ET ON DIT QU'IL EST PARTIEL. Un compte
            # interrompu servi comme un compte complet serait plus bas que la
            # réalité, et il se lirait comme une décrue du registre.
            return {"ok": False, "motif": "registre_injoignable",
                    "detail": type(e).__name__, "partiel": len(noms),
                    "pages": pages}
        lot = d.get("servers") or []
        if not lot:
            break
        for e in lot:
            s = e.get("server") or {}
            meta = ((e.get("_meta") or {})
                    .get("io.modelcontextprotocol.registry/official") or {})
            nom = s.get("name")
            if nom and meta.get("status") == "active":
                noms.add(nom)
        pages += 1
        curseur = (d.get("metadata") or {}).get("nextCursor")
        if not curseur:
            break
    if pages >= pages_max and curseur:
        return {"ok": False, "motif": "registre_trop_long",
                "partiel": len(noms), "pages": pages}
    return {"ok": True, "valeur": len(noms), "pages": pages}


def rafraichir_mcp(aujourdhui=None, ouvrir=None, pages_max=_PAGES_MAX):
    """Recompte le registre et retient le résultat AVEC sa date."""
    r = compter_mcp(pages_max=pages_max, ouvrir=ouvrir)
    with _VERROU:
        if r.get("ok"):
            _ETAT_MCP.update({"valeur": r["valeur"],
                              "le": _aujourdhui(aujourdhui).isoformat(),
                              "motif": None})
        else:
            # LE COMPTE PRÉCÉDENT RESTE EN PLACE, ET SA DATE AUSSI. Écraser un
            # chiffre daté par un échec l'aurait fait disparaître de la page ;
            # le garder avec sa vraie date le fait simplement vieillir, ce qui
            # est exactement ce qui s'est passé.
            _ETAT_MCP["motif"] = r.get("motif")
    return dict(r)


def etat_mcp():
    with _VERROU:
        return dict(_ETAT_MCP)


def poser_mcp(valeur, le):
    """Pose un compte connu — utilisé au démarrage et par les règles."""
    with _VERROU:
        _ETAT_MCP.update({"valeur": int(valeur),
                          "le": _jour(le).isoformat(), "motif": None})


# ═══════════════════════════════════════════════════════════════════════════
#  LES SOURCES ÉTABLIES APRÈS COUP — SUPERPOSÉES, JAMAIS ÉCRITES ICI
# ═══════════════════════════════════════════════════════════════════════════
#
# CINQ DES SIX CHIFFRES SONT PUBLIÉS SANS ADRESSE OUVRABLE, et le bandeau le
# dit déjà dans sa réserve. Quand une référence est enfin établie — par
# `veille_chiffres`, puis validée par une personne —, elle se pose ICI et se
# superpose au chiffre, exactement comme le décompte MCP se superpose au sien.
#
# POURQUOI PAS UNE RÉÉCRITURE DU SOURCE. Un programme qui modifie le fichier
# où sont écrits les chiffres d'une page publique est précisément ce qu'on
# refuse ailleurs. La superposition laisse le source lisible et vrai : il dit
# ce que le cabinet savait au moment où il l'a écrit, et le magasin dit ce
# qu'on a appris depuis, avec le nom de qui l'a validé.

_SOURCES = {}


def poser_source(cle, champs, par, le=None):
    """Pose la référence établie d'un chiffre, avec le nom qui la porte."""
    if cle not in CHIFFRES_PAR_CLE:
        return None
    with _VERROU:
        _SOURCES[cle] = dict(
            {k: champs.get(k) for k in
             ("lien", "editeur", "titre", "publie_le", "citation",
              "echantillon")},
            valide_par=str(par or "").strip(),
            valide_le=(_jour(le) or datetime.date.today()).isoformat())
        return dict(_SOURCES[cle])


def sources_confirmees():
    with _VERROU:
        return {k: dict(v) for k, v in _SOURCES.items()}


def oublier_source(cle):
    with _VERROU:
        return _SOURCES.pop(cle, None) is not None


def charger_sources(magasin):
    """Recharge les références validées — au démarrage, depuis la base.

    SANS CELA, UN REDÉMARRAGE FERAIT SILENCIEUSEMENT REVENIR LA RÉSERVE
    « source à confirmer » sur une page où quelqu'un l'avait levée. Un
    retour en arrière que personne n'a décidé et que rien n'annonce est
    pire que l'absence de la fonction.
    """
    if not isinstance(magasin, dict):
        return 0
    poses = 0
    for cle, champs in magasin.items():
        if isinstance(champs, dict) and poser_source(
                cle, champs, champs.get("valide_par"), champs.get("valide_le")):
            poses += 1
    return poses


# ═══════════════════════════════════════════════════════════════════════════
#  LA FRAÎCHEUR
# ═══════════════════════════════════════════════════════════════════════════

def fraicheur(chiffre, aujourdhui=None):
    """L'âge du chiffre, et ce qu'il faut en faire.

    L'ÂGE SE COMPTE DEPUIS LA MESURE, PAS DEPUIS LA VÉRIFICATION. Rouvrir un
    rapport de 2024 aujourd'hui ne rajeunit pas son enquête : ça met à jour ce
    qu'on sait de lui, pas ce qu'il mesure. Compter depuis la vérification
    permettrait de garder un chiffre éternellement « frais » en le relisant.
    """
    jour = _aujourdhui(aujourdhui)
    mesure = _jour(chiffre.get("mesure_le"))
    if chiffre.get("cle") == "mcp":
        e = etat_mcp()
        mesure = _jour(e.get("le"))
    if mesure is None:
        return {"age_jours": None, "etat": "inconnu",
                "dit": ETATS.get("perime"), "seuil": None}
    age = (jour - mesure).days
    seuil = PEREMPTION[chiffre["nature"]]
    etat = ("frais" if age <= seuil
            else "a_revoir" if age <= seuil * 2 else "perime")
    return {"age_jours": age, "etat": etat, "dit": ETATS[etat], "seuil": seuil}


def _mois(age):
    if age is None:
        return None
    if age == 0:
        return "aujourd'hui"
    if age < 45:
        return "%d jour%s" % (age, "s" if age > 1 else "")
    m = int(round(age / 30.44))
    if m < 24:
        return "%d mois" % m
    return "%d ans" % int(round(age / 365.25))


def _milliers(n):
    """13328 → « 13 328 », avec une espace insécable étroite.

    UN NOMBRE À CINQ CHIFFRES SANS SÉPARATEUR SE LIT DE TRAVERS, et celui-ci
    est fait pour être cité. L'espace est insécable : une coupure de ligne
    entre le 13 et le 328 produirait deux nombres.
    """
    return "\u202f".join(reversed(
        [str(n)[::-1][i:i + 3][::-1] for i in range(0, len(str(n)), 3)]))


def chiffres(aujourdhui=None):
    """Les six chiffres, chacun avec son âge et son état.

    UN CHIFFRE SANS VALEUR N'EST PAS RENDU À ZÉRO. Le décompte du registre
    vaut `None` tant que personne ne l'a compté : rendre 0 aurait affiché
    « 0 serveur MCP » sur la page d'un cabinet qui explique qu'il faut les
    inventorier.
    """
    jour = _aujourdhui(aujourdhui)
    sortie = []
    for c in CHIFFRES:
        d = dict(c)
        if c["cle"] == "mcp":
            e = etat_mcp()
            d["valeur"] = e.get("valeur")
            d["mesure_le"] = e.get("le")
            d["verifie_le"] = e.get("le")
            d["affiche"] = (_milliers(e["valeur"])
                            if e.get("valeur") is not None else None)
            d["motif_absence"] = e.get("motif")
        # LA RÉFÉRENCE ÉTABLIE APRÈS COUP LÈVE LA RÉSERVE — c'est tout
        # l'objet de l'opération. La garder afficherait « référence à
        # établir » à côté du lien qui l'établit.
        src = _SOURCES.get(c["cle"])
        if src:
            d["lien"] = src.get("lien") or d.get("lien")
            d["source"] = src.get("editeur") or d.get("source")
            d["titre_source"] = src.get("titre")
            d["citation"] = src.get("citation")
            d["echantillon"] = src.get("echantillon")
            d["source_validee_par"] = src.get("valide_par")
            d["source_validee_le"] = src.get("valide_le")
            d["a_confirmer"] = None
        f = fraicheur(d, jour)
        d["fraicheur"] = f
        d["age_dit"] = _mois(f["age_jours"])
        d["servi"] = d.get("affiche") is not None
        sortie.append(d)
    return sortie


def bandeau(aujourdhui=None):
    """Ce que la page affiche, en une seule réponse."""
    jour = _aujourdhui(aujourdhui)
    liste = chiffres(jour)
    servis = [c for c in liste if c["servi"]]
    a_revoir = [c for c in servis if c["fraicheur"]["etat"] != "frais"]
    sans_source = [c for c in servis if c.get("a_confirmer")]
    return {
        "ok": True,
        "titre": "IA Security en chiffres",
        "aujourdhui": jour.isoformat(),
        "chiffres": liste,
        "servis": len(servis),
        "a_revoir": [c["cle"] for c in a_revoir],
        "sources_a_confirmer": [c["cle"] for c in sans_source],
        # LA RÉSERVE EST RENDUE AVEC LES CHIFFRES, et non écrite dans la page :
        # un bandeau qui circule en capture d'écran emporte sa réserve.
        "reserve":
            "Un seul de ces chiffres se recompte : le registre MCP, dénombré "
            "ici par pagination du registre public. Les autres sont des "
            "chiffres de rapport — ils ne se rafraîchissent pas, ils "
            "vieillissent, et leur âge est affiché. "
            + ("Aucune source n'attend confirmation."
               if not sans_source else
               "%d d'entre eux attendent encore la référence exacte de leur "
               "source et sont signalés comme tels." % len(sans_source)),
    }


def referentiel():
    return {"chiffres": list(CHIFFRES), "peremption": dict(PEREMPTION),
            "etats": dict(ETATS), "registre_mcp": REGISTRE_MCP}


# ═══════════════════════════════════════════════════════════════════════════
#  LA GARDE
# ═══════════════════════════════════════════════════════════════════════════

def _verifier():
    fautes = []
    if len(CHIFFRES_PAR_CLE) != len(CHIFFRES):
        fautes.append("deux chiffres portent la même clé")
    for c in CHIFFRES:
        ou = "le chiffre « %s »" % c["cle"]
        if not str(c.get("source") or "").strip():
            fautes.append("%s ne nomme aucune source" % ou)
        if c.get("nature") not in PEREMPTION:
            fautes.append("%s n'a pas de nature connue : %r" % (ou, c.get("nature")))
        if not str(c.get("dit") or "").strip():
            fautes.append("%s ne dit pas ce qu'il mesure" % ou)
        # UN CHIFFRE FIGÉ DOIT PORTER SA DATE. Celui du registre n'en a pas
        # ici : il la reçoit du comptage, et c'est la seule exception.
        if c["cle"] != "mcp" and _jour(c.get("mesure_le")) is None:
            fautes.append("%s ne dit pas de quand il date" % ou)
        if c["cle"] != "mcp" and c.get("valeur") is None:
            fautes.append("%s n'a pas de valeur" % ou)
        if c["cle"] != "mcp" and not str(c.get("affiche") or "").strip():
            fautes.append("%s n'a pas de forme affichable" % ou)
    # LA RÉCIPROQUE : un champ `a_confirmer` vide sur un chiffre sans lien ET
    # sans source nommément identifiable ferait passer une incertitude pour
    # une certitude. On exige que l'absence de référence soit DITE.
    for c in CHIFFRES:
        if not c.get("lien") and not c.get("a_confirmer") and c["cle"] != "mcp":
            fautes.append("le chiffre « %s » n'a ni lien vérifiable ni réserve "
                          "déclarée : son incertitude ne se voit nulle part"
                          % c["cle"])
    if fautes:
        raise RuntimeError("chiffres_securite_ia — table incohérente : "
                           + " ; ".join(fautes))
    return []


# ═══════════════════════════════════════════════════════════════════════════
#  LE DERNIER COMPTE CONNU — POSÉ AU CHARGEMENT, ET DATÉ
# ═══════════════════════════════════════════════════════════════════════════
#
# POURQUOI UNE VALEUR DE DÉPART, ALORS QUE LE FIL LA RECOMPTE. Le comptage
# demande plus de mille pages et quelques minutes ; entre le démarrage du
# service et la fin du premier comptage, la page afficherait un tiret. Un
# tiret n'est pas faux, mais il n'apprend rien, et il tombe précisément au
# moment où le service vient d'être redéployé — c'est-à-dire quand on le
# regarde.
#
# CE QUI REND CETTE VALEUR HONNÊTE, C'EST SA DATE. Elle est posée avec le
# jour où elle a été mesurée, pas avec le jour du démarrage : elle vieillit
# donc à l'écran, exactement comme les chiffres d'enquête, jusqu'à ce que le
# fil la remplace. Une valeur de repli datée du démarrage aurait été
# éternellement « fraîche » et éternellement fausse.
#
# ET ELLE VAUT D'ÊTRE REGARDÉE. Le chiffre transmis pour ce bandeau annonçait
# 9 400 serveurs. Le comptage du registre en a trouvé 33 089 actifs le même
# jour, sur 1 084 pages — plus du triple. C'est la démonstration de ce que ce
# module existe pour éviter : un nombre parfaitement lisible, parfaitement
# citable, et périmé sans que rien ne le dise.
DERNIER_COMPTE_CONNU = {"valeur": 33089, "le": "2026-09-19",
                        "pages": 1084, "dont_toutes_versions": 33438}

poser_mcp(DERNIER_COMPTE_CONNU["valeur"], DERNIER_COMPTE_CONNU["le"])


_FAUTES = _verifier()
