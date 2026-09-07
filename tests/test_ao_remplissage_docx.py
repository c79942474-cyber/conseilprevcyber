# -*- coding: utf-8 -*-
"""Le formulaire OFFICIEL est rempli dans son propre fichier — jamais redessiné,
jamais signé.

CE QUI SÉPARE CE MODULE D'UN FAC-SIMILÉ. Un formulaire redessiné par un
programme serait refusé par l'acheteur — ou pire, accepté et faux. Ici, on
ouvre le fichier du ministère, dans sa version, avec sa mise en page et sa date
de mise à jour, et l'on écrit dans les emplacements qu'il laisse vides. Ce qui
sort reste le formulaire officiel.

CES RÈGLES MESURENT LE DOCUMENT PRODUIT, pas le code qui le produit. Elles
l'ouvrent, le comparent au modèle paragraphe par paragraphe, et vérifient que
chaque valeur est sous LE BON intitulé. Vérifier qu'une valeur est « quelque
part dans le document » serait vert pour une valeur déposée dans le mauvais
cadre — c'est-à-dire pour la faute qui compte.

LE PIÈGE PROPRE AU DC4, ET IL EST RÉEL. Les cadres D et E portent les mêmes
intitulés mot pour mot — « Adresse électronique : », « Numéro SIRET… », « Nom
commercial et dénomination sociale… ». L'un identifie le TITULAIRE, l'autre le
SOUS-TRAITANT. Une ancre sans rang déposerait le SIRET du titulaire dans la
case du sous-traitant : une case pleine, plausible, et fausse.
"""
import io
import os
import shutil
import sys
import tempfile

import docx
import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc                                                     # noqa: E402
import ao_formulaires as F                                       # noqa: E402

RC = """RÈGLEMENT DE LA CONSULTATION
Pouvoir adjudicateur : Communauté d'agglomération de l'Essai.
Objet du marché : maîtrise d'œuvre pour un centre de données régional.
Référence de la consultation : 2026-MOE-014.
La consultation est allotie en 3 lots.
"""

FICHE = {"raison_sociale": "Bureau d'études Essai", "forme_juridique": "SAS",
         "siret": "80295478500019", "adresse": "5 rue de l'Essai, 75001 Paris",
         "courriel": "contact@essai.example",
         "representant_nom": "A. Dupont", "representant_qualite": "Président"}

SAISIES = {
    "dc4.sous_traitance": "oui — lot 3",
    "dc4.sous_traitant": "Froid Concept SARL — 59000 Lille — SIRET 51234567800021",
    "dc4.sous_traitant_pouvoir": "M. Martin, gérant",
    "dc4.prestations": "Génie climatique — lot 3",
    "dc4.montant": "TVA 20 % · 84 000 € HT",
    "dc4.compte": "Banque Essai — FR76 1234 5678 9012",
    "dc4.duree_sous_traitance": "8 mois",
}


def _net(s):
    return " ".join((s or "").replace("’", "'").split())


def _paras(source):
    """Les paragraphes DANS L'ORDRE DU DOCUMENT, cellules de tableau comprises.

    ON LIT COMME LE MOTEUR ÉCRIT, et c'est une correction. Ces règles
    passaient par `docx.Document(...).paragraphs`, qui ignore les paragraphes
    vivant dans un tableau : les indices rendus par le rapport ne désignaient
    plus les mêmes lignes, et la règle tombait pour un décalage de
    référentiel — pas pour une valeur mal placée.
    """
    return [_net(p.text) for p in F.paragraphes(docx.Document(source))]


def _produit(saisies=None):
    an = ao_dc.analyser([{"nom": "01_RC.pdf", "texte": RC}])
    r = ao_dc.remplir(fiche=FICHE, analyse=an,
                      saisies=SAISIES if saisies is None else saisies)
    octets, rapport = F.remplir_document("dc4", F.valeurs_pour(r, "dc4"))
    assert octets, rapport
    return octets, rapport


@pytest.fixture(scope="module")
def document():
    octets, rapport = _produit()
    return _paras(io.BytesIO(octets)), _paras(F.chemin_modele("dc4")), rapport


# ══════════════════════════════════════════════════════════════════════════
# 1. CHAQUE VALEUR SOUS LE BON INTITULÉ — LE PIÈGE DES CADRES D ET E
# ══════════════════════════════════════════════════════════════════════════

# L'INTITULÉ ATTENDU DEVANT CHAQUE VALEUR, relevé sur le formulaire. C'est ce
# qui distingue « la valeur est dans le document » de « la valeur est au bon
# endroit » — et seule la seconde question a un intérêt.
DEVANT = {
    "titulaire": "Nom commercial et dénomination sociale",
    "titulaire_adresse": "Adresses postale et du siège social",
    "titulaire_courriel": "Adresse électronique :",
    "titulaire_siret": "Numéro SIRET",
    "titulaire_forme": "Forme juridique du soumissionnaire individuel",
    "sous_traitant": "Nom commercial et dénomination sociale",
    "sous_traitant_pouvoir": "(Indiquer le nom, prénom et la qualité",
    "prestations": "Nature des prestations sous-traitées :",
    "montant": "Montant des prestations sous-traitées :",
    "compte": "Nom de l'établissement bancaire",
    "duree_sous_traitance": "La durée du contrat de sous-traitance en nombre",
}


