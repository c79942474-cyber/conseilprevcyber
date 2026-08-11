"""QUI VOIT QUOI — la politique d'accès, éprouvée porte par porte.

LA RÈGLE ARRÊTÉE. Les pages du menu latéral demandent un compte client :
inscription, confirmation de l'adresse par le client lui-même, validation par
l'administrateur, qui en est averti par courriel. Dix pages restent en accès
direct. L'administrateur atteint tout le site.

CE QUE CES TESTS ÉPROUVENT, ET DANS QUEL ORDRE :

  1. les dix pages ouvertes le sont RÉELLEMENT — une politique qui ferme trop
     est aussi fausse qu'une politique qui ferme trop peu, et elle se remarque
     plus tard, quand un prospect s'est heurté à la page « Contact » ;
  2. toutes les autres refusent l'inconnu ET s'ouvrent au client validé — une
     porte qui refuse tout le monde n'est pas une protection, c'est une panne ;
  3. LES INTERFACES SUIVENT LEURS PAGES. C'est le point qui décide : fermer une
     page en laissant son interface en /api ne protège rien, le contenu se
     récupère en une ligne de commande. C'est l'état qu'on a trouvé ici ;
  4. l'administrateur passe partout ;
  5. le chemin pour OBTENIR un compte reste praticable sans compte — sinon la
     porte n'a pas de sonnette.

Le compte employé pour « client » porte le rôle « user », et non le compte de
recette du dépôt, qui est administrateur : s'en servir aurait prouvé « un admin
y arrive » en laissant croire qu'on avait prouvé le cas ordinaire.
"""
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import acces  # noqa: E402
import app as A  # noqa: E402

H = {"Origin": "http://localhost"}


def menu():
    with open(os.path.join(ICI, "nav.js"), encoding="utf-8") as f:
        js = f.read()
    i = js.index("var NAV_SECTIONS")
    bloc = re.sub(r"//[^\n]*", "", js[i:js.index("];", i)])
    return sorted({a for a, _ in re.findall(r'\["(/[^"]*)",\s*"([^"]*)"\]', bloc)})


MENU = menu()
OUVERTES = [c for c in MENU if acces.ouvert(c)]
FERMEES = [c for c in MENU if not acces.ouvert(c)]


# ── 1. La politique dit ce que la décision disait ──────────────────────────

def test_les_dix_pages_en_acces_direct_sont_celles_qui_ont_ete_nommees():
    assert sorted(acces.DIRECT) == sorted([
        "/", "/about", "/contact", "/etudes-de-cas", "/faq", "/ressources",
        "/secteurs", "/services", "/veille", "/vos-projets"])


def test_le_menu_est_bien_lu():
    """Un menu vide validerait n'importe quoi en silence."""
    assert len(MENU) >= 40, len(MENU)
    assert len(OUVERTES) == 10, OUVERTES
    assert len(FERMEES) >= 30, len(FERMEES)


# ── 2. Les portes ouvertes le sont, les fermées le sont ────────────────────

@pytest.mark.parametrize("chemin", OUVERTES)
def test_une_page_en_acces_direct_s_ouvre_sans_compte(anonyme, chemin):
    """Fermer trop est une faute aussi réelle que ne pas fermer assez : elle se
    paie en prospects qui se heurtent à un formulaire sur « Contact »."""
    r = anonyme.get(chemin)
    assert r.status_code == 200, (chemin, r.status_code)


@pytest.mark.parametrize("chemin", FERMEES)
def test_une_page_reservee_renvoie_l_inconnu_vers_la_connexion(anonyme, chemin):
    r = anonyme.get(chemin)
    assert r.status_code == 302, (chemin, r.status_code)
    assert "/connexion" in r.headers.get("Location", ""), chemin


@pytest.mark.parametrize("chemin", FERMEES)
def test_ET_QU_ELLE_S_OUVRE_AU_CLIENT_VALIDE(connecte, chemin):
    """L'AUTRE MOITIÉ, sans laquelle le contrôle précédent ne prouve rien : une
    porte qui refuse tout le monde le passerait aussi."""
    r = connecte.get(chemin)
    assert r.status_code == 200, (chemin, r.status_code)


