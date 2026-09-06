# -*- coding: utf-8 -*-
"""Choisir plusieurs pièces, et les faire produire EN MÊME TEMPS.

CE QUI ÉTAIT EN CAUSE. Les vingt-trois pièces des deux dossiers se remplissaient
une par une, et seules les quatre qui ont un formulaire de l'État avaient un
bouton. Répondre à une consultation, c'était donc vingt-trois gestes, dont
dix-neuf n'existaient pas.

LES DEUX PROPRIÉTÉS QUE CES RÈGLES TIENNENT, et qu'aucune lecture de source ne
donne :

  · CHAQUE PIÈCE PRODUIT QUELQUE CHOSE DE RÉEL, et ce quelque chose suit sa
    VOIE. Quatre rendent le fichier du ministère ; les autres rendent leur
    report, leur plan, ou la demande à faire avec son délai. Aucune ne rend un
    fac-similé — un imprimé refait ici serait refusé, ou pire, accepté et faux.

  · « SIMULTANÉMENT » VEUT DIRE QUE LES PRODUCTIONS SE RECOUVRENT. Une file
    d'attente déguisée en lot passe toute relecture : elle appelle les mêmes
    fonctions, dans le même ordre, et rend le même résultat — seulement plus
    lentement. On mesure donc combien d'appels sont EN VOL avant que le premier
    revienne. Mesuré en navigateur : 6 au même instant, 23 pièces en 1,25 s pour
    6,7 s de travail.
"""
import io
import json
import os
import re
import subprocess
import sys
import zipfile

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc                                                       # noqa: E402
import ao_formulaires                                              # noqa: E402
from conftest import ORIGINE                                       # noqa: E402
from test_ao_formulaires import _js_source                         # noqa: E402

import pytest                                                      # noqa: E402

FICHE = {"raison_sociale": "CONSEILPREV", "siret": "73282932000074"}
MODELES = {v["piece"] for v in ao_formulaires.MODELES.values()}


