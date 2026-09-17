# -*- coding: utf-8 -*-
"""SÉCURITÉ DE L'IA — LA CHAÎNE D'AUTONOMIE.

CE MODULE N'EST PAS `garde_ia`, ET LA DISTINCTION IMPORTE. `garde_ia` est la
DÉFENSE du cabinet : il clôt les extraits de la base de connaissance pour
qu'un document déposé ne puisse pas parler au nom de la maison. Celui-ci est
une MÉTHODE D'ANALYSE vendue au client, pour mesurer la sécurité de SES
systèmes d'IA. Deux choses différentes ; il s'est d'abord appelé `securite_ia`,
à un caractère de son voisin, et un fichier de recette en a fait les frais.

════════════════════════════════════════════════════════════════════════════
LE DÉFAUT QUE CE MODULE COMBLE, ET IL A ÉTÉ MESURÉ AVANT D'ÊTRE ÉCRIT
════════════════════════════════════════════════════════════════════════════
Les deux plateformes du cabinet portaient onze modules traitant de l'IA.
AUCUN ne mesurait une attaque. La matrice de risques positionnait les systèmes
selon la « probabilité de NON-CONFORMITÉ » ; le radar portait sur six
dimensions RÉGLEMENTAIRES ; l'audit de maturité suivait les huit piliers de
l'AI Act, où « sûreté » désigne la safety du produit et non la résistance à un
attaquant. Les mots « injection de prompt » et « empoisonnement » figuraient
une fois chacun, dans une phrase de présentation sectorielle — jamais comme un
contrôle. Un système parfaitement conforme et trivialement détournable passait
au vert partout.

════════════════════════════════════════════════════════════════════════════
CE QUE CE MODULE MESURE, ET POURQUOI CE N'EST PAS UNE DÉCLARATION
════════════════════════════════════════════════════════════════════════════
Une analyse de risque classique part de ce qu'on REDOUTE, ce qui suppose de
l'avoir imaginé. Un agent produit des chemins nouveaux à chaque exécution :
la liste des scénarios vieillit plus vite qu'on ne l'écrit.

Ce module part de l'autre bout — de ce que le système PEUT FAIRE, qui se
constate. Toute action d'un système d'IA franchit cinq maillons : elle perçoit
une entrée, elle raisonne, elle tranche, elle agit sur un outil, et cela
produit un effet. Chaque maillon reçoit DEUX notes, et les deux se constatent
sur pièce :

  · l'AUTONOMIE — ce que le système fait sans que personne ne valide ;
  · la MAÎTRISE — ce qui, à ce maillon, l'en empêche ou le rattrape.

L'ÉCART entre les deux est ce qui compte. Un maillon dont l'autonomie dépasse
la maîtrise est un maillon ouvert, et il l'est que quelqu'un l'ait imaginé ou
non. C'est la différence entre « nous n'avons pas prévu ce scénario » et
« l'agent atteint cette base sans qu'aucun contrôle ne s'y oppose ».

LE PIRE ÉCART COMMANDE LA CHAÎNE, JAMAIS LA MOYENNE. Une capacité de
raisonnement remarquablement encadrée derrière un maillon d'action grand
ouvert produit un incident, et la moyenne des cinq maillons dirait le
contraire. `evaluer()` rend donc le maximum des écarts, et une règle de
`tests/` refuse toute implémentation qui moyennerait.

════════════════════════════════════════════════════════════════════════════
CE QUE CE MODULE N'EST PAS
════════════════════════════════════════════════════════════════════════════
Ce n'est pas un audit : personne n'est venu sur site, rien n'a été éprouvé.
C'est une grille qui structure un constat, et le document produit le dit dans
sa première ligne. Un maillon coté 4 en maîtrise signifie « on affirme tenir
cela » ; il faudra le montrer.

Ce n'est pas non plus une conformité. Aucun des référentiels cités ne se
certifie sur cette base — et l'un d'eux, ISO/IEC 27090, ne se certifie pas du
tout. `SOURCES` porte la licence et le caractère certifiable de chacun, et une
règle refuse qu'on l'oublie.

════════════════════════════════════════════════════════════════════════════
D'OÙ VIENT LE VOCABULAIRE, ET CE QU'IL DOIT À QUI
════════════════════════════════════════════════════════════════════════════
La restitution emploie la grammaire d'EBIOS Risk Manager — valeur métier, bien
support critique, événement redouté, gravité, source de risque, scénario
opérationnel. Ce n'est pas un emprunt décoratif : c'est ce qui rend la mesure
lisible par un auditeur NIS2 sans qu'on ait à lui expliquer une méthode neuve.

Le guide ANSSI-PA-048 (EBIOS RM v1.5, septembre 2024) est publié sous Licence
Ouverte Etalab : le vocabulaire est donc repris librement, avec mention de sa
paternité, et AUCUN passage du guide n'est recopié ici. Relevé fait le 17
septembre 2026 : ce guide de cent pages ne contient pas une seule occurrence
du mot « intelligence artificielle ». La transposition est donc bien à
construire, et c'est l'objet de ce fichier.
"""

