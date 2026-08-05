"""Les projets d'ingénierie centre de données, et leur historique.

POURQUOI CE MODULE. L'historique des livrables existait déjà, mais à plat : une
liste de documents portant un nom de client en texte libre. Retrouver « ce qui a
été produit pour le projet Amsterdam, en phase APD » supposait de lire les
intitulés un par un et d'espérer que la même orthographe ait été employée à
chaque fois. Un projet est un OBJET : il a un identifiant, un propriétaire, une
filière, un statut, une date de dernière activité — et les livrables s'y
rattachent au lieu de le décrire.

LE PROPRIÉTAIRE EST STRUCTURANT. Chaque projet appartient au compte qui l'a
créé, et les lectures sont filtrées dessus. Sans ce filtre, deux clients
connectés au même service verraient l'historique l'un de l'autre — le genre de
défaut qui ne se voit qu'une fois, et une fois de trop.

Deux implémentations interchangeables, comme rag_store et livrables_store :
PostgreSQL si DATABASE_URL est défini, mémoire sinon.
"""
import json
import logging
import os
import threading
import time
import uuid

_log = logging.getLogger("projets_dc")

LIST_LIMIT = 400
MAX_PROJETS_PAR_COMPTE = 200
MAX_COLLABORATEURS = 25

# Le statut d'un projet. Vocabulaire fermé : « en cours », « en_cours »,
# « EN COURS » écrits au fil de l'eau rendraient tout filtre inutile.
STATUTS = {
    "cadrage": {"nom": "Cadrage", "rang": 1,
                "aide": "Le projet est ouvert, les hypothèses ne sont pas arrêtées."},
    "en_cours": {"nom": "En cours", "rang": 2,
                 "aide": "Des phases sont franchies et des livrables produits."},
    "suspendu": {"nom": "Suspendu", "rang": 3,
                 "aide": "Arrêté temporairement ; l'historique reste consultable."},
    "livre": {"nom": "Livré", "rang": 4,
              "aide": "Le dossier a été remis. Les livrables restent accessibles "
                      "en lecture."},
    "archive": {"nom": "Archivé", "rang": 5,
                "aide": "Conservé pour mémoire, retiré des listes courantes."},
}
STATUT_DEFAUT = "cadrage"

# L'état d'un livrable dans le projet, distinct du statut du projet. Un projet
# « en cours » peut porter des brouillons ET des pièces visées : confondre les
# deux ferait croire qu'un dossier est prêt parce que le projet avance.
ETATS_LIVRABLE = {
    "brouillon": {"nom": "Brouillon", "rang": 1, "aide": "Produit, non relu."},
    "relu": {"nom": "Relu", "rang": 2,
             "aide": "Relu par un ingénieur, pas encore visé."},
    "vise": {"nom": "Visé", "rang": 3, "aide": "Visé et versé au dossier."},
    "obsolete": {"nom": "Obsolète", "rang": 4,
                 "aide": "Remplacé par une version postérieure."},
}
ETAT_DEFAUT = "brouillon"


# ═══════════════════════════════════════════════════════════════════════════
#  LES VISAS : QUI A VALIDÉ, QUI A REJETÉ, ET CE QUI EN RÉSULTE
# ═══════════════════════════════════════════════════════════════════════════
# L'état d'un livrable — brouillon, relu, visé — dit où EN EST la rédaction.
# Il ne dit pas ce que le client en pense. Un document parfaitement rédigé et
# rejeté par le client n'est pas un document prêt, et l'afficher « visé » ferait
# passer un point de blocage pour un point d'avancement.
#
# Un livrable porte donc une LISTE d'avis, pas un état unique : un document
# rejeté par un collègue puis validé par le client a deux avis, et n'en garder
# qu'un ferait disparaître celui qui gêne.

