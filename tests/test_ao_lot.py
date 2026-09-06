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
def projet(connecte, monkeypatch):
    """Un projet du compte, avec le chiffrement du dossier ACTIF.

    SANS CLÉ, LE MODULE REFUSE D'ÉCRIRE — et il a raison : conserver un dossier
    de consultation en clair serait pire que ne pas le conserver. La règle
    fournit donc une clé, au lieu de sauter le contrôle."""
    import ao_projet
    from cryptography.fernet import Fernet
    monkeypatch.setenv(ao_projet.VAR_CLE, Fernet.generate_key().decode())
    r = connecte.post("/api/datacenter/projets",
                      json={"nom": "Dossier d'essai"}, headers=ORIGINE)
    assert r.status_code == 200, r.data[:200]
    return r.get_json()["projet"]["id"]


@pytest.fixture
def projet_admin(admin, monkeypatch):
    """Le même projet, sur le compte d'administration : `/analyser` lui est
    ouverte, et c'est la seule façon de comparer les deux routes."""
    import ao_projet
    from cryptography.fernet import Fernet
    monkeypatch.setenv(ao_projet.VAR_CLE, Fernet.generate_key().decode())
    r = admin.post("/api/datacenter/projets",
                   json={"nom": "Dossier d'essai (admin)"}, headers=ORIGINE)
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
        connecte, projet):
    """LE DÉFAUT MESURÉ, ET SA RÈGLE. Deux pièces, puis une troisième : le
    dossier en portait UNE. Le geste « une par une » que la page propose était
    donc une façon de perdre son dossier."""
    _deposer(connecte, projet, pieces=DCE[:2], fiche={})
    noms, _ = _dossier(connecte, projet)
    assert noms == ["reglement-de-consultation.pdf", "CCAP.pdf"], noms
    _deposer(connecte, projet, pieces=DCE[2:])
    noms, a = _dossier(connecte, projet)
    assert len(noms) == 3, "la troisième pièce a effacé les deux autres : %s" % noms
    assert len(a.get("pieces") or []) == 3, (
        "le relevé ne porte que sur %d pièce(s) : il est refait sur le dernier "
        "dépôt et non sur le dossier entier"
        % len(a.get("pieces") or []))


def test_une_piece_REDEPOSEE_remplace_la_sienne_et_garde_sa_place(connecte, projet):
    """Le geste du rectificatif : l'acheteur republie un CCAP trois jours plus
    tard. Garder les deux ferait relever deux fois des clauses contradictoires ;
    l'ajouter à la fin réordonnerait le dossier à chaque dépôt."""
    _deposer(connecte, projet, pieces=DCE, fiche={})
    _deposer(connecte, projet,
             pieces=[{"nom": "CCAP.pdf", "texte": "RECTIFICATIF. Pénalités : 1/2000."}])
    noms, _ = _dossier(connecte, projet)
    assert noms == [p["nom"] for p in DCE], noms


def test_une_piece_se_RETIRE_sans_perdre_le_dossier(connecte, projet):
    """Sans ce geste, corriger un dépôt fautif imposerait de tout effacer puis
    de tout redéposer — c'est-à-dire de perdre ce qu'on ne retrouverait pas."""
    _deposer(connecte, projet, pieces=DCE, fiche={})
    r = _deposer(connecte, projet, retirer="CCTP.pdf")
    assert r.status_code == 200
    noms, a = _dossier(connecte, projet)
    assert noms == ["reglement-de-consultation.pdf", "CCAP.pdf"], noms
    assert len(a["pieces"]) == 2, "le relevé n'a pas suivi le retrait"
    assert _deposer(connecte, projet, retirer="JAMAIS-DEPOSE.pdf").status_code == 404


def test_le_remplacement_reste_possible_mais_il_faut_le_DEMANDER(connecte, projet):
    _deposer(connecte, projet, pieces=DCE, fiche={})
    _deposer(connecte, projet, pieces=[{"nom": "SEUL.pdf", "texte": "x"}],
             remplacer=True)
    noms, _ = _dossier(connecte, projet)
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