# ══════════════════════════════════════════════════════════════════════════
#  LES SOURCES, ET CE QU'ON A LE DROIT D'EN FAIRE
# ══════════════════════════════════════════════════════════════════════════
# POURQUOI LA LICENCE EST DANS LA TABLE. Deux de ces sources sont sous Licence
# Ouverte et peuvent être adaptées, y compris commercialement, à la seule
# condition d'en mentionner la paternité : c'est sur elles qu'un produit se
# bâtit sans négociation. Les autres se CITENT et ne se recopient pas. Ranger
# les huit sur la même étagère ferait tôt ou tard recopier le mauvais texte.
#
# ET POURQUOI `certifiable` EST UN CHAMP. « Conforme ISO 27090 » ne veut rien
# dire : le texte est informatif et ne porte aucune exigence. Un module qui
# laisserait croire le contraire vendrait une conformité qui n'existe pas.
SOURCES = [
    {"cle": "pa048", "titre": "ANSSI-PA-048 — EBIOS Risk Manager v1.5",
     "date": "septembre 2024", "licence": "Licence Ouverte / Etalab v1",
     "reutilisable": True, "certifiable": False,
     "apporte": "La grammaire de l'analyse de risque : valeur métier, bien "
                "support, événement redouté, source de risque, scénario "
                "opérationnel, socle de sécurité, plan de traitement.",
     "reserve": "Cent pages, zéro occurrence du mot « intelligence "
                "artificielle » — relevé du 17 septembre 2026. La méthode "
                "n'est pas prévue pour un système non déterministe."},
    {"cle": "pa102", "titre": "ANSSI-PA-102 — Recommandations de sécurité "
                              "pour un système d'IA générative",
     "date": "avril 2024", "licence": "Licence Ouverte v2.0",
     "reutilisable": True, "certifiable": False,
     "apporte": "Trente-cinq recommandations, qui forment le socle de "
                "sécurité mesurable de la chaîne. Trois familles d'attaques "
                "— manipulation, infection, exfiltration — et quatre besoins "
                "de sécurité dont la traçabilité.",
     "reserve": "Porte sur l'IA générative. Les agents et les systèmes "
                "multi-agents n'y sont pas traités : c'est OWASP qui les "
                "couvre."},
    {"cle": "anssi19", "titre": "ANSSI et dix-neuf agences partenaires — "
                                "Développer la confiance dans l'IA par les "
                                "risques cyber",
     "date": "février 2025", "licence": "Publication publique",
     "reutilisable": False, "certifiable": False,
     "apporte": "Le consensus international : empoisonnement, extraction, "
                "évasion — et la chaîne d'approvisionnement à trois piliers, "
                "capacité de calcul, modèles et dépendances, données.",
     "reserve": "Analyse haut niveau, volontairement non exhaustive. Ne "
                "descend pas au niveau de la technique d'attaque."},
    {"cle": "asi", "titre": "OWASP Top 10 des applications agentiques",
     "date": "décembre 2025", "licence": "Creative Commons (OWASP)",
     "reutilisable": False, "certifiable": False,
     "apporte": "La seule taxonomie de menaces propre aux agents. Trois de "
                "ses dix risques — communication inter-agents, défaillances "
                "en cascade, agents malveillants — n'ont aucun équivalent "
                "dans une application à modèle de langage simple.",
     "reserve": "Liste de risques, pas méthode d'analyse : elle dit quoi "
                "chercher, jamais dans quel ordre ni jusqu'où."},
    {"cle": "atlas", "titre": "MITRE ATLAS",
     "date": "v5.1.0, novembre 2025", "licence": "Termes MITRE",
     "reutilisable": False, "certifiable": False,
     "apporte": "Le catalogue de techniques adverses, tactique par tactique. "
                "L'essentiel de ses mesures se rattache à des contrôles déjà "
                "en place : c'est l'argument d'intégration au centre "
                "opérationnel de sécurité existant.",
     "reserve": "Catalogue de techniques constatées. Ne dit rien de la "
                "gravité pour VOTRE métier."},
    {"cle": "cop", "titre": "Code of Practice for General-Purpose AI Models "
                            "— Safety and Security Chapter",
     "date": "Commission européenne", "licence": "Texte européen",
     "reutilisable": False, "certifiable": False,
     "apporte": "Dix engagements qui structurent un dispositif complet : "
                "cadre, identification, analyse, acceptation du risque, "
                "mesures de sûreté, mesures de sécurité, rapports, "
                "responsabilités, signalement d'incident grave, "
                "documentation.",
     "reserve": "S'adresse aux FOURNISSEURS de modèles à usage général. Un "
                "opérateur d'infrastructure critique n'en est pas un — il "
                "s'en inspire, il n'y est pas soumis."},
    {"cle": "pren18286", "titre": "prEN 18286 — Système de management de la "
                                  "qualité pour le règlement européen sur l'IA",
     "date": "CEN/CLC JTC 21, enquête 2025", "licence": "Projet de norme",
     "reutilisable": False, "certifiable": False,
     "apporte": "La destination documentaire : ce que le système de "
                "management de la qualité devra contenir pour l'article 17 "
                "du règlement.",
     "reserve": "PROJET au stade de l'enquête publique. Le citer comme une "
                "norme en vigueur serait faux."},
    {"cle": "iso27090", "titre": "ISO/IEC 27090 — Menaces de sécurité visant "
                                 "les systèmes d'IA",
     "date": "FDIS 2026", "licence": "Norme ISO (payante)",
     "reutilisable": False, "certifiable": False,
     "apporte": "La taxonomie normalisée des menaces propres à l'IA.",
     "reserve": "INFORMATIVE : aucune exigence « shall », donc AUCUNE "
                "certification possible. « Conforme ISO 27090 » ne veut "
                "rien dire et ne doit jamais être écrit."},
]

