# -*- coding: utf-8 -*-
"""La lecture assistée du dossier : ce qu'elle remplit, et ce qu'elle REFUSE.

POURQUOI CE FICHIER EXISTE. Le relevé par motifs de `ao_dc` cherche dix-sept
points ; le report en attend quatre-vingt-treize. Les rubriques restantes
sortaient « à saisir » **par construction** — aucune extraction ne les visait.
Ce module les vise. Mesuré le 13 septembre sur une consultation réaliste :
30 rubriques sans aucun chemin de recherche.

CE QUE CES RÈGLES MESURENT EN PREMIER, ET C'EST LE POINT DU FICHIER : le
REFUS. Un remplissage automatique ne meurt pas d'une case vide — il meurt
d'une case remplie faux et signée. La règle centrale fait donc mentir le
modèle : elle lui fait rendre une valeur plausible accompagnée d'un passage
qui n'existe dans aucune pièce, et exige que RIEN n'entre. Une règle qui se
contenterait de vérifier qu'un modèle honnête remplit serait verte pendant que
la porte reste ouverte.

LE CLIENT ET L'EXÉCUTEUR SONT INJECTÉS. Aucune règle d'ici n'a besoin de clé,
de réseau ni de fil d'exécution : ce qui est mesuré est le RÉSULTAT, jamais
l'ordonnancement.
"""
import collections
import types

import pytest

import ao_dc as D
import ao_extraction as X


RC = u"""REGLEMENT DE CONSULTATION
Pouvoir adjudicateur : SYNDICAT MIXTE NUMERIQUE DE L'EURE, 14 boulevard Georges Chauvin, 27000 Evreux.
Objet du marche : conception-realisation d'un centre de donnees de 2,5 MW IT, Tier III.
Procedure : appel d'offres ouvert. Allotissement : lot 1 genie civil ; lot 2 courants forts.
Remise des offres : le 14 novembre 2026 a 12h00, sur la plateforme PLACE.
Duree du marche : 30 mois. Variantes autorisees. Criteres : valeur technique 60 %, prix 40 %.
Numero de la consultation : 2026-DC-014.
"""
CCTP = u"""CAHIER DES CLAUSES TECHNIQUES PARTICULIERES
Puissance IT : 2 500 kW. PUE cible annuel : 1,25. Redondance N+1 froid, 2N electrique.
Groupes electrogenes : autonomie 72 heures. Certification Uptime Institute Tier III.
"""
DOCS = [{"nom": "RC.pdf", "texte": RC}, {"nom": "CCTP.pdf", "texte": CCTP}]
FICHE = {"denomination": "CONSEILPREV", "siret": "91000000000015"}

# Un passage RÉEL du règlement, recopié caractère pour caractère.
VRAI = "Remise des offres : le 14 novembre 2026 a 12h00, sur la plateforme PLACE."


def _analyse():
    return D.analyser(DOCS)


def _remplissage(extraits=None):
    return D.remplir(fiche=FICHE, analyse=_analyse(), extraits=extraits)


def _corpus():
    return X.corpus(DOCS, _analyse())


def _compte(r):
    return collections.Counter(x["statut"] for p in r["pieces"]
                               for x in (p.get("rubriques") or []))


def _faux_client(propositions):
    """Un faux SDK qui rend ce qu'on lui dit, sans clé ni réseau.

    `propositions` reçoit les arguments de l'appel — le schéma d'outil compris
    — pour qu'une règle puisse répondre AVEC les clés que le schéma offre, au
    lieu de les recopier et de diverger le jour où elles changent."""
    class _Bloc:
        type = "tool_use"
        name = X.OUTIL

        def __init__(self, d):
            self.input = d

    class _Rep:
        def __init__(self, d):
            self.content = [_Bloc(d)]
            self.usage = None
            self.model = "faux"

    class _Msg:
        dernier_appel = {}

        @staticmethod
        def create(**kw):
            _Msg.dernier_appel = kw
            return _Rep({"rubriques": propositions(kw)})

    class _Anthropic:
        def __init__(self, *a, **k):
            self.messages = _Msg()

    m = types.ModuleType("anthropic")
    m.Anthropic = _Anthropic
    m.dernier = _Msg
    return m


