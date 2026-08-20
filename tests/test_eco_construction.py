"""L'ÉCONOMISTE DE LA CONSTRUCTION — la discipline qui manquait, et ses attaches.

CE QUE SON ABSENCE COÛTAIT, ET POURQUOI ELLE NE SE VOYAIT PAS. Le référentiel
portait quinze disciplines et pas celle-là. Ses livrables, eux, étaient bien au
registre — estimation par lot, décomposition du prix, écart au budget — mais
rattachés au management du design et à la conduite de projet. Or ces deux-là
COORDONNENT le chiffrage, elles ne le produisent pas. Un maître d'ouvrage qui
cherchait « qui établit la DPGF » ne trouvait personne.

UNE DISCIPLINE NE S'AJOUTE PAS EN UNE LIGNE, et c'est tout l'objet de ce
fichier. Elle vit à cinq endroits, et il suffit d'en oublier un pour qu'elle
paraisse posée tout en étant creuse :

  1. la table des disciplines — sinon elle n'existe pas ;
  2. le vocabulaire de repli — sinon une recherche sur son nom ne ramène rien ;
  3. les sous-dossiers de la base de connaissance — sinon la remontée
     documentaire est vide, SANS ERREUR : le module le dit lui-même en
     commentaire, « la recette le voit, l'exploitation non » ;
  4. un thème du guide — sinon elle n'apparaît dans aucun parcours ;
  5. au moins une pièce — sinon on peut la sélectionner et ne rien obtenir.

Les contrôles ci-dessous tiennent ces cinq points, et le dernier vérifie que
les disciplines auxquelles on a repris ces pièces n'ont pas été vidées.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collections import Counter
import ingenierie_dc as ID

CLE = "eco_construction"


def _pieces_par_discipline():
    """Recompté depuis le registre, jamais recopié : une liste écrite à la main
    cesserait d'être vraie à la première pièce ajoutée."""
    c = Counter()
    for p in ID.PHASES:
        for x in ID.pieces(p["code"]):
            if x.get("discipline"):
                c[x["discipline"]] += 1
    return c


def test_la_discipline_existe_et_se_nomme():
    d = ID.DISCIPLINES.get(CLE)
    assert d, "la discipline n'est pas au référentiel"
    assert "conomie de la construction" in d["nom"], d["nom"]
    # L'aide doit DIRE le métier, pas le paraphraser : ce référentiel refuse
    # ailleurs les libellés qui n'apprennent rien.
    assert len(d["aide"]) > 200, len(d["aide"])
    for mot in ("quantitatif", "prix", "budget"):
        assert mot in d["aide"].lower(), mot


def test_LE_POINT_QUI_DECIDE_elle_porte_des_pieces():
    """Une discipline sans pièce se sélectionne et ne rend rien. Aucune des
    quinze autres n'était dans ce cas ; la seizième ne doit pas l'être."""
    c = _pieces_par_discipline()
    assert c.get(CLE, 0) > 0, "discipline sélectionnable mais vide"
    vides = [k for k in ID.DISCIPLINES if not c.get(k)]
    assert vides == [], "disciplines sans aucune pièce : %s" % vides


def test_les_deux_specifications_reprises_sont_BIEN_les_siennes():
    """L'agrégation financière et l'étude forfaitaire sont du chiffrage, pas de
    la coordination. Ce contrôle nomme les deux codes : un déplacement futur
    vers une autre discipline devra être délibéré."""
    trouve = {}
    for p in ID.PHASES:
        for x in ID.pieces(p["code"]):
            if x["code"] in ("SPC-COUTAG", "SPC-FORFAIT"):
                trouve[x["code"]] = x["discipline"]
    assert trouve.get("SPC-COUTAG") == CLE, trouve
    assert trouve.get("SPC-FORFAIT") == CLE, trouve


