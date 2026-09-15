# -*- coding: utf-8 -*-
"""Le fonds documentaire entre dans le REMPLISSAGE — par une porte nommée.

CE QUE J'AVAIS RÉPONDU, ET QUI ÉTAIT FAUX. « Le RAG contient les CCTP et les
dossiers d'AUTRES consultations ; le brancher sur le remplissage importerait
les valeurs d'un autre marché dans le DC1 de celui-ci. » La base contient
aussi — et c'est ce que ma lecture avait manqué — les pièces de CONSEILPREV
elle-même : Kbis, bilans, attestations, mémoires, références. Les laisser
dehors revenait à retaper à la main ce que la maison a déjà déposé une fois.

CE QUI RESTE VRAI, ET QUI COMMANDE LA FORME DU BRANCHEMENT. La base contient
LES DEUX. Normes, guides ANSSI, CCTP d'autres marchés et références clientes
nommées y voisinent avec nos propres pièces, et aucun champ ne disait
lesquelles sont les nôtres. Chercher « chiffre d'affaires » dans un fonds
indifférencié ramènerait celui d'EDF.

CE QUE CES RÈGLES MESURENT, ET POURQUOI ELLES NE SE CONTENTENT PAS DE
CONSTATER. Le défaut qu'on chasse ici — une règle verte pendant que l'effet
est nul — se serait écrit tout seul : « `rag` figure dans la signature de
`lire_le_dossier` ». Ce serait vrai, et le fonds pourrait n'apporter aucune
pièce. On mesure donc COMBIEN de rubriques deviennent cherchables, QUELS
documents entrent, et surtout lesquels ne peuvent PAS entrer.
"""
import os
import types

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import ao_atelier as T                                           # noqa: E402
import ao_dc as A                                                # noqa: E402
import ao_extraction as X                                        # noqa: E402
import rag_store as R                                            # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
#  UN MAGASIN DE DÉMONSTRATION — trois documents, et un seul jeu de règles
# ═══════════════════════════════════════════════════════════════════════════
#
# LES TROIS SONT CHOISIS POUR CE QU'ILS RISQUENT :
#   · le Kbis est INTERNE — s'il faut `public_only`, il ne sort jamais, et le
#     branchement ne sert précisément à rien ;
#   · le bilan porte un chiffre d'affaires, mot que la requête ramène ;
#   · le CCTP de Marseille porte le SIRET D'UN AUTRE ACHETEUR et un chiffre
#     d'affaires exigé. C'est le document qui, s'il passait, ferait exactement
#     ce que je redoutais — et il est rangé HORS de la famille du cabinet.
SIRET_MAISON = "908 123 456 00017"
SIRET_AUTRE_ACHETEUR = "200 054 807 00012"

FONDS = [
    {"title": "Kbis CONSEILPREV 2026.pdf",
     "theme": "Cabinet / Identité & existence légale",
     "visibility": "interne",
     "content": "Extrait Kbis. CONSEILPREV SAS, SIREN 908 123 456, "
                "SIRET %s, capital social 15 000 euros, siege social "
                "12 rue de la Paix 75002 Paris." % SIRET_MAISON},
    {"title": "Bilan 2025 CONSEILPREV.pdf",
     "theme": "Cabinet / Comptes, bilans & chiffre d'affaires",
     "visibility": "interne",
     "content": "Chiffre d affaires hors taxes de l exercice 2025 : "
                "412 000 euros. Effectif moyen : 4 salaries."},
    {"title": "CCTP data center Marseille (autre marche).pdf",
     "theme": "Data center / Appels d'offres & CCTP",
     "visibility": "public",
     "content": "Le pouvoir adjudicateur, METROPOLE AIX MARSEILLE, "
                "SIRET %s, exige un chiffre d affaires de 3 000 000 euros."
                % SIRET_AUTRE_ACHETEUR},
]