def _cles_offertes(kw):
    return (kw["tools"][0]["input_schema"]["properties"]["rubriques"]
            ["items"]["properties"]["rubrique"]["enum"])


# ═══════════════════════════════════════════════════════════════════════════
#  CE QU'ON CHERCHE — et surtout ce qu'on ne cherche PAS
# ═══════════════════════════════════════════════════════════════════════════

def test_on_ne_recherche_QUE_ce_qui_reste_a_trouver():
    r = _remplissage()
    vises = {(c["cle"], x["cle"]) for c in X.cibles(r) for x in c["rubriques"]}
    assert vises, "aucune rubrique visée : l'extraction n'a rien à faire"
    for p in r["pieces"]:
        for x in (p.get("rubriques") or []):
            if (p["cle"], x["cle"]) in vises:
                assert x["source"] in X.SOURCES_CIBLES
                assert x["statut"] in X.STATUTS_CIBLES


def test_une_DECLARATION_sur_l_honneur_n_est_JAMAIS_recherchee():
    """LE POINT DE SÉCURITÉ. Pré-cocher une déclaration sur l'honneur, c'est
    signer à la place de quelqu'un. Aucune automatisation ne doit y toucher —
    et une règle doit l'interdire, pas l'espérer."""
    r = _remplissage()
    vises = {(c["cle"], x["cle"]) for c in X.cibles(r) for x in c["rubriques"]}
    declarations = {(p["cle"], x["cle"]) for p in r["pieces"]
                    for x in (p.get("rubriques") or [])
                    if x["source"] == "declaration"}
    assert declarations, "le montage ne contient aucune déclaration à protéger"
    assert not (vises & declarations)


def test_une_rubrique_de_la_FICHE_n_est_JAMAIS_cherchee_chez_l_ACHETEUR():
    """Le SIRET du candidat n'est pas dans le règlement de l'acheteur. L'y
    chercher ferait remonter le SIRET DE L'ACHETEUR — et il serait recopié.

    CETTE RÈGLE A CHANGÉ DE FORME, PAS DE RAISON. Elle interdisait de
    CHERCHER une rubrique de la fiche, tout court — la seule protection
    possible quand le dépôt ne connaissait qu'un côté. Depuis qu'il en a deux,
    ces rubriques se cherchent, mais UNIQUEMENT dans les documents que nous
    avons déposés : Kbis, bilans, attestations. Le règlement de l'acheteur
    n'entre pas dans ce corpus-là.

    POURQUOI LE GARDE-FOU HABITUEL NE SUFFISAIT PAS ICI. Toute valeur extraite
    doit être CITÉE dans un document déposé, sans quoi elle est rejetée. Le
    SIRET de l'acheteur, lui, EST cité — noir sur blanc, dans son propre
    règlement. La citation existe, elle est exacte, et la valeur est fausse.
    Seul le cloisonnement des corpus protège de ce défaut-là.
    """
    r = _remplissage()
    fiches = {(p["cle"], x["cle"]) for p in r["pieces"]
              for x in (p.get("rubriques") or []) if x["source"] == "fiche"}
    assert fiches
    vus = {}
    for c in X.cibles(r):
        for x in c["rubriques"]:
            vus.setdefault((c["cle"], x["cle"]), set()).add(c.get("corpus_cote"))
    for cle in fiches & set(vus):
        assert vus[cle] == {"cabinet"}, (
            "%s est cherchée hors des documents du cabinet (%r) : le SIRET de "
            "l'acheteur redevient atteignable" % (cle, vus[cle]))
    # ET LE TÉMOIN : elles sont bien cherchées. Une règle qui n'en verrait
    # aucune serait verte en ne protégeant plus rien.
    assert fiches & set(vus), (
        "aucune rubrique de la fiche n'est cherchée : la règle est vide")


