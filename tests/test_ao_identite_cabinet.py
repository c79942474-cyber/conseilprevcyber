# -*- coding: utf-8 -*-
"""Pourquoi les DC1, DC2, DC4 et l'acte d'engagement sortaient à moitié vides.

CE QUE LE DIAGNOSTIC A ÉTABLI, ET CE QU'IL A DÉMENTI. La plainte visait
l'objet du marché : « il est dans le RC, les formulaires ne sont pas remplis ».
Mesuré de bout en bout — module, formulaires, route — l'objet EST relevé et
EST posé dans les quatre documents. Trois hypothèses tombées.

CE QUI MANQUE VIENT DE L'IDENTITÉ DU CABINET, PAS DU DOSSIER DÉPOSÉ. Mesuré :
`fiche_candidat()` rendait 10 champs sur 20. Et deux valeurs que `IDENTITE`
DÉTIENT — le SIREN et le numéro de TVA, vérifiés cohérents entre eux par la
règle de clé — n'étaient simplement pas recopiées : elles n'atteignaient
jamais un formulaire. En aval, `derive()` savait les déduire, mais À PARTIR DU
SIRET, absent. Deux chemins vers la même valeur, tous deux coupés.

LE RESTE N'EST PAS UN DÉFAUT DE CODE, ET LE DIRE COMPTE. Le DC2 ouvre des
cases pour le RCS, le code NAF et les trois chiffres d'affaires ; personne ne
les a portées au dossier d'entreprise. Aucune correction logicielle ne les
inventera — ce sont des faits sur une entreprise réelle, et un chiffre inventé
dans un formulaire de l'État est une fausse déclaration. Ce qui SE corrige,
c'est le SILENCE : le document sortait à moitié vide sans dire ce qui lui
manquait, et « 7 valeur(s) portée(s) » se lit comme « aussi rempli qu'il peut
l'être ».

MESURE DE RÉFÉRENCE : avec l'identité complète, les quatre formulaires passent
de 25 à 34 valeurs posées.
"""
import io
import os
import re

import pytest

import ao_dc
import ao_formulaires
import dossier_entreprise


#: Un règlement de consultation qui porte tout ce que le relevé sait chercher.
RC = """RÈGLEMENT DE LA CONSULTATION
Pouvoir adjudicateur : COMMUNAUTÉ D'AGGLOMÉRATION DE VAL-D'EUROPE
Objet du marché : construction d'un centre de données de 12 MW — lot 2, CVC.
Référence de la consultation : 2026-DC-0142
La consultation est allotie en 4 lots.
"""

#: Les quatre formulaires de l'État, et le modèle qui les porte.
QUATRE = (("dc1", "dc1"), ("dc2", "dc2"), ("dc4", "dc4"),
          ("attri1", "acte_engagement"))


@pytest.fixture(scope="module")
def analyse():
    return ao_dc.analyser([{"nom": "RC.pdf", "texte": RC, "extension": ".pdf"}])


def _poser(fiche, analyse):
    """Le nombre de valeurs RÉELLEMENT écrites dans les quatre formulaires."""
    r = ao_dc.remplir(fiche=fiche, analyse=analyse)
    total, detail = 0, {}
    for modele, cle in QUATRE:
        _, rap = ao_formulaires.remplir_document(
            modele, ao_formulaires.valeurs_pour(r, cle))
        detail[modele] = [p["rubrique"] for p in rap["places"]]
        total += len(rap["places"])
    return total, detail


# ═══════════════════════════════════════════════════════════════════════════
#  1. CE QUI MARCHAIT DÉJÀ — ET QU'IL FAUT EMPÊCHER DE CASSER
# ═══════════════════════════════════════════════════════════════════════════

def test_l_objet_du_RC_arrive_bien_dans_les_quatre_formulaires(analyse):
    """LA RÈGLE QUI FIXE LE DIAGNOSTIC.

    Elle existe parce que la plainte visait l'objet et que la mesure l'a
    démentie. Sans elle, la prochaine lecture du dossier repartirait sur la
    même fausse piste — et une régression sur ce chemin passerait inaperçue.
    """
    r = ao_dc.remplir(fiche=dossier_entreprise.fiche_candidat()["fiche"],
                      analyse=analyse)
    for modele, cle in QUATRE:
        v = ao_formulaires.valeurs_pour(r, cle)
        objet = v.get("objet_consultation") or v.get("objet_marche")
        assert objet and "centre de données" in objet, (
            "%s ne reçoit pas l'objet relevé au RC : %r" % (modele, v))
        _, rap = ao_formulaires.remplir_document(modele, v)
        poses = {p["rubrique"] for p in rap["places"]}
        assert poses & {"objet_consultation", "objet_marche"}, (
            "%s détient l'objet mais ne l'écrit nulle part" % modele)


# ═══════════════════════════════════════════════════════════════════════════
#  2. LE DÉFAUT CORRIGÉ : DEUX VALEURS DÉTENUES QUI N'ARRIVAIENT NULLE PART
# ═══════════════════════════════════════════════════════════════════════════

