# -*- coding: utf-8 -*-
"""COMBIEN de documents ce dossier-là demande — et pourquoi c'était faux avant.

LE DÉFAUT, MESURÉ. `remplir()` rendait TOUJOURS les vingt-trois pièces du
catalogue : qu'on ait déposé un règlement de consultation qui énumère ses
pièces ou rien du tout, l'écran annonçait le même nombre. Le compte affiché
était donc une propriété du CATALOGUE, jamais du dossier de l'acheteur, et
« 23 documents à remplir » se lisait comme une exigence de la consultation.

`exigees()` SAVAIT DÉJÀ, ET NE SERVAIT À RIEN. Elle rendait, pour chaque pièce,
si le texte déposé la nomme et où. Son résultat s'affichait en PASTILLE à côté
de chaque ligne — « exigée » / « non repérée » — et n'entrait dans aucune
décision. C'est le défaut de la maison dans sa forme la plus pure : une mesure
juste, calculée, affichée, et sans effet.

CE QUE CES RÈGLES REFUSENT DE LAISSER REVENIR :

  · UN NOMBRE CONSTANT. Un dossier muet et un dossier bavard doivent rendre
    des comptes DIFFÉRENTS. C'est la règle décisive de ce fichier.

  · UN SOCLE QUI AVALE LE CATALOGUE. Trois pièces au socle, pas treize : un
    socle large ramènerait la sélection à la liste complète et on aurait
    rhabillé le défaut qu'on corrige.

  · UNE PIÈCE QUI DISPARAÎT. Ce qui n'est pas repéré ressort `retenue: False`
    avec son motif, jamais absent : masquer un défaut de reconnaissance le
    ferait passer pour une absence d'exigence.

  · UNE PROMESSE DE REMPLISSAGE AUTOMATIQUE QU'ON NE TIENT PAS. Quatre
    modèles de l'État sont remplissables ; les autres pièces se rédigent ou
    s'obtiennent d'un tiers. Annoncer « sept documents remplis
    automatiquement » quand trois seulement le sont est la promesse la plus
    facile à démentir de tout ce module.

  · UN ÉCRAN ET UNE ARCHIVE QUI NE PARLENT PAS DU MÊME DOSSIER. Le périmètre
    est lu par UN seul lecteur, partagé par le remplissage, l'export,
    l'archive et le parcours.
"""
import re

import pytest

import ao_dc
import ao_formulaires


RC_MUET = """RÈGLEMENT DE LA CONSULTATION
Pouvoir adjudicateur : COMMUNAUTÉ D'AGGLOMÉRATION DE VAL-D'EUROPE
Objet du marché : construction d'un centre de données de 12 MW.
Les pièces à produire sont énumérées au CCAP.
"""

RC_BAVARD = """RÈGLEMENT DE LA CONSULTATION
Pouvoir adjudicateur : COMMUNAUTÉ D'AGGLOMÉRATION DE VAL-D'EUROPE
Objet du marché : construction d'un centre de données de 12 MW.
Les candidats produiront un DC1 et un DC2, une déclaration sur l'honneur,
les CV des intervenants clés, un organigramme, la liste des références
principales et une attestation d'assurance responsabilité civile
professionnelle. Un mémoire technique est exigé.
La décomposition du prix global et forfaitaire sera remise sur le modèle joint.
"""


def _sel(texte, **kw):
    a = ao_dc.analyser([{"nom": "RC.txt", "texte": texte}])
    return ao_dc.selection(a, **kw), a


# ═══════════════════════════════════════════════════════════════════════════
#  1. LE NOMBRE EST DÉRIVÉ — LA RÈGLE DÉCISIVE
# ═══════════════════════════════════════════════════════════════════════════