def test_le_corpus_du_cabinet_EXCLUT_les_pieces_de_l_acheteur():
    """La contrainte, mesurée sur le corpus lui-même et pas sur l'intention.

    C'EST LE POINT OÙ LE DÉFAUT SE PRODUIRAIT. Si `corpus_du_cote` rendait le
    corpus entier faute de documents du cabinet — le repli « commode » —, la
    recherche du SIRET du candidat repartirait dans le règlement de
    l'acheteur, et la protection serait annulée exactement quand elle est le
    plus nécessaire : quand nous n'avons rien déposé.
    """
    an = {"pieces": [{"fichier": "01_RC.pdf", "rang_lecture": 1, "sigle": "RC"}],
          "pieces_cabinet": [{"fichier": "KBIS.pdf", "cle": "extrait_kbis"}]}
    docs = [{"nom": "01_RC.pdf", "texte": "SIRET de l'acheteur 21750001600019."},
            {"nom": "KBIS.pdf", "texte": "CONSEILPREV, SIRET 49453015700038."}]
    corp = X.corpus(docs, an)
    vu = X.corpus_du_cote(corp, "cabinet")
    assert [x["fichier"] for x in vu["pieces"]] == ["KBIS.pdf"], vu["pieces"]
    assert "21750001600019" not in " ".join(x["texte"] for x in vu["pieces"])
    # SANS AUCUN DOCUMENT DU CABINET, LE CORPUS EST VIDE — pas entier.
    vide = X.corpus_du_cote(X.corpus(docs[:1], {"pieces": an["pieces"]}),
                            "cabinet")
    assert vide["pieces"] == [], vide["pieces"]
    # ET SANS CÔTÉ DEMANDÉ, RIEN N'EST RETIRÉ : le reste cherche partout.
    assert len(X.corpus_du_cote(corp, None)["pieces"]) == 2


def test_une_rubrique_DEJA_remplie_n_est_pas_remise_en_jeu():
    r = _remplissage()
    vises = {(c["cle"], x["cle"]) for c in X.cibles(r) for x in c["rubriques"]}
    remplies = {(p["cle"], x["cle"]) for p in r["pieces"]
                for x in (p.get("rubriques") or []) if x["statut"] == "rempli"}
    assert remplies
    assert not (vises & remplies)


# ═══════════════════════════════════════════════════════════════════════════
#  LA CITATION SE VÉRIFIE — le cœur du fichier
# ═══════════════════════════════════════════════════════════════════════════

def test_une_citation_INVENTEE_fait_rejeter_la_valeur_ENTIERE():
    """LA RÈGLE CENTRALE. Le modèle rend une valeur parfaitement plausible avec
    un passage qui n'existe dans aucune pièce. Rien ne doit entrer — ni en
    « à confirmer », ni en gris, ni nulle part."""
    def ment(kw):
        return [{"rubrique": c, "valeur": "3 mars 2027",
                 "citation": "Les offres sont remises au plus tard le 3 mars "
                             "2027 a midi selon le present reglement."}
                for c in _cles_offertes(kw)[:2]]

    avant = _compte(_remplissage())
    res = X.lire_le_dossier(_remplissage(), DOCS, _analyse(),
                            client=_faux_client(ment))
    assert res["extraits"] == {}, "une valeur au passage inventé est passée"
    assert res["rejets"], "le rejet n'est même pas signalé"
    assert all(x["motif"] == "citation_introuvable" for x in res["rejets"])
    apres = _compte(_remplissage(res["extraits"]))
    assert apres["rempli"] == avant["rempli"]


