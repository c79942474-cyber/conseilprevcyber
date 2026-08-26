"""AUTO-ÉVALUATION DE MATURITÉ OT — ce qu'elle vaut, et ce qu'elle ne remplace pas.

CE MODULE REND UN CHIFFRE PAR DOMAINE, ET IL EST LE PREMIER DU SITE À LE
FAIRE. `checklist_62443` s'y refuse, et il a raison de s'y refuser : un compte
de cases n'est pas un niveau. Ici la situation est différente, et la
différence tient en une phrase — LE NIVEAU N'EST PAS CALCULÉ, IL EST DÉCLARÉ.
On ne déduit pas « ML 2 » de vingt-sept cases : on demande à quelqu'un de
choisir, parmi six descriptions concrètes, celle qui correspond à ce qu'il
peut MONTRER. C'est une auto-évaluation, et elle s'annonce comme telle.

════════════════════════════════════════════════════════════════════════════
CE QUE CECI N'EST PAS, ET LA PAGE LE DIT DÉJÀ MIEUX QUE MOI
════════════════════════════════════════════════════════════════════════════
La page `/maturite-ot` promet un assessment qui va « au-delà de la case à
cocher ». Un vrai assessment se conduit : entretiens, relevés, preuves
examinées, contradiction. Ce module ne fait rien de tout cela, et il ne peut
pas — personne n'est venu sur site.

CE QU'IL FAIT : il structure une déclaration. C'est utile, et c'est autre
chose. Un dirigeant qui pose ses six niveaux et voit son écart à la cible
tient une base de discussion en dix minutes ; il ne tient pas un assessment,
et le document produit le dit dans sa première ligne.

LE MOT « ML » N'EST PAS EMPRUNTÉ. L'échelle ci-dessous est à SIX degrés
(0 à 5) et porte des noms qui lui appartiennent. La 62443-2-4 en a quatre
(ML 1 à 4) et ils s'appliquent au programme d'un PRESTATAIRE ; les recopier
ici ferait croire à une équivalence qui n'existe pas. La correspondance
approximative est déclarée dans `VOISINAGES`, avec le mot « approximative »
dedans.

════════════════════════════════════════════════════════════════════════════
LES DOMAINES SONT CEUX DE LA CHECKLIST, ET C'EST DÉLIBÉRÉ
════════════════════════════════════════════════════════════════════════════
Six domaines, exactement les six sections de `checklist_62443`. Inventer un
septième découpage aurait donné deux vocabulaires pour la même chose sur le
même site — et le lecteur qui passe de la liste à l'auto-évaluation aurait dû
traduire de tête. La liste dit CE QU'IL FAUT AVOIR ; ce module dit À QUEL
POINT ON LE TIENT. Même terrain, deux questions.
"""

import checklist_62443 as CK

VERSION = "2026-08-a"

#: CE QUE CE MODULE N'EST PAS. Voyage avec chaque résultat et ouvre chaque
#: document : servie à part, la réserve resterait sur la page pendant que le
#: chiffre, lui, partirait en réunion.
REFUS_ASSESSMENT = (
    "Ceci est une AUTO-ÉVALUATION DÉCLARATIVE, pas un assessment. Un "
    "assessment se conduit : entretiens, relevés, preuves examinées, "
    "contradiction. Ici, les niveaux sont ceux que VOUS déclarez, et rien ne "
    "les a vérifiés. L'écart entre les deux est précisément ce qu'un "
    "assessment mesure — et c'est souvent d'un degré, toujours dans le même "
    "sens."
)

#: L'ÉCHELLE. Six degrés, décrits par CE QU'ON PEUT MONTRER — jamais par un
#: adjectif. « Maturité moyenne » ne se choisit pas : « écrit mais pas
#: appliqué » se reconnaît.
ECHELLE = [
    {"n": 0, "nom": "Rien",
     "dit": "Rien n'existe sur ce domaine. Ni document, ni responsable, ni "
            "pratique établie."},
    {"n": 1, "nom": "Ponctuel",
     "dit": "Des actions existent, mais elles tiennent à des personnes et à "
            "des occasions. Rien n'est écrit ; le départ de quelqu'un ferait "
            "disparaître la pratique."},
    {"n": 2, "nom": "Écrit",
     "dit": "C'est écrit et validé, mais pas appliqué partout. L'écart entre "
            "le document et le terrain n'est ni mesuré ni assumé."},
    {"n": 3, "nom": "Appliqué",
     "dit": "C'est appliqué sur tout le périmètre, et on peut le montrer. "
            "C'est le premier degré où une preuve existe pour un auditeur."},
    {"n": 4, "nom": "Mesuré",
     "dit": "L'application est mesurée : des indicateurs existent, ils sont "
            "regardés, et un écart déclenche une action nommée."},
    {"n": 5, "nom": "Tenu dans le temps",
     "dit": "Les mesures alimentent une révision périodique qui a "
            "RÉELLEMENT changé quelque chose au moins une fois. Sans cette "
            "dernière condition, le degré 5 est un degré 4 qui se raconte."},
]

MINI, MAXI = 0, 5

