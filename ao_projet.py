# -*- coding: utf-8 -*-
"""Le dossier marché d'un projet : ses pièces, ses relevés, sa fiche — conservés.

POURQUOI CE MODULE EXISTE, ET CE QU'IL NE FAIT PAS. Les trois routes de
remplissage ne conservent rien : tout vient de la requête et repart dans la
réponse. C'est sûr, et c'est épuisant — le même règlement de consultation est
redéposé, réanalysé et retapé à chaque session. Ici, le dossier s'attache au
PROJET : déposé une fois, il nourrit le remplissage tant que la consultation
est ouverte.

CE QUE LA CONSERVATION NE CHANGE PAS, ET C'EST LE POINT. Elle ne rend AUCUNE
déclaration sur l'honneur remplissable. Les six rubriques de déclaration
affirment des faits sur LE CANDIDAT — absence d'interdiction de soumissionner,
situation fiscale et sociale — ou ENGAGENT sur une offre. Les dix-sept relevés
du dossier marché portent tous, sans exception, sur LA CONSULTATION : acheteur,
objet, lots, délais, critères, pénalités. L'intersection des deux ensembles est
vide, et une règle le mesure. Conserver le règlement de consultation n'apprend
rien sur le casier judiciaire de qui le lit.

CE QUE LA CONSERVATION APPORTE VRAIMENT AUX DÉCLARATIONS : les PREUVES. Les
attestations qui soutiennent ce qui est affirmé (URSSAF, fiscale, KBIS,
assurances) vivent au dossier d'entreprise avec leur date de péremption. Une
affirmation se fait alors en connaissance de cause, preuve à l'appui, en un
geste daté — jamais par pré-remplissage. On automatise la preuve, jamais
l'affirmation.

TROIS INVARIANTS DE CONSERVATION :

  1. ON NE LIT PAS UN DOSSIER SANS AVOIR PASSÉ LE CONTRÔLE D'ACCÈS. L'API ne
     prend pas un identifiant de projet mais LE PROJET — l'enregistrement que
     `projets_dc.obtenir(compte, id)` rend, et qui vaut None sans accès. Un
     appelant ne peut donc pas atteindre un dossier en devinant un identifiant :
     il lui faudrait d'abord fabriquer un projet auquel il a accès.

  2. CHIFFRÉ AU REPOS, OU PAS STOCKÉ DU TOUT. Sans clé, sans bibliothèque, le
     dépôt est REFUSÉ avec sa raison. Il n'existe aucun repli en clair : un
     repli silencieux ferait exactement ce que le chiffrement devait empêcher,
     et personne ne le verrait.

  3. LA DURÉE DE CONSERVATION EST PORTÉE PAR LA LIGNE, ET LA PURGE L'APPLIQUE.
     L'échéance est calculée à l'écriture et stockée en clair à côté du coffre :
     la purge n'a donc rien à déchiffrer pour savoir quoi effacer. Une purge qui
     devrait ouvrir les coffres finirait par ne plus tourner.

CE QUI RESTE EN CLAIR, ET POURQUOI. L'identifiant du projet, les compteurs
(nombre de pièces, taille) et les trois dates. Rien de tout cela n'est une
donnée personnelle ni un secret d'affaires, et c'est ce qui permet à la purge
et à l'état de fonctionner sans jamais déchiffrer. Le propriétaire n'est PAS
recopié ici : il vit dans `projets_dc`, et deux copies d'une même autorisation
finissent par diverger — c'est la copie oubliée qui laisse passer.
"""
import hashlib
import json
import logging
import os
import threading
import time

_log = logging.getLogger("ao_projet")

VERSION = "2026-09-a"

# ── LA DURÉE DE CONSERVATION ──────────────────────────────────────────────
# Comptée depuis la DERNIÈRE activité, pas depuis le dépôt : un dossier qu'on
# rouvre est un dossier vivant. Douze mois couvrent l'instruction d'une
# consultation, ses questions-réponses et l'éventuel recours ; au-delà, les
# pièces sont celles d'un marché attribué et n'ont plus à être ici.
CONSERVATION_JOURS = 365
CONSERVATION_MOTIF = (
    "Durée de l'instruction d'une consultation, de ses questions-réponses et "
    "du délai de recours. Comptée depuis la dernière activité sur le projet.")

MAX_PIECES = 40
MAX_OCTETS_PIECE = 400_000
MAX_OCTETS_TOTAL = 4_000_000

