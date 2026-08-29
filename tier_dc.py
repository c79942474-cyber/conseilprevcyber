"""La qualification Tier d'un site — ce que la topologie permet d'atteindre.

CE QUE CE MODULE EST. Les règles de composition du référentiel Tier de l'Uptime
Institute, portées en français et rendues CALCULABLES. Il répond à une question
que la plateforme laissait sans réponse : « au vu de ce qui est réellement
installé, quel niveau ce site peut-il revendiquer, et qu'est-ce qui l'en
empêche ? »

CE QU'IL N'EST PAS, ET IL FAUT LE LIRE AVANT LE RESTE. Il ne décerne aucun
niveau. Un niveau Tier est CERTIFIÉ par l'Uptime Institute sur dossier, et la
certification porte séparément sur les documents de conception et sur l'ouvrage
construit — l'une ne vaut pas l'autre. Ce module dit ce qu'un niveau EXIGE et
calcule ce que la topologie décrite permettrait de revendiquer. Un site n'est
pas Tier III parce que ce module l'affiche.

LA RÈGLE QUI CHANGE TOUT, ET QUI MANQUAIT. Le niveau d'un site est le NIVEAU LE
PLUS BAS de ses sous-systèmes. Pas leur moyenne. Il n'existe pas de niveau
fractionnaire, pas de « Tier III et demi », pas de « Tier III sauf sur le
froid ». Une chaîne électrique tolérante à la panne desservie par une production
de froid à chemin unique fait un site Tier I — et c'est exactement le dossier
qu'on voit se présenter comme Tier IV parce qu'on a regardé le lot le plus
soigné.

UN STANDARD FONDÉ SUR LES RÉSULTATS, PAS SUR UNE LISTE DE MATÉRIEL. Les niveaux
se démontrent par des essais dont l'issue est observable — retirer un composant
du service sans couper l'informatique, provoquer un défaut et constater que la
charge tient. Beaucoup de conceptions qui passent une liste de contrôle échouent
à cette épreuve, et c'est le sens de la distinction : on ne compte pas des
onduleurs, on éprouve un comportement.

D'OÙ VIENNENT CES RÈGLES. Du référentiel Tier Standard « Topology » de l'Uptime
Institute. Elles sont REFORMULÉES — aucune phrase du document n'est reproduite,
conformément à la discipline déjà appliquée aux textes normatifs dans ce dépôt
et à la clause de droit d'auteur du document lui-même, qui exige une
autorisation écrite pour toute reproduction. Ce qui est encodé ici, ce sont des
règles d'ingénierie, dans nos mots ; le texte de référence se lit chez son
auteur.
"""

import math

VERSION = "2026-08-a"

SOURCE = (
    "Règles de composition reformulées d'après le référentiel Tier Standard "
    "« Topology » de l'Uptime Institute. Aucun extrait du document n'est "
    "reproduit ici : ce module encode des règles d'ingénierie dans ses propres "
    "termes. Le texte de référence, ses définitions exactes et ses éventuelles "
    "révisions se consultent chez son auteur.")

RESERVE = (
    "AUCUN NIVEAU N'EST DÉCERNÉ ICI. Ce calcul dit ce que la topologie DÉCRITE "
    "permettrait de revendiquer, sur les seules données saisies. La "
    "certification est délivrée par l'Uptime Institute sur dossier, et elle "
    "porte séparément sur les documents de conception et sur l'ouvrage "
    "construit — l'une ne vaut pas l'autre. Un dossier « conçu selon les "
    "principes du niveau III » n'est pas certifié, et l'écrire autrement dans "
    "une plaquette est un risque contractuel.")


# ═══════════════════════════════════════════════════════════════════════════
#  1. CE QUE CHAQUE NIVEAU EXIGE
# ═══════════════════════════════════════════════════════════════════════════
# LA DISTINCTION QUE CETTE TABLE PORTE, ET QU'ON MANQUE LE PLUS SOUVENT : le
# BACKBONE ÉLECTRIQUE et la DISTRIBUTION CRITIQUE n'ont pas la même exigence au
# niveau III.
#
#   · le backbone électrique va de la sortie de la production sur site jusqu'à
#     l'entrée des onduleurs, et alimente aussi les équipements mécaniques
#     critiques. Au niveau III, un seul de ses chemins a besoin de desservir à
#     un instant donné : un actif, un alterné ;
#
#   · la distribution critique va de la SORTIE DES ONDULEURS jusqu'aux baies.
#     Au niveau III, elle exige DEUX chemins simultanément actifs.
#
# Écrire « niveau III : plusieurs chemins dont un seul actif » sans cette
# nuance — ce que faisait cette plateforme — décrit correctement le backbone et
# faussement la distribution critique. C'est la faute qui se découvre en revue
# de conception, quand la moitié du câblage terminal est à refaire.

