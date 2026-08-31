# -*- coding: utf-8 -*-
"""La page qui vend l'accès : elle doit être trouvable, et ne jamais mentir.

CE QUI ÉTAIT EN CAUSE. La mécanique de paiement fonctionnait, et personne ne
pouvait la trouver : aucune page de tarif, aucun bouton, rien dans le menu, et
le montant n'existait que dans l'objet `price_…` de Stripe. Le seul chemin vers
la caisse passait par /connexion — donc supposait un compte déjà confirmé, ce
qu'un acheteur n'a pas. Pendant ce temps l'accueil ne décrivait qu'une voie :
« l'accès est validé par notre équipe ».

LES DEUX RÈGLES QUI TIENNENT TOUT :

  · LE PRIX VIENT DE STRIPE, JAMAIS DE LA PAGE. Un montant recopié dérive le
    jour où il change dans Stripe, et le client découvre le désaccord la carte
    à la main. Illisible, il ne s'affiche pas : un prix qu'on ne peut pas
    prouver n'est pas un prix.
  · LE PÉRIMÈTRE VIENT DU MENU, JAMAIS DE LA PAGE. Une liste écrite à la main
    décrit un site qui n'existe plus dès qu'une page change de rubrique.
"""
import io
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import acces                                                       # noqa: E402
import paiement                                                    # noqa: E402
import perimetre                                                   # noqa: E402

PAGE = "acces.html"


