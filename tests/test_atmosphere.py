"""L'ATMOSPHÈRE DU FOND : deux terres, un bleu encré, un satiné — et la lisibilité.

CE QUI A DÉCLENCHÉ CE FICHIER. Une demande : faire fluctuer les couleurs, style
papier couché, orange terre et bleu, avec des blobs qui dérivent. Trois défauts
sont apparus en la préparant, et aucun ne se voyait à la lecture.

PREMIER DÉFAUT : UN NOM QUI DISAIT UNE AUTRE COULEUR. `--blob-turquoise`
contenait `rgba(255,140,80)` — de l'orange, depuis l'origine. On lit le nom, on
ne recalcule pas la teinte : une variable ainsi nommée fait prendre une décision
sur une couleur qu'elle n'a pas. La règle compare désormais la teinte calculée à
la famille que le nom annonce.

DEUXIÈME DÉFAUT : UNE COUCHE QUI SERAIT MORTE SUR LA PAGE VISÉE. Six pages du
site — dont l'accueil, précisément celle pour laquelle le satiné était demandé —
redéclarent `body{background-image}` EN ENTIER. Posé dans le fond du corps, le
satiné y aurait disparu sans un mot. Il est donc sur `html::after`, et la règle
vérifie que la liste des pages qui écrasent leur fond n'est pas vide : sans
cela, elle passerait pour une raison qui n'existe plus.

TROISIÈME DÉFAUT, ET C'EST LE PLUS SÉRIEUX : « CONTRASTE ÉLEVÉ (AA) » ÉTAIT UNE
AFFIRMATION. Elle est écrite dans le commentaire de l'accueil, et rien, dans les
cent fichiers de tests, ne calculait le moindre rapport de contraste. Or un halo
posé sur la partie claire du dégradé éclaircit le fond et fait chuter le
contraste du texte.

  MESURÉ, SUR LE MODÈLE DÉCRIT PLUS BAS :
    · aux valeurs d'origine   : 3,02:1 (corps) · 2,56:1 (accueil) · 2,64:1
    · première version d'ici  : 2,57:1 · 2,21:1 · 2,29:1   ← une aggravation
    · deuxième version        : 3,33:1 · 2,76:1 · 2,85:1
    · valeurs retenues        : 3,45:1 · 2,98:1 · 3,05:1

QUATRIÈME DÉFAUT, ET IL EST DE CE FICHIER : UNE RÈGLE VERTE PENDANT QUE L'EFFET
ÉTAIT INVISIBLE. `test_la_couleur_fluctue_et_pas_seulement_la_position`
vérifiait que `opacity` et `hue-rotate` FIGURENT dans les images-clés. C'était le
cas, et l'on ne voyait rien : l'excursion .74→1 sur une couche à faible alpha
donnait 1,8 à 3,9 ΔE entre les deux extrêmes — au seuil de perception sur une
frontière nette, très en dessous sur un dégradé de 58vmax flouté à 90 px. Et à
90-115 s le cycle, l'écart avançait de 0,2 ΔE par seconde, que l'œil absorbe en
s'adaptant. Le rendu était objectivement PLUS DISCRET qu'avant la modification.

Une règle qui constate une propriété SYNTAXIQUE passe pour une raison sans
rapport avec ce qu'elle prétend. Celles-ci MESURENT : écart perceptuel entre les
extrêmes d'une animation, écart par seconde, écart de chaque halo au fond.

LA SORTIE EST L'ISO-LUMINANCE. Le contraste ne souffre pas de la COULEUR d'un
halo mais de sa CLARTÉ. Le bleu ardoise `rgb(28,64,102)` a une luminance de
0,049 contre 0,050 pour le fond dominant : invisible en clarté, ΔE 24 en chroma.
D'où des alphas deux fois plus hauts, une couleur franche, ET un contraste qui
monte encore.

CE QUE CES RÈGLES TIENNENT, ET CE QU'ELLES NE TIENNENT PAS. Elles tiennent la
NON-RÉGRESSION : le pire composite ne doit plus jamais redescendre sous les
valeurs retenues, qui sont meilleures que toutes les précédentes. Elles NE
PEUVENT PAS annoncer l'AA, parce que
l'écart restant ne vient pas des halos mais des teintes claires du dégradé
lui-même — `#985B2C` en bas de l'accueil ne donne que 4,80:1 À NU, avant tout
halo. Le combler suppose d'assombrir ces arrêts de dégradé : c'est une décision
d'identité visuelle, elle n'a pas été demandée, et l'inventer ici l'aurait faite
en douce. Elle est signalée, chiffrée, et laissée ouverte.
"""
import io
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