ROLES_VISA = {
    "client": {"nom": "Client", "rang": 1,
               "aide": "Le maître d'ouvrage ou son représentant. Son refus "
                       "bloque la remise."},
    "collegue": {"nom": "Collègue du projet", "rang": 2,
                 "aide": "Un membre de l'équipe invité sur le projet. Son refus "
                         "bloque la transmission au client."},
    "moe": {"nom": "Maîtrise d'œuvre", "rang": 3,
            "aide": "Relecture interne avant transmission."},
}

DECISIONS_VISA = {
    "valide": {"nom": "Validé", "rang": 1},
    "rejete": {"nom": "Rejeté", "rang": 2},
}

# Les états de validation affichés, du plus bloquant au plus avancé. L'ordre
# n'est pas cosmétique : c'est lui qui décide ce qu'on montre quand plusieurs
# avis coexistent.
ETATS_VISA = {
    "rejete_client": {"nom": "Rejeté par le client", "rang": 1,
                      "couleur": "#F39F7D",
                      "aide": "Le client a refusé la pièce. Rien ne se remet "
                              "tant que le motif n'est pas levé."},
    "rejete_collegue": {"nom": "Rejeté en interne", "rang": 2,
                        "couleur": "#E8B44A",
                        "aide": "Un membre de l'équipe a refusé la pièce. Elle "
                                "ne part pas au client en l'état."},
    "en_attente": {"nom": "En attente de visa", "rang": 3,
                   "couleur": "#9FB3C8",
                   "aide": "Produite, soumise à personne pour l'instant."},
    "valide_interne": {"nom": "Validé en interne", "rang": 4,
                       "couleur": "#5BC8E8",
                       "aide": "Relue et acceptée par l'équipe ; le client ne "
                               "s'est pas encore prononcé."},
    "valide_client": {"nom": "Validé par le client", "rang": 5,
                      "couleur": "#7FD4A8",
                      "aide": "Le client a accepté la pièce."},
}


def synthese_visas(visas):
    """L'état de validation d'un livrable, dérivé de ses avis.

    DEUX RÈGLES, et la seconde est celle qu'on oublie :

      · Pour un même acteur, seul le DERNIER avis compte. Un client qui rejette
        puis valide après correction a validé ; garder son refus figerait le
        dossier sur un grief levé.

      · Un refus non levé l'emporte sur toute validation, quel que soit son
        auteur. Un document rejeté par le client puis validé par un collègue
        reste bloqué : la validation interne ne lève pas le refus du client, et
        afficher « validé » ferait remettre une pièce refusée.
    """
    derniers = {}
    for v in (visas or []):
        if not isinstance(v, dict):
            continue
        role = v.get("role")
        if role not in ROLES_VISA or v.get("decision") not in DECISIONS_VISA:
            continue
        cle = (role, (v.get("par") or "").strip().lower())
        prec = derniers.get(cle)
        if not prec or (v.get("le") or 0) >= (prec.get("le") or 0):
            derniers[cle] = v
    avis = list(derniers.values())
    if not avis:
        return {"etat": "en_attente", "nom": ETATS_VISA["en_attente"]["nom"],
                "couleur": ETATS_VISA["en_attente"]["couleur"],
                "avis": [], "bloquants": []}
    bloquants = [v for v in avis if v.get("decision") == "rejete"]
    if any(v.get("role") == "client" for v in bloquants):
        etat = "rejete_client"
    elif bloquants:
        etat = "rejete_collegue"
    elif any(v.get("role") == "client" and v.get("decision") == "valide"
             for v in avis):
        etat = "valide_client"
    else:
        etat = "valide_interne"
    return {"etat": etat, "nom": ETATS_VISA[etat]["nom"],
            "couleur": ETATS_VISA[etat]["couleur"],
            "avis": sorted(avis, key=lambda v: -(v.get("le") or 0)),
            "bloquants": bloquants}