class Magasin(object):
    """Il RETIENT ce qu'on lui demande — c'est ce qui rend les règles mesurantes.

    Un magasin qui se contente de répondre laisserait indémontrable la
    propriété la plus importante : qu'une cible du côté acheteur ne
    l'interroge JAMAIS. Ici, l'absence d'appel est une donnée.
    """

    def __init__(self, base=None):
        self.base = list(base if base is not None else FONDS)
        self.appels = []

    def search(self, query, k=5, public_only=True, theme=None, doc_ids=None):
        self.appels.append({"query": query, "k": k,
                            "public_only": public_only, "theme": theme})
        themes = ({theme} if isinstance(theme, str)
                  else set(theme) if theme else None)
        out = []
        for d in self.base:
            if themes is not None and d["theme"] not in themes:
                continue
            if public_only and d.get("visibility") != "public":
                continue
            out.append(dict(d))
        return out[:k]


RC = ("REGLEMENT DE LA CONSULTATION\n"
      "Pouvoir adjudicateur : VILLE DE PARIS, SIRET 217 500 016 00019.\n"
      "Objet : construction d un centre de donnees.\n"
      "Les candidats produiront le DC1, le DC2, une attestation d assurance.\n"
      "Criteres : prix 40 %, valeur technique 60 %.\n")


def _dossier():
    """Un dossier SANS AUCUN document du cabinet déposé — le cas qui compte.

    C'est là que le fonds se mesure : quand on a déposé ses pièces du matin,
    il n'ajoute qu'un peu ; quand on n'en a déposé aucune, il fait la
    différence entre « sept pièces non lues » et « sept pièces lues ».
    """
    docs = [{"nom": "RC.pdf", "extension": "pdf", "cote": "consultation",
             "texte": RC}]
    analyse = A.analyser(docs)
    return docs, analyse, A.remplir(fiche={}, analyse=analyse)


def _lues(rag):
    """Les pièces que `lire_le_dossier` a RÉELLEMENT envoyées au modèle.

    ON PASSE PAR LA VRAIE FONCTION, ET C'EST LA BATTERIE QUI L'A EXIGÉ. Une
    première version refaisait ici, à la main, ce que `lire_le_dossier` fait —
    `corpus_du_cote` puis `avec_le_fonds`. La mutation qui RETIRAIT la fusion
    de `lire_le_dossier` survivait donc à cette règle : la règle mesurait ses
    propres ingrédients, pas le plat. C'est exactement le défaut que ce
    fichier prétend chasser, écrit par moi, dans le fichier qui le chasse.
    """
    docs, analyse, rempl = _dossier()
    lu = X.lire_le_dossier(rempl, docs, analyse, rag=rag,
                           client=_client_qui_rend_rien())
    return lu


def _cible(cote="cabinet"):
    return {"cle": "dc2", "nom": "DC2", "corpus_cote": cote,
            "rubriques": [{"cle": "siret", "libelle": "SIRET du candidat",
                           "aide": ""},
                          {"cle": "ca1", "libelle": "chiffre d affaires",
                           "aide": ""}]}


# ═══════════════════════════════════════════════════════════════════════════
#  LE VOCABULAIRE : une famille nommée, et pas une devinette
# ═══════════════════════════════════════════════════════════════════════════

