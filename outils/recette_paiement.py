#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Éprouve la chaîne de paiement de bout en bout, étape par étape.

CE QUE CE SCRIPT FAIT. Il rejoue le parcours réel d'un acheteur — compte
confirmé, refus des consentements manquants, ouverture de la caisse,
notification signée, ouverture de l'accès, rejeu, signatures invalides,
courriels, journal — et rend un verdict par étape. Il sort en erreur au premier
échec : une recette qui continue après un échec finit par se lire comme un
succès.

DEUX MODES, ET IL DIT LEQUEL. Quand les trois clés sont posées et que Stripe
répond, le dernier segment est RÉEL : le prix est lu chez Stripe, sa nature
vérifiée, et une vraie caisse de test est ouverte — le script imprime l'URL à
ouvrir dans un navigateur. Sinon il simule le SDK, et il l'annonce en tête ET
en pied : un mode simulé n'est pas une recette de la chaîne Stripe, et le
présenter comme telle serait le seul vrai échec de ce script.

DEUX GARDES, PARCE QU'UNE RECETTE QUI ABÎME LA PRODUCTION N'EN EST PAS UNE :

  · refus net sur une clé « sk_live_ » — on ne fait pas de recette en
    production, jamais ;
  · le compte de recette est EFFACÉ à la fin, et le magasin sur lequel le
    script a travaillé est nommé — PostgreSQL ou fichier local — pour qu'on
    sache ce qui a été touché.

Usage :  python3 outils/recette_paiement.py
         Code de sortie non nul dès qu'une étape échoue.