# Le nom de la variable qui porte la clé. Une clé Fernet, base64url de 32
# octets — `cryptography.fernet.Fernet.generate_key()` en produit une.
VAR_CLE = "AO_PROJET_CLE"


class DossierError(Exception):
    def __init__(self, code, status=400, detail=""):
        super().__init__(code)
        self.code = code
        self.status = status
        self.detail = detail or ""


def _now_ms():
    return int(time.time() * 1000)


# ── LE CHIFFREMENT — ET SON ABSENCE, QUI EST UN ÉTAT NOMMÉ ────────────────

def _fernet():
    """La serrure, ou None avec la raison consignée.

    L'import est DIFFÉRÉ et la clé lue à chaque appel : le service démarre sans
    clé et le dit, plutôt que de refuser de démarrer. Ce qui ne démarre pas se
    remet en marche en enlevant la sécurité — on préfère un service qui tourne
    et qui refuse d'écrire.
    """
    cle = (os.environ.get(VAR_CLE) or "").strip()
    if not cle:
        return None, "cle_absente"
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return None, "bibliotheque_absente"
    try:
        return Fernet(cle.encode("ascii")), None
    except Exception:
        # Une clé mal formée est un incident de configuration, pas un secret :
        # on dit qu'elle est invalide, jamais ce qu'elle contient.
        return None, "cle_invalide"


MOTIFS = {
    "cle_absente": "La clé de chiffrement n'est pas configurée (%s). Rien "
                   "n'est conservé tant qu'elle manque." % VAR_CLE,
    "bibliotheque_absente": "La bibliothèque de chiffrement n'est pas "
                            "installée sur ce service.",
    "cle_invalide": "La clé de chiffrement configurée n'est pas une clé "
                    "valide. Elle doit être une clé Fernet (base64url, "
                    "32 octets).",
}


def chiffrement():
    """Ce que l'exploitation doit savoir, sans rien révéler de la clé."""
    f, motif = _fernet()
    return {"actif": f is not None,
            "motif": motif,
            "message": MOTIFS.get(motif, "") if motif else "",
            "variable": VAR_CLE}


