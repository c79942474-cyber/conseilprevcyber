# -*- coding: utf-8 -*-
"""Choisir une pièce dans la liste déroulante, et que le dossier change.

CE QUI EXISTAIT, ET POURQUOI ÇA NE SUFFISAIT PAS. Les trois groupes de la
colonne « Les documents à produire » — dossier de candidature, dossier
d'offre, pièces non repérées — portaient chacun une liste déroulante. Elle ne
servait qu'à ATTEINDRE une pièce plus bas dans la page, et c'était écrit dans
le script en toutes lettres :

    « LA DÉROULANTE MÈNE À LA PIÈCE dans le dossier rempli, en dessous : elle
      sert à ATTEINDRE, pas à choisir. Un sélecteur qui modifierait la
      sélection ferait de chaque parcours de la liste une décision. »

Pour ajouter une pièce non repérée, il fallait donc la retrouver dans la liste
détaillée en dessous — quinze lignes avec leur motif et leur citation — et y
presser « ajouter ». La déroulante nommait les pièces sans permettre de les
prendre.

CE QUI CHANGE, ET CE QUI EST GARDÉ DE L'ANCIENNE DÉCISION. La déroulante
CHOISIT désormais ; un bouton nommé AGIT. Parcourir reste gratuit — le souci
d'origine est juste : dérouler quinze noms pour voir ce qu'ils sont ne doit
pas engager le dossier. Il faut un second geste, et ce geste dit sur quelle
pièce il porte : « ＋ Ajouter : Convention de groupement », pas « Appliquer ».

CE QUE CES RÈGLES MESURENT. Le geste entier, exécuté : on rend la colonne, on
la branche, on choisit une option, on presse le bouton — et l'on regarde ce
qui part au moteur. Une règle qui chercherait « data-sel-agir » dans le
fichier serait verte avec un bouton que personne n'écoute.
"""
import io
import json
import os
import re
import subprocess

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import ao_dc as A                                                # noqa: E402


def _js_source(*noms):
    src = io.open(os.path.join(ICI, "ingenierie-dc.js"), encoding="utf-8").read()
    out = []
    for nom in noms:
        i = src.index("\n  function %s(" % nom) + 1
        p, k = 1, src.index("{", i) + 1
        while p:
            p += 1 if src[k] == "{" else (-1 if src[k] == "}" else 0)
            k += 1
        out.append(src[i:k])
    return "\n".join(out)


# ═══════════════════════════════════════════════════════════════════════════
#  UN DOM RÉDUIT — mais qui rend vraiment les options et écoute les clics
# ═══════════════════════════════════════════════════════════════════════════
#
# POURQUOI PAS UN VRAI NAVIGATEUR ICI. La maison tient les scripts de
# navigateur hors de `tests/`. Le double n'implémente que ce que le rendu et
# le brancheur touchent — un analyseur d'options, `querySelector`,
# `addEventListener`, `dataset` — et RIEN de plus, pour qu'une règle verte
# veuille dire quelque chose.
DOM = r"""
function Noeud(html, attrs) {
  this.html = html || "";
  this.dataset = attrs || {};
  this.disabled = false;
  this.textContent = "";
  this.value = "";
  this.options = [];
  this.selectedIndex = -1;
  this._ecoute = {};
}
Noeud.prototype.addEventListener = function (n, f) {
  (this._ecoute[n] = this._ecoute[n] || []).push(f);
};
Noeud.prototype.declencher = function (n) {
  (this._ecoute[n] || []).forEach(function (f) { f({}); });
};
Noeud.prototype.choisir = function (valeur) {
  for (var i = 0; i < this.options.length; i++) {
    if (this.options[i].value === valeur) {
      this.value = valeur; this.selectedIndex = i;
      this.declencher("change");
      return true;
    }
  }
  return false;
};

/* LES SÉLECTEURS ET LES BOUTONS SONT LUS SUR LE HTML RENDU, pas fabriqués à
   côté : c'est ce qui fait que ces règles mesurent le rendu et non un décor
   que la règle se serait donné. */
function analyser(html) {
  var noeuds = [], m;
  var reSel = /<select([^>]*)>([\s\S]*?)<\/select>/g;
  while ((m = reSel.exec(html))) {
    var n = new Noeud(m[0], attributs(m[1]));
    var reOpt = /<option value="([^"]*)"[^>]*>([\s\S]*?)<\/option>/g, o;
    while ((o = reOpt.exec(m[2]))) {
      n.options.push({ value: o[1], textContent: o[2] });
    }
    noeuds.push(n);
  }
  var reBtn = /<button([^>]*)>([\s\S]*?)<\/button>/g;
  while ((m = reBtn.exec(html))) {
    var b = new Noeud(m[0], attributs(m[1]));
    b.textContent = m[2];
    b.disabled = / disabled/.test(m[1]);
    noeuds.push(b);
  }
  return noeuds;
}
function attributs(txt) {
  var d = {}, m, re = /data-([a-z-]+)="([^"]*)"/g;
  while ((m = re.exec(txt))) {
    d[m[1].replace(/-([a-z])/g, function (_, c) { return c.toUpperCase(); })]
      = m[2];
  }
  return d;
}
function Zone(html) { this.innerHTML = html; this.noeuds = analyser(html); }
Zone.prototype.querySelectorAll = function (sel) {
  var m = /\[data-([a-z-]+)\]/.exec(sel);
  if (!m) return [];
  var cle = m[1].replace(/-([a-z])/g, function (_, c) { return c.toUpperCase(); });
  return this.noeuds.filter(function (n) { return n.dataset[cle] !== undefined; });
};
Zone.prototype.querySelector = function (sel) {
  var m = /\[data-([a-z-]+)="([^"]*)"\]/.exec(sel);
  if (!m) return null;
  var cle = m[1].replace(/-([a-z])/g, function (_, c) { return c.toUpperCase(); });
  var t = this.noeuds.filter(function (n) { return n.dataset[cle] === m[2]; });
  return t[0] || null;
};
"""