EXIGENCES = {
    "I": {
        "nom": "Tier I — infrastructure de base",
        "rang": 1,
        "capacite_min": "N",
        "capacite_aide": "Le strict besoin, sans composant de réserve.",
        "backbone": 1,
        "backbone_aide": "Un chemin unique de la production sur site aux "
                         "onduleurs et aux équipements mécaniques critiques.",
        "distribution_critique": 1,
        "distribution_aide": "Un chemin unique de la sortie des onduleurs aux "
                             "baies.",
        "maintenable_sans_interruption": False,
        "tolerant_panne": False,
        "compartimente": False,
        "froid_continu": False,
        "autonomie_h": 12,
        "posture": "tactique",
        "posture_aide": "Retenu pour un besoin de court terme : le premier "
                        "coût et le délai de mise sur le marché pèsent plus "
                        "que le coût global et la disponibilité.",
    },
    "II": {
        "nom": "Tier II — composants de capacité redondants",
        "rang": 2,
        "capacite_min": "N+1",
        "capacite_aide": "Des composants de réserve — production sur site, "
                         "onduleurs et stockage, groupes froid, rejet de "
                         "chaleur, pompes, unités de traitement d'air, cuves.",
        "backbone": 1,
        "backbone_aide": "Un chemin unique, malgré les composants redondants. "
                         "C'est le chemin, et non les machines, qui limite le "
                         "niveau.",
        "distribution_critique": 1,
        "distribution_aide": "Un chemin unique jusqu'aux baies.",
        "maintenable_sans_interruption": False,
        "tolerant_panne": False,
        "compartimente": False,
        "froid_continu": False,
        "autonomie_h": 12,
        "posture": "tactique",
        "posture_aide": "Même logique de court terme que le niveau I, avec "
                        "une marge sur les machines. L'arrêt annuel pour "
                        "entretien reste nécessaire.",
    },
    "III": {
        "nom": "Tier III — maintenable sans interruption",
        "rang": 3,
        "capacite_min": "N+1",
        "capacite_aide": "Des composants de réserve, ET des chemins de "
                         "distribution multiples et indépendants.",
        "backbone": 2,
        "backbone_actifs": 1,
        "backbone_aide": "Deux chemins, dont un seul a besoin de desservir à "
                         "un instant donné : un actif, un alterné. Vaut aussi "
                         "pour la distribution mécanique — les réseaux qui "
                         "évacuent la chaleur de la salle vers l'extérieur.",
        "distribution_critique": 2,
        "distribution_critique_actifs": 2,
        "distribution_aide": "DEUX chemins simultanément actifs de la sortie "
                             "des onduleurs aux baies. C'est ici que le "
                             "niveau III diffère de ce qu'on en retient "
                             "d'ordinaire.",
        "maintenable_sans_interruption": True,
        "tolerant_panne": False,
        "compartimente": False,
        "froid_continu": False,
        "autonomie_h": 12,
        "informatique_bi_alimentee": True,
        "posture": "strategique",
        "posture_aide": "Retenu quand la disponibilité et la durée de vie "
                        "priment : l'infrastructure survit au besoin "
                        "informatique qui l'a justifiée, et laisse arbitrer la "
                        "croissance sans être contraint par la topologie.",
    },
    "IV": {
        "nom": "Tier IV — tolérant à la panne",
        "rang": 4,
        "capacite_min": "N après toute panne",
        "capacite_aide": "L'exigence porte sur le RÉSULTAT : après n'importe "
                         "quelle défaillance, la capacité restante doit encore "
                         "assurer N en puissance et en froid. Le 2N est un "
                         "moyen d'y parvenir, pas l'exigence.",
        "backbone": 2,
        "backbone_actifs": 2,
        "backbone_aide": "Deux chemins simultanément actifs, indépendants et "
                         "physiquement séparés.",
        "distribution_critique": 2,
        "distribution_critique_actifs": 2,
        "distribution_aide": "Deux chemins simultanément actifs jusqu'aux "
                             "baies.",
        "maintenable_sans_interruption": True,
        "tolerant_panne": True,
        "compartimente": True,
        "froid_continu": True,
        "autonomie_h": 12,
        "informatique_bi_alimentee": True,
        "posture": "strategique",
        "posture_aide": "Le niveau des exploitations qui ne peuvent pas "
                        "planifier d'arrêt. Une activité de maintenance qui "
                        "met une chaîne hors service expose le site le temps "
                        "de l'intervention — sans faire perdre le niveau, qui "
                        "se juge en fonctionnement normal.",
    },
}

ORDRE = ["I", "II", "III", "IV"]


# ═══════════════════════════════════════════════════════════════════════════
#  2. CE QUI SE DÉMONTRE, ET CE QUE L'EXPLOITANT VIT
# ═══════════════════════════════════════════════════════════════════════════
# POURQUOI LES DEUX SONT SÉPARÉS. Les essais de confirmation sont ce que le
# commissioning agent doit PROUVER — ils se contractualisent, se planifient et
# se constatent. Les impacts d'exploitation sont ce que le client VIVRA — ils
# se vendent, ou plutôt ils s'annoncent avant de se découvrir.
#
# La colonne des essais est la plus utile de tout le module : c'est elle qui
# transforme un niveau annoncé en programme d'essais opposable. Un niveau écrit
# au marché sans les essais qui le démontrent est une clause invérifiable.

ESSAIS_CONFIRMATION = {
    "I": [
        "La capacité installée suffit au besoin du site.",
        "Toute intervention programmée impose d'arrêter tout ou partie de "
        "l'infrastructure, et donc l'informatique.",
    ],
    "II": [
        "Un composant de réserve se retire du service de façon programmée sans "
        "arrêter l'informatique.",
        "Retirer un chemin de distribution du service impose en revanche "
        "d'arrêter l'informatique.",
        "La capacité installée à demeure suffit au besoin quand un composant "
        "de réserve est hors service, quelle qu'en soit la raison.",
    ],
    "III": [
        "Chaque composant de capacité et chaque élément des chemins de "
        "distribution se retire du service de façon programmée sans impact sur "
        "l'informatique.",
        "La capacité restante suffit au besoin pendant qu'un composant ou un "
        "chemin est hors service.",
        "L'informatique est bi-alimentée, ou dotée de commutateurs au point "
        "d'usage là où elle ne l'est pas.",
    ],
    "IV": [
        "Une défaillance unique — d'un système, d'un composant ou d'un élément "
        "de distribution — n'a aucun impact sur l'informatique.",
        "L'automatisme de conduite réagit seul à une défaillance et maintient "
        "l'informatique.",
        "Chaque composant et chaque élément des chemins se retire du service "
        "de façon programmée sans impact sur l'informatique.",
        "La capacité restante suffit au besoin quand des composants ou un "
        "chemin sont hors service.",
        "Tout défaut potentiel se détecte, s'isole et se confine en maintenant "
        "la capacité N sur la charge critique.",
    ],
}

