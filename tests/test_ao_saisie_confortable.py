# -*- coding: utf-8 -*-
"""Remplir à la main devient possible — et ce qui se lit une fois se recopie.

QUATRE DÉFAUTS, MESURÉS SUR LA PAGE RÉELLE.

1. LE CLAVIER. Chaque frappe appelait `aoRemplir`, qui interroge le serveur
   450 ms après la dernière touche puis REPEINT toute la zone. Le champ dans
   lequel on écrivait devenait un nœud détruit : focus perdu, curseur à zéro.
   Pire — la requête était partie avec la valeur d'il y a 450 ms, donc la
   réponse rapportait un texte PLUS VIEUX que ce qui était à l'écran et
   effaçait les dernières lettres. Mesuré dans Chromium : sur « VILLE DE
   PARIS » tapé puis corrigé au milieu, neuf caractères perdus et le focus
   parti (voir `outils/recette_saisie_clavier.py`).

2. LA RECOPIE. L'identification de l'acheteur est demandée par le DC1
   (cadre A), le DC2, le DC4 (cadre D) et l'ATTRI1 (cadre A) ; l'objet, par le
   DC1 (cadre B), le DC2 et l'ATTRI1. C'est LE MÊME FAIT. Le relevé par motifs
   le savait — il est indexé par clé de relevé. La lecture assistée ne le
   savait pas : ses valeurs sont rangées sous « pièce.rubrique », si bien que
   le modèle pouvait lire l'acheteur pour le DC1 et laisser trois cadres vides
   à côté d'un cadre rempli, avec la même question et la réponse disponible.

3. L'APERÇU. Les vingt-trois cartes déroulaient TOUTES leurs rubriques dans
   une grille de colonnes de 320 px. Une pièce de quinze rubriques donnait une
   colonne de deux mètres de haut et des champs de deux centimètres de large.

4. LE TÉLÉCHARGEMENT D'UNE PIÈCE n'apparaissait qu'APRÈS une production en
   lot : pour emporter une seule pièce, il fallait lancer les vingt-trois.
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
    """Les fonctions demandées, extraites de la source SERVIE, par comptage
    d'accolades — recopier leur corps ici éprouverait un script imaginaire."""
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


def _node(prog, **env):
    out = subprocess.run(["/opt/node22/bin/node"], input=prog,
                         capture_output=True, text=True, timeout=60,
                         env=dict(os.environ, **env))
    assert out.returncode == 0, out.stderr[-2500:]
    return out.stdout


# ═══════════════════════════════════════════════════════════════════════════
#  1. LE CLAVIER — un DOM réduit, mais un vrai comportement de focus
# ═══════════════════════════════════════════════════════════════════════════
#
# POURQUOI UN DOUBLE ET NON UN NAVIGATEUR ICI. La maison tient les scripts de
# navigateur hors de `tests/` : la suite doit tourner vite et sans processus
# externe lourd. Le double implémente exactement ce que les deux gardes
# touchent — `activeElement`, `contains`, `querySelector`, `focus`,
# `setSelectionRange` — et RIEN d'autre, pour qu'une règle verte ici veuille
# dire quelque chose. La vérification en vrai navigateur existe, à part :
# `outils/recette_saisie_clavier.py`.
DOM = """
var DOC = { activeElement: null };
global.document = DOC;
function Champ(attr, cle, valeur) {
  this._a = {}; this._a[attr] = cle;
  this.value = valeur; this.selectionStart = 0; this.selectionEnd = 0;
  this.focus_recu = 0;
}
Champ.prototype.getAttribute = function (n) {
  return this._a[n] === undefined ? null : this._a[n];
};
Champ.prototype.hasAttribute = function (n) { return this._a[n] !== undefined; };
Champ.prototype.focus = function () { this.focus_recu++; DOC.activeElement = this; };
Champ.prototype.setSelectionRange = function (a, b) {
  this.selectionStart = a; this.selectionEnd = b;
};
function Zone(champs) { this.champs = champs || []; }
Zone.prototype.contains = function (n) { return this.champs.indexOf(n) >= 0; };
Zone.prototype.querySelector = function (sel) {
  var m = /\\[(data-[a-z]+)="(.*)"\\]$/.exec(sel);
  if (!m) return null;
  for (var i = 0; i < this.champs.length; i++) {
    if (this.champs[i].getAttribute(m[1]) === m[2].replace(/\\\\(.)/g, "$1")) {
      return this.champs[i];
    }
  }
  return null;
};
"""


