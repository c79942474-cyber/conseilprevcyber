# -*- coding: utf-8 -*-
"""L'AVANCEMENT SE VOIT — bleu tant que ça reste à faire, vert battant une fois
validé ou calculé.

POURQUOI CE FICHIER EXISTE. Le dispositif d'accompagnement de Sentinel parlait
trois langues à la fois : le parcours guidé encadrait d'AMBRE ce qui restait à
faire, le guide d'étapes le disait en ambre aussi mais peignait le fait en
TEAL, et les blocs de page ne disaient rien du tout — fermé, le guide fermait
l'information avec lui. Trois vocabulaires pour un seul état, et une page qui
redevenait muette dès qu'on refermait le panneau.

CE QUI EST ÉPROUVÉ ICI, ET CE QUI NE L'EST PAS. Ces règles ne vérifient pas
qu'un mot-clé figure quelque part — c'est le défaut qui a laissé passer, deux
fois cette semaine, un effet invisible sous une règle verte. Elles MESURENT :

  · le contraste composé du bleu et du vert sur les quatre fonds du site ;
  · l'écart perceptuel entre eux, et avec le cyan de marque ;
  · le contraste À CHAQUE PHASE du battement — c'est cette règle-là qui a
    trouvé que ma flèche tombait à 2,2:1 au creux de son cycle ;
  · la cadence, en éclats par seconde, contre le seuil de photosensibilité ;
  · le NOMBRE de flèches mises en avant, en exécutant le rendu sous Node.

LA GRAMMAIRE EST DÉFINIE UNE FOIS. Trois modules l'emploient ; trois copies de
la même seconde et demie auraient divergé au premier réglage. Une règle vérifie
qu'aucun consommateur ne réécrit ni la cadence ni les images-clés.
"""
import io
import json
import os
import re
import subprocess

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# LE MÊME OUTILLAGE COLORIMÉTRIQUE QUE L'ATMOSPHÈRE, et non une seconde copie :
# deux implémentations du contraste CIE divergent, et c'est celle qui n'est pas
# relue qui se trompe.
from test_atmosphere import contraste, ecart_percu, _sur, _rgb  # noqa: E402


def lire(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


CSS = lire("styles.css")
PARCOURS = lire("parcours.js")
GUIDE = lire("guide-etapes.js")

# Les quatre fonds sur lesquels un état peut se poser.
FONDS = ["--bg", "--bg2", "--panel", "--panel2"]
# Les images-clés de la grammaire d'avancement — celles qui disent un ÉTAT.
GRAMMAIRE = ["cpValide", "cpVersSuite", "cpTexteValide", "cpRail", "cpJeton",
             "cpJauge", "cpPastille", "cpTexteValide", "cpAvance"]


def _sans_commentaires(css):
    """Les commentaires de cette feuille sont des paragraphes entiers, et ils
    contiennent des accolades, des deux-points et des noms de sélecteurs. Les
    scanner comme du code faisait prendre une phrase d'explication pour une
    règle — mesuré : trois « sélecteurs » relevés étaient des morceaux de
    prose."""
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.S)


PALETTE = dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*(#[0-9A-Fa-f]{6})\b",
                          _sans_commentaires(CSS)))


def var(nom):
    """La couleur déclarée dans la feuille, en composantes — jamais recopiée
    ici. Une règle qui porterait sa propre copie de #9CC4F5 resterait verte le
    jour où la feuille en changerait.

    L'outillage de l'atmosphère travaille en TRIPLETS et non en hexadécimal :
    on lui parle sa langue plutôt que d'en écrire une seconde conversion."""
    assert nom in PALETTE, ("la feuille ne déclare pas %s : %s"
                            % (nom, sorted(PALETTE)))
    return _rgb(PALETTE[nom])


def keyframes(nom, src=None):
    """Les phases d'une animation, telles qu'elles sont écrites."""
    s = src if src is not None else (CSS + "\n" + PARCOURS + "\n" + GUIDE)
    m = re.search(r"@keyframes\s+" + re.escape(nom) + r"\s*\{", s)
    if not m:
        return None
    i, p = m.end(), 1
    while p:
        if s[i] == "{":
            p += 1
        elif s[i] == "}":
            p -= 1
        i += 1
    corps = s[m.end():i - 1]
    # Les sources JS portent le CSS en morceaux de chaîne : on recolle.
    corps = _sans_commentaires(re.sub(r'",\s*\n?\s*"', "", corps))
    return dict(re.findall(r"([\d%,.\s]+?)\s*\{([^}]*)\}", corps))


