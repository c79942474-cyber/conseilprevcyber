# -*- coding: utf-8 -*-
"""Le dossier conservé s'offre en liste déroulante, et on en retire une pièce.

LA RÈGLE DU DONNEUR D'ORDRE : « le dossier et ses documents sont alors stockés
et disponibles dans une liste déroulante avec possibilité de les supprimer ».

CE QUI Y MANQUAIT. La file de DÉPÔT — les pièces choisies avant l'analyse —
était déjà une déroulante avec retrait. Le dossier CONSERVÉ, lui, c'est-à-dire
celui qui est réellement stocké chiffré dans le projet, n'était qu'une liste à
puces. C'est pourtant celui que la règle vise : « stockés », pas « choisis ».

CES RÈGLES EXÉCUTENT LE RENDU, ELLES NE LE RELISENT PAS. Chercher `<select`
dans le fichier dirait qu'une balise existe, pas qu'elle porte les pièces du
dossier ni que le bouton « Retirer » atteint celle qu'on a choisie. Le piège
est consigné deux fois ailleurs dans ce dépôt : une règle qui constate une
propriété syntaxique reste verte pendant que l'écran ne fait plus rien.

LES DEUX DANGERS PROPRES À CE GESTE :

  · DEUX LISTES QUI DIVERGENT. La déroulante et le détail montrent les mêmes
    pièces ; les alimenter séparément aurait garanti qu'elles s'écartent — et
    c'est la déroulante, plus courte, qu'on aurait crue exhaustive.

  · UN RETRAIT QUI PART TOUT SEUL. Ce qui est retiré du dossier conservé ne se
    retrouve pas : le fichier d'origine n'est pas gardé, seul son texte
    extrait l'était. Un sélecteur qui supprimerait au changement ferait de
    chaque parcours de la liste une perte définitive.
"""
import io
import json
import os
import re
import subprocess

import pytest


ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from test_ao_formulaires import _js_source                      # noqa: E402


def _node(prog, env=None):
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60, env=dict(os.environ, **(env or {})))
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout


# --------------------------------------------------------------------------
# LE RENDU, EXÉCUTÉ.
# --------------------------------------------------------------------------
def _rendu(noms):
    """Le balisage que `aoProjetRendre` produit RÉELLEMENT sur un dossier."""
    etat = {
        "dossier": {"pieces": [{"nom": n, "octets": 120 + i * 10,
                                "empreinte": "abcdef0123456789"}
                               for i, n in enumerate(noms)],
                    "maj_le": 1750000000000, "purge_le": 1780000000000},
        "declarations": {"lignes": []},
        "textes": [],
    }
    prog = (_js_source("esc", "aoOctets", "aoJour", "aoTexteBouton",
                       "aoProjetRendre")
            + "\nfunction fr(n){ return String(Math.round(Number(n)||0)); }"
            + "\nfunction aoProjetInvite(){ return '<i>invite</i>'; }"
            + "\nfunction aoDeclaration(){ return ''; }"
            + "\nfunction aoProjetBrancher(){}"
            + "\nvar AO_PROJET = 'p1';"
            + "\nvar AO_PROJET_ETAT = JSON.parse(process.env.ET);"
            + "\nvar zone = { innerHTML: '' };"
            + "\nfunction $(s){ return s === '#ig-ao-projet' ? zone : null; }"
            + "\naoProjetRendre();"
            + "\nprocess.stdout.write(zone.innerHTML);\n")
    return _node(prog, {"ET": json.dumps(etat)})


def _deroulante(h):
    """Le contenu de la liste déroulante des pièces conservées."""
    m = re.search(r'<select id="ig-cons-piece"[^>]*>(.*?)</select>', h, re.S)
    return m.group(1) if m else None


def _options(h):
    bloc = _deroulante(h)
    assert bloc is not None, "aucune liste déroulante des pièces conservées"
    return re.findall(r'<option value="([^"]*)">(.*?)</option>', bloc, re.S)


# --------------------------------------------------------------------------
# LES GESTES, EXÉCUTÉS.
# --------------------------------------------------------------------------
def _gestes(choix, evenements=("click",)):
    """Ce que les boutons de la déroulante APPELLENT, en les déclenchant.

    Les fonctions visées sont remplacées par des mouchards : on mesure ce qui
    est demandé, pas ce qui est écrit. Une poignée branchée sur la mauvaise
    valeur, ou branchée sur rien, se voit ici et nulle part ailleurs.
    """
    prog = (_js_source("aoProjetBrancher")
            + "\nvar trace = [];"
            + "\nfunction aoProjetRetirer(n){ trace.push(['retirer', n]); }"
            + "\nfunction aoTexteOuvrir(n){ trace.push(['lire', n]); }"
            + "\nfunction aoProjetMsg(t){ trace.push(['msg', t]); }"
            + "\nfunction aoProjetRetenir(){} function aoProjetDeposer(){}"
            + "\nfunction aoProjetOublier(){} function aoTexteBrancherListe(){}"
            + "\nfunction aoAffirmer(){}"
            + "\nfunction elt(){ var e = { h: {},"
              " addEventListener: function (t, f) { e.h[t] = f; } }; return e; }"
            + "\nvar pc = elt(); pc.value = process.env.CHOIX;"
            + "\nvar lir = elt(), otz = elt();"
            + "\nvar tab = { '#ig-cons-piece': pc, '#ig-cons-lire': lir,"
              " '#ig-cons-otez': otz };"
            + "\nfunction $(s){ return tab[s] || null; }"
            + "\nvar z = { querySelectorAll: function () { return []; } };"
            + "\naoProjetBrancher(z);"
            + "\nvar EV = JSON.parse(process.env.EV);"
            + "\nEV.forEach(function (e) {"
              " if (pc.h[e]) pc.h[e]();"
              " if (lir.h[e]) lir.h[e]();"
              " if (otz.h[e]) otz.h[e](); });"
            + "\nprocess.stdout.write(JSON.stringify("
              "{trace: trace, poignees: {pc: Object.keys(pc.h),"
              " lire: Object.keys(lir.h), otez: Object.keys(otz.h)}}));\n")
    return json.loads(_node(prog, {"CHOIX": choix,
                                   "EV": json.dumps(list(evenements))}))