def _clavier(attr="data-saisie", cle="dc1.acheteur", tape="VILLE DE PARIS",
             curseur=8, echo="VILLE"):
    """Le scénario réel : on tape, on remonte le curseur, le serveur répond."""
    prog = DOM + _js_source("aoFocusRetenir", "aoFocusRendre") + """
    var avant = new Champ(%(attr)s, %(cle)s, %(tape)s);
    avant.selectionStart = avant.selectionEnd = %(cur)d;
    var zone = new Zone([avant]);
    DOC.activeElement = avant;

    var garde = aoFocusRetenir(zone);

    /* LE REPEINT : le nœud d'avant est jeté, un nœud NEUF le remplace, porteur
       de la valeur que le serveur avait au départ de la requête. */
    var apres = new Champ(%(attr)s, %(cle)s, %(echo)s);
    zone.champs = [apres];
    DOC.activeElement = null;

    aoFocusRendre(zone, garde);
    process.stdout.write(JSON.stringify({
      garde: garde !== null,
      focus: DOC.activeElement === apres,
      focus_recu: apres.focus_recu,
      valeur: apres.value,
      curseur: apres.selectionStart
    }));
    """ % {"attr": json.dumps(attr), "cle": json.dumps(cle),
           "tape": json.dumps(tape), "cur": curseur, "echo": json.dumps(echo)}
    return json.loads(_node(prog))


def test_le_repeint_REND_le_focus_et_le_curseur_au_champ_en_cours():
    """Sans cela, on ne peut pas taper une phrase : on est éjecté du champ.

    LE CURSEUR COMPTE AUTANT QUE LE FOCUS. Le rendre en fin de ligne obligerait
    à repointer à la souris après chaque pause de frappe — ce qui est le geste
    qu'on essaie de supprimer.
    """
    r = _clavier()
    assert r["garde"] is True, "rien n'a été retenu"
    assert r["focus"] is True, "le champ n'a pas récupéré le focus"
    assert r["focus_recu"] == 1
    assert r["curseur"] == 8, r


def test_la_valeur_VIVANTE_l_emporte_sur_l_echo_du_serveur():
    """La requête part avec la valeur d'il y a 450 ms.

    Si l'on a continué de taper pendant l'aller-retour, la réponse rapporte un
    texte PLUS VIEUX que l'écran. Le repeint l'écrirait dans le champ et
    effacerait les dernières lettres — c'est ce qui fait « sauter » les
    caractères. Mesuré ici sur l'écart exact : « VILLE DE PARIS » tapé,
    « VILLE » renvoyé.
    """
    r = _clavier(tape="VILLE DE PARIS", echo="VILLE")
    assert r["valeur"] == "VILLE DE PARIS", (
        "l'écho du serveur a écrasé ce qui venait d'être tapé : %r" % r["valeur"])


def test_la_garde_couvre_AUSSI_la_fiche_du_cabinet():
    """Deux zones repeignent des champs, et la fiche est la plus tapée des deux.

    Ne couvrir que les cartes aurait laissé le défaut entier là où l'on saisit
    la raison sociale, le SIRET et l'adresse — c'est-à-dire là où l'on tape
    le plus.
    """
    r = _clavier(attr="data-fiche", cle="raison_sociale",
                 tape="CONSEILPREV SARL", curseur=4, echo="CONS")
    assert r["focus"] is True and r["valeur"] == "CONSEILPREV SARL"
    assert r["curseur"] == 4