# ══════════════════════════════════════════════════════════════════════════
#  UNE SEULE DÉFINITION — trois consommateurs
# ══════════════════════════════════════════════════════════════════════════
def test_la_cadence_du_battement_est_ecrite_UNE_fois_et_LUE_partout():
    """UNE SECONDE ET DEMIE ÉCRITE TROIS FOIS EN FAIT TROIS CADENCES. Le
    parcours guidé battait à 1,8 s, le guide d'étapes à 1,5 s, et rien ne le
    disait : deux dispositifs côte à côte sur la même page, désaccordés.

    La règle mesure ce qui compte : toute animation qui NOMME une image-clé de
    la grammaire doit prendre sa durée dans `var(--cp-battement)`, jamais dans
    un littéral. Le témoin positif est dans la règle — s'il n'y avait AUCUNE
    animation à mesurer, elle passerait pour rien."""
    assert len(re.findall(r"--cp-battement\s*:", CSS)) == 1, (
        "la cadence est déclarée plusieurs fois dans la feuille")
    noms = "|".join(sorted(set(GRAMMAIRE)))
    trouvees = []
    for fichier, src in (("styles.css", CSS), ("parcours.js", PARCOURS),
                         ("guide-etapes.js", GUIDE)):
        for m in re.finditer(r"animation\s*:\s*([^;\"'}]+)", src):
            decl = m.group(1)
            if not re.search(r"\b(?:%s)\b" % noms, decl):
                continue
            trouvees.append((fichier, decl.strip()))
            assert "var(--cp-battement)" in decl, (
                "%s fixe une durée en dur au lieu de lire la cadence "
                "partagée : « %s »" % (fichier, decl.strip()))
    assert len(trouvees) >= 6, (
        "témoin : seules %d animations de la grammaire ont été trouvées — "
        "la règle ne mesure presque rien : %s" % (len(trouvees), trouvees))


def test_les_images_cles_partagees_ne_sont_definies_qu_UNE_fois():
    """Une image-clé redéfinie dans un module gagne sur la feuille pour ce
    module SEULEMENT : les deux moitiés du site battent alors différemment, et
    rien ne lève.

    LA LISTE N'EST PLUS TENUE À LA MAIN, et c'est une mutation qui l'a exigé.
    Elle nommait trois images-clés ; le jour où `cpAvance` a gagné un second
    consommateur, il n'y figurait pas — et une redéfinition dans un module
    passait sans bruit. Une règle dont la portée se met à jour à la main finit
    toujours par mesurer moins que ce qu'elle annonce. On part donc de ce que
    la FEUILLE définit, et on interdit qu'un module le redéfinise."""
    partagees = set(re.findall(r"@keyframes\s+(cp[A-Za-z0-9]+)", CSS))
    assert len(partagees) >= 4, (
        "témoin : la feuille ne définit que %d image(s)-clé(s) de la grammaire"
        % len(partagees))
    ailleurs = []
    for fichier, src in [("parcours.js", PARCOURS), ("guide-etapes.js", GUIDE)] + [
            (f, lire(f)) for f in sorted(os.listdir(ICI)) if f.endswith(".html")]:
        for nom in re.findall(r"@keyframes\s+(cp[A-Za-z0-9]+)", src):
            if nom in partagees:
                ailleurs.append((fichier, nom))
    assert not ailleurs, (
        "ces images-clés de la feuille sont redéfinies ailleurs : %s" % ailleurs)
    for nom in sorted(partagees):
        assert len(re.findall(r"@keyframes\s+" + nom + r"\b", CSS)) == 1, (
            "%s est défini deux fois dans la feuille elle-même" % nom)


# ══════════════════════════════════════════════════════════════════════════
#  CE QUE L'ŒIL VOIT — mesuré, pas affirmé
# ══════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("fond", FONDS)
def test_le_bleu_et_le_vert_se_voient_sur_les_QUATRE_fonds(fond):
    """Un état qu'on ne distingue pas du fond n'est pas un état. Le plancher
    des éléments non textuels est 3:1 (WCAG 1.4.11) ; le jeton et le compte
    portent du TEXTE, et c'est alors 4,5:1 qu'il faut — tenu sur trois fonds
    sur quatre, ce que la règle dit au lieu de le taire."""
    f = var(fond)
    for nom in ("--blue", "--green"):
        c = contraste(var(nom), f)
        assert c >= 3.0, "%s sur %s : %.2f:1 — sous le plancher" % (nom, fond, c)


def test_les_deux_couleurs_tiennent_le_seuil_TEXTE_sur_la_plupart_des_fonds():
    """Ce qui est mesuré ici est un COMPTE, pas une impression : au moins trois
    des quatre fonds doivent porter chacune des deux couleurs à 4,5:1. Le
    quatrième — le panneau clair — est nommé plutôt que dissimulé."""
    for nom in ("--blue", "--green"):
        bons = [f for f in FONDS if contraste(var(nom), var(f)) >= 4.5]
        assert len(bons) >= 3, (
            "%s ne tient le seuil texte que sur %d fond(s) : %s"
            % (nom, len(bons), {f: round(contraste(var(nom), var(f)), 2)
                                for f in FONDS}))