def test_un_dossier_muet_et_un_dossier_bavard_ne_rendent_PAS_le_meme_compte():
    """LA RÈGLE QUI MANQUAIT, ET QUI DÉFINIT CE TOUR.

    Elle ne vérifie pas qu'une fonction de sélection EXISTE — elle vérifie que
    son résultat DÉPEND du dossier. Une `selection()` qui rendrait les
    vingt-trois pièces quoi qu'il arrive passerait toute règle écrite sur sa
    présence, et ne corrigerait rien.
    """
    muet, _ = _sel(RC_MUET)
    bavard, _ = _sel(RC_BAVARD)
    assert muet["retenues"] < bavard["retenues"], (
        "le même compte pour un dossier muet (%d) et un dossier bavard (%d) : "
        "la sélection ne lit pas le dossier"
        % (muet["retenues"], bavard["retenues"]))
    assert muet["retenues"] < muet["catalogue"], (
        "un dossier muet retient %d pièces sur %d : c'est le catalogue, pas "
        "une sélection" % (muet["retenues"], muet["catalogue"]))
    assert bavard["retenues"] < bavard["catalogue"], (
        "un dossier bavard retient TOUT le catalogue : la sélection ne filtre "
        "plus rien")


def test_chaque_piece_retenue_dit_POURQUOI_elle_l_est():
    """Un périmètre sans motif ne se discute pas — et un opérateur qui ne peut
    pas discuter une sélection la subit ou l'ignore."""
    s, _ = _sel(RC_BAVARD)
    motifs = ("citee", "socle", "ajoutee")
    for x in s["lignes"]:
        if x["retenue"]:
            assert x["pourquoi"] in motifs, x
            assert x["motif"] and len(x["motif"]) > 15, x
        else:
            assert x["pourquoi"] in ("non_reperee", "ecartee"), x
            assert x["motif"], x


def test_une_piece_citee_porte_la_citation_qui_la_declenche():
    """SANS CITATION, « exigée » EST UNE AFFIRMATION. C'est la doctrine du
    module depuis le début : chaque point relevé porte sa position dans la
    pièce, pour être vérifié."""
    s, _ = _sel(RC_BAVARD)
    citees = [x for x in s["lignes"] if x["pourquoi"] == "citee"]
    assert citees, "aucune pièce citée sur un dossier qui les énumère"
    for x in citees:
        c = x["citation"]
        assert c and c.get("texte"), x
        assert c.get("fichier") == "RC.txt", c
        assert isinstance(c.get("part"), (int, float)), c


# ═══════════════════════════════════════════════════════════════════════════
#  2. LE SOCLE — ÉTROIT, ET MOTIVÉ
# ═══════════════════════════════════════════════════════════════════════════

def test_un_dossier_muet_ne_rend_JAMAIS_zero():
    """« Aucun document à remplir » serait faux, et faux dans le sens qui fait
    perdre le marché. Un RC qui renvoie au CCAP est fréquent."""
    s, _ = _sel(RC_MUET)
    assert s["retenues"] >= 1, "un dossier muet ne retient rien"
    assert all(x["pourquoi"] == "socle" for x in s["lignes"] if x["retenue"]), (
        "sur un dossier muet, ce qui est retenu doit l'être PAR LE SOCLE — "
        "sinon quelque chose a été repéré dans un texte qui ne dit rien")


def test_le_socle_reste_etroit():
    """LE TÉMOIN NÉGATIF DU SOCLE. Un socle large ramènerait la sélection au
    catalogue entier — le défaut qu'on corrige, rhabillé."""
    catalogue = len(ao_dc.DOSSIER_CANDIDATURE) + len(ao_dc.DOSSIER_OFFRE)
    assert len(ao_dc.SOCLE_REPONSE) <= max(3, catalogue // 6), (
        "le socle porte %d pièces sur %d : ce n'est plus un socle"
        % (len(ao_dc.SOCLE_REPONSE), catalogue))


def test_chaque_piece_du_socle_dit_pourquoi_aucune_consultation_ne_peut_s_en_passer():
    """LE SOCLE N'EST PAS UNE LISTE D'OBLIGATIONS LÉGALES, et le confondre
    ferait écrire une contre-vérité : le code de la commande publique n'impose
    aucun FORMULAIRE, et depuis le DUME le DC1 et le DC2 sont des modèles
    d'usage. Chaque motif doit donc parler de l'INFORMATION demandée, pas
    d'une obligation de support."""
    for cle, motif in ao_dc.SOCLE_REPONSE.items():
        assert len(motif) > 40, (cle, motif)
        interdits = ("obligatoire", "la loi", "le code impose", "imposé par")
        faux = [m for m in interdits if m in motif.lower()]
        assert not faux, (
            "le motif du socle de « %s » se réclame d'une obligation : %r"
            % (cle, faux))


