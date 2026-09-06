# -*- coding: utf-8 -*-
"""Ce que le dossier marché REMPLIT vraiment — mesuré sur des formulations,
jamais sur les motifs.

LE DÉFAUT QUE CE FICHIER CORRIGE, ET IL ÉTAIT SILENCIEUX. Un relevé sans
groupe de capture CITE le passage et n'en extrait rien : la case reste
« non relevée » sur un dossier qui la porte en toutes lettres. Le contrôle de
chargement de `ao_dc` interdit d'y brancher une rubrique — il l'a d'ailleurs
fait deux fois — mais il ne dit pas que le motif rate la formulation la plus
courante. C'est mesurable, et ce n'est mesurable que sur des phrases.

LES PHRASES CI-DESSOUS SONT DES FORMULATIONS DE RÈGLEMENT DE CONSULTATION ET
DE CCAP. Éprouver l'expression régulière sur la phrase qui a servi à l'écrire
ne prouve rien : on l'éprouve sur les variantes qu'on n'a pas en tête en
l'écrivant — « allotie en 3 lots », « comporte 3 lots », « décomposé en
5 lots », « n'est pas alloti ».

CE QUE LA MESURE A DONNÉ AVANT CORRECTION : sur quatre façons d'annoncer un
allotissement, UNE SEULE rendait une valeur. La date limite et le délai
d'exécution n'en rendaient AUCUNE — six motifs, zéro groupe de capture.
"""
import os
import re
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc as A                                                # noqa: E402

PAR_CLE = {r["cle"]: r for r in A.RELEVES}


def _valeur(cle, phrase):
    """La valeur que le relevé tire de CETTE phrase, ou None.

    ON PASSE PAR `_extraire`, la fonction qui sert en production, plutôt que
    par `re.search` : une règle qui referait le travail à côté mesurerait sa
    propre copie.
    """
    for c in A._extraire(phrase, PAR_CLE[cle]["motifs"], maxi=4):
        if c["valeur"]:
            return c["valeur"]
    return None


# ══════════════════════════════════════════════════════════════════════════
# 1. L'ALLOTISSEMENT — QUATRE FAÇONS DE LE DIRE, QUATRE QUI DOIVENT RENDRE
# ══════════════════════════════════════════════════════════════════════════

LOTS = {
    "La consultation est allotie en 3 lots.": "3 lots",
    "Le marché est alloti en 4 lots.": "4 lots",
    "Le marché comporte 3 lots.": "3 lots",
    "Le marché est décomposé en 5 lots.": "5 lots",
}


def test_les_quatre_facons_d_annoncer_un_allotissement_rendent_le_compte():
    """UNE SEULE SUR QUATRE RENDAIT QUELQUE CHOSE AVANT. Les trois autres
    tombaient sur un motif sans groupe de capture : le passage était cité, la
    case restait vide, et le DC1 partait sans lots."""
    for phrase, attendu in LOTS.items():
        assert _valeur("lots", phrase) == attendu, (
            "« %s » rend %r au lieu de %r"
            % (phrase, _valeur("lots", phrase), attendu))


def test_un_marche_NON_alloti_est_une_reponse_et_non_une_absence():
    """« Non relevé » enverrait chercher un allotissement qui n'existe pas —
    et ferait cocher au DC1 une case de lots sur un marché qui n'en a
    aucun."""
    for phrase in ("Marché non alloti.",
                   "Le présent marché n'est pas alloti.",
                   "Consultation sans allotissement."):
        v = _valeur("lots", phrase)
        assert v and "alloti" in v.lower(), (phrase, v)


def test_le_compte_de_lots_passe_AVANT_l_intitule_du_premier_lot():
    """L'ORDRE DES MOTIFS DÉCIDE DE LA VALEUR RETENUE. `_index_releves` garde
    la première citation qui porte une valeur : si l'intitulé du lot n° 1
    passait devant, le DC1 recevrait « conception » là où il faut « 3 lots » —
    une case pleine, plausible, et qui ne dit pas l'allotissement."""
    phrase = ("La consultation est allotie en 3 lots. "
              "Lot n° 1 : conception. Lot n° 2 : suivi de travaux.")
    assert _valeur("lots", phrase) == "3 lots", _valeur("lots", phrase)
    # ET L'INTITULÉ SEUL RESTE RELEVÉ quand aucun compte n'est donné : sans ce
    # témoin, on aurait pu supprimer le motif au lieu de le déplacer.
    assert _valeur("lots", "Lot n° 1 : conception.") == "conception"


# ══════════════════════════════════════════════════════════════════════════
# 2. LA DATE LIMITE ET LE DÉLAI — AUCUN MOTIF NE CAPTURAIT
# ══════════════════════════════════════════════════════════════════════════