CSS = io.open(os.path.join(ICI, 'styles.css'), encoding='utf-8').read()
ACCUEIL = io.open(os.path.join(ICI, 'index.html'), encoding='utf-8').read()

# Les familles de teintes, en degrés. Un nom hors de cette table fait échouer :
# une couleur nouvelle demande une décision, pas un ajout silencieux.
FAMILLES = {
    'terre': (18, 48),      # ocre chaud
    'brique': (0, 22),      # rouge terreux
    'bleu': (185, 250),     # encre froide
}

# LE PIRE COMPOSITE ADMIS, PAR FOND DE RÉFÉRENCE. Redescendre est interdit ;
# monter demande de mettre ces nombres à jour, ce qui est le seul moyen de rendre
# une amélioration visible plutôt que de la laisser s'éroder.
CONTRASTE_PLANCHER = {'#9C3C20': 3.42, '#985B2C': 2.95, '#B04824': 3.02}

# Le texte le plus exposé : `--muted` est plus sombre que `--ink`, donc son
# contraste sur un fond clair est le plus faible des deux.
TEXTE = '#E6D5C6'

# Le fond dominant du site, contre lequel se mesure la présence d'un halo.
FOND_DOMINANT = '#6E2A18'

# LES SEUILS DE PERCEPTION, ET POURQUOI ILS SONT CE QU'ILS SONT.
# ΔE ≈ 2 est le seuil sur une FRONTIÈRE NETTE. Un halo de 58vmax flouté à 90 px
# n'a pas de frontière : l'écart s'étale sur des centaines de pixels et l'œil
# l'intègre. Les seuils ci-dessous sont donc plus exigeants que le seuil
# théorique, et ils correspondent à ce qui a été mesuré comme réellement visible.
DE_HALO_MINIMAL = 6.0        # un halo qu'on ne distingue pas du fond n'existe pas
DE_FLUCTUATION_MINIMALE = 3.0  # entre les deux extrêmes d'une animation
DE_PAR_SECONDE_MINIMAL = 0.15  # en dessous, l'adaptation de l'œil absorbe tout
DE_PAR_SECONDE_MAXIMAL = 1.5   # au-dessus, ce n'est plus une dérive, c'est un clignotement

# L'écart de CLARTÉ admis entre un halo et le fond. C'est lui qui coûte le
# contraste ; le borner est ce qui permet des alphas élevés.
ECART_CLARTE_MAXIMAL = 30.0
# Et au moins un halo doit être franchement iso-luminant : c'est celui qui porte
# la couleur nouvelle sans rien coûter.
ECART_CLARTE_ISO = 5.0


# ── Couleur : calculs ──────────────────────────────────────────────────────

def _rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _teinte(r, g, b):
    import colorsys
    return colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)[0] * 360.0


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _lum(c):
    return .2126 * _lin(c[0]) + .7152 * _lin(c[1]) + .0722 * _lin(c[2])


