# -*- coding: utf-8 -*-
"""LE FORMULAIRE ACCEPTAIT TOUT SANS RIEN DIRE, PUIS LE SERVEUR ÉCARTAIT.

Le serveur borne désormais chaque grandeur à son domaine physique. Restait le
geste de saisie : rien ne disait, AU MOMENT OÙ L'ON TAPE, si la valeur serait
prise. Le lecteur remplissait dix champs, lançait l'étude, et découvrait
ensuite lesquels avaient été écartés — ou pire, ne le découvrait pas.

DEUX ÉTATS, ET UN TROISIÈME QUI N'EN EST PAS UN.
  VERT — la valeur est recevable, le calcul la prendra.
  BLEU — elle ne l'est pas, et le champ dit POURQUOI. Pas « erreur » : la
         raison. « C'est une part : entre 0 et 1 » se corrige ; « champ
         invalide » ne se corrige pas.
  VIDE — ni l'un ni l'autre. Un champ non rempli est un choix, pas un défaut,
         et le colorer transformerait un formulaire de dix champs facultatifs
         en dix reproches.

LA DISTINCTION QUI DÉCIDE DE TOUT. Le DOMAINE n'est pas la PLAGE OBSERVÉE. Un
centre de 15 kW sort du cadrage du cabinet et se calcule très bien : il doit
être VERT, avec sa note. Le peindre en bleu priverait son auteur d'un résultat
juste — c'est le défaut symétrique, aussi grave que l'autre, et une règle le
garde.

LA COULEUR N'EST JAMAIS SEULE. `aria-invalid` sur le champ, un message en clair
sous lui : un liseré ne s'entend pas, et huit pour cent des hommes distinguent
mal le vert du bleu.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import datacenter  # noqa: E402

MOTEUR = io.open(os.path.join(ICI, "datacenter.js"), encoding="utf-8").read()
PAGE = io.open(os.path.join(ICI, "datacenter.html"), encoding="utf-8").read()
NODE = shutil.which("node")

CHAMPS = {c["id"]: c for c in datacenter.CHAMPS if c["type"] == "nombre"}


def _fn(nom):
    d = MOTEUR.index("function %s(" % nom)
    return MOTEUR[d:MOTEUR.index("\n  }", d) + 4]


def _verdict(champ_id, valeur):
    """Évalue le VRAI code de la page, tel qu'il est servi."""
    if not NODE:
        pytest.skip("node absent : le verdict ne peut pas être évalué")
    prog = (_fn("verdictSaisie")
            + "\nconsole.log(JSON.stringify(verdictSaisie(%s, %s)));"
            % (json.dumps(CHAMPS[champ_id], ensure_ascii=False, default=str),
               json.dumps(valeur)))
    r = subprocess.run([NODE, "-e", prog], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        pytest.fail("verdictSaisie ne s'évalue pas :\n%s" % (r.stderr or "")[-900:])
    return json.loads(r.stdout)


# ── 1. LES TROIS ÉTATS ───────────────────────────────────────────────────

@pytest.mark.parametrize("vide", ["", None])
def test_un_champ_vide_n_est_ni_vert_ni_bleu(vide):
    """Un champ non rempli est un CHOIX. Le colorer transformerait un
    formulaire de dix champs facultatifs en dix reproches, et le lecteur
    apprendrait à ignorer la couleur — ce qui la rendrait inutile là où elle
    compte."""
    assert _verdict("taux_charge", vide) is None


@pytest.mark.parametrize("champ,valeur", [
    ("taux_charge", "0.65"), ("part_renouvelable", "0.4"),
    ("pue_cible", "1.3"), ("prix_electricite_eur_mwh", "110"),
    ("nb_serveurs", "2500"), ("puissance_it_kw", "1000"),
])
def test_une_valeur_recevable_est_verte(champ, valeur):
    v = _verdict(champ, valeur)
    assert v and v["ok"], "%s = %s devrait être recevable : %r" % (champ, valeur, v)


@pytest.mark.parametrize("champ,valeur", [
    ("taux_charge", "1.5"), ("taux_charge", "0"),
    ("part_renouvelable", "-99"), ("part_evaporative", "2"),
    ("pue_cible", "0.5"), ("cycles_concentration", "0.5"),
    ("puissance_it_kw", "0"), ("intensite_reseau_g", "-1"),
])
def test_une_valeur_hors_domaine_est_bleue_et_dit_pourquoi(champ, valeur):
    v = _verdict(champ, valeur)
    assert v and not v["ok"], "%s = %s est accepté" % (champ, valeur)
    assert len(v.get("pourquoi") or "") > 25, (
        "%s = %s est refusé sans raison lisible : « %s »"
        % (champ, valeur, v.get("pourquoi")))


@pytest.mark.parametrize("valeur", ["abc", "75 %", "nan", "inf", "1e400"])
def test_une_saisie_illisible_ou_non_finie_est_bleue(valeur):
    """« nan » et « inf » sont des nombres pour `parseFloat` comme pour
    `float()` : sans le contrôle du fini, ils passeraient au vert ici avant
    d'être écartés là-bas."""
    v = _verdict("taux_charge", valeur)
    assert v and not v["ok"], "« %s » passe pour recevable" % valeur


# ── 2. LE DOMAINE N'EST PAS LA PLAGE OBSERVÉE ────────────────────────────

def test_une_valeur_hors_plage_observee_reste_verte():
    """LE DÉFAUT SYMÉTRIQUE. La plage observée du cabinet commence à 20 kW ; un
    centre de 15 kW est réel et se calcule très bien. Le peindre en bleu dirait
    à son auteur que sa saisie est fautive alors qu'elle ne l'est pas."""
    v = _verdict("puissance_it_kw", "15")
    assert v and v["ok"], (
        "15 kW est marqué comme non recevable : le cadrage du cabinet a été "
        "confondu avec le domaine physique")


def test_la_note_de_plage_ne_s_affiche_pas_sur_une_valeur_ecartee():
    """Superposer « c'est rare » et « ça n'entrera pas dans le calcul » donne
    deux messages contradictoires sur le même champ."""
    corps = _fn("controlerPlages")
    # DEUX BORNAGES SUCCESSIFS, ET CHACUN APPRENAIT QUELQUE CHOSE.
    #
    # La première version coupait à la première occurrence d'« ig-hors » — qui
    # est le RETRAIT de l'ancienne note, pas sa création : elle accusait un code
    # juste.
    #
    # La seconde coupait à la création et cherchait « !verdict.ok » n'importe où
    # avant. Elle a laissé SURVIVRE la mutation qui retire la garde : le motif
    # existe aussi dans le bloc du liseré, deux dizaines de lignes plus haut.
    # Une règle qui cherche loin trouve toujours.
    #
    # On borne donc à la SECTION de la plage observée : entre la fin du bloc de
    # refus et la fabrication de la note, il n'y a qu'une garde possible.
    i_refus = corps.index("lab.appendChild(r)")
    i_note = corps.index('n.className = "ig-hors"')
    garde = corps[i_refus:i_note]
    assert "verdict.ok" in garde, (
        "la note de plage est fabriquée sans vérifier que la valeur est "
        "recevable : « c'est rare » et « ça n'entrera pas dans le calcul » se "
        "superposeront sur le même champ")


# ── 3. LA COULEUR N'EST JAMAIS SEULE ─────────────────────────────────────

def test_le_refus_pose_aria_invalid():
    """Un liseré ne s'entend pas. Sans `aria-invalid`, une saisie écartée est
    invisible pour qui n'a pas l'écran."""
    assert 'setAttribute("aria-invalid", "true")' in _fn("controlerPlages")


def test_le_refus_est_aussi_ecrit_en_clair():
    corps = _fn("controlerPlages")
    assert "dc-refus" in corps and "n'entrera pas dans le calcul" in corps


def test_l_etat_precedent_est_efface_avant_le_nouveau():
    """Sans retrait, un champ corrigé garderait son liseré bleu et son message :
    le lecteur corrigerait sans jamais voir que c'est bon."""
    corps = _fn("controlerPlages")
    assert 'classList.remove("dc-ok", "dc-ko")' in corps
    assert 'removeAttribute("aria-invalid")' in corps
    assert corps.count("if (vieux") + corps.count("if (vieuxR") >= 2


@pytest.mark.parametrize("classe", ["dc-ok", "dc-ko", "dc-refus", "dc-dom",
                                    "dc-av", "dc-suite"])
def test_chaque_classe_employee_est_stylee(classe):
    """LA CSS DÉCIDE DE L'APPARENCE, PAS L'INTENTION. Une classe posée par le
    script et absente de la feuille ne colore rien, et rien ne le signale."""
    assert re.search(r"\.%s[\s,{:.>]" % re.escape(classe), PAGE), (
        "la classe « %s » est posée par le script et stylée nulle part" % classe)


def test_le_vert_et_le_bleu_sont_bien_deux_couleurs_distinctes():
    """Une règle qui vérifie deux classes sans vérifier qu'elles diffèrent
    laisserait passer un copier-coller qui peint tout de la même couleur."""
    def bord(classe):
        m = re.search(r"\.dc-champ\.%s>input[^{]*\{([^}]*)\}" % classe, PAGE)
        assert m, "la classe %s n'a pas de bordure définie" % classe
        return re.search(r"border-color:([^;]+)", m.group(1)).group(1).strip()
    assert bord("dc-ok") != bord("dc-ko"), (
        "recevable et écarté portent la même couleur de bordure")


# ── 4. LES BORNES VIENNENT DU SERVEUR ────────────────────────────────────

def test_la_page_ne_tient_aucune_table_de_bornes():
    """Une seconde source diverge, et c'est la page qui laisse alors passer ce
    que le serveur refusera — le pire des deux, puisque l'utilisateur aura vu
    du vert."""
    corps = _fn("verdictSaisie")
    assert "c.domaine" in corps or "d = c.domaine" in corps
    for id_champ in CHAMPS:
        assert '"%s"' % id_champ not in corps, (
            "« %s » est nommé dans le verdict : la page décide au lieu de lire "
            "le référentiel" % id_champ)


def test_les_bornes_sont_posees_sur_le_champ_lui_meme():
    """Le navigateur et l'assistance vocale les lisent là — pas dans un script
    qu'ils n'exécutent pas."""
    corps = MOTEUR[MOTEUR.index("function bâtirFormulaire"):]
    corps = corps[:corps.index("\n  }")]
    assert 'data-min="' in corps and 'data-max="' in corps
    assert 'aria-describedby="' in corps, (
        "le domaine n'est pas rattaché au champ : il ne sera pas annoncé")


def test_chaque_champ_annonce_ses_valeurs_admises():
    corps = MOTEUR[MOTEUR.index("function bâtirFormulaire"):]
    assert "Valeurs admises" in corps[:corps.index("\n  }")]


# ── 5. L'AVANCEMENT COMPTE CE QUI ENTRERA DANS LE CALCUL ─────────────────

def test_l_avancement_compte_les_champs_recevables_et_non_remplis():
    """Compter une saisie écartée mentirait sur l'avancement : le lecteur
    croirait avoir renseigné dix champs quand le calcul n'en verra que sept."""
    corps = _fn("majAvancement")
    assert "verdictSaisie" in corps, (
        "l'avancement compte les champs remplis sans vérifier qu'ils sont "
        "recevables")
    assert "v.ok" in corps


def test_l_avancement_dit_ce_qui_retient_l_etude():
    corps = _fn("majAvancement")
    assert "puissance_it_kw" in corps and "nécessaire" in corps, (
        "l'avancement ne nomme pas le champ sans lequel rien ne se calcule")


def test_la_zone_d_avancement_existe_dans_la_page():
    assert 'id="dc-avancement"' in PAGE
    assert 'aria-live="polite"' in PAGE[PAGE.index('id="dc-avancement"') - 200:
                                        PAGE.index('id="dc-avancement"') + 200], (
        "l'avancement change sans être annoncé : un lecteur d'écran ne saura "
        "pas que le compte a bougé")


# ── 6. LA FLÈCHE VERS L'ÉTAPE SUIVANTE ───────────────────────────────────

def test_la_fleche_ne_pointe_que_vers_une_etape_visible():
    """Une flèche vers un bloc masqué envoie sur du vide — et le lecteur
    apprend à ne plus la regarder, ce qui perd toute la signalétique."""
    corps = _fn("majSuites")
    # « hidden in corps » A LAISSÉ SURVIVRE la mutation qui retire le filtre :
    # le mot restait ailleurs. C'est le FILTRE qu'on vérifie, pas la présence
    # d'un mot quelque part dans la fonction.
    assert "!s.hidden" in corps, (
        "les sections ne sont pas filtrées sur leur visibilité : la flèche "
        "enverra vers un bloc masqué, c'est-à-dire vers rien")
    assert re.search(r"visibles\s*=\s*sections\.filter", corps), (
        "« visibles » ne dérive plus d'un filtre : le nom ment sur ce qu'il "
        "contient")


def test_la_fleche_se_recalcule_quand_la_suite_change():
    """Après le calcul, trois sections s'ouvrent : la suivante n'est plus la
    même. Une flèche posée une fois pointerait vers l'étape d'avant."""
    assert MOTEUR.count("majSuites();") >= 3, (
        "la flèche n'est recalculée qu'à %d endroit(s) : elle se périmera à "
        "l'ouverture des sections" % MOTEUR.count("majSuites();"))


def test_la_derniere_etape_ne_porte_pas_de_fleche():
    corps = _fn("majSuites")
    assert "if (!suivante) return;" in corps


def test_le_focus_suit_le_defilement():
    """Sans lui, la tabulation repart du haut du document : le geste n'aurait
    servi qu'à la souris."""
    corps = _fn("majSuites")
    assert "focus(" in corps and "tabindex" in corps


def test_le_defilement_respecte_la_preference_de_mouvement():
    corps = _fn("majSuites")
    assert "prefers-reduced-motion" in corps and '"auto"' in corps


def test_la_fleche_dit_ou_elle_mene():
    """« Suivant » n'apprend rien. Le nom de l'étape, et le rang, disent où
    l'on va et combien il en reste."""
    corps = _fn("majSuites")
    assert "Étape " in corps and "aria-label" in corps