def test_la_famille_du_cabinet_est_declaree_et_ses_themes_sont_du_vocabulaire():
    """Une famille dont les thèmes ne sont pas dans THEMES est inatteignable.

    `set_theme` valide contre `THEMES` : un thème présent dans la famille mais
    absent du vocabulaire à plat serait proposé par la console d'un côté et
    refusé de l'autre. La famille se range donc dans la même table que les
    autres, et cette règle le vérifie plutôt que de l'espérer.
    """
    themes = R.themes_famille(R.FAMILLE_CABINET)
    assert themes, "la famille du cabinet ne porte aucun thème"
    manquants = [t for t in themes if t not in R.THEMES]
    assert not manquants, "thèmes hors vocabulaire : %s" % manquants

    # LES QUATRE QU'AUCUNE CONSULTATION FRANÇAISE NE DISPENSE, et la raison
    # pour laquelle on ne se contente pas de compter les thèmes. Identité,
    # assurance, régularité fiscale et sociale, capacité financière : ce sont
    # les quatre pièces que TOUT acheteur demande. Si l'une n'a pas de thème,
    # le document correspondant n'a nulle part où être rangé — donc il n'est
    # jamais lu, et la rubrique reste à saisir sans que rien ne le dise.
    #
    # LA BATTERIE A EXIGÉ CETTE RÈGLE-CI. La version d'avant se contentait de
    # `len(themes) >= 5` : la mutation qui retirait un thème de la famille
    # passait tranquillement, parce que neuf sont encore plus que cinq.
    indispensables = {
        "identité": ("identit", "légale"),
        "assurances": ("assurance",),
        "régularité fiscale et sociale": ("fiscale", "sociale"),
        "capacité financière": ("bilan", "comptes", "affaires"),
    }
    bas = [t.lower() for t in themes]
    absents = [quoi for quoi, mots in indispensables.items()
               if not any(m in t for t in bas for m in mots)]
    assert not absents, (
        "aucun thème n'accueille : %s — les documents correspondants "
        "resteront hors de portée du remplissage" % ", ".join(absents))


def test_la_famille_du_cabinet_ne_recycle_aucun_theme_d_une_autre_famille():
    """Un thème partagé rendrait la borne poreuse.

    Si « Data center / Appels d'offres & CCTP » figurait dans les deux
    familles, la recherche bornée au cabinet ramènerait les CCTP des autres
    marchés — et toutes les règles ci-dessous passeraient quand même, parce
    qu'elles interrogent la famille, pas la table.
    """
    cab = set(R.themes_famille(R.FAMILLE_CABINET))
    autres = set(t for f, ts in R.THEME_FAMILLES if f != R.FAMILLE_CABINET
                 for t in ts)
    assert not (cab & autres), "thèmes partagés : %s" % sorted(cab & autres)


def test_la_console_PROPOSE_la_famille_du_cabinet():
    """Une famille où personne ne peut ranger un document ne sert à rien.

    C'EST LE MÊME DÉFAUT QU'AILLEURS, DÉPLACÉ D'UN CRAN. Tout ce qui précède
    peut être vert — la famille déclarée, la recherche bornée, le fonds
    branché — et l'apport rester nul, parce que la console n'offre nulle part
    où ranger le Kbis. Le rangement est un geste humain : s'il n'est pas
    proposé, il n'a pas lieu.

    DEUX CHOSES SE MESURENT ICI. Que la route de vocabulaire transmette la
    famille, et que la page ne l'ÉCARTE pas : deux familles le sont — les
    entreprises et Engineering ont leur propre bloc de chargement — et la
    page ne rend en liste générale que ce qui n'est ni l'une ni l'autre.
    """
    import app as APP

    voc = APP._familles_payload()
    noms = [g["nom"] for g in voc["groupes"]]
    assert R.FAMILLE_CABINET in noms, noms

    themes = dict((g["nom"], g["themes"]) for g in voc["groupes"])
    assert set(themes[R.FAMILLE_CABINET]) == set(
        R.themes_famille(R.FAMILLE_CABINET))

    # Les deux familles que la page écarte de la liste générale.
    assert voc["entreprises"] != R.FAMILLE_CABINET
    assert voc["engineering"] != R.FAMILLE_CABINET


# ═══════════════════════════════════════════════════════════════════════════
#  L'APPORT — ce que le branchement change, compté
# ═══════════════════════════════════════════════════════════════════════════

