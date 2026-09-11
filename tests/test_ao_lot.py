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
import html
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
    """Les pièces TELLES QUE LA ROUTE LES VOIT.

    LE SOCLE EST INCLUS, ET C'EST NÉCESSAIRE. `_ao_charge` fait partir la fiche
    du dossier d'entreprise et laisse ce que l'appelant envoie la corriger.
    Interroger le module avec la seule fiche d'essai donnerait des pièces plus
    pauvres que celles que la route produit, et une règle qui compare les deux
    mesurerait l'écart entre son propre montage et le produit."""
    return ao_dc.remplir(fiche=_socle(), analyse=None, saisies={})["pieces"]


def _socle():
    """La fiche telle que la route la compose : le dossier d'entreprise, que
    ce que l'appelant envoie corrige. UN SEUL ENDROIT — deux montages
    divergeraient, et la règle mesurerait l'écart entre eux."""
    import dossier_entreprise as _de
    socle = dict(_de.fiche_candidat()["fiche"])
    socle.update(FICHE)
    return socle


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

def test_les_vingt_trois_pieces_produisent_TOUTES_un_document(marche):
    """ON LES ÉNUMÈRE, ON N'EN ÉCHANTILLONNE PAS TROIS. Une pièce qui refuse
    de produire laisse une carte grise au milieu de vingt-deux vertes, et
    personne ne sait si c'est une nature ou une panne."""
    muettes = []
    for p in _pieces():
        r = _produire(marche, p["cle"])
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


def test_un_formulaire_officiel_sort_en_Word_QUEL_QUE_SOIT_le_format_demande(marche):
    """Ce qui sort EST le fichier du ministère. Le convertir en PDF ou en
    classeur en ferait un fac-similé, qui serait refusé — ou pire, accepté et
    faux."""
    for fmt in ("docx", "pdf", "xlsx"):
        r = _produire(marche, "dc1", fmt)
        assert r.status_code == 200
        d = json.loads(r.headers["X-Piece"])
        assert d["production"] == "formulaire_officiel"
        assert r.headers["Content-Disposition"].endswith(".docx"), fmt
        assert zipfile.ZipFile(io.BytesIO(r.data)).namelist()[0].startswith(
            ("word/", "[Content_Types]", "_rels"))


def test_une_piece_SANS_formulaire_officiel_suit_le_format_demande(marche):
    for fmt, sig in (("docx", "word/"), ("xlsx", "xl/")):
        r = _produire(marche, "memoire_technique", fmt)
        assert r.status_code == 200
        noms = zipfile.ZipFile(io.BytesIO(r.data)).namelist()
        assert any(n.startswith(sig) for n in noms), (fmt, noms[:3])


def test_le_document_d_une_piece_contient_VRAIMENT_ses_rubriques(marche):
    """On ouvre le fichier produit. Vérifier le Markdown qui a servi à l'écrire
    serait vert le jour où la mise en page perd le corps du document."""
    r = _produire(marche, "honneur")
    t = _texte_docx(r.data)
    p = next(x for x in _pieces() if x["cle"] == "honneur")
    assert p["nom"][:20] in t
    attendues = [l["libelle"] for l in p["rubriques"]][:5]
    absentes = [a for a in attendues if a[:18] not in t]
    assert not absentes, "rubriques absentes du document : %s" % absentes


def test_une_piece_A_OBTENIR_porte_son_DELAI_dans_le_document(marche):
    """C'est la seule chose qu'on ne rattrape pas la dernière nuit : une
    attestation se demande, elle ne se rédige pas."""
    r = _produire(marche, "pouvoirs")
    t = _texte_docx(r.data)
    assert "Délai d'obtention" in t
    d = json.loads(r.headers["X-Piece"])
    assert d["production"] == "demande"


def test_une_piece_inconnue_est_refusee_et_dit_lesquelles_existent(marche):
    r = _produire(marche, "nexiste_pas")
    assert r.status_code == 400
    j = r.get_json()
    assert j["error"] == "piece_inconnue"
    assert len(j["disponibles"]) == 23


def test_l_en_tete_dit_ce_qui_a_ete_PORTE_et_ce_qui_RESTE(marche):
    """Un téléchargement ne rend pas de JSON, et une pièce partielle se lirait
    comme complète si personne ne disait ce qui manque."""
    r = _produire(marche, "honneur")
    d = json.loads(r.headers["X-Piece"])
    for c in ("cle", "nom", "production", "production_nom", "places"):
        assert c in d, d
    assert isinstance(d["places"], int)

    # LA RÈGLE CHERCHE UNE PIÈCE PARTIELLE AU LIEU D'EN SUPPOSER UNE.
    #
    # POURQUOI ELLE A CHANGÉ. Elle éprouvait `honneur` en tenant pour acquis
    # qu'il lui manquerait toujours quelque chose — « le dossier d'essai n'a
    # qu'une raison sociale et un SIRET ». La fiche part désormais du dossier
    # d'entreprise, et cette pièce-là n'a plus rien à compléter : la règle
    # tombait sur une amélioration. Ce qu'elle doit tenir n'est pas « cette
    # pièce est partielle » mais « une pièce partielle DIT ce qui lui manque ».
    #
    # Dix des vingt champs de la fiche ne sont pas portés par le dossier
    # (SIRET, RCS, NAF, effectif, chiffres d'affaires, assurance) : il reste
    # donc forcément des pièces incomplètes, et si un jour il n'en reste
    # aucune, la première assertion le dira plutôt que de passer en silence.
    # QUELLES PIÈCES SONT RÉELLEMENT INCOMPLÈTES : c'est le module qui le dit,
    # pas une supposition de la règle. Une pièce SANS rubrique — un plan à
    # rédiger, un justificatif à obtenir — n'est pas « incomplète et muette » :
    # elle n'a rien à placer, et c'est sa nature.
    par_cle = {p["cle"]: p for p in _pieces()}
    incompletes = [c for c, p in par_cle.items()
                   if [x for x in (p.get("rubriques") or [])
                       if x.get("source") == "fiche" and not x.get("valeur")]]
    assert incompletes, (
        "aucune pièce n'attend plus rien de la fiche, alors que dix des vingt "
        "champs ne sont pas portés par le dossier d'entreprise")
    muettes = []
    for cle in incompletes:
        h = json.loads(_produire(marche, cle).headers["X-Piece"])
        if not ((h.get("reste") or []) or (h.get("non_places") or [])):
            muettes.append(cle)
    assert not muettes, (
        "ces pièces attendent des champs de la fiche et ne disent RIEN de ce "
        "qui leur manque : %s" % muettes)


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
    # LA FENÊTRE ÉTAIT DE 200 OCTETS APRÈS L'ANCRE, ET C'EST CE QU'ELLE
    # MESURAIT. Un commentaire ajouté entre l'affectation et l'appel la
    # faisait tomber alors que rien du comportement n'avait changé — la règle
    # mesurait la longueur d'un commentaire. On borne désormais à la FONCTION
    # qui porte l'affectation : c'est ce qu'on veut dire, et un commentaire
    # n'en change pas le sens.
    i = js.index("function aoProjetEtat(")
    fonction = js[i:js.index("\n  }", i)]
    assert "AO_PROJET_ETAT = xj[1];" in fonction, (
        "l'état n'est plus retenu là où on le croyait")
    assert "aoProjetReprendre()" in fonction, (
        "la reprise n'est appelée nulle part : elle ne servirait à rien")


# ══════════════════════════════════════════════════════════════════════════
# 5. LE DOSSIER SE CHARGE UNE PAR UNE, ET IL SERT VRAIMENT À REMPLIR
# ══════════════════════════════════════════════════════════════════════════
#
# CE QUI A ÉTÉ MESURÉ, ET QUI A MOTIVÉ CE BLOC. Déposer une pièce de plus
# EFFAÇAIT les précédentes : deux pièces déposées, puis une troisième, et le
# dossier n'en portait plus qu'une. Charger « une par une » était donc
# destructeur, et silencieusement — le dépôt répondait 200.

DCE = [
    {"nom": "reglement-de-consultation.pdf", "texte": """
RÈGLEMENT DE LA CONSULTATION
Pouvoir adjudicateur : COMMUNAUTÉ D'AGGLOMÉRATION DE VAL-D'EUROPE
Objet du marché : construction d'un centre de données de 12 MW — lot 2, CVC.
Référence de la consultation : 2026-DC-0142
La consultation est allotie en 4 lots. Le présent lot est le lot n° 2.
Procédure : appel d'offres ouvert.
Les offres sont remises sur la plateforme PLACE.
Critères de jugement des offres : prix 40 %, valeur technique 60 %.
Durée du marché : 24 mois à compter de la notification.
"""},
    {"nom": "CCAP.pdf", "texte": """
CAHIER DES CLAUSES ADMINISTRATIVES PARTICULIÈRES
Article 12 — Pénalités de retard : 1/1000 du montant par jour de retard.
Article 15 — Avance : 5 % du montant du marché.
"""},
    {"nom": "CCTP.pdf", "texte": "Le titulaire fournit et pose les groupes froids."},
]


@pytest.fixture
def projet(marche, monkeypatch):
    """Un projet du compte, avec le chiffrement du dossier ACTIF.

    SANS CLÉ, LE MODULE REFUSE D'ÉCRIRE — et il a raison : conserver un dossier
    de consultation en clair serait pire que ne pas le conserver. La règle
    fournit donc une clé, au lieu de sauter le contrôle."""
    import ao_projet
    from cryptography.fernet import Fernet
    monkeypatch.setenv(ao_projet.VAR_CLE, Fernet.generate_key().decode())
    r = marche.post("/api/datacenter/projets",
                    json={"nom": "Dossier d'essai"}, headers=ORIGINE)
    assert r.status_code == 200, r.data[:200]
    return r.get_json()["projet"]["id"]


def _deposer(cl, pid, **kw):
    return cl.post("/api/datacenter/marche/projet/dossier",
                   json=dict(projet=pid, **kw), headers=ORIGINE)


def _dossier(cl, pid):
    d = cl.get("/api/datacenter/marche/projet/dossier?projet=" + pid,
               headers=ORIGINE).get_json()["dossier"] or {}
    return ([p["nom"] for p in (d.get("pieces") or [])],
            d.get("analyse") or {})


