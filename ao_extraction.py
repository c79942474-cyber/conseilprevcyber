# -*- coding: utf-8 -*-
"""Remplir les rubriques qui restaient à saisir, en les LISANT dans le dossier.

POURQUOI CE MODULE EXISTE, ET CE QU'IL CORRIGE. Le relevé de `ao_dc` cherche
DIX-SEPT points de vigilance par motifs écrits à la main. Le report en attend
QUATRE-VINGT-TREIZE. L'écart n'est pas un défaut de lecture : c'est qu'il
n'existait **aucun chemin d'extraction** pour les rubriques restantes — elles
sortaient « à saisir » par construction. Mesuré sur une consultation réelle le
13 septembre : 15 rubriques de source « consultation », 27 de source « saisie »,
43 de la fiche cabinet, 6 déclarations, 2 calculs. Les 27 saisies et les relevés
manqués n'avaient personne pour les chercher.

CE MODULE RETOURNE LA QUESTION. Au lieu de chercher ce qu'un catalogue de
motifs sait voir, il part de CE QU'IL FAUT REMPLIR — rubrique par rubrique, le
report le sait déjà — et va le chercher dans les pièces déposées.

════════════════════════════════════════════════════════════════════════════
 LA RÈGLE QUI GOUVERNE TOUT : PAS DE VALEUR SANS CITATION VÉRIFIÉE
════════════════════════════════════════════════════════════════════════════
Le risque d'un remplissage automatique n'est pas la case vide : c'est la case
remplie FAUX et signée. Une valeur proposée n'est donc retenue que si la
citation qui l'accompagne se retrouve **mot pour mot dans le texte déposé**.
La comparaison tolère les espaces et la casse — un lecteur de PDF recompose les
blancs — et rien d'autre. Une citation introuvable fait REJETER la proposition :
elle n'est pas dégradée, pas affichée en gris, pas « à confirmer ». Elle
n'existe pas. C'est la seule défense contre un passage inventé.

ET CE QUI PASSE RESTE MARQUÉ. Une valeur lue ici porte son origine — le
fichier, l'endroit du document, et le fait qu'elle vient d'une LECTURE
ASSISTÉE. Ce qui se recopie sur un formulaire de l'État doit dire d'où il vient.

════════════════════════════════════════════════════════════════════════════
 UN APPEL PAR PIÈCE, PAS UN PAR RUBRIQUE
════════════════════════════════════════════════════════════════════════════
Sept pièces portent des rubriques, pour quatre-vingt-treize rubriques. Un appel
par rubrique, c'est quatre-vingt-treize allers-retours et autant de fois le même
dossier relu. Un appel par pièce en fait sept, et donne au modèle les rubriques
ENSEMBLE — ce qui compte, parce que l'objet du marché et l'intitulé de la
consultation se lisent dans la même phrase.

LA SORTIE EST STRUCTURÉE PAR UN OUTIL, PAS PAR UNE CONSIGNE DE FORMAT. Le SDK
est épinglé à `anthropic==0.75.0` et n'est pas installé sur le poste de
développement : une liaison que l'on ne peut pas éprouver ici ne doit pas être
choisie sur la foi d'un souvenir. `tools` + `tool_choice` est la forme stable
sur toutes les versions du SDK, et les règles la fixent avec un client injecté.

TOUT CE QUI PEUT ÊTRE PUR L'EST. `cibles`, `requete`, `corpus`,
`verifier_citation` et `retenir` sont des fonctions de leurs arguments : elles
s'éprouvent sans clé, sans réseau et sans modèle. La seule impureté est
`extraire`, et le client y est INJECTÉ.
"""
import json
import logging
import os
import re
import unicodedata

import reglages


_log = logging.getLogger(__name__)