def test_le_fonds_APPORTE_des_pieces_la_ou_aucun_document_cabinet_n_est_depose():
    """LA RÈGLE QUI MESURE L'EFFET, et la seule qui tombe si le fonds n'entre pas.

    Sans magasin, une cible du côté cabinet n'a aucun corpus : `lire_le_dossier`
    la traite en non-lieu et ne la lit pas. Avec le fonds, elle est lue.

    ON COMPTE LES RUBRIQUES, PAS LES BRANCHEMENTS. Une règle qui vérifierait
    que `rag` figure dans la signature serait verte avec un fonds qui
    n'apporte rien — exactement le défaut qu'on corrige ici.
    """
    docs, analyse, rempl = _dossier()
    toutes = X.cibles(rempl)
    par_cle = {c["cle"]: c for c in toutes}
    cote = {c["cle"]: c.get("corpus_cote") for c in toutes}

    sans = _lues(None)
    avec = _lues(Magasin())

    def compte(lu):
        cles = [p["cle"] for p in lu["pieces"]]
        return cles, sum(len(par_cle[k]["rubriques"]) for k in cles if k in par_cle)

    cles_sans, r_sans = compte(sans)
    cles_avec, r_avec = compte(avec)

    assert len(cles_avec) > len(cles_sans), (
        "le fonds n'ouvre aucune pièce de plus (%d puis %d)"
        % (len(cles_sans), len(cles_avec)))
    assert r_avec >= r_sans + 20, (
        "apport trop faible : %d rubriques cherchées sans le fonds, "
        "%d avec" % (r_sans, r_avec))
    # Et l'apport porte bien sur le CÔTÉ CABINET, pas sur un élargissement
    # général : aucune pièce du côté acheteur n'apparaît ou ne disparaît.
    cons_sans = {k for k in cles_sans if cote.get(k) != "cabinet"}
    cons_avec = {k for k in cles_avec if cote.get(k) != "cabinet"}
    assert cons_sans == cons_avec, (cons_sans, cons_avec)
    # Et le fonds est bien ce qui les a ouvertes.
    assert avec["corpus"]["fonds"] and not sans["corpus"]["fonds"]


def test_le_bilan_DIT_quels_documents_du_fonds_ont_ete_admis():
    """Un apport qu'on ne peut pas relire n'est pas un apport, c'est une rumeur.

    `lire_le_dossier` rend `corpus.fonds` : les titres RÉELLEMENT entrés dans
    un corpus de lecture. Sans cette liste, un fonds mal rangé — donc muet —
    serait indiscernable d'un fonds qui fonctionne.
    """
    docs, analyse, rempl = _dossier()
    lu = X.lire_le_dossier(rempl, docs, analyse, rag=Magasin(),
                           client=_client_muet())
    assert lu["corpus"]["fonds"], "le bilan ne nomme aucun document du fonds"
    assert "Kbis CONSEILPREV 2026.pdf" in lu["corpus"]["fonds"]
    # Et sans magasin, la clé existe quand même — vide. Une clé absente
    # forcerait chaque lecteur à écrire `.get("fonds") or []`, et le premier
    # qui l'oublierait tomberait.
    sec = X.lire_le_dossier(rempl, docs, analyse, client=_client_muet())
    assert sec["corpus"]["fonds"] == []


def _client_muet():
    """On mesure ici le CORPUS admis, pas ce que le modèle en tire."""
    return _client_qui_rend_rien()


# ═══════════════════════════════════════════════════════════════════════════
#  LES TROIS BORNES — et ce qui se passe quand on les retire
# ═══════════════════════════════════════════════════════════════════════════

def test_une_cible_du_cote_ACHETEUR_n_interroge_JAMAIS_le_fonds():
    """Le fonds ne sait rien de CE marché-ci ; ce qu'il en dirait vient d'un autre.

    Mesuré par l'ABSENCE D'APPEL, et non par un résultat vide : un magasin qui
    répondrait « rien » pour une autre raison rendrait la règle complaisante.
    """
    rag = Magasin()
    assert X.chercher_au_fonds(_cible(cote=None), rag) == []
    assert rag.appels == [], "le fonds a été interrogé du côté acheteur"


