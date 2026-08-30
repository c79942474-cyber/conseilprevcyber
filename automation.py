"""Automatisation temps réel CONSEILPREV — planificateur et travaux de fond.

Un planificateur léger (thread démon) exécute des travaux périodiques, chacun
best-effort et isolé (une erreur n'arrête jamais la boucle) :

  - auto-surveillance : alerte email si un magasin bascule en mode mémoire
    (base injoignable) — et signale le retour à la normale ;
  - purge RGPD automatique des fiches clients expirées (art. 5.1.e) + alerte
    30 jours avant échéance ;
  - indexation RAG autonome : les documents en attente d'embeddings sont
    indexés côté serveur (plus besoin de garder la console ouverte) ;
  - veille CERT-FR : lecture périodique des flux officiels (alertes + avis),
    résumé par LLM (best-effort), publication sur /veille et alimentation
    automatique de la base de connaissance (thème « Veille ») ;
  - alertes critiques du cockpit : agrégées et envoyées par email avec
    anti-rafale (au plus un envoi par heure) ;
  - rapport hebdomadaire : synthèse d'activité générée chaque lundi matin,
    déposée dans l'historique des livrables et envoyée par email.

L'état persistant (dernier envoi, éléments de veille déjà vus…) est stocké
dans PostgreSQL si DATABASE_URL est défini, sinon en mémoire. Aucune donnée
personnelle n'est journalisée. Désactivation globale : AUTOMATION_DISABLED=1.
"""
import base64
import hashlib
import html as html_lib
import json
import logging
import os
import re
import lien_externe   # une adresse venue du dehors n'est pas une adresse
import reglages   # un réglage illisible ne doit pas arrêter le service
import threading
import veille_sources   # le catalogue des flux, et leur santé — voir le module
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

_log = logging.getLogger("automation")

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
# LES FLUX SONT UNE DONNÉE, PAS DU CODE. Ils vivent dans `veille_sources`, qui
# porte aussi le pays, le domaine et la nature de chaque émetteur — et l'état de
# ce que chaque passage a réellement rapporté.
VEILLE_MAX_ITEMS = reglages.entier("VEILLE_MAX_ITEMS", 2000, mini=50)

# ── CE QUE LES RÉSUMÉS COÛTENT, ET POURQUOI ILS SONT ÉTEINTS ──────────────
# Chaque nouvel élément déclenchait un appel au modèle. Sur deux flux CERT-FR
# c'était quelques appels par jour ; sur une trentaine de flux mondiaux, c'est
# l'actualité du monde entier prélevée sur le budget qui sert AUSSI à rédiger
# les livrables — et qui, épuisé, arrête les deux.
#
# Le repli existait déjà : le chapeau que la source publie elle-même, employé
# quand l'IA échoue. Sur un flux officiel, ce chapeau est écrit par le
# régulateur ; il n'a pas besoin d'être reformulé. On en fait donc le
# comportement NORMAL, et le résumé devient un choix explicite et borné.
VEILLE_RESUME = reglages.booleen("VEILLE_RESUME", False)
VEILLE_RESUME_MAX = reglages.entier("VEILLE_RESUME_MAX", 10, mini=0)

# ── CE QU'UN CATALOGUE QUI GROSSIT FAIT AU PLANIFICATEUR ──────────────────
# `_loop` appelle les travaux L'UN APRÈS L'AUTRE, dans un seul fil. Avec deux
# flux CERT-FR, la collecte durait quelques secondes et cela ne prêtait pas à
# conséquence. À trente-six flux, chacun pouvant attendre vingt secondes avant
# d'abandonner, un passage peut occuper DOUZE MINUTES — et pendant ce temps
# aucun autre travail ne tourne. Dont le rebranchement de la base, prévu toutes
# les trois minutes précisément pour qu'« une base revenue soit reprise sans
# que personne n'attende ».
#
# Une base qui tomberait pendant un passage lent resterait donc débranchée
# jusqu'à la fin de ce passage. La veille aurait dégradé la disponibilité du
# site — et rien ne l'aurait signalé.
#
# On borne donc le passage. Ce qui n'a pas été lu cette fois l'est au suivant :
# `veille_sources.ordre_de_passage()` commence par les sources les plus
# anciennement interrogées, ce qui interdit qu'une queue de catalogue soit
# systématiquement sautée.
VEILLE_BUDGET_S = reglages.entier("VEILLE_BUDGET_S", 180, mini=10)
# Texte complet des bulletins (base de connaissance exploitable) : on récupère
# le contenu intégral du bulletin CERT-FR (JSON officiel, sinon HTML) plutôt que
# le seul résumé RSS. Désactivable (VEILLE_FULLTEXT=0) ; nombre max de bulletins
# récupérés en entier par passage (borne le temps du job en arrière-plan).
_VEILLE_FULLTEXT = os.environ.get("VEILLE_FULLTEXT", "1").strip().lower() not in ("0", "false", "no")
_VEILLE_FULLTEXT_MAX = reglages.entier("VEILLE_FULLTEXT_MAX", 25, mini=0)
ALERT_COOLDOWN_S = reglages.entier("ALERTES_COOLDOWN_MIN", 60, mini=0) * 60


