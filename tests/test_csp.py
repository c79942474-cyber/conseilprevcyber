"""Retirer `'unsafe-inline'` de `script-src`, sans casser les pages.

CE QUE CELA CHANGE. Tant que `script-src` admettait l'exécution en ligne,
l'échappement était la SEULE défense : un oubli — il y en avait un sur les
liens de flux — devenait directement exploitable. Sans elle, le même oubli
devient inerte, le navigateur refusant d'exécuter ce qui n'est pas annoncé.

DES EMPREINTES, PAS DES JETONS. Un jeton change à chaque réponse et oblige à
réécrire le corps de la page : le cache mémoire et l'ETag fort tombent avec
lui. Les scripts d'ici sont statiques ; leurs empreintes se calculent une fois,
sur les octets mêmes que le navigateur recevra.

CE QUE CES RÈGLES DOIVENT ATTRAPER, PARCE QUE RIEN D'AUTRE NE LE FERA. Une
empreinte fausse ne produit AUCUNE erreur serveur : la page part avec 200, le
navigateur refuse le script, et l'écran est mort chez le visiteur. Il n'y a ni
trace, ni journal, ni alerte. C'est le seul endroit où le défaut se voit avant
le déploiement.
"""
import base64
import glob
import hashlib
import os
import re
import sys
from html.parser import HTMLParser

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import app as application                                          # noqa: E402
import csp                                                         # noqa: E402


class _Lecteur(HTMLParser):
    """Un VRAI analyseur HTML — pas l'expression régulière du module.

    Si les deux étaient d'accord par construction, la comparaison ne prouverait
    rien. Celui-ci lit comme un navigateur : c'est le seul juge qui compte.
    """

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.dans = False
        self.blocs = []
        self._courant = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and not dict(attrs).get("src"):
            self.dans, self._courant = True, []

    def handle_endtag(self, tag):
        if tag == "script" and self.dans:
            self.blocs.append("".join(self._courant))
            self.dans = False

    def handle_data(self, d):
        if self.dans:
            self._courant.append(d)


def _attendues(octets):
    p = _Lecteur()
    p.feed(octets.decode("utf-8", "replace"))
    return ["'sha256-%s'" % base64.b64encode(
        hashlib.sha256(b.encode("utf-8")).digest()).decode() for b in p.blocs]


PAGES = sorted(os.path.basename(f) for f in glob.glob(os.path.join(ICI, "*.html")))


# ── 1. Plus rien ne s'exécute en ligne sans être annoncé ──────────────────

def test_la_politique_globale_n_admet_plus_le_script_en_ligne():
    c = application._SECURITY_HEADERS["Content-Security-Policy"]
    assert "script-src 'self'" in c
    assert "script-src 'self' 'unsafe-inline'" not in c
    assert "'unsafe-eval'" not in c


def test_le_style_en_ligne_reste_admis_et_c_est_un_choix():
    """Un style ne s'exécute pas. Mille trente-quatre attributs `style=` pour
    un risque marginal serait un mauvais échange — et un échange perdu deux
    fois, puisqu'il retarderait celui qui compte."""
    assert "style-src 'self' 'unsafe-inline'" in csp.sans_script_en_ligne()


def test_aucun_attribut_de_gestionnaire_ne_subsiste():
    """`onclick`, `onsubmit`, `ontoggle` NE SONT COUVERTS PAR AUCUNE EMPREINTE
    — la spécification ne le permet pas. Ils sont bloqués net. Il y en avait
    seize, dont douze identiques dans une seule page."""
    fautes = []
    for nom in PAGES:
        src = open(os.path.join(ICI, nom), encoding="utf-8").read()
        for m in re.finditer(r"\son[a-z]+\s*=\s*\"", src):
            fautes.append("%s:%d" % (nom, src[:m.start()].count("\n") + 1))
    assert not fautes, "gestionnaires en ligne — pages mortes : " + ", ".join(fautes[:6])


# ── 2. L'empreinte doit être celle qu'un navigateur calculera ─────────────

@pytest.mark.parametrize("nom", PAGES)
def test_chaque_page_porte_l_empreinte_de_chacun_de_ses_scripts(nom):
    """LA RÈGLE QUI REMPLACE L'ABSENCE D'ERREUR SERVEUR.

    On compare la politique du module au verdict d'un analyseur HTML
    indépendant. Une empreinte manquante ne se verrait nulle part ailleurs :
    la page part avec 200 et meurt chez le visiteur.
    """
    with application.app.test_request_context("/"):
        ent = application._static_entry(nom)
    politique = ent["csp"] or ""
    for h in _attendues(ent["raw"]):
        assert h in politique, "%s : script non annoncé" % nom


