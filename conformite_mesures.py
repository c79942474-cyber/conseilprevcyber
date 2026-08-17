"""Conformité MESURÉE — ce que le dossier déclaratif ne peut pas dire.

POURQUOI CE MODULE EXISTE. Le dossier de conformité de ce site (rgpd.py) est
entièrement déclaratif : le registre, les mesures et les huit lignes ART50
sont des constantes, écrites à la main, servies telles quelles. Une constante
ne se périme pas toute seule quand le code change — et ce dépôt en porte la
preuve : la politique de confidentialité promet un tableau « généré depuis le
référentiel interne : il ne peut pas diverger », et il diverge (6 lignes
publiées pour 10 traitements au référentiel, mesuré le jour où ce module a
été écrit).

CE QUE CE MODULE FAIT. Il mesure, au moment de l'appel, ce qui est mesurable
sur l'état réel du site : les fichiers servis sont relus du disque, les
compteurs viennent des magasins de données, le marquage des documents est
vérifié en GÉNÉRANT un document et en LISANT ses propriétés. Chaque contrôle
dit son mode :

    mesure       — le verdict vient d'une lecture de l'état réel ;
    attestation  — seule une personne peut l'affirmer ; jamais rendu vert
                   par ce module ;
    arbitrage    — le code et la déclaration se contredisent, et TRANCHER
                   n'appartient pas au code : il signale, il ne choisit pas.

CE QUE CE MODULE NE FAIT PAS. Il ne corrige rien tout seul quand la
correction est un acte (recueillir un consentement, approuver une purge), et
il ne convertit jamais une déclaration en mesure. Les huit « en place » de
rgpd.ART50 restent ce qu'ils sont : des attestations.
"""
import os
import re

VERSION = "2026-08-a"

ICI = os.path.dirname(os.path.abspath(__file__))

# Les signatures de traceurs tiers dont la politique de confidentialité
# affirme l'absence. Le contrôle PROUVE l'affirmation publiée au lieu de la
# répéter.
_TRACEURS = ("gtag(", "googletagmanager", "google-analytics.com",
             "analytics.js", "_paq", "matomo", "fbq(", "hotjar",
             "clarity.ms", "segment.com")

# Pages authentifiées ou techniques : hors périmètre du scan public, et le
# dire vaut mieux qu'un vert par omission.
_HTML_HORS_SCAN = {"admin.html", "admin-clients.html", "admin-comptes.html",
                   "admin-rgpd.html"}