def test_le_fonds_ne_rend_QUE_la_famille_du_cabinet():
    """Le CCTP d'un AUTRE marché ne doit pas pouvoir entrer.

    C'est la crainte qui m'avait fait refuser le branchement, et elle était
    fondée : ce document porte le SIRET d'un autre acheteur ET un chiffre
    d'affaires. S'il entrait, il serait cité — donc accepté par le garde-fou,
    puisque sa citation serait exacte — et recopié dans notre DC2.
    """
    rag = Magasin()
    pieces = X.chercher_au_fonds(_cible(), rag)

    assert pieces, "le fonds ne rend rien du tout"
    fichiers = [p["fichier"] for p in pieces]
    assert not any("Marseille" in f for f in fichiers), fichiers

    texte = " ".join(p["texte"] for p in pieces)
    assert SIRET_AUTRE_ACHETEUR not in texte
    assert "3 000 000" not in texte
    assert SIRET_MAISON in texte, "le document de la maison n'est pas lu"

    # Et les thèmes demandés sont EXACTEMENT ceux de la famille : demander la
    # famille « et un peu plus » rouvrirait la porte en silence.
    assert set(rag.appels[0]["theme"]) == set(
        R.themes_famille(R.FAMILLE_CABINET))


def test_une_famille_vide_ne_vaut_PAS_toute_la_base():
    """Le repli dangereux : `theme=None` cherche PARTOUT.

    Si la famille disparaissait — renommée, retirée — un code qui passe
    `theme=themes` sans vérifier rendrait `theme=[]`, puis `theme=None` au
    magasin : la borne s'évaporerait sans un mot. On préfère ne rien lire, et
    cette règle mesure qu'AUCUNE recherche n'est lancée.
    """
    rag = Magasin()
    initial = R.themes_famille

    try:
        R.themes_famille = lambda nom: []
        assert X.chercher_au_fonds(_cible(), rag) == []
    finally:
        R.themes_famille = initial
    assert rag.appels == [], "une recherche non bornée a été lancée"


def test_le_fonds_lit_AUSSI_ce_qui_est_range_en_interne():
    """Sinon le branchement ne sert à rien, et la règle serait verte quand même.

    Un Kbis, un bilan, une attestation se rangent en INTERNE — c'est même la
    raison d'être du drapeau. `chercher_socle` impose `public_only=True` parce
    qu'un brouillon RECOPIE ses extraits et part chez l'acheteur. Ici rien ne
    part : on lit une valeur pour la reporter dans notre propre formulaire,
    derrière `@admin_required`. Exiger `public_only` aurait rendu illisibles
    exactement les documents visés.
    """
    rag = Magasin()
    pieces = X.chercher_au_fonds(_cible(), rag)
    assert rag.appels[0]["public_only"] is False
    internes = [d["title"] for d in FONDS if d["visibility"] == "interne"]
    lus = {p["fichier"] for p in pieces}
    assert set(internes) <= lus, (internes, lus)


def test_le_socle_de_REDACTION_reste_public_only():
    """L'inverse, et c'est délibéré : un brouillon sort du site.

    Les deux chemins lisent le même fonds et n'ont pas le même risque. Si l'un
    des deux dérivait vers l'autre, personne ne le verrait — d'où cette règle
    qui les mesure ensemble.
    """
    import ao_redaction as Q
    rag = Magasin()
    Q.chercher_socle({"cle": "memoire_technique", "nom": "Mémoire",
                      "rubriques": []}, rag)
    assert rag.appels, "la rédaction n'a pas interrogé le fonds"
    assert rag.appels[0]["public_only"] is True


# ═══════════════════════════════════════════════════════════════════════════
#  L'ORDRE, LA CITATION, LE PROMPT
# ═══════════════════════════════════════════════════════════════════════════