def test_le_depot_conserve_le_TEXTE_des_pieces_que_la_page_envoie(connecte, projet):
    """La règle qui manquait. Elle poste ce que le navigateur poste."""
    r = _deposer(connecte, projet, pieces=_comme_la_page(DCE), fiche={})
    assert r.status_code == 200, r.data[:300]
    d = connecte.get("/api/datacenter/marche/projet/dossier?projet=" + projet,
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
        connecte, projet):
    """LA PROMESSE DE LA PAGE, DE BOUT EN BOUT — par la route, pas par le
    module. « Charger les pièces de la consultation pour remplir
    automatiquement les pièces choisies » n'est tenu que si l'acheteur relevé
    dans le règlement ressort dans un document produit."""
    _deposer(connecte, projet, pieces=_comme_la_page(DCE), fiche={})
    d = connecte.get("/api/datacenter/marche/projet/dossier?projet=" + projet,
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


def test_ce_qui_n_a_pas_pu_etre_lu_au_depot_est_NOMME(connecte, projet):
    """Un dépôt de trois pièces dont une est illisible ne doit pas se lire
    comme un dépôt de trois. L'écarter en silence ferait croire le dossier
    complet — et c'est précisément l'erreur qu'on vient de corriger."""
    charge = _comme_la_page(DCE[:1]) + [{"nom": "ABIME.pdf", "contenu": "@@@"}]
    r = _deposer(connecte, projet, pieces=charge, fiche={})
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    assert "ABIME.pdf" in json.dumps(j.get("ignores") or [], ensure_ascii=False), (
        "la pièce illisible n'est pas nommée dans la réponse : %r"
        % (j.get("ignores"),))
    noms, _ = _dossier(connecte, projet)
    assert noms == _noms_page(DCE[:1]), noms


def test_l_analyse_et_le_depot_lisent_par_la_MEME_porte(admin, projet_admin):
    """DEUX EXTRACTIONS, C'EST UNE DIVERGENCE EN ATTENTE. Celle qu'on vient de
    payer : l'analyse décodait le base64, le dépôt non. La règle exige que le
    même contenu illisible soit écarté par les deux routes avec le MÊME motif —
    ce qui n'est vrai que s'il n'y a qu'une porte."""
    charge = [{"nom": "ABIME.pdf", "contenu": "@@@"}]
    a = admin.post("/api/datacenter/marche/analyser",
                   json={"documents": charge}, headers=ORIGINE).get_json()
    d = _deposer(admin, projet_admin,
                 pieces=_comme_la_page(DCE[:1]) + charge).get_json()
    motif_a = [x["pourquoi"] for x in (a.get("ignores") or [])
               if x["fichier"] == "ABIME.pdf"]
    motif_d = [x["pourquoi"] for x in (d.get("ignores") or [])
               if x["fichier"] == "ABIME.pdf"]
    assert motif_a and motif_a == motif_d, (
        "les deux routes n'écartent pas la même pièce pour la même raison — "
        "elles ne partagent donc pas leur extraction : analyse %r, dépôt %r"
        % (motif_a, motif_d))


def test_la_page_envoie_la_forme_QUE_LE_DEPOT_LIT(connecte, projet):
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
    r = _deposer(connecte, projet, pieces=charge, fiche={})
    assert r.status_code == 200, r.data[:300]
    d = connecte.get("/api/datacenter/marche/projet/dossier?projet=" + projet,
                     headers=ORIGINE).get_json()["dossier"]
    assert d and all(p["octets"] for p in d["pieces"]), (
        "la route ne sait pas lire les champs %r que la page pose : le dossier "
        "conservé est vide" % (cles,))


def test_le_depot_passe_par_l_ANTIVIRUS_comme_l_analyse(connecte, projet):
    """CE QUE LA PORTE PARTAGÉE FAIT GAGNER, et qu'il faut donc tenir. Avant,
    le dépôt ne recevait que du texte : aucun fichier n'était ouvert, et
    l'antivirus n'avait rien à inspecter. Maintenant que le dépôt décode et
    extrait, il ouvre des fichiers — exactement ce contre quoi cette porte
    existe. Un contenu qui ment sur son extension doit être refusé ICI aussi.
    """
    charge = [{"nom": "piege.pdf", "contenu": _b64("Ceci n'est pas un PDF.")}]
    j = _deposer(connecte, projet, pieces=charge, fiche={}).get_json()
    motifs = " ".join(x["pourquoi"] for x in (j.get("ignores") or []))
    assert "extension" in motifs, (
        "un contenu qui ment sur son extension entre au dossier sans que "
        "l'inspection structurelle l'ait vu : %r" % (j.get("ignores"),))
    noms, _ = _dossier(connecte, projet)
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