def test_le_bleu_ne_se_CONFOND_ni_avec_le_vert_ni_avec_le_cyan_de_marque():
    """LE DÉFAUT QUE CETTE RÈGLE INTERDIT : prendre --cyan ou --teal pour le
    « pas encore fait ». Ce sont des cyans VERTS ; posés à côté du vert
    « fait », ils demandaient à l'œil de comparer deux nuances au lieu de lire
    un état. ΔE 2 est le seuil de perception sur une frontière nette."""
    b = var("--blue")
    assert ecart_percu(b, var("--green")) >= 40, (
        "bleu et vert trop proches : ΔE %.0f" % ecart_percu(b, var("--green")))
    assert ecart_percu(b, var("--teal")) >= 40, (
        "le bleu se confond avec le teal : ΔE %.0f" % ecart_percu(b, var("--teal")))
    assert ecart_percu(b, var("--cyan")) >= 20, (
        "le bleu se confond avec le cyan de marque : ΔE %.0f"
        % ecart_percu(b, var("--cyan")))


# ══════════════════════════════════════════════════════════════════════════
#  LE BATTEMENT NE COÛTE PAS DE LISIBILITÉ
# ══════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("nom", sorted(set(GRAMMAIRE)))
def test_aucune_phase_du_battement_ne_change_la_COULEUR_de_ce_qu_on_lit(nom):
    """LA RÈGLE QUI A TROUVÉ MON PROPRE DÉFAUT. La flèche « à faire ensuite »
    variait d'opacité de .5 à 1 : composée sur les quatre fonds, elle tombait
    entre 2,21 et 2,48:1 au creux du cycle — sous le plancher, et elle porte un
    libellé. Une règle qui se serait contentée de vérifier la présence d'une
    animation l'aurait laissée passer.

    L'invariant est général : une image-clé d'état n'a le droit de toucher
    qu'au CONTOUR (border-color), à la LUEUR (box-shadow, text-shadow) et à la
    POSITION (transform). Ni `color`, ni `background`, ni `opacity` : ces
    trois-là changent le contraste de ce que le lecteur est en train de lire,
    et le changent la moitié du temps."""
    k = keyframes(nom)
    if k is None:
        pytest.skip("%s n'est pas (ou plus) défini" % nom)
    permises = {"border-color", "box-shadow", "text-shadow", "transform"}
    for phase, decl in k.items():
        props = {p.strip().lower()
                 for p in re.findall(r"(^|;)\s*([a-z-]+)\s*:", decl)
                 for p in [p[1] if isinstance(p, tuple) else p]}
        props = {m.group(1).lower()
                 for m in re.finditer(r"(?:^|;)\s*([a-z-]+)\s*:", decl)}
        interdites = props - permises
        assert not interdites, (
            "%s, phase %s : %s touche à ce qui se lit (%s)"
            % (nom, phase.strip(), sorted(interdites), decl.strip()))
        assert props, "%s, phase %s : n'anime rien" % (nom, phase.strip())


def test_le_contour_vert_reste_VISIBLE_au_creux_de_son_cycle():
    """Un contour qui s'éteint à mi-cycle laisse le bloc NU la moitié du
    temps : on aurait un clignotant, pas un encadrement. La phase basse est
    donc composée sur les quatre fonds et mesurée."""
    k = keyframes("cpValide")
    assert k, "cpValide a disparu"
    bas = [d for p, d in k.items() if p.strip().startswith("0%")]
    assert bas, "cpValide n'a plus de phase basse : %s" % list(k)
    m = re.search(r"border-color\s*:\s*rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)", bas[0])
    assert m, "la phase basse ne pose plus de contour : %s" % bas[0]
    teinte = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    alpha = float(m.group(4))
    for f in FONDS:
        c = contraste(_sur(var(f), teinte, alpha), var(f))
        assert c >= 2.0, (
            "au creux du battement le contour ne vaut plus que %.2f:1 sur %s"
            % (c, f))


def test_la_cadence_reste_sous_le_seuil_de_photosensibilite():
    """Au-delà de trois éclats par seconde, c'est un stroboscope (WCAG 2.3.1).
    En deçà d'un cycle toutes les six secondes, l'œil s'adapte et
    n'enregistre rien — un battement qu'on ne voit pas ne dit rien."""
    m = re.search(r"--cp-battement\s*:\s*([\d.]+)s", CSS)
    assert m, "la cadence n'est plus lisible dans la feuille"
    periode = float(m.group(1))
    assert 1.2 <= periode <= 6.0, "cadence hors bornes : %s s" % periode
    assert 1.0 / periode < 3.0, "%.2f éclats/s — seuil dépassé" % (1.0 / periode)


