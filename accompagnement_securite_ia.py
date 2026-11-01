# -*- coding: utf-8 -*-
"""L'ACCOMPAGNEMENT DE LA PAGE /securite-ia — phase par phase.

CE QUI MANQUAIT. La page tenait ses instruments (chaîne d'autonomie,
restitution EBIOS, contre-expertise, ambition, architecture) mais laissait le
client seul devant eux : aucun cadrage préalable, aucun repère de progression,
aucune définition au survol d'un terme, et une restitution EBIOS qui rendait
des « vraisemblances sans risques » faute de gravité — la route savait la
recevoir, la page ne la demandait jamais.

CE QUE CE MODULE SERT, ET QUE LA PAGE NE RECOPIE PAS :
  · PHASES — pour chacune : ce qu'on y fait, ce qu'il faut préparer, qui doit
    être présent, comment lire le résultat, la décision qu'elle éclaire, le
    piège, et SES sources (des clés vers les tables de `chaine_autonomie` et
    de `contre_expertise_ia`, jamais une seconde table) ;
  · GLOSSAIRE — les définitions des info-bulles, chacune avec sa source ;
  · GRAVITES — l'échelle à quatre niveaux d'EBIOS Risk Manager, dite avec nos
    mots (le guide est sous Licence Ouverte : le vocabulaire se reprend, le
    texte ne se recopie pas) ;
  · la GRILLE D'ACCEPTATION et `aide_a_la_decision()`.

LA GRILLE EST UNE GRILLE PAR DÉFAUT, ET ELLE LE DIT. Dans EBIOS RM, c'est
l'organisation qui fixe ses seuils d'acceptation du risque. Celle-ci est la
proposition du cabinet pour amorcer la discussion ; chaque décision rendue
porte la mention qu'elle doit être validée par la direction. Une aide à la
décision qui se ferait passer pour la décision prendrait la place de celui
qui en répond.

ET ELLE NE MOYENNE RIEN. Comme la chaîne, le parc se lit à son pire : la
décision d'ensemble est commandée par le maillon le plus mal placé dans la
grille, jamais par une proportion de maillons « acceptables ».
"""

from __future__ import unicode_literals

import chaine_autonomie
import contre_expertise_ia


# ═══════════════════════════════════════════════════════════════════════════
#  1. LES SOURCES — des renvois, pas une table de plus
# ═══════════════════════════════════════════════════════════════════════════
#
# Une clé de `chaine_autonomie.SOURCES` (« pa048 »…) ou le nom court d'une
# source de `contre_expertise_ia.SOURCES` (« NIS 2 »…). `_verifier()` refuse
# un renvoi qui ne mène nulle part.

def _source(cle):
    for s in chaine_autonomie.SOURCES:
        if s["cle"] == cle:
            return {"cle": s["cle"], "titre": s["titre"], "date": s["date"],
                    "licence": s["licence"], "apporte": s["apporte"],
                    "reserve": s["reserve"], "url": None,
                    "certifiable": s["certifiable"]}
    for s in contre_expertise_ia.SOURCES:
        if s["court"] == cle:
            return {"cle": s["court"], "titre": s["nom"], "date": None,
                    "licence": s["licence"],
                    "apporte": "Nature : %s. Seul le texte publié au Journal "
                               "officiel de l'Union fait foi." % s["nature"],
                    "reserve": None, "url": s["url"], "certifiable": False}
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  2. LES PHASES DE LA PAGE, DANS L'ORDRE DU TRAVAIL
# ═══════════════════════════════════════════════════════════════════════════
#
# `ancre` est l'identifiant de la section de la page : c'est par lui que la
# barre de progression mène à la phase et que l'encadré s'y pose. `fait_quand`
# dit au client ce qui fera passer la phase à « faite » — la page le mesure,
# elle ne le croit pas sur parole.