def _src(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


def _pieces():
    return ao_dc.remplir(fiche=FICHE, analyse=None, saisies={})["pieces"]


def _produire(cl, cle, fmt="docx"):
    return cl.post("/api/datacenter/marche/piece",
                   json={"piece": cle, "fiche": FICHE, "format": fmt},
                   headers=ORIGINE)


def _texte_docx(blob):
    """Le texte du document, lu dans le fichier — pas dans le Markdown qui a
    servi à l'écrire. Un document vide passerait le second contrôle."""
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    # LA TYPOGRAPHIE EST APPLIQUÉE AU RENDU — l'apostrophe droite des sources
    # devient courbe dans le document. Chercher la droite ferait échouer la
    # règle sur un document parfaitement juste.
    return re.sub(r"<[^>]+>", " ", xml).replace("\u2019", "'")


# ── 1. CHAQUE PIÈCE PRODUIT, ET CE QU'ELLE PRODUIT SUIT SA VOIE ──────────

def test_les_vingt_trois_pieces_produisent_TOUTES_un_document(connecte):
    """ON LES ÉNUMÈRE, ON N'EN ÉCHANTILLONNE PAS TROIS. Une pièce qui refuse
    de produire laisse une carte grise au milieu de vingt-deux vertes, et
    personne ne sait si c'est une nature ou une panne."""
    muettes = []
    for p in _pieces():
        r = _produire(connecte, p["cle"])
        if r.status_code != 200 or len(r.data) < 500:
            muettes.append("%s (%s)" % (p["cle"], r.status_code))
    assert not muettes, "ces pièces ne produisent rien : " + ", ".join(muettes)


def test_la_production_suit_la_VOIE_de_la_piece():
    """Le référentiel dit déjà comment chaque pièce se fabrique. Une seconde
    classification, écrite ici, dériverait de la première."""
    attendu = {"remplir": "report", "completer": "plan",
               "rediger": "plan", "obtenir": "demande"}
    for p in _pieces():
        v = ao_dc.production(p, MODELES)
        if p["cle"] in MODELES:
            assert v == "formulaire_officiel", p["cle"]
        else:
            assert v == attendu[p["voie"]], (p["cle"], p["voie"], v)
    assert set(ao_dc.PRODUCTIONS) == {"formulaire_officiel", "report", "plan",
                                      "demande"}


def test_un_formulaire_officiel_sort_en_Word_QUEL_QUE_SOIT_le_format_demande(connecte):
    """Ce qui sort EST le fichier du ministère. Le convertir en PDF ou en
    classeur en ferait un fac-similé, qui serait refusé — ou pire, accepté et
    faux."""
    for fmt in ("docx", "pdf", "xlsx"):
        r = _produire(connecte, "dc1", fmt)
        assert r.status_code == 200
        d = json.loads(r.headers["X-Piece"])
        assert d["production"] == "formulaire_officiel"
        assert r.headers["Content-Disposition"].endswith(".docx"), fmt
        assert zipfile.ZipFile(io.BytesIO(r.data)).namelist()[0].startswith(
            ("word/", "[Content_Types]", "_rels"))


def test_une_piece_SANS_formulaire_officiel_suit_le_format_demande(connecte):
    for fmt, sig in (("docx", "word/"), ("xlsx", "xl/")):
        r = _produire(connecte, "memoire_technique", fmt)
        assert r.status_code == 200
        noms = zipfile.ZipFile(io.BytesIO(r.data)).namelist()
        assert any(n.startswith(sig) for n in noms), (fmt, noms[:3])


def test_le_document_d_une_piece_contient_VRAIMENT_ses_rubriques(connecte):
    """On ouvre le fichier produit. Vérifier le Markdown qui a servi à l'écrire
    serait vert le jour où la mise en page perd le corps du document."""
    r = _produire(connecte, "honneur")
    t = _texte_docx(r.data)
    p = next(x for x in _pieces() if x["cle"] == "honneur")
    assert p["nom"][:20] in t
    attendues = [l["libelle"] for l in p["rubriques"]][:5]
    absentes = [a for a in attendues if a[:18] not in t]
    assert not absentes, "rubriques absentes du document : %s" % absentes


def test_une_piece_A_OBTENIR_porte_son_DELAI_dans_le_document(connecte):
    """C'est la seule chose qu'on ne rattrape pas la dernière nuit : une
    attestation se demande, elle ne se rédige pas."""
    r = _produire(connecte, "pouvoirs")
    t = _texte_docx(r.data)
    assert "Délai d'obtention" in t
    d = json.loads(r.headers["X-Piece"])
    assert d["production"] == "demande"


def test_une_piece_inconnue_est_refusee_et_dit_lesquelles_existent(connecte):
    r = _produire(connecte, "nexiste_pas")
    assert r.status_code == 400
    j = r.get_json()
    assert j["error"] == "piece_inconnue"
    assert len(j["disponibles"]) == 23


def test_l_en_tete_dit_ce_qui_a_ete_PORTE_et_ce_qui_RESTE(connecte):
    """Un téléchargement ne rend pas de JSON, et une pièce partielle se lirait
    comme complète si personne ne disait ce qui manque."""
    r = _produire(connecte, "honneur")
    d = json.loads(r.headers["X-Piece"])
    for c in ("cle", "nom", "production", "production_nom", "places"):
        assert c in d, d
    assert isinstance(d["places"], int)
    assert d["reste"] or d["non_places"], (
        "une pièce qui ne dit RIEN de ce qui reste : le dossier d'essai n'a "
        "pourtant qu'une raison sociale et un SIRET")


def test_la_route_est_fermee_a_l_anonyme(anonyme):
    r = anonyme.post("/api/datacenter/marche/piece",
                     json={"piece": "dc1"}, headers=ORIGINE)
    assert r.status_code in (401, 403)


def test_le_bloc_d_une_piece_n_est_ECRIT_qu_une_fois():
    """Le document d'ensemble et celui d'une pièce partagent leur corps. Deux
    rédactions du même bloc finiraient par ne plus dire la même chose, et c'est
    celle qu'on oublie qui circulerait."""
    r = ao_dc.remplir(fiche=FICHE, analyse=None, saisies={})
    seule = ao_dc.markdown_piece(r, "honneur", MODELES)
    ensemble = ao_dc.markdown_remplissage(r)
    # Le corps de la pièce, tel quel, dans le document d'ensemble.
    corps = seule.split("### ", 1)
    reperes = [l for l in seule.split("\n")
               if l.startswith("| ") and "|" in l[2:]][:4]
    assert reperes, seule[:400]
    for l in reperes:
        assert l in ensemble, "le bloc de la pièce diverge du document : " + l


# ── 2. LE LOT — LA PAGE, EXÉCUTÉE ────────────────────────────────────────

def _node(prog, env=None):
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60, env=dict(os.environ, **(env or {})))
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout


