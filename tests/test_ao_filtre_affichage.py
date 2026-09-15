# -*- coding: utf-8 -*-
"""CHOISIR CE QU'ON REGARDE — SANS CHANGER CE QU'ON DÉPOSE.

CE QUI ÉTAIT EN CAUSE. Une consultation ordinaire retient une quinzaine de
pièces à produire et dépose une douzaine de fichiers. La colonne de droite
déroulait les quinze lignes avec leur motif et leur citation ; la colonne de
gauche déroulait les douze cartes avec ce que chaque pièce engage, son piège
et tous ses relevés. Chercher ce que dit le CCAP demandait de passer devant
tout le reste.

DEUX DÉROULANTES VIVENT DÉSORMAIS CÔTE À CÔTE, ET ELLES NE FONT PAS LA MÊME
CHOSE :

  · `data-sel-liste` CHOISIT une pièce, et un bouton nommé l'ajoute ou la
    retire. Elle ENGAGE le dossier.
  · `data-vue-liste` ne fait que MONTRER. Elle ne touche ni la sélection, ni
    les comptes, ni ce qui partira dans l'archive.

LES CONFONDRE SERAIT LE PIRE DÉFAUT POSSIBLE ICI : « je n'affiche que les
brouillons » ne doit jamais vouloir dire « je ne dépose que les brouillons ».
C'est la propriété centrale que ces règles tiennent, et elles la tiennent en
EXÉCUTANT le filtre, pas en lisant la source.

CE QU'ELLES TIENNENT AUSSI :

  · UN FILTRE DIT CE QU'IL CACHE. Une liste de quinze pièces filtrée à quatre
    se lit comme une liste de quatre pièces, et c'est au dépôt qu'on s'en
    aperçoit.

  · LES ALERTES NE SONT JAMAIS MASQUÉES. Elles disent ce qui rend l'offre
    irrecevable. Un filtre d'affichage qui escamote un risque n'est plus un
    filtre, c'est une omission.

  · LA PAGE NE PORTE PLUS SA PROPRE TABLE DES CATÉGORIES. Les quatre phrases
    y étaient recopiées mot pour mot : deux tables du même texte, qui
    divergent le jour où l'on en corrige une.
"""
import io
import json
import os
import re
import subprocess
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc as A                                                # noqa: E402

import pytest                                                    # noqa: E402

NODE = "/opt/node22/bin/node"


def _src(nom="ingenierie-dc.js"):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


def _js_source(*noms):
    src = _src()
    out = []
    for nom in noms:
        i = src.index("\n  function %s(" % nom) + 1
        p, k = 1, src.index("{", i) + 1
        while p:
            p += 1 if src[k] == "{" else (-1 if src[k] == "}" else 0)
            k += 1
        out.append(src[i:k])
    return "\n".join(out)


def _node(prog, env=None):
    out = subprocess.run([NODE], input=prog, capture_output=True, text=True,
                         timeout=60, env=dict(os.environ, **(env or {})))
    assert out.returncode == 0, out.stderr[-2500:]
    return json.loads(out.stdout)


