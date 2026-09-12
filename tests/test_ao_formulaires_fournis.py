# -*- coding: utf-8 -*-
"""Le formulaire vierge joint au dossier entre dans les documents à produire.

LA CLAUSE DU DONNEUR D'ORDRE : « possibilité de charger d'autres documents à
remplir à gauche, qui sont à remplir en fonction du dossier marché et se
retrouvent à droite automatiquement ».

LE MANQUE, MESURÉ AVANT D'ÊTRE COMBLÉ. La sélection avait UNE seule source :
les citations du règlement de consultation. Un DC4 vierge déposé avec le
dossier n'était donc rien — ni pièce du dossier de consultation, puisqu'il ne
porte aucune clause à relever, ni fichier illisible. Il tombait en
« non identifié », et la colonne de droite ne le voyait pas. Or un formulaire
que l'acheteur JOINT est un formulaire qu'il attend rempli : le fait est au
moins aussi fort qu'une phrase de son règlement, et il ne dépend d'aucune
lecture de texte.

LE PIÈGE PROPRE À CE MODULE, ET C'EST LE PLUS IMPORTANT DE CE FICHIER. « DC »
est le sigle de la Déclaration du Candidat — et celui du centre de données.
Ce module ne traite QUE des centres de données. Mesuré avant correction :
« lot DC 2 - CVC.pdf », un lot de travaux, passait pour un formulaire DC2 à
remplir ; et « plan-dc-1er-etage.pdf » pour un DC1. Deux gardes tiennent le
sigle : un nom qui désigne un LOT ne désigne pas un cerfa, et le texte, quand
il existe, l'emporte sur le nom.

CE QUE CES RÈGLES REFUSENT DE FAIRE. Aucune ne se contente de vérifier qu'une
pièce est retenue : chacune porte son TÉMOIN NÉGATIF — le même dossier sans le
formulaire, le même nom sans le fichier, le même sigle dans un autre sens. Une
règle qui dirait seulement « dc4 est retenue » serait verte grâce au socle le
jour où quelqu'un y ajouterait le DC4.
"""
import io
import json
import os
import re
import subprocess

import pytest

import ao_dc


ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from test_ao_formulaires import _js_source                      # noqa: E402


def _node(prog, env=None):
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60, env=dict(os.environ, **(env or {})))
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout


#: Un règlement qui ne nomme NI le DC4 NI la sous-traitance : c'est ce qui
#: rend la mesure concluante. Si le règlement le citait, la pièce serait
#: retenue de toute façon et le formulaire joint n'aurait rien prouvé.
RC_MUET_SUR_DC4 = (
    "REGLEMENT DE LA CONSULTATION\n"
    "Article 5 — Composition du dossier de candidature\n"
    "Le candidat produit la lettre de candidature et la déclaration du "
    "candidat dûment complétées, ainsi qu'une déclaration sur l'honneur.\n"
)


def _dossier(*fichiers):
    return ao_dc.analyser([{"nom": n, "texte": t, "extension": e}
                           for n, t, e in fichiers])


def _ligne(sel, cle):
    for x in sel["lignes"]:
        if x["cle"] == cle:
            return x
    raise AssertionError("pièce absente du catalogue : %s" % cle)


# ==========================================================================
# LE FAIT : LE FORMULAIRE EST LÀ, DONC IL EST ATTENDU
# ==========================================================================
def test_un_formulaire_JOINT_entre_dans_les_documents_a_produire():
    a = _dossier(("RC.pdf", RC_MUET_SUR_DC4, ".pdf"),
                 ("DC4.pdf", "", ".pdf"))
    x = _ligne(ao_dc.selection(analyse=a), "dc4")
    assert x["retenue"], x
    assert x["pourquoi"] == "fournie_au_dossier", x["pourquoi"]