# ── 3. LES INTERFACES SUIVENT LEURS PAGES — le point qui décide ────────────

def interfaces_par_regime():
    ouvertes, fermees = [], []
    for rule in A.app.url_map.iter_rules():
        c = str(rule.rule)
        if not c.startswith("/api/") or "<" in c:
            continue
        vue = A.app.view_functions.get(rule.endpoint)
        (fermees if getattr(vue, "auth_gated", False) else ouvertes).append(c)
    return sorted(ouvertes), sorted(fermees)


def test_aucune_interface_n_est_ouverte_sans_motif_ecrit():
    """LE CONTRÔLE QUI COMPTE LE PLUS ICI. Fermer une page sans fermer
    l'interface qui la nourrit ne protège rien : la page renvoie vers le
    formulaire de connexion, et le même contenu se récupère en une ligne de
    commande. Quinze interfaces étaient dans cet état — le calcul, l'état de
    l'art, les lacunes et l'assistant des pages qu'on venait de fermer.

    La règle est donc inversée : toute interface est fermée, sauf motif écrit."""
    ouvertes, _ = interfaces_par_regime()
    sans_motif = [c for c in ouvertes
                  if c not in acces.API_OUVERTES and c not in acces.API_JETON]
    assert not sans_motif, sans_motif


@pytest.mark.parametrize("chemin", sorted(acces.API_OUVERTES))
def test_une_interface_declaree_ouverte_l_est_vraiment(chemin):
    """Une exception déclarée mais fermée en pratique casse ce qu'elle devait
    permettre — créer un compte, se connecter, envoyer un message."""
    _, fermees = interfaces_par_regime()
    assert chemin not in fermees, chemin


@pytest.mark.parametrize("chemin", ["/api/datacenter/etude",
                                    "/api/datacenter/etat-art",
                                    "/api/datacenter/lacunes",
                                    "/api/datacenter/referentiel",
                                    "/api/datacenter/strategie/questionnaire",
                                    "/api/chat"])
def test_les_interfaces_des_pages_fermees_refusent_l_inconnu(anonyme, chemin):
    r = anonyme.get(chemin)
    if r.status_code == 405:                       # interface en écriture seule
        r = anonyme.post(chemin, headers=H, json={})
    assert r.status_code == 401, (chemin, r.status_code)


def test_chaque_motif_d_exception_est_ecrit_et_non_vide():
    """C'est le motif qui rend une exception coûteuse à ajouter, donc rare."""
    for table in (acces.API_OUVERTES, acces.API_JETON, acces.HORS_MENU_OUVERT):
        for chemin, motif in table.items():
            assert motif and len(motif.strip()) > 12, (chemin, motif)


# ── 4. L'administrateur atteint tout le site ───────────────────────────────

@pytest.mark.parametrize("chemin", MENU)
def test_l_administrateur_atteint_toutes_les_pages(admin, chemin):
    r = admin.get(chemin)
    assert r.status_code == 200, (chemin, r.status_code)


def test_l_administrateur_atteint_aussi_ses_propres_pages(admin):
    for chemin in ("/admin", "/admin/comptes", "/admin/base-connaissance",
                   "/admin/clients"):
        r = admin.get(chemin)
        assert r.status_code == 200, (chemin, r.status_code)


def test_un_client_valide_n_atteint_PAS_les_pages_d_administration(connecte):
    """« Tout le site est accessible aux admin » ne veut pas dire l'inverse."""
    for chemin in ("/admin", "/admin/comptes", "/admin/clients"):
        r = connecte.get(chemin)
        assert r.status_code in (302, 401, 403), (chemin, r.status_code)


# ── 5. La porte a une sonnette ─────────────────────────────────────────────

@pytest.mark.parametrize("chemin", ["/connexion", "/inscription",
                                    "/mot-de-passe-oublie"])
def test_obtenir_un_compte_ne_demande_pas_de_compte(anonyme, chemin):
    r = anonyme.get(chemin)
    assert r.status_code == 200, (chemin, r.status_code)


