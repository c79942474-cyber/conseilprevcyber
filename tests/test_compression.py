"""LA COMPRESSION DES RÉPONSES — et un piège qui n'avait ici aucune victime.

CE SITE N'AVAIT PAS LE DÉFAUT, ET C'EST PRÉCISÉMENT CE QUI LE RENDAIT
DANGEREUX. `_compress_text` écartait toute réponse `direct_passthrough` ou
`is_streamed`. Or une réponse de `send_from_directory` a pour corps un
`FileWrapper`, objet sans longueur, que Werkzeug déclare `is_streamed` : le
crochet ne pouvait donc comprimer AUCUN fichier servi ainsi.

Ici la conséquence était nulle, parce que `_serve_fast` gzippe les assets
lui-même, en mémoire, au niveau 9, avec un ETag fort et une URL versionnée —
`send_from_directory` n'est plus qu'un repli pour fichier illisible. Sur les
deux sites voisins, où le même code servait bel et bien les fichiers par
`send_from_directory`, le même écartement valait 2,3 Mo par première visite,
et rien ne le signalait.

CE QUE CES CONTRÔLES GARDENT DONC :

  1. Le crochet comprime les réponses TEXTE calculées (les API JSON).
  2. Il comprime aussi un fichier servi en passe-plat — le cas qu'il ne
     voyait pas.
  3. Il ne rassemble JAMAIS un vrai flux en mémoire ; les deux cas que
     `is_streamed` confond sont éprouvés séparément.
  4. Il ne touche ni aux réponses déjà encodées par `_serve_fast`, ni aux
     binaires, ni au 304 d'une revisite.

ET ILS MESURENT LE CORPS, PAS L'EN-TÊTE : une réponse annoncée gzip est
décompressée et comparée à l'original. Un en-tête peut mentir.
"""
import gzip
import json
import os
import sys

import pytest
from flask import Response

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import app as A  # noqa: E402


# TROIS ROUTES DE RECETTE, POSÉES AVANT LA PREMIÈRE REQUÊTE — Flask refuse de
# les enregistrer après coup. Elles éprouvent trois cas que les routes du site
# n'offrent pas ensemble : un fichier servi en PASSE-PLAT (le cas aveugle), un
# vrai flux, et une réponse trop courte pour valoir une compression. Elles
# passent par le crochet réel, pas par une imitation.
@A.app.route("/_recette_compression_fichier")
def _recette_compression_fichier():
    return A.send_from_directory(ICI, "parcours.js",
                                 mimetype="text/javascript; charset=utf-8")


@A.app.route("/_recette_compression_flux")
def _recette_compression_flux():
    def gen():
        for _ in range(400):
            yield "du texte assez long pour dépasser le seuil, " * 3
    return Response(gen(), mimetype="text/plain")


@A.app.route("/_recette_compression_court")
def _recette_compression_court():
    return Response("court" * 20, mimetype="text/plain")


@A.app.route("/_recette_compression_json")
def _recette_compression_json():
    """Une réponse JSON CALCULÉE, au-dessus du seuil.

    Elle existe parce que `/health` fait 756 octets — moins que le seuil de
    compression — et qu'aucune autre API publique ne dépasse celui-ci sans
    authentification. Mesurer ce chemin sur un endpoint trop court aurait
    donné un contrôle qui saute : il aurait déclaré l'axe non mesuré au lieu
    de le mesurer."""
    return Response(json.dumps({"lignes": [{"n": i, "texte": "veille industrielle"}
                                           for i in range(200)]}),
                    mimetype="application/json")


NAV = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}


def _get(chemin, gzip_accepte=True, **entetes):
    h = dict(NAV)
    h["Accept-Encoding"] = "gzip, deflate" if gzip_accepte else "identity"
    h.update(entetes)
    return A.app.test_client().get(chemin, headers=h)


# ── LE CAS AVEUGLE : UN FICHIER SERVI EN PASSE-PLAT ───────────────────────