# ═══════════════════════════════════════════════════════════════════════════
#  UN DOM RÉDUIT — mais qui porte vraiment `hidden`, les classes et `closest`
# ═══════════════════════════════════════════════════════════════════════════
#
# POURQUOI PAS UN NAVIGATEUR ICI. La maison tient les scripts de navigateur
# hors de `tests/` : ils vivent dans `outils/recette_filtre_affichage.py`, qui
# mesure la même chose sur un vrai Chromium. Le double n'implémente que ce que
# les deux fonctions de filtrage touchent — `querySelector`,
# `querySelectorAll`, `closest`, `dataset`, `hidden`, `classList.contains`,
# `textContent` — et RIEN de plus, pour qu'une règle verte veuille dire
# quelque chose.
DOM = r"""
function El(tag, cls, ds) {
  this.tag = tag;
  this.hidden = false;
  this.textContent = "";
  this.dataset = ds || {};
  this.enfants = [];
  this.parent = null;
  var c = (cls || "").split(" ").filter(Boolean);
  this.classes = c;
  this.classList = { contains: function (x) { return c.indexOf(x) >= 0; } };
}
El.prototype.ajouter = function (e) {
  e.parent = this; this.enfants.push(e); return e;
};
El.prototype.tous = function () {
  var out = [];
  this.enfants.forEach(function (e) {
    out.push(e); out = out.concat(e.tous());
  });
  return out;
};
function cle(s) {
  return s.replace(/-([a-z])/g, function (_, c) { return c.toUpperCase(); });
}
function correspond(n, sel) {
  var m = /^\[data-([a-z-]+)="([^"]*)"\]$/.exec(sel);
  if (m) return n.dataset[cle(m[1])] === m[2];
  m = /^\[data-([a-z-]+)\]$/.exec(sel);
  if (m) return n.dataset[cle(m[1])] !== undefined;
  m = /^\.([A-Za-z0-9_-]+)$/.exec(sel);
  if (m) return n.classes.indexOf(m[1]) >= 0;
  throw new Error("sélecteur non géré par le double : " + sel);
}
El.prototype.querySelectorAll = function (sel) {
  return this.tous().filter(function (n) { return correspond(n, sel); });
};
El.prototype.querySelector = function (sel) {
  return this.querySelectorAll(sel)[0] || null;
};
El.prototype.closest = function (sel) {
  var n = this;
  while (n) { if (correspond(n, sel)) return n; n = n.parent; }
  return null;
};
"""


def _selection(texte=None):
    """La sélection RÉELLE du moteur — jamais une maquette."""
    an = A.analyser([{"nom": "RC.pdf", "extension": ".pdf",
                      "cote": "consultation",
                      "texte": texte or (
                          "Reglement de la consultation. Pieces a produire : "
                          "lettre de candidature DC1, declaration du candidat "
                          "DC2, attestation d'assurance responsabilite civile "
                          "professionnelle, liste des references de moins de "
                          "cinq ans, curriculum vitae des intervenants, "
                          "extrait Kbis, memoire technique, acte "
                          "d'engagement.")}])
    return A.selection(an)


# ═══════════════════════════════════════════════════════════════════════════
#  1. LE MOTEUR : UNE SEULE DÉRIVATION, QUATRE VUES
# ═══════════════════════════════════════════════════════════════════════════

def test_chaque_ligne_porte_une_categorie_DECLAREE():
    """UNE CATÉGORIE HORS TABLE TRAVERSERAIT L'ÉCRAN EN CLÉ DE PROGRAMME, et
    la déroulante ne l'offrirait jamais — la pièce serait invisible sous tout
    filtre sans que rien ne le dise."""
    s = _selection()
    hors = sorted({x["categorie"] for x in s["lignes"]}
                  - set(A.CATEGORIES_PIECE))
    assert not hors, "catégorie(s) hors de CATEGORIES_PIECE : %r" % hors
    assert all(x.get("categorie") for x in s["lignes"])


def test_les_quatre_listes_sont_des_VUES_de_la_categorie():
    """ELLES ÉTAIENT QUATRE COMPRÉHENSIONS SÉPARÉES, chacune relisant
    `voie()`. La page ne pouvait donc pas filtrer sans recalculer, et deux
    calculs de la même chose finissent toujours par diverger.

    CETTE RÈGLE TOMBE si l'une des quatre cesse de suivre la catégorie."""
    s = _selection()
    par_cat = {}
    for x in s["lignes"]:
        if x["retenue"]:
            par_cat.setdefault(x["categorie"], []).append(x["cle"])
    assert s["remplissables"] == par_cat.get("remplissable", [])
    assert s["au_report"] == par_cat.get("au_report", [])
    assert s["redigeables"] == par_cat.get("redigeable", [])
    assert s["a_demander"] == par_cat.get("a_demander", [])