def test_les_disciplines_qui_les_portaient_ne_sont_pas_VIDEES():
    """Reprendre des pièces à une discipline ne doit pas la réduire à rien :
    le management du design et la conduite de projet gardent l'essentiel de
    leur registre, parce que leur objet n'était pas le chiffrage."""
    c = _pieces_par_discipline()
    assert c.get("design_mgmt", 0) > 50, c.get("design_mgmt")
    assert c.get("projet", 0) > 50, c.get("projet")


def test_elle_est_CHERCHABLE_par_son_vocabulaire():
    """Sans repli, une recherche sur « DPGF » ou « quantitatif » ne ramènerait
    rien pour cette discipline."""
    v = ID._RECHERCHE_DISCIPLINE.get(CLE, "")
    assert v, "aucun vocabulaire de repli"
    assert len(v.split()) >= 6, v
    for mot in ("DPGF", "estimation", "quantitatif"):
        assert mot.lower() in v.lower(), mot
    # …et la santé du module ne doit pas la compter parmi les oubliées.
    assert CLE not in ID.sante()["disciplines_sans_vocabulaire_de_repli"]


def test_LE_POINT_QUI_DECIDE_ses_sous_dossiers_EXISTENT_DEJA():
    """LE PIÈGE QUE LE MODULE SIGNALE LUI-MÊME. Un sous-dossier inventé ne lève
    aucune erreur : la recherche documentaire remonte simplement vide. Les deux
    retenus doivent donc être déjà employés par d'autres disciplines."""
    mien = ID.SOUS_DOSSIERS_DISCIPLINE.get(CLE)
    assert mien, "aucun sous-dossier"
    connus = set()
    for cle, v in ID.SOUS_DOSSIERS_DISCIPLINE.items():
        if cle != CLE:
            connus |= set(v)
    for d in mien:
        assert d in connus, (
            "« %s » n'est employé par aucune autre discipline : dossier "
            "probablement inexistant, la recherche remonterait vide sans erreur" % d)


def test_elle_apparait_dans_le_theme_du_cout():
    """Sans thème, la discipline n'entre dans aucun parcours guidé."""
    cout = [t for t in ID.THEMES_GUIDE if t["id"] == "cout"]
    assert cout, "le thème « coût » a disparu"
    assert CLE in cout[0]["disciplines"], cout[0]["disciplines"]
    # La conduite de projet y reste : le pilotage du budget n'est pas le
    # chiffrage, et les deux se lisent ensemble sur ce thème.
    assert "projet" in cout[0]["disciplines"], cout[0]["disciplines"]


def test_le_glossaire_servi_aux_PAGES_porte_les_seize_disciplines():
    """Une discipline connue du module mais absente du glossaire servi ne sert
    à personne : c'est ce glossaire qui alimente les étiquettes et les
    infobulles de la page. Le référentiel, lui, ne publie pas cette table —
    il publie les pièces, qui la citent par sa clé."""
    # LE CHEMIN RÉEL, pas la fonction interne : c'est `referentiel()` que la
    # route /api sert à la page, et le glossaire y est imbriqué. Contrôler
    # `glossaire()` seul laisserait passer une régression qui casserait
    # l'imbrication sans toucher la fonction.
    g = ID.referentiel()["glossaire"]["discipline"]
    assert CLE in g, sorted(g)
    assert len(g) == len(ID.DISCIPLINES), (len(g), len(ID.DISCIPLINES))
    # …et l'étiquette servie est bien le nom, pas la clé brute.
    libelle = g[CLE]
    texte = libelle if isinstance(libelle, str) else libelle.get("nom", "")
    assert "conomie" in texte, texte


def test_la_sante_du_module_ne_signale_aucune_incoherence():
    """Les gardes existantes du module portent sur les disciplines : elles
    doivent rester muettes après l'ajout."""
    s = ID.sante()
    assert s["disciplines_inconnues"] == [], s["disciplines_inconnues"]
    assert s["guide_disciplines_inconnues"] == [], s["guide_disciplines_inconnues"]
    assert s["guide_themes_vides"] == [], s["guide_themes_vides"]