def test_sans_le_formulaire_le_MEME_dossier_ne_le_retient_PAS():
    """LE TÉMOIN QUI DONNE SON SENS À LA RÈGLE PRÉCÉDENTE. Sans lui, elle
    serait verte le jour où quelqu'un ajouterait le DC4 au socle — et l'on
    croirait mesurer le formulaire joint."""
    a = _dossier(("RC.pdf", RC_MUET_SUR_DC4, ".pdf"))
    x = _ligne(ao_dc.selection(analyse=a), "dc4")
    assert not x["retenue"], (
        "le DC4 est retenu SANS que le dossier le joigne ni le cite : la "
        "mesure du formulaire joint ne prouve plus rien")


def test_le_fichier_qui_apporte_la_piece_est_NOMME():
    """« Fournie au dossier » sans le nom du fichier est une affirmation de
    plus : on ne saurait pas lequel des quinze dépôts la porte."""
    a = _dossier(("RC.pdf", RC_MUET_SUR_DC4, ".pdf"),
                 ("DC4 sous-traitance.pdf", "", ".pdf"))
    x = _ligne(ao_dc.selection(analyse=a), "dc4")
    assert x["fichier_fourni"] == "DC4 sous-traitance.pdf", x
    assert "DC4 sous-traitance.pdf" in x["motif"], x["motif"]


def test_une_piece_CITEE_et_fournie_dit_CITEE_sans_perdre_le_formulaire():
    """L'exigence prime sur la commodité : c'est le règlement qui dit ce qui
    est dû. Mais perdre au passage qu'on tient déjà le formulaire ferait
    rechercher un document qu'on a sous la main."""
    rc = (RC_MUET_SUR_DC4
          + "En cas de sous-traitance, le candidat produit une déclaration "
            "de sous-traitance (formulaire DC4).\n")
    a = _dossier(("RC.pdf", rc, ".pdf"), ("DC4.pdf", "", ".pdf"))
    x = _ligne(ao_dc.selection(analyse=a), "dc4")
    assert x["pourquoi"] == "citee", x["pourquoi"]
    assert x["fichier_fourni"] == "DC4.pdf", x


def test_une_piece_ECARTEE_a_la_main_le_reste_meme_si_le_formulaire_est_joint():
    """Le geste de l'opérateur l'emporte sur le fait : il sait quelque chose
    que le dossier ne dit pas — qu'il ne sous-traitera pas, par exemple."""
    a = _dossier(("RC.pdf", RC_MUET_SUR_DC4, ".pdf"), ("DC4.pdf", "", ".pdf"))
    x = _ligne(ao_dc.selection(analyse=a, ecartees=["dc4"]), "dc4")
    assert not x["retenue"] and x["pourquoi"] == "ecartee", x


# ==========================================================================
# « DC » : LE SIGLE DU CENTRE DE DONNÉES AUTANT QUE CELUI DU CANDIDAT
# ==========================================================================
NOMS = [
    # (nom de fichier, texte, pièce attendue ou None)
    ("DC1.pdf", "", "dc1"),
    ("DC 1 - lettre de candidature.pdf", "", "dc1"),
    ("dc_01.pdf", "", "dc1"),
    ("declaration du candidat DC2.pdf", "", "dc2"),
    ("DC4.pdf", "", "dc4"),
    # Les pièges du domaine — tous mesurés avant correction.
    ("plan-dc-1er-etage.pdf", "", None),
    ("lot DC 2 - CVC.pdf", "", None),
    ("lot DC 2 - CVC.pdf", "CCTP lot CVC — groupes froids et free cooling",
     None),
    ("dc10-annexe.pdf", "", None),
    ("DCE.zip", "", None),
    ("CCAP.pdf", "", None),
]


@pytest.mark.parametrize("nom,texte,attendu", NOMS)
def test_le_nom_de_fichier_est_lu_SANS_confondre_les_deux_sens_de_DC(
        nom, texte, attendu):
    a = _dossier((nom, texte, ".pdf"))
    rendu = [f["cle"] for f in a["formulaires_fournis"]]
    assert rendu == ([attendu] if attendu else []), \
        "%s → %s (attendu %s)" % (nom, rendu, attendu)