DATES = {
    "Date limite de remise des offres : 30 octobre 2026 à 12 h 00.":
        "30 octobre 2026 à 12 h 00",
    "Date et heure limites de réception des plis : 12/11/2026 à 16h00.":
        "12/11/2026 à 16h00",
    "Les offres sont remises avant le 30 octobre 2026 à 12 h 00.":
        "30 octobre 2026 à 12 h 00",
    "Date limite : 30/10/2026.": "30/10/2026",
}

DELAIS = {
    "Délai d'exécution : 18 mois à compter de la notification.":
        "18 mois à compter de la notification",
    "Délai global d'exécution : 24 mois.": "24 mois",
    "Durée du marché : 4 ans, reconductible une fois.":
        "4 ans, reconductible une fois",
    "Le délai d'exécution est de 18 mois à compter de la notification.":
        "18 mois à compter de la notification",
    "La durée du marché est de 36 mois.": "36 mois",
    "Délai de réalisation : 52 semaines.": "52 semaines",
}


def test_la_date_limite_est_extraite_et_non_seulement_citee():
    """« Le seul élément qui rend tout le reste inutile s'il est manqué », dit
    la table elle-même — et il n'était pas extrait."""
    for phrase, attendu in DATES.items():
        assert _valeur("date_limite", phrase) == attendu, (
            phrase, _valeur("date_limite", phrase))


def test_le_delai_d_execution_est_extrait_et_non_seulement_cite():
    """C'est lui qui remplit la durée d'exécution de l'acte d'engagement.
    Sans capture, la case se ressaisissait à la main sur un CCAP qui l'écrit
    noir sur blanc."""
    for phrase, attendu in DELAIS.items():
        assert _valeur("delai", phrase) == attendu, (
            phrase, _valeur("delai", phrase))


def test_les_motifs_sans_capture_sont_GARDES_pour_la_citation():
    """ILS NE SONT PAS DU RÉSIDU. Quand la phrase ne se laisse pas découper,
    ils repèrent quand même le passage — et le rappel de consultation a besoin
    de la CITATION, pas de la valeur. Les supprimer ferait disparaître la date
    limite du rappel sur les dossiers rédigés sans deux-points."""
    for cle in ("date_limite", "delai"):
        motifs = PAR_CLE[cle]["motifs"]
        avec = [m for m in motifs if re.compile(m).groups]
        sans = [m for m in motifs if not re.compile(m).groups]
        assert avec and sans, (cle, len(avec), len(sans))
        # LES CAPTURANTS PASSENT DEVANT : sinon le motif large gagnerait et
        # rendrait la phrase entière au lieu de la valeur.
        assert motifs.index(avec[-1]) < motifs.index(sans[0]), cle
    cite = A._extraire("La date limite de dépôt figure au calendrier joint.",
                       PAR_CLE["date_limite"]["motifs"])
    assert cite and cite[0]["valeur"] is None, cite


# ══════════════════════════════════════════════════════════════════════════
# 3. LA RÉFÉRENCE — LE LIBELLÉ AVALAIT LA VALEUR
# ══════════════════════════════════════════════════════════════════════════

def test_la_reference_rend_le_numero_et_non_la_phrase():
    """DÉFAUT TROUVÉ EN MESURANT AUTRE CHOSE. « Référence de la consultation :
    2026-MOE-014 » rendait « de la consultation : 2026-MOE-014 » — la case du
    DC1 recevait la phrase entière. Personne ne le voyait : la case était
    pleine."""
    cas = {"Référence de la consultation : 2026-MOE-014.": "2026-MOE-014",
           "Référence : 2026-MOE-014.": "2026-MOE-014",
           "N° de marché : AO-2026-14.": "AO-2026-14",
           "Référence du dossier : DCE/2026/017.": "DCE/2026/017",
           "Référence de l'opération : OP-2026-3.": "OP-2026-3"}
    for phrase, attendu in cas.items():
        assert _valeur("reference", phrase) == attendu, (
            phrase, _valeur("reference", phrase))


# ══════════════════════════════════════════════════════════════════════════
# 4. CE QUE LE DOSSIER REMPLIT, BOUT EN BOUT
# ══════════════════════════════════════════════════════════════════════════

RC = """RÈGLEMENT DE LA CONSULTATION
Pouvoir adjudicateur : Communauté d'agglomération de l'Essai.
Objet du marché : maîtrise d'œuvre pour un centre de données régional.
Référence de la consultation : 2026-MOE-014.
La consultation est allotie en 3 lots.
Date limite de remise des offres : 30 octobre 2026 à 12 h 00.
"""
CCAP = """CAHIER DES CLAUSES ADMINISTRATIVES PARTICULIÈRES
Délai d'exécution : 18 mois à compter de la notification.
"""