def test_tout_battement_s_arrete_en_MOUVEMENT_REDUIT():
    """Le repli ne se contente pas d'exister : chaque sélecteur qui reçoit une
    animation de la grammaire doit se retrouver dans un bloc de mouvement
    réduit. Un seul oubli laisse un lecteur sensible devant un écran qui
    bouge."""
    noms = "|".join(sorted(set(GRAMMAIRE)))
    anime, repli = set(), set()
    for src in (CSS, PARCOURS, GUIDE):
        plat = _sans_commentaires(re.sub(r'",\s*\n?\s*"', "", src))
        for m in re.finditer(r"([^{}\"';]+)\{[^{}]*animation\s*:\s*[^;]*?"
                             r"\b(?:%s)\b[^;}]*" % noms, plat):
            for s in m.group(1).split(","):
                s = s.strip()
                if s and not s.startswith("@") and "keyframes" not in s:
                    anime.add(s)
        for m in re.finditer(r"prefers-reduced-motion[^{]*\{(.*?)\}\s*\}", plat, re.S):
            for mm in re.finditer(r"([^{}\"';]+)\{[^{}]*animation\s*:\s*none", m.group(1)):
                for s in mm.group(1).split(","):
                    if s.strip():
                        repli.add(s.strip())
    assert len(anime) >= 6, "témoin : %d sélecteurs animés trouvés" % len(anime)
    manquants = sorted(s for s in anime if s not in repli)
    assert not manquants, (
        "ces sélecteurs battent sans repli en mouvement réduit : %s" % manquants)


# ══════════════════════════════════════════════════════════════════════════
#  L'ÉTAT NE SE LIT JAMAIS PAR LA COULEUR SEULE
# ══════════════════════════════════════════════════════════════════════════
def test_chaque_etat_porte_un_TEXTE_et_pas_seulement_une_couleur():
    """TROISIÈME CANAL, ET IL EST LE SEUL UNIVERSEL. Le bleu et le vert se
    rapprochent en tritanopie ; le mouvement n'existe pas sous mouvement
    réduit. Reste le mot. Chaque branche qui rend un état doit donc porter un
    libellé — et la règle lit le CODE qui les produit, pas une liste tenue à
    côté."""
    i = GUIDE.index("function jeton(")
    corps = GUIDE[i:GUIDE.index("\n  function peindreBlocs", i)]
    # LE PIÈGE, ET IL M'A EU. Une première version cherchait `txt:"([^"]+)"` —
    # avec un « + ». Un libellé VIDÉ ne correspondait donc plus au motif : il
    # n'était pas signalé, il était SAUTÉ, et la règle restait verte sur
    # exactement le défaut qu'elle prétend chasser. Mesuré par mutation.
    # L'étoile relève le cas vide ; c'est l'assertion qui le juge.
    rendus = re.findall(r"\{\s*cl:\s*\"([a-z-]+)\",\s*txt:\s*\"([^\"]*)\"", corps)
    assert len(rendus) >= 5, "jeton() ne rend que %d états : %s" % (len(rendus), rendus)
    for cl, txt in rendus:
        assert txt.strip(), "l'état %s n'a pas de libellé" % cl
    etats = {cl for cl, _ in rendus}
    assert {"cp-valide", "cp-attente", "cp-avenir"} <= etats, etats
    # Et côté parcours : les deux badges disent leur état en toutes lettres.
    assert 'pc-e-etat fait' in PARCOURS and "Visitée" in PARCOURS
    assert 'pc-e-etat reste' in PARCOURS and "À faire" in PARCOURS


# ══════════════════════════════════════════════════════════════════════════
#  LES FLÈCHES — le rendu EXÉCUTÉ, pas relu
# ══════════════════════════════════════════════════════════════════════════
def _connecteurs(faites, n=5):
    """Le balisage que le parcours produit RÉELLEMENT pour un avancement donné.

    On exécute la source servie, on ne la relit pas : une règle qui recopierait
    la boucle éprouverait sa propre copie."""
    i = PARCOURS.index("  function fleche(")
    j = PARCOURS.index("\n  }", i) + 4
    src_fleche = PARCOURS[i:j]
    a = PARCOURS.index("    var faitesTab = ")
    b = PARCOURS.index("\n    var tete;", a)
    bloc = PARCOURS[a:b]
    prog = (
        "function esc(t){return String(t);}\n"
        + src_fleche
        + "\nfunction etapeHtml(a,e,i){return '<E'+i+'>';}\n"
        + "var idParcours='p', ici='/x', sec=null, perso=null, compteur='';\n"
        + "var vus = JSON.parse(process.env.VUS);\n"
        + "var source = { etapes: JSON.parse(process.env.ET) };\n"
        + bloc
        + "\nprocess.stdout.write(etapes);\n")
    etapes = [{"url": "/p%d" % k, "label": "L%d" % k} for k in range(n)]
    out = subprocess.run(
        ["node"], input=prog, capture_output=True, text=True, timeout=60,
        env=dict(os.environ,
                 ET=json.dumps(etapes),
                 VUS=json.dumps(["/p%d" % k for k in range(n) if faites[k]])))
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout


