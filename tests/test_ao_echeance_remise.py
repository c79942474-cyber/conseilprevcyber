# -*- coding: utf-8 -*-
"""VALIDES À LA DATE DE REMISE — LA QUESTION QUE L'ÉCRAN POSAIT SANS Y RÉPONDRE.

CE QUI ÉTAIT EN CAUSE, ET QUI SE LISAIT DANS LE CODE LUI-MÊME. L'étape
« attestations » du parcours demande, en toutes lettres : « Mes attestations
sont-elles valides À LA DATE DE REMISE ? », et son piège ajoute : « C'est
l'échéance comparée au jour de la remise qui décide. » Elle comparait à
AUJOURD'HUI.

MESURÉ AVANT CORRECTION, sur un dossier à remettre dans quarante jours avec
une attestation de vigilance valable encore dix : « 2 attestation(s) valide(s)
sur 2 », étape FAITE — et le dossier serait parti avec une attestation périmée
depuis trente jours. Une mesure verte pour une raison sans rapport avec ce
qu'elle prétend : le défaut que ce dossier poursuit depuis des semaines, cette
fois dans un écran.

CE QUE CES RÈGLES TIENNENT :

  · LA DATE DE REMISE EST LUE, PAS SAISIE. Elle vient du règlement de
    consultation déposé, avec sa citation. Une date saisie serait une date
    qu'on peut se tromper en recopiant, et l'écran l'annoncerait avec
    l'autorité d'un relevé.

  · CE QUI N'EST PAS LISIBLE EST DÉCLARÉ ILLISIBLE. « Courant octobre », « au
    plus tard trente jours après notification » sont des échéances valables
    pour un juriste et illisibles pour un programme. On rend None, et l'écran
    dit qu'il n'a pas pu répondre — au lieu d'inventer une date.

  · ENTRE DEUX DATES, LA PLUS PROCHE. Exception assumée à la règle du module
    (« la pièce ouverte en premier fait foi ») : une candidature remise en
    retard est irrecevable, sans recours et sans nuance.

  · « VALIDE » NE PERD PAS SON SENS. L'alerte des trente jours est un DRAPEAU,
    pas un état : une attestation valide reste comptée valide, sans quoi
    `couverture()` déclarerait non prouvée une déclaration qui l'est.
"""
import datetime
import io
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc                                                       # noqa: E402
import ao_parcours                                                 # noqa: E402
import dossier_entreprise as DE                                    # noqa: E402
from conftest import ORIGINE                                       # noqa: E402

import pytest                                                      # noqa: E402

JOUR = datetime.date(2026, 9, 15)
REMISE = JOUR + datetime.timedelta(days=40)          # 2026-10-25


def _rc(quand=None):
    return (u"REGLEMENT DE LA CONSULTATION\n"
            u"Article 6 — Remise des plis\n"
            u"Date et heure limites de remise des offres : %s a 12h00.\n"
            % (quand or REMISE.strftime("%d/%m/%Y")))


def _analyse(texte=None, nom="RC-2026.pdf"):
    return ao_dc.analyser([{"nom": nom, "texte": texte or _rc(),
                            "extension": ".pdf"}])


def _att(cle, nom, jours):
    """Une attestation qui expire dans `jours` jours à compter de JOUR."""
    return {"annexe": cle.upper()[:3], "cle": cle, "nom": nom,
            "organisme": "Organisme", "delivree_le": "2026-03-01",
            "valable_jusqu_au": (JOUR + datetime.timedelta(days=jours)).isoformat(),
            "couvre": [], "manques": []}


def _etat(table, remise=None):
    return DE.etat_attestations(aujourdhui=JOUR.isoformat(), table=table,
                                remise=remise)


def _etape(etat_att):
    return next(x for x in ao_parcours.parcours({"attestations": etat_att})["etapes"]
                if x["id"] == "attestations")


# ══════════════════════════════════════════════════════════════════════════
#  1. LA DATE S'ÉCRIT À LA FRANÇAISE, ET SE LIT COMME TELLE
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("brut,attendu", [
    (u"25/10/2026 a 12h00", (2026, 10, 25)),
    (u"25-10-2026", (2026, 10, 25)),
    (u"25.10.2026 à 12 h 00", (2026, 10, 25)),
    (u"25/10/26", (2026, 10, 25)),
    (u"vendredi 25 octobre 2026 à 12h", (2026, 10, 25)),
    (u"1er avril 2027", (2027, 4, 1)),
    (u"3 sept. 26", (2026, 9, 3)),
    (u"29 février 2028", (2028, 2, 29)),
])
def test_les_formes_francaises_courantes_se_lisent(brut, attendu):
    """HUIT FORMES, PARCE QU'UN RÈGLEMENT DE CONSULTATION LES UTILISE TOUTES.
    Une seule forme reconnue ferait une fonction verte et un écran muet sur
    les sept autres dossiers."""
    assert ao_dc.jour_francais(brut) == datetime.date(*attendu)