#: LA CORRESPONDANCE AVEC LES ÉCHELLES CONNUES — approximative, et le mot est
#: dans le texte. Elle est servie parce que le lecteur la cherchera de toute
#: façon ; la taire le laisserait la faire de tête, et plus mal.
VOISINAGES = (
    "Correspondance APPROXIMATIVE, donnée pour situer et non pour convertir : "
    "les degrés 2–3 de cette échelle sont proches de ML 2 (62443-2-4) et du "
    "niveau « Repeatable » du C2M2 ; les degrés 4–5 de ML 3–4 et de "
    "« Managed ». Aucune équivalence n'est exacte : la 62443-2-4 s'applique "
    "au programme d'un PRESTATAIRE, le C2M2 se constate par domaine sur "
    "entretien, et le NIST CSF n'est pas une échelle de maturité mais un "
    "cadre de fonctions."
)

#: LES SIX DOMAINES. `section` renvoie à la section de `checklist_62443` qui
#: dit CE QU'IL FAUT AVOIR ; ce module dit à quel point on le tient.
#:
#: `gravite` et `effort` sont des JUGEMENTS DE CE CABINET, motivés chacun.
#: Ils servent à ordonner, jamais à noter : la priorité qui en sort est un
#: ordre de passage, pas une évaluation du client.
DOMAINES = [
    {
        "cle": "gouvernance",
        "objet": "la politique, le responsable désigné, l'analyse de risque "
                 "et le traitement des risques",
        "gravite": 5,
        "gravite_dit": "Ce qui n'a pas de propriétaire ne se maintient pas. "
                       "Un domaine faible ici fait retomber les cinq autres "
                       "au premier projet pressé — c'est le seul dont la "
                       "faiblesse se propage à tout le reste.",
        "effort": 2,
        "effort_dit": "Écrire une politique et désigner un responsable "
                      "coûte des décisions, pas des travaux. C'est le "
                      "meilleur rapport de la liste.",
        "cible": 4,
        "cible_dit": "Une gouvernance non mesurée redevient déclarative en "
                     "dix-huit mois. Le degré 4 est le premier qui tienne "
                     "sans surveillance rapprochée.",
    },
    {
        "cle": "architecture",
        "objet": "l'inventaire des actifs, le modèle de zones et conduits, "
                 "et ce qui les sépare réellement",
        "gravite": 5,
        "gravite_dit": "C'est ici que le coût d'une intrusion se décide : un "
                       "réseau plat propage en minutes ce qu'un zonage "
                       "contient. Et l'inventaire commande tout le reste.",
        "effort": 5,
        "effort_dit": "Segmenter un parc en service demande des arrêts, des "
                      "essais et de l'argent. C'est le poste le plus lourd, "
                      "et le prétendre rapide serait mentir sur un devis.",
        "cible": 4,
        "cible_dit": "Un zonage non mesuré dérive à chaque projet. Le degré "
                     "5 n'est pas exigé : la revue périodique d'un zonage "
                     "coûte cher pour un gain marginal une fois qu'il est "
                     "tenu.",
    },
    {
        "cle": "acces",
        "objet": "l'authentification, les privilèges, les comptes par défaut "
                 "et la journalisation",
        "gravite": 4,
        "gravite_dit": "C'est la porte la plus empruntée, et l'écart entre "
                       "la politique écrite et le terrain y est le plus "
                       "fréquent : le compte partagé de l'astreinte survit "
                       "à toutes les politiques.",
        "effort": 3,
        "effort_dit": "Techniquement faisable, humainement disputé. Le coût "
                      "est en négociation avec l'exploitation, pas en "
                      "matériel.",
        "cible": 4,
        "cible_dit": "Sans mesure, une revue de droits qui ne retire jamais "
                     "rien passe pour une revue. Le degré 4 est celui où "
                     "l'on s'en aperçoit.",
    },
    {
        "cle": "protection",
        "objet": "l'antivirus, les sauvegardes restaurées, les correctifs et "
                 "le durcissement",
        "gravite": 4,
        "gravite_dit": "C'est ce qui décide de la durée d'un arrêt. Une "
                       "sauvegarde jamais restaurée ne se découvre qu'au "
                       "moment où elle devait servir.",
        "effort": 4,
        "effort_dit": "Chaque mesure se heurte à la disponibilité du "
                      "procédé : une fenêtre de correctif se négocie des "
                      "mois à l'avance.",
        "cible": 3,
        "cible_dit": "Le degré 3 — appliqué et démontrable — suffit ici tant "
                     "que l'architecture n'est pas tenue : mesurer des "
                     "correctifs sur un parc non segmenté optimise le "
                     "mauvais problème.",
    },
    {
        "cle": "detection",
        "objet": "les sondes, la corrélation des journaux, la référence de "
                 "trafic et la veille",
        "gravite": 3,
        "gravite_dit": "Détecter ne protège pas ; cela raccourcit. La "
                       "gravité est réelle mais seconde : une détection "
                       "posée sur un réseau plat alerte sur un incendie "
                       "déjà généralisé.",
        "effort": 4,
        "effort_dit": "Une sonde se pose, une référence de trafic se "
                      "construit sur des mois, et un destinataire nommé doit "
                      "exister — c'est ce dernier point qui coûte.",
        "cible": 3,
        "cible_dit": "Viser plus haut avant que l'architecture et l'accès ne "
                     "soient tenus revient à acheter des alertes que "
                     "personne ne peut traiter.",
    },
    {
        "cle": "fournisseurs",
        "objet": "l'évaluation des fournisseurs, les clauses au marché et la "
                 "certification des composants",
        "gravite": 3,
        "gravite_dit": "Le risque entre par le prestataire — accès distant, "
                       "maintenance, composants. La gravité est forte mais "
                       "elle se traite au rythme des renouvellements de "
                       "contrat, pas au vôtre.",
        "effort": 2,
        "effort_dit": "Écrire des clauses et une grille d'évaluation coûte "
                      "du temps de juriste, pas d'arrêt de production.",
        "cible": 3,
        "cible_dit": "Appliqué et démontrable suffit : c'est le fournisseur "
                     "qui porte la mesure au-delà, et c'est à lui qu'on la "
                     "demande.",
    },
]

