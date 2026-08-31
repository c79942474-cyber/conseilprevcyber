# -*- coding: utf-8 -*-
"""Un refus n'est pas un cul-de-sac.

CE QUI EST ARRIVÉ. La recette de paiement s'est arrêtée sur « Accès réservé à
l'administrateur. » — un fragment HTML nu : pas de feuille de style, pas
d'en-tête, et surtout pas le tiroir de `nav.js` qui porte le bouton
« Déconnexion ». Ce n'était pourtant PAS le cas « personne n'est connecté »,
qui redirige proprement : c'était « quelqu'un est connecté, mais ce n'est pas
l'administrateur » — le navigateur portait encore la session du compte de test.

Et `/connexion` renvoie AILLEURS tout visiteur déjà connecté. Le visiteur était
donc enfermé : /admin sans issue, /connexion qui rebondit, aucun bouton de
déconnexion nulle part — et rien ne disait même quel compte il portait. Le cas
n'est pas propre à la recette : l'exploitant qui tient un compte de test sur son
propre site y tombe dès qu'il ouvre /admin sans avoir quitté ce compte.

CE QUE CES RÈGLES TIENNENT. Le refus reste un refus — 403, même politique
d'accès, aucun contenu de la page demandée — mais il porte de quoi en sortir :
qui est connecté, et le geste qui débloque.
"""
import io
import os
import re
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

PAGE = "acces-administrateur.html"


def _src(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


# ── 1. Le refus est une page, et il reste un refus ────────────────────────

def test_un_client_connecte_recoit_une_vraie_page_et_non_un_fragment(connecte):
    r = connecte.get("/admin")
    assert r.status_code == 403
    corps = r.get_data(as_text=True)
    # Une PAGE : document complet, feuille de style, et le geste qui débloque.
    assert corps.lstrip().lower().startswith("<!doctype html")
    assert "/styles.css" in corps
    assert "/api/auth/logout" in corps, "aucun moyen de quitter le compte en cours"
    assert "/api/auth/me" in corps, "la page ne dit pas de quel compte se déconnecter"


def test_le_refus_ne_laisse_rien_filtrer_de_la_page_demandee(connecte):
    """Une page d'erreur qui montrerait le contenu protégé serait la fuite
    elle-même. On éprouve sur une page d'administration RICHE."""
    corps = connecte.get("/admin/comptes").get_data(as_text=True)
    reelle = _src("admin-comptes.html")
    # Un repère du vrai contenu, choisi hors des parties communes à tout le site.
    assert "/api/admin/users" in reelle
    assert "/api/admin/users" not in corps


def test_le_refus_n_est_jamais_mis_en_cache(connecte):
    """Servi SOUS l'adresse demandée : mémorisé pour /admin, il se
    réafficherait après une connexion réussie en administrateur — le refus
    survivrait à sa propre cause."""
    r = connecte.get("/admin")
    assert "no-store" in (r.headers.get("Cache-Control") or "")


def test_l_anonyme_est_toujours_redirige_et_ne_voit_pas_cette_page(anonyme):
    """LES DEUX CAS RESTENT DISTINCTS. « Personne n'est connecté » se règle par
    la connexion, pas par une déconnexion : les confondre enverrait un visiteur
    sans session cliquer sur « se déconnecter »."""
    r = anonyme.get("/admin")
    assert r.status_code in (301, 302)
    assert "/connexion" in (r.headers.get("Location") or "")
    assert "next=/admin" in (r.headers.get("Location") or "")


def test_l_administrateur_recoit_toujours_sa_console(admin):
    r = admin.get("/admin")
    assert r.status_code == 200
    assert "acces-administrateur" not in r.get_data(as_text=True)


def test_la_route_api_rend_du_json_jamais_du_html(connecte):
    """Un appel de programme attend un objet, pas une page : lui servir du HTML
    ferait échouer l'analyse au lieu de dire « interdit »."""
    r = connecte.get("/api/admin/reglages")
    assert r.status_code == 403
    assert r.is_json
    assert "administrateur" in (r.get_json().get("error") or "")


# ── 2. La page ramène EXACTEMENT là où l'on allait ────────────────────────

def _script(source):
    m = re.search(r"<script(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>", source, re.S)
    assert m, "aucun script en ligne dans " + PAGE
    return m.group(1)


def test_la_page_compose_son_retour_depuis_le_chemin_reellement_demande():
    """LE REFUS EST RENDU EN PLACE, sans redirection : l'adresse de la barre EST
    celle qu'on voulait. Figer ce retour sur « /admin » perdrait la page
    réellement visée — /admin/clients, /admin/base-connaissance — et ferait
    recommencer la navigation après chaque changement de compte."""
    js = _script(_src(PAGE))
    m = re.search(r"var\s+cible\s*=\s*([^;]+);", js)
    assert m, "la page ne calcule plus sa cible"
    assert "location.pathname" in m.group(1), (
        "le retour ne suit plus le chemin demandé : " + m.group(1).strip())
    # Et cette cible est bien CELLE qui part dans next.
    assert re.search(r"'/connexion\?next='\s*\+\s*encodeURIComponent\(cible\)", js)


def test_la_deconnexion_est_un_post_et_non_un_lien():
    """La route est derrière la garde d'origine : un <a href> ne déconnecterait
    rien, et donnerait l'illusion du contraire."""
    js = _script(_src(PAGE))
    m = re.search(r"fetch\('/api/auth/logout'\s*,\s*\{([^}]*)\}", js)
    assert m, "la déconnexion ne passe plus par fetch"
    assert "method:'POST'" in m.group(1).replace(" ", "")


def test_la_page_n_execute_rien_en_ligne_hors_empreinte():
    """La CSP du site n'admet plus `unsafe-inline` : un attribut on*= poserait
    un bouton mort chez le visiteur, en silence."""
    import csp
    octets = io.open(os.path.join(ICI, PAGE), "rb").read()
    politique = csp.pour(octets)
    script_src = re.search(r"script-src[^;]*", politique).group(0)
    assert "unsafe-inline" not in script_src
    assert script_src.count("sha256-") == 1
    assert not re.search(rb"\son[a-z]+\s*=", octets), "attribut d'événement en ligne"
