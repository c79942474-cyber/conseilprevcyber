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
    module SEULEMENT : les deux moitiés du site battent alors différemment,
    et rien ne lève."""
    tout = {"styles.css": CSS, "parcours.js": PARCOURS, "guide-etapes.js": GUIDE}
    for nom in ("cpValide", "cpVersSuite", "cpTexteValide"):
        ou = [(f, len(re.findall(r"@keyframes\s+" + nom + r"\b", s)))
              for f, s in tout.items()]
        total = sum(n for _, n in ou)
        assert total == 1, "%s est défini %d fois : %s" % (nom, total, ou)
        assert dict(ou)["styles.css"] == 1, (
            "%s doit vivre dans la feuille partagée, pas dans un module : %s"
            % (nom, ou))


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
