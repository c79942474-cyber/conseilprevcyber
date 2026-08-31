# -*- coding: utf-8 -*-
"""Le paiement qui ouvre un accès — et ce qu'il ne fait jamais.

CE QUE CE MODULE VEND. Un seul article : l'OUVERTURE D'UN COMPTE. La table des
comptes ne porte ni offre, ni palier, ni quota — l'accès y est binaire. Un
paiement n'a donc qu'une chose à faire, et c'est celle-là : poser `approved`.
Tout ce qui ressemblerait à un abonnement — échéance, renouvellement,
résiliation — demanderait d'abord de savoir FERMER un accès impayé, ce que ce
modèle ne sait pas faire. Le prétendre serait vendre ce qu'on ne tient pas.

LE MÊME COMPTE STRIPE QUE SENTINEL, DEUX CATALOGUES. Une facturation, un
tableau de bord, une TVA ; deux applications indépendantes, chacune avec son
identifiant de prix. Aucune donnée personnelle ne circule de l'une à l'autre.

DEUX RÈGLES REPRISES DE SENTINEL, PARCE QU'ELLES SONT JUSTES :

  · AUCUN ACCÈS N'EST OUVERT SANS UN ÉVÉNEMENT DE PAIEMENT DONT LA SIGNATURE
    EST VÉRIFIÉE. La route d'ouverture n'existe pas ; il n'y a que la
    notification signée. Un client ne peut donc pas se promouvoir en appelant
    une adresse.
  · L'IMPORT DE `stripe` EST DIFFÉRÉ ET LES POINTS D'ENTRÉE SONT INERTES tant
    que les clés manquent. Une configuration absente ne doit jamais empêcher le
    service de démarrer — c'est la leçon de l'incident des réglages, et elle
    vaut ici autant qu'ailleurs.

ET UNE RÈGLE QUI EST PROPRE À CE MODULE, LA PLUS IMPORTANTE :

  ON OUVRE L'ADRESSE QUE NOTRE SERVEUR A LIÉE, JAMAIS CELLE TAPÉE AU PAIEMENT.
  Le lien est posé à la création de la session, depuis le compte visé, et
  voyage dans `client_reference_id`. La notification lit CELA. Se fier à
  l'adresse saisie dans le formulaire Stripe ferait qu'une faute de frappe
  encaisse un paiement qui n'ouvre rien — et personne, ni le client ni vous, ne
  saurait pourquoi.
"""
import logging
import os
import threading
import time

VERSION = "2026-08-a"

# LA VERSION DES CONDITIONS ACCEPTÉES À L'ACHAT. Elle est conservée avec la
# renonciation au droit de rétractation : une renonciation dont on ne sait plus
# à quel texte elle se rapportait ne prouve rien. Un essai vérifie qu'elle est
# bien celle qu'affiche `cgv.html` — deux exemplaires dériveraient.
VERSION_CGV = "PROJET 2026-08-a"

_log = logging.getLogger("paiement")

# Les mêmes clés de COMPTE que Sentinel ; un identifiant de PRIX distinct.
CLE = "STRIPE_SECRET_KEY"
CLE_WEBHOOK = "STRIPE_WEBHOOK_SECRET"
CLE_PRIX = "STRIPE_PRICE_ACCES"


def _valeur(nom):
    return (os.environ.get(nom) or "").strip()


def configure():
    """Le paiement est-il utilisable ? Les trois valeurs, ou rien.

    On exige les TROIS ensemble : une clé sans identifiant de prix ouvrirait un
    bouton qui mène à une erreur, et un bouton qui échoue vaut moins qu'un
    bouton absent.
    """
    return bool(_valeur(CLE) and _valeur(CLE_WEBHOOK) and _valeur(CLE_PRIX))


def _stripe():
    """Le module, importé au dernier moment. None s'il manque.

    Différé : la bibliothèque n'a pas à être installée pour que le site
    démarre, et son absence se traite comme une absence de configuration —
    jamais comme une panne.
    """
    try:
        import stripe
    except ImportError:                                   # pragma: no cover
        _log.warning("paiement : la bibliothèque stripe n'est pas installée")
        return None
    stripe.api_key = _valeur(CLE)
    return stripe


# ── LE PRIX VIENT DE STRIPE, JAMAIS DE LA PAGE ────────────────────────────
# L'écrire dans le HTML serait plus simple et faux : le jour où il change dans
# Stripe, la page annonce un montant et la caisse en encaisse un autre. Le
# client découvre alors le désaccord au pire moment — la carte à la main. On lit
# donc la source ; et quand on ne peut pas la lire, on n'affiche AUCUN montant.
# Un prix qu'on ne peut pas prouver n'est pas un prix.
#
# MIS EN CACHE, parce qu'un aller-retour Stripe par affichage de page se paierait
# en latence chez le visiteur. Dix minutes : un tarif ne change pas trois fois
# par heure, et une modification est visible au pire au bout de ce délai.
TARIF_TTL_S = 600
_TARIF = {"valeur": None, "lu_a": 0.0}
_VERROU_TARIF = threading.Lock()


