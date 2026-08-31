# -*- coding: utf-8 -*-
"""Les conditions de vente : atteignables avant l'achat, et vraies.

CE QUI ÉTAIT EN CAUSE. /acces vend une ouverture de compte depuis trois
commits, et le dépôt n'avait ni conditions de vente, ni mention de TVA, ni
droit de rétractation réglé. Sentinel en a, longues et détaillées — et
inutilisables ici : elles décrivent des abonnements mensuels, du prélèvement
SEPA, du prorata et de la résiliation, quand cyber vend UN paiement, UNE fois,
sans échéance. Les recopier aurait été la faute corrigée trois fois cette
semaine : un document qui décrit autre chose que la réalité.

LES DEUX RÈGLES QUI TIENNENT TOUT :

  · DES CONDITIONS INACCESSIBLES AVANT L'ACHAT NE SONT PAS OPPOSABLES. La page
    est ouverte, indexée, et liée depuis le bloc de règlement lui-même — par un
    lien STATIQUE, qui ne dépend d'aucun script.
  · UNE RENONCIATION ÉCRITE MAIS NON RECUEILLIE NE VAUT RIEN. L'accès s'ouvrant
    dès le paiement, le consommateur ne perd son droit de rétractation que s'il
    a demandé l'exécution immédiate et reconnu cette perte. La case est dans la
    page, le REFUS est dans le serveur, et la trace est au journal.
"""
import io
import os
import re
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import acces                                                       # noqa: E402
import audit                                                       # noqa: E402
import auth                                                        # noqa: E402
import paiement                                                    # noqa: E402
from conftest import ORIGINE                                        # noqa: E402

import pytest                                                      # noqa: E402

CGV = "cgv.html"
CLIENT = "acheteur.cgv@example.test"


