"""LE FOND DU BANDEAU — affiche d'abord, vidéo ensuite, et seulement si.

CE QUI A DÉCLENCHÉ CE FICHIER. Une demande de fond animé, et une contrainte
posée d'emblée : image fixe d'abord, vidéo ensuite, et seulement sur écran
large. Trois défauts sont apparus en éprouvant le montage dans un vrai
navigateur — aucun ne se voyait à la lecture du code.

PREMIER DÉFAUT : L'ÉCHEC NE SE SIGNALAIT PAS LÀ OÙ ON L'ATTENDAIT. Sans
fichier vidéo — l'état du site tant qu'aucun n'est déposé — les événements
reçus sont :

    video:loadstart · source0:error · source1:error
    networkState = 3 (NETWORK_NO_SOURCE), readyState = 0
    v.error = null, et la promesse de play() ne se règle JAMAIS

Autrement dit : `error` se déclenche sur les balises `<source>`, pas sur la
`<video>` ; l'élément ne porte aucune erreur ; attendre le rejet de `play()`
revient à attendre indéfiniment. Une première version guettait `video.error`
et ce rejet : elle laissait un élément vidéo mort au-dessus de l'affiche,
sans que rien ne le signale.

DEUXIÈME DÉFAUT : UNE COLLISION DE SPÉCIFICITÉ. `.fond-hero > *`, écrite pour
faire passer le contenu au-dessus du décor, l'emporte sur `.fond-hero-video`
et lui imposait `position:relative`. La vidéo retombait dans le flux et son
`left:50%` la décalait hors de la fenêtre — mesuré : `156..1596` pour une
fenêtre de 1440, soit 156 px de débordement horizontal. Les pseudo-éléments,
eux, échappaient à la règle : le fond semblait donc juste tant que la vidéo
ne démarrait pas.

TROISIÈME DÉFAUT : LA GÉOMÉTRIE. Mesurée, la section fait 1032 × 1407 — plus
haute que large, et bornée par un conteneur de 1080 px. Une vidéo panoramique
y était agrandie d'un facteur deux et recadrée jusqu'à n'en montrer que le
milieu, tout en s'arrêtant net à 1032 px de large.

CE QUE CES CONTRÔLES NE PEUVENT PAS FAIRE. Juger l'image. Ils vérifient les
mécanismes : que les tranches d'octets sont servies (sans quoi Safari refuse
de lire), que la vidéo n'est jamais dans le HTML livré, que les conditions de
refus sont toutes présentes, et que les fichiers annoncés existent.
"""
import io
import os
import re
import struct
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

os.environ.setdefault('FLASK_SECRET_KEY', 'recette-fond-hero')

import app as application  # noqa: E402

MEDIA = os.path.join(ICI, 'media')
CSS = io.open(os.path.join(ICI, 'styles.css'), encoding='utf-8').read()
JS = io.open(os.path.join(ICI, 'fond-hero.js'), encoding='utf-8').read()
PAGE = io.open(os.path.join(ICI, 'index.html'), encoding='utf-8').read()

_IP = [60]


def _get(chemin, **entetes):
    _IP[0] += 1
    e = {'X-Forwarded-For': '198.51.100.%d' % (_IP[0] % 250 + 1),
         'User-Agent': 'Mozilla/5.0 (recette)',
         'Accept-Language': 'fr-FR,fr;q=0.9', 'Accept': '*/*'}
    e.update(entetes)
    return application.app.test_client().get(chemin, headers=e)


def _dimensions_webp(chemin):
    """Largeur et hauteur d'un WebP, lues dans son en-tête.

    Trois variantes coexistent (VP8 avec perte, VP8L sans perte, VP8X
    étendu) et elles ne rangent pas la taille au même endroit. On les
    distingue plutôt que de supposer laquelle l'encodeur a produite."""
    d = io.open(chemin, 'rb').read(40)
    assert d[:4] == b'RIFF' and d[8:12] == b'WEBP', chemin
    tag = d[12:16]
    if tag == b'VP8 ':
        l, h = struct.unpack('<HH', d[26:30])
        return l & 0x3FFF, h & 0x3FFF
    if tag == b'VP8L':
        b = struct.unpack('<I', d[21:25])[0]
        return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
    if tag == b'VP8X':
        l = d[24] | (d[25] << 8) | (d[26] << 16)
        h = d[27] | (d[28] << 8) | (d[29] << 16)
        return l + 1, h + 1
    raise AssertionError('WebP de type inconnu : %r' % tag)