PHASES = (
    {"cle": "cadrage", "ancre": "cadrage",
     "titre": "Cadrer ce qui compterait si ça cassait",
     "objectif": "Nommer la valeur métier que les systèmes d'IA servent, et "
                 "dire quelle gravité aurait sa perte. C'est la seule donnée "
                 "que l'outil ne peut pas déduire : elle dépend de votre "
                 "métier, pas de votre architecture.",
     "a_preparer": ["La liste des processus métier où l'IA intervient déjà",
                    "Votre statut au titre de NIS 2, s'il est établi",
                    "Le dernier incident ou quasi-incident lié à un système "
                    "d'IA, s'il y en a eu un"],
     "qui": "Le responsable du métier concerné, avec le RSSI. La sécurité "
            "ne fixe pas seule la gravité d'une perte métier.",
     "comment_lire": "Sans gravité, la restitution donne des vraisemblances "
                     "sans risques : elle dit ce qui peut arriver, jamais ce "
                     "que cela coûterait. Avec elle, chaque maillon ouvert "
                     "reçoit un niveau de risque et une décision proposée.",
     "decision": "Le niveau de gravité retenu, assumé par le métier.",
     "piege": "Choisir la gravité la plus basse pour que le tableau soit vert. "
              "La grille ne protège que si la gravité est celle que le métier "
              "défendrait devant un auditeur.",
     "sources": ["pa048", "NIS 2"],
     "fait_quand": "La valeur métier et la gravité sont renseignées."},
    {"cle": "parc", "ancre": "parc",
     "titre": "Inventorier les systèmes du parc",
     "objectif": "Déclarer chaque système d'IA qui tourne, y compris ceux "
                 "qu'aucun projet n'a déclarés : connecteurs, copilotes, "
                 "agents branchés pour gagner du temps.",
     "a_preparer": ["Le registre des systèmes d'IA, s'il existe",
                    "La liste des abonnements à des services d'IA payés par "
                    "carte ou par note de frais",
                    "Les connecteurs ouverts vers la messagerie, le stockage "
                    "et les outils métier"],
     "qui": "La DSI et les achats : un système qu'aucun projet n'a déclaré "
            "se trouve dans les factures avant de se trouver dans les "
            "schémas.",
     "comment_lire": "Le parc se lit à son pire système : c'est lui qui "
                     "commande l'exposition. Un système déclaré sans cotation "
                     "n'est ni sain ni exposé — il n'a pas encore été regardé.",
     "decision": "Le périmètre de l'analyse : quels systèmes sont dedans, et "
                 "lesquels sont explicitement hors champ.",
     "piege": "Coter un système « représentatif » à la place du parc : c'est "
              "faire de tête la moyenne que la méthode interdit.",
     "sources": ["pa102", "Règlement sur l'IA"],
     "fait_quand": "Au moins un système est déclaré."},
    {"cle": "chaine", "ancre": "chaine",
     "titre": "Coter la chaîne de chaque système",
     "objectif": "Pour chaque maillon, constater deux degrés sur pièce : "
                 "l'autonomie (ce qui part sans validation) et la maîtrise "
                 "(ce qui l'en empêche ou le rattrape).",
     "a_preparer": ["Les schémas d'architecture du système",
                    "La liste des outils et des droits qu'il détient",
                    "Les journaux d'un jour de fonctionnement ordinaire",
                    "Le dernier test d'intrusion ou exercice, s'il existe"],
     "qui": "L'architecte du système et l'exploitant : ils savent ce qui "
            "part sans validation, et ce qui en garde la trace.",
     "comment_lire": "L'écart d'un maillon est son autonomie moins sa "
                     "maîtrise. Un écart positif est un maillon ouvert. Le "
                     "pire écart commande la chaîne — jamais la moyenne.",
     "decision": "Rien encore : cette phase constate. La décision vient à la "
                 "phase suivante, une fois la gravité appliquée.",
     "piege": "Coter la maîtrise sur la foi d'une politique écrite. Une règle "
              "que rien n'applique techniquement vaut « Déclarée », pas "
              "davantage.",
     "sources": ["pa102", "asi", "atlas", "iso27090"],
     "fait_quand": "Au moins un maillon d'un système porte ses deux notes."},
    {"cle": "ebios", "ancre": "ebios",
     "titre": "Lire le risque et décider du traitement",
     "objectif": "Relire le constat dans la grammaire d'EBIOS Risk Manager, "
                 "obtenir pour chaque maillon ouvert un niveau de risque, et "
                 "choisir son traitement.",
     "a_preparer": ["La gravité retenue en phase de cadrage",
                    "Les seuils d'acceptation du risque de votre "
                    "organisation, s'ils sont écrits"],
     "qui": "Le propriétaire du risque — celui qui en répond devant la "
            "direction — avec le RSSI.",
     "comment_lire": "Chaque maillon ouvert devient un scénario : bien "
                     "support critique, événement redouté, vraisemblance "
                     "déduite de l'écart. Croisée avec la gravité, la "
                     "vraisemblance donne un niveau : acceptable, tolérable "
                     "sous conditions, ou inacceptable.",
     "decision": "Pour chaque maillon ouvert : réduire, transférer, refuser "
                 "ou accepter — et, pour réduire, lequel des deux leviers "
                 "(baisser l'autonomie ou monter la maîtrise).",
     "piege": "Traiter d'abord les écarts les plus faciles. Le plan doit "
              "commencer par le pire maillon : c'est lui qui commande la "
              "chaîne.",
     "sources": ["pa048", "pa102", "NIS 2"],
     "fait_quand": "Un calcul a rendu au moins un niveau de risque, gravité "
                   "comprise."},
    {"cle": "usine", "ancre": "usine",
     "titre": "Soustraire ce qui tourne sans contrôle",
     "objectif": "Déclarer les cas d'usage déjà en service et les contrôles "
                 "en place, et obtenir ce qui tourne sans le contrôle requis "
                 "— et depuis combien de jours.",
     "a_preparer": ["La date de mise en service de chaque cas d'usage",
                    "La liste des contrôles réellement opérationnels, pas "
                    "ceux du plan"],
     "qui": "Le responsable du programme d'IA et le RSSI.",
     "comment_lire": "L'écran rend une soustraction, pas un taux de "
                     "couverture : un taux monte pendant que des cas d'usage "
                     "partent sans contrôle. La feuille de route suit les "
                     "prérequis, pas les préférences.",
     "decision": "Quels cas d'usage suspendre ou encadrer en attendant "
                 "leur contrôle, et dans quel ordre ouvrir les lots.",
     "piege": "Compter un contrôle « en cours de déploiement » comme en "
              "place. Il ne l'est qu'une fois opérationnel.",
     "sources": ["asi", "atlas", "DORA", "NIS 2"],
     "fait_quand": "La soustraction a été lancée."},
    {"cle": "ambition", "ancre": "ambition",
     "titre": "Confronter l'ambition au temps des contrôles",
     "objectif": "Poser deux dates — celle de l'ambition annoncée, celle où "
                 "les contrôles requis peuvent être prêts — et rendre "
                 "l'écart.",
     "a_preparer": ["L'ambition telle que la direction l'a formulée",
                    "Sa date annoncée"],
     "qui": "La direction, avec le RSSI : c'est elle qui arbitre.",
     "comment_lire": "L'écran ne recommande rien : il rend l'écart et trois "
                     "issues — réduire l'ambition, décaler la date, ou "
                     "accepter le risque par écrit.",
     "decision": "Réduire, décaler ou accepter. Ce choix n'appartient pas à "
                 "la sécurité ; elle doit seulement le rendre explicite.",
     "piege": "Présenter l'écart comme une opinion. Deux dates ne se "
              "discutent pas comme deux avis.",
     "sources": ["cop", "pren18286", "Règlement sur l'IA"],
     "fait_quand": "Les deux dates ont été soustraites."},
    {"cle": "architecture", "ancre": "architecture",
     "titre": "Challenger l'architecture",
     "objectif": "Poser les questions qui ont une mauvaise réponse "
                 "reconnaissable, et demander la pièce qui prouve la bonne.",
     "a_preparer": ["Le dossier d'architecture du système le plus exposé",
                    "Les preuves : configurations, journaux, comptes rendus "
                    "de tests"],
     "qui": "L'architecte, face au RSSI ou à l'auditeur.",
     "comment_lire": "Une réponse sans pièce vaut une réponse manquante. La "
                     "question est close quand la pièce est en main.",
     "decision": "Les questions restées sans pièce deviennent des actions "
                 "du plan de traitement.",
     "piege": "Demander « est-ce sécurisé ? » : on répondra oui.",
     "sources": ["pa102", "asi", "anssi19"],
     "fait_quand": "Au moins une question a été dépliée."},
    {"cle": "directions", "ancre": "deux-sens",
     "titre": "Ne pas oublier la menace armée par l'IA",
     "objectif": "Distinguer les trois directions : sécuriser l'IA, "
                 "augmenter la cyber par l'IA, et se défendre contre une "
                 "menace que l'IA arme.",
     "a_preparer": ["Les scénarios d'attaque récents de votre secteur"],
     "qui": "Le RSSI et le centre opérationnel de sécurité.",
     "comment_lire": "La troisième direction ne porte pas sur vos systèmes "
                     "d'IA : elle se traite dans la détection et la réponse, "
                     "pas en durcissant une usine qu'elle n'attaque pas.",
     "decision": "Qui porte la troisième direction dans l'organisation.",
     "piege": "La ranger dans le projet d'IA : elle tombe alors entre les "
              "chaises.",
     "sources": ["anssi19", "atlas"],
     "fait_quand": "La section a été parcourue."},
)