def test_chaque_valeur_est_ecrite_sous_son_propre_intitule(document):
    """« Présente dans le document » ne veut rien dire : une valeur déposée
    dans le mauvais cadre y serait présente aussi."""
    out, _mod, rapport = document
    par_rubrique = {x["rubrique"]: x for x in rapport["places"]}
    for rubrique, intitule in DEVANT.items():
        assert rubrique in par_rubrique, (
            "%s n'a pas été placée : %s" % (rubrique, rapport["non_places"]))
        i = par_rubrique[rubrique]["paragraphe"] + 1     # le bandeau décale
        avant = [t for t in out[max(0, i - 4):i] if t]
        assert avant, (rubrique, i)
        assert _net(intitule) in avant[-1], (
            "« %s » est écrite sous « %s » au lieu de « %s »"
            % (rubrique, avant[-1][:70], intitule))


def test_le_titulaire_va_au_cadre_D_et_le_sous_traitant_au_cadre_E(document):
    """LE PIÈGE DE CE FORMULAIRE, ET IL EST RÉEL. Les deux cadres portent les
    mêmes intitulés, mot pour mot. Une ancre sans rang mettrait l'identité du
    titulaire dans la case du sous-traitant : pleine, plausible, fausse — et
    un DC4 qui présente le titulaire comme son propre sous-traitant ne
    présente aucun sous-traitant."""
    out, _mod, rapport = document
    d = next(i for i, t in enumerate(out) if t.startswith("D - Identification"))
    e = next(i for i, t in enumerate(out) if t.startswith("E - Identification"))
    f = next(i for i, t in enumerate(out) if t.startswith("F - Nature"))
    assert d < e < f, (d, e, f)
    par_rubrique = {x["rubrique"]: x["paragraphe"] + 1
                    for x in rapport["places"]}
    for rubrique in ("titulaire", "titulaire_adresse", "titulaire_courriel",
                     "titulaire_siret", "titulaire_forme"):
        assert d < par_rubrique[rubrique] < e, (
            "« %s » est sortie du cadre D (¶%d, cadres D=%d E=%d)"
            % (rubrique, par_rubrique[rubrique], d, e))
    for rubrique in ("sous_traitant", "sous_traitant_pouvoir"):
        assert e < par_rubrique[rubrique] < f, (
            "« %s » n'est pas dans le cadre E (¶%d, cadres E=%d F=%d)"
            % (rubrique, par_rubrique[rubrique], e, f))
    # ET LES DEUX IDENTITÉS SONT BIEN DISTINCTES DANS LE DOCUMENT.
    assert out[par_rubrique["titulaire"]] != out[par_rubrique["sous_traitant"]]


# ══════════════════════════════════════════════════════════════════════════
# 2. ON N'ÉCRIT QUE DANS DU VIDE — L'INVARIANT, PAS L'INTENTION
# ══════════════════════════════════════════════════════════════════════════

def test_aucun_paragraphe_porteur_de_texte_n_est_ecrase(document):
    """C'est ce qui rend STRUCTURELLEMENT impossible d'écraser une mention
    légale, un intitulé de cadre ou une déclaration : elles portent du texte.
    Une liste noire de zones à éviter serait une énumération, donc oubliable ;
    ceci est un invariant."""
    out, mod, _r = document
    assert len(out) == len(mod) + 1, "le bandeau doit ajouter UN paragraphe"
    for i in range(1, len(out)):
        if out[i] == mod[i - 1]:
            continue
        assert F._emplacement_libre(mod[i - 1]), (
            "¶%d portait « %s » et a été écrasé par « %s »"
            % (i, mod[i - 1][:60], out[i][:60]))


def test_rien_n_est_ecrit_dans_les_declarations_ni_dans_les_signatures(document):
    """La seconde barrière, et elle protège du BLANC là où la première protège
    du texte : les blocs de signature contiennent des lignes vides, qu'une
    ancre qui glisserait pourrait remplir."""
    out, mod, _r = document
    k = next(i for i, t in enumerate(out)
             if t.startswith("K1 - Le sous-traitant déclare sur l'honneur"))
    m = next(i for i, t in enumerate(out) if t.startswith("M - Acceptation"))
    assert k < m, (k, m)
    modifies = [i for i in range(1, len(out)) if out[i] != mod[i - 1]]
    assert modifies, "rien n'a été écrit : la règle ne mesure rien"
    assert [i for i in modifies if i >= k] == [], (
        "des valeurs ont été écrites dans la zone de déclaration ou de "
        "signature : %s" % [i for i in modifies if i >= k])