# ── LES FICHIERS ANNONCÉS EXISTENT ───────────────────────────────────────

def test_tout_media_appele_par_la_feuille_de_style_existe():
    """S'il manque, le bandeau retombe sur le dégradé sans qu'aucune erreur ne
    s'affiche — un défaut parfaitement silencieux.

    ON RELIT LA FEUILLE PLUTÔT QUE DE RECOPIER DEUX NOMS. La règle citait les
    fichiers à la main ; renommer une seule des deux occurrences de
    `image-set` la laissait verte, l'autre portant encore le bon nom. On
    vérifie donc TOUT ce que la feuille appelle."""
    appeles = set(re.findall(r'url\("/media/([^"]+)"\)', CSS))
    assert appeles, "la feuille de style n'appelle aucun média"
    for nom in sorted(appeles):
        assert os.path.isfile(os.path.join(MEDIA, nom)), (
            "%s est appelé par styles.css mais absent de media/" % nom)


def test_les_deux_definitions_de_laffiche_sont_declarees():
    """`image-set` est écrit deux fois — la version standard et la version
    préfixée pour les navigateurs anciens. Les deux doivent nommer les mêmes
    fichiers, sinon un visiteur sur deux reçoit autre chose."""
    jeux = re.findall(r'image-set\(([^;]+?)\)\s*,', CSS.replace("\n", " "))
    noms = [set(re.findall(r'/media/([^"]+)', j)) for j in jeux]
    assert len(noms) >= 2, "une seule déclaration image-set"
    assert all(n == noms[0] for n in noms), noms


def test_les_deux_affiches_ont_le_meme_cadrage():
    """Le navigateur choisit l'une ou l'autre selon l'écran. Deux cadrages
    différents feraient sauter l'image d'un appareil à l'autre."""
    l1, h1 = _dimensions_webp(os.path.join(MEDIA, 'hero-fond-1600.webp'))
    l2, h2 = _dimensions_webp(os.path.join(MEDIA, 'hero-fond-3200.webp'))
    assert abs((l1 / h1) - (l2 / h2)) < 0.01, "%dx%d vs %dx%d" % (l1, h1, l2, h2)
    assert (l2, h2) == (l1 * 2, h1 * 2), "la version 2x n'est pas exactement double"


def test_laffiche_est_panoramique():
    """La section mesure 1032 × 1407 : plus haute que large. C'est le BANDEAU
    qui est panoramique, pas la section, et l'affiche doit épouser le bandeau
    — sinon elle est agrandie et recadrée jusqu'à n'en montrer que le milieu."""
    l, h = _dimensions_webp(os.path.join(MEDIA, 'hero-fond-1600.webp'))
    assert 2.0 < l / h < 3.2, "cadrage %dx%d (rapport %.2f)" % (l, h, l / h)


def test_laffiche_reste_legere():
    """Elle est chargée par TOUT LE MONDE, y compris ceux qui n'auront jamais
    la vidéo. C'est elle qu'il faut garder petite, pas la vidéo."""
    o = os.path.getsize(os.path.join(MEDIA, 'hero-fond-1600.webp'))
    assert o < 120 * 1024, "affiche de %d o : trop lourde pour un fond" % o


# ── LE SERVICE DES MÉDIAS ────────────────────────────────────────────────

def test_laffiche_est_servie_avec_son_type():
    r = _get('/media/hero-fond-1600.webp')
    assert r.status_code == 200
    assert r.headers['Content-Type'].startswith('image/webp')


@pytest.mark.parametrize('tranche,attendu', [
    ('bytes=0-1', 2),      # LA PREMIÈRE QUESTION DE SAFARI
    ('bytes=0-99', 100),
])
def test_les_tranches_doctets_sont_servies(tranche, attendu):
    """SANS CELA, SAFARI NE LIT PAS LA VIDÉO — ni sur iOS ni sur macOS. Il
    demande d'abord les premiers octets ; une réponse 200 avec le fichier
    entier lui dit que la source ne sait pas se positionner, et il abandonne
    sans message d'erreur. Juste un fond noir."""
    r = _get('/media/hero-fond-1600.webp', Range=tranche)
    assert r.status_code == 206, (
        "réponse %d au lieu de 206 : les requêtes partielles ne sont pas "
        "servies" % r.status_code)
    assert r.headers.get('Content-Range')
    assert len(r.get_data()) == attendu


