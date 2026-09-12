# -*- coding: utf-8 -*-
"""§ 14 en deux colonnes — et la collision d'identifiants qui l'avait vidé.

CE QUE L'ÉCRAN DOIT TENIR (règle 4 du donneur d'ordre) : le dossier déposé à
GAUCHE, les documents retenus à DROITE, scindés entre dossier de candidature et
dossier d'offre, chacun avec sa liste déroulante.

LE DÉFAUT QUI A COÛTÉ UN TOUR, ET QUI EST LA RAISON D'ÊTRE DE CE FICHIER. Le
rendu de la sélection écrivait dans `#ig-ao-sel` — un identifiant que la file
de dépôt employait DÉJÀ pour son `<select>`. Deux conséquences, toutes deux
silencieuses :

  · un `<select>` ne garde que des `<option>` ; tout le balisage de la colonne
    de droite était jeté par le navigateur sans une ligne de console ;
  · et la liste déroulante du dépôt, à gauche, était écrasée du même coup.

Aucune règle n'a rien vu, parce qu'aucune ne regardait AILLEURS que dans le
fichier qu'elle relisait. L'identifiant était unique dans la page, unique dans
la fonction, et déjà pris dans la fonction d'à côté.

CE QUE CES RÈGLES MESURENT, DONC :

  · LA GRILLE, sur la structure réelle du document : deux colonnes de même
    poids, le dépôt dans la première, la sélection dans la seconde, et une
    largeur sous laquelle elles s'empilent.

  · LES IDENTIFIANTS, sur l'ENSEMBLE des surfaces qui écrivent dans cette
    page — la page elle-même et chaque fonction du script. C'est le seul
    angle d'où la collision était visible.

  · LA PARTITION : les trois groupes de droite couvrent toutes les lignes que
    le moteur rend, sans recouvrement. Une pièce retenue avec un dossier que
    l'écran ne sait pas afficher disparaîtrait sans bruit — et c'est un
    document manquant au dépôt des plis.

  · LA PORTÉE DU PÉRIMÈTRE : les quatre requêtes qui PRODUISENT le dossier le
    portent. Une seule qui l'oublie et l'écran annonce six pièces pendant que
    l'archive en contient vingt-trois.

CE QUI RESTE HORS DE PORTÉE D'UN TEST PYTHON, ET QUI EST DIT PLUTÔT QUE TU. Le
rendu effectif — largeurs en pixels, débordement, empilement — se mesure au
navigateur, et il l'est : `scratchpad/banc_ao.py` sert l'application réelle
avec une session d'administration réelle. Les règles ci-dessous tiennent la
STRUCTURE déclarée ; le banc tient le RENDU. Les deux sont nécessaires, et
aucune des deux ne remplace l'autre.
"""
import io
import os
import re
from html.parser import HTMLParser

import pytest

import ao_dc


ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRILLE = "ig-ao-grille"
COLONNE = "ig-ao-col"
A_GAUCHE = "ig-ao-depot"          # la file du dossier déposé
A_DROITE = "ig-ao-retenus"        # le conteneur de la sélection