def test_un_nom_qui_porte_le_LIBELLE_echappe_a_la_garde_des_lots():
    """La garde vise le sigle nu près d'un numéro de lot. Un nom qui dit
    « lettre de candidature » ne dit plus « lot de travaux »."""
    a = _dossier(("DC1 - lettre de candidature - lot 1.pdf", "", ".pdf"))
    assert [f["cle"] for f in a["formulaires_fournis"]] == ["dc1"]


def test_le_TEXTE_contredit_le_nom_et_l_EMPORTE():
    """La doctrine du module, déjà écrite pour les pièces du candidat : le nom
    propose, le texte dispose. Un fichier nommé DC4 dont le texte est un CCTP
    est un CCTP mal nommé."""
    a = _dossier(("DC4.pdf",
                  "CAHIER DES CLAUSES TECHNIQUES PARTICULIERES\n"
                  "Groupes froids, redondance N+1, free cooling.", ".pdf"))
    assert a["formulaires_fournis"] == []


def test_un_formulaire_SANS_texte_est_quand_meme_place():
    """Un cerfa scanné ne rend aucune ligne. Exiger la confirmation du texte
    dans tous les cas reviendrait à ne jamais reconnaître un formulaire
    numérisé — c'est-à-dire la moitié d'entre eux."""
    a = _dossier(("DC4.pdf", "", ".pdf"))
    assert [f["cle"] for f in a["formulaires_fournis"]] == ["dc4"]


def test_le_TEXTE_qui_nomme_un_formulaire_ne_vaut_PAS_formulaire_joint():
    """Le règlement de la consultation nomme « DC1 » à longueur de page.
    Reconnaître sur le texte ferait passer le règlement lui-même pour un
    formulaire — et la citation, elle, a déjà son propre chemin."""
    rc = (RC_MUET_SUR_DC4
          + "Les candidats produiront un DC1 et un DC2, ainsi qu'un DC4 en "
            "cas de sous-traitance.\n")
    a = _dossier(("RC.pdf", rc, ".pdf"))
    assert a["formulaires_fournis"] == [], a["formulaires_fournis"]
    x = _ligne(ao_dc.selection(analyse=a), "dc4")
    assert x["pourquoi"] == "citee", (
        "le DC4 nommé dans le texte doit être « citée », pas « fournie »")


# ==========================================================================
# LES PIÈCES DU DCE QUI SONT DÉJÀ DES FORMULAIRES DE RÉPONSE
# ==========================================================================
def test_l_acte_d_engagement_du_DCE_appelle_la_piece_de_reponse():
    """L'acte d'engagement et la DPGF sont identifiés comme pièces du dossier
    de consultation. Les reconnaître une seconde fois par leur nom aurait
    donné deux définitions ; la table dit simplement ce qu'ils commandent."""
    a = _dossier(("Acte d'engagement.pdf",
                  "ACTE D ENGAGEMENT\nLe présent acte d'engagement est établi "
                  "pour le marché de travaux.", ".pdf"))
    assert [f["cle"] for f in a["formulaires_fournis"]] == ["acte_engagement"]


def test_chaque_code_du_DCE_renvoie_a_une_piece_du_CATALOGUE():
    """Une correspondance vers une clé qui n'existe pas serait muette : la
    pièce ne serait jamais retenue, et rien ne le dirait."""
    cles = {p["cle"] for p in ao_dc.DOSSIER_CANDIDATURE + ao_dc.DOSSIER_OFFRE}
    for code, rep in ao_dc.CODE_DCE_VERS_REPONSE.items():
        assert code in ao_dc.PIECES_MARCHE, \
            "« %s » n'est pas un code de pièce du DCE" % code
        assert rep in cles, \
            "« %s » ne désigne aucune pièce du catalogue" % rep