@pytest.mark.parametrize("faites,rang", [
    ([False] * 5, 0),
    ([True, False, False, False, False], 1),
    ([True, True, True, False, False], 3),
    ([True, True, True, True, False], 4),
])
def test_UNE_SEULE_fleche_designe_la_prochaine_a_faire(faites, rang):
    """UN GUIDE QUI SOULIGNE TOUT NE GUIDE RIEN. Avant, un « ↓ » identique
    séparait toutes les étapes : une ponctuation, pas un guide. La flèche mise
    en avant est désormais UNIQUE, et c'est celle qui mène à la première étape
    non faite — mesuré en exécutant le rendu, pas en relisant la boucle."""
    h = _connecteurs(faites)
    assert h.count("pc-fl-suite") == 1, (
        "%d flèches mises en avant au lieu d'une : %s" % (h.count("pc-fl-suite"), h))
    # Elle est placée JUSTE avant l'étape visée, et nulle part ailleurs.
    i = h.index("pc-fl-suite")
    suite = h[i:]
    assert suite.index("<E%d>" % rang) < (suite.index("<E%d>" % (rang + 1))
                                          if ("<E%d>" % (rang + 1)) in suite else 10 ** 9), h
    assert "À faire ensuite" in h or "Commencez ici" in h, h


def test_le_chemin_DEJA_PARCOURU_se_lit_en_vert_et_le_reste_non():
    """Les flèches entre deux étapes faites disent le chemin parcouru ; entre
    deux étapes à faire, elles se taisent. Compté sur un avancement connu :
    trois étapes faites font exactement deux liaisons vertes."""
    h = _connecteurs([True, True, True, False, False])
    assert h.count("pc-fl-fait") == 2, (
        "%d liaisons vertes au lieu de 2 : %s" % (h.count("pc-fl-fait"), h))
    assert h.count("pc-fl-calme") == 1, h


def test_toutes_les_etapes_faites_n_appellent_AUCUNE_fleche_de_suite():
    """Le parcours terminé ne doit plus pousser nulle part — une flèche qui
    désigne le vide est pire qu'aucune flèche."""
    h = _connecteurs([True] * 5)
    assert "pc-fl-suite" not in h, h
    assert h.count("pc-fl-fait") == 4, h


# ══════════════════════════════════════════════════════════════════════════
#  LE BLOC DE PAGE — l'état vit hors du panneau
# ══════════════════════════════════════════════════════════════════════════
def test_l_etat_des_blocs_ne_depend_PAS_de_l_ouverture_du_panneau():
    """LE DÉFAUT QUE CETTE RÈGLE FERME. `demarrer()` sortait à sa première
    ligne quand la page n'avait pas de `#gd` : une page à vingt sections
    numérotées n'avait alors AUCUN marquage d'avancement, pas même celui qui ne
    doit rien au panneau. Et guide ouvert, l'état ne se rafraîchissait que
    parce que le panneau se redessinait.

    La règle mesure l'ORDRE du code : `peindreBlocs()` et le branchement des
    écoutes précèdent la sortie anticipée, et les écoutes appellent la peinture
    hors de toute condition d'ouverture."""
    i = GUIDE.index("  function demarrer(")
    corps = GUIDE[i:GUIDE.index("\n  if (document.readyState", i)]
    assert "peindreBlocs();" in corps
    assert corps.index("peindreBlocs();") < corps.index("if (!z) return;"), (
        "la peinture des blocs est encore derrière la sortie anticipée")
    assert corps.index("brancherEtat();") < corps.index("if (!z) return;")
    b = GUIDE.index("  function brancherEtat(")
    ecoutes = GUIDE[b:GUIDE.index("\n  function demarrer(", b)]
    for ev in ("change", "input"):
        m = re.search(r'addEventListener\("%s",\s*function\s*\(\)\s*\{([^}]*)\}' % ev,
                      ecoutes)
        assert m, "plus d'écoute « %s » dans brancherEtat" % ev
        avant = m.group(1).split("if (OUVERT)")[0]
        assert "peindreBlocs()" in avant, (
            "« %s » ne repeint les blocs que si le panneau est ouvert : %s"
            % (ev, m.group(1)))
    assert "attributeFilter" in ecoutes and '"hidden"' in ecoutes, (
        "rien n'observe l'apparition d'une section calculée")


def test_les_pages_NUMEROTEES_chargent_toutes_le_module_d_etat():
    """LA RÈGLE QUI MANQUAIT, et elle ne se déduit d'aucune autre : une page
    peut numéroter dix-huit sections sans jamais charger le module qui les
    peint. C'était le cas de l'ingénierie data centre — vingt sections, aucun
    marquage. On compte les sections NUMÉROTÉES pour ne pas exiger le module
    d'une page qui porte une seule étape."""
    manquantes = []
    for f in sorted(os.listdir(ICI)):
        if not f.endswith(".html"):
            continue
        src = lire(f)
        n = len(re.findall(r'class="[^"]*\brc-etape\b', src))
        if n >= 2 and "guide-etapes.js" not in src:
            manquantes.append((f, n))
    assert not manquantes, (
        "ces pages numérotent leurs sections sans charger le module d'état : %s"
        % manquantes)