def _banc_lot(corps):
    """Le lot, exécuté hors navigateur, avec un `demander` sous contrôle.

    CE QUE LE BANC PERMET, ET QU'AUCUNE LECTURE NE DONNE : compter combien
    d'appels sont partis AVANT que le premier revienne. Une file d'attente
    déguisée en lot appelle les mêmes fonctions dans le même ordre — seule
    cette mesure les sépare.
    """
    return _node(
        _js_source("aoLotBarre", "aoLotEtatCarte", "aoLotMsg",
                   "aoLotRafraichirCarte", "aoLotCompter", "aoLotBasculer",
                   "aoLotRemplir", "aoLotUne")
        + "\nvar AO_CHOISIES = {}, AO_PRODUIT = {}, AO_LOT_FMT = 'docx';"
        + "\nvar AO_DERNIER = null, AO_FICHE = {}, AO_ANALYSE = null;"
        + "\nvar AO_SAISIES = {}, DELAI_MOYEN = 1000;"
        + "\nvar AO_LOT_FRONT = " + str(_front()) + ";"
        + "\nvar appels = [], resolveurs = [];"
        + "\nfunction demander(u, o) { appels.push(JSON.parse(o.body).piece);"
        + "  return new Promise(function (res) { resolveurs.push(res); }); }"
        + "\nfunction esc(x) { return String(x == null ? '' : x); }"
        + "\nglobal.URL = { createObjectURL: function () { return 'blob:x'; },"
        + "  revokeObjectURL: function () {} };"
        + "\nglobal.document = { querySelector: function () { return null; },"
        + "  querySelectorAll: function () { return []; } };"
        + "\nglobal.window = {};"
        + corps)


def _front():
    m = re.search(r"var AO_LOT_FRONT = (\d+);", _src("ingenierie-dc.js"))
    assert m, "la borne de front n'est plus déclarée"
    return int(m.group(1))


def test_le_front_est_borne_ET_superieur_a_un():
    """UN SEUL À LA FOIS SERAIT UNE FILE, pas un lot — et la page promettrait
    une simultanéité qu'elle n'aurait pas. Trop haut, le navigateur met en
    file lui-même et le serveur répond plus lentement à chacun."""
    n = _front()
    assert 2 <= n <= 12, "front de %d" % n


def test_le_lot_lance_PLUSIEURS_productions_avant_qu_une_seule_revienne():
    """LA RÈGLE QUI SÉPARE UN LOT D'UNE FILE. Aucune réponse n'est rendue :
    on compte ce qui est parti. Une file n'aurait envoyé qu'un seul appel."""
    r = _banc_lot(
        "\nvar r = { pieces: [] };"
        "\nfor (var i = 0; i < 20; i++) { var c = 'p' + i;"
        "  r.pieces.push({ cle: c, nom: c, bloquant: false });"
        "  AO_CHOISIES[c] = true; }"
        "\nAO_DERNIER = r;"
        "\naoLotRemplir(r);"
        "\nsetTimeout(function () {"
        "  process.stdout.write(JSON.stringify({ partis: appels.length,"
        "    cours: Object.keys(AO_PRODUIT).filter("
        "      function (k) { return AO_PRODUIT[k].etat === 'cours'; }).length"
        "  })); }, 30);\n")
    d = json.loads(r)
    assert d["partis"] == _front(), (
        "%d appel(s) partis avant tout retour : le lot n'en lance pas "
        "plusieurs à la fois" % d["partis"])
    assert d["cours"] == 20, (
        "%d carte(s) seulement passent en « en cours » : les autres restent "
        "muettes pendant qu'on les produit" % d["cours"])