def test_la_categorie_suit_voie_et_ne_la_recopie_pas():
    """SI ELLE ÉTAIT UNE TABLE ÉCRITE À LA MAIN, elle se désaccorderait le
    jour où une pièce change de nature — et le compte affiché mentirait sans
    qu'aucune règle tombe. `voie()` est la même fonction que `remplir()`
    consulte et que `ao_redaction` lit pour décider qui part à l'atelier."""
    attendu = {"remplir": "au_report", "rediger": "redigeable",
               "completer": "redigeable", "obtenir": "a_demander"}
    vus = set()
    for x in _selection()["lignes"]:
        if x["remplissable"]:
            assert x["categorie"] == "remplissable", x["cle"]
            continue
        v = A.voie(x["cle"], x["nature"])
        vus.add(v)
        assert x["categorie"] == attendu[v], (x["cle"], v, x["categorie"])
    assert len(vus) >= 3, "l'échantillon ne couvre pas assez de voies : %r" % vus


def test_les_quatre_categories_sortent_avec_leurs_libelles_et_leurs_pieces():
    """LA PAGE LES LIT, elle ne les recopie plus. L'ordre est celui de
    l'effort : ce que la machine fait seule d'abord."""
    s = _selection()
    assert [c["cle"] for c in s["categories"]] == list(A.CATEGORIES_PIECE)
    for c in s["categories"]:
        assert c["court"] and c["long"]
        assert len(c["court"]) < len(c["long"]), \
            "le libellé court de « %s » n'est pas plus court" % c["cle"]
    par = {c["cle"]: c["pieces"] for c in s["categories"]}
    assert par["remplissable"] == s["remplissables"]
    assert par["redigeable"] == s["redigeables"]


def test_la_page_ne_porte_PLUS_sa_propre_table_des_categories():
    """LES QUATRE PHRASES Y ÉTAIENT RECOPIÉES MOT POUR MOT. Deux tables du
    même texte divergent le jour où l'on en corrige une, et personne ne
    revérifie un libellé."""
    js = _src()
    for c in A.CATEGORIES_PIECE.values():
        assert c["long"] not in js, \
            "la page recopie encore « %s »" % c["long"][:40]
    assert "sel.categories" in js, \
        "la page ne lit pas le tableau des catégories du module"


# ═══════════════════════════════════════════════════════════════════════════
#  2. LE FILTRE DES PIÈCES À PRODUIRE — EXÉCUTÉ
# ═══════════════════════════════════════════════════════════════════════════

def _banc_liste(groupe, cat, lignes):
    """Un groupe rendu à la main, puis filtré par la VRAIE fonction."""
    prog = DOM + _js_source("aoVueAppliquer") + """
    var AO_VUE = {};
    var lignes = JSON.parse(process.env.LIGNES);
    var z = new El("div");
    var bloc = z.ajouter(new El("div", "ig-ao-sg"));
    bloc.ajouter(new El("select", "", {vueListe: process.env.GROUPE}));
    var dit = bloc.ajouter(new El("span", "ig-ao-vm",
                                  {vueMasque: process.env.GROUPE}));
    var ul = bloc.ajouter(new El("ul", "ig-ao-sl"));
    lignes.forEach(function (x) {
      ul.ajouter(new El("li", "", {vuePiece: x.cle, vueCat: x.categorie}));
      ul.ajouter(new El("li", "ig-ao-sc", {vuePiece: x.cle,
                                           vueCat: x.categorie}));
    });
    aoVueAppliquer(z, process.env.GROUPE, process.env.CAT);
    var pieces = z.querySelectorAll("[data-vue-piece]");
    process.stdout.write(JSON.stringify({
      dit: dit.textContent,
      memoire: AO_VUE[process.env.GROUPE],
      visibles: pieces.filter(function (n) {
        return !n.hidden && !n.classList.contains("ig-ao-sc"); })
        .map(function (n) { return n.dataset.vuePiece; }),
      citations_visibles: pieces.filter(function (n) {
        return !n.hidden && n.classList.contains("ig-ao-sc"); })
        .map(function (n) { return n.dataset.vuePiece; })
    }));
    """
    return _node(prog, {"LIGNES": json.dumps(lignes), "GROUPE": groupe,
                        "CAT": cat})


