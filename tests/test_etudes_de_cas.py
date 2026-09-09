# -*- coding: utf-8 -*-
"""LES ÉTUDES DE CAS SONT DES CARTES QUI PIVOTENT — ET RIEN NE S'EST PERDU.

CE QUE CES RÈGLES GARDENT, ET POURQUOI ELLES EXISTENT.

  — LA SUBSTANCE. Faire passer neuf fiches d'une grille à des cartes, c'est
    réécrire leur balisage. Une phrase perdue au passage ne se voit pas : la
    page reste belle, elle dit seulement moins. Chaque étude déclare donc ici
    les termes qu'elle DOIT porter, et la règle les cherche dans SA carte —
    pas dans la page, où n'importe quelle autre fiche les fournirait.

  — LES DEUX NATURES. Cette page porte des missions conduites ET des cas
    types. Un cas type qui dériverait au milieu des missions se lirait comme
    une mission. La séparation est donc structurelle, et mesurée : la fiche
    « cas type » est dans la bande des cadres, jamais dans un rail.

  — LA FICHE CHIFFRÉE. Elle ne pivote pas, et ce n'est pas un oubli : elle
    porte un tableau de comparaison qu'une carte de 330 px rendrait illisible.
    Elle garde donc sa pleine largeur ET l'ancre que son script vise — sans
    laquelle plus aucun nombre ne serait peint.

  — LE SCRIPT, EXÉCUTÉ. Le pivot, la fermeture, la bascule et la marque de
    défilement sont vérifiés en FAISANT tourner etudes-cartes.js contre un DOM
    factice. Une règle qui chercherait « aria-pressed » dans la source serait
    verte le jour où l'attribut serait posé sur le mauvais élément.

  — DEUX PIÈGES VENUS DE LA FEUILLE PARTAGÉE, tous deux mesurés en navigateur
    par recette_cas_poste_ht.js et tenus ici par leur mécanisme : la « loupe »
    au survol, qui mettait une mise à l'échelle sur le conteneur de
    perspective ; et l'apparition au défilement, qui laissait quatre cartes
    sur dix-sept à opacity 0 après quatorze secondes.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

PAGE = "etudes-de-cas.html"
SCRIPT = "etudes-cartes.js"


def _src(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


def _texte(html_):
    import html as _h
    return re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", html_))).strip()


def _element(src, debut, balise="span"):
    """Le contenu de l'élément qui s'ouvre à `debut`, bornes comptées.

    POURQUOI PAS UNE LIGNE, NI UNE EXPRESSION NON GOURMANDE. Une batterie de
    mutations a montré les deux défauts : l'expression non gourmande s'arrête
    au premier « </span></span> », donc au badge imbriqué ; et lire la LIGNE
    laisse passer un badge sorti de l'élément mais resté sur la même ligne —
    la mutation qui déplaçait la pastille hors du bloc du nom a survécu à une
    règle qui prétendait justement l'interdire. On compte donc les bornes."""
    o, f = "<" + balise, "</" + balise + ">"
    i = src.index(">", debut) + 1
    prof, dep = 1, i
    while prof:
        po, pf = src.find(o, i), src.find(f, i)
        assert pf != -1, "élément non refermé"
        if po != -1 and po < pf:
            prof += 1
            i = po + len(o)
        else:
            prof -= 1
            i = pf + len(f)
    return src[dep:i - len(f)]


def _cartes():
    """Chaque carte pivotante de la page, découpée sur son <button>.

    Le découpage est fait sur la balise ouvrante ET sur le </button> qui suit :
    une carte est ainsi rendue avec ses deux faces, et jamais avec la voisine."""
    src = _src(PAGE)
    out = {}
    # LE MOTIF LIT UNE LISTE DE CLASSES, PAS UNE CHAÎNE EXACTE. Le premier jet
    # exigeait `class="case eN"` au caractère près : le jour où la carte des
    # cadres a reçu un modificateur de format — `class="case case--large e9"` —
    # elle a cessé d'exister POUR LA RÈGLE. Quatre contrôles sont alors devenus
    # rouges en annonçant « la fiche e9 a disparu de la page », alors qu'elle
    # y était, entière. Une règle qui se casse sur l'ordre des classes ne
    # mesure pas la carte, elle mesure sa mise en forme.
    for m in re.finditer(r'<button type="button" class="([^"]*\bcase\b[^"]*)"', src):
        cles = [c for c in m.group(1).split() if re.fullmatch(r"e\d+", c)]
        if not cles:
            continue
        fin = src.index("</button>", m.start())
        out[cles[0]] = src[m.start():fin]
    return out


CARTES = _cartes()

# ═══════════════════════════════════════════════════════════════════════════
#  1. LA SUBSTANCE — chaque étude porte ce qu'elle portait
# ═══════════════════════════════════════════════════════════════════════════