def _formater(centimes, devise):
    """« 490,00 € » — la virgule décimale et l'espace insécable du français.

    Les devises sans sous-unité (yen, won) ne prennent pas de décimales : les
    diviser par cent afficherait un montant cent fois trop petit.
    """
    sans_decimale = str(devise or "").lower() in ("jpy", "krw", "vnd", "clp", "isk")
    symbole = {"eur": "\u00a0€", "usd": "\u00a0$", "gbp": "\u00a0£"}.get(
        str(devise or "").lower(), "\u00a0" + str(devise or "").upper())
    if sans_decimale:
        return "%d%s" % (centimes, symbole)
    return ("%.2f" % (centimes / 100.0)).replace(".", ",") + symbole


def tarif():
    """Le tarif RÉEL de l'article vendu, lu chez Stripe. None si illisible.

    `recurrent` n'est pas une décoration : `session_paiement` ouvre la caisse en
    `mode="payment"`. Un prix Stripe RÉCURRENT la ferait échouer à chaque
    tentative, sans que rien ne l'explique — les visiteurs verraient « paiement
    momentanément indisponible » et personne ne saurait pourquoi. C'est la
    console d'administration qui le signale, à l'endroit où elle nomme déjà les
    variables manquantes.
    """
    if not configure():
        return None
    maintenant = time.time()
    with _VERROU_TARIF:
        if _TARIF["valeur"] and maintenant - _TARIF["lu_a"] < TARIF_TTL_S:
            return dict(_TARIF["valeur"])
    st = _stripe()
    if st is None:
        return None
    try:
        prix = st.Price.retrieve(_valeur(CLE_PRIX))
        centimes = prix.get("unit_amount")
        devise = prix.get("currency") or ""
        if centimes is None:
            # Un prix « à la carte » (unit_amount absent) n'a pas de montant à
            # afficher : on préfère ne rien dire plutôt qu'annoncer zéro.
            return None
        valeur = {"montant": int(centimes), "devise": devise,
                  "affichage": _formater(int(centimes), devise),
                  "recurrent": bool(prix.get("recurring"))}
    except Exception as exc:
        _log.warning("paiement : tarif non lu (%s)", type(exc).__name__)
        return None
    with _VERROU_TARIF:
        _TARIF["valeur"], _TARIF["lu_a"] = valeur, maintenant
    return dict(valeur)


def session_paiement(email, base):
    """Ouvre une caisse pour CE compte. Rend l'URL hébergée, ou None.

    `client_reference_id` porte l'adresse liée par NOUS. C'est la seule chose
    que la notification aura le droit de croire.
    """
    if not (configure() and email):
        return None
    st = _stripe()
    if st is None:
        return None
    try:
        s = st.checkout.Session.create(
            mode="payment",
            line_items=[{"price": _valeur(CLE_PRIX), "quantity": 1}],
            client_reference_id=email,
            # Pré-remplie par confort ; elle n'a AUCUNE valeur d'identité —
            # le client peut la changer, et c'est son droit : la facture n'est
            # pas forcément à la même adresse que le compte.
            customer_email=email,
            success_url="%s/connexion?paye=1" % base,
            cancel_url="%s/connexion?paye=0" % base,
        )
        return s.url
    except Exception as exc:
        _log.warning("paiement : caisse non ouverte (%s)", type(exc).__name__)
        return None


def lire_evenement(charge, signature):
    """L'événement, SI sa signature est valable. None sinon.

    Aucune tolérance : une charge non signée, mal signée, ou signée d'un autre
    secret ne rend rien. C'est le seul point qui empêche un tiers d'ouvrir des
    accès en imitant Stripe.
    """
    if not configure():
        return None
    st = _stripe()
    if st is None:
        return None
    try:
        return st.Webhook.construct_event(charge, signature,
                                          _valeur(CLE_WEBHOOK))
    except Exception:
        _log.warning("paiement : notification refusée (signature)")
        return None


def compte_a_ouvrir(evenement):
    """L'adresse à ouvrir, prise du lien posé par nous — et de lui seul.

    Rend None pour tout événement qui n'est pas un paiement abouti : Stripe en
    émet des dizaines de sortes, et n'en retenir qu'une est ce qui empêche
    qu'une session simplement CRÉÉE ouvre un accès.
    """
    if not isinstance(evenement, dict):
        evenement = getattr(evenement, "to_dict", lambda: {})()
    if evenement.get("type") != "checkout.session.completed":
        return None
    obj = ((evenement.get("data") or {}).get("object") or {})
    if obj.get("payment_status") != "paid":
        return None
    return (obj.get("client_reference_id") or "").strip().lower() or None


def glossaire():
    return {
        "ce qui est vendu": "l'ouverture d'un compte, une fois — ni abonnement, "
                            "ni renouvellement, ni résiliation",
        "client_reference_id": "l'adresse liée PAR NOTRE SERVEUR à la création "
                               "de la caisse ; la seule que la notification a "
                               "le droit de croire",
        "signature": "sans elle, rien n'est ouvert : c'est ce qui empêche un "
                     "tiers d'imiter Stripe",
        "configure": "les trois valeurs ensemble, ou rien — un bouton qui mène "
                     "à une erreur vaut moins qu'un bouton absent",
    }


def referentiel():
    return {"version": VERSION, "configure": configure(),
            "variables": [CLE, CLE_WEBHOOK, CLE_PRIX], "tarif": tarif()}