LIGNES = [{"cle": "dc1", "categorie": "remplissable"},
          {"cle": "dc2", "categorie": "remplissable"},
          {"cle": "memoire_technique", "categorie": "redigeable"},
          {"cle": "kbis", "categorie": "a_demander"}]


def test_le_filtre_ne_montre_QUE_la_categorie_choisie():
    r = _banc_liste("candidature", "remplissable", LIGNES)
    assert r["visibles"] == ["dc1", "dc2"]


def test_la_citation_suit_SA_piece_et_ne_reste_pas_orpheline():
    """CE SONT DEUX <li> FRÈRES. N'en masquer qu'un laisserait une citation
    sous une pièce disparue — et cette citation est ce qui justifie la
    pièce : lue seule, elle se rattache à la ligne d'à côté."""
    r = _banc_liste("candidature", "redigeable", LIGNES)
    assert r["visibles"] == ["memoire_technique"]
    assert r["citations_visibles"] == ["memoire_technique"]


def test_le_filtre_DIT_combien_il_masque():
    """UNE LISTE FILTRÉE SANS CE COMPTE SE LIT COMME UNE LISTE COURTE."""
    r = _banc_liste("candidature", "a_demander", LIGNES)
    assert "1 affichée(s), 3 masquée(s)" in r["dit"]
    assert "portent sur l'ensemble" in r["dit"], \
        "le filtre ne dit pas que les comptes du haut restent entiers"


def test_sans_filtre_rien_n_est_masque_et_rien_n_est_dit():
    """LE TÉMOIN NÉGATIF. Sans lui, une règle qui constate un message
    passerait aussi sur un écran qui en affiche toujours un."""
    r = _banc_liste("candidature", "", LIGNES)
    assert len(r["visibles"]) == len(LIGNES)
    assert r["dit"] == ""


def test_le_choix_est_MEMORISE_pour_survivre_au_redessin():
    """LE BLOC EST RÉAFFICHÉ À CHAQUE AJOUT OU RETRAIT DE PIÈCE. Sans mémoire,
    le filtre sauterait à « tout afficher » au moment précis où l'on travaille
    sur une catégorie."""
    r = _banc_liste("offre", "redigeable", LIGNES)
    assert r["memoire"] == "redigeable"


def test_les_options_ne_proposent_que_les_categories_PRESENTES():
    """UNE OPTION QUI MÈNE À UNE LISTE VIDE SE LIT COMME UN FILTRE CASSÉ."""
    s = _selection()
    lignes = [x for x in s["lignes"] if x["retenue"]
              and x["dossier"] == "candidature"]
    prog = DOM + _js_source("esc", "aoVueOptions") + """
    var AO_SELECTION = JSON.parse(process.env.SEL);
    var lignes = JSON.parse(process.env.LIGNES);
    var h = aoVueOptions(lignes, "");
    var re = /<option value="([^"]*)"[^>]*>([^<]*)<\\/option>/g, m, out = [];
    while ((m = re.exec(h))) out.push([m[1], m[2]]);
    process.stdout.write(JSON.stringify(out));
    """
    opts = _node(prog, {"SEL": json.dumps(s), "LIGNES": json.dumps(lignes)})
    presentes = {x["categorie"] for x in lignes}
    assert {o[0] for o in opts} == presentes, (opts, presentes)
    for cle, libelle in opts:
        n = sum(1 for x in lignes if x["categorie"] == cle)
        assert libelle.endswith("(%d)" % n), \
            "l'option « %s » annonce un compte qui n'est pas celui de ce " \
            "groupe" % libelle