# ══════════════════════════════════════════════════════════════════════════
#  L'ÉCHELLE — DEUX AXES, ET LES DEUX SE CONSTATENT
# ══════════════════════════════════════════════════════════════════════════
# CHAQUE DEGRÉ EST UN FAIT, PAS UNE APPRÉCIATION. « Bon », « satisfaisant »,
# « en cours » ne se vérifient pas et se cotent toujours trop haut. Les
# libellés ci-dessous décrivent une chose qu'on peut MONTRER — une liste tenue,
# un journal, un seuil écrit. Celui qui cote doit pouvoir produire la pièce.
AUTONOMIE = [
    {"degre": 0, "nom": "Rien sans validation",
     "dit": "Aucune action ne part sans qu'un humain l'ait approuvée, à ce maillon."},
    {"degre": 1, "nom": "Suggestion",
     "dit": "Le système propose ; c'est un humain qui exécute."},
    {"degre": 2, "nom": "Exécution encadrée",
     "dit": "Le système exécute seul, mais dans une liste d'actions fermée et écrite."},
    {"degre": 3, "nom": "Exécution ouverte",
     "dit": "Le système compose ses actions à l'exécution, sur un périmètre qui n'est pas énuméré."},
    {"degre": 4, "nom": "Autonomie pleine",
     "dit": "Le système enchaîne, délègue à d'autres agents et persiste ses décisions sans reprise humaine."},
]
MAITRISE = [
    {"degre": 0, "nom": "Aucune",
     "dit": "Rien n'est en place à ce maillon, ou personne ne sait dire ce qui l'est."},
    {"degre": 1, "nom": "Déclarée",
     "dit": "Une règle existe par écrit ; rien ne l'applique techniquement."},
    {"degre": 2, "nom": "Appliquée",
     "dit": "Un mécanisme technique l'applique, sans que son contournement soit détecté."},
    {"degre": 3, "nom": "Journalisée",
     "dit": "Le mécanisme est appliqué ET chaque franchissement laisse une trace exploitable."},
    {"degre": 4, "nom": "Éprouvée",
     "dit": "La trace est revue, et le contournement a été TENTÉ lors d'un test documenté."},
]

# ══════════════════════════════════════════════════════════════════════════
#  LES CINQ MAILLONS
# ══════════════════════════════════════════════════════════════════════════
# POURQUOI CINQ, ET POURQUOI CEUX-LÀ. Ce ne sont pas cinq thèmes choisis pour
# couvrir un sujet : c'est la séquence que franchit une action, dans l'ordre
# où elle la franchit. Une action perçue mais jamais décidée n'atteint aucun
# outil ; un outil atteint sans effet réel ne casse rien. L'ordre porte donc
# une information : le maillon ouvert le plus TARDIF est le plus coûteux,
# parce que tout ce qui précède a déjà été franchi.
MAILLONS = [
    {"cle": "perception", "rang": 1, "nom": "Perception",
     "question": "Qu'est-ce que le système accepte en entrée, et qui l'a écrit ?",
     "constat": "La liste des sources d'entrée, et lesquelles ne sont pas maîtrisées : "
                "document déposé par un tiers, page web, courriel, ticket, capteur.",
     "bien_support": "Entrées et sources de données",
     "socle": ["R25 — filtrer les entrées et les sorties",
               "R4 — évaluer la confiance des sources de données externes",
               "R13 — passerelle Internet sécurisée si le système est exposé"],
     "piege": "Une source réputée interne n'est pas une source maîtrisée : un ticket "
              "client, un courriel entrant et un document fournisseur sont écrits "
              "par des tiers et arrivent par l'intérieur."},
    {"cle": "raisonnement", "rang": 2, "nom": "Raisonnement",
     "question": "Sur quoi le système raisonne-t-il, et qui peut le modifier ?",
     "constat": "Le modèle et ses poids, le prompt système, les garde-fous, la base "
                "de connaissance interrogée, et qui a le droit d'y écrire.",
     "bien_support": "Modèle, prompt système et base de connaissance",
     "socle": ["R20 — protéger en intégrité les fichiers du système d'IA",
               "R21 — proscrire le ré-entraînement en production",
               "R6 — utiliser des formats de modèles sécurisés",
               "R3 — évaluer la confiance des bibliothèques externes"],
     "piege": "Le prompt système est un fichier de configuration qui décide du "
              "comportement : s'il se modifie sans revue ni trace, le système change "
              "d'avis sans que rien ne le dise."},
    {"cle": "decision", "rang": 3, "nom": "Décision",
     "question": "Qu'est-ce que le système tranche seul, et à partir de quel seuil il escalade ?",
     "constat": "Les seuils d'escalade ÉCRITS, ce qui déclenche une reprise humaine, "
                "et ce qui se passe quand le système hésite.",
     "bien_support": "Règles de décision et seuils d'escalade",
     "socle": ["R9 — proscrire l'usage automatisé pour des actions critiques sur le SI",
               "R27 — limiter les actions automatiques depuis des entrées non maîtrisées",
               "R8 — besoin d'en connaître dès la conception"],
     "piege": "Un seuil qui n'est écrit nulle part est un seuil que personne ne peut "
              "montrer à un auditeur, et que le prochain réglage déplacera sans débat."},
    {"cle": "action", "rang": 4, "nom": "Action",
     "question": "Quels outils le système peut-il atteindre, aujourd'hui, sans demander ?",
     "constat": "LA LISTE EXHAUSTIVE des outils, interfaces, bases, navigateurs et "
                "exécutions de code atteignables — et, pour chacun, l'identifiant "
                "employé et sa durée de vie.",
     "bien_support": "Outils, connecteurs et identifiants",
     "socle": ["R26 — maîtriser les interactions avec les autres applications métier",
               "R10 — maîtriser les accès à privilèges",
               "R29 — journaliser l'ensemble des traitements",
               "R28 — cloisonner dans un environnement dédié"],
     "piege": "C'est le maillon où se trouvent les agents que personne n'a déclarés. "
              "Un identifiant de longue durée confié à un agent est un accès permanent "
              "accordé à une chose qui change d'avis."},
    {"cle": "effet", "rang": 5, "nom": "Effet",
     "question": "Qu'est-ce qui change dans le monde réel, et comment revient-on en arrière ?",
     "constat": "Les effets irréversibles : un ordre passé, un paiement, un accès "
                "accordé, une consigne envoyée à un automate. Et le moyen d'arrêter.",
     "bien_support": "Effets métier et moyens d'arrêt",
     "socle": ["R15 — prévoir un mode dégradé des services métier sans système d'IA",
               "R24 — tests fonctionnels métier avant mise en production",
               "R23 — audit de sécurité avant mise en production"],
     "piege": "C'est le maillon que la cybersécurité industrielle connaît déjà : au-delà, "
              "il n'y a plus de correctif, il y a une conséquence. Un interrupteur d'arrêt "
              "qui n'a jamais été actionné en exercice n'est pas un interrupteur d'arrêt."},
]