def test_une_citation_REELLE_est_retenue_ET_situee_dans_le_document():
    def honnete(kw):
        return [{"rubrique": _cles_offertes(kw)[0],
                 "valeur": "14 novembre 2026 à 12h00", "citation": VRAI}]

    res = X.lire_le_dossier(_remplissage(), DOCS, _analyse(),
                            client=_faux_client(honnete))
    assert res["extraits"], "un passage réel a été rejeté"
    e = list(res["extraits"].values())[0]
    assert e["fichier"] == "RC.pdf"
    assert e["sigle"] == "RC"
    assert 0 <= e["part"] <= 100


def test_une_valeur_SANS_citation_est_rejetee_et_le_MOTIF_le_dit():
    """Une valeur nue n'est pas « moins sûre » : elle est irrecevable. Et le
    motif du rejet doit la distinguer d'un passage introuvable — les deux ne
    disent pas la même chose du modèle."""
    def nue(kw):
        return [{"rubrique": _cles_offertes(kw)[0], "valeur": "14 novembre 2026",
                 "citation": ""}]

    res = X.lire_le_dossier(_remplissage(), DOCS, _analyse(),
                            client=_faux_client(nue))
    assert res["extraits"] == {}
    assert any(x["motif"] == "sans_citation" for x in res["rejets"]), \
        "une valeur sans passage est rejetée sous un motif qui ment"


def test_une_citation_TROP_COURTE_ne_prouve_RIEN():
    """« 2026 » se retrouve dans n'importe quel dossier. Accepter un fragment
    de quelques signes reviendrait à ne rien vérifier du tout."""
    corp = _corpus()
    assert X.verifier_citation("2026", corp) is None
    assert X.verifier_citation("Remise des offres", corp) is None
    assert X.verifier_citation(VRAI, corp) is not None


def test_la_citation_tolere_les_BLANCS_et_la_CASSE_mais_PAS_la_reformulation():
    """La frontière exacte de la tolérance, mesurée des DEUX côtés. Un lecteur
    de PDF recompose les blancs et coupe les lignes ; il ne réécrit pas les
    phrases."""
    corp = _corpus()
    recompose = VRAI.upper().replace(" ", "   \n ")
    assert X.verifier_citation(recompose, corp) is not None, \
        "une citation honnête, seulement remise en forme, est rejetée"
    reformule = "Les offres doivent etre remises le 14 novembre 2026 avant midi."
    assert X.verifier_citation(reformule, corp) is None, \
        "une citation REFORMULÉE passe : la vérification ne vérifie rien"


def test_une_rubrique_HORS_CIBLE_est_rejetee():
    """Le modèle ne remplit pas ce qu'on ne lui a pas demandé — notamment pas
    une rubrique qu'une saisie humaine occupe déjà."""
    def deborde(kw):
        return [{"rubrique": "rubrique_qui_n_existe_pas",
                 "valeur": "peu importe", "citation": VRAI}]

    res = X.lire_le_dossier(_remplissage(), DOCS, _analyse(),
                            client=_faux_client(deborde))
    assert res["extraits"] == {}
    assert any(x["motif"] == "hors_cible" for x in res["rejets"])


def test_le_schema_de_l_outil_n_offre_QUE_les_rubriques_de_la_piece():
    r = _remplissage()
    for c in X.cibles(r):
        enum = (X._outil(c)["input_schema"]["properties"]["rubriques"]
                ["items"]["properties"]["rubrique"]["enum"])
        assert set(enum) == {x["cle"] for x in c["rubriques"]}


# ═══════════════════════════════════════════════════════════════════════════
#  CE QUI ENTRE DANS LE REPORT, ET COMMENT IL EST MARQUÉ
# ═══════════════════════════════════════════════════════════════════════════

def _extrait_pour(r, statut_voulu="a_saisir", source="saisie"):
    for p in r["pieces"]:
        for x in (p.get("rubriques") or []):
            if x["source"] == source and x["statut"] == statut_voulu:
                return "%s.%s" % (p["cle"], x["cle"]), p["cle"], x["cle"]
    raise AssertionError("aucune rubrique %s/%s dans le montage" % (source, statut_voulu))