# ══════════════════════════════════════════════════════════════════════════
#  L'ASSISTANT DU DIAGNOSTIC — le dernier parcours guidé qui restait muet
# ══════════════════════════════════════════════════════════════════════════
DIAG = lire("diagnostic.html")


def _bloc_js(nom, src=None):
    """La fonction demandée, extraite de la page SERVIE, par comptage
    d'accolades. La recopier ici éprouverait un script imaginaire."""
    src = DIAG if src is None else src
    i = src.index("function %s(" % nom)
    p, k = 1, src.index("{", i) + 1
    while p:
        if src[k] == "{":
            p += 1
        elif src[k] == "}":
            p -= 1
        k += 1
    return src[i:k]


def _assistant(reponses, rang):
    """La jauge que la page produit RÉELLEMENT pour un état de réponses donné.

    `reponses` est ce que le visiteur a coché, `rang` la question qu'il a sous
    les yeux — les deux sont INDÉPENDANTS, et c'est tout l'objet de ces règles."""
    champs = re.search(r"var CHAMPS=(\[[^\]]*\]);", DIAG)
    assert champs, "la liste des champs a disparu de la page"
    prog = (
        "var TOTAL=4, step=" + str(rang) + ";\n"
        "var CHAMPS=" + champs.group(1) + ";\n"
        "var REP=JSON.parse(process.env.REP);\n"
        "function val(n){ return REP[n] || null; }\n"
        "var J={innerHTML:'',attrs:{},setAttribute:function(k,v){this.attrs[k]=v;}};\n"
        "var document={getElementById:function(id){"
        "  if(id==='stepJauge') return J; throw new Error('inattendu: '+id); }};\n"
        + _bloc_js("repondu") + "\n" + _bloc_js("jauge") + "\n"
        "jauge();\n"
        "process.stdout.write(JSON.stringify({html:J.innerHTML,"
        "libelle:J.attrs['aria-label']}));\n")
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60,
                         env=dict(os.environ, REP=json.dumps(reponses)))
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout)


def test_la_jauge_du_diagnostic_constate_les_REPONSES_et_non_le_RANG():
    """LE DÉFAUT QUE CETTE RÈGLE FERME, et il était structurel. La barre se
    remplissait sur `(step-1)/TOTAL` : elle mesurait l'AVANCÉE DANS LE
    FORMULAIRE, pas le travail. Revenir à la question 1 après en avoir répondu
    trois la ramenait à zéro — sous les yeux de quelqu'un qui venait justement
    de répondre trois fois.

    Mesuré sur l'état RÉEL : trois réponses en poche, retour à la question 1.
    Trois segments doivent être verts, et l'anneau bleu doit dire où l'on est."""
    trois = {"secteur": "energie", "taille": "grande", "situation": "debut"}
    r = _assistant(trois, rang=1)
    assert r["html"].count('class="fa') == 3, r["html"]
    assert r["html"].count("av") == 1, r["html"]
    # L'anneau de position est sur la PREMIÈRE, là où le lecteur se trouve.
    assert r["html"].split("</span>")[0].endswith('class="fa ou">'), r["html"]
    # Et le témoin négatif : sans aucune réponse, aucun vert, quel que soit le rang.
    vide = _assistant({}, rang=4)
    assert vide["html"].count('class="fa') == 0, vide["html"]


def test_le_libelle_de_la_jauge_DIT_le_compte_et_change_avec_lui():
    """LA JAUGE EST UN GRAPHIQUE : sans libellé, elle n'existe pas pour qui
    écoute la page. Et un libellé FIXE serait pire qu'aucun — il affirmerait
    un avancement qui ne bouge pas. On mesure donc qu'il CHANGE."""
    a = _assistant({}, rang=1)["libelle"]
    b = _assistant({"secteur": "eau"}, rang=2)["libelle"]
    c = _assistant({"secteur": "eau", "taille": "petite"}, rang=2)["libelle"]
    assert a and b and c, (a, b, c)
    assert a != b != c, (a, b, c)
    assert "aucune" in a.lower(), a
    assert "1 question répondue" in b, b
    assert "2 questions répondues" in c, c


def test_la_jauge_du_diagnostic_a_AUTANT_de_segments_que_la_page_a_de_questions():
    """UNE JAUGE QUI PROMET QUATRE ÉTAPES SUR UNE PAGE QUI EN PORTE CINQ fait
    chercher une question qui n'existe pas — ou en cache une. Le nombre est
    écrit une fois dans le script ; la règle le confronte au balisage."""
    n = len(re.findall(r'class="stepblock', DIAG))
    m = re.search(r"var step=1,\s*TOTAL=(\d+);", DIAG)
    assert m, "le total des étapes a disparu du script"
    assert int(m.group(1)) == n, (
        "le script annonce %s étapes, la page en porte %d" % (m.group(1), n))
    assert _assistant({}, rang=1)["html"].count("<span") == n