def test_le_compte_des_options_est_celui_DU_GROUPE_pas_du_dossier_entier():
    """« 8 brouillons » SUR UN GROUPE QUI N'EN CONTIENT QU'UN est un chiffre
    juste au mauvais endroit — et c'est la sorte d'erreur qu'on ne remarque
    pas, parce que le nombre existe ailleurs dans la page."""
    prog = DOM + _js_source("esc", "aoVueOptions") + """
    var AO_SELECTION = {categories: [
      {cle: "remplissable", court: "Cerfa", long: "x"},
      {cle: "redigeable", court: "Brouillon", long: "y"}]};
    var h = aoVueOptions([{categorie: "redigeable"}], "");
    process.stdout.write(JSON.stringify({html: h}));
    """
    h = _node(prog)["html"]
    assert "Brouillon (1)" in h
    assert "Cerfa" not in h, \
        "une catégorie absente du groupe est quand même proposée"


# ═══════════════════════════════════════════════════════════════════════════
#  3. LE FILTRE DU RELEVÉ — ET LES ALERTES QUI NE BOUGENT PAS
# ═══════════════════════════════════════════════════════════════════════════

def _banc_doc(choix, sections):
    prog = DOM + _js_source("aoVueDocAppliquer") + """
    var AO_VUE_DOC = "";
    var z = new El("div");
    var al = z.ajouter(new El("div", "ig-ao-al"));
    al.ajouter(new El("p", "ig-ao-a ig-ao-a-bloquante"));
    var dit = z.ajouter(new El("span", "ig-ao-vm", {vueDocMasque: ""}));
    JSON.parse(process.env.SECTIONS).forEach(function (s) {
      z.ajouter(new El("div", "", {vueDocItem: s}));
    });
    aoVueDocAppliquer(z, process.env.CHOIX);
    process.stdout.write(JSON.stringify({
      dit: dit.textContent, memoire: AO_VUE_DOC,
      alerte_masquee: al.hidden,
      visibles: z.querySelectorAll("[data-vue-doc-item]")
        .filter(function (n) { return !n.hidden; })
        .map(function (n) { return n.dataset.vueDocItem; })
    }));
    """
    return _node(prog, {"SECTIONS": json.dumps(sections), "CHOIX": choix})


SECTIONS = ["manquantes", "doc:RC.pdf", "doc:CCAP.pdf", "inconnues", "nous"]


def test_le_releve_montre_UNE_section_a_la_fois():
    r = _banc_doc("doc:CCAP.pdf", SECTIONS)
    assert r["visibles"] == ["doc:CCAP.pdf"]
    assert "1 section(s) affichée(s), 4 masquée(s)" in r["dit"]


def test_les_ALERTES_ne_sont_JAMAIS_masquees():
    """LA SEULE RÈGLE NON NÉGOCIABLE DE CE FILTRE. Elles disent ce qui rend
    l'offre irrecevable — une pièce essentielle absente, une date limite non
    trouvée. Les cacher parce qu'on regarde le CCTP serait le pire résultat
    possible : un filtre d'affichage qui escamote un risque n'est plus un
    filtre, c'est une omission."""
    for choix in SECTIONS:
        r = _banc_doc(choix, SECTIONS)
        assert r["alerte_masquee"] is False, \
            "le filtre « %s » a masqué le bloc des alertes" % choix