ORDRE = [d["cle"] for d in DOMAINES]

#: OÙ CHAQUE DOMAINE SE TRAITE SUR CE SITE. Un écart nommé sans destination
#: laisse le lecteur avec un constat et rien d'autre — c'est le reproche
#: qu'on fait, à juste titre, aux diagnostics.
#:
#: LES RAPPROCHEMENTS SE FONT PAR LA PARTIE DE LA NORME, pas par
#: ressemblance de titre : le domaine « gouvernance » relève de la 62443-2-1,
#: et `/programme-securite` traite le CSMS de la 62443-2-1. Un lien posé sur
#: une parenté de vocabulaire enverrait le lecteur sur une page voisine du
#: sujet, ce qui use plus la confiance qu'une absence de lien.
#:
#: CHAQUE LIEN PORTE SA RAISON. Sans elle, une liste de liens est un menu
#: déguisé en conseil, et le lecteur clique au hasard.
RESSOURCES = {
    "gouvernance": [
        {"chemin": "/programme-securite", "titre": "Programme de sécurité (CSMS)",
         "pourquoi": "La même partie de la norme que ce domaine — la 62443-2-1 : "
                     "c'est là que se construisent la politique, les rôles et le "
                     "traitement des risques que vous venez de coter."},
        {"chemin": "/operating-model", "titre": "Operating model & gouvernance",
         "pourquoi": "Le degré 3 demande une application sur tout le périmètre : "
                     "cela suppose des rôles tenus et un rythme de décision, "
                     "c'est-à-dire un modèle opérationnel, pas une politique de plus."},
    ],
    "architecture": [
        {"chemin": "/analyse-de-risque", "titre": "Analyse de risque — zones & conduits",
         "pourquoi": "La 62443-3-2, partie de ce domaine : le découpage en zones "
                     "ne se décide pas sur un schéma réseau, il se déduit d'une "
                     "analyse de risque du système considéré."},
        {"chemin": "/architecture-cible", "titre": "Architecture cible OT",
         "pourquoi": "Ce que le zonage devient une fois posé : DMZ industrielle, "
                     "rebonds, diodes. C'est ici que le coût du degré 3 se chiffre."},
    ],
    "acces": [
        {"chemin": "/exigences-systeme", "titre": "Exigences système (62443-3-3)",
         "pourquoi": "Les deux premiers fondements de la 62443-3-3 — identification "
                     "et contrôle d'usage — sont exactement le contenu de ce "
                     "domaine, exigence par exigence et par niveau de sécurité."},
        {"chemin": "/technologies-securite", "titre": "Technologies de sécurité",
         "pourquoi": "Ce qui existe techniquement pour authentifier en OT, où les "
                     "solutions de l'informatique de gestion ne s'appliquent pas "
                     "telles quelles."},
    ],
    "protection": [
        {"chemin": "/gestion-correctifs", "titre": "Gestion des correctifs",
         "pourquoi": "La 62443-2-3 : un correctif s'applique quand le procédé le "
                     "permet. C'est la partie qui décrit comment tenir un parc à "
                     "jour sans arrêter la production."},
        {"chemin": "/continuite-ot", "titre": "Continuité & restauration",
         "pourquoi": "La sauvegarde qui compte est celle qu'on a restaurée. La "
                     "restauration des configurations d'automates y est traitée "
                     "pour elle-même, avec son exercice."},
    ],
    "detection": [
        {"chemin": "/technologies-securite", "titre": "Technologies de sécurité",
         "pourquoi": "Le panorama de la TR 62443-3-1 : ce qui se pose réellement "
                     "sur un réseau industriel pour détecter, et ce que chaque "
                     "technologie voit ou ne voit pas."},
        {"chemin": "/metriques-62443", "titre": "Métriques 62443-1-3",
         "pourquoi": "Le degré 4 exige des indicateurs regardés. La 62443-1-3 dit "
                     "lesquels se mesurent et comment, plutôt que d'en inventer."},
    ],
    "fournisseurs": [
        {"chemin": "/exigences-prestataires", "titre": "Exigences prestataires",
         "pourquoi": "La 62443-2-4, partie de ce domaine : les capacités qu'un "
                     "prestataire doit démontrer, à reprendre telles quelles dans "
                     "une grille d'évaluation."},
        {"chemin": "/exigences-composants", "titre": "Exigences composants",
         "pourquoi": "La 62443-4-2 : ce qu'on exige d'un composant certifié. C'est "
                     "ce qui se met au marché, et une exigence absente du marché "
                     "ne se rattrape pas après notification."},
    ],
}