# ══════════════════════════════════════════════════════════════════════════
#  LES MENACES, RATTACHÉES AU MAILLON QU'ELLES FRANCHISSENT
# ══════════════════════════════════════════════════════════════════════════
# CE RATTACHEMENT EST LE CŒUR DU MODULE. Une liste de menaces posée à plat
# n'apprend rien : on la lit, on hoche la tête, on ne fait rien. Rattachée au
# maillon qu'elle franchit, chaque menace devient une QUESTION à poser à un
# endroit précis de l'architecture — et le maillon dont l'écart est le plus
# grand désigne les menaces qui, chez ce client-là, ne rencontrent rien.
#
# LES IDENTIFIANTS SONT CEUX D'OWASP, ET LES INTITULÉS SONT LES NÔTRES : on
# nomme un risque public par son identifiant public, sans recopier le texte
# d'un document sous licence tierce.
MENACES = [
    {"cle": "ASI01", "nom": "Détournement d'objectif", "maillon": "perception",
     "dit": "Le texte présenté au système remplace l'objectif qu'on lui avait donné."},
    {"cle": "ASI02", "nom": "Mésusage d'outils", "maillon": "action",
     "dit": "Un outil légitime est employé pour ce qu'il n'était pas destiné à faire."},
    {"cle": "ASI03", "nom": "Abus d'identité et de privilèges", "maillon": "action",
     "dit": "L'agent agit sous une identité plus puissante que ce que sa tâche exige."},
    {"cle": "ASI04", "nom": "Chaîne d'approvisionnement", "maillon": "raisonnement",
     "dit": "Le modèle, une bibliothèque ou un jeu de données arrive déjà compromis."},
    {"cle": "ASI05", "nom": "Exécution de code inattendue", "maillon": "action",
     "dit": "Le système obtient une exécution que rien dans sa spécification ne prévoyait."},
    {"cle": "ASI06", "nom": "Empoisonnement de mémoire", "maillon": "raisonnement",
     "dit": "Ce qui a été écrit en mémoire aujourd'hui déclenche l'attaque dans plusieurs jours."},
    {"cle": "ASI07", "nom": "Communication inter-agents non sécurisée", "maillon": "action",
     "dit": "Un agent croit un autre agent sur parole, et rien ne vérifie l'émetteur."},
    {"cle": "ASI08", "nom": "Défaillances en cascade", "maillon": "effet",
     "dit": "L'erreur d'un agent est reprise en entrée par le suivant, et s'amplifie."},
    {"cle": "ASI09", "nom": "Exploitation de la confiance humain-agent", "maillon": "decision",
     "dit": "L'opérateur valide sans lire, parce que les mille validations précédentes étaient justes."},
    {"cle": "ASI10", "nom": "Agents malveillants", "maillon": "effet",
     "dit": "Un agent poursuit un objectif propre, dissimule ses traces ou résiste à l'arrêt."},
    # LES TROIS FAMILLES ANSSI, qui ne recoupent pas OWASP : elles décrivent
    # l'atteinte au MODÈLE, là où les dix risques ci-dessus décrivent l'atteinte
    # par l'AGENT. Un module qui n'aurait retenu qu'OWASP serait aveugle à
    # l'empoisonnement d'un jeu d'entraînement.
    {"cle": "ANSSI-INF", "nom": "Infection", "maillon": "raisonnement",
     "dit": "Le système est contaminé à l'entraînement : données altérées ou porte dérobée."},
    {"cle": "ANSSI-MAN", "nom": "Manipulation", "maillon": "perception",
     "dit": "Des requêtes malveillantes détournent le comportement en production."},
    {"cle": "ANSSI-EXF", "nom": "Exfiltration", "maillon": "action",
     "dit": "Données d'entraînement, requêtes ou paramètres du modèle sont dérobés."},
]