IMPACTS_EXPLOITATION = {
    "I": [
        "Le site est exposé aux interruptions, programmées comme non "
        "programmées. Une erreur humaine sur un composant d'infrastructure "
        "interrompt le service.",
        "La défaillance de n'importe quel système, composant ou élément de "
        "distribution atteint l'informatique.",
        "L'infrastructure doit être entièrement arrêtée une fois par an pour "
        "l'entretien préventif. Y renoncer augmente le risque d'interruption "
        "ET la gravité de la panne qui suivra.",
    ],
    "II": [
        "Le site reste exposé aux interruptions programmées et non "
        "programmées ; une erreur humaine peut encore interrompre le service.",
        "La défaillance d'un composant redondé peut être absorbée ; celle d'un "
        "système ou d'un élément de distribution ne l'est pas.",
        "L'arrêt annuel complet pour entretien reste nécessaire.",
    ],
    "III": [
        "L'entretien programmé ne coupe plus le service : c'est ce que le "
        "niveau achète, et c'est tout ce qu'il achète.",
        "Un défaut NON PROGRAMMÉ peut encore interrompre le service. "
        "Maintenable sans interruption ne veut pas dire tolérant à la panne, "
        "et confondre les deux est la promesse commerciale la plus "
        "fréquemment démentie par les faits.",
    ],
    "IV": [
        "Le site n'est pas exposé à l'interruption par un événement non "
        "programmé unique.",
        "Le site n'est pas exposé à l'interruption par une activité "
        "programmée.",
        "L'entretien se conduit en s'appuyant sur les composants et les "
        "chemins redondants pour intervenir en sécurité sur le reste.",
        "PENDANT cet entretien, le site est exposé si une défaillance survient "
        "sur le chemin restant. Cette configuration temporaire ne fait pas "
        "perdre le niveau, qui se juge en fonctionnement normal — mais elle "
        "se planifie, et le client doit le savoir.",
        "Le déclenchement de l'alarme incendie, de l'extinction automatique ou "
        "de l'arrêt d'urgence peut interrompre le service, quel que soit le "
        "niveau.",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
#  3. LES SOUS-SYSTÈMES DONT LA NOTE DÉCIDE DE CELLE DU SITE
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE CETTE LISTE SERT. Le niveau d'un site est le plus bas de ses
# sous-systèmes — encore faut-il savoir lesquels compter. Une liste courte ferait
# oublier ceux qu'on note rarement, et ce sont précisément eux qui limitent : le
# stockage de combustible, l'eau d'appoint, les télécommunications.

SOUS_SYSTEMES = {
    "prod_elec": {
        "nom": "Production électrique sur site",
        "aide": "Groupes électrogènes ou piles à combustible. Ils sont la "
                "source PRIMAIRE du site : le réseau public est une "
                "alternative économique, pas une source qualifiante.",
    },
    "backbone_elec": {
        "nom": "Backbone électrique",
        "aide": "De la sortie de la production sur site à l'entrée des "
                "onduleurs, et l'alimentation des équipements mécaniques "
                "critiques.",
    },
    "distribution_critique": {
        "nom": "Distribution critique",
        "aide": "De la sortie des onduleurs aux baies. C'est le sous-système "
                "dont l'exigence de niveau III est la plus souvent mal lue : "
                "deux chemins simultanément actifs, pas un actif et un "
                "alterné.",
    },
    "onduleurs": {
        "nom": "Onduleurs et stockage d'énergie",
        "aide": "Ils tiennent la charge entre la perte du réseau et la reprise "
                "par la production sur site.",
    },
    "prod_froid": {
        "nom": "Production de froid",
        "aide": "Groupes froid, tours, échangeurs. Une chaîne électrique "
                "tolérante à la panne desservie par une production de froid à "
                "chemin unique fait un site de niveau I.",
    },
    "distribution_meca": {
        "nom": "Distribution mécanique",
        "aide": "Les réseaux qui évacuent la chaleur de la salle vers "
                "l'extérieur — eau glacée, eau de condensation, fluide "
                "frigorigène. Au niveau III, un chemin actif et un alterné "
                "suffisent.",
    },
    "combustible": {
        "nom": "Stockage de combustible",
        "aide": "Douze heures d'autonomie à la capacité N sont exigées à tous "
                "les niveaux. Aux niveaux III et IV, le circuit "
                "d'alimentation doit lui aussi tenir l'exigence du niveau.",
    },
    "eau_appoint": {
        "nom": "Eau d'appoint",
        "aide": "Sur tout site à refroidissement évaporatif, douze heures de "
                "réserve sur site sont exigées. Aux niveaux III et IV, le "
                "système d'appoint doit tenir l'exigence du niveau jusqu'au "
                "point de livraison, sur cette durée.",
        "si": "evaporatif",
    },
    "telecom": {
        "nom": "Télécommunications",
        "aide": "Les équipements des points de raccordement opérateur doivent "
                "être alimentés et refroidis au niveau visé dès lors qu'ils "
                "sont critiques. Au niveau IV, ils relèvent aussi du "
                "compartimentage.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  4. LES RÈGLES DURES
# ═══════════════════════════════════════════════════════════════════════════
# CE QUI DISTINGUE CES SEPT-LÀ DU RESTE : chacune RENVERSE une hypothèse
# courante, et chacune se vérifie sur un dossier. Ce sont celles qui font
# perdre une certification à un projet qui se croyait conforme.

REGLES = {
    "plus_bas_sous_systeme": {
        "nom": "Le niveau du site est le plus bas de ses sous-systèmes",
        "interdit": "Toute moyenne, toute note partielle, tout niveau "
                    "fractionnaire. Il n'existe pas de « niveau III et demi », "
                    "ni de « niveau III sauf sur le froid ».",
        "hypothese_renversee": "On juge un site sur son lot le plus soigné — "
                               "en général l'électricité, parce que c'est là "
                               "que le budget est passé. Le site vaut ce que "
                               "vaut son maillon le plus faible, et c'est "
                               "souvent la distribution mécanique ou l'eau "
                               "d'appoint.",
        "verifier": "Notez chaque sous-système séparément, puis prenez le "
                    "minimum. Si un sous-système n'est pas noté, le résultat "
                    "est un plafond, pas un verdict.",
    },
    "reseau_non_qualifiant": {
        "nom": "Le réseau public n'est pas une source qualifiante",
        "interdit": "Compter une arrivée publique — électricité, eau, gaz, "
                    "froid urbain — comme un chemin ou une source au titre du "
                    "niveau. Tout service provenant d'au-delà de la limite de "
                    "propriété et hors du contrôle de l'exploitant est traité "
                    "comme non fiable.",
        "hypothese_renversee": "« Nous avons deux arrivées, donc nous sommes "
                               "redondants. » Deux arrivées publiques ne "
                               "comptent pour aucun niveau, même issues de "
                               "postes sources distincts. La production sur "
                               "site est la source primaire ; le réseau est "
                               "une alternative économique.",
        "verifier": "La perte du service doit être détectée et reprise par les "
                    "moyens du site SANS intervention humaine, et les systèmes "
                    "interrompus doivent redémarrer seuls au retour.",
    },
    "pas_de_mtbf": {
        "nom": "Un niveau ne se déduit pas d'un calcul de fiabilité",
        "interdit": "Revendiquer un niveau à partir d'un temps moyen entre "
                    "défaillances, d'une disponibilité prévisionnelle en "
                    "pourcentage, ou de tout autre agrégat statistique.",
        "hypothese_renversee": "« Notre étude donne 99,995 %, donc niveau "
                               "IV. » Le niveau qualifie une TOPOLOGIE et se "
                               "démontre par des essais dont l'issue est "
                               "observable, pas par un nombre.",
        "verifier": "Demandez le protocole d'essai, pas la note de calcul.",
    },
    "groupe_illimite": {
        "nom": "Aux niveaux III et IV, le groupe ne peut pas être limité en "
               "heures consécutives",
        "interdit": "Retenir, pour un niveau III ou IV, un groupe dont le "
                    "constructeur limite le nombre d'heures consécutives à la "
                    "puissance demandée.",
        "hypothese_renversee": "On dimensionne sur la plaque signalétique. Or "
                               "la classe de service décide : une puissance "
                               "dite de secours n'est pas une puissance "
                               "continue, et un même moteur n'annonce pas le "
                               "même chiffre selon la classe.",
        "verifier": "La classe ISO 8528-1 retenue, et la capacité que le "
                    "constructeur certifie pour un fonctionnement de durée "
                    "illimitée. Une limite réglementaire d'heures annuelles "
                    "pour émissions ne lève PAS cette exigence : ce sont deux "
                    "contraintes distinctes.",
    },
    "conditions_extremes": {
        "nom": "Les capacités se déterminent aux conditions extrêmes",
        "interdit": "Dimensionner sur une valeur de température dépassée un "
                    "certain pourcentage du temps, comme on le fait pour un "
                    "bâtiment ordinaire.",
        "hypothese_renversee": "Une valeur dépassée 2 % du temps semble "
                               "prudente. Elle laisse l'équipement "
                               "sous-dimensionné environ 175 heures par an — "
                               "et ces heures ne sont pas une semaine "
                               "d'affilée : ce sont quelques heures chaque "
                               "après-midi pendant un ou deux mois. Même une "
                               "valeur à 0,4 %, tenue pour conservatrice, "
                               "laisse une trentaine d'heures de "
                               "sous-capacité.",
        "verifier": "Les capacités constructeur corrigées de la température "
                    "et de l'altitude réelles du site, aux extrêmes annuels "
                    "sur vingt ans, en bulbe sec ET en bulbe humide. Et le "
                    "minimum : beaucoup de groupes froid à condensation par "
                    "air ne démarrent pas sous une certaine température.",
    },
    "informatique_bi_alimentee": {
        "nom": "Aux niveaux III et IV, l'informatique doit être bi-alimentée",
        "interdit": "Raccorder un équipement à alimentation simple sur une "
                    "distribution à deux chemins sans commutateur au point "
                    "d'usage.",
        "hypothese_renversee": "On double la distribution et on considère le "
                               "sujet clos. Le matériel réseau et les baies de "
                               "stockage anciennes restent souvent en "
                               "alimentation simple, et ramènent le point "
                               "unique jusque dans la baie.",
        "verifier": "L'inventaire des équipements à alimentation simple, et "
                    "les commutateurs prévus pour eux — sachant qu'un "
                    "commutateur devient à son tour un organe unique.",
    },
    "autonomie_douze_heures": {
        "nom": "Douze heures d'autonomie sur site, à la capacité N",
        "interdit": "Compter sur un contrat de réapprovisionnement pour tenir "
                    "l'autonomie exigée.",
        "hypothese_renversee": "« Nous serons livrés en quatre heures. » En "
                               "crise régionale, la file d'attente est la même "
                               "pour tout le monde, et l'exigence porte sur ce "
                               "qui est STOCKÉ.",
        "verifier": "Le volume réellement stocké, volume mort déduit, rapporté "
                    "à la consommation à la capacité N. Et, sur un site à "
                    "refroidissement évaporatif, la réserve d'eau d'appoint "
                    "sur la même durée.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  LA QUALIFICATION
# ═══════════════════════════════════════════════════════════════════════════

def _rang(niveau):
    e = EXIGENCES.get(str(niveau or "").upper().strip())
    return e["rang"] if e else None


def qualifier(sous_systemes, evaporatif=False):
    """Le niveau que la topologie décrite permettrait de revendiquer.

    `sous_systemes` : un dict {clé de SOUS_SYSTEMES → niveau ("I".."IV")}. Une
    clé absente, vide ou inconnue vaut NON ÉVALUÉE — jamais conforme.

    CE QUE CETTE FONCTION REFUSE DE FAIRE, et c'est sa raison d'être : une
    moyenne. Le niveau du site est le MINIMUM des sous-systèmes notés. Un
    sous-système non noté ne se comble pas par optimisme : tant qu'il en reste
    un, le résultat est un PLAFOND — « au mieux ce niveau » — et non un
    verdict.
    """
    sous_systemes = sous_systemes if isinstance(sous_systemes, dict) else {}
    attendus = [c for c, s in SOUS_SYSTEMES.items()
                if s.get("si") != "evaporatif" or evaporatif]
    notes, absents, inconnus = {}, [], []
    for cle in attendus:
        brut = sous_systemes.get(cle)
        code = str(brut or "").upper().strip()
        if not code:
            absents.append(cle)
            continue
        if code not in EXIGENCES:
            inconnus.append({"sous_systeme": cle, "saisi": str(brut)[:20]})
            absents.append(cle)
            continue
        notes[cle] = code

    # Les sous-systèmes hors périmètre — l'eau d'appoint sur un site sec —
    # sont dits, pour qu'une absence ne se lise pas comme un oubli.
    hors_perimetre = [c for c in SOUS_SYSTEMES if c not in attendus]

    if not notes:
        return {
            "version": VERSION,
            "niveau": None,
            "evalue": False,
            "pourquoi": ("Aucun sous-système n'est noté. Un niveau de site est "
                         "le plus bas de ses sous-systèmes : sans aucune note, "
                         "il n'y a rien à minorer."),
            "sous_systemes": _detail([], notes, absents, hors_perimetre),
            "non_evalues": absents,
            "inconnus": inconnus,
            "plafond": True,
            "reserve": RESERVE,
            "source": SOURCE,
        }

    rang_min = min(_rang(n) for n in notes.values())
    niveau = ORDRE[rang_min - 1]
    limitants = sorted(c for c, n in notes.items() if _rang(n) == rang_min)
    return {
        "version": VERSION,
        "niveau": niveau,
        "niveau_nom": EXIGENCES[niveau]["nom"],
        "evalue": True,
        # LE PLAFOND, ET NON LE VERDICT. Tant qu'un sous-système attendu n'est
        # pas noté, il peut être plus bas que tous les autres : le niveau rendu
        # ne peut que descendre.
        "plafond": bool(absents),
        "limitants": [{"cle": c, "nom": SOUS_SYSTEMES[c]["nom"],
                       "niveau": notes[c]} for c in limitants],
        "sous_systemes": _detail(limitants, notes, absents, hors_perimetre),
        "non_evalues": absents,
        "inconnus": inconnus,
        "exigences": dict(EXIGENCES[niveau]),
        "essais": list(ESSAIS_CONFIRMATION[niveau]),
        "impacts": list(IMPACTS_EXPLOITATION[niveau]),
        "lecture": _lecture(niveau, limitants, notes, absents),
        "regle": REGLES["plus_bas_sous_systeme"],
        "reserve": RESERVE,
        "source": SOURCE,
    }


def _detail(limitants, notes, absents, hors_perimetre):
    out = []
    for cle, s in SOUS_SYSTEMES.items():
        if cle in hors_perimetre:
            out.append({"cle": cle, "nom": s["nom"], "aide": s["aide"],
                        "etat": "hors_perimetre",
                        "pourquoi": "Sans refroidissement évaporatif, ce "
                                    "sous-système n'a pas lieu d'être noté."})
        elif cle in notes:
            out.append({"cle": cle, "nom": s["nom"], "aide": s["aide"],
                        "etat": "note", "niveau": notes[cle],
                        "limitant": cle in limitants})
        else:
            out.append({"cle": cle, "nom": s["nom"], "aide": s["aide"],
                        "etat": "non_evalue",
                        "pourquoi": "Non noté. Ce n'est pas « conforme » : "
                                    "c'est « inconnu », et il peut être plus "
                                    "bas que tous les autres."})
    return out


def _lecture(niveau, limitants, notes, absents):
    """La phrase qui se lit en premier, et qui doit dire l'essentiel.

    ELLE NOMME LE SOUS-SYSTÈME LIMITANT. « Votre site est de niveau I » sans
    dire lequel des neuf le tire vers le bas n'aide personne — alors que « le
    site est de niveau I parce que la distribution mécanique l'est » se traite
    en une réunion.
    """
    noms = ", ".join(SOUS_SYSTEMES[c]["nom"] for c in limitants)
    bouts = ["Le site relève du %s, parce que %s %s à ce niveau."
             % (EXIGENCES[niveau]["nom"], noms,
                "y est" if len(limitants) == 1 else "y sont")]
    meilleurs = [c for c, n in notes.items() if _rang(n) > _rang(niveau)]
    if meilleurs:
        bouts.append("Les %d autre(s) sous-système(s) notés sont plus haut : "
                     "leur avance ne remonte pas le site, elle est payée sans "
                     "être obtenue." % len(meilleurs))
    if absents:
        bouts.append("%d sous-système(s) ne sont pas notés. Ce résultat est "
                     "donc un PLAFOND : il ne peut que descendre."
                     % len(absents))
    return " ".join(bouts)


def ecart_au_vise(sous_systemes, vise, evaporatif=False):
    """Ce qui manque pour atteindre un niveau visé, sous-système par sous-système.

    POURQUOI CETTE FONCTION EXISTE À CÔTÉ DE `qualifier`. Savoir qu'on est au
    niveau I ne dit pas quoi faire. Savoir que six sous-systèmes sur neuf
    tiennent déjà le niveau III et que trois manquent — ceux-là — se traduit
    directement en plan d'action et en chiffrage.
    """
    code = str(vise or "").upper().strip()
    if code not in EXIGENCES:
        return {"vise": None,
                "pourquoi": "Niveau visé inconnu : %s. Les niveaux sont %s."
                            % (vise, ", ".join(ORDRE))}
    q = qualifier(sous_systemes, evaporatif)
    r_vise = EXIGENCES[code]["rang"]
    manquants, tiennent = [], []
    for s in q["sous_systemes"]:
        if s["etat"] == "hors_perimetre":
            continue
        if s["etat"] == "non_evalue":
            manquants.append(dict(s, ecart="non évalué"))
        elif _rang(s["niveau"]) < r_vise:
            manquants.append(dict(s, ecart="%s au lieu de %s"
                                  % (s["niveau"], code)))
        else:
            tiennent.append(s)
    return {
        "vise": code,
        "vise_nom": EXIGENCES[code]["nom"],
        "atteint": q["niveau"],
        "conforme": bool(q["evalue"] and _rang(q["niveau"]) >= r_vise
                         and not q["plafond"]),
        "manquants": manquants,
        "tiennent": tiennent,
        "essais_a_demontrer": list(ESSAIS_CONFIRMATION[code]),
        "exigences": dict(EXIGENCES[code]),
        "lecture": _lecture_ecart(code, manquants, tiennent, q),
        "reserve": RESERVE,
    }


def _lecture_ecart(code, manquants, tiennent, q):
    if not manquants:
        return ("Tous les sous-systèmes évalués tiennent le %s. Reste à le "
                "DÉMONTRER : le niveau se constate par des essais dont l'issue "
                "est observable, pas par une liste de matériel."
                % EXIGENCES[code]["nom"])
    return ("%d sous-système(s) sur %d n'atteignent pas le %s. Ce sont eux, et "
            "eux seuls, qui décident : porter les %d autres plus haut ne "
            "remonte rien."
            % (len(manquants), len(manquants) + len(tiennent),
               EXIGENCES[code]["nom"], len(tiennent)))


# ═══════════════════════════════════════════════════════════════════════════
#  LES GROUPES ÉLECTROGÈNES — CE QUI COMPTE VRAIMENT
# ═══════════════════════════════════════════════════════════════════════════
# LA RÈGLE, ET POURQUOI ELLE SURPREND. Aux niveaux III et IV, un groupe ne doit
# pas être limité en heures consécutives à la puissance demandée. Or la classe
# de service décide de cette limite, et la plaque signalétique annonce une
# puissance qui dépend de la classe :
#
#   · CONTINU — durée illimitée à la puissance nominale. Éligible tel quel ;
#   · PRIME — durée limitée à la puissance nominale. Pour un usage illimité, la
#     capacité se déclasse ; le référentiel de classes retient un ordre de
#     grandeur de 70 %, et le constructeur peut certifier une autre valeur, plus
#     haute ou plus basse ;
#   · SECOURS — limité en heures annuelles par définition. Ne répond pas à
#     l'exigence, sauf certification constructeur d'une capacité tenable sans
#     limite de durée.
#
# CE QUE LE MODULE FAIT DE LA VALEUR CERTIFIÉE : elle l'emporte TOUJOURS sur le
# déclassement par défaut, et le résultat dit laquelle a servi. Un déclassement
# forfaitaire appliqué en silence sur un groupe dont le constructeur certifie
# mieux ferait acheter une machine de trop.

CLASSES_GROUPE = {
    "continu": {
        "nom": "Continu",
        "illimite": True,
        "part": 1.0,
        "eligible_iii_iv": True,
        "aide": "Fonctionnement de durée illimitée à la puissance nominale. "
                "La classe la plus chère à l'achat, et la seule qui n'appelle "
                "aucune justification pour un niveau III ou IV.",
    },
    "prime": {
        "nom": "Prime",
        "illimite": False,
        "part": 0.70,
        "eligible_iii_iv": "declasse",
        "aide": "Durée limitée à la puissance nominale. Pour un usage de durée "
                "illimitée, la capacité se déclasse — de l'ordre de 70 % à "
                "défaut de certification constructeur, laquelle l'emporte.",
    },
    "secours": {
        "nom": "Secours",
        "illimite": False,
        "part": 0.0,
        "eligible_iii_iv": False,
        "aide": "Limité en heures annuelles par définition. Ne répond pas à "
                "l'exigence des niveaux III et IV, sauf certification "
                "constructeur d'une capacité tenable sans limite de durée.",
    },
}

# Part de la puissance nominale retenue, à défaut de certification, pour un
# groupe de classe « prime » exploité sans limite de durée. ORDRE DE GRANDEUR
# DÉCLARÉ, pas une mesure : le constructeur peut certifier plus ou moins, et sa
# valeur remplace celle-ci dès qu'elle est saisie.
DECLASSEMENT_PRIME = 0.70
DECLASSEMENT_SOURCE = (
    "Ordre de grandeur du déclassement d'un groupe de classe « prime » pour un "
    "fonctionnement de durée illimitée, tel que le retient le référentiel de "
    "classes de service. La valeur certifiée par le constructeur l'emporte "
    "toujours : ce repère ne sert qu'à défaut, et le résultat dit lequel a "
    "servi.")


def capacite_qualifiante_groupes(puissance_kw, classe, certifiee_kw=None):
    """Les kilowatts d'un groupe qui comptent pour un niveau III ou IV.

    Rend toujours un dict, jamais None : une classe inconnue est un REFUS
    nommé, pas un silence — c'est la faute que le compteur de redondance de ce
    dépôt a mis longtemps à corriger, et elle ne se reproduit pas ici.
    """
    p = _nombre(puissance_kw)
    c = str(classe or "").strip().lower()
    if c not in CLASSES_GROUPE:
        return {"nature": "refus", "erreur": "classe_inconnue",
                "message": ("Classe de service inconnue : « %s ». Les classes "
                            "sont %s — et elles décident de ce qui compte pour "
                            "un niveau III ou IV."
                            % (classe, ", ".join(CLASSES_GROUPE))),
                "classes": sorted(CLASSES_GROUPE)}
    if p is None or p <= 0:
        return {"nature": "refus", "erreur": "puissance_illisible",
                "message": "Puissance nominale illisible ou nulle : « %s »."
                           % puissance_kw,
                "saisi": str(puissance_kw)[:20]}
    k = CLASSES_GROUPE[c]
    cert = _nombre(certifiee_kw)
    if cert is not None and cert > 0:
        # LA CERTIFICATION L'EMPORTE, y compris sur un groupe de secours : le
        # référentiel admet qu'un constructeur atteste une capacité tenable
        # sans limite de durée, quelle que soit la classe affichée.
        qualifiante = min(cert, p)
        origine = "certification du constructeur"
        eligible = True
        note = ("La capacité certifiée sans limite de durée l'emporte sur le "
                "déclassement par défaut de la classe.")
        if cert > p:
            note += (" Elle est plafonnée à la puissance nominale : une "
                     "certification supérieure à la plaque ne s'utilise pas.")
    else:
        qualifiante = p * k["part"]
        origine = ("puissance nominale" if k["part"] == 1.0
                   else "déclassement par défaut de la classe")
        eligible = bool(k["eligible_iii_iv"])
        note = k["aide"]
        if k["part"] == 0.0:
            note += (" Faute de certification, aucun kilowatt de ce groupe ne "
                     "compte pour un niveau III ou IV.")
    return {
        "nature": "calcule",
        "classe": c, "classe_nom": k["nom"],
        "puissance_nominale_kw": p,
        "qualifiante_kw": qualifiante,
        "part": (qualifiante / p) if p else None,
        "origine": origine,
        "eligible_iii_iv": eligible,
        "note": note,
        "regle": REGLES["groupe_illimite"],
        "source": DECLASSEMENT_SOURCE if origine.startswith("déclassement")
                  else SOURCE,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  L'AUTONOMIE SUR SITE
# ═══════════════════════════════════════════════════════════════════════════

AUTONOMIE_H = 12

# Consommation spécifique d'un groupe diesel à sa puissance déclarée. REPÈRE DE
# DIMENSIONNEMENT, pas une mesure : la consommation réelle dépend du moteur, du
# taux de charge et des conditions. Il sert à dire un ORDRE DE GRANDEUR du
# volume à stocker, et le résultat le déclare.
CONSO_SPECIFIQUE_L_KWH = 0.25
CONSO_SOURCE = (
    "Repère de dimensionnement posé par le cabinet : de l'ordre de 0,25 litre "
    "de gazole par kilowattheure électrique produit, à charge nominale. Il "
    "cadre un volume ; la courbe du constructeur retenu le remplace dès "
    "qu'elle est connue, et l'écart entre les deux peut atteindre 20 %.")


def autonomie(profil):
    """Les réserves sur site exigées : douze heures de combustible, et d'eau.

    CE QUE CETTE FONCTION REND ET QUI N'EST PAS UN VOLUME : le lien avec le
    régime administratif. Le volume exigé par le niveau visé décide du volume
    stocké, lequel décide de la rubrique d'installation classée — et donc du
    délai d'instruction. Les trois se décident ensemble ou pas du tout.
    """
    p_elec = _nombre(profil.get("groupes_puissance_elec_kw"))
    manques, out = [], {"heures": AUTONOMIE_H, "reserve": RESERVE}

    if p_elec is None or p_elec <= 0:
        manques.append("la puissance électrique installée des groupes, pour "
                       "calculer le volume de combustible à stocker")
    else:
        litres = p_elec * CONSO_SPECIFIQUE_L_KWH * AUTONOMIE_H
        out["combustible"] = {
            "volume_m3": litres / 1000.0,
            "detail": {"puissance électrique (kW)": p_elec,
                       "consommation spécifique (L/kWh)": CONSO_SPECIFIQUE_L_KWH,
                       "durée (h)": AUTONOMIE_H,
                       "calcul": "volume = puissance × consommation × durée"},
            "source": CONSO_SOURCE,
            "estime": True,
            "note": ("Volume à la capacité N, hors volume mort et hors "
                     "nourrices. C'est un PLANCHER d'exigence, pas un "
                     "dimensionnement de cuve."),
        }

    fam = (profil.get("refroidissement") or "").strip()
    evaporatif = fam in ("tour_evaporative", "adiabatique")
    out["evaporatif"] = evaporatif
    if evaporatif:
        m3_an = _nombre(profil.get("eau_m3_an"))
        if m3_an is None:
            manques.append("la consommation d'eau annuelle du site, pour "
                           "calculer la réserve d'appoint de douze heures")
        else:
            # Rapportée à l'heure sur l'année : c'est une MOYENNE, et la
            # pointe estivale est plus haute. Le dire, parce qu'une réserve
            # dimensionnée sur la moyenne manque au moment où elle sert.
            out["eau_appoint"] = {
                "volume_m3": m3_an / 8760.0 * AUTONOMIE_H,
                "detail": {"consommation annuelle (m³/an)": m3_an,
                           "durée (h)": AUTONOMIE_H,
                           "calcul": "volume = annuel / 8760 × durée"},
                "estime": True,
                "note": ("Calculé sur la consommation MOYENNE. La pointe "
                         "estivale est plus élevée, et c'est en pointe qu'une "
                         "réserve sert : dimensionnez sur le mois le plus "
                         "chaud, pas sur l'année."),
            }
    else:
        out["eau_appoint"] = {
            "volume_m3": None,
            "pourquoi": ("Le mode de refroidissement retenu n'est pas "
                         "évaporatif : aucune réserve d'eau d'appoint n'est "
                         "exigée à ce titre. Elle le redeviendrait si un "
                         "appoint évaporatif ou adiabatique était ajouté."),
        }

    out["manques"] = manques
    out["regle"] = REGLES["autonomie_douze_heures"]
    out["lien_icpe"] = (
        "Le volume exigé par le niveau visé décide du volume stocké, lequel "
        "décide de la rubrique d'installation classée applicable au "
        "combustible — et donc du délai d'instruction. Portez le volume au "
        "criblage réglementaire : les deux se décident ensemble.")
    return out


def _nombre(v):
    """Une valeur numérique utilisable, ou None. Les non finies sont écartées."""
    if v is None or v == "":
        return None
    try:
        f = float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


# ═══════════════════════════════════════════════════════════════════════════
#  LE SERVICE AUX PAGES
# ═══════════════════════════════════════════════════════════════════════════

def referentiel():
    """Les tables, sans qualification — pour la page et la documentation."""
    return {
        "version": VERSION,
        "source": SOURCE,
        "reserve": RESERVE,
        "exigences": EXIGENCES,
        "ordre": ORDRE,
        "essais": ESSAIS_CONFIRMATION,
        "impacts": IMPACTS_EXPLOITATION,
        "sous_systemes": SOUS_SYSTEMES,
        "regles": REGLES,
        "classes_groupe": CLASSES_GROUPE,
        "declassement_prime": DECLASSEMENT_PRIME,
        "declassement_source": DECLASSEMENT_SOURCE,
        "autonomie_h": AUTONOMIE_H,
        "glossaire": glossaire(),
    }


def _aide_exigence(code, v):
    bouts = [
        "Capacité minimale — %s. %s" % (v["capacite_min"], v["capacite_aide"]),
        "Backbone électrique — %s" % v["backbone_aide"],
        "Distribution critique — %s" % v["distribution_aide"],
    ]
    acquis = [nom for cle, nom in (
        ("maintenable_sans_interruption", "maintenable sans interruption"),
        ("tolerant_panne", "tolérant à la panne"),
        ("compartimente", "compartimenté"),
        ("froid_continu", "froid continu")) if v.get(cle)]
    bouts.append("Ce que le niveau ajoute — %s."
                 % (", ".join(acquis) if acquis
                    else "aucune de ces quatre exigences"))
    bouts.append("Autonomie sur site — %d heures à la capacité N."
                 % v["autonomie_h"])
    bouts.append("Posture — %s" % v["posture_aide"])
    bouts.append(RESERVE)
    return "\n\n".join(bouts)


def glossaire():
    """Les familles d'infobulles servies par ce module.

    Elles ne recouvrent PAS la famille « tier » que tient déjà le cadre
    d'ingénierie : celle-ci nomme les niveaux, celles-là portent les exigences,
    les essais et les règles. Un contrôle de démarrage refuse qu'une famille
    soit revendiquée deux fois.
    """
    return {
        "tier_exigence": {k: {"nom": v["nom"], "aide": _aide_exigence(k, v)}
                          for k, v in EXIGENCES.items()},
        "tier_essai": {k: {
            "nom": "Essais de confirmation — %s" % v["nom"],
            "aide": ("Ce qui se DÉMONTRE pour ce niveau :\n· %s\n\nCe que "
                     "l'exploitant vivra :\n· %s\n\n%s"
                     % ("\n· ".join(ESSAIS_CONFIRMATION[k]),
                        "\n· ".join(IMPACTS_EXPLOITATION[k]), SOURCE)),
        } for k, v in EXIGENCES.items()},
        "tier_regle": {k: {
            "nom": v["nom"],
            "aide": ("Ce que la règle interdit — %s\n\nL'hypothèse qu'elle "
                     "renverse — %s\n\nCe qu'il faut vérifier — %s\n\n%s"
                     % (v["interdit"], v["hypothese_renversee"], v["verifier"],
                        SOURCE)),
        } for k, v in REGLES.items()},
        "classe_groupe": {k: {
            "nom": "Groupe de classe « %s »" % v["nom"],
            "aide": ("%s\n\nÉligible aux niveaux III et IV — %s"
                     % (v["aide"],
                        "oui" if v["eligible_iii_iv"] is True else
                        "après déclassement" if v["eligible_iii_iv"] == "declasse"
                        else "non, sauf certification constructeur")),
        } for k, v in CLASSES_GROUPE.items()},
    }


# ═══════════════════════════════════════════════════════════════════════════
#  LES CONTRÔLES DE COHÉRENCE
# ═══════════════════════════════════════════════════════════════════════════

def _verifier():
    """Les fautes de structure, ou une liste vide.

    LES DEUX VÉRIFICATIONS QUI COMPTENT :

      · les rangs sont strictement croissants dans l'ordre déclaré — c'est sur
        eux que repose le « plus bas des sous-systèmes », et un rang en double
        rendrait le minimum ambigu ;

      · les exigences ne RÉGRESSENT jamais d'un niveau au suivant. Un niveau
        supérieur qui perdrait une exigence du précédent ferait remonter un
        site en abaissant sa topologie.
    """
    fautes = []
    if list(EXIGENCES) != ORDRE:
        fautes.append("l'ordre déclaré ne couvre pas exactement les niveaux : "
                      "%s contre %s" % (ORDRE, list(EXIGENCES)))
    rangs = [EXIGENCES[c]["rang"] for c in ORDRE if c in EXIGENCES]
    if rangs != sorted(set(rangs)) or len(rangs) != len(set(rangs)):
        fautes.append("les rangs ne sont pas strictement croissants : %s" % rangs)
    for code in ORDRE:
        v = EXIGENCES.get(code)
        if not v:
            fautes.append("niveau manquant : %s" % code)
            continue
        for champ in ("nom", "capacite_min", "capacite_aide", "backbone_aide",
                      "distribution_aide", "posture_aide"):
            if not (v.get(champ) or "").strip():
                fautes.append("niveau %s : champ « %s » vide" % (code, champ))
        if v.get("autonomie_h") != AUTONOMIE_H:
            fautes.append("niveau %s : autonomie %s au lieu de %d — l'exigence "
                          "est la même à tous les niveaux"
                          % (code, v.get("autonomie_h"), AUTONOMIE_H))
        if code not in ESSAIS_CONFIRMATION or not ESSAIS_CONFIRMATION[code]:
            fautes.append("niveau %s : aucun essai de confirmation" % code)
        if code not in IMPACTS_EXPLOITATION or not IMPACTS_EXPLOITATION[code]:
            fautes.append("niveau %s : aucun impact d'exploitation" % code)
    # Aucune exigence booléenne ne régresse en montant.
    for champ in ("maintenable_sans_interruption", "tolerant_panne",
                  "compartimente", "froid_continu"):
        vus = [bool(EXIGENCES[c].get(champ)) for c in ORDRE if c in EXIGENCES]
        if vus != sorted(vus):
            fautes.append("l'exigence « %s » régresse d'un niveau au suivant : "
                          "%s" % (champ, dict(zip(ORDRE, vus))))
    for champ in ("backbone", "distribution_critique"):
        vus = [EXIGENCES[c].get(champ) for c in ORDRE if c in EXIGENCES]
        if any(a is None for a in vus) or vus != sorted(vus):
            fautes.append("le nombre de chemins « %s » régresse ou manque : %s"
                          % (champ, dict(zip(ORDRE, vus))))
    for cle, s in SOUS_SYSTEMES.items():
        for champ in ("nom", "aide"):
            if not (s.get(champ) or "").strip():
                fautes.append("sous-système %s : champ « %s » vide" % (cle, champ))
    for cle, r in REGLES.items():
        for champ in ("nom", "interdit", "hypothese_renversee", "verifier"):
            if not (r.get(champ) or "").strip():
                fautes.append("règle %s : champ « %s » vide" % (cle, champ))
    for cle, k in CLASSES_GROUPE.items():
        p = k.get("part")
        if not isinstance(p, float) or not (0.0 <= p <= 1.0):
            fautes.append("classe %s : part hors [0, 1] (%s)" % (cle, p))
    if CLASSES_GROUPE["prime"]["part"] != DECLASSEMENT_PRIME:
        fautes.append("le déclassement « prime » est écrit deux fois et les "
                      "deux valeurs diffèrent (%s et %s)"
                      % (CLASSES_GROUPE["prime"]["part"], DECLASSEMENT_PRIME))
    return fautes


_FAUTES = _verifier()
if _FAUTES:
    raise RuntimeError("tier_dc — table incohérente : " + " ; ".join(_FAUTES))