def test_les_pieces_se_chargent_UNE_PAR_UNE_sans_effacer_les_precedentes(
        marche, projet):
    """LE DÉFAUT MESURÉ, ET SA RÈGLE. Deux pièces, puis une troisième : le
    dossier en portait UNE. Le geste « une par une » que la page propose était
    donc une façon de perdre son dossier."""
    _deposer(marche, projet, pieces=DCE[:2], fiche={})
    noms, _ = _dossier(marche, projet)
    assert noms == ["reglement-de-consultation.pdf", "CCAP.pdf"], noms
    _deposer(marche, projet, pieces=DCE[2:])
    noms, a = _dossier(marche, projet)
    assert len(noms) == 3, "la troisième pièce a effacé les deux autres : %s" % noms
    assert len(a.get("pieces") or []) == 3, (
        "le relevé ne porte que sur %d pièce(s) : il est refait sur le dernier "
        "dépôt et non sur le dossier entier"
        % len(a.get("pieces") or []))


def test_une_piece_REDEPOSEE_remplace_la_sienne_et_garde_sa_place(marche, projet):
    """Le geste du rectificatif : l'acheteur republie un CCAP trois jours plus
    tard. Garder les deux ferait relever deux fois des clauses contradictoires ;
    l'ajouter à la fin réordonnerait le dossier à chaque dépôt."""
    _deposer(marche, projet, pieces=DCE, fiche={})
    _deposer(marche, projet,
             pieces=[{"nom": "CCAP.pdf", "texte": "RECTIFICATIF. Pénalités : 1/2000."}])
    noms, _ = _dossier(marche, projet)
    assert noms == [p["nom"] for p in DCE], noms


def test_une_piece_se_RETIRE_sans_perdre_le_dossier(marche, projet):
    """Sans ce geste, corriger un dépôt fautif imposerait de tout effacer puis
    de tout redéposer — c'est-à-dire de perdre ce qu'on ne retrouverait pas."""
    _deposer(marche, projet, pieces=DCE, fiche={})
    r = _deposer(marche, projet, retirer="CCTP.pdf")
    assert r.status_code == 200
    noms, a = _dossier(marche, projet)
    assert noms == ["reglement-de-consultation.pdf", "CCAP.pdf"], noms
    assert len(a["pieces"]) == 2, "le relevé n'a pas suivi le retrait"
    assert _deposer(marche, projet, retirer="JAMAIS-DEPOSE.pdf").status_code == 404


def test_le_remplacement_reste_possible_mais_il_faut_le_DEMANDER(marche, projet):
    _deposer(marche, projet, pieces=DCE, fiche={})
    _deposer(marche, projet, pieces=[{"nom": "SEUL.pdf", "texte": "x"}],
             remplacer=True)
    noms, _ = _dossier(marche, projet)
    assert noms == ["SEUL.pdf"], noms


# ── L'APPORT DU DOSSIER AU REMPLISSAGE, COMPTÉ ───────────────────────────

def test_le_dossier_depose_ALIMENTE_VRAIMENT_les_formulaires_de_l_Etat():
    """« Les pièces déposées servent à remplir » est une affirmation tant qu'on
    ne compte pas. On remplit les quatre formulaires officiels deux fois — sans
    dossier, puis avec — et l'on exige que l'écart existe.

    C'EST LA RÈGLE QUI TIENT LA PROMESSE DE LA PAGE. Un relevé qui cesserait
    d'alimenter le remplissage ne se verrait nulle part ailleurs : les
    documents sortiraient, simplement plus vides."""
    fiche = {"raison_sociale": "CONSEILPREV", "siret": "73282932000074",
             "forme_juridique": "SASU"}
    sans = ao_dc.remplir(fiche=fiche, analyse=None, saisies={})
    avec = ao_dc.remplir(fiche=fiche, analyse=ao_dc.analyser(DCE), saisies={})
    assert avec["etat"]["remplies"] > sans["etat"]["remplies"], (
        "le dossier n'ajoute aucune rubrique remplie : %d contre %d"
        % (avec["etat"]["remplies"], sans["etat"]["remplies"]))
    assert avec["etat"]["non_trouvees"] < sans["etat"]["non_trouvees"]
    maigres = []
    for cle, m in ao_formulaires.MODELES.items():
        vs = len(ao_formulaires.valeurs_pour(sans, m["piece"]))
        va = len(ao_formulaires.valeurs_pour(avec, m["piece"]))
        if va <= vs:
            maigres.append("%s (%d → %d)" % (cle, vs, va))
    assert not maigres, (
        "ces formulaires ne reçoivent RIEN du dossier déposé : "
        + ", ".join(maigres))


def test_les_valeurs_venues_du_dossier_se_PLACENT_dans_le_fichier_officiel():
    """Une valeur fournie et non placée ne sert à rien : le formulaire sort
    avec sa case vide, et personne ne le sait.

    ON COMPARE LES DEUX REMPLISSAGES, on ne fixe pas de seuil. « Au moins cinq
    valeurs placées » était un nombre choisi par moi, que le dossier d'essai
    pouvait franchir ou non selon les champs de la fiche — un seuil arbitraire
    mesure la fixture, pas le produit. Ce qui doit tenir est un ÉCART : chacun
    des quatre formulaires officiels place, grâce au dossier déposé, des cases
    qu'il laissait vides sans lui."""
    fiche = {"raison_sociale": "CONSEILPREV", "siret": "73282932000074"}
    sans = ao_dc.remplir(fiche=fiche, analyse=None, saisies={})
    avec = ao_dc.remplir(fiche=fiche, analyse=ao_dc.analyser(DCE), saisies={})
    for cle, m in ao_formulaires.MODELES.items():
        pose = {}
        for nom, r in (("sans", sans), ("avec", avec)):
            v = ao_formulaires.valeurs_pour(r, m["piece"])
            _o, rap = ao_formulaires.remplir_document(cle, v)
            assert rap["ok"], (cle, rap.get("motif"))
            # UNE VALEUR FOURNIE QUI DISPARAÎT SANS UN MOT est le pire des
            # cas : le formulaire sort, il a l'air complet, et une case est
            # vide. Chacune tombe donc dans l'un des trois sacs du rapport —
            # placée, non placée faute d'emplacement libre, ou SANS ANCRE
            # parce que ce formulaire-là ne demande pas cette valeur (le DC2
            # ne demande ni le SIREN ni la TVA, que la fiche fournit).
            comptees = (len(rap["places"]) + len(rap["non_places"])
                        + len(rap["sans_ancre"]))
            assert comptees == len(v), (
                "%s (%s) : %d valeur(s) fournies, %d comptées — %s disparaît "
                "sans un mot"
                % (cle, nom, len(v), comptees,
                   sorted(set(v) - {x["rubrique"] for x in rap["places"]}
                          - {x["rubrique"] for x in rap["non_places"]}
                          - set(rap["sans_ancre"]))))
            pose[nom] = {x["rubrique"] for x in rap["places"]}
        gagnees = pose["avec"] - pose["sans"]
        assert gagnees, (
            "%s ne place AUCUNE case de plus grâce au dossier déposé : le "
            "relevé ne sert pas au remplissage" % cle)


def test_la_carte_annonce_AVANT_le_choix_ce_qu_elle_produira():
    """Sans cela on coche vingt-trois pièces en croyant recevoir vingt-trois
    formulaires, et l'on découvre après coup que dix-neuf sont des plans."""
    from test_ao_formulaires import _carte_rendue, _rempli
    h = _carte_rendue(_rempli())
    assert h.count('class="ig-ao-pr') == 23, h[:200]
    js = _src("ingenierie-dc.js")
    bloc = js[js.index("function aoProduira("):]
    bloc = bloc[:bloc.index("\n  }")]
    assert "AO_FORMULAIRES.etat.prets" in bloc, (
        "l'annonce ne vient pas de ce que le SERVEUR dit avoir déposé : elle "
        "promettrait un formulaire absent")


def test_l_ecran_montre_ce_qui_est_conserve_et_laisse_en_RETIRER_une():
    js = _src("ingenierie-dc.js")
    bloc = js[js.index("function aoProjetRendre("):]
    bloc = bloc[:bloc.index("\n  }\n")]
    assert "data-retirer=" in bloc, "aucun geste pour retirer une pièce"
    assert "Un dépôt AJOUTE" in bloc, (
        "l'écran ne dit pas que le dépôt ajoute : on croira qu'il remplace, "
        "et c'est ce qu'il faisait")
    ret = js[js.index("function aoProjetRetirer("):]
    ret = ret[:ret.index("\n  }")]
    assert "AO_ANALYSE = null" in ret, (
        "l'analyse à l'écran survivrait au retrait : on remplirait depuis une "
        "pièce qu'on vient d'enlever")


# ══ CE QUE LA PAGE ENVOIE VRAIMENT, ET CE QUE LE DÉPÔT EN FAIT ═══════════
#
# LE DÉFAUT QUE CES RÈGLES TIENNENT, ET POURQUOI AUCUNE AUTRE NE L'A VU.
# Toutes les règles de dépôt ci-dessus postent `{"nom": …, "texte": …}` — la
# forme que `ao_projet.deposer` lit. La PAGE, elle, n'a pas le texte : elle lit
# le fichier dans le navigateur et transmet ses octets en base64 sous
# `contenu`. La route d'analyse décodait et extrayait ; la route de dépôt ne
# lisait que `texte`, absent, et conservait donc des pièces VIDES.
#
# MESURÉ EN NAVIGATEUR avant correction : trois pièces déposées, toutes à
# « 0 o », toutes avec l'empreinte e3b0c44298fc… — le sha256 de la chaîne
# vide. Le dossier était conservé, l'écran l'affichait comme complet, et le
# remplissage automatique des vingt-trois pièces travaillait sur rien.
#
# Les règles étaient vertes parce qu'elles mesuraient la porte du dessous au
# lieu de la charge que le navigateur pousse dans la route — une règle qui
# passe pour une raison sans rapport avec ce qu'elle prétend. Celles-ci
# passent par la ROUTE, avec la forme de la PAGE.

def _b64(texte):
    import base64
    return base64.b64encode(texte.encode("utf-8")).decode("ascii")


SHA_DU_VIDE = ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b"
               "7852b855")


def _comme_la_page(pieces):
    """La charge telle que `aoLire` la construit : le nom, et les octets du
    fichier en base64. Jamais `texte` — la page ne l'a pas.

    L'EXTENSION DEVIENT `.txt`, ET C'EST LA PORTE QUI L'IMPOSE. Transmettre du
    texte brut sous un nom en `.pdf` est refusé par l'inspection structurelle
    — « Le contenu ne correspond pas à l'extension annoncée » — et ce refus est
    juste. Les règles ci-dessus n'y étaient pas soumises parce qu'elles
    passaient le texte en clair, sans jamais ouvrir de fichier : la porte
    n'existait pas pour elles.
    """
    return [{"nom": p["nom"].rsplit(".", 1)[0] + ".txt",
             "contenu": _b64(p["texte"])} for p in pieces]