def _ordre(vocabulaire):
    """Les clés d'un vocabulaire, dans l'ordre du CYCLE DE VIE.

    Un dictionnaire n'a pas d'ordre une fois sérialisé : Flask trie les clés,
    et la page recevait donc « archive, cadrage, en_cours, livre, suspendu ».
    Une liste déroulante bâtie sur cet ordre proposait « Archivé » en premier
    choix — et le premier choix est celui que le navigateur retient quand rien
    n'est sélectionné. Les projets naissaient archivés, donc invisibles dans
    leur propre liste, sans la moindre erreur nulle part.

    L'ordre est désormais porté par les données elles-mêmes, et servi à part.
    """
    return sorted(vocabulaire, key=lambda k: vocabulaire[k].get("rang", 99))


def _now_ms():
    return int(time.time() * 1000)


def _valid_id(v):
    return isinstance(v, str) and len(v) == 32 and all(
        c in "0123456789abcdef" for c in v)


def _clean(rec, partiel=False):
    """Normalise un projet entrant. `partiel` sert aux mises à jour."""
    out = {}
    if not partiel or "nom" in rec:
        nom = (rec.get("nom") or "").strip()[:160]
        if not nom:
            raise ProjetError("nom_manquant", 400,
                              "Un projet doit porter un nom.")
        out["nom"] = nom
    for champ, taille in (("client", 200), ("secteur", 80), ("perimetre", 80),
                          ("maitrise_ouvrage", 80), ("note", 2000)):
        if not partiel or champ in rec:
            out[champ] = (rec.get(champ) or "").strip()[:taille]
    if not partiel or "filiere" in rec:
        f = (rec.get("filiere") or "moe").strip()
        out["filiere"] = f if f in ("moe", "indus") else "moe"
    if not partiel or "statut" in rec:
        s = (rec.get("statut") or STATUT_DEFAUT).strip()
        out["statut"] = s if s in STATUTS else STATUT_DEFAUT
    if not partiel or "phase" in rec:
        out["phase"] = (rec.get("phase") or "").strip()[:12].upper()
    if "collaborateurs" in rec:
        out["collaborateurs"] = _emails(rec.get("collaborateurs"))
    elif not partiel:
        out["collaborateurs"] = []
    return out


def _emails(v):
    """Normalise une liste d'adresses. Minuscules et dédoublonnées : « Jean@X »
    et « jean@x » désignent le même collègue, et les garder toutes deux ferait
    apparaître deux invités là où il n'y en a qu'un — puis un accès resterait
    après le retrait de l'autre."""
    if isinstance(v, str):
        v = [v]
    vus, out = set(), []
    for x in (v or []):
        e = str(x or "").strip().lower()[:200]
        # Contrôle minimal : une arobase entourée de quelque chose. On ne
        # valide pas plus loin — une adresse mal formée ne donne aucun accès,
        # puisque l'accès se prouve par une session, jamais par cette liste.
        if "@" not in e or e.startswith("@") or e.endswith("@") or e in vus:
            continue
        vus.add(e)
        out.append(e)
        if len(out) >= MAX_COLLABORATEURS:
            break
    return out


class ProjetError(Exception):
    def __init__(self, code, status=400, detail=""):
        super().__init__(code)
        self.code = code
        self.status = status
        self.detail = detail or ""


# ============================================================================
#  Mémoire (repli non persistant)
# ============================================================================

def _accede(r, compte):
    """Qui voit un projet : son propriétaire, et les collègues invités.

    Écrite une fois et appelée partout. Recopiée à chaque requête, elle finit
    par diverger d'un endroit à l'autre — et c'est l'endroit oublié qui laisse
    passer."""
    if not r or not compte:
        return False
    return (r.get("proprietaire") == compte
            or compte in (r.get("collaborateurs") or []))