#: LE DÉROULÉ D'UN ASSESSMENT CONDUIT, ET OÙ CHAQUE ÉTAPE SE PRÉPARE. Les six
#: cartes de la page décrivaient un service sans conduire nulle part : un
#: lecteur qui voulait savoir ce que « revue du dispositif » veut dire n'avait
#: aucun endroit où aller.
#:
#: `chemin` vaut None pour les deux étapes qui n'ont pas de page : la cotation
#: se fait sur CETTE page, et le benchmark ne se fait nulle part sur ce site —
#: c'est déjà dit dans les livrables, et le redire ici en lien mènerait à une
#: page qui n'existe pas.
DEROULE = [
    {"n": 1, "titre": "Entretiens & ateliers",
     "dit": "Rencontrer les acteurs IT, OT, engineering, opérations et sûreté.",
     "chemin": "/methodologie", "lien": "Voir la démarche",
     "pourquoi": "La démarche décrit qui est rencontré, dans quel ordre et pour "
                 "établir quoi — c'est ce qui distingue une série d'entretiens "
                 "d'un tour de table."},
    {"n": 2, "titre": "Revue documentaire",
     "dit": "Politiques, procédures, architectures, analyses de risques existantes.",
     "chemin": "/referentiel", "lien": "Voir le référentiel 62443",
     "pourquoi": "Savoir quelle partie de la série fonde chaque document évite "
                 "de réclamer une pièce que la norme ne demande pas."},
    {"n": 3, "titre": "Revue du dispositif",
     "dit": "Observer le dispositif en place sur le terrain et ses pratiques réelles.",
     "chemin": "/audit-conformite", "lien": "Voir l'audit de conformité",
     "pourquoi": "L'audit de conformité est cette revue conduite jusqu'au bout : "
                 "état des lieux des actifs et écart aux exigences, sur preuves."},
    {"n": 4, "titre": "Cotation",
     "dit": "Positionner chaque domaine sur l'échelle de maturité, preuves à l'appui.",
     "chemin": None, "lien": "Renseigner l'auto-évaluation",
     "pourquoi": "C'est l'étape que cette page structure — à ceci près qu'ici les "
                 "degrés sont déclarés, et que là ils sont constatés sur preuves."},
    {"n": 5, "titre": "Benchmark",
     "dit": "Situer votre maturité au regard de votre secteur.",
     "chemin": None, "lien": None,
     "pourquoi": "Aucune page de ce site ne le fait, et c'est assumé : un "
                 "positionnement sectoriel demande un panel, une méthode et une "
                 "date, qu'aucune donnée d'ici ne fournit."},
    {"n": 6, "titre": "Restitution",
     "dit": "Présenter les résultats et les priorités aux décideurs.",
     "chemin": "/contact", "lien": "En parler au cabinet",
     "pourquoi": "Un support de restitution est un texte qui engage celui qui le "
                 "présente ; il se commande, il ne se génère pas."},
]

#: CE QUE L'AUTO-ÉVALUATION NE COUVRE PAS, ET QU'UN ASSESSMENT CONDUIT COUVRE.
#: La page promettait huit domaines dont deux n'ont aucune section de checklist
#: derrière eux — et, symétriquement, oubliait les contrôles d'accès, qui sont
#: la porte la plus empruntée. Les faire disparaître silencieusement aurait
#: réduit la promesse ; les coter sans référentiel écrit aurait fabriqué un
#: chiffre. Ils sont donc NOMMÉS, avec la raison de leur absence.
HORS_PORTEE = [
    {
        "nom": "Continuité & résilience",
        "pourquoi": "La restauration d'une sauvegarde et le repli d'un procédé "
                    "se cotent sur un exercice réellement joué, pas sur une "
                    "déclaration. Le point « sauvegardes restaurées » est dans "
                    "le domaine Protection technique ; la continuité au sens "
                    "large — repli, mode dégradé, délai de reprise tenu — "
                    "demande un exercice observé.",
        "ou_ca_se_constate": "Un exercice de reprise chronométré, avec son "
                             "compte rendu et ce qui a été corrigé après.",
        # HORS PORTÉE DE CE FORMULAIRE N'EST PAS HORS SUJET DU CABINET. Les
        # deux domaines écartés ont chacun leur page : dire « on ne le cote
        # pas » sans dire « voici où c'est traité » transformerait une réserve
        # honnête en fin de non-recevoir.
        "chemin": "/continuite-ot",
        "titre_page": "Continuité & gestion de crise OT",
    },
    {
        "nom": "Culture & compétences",
        "pourquoi": "Aucun document ne prouve qu'une équipe a compris quelque "
                    "chose. Une feuille d'émargement prouve une présence. La "
                    "coter depuis un formulaire donnerait le degré que "
                    "l'organisation souhaite avoir, sans contradiction "
                    "possible.",
        "ou_ca_se_constate": "Des entretiens en dehors de la hiérarchie, et "
                             "ce que fait réellement un opérateur devant une "
                             "clé USB inconnue.",
        "chemin": "/formation",
        "titre_page": "Formation & transfert de compétences",
    },
]