# CE TABLEAU EST LE CONTRAT DE LA MIGRATION. Il énumère, étude par étude, ce
# que la fiche disait dans la grille d'origine et doit dire encore. Il n'est
# pas une liste de mots-clés décoratifs : chaque entrée est un fait technique
# que la fiche perdrait sans bruit si le balisage l'avalait.
SUBSTANCE = {
    "e1": ("EDF — DSI", ["Mission Sûreté du SI", "datacenters et réseaux d’EDF SA",
                         "guides de sûreté de fonctionnement", "EDF DSIT",
                         "revues d’architectures", "EBIOS RM"]),
    "e2": ("RENAULT", ["WP.29", "CSMS", "Roadsecurity Plan", "ISO/SAE 21434",
                       "SUMS", "R155/R156", "PIA / AIPD / RGPD"]),
    "e3": ("ATOS — Société du Grand Paris", ["réseau multi-services",
                                             "systèmes de surveillance des espaces",
                                             "lignes 15, 16 et 17", "EBIOS RM",
                                             "EGIS", "SETEC"]),
    "e4": ("ALSTOM — Projet REM (Montréal)", ["contrat SIEM", "WP1.1", "DAT",
                                              "dossier d’architecture technique",
                                              "WP2.1", "pré-intégration",
                                              "plateforme d’hébergement du SIEM",
                                              "analyse de risque système"]),
    "e5": ("GRDF — Projet Biométhane", ["politique de sécurité du SI Industriel",
                                        "EBIOS", "MCS", "cartographie du SI industriel",
                                        "Specification for Design System Integration",
                                        "détection d’incident", "MCO", "LPM", "NIS",
                                        "NIST SP 800‑82", "NIST SP 800‑53",
                                        "ANSSI", "IEC 62443", "ISO 27001"]),
    "e6": ("TECHNIPENERGIES", ["PLC, HMI, SCADA, DCS", "KARISH", "Tanin FPSO",
                               "GTLA", "MANASEER MCC", "Martin Linge", "MOTIVA FEED",
                               "US GAS CAP"]),
    "e7": ("Groupe d’assurance international", ["AMOA", "Cartographie de l’exposition du SI",
                                                "Chaînes de patching", "SOC",
                                                "Gouvernance", "gestion de crise",
                                                "TTD", "MTTR", "MTTP",
                                                "taux d’automatisation", "IT/OT"]),
    "e8": ("Management OT — Offshore Substation Wind Farm",
           ["schéma de sécurité OT", "IEC 62443", "ISO 27000",
            "prestataire de services IACS", "security levels",
            "niveaux de maturité", "système et composant", "EPCI",
            "fournisseurs et sous-traitants"]),
    "e9": ("Postes haute tension", ["62443‑3‑2", "62443‑3‑3", "62443‑2‑4",
                                    "bus de process", "bus de station", "téléconduite",
                                    "SL‑T", "NIS2", "Bundesnetzagentur", "EnWG",
                                    "BDEW", "critères d’acceptation"]),
}


@pytest.mark.parametrize("cle", sorted(SUBSTANCE))
def test_chaque_etude_porte_encore_TOUTE_sa_substance(cle):
    nom, termes = SUBSTANCE[cle]
    assert cle in CARTES, "la fiche %s (%s) a disparu de la page" % (cle, nom)
    lu = _texte(CARTES[cle])
    assert nom in lu, "la carte %s ne porte plus son intitulé %r" % (cle, nom)
    manquants = [t for t in termes if _texte(t) not in lu]
    assert not manquants, (
        "la carte %s (%s) a perdu au passage en carte : %s"
        % (cle, nom, ", ".join(manquants)))


def test_il_y_a_NEUF_cartes_et_pas_une_de_plus():
    """Un compte, pas une présence. En perdre une ou en dupliquer une se
    verrait ici avant l'écran.

    NEUF, PUIS DIX. La dixième est « Client Impact », qui était une fiche
    déroulée et devient une carte au format large. Le compte se met à jour
    parce que c'est une décision, pas un accident : neuf missions dans les
    rails, une dixième carte dans la bande des cadres. Le partage entre les
    deux est gardé par `test_le_cas_type_ne_derive_pas_parmi_les_missions`."""
    assert len(CARTES) == 10, sorted(CARTES)
    # LE PARTAGE EST MESURÉ, PAS SUPPOSÉ : huit missions dans les rails, deux
    # cadres dans la bande. Une carte de cadre qui glisserait parmi les
    # missions se lirait comme une mission conduite — c'est précisément ce que
    # la bande pointillée existe pour empêcher.
    src = _src(PAGE)
    d_cad = src.index('<div class="cadres"')
    dans_cadres = sorted(c for c in CARTES if src.index(CARTES[c][:60]) > d_cad)
    assert dans_cadres == ["e10", "e9"], dans_cadres
    assert len(CARTES) - len(dans_cadres) == 8, sorted(CARTES)
    assert len(SUBSTANCE) == 9


@pytest.mark.parametrize("cle", sorted(SUBSTANCE))
def test_chaque_carte_a_ses_deux_faces_et_de_quoi_les_lire(cle):
    """LE DÉFAUT QUE CETTE RÈGLE PREND : une carte dont le verso serait resté
    vide se retourne parfaitement et ne montre rien. On mesure donc la
    LONGUEUR du propos, pas la présence de la balise."""
    b = CARTES[cle]
    assert b.count('class="case-face case-recto"') == 1
    assert b.count('class="case-face case-verso"') == 1
    recto = b[b.index("case-recto"):b.index("case-verso")]
    verso = b[b.index("case-verso"):]
    for zone, nom, mini in ((recto, "recto", 60), (verso, "verso", 240)):
        assert len(_texte(zone)) >= mini, (
            "le %s de %s ne porte que %d caractères"
            % (nom, cle, len(_texte(zone))))
    assert '<span class="case-co">' in recto, "le nom n'est pas sur la face visible"
    assert '<span class="tags">' in recto, "les mots-clés ne sont pas sur la face visible"
    # L'ACCROCHE EST SUR UNE FACE, PAS FORCÉMENT SUR LE VERSO. Les cartes de
    # mission, larges de 330 px, la portent au verso : le recto y est déjà
    # plein. Les deux cartes de la bande des cadres font 978 px — badges,
    # titre et étiquettes n'y remplissent que le tiers haut, et laissaient
    # 190 px de vide mesurés. L'accroche est donc passée à leur recto. Ce que
    # la règle garde n'est pas SA PLACE, c'est qu'elle EXISTE et que le verso
    # porte sa mention de nature.
    assert '<span class="para">' in b, (
        "%s n'a plus d'accroche, ni au recto ni au verso" % cle)
    assert '<span class="v-pied">' in verso


# ═══════════════════════════════════════════════════════════════════════════
#  2. LES DEUX NATURES — et la séparation qui les tient
# ═══════════════════════════════════════════════════════════════════════════