# LES RÉGLAGES PASSENT PAR `reglages`, ET CE N'EST PAS UNE COQUETTERIE. Une
# règle du dépôt parcourt l'arbre syntaxique et refuse tout `int(os.environ…)` :
# une variable mal saisie sur Render arrêterait le service AU CHARGEMENT, pour
# un plafond de jetons. Elle a attrapé ces trois lignes à la première suite
# complète — elle fait exactement ce pour quoi elle a été écrite.
MODELE = os.environ.get("AO_EXTRACTION_MODEL", "claude-opus-5")
JETONS_MAX = reglages.entier("AO_EXTRACTION_MAX_TOKENS", 8000, mini=1000)
DELAI = reglages.reel("AO_EXTRACTION_TIMEOUT", 180.0, mini=10.0)

# COMBIEN DE TEXTE ON DONNE À LIRE, ET POURQUOI PAS TOUT. Un dossier de marché
# fait des centaines de pages ; les verser en entier coûterait la fenêtre
# entière et noierait les rubriques. On donne les pièces ENTIÈRES tant qu'elles
# tiennent, en commençant par celles que l'ordre de lecture met en premier —
# le règlement de consultation fait foi sur ce qu'il faut remettre.
CORPUS_MAX = reglages.entier("AO_EXTRACTION_CORPUS_MAX", 120000, mini=2000)

# LES SOURCES QUE CE MODULE A LE DROIT DE REMPLIR.
#
# LA FICHE Y ENTRE, ET C'EST LE GAIN PRINCIPAL DE CE MODULE. Elle en était
# exclue au motif qu'elle « se saisit une fois et ne se devine pas ». C'était
# juste tant que le dépôt ne connaissait qu'un côté, celui de l'acheteur : la
# forme juridique du candidat n'a rien à faire dans un CCTP, et l'y chercher
# n'aurait ramené que du bruit.
#
# CE QUI A CHANGÉ : LE DÉPÔT PREND MAINTENANT VOS PROPRES DOCUMENTS. Un Kbis
# porte la forme juridique, la ville d'immatriculation au RCS et le capital ;
# un bilan porte les chiffres d'affaires. Mesuré sur un dossier réel, ce sont
# VINGT-HUIT rubriques `fiche` restées vides — vingt-deux « à saisir » et six
# « invalide » — qu'aucune recherche ne visait, sur quatre-vingt-treize. Le
# module lisait ces documents et ne s'en servait pour rien.
#
# CE QUI PROTÈGE DE LA DEVINETTE RESTE ENTIER, et c'est ce qui rend l'ouverture
# tenable : toute valeur extraite doit se retrouver CITÉE dans un document
# déposé, sans quoi elle est REJETÉE (`rejets`) et rien n'est reporté. Ouvrir
# la fiche à la recherche n'ouvre donc pas la porte à l'invention — cela permet
# de lire dans vos pièces ce que vous auriez retapé à la main.
#
# UN CALCUL NE SE CHERCHE TOUJOURS PAS : il se dérive d'une autre rubrique, et
# aller le lire ailleurs mettrait en concurrence une valeur calculée et une
# valeur lue. Une DÉCLARATION SUR L'HONNEUR non plus : elle s'affirme par une
# personne et JAMAIS par un programme — la pré-cocher serait signer à la place
# de quelqu'un.
SOURCES_CIBLES = ("saisie", "consultation", "fiche")

# ── LA CONTRAINTE QUI REND L'OUVERTURE DE LA FICHE TENABLE ────────────────
# CE QUE LA RÈGLE MAISON DISAIT, ET ELLE AVAIT RAISON : « Le SIRET du candidat
# n'est pas dans le règlement de l'acheteur. L'y chercher ferait remonter le
# SIRET DE L'ACHETEUR — et il serait recopié. » Le garde-fou habituel — une
# valeur doit être CITÉE dans un document déposé — ne protège pas de ce
# défaut-là : le SIRET de l'acheteur EST cité, noir sur blanc, dans son propre
# règlement. La citation existe, elle est exacte, et la valeur est fausse.
#
# CE QUI REND LA RECHERCHE POSSIBLE AUJOURD'HUI : le dépôt a deux côtés. Une
# rubrique qui décrit LE CANDIDAT ne se cherche que dans les documents QUE
# NOUS AVONS DÉPOSÉS — Kbis, bilans, attestations. Le règlement de l'acheteur
# n'entre pas dans ce corpus-là, et son SIRET ne peut donc plus être proposé.
#
# SANS DOCUMENT DU CABINET, RIEN NE CHANGE : la liste est vide, aucune
# recherche ne part, et la fiche reste à saisir comme avant.
SOURCES_DU_CANDIDAT = ("fiche",)