class MemoryProjetsStore:
    def __init__(self):
        self._p = {}
        self._lock = threading.RLock()

    def creer(self, proprietaire, rec):
        r = _clean(rec)
        with self._lock:
            miens = [x for x in self._p.values() if x["proprietaire"] == proprietaire]
            if len(miens) >= MAX_PROJETS_PAR_COMPTE:
                raise ProjetError("trop_de_projets", 409,
                                  "Ce compte a atteint %d projets."
                                  % MAX_PROJETS_PAR_COMPTE)
            pid = uuid.uuid4().hex
            r.update(id=pid, proprietaire=proprietaire,
                     cree_le=_now_ms(), maj_le=_now_ms())
            self._p[pid] = r
            return dict(r)

    def lister(self, proprietaire, inclure_archives=False):
        with self._lock:
            out = [dict(x) for x in self._p.values()
                   if _accede(x, proprietaire)
                   and (inclure_archives or x["statut"] != "archive")]
        return sorted(out, key=lambda x: -x["maj_le"])[:LIST_LIMIT]

    def obtenir(self, proprietaire, pid):
        with self._lock:
            r = self._p.get(pid)
            # Le contrôle d'accès est fait ICI et non dans la route : une
            # vérification posée dans l'appelant s'oublie au deuxième appelant,
            # et c'est ce jour-là qu'un client voit le dossier d'un autre.
            return dict(r) if r and _accede(r, proprietaire) else None

    def modifier(self, proprietaire, pid, rec):
        with self._lock:
            r = self._p.get(pid)
            # Modifier est ouvert aux invités — ils travaillent sur le dossier.
            if not r or not _accede(r, proprietaire):
                return None
            # Sauf la liste des invités elle-même : un collègue qui pourrait
            # s'ajouter des collègues ferait du partage une porte qui s'élargit
            # toute seule. Seul le propriétaire invite.
            if "collaborateurs" in rec and r["proprietaire"] != proprietaire:
                rec = {k: v for k, v in rec.items() if k != "collaborateurs"}
            r.update(_clean(rec, partiel=True))
            r["maj_le"] = _now_ms()
            return dict(r)

    def supprimer(self, proprietaire, pid):
        with self._lock:
            r = self._p.get(pid)
            # Supprimer reste au SEUL propriétaire, même quand des invités
            # peuvent écrire : partager un dossier ne donne pas le droit de le
            # faire disparaître pour tout le monde.
            if not r or r["proprietaire"] != proprietaire:
                return False
            del self._p[pid]
            return True

    def toucher(self, pid):
        """Marque une activité sur le projet. Appelé à chaque livrable produit :
        la date de dernière activité est ce qui trie utilement une liste de
        projets, et la recalculer à la lecture coûterait un parcours complet."""
        with self._lock:
            r = self._p.get(pid)
            if r:
                r["maj_le"] = _now_ms()

    def tous(self):
        with self._lock:
            return [dict(x) for x in self._p.values()]

    def restaurer(self, lignes):
        n = 0
        with self._lock:
            for r in lignes or []:
                if _valid_id(r.get("id")) and r.get("proprietaire"):
                    self._p[r["id"]] = dict(r)
                    n += 1
        return n


# ============================================================================
#  PostgreSQL
# ============================================================================

