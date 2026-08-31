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

def test_les_onze_pages_en_acces_direct_sont_celles_qui_ont_ete_nommees():
    """LA ONZIÈME EST « /acces », ET ELLE A ÉTÉ DÉCIDÉE, PAS SUBIE.

    Le site vendait un accès sans jamais dire ce qu'il ouvrait ni ce qu'il
    coûtait : le seul chemin vers la caisse passait par /connexion, donc
    supposait un compte déjà confirmé — ce qu'un acheteur n'a pas. Fermer la
    page qui vend l'accès derrière l'accès ne protège rien et n'ouvre rien.

    Cette liste est la trace écrite de la décision. La mettre à jour EST l'acte
    par lequel on ouvre une page ; c'est pour cela qu'elle est énumérée à la
    main et qu'aucune règle ne la calcule depuis `acces.DIRECT`."""
    assert sorted(acces.DIRECT) == sorted([
        "/", "/about", "/acces", "/contact", "/etudes-de-cas", "/faq",
        "/ressources", "/secteurs", "/services", "/veille", "/vos-projets"])


def test_le_menu_est_bien_lu():
    """Un menu vide validerait n'importe quoi en silence."""
    assert len(MENU) >= 40, len(MENU)
    assert len(OUVERTES) == 11, OUVERTES
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
    """Elle dit LESQUELLES demandent un compte, pas ce qu'elles contiennent.

    `admin` a été ajouté délibérément, et la liste des clés reste FERMÉE pour
    qu'une clé future y bute encore. Ce champ ne divulgue rien de plus :
    distinguer « demande un compte » de « demande le rôle administrateur »
    reste une exigence d'accès, exactement ce qu'un clic apprend. Sans cette
    distinction, nav.js ne pouvait pas marquer, pour un client CONNECTÉ, les
    pages qui lui restent fermées — il voyait des liens sans marque menant à
    un refus."""
    j = anonyme.get("/api/acces").get_json()
    assert set(j) == {"ok", "client", "admin", "note"}, sorted(j)
    assert all(isinstance(c, str) and c.startswith("/") for c in j["client"])
    assert all(isinstance(c, str) and c.startswith("/") for c in j["admin"])
    # L'ensemble « admin » est un SOUS-ENSEMBLE de « client » : une page
    # réservée à l'administration demande d'abord un compte.
    assert set(j["admin"]) <= set(j["client"]), sorted(
        set(j["admin"]) - set(j["client"]))


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
    l'autre laisse un compte en suspens que personne n'attend.

    L'ORDRE A CHANGÉ, ET L'EXIGENCE EST PLUS FORTE QU'AVANT. Les deux courriels
    partaient ensemble, au dépôt de la demande : l'administrateur recevait donc
    des liens d'approbation portant des adresses que PERSONNE n'avait prouvées,
    et le message le priait d'attendre une confirmation dont rien ne l'avisait
    ensuite. Il est maintenant prévenu à la confirmation — les deux
    destinataires y sont toujours, dans l'ordre qui les rend utiles."""
    import auth
    r = anonyme.post("/api/auth/register", headers=H,
                     json=dict(NOUVELLE, captcha=_captcha(anonyme)))
    assert r.status_code == 200, r.get_data(as_text=True)[:200]

    # 1. Au dépôt : le client seul, et rien dans la boîte de l'exploitant.
    assert [m["to"] for m in courriels] == [NOUVELLE["email"]], (
        [m["to"] for m in courriels])
    au_client = next(m for m in courriels if m["to"] == NOUVELLE["email"])
    assert "/verifier-email/" in au_client["html"]
    assert not auth.store.get(NOUVELLE["email"]).get("approve_token"), (
        "un lien d'approbation existe avant que l'adresse soit prouvée")

    # 2. À la confirmation : l'administrateur, avec un lien immédiatement utile.
    u = auth.store.get(NOUVELLE["email"])
    anonyme.get("/verifier-email/%s" % u["verify_token"])
    a_l_admin = next(m for m in courriels if m["to"] == auth.ADMIN_EMAIL)
    assert "/admin/approuver/" in a_l_admin["html"]
    assert NOUVELLE["email"] in a_l_admin["html"], "l'admin doit savoir qui"
    assert auth.store.get(NOUVELLE["email"])["approve_expire"] > auth._now_ms(), (
        "le lien d'approbation n'a pas d'échéance")


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
    # LE JETON SE LIT APRÈS LA CONFIRMATION : c'est elle qui le frappe. Relu
    # sur la fiche d'avant, il valait None — et le lien menait nulle part.
    u = auth.store.get(NOUVELLE["email"])

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


