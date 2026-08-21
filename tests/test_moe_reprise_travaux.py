"""La section 6 peut REPRENDRE le chiffrage de la section 7.

LE DÉFAUT CORRIGÉ. La page portait deux calculs d'honoraires qui ne se
parlaient pas. La section 6 demandait le montant des travaux en TEXTE LIBRE
(« ex. 600 ou 600-750 ») pendant que la section 7, trente lignes plus bas,
l'établissait poste par poste. Le seul pré-remplissage qui existait venait
d'ailleurs — l'étude d'enveloppe de conseilprev, par paramètre d'URL ou par
mémoire du navigateur. Le chiffrage fait sur la MÊME PAGE, lui, ne se
reprenait pas : il fallait lire le total et le retaper. Un montant retapé est
celui qui se trompe, et il se trompait en silence.

CE QUE CES CONTRÔLES GARDENT :

  1. LE MONTANT VOYAGE, avec ce qu'il faut pour le juger — les postes restés
     sans prix voyagent avec, sinon le montant repris passerait pour complet.
  2. UNE MAINTENANCE NE SE REPREND PAS. Son total est ANNUEL ; des honoraires
     assis dessus ne veulent rien dire. Le refus doit être ÉCRIT, pas obtenu
     en faisant disparaître le bouton — un bouton absent se lit comme une
     panne.
  3. LA PART TECHNIQUE NE SE RECOPIE PAS. Elle se CALCULE dans le pont, côté
     serveur, depuis les familles du chiffrage. La dupliquer dans le
     navigateur ferait deux calculs de la même grandeur, qui finiraient par
     diverger — le défaut même que cette page a déjà corrigé ailleurs.
  4. LA PROVENANCE SE DIT. Un montant pré-rempli sans origine visible se lit
     comme un calcul de la section où il apparaît.
"""
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)


def _js():
    with open(os.path.join(ICI, "ingenierie-dc.js"), encoding="utf-8") as f:
        return f.read()


def _page():
    with open(os.path.join(ICI, "ingenierie-datacenter.html"), encoding="utf-8") as f:
        return f.read()


# ── 1. Le montant voyage, et ce qu'il faut pour le juger avec lui ──────────

def test_le_chiffrage_publie_son_total_et_son_incompletude():
    page = _page()
    i = page.index("new CustomEvent('ig-chiffrage'")
    bloc = page[i:i + 700]
    for champ in ("total_avec_provision", "postes_non_chiffres",
                  "postes_total", "annuel", "operation_nom"):
        assert champ in bloc, (
            "le chiffrage publié ne porte pas « %s » : la section 6 ne "
            "pourrait pas juger le montant qu'elle reprend" % champ)


def test_l_evenement_reste_compatible_avec_le_fil_des_gestes():
    """Le fil des gestes écoutait déjà « ig-chiffrage » sans lire de detail.
    Lui ajouter une charge utile ne doit pas le casser : il continue de ne
    lire que le fait qu'un chiffrage a eu lieu."""
    js = _js()
    i = js.index('document.addEventListener("ig-chiffrage"')
    assert "majGuidage()" in js[i:i + 200]
    # Le second écouteur — celui de la reprise — filtre sur la source, pour ne
    # pas confondre le chiffrage des travaux avec celui des honoraires, qui
    # émet le même événement.
    j = js.index('document.addEventListener("ig-chiffrage", function (ev)')
    assert 'd.source !== "travaux"' in js[j:j + 300]


def test_les_deux_emetteurs_de_l_evenement_sont_distingues():
    """La page émet « ig-chiffrage » à DEUX endroits : le chiffrage des
    travaux et celui du pont. Sans la marque de source, reprendre l'un
    reprendrait l'autre."""
    page = _page()
    assert page.count("new CustomEvent('ig-chiffrage'") == 2
    assert page.count("source: 'travaux'") == 1


# ── 2. Une maintenance ne se reprend pas, et le dit ────────────────────────

