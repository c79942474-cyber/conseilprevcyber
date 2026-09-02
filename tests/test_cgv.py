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
    for page, ident in (("acces.html", "acCgv"), ("connexion.html", "payerCgv")):
        src = _src(page)
        # Ancré sur la CASE elle-même, et non sur un mot : « cgv » se trouve
        # partout dans la page, et la règle passerait alors sur un fragment qui
        # ne prouve rien. Le lien vit dans la case d'ACCEPTATION — c'est celle
        # qui a besoin de mener au texte qu'elle fait accepter.
        i = src.index('id="%s"' % ident)
        bloc = src[i:i + 500]
        assert 'href="/cgv"' in bloc, page


# ── 2. Le document dit la vérité de cette offre-là ────────────────────────

def test_les_quinze_articles_sont_presents():
    src = _src(CGV)
    for n in range(1, 16):
        assert "Article %d —" % n in src, "article %d manquant" % n


def test_les_mentions_dont_l_absence_est_une_faute():
    src = _src(CGV)
    # LA LISTE A CHANGÉ AVEC LE PUBLIC. La vente étant réservée aux
    # professionnels, R212-1 (clauses abusives du code de la consommation) cède
    # la place à l'article 1171 du code civil, et L616-1 (médiation) à la
    # constatation qu'elle est sans objet. Ce qui NE change pas, c'est la
    # réserve de l'article L221-3 : elle est la raison pour laquelle le régime
    # protecteur ne disparaît pas tout à fait.
    for mention in ("L221-3", "L221-18", "L221-25", "L221-28", "L224-25-12",
                    "1170", "1171", "1604", "1641", "TVA", "médiation",
                    "Formulaire type de rétractation"):
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


def test_le_texte_en_vigueur_ne_porte_ni_bandeau_ni_crochet():
    """UN CONTRAT AVEC DES CROCHETS DEDANS SE LIT COMME INACHEVÉ. Tant qu'il
    portait le bandeau « projet », les crochets étaient honnêtes ; le bandeau
    retiré, ils deviennent des trous."""
    src = _src(CGV)
    assert "Projet — non publié" not in src
    sans_commentaires = re.sub(r"<!--.*?-->", "", src, flags=re.S)
    fautes = re.findall(r"\[À [A-ZÀ-Ÿ]+[^\]]*\]", sans_commentaires)
    assert not fautes, "crochets restés dans un texte en vigueur : %s" % fautes
    assert "Version <b>2026-09-a</b>, en vigueur" in src


def test_les_points_ouverts_ne_sont_plus_sous_les_yeux_du_client():
    """Ils ne disparaissent pas : ils changent de place. Un client n'a pas à
    lire « à confronter au corpus » sur huit articles du contrat qu'on lui
    oppose ; le vendeur, lui, doit continuer de le savoir."""
    src = _src(CGV)
    assert "cgv-verif" not in src, "pastille encore visible"
    assert "Ce qui reste à confronter" not in src
    assert re.search(r"<!-- verif:[a-z]+ -->", src), "les marques ont disparu"
    doc = _src("docs/cgv-points-ouverts.md")
    # L'ÉTAT DE LA CONFRONTATION AU CORPUS, ET NON UNE PHRASE FIGÉE. La règle
    # exigeait « Aucune décision de justice n'a été lue » — vrai tant que les
    # serveurs juridiques étaient refusés, faux le jour où l'un d'eux a répondu.
    # Une règle qui verrouille un libellé empêche de dire la vérité suivante.
    # Ce qui doit tenir : que le document dise combien de points sont confrontés
    # et combien ne le sont pas, et que ce compte soit celui du tableau.
    lignes = re.findall(r"^\| `([a-z]+)` \| \d+ \| (.*)$", doc, re.M)
    assert len(lignes) == 8, "le tableau des huit points en compte %d" % len(lignes)
    confrontes = [c for c, t in lignes if "CONFRONTÉ" in t]
    restants = len(lignes) - len(confrontes)
    if restants:
        mot = {1: "un", 2: "deux", 3: "trois", 4: "quatre",
               5: "cinq", 6: "six", 7: "sept", 8: "huit"}[restants]
        assert ("%s autres restent non confrontés" % mot) in doc or \
               ("%s points restent non confrontés" % mot) in doc, (
            "%d point(s) ne sont pas confrontés au corpus, et le document ne le "
            "dit pas en toutes lettres" % restants)
    for cle in confrontes:
        assert "librejustice.fr/decision/" in doc, (
            "le point « %s » se dit confronté sans citer de décision" % cle)