def test_un_script_modifie_d_un_octet_change_l_empreinte():
    """LA RÈGLE QUI INTERDIT DE FIGER UNE VALEUR À LA MAIN. Une empreinte
    saisie devient fausse au premier changement, et la page cesse de
    fonctionner en silence."""
    a = csp.pour(b"<html><script>var x=1;</script></html>")
    b = csp.pour(b"<html><script>var x=2;</script></html>")
    assert a != b
    assert a.count("sha256-") == b.count("sha256-") == 1


def test_l_empreinte_porte_sur_les_octets_exacts():
    """Ni espaces retirés, ni fin de ligne normalisée : le navigateur empreinte
    ce qu'il lit entre les balises, à l'octet près."""
    assert csp.pour(b"<script>a</script>") != csp.pour(b"<script> a</script>")


def test_un_script_externe_n_a_pas_d_empreinte():
    """Il est déjà couvert par `'self'` ; lui en calculer une n'aurait aucun
    sens, et masquerait qu'il vient d'ailleurs."""
    assert csp.pour(b'<script src="/nav.js"></script>').count("sha256-") == 0


def test_une_reponse_sans_script_ne_recoit_aucune_empreinte():
    assert csp.sans_script_en_ligne().count("sha256-") == 0


# ── 3. Le cache ne peut pas être en retard sur le contenu ─────────────────

def test_le_cache_est_indexe_sur_le_contenu_et_non_sur_l_horodatage():
    """UNE CLÉ `(date, taille)` NE VOIT PAS deux écritures dans la même seconde
    à taille égale. Sur un fichier compilé, ce piège coûte un essai faussement
    vert ; ici il coûterait une page morte en production, sans erreur serveur
    et sans trace. Deux contenus de MÊME TAILLE doivent donner deux politiques.
    """
    a = csp.pour(b"<script>var x=1;</script>")
    b = csp.pour(b"<script>var x=2;</script>")
    assert a != b


# ── 4. Les pages qui ne passent pas par le chemin rapide ─────────────────

@pytest.mark.parametrize("chemin", ["/connexion", "/inscription",
                                    "/mot-de-passe-oublie"])
def test_les_pages_d_authentification_recoivent_leur_politique(anonyme, chemin):
    """Elles sont servies par `auth.py`, hors du chemin rapide. Sans passage
    dédié, elles recevraient la politique globale — et la page de connexion
    tomberait le jour du déploiement, sans erreur serveur."""
    r = anonyme.get(chemin)
    assert r.status_code == 200
    politique = r.headers.get("Content-Security-Policy", "")
    for h in _attendues(r.get_data()):
        assert h in politique, "%s : script non annoncé" % chemin


def test_une_page_du_chemin_rapide_porte_sa_propre_politique(anonyme):
    r = anonyme.get("/veille")
    politique = r.headers.get("Content-Security-Policy", "")
    assert politique.count("sha256-") >= 1
    assert politique != application._SECURITY_HEADERS["Content-Security-Policy"]


def test_l_empreinte_porte_sur_les_octets_TRANSFORMES(monkeypatch):
    """UN PIÈGE LATENT, MIS AU JOUR PAR UNE MUTATION QUI SURVIVAIT.

    `_versionner_html` réécrit `"/nav.js"` en `"/nav.js?v=…"` par un
    `replace` sur TOUT le document — pas seulement dans les balises. Un script
    intégré qui contiendrait ce littéral serait donc modifié avant d'être
    servi. Aujourd'hui aucun ne le contient, si bien qu'empreindre le fichier
    d'origine donnerait le même résultat : la mutation était sans effet, et la
    règle ne prouvait rien.

    Elle le prouve maintenant. Le jour où un script portera ce littéral,
    empreindre la mauvaise version rendrait la page morte chez le visiteur,
    avec un 200 et aucune trace.
    """
    asset = sorted(application._ASSETS_VERSIONNES)[0]
    origine = ('<html><script>var s="/%s";</script></html>' % asset).encode()
    with application.app.test_request_context("/"):
        transforme = application._versionner_html(origine)
    assert transforme != origine, "le transformateur doit toucher ce document"
    assert csp.pour(transforme) != csp.pour(origine)
    # Et c'est bien la version TRANSFORMÉE qui doit être annoncée : c'est elle
    # que le navigateur reçoit.
    for h in _attendues(transforme):
        assert h in csp.pour(transforme)
