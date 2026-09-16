# -*- coding: utf-8 -*-
"""L'ÉTAGÈRE DU CABINET — les documents qu'on dépose UNE FOIS et qui servent
à tous les dossiers suivants.

CE QUI ÉTAIT EN CAUSE. Le § 14 a deux zones de dépôt : les pièces de
l'acheteur, et les nôtres. Celles de l'acheteur changent à chaque
consultation, et c'est normal. Les nôtres — organigramme, CV, moyens,
certifications, références, note méthodologique — sont les MÊMES d'un dossier
à l'autre, et il fallait pourtant les redéposer à chaque fois : elles vivaient
le temps d'une page.

CE MODULE N'EST PAS UN SECOND MAGASIN, et c'est la décision qui commande tout
le reste. L'étagère EST la famille « CONSEILPREV — pièces du cabinet » de la
base de connaissance. Elle est déjà lue par les deux chercheurs qui comptent :

  · `ao_extraction.chercher_au_fonds` — qui remplit les formulaires ;
  · `ao_redaction.chercher_au_fonds_cabinet` — qui rédige les brouillons.

Ranger un document ailleurs aurait demandé de brancher une troisième source
dans les deux, et une troisième source qu'on oublie de brancher est une
étagère qui a l'air pleine et ne sert à rien.

CE QUE CE MODULE PORTE, DONC : les règles PROPRES à l'étagère — le plafond, le
rayon déduit de la pièce, et le choix de publication qui décide si un document
nourrira les brouillons. Le stockage, l'extraction et le découpage restent au
magasin, qui les fait déjà.
"""
import logging

import reglages

_log = logging.getLogger("dossier_cabinet")

VERSION = "2026-09-a"

#: COMBIEN DE DOCUMENTS L'ÉTAGÈRE PORTE, ET POURQUOI CE NOMBRE-LÀ.
#:
#: Les vingt-trois pièces d'une réponse se ramènent à une dizaine de TYPES de
#: documents du cabinet — les dix rayons de la famille. Quinze laisse de quoi
#: tenir deux versions de ce qui vieillit (l'organigramme, les références) sans
#: ouvrir la porte à une archive.
#:
#: LE PLAFOND EST UNE DÉCISION, PAS UNE LIMITE TECHNIQUE. Une étagère qu'on lit
#: d'un écran est une étagère qu'on tient à jour ; à cinquante documents, plus
#: personne ne sait lequel est la dernière version, et les chercheurs ramènent
#: le plus vieux aussi souvent que le plus récent. Le refus NOMME ce qu'il faut
#: retirer plutôt que de laisser supprimer au hasard.
MAX_DOCUMENTS = reglages.entier("AO_CABINET_MAX_DOCS", 15, mini=1, maxi=60)


class EtagereError(Exception):
    """Erreur portant un code interne et un statut HTTP."""

    def __init__(self, code, status=400, detail=""):
        Exception.__init__(self, code)
        self.code = code
        self.status = status
        self.detail = detail


# ── LES DEUX RÉGIMES DE PUBLICATION, ET CE QU'ILS COÛTENT ──────────────────
#
# CE CHOIX N'EST PAS UN DÉTAIL DE RANGEMENT : il décide si le document
# nourrira les BROUILLONS. `ao_redaction` lit les rayons qui peuvent décrire un
# TIERS — mémoires passés, références — uniquement s'ils sont publiables,
# parce qu'un brouillon recopie ses extraits et part chez un acheteur.
#
# LE DÉFAUT EST « interne », ET C'EST DÉLIBÉRÉ. Se tromper vers l'interne coûte
# un brouillon plus maigre ; se tromper vers le publiable peut envoyer
# l'architecture d'un client chez un autre. Des deux erreurs, une seule se
# rattrape.
VISIBILITES = {
    "internal": {
        "nom": "Interne",
        "dit": "Lisible pour remplir vos formulaires. Sur les rayons qui "
               "peuvent décrire un client — mémoires, références — il ne "
               "nourrira PAS les brouillons.",
    },
    "public": {
        "nom": "Publiable",
        "dit": "Ses extraits pourront être recopiés dans un brouillon remis à "
               "un acheteur. Ne le marquez ainsi que si rien n'y engage la "
               "confidentialité d'un client.",
    },
}
VISIBILITE_DEFAUT = "internal"


