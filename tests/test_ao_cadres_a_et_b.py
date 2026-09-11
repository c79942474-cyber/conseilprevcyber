# -*- coding: utf-8 -*-
"""Les cadres A et B des formulaires : pourquoi ils restaient vides.

LA PLAINTE, ET CE QU'ELLE DÉSIGNAIT VRAIMENT. « A - Identification de
l'acheteur » et « B - Objet de la consultation » ressortaient vides sur les
DC1, DC2 et DC4, alors que le règlement de consultation déposé porte les deux
en première page. Le remplissage n'était pas en cause : mesuré, la valeur se
pose bien juste sous l'intitulé du cadre. C'est le RELEVÉ qui ne voyait rien.

LA CAUSE, MESURÉE SUR LES HUIT FORMES QU'UN RC REND VRAIMENT. Tous les motifs
de l'acheteur exigeaient DEUX-POINTS suivis de la valeur. Or un règlement
présente presque toujours son cadre d'identification en TABLEAU : l'extracteur
PDF rend alors l'intitulé sur une ligne et la valeur sur la suivante, sans
deux-points. Trois formulations sur huit passaient. Celles qui échouaient sont
les plus courantes — dont « Identification de l'acheteur », qui est l'intitulé
EXACT du cadre A du DC1.

LE PIÈGE DE L'ÉLARGISSEMENT, ET IL A ÉTÉ TOUCHÉ. Prendre « la ligne d'après »
fait entrer n'importe quoi. Premier essai : « Maître d'ouvrage \\n voir article
2 du présent règlement » ressortait comme nom d'acheteur — une phrase de renvoi
recopiée dans le cadre A d'un formulaire de l'État. La garde de majuscule ne
gardait rien parce que `_extraire` compile en IGNORECASE. D'où `(?-i:…)`, et
d'où la moitié négative de ce fichier : un relevé trop large est PIRE qu'un
relevé absent, parce qu'une case vide se remarque et qu'une case fausse se
signe.
"""
import pytest

import ao_dc
import ao_formulaires
import dossier_entreprise

SOCLE = ("RÈGLEMENT DE LA CONSULTATION\n"
         "Le présent règlement de la consultation fixe les modalités.\n")


def _relever(corps, cle):
    a = ao_dc.analyser([{"nom": "RC.pdf", "texte": SOCLE + corps,
                         "extension": ".pdf"}])
    props = ao_dc._index_releves(a).get(cle) or [{}]
    return props[0].get("valeur")


#: Les huit formes sous lesquelles un RC nomme son acheteur. Toutes viennent
#: de documents réels ou de l'intitulé officiel des formulaires.
ACHETEUR = [
    ("deux-points sur la même ligne",
     "Pouvoir adjudicateur : Communauté d'agglomération de Sophia Antipolis\n"),
    ("deux-points, valeur à la ligne suivante",
     "Pouvoir adjudicateur :\nCommunauté d'agglomération de Sophia Antipolis\n"),
    ("tableau à deux colonnes, sans deux-points",
     "Pouvoir adjudicateur\nCommunauté d'agglomération de Sophia Antipolis\n"),
    ("l'intitulé EXACT du cadre A du DC1",
     "Identification de l'acheteur\n"
     "Communauté d'agglomération de Sophia Antipolis\n"),
    ("« Acheteur » tout court",
     "Acheteur : Communauté d'agglomération de Sophia Antipolis\n"),
    ("« organisme acheteur », formule des avis publiés",
     "Nom et adresse officiels de l'organisme acheteur : Communauté "
     "d'agglomération de Sophia Antipolis\n"),
    ("« Maître d'ouvrage » sur deux lignes",
     "Maître d'ouvrage\nCommunauté d'agglomération de Sophia Antipolis\n"),
    ("« Collectivité »",
     "Collectivité : Commune de Biot\n"),
]

