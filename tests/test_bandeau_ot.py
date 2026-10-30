"""LE BANDEAU « OFFSHORE SUBSTATIONS — OT SECURITY », EN TÊTE DE L'ACCUEIL.

CE QUI EST DEMANDÉ. Un bandeau plus long que large, tiré de l'animation
« Offshore Substation Expert — UK », qui met en avant la cybersécurité
industrielle (OT) des sous-stations en mer, posé AU-DESSUS du titre
« Concevoir et sécuriser vos installations industrielles », et qui mène au
profil LinkedIn.

CE QUI EST MESURÉ ICI :
  · la vidéo publiée est bien celle que rend sa source (même chronologie),
    au format du bandeau LinkedIn, lisible par tout navigateur ;
  · la source met l'OT en tête ;
  · le bandeau est au-dessus du titre, et TOUT ENTIER un lien vers le profil,
    dans un nouvel onglet — la pause, elle, reste hors du lien ;
  · la page ne livre que l'affiche (contrat de tests/test_fond_hero.py) ; la
    vidéo, insérée après le chargement, est muette, en boucle, en ligne, et
    cède au mouvement réduit comme à la pause demandée.
"""
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

os.environ.setdefault('FLASK_SECRET_KEY', 'recette-bandeau-ot')

import app as application  # noqa: E402

PROFIL = 'https://www.linkedin.com/in/cerfchristophe'
VIDEO = os.path.join(ICI, 'media', 'bandeau-offshore-ot.mp4')
AFFICHE = os.path.join(ICI, 'media', 'bandeau-offshore-ot.jpg')
SOURCE_DIR = os.path.join(ICI, 'outils', 'bandeau_offshore_ot')


def _lire(*chemin):
    return io.open(os.path.join(ICI, *chemin), encoding='utf-8').read()


PAGE = _lire('index.html')
CSS = _lire('styles.css')
JS = _lire('bandeau-ot.js')
SOURCE = _lire('outils', 'bandeau_offshore_ot', 'bandeau.html')

_IP = [120]


def _get(chemin, **entetes):
    _IP[0] += 1
    e = {'X-Forwarded-For': '198.51.100.%d' % (_IP[0] % 250 + 1),
         'User-Agent': 'Mozilla/5.0 (recette)',
         'Accept-Language': 'fr-FR,fr;q=0.9', 'Accept': '*/*'}
    e.update(entetes)
    return application.app.test_client().get(chemin, headers=e)


def _figure():
    m = re.search(r'<figure class="bandeau-ot"[^>]*>(.*?)</figure>', PAGE, re.S)
    assert m, "le bandeau n'est plus dans l'accueil"
    return m.group(0)