def _verifier():
    """LES DOMAINES DOIVENT RESTER CEUX DE LA CHECKLIST, et chaque jugement
    doit se défendre.

    Un domaine qui s'en détacherait donnerait deux vocabulaires pour la même
    chose sur le même site ; un `gravite` ou un `effort` sans motif écrit
    serait un classement arbitraire présenté comme une méthode.
    """
    sections = {s["cle"] for s in CK.SECTIONS}
    vus = set()
    for d in DOMAINES:
        if d["cle"] not in sections:
            raise ValueError("domaine hors checklist : %s" % d["cle"])
        if d["cle"] in vus:
            raise ValueError("domaine en double : %s" % d["cle"])
        vus.add(d["cle"])
        for champ in ("objet", "gravite_dit", "effort_dit", "cible_dit"):
            if len(str(d.get(champ, "")).strip()) < 60:
                raise ValueError("%s sans %s écrit" % (d["cle"], champ))
        for champ in ("gravite", "effort"):
            if not 1 <= d[champ] <= 5:
                raise ValueError("%s : %s hors 1–5" % (d["cle"], champ))
        if not MINI <= d["cible"] <= MAXI:
            raise ValueError("%s : cible hors échelle" % d["cle"])
    # AUCUNE SECTION DE LA CHECKLIST N'EST OUBLIÉE : un domaine manquant
    # laisserait un pan du terrain hors de l'auto-évaluation sans que rien ne
    # le signale.
    if vus != sections:
        raise ValueError("sections sans domaine : %s" % sorted(sections - vus))
    if [e["n"] for e in ECHELLE] != list(range(MINI, MAXI + 1)):
        raise ValueError("échelle discontinue")
    # UN DOMAINE HORS PORTÉE DOIT DIRE OÙ IL SE CONSTATE. Sans cela, la
    # réserve devient un refus sans suite, et le lecteur n'apprend rien de ce
    # qu'il faudrait faire.
    for h in HORS_PORTEE:
        for champ in ("pourquoi", "ou_ca_se_constate"):
            if len(str(h.get(champ, "")).strip()) < 40:
                raise ValueError("hors portée « %s » sans %s écrit"
                                 % (h.get("nom"), champ))
        if not str(h.get("chemin", "")).startswith("/"):
            raise ValueError("hors portée « %s » sans page où l'adresser"
                             % h.get("nom"))
    # CHAQUE DOMAINE A UNE DESTINATION. Un écart nommé sans endroit où le
    # traiter laisse le lecteur avec un constat — c'est le reproche qu'on fait
    # aux diagnostics, et il est mérité.
    if set(RESSOURCES) != vus:
        raise ValueError("domaines sans ressource : %s"
                         % sorted(vus - set(RESSOURCES)))
    for cle, liens in RESSOURCES.items():
        if not liens:
            raise ValueError("%s : aucune ressource" % cle)
        for l in liens:
            if not str(l.get("chemin", "")).startswith("/"):
                raise ValueError("%s : chemin absent ou relatif" % cle)
            # UN LIEN SANS RAISON ÉCRITE EST UN MENU DÉGUISÉ EN CONSEIL. Le
            # lecteur clique alors au hasard, et la page ne l'a aidé en rien.
            if len(str(l.get("pourquoi", "")).strip()) < 60:
                raise ValueError("%s → %s : sans motif écrit"
                                 % (cle, l.get("chemin")))
            if not str(l.get("titre", "")).strip():
                raise ValueError("%s → %s : sans intitulé" % (cle, l.get("chemin")))
    if [e["n"] for e in DEROULE] != list(range(1, len(DEROULE) + 1)):
        raise ValueError("déroulé discontinu")
    for e in DEROULE:
        if len(str(e.get("pourquoi", "")).strip()) < 60:
            raise ValueError("étape %s du déroulé sans motif écrit" % e.get("n"))
        # UNE ÉTAPE SANS PAGE DOIT DIRE POURQUOI ELLE N'EN A PAS, et non
        # rester muette : « benchmark » sans lien se lirait comme un oubli.
        if e.get("chemin") is not None and not str(e["chemin"]).startswith("/"):
            raise ValueError("étape %s : chemin relatif" % e.get("n"))


_verifier()


def virgule(x):
    """LA VIRGULE DÉCIMALE, PARCE QUE LE DOCUMENT EST EN FRANÇAIS. « 1.5 sur
    5 » dans un rapport français signale une chaîne de production qui n'a pas
    été relue ; le lecteur qui le remarque doute ensuite du reste."""
    if x is None:
        return None
    s = ("%.2f" % float(x)).rstrip("0").rstrip(".")
    return (s or "0").replace(".", ",")


def _domaine(cle):
    return next(d for d in DOMAINES if d["cle"] == cle)


def _nom_section(cle):
    return next(s["nom"] for s in CK.SECTIONS if s["cle"] == cle)