OBJET = [
    ("deux-points sur la même ligne",
     "Objet du marché : construction d'un centre de données de 2 MW\n"),
    ("valeur à la ligne suivante",
     "Objet du marché :\nconstruction d'un centre de données de 2 MW\n"),
    ("tableau, sans deux-points",
     "Objet du marché\nconstruction d'un centre de données de 2 MW\n"),
    ("l'intitulé EXACT du cadre B du DC1",
     "Objet de la consultation\nconstruction d'un centre de données de 2 MW\n"),
    ("« Intitulé du marché »",
     "Intitulé du marché : construction d'un centre de données de 2 MW\n"),
    ("« Désignation des prestations »",
     "Désignation des prestations : construction d'un centre de données\n"),
]


@pytest.mark.parametrize("nom,corps", ACHETEUR, ids=[x[0] for x in ACHETEUR])
def test_l_acheteur_est_releve_sous_toutes_ses_formes(nom, corps):
    """Huit formes, huit relevés. Trois seulement passaient avant.

    On mesure la VALEUR rendue, pas l'existence d'un motif : un motif ajouté
    qui ne capture rien laisserait une règle de présence verte et le cadre A
    vide.
    """
    v = _relever(corps, "acheteur")
    assert v, "« %s » : l'acheteur n'est pas relevé" % nom
    assert "Communauté d'agglomération" in v or "Commune de Biot" in v, v


@pytest.mark.parametrize("nom,corps", OBJET, ids=[x[0] for x in OBJET])
def test_l_objet_est_releve_sous_toutes_ses_formes(nom, corps):
    v = _relever(corps, "objet")
    assert v, "« %s » : l'objet n'est pas relevé" % nom
    assert "centre de données" in v, v


# ═══════════════════════════════════════════════════════════════════════════
#  LA MOITIÉ NÉGATIVE — UN RELEVÉ FAUX EST PIRE QU'UN RELEVÉ ABSENT
# ═══════════════════════════════════════════════════════════════════════════

FAUX = [
    ("le mot sans nom d'organisme",
     "Le pouvoir adjudicateur se réserve le droit de ne pas donner suite.\n"),
    ("le profil d'acheteur porte une adresse, pas un nom",
     "Profil d'acheteur : https://www.marches-securises.fr\n"),
    ("un cadre vide : l'intitulé suivant n'est pas une réponse",
     "Pouvoir adjudicateur\nObjet du marché :\n"),
    ("une phrase de renvoi n'est pas un acheteur",
     "Maître d'ouvrage\nvoir article 2 du présent règlement\n"),
    ("l'intitulé suivi de rien",
     "Pouvoir adjudicateur\n\n"),
    # CES DEUX-LÀ VIENNENT D'UNE MUTATION SURVIVANTE. Le refus d'une adresse
    # était écrit « \s*:\s*(?!https?:) » : le moteur reculait `\s*` d'un
    # caractère, évaluait le refus sur « espace + https » et capturait
    # « https://www » comme nom d'acheteur. La garde avait l'air juste et ne
    # gardait rien — et aucun cas d'essai ne l'atteignait, puisque
    # « Profil d'acheteur » est déjà écarté par l'ancrage en début de ligne.
    ("une adresse de plateforme n'est pas un acheteur",
     "Acheteur : https://www.ville-de-biot.fr\n"),
    ("une adresse sans protocole non plus",
     "Acheteur : www.ville-de-biot.fr/marches-publics\n"),
]


@pytest.mark.parametrize("nom,corps", FAUX, ids=[x[0] for x in FAUX])
def test_ce_qui_n_est_pas_un_acheteur_n_est_pas_releve(nom, corps):
    """UNE CASE VIDE SE REMARQUE, UNE CASE FAUSSE SE SIGNE.

    Ces cinq cas ont été touchés en élargissant : le quatrième relevait
    « voir article 2 du présent règlement » comme nom d'acheteur, et l'aurait
    fait écrire dans le cadre A d'un DC1.
    """
    v = _relever(corps, "acheteur")
    assert not v, "« %s » : a relevé %r comme acheteur" % (nom, v)