def test_un_paragraphe_de_cellule_fusionnee_n_entre_qu_UNE_fois():
    """UNE CELLULE FUSIONNÉE EST RENDUE PLUSIEURS FOIS PAR `row.cells`, et le
    même paragraphe entrerait deux fois dans la liste du document — assez pour
    qu'une valeur soit écrite deux fois, ou qu'un indice « déjà pris » en
    écarte un autre.

    ET CE N'EST PAS UNE PRÉCAUTION THÉORIQUE : le DC2 en compte deux, l'ATTRI1
    quatre. Une batterie de mutations a d'abord montré que retirer le
    dédoublonnage ne faisait tomber aucune règle — la mesure ci-dessous
    existe parce qu'il n'y en avait aucune.
    """
    vus_par_modele = {}
    for cle in sorted(F.MODELES):
        blocs = F.paragraphes(docx.Document(F.chemin_modele(cle)))
        elements = [id(b._p) for b in blocs]
        assert len(elements) == len(set(elements)), (
            "%s : %d paragraphe(s) rendu(s) deux fois"
            % (cle, len(elements) - len(set(elements))))
        vus_par_modele[cle] = len(blocs)
    # LE TÉMOIN QUI PROUVE QUE LA RÈGLE MORD, et il a fallu le corriger : je
    # comptais d'abord les fusions HORIZONTALES, ligne par ligne — il n'y en a
    # qu'une. L'écart réel vient aussi des fusions VERTICALES, où la même
    # cellule reparaît d'une ligne à l'autre. Ce qu'il faut mesurer, c'est
    # donc ce que le dédoublonnage RETIRE, pas une forme particulière de
    # fusion : on refait le parcours sans lui et on compare.
    from docx.table import Table                                # noqa: PLC0415
    from docx.text.paragraph import Paragraph                   # noqa: PLC0415

    def _naif(doc):
        out = []

        def _p(parent, el):
            for e in el.iterchildren():
                if e.tag.endswith("}p"):
                    out.append(Paragraph(e, parent))
                elif e.tag.endswith("}tbl"):
                    for ligne in Table(e, parent).rows:
                        for c in ligne.cells:
                            _p(c, c._tc)
        _p(doc, doc.element.body)
        return out

    doublons = {cle: len(_naif(docx.Document(F.chemin_modele(cle))))
                - vus_par_modele[cle] for cle in vus_par_modele}
    assert sum(doublons.values()) >= 2, (
        "aucun paragraphe n'est rendu deux fois sans le dédoublonnage : le "
        "témoin de cette règle a disparu — %s" % doublons)
    assert doublons["dc2"] and doublons["attri1"], doublons


@pytest.mark.parametrize("cle,ancre", [
    ("attri1", "C - Signature du marché public"),
    ("dc1", "F1 – Exclusions de la procédure"),
    ("dc4", "K1 - Le sous-traitant déclare sur l’honneur"),
])
def test_une_ancre_qui_viserait_une_signature_ou_une_declaration_ne_place_RIEN(
        cle, ancre):
    """LA BARRIÈRE QUI PROTÈGE LE BLANC, éprouvée sur les trois formulaires
    qui portent une déclaration ou une signature.

    Une batterie de mutations a montré que la retirer ne faisait tomber
    AUCUNE règle : sur ces documents, l'invariant « on n'écrit que dans du
    vide » suffit tant que les ancres ne s'égarent pas. Mais les blocs de
    signature CONTIENNENT des lignes vides — 132 paragraphes interdits à
    l'ATTRI1, 32 au DC4 — et une ancre qui glisserait y écrirait. On le
    provoque, avec son témoin.
    """
    paras = [pa.text for pa in
             F.paragraphes(docx.Document(F.chemin_modele(cle)))]
    interdits = F._zones_interdites(paras, cle)
    assert interdits, cle
    assert F._cible(paras, interdits, set(), ancre, 1) is None, (
        "%s : une ancre visant une zone de signature ou de déclaration a "
        "trouvé un emplacement" % cle)
    sans = F._cible(paras, set(), set(), ancre, 1)
    assert sans is not None and sans in interdits, (
        "%s : sans la barrière, cette ancre ne place rien non plus — la règle "
        "serait verte pour une raison sans rapport avec ce qu'elle mesure"
        % cle)


def test_le_DC2_n_a_ni_declaration_ni_signature_et_le_dit():
    """L'ABSENCE D'ENTRÉE DANS LA TABLE EST UN CONSTAT, PAS UN OUBLI. Le DC2
    ne porte ni déclaration sur l'honneur ni bloc de signature — elles vivent
    au DC1. Une règle le vérifie sur le document, faute de quoi on ne saurait
    pas distinguer « rien à protéger » de « protection oubliée »."""
    assert "dc2" not in F.ZONES_INTERDITES
    paras = [F._net(pa.text) for pa in
             F.paragraphes(docx.Document(F.chemin_modele("dc2")))]
    for interdit in ("declare sur l'honneur", "Signature", "signataire"):
        assert not any(interdit.lower() in t.lower() for t in paras), (
            "le DC2 porte « %s » : il lui faut une zone interdite" % interdit)
    # ET LES TROIS AUTRES EN PORTENT, sinon la distinction ne sépare rien.
    assert set(F.ZONES_INTERDITES) == {"dc1", "attri1", "dc4"}