def test_sans_champ_actif_la_garde_ne_fait_RIEN():
    """LE TÉMOIN NÉGATIF. Une garde qui poserait le focus quand personne ne
    tapait volerait le curseur à chaque repeint — y compris pendant qu'on lit
    une autre partie de la page.
    """
    prog = DOM + _js_source("aoFocusRetenir", "aoFocusRendre") + """
    var c = new Champ("data-saisie", "dc1.acheteur", "x");
    var zone = new Zone([c]);
    DOC.activeElement = null;                    /* personne ne tape */
    var g1 = aoFocusRetenir(zone);
    /* Et un élément actif HORS de la zone ne doit pas davantage la concerner. */
    DOC.activeElement = new Champ("data-saisie", "ailleurs", "y");
    var g2 = aoFocusRetenir(zone);
    aoFocusRendre(zone, g1);
    process.stdout.write(JSON.stringify(
      {g1: g1, g2: g2, focus_recu: c.focus_recu}));
    """
    r = json.loads(_node(prog))
    assert r["g1"] is None and r["g2"] is None
    assert r["focus_recu"] == 0, "la garde a volé le focus sans raison"


def test_les_DEUX_rendus_de_la_page_encadrent_leur_repeint():
    """La garde doit être POSÉE, pas seulement écrite.

    On mesure sur la source des deux fonctions de rendu — c'est le seul
    endroit où la pose se voit — mais on mesure l'ENCADREMENT : le témoin est
    pris AVANT `innerHTML` et rendu APRÈS. Une garde posée après le repeint ne
    retiendrait rien, et une règle qui se contenterait de trouver les deux
    noms quelque part serait verte pour cet ordre-là.
    """
    for nom in ("aoRempliRendre", "aoFicheRendre"):
        bloc = _js_source(nom)
        i_ret = bloc.find("aoFocusRetenir(")
        i_html = bloc.find("innerHTML = ")
        i_ren = bloc.find("aoFocusRendre(")
        assert i_ret >= 0, "%s ne retient aucun focus" % nom
        assert i_ren >= 0, "%s ne rend aucun focus" % nom
        assert i_ret < i_html < i_ren, (
            "%s n'encadre pas son repeint (retenir=%d, innerHTML=%d, rendre=%d)"
            % (nom, i_ret, i_html, i_ren))


# ═══════════════════════════════════════════════════════════════════════════
#  2. LA RECOPIE — un fait de la consultation vaut pour toutes ses pièces
# ═══════════════════════════════════════════════════════════════════════════

RC_MUET = "Le pouvoir adjudicateur passe ce marche."
_DOCS = [{"nom": "RC.pdf", "extension": "pdf", "cote": "consultation",
          "texte": RC_MUET}]


def _extrait(valeur):
    return {"valeur": valeur, "citation": RC_MUET, "fichier": "RC.pdf",
            "sigle": "RC", "part": 3, "non_identifie": False}


def _cadres(extraits, cles=("acheteur", "objet_consultation", "objet_marche")):
    an = A.analyser(_DOCS)
    r = A.remplir(fiche={}, analyse=an, extraits=extraits)
    return [(p["cle"], l["cle"], l["statut"], l.get("valeur") or "",
             l.get("recopie_de") or "")
            for p in r["pieces"] for l in p["rubriques"] if l["cle"] in cles]


LU_DC1 = {"dc1.acheteur": _extrait("VILLE DE PARIS"),
          "dc1.objet_consultation": _extrait("Construction d un centre")}


def test_un_fait_lu_UNE_FOIS_remplit_TOUS_les_cadres_qui_le_demandent():
    """LA RÈGLE QUI MESURE L'EFFET, et la seule que la recopie fait vivre.

    Deux valeurs lues pour le seul DC1 ; on compte combien de cadres sont
    remplis dans les VINGT-TROIS pièces. Sans recopie : deux — ceux du DC1.
    Une règle qui vérifierait la présence d'un index serait verte avec un
    index que personne ne consulte.
    """
    sans = _cadres(None)
    propre = [x for x in _cadres(LU_DC1) if x[2] == "rempli"]

    assert not [x for x in sans if x[2] == "rempli"], sans
    assert len(propre) >= 8, (
        "la lecture du DC1 ne remplit que %d cadre(s) : %r"
        % (len(propre), propre))
    # ET ELLE TRAVERSE LES QUATRE FORMULAIRES DE L'ÉTAT, pas seulement le DC2.
    assert {x[0] for x in propre} >= {"dc1", "dc2", "dc4", "acte_engagement"}