def test_un_cas_type_n_est_JAMAIS_dans_un_rail_de_missions():
    """CE QUE CETTE RÈGLE EMPÊCHE, EN UNE PHRASE : qu'une fiche sans client
    dérive au milieu des références et se lise comme une référence.

    On mesure la place réelle dans le document, par les bornes des deux
    conteneurs — pas la présence d'un badge, qu'une carte mal placée porterait
    tout aussi bien."""
    src = _src(PAGE)
    d_kal, f_kal = src.index('<div class="kal"'), src.index('<div class="kal-grille"') \
        if '<div class="kal-grille"' in src else src.index('<div class="cadres"')
    d_cad = src.index('<div class="cadres"')
    for cle, bloc in CARTES.items():
        pos = src.index(bloc)
        cas_type = 'class="typ"' in bloc
        dans_rail = d_kal < pos < f_kal
        dans_cadres = pos > d_cad
        if cas_type:
            assert dans_cadres and not dans_rail, (
                "%s est un cas type et dérive parmi les missions" % cle)
        else:
            assert dans_rail and not dans_cadres, (
                "%s est une mission et n'est pas dans un rail" % cle)


def test_le_badge_de_nature_se_lit_du_MEME_REGARD_que_le_nom():
    """La page a été écrite pour cette propriété : une fiche qui n'est pas une
    mission menée le dit à l'endroit où on lit le nom, pas dans une note de
    bas de carte. On mesure donc que les deux sont dans le MÊME .case-top —
    et sur le RECTO, sans avoir à retourner quoi que ce soit.

    (L'écart en pixels, lui, est mesuré en navigateur par
    recette_cas_poste_ht.js : 37 px, sous le seuil de 40 qu'elle impose.)"""
    marques = 0
    for cle, bloc in CARTES.items():
        for classe in ("typ", "anon"):
            if 'class="%s"' % classe not in bloc:
                continue
            marques += 1
            recto = bloc[bloc.index("case-recto"):bloc.index("case-verso")]
            # LE BLOC EST DÉLIMITÉ PAR SES BORNES, PAS PAR SA LIGNE. Une
            # mutation qui sortait la pastille de l'élément en la laissant sur
            # la même ligne survivait à la version précédente de cette règle.
            top = _element(recto, recto.index('<span class="case-top">'))
            assert 'class="%s"' % classe in top, (
                "%s : le badge %s n'est pas dans le bloc du nom" % (cle, classe))
            assert 'class="case-co"' in top, (
                "%s : le nom n'est pas dans le bloc du badge" % cle)
    # DEUX, PUIS TROIS. La troisième est « Client Impact », devenue carte : elle
    # porte « cas type » ET « chiffres calculés », deux marques distinctes —
    # l'une dit qu'aucun client n'est revendiqué, l'autre que les nombres
    # sortent d'un moteur de calcul et non d'un relevé de terrain. Le compte
    # est une garde, pas un décor : il demande une décision à chaque marque
    # ajoutée, et la voici.
    assert marques == 3, (
        "trois fiches exactement portent une marque de nature — deux cas types "
        "et une référence anonymisée ; %d trouvée(s)" % marques)


def test_aucun_nom_accessible_ne_porte_de_BALISAGE():
    """LE DÉFAUT QU'ELLE A PRIS, ET QUI NE SE VOYAIT PAS À L'ÉCRAN.

    Le gabarit des cartes injectait la marque de nature dans l'attribut
    aria-label telle qu'elle est écrite dans le recto — c'est-à-dire du
    balisage. L'attribut se refermait donc au premier guillemet de
    « class="anon" », le reste se lisait comme des attributs, et le nom
    accessible devenait « Groupe d'assurance international — <span class= ».

    Sur les DEUX SEULES cartes dont la nature doit être annoncée. À l'écran,
    rien ne paraissait : le recto porte la pastille, visible. C'est
    précisément le genre de défaut qu'aucun coup d'œil ne prend.

    La règle vaut pour la page entière, pas pour ces deux cartes : le même
    gabarit servira ailleurs."""
    import html as _h
    fautes = []
    for m in re.finditer(r'aria-label="([^"]*)"', _src(PAGE)):
        v = _h.unescape(m.group(1))
        if "<" in v or ">" in v or not v.strip():
            fautes.append(v[:70])
    assert not fautes, (
        "des noms accessibles portent du balisage ou sont vides :\n  %s"
        % "\n  ".join(fautes))


def test_chaque_carte_ANNONCE_SA_NATURE_dans_son_nom_accessible():
    """Ce que voit un lecteur d'écran doit dire la même chose que la pastille
    que voit l'œil. On lit donc le nom accessible et on y cherche la nature —
    la vraie, celle que la carte affiche."""
    for cle, bloc in CARTES.items():
        m = re.search(r'aria-label="([^"]*)"', bloc)
        assert m, "%s n'a pas de nom accessible" % cle
        lu = m.group(1)
        attendu = ("cas type" if 'class="typ"' in bloc
                   else "référence anonymisée" if 'class="anon"' in bloc
                   else "mission conduite")
        assert attendu in lu, (
            "%s affiche « %s » et annonce « %s »" % (cle, attendu, lu))


def test_le_pied_de_chaque_verso_dit_la_MEME_nature_que_sa_face():
    """UNE CARTE QUI SE CONTREDIRAIT D'UNE FACE À L'AUTRE serait pire que
    muette. Le bandeau du recto, l'en-tête du verso et le pied doivent dire la
    même chose — et « Mission conduite » est interdit là où « cas type » est
    affiché."""
    for cle, bloc in CARTES.items():
        cas_type = 'class="typ"' in bloc
        anonyme = 'class="anon"' in bloc
        lu = _texte(bloc)
        if cas_type:
            assert "Cadre d’intervention" in lu, cle
            assert "Mission conduite" not in lu, (
                "%s est un cas type et se dit mission conduite" % cle)
            assert "aucun client" in lu, cle
        elif anonyme:
            assert "Référence anonymisée" in lu, cle
            assert "Aucune donnée client" in lu, cle
        else:
            assert "Mission conduite" in lu, cle
            assert "Étude de cas" in lu, cle