def _rempli():
    an = A.analyser([{"nom": "01_RC.pdf", "texte": RC},
                     {"nom": "02_CCAP.pdf", "texte": CCAP}])
    return A.remplir(fiche={"raison_sociale": "Essai"}, analyse=an,
                     saisies={"dc4.sous_traitance": "oui"})


def test_cinq_releves_distincts_nourrissent_les_formulaires():
    """LA MESURE QUI COMPTE, et elle est datée. Trois relevés seulement
    remplissaient une case — acheteur, objet, référence. L'allotissement et le
    délai les rejoignent. Ce que la règle tient, c'est qu'ils remplissent
    RÉELLEMENT, sur un dossier écrit comme les vrais le sont."""
    r = _rempli()
    remplis = {}
    for p in r["pieces"]:
        for l in p["rubriques"]:
            if l["source"] == "consultation" and l["statut"] == "rempli":
                remplis.setdefault(l["releve"] if "releve" in l else l["cle"],
                                   set()).add(p["cle"])
    par_rubrique = {}
    for p in r["pieces"]:
        for l in p["rubriques"]:
            if l["source"] == "consultation":
                par_rubrique.setdefault(p["cle"], {})[l["cle"]] = l
    # L'ALLOTISSEMENT ARRIVE SUR LES TROIS FORMULAIRES QUI LE DEMANDENT.
    for piece in ("dc1", "acte_engagement", "dc4"):
        lots = par_rubrique[piece]["lots"]
        assert lots["statut"] == "rempli", (piece, lots["statut"])
        assert lots["valeur"] == "3 lots", (piece, lots["valeur"])
    # LA DURÉE DE L'ACTE D'ENGAGEMENT VIENT DU CCAP, plus d'une saisie.
    duree = par_rubrique["acte_engagement"]["duree"]
    assert duree["statut"] == "rempli", duree
    assert duree["valeur"].startswith("18 mois"), duree
    # L'ORIGINE NOMME LA PIÈCE PAR SON SIGLE, pas par son nom de fichier —
    # « Relevé dans CCAP » plutôt que « dans 02_CCAP.pdf ». C'est une
    # correction de MA règle, pas du module : j'y cherchais le nom de fichier,
    # et elle serait tombée pour une raison sans rapport avec ce qu'elle
    # prétend mesurer. Ce qui compte est que la durée soit attribuée à la
    # pièce QUI LA PORTE, et le CCAP la porte — pas le RC.
    assert "CCAP" in duree["origine"], duree["origine"]
    assert "RC" not in duree["origine"].replace("CCAP", ""), (
        "la durée est attribuée au règlement de consultation, qui ne la "
        "porte pas : %s" % duree["origine"])
    assert duree["citation"]["fichier"] == "02_CCAP.pdf", duree["citation"]
    # ET LA RÉFÉRENCE EST LE NUMÉRO, PAS LA PHRASE.
    assert par_rubrique["dc1"]["reference"]["valeur"] == "2026-MOE-014"


def test_chaque_valeur_relevee_porte_sa_citation_et_sa_position():
    """Une valeur sans sa phrase d'origine est une interprétation déguisée.
    C'est la citation qui permet d'aller vérifier « 18 mois à compter de la
    notification » au CCAP — et le point de départ, que la valeur ne dit
    pas."""
    r = _rempli()
    vus = 0
    for p in r["pieces"]:
        for l in p["rubriques"]:
            if l["source"] == "consultation" and l["statut"] == "rempli":
                vus += 1
                assert l["citation"] and l["citation"]["texte"], (p["cle"], l["cle"])
                assert l["citation"]["fichier"], (p["cle"], l["cle"])
                assert 0 <= l["citation"]["part"] <= 100, l["citation"]
                assert l["valeur"] in l["citation"]["texte"], (
                    "la valeur ne figure pas dans sa propre citation : %r / %r"
                    % (l["valeur"], l["citation"]["texte"]))
    assert vus >= 15, vus


def test_l_allotissement_releve_ne_decide_PAS_de_l_objet_de_la_candidature():
    """DEUX CHOSES DIFFÉRENTES, ET LES CONFONDRE COÛTE LA CANDIDATURE : ce que
    la consultation DÉCOUPE se relève, ce à quoi vous POSTULEZ se décide. Un
    module qui déduirait la seconde de la première ferait postuler à trois lots
    quelqu'un qui n'en veut qu'un."""
    dc1 = [p for p in _rempli()["pieces"] if p["cle"] == "dc1"][0]
    par_cle = {l["cle"]: l for l in dc1["rubriques"]}
    assert par_cle["lots"]["source"] == "consultation"
    assert par_cle["lots"]["statut"] == "rempli"
    assert par_cle["objet_candidature"]["source"] == "saisie"
    assert par_cle["objet_candidature"]["statut"] == "a_saisir"
    assert par_cle["objet_candidature"]["valeur"] is None