def test_la_recopie_DIT_de_quelle_piece_elle_vient():
    """Une valeur lue une fois et reportée trois fois n'est pas trois lectures
    concordantes. Le relecteur doit pouvoir le voir avant de signer."""
    lus = _cadres(LU_DC1)
    dc1 = [x for x in lus if x[0] == "dc1" and x[2] == "rempli"]
    autres = [x for x in lus if x[0] != "dc1" and x[2] == "rempli"]

    assert dc1 and all(not x[4] for x in dc1), (
        "la pièce qui a LU annonce une recopie : %r" % dc1)
    assert autres and all(x[4] for x in autres), (
        "une recopie ne dit pas d'où elle vient : %r"
        % [x for x in autres if not x[4]])
    # LE NOM DE LA PIÈCE, PAS SA CLÉ : « dc1 » ne dit rien à qui relit.
    assert all("DC1" in x[4] for x in autres), autres[:3]


def test_la_lecture_PROPRE_d_une_piece_l_emporte_sur_la_recopie():
    """Elle a été faite sur cette pièce-ci, avec ses libellés.

    Si la recopie passait devant, une lecture faite exprès pour l'ATTRI1
    serait écrasée par celle du DC1 — et l'on ne saurait jamais laquelle des
    deux le document porte.
    """
    lu = dict(LU_DC1)
    lu["acte_engagement.acheteur"] = _extrait("SA PROPRE LECTURE")
    ae = [x for x in _cadres(lu)
          if x[0] == "acte_engagement" and x[1] == "acheteur"]
    assert ae and ae[0][3] == "SA PROPRE LECTURE", ae
    assert not ae[0][4], "sa propre lecture est annoncée comme une recopie"


def test_seules_les_rubriques_de_CONSULTATION_se_recopient():
    """Une SAISIE se décide par pièce et ne se recopie pas.

    « Le candidat se présente-t-il seul ou en groupement pour CETTE pièce »
    n'est pas un fait de la consultation : le recopier reviendrait à décider à
    la place de l'opérateur, sur toutes les pièces, depuis une seule réponse.
    """
    # LA GARDE SE MESURE SUR LE CAS QU'ELLE EXISTE POUR, ET IL FAUT LE POSER.
    #
    # UNE MUTATION A SURVÉCU À LA PREMIÈRE VERSION DE CETTE RÈGLE. Elle
    # parcourait la table réelle et remontait chaque entrée de l'index à sa
    # rubrique d'origine — vert, forcément : aujourd'hui AUCUNE rubrique de
    # source « saisie » ne porte de relevé, si bien que retirer le filtre sur
    # la source ne changeait rien. La règle constatait un état du catalogue au
    # lieu de mesurer la garde. On pose donc le cas à la main.
    faux = dict(A.RUBRIQUES)
    faux["dc1"] = list(A.RUBRIQUES["dc1"]) + [
        {"cle": "essai_saisie", "libelle": "Décidé pour cette consultation",
         "source": "saisie", "releve": "acheteur"}]
    vrai = A.RUBRIQUES
    try:
        A.RUBRIQUES = faux
        index = A._index_de_recopie({"dc1.essai_saisie": _extrait("À NE PAS RECOPIER")})
    finally:
        A.RUBRIQUES = vrai
    assert index == {}, (
        "une rubrique de source « saisie » entre dans l'index de recopie : "
        "un choix fait pour UNE pièce se propagerait aux vingt-deux autres — "
        "%r" % index)

    # ET LE TÉMOIN POSITIF, sur le même faux catalogue : la garde n'écarte pas
    # tout. Sans lui, un `return {}` sec passerait cette règle.
    try:
        A.RUBRIQUES = faux
        index2 = A._index_de_recopie({"dc1.acheteur": _extrait("VILLE DE PARIS")})
    finally:
        A.RUBRIQUES = vrai
    assert "acheteur" in index2, index2