# ── 6. La garde d'accès LIT le décorateur, plutôt que l'affirmer du préfixe ─
#
# LE DÉFAUT CORRIGÉ. _acces_reels()/_acces_api_reels() écrivaient "admin" en
# dur pour tout chemin sous /admin*, sans jamais regarder si @admin_required
# était réellement posé — et verifier_api() n'avait de toute façon aucune
# branche pour comparer un statut "admin" attendu à ce qui est réel : une
# interface /api/admin/… gardée par le seul @login_required (donc ouverte à
# n'importe quel compte client) aurait traversé le contrôle de démarrage sans
# un mot. admin_required pose maintenant `admin_gated`, un repère PLUS FIN que
# `auth_gated` (que login_required pose aussi) et le seul que ces deux
# fonctions lisent désormais.

def test_admin_required_pose_un_repere_plus_fin_que_login_required():
    """Sans ce second repère, rien ne distingue « exige une session » de
    « exige le rôle admin » sur le décorateur lui-même."""
    import auth

    @auth.login_required
    def page_client():
        return "ok"

    @auth.admin_required
    def page_admin():
        return "ok"

    assert getattr(page_client, "auth_gated", False) is True
    assert getattr(page_client, "admin_gated", False) is False
    assert getattr(page_admin, "auth_gated", False) is True
    assert getattr(page_admin, "admin_gated", False) is True


def test_acces_reels_lit_le_decorateur_et_non_le_prefixe_admin():
    """/admin/acces EST sous /admin, et n'est délibérément protégée par
    AUCUN décorateur — c'est le portail public qui MÈNE à la connexion admin.
    AVANT LE CORRECTIF, elle aurait été comptée "admin" par le seul effet de
    son chemin ; deux comparaisons construites sur le même raccourci se
    seraient alors accordées entre elles sans jamais avoir regardé le code."""
    reels = A._acces_reels()
    assert reels.get("/admin/acces") == "direct", reels.get("/admin/acces")
    # Contre-épreuve : une VRAIE page admin, elle, doit ressortir "admin".
    assert reels.get("/admin/comptes") == "admin", reels.get("/admin/comptes")


def test_acces_api_reels_distingue_admin_de_client():
    """Les 40 interfaces /api/admin/ réelles doivent toutes ressortir "admin" —
    pas "client", ce que rendait auth_gated seul, incapable de distinguer les
    deux paliers."""
    reels = A._acces_api_reels()
    admin_api = [c for c in reels if c.startswith("/api/admin/")]
    assert len(admin_api) >= 30, "la famille /api/admin/ semble incomplète"
    non_admin = {c: reels[c] for c in admin_api if reels[c] != "admin"}
    assert not non_admin, non_admin


def test_verifier_api_refuse_desormais_une_interface_admin_mal_protegee():
    """LE POINT QUI DÉCIDE. Avant le correctif, verifier_api() n'avait AUCUNE
    branche pour le statut "admin" : cette entrée fabriquée — une interface
    /api/admin/ protégée par un simple compte client — traversait le contrôle
    sans un mot. Elle doit désormais produire un écart nommé."""
    faux = {"/api/admin/exemple-invente": "client"}
    ecarts = acces.verifier_api(faux)
    assert ecarts, "une interface /api/admin/ mal protégée n'a pas été détectée"
    assert "/api/admin/exemple-invente" in ecarts[0]


def test_verifier_api_n_est_pas_devenu_trop_strict():
    """Le correctif ne doit pas se mettre à accuser les 40 interfaces admin
    réellement protégées : le système réel doit rester à zéro écart."""
    assert acces.verifier_api(A._acces_api_reels()) == []