"""
import hashlib
import hmac
import json
import os
import sys
import time

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

ACHETEUR = "recette.paiement@example.test"
ORIGINE = {"Origin": "http://localhost"}

_ETAT = {"n": 0, "echecs": 0}


def _ligne(c="─"):
    return c * 78


def etape(titre):
    _ETAT["n"] += 1
    print()
    print(_ligne())
    print("  %2d. %s" % (_ETAT["n"], titre))
    print(_ligne())


def ok(quoi, detail=""):
    print("      ✓ %s%s" % (quoi, (" — " + detail) if detail else ""))


def echec(quoi, detail=""):
    _ETAT["echecs"] += 1
    print("      ✗ %s%s" % (quoi, (" — " + detail) if detail else ""))
    raise SystemExit(_fin(1))


def verifier(condition, quoi, detail=""):
    (ok if condition else echec)(quoi, detail)


# ── La caisse simulée ─────────────────────────────────────────────────────

class _CaisseSimulee:
    """Un faux SDK qui GARDE ce qu'on lui a passé.

    L'intérêt n'est pas de rendre une URL : c'est de pouvoir relire les
    arguments réellement transmis. Une caisse ouverte en `mode="subscription"`,
    ou sans `client_reference_id`, encaisserait sans rien ouvrir — et aucune
    règle ne le verrait si l'on ne regardait que la valeur de retour.
    """
    def __init__(self):
        self.appels = []
        sdk = self

        class _Session:
            @staticmethod
            def create(**kw):
                sdk.appels.append(kw)
                return type("S", (), {"url": "https://caisse.simulee.test/cs_test"})()

        class _Price:
            @staticmethod
            def retrieve(_id):
                return {"unit_amount": 49000, "currency": "eur"}

        self.checkout = type("C", (), {"Session": _Session})()
        self.Price = _Price
        self.Webhook = None      # posé plus bas : la vraie vérification


def _signer(evenement, secret, decalage_s=0):
    """Une charge réellement signée, au schéma de Stripe."""
    charge = json.dumps(evenement).encode()
    t = int(time.time()) + decalage_s
    sig = hmac.new(secret.encode(), b"%d.%s" % (t, charge), hashlib.sha256).hexdigest()
    return charge, "t=%d,v1=%s" % (t, sig)


def _evenement(reference, montant=49000):
    return {"id": "evt_recette", "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_recette", "payment_status": "paid",
                                "amount_total": montant, "currency": "eur",
                                "client_reference_id": reference,
                                "customer_details": {"email": "autre@example.test"}}}}


def _fin(code):
    print()
    print(_ligne("═"))
    if code == 0:
        print("  RECETTE PASSÉE — %d étapes." % _ETAT["n"])
    else:
        print("  RECETTE ÉCHOUÉE à l'étape %d." % _ETAT["n"])
    if _ETAT.get("simule"):
        print()
        print("  ⚠ LE SEGMENT STRIPE N'A PAS ÉTÉ JOUÉ. Le SDK a été simulé :")
        print("    tout ce qui précède l'appel à Stripe est éprouvé, l'appel")
        print("    lui-même ne l'est pas. Relancez ce script avec les trois")
        print("    clés sk_test_… depuis un réseau qui joint api.stripe.com")
        print("    pour ouvrir une vraie caisse et aller jusqu'au paiement.")
    print(_ligne("═"))
    return code


def main():
    print(_ligne("═"))
    print("  CHAÎNE DE PAIEMENT — recette de bout en bout")
    print(_ligne("═"))

    import paiement

    # ── Garde : jamais de recette en production ──────────────────────────
    cle = (os.environ.get(paiement.CLE) or "").strip()
    if cle.startswith("sk_live_"):
        print()
        print("  ⛔ CLÉ DE PRODUCTION DÉTECTÉE. Cette recette crée un compte,")
        print("     ouvre une caisse et ouvre un accès : elle ne s'exécute pas")
        print("     sur une clé « sk_live_ ». Posez une clé sk_test_… .")
        return 2

    reel = bool(paiement.configure())
    if reel:
        try:
            reel = paiement.tarif() is not None
        except Exception:
            reel = False
    _ETAT["simule"] = not reel
    print("  Mode : %s" % ("RÉEL — le dernier segment appelle Stripe" if reel
                           else "SIMULÉ — le SDK est remplacé, Stripe n'est pas appelé"))

    import auth
    print("  Magasin de comptes : %s" % type(auth.store).__name__)

    simulee = None
    if not reel:
        for nom in (paiement.CLE, paiement.CLE_WEBHOOK, paiement.CLE_PRIX):
            os.environ.setdefault(nom, "recette")
        os.environ[paiement.CLE_WEBHOOK] = "recette"
        simulee = _CaisseSimulee()
        vrai_stripe = paiement._stripe

        def _sdk():
            import stripe
            simulee.Webhook = stripe.Webhook      # la vérification reste RÉELLE
            return simulee
        paiement._stripe = _sdk
        paiement._TARIF = {"valeur": None, "lu_a": 0.0}

    import app as A
    A.app.config["TESTING"] = True
    client = A.app.test_client()
    courriels = []
    auth.send_email = lambda to, nom, sujet, html: courriels.append((to, sujet, html))
    auth.threading.Thread = lambda target, args=(), daemon=None: type(
        "T", (), {"start": lambda _s: target(*args)})()

    try:
        return _parcours(client, paiement, auth, courriels, simulee, reel)
    finally:
        try:
            auth.store.delete(ACHETEUR)
            print("\n  Compte de recette effacé : %s" % ACHETEUR)
        except Exception as e:
            print("\n  ⚠ compte de recette NON effacé (%s) : %s"
                  % (type(e).__name__, ACHETEUR))


def _parcours(client, paiement, auth, courriels, simulee, reel):
    etape("Configuration des trois variables")
    manque = [v for v in (paiement.CLE, paiement.CLE_WEBHOOK, paiement.CLE_PRIX)
              if not (os.environ.get(v) or "").strip()]
    verifier(not manque, "les trois valeurs sont posées",
             "sinon la caisse reste éteinte : %s" % manque)

    etape("Tarif, et nature du prix")
    t = paiement.tarif()
    verifier(t is not None, "le tarif est lu chez Stripe",
             "un prix illisible n'est pas un prix : rien ne s'affiche")
    verifier(not t["recurrent"], "le prix est à paiement unique",
             "un prix récurrent ferait échouer la caisse ouverte en mode « payment »")
    ok("montant", t["affichage"] or "non renseigné")

    etape("Compte de recette : confirmé, non approuvé")
    try:
        auth.store.delete(ACHETEUR)
    except Exception:
        pass
    auth.store.create({"email": ACHETEUR, "name": "Recette", "org": "Recette SARL",
                       "password_hash": "x", "email_verified": True,
                       "approved": False, "role": "user",
                       "verify_token": None, "verify_expire": None,
                       "approve_token": None, "approve_expire": None,
                       "reset_token": None, "reset_expire": None,
                       "created_at": 0, "last_login": None})
    u = auth.store.get(ACHETEUR)
    verifier(u and u["email_verified"] and not u["approved"],
             "adresse confirmée, accès fermé", "l'état exact où le paiement sert")

    etape("La page annonce le paiement")
    j = client.get("/api/paiement/etat").get_json()
    verifier(j["configure"] is True, "/api/paiement/etat dit « configuré »",
             "sinon le bloc de /acces reste caché")

    etape("Trois refus, un par consentement manquant")
    complet = {"email": ACHETEUR, "professionnel": True, "cgv": True,
               "renonciation": True}
    A_ = __import__("app")
    vrai_blocked = A_.guard.blocked
    A_.guard.blocked = lambda *a, **k: False
    for champ, motif in (("professionnel", "qualite_non_declaree"),
                         ("cgv", "conditions_non_acceptees"),
                         ("renonciation", "renonciation_absente")):
        charge = dict(complet)
        charge.pop(champ)
        r = client.post("/api/paiement/checkout", json=charge, headers=ORIGINE)
        verifier(r.status_code == 400 and r.get_json()["error"] == motif,
                 "sans « %s » : refus %s" % (champ, motif),
                 "reçu %s / %s" % (r.status_code, (r.get_json() or {}).get("error")))

    etape("La caisse s'ouvre avec les trois consentements")
    r = client.post("/api/paiement/checkout", json=complet, headers=ORIGINE)
    A_.guard.blocked = vrai_blocked
    verifier(r.status_code == 200 and r.get_json().get("url"),
             "une caisse est ouverte", (r.get_json() or {}).get("message", ""))
    if reel:
        print("      → OUVREZ CETTE ADRESSE ET PAYEZ AVEC 4242 4242 4242 4242 :")
        print("        %s" % r.get_json()["url"])
    else:
        kw = simulee.appels[-1]
        verifier(kw.get("mode") == "payment", "mode « payment »", str(kw.get("mode")))
        verifier(kw.get("client_reference_id") == ACHETEUR,
                 "le compte lié est celui de NOTRE serveur",
                 "et non l'adresse tapée au paiement")
        verifier(bool(kw.get("line_items")), "un article est passé", str(kw.get("line_items")))
        ok("retour", str(kw.get("success_url")))

    etape("La notification, réellement signée")
    secret = os.environ[paiement.CLE_WEBHOOK]
    charge, entete = _signer(_evenement(ACHETEUR), secret)
    ev = paiement.lire_evenement(charge, entete)
    verifier(ev is not None, "la signature est vérifiée et acceptée")
    verifier(paiement.compte_a_ouvrir(ev) == ACHETEUR,
             "le compte à ouvrir est celui du lien posé par nous",
             "et non « autre@example.test » saisi au paiement")

    etape("L'accès s'ouvre, par la voie tracée")
    avant = len(courriels)
    r = client.post("/api/stripe/webhook", data=charge,
                    headers={"Stripe-Signature": entete})
    verifier(r.status_code == 200 and r.get_json()["traite"] is True,
             "la notification est traitée")
    verifier(auth.store.get(ACHETEUR)["approved"] is True, "l'accès est ouvert")
    vers_acheteur = [h for to, _s, h in courriels[avant:] if to == ACHETEUR]
    verifier(vers_acheteur, "l'acheteur reçoit un courriel")
    conf = vers_acheteur[-1]
    for du, quoi in (("L221-28", "la renonciation est confirmée"),
                     (paiement.VERSION_CGV, "la version des conditions y figure"),
                     ("support durable", "le message se dit support durable")):
        verifier(du in conf, quoi)

    etape("Le rejeu n'ouvre rien de plus")
    avant = len(courriels)
    r = client.post("/api/stripe/webhook", data=charge,
                    headers={"Stripe-Signature": entete})
    verifier(r.status_code == 200, "Stripe reçoit toujours 200",
             "un 500 déclencherait trois jours de réessais")
    verifier(len(courriels) == avant, "aucun second courriel",
             "l'ouverture n'agit que si l'accès était fermé")

    etape("Une signature fausse, puis périmée, n'ouvrent rien")
    auth.store.update(ACHETEUR, approved=False)
    _, faux = _signer(_evenement(ACHETEUR), "pas_le_bon_secret")
    r = client.post("/api/stripe/webhook", data=charge,
                    headers={"Stripe-Signature": faux})
    verifier(r.status_code == 400 and not auth.store.get(ACHETEUR)["approved"],
             "signature d'un autre secret : refusée",
             "c'est le seul point qui empêche un tiers d'imiter Stripe")
    vieille_charge, vieux = _signer(_evenement(ACHETEUR), secret, decalage_s=-3600)
    r = client.post("/api/stripe/webhook", data=vieille_charge,
                    headers={"Stripe-Signature": vieux})
    verifier(r.status_code == 400 and not auth.store.get(ACHETEUR)["approved"],
             "signature périmée : refusée",
             "sans quoi une charge captée hier serait rejouable")

    etape("Le journal porte les trois consentements")
    # ON LIT PAR ACTION, ET ON VÉRIFIE LA CIBLE. `audit.lire` filtre sur
    # l'ACTEUR ; or la caisse s'appelle sans session — l'acteur est « anonyme »
    # et c'est la CIBLE qui porte l'adresse. Interroger par acteur ne rendait
    # rien, et c'est le script qui se trompait, pas le code.
    import audit
    for a in ("paiement.qualite", "paiement.conditions", "paiement.renonciation"):
        entrees = [e for e in audit.lire(limit=200, action=a)
                   if (e.get("cible") or "") == ACHETEUR]
        verifier(entrees, "trace « %s »" % a,
                 "un consentement non tracé n'est pas opposable")
    ouvertures = [e for e in audit.lire(limit=200, action="compte.approbation")
                  if (e.get("cible") or "") == ACHETEUR
                  and "paiement" in (e.get("detail") or "")]
    verifier(ouvertures, "l'ouverture est tracée « par paiement »",
             "le registre doit dire par quelle voie le compte est entré")

    return _fin(0)


if __name__ == "__main__":
    sys.exit(main())