def test_la_page_annonce_les_deux_natures_AVANT_de_les_montrer():
    src = _src(PAGE)
    tete = src[src.index('<section class="page-head">'):src.index('<div class="kal-barre">')]
    lu = _texte(tete)
    assert "cas type" in lu.lower() and "démarche" in lu
    assert 'class="typ"' in tete, "le chapeau nomme le badge sans le montrer"
    assert "Cadres d'intervention" in lu or "Cadres d’intervention" in lu, (
        "le chapeau ne dit pas OÙ sont passés les cas types")


# ═══════════════════════════════════════════════════════════════════════════
#  3. LA FICHE CHIFFRÉE — elle ne pivote pas, et ses nombres se peignent
# ═══════════════════════════════════════════════════════════════════════════

def test_la_fiche_chiffree_garde_L_ANCRE_QUE_SON_SCRIPT_VISE():
    """SANS CETTE RÈGLE, LE DÉFAUT EST INVISIBLE : la page se sert
    parfaitement, la fiche s'affiche, et pas un nombre n'apparaît — parce que
    impact-client.js cherche une ancre que le remaniement a emportée.

    On ne cherche donc pas « ci-calcul » dans la page : on lit dans le script
    l'identifiant qu'il vise RÉELLEMENT, et on l'exige dans la page."""
    js = _src("impact-client.js")
    vise = re.findall(r'getElementById\("([^"]+)"\)', js)
    assert vise, "impact-client.js ne vise plus aucune ancre ?"
    src = _src(PAGE)
    for ancre in set(vise):
        assert 'id="%s"' % ancre in src, (
            "impact-client.js peint dans #%s, que la page ne porte plus" % ancre)


def test_le_TABLEAU_reste_hors_du_pivot_meme_si_le_recit_y_entre():
    """L'ARBITRAGE CHANGE DE PORTÉE, ET SON MOTIF EXPLIQUE POURQUOI.

    L'ancienne règle disait « la fiche chiffrée NE PIVOTE PAS », et son motif
    était la LARGEUR : « un tableau de comparaison serré dans une carte de
    330 px devient illisible avant d'être informatif ». Le format large répond
    à cette objection — la carte fait 978 px mesurés, presque trois fois plus.
    Le RÉCIT entre donc dans une carte.

    LE TABLEAU, LUI, RESTE DEHORS, et c'est une mesure qui le décide : le bloc
    calculé fait 1 093 px de haut à lui seul, 2 959 des 4 380 caractères de la
    fiche. Derrière un pivot, il faudrait cliquer puis faire défiler mille
    pixels pour atteindre ce qui fait l'intérêt de la fiche. Une carte qui
    replie sa substance n'est pas une refonte, c'est une perte.

    CE QUE LA RÈGLE GARDE désormais : l'ancre du tableau n'est JAMAIS dans une
    face de carte."""
    src = _src(PAGE)
    d = src.index('id="cas-impact-client"')
    ouvre = src.rindex("<div", 0, d)
    bloc = src[ouvre:src.index('<div class="divider">', d)]
    assert 'class="ci-bloc' in src[ouvre:src.index(">", d) + 1], (
        "le cas n'est plus tenu en un seul bloc")
    assert "ci-large" in src[ouvre:src.index(">", d) + 1]
    # L'ANCRE DU TABLEAU N'EST PAS DANS UNE FACE. On mesure la POSITION, pas la
    # présence : `#ci-calcul` doit tomber après la fermeture du bouton.
    fin_bouton = bloc.rindex("</button>")
    assert bloc.index('id="ci-calcul"') > fin_bouton, (
        "l'ancre du tableau est passée DANS la carte : le lecteur devra "
        "cliquer puis faire défiler mille pixels pour atteindre les chiffres")
    assert '<div class="fiche-calc">' in bloc[fin_bouton:], (
        "le bloc chiffré n'a plus son propre encadré sous la carte")
    # LE TABLEAU N'EST PAS DANS LA PAGE, ET C'EST NORMAL : il est bâti à
    # l'affichage par impact-client.js dans l'ancre. La première version de
    # cette règle le cherchait dans le HTML et tombait pour une raison sans
    # rapport avec ce qu'elle garde. La chaîne réelle est celle-ci : le script
    # écrit un tableau, la page lui donne une ancre, donc la fiche qui la
    # porte ne peut pas être une carte de 330 px.
    js = _src("impact-client.js")
    assert '<table class="ci-t"' in js, (
        "impact-client.js ne bâtit plus de tableau : l'arbitrage de pleine "
        "largeur n'a plus de raison d'être, cette règle non plus")
    assert 'id="ci-calcul"' in bloc, "la fiche a perdu l'ancre où le tableau se peint"


def test_Client_Impact_porte_SES_DEUX_marques_de_nature():
    """DEUX MARQUES, DEUX CHOSES DIFFÉRENTES, et une seule ne suffit pas :
    « cas type » dit qu'aucun client n'est revendiqué, « chiffres calculés »
    que les nombres sortent d'un moteur et non d'un relevé de terrain. Une
    fiche qui ne porterait que la première se lirait comme une mesure de
    site.

    CETTE RÈGLE EST NÉE D'UNE ASSERTION MAL LOGÉE. Le contrôle du badge vivait
    dans la règle du tableau : une mutation qui retirait le badge faisait
    tomber une règle dont le nom parle de tout autre chose, et personne
    n'aurait su, en lisant l'échec, ce qui avait réellement disparu."""
    b = CARTES["e10"]
    top = b[b.index('class="case-top"'):b.index("</span>", b.index('class="case-co"'))]
    for classe, quoi in (("typ", "cas type"), ("calc", "chiffres calculés")):
        assert 'class="%s"' % classe in top, (
            "Client Impact ne porte plus la marque « %s » au même regard que "
            "son nom" % quoi)