TROIS = ["RC.pdf", "CCTP data center.pdf", "DPGF.xlsx"]


# ==========================================================================
# LA DÉROULANTE
# ==========================================================================
def test_le_dossier_conserve_s_offre_en_liste_DEROULANTE():
    """« stockés et disponibles dans une liste déroulante » — au sens propre."""
    h = _rendu(TROIS)
    assert _deroulante(h) is not None, h[:400]
    assert h.count('<select id="ig-cons-piece"') == 1, \
        "la déroulante des pièces conservées est rendue plusieurs fois"


def test_la_deroulante_nomme_CHAQUE_piece_conservee():
    """Une déroulante qui n'en montre que deux sur trois est pire qu'aucune :
    on la croit exhaustive."""
    vals = [v for v, _ in _options(_rendu(TROIS)) if v]
    assert vals == TROIS, "la déroulante montre %s" % vals


def test_la_deroulante_et_le_detail_montrent_les_MEMES_pieces():
    """LE DANGER PROPRE À DEUX RENDUS D'UNE MÊME TABLE. Ils divergeraient le
    jour où l'un des deux serait filtré, trié ou tronqué — et rien à l'écran
    ne le dirait."""
    h = _rendu(TROIS)
    deroulante = sorted(v for v, _ in _options(h) if v)
    detail = sorted(set(re.findall(r'data-retirer="([^"]*)"', h)))
    assert deroulante == detail, \
        "déroulante %s ≠ détail %s" % (deroulante, detail)


def test_la_deroulante_annonce_le_NOMBRE_de_pieces_avant_qu_on_l_ouvre():
    """Trois pièces ou quinze ne se décident pas de la même façon, et on le
    sait avant d'ouvrir la liste."""
    tete = _options(_rendu(TROIS))[0]
    assert tete[0] == "", "la première entrée n'est pas une invite"
    assert "3 pièce(s)" in tete[1], tete[1]


def test_un_dossier_conserve_qui_ne_porte_RIEN_ne_le_cache_pas():
    """Une déroulante vide qui annonce « 3 pièce(s) » serait un mensonge ;
    une déroulante absente ferait croire à une panne."""
    h = _rendu([])
    assert _deroulante(h) is not None, "la déroulante disparaît sur un dossier vide"
    opts = _options(h)
    assert [v for v, _ in opts if v] == [], "des pièces sortent de nulle part"
    assert "0 pièce(s)" in opts[0][1], opts[0][1]


def test_la_taille_annoncee_dans_la_deroulante_dit_qu_elle_est_celle_du_TEXTE():
    """« 130 o » à côté de « RC.pdf » se lit comme la taille du PDF. Le PDF
    n'est pas conservé — c'est celle du texte extrait."""
    for val, libelle in _options(_rendu(TROIS)):
        if not val:
            continue
        assert "de texte" in libelle, libelle


# ==========================================================================
# LES DEUX GESTES
# ==========================================================================
def test_RETIRER_porte_sur_la_piece_CHOISIE_dans_la_deroulante():
    """« avec possibilité de les supprimer », depuis la déroulante elle-même."""
    t = _gestes("CCTP data center.pdf")["trace"]
    assert ["retirer", "CCTP data center.pdf"] in t, t


def test_LIRE_ouvre_la_piece_choisie_et_pas_une_autre():
    t = _gestes("DPGF.xlsx")["trace"]
    assert ["lire", "DPGF.xlsx"] in t, t


def test_un_geste_sans_piece_choisie_le_DIT_au_lieu_de_ne_rien_faire():
    """Un bouton muet se reclique, puis se prend pour une panne."""
    r = _gestes("")
    gestes = [x for x in r["trace"] if x[0] in ("retirer", "lire")]
    assert not gestes, "un geste part sans pièce choisie : %s" % gestes
    dits = [x[1] for x in r["trace"] if x[0] == "msg"]
    assert len(dits) == 2, "les deux boutons ne disent pas ce qui manque : %s" % dits
    for d in dits:
        assert "pièce" in d, d