_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS projets_dc (
        id TEXT PRIMARY KEY,
        proprietaire TEXT NOT NULL,
        nom TEXT NOT NULL,
        client TEXT,
        secteur TEXT,
        perimetre TEXT,
        maitrise_ouvrage TEXT,
        filiere TEXT,
        phase TEXT,
        statut TEXT,
        note TEXT,
        cree_le BIGINT,
        maj_le BIGINT)""",
    # Les collègues invités sur le projet (ajout compatible : les projets
    # antérieurs restent lisibles, sans invité).
    "ALTER TABLE projets_dc ADD COLUMN IF NOT EXISTS collaborateurs TEXT",
    "CREATE INDEX IF NOT EXISTS projets_dc_prop_idx "
    "ON projets_dc (proprietaire, maj_le DESC)",
]

_COLS = ("id,proprietaire,nom,client,secteur,perimetre,maitrise_ouvrage,"
         "filiere,phase,statut,note,cree_le,maj_le,collaborateurs")


def _row(r):
    if not r:
        return None
    d = dict(zip(_COLS.split(","), r))
    # La liste des invités est stockée sérialisée ; illisible, elle rend une
    # liste vide plutôt qu'une exception — un partage perdu se refait, un
    # projet qui ne s'ouvre plus bloque le dossier.
    v = d.get("collaborateurs")
    if not isinstance(v, list):
        try:
            d["collaborateurs"] = json.loads(v) if v else []
        except (ValueError, TypeError):
            d["collaborateurs"] = []
    if not isinstance(d["collaborateurs"], list):
        d["collaborateurs"] = []
    return d


def _pour_pg(r):
    """Sérialise les champs composés avant écriture."""
    out = dict(r)
    if isinstance(out.get("collaborateurs"), list):
        out["collaborateurs"] = json.dumps(out["collaborateurs"], ensure_ascii=False)
    return out


class PostgresProjetsStore:
    def __init__(self, dsn):
        import psycopg
        self._psycopg = psycopg
        self._dsn = dsn
        with self._conn() as c:
            for s in _SCHEMA:
                c.execute(s)

    def _conn(self):
        return self._psycopg.connect(self._dsn, autocommit=True)

    def creer(self, proprietaire, rec):
        r = _clean(rec)
        with self._conn() as c:
            n = c.execute("SELECT COUNT(*) FROM projets_dc WHERE proprietaire=%s",
                          (proprietaire,)).fetchone()[0]
            if n >= MAX_PROJETS_PAR_COMPTE:
                raise ProjetError("trop_de_projets", 409,
                                  "Ce compte a atteint %d projets."
                                  % MAX_PROJETS_PAR_COMPTE)
            pid = uuid.uuid4().hex
            t = _now_ms()
            c.execute(
                "INSERT INTO projets_dc (" + _COLS + ") VALUES "
                "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (pid, proprietaire, r["nom"], r["client"], r["secteur"],
                 r["perimetre"], r["maitrise_ouvrage"], r["filiere"],
                 r["phase"], r["statut"], r["note"], t, t,
                 json.dumps(r.get("collaborateurs") or [], ensure_ascii=False)))
            return _row(c.execute("SELECT " + _COLS + " FROM projets_dc WHERE id=%s",
                                  (pid,)).fetchone())

    def lister(self, proprietaire, inclure_archives=False):
        # Le propriétaire OU un invité. Le filtre reste dans la requête : le
        # ramener côté Python chargerait tous les projets de la base pour en
        # écarter la plupart, et un oubli de filtre ne se verrait pas.
        q = ("SELECT " + _COLS + " FROM projets_dc "
             "WHERE (proprietaire=%s OR collaborateurs LIKE %s)"
             + ("" if inclure_archives else " AND statut<>'archive'")
             + " ORDER BY maj_le DESC LIMIT %s")
        motif = '%%"' + (proprietaire or "") + '"%%'
        with self._conn() as c:
            lignes = [_row(x) for x in
                      c.execute(q, (proprietaire, motif, LIST_LIMIT)).fetchall()]
        # Le LIKE est un PRÉ-FILTRE, pas la décision : « a@b.fr » figure aussi
        # dans « xa@b.fr ». La règle d'accès tranche ensuite, la même qu'en
        # mémoire, pour que les deux magasins ne divergent pas.
        return [x for x in lignes if _accede(x, proprietaire)]

    def obtenir(self, proprietaire, pid):
        with self._conn() as c:
            r = _row(c.execute("SELECT " + _COLS + " FROM projets_dc WHERE id=%s",
                               (pid,)).fetchone())
        return r if _accede(r, proprietaire) else None

    def modifier(self, proprietaire, pid, rec):
        # L'accès est vérifié AVANT d'écrire : un UPDATE filtré sur le seul
        # propriétaire aurait interdit toute modification aux invités, et un
        # UPDATE sans filtre les aurait laissés modifier n'importe quel projet.
        actuel = self.obtenir(proprietaire, pid)
        if not actuel:
            return None
        # Seul le propriétaire invite : un collègue qui pourrait s'ajouter des
        # collègues ferait du partage une porte qui s'élargit toute seule.
        if "collaborateurs" in rec and actuel["proprietaire"] != proprietaire:
            rec = {k: v for k, v in rec.items() if k != "collaborateurs"}
        r = _clean(rec, partiel=True)
        if not r:
            return actuel
        r = _pour_pg(r)
        sets = ", ".join("%s=%%s" % k for k in r) + ", maj_le=%s"
        vals = list(r.values()) + [_now_ms(), pid]
        with self._conn() as c:
            c.execute("UPDATE projets_dc SET " + sets + " WHERE id=%s", vals)
        return self.obtenir(proprietaire, pid)

    def supprimer(self, proprietaire, pid):
        with self._conn() as c:
            return c.execute("DELETE FROM projets_dc WHERE id=%s AND proprietaire=%s",
                             (pid, proprietaire)).rowcount > 0

    def toucher(self, pid):
        with self._conn() as c:
            c.execute("UPDATE projets_dc SET maj_le=%s WHERE id=%s", (_now_ms(), pid))

    def tous(self):
        with self._conn() as c:
            return [_row(x) for x in c.execute(
                "SELECT " + _COLS + " FROM projets_dc").fetchall()]

    def restaurer(self, lignes):
        n = 0
        with self._conn() as c:
            for r in lignes or []:
                if not _valid_id(r.get("id")) or not r.get("proprietaire"):
                    continue
                c.execute(
                    "INSERT INTO projets_dc (" + _COLS + ") VALUES "
                    "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT (id) DO UPDATE SET nom=EXCLUDED.nom,"
                    "statut=EXCLUDED.statut,phase=EXCLUDED.phase,"
                    "note=EXCLUDED.note,maj_le=EXCLUDED.maj_le",
                    tuple(_pour_pg(r).get(k) for k in _COLS.split(",")))
                n += 1
        return n


def _migrer(mem, pg):
    """Reverse le contenu mémoire dans PostgreSQL quand la base redevient
    joignable. Sans cela, les projets créés pendant une coupure disparaîtraient
    au redéploiement suivant — silencieusement."""
    lignes = mem.tous()
    if not lignes:
        return 0
    n = pg.restaurer(lignes)
    _log.info("Projets : %d enregistrement(s) reversés en base.", n)
    return n


def make_projets_store():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return MemoryProjetsStore()
    if dsn.startswith("postgres://"):
        dsn = "postgresql://" + dsn[len("postgres://"):]
    from resilience import MagasinResilient
    return MagasinResilient("Projets ingénierie",
                            lambda: PostgresProjetsStore(dsn),
                            MemoryProjetsStore(), migrer=_migrer)


def referentiel():
    """Les vocabulaires fermés, servis à la page plutôt que recopiés dedans."""
    return {"statuts": STATUTS, "statut_defaut": STATUT_DEFAUT,
            "max_collaborateurs": MAX_COLLABORATEURS,
            "roles_visa": ROLES_VISA, "decisions_visa": DECISIONS_VISA,
            "etats_visa": ETATS_VISA,
            "etats_visa_ordre": _ordre(ETATS_VISA),
            "statuts_ordre": _ordre(STATUTS),
            "etats_livrable": ETATS_LIVRABLE, "etat_defaut": ETAT_DEFAUT,
            "etats_ordre": _ordre(ETATS_LIVRABLE),
            "max_par_compte": MAX_PROJETS_PAR_COMPTE}