def _coffrer(clair):
    f, motif = _fernet()
    if f is None:
        raise DossierError("chiffrement_indisponible", 503, MOTIFS.get(motif, ""))
    brut = json.dumps(clair, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return f.encrypt(brut), hashlib.sha256(brut).hexdigest(), len(brut)


def _ouvrir(coffre):
    f, motif = _fernet()
    if f is None:
        raise DossierError("chiffrement_indisponible", 503, MOTIFS.get(motif, ""))
    if isinstance(coffre, memoryview):
        coffre = coffre.tobytes()
    if isinstance(coffre, str):
        coffre = coffre.encode("ascii")
    try:
        return json.loads(f.decrypt(coffre).decode("utf-8"))
    except Exception:
        # Un coffre qu'on ne sait plus ouvrir (clé tournée, ligne abîmée) est
        # signalé, jamais silencieusement rendu vide : un dossier vide se
        # redéposerait par-dessus, et le dépôt d'origine serait perdu deux fois.
        raise DossierError("coffre_illisible", 409,
                           "Ce dossier ne s'ouvre pas avec la clé actuelle.")


# ── CE QUI ENTRE : DES PIÈCES, RIEN D'AUTRE ───────────────────────────────

def _piece(p):
    nom = str((p or {}).get("nom") or "").strip()[:200]
    texte = str((p or {}).get("texte") or "")
    if not nom:
        raise DossierError("piece_sans_nom", 400,
                           "Chaque pièce déposée doit porter son nom de fichier.")
    if len(texte.encode("utf-8")) > MAX_OCTETS_PIECE:
        raise DossierError("piece_trop_grande", 413,
                           "« %s » dépasse %d octets de texte."
                           % (nom, MAX_OCTETS_PIECE))
    return {"nom": nom, "texte": texte,
            "empreinte": hashlib.sha256(texte.encode("utf-8")).hexdigest(),
            "octets": len(texte.encode("utf-8"))}


def _valider(pieces):
    if not isinstance(pieces, (list, tuple)) or not pieces:
        raise DossierError("aucune_piece", 400,
                           "Un dossier marché contient au moins une pièce.")
    if len(pieces) > MAX_PIECES:
        raise DossierError("trop_de_pieces", 413,
                           "Un dossier porte au plus %d pièces." % MAX_PIECES)
    out, total = [], 0
    for p in pieces:
        q = _piece(p)
        total += q["octets"]
        if total > MAX_OCTETS_TOTAL:
            raise DossierError("dossier_trop_grand", 413,
                               "Le dossier dépasse %d octets de texte."
                               % MAX_OCTETS_TOTAL)
        out.append(q)
    return out


def _projet_id(projet):
    """L'identifiant, à condition qu'on nous ait donné un VRAI projet.

    C'est ici que l'invariant d'accès se tient : l'appelant doit avoir obtenu
    l'enregistrement auprès de `projets_dc`, qui rend None sans accès. Accepter
    une chaîne ferait de cet argument un identifiant devinable, et le contrôle
    d'accès dépendrait alors de la discipline de chaque appelant.
    """
    if not isinstance(projet, dict) or not projet.get("id"):
        raise DossierError("projet_requis", 403,
                           "Le dossier marché se lit à partir du projet "
                           "obtenu par le contrôle d'accès, jamais d'un "
                           "identifiant fourni.")
    return projet["id"]


def _assembler(meta, clair):
    """Les métadonnées en clair et le contenu du coffre, sans se recouvrir.

    `pieces` DÉSIGNAIT DEUX CHOSES : le compteur de la colonne et la liste du
    coffre. La liste écrasait le compteur au moment de fusionner, si bien que
    le même nom rendait un entier après un dépôt et une liste après une
    lecture. Le compteur s'appelle donc `nb_pieces`, et `pieces` est la liste,
    partout.
    """
    out = dict(meta)
    out["nb_pieces"] = out.pop("pieces", None)
    out.pop("coffre", None)
    out.update(clair)
    return out


# ============================================================================
#  Mémoire (repli non persistant)
# ============================================================================

class MemoryDossierStore:
    """Le même contrat que PostgreSQL, y compris le chiffrement.

    Chiffrer en mémoire n'apporte rien à la sécurité — le processus détient la
    clé. Ce qu'il apporte est bien plus utile : les deux magasins passent EXACTEMENT
    les mêmes règles. Un magasin de repli qui stockerait en clair laisserait la
    règle « c'est illisible en base » verte sans jamais l'éprouver.
    """

    def __init__(self):
        self._d = {}
        self._v = threading.Lock()

    def deposer(self, pid, pieces, analyse=None, fiche=None, affirmations=None):
        # LES AFFIRMATIONS SONT UN ARGUMENT, PAS UNE RELECTURE. La première
        # version les relisait dans le coffre stocké : `ecrire_affirmations`
        # posait alors les ANCIENNES par-dessus les nouvelles, et le geste
        # d'affirmation était perdu sans le moindre message.
        if affirmations is None:
            affirmations = self._affirmations(pid)
        coffre, empreinte, octets = _coffrer(
            {"pieces": pieces, "analyse": analyse, "fiche": fiche or {},
             "affirmations": affirmations})
        t = _now_ms()
        with self._v:
            ancien = self._d.get(pid)
            self._d[pid] = {
                "projet": pid, "coffre": coffre, "empreinte": empreinte,
                "pieces": len(pieces), "octets": octets,
                "cree_le": (ancien or {}).get("cree_le", t), "maj_le": t,
                "purge_le": t + CONSERVATION_JOURS * 86400 * 1000}
            return dict(self._d[pid])

    def _affirmations(self, pid):
        r = self._d.get(pid)
        if not r:
            return []
        try:
            return _ouvrir(r["coffre"]).get("affirmations") or []
        except DossierError:
            return []

    def lire(self, pid):
        with self._v:
            r = self._d.get(pid)
        if not r:
            return None
        return _assembler(r, _ouvrir(r["coffre"]))

    def ecrire_affirmations(self, pid, affirmations):
        with self._v:
            r = self._d.get(pid)
        if not r:
            return None
        clair = _ouvrir(r["coffre"])
        return self.deposer(pid, clair.get("pieces") or [],
                            clair.get("analyse"), clair.get("fiche"),
                            affirmations)

    def oublier(self, pid):
        with self._v:
            return self._d.pop(pid, None) is not None

    def purger(self, maintenant=None):
        t = maintenant if maintenant is not None else _now_ms()
        with self._v:
            morts = [k for k, v in self._d.items() if (v.get("purge_le") or 0) <= t]
            for k in morts:
                del self._d[k]
        return len(morts)

    def compter(self):
        with self._v:
            return {"dossiers": len(self._d),
                    "octets": sum(v.get("octets") or 0 for v in self._d.values())}


# ============================================================================
#  PostgreSQL
# ============================================================================

_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS ao_projet_dossier (
        projet TEXT PRIMARY KEY,
        coffre BYTEA NOT NULL,
        empreinte TEXT,
        pieces INT,
        octets INT,
        cree_le BIGINT,
        maj_le BIGINT,
        purge_le BIGINT)""",
    # La purge balaie par échéance : l'index est ce qui l'empêche de lire toute
    # la table à chaque passage, donc ce qui la garde assez peu coûteuse pour
    # tourner souvent.
    "CREATE INDEX IF NOT EXISTS ao_projet_dossier_purge_idx "
    "ON ao_projet_dossier (purge_le)",
]

_COLS = "projet,empreinte,pieces,octets,cree_le,maj_le,purge_le"


class PostgresDossierStore:
    def __init__(self, dsn):
        import psycopg
        self._psycopg = psycopg
        self._dsn = dsn
        with self._conn() as c:
            for s in _SCHEMA:
                c.execute(s)

    def _conn(self):
        return self._psycopg.connect(self._dsn, autocommit=True)

    def deposer(self, pid, pieces, analyse=None, fiche=None, affirmations=None):
        if affirmations is None:
            actuel = self.lire(pid)
            affirmations = (actuel or {}).get("affirmations") or []
        coffre, empreinte, octets = _coffrer(
            {"pieces": pieces, "analyse": analyse, "fiche": fiche or {},
             "affirmations": affirmations})
        t = _now_ms()
        purge = t + CONSERVATION_JOURS * 86400 * 1000
        with self._conn() as c:
            c.execute(
                "INSERT INTO ao_projet_dossier "
                "(projet,coffre,empreinte,pieces,octets,cree_le,maj_le,purge_le) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (projet) DO UPDATE SET "
                "coffre=EXCLUDED.coffre, empreinte=EXCLUDED.empreinte, "
                "pieces=EXCLUDED.pieces, octets=EXCLUDED.octets, "
                "maj_le=EXCLUDED.maj_le, purge_le=EXCLUDED.purge_le",
                (pid, coffre, empreinte, len(pieces), octets, t, t, purge))
            r = c.execute("SELECT " + _COLS + " FROM ao_projet_dossier "
                          "WHERE projet=%s", (pid,)).fetchone()
        return dict(zip(_COLS.split(","), r)) if r else None

    def lire(self, pid):
        with self._conn() as c:
            r = c.execute("SELECT " + _COLS + ",coffre FROM ao_projet_dossier "
                          "WHERE projet=%s", (pid,)).fetchone()
        if not r:
            return None
        return _assembler(dict(zip(_COLS.split(","), r[:-1])), _ouvrir(r[-1]))

    def ecrire_affirmations(self, pid, affirmations):
        actuel = self.lire(pid)
        if not actuel:
            return None
        return self._reposer(pid, actuel.get("pieces") or [],
                             actuel.get("analyse"), actuel.get("fiche"),
                             affirmations)

    def _reposer(self, pid, pieces, analyse, fiche, affirmations):
        coffre, empreinte, octets = _coffrer(
            {"pieces": pieces, "analyse": analyse, "fiche": fiche or {},
             "affirmations": affirmations})
        t = _now_ms()
        with self._conn() as c:
            c.execute("UPDATE ao_projet_dossier SET coffre=%s, empreinte=%s, "
                      "octets=%s, maj_le=%s, purge_le=%s WHERE projet=%s",
                      (coffre, empreinte, octets, t,
                       t + CONSERVATION_JOURS * 86400 * 1000, pid))
        return self.lire(pid)

    def oublier(self, pid):
        with self._conn() as c:
            n = c.execute("DELETE FROM ao_projet_dossier WHERE projet=%s",
                          (pid,)).rowcount
        return bool(n)

    def purger(self, maintenant=None):
        t = maintenant if maintenant is not None else _now_ms()
        with self._conn() as c:
            return c.execute("DELETE FROM ao_projet_dossier WHERE purge_le<=%s",
                             (t,)).rowcount

    def compter(self):
        with self._conn() as c:
            r = c.execute("SELECT COUNT(*), COALESCE(SUM(octets),0) "
                          "FROM ao_projet_dossier").fetchone()
        return {"dossiers": r[0], "octets": int(r[1] or 0)}


def make_dossier_store():
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        try:
            return PostgresDossierStore(dsn)
        except Exception:
            _log.exception("dossier marché : bascule en mémoire")
    return MemoryDossierStore()


# ============================================================================
#  L'API publique — celle qui tient les invariants
# ============================================================================

_STORE = None
_VERROU = threading.Lock()


def store():
    global _STORE
    if _STORE is None:
        with _VERROU:
            if _STORE is None:
                _STORE = make_dossier_store()
    return _STORE


def _fusionner(anciennes, nouvelles):
    """Le dossier existant complété par ce qui arrive.

    UN DOSSIER DE CONSULTATION NE SE DÉPOSE PAS D'UN SEUL COUP, et c'est la
    réalité du geste : on reçoit le règlement et le CCAP, on demande le CCTP,
    l'acheteur publie un rectificatif trois jours plus tard. Remplacer à chaque
    dépôt effaçait les pièces précédentes — mesuré : déposer une pièce de plus
    n'en laissait qu'une. Charger « une par une » était donc destructeur, et
    silencieusement.

    LE NOM FAIT L'IDENTITÉ. Un CCAP redéposé REMPLACE l'ancien : c'est le geste
    du rectificatif, et garder les deux ferait relever deux fois des clauses
    contradictoires. Un nom nouveau s'ajoute. L'ORDRE D'ARRIVÉE est conservé,
    la version reprenant la place de celle qu'elle remplace : un dossier qui se
    réordonnerait à chaque dépôt se comparerait mal à celui de la veille.
    """
    par_nom = {p["nom"]: i for i, p in enumerate(anciennes)}
    out = list(anciennes)
    for p in nouvelles:
        i = par_nom.get(p["nom"])
        if i is None:
            par_nom[p["nom"]] = len(out)
            out.append(p)
        else:
            out[i] = p
    return out


def deposer(projet, pieces, fiche=None, remplacer=False):
    """Ajouter des pièces au dossier marché d'un projet, et le relever.

    LE DÉPÔT AJOUTE, IL NE REMPLACE PAS — `remplacer=True` pour l'exiger. Le
    geste qui vide reste `oublier()`, qui le dit et qui efface tout : deux
    façons de perdre un dossier, dont une par accident, en faisaient une de
    trop.

    LE RELEVÉ SE FAIT ICI, PAS À LA LECTURE, et il porte sur le dossier ENTIER
    — pas sur les seules pièces qui arrivent. C'est le dossier entier qui dit
    ce qui MANQUE, et un relevé fait sur le dernier fichier déposé annoncerait
    neuf pièces manquantes à chaque ajout. Analyser à chaque lecture, à
    l'inverse, ferait varier le résultat quand les motifs évoluent : deux
    lectures du même dossier ne diraient plus la même chose. On relève au
    dépôt, et la version du releveur est conservée avec le résultat.
    """
    pid = _projet_id(projet)
    arrivees = _valider(pieces)
    anciennes = [] if remplacer else ((lire(projet) or {}).get("pieces") or [])
    entier = _fusionner(anciennes, arrivees)
    # LES BORNES PORTENT SUR L'ENSEMBLE, et le refus NOMME ce qui déborde :
    # « le dossier dépasse » sans dire de combien ni à cause de quoi laisse
    # supprimer au hasard.
    if len(entier) > MAX_PIECES:
        raise DossierError("trop_de_pieces", 413,
                           "Le dossier porterait %d pièces ; il en admet %d. "
                           "Retirez-en avant d'ajouter."
                           % (len(entier), MAX_PIECES))
    total = sum(p["octets"] for p in entier)
    if total > MAX_OCTETS_TOTAL:
        raise DossierError("dossier_trop_grand", 413,
                           "Le dossier porterait %d octets de texte ; il en "
                           "admet %d." % (total, MAX_OCTETS_TOTAL))
    import ao_dc
    analyse = ao_dc.analyser([{"nom": p["nom"], "texte": p["texte"]}
                              for p in entier])
    analyse["version_ao_dc"] = ao_dc.VERSION
    return store().deposer(pid, entier, analyse, fiche or {})


def retirer(projet, nom):
    """Retirer UNE pièce du dossier, et refaire le relevé sur ce qui reste.

    POURQUOI CE GESTE EXISTE À CÔTÉ DE `oublier`. Une pièce déposée par erreur
    — le mauvais lot, un doublon — n'a pas à coûter tout le dossier. Et sans
    lui, la seule façon de corriger serait de tout effacer puis de tout
    redéposer, c'est-à-dire de perdre au passage ce qu'on ne retrouverait pas.

    RENVOIE None SI LA PIÈCE N'Y ÉTAIT PAS : un retrait qui réussit sans rien
    retirer ferait croire à une correction faite.
    """
    d = lire(projet) or {}
    restantes = [p for p in (d.get("pieces") or [])
                 if p["nom"] != str(nom or "").strip()]
    if len(restantes) == len(d.get("pieces") or []):
        return None
    if not restantes:
        oublier(projet)
        return {"pieces": [], "vide": True}
    return deposer(projet, [{"nom": p["nom"], "texte": p["texte"]}
                            for p in restantes], d.get("fiche"),
                   remplacer=True)


def lire(projet):
    """Le dossier conservé d'un projet, ou None. L'accès est déjà tranché."""
    return store().lire(_projet_id(projet))


def oublier(projet):
    """L'effacement à la demande. Il efface, il n'archive pas."""
    return store().oublier(_projet_id(projet))


def purger(maintenant=None):
    """Effacer ce qui a dépassé son échéance. Rend le nombre de lignes parties."""
    return store().purger(maintenant)


def etat():
    """Ce que l'exploitation doit voir, sans ouvrir un seul coffre."""
    c = store().compter()
    return {"version": VERSION,
            "chiffrement": chiffrement(),
            "conservation_jours": CONSERVATION_JOURS,
            "conservation_motif": CONSERVATION_MOTIF,
            "magasin": store().__class__.__name__,
            "dossiers": c["dossiers"],
            "octets": c["octets"],
            "limites": {"pieces": MAX_PIECES,
                        "octets_piece": MAX_OCTETS_PIECE,
                        "octets_total": MAX_OCTETS_TOTAL}}


# ============================================================================
#  L'AFFIRMATION — un geste humain, daté, preuve sous les yeux
# ============================================================================
#
# CE QU'ELLE N'EST PAS, ET C'EST TOUT L'ENJEU. Une affirmation n'est PAS une
# valeur. Elle n'entre jamais dans le dictionnaire que `ao_formulaires` écrit
# dans le fichier : les six rubriques de déclaration sortent de `ao_dc.remplir()`
# au statut `a_declarer`, sans valeur, affirmées ou non. Consigner qu'une
# personne a affirmé quelque chose et REMPLIR la case à sa place sont deux
# gestes opposés, et c'est le second que ce module refuse.
#
# CE QU'ELLE EST : la trace de qui a affirmé quoi, quand, sur QUEL TEXTE, avec
# quelles preuves valides ce jour-là. Elle sert à retrouver, six mois plus
# tard, ce qui a été assumé — pas à l'assumer d'avance.

AFFIRMATION_MAX = 40


def _empreinte_texte(t):
    return hashlib.sha256(" ".join(str(t or "").split()).encode("utf-8")).hexdigest()


def affirmer(projet, cle, par, texte_vu, reconnait_sans_preuve=False,
             aujourdhui=None):
    """Consigner qu'une personne assume une déclaration, ou refuser en le disant.

    QUATRE REFUS, ET AUCUN N'EST DÉCORATIF :

      · `declaration_inconnue` — la clé ne désigne aucune des six ;
      · `texte_divergent` — le texte affiché à la personne n'est pas celui que
        la pièce contient. Elle a lu autre chose que ce qu'elle affirme, ce qui
        est exactement le mal qu'on veut empêcher ;
      · `preuve_incomplete` — une attestation attendue est absente ou périmée.
        Les manquantes sont nommées, jamais résumées en « incomplet » ;
      · `reconnaissance_requise` — la déclaration n'attend AUCUNE preuve de
        nous (engagement contractuel, ou déclaration du sous-traitant). Une
        attente vide passerait sinon pour « tout est là », et l'affirmation la
        plus risquée serait justement la seule à ne rien exiger.
    """
    pid = _projet_id(projet)
    import ao_dc
    import dossier_entreprise
    par_cle = {d["cle"]: d for d in ao_dc.declarations()}
    d = par_cle.get(cle)
    if d is None:
        raise DossierError("declaration_inconnue", 400,
                           "Déclarations connues : %s."
                           % ", ".join(sorted(par_cle)))
    qui = str(par or "").strip()[:200]
    if not qui:
        raise DossierError("affirmant_manquant", 400,
                           "Une affirmation porte le nom de qui l'assume.")
    if _empreinte_texte(texte_vu) != _empreinte_texte(d["texte"]):
        raise DossierError("texte_divergent", 409,
                           "Le texte affirmé n'est pas celui que « %s » "
                           "contient." % d["piece_nom"])

    couv = dossier_entreprise.couverture(cle, aujourdhui)
    if couv["etat"] == "incomplete":
        manque = ", ".join("%s (%s)" % (m["nom"], m["etat"])
                           for m in couv["manquantes"])
        raise DossierError("preuve_incomplete", 409,
                           "Il manque : %s." % (manque or "une preuve"))
    if couv["etat"] == "sans_preuve_interne" and not reconnait_sans_preuve:
        raise DossierError("reconnaissance_requise", 409, couv["motif"])

    trace = {"cle": cle, "piece": d["piece"], "par": qui, "le": _now_ms(),
             "engage": d["engage"], "engage_nom": d["engage_nom"],
             "texte_empreinte": _empreinte_texte(d["texte"]),
             "couverture": couv["etat"],
             "preuves": list(couv["valides"]),
             "reconnaissance": bool(reconnait_sans_preuve
                                    and couv["etat"] == "sans_preuve_interne"),
             "jour_preuve": couv["jour"]}
    anciennes = [a for a in (affirmations(projet) or []) if a.get("cle") != cle]
    nouvelles = (anciennes + [trace])[-AFFIRMATION_MAX:]
    store().ecrire_affirmations(pid, nouvelles)
    return trace


def affirmations(projet):
    d = lire(projet)
    return (d or {}).get("affirmations") or []


def etat_affirmations(projet, aujourdhui=None):
    """Où en sont les six déclarations — et ce qui a VIEILLI depuis.

    UNE AFFIRMATION N'EST PAS ACQUISE UNE FOIS POUR TOUTES. Deux choses la
    périment, et les deux se mesurent ici plutôt que de se supposer :

      · LE TEXTE A CHANGÉ. L'empreinte consignée ne correspond plus à celle de
        la pièce : la personne a assumé une rédaction qui n'est plus celle du
        formulaire ;
      · LA PREUVE A EXPIRÉ. L'attestation valide le jour de l'affirmation ne
        l'est plus. L'affirmation reste vraie de ce jour-là ; elle ne dit plus
        rien d'aujourd'hui.

    Les deux sont RENDUS, jamais effacés : supprimer une affirmation périmée
    ferait disparaître la trace de ce qui avait été assumé, et c'est la trace
    qui a de la valeur.
    """
    import ao_dc
    import dossier_entreprise
    par_cle = {a["cle"]: a for a in affirmations(projet)}
    lignes = []
    for d in ao_dc.declarations():
        a = par_cle.get(d["cle"])
        couv = dossier_entreprise.couverture(d["cle"], aujourdhui)
        raisons = []
        if a:
            if a.get("texte_empreinte") != _empreinte_texte(d["texte"]):
                raisons.append("texte_modifie")
            if couv["etat"] == "incomplete":
                raisons.append("preuve_expiree")
        lignes.append({
            "cle": d["cle"], "piece": d["piece"], "libelle": d["libelle"],
            "engage": d["engage"], "engage_nom": d["engage_nom"],
            "message": d["message"],
            "affirmee": bool(a),
            "par": (a or {}).get("par"), "le": (a or {}).get("le"),
            "a_revoir": raisons,
            "couverture": couv["etat"], "manquantes": couv["manquantes"],
            "motif_sans_preuve": couv["motif"] if couv["etat"] ==
                                 "sans_preuve_interne" else "",
            # CE CHAMP EST UNE CONSTANTE, ET C'EST VOULU. Il dit à l'écran ce
            # que le module garantit : quoi qu'il arrive ici, la case du
            # formulaire reste vide. L'afficher évite qu'on attende de cette
            # page un remplissage qu'elle ne fera jamais.
            "remplit_le_formulaire": False,
        })
    a_revoir = [l["cle"] for l in lignes if l["a_revoir"]]
    return {"lignes": lignes,
            "affirmees": [l["cle"] for l in lignes if l["affirmee"]],
            "a_revoir": a_revoir,
            "restantes": [l["cle"] for l in lignes if not l["affirmee"]]}