def test_les_pages_legales_restent_lisibles_sans_compte(anonyme):
    """Exiger un compte pour lire sa propre politique de confidentialité serait
    contradictoire — et l'accès à ces mentions est une obligation."""
    for chemin in ("/mentions-legales", "/politique-confidentialite",
                   "/conformite"):
        assert anonyme.get(chemin).status_code == 200, chemin


# ── 6. Ce que le site déclare aux moteurs, et à ses visiteurs ──────────────

def test_le_plan_du_site_ne_declare_que_des_pages_atteignables(anonyme):
    """Déclarer une adresse qui renvoie vers un formulaire de connexion fait
    indexer le formulaire, et promet au lecteur venu d'un moteur une page qu'il
    n'atteindra pas."""
    from urllib.parse import urlparse
    x = anonyme.get("/sitemap.xml").get_data(as_text=True)
    declares = re.findall(r"<loc>([^<]+)</loc>", x)
    assert declares, "le plan du site est vide"
    for url in declares:
        c = urlparse(url).path.rstrip("/") or "/"
        assert acces.ouvert(c), (c, url)


def test_la_liste_servie_dit_ce_qui_demande_un_compte(anonyme):
    j = anonyme.get("/api/acces").get_json()
    assert j["ok"] is True
    assert set(FERMEES) <= set(j["client"]), sorted(set(FERMEES) - set(j["client"]))
    for chemin in OUVERTES:
        assert chemin not in j["client"], chemin


def test_la_liste_servie_ne_divulgue_rien_d_autre(anonyme):
    """Elle dit LESQUELLES demandent un compte, pas ce qu'elles contiennent."""
    j = anonyme.get("/api/acces").get_json()
    assert set(j) == {"ok", "client", "note"}, sorted(j)
    assert all(isinstance(c, str) and c.startswith("/") for c in j["client"])


# ── 7. LE PARCOURS QUI DONNE UN COMPTE ─────────────────────────────────────
# La règle ne dit pas seulement « il faut un compte » : elle dit COMMENT on
# l'obtient — inscription, confirmation par le client sur sa propre adresse,
# validation par l'administrateur, qui en est averti par courriel. Chacun de
# ces quatre temps est un endroit où le parcours peut se rompre en silence.

@pytest.fixture
def courriels(monkeypatch):
    """Capture les envois au lieu de les faire partir.

    Les envois se font dans un fil séparé : on remplace `Thread` par une
    exécution immédiate, sans quoi le test lirait la boîte avant l'envoi et
    conclurait à tort qu'aucun courriel ne part."""
    import auth
    boite = []
    monkeypatch.setattr(auth, "send_email",
                        lambda to, nom, sujet, html: boite.append(
                            {"to": to, "sujet": sujet, "html": html}) or True)

    class FilImmediat:
        def __init__(self, target=None, args=(), daemon=None, **k):
            self._t, self._a = target, args

        def start(self):
            self._t(*self._a)

    monkeypatch.setattr(auth.threading, "Thread", FilImmediat)
    return boite


NOUVELLE = {"email": "prospect.essai@example.test", "name": "Prospect Essai",
            "org": "Essai SA", "password": "MotDePasseSolide!2026"}


@pytest.fixture
def sans_trace():
    """Le compte d'essai ne doit pas survivre au test."""
    import auth
    auth.store.delete(NOUVELLE["email"])
    yield
    auth.store.delete(NOUVELLE["email"])


def _captcha(c):
    j = c.get("/api/auth/captcha").get_json()
    q = j.get("question") or j.get("captcha") or ""
    a, b = [int(x) for x in re.findall(r"\d+", q)[:2]]
    return a + b


def test_l_inscription_ecrit_AU_CLIENT_et_PREVIENT_l_administrateur(
        anonyme, courriels, sans_trace):
    """LES DEUX DESTINATAIRES, ET C'EST TOUTE LA DEMANDE. Le client reçoit sur
    SA propre adresse le lien qui confirme qu'elle est bien la sienne ;
    l'administrateur reçoit sur la sienne la demande à valider. L'un sans
    l'autre laisse un compte en suspens que personne n'attend."""
    import auth
    r = anonyme.post("/api/auth/register", headers=H,
                     json=dict(NOUVELLE, captcha=_captcha(anonyme)))
    assert r.status_code == 200, r.get_data(as_text=True)[:200]

    destinataires = [m["to"] for m in courriels]
    assert NOUVELLE["email"] in destinataires, destinataires
    assert auth.ADMIN_EMAIL in destinataires, destinataires

    au_client = next(m for m in courriels if m["to"] == NOUVELLE["email"])
    assert "/verifier-email/" in au_client["html"]
    a_l_admin = next(m for m in courriels if m["to"] == auth.ADMIN_EMAIL)
    assert "/admin/approuver/" in a_l_admin["html"]
    assert NOUVELLE["email"] in a_l_admin["html"], "l'admin doit savoir qui"