def test_une_ancre_qui_viserait_une_declaration_ne_place_RIEN():
    """LA SECONDE BARRIÈRE, ET LA SEULE MESURE QUI PROUVE QU'ELLE SERT.

    Une batterie de mutations a montré que la retirer ne faisait tomber
    AUCUNE règle : sur ce formulaire, l'invariant « on n'écrit que dans du
    vide » suffit à protéger les déclarations, qui portent du texte. Une
    barrière qu'aucune règle ne distingue est une barrière qu'on ne peut pas
    revendiquer — et qu'on supprimerait un jour en croyant nettoyer.

    Ce qu'elle protège, c'est le BLANC : le cadre K1 contient des lignes
    vides, et une ancre qui les viserait y écrirait. On le vérifie avec son
    témoin — sans la barrière, la valeur atterrit bien dans le bloc des
    déclarations.
    """
    paras = [pa.text for pa in docx.Document(F.chemin_modele("dc4")).paragraphs]
    interdits = F._zones_interdites(paras, "dc4")
    ancre = "K1 - Le sous-traitant déclare sur l’honneur"
    assert F._cible(paras, interdits, set(), ancre, 1) is None, (
        "une ancre visant la déclaration sur l'honneur a trouvé un "
        "emplacement : la barrière ne protège rien")
    sans = F._cible(paras, set(), set(), ancre, 1)
    assert sans is not None and sans in interdits, (
        "sans la barrière, cette ancre ne place rien non plus : la règle "
        "serait verte pour une raison sans rapport avec ce qu'elle mesure")


def test_le_remplissage_ne_franchit_jamais_l_intitule_du_cadre_suivant():
    """L'AUTRE ARRÊT, ET IL EST INERTE SUR CE FORMULAIRE-CI — la même batterie
    l'a montré : tous les cadres du DC4 offrent une ligne libre, si bien
    qu'aucune ancre ne cherche au-delà du sien.

    Il n'en est pas moins nécessaire, et il le deviendra visiblement avec les
    trois autres formulaires. On le mesure donc SUR LE MÉCANISME plutôt que
    sur ce document : `_cible()` travaille sur une liste de paragraphes, et
    rien n'oblige à fabriquer un fichier Word pour éprouver une règle de
    parcours.
    """
    ancre = "Nature des prestations sous-traitées :"
    # Le premier emplacement libre est DERRIÈRE l'intitulé du cadre suivant.
    barre = [ancre, "(une note qui occupe la place)",
             "G - Prix des prestations sous-traitées", ""]
    assert F._cible(barre, set(), set(), ancre, 1) is None, (
        "la valeur a franchi l'intitulé du cadre suivant et se serait "
        "déposée dans un cadre qui ne l'attend pas")
    # LE TÉMOIN : le même cas sans cadre interposé place bien la valeur.
    libre = [ancre, "(une note qui occupe la place)", "(une seconde note)", ""]
    assert F._cible(libre, set(), set(), ancre, 1) == 3


def test_une_declaration_ne_peut_pas_etre_ecrite_meme_si_une_ancre_la_designe():
    """LA TROISIÈME BARRIÈRE, POSÉE EN AMONT DES DEUX AUTRES. `valeurs_pour()`
    ne retient que le statut « rempli » ; une déclaration est toujours
    `a_declarer` et sans valeur. Elle ne peut donc pas entrer dans le
    document, même si la table d'ancres la nommait."""
    an = ao_dc.analyser([{"nom": "01_RC.pdf", "texte": RC}])
    r = ao_dc.remplir(fiche=FICHE, analyse=an, saisies=SAISIES)
    vals = F.valeurs_pour(r, "dc4")
    piece = [p for p in r["pieces"] if p["cle"] == "dc4"][0]
    declarations = [l["cle"] for l in piece["rubriques"]
                    if l["source"] == "declaration"]
    assert declarations, "aucune déclaration : le témoin de la règle a disparu"
    for cle in declarations:
        assert cle not in vals, cle
    # ET LE TÉMOIN POSITIF : ce qui est « rempli » passe, sinon la règle
    # serait verte devant une fonction qui ne rend jamais rien.
    assert vals.get("titulaire") == FICHE["raison_sociale"], vals


# ══════════════════════════════════════════════════════════════════════════
# 3. LE MODÈLE EST ÉPINGLÉ — UN FICHIER QUI A BOUGÉ FAIT REFUSER
# ══════════════════════════════════════════════════════════════════════════

def test_le_modele_du_depot_est_bien_celui_qui_a_ete_ancre():
    """Les ancres sont des phrases de CE fichier-ci. Un formulaire mis à jour
    les déplace, les reformule ou les supprime — et le remplissage écrirait à
    côté, sans rien signaler."""
    etat = F.modeles_disponibles()
    assert etat["manquants"] == [] and etat["alteres"] == [], etat
    # LES QUATRE FORMULAIRES DE L'ÉTAT, et chacun couvre une pièce du dossier.
    assert etat["prets"] == ["attri1", "dc1", "dc2", "dc4"], etat["prets"]
    for cle, m in F.MODELES.items():
        assert F.empreinte(F.chemin_modele(cle)) == m["empreinte"], cle
        assert m["piece"] in {p["cle"] for p in
                              ao_dc.DOSSIER_CANDIDATURE + ao_dc.DOSSIER_OFFRE}, cle