def test_l_appariement_se_fait_sur_le_RELEVE_et_pas_sur_le_nom_de_rubrique():
    """Deux rubriques peuvent partager un nom sans désigner le même fait.

    C'est le relevé — « ce point précis du règlement » — qui porte l'identité.
    Mesuré sur un cas réel du catalogue : `objet_consultation` (DC1, DC2) et
    `objet_marche` (ATTRI1, DC4) portent des NOMS DIFFÉRENTS et le même
    relevé ; un appariement par nom laisserait l'ATTRI1 vide.
    """
    noms = {}
    for cle_piece, defs in A.RUBRIQUES.items():
        for r in defs:
            if r.get("source") == "consultation" and r.get("releve"):
                noms.setdefault(r["releve"], set()).add(r["cle"])
    partages = {k: v for k, v in noms.items() if len(v) > 1}
    assert partages, (
        "aucun relevé n'est porté par deux noms de rubrique : le témoin de "
        "cette règle a disparu du catalogue")

    lus = _cadres(LU_DC1)
    attri = [x for x in lus if x[0] == "acte_engagement"
             and x[1] == "objet_marche"]
    assert attri and attri[0][2] == "rempli", (
        "l'objet du marché de l'ATTRI1 reste vide alors que le DC1 l'a lu "
        "sous un autre nom de rubrique : %r" % attri)


# ═══════════════════════════════════════════════════════════════════════════
#  3. L'APERÇU, L'AGRANDISSEMENT, LE TÉLÉCHARGEMENT — le rendu est EXÉCUTÉ
# ═══════════════════════════════════════════════════════════════════════════

def _carte(remplissage, ouverte=None):
    prog = (_js_source("esc", "info", "aoMenuDocs", "aoFormulairesBoutons",
                       "aoProduira", "aoLotBarre", "aoLotEtatCarte",
                       "aoFocusRetenir", "aoFocusRendre", "aoRempliRendre")
            + "\nvar AO_FORMULAIRES = null, AO_DOC = '', AO_SAISIES = {};"
            + "\nvar AO_CHOISIES = {}, AO_PRODUIT = {}, AO_LOT_FMT = 'docx';"
            + "\nvar AO_DERNIER = null, AO_REMPLI = null;"
            + "\nvar AO_OUVERTE = process.env.OUVERTE || null, AO_APERCU = 4;"
            + "\nvar AO_ETAT_CLASSE = { rempli: 'ok', a_saisir: 'att',"
              " a_declarer: 'dec', non_trouve: 'att', invalide: 'mal' };"
            + "\nvar CADRE = { glossaire: {} };"
            + "\nvar zone = { innerHTML: '', querySelectorAll: function ()"
              " { return []; } };"
            + "\nfunction $(s) { return s === '#ig-ao-rempli' ? zone : null; }"
            + "\nfunction aoBrancherMenu() {}\nfunction aoBrancherLot() {}"
            + "\nfunction aoExporter() {}\nfunction aoFicheEnregistrer() {}"
            + "\nfunction aoRemplir() {}\nfunction aoOuvrir() {}"
            + "\nfunction aoPieceEmporter() {}"
            + "\nglobal.document = { querySelectorAll: function () { return []; },"
              " querySelector: function () { return null; } };"
            + "\naoRempliRendre(JSON.parse(process.env.R));"
            + "\nprocess.stdout.write(zone.innerHTML);\n")
    return _node(prog, R=json.dumps(remplissage), OUVERTE=ouverte or "")


def _piece_longue(r):
    """La première pièce qui a plus de rubriques que l'aperçu n'en montre."""
    return next(p for p in r["pieces"] if len(p["rubriques"]) > 4)