def test_l_adresse_de_l_administrateur_est_bien_celle_qui_a_ete_donnee():
    import auth
    assert auth.ADMIN_EMAIL == "christophe.cerf@outlook.com", auth.ADMIN_EMAIL


def test_un_compte_inscrit_mais_NON_VALIDE_n_ouvre_aucune_page(
        anonyme, courriels, sans_trace):
    """LE CONTRÔLE QUI COMPTE DANS CE PARCOURS. S'inscrire ne donne rien : ni
    la confirmation d'adresse seule, ni l'attente de validation ne doivent
    ouvrir une page réservée. Sans ce contrôle, « validation par l'admin »
    serait une formalité que le site n'applique pas."""
    import auth
    anonyme.post("/api/auth/register", headers=H,
                 json=dict(NOUVELLE, captcha=_captcha(anonyme)))
    ferme = FERMEES[0]

    c = A.app.test_client()
    with c.session_transaction() as s:
        s["user_email"] = NOUVELLE["email"]
    assert c.get(ferme).status_code == 302, "inscrit, non confirmé : refusé"

    # Adresse confirmée, mais pas encore validée par l'administrateur.
    u = auth.store.get(NOUVELLE["email"])
    anonyme.get("/verifier-email/%s" % u["verify_token"])
    assert auth.store.get(NOUVELLE["email"])["email_verified"] is True
    assert c.get(ferme).status_code == 302, (
        "adresse confirmée mais accès non validé : toujours refusé")


def test_la_validation_par_l_administrateur_ouvre_ET_PREVIENT_le_client(
        anonyme, courriels, sans_trace):
    import auth
    anonyme.post("/api/auth/register", headers=H,
                 json=dict(NOUVELLE, captcha=_captcha(anonyme)))
    u = auth.store.get(NOUVELLE["email"])
    anonyme.get("/verifier-email/%s" % u["verify_token"])

    del courriels[:]
    r = anonyme.get("/admin/approuver/%s" % u["approve_token"])
    assert r.status_code == 200, r.status_code

    assert [m["to"] for m in courriels] == [NOUVELLE["email"]], (
        "le client doit être prévenu sur SA propre adresse, et lui seul")
    assert "/connexion" in courriels[0]["html"]

    c = A.app.test_client()
    with c.session_transaction() as s:
        s["user_email"] = NOUVELLE["email"]
    assert c.get(FERMEES[0]).status_code == 200, "validé : la page s'ouvre"


def test_le_point_de_sante_DIT_si_le_courriel_peut_partir(anonyme, monkeypatch):
    """LA PANNE LA PLUS DANGEREUSE DE CE DISPOSITIF EST SILENCIEUSE. Sans clef
    d'envoi, send_email() renvoie faux et journalise : personne ne reçoit rien,
    le visiteur attend un lien qui ne viendra pas, et l'administrateur ignore
    qu'une demande dort. Depuis que tout l'accès au site passe par trois
    courriels, cet état doit se CONSTATER de l'extérieur, sans lire les
    journaux."""
    import auth

    monkeypatch.delenv("BREVO_API_KEY", raising=False)
    j = anonyme.get("/health").get_json()
    assert j["courriel"] == "SANS_CLEF", j.get("courriel")
    assert j["status"] == "degraded"
    assert "inscription" in j["cause_courriel"]
    assert j["courriel_admin"] == auth.ADMIN_EMAIL

    monkeypatch.setenv("BREVO_API_KEY", "clef-d-essai")
    j = anonyme.get("/health").get_json()
    assert j["courriel"] == "configure", j.get("courriel")
    assert "cause_courriel" not in j