def test_le_service_annonce_quil_accepte_les_tranches():
    assert _get('/media/hero-fond-1600.webp').headers.get('Accept-Ranges') == 'bytes'


def test_une_video_nest_jamais_comprimee():
    """Comprimer un flux déjà compressé le fait grossir, et casse les
    requêtes partielles au passage."""
    for nom in ('hero-fond.webm', 'hero-fond.mp4'):
        if not os.path.isfile(os.path.join(MEDIA, nom)):
            continue
        r = _get('/media/' + nom, **{'Accept-Encoding': 'gzip, deflate, br'})
        assert r.headers.get('Content-Encoding') is None, nom


@pytest.mark.parametrize('chemin', [
    '/media/app.py', '/media/styles.css', '/media/inexistant.mp4',
    '/media/..%2Fapp.py',
])
def test_un_chemin_hors_media_ne_sort_pas(chemin):
    assert _get(chemin).status_code == 404, chemin


def test_un_fichier_interdit_DANS_media_ne_sort_pas():
    """LE CONTRÔLE PRÉCÉDENT NE PROUVAIT RIEN SUR LA LISTE BLANCHE. Aucun de
    ses chemins n'existe dans `media/` : c'est le contrôle d'existence qui
    répondait 404, et retirer entièrement la liste blanche le laissait passer
    — une mutation l'a montré. On dépose donc pour de bon un fichier à
    extension interdite, ce qui est exactement le scénario redouté : une
    sauvegarde ou un fichier de configuration oublié dans le dossier."""
    piege = os.path.join(MEDIA, 'sauvegarde-recette.env')
    io.open(piege, 'w').write('MOT_DE_PASSE=ne-doit-pas-sortir')
    try:
        r = _get('/media/sauvegarde-recette.env')
        assert r.status_code == 404, (
            "un fichier .env déposé dans media/ est téléchargeable (%d)"
            % r.status_code)
        assert b'ne-doit-pas-sortir' not in r.get_data()
    finally:
        os.remove(piege)


def test_les_medias_se_gardent_longtemps():
    cc = _get('/media/hero-fond-1600.webp').headers.get('Cache-Control') or ''
    assert 'max-age' in cc and 'no-store' not in cc


# ── LA VIDÉO N'EST PAS DANS LA PAGE LIVRÉE ───────────────────────────────

def test_aucune_balise_video_dans_le_html():
    """C'EST TOUT LE CONTRAT. Une `<video autoplay>` écrite dans le document
    commence son téléchargement AVANT le texte : quelques méga-octets passent
    devant le contenu dans la file du réseau. Ici la vidéo n'existe pas tant
    que les conditions ne sont pas réunies — rien à télécharger, rien à
    annuler."""
    assert '<video' not in PAGE.lower(), (
        "une balise vidéo figure dans le HTML livré : elle se chargera avant "
        "le texte, sur tous les appareils")


def test_le_bandeau_declare_ses_fichiers_et_son_seuil():
    assert 'data-fond-hero' in PAGE
    assert re.search(r'data-video="[\w.-]+\.(mp4|webm)"', PAGE)
    assert re.search(r'data-largeur-mini="\d+"', PAGE)
    assert '/fond-hero.js' in PAGE


def test_retirer_lattribut_suffit_a_desactiver_la_video():
    """Il doit rester possible de couper la vidéo sans toucher au script ni à
    la feuille de style — sinon personne n'osera le faire."""
    assert 'if (!video && !videoWebm) return' in JS


# ── LES CONDITIONS DE REFUS ──────────────────────────────────────────────

@pytest.mark.parametrize('condition,repere', [
    # L'EXPRESSION, PAS LE NOM. Chercher « LARGEUR_MINI » laissait passer un
    # `if (false)` : la constante restait déclarée plus haut, donc présente.
    ("écran étroit", '< LARGEUR_MINI'),
    ("mouvement réduit", 'prefers-reduced-motion'),
    ("appareil tactile", 'pointer: coarse'),
    ("économiseur de données", 'saveData'),
    ("connexion lente", 'effectiveType'),
    ("onglet caché", 'visibilitychange'),
    ("bandeau hors écran", 'IntersectionObserver'),
])
def test_la_condition_de_refus_est_presente(condition, repere):
    """Chacune couvre une part réelle des visites. Ensemble, elles font que
    l'affiche est ce que verra le plus grand nombre — d'où l'exigence qu'elle
    soit belle, et pas un pis-aller."""
    assert repere in JS, "la condition « %s » a disparu" % condition