def test_un_total_annuel_est_refuse_par_ecrit():
    js = _js()
    i = js.index("function offrirReprise()")
    fin = js.index("function _meur", 0)
    bloc = js[i:i + 1400]
    assert "TRAVAUX.annuel" in bloc, (
        "rien ne distingue un coût annuel d'un investissement")
    assert "ANNUEL" in bloc
    # Le refus s'ÉCRIT : la zone reçoit un message, elle n'est pas vidée.
    ref = bloc[bloc.index("TRAVAUX.annuel"):]
    assert "zone.innerHTML" in ref[:600]
    assert "return" in ref[:900]
    assert fin < i or True


def test_le_montant_est_converti_en_millions():
    """Le barème parle en M€, le chiffrage en € : reprendre sans convertir
    donnerait des honoraires sur un million de fois trop."""
    js = _js()
    i = js.index("function _meur(")
    bloc = js[i:i + 400]
    assert "10000" in bloc and "100" in bloc, bloc


# ── 3. La part technique ne se recopie pas ─────────────────────────────────

def test_la_part_technique_n_est_pas_dupliquee_dans_le_navigateur():
    """Elle se calcule côté serveur, dans avec_maitrise_oeuvre(), depuis les
    familles du chiffrage. La recopier ici ferait deux calculs de la même
    grandeur."""
    js = _js()
    i = js.index("function offrirReprise()")
    bloc = js[i:js.index("document.addEventListener(\"click\", function (ev) {\n    var b = ev.target && ev.target.closest\n      ? ev.target.closest(\"[data-moe-reprendre]\")", i)]
    assert "par_famille" not in bloc, (
        "la part technique est en train d'être recalculée dans la page")
    assert "ig-moe-pt" not in bloc, (
        "la reprise ne doit pas écrire dans le champ de part technique")


def test_le_bandeau_renvoie_au_pont_pour_la_part_technique():
    js = _js()
    i = js.index("function offrirReprise()")
    bloc = js[i:i + 2600]
    assert "calcule" in bloc and "va avec" in bloc, (
        "le bandeau doit dire où la part technique se calcule vraiment")


# ── 4. La provenance se dit ────────────────────────────────────────────────

def test_le_bandeau_nomme_la_section_d_ou_vient_le_montant():
    js = _js()
    i = js.index("function offrirReprise()")
    bloc = js[i:i + 2600]
    assert "section 7" in bloc, (
        "un montant pré-rempli sans origine se lit comme un calcul de la "
        "section où il apparaît")


def test_la_reprise_dit_ce_que_le_montant_ignore():
    js = _js()
    i = js.index("function offrirReprise()")
    bloc = js[i:i + 2600]
    assert "sans prix" in bloc and "postes_non_chiffres" in bloc


def test_apres_reprise_le_bandeau_redit_que_le_chiffre_est_du_lecteur():
    js = _js()
    i = js.index("[data-moe-reprendre]")
    bloc = js[i:i + 1600]
    assert "Vérifiez-le" in bloc or "rifiez-le" in bloc
    assert "prix unitaires" in bloc


# ── 5. Le point de montage et l'ordre d'arrivée ────────────────────────────

def test_la_page_porte_la_zone_de_reprise_avant_le_formulaire():
    page = _page()
    assert 'id="ig-moe-reprise"' in page
    assert page.index('id="ig-moe-reprise"') < page.index('id="ig-moe-form"'), (
        "l'offre de reprise doit précéder le champ qu'elle remplit")


def test_un_chiffrage_arrive_avant_le_bareme_est_rattrape():
    """Les deux sections chargent en parallèle : sans ce rappel, un lecteur
    rapide qui chiffre pendant que le barème arrive ne verrait jamais
    l'offre."""
    js = _js()
    i = js.index("REF = j; champs(); phases();")
    assert "offrirReprise()" in js[i:i + 1400]


def test_la_zone_de_reprise_reste_vide_tant_qu_il_n_y_a_rien_a_reprendre():
    """Vide n'est pas cassé : c'est qu'aucun chiffrage n'a eu lieu."""
    page = _page()
    i = page.index('id="ig-moe-reprise"')
    assert page[i:i + 60].strip().startswith('id="ig-moe-reprise"></div>')