# ═══════════════════════════════════════════════════════════════════════════
#  3. LE GLOSSAIRE DES INFO-BULLES
# ═══════════════════════════════════════════════════════════════════════════

GLOSSAIRE = (
    {"cle": "autonomie", "terme": "Autonomie",
     "definition": "Ce que le système fait à ce maillon sans qu'un humain "
                   "l'ait validé. Elle se constate sur pièce : droits, "
                   "outils, journaux.", "source": "pa102"},
    {"cle": "maitrise", "terme": "Maîtrise",
     "definition": "Ce qui, à ce maillon, empêche ou rattrape l'action du "
                   "système. Déclarée (écrite), appliquée (technique), "
                   "journalisée (tracée), éprouvée (testée).",
     "source": "pa102"},
    {"cle": "ecart", "terme": "Écart",
     "definition": "Autonomie moins maîtrise. Positif, le maillon est "
                   "ouvert. C'est le pire écart qui commande la chaîne, "
                   "jamais la moyenne.", "source": "pa048"},
    {"cle": "maillon", "terme": "Maillon",
     "definition": "L'une des cinq étapes que franchit toute action d'un "
                   "système d'IA, de ce qu'il perçoit à l'effet qu'il "
                   "produit.", "source": "pa102"},
    {"cle": "valeur_metier", "terme": "Valeur métier",
     "definition": "Ce que l'organisation veut protéger : un processus ou "
                   "une information dont la perte la toucherait. Notion "
                   "d'EBIOS Risk Manager.", "source": "pa048"},
    {"cle": "gravite", "terme": "Gravité",
     "definition": "L'ampleur des conséquences pour l'organisation si la "
                   "valeur métier est atteinte, sur quatre niveaux. C'est le "
                   "métier qui la fixe.", "source": "pa048"},
    {"cle": "vraisemblance", "terme": "Vraisemblance",
     "definition": "La facilité avec laquelle le scénario peut se produire. "
                   "Ici, elle est déduite de l'écart : ce n'est pas une "
                   "probabilité.", "source": "pa048"},
    {"cle": "bien_support", "terme": "Bien support critique",
     "definition": "Le composant technique sur lequel repose la valeur "
                   "métier, et par lequel le scénario passe.",
     "source": "pa048"},
    {"cle": "evenement_redoute", "terme": "Événement redouté",
     "definition": "Ce qui arriverait à la valeur métier : divulgation, "
                   "altération, indisponibilité, perte de traçabilité.",
     "source": "pa048"},
    {"cle": "socle", "terme": "Socle de sécurité",
     "definition": "Les mesures de référence applicables au maillon, tirées "
                   "des recommandations publiques de l'ANSSI pour l'IA "
                   "générative.", "source": "pa102"},
    {"cle": "statut_nis2", "terme": "Statut NIS 2",
     "definition": "Entité essentielle ou importante au sens de la "
                   "directive NIS 2 : l'entité doit prendre des mesures de "
                   "gestion des risques et notifier ses incidents "
                   "importants.", "source": "NIS 2"},
    {"cle": "traitement", "terme": "Traitement du risque",
     "definition": "Le choix fait pour chaque risque : le réduire, le "
                   "transférer, le refuser en renonçant à l'usage, ou "
                   "l'accepter par écrit.", "source": "pa048"},
)