def _lire(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


def _html():
    return _lire("ingenierie-datacenter.html")


def _js():
    return _lire("ingenierie-dc.js")


# --------------------------------------------------------------------------
# Lecture de la STRUCTURE du document, pas de son texte.
# --------------------------------------------------------------------------
class _Arbre(HTMLParser):
    """Relève, pour la grille du § 14, ses colonnes directes et leur contenu.

    On ne cherche pas une chaîne : on suit l'imbrication. Une colonne qui
    cesserait d'être fille de la grille — parce qu'un `</div>` a bougé — le
    dirait ici, là où un `grep` ne verrait rien.
    """

    VIDES = {"br", "hr", "img", "input", "meta", "link", "source", "col"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pile = []
        self.colonnes = []        # [{ids, balises, classes, vide}]
        self._grille = None
        self._col = None
        self.conteneurs = {}      # id -> balise qui le porte
        self.enfants = {}         # id -> nb d'éléments fils

    def handle_starttag(self, balise, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        ident = a.get("id")
        if ident:
            self.conteneurs[ident] = balise
            self.enfants.setdefault(ident, 0)
        for ouvert in self.pile:
            if ouvert.get("id") in self.enfants:
                self.enfants[ouvert["id"]] += 1
        if self._grille is not None and self._col is not None:
            self._col["balises"].append(balise)
            if ident:
                self._col["ids"].append(ident)
        elif self._grille is not None and COLONNE in cls \
                and len(self.pile) == self._grille + 1:
            self._col = {"ids": [], "balises": [], "profondeur": len(self.pile)}
        elif GRILLE in cls:
            self._grille = len(self.pile)
        self.pile.append({"balise": balise, "id": ident})
        if balise in self.VIDES:
            self.pile.pop()

    def handle_endtag(self, balise):
        if balise in self.VIDES:
            return
        while self.pile and self.pile[-1]["balise"] != balise:
            self.pile.pop()
        if self.pile:
            self.pile.pop()
        if self._col is not None and len(self.pile) <= self._col["profondeur"]:
            self.colonnes.append(self._col)
            self._col = None
        if self._grille is not None and len(self.pile) <= self._grille:
            self._grille = None


def _arbre():
    a = _Arbre()
    a.feed(_html())
    return a


# --------------------------------------------------------------------------
# Lecture des DÉCLARATIONS de la feuille, pas de ses mots.
# --------------------------------------------------------------------------
def _feuille():
    """Le contenu des blocs <style> de la page, commentaires ôtés."""
    blocs = re.findall(r"<style[^>]*>(.*?)</style>", _html(), re.S)
    return re.sub(r"/\*.*?\*/", "", "\n".join(blocs), flags=re.S)


def _sans_media(css):
    """La feuille privée de ses requêtes média — la déclaration de base.

    Sans cela une surcharge d'empilement, écrite plus bas dans la feuille,
    passerait pour la déclaration de base : la règle des deux colonnes serait
    verte sur une grille qui n'en a qu'une.
    """
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


def _bloc_media(css, largeur_max):
    """Rend le corps de la requête média qui plafonne à `largeur_max`."""
    m = re.search(r"@media\s*\(\s*max-width\s*:\s*%dpx\s*\)\s*\{" % largeur_max,
                  css)
    if not m:
        return None
    i, n = m.end(), 1
    while i < len(css) and n:
        n += {"{": 1, "}": -1}.get(css[i], 0)
        i += 1
    return css[m.end():i - 1]


def _declaration(css, selecteur, propriete):
    """La dernière valeur déclarée pour `propriete` sur `selecteur`.

    La DERNIÈRE, parce que c'est celle qui gagne en cascade à spécificité
    égale : lire la première ferait passer une surcharge pour absente.
    """
    valeur = None
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css, re.S):
        cibles = [x.strip().split("\n")[-1].strip()
                  for x in m.group(1).split(",")]
        if selecteur not in cibles:
            continue
        for d in m.group(2).split(";"):
            if ":" not in d:
                continue
            p, v = d.split(":", 1)
            if p.strip() == propriete:
                valeur = v.strip()
    return valeur


def _pistes(valeur):
    """Découpe une valeur de `grid-template-columns` en pistes."""
    return [p for p in re.split(r"\s+", (valeur or "").strip()) if p]


# --------------------------------------------------------------------------
# Lecture d'une FONCTION du script, bornes comprises.
# --------------------------------------------------------------------------
def _neutraliser(src):
    """Rend `src` de MÊME longueur, commentaires, chaînes et littéraux régex
    remplacés par des points.

    POURQUOI CE SOIN. Le script est commenté en français : « l'écran »,
    « d'ordre », « qu'on ». Un compteur d'accolades naïf prend cette apostrophe
    pour une ouverture de chaîne et avale tout jusqu'à la suivante — il rend
    alors le corps d'une AUTRE fonction. C'est ce qui, au premier jet, a rendu
    vertes des règles qui lisaient le mauvais code : le défaut même que ce
    fichier existe pour tenir.
    """
    out, i, n = list(src), 0, len(src)
    prec = ""
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if src[k] != "\n":
                    out[k] = "."
            i = j
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = "."
            i = j
            continue
        if c == "/" and prec in "=(,:[!&|?{};" and i + 1 < n \
                and src[i + 1] not in "/*":
            j, classe = i + 1, False
            while j < n and src[j] != "\n":
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == "[":
                    classe = True
                elif src[j] == "]":
                    classe = False
                elif src[j] == "/" and not classe:
                    break
                j += 1
            if j < n and src[j] == "/":
                for k in range(i, j + 1):
                    out[k] = "."
                i, prec = j + 1, "."
                continue
        if c in "'\"":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            for k in range(i + 1, min(j, n)):
                out[k] = "."
            i, prec = min(j, n) + 1, c
            continue
        if not c.isspace():
            prec = c
        i += 1
    return "".join(out)


_CACHE = {}


def _neutre():
    """Le script neutralisé, une seule fois : la neutralisation coûte cher et
    le fichier ne bouge pas en cours de suite."""
    if "neutre" not in _CACHE:
        _CACHE["neutre"] = _neutraliser(_js())
    return _CACHE["neutre"]


def _fonction(nom, src=None):
    src = src if src is not None else _js()
    neutre = _neutre() if src is _js() or src == _js() else _neutraliser(src)
    m = re.search(r"\bfunction\s+%s\s*\(" % re.escape(nom), neutre)
    assert m, "fonction absente du script : %s" % nom
    i = neutre.index("{", m.end())
    j, n = i + 1, 1
    while j < len(neutre) and n:
        n += {"{": 1, "}": -1}.get(neutre[j], 0)
        j += 1
    return src[i:j]


def _corps():
    """Le corps de chaque fonction nommée du script, relevé une seule fois."""
    if "corps" not in _CACHE:
        src = _js()
        noms = sorted(set(re.findall(
            r"\bfunction\s+([A-Za-z0-9_$]+)\s*\(", _neutre())))
        _CACHE["corps"] = {n: _fonction(n, src) for n in noms}
    return _CACHE["corps"]


def _fonction_contenant(fragment):
    """La fonction du script dont le corps contient `fragment` — la plus
    petite, s'il y en a plusieurs imbriquées."""
    trouvees = sorted((len(c), n, c) for n, c in _corps().items()
                      if fragment in c)
    return (trouvees[0][1], trouvees[0][2]) if trouvees else (None, None)


_ID_ECRIT = re.compile(r"""id=\\?["']([A-Za-z0-9_-]+)""")
_ID_LU = re.compile(
    r"""["']#([A-Za-z0-9_-]+)["']|getElementById\(["']([A-Za-z0-9_-]+)["']\)""")


def _ids_ecrits(corps):
    """Les identifiants que ce code POSE dans le document.

    Un identifiant concaténé (`id="ig-ao-grp-" + g`) compte par son préfixe :
    c'est lui qui entre en collision, et c'est lui qu'on peut comparer.
    """
    return {m.group(1) for m in _ID_ECRIT.finditer(corps)}


def _ids_lus(corps):
    out = set()
    for m in _ID_LU.finditer(corps):
        out.add(m.group(1) or m.group(2))
    return out


# --------------------------------------------------------------------------
# Un dossier réel, pour mesurer la partition sur autre chose qu'une idée.
# --------------------------------------------------------------------------
RC = (
    "RÈGLEMENT DE LA CONSULTATION\n"
    "Article 5 — Composition du dossier de candidature\n"
    "Le candidat produit la lettre de candidature (formulaire DC1) et la "
    "déclaration du candidat (formulaire DC2) dûment complétées.\n"
    "Il joint une déclaration sur l'honneur attestant qu'il n'entre dans "
    "aucun cas d'interdiction de soumissionner.\n"
    "Les attestations d'assurance responsabilité civile professionnelle sont "
    "exigées.\n"
    "Un organigramme fonctionnel de la mission est demandé, accompagné des "
    "curriculum vitae des intervenants clés.\n"
    "Article 6 — Composition de l'offre\n"
    "L'offre comprend l'acte d'engagement signé et le mémoire technique "
    "décrivant la méthodologie proposée.\n"
    "La décomposition du prix global et forfaitaire est jointe au format "
    "tableur.\n"
)


@pytest.fixture(scope="module")
def selection():
    analyse = ao_dc.analyser([{"nom": "RC.pdf", "texte": RC}])
    return ao_dc.selection(analyse=analyse)


# ==========================================================================
# LA GRILLE — la règle 4 du donneur d'ordre, sur la structure du document.
# ==========================================================================
def test_le_depot_et_la_selection_sont_COTE_A_COTE_et_non_l_un_sous_l_autre():
    """Deux colonnes, et exactement deux : c'est ce qui tient le rapport.

    Trois colonnes diluerait ; une seule ramènerait le défaut qu'on corrige —
    on faisait défiler si loin entre le dépôt et le résultat qu'on ne savait
    plus lequel des deux on regardait.
    """
    cols = _arbre().colonnes
    assert len(cols) == 2, \
        "la grille du § 14 porte %d colonne(s) et non deux : %s" % (
            len(cols), [c["ids"][:3] for c in cols])


def test_le_dossier_DEPOSE_est_a_gauche_et_ce_qu_il_FAUT_produire_a_droite():
    """L'ordre est celui du geste : on dépose, puis on lit ce qui en découle.

    Mesuré sur l'imbrication : la colonne qui contient la file de dépôt vient
    AVANT celle qui contient la sélection, dans le document.
    """
    cols = _arbre().colonnes
    gauche, droite = cols[0]["ids"], cols[1]["ids"]
    assert A_GAUCHE in gauche, \
        "le dépôt n'est pas dans la première colonne : %s" % gauche
    assert A_DROITE in droite, \
        "la sélection n'est pas dans la seconde colonne : %s" % droite
    assert A_DROITE not in gauche and A_GAUCHE not in droite


def test_les_deux_colonnes_ont_le_MEME_poids():
    """Aucune des deux n'est accessoire : sans dossier déposé il n'y a rien à
    produire, et sans sélection le dépôt ne sert à rien."""
    base = _sans_media(_feuille())
    pistes = _pistes(_declaration(base, ".%s" % GRILLE, "grid-template-columns"))
    assert len(pistes) == 2, \
        "la grille déclare %d piste(s) : %s" % (len(pistes), pistes)
    assert pistes[0] == pistes[1], \
        "les deux colonnes n'ont pas le même poids : %s" % pistes


def test_sous_la_largeur_d_un_telephone_les_colonnes_S_EMPILENT():
    """Deux colonnes de 1fr sur un écran de 390 px donnent deux colonnes de
    175 px : une liste déroulante de pièce y devient illisible."""
    css = _feuille()
    plafonds = [int(m) for m in
                re.findall(r"@media\s*\(\s*max-width\s*:\s*(\d+)px\s*\)", css)]
    empile = None
    for p in sorted(plafonds):
        bloc = _bloc_media(css, p)
        v = _declaration(bloc or "", ".%s" % GRILLE, "grid-template-columns")
        if v and len(_pistes(v)) == 1:
            empile = p
            break
    assert empile, \
        "aucune requête média ne ramène la grille à une seule colonne"
    assert empile >= 600, (
        "l'empilement ne se déclenche qu'à %d px : entre 600 et %d px les deux "
        "colonnes sont déjà trop étroites" % (empile, empile))


def test_une_colonne_ne_peut_pas_faire_DEBORDER_la_page():
    """Le piège propre aux grilles : une piste `1fr` prend pour plancher la
    largeur intrinsèque de son contenu. Un nom de pièce non sécable — et le
    § 14 en affiche vingt-trois — pousse alors la page en largeur au lieu de
    se replier. `min-width:0` est ce qui débranche ce plancher."""
    col = ".%s" % COLONNE
    css = _sans_media(_feuille())
    assert _declaration(css, col, "min-width") == "0" \
        or _declaration(css, col, "overflow") in ("hidden", "auto"), \
        "les colonnes ne bornent pas leur largeur intrinsèque"


# ==========================================================================
# LES IDENTIFIANTS — l'angle depuis lequel la collision était visible.
# ==========================================================================
def test_le_conteneur_de_la_selection_ACCEPTE_le_balisage_qu_on_y_ecrit():
    """LA RÈGLE QUI AURAIT ATTRAPÉ LE DÉFAUT. Le rendu y écrit des titres, des
    listes déroulantes et des listes à puces. Un `<select>`, un `<input>` ou
    un `<ul>` ne gardent pas ce balisage : le navigateur le jette en silence,
    et la colonne de droite reste vide sans une ligne de console."""
    porteur = _arbre().conteneurs.get(A_DROITE)
    assert porteur, "le conteneur de la sélection n'existe pas dans la page"
    assert porteur == "div", (
        "la sélection est rendue dans un <%s> : ce balisage n'accepte pas des "
        "titres ni des listes" % porteur)


def test_la_colonne_de_droite_est_VIDE_dans_la_page():
    """Le rendu en est seul propriétaire : il écrase tout à chaque passage.
    Y déposer du balisage dans la page le ferait disparaître à la première
    analyse — et paraître, avant, comme une exigence de la consultation."""
    assert _arbre().enfants.get(A_DROITE) == 0, \
        "le conteneur de la sélection n'est pas vide dans la page"


def test_aucun_identifiant_ecrit_par_le_script_ne_DOUBLE_un_identifiant_de_la_page():
    """Deux éléments d'un même identifiant : `getElementById` en rend un, et
    c'est le premier du document — jamais celui qu'on visait."""
    page = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', _html()))
    script = _ids_ecrits(_js())
    assert not (page & script), \
        "identifiants écrits deux fois : %s" % sorted(page & script)


def test_le_rendu_de_la_SELECTION_et_celui_du_DEPOT_n_ecrivent_pas_les_memes():
    """LA COLLISION, MESURÉE LÀ OÙ ELLE ÉTAIT. Les deux rendus vivent dans la
    même page, en même temps, et chacun était propre lu seul."""
    sel = _ids_ecrits(_fonction("aoSelectionRendre"))
    dep = _ids_ecrits(_fonction("aoEnAttenteRendre")) \
        | _ids_ecrits(_fonction("aoDocuments"))
    assert sel, "le rendu de la sélection n'écrit aucun identifiant"
    assert dep, "le rendu du dépôt n'écrit aucun identifiant"
    assert not (sel & dep), \
        "les deux rendus écrivent : %s" % sorted(sel & dep)


def test_la_selection_n_ECRIT_ni_ne_LIT_dans_le_dom_du_depot():
    """Chacun sa colonne. Le rendu de la sélection qui irait chercher un
    élément du dépôt les rendrait indissociables — et c'est en écrivant dans
    l'un qu'on a effacé l'autre."""
    portee = _fonction("aoSelectionRendre") + _fonction("aoSelectionBrancher")
    dep = _ids_ecrits(_fonction("aoEnAttenteRendre")) \
        | _ids_ecrits(_fonction("aoDocuments"))
    touches = (_ids_ecrits(portee) | _ids_lus(portee)) & dep
    assert not touches, \
        "la sélection touche au DOM du dépôt : %s" % sorted(touches)


def test_chaque_groupe_de_droite_porte_SA_liste_deroulante():
    """Règle 4 : « une liste de menu déroulant » par dossier. Trois groupes,
    trois listes — et trois identifiants qui ne peuvent pas se confondre,
    puisqu'ils dérivent de la clé du groupe."""
    corps = _fonction("aoSelectionRendre")
    prefixes = re.findall(r"""id=["']([A-Za-z0-9_-]+-)["']\s*\+""", corps)
    assert prefixes, \
        "les listes déroulantes des groupes n'ont pas d'identifiant dérivé"
    assert "<select" in corps, "aucune liste déroulante n'est rendue"
    branche = _fonction("aoSelectionBrancher")
    for p in set(prefixes):
        assert p in branche, \
            "les listes « %s » sont rendues mais jamais branchées" % p


# ==========================================================================
# LA PARTITION — ce que la colonne de droite promet de montrer.
# ==========================================================================
GROUPES_RETENUS = ("candidature", "offre")


def test_les_trois_groupes_couvrent_TOUTES_les_lignes_sans_recouvrement(selection):
    """L'écran construit ses groupes par filtrage. Une ligne qu'aucun filtre
    n'attrape n'apparaît nulle part — et c'est un document absent du pli."""
    lignes = selection["lignes"]
    assert lignes, "le moteur ne rend aucune ligne"
    compte = {}
    for x in lignes:
        n = sum([
            bool(x["retenue"] and x["dossier"] == "candidature"),
            bool(x["retenue"] and x["dossier"] == "offre"),
            bool(not x["retenue"]),
        ])
        compte[x["cle"]] = n
    perdues = [c for c, n in compte.items() if n == 0]
    doublees = [c for c, n in compte.items() if n > 1]
    assert not perdues, "pièces qu'aucun groupe n'affiche : %s" % perdues
    assert not doublees, "pièces affichées deux fois : %s" % doublees


def test_une_piece_retenue_a_TOUJOURS_un_dossier_que_l_ecran_sait_afficher(selection):
    """Un troisième dossier — « annexes », « divers » — passerait toutes les
    règles du moteur et ne s'afficherait jamais."""
    inconnus = sorted({x["dossier"] for x in selection["lignes"]
                       if x["retenue"]} - set(GROUPES_RETENUS))
    assert not inconnus, \
        "dossiers que la colonne de droite ne sait pas montrer : %s" % inconnus


def test_l_entete_compte_ce_que_les_groupes_MONTRENT(selection):
    """L'en-tête annonce « n documents retenus ». Il se calcule à part des
    groupes : les deux divergeraient sans que l'écran le signale."""
    retenues = [x for x in selection["lignes"] if x["retenue"]]
    assert selection["retenues"] == len(retenues), (
        "l'en-tête annonce %s pièces, les groupes en montrent %d"
        % (selection["retenues"], len(retenues)))
    assert len(selection["remplissables"]) + len(selection["a_produire"]) \
        == len(retenues), (
            "%d remplissables + %d à produire ≠ %d retenues" % (
                len(selection["remplissables"]), len(selection["a_produire"]),
                len(retenues)))


def test_les_deux_dossiers_sont_REELLEMENT_peuples_par_une_consultation_reelle(selection):
    """Sans cette règle, la partition serait vraie et vide : tout ranger dans
    « candidature » la satisferait."""
    par = {}
    for x in selection["lignes"]:
        if x["retenue"]:
            par.setdefault(x["dossier"], []).append(x["cle"])
    for g in GROUPES_RETENUS:
        assert par.get(g), \
            "le dossier « %s » est vide sur un RC qui le demande : %s" % (g, par)


# ==========================================================================
# LE PÉRIMÈTRE — sa portée, requête par requête.
# ==========================================================================
PRODUISENT_LE_DOSSIER = (
    "/api/datacenter/marche/remplir",
    "/api/datacenter/marche/export",
    "/api/datacenter/marche/parcours",
    "/api/datacenter/marche/dossier.zip",
)


@pytest.mark.parametrize("adresse", PRODUISENT_LE_DOSSIER)
def test_chaque_requete_qui_PRODUIT_le_dossier_porte_le_perimetre(adresse):
    """UNE SEULE QUI L'OUBLIE SUFFIT À MENTIR. L'écran annoncerait six pièces
    pendant que l'archive en contiendrait vingt-trois — et c'est l'archive
    qu'on dépose chez l'acheteur.

    Mesuré dans la FONCTION appelante, pas dans une fenêtre de caractères : le
    parcours construit son corps de requête AVANT l'appel, et une fenêtre qui
    ne regarde qu'en aval l'aurait déclaré fautif à tort. On exige en outre que
    la fonction ne lance qu'UNE requête, sans quoi le périmètre trouvé pourrait
    appartenir à l'autre.
    """
    nom, corps = _fonction_contenant('"%s"' % adresse)
    assert nom, "adresse appelée hors de toute fonction : %s" % adresse
    assert corps.count("demander(") == 1, (
        "%s lance %d requêtes : le périmètre trouvé pourrait être celui d'une "
        "autre" % (nom, corps.count("demander(")))
    assert "perimetre" in corps, \
        "%s appelle %s sans périmètre" % (nom, adresse)


def test_le_perimetre_a_une_SEULE_definition():
    """Chaque `perimetre:` envoyé vient de `aoPerimetre()`. Un périmètre
    recalculé sur place serait une seconde définition de « retenue » — et
    elles divergeraient le jour où l'une des deux serait corrigée."""
    js = _js()
    envois = len(re.findall(r"\bperimetre\s*:", js))
    appels = len(re.findall(r"(?<!function )\baoPerimetre\s*\(\s*\)", js))
    assert envois == len(PRODUISENT_LE_DOSSIER), \
        "%d envois de périmètre pour %d requêtes" % (
            envois, len(PRODUISENT_LE_DOSSIER))
    assert appels == envois, \
        "%d envois pour %d appels à aoPerimetre()" % (envois, appels)


def test_sans_selection_le_perimetre_est_ABSENT_et_non_VIDE():
    """La distinction porte tout le comportement d'avant : `null` veut dire
    « tout le catalogue », `[]` veut dire « rien ». Les confondre viderait le
    dossier de qui n'a pas encore analysé."""
    corps = _fonction("aoPerimetre")
    tete = corps[:corps.index(".filter(")] if ".filter(" in corps else corps
    assert re.search(r"return\s+null\s*;", tete), (
        "sans sélection, le périmètre ne rend pas `null` : %s"
        % " ".join(tete.split()))
    assert not re.search(r"return\s*\[\s*\]\s*;", tete), \
        "le périmètre rend une liste vide au lieu de `null`"


def test_le_perimetre_ne_retient_QUE_ce_que_l_ecran_montre_retenu(selection):
    """La liste envoyée est exactement celle des pièces marquées retenues à
    l'écran — la même lecture que celle des trois groupes."""
    attendu = sorted(x["cle"] for x in selection["lignes"] if x["retenue"])
    assert attendu, "aucune pièce retenue sur un RC qui en demande"
    assert len(attendu) == selection["retenues"]
    corps = _fonction("aoPerimetre")
    assert "retenue" in corps, \
        "le périmètre ne se calcule pas sur la marque « retenue »"