def test_un_modele_altere_fait_refuser_le_remplissage(tmp_path, monkeypatch):
    """ON PROVOQUE L'ALTÉRATION plutôt que de constater l'accord. Vérifier que
    l'empreinte concorde aujourd'hui ne dit rien de ce qui arriverait demain :
    seule cette règle prouve que la garde REFUSE."""
    faux = tmp_path / "modeles"
    faux.mkdir()
    shutil.copy(F.chemin_modele("dc4"), str(faux / "DC4.docx"))
    with io.open(str(faux / "DC4.docx"), "ab") as f:
        f.write(b"\n")                       # un octet suffit
    monkeypatch.setattr(F, "DOSSIER_MODELES", str(faux))
    octets, rapport = F.remplir_document("dc4", {"titulaire": "Essai"})
    assert octets is None
    assert rapport["ok"] is False and rapport["motif"] == "modele_altere"
    assert rapport["trouvee"] != rapport["attendue"]
    assert F.modeles_disponibles()["alteres"] == ["dc4"]


def test_un_modele_absent_est_dit_absent_et_non_altere(tmp_path, monkeypatch):
    """Les confondre enverrait chercher une corruption là où il n'y a qu'un
    fichier à déposer — et c'est exactement l'état des trois autres
    formulaires tant qu'ils ne sont pas fournis en .docx."""
    vide = tmp_path / "aucun"
    vide.mkdir()
    monkeypatch.setattr(F, "DOSSIER_MODELES", str(vide))
    octets, rapport = F.remplir_document("dc4", {"titulaire": "Essai"})
    assert octets is None and rapport["motif"] == "modele_absent"
    etat = F.modeles_disponibles()
    assert etat["manquants"] == sorted(F.MODELES) and etat["alteres"] == []


# ══════════════════════════════════════════════════════════════════════════
# 4. LE DOCUMENT DIT CE QU'IL EST, ET LE RAPPORT DIT CE QUI MANQUE
# ══════════════════════════════════════════════════════════════════════════

def test_le_document_porte_en_tete_qu_il_n_est_ni_signe_ni_verifie(document):
    """Un document qui circule sans dire cela finirait par être déposé tel
    quel. Le bandeau est POSÉ DEVANT le formulaire, jamais inséré dans un
    cadre : le formulaire officiel n'est pas altéré, il est précédé."""
    out, _mod, _r = document
    assert out[0] == _net(F.BANDEAU), out[0][:80]
    for mot in ("NON SIGNÉ", "NON VÉRIFIÉ", "PROJET"):
        assert mot in F.BANDEAU, mot


def test_le_bandeau_seul_ne_touche_a_RIEN_d_autre_dans_le_formulaire():
    """LA MESURE QUI LE PROUVE, ET C'EST UNE CORRECTION. La règle précédente
    comparait le document REMPLI au modèle et exigeait qu'ils soient
    identiques après le bandeau — elle tombait pour les valeurs écrites,
    c'est-à-dire pour une raison sans rapport avec ce qu'elle prétendait
    mesurer. Ce qu'il fallait comparer, c'est un document SANS VALEUR : là,
    l'écart doit être exactement d'un paragraphe, en tête, et rien d'autre.
    """
    octets, rapport = F.remplir_document("dc4", {})
    assert rapport["ok"] and rapport["places"] == [], rapport
    sans = _paras(io.BytesIO(octets))
    modele = _paras(F.chemin_modele("dc4"))
    assert sans[0] == _net(F.BANDEAU)
    assert sans[1:] == modele, (
        "le bandeau seul a modifié %d autre(s) paragraphe(s)"
        % sum(1 for a, b in zip(sans[1:], modele) if a != b))


def test_sans_bandeau_le_formulaire_ressort_octet_pour_octet_inchange():
    """LE TÉMOIN NÉGATIF de la règle précédente : sans bandeau ni valeur, le
    document produit doit être le modèle. Sans lui, la comparaison ne dirait
    pas si c'est le bandeau qui ajoute le paragraphe ou le remplissage."""
    octets, _r = F.remplir_document("dc4", {}, bandeau=None)
    assert _paras(io.BytesIO(octets)) == _paras(F.chemin_modele("dc4"))


def test_le_rapport_nomme_ce_qui_n_a_PAS_ete_place():
    """Un formulaire rendu sans dire ce qui manque se lit comme un formulaire
    complet. On provoque une ancre introuvable et on mesure que le rapport la
    nomme au lieu de la perdre."""
    garde = list(F.ANCRES["dc4"])
    try:
        F.ANCRES["dc4"] = garde + [{"rubrique": "titulaire",
                                    "ancre": "Un intitulé qui n'existe pas"}]
        _octets, rapport = _produit()
        manques = [x["rubrique"] for x in rapport["non_places"]]
        assert manques == ["titulaire"], rapport["non_places"]
        assert rapport["non_places"][0]["motif"] == "emplacement_introuvable"
    finally:
        F.ANCRES["dc4"] = garde
    assert _produit()[1]["non_places"] == [], "la table n'a pas été remise"