def _lab(c):
    """sRGB → Lab (D65). C'est dans cet espace qu'une différence de couleur se
    compare à ce que l'œil perçoit ; en RGB, deux écarts numériques égaux ne se
    voient pas également."""
    r, g, b = [_lin(x) for x in c]
    X = r * .4124 + g * .3576 + b * .1805
    Y = r * .2126 + g * .7152 + b * .0722
    Z = r * .0193 + g * .1192 + b * .9505
    f = lambda t: t ** (1 / 3.) if t > 0.008856 else (7.787 * t + 16 / 116.)
    fx, fy, fz = f(X / .95047), f(Y / 1.0), f(Z / 1.08883)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def ecart_percu(a, b):
    """ΔE : l'écart tel qu'il se voit, et non tel qu'il s'écrit."""
    import math
    return math.dist(_lab(a), _lab(b))


def contraste(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + .05) / (min(la, lb) + .05)


def _sur(fond, couche, alpha):
    return tuple(couche[i] * alpha + fond[i] * (1 - alpha) for i in range(3))


def _variables(bloc=CSS):
    """Chaque déclaration `--blob-<nom>:rgba(...)` du fichier, variantes comprises."""
    out = []
    for nom, r, g, b, a in re.findall(
            r'--blob-([a-z]+)\s*:\s*rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)',
            bloc):
        out.append((nom, (int(r), int(g), int(b)), float(a)))
    return out


def _satine():
    """Les couches du satiné, lues dans la règle `html::after`."""
    bloc = CSS[CSS.index('html::after{'):]
    bloc = bloc[:bloc.index('}')]
    return [((int(r), int(g), int(b)), float(a)) for r, g, b, a in
            re.findall(r'rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)', bloc)]


def _pire(base_hex, alphas_par_nom):
    """LE MODÈLE, ET IL EST ÉCRIT PARCE QU'UN CHIFFRE SANS MODÈLE NE SE COMPARE
    À RIEN. Le halo qui éclaircit le plus, à son alpha nominal, posé sur l'arrêt
    le plus clair du dégradé, puis le satiné par-dessus.

    Les trois halos ne sont PAS empilés : ils sont ancrés à trois bords opposés,
    et les additionner décrirait une géométrie qui n'existe pas. Les couches
    radiales propres à chaque page sont hors modèle — positionnées, souvent hors
    cadre, et recouvertes par le voile sombre du bandeau."""
    base = _rgb(base_hex)
    pire = 99.0
    for _, couleur, alpha in alphas_par_nom:
        f = _sur(base, couleur, alpha)
        for couleur_s, alpha_s in _satine():
            f = _sur(f, couleur_s, alpha_s)
        pire = min(pire, contraste(_rgb(TEXTE), f))
    return pire


# ── 1. Le nom dit la couleur ───────────────────────────────────────────────

def test_chaque_variable_de_halo_porte_la_teinte_que_son_nom_annonce():
    """LA RÈGLE QUI AURAIT ATTRAPÉ `--blob-turquoise: rgba(255,140,80)`."""
    vus = _variables()
    assert vus, "aucune variable de halo trouvée : la règle ne garde plus rien"
    for nom, (r, g, b), _ in vus:
        assert nom in FAMILLES, (
            "« --blob-%s » n'appartient à aucune famille déclarée : une couleur "
            "nouvelle demande une décision, pas un ajout silencieux" % nom)
        lo, hi = FAMILLES[nom]
        h = _teinte(r, g, b)
        assert lo <= h <= hi, (
            "« --blob-%s » vaut rgb(%d,%d,%d), de teinte %.0f° — hors de la "
            "famille annoncée (%d–%d°). Un nom qui dit une autre couleur que sa "
            "valeur vaut moins que pas de nom." % (nom, r, g, b, h, lo, hi))


def test_les_trois_familles_sont_toutes_servies():
    """Deux terres et un bleu : si une famille disparaissait, l'atmosphère
    redeviendrait monochrome sans que rien ne le dise."""
    familles = {nom for nom, _, _ in _variables()}
    assert familles == set(FAMILLES), familles


