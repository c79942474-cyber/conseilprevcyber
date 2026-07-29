"""Reconnexion automatique des magasins de données — mécanisme partagé.

CE QU'IL CORRIGE. Trois magasins sur six choisissaient leur moteur UNE SEULE
FOIS, au démarrage : `make_clients_store`, `make_livrables_store` et le magasin
du cockpit. Si PostgreSQL n'était pas joignable à cet instant — base qui se
réveille, redéploiement simultané du service et de la base, coupure de quelques
secondes — ils restaient en mémoire pour toute la vie du processus. Aucune
reconnexion, aucun rattrapage, aucun signal : la seule issue était un
redéploiement manuel. Pour les fiches clients, cela signifie des données
personnelles perdues au prochain redémarrage ; pour l'historique des livrables,
un travail effacé.

Le magasin de la base documentaire et celui des comptes avaient chacun résolu
le problème dans leur coin, avec deux mécanismes différents. Ce module en fait
un seul, pour que le comportement soit le même partout et qu'un correctif
profite à tous.

CE QU'IL FAIT.
  - Sert immédiatement depuis un repli : aucune requête n'attend jamais une
    base injoignable. Un démarrage ne doit pas dépendre d'une base lente, sans
    quoi la sonde de l'hébergeur échoue et l'instance est redémarrée en boucle.
  - Retente en tâche de fond, avec un recul EXPONENTIEL borné et une gigue.
    Le recul évite de marteler une base durablement absente ; la gigue évite
    que plusieurs magasins ne frappent en même temps, ce qui aggraverait une
    saturation de connexions au lieu de la laisser retomber.
  - REVERSE le contenu du repli dans la base au moment de basculer, quand le
    magasin sait le faire. Sans cela, il faudrait choisir entre guérir et
    conserver ce qui a été écrit pendant la panne — un choix qu'on ne devrait
    jamais avoir à faire, et qui bloquait la reconnexion en pratique.
  - Expose un état LISIBLE : mode courant, cause réelle de l'échec, nombre
    d'essais, date du prochain. « La connexion échoue » sans dire pourquoi
    n'aide personne à décider quoi faire.

CE QU'IL NE FAIT PAS. Il ne rejoue pas les écritures perdues par un magasin qui
ne sait pas énumérer son contenu : dans ce cas la bascule n'a lieu que si le
repli est vide, et l'état le dit. Prétendre le contraire serait pire que la
limite elle-même.

Module autonome : bibliothèque standard uniquement.
"""
import logging
import os
import random
import threading
import time

_log = logging.getLogger("resilience")

# Recul exponentiel : 30 s, 60 s, 120 s… plafonné à 5 minutes. Le plafond
# compte autant que la progression — sans lui, une base absente une nuit ne
# serait retentée qu'une fois par heure au matin, et le rétablissement
# passerait inaperçu pendant très longtemps.
DELAI_MIN = float(os.environ.get("RECONNECT_MIN_S", "30"))
DELAI_MAX = float(os.environ.get("RECONNECT_MAX_S", "300"))


def _assainir(exc):
    """Message d'erreur montrable : jamais d'identifiant ni de mot de passe.

    Une chaîne de connexion se glisse volontiers dans un message d'exception ;
    l'afficher dans une console d'administration reviendrait à publier le mot
    de passe de la base à qui sait ouvrir les outils de développement.
    """
    txt = str(exc or "").strip()
    if "://" in txt:
        avant, _, apres = txt.partition("://")
        _, _, suite = apres.partition("@")
        txt = avant + "://…@" + (suite or "…")
    txt = " ".join(txt.split())
    return txt[:240] or type(exc).__name__