def rayons():
    """Les rayons de l'étagère, tels que la base les déclare."""
    import rag_store                                              # noqa: PLC0415
    return rag_store.themes_famille(rag_store.FAMILLE_CABINET)


def destination(cle_piece, nom=""):
    """Où ce document se range — ou pourquoi il ne se range pas.

    FONCTION PURE, et c'est ce qui la rend éprouvable : ce qui décide du rayon
    d'un document doit se mesurer sans magasin.

    TROIS RÉPONSES ET PAS DEUX. « Rangeable ici », « reconnu mais qui ne se
    conserve pas » — une DPGF chiffrée pour ce marché-ci — et « pas reconnu ».
    Les deux derniers se soignent différemment : l'un ne se soigne pas, l'autre
    demande de renommer le fichier. Les confondre ferait chercher une faute de
    nommage là où il n'y en a pas.
    """
    import ao_dc                                                  # noqa: PLC0415
    if not cle_piece:
        # ── LA DOCUMENTATION N'EST PAS UNE PIÈCE, ET SE RANGE QUAND MÊME ──
        #
        # Une fiche technique, un guide, une norme ne fournissent AUCUNE des
        # vingt-trois pièces à produire — on ne remet pas un guide ANSSI à un
        # acheteur dans un dossier de candidature. Ils sont pourtant la
        # matière avec laquelle un mémoire technique s'écrit. Les refuser
        # parce qu'ils ne sont pas des pièces, c'était refuser sept des neuf
        # types de documents qu'un cabinet conserve.
        rayon = ao_dc.documentation_du_cabinet(nom)
        if rayon:
            return {"rayon": rayon, "refus": "", "dit": ""}
        return {"rayon": "", "refus": "piece_inconnue",
                "dit": "Le nom de ce fichier ne dit ni la pièce qu'il fournit, "
                       "ni la documentation qu'il apporte. Renommez-le d'après "
                       "l'un ou l'autre — « organigramme.pdf », "
                       "« references-2025.docx », « fiche-technique-groupe-"
                       "froid.pdf », « guide-anssi.pdf », « norme-EN-50600.pdf » "
                       "— et redéposez-le."}
    motif = ao_dc.SANS_ETAGERE.get(cle_piece)
    if motif:
        return {"rayon": "", "refus": "ne_se_conserve_pas", "dit": motif}
    rayon = ao_dc.theme_cabinet(cle_piece)
    if not rayon:
        return {"rayon": "", "refus": "sans_rayon",
                "dit": "Cette pièce n'a pas de rayon déclaré sur l'étagère."}
    return {"rayon": rayon, "refus": "", "dit": ""}


def etagere(rag=None):
    """Ce qui est rangé, rayon par rayon, et ce qu'il reste de place.

    LE MAGASIN EST INJECTÉ, JAMAIS DEVINÉ — comme partout ailleurs dans ce
    dossier. Sans lui, on rend une étagère VIDE ET NOMMÉE : l'écran dit que la
    base n'est pas jointe au lieu d'annoncer zéro document, ce qui se lirait
    comme « vous n'avez rien rangé ».
    """
    vide = {"documents": [], "total": 0, "places": MAX_DOCUMENTS,
            "plafond": MAX_DOCUMENTS, "rayons": rayons(),
            "absent": "magasin_non_joint"}
    if rag is None:
        return vide
    try:
        connus = set(rayons())
        docs = [d for d in rag.list_documents(limit=200)
                if (d.get("theme") or "") in connus]
    except Exception:
        _log.exception("étagère du cabinet : base injoignable")
        return dict(vide, absent="base_injoignable")
    docs.sort(key=lambda d: ((d.get("theme") or ""), (d.get("title") or "")))
    lignes = [{"id": d.get("id") or d.get("doc_id") or "",
               "titre": d.get("title") or d.get("filename") or "",
               "fichier": d.get("filename") or "",
               "rayon": d.get("theme") or "",
               "visibilite": d.get("visibility") or "",
               # CE QUE CE DOCUMENT NOURRIT, DIT SUR SA LIGNE. Un document
               # interne rangé sur un rayon « tiers » ne nourrit pas les
               # brouillons — et c'est invisible sans cette colonne.
               "nourrit_les_brouillons": _nourrit(d.get("theme") or "",
                                                  d.get("visibility") or ""),
               "octets": d.get("bytes") or d.get("size") or 0}
              for d in docs]
    return {"documents": lignes, "total": len(lignes),
            "places": max(0, MAX_DOCUMENTS - len(lignes)),
            "plafond": MAX_DOCUMENTS, "rayons": rayons(), "absent": ""}


