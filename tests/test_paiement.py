"""Un paiement ouvre un accès — et rien d'autre ne l'ouvre.

CE QUE CE CHEMIN VEND. La table des comptes ne porte ni offre, ni palier, ni
quota : l'accès y est binaire. Un paiement n'a donc qu'une chose à faire —
poser `approved`. Tout ce qui ressemblerait à un abonnement demanderait d'abord
de savoir FERMER un accès impayé, ce que ce modèle ne sait pas faire.

LES DEUX RÈGLES QUI TIENNENT TOUT :

  · AUCUNE ROUTE N'OUVRE UN ACCÈS. Il n'y a que la notification signée. Un
    client ne peut pas se promouvoir en appelant une adresse.
  · ON OUVRE L'ADRESSE QUE NOTRE SERVEUR A LIÉE, jamais celle tapée dans le
    formulaire de paiement. Sinon une faute de frappe encaisse un paiement qui
    n'ouvre rien, et personne ne sait pourquoi.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import auth                                                        # noqa: E402
import paiement                                                    # noqa: E402
from conftest import ORIGINE                                        # noqa: E402

ACHETEUR = "acheteur.paiement@example.test"
AUTRE = "quelqu-un-dautre@example.test"


def _evenement(reference, paye=True, sorte="checkout.session.completed",
               email_saisi=AUTRE):
    return {"type": sorte,
            "data": {"object": {
                "payment_status": "paid" if paye else "unpaid",
                "client_reference_id": reference,
                "customer_details": {"email": email_saisi}}}}


@pytest.fixture
def compte(monkeypatch):
    """Un compte confirmé, pas encore ouvert — l'état exact où le paiement sert."""
    envois = []
    monkeypatch.setattr(auth, "send_email",
                        lambda *a, **k: envois.append(a[2] if len(a) > 2 else ""))
    try:
        auth.store.create({"email": ACHETEUR, "name": "Acheteur", "org": "Essai",
                           "password_hash": "x", "email_verified": True,
                           "approved": False, "role": "user",
                           "verify_token": None, "verify_expire": None,
                           "approve_token": None, "approve_expire": None,
                           "reset_token": None, "reset_expire": None,
                           "created_at": 0, "last_login": None})
    except Exception:
        pass
    auth.store.update(ACHETEUR, email_verified=True, approved=False)
    yield envois
    try:
        auth.store.update(ACHETEUR, approved=False)
    except Exception:
        pass


@pytest.fixture
def configure(monkeypatch):
    for nom in (paiement.CLE, paiement.CLE_WEBHOOK, paiement.CLE_PRIX):
        monkeypatch.setenv(nom, "essai")
    return True


# ── 1. Sans clés, le service vit sa vie ───────────────────────────────────

def test_sans_cles_le_paiement_se_declare_absent(monkeypatch):
    """Une configuration manquante ne doit JAMAIS empêcher le service de
    tourner — c'est la leçon de l'incident des réglages, et elle vaut ici."""
    for nom in (paiement.CLE, paiement.CLE_WEBHOOK, paiement.CLE_PRIX):
        monkeypatch.delenv(nom, raising=False)
    assert paiement.configure() is False
    assert paiement.session_paiement(ACHETEUR, "https://x") is None
    assert paiement.lire_evenement(b"{}", "sig") is None


def test_les_trois_valeurs_ensemble_ou_rien(monkeypatch):
    """Une clé sans identifiant de prix ouvrirait un bouton qui mène à une
    erreur — et un bouton qui échoue vaut moins qu'un bouton absent."""
    monkeypatch.setenv(paiement.CLE, "sk")
    monkeypatch.setenv(paiement.CLE_WEBHOOK, "wh")
    monkeypatch.delenv(paiement.CLE_PRIX, raising=False)
    assert paiement.configure() is False


def test_les_routes_repondent_sans_cles_jamais_500(anonyme, monkeypatch):
    for nom in (paiement.CLE, paiement.CLE_WEBHOOK, paiement.CLE_PRIX):
        monkeypatch.delenv(nom, raising=False)
    assert anonyme.get("/api/paiement/etat").get_json()["configure"] is False
    r = anonyme.post("/api/paiement/checkout", json={"email": ACHETEUR},
                     headers=ORIGINE)
    assert r.status_code == 503 and r.get_json()["error"] == "paiement_non_configure"