def _chroma(c):
    """L'intensité colorée en Lab. LA SATURATION HSV MESURAIT AUTRE CHOSE : le
    bleu ardoise y monte à 0,73 contre 0,58 pour l'ancien, alors qu'il est
    visiblement PLUS sourd — HSV divise par la composante maximale, donc une
    couleur sombre paraît saturée. La chroma, elle, dit ce qu'on voit."""
    import math
    _, a, b = _lab(c)
    return math.hypot(a, b)


def test_le_bleu_reste_minoritaire_et_moins_vif_que_le_cyan_de_marque():
    """Le cyan de l'interface sur fond brique donnerait du néon. Le bleu de
    l'atmosphère doit rester une encre — et la référence n'est pas un seuil
    inventé, c'est `--cyan` lui-même : celui qu'on ne veut pas."""
    m = re.search(r'--cyan\s*:\s*(#[0-9A-Fa-f]{6})', CSS)
    assert m, "--cyan a disparu : la référence de comparaison n'existe plus"
    plafond = _chroma(_rgb(m.group(1)))
    bleus = [(c, a) for nom, c, a in _variables() if nom == 'bleu']
    assert bleus
    for c, _ in bleus:
        assert _chroma(c) < plafond, (
            "le bleu de l'atmosphère (chroma %.1f) est aussi vif que le cyan de "
            "l'interface (%.1f) : c'est un néon, pas une encre"
            % (_chroma(c), plafond))
    terres = [1 for nom, _, _ in _variables() if nom in ('terre', 'brique')]
    assert len(terres) >= 2 * len(bleus), "le bleu n'est plus minoritaire"


def test_la_variante_couchant_redefinit_les_trois():
    """Une variante qui en oublie une retombe sur la valeur de base — en
    silence, et avec la mauvaise couleur."""
    # DEUX RÈGLES PORTENT CE SÉLECTEUR : l'une pose le fond, l'autre les
    # variables. Prendre la première venue faisait échouer la recherche sur un
    # bloc qui n'a jamais eu à les contenir.
    blocs = [CSS[m.end():CSS.index('}', m.end())]
             for m in re.finditer(r'body\[data-fond="couchant"\]\s*\{', CSS)]
    porteurs = [b for b in blocs if '--blob-' in b]
    assert len(porteurs) == 1, "%d bloc(s) déclarent les halos du couchant" % len(porteurs)
    assert {nom for nom, _, _ in _variables(porteurs[0])} == set(FAMILLES), porteurs[0]


# ── 2. Le satiné survit aux pages qui redéclarent leur fond ────────────────

def _pages_qui_ecrasent_le_fond():
    """Relue du dépôt, jamais recopiée : une liste figée cesserait de décrire
    le site au premier ajout de page."""
    out = []
    for f in sorted(os.listdir(ICI)):
        if not f.endswith('.html'):
            continue
        h = io.open(os.path.join(ICI, f), encoding='utf-8').read()
        for m in re.finditer(r'\bbody\s*\{(.*?)\}', h, re.S):
            if 'background-image' in m.group(1):
                out.append(f)
                break
    return out


def test_des_pages_redeclarent_bien_leur_fond():
    """SANS CELA, LA RÈGLE SUIVANTE PASSERAIT POUR UNE RAISON QUI N'EXISTE
    PLUS. C'est ce risque qui justifie de poser le satiné ailleurs."""
    pages = _pages_qui_ecrasent_le_fond()
    assert pages, "plus aucune page n'écrase le fond du corps : la règle est à revoir"
    assert 'index.html' in pages, (
        "l'accueil n'écrase plus son fond : vérifier que le satiné y est bien "
        "encore nécessaire sur un pseudo-élément")


def test_le_satine_se_voit():
    """LA MUTATION QUI A SURVÉCU. Ramener le reflet de .045 à .008 ne faisait
    tomber aucune règle : le satiné pouvait devenir invisible sans que rien ne
    le dise, alors que c'est lui qui distingue un papier couché d'un aplat mat.
    Le même défaut que pour les halos, à un étage de plus — vérifier la présence
    d'une couche ne dit rien de ce qu'elle produit."""
    fond = _rgb(FOND_DOMINANT)
    f = fond
    for couleur, alpha in _satine():
        f = _sur(f, couleur, alpha)
    ecart = ecart_percu(fond, f)
    assert ecart >= 5.0, (
        "le satiné ne déplace le fond que de %.1f ΔE : la surface est mate, et "
        "le papier couché n'existe que dans le commentaire" % ecart)