def referentiel():
    """Ce qu'il faut pour dresser le formulaire — servi, jamais recopié dans
    la page : deux tables du même objet divergent au premier ajout."""
    return {
        "version": VERSION,
        "echelle": ECHELLE,
        "mini": MINI, "maxi": MAXI,
        "voisinages": VOISINAGES,
        "ce_que_ce_n_est_pas": REFUS_ASSESSMENT,
        "hors_portee": HORS_PORTEE,
        "deroule": DEROULE,
        "domaines": [
            dict(d, nom=_nom_section(d["cle"]),
                 ressources=RESSOURCES[d["cle"]],
                 dit=next(s["dit"] for s in CK.SECTIONS if s["cle"] == d["cle"]),
                 partie=next(s["partie"] for s in CK.SECTIONS
                             if s["cle"] == d["cle"]))
            for d in DOMAINES
        ],
        "ordre": ORDRE,
    }


def evaluer(niveaux=None, cibles=None):
    """L'ÉCART PAR DOMAINE, ET L'ORDRE DANS LEQUEL LE COMBLER.

    `niveaux` : {domaine: 0–5}, ce que le client déclare tenir.
    `cibles`  : {domaine: 0–5}, facultatif — à défaut, la cible recommandée,
                qui porte sa raison écrite.

    UN DOMAINE NON RENSEIGNÉ N'EST PAS ZÉRO. Zéro est une déclaration ; ne pas
    répondre en est une autre, et les confondre ferait dire au radar que le
    client n'a rien alors qu'il n'a rien DIT.
    """
    niveaux = niveaux or {}
    cibles = cibles or {}
    inconnus = sorted(set(niveaux) - set(ORDRE)) + sorted(set(cibles) - set(ORDRE))
    if inconnus:
        return {"ok": False, "erreur": "domaines_inconnus",
                "message": "Domaine(s) inconnu(s) : %s." % ", ".join(inconnus),
                "connus": list(ORDRE)}

    def borne(v):
        try:
            v = int(v)
        except (TypeError, ValueError):
            return None
        return v if MINI <= v <= MAXI else None

    lignes, repondus = [], 0
    for d in DOMAINES:
        n = borne(niveaux.get(d["cle"]))
        c = borne(cibles.get(d["cle"]))
        # LA CIBLE PAR DÉFAUT EST CELLE QUI SERT RÉELLEMENT. Une cible hors
        # échelle est écartée et la recommandation reprend la main : dire le
        # contraire ferait passer pour un choix du client une valeur qu'il n'a
        # pas obtenue.
        choisie = c is not None
        if c is None:
            c = d["cible"]
        if n is not None:
            repondus += 1
        ecart = None if n is None else max(0, c - n)
        # LA PRIORITÉ CLASSE, ELLE NE NOTE PAS. Un écart qui porte sur un
        # domaine grave et peu coûteux passe devant ; l'effort DIVISE parce
        # qu'un chantier de dix-huit mois ne se met pas en tête d'une feuille
        # de route qu'on veut voir bouger.
        poids = None if ecart is None else round(ecart * d["gravite"] / d["effort"], 2)
        lignes.append({
            "cle": d["cle"], "nom": _nom_section(d["cle"]),
            "objet": d["objet"],
            "niveau": n, "niveau_nom": None if n is None else ECHELLE[n]["nom"],
            "niveau_dit": None if n is None else ECHELLE[n]["dit"],
            "cible": c, "cible_nom": ECHELLE[c]["nom"],
            "cible_par_defaut": not choisie,
            "cible_dit": d["cible_dit"],
            "ecart": ecart,
            "gravite": d["gravite"], "gravite_dit": d["gravite_dit"],
            # LA DESTINATION VOYAGE AVEC L'ÉCART. Servie à part, elle
            # obligerait la page à recroiser deux listes — et c'est au
            # premier ajout de domaine que le croisement se perd.
            "ressources": RESSOURCES[d["cle"]],
            "effort": d["effort"], "effort_dit": d["effort_dit"],
            "poids": poids,
            "section_checklist": d["cle"],
        })

    avec = [l for l in lignes if l["ecart"] is not None]
    a_combler = sorted([l for l in avec if l["ecart"] > 0],
                       key=lambda l: (-l["poids"], l["cle"]))
    atteints = [l for l in avec if l["ecart"] == 0]
    manquants = [l["cle"] for l in lignes if l["niveau"] is None]

    return {
        "ok": True, "version": VERSION,
        "domaines": lignes,
        "repondus": repondus, "sur": len(DOMAINES),
        "manquants": manquants,
        # LA MOYENNE EST SERVIE ET DÉSAMORCÉE DANS LA MÊME RÉPONSE. La taire
        # ne l'empêcherait pas d'être calculée de tête ; la nommer « moyenne
        # des degrés déclarés » lui donne son sens exact.
        "moyenne_declaree": (round(sum(l["niveau"] for l in avec) / len(avec), 2)
                             if avec else None),
        "a_combler": a_combler,
        "atteints": [l["cle"] for l in atteints],
        "ce_que_ce_n_est_pas": REFUS_ASSESSMENT,
        "voisinages": VOISINAGES,
        "hors_portee": HORS_PORTEE,
        "lecture": _lecture(avec, a_combler, manquants),
    }