def test_lechec_se_detecte_sur_les_sources_epuisees():
    """LE DÉFAUT MESURÉ. `error` ne se déclenche pas sur la `<video>` mais sur
    ses `<source>`, et la promesse de `play()` ne se règle jamais. Guetter
    l'un ou l'autre laisse un élément mort dans la page."""
    assert 'echouees' in JS and 'sources.length' in JS
    i = JS.index('echouees')
    assert 'abandonne' in JS[i:i + 400]


def test_une_butee_de_temps_existe():
    """Une source peut ne jamais répondre sans qu'aucun événement ne
    survienne : serveur muet, fichier tronqué."""
    assert re.search(r'setTimeout\(function \(\) \{\s*if \(!fini\) abandonne', JS)


def test_la_video_est_muette_et_en_ligne():
    """`muted` AVANT `autoplay`, et `playsinline` : sans le premier, iOS
    refuse la lecture automatique ; sans le second, il ouvre le lecteur en
    plein écran par-dessus le site."""
    i, j = JS.index('v.muted = true'), JS.index('v.autoplay = true')
    assert i < j, "`muted` est posé après `autoplay` : iOS refusera de lire"
    assert 'playsInline' in JS and 'playsinline' in JS


def test_la_video_ne_se_charge_quapres_la_page():
    """Un ornement passe après le contenu."""
    assert 'requestIdleCallback' in JS
    assert re.search(r'addEventListener\("load", demarrer', JS)


# ── LA MISE EN PAGE ──────────────────────────────────────────────────────

def test_la_video_echappe_a_la_regle_qui_leve_le_contenu():
    """LE DÉFAUT MESURÉ : `.fond-hero > *` l'emporte en spécificité sur
    `.fond-hero-video` et lui imposait `position:relative`. La vidéo
    retombait dans le flux et se décalait de 156 px hors de la fenêtre."""
    assert '.fond-hero > *:not(.fond-hero-video)' in CSS, (
        "la règle qui lève le contenu capture aussi la vidéo : elle sortira "
        "de la fenêtre")


def test_le_fond_sort_du_conteneur():
    """La section vit dans un conteneur de 1080 px centré. Un fond qui s'y
    arrête laisse le dégradé de page de part et d'autre — ce n'est plus un
    fond d'écran."""
    assert '100vw' in CSS and '-50vw' in CSS


def test_le_bandeau_a_une_hauteur_propre():
    """Il ne couvre pas toute la section, mesurée à 1407 px de haut."""
    # LA DÉCLARATION DOIT ÊTRE DANS LA RÈGLE DE BASE, PAS SEULEMENT DANS LA
    # REQUÊTE MÉDIA MOBILE. Deux versions de ce contrôle ont été trop faibles :
    # chercher « --fond-h » laissait passer un retrait (le nom subsiste dans
    # les règles qui l'utilisent), et chercher « --fond-h:clamp( » laissait
    # passer le retrait de la SEULE déclaration bureau, celle du mobile
    # suffisant à satisfaire la chaîne. Sur grand écran, la hauteur devenait
    # alors invalide et le bandeau disparaissait.
    i = CSS.index('.fond-hero{')
    base = CSS[i:CSS.index('}', i)]
    assert '--fond-h:' in base, (
        "la hauteur du bandeau n'est pas déclarée dans la règle de base : "
        "elle sera invalide partout sauf là où une requête média la repose")


def test_le_raccord_se_fait_par_transparence():
    """Un aplat de couleur en bas du voile laissait une ligne horizontale
    visible : il fallait qu'il tombe juste sur le fond de page à cette
    hauteur, et il n'y tombait pas."""
    assert 'mask-image' in CSS


def test_laffiche_reste_sous_la_video():
    """Elle doit rester visible PENDANT tout le chargement : sans cela on
    remplace une image fixe par un rectangle noir le temps du décodage."""
    assert re.search(r'\.fond-hero-video\{[^}]*opacity:0', CSS.replace('\n', ''))
    assert 'v.style.opacity = "0"' in JS
    assert 'v.style.opacity = "1"' in JS