# ── 2. L'adresse ouverte est celle QUE NOUS AVONS LIÉE ────────────────────

def test_on_ouvre_le_compte_lie_et_non_l_adresse_tapee_au_paiement():
    """LA RÈGLE LA PLUS IMPORTANTE DU MODULE.

    Le formulaire de paiement laisse saisir n'importe quelle adresse — c'est
    normal, la facture n'est pas forcément à celle du compte. Si l'on ouvrait
    d'après elle, une faute de frappe encaisserait un paiement qui n'ouvre
    rien.
    """
    ev = _evenement(ACHETEUR, email_saisi=AUTRE)
    assert paiement.compte_a_ouvrir(ev) == ACHETEUR


def test_seul_un_paiement_ABOUTI_ouvre_quelque_chose():
    """Stripe émet des dizaines de sortes d'événements : n'en retenir qu'une
    est ce qui empêche une session simplement CRÉÉE d'ouvrir un accès."""
    assert paiement.compte_a_ouvrir(_evenement(ACHETEUR, paye=False)) is None
    assert paiement.compte_a_ouvrir(
        _evenement(ACHETEUR, sorte="checkout.session.created")) is None
    assert paiement.compte_a_ouvrir(_evenement(None)) is None


# ── 3. L'ouverture elle-même ──────────────────────────────────────────────

def test_un_paiement_ouvre_l_acces_et_le_trace(compte):
    assert auth.ouvrir_par_paiement(ACHETEUR, "https://x") is True
    assert auth.store.get(ACHETEUR)["approved"] is True


def test_le_rejeu_n_ouvre_ET_N_AVERTIT_qu_une_fois(compte):
    """STRIPE RÉÉMET jusqu'à acquittement. Sans cette garde, le courriel
    d'activation partirait plusieurs fois pour un seul paiement."""
    assert auth.ouvrir_par_paiement(ACHETEUR, "https://x") is True
    envoyes = len(compte)
    assert auth.ouvrir_par_paiement(ACHETEUR, "https://x") is False
    assert len(compte) == envoyes, "le rejeu a renvoyé des courriels"


def test_une_adresse_non_confirmee_n_est_pas_ouverte(compte):
    """Même règle que l'approbation manuelle, qui refuse déjà : « l'approuver
    maintenant ne lui ouvrirait rien »."""
    auth.store.update(ACHETEUR, email_verified=False)
    assert auth.ouvrir_par_paiement(ACHETEUR, "https://x") is False
    assert auth.store.get(ACHETEUR)["approved"] is False


def test_une_adresse_inconnue_ne_disparait_pas(compte):
    """Un paiement encaissé pour un compte introuvable doit laisser une trace,
    sans quoi il s'évapore."""
    assert auth.ouvrir_par_paiement("personne@inexistant.test", "https://x") is False


# ── 4. La caisse ne s'ouvre que pour un compte éligible ───────────────────

def test_payable_refuse_ce_qui_ne_doit_pas_payer(compte):
    assert auth.payable(ACHETEUR)
    auth.store.update(ACHETEUR, approved=True)
    assert auth.payable(ACHETEUR) is None, "un accès déjà ouvert n'a rien à acheter"
    auth.store.update(ACHETEUR, approved=False, email_verified=False)
    assert auth.payable(ACHETEUR) is None, "adresse non confirmée"
    assert auth.payable("personne@inexistant.test") is None


def test_la_caisse_ne_dit_pas_si_le_compte_existe(anonyme, configure, compte):
    """Trois messages distincts feraient de cette adresse un moyen de savoir
    qui a un compte ici, sans en avoir un soi-même."""
    auth.store.update(ACHETEUR, approved=True)
    a = anonyme.post("/api/paiement/checkout", json={"email": ACHETEUR},
                     headers=ORIGINE)
    b = anonyme.post("/api/paiement/checkout",
                     json={"email": "personne@inexistant.test"}, headers=ORIGINE)
    assert a.status_code == b.status_code == 400
    assert a.get_json() == b.get_json()


