# -*- coding: utf-8 -*-
"""L'ATELIER : lire, remplir, rédiger, RELIRE CE QU'ON VIENT D'ÉCRIRE, et boucler.

CE QUI MANQUAIT, ET QUI N'ÉTAIT PAS UN DÉTAIL. Le remplissage était une PASSE :
analyser → remplir → rédiger, puis fin. Or le mémoire technique qu'on vient de
rédiger contient l'équipe, les moyens et les références — exactement ce que le
DC2 et l'acte d'engagement redemandent trois cases plus loin. Personne ne le
relisait. Chaque tour de boucle rend donc au dossier ce que le tour précédent y
a écrit.

LA BOUCLE S'ARRÊTE QUAND ELLE N'APPORTE PLUS RIEN, pas au bout d'un nombre
choisi à l'avance. Un compteur fixe s'arrête trop tôt sur les gros dossiers et
tourne pour rien sur les petits. Le critère est le seul qui compte : ce tour
a-t-il rempli une rubrique de plus ? Un plafond dur reste, mais comme
garde-fou — pas comme règle.

ET LES BROUILLONS ENTRENT DANS LE CORPUS SOUS LEUR PROPRE NOM. Une valeur lue
dans un brouillon que nous avons écrit n'a pas le même poids qu'une valeur lue
dans le règlement de l'acheteur : elle est citable, vérifiable, mais elle vient
de nous. La pièce d'origine le dit, et l'écran le montre.

L'ÉVENTAIL — POURQUOI IL EST INJECTÉ. Sept extractions et onze rédactions sont
indépendantes : enchaînées, c'est la somme des dix-huit attentes ; lancées
ensemble, c'est la plus longue. L'exécuteur est un argument pour qu'une règle
puisse dérouler l'atelier en séquence et mesurer le RÉSULTAT, jamais
l'ordonnancement.

CE QUI NE S'AUTOMATISERA PAS, ET QUI EST RÉCLAMÉ TÔT. Les attestations fiscales
et sociales, les assurances, les bilans, les pouvoirs et les CV ne sortent
d'aucun algorithme. L'atelier les nomme AU PREMIER TOUR, avec ce qu'il faut
faire pour les obtenir — les découvrir la veille du dépôt est la façon la plus
courante de perdre une consultation qu'on avait gagnée.
"""
import logging

import reglages

import ao_dc
import ao_extraction
import ao_redaction


_log = logging.getLogger(__name__)

# LE PLAFOND EST UN GARDE-FOU, PAS LE CRITÈRE D'ARRÊT. La boucle s'arrête
# d'elle-même dès qu'un tour n'apporte rien ; ce nombre n'existe que pour le
# cas où un apport fantôme se répéterait indéfiniment.
TOURS_MAX = reglages.entier("AO_ATELIER_TOURS_MAX", 3, mini=1, maxi=6)

# COMBIEN DE TRAVAUX EN MÊME TEMPS. Au-delà, on ne gagne plus rien et on se
# fait limiter par le fournisseur — ce qui rallonge tout au lieu de raccourcir.
EVENTAIL = reglages.entier("AO_ATELIER_EVENTAIL", 6, mini=1, maxi=16)


def executeur_parallele(largeur=None):
    """L'éventail réel. Rendu par une fabrique pour rester injectable.

    RIEN N'EST PARTAGÉ ENTRE LES TRAVAUX : chaque appel lit un corpus immuable
    et rend son propre résultat. C'est ce qui rend le parallélisme sûr ici, et
    c'est la raison pour laquelle il ne faut RIEN y ajouter qui écrive.
    """
    import concurrent.futures as cf
    n = max(1, int(largeur or EVENTAIL))

    def lancer(fn, items):
        items = list(items)
        if len(items) <= 1:
            return [fn(x) for x in items]
        with cf.ThreadPoolExecutor(max_workers=min(n, len(items))) as pool:
            return list(pool.map(fn, items))
    return lancer