@pytest.mark.parametrize("brut", [
    u"", u"courant octobre", u"à la rentrée",
    u"au plus tard trente jours après notification",
    u"32/01/2026", u"25/13/2026", u"29 février 2027",
    # LE CAS QUI COMPTE VRAIMENT, ET QUI MANQUAIT. Les trois précédents sont
    # refusés des DEUX côtés — « 25/13 » relu à l'envers donne le mois 25, tout
    # aussi impossible — si bien qu'une mutation ajoutant une relecture
    # mois/jour a SURVÉCU : la règle ne mesurait pas ce qu'elle annonçait.
    #
    # « 05/31/2026 » est une date écrite à l'américaine dans un dossier
    # français. Lue à la française elle est impossible (mois 31) ; relue à
    # l'envers elle devient le 31 mai, parfaitement plausible et parfaitement
    # fausse. Une échéance inventée là fait travailler sur une date qui
    # n'existe pas dans le règlement.
    u"05/31/2026",
])
def test_ce_qui_n_est_pas_une_date_rend_None(brut):
    """RENDRE None EST LA BONNE RÉPONSE. « Courant octobre » est une échéance
    valable pour un juriste et illisible pour un programme : en inventer une
    ferait dire à l'écran « vous avez jusqu'au 31 octobre », ce qui est pire
    que « je n'ai pas su la lire ».

    ET LES DATES IMPOSSIBLES SONT REFUSÉES, PAS RELUES À L'ENVERS. « 25/13 »
    relu en mois/jour donnerait le 13 décembre — une échéance fausse de sept
    semaines, avec l'air d'en être sûre."""
    assert ao_dc.jour_francais(brut) is None


def test_le_jour_vient_AVANT_le_mois_et_c_est_sans_exception():
    """LE DOSSIER EST FRANÇAIS. « 05/10/2026 » est le 5 octobre, jamais le
    10 mai. Les deux nombres étant inférieurs à treize, aucun garde-fou
    automatique ne peut trancher : c'est la convention qui décide, et elle est
    tenue ici."""
    assert ao_dc.jour_francais(u"05/10/2026") == datetime.date(2026, 10, 5)


def test_l_annee_a_deux_chiffres_va_dans_ce_siecle():
    """UN RÈGLEMENT DE CONSULTATION NE FIXE PAS D'ÉCHÉANCE AU SIÈCLE DERNIER.
    Le pivot est déclaré dans le module plutôt qu'implicite : c'est le genre
    de constante qu'on cherche en vain le jour où une date part de travers."""
    assert ao_dc.jour_francais(u"25/10/26").year == 2026
    assert ao_dc._PIVOT_SIECLE == 80


# ══════════════════════════════════════════════════════════════════════════
#  2. LA DATE VIENT DU DOSSIER DÉPOSÉ, AVEC SA CITATION
# ══════════════════════════════════════════════════════════════════════════

def test_la_date_limite_est_lue_dans_le_reglement_avec_sa_citation():
    """UNE VALEUR SANS SA PHRASE D'ORIGINE EST UNE INTERPRÉTATION DÉGUISÉE.
    L'écran doit pouvoir montrer la phrase et la pièce d'où elle vient."""
    d = ao_dc.date_limite(_analyse())
    assert d["date"] == REMISE.isoformat()
    assert "limites de remise" in d["citation"]
    assert d["fichier"] == "RC-2026.pdf" and d["sigle"] == "RC"
    assert d["pourquoi"] == ""


def test_sans_dossier_la_date_est_DECLAREE_illisible():
    """LE TÉMOIN NÉGATIF. Sans lui, une règle qui lit une date passerait aussi
    bien sur un module qui en rend toujours une."""
    d = ao_dc.date_limite(ao_dc.analyser([]))
    assert d["date"] is None
    assert "n'a pas été lue" in d["pourquoi"]
    assert "ce n'est pas" in d["pourquoi"].lower()


