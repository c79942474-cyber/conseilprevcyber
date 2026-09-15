# -*- coding: utf-8 -*-
"""Le guide de parcours DIT ce que la page fait — et on le mesure.

LE DÉFAUT QU'ON CORRIGE, ET IL EST D'UN GENRE PARTICULIER. Rien n'était cassé :
les sept étapes se mesuraient, la route les rendait, les règles étaient vertes.
Le guide était simplement DEVENU FAUX, en cinq tours, sans qu'aucune règle
n'ait de raison de tomber — parce qu'aucune ne comparait ce qu'il promet à ce
que la page offre.

    · « Déposez les pièces du dossier de consultation » — il y a DEUX zones
      depuis, l'acheteur à gauche et le cabinet à droite, et se tromper de
      côté fait lire un mémoire comme un règlement.
    · « Parcourez les pièces » — l'atelier lit, remplit, rédige et relit d'un
      geste ; toute rubrique se corrige à la main ; la carte s'ouvre en grand.
    · « le report et les quatre formulaires officiels » — l'archive porte
      désormais les vingt-trois pièces une à une et les brouillons rédigés.
    · Et le geste qui décide de TOUT le reste — quelles pièces cette
      consultation demande — n'était pas une étape du tout.

UN GUIDE FAUX EST PIRE QU'UN GUIDE ABSENT : on le suit. Ces règles comparent
donc chaque promesse à la chose promise, dans le module ou dans la page.
"""
import io
import os
import re

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import ao_dc as A                                                # noqa: E402
import ao_parcours as P                                          # noqa: E402