# ══════════════════════════════════════════════════════════════════════════
#  LES ÉVÉNEMENTS REDOUTÉS — LA SORTIE EN GRAMMAIRE EBIOS
# ══════════════════════════════════════════════════════════════════════════
# UN ÉVÉNEMENT REDOUTÉ PORTE ATTEINTE À UN BESOIN DE SÉCURITÉ D'UNE VALEUR
# MÉTIER : c'est la définition du guide, et on s'y tient. Ce que le module
# apporte, c'est qu'il ne demande PAS au client d'imaginer ces événements — il
# les DÉRIVE du maillon ouvert. Le maillon constaté ouvert désigne l'événement
# redouté ; l'écart en donne la vraisemblance ; le client n'apporte que la
# gravité, qui est la seule chose que lui seul connaît.
REDOUTES = {
    "perception": {"besoin": "Intégrité",
                   "evenement": "Le système agit sur l'objectif d'un tiers au lieu du vôtre"},
    "raisonnement": {"besoin": "Intégrité",
                     "evenement": "Le système répond faux, durablement, sans que rien ne le signale"},
    "decision": {"besoin": "Traçabilité",
                 "evenement": "Une décision engageante est prise sans que personne ne puisse dire qui l'a voulue"},
    "action": {"besoin": "Confidentialité",
               "evenement": "Le système atteint une ressource que son usage ne justifie pas"},
    "effet": {"besoin": "Disponibilité",
              "evenement": "Un effet irréversible se produit sans reprise possible"},
}

_PAR_CLE = {m["cle"]: m for m in MAILLONS}
_ORDRE = [m["cle"] for m in MAILLONS]


# ══════════════════════════════════════════════════════════════════════════
#  LA GARDE, ARMÉE À L'IMPORT
# ══════════════════════════════════════════════════════════════════════════
def _verifier():
    """Ce que ce module refuse de démarrer sans.

    Une menace rattachée à un maillon inexistant ne lève aucune erreur à
    l'usage : elle disparaît simplement du relevé, et le maillon qu'elle
    visait paraît plus sain qu'il ne l'est. C'est le défaut le moins visible
    d'une table de correspondance, et il se referme ici."""
    pb = []
    if len(_ORDRE) != len(set(_ORDRE)):
        pb.append("deux maillons portent la même clé")
    if [m["rang"] for m in MAILLONS] != list(range(1, len(MAILLONS) + 1)):
        pb.append("les rangs des maillons ne se suivent pas : l'ordre porte "
                  "une information, il ne peut pas avoir de trou")
    for m in MENACES:
        if m["maillon"] not in _PAR_CLE:
            pb.append("menace %s rattachée au maillon inconnu « %s »"
                      % (m["cle"], m["maillon"]))
    orphelins = sorted(set(_ORDRE) - {m["maillon"] for m in MENACES})
    if orphelins:
        pb.append("maillon(s) qu'aucune menace ne vise : %s — soit le maillon "
                  "n'a pas lieu d'être, soit la table est incomplète" % orphelins)
    manquants = sorted(set(_ORDRE) - set(REDOUTES))
    if manquants:
        pb.append("maillon(s) sans événement redouté : %s" % manquants)
    for s in SOURCES:
        if s.get("certifiable") and not s.get("reutilisable"):
            pb.append("source %s déclarée certifiable : à vérifier avant de "
                      "l'écrire dans une proposition" % s["cle"])
        if not (s.get("reserve") or "").strip():
            pb.append("source %s sans réserve écrite : une source dont on ne "
                      "dit pas la limite finit par être citée hors de son "
                      "domaine" % s["cle"])
    for e in (AUTONOMIE, MAITRISE):
        if [d["degre"] for d in e] != list(range(len(e))):
            pb.append("une échelle ne va pas de 0 à %d sans trou" % (len(e) - 1))
    if pb:
        raise RuntimeError("securite_ia : " + " | ".join(pb))


_verifier()


# ══════════════════════════════════════════════════════════════════════════
#  CE QUE LA PAGE DEMANDE
# ══════════════════════════════════════════════════════════════════════════
def referentiel():
    """La chaîne, les échelles, les menaces et les sources — servies, jamais
    recopiées dans la page. Une seconde liste écrite dans le gabarit
    afficherait un libellé périmé le jour où celui-ci changerait."""
    par_maillon = {}
    for m in MENACES:
        par_maillon.setdefault(m["maillon"], []).append(
            {"cle": m["cle"], "nom": m["nom"], "dit": m["dit"]})
    return {
        "ok": True,
        "maillons": [dict(m, menaces=par_maillon.get(m["cle"], []),
                          redoute=REDOUTES[m["cle"]]) for m in MAILLONS],
        "autonomie": AUTONOMIE,
        "maitrise": MAITRISE,
        "sources": SOURCES,
    }