def test_une_echeance_en_prose_ne_donne_AUCUNE_date():
    """Le relevé peut trouver la PHRASE sans que la valeur soit une date. Le
    module doit alors se taire sur la date tout en ayant vu le passage."""
    texte = (u"REGLEMENT DE LA CONSULTATION\n"
             u"Date et heure limites de remise des offres : courant octobre, "
             u"selon avis rectificatif.\n")
    d = ao_dc.date_limite(_analyse(texte))
    assert d["date"] is None
    assert d["propositions"] >= 1, \
        "le relevé n'a même pas vu le passage : la règle ne mesure pas ce " \
        "qu'elle croit"


def test_entre_deux_dates_la_PLUS_PROCHE_est_retenue_et_l_autre_NOMMEE():
    """EXCEPTION ASSUMÉE À LA RÈGLE DU MODULE. Partout ailleurs, la pièce
    ouverte en premier fait foi. Ici non : retenir la plus tardive ferait
    travailler sur une échéance qui n'existe peut-être pas, et une candidature
    remise en retard est irrecevable, sans recours et sans nuance.

    L'AUTRE EST NOMMÉE, jamais écrasée en silence : c'est une divergence entre
    deux pièces, et c'est au lecteur de trancher sur le papier."""
    tot = (REMISE - datetime.timedelta(days=10)).strftime("%d/%m/%Y")
    a = ao_dc.analyser([
        {"nom": "RC-2026.pdf", "texte": _rc(), "extension": ".pdf"},
        {"nom": "avenant-1.pdf", "extension": ".pdf",
         "texte": u"Remise des plis : %s a 12h00 (modification).\n" % tot}])
    d = ao_dc.date_limite(a)
    assert d["date"] == (REMISE - datetime.timedelta(days=10)).isoformat()
    assert [x["date"] for x in d["divergences"]] == [REMISE.isoformat()]


# ══════════════════════════════════════════════════════════════════════════
#  3. LE QUATRIÈME ÉTAT : VALIDE AUJOURD'HUI, MORTE LE JOUR QUI COMPTE
# ══════════════════════════════════════════════════════════════════════════

def test_une_attestation_qui_expire_avant_la_remise_change_d_ETAT():
    """LE CAS QUI A MOTIVÉ TOUT CE TOUR, chiffré : dix jours de validité pour
    une remise à quarante jours."""
    e = _etat([_att("vigilance", "Vigilance", 10),
               _att("fiscale", "Fiscale", 200)], remise=REMISE.isoformat())
    par = {l["cle"]: l for l in e["lignes"]}
    assert par["vigilance"]["etat"] == "expire_avant_remise"
    assert par["fiscale"]["etat"] == "valide"
    assert e["expirent_avant_remise"] == ["vigilance"]
    assert e["remise"] == REMISE.isoformat()


def test_elle_dit_DE_COMBIEN_elle_manque():
    """UN JOUR ET SIX MOIS NE SE TRAITENT PAS PAREIL : l'un se renouvelle,
    l'autre se demande tout de suite."""
    e = _etat([_att("vigilance", "Vigilance", 10)], remise=REMISE.isoformat())
    assert e["lignes"][0]["jours_avant_remise"] == -30


def test_sans_date_de_remise_l_ancien_comportement_est_INTACT():
    """TOUS LES APPELANTS QUI NE CONNAISSENT PAS DE CONSULTATION GARDENT LEUR
    RÉPONSE — l'écran du dossier d'entreprise, `couverture()`. Ce qui change,
    c'est qu'on SAIT désormais que le verdict ne vaut que pour aujourd'hui."""
    e = _etat([_att("vigilance", "Vigilance", 10)])
    assert e["lignes"][0]["etat"] == "valide"
    assert e["expirent_avant_remise"] == []
    assert e["remise"] is None


def test_une_date_de_remise_DEPASSEE_est_ignoree():
    """Une date limite déjà passée signale un dossier archivé ou une lecture
    fausse, pas une attestation à renouveler. Comparer à elle ferait ressortir
    tout le dossier en rouge pour une raison sans rapport."""
    e = _etat([_att("vigilance", "Vigilance", 10)],
              remise=(JOUR - datetime.timedelta(days=5)).isoformat())
    assert e["remise"] is None
    assert e["lignes"][0]["etat"] == "valide"