def _src(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


@pytest.fixture
def configure(monkeypatch):
    for nom in (paiement.CLE, paiement.CLE_WEBHOOK, paiement.CLE_PRIX):
        monkeypatch.setenv(nom, "essai")


@pytest.fixture
def compte(monkeypatch):
    monkeypatch.setattr(auth, "send_email", lambda *a, **k: True)
    try:
        auth.store.create({"email": CLIENT, "name": "Acheteur", "org": "Essai",
                           "password_hash": "x", "email_verified": True,
                           "approved": False, "role": "user",
                           "verify_token": None, "verify_expire": None,
                           "approve_token": None, "approve_expire": None,
                           "reset_token": None, "reset_expire": None,
                           "created_at": 0, "last_login": None})
    except Exception:
        pass
    auth.store.update(CLIENT, email_verified=True, approved=False)
    yield
    try:
        auth.store.update(CLIENT, approved=False)
    except Exception:
        pass


# ── 1. Atteignables avant l'achat ─────────────────────────────────────────

def test_les_conditions_sont_ouvertes_a_un_anonyme(anonyme):
    """Enfermer derrière le compte qu'elles servent à vendre les conditions
    qui régissent cette vente les priverait de tout effet."""
    r = anonyme.get("/cgv")
    assert r.status_code == 200
    assert acces.ouvert("/cgv")
    assert "/cgv<" in anonyme.get("/sitemap.xml").get_data(as_text=True)


def test_le_bloc_de_reglement_porte_un_lien_STATIQUE_vers_les_conditions():
    """C'est ce lien-là qui porte l'obligation. Celui du pied de page est posé
    par nav.js : un confort, qui disparaît si le script ne s'exécute pas."""
    for page, ident in (("acces.html", "acRenonce"), ("connexion.html", "payerRenonce")):
        src = _src(page)
        # Ancré sur la CASE elle-même, et non sur un mot : « renonce » se
        # trouve aussi dans la feuille de style, et la règle passait alors sur
        # un fragment qui ne prouvait rien.
        i = src.index('id="%s"' % ident)
        bloc = src[i:i + 900]
        assert 'href="/cgv"' in bloc, page


# ── 2. Le document dit la vérité de cette offre-là ────────────────────────

def test_les_quinze_articles_sont_presents():
    src = _src(CGV)
    for n in range(1, 16):
        assert "Article %d —" % n in src, "article %d manquant" % n


def test_les_mentions_dont_l_absence_est_une_faute():
    src = _src(CGV)
    for mention in ("L221-18", "L221-25", "L221-28", "L224-25-12", "R212-1",
                    "L616-1", "TVA", "médiation", "Formulaire type de rétractation"):
        assert mention in src, mention


def _identite(source):
    """Les valeurs déclarées, extraites par leur ÉTIQUETTE.

    Chercher « 494 530 157 » quelque part dans la page ne prouve rien : ce
    nombre figure aussi dans le numéro de TVA. Une règle écrite ainsi restait
    verte alors que le RCS avait été remplacé — elle passait pour une raison
    sans rapport avec ce qu'elle affirmait. On extrait donc CHAQUE valeur
    derrière son étiquette, et on les compare une à une.
    """
    out = {}
    for etiquette in ("Forme juridique", "Siège social", "RCS",
                      "TVA intracommunautaire"):
        m = re.search(r"<strong>%s</strong>\s*:\s*([^<&]+)" % re.escape(etiquette),
                      source)
        out[etiquette] = re.sub(r"\s+", " ", m.group(1)).strip() if m else None
    return out


def test_l_identite_ne_diverge_pas_des_mentions_legales():
    """Deux exemplaires du RCS et de l'adresse dérivent, et c'est celui qu'on
    oublie de corriger qui reste."""
    ml, cgv = _identite(_src("mentions-legales.html")), _identite(_src(CGV))
    for etiquette, valeur in ml.items():
        assert valeur, "mentions légales : « %s » introuvable" % etiquette
        assert cgv[etiquette] == valeur, (
            "%s : CGV « %s » ≠ mentions légales « %s »"
            % (etiquette, cgv[etiquette], valeur))
    # Le reste de l'identité, qui n'est pas étiqueté de la même façon.
    for fait in ("CONSEILPREV", "Christophe Cerf", "christophe.cerf@outlook.com"):
        assert fait in _src("mentions-legales.html") and fait in _src(CGV), fait


def test_aucun_prix_ne_figure_dans_les_conditions():
    """LA MÊME DÉRIVE QUE LA PAGE D'ACCÈS. Un montant écrit ici vieillirait
    sans que personne s'en aperçoive, et le prix est déjà lu chez Stripe.
    Le capital social est exclu : c'est une mention d'identité, pas un prix."""
    src = _src(CGV)
    identite = re.search(r'<ul id="cgv-identite">.*?</ul>', src, re.S)
    assert identite, "le bloc d'identité n'est plus repérable"
    hors_identite = src.replace(identite.group(0), "")
    hors_identite = re.sub(r"<!--.*?-->", "", hors_identite, flags=re.S)
    fautes = re.findall(r"\d[\d   .,]*\s*(?:€|EUR\b)", hors_identite)
    assert not fautes, "montant écrit dans les CGV : %s" % fautes[:3]


def test_aucun_renvoi_a_la_plateforme_europeenne_de_litiges():
    """Elle a cessé de fonctionner le 20 juillet 2025 ; beaucoup de CGV la
    citent encore, et renvoyer un consommateur vers une porte fermée est pire
    que ne rien dire."""
    src = _src(CGV).lower()
    for mort in ("ec.europa.eu/consumers/odr", "webgate.ec.europa.eu/odr",
                 "plateforme européenne de règlement en ligne"):
        assert mort not in src, mort


def test_le_document_dit_lui_meme_qu_il_est_un_projet():
    """Publier un projet sans le marquer engagerait l'éditeur sur un texte
    qu'il n'a pas validé."""
    src = _src(CGV)
    assert "Projet — non publié" in src
    assert "[À ARBITRER]" in src or "À ARBITRER" in src


def test_la_version_affichee_est_celle_que_le_serveur_conserve():
    """La renonciation est conservée avec la version des conditions : deux
    exemplaires de ce numéro dériveraient, et la trace ne prouverait plus à
    quel texte elle se rapportait."""
    assert paiement.VERSION_CGV.replace(" ", "&nbsp;") in _src(CGV) \
        or paiement.VERSION_CGV in _src(CGV)


# ── 3. La renonciation est refusée par le SERVEUR si elle manque ──────────

def test_la_caisse_refuse_sans_renonciation(anonyme, configure, compte):
    r = anonyme.post("/api/paiement/checkout", json={"email": CLIENT},
                     headers=ORIGINE)
    assert r.status_code == 400
    assert r.get_json()["error"] == "renonciation_absente"


def test_une_renonciation_seulement_declaree_ne_suffit_pas(anonyme, configure, compte):
    """« renonciation »: « oui » n'est pas « renonciation »: true. Le serveur
    exige la valeur, pas sa présence."""
    for valeur in ("oui", 1, "true", None, ""):
        r = anonyme.post("/api/paiement/checkout",
                         json={"email": CLIENT, "renonciation": valeur},
                         headers=ORIGINE)
        assert r.status_code == 400, valeur


def test_la_renonciation_est_tracee_avec_la_version_des_conditions(
        anonyme, configure, compte, monkeypatch):
    """Une renonciation non prouvable ne vaut pas mieux que pas de
    renonciation."""
    vues = []
    vrai = audit.journaliser
    monkeypatch.setattr(audit, "journaliser",
                        lambda action, **k: vues.append((action, k)) or vrai(action, **k))
    monkeypatch.setattr(paiement, "session_paiement",
                        lambda email, base: "https://caisse.test/x")
    r = anonyme.post("/api/paiement/checkout",
                     json={"email": CLIENT, "renonciation": True}, headers=ORIGINE)
    assert r.status_code == 200 and r.get_json()["url"]
    traces = [k for a, k in vues if a == "paiement.renonciation"]
    assert traces, "la renonciation n'a laissé aucune trace"
    assert traces[0]["cible"] == CLIENT
    assert paiement.VERSION_CGV in traces[0]["detail"]


# ── 4. Le bouton dit qu'il engage à payer ─────────────────────────────────

def test_le_bouton_nomme_le_paiement():
    """Art. L221-14 : la mention doit être non ambiguë sur l'obligation de
    payer. « Ouvrir mon accès » ne la portait pas."""
    for page, ident in (("acces.html", "acBtn"), ("connexion.html", "payerBtn")):
        src = _src(page)
        bouton = re.search(r'<button[^>]*id="%s"[^>]*>([^<]*)</button>' % ident, src)
        assert bouton, page
        assert "Payer" in bouton.group(1), (page, bouton.group(1))


def test_les_deux_chemins_vers_la_caisse_portent_la_case():
    """Deux chemins dont un seul recueille le consentement laisseraient une
    porte par laquelle il manque — et c'est celle-là qui servirait."""
    for page, ident in (("acces.html", "acRenonce"), ("connexion.html", "payerRenonce")):
        src = _src(page)
        assert 'id="%s"' % ident in src, page
        assert "L221-28" in src, page
        # La page envoie bien le drapeau, et ne se contente pas de l'afficher.
        assert "renonciation" in src, page
