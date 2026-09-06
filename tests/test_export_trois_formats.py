# -*- coding: utf-8 -*-
"""Les trois formats, servis partout, par une seule porte.

CE QUI ÉTAIT EN CAUSE. Le site produisait des documents en Word et en PDF, et
le triptyque « si pdf … sinon docx », type MIME recopié à la main, figurait
QUATORZE fois dans app.py. Deux conséquences, et la seconde est la pire :

  · aucun classeur nulle part, alors que la moitié de ce qui sort est fait de
    TABLEAUX — bordereau de pièces, DPGF, relevés, écarts au référentiel — et
    qu'on ne trie pas une colonne dans un PDF ;
  · un troisième format aurait donné quatorze occasions de diverger. Une route
    qui ignore le nouveau format ne casse rien : elle rend un Word quand on lui
    demande un classeur, sans rien dire. Le téléchargement marche, et c'est ce
    qui rend le défaut invisible.

CE QUE CES RÈGLES MESURENT. Le RÉSULTAT, jamais la présence : un classeur est
rouvert et ses feuilles sont lues, une archive est dézippée et son contenu
compté. Vérifier que « xlsx » figure dans le code aurait été vert le jour où le
classeur sort vide.
"""
import io
import os
import re
import sys
import zipfile

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import livrables_export as LE                                      # noqa: E402
from conftest import ORIGINE                                       # noqa: E402

import openpyxl                                                    # noqa: E402
import pytest                                                      # noqa: E402