def test_PARCOURIR_la_liste_ne_RETIRE_rien():
    """LE DANGER NOMMÉ. Ce qui est retiré ne se retrouve pas : seul le texte
    extrait était conservé, le fichier d'origine non. Un sélecteur qui agirait
    au changement transformerait chaque coup d'œil en perte définitive."""
    r = _gestes("RC.pdf", evenements=("change", "input"))
    assert not r["trace"], \
        "parcourir la liste a déclenché : %s" % r["trace"]


def test_les_deux_boutons_sont_REELLEMENT_branches():
    """Sans cette règle, les trois précédentes seraient vertes sur une trace
    vide — c'est-à-dire sur deux boutons morts."""
    p = _gestes("RC.pdf")["poignees"]
    assert "click" in p["lire"], "« Lire » n'écoute aucun clic"
    assert "click" in p["otez"], "« Retirer » n'écoute aucun clic"


# ==========================================================================
# LES DEUX DÉROULANTES DU MÊME BLOC
# ==========================================================================
def _selects(nom):
    return set(re.findall(r"""id=\\?["'](ig-cons-[A-Za-z0-9_-]+)""",
                          _js_source(nom)))


def test_la_deroulante_des_PIECES_n_est_pas_celle_des_PROJETS():
    """Le même bloc rend une déroulante de PROJETS quand rien n'est rattaché,
    et une déroulante de PIÈCES quand un dossier est conservé. Leur donner le
    même identifiant ferait lire l'une pour l'autre au branchement — et c'est
    un retrait de pièce qui partirait sur un nom de projet."""
    invite = _selects("aoProjetInvite")
    rendu = _selects("aoProjetRendre")
    assert "ig-cons-sel" in invite, "la déroulante des projets a changé de nom"
    assert "ig-cons-piece" in rendu, "la déroulante des pièces a changé de nom"
    assert "ig-cons-sel" not in rendu and "ig-cons-piece" not in invite, \
        "les deux blocs se disputent un identifiant : %s" % sorted(invite & rendu)


# ==========================================================================
# LA CLASSE DE LA RANGÉE — l'autre forme de la collision
# ==========================================================================
def _feuille_base():
    """La feuille de la page, commentaires et requêtes média ôtés."""
    css = io.open(os.path.join(ICI, "ingenierie-datacenter.html"),
                  encoding="utf-8").read()
    css = re.sub(r"/\*.*?\*/", "",
                 "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", css, re.S)),
                 flags=re.S)
    out, i = [], 0
    while True:
        m = re.compile(r"@media[^{]*\{").search(css, i)
        if not m:
            out.append(css[i:])
            return "".join(out)
        out.append(css[i:m.start()])
        j, n = m.end(), 1
        while j < len(css) and n:
            n += {"{": 1, "}": -1}.get(css[j], 0)
            j += 1
        i = j


def test_la_rangee_de_la_deroulante_a_sa_PROPRE_classe():
    """LE DÉFAUT QUE CETTE RÈGLE TIENT, ET QUE J'AI COMMIS.

    La première version de cette rangée s'appelait `ig-cons-d` — un nom que le
    bloc des six déclarations employait DÉJÀ. Mesuré au navigateur : la rangée
    héritait d'un cadre et de douze pixels de marge qu'elle n'avait pas
    demandés et, plus grave, le `display:flex` déclaré pour elle s'appliquait
    aux six déclarations, qui ne sont pas des rangées.

    C'est la version « feuille de style » de la collision d'identifiants
    corrigée au § 14 : elle ne casse rien à l'endroit qu'on regarde.

    LA MESURE PORTE SUR LA CLASSE RÉELLEMENT RENDUE, lue dans le balisage
    produit — la recopier ici rendrait la règle verte sur un nom qui n'est plus
    employé. La feuille entière n'est pas passée au crible : trois classes y
    sont déjà déclarées deux fois avec des valeurs qui se contredisent, et les
    reprendre déborde de ce geste.
    """
    h = _rendu(TROIS)
    m = re.search(r'<div class="([A-Za-z0-9_ -]+)"><label class="dc-lab" '
                  r'for="ig-cons-piece"', h)
    assert m, "la rangée de la déroulante n'a pas de conteneur identifiable"
    classes = m.group(1).split()
    assert len(classes) == 1, "la rangée porte plusieurs classes : %s" % classes
    classe = classes[0]

    base = _feuille_base()
    nues = [sel.strip().split("\n")[-1].strip()
            for b in re.finditer(r"([^{}]+)\{([^{}]*)\}", base, re.S)
            for sel in b.group(1).split(",")]
    assert nues.count("." + classe) == 1, (
        "« %s » est déclarée %d fois dans la feuille : la rangée hérite de "
        "règles écrites pour un autre bloc"
        % (classe, nues.count("." + classe)))

    autres = [n for n, c in
              [(n, _js_source(n)) for n in ("aoProjetInvite", "aoDeclaration")]
              if 'class="%s"' % classe in c]
    assert not autres, \
        "« %s » est aussi posée par : %s" % (classe, autres)