def test_un_fichier_servi_en_passe_plat_est_compresse():
    """LE CONTRÔLE QUI REND LE PIÈGE IMPOSSIBLE À REVENIR. C'est exactement la
    forme de réponse que l'ancienne garde écartait."""
    r = _get("/_recette_compression_fichier")
    assert r.status_code == 200
    assert r.headers.get("Content-Encoding") == "gzip", (
        "un fichier en passe-plat repart en clair : le crochet ne le voit pas")
    attendu = open(os.path.join(ICI, "parcours.js"), "rb").read()
    assert gzip.decompress(r.data) == attendu


def test_la_longueur_annoncee_est_celle_du_corps_compresse():
    """Une longueur restée sur la taille d'origine ferait attendre le client
    indéfiniment."""
    r = _get("/_recette_compression_fichier")
    assert int(r.headers["Content-Length"]) == len(r.data)


def test_vary_previent_les_caches_intermediaires():
    r = _get("/_recette_compression_fichier")
    assert "accept-encoding" in (r.headers.get("Vary") or "").lower()


def test_un_client_qui_ne_sait_pas_lire_gzip_recoit_le_fichier_en_clair():
    r = _get("/_recette_compression_fichier", gzip_accepte=False)
    assert not r.headers.get("Content-Encoding")
    assert r.data == open(os.path.join(ICI, "parcours.js"), "rb").read()


# ── CE QUE LE CROCHET DOIT LAISSER TRANQUILLE ─────────────────────────────

def test_un_vrai_flux_nest_pas_rassemble_en_memoire():
    """`is_streamed` recouvre deux choses. Le crochet doit comprimer la
    première (un fichier borné) et laisser passer la seconde (un générateur) :
    le lire jusqu'au bout annulerait sa raison d'être."""
    r = _get("/_recette_compression_flux")
    assert r.status_code == 200
    assert len(r.data) > A._GZIP_MIN, (
        "le flux de recette est trop court : il serait écarté par le seuil, "
        "et ce contrôle ne mesurerait plus rien")
    assert not r.headers.get("Content-Encoding")


def test_une_reponse_trop_courte_nest_pas_compressee():
    r = _get("/_recette_compression_court")
    assert r.status_code == 200
    assert not r.headers.get("Content-Encoding")


# ── CE QUE `_serve_fast` FAIT DÉJÀ, ET QU'IL NE FAUT PAS DÉFAIRE ──────────

class _EspionGzip:
    """Le module `gzip`, à ceci près qu'il compte ses compressions.

    COMPTER LES APPELS, PAS L'EN-TÊTE. Le crochet garde une sécurité de
    dernier ressort : si la version compressée est plus grosse que l'original,
    elle est jetée. Une réponse DÉJÀ gzippée par `_serve_fast` recomprimée par
    erreur grossit donc, se fait jeter, et arrive intacte — en-tête correct,
    contrôle vert, et 9 ms de processeur brûlées à chaque page. La mutation
    qui retire la garde `Content-Encoding` a effectivement survécu à un
    contrôle qui ne regardait que le résultat."""

    def __init__(self, compteur):
        self._c = compteur

    def __getattr__(self, nom):
        return getattr(gzip, nom)

    def compress(self, data, *a, **kw):
        self._c["n"] += 1
        return gzip.compress(data, *a, **kw)


@pytest.fixture
def compressions(monkeypatch):
    c = {"n": 0}
    monkeypatch.setattr(A, "gzip", _EspionGzip(c))
    return c


def test_les_pages_gardent_leur_compression_maison(compressions):
    """`_serve_fast` gzippe au niveau 9, en mémoire, une fois pour toutes. Le
    crochet voit une réponse déjà encodée et doit passer son chemin — la
    recomprimer produirait un double encodage, ou, plus insidieusement, le
    travail complet d'une compression jetée."""
    # LA PREMIÈRE VISITE REMPLIT LE CACHE DE `_serve_fast`, ce qui compresse
    # légitimement une fois. Ce n'est pas ce qu'on mesure, et compter à partir
    # de là rendrait le contrôle dépendant de l'ordre des tests.
    _get("/")
    compressions["n"] = 0
    r = _get("/")
    assert r.status_code == 200
    assert r.headers.get("Content-Encoding") == "gzip"
    clair = gzip.decompress(r.data)
    assert clair[:200].lower().count(b"<!doctype") == 1, (
        "la page a été encodée deux fois")
    assert compressions["n"] == 0, (
        "une page déjà compressée par _serve_fast est repassée au compresseur")