def test_la_liste_des_questions_n_est_ecrite_qu_UNE_fois():
    """`show()` et la jauge lisent la même liste. Écrite deux fois, elle se
    serait séparée à la première question ajoutée — et c'est la jauge, muette,
    qui aurait eu tort."""
    assert DIAG.count("'secteur','taille','situation','priorite'") == 1, (
        "la liste des champs est recopiée : %d occurrences"
        % DIAG.count("'secteur','taille','situation','priorite'"))


def test_la_fleche_du_bouton_n_avance_QUE_quand_on_peut_avancer():
    """Une flèche qui s'agite sur un bouton désactivé invite à un geste qui ne
    marche pas. On lit le code qui la pose : la classe est conditionnée à ce
    QUI REND LE BOUTON ACTIF, et à rien d'autre."""
    corps = _bloc_js("show")
    assert "b.disabled=!pret" in corps.replace(" ", ""), corps[-700:]
    m = re.search(r"'<span class=\"'\+\(([a-z]+)\?'cp-av':''\)", corps)
    assert m, "la flèche n'est plus conditionnée : %s" % corps[-500:]
    assert m.group(1) == "pret", (
        "la flèche suit « %s » et non la disponibilité du bouton" % m.group(1))
    assert "f.classList.toggle('cp-valide', repondu(n-1))" in corps, corps[:600]


# ══════════════════════════════════════════════════════════════════════════
#  LE PANNEAU GUIDÉ — ce qu'il dit, et ce qu'il compte pour une réponse
# ══════════════════════════════════════════════════════════════════════════
def _pages_guidees():
    """Les pages qui portent le point d'accroche du panneau."""
    out = []
    for f in sorted(os.listdir(ICI)):
        if f.endswith(".html") and 'id="gd"' in lire(f):
            out.append(f)
    return out


def _sections_numerotees(src):
    """Ce que `etapesDeLaPage()` retiendrait : une section, un numéro, un titre."""
    out = []
    for m in re.finditer(r"<section\b([^>]*)>(.*?)</section>", src, re.S):
        n = re.search(r'<span class="n">([^<]*)</span>', m.group(2))
        h = re.search(r"<h[23][^>]*>(.*?)</h[23]>", m.group(2), re.S)
        if not n or not h or not n.group(1).strip().isdigit():
            continue
        gd = re.search(r'data-gd="([^"]*)"', m.group(1))
        out.append({"n": n.group(1).strip(),
                    "titre": re.sub(r"<[^>]+>", "", h.group(1)).strip(),
                    "pourquoi": gd.group(1) if gd else ""})
    return out


def test_chaque_section_guidee_DIT_pourquoi_elle_demande_ce_qu_elle_demande():
    """LE SEUL TEXTE QUE LA MACHINE NE PEUT PAS DÉDUIRE. Elle sait compter des
    champs ; elle ne sait pas dire pourquoi ils décident de quelque chose. Une
    étape sans ce texte se réduit à « trois listes déroulantes » — ce que le
    lecteur voyait déjà sans le parcours.

    ET LE TEXTE DOIT APPORTER QUELQUE CHOSE. Remplir l'attribut en reformulant
    le titre est la façon la plus facile de satisfaire une règle sans rien
    apprendre à personne, et cela ne se voit pas à la relecture.

    UNE PREMIÈRE VERSION MESURAIT LE RECOUVREMENT des mots avec le titre — et
    se trompait de cible : elle punissait « Les deux filières face à face »,
    dont l'unique mot porteur est « filières », qu'un bon texte est justement
    obligé d'employer. Elle ne mesurait pas « répète le titre » mais « parle du
    sujet ». On mesure donc l'INVERSE, qui est la vraie prétention : combien de
    mots porteurs le texte apporte que le titre n'a pas."""
    pages = _pages_guidees()
    assert len(pages) >= 4, "témoin : %d page(s) guidée(s) trouvée(s)" % len(pages)
    sans, creux, pauvres = [], [], []
    for f in pages:
        for s in _sections_numerotees(lire(f)):
            if not s["pourquoi"].strip():
                sans.append((f, s["n"], s["titre"]))
                continue
            if len(s["pourquoi"]) < 80:
                creux.append((f, s["n"], s["pourquoi"]))
            mots = lambda t: {w.lower().strip(".,;:!?«»'’()") for w in t.split()
                              if len(w) > 4}
            neufs = mots(s["pourquoi"]) - mots(s["titre"])
            if len(neufs) < 8:
                pauvres.append((f, s["n"], s["titre"], len(neufs)))
    assert not sans, "sections guidées sans « pourquoi » : %s" % sans
    assert not creux, "« pourquoi » trop courts pour dire quoi que ce soit : %s" % creux
    assert not pauvres, (
        "ces « pourquoi » n'apportent presque rien que le titre ne dise déjà "
        "(mots porteurs neufs) : %s" % pauvres)