def test_la_version_affichee_est_celle_que_le_serveur_conserve():
    """La renonciation est conservée avec la version des conditions : deux
    exemplaires de ce numéro dériveraient, et la trace ne prouverait plus à
    quel texte elle se rapportait."""
    assert paiement.VERSION_CGV.replace(" ", "&nbsp;") in _src(CGV) \
        or paiement.VERSION_CGV in _src(CGV)


# ── 3. La renonciation est refusée par le SERVEUR si elle manque ──────────

def test_la_caisse_refuse_sans_renonciation(anonyme, configure, compte):
    """Les conditions acceptées, la renonciation manquante : c'est le second
    consentement qui est en cause, et le message doit le dire."""
    r = anonyme.post("/api/paiement/checkout",
                     json={"email": CLIENT, "professionnel": True, "cgv": True},
                     headers=ORIGINE)
    assert r.status_code == 400
    assert r.get_json()["error"] == "renonciation_absente"


def test_la_caisse_refuse_sans_acceptation_des_conditions(anonyme, configure, compte):
    """DEUX CONSENTEMENTS DISTINCTS, ET DEUX REFUS DISTINCTS. Une case unique
    en portait trois — acceptation, exécution immédiate, renoncement — et un
    consentement groupé est le plus facile à contester."""
    r = anonyme.post("/api/paiement/checkout",
                     json={"email": CLIENT, "professionnel": True, "renonciation": True},
                     headers=ORIGINE)
    assert r.status_code == 400
    assert r.get_json()["error"] == "conditions_non_acceptees"


def test_la_caisse_refuse_sans_declaration_de_qualite(anonyme, configure, compte):
    """UNE RESTRICTION DÉCLARÉE N'EST PAS UNE RESTRICTION. Les conditions
    réservent la vente aux professionnels ; sans ce refus au serveur, la clause
    de l'article 1 serait une phrase."""
    r = anonyme.post("/api/paiement/checkout",
                     json={"email": CLIENT, "cgv": True, "renonciation": True},
                     headers=ORIGINE)
    assert r.status_code == 400
    assert r.get_json()["error"] == "qualite_non_declaree"


def test_une_renonciation_seulement_declaree_ne_suffit_pas(anonyme, configure,
                                                          compte, monkeypatch):
    """« renonciation »: « oui » n'est pas « renonciation »: true. Le serveur
    exige la valeur, pas sa présence."""
    # LE PLAFOND DE CADENCE N'EST PAS L'OBJET DE CETTE RÈGLE. Quinze essais
    # le déclenchent et le 429 masquerait le 400 qu'on veut voir ; la cadence a
    # sa propre règle ailleurs.
    import app as _app
    monkeypatch.setattr(_app.guard, "blocked", lambda *a, **k: False)
    for valeur in ("oui", 1, "true", None, ""):
        for champ in ("professionnel", "cgv", "renonciation"):
            charge = {"email": CLIENT, "professionnel": True, "cgv": True,
                      "renonciation": True}
            charge[champ] = valeur
            r = anonyme.post("/api/paiement/checkout", json=charge, headers=ORIGINE)
            assert r.status_code == 400, (champ, valeur)


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
                     json={"email": CLIENT, "professionnel": True, "cgv": True,
                           "renonciation": True},
                     headers=ORIGINE)
    assert r.status_code == 200 and r.get_json()["url"]
    assert [k for a, k in vues if a == "paiement.qualite"], (
        "la déclaration de qualité professionnelle n'a laissé aucune trace")
    for action in ("paiement.renonciation", "paiement.conditions"):
        traces = [k for a, k in vues if a == action]
        assert traces, "%s n'a laissé aucune trace" % action
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
    for page, cases in (("acces.html", ("acPro", "acCgv", "acRenonce")),
                        ("connexion.html", ("payerPro", "payerCgv", "payerRenonce"))):
        src = _src(page)
        for ident in cases:
            assert 'id="%s"' % ident in src, (page, ident)
        assert "L221-28" in src, page
        # La page envoie bien les DEUX drapeaux, et ne se contente pas de les
        # afficher : séparer à l'écran sans séparer à l'envoi serait cosmétique.
        envoi = src[src.index("checkout"):src.index("checkout") + 400]
        for drapeau in ("professionnel", "cgv", "renonciation"):
            assert drapeau in envoi, (page, drapeau)