def _node(prog):
    out = subprocess.run(["/opt/node22/bin/node"], input=prog,
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr[-2500:]
    return out.stdout


def _selection(ajouts=None, ecartees=None):
    """La sélection réelle du moteur — jamais une maquette.

    Un dossier de démonstration où RIEN n'est cité : le règlement ne nomme
    aucune pièce, donc tout tombe dans « non repérées » et les deux autres
    groupes sont vides. C'est le cas qui a motivé la demande.
    """
    an = A.analyser([{"nom": "RC.pdf", "extension": "pdf",
                      "cote": "consultation",
                      "texte": "Reglement de la consultation. "
                               "Le pouvoir adjudicateur passe ce marche."}])
    return A.selection(an, ajouts=ajouts, ecartees=ecartees)


def _ecran(sel):
    """Le HTML rendu, et le journal de ce que les gestes envoient au moteur."""
    prog = (DOM
            + _js_source("esc", "aoSelectionRendre", "aoSelectionBrancher",
                         "aoVueOptions", "aoVueAppliquer", "aoVueBrancher")
            + """
    var AO_SELECTION = null, AO_VUE = {};
    var AO_SEL_AJOUTS = {}, AO_SEL_ECARTEES = {};
    var JOURNAL = [];
    function aoSelectionRecalculer() {
      JOURNAL.push({ajouts: Object.keys(AO_SEL_AJOUTS),
                    ecartees: Object.keys(AO_SEL_ECARTEES)});
    }
    var zone = null;
    function $(s, p) { return s === "#ig-ao-retenus" ? zone : null; }
    global.document = { getElementById: function () { return null; } };

    var sel = JSON.parse(process.env.SEL || "null");
    zone = { innerHTML: "", querySelectorAll: function () { return []; },
             querySelector: function () { return null; } };
    aoSelectionRendre(sel);
    var html = zone.innerHTML;

    /* ON REBRANCHE SUR LE HTML RÉELLEMENT PRODUIT : le rendu écrit dans une
       zone muette, puis on analyse ce qu'il a écrit et l'on branche dessus.
       Brancher sur autre chose que ce qui est rendu mesurerait deux écrans. */
    var vraie = new Zone(html);
    aoSelectionBrancher(vraie);

    var ordre = JSON.parse(process.env.GESTES || "[]");
    var faits = [];
    ordre.forEach(function (g) {
      var sl = vraie.querySelector('[data-sel-liste="' + g.groupe + '"]');
      var bt = vraie.querySelector('[data-sel-agir="' + g.groupe + '"]');
      if (!sl || !bt) { faits.push({groupe: g.groupe, erreur: "absent"}); return; }
      var avant = {libelle: bt.textContent, eteint: bt.disabled};
      var ok = g.valeur === null ? true : sl.choisir(g.valeur);
      var apres = {libelle: bt.textContent, eteint: bt.disabled};
      if (g.presser) bt.declencher("click");
      faits.push({groupe: g.groupe, choisi: ok, avant: avant, apres: apres});
    });
    process.stdout.write(JSON.stringify(
      {html: html, journal: JOURNAL, faits: faits,
       options: vraie.querySelectorAll("[data-sel-liste]").map(function (s) {
         return {groupe: s.dataset.selListe,
                 valeurs: s.options.map(function (o) { return o.value; })};
       })}));
    """)
    return prog


def _jouer(sel, gestes):
    import subprocess as sp
    out = sp.run(["/opt/node22/bin/node"], input=_ecran(sel),
                 capture_output=True, text=True, timeout=60,
                 env=dict(os.environ, SEL=json.dumps(sel),
                          GESTES=json.dumps(gestes)))
    assert out.returncode == 0, out.stderr[-2500:]
    return json.loads(out.stdout)


GROUPES = ("candidature", "offre", "__non")


# ═══════════════════════════════════════════════════════════════════════════
#  LES TROIS GROUPES PORTENT LEUR LISTE, ET ELLE CONTIENT LEURS PIÈCES
# ═══════════════════════════════════════════════════════════════════════════

def test_les_TROIS_groupes_portent_une_liste_qui_nomme_LEURS_pieces():
    """Une liste qui existe mais ne contient pas les bonnes pièces ne sert à
    rien, et se repère mal : elle a l'air de fonctionner.

    On compare les options de chaque liste aux lignes que le MOTEUR range dans
    ce groupe — jamais à une liste recopiée ici, qui divergerait du jour où le
    catalogue change.
    """
    sel = _selection()
    r = _jouer(sel, [])
    par_groupe = {o["groupe"]: o["valeurs"] for o in r["options"]}

    attendu = {
        "candidature": [x["cle"] for x in sel["lignes"]
                        if x["retenue"] and x["dossier"] == "candidature"],
        "offre": [x["cle"] for x in sel["lignes"]
                  if x["retenue"] and x["dossier"] == "offre"],
        "__non": [x["cle"] for x in sel["lignes"] if not x["retenue"]],
    }
    for g in GROUPES:
        if not attendu[g]:
            continue                       # un groupe vide ne rend pas de liste
        assert g in par_groupe, "le groupe « %s » n'a pas de liste" % g
        # La première option est l'invite « choisir… » : elle porte une valeur
        # vide, et c'est ce qui garde le bouton éteint au départ.
        valeurs = [v for v in par_groupe[g] if v]
        cles = [v.split(":", 1)[1] for v in valeurs]
        assert cles == attendu[g], (g, cles[:5], attendu[g][:5])

    assert attendu["__non"], (
        "le dossier de démonstration ne laisse aucune pièce non repérée : "
        "les règles ci-dessous ne mesureraient rien")


def test_le_geste_de_chaque_option_SUIT_l_etat_de_sa_ligne():
    """« on: » pour une pièce à ajouter, « off: » pour une pièce à retirer.

    CE QUE CETTE RÈGLE ATTRAPE, ET CE QU'ELLE N'ATTRAPE PAS — dit ici parce
    que la batterie l'a montré. Elle fait tomber une INVERSION : le jour où
    « ajouter » écrirait « off: », l'écran retirerait les pièces qu'on croit
    prendre. Elle ne fait PAS tomber une lecture du groupe au lieu de la
    ligne (`g[2]` au lieu de `x.retenue`), et c'est normal : le filtre qui
    construit les groupes garantit qu'aucun ne mêle les deux états, donc les
    deux expressions donnent le même résultat. Prétendre mesurer cette
    distinction serait écrire une règle qui passe pour une raison sans
    rapport avec ce qu'elle annonce. On garde `x.retenue` parce qu'il dit la
    VRAIE raison du geste ; la règle, elle, mesure ce qui est mesurable.
    """
    sel = _selection()
    r = _jouer(sel, [])
    par_cle = {x["cle"]: x for x in sel["lignes"]}
    for o in r["options"]:
        for v in o["valeurs"]:
            if not v:
                continue
            geste, cle = v.split(":", 1)
            assert geste in ("on", "off"), v
            attendu = "off" if par_cle[cle]["retenue"] else "on"
            assert geste == attendu, (cle, geste, attendu)


# ═══════════════════════════════════════════════════════════════════════════
#  CHOISIR NE DÉCIDE PAS ; PRESSER DÉCIDE
# ═══════════════════════════════════════════════════════════════════════════

def test_PARCOURIR_la_liste_ne_change_RIEN_au_dossier():
    """C'est ce que l'ancienne décision protégeait, et on le garde.

    Dérouler quinze noms pour voir ce qu'ils sont ne doit pas engager le
    dossier : sans cette réserve, chaque parcours de la liste deviendrait une
    décision — et l'on ne pourrait plus lire la liste sans la modifier.
    """
    sel = _selection()
    cle = next(x["cle"] for x in sel["lignes"] if not x["retenue"])
    r = _jouer(sel, [{"groupe": "__non", "valeur": "on:" + cle,
                      "presser": False}])
    assert r["faits"][0]["choisi"] is True, r["faits"]
    assert r["journal"] == [], (
        "choisir dans la liste a déjà modifié le dossier : %r" % r["journal"])


def test_le_bouton_DIT_ce_qu_il_va_faire_et_sur_quelle_piece():
    """« Appliquer » n'engage que celui qui se souvient de ce qu'il vient de
    sélectionner. Le bouton porte donc le geste ET le nom.

    Et il est ÉTEINT tant qu'aucune pièce n'est choisie : un bouton vif qui ne
    fait rien se lit comme une panne, pas comme une étape manquante.
    """
    sel = _selection()
    ligne = next(x for x in sel["lignes"] if not x["retenue"])
    r = _jouer(sel, [{"groupe": "__non", "valeur": "on:" + ligne["cle"],
                      "presser": False}])
    f = r["faits"][0]
    assert f["avant"]["eteint"] is True, "le bouton est vif sans pièce choisie"
    assert "Choisissez" in f["avant"]["libelle"], f["avant"]
    assert f["apres"]["eteint"] is False, "le bouton reste éteint après le choix"
    assert "Ajouter" in f["apres"]["libelle"], f["apres"]
    assert ligne["nom"] in f["apres"]["libelle"], (
        "le bouton ne nomme pas la pièce : %r" % f["apres"]["libelle"])


def test_PRESSER_ajoute_la_piece_non_reperee_au_dossier():
    """LA RÈGLE QUI MESURE L'EFFET — et la seule que le branchement fait vivre.

    On regarde ce qui part au moteur : la clé de la pièce, du bon côté. Une
    règle qui vérifierait la présence d'un écouteur serait verte avec un
    écouteur qui n'envoie rien.
    """
    sel = _selection()
    ligne = next(x for x in sel["lignes"] if not x["retenue"])
    r = _jouer(sel, [{"groupe": "__non", "valeur": "on:" + ligne["cle"],
                      "presser": True}])
    assert r["journal"], "presser le bouton n'a rien envoyé au moteur"
    dernier = r["journal"][-1]
    assert dernier["ajouts"] == [ligne["cle"]], dernier
    assert dernier["ecartees"] == [], dernier


def test_PRESSER_retire_une_piece_retenue():
    """Le geste inverse, dans les deux groupes de dossier.

    Sans lui, la déroulante ne servirait qu'à ajouter : on pourrait prendre
    une pièce et jamais la rendre, ce qui oblige à redescendre dans la liste
    détaillée — le geste qu'on vient précisément d'éviter.
    """
    cles = [x["cle"] for x in _selection()["lignes"] if not x["retenue"]][:2]
    sel = _selection(ajouts=cles)
    retenue = next(x for x in sel["lignes"]
                   if x["retenue"] and x["cle"] in cles)
    r = _jouer(sel, [{"groupe": retenue["dossier"],
                      "valeur": "off:" + retenue["cle"], "presser": True}])
    assert r["journal"], "presser n'a rien envoyé"
    dernier = r["journal"][-1]
    assert dernier["ecartees"] == [retenue["cle"]], dernier
    # ET LA MARQUE INVERSE EST LEVÉE — une mutation a survécu à la première
    # version de cette règle, qui ne regardait que la moitié du couple :
    # poser « écartée » SANS retirer « ajoutée » laisse la pièce dans les deux
    # listes, et c'est au moteur qu'on demande alors de trancher ce que
    # l'écran n'a pas tranché.
    assert retenue["cle"] not in dernier["ajouts"], dernier
    assert "Retirer" in r["faits"][0]["apres"]["libelle"], r["faits"][0]


def test_ajouter_puis_retirer_la_MEME_piece_ne_laisse_pas_les_deux_marques():
    """Une pièce à la fois ajoutée et écartée est un état que le moteur ne
    sait pas trancher — et il n'aurait pas à le savoir : les deux gestes sont
    exclusifs, et chacun efface l'autre."""
    sel = _selection()
    ligne = next(x for x in sel["lignes"] if not x["retenue"])
    r = _jouer(sel, [{"groupe": "__non", "valeur": "on:" + ligne["cle"],
                      "presser": True},
                     {"groupe": "__non", "valeur": "on:" + ligne["cle"],
                      "presser": True}])
    for etat in r["journal"]:
        communes = set(etat["ajouts"]) & set(etat["ecartees"])
        assert not communes, ("une pièce est ajoutée ET écartée : %s"
                              % sorted(communes))


def test_la_liste_DETAILLEE_et_ses_boutons_restent():
    """Les deux chemins mènent au même moteur, et c'est voulu.

    La déroulante sert quand on sait déjà ce qu'on cherche parmi quinze ; la
    liste détaillée sert à LIRE le motif et la citation avant de trancher.
    Supprimer la seconde au profit de la première ferait choisir sans savoir
    pourquoi la pièce est là.
    """
    r = _jouer(_selection(), [])
    h = r["html"]
    assert "data-sel-on=" in h or "data-sel-off=" in h, (
        "la liste détaillée a perdu ses boutons")
    assert "ig-ao-sc" in h, "les motifs et citations ne sont plus rendus"


def test_le_bouton_ALLER_A_LA_PIECE_survit_a_la_bascule():
    """L'ancien usage de la déroulante — atteindre une pièce plus bas — était
    utile et n'avait pas à disparaître. Il devient un bouton à lui."""
    sel = _selection()
    ligne = next(x for x in sel["lignes"] if not x["retenue"])
    r = _jouer(sel, [{"groupe": "__non", "valeur": "on:" + ligne["cle"],
                      "presser": False}])
    assert 'data-sel-voir="__non"' in r["html"], r["html"][:400]
    assert r["journal"] == [], "atteindre une pièce a modifié le dossier"


def test_le_couple_choisir_agir_a_une_mise_en_page():
    """Une classe posée par le rendu et absente de la feuille ne change RIEN
    à l'écran — et c'est le défaut que ce dépôt traque : une marque qui ne
    produit aucun effet.

    DEUX CHOSES SE MESURENT ENSEMBLE. Que la ligne existe — sans elle, le
    sélecteur et les deux boutons s'empilent en trois lignes pleine largeur —
    et qu'un bouton ÉTEINT se voie éteint : pressé sans pièce choisie, il ne
    fait rien, ce qui se lit comme une panne et non comme une étape manquante.
    """
    css = io.open(os.path.join(ICI, "ingenierie-datacenter.html"),
                  encoding="utf-8").read()
    assert ".ig-ao-ch{" in css, (
        "la classe du couple choisir/agir n'a aucune règle : les trois "
        "commandes s'empilent")
    bloc = css[css.index(".ig-ao-ch{"):]
    bloc = bloc[:bloc.index("\n  .ig-ao-sl{")]
    assert "display:flex" in bloc, bloc[:200]
    eteint = [l for l in bloc.splitlines() if ":disabled" in l]
    assert eteint, "un bouton éteint ne se distingue pas d'un bouton vif"
    assert any("opacity" in l or "cursor" in l for l in eteint), eteint

    # ET LA CLASSE EST RÉELLEMENT POSÉE PAR LE RENDU — une règle CSS sans
    # élément qui la porte ne vaut pas mieux que l'inverse.
    assert 'class="ig-ao-ch"' in _jouer(_selection(), [])["html"]


@pytest.mark.parametrize("groupe", GROUPES)
def test_un_groupe_VIDE_ne_rend_aucune_liste(groupe):
    """Une déroulante « 0 pièce(s) — choisir… » est un piège : on l'ouvre, on
    n'y trouve rien, et l'on croit à un défaut d'affichage. Le groupe dit sa
    phrase et se tait."""
    sel = _selection()
    vide = dict(sel, lignes=[x for x in sel["lignes"]
                             if (x["dossier"] != groupe if groupe != "__non"
                                 else x["retenue"])])
    r = _jouer(vide, [])
    rendus = {o["groupe"] for o in r["options"]}
    assert groupe not in rendus, (
        "le groupe « %s » rend une liste alors qu'il n'a aucune pièce" % groupe)