def _noms_page(pieces):
    return [p["nom"].rsplit(".", 1)[0] + ".txt" for p in pieces]


def test_le_depot_conserve_le_TEXTE_des_pieces_que_la_page_envoie(marche, projet):
    """La règle qui manquait. Elle poste ce que le navigateur poste."""
    r = _deposer(marche, projet, pieces=_comme_la_page(DCE), fiche={})
    assert r.status_code == 200, r.data[:300]
    d = marche.get("/api/datacenter/marche/projet/dossier?projet=" + projet,
                     headers=ORIGINE).get_json()["dossier"]
    vides = [p["nom"] for p in d["pieces"]
             if not p["octets"] or p["empreinte"] == SHA_DU_VIDE]
    assert not vides, (
        "ces pièces ont été conservées VIDES alors que la page a transmis "
        "leur contenu : " + ", ".join(vides))
    # ET LE COMPTE EST LE BON : un décodage partiel passerait le contrôle
    # ci-dessus en ne conservant qu'un octet.
    attendu = [len(p["texte"].encode("utf-8")) for p in DCE]
    assert [p["octets"] for p in d["pieces"]] == attendu, (
        "le texte conservé n'est pas celui transmis : %s au lieu de %s"
        % ([p["octets"] for p in d["pieces"]], attendu))


def test_le_dossier_ainsi_depose_ALIMENTE_le_remplissage_des_vingt_trois(
        marche, projet):
    """LA PROMESSE DE LA PAGE, DE BOUT EN BOUT — par la route, pas par le
    module. « Charger les pièces de la consultation pour remplir
    automatiquement les pièces choisies » n'est tenu que si l'acheteur relevé
    dans le règlement ressort dans un document produit."""
    _deposer(marche, projet, pieces=_comme_la_page(DCE), fiche={})
    d = marche.get("/api/datacenter/marche/projet/dossier?projet=" + projet,
                     headers=ORIGINE).get_json()["dossier"]
    cites = json.dumps((d.get("analyse") or {}).get("pieces") or [],
                       ensure_ascii=False).upper()
    assert "VAL-D'EUROPE" in cites, (
        "l'acheteur nommé dans le règlement déposé n'est cité par aucun relevé "
        "du dossier conservé : celui-ci ne sert donc à rien pour remplir")
    # ET LE RELEVÉ SERT VRAIMENT AU REMPLISSAGE : on repart de l'analyse
    # conservée, exactement comme la page, et on exige que l'écart existe.
    fiche = {"raison_sociale": "CONSEILPREV", "siret": "73282932000074"}
    sans = ao_dc.remplir(fiche=fiche, analyse=None, saisies={})
    avec = ao_dc.remplir(fiche=fiche, analyse=d["analyse"], saisies={})
    assert avec["etat"]["remplies"] > sans["etat"]["remplies"], (
        "l'analyse conservée n'ajoute aucune rubrique remplie : %d contre %d"
        % (avec["etat"]["remplies"], sans["etat"]["remplies"]))


def test_ce_qui_n_a_pas_pu_etre_lu_au_depot_est_NOMME(marche, projet):
    """Un dépôt de trois pièces dont une est illisible ne doit pas se lire
    comme un dépôt de trois. L'écarter en silence ferait croire le dossier
    complet — et c'est précisément l'erreur qu'on vient de corriger."""
    charge = _comme_la_page(DCE[:1]) + [{"nom": "ABIME.pdf", "contenu": "@@@"}]
    r = _deposer(marche, projet, pieces=charge, fiche={})
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    assert "ABIME.pdf" in json.dumps(j.get("ignores") or [], ensure_ascii=False), (
        "la pièce illisible n'est pas nommée dans la réponse : %r"
        % (j.get("ignores"),))
    noms, _ = _dossier(marche, projet)
    assert noms == _noms_page(DCE[:1]), noms


def test_l_analyse_et_le_depot_lisent_par_la_MEME_porte(marche, projet):
    """DEUX EXTRACTIONS, C'EST UNE DIVERGENCE EN ATTENTE. Celle qu'on vient de
    payer : l'analyse décodait le base64, le dépôt non. La règle exige que le
    même contenu illisible soit écarté par les deux routes avec le MÊME motif —
    ce qui n'est vrai que s'il n'y a qu'une porte."""
    charge = [{"nom": "ABIME.pdf", "contenu": "@@@"}]
    a = marche.post("/api/datacenter/marche/analyser",
                    json={"documents": charge}, headers=ORIGINE).get_json()
    d = _deposer(marche, projet,
                 pieces=_comme_la_page(DCE[:1]) + charge).get_json()
    motif_a = [x["pourquoi"] for x in (a.get("ignores") or [])
               if x["fichier"] == "ABIME.pdf"]
    motif_d = [x["pourquoi"] for x in (d.get("ignores") or [])
               if x["fichier"] == "ABIME.pdf"]
    assert motif_a and motif_a == motif_d, (
        "les deux routes n'écartent pas la même pièce pour la même raison — "
        "elles ne partagent donc pas leur extraction : analyse %r, dépôt %r"
        % (motif_a, motif_d))


def test_la_page_envoie_la_forme_QUE_LE_DEPOT_LIT(marche, projet):
    """LA RÈGLE STRUCTURELLE. Les deux précédentes tiendraient encore si la
    page se mettait à envoyer un troisième nom de champ. Celle-ci lit les clés
    que `aoLire` pose réellement dans les objets que `aoProjetDeposer` envoie,
    et exige que la route sache en tirer le texte — quel que soit leur nom."""
    src = _js_source("aoLire")
    # LES CHAMPS DU SUCCÈS, pas ceux de l'échec : `aoLire` rend `{nom, erreur}`
    # quand la lecture rate, et c'est l'AUTRE littéral qui devient AO_DOCS.
    litteraux = [set(re.findall(r"(\w+)\s*:", bloc))
                 for bloc in re.findall(r"ok\(\{(.*?)\}\)", src, re.S)]
    succes = [c for c in litteraux if "erreur" not in c]
    assert len(succes) == 1 and len(succes[0]) == 2, (
        "aoLire ne pose plus exactement deux champs au succès : %r — la règle "
        "ne mesure donc plus la charge réelle et doit être reprise" % (litteraux,))
    cles = sorted(succes[0])
    nom_cle = "nom" if "nom" in cles else cles[0]
    contenu_cle = [c for c in cles if c != nom_cle][0]
    charge = [{nom_cle: p["nom"].rsplit(".", 1)[0] + ".txt",
               contenu_cle: _b64(p["texte"])} for p in DCE]
    r = _deposer(marche, projet, pieces=charge, fiche={})
    assert r.status_code == 200, r.data[:300]
    d = marche.get("/api/datacenter/marche/projet/dossier?projet=" + projet,
                     headers=ORIGINE).get_json()["dossier"]
    assert d and all(p["octets"] for p in d["pieces"]), (
        "la route ne sait pas lire les champs %r que la page pose : le dossier "
        "conservé est vide" % (cles,))


def test_le_depot_passe_par_l_ANTIVIRUS_comme_l_analyse(marche, projet):
    """CE QUE LA PORTE PARTAGÉE FAIT GAGNER, et qu'il faut donc tenir. Avant,
    le dépôt ne recevait que du texte : aucun fichier n'était ouvert, et
    l'antivirus n'avait rien à inspecter. Maintenant que le dépôt décode et
    extrait, il ouvre des fichiers — exactement ce contre quoi cette porte
    existe. Un contenu qui ment sur son extension doit être refusé ICI aussi.
    """
    charge = [{"nom": "piege.pdf", "contenu": _b64("Ceci n'est pas un PDF.")}]
    j = _deposer(marche, projet, pieces=charge, fiche={}).get_json()
    motifs = " ".join(x["pourquoi"] for x in (j.get("ignores") or []))
    assert "extension" in motifs, (
        "un contenu qui ment sur son extension entre au dossier sans que "
        "l'inspection structurelle l'ait vu : %r" % (j.get("ignores"),))
    noms, _ = _dossier(marche, projet)
    assert not noms, "la pièce refusée a tout de même été conservée : %s" % noms


def test_la_reprise_annonce_une_DATE_et_non_un_horodatage():
    """MESURÉ À L'ÉCRAN : « Dossier conservé repris : 3 pièce(s) identifiée(s),
    relevées le 1788728142 ». La date était fabriquée en découpant les dix
    premiers chiffres de l'horodatage. La règle exécute la phrase sur un
    horodatage connu et exige une date lisible — chercher le mot « aoJour »
    dans la source constaterait un appel sans jamais lire son résultat."""
    src = _js_source("aoJour", "aoRepriseMsg")
    quand = 1_788_728_142_000                    # 6 septembre 2026
    sortie = subprocess.run(
        ["node", "-e", src + """
        var d = {maj_le: %d, analyse: {pieces: [1, 2, 3]}};
        console.log(aoRepriseMsg(d));
        """ % quand],
        capture_output=True, text=True, timeout=60)
    assert sortie.returncode == 0, sortie.stderr[-600:]
    dit = sortie.stdout.strip()
    assert "3 pièce(s)" in dit, dit
    assert "2026" in dit and "1788728142" not in dit, (
        "la reprise affiche l'horodatage brut au lieu d'une date : %r" % dit)


# ══ LE TRANSPORT : CE QUI PASSE VRAIMENT PAR LA ROUTE ════════════════════
#
# LE DÉFAUT MESURÉ. Le site annonce 20 Mo par fichier. Les deux routes d'appel
# d'offres — analyser, et conserver — n'étaient pas déclarées dans
# `_LARGE_BODY_PATHS` et retombaient donc sur le plafond commun de 512 Ko de
# corps JSON, soit, l'inflation du base64 déduite, environ 380 Ko de fichier
# réel — POUR L'ENSEMBLE des pièces d'un même envoi. Mesuré en navigateur : un
# projet de marché de 818 Ko rend « Contenu trop volumineux » en 1,2 s ; le
# même dossier en 28 Ko passe.
#
# C'EST LE MÊME DÉFAUT QUE CELUI DÉJÀ PAYÉ POUR `/api/datacenter/depot`, dont
# le commentaire de `_LARGE_BODY_PATHS` porte encore le récit. Les routes
# d'appel d'offres ont été écrites après, et n'ont jamais rejoint la liste.
#
# CES RÈGLES POSTENT UN CORPS RÉEL. Vérifier que la route figure dans un
# ensemble constaterait une appartenance ; ce qu'on veut savoir, c'est ce qui
# franchit la porte.