def test_le_satine_est_porte_par_un_pseudo_element_et_non_par_le_fond_du_corps():
    assert 'html::after{' in CSS, "le satiné a disparu"
    couches = _satine()
    assert len(couches) >= 2, "le satiné n'a plus son reflet et son grain"
    # Le grain et le reflet ne doivent pas être passés dans body{...}, où six
    # pages les effaceraient.
    i = CSS.index('body{')
    corps = CSS[i:CSS.index('}', i)]
    assert 'repeating-linear-gradient' not in corps, (
        "le grain du satiné est dans le fond du corps : il disparaîtra sur les "
        "pages qui le redéclarent — %s" % ', '.join(_pages_qui_ecrasent_le_fond()))


# ── 3. Les trajets, et la fluctuation ──────────────────────────────────────

def _etapes(nom):
    i = CSS.index('@keyframes %s{' % nom)
    j = CSS.index('\n}', i)
    return CSS[i:j]


@pytest.mark.parametrize('nom', ['blobA', 'blobB', 'blobC'])
def test_chaque_trajet_est_bidirectionnel(nom):
    """« De haut en bas ET de gauche à droite » : les anciennes courbes étaient
    des diagonales, ce qui donnait trois glissements parallèles."""
    bloc = _etapes(nom)
    dx = [abs(float(v)) for v in re.findall(r'translate\((-?[\d.]+)vw', bloc)]
    dy = [abs(float(v)) for v in re.findall(r'translate\([^,]+,\s*(-?[\d.]+)vh', bloc)]
    assert dx and max(dx) >= 20, "%s ne parcourt pas l'horizontale (%s)" % (nom, dx)
    assert dy and max(dy) >= 20, "%s ne parcourt pas la verticale (%s)" % (nom, dy)


# Quel halo porte quelle animation. Le rattachement se lit dans la feuille : le
# recopier ferait dériver la règle du code qu'elle mesure.
def _halo_de(anim):
    m = re.search(r'background:radial-gradient\([^;]*var\(--blob-(\w+)\)[^;]*\);\s*\n?\s*'
                  r'animation:%s ' % anim, CSS)
    if not m:
        m = re.search(r'var\(--blob-(\w+)\)[^}]*?animation:%s ' % anim, CSS, re.S)
    assert m, "aucun halo ne porte l'animation %s" % anim
    return m.group(1)


def _couleur_du_halo(nom):
    for n, c, a in _variables(CSS[:CSS.index('body[data-fond')]):
        if n == nom:
            return c, a
    raise AssertionError("halo %s introuvable" % nom)


@pytest.mark.parametrize('nom', ['blobA', 'blobB', 'blobC'])
def test_la_couleur_fluctue_ASSEZ_pour_se_voir(nom):
    """LA RÈGLE QUI ÉTAIT VERTE PENDANT QUE L'EFFET ÉTAIT INVISIBLE.

    Elle se contentait de trouver `opacity` et `hue-rotate` dans les images-clés.
    Les deux y étaient, et l'excursion .74→1 sur une couche à faible alpha ne
    déplaçait la couleur que de 1,8 à 3,9 ΔE — sous le seuil, sur un dégradé
    aussi large. Constater une propriété syntaxique ne mesure rien : on calcule
    désormais l'écart entre les deux extrêmes, composités sur le fond."""
    bloc = _etapes(nom)
    assert 'opacity' in bloc, "%s ne fait varier que sa position" % nom
    assert 'hue-rotate' in bloc, "%s ne fait pas varier sa teinte" % nom
    opacites = [float(o) for o in re.findall(r'opacity:([\d.]+)', bloc)]
    assert len(opacites) >= 2, "%s n'a qu'une opacité : rien ne fluctue" % nom
    couleur, alpha = _couleur_du_halo(_halo_de(nom))
    fond = _rgb(FOND_DOMINANT)
    ecart = ecart_percu(_sur(fond, couleur, alpha * min(opacites)),
                        _sur(fond, couleur, alpha * max(opacites)))
    assert ecart >= DE_FLUCTUATION_MINIMALE, (
        "%s : entre ses deux extrêmes la couleur ne bouge que de %.1f ΔE "
        "(minimum %.1f). L'animation existe et ne se voit pas."
        % (nom, ecart, DE_FLUCTUATION_MINIMALE))