def a_reclamer(remplissage):
    """CE QU'AUCUN ALGORITHME NE PRODUIRA, nommé dès le premier tour.

    PURE. Les pièces dont la voie est « obtenir » viennent d'un tiers — le
    greffe, l'assureur, l'expert-comptable, la personne habilitée. Les
    découvrir la veille du dépôt est la façon la plus courante de perdre une
    consultation qu'on avait gagnée.
    """
    out = []
    for p in (remplissage or {}).get("pieces", []):
        if p.get("voie") != "obtenir":
            continue
        out.append({"cle": p.get("cle"), "nom": p.get("nom") or p.get("cle"),
                    "dossier": p.get("dossier"),
                    "bloquant": bool(p.get("bloquant")),
                    "ou": p.get("produit_par") or p.get("ou") or "",
                    "piege": p.get("piege") or ""})
    # LES BLOQUANTES EN PREMIER : c'est l'ordre dans lequel il faut s'en
    # occuper, pas l'ordre du catalogue.
    out.sort(key=lambda x: (not x["bloquant"], x["nom"]))
    return out


def _brouillons_en_corpus(brouillons):
    """Les brouillons produits, rendus lisibles au tour suivant.

    ILS ENTRENT SOUS LEUR PROPRE NOM, jamais confondus avec une pièce de
    l'acheteur : le sigle porte « BROUILLON », et une valeur qui en sera tirée
    dira d'où elle vient. Les fondre dans le dossier déposé ferait citer comme
    exigence de l'acheteur une phrase que nous avons écrite nous-mêmes.
    """
    return [{"nom": "brouillon-%s.md" % b["cle"],
             "texte": b.get("markdown") or ""}
            for b in (brouillons or []) if (b.get("markdown") or "").strip()]


def _analyse_avec_brouillons(analyse, brouillons):
    """L'analyse, augmentée des brouillons déclarés NON IDENTIFIÉS.

    `ao_extraction.corpus` range les fichiers inconnus en dernier : un
    brouillon ne peut donc pas prendre le pas sur le règlement de consultation
    quand le budget de texte est atteint. C'est exactement le rang qu'il doit
    avoir.
    """
    a = dict(analyse or {})
    inconnues = list(a.get("inconnues") or [])
    for b in (brouillons or []):
        if (b.get("markdown") or "").strip():
            inconnues.append({"fichier": "brouillon-%s.md" % b["cle"],
                              "sigle": "BROUILLON %s" % b["cle"], "releves": []})
    a["inconnues"] = inconnues
    return a


def rediger_tout(remplissage, analyse, corpus_dossier, rag=None,
                 client=None, executeur=None, pieces=None):
    """Les pièces rédigeables, EN ÉVENTAIL. Une qui tombe n'emporte pas les autres."""
    redigeables = ao_redaction.pieces_redigeables(remplissage)
    if pieces is not None:
        garder = set(pieces)
        redigeables = [p for p in redigeables if p["cle"] in garder]

    def un(p):
        try:
            if client is not None:
                garde = ao_redaction._client
                ao_redaction._client = lambda: client
                try:
                    return (ao_redaction.rediger(p["cle"], remplissage,
                                                 analyse=analyse, rag=rag,
                                                 corpus_dossier=corpus_dossier),
                            None)
                finally:
                    ao_redaction._client = garde
            return (ao_redaction.rediger(p["cle"], remplissage, analyse=analyse,
                                         rag=rag, corpus_dossier=corpus_dossier),
                    None)
        except ao_redaction.RedactionError as e:
            return (None, {"cle": p["cle"], "nom": p["nom"], "code": e.code,
                           "dit": e.detail})
        except Exception as e:                      # noqa: BLE001
            _log.exception("rédaction : pièce %s", p.get("cle"))
            return (None, {"cle": p["cle"], "nom": p["nom"],
                           "code": "inattendu", "dit": str(e)[:200]})

    faits = list(executeur(un, redigeables)) if executeur else [un(p) for p in redigeables]
    return ([b for b, _e in faits if b], [e for _b, e in faits if e])