def _src(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


def _etape(cle):
    return next(e for e in P.ETAPES if e["id"] == cle)


def _texte(e):
    """Tout ce que l'étape DIT — c'est cela que le lecteur suit."""
    return " ".join(str(e.get(k) or "") for k in
                    ("nom", "question", "pourquoi", "geste", "piege"))


# ═══════════════════════════════════════════════════════════════════════════
#  LE GESTE QUI DÉCIDE DE TOUT LE RESTE EST UNE ÉTAPE
# ═══════════════════════════════════════════════════════════════════════════

def test_choisir_les_pieces_EST_une_etape_et_precede_ce_qu_elle_commande():
    """Le périmètre décide des attestations à réclamer, des rubriques à
    remplir et du contenu de l'archive.

    Le placer après le remplissage ferait remplir des pièces qu'on ne dépose
    pas, et demander des attestations dont on n'a pas besoin — trois semaines
    d'attente pour rien.
    """
    ids = [e["id"] for e in P.ETAPES]
    assert "choisir" in ids, (
        "le parcours ne nomme pas le geste qui fixe le périmètre : %s" % ids)
    for apres in ("attestations", "remplir", "emporter"):
        assert ids.index("choisir") < ids.index(apres), (
            "« choisir » arrive après « %s », qu'il commande pourtant" % apres)
    assert ids.index("lire") < ids.index("choisir"), (
        "on choisit les pièces avant d'avoir lu ce que le règlement demande")


def test_l_etape_du_choix_MESURE_la_selection_et_pas_une_impression():
    """Une étape sans nombre n'est pas une étape franchie.

    On la fait tourner sur une sélection réelle et l'on regarde ce qu'elle
    rend : le compte des retenues, celui du catalogue, et le NOM des pièces
    non repérées — « il reste 3 choses » n'aide personne à savoir lesquelles.
    """
    an = A.analyser([{"nom": "RC.pdf", "extension": "pdf",
                      "cote": "consultation",
                      "texte": "Reglement de la consultation."}])
    sel = A.selection(an)
    r = _etape("choisir")["mesurer"]({"selection": sel})

    assert str(sel["catalogue"]) in r["mesure"], r["mesure"]
    assert str(sel["retenues"]) in r["mesure"], r["mesure"]
    assert r["reste"] and all(isinstance(x, str) and x for x in r["reste"])
    # ET SANS DOSSIER, ELLE NE SE DÉCLARE PAS FAITE — elle dit ce qu'elle
    # mesurerait. Une étape verte sur un dossier vide ferait croire le
    # périmètre arrêté.
    vide = _etape("choisir")["mesurer"]({})
    assert vide["fait"] is False and str(P.PIECES_REPONSE) in vide["mesure"]

    # ZÉRO PIÈCE RETENUE N'EST PAS UN PÉRIMÈTRE ARRÊTÉ, et une mutation a
    # survécu à la première version de cette règle : elle n'éprouvait que le
    # cas « aucune sélection du tout », qui sort par une autre porte —
    # l'expression de `fait` n'était jamais atteinte. On pose donc le cas qui
    # la traverse : des lignes, et rien de retenu. C'est précisément l'état
    # d'un dossier dont le règlement ne cite aucune pièce, celui qui appelle
    # la déroulante des non repérées.
    rien = _etape("choisir")["mesurer"](
        {"selection": dict(sel, retenues=0,
                           lignes=[dict(x, retenue=False)
                                   for x in sel["lignes"]])})
    assert rien["fait"] is False, (
        "une sélection qui ne retient AUCUNE pièce se déclare faite : le "
        "parcours dirait le périmètre arrêté sur un dossier vide")
    assert r["fait"] is True, (
        "le témoin positif est cassé : une vraie sélection n'est pas faite")


def test_le_compte_du_catalogue_est_LU_sur_le_module():
    """Recopier « 23 » ici le ferait mentir au premier ajout de pièce.

    ET LA PREMIÈRE VERSION S'Y ÉTAIT TROMPÉE en le lisant sur `RUBRIQUES`, qui
    ne porte que les pièces AYANT des rubriques — sept sur vingt-trois. Le
    parcours aurait annoncé « sept pièces au catalogue » à côté d'un écran qui
    en montre vingt-trois.
    """
    an = A.analyser([{"nom": "RC.pdf", "extension": "pdf",
                      "cote": "consultation", "texte": "x"}])
    assert P.PIECES_REPONSE == A.selection(an)["catalogue"], (
        P.PIECES_REPONSE, A.selection(an)["catalogue"])
    assert P.PIECES_REPONSE > len(A.RUBRIQUES), (
        "le compte est lu sur la table des rubriques, qui ne couvre pas les "
        "pièces sans rubrique")


# ═══════════════════════════════════════════════════════════════════════════
#  CHAQUE PROMESSE EST COMPARÉE À LA CHOSE PROMISE
# ═══════════════════════════════════════════════════════════════════════════

def test_l_etape_du_depot_annonce_les_DEUX_zones_que_la_page_offre():
    """Se tromper de côté fait lire un mémoire du cabinet comme un règlement
    de l'acheteur — c'est arrivé, et c'est ce qui a motivé la séparation.

    La page offre deux zones ; le guide doit les annoncer. On vérifie les
    deux : le script les rend, et l'étape les nomme.
    """
    js = _src("ingenierie-dc.js")
    cotes = set(re.findall(r'aoBrancherDepot\([^,]+,\s*"(\w+)"', js))
    if not cotes:
        cotes = set(re.findall(r'cote:\s*"(cabinet|consultation)"', js))
    assert {"cabinet", "consultation"} <= cotes, (
        "la page n'a pas deux zones de dépôt : %s" % sorted(cotes))

    t = _texte(_etape("consultation")).lower()
    assert "deux zones" in t, t
    assert "acheteur" in t and "cabinet" in t, t


def test_l_etape_du_remplissage_annonce_l_atelier_et_la_correction_a_la_main():
    """Les deux gestes qui font le remplissage aujourd'hui.

    Le guide disait « parcourez les pièces », ce qui décrit une lecture. Or il
    y a UN bouton qui lit, remplit, rédige et relit — et, depuis, toute
    rubrique se corrige à la main. Taire l'un ou l'autre fait faire à la main
    ce qui se fait d'un clic, ou croire immuable ce qui se corrige.
    """
    t = _texte(_etape("remplir")).lower()
    # LE GESTE, PAS LE MOT. Une mutation a survécu à la première version : elle
    # cherchait « atelier » quelque part, et « l'atelier existe aussi » à côté
    # de « parcourez les pièces » la laissait verte. Ce qu'il faut dire, c'est
    # CE QUE L'ATELIER FAIT — sans quoi on le prend pour une option.
    assert "lancez l'atelier" in t, (
        "le guide nomme l'atelier sans dire de le lancer", t)
    for verbe in ("lit", "remplit", "rédige"):
        assert verbe in t, ("le guide ne dit pas que l'atelier %s" % verbe, t)
    assert "corrig" in t or "à la main" in t, t
    assert "en grand" in t, (
        "le guide ne dit pas qu'une carte s'ouvre pour être remplie", t)

    # ET CE QU'IL ANNONCE EXISTE : le bouton de l'atelier et l'ouverture en
    # grand sont dans la page et dans le script.
    assert 'id="ao-atelier"' in _src("ingenierie-datacenter.html")
    assert "data-ao-ouvrir=" in _src("ingenierie-dc.js")


def test_l_etape_d_emport_decrit_le_contenu_REEL_de_l_archive():
    """Elle promettait « le report et les quatre formulaires » — c'était vrai,
    et ça ne l'est plus : l'archive porte les vingt-trois pièces une à une et
    les brouillons rédigés.

    Une promesse en dessous de la réalité fait redemander à la main ce qu'on
    tient déjà ; au-dessus, elle fait déposer un dossier incomplet.
    """
    t = _texte(_etape("emporter")).lower()
    app = _src("app.py")
    for dossier in ("pieces/", "brouillons/"):
        assert dossier in app, (
            "l'archive ne range plus rien sous « %s »" % dossier)
        assert dossier in t, (
            "le guide ne dit pas que l'archive porte « %s »" % dossier)
    assert "⬇" in t or "carte" in t, (
        "le guide ne dit pas qu'une pièce seule s'emporte", t)


def test_le_guide_de_la_SECTION_dit_le_parcours_et_pas_seulement_l_acces():
    """`data-gd` est ce que le panneau guidé affiche pour cette section.

    Il ne disait QUE la restriction d'accès — vrai, utile, et sans rapport
    avec ce qu'il faut faire. Une section qui explique à qui elle est réservée
    sans dire ce qu'on y fait laisse l'opérateur devant quatorze commandes.
    """
    page = _src("ingenierie-datacenter.html")
    i = page.index('id="ig-ao"')
    bloc = page[max(0, i - 900):i + 900]
    m = re.search(r'data-gd="([^"]*)"', bloc)
    assert m, "la section §14 n'a plus de guide"
    gd = m.group(1).lower()

    # LES GESTES, DANS L'ORDRE DU PARCOURS — et pas une liste de mots-clés :
    # chacun doit apparaître APRÈS le précédent.
    ordre = ["dépos", "choisis", "atelier", "corrig", "déclaration", "archive"]
    pos = [gd.find(x) for x in ordre]
    assert all(p >= 0 for p in pos), (
        "le guide de la section ne nomme pas : %s"
        % [x for x, p in zip(ordre, pos) if p < 0])
    assert pos == sorted(pos), (
        "les gestes ne sont pas dans l'ordre du parcours : %s" % list(zip(ordre, pos)))
    # ET LA RESTRICTION RESTE DITE : elle n'était pas fausse, elle était seule.
    assert "conseilprev" in gd


def test_la_ROUTE_rend_l_etape_du_choix_AVEC_ses_nombres(marche):
    """Le module sait mesurer ; encore faut-il que la route lui donne à
    mesurer.

    UNE MUTATION A SURVÉCU À LA PREMIÈRE VERSION DE CE FICHIER : couper la
    sélection dans l'état transmis laissait toutes les règles vertes — le
    compte des étapes ne bougeait pas, et l'étape se contentait de dire
    « aucun dossier analysé ». L'écran aurait affiché une étape morte à côté
    d'une colonne qui montre vingt-trois pièces.
    """
    from conftest import ORIGINE
    r = marche.post("/api/datacenter/marche/parcours",
                    json={"fiche": {"raison_sociale": "CONSEILPREV"},
                          "analyse": A.analyser(
                              [{"nom": "RC.pdf", "extension": "pdf",
                                "cote": "consultation",
                                "texte": "Reglement de la consultation."}])},
                    headers=ORIGINE)
    assert r.status_code == 200, r.data[:300]
    etapes = {e["id"]: e for e in r.get_json()["parcours"]["etapes"]}
    assert "choisir" in etapes, sorted(etapes)
    m = etapes["choisir"]["mesure"]
    assert str(P.PIECES_REPONSE) in m, (
        "l'étape du choix ne compte pas le catalogue — la sélection "
        "n'atteint pas le module : %r" % m)
    assert "non repérée" in m, m


def test_la_version_du_parcours_a_SUIVI_le_changement():
    """Un parcours dont le contenu change sans que sa version bouge ne se
    compare pas à celui d'hier — et c'est la version que la route rend à la
    page, donc la seule chose qui permette de dire « vous lisez l'ancien »."""
    assert P.VERSION > "2026-09-b", P.VERSION


@pytest.mark.parametrize("cle", [e["id"] for e in P.ETAPES])
def test_aucune_etape_ne_promet_un_controle_qui_n_existe_plus(cle):
    """L'ancre de chaque étape désigne un vrai contrôle.

    La règle existe déjà dans `test_ao_parcours`; celle-ci la double pour la
    NOUVELLE étape, dont l'ancre a été écrite dans le même tour que sa cible —
    c'est exactement le cas où l'on se relit soi-même et où l'on voit ce qu'on
    a voulu écrire.
    """
    a = _etape(cle)["ancre"]
    if not a.startswith("#"):
        return
    page, js = _src("ingenierie-datacenter.html"), _src("ingenierie-dc.js")
    assert ('id="%s"' % a[1:]) in page or ('id="%s"' % a[1:]) in js, (cle, a)
