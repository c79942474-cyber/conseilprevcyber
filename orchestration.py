# -*- coding: utf-8 -*-
"""LES PATRONS AGENTIQUES — planifier, chercher par point, écrire, se relire.

═══════════════════════════════════════════════════════════════════════════
 LE DÉFAUT QUE CE MODULE CORRIGE, MESURÉ AVANT D'ÉCRIRE UNE LIGNE
═══════════════════════════════════════════════════════════════════════════

Tout ce que la plateforme produit — les quatre-vingt-dix types de livrables
et les onze pièces d'un dossier de consultation — était écrit de la même
façon : UNE requête composée par des règles fixes, UNE recherche, UN appel au
modèle, et personne pour relire le résultat.

MESURÉ LE 17 SEPTEMBRE 2026, sur un fonds de douze documents et le type
« synthese-62443 », dont le plan de six sections est DÉJÀ déclaré dans la
donnée (`livrables.TYPES[*]["sections"]` — les quatre-vingt-dix en ont un) :

  · la requête unique ramène 4 documents ;
  · DEUX des documents qui répondent au plan ne sont jamais vus — la note de
    priorisation des recommandations et le plan de reprise, c'est-à-dire
    exactement ceux qui répondent aux sections « Recommandations priorisées »
    et « Prochaines étapes » ;
  · son troisième résultat sur quatre est une note carbone dont le texte dit
    « aucun lien avec les niveaux de sécurité » : du bruit qui occupe une
    place dans un budget de huit extraits.

LE PLAN EXISTAIT, ET LA RECHERCHE NE S'EN SERVAIT PAS. C'est le défaut en une
phrase. `ingenierie_dc.couverture_documentaire` interroge bien la base une
fois par point exigé — et ce chemin-là est le seul : il ne sert qu'aux pièces
de maîtrise d'œuvre qui portent une phase ET un code. Les quatre-vingt-dix
types de livrables et les onze pièces d'un marché n'y avaient pas droit.

INTERROGER PAR SECTION NE SUFFIT PAS, et la mesure le dit aussi : la même
note carbone ressort sur trois sections des six. Chercher mieux ramène plus
de bon ET plus de bruit. Il faut donc l'étape qui relit et rejette — et c'est
pourquoi ce module ne se contente pas de multiplier les requêtes.

═══════════════════════════════════════════════════════════════════════════
 LE SIGNAL QUI EXISTAIT DÉJÀ, ET QUE PERSONNE NE CONSOMMAIT
═══════════════════════════════════════════════════════════════════════════

`ao_redaction.rediger` rend depuis toujours `a_completer` : le nombre de
marques « [À COMPLÉTER » que LE MODÈLE LUI-MÊME a posées dans son brouillon.
C'est un aveu, écrit par celui qui sait — et un relevé des appelants montre
qu'il n'était que AFFICHÉ : `ingenierie-dc.js` le met en gras, et rien, nulle
part, ne va chercher ce qui manque. Le critique de ce module est le
consommateur qui manquait.

═══════════════════════════════════════════════════════════════════════════
 POURQUOI PAS LANGCHAIN NI SEMANTIC KERNEL
═══════════════════════════════════════════════════════════════════════════

La demande autorisait « ou équivalents », et la mesure a tranché.

PREMIÈRE RAISON — LE REGISTRE RGPD DEVIENDRAIT FAUX. `pip install langchain
langchain-anthropic langchain-community` tire QUARANTE ET UN paquets, dont
`langsmith`. Le registre des traitements (`rgpd.py`) nomme quatre
sous-traitants et QUATRE SEULEMENT : Render, Mistral AI, Anthropic, Brevo.
Un chemin de données supplémentaire, fût-il dormant, rendrait faux un
document qui engage le cabinet — et les invites en question portent les
documents du cabinet et les pièces de marché de ses clients.

DEUXIÈME RAISON — LA RÉSOLUTION DÉPLACERAIT UNE ÉPINGLE QUI COMPTE. Le même
dry-run montre que `anthropic` est retiré par la chaîne : il est épinglé ici
à `0.75.0`, et `ao_redaction` comme `assistant` sont écrits contre cette
version. Un cadre qui ramène sa propre borne décide à leur place.

TROISIÈME RAISON, LA PLUS SOLIDE — CE QU'IL FAUDRAIT ENVELOPPER N'EST PAS UN
MAGASIN DE VECTEURS. `rag.search` porte `public_only`, qui n'est pas un
réglage de confort : les extraits sont reproduits MOT POUR MOT dans un
document qui sort du site (voir `app._extraits_pour`). Le faire passer pour
un `BaseRetriever` obligerait soit à réimplémenter cette frontière dans
l'enveloppe, soit à la perdre. On n'enveloppe pas une frontière de
confidentialité pour gagner une abstraction.

CE QUE L'ON GARDE DU CADRE, EN REVANCHE, C'EST SA FORME. `Etape` a la
signature d'un Runnable, `Chaine` celle d'une séquence : adopter LangChain
plus tard se ferait en réécrivant ces deux classes, pas les cinq rôles.

═══════════════════════════════════════════════════════════════════════════
 CE QUI EST DÉTERMINISTE, ET POURQUOI C'EST LE POINT
═══════════════════════════════════════════════════════════════════════════

Le planificateur, le documentaliste et le vérificateur N'APPELLENT AUCUN
MODÈLE. Seuls le rédacteur et, s'il est fourni, le critique en demandent un.

Trois conséquences, et aucune n'est un détail :

  1. LE GAIN PRINCIPAL EST GRATUIT. Chercher par point et déclarer ce qui
     manque ne coûte pas un jeton de plus qu'aujourd'hui.
  2. CE MODULE S'ÉPROUVE SANS SIMULER UN MODÈLE. Une règle qui mesure la
     couverture mesure un fait, pas l'humeur d'un générateur.
  3. LE CHEMIN « SANS MODÈLE » DE LA PLATEFORME (`_trame_sans_modele`) EN
     PROFITE AUSSI — il rend un document de travail, et il a autant besoin de
     savoir ce que la base ne documente pas.
"""

import re


# ═══════════════════════════════════════════════════════════════════════════
#  LES BORNES — ET POURQUOI CHACUNE EXISTE
# ═══════════════════════════════════════════════════════════════════════════