def test_la_carte_repliee_montre_un_APERCU_et_COMPTE_ce_qu_elle_cache():
    """Un aperçu muet ferait croire à une pièce de quatre rubriques.

    On compte les champs RÉELLEMENT produits pour une pièce donnée, repliée
    puis ouverte — et l'écart est le sujet de la règle.
    """
    r = A.remplir(fiche={"raison_sociale": "CONSEILPREV"})
    p = _piece_longue(r)
    prefixe = 'data-saisie="%s.' % p["cle"]

    replie = _carte(r).count(prefixe)
    ouvert = _carte(r, ouverte=p["cle"]).count(prefixe)

    assert replie <= 4, "la carte repliée déroule %d champs" % replie
    assert ouvert > replie, (
        "ouvrir la pièce n'ajoute rien : %d champs dans les deux cas" % ouvert)
    # LE COMPTE DE CE QUI RESTE EST ÉCRIT, et c'est un bouton.
    h = _carte(r)
    assert "autre(s) rubrique(s) — ouvrir en grand" in h, h[:400]
    assert 'data-ao-ouvrir="%s"' % p["cle"] in h


def test_l_apercu_montre_D_ABORD_ce_qui_demande_attention():
    """« REMPLI » NE VEUT PAS DIRE « RÉGLÉ », et une règle maison l'a montré.

    Une valeur lue dans un fichier que l'identification n'a pas su nommer
    porte l'état « rempli » et l'avertissement `a_confirmer` : c'est
    précisément celle qu'il faut relire. La ranger derrière les rubriques
    vides l'aurait fait disparaître de l'aperçu, et l'avertissement serait
    devenu du décor.
    """
    r = A.remplir(fiche={}, analyse=A.analyser(_DOCS), extraits=LU_DC1)
    h = _carte(r)
    # Les deux valeurs lues portent `a_confirmer` : elles doivent être VISIBLES
    # sur la carte repliée du DC1.
    assert "VILLE DE PARIS" in h, (
        "une valeur à confirmer est cachée dans le repli de l'aperçu")
    assert "ig-ao-og-conf" in h or "LECTURE ASSISTÉE" in h, h[:600]


def test_la_piece_ouverte_prend_la_LARGEUR_et_ses_champs_grossissent():
    """« Ouvrir en grand » doit l'être pour de vrai.

    La classe est posée par le rendu ; la largeur et la taille des champs
    viennent de la feuille de la page. Les deux se mesurent ensemble : une
    classe sans règle CSS ne change rien à l'écran, et c'est le défaut qu'on
    chasse — une marque posée qui ne produit aucun effet.
    """
    r = A.remplir(fiche={"raison_sociale": "CONSEILPREV"})
    p = _piece_longue(r)
    h = _carte(r, ouverte=p["cle"])
    assert "ig-ao-cp-grand" in h, "la pièce ouverte n'est pas marquée"
    assert h.count("ig-ao-cp-grand") == 1, "plus d'une pièce ouverte à la fois"

    css = io.open(os.path.join(ICI, "ingenierie-datacenter.html"),
                  encoding="utf-8").read()
    bloc = css[css.index(".ig-ao-cp-grand{"):]
    bloc = bloc[:bloc.index("\n  .ig-ao-cpa{")]
    assert "grid-column:1 / -1" in bloc, bloc[:300]
    assert ".ig-ao-cp-grand .ig-ao-si{" in bloc, (
        "les champs de la pièce ouverte gardent leur taille de colonne")


def test_le_bouton_de_repli_dit_l_etat_ou_l_on_EST():
    """Un bouton qui dit « Ouvrir » sur une pièce ouverte fait refermer par
    erreur ce qu'on venait d'ouvrir."""
    r = A.remplir(fiche={"raison_sociale": "CONSEILPREV"})
    p = _piece_longue(r)
    ferme, ouvert = _carte(r), _carte(r, ouverte=p["cle"])
    assert "Ouvrir en grand" in ferme and "Replier" not in ferme
    assert "Replier" in ouvert
    assert 'aria-expanded="true"' in ouvert
    assert 'aria-expanded="true"' not in ferme


def test_CHAQUE_carte_porte_son_bouton_de_telechargement_sans_rien_lancer():
    """Le « ⬇ » n'apparaissait qu'APRÈS une production en lot.

    Pour emporter UNE pièce, il fallait donc lancer les vingt-trois. Le bouton
    est désormais dans l'en-tête de chaque carte, produite ou non.
    """
    r = A.remplir(fiche={"raison_sociale": "CONSEILPREV"})
    h = _carte(r)
    boutons = set(re.findall(r'data-ao-prendre="([^"]+)"', h))
    assert boutons == {p["cle"] for p in r["pieces"]}, (
        "manquent : %r" % sorted({p["cle"] for p in r["pieces"]} - boutons))


