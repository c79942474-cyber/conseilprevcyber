# -*- coding: utf-8 -*-
"""UNE SEULE COMPOSITION DU REPORT, POUR /export ET POUR /dossier.zip.

LE DOUBLON, MESURÉ. Les deux routes portaient vingt-cinq lignes de code
identiques : la charge utile, le remplissage, le markdown, le cartouche et le
bordereau. Ce n'était pas une redite de confort — c'est le CARTOUCHE qui était
en double, et le cartouche porte le périmètre annoncé (« N rubriques ·
N pièces »). Deux copies divergent au premier ajout, et celle qu'on oublie
part chez l'acheteur avec un en-tête qui ment sur son propre contenu.

CE QUE CES RÈGLES TIENNENT, et pourquoi elles ne se contentent pas de
constater que l'aide existe :

  · les deux routes APPELLENT la même aide — une seule occurrence de la
    composition dans tout le fichier ;
  · elles rendent le MÊME report pour la même requête — comparé sur le
    markdown et sur le cartouche, pas sur la présence d'un appel ;
  · chacune garde SON libellé de journal : c'est lui qui dit, dans les traces,
    lequel des deux gestes a échoué.
"""
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)


def source():
    with open(os.path.join(ICI, "app.py"), encoding="utf-8") as f:
        return f.read()


def corps(fn, s=None):
    s = s or source()
    d = s.index("def %s(" % fn)
    f = s.find("@app.route(", d)
    return re.sub(r'"""[\s\S]*?"""', "", s[d:f], count=1)


CHARGE = {"fiche": {"raison_sociale": "ESSAI SARL", "siret": "494 530 157 00036"},
          "analyse": None, "saisies": {}, "format": "docx"}


# ═══════════════════════════════════════════════════════════════════════════
#  1. LA COMPOSITION N'EXISTE QU'UNE FOIS
# ═══════════════════════════════════════════════════════════════════════════

def test_le_cartouche_du_report_n_est_ecrit_qu_une_fois():
    """La règle porte sur le CARTOUCHE, pas sur un nom de fonction : c'est lui
    qui portait le périmètre en double."""
    s = source()
    n = s.count('"label": "Réponse à consultation — pièces préparées"')
    assert n == 1, "le cartouche du report est écrit %d fois" % n


def test_les_deux_routes_passent_par_la_meme_aide():
    for fn in ("api_datacenter_marche_export", "api_datacenter_marche_dossier_zip"):
        c = corps(fn)
        assert "_ao_report(data)" in c, "%s ne passe pas par l'aide" % fn
        assert "ao_dc.markdown_remplissage(" not in c, (
            "%s recompose le report chez elle" % fn)


def test_chaque_route_garde_son_libelle_de_journal():
    """Un libellé commun rendrait les traces muettes sur le geste en cause."""
    a = corps("api_datacenter_marche_export")
    b = corps("api_datacenter_marche_dossier_zip")
    assert "remplissage à exporter" in a
    assert "dossier complet — remplissage" in b


# ═══════════════════════════════════════════════════════════════════════════
#  2. LES DEUX ROUTES RENDENT LE MÊME REPORT — MESURÉ, PAS SUPPOSÉ
# ═══════════════════════════════════════════════════════════════════════════

def test_l_aide_rend_le_meme_report_a_chaque_appel():
    import app as A
    with A.app.test_request_context(json=CHARGE):
        f1, r1, md1, meta1, fmt1 = A._ao_report(dict(CHARGE))
        f2, r2, md2, meta2, fmt2 = A._ao_report(dict(CHARGE))
    assert md1 == md2 and meta1 == meta2 and fmt1 == fmt2
    assert r1["etat"] == r2["etat"]


def test_le_cartouche_annonce_le_perimetre_du_remplissage_rendu():
    """LE POINT QUI COMPTE. Un cartouche qui annonce un périmètre étranger au
    contenu est exactement ce que la duplication produisait à terme."""
    import app as A
    with A.app.test_request_context(json=CHARGE):
        _f, r, _md, meta, _fmt = A._ao_report(dict(CHARGE))
    attendu = "%d rubriques · %d pièces (%d candidature, %d offre)" % (
        r["etat"]["rubriques"], r["etat"]["pieces"],
        r["etat"]["candidature"], r["etat"]["offre"])
    assert meta["perimetre"] == attendu


def test_le_report_ne_se_declare_pas_produit_par_un_modele():
    import app as A
    with A.app.test_request_context(json=CHARGE):
        _f, _r, _md, meta, _fmt = A._ao_report(dict(CHARGE))
    assert meta["ia"] is False


def test_le_bordereau_est_pose_par_l_aide_et_non_par_les_routes():
    s = source()
    assert corps("_ao_report", s).count("_poser_bordereau(") == 1
    for fn in ("api_datacenter_marche_export", "api_datacenter_marche_dossier_zip"):
        assert "_poser_bordereau(" not in corps(fn, s), (
            "%s pose encore son propre bordereau" % fn)