def test_le_RENDU_ne_rend_pas_les_alertes_filtrables():
    """CE QUE LA RÈGLE PRÉCÉDENTE NE POUVAIT PAS VOIR, ET POURQUOI ELLE ÉTAIT
    FAIBLE. Elle construit son propre DOM : le bloc d'alertes qu'elle pose à
    la main ne porte évidemment pas `data-vue-doc-item`, si bien qu'une
    mutation ajoutant cet attribut DANS LE RENDU a survécu. La règle mesurait
    son décor, pas le produit.

    ICI ON LIT LE HTML RENDU, et l'on exige que le bloc des alertes ne porte
    aucune étiquette de filtre : c'est ce qui le rend inatteignable par
    `aoVueDocAppliquer`, quelle que soit la section choisie."""
    a = A.analyser([{"nom": "RC.pdf", "extension": ".pdf", "texte":
                     "Reglement de la consultation. Le pouvoir adjudicateur "
                     "passe ce marche."},
                    {"nom": "inconnu.xyz", "extension": ".xyz", "texte": ""}])
    assert a["alertes"], "le dossier d'essai ne porte aucune alerte à protéger"
    prog = DOM + _js_source("esc", "aoVueDoc", "aoTexteBouton", "aoRendre") + """
    var AO_VUE_DOC = "";
    var zone = {innerHTML: "", querySelectorAll: function () { return []; },
                querySelector: function () { return null; }};
    function $(x) { return x === "#ig-ao-out" ? zone : null; }
    function info() { return ""; }
    function aoTexteBrancherListe() {}
    function aoTexteFermer() {}
    function aoIgnores() {}
    function aoVueDocBrancher() {}
    aoRendre(JSON.parse(process.env.A));
    process.stdout.write(JSON.stringify({html: zone.innerHTML}));
    """
    h = _node(prog, {"A": json.dumps(a)})["html"]
    # ON DÉCOUPE LA BALISE OUVRANTE, PAS UNE FENÊTRE DE N CARACTÈRES.
    #
    # PREMIÈRE VERSION DE CETTE RÈGLE : `h[i - 40:j]`. Le bloc des alertes est
    # le PREMIER du relevé, donc `i` valait moins de 40 : `i - 40` était
    # négatif, Python comptait depuis la fin, et la tranche ressortait VIDE.
    # La règle passait sur une chaîne vide — verte pour une raison sans aucun
    # rapport avec ce qu'elle prétendait — et la mutation qui rend les alertes
    # filtrables a survécu deux fois.
    i = h.index('class="ig-ao-al"')
    bloc = h[h.rindex("<div", 0, i):h.index(">", i) + 1]
    assert "ig-ao-al" in bloc, "la découpe n'a pas saisi la balise ouvrante"
    assert "data-vue-doc-item" not in bloc, \
        "le bloc des alertes porte une étiquette de filtre : il peut donc " \
        "être masqué"
    # ET LE TÉMOIN POSITIF : les sections filtrables, elles, sont étiquetées.
    assert h.count("data-vue-doc-item") >= 2, \
        "plus aucune section n'est filtrable — la règle ne mesure plus rien"


def test_sans_choix_tout_le_releve_est_visible():
    r = _banc_doc("", SECTIONS)
    assert r["visibles"] == SECTIONS and r["dit"] == ""


def test_la_deroulante_du_releve_nomme_chaque_piece_par_sigle_ET_fichier():
    """« CCAP » SEUL NE SUFFIT PAS quand deux fichiers portent le même sigle,
    et le nom de fichier seul ne dit pas ce qu'on va lire."""
    a = {"manquantes": [{"sigle": "AE"}], "pieces": [
            {"sigle": "RC", "fichier": "Reglement.pdf"},
            {"sigle": "CCAP", "fichier": "CCAP-v2.pdf"}],
         "inconnues": [{"fichier": "x.dwg"}], "pieces_candidat": []}
    prog = DOM + _js_source("esc", "aoVueDoc") + """
    process.stdout.write(JSON.stringify(
      {html: aoVueDoc(JSON.parse(process.env.A))}));
    """
    h = _node(prog, {"A": json.dumps(a)})["html"]
    assert 'value="doc:Reglement.pdf">RC — Reglement.pdf' in h
    assert 'value="doc:CCAP-v2.pdf">CCAP — CCAP-v2.pdf' in h
    assert "Absent du dossier déposé (1)" in h
    assert "Fichiers non reconnus (1)" in h
    assert "VOTRE dossier" not in h, \
        "une section vide est quand même proposée"