def _nourrit(rayon, visibilite):
    """Ce document atteindra-t-il un brouillon ?

    ELLE LIT `ao_redaction`, ELLE NE RECOPIE PAS SA RÈGLE. Deux tables des
    mêmes rayons auraient divergé, et la divergence se serait vue comme une
    colonne qui promet un apport que le rédacteur refuse.
    """
    import ao_redaction                                           # noqa: PLC0415
    if rayon in ao_redaction.FONDS_NOUS:
        return True
    if rayon in ao_redaction.FONDS_TIERS:
        return visibilite == "public"
    # LA DOCUMENTATION NOURRIT, QUEL QUE SOIT LE RÉGIME — et l'oublier ici
    # était une faute en sens INVERSE de celle que cette fonction devait
    # éviter : l'écran aurait dit qu'une norme rangée n'atteint aucun
    # brouillon, alors que le rédacteur la lit sans filtre de publication.
    # Une colonne qui NIE un apport réel se paie deux fois — on range moins,
    # et on relit moins ce qui sort.
    #
    # LE RÉGIME NE COMMANDE PAS CE LOT, parce que le risque qu'il porte n'est
    # pas la confidentialité d'un client mais le droit d'auteur d'un tiers :
    # marquer publiable une norme ne donne pas le droit de la recopier. La
    # barrière est dans la consigne de rédaction, pas dans le rangement.
    if rayon in ao_redaction.FONDS_DOCUMENTATION:
        return True
    return False


def ranger(rag, nom, octets, cle_piece, visibilite=VISIBILITE_DEFAUT,
           titre=""):
    """Poser UN document sur l'étagère. Rend ce que le magasin a enregistré.

    LE PLAFOND SE VÉRIFIE AVANT L'ÉCRITURE, et le refus NOMME l'étagère :
    « quinze sur quinze » sans dire lesquels laisse supprimer au hasard.

    UN DOCUMENT DÉJÀ PRÉSENT NE COMPTE PAS DEUX FOIS : le magasin dédoublonne
    sur l'empreinte du contenu et met le rayon à jour. Redéposer une version
    identique est donc sans effet — et redéposer une version CORRIGÉE crée une
    entrée de plus, ce qui est le comportement voulu : c'est à l'opérateur de
    retirer l'ancienne, et l'écran lui montre les deux.
    """
    if rag is None:
        raise EtagereError("magasin_absent", 503,
                           "La base de connaissance n'est pas jointe : "
                           "impossible de conserver un document.")
    d = destination(cle_piece, nom)
    if d["refus"]:
        raise EtagereError(d["refus"], 400, d["dit"])
    if visibilite not in VISIBILITES:
        raise EtagereError("visibilite_inconnue", 400,
                           "Le régime de publication doit être « %s »."
                           % " » ou « ".join(VISIBILITES))
    etat = etagere(rag)
    if etat["absent"]:
        raise EtagereError("etagere_illisible", 503,
                           "L'étagère n'a pas pu être lue (%s) : on ne range "
                           "pas dans une étagère qu'on ne voit pas."
                           % etat["absent"])
    if etat["total"] >= MAX_DOCUMENTS:
        raise EtagereError(
            "etagere_pleine", 409,
            "L'étagère porte déjà %d documents sur %d. Retirez-en un avant "
            "d'ajouter : %s." % (etat["total"], MAX_DOCUMENTS,
                                 ", ".join(x["titre"] for x in
                                           etat["documents"][:6]) or "—"))
    import rag_store                                              # noqa: PLC0415
    try:
        doc = rag.ingest_bytes(nom, octets, title=(titre or "").strip(),
                               theme=d["rayon"], visibility=visibilite)
    except rag_store.RagError as exc:
        raise EtagereError(exc.code, getattr(exc, "status", 400),
                           getattr(exc, "detail", "") or "")
    return {"range": True, "rayon": d["rayon"], "visibilite": visibilite,
            "nourrit_les_brouillons": _nourrit(d["rayon"], visibilite),
            "document": {"id": (doc or {}).get("id") or "",
                         "titre": (doc or {}).get("title") or nom},
            "etagere": etagere(rag)}