def test_une_rubrique_sans_valeur_est_ignoree_et_non_placee_a_vide(document):
    """Écrire une chaîne vide dans une case la ferait passer pour renseignée.
    Ce qui n'a pas de valeur ressort dans `ignores`, avec son motif."""
    _out, _mod, rapport = document
    ancrees = {a["rubrique"] for a in F.ANCRES["dc4"]}
    traitees = {x["rubrique"] for x in
                rapport["places"] + rapport["non_places"] + rapport["ignores"]}
    assert traitees == ancrees, ancrees - traitees
    for x in rapport["ignores"]:
        assert x["motif"] == "sans_valeur", x
    for x in rapport["places"]:
        assert str(x["valeur"]).strip(), x


def test_le_rapport_dit_quelle_version_du_formulaire_a_ete_remplie(document):
    """Le formulaire porte lui-même sa date de mise à jour en dernière page.
    La rendre permet de dire au client quelle version il dépose — et de
    constater qu'elle a vieilli."""
    out, _mod, rapport = document
    assert rapport["maj"] == "12/10/2023", rapport["maj"]
    assert any(rapport["maj"] in t for t in out), (
        "la date annoncée par la table ne figure pas dans le document : "
        "elle a été recopiée au lieu d'être relevée sur le formulaire")
    assert "ministère" in rapport["source"], rapport["source"]


# ══════════════════════════════════════════════════════════════════════════
# 5. LA ROUTE — CE QUI SORT DU SERVEUR EST BIEN LE FORMULAIRE OFFICIEL
# ══════════════════════════════════════════════════════════════════════════

ORIGINE = {"Origin": "http://localhost"}
CORPS = {"modele": "dc4", "fiche": FICHE, "saisies": SAISIES}


def test_un_visiteur_anonyme_ne_remplit_aucun_formulaire(anonyme):
    """La route reçoit une fiche d'entreprise et rend un document nominatif."""
    for chemin, methode in (("/api/datacenter/marche/formulaire", "post"),
                            ("/api/datacenter/marche/formulaires", "get")):
        r = getattr(anonyme, methode)(chemin, json=CORPS, headers=ORIGINE)
        assert r.status_code in (401, 403), (chemin, r.status_code)


def test_la_route_rend_un_docx_ouvrable_et_rempli(marche):
    """ON OUVRE CE QUE LE SERVEUR A RENDU. Vérifier le type MIME dirait
    seulement que l'en-tête est juste ; un fichier tronqué le porterait
    aussi."""
    r = marche.post("/api/datacenter/marche/formulaire", json=CORPS,
                      headers=ORIGINE)
    assert r.status_code == 200, r.data[:200]
    assert "wordprocessingml" in r.headers["Content-Type"], r.headers
    assert "non-signe" in r.headers.get("Content-Disposition", "")
    paras = _paras(io.BytesIO(r.data))
    assert paras[0] == _net(F.BANDEAU)
    assert FICHE["raison_sociale"] in paras, "la fiche n'est pas entrée"
    assert FICHE["siret"] in paras, "le SIRET n'est pas entré"


def test_la_route_dit_dans_un_en_tete_ce_qui_n_a_pas_ete_place(marche):
    """Un téléchargement ne rend pas de JSON, et la page a besoin de dire ce
    qui manque : sans cela, un formulaire partiel se lirait comme complet."""
    import json as _json
    r = marche.post("/api/datacenter/marche/formulaire", json=CORPS,
                      headers=ORIGINE)
    etat = _json.loads(r.headers["X-Remplissage"])
    assert etat["places"] >= 10, etat
    assert etat["maj"] == "12/10/2023", etat
    assert isinstance(etat["non_places"], list)
    assert isinstance(etat["ignores"], list)


def test_un_modele_inconnu_est_refuse_en_400_et_les_choix_sont_dits(marche):
    """Refuser sans dire ce qui est possible ferait deviner le nom du
    formulaire."""
    r = marche.post("/api/datacenter/marche/formulaire",
                      json=dict(CORPS, modele="dc9"), headers=ORIGINE)
    assert r.status_code == 400, r.status_code
    j = r.get_json()
    assert j["error"] == "modele_inconnu"
    assert "dc4" in j["disponibles"]


def test_la_route_ne_declare_rien_meme_avec_une_fiche_complete(marche):
    """LA LIGNE À NE PAS FRANCHIR. Aucune des affirmations du cadre K1 ne doit
    apparaître comme cochée ou reprise dans le document produit : leur
    fausseté est sanctionnée pénalement, et une case remplie par un programme
    est une déclaration que personne n'a faite."""
    r = marche.post("/api/datacenter/marche/formulaire", json=CORPS,
                      headers=ORIGINE)
    produit = _paras(io.BytesIO(r.data))
    modele = _paras(F.chemin_modele("dc4"))
    k = next(i for i, t in enumerate(produit)
             if t.startswith("K1 - Le sous-traitant déclare sur l'honneur"))
    assert produit[k:] == modele[k - 1:], (
        "la zone des déclarations et des signatures a été touchée par la "
        "route")