def test_sous_trois_sections_le_filtre_ne_s_affiche_PAS():
    """UN ÉCRAN QUI OFFRE UN OUTIL INUTILE FAIT DOUTER DE CEUX QUI SERVENT."""
    a = {"manquantes": [], "pieces": [{"sigle": "RC", "fichier": "R.pdf"}],
         "inconnues": [], "pieces_candidat": []}
    prog = DOM + _js_source("esc", "aoVueDoc") + """
    process.stdout.write(JSON.stringify(
      {html: aoVueDoc(JSON.parse(process.env.A))}));
    """
    assert _node(prog, {"A": json.dumps(a)})["html"] == ""


def test_le_filtre_promet_que_les_alertes_restent():
    """LA PROMESSE EST ÉCRITE À CÔTÉ DE LA DÉROULANTE. Sans elle, l'opérateur
    qui filtre ne sait pas qu'il voit encore tout ce qui l'engage."""
    a = {"manquantes": [{"sigle": "AE"}],
         "pieces": [{"sigle": "RC", "fichier": "R.pdf"},
                    {"sigle": "CCAP", "fichier": "C.pdf"}],
         "inconnues": [], "pieces_candidat": []}
    prog = DOM + _js_source("esc", "aoVueDoc") + """
    process.stdout.write(JSON.stringify(
      {html: aoVueDoc(JSON.parse(process.env.A))}));
    """
    assert "alertes restent affichées" in _node(prog, {"A": json.dumps(a)})["html"]


# ═══════════════════════════════════════════════════════════════════════════
#  4. CE QUI MONTRE NE DÉCIDE RIEN — LA PROPRIÉTÉ CENTRALE
# ═══════════════════════════════════════════════════════════════════════════

def test_le_filtre_d_affichage_ne_TOUCHE_PAS_la_selection():
    """« JE N'AFFICHE QUE LES BROUILLONS » NE DOIT JAMAIS VOULOIR DIRE « JE NE
    DÉPOSE QUE LES BROUILLONS ». On exécute le filtre et l'on regarde les
    deux registres que le geste d'ajout/retrait alimente : ils doivent être
    intacts."""
    prog = DOM + _js_source("aoVueAppliquer") + """
    var AO_VUE = {}, AO_SEL_AJOUTS = {}, AO_SEL_ECARTEES = {};
    var recalculs = 0;
    function aoSelectionRecalculer() { recalculs += 1; }
    var z = new El("div");
    var bloc = z.ajouter(new El("div", "ig-ao-sg"));
    bloc.ajouter(new El("select", "", {vueListe: "candidature"}));
    bloc.ajouter(new El("span", "ig-ao-vm", {vueMasque: "candidature"}));
    ["dc1", "dc2", "kbis"].forEach(function (c) {
      bloc.ajouter(new El("li", "", {vuePiece: c, vueCat: "remplissable"}));
    });
    aoVueAppliquer(z, "candidature", "a_demander");
    process.stdout.write(JSON.stringify({
      ajouts: Object.keys(AO_SEL_AJOUTS),
      ecartees: Object.keys(AO_SEL_ECARTEES),
      recalculs: recalculs}));
    """
    r = _node(prog)
    assert r["ajouts"] == [] and r["ecartees"] == []
    assert r["recalculs"] == 0, \
        "le filtre d'affichage a relancé un calcul de sélection"