# COMBIEN DE TOURS LA BOUCLE ACCEPTE. Trois, parce que les trois stratégies de
# reformulation ci-dessous sont épuisées à ce moment-là : un quatrième tour
# reposerait la même question. La borne n'est pas la garantie de terminaison
# — voir `_stagnation` — elle en est le filet.
TOURS_MAX = 3

# COMBIEN D'EXTRAITS PAR POINT. Le budget global de la rédaction est de huit
# extraits ; un plan fait six points. Trois par point, dédoublonnés, tiennent
# dans ce que le brief peut porter sans noyer la consigne.
PAR_POINT = 3

# EN DEÇÀ DE QUOI UNE SECTION EST « MINCE ». Mesuré sur les brouillons rendus
# par la plateforme : une section nourrie fait quatre cents signes ou plus ;
# en dessous de cent cinquante, c'est une phrase d'annonce suivie de rien.
MINCE = 150

# LA MARQUE QUE LE MODÈLE POSE LUI-MÊME. Reprise de `ao_redaction`, PAS
# recopiée : l'import est différé pour que ce module reste utilisable seul.
def _marque_a_completer():
    try:
        import ao_redaction                                       # noqa: PLC0415
        return ao_redaction._A_COMPLETER
    except Exception:
        return "[À COMPLÉTER"


# ═══════════════════════════════════════════════════════════════════════════
#  LES CINQ RÔLES — ORCHESTRATION MULTI-AGENTS
# ═══════════════════════════════════════════════════════════════════════════
#
# UN RÔLE N'EST PAS UNE INVITE DÉCORATIVE. Chacun porte trois choses : ce
# qu'il DÉCIDE, ce qu'il n'a PAS le droit de faire, et s'il consomme un
# modèle. Le troisième champ est celui qui coûte, et le deuxième celui qui
# protège — un rôle qui n'a pas le droit d'élargir la visibilité ne peut pas
# la perdre par mégarde au fond d'une boucle.