# ═══════════════════════════════════════════════════════════════════════════
#  4. CE QUE LA PAGE DOIT ENCORE À CEUX QUI N'EXÉCUTENT PAS LE SCRIPT
# ═══════════════════════════════════════════════════════════════════════════

def test_les_neuf_etudes_sont_LISIBLES_SANS_SCRIPT(anonyme):
    """UN KALÉIDOSCOPE QUI VIDE LA PAGE ÉCHANGE LE RÉFÉRENCEMENT CONTRE UN
    EFFET. Le propos de chaque fiche doit être dans le HTML servi, et non
    fabriqué à l'affichage : c'est ce que lisent l'indexeur, le lecteur sans
    script, et l'aperçu partagé."""
    servi = anonyme.get("/etudes-de-cas").get_data(as_text=True)
    lu = _texte(servi)
    for cle, (nom, termes) in SUBSTANCE.items():
        assert nom in lu, nom
        for t in termes[:3]:
            assert _texte(t) in lu, (cle, t)
    assert "etudes-cartes.js" in servi, "le script du mouvement n'est pas appelé"


def test_chaque_script_de_la_page_est_REELLEMENT_SERVI(anonyme):
    """LA RÈGLE QUI MANQUE TOUJOURS AILLEURS. Une page qui référence un script
    absent est une page valide : elle se sert, et rien ne bouge. On demande
    donc au serveur, pas à une liste."""
    page = anonyme.get("/etudes-de-cas").get_data(as_text=True)
    scripts = re.findall(r'<script src="(/[^"?]+\.js)', page)
    assert scripts, "la page ne référence aucun script ?"
    fautes = []
    for src in scripts:
        r = anonyme.get(src)
        t = (r.headers.get("Content-Type") or "").lower()
        if r.status_code != 200 or "javascript" not in t:
            fautes.append("%s → %d, type %r" % (src, r.status_code, t))
    assert not fautes, "\n  ".join(fautes)


# ═══════════════════════════════════════════════════════════════════════════
#  5. LES DEUX PIÈGES DE LA FEUILLE PARTAGÉE
# ═══════════════════════════════════════════════════════════════════════════

def _specificite(sel, porte=".case"):
    """(#id, .classe|:pseudo-classe|[attr], balise) — de quoi comparer deux
    règles qui se disputent la même propriété.

    UNE LISTE SÉPARÉE PAR DES VIRGULES N'A PAS DE SPÉCIFICITÉ PROPRE : chaque
    membre a la sienne, et c'est celui qui atteint l'élément qui compte. Sans
    cette distinction, « .metric:hover,.case:hover,.kpi:hover,.stat:hover »
    comptait huit classes au lieu de deux — la règle aurait exigé une
    neutralisation impossible, pour une raison sans rapport avec la cascade."""
    membres = [m for m in sel.split(",") if porte in m] or sel.split(",")
    def poids(m):
        return (len(re.findall(r"#[\w-]+", m)),
                len(re.findall(r"\.[\w-]+|\[[^\]]+\]|:(?!:)[\w-]+", m)),
                len(re.findall(r"(?:^|[\s>+~])([a-zA-Z][\w-]*)", m)))
    return max(poids(m) for m in membres)


def _hors_media(css):
    """La feuille SANS ses blocs @media.

    LE FAUX VERT QU'ELLE FERME, TROUVÉ PAR MUTATION. La règle de la loupe
    cherchait une neutralisation « .case:hover{transform:none} » n'importe où
    dans la cascade. Elle en trouvait une — mais à l'intérieur du bloc
    « @media (prefers-reduced-motion: reduce) », où elle ne s'applique qu'aux
    lecteurs qui ont désactivé les animations. Pour tout le monde d'autre, la
    loupe reprenait la main, et la règle restait verte. Une déclaration sous
    condition ne neutralise rien pour qui ne remplit pas la condition."""
    out, i, prof = [], 0, 0
    while i < len(css):
        if css.startswith("@media", i):
            j = css.index("{", i) + 1
            prof = 1
            while prof:
                if css[j] == "{":
                    prof += 1
                elif css[j] == "}":
                    prof -= 1
                j += 1
            i = j
            continue
        out.append(css[i])
        i += 1
    return "".join(out)


def _cascade():
    """Ce que le navigateur lit, DANS L'ORDRE : la feuille partagée, puis le
    bloc en ligne de la page.

    LES DEUX RÈGLES QUI SUIVENT MESURENT UNE CASCADE, PAS UN FICHIER. Le
    mécanisme des cartes a été mutualisé dans styles.css après avoir vécu en
    ligne dans la page : une règle qui aurait cherché la neutralisation « dans
    etudes-de-cas.html » serait tombée le jour du déménagement, sans que rien
    ait cessé de fonctionner. Ce qui compte est l'ordre où le navigateur les
    rencontre, et c'est cela qu'on reconstitue."""
    page = _src(PAGE)
    enligne = page[page.index("<style>"):page.index("</style>")]
    return _src("styles.css") + "\n/* ↓ bloc en ligne de la page ↓ */\n" + enligne