def _remplies(remplissage):
    return sum(1 for p in (remplissage or {}).get("pieces", [])
               for x in (p.get("rubriques") or []) if x.get("statut") == "rempli")


def atelier(fiche=None, documents=None, analyse=None, saisies=None,
            groupement=False, fournies=None, perimetre=None,
            rag=None, client_extraction=None, client_redaction=None,
            executeur=None, tours_max=None, rediger=True):
    """Le dossier entier, jusqu'à ce qu'un tour n'apporte plus rien.

    Rend le remplissage final, les brouillons, ce qui a été lu, ce qui a été
    REJETÉ, ce qu'il reste à réclamer, et le journal des tours — parce qu'un
    atelier qui rend un résultat sans dire ce qu'il a fait ne se débogue pas.
    """
    documents = list(documents or [])
    analyse = analyse if analyse is not None else ao_dc.analyser(documents)
    plafond = int(tours_max or TOURS_MAX)

    extraits, rejets, brouillons, echecs, journal = {}, [], [], [], []
    reclamations = None

    for tour in range(1, plafond + 1):
        remplissage = ao_dc.remplir(fiche=fiche, analyse=analyse,
                                    saisies=saisies, groupement=groupement,
                                    fournies=fournies, perimetre=perimetre,
                                    extraits=extraits)
        if reclamations is None:
            # AU PREMIER TOUR, et une seule fois : ce qui ne viendra jamais
            # d'un algorithme se réclame tout de suite.
            reclamations = a_reclamer(remplissage)

        avant = _remplies(remplissage)
        an_lecture = _analyse_avec_brouillons(analyse, brouillons)
        docs_lecture = documents + _brouillons_en_corpus(brouillons)

        lu = ao_extraction.lire_le_dossier(remplissage, docs_lecture, an_lecture,
                                           client=client_extraction,
                                           executeur=executeur)
        neufs = {k: v for k, v in lu["extraits"].items() if k not in extraits}
        extraits.update(neufs)
        rejets.extend(lu["rejets"])
        echecs.extend(lu["echecs"])

        apres_lecture = ao_dc.remplir(fiche=fiche, analyse=analyse,
                                      saisies=saisies, groupement=groupement,
                                      fournies=fournies, perimetre=perimetre,
                                      extraits=extraits)
        gagne = _remplies(apres_lecture) - avant

        redigees = 0
        if rediger and not brouillons:
            # LES BROUILLONS SE PRODUISENT UNE FOIS, AU TOUR OÙ LE REPORT EST
            # LE PLUS COMPLET. Les refaire à chaque tour paierait onze appels
            # de modèle pour réécrire un texte que le tour précédent a déjà
            # rendu — et rendrait le résultat instable d'un tour à l'autre.
            corp = ao_extraction.corpus(documents, analyse)
            brouillons, ech = rediger_tout(apres_lecture, analyse, corp, rag=rag,
                                           client=client_redaction,
                                           executeur=executeur)
            echecs.extend(ech)
            redigees = len(brouillons)

        journal.append({"tour": tour, "remplies_avant": avant,
                        "lues": len(neufs), "gagnees": gagne,
                        "redigees": redigees,
                        "rejets": len(lu["rejets"])})

        # LE CRITÈRE D'ARRÊT : ce tour a-t-il apporté quelque chose ? Ni un
        # compteur, ni une heuristique — l'apport lui-même.
        if not neufs and not redigees:
            break

    final = ao_dc.remplir(fiche=fiche, analyse=analyse, saisies=saisies,
                          groupement=groupement, fournies=fournies,
                          perimetre=perimetre, extraits=extraits)
    return {
        "remplissage": final,
        "brouillons": brouillons,
        "extraits": extraits,
        "rejets": rejets,
        "echecs": echecs,
        "reclamations": reclamations or [],
        "journal": journal,
        "tours": len(journal),
        "remplies": _remplies(final),
        "rubriques": sum(len(p.get("rubriques") or [])
                         for p in final.get("pieces", [])),
    }