def _degre(valeur, echelle):
    """Un degré lu dans ce qui arrive du réseau.

    Rend None pour l'absent ET pour l'invalide, jamais 0 : conflater « non
    renseigné » et « degré zéro » ferait passer un maillon jamais regardé pour
    un maillon sans aucune maîtrise — c'est-à-dire pour le pire, ce qui fait
    remonter une alerte sur du vide."""
    try:
        d = int(valeur)
    except (TypeError, ValueError):
        return None
    return d if 0 <= d <= len(echelle) - 1 else None


def evaluer(autonomie=None, maitrise=None):
    """L'écart par maillon, et LE PIRE qui commande la chaîne.

    LA MOYENNE EST REFUSÉE, ET C'EST LA DÉCISION CENTRALE DE CE MODULE. Une
    chaîne vaut son maillon le plus faible. Un raisonnement remarquablement
    encadré derrière un maillon d'action grand ouvert produit un incident, et
    la moyenne des cinq dirait le contraire — elle dirait même que tout va
    plutôt bien. `ecart_max` est donc un maximum, et une règle de `tests/`
    éprouve qu'aucune moyenne ne s'y est glissée."""
    autonomie = autonomie if isinstance(autonomie, dict) else {}
    maitrise = maitrise if isinstance(maitrise, dict) else {}
    inconnus = sorted((set(autonomie) | set(maitrise)) - set(_ORDRE))
    if inconnus:
        return {"ok": False, "erreur": "maillons_inconnus", "maillons": inconnus}

    lignes, renseignes = [], 0
    for m in MAILLONS:
        a = _degre(autonomie.get(m["cle"]), AUTONOMIE)
        t = _degre(maitrise.get(m["cle"]), MAITRISE)
        complet = a is not None and t is not None
        if complet:
            renseignes += 1
        lignes.append({
            "cle": m["cle"], "rang": m["rang"], "nom": m["nom"],
            "autonomie": a, "maitrise": t,
            "ecart": (a - t) if complet else None,
            "ouvert": bool(complet and a > t),
            "bien_support": m["bien_support"],
            "redoute": REDOUTES[m["cle"]],
            "socle": m["socle"],
        })

    mesures = [l for l in lignes if l["ecart"] is not None]
    if not mesures:
        return {"ok": True, "renseignes": 0, "maillons": lignes,
                "ecart_max": None, "commande": None, "ouverts": [],
                "lecture": "Aucun maillon n'est encore renseigné : la chaîne "
                           "ne dit rien tant que ses deux notes ne sont pas "
                           "posées sur au moins un maillon."}

    ecart_max = max(l["ecart"] for l in mesures)
    # LE MAILLON QUI COMMANDE, ET POURQUOI LE PLUS TARDIF GAGNE. À écart égal,
    # on retient celui de rang le plus élevé : tout ce qui le précède a déjà
    # été franchi, et c'est là que la conséquence se paie.
    commande = max((l for l in mesures if l["ecart"] == ecart_max),
                   key=lambda l: l["rang"])
    ouverts = [l for l in mesures if l["ouvert"]]
    return {
        "ok": True,
        "renseignes": renseignes,
        "maillons": lignes,
        "ecart_max": ecart_max,
        "commande": commande["cle"],
        "ouverts": [l["cle"] for l in ouverts],
        "menaces_sans_reponse": [
            {"cle": x["cle"], "nom": x["nom"], "dit": x["dit"],
             "maillon": x["maillon"]}
            for x in MENACES if x["maillon"] in {l["cle"] for l in ouverts}],
        "lecture": _lecture(ecart_max, commande, ouverts, renseignes),
    }


def _lecture(ecart_max, commande, ouverts, renseignes):
    """La phrase que le lecteur retient. Elle nomme le maillon, jamais un score."""
    if ecart_max <= 0:
        return ("Aucun maillon renseigné n'est ouvert : à ce stade, l'autonomie "
                "constatée ne dépasse la maîtrise nulle part. Ce constat vaut "
                "pour %d maillon(s) sur %d — il ne vaut rien pour les autres."
                % (renseignes, len(MAILLONS)))
    return ("La chaîne se joue au maillon « %s » : l'autonomie y dépasse la "
            "maîtrise de %d degré(s), et c'est le plus tardif des maillons à "
            "cet écart — tout ce qui le précède a déjà été franchi. %d maillon(s) "
            "ouvert(s) au total. Ni la moyenne des cinq ni le nombre de mesures "
            "en place ne changent cette lecture."
            % (commande["nom"], ecart_max, len(ouverts)))


# ══════════════════════════════════════════════════════════════════════════
#  LA RESTITUTION EN GRAMMAIRE EBIOS
# ══════════════════════════════════════════════════════════════════════════
# POURQUOI UNE SECONDE SORTIE PLUTÔT QU'UNE SECONDE MÉTHODE. La chaîne
# d'autonomie mesure bien, et ne se défend pas : aucun régulateur ne la
# connaît. EBIOS RM se défend, et mesure mal un système non déterministe —
# elle demande d'énumérer des chemins d'attaque qu'un agent recompose à chaque
# exécution. Conduire les deux serait entretenir deux méthodes qui
# divergeraient à la première mission.
#
# On en conduit donc UNE, et on la restitue DEUX FOIS. Le constat est fait par
# la chaîne ; il ressort dans le vocabulaire du guide, où un auditeur NIS2 le
# lit sans qu'on ait à lui expliquer quoi que ce soit.
#
# CE QUE LE CLIENT APPORTE, ET CE QUE LE MODULE DÉDUIT. La gravité est la
# seule chose qu'il est seul à savoir : elle dépend de son métier, pas de son
# architecture. Tout le reste — bien support critique, événement redouté,
# vraisemblance élémentaire, socle applicable — se déduit de ce qui a été
# constaté. Demander au client d'imaginer les scénarios serait lui rendre le
# travail pour lequel il paie.