def test_le_siren_et_la_tva_detenus_sortent_de_la_fiche():
    """Ils étaient dans `IDENTITE` et `fiche_candidat()` ne les recopiait pas.

    On mesure la SORTIE de la fonction, pas la présence d'une ligne : une clé
    ajoutée au dictionnaire d'entrée sans être rendue laisserait une règle de
    présence verte et le formulaire vide.
    """
    ident = dossier_entreprise.IDENTITE
    f = dossier_entreprise.fiche_candidat()["fiche"]
    for cle in ("siren", "tva"):
        assert ident.get(cle), (
            "l'identité ne porte plus %s : la règle n'éprouve plus rien" % cle)
        assert f.get(cle) == str(ident[cle]).strip(), (
            "%s est détenu (%r) et ne sort pas de la fiche (%r)"
            % (cle, ident.get(cle), f.get(cle)))


def test_le_siren_et_la_tva_declares_sont_coherents_entre_eux():
    """UN TÉMOIN QUI GARDE LA DONNÉE, PAS LE CODE.

    La clé de TVA se calcule depuis le SIREN. Deux valeurs déclarées qui ne
    se répondent pas signifient qu'au moins une est fausse — et une TVA fausse
    sur un DC2 se corrige après coup, mal.
    """
    siren = re.sub(r"\D", "", str(dossier_entreprise.IDENTITE.get("siren") or ""))
    tva = re.sub(r"[^0-9A-Z]", "",
                 str(dossier_entreprise.IDENTITE.get("tva") or "").upper())
    assert len(siren) == 9, siren
    cle = (12 + 3 * (int(siren) % 97)) % 97
    assert tva == "FR%02d%s" % (cle, siren), (
        "la TVA déclarée %r ne correspond pas au SIREN déclaré %r" % (tva, siren))


def test_la_tva_se_deduit_du_siren_seul():
    """La règle de clé ne demande QUE le SIREN ; `derive` exigeait un SIRET.

    C'est le cas réel : l'avis INSEE donne le SIREN, le NIC se cherche. Perdre
    la TVA en attendant cinq chiffres dont elle ne dépend pas était gratuit.
    """
    d = ao_dc.derive({"siren": "494530157"})
    assert d.get("tva", {}).get("valeur") == "FR24494530157", d
    assert "SIREN" in d["tva"]["regle"], d["tva"]["regle"]


def test_une_tva_deja_declaree_n_est_pas_recalculee():
    """UNE VALEUR DÉCLARÉE L'EMPORTE SUR UNE VALEUR CALCULÉE.

    Elle se vérifie sur un document ; la déduction, non. Recalculer par-dessus
    écraserait en silence une valeur que quelqu'un a lue sur une pièce.
    """
    d = ao_dc.derive({"siren": "494530157", "tva": "FR 24 494 530 157"})
    assert "tva" not in d, d


def test_le_siret_reste_le_chemin_qui_donne_les_deux():
    """LE TÉMOIN INVERSE : le SIRET rend le SIREN ET la TVA. Sans lui, la
    règle précédente passerait sur un `derive` qui aurait perdu le SIRET."""
    d = ao_dc.derive({"siret": "73282932000074"})
    assert d["siren"]["valeur"] == "732829320", d
    assert d["tva"]["valeur"] == "FR44732829320", d


# ═══════════════════════════════════════════════════════════════════════════
#  3. LE SILENCE CESSE : LE DOCUMENT DIT CE QUI LUI MANQUE
# ═══════════════════════════════════════════════════════════════════════════

def test_le_dc2_nomme_ses_cases_ouvertes_et_vides(analyse):
    """LA RÈGLE DÉCISIVE DE CE FICHIER.

    Le DC2 ouvre des cases pour le SIRET, le RCS, le code NAF et les trois
    chiffres d'affaires. Faute de valeur, elles restaient vides EN SILENCE.
    On mesure que chacune est nommée, et qu'elle porte où la trouver.
    """
    r = ao_dc.remplir(fiche=dossier_entreprise.fiche_candidat()["fiche"],
                      analyse=analyse)
    piece = next(p for p in r["pieces"] if p["cle"] == "dc2")
    vides = ao_formulaires.cases_vides("dc2", piece,
                                       dossier_entreprise.OU_TROUVER)
    cles = {c["cle"] for c in vides}
    assert {"rcs", "naf", "ca_n1", "ca_n2", "ca_n3"} <= cles, sorted(cles)
    for c in vides:
        if c["source"] == "fiche":
            assert c["ou_trouver"], (
                "« %s » manque sans dire où le trouver" % c["cle"])
            assert c["libelle"] and c["libelle"] != c["cle"], c