# ── 5. CE QUI SE JUGE NE SE LIT PAS — la confrontation au corpus ──────────
#
# Huit clauses du projet ne valent que ce que la jurisprudence leur laisse
# valoir. Ces règles ne vérifient pas le droit — elles ne le peuvent pas — mais
# elles vérifient que l'INSTRUMENT existe, qu'il refuse de se taire quand le
# corpus ne répond pas, et que le projet et la grille ne dérivent pas l'un de
# l'autre.

def _grille():
    sys.path.insert(0, os.path.join(ICI, "outils"))
    import verifier_cgv
    return verifier_cgv


def test_chaque_clause_marquee_a_son_point_de_controle():
    """DANS LES DEUX SENS. Une clause marquée sans point serait une promesse de
    vérification que rien ne tient ; un point sans clause marquée serait une
    vérification dont le lecteur du projet ignore l'existence."""
    marques = set(re.findall(r"<!-- verif:([a-z]+) -->", _src(CGV)))
    grille = {p["cle"] for p in _grille().POINTS}
    assert marques == grille, (
        "marquées sans point : %s ; points sans marque : %s"
        % (sorted(marques - grille), sorted(grille - marques)))


def test_chaque_point_porte_sa_question_et_son_ancrage():
    """Un point sans question n'interroge rien ; un point sans ancrage légal
    ne dit pas ce qu'on cherche à valider."""
    for p in _grille().POINTS:
        for champ in ("cle", "article", "ancrage", "enjeu", "question"):
            assert (p.get(champ) or "").strip(), (p.get("cle"), champ)
        assert len(p["question"].split()) >= 6, p["cle"]


def test_l_instrument_refuse_de_se_taire_quand_le_corpus_ne_repond_pas(monkeypatch, capsys):
    """LA RÈGLE QUI COMPTE. « Aucune décision trouvée » et « je n'ai pas pu
    chercher » sont deux phrases opposées : les confondre rendrait un contrôle
    rassurant qui n'a rien contrôlé."""
    import librejustice
    v = _grille()
    monkeypatch.setattr(librejustice, "disponible",
                        lambda: {"ok": False, "motif": "corpus injoignable (essai)"})
    code = v.main(["verifier_cgv.py"])
    sortie = capsys.readouterr().out
    assert code != 0, "un corpus injoignable est sorti en succès"
    assert "AUCUN POINT N'A ÉTÉ VÉRIFIÉ" in sortie
    assert "injoignable" in sortie


def test_l_instrument_distingue_une_liste_vide_d_une_absence_de_reponse(monkeypatch, capsys):
    """Une liste vide EST une réponse — le corpus a cherché et n'a rien —, et
    elle ne doit pas se lire comme une validation."""
    import librejustice
    v = _grille()
    monkeypatch.setattr(librejustice, "disponible", lambda: {"ok": True, "outils": ["x"]})
    monkeypatch.setattr(librejustice, "rechercher",
                        lambda q, limite=6, **k: {"ok": True, "decisions": [],
                                                  "motif": "", "requete": q})
    code = v.main(["verifier_cgv.py", "garantie"])
    sortie = capsys.readouterr().out
    assert code == 0
    assert "Aucune décision dans le corpus" in sortie
    assert "ne valide pas la clause" in sortie