# CE QU'ON NE CHERCHE JAMAIS, ET C'EST DIT ICI PLUTÔT QU'AILLEURS. Une
# déclaration sur l'honneur s'affirme par une personne : la pré-remplir serait
# signer à la place de quelqu'un. Elle est déjà hors d'atteinte par son ÉTAT
# (`a_declarer` n'appelle aucune recherche) — mais une protection qui ne tient
# que par coïncidence n'est pas une protection. La batterie l'a montré : la
# mutation qui ajoutait « declaration » aux sources SURVIVAIT, parce que le
# filtre d'état la rattrapait. L'interdit est donc écrit, et il faut désormais
# DEUX retouches pour le lever.
SOURCES_INTERDITES = ("declaration",)

# LES ÉTATS QUI APPELLENT UNE RECHERCHE. Une rubrique déjà remplie ne se
# recherche pas : on ne va pas écraser une saisie humaine ni un relevé cité.
#
# « invalide » Y ENTRE AVEC L'OUVERTURE DE LA FICHE. Une rubrique invalide
# porte une valeur que le contrôle refuse — un SIRET à treize chiffres, un
# code postal tronqué. Elle n'est pas « remplie » : elle est fausse, et le
# document sortirait avec. La chercher dans les pièces déposées est
# exactement le geste utile ; et comme toute valeur extraite doit être citée
# pour être reportée, on ne remplace une valeur fausse que par une valeur
# qu'un document porte noir sur blanc.
STATUTS_CIBLES = ("a_saisir", "non_trouve", "invalide")


class ExtractionError(Exception):
    """Un refus nommé, avec son code HTTP — même forme que `ao_redaction`."""

    def __init__(self, code, status=502, detail=""):
        super(ExtractionError, self).__init__(code)
        self.code = code
        self.status = status
        self.detail = detail


# ═══════════════════════════════════════════════════════════════════════════
#  CE QU'IL RESTE À TROUVER
# ═══════════════════════════════════════════════════════════════════════════

def cibles(remplissage):
    """Par pièce, les rubriques qui restent à trouver — et rien d'autre.

    FONCTION PURE, et c'est délibéré : ce qu'on cherche décide de tout le
    reste, et une règle doit pouvoir l'éprouver sans modèle ni dossier.

    ON NE RECHERCHE PAS CE QUI EST DÉJÀ LÀ. Une rubrique remplie par la fiche,
    par un calcul ou par un relevé cité ne revient pas dans la liste : la
    relancer au modèle reviendrait à mettre en concurrence une valeur sûre et
    une valeur lue, pour ne rien gagner et risquer de l'écraser.
    """
    out = []
    for p in (remplissage or {}).get("pieces", []):
        restes = [r for r in (p.get("rubriques") or [])
                  if r.get("source") in SOURCES_CIBLES
                  and r.get("source") not in SOURCES_INTERDITES
                  and r.get("statut") in STATUTS_CIBLES]
        if not restes:
            continue
        # DEUX ENTRÉES QUAND LA PIÈCE MÊLE LES DEUX, et pas une seule avec un
        # corpus élargi : ce qui décrit le candidat et ce qui décrit la
        # consultation ne se cherchent pas au même endroit, et les fondre
        # rouvrirait la porte au SIRET de l'acheteur.
        for cote, lot in (("cabinet", [r for r in restes
                                       if r.get("source") in SOURCES_DU_CANDIDAT]),
                          (None, [r for r in restes
                                  if r.get("source") not in SOURCES_DU_CANDIDAT])):
            if not lot:
                continue
            out.append({
                "cle": p.get("cle"),
                "nom": p.get("nom") or p.get("cle"),
                "dossier": p.get("dossier"),
                # LE CORPUS ADMIS POUR CETTE ENTRÉE. `None` veut dire « tout
                # ce qui a été déposé » ; « cabinet » borne aux documents que
                # nous avons fournis.
                "corpus_cote": cote,
                "rubriques": [{"cle": r.get("cle"), "libelle": r.get("libelle"),
                               "source": r.get("source"),
                               "aide": r.get("aide") or r.get("message") or ""}
                              for r in lot],
            })
    return out