def test_l_etat_des_modeles_distingue_pret_absent_et_altere(marche):
    """La page ne devine pas : un bouton proposé pour un modèle absent
    produirait une erreur au clic, un bouton caché ferait croire que la
    fonction n'existe pas."""
    r = marche.get("/api/datacenter/marche/formulaires", headers=ORIGINE)
    assert r.status_code == 200
    j = r.get_json()
    assert j["etat"]["prets"] == ["attri1", "dc1", "dc2", "dc4"], j["etat"]
    assert set(j["etat"]) == {"prets", "manquants", "alteres"}
    # L'EMPREINTE NE SORT PAS. Elle sert à refuser un fichier modifié ; la
    # publier n'aide personne et invite à la reproduire.
    assert "empreinte" not in j["modeles"]["dc4"], j["modeles"]["dc4"]
    assert j["modeles"]["dc4"]["maj"] == "12/10/2023"
    assert "NON SIGNÉ" in j["bandeau"]


# ══════════════════════════════════════════════════════════════════════════
# 6. LES TROIS AUTRES FORMULAIRES — DC1, DC2, ATTRI1
# ══════════════════════════════════════════════════════════════════════════
#
# CE QUI A CHANGÉ DANS LE MOTEUR POUR LES ACCUEILLIR, et c'était nécessaire :
# ces trois-là portent leurs INTITULÉS DE CADRE dans des tableaux d'une seule
# cellule qui leur servent d'encadré. `doc.paragraphs` ne rend que le corps :
# l'arrêt au cadre suivant ne voyait donc AUCUN cadre, et une ancre dont
# l'emplacement aurait disparu aurait déposé sa valeur dix cadres plus loin.
# Le moteur lit désormais le document dans son ORDRE RÉEL — 217 paragraphes au
# DC1 au lieu de 168, 339 au DC2 au lieu de 223.

FICHE_COMPLETE = dict(FICHE, rcs="Paris B 802 954 785", naf="7112B",
                      ca_n1="1 400 000 €", ca_n2="1 250 000 €",
                      ca_n3="980 000 €", capital="50 000 €", effectif="12")

CCAP = "CCAP\nDélai d'exécution : 18 mois à compter de la notification.\n"


def _forme(cle):
    """Un formulaire rempli, avec son rapport et les deux listes de
    paragraphes — le modèle et le produit."""
    an = ao_dc.analyser([{"nom": "01_RC.pdf", "texte": RC},
                         {"nom": "02_CCAP.pdf", "texte": CCAP}])
    r = ao_dc.remplir(fiche=FICHE_COMPLETE, analyse=an, saisies=SAISIES)
    octets, rapport = F.remplir_document(
        cle, F.valeurs_pour(r, F.MODELES[cle]["piece"]))
    assert octets, rapport
    return (_paras(io.BytesIO(octets)), _paras(F.chemin_modele(cle)), rapport)


# L'INTITULÉ ATTENDU DEVANT CHAQUE VALEUR, relevé sur chaque formulaire. C'est
# ce qui distingue « la valeur est dans le document » de « la valeur est au bon
# endroit ». Seule la seconde question a un intérêt.
DEVANT_FORMES = {
    "dc1": {
        "acheteur": "(Reprendre le contenu de la mention",
        "objet_consultation": "(Reprendre le contenu de la mention",
        "lots": "pour le lot n°",
        "candidat": "Nom commercial et dénomination sociale",
        "adresse": "Adresses postale et du siège social",
        "siret": "Numéro SIRET",
    },
    "dc2": {
        "acheteur": "(Reprendre le contenu de la mention",
        "objet_consultation": "(Reprendre le contenu de la mention",
        "candidat": "Nom commercial et dénomination sociale",
        "siret": "Numéro SIRET",
        "forme": "Forme juridique du candidat individuel",
        "rcs": "E1 - Renseignements sur l'inscription",
    },
    "attri1": {
        "objet_marche": "(Reprendre le contenu de la mention",
        "lots": "(Indiquer l'intitulé du ou des lots",
        "titulaire": "[Indiquer le nom commercial",
        "duree": "B5 - Durée d'exécution du marché public",
    },
}


@pytest.mark.parametrize("cle", ["dc1", "dc2", "attri1"])
def test_chaque_valeur_des_trois_formulaires_est_sous_son_intitule(cle):
    out, _mod, rapport = _forme(cle)
    par_rubrique = {x["rubrique"]: x for x in rapport["places"]}
    assert rapport["non_places"] == [], rapport["non_places"]
    for rubrique, intitule in DEVANT_FORMES[cle].items():
        assert rubrique in par_rubrique, (cle, rubrique, sorted(par_rubrique))
        i = par_rubrique[rubrique]["paragraphe"] + 1     # le bandeau décale
        avant = [t for t in out[max(0, i - 5):i] if t]
        assert avant, (cle, rubrique)
        assert _net(intitule) in avant[-1], (
            "%s : « %s » est écrite sous « %s » au lieu de « %s »"
            % (cle, rubrique, avant[-1][:70], intitule))