# ═══════════════════════════════════════════════════════════════════════════
#  3. RIEN NE DISPARAÎT, ET LE GESTE DE L'OPÉRATEUR L'EMPORTE
# ═══════════════════════════════════════════════════════════════════════════

def test_une_piece_non_reperee_reste_VISIBLE():
    """Masquer ce qui n'a pas été repéré ferait passer un défaut de
    reconnaissance pour une absence d'exigence."""
    s, _ = _sel(RC_MUET)
    assert s["catalogue"] == len(s["lignes"]), (
        "des lignes ont disparu : %d rendues pour %d au catalogue"
        % (len(s["lignes"]), s["catalogue"]))
    non = [x for x in s["lignes"] if not x["retenue"]]
    assert non, "toutes les pièces sont retenues sur un dossier muet"
    for x in non:
        assert x["nom"], x
        assert x["dossier"] in ("candidature", "offre"), x


def test_l_operateur_peut_ajouter_ce_que_le_moteur_n_a_pas_repere():
    s, _ = _sel(RC_MUET, ajouts=["references"])
    lg = {x["cle"]: x for x in s["lignes"]}
    assert lg["references"]["retenue"] is True
    assert lg["references"]["pourquoi"] == "ajoutee"


def test_ecarter_une_piece_CITEE_laisse_une_trace():
    """RETIRER CE QUE L'ACHETEUR DEMANDE EST UNE DÉCISION, pas un réglage. Le
    geste passe — l'opérateur connaît la consultation, le moteur lit un texte
    — mais il ne s'efface pas."""
    s, _ = _sel(RC_BAVARD, ecartees=["cv"])
    lg = {x["cle"]: x for x in s["lignes"]}
    assert lg["cv"]["retenue"] is False
    assert lg["cv"]["pourquoi"] == "ecartee"
    assert lg["cv"]["contre_citation"] is True, (
        "le CV était cité au dossier : l'écarter doit se voir")
    # ET LE TÉMOIN : écarter une pièce NON citée ne laisse pas cette trace,
    # sinon le signal ne distinguerait plus rien.
    s2, _ = _sel(RC_MUET, ecartees=["cv"])
    lg2 = {x["cle"]: x for x in s2["lignes"]}
    assert lg2["cv"]["contre_citation"] is False, lg2["cv"]


def test_ecarter_l_emporte_sur_ajouter():
    """Deux gestes contradictoires arrivent — l'écran a pu les empiler. Le
    refus l'emporte : retenir une pièce que l'opérateur vient de retirer est
    la surprise la plus désagréable des deux."""
    s, _ = _sel(RC_BAVARD, ajouts=["cv"], ecartees=["cv"])
    lg = {x["cle"]: x for x in s["lignes"]}
    assert lg["cv"]["retenue"] is False, lg["cv"]


# ═══════════════════════════════════════════════════════════════════════════
#  4. CE QUI SE REMPLIT VRAIMENT — LA PROMESSE BORNÉE
# ═══════════════════════════════════════════════════════════════════════════

def test_remplissable_est_LU_sur_le_catalogue_des_modeles():
    """LA CORRESPONDANCE NE SE RECOPIE PAS, ET C'EST MESURÉ.

    Les clés ne coïncident pas : le modèle de l'acte d'engagement s'appelle
    « attri1 », la pièce « acte_engagement ». Un `cle in MODELES` déclarait
    l'acte d'engagement NON remplissable alors qu'il l'est — deux
    remplissables au lieu de trois, mesuré avant correction.
    """
    s, _ = _sel(RC_MUET)
    attendus = {m.get("piece") or c for c, m in ao_formulaires.MODELES.items()}
    for x in s["lignes"]:
        assert x["remplissable"] == (x["cle"] in attendus), x
    assert "acte_engagement" in s["remplissables"], (
        "l'acte d'engagement est déclaré non remplissable alors qu'ATTRI1 "
        "existe : la correspondance pièce → modèle a été recopiée au lieu "
        "d'être lue")


