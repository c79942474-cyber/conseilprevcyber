# -*- coding: utf-8 -*-
"""CINQUANTE-QUATRE CARTES NE SE PARCOURENT PAS.

CE QUI A DÉCLENCHÉ CE FICHIER. Le registre de la phase APD affiche cinquante-
quatre pièces à rédiger, classées par importance décroissante. C'est le bon
ordre pour DÉCIDER par quoi commencer. Ce n'est pas le geste qu'on fait pour
ATTEINDRE une pièce qu'on a déjà en tête : il fallait alors faire défiler la
grille entière en lisant chaque titre.

CE QUE CES RÈGLES GARDENT, DANS L'ORDRE DE CE QUI FAIT MAL :

1. QUE LE DÉCOMPTE SOIT VRAI. Un sélecteur qui annonce cinquante-quatre pièces
   et n'en propose que cinquante-deux ment sur ce qu'il contient — et ment
   précisément là où le lecteur vient chercher un chiffre.
2. QUE L'ORDRE SOIT CELUI DU REGISTRE. Obligatoire, indispensable, utile : ce
   qui bloque la phase d'abord. Un ordre alphabétique, ou l'ordre de rendu du
   serveur, ferait du sélecteur un second classement contredisant le premier.
3. QU'AUCUNE PIÈCE NE DISPARAISSE. Un caractère que le serveur ajouterait
   demain et que le sélecteur ne connaîtrait pas doit sortir malgré tout : le
   perdre le rendrait inatteignable, en silence.
4. QUE LE CLAVIER RENDE CE QU'UN <select> DONNAIT. On a remplacé un élément
   natif ; c'est le prix, et il se paie.
"""
import io
import json
import os
import re
import shutil
import subprocess

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOTEUR = io.open(os.path.join(ICI, 'ingenierie-dc.js'), encoding='utf-8').read()
PAGE = io.open(os.path.join(ICI, 'ingenierie-datacenter.html'), encoding='utf-8').read()
NODE = shutil.which('node')


def _fn(nom, indent='    '):
    """Une fonction du moteur, bornée à l'accolade de MÊME INDENTATION.

    Compter les accolades se perd sur « /[\\u0300-\\u036f]/ » — une
    quantification d'expression rationnelle en contient deux."""
    d = MOTEUR.index('function %s(' % nom)
    return MOTEUR[d:MOTEUR.index('\n%s}' % indent, d) + len(indent) + 2]


def _blocs_media(motif):
    """Le CONTENU de chaque @media dont la condition contient `motif`.

    Compté accolade par accolade : une requête média contient des règles, donc
    des accolades imbriquées, et « jusqu'à la prochaine } » s'arrête à la
    première règle."""
    out = []
    for m in re.finditer(r'@media[^{]*%s[^{]*\{' % re.escape(motif), PAGE):
        i, profondeur = m.end(), 1
        while i < len(PAGE) and profondeur:
            if PAGE[i] == '{':
                profondeur += 1
            elif PAGE[i] == '}':
                profondeur -= 1
            i += 1
        out.append(PAGE[m.end():i - 1])
    return out


def _piece(code, titre, caractere, ordre, nom=None):
    return {'code': code, 'titre': titre, 'caractere': caractere, 'ordre': ordre,
            'caractere_nom': nom or caractere.capitalize()}


# Un registre de laboratoire qui ressemble au vrai : trois caractères, des
# accents, des apostrophes, et un ordre de rendu volontairement mélangé.
PIECES = [
    _piece('APD-07', "Note de calcul thermique", 'utile', 7, 'Utile'),
    _piece('APD-01', "Programme technique détaillé", 'obligatoire', 1, 'Obligatoire'),
    _piece('APD-04', "Schéma unifilaire d'ensemble", 'indispensable', 4, 'Indispensable'),
    _piece('APD-02', "Bilan de puissance", 'obligatoire', 2, 'Obligatoire'),
    _piece('APD-09', "Étude d'énergie & sobriété", 'utile', 9, 'Utile'),
    _piece('APD-05', "Plan de zoning", 'indispensable', 5, 'Indispensable'),
]