def test_la_LOUPE_du_site_ne_s_applique_pas_a_une_carte_qui_pivote():
    """LE DÉFAUT, MESURÉ AVANT CORRECTION : styles.css agrandit « .case » de
    5 % au survol. Sur une carte qui pivote, cette mise à l'échelle porte sur
    le CONTENEUR DE PERSPECTIVE — la projection du pivot est faussée, et la
    carte survolée passait de 330 à 346,5 px, cessant d'avoir la taille des
    huit autres.

    La règle suit le vrai mécanisme : elle ne réclame la neutralisation QUE
    tant que la feuille partagée agrandit .case, et elle vérifie ce qui fait
    qu'elle gagne — spécificité au moins égale, et déclarée APRÈS."""
    # SANS LES BLOCS @media : une neutralisation qui n'existe que sous
    # « prefers-reduced-motion » ne neutralise rien pour le visiteur ordinaire.
    casc = _hors_media(_cascade())
    loupe = re.search(r"([^\n{]*\.case:hover[^\n{]*)\{([^}]*scale\([^}]*)\}", casc, re.S)
    if not loupe:
        pytest.skip("la feuille partagée n'agrandit plus .case au survol")
    neutre = None
    for m in re.finditer(r"([^\n{]*\.case:hover[^\n{]*)\{([^}]*)\}", casc):
        if "transform:none" in m.group(2):
            neutre = m
    assert neutre, (
        "rien ne neutralise la loupe : la carte survolée n'aura pas la "
        "largeur des autres")
    assert _specificite(neutre.group(1)) >= _specificite(loupe.group(1)), (
        "la neutralisation est moins spécifique que la loupe : %s contre %s"
        % (neutre.group(1).strip(), loupe.group(1).strip()))
    assert neutre.start() > loupe.start(), (
        "la neutralisation est rencontrée AVANT la loupe : à spécificité "
        "égale, c'est la loupe qui gagnerait")


def test_une_carte_de_rail_ne_depend_pas_de_l_apparition_au_defilement():
    """LE DÉFAUT, MESURÉ AVANT CORRECTION : nav.js pose « .rv » (opacity:0)
    sur « main .case » puis attend qu'un IntersectionObserver la voie entrer
    dans la fenêtre. Une carte de rail est rognée HORIZONTALEMENT par sa
    piste : elle n'entre pas tant qu'elle n'a pas dérivé. Quatre cartes sur
    dix-sept restaient invisibles après quatorze secondes de dérive — tout le
    second rail.

    La règle suit la dépendance : elle n'exige le rattrapage QUE tant que
    nav.js met .case en attente, et elle vérifie que la règle qui rattrape
    l'emporte réellement sur « .rv »."""
    nav = _src("nav.js")
    bloc = nav[nav.index("function initReveal()"):]
    bloc = bloc[:bloc.index("\n  }")]
    if ".case" not in bloc or '"rv"' not in bloc:
        pytest.skip("nav.js ne met plus les cartes en attente d'apparition")
    casc = _hors_media(_cascade())
    m = re.search(r"([^\n{]*\.case\.rv[^\n{]*)\{([^}]*)\}", casc)
    assert m and "opacity:1" in m.group(2), (
        "rien ne rend visible une carte de rail : elle attendra d'avoir "
        "dérivé jusque dans la fenêtre")
    rv = re.search(r"(^|\})\s*(\.rv)\{([^}]*opacity:0[^}]*)\}", casc, re.M)
    assert rv, "la feuille partagée ne définit plus .rv ?"
    assert _specificite(m.group(1), ".case") > _specificite(rv.group(2), ".rv"), (
        "le rattrapage n'est pas plus spécifique que .rv")


# ═══════════════════════════════════════════════════════════════════════════
#  6. LE SCRIPT — EXÉCUTÉ, PAS RELU
# ═══════════════════════════════════════════════════════════════════════════