#: La vraisemblance élémentaire, déduite de l'écart. Ce n'est pas une
#: probabilité : c'est une échelle de faisabilité, comme celle du guide.
_VRAISEMBLANCE = {
    0: ("Improbable", "L'autonomie ne dépasse pas la maîtrise à ce maillon."),
    1: ("Peu vraisemblable", "Un degré d'écart : le franchissement suppose une erreur ou un concours de circonstances."),
    2: ("Vraisemblable", "Deux degrés : le franchissement ne demande aucune compétence particulière."),
    3: ("Très vraisemblable", "Trois degrés : rien ne s'oppose au franchissement, et rien n'en garderait la trace."),
    4: ("Quasi certain", "Quatre degrés : le maillon est ouvert et l'action se produit dans le cours normal du fonctionnement."),
}

#: Les sources de risque, au sens de l'atelier 2. Elles ne sont pas déduites
#: de l'architecture : ce sont celles que la documentation publique constate
#: sur les systèmes d'IA, et le client retire celles qui ne le visent pas.
SOURCES_DE_RISQUE = [
    {"cle": "etat", "nom": "Groupe commandité par un État",
     "objectif": "Prépositionnement durable sur une infrastructure critique",
     "dit": "Ce que la sophistication ne permet plus de distinguer : les capacités des "
            "modèles ont effacé l'écart d'outillage entre un opérateur étatique et un "
            "individu isolé."},
    {"cle": "crime", "nom": "Criminalité à motivation financière",
     "objectif": "Extorsion, fraude au virement, revente de données",
     "dit": "Cherche le chemin le moins coûteux : un agent mal cloisonné est moins cher "
            "à détourner qu'un système à compromettre."},
    {"cle": "interne", "nom": "Interne, sans intention malveillante",
     "objectif": "Aller plus vite que la procédure",
     "dit": "La source la plus fréquente des agents que personne n'a déclarés : un "
            "connecteur branché un vendredi pour gagner du temps."},
    {"cle": "concurrent", "nom": "Concurrent ou prestataire indélicat",
     "objectif": "Extraction du modèle, des données ou du savoir-faire",
     "dit": "Vise le maillon du raisonnement : les poids et la base de connaissance "
            "portent l'investissement, pas l'application."},
    {"cle": "agent", "nom": "Le système lui-même",
     "objectif": "Optimiser ce qu'on lui a demandé de mesurer",
     "dit": "Source de risque sans intention : la défaillance ne vient pas d'un "
            "attaquant mais de l'optimisation. Absente des catalogues classiques, "
            "elle est nommée ici parce que la chaîne la rend visible au maillon « effet »."},
]


def restitution_ebios(autonomie=None, maitrise=None, valeur_metier=None,
                      gravite=None):
    """Le constat de la chaîne, dit dans la grammaire du guide ANSSI.

    Rend les scénarios de risque des maillons OUVERTS uniquement : un maillon
    dont la maîtrise couvre l'autonomie ne porte pas de scénario, et en écrire
    un ferait un document qui hurle partout et qu'on cesse de lire."""
    d = evaluer(autonomie, maitrise)
    if not d.get("ok"):
        return d
    vm = (valeur_metier or "").strip() or None
    try:
        g = int(gravite)
        g = g if 1 <= g <= 4 else None
    except (TypeError, ValueError):
        g = None

    ouverts = [l for l in d["maillons"] if l["ouvert"]]
    scenarios = []
    for l in sorted(ouverts, key=lambda x: (-x["ecart"], -x["rang"])):
        nom_v, dit_v = _VRAISEMBLANCE[l["ecart"]]
        actions = [{"cle": m["cle"], "nom": m["nom"], "dit": m["dit"]}
                   for m in MENACES if m["maillon"] == l["cle"]]
        scenarios.append({
            "maillon": l["cle"],
            "bien_support_critique": l["bien_support"],
            "evenement_redoute": l["redoute"]["evenement"],
            "besoin_de_securite": l["redoute"]["besoin"],
            "vraisemblance": nom_v,
            "vraisemblance_dit": dit_v,
            "ecart": l["ecart"],
            "actions_elementaires": actions,
            "socle_applicable": l["socle"],
        })
    return {
        "ok": True,
        "valeur_metier": vm,
        "gravite": g,
        "manque": ([] if vm else ["valeur_metier"]) + ([] if g else ["gravite"]),
        "scenarios": scenarios,
        "sources_de_risque": SOURCES_DE_RISQUE,
        "socle_de_securite": sorted({r for s in scenarios for r in s["socle_applicable"]}),
        "commande": d["commande"],
        "lecture": d["lecture"],
        # CE QUE LE MODULE NE DÉDUIT PAS, et le dit plutôt que de l'inventer.
        "a_fournir": "La gravité de chaque événement redouté dépend de votre "
                     "métier et non de votre architecture : elle ne se déduit "
                     "d'aucune mesure faite ici. Sans elle, ce document porte "
                     "des vraisemblances sans risques.",
    }