def test_ce_qui_NE_se_remplit_pas_est_compte_a_part():
    """« Sept documents remplis automatiquement » quand trois le sont est la
    promesse la plus facile à démentir de ce module."""
    s, _ = _sel(RC_BAVARD)
    assert set(s["remplissables"]) | set(s["a_produire"]) == {
        x["cle"] for x in s["lignes"] if x["retenue"]}
    assert not (set(s["remplissables"]) & set(s["a_produire"]))
    assert s["a_produire"], (
        "toutes les pièces retenues seraient remplissables : le témoin est "
        "cassé, ou le catalogue des modèles a doublé sans qu'on le sache")


# ═══════════════════════════════════════════════════════════════════════════
#  5. LES DEUX DOSSIERS, ET LE PÉRIMÈTRE QUI EN DÉCOULE
# ═══════════════════════════════════════════════════════════════════════════

def test_chaque_piece_est_rangee_dans_SON_dossier():
    """« Candidature » établit qui vous êtes, « offre » ce que vous proposez.
    Un lecteur qui cherche l'un ne doit pas le trouver rangé sous l'autre."""
    s, _ = _sel(RC_BAVARD)
    cand = {p["cle"] for p in ao_dc.DOSSIER_CANDIDATURE}
    offre = {p["cle"] for p in ao_dc.DOSSIER_OFFRE}
    for x in s["lignes"]:
        attendu = "candidature" if x["cle"] in cand else "offre"
        assert x["dossier"] == attendu, x
        assert x["cle"] in (cand | offre), x
    assert s["par_dossier"]["candidature"] and s["par_dossier"]["offre"], (
        "un des deux dossiers est vide sur un RC qui demande des pièces des "
        "deux : %r" % s["par_dossier"])


def test_le_perimetre_borne_REELLEMENT_le_remplissage():
    """LE PONT ENTRE LA DÉCISION ET L'ÉCRAN. Sans lui, `selection()` serait
    une jolie fonction que personne n'écoute — exactement le sort d'`exigees`.
    """
    s, a = _sel(RC_BAVARD)
    peri = [x["cle"] for x in s["lignes"] if x["retenue"]]
    tout = ao_dc.remplir(fiche={}, analyse=a)
    cible = ao_dc.remplir(fiche={}, analyse=a, perimetre=peri)
    assert len(tout["pieces"]) == s["catalogue"], len(tout["pieces"])
    assert len(cible["pieces"]) == len(peri), (
        "le périmètre demandait %d pièces, le remplissage en rend %d"
        % (len(peri), len(cible["pieces"])))
    assert {p["cle"] for p in cible["pieces"]} == set(peri)


def test_un_perimetre_VIDE_n_est_pas_un_perimetre_ABSENT():
    """LA DISTINCTION QUI FAIT TOUT L'INTÉRÊT DU PARAMÈTRE. Confondre `[]` et
    `None` ferait réapparaître les vingt-trois pièces au moment précis où la
    sélection conclut qu'aucune n'est demandée."""
    a = ao_dc.analyser([{"nom": "RC.txt", "texte": RC_MUET}])
    assert len(ao_dc.remplir(fiche={}, analyse=a, perimetre=[])["pieces"]) == 0
    assert len(ao_dc.remplir(fiche={}, analyse=a, perimetre=None)["pieces"]) == \
        len(ao_dc.DOSSIER_CANDIDATURE) + len(ao_dc.DOSSIER_OFFRE)


def test_deux_appels_sur_le_meme_dossier_rendent_la_meme_selection():
    """Elle ne lit pas l'horloge, et ne garde pas d'état entre deux appels."""
    a = ao_dc.analyser([{"nom": "RC.txt", "texte": RC_BAVARD}])
    assert ao_dc.selection(a) == ao_dc.selection(a)