# ── 5. La notification : le seul chemin qui ouvre ─────────────────────────

def test_une_notification_non_signee_n_ouvre_rien(anonyme, configure, compte):
    r = anonyme.post("/api/stripe/webhook", data=b'{"type":"x"}')
    assert r.status_code == 400
    assert auth.store.get(ACHETEUR)["approved"] is False


def test_la_notification_passe_la_garde_d_origine(anonyme, configure):
    """STRIPE N'ENVOIE NI « Origin » NI « Referer », et ne peut pas porter
    notre en-tête maison. Sans l'exemption, chaque paiement serait rejeté en
    403 : l'argent passerait, aucun accès ne s'ouvrirait, et Stripe
    réessaierait trois jours."""
    r = anonyme.post("/api/stripe/webhook", data=b"{}")
    assert r.status_code != 403, "la garde d'origine bloque les paiements"


def test_une_notification_signee_ouvre_le_compte(anonyme, configure, compte,
                                                 monkeypatch):
    monkeypatch.setattr(paiement, "lire_evenement",
                        lambda charge, sig: _evenement(ACHETEUR))
    r = anonyme.post("/api/stripe/webhook", data=b"{}",
                     headers={"Stripe-Signature": "t=1,v1=x"})
    assert r.status_code == 200 and r.get_json()["traite"] is True
    assert auth.store.get(ACHETEUR)["approved"] is True


def test_un_evenement_inconnu_rend_200_sans_rien_ouvrir(anonyme, configure,
                                                        compte, monkeypatch):
    """Rendre 500 sur ce qu'on ne traite pas déclencherait des jours de
    réessais pour un cas qui ne s'arrangera pas tout seul."""
    monkeypatch.setattr(paiement, "lire_evenement",
                        lambda charge, sig: _evenement("inconnu@x.test"))
    r = anonyme.post("/api/stripe/webhook", data=b"{}",
                     headers={"Stripe-Signature": "t=1,v1=x"})
    assert r.status_code == 200 and r.get_json()["traite"] is False
    assert auth.store.get(ACHETEUR)["approved"] is False


# ── 6. La page ────────────────────────────────────────────────────────────

def test_la_page_ne_montre_le_bouton_que_si_le_paiement_est_configure():
    page = open(os.path.join(ICI, "connexion.html"), encoding="utf-8").read()
    assert 'id="payer" style="display:none' in page
    assert "/api/paiement/etat" in page
    assert "j.configure" in page


# ── 6. LE CHEMIN VERS LA CAISSE DOIT EXISTER, ET SON ABSENCE SE VOIR ──────
#
# CE QUI EST ARRIVÉ. Le parcours complet a été refait — inscription, courriel,
# notification, validation — sans jamais rencontrer la caisse. Deux causes,
# toutes deux silencieuses :
#
#   · le paiement n'était pas configuré, et AUCUN écran ne le disait. Côté
#     visiteur ce silence est voulu (un bouton qui mène à une erreur vaut moins
#     qu'un bouton absent) ; côté exploitant, c'était un piège ;
#   · l'offre ne vivait QUE sur /connexion?verifie=1, la page atteinte juste
#     après le clic du courriel. Onglet fermé, retour le lendemain : plus aucun
#     chemin vers la caisse, ni lien, ni page, ni mention.

def _script_connexion():
    return open(os.path.join(ICI, "connexion.html"), encoding="utf-8").read()


def _bloc_apres(source, debut):
    """Le corps de l'accolade ouverte juste après `debut`, par comptage réel.

    Lu par les ACCOLADES et non par les lignes : c'est la structure du script
    qui est en cause, et une règle qui chercherait un mot survivrait au
    déplacement du bloc."""
    i = source.index(debut) + len(debut)
    j = source.index("{", i)
    profondeur, k = 0, j
    while k < len(source):
        if source[k] == "{":
            profondeur += 1
        elif source[k] == "}":
            profondeur -= 1
            if profondeur == 0:
                return source[j:k + 1]
        k += 1
    raise AssertionError("accolade non refermée après " + debut)