def corpus_du_cote(corp, cote):
    """Le corpus borné à un côté — ou le corpus entier si aucun n'est demandé.

    RENDRE UN CORPUS VIDE PLUTÔT QUE LE CORPUS ENTIER quand notre côté est
    vide : c'est la différence entre « je ne trouve rien » et « je cherche le
    SIRET du candidat dans le règlement de l'acheteur ».
    """
    if not cote:
        return corp
    pieces = [x for x in (corp or {}).get("pieces") or []
              if x.get("cote") == cote]
    return dict(corp or {}, pieces=pieces,
                octets=sum(len(x.get("texte") or "") for x in pieces))


def requete(cible):
    """Ce qu'on va chercher dans le dossier, dérivé des RUBRIQUES elles-mêmes.

    PURE, et séparée de la recherche exprès : c'est la requête qui décide de la
    pertinence des passages, et elle doit s'éprouver seule.

    ELLE PART DES LIBELLÉS, PAS DU NOM DE LA PIÈCE. « Formulaire DC2 » ne
    ramène rien du dossier d'un acheteur ; « chiffre d'affaires effectifs
    références capacité technique » ramène les passages où la consultation dit
    ce qu'elle exige.
    """
    mots = [str(r.get("libelle") or "") for r in (cible or {}).get("rubriques", [])]
    return " ".join(" ".join(mots).split())[:600]