# ═══════════════════════════════════════════════════════════════════════════
#  4. LES LISTES DU FORMULAIRE DE CADRAGE
# ═══════════════════════════════════════════════════════════════════════════

#: L'échelle de gravité d'EBIOS RM, à quatre niveaux, dite avec nos mots.
GRAVITES = (
    {"niveau": 1, "nom": "Mineure",
     "dit": "Des conséquences que l'organisation absorbe sans difficulté "
            "notable."},
    {"niveau": 2, "nom": "Significative",
     "dit": "Des conséquences réelles, surmontées avec des efforts et un "
            "coût."},
    {"niveau": 3, "nom": "Grave",
     "dit": "Des conséquences lourdes : l'activité est dégradée, et "
            "l'organisation s'en remet difficilement."},
    {"niveau": 4, "nom": "Critique",
     "dit": "Des conséquences dont l'organisation pourrait ne pas se "
            "relever, ou qui atteignent la sécurité des personnes."},
)

#: Les secteurs, et pour chacun des valeurs métier souvent rencontrées —
#: des suggestions, jamais une liste fermée.
SECTEURS = (
    {"cle": "industrie", "nom": "Industrie et production",
     "valeurs": ["Continuité de la production",
                 "Sûreté des installations et des personnes",
                 "Savoir-faire de fabrication"]},
    {"cle": "energie", "nom": "Énergie et réseaux",
     "valeurs": ["Continuité de la fourniture",
                 "Pilotage du réseau", "Sûreté des installations"]},
    {"cle": "sante", "nom": "Santé",
     "valeurs": ["Continuité des soins", "Confidentialité des données "
                 "de santé", "Exactitude des décisions cliniques"]},
    {"cle": "finance", "nom": "Banque, finance et assurance",
     "valeurs": ["Intégrité des opérations de paiement",
                 "Confidentialité des données clients",
                 "Conformité des décisions d'octroi"]},
    {"cle": "public", "nom": "Administration et services publics",
     "valeurs": ["Continuité du service aux usagers",
                 "Confidentialité des données des usagers",
                 "Égalité de traitement des décisions"]},
    {"cle": "numerique", "nom": "Services numériques et logiciels",
     "valeurs": ["Disponibilité du service client",
                 "Confidentialité des données hébergées",
                 "Intégrité du code livré"]},
    {"cle": "autre", "nom": "Autre secteur", "valeurs": []},
)