@pytest.mark.parametrize('nom', ['blobA', 'blobB', 'blobC'])
def test_la_fluctuation_avance_assez_vite_pour_etre_enregistree(nom):
    """UNE DÉRIVE QU'ON NE PEUT PAS VOIR N'EST PAS SUBTILE, ELLE EST ABSENTE.
    À 90-115 s le cycle, l'écart avançait de 0,2 ΔE par seconde : l'œil s'adapte
    au fur et à mesure et n'enregistre rien. La borne haute existe aussi — une
    dérive n'est pas un clignotement."""
    bloc = _etapes(nom)
    duree = re.search(r'animation:%s (\d+)s' % nom, CSS)
    assert duree, "%s n'est rattachée à aucune durée" % nom
    demi_cycle = int(duree.group(1)) / 2.0
    opacites = [float(o) for o in re.findall(r'opacity:([\d.]+)', bloc)]
    couleur, alpha = _couleur_du_halo(_halo_de(nom))
    fond = _rgb(FOND_DOMINANT)
    ecart = ecart_percu(_sur(fond, couleur, alpha * min(opacites)),
                        _sur(fond, couleur, alpha * max(opacites)))
    vitesse = ecart / demi_cycle
    assert vitesse >= DE_PAR_SECONDE_MINIMAL, (
        "%s avance de %.2f ΔE/s (minimum %.2f) : sur %s s, l'adaptation de l'œil "
        "absorbe le changement" % (nom, vitesse, DE_PAR_SECONDE_MINIMAL, duree.group(1)))
    assert vitesse <= DE_PAR_SECONDE_MAXIMAL, (
        "%s avance de %.2f ΔE/s : ce n'est plus une dérive de fond" % (nom, vitesse))


@pytest.mark.parametrize('halo', sorted(FAMILLES))
def test_chaque_halo_se_distingue_du_fond(halo):
    """Un halo qu'on ne distingue pas du fond n'existe pas. La brique est la
    plus discrète des trois — un rouge sur un rouge — et c'est assumé ; encore
    faut-il qu'elle passe le seuil."""
    couleur, alpha = _couleur_du_halo(halo)
    fond = _rgb(FOND_DOMINANT)
    ecart = ecart_percu(fond, _sur(fond, couleur, alpha))
    assert ecart >= DE_HALO_MINIMAL, (
        "« %s » ne s'écarte du fond que de %.1f ΔE (minimum %.1f) : il est posé "
        "et on ne le voit pas" % (halo, ecart, DE_HALO_MINIMAL))


def test_les_halos_changent_la_chroma_et_non_la_clarte():
    """C'EST TOUT L'ARBITRAGE, ET IL SE VÉRIFIE. Le contraste du texte ne souffre
    pas de la couleur d'un halo mais de sa CLARTÉ. Borner l'écart de clarté est
    ce qui permet des alphas assez hauts pour que la couleur se voie ; et au
    moins un halo doit être franchement iso-luminant — c'est celui qui porte la
    teinte nouvelle sans rien coûter."""
    fond = _lab(_rgb(FOND_DOMINANT))[0]
    ecarts = {}
    for halo in FAMILLES:
        couleur, _ = _couleur_du_halo(halo)
        ecarts[halo] = abs(_lab(couleur)[0] - fond)
    for halo, e in ecarts.items():
        assert e <= ECART_CLARTE_MAXIMAL, (
            "« %s » s'écarte de %.1f en clarté (maximum %.1f) : il éclaircit le "
            "fond, et c'est le contraste du texte qui paie" % (halo, e, ECART_CLARTE_MAXIMAL))
    assert min(ecarts.values()) <= ECART_CLARTE_ISO, (
        "aucun halo n'est iso-luminant (écarts : %s) : sans lui, monter les "
        "alphas se paie en lisibilité"
        % ', '.join('%s %.1f' % kv for kv in sorted(ecarts.items())))