class MagasinResilient:
    """Enveloppe : sert depuis `repli` tant que `fabriquer` échoue.

    `fabriquer()`   construit le magasin persistant, ou lève.
    `repli`         magasin de secours, immédiatement utilisable.
    `migrer(m, p)`  optionnel : verse le contenu du repli dans le magasin
                    persistant, retourne (repris, echecs). Sans lui, la bascule
                    n'a lieu que si le repli est vide.
    `vide(m)`       optionnel : dit si le repli ne contient rien à préserver.
    """

    def __init__(self, nom, fabriquer, repli, migrer=None, vide=None):
        self.nom = nom
        self._fabriquer = fabriquer
        self._repli = repli
        self._migrer = migrer
        self._vide = vide
        self._pg = None
        self._lock = threading.Lock()
        self._en_cours = False
        self._echecs = 0
        self._cause = ""
        self._dernier_essai = 0.0
        self._prochain_essai = 0.0
        self._depuis = time.time()
        self._bascules = 0
        # Premier essai EN TÂCHE DE FOND : le processus démarre instantanément.
        self._programmer(immediat=True)

    # ── état ────────────────────────────────────────────────────────────
    @property
    def persistent(self):
        actif = self._pg if self._pg is not None else self._repli
        return bool(getattr(actif, "persistent", False))

    def etat(self):
        """Vue destinée à la console d'administration et à /health."""
        return {
            "magasin": self.nom,
            "mode": "postgres" if self._pg is not None else "repli",
            "persistant": self.persistent,
            "cause": self._cause,
            "echecs_consecutifs": self._echecs,
            "dernier_essai_s": int(time.time() - self._dernier_essai) if self._dernier_essai else None,
            "prochain_essai_s": max(0, int(self._prochain_essai - time.time())) if self._pg is None else None,
            "degrade_depuis_s": int(time.time() - self._depuis) if self._pg is None else None,
            "bascules": self._bascules,
        }

    # ── reconnexion ─────────────────────────────────────────────────────
    def _delai(self):
        """Recul exponentiel borné, avec gigue de ±20 %."""
        base = min(DELAI_MIN * (2 ** max(0, self._echecs - 1)), DELAI_MAX)
        return base * (0.8 + 0.4 * random.random())

    def _programmer(self, immediat=False):
        with self._lock:
            if self._pg is not None or self._en_cours:
                return
            if not immediat and time.time() < self._prochain_essai:
                return
            self._en_cours = True
        threading.Thread(target=self._essayer, daemon=True).start()

    def _essayer(self):
        try:
            self._dernier_essai = time.time()
            try:
                pg = self._fabriquer()
            except Exception as exc:
                self._echecs += 1
                self._cause = _assainir(exc)
                self._prochain_essai = time.time() + self._delai()
                _log.warning("%s : base injoignable (échec %d, cause : %s) — "
                             "nouvel essai dans %ds.", self.nom, self._echecs,
                             self._cause, int(self._prochain_essai - time.time()))
                return False

            # La base répond. Reste à ne rien perdre de ce qui a été écrit
            # pendant la panne.
            if self._migrer is not None:
                try:
                    repris, echecs = self._migrer(self._repli, pg)
                except Exception as exc:
                    self._echecs += 1
                    self._cause = "reprise du repli impossible : " + _assainir(exc)
                    self._prochain_essai = time.time() + self._delai()
                    _log.warning("%s : %s", self.nom, self._cause)
                    return False
                if echecs:
                    self._echecs += 1
                    self._cause = ("base jointe, mais %d élément(s) du repli n'ont pas pu "
                                   "y être versés — on reste en repli pour ne rien perdre" % echecs)
                    self._prochain_essai = time.time() + self._delai()
                    _log.warning("%s : %s", self.nom, self._cause)
                    return False
                if repris:
                    _log.info("%s : %d élément(s) du repli versés en base.", self.nom, repris)
            elif self._vide is not None and not self._vide(self._repli):
                # Rien pour reverser et le repli n'est pas vide : basculer
                # masquerait son contenu. On le DIT plutôt que de le faire.
                self._echecs += 1
                self._cause = ("base jointe, mais le repli contient des données non "
                               "reversables — bascule suspendue, intervention requise")
                self._prochain_essai = time.time() + self._delai()
                _log.warning("%s : %s", self.nom, self._cause)
                return False

            self._pg = pg
            self._echecs = 0
            self._cause = ""
            self._bascules += 1
            _log.info("%s : base connectée.", self.nom)
            return True
        finally:
            self._en_cours = False

    def _maybe_reconnect(self):
        """Essai non bloquant, respectant le recul. Appelé par la tâche
        périodique et par les lectures."""
        self._programmer(immediat=False)

    def reconnecter(self):
        """Essai IMMÉDIAT et synchrone — bouton « Reconnecter » de la console.
        Une demande explicite ignore le recul : c'est tout son intérêt."""
        with self._lock:
            if self._pg is not None:
                return True
            self._en_cours = True
        return bool(self._essayer())

    # ── délégation ──────────────────────────────────────────────────────
    def __getattr__(self, nom):
        """Tout le reste va au magasin actif.

        Appelé seulement si l'attribut n'existe pas sur l'enveloppe : `persistent`,
        `etat` et `reconnecter` ci-dessus ont donc priorité, et le magasin sous-
        jacent garde son API intacte pour tout le reste — aucun appelant n'a à
        savoir qu'il parle à une enveloppe.
        """
        if nom.startswith("_"):
            raise AttributeError(nom)
        actif = self._pg if self._pg is not None else self._repli
        return getattr(actif, nom)