def test_ce_qui_a_ete_depose_ce_matin_passe_AVANT_ce_qui_dort_dans_la_base():
    """Deux Kbis, l'un déposé, l'autre au fonds : c'est le déposé qui commande.

    Le budget de texte se dépense dans l'ordre de lecture ; l'ordre est donc
    celui du risque. Un Kbis glissé dans la zone du cabinet ce matin est plus
    à jour que celui qui dort dans la base depuis deux ans.
    """
    depose = {"fichier": "Kbis.pdf", "sigle": "kbis", "texte": "frais",
              "rang": 500, "non_identifie": False, "cote": "cabinet"}
    corp = {"pieces": [depose], "octets": 5, "tronques": []}
    fondu = X.avec_le_fonds(corp, X.chercher_au_fonds(_cible(), Magasin()))

    rangs = [p["rang"] for p in fondu["pieces"]]
    assert rangs == sorted(rangs), rangs
    assert fondu["pieces"][0]["fichier"] == "Kbis.pdf"
    assert all(p["rang"] > 500 for p in fondu["pieces"] if p.get("fonds"))
    # Et les octets suivent : un corpus dont la taille annoncée ignore le
    # fonds ferait mentir le bilan sur ce qui a été donné à lire.
    assert fondu["octets"] == sum(len(p["texte"]) for p in fondu["pieces"])


def test_la_fusion_REFUSE_une_piece_qui_ne_dit_pas_le_cote_cabinet():
    """Le `cote` d'une pièce du fonds doit PORTER quelque chose.

    LA BATTERIE A ÉCRIT CETTE RÈGLE. Tant que rien ne lisait ce champ, on
    pouvait le mettre à « consultation » sans qu'aucune règle bronche : il
    était décoratif, et un champ décoratif ment le jour où un appelant change.
    La borne du côté vit dans `chercher_au_fonds` ; `avec_le_fonds` la
    revérifie sur ce qu'on lui présente, et c'est ce second verrou qu'on
    mesure ici.
    """
    vraies = X.chercher_au_fonds(_cible(), Magasin())
    assert vraies, "le fonds ne rend rien — la règle ne mesurerait rien"

    vide = {"pieces": [], "octets": 0, "tronques": []}
    assert X.avec_le_fonds(vide, vraies)["pieces"], "les vraies sont refusées"

    for faussee in ([dict(p, cote="consultation") for p in vraies],
                    [dict(p, fonds=False) for p in vraies]):
        assert X.avec_le_fonds(vide, faussee)["pieces"] == [], faussee[0]


def test_une_valeur_lue_au_fonds_reste_soumise_a_la_CITATION():
    """Le garde-fou ne connaît pas la provenance, et c'est ce qu'on vérifie.

    Le fonds n'achète aucune dispense : une valeur dont la citation ne se
    retrouve pas mot pour mot dans le corpus est rejetée, qu'elle vienne d'un
    document déposé ou de la base.
    """
    corp = X.avec_le_fonds({"pieces": [], "octets": 0, "tronques": []},
                           X.chercher_au_fonds(_cible(), Magasin()))
    vraie = "SIRET %s, capital social 15 000 euros" % SIRET_MAISON
    assert X.verifier_citation(vraie, corp), "une citation exacte est rejetée"
    assert X.verifier_citation(
        "SIRET 111 222 333 00044, capital social 90 000 euros", corp) is None