def test_une_attestation_deja_perimee_reste_PERIMEE_pas_expirante():
    """LES DEUX NE SE SOIGNENT PAS PAREIL, et les confondre ferait croire
    qu'on a encore le temps."""
    e = _etat([_att("vigilance", "Vigilance", -3)], remise=REMISE.isoformat())
    assert e["lignes"][0]["etat"] == "perimee"
    assert e["perimees"] == ["vigilance"] and e["expirent_avant_remise"] == []


def test_les_quatre_etats_sont_DECLARES_et_aucun_autre_ne_sort():
    """L'ÉNUMÉRATION EST LA RÉFÉRENCE. Un cinquième état apparu sans y figurer
    traverserait l'écran en clé de programme — « expire_avant_remise » affiché
    tel quel à quelqu'un qui prépare un dossier."""
    e = _etat([_att("vigilance", "Vigilance", 10),
               _att("fiscale", "Fiscale", 200),
               _att("vieille", "Vieille", -40),
               {"annexe": "X", "cle": "sansdate", "nom": "Sans date",
                "organisme": "O", "delivree_le": None,
                "valable_jusqu_au": None, "couvre": [], "manques": []}],
              remise=REMISE.isoformat())
    vus = {l["etat"] for l in e["lignes"]}
    assert vus == set(DE.ETATS_ATTESTATION), vus


# ══════════════════════════════════════════════════════════════════════════
#  4. L'ALERTE EST UN DRAPEAU, PAS UN ÉTAT
# ══════════════════════════════════════════════════════════════════════════

def test_une_attestation_bientot_perimee_est_signalee_SANS_cesser_d_etre_valide():
    """SI C'ÉTAIT UN ÉTAT, `couverture()` DÉCLARERAIT NON PROUVÉE UNE
    DÉCLARATION QUI L'EST. Le drapeau se pose à côté et ne retire rien."""
    e = _etat([_att("vigilance", "Vigilance", 12)])
    assert e["lignes"][0]["etat"] == "valide"
    assert e["lignes"][0]["alerte"] is True
    assert e["valides"] == ["vigilance"] and e["bientot"] == ["vigilance"]


def test_au_dela_du_seuil_aucune_alerte():
    """LE TÉMOIN NÉGATIF DU DRAPEAU. Sans lui, une règle qui constate une
    alerte passerait sur un module qui en lève toujours une."""
    e = _etat([_att("fiscale", "Fiscale", DE.JOURS_ALERTE + 1)])
    assert e["lignes"][0]["alerte"] is False and e["bientot"] == []


def test_le_seuil_est_DECLARE_et_rendu_avec_la_mesure():
    """UN NOMBRE MAGIQUE DANS UNE COMPARAISON NE SE DISCUTE PAS. Celui-ci est
    nommé, justifié dans le module, et rendu à l'écran pour qu'il puisse
    écrire « valides moins de N jours » au lieu d'un nombre en dur."""
    assert DE.JOURS_ALERTE >= 7
    assert _etat([])["seuil_alerte"] == DE.JOURS_ALERTE


def test_une_perimee_ne_porte_PAS_l_alerte():
    """« À relancer maintenant » sur une attestation déjà morte ferait croire
    qu'il reste une marge."""
    e = _etat([_att("vigilance", "Vigilance", -2)])
    assert e["lignes"][0]["alerte"] is False


# ══════════════════════════════════════════════════════════════════════════
#  5. LE PARCOURS RÉPOND À LA QUESTION QU'IL POSE
# ══════════════════════════════════════════════════════════════════════════

def test_l_etape_REFUSE_de_se_dire_faite_quand_une_attestation_meurt_avant():
    """LE CŒUR DE CE TOUR. Avant : « 2 valide(s) sur 2 », étape FAITE, et le
    dossier partait avec une attestation périmée depuis trente jours."""
    e = _etape(_etat([_att("vigilance", "Vigilance", 10),
                      _att("fiscale", "Fiscale", 200)],
                     remise=REMISE.isoformat()))
    assert e["fait"] is False
    assert e["reste"] == ["vigilance"]
    assert "LE JOUR DE LA REMISE" in e["mesure"]
    assert REMISE.isoformat() in e["mesure"]