def test_les_assets_gardent_leur_url_immuable_et_leur_compression():
    """Les assets portent « ?v=<empreinte> » et un an de cache. Comprimer ne
    doit toucher ni l'un ni l'autre."""
    page = gzip.decompress(_get("/").data).decode("utf-8")
    import re
    ref = re.search(r'src="(/nav\.js\?v=[a-f0-9]+)"', page)
    assert ref, "la page ne référence plus /nav.js avec une empreinte"
    r = _get(ref.group(1))
    assert r.status_code == 200
    assert r.headers.get("Content-Encoding") == "gzip"
    assert "immutable" in (r.headers.get("Cache-Control") or "")
    assert gzip.decompress(r.data) == open(os.path.join(ICI, "nav.js"), "rb").read()


def test_la_revisite_dune_page_recoit_un_304_sans_corps():
    """Le 304 de `_serve_fast`, qui pose son propre ETag fort."""
    r1 = _get("/")
    etag = r1.headers.get("ETag")
    assert etag, "la page d'accueil est servie sans ETag"
    r2 = _get("/", **{"If-None-Match": etag})
    assert r2.status_code == 304
    assert r2.data == b""


def test_la_revisite_dun_fichier_comprime_recoit_un_304_sans_corps():
    """LE 304 DU CHEMIN QUE LE CROCHET TOUCHE VRAIMENT. La page d'accueil ne
    l'éprouve pas : `_serve_fast` l'ayant déjà encodée, le crochet passe son
    chemin avant même de voir l'étiquette. Seul un fichier servi en passe-plat
    traverse la compression ET porte un ETag — c'est là qu'un suffixe ajouté
    à l'étiquette ferait tomber le 304, c'est-à-dire le gain le plus important
    des deux."""
    r1 = _get("/_recette_compression_fichier")
    etag = r1.headers.get("ETag")
    assert etag, "le fichier est servi sans ETag : chaque revisite retélécharge"
    assert r1.headers.get("Content-Encoding") == "gzip"
    r2 = _get("/_recette_compression_fichier", **{"If-None-Match": etag})
    assert r2.status_code == 304
    assert r2.data == b""


# ── LES RÉPONSES CALCULÉES ────────────────────────────────────────────────

def test_une_reponse_dapi_calculee_arrive_compressee():
    """Les API JSON ne viennent d'aucun fichier : elles empruntent l'autre
    chemin du crochet, celui qui existait déjà et fonctionnait."""
    r = _get("/_recette_compression_json")
    assert r.status_code == 200
    assert r.headers.get("Content-Encoding") == "gzip"
    clair = gzip.decompress(r.data)
    assert len(clair) > len(r.data) * 2, "le JSON gagne moins de moitié"
    assert len(json.loads(clair)["lignes"]) == 200


def test_le_bilan_de_sante_reste_lisible():
    """`/health` est plus court que le seuil : il part donc en clair, et c'est
    le comportement voulu — sous un paquet réseau, l'en-tête gzip coûte plus
    qu'il ne rend. Ce qui compte est qu'il reste du JSON valide."""
    r = _get("/health")
    if r.status_code != 200:
        pytest.skip("/health indisponible (%s)" % r.status_code)
    corps = (gzip.decompress(r.data) if r.headers.get("Content-Encoding") == "gzip"
             else r.data)
    assert isinstance(json.loads(corps), dict)


# ── LE CROCHET EST-IL SEULEMENT BRANCHÉ ? ─────────────────────────────────

def test_le_crochet_est_enregistre_sur_lapplication():
    """Un contrôle qui prouve que la règle fonctionne ne prouve pas qu'elle
    s'exécute. Celui-ci lit la liste des crochets de Flask."""
    noms = [f.__name__ for f in A.app.after_request_funcs.get(None, [])]
    assert "_compress_text" in noms