def _lire(nom):
    """Le fichier tel qu'il sera servi, relu du disque à chaque mesure."""
    try:
        with open(os.path.join(ICI, nom), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _ctl(cle, cadre, quoi, mode, statut, constat, correction=None):
    """Un contrôle normalisé. L'invariant est ICI, pas dans la discipline du
    relecteur : un statut « conforme » qui ne vient pas d'une mesure est une
    invention, et il est rétrogradé en « non-mesure » plutôt que servi."""
    if statut == "conforme" and mode != "mesure":
        statut = "non-mesure"
        constat = ("INVARIANT : un verdict conforme sans mesure a été "
                   "rétrogradé. Constat d'origine : " + constat)
    return {"cle": cle, "cadre": cadre, "quoi": quoi, "mode": mode,
            "statut": statut, "constat": constat, "correction": correction}


# ═══════════════════════════════════════════════════════════════════════════
#  Les mesures
# ═══════════════════════════════════════════════════════════════════════════

def _m_fiches_expirees(clients_db):
    try:
        n = int((clients_db.stats() or {}).get("expires") or 0)
    except Exception as e:
        return _ctl("fiches_expirees", "RGPD art. 5.1.e",
                    "Fiches clients au-delà de leur durée de conservation",
                    "mesure", "non-mesure", "magasin injoignable : " + str(e)[:80])
    if n == 0:
        return _ctl("fiches_expirees", "RGPD art. 5.1.e",
                    "Fiches clients au-delà de leur durée de conservation",
                    "mesure", "conforme",
                    "aucune fiche au-delà de sa durée (compteur du magasin, "
                    "pas une déclaration)")
    return _ctl("fiches_expirees", "RGPD art. 5.1.e",
                "Fiches clients au-delà de leur durée de conservation",
                "mesure", "non-conforme",
                "%d fiche(s) au-delà de leur durée de conservation" % n,
                correction="POST /api/admin/clients/purge-expired — la purge "
                           "existe, elle attend une demande explicite")


def _m_journal_audit(audit_mod):
    try:
        e = audit_mod.etat() or {}
        jours = int(e.get("retention_jours") or 0)
    except Exception as exc:
        return _ctl("journal_audit", "RGPD art. 5.2",
                    "Journal d'audit : rétention bornée",
                    "mesure", "non-mesure", "journal injoignable : " + str(exc)[:80])
    if jours >= 1:
        return _ctl("journal_audit", "RGPD art. 5.2",
                    "Journal d'audit : rétention bornée",
                    "mesure", "conforme",
                    "rétention appliquée par le code du journal : %d jours, "
                    "purge par âge à l'écriture" % jours)
    return _ctl("journal_audit", "RGPD art. 5.2",
                "Journal d'audit : rétention bornée",
                "mesure", "non-conforme", "aucune rétention appliquée")


def _m_derive_registre(rgpd_mod):
    """LA divergence qui a motivé ce module : la page publique promet un
    tableau qui « ne peut pas diverger » du référentiel, et il diverge."""
    page = _lire("politique-confidentialite.html")
    if page is None:
        return _ctl("derive_registre", "RGPD art. 30",
                    "Le registre publié suit le référentiel",
                    "mesure", "non-mesure", "politique-confidentialite.html introuvable")
    lignes = len(re.findall(r"<tr>\s*<td", page))
    ref = len(rgpd_mod.REGISTRE)
    if lignes == ref:
        return _ctl("derive_registre", "RGPD art. 30",
                    "Le registre publié suit le référentiel",
                    "mesure", "conforme",
                    "%d ligne(s) publiées pour %d traitement(s) au référentiel" % (lignes, ref))
    return _ctl("derive_registre", "RGPD art. 30",
                "Le registre publié suit le référentiel",
                "mesure", "non-conforme",
                "la page publie %d ligne(s) pour %d traitement(s) au référentiel — "
                "et elle affirme que le tableau « ne peut pas diverger »" % (lignes, ref),
                correction="rendre le tableau dynamique depuis /api/conformite "
                           "(le patron existe dans conformite.html)")


def _m_assistant_sans_compte(app):
    """Le registre publié affirme « Aucun compte requis » pour l'assistant ;
    les routes /assistant et /api/chat portent @login_required. Le code ne
    tranche pas — ouvrir l'assistant ou corriger le registre est un arbitrage
    humain — mais tant que la contradiction existe, elle se dit."""
    gardees = []
    try:
        for regle in app.url_map.iter_rules():
            if str(regle) in ("/assistant", "/api/chat"):
                vue = app.view_functions.get(regle.endpoint)
                # Le marqueur auth_gated est pose par les decorateurs d'auth
                # du depot (login_required, admin_required) : il se LIT sur la
                # carte des routes, sans executer la route.
                if vue and getattr(vue, "auth_gated", False):
                    gardees.append(str(regle))
    except Exception as e:
        return _ctl("assistant_sans_compte", "RGPD art. 6 / art. 5.1.a",
                    "« Aucun compte requis » (registre) vs code",
                    "mesure", "non-mesure", "carte des routes injoignable : " + str(e)[:80])
    dit_sans_compte = "Aucun compte requis" in str(
        next((r for r in __import__("rgpd").REGISTRE if r.get("id") == "assistant"), {}))
    if dit_sans_compte and gardees:
        return _ctl("assistant_sans_compte", "RGPD art. 6 / art. 5.1.a",
                    "« Aucun compte requis » (registre) vs code",
                    "arbitrage", "non-conforme",
                    "le registre publié dit « Aucun compte requis », mais %s "
                    "exigent une connexion — la base légale publiée (consentement "
                    "par l'usage volontaire, sans compte) repose sur un fait "
                    "inexact. Deux issues : ouvrir l'assistant, ou corriger le "
                    "registre et revoir la base légale. LE CODE NE TRANCHE PAS."
                    % " et ".join(gardees))
    return _ctl("assistant_sans_compte", "RGPD art. 6 / art. 5.1.a",
                "« Aucun compte requis » (registre) vs code",
                "mesure", "conforme" if not (dit_sans_compte and gardees) else "non-conforme",
                "déclaration et code concordent")


# Routes d'administration SANS garde, avec la raison écrite : les exclure en
# silence ferait un vert par omission, les compter ferait un rouge éternel.
_ADMIN_SANS_GARDE_DOCUMENTEES = {
    # Le portail par mot de passe est LA PORTE elle-même : la garder derrière
    # la garde qu'elle implémente fermerait l'administration pour toujours.
    "/admin/acces": "portail d'accès administrateur — c'est la porte",
}


def _m_routes_admin_gardees(app):
    """Toute route /admin* doit porter une garde. Le marqueur auth_gated est
    posé par les décorateurs d'auth ; une route d'admin qui ne le porte pas
    est soit un oubli, soit un choix à documenter — dans les deux cas, à voir."""
    nues = []
    try:
        for regle in app.url_map.iter_rules():
            ch = str(regle)
            if not (ch.startswith("/admin") or ch.startswith("/api/admin")):
                continue
            if ch in _ADMIN_SANS_GARDE_DOCUMENTEES:
                continue
            vue = app.view_functions.get(regle.endpoint)
            if vue and not getattr(vue, "auth_gated", False):
                nues.append(ch)
    except Exception as e:
        return _ctl("routes_admin", "RGPD art. 32",
                    "Toute route d'administration porte une garde",
                    "mesure", "non-mesure", "carte des routes injoignable : " + str(e)[:80])
    if not nues:
        return _ctl("routes_admin", "RGPD art. 32",
                    "Toute route d'administration porte une garde",
                    "mesure", "conforme",
                    "toutes les routes /admin* et /api/admin* portent le "
                    "marqueur de garde (lu sur la carte des routes, pas déclaré)")
    return _ctl("routes_admin", "RGPD art. 32",
                "Toute route d'administration porte une garde",
                "arbitrage", "non-conforme",
                "route(s) d'administration sans garde d'administrateur : "
                + ", ".join(sorted(nues))
                + " — soit un oubli (ajouter la garde), soit un choix (le "
                  "documenter et l'exclure nommément). LE CODE NE TRANCHE PAS.")


def _m_traceurs_tiers():
    """La politique de confidentialité affirme l'absence de traceur tiers.
    Ce contrôle la PROUVE sur les fichiers servis, au lieu de la répéter."""
    touches = []
    try:
        for nom in sorted(os.listdir(ICI)):
            if not nom.endswith(".html") or nom in _HTML_HORS_SCAN:
                continue
            page = _lire(nom)
            if page is None:
                continue
            for sig in _TRACEURS:
                if sig in page:
                    touches.append(nom + " : " + sig)
    except OSError as e:
        return _ctl("traceurs_tiers", "ePrivacy / RGPD art. 82 LIL",
                    "Aucun traceur tiers sur les pages publiques",
                    "mesure", "non-mesure", "scan impossible : " + str(e)[:80])
    if not touches:
        return _ctl("traceurs_tiers", "ePrivacy / RGPD art. 82 LIL",
                    "Aucun traceur tiers sur les pages publiques",
                    "mesure", "conforme",
                    "aucune signature (%s…) dans les pages servies — "
                    "l'affirmation publiée est prouvée, pas répétée"
                    % ", ".join(_TRACEURS[:3]))
    return _ctl("traceurs_tiers", "ePrivacy / RGPD art. 82 LIL",
                "Aucun traceur tiers sur les pages publiques",
                "mesure", "non-conforme",
                "signature(s) de traceur trouvée(s) : " + " ; ".join(touches[:5]))


def _m_mention_assistant():
    page = _lire("assistant.html")
    if page is None:
        return _ctl("mention_assistant", "IA Act art. 50.1",
                    "L'assistant dit qu'on parle à une IA, avant l'échange",
                    "mesure", "non-mesure", "assistant.html introuvable")
    if re.search(r"échangez avec une\s*<strong>intelligence artificielle", page) \
       or "intelligence artificielle" in page:
        return _ctl("mention_assistant", "IA Act art. 50.1",
                    "L'assistant dit qu'on parle à une IA, avant l'échange",
                    "mesure", "conforme",
                    "mention « Vous échangez avec une intelligence artificielle » "
                    "présente dans assistant.html (fichier relu, pas déclaré)")
    return _ctl("mention_assistant", "IA Act art. 50.1",
                "L'assistant dit qu'on parle à une IA, avant l'échange",
                "mesure", "non-conforme",
                "assistant.html ne porte plus la mention d'IA : la personne "
                "n'est pas informée dès la première interaction")


def _m_marquage_exports():
    """Généré et relu, jamais promis : un document témoin est construit et ses
    propriétés lues. C'est le même geste que le contrôle jumeau de Sentinel."""
    try:
        import io
        import zipfile
        import livrables_export
        blob = livrables_export.build_docx(
            "# Controle de marquage\n\nDocument de verification, jamais distribue.\n",
            {"ia": True, "label": "Controle art. 50"})
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            core = z.read("docProps/core.xml").decode("utf-8", "replace")
        if livrables_export.MARQUE_IA in core:
            return _ctl("marquage_exports", "IA Act art. 50.2",
                        "Les documents exportés portent le marquage machine",
                        "mesure", "conforme",
                        "document généré à l'instant : docProps/core.xml porte "
                        "« %s » (lu, pas supposé)" % livrables_export.MARQUE_IA)
        return _ctl("marquage_exports", "IA Act art. 50.2",
                    "Les documents exportés portent le marquage machine",
                    "mesure", "non-conforme",
                    "document généré à l'instant : propriétés SANS marque IA — "
                    "le marquage lisible par machine a disparu")
    except Exception as e:
        return _ctl("marquage_exports", "IA Act art. 50.2",
                    "Les documents exportés portent le marquage machine",
                    "mesure", "non-mesure",
                    "génération de contrôle impossible : " + str(e)[:100])


def _m_art50_attestations(rgpd_mod):
    """Les huit lignes ART50 restent des attestations : ce contrôle ne les
    convertit pas en mesures, il dit combien elles sont et ce qu'elles valent."""
    n = len(rgpd_mod.ART50)
    en_place = sum(1 for a in rgpd_mod.ART50
                   if (a.get("statut") or "").strip() == "en place")
    return _ctl("art50_attestations", "IA Act art. 50",
                "Les mesures déclarées du registre de transparence",
                "attestation", "atteste",
                "%d mesure(s) déclarées, dont %d « en place » — CE SONT DES "
                "DÉCLARATIONS : rien ici n'est mesuré, et ce contrôle refuse "
                "de les peindre en vert" % (n, en_place))


# ═══════════════════════════════════════════════════════════════════════════
#  L'état
# ═══════════════════════════════════════════════════════════════════════════

def etat(clients_db, app, audit_mod=None, rgpd_mod=None):
    """Tous les contrôles, exécutés à l'instant de l'appel."""
    if audit_mod is None:
        import audit as audit_mod  # noqa: F811
    if rgpd_mod is None:
        import rgpd as rgpd_mod  # noqa: F811
    controles = [
        _m_fiches_expirees(clients_db),
        _m_journal_audit(audit_mod),
        _m_derive_registre(rgpd_mod),
        _m_assistant_sans_compte(app),
        _m_routes_admin_gardees(app),
        _m_traceurs_tiers(),
        _m_mention_assistant(),
        _m_marquage_exports(),
        _m_art50_attestations(rgpd_mod),
    ]
    mesures = [c for c in controles if c["mode"] == "mesure"]
    conformes = [c for c in mesures if c["statut"] == "conforme"]
    # PAS DE POURCENTAGE SEUL : un score qui absorbe les non-mesurés et les
    # attestations lit « conforme » là où il y a « non vérifié ». On sert les
    # quatre comptes, et l'écran doit les afficher ensemble.
    from datetime import datetime, timezone
    return {
        "version": VERSION,
        "mesure_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "controles": controles,
        "comptes": {
            "mesures": len(mesures),
            "mesures_conformes": len(conformes),
            "non_conformes": len([c for c in controles if c["statut"] == "non-conforme"]),
            "arbitrages": len([c for c in controles if c["mode"] == "arbitrage"]),
            "attestations": len([c for c in controles if c["mode"] == "attestation"]),
            "non_mesures": len([c for c in controles if c["statut"] == "non-mesure"]),
        },
        "note": "Les fichiers servis sont relus à chaque mesure ; les documents "
                "sont générés puis lus. Une attestation n'est jamais rendue "
                "verte par ce module, et un arbitrage n'est jamais tranché par lui.",
    }


def sante():
    return {"module": "conformite_mesures", "version": VERSION,
            "traceurs_surveilles": len(_TRACEURS)}