STATUTS_NIS2 = (
    {"cle": "essentielle", "nom": "Entité essentielle"},
    {"cle": "importante", "nom": "Entité importante"},
    {"cle": "hors", "nom": "Hors du champ de NIS 2"},
    {"cle": "inconnu", "nom": "Statut non établi"},
)
_STATUTS = {s["cle"]: s for s in STATUTS_NIS2}


# ═══════════════════════════════════════════════════════════════════════════
#  5. LA GRILLE D'ACCEPTATION, ET L'AIDE À LA DÉCISION
# ═══════════════════════════════════════════════════════════════════════════
#
# Lignes : gravité 1 à 4. Colonnes : écart 1 à 4 (la vraisemblance déduite).
# A = acceptable, T = tolérable sous conditions, I = inacceptable.
# La diagonale est volontairement sévère côté gravité : une gravité critique
# ne tolère pas deux degrés d'écart, quelle que soit la facilité du reste.

GRILLE = {
    1: ("A", "A", "T", "T"),
    2: ("A", "T", "T", "I"),
    3: ("T", "T", "I", "I"),
    4: ("T", "I", "I", "I"),
}

NIVEAUX = {
    "A": {"cle": "acceptable", "nom": "Acceptable",
          "decision": "Accepter, par écrit, et réévaluer à la prochaine "
                      "évolution du système.",
          "options": ["Accepter le risque, avec un nom et une date",
                      "Le réduire quand même si le coût est faible"],
          "rang": 0},
    "T": {"cle": "tolerable", "nom": "Tolérable sous conditions",
          "decision": "Réduire selon un plan daté et suivi ; l'usage peut "
                      "continuer pendant ce temps, sous surveillance.",
          "options": ["Réduire selon un plan daté",
                      "Transférer une part du risque (contrat, assurance)",
                      "Accepter temporairement, jusqu'à une date écrite"],
          "rang": 1},
    "I": {"cle": "inacceptable", "nom": "Inacceptable",
          "decision": "Réduire avant toute extension de l'usage, ou "
                      "suspendre l'autonomie de ce maillon jusqu'à ce que la "
                      "maîtrise la rattrape.",
          "options": ["Réduire avant toute extension",
                      "Refuser : renoncer à l'usage ou à ce degré "
                      "d'autonomie",
                      "Suspendre l'autonomie du maillon en attendant"],
          "rang": 2},
}