_HARNAIS = r"""
/* Un DOM factice, juste assez pour etudes-cartes.js : ce qui est mesuré ici,
   c'est le COMPORTEMENT du script, pas sa source. */
function El(tag, cls) {
  this.tagName = String(tag).toUpperCase();
  this.className = cls || "";
  this.children = [];
  this.parentElement = null;
  this._attrs = {};
  this._texte = "";
  this.scrollHeight = 0;
  this.clientHeight = 0;
  this.focus_appele = 0;
  var self = this;
  this.classList = {
    add: function () { for (var i = 0; i < arguments.length; i++) if (!self.classList.contains(arguments[i])) self.className = (self.className + " " + arguments[i]).trim(); },
    remove: function () { var jeter = [].slice.call(arguments); self.className = self.className.split(/\s+/).filter(function (c) { return c && jeter.indexOf(c) < 0; }).join(" "); },
    contains: function (c) { return self.className.split(/\s+/).indexOf(c) >= 0; },
    toggle: function (c, v) { var on = v === undefined ? !self.classList.contains(c) : !!v; if (on) self.classList.add(c); else { self.className = self.className.split(/\s+/).filter(function (x) { return x && x !== c; }).join(" "); } }
  };
}
El.prototype.setAttribute = function (k, v) { this._attrs[k] = String(v); };
El.prototype.getAttribute = function (k) { return k in this._attrs ? this._attrs[k] : null; };
El.prototype.hasAttribute = function (k) { return k in this._attrs; };
El.prototype.appendChild = function (e) { e.parentElement = this; this.children.push(e); return e; };
El.prototype.focus = function () { this.focus_appele++; };
Object.defineProperty(El.prototype, "textContent", {
  get: function () { return this._texte || this.children.map(function (c) { return c.textContent; }).join(""); },
  set: function (v) { this._texte = String(v); this.children = []; }
});
El.prototype.cloneNode = function () {
  var c = new El(this.tagName, this.className);
  for (var k in this._attrs) c._attrs[k] = this._attrs[k];
  c._texte = this._texte; c.scrollHeight = this.scrollHeight; c.clientHeight = this.clientHeight;
  var self = this;
  this.children.forEach(function (e) { c.appendChild(e.cloneNode(true)); });
  return c;
};
function correspond(el, sel) {
  return sel.trim().split(",").some(function (s) {
    s = s.trim();
    var tag = (s.match(/^[a-zA-Z][\w-]*/) || [""])[0];
    if (tag && el.tagName !== tag.toUpperCase()) return false;
    var neg = s.match(/:not\(\[([^\]]+)\]\)/);
    if (neg && el.hasAttribute(neg[1])) return false;
    var attr = s.replace(/:not\([^)]*\)/g, "").match(/\[([\w-]+)\]/);
    if (attr && !el.hasAttribute(attr[1])) return false;
    var cls = s.replace(/:not\([^)]*\)/g, "").match(/\.[\w-]+/g) || [];
    return cls.every(function (c) { return el.classList.contains(c.slice(1)); });
  });
}
El.prototype.querySelectorAll = function (sel) {
  var out = [];
  (function creuser(n) {
    n.children.forEach(function (e) { if (correspond(e, sel)) out.push(e); creuser(e); });
  })(this);
  return out;
};
El.prototype.querySelector = function (sel) { return this.querySelectorAll(sel)[0] || null; };
El.prototype.closest = function (sel) {
  var n = this;
  while (n) { if (correspond(n, sel)) return n; n = n.parentElement; }
  return null;
};

var racine = new El("div", "racine");
var ecouteurs = { click: [], keydown: [] };
global.document = {
  body: new El("body", ""),
  getElementById: function (id) { return racine.querySelectorAll("[id-" + id + "]")[0] || null; },
  querySelectorAll: function (s) { return racine.querySelectorAll(s); },
  querySelector: function (s) { return racine.querySelector(s); },
  addEventListener: function (t, f) { (ecouteurs[t] || (ecouteurs[t] = [])).push(f); }
};
global.window = {
  matchMedia: function () { return { matches: JSON.parse(process.env.CALME || "false") }; },
  requestAnimationFrame: function (f) { f(); },
  addEventListener: function () {}
};
global.module = undefined;

function poser(cls, id) {
  var e = new El("button", "case " + cls);
  if (id) e.setAttribute("id-" + id, "1");
  e.setAttribute("aria-pressed", "false");
  var verso = new El("span", "case-face case-verso");
  var texte = new El("span", "v-texte");
  var etat = new El("span", "v-etat");
  etat.textContent = "Énergie";
  verso.appendChild(texte); verso.appendChild(etat);
  e.appendChild(verso);
  return e;
}
var kal = new El("div", "kal"); kal.setAttribute("id-kal", "1"); racine.appendChild(kal);
var railA = new El("div", "kal-rail"); kal.appendChild(railA);
var railB = new El("div", "kal-rail inverse"); kal.appendChild(railB);
var c1 = railA.appendChild(poser("e1"));
var c2 = railA.appendChild(poser("e2"));
var c3 = railB.appendChild(poser("e3"));
var cadres = new El("div", "cadres"); racine.appendChild(cadres);
var c9 = cadres.appendChild(poser("e9"));
// UNE SEULE boîte déborde : c'est ce qui permet de dire que la marque est
// MESURÉE et non posée partout.
c1.querySelector(".v-texte").scrollHeight = 600;
c1.querySelector(".v-texte").clientHeight = 200;
var bR = new El("button", "vues"); bR.setAttribute("id-kal-v-rails", "1"); racine.appendChild(bR);
var bG = new El("button", "vues"); bG.setAttribute("id-kal-v-grille", "1"); racine.appendChild(bG);
bR.addEventListener = function (t, f) { this._r = f; };
bG.addEventListener = function (t, f) { this._g = f; };

require(process.argv[2]);

function cliquer(el) { ecouteurs.click.forEach(function (f) { f({ target: el }); }); }
function touche(k) { ecouteurs.keydown.forEach(function (f) { f({ key: k }); }); }

var rapport = { calme: JSON.parse(process.env.CALME || "false") };
rapport.copies = racine.querySelectorAll("[data-copie]").length;
rapport.derive = kal.classList.contains("derive");
rapport.copie_muette = racine.querySelectorAll("[data-copie]")
  .every(function (c) { return c.getAttribute("aria-hidden") === "true"
                            && c.getAttribute("tabindex") === "-1"; });
rapport.marque = { deborde: c1.querySelector(".v-etat").textContent,
                   normale: c3.querySelector(".v-etat").textContent };
// La marque REVIENT en arrière si le débordement cesse : preuve qu'elle est
// mesurée à chaque passage, et non posée une fois pour toutes.
c1.querySelector(".v-texte").scrollHeight = 100;
if (bR._r) { bG._g(); bR._r(); }
rapport.marque.apres_retour = c1.querySelector(".v-etat").textContent;

cliquer(c1);
rapport.un = { c1: c1.getAttribute("aria-pressed"), fige: document.body.classList.contains("kal-fige") };
cliquer(c2);
rapport.deux = { c1: c1.getAttribute("aria-pressed"), c2: c2.getAttribute("aria-pressed") };
touche("Escape");
rapport.echap = { c2: c2.getAttribute("aria-pressed"), focus: c2.focus_appele,
                  fige: document.body.classList.contains("kal-fige") };
cliquer(c9);
cliquer(racine);          // un clic hors carte
rapport.dehors = { c9: c9.getAttribute("aria-pressed"),
                   fige: document.body.classList.contains("kal-fige") };
if (bG._g) { bG._g(); }
rapport.grille = { classe: kal.classList.contains("grille"), derive: kal.classList.contains("derive"),
                   presse_r: bR.getAttribute("aria-pressed"), presse_g: bG.getAttribute("aria-pressed") };
if (bR._r) { bR._r(); }
rapport.retour = { classe: kal.classList.contains("grille"), derive: kal.classList.contains("derive") };
process.stdout.write(JSON.stringify(rapport));
"""


def _executer(calme=False):
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le script ne peut pas être exécuté")
    with tempfile.TemporaryDirectory() as d:
        h = os.path.join(d, "h.js")
        with io.open(h, "w", encoding="utf-8") as f:
            f.write(_HARNAIS)
        env = dict(os.environ, CALME="true" if calme else "false")
        p = subprocess.run([node, h, os.path.join(ICI, SCRIPT)],
                           capture_output=True, text=True, timeout=90, env=env)
    if p.returncode != 0:
        pytest.fail("le script ne tourne pas :\n%s" % (p.stderr or "")[-1500:])
    return json.loads(p.stdout)


JOUE = _executer()