def test_une_valeur_lue_est_marquee_A_CONFIRMER_et_porte_son_ORIGINE():
    r0 = _remplissage()
    k, pc, rc = _extrait_pour(r0)
    ext = {k: {"valeur": "14 novembre 2026", "citation": VRAI,
               "fichier": "RC.pdf", "sigle": "RC", "part": 42,
               "non_identifie": False}}
    r1 = _remplissage(ext)
    ligne = next(x for p in r1["pieces"] if p["cle"] == pc
                 for x in p["rubriques"] if x["cle"] == rc)
    assert ligne["statut"] == "rempli"
    assert ligne["valeur"] == "14 novembre 2026"
    assert ligne.get("a_confirmer") is True, \
        "une valeur LUE est présentée comme une valeur sûre"
    assert "LECTURE ASSISTÉE" in (ligne["origine"] or "")
    assert "RC" in (ligne["origine"] or "")
    assert (ligne.get("citation") or {}).get("texte") == VRAI


def test_ce_qui_est_LU_n_ECRASE_JAMAIS_une_saisie_humaine():
    """Une personne qui a corrigé une valeur l'a fait parce que la lecture
    s'était trompée. La relancer à chaque tour l'écraserait sans fin."""
    r0 = _remplissage()
    k, pc, rc = _extrait_pour(r0)
    ext = {k: {"valeur": "LU", "citation": VRAI, "fichier": "RC.pdf",
               "sigle": "RC", "part": 10, "non_identifie": False}}
    r1 = D.remplir(fiche=FICHE, analyse=_analyse(),
                   saisies={k: "SAISI À LA MAIN"}, extraits=ext)
    ligne = next(x for p in r1["pieces"] if p["cle"] == pc
                 for x in p["rubriques"] if x["cle"] == rc)
    assert ligne["valeur"] == "SAISI À LA MAIN"
    assert "Saisi" in (ligne["origine"] or "")


def test_le_releve_par_MOTIFS_passe_avant_la_lecture_assistee():
    """Un motif qui a mordu est déterministe et rejouable ; une lecture ne
    l'est pas. Inverser l'ordre ferait varier d'un tour à l'autre une valeur
    que le motif rendait stable."""
    r0 = _remplissage()
    ligne = next((x for p in r0["pieces"] for x in (p.get("rubriques") or [])
                  if x["source"] == "consultation" and x["statut"] == "rempli"), None)
    assert ligne is not None, "le montage n'a aucun relevé par motifs"
    piece = next(p for p in r0["pieces"]
                 if any(y is ligne for y in (p.get("rubriques") or [])))
    k = "%s.%s" % (piece["cle"], ligne["cle"])
    r1 = _remplissage({k: {"valeur": "VALEUR LUE", "citation": VRAI,
                           "fichier": "RC.pdf", "sigle": "RC", "part": 5,
                           "non_identifie": False}})
    apres = next(x for p in r1["pieces"] if p["cle"] == piece["cle"]
                 for x in p["rubriques"] if x["cle"] == ligne["cle"])
    assert apres["valeur"] == ligne["valeur"]
    assert "Relevé" in (apres["origine"] or "")


# ═══════════════════════════════════════════════════════════════════════════
#  L'ÉVENTAIL, LE CORPUS, ET CE QUI TOMBE
# ═══════════════════════════════════════════════════════════════════════════

def test_le_dossier_entier_remplit_MEME_si_une_piece_tombe():
    """Un atelier tout-ou-rien rendrait zéro rubrique parce qu'une pièce a
    dépassé le délai."""
    appels = {"n": 0}

    def capricieux(kw):
        appels["n"] += 1
        if appels["n"] == 1:
            raise X.ExtractionError("reseau", 502, "coupure simulée")
        return [{"rubrique": _cles_offertes(kw)[0],
                 "valeur": "14 novembre 2026", "citation": VRAI}]

    res = X.lire_le_dossier(_remplissage(), DOCS, _analyse(),
                            client=_faux_client(capricieux))
    assert res["echecs"], "l'échec n'est pas signalé"
    assert res["echecs"][0]["code"] == "reseau"
    assert res["extraits"], "une pièce tombée a emporté tout le dossier"