def _rendre(pieces, cle='reste'):
    if not NODE:
        pytest.skip('node absent : le sélecteur ne peut pas être évalué')
    src = ('function esc(s){return String(s==null?"":s)'
           '.replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",'
           '">":"&gt;","\\"":"&quot;"}[c];});}\n'
           + _fn('sansAccent', '  ') + '\n' + _fn('selecteurPieces') + '\n')
    prog = src + 'console.log(JSON.stringify(selecteurPieces(%s,%s)));' % (
        json.dumps(pieces, ensure_ascii=False), json.dumps(cle))
    r = subprocess.run([NODE, '-e', prog], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        pytest.fail("selecteurPieces ne s'évalue pas :\n%s" % (r.stderr or '')[-1500:])
    return json.loads(r.stdout)


HTML = _rendre(PIECES)


# ── 1. LE DÉCOMPTE ───────────────────────────────────────────────────────

def test_le_bouton_annonce_le_nombre_total():
    m = re.search(r'class="ig-sel-n">(\d+)<', HTML)
    assert m, "le bouton n'affiche aucun décompte"
    assert int(m.group(1)) == len(PIECES), (
        "le bouton annonce %s pièces pour %d dans la liste"
        % (m.group(1), len(PIECES)))


def test_le_bouton_detaille_le_decompte_par_caractere():
    """C'est le chiffre que le lecteur vient chercher : combien d'obligatoires
    restent. Le total seul ne le dit pas."""
    for attendu in ('2 obligatoires', '2 indispensables', '2 utiles'):
        assert attendu in HTML, "le résumé du bouton n'annonce pas « %s »" % attendu


def test_chaque_groupe_porte_son_propre_decompte():
    entetes = re.findall(r'class="ig-sel-gh">.*?<b>(\d+)</b>', HTML)
    assert [int(x) for x in entetes] == [2, 2, 2], (
        "les décomptes de groupe ne correspondent pas : %s" % entetes)


def test_le_total_annonce_egale_le_nombre_d_options_rendues():
    """LE MENSONGE LE PLUS FACILE À COMMETTRE. Le décompte vient de la liste,
    les options viennent d'un regroupement : rien ne garantit qu'ils restent
    d'accord, et un écart ne se voit pas à l'œil."""
    annonce = int(re.search(r'class="ig-sel-n">(\d+)<', HTML).group(1))
    rendues = HTML.count('role="option"')
    assert annonce == rendues, (
        "le bouton annonce %d pièces, le panneau en propose %d" % (annonce, rendues))


def test_le_singulier_est_respecte():
    h = _rendre([PIECES[1]])
    assert 'pièce ·' in h and 'pièces ·' not in h, (
        "une pièce unique est annoncée au pluriel")
    assert '1 obligatoire<' in h.replace('</span>', '<'), (
        "le détail met un « s » à un seul élément")


# ── 2. L'ORDRE EST CELUI DU REGISTRE ─────────────────────────────────────

def test_les_groupes_suivent_l_importance_decroissante():
    """« Ce qui bloque la phase d'abord, ce qui enrichit le dossier ensuite » —
    c'est la promesse écrite au-dessus du registre. Un sélecteur qui classe
    autrement en fait un second classement, qui contredit le premier."""
    noms = re.findall(r'class="ig-sel-gh"><i[^>]*></i>([^<]+)<b>', HTML)
    assert noms == ['Obligatoire', 'Indispensable', 'Utile'], (
        "les groupes sortent dans l'ordre %s" % noms)


def test_l_ordre_ne_depend_pas_de_l_ordre_d_arrivee():
    """La liste de laboratoire arrive délibérément mélangée. Si le sélecteur se
    contentait de suivre le serveur, cette règle passerait par accident le jour
    où le serveur trie déjà — et échouerait le jour où il cesse."""
    melange = [PIECES[0], PIECES[4], PIECES[2], PIECES[5], PIECES[1], PIECES[3]]
    noms = re.findall(r'class="ig-sel-gh"><i[^>]*></i>([^<]+)<b>', _rendre(melange))
    assert noms == ['Obligatoire', 'Indispensable', 'Utile']


def test_dans_un_groupe_l_ordre_du_registre_est_conserve():
    """À l'intérieur d'un caractère, c'est le rang calculé par le serveur qui
    ordonne. Le sélecteur ne le recalcule pas : il le respecte."""
    codes = re.findall(r'data-code="(APD-\d+)"', HTML)
    assert codes == ['APD-01', 'APD-02', 'APD-04', 'APD-05', 'APD-07', 'APD-09'], codes


def test_un_caractere_inconnu_ne_fait_pas_disparaitre_sa_piece():
    """LA PERTE SILENCIEUSE. Le serveur peut ajouter un caractère demain ; s'il
    n'est pas dans la liste d'ordre du script, filtrer sur cette liste rendrait
    la pièce inatteignable sans qu'aucun message ne le signale — et le décompte
    du bouton deviendrait faux."""
    plus = PIECES + [_piece('APD-12', "Pièce d'un caractère futur", 'recommande', 12,
                            'Recommandé')]
    h = _rendre(plus)
    assert 'APD-12' in h, "la pièce au caractère inconnu a disparu du sélecteur"
    assert int(re.search(r'class="ig-sel-n">(\d+)<', h).group(1)) == len(plus)
    noms = re.findall(r'class="ig-sel-gh"><i[^>]*></i>([^<]+)<b>', h)
    assert noms[:3] == ['Obligatoire', 'Indispensable', 'Utile'], (
        "le caractère inconnu s'est glissé avant les rangs connus : %s" % noms)
    assert noms[-1] == 'Recommandé', "il devrait passer en queue : %s" % noms


def test_aucune_piece_sans_selecteur():
    assert _rendre([]) == '', "un groupe vide affiche un sélecteur qui n'ouvre rien"


# ── 3. CE QUE CHAQUE ENTRÉE MONTRE ───────────────────────────────────────

def test_chaque_entree_porte_le_code_le_titre_et_le_rang():
    """C'est ce qu'un <select> natif ne pouvait pas distinguer, et la raison
    pour laquelle on ne l'a pas employé."""
    bloc = HTML[HTML.index('data-code="APD-01"'):]
    bloc = bloc[:bloc.index('</div>') + 6]
    assert '<code>APD-01</code>' in bloc
    assert 'Programme technique détaillé' in bloc
    assert 'n° 1' in bloc


def test_la_recherche_est_insensible_aux_accents():
    """Un registre français sans normalisation oblige à composer les accents
    pour atteindre la moitié des pièces : « energie » doit trouver
    « Étude d'énergie »."""
    m = re.search(r'data-code="APD-09" data-cherche="([^"]*)"', HTML)
    assert m, "l'entrée ne porte pas de clé de recherche"
    assert 'energie' in m.group(1), (
        "la clé de recherche garde ses accents : « %s »" % m.group(1))
    assert 'etude' in m.group(1), "la clé n'est pas en minuscules"


def test_la_cle_de_recherche_couvre_le_code_et_le_titre():
    m = re.search(r'data-code="APD-04" data-cherche="([^"]*)"', HTML)
    assert 'apd-04' in m.group(1) and 'unifilaire' in m.group(1)


def test_un_titre_hostile_ne_produit_pas_de_balise():
    h = _rendre([_piece('X-1', '<img src=x onerror=alert(1)>', 'utile', 1, 'Utile')])
    assert '<img' not in h
    assert '&lt;img src=x onerror=alert(1)&gt;' in h


# ── 4. LE COMPOSANT EST UN LISTBOX, PAS UNE DIV CLIQUABLE ────────────────

def test_le_bouton_declare_ce_qu_il_ouvre():
    assert 'aria-haspopup="listbox"' in HTML
    assert 'aria-expanded="false"' in HTML
    m = re.search(r'aria-controls="([^"]+)"', HTML)
    assert m, "le bouton ne désigne pas le panneau qu'il commande"
    assert 'id="%s"' % m.group(1) in HTML, (
        "aria-controls désigne « %s », qui n'existe pas dans le rendu" % m.group(1))


def test_le_panneau_est_un_listbox_et_ses_entrees_des_options():
    assert 'role="listbox"' in HTML
    assert HTML.count('role="option"') == len(PIECES)
    assert HTML.count('aria-selected="false"') == len(PIECES)


def test_chaque_option_a_un_identifiant_unique():
    """aria-activedescendant DÉSIGNE une option par son identifiant : deux
    options homonymes et le lecteur d'écran annonce la mauvaise."""
    ids = re.findall(r'class="ig-sel-o" role="option" aria-selected="false" id="([^"]+)"', HTML)
    assert len(ids) == len(PIECES), ids
    assert len(set(ids)) == len(ids), "identifiants d'option en double"


def test_deux_selecteurs_sur_la_page_ne_se_confondent_pas():
    """Le registre porte deux groupes — à rédiger, rédigées. Des identifiants
    partagés feraient commander le second panneau par le premier bouton."""
    a = set(re.findall(r'id="(ig-sel-[^"]+)"', _rendre(PIECES, 'reste')))
    b = set(re.findall(r'id="(ig-sel-[^"]+)"', _rendre(PIECES, 'faits')))
    assert not (a & b), "identifiants partagés entre les deux sélecteurs : %s" % (a & b)


def test_chaque_groupe_est_annonce_avec_son_effectif():
    labels = re.findall(r'role="group" aria-label="([^"]+)"', HTML)
    assert labels == ['Obligatoire : 2 pièces', 'Indispensable : 2 pièces',
                      'Utile : 2 pièces'], labels


# ── 5. LE CLAVIER REND CE QU'UN <select> DONNAIT ─────────────────────────

@pytest.mark.parametrize('touche,pourquoi', [
    ('ArrowDown', "descendre dans la liste"),
    ('ArrowUp', "remonter"),
    ('Home', "revenir à la première pièce"),
    ('End', "aller à la dernière"),
    ('Enter', "choisir"),
    ('Escape', "renoncer et revenir au bouton"),
    ('Tab', "sortir du composant"),
])
def test_le_panneau_traite_la_touche(touche, pourquoi):
    """UN COMPOSANT QUI NE REND PAS TOUT CE QUE L'ÉLÉMENT NATIF DONNAIT est un
    recul. On l'a remplacé pour afficher des pastilles et des décomptes ; on ne
    l'a pas remplacé pour retirer le clavier."""
    d = MOTEUR.index('panneau.addEventListener("keydown"')
    bloc = MOTEUR[d:MOTEUR.index('\n      });', d)]
    assert '"%s"' % touche in bloc, (
        "le panneau ne traite pas %s — impossible de %s" % (touche, pourquoi))


def test_le_bouton_s_ouvre_au_clavier():
    d = MOTEUR.index('bouton.addEventListener("keydown"')
    bloc = MOTEUR[d:MOTEUR.index('\n      });', d)]
    for t in ('ArrowDown', 'ArrowUp', 'Enter'):
        assert '"%s"' % t in bloc, "le bouton ne s'ouvre pas avec %s" % t


def test_echap_rend_le_focus_au_bouton():
    """Sans cela, Échap laisse le focus nulle part et la tabulation suivante
    repart du haut du document."""
    d = MOTEUR.index('function fermer(rendreFocus)')
    bloc = MOTEUR[d:MOTEUR.index('\n      }', d)]
    assert 'bouton.focus()' in bloc
    d2 = MOTEUR.index('e.key === "Escape"')
    assert 'fermer(true)' in MOTEUR[d2:d2 + 90], (
        "Échap ferme sans rendre le focus au bouton")


def test_le_focus_ne_saute_pas_d_option_en_option():
    """aria-activedescendant, pas focus() : déplacer le focus réel dans une
    liste longue fait défiler le document et le panneau se dérobe."""
    d = MOTEUR.index('function viser(i)')
    bloc = MOTEUR[d:MOTEUR.index('\n      }', d)]
    assert 'aria-activedescendant' in bloc
    assert 'o.focus()' not in bloc


def test_le_clic_dehors_ferme_le_panneau():
    assert 'if (!sel.contains(e.target)) fermer(false);' in MOTEUR, (
        "le panneau reste ouvert par-dessus les cartes qu'il sert à atteindre")


# ── 6. LE MOUVEMENT SUIT LA PRÉFÉRENCE SYSTÈME ───────────────────────────

def test_le_defilement_respecte_la_preference_de_mouvement():
    """La CSS ne peut rien ici : le défilement doux est demandé par le script.
    « prefers-reduced-motion » doit donc être lu en JavaScript, sans quoi la
    préférence est ignorée précisément sur le seul mouvement de trente cartes
    que la page produise."""
    d = MOTEUR.index('function allerALaPiece')
    bloc = MOTEUR[d:MOTEUR.index('\n  }', d)]
    assert 'prefers-reduced-motion' in bloc, (
        "le défilement animé ignore la préférence système")
    assert '"auto"' in bloc, "aucune solution de repli sans animation"


def test_le_repere_visuel_s_efface_de_lui_meme():
    d = MOTEUR.index('function allerALaPiece')
    bloc = MOTEUR[d:MOTEUR.index('\n  }', d)]
    assert 'setTimeout' in bloc and 'remove("ig-vise")' in bloc, (
        "le surlignage reste : il se lira comme un état de la pièce")


def test_l_animation_est_neutralisee_sous_preference_reduite():
    blocs = _blocs_media('prefers-reduced-motion')
    assert blocs, "la page ne prévoit rien pour « réduire les animations »"
    # LA PAGE EN COMPTE PLUSIEURS, et la première ne parle pas du sélecteur.
    # Une règle qui ne lisait que celle-là accusait un code correct — et aurait
    # laissé passer l'inverse le jour où l'ordre des blocs change.
    vise = [b for b in blocs if 'ig-vise' in b]
    assert vise, ("l'animation du repère n'est neutralisée dans aucun des %d "
                  "blocs « prefers-reduced-motion » de la page" % len(blocs))
    assert 'animation:none' in vise[0]


# ── 7. LE RENDU EST BRANCHÉ, ET STYLÉ ────────────────────────────────────

def test_le_selecteur_est_pose_dans_chaque_groupe_du_registre():
    d = MOTEUR.index('function groupe(titre, liste, sous, marque)')
    bloc = MOTEUR[d:MOTEUR.index('\n    }', d)]
    assert 'selecteurPieces(liste,' in bloc, (
        "le sélecteur est écrit mais le registre ne l'affiche pas")


def test_le_comportement_est_branche_apres_chaque_redessin():
    d = MOTEUR.index('function brancherPieces()')
    bloc = MOTEUR[d:d + 2500]
    assert 'brancherSelecteurs()' in bloc, (
        "le sélecteur est rendu mais aucun événement ne lui est attaché : il "
        "s'affiche et ne fait rien")


def test_toute_classe_du_rendu_est_stylee():
    """LA CSS DÉCIDE DE LA MISE EN PAGE, PAS L'INTENTION. Une classe absente de
    la feuille de style produit un bloc sans forme, et rien ne le signale."""
    manquantes = []
    for attr in re.findall(r'class="([^"]+)"', HTML):
        for c in attr.split():
            if not c.startswith('ig-sel'):
                continue
            if not re.search(r'\.%s[\s,{:\[]' % re.escape(c), PAGE):
                manquantes.append(c)
    assert not manquantes, (
        "classe(s) rendue(s) et stylée(s) nulle part : %s"
        % ', '.join(sorted(set(manquantes))))


def test_le_panneau_est_masque_tant_qu_on_ne_l_ouvre_pas():
    assert 'role="listbox" tabindex="-1"' in HTML
    assert re.search(r'role="listbox"[^>]*hidden>', HTML), (
        "le panneau s'affiche déplié au chargement, sous la grille")


def test_le_panneau_ne_pousse_pas_la_grille():
    """Un panneau dans le flux décalerait cinquante-quatre cartes à chaque
    ouverture. Il flotte au-dessus, et son conteneur lui sert de repère."""
    assert re.search(r'\.ig-sel\{[^}]*position:relative', PAGE)
    assert re.search(r'\.ig-sel-p\{[^}]*position:absolute', PAGE)


@pytest.mark.parametrize('regle,quoi', [
    ('ig-sel-p', "le panneau"),
    ('ig-sel-gh', "l'en-tête de groupe, qui reste collée pendant le défilement"),
])
def test_le_panneau_reste_opaque_meme_sans_jeton_de_couleur(regle, quoi):
    """LE SEUL ÉLÉMENT DE LA PAGE QUI DOIT ÊTRE OPAQUE, et le défaut a été vu
    pour de bon : sur un rendu où la feuille de style partagée ne s'était pas
    chargée, `background:var(--bg2)` s'est résolu en transparent et le texte des
    cartes traversait la liste. En production le jeton existe ; ailleurs dans la
    page son absence serait cosmétique. Ici elle casse le composant, parce qu'il
    flotte au-dessus de cinquante-quatre cartes."""
    m = re.search(r'\.%s\{(.*?)\}' % regle, PAGE, re.S)
    assert m, "%s n'est pas stylé" % quoi
    fond = re.search(r'background:\s*var\(--[a-z0-9-]+\s*,\s*(#[0-9A-Fa-f]{3,8})\s*\)',
                     m.group(1))
    assert fond, ("%s n'a pas de couleur de repli : un jeton manquant le rend "
                  "transparent" % quoi)


def test_les_entetes_de_groupe_restent_visibles_au_defilement():
    """Au bout de vingt lignes, on ne sait plus si l'on est encore dans les
    obligatoires — et c'est la seule chose que le sélecteur devait dire."""
    m = re.search(r'\.ig-sel-gh\{([^}]*)\}', PAGE)
    assert m and 'position:sticky' in m.group(1), (
        "les en-têtes de groupe défilent avec la liste")


def test_la_pastille_de_chaque_caractere_porte_sa_couleur():
    """Les couleurs sont celles des cartes du registre. Un sélecteur qui en
    emploie d'autres invente un second code visuel pour la même information."""
    for classe, couleur in (('d-obligatoire', '#F2A65A'),
                            ('d-indispensable', '#5BC8E8'),
                            ('d-utile', '#9FB3C8')):
        m = re.search(r'\.ig-sel-d\.%s\{([^}]*)\}' % classe, PAGE)
        assert m, "la pastille « %s » n'est pas stylée" % classe
        assert couleur in m.group(1), (
            "« %s » n'emploie pas la couleur du registre (%s)" % (classe, couleur))