def test_le_rail_est_double_et_les_copies_sortent_du_nom_accessible():
    """Sans les copies, la dérive glisserait jusqu'au vide puis sauterait.
    Avec elles mais sans précaution, un lecteur d'écran annoncerait six études
    là où il y en a trois."""
    assert JOUE["copies"] == 3, JOUE
    assert JOUE["derive"] is True
    assert JOUE["copie_muette"] is True


def test_SANS_MOUVEMENT_aucune_copie_n_est_posee():
    """Les deux vont ensemble : des copies sans dérive feraient lire chaque
    fiche deux fois. « prefers-reduced-motion » retire donc les deux."""
    calme = _executer(calme=True)
    assert calme["copies"] == 0, calme
    assert calme["derive"] is False


def test_une_seule_carte_est_retournee_a_la_fois():
    assert JOUE["un"] == {"c1": "true", "fige": True}
    assert JOUE["deux"] == {"c1": "false", "c2": "true"}


def test_echap_referme_ET_rend_le_focus_a_la_carte():
    assert JOUE["echap"]["c2"] == "false"
    assert JOUE["echap"]["focus"] == 1, "la carte fermée ne récupère pas le focus"
    assert JOUE["echap"]["fige"] is False


def test_un_clic_hors_carte_referme():
    assert JOUE["dehors"] == {"c9": "false", "fige": False}


def test_la_bascule_met_les_rails_a_plat_ET_coupe_la_derive():
    """UNE GRILLE QUI DÉRIVE SERAIT ILLISIBLE : la bascule doit faire les deux,
    et savoir revenir."""
    assert JOUE["grille"] == {"classe": True, "derive": False,
                              "presse_r": "false", "presse_g": "true"}
    assert JOUE["retour"] == {"classe": False, "derive": True}


def test_la_marque_de_defilement_est_MESUREE_et_pas_posee_partout():
    """LE DÉFAUT QUE CETTE RÈGLE PREND : une marque « défiler ↓ » posée sur
    toutes les cartes ne dit plus rien — et une carte qui déborde vraiment ne
    se distingue plus. On vérifie donc les trois états : marquée quand elle
    déborde, intacte quand elle ne déborde pas, et REVENUE quand le
    débordement cesse."""
    assert JOUE["marque"]["deborde"] == "défiler ↓"
    assert JOUE["marque"]["normale"] == "Énergie", (
        "une carte qui ne déborde pas a perdu son secteur")
    assert JOUE["marque"]["apres_retour"] == "Énergie", (
        "la marque ne redescend jamais : elle constate au lieu de mesurer")


# ═══════════════════════════════════════════════════════════════════════════
#  LE FORMAT LARGE DE LA BANDE DES CADRES
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE LA MESURE A ÉTABLI, ET QUI A DÉCIDÉ CE FORMAT. Le verso de « Postes
# haute tension » demandait 490 px de lecture dans une boîte de 259 px à
# 288 px de large : deux tiers du texte étaient derrière un défilement, sur une
# fiche que rien n'obligeait à la largeur des missions. À 978 px, le même texte
# tient entier — 257 px de contenu dans 257 px de boîte, zéro défilement.

def test_les_deux_cadres_portent_le_format_LARGE():
    """Sans le modificateur, elles reprennent 330 px et le verso redevient un
    tiroir : la mesure d'origine reste vraie, seul le format la corrigeait."""
    for cle in ("e9", "e10"):
        b = CARTES[cle]
        ouvre = b[:b.index(">")]
        assert "case--large" in ouvre, (
            "%s a perdu le format large : son verso redevient un défilement"
            % cle)


def test_le_format_large_ne_touche_PAS_les_cartes_de_mission():
    """LA POIGNÉE EST UNIQUE ET LOCALE. `--carte` vit dans styles.css, partagé
    avec /references : élargir « .case » y aurait élargi les dix cartes de
    références sans que personne ne le demande. Le modificateur est donc dans
    la feuille de la page, et les missions gardent leur largeur."""
    page = _src(PAGE)
    assert ".case--large{" in page, (
        "le format large n'est plus défini dans la feuille de la page")
    css = _src("styles.css")
    assert "case--large" not in css, (
        "le format large a migré dans la feuille partagée : il élargirait "
        "aussi les cartes de /references")
    for cle in CARTES:
        if cle in ("e9", "e10"):
            continue
        assert "case--large" not in CARTES[cle][:CARTES[cle].index(">")], (
            "%s, qui est une mission, a reçu le format large" % cle)


def test_le_recto_large_porte_une_accroche_et_pas_seulement_des_etiquettes():
    """LE DÉFAUT MESURÉ APRÈS LE PREMIER JET : à 978 px, badges, titre, rôle et
    étiquettes ne remplissaient que le tiers haut et laissaient 190 px de vide.
    Une carte large sans phrase montre surtout du fond."""
    for cle in ("e9", "e10"):
        b = CARTES[cle]
        recto = b[b.index('class="case-face case-recto"'):
                  b.index('class="case-face case-verso"')]
        assert '<span class="para">' in recto, (
            "%s : le recto large n'a pas d'accroche" % cle)
        assert len(_texte(recto)) >= 260, (
            "%s : le recto large porte %d caractères — il montrera du vide"
            % (cle, len(_texte(recto))))


def test_l_accroche_n_est_pas_REPETEE_du_recto_au_verso():
    """Le format large a déplacé l'accroche vers le recto. La laisser aussi au
    verso ferait lire deux fois la même phrase à qui retourne la carte — et
    prendrait la place des points techniques qui, eux, ne sont nulle part
    ailleurs."""
    for cle in ("e9", "e10"):
        b = CARTES[cle]
        d = b.index('class="case-face case-verso"')
        verso = b[d:]
        assert '<span class="para">' not in verso, (
            "%s : l'accroche est répétée au verso" % cle)
        assert verso.count('<span class="pt">') >= 2, (
            "%s : le verso ne porte plus au moins deux points techniques" % cle)