def test_chaque_formulaire_de_la_table_designe_une_piece_du_CATALOGUE():
    cles = {p["cle"] for p in ao_dc.DOSSIER_CANDIDATURE + ao_dc.DOSSIER_OFFRE}
    manquantes = sorted(set(ao_dc.FORMULAIRES_FOURNIS) - cles)
    assert not manquantes, manquantes


def test_le_meme_formulaire_depose_deux_fois_NOMME_le_premier():
    """Deux copies du même cerfa ne font pas deux pièces à produire — et la
    ligne doit nommer L'ORIGINAL, pas le doublon.

    CETTE RÈGLE A D'ABORD ÉTÉ ÉCRITE FAUSSE, et la mutation l'a montré : elle
    comptait les lignes du catalogue, qui sont uniques par construction. Elle
    ne pouvait pas tomber. Ce qui se choisit réellement quand un fichier est
    déposé deux fois, c'est le nom porté sur la ligne ; un « (copie) » venu
    désigner la pièce à la place de l'original enverrait l'opérateur ouvrir
    le mauvais fichier.
    """
    a = _dossier(("RC.pdf", RC_MUET_SUR_DC4, ".pdf"),
                 ("DC4.pdf", "", ".pdf"),
                 ("DC4 (copie).pdf", "", ".pdf"))
    vus = [f["fichier"] for f in a["formulaires_fournis"] if f["cle"] == "dc4"]
    assert vus == ["DC4.pdf", "DC4 (copie).pdf"], (
        "le montage ne mesure plus rien : l'analyse ne voit pas les deux "
        "dépôts — %s" % vus)
    sel = ao_dc.selection(analyse=a)
    assert [x["cle"] for x in sel["lignes"]].count("dc4") == 1
    assert _ligne(sel, "dc4")["fichier_fourni"] == "DC4.pdf", \
        "c'est le doublon qui désigne la pièce, pas l'original"


def test_le_formulaire_joint_est_REELLEMENT_rempli_et_pas_seulement_annonce():
    """La sélection qui retient sans que le remplissage suive serait la
    version « à droite » du défaut corrigé au § 14 : une mesure juste,
    affichée, et sans effet."""
    a = _dossier(("RC.pdf", RC_MUET_SUR_DC4, ".pdf"), ("DC4.pdf", "", ".pdf"))
    sel = ao_dc.selection(analyse=a)
    peri = [x["cle"] for x in sel["lignes"] if x["retenue"]]
    assert "dc4" in peri
    r = ao_dc.remplir(fiche={}, analyse=a, perimetre=peri)
    assert "dc4" in [p["cle"] for p in r["pieces"]], \
        [p["cle"] for p in r["pieces"]]


# ==========================================================================
# LES DEUX ÉCRANS DISENT LA MÊME CHOSE DU MÊME FICHIER
# ==========================================================================
def _selection_rendue(sel):
    prog = (_js_source("esc", "aoSelectionRendre")
            + "\nfunction aoSelectionBrancher(){}"
            + "\nvar AO_SELECTION = null;"
            + "\nvar zone = { innerHTML: '' };"
            + "\nfunction $(s){ return s === '#ig-ao-retenus' ? zone : null; }"
            + "\naoSelectionRendre(JSON.parse(process.env.SEL));"
            + "\nprocess.stdout.write(zone.innerHTML);\n")
    return _node(prog, {"SEL": json.dumps(sel)})