def _sonde(*args):
    if not shutil.which('ffprobe'):
        pytest.skip('ffprobe absent')
    return json.loads(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-of', 'json'] + list(args) + [VIDEO]))


def _atomes_racine(chemin):
    noms, d = [], io.open(chemin, 'rb').read()
    i = 0
    while i + 8 <= len(d):
        taille, nom = struct.unpack('>I4s', d[i:i + 8])
        noms.append(nom.decode('latin-1'))
        if taille == 1:
            taille = struct.unpack('>Q', d[i + 8:i + 16])[0]
        if taille < 8:
            break
        i += taille
    return noms


def _dimensions_jpeg(chemin):
    d = io.open(chemin, 'rb').read()
    assert d[:2] == b'\xff\xd8', 'pas un JPEG'
    i = 2
    while i < len(d):
        assert d[i] == 0xFF
        marque, longueur = d[i + 1], struct.unpack('>H', d[i + 2:i + 4])[0]
        if marque in (0xC0, 0xC1, 0xC2):
            h, l = struct.unpack('>HH', d[i + 5:i + 9])
            return l, h
        i += 2 + longueur
    raise AssertionError('dimensions introuvables')


# ── LA VIDÉO ─────────────────────────────────────────────────────────────

def test_la_video_publiee_est_CELLE_de_la_source():
    """Une source modifiée sans que la vidéo soit refaite publierait un
    bandeau qui ne dit plus ce que dit le dépôt."""
    durees = [float(x) for x in re.search(
        r'var DUREES = \[([^\]]+)\]', SOURCE).group(1).split(',')]
    assert len(durees) == SOURCE.count('class="scene'), (
        'une scène sans durée, ou une durée sans scène')
    flux = _sonde('-count_frames', '-select_streams', 'v:0', '-show_entries',
                  'stream=r_frame_rate,nb_read_frames')['streams'][0]
    assert flux['r_frame_rate'] == '30/1'
    assert int(flux['nb_read_frames']) == round(sum(durees) * 30), (
        'la vidéo ne suit plus la chronologie de sa source : relancer '
        'node outils/bandeau_offshore_ot/engendrer.js')


def test_la_video_est_un_BANDEAU_LINKEDIN_lisible_par_tout_navigateur():
    flux = _sonde('-show_entries',
                  'stream=codec_type,codec_name,width,height,pix_fmt')['streams']
    assert len(flux) == 1, 'une piste en trop (le son ?)'
    v = flux[0]
    assert (v['width'], v['height']) == (1584, 396), 'format LinkedIn 1584 × 396'
    assert v['codec_name'] == 'h264' and v['pix_fmt'] == 'yuv420p'
    atomes = _atomes_racine(VIDEO)
    assert atomes.index('moov') < atomes.index('mdat'), (
        "l'index est en queue : la lecture attendrait le fichier entier")


def test_l_affiche_et_la_video_restent_LEGERES():
    assert _dimensions_jpeg(AFFICHE) == (1584, 396)
    assert os.path.getsize(AFFICHE) < 300 * 1024
    assert os.path.getsize(VIDEO) < 2.5 * 1024 * 1024


def test_la_source_met_la_CYBERSECURITE_OT_en_tete():
    """La première scène et la pastille, présentes de bout en bout, portent
    l'OT ; la cinquième question — la seule sur l'OT — est celle qui ressort."""
    premiere = re.search(r'data-scene="0".*?</section>', SOURCE, re.S).group(0)
    assert 'OT cybersecurity' in premiere and 'IEC 62443' in premiere
    assert re.search(r'class="pastille">[^<]*OT SECURITY<', SOURCE)
    assert re.search(r'class="carte q5[^"]*"[^>]*><span class="num">5</span>'
                     r'<div><div class="c">Industrial', SOURCE)


# ── LA PAGE ──────────────────────────────────────────────────────────────

def test_le_bandeau_est_AU_DESSUS_du_titre_dans_le_heros():
    section = PAGE.index('data-fond-hero')
    bandeau = PAGE.index('<figure class="bandeau-ot"')
    titre = PAGE.index('<h1>Concevoir et sécuriser vos installations industrielles')
    assert section < bandeau < titre


def test_le_bandeau_ENTIER_mene_au_profil_LinkedIn_dans_un_nouvel_onglet():
    fig = _figure()
    lien = re.search(r'<a class="bandeau-ot-lien"([^>]*)>(.*?)</a>', fig, re.S)
    assert lien, 'le bandeau a perdu son lien'
    attrs, dedans = lien.groups()
    assert 'href="%s"' % PROFIL in attrs
    assert 'target="_blank"' in attrs
    assert re.search(r'rel="[^"]*\bnoopener\b', attrs), (
        "sans noopener, l'onglet LinkedIn pourrait piloter cette page")
    assert 'class="bandeau-ot-media"' in dedans, "l'affiche n'est plus cliquable"
    assert '<button' not in dedans, 'un bouton dans un lien : la pause ouvrirait LinkedIn'
    assert fig.index('</a>') < fig.index('<button'), 'la pause doit suivre le lien'


def test_le_lien_se_NOMME_pour_qui_ne_voit_pas_l_image():
    fig = _figure()
    nom = re.search(r'<span class="sr-only">([^<]*)</span>\s*</a>', fig)
    assert nom and 'LinkedIn' in nom.group(1) and 'nouvel onglet' in nom.group(1)
    desc = re.search(r'aria-describedby="([^"]+)"', fig).group(1)
    assert 'id="%s"' % desc in fig, 'la description annoncée n’existe pas'


def test_l_affiche_RESERVE_sa_place():
    """Sans hauteur réservée, le titre saute vers le bas à l'arrivée de
    l'image : c'est le décalage que mesure le CLS."""
    img = re.search(r'<img class="bandeau-ot-media"[^>]*>', _figure()).group(0)
    assert 'width="1584"' in img and 'height="396"' in img
    assert re.search(r'\.bandeau-ot-media,\.bandeau-ot-video\{[^}]*aspect-ratio:4/1', CSS)


def test_les_fichiers_du_bandeau_sont_SERVIS():
    nom = re.search(r'data-video="([\w.-]+)"', _figure()).group(1)
    assert os.path.isfile(os.path.join(ICI, 'media', nom))
    assert '<script src="/bandeau-ot.js" defer></script>' in PAGE
    r = _get('/bandeau-ot.js')
    assert r.status_code == 200 and 'javascript' in r.headers['Content-Type']
    r = _get('/media/' + nom, Range='bytes=0-99')
    assert r.status_code == 206, 'sans tranches, Safari refuse de lire'
    assert _get('/media/bandeau-offshore-ot.jpg').status_code == 200


# ── LE SCRIPT ────────────────────────────────────────────────────────────

def test_la_video_n_arrive_qu_APRES_la_page():
    assert '<video' not in PAGE.lower()
    assert re.search(r'addEventListener\("load", demarrer', JS)


def test_la_video_inseree_est_muette_en_boucle_et_en_ligne():
    for attendu in ('v.muted = true;', 'v.setAttribute("muted", "");',
                    'v.setAttribute("playsinline", "");', 'v.loop = true;'):
        assert attendu in JS, attendu


def test_il_cede_au_MOUVEMENT_REDUIT_et_a_la_PAUSE_demandee():
    assert 'prefers-reduced-motion: reduce' in JS
    assert re.search(r'<button type="button" class="bandeau-ot-btn"[^>]*\shidden>', PAGE), (
        'le bouton de pause doit rester caché tant que la vidéo ne tourne pas')
    assert 'if (!v || !voulue) return;' in JS, (
        "revenir à l'écran relancerait une animation que le visiteur a arrêtée")