def _now_ms():
    return int(time.time() * 1000)


# ============================================================================
#  État clé/valeur persistant (PostgreSQL si possible, sinon mémoire)
# ============================================================================
class _State:
    def __init__(self, dsn):
        self._mem = {}
        self._pool = None
        if dsn:
            try:
                from psycopg_pool import ConnectionPool
                sep = "&" if "?" in dsn else "?"
                dsn = dsn + sep + "connect_timeout=5&client_encoding=UTF8"
                self._pool = ConnectionPool(dsn, min_size=1, max_size=1,
                                            kwargs={"autocommit": True}, timeout=8, open=True)
                with self._pool.connection() as conn:
                    conn.execute("""CREATE TABLE IF NOT EXISTS automation_state (
                        key TEXT PRIMARY KEY, value TEXT)""")
                    conn.execute("""CREATE TABLE IF NOT EXISTS veille_items (
                        guid TEXT PRIMARY KEY,
                        source TEXT, title TEXT, link TEXT,
                        published BIGINT, resume TEXT, created_at BIGINT)""")
            except Exception as exc:
                _log.warning("automation : état en mémoire (PostgreSQL injoignable : %s)", exc)
                self._pool = None

    def get(self, key, default=None):
        if self._pool:
            try:
                with self._pool.connection() as conn:
                    r = conn.execute("SELECT value FROM automation_state WHERE key=%s",
                                     (key,)).fetchone()
                return r[0] if r else default
            except Exception:
                pass
        return self._mem.get(key, default)

    def set(self, key, value):
        self._mem[key] = value
        if self._pool:
            try:
                with self._pool.connection() as conn:
                    conn.execute(
                        "INSERT INTO automation_state(key,value) VALUES(%s,%s) "
                        "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (key, str(value)))
            except Exception:
                pass

    # -- veille --
    def veille_add(self, item):
        if self._pool:
            try:
                with self._pool.connection() as conn:
                    conn.execute(
                        "INSERT INTO veille_items(guid,source,title,link,published,resume,created_at) "
                        "VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (guid) DO NOTHING",
                        (item["guid"], item["source"], item["title"], item["link"],
                         item["published"], item["resume"], _now_ms()))
                    conn.execute(
                        "DELETE FROM veille_items WHERE guid IN (SELECT guid FROM veille_items "
                        "ORDER BY published DESC OFFSET %s)", (VEILLE_MAX_ITEMS,))
                return
            except Exception:
                pass
        lst = self._mem.setdefault("_veille", [])
        if not any(x["guid"] == item["guid"] for x in lst):
            lst.append(dict(item, created_at=_now_ms()))
            lst.sort(key=lambda x: x["published"], reverse=True)
            del lst[VEILLE_MAX_ITEMS:]

    def veille_has(self, guid):
        if self._pool:
            try:
                with self._pool.connection() as conn:
                    return bool(conn.execute("SELECT 1 FROM veille_items WHERE guid=%s",
                                             (guid,)).fetchone())
            except Exception:
                pass
        return any(x["guid"] == guid for x in self._mem.get("_veille", []))

    def veille_list(self, limit=60):
        if self._pool:
            try:
                with self._pool.connection() as conn:
                    rows = conn.execute(
                        "SELECT guid,source,title,link,published,resume FROM veille_items "
                        "ORDER BY published DESC LIMIT %s", (limit,)).fetchall()
                keys = ("guid", "source", "title", "link", "published", "resume")
                return [dict(zip(keys, r)) for r in rows]
            except Exception:
                pass
        return [dict(x) for x in self._mem.get("_veille", [])[:limit]]


# ============================================================================
#  Contexte global du module (rempli par init)
# ============================================================================
_deps = {}
_state = None
_started = False
_crit_lock = threading.Lock()
_crit_buffer = []


def notify_admin(subject, html_body):
    """Email à l'administrateur via Brevo (best-effort). Renvoie True si envoyé."""
    api_key = os.environ.get("BREVO_API_KEY")
    to = _deps.get("notify_to")
    sender = _deps.get("sender")
    if not (api_key and to and sender):
        return False
    try:
        r = requests.post(
            BREVO_API_URL,
            json={"sender": sender, "to": [{"email": to, "name": "CONSEILPREV"}],
                  "subject": subject, "htmlContent": html_body},
            headers={"api-key": api_key, "accept": "application/json",
                     "content-type": "application/json"}, timeout=12)
        return r.status_code in (200, 201)
    except requests.RequestException:
        return False


# ============================================================================
#  Travaux périodiques
# ============================================================================
def job_surveillance():
    """Alerte si un magasin est en mode dégradé — et au retour à la normale.

    DEUX DÉFAUTS CORRIGÉS ICI, tous deux du même genre : l'alerte existait mais
    n'aidait pas.

    Elle ne se déclenchait qu'au CHANGEMENT d'état. Une base tombée le vendredi
    soir produisait un courriel, puis plus rien : le lundi, rien ne distinguait
    « c'est réparé » de « personne n'a regardé ». On rappelle donc l'état
    dégradé une fois par jour tant qu'il dure — assez pour ne pas être oublié,
    assez peu pour ne pas être filtré comme du bruit.

    Elle ne disait pas POURQUOI. « Vérifiez DATABASE_URL » quand la variable est
    correctement définie envoie chercher au mauvais endroit ; c'est exactement
    ce qu'a vécu l'administrateur. Le message porte maintenant la cause réelle
    remontée par le magasin, assainie de tout identifiant, plus le nombre
    d'échecs et la date du prochain essai.
    """
    parts, details = [], []
    for name in ("rag", "clients", "livrables"):
        store = _deps.get(name)
        if store is None or getattr(store, "persistent", True):
            continue
        parts.append(name)
        cause = ""
        try:
            etat = store.etat() if hasattr(store, "etat") else {}
            cause = etat.get("cause") or ""
            if etat.get("echecs_consecutifs"):
                cause += " (%d échec(s) consécutif(s))" % etat["echecs_consecutifs"]
        except Exception:
            cause = ""
        if not cause:
            cause = str(getattr(store, "_last_error", "") or "cause non remontée")
        details.append("<li><b>%s</b> — %s</li>" % (html_lib.escape(name),
                                                    html_lib.escape(cause[:300])))

    mode = ",".join(parts) or "ok"
    previous = _state.get("sante.mode", "ok")
    today = time.strftime("%Y-%m-%d")
    rappel_fait = _state.get("sante.rappel") == today

    if mode == previous and (mode == "ok" or rappel_fait):
        return
    _state.set("sante.mode", mode)

    if mode != "ok":
        _state.set("sante.rappel", today)
        notify_admin(
            "⚠️ Site en mode dégradé — base de données injoignable",
            "<p>Les magasins suivants fonctionnent <b>en repli</b> : <b>%s</b>.</p>"
            "<p><b>Cause remontée par le site :</b></p><ul>%s</ul>"
            "<p>La reconnexion est retentée automatiquement toutes les 3 minutes, "
            "avec un espacement croissant. Aucun redéploiement n'est nécessaire : "
            "dès que la base répond, le site s'y rebranche seul et reverse ce qui "
            "a été écrit entre-temps.</p>"
            "<p>Si l'état persiste, la cause ci-dessus indique où chercher — "
            "nombre de connexions, base suspendue, ou URL pointant vers une base "
            "qui n'existe plus.</p>" % (html_lib.escape(mode), "".join(details)))
    elif previous != "ok":
        _state.set("sante.rappel", "")
        notify_admin("✅ Site rétabli — persistance active",
                     "<p>Tous les magasins sont repassés en mode persistant, et "
                     "ce qui avait été écrit pendant la panne a été versé en base.</p>")


def job_rebranchement():
    """Rattrapage périodique des magasins tombés en mode dégradé.

    POURQUOI CETTE TÂCHE EXISTE. La console d'administration affiche « la
    connexion est retentée automatiquement ». C'était vrai à moitié : la
    reconnexion n'était tentée qu'À L'OCCASION d'une lecture, donc seulement si
    quelqu'un consultait la page — et sur la base documentaire, elle s'arrêtait
    définitivement dès qu'un document avait été chargé en mode dégradé. Aucune
    des six tâches planifiées ne s'en occupait. Un site qui n'est consulté par
    personne pendant la nuit restait dégradé au matin, base revenue ou non.

    Le rattrapage est ici INCONDITIONNEL et périodique : c'est ce qui rend la
    phrase affichée vraie. Il ne coûte rien quand tout va bien (un test
    d'attribut en mémoire, aucune requête) et ne martèle pas une base
    durablement absente, l'ordonnanceur l'espaçant déjà de plusieurs minutes.
    """
    for nom in ("rag", "clients", "livrables", "cockpit"):
        store = _deps.get(nom)
        if store is None or getattr(store, "persistent", True):
            continue
        try:
            # Chaque magasin expose sa propre reconnexion : on ne présume pas
            # de son mécanisme, on le déclenche.
            for methode in ("_maybe_reconnect", "reconnect", "reconnecter"):
                fn = getattr(store, methode, None)
                if callable(fn):
                    fn()
                    _log.info("rebranchement : essai déclenché sur « %s ».", nom)
                    break
        except Exception:
            _log.warning("rebranchement : échec de l'essai sur « %s ».", nom)

    # Les comptes ont leur propre magasin résilient, hors du registre ci-dessus.
    try:
        import auth as _auth
        if getattr(_auth.store, "mode", "") == "repli_fichier":
            _auth.store.reconnecter()
            _log.info("rebranchement : essai déclenché sur les comptes.")
    except Exception:
        pass


def job_purge_rgpd():
    """Purge quotidienne des données arrivées au terme de leur conservation.

    Deux traitements y passent : les fiches clients expirées et le journal
    d'audit au-delà de sa durée de conservation. Le journal s'élaguait jusqu'ici
    à l'écriture seule, ce qui borne le VOLUME mais pas la DURÉE : sans activité
    d'administration, des traces nominatives seraient restées en base
    indéfiniment. Une durée de conservation n'existe que si quelque chose la
    fait respecter sans qu'on y pense (art. 5.1.e).
    """
    today = time.strftime("%Y-%m-%d")
    if _state.get("rgpd.last_purge") == today:
        return
    _state.set("rgpd.last_purge", today)

    try:
        import audit
        efface = audit.purger()
        if efface:
            _log.info("purge RGPD : %d entrée(s) de journal au-delà de %d jours.",
                      efface, audit.RETENTION_JOURS)
    except Exception:
        _log.warning("purge RGPD : journal d'audit non purgé (base injoignable ?).")

    # LA REVUE DES COMPTES INACTIFS — déclarée au registre comme mesure de
    # limitation de conservation, et que rien n'exécutait : last_login était
    # écrit à chaque connexion et jamais lu. La revue devient automatique ;
    # la DÉCISION (suspendre, supprimer) reste humaine, depuis /admin/comptes.
    try:
        auth_mod = _deps.get("auth")
        if auth_mod is not None:
            seuil = _now_ms() - 24 * 30 * 24 * 3600 * 1000   # 24 mois
            dormants = [u for u in auth_mod.store.list_all()
                        if max(u.get("last_login") or 0,
                               u.get("created_at") or 0) < seuil]
            if dormants:
                lignes = "".join(
                    "<li>%s</li>" % html_lib.escape(u.get("email") or "?")
                    for u in dormants[:20])
                notify_admin(
                    "🗄️ RGPD — comptes inactifs depuis plus de 2 ans",
                    "<p><b>%d</b> compte(s) sans connexion depuis plus de "
                    "24 mois. Suspendez ou supprimez depuis /admin/comptes — "
                    "la revue est automatique, la décision reste humaine.</p>"
                    "<ul>%s</ul>" % (len(dormants), lignes))
    except Exception:
        _log.warning("purge RGPD : revue des comptes inactifs non faite.")

    clients = _deps.get("clients")
    if clients is None:
        return
    n = clients.purge_expired(actor="automate")
    soon = [c for c in clients.list()
            if 0 < c.get("expire_at", 0) - _now_ms() < 30 * 24 * 3600 * 1000]
    if n or soon:
        rows = "".join("<li>%s — expire le %s</li>" % (
            html_lib.escape(c["entreprise"]),
            time.strftime("%d/%m/%Y", time.localtime(c["expire_at"] / 1000))) for c in soon[:20])
        notify_admin(
            "🧹 RGPD — conservation des fiches clients",
            ("<p><b>%d</b> fiche(s) expirée(s) purgée(s) automatiquement "
             "(journal pseudonymisé conservé).</p>" % n if n else "")
            + ("<p>Fiches arrivant à échéance sous 30 jours :</p><ul>%s</ul>"
               "<p>Prolongez la conservation (si la relation a repris) ou laissez la "
               "purge automatique faire son travail.</p>" % rows if soon else ""))


def job_index_rag():
    """Indexation vectorielle autonome des documents en attente (côté serveur)."""
    rag = _deps.get("rag")
    if rag is None or not getattr(rag, "persistent", False):
        return
    try:
        pending = [d for d in rag.list_documents() if d.get("status") == "indexing"]
    except Exception:
        return
    budget = 30                                  # lots max par passage (≈300 chunks)
    for doc in pending:
        while budget > 0:
            budget -= 1
            try:
                out = rag.index_next(doc["id"])
            except Exception:
                return
            if out.get("done") or out.get("degraded"):
                break
        if budget <= 0:
            return


def _strip_html(text):
    return re.sub(r"<[^>]+>", " ", text or "").replace("&nbsp;", " ").strip()


def _sans_espace_de_noms(tag):
    """« {http://www.w3.org/2005/Atom}entry » → « entry ».

    Atom place TOUT dans un espace de noms ; RSS 2.0 n'en met aucun. Comparer
    les balises sans le préfixe est ce qui permet un seul lecteur pour les deux
    formats, sans écrire deux fois la même boucle.
    """
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _date_en_ms(texte):
    """Une date de flux en millisecondes, EN GARDANT SON FUSEAU.

    CE QUI ÉTAIT FAUX, ET QUI NE SE VOYAIT PAS SUR DEUX FLUX FRANÇAIS. La date
    était lue par `time.strptime(pub[:25], "%a, %d %b %Y %H:%M:%S")` : la
    troncature à vingt-cinq caractères COUPE le décalage horaire, et
    `time.mktime` interprète ensuite l'heure obtenue dans le fuseau du serveur.
    Tant que les sources étaient à Paris et le serveur en Europe, l'erreur était
    nulle. Sur des flux répartis du Japon à la Californie, elle atteint un jour
    entier — et une veille se lit par ordre de fraîcheur.

    Les deux formats du monde des flux, l'un et l'autre dans la bibliothèque
    standard : RFC 822 pour RSS, ISO 8601 pour Atom.
    """
    texte = (texte or "").strip()
    if not texte:
        return None
    try:                                    # RSS : « Tue, 26 Aug 2026 09:12:00 +0200 »
        d = parsedate_to_datetime(texte)
        if d is not None:
            if d.tzinfo is None:            # sans fuseau, la seule lecture honnête est UTC
                d = d.replace(tzinfo=timezone.utc)
            return int(d.timestamp() * 1000)
    except (TypeError, ValueError, OverflowError):
        pass
    try:                                    # Atom : « 2026-08-26T09:12:00Z »
        d = datetime.fromisoformat(texte.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return int(d.timestamp() * 1000)
    except (TypeError, ValueError, OverflowError):
        return None


def _parse_feed(source, xml_text):
    """Les éléments d'un flux RSS 2.0 OU Atom.

    POURQUOI ATOM N'ÉTAIT PAS LU, ET POURQUOI PERSONNE NE L'AURAIT VU. Le
    lecteur itérait sur `item` — la balise de RSS. Un flux Atom emploie `entry`,
    dans un espace de noms : la boucle ne trouvait rien, ne levait rien, et
    rendait une liste vide. Une source américaine entière pouvait donc manquer à
    la page sans qu'aucune erreur ne soit journalisée. C'est ce silence que
    `veille_sources` compte désormais.
    """
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for noeud in root.iter():
        balise = _sans_espace_de_noms(noeud.tag)
        if balise not in ("item", "entry"):
            continue
        champs = {}
        lien_atom = ""
        for enfant in noeud:
            nom = _sans_espace_de_noms(enfant.tag)
            if nom == "link" and not (enfant.text or "").strip():
                # Atom porte l'adresse en ATTRIBUT, pas en texte. La lire comme
                # du texte rendait une chaîne vide — donc un élément sans lien,
                # donc un élément écarté.
                rel = enfant.get("rel") or "alternate"
                if rel == "alternate" and enfant.get("href") and not lien_atom:
                    lien_atom = enfant.get("href")
                continue
            if nom not in champs and (enfant.text or "").strip():
                champs[nom] = enfant.text.strip()
        lien = champs.get("link") or lien_atom
        guid = champs.get("guid") or champs.get("id") or lien
        if not guid:
            continue
        publie = None
        for cle in ("pubDate", "published", "updated", "date"):
            if champs.get(cle):
                publie = _date_en_ms(champs[cle])
                if publie is not None:
                    break
        chapeau = (champs.get("description") or champs.get("summary")
                   or champs.get("content") or "")
        items.append({"guid": guid, "source": source,
                      "title": _strip_html(champs.get("title", ""))[:300],
                      "link": (lien or "")[:400],
                      "published": publie if publie is not None else _now_ms(),
                      "description": _strip_html(chapeau)[:2000]})
    return items


def _fetch_url(url, timeout=12):
    r = requests.get(url, timeout=timeout,
                     headers={"User-Agent": "conseilprevcyber-veille/1.0"})
    r.raise_for_status()
    return r.text


def _fetch_feed(url):
    return _fetch_url(url, timeout=20)


def _certfr_json_text(obj):
    """Extrait le texte lisible d'un bulletin CERT-FR au format JSON officiel.
    Cible le contenu intégral (champ « content ») ; à défaut, recompose à partir
    des champs utiles (résumé, systèmes affectés, CVE)."""
    if not isinstance(obj, dict):
        return ""
    content = obj.get("content")
    if isinstance(content, str) and len(content.strip()) > 60:
        return content.strip()
    bits = []
    for k in ("title", "summary", "description"):
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            bits.append(v.strip())
    for k, label in (("affected_systems", "Systèmes affectés"), ("cves", "CVE")):
        v = obj.get(k)
        if isinstance(v, list):
            names = []
            for x in v:
                if isinstance(x, str):
                    names.append(x)
                elif isinstance(x, dict):
                    names.append(x.get("name") or x.get("product")
                                 or x.get("cve") or x.get("description") or "")
            names = [n for n in names if n]
            if names:
                bits.append(label + " : " + ", ".join(names[:60]))
    return "\n\n".join(bits).strip()


_HTML_DROP = re.compile(r"(?is)<(script|style|nav|header|footer|aside|form|noscript)\b.*?</\1>")
_HTML_NL = re.compile(r"(?i)</(p|div|li|h[1-6]|tr|section|article)\s*>|<br\s*/?>")


def _html_to_text(html):
    """Convertit une page HTML en texte lisible (best-effort, sans dépendance) :
    retire scripts/nav/pied de page, privilégie le contenu principal, transforme
    les balises de bloc en sauts de ligne, décode les entités."""
    if not html:
        return ""
    html = _HTML_DROP.sub(" ", html)
    m = re.search(r"(?is)<(article|main)\b[^>]*>(.*?)</\1>", html)
    if m:
        html = m.group(2)
    html = _HTML_NL.sub("\n", html)
    text = re.sub(r"<[^>]+>", " ", html)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n[ \t]*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _fetch_bulletin_text(link, fetcher=None):
    """Texte complet d'un bulletin : JSON officiel de préférence, sinon page
    HTML. Best-effort — renvoie None si indisponible.

    L'ADRESSE VIENT DU FLUX, DONC DU DEHORS, et c'est le serveur qui va la
    chercher. Ce n'est pas le même risque qu'un lien affiché : une adresse
    pointant sur 169.254.169.254, sur la boucle locale ou sur un réseau privé
    ferait interroger l'infrastructure elle-même — métadonnées d'hébergeur,
    bases, pages d'administration — par un serveur qui, lui, a le droit. La
    requête part de l'intérieur : aucun pare-feu ne la voit passer.
    """
    if link and not lien_externe.joignable(link):
        _log.warning("veille : adresse de bulletin écartée (hôte interne ou "
                     "schéma refusé)")
        return None
    if not link or not _VEILLE_FULLTEXT:
        return None
    fetcher = fetcher or _fetch_url
    base = link.rstrip("/")
    try:                                   # 1) API JSON officielle : <lien>/json/
        txt = _certfr_json_text(json.loads(fetcher(base + "/json/")))
        if txt and len(txt) > 80:
            return txt[:40000]
    except Exception:
        pass
    try:                                   # 2) repli : page HTML du bulletin
        txt = _html_to_text(fetcher(link))
        if txt and len(txt) > 120:
            return txt[:40000]
    except Exception:
        pass
    return None


# La veille alimente-t-elle encore la base documentaire ?
#
# NON PAR DÉFAUT, ET C'EST UN CHOIX. Les bulletins CERT-FR ont leur propre
# magasin et leur propre page ; la base documentaire n'en recevait qu'une
# COPIE, pour la recherche. À raison d'une collecte toutes les six heures,
# cette copie a fini par occuper la majorité du fonds — trois documents listés
# sur cinq — pour répondre à des questions qu'on ne pose pas à une base
# d'ingénierie. La veille continue exactement comme avant sur sa page ; seule
# la copie s'arrête.
#
# LA VARIABLE EXISTE POUR POUVOIR REVENIR EN ARRIÈRE SANS TOUCHER AU CODE.
# Un jour où la recherche devra porter sur les bulletins, `VEILLE_RAG=1`
# suffira — et les documents reprendront leur place, avec leur thème.
VEILLE_VERS_RAG = (os.environ.get("VEILLE_RAG", "0").strip().lower()
                   in ("1", "oui", "on", "true", "vrai"))


def veille_refresh(fetcher=None):
    """Lit les flux, résume les nouveautés (LLM best-effort) et publie.

    N'ALIMENTE PLUS LA BASE DOCUMENTAIRE, sauf si `VEILLE_RAG` le redemande.
    Renvoie le nombre de nouveaux éléments."""
    feed_fetcher = fetcher or _fetch_feed
    # fetcher personnalisé (tests) réutilisé aussi pour les bulletins ; sinon le
    # récupérateur de bulletin utilise son défaut (timeout plus court).
    bulletin_fetcher = fetcher
    summarize = _deps.get("summarize") if VEILLE_RESUME else None
    rag = _deps.get("rag")
    new_count = 0
    fulltext_budget = _VEILLE_FULLTEXT_MAX          # borne les récupérations/passage
    # DEUX GARDES, DEUX RÔLES DISTINCTS — et c'est une mutation qui l'a
    # mis au jour : `summarize` mis à None commande le OUI/NON, ce budget
    # commande le COMBIEN. Écrire ici `... if VEILLE_RESUME else 0`
    # dupliquait le premier rôle : l'une des deux gardes devenait morte, et
    # plus aucune règle ne pouvait dire laquelle portait réellement.
    resume_budget = VEILLE_RESUME_MAX
    echeance = time.time() + VEILLE_BUDGET_S
    interrompu = 0
    for src in veille_sources.ordre_de_passage():
        if time.time() > echeance:
            # On ne tait pas l'interruption : un catalogue qui ne tient plus
            # dans son budget est une information d'exploitation, pas un détail.
            interrompu += 1
            continue
        source, url = src["cle"], src["url"]
        try:
            xml_text = feed_fetcher(url)
        except Exception as exc:
            _log.warning("veille : flux %s injoignable (%s)", source, exc)
            veille_sources.noter_echec(source, exc)
            continue
        lus = _parse_feed(source, xml_text)
        # ON NOTE CE QUE LE PASSAGE A DONNÉ, y compris zéro. Un flux qui répond
        # sans rien rendre — adresse valide pointant ailleurs, format inconnu du
        # lecteur — ne lève rien : sans ce comptage, il disparaîtrait de la page
        # sans que rien ne le signale.
        veille_sources.noter_succes(source, len(lus))
        for item in lus[:30]:
            if _state.veille_has(item["guid"]):
                continue
            resume = None
            # LE CHAPEAU DE LA SOURCE D'ABORD. Le résumé par modèle est un
            # choix explicite (VEILLE_RESUME), et il est BORNÉ par passage :
            # l'actualité mondiale ne doit pas pouvoir vider un budget qui sert
            # aussi à rédiger les livrables.
            if summarize and resume_budget > 0:
                resume_budget -= 1
                try:
                    resume = summarize(item["title"], item["description"])
                except Exception:
                    resume = None
            item["resume"] = (resume or item["description"][:500]).strip()
            _state.veille_add(item)
            new_count += 1
            # Alimente la base de connaissance (thème Veille, public) — seulement
            # si on l'a redemandé ; voir `VEILLE_VERS_RAG` ci-dessus.
            if rag is not None and VEILLE_VERS_RAG:
                try:
                    # Contenu intégral du bulletin (base exploitable) ; à défaut,
                    # le résumé. On borne le nombre de récupérations par passage.
                    body = item["resume"]
                    # LE CORPS N'EST REPRIS QUE DES SOURCES QUI L'AUTORISENT.
                    # C'est une limite de droit : reprendre le texte d'un
                    # article de presse n'est plus de l'agrégation. Le
                    # catalogue tranche, source par source.
                    if (fulltext_budget > 0
                            and veille_sources.texte_integral_permis(source)):
                        fulltext_budget -= 1
                        full = _fetch_bulletin_text(item["link"], bulletin_fetcher)
                        if full:
                            body = full
                    emetteur = (src["nom"] if src else source)
                    md = ("# %s\n\nSource : %s — %s\n\n%s\n" %
                          (item["title"], emetteur, item["link"], body))
                    slug = hashlib.sha256(item["guid"].encode()).hexdigest()[:10]
                    rag.ingest_bytes("veille-%s-%s.md" % (source, slug), md.encode("utf-8"),
                                     title="[%s] %s" % (emetteur, item["title"][:240]),
                                     theme="Veille", visibility="public")
                except Exception:
                    pass
    if interrompu:
        _log.warning("veille : passage interrompu au budget de %d s — %d source(s) "
                     "reportées au passage suivant (elles y passeront en tête)",
                     VEILLE_BUDGET_S, interrompu)
    if new_count:
        _state.set("veille.last_new", str(_now_ms()))
    return new_count


def veille_list(limit=60):
    return _state.veille_list(limit=limit) if _state else []


def job_veille():
    veille_refresh()


def record_critical(evt):
    """Appelé par l'ingestion cockpit pour chaque événement critique (anti-rafale)."""
    with _crit_lock:
        _crit_buffer.append({"asset": evt.get("asset", ""), "zone": evt.get("zone", ""),
                             "event": evt.get("event", ""), "ts": evt.get("ts")})
        del _crit_buffer[:-100]


def job_alertes():
    """Envoie au plus un email d'alerte agrégé par heure."""
    with _crit_lock:
        if not _crit_buffer:
            return
        last = float(_state.get("alertes.last_sent", "0") or 0)
        if time.time() - last < ALERT_COOLDOWN_S:
            return
        batch = list(_crit_buffer)
        _crit_buffer.clear()
    _state.set("alertes.last_sent", str(time.time()))
    rows = "".join("<li><b>%s</b> · zone %s — %s</li>" % (
        html_lib.escape(e["asset"] or "?"), html_lib.escape(e["zone"] or "?"),
        html_lib.escape(e["event"] or "")) for e in batch[:15])
    more = len(batch) - 15
    notify_admin(
        "🚨 Cockpit — %d événement(s) critique(s)" % len(batch),
        "<p>Événements critiques reçus par le cockpit :</p><ul>%s</ul>%s"
        "<p>Détail en temps réel : /demo · tendances : /tendances</p>"
        % (rows, ("<p>… et %d de plus.</p>" % more) if more > 0 else ""))


def _default_report(data):
    lines = ["# Rapport hebdomadaire — CONSEILPREV Cyber", "",
             "_Généré automatiquement — brouillon à relire._", ""]
    for section, values in data.items():
        lines.append("## " + section)
        if isinstance(values, dict):
            for k, v in values.items():
                lines.append("- **%s** : %s" % (k, v))
        else:
            lines.append(str(values))
        lines.append("")
    return "\n".join(lines)


def job_rapport_hebdo():
    """Chaque lundi ≥ 7 h : synthèse d'activité → historique livrables + email."""
    now = time.localtime()
    week = time.strftime("%G-W%V", now)
    if now.tm_wday != 0 or now.tm_hour < 7 or _state.get("rapport.week") == week:
        return
    _state.set("rapport.week", week)
    data = {}
    try:
        cockpit = _deps.get("cockpit")
        if cockpit is not None:
            t = cockpit.trends(days=7)
            total = sum(d.get("total", 0) for d in t.get("days", [])) if isinstance(t, dict) else 0
            data["Cockpit (7 jours)"] = {"événements": total}
    except Exception:
        pass
    for label, name, fn in (("Base de connaissance", "rag", "stats"),
                            ("Livrables", "livrables", "stats"),
                            ("Clients & prospects", "clients", "stats")):
        try:
            obj = _deps.get(name)
            if obj is not None:
                s = getattr(obj, fn)()
                data[label] = {k: v for k, v in s.items() if not isinstance(v, dict)}
        except Exception:
            pass
    data["Veille CERT-FR"] = {"éléments suivis": len(veille_list(limit=200))}

    md = None
    gen = _deps.get("generate_report")
    if gen:
        try:
            md = gen(data)
        except Exception:
            md = None
    md = md or _default_report(data)
    saved = None
    hist = _deps.get("livrables")
    if hist is not None:
        try:
            saved = hist.save({"type": "reporting-programme",
                               "label": "Rapport hebdomadaire automatique (%s)" % week,
                               "client": "CONSEILPREV — interne", "model": "automate",
                               "markdown": md, "sources": []})
        except Exception:
            saved = None
    notify_admin("📊 Rapport hebdomadaire — %s" % week,
                 "<p>Le rapport d'activité de la semaine est disponible dans "
                 "l'historique des livrables%s.</p>"
                 % (" (id %s)" % saved if saved else ""))


# ============================================================================
#  Planificateur
# ============================================================================
_JOBS = []


def _register_jobs():
    veille_hours = reglages.reel("VEILLE_INTERVAL_HOURS", 6, mini=0.1)
    _JOBS[:] = [
        # Toutes les 3 minutes : assez court pour qu'une base revenue soit
        # reprise sans que personne n'attende, assez espacé pour ne pas
        # marteler une base durablement absente. Premier essai à 45 s, après
        # que les magasins aient eu le temps de se construire.
        {"name": "rebranchement", "every": 180, "fn": job_rebranchement, "first": 45},
        {"name": "surveillance", "every": 3600, "fn": job_surveillance, "first": 90},
        {"name": "purge_rgpd", "every": 6 * 3600, "fn": job_purge_rgpd, "first": 300},
        {"name": "index_rag", "every": 120, "fn": job_index_rag, "first": 60},
        {"name": "veille", "every": veille_hours * 3600, "fn": job_veille, "first": 180},
        {"name": "alertes", "every": 300, "fn": job_alertes, "first": 120},
        {"name": "rapport_hebdo", "every": 3600, "fn": job_rapport_hebdo, "first": 600},
    ]
    now = time.time()
    for job in _JOBS:
        job["next"] = now + job["first"]


def _loop():
    while True:
        time.sleep(30)
        now = time.time()
        for job in _JOBS:
            if now < job["next"]:
                continue
            job["next"] = now + job["every"]
            try:
                job["fn"]()
            except Exception:
                _log.exception("automation : échec du travail %s", job["name"])


def init(sender=None, notify_to=None, rag=None, clients=None, livrables=None,
         cockpit=None, summarize=None, generate_report=None, dsn=None, start=True,
         auth=None):
    """Initialise le contexte et démarre le planificateur (sauf AUTOMATION_DISABLED=1)."""
    global _state, _started
    _deps.update(sender=sender, notify_to=notify_to, rag=rag, clients=clients,
                 livrables=livrables, cockpit=cockpit, summarize=summarize,
                 generate_report=generate_report, auth=auth)
    _state = _State(dsn)
    _register_jobs()
    if _started or not start or os.environ.get("AUTOMATION_DISABLED") == "1":
        return
    _started = True
    threading.Thread(target=_loop, daemon=True).start()
    _log.info("automation : planificateur démarré (%d travaux)", len(_JOBS))