def test_le_prompt_NOMME_le_fonds_et_cesse_de_dire_acheteur():
    """Deux correctifs dans la même phrase, et ils se mesurent sur le texte rendu.

    L'en-tête disait « Pièces déposées par l'acheteur » pour TOUTES les
    cibles — donc aussi pour celles où l'on ne donne à lire que NOS documents.
    Et rien ne distinguait un document du fonds d'une pièce déposée ce matin.
    """
    corp = X.avec_le_fonds({"pieces": [], "octets": 0, "tronques": []},
                           X.chercher_au_fonds(_cible(), Magasin()))
    texte = X.demande(_cible(), corp)
    assert "Documents du cabinet" in texte
    assert "déposées par l'acheteur" not in texte
    assert "BASE DE CONNAISSANCE DU CABINET" in texte

    # Et du côté acheteur, l'en-tête d'origine reste — c'est là qu'il est vrai.
    cote_acheteur = X.demande(_cible(cote=None),
                              {"pieces": [{"fichier": "RC.pdf", "sigle": "RC",
                                           "texte": RC}]})
    assert "déposées par l'acheteur" in cote_acheteur
    assert "BASE DE CONNAISSANCE" not in cote_acheteur


# ═══════════════════════════════════════════════════════════════════════════
#  LE FIL COMPLET — de la route jusqu'à la recherche
# ═══════════════════════════════════════════════════════════════════════════

def test_le_magasin_DESCEND_de_l_atelier_jusqu_a_la_lecture():
    """Il n'y descendait pas, et c'était tout le défaut.

    `atelier(rag=...)` le passait à la RÉDACTION seule. Mesuré en exécutant
    l'atelier — pas en lisant sa source : un `rag=rag` écrit et jamais
    parcouru rendrait une règle syntaxique verte.
    """
    docs, analyse, _ = _dossier()
    rag = Magasin()
    T.atelier(fiche={}, documents=docs, analyse=analyse, rag=rag,
              rediger=False, tours_max=1,
              client_extraction=_client_qui_rend_rien())
    assert rag.appels, "l'atelier n'a jamais interrogé le fonds pour remplir"
    assert all(set(a["theme"]) == set(R.themes_famille(R.FAMILLE_CABINET))
               for a in rag.appels)


def _client_qui_rend_rien():
    """Un faux SDK qui ne propose RIEN — le fil se déroule sans clé ni réseau.

    Même forme que celui de `test_ao_extraction` : un module portant
    `Anthropic`, parce que c'est ce que `extraire` construit.
    """
    class _Bloc(object):
        type = "tool_use"
        name = X.OUTIL
        input = {"rubriques": []}

    class _Rep(object):
        content = [_Bloc()]
        usage = None
        model = "faux"

    class _Msg(object):
        appels = 0

        @staticmethod
        def create(**kw):
            _Msg.appels += 1
            return _Rep()

    class _Anthropic(object):
        def __init__(self, *a, **k):
            self.messages = _Msg()

    m = types.ModuleType("anthropic")
    m.Anthropic = _Anthropic
    m.compteur = _Msg
    return m


def test_l_atelier_FAIT_REMONTER_ce_que_le_fonds_a_apporte():
    """`lire_le_dossier` le dit, `atelier` doit le transmettre, la page l'affiche.

    Un maillon muet au milieu suffit à rendre l'apport invisible : l'écran
    dirait « 12 rubriques remplies » sans jamais dire d'où. On exécute
    l'atelier, et on lit ce qu'il rend.
    """
    docs, analyse, _ = _dossier()
    avec = T.atelier(fiche={}, documents=docs, analyse=analyse, rag=Magasin(),
                     rediger=False, tours_max=1,
                     client_extraction=_client_qui_rend_rien())
    sans = T.atelier(fiche={}, documents=docs, analyse=analyse,
                     rediger=False, tours_max=1,
                     client_extraction=_client_qui_rend_rien())
    assert "Kbis CONSEILPREV 2026.pdf" in avec["fonds"]
    assert sans["fonds"] == []