def test_l_instrument_n_ecrit_aucune_decision_qu_il_n_a_pas_recue(monkeypatch, capsys):
    """Il rapporte ce que le corpus rend, et rien d'autre : c'est toute la
    raison d'être de librejustice.py."""
    import librejustice
    v = _grille()
    monkeypatch.setattr(librejustice, "disponible", lambda: {"ok": True, "outils": ["x"]})
    monkeypatch.setattr(librejustice, "rechercher",
                        lambda q, limite=6, **k: {"ok": True, "requete": q, "motif": "",
                                                  "decisions": [{"titre": "Cass. civ. 1re, 1 janv. 2000",
                                                                 "url": "https://librejustice.fr/d/1",
                                                                 "apercu": "un aperçu",
                                                                 "apercu_non_citable": True}]})
    v.main(["verifier_cgv.py", "plafond"])
    sortie = capsys.readouterr().out
    assert "Cass. civ. 1re, 1 janv. 2000" in sortie
    assert "https://librejustice.fr/d/1" in sortie
    # L'aperçu est servi AVEC son avertissement : il finirait sinon cité comme
    # la position de la cour.
    assert "NON CITABLE" in sortie


def test_les_corrections_qui_ne_dependent_pas_du_corpus_sont_faites():
    """Elles se tirent du code, pas de la jurisprudence : rien ne justifiait
    de les remettre à plus tard."""
    src = _src(CGV)
    for fait in ("1110",        # contrat d'adhésion
                 "1190",        # interprétation contre le vendeur
                 "1127-1",      # conservation et impression
                 "1127-2",      # déroulement de la commande
                 "1170",        # clause limitative et obligation essentielle
                 "1171",        # déséquilibre significatif
                 "L442-1"):     # pratiques restrictives
        assert fait in src, "article %s absent du projet" % fait


# ── 6. LA CONFIRMATION DE COMMANDE, SUR UN SUPPORT DURABLE ───────────────
#
# CE QUI MANQUAIT. L'acheteur recevait « votre accès a été approuvé », et rien
# d'autre : ni ce qu'il avait acheté, ni le prix, ni la version des conditions,
# ni un mot de la renonciation. Le seul message parlant de commande partait chez
# l'administrateur. La renonciation ne vivait donc que dans le journal du
# serveur — prouvable par le vendeur, jamais confirmée à l'acheteur, alors que
# c'est cette confirmation qui fait tenir l'exclusion (art. L221-13).

def _courriels(monkeypatch):
    envois = []
    monkeypatch.setattr(auth, "send_email",
                        lambda to, nom, sujet, html: envois.append((to, sujet, html)))
    return envois


COMMANDE = {"reference": "cs_test_x", "montant": 49000, "devise": "eur",
            "affichage": "490,00 €", "conditions": paiement.VERSION_CGV}


def test_le_chemin_payant_confirme_la_commande_a_l_acheteur(monkeypatch, compte):
    envois = _courriels(monkeypatch)
    auth._confirmer_commande(auth.store.get(CLIENT), COMMANDE, "https://exemple.test")
    to, sujet, html = envois[-1]
    assert to == CLIENT
    assert "ommande" in sujet
    for du in ("490,00", paiement.VERSION_CGV, "/cgv",
               "L221-25", "L221-28", "support durable",
               "perte de votre droit de rétractation"):
        assert du in html, du


def test_la_confirmation_porte_l_identite_du_vendeur(monkeypatch, compte):
    """Sans elle, la confirmation ne confirme pas un contrat : elle annonce un
    accès."""
    envois = _courriels(monkeypatch)
    auth._confirmer_commande(auth.store.get(CLIENT), COMMANDE, "https://exemple.test")
    html = envois[-1][2]
    for champ in ("denomination", "siege", "rcs", "contact"):
        assert paiement.VENDEUR[champ] in html, champ