VALIDATION = ("Grille par défaut du cabinet. Dans EBIOS Risk Manager, c'est "
              "l'organisation qui fixe ses seuils d'acceptation : cette "
              "proposition doit être validée par la direction avant de "
              "servir de décision.")


def _degre(echelle, d):
    for x in echelle:
        if x["degre"] == d:
            return x
    return None


def _refermer(autonomie, maitrise):
    """Les deux leviers qui referment un maillon, nommés par leurs degrés."""
    a = _degre(chaine_autonomie.AUTONOMIE, autonomie)
    m_cible = _degre(chaine_autonomie.MAITRISE, autonomie)
    a_cible = _degre(chaine_autonomie.AUTONOMIE, maitrise)
    m = _degre(chaine_autonomie.MAITRISE, maitrise)
    return [
        {"levier": "baisser_autonomie",
         "dit": "Ramener l'autonomie de « %s » à « %s »."
                % (a["nom"], a_cible["nom"])},
        {"levier": "monter_maitrise",
         "dit": "Faire passer la maîtrise de « %s » à « %s »."
                % (m["nom"], m_cible["nom"])},
    ]


def niveau(ecart, gravite):
    """Le niveau de la grille, ou None si l'un des deux manque."""
    try:
        g, e = int(gravite), int(ecart)
    except (TypeError, ValueError):
        return None
    if g not in GRILLE or e < 1:
        return None
    return NIVEAUX[GRILLE[g][min(e, 4) - 1]]


def aide_a_la_decision(systemes, gravite=None, statut_nis2=None):
    """Pour chaque maillon ouvert du parc : son niveau, la décision
    proposée et les deux leviers qui le referment — puis la décision
    d'ensemble, commandée par le pire, jamais par une proportion."""
    d = chaine_autonomie.evaluer_parc(systemes)
    if not d.get("ok"):
        return d
    try:
        g = int(gravite)
        g = g if g in GRILLE else None
    except (TypeError, ValueError):
        g = None
    lignes = []
    noms = {m["cle"]: m["nom"] for m in chaine_autonomie.MAILLONS}
    for s in d["systemes"]:
        for cle, x in zip([m["cle"] for m in chaine_autonomie.MAILLONS],
                          s["chaine"]["maillons"]):
            if not x.get("ouvert"):
                continue
            n = niveau(x["ecart"], g)
            lignes.append({
                "systeme": s["nom"], "maillon": cle, "maillon_nom": noms[cle],
                "ecart": x["ecart"],
                "niveau": n["cle"] if n else None,
                "niveau_nom": n["nom"] if n else None,
                "decision": n["decision"] if n else None,
                "options": list(n["options"]) if n else [],
                "refermer": _refermer(x["autonomie"], x["maitrise"]),
                "_rang": n["rang"] if n else -1,
            })
    lignes.sort(key=lambda l: (-l["_rang"], -l["ecart"]))
    for l in lignes:
        l.pop("_rang")
    compte = {k: sum(1 for l in lignes if l["niveau"] == v["cle"])
              for k, v in (("inacceptable", NIVEAUX["I"]),
                           ("tolerable", NIVEAUX["T"]),
                           ("acceptable", NIVEAUX["A"]))}
    if not lignes:
        ensemble = ("Aucun maillon ouvert parmi les systèmes cotés : rien à "
                    "traiter à ce stade. Ce constat ne vaut que pour les "
                    "maillons renseignés.")
    elif g is None:
        ensemble = ("%d maillon(s) ouvert(s), mais aucune gravité n'est "
                    "renseignée : sans elle, l'outil ne peut pas dire ce "
                    "qui est acceptable. Renseignez-la à la phase de "
                    "cadrage." % len(lignes))
    elif compte["inacceptable"]:
        pire = lignes[0]
        ensemble = ("Ne pas étendre l'usage de l'IA sur ce périmètre tant "
                    "que les %d maillon(s) inacceptable(s) ne sont pas "
                    "refermés — à commencer par « %s » sur « %s »."
                    % (compte["inacceptable"], pire["maillon_nom"],
                       pire["systeme"]))
    elif compte["tolerable"]:
        ensemble = ("L'usage peut continuer, sous condition d'un plan de "
                    "réduction daté pour %d maillon(s) tolérable(s), suivi "
                    "jusqu'à sa clôture." % compte["tolerable"])
    else:
        ensemble = ("Les maillons ouverts sont acceptables avec la gravité "
                    "retenue : formaliser l'acceptation par écrit, avec un "
                    "nom et une date de réévaluation.")
    statut = _STATUTS.get(str(statut_nis2 or ""))
    nis2 = None
    if statut and statut["cle"] in ("essentielle", "importante"):
        nis2 = ("%s : le plan de traitement fait partie des mesures de "
                "gestion des risques que l'autorité peut demander à voir, et "
                "un incident important sur ces systèmes se notifie."
                % statut["nom"])
    elif statut and statut["cle"] == "inconnu":
        nis2 = ("Statut NIS 2 non établi : l'établir avant de présenter le "
                "plan, car il fixe ce que l'autorité peut exiger.")
    return {"ok": True, "gravite": g, "lignes": lignes, "compte": compte,
            "ensemble": ensemble, "nis2": nis2, "validation": VALIDATION}