def test_la_page_NOMME_les_documents_du_fonds_et_dit_quoi_faire_sinon():
    """Exécutée sous node, pas relue : un `if` mort passerait une règle lue.

    DEUX CAS, ET LE SECOND COMPTE AUTANT. Quand le fonds a servi, on nomme les
    documents. Quand il n'a rien donné, on dit POURQUOI et où ranger les
    pièces — sinon l'opérateur cherche le défaut dans le moteur alors que le
    Kbis est simplement rangé sous « Général ».
    """
    import json
    import subprocess

    src = _js_source("esc", "atelierBilan")
    pont = """
    var DOC = {ecrits: []};
    var document = {
      getElementById: function (id) {
        return {set innerHTML(v) { DOC.ecrits.push(v); }, hidden: true};
      },
      querySelectorAll: function () { return []; },
      querySelector: function () { return null; }
    };
    var AO_REMPLI = null, AO_ANALYSE = null, AO_CHOIX_FAIT = true;
    function aoRempliRendre() {}
    function aoToutChoisir() {}
    function aoRedigerRendre() {}
    %s
    var sorties = [];
    [ {remplies: 1, rubriques: 2, fonds: ["Kbis CONSEILPREV.pdf"]},
      {remplies: 1, rubriques: 2, fonds: []} ].forEach(function (j) {
        DOC.ecrits = [];
        atelierBilan(j);
        sorties.push(DOC.ecrits.join(""));
    });
    console.log(JSON.stringify(sorties));
    """ % src

    out = subprocess.check_output(["/opt/node22/bin/node", "-e", pont],
                                  stderr=subprocess.STDOUT).decode("utf-8")
    avec, sans = json.loads(out.strip().splitlines()[-1])

    assert "Kbis CONSEILPREV.pdf" in avec
    assert "base de connaissance" in avec.lower()

    # Le cas vide ne NOMME aucun document — il n'y en a aucun — mais il dit
    # où ranger les pièces pour que la prochaine fois en nomme.
    assert "Kbis CONSEILPREV.pdf" not in sans
    assert "pièces du cabinet" in sans, sans
    assert "rang" in sans.lower(), sans


def _js_source(*noms):
    """Les fonctions demandées, extraites de la source SERVIE, par comptage
    d'accolades — recopier leur corps ici éprouverait un script imaginaire."""
    import io as _io
    src = _io.open(os.path.join(ICI, "ingenierie-dc.js"), encoding="utf-8").read()
    out = []
    for nom in noms:
        i = src.index("\n  function %s(" % nom) + 1
        p, k = 1, src.index("{", i) + 1
        while p:
            p += 1 if src[k] == "{" else (-1 if src[k] == "}" else 0)
            k += 1
        out.append(src[i:k])
    return "\n".join(out)


def test_sans_magasin_le_remplissage_est_EXACTEMENT_celui_d_avant():
    """La non-régression : le fonds est un APPORT, jamais une dépendance.

    Une base injoignable, un magasin non joint, une famille vide : dans les
    trois cas le dossier doit se remplir avec ce qui a été déposé, comme
    avant le 15 septembre 2026.
    """
    docs, analyse, rempl = _dossier()
    temoin = X.lire_le_dossier(rempl, docs, analyse, client=_client_qui_rend_rien())

    class Casse(Magasin):
        def search(self, *a, **k):
            raise RuntimeError("base injoignable")

    panne = X.lire_le_dossier(rempl, docs, analyse, rag=Casse(),
                              client=_client_qui_rend_rien())
    assert panne["echecs"] == temoin["echecs"] == []
    assert panne["corpus"]["fonds"] == []
    assert len(panne["pieces"]) == len(temoin["pieces"])


@pytest.mark.parametrize("cote", [None, "consultation", "acheteur", ""])
def test_seul_le_mot_cabinet_ouvre_le_fonds(cote):
    """Aucune valeur voisine ne doit ouvrir la porte par inadvertance.

    `corpus_du_cote` retombe sur « tout le corpus » pour une valeur fausse ;
    si `chercher_au_fonds` faisait le même repli, une faute de frappe dans un
    appelant donnerait le fonds à une cible du côté acheteur.
    """
    rag = Magasin()
    assert X.chercher_au_fonds(_cible(cote=cote), rag) == []
    assert rag.appels == []