def corpus(documents, analyse=None):
    """Le texte déposé, pièce par pièce — LA SEULE SOURCE ADMISE POUR CITER.

    L'analyse ne transporte pas le texte : elle en rend la taille, le sigle et
    le rang de lecture. Le texte, lui, reste dans les documents déposés. Les
    apparier ici est ce qui permet à une citation de nommer « RC » plutôt que
    « document 3 ».

    L'ORDRE DE LECTURE EST CELUI DE L'ANALYSE. Le règlement de consultation
    passe avant le CCTP, et un fichier que l'identification n'a pas su nommer
    passe en dernier : si le budget de texte est atteint, c'est lui qu'on
    tronque, jamais le RC.
    """
    par_fichier = {}
    for p in (analyse or {}).get("pieces", []):
        par_fichier[p.get("fichier")] = (p.get("rang_lecture", 99),
                                         p.get("sigle") or p.get("code"), False)
    for p in (analyse or {}).get("inconnues", []):
        par_fichier.setdefault(p.get("fichier"), (900, None, True))
    # LES DOCUMENTS DU CABINET ONT UN RANG ET UN NOM, comme les autres.
    #
    # CE QUE LA SÉPARATION DES DEUX CÔTÉS AVAIT CASSÉ SANS LE DIRE. Depuis
    # qu'un document déposé du côté cabinet ne figure plus ni dans `pieces`
    # ni dans `inconnues`, il retombait sur le défaut `(950, None, True)` :
    # lu en DERNIER — donc le premier tronqué quand le budget de texte est
    # atteint — et marqué `non_identifie`, ce qui fait ressortir chaque
    # valeur qu'il porte avec « FICHIER NON IDENTIFIÉ, à confirmer ».
    # Autrement dit : une attestation déposée exprès, nommée sans ambiguïté
    # et rattachée à sa pièce, était lue comme un fichier anonyme de dernier
    # recours.
    #
    # LE RANG 500 LES PLACE APRÈS LES PIÈCES DE L'ACHETEUR ET AVANT LES
    # FICHIERS NON RECONNUS. C'est l'ordre du risque : ce que l'acheteur
    # écrit commande, ce que nous déposons vient ensuite, ce que personne
    # n'a su nommer passe en dernier.
    cabinet = set()
    for p in (analyse or {}).get("pieces_cabinet", []):
        cabinet.add(p.get("fichier"))
        par_fichier.setdefault(
            p.get("fichier"), (500, p.get("cle") or "cabinet", False))

    lus = []
    for d in (documents or []):
        nom = d.get("nom") or d.get("fichier") or ""
        texte = str(d.get("texte") or "")
        if not texte.strip():
            continue
        rang, sigle, inconnu = par_fichier.get(nom, (950, None, True))
        # LE CÔTÉ VOYAGE AVEC LE TEXTE, parce que la recherche en dépend :
        # une rubrique de la fiche ne se cherche QUE de notre côté.
        lus.append({"fichier": nom, "sigle": sigle, "texte": texte,
                    "rang": rang, "non_identifie": inconnu,
                    "cote": "cabinet" if nom in cabinet else "consultation"})
    lus.sort(key=lambda x: (x["rang"], x["fichier"]))

    # LE BUDGET SE DÉPENSE DANS L'ORDRE DE LECTURE, et ce qui dépasse est
    # ANNONCÉ. Tronquer en silence ferait dire « non trouvé » à une rubrique
    # dont la réponse était dans la partie qu'on n'a pas donnée à lire.
    total, gardes, tronques = 0, [], []
    for x in lus:
        reste = CORPUS_MAX - total
        if reste <= 0:
            tronques.append(x["fichier"])
            continue
        if len(x["texte"]) > reste:
            x = dict(x, texte=x["texte"][:reste], tronque=True)
            tronques.append(x["fichier"])
        total += len(x["texte"])
        gardes.append(x)
    for x in gardes:
        x.setdefault("tronque", False)
    return {"pieces": gardes, "octets": total, "tronques": tronques}


# ═══════════════════════════════════════════════════════════════════════════
#  LA CITATION SE VÉRIFIE — C'EST TOUT LE MODULE
# ═══════════════════════════════════════════════════════════════════════════

def _normaliser(s):
    """Ce qui est comparé : les mots, sans les blancs ni la casse ni les accents.

    POURQUOI CETTE TOLÉRANCE-LÀ ET PAS UNE AUTRE. Un lecteur de PDF recompose
    les blancs, coupe les lignes au milieu des phrases et rend parfois les
    accents autrement. Exiger l'identité stricte ferait rejeter des citations
    honnêtes. Tolérer davantage — la ponctuation, l'ordre des mots — laisserait
    passer une citation recomposée, c'est-à-dire inventée.
    """
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip().lower()


def verifier_citation(citation, corp):
    """La citation se retrouve-t-elle MOT POUR MOT dans une pièce déposée ?

    Rend la pièce et l'endroit du document, ou None. None fait REJETER la
    proposition entière — pas la dégrader.

    UNE CITATION TROP COURTE NE PROUVE RIEN. « 2026 » se retrouve dans
    n'importe quel dossier : accepter un fragment de quatre signes reviendrait
    à ne rien vérifier du tout.
    """
    aiguille = _normaliser(citation)
    if len(aiguille) < 24:
        return None
    for p in (corp or {}).get("pieces", []):
        meule = _normaliser(p["texte"])
        i = meule.find(aiguille)
        if i >= 0:
            part = int(round(100.0 * i / max(len(meule), 1)))
            return {"fichier": p["fichier"], "sigle": p["sigle"],
                    "part": part, "non_identifie": p.get("non_identifie", False)}
    return None