@pytest.mark.parametrize("cle", ["dc1", "dc2", "attri1"])
def test_aucun_paragraphe_porteur_de_texte_n_est_ecrase_sur_les_trois(cle):
    """Le même invariant que sur le DC4, éprouvé sur des documents dont la
    structure est tout autre — onze tableaux au DC1, douze au DC2."""
    out, mod, _r = _forme(cle)
    assert len(out) == len(mod) + 1, (cle, len(out), len(mod))
    modifies = 0
    for i in range(1, len(out)):
        if out[i] == mod[i - 1]:
            continue
        modifies += 1
        assert F._emplacement_libre(mod[i - 1]), (
            "%s ¶%d portait « %s » et a été écrasé par « %s »"
            % (cle, i, mod[i - 1][:60], out[i][:60]))
    assert modifies == len(_forme(cle)[2]["places"]), cle


def test_l_acte_d_engagement_n_ecrit_RIEN_dans_les_blocs_de_signature():
    """LES CADRES C ET D SONT LES SIGNATURES — celle du titulaire, puis celle
    de l'acheteur. Y déposer un nom ferait ressembler à signé un document qui
    ne l'est pas, et c'est exactement ce que ce module refuse de produire."""
    out, mod, _r = _forme("attri1")
    c = next(i for i, t in enumerate(out)
             if t.startswith("C - Signature du marché public"))
    d = next(i for i, t in enumerate(out)
             if t.startswith("D - Identification et signature de l'acheteur"))
    assert c < d, (c, d)
    modifies = [i for i in range(1, len(out)) if out[i] != mod[i - 1]]
    assert modifies, "rien n'a été écrit : la règle ne mesure rien"
    assert [i for i in modifies if i >= c] == [], (
        "des valeurs ont été écrites dans les blocs de signature : %s"
        % [i for i in modifies if i >= c])


def test_le_DC1_n_ecrit_RIEN_dans_la_declaration_sur_l_honneur():
    """F1 porte la déclaration d'absence d'interdiction de soumissionner. Sa
    fausseté est sanctionnée pénalement : rien n'y entre."""
    out, mod, _r = _forme("dc1")
    f1 = next(i for i, t in enumerate(out)
              if t.startswith("F1 – Exclusions de la procédure"))
    f2 = next(i for i, t in enumerate(out) if t.startswith("F2 –"))
    modifies = [i for i in range(1, len(out)) if out[i] != mod[i - 1]]
    assert [i for i in modifies if f1 <= i < f2] == [], (
        "des valeurs ont été écrites dans la déclaration sur l'honneur")


def test_les_trois_chiffres_d_affaires_du_DC2_sont_dans_LEUR_ordre():
    """LE PIÈGE PROPRE AU DC2. Le cadre F1 range trois exercices côte à côte,
    et les trois lignes libres qui suivent « Chiffre d'affaires global » sont
    leurs trois colonnes. Inverser l'ordre attribuerait le chiffre du dernier
    exercice à l'avant-dernier — une erreur qui se lit comme une entreprise en
    croissance ou en déclin, selon le sens, et qu'aucune case vide ne
    signale."""
    out, _mod, rapport = _forme("dc2")
    places = {x["rubrique"]: x["paragraphe"] for x in rapport["places"]}
    assert places["ca_n1"] < places["ca_n2"] < places["ca_n3"], places
    assert out[places["ca_n1"] + 1] == FICHE_COMPLETE["ca_n1"]
    assert out[places["ca_n3"] + 1] == FICHE_COMPLETE["ca_n3"]
    # ET ILS SE SUIVENT : trois colonnes, trois lignes consécutives.
    assert places["ca_n3"] - places["ca_n1"] == 2, places


def test_ce_qu_on_detient_et_que_le_formulaire_n_offre_pas_est_DIT():
    """Une valeur qu'on a et qu'on ne pose pas doit se dire. Sans cette liste,
    le rapport annoncerait sept valeurs écrites là où le report en connaît
    onze, et l'écart resterait inexpliqué — on chercherait un défaut de
    remplissage là où il n'y a qu'un formulaire sans case."""
    _out, _mod, rapport = _forme("attri1")
    # L'ATTRI1 N'A PAS DE CASE « acheteur » À LA MAIN DU CANDIDAT : son cadre D
    # est le bloc de signature de l'acheteur. Le signataire du titulaire est au
    # cadre C. Les deux sont interdits, et le rapport les nomme.
    for rubrique in ("acheteur", "signataire", "qualite"):
        assert rubrique in rapport["sans_ancre"], (rubrique,
                                                   rapport["sans_ancre"])
    assert set(rapport["sans_ancre"]).isdisjoint(
        {x["rubrique"] for x in rapport["places"]})
    # ET LE DC1, QUI A DES CASES POUR TOUT CE QU'IL DEMANDE, en a moins.
    assert len(_forme("dc1")[2]["sans_ancre"]) < len(rapport["sans_ancre"])