def test_la_majuscule_est_exigee_malgre_le_drapeau_ignorecase():
    """LA RÈGLE QUI GARDE LA GARDE.

    `_extraire` compile en IGNORECASE : une classe [A-Z] y matche aussi les
    minuscules, et la garde ne gardait donc rien. Le témoin direct : la même
    ligne, en majuscule puis en minuscule, doit donner deux résultats
    différents. Sans cette règle, retirer `(?-i:…)` passerait inaperçu.
    """
    assert _relever("Maître d'ouvrage\nVille de Biot et ses environs\n",
                    "acheteur"), "un nom propre doit passer"
    assert not _relever("Maître d'ouvrage\nvoir le cahier des charges joint\n",
                        "acheteur"), "une phrase en minuscules ne doit pas passer"


# ═══════════════════════════════════════════════════════════════════════════
#  L'EFFET DE BOUT EN BOUT : LES CADRES A ET B SE REMPLISSENT
# ═══════════════════════════════════════════════════════════════════════════

RC_TABLEAU = SOCLE + (
    "\nIdentification de l'acheteur\n"
    "Communauté d'agglomération de Sophia Antipolis\n\n"
    "Objet de la consultation\n"
    "Construction d'un centre de données de 2 MW sur la commune de Biot\n")


def test_les_cadres_A_et_B_se_remplissent_sur_un_RC_en_tableau():
    """LA RÈGLE DÉCISIVE. Elle mesure le DOCUMENT, pas le relevé.

    Un relevé juste qui n'arriverait pas jusqu'au formulaire ne corrigerait
    rien de ce qui a été signalé — et c'est exactement la confusion qu'il a
    fallu défaire pour trouver la cause.
    """
    a = ao_dc.analyser([{"nom": "RC.pdf", "texte": RC_TABLEAU,
                         "extension": ".pdf"}])
    r = ao_dc.remplir(fiche=dossier_entreprise.fiche_candidat()["fiche"],
                      analyse=a)
    for modele, cle in (("dc1", "dc1"), ("dc2", "dc2"), ("dc4", "dc4")):
        _, rap = ao_formulaires.remplir_document(
            modele, ao_formulaires.valeurs_pour(r, cle))
        poses = {p["rubrique"] for p in rap["places"]}
        assert "acheteur" in poses, (
            "%s : le cadre A reste vide sur un RC qui nomme son acheteur"
            % modele)
        assert poses & {"objet_consultation", "objet_marche"}, (
            "%s : le cadre B reste vide" % modele)


def test_l_acte_d_engagement_garde_son_acheteur_sans_ancre():
    """CE QUI N'EST PAS UN DÉFAUT, ET QU'IL NE FAUT PAS « CORRIGER ».

    L'ATTRI1 n'a délibérément pas d'ancre pour l'acheteur : ses cadres C et D
    sont les blocs de SIGNATURE, et y écrire un nom ferait ressembler à signé
    un document qui ne l'est pas. La valeur est détenue et ressort en
    `sans_ancre` — nommée, donc, jamais perdue en silence.
    """
    a = ao_dc.analyser([{"nom": "RC.pdf", "texte": RC_TABLEAU,
                         "extension": ".pdf"}])
    r = ao_dc.remplir(fiche=dossier_entreprise.fiche_candidat()["fiche"],
                      analyse=a)
    v = ao_formulaires.valeurs_pour(r, "acte_engagement")
    assert v.get("acheteur"), "l'acte d'engagement ne détient plus l'acheteur"
    _, rap = ao_formulaires.remplir_document("attri1", v)
    assert "acheteur" in rap["sans_ancre"], (
        "l'acheteur est écrit quelque part dans l'acte d'engagement : "
        "vérifier que ce n'est pas dans un bloc de signature — %r"
        % [p["rubrique"] for p in rap["places"]])