def test_le_bouton_d_emport_NE_selectionne_PAS_la_carte():
    """La carte est un interrupteur : cliquer dedans la choisit.

    Prendre un document ou l'ouvrir en grand n'est pas choisir de le déposer.
    La réserve existe déjà dans le brancheur — elle ignore
    `input, textarea, select, a, button` — et les deux commandes SONT des
    boutons. Cette règle mesure que la réserve les couvre toujours, parce
    qu'un jour où elle serait resserrée, ouvrir une pièce la décocherait.
    """
    bloc = _js_source("aoBrancherLot")
    m = re.search(r'closest\(("|\')([^"\']+)\1\)', bloc)
    assert m, "le brancheur ne réserve plus aucun élément au clic"
    assert "button" in m.group(2), m.group(2)
    # ET LES DEUX COMMANDES SONT BIEN DES <button>, pas des <a> ni des <span>.
    r = A.remplir(fiche={"raison_sociale": "CONSEILPREV"})
    h = _carte(r)
    for attr in ("data-ao-prendre", "data-ao-ouvrir"):
        for m2 in re.finditer(r"<(\w+)[^>]*%s=" % attr, h):
            assert m2.group(1) == "button", (attr, m2.group(0))


def test_les_brouillons_sont_RETENUS_pour_pouvoir_partir_avec_l_archive():
    """Ils ne vivaient que dans le HTML de leur bloc.

    « Tout le dossier » ne pouvait pas les joindre, et fermer l'onglet les
    perdait tous les onze. On exécute le rendu d'un brouillon et l'on regarde
    le stock — relire la source dirait qu'une affectation existe, pas qu'elle
    s'exécute.
    """
    prog = (_js_source("esc", "fr", "aoRedigerRendre")
            + "\nvar AO_LOT_FMT = 'docx';"
            + "\nglobal.window = {};"      # le rendu cherche CPMarkdown
            + "\nfunction aoBrouillonEmporter() {}"
            + "\nvar z = { innerHTML: '', querySelectorAll: function ()"
              " { return []; } };"
            + "\naoRedigerRendre(z, {cle: 'memoire_technique',"
              " nom: 'Mémoire technique', markdown: '# Mémoire\\n\\nTexte.'});"
            + "\naoRedigerRendre(z, {cle: 'dpgf', nom: 'DPGF', markdown: '# D'});"
            + "\n/* Un rendu SANS texte ne doit rien stocker : un brouillon vide"
              "   dans l'archive se télécharge et déçoit. */"
            + "\naoRedigerRendre(z, {cle: 'vide', nom: 'Vide'});"
            + "\nprocess.stdout.write(JSON.stringify(aoBrouillonsListe()));\n")
    # `aoBrouillonsListe` et `AO_BROUILLONS` vivent à côté de `aoRedigerRendre`
    # dans le module : on les prend avec.
    prog = _js_source("aoBrouillonsListe") + "\nvar AO_BROUILLONS = {};\n" + prog
    lu = json.loads(_node(prog))
    assert {x["piece"] for x in lu} == {"memoire_technique", "dpgf"}, lu
    assert all(x["texte"] for x in lu), lu


def test_l_archive_demandee_par_la_page_EMPORTE_les_brouillons():
    """Le stock ne sert à rien s'il ne part pas.

    Mesuré sur la charge utile que la page compose vraiment : `aoDossierComplet`
    doit poser `brouillons` dans le corps de sa requête.
    """
    bloc = _js_source("aoDossierComplet")
    assert "brouillons: aoBrouillonsListe()" in bloc, (
        "l'archive part sans les brouillons")
    # ET LE PÉRIMÈTRE RESTE, sinon l'archive porterait les vingt-trois pièces
    # quand la consultation n'en demande que douze.
    assert "perimetre: aoPerimetre()" in bloc