def test_la_mesure_DIT_a_quelle_date_son_verdict_vaut():
    """« 5 VALIDES SUR 5 » N'EST PAS UNE RÉPONSE SI ON NE SAIT PAS À QUELLE
    DATE. C'est précisément ce qui rendait l'ancien écran faux sans être
    mensonger : il ne disait pas de quoi il parlait."""
    e = _etape(_etat([_att("fiscale", "Fiscale", 200)],
                     remise=REMISE.isoformat()))
    assert e["fait"] is True
    assert REMISE.isoformat() in e["mesure"]
    assert "date limite relevée dans le dossier" in e["mesure"]


def test_sans_date_de_remise_l_etape_dit_qu_elle_n_a_pas_repondu():
    """ET NE SE DÉCLARE PAS FAITE. Se déclarer faite sur une question qu'on
    n'a pas posée est exactement ce qu'on corrige."""
    e = _etape(_etat([_att("fiscale", "Fiscale", 200)]))
    assert e["fait"] is False
    assert "NON LUE" in e["mesure"] and "ne répond pas à la question" in e["mesure"]


def test_la_question_et_le_piege_de_l_etape_parlent_bien_de_la_remise():
    """CE QUE L'ÉCRAN PROMET DOIT RESTER CE QUE LA MESURE FAIT. Si un jour
    quelqu'un réécrit la question en « valides aujourd'hui ? », cette règle
    tombe — et c'est le bon moment pour se demander laquelle des deux a
    raison."""
    e = next(x for x in ao_parcours.parcours({})["etapes"]
             if x["id"] == "attestations")
    assert "DATE DE REMISE" in e["question"]
    assert "remise" in e["piege"].lower()
    assert "règlement de consultation" in e["geste"]


# ══════════════════════════════════════════════════════════════════════════
#  6. LA ROUTE, ET L'ÉCRAN
# ══════════════════════════════════════════════════════════════════════════

def test_la_route_du_parcours_rend_la_date_limite_lue(marche):
    """ELLE VIENT DE L'ANALYSE, PAS DE LA PAGE. Une date transmise par le
    navigateur serait une date SAISIE — donc une date qu'on peut se tromper en
    recopiant — et l'écran l'annoncerait avec l'autorité d'un relevé."""
    r = marche.post("/api/datacenter/marche/parcours",
                    json={"fiche": {"raison_sociale": "CONSEILPREV"},
                          "analyse": _analyse()},
                    headers=ORIGINE)
    assert r.status_code == 200
    j = r.get_json()
    et = next(x for x in j["parcours"]["etapes"] if x["id"] == "attestations")
    assert REMISE.isoformat() in et["mesure"], et["mesure"]


def test_la_route_ne_reclame_PAS_la_date_a_la_page(marche):
    """UNE DATE ENVOYÉE PAR LE NAVIGATEUR NE DOIT RIEN CHANGER. Sinon, il
    suffirait de poster « remise: 2099-01-01 » pour faire passer l'étape au
    vert avec des attestations mortes."""
    r = marche.post("/api/datacenter/marche/parcours",
                    json={"fiche": {"raison_sociale": "CONSEILPREV"},
                          "analyse": ao_dc.analyser([]),
                          "remise": "2099-01-01", "date_limite": "2099-01-01"},
                    headers=ORIGINE)
    et = next(x for x in r.get_json()["parcours"]["etapes"]
              if x["id"] == "attestations")
    assert "2099" not in et["mesure"], \
        "une date envoyée par la page est entrée dans la mesure"


def test_l_ecran_du_dossier_nomme_les_etats_au_lieu_de_les_coder():
    """« expire_avant_remise » EST UNE CLÉ DE PROGRAMME. Sur l'écran de
    quelqu'un qui prépare un dossier, elle doit dire ce qu'elle veut dire."""
    src = io.open(os.path.join(ICI, "admin-dossier-entreprise.html"),
                  encoding="utf-8").read()
    assert "périmée le jour de la remise" in src
    for cle in DE.ETATS_ATTESTATION:
        assert cle in src, "l'écran ignore l'état « %s »" % cle


def test_l_ecran_compte_les_attestations_BIENTOT_perimees():
    """SANS CE COMPTE, le seul chiffre vert de l'écran — « 5 valides sur 5 » —
    couvrait le cas d'une attestation valide encore douze jours."""
    src = io.open(os.path.join(ICI, "admin-dossier-entreprise.html"),
                  encoding="utf-8").read()
    assert "a.bientot" in src or "bientot ||" in src
    assert "seuil_alerte" in src, \
        "l'écran écrit le seuil en dur au lieu de le lire"
    assert "à relancer maintenant" in src