def test_un_montant_absent_n_est_pas_invente(monkeypatch, compte):
    """Une confirmation sans prix est incomplète ; une confirmation avec un
    prix faux est fausse. On ne remplit pas le trou."""
    envois = _courriels(monkeypatch)
    sans = dict(COMMANDE, montant=None, affichage=None, devise=None)
    auth._confirmer_commande(auth.store.get(CLIENT), sans, "https://exemple.test")
    html = envois[-1][2]
    assert "490" not in html and "0,00" not in html
    assert "reçu" in html, "le message ne dit pas où trouver le montant"


def test_le_chemin_manuel_ne_parle_d_aucune_commande(monkeypatch, compte):
    """Il n'y en a pas. Y mélanger une confirmation serait la faute déjà
    corrigée sur l'avertissement d'ouverture payée."""
    envois = _courriels(monkeypatch)
    auth._send_approved(auth.store.get(CLIENT), "https://exemple.test")
    html = envois[-1][2]
    for absent in ("L221-28", "rétractation", "Montant", paiement.VERSION_CGV):
        assert absent not in html, absent


def test_l_ouverture_payee_envoie_la_confirmation_et_non_l_approbation(monkeypatch, compte):
    """`commande` non nul SIGNIFIE chemin payant : c'est ce qui décide du
    message, et un événement sans montant reste un chemin payant."""
    envois = _courriels(monkeypatch)
    monkeypatch.setattr(auth.threading, "Thread",
                        lambda target, args=(), daemon=None: type(
                            "T", (), {"start": lambda _s: target(*args)})())
    assert auth.ouvrir_par_paiement(CLIENT, "https://exemple.test",
                                    commande=dict(COMMANDE, montant=None,
                                                  affichage=None)) is True
    vers_client = [h for to, _s, h in envois if to == CLIENT]
    assert vers_client, "l'acheteur n'a rien reçu"
    assert "L221-28" in vers_client[-1], (
        "le chemin payant a envoyé le message du chemin manuel")


def test_l_evenement_verifie_fournit_les_details_de_la_commande():
    """Ils viennent de la notification DÉJÀ signée, jamais d'un second appel :
    la signature n'a été contrôlée que sur celle-là."""
    ev = {"type": "checkout.session.completed",
          "data": {"object": {"id": "cs_1", "amount_total": 12300,
                              "currency": "eur", "payment_status": "paid"}}}
    d = paiement.details_commande(ev)
    assert d["montant"] == 12300 and d["affichage"].startswith("123,00")
    assert d["conditions"] == paiement.VERSION_CGV
    # Sans montant, le dictionnaire EXISTE quand même : il dit « chemin
    # payant », pas « prix connu ». Les confondre ferait partir le courriel du
    # chemin manuel sur un événement incomplet.
    sans = paiement.details_commande(
        {"type": "checkout.session.completed", "data": {"object": {"id": "cs_2"}}})
    assert sans is not None and sans["montant"] is None
    assert paiement.details_commande({"type": "autre.chose"}) is None


def test_l_identite_du_vendeur_est_la_meme_dans_les_trois_exemplaires():
    """Le courriel ne peut pas lire une page HTML : il y a trois copies, et
    c'est une règle — non la discipline — qui les tient ensemble."""
    ml = _identite(_src("mentions-legales.html"))
    assert paiement.VENDEUR["siege"] == ml["Siège social"]
    assert paiement.VENDEUR["rcs"] in ml["RCS"]
    assert paiement.VENDEUR["forme"] == ml["Forme juridique"]
    assert paiement.VENDEUR["tva"] == ml["TVA intracommunautaire"]


def test_l_arbitrage_du_remboursement_est_consigne_et_le_risque_nomme():
    """Un projet qui continue de proposer une option que le donneur d'ordre a
    rejetée n'inspire pas confiance — et un risque tu n'est pas un risque
    absent."""
    src = _src(CGV)
    assert "expressément écarté" in src
    assert "À ARBITRER]</strong> — <em>Le vendeur peut choisir" not in src
    assert "Risque assumé" in src
    assert "malgré</em> la renonciation" in src
    # La marque reste : le corpus n'a pas parlé.
    assert "<!-- verif:retractation -->" in src