def _src(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


class _FauxPrix(dict):
    pass


def _faux_stripe(monkeypatch, prix=None, leve=False, compteur=None):
    class _Price:
        @staticmethod
        def retrieve(_id):
            if compteur is not None:
                compteur.append(_id)
            if leve:
                raise RuntimeError("stripe injoignable")
            return prix
    monkeypatch.setattr(paiement, "_stripe", lambda: type("S", (), {"Price": _Price}))
    monkeypatch.setattr(paiement, "_TARIF", {"valeur": None, "lu_a": 0.0})


@pytest.fixture
def configure(monkeypatch):
    for nom in (paiement.CLE, paiement.CLE_WEBHOOK, paiement.CLE_PRIX):
        monkeypatch.setenv(nom, "essai")
    monkeypatch.setattr(paiement, "_TARIF", {"valeur": None, "lu_a": 0.0})


# ── 1. Une page de vente derrière une connexion ne vend rien ──────────────

def test_la_page_est_ouverte_a_un_visiteur_anonyme(anonyme):
    r = anonyme.get("/acces")
    assert r.status_code == 200
    assert "Obtenir un" in r.get_data(as_text=True)


def test_la_page_est_declaree_ouverte_et_figure_dans_le_plan_du_site(anonyme):
    assert acces.ouvert("/acces")
    plan = anonyme.get("/sitemap.xml").get_data(as_text=True)
    assert "/acces<" in plan, "invendable : introuvable par les moteurs"


def test_le_menu_et_la_recherche_y_mènent():
    """Une page hors du tiroir n'existe pas pour le visiteur qui cherche."""
    nav = _src("nav.js")
    assert '["/acces", "Obtenir un accès"]' in nav
    assert '["/acces", "Obtenir un accès",' in nav   # l'index de recherche


# ── 2. Le prix vient de Stripe, et se tait quand il ne peut pas se prouver ─

def test_le_tarif_est_lu_chez_stripe_et_formate(configure, monkeypatch):
    _faux_stripe(monkeypatch, prix={"unit_amount": 49000, "currency": "eur"})
    t = paiement.tarif()
    assert t["montant"] == 49000 and t["devise"] == "eur"
    assert t["affichage"].startswith("490,00")
    assert t["recurrent"] is False


def test_un_tarif_illisible_ne_rend_aucun_montant(configure, monkeypatch):
    """UN PRIX QU'ON NE PEUT PAS PROUVER N'EST PAS UN PRIX. Rendre un montant
    de repli, ou zéro, ferait annoncer à la page ce que la caisse
    contredirait."""
    _faux_stripe(monkeypatch, leve=True)
    assert paiement.tarif() is None


def test_sans_configuration_il_n_y_a_pas_de_tarif(monkeypatch):
    for nom in (paiement.CLE, paiement.CLE_WEBHOOK, paiement.CLE_PRIX):
        monkeypatch.delenv(nom, raising=False)
    assert paiement.tarif() is None


def test_un_prix_sans_montant_unitaire_ne_s_affiche_pas(configure, monkeypatch):
    """Un prix « à la carte » n'a pas de montant : annoncer 0 serait faux."""
    _faux_stripe(monkeypatch, prix={"unit_amount": None, "currency": "eur"})
    assert paiement.tarif() is None


def test_le_tarif_n_interroge_stripe_qu_une_fois(configure, monkeypatch):
    """Un aller-retour Stripe par affichage de page se paierait en latence chez
    le visiteur."""
    appels = []
    _faux_stripe(monkeypatch, prix={"unit_amount": 1000, "currency": "eur"},
                 compteur=appels)
    paiement.tarif()
    paiement.tarif()
    paiement.tarif()
    assert len(appels) == 1, appels


def test_un_prix_recurrent_est_signale_comme_inoperant(admin, configure, monkeypatch):
    """LE PIRE DES CAS : tout paraît en ordre. Les trois variables sont là, le
    panneau est muet, la page affiche son bouton — et la caisse, ouverte en
    `mode="payment"`, échoue à chaque tentative sur un prix d'abonnement."""
    _faux_stripe(monkeypatch, prix={"unit_amount": 1000, "currency": "eur",
                                    "recurring": {"interval": "month"}})
    j = admin.get("/api/admin/reglages").get_json()
    lignes = [e for e in j["ecartes"] if e["variable"] == paiement.CLE_PRIX]
    assert lignes, "un prix récurrent passe inaperçu"
    assert "RÉCURRENT" in lignes[0]["consequence"]


def test_la_page_ne_contient_aucun_montant_en_dur():
    """La règle qui empêche la dérive de revenir : un chiffre suivi d'un
    symbole monétaire dans le HTML est un prix recopié."""
    page = _src(PAGE)
    fautes = re.findall(r"\d[\d   .,]*\s*(?:€|EUR\b|\$|£)", page)
    assert not fautes, "montant écrit en dur dans la page : %s" % fautes[:3]


def test_la_page_ne_contient_aucun_compte_de_pages_en_dur():
    """LA MÊME DÉRIVE QUE LE PRIX, ET ELLE A EU LIEU. Le chapeau annonçait
    « dix pages restent ouvertes à tous » ; il est devenu faux le jour même, en
    ouvrant la page qui le portait. Les nombres viennent du serveur."""
    page = _src(PAGE)
    corps = page[page.index("<main"):page.index("</main>")]
    # LES COMMENTAIRES NE SONT PAS LUS PAR LE VISITEUR. Celui qui explique ce
    # défaut cite la phrase fautive : le compter serait tester le texte de la
    # règle, pas la page.
    corps = re.sub(r"<!--.*?-->", "", corps, flags=re.S)
    fautes = re.findall(
        r"\b(?:[Uu]ne?|[Dd]eux|[Tt]rois|[Qq]uatre|[Cc]inq|[Ss]ix|[Ss]ept|"
        r"[Hh]uit|[Nn]euf|[Dd]ix|[Oo]nze|[Dd]ouze|[Tt]rente|[Qq]uarante|\d+)"
        r"\s+(?:autres?\s+)?pages?\b", corps)
    assert not fautes, "compte de pages écrit en dur : %s" % fautes[:3]


def test_l_etat_du_paiement_sert_le_tarif(anonyme, configure, monkeypatch):
    _faux_stripe(monkeypatch, prix={"unit_amount": 25000, "currency": "eur"})
    j = anonyme.get("/api/paiement/etat").get_json()
    assert j["configure"] is True
    assert j["tarif"]["affichage"].startswith("250,00")


# ── 3. Le périmètre vient du menu ─────────────────────────────────────────

def test_le_perimetre_dit_le_meme_ouvert_ferme_que_la_politique():
    """Dans les deux sens, sur TOUTES les entrées : un périmètre qui
    divergerait de la politique vendrait ce qui est déjà gratuit, ou
    tairait ce qu'on achète."""
    e = perimetre.etat()
    assert e["lisible"] and e["n_client"] >= 30
    for rub in e["rubriques"]:
        for p in rub["pages"]:
            assert p["ouverte"] == acces.ouvert(p["chemin"]), p["chemin"]


def test_le_perimetre_ne_promet_que_des_pages_reellement_servies():
    import app as A
    connues = set(A.PAGES)
    inconnues = [p["chemin"] for r in perimetre.etat()["rubriques"]
                 for p in r["pages"] if p["chemin"] not in connues]
    assert not inconnues, inconnues


def test_un_menu_illisible_ne_rend_pas_une_liste_vide_mais_rien():
    """Servir « votre accès ouvre 0 page » serait pire que se taire :
    l'appelant sait distinguer une absence d'une liste vide."""
    assert perimetre.rubriques(source="ceci n'est pas un menu") == []


def test_la_page_ne_recopie_pas_le_perimetre():
    """Une liste écrite à la main décrit un site qui n'existe plus dès qu'une
    page change de rubrique.

    ON NE REGARDE QUE LE CORPS. Le pied de page — partagé avec les quarante
    autres pages du site — porte légitimement les colonnes « Expertise »,
    « Ressources », « Entreprise ». Une règle qui les compterait comme une
    copie du périmètre tomberait sur le mauvais coupable, et l'on finirait par
    la désarmer."""
    page = _src(PAGE)
    corps = page[page.index("<main"):page.index("</main>")]
    for rub in perimetre.etat()["rubriques"]:
        assert rub["rubrique"] not in corps, rub["rubrique"]
    assert "/api/acces/perimetre" in page


def test_la_route_du_perimetre_est_ouverte_et_distincte_de_la_route_chaude(anonyme):
    """Elle est à part de /api/acces, que nav.js appelle à CHAQUE page : y
    verser les libellés ferait payer à quarante pages le détail dont une
    seule a besoin."""
    j = anonyme.get("/api/acces/perimetre").get_json()
    assert j["ok"] and j["lisible"]
    chaude = anonyme.get("/api/acces").get_json()
    assert "rubriques" not in chaude


# ── 4. La page ne montre que ce qui existe ────────────────────────────────

def _script(source):
    return "\n".join(re.findall(
        r"<script(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>", source, re.S))


def test_la_voie_payante_est_masquee_et_revelee_par_le_serveur():
    page = _src(PAGE)
    assert 'id="acVoiePayante" hidden' in page
    assert 'id="acRegler" hidden' in page
    js = _script(page)
    assert re.search(r"if\(!j \|\| !j\.configure\) return;", js), (
        "la voie payante n'est plus conditionnée à l'état du serveur")


def test_la_voie_gratuite_est_toujours_offerte():
    """Elle ne dépend d'aucune configuration : c'est la voie du site, et la
    seule quand le paiement est éteint."""
    page = _src(PAGE)
    bloc = page[page.index("Validation par notre équipe") - 400:
                page.index("Validation par notre équipe") + 400]
    assert "hidden" not in bloc
    assert 'href="/inscription"' in bloc


def test_la_page_ne_decide_pas_elle_meme_qui_peut_payer():
    """Aucune règle d'éligibilité ne descend dans la page : le serveur refuse,
    avec un message identique pour « inconnue », « non confirmée » et « déjà
    ouverte » — sans quoi cette page dirait qui a un compte chez nous."""
    js = _script(_src(PAGE))
    assert "/api/paiement/checkout" in js
    for mot in ("email_verified", "approved", "confirmée ?", "existe"):
        assert mot not in js


def test_l_accueil_renvoie_vers_la_page_sans_promettre_le_paiement():
    """L'accueil est statique : il ne peut pas savoir si le paiement est
    allumé. Il renvoie donc vers la page qui, elle, interroge le serveur."""
    accueil = _src("index.html")
    assert 'href="/acces"' in accueil
    for mot in ("Stripe", "carte bancaire", "réglant en ligne"):
        assert mot not in accueil


def test_la_page_n_execute_rien_en_ligne_hors_empreinte():
    import csp
    octets = io.open(os.path.join(ICI, PAGE), "rb").read()
    script_src = re.search(r"script-src[^;]*", csp.pour(octets)).group(0)
    assert "unsafe-inline" not in script_src
    assert not re.search(rb"\son[a-z]+\s*=", octets)