@pytest.mark.parametrize('nom', ['blobA', 'blobB', 'blobC'])
def test_chaque_etape_qui_pose_un_filtre_garde_le_flou(nom):
    """`filter` REMPLACE la propriété entière. Une étape qui ne poserait que
    `hue-rotate()` supprimerait le `blur(90px)` — et l'on verrait trois disques
    nets à la place des halos."""
    for etape in re.findall(r'filter:([^;}]+)', _etapes(nom)):
        assert 'blur(' in etape, (
            "%s : une étape pose un filtre sans flou → « %s »" % (nom, etape.strip()))


def test_toute_animation_de_fond_sarrete_en_mouvement_reduit():
    """La liste est DÉRIVÉE de la feuille, pas énumérée à la main : un
    quatrième élément animé échapperait sinon au bloc en silence — c'est
    exactement ce qui a failli arriver au satiné."""
    animes = set()
    for sel, corps in re.findall(r'\n((?:html|body)::(?:before|after))\{(.*?)\n\}', CSS, re.S):
        if 'animation:' in corps:
            animes.add(sel)
    assert animes, "aucun pseudo-élément racine animé : la règle ne garde rien"
    i = CSS.index('@media (prefers-reduced-motion: reduce){')
    bloc = CSS[i:CSS.index('\n}', i)]
    for sel in sorted(animes):
        assert sel in bloc, (
            "%s est animé mais n'est pas arrêté en mouvement réduit" % sel)


def test_le_mouvement_reste_une_derive():
    """« Subtil » veut dire qu'on ne surprend pas le regard — pas qu'on ne voit
    rien. La borne était à soixante secondes minimum, ce qui garantissait
    l'imperceptibilité au lieu de la douceur. La lenteur se juge maintenant en
    ΔE par seconde (règle voisine) ; il reste ici une borne basse de durée, pour
    qu'aucune animation de fond ne devienne un mouvement qu'on suit du regard."""
    durees = [int(d) for d in re.findall(r'animation:(?:blob[ABC]|satine) (\d+)s', CSS)]
    assert durees, "plus aucune animation de fond"
    for d in durees:
        assert d >= 20, "une animation de fond dure %s s : c'est un mouvement, pas une dérive" % d


def test_les_cycles_sont_premiers_entre_eux():
    """Trois durées à multiples communs ramèneraient périodiquement la scène
    dans la même configuration, et la dérive se mettrait à se répéter."""
    import math
    durees = [int(d) for d in re.findall(r'animation:blob[ABC] (\d+)s', CSS)]
    assert len(durees) == 3, durees
    for i in range(3):
        for j in range(i + 1, 3):
            assert math.gcd(durees[i], durees[j]) == 1, (
                "les cycles %ds et %ds partagent un diviseur : la scène se "
                "répétera" % (durees[i], durees[j]))


# ── 4. La lisibilité, calculée ─────────────────────────────────────────────