def test_l_eventail_rend_le_MEME_resultat_que_la_sequence():
    """L'exécuteur est injecté : ce qui est mesuré est le résultat, jamais
    l'ordonnancement."""
    def honnete(kw):
        return [{"rubrique": _cles_offertes(kw)[0],
                 "valeur": "14 novembre 2026", "citation": VRAI}]

    sequence = X.lire_le_dossier(_remplissage(), DOCS, _analyse(),
                                 client=_faux_client(honnete))
    inverse = X.lire_le_dossier(
        _remplissage(), DOCS, _analyse(), client=_faux_client(honnete),
        executeur=lambda f, xs: list(reversed([f(x) for x in reversed(list(xs))])))
    assert sequence["extraits"] == inverse["extraits"]


def test_le_corpus_respecte_l_ORDRE_DE_LECTURE():
    """Le règlement de consultation fait foi : il se lit en premier, et c'est
    lui qu'on garde si le budget de texte est atteint."""
    corp = _corpus()
    sigles = [p["sigle"] for p in corp["pieces"]]
    assert sigles[0] == "RC", "le RC n'est pas lu en premier : %s" % sigles


def test_ce_qui_est_TRONQUE_est_ANNONCE(monkeypatch):
    """Tronquer en silence ferait dire « non trouvé » à une rubrique dont la
    réponse était dans la partie qu'on n'a pas donnée à lire.

    LA RÈGLE MESURE LA TRONCATURE, PAS LE FICHIER SAUTÉ. Sa première version se
    contentait d'exiger que `tronques` ne soit pas vide — et il ne l'était
    jamais, parce que le SECOND document, entièrement sauté, s'y inscrivait de
    toute façon. La batterie l'a montré : M14 survivait. On exige désormais que
    la pièce effectivement COUPÉE y figure nommément."""
    monkeypatch.setattr(X, "CORPUS_MAX", 200)
    corp = X.corpus(DOCS, _analyse())
    assert corp["octets"] <= 200
    coupees = [p["fichier"] for p in corp["pieces"] if p.get("tronque")]
    assert coupees, "le montage ne coupe aucune pièce : la règle ne mesure rien"
    for f in coupees:
        assert f in corp["tronques"], \
            "%s a été coupé en silence" % f


def test_sans_dossier_depose_l_extraction_REFUSE_au_lieu_d_inventer():
    r = _remplissage()
    cible = X.cibles(r)[0]
    with pytest.raises(X.ExtractionError) as e:
        X.extraire(cible, {"pieces": []}, client=_faux_client(lambda kw: []))
    assert e.value.code == "sans_dossier"


# ═══════════════════════════════════════════════════════════════════════════
#  LA RÈGLE QUI MESURE L'APPORT, pas la présence du branchement
# ═══════════════════════════════════════════════════════════════════════════

def test_la_lecture_assistee_AUGMENTE_le_remplissage():
    """Une règle qui vérifierait que le module est appelé serait verte pendant
    qu'il ne rend rien. On compte les rubriques remplies AVANT et APRÈS."""
    def honnete(kw):
        return [{"rubrique": c, "valeur": "14 novembre 2026", "citation": VRAI}
                for c in _cles_offertes(kw)]

    avant = _compte(_remplissage())
    res = X.lire_le_dossier(_remplissage(), DOCS, _analyse(),
                            client=_faux_client(honnete))
    apres = _compte(_remplissage(res["extraits"]))
    assert len(res["extraits"]) >= 10, \
        "la lecture ne rend que %d rubriques" % len(res["extraits"])
    assert apres["rempli"] > avant["rempli"], \
        "le remplissage n'a pas bougé : %d → %d" % (avant["rempli"], apres["rempli"])
    assert apres["a_saisir"] < avant["a_saisir"]