def _lecture(avec, a_combler, manquants):
    if not avec:
        return ("Aucun domaine n'est renseigné. Cette évaluation se remplit "
                "avec les documents sous les yeux : c'est le seul usage qui "
                "en vaille la peine.")
    if manquants:
        return ("%d domaine(s) sur 6 renseignés. Les autres ne sont pas à "
                "zéro — ils sont sans réponse, et le radar les laisse vides "
                "plutôt que de les compter." % len(avec))
    if not a_combler:
        return ("Tous les domaines déclarés atteignent leur cible. C'est le "
                "moment où une auto-évaluation ne suffit plus : ce qui reste "
                "à savoir est l'écart entre ce qui est déclaré et ce qui se "
                "constate, et cela se mesure sur place.")
    p = a_combler[0]
    return ("%d domaine(s) sous leur cible. Le premier à prendre est « %s » : "
            "écart de %d degré(s) sur un domaine de gravité %d/5 pour un "
            "effort %d/5." % (len(a_combler), p["nom"], p["ecart"],
                              p["gravite"], p["effort"]))


def plan(niveaux=None, cibles=None):
    """LE CHEMIN, DEGRÉ PAR DEGRÉ.

    Une étape n'est pas « passer de 1 à 4 » : c'est passer de 1 à 2, puis de
    2 à 3. Chaque degré a sa description, et c'est elle qui dit ce qu'il faut
    produire — sauter les intermédiaires ferait une feuille de route dont
    aucune ligne ne se termine.
    """
    ev = evaluer(niveaux, cibles)
    if not ev.get("ok"):
        return ev
    etapes = []
    for l in ev["a_combler"]:
        for degre in range(l["niveau"] + 1, l["cible"] + 1):
            etapes.append({
                "domaine": l["cle"], "nom": l["nom"], "objet": l["objet"],
                "de": degre - 1, "vers": degre,
                "vers_nom": ECHELLE[degre]["nom"],
                "ce_qu_il_faut": ECHELLE[degre]["dit"],
                "poids": l["poids"],
                "section_checklist": l["cle"],
            })
    return dict(ev, etapes=etapes, n_etapes=len(etapes))


# ══════════════════════════════════════════════════════════════════════════
#  LES CINQ LIVRABLES DE LA PAGE — ce qui se calcule, et ce qui ne se calcule
#  pas. Un bloc qui promet un document sans dire d'où il sortirait est un
#  bloc décoratif ; celui qui ne peut pas être calculé le dit et nomme ce
#  qu'il faudrait.
# ══════════════════════════════════════════════════════════════════════════
LIVRABLES = {
    "mat-radar": {
        "calculable": True,
        "dit": "Les six degrés déclarés, leurs cibles et l'écart par "
               "domaine — c'est exactement ce que cette page produit.",
    },
    "mat-carto-ecarts": {
        "calculable": True,
        "dit": "Les écarts classés par gravité et effort, avec le motif "
               "écrit de chaque pondération.",
    },
    "mat-plan-montee": {
        "calculable": True,
        "dit": "Le passage degré par degré, avec ce qu'il faut produire à "
               "chacun.",
    },
    "mat-benchmark": {
        "calculable": False,
        "dit": "Un positionnement sectoriel demande des données de secteur : "
               "un panel, une méthode de collecte et une date. Ce site n'en "
               "détient aucune, et un « vous êtes au-dessus de la moyenne » "
               "fabriqué serait la pire ligne du document.",
        "ce_qu_il_faudrait": "Un panel d'au moins vingt installations "
                             "comparables, évaluées sur la même échelle et à "
                             "moins de dix-huit mois — ou l'achat d'une "
                             "étude qui le dise.",
    },
    "mat-restitution-comex": {
        "calculable": False,
        "dit": "Un support de restitution est un texte : il hiérarchise, "
               "choisit ce qu'on tait, et engage celui qui le présente. Rien "
               "de cela ne se dérive de six curseurs.",
        "ce_qu_il_faudrait": "Un consultant qui écrit et signe, à partir de "
                             "cette auto-évaluation et de ce qu'un "
                             "assessment aura constaté sur place.",
    },
}


def livrables(niveaux=None, cibles=None):
    """CE QUE CETTE PAGE PEUT SERVIR AUJOURD'HUI, ET CE QU'ELLE NE PEUT PAS.

    Les cinq blocs de `/maturite-ot` renvoyaient tous vers l'espace
    administrateur : pour un visiteur, la section entière était inerte. Trois
    se calculent depuis ses propres réponses ; deux non, et ils le disent."""
    ev = evaluer(niveaux, cibles)
    ok = ev.get("ok") and ev.get("repondus", 0) > 0
    out = []
    for liv in _livrables_page():
        d = LIVRABLES[liv["id"]]
        out.append({
            "id": liv["id"], "label": liv["label"],
            "calculable": d["calculable"],
            "dit": d["dit"],
            "ce_qu_il_faudrait": d.get("ce_qu_il_faudrait"),
            "pret": bool(d["calculable"] and ok),
        })
    return {"ok": True, "livrables": out,
            "repondus": ev.get("repondus", 0) if ev.get("ok") else 0}


def _livrables_page():
    """Les cinq livrables de la page, LUS DANS `livrables.py` — jamais
    recopiés. Leur intitulé vit là-bas ; une seconde liste ici afficherait un
    titre périmé le jour où l'autre changerait."""
    import livrables as LV
    connus = set(LIVRABLES)
    out = [l for l in LV.TYPES if l["id"] in connus]
    manquants = connus - {l["id"] for l in out}
    if manquants:
        raise ValueError("livrable déclaré ici et absent de livrables.py : %s"
                         % sorted(manquants))
    return out