def test_une_reponse_ne_fait_basculer_QUE_sa_propre_carte():
    """C'est ce qui rend l'état lisible : on voit le dossier se remplir, on ne
    regarde pas une barre avancer."""
    r = _banc_lot(
        "\nvar r = { pieces: [{cle:'a',nom:'a'},{cle:'b',nom:'b'},"
        "  {cle:'c',nom:'c'}] };"
        "\nr.pieces.forEach(function (p) { AO_CHOISIES[p.cle] = true; });"
        "\nAO_DERNIER = r;"
        "\naoLotRemplir(r);"
        "\nsetTimeout(function () {"
        "  resolveurs[0]({ ok: true, headers: { get: function (h) {"
        "      return h === 'X-Piece' ? '{\"places\":2,\"reste\":[]}'"
        "        : 'attachment; filename=\"a.docx\"'; } },"
        "    blob: function () { return Promise.resolve('BLOB'); } });"
        "  setTimeout(function () {"
        "    process.stdout.write(JSON.stringify(AO_PRODUIT)); }, 30); }, 20);\n")
    d = json.loads(r)
    assert d["a"]["etat"] == "fait", d
    assert d["b"]["etat"] == "cours" and d["c"]["etat"] == "cours", d
    assert d["a"]["url"] == "blob:x" and d["a"]["nom"] == "a.docx", d


def test_un_refus_passe_la_carte_au_rouge_avec_SA_raison():
    r = _banc_lot(
        "\nvar r = { pieces: [{cle:'a',nom:'a'}] };"
        "\nAO_CHOISIES.a = true; AO_DERNIER = r;"
        "\naoLotRemplir(r);"
        "\nsetTimeout(function () {"
        "  resolveurs[0]({ ok: false, json: function () {"
        "    return Promise.resolve({ message: 'Modèle absent du serveur' });"
        "  } });"
        "  setTimeout(function () {"
        "    process.stdout.write(JSON.stringify(AO_PRODUIT)); }, 30); }, 20);\n")
    d = json.loads(r)
    assert d["a"]["etat"] == "mal"
    assert "Modèle absent" in d["a"]["texte"], d


# ── 3. LES COULEURS, ET CE QU'ELLES DISENT ───────────────────────────────

ETATS = {"sel": "#1D4ED8", "cours": "#1D4ED8", "fait": "#15803D",
         "mal": "#DC2626"}


def test_les_quatre_etats_ont_chacun_leur_regle_et_sa_couleur():
    """CHOISIE bleu foncé, REMPLIE vert foncé, EN ÉCHEC rouge — c'est le geste
    demandé, et il ne se lit que si les trois sont distincts."""
    page = _src("ingenierie-datacenter.html")
    for etat, couleur in ETATS.items():
        m = re.search(r"\.ig-ao-cp-%s\{[^}]*" % etat, page)
        assert m, "l'état « %s » n'a pas de règle" % etat
        assert couleur in m.group(0), (
            "l'état « %s » n'est pas en %s : %s" % (etat, couleur, m.group(0)))
        assert "2px" in m.group(0), (
            "l'état « %s » n'épaissit pas le contour : une différence de "
            "teinte seule ne se voit pas sur une grille dense, et pas du tout "
            "pour qui distingue mal le rouge du vert" % etat)
    assert len({ETATS["sel"], ETATS["fait"], ETATS["mal"]}) == 3


def test_la_carte_porte_la_classe_de_SON_etat():
    """Exécutée, pas relue : `esc(undefined)` ou une propriété absente ne se
    voient qu'en faisant tourner la fonction."""
    from test_ao_formulaires import _carte_rendue, _rempli
    h = _carte_rendue(_rempli())
    assert h.count('role="button"') == 23, h[:200]
    assert h.count('aria-pressed="false"') == 23
    assert h.count('tabindex="0"') >= 23


def test_la_carte_est_un_interrupteur_au_CLAVIER_aussi():
    """Un `div` cliquable sans écouteur clavier se choisit à la souris et
    jamais autrement."""
    js = _src("ingenierie-dc.js")
    bloc = js[js.index("function aoBrancherLot("):]
    bloc = bloc[:bloc.index("\n  }")]
    assert 'addEventListener("keydown"' in bloc
    assert '"Enter"' in bloc and '" "' in bloc