ROLES = {
    "planificateur": {
        "nom": "Planificateur",
        "decide": "Le plan : les points que le document DOIT couvrir.",
        "interdit": "Il n'écrit pas une ligne du document et ne cherche rien.",
        "modele": False,
        "pourquoi": "Le plan existait déjà dans la donnée (sections d'un type, "
                    "contenu exigé d'une pièce) ; personne ne le lisait.",
    },
    "documentaliste": {
        "nom": "Documentaliste",
        "decide": "Quoi chercher, pour QUEL point, et avec quel vocabulaire.",
        "interdit": "Il n'élargit JAMAIS la visibilité : un point que seuls "
                    "des documents internes couvriraient reste déclaré absent.",
        "modele": False,
        "pourquoi": "Une requête unique ne voyait pas deux des six documents "
                    "qui répondaient au plan.",
    },
    "redacteur": {
        "nom": "Rédacteur",
        "decide": "Le texte, section par section, sur les extraits reçus.",
        "interdit": "Il n'invente pas de source et ne complète pas un point "
                    "déclaré absent : il porte la marque et passe.",
        "modele": True,
        "pourquoi": "Un appel unique rendait le document d'un bloc, sans "
                    "qu'on sache quelle section avait manqué de matière.",
    },
    "critique": {
        "nom": "Critique",
        "decide": "Par point : couvert, mince, ou absent — et ce qui manque.",
        "interdit": "Il ne réécrit pas : il rend un verdict, le tour suivant "
                    "s'en sert. Un critique qui corrige masque ce qu'il corrige.",
        "modele": False,
        "pourquoi": "« a_completer » était produit depuis toujours et n'était "
                    "que affiché : aucun appelant n'allait chercher le manque.",
    },
    "verificateur": {
        "nom": "Vérificateur",
        "decide": "Ce qui, dans le texte, n'est adossé à AUCUNE source reçue.",
        "interdit": "Il ne juge pas le style et ne consomme pas de modèle : "
                    "un contrôle de provenance qui coûte un appel ne serait "
                    "pas passé sur chaque section.",
        "modele": False,
        "pourquoi": "Un chiffre qui ne vient ni des extraits ni de la fiche "
                    "du projet a été produit par le modèle — et rien ne le "
                    "distinguait d'un chiffre relevé.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  LA TRACE — CE QUI REND LE ReAct HONNÊTE
# ═══════════════════════════════════════════════════════════════════════════
#
# POURQUOI LA TRACE EST UN OBJET, ET PAS UN JOURNAL. Un ReAct dont on ne voit
# pas les tours est un appel unique qu'on a décrit avec plus de mots. Ce qui
# fait la différence entre les deux est vérifiable ou ne l'est pas : la trace
# porte, par tour, ce qui a été PENSÉ (quelle stratégie, et pourquoi
# celle-là), ce qui a été FAIT (la requête exacte), et ce qui a été OBSERVÉ
# (ce qui est revenu). Elle redescend avec le brouillon et s'écrit dans le
# document, en annexe.
#
# ELLE EST AUSSI CE QUI PERMET DE MESURER LE MODULE. Une règle qui veut
# vérifier que la relance a changé de vocabulaire lit la trace ; sans elle,
# elle ne pourrait que constater que la boucle a tourné.

class Trace:
    """Le registre des tours — pensée, action, observation."""

    def __init__(self):
        self.pas = []

    def noter(self, role, pensee, action, observation, tour=0):
        if role not in ROLES:
            raise ValueError("rôle inconnu de la trace : %s" % role)
        self.pas.append({
            "rang": len(self.pas) + 1,
            "tour": int(tour),
            "role": role,
            "pensee": str(pensee or ""),
            "action": str(action or ""),
            "observation": str(observation or ""),
        })
        return self.pas[-1]

    def tours(self):
        """Combien de tours distincts la boucle a réellement faits."""
        return len({p["tour"] for p in self.pas}) if self.pas else 0

    def par_role(self, role):
        return [p for p in self.pas if p["role"] == role]

    def markdown(self):
        """La trace en clair — ce qui part en annexe du document.

        ELLE NOMME LE RÔLE, PAS « L'IA ». Un lecteur qui reçoit le document
        doit pouvoir dire qui a décidé quoi ; « l'assistant a cherché » ne le
        lui dit pas.
        """
        if not self.pas:
            return ""
        out = ["## Comment ce document a été construit", "",
               "Chaque ligne dit ce qui a été cherché, et ce qui est revenu.", ""]
        tour = None
        for p in self.pas:
            if p["tour"] != tour:
                tour = p["tour"]
                out.append("")
                out.append("**Tour %d**" % (tour + 1))
            out.append("- *%s* — %s" % (ROLES[p["role"]]["nom"], p["pensee"]))
            if p["action"]:
                out.append("  - a cherché : `%s`" % p["action"][:200])
            if p["observation"]:
                out.append("  - a obtenu : %s" % p["observation"])
        return "\n".join(out)


# ═══════════════════════════════════════════════════════════════════════════
#  ETAPE ET CHAINE — LE CHAÎNAGE D'INVITES, ET LA COUTURE DU CADRE
# ═══════════════════════════════════════════════════════════════════════════
#
# C'EST ICI, ET NULLE PART AILLEURS, QU'UN CADRE VIENDRAIT SE BRANCHER.
# `Etape.executer(etat, trace)` a la forme d'un Runnable ; `Chaine` celle
# d'une séquence. Les cinq rôles ne connaissent ni l'une ni l'autre : ils
# prennent un état et en rendent un. Remplacer ces deux classes par LangChain
# ou Semantic Kernel ne toucherait aucun rôle — c'est la raison d'être de la
# couture, et c'est ce qui rend le choix de ce tour réversible.

class Etape:
    """Un maillon nommé de la chaîne."""

    def __init__(self, nom, role, fonction):
        if role not in ROLES:
            raise ValueError("étape « %s » : rôle inconnu %s" % (nom, role))
        self.nom = nom
        self.role = role
        self._f = fonction

    def executer(self, etat, trace):
        return self._f(etat, trace)


class Chaine:
    """Des étapes en suite, l'état passe de l'une à l'autre.

    UNE ÉTAPE QUI REND `None` N'EFFACE PAS L'ÉTAT. C'est une commodité qui
    évite à chaque rôle de terminer par `return etat` — et c'est surtout un
    garde-fou : un `return` oublié effaçait tout le travail des étapes
    précédentes, en silence.
    """

    def __init__(self, etapes):
        self.etapes = list(etapes)
        vus = set()
        for e in self.etapes:
            if e.nom in vus:
                raise ValueError("deux étapes portent le nom « %s »" % e.nom)
            vus.add(e.nom)

    def executer(self, etat=None, trace=None):
        etat = dict(etat or {})
        trace = trace if trace is not None else Trace()
        for e in self.etapes:
            suite = e.executer(etat, trace)
            if suite is not None:
                etat = suite
        return etat, trace


# ═══════════════════════════════════════════════════════════════════════════
#  1. LE PLANIFICATEUR — PLAN-AND-EXECUTE
# ═══════════════════════════════════════════════════════════════════════════

_VIDES = {
    "de", "du", "des", "la", "le", "les", "et", "ou", "a", "au", "aux", "en",
    "un", "une", "pour", "par", "sur", "dans", "avec", "sans", "ses", "son",
    "sa", "ce", "cet", "cette", "aux", "d", "l", "qui", "que",
}


def _mots_porteurs(texte):
    """Les mots d'un intitulé qui DÉSIGNENT quelque chose.

    POURQUOI ÉCARTER LES VIDES ICI PLUTÔT QU'AU MAGASIN. Le magasin compare
    les termes tels quels ; lui apprendre les mots vides toucherait toutes les
    recherches de l'application, ce qui n'est pas la décision de ce tour. Ici,
    l'enjeu est différent et local : on se sert de ces mots pour DIRE de quoi
    parle un point, et « de » ne dit rien.
    """
    brut = re.sub(r"[^\w\s-]", " ", (texte or "").lower(), flags=re.UNICODE)
    return [m for m in brut.split() if len(m) > 2 and m not in _VIDES]


def planifier(points, source=""):
    """Le plan : une liste de points, chacun avec ce qui le désigne.

    `points` est une liste de chaînes (les sections d'un type, le contenu
    exigé d'une pièce) ou de dicts déjà formés. On ne l'invente pas : il est
    DÉJÀ dans la donnée, et c'est tout l'intérêt — les quatre-vingt-dix types
    déclarent leurs sections, les pièces déclarent leur contenu.
    """
    plan = []
    for i, p in enumerate(points or []):
        if isinstance(p, dict):
            intitule = str(p.get("intitule") or p.get("nom") or p.get("titre") or "")
            cle = str(p.get("cle") or "") or "p%d" % (i + 1)
        else:
            intitule = str(p or "")
            cle = "p%d" % (i + 1)
        intitule = intitule.strip()
        if not intitule:
            continue
        plan.append({
            "rang": len(plan) + 1,
            "cle": cle,
            "intitule": intitule,
            "mots": _mots_porteurs(intitule),
            "source": source,
        })
    return plan


def plan_du_livrable(type_id, livrables_mod=None):
    """Le plan d'un des quatre-vingt-dix types — ses sections déclarées."""
    if livrables_mod is None:
        import livrables as livrables_mod                         # noqa: PLC0415
    t = livrables_mod.get_type(type_id)
    if not t:
        return []
    return planifier(t.get("sections") or [], source="type:%s" % type_id)


def plan_de_la_piece(piece):
    """Le plan d'une pièce de marché — ce qu'elle doit démontrer.

    UNE PIÈCE NE DÉCLARE PAS TOUJOURS SON CONTENU, et c'est un fait de la
    donnée, pas un oubli : un mémoire technique se plie aux critères du
    règlement de consultation, qui changent d'un marché à l'autre. Sans
    contenu déclaré, on rend un plan VIDE plutôt qu'un plan inventé — et
    l'appelant retombe alors sur le chemin d'avant, qui fonctionne.
    """
    pts = (piece or {}).get("contenu") or (piece or {}).get("points") or []
    return planifier(pts, source="piece:%s" % (piece or {}).get("cle", ""))


# ═══════════════════════════════════════════════════════════════════════════
#  2. LE DOCUMENTALISTE — RAG AGENTIQUE, UNE RECHERCHE PAR POINT
# ═══════════════════════════════════════════════════════════════════════════
#
# LES TROIS STRATÉGIES, ET POURQUOI ELLES SONT DANS CET ORDRE. Chacune répond
# à une raison DIFFÉRENTE pour laquelle un point revient vide, et l'ordre va
# du plus visé au plus large — on ne passe à la suivante que si la
# précédente n'a rien rendu.
#
#   1. « point + sujet » — le cas normal : on cherche ce point-ci, dans le
#      domaine de ce document-ci.
#   2. « point seul, sans accents, au singulier » — le point est peut-être
#      documenté GÉNÉRIQUEMENT (une méthode de priorisation ne parle pas de
#      centres de données), et l'extraction d'un PDF rend souvent un texte
#      sans accents. Cette variante-là n'est pas une invention de ce module :
#      `ao_redaction.requete_fonds` a dû l'apprendre à ses dépens, une note
#      méthodologique bien rangée restant introuvable à cause d'un accent.
#   3. « le mot le plus distinctif, seul » — dernier recours, quand la
#      combinaison de mots ne touche rien mais qu'un terme rare porterait.
#
# CE QU'AUCUNE STRATÉGIE NE FAIT : ÉLARGIR LA VISIBILITÉ. Voir ci-dessous.

def _sans_accent(s):
    try:
        import ao_dc                                              # noqa: PLC0415
        return ao_dc._sans_accent(s)
    except Exception:
        import unicodedata                                        # noqa: PLC0415
        return "".join(c for c in unicodedata.normalize("NFD", s or "")
                       if unicodedata.category(c) != "Mn")


def _singulier(mots):
    return [m[:-1] if len(m) > 4 and m.endswith("s") else m for m in mots]


def strategies(point, sujet=""):
    """Les requêtes successives pour UN point, de la plus visée à la plus large.

    Rend une liste de (nom, requête). Le nom entre dans la trace : une règle
    peut alors mesurer QUELLE stratégie a trouvé, pas seulement qu'on a trouvé.
    """
    mots = point.get("mots") or []
    if not mots:
        return []
    s = []
    s.append(("point+sujet", " ".join(mots + _mots_porteurs(sujet))))
    s.append(("point-nu-sans-accent",
              " ".join(_singulier([_sans_accent(m) for m in mots]))))
    distinctif = max(mots, key=len)
    s.append(("mot-distinctif", distinctif))
    # DÉDOUBLONNAGE : sur un intitulé sans accent ni pluriel, les deux
    # premières stratégies sont le même texte à un mot près. Reposer la même
    # question compte un tour pour rien, et la trace mentirait en laissant
    # croire qu'on a essayé autre chose.
    vues, net = set(), []
    for nom, q in s:
        q = " ".join(q.split())
        if q and q not in vues:
            vues.add(q)
            net.append((nom, q))
    return net


def documenter(plan, chercher, sujet="", public_only=True, par_point=PAR_POINT,
               tours_max=TOURS_MAX, trace=None, deja=None):
    """Une recherche PAR POINT, relancée sur ce qui est resté vide.

    `chercher(requete, k, public_only)` est injectée — ce module ne connaît
    pas la base, exactement comme `ingenierie_dc.couverture_documentaire`, et
    pour la même raison : il reste éprouvable sans elle.

    ═══ LA FRONTIÈRE QUE LA BOUCLE NE FRANCHIT PAS ═══════════════════════
    `public_only` est passé TEL QUEL à chaque tour, et ce module n'a aucun
    chemin qui le change. Ce n'est pas une précaution de style : les extraits
    sont reproduits mot pour mot dans un document qui sort du site. Une
    boucle « qui élargit quand elle ne trouve rien » est exactement la forme
    que prendrait la fuite — elle paraîtrait serviable, et elle recopierait
    un document interne dans un livrable remis au client. Un point que seuls
    des documents internes couvriraient doit donc ressortir ABSENT.

    ═══ LA TERMINAISON, ET POURQUOI LA BORNE N'EN EST PAS LA PREUVE ══════
    On s'arrête sur trois conditions, et la deuxième est celle qui compte :
      · plus aucun point vide ;
      · un tour n'a rapporté AUCUN document nouveau (`_stagnation`) — la base
        n'a plus rien à dire, et reposer la question ne la fera pas parler ;
      · `tours_max` atteint, qui n'est que le filet.
    Sans la deuxième, une base muette ferait tourner la boucle jusqu'à la
    borne à chaque document produit, pour rien.
    """
    trace = trace if trace is not None else Trace()
    etats = {p["cle"]: {"point": p, "extraits": [], "requetes": [],
                        "trouve_par": None, "injoignable": False} for p in plan}
    vus = set(deja or ())
    for tour in range(max(1, int(tours_max))):
        vides = [p for p in plan if not etats[p["cle"]]["extraits"]]
        if not vides:
            break
        avant = len(vus)
        for p in vides:
            jeu = strategies(p, sujet)
            if tour >= len(jeu):
                continue
            nom, requete = jeu[tour]
            etats[p["cle"]]["requetes"].append({"tour": tour, "strategie": nom,
                                                "requete": requete})
            try:
                hits = chercher(requete, par_point, public_only) or []
            except Exception:
                # ═══ « LA BASE N'A RIEN » ET « ON N'A PAS PU DEMANDER » NE
                # SONT PAS LA MÊME PHRASE. Cette distinction n'est pas de moi :
                # `ingenierie_dc.couverture_documentaire` la faisait déjà, et
                # ce module la confondait. Dire au client que la base ne
                # documente pas un point alors qu'elle était injoignable, c'est
                # lui faire réécrire à la main ce qui est peut-être rangé chez
                # lui — et lui faire perdre confiance dans son propre fonds.
                etats[p["cle"]]["injoignable"] = True
                hits = []
            # ═══ DEUX DÉDOUBLONNAGES, ET LES CONFONDRE ÉTAIT UN DÉFAUT ═══
            #
            # MESURÉ : avec un seul ensemble « vu » partagé par tous les
            # points, une note méthodologique qui répond à trois points du
            # plan n'était attribuée qu'au PREMIER — les deux autres
            # ressortaient « à écrire », et le document annonçait donc au
            # client qu'il manquait une matière qu'il possède. Sur une pièce
            # de trois points servie par un seul document, cela donnait
            # 1 point couvert sur 3 au lieu de 3.
            #
            # `ingenierie_dc.couverture_documentaire` dédoublonne PAR POINT,
            # et c'est la bonne lecture : un même document peut légitimement
            # appuyer plusieurs points.
            #
            # L'ENSEMBLE GLOBAL SURVIT, POUR UN AUTRE USAGE. Il ne sert plus
            # à filtrer les extraits mais à répondre à UNE seule question :
            # « ce tour a-t-il rapporté quelque chose que les tours
            # précédents n'avaient pas ? » — c'est-à-dire la condition
            # d'arrêt. Deux besoins, deux ensembles.
            vus_ici, neufs = set(), []
            for h in hits:
                cle = (h.get("doc_id"), (h.get("content") or "")[:120])
                if cle in vus_ici:
                    continue
                vus_ici.add(cle)
                neufs.append(h)
                vus.add(cle)
            if neufs:
                etats[p["cle"]]["extraits"] = neufs
                etats[p["cle"]]["trouve_par"] = nom
            trace.noter(
                "documentaliste", tour=tour,
                pensee="« %s » n'a rien — stratégie « %s »" % (p["intitule"], nom)
                       if tour else "chercher ce que « %s » exige" % p["intitule"],
                action=requete,
                observation=("%d extrait(s) : %s" % (
                    len(neufs), ", ".join((h.get("title") or "?")[:40] for h in neufs))
                    if neufs else "rien"))
        if _stagnation(len(vus), avant):
            trace.noter("documentaliste", tour=tour,
                        pensee="le tour n'a rapporté aucun document nouveau — "
                               "la base n'a plus rien sur ces points",
                        action="", observation="arrêt, les manques sont déclarés")
            break
    return _bilan(plan, etats, trace)


def _stagnation(apres, avant):
    """Un tour qui n'apporte rien de neuf arrête la boucle.

    ÉCRITE COMME FONCTION, ET PAS EN LIGNE. Une mutation qui neutralise cette
    condition doit faire tomber une règle NOMMÉE ; noyée dans un `if`, elle
    aurait été indiscernable d'un ajustement de borne.
    """
    return apres <= avant


def _bilan(plan, etats, trace):
    """Le bilan — DANS LE VOCABULAIRE DE `ingenierie_dc.couverture_documentaire`.

    CE N'EST PAS UNE COÏNCIDENCE, C'EST LA DÉCISION QUI ÉVITE UN DOUBLON.
    Ce module rend exactement la forme que `extraits_pour_redaction` et
    `consigne_manques` savent déjà lire : mêmes clés « point », « etat »,
    « extraits », même triade couvert / a_ecrire / inconnu. Ces deux
    fonctions-là s'appliquent donc TELLES QUELLES à ce que rend ce module, et
    rien n'a été recopié — ni leur service par TOURS, qui répartit les appuis
    sous la coupe du budget, ni la consigne qui nomme les trous au rédacteur.
    Une seule grammaire, deux producteurs.

    ET C'EST EN LISANT LEUR CODE QUE CE MODULE A CORRIGÉ UNE FAUTE. Ils
    séparent « la base n'a rien rendu » de « la base n'a pas répondu » ; ce
    module écrivait « absent » dans les deux cas. Un client à qui l'on dit que
    son fonds ne documente pas un point, alors que la recherche avait échoué,
    réécrit à la main ce qu'il possède déjà.
    """
    points = []
    for p in plan:
        e = etats[p["cle"]]
        if e["extraits"]:
            etat = "couvert"
        elif e["injoignable"]:
            etat = "inconnu"
        else:
            etat = "a_ecrire"
        docs, ecartes, vus = [], [], set()
        for h in e["extraits"]:
            fiche = {"doc_id": h.get("doc_id"),
                     "titre": _titre(h),
                     "theme": h.get("theme"),
                     "nature": h.get("nature"),
                     "nature_nom": h.get("nature_nom"),
                     "date_source": h.get("date_source"),
                     "raisons": h.get("raisons") or []}
            if fiche["doc_id"] in vus:
                # UN SECOND PASSAGE DU MÊME DOCUMENT N'EST PAS UNE SOURCE DE
                # PLUS — mais il figure au dossier : un extrait retiré en
                # silence se lit comme un extrait qui n'a jamais existé. La
                # doctrine est celle de `ingenierie_dc`, et c'est voulu : les
                # deux producteurs alimentent le MÊME rendu.
                ecartes.append(dict(fiche, motif="doublon de source",
                                    dit="Un autre passage du même document "
                                        "est déjà retenu pour ce point."))
                continue
            vus.add(fiche["doc_id"])
            docs.append(fiche)
        points.append({
            # « point » est le nom de la clé chez `ingenierie_dc` ; « intitule »
            # et « cle » sont EN PLUS, et n'y gênent personne.
            "point": p["intitule"],
            "cle": p["cle"], "rang": p["rang"], "intitule": p["intitule"],
            # ═══ « documents » ET « ecartes » NE SONT PAS DÉCORATIFS ═══
            # `ingenierie_dc.couverture_markdown` les LIT pour écrire l'annexe
            # du document. Sans eux, le chemin sans modèle levait une
            # KeyError sur chaque type hors centre de données — c'est-à-dire
            # sur quatre-vingt-neuf des quatre-vingt-dix. Mesuré en essayant
            # ce rendu AVANT de brancher, pas après.
            "documents": docs, "ecartes": ecartes,
            "extraits": [dict(h, point=p["intitule"]) for h in e["extraits"]],
            "requetes": e["requetes"],
            "requete": (e["requetes"][-1]["requete"] if e["requetes"] else ""),
            "trouve_par": e["trouve_par"],
            "etat": etat,
        })
    manques = [q for q in points if q["etat"] != "couvert"]
    tous = [h for q in points for h in q["extraits"]]
    trace.noter("documentaliste", tour=max((r["tour"] for q in points
                                            for r in q["requetes"]), default=0),
                pensee="bilan de la recherche",
                action="",
                observation="%d point(s) documenté(s) sur %d, %d extrait(s), "
                            "%d document(s) distinct(s)"
                            % (len(points) - len(manques), len(points), len(tous),
                               len({h.get("doc_id") for h in tous})))
    return {"points": points, "manques": manques, "extraits": tous,
            "resume": _resume(points),
            "lecture": _lecture(_resume(points)),
            "reserve": "La couverture est CONSTATÉE sur la base interrogée, "
                       "pas promise : un point « documenté » signale qu'un "
                       "document parle du sujet, jamais qu'il répond à la "
                       "question.",
            "documents": sorted({h.get("doc_id") for h in tous if h.get("doc_id")},
                                key=str)}


def _titre(hit):
    """Le titre présentable d'un extrait, nettoyé s'il peut l'être."""
    brut = hit.get("title") or hit.get("titre") or "?"
    try:
        import extraits as _e                                     # noqa: PLC0415
        return _e.titre_document(brut)
    except Exception:
        return brut


def _lecture(r):
    """La phrase qui se lit en tête de l'annexe — celle qu'on lira vraiment.

    ELLE DIT CE QUE LA COUVERTURE NE PROUVE PAS. « Six points sur six
    documentés » se lit comme « le document est sourcé », et ce n'est pas la
    même chose : un extrait qui parle du sujet n'est pas un extrait qui
    répond au point. Le dire ici est le seul endroit où cela sera lu.
    """
    total, couverts = r["total"], r["couverts"]
    if r["inconnus"]:
        return ("Couverture INDÉTERMINÉE : la base n'a pas répondu. Ce qui "
                "est écrit reste exact, mais rien ici ne dit ce que le fonds "
                "aurait apporté.")
    if not total:
        return "Ce document ne déclare aucun point à couvrir."
    if r["a_ecrire"] == 0:
        return ("Chacun des %d points du plan trouve de la matière dans la "
                "base. Cela ne dit pas qu'elle SUFFIT : c'est au relecteur de "
                "juger si l'extrait traite le point ou l'effleure." % total)
    if couverts == 0:
        return ("AUCUN des %d points du plan n'est documenté par la base. Le "
                "document s'écrit intégralement depuis le projet — c'est "
                "faisable, mais il faut le savoir AVANT de commencer." % total)
    return ("%d des %d points du plan sont documentés ; %d s'écrivent depuis "
            "le projet, sans appui documentaire. Les nommer évite de s'en "
            "apercevoir en cours de rédaction."
            % (couverts, total, r["a_ecrire"]))


def _resume(points):
    """Le compte par état — même forme que le « resume » de `ingenierie_dc`."""
    return {"total": len(points),
            "couverts": sum(1 for q in points if q["etat"] == "couvert"),
            "a_ecrire": sum(1 for q in points if q["etat"] == "a_ecrire"),
            "inconnus": sum(1 for q in points if q["etat"] == "inconnu")}


# ═══════════════════════════════════════════════════════════════════════════
#  3. LE VÉRIFICATEUR — CE QUI N'EST ADOSSÉ À RIEN
# ═══════════════════════════════════════════════════════════════════════════
#
# CE QU'IL CHERCHE, ET POURQUOI CE CHOIX-LÀ. Un livrable de conseil se lit sur
# ses CHIFFRES : une puissance, un niveau, un délai, un pourcentage. Un chiffre
# qui ne figure NI dans un extrait reçu NI dans la fiche remplie par le client
# n'a qu'une origine possible — le modèle l'a produit. Ce n'est pas
# nécessairement faux, et c'est exactement pour cela qu'il faut le signaler
# plutôt que le supprimer : c'est au relecteur de trancher, et il ne peut le
# faire que s'il sait lesquels regarder.
#
# IL NE CONSOMME PAS DE MODÈLE, ET C'EST DÉLIBÉRÉ. Un contrôle de provenance
# qui coûterait un appel par section ne serait pas passé sur chaque section :
# on l'aurait réservé « aux documents importants », c'est-à-dire à ceux qu'on
# relit déjà.

_CHIFFRE = re.compile(r"(?<![\w.,])(\d[\d   ]*(?:[.,]\d+)?)\s*"
                      r"(%|kW|MW|kVA|MVA|V|A|Hz|°C|m²|m2|m³|m3|kWh|MWh|dBA|"
                      r"mm|cm|km|h|min|j|ans?|mois|€|k€|M€)?", re.IGNORECASE)


def _chiffres(texte):
    """Les grandeurs citées par un texte, normalisées pour la comparaison."""
    out = set()
    for m in _CHIFFRE.finditer(texte or ""):
        val = m.group(1).replace(" ", "").replace(" ", "").replace(",", ".")
        val = val.rstrip(".")
        if not val or val in {"0", "1", "2"}:
            # LES TRÈS PETITS ENTIERS SONT ÉCARTÉS, et c'est une correction.
            # « niveau 2 », « en 2 temps », « les 2 sites » : mesuré sur des
            # brouillons, ils produisaient l'essentiel des signalements et
            # aucun n'était une grandeur relevée. Un contrôle qui crie sur
            # tout est un contrôle qu'on éteint.
            continue
        unite = (m.group(2) or "").lower().replace("²", "2").replace("³", "3")
        out.add((val, unite))
    return out


def verifier_sources(texte, extraits, fiche=None, trace=None, tour=0):
    """Les grandeurs du texte qui ne viennent d'aucune source reçue."""
    adosse = set()
    for h in extraits or []:
        adosse |= _chiffres(h.get("content") or "")
    for v in (fiche or {}).values():
        if isinstance(v, str):
            adosse |= _chiffres(v)
    # LA COMPARAISON PORTE SUR LA VALEUR, PAS SUR L'UNITÉ. « 400 kW » dans
    # l'extrait et « 400 » dans le texte sont la même grandeur reprise ;
    # exiger l'unité des deux côtés aurait signalé toutes les reprises
    # correctes, c'est-à-dire le cas normal.
    valeurs = {v for v, _u in adosse}
    orphelins = sorted({v for v, _u in _chiffres(texte)} - valeurs)
    if trace is not None:
        trace.noter("verificateur", tour=tour,
                    pensee="d'où viennent les grandeurs citées",
                    action="",
                    observation=("aucune grandeur sans source"
                                 if not orphelins else
                                 "%d grandeur(s) sans source : %s"
                                 % (len(orphelins), ", ".join(orphelins[:8]))))
    return orphelins


# ═══════════════════════════════════════════════════════════════════════════
#  4. LE CRITIQUE — SELF-REFINEMENT
# ═══════════════════════════════════════════════════════════════════════════
#
# IL REND UN VERDICT, IL NE CORRIGE PAS. Un critique qui réécrit fait
# disparaître ce qu'il a corrigé : on ne saurait plus si le document est bon
# ou s'il a été rattrapé. Ce qu'il rend pilote le tour suivant, et se retrouve
# dans l'annexe du document — ce qui veut dire qu'un manque non comblé est
# LISIBLE par celui qui reçoit le livrable.
#
# TROIS ÉTATS, ET « MINCE » EST LE PLUS UTILE. « absent » se voit à l'œil nu ;
# « mince » est le cas qui passait : une section présente, bien tournée, de
# trois lignes, sous un titre qui promettait une analyse. C'est celle-là
# qu'un relecteur pressé valide.

def _sections_du_texte(texte):
    """Découpe un Markdown en (titre, corps) — sur les titres de niveau 2 et 3."""
    out, titre, corps = [], None, []
    for ligne in (texte or "").splitlines():
        m = re.match(r"^\s{0,3}#{2,3}\s+(.*\S)\s*$", ligne)
        if m:
            if titre is not None:
                out.append((titre, "\n".join(corps).strip()))
            titre, corps = m.group(1), []
        elif titre is not None:
            corps.append(ligne)
    if titre is not None:
        out.append((titre, "\n".join(corps).strip()))
    return out


def _appariee(intitule, titres):
    """Le titre du brouillon qui correspond à ce point du plan.

    L'APPARIEMENT EST LEXICAL ET TOLÉRANT, parce que le rédacteur reformule :
    « Écarts constatés » devient « 4. Les écarts relevés sur site ». On exige
    que la MOITIÉ des mots porteurs du point se retrouvent, sans accents.
    """
    mots = {_sans_accent(m) for m in _mots_porteurs(intitule)}
    if not mots:
        return None
    for t, corps in titres:
        vus = {_sans_accent(m) for m in _mots_porteurs(t)}
        if len(mots & vus) * 2 >= len(mots):
            return (t, corps)
    return None


def critiquer(plan, texte, documentation=None, fiche=None, trace=None, tour=0,
              mince=MINCE):
    """Relit le brouillon CONTRE le plan. Rend le verdict, pas une correction."""
    trace = trace if trace is not None else Trace()
    titres = _sections_du_texte(texte)
    par_cle = {q["cle"]: q for q in (documentation or {}).get("points", [])}
    marque = _marque_a_completer()
    verdicts, manques = [], []
    for p in plan:
        appar = _appariee(p["intitule"], titres)
        doc = par_cle.get(p["cle"], {})
        if appar is None:
            etat, raison = "absent", "aucune section du brouillon ne traite ce point"
        else:
            _t, corps = appar
            if marque in corps:
                etat, raison = "a_completer", "le rédacteur a posé la marque lui-même"
            elif len(corps) < mince:
                etat = "mince"
                raison = ("%d signes — la section annonce sans traiter" % len(corps))
            else:
                etat, raison = "couvert", ""
        verdicts.append({
            "cle": p["cle"], "intitule": p["intitule"], "etat": etat,
            "raison": raison,
            # POURQUOI LE VERDICT PORTE L'ÉTAT DOCUMENTAIRE. Une section mince
            # sur un point que la base ne documente pas n'appelle pas la même
            # action qu'une section mince sur un point bien documenté : la
            # première est un manque à déclarer, la seconde un tour à refaire.
            "documente": bool(doc.get("extraits")),
            # L'ÉTAT DOCUMENTAIRE DU POINT, tel que le documentaliste l'a
            # établi — « inconnu » compris : une section mince sur un point
            # qu'on n'a PAS PU chercher n'appelle pas la même suite qu'une
            # section mince sur un point que la base ignore vraiment.
            "etat_documentaire": doc.get("etat") or "a_ecrire",
        })
        if etat != "couvert":
            manques.append(verdicts[-1])
    orphelins = verifier_sources(texte, (documentation or {}).get("extraits"),
                                 fiche, trace, tour)
    trace.noter("critique", tour=tour,
                pensee="relire le brouillon contre le plan, point par point",
                action="",
                observation="%d point(s) couvert(s) sur %d%s"
                            % (len(plan) - len(manques), len(plan),
                               ("" if not manques else " — à reprendre : "
                                + ", ".join(m["intitule"] for m in manques[:5]))))
    return {"points": verdicts, "manques": manques, "sans_source": orphelins,
            "couverts": len(plan) - len(manques), "total": len(plan)}


# ═══════════════════════════════════════════════════════════════════════════
#  5. LA BOUCLE — ReAct
# ═══════════════════════════════════════════════════════════════════════════

def conduire(plan, chercher, rediger, sujet="", fiche=None, public_only=True,
             tours_max=TOURS_MAX, trace=None):
    """Chercher, écrire, se relire — et recommencer SUR CE QUI MANQUE.

    `rediger(plan, documentation, verdict, tour)` rend le Markdown. Elle est
    injectée : c'est le seul rôle qui consomme un modèle, et l'injecter est ce
    qui permet d'éprouver la boucle sans en appeler un.

    ═══ CE QUE LE SECOND TOUR FAIT DE DIFFÉRENT ══════════════════════════
    Il ne recommence pas : il RESTREINT. Le plan du tour suivant ne porte que
    les points que le critique a refusés, et la recherche reprend à la
    stratégie suivante pour ceux-là. Sans cette restriction, « boucler »
    reviendrait à repayer le document entier pour corriger une section.

    ═══ POURQUOI LE MEILLEUR TOUR, ET PAS LE DERNIER ═════════════════════
    Un tour peut rendre MOINS bien que le précédent — le rédacteur reprend
    une section et en abîme une autre. Garder le dernier ferait de la boucle
    un pari ; on garde donc celui qui couvre le plus de points, et la trace
    dit lequel.
    """
    trace = trace if trace is not None else Trace()
    if not plan:
        return {"markdown": "", "plan": [], "documentation": None,
                "verdict": None, "tours": 0, "trace": trace,
                "raison_arret": "plan_vide"}

    meilleur, vus, restant = None, set(), list(plan)
    documentation = {"points": [], "manques": [], "extraits": [], "documents": []}
    raison = "tours_max"
    for tour in range(max(1, int(tours_max))):
        trace.noter("planificateur", tour=tour,
                    pensee=("le plan entier — %d point(s)" % len(restant)) if not tour
                           else ("reprise des %d point(s) refusés par le critique"
                                 % len(restant)),
                    action="", observation=", ".join(p["intitule"] for p in restant))
        doc = documenter(restant, chercher, sujet=sujet, public_only=public_only,
                         tours_max=1, trace=trace, deja=vus)
        vus |= {(h.get("doc_id"), (h.get("content") or "")[:120])
                for h in doc["extraits"]}
        documentation = _fusionner(documentation, doc)
        texte = rediger(plan, documentation, meilleur and meilleur["verdict"], tour)
        verdict = critiquer(plan, texte, documentation, fiche, trace, tour)
        etat = {"markdown": texte, "verdict": verdict, "tour": tour}
        if meilleur is None or verdict["couverts"] > meilleur["verdict"]["couverts"]:
            meilleur = etat
        if not verdict["manques"]:
            raison = "plan_couvert"
            break
        suite = [p for p in plan
                 if p["cle"] in {m["cle"] for m in verdict["manques"]}]
        # LA BASE A-T-ELLE ENCORE QUELQUE CHOSE ? Un point refusé que la
        # recherche ne documente pas ne sera pas mieux écrit au tour suivant :
        # il manque de MATIÈRE, pas de rédaction. On ne le repasse donc pas,
        # et s'il ne reste que ceux-là, on s'arrête et on le déclare.
        suite = [p for p in suite
                 if any(q["cle"] == p["cle"] and q["extraits"]
                        for q in documentation["points"])
                 or _reste_une_strategie(p, documentation, tour)]
        if not suite:
            raison = "rien_de_plus_dans_la_base"
            break
        restant = suite
    return {"markdown": meilleur["markdown"], "plan": plan,
            "documentation": documentation, "verdict": meilleur["verdict"],
            "tours": meilleur["tour"] + 1, "trace": trace,
            "raison_arret": raison}


def _reste_une_strategie(point, documentation, tour):
    """Reste-t-il une façon de reposer la question pour ce point ?"""
    return tour + 1 < len(strategies(point))


def _fusionner(a, b):
    """Les extraits de deux tours, sans doublon, l'ordre du premier d'abord."""
    par_cle = {q["cle"]: dict(q) for q in a["points"]}
    for q in b["points"]:
        if q["cle"] in par_cle and par_cle[q["cle"]]["extraits"]:
            par_cle[q["cle"]]["extraits"] = (par_cle[q["cle"]]["extraits"]
                                             + q["extraits"])
            par_cle[q["cle"]]["requetes"] += q["requetes"]
        else:
            par_cle[q["cle"]] = dict(q)
    points = sorted(par_cle.values(), key=lambda q: q["rang"])
    for q in points:
        # L'ÉTAT SE RECALCULE APRÈS FUSION. Un point resté vide au premier tour
        # et servi au second est COUVERT ; garder son état d'origine ferait
        # écrire au document qu'il manque une matière qu'il porte.
        q["etat"] = ("couvert" if q["extraits"]
                     else ("inconnu" if q.get("etat") == "inconnu" else "a_ecrire"))
    tous = [h for q in points for h in q["extraits"]]
    return {"points": points,
            "manques": [q for q in points if q["etat"] != "couvert"],
            "extraits": tous,
            "resume": _resume(points),
            "lecture": _lecture(_resume(points)),
            "reserve": "La couverture est CONSTATÉE sur la base interrogée, "
                       "pas promise : un point « documenté » signale qu'un "
                       "document parle du sujet, jamais qu'il répond à la "
                       "question.",
            "documents": sorted({h.get("doc_id") for h in tous if h.get("doc_id")},
                                key=str)}


# ═══════════════════════════════════════════════════════════════════════════
#  CE QUI S'ÉCRIT DANS LE DOCUMENT
# ═══════════════════════════════════════════════════════════════════════════

def annexe(resultat):
    """Ce que le document dit de sa propre fabrication.

    ELLE EST DANS LE DOCUMENT, PAS DANS UNE CONSOLE. Un manque affiché à
    l'écran au moment de la génération est un manque que personne ne relit ;
    écrit en annexe, il voyage avec le document et arrive sous les yeux de
    celui qui doit le combler.
    """
    v, d = resultat.get("verdict"), resultat.get("documentation")
    if not v:
        return ""
    out = ["## Ce que ce document couvre, et ce qu'il ne couvre pas", ""]
    out.append("| Point du plan | Traité | Documenté par la base |")
    out.append("|---|---|---|")
    docs = {q["cle"]: q for q in (d or {}).get("points", [])}
    dit = {"couvert": "oui", "mince": "à étoffer", "absent": "non",
           "a_completer": "marqué à compléter"}
    for p in v["points"]:
        q = docs.get(p["cle"], {})
        n = len({h.get("doc_id") for h in q.get("extraits", [])})
        out.append("| %s | %s | %s |"
                   % (p["intitule"], dit.get(p["etat"], p["etat"]),
                      ("%d document(s)" % n) if n else "**aucun**"))
    absents = [p for p in v["points"] if not docs.get(p["cle"], {}).get("extraits")]
    if absents:
        out += ["", "**La base documentaire ne dit rien sur %d point(s)** : %s. "
                "Ces passages sont à écrire à la main, ou à documenter avant "
                "remise." % (len(absents),
                             ", ".join("« %s »" % p["intitule"] for p in absents))]
    if v.get("sans_source"):
        out += ["", "**Grandeurs citées sans source dans les extraits reçus** : "
                "%s. À vérifier avant remise — elles ne viennent ni de la base, "
                "ni de la fiche du projet."
                % ", ".join(v["sans_source"][:12])]
    if resultat.get("raison_arret") == "rien_de_plus_dans_la_base":
        out += ["", "*La recherche s'est arrêtée d'elle-même : les points "
                "restants ne sont documentés par aucun document accessible.*"]
    return "\n".join(out)


# ═══════════════════════════════════════════════════════════════════════════
#  LA GARDE — CE QUE CE MODULE REFUSE DE LAISSER PASSER
# ═══════════════════════════════════════════════════════════════════════════

def _verifier():
    fautes = []
    for cle, r in ROLES.items():
        for champ in ("nom", "decide", "interdit", "pourquoi"):
            if not str(r.get(champ) or "").strip():
                fautes.append("le rôle « %s » n'a pas de %s écrit" % (cle, champ))
        if "modele" not in r:
            fautes.append("le rôle « %s » ne dit pas s'il consomme un modèle" % cle)
    # UN SEUL RÔLE A LE DROIT D'APPELER UN MODÈLE, et cette garde est le seul
    # endroit qui le dise. Le jour où l'on en branchera un second, ce sera une
    # décision prise ici, pas un effet de bord ailleurs.
    avec = sorted(c for c, r in ROLES.items() if r.get("modele"))
    if avec != ["redacteur"]:
        fautes.append("les rôles qui consomment un modèle ont changé : %s" % avec)
    if TOURS_MAX < 1:
        fautes.append("TOURS_MAX doit valoir au moins 1")
    if fautes:
        raise RuntimeError("orchestration — table incohérente : "
                           + " ; ".join(fautes))
    return fautes


_FAUTES = _verifier()