def test_les_manques_sont_classes_par_ce_qui_les_corrige(analyse):
    """TROIS MANQUES QUI NE SE CORRIGENT PAS PAREIL.

    Une donnée d'identité se cherche une fois sur un Kbis ; une valeur non
    relevée se lit dans la pièce déposée ; une saisie se DÉCIDE pour cette
    consultation. Les mêler enverrait chercher dans un Kbis un montant qui se
    décide — et c'est précisément ce qu'une liste indifférenciée ferait.
    """
    r = ao_dc.remplir(fiche=dossier_entreprise.fiche_candidat()["fiche"],
                      analyse=analyse)
    piece = next(p for p in r["pieces"] if p["cle"] == "acte_engagement")
    vides = ao_formulaires.cases_vides("attri1", piece,
                                       dossier_entreprise.OU_TROUVER)
    par_source = {}
    for c in vides:
        par_source.setdefault(c["source"], set()).add(c["cle"])
    assert "siret" in par_source.get("fiche", set()), par_source
    assert par_source.get("saisie"), (
        "aucune saisie propre à la consultation : le classement ne distingue "
        "plus rien — %r" % par_source)
    # ET LE TÉMOIN : une saisie ne porte JAMAIS un « où le trouver ». Elle ne
    # se trouve pas, elle se décide.
    for c in vides:
        if c["source"] == "saisie":
            assert not c["ou_trouver"], c


def test_une_case_deja_remplie_n_est_pas_annoncee_comme_vide(analyse):
    """LE TÉMOIN NÉGATIF. Sans lui, une fonction qui rendrait TOUTES les
    rubriques ancrées passerait la règle ci-dessus — et la liste de travail
    deviendrait du bruit."""
    r = ao_dc.remplir(fiche=dossier_entreprise.fiche_candidat()["fiche"],
                      analyse=analyse)
    piece = next(p for p in r["pieces"] if p["cle"] == "dc2")
    vides = {c["cle"] for c in ao_formulaires.cases_vides("dc2", piece)}
    remplies = {l["cle"] for l in piece["rubriques"] if l["statut"] == "rempli"}
    assert remplies, "le témoin est cassé : plus rien n'est rempli"
    assert not (vides & remplies), sorted(vides & remplies)


def test_on_ne_nomme_que_ce_que_CE_formulaire_sait_ecrire(analyse):
    """Une valeur manquante SANS case ouverte ne coûte rien sur ce document.

    L'annoncer ferait chercher un remède sans effet — et noierait les lignes
    qui, elles, font vraiment avancer la pièce.
    """
    r = ao_dc.remplir(fiche={}, analyse=analyse)
    piece = next(p for p in r["pieces"] if p["cle"] == "dc1")
    ancrees = {a["rubrique"] for a in ao_formulaires.ANCRES["dc1"]}
    vides = {c["cle"] for c in ao_formulaires.cases_vides("dc1", piece)}
    assert vides <= ancrees, sorted(vides - ancrees)
    assert vides, "un DC1 sans aucune fiche devrait avoir des cases vides"


# ═══════════════════════════════════════════════════════════════════════════
#  4. CE QUE COMPLÉTER L'IDENTITÉ RAPPORTERAIT — MESURÉ
# ═══════════════════════════════════════════════════════════════════════════

def test_completer_l_identite_remplit_neuf_cases_de_plus(analyse):
    """LE CHIFFRE QUI RÉPOND À « POURQUOI CE N'EST PAS REMPLI ».

    Il ne mesure pas le code : il mesure ce que porter dix valeurs sur un Kbis,
    un avis INSEE et une liasse fiscale ferait gagner. C'est la seule façon
    d'arbitrer entre « corriger le programme » et « porter les données », et
    la réponse ici est la seconde.
    """
    reel = dossier_entreprise.fiche_candidat()["fiche"]
    complet = dict(reel, siret="49453015700028", rcs="RCS Paris 494 530 157",
                   naf="7022Z", effectif="3", ca_n1="180 000 €",
                   ca_n2="165 000 €", ca_n3="150 000 €",
                   assurance_compagnie="—", assurance_police="—",
                   assurance_echeance="31/12/2026")
    avant, _ = _poser(reel, analyse)
    apres, detail = _poser(complet, analyse)
    assert apres - avant >= 8, (
        "compléter l'identité ne rapporte que %d case(s) : le diagnostic "
        "n'est plus celui que ce fichier décrit" % (apres - avant))
    assert "siret" in detail["dc1"], detail["dc1"]
    assert {"rcs", "naf", "ca_n1"} <= set(detail["dc2"]), detail["dc2"]


def test_les_valeurs_qui_manquent_ne_sont_JAMAIS_inventees():
    """LA RÈGLE QUI INTERDIT LE REMÈDE FACILE.

    Un SIRET, un RCS, un code NAF ou un chiffre d'affaires sont des faits sur
    une entreprise réelle. Les porter en dur pour faire verdir un écran
    mettrait une fausse déclaration dans un formulaire de l'État. Ce qui n'est
    pas connu reste None, et `fiche_candidat` le range dans `manques`.
    """
    f = dossier_entreprise.fiche_candidat()
    manques = {m["cle"] for m in f["manques"]}
    for cle in ("siret", "rcs", "naf", "ca_n1"):
        assert cle not in f["fiche"] or f["fiche"][cle], (
            "%s est présent mais vide : une valeur vide passe pour une "
            "réponse" % cle)
        if cle not in f["fiche"]:
            assert cle in manques, (
                "%s manque sans être déclaré manquant" % cle)
            assert dossier_entreprise.OU_TROUVER.get(cle), (
                "%s manque sans dire où le chercher" % cle)