def test_le_pourquoi_vit_sur_la_SECTION_et_non_dans_un_registre():
    """Un registre de textes dans le script se désynchronise au premier titre
    renommé, et c'est le registre qu'on croit à jour. Le module LIT l'attribut
    posé à côté de ce qu'il explique — et ne porte aucune table de secours."""
    assert 'getAttribute("data-gd")' in GUIDE, GUIDE[:200]
    # Aucune table page → texte : ce serait la copie qui dérive.
    assert not re.search(r"(POURQUOI|TEXTES|REGISTRE)\s*=\s*\{", GUIDE), (
        "un registre de « pourquoi » est apparu dans le module")


def _rempli(cas):
    """Ce que `rempli()` répond RÉELLEMENT — la fonction servie, exécutée."""
    src = (_bloc_js("depart", GUIDE) + "\n" + _bloc_js("noterGeste", GUIDE)
           + "\n" + _bloc_js("rempli", GUIDE))
    prog = ("var DEPART=new WeakMap(), TOUCHE=new WeakSet();\n" + src + """
function champ(v){ return {type:'text', value:v}; }
var out={};
// 1. LE SCRIPT DE LA PAGE ÉCRIT une valeur : ce n'est pas une réponse.
var a=champ(''); depart(a); a.value='250';
out.script_seul = rempli(a);
// 2. UNE MAIN touche et change : c'en est une.
var b=champ(''); depart(b); b.value='250';
noterGeste({isTrusted:true, target:b});
out.main = rempli(b);
// 3. UNE MAIN touche mais la valeur de départ n'a pas bougé : on ne peut pas
//    savoir, donc on ne l'affirme pas.
var c=champ('80'); depart(c); noterGeste({isTrusted:true, target:c});
out.touche_sans_bouger = rempli(c);
// 4. UN ÉVÉNEMENT SYNTHÉTIQUE ne vaut pas une main.
var d=champ(''); depart(d); d.value='250';
noterGeste({isTrusted:false, target:d});
out.evenement_fabrique = rempli(d);
process.stdout.write(JSON.stringify(out));
""")
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60)
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout)[cas]


def test_une_reponse_exige_un_GESTE_et_non_une_ecriture_du_SCRIPT():
    """LE DÉFAUT QUE CECI FERME, trouvé en posant le module sur une page neuve.
    Le module comparait la valeur d'un champ à celle vue en arrivant pour
    distinguer une RÉPONSE d'un défaut. Cela distingue en réalité « a changé »
    de « n'a pas changé » — et la page elle-même change des valeurs.

    L'ingénierie data centre écrit ses prix unitaires de référence quelques
    centaines de millisecondes après le chargement. Le relevé était pris avant :
    la comparaison voyait bouger vingt-six champs, et la section s'annonçait
    « ✓ Renseigné » à quelqu'un qui n'avait rien fait. Mesuré au navigateur, sur
    la page réelle.

    LES QUATRE CAS SONT ÉPROUVÉS ENSEMBLE, et c'est nécessaire : une règle qui
    n'éprouverait que le premier serait satisfaite par un `rempli()` qui répond
    toujours faux — c'est-à-dire par un parcours qui n'avance jamais."""
    assert _rempli("script_seul") is False, (
        "une écriture du script compte encore comme une réponse")
    assert _rempli("main") is True, (
        "une vraie saisie ne compte plus : le parcours n'avancerait jamais")
    assert _rempli("touche_sans_bouger") is False
    assert _rempli("evenement_fabrique") is False, (
        "un événement fabriqué vaut une main : le garde ne garde rien")


def test_la_recette_du_guide_ne_FABRIQUE_plus_ses_evenements():
    """CONSÉQUENCE DIRECTE DU GARDE, et il fallait la tirer. Le module ne
    crédite plus que ce qu'une main a touché ; une recette qui continue de
    fabriquer ses `Event` éprouve un chemin qu'aucun visiteur n'emprunte, et
    rendrait « rien n'avance » sur un module qui avance très bien.

    Le plus dangereux n'est pas qu'elle échoue — c'est qu'on la « répare » en
    rouvrant le garde. La règle ferme cette porte : la recette passe par le
    clavier et la souris du pilote, seuls gestes que le navigateur marque
    comme dignes de confiance."""
    rec = lire("recette_guide_etapes.js")
    assert "dispatchEvent" not in rec, (
        "la recette fabrique de nouveau ses événements : elle n'éprouve plus "
        "le chemin d'un lecteur")
    for geste in ("pg.fill(", "pg.click(", "pg.keyboard.type(", "pg.selectOption("):
        assert geste in rec, "la recette n'emploie plus %s" % geste