def test_l_offre_de_paiement_ne_vit_plus_du_seul_instant_de_la_confirmation():
    page = _script_connexion()
    branche = _bloc_apres(page, "if(q.get('verifie'))")
    assert "/api/paiement/etat" not in branche, (
        "l'offre est de nouveau enfermée dans la branche ?verifie=1 : elle "
        "disparaît dès que l'onglet est fermé")
    # Et elle est bien posée AILLEURS dans le script — l'avoir sortie de la
    # branche ne vaut rien si on l'a simplement supprimée.
    assert "/api/paiement/etat" in page
    assert "j.configure" in page


def test_le_courriel_de_confirmation_ne_promet_que_ce_qui_existe(monkeypatch):
    """Annoncer une porte qui n'existe pas coûte plus cher qu'un délai
    d'attente annoncé franchement."""
    envois = []
    monkeypatch.setattr(auth, "send_email",
                        lambda to, nom, sujet, html: envois.append(html))
    u = {"email": "x@example.test", "name": "X", "verify_token": "jeton"}

    for nom in (paiement.CLE, paiement.CLE_WEBHOOK, paiement.CLE_PRIX):
        monkeypatch.delenv(nom, raising=False)
    auth._send_verify(u, base="https://exemple.test")
    assert "en réglant en ligne" not in envois[-1]

    for nom in (paiement.CLE, paiement.CLE_WEBHOOK, paiement.CLE_PRIX):
        monkeypatch.setenv(nom, "essai")
    auth._send_verify(u, base="https://exemple.test")
    assert "en réglant en ligne" in envois[-1]


def _absents_paiement(client):
    r = client.get("/api/admin/reglages")
    assert r.status_code == 200, r.status_code
    return [a for a in r.get_json()["absents"] if "STRIPE" in a["variable"]]


def test_les_reglages_nomment_les_variables_de_paiement_qui_manquent(admin, monkeypatch):
    for nom in (paiement.CLE, paiement.CLE_WEBHOOK, paiement.CLE_PRIX):
        monkeypatch.delenv(nom, raising=False)
    lignes = _absents_paiement(admin)
    assert len(lignes) == 1
    for nom in (paiement.CLE, paiement.CLE_WEBHOOK, paiement.CLE_PRIX):
        assert nom in lignes[0]["variable"]
    assert "éteint" in lignes[0]["consequence"]


def test_une_configuration_PARTIELLE_est_signalee_comme_telle(admin, monkeypatch):
    """LE CAS DANGEREUX N'EST PAS ZÉRO SUR TROIS, C'EST DEUX SUR TROIS : la
    clé est posée, on croit avoir configuré, et rien ne s'allume."""
    monkeypatch.setenv(paiement.CLE, "sk_essai")
    monkeypatch.setenv(paiement.CLE_WEBHOOK, "whsec_essai")
    monkeypatch.delenv(paiement.CLE_PRIX, raising=False)
    lignes = _absents_paiement(admin)
    assert len(lignes) == 1
    assert lignes[0]["variable"] == paiement.CLE_PRIX
    assert "2 valeur(s) sur 3 sont DÉJÀ posées" in lignes[0]["consequence"]


def test_rien_n_est_signale_quand_le_paiement_est_configure(admin, configure):
    assert _absents_paiement(admin) == []


def test_le_blueprint_declare_les_trois_variables():
    """render.yaml est la liste de ce dont le service a besoin. S'il se tait
    sur le paiement, personne ne sait qu'il faut poser quoi que ce soit."""
    y = open(os.path.join(ICI, "render.yaml"), encoding="utf-8").read()
    for nom in (paiement.CLE, paiement.CLE_WEBHOOK, paiement.CLE_PRIX):
        assert "key: " + nom in y, nom + " absent du blueprint"
    # L'adresse à déclarer chez Stripe y figure : c'est la seule information
    # que le tableau de bord de l'hébergeur ne donne pas.
    assert "/api/stripe/webhook" in y
    assert "checkout.session.completed" in y