def test_sans_analyse_la_selection_le_DIT():
    """Un socle rendu sans qu'aucun dossier n'ait été lu se lit comme une
    sélection. Le drapeau existe pour que l'écran puisse le distinguer."""
    s = ao_dc.selection(None)
    assert s["sans_analyse"] is True
    assert s["retenues"] == len(ao_dc.SOCLE_REPONSE)
    s2, _ = _sel(RC_MUET)
    assert s2["sans_analyse"] is False


# ═══════════════════════════════════════════════════════════════════════════
#  6. LES MOTIFS D'EXIGENCE — LES HUIT QUI N'EN AVAIENT AUCUN
# ═══════════════════════════════════════════════════════════════════════════

def test_les_vingt_trois_pieces_ont_TOUTES_un_motif_d_exigence():
    """MESURÉ : huit pièces n'en avaient aucun — dont la déclaration sur
    l'honneur, les CV et la note d'équipe, parmi les plus demandées. Elles ne
    pouvaient donc JAMAIS être repérées : pas « rarement », jamais."""
    catalogue = {p["cle"] for p in ao_dc.DOSSIER_CANDIDATURE + ao_dc.DOSSIER_OFFRE}
    sans = sorted(catalogue - set(ao_dc.EXIGENCES))
    assert not sans, (
        "ces pièces ne peuvent jamais être repérées, faute de motif : %s" % sans)


@pytest.mark.parametrize("cle,phrase", [
    ("dc1", "Les candidats produiront un DC1 et un DC2."),
    ("dc2", "Les candidats produiront un DC1 et un DC2."),
    ("dc1", "Le DC1 sera remis signé par le mandataire."),
    ("dc4", "Le candidat devra joindre un DC4 par sous-traitant."),
    ("honneur", "Une déclaration sur l'honneur attestant l'absence "
                "d'interdiction de soumissionner."),
    ("cv", "Les CV des intervenants clés affectés à la mission."),
    ("equipe", "Une note de présentation de l'équipe dédiée au projet."),
    ("atd_atp", "Justificatifs d'aptitude technique et professionnelle."),
    ("conventions", "La convention collective applicable au personnel."),
    ("repartition_competences", "La répartition des prestations entre les membres."),
    ("autonomie_commerciale", "Attestation d'autonomie commerciale."),
    ("tiers", "Le questionnaire fournisseur de l'acheteur, complété."),
])
def test_les_formulations_reelles_sont_reperees(cle, phrase):
    """LES SIGLES NUS COMPTAIENT, ET ÉTAIENT RATÉS. « Les candidats produiront
    un DC1 et un DC2 » — formulation des plus banales — ne repérait RIEN : les
    motifs exigeaient le mot « formulaire » ou un « candidature » à moins de
    trente caractères."""
    assert ao_dc._extraire(phrase, ao_dc.EXIGENCES[cle], maxi=1), (
        "« %s » ne repère pas %s" % (phrase, cle))


@pytest.mark.parametrize("cle,phrase", [
    ("cv", "Le local technique CVC est situé en toiture."),
    ("equipe", "L'équipement de climatisation est de type DX."),
    ("dc1", "Le plan DC1-03 figure au dossier graphique."),
    ("dc1", "Le lot DC1 comprend les travaux de gros œuvre."),
    ("conventions", "Les conventions de raccordement au réseau public."),
    ("tiers", "Un tiers de confiance horodate les dépôts."),
    ("honneur", "Les travaux font honneur au savoir-faire de l'entreprise."),
    ("atd_atp", "La capacité technique du groupe froid est de 1,2 MW."),
])
def test_les_motifs_elargis_ne_RAMASSENT_pas(cle, phrase):
    """LE TÉMOIN NÉGATIF, SANS LEQUEL UN MOTIF LARGE PASSE POUR UN BON MOTIF.

    Élargir la reconnaissance sans mesurer les faux positifs aurait produit une
    sélection qui retient tout — donc rien. Ces huit phrases portent le mot
    sans porter l'exigence : un CCTP de centre de données parle de CVC, de lots
    DC, de tiers de confiance et de capacité technique à longueur de page.
    """
    assert not ao_dc._extraire(phrase, ao_dc.EXIGENCES[cle], maxi=1), (
        "« %s » est ramassé comme une exigence de %s" % (phrase, cle))
