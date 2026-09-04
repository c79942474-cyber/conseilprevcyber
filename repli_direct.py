# -*- coding: utf-8 -*-
"""Le repli en connexion directe, écrit UNE fois pour tous les magasins.

L'INCIDENT, CONSTATÉ TROIS FOIS SUR DEUX ANS. La base répond parfaitement — une
connexion directe s'établit dans la seconde, sur 27 connexions ouvertes pour 103
autorisées — et pourtant toute opération échoue en « PoolTimeout ». Ni le réseau,
ni la base, ni un plafond : le POOL. Après un incident de connexion, psycopg_pool
se met en retrait et refuse d'en ouvrir de nouvelles pendant plusieurs minutes ;
les demandes attendent leur délai puis renoncent.

POURQUOI CE MODULE EXISTE, ALORS QUE LE REMÈDE ÉTAIT DÉJÀ ÉCRIT. Il l'était deux
fois — dans les comptes et dans la base de connaissance — et c'est précisément ce
qui a coûté cher : les magasins qui ne l'avaient pas ne se distinguaient en rien
de ceux qui l'avaient, et le troisième (l'automatisation) n'a été trouvé qu'un an
plus tard, par un utilisateur, sur la page publique de veille. Quatre autres
attendaient derrière lui.

Sept recopies d'une même correction divergent à la première retouche, et c'est
celle qu'on oublie qui reste muette. Elle vit donc ici, et les magasins l'appellent.

CE QUE L'HÔTE DOIT PORTER : `_dsn` (la chaîne de connexion complète) et `_pool`
(qui peut valoir None — un pool absent n'est pas une raison d'abandonner la base).
Le reste est posé au premier repli.

CE QUE CE REPLI NE FAIT PAS. Il traite l'échec d'ACQUISITION, et lui seul : une
erreur survenant DANS la requête remonte à l'appelant, qui sait quoi en faire.
"""
import time
from contextlib import contextmanager

# Attente maximale pour obtenir une connexion du pool avant de passer en direct.
# COURTE, et c'est le point : un pool en bonne santé répond en millisecondes.
# La première version de ce repli attendait douze secondes, si bien qu'une page
# composée de plusieurs opérations les payait CHACUNE avant de basculer — la
# requête dépassait le délai du navigateur et l'utilisateur voyait « Service
# momentanément indisponible ». Le repli fonctionnait, trop tard pour servir.
POOL_ACQUIS_S = 1.5

# Puis on cesse de solliciter le pool pendant une minute. Sans cette grâce,
# chaque opération repaie l'attente tant que le pool boude.
POOL_GRACE_S = 60.0


@contextmanager
def connexion(hote, etiquette, log, kwargs=None):
    """Une connexion pour une opération : du pool, ou directe s'il ne rend pas
    la main.

    `etiquette` nomme le magasin dans le journal — « clients », « livrables »…
    Un message qui ne dit pas QUI s'est replié n'aide personne à trois heures du
    matin, et c'est ce qui a fait manquer le défaut de la veille : le journal
    criait, mais sous le nom des deux autres magasins.
    """
    import psycopg
    pool = getattr(hote, "_pool", None)
    try:
        if pool is None or time.time() < getattr(hote, "_pool_ko_jusqu", 0.0):
            raise RuntimeError("pool absent ou en période de grâce")
        conn = pool.getconn(timeout=POOL_ACQUIS_S)
    except Exception as exc:
        hote.replis_directs = getattr(hote, "replis_directs", 0) + 1
        hote._pool_ko_jusqu = time.time() + POOL_GRACE_S
        log.warning("%s : pool indisponible (%s) — connexion directe pour cette "
                    "opération (%d au total).", etiquette, type(exc).__name__,
                    hote.replis_directs)
        direct = psycopg.connect(hote._dsn, **(kwargs or {}))
        try:
            yield direct
        finally:
            try:
                direct.close()
            except Exception:
                pass
        return
    try:
        yield conn
    finally:
        try:
            pool.putconn(conn)
        except Exception:
            pass