def markdown(niveaux=None, cibles=None, titre=None):
    """L'auto-évaluation, l'écart et le plan — en Markdown, pour `build_docx`
    et `build_pdf` qui portent la charte de la maison."""
    d = plan(niveaux, cibles)
    if not d.get("ok"):
        return None
    L = []
    A = L.append
    A("# %s" % (titre or "Auto-évaluation de maturité OT"))
    A("")
    A("> **Ce que ce document n'est pas.** %s" % REFUS_ASSESSMENT)
    A("")
    A("## Où vous situez-vous")
    A("")
    A(d["lecture"])
    A("")
    if d["moyenne_declaree"] is not None:
        A("Moyenne des degrés **déclarés** : %s sur 5. Ce n'est pas une note : "
          "un domaine grave à 1 et un domaine mineur à 5 donnent la même "
          "moyenne que l'inverse, et ce n'est pas la même installation."
          % virgule(d["moyenne_declaree"]))
        A("")
    A("| Domaine | Déclaré | Cible | Écart | Gravité | Effort |")
    A("| --- | --- | --- | --- | --- | --- |")
    for l in d["domaines"]:
        A("| %s | %s | %d — %s | %s | %d/5 | %d/5 |"
          % (l["nom"],
             "— (sans réponse)" if l["niveau"] is None
             else "%d — %s" % (l["niveau"], l["niveau_nom"]),
             l["cible"], l["cible_nom"],
             "—" if l["ecart"] is None else str(l["ecart"]),
             l["gravite"], l["effort"]))
    A("")
    A("## L'échelle employée")
    A("")
    for e in ECHELLE:
        A("- **%d — %s.** %s" % (e["n"], e["nom"], e["dit"]))
    A("")
    A("*%s*" % VOISINAGES)
    A("")
    if d["a_combler"]:
        A("## Ce qui est sous la cible, dans l'ordre")
        A("")
        A("L'ordre vient de la gravité du domaine divisée par l'effort qu'il "
          "demande — un jugement de ce cabinet, motivé domaine par domaine "
          "ci-dessous. Il classe un ordre de passage ; il ne note personne.")
        A("")
        for l in d["a_combler"]:
            A("**%s** — écart de %d degré(s).  " % (l["nom"], l["ecart"]))
            A("*Gravité %d/5.* %s  " % (l["gravite"], l["gravite_dit"]))
            A("*Effort %d/5.* %s  " % (l["effort"], l["effort_dit"]))
            A("*Cible %d — %s.* %s  " % (l["cible"], l["cible_nom"], l["cible_dit"]))
            A("")
    if d["etapes"]:
        A("## Le plan, degré par degré")
        A("")
        A("Une étape n'est pas « passer de 1 à 4 » : c'est passer de 1 à 2, "
          "puis de 2 à 3. Sauter les intermédiaires ferait une feuille de "
          "route dont aucune ligne ne se termine.")
        A("")
        for e in d["etapes"]:
            A("**%s — du degré %d au degré %d (%s)**  "
              % (e["nom"], e["de"], e["vers"], e["vers_nom"]))
            A("Porte sur %s.  " % e["objet"])
            A("*Ce qu'il faut pouvoir montrer :* %s  " % e["ce_qu_il_faut"])
            A("")
    A("## Les deux domaines que ce formulaire ne cote pas")
    A("")
    A("Ils ne sont pas absents du sujet : ils sont absents de ce qui se "
      "déclare. Un assessment conduit les couvre.")
    A("")
    for h in HORS_PORTEE:
        A("- **%s.** %s *Où cela se constate :* %s"
          % (h["nom"], h["pourquoi"], h["ou_ca_se_constate"]))
    A("")
    A("## Ce que cette auto-évaluation ne produit pas")
    A("")
    for liv in livrables(niveaux, cibles)["livrables"]:
        if liv["calculable"]:
            continue
        A("- **%s.** %s *Ce qu'il faudrait :* %s"
          % (liv["label"], liv["dit"], liv["ce_qu_il_faudrait"]))
    A("")
    A("*Auto-évaluation version %s · échelle à six degrés propre à ce "
      "cabinet.*" % VERSION)
    return "\n".join(L)


def sante():
    return {
        "module": "maturite_ot",
        "version": VERSION,
        "portee": "Structure une AUTO-ÉVALUATION déclarative de maturité OT "
                  "sur six domaines et six degrés, calcule l'écart à la cible "
                  "et le plan degré par degré. Ne conduit aucun assessment et "
                  "n'en rend aucun résultat.",
        "domaines": len(DOMAINES),
        "degres": len(ECHELLE),
        "domaines_alignes_sur_la_checklist": ORDRE == [s["cle"] for s in CK.SECTIONS],
        "livrables_calculables": sorted(k for k, v in LIVRABLES.items()
                                        if v["calculable"]),
        "livrables_non_calculables": sorted(k for k, v in LIVRABLES.items()
                                            if not v["calculable"]),
        "hors_portee": [h["nom"] for h in HORS_PORTEE],
        "modeles_de_langage": 0,
    }