@pytest.mark.parametrize('base', sorted(CONTRASTE_PLANCHER))
def test_le_pire_composite_ne_redescend_pas(base):
    """NON-RÉGRESSION, ET C'EST CE QUE CETTE RÈGLE PEUT HONNÊTEMENT TENIR.
    Voir l'en-tête : l'écart à l'AA vient des arrêts clairs du dégradé, pas des
    halos, et le combler est une décision d'identité visuelle qui n'a pas été
    prise ici."""
    obtenu = _pire(base, _variables(CSS[:CSS.index('body[data-fond')]))
    plancher = CONTRASTE_PLANCHER[base]
    assert obtenu >= plancher, (
        "sur %s, le pire composite tombe à %.2f:1 alors que %.2f:1 est acquis : "
        "les halos ou le satiné ont été éclaircis" % (base, obtenu, plancher))


def test_l_attenuation_a_bien_ameliore_l_existant():
    """Le point de comparaison : les alphas d'origine (.30/.28/.24) sans satiné.
    Si la nouvelle atmosphère était moins lisible que l'ancienne, elle serait à
    refuser quelle que soit sa beauté."""
    avant = {}
    for base in CONTRASTE_PLANCHER:
        f = _sur(_rgb(base), (255, 185, 120), .30)
        avant[base] = contraste(_rgb(TEXTE), f)
    for base in CONTRASTE_PLANCHER:
        assert CONTRASTE_PLANCHER[base] > avant[base], (
            "sur %s, l'atmosphère retenue (%.2f) n'est pas meilleure que "
            "l'ancienne (%.2f)" % (base, CONTRASTE_PLANCHER[base], avant[base]))


def test_le_voile_du_bandeau_protege_le_titre():
    """Le seul endroit où l'AA est réellement tenue, et c'est le voile sombre
    de `.fond-hero::after` qui la tient — pas le dégradé."""
    i = CSS.index('.fond-hero::after{')
    bloc = CSS[i:CSS.index('}', i)]
    voiles = re.findall(r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)', bloc)
    assert voiles, "le voile du bandeau a disparu"
    pic = max(float(a) for *_, a in voiles)
    assert pic >= .40, (
        "le voile ne dépasse plus 40 %% d'opacité (%.2f) : le titre n'est plus "
        "protégé de l'affiche ni de la vidéo posées dessous" % pic)


# ── 5. La grille a reculé ──────────────────────────────────────────────────

@pytest.mark.parametrize('nom,texte,seuil', [
    ('styles.css', CSS, .12),
    ('index.html', ACCUEIL, .10),
], ids=['styles.css', 'index.html'])
def test_la_grille_est_passee_derriere_le_satine(nom, texte, seuil):
    """Le papier couché est lisse : une trame de papier millimétré tire dans
    l'autre sens."""
    alphas = [float(a) for a in re.findall(
        r'linear-gradient\((?:90deg,\s*)?rgba\(168,\s*104,\s*68,\s*([\d.]+)\)\s*1px', texte)]
    assert alphas, "la grille a disparu de %s : elle devait reculer, pas partir" % nom
    assert max(alphas) <= seuil, (
        "%s : la grille est à %.2f d'opacité, au-dessus du seuil %.2f"
        % (nom, max(alphas), seuil))


def test_l_accueil_porte_l_echo_froid():
    """Sans lui, l'accueil serait la seule page à ne pas dire le bleu."""
    i = ACCUEIL.index('background-image:')
    bloc = ACCUEIL[i:ACCUEIL.index('background-size:', i)]
    froids = [t for t in re.findall(r'rgba\((\d+),\s*(\d+),\s*(\d+),', bloc)
              if int(t[2]) > int(t[0])]
    assert froids, "le ciel de l'accueil ne porte aucune nuée froide"


def test_les_couches_et_leurs_tailles_se_correspondent():
    """Une couche ajoutée sans sa taille décale toute la liste : la grille se
    met à dimensionner un dégradé, en silence."""
    m = re.search(r'background-image:(.*?);\s*\n\s*background-size:(.*?);', ACCUEIL, re.S)
    assert m
    couches = [l for l in m.group(1).split('\n') if 'gradient' in l]
    tailles = [t.strip() for t in m.group(2).split(',')]
    assert len(couches) == len(tailles), (
        "%d couches pour %d tailles" % (len(couches), len(tailles)))