def test_les_deux_deroulantes_restent_DISTINCTES_dans_le_rendu():
    """UNE SEULE DÉROULANTE POUR LES DEUX GESTES SERAIT LA CONFUSION QU'ON
    ÉVITE. La règle lit le rendu réel, pas la source : c'est ce que
    l'utilisateur voit qui doit porter deux commandes séparées."""
    s = _selection()
    prog = DOM + _js_source("esc", "aoVueOptions", "aoSelectionRendre") + """
    var AO_SELECTION = null, AO_VUE = {};
    var zone = {innerHTML: "", querySelectorAll: function () { return []; }};
    function $(x) { return x === "#ig-ao-retenus" ? zone : null; }
    function aoSelectionBrancher() {}
    function aoVueBrancher() {}
    function info() { return ""; }
    aoSelectionRendre(JSON.parse(process.env.SEL));
    var h = zone.innerHTML;
    process.stdout.write(JSON.stringify({
      vue: (h.match(/data-vue-liste="/g) || []).length,
      sel: (h.match(/data-sel-liste="/g) || []).length,
      masque: (h.match(/data-vue-masque="/g) || []).length,
      agir: (h.match(/data-sel-agir="/g) || []).length,
      ordre: h.indexOf("data-vue-liste") < h.indexOf("data-sel-liste")}));
    """
    r = _node(prog, {"SEL": json.dumps(s)})
    assert r["vue"] == 3 and r["sel"] == 3, r
    assert r["masque"] == 3 and r["agir"] == 3, r
    assert r["ordre"] is True, \
        "la déroulante qui ENGAGE est proposée avant celle qui montre"


def test_le_rendu_etiquette_chaque_ligne_de_sa_categorie():
    """SANS CET ATTRIBUT, LE FILTRE NE PEUT RIEN MASQUER — et une règle qui
    exécute `aoVueAppliquer` sur un DOM fabriqué à la main ne le verrait pas :
    c'est le RENDU qui doit poser l'étiquette."""
    s = _selection()
    prog = DOM + _js_source("esc", "aoVueOptions", "aoSelectionRendre") + """
    var AO_SELECTION = null, AO_VUE = {};
    var zone = {innerHTML: "", querySelectorAll: function () { return []; }};
    function $(x) { return x === "#ig-ao-retenus" ? zone : null; }
    function aoSelectionBrancher() {}
    function aoVueBrancher() {}
    function info() { return ""; }
    aoSelectionRendre(JSON.parse(process.env.SEL));
    process.stdout.write(JSON.stringify({html: zone.innerHTML}));
    """
    h = _node(prog, {"SEL": json.dumps(s)})["html"]
    # ON LIT LES PAIRES, PAS LES ATTRIBUTS SÉPARÉMENT. Chercher
    # `data-vue-cat="redigeable"` quelque part dans le HTML est vrai dès
    # qu'UNE ligne le porte : une mutation qui vide l'étiquette de la pièce en
    # laissant celle de sa citation a survécu pour cette seule raison.
    paires = re.findall(r'data-vue-piece="([^"]*)" data-vue-cat="([^"]*)"', h)
    par_cle = {}
    for cle, cat in paires:
        par_cle.setdefault(cle, set()).add(cat)
    for x in s["lignes"]:
        assert x["cle"] in par_cle, "aucune ligne rendue pour %s" % x["cle"]
        assert par_cle[x["cle"]] == {x["categorie"]}, (
            "la pièce « %s » est étiquetée %r au lieu de %r — la ligne et sa "
            "citation doivent porter la MÊME catégorie, sinon le filtre en "
            "masque une et garde l'autre"
            % (x["cle"], sorted(par_cle[x["cle"]]), x["categorie"]))


def test_la_recette_navigateur_existe_et_mesure_les_DEUX_filtres():
    """LES SCRIPTS DE NAVIGATEUR VIVENT DANS `outils/`, JAMAIS DANS `tests/`.
    Le double ci-dessus n'est pas un navigateur : il ne sait rien de la mise
    en page, du clavier ni du défilement. La recette est ce qui l'éprouve pour
    de vrai, et une règle doit garantir qu'elle existe encore."""
    p = os.path.join(ICI, "outils", "recette_filtre_affichage.py")
    assert os.path.exists(p), "la recette navigateur a disparu"
    src = io.open(p, encoding="utf-8").read()
    assert "data-vue-liste" in src and "data-vue-doc" in src
    assert "chromium" in src.lower()