# ── 7. LA RESTRICTION B2B EST EFFECTIVE, PAS DÉCORATIVE ──────────────────
#
# Les conditions de Sentinel se déclarent « exclusivement B2B » pendant que leur
# formulaire accepte tout le monde. Celles-ci ne le peuvent pas : l'inscription
# exige une organisation, et la vente exige une déclaration de qualité, refusée
# au serveur et tracée.

def test_l_inscription_refuse_une_demande_sans_organisation(anonyme, monkeypatch):
    monkeypatch.setattr(auth, "send_email", lambda *a, **k: True)
    monkeypatch.setattr(auth, "_check_captcha", lambda slot, rep: True)
    r = anonyme.post("/api/auth/register", headers=ORIGINE, json={
        "email": "sans.orga@example.test", "name": "Sans Orga",
        "password": "MotDePasse2026", "captcha": "0"})
    assert r.status_code == 400
    assert "rofessionnel" in r.get_json()["error"]


def test_l_inscription_accepte_une_demande_avec_organisation(anonyme, monkeypatch):
    """La règle doit DISCRIMINER : refuser tout le monde la satisferait aussi."""
    monkeypatch.setattr(auth, "send_email", lambda *a, **k: True)
    monkeypatch.setattr(auth, "_check_captcha", lambda slot, rep: True)
    monkeypatch.setattr(auth.threading, "Thread",
                        lambda target, args=(), daemon=None: type(
                            "T", (), {"start": lambda _s: None})())
    r = anonyme.post("/api/auth/register", headers=ORIGINE, json={
        "email": "avec.orga@example.test", "name": "Avec Orga",
        "org": "Une société", "password": "MotDePasse2026", "captcha": "0"})
    assert r.status_code == 200, r.get_json()


def test_le_formulaire_ne_dit_plus_l_organisation_facultative():
    """Un champ requis au serveur et annoncé « facultatif » à l'écran envoie le
    demandeur dans un refus qu'il ne comprend pas."""
    src = _src("inscription.html")
    champ = re.search(r'<input id="org"[^>]*>', src).group(0)
    assert "required" in champ
    libelle = src[src.index('for="org"'):src.index('<input id="org"')]
    assert "Facultatif" not in libelle


def test_le_texte_reserve_la_vente_aux_professionnels_et_dit_pourquoi():
    src = _src(CGV)
    assert "vendu aux\n      professionnels" in src or "vendu aux professionnels" in src
    assert "n'est pas proposé aux\n      consommateurs" in src or \
           "pas proposé aux consommateurs" in src
    # LA RÉSERVE N'EST PAS ENFOUIE : elle est dans le chapeau, avant les
    # articles, parce qu'elle décide de ce que la moitié d'entre eux valent.
    chapeau = src[:src.index("Article 1 —")]
    assert "L221-3" in chapeau
    assert "cinq salariés ou moins" in chapeau


def test_les_arbitrages_sont_ecrits_dans_le_texte_et_leur_risque_dans_le_dossier():
    """Un contrat n'argumente pas contre lui-même ; le vendeur doit pourtant
    savoir où il est exposé. Deux endroits, deux rôles."""
    src, doc = _src(CGV), _src("docs/cgv-points-ouverts.md")
    assert "préavis de trois mois" in src
    assert "ne donne lieu à aucun remboursement" in src
    assert "montant effectivement payé" in src
    assert "sans objet" in src            # la médiation
    for risque in ("déséquilibre\nsignificatif", "déséquilibre significatif"):
        if risque in doc:
            break
    else:
        raise AssertionError("le risque de la clause de cessation n'est pas écrit")
    assert "L221-3" in doc


def test_le_dossier_des_points_ouverts_et_la_grille_ne_derivent_pas():
    doc = _src("docs/cgv-points-ouverts.md")
    cles = set(re.findall(r"\| `([a-z]+)` \|", doc))
    assert cles == {p["cle"] for p in _grille().POINTS}, sorted(cles)


def test_la_version_des_conditions_est_celle_qui_est_affichee():
    assert paiement.VERSION_CGV == "2026-09-a"
    assert "PROJET" not in paiement.VERSION_CGV
    assert paiement.VERSION_CGV in _src(CGV)