def _src(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


def _classeur(md, meta=None):
    return openpyxl.load_workbook(io.BytesIO(LE.build_xlsx(md, meta or {})))


DEUX_TABLEAUX = """# Dossier

## Candidature

| Pièce | Nature | État |
|---|---|---|
| DC1 | Lettre de candidature | à signer |
| DC2 | Déclaration du candidat | rempli |

## Offre

| Poste | Quantité |
|---|---|
| Groupe froid | 4 |
"""


# ── 1. LA PORTE UNIQUE ────────────────────────────────────────────────────

# CE QUE LE FICHIER EST VRAIMENT, ET NON CE QUE SON EN-TÊTE ANNONCE. Un
# document Word et un classeur sont tous deux des archives zip ; seuls leurs
# membres les distinguent. Un PDF s'annonce dans ses quatre premiers octets.
SIGNATURES = {"docx": "word/", "xlsx": "xl/", "pdf": None}


def _nature(blob):
    if blob[:4] == b"%PDF":
        return "pdf"
    noms = zipfile.ZipFile(io.BytesIO(blob)).namelist()
    for fmt, prefixe in SIGNATURES.items():
        if prefixe and any(n.startswith(prefixe) for n in noms):
            return fmt
    return "?"


def test_chaque_format_produit_VRAIMENT_un_fichier_de_ce_format():
    """LA RÈGLE A ÉTÉ REPRISE PARCE QU'ELLE PASSAIT À CÔTÉ. Elle vérifiait la
    distinction des types MIME et la taille du contenu : une mutation qui
    faisait rendre un Word à `composer` pour les trois formats la laissait
    verte, puisque le type MIME venait d'une table intacte. On ouvre donc le
    fichier et on regarde ce qu'il contient."""
    md = "# T\n\nUn texte.\n\n| a |\n|---|\n| 1 |\n"
    vus = {}
    for f in LE.FORMATS:
        blob, mime, ext = LE.composer(md, {"label": "T"}, f)
        assert blob and len(blob) > 500, "%s : document vide ou tronqué" % f
        assert ext == f
        assert _nature(blob) == f, (
            "on a demandé %s et l'on a reçu un fichier %s"
            % (f, _nature(blob)))
        vus[mime] = f
    assert len(vus) == len(LE.FORMATS), (
        "deux formats partagent un type MIME : le navigateur ouvrirait l'un "
        "pour l'autre")


def test_un_format_inconnu_est_REFUSE_au_code_et_NORMALISE_au_reseau():
    """Deux fonctions, deux offices. `format_demande` reçoit n'importe quoi du
    réseau et rend un format connu ; `composer`, appelée depuis le code, lève —
    rendre un Word à qui a demandé un csv serait un mensonge silencieux."""
    assert LE.format_demande("XLSX ") == "xlsx"
    assert LE.format_demande("csv") == LE.FORMAT_DEFAUT
    assert LE.format_demande(None) == LE.FORMAT_DEFAUT
    with pytest.raises(LE.FormatInconnu):
        LE.composer("# x", {}, "csv")


def test_aucune_route_ne_recopie_la_liste_des_formats():
    """LA RÈGLE QUI EMPÊCHE LE RETOUR EN ARRIÈRE. Une route qui réécrit
    ("docx", "pdf") chez elle sert deux formats sur trois, sans rien casser et
    sans rien dire."""
    src = _src("app.py")
    for motif in ('("docx", "pdf")', '("pdf", "docx")',
                  '"application/vnd.openxmlformats-officedocument"\n'
                  '                        ".wordprocessingml.document"'):
        assert motif not in src, (
            "app.py recopie la liste ou le type MIME (%r) au lieu de passer "
            "par livrables_export" % motif[:40])
    assert src.count("livrables_export.composer") >= 14, (
        "les points d'export ne passent plus tous par la porte unique")


# ── 2. LE CLASSEUR REND CE QU'EXCEL SERT À RENDRE ────────────────────────

def test_le_classeur_contient_VRAIMENT_les_tableaux_du_document():
    """On rouvre le fichier et on lit les cellules. Chercher « xlsx » dans le
    code serait vert le jour où le classeur sort vide."""
    wb = _classeur(DEUX_TABLEAUX, {"label": "Dossier"})
    assert "Candidature" in wb.sheetnames and "Offre" in wb.sheetnames, (
        "les feuilles ne portent pas le titre de leur tableau : %s"
        % wb.sheetnames)
    f = wb["Candidature"]
    assert [c.value for c in f[1]] == ["Pièce", "Nature", "État"]
    assert [c.value for c in f[2]] == ["DC1", "Lettre de candidature", "à signer"]
    assert f.freeze_panes == "A2", "l'en-tête ne reste pas visible au défilement"
    assert f.auto_filter.ref, "le tableau n'est pas filtrable — c'est tout "\
                              "l'intérêt du format"
    assert wb["Offre"].max_row == 2


def test_un_document_sans_tableau_LE_DIT_au_lieu_de_livrer_une_grille_vide():
    wb = _classeur("# Note\n\nUn texte sans le moindre tableau.\n")
    assert set(wb.sheetnames) == {LE.FEUILLE_GARDE, LE.FEUILLE_TEXTE}
    d = wb[LE.FEUILLE_GARDE]
    dit = next((r[1].value for r in d.iter_rows()
                if r[0].value == "Feuilles de données"), None)
    assert dit and "aucune" in dit, (
        "un document narratif ne dit pas qu'il n'a pas de tableau : le "
        "classeur passe pour un export raté")


def test_le_texte_du_document_ne_se_perd_pas_dans_le_classeur():
    wb = _classeur(DEUX_TABLEAUX, {"label": "Dossier"})
    lu = [c.value for r in wb[LE.FEUILLE_TEXTE].iter_rows() for c in r]
    assert "Candidature" in lu and "Offre" in lu, (
        "les titres du document ne figurent nulle part dans le classeur")


def test_les_noms_de_feuille_tiennent_dans_la_limite_du_format():
    """Excel refuse au-delà de 31 signes et refuse les doublons. Deux tableaux
    sous le même titre, c'est le cas courant d'un relevé par pièce."""
    md = ("## Relevés\n\n| a |\n|---|\n| 1 |\n\n| b |\n|---|\n| 2 |\n\n"
          "## Un titre de section beaucoup trop long pour une feuille Excel\n\n"
          "| c |\n|---|\n| 3 |\n")
    noms = _classeur(md).sheetnames
    assert len(noms) == len(set(noms)), "deux feuilles portent le même nom"
    for n in noms:
        assert len(n) <= LE.XL_NOM_MAX, "« %s » fait %d signes" % (n, len(n))
        assert not set(n) & set("[]:*?/\\"), "« %s » porte un signe interdit" % n
    # L'UNICITÉ SEULE NE PROUVAIT RIEN, et une mutation l'a montré : openpyxl
    # renomme lui-même une feuille en double, et la règle restait verte pendant
    # que notre dédoublonnage était supprimé. Ce qui compte est le nom qui en
    # sort — « Relevés (2) » se lit, « Relevés1 » se subit.
    assert "Relevés" in noms and "Relevés (2)" in noms, (
        "le dédoublonnage ne vient plus de nous : %s" % noms)


def test_la_largeur_du_tableau_vient_de_l_EN_TETE_et_non_de_la_premiere_ligne():
    """Un tableau Markdown mal aligné ne doit pas perdre sa dernière colonne —
    et c'est souvent celle qui porte l'observation.

    CE QUE CETTE RÈGLE A APPRIS. Elle protégeait un complètement des lignes
    courtes ; la mutation qui supprimait ce complètement ne la faisait pas
    tomber, parce que la largeur ne vient PAS des lignes : elle vient de
    l'en-tête, écrit en premier. Le complètement était du code mort. La règle
    vise donc désormais ce qui tient réellement la largeur."""
    wb = _classeur("| a | b | c |\n|---|---|---|\n| 1 | 2 |\n")
    f = wb[[n for n in wb.sheetnames
            if n not in (LE.FEUILLE_GARDE, LE.FEUILLE_TEXTE)][0]]
    assert [c.value for c in f[1]] == ["a", "b", "c"], (
        "l'en-tête du tableau n'est plus celui du document")
    assert f.max_column == 3, "le tableau a perdu une colonne"


def test_le_balisage_ne_se_lit_pas_dans_une_cellule():
    wb = _classeur("| x |\n|---|\n| **gras** et [lien](http://e.test) |\n")
    f = wb[[n for n in wb.sheetnames
            if n not in (LE.FEUILLE_GARDE, LE.FEUILLE_TEXTE)][0]]
    assert f.cell(2, 1).value == "gras et lien"


def test_la_garde_du_classeur_porte_les_memes_champs_que_les_deux_autres():
    meta = {"label": "Objet", "client": "Client X", "numero": "AO-001"}
    wb = _classeur("# T\n", meta)
    lu = {r[0].value: r[1].value for r in wb[LE.FEUILLE_GARDE].iter_rows()
          if r[0].value}
    for cle, val in LE._fiche(meta):
        assert lu.get(cle) == val, "le cartouche du classeur perd « %s »" % cle


# ── 3. LES PAGES OFFRENT LES TROIS ───────────────────────────────────────

def test_chaque_bloc_qui_offre_le_PDF_offre_aussi_le_classeur():
    """ON ÉNUMÈRE LES FICHIERS, ON N'EN ÉCHANTILLONNE PAS UN. Un point d'export
    oublié rend un site qui offre Excel « presque partout » — et c'est la page
    qu'on utilise qui manque."""
    manquants = []
    for nom in sorted(os.listdir(ICI)):
        if not nom.endswith((".html", ".js")) or nom.startswith("recette_"):
            continue
        src = _src(nom)
        # Un BLOC D'EXPORT se reconnaît à un bouton qui demande le PDF, et non
        # à la simple présence du mot : « .pdf » dans une liste de formats
        # acceptés au dépôt n'est pas un export.
        if not re.search(r'(?:id="[\w-]*-?pdf"|data-[\w-]*="pdf"|'
                         r"exporter\(\"pdf\"\)|'pdf'\))", src):
            continue
        if "xlsx" not in src:
            manquants.append(nom)
    assert not manquants, (
        "ces pages offrent le PDF sans offrir le classeur : "
        + ", ".join(manquants))


# ── 4. L'ARCHIVE DU DOSSIER D'APPEL D'OFFRES ─────────────────────────────

def _archive(cl, fmt="docx"):
    r = cl.post("/api/datacenter/marche/dossier.zip",
                json={"fiche": {"raison_sociale": "CONSEILPREV",
                                "siret": "73282932000074"},
                      "saisies": {}, "format": fmt}, headers=ORIGINE)
    assert r.status_code == 200, r.data[:300]
    return zipfile.ZipFile(io.BytesIO(r.data)), r.headers.get("X-Dossier")


def test_l_archive_porte_le_report_les_quatre_formulaires_et_son_bordereau(connecte):
    z, entete = _archive(connecte)
    noms = set(z.namelist())
    assert "BORDEREAU.txt" in noms
    assert "reponse-consultation.docx" in noms
    formulaires = {n for n in noms if n.endswith("-projet-non-signe.docx")}
    assert len(formulaires) == 4, (
        "l'archive porte %d formulaire(s) sur 4 : %s"
        % (len(formulaires), sorted(formulaires)))
    for n in noms:
        assert z.getinfo(n).file_size > 200, "« %s » est vide dans l'archive" % n
    assert '"pieces": 5' in (entete or ""), entete


def test_le_format_demande_ne_change_QUE_le_report(connecte):
    """Les formulaires officiels restent en Word, et c'est voulu : ce qui sort
    EST le fichier du ministère. Un fac-similé serait refusé — ou pire, accepté
    et faux."""
    for fmt in LE.FORMATS:
        z, _ = _archive(connecte, fmt)
        noms = set(z.namelist())
        assert ("reponse-consultation." + fmt) in noms, sorted(noms)
        assert len([n for n in noms
                    if n.endswith("-projet-non-signe.docx")]) == 4


def test_le_bordereau_NOMME_ce_qui_n_a_pas_pu_etre_produit(connecte, monkeypatch):
    """Une archive silencieusement incomplète est pire que pas d'archive :
    celui qui la reçoit compte six fichiers au lieu de sept et ne saura jamais
    si le septième n'existait pas ou s'il a échoué."""
    import ao_formulaires
    vrai = ao_formulaires.remplir_document

    def casse(modele, valeurs):
        if modele == "dc2":
            return b"", {"ok": False, "motif": "modele_absent"}
        return vrai(modele, valeurs)

    monkeypatch.setattr(ao_formulaires, "remplir_document", casse)
    z, entete = _archive(connecte)
    bord = z.read("BORDEREAU.txt").decode("utf-8")
    assert "dc2-projet-non-signe.docx" not in z.namelist()
    assert "CE QUI N'A PAS PU ÊTRE PRODUIT" in bord
    assert "dc2-projet-non-signe.docx" in bord and "absent" in bord
    assert "dc2" in (entete or ""), (
        "la page ne peut pas dire ce qui manque : le compte ne voyage pas")


def test_une_archive_qui_ne_contient_rien_est_REFUSEE(connecte, monkeypatch):
    """Un zip qui ne porte qu'un bordereau d'échecs se télécharge et déçoit."""
    import ao_formulaires
    monkeypatch.setattr(ao_formulaires, "remplir_document",
                        lambda m, v: (b"", {"ok": False, "motif": "modele_absent"}))
    monkeypatch.setattr(LE, "composer",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    r = connecte.post("/api/datacenter/marche/dossier.zip",
                      json={"fiche": {}, "format": "docx"}, headers=ORIGINE)
    assert r.status_code == 409
    assert r.get_json()["error"] == "dossier_vide"