def test_la_liste_deroulante_CHOISIT_aussi():
    """Le geste demandé est « au clic OU dans la liste ». Une liste qui ne
    ferait que défiler obligerait à retrouver la carte pour la cliquer.

    ON EXÉCUTE LE GESTIONNAIRE, ON NE CHERCHE PLUS LA LIGNE. Une mutation l'a
    montré : mettre l'affectation dans une branche morte — `if (false)` — la
    laissait dans le fichier, et la règle restait verte pendant que la liste
    ne choisissait plus rien."""
    r = _node(
        _js_source("aoBrancherMenu")
        + "\nvar AO_DOC = '', AO_CHOISIES = {};"
        + "\nvar sel = { value: 'dc2', _f: null,"
        + "  addEventListener: function (t, f) { if (t === 'change') this._f = f; } };"
        + "\nfunction $(s) { return s === '#ig-ao-doc' ? sel : null; }"
        + "\nfunction aoLotRafraichirCarte() {}"
        + "\nfunction aoLotCompter() {}"
        + "\nglobal.document = { querySelectorAll: function () { return []; },"
        + "  querySelector: function () { return null; } };"
        + "\naoBrancherMenu({ pieces: [{cle:'dc2', famille:'f'}],"
        + "  familles: { f: { nom:'F', etablit:'e', qui:'q' } } });"
        + "\nsel._f();"
        + "\nprocess.stdout.write(JSON.stringify(AO_CHOISIES));\n")
    assert json.loads(r) == {"dc2": True}, (
        "choisir dans la liste n'ajoute pas la pièce au lot : %s" % r)


def test_la_barre_COMPTE_avant_de_proposer():
    """« Remplir les pièces choisies » sans le nombre laisse lancer vingt-trois
    productions en croyant en lancer une."""
    r = _banc_lot(
        "\nvar r = { pieces: [{cle:'a'},{cle:'b'},{cle:'c'}], familles: {} };"
        "\nAO_CHOISIES.a = true;"
        "\nprocess.stdout.write(aoLotBarre(r));\n")
    assert "1 choisie(s) sur 3" in r, r[:300]
    assert "Remplir les 1 pièce(s) choisie(s)" in r
    r2 = _banc_lot(
        "\nvar r = { pieces: [{cle:'a'}], familles: {} };"
        "\nprocess.stdout.write(aoLotBarre(r));\n")
    assert "disabled" in r2, "le bouton est actif sans aucun choix"


# ── 4. LES DEUX DÉPÔTS, ET LE DOSSIER QUI SURVIT ─────────────────────────

def test_les_deux_depots_de_la_page_disent_OU_VA_ce_qu_on_y_met():
    """Déposer un règlement de consultation dans la base de connaissance ne le
    fait pas analyser comme un dossier de marché, et l'inverse non plus. Cette
    erreur-là ne se voit qu'au moment où l'on cherche le résultat là où il
    n'est pas."""
    # LES COMMENTAIRES SONT RETIRÉS D'ABORD, et une mutation a montré
    # pourquoi : le commentaire qui EXPLIQUE la mention contient les mêmes
    # mots qu'elle. La règle restait verte pendant que la mention disparaissait
    # de la page — verte grâce au texte que le lecteur ne voit jamais.
    page = re.sub(r"<!--.*?-->", " ", _src("ingenierie-datacenter.html"),
                  flags=re.S)
    i13 = page.index("Apporter vos documents")
    i14 = page.index("Répondre à l'appel d'offres")
    b13, b14 = page[i13:i14], page[i14:i14 + 4000]
    assert "base de connaissance" in b13 and "§&nbsp;14" in b13, (
        "le § 13 ne dit pas ce qu'il n'est pas")
    assert "§&nbsp;13" in b14 and "conservé chiffré" in b14, (
        "le § 14 ne dit ni ce qu'il n'est pas, ni qu'il conserve")


def test_le_dossier_conserve_porte_DEJA_son_analyse():
    """Elle est relevée AU DÉPÔT, avec la version du releveur. La refaire à la
    lecture ferait varier le résultat quand les motifs évoluent."""
    src = _src("ao_projet.py")
    bloc = src[src.index("\ndef deposer("):src.index("\ndef lire(")]
    assert "ao_dc.analyser(" in bloc and 'analyse["version_ao_dc"]' in bloc


def test_la_page_REPREND_le_dossier_conserve_sans_rien_redeposer():
    js = _src("ingenierie-dc.js")
    bloc = js[js.index("function aoProjetReprendre("):]
    bloc = bloc[:bloc.index("\n  }")]
    assert "AO_ANALYSE = d.analyse" in bloc
    assert "if (!d || AO_ANALYSE) return" in bloc, (
        "la reprise écraserait une analyse déjà à l'écran")
    assert "!Object.keys(AO_FICHE || {}).length" in bloc, (
        "la reprise écraserait une saisie en cours")
    appel = js[js.index("AO_PROJET_ETAT = xj[1];"):][:200]
    assert "aoProjetReprendre()" in appel, (
        "la reprise n'est appelée nulle part : elle ne servirait à rien")