def retenir(cible, propositions, corp):
    """Le filtre : ne passe que ce qui est cité ET vérifié.

    Rend `(extraits, rejets)`. Les rejets sont NOMMÉS, jamais tus : une
    proposition écartée parce que sa citation est introuvable est le signal le
    plus important que ce module produit — il dit que le modèle a inventé.
    """
    attendues = {r["cle"] for r in (cible or {}).get("rubriques", [])}
    extraits, rejets = {}, []
    for p in (propositions or []):
        cle = str(p.get("rubrique") or "")
        valeur = str(p.get("valeur") or "").strip()
        citation = str(p.get("citation") or "").strip()
        if cle not in attendues:
            rejets.append({"rubrique": cle, "motif": "hors_cible",
                           "dit": "Cette rubrique n'était pas demandée."})
            continue
        if not valeur:
            continue
        if not citation:
            rejets.append({"rubrique": cle, "motif": "sans_citation",
                           "dit": "Valeur proposée sans passage à l'appui."})
            continue
        ou = verifier_citation(citation, corp)
        if ou is None:
            rejets.append({"rubrique": cle, "motif": "citation_introuvable",
                           "dit": "Le passage cité ne se retrouve dans aucune "
                                  "pièce déposée.", "citation": citation[:200]})
            continue
        extraits["%s.%s" % (cible["cle"], cle)] = {
            "valeur": valeur, "citation": citation,
            "fichier": ou["fichier"], "sigle": ou["sigle"], "part": ou["part"],
            "non_identifie": ou["non_identifie"], "piece_reponse": cible["cle"],
            "rubrique": cle,
        }
    return extraits, rejets


# ═══════════════════════════════════════════════════════════════════════════
#  L'APPEL — la seule impureté, et le client y est injecté
# ═══════════════════════════════════════════════════════════════════════════

OUTIL = "reporter_les_rubriques"

CONSIGNE = (
    "Vous lisez les pièces d'une consultation (marché public ou privé) pour "
    "reporter des rubriques d'un dossier de réponse.\n\n"
    "RÈGLE ABSOLUE : chaque valeur que vous rendez doit être accompagnée d'un "
    "passage RECOPIÉ MOT POUR MOT depuis les pièces fournies. Le passage est "
    "vérifié caractère par caractère contre le texte déposé : un passage "
    "reformulé, résumé ou reconstitué fait rejeter la valeur.\n\n"
    "SI UNE RUBRIQUE N'EST PAS DANS LES PIÈCES, NE LA RENDEZ PAS. Une rubrique "
    "absente de votre réponse sera présentée comme « à saisir », ce qui est "
    "exact et sans danger. Une rubrique inventée serait recopiée sur un "
    "formulaire signé — c'est la seule faute qui compte ici.\n\n"
    "La valeur est ce qui se recopie dans la case : courte, sans commentaire, "
    "sans « selon le RC ». Le passage cité porte le contexte."
)