import app as _app                                                 # noqa: E402

CORPS_PETIT = 512 * 1024                       # l'ancien plafond commun


def _piece_de(octets):
    """Une pièce dont le CORPS transmis dépasse `octets`, base64 compris."""
    return {"nom": "gros.txt", "contenu": _b64("A" * int(octets * 3 / 4))}


def test_une_piece_PLUS_GROSSE_QUE_L_ANCIEN_PLAFOND_est_acceptee(marche, projet):
    """La règle qui manquait, du côté qui compte : le dépôt."""
    r = _deposer(marche, projet, pieces=[_piece_de(CORPS_PETIT * 2)], fiche={})
    assert r.status_code != 413, (
        "le dossier marché refuse encore un envoi d'environ %d Ko : les pièces "
        "d'une consultation ne passent donc pas la porte"
        % (CORPS_PETIT * 2 // 1024))
    assert r.status_code == 200, r.data[:200]
    d = marche.get("/api/datacenter/marche/projet/dossier?projet=" + projet,
                     headers=ORIGINE).get_json()["dossier"]
    assert d["pieces"] and d["pieces"][0]["octets"] > 0


def test_l_analyse_accepte_le_MEME_volume_que_le_depot(marche):
    """DEUX PLAFONDS DIFFÉRENTS SUR LE MÊME GESTE SERAIT PIRE QUE LE DÉFAUT.
    On analyse puis on conserve les mêmes fichiers ; un dossier qui franchit la
    première porte et bute sur la seconde ne se comprend pas."""
    r = marche.post("/api/datacenter/marche/analyser",
                    json={"documents": [_piece_de(CORPS_PETIT * 2)]},
                    headers=ORIGINE)
    assert r.status_code != 413, (
        "l'analyse refuse un volume que le dépôt accepte : les deux portes du "
        "même geste n'ont pas le même plafond")


def test_le_plafond_de_transport_TIENT_ce_que_le_site_ANNONCE():
    """L'ÉCART ENTRE CE QUI EST PROMIS ET CE QUI PASSE EST LE DÉFAUT LUI-MÊME.
    Le site annonce une taille maximale par fichier (`DEPOT_MAX_MB`, servie à
    la page par l'état du dépôt). Si le transport en une requête ne la porte
    pas, l'annonce est fausse — et c'est exactement ce qui s'est produit."""
    import antivirus
    porte = _app.RAG_UPLOAD_MAX
    annonce = antivirus.MAX_OCTETS * antivirus.SURCOUT_BASE64
    assert annonce <= porte, (
        "le site annonce %d Mo par fichier mais n'accepte que %d Mo de corps : "
        "les plus gros échoueront au transport"
        % (antivirus.MAX_OCTETS // 1048576, porte // 1048576))
    for route in ("/api/datacenter/marche/analyser",
                  "/api/datacenter/marche/projet/dossier"):
        assert route in _app._LARGE_BODY_PATHS, (
            "%s reçoit des fichiers en base64 mais reste au plafond commun de "
            "%d Ko" % (route, _app.SMALL_BODY_MAX // 1024))


def test_le_refus_de_transport_NOMME_le_volume_qui_a_echoue():
    """« Analyse indisponible. » couvrait le délai dépassé, la coupure réseau
    et le refus du serveur : trois pannes, trois gestes, un seul mot. La règle
    exécute la phrase sur chacune et exige qu'elles diffèrent, et que le volume
    y figure — c'est lui qui dit s'il faut alléger ou réessayer."""
    src = _js_source("fr", "aoOctets", "aoPanne")
    sortie = subprocess.run(
        ["node", "-e", "var DELAI_LONG = 130000;\n" + src + """
        var o = 5 * 1024 * 1024;
        var d = new Error("x"); d.name = "DelaiDepasse"; d.delai = 130000;
        var s = new Error("x"); s.name = "SessionEteinte";
        console.log(JSON.stringify([aoPanne(d, o), aoPanne(s, o),
                                    aoPanne(new Error("réseau"), o),
                                    aoPanne(new Error("x"), 1.5 * 1048576)]));
        """], capture_output=True, text=True, timeout=60)
    assert sortie.returncode == 0, sortie.stderr[-600:]
    delai, session, autre, aoPanne_1_5 = json.loads(sortie.stdout)
    assert len({delai, session, autre}) == 3, (
        "les trois pannes rendent le même message : %r" % [delai, session, autre])
    assert "130" in delai and "5 Mo" in delai, delai
    assert "session" in session.lower(), session
    assert "5 Mo" in autre, autre
    # LA TAILLE EST ÉCRITE À LA FRANÇAISE, comme tout le reste de la page.
    assert "1,50 Mo" in aoPanne_1_5, aoPanne_1_5


def test_l_analyse_et_le_depot_prennent_le_DELAI_LONG():
    """DOUZE SECONDES ÉTAIT UN BUDGET D'APERÇU. Ces deux appels téléversent
    plusieurs mégaoctets, les passent à l'antivirus, en extraient le texte PDF
    par PDF, puis refont dix-sept relevés. La règle lit le délai passé à
    `demander` dans chacun des deux, au lieu de constater qu'un mot figure
    quelque part dans le fichier."""
    src = _src("ingenierie-dc.js")
    for fonction, adresse in (("aoAnalyser", "/api/datacenter/marche/analyser"),
                              ("aoProjetDeposer",
                               "/api/datacenter/marche/projet/dossier")):
        bloc = _js_source(fonction)
        assert adresse in bloc, "%s n'appelle plus %s" % (fonction, adresse)
        # le troisième argument de `demander`, tel qu'il est écrit ici
        m = re.search(r"\}\s*,\s*(DELAI_\w+)\s*\)", bloc)
        assert m and m.group(1) == "DELAI_LONG", (
            "%s laisse à %s le délai %s : un transfert de plusieurs mégaoctets "
            "sera coupé en plein vol"
            % (fonction, adresse, m.group(1) if m else "par défaut (12 s)"))
    assert "var DELAI_LONG = 130000;" in src


def test_un_document_TROP_LONG_le_dit_au_lieu_d_etre_coupe_en_silence(
        marche, projet):
    """LE DÉFAUT MESURÉ SUR UN VRAI DOCUMENT. Un projet de marché de 120 pages
    porte 762 460 caractères ; le coffre en conserve 400 000. La coupe se
    faisait en amont et sans un mot : le dossier s'affichait conservé, les
    relevés tournaient sur un texte qui s'arrête au milieu, et 48 % des clauses
    n'existaient plus pour personne.

    LE PLAFOND RESTE — il protège le coffre et le releveur. Ce qui change est
    qu'il se voit."""
    long = "A" * (_app.MARCHE_TEXTE_MAX + 50_000)
    r = _deposer(marche, projet,
                 pieces=[{"nom": "marche.txt", "contenu": _b64(long)}], fiche={})
    assert r.status_code == 200, r.data[:200]
    dits = json.dumps(r.get_json().get("ignores") or [], ensure_ascii=False)
    assert "marche.txt" in dits, (
        "la pièce écourtée n'est pas nommée dans la réponse : %s" % dits[:300])
    assert str(len(long)) in dits and str(_app.MARCHE_TEXTE_MAX) in dits, (
        "le nombre de caractères gardés et le total ne sont pas dits : %s"
        % dits[:300])
    # ET LA PIÈCE EST BIEN CONSERVÉE, écourtée mais présente.
    d = marche.get("/api/datacenter/marche/projet/dossier?projet=" + projet,
                     headers=ORIGINE).get_json()["dossier"]
    assert d["pieces"][0]["octets"] == _app.MARCHE_TEXTE_MAX


def test_la_coupe_et_le_REFUS_du_coffre_parlent_du_meme_plafond():
    """DEUX CHIFFRES POUR LA MÊME LIMITE EST UNE DIVERGENCE EN ATTENTE. La
    route coupait à 400 000 écrit en dur pendant que `ao_projet` refusait à
    `MAX_OCTETS_PIECE` : le refus nommé du module ne se déclenchait jamais,
    puisque le texte lui arrivait déjà coupé pile à la limite."""
    import ao_projet as _p
    assert _app.MARCHE_TEXTE_MAX == _p.MAX_OCTETS_PIECE, (
        "la route coupe à %d et le coffre refuse à %d : personne ne peut dire "
        "laquelle des deux s'applique"
        % (_app.MARCHE_TEXTE_MAX, _p.MAX_OCTETS_PIECE))


def test_l_avertissement_du_depot_est_pose_APRES_le_re_rendu():
    """MESURÉ EN NAVIGATEUR : la pièce était bel et bien écourtée, et la ligne
    de message restait vide. `aoProjetEtat` reconstruit tout le bloc,
    `#ig-cons-msg` compris ; écrire dedans avant elle revient à écrire sur un
    élément qu'elle va remplacer.

    LA RÈGLE MESURE L'IMBRICATION, pas la présence des deux appels : les deux
    étaient là avant la correction, dans le mauvais ordre."""
    bloc = _js_source("aoProjetDeposer")
    i = bloc.find("aoProjetEtat()")
    assert i > 0, "aoProjetDeposer ne rafraîchit plus l'état"
    # le corps du .then qui suit aoProjetEtat(), par comptage d'accolades
    j = bloc.index("{", bloc.index(".then", i))
    n, fin = 0, None
    for k in range(j, len(bloc)):
        if bloc[k] == "{":
            n += 1
        elif bloc[k] == "}":
            n -= 1
            if n == 0:
                fin = k
                break
    assert fin, "le .then qui suit aoProjetEtat() n'est pas refermé"
    dedans = bloc[j:fin]
    assert "aoProjetMsg" in dedans, (
        "l'avertissement du dépôt est posé HORS du .then qui suit "
        "aoProjetEtat() : le re-rendu l'effacera avant qu'il soit lu")


# ══ LE REMPLISSAGE SANS SAISIE ═══════════════════════════════════════════
#
# CE QUI A ÉTÉ MESURÉ, ET QUI DONNE SON OBJET À CES RÈGLES. Les vingt-trois
# pièces comptent soixante-quatre rubriques. Réparties par ORIGINE :
#
#     fiche         38   l'identité du candidat — 20 champs
#     saisie        26   des choix propres à CETTE offre (lot, groupement…)
#     consultation  15   l'acheteur, l'objet, la référence, les lots
#     declaration    6   les déclarations sur l'honneur
#     calcul         2   SIREN et TVA, déduits du SIRET
#
# Et ce que chaque source apporte, compté sur un dossier réel :
#
#                                     remplies   à saisir   non trouvées
#     rien du tout                           0         47             12
#     les pièces seules                     11         47              1
#     le dossier d'entreprise seul          19         28             12
#     LES DEUX                              30         28              1
#
# TRENTE RUBRIQUES SUR SOIXANTE-QUATRE SANS UNE SEULE FRAPPE. Les vingt-huit
# qui restent sont des choix propres à cette offre, et les six déclarations ne
# se pré-remplissent JAMAIS : leur fausseté est pénalement sanctionnée.

def test_le_dossier_d_entreprise_remplit_la_fiche_SANS_AUCUNE_SAISIE(marche):
    """LA RÈGLE CENTRALE. Une requête qui n'envoie RIEN doit tout de même
    ressortir avec l'identité du cabinet placée dans les pièces."""
    import dossier_entreprise as _de
    j = marche.post("/api/datacenter/marche/remplir", json={},
                    headers=ORIGINE).get_json()
    e = j["remplissage"]["etat"]
    socle = _de.fiche_candidat()["fiche"]
    assert e["remplies"] >= len(socle), (
        "une requête vide ne remplit que %d rubrique(s) alors que le dossier "
        "d'entreprise en fournit %d" % (e["remplies"], len(socle)))
    # ON MESURE LES RUBRIQUES REMPLIES, pas les clés de la fiche.
    #
    # POURQUOI. Les rubriques portent LEURS noms — `candidat`, `titulaire`,
    # `signataire`, `contact` — et non ceux des champs de la fiche : la
    # correspondance est faite par le moteur. Comparer les deux jeux de clés
    # mesurerait la nomenclature, pas le report.
    #
    # ONZE RUBRIQUES DISTINCTES REÇOIVENT LE DOSSIER, mesuré : adresse,
    # candidat, capital, contact, forme, qualite, signataire, titulaire,
    # titulaire_adresse, titulaire_courriel, titulaire_forme. Les autres
    # attendent les dix champs que le dossier ne porte pas.
    remplies = {l.get("cle") for p in j["remplissage"]["pieces"]
                for l in p["rubriques"]
                if l.get("source") == "fiche" and l.get("valeur")}
    assert len(remplies) >= 11, (
        "le dossier d'entreprise ne remplit plus que %d rubrique(s) "
        "distincte(s) : %s" % (len(remplies), sorted(remplies)))
    # ET LES VALEURS SONT BIEN LES SIENNES, pas des chaînes quelconques.
    valeurs = {l["valeur"] for p in j["remplissage"]["pieces"]
               for l in p["rubriques"] if l.get("valeur")}
    # PRÉSENCE, PAS ÉGALITÉ : une rubrique peut COMPOSER plusieurs champs —
    # l'adresse en porte trois, le contact deux. Exiger la valeur seule ferait
    # échouer la règle sur la composition, qui est précisément ce qu'on veut.
    tout = " § ".join(str(v) for v in valeurs)
    for cle in ("raison_sociale", "capital", "representant_nom", "courriel",
                "code_postal", "ville", "telephone"):
        assert socle[cle] in tout, (
            "« %s » du dossier d'entreprise n'atteint aucune pièce" % cle)
    # ET L'ADRESSE EST ÉCRITE À L'USAGE POSTAL : « rue, code postal ville ».
    # « 75015, Paris » n'est l'usage nulle part, et un DC1 se lit.
    attendu = "%s, %s %s" % (socle["adresse"], socle["code_postal"],
                             socle["ville"])
    assert attendu in tout, (
        "l'adresse n'est pas composée à l'usage postal : %r attendu" % attendu)


def test_ce_que_le_dossier_NE_PEUT_PAS_fournir_est_NOMME():
    """DIX CHAMPS NE SONT PAS PORTÉS par les documents d'origine — le SIRET y
    figure explicitement comme absent. Les inventer produirait un DC1 faux ;
    les taire ferait croire le formulaire complet. Chacun ressort donc avec
    l'endroit où le trouver, comme les attestations le font déjà.

    LE TOTAL N'EST PLUS ÉPINGLÉ À VINGT, ET C'EST UNE CORRECTION. Ce nombre
    ne mesurait rien d'autre que « personne n'a ajouté de champ » : le jour où
    le SIREN et la TVA — détenus par l'identité et jusque-là perdus — ont
    rejoint la fiche, la règle est tombée alors que le dossier s'AMÉLIORAIT.
    Ce qui compte est l'invariant : tout champ attendu est soit fourni, soit
    déclaré manquant, et aucun ne disparaît entre les deux. Le plancher
    garantit que la fiche ne se vide pas."""
    import dossier_entreprise as _de
    r = _de.fiche_candidat()
    assert r["fournis"] + len(r["manques"]) == r["attendus"], r
    assert r["attendus"] >= 20, (
        "la fiche candidat a maigri : %d champs attendus" % r["attendus"])
    assert r["manques"], "le dossier prétend tout fournir"
    nus = [m["cle"] for m in r["manques"]
           if len((m.get("ou_trouver") or "").strip()) < 25]
    assert not nus, (
        "ces champs manquants ne disent pas où les trouver : %s" % nus)
    # ET LE SIRET EN FAIT PARTIE, nommément : c'est le cas que les documents
    # d'origine signalent eux-mêmes.
    assert "siret" in [m["cle"] for m in r["manques"]]


def test_les_pieces_et_le_dossier_s_ADDITIONNENT():
    """LE GAIN EST MESURÉ, PAS AFFIRMÉ. Chacune des deux sources apporte, et
    les deux ensemble apportent plus que chacune seule — sans quoi l'une
    écraserait l'autre."""
    import dossier_entreprise as _de
    a = ao_dc.analyser(DCE)
    f = _de.fiche_candidat()["fiche"]
    rien = ao_dc.remplir(fiche={}, analyse=None, saisies={})["etat"]["remplies"]
    pieces = ao_dc.remplir(fiche={}, analyse=a, saisies={})["etat"]["remplies"]
    dossier = ao_dc.remplir(fiche=f, analyse=None, saisies={})["etat"]["remplies"]
    deux = ao_dc.remplir(fiche=f, analyse=a, saisies={})["etat"]["remplies"]
    assert rien == 0, rien
    assert pieces > 0 and dossier > 0, (pieces, dossier)
    assert deux > pieces and deux > dossier, (
        "les deux sources ne s'additionnent pas : pièces %d, dossier %d, "
        "ensemble %d" % (pieces, dossier, deux))


def test_les_six_declarations_ne_se_pre_remplissent_JAMAIS():
    """LA LIGNE QUE L'AUTOMATISATION NE FRANCHIT PAS. Une case cochée par un
    programme est une déclaration que personne n'a faite, et sa fausseté est
    pénalement sanctionnée. Le socle du dossier d'entreprise ne doit rien y
    changer."""
    import dossier_entreprise as _de
    r = ao_dc.remplir(fiche=_de.fiche_candidat()["fiche"],
                      analyse=ao_dc.analyser(DCE), saisies={})
    remplies = [l["libelle"] for p in r["pieces"] for l in p["rubriques"]
                if l.get("source") == "declaration" and l.get("valeur")]
    assert not remplies, (
        "des déclarations sur l'honneur sont pré-remplies : %s" % remplies)


def test_les_documents_du_cabinet_portent_l_EN_TETE_et_les_formulaires_NON():
    """LES DEUX MOITIÉS DE LA MÊME RÈGLE, et la seconde compte autant.

    Une note ou une lettre écrite par CONSEILPREV doit sortir sur son papier —
    sinon il faut la recomposer avant de la joindre. Un formulaire de l'État,
    lui, ne doit JAMAIS en porter : ce qui sort pour lui EST le fichier du
    ministère, et un bandeau d'entreprise en ferait un fac-similé, refusé à
    l'ouverture des plis."""
    import dossier_entreprise as _de
    bandeau = _de.PAPIER_ENTETE["bandeau"]
    r = ao_dc.remplir(fiche=_de.fiche_candidat()["fiche"],
                      analyse=ao_dc.analyser(DCE), saisies={})
    officiels = sorted(MODELES)
    nus, coiffes = [], []
    for p in r["pieces"]:
        md = ao_dc.markdown_piece(r, p["cle"], officiels) or ""
        voie = ao_dc.production(p, officiels)
        if voie == "formulaire_officiel":
            if bandeau in md:
                coiffes.append(p["cle"])
        elif bandeau not in md:
            nus.append(p["cle"])
    assert not nus, (
        "ces documents du cabinet sortent sans en-tête : %s" % nus)
    assert not coiffes, (
        "ces formulaires de l'État portent un bandeau d'entreprise — ce sont "
        "des fac-similés : %s" % coiffes)
    # LE TÉMOIN : l'en-tête porte bien la signature et le pied de page.
    md = ao_dc.markdown_piece(r, "conventions", officiels) or ""
    assert _de.IDENTITE["representant_nom"] in md, "l'en-tête ne signe pas"
    assert _de.IDENTITE["siren"] in md, "le pied de page perd les mentions"


def test_ce_que_l_ECRAN_envoie_l_emporte_sur_le_dossier(marche):
    """L'ORDRE DE LA FUSION, MESURÉ DANS LE BON SENS.

    Le dossier fournit le socle ; une valeur transmise par l'écran l'emporte,
    parce qu'elle est plus récente et parce qu'une consultation peut demander
    une variante — un établissement secondaire, un autre signataire. L'inverse
    rendrait toute correction impossible, et une règle qui ne mesure que la
    non-persistance ne le voit pas : dans les deux sens, la valeur envoyée a
    disparu au second appel."""
    import dossier_entreprise as _de
    socle = _de.fiche_candidat()["fiche"]["raison_sociale"]
    autre = "CONSEILPREV — ÉTABLISSEMENT DE LYON"
    assert autre != socle
    j = marche.post("/api/datacenter/marche/remplir",
                    json={"fiche": {"raison_sociale": autre}},
                    headers=ORIGINE).get_json()
    valeurs = {l["valeur"] for p in j["remplissage"]["pieces"]
               for l in p["rubriques"] if l.get("valeur")}
    assert autre in valeurs, (
        "la valeur envoyée par l'écran n'atteint pas les pièces : le dossier "
        "d'entreprise l'écrase, et aucune correction n'est possible")
    assert socle not in valeurs, (
        "les deux valeurs coexistent : le formulaire porterait deux "
        "dénominations différentes")


def test_une_adresse_qui_ne_se_decoupe_pas_est_REFUSEE_pas_devinee():
    """UN CODE POSTAL INVENTÉ NE SE VOIT PAS, et c'est ce qui le rend
    dangereux : il part dans un DC1 et personne ne le relit. Une adresse qui
    ne se laisse pas découper doit donc rendre trois champs vides — qui
    ressortent alors comme manquants, ce qui se corrige."""
    import dossier_entreprise as _de
    for brut in ("19 rue Auguste Chabrières, 75015 Paris",):
        assert _de._scinder_adresse(brut) == ("19 rue Auguste Chabrières",
                                              "75015", "Paris"), brut
    for brut in ("", None, "Chez Untel", "19 rue X 75015 Paris",
                 "19 rue X, Paris"):
        assert _de._scinder_adresse(brut) == (None, None, None), (
            "« %s » a été découpée alors qu'elle n'en porte pas les repères : "
            "%r" % (brut, _de._scinder_adresse(brut)))
    # ET LE REFUS SE VOIT DANS LA FICHE : les trois champs y sont manquants.
    r = _de.fiche_candidat(dict(_de.IDENTITE, adresse="Chez Untel"))
    manquants = {m["cle"] for m in r["manques"]}
    for c in ("adresse", "code_postal", "ville"):
        assert c in manquants, (
            "« %s » ne ressort pas comme manquant : une valeur devinée "
            "passerait pour une réponse" % c)


def test_une_composition_incomplete_SAUTE_le_manquant_et_le_DIT():
    """UN POINT D'INTERROGATION DANS UN DC1 SE LIT COMME UNE RÉPONSE.

    Une rubrique qui compose trois champs et n'en reçoit que deux doit rendre
    les deux — « 19 rue X, 75015 » —, jamais « 19 rue X, 75015, ? ». Et elle
    doit DIRE lequel manque : la valeur est là, donc la pièce se dirait
    complète, et personne ne relit une case déjà remplie."""
    import dossier_entreprise as _de
    partielle = dict(_de.fiche_candidat()["fiche"])
    partielle.pop("ville", None)
    r = ao_dc.remplir(fiche=partielle, analyse=None, saisies={})
    lignes = [l for p in r["pieces"] for l in p["rubriques"]
              if l.get("cle") == "adresse"]
    assert lignes, "la rubrique adresse a disparu"
    l = lignes[0]
    assert l["valeur"] == "%s, %s" % (partielle["adresse"],
                                      partielle["code_postal"]), l["valeur"]
    assert "?" not in l["valeur"], (
        "un champ manquant a été remplacé par un signe : %r" % l["valeur"])
    assert "Ville" in (l.get("message") or ""), (
        "la rubrique ne dit pas quel champ lui manque : %r" % l.get("message"))


def test_une_valeur_DETENUE_que_le_formulaire_n_offre_pas_d_ecrire_est_NOMMEE(marche):
    """CE QU'ON A, QUI EST JUSTE, ET QUI N'A PAS DE CASE.

    LE DÉFAUT MESURÉ. Le DC1 recevait cinq valeurs et n'en écrivait que deux ;
    l'en-tête annonçait « 2 valeur(s) portée(s) » et se taisait sur les trois
    autres. Ce n'est ni `non_places` — le modèle n'a AUCUN emplacement pour
    elles —, ni `reste` — elles ne manquent pas, on les détient. Le module les
    calcule (`sans_ancre`) précisément pour qu'on les dise ; la route les
    jetait avant la page.

    POURQUOI CELA COMPTE. « 2 portées » sur un formulaire qui ne peut pas
    faire mieux se lit comme « aussi rempli que possible ». Trois lignes
    restaient à recopier à la main, et rien ne le disait.

    LA RÈGLE COMPARE AU MODULE, ELLE NE RECOPIE PAS UNE LISTE. Écrire ici
    « DC1 doit dire forme, signataire, qualite » ferait une seconde vérité qui
    dériverait de la première au premier modèle mis à jour.
    """
    par_cle = {p["cle"]: p for p in _pieces()}
    r_module = ao_dc.remplir(fiche=_socle(), analyse=None, saisies={})
    muets, vus = [], 0
    for modele, m in ao_formulaires.MODELES.items():
        cle = m["piece"]
        assert cle in par_cle, (modele, cle)
        valeurs = ao_formulaires.valeurs_pour(r_module, cle)
        _blob, rap = ao_formulaires.remplir_document(modele, valeurs)
        attendu = list(rap.get("sans_ancre") or [])
        d = json.loads(_produire(marche, cle).headers["X-Piece"])
        dit = list(d.get("sans_ancre") or [])
        if attendu:
            vus += 1
        if sorted(dit) != sorted(attendu):
            muets.append("%s : l'en-tête dit %s, le modèle en détient %s"
                         % (cle, dit or "rien", attendu or "aucune"))
    assert not muets, " · ".join(muets)
    # ET IL Y EN A BIEN, sans quoi la règle passerait sur quatre listes vides.
    # MESURÉ : DC1, DC2 et ATTRI1 en détiennent ; le DC4 place tout ce qu'il a.
    assert vus >= 3, (
        "aucun formulaire ne détient plus de valeurs qu'il n'en place : la "
        "règle ne mesure plus rien (%d)" % vus)


def test_les_DEUX_ecrans_disent_ce_qui_reste_a_recopier_a_la_main():
    """LA MESURE NE SERT À RIEN SI ELLE S'ARRÊTE À L'EN-TÊTE HTTP.

    Deux chemins produisent un formulaire officiel — le bouton par formulaire
    (en-tête `X-Remplissage`) et la production en lot (en-tête `X-Piece`) — et
    ils dessinent deux endroits différents. Un seul des deux corrigé laisserait
    la moitié des utilisateurs devant « 2 valeur(s) portée(s) ».

    CE QUE CETTE RÈGLE-CI FAIT, ET CE QU'ELLE NE FAIT PAS. Elle LIT LA SOURCE
    de la page : elle tient qu'aucun des deux écrans ne perde la mention. Elle
    ne prouve pas que le texte s'affiche — c'est la recette navigateur qui le
    voit, et ce sont les deux règles d'en-tête qui mesurent que les VALEURS
    dites sont bien celles que le modèle détient. Le dire ici évite de la
    croire plus forte qu'elle n'est."""
    js = _src("ingenierie-dc.js")
    for ancre, quoi in ((".sans_ancre", "l'en-tête du bouton par formulaire"),
                        ("d.sans_ancre", "la carte de la production en lot")):
        assert ancre in js, "%s ne lit pas la liste" % quoi
    assert js.count("recopier à la main") >= 2, (
        "les deux écrans ne disent pas ce qui reste à recopier : %d mention(s)"
        % js.count("recopier à la main"))


def test_le_bouton_PAR_FORMULAIRE_dit_lui_aussi_ce_qui_reste_a_recopier(marche):
    """L'AUTRE CHEMIN, ET IL PORTE SON PROPRE EN-TÊTE.

    Deux routes produisent un formulaire officiel : /marche/piece (en-tête
    `X-Piece`, la production en lot) et /marche/formulaire (en-tête
    `X-Remplissage`, le bouton par formulaire). Corriger la première seule
    laisserait la seconde muette — et c'est la seconde que l'on clique quand
    on ne veut qu'un DC1.

    ON MESURE L'EN-TÊTE RENDU, pas la présence de la clé dans la source :
    une clé écrite et jamais servie ne dirait rien à personne."""
    r_module = ao_dc.remplir(fiche=_socle(), analyse=None, saisies={})
    muets = []
    for modele, m in ao_formulaires.MODELES.items():
        valeurs = ao_formulaires.valeurs_pour(r_module, m["piece"])
        _blob, rap = ao_formulaires.remplir_document(modele, valeurs)
        attendu = sorted(rap.get("sans_ancre") or [])
        rep = marche.post("/api/datacenter/marche/formulaire",
                          json={"modele": modele, "fiche": FICHE},
                          headers=ORIGINE)
        assert rep.status_code == 200, (modele, rep.status_code)
        d = json.loads(rep.headers["X-Remplissage"])
        if sorted(d.get("sans_ancre") or []) != attendu:
            muets.append("%s : l'en-tête dit %s, le modèle en détient %s"
                         % (modele, sorted(d.get("sans_ancre") or []) or "rien",
                            attendu or "aucune"))
    assert not muets, " · ".join(muets)


# ═══════════════════════════════════════════════════════════════════════════
#  CE QUE LE RÈGLEMENT DE CONSULTATION VERSE DANS LES CADRES DU DC1 ET DU DC2
# ═══════════════════════════════════════════════════════════════════════════
#
# CE QUI A DÉCLENCHÉ CETTE SECTION. Un dossier réel, analysé de bout en bout,
# a montré DEUX valeurs fausses écrites dans les formulaires du ministère —
# pas absentes : FAUSSES, et donc recopiées telles quelles par qui remplit.

RC_LIGNES = """RÈGLEMENT DE LA CONSULTATION

Pouvoir adjudicateur : Communauté d'agglomération de l'Essai
SIRET : 24780064500147

Objet du marché : construction et exploitation d'un centre de données
Procédure : procédure formalisée — appel d'offres ouvert
Allotissement : le marché est alloti en 3 lots.
Référence de la consultation : 2026-C-00396
"""


def _releve(cle, texte=RC_LIGNES):
    an = ao_dc.analyser([{"nom": "01_RC.pdf", "texte": texte}])
    props = ao_dc._index_releves(an).get(cle) or []
    return props[0]["valeur"] if props else None


def test_l_objet_s_arrete_au_champ_suivant_et_PAS_au_premier_point():
    """DEUX FAUTES SYMÉTRIQUES, ET IL FAUT LES ÉVITER TOUTES DEUX.

    S'arrêter au premier saut de ligne tronquerait un objet coupé par la mise
    en page d'un PDF — c'est pour cela que la capture les franchissait. Mais
    les franchir TOUS versait la ligne suivante dans la case : mesuré sur un
    règlement écrit une ligne par rubrique, le cadre B du DC1 portait
    « construction et exploitation d'un centre de données Procédure :
    procédure formalisée ». L'objet ET la procédure.

    ON MESURE LES DEUX CAS, pas seulement celui qu'on vient de corriger."""
    v = _releve("objet")
    assert v == "construction et exploitation d'un centre de données", repr(v)
    assert "Procédure" not in v, (
        "la ligne suivante du règlement est versée dans l'objet : %r" % v)
    # ET LE TÉMOIN INVERSE : une continuation de ligne reste prise.
    coupe = ("Objet du marché : maîtrise d'œuvre pour la construction d'un\n"
             "centre de données de 4 MW IT sur le site de la zone nord.\n")
    w = _releve("objet", coupe)
    assert w and "zone nord" in w, (
        "un objet coupé par la mise en page est tronqué : %r" % w)


def test_la_reference_reconnait_la_forme_ANNEE_LETTRE_NUMERO():
    """« 2026-C-00396 » — année, lettre de service, numéro — est une forme
    courante, et elle n'entrait dans aucun des deux motifs : le premier veut
    le mot « référence » écrit, le second exige des CHIFFRES après le premier
    séparateur. Le cadre B du DC1 partait sans elle.

    ON ÉNUMÈRE LES FORMES, on n'en échantillonne pas une."""
    assert _releve("reference") == "2026-C-00396"
    for texte, attendu in (
            ("Consultation n° 2026-C-00396 — travaux", "2026-C-00396"),
            ("Marché n° 2024-018-TRX", "2024-018-TRX"),
            ("Dossier 2026/C/00396", "2026/C/00396"),
            ("Objet : travaux (2026-C-00396)", "2026-C-00396")):
        v = _releve("reference", "RÈGLEMENT DE LA CONSULTATION\n" + texte + "\n")
        assert v == attendu, "%r -> %r (attendu %r)" % (texte, v, attendu)


def test_le_cadre_C_du_DC1_recoit_la_DECISION_du_candidat_pas_le_nombre_de_lots():
    """LA FAUTE LA PLUS COÛTEUSE DES DEUX, parce qu'elle est PLAUSIBLE.

    Le cadre C demande « la candidature est présentée … pour le lot n°……. ou
    les lots n°…………… ». Le module y écrivait `lots`, c'est-à-dire
    l'allotissement RELEVÉ au règlement — « 3 lots ». L'acheteur qui ouvrait
    le pli lisait « présentée pour le lot n° 3 lots » : une réponse fausse à
    la question qui détermine à QUOI l'on postule, dans un formulaire signé.

    CE QUE LE CADRE ATTEND est `objet_candidature`, une DÉCISION que personne
    ne peut prendre à la place du candidat. Sans elle, la ligne reste vide et
    la pièce le dit."""
    ancres = {a["rubrique"]: a["ancre"] for a in ao_formulaires.ANCRES["dc1"]}
    assert ancres.get("objet_candidature") == "pour le lot n°", ancres
    assert "lots" not in ancres, (
        "l'allotissement relevé est de nouveau écrit dans le cadre C")
    # ET ON LE MESURE SUR LE DOCUMENT PRODUIT, pas seulement sur la table.
    an = ao_dc.analyser([{"nom": "01_RC.pdf", "texte": RC_LIGNES}])
    r = ao_dc.remplir(fiche=_socle(), analyse=an, saisies={})
    _b, rap = ao_formulaires.remplir_document(
        "dc1", ao_formulaires.valeurs_pour(r, "dc1"))
    ecrites = {x["rubrique"]: x["valeur"] for x in rap["places"]}
    assert "lots" not in ecrites, (
        "« %s » est écrit dans le DC1" % ecrites.get("lots"))
    assert "lots" in rap["sans_ancre"], (
        "l'allotissement n'est plus DIT alors qu'on le détient : %s"
        % rap["sans_ancre"])
    # ET LA LIGNE RESTE VIDE, SANS ÊTRE OUBLIÉE.
    p = next(x for x in r["pieces"] if x["cle"] == "dc1")
    oc = next(l for l in p["rubriques"] if l["cle"] == "objet_candidature")
    assert oc["statut"] == "a_saisir" and not oc.get("valeur"), oc


def test_le_SIRET_du_candidat_ne_peut_PAS_venir_du_reglement_de_consultation():
    """LE PIÈGE QUE LE RÈGLEMENT TEND. Un RC porte le SIRET de L'ACHETEUR —
    ici 24780064500147. Les cadres C1 du DC2 et D du DC1 demandent celui du
    CANDIDAT. Les confondre remplirait la case d'un numéro juste, plausible,
    et qui désigne la mauvaise entreprise : le candidat se déclarerait sous
    l'identité de son acheteur.

    LA GARANTIE EST STRUCTURELLE, et c'est ce qu'on mesure : aucun relevé de
    consultation ne s'appelle « siret », et TOUTES les rubriques de SIRET
    tirent de la fiche. Une règle qui vérifierait seulement que la valeur
    n'apparaît pas serait verte tant que le dossier d'essai ne la contient
    pas."""
    assert not [r for r in ao_dc.RELEVES if r["cle"] == "siret"], (
        "un relevé « siret » existe : le SIRET de l'acheteur peut désormais "
        "atteindre une rubrique de consultation")
    fautes = []
    for piece, rubriques in ao_dc.RUBRIQUES.items():
        for l in rubriques:
            if "siret" in l["cle"] and l["source"] != "fiche":
                fautes.append("%s.%s (source=%s)" % (piece, l["cle"], l["source"]))
    assert not fautes, "un SIRET ne vient plus de la fiche : %s" % fautes
    # ET LE TÉMOIN SUR UN DOSSIER QUI PORTE LE NUMÉRO DE L'ACHETEUR.
    an = ao_dc.analyser([{"nom": "01_RC.pdf", "texte": RC_LIGNES}])
    r = ao_dc.remplir(fiche=_socle(), analyse=an, saisies={})
    for cle in ("dc1", "dc2"):
        p = next(x for x in r["pieces"] if x["cle"] == cle)
        vals = " ".join(str(l.get("valeur") or "") for l in p["rubriques"])
        assert "24780064500147" not in vals, (
            "%s porte le SIRET de l'acheteur" % cle)


def test_le_cadre_C1_du_DC2_recoit_les_CINQ_lignes_que_le_dossier_porte():
    """« C1 — CAS GÉNÉRAL » OUVRE CINQ LIGNES et n'en recevait que deux.

    Nom, adresses, adresse électronique, téléphone et télécopie, SIRET, forme
    juridique. Le dossier d'entreprise porte l'adresse, le courriel et le
    téléphone — et aucune rubrique ne les demandait : trois lignes à recopier
    à la main d'un dossier qui les contenait.

    ON MESURE LE DOCUMENT PRODUIT, SOUS SON INTITULÉ. Vérifier qu'une valeur
    est « quelque part » serait vert pour une valeur posée dans le mauvais
    cadre — le DC2 porte « Adresse internet : » plus bas, au cadre C2."""
    an = ao_dc.analyser([{"nom": "01_RC.pdf", "texte": RC_LIGNES}])
    socle = _socle()
    r = ao_dc.remplir(fiche=socle, analyse=an, saisies={})
    attendu = {
        "dc1": {"courriel": socle["courriel"], "telephone": socle["telephone"]},
        "dc2": {"adresse": "%s, %s %s" % (socle["adresse"], socle["code_postal"],
                                          socle["ville"]),
                "courriel": socle["courriel"], "telephone": socle["telephone"]},
    }
    for modele, lignes in attendu.items():
        _b, rap = ao_formulaires.remplir_document(
            modele, ao_formulaires.valeurs_pour(r, modele))
        ecrites = {x["rubrique"]: x["valeur"] for x in rap["places"]}
        for cle, valeur in lignes.items():
            assert ecrites.get(cle) == valeur, (
                "%s : « %s » vaut %r, attendu %r"
                % (modele, cle, ecrites.get(cle), valeur))


# ═══════════════════════════════════════════════════════════════════════════
#  « RC » VEUT DIRE TROIS CHOSES, ET DEUX NE SONT PAS DU DOSSIER MARCHÉ
# ═══════════════════════════════════════════════════════════════════════════
#
#   · RC      — le RÈGLEMENT DE CONSULTATION, pièce de l'acheteur ;
#   · RCS     — le REGISTRE DU COMMERCE ET DES SOCIÉTÉS, où CONSEILPREV est
#               immatriculée : le Kbis, une pièce à NOUS ;
#   · RC pro  — la RESPONSABILITÉ CIVILE professionnelle : l'attestation de
#               notre assureur, une pièce à NOUS elle aussi.

def _ident(nom, texte=""):
    return ao_dc.identifier(nom, texte)


def test_une_attestation_RC_PRO_n_est_PAS_prise_pour_le_reglement():
    """LE DÉFAUT MESURÉ, ET SA CONSÉQUENCE LA PIRE.

    « attestation-rc-pro.pdf » était identifié RÈGLEMENT DE LA CONSULTATION,
    sur son seul nom. Le module cherchait alors dans une attestation
    d'assurance la date limite, les critères et l'objet du marché — il ne
    trouvait rien, et le disait. Mais surtout il déclarait le règlement
    PRÉSENT alors qu'il MANQUAIT : « ce qui manque », l'information que ce
    module vend comme la plus utile, devenait fausse dans le sens qui coûte.

    LA BORNE `(?![a-z])` NE SUFFISAIT PAS : elle protège « rcs » et
    « rcpro », où la lettre suit immédiatement, et laisse passer « rc-pro »,
    « rc_pro », « rc pro » et « rc professionnelle ».

    ON ÉNUMÈRE LES ÉCRITURES, on n'en échantillonne pas une."""
    for nom in ("attestation-rc-pro.pdf", "RC-professionnelle-2026.pdf",
                "RC_pro.pdf", "rc pro 2026.pdf", "RC.professionnelle.pdf",
                "assurance-responsabilite-civile.pdf"):
        r = _ident(nom, "ATTESTATION D'ASSURANCE responsabilité civile "
                        "professionnelle — police n° 12345")
        assert r["code"] != "rc", (
            "« %s » est pris pour le règlement de consultation" % nom)
        assert (r.get("candidat") or {}).get("cle") == "assurance_rc_pro", (
            "« %s » n'est pas nommé : %s" % (nom, r.get("pourquoi")))


def test_un_extrait_RCS_ou_KBIS_n_est_PAS_pris_pour_le_reglement():
    """LE REGISTRE DU COMMERCE EST À NOUS. C'est de lui que se lisent la ville
    d'immatriculation au RCS, la forme juridique et le capital de la fiche."""
    for nom in ("extrait-RCS.pdf", "kbis.pdf", "KBIS_CONSEILPREV.pdf",
                "rcs_paris.pdf"):
        r = _ident(nom, "EXTRAIT KBIS — registre du commerce et des sociétés")
        assert r["code"] != "rc", nom
        assert (r.get("candidat") or {}).get("cle") == "extrait_kbis", (
            "« %s » n'est pas nommé : %s" % (nom, r.get("pourquoi")))


def test_le_VRAI_reglement_reste_reconnu_meme_quand_il_PARLE_de_RC_pro():
    """LE TÉMOIN INVERSE, ET IL EST INDISPENSABLE. Un règlement de
    consultation EXIGE une attestation de responsabilité civile et la nomme
    dans sa liste de pièces à remettre. Une garde posée sur le TEXTE
    écarterait donc le vrai règlement.

    LA RÈGLE RETENUE : le NOM décide, le texte CONFIRME ou CONTREDIT. Un
    fichier nommé « rc-pro » dont le texte dit « règlement de la
    consultation » est le règlement, mal nommé, et rien n'est écarté."""
    r = _ident("RC.pdf", "RÈGLEMENT DE LA CONSULTATION. Le candidat produira "
                         "une attestation d'assurance responsabilité civile "
                         "professionnelle en cours de validité.")
    assert r["code"] == "rc", r
    mal_nomme = _ident("rc-pro.pdf", "RÈGLEMENT DE LA CONSULTATION — "
                                     "critères de jugement et pondération")
    assert mal_nomme["code"] == "rc", (
        "un règlement mal nommé est écarté : %s" % mal_nomme.get("pourquoi"))
    for nom in ("01_RC.pdf", "reglement-de-consultation.pdf", "RDC.pdf"):
        assert _ident(nom, "Composition du dossier à remettre.")["code"] == "rc", nom


def test_le_reglement_est_declare_MANQUANT_quand_seule_la_RC_pro_est_deposee():
    """LA CONSÉQUENCE, MESURÉE SUR L'ANALYSE COMPLÈTE — pas sur la seule
    identification. C'est là que le défaut coûtait : le dossier paraissait
    complet."""
    a = ao_dc.analyser([
        {"nom": "attestation-rc-pro.pdf",
         "texte": "ATTESTATION D'ASSURANCE responsabilité civile professionnelle"},
        {"nom": "02_CCAP.pdf", "texte": "Cahier des clauses administratives "
                                        "particulières — pénalités de retard"},
    ])
    assert "rc" not in {p["code"] for p in a["pieces"]}, (
        "le règlement est déclaré présent sur la foi d'une attestation")
    assert "rc" in {m["code"] for m in a["manquantes"]}, (
        "le règlement absent n'est pas signalé manquant")
    # ET LA PIÈCE EST NOMMÉE, pas rangée avec les fichiers illisibles.
    assert [p["fichier"] for p in a["pieces_candidat"]] == \
        ["attestation-rc-pro.pdf"], a["pieces_candidat"]
    assert not a["inconnues"], a["inconnues"]


def test_l_ecran_DIT_que_ces_pieces_sont_les_notres_et_ou_elles_vont():
    """UNE PIÈCE ÉCARTÉE SANS UN MOT ENVERRAIT CHERCHER UNE FAUTE DE NOMMAGE
    LÀ OÙ IL N'Y EN A PAS : le fichier est bien nommé, il appartient
    simplement à l'autre dossier."""
    a = ao_dc.analyser([{"nom": "kbis.pdf", "texte": "Extrait Kbis"}])
    alertes = " ".join(x["texte"] for x in a["alertes"])
    assert "VOTRE dossier" in alertes, alertes
    assert "responsabilité civile" in alertes and "registre du commerce" in alertes, (
        "l'alerte ne lève pas l'ambiguïté du sigle : %s" % alertes)
    p = a["pieces_candidat"][0]
    for champ in ("nom", "dossier", "ou"):
        assert (p.get(champ) or "").strip(), (champ, p)
    # ET LA PAGE LES DESSINE — un champ rendu par le serveur que personne
    # n'affiche est une correction que personne ne voit.
    #
    # ON EXÉCUTE LE RENDU, ON NE CHERCHE PAS LE NOM DANS LE FICHIER. Deux
    # mutations l'ont prouvé nécessaire : remplacer la condition par
    # `if (false)` laisse « a.pieces_candidat » dans la boucle juste en
    # dessous, et renommer la règle de style laisse « ig-ao-nous » sur la
    # ligne suivante. Une règle qui cherche une chaîne survit aux deux.
    # LE TEXTE EST ÉCHAPPÉ AU RENDU, ET IL DOIT L'ÊTRE. On déséchappe pour
    # comparer — ce qui vérifie au passage que l'échappement a bien eu lieu :
    # un texte arrivé brut ne se déséchapperait pas en lui-même.
    rendu = html.unescape(_rendu_analyse(a))
    assert "ig-ao-nous" in rendu, (
        "le bloc des pièces du candidat n'est pas dessiné")
    for p in a["pieces_candidat"]:
        assert p["fichier"] in rendu and p["nom"] in rendu, (
            "« %s » n'apparaît pas à l'écran" % p["fichier"])
        assert p["ou"] in rendu, "où la porter n'est pas dit"
    # ET LE BLOC A UN STYLE À LUI : sans quoi il se confondrait avec une
    # pièce du marché.
    css = _src("ingenierie-datacenter.html")
    assert ".ig-ao-nous{" in css, (
        "le bloc n'a plus de règle de style propre")
    # LE TÉMOIN NÉGATIF : sans pièce à nous, aucun bloc.
    vide = html.unescape(_rendu_analyse(ao_dc.analyser(
        [{"nom": "01_RC.pdf", "texte": "RÈGLEMENT DE LA CONSULTATION"}])))
    assert "ig-ao-nous" not in vide, (
        "le bloc s'affiche alors qu'aucune pièce du candidat n'a été déposée")


def _rendu_analyse(analyse):
    """Le HTML que `aoRendre` produit RÉELLEMENT, en l'exécutant sous node.

    Le rendu écrit dans le DOM ; on lui en donne un minimal — un objet qui
    retient ce qu'on lui pose — et l'on relit ce qu'il a écrit."""
    prog = _js_source("esc", "info", "aoTexteBouton", "aoTexteFermer",
                       "aoTexteBrancherListe", "aoIgnores", "aoRendre") + "\n".join([
        "",
        # LE RENDU BRANCHE DÉSORMAIS DES ÉCOUTEURS SUR CE QU'IL VIENT
        # D'ÉCRIRE (le bouton « Lire » de chaque pièce) et ferme le lecteur.
        # Le banc doit donc offrir `querySelectorAll` sur la zone, comme le
        # ferait un vrai élément. Sans cela il tombe — et c'est son office.
        "const zone = {innerHTML: '', querySelectorAll: () => []};",
        "const lect = {innerHTML: ''};",
        "var AO_TEXTES = {}, AO_TEXTE_OUVERT = null;",
        "globalThis.$ = (s) => (s === '#ig-ao-lect' ? lect : zone);",
        "globalThis.document = {querySelector: () => null,"
        " querySelectorAll: () => []};",
        "aoRendre(JSON.parse(process.env.AN));",
        "process.stdout.write(zone.innerHTML);",
        "",
    ])
    out = subprocess.run(["node"], input=prog, capture_output=True,
                         text=True, timeout=60,
                         env=dict(os.environ, AN=json.dumps(analyse)))
    assert out.returncode == 0, out.stderr[-1500:]
    return out.stdout


def test_le_cadre_A_de_l_ATTRI1_recoit_l_objet_du_MARCHE_relevé_au_reglement():
    """« A — OBJET DE L'ACTE D'ENGAGEMENT » ATTEND L'OBJET DU MARCHÉ PUBLIC,
    et cet objet est écrit dans le règlement de consultation — pas ailleurs.

    LE CADRE PORTE DEUX CHOSES, ET IL FAUT LES SÉPARER :
      · « Objet du marché public » — un FAIT, relevé au règlement ;
      · « Cet acte d'engagement correspond … au lot n°……. ou aux lots
        n°…………… » avec l'instruction « Indiquer l'INTITULÉ du ou des lots » —
        une DÉCISION du titulaire.

    LE DÉFAUT MESURÉ, jumeau de celui du cadre C du DC1 : l'allotissement
    relevé — « 3 lots » — était écrit sous la seconde ligne. L'acheteur lisait
    « cet acte d'engagement correspond au lot n° 3 lots », là où le formulaire
    réclame un intitulé."""
    an = ao_dc.analyser([{"nom": "01_RC.pdf", "texte": RC_LIGNES}])
    r = ao_dc.remplir(fiche=_socle(), analyse=an, saisies={})
    _b, rap = ao_formulaires.remplir_document(
        "attri1", ao_formulaires.valeurs_pour(r, "acte_engagement"))
    ecrites = {x["rubrique"]: x["valeur"] for x in rap["places"]}
    # L'OBJET DU MARCHÉ ARRIVE, ET IL VIENT BIEN DU RÈGLEMENT.
    assert ecrites.get("objet_marche") == \
        "construction et exploitation d'un centre de données", ecrites
    assert "Procédure" not in ecrites.get("objet_marche", ""), (
        "la ligne suivante du règlement est versée dans le cadre A")
    # ET L'ALLOTISSEMENT N'EST PAS ÉCRIT À LA PLACE DE LA DÉCISION.
    assert "lots" not in ecrites, (
        "« %s » est écrit dans le cadre A" % ecrites.get("lots"))
    assert "lots" in rap["sans_ancre"], rap["sans_ancre"]
    p = next(x for x in r["pieces"] if x["cle"] == "acte_engagement")
    lv = next(l for l in p["rubriques"] if l["cle"] == "lots_vises")
    assert lv["statut"] == "a_saisir" and not lv.get("valeur"), lv
    # QUAND LA DÉCISION EST PRISE, ELLE S'ÉCRIT — et sous SON intitulé.
    r2 = ao_dc.remplir(fiche=_socle(), analyse=an,
                       saisies={"acte_engagement.lots_vises": "Lot 3 — froid"})
    _b2, rap2 = ao_formulaires.remplir_document(
        "attri1", ao_formulaires.valeurs_pour(r2, "acte_engagement"))
    assert {x["rubrique"]: x["valeur"] for x in rap2["places"]}.get(
        "lots_vises") == "Lot 3 — froid", rap2["places"]