# ══════════════════════════════════════════════════════════════════════════
#  LE DOCUMENT EMPORTÉ
# ══════════════════════════════════════════════════════════════════════════
def markdown(autonomie=None, maitrise=None, valeur_metier=None, gravite=None,
             titre=None):
    """Le Markdown que `livrables_export` met en Word et en PDF.

    LA PREMIÈRE LIGNE DIT CE QUE LE DOCUMENT N'EST PAS, et ce n'est pas une
    précaution de style : un relevé de chaîne d'autonomie ressemble à un audit
    et n'en est pas un. Un document qui laisse l'ambiguïté se retrouve cité en
    comité comme s'il valait constat sur site."""
    r = restitution_ebios(autonomie, maitrise, valeur_metier, gravite)
    if not r.get("ok"):
        return None
    d = evaluer(autonomie, maitrise)
    L = []
    A = L.append
    A("# %s" % (titre or "Chaîne d'autonomie — relevé de sécurité de l'IA"))
    A("")
    A("> **Ce document n'est pas un audit.** Il structure un constat déclaré : "
      "personne n'est venu sur site, aucun contournement n'a été éprouvé. Un "
      "maillon coté haut en maîtrise signifie « nous affirmons tenir cela », "
      "et il faudra le montrer. Il ne vaut aucune conformité : les "
      "référentiels cités en fin de document portent chacun sa licence et son "
      "caractère certifiable, et l'un d'eux ne se certifie pas du tout.")
    A("")
    if r["valeur_metier"]:
        A("**Valeur métier étudiée** — %s" % r["valeur_metier"])
        A("")
    A("## La lecture")
    A("")
    A(d["lecture"])
    A("")
    A("## La chaîne, maillon par maillon")
    A("")
    A("| # | Maillon | Autonomie | Maîtrise | Écart | Bien support |")
    A("|---|---------|-----------|----------|-------|--------------|")
    for l in d["maillons"]:
        a = AUTONOMIE[l["autonomie"]]["nom"] if l["autonomie"] is not None else "—"
        t = MAITRISE[l["maitrise"]]["nom"] if l["maitrise"] is not None else "—"
        e = ("+%d" % l["ecart"]) if l["ecart"] and l["ecart"] > 0 else (
            "0" if l["ecart"] == 0 else "—")
        A("| %d | %s | %s | %s | **%s** | %s |"
          % (l["rang"], l["nom"], a, t, e, l["bien_support"]))
    A("")
    if r["scenarios"]:
        A("## Les scénarios de risque des maillons ouverts")
        A("")
        for s in r["scenarios"]:
            m = _PAR_CLE[s["maillon"]]
            A("### %s — %s" % (m["nom"], s["vraisemblance"]))
            A("")
            A("- **Bien support critique** — %s" % s["bien_support_critique"])
            A("- **Événement redouté** — %s" % s["evenement_redoute"])
            A("- **Besoin de sécurité atteint** — %s" % s["besoin_de_securite"])
            A("- **Vraisemblance élémentaire** — %s. %s"
              % (s["vraisemblance"], s["vraisemblance_dit"]))
            if r["gravite"]:
                A("- **Gravité déclarée** — %d sur 4" % r["gravite"])
            A("")
            A("Actions élémentaires que ce maillon ne rencontre pas :")
            A("")
            for a in s["actions_elementaires"]:
                A("- **%s · %s** — %s" % (a["cle"], a["nom"], a["dit"]))
            A("")
            A("Socle applicable à ce maillon :")
            A("")
            for x in s["socle_applicable"]:
                A("- %s" % x)
            A("")
    else:
        A("## Aucun maillon ouvert parmi ceux renseignés")
        A("")
        A("Ce constat ne vaut que pour les maillons renseignés. Un maillon "
          "laissé vide n'est pas un maillon sain : c'est un maillon qu'on "
          "n'a pas regardé.")
        A("")
    if r["manque"]:
        A("> **Ce document est incomplet.** %s" % r["a_fournir"])
        A("")
    A("## Les sources, et ce qu'on a le droit d'en faire")
    A("")
    A("| Source | Licence | Réutilisable | Certifiable |")
    A("|--------|---------|--------------|-------------|")
    for s in SOURCES:
        A("| %s (%s) | %s | %s | %s |"
          % (s["titre"], s["date"], s["licence"],
             "oui" if s["reutilisable"] else "citation seule",
             "oui" if s["certifiable"] else "**non**"))
    A("")
    A("*Méthode de la chaîne d'autonomie — CONSEILPREV. Vocabulaire d'analyse "
      "de risque repris d'EBIOS Risk Manager (ANSSI-PA-048, Licence Ouverte "
      "Etalab) ; socle de sécurité repris des recommandations ANSSI-PA-102 "
      "(Licence Ouverte v2.0). Identifiants de menaces : OWASP.*")
    return "\n".join(L)


def sante():
    """Ce que le module expose de lui-même, pour la recette et l'écran admin."""
    return {"maillons": len(MAILLONS), "menaces": len(MENACES),
            "sources": len(SOURCES),
            "reutilisables": sum(1 for s in SOURCES if s["reutilisable"]),
            "certifiables": sum(1 for s in SOURCES if s["certifiable"])}