def _outil(cible):
    """Le schéma de sortie, dérivé des rubriques demandées.

    PURE : une règle doit pouvoir vérifier que l'outil n'offre QUE les
    rubriques de la pièce — un schéma ouvert laisserait le modèle rendre des
    clés que le report ne connaît pas, et `retenir` les jetterait sans qu'on
    sache que le schéma en était la cause.
    """
    cles = [r["cle"] for r in cible["rubriques"]]
    return {
        "name": OUTIL,
        "description": ("Reporter les rubriques trouvées dans les pièces "
                        "déposées, chacune avec son passage à l'appui."),
        "input_schema": {
            "type": "object",
            "properties": {
                "rubriques": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rubrique": {"type": "string", "enum": cles},
                            "valeur": {"type": "string"},
                            "citation": {"type": "string"},
                        },
                        "required": ["rubrique", "valeur", "citation"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["rubriques"],
            "additionalProperties": False,
        },
    }


def demande(cible, corp):
    """Le message : les rubriques à trouver, puis les pièces à lire.

    PURE. L'ordre compte — les rubriques AVANT le texte : ce qui est demandé
    doit être lu avant les centaines de pages, pas après.
    """
    rub = "\n".join(
        "- `%s` — %s%s" % (r["cle"], r["libelle"],
                           ("  (%s)" % r["aide"]) if r.get("aide") else "")
        for r in cible["rubriques"])
    pieces = "\n\n".join(
        "───── %s (%s)%s ─────\n%s"
        % (p["sigle"] or p["fichier"], p["fichier"],
           " — FICHIER NON IDENTIFIÉ" if p.get("non_identifie") else "",
           p["texte"])
        for p in corp.get("pieces", []))
    return ("Pièce de réponse à remplir : « %s ».\n\n"
            "Rubriques à trouver :\n%s\n\n"
            "Pièces déposées par l'acheteur :\n\n%s"
            % (cible["nom"], rub, pieces))


def _client():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ExtractionError("sans_cle", 503,
                              "ANTHROPIC_API_KEY n'est pas posée : la lecture "
                              "assistée est indisponible.")
    try:
        import anthropic
    except ImportError:
        raise ExtractionError("sans_sdk", 503, "Le paquet anthropic manque.")
    return anthropic


def extraire(cible, corp, client=None):
    """UNE pièce, UN appel : les rubriques trouvées, chacune avec sa citation.

    Le client est injecté pour que les règles éprouvent la chaîne entière sans
    clé ni réseau. Sans injection, on prend celui du module.

    CE QUI SORT N'EST PAS CE QUE LE MODÈLE A DIT : c'est ce que `retenir` a
    laissé passer. Les deux sont rendus — les retenus ET les rejetés — parce
    qu'un rejet pour citation introuvable est une information sur le modèle,
    pas un détail d'implémentation.
    """
    if not cible.get("rubriques"):
        return {"cle": cible.get("cle"), "extraits": {}, "rejets": [],
                "propositions": 0}
    if not (corp or {}).get("pieces"):
        raise ExtractionError("sans_dossier", 400,
                              "Aucune pièce déposée à lire : sans dossier, "
                              "toute valeur serait inventée.")
    anthropic = client or _client()
    cli = anthropic.Anthropic()
    outil = _outil(cible)
    try:
        reponse = cli.messages.create(
            model=MODELE,
            max_tokens=JETONS_MAX,
            timeout=DELAI,
            system=[{"type": "text", "text": CONSIGNE,
                     # LA CONSIGNE EST MISE EN CACHE : les sept pièces d'un
                     # même dossier partagent ce préfixe, et l'atelier se
                     # relance à chaque dépôt complémentaire.
                     "cache_control": {"type": "ephemeral"}}],
            tools=[outil],
            tool_choice={"type": "tool", "name": OUTIL},
            messages=[{"role": "user", "content": demande(cible, corp)}])
    except ExtractionError:
        # UN REFUS DÉJÀ NOMMÉ TRAVERSE. Le filet ci-dessous classe les pannes
        # du fournisseur d'après le NOM de leur classe ; sans cette sortie il
        # avalait aussi nos propres refus et les rendait tous en « api » — un
        # défaut trouvé par la règle de l'éventail, qui attendait « reseau ».
        raise
    except Exception as exc:                       # noqa: BLE001
        nom = type(exc).__name__
        if nom == "RateLimitError":
            raise ExtractionError("cadence", 429, "Le fournisseur limite la cadence.")
        if nom in ("APIConnectionError", "APITimeoutError"):
            raise ExtractionError("reseau", 502, "Le fournisseur est injoignable.")
        if nom == "AuthenticationError":
            raise ExtractionError("cle_refusee", 502, "La clé a été refusée.")
        if nom == "NotFoundError":
            raise ExtractionError("modele_inconnu", 502,
                                  "Le modèle « %s » n'est pas ouvert à cette clé."
                                  % MODELE)
        raise ExtractionError("api", 502, str(exc)[:300])

    props = []
    for b in getattr(reponse, "content", []) or []:
        if getattr(b, "type", "") == "tool_use" and getattr(b, "name", "") == OUTIL:
            entree = getattr(b, "input", None) or {}
            if isinstance(entree, str):
                try:
                    entree = json.loads(entree)
                except ValueError:
                    entree = {}
            props.extend(entree.get("rubriques") or [])

    extraits, rejets = retenir(cible, props, corp)
    u = getattr(reponse, "usage", None)
    return {
        "cle": cible["cle"], "nom": cible["nom"],
        "extraits": extraits, "rejets": rejets,
        "propositions": len(props), "retenus": len(extraits),
        "modele": getattr(reponse, "model", MODELE),
        "jetons": {"entree": getattr(u, "input_tokens", 0),
                   "sortie": getattr(u, "output_tokens", 0),
                   "cache_lu": getattr(u, "cache_read_input_tokens", 0)} if u else {},
    }


def lire_le_dossier(remplissage, documents, analyse=None, client=None,
                    executeur=None):
    """Toutes les pièces, EN ÉVENTAIL : le temps mur est celui de la plus lente.

    Sept pièces enchaînées, c'est la somme des sept attentes. Lancées ensemble,
    c'est la plus longue — et le dossier se remplit pendant qu'on regarde.

    L'EXÉCUTEUR EST INJECTÉ. Une règle doit pouvoir dérouler l'éventail en
    séquence, sans fil d'exécution, pour que ce qu'elle mesure soit le RÉSULTAT
    et non l'ordonnancement.

    UNE PIÈCE QUI TOMBE NE FAIT PAS TOMBER LE DOSSIER. Son échec est nommé et
    les six autres remplissent. Un atelier tout-ou-rien rendrait zéro rubrique
    parce qu'une pièce a dépassé le délai.
    """
    corp = corpus(documents, analyse)
    liste = cibles(remplissage)
    if not liste:
        return {"extraits": {}, "rejets": [], "pieces": [], "echecs": [],
                "corpus": {"octets": corp["octets"], "tronques": corp["tronques"]}}

    def un(cible):
        try:
            return (cible,
                    extraire(cible,
                             corpus_du_cote(corp, cible.get("corpus_cote")),
                             client=client), None)
        except ExtractionError as e:
            return (cible, None, {"cle": cible["cle"], "nom": cible["nom"],
                                  "code": e.code, "dit": e.detail})
        except Exception as e:                     # noqa: BLE001
            _log.exception("lecture assistée : pièce %s", cible.get("cle"))
            return (cible, None, {"cle": cible["cle"], "nom": cible["nom"],
                                  "code": "inattendu", "dit": str(e)[:200]})

    # UNE CIBLE SANS CORPUS N'EST PAS UN ÉCHEC, C'EST UN NON-LIEU. Les
    # rubriques de la fiche ne se cherchent que dans les documents du cabinet ;
    # quand on n'en a déposé aucun, il n'y a rien à lire — et lancer l'appel
    # pour récolter un « sans_dossier » par pièce remplirait le bilan d'échecs
    # qui ne disent rien, en consommant des jetons pour rien.
    liste = [c for c in liste
             if (corpus_du_cote(corp, c.get("corpus_cote")) or {}).get("pieces")]
    if not liste:
        return {"extraits": {}, "rejets": [], "pieces": [], "echecs": [],
                "corpus": {"octets": corp["octets"],
                           "tronques": corp["tronques"]}}

    resultats = list(executeur(un, liste)) if executeur else [un(c) for c in liste]

    extraits, rejets, pieces, echecs = {}, [], [], []
    for _cible, r, echec in resultats:
        if echec:
            echecs.append(echec)
            continue
        extraits.update(r["extraits"])
        rejets.extend(r["rejets"])
        pieces.append({k: r[k] for k in ("cle", "nom", "propositions",
                                         "retenus", "jetons") if k in r})
    return {"extraits": extraits, "rejets": rejets, "pieces": pieces,
            "echecs": echecs,
            "corpus": {"octets": corp["octets"], "tronques": corp["tronques"]}}