# ═══════════════════════════════════════════════════════════════════════════
#  6. CE QUE LA ROUTE SERT
# ═══════════════════════════════════════════════════════════════════════════

def referentiel():
    return {
        "phases": [dict(p, a_preparer=list(p["a_preparer"]),
                        sources=[_source(c) for c in p["sources"]])
                   for p in PHASES],
        "glossaire": [dict(t, source=_source(t["source"])) for t in GLOSSAIRE],
        "gravites": list(GRAVITES),
        "secteurs": [dict(s, valeurs=list(s["valeurs"])) for s in SECTEURS],
        "statuts_nis2": list(STATUTS_NIS2),
        "grille": {str(g): [NIVEAUX[x]["cle"] for x in GRILLE[g]] for g in GRILLE},
        "niveaux": [dict(v, options=list(v["options"])) for v in NIVEAUX.values()],
        "validation": VALIDATION,
    }


def _verifier():
    fautes = []
    for p in PHASES:
        for c in p["sources"]:
            if _source(c) is None:
                fautes.append("phase %s : source « %s » introuvable" % (p["cle"], c))
        for champ in ("objectif", "qui", "comment_lire", "decision", "piege",
                      "fait_quand"):
            if not p.get(champ):
                fautes.append("phase %s : « %s » vide" % (p["cle"], champ))
        if not p["sources"]:
            fautes.append("phase %s : aucune source" % p["cle"])
    for t in GLOSSAIRE:
        if _source(t["source"]) is None:
            fautes.append("terme %s : source introuvable" % t["cle"])
    if sorted(GRILLE) != [1, 2, 3, 4] or any(len(v) != 4 for v in GRILLE.values()):
        fautes.append("la grille n'est pas 4 × 4")
    for g in GRILLE:
        rangs = [NIVEAUX[x]["rang"] for x in GRILLE[g]]
        if rangs != sorted(rangs):
            fautes.append("gravité %d : le niveau baisse quand l'écart monte" % g)
    for i in range(4):
        col = [NIVEAUX[GRILLE[g][i]]["rang"] for g in (1, 2, 3, 4)]
        if col != sorted(col):
            fautes.append("écart %d : le niveau baisse quand la gravité monte" % (i + 1))
    if fautes:
        raise ValueError("accompagnement_securite_ia : " + " ; ".join(fautes))


_verifier()