def test_la_ligne_de_droite_NOMME_le_fichier_qui_apporte_le_formulaire():
    a = _dossier(("RC.pdf", RC_MUET_SUR_DC4, ".pdf"),
                 ("DC4 sous-traitance.pdf", "", ".pdf"))
    h = _selection_rendue(ao_dc.selection(analyse=a))
    # LE NOM DU FICHIER FIGURE AUSSI DANS LE MOTIF, en note sous la ligne.
    # Se contenter de le chercher dans la page entière rendait cette règle
    # verte alors que le marqueur de ligne avait disparu — mesuré par
    # mutation. On lit donc le MARQUEUR, et rien d'autre.
    m = re.search(r"formulaire joint&nbsp;: ([^<]*)</span>", h)
    assert m, (
        "la ligne ne porte pas le marqueur du formulaire joint — le nom du "
        "fichier n'est plus lisible qu'en note de motif")
    assert m.group(1) == "DC4 sous-traitance.pdf", m.group(1)
    assert "fournie au dossier" in h, \
        "le motif n'est pas rendu lisible : les tirets bas restent à l'écran"


def test_la_pastille_du_formulaire_JOINT_a_sa_propre_teinte():
    """Trois motifs, trois teintes. Un motif sans classe se peindrait comme
    « ajoutée à la main » — et l'on croirait avoir choisi ce que le dossier
    impose."""
    a = _dossier(("RC.pdf", RC_MUET_SUR_DC4, ".pdf"), ("DC4.pdf", "", ".pdf"))
    h = _selection_rendue(ao_dc.selection(analyse=a))
    m = re.search(r'<span class="p ([a-z-]+)">fournie au dossier</span>', h)
    assert m, "la pastille « fournie au dossier » n'a pas de classe propre"
    classe = m.group(1)
    css = io.open(os.path.join(ICI, "ingenierie-datacenter.html"),
                  encoding="utf-8").read()
    assert ".%s{" % classe in css, \
        "la classe « %s » n'est déclarée nulle part" % classe
    for autre in ("p-citee", "p-socle"):
        assert classe != autre, "la pastille reprend la teinte de %s" % autre


def _releve_rendu(analyse):
    prog = (_js_source("esc", "aoTexteBouton", "aoIgnores", "aoExigence",
                       "aoRendre")
            + "\nvar AO_TEXTES = {};"
            + "\nfunction info(){ return ''; }"
            + "\nfunction aoTexteBrancherListe(){}"
            + "\nfunction aoTexteFermer(){}"
            + "\nvar zone = { innerHTML: '', querySelectorAll: function () "
              "{ return []; } };"
            + "\nvar ign = { innerHTML: '' }, lect = { innerHTML: '' };"
            + "\nfunction $(s) { return s === '#ig-ao-out' ? zone"
              " : (s === '#ig-ao-ign' ? ign"
              " : (s === '#ig-ao-lect' ? lect : null)); }"
            + "\nvar CADRE = { glossaire: {} };"
            + "\nglobal.document = { querySelectorAll: function () { return []; },"
              " querySelector: function () { return null; } };"
            + "\naoRendre(JSON.parse(process.env.AN));"
            + "\nprocess.stdout.write(zone.innerHTML);\n")
    return _node(prog, {"AN": json.dumps(analyse)})


def test_l_ecran_de_GAUCHE_ne_dit_pas_NON_RECONNU_de_ce_qu_il_a_place_a_droite():
    """DEUX ÉCRANS QUI SE CONTREDISENT SUR LE MÊME FICHIER SONT PIRES QU'UN
    SEUL MUET. Le DC4 vierge n'est reconnu par aucune pièce du dossier de
    consultation — il n'en est pas une. Le laisser dire « non identifié »
    ferait chercher une panne d'extraction pendant que la colonne de droite
    l'annonce à remplir."""
    a = _dossier(("RC.pdf", RC_MUET_SUR_DC4, ".pdf"), ("DC4.pdf", "", ".pdf"))
    assert any(x.get("formulaire_fourni") == "dc4"
               for x in a["inconnues"]), \
        "le montage ne mesure plus rien : le DC4 n'est plus un « inconnu »"
    h = _releve_rendu(a)
    i = h.index("DC4.pdf")
    bloc = h[i:i + 600]
    assert "documents à produire" in bloc, bloc[:400]
    assert "Formulaire à remplir" in bloc, bloc[:400]
